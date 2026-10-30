import { $, hideAlert, showAlert } from "./utils.js";

export function setupUciDefaults(
  config = {},
  getService = () => ({ distribution: config.distribution || "OpenWrt" })
) {
  const button = $("#uci-defaults-template");
  const fallbackTemplate = button.getAttribute("data-link");
  const textarea = $("#uci-defaults-content");
  const label = $("#uci-defaults-distribution");
  let distribution = getService().distribution;
  const drafts = new Map([[distribution, textarea.value]]);
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

  button.onclick = async () => {
    if (button.disabled) return;
    const request = ++requestGeneration;
    const revision = editGeneration;
    const original = textarea.value;
    const templates = config.uci_defaults_templates || {};
    const url = Object.prototype.hasOwnProperty.call(templates, distribution)
      ? templates[distribution]
      : fallbackTemplate;
    setLoading(true);
    try {
      const response = await fetch(url);
      if (response.status !== 200) {
        throw new Error(`Failed to fetch ${response.url || url}`);
      }
      const text = (await response.text()).replace(/\r\n?/g, "\n");
      if (
        request !== requestGeneration ||
        revision !== editGeneration ||
        original !== textarea.value
      )
        return;
      hideAlert();
      if (!text || textarea.value.includes(text)) return;
      const separator = original && !original.endsWith("\n") ? "\n" : "";
      textarea.value = original + separator + text;
      drafts.set(distribution, textarea.value);
    } catch (error) {
      if (request === requestGeneration) showAlert(error.message);
    } finally {
      if (request === requestGeneration) setLoading(false);
    }
  };

  syncDistribution();
  return syncDistribution;
}
