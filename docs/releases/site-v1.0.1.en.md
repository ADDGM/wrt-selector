Wrt Selector site-v1.0.1 is a maintenance version focused on complete bilingual release-note generation, link validation and upstream Danish/Romanian translation updates. The OpenWrt/ImmortalWrt selection, build customization and first-boot script features from site-v1.0.0 remain available. ADDGM maintains this derivative independently; it is not an official selector.

[Use online](https://addgm.github.io/wrt-selector/) · [English documentation](../../README.md) · [Usage guide](../en/usage.md)

## Highlights

- **Complete bilingual release notes**: each version stores its overview, highlights, requirements, deployment instructions, limitations and acknowledgements. The workflow adds commit details, version comparisons and verified artifact metadata, so the body does not need a separate post-release expansion.
- **Link and artifact validation**: document links point to the matching version, and language navigation is checked against GitHub-rendered Markdown. Missing content, invalid links, mismatched ZIP checksums or inconsistent build metadata stop publication.
- **Previewable, downloadable notes**: maintainers can preview notes before creating a tag. Releases include a release-notes.md download containing the same complete Markdown used for the release page.
- **Upstream translations**: update Danish build-status messages and Romanian descriptions from the official OpenWrt upstream.

## Requirements

Use a modern JavaScript-enabled browser with network access to the selected build service; no minimum browser version is declared. Hosting requires static HTTP(S), without Node.js or a local firmware toolchain.

The default configuration provides OpenWrt official, ImmortalWrt official and ImmortalWrt KyaruCloud services. Configured root filesystem ranges are 1–1024 MiB for OpenWrt and 1–4096 MiB for ImmortalWrt. Leave size empty for the device default; these limits are not live backend capability detection.

Development uses Node.js 22/24 and Yarn Classic 1.x. Packaging and note generation use Python 3.11+ and Git; actual Markdown rendering checks require an authenticated GitHub CLI. Normal website use and hosting do not require these development tools.

## Usage and deployment

1. Select the distribution, service, version and exact device online; check image types against device installation instructions before requesting a custom build.
2. For self-hosting, verify the website ZIP on this page with SHA-256 and extract it into the web root, with index.html at its root.
3. Upgrading from site-v1.0.0 needs no configuration-format migration. Preserve custom config.js, first-boot templates and other modifications before replacing files; review configuration and refresh cached assets afterward.
4. Before publishing the next version, maintainers review both language files and follow the [deployment and release guide](../en/deployment.md) to preview them. The workflow generates the complete body and uploads the notes file.

Pages tracks develop. Use the corresponding Release ZIP to deploy a fixed version. The website ZIP does not contain router firmware; see the [configuration guide](../en/configuration.md) for configuration and service selection.

## Known limitations

- Devices, versions, packages and custom-feed allow lists depend on the backend. Editable fields do not guarantee feed acceptance; root filesystem sizing depends on target support and does not increase physical storage.
- First-boot script drafts exist only in the current page, disappear on refresh/navigation and are not included in shared links. Script credentials are sent to the build service and included in firmware.
- This maintenance version adds no hardware-flashing or real first-boot verification. Automated build-flow tests use mocked catalogue and ASU responses and do not cover every device, service or custom-feed combination.
- Release-link checks cover versioned files, planned upload assets and rendered anchors. Third-party website availability is not a publication gate.
- Telegram API acceptance does not mean a message was read. Missing configuration skips notification, and notification failures do not change the release or deployment result.

Use this workflow's results as verification evidence. Note-generation time is not the actual publication time.

## Acknowledgements

Thanks to the direct upstream [OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org) and its translation contributors. The project retains its references and acknowledgements for [CzBiX/openwrt-firmware-selector](https://github.com/CzBiX/openwrt-firmware-selector), [EkkoG/ofs-next](https://github.com/EkkoG/ofs-next) and [ImmortalWrt Firmware Selector](https://github.com/immortalwrt/firmware-selector-immortalwrt-org), and thanks the OpenWrt, ImmortalWrt, KyaruCloud and ASU service maintainers.

The inherited [CC0 1.0 Universal license](../../LICENSE) and history are retained. See [acknowledgements](../en/acknowledgements.md) and the [changelog](../../CHANGELOG.md).
