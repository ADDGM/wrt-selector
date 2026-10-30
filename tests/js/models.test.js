import { mockElement } from "./setup.js";
import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  insertSnapshotVersions,
  normalizeOverviewProfiles,
  changeModel,
  setupProfilesAutocomplete,
} from "../../www/js/models.js";

describe("device requests after catalogue changes", () => {
  const originalFetch = globalThis.fetch;
  const originalQuery = document._qsImpl;
  afterEach(() => {
    globalThis.fetch = originalFetch;
    document._qsImpl = originalQuery;
  });

  for (const failure of [false, true]) {
    it(`ignores a late ${
      failure ? "error" : "success"
    } without changing the current alert`, async () => {
      let finish;
      let current = true;
      const alert = mockElement({ innerText: "current catalogue error" });
      document._qsImpl = () => alert;
      globalThis.fetch = () => new Promise((resolve) => (finish = resolve));
      const pending = changeModel(
        "25.12.6",
        {
          profiles: { Device: { id: "device", target: "x86/64" } },
        },
        "Device",
        {
          config: {
            image_urls: {
              "25.12.6": "https://downloads.example/releases/25.12.6",
            },
          },
          isCurrent: () => current,
          updateImages: () => assert.fail("Old device must not update images"),
          setCurrentDevice: () =>
            assert.fail("Old device must not become current"),
        }
      );
      current = false;
      finish({
        status: failure ? 501 : 200,
        url: "old-device",
        json: async () => ({}),
      });
      await pending;
      assert.equal(alert.innerText, "current catalogue error");
    });
  }

  it("still shows errors for the current catalogue", async () => {
    const alert = mockElement();
    document._qsImpl = () => alert;
    globalThis.fetch = async () => {
      throw new TypeError("Current request failed");
    };
    await changeModel(
      "v1",
      { profiles: { Device: { id: "device", target: "x86/64" } } },
      "Device",
      {
        config: { image_urls: { v1: "https://downloads.example" } },
        isCurrent: () => true,
      }
    );
    assert.equal(alert.innerText, "Current request failed");
  });
});

