# Configuration

[简体中文](../zh-CN/configuration.md) · [Home](../../README.md)

Edit [`www/config.js`](../../www/config.js) before deploying. The site uses plain HTML/CSS/JavaScript; it has no frontend compilation step. Configuration is public browser content. Telegram credentials belong in GitHub Actions Secrets, never here.

## Distributions and build services

`asu_services` groups services by their `distribution` string. Each service must use the firmware metadata and downloads for its own distribution.

```javascript
asu_services: [
  {
    id: "openwrt",
    distribution: "OpenWrt",
    name: "OpenWrt (official)",
    url: "https://sysupgrade.openwrt.org",
    image_url: "https://downloads.openwrt.org",
    rootfs_size_mb_max: 1024,
  },
],
```

This is a fragment of the existing `config` object. The repository already configures OpenWrt official, ImmortalWrt official and ImmortalWrt KyaruCloud services; preserve the entries you need.

| Field | Meaning |
| --- | --- |
| `id` | Unique stable identifier used in `asu` selection links |
| `distribution` | Display/grouping name and first-boot draft/template key |
| `name` | Service label |
| `url` | ASU base URL |
| `image_url` | Matching firmware metadata/download base URL |
| `rootfs_size_mb_max` | Maximum size exposed in the form |
| `versions`, `default_version` | Optional overrides for the source's version index |
| `show_snapshots` | Include snapshots in the catalog |
| `info_url` | Optional device-information link override |
| `asu_extra_packages` | Override the global extra package list; `[]` adds none |

Service base URLs must be HTTP(S), without credentials, query strings or fragments. `asu_url` chooses the initial service unless a valid `asu` link parameter takes precedence. Switching distributions chooses that group's configured default service, or its first service.

The compatibility ID `immortalwrt` means KyaruCloud; `immortalwrt-official` means the official ImmortalWrt service. Do not change an ID merely to rename its label. Both currently use `https://downloads.immortalwrt.org` and an empty extra-package override. OpenWrt uses the global defaults `luci` and `luci-app-attendedsysupgrade`.

Without `asu_services`, the legacy single-service settings still work: `asu_url`, `image_url`, `versions`, `default_version` and optional `asu_rootfs_size_mb_max` (default 1024). A missing per-service distribution inherits the top-level `distribution`, or `OpenWrt`; explicitly set it for another system.

## Build defaults

| Setting | Default / behavior |
| --- | --- |
| `asu_rootfs_size_mb` | Optional initial size; empty uses the device default |
| `asu_repositories` | Map of feed names to repository URLs (opkg directories or APK indexes as required by the backend) |
| `asu_repositories_mode` | `append` by default; `replace` uses only supplied feeds |
| `asu_repository_keys` | List of complete feed signing public keys |
| `asu_extra_packages` | Extra packages, unless a service overrides them |

Feed URLs support `{openwrt_branch}`, `{openwrt_version}`, `{target}` and `{subtarget}`. For version `24.10.3` and target `ramips/mt7621`, these resolve to `24.10`, `24.10.3`, `ramips` and `mt7621`. Placeholder names also apply when using ImmortalWrt.

The form initializes from these values. Removing a configured row removes it from subsequent requests on that page; reloading restores deployment defaults. Feed mode is sent only when custom feeds are present. The selected backend decides which feeds and keys it accepts; allow lists and build availability can change independently of this site.

## Build-time and on-device feeds

