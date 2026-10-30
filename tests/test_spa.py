from playwright.sync_api import sync_playwright, expect

def test_spa(simplehttpserver):
    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page()
        # Keep the legacy single-service catalog test independent of live releases.
        page.route("**/config.js", lambda route: route.fulfill(
            content_type="application/javascript",
            body='window.config = {image_url: "../misc", versions: ["23.05.4", "19.07.10"], default_version: "23.05.4", asu_url: "https://sysupgrade.openwrt.org"};'
        ))
        page.goto("http://localhost:8000/www/")
        page.select_option("#languages-select", "en")
        expect(page).to_have_title("OpenWrt / ImmortalWrt Firmware Selector")
        expect(page.locator("#firmware-distribution")).to_have_value("OpenWrt")

        assert page.locator("#versions").select_option("19.07.10")[0] == "19.07.10"
        expect(page.locator("#models")).to_be_enabled()

        page.fill("#models", "a7 v5")
        models = page.inner_text("#models-autocomplete-list")
        assert "TP-Link Archer A7 v5" in models

        locator = page.locator(".tr-message")
        expect(locator).to_contain_text('Choose a firmware distribution and build service')

        page.select_option("#languages-select", "de")
        expect(locator).to_contain_text('benutze die Eingabe um die passende')

        page.select_option("#languages-select", "ca")
        expect(locator).to_contain_text('el nom o el model del vostre dispositiu')

        page.select_option("#languages-select", "pl")
        expect(locator).to_contain_text('nazwę lub model swojego urządzenia')

        browser.close()
