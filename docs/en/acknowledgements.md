# Acknowledgements

[简体中文](../zh-CN/acknowledgements.md) · [Home](../../README.md)

Wrt Selector builds on the work of open-source authors, translators and service operators. Thank you to the projects below for the code, reference implementations and build infrastructure that make this project possible.

## Upstream and references

| Project | How it relates to Wrt Selector |
| --- | --- |
| [OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org) | The direct upstream of this repository. It provides the original static selector, device catalog and download flow, ASU integration, translations and historical development. This fork continues to follow changes merged into upstream `main`. |
| [CzBiX/openwrt-firmware-selector](https://github.com/CzBiX/openwrt-firmware-selector) | A reference for selector implementation and configurable ASU service selection. Its service configuration was examined when adapting this project's build-service options. |
| [EkkoG/ofs-next](https://github.com/EkkoG/ofs-next) | A reference for advanced build controls, including root filesystem size and feed signing public-key input. Its KyaruCloud service configuration also informed the service comparison; this project's limits are checked against the selected backend. |
| [ImmortalWrt Firmware Selector](https://github.com/immortalwrt/firmware-selector-immortalwrt-org) | A reference for ImmortalWrt service configuration during the multi-distribution adaptation. Its repository and deployed defaults were checked separately, helping this project present the official and KyaruCloud services explicitly. |

## Firmware and service operators

[OpenWrt ASU](https://github.com/openwrt/asu) provides the Attended SysUpgrade build-server project and API model for image requests, progress polling and custom-build results. Wrt Selector is a client of configured ASU services.

Thanks to the [OpenWrt](https://openwrt.org/) and [ImmortalWrt](https://immortalwrt.org/) communities for firmware, device metadata and package infrastructure, and to the operators of the configured services:

- [OpenWrt official ASU](https://sysupgrade.openwrt.org/)
- [ImmortalWrt official ASU](https://sysupgrade.immortalwrt.org/)
- [KyaruCloud ASU](https://sysupgrade.kyarucloud.moe/)

The service links identify the infrastructure used by the default configuration; they do not imply that all services are maintained by this repository's authors.

## Attribution and contributions

The inherited [CC0 1.0 Universal license](../../LICENSE), upstream Git history and [upstream release notes](../../CHANGELOG.md#upstream-history) remain available. Refer to each external project's own license when reusing its code. Acknowledgements complement source and license attribution.

Contributors to the original translations and to this fork's code, documentation and testing are also gratefully acknowledged. When adding another reference, record both its repository link and the specific idea or implementation used, and update both language versions.
