from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


BASE_URL = "http://localhost:8000/www/"
INDEX_PATH = Path(__file__).resolve().parents[1] / "www" / "index.html"
SERVICES = [
    ("openwrt", "OpenWrt", "https://sysupgrade.openwrt.org", "25.12.6", 1024),
    ("immortalwrt-official", "ImmortalWrt", "https://sysupgrade.immortalwrt.org", "25.12.2", 4096),
    ("immortalwrt", "ImmortalWrt", "https://sysupgrade.kyarucloud.moe", "25.12.2", 4096),
]
PROFILES = [
    {"id": "device-a", "target": "ramips/mt7621", "titles": [{"title": "Test Device A"}]},
    {"id": "device-b", "target": "x86/64", "titles": [{"title": "Test Device B"}]},
]


@pytest.fixture
def selector(simplehttpserver):
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch()
        page = browser.new_page(locale="en-US")
        state = SimpleNamespace(
            page=page, counts=Counter(), posts=[], polls=[], errors=[],
            unexpected=[], overview_statuses=[], delay_a=False, delayed_profiles=[],
        )
        page.on("pageerror", lambda error: state.errors.append(str(error)))

        def serve_profile(route):
            path = urlsplit(route.request.url).path
            profile = PROFILES[0 if "/ramips/" in path else 1]
            route.fulfill(json={
                "target": profile["target"],
                "version_number": path.split("/releases/")[1].split("/")[0],
                "version_code": "r-test",
                "default_packages": ["base-files"],
                "profiles": {profile["id"]: {
                    "titles": profile["titles"], "images": [],
                    "device_packages": [profile["id"] + "-package"],
                }},
            })

        def handle(route):
            request = route.request
            parsed = urlsplit(request.url)
            if parsed.hostname == "localhost":
                # Keep local HTTP scanners from injecting scripts into the test document.
                if request.resource_type == "document" and parsed.path == "/www/":
                    route.fulfill(path=str(INDEX_PATH))
                else:
                    route.continue_()
                return
            state.counts[request.url] += 1
            if parsed.hostname in ("downloads.openwrt.org", "downloads.immortalwrt.org"):
                version = "25.12.2" if "immortalwrt" in parsed.hostname else "25.12.6"
                if parsed.path.endswith("/.versions.json"):
                    route.fulfill(json={"stable_version": version, "versions_list": [version, "24.10.4"]})
                    return
                if parsed.path.endswith("/.overview.json"):
                    status = state.overview_statuses.pop(0) if state.overview_statuses else 200
                    if status == 200:
                        route.fulfill(json={"profiles": PROFILES})
                    else:
                        route.fulfill(status=status, body="")
                    return
                if parsed.path.endswith("/profiles.json"):
                    if state.delay_a and "/ramips/" in parsed.path:
                        state.delayed_profiles.append(route)
                    else:
                        serve_profile(route)
                    return
            if any(request.url.startswith(service[2] + "/api/v1/build") for service in SERVICES):
                if request.method == "POST":
                    state.posts.append((request.url, request.post_data_json))
                    route.fulfill(status=202, json={"request_hash": "test-job", "detail": "queued"})
                else:
                    state.polls.append(request.url)
                    body = state.posts[-1][1]
                    route.fulfill(json={
                        "bin_dir": "test-job", "build_cmd": "make image", "manifest": "base-files - 1",
                        "target": body["target"], "version_number": body["version"],
                        "version_code": body["version_code"], "titles": PROFILES[1]["titles"],
                        "images": [{"type": "sysupgrade", "name": "firmware-test.bin"}],
                    })
                return
            state.unexpected.append(request.url)
            route.abort()

        state.serve_profile = serve_profile
        # Use the real deployment config and local templates; no remote builds or feeds.
        page.route("**/*", handle)
        try:
            yield state
            assert state.errors == []
            assert state.unexpected == []
        finally:
            browser.close()


def open_selector(state, service="openwrt"):
    page = state.page
    page.goto(BASE_URL + "?asu=" + service)
    expect(page.locator("#models")).to_be_enabled()
    page.select_option("#languages-select", "en")
    return page


def select_device(page):
    expect(page.locator("#models")).to_be_enabled()
    page.fill("#models", "Test Device B")
    expect(page.locator("#images")).to_be_visible()
    expect(page.locator("#image-model")).to_have_text("Test Device B")
    page.locator("#asu > summary").click()


