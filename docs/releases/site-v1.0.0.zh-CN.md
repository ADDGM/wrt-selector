Wrt Selector 首个个人版本：在同一页面选择 OpenWrt / ImmortalWrt、构建服务、软件包、软件源及首次启动脚本。项目由 ADDGM 基于 OpenWrt Firmware Selector 独立维护，不是 OpenWrt 或 ImmortalWrt 官方选择器。

[在线使用](https://addgm.github.io/wrt-selector/) · [中文文档](../../README.zh-CN.md) · [使用指南](../zh-CN/usage.md)

## 本版本重点

- **双系统、三套服务**：OpenWrt 官方、ImmortalWrt 官方和 ImmortalWrt KyaruCloud。目录与下载源跟随服务，请求、轮询及结果下载绑定提交时的服务与设备。
- **高级构建选项**：可编辑软件包、根文件系统大小、自定义软件源和签名公钥；支持追加/替换模式，提交前校验容量、名称、地址及必填内容。
- **首次启动脚本**：OpenWrt 和 ImmortalWrt 分别保存当前页面草稿，切换两个 ImmortalWrt 服务时共用草稿。模板追加、去重，并避免迟到请求覆盖新编辑。
- **中文示例注释**：简中和繁中共用中文注释，其他语言回退英文；切换语言保留草稿。ImmortalWrt 示例可选设置语言、已安装 Argon 主题、时区、网络与密码，校验输入和失败，默认不启用配置或第三方软件源。
- **界面与文档**：响应式布局、明暗样式、设备分享链接、独立 W 与路由节点图标，以及对应的中英文文档。
- **站点交付**：经过检查的网站 ZIP、SHA-256 与源码信息；develop 检查通过后部署 Pages，Pages/Release 各发送一条可选 Telegram 汇总。

## 运行环境

| 系统 | 默认构建服务 | 配置的根文件系统范围 |
| --- | --- | --- |
| OpenWrt | [官方 ASU](https://sysupgrade.openwrt.org/) | 1–1024 MiB |
| ImmortalWrt | [官方 ASU](https://sysupgrade.immortalwrt.org/) | 1–4096 MiB |
| ImmortalWrt | [KyaruCloud ASU](https://sysupgrade.kyarucloud.moe/) | 1–4096 MiB |

这些是部署配置，不是实时能力探测；留空采用设备默认值。两个 ImmortalWrt 服务使用 ImmortalWrt 元数据，不构建 OpenWrt 修订版本。

访问网站需要启用 JavaScript 的现代浏览器及对应服务的网络访问；不声明最低浏览器版本。部署只需静态 HTTP(S) 托管，无需 Node.js 或本地固件编译环境。开发使用 Node.js 22/24、Yarn Classic 1.x；打包使用 Python 3.11+ 与 Git。

## 使用与部署

1. 选择系统、服务、版本及准确设备，结合设备安装文档核对镜像类型。
2. 定制构建前检查软件包、软件源和首次启动脚本；构建由所选外部 ASU 服务执行。
3. 自建站点时将网站 ZIP 解压到 Web 根目录，使 index.html 位于根目录，按[配置指南](../zh-CN/configuration.md)修改 config.js。
4. 替换部署前保存自定义配置、模板和其他定制文件，更新后核对配置并刷新静态资源缓存。

Pages 跟随 develop 更新，需要复现版本时使用对应 Release ZIP。旧仓库 Pages 地址不会随更名重定向。历史 asu=immortalwrt 分享链接继续表示 KyaruCloud，官方服务使用 asu=immortalwrt-official。

## 已知限制

- 设备、版本、软件包及自定义软件源允许列表由后端决定，前端可填写不保证任意软件源被接受；构建阶段软件源不会自动成为设备运行时软件源。
- 根文件系统大小仅在目标支持时调整分区，不增加物理存储。
- 草稿只在当前页面内保留，刷新或离开后清空，分享链接不包含草稿。
- 模板需要按硬件和已安装组件检查，不自动安装 Argon 或第三方源。脚本内凭证会提交给构建服务并进入固件。
- 本版未完成真实路由器刷写、首次启动实机验收及全部服务/自定义源组合的端到端验证；自动化构建流程测试使用模拟目录与 ASU 响应，真实 Safari 未单独验收。
- Telegram API 接受不代表已读；取消通知为尽力执行，缺配置时跳过，通知失败不改变发布或部署结果。

具体检查结果以本次工作流为准，不把前一版本的测试数量或线上验收结果当作本次证据。

## 鸣谢

感谢直接上游 [OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org)，以及 [CzBiX/openwrt-firmware-selector](https://github.com/CzBiX/openwrt-firmware-selector)、[EkkoG/ofs-next](https://github.com/EkkoG/ofs-next)、[ImmortalWrt Firmware Selector](https://github.com/immortalwrt/firmware-selector-immortalwrt-org) 提供参考。感谢 OpenWrt、ImmortalWrt、KyaruCloud、ASU 和翻译贡献者。

项目保留上游 [CC0 1.0 Universal](../../LICENSE) 与历史。详见[鸣谢](../zh-CN/acknowledgements.md)、[开发指南](../zh-CN/development.md)、[部署与发版](../zh-CN/deployment.md)和[更新记录](../../CHANGELOG.zh-CN.md)。
