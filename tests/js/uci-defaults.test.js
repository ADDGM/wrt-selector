import { mockElement } from "./setup.js";
import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import { setupUciDefaults } from "../../www/js/uci-defaults.js";

const originalQuery = document._qsImpl;
const originalFetch = globalThis.fetch;

afterEach(() => {
  document._qsImpl = originalQuery;
  globalThis.fetch = originalFetch;
});

function mount(config = {}, initial = "") {
  let service = { distribution: "OpenWrt", id: "openwrt" };
  let onInput;
  const input = mockElement({
    value: initial,
    addEventListener: (name, callback) => {
      if (name === "input") onInput = callback;
    },
  });
  const button = mockElement({ getAttribute: () => "legacy.sh" });
  const label = mockElement();
  const alert = mockElement();
  document._qsImpl = (selector) =>
    ({
      "#uci-defaults-content": input,
      "#uci-defaults-template": button,
      "#uci-defaults-distribution": label,
      "#alert": alert,
    }[selector]);
  const sync = setupUciDefaults(config, () => service);
  return {
    input,
    button,
    label,
    alert,
    edit(value) {
      input.value = value;
      onInput();
    },
    select(distribution, id = distribution) {
      service = { distribution, id };
      sync();
    },
  };
}

function response(text, status = 200) {
  return { status, text: async () => text };
}

const config = {
  uci_defaults_templates: { OpenWrt: "open.sh", ImmortalWrt: "immortal.sh" },
};

describe("distribution script drafts", () => {
  it("keeps separate drafts, including empty drafts, and shares them between same-system services", () => {
    globalThis.fetch = () => {
      throw Error("Templates require an explicit click");
    };
    const ui = mount(config, "# initial");
    assert.equal(ui.input.value, "# initial");
    ui.edit("uci set system.@system[0].hostname='OpenWrt-custom'\n");
    const open = ui.input.value;
    ui.select("ImmortalWrt", "official");
    assert.equal(ui.input.value, "");
    assert.equal(ui.label.textContent, "ImmortalWrt");
    ui.edit("# immortal\necho 'keep exactly'");
    ui.select("ImmortalWrt", "kyaru");
    assert.equal(ui.input.value, "# immortal\necho 'keep exactly'");
    ui.select("OpenWrt");
    assert.equal(ui.input.value, open);
    ui.edit("");
    ui.select("ImmortalWrt");
    ui.select("OpenWrt");
    assert.equal(ui.input.value, "");
  });

  it("inserts the matching template once without removing or rewriting existing commands", async () => {
    const urls = [];
    globalThis.fetch = async (url) => {
      urls.push(url);
      return response(`# ${url}\r\necho done\r\n`);
    };
    const ui = mount(config);
    ui.edit("echo 'OpenWrt must stay literal'");
    await ui.button.onclick();
    const expected = "echo 'OpenWrt must stay literal'\n# open.sh\necho done\n";
    assert.equal(ui.input.value, expected);
    await ui.button.onclick();
    assert.equal(ui.input.value, expected);
    ui.select("ImmortalWrt");
    await ui.button.onclick();
    assert.equal(ui.input.value, "# immortal.sh\necho done\n");
    ui.select("OpenWrt");
    assert.equal(ui.input.value, expected);
    assert.deepEqual(urls, ["open.sh", "open.sh", "immortal.sh"]);
  });

  it("ignores a pending template after switching away and back", async () => {
    let resolve;
    globalThis.fetch = () =>
      new Promise((done) => {
        resolve = done;
      });
    const ui = mount(config);
    ui.edit("# keep");
    const pending = ui.button.onclick();
    assert.equal(ui.button.disabled, true);
    ui.select("ImmortalWrt");
    assert.equal(ui.button.disabled, false);
    ui.edit("# other");
    ui.select("OpenWrt");
    resolve(response("# stale template"));
    await pending;
    assert.equal(ui.input.value, "# keep");
    ui.select("ImmortalWrt");
    assert.equal(ui.input.value, "# other");
  });

  it("does not inject a pending template after the user edits and undoes the draft", async () => {
    let resolve;
    globalThis.fetch = () =>
      new Promise((done) => {
        resolve = done;
      });
    const ui = mount(config);
    ui.edit("# original");
    const pending = ui.button.onclick();
    ui.edit("# changed");
    ui.edit("# original");
    resolve(response("# template"));
    await pending;
    assert.equal(ui.input.value, "# original");
    assert.equal(ui.button.disabled, false);
  });

  it("continues a pending template across services in the same distribution", async () => {
    let resolve;
    globalThis.fetch = () =>
      new Promise((done) => {
        resolve = done;
      });
    const ui = mount(config);
    ui.select("ImmortalWrt", "official");
    const pending = ui.button.onclick();
    ui.select("ImmortalWrt", "kyaru");
    assert.equal(ui.button.disabled, true);
    resolve(response("# immortal template"));
    await pending;
    assert.equal(ui.input.value, "# immortal template");
  });

  it("retains drafts on load failure and permits retry", async () => {
    globalThis.fetch = async () => response("not found", 404);
    const ui = mount(config, "# custom");
    await ui.button.onclick();
    assert.equal(ui.input.value, "# custom");
    assert.equal(ui.button.disabled, false);
    assert.match(ui.alert.innerText, /Failed to fetch open.sh/);
    globalThis.fetch = async () => response("# template");
    await ui.button.onclick();
    assert.equal(ui.input.value, "# custom\n# template");
    assert.equal(ui.alert.innerText, "");
  });

  it("does not show an old request error over another distribution", async () => {
    let reject;
    globalThis.fetch = () =>
      new Promise((_resolve, fail) => {
        reject = fail;
      });
    const ui = mount(config);
    const pending = ui.button.onclick();
    ui.select("ImmortalWrt");
    reject(Error("old failure"));
    await pending;
    assert.equal(ui.alert.innerText, "");
    assert.equal(ui.button.disabled, false);
  });

  it("uses the legacy template fallback for an unconfigured distribution", async () => {
    let requested;
    globalThis.fetch = async (url) => {
      requested = url;
      return response("# legacy");
    };
    const ui = mount();
    ui.select("Custom");
    await ui.button.onclick();
    assert.equal(requested, "legacy.sh");
    assert.equal(ui.input.value, "# legacy");
  });
});
