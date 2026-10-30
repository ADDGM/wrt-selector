export function normalizeAsuUrl(value) {
  const raw = String(value || "").trim();
  const url = new URL(raw);
  if (
    !/^https?:\/\//i.test(raw) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    /\s/.test(raw)
  ) {
    throw new Error("Invalid ASU service URL");
  }
  return url.href.replace(/\/+$/, "");
}

export function getAsuServices(config) {
  const entries = config.asu_services?.length
    ? config.asu_services
    : [
        {
          id: "default",
          name: config.asu_url || "OpenWrt",
          url: config.asu_url,
          image_url: config.image_url,
          versions: config.versions,
          default_version: config.default_version,
          rootfs_size_mb_max: config.asu_rootfs_size_mb_max,
        },
      ];
  const ids = new Set();
  return entries.map((entry) => {
    if (!/^[\w.-]+$/.test(entry.id) || ids.has(entry.id)) {
      throw new Error(
        "ASU service IDs must be unique and contain only letters, numbers, dots, underscores or hyphens"
      );
    }
    ids.add(entry.id);
    const maximum = entry.rootfs_size_mb_max ?? 1024;
    if (!Number.isSafeInteger(maximum) || maximum < 1) {
      throw new Error("Invalid ASU root filesystem size limit");
    }
    const distribution = entry.distribution ?? config.distribution ?? "OpenWrt";
    if (typeof distribution !== "string" || !distribution.trim()) {
      throw new Error("Invalid firmware distribution name");
    }
    const extraPackages =
      entry.asu_extra_packages ?? config.asu_extra_packages ?? [];
    if (
      !Array.isArray(extraPackages) ||
      extraPackages.some((pkg) => typeof pkg !== "string")
    ) {
      throw new Error("ASU extra packages must be a list of package names");
    }
    return {
      ...entry,
      distribution: distribution.trim(),
      name: entry.name || entry.id,
      url: entry.url ? normalizeAsuUrl(entry.url) : "",
      image_url: entry.image_url || config.image_url,
      rootfs_size_mb_max: maximum,
      asu_extra_packages: [...extraPackages],
    };
  });
}

export function selectAsuService(services, config, requestedId, distribution) {
  const candidates = distribution
    ? services.filter((service) => service.distribution === distribution)
    : services;
  return (
    candidates.find((service) => service.id === requestedId) ||
    candidates.find(
      (service) => service.url === (config.asu_url || "").replace(/\/+$/, "")
    ) ||
    candidates[0]
  );
}
