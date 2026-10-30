/* exported config */

var config = {
  // Show help text for images
  show_help: true,

  // Optional fixed versions for a deployment using a single ASU service
  // versions: ["23.05.4", "19.07.10"],

  // Pre-selected version (optional if provided by .versions.json)
  // default_version: "23.05.4",

  // Image download URL (e.g. "https://downloads.openwrt.org")
  image_url: "https://downloads.openwrt.org",

  // Insert snapshot versions (optional)
  //show_snapshots: true,

  // Info link URL (optional)
  info_url: "https://openwrt.org/start?do=search&id=toh&q={title} @toh",

  // Attended Sysupgrade Server support (optional)
  asu_url: "https://sysupgrade.openwrt.org",
  // Each build service must use metadata from its own firmware distribution.
  // Omit versions/default_version here to follow that source's version index.
  asu_services: [
    {
      id: "openwrt",
      distribution: "OpenWrt",
      name: "OpenWrt (official)",
      url: "https://sysupgrade.openwrt.org",
      image_url: "https://downloads.openwrt.org",
      rootfs_size_mb_max: 1024,
    },
    {
      id: "immortalwrt-official",
      distribution: "ImmortalWrt",
      name: "ImmortalWrt (official)",
      url: "https://sysupgrade.immortalwrt.org",
      image_url: "https://downloads.immortalwrt.org",
      rootfs_size_mb_max: 4096,
      show_snapshots: true,
      asu_extra_packages: [],
    },
    {
      // Keep this ID for existing KyaruCloud selection links.
      id: "immortalwrt",
      distribution: "ImmortalWrt",
      name: "ImmortalWrt · KyaruCloud",
      url: "https://sysupgrade.kyarucloud.moe",
      image_url: "https://downloads.immortalwrt.org",
      rootfs_size_mb_max: 4096,
      show_snapshots: true,
      asu_extra_packages: [],
    },
  ],
  asu_extra_packages: ["luci", "luci-app-attendedsysupgrade"],
  // Example scripts are selected by distribution, not by build server.
  uci_defaults_templates: {
    OpenWrt: "uci-defaults/setup.sh",
    ImmortalWrt: "uci-defaults/immortalwrt.sh",
  },
  // Initial root filesystem size in MiB (optional, within the service's limit)
  // asu_rootfs_size_mb: 256,
  // Initial custom feeds and public keys (optional, editable in the page)
  // asu_repositories: {
  //   my_feed: "https://example.com/packages/{openwrt_branch}/{target}/{subtarget}",
  // },
  // asu_repositories_mode: "append", // Default: "append"; or "replace"
  // asu_repository_keys: [
  //   "untrusted comment: my feed signing key\n<base64 public key>",
  // ],
};