describe("model selection requests", () => {
  const originalFetch = globalThis.fetch;
  const originalQuery = document._qsImpl;
  afterEach(() => {
    globalThis.fetch = originalFetch;
    document._qsImpl = originalQuery;
  });

  function mount() {
    const input = mockElement();
    const alert = mockElement();
    const requests = [];
    const updates = [];
    let device = {};
    let catalogueCurrent = true;
    document._qsImpl = (selector) => (selector === "#models" ? input : alert);
    globalThis.fetch = (url) =>
      new Promise((resolve, reject) => {
        requests.push({
          url,
          reject,
          finish(id) {
            resolve({
              status: 200,
              json: async () => ({
                profiles: {
                  [id]: {
                    images: [],
                    titles: [{ title: id }],
                    device_packages: [id],
                  },
                },
              }),
            });
          },
        });
      });
    const updateImages = (version, data) => {
      if (data) updates.push({ version, id: data.id, current: device.id });
    };
    setupProfilesAutocomplete(
      "v1",
      {
        profiles: {
          A: { id: "a", target: "target/a" },
          B: { id: "b", target: "target/b" },
        },
      },
      {
        updateImages,
        changeModelContext: {
          config: { image_urls: { v1: "https://downloads.example/v1" } },
          updateImages,
          setCurrentDevice: (next) => (device = next),
          isCurrent: () => catalogueCurrent,
        },
      }
    );
    return {
      requests,
      updates,
      alert,
      device: () => device,
      select(value, enter = false) {
        input.value = value;
        if (enter) input.onkeyup({ key: "Enter" });
        else input.oninput();
      },
      leaveCatalogue() {
        catalogueCurrent = false;
      },
    };
  }

  const flush = () => new Promise((resolve) => setImmediate(resolve));

  it("keeps the latest device when responses arrive in reverse order", async () => {
    const ui = mount();
    ui.select("A");
    ui.select("B");
    ui.requests[1].finish("b");
    await flush();
    ui.requests[0].finish("a");
    await flush();
    assert.equal(ui.device().id, "b");
    assert.deepEqual(ui.updates, [{ version: "v1", id: "b", current: "b" }]);
  });

  it("clears the build device during edits and discards an in-flight response after clearing input", async () => {
    const ui = mount();
    ui.select("A");
    ui.requests[0].finish("a");
    await flush();
    ui.select("B");
    assert.deepEqual(ui.device(), {});
    ui.select("");
    ui.requests[1].finish("b");
    await flush();
    assert.deepEqual(ui.device(), {});
    assert.equal(ui.updates.length, 1);
  });

  it("invalidates a request even if the input is edited back to the same title", async () => {
    const ui = mount();
    ui.select("A");
    ui.select("");
    ui.select("A");
    ui.requests[0].finish("a");
    await flush();
    assert.deepEqual(ui.device(), {});
    assert.equal(ui.updates.length, 0);
    ui.requests[1].finish("a");
    await flush();
    assert.equal(ui.device().id, "a");
  });

  it("ignores an old failure while showing a failure from the selected device", async () => {
    const ui = mount();
    ui.select("A");
    ui.select("B");
    ui.requests[1].reject(new Error("B failed"));
    await flush();
    ui.requests[0].reject(new Error("A failed"));
    await flush();
    assert.equal(ui.alert.innerText, "B failed");
    assert.deepEqual(ui.device(), {});
  });

  it("tracks selections through the Enter callback as well as input events", async () => {
    const ui = mount();
    ui.select("A", true);
    ui.select("B", true);
    ui.requests[1].finish("b");
    ui.requests[0].finish("a");
    await flush();
    assert.equal(ui.device().id, "b");
    assert.equal(ui.updates.length, 1);
  });

  it("continues to isolate responses and callbacks from a replaced catalogue", async () => {
    const ui = mount();
    ui.select("A");
    ui.leaveCatalogue();
    ui.select("B", true);
    ui.requests[0].finish("a");
    await flush();
    assert.equal(ui.requests.length, 1);
    assert.equal(ui.updates.length, 0);
    assert.deepEqual(ui.device(), {});
  });
});

describe("insertSnapshotVersions", () => {
  it("adds branch snapshots and SNAPSHOT", () => {
    const versions = ["23.05.4", "22.03.6"];
    insertSnapshotVersions(versions);
    assert.ok(versions.includes("23.05-SNAPSHOT"));
    assert.ok(versions.includes("22.03-SNAPSHOT"));
    assert.ok(versions.includes("SNAPSHOT"));
  });

  it("does not duplicate existing branch snapshots", () => {
    const versions = ["23.05.4", "23.05.3"];
    insertSnapshotVersions(versions);
    const count = versions.filter((v) => v === "23.05-SNAPSHOT").length;
    assert.equal(count, 1);
  });

  it("always appends SNAPSHOT at the end", () => {
    const versions = ["21.02.1"];
    insertSnapshotVersions(versions);
    assert.equal(versions[versions.length - 1], "SNAPSHOT");
  });

  it("handles empty versions list", () => {
    const versions = [];
    insertSnapshotVersions(versions);
    assert.deepEqual(versions, ["SNAPSHOT"]);
  });

  it("handles versions with different major branches", () => {
    const versions = ["23.05.4", "22.03.6", "21.02.7"];
    insertSnapshotVersions(versions);
    assert.ok(versions.includes("23.05-SNAPSHOT"));
    assert.ok(versions.includes("22.03-SNAPSHOT"));
    assert.ok(versions.includes("21.02-SNAPSHOT"));
    assert.ok(versions.includes("SNAPSHOT"));
  });

  it("does not add duplicate SNAPSHOT entry", () => {
    const versions = ["23.05.1"];
    insertSnapshotVersions(versions);
    const count = versions.filter((v) => v === "SNAPSHOT").length;
    assert.equal(count, 1);
  });

  it("preserves original version entries", () => {
    const versions = ["23.05.4", "22.03.6"];
    insertSnapshotVersions(versions);
    assert.ok(versions.includes("23.05.4"));
    assert.ok(versions.includes("22.03.6"));
  });
});

