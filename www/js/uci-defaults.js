import { $, hideAlert, showAlert } from "./utils.js";

export function setupUciDefaults(
  config = {},
  getService = () => ({ distribution: config.distribution || "OpenWrt" })
) {
  const button = $("#uci-defaults-template");
  const fallbackTemplate = button.getAttribute("data-link");
  const textarea = $("#uci-defaults-content");
  const label = $("#uci-defaults-distribution");
  const languageSelect = $("#languages-select");
  const templateLanguage = () =>
    ["zh-cn", "zh-tw"].includes(languageSelect?.value) ? "zh-cn" : "en";
  let distribution = getService().distribution;
  const drafts = new Map([[distribution, textarea.value]]);
  const loadedTemplates = new Map();
  let requestGeneration = 0;
  let editGeneration = 0;

  function setLoading(loading) {
    button.disabled = loading;
    button.setAttribute("aria-busy", String(loading));
  }

  function syncDistribution() {
    const next = getService().distribution;
    if (next !== distribution) {
      drafts.set(distribution, textarea.value);
      distribution = next;
      textarea.value = drafts.get(next) ?? "";
      // Ignore template responses belonging to a previous selection.
      requestGeneration += 1;
      setLoading(false);
    }
    label.textContent = distribution;
  }

  textarea.addEventListener("input", () => {
    editGeneration += 1;
    drafts.set(distribution, textarea.value);
  });

  languageSelect?.addEventListener("change", () => {
    // Keep the draft, but discard responses requested before the language change.
    requestGeneration += 1;
    setLoading(false);
  });

  button.onclick = async () => {
    if (button.disabled) return;
    const request = ++requestGeneration;
    const revision = editGeneration;
    const original = textarea.value;
    const language = templateLanguage();
    const templates = config.uci_defaults_templates || {};
    const template = Object.prototype.hasOwnProperty.call(
      templates,
      distribution
    )
      ? templates[distribution]
      : fallbackTemplate;
    const url =
      typeof template === "string"
        ? template
        : template?.[language] || template?.en || fallbackTemplate;
    setLoading(true);
    try {
      const response = await fetch(url);
      if (response.status !== 200) {
        throw new Error(`Failed to fetch ${response.url || url}`);
      }
      const text = (await response.text()).replace(/\r\n?/g, "\n");
      if (
        request !== requestGeneration ||
        language !== templateLanguage() ||
        revision !== editGeneration ||
        original !== textarea.value
      )
        return;
      hideAlert();
      if (!text) return;
      const variants = loadedTemplates.get(distribution) || new Set();
      variants.add(text);
      loadedTemplates.set(distribution, variants);
      // An intact example in either language already satisfies the insertion.
      if ([...variants].some((variant) => textarea.value.includes(variant)))
        return;
      const separator = original && !original.endsWith("\n") ? "\n" : "";
      textarea.value = original + separator + text;
      drafts.set(distribution, textarea.value);
    } catch (error) {
      if (request === requestGeneration && language === templateLanguage())
        showAlert(error.message);
    } finally {
      if (request === requestGeneration) setLoading(false);
    }
  };

  syncDistribution();
  return syncDistribution;
}
