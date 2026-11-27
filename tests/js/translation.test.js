import "./setup.js";
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { translate } from "../../www/js/translation.js";

describe("translate", () => {
  it("fetches on first translate to en when no language is loaded yet", () => {
    let fetchCalled = false;
    globalThis.fetch = () => {
      fetchCalled = true;
      return Promise.resolve({ status: 200, json: () => Promise.resolve({}) });
    };

    translate("en");
    assert.equal(fetchCalled, true);
  });

  it("does not throw when called without arguments", () => {
    globalThis.fetch = () =>
      Promise.resolve({ status: 200, json: () => Promise.resolve({}) });
    assert.doesNotThrow(() => translate());
  });

  it("does not throw when called with the current language", () => {
    globalThis.fetch = () =>
      Promise.resolve({ status: 200, json: () => Promise.resolve({}) });
    assert.doesNotThrow(() => translate("en"));
  });

  it("calls fetch with correct URL for a new language", async () => {
    let fetchedUrl;
    globalThis.fetch = (url) => {
      fetchedUrl = url;
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve({ "tr-hello": "Hallo" }),
      });
    };

    translate("de");
    await new Promise((r) => setTimeout(r, 50));

    assert.equal(fetchedUrl, "langs/de.json");
  });

  it("does not fetch again when language was already loaded", () => {
    let fetchCalled = false;
    globalThis.fetch = () => {
      fetchCalled = true;
      return Promise.resolve({ status: 200, json: () => Promise.resolve({}) });
    };

    translate("de");
    assert.equal(fetchCalled, false);
  });

  it("fetches again when switching to another new language", async () => {
    let fetchedUrl;
    globalThis.fetch = (url) => {
      fetchedUrl = url;
      return Promise.resolve({
        status: 200,
        json: () => Promise.resolve({ "tr-hello": "Bonjour" }),
      });
    };

    translate("fr");
    await new Promise((r) => setTimeout(r, 50));

    assert.equal(fetchedUrl, "langs/fr.json");
  });

  it("replaces image help when the next language lacks a specific or generic translation", async (t) => {
    const key = "tr-x86-combined-efi-help";
    const row = {
      dataset: {
        trFallback: "tr-other-help",
        trDefault: "COMBINED-EFI",
        trDetail: "tr-squashfs-help",
      },
    };
    t.mock.method(document, "_qsaImpl", (selector) =>
      ["[data-tr-fallback]", `.${key}`].includes(selector) ? [row] : []
    );
    const fetchMock = t.mock.method(globalThis, "fetch");
    for (const [lang, mapping, expected] of [
      [
        "with-specific",
        {
          [key]: "UEFI image.",
          "tr-squashfs-help": "Read-only base.",
          "tr-other-help": "Other file",
        },
        "UEFI image. Read-only base.",
      ],
      ["only-specific", { [key]: "Image UEFI." }, "Image UEFI."],
      ["only-generic", { "tr-other-help": "Autre fichier" }, "Autre fichier"],
      ["no-image-help", {}, "COMBINED-EFI"],
    ]) {
      fetchMock.mock.mockImplementation(async () => ({
        status: 200,
        json: async () => mapping,
      }));
      translate(lang);
      await new Promise(setImmediate);
      assert.equal(row.innerText, expected);
    }
  });

  it("handles fetch rejection gracefully", async () => {
    globalThis.fetch = () => Promise.reject(new Error("Network error"));

    assert.doesNotThrow(() => translate("xx"));
    await new Promise((r) => setTimeout(r, 50));
  });

  it("handles non-200 response gracefully", async () => {
    globalThis.fetch = () =>
      Promise.resolve({ status: 404, url: "langs/zz.json" });

    assert.doesNotThrow(() => translate("zz"));
    await new Promise((r) => setTimeout(r, 50));
  });
});