describe("normalizeOverviewProfiles", () => {
  it("transforms profile array to title-keyed object", () => {
    const input = {
      profiles: [
        {
          id: "device1",
          target: "ramips/mt7621",
          titles: [{ title: "Device One" }],
        },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    assert.ok("Device One" in result.profiles);
    assert.equal(result.profiles["Device One"].id, "device1");
    assert.equal(result.profiles["Device One"].target, "ramips/mt7621");
  });

  it("expands multiple titles into separate entries", () => {
    const input = {
      profiles: [
        {
          id: "device1",
          target: "ramips/mt7621",
          titles: [{ title: "Name A" }, { title: "Name B" }],
        },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    assert.ok("Name A" in result.profiles);
    assert.ok("Name B" in result.profiles);
  });

  it("builds title from vendor/model/variant", () => {
    const input = {
      profiles: [
        {
          id: "device1",
          target: "ath79/generic",
          titles: [{ vendor: "TP-Link", model: "Archer", variant: "v5" }],
        },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    assert.ok("TP-Link Archer v5" in result.profiles);
  });

  it("appends target to duplicate titles", () => {
    const input = {
      profiles: [
        {
          id: "dev1",
          target: "ramips/mt7621",
          titles: [{ title: "Same Name" }],
        },
        {
          id: "dev2",
          target: "ath79/generic",
          titles: [{ title: "Same Name" }],
        },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    const keys = Object.keys(result.profiles);
    assert.equal(keys.length, 2);
    assert.ok(keys.some((k) => k.includes("ramips/mt7621")));
    assert.ok(keys.some((k) => k.includes("ath79/generic")));
  });

  it("skips entries with empty title", () => {
    const input = {
      profiles: [
        {
          id: "device1",
          target: "ramips/mt7621",
          titles: [{ vendor: "", model: "", variant: "" }],
        },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    assert.equal(Object.keys(result.profiles).length, 0);
  });

  it("handles empty profiles array", () => {
    const input = { profiles: [] };
    const result = normalizeOverviewProfiles(input);
    assert.deepEqual(result.profiles, {});
  });

  it("preserves id and target on resulting entries", () => {
    const input = {
      profiles: [
        {
          id: "my-device",
          target: "ath79/generic",
          titles: [{ title: "My Device" }],
        },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    const entry = result.profiles["My Device"];
    assert.equal(entry.id, "my-device");
    assert.equal(entry.target, "ath79/generic");
  });

  it("handles case-insensitive duplicate detection", () => {
    const input = {
      profiles: [
        {
          id: "dev1",
          target: "ramips/mt7621",
          titles: [{ title: "My Device" }],
        },
        {
          id: "dev2",
          target: "ath79/generic",
          titles: [{ title: "my device" }],
        },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    const keys = Object.keys(result.profiles);
    assert.equal(keys.length, 2);
    assert.ok(keys.every((k) => k.includes("/")));
  });

  it("handles profile with vendor only", () => {
    const input = {
      profiles: [
        {
          id: "device1",
          target: "ramips/mt7621",
          titles: [{ vendor: "TP-Link" }],
        },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    assert.ok("TP-Link" in result.profiles);
  });

  it("handles many profiles without duplicates", () => {
    const input = {
      profiles: [
        { id: "d1", target: "t1", titles: [{ title: "Device A" }] },
        { id: "d2", target: "t2", titles: [{ title: "Device B" }] },
        { id: "d3", target: "t3", titles: [{ title: "Device C" }] },
      ],
    };
    const result = normalizeOverviewProfiles(input);
    assert.equal(Object.keys(result.profiles).length, 3);
  });
});
