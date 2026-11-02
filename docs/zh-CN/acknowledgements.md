# 鸣谢

[English](../en/acknowledgements.md) · [返回首页](../../README.zh-CN.md)

Wrt Selector 建立在开源作者、翻译贡献者和服务维护者的工作之上。感谢以下项目提供的代码、实现参考和构建基础设施，让本项目能够持续完善。

## 上游与参考项目

| 项目 | 本项目的继承或参考方式 |
| --- | --- |
| [OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org) | 本仓库的直接上游，提供原始静态选择器、设备目录与下载流程、ASU 集成、翻译和开发历史。本分支继续跟随已经合入上游 `main` 的更新。 |
| [CzBiX/openwrt-firmware-selector](https://github.com/CzBiX/openwrt-firmware-selector) | 选择器实现和可配置 ASU 服务入口的参考；适配本项目构建服务选项时核对了其服务配置。 |
| [EkkoG/ofs-next](https://github.com/EkkoG/ofs-next) | 根文件系统大小、软件源签名公钥输入等高级构建选项的参考，同时核对了其 KyaruCloud 服务配置；本项目的容量限制按所选后端分别校验。 |
| [ImmortalWrt Firmware Selector](https://github.com/immortalwrt/firmware-selector-immortalwrt-org) | 双系统适配时的 ImmortalWrt 服务配置参考。分别核对其仓库和线上默认配置后，本项目将官方服务与 KyaruCloud 服务明确列为两个入口。 |

## 固件与服务维护者

[OpenWrt ASU](https://github.com/openwrt/asu) 提供 Attended SysUpgrade 构建服务器项目和 API 模型，用于镜像请求、进度轮询及定制构建结果。Wrt Selector 作为已配置 ASU 服务的客户端使用这些能力。

感谢 [OpenWrt](https://openwrt.org/) 和 [ImmortalWrt](https://immortalwrt.org/) 社区提供固件、设备元数据和软件包基础设施，也感谢默认配置所使用的服务维护者：

- [OpenWrt 官方 ASU](https://sysupgrade.openwrt.org/)
- [ImmortalWrt 官方 ASU](https://sysupgrade.immortalwrt.org/)
- [KyaruCloud ASU](https://sysupgrade.kyarucloud.moe/)

这些链接说明默认配置使用的服务来源，不代表所有服务都由本仓库作者维护。

## 来源与贡献

项目保留继承的 [CC0 1.0 Universal 许可证](../../LICENSE)、上游 Git 历史和[上游发布记录](../../CHANGELOG.md#upstream-history)。复用外部项目代码时，请遵循相应项目自己的许可证。鸣谢与源码、许可证中的归属说明共同保留。

同时感谢原始翻译，以及本分支代码、文档和测试的贡献者。后续增加参考项目时，请记录仓库链接和具体借鉴的想法或实现，并同步两种语言。
