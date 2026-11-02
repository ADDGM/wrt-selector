import { mockElement } from "./setup.js";
import { afterEach, describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
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
  let onLanguageChange;
  const language = mockElement({
    value: "en",
    addEventListener: (name, callback) => {
      if (name === "change") onLanguageChange = callback;
    },
  });
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
      "#languages-select": language,
    }[selector]);
  const sync = setupUciDefaults(config, () => service);
  return {
    input,
    button,
    label,
    alert,
    language,
    selectLanguage(value) {
      language.value = value;
      onLanguageChange();
    },
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

const localizedConfig = {
  uci_defaults_templates: {
    OpenWrt: { en: "open.sh", "zh-cn": "open.zh-cn.sh" },
    ImmortalWrt: { en: "immortal.sh", "zh-cn": "immortal.zh-cn.sh" },
  },
};

describe("localized script examples", () => {
  it("selects shared Chinese comments for zh-cn and zh-tw, and English for other languages", async () => {
    const urls = [];
    globalThis.fetch = async (url) => {
      urls.push(url);
      return response(`# ${url}\necho done\n`);
    };
    const ui = mount(localizedConfig);
    for (const distribution of ["OpenWrt", "ImmortalWrt"]) {
      ui.select(distribution);
      for (const language of ["zh-cn", "en", "zh-tw", "de", ""]) {
        ui.edit("");
        ui.selectLanguage(language);
        await ui.button.onclick();
        const expected =
          localizedConfig.uci_defaults_templates[distribution][
          ["zh-cn", "zh-tw"].includes(language) ? "zh-cn" : "en"
          ];
        assert.equal(urls.at(-1), expected);
        assert.equal(ui.input.value, `# ${expected}\necho done\n`);
      }
    }
  });

  it("preserves drafts across language changes, deduplicates intact variants and permits reinsertion after deletion", async () => {
    globalThis.fetch = async (url) => response(`# ${url}\necho done\n`);
    const ui = mount(localizedConfig, "echo custom");
    ui.selectLanguage("zh-cn");
    await ui.button.onclick();
    const chineseDraft = ui.input.value;
    ui.selectLanguage("en");
    assert.equal(ui.input.value, chineseDraft);
    await ui.button.onclick();
    assert.equal(ui.input.value, chineseDraft);
    ui.select("ImmortalWrt");
    await ui.button.onclick();
    const immortalDraft = ui.input.value;
    ui.select("OpenWrt");
    await ui.button.onclick();
    assert.equal(ui.input.value, chineseDraft);
    ui.edit("echo custom");
    await ui.button.onclick();
    assert.equal(ui.input.value, "echo custom\n# open.sh\necho done\n");
    ui.selectLanguage("zh-cn");
    await ui.button.onclick();
    assert.equal(ui.input.value, "echo custom\n# open.sh\necho done\n");
    ui.select("ImmortalWrt");
    assert.equal(ui.input.value, immortalDraft);
    await ui.button.onclick();
    assert.equal(ui.input.value, immortalDraft);
  });

  it("discards pending text after a language change, including changing away and back", async () => {
    for (const changeBack of [false, true]) {
      let resolve;
      globalThis.fetch = () =>
        new Promise((done) => {
          resolve = done;
        });
      const ui = mount(localizedConfig, "# custom");
      const pending = ui.button.onclick();
      ui.selectLanguage("zh-cn");
      if (changeBack) ui.selectLanguage("en");
      assert.equal(ui.button.disabled, false);
      resolve(response("# old language"));
      await pending;
      assert.equal(ui.input.value, "# custom");
    }
  });

  it("does not let an old language request unlock or report an error over a newer request", async () => {
    let rejectOld;
    let resolveNew;
    globalThis.fetch = () =>
      new Promise((_resolve, reject) => {
        rejectOld = reject;
      });
    const ui = mount(localizedConfig);
    const oldRequest = ui.button.onclick();
    ui.selectLanguage("zh-cn");
    globalThis.fetch = () =>
      new Promise((resolve) => {
        resolveNew = resolve;
      });
    const newRequest = ui.button.onclick();
    rejectOld(Error("old language failed"));
    await oldRequest;
    assert.equal(ui.alert.innerText, "");
    assert.equal(ui.button.disabled, true);
    resolveNew(response("# 中文示例"));
    await newRequest;
    assert.equal(ui.input.value, "# 中文示例");
    assert.equal(ui.button.disabled, false);
  });

  it("falls back to English, legacy string URLs and data-link without requesting an object", async () => {
    let requested;
    globalThis.fetch = async (url) => {
      requested = url;
      return response("# example");
    };
    for (const [template, expected] of [
      [{ en: "english.sh" }, "english.sh"],
      ["single.sh", "single.sh"],
      [{}, "legacy.sh"],
    ]) {
      const ui = mount({ uci_defaults_templates: { OpenWrt: template } });
      ui.selectLanguage("zh-cn");
      await ui.button.onclick();
      assert.equal(requested, expected);
    }
  });

  it("loads real configured templates whose translations preserve code, logs and sample assignments", async () => {
    const root = new URL("../../www/", import.meta.url);
    const context = {};
    runInNewContext(readFileSync(new URL("config.js", root), "utf8"), context);
    globalThis.fetch = async (url) =>
      response(readFileSync(new URL(url, root), "utf8"));
    const ui = mount(context.config);
    const executableAndOptions = (text) =>
      text
        .split("\n")
        .filter(
          (line) =>
            !line.trimStart().startsWith("#") || /^\s*#(?:!|\s*\w+=)/.test(line)
        );
    for (const distribution of ["OpenWrt", "ImmortalWrt"]) {
      ui.select(distribution);
      ui.selectLanguage("en");
      await ui.button.onclick();
      const english = ui.input.value;
      ui.edit("");
      ui.selectLanguage("zh-cn");
      await ui.button.onclick();
      const chinese = ui.input.value;
      assert.match(chinese, /#.*[\u4e00-\u9fff]/);
      assert.notEqual(english, chinese);
      assert.deepEqual(
        executableAndOptions(english),
        executableAndOptions(chinese)
      );
      assert.match(chinese, new RegExp(`# wlan_name="${distribution}"`));
    }
  });
});
