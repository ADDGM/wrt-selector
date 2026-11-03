The first personal Wrt Selector release brings OpenWrt and ImmortalWrt, build services, packages, repositories and first-boot scripts into one interface. ADDGM maintains this derivative of OpenWrt Firmware Selector independently; it is not an official OpenWrt or ImmortalWrt selector.

[Use online](https://addgm.github.io/wrt-selector/) · [English documentation](../../README.md) · [Usage guide](../en/usage.md)

## Highlights

- **Two distributions, three services**: OpenWrt official, ImmortalWrt official and ImmortalWrt KyaruCloud. Catalogues and downloads follow the service; submission, polling and results remain tied to the submitted device and service.
- **Advanced options**: editable packages, root filesystem size, custom repositories and signing public keys, with append/replace modes and input validation.
- **First-boot scripts**: separate in-page drafts for OpenWrt and ImmortalWrt, shared drafts across ImmortalWrt services, appending and duplicate prevention without late requests overwriting new edits.
- **Localized examples**: Simplified/Traditional Chinese share Chinese comments; other languages use English. Language changes preserve drafts. The ImmortalWrt example validates optional language, installed Argon, timezone, network and password settings without enabling configuration or third-party feeds by default.
- **Interface and documentation**: responsive layouts, light/dark styles, device-selection links, the independent W/network-node identity and paired English/Chinese guides.
- **Delivery**: checked website ZIPs, SHA-256 and source metadata; checked develop pushes deploy Pages, with one optional Telegram summary per Pages/Release workflow.

## Requirements

| Distribution | Configured build service | Configured root filesystem range |
| --- | --- | --- |
| OpenWrt | [Official ASU](https://sysupgrade.openwrt.org/) | 1–1024 MiB |
| ImmortalWrt | [Official ASU](https://sysupgrade.immortalwrt.org/) | 1–4096 MiB |
| ImmortalWrt | [KyaruCloud ASU](https://sysupgrade.kyarucloud.moe/) | 1–4096 MiB |

These are deployment limits, not live capability detection. Leave size empty for the device default. Both ImmortalWrt services use ImmortalWrt metadata, not OpenWrt revisions.

Use a modern JavaScript-enabled browser with network access to the selected services; no minimum browser version is declared. Hosting only requires static HTTP(S), without Node.js or a local firmware toolchain. Development uses Node.js 22/24 and Yarn Classic 1.x; packaging uses Python 3.11+ and Git.

## Usage and deployment

1. Select the distribution, service, version and exact device; check image types against device installation instructions.
2. Review packages, feeds and first-boot scripts before requesting a build from the selected external ASU service.
3. To self-host, extract the website ZIP into the web root with index.html at its root, then edit config.js using the [configuration guide](../en/configuration.md).
4. Preserve custom configuration, templates and other modifications before replacing a deployment; review configuration and refresh cached assets afterward.

Pages tracks develop and can advance beyond a release. Use the corresponding Release ZIP for a fixed version. Old Pages URLs do not redirect after a repository rename. Existing asu=immortalwrt links still select KyaruCloud; the official service uses asu=immortalwrt-official.

## Known limitations

- Devices, versions, packages and repository allow lists depend on the backend. Editable fields do not guarantee feed acceptance; build-time feeds do not automatically configure device runtime feeds.
- Root filesystem sizing changes partitions only where supported and does not increase physical storage.
- Drafts disappear on refresh/navigation and are not included in shared links.
- Review templates against hardware and installed components. They do not install Argon or third-party feeds. Script credentials are sent to the build service and included in firmware.
- Hardware flashing, real first-boot execution and every service/custom-feed combination have not been verified. Automated build-flow tests mock catalogue and ASU responses; real Safari was not separately validated.
- Telegram API acceptance does not mean a message was read. Cancellation notification is best effort; missing configuration skips delivery and notification failures do not change the deployment/release result.

Use this workflow's results as evidence; previous versions' test counts and deployment checks are not evidence for this run.

## Acknowledgements

Thanks to the direct upstream [OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org), references [CzBiX/openwrt-firmware-selector](https://github.com/CzBiX/openwrt-firmware-selector), [EkkoG/ofs-next](https://github.com/EkkoG/ofs-next), [ImmortalWrt Firmware Selector](https://github.com/immortalwrt/firmware-selector-immortalwrt-org), and the OpenWrt, ImmortalWrt, KyaruCloud, ASU and translation contributors.

The inherited [CC0 1.0 Universal license](../../LICENSE) and history are retained. See [acknowledgements](../en/acknowledgements.md), [development](../en/development.md), [deployment](../en/deployment.md) and the [changelog](../../CHANGELOG.md).
