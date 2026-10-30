import "./setup.js";
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  getAsuServices,
  normalizeAsuUrl,
  selectAsuService,
} from "../../www/js/asu-services.js";
import { getSelectionUrl } from "../../www/js/images.js";

describe("ASU services", () => {
  it("preserves legacy single-service metadata and defaults", () => {
    const config = {
      asu_url: "https://example.com/asu/",
      image_url: "../misc",
      versions: ["23.05.4"],
      default_version: "23.05.4",
    };
    const [service] = getAsuServices(config);
    assert.equal(service.url, "https://example.com/asu");
    assert.equal(service.image_url, "../misc");
    assert.deepEqual(service.versions, ["23.05.4"]);
    assert.equal(service.rootfs_size_mb_max, 1024);
    assert.equal(service.distribution, "OpenWrt");
    assert.equal(selectAsuService([service], config).id, service.id);
  });

  it("limits service selection to the chosen distribution, including default and shared IDs", () => {
    const config = {
      asu_url: "https://open.example",
      asu_services: [
        { id: "openwrt", distribution: "OpenWrt", url: "https://open.example" },
        {
          id: "immortalwrt-official",
          distribution: "ImmortalWrt",
          url: "https://immortal.example",
        },
        {
          id: "immortalwrt",
          distribution: "ImmortalWrt",
          url: "https://third.example",
        },
      ],
    };
    const services = getAsuServices(config);
    assert.equal(
      selectAsuService(services, config, "openwrt", "ImmortalWrt").id,
      "immortalwrt-official"
    );
    assert.equal(
      selectAsuService(services, config, "immortalwrt", "OpenWrt").id,
      "openwrt"
    );
    const shared = selectAsuService(services, config, "immortalwrt");
    assert.equal(shared.distribution, "ImmortalWrt");
    assert.equal(shared.url, "https://third.example");
    assert.equal(
      selectAsuService(services, config, undefined, "Unknown"),
      undefined
    );
  });

  it("uses per-service package defaults without reintroducing global extras", () => {
    const config = {
      distribution: "OpenWrt",
      asu_extra_packages: ["luci", "luci-app-attendedsysupgrade"],
      asu_services: [
        { id: "openwrt" },
        {
          id: "immortalwrt",
          distribution: "ImmortalWrt",
          asu_extra_packages: [],
        },
        {
          id: "custom",
          distribution: "ImmortalWrt",
          asu_extra_packages: ["custom-package"],
        },
      ],
    };
    const services = getAsuServices(config);
    assert.deepEqual(services[0].asu_extra_packages, config.asu_extra_packages);
    assert.deepEqual(services[1].asu_extra_packages, []);
    assert.deepEqual(services[2].asu_extra_packages, ["custom-package"]);
    services[0].asu_extra_packages.push("edited");
    assert.equal(config.asu_extra_packages.length, 2);
  });

  it("binds each service to its own metadata and size limit", () => {
    const config = {
      asu_url: "https://official.example",
      versions: ["legacy"],
      asu_services: [
        {
          id: "official",
          name: "Official",
          url: "https://official.example",
          image_url: "https://official-data.example",
          rootfs_size_mb_max: 1024,
        },
        {
          id: "third",
          name: "Third",
          url: "https://third.example",
          image_url: "https://third-data.example",
          rootfs_size_mb_max: 4096,
        },
      ],
    };
    const services = getAsuServices(config);
    assert.equal(
      selectAsuService(services, config, "third").image_url,
      "https://third-data.example"
    );
    assert.equal(
      selectAsuService(services, config, "third").rootfs_size_mb_max,
      4096
    );
    assert.equal(selectAsuService(services, config, "unknown").id, "official");
    assert.equal(services[0].versions, undefined);
  });

  it("normalizes base paths and rejects non-HTTP, credential and query URLs", () => {
    assert.equal(
      normalizeAsuUrl(" https://EXAMPLE.com/asu/// "),
      "https://example.com/asu"
    );
    for (const url of [
      "file:///tmp",
      "javascript:alert(1)",
      "/asu",
      "https://user:pass@example.com",
      "https://example.com?key=1",
      "https://example.com/#x",
      "https://example.com/a b",
    ]) {
      assert.throws(() => normalizeAsuUrl(url));
    }
  });

  it("rejects ambiguous service IDs and invalid size limits", () => {
    for (const asu_services of [
      [{ id: "same" }, { id: "same" }],
      [{ id: "bad id" }],
      [{ id: "good", rootfs_size_mb_max: 0 }],
      [{ id: "good", rootfs_size_mb_max: 1.5 }],
      [{ id: "good", distribution: " " }],
      [{ id: "good", distribution: {} }],
      [{ id: "good", asu_extra_packages: "luci" }],
    ])
      assert.throws(() => getAsuServices({ asu_services }));
  });

  it("shares service, version and model without carrying stale URL parameters", () => {
    const url = new URL(
      getSelectionUrl(
        {
          version_number: "24.10.6",
          target: "x86/64",
          id: "vendor,device+name",
        },
        "immortalwrt"
      )
    );
    assert.equal(url.searchParams.get("asu"), "immortalwrt");
    assert.equal(url.searchParams.get("target"), "x86/64");
    assert.equal(url.searchParams.get("id"), "vendor,device+name");
    assert.equal(
      new URL(
        getSelectionUrl({ version_number: "v", target: "t", id: "i" })
      ).searchParams.has("asu"),
      false
    );
  });
});