The form sends `repositories`, `repositories_mode` and `repository_keys` to ASU. In the [examined ASU implementation](https://github.com/openwrt/asu/blob/77c5636045b0aed0762727363be105b2a5fa47fd/asu/build.py#L98), custom keys and repository files are injected into the **ImageBuilder directory**. This does not establish that they become the flashed device's package-manager configuration. A first-boot script that writes `/etc/apk/repositories.d/` and `/etc/apk/keys/` instead configures **later installations on the device**; it cannot supply packages for the earlier image build.

API support also does not mean arbitrary feeds are accepted. On 2026-11-03, OpenWrt official exposed all three fields but reported an empty `server.repository_allow_list`. The [examined allow-list implementation](https://github.com/openwrt/asu/blob/77c5636045b0aed0762727363be105b2a5fa47fd/asu/repositories.py#L6) permits no custom repository when that list is empty. ImmortalWrt official and KyaruCloud returned HTTP 403 to the metadata checks, so their current policies were not verified. These checks did not submit a firmware build.

Use an accepted feed to include a package in a build. If packages are to be installed after flashing, separately configure the device or verify that the backend's output already contains the required feed and key. The ImmortalWrt example intentionally does not embed Cooluc defaults: an APK `openwrt-25.12` feed is not a generic opkg/other-version feed, and redacted keys or hash placeholders cannot establish trust. Never disable signature checks to make such placeholders work.

## Device-specific packages

Copy [`www/device_packages.json.example`](../../www/device_packages.json.example) to `www/device_packages.json` and map device profile IDs to package lists. A missing or invalid file is ignored. The first comma/underscore separator is tried in both forms, so `tplink,archer-c7-v5` can match `tplink_archer-c7-v5`.

Packages are prefilled in this order: image defaults, profile `device_packages`, the service's effective `asu_extra_packages`, then this optional map. The map applies across distributions; use packages available in your intended systems. Track the file in Git if it must enter a release ZIP.

## First-boot templates

`uci_defaults_templates` maps distribution names to a single URL or an object with English and Simplified Chinese URLs:

```javascript
uci_defaults_templates: {
  OpenWrt: {
    en: "uci-defaults/setup.sh",
    "zh-cn": "uci-defaults/setup.zh-cn.sh",
  },
  ImmortalWrt: {
    en: "uci-defaults/immortalwrt.sh",
    "zh-cn": "uci-defaults/immortalwrt.zh-cn.sh",
  },
},
```

Use the exact distribution names from `asu_services`. Unconfigured distributions fall back to the template button's `data-link`. Templates load only when the user requests an example; they do not prefill or persist drafts. See [draft behavior](usage.md#first-boot-scripts).

Both `zh-cn` and `zh-tw` interfaces select the Chinese URL stored under `zh-cn`; all other languages select `en`. A missing Chinese URL falls back to `en`, then to `data-link` when no usable mapping exists. Single-URL configurations still work for every language. Changing the interface language does not translate or replace existing drafts. Keep localized templates equivalent in commands, sample assignments and log messages; translate comments only.

## Hosting firmware metadata yourself

Hosting this selector does not require mirroring firmware or running ASU. To use your own firmware source, expose metadata and images in the OpenWrt download layout and configure the matching `image_url`:

```text
<image_url>/.versions.json
<image_url>/releases/<version>/.overview.json
<image_url>/releases/<version>/targets/<target>/<subtarget>/profiles.json
<image_url>/releases/<version>/targets/<target>/<subtarget>/<image-file>
```

An optional `.versions.json` supplies `stable_version` and `versions_list`. Explicit `versions` and `default_version` settings can override it. The version's `.overview.json` summarizes device profiles; per-target `profiles.json` supplies image details. Generate JSON when building firmware by enabling **Global build settings → Create JSON info files per build image** in `make menuconfig`.

For an existing release directory, a POSIX shell with `find` and `jq` can generate its overview:

```sh
VERSION_PATH="releases/24.10.3"
find "$VERSION_PATH" -iname profiles.json -exec cat {} + |
  jq -s '{release: .[0].version_number, profiles: [.[] | .target as $target | .profiles | to_entries[] | {id: .key, titles: .value.titles, target: $target}]}' > "$VERSION_PATH/.overview.json"
```

Use a real version directory containing `profiles.json` files. A source on another origin must permit browser access with suitable CORS headers. Snapshot sources need the corresponding snapshot layout. Metadata format compatibility alone does not provide a working ImageBuilder/ASU backend.