@pytest.mark.parametrize("service,distribution,backend,version,maximum", SERVICES)
def test_build_request_polling_and_download(selector, service, distribution, backend, version, maximum):
    page = open_selector(selector, service)
    expect(page.locator("#firmware-distribution")).to_have_value(distribution)
    select_device(page)
    page.locator("#asu-advanced > summary").click()
    size = page.locator("#asu-rootfs-size")
    expect(size).to_have_attribute("max", str(maximum))
    size.fill(str(maximum + 1))
    page.locator("#asu-request-build").click()
    expect(page.locator("#asu-buildstatus")).to_contain_text("whole number")
    assert selector.posts == []
    size.fill("1024" if maximum == 1024 else "2048")
    script = "# " + distribution + "\necho 'keep this command'\n"
    page.fill("#uci-defaults-content", script)
    page.fill("#asu-packages", "base-files custom-package")
    page.locator("#asu-add-repository").click()
    page.locator(".asu-repository-name").fill("custom")
    page.locator(".asu-repository-url").fill(
        "https://feeds.example/{openwrt_branch}/{openwrt_version}/{target}/{subtarget}"
    )
    expect(page.locator("#asu-repositories-mode")).to_have_value("append")
    for key in ("public-key-one\nline-two", "public-key-two"):
        page.locator("#asu-add-key").click()
        page.locator("#asu-repository-keys textarea").last.fill(key)
    with page.expect_request(backend + "/api/v1/build") as sent:
        page.locator("#asu-request-build").click()
    body = sent.value.post_data_json
    assert body["profile"] == "device-b"
    assert body["target"] == "x86/64"
    assert body["version"] == version
    assert body["packages"] == ["base-files", "custom-package"]
    assert body["defaults"] == script
    assert body["rootfs_size_mb"] == (1024 if maximum == 1024 else 2048)
    assert body["repositories_mode"] == "append"
    assert body["repositories"] == {"custom": f"https://feeds.example/25.12/{version}/x86/64"}
    assert body["repository_keys"] == ["public-key-one\nline-two", "public-key-two"]
    for control in ("#firmware-distribution", "#asu-service", "#versions", "#models"):
        expect(page.locator(control)).to_be_disabled()
    expect(page.locator("#download-table1 a")).to_have_attribute(
        "href", backend + "/store/test-job/firmware-test.bin", timeout=15000
    )
    assert selector.polls == [backend + "/api/v1/build/test-job"]
    assert len(selector.posts) == 1
    for control in ("#firmware-distribution", "#asu-service", "#versions", "#models"):
        expect(page.locator(control)).to_be_enabled()


def test_distribution_drafts_and_catalogue_reuse(selector):
    page = open_selector(selector)
    select_device(page)
    draft = page.locator("#uci-defaults-content")
    draft.fill("# OpenWrt custom\n")
    page.locator("#uci-defaults-template").click()
    expect(page.locator("#uci-defaults-template")).to_be_enabled()
    open_draft = draft.input_value()
    assert open_draft.startswith("# OpenWrt custom\n")
    assert len(open_draft) > len("# OpenWrt custom\n")
    page.locator("#uci-defaults-template").click()
    expect(page.locator("#uci-defaults-template")).to_be_enabled()
    expect(draft).to_have_value(open_draft)
    page.select_option("#firmware-distribution", "ImmortalWrt")
    select_device(page)
    expect(draft).to_have_value("")
    draft.fill("# ImmortalWrt custom\n")
    page.locator("#uci-defaults-template").click()
    expect(page.locator("#uci-defaults-template")).to_be_enabled()
    immortal_draft = draft.input_value()
    assert len(immortal_draft) > len("# ImmortalWrt custom\n")
    page.select_option("#asu-service", "immortalwrt")
    select_device(page)
    expect(draft).to_have_value(immortal_draft)
    page.select_option("#firmware-distribution", "OpenWrt")
    select_device(page)
    expect(draft).to_have_value(open_draft)
    for url, count in selector.counts.items():
        if url.endswith(("/.versions.json", "/.overview.json")):
            assert count == 1, (url, count)
    page.reload()
    expect(page.locator("#images")).to_be_visible()
    expect(draft).to_have_value("")


def test_catalogue_transient_failure_and_retry(selector):
    selector.overview_statuses = [501]
    page = open_selector(selector)
    expect(page.locator("#alert")).to_be_hidden()
    url = "https://downloads.openwrt.org/releases/25.12.6/.overview.json"
    assert selector.counts[url] == 2
    selector.overview_statuses = [501, 501]
    page.reload()
    expect(page.locator("#alert")).to_contain_text("HTTP 501")
    expect(page.locator("#models")).to_be_disabled()
    assert selector.counts[url] == 4
    page.select_option("#firmware-distribution", "ImmortalWrt")
    expect(page.locator("#models")).to_be_enabled()
    page.select_option("#firmware-distribution", "OpenWrt")
    expect(page.locator("#models")).to_be_enabled()
    expect(page.locator("#alert")).to_be_hidden()
    assert selector.counts[url] == 5


def test_late_model_response_does_not_replace_selection(selector):
    page = open_selector(selector)
    selector.delay_a = True
    with page.expect_request("**/ramips/mt7621/profiles.json"):
        page.fill("#models", "Test Device A")
    select_device(page)
    with page.expect_response("**/ramips/mt7621/profiles.json"):
        selector.serve_profile(selector.delayed_profiles.pop())
    page.wait_for_load_state("networkidle")
    expect(page.locator("#image-model")).to_have_text("Test Device B")
    assert "device-b-package" in page.locator("#asu-packages").input_value()
    assert "id=device-b" in page.locator("#image-link").get_attribute("href")
    with page.expect_request("**/ramips/mt7621/profiles.json"):
        page.fill("#models", "Test Device A")
    page.fill("#models", "")
    with page.expect_response("**/ramips/mt7621/profiles.json"):
        selector.serve_profile(selector.delayed_profiles.pop())
    page.wait_for_load_state("networkidle")
    expect(page.locator("#images")).to_be_hidden()
    page.locator("#asu-request-build").evaluate("button => button.click()")
    assert selector.posts == []
