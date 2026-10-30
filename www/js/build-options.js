import { $, $$ } from "./utils.js";
import { translate } from "./translation.js";
import { getAsuServices, selectAsuService } from "./asu-services.js";

export const buildOptionMessages = {
  "tr-rootfs-invalid":
    "Enter a whole number within the selected service's size range, or leave it empty.",
  "tr-repository-name-invalid":
    "Enter a feed name using letters, numbers, underscores, dots or hyphens.",
  "tr-repository-name-duplicate": "Each feed must have a different name.",
  "tr-repository-url-invalid":
    "Enter a complete HTTP or HTTPS feed URL. Check any placeholders.",
};

export function buildOptionsFromConfig(config) {
  return {
    rootfsSize: config.asu_rootfs_size_mb ?? "",
    repositories: Object.entries(config.asu_repositories || {}).map(
      ([name, url]) => ({ name, url })
    ),
    repositoryKeys: [...(config.asu_repository_keys || [])],
    repositoriesMode:
      config.asu_repositories_mode === "replace" ? "replace" : "append",
  };
}

function invalidOption(message, selector, index) {
  const error = new Error(message);
  error.selector = selector;
  error.index = index;
  throw error;
}

export function prepareBuildOptions(options, device, version, maximum = 1024) {
  const result = { repositories: {}, repository_keys: [] };
  const size = String(options.rootfsSize ?? "").trim();
  if (size !== "") {
    if (!/^\d+$/.test(size) || Number(size) < 1 || Number(size) > maximum) {
      invalidOption("tr-rootfs-invalid", "#asu-rootfs-size");
    }
    result.rootfs_size_mb = Number(size);
  }

  const [target = "", subtarget = ""] = String(device.target || "").split("/");
  const versionString = String(version || "");
  const branch = versionString.match(/^(\d+\.\d+)/)?.[1] || versionString;
  const replacements = {
    openwrt_branch: branch,
    openwrt_version: versionString,
    target,
    subtarget,
  };
  const names = new Set();
  const repositories = [];
  for (const [index, row] of (options.repositories || []).entries()) {
    const name = String(row.name || "").trim();
    const rawUrl = String(row.url || "").trim();
    if (!name && !rawUrl) continue;
    if (!/^[\w.-]+$/.test(name)) {
      invalidOption(
        "tr-repository-name-invalid",
        "#asu-repositories .asu-repository-name",
        index
      );
    }
    if (names.has(name)) {
      invalidOption(
        "tr-repository-name-duplicate",
        "#asu-repositories .asu-repository-name",
        index
      );
    }

    const url = rawUrl.replace(/\{([^{}]+)\}/g, (match, key) =>
      Object.prototype.hasOwnProperty.call(replacements, key)
        ? replacements[key]
        : match
    );
    let validUrl = /^https?:\/\/[^\s{}]+$/i.test(url);
    try {
      const parsed = new URL(url);
      validUrl = validUrl && !!parsed.hostname;
    } catch {
      validUrl = false;
    }
    if (!validUrl) {
      invalidOption(
        "tr-repository-url-invalid",
        "#asu-repositories .asu-repository-url",
        index
      );
    }
    names.add(name);
    repositories.push([name, url]);
  }
  result.repositories = Object.fromEntries(repositories);
  if (repositories.length > 0) {
    result.repositories_mode =
      options.repositoriesMode === "replace" ? "replace" : "append";
  }
  result.repository_keys = (options.repositoryKeys || [])
    .map((key) => String(key).replace(/\r\n?/g, "\n").trim())
    .filter(Boolean);
  return result;
}

export function setupBuildOptions(
  config,
  getService = () => selectAsuService(getAsuServices(config), config)
) {
  const initial = buildOptionsFromConfig(config);
  const rootfs = $("#asu-rootfs-size");
  const mode = $("#asu-repositories-mode");
  rootfs.value = initial.rootfsSize;
  mode.value = initial.repositoriesMode;
  function updateSizeRange() {
    const maximum = getService().rootfs_size_mb_max;
    rootfs.max = maximum;
    $("#asu-rootfs-range").textContent = `1–${maximum}`;
  }
  updateSizeRange();
  $("#asu-service").addEventListener("change", updateSizeRange);

  function addRow(template, container) {
    const row = $(template).content.firstElementChild.cloneNode(true);
    row.querySelector("button").addEventListener("click", () => row.remove());
    $(container).appendChild(row);
    return row;
  }

  function addRepository(repository = {}) {
    const row = addRow("#asu-repository-template", "#asu-repositories");
    row.querySelector(".asu-repository-name").value = repository.name || "";
    row.querySelector(".asu-repository-url").value = repository.url || "";
    return row;
  }

  function addKey(key = "") {
    const row = addRow("#asu-key-template", "#asu-repository-keys");
    row.querySelector("textarea").value = key;
    return row;
  }

  initial.repositories.forEach(addRepository);
  initial.repositoryKeys.forEach(addKey);
  $("#asu-add-repository").addEventListener("click", () => {
    const row = addRepository();
    translate();
    row.querySelector("input").focus();
  });
  $("#asu-add-key").addEventListener("click", () => {
    const row = addKey();
    translate();
    row.querySelector("textarea").focus();
  });

  return (device, version, service = getService()) => {
    try {
      if (rootfs.validity.badInput) {
        invalidOption("tr-rootfs-invalid", "#asu-rootfs-size");
      }
      return prepareBuildOptions(
        {
          rootfsSize: rootfs.value,
          repositoriesMode: mode.value,
          repositories: Array.from(
            $$("#asu-repositories .asu-repository"),
            (row) => ({
              name: row.querySelector(".asu-repository-name").value,
              url: row.querySelector(".asu-repository-url").value,
            })
          ),
          repositoryKeys: Array.from(
            $$("#asu-repository-keys textarea"),
            (input) => input.value
          ),
        },
        device,
        version,
        service.rootfs_size_mb_max
      );
    } catch (error) {
      $("#asu-advanced").open = true;
      if (error.selector) {
        $$(error.selector)[error.index || 0]?.focus();
      }
      throw error;
    }
  };
}
