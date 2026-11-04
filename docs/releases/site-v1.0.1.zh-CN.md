Wrt Selector site-v1.0.1 是维护版本，重点完善双语发布说明的自动生成与链接校验，并同步上游丹麦语、罗马尼亚语文案。现有 OpenWrt / ImmortalWrt 选型、构建定制和首次启动脚本功能延续 site-v1.0.0；项目仍由 ADDGM 独立维护，不是官方选择器。

[在线使用](https://addgm.github.io/wrt-selector/) · [中文文档](../../README.zh-CN.md) · [使用指南](../zh-CN/usage.md)

## 本版本重点

- **完整双语发布说明**：版本简介、亮点、运行环境、部署说明、限制与鸣谢随版本保存；工作流自动补齐提交明细、版本对比及真实产物信息，无需在发布后另行补写正文。
- **链接与产物校验**：文档链接固定到对应版本，语言跳转按 GitHub 实际渲染结果校验；缺少内容、无效链接、ZIP 校验值或构建信息不一致时阻止发布。
- **可预览、可下载的说明**：维护者可在创建标签前生成本地预览；发布时增加 release-notes.md 下载文件，与发布页使用同一份完整正文。
- **上游翻译更新**：同步 OpenWrt 官方上游的丹麦语构建状态文案和罗马尼亚语说明调整。

## 运行环境

访问网站需要启用 JavaScript 的现代浏览器及对应构建服务的网络访问；不声明最低浏览器版本。部署使用静态 HTTP(S) 托管，无需 Node.js 或本地固件编译环境。

默认提供 OpenWrt 官方、ImmortalWrt 官方和 ImmortalWrt KyaruCloud 三套服务。配置的根文件系统范围为 OpenWrt 1–1024 MiB、ImmortalWrt 1–4096 MiB，留空采用设备默认值；这些限制不是后端能力的实时探测。

开发使用 Node.js 22/24、Yarn Classic 1.x；打包与说明生成使用 Python 3.11+、Git，真实 Markdown 渲染校验使用已登录的 GitHub CLI。普通网站访问与部署不需要这些开发工具。

## 使用与部署

1. 在线使用时选择系统、服务、版本及准确设备，结合设备安装说明核对镜像类型，再提交定制构建。
2. 自建站点使用本页的网站 ZIP，核对 SHA-256 后解压到 Web 根目录，使 index.html 位于根目录。
3. 从 site-v1.0.0 升级无需配置格式迁移；覆盖前保存自定义 config.js、首次启动模板和其他定制文件，更新后核对配置并刷新静态资源缓存。
4. 维护者发布下一版本前审定两种语言的版本内容，按[部署与发版指南](../zh-CN/deployment.md)完成预览；工作流负责生成完整正文和上传说明文件。

Pages 跟随 develop 更新，固定版本部署使用对应 Release ZIP。网站 ZIP 不包含路由器固件；配置和服务选择详见[配置指南](../zh-CN/configuration.md)。

## 已知限制

- 设备、版本、软件包及自定义软件源允许列表由后端决定，前端可填写不保证任意软件源被接受；根文件系统调整依赖目标支持，也不会增加物理存储。
- 首次启动脚本草稿只保存在当前页面，刷新或离开后清空，分享链接不包含草稿；脚本内凭证会提交给构建服务并进入固件。
- 本维护版本没有新增真实路由器刷写或首次启动实机验证。自动化构建流程测试使用模拟目录与 ASU 响应，未覆盖全部硬件、服务和自定义软件源组合。
- 发布链接检查覆盖对应版本的文件、计划上传的资产及实际渲染锚点；第三方网站的实时可用性不作为发布门禁。
- Telegram API 接受不代表消息已读；缺少配置时跳过通知，通知失败不改变发布或部署结果。

检查结果以本次工作流为准，说明生成时间不代表实际发布时间。

## 鸣谢

感谢直接上游 [OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org) 及翻译贡献者。项目继续保留来自 [CzBiX/openwrt-firmware-selector](https://github.com/CzBiX/openwrt-firmware-selector)、[EkkoG/ofs-next](https://github.com/EkkoG/ofs-next)、[ImmortalWrt Firmware Selector](https://github.com/immortalwrt/firmware-selector-immortalwrt-org) 的参考与致谢，并感谢 OpenWrt、ImmortalWrt、KyaruCloud 和 ASU 服务维护者。

项目保留上游 [CC0 1.0 Universal](../../LICENSE) 与历史。详见[鸣谢](../zh-CN/acknowledgements.md)和[更新记录](../../CHANGELOG.zh-CN.md)。
