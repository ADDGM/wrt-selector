# Wrt Selector 更新记录

[English](CHANGELOG.md) · [返回首页](README.zh-CN.md)

个人版本使用 `site-v*`。上游 OpenWrt 的 `v*` 历史属于另一条版本序列，不代表 Wrt Selector 已经发布的个人版本。

## site-v1.0.1 — 版本摘要

本维护版本完善发布交付流程，并同步上游翻译更新。实际发布状态和可下载产物以 [GitHub Releases](https://github.com/ADDGM/wrt-selector/releases) 为准。

- 将审定的版本内容与经过核验的 Git、构建信息组合，自动生成完整中英文发布说明。
- 按 GitHub 实际渲染结果校验发布链接，同一份 release-notes.md 同时作为 Release 正文和下载文件。
- 提供本地发布预览，在发布前拒绝不完整内容、无效链接或不一致的产物信息。
- 同步 OpenWrt 官方上游的丹麦语、罗马尼亚语翻译；从 site-v1.0.0 升级无需配置格式迁移。

## site-v1.0.0 — 版本摘要

以下是首个个人版本的变更摘要。实际发布状态和可下载产物以 [GitHub Releases](https://github.com/ADDGM/wrt-selector/releases) 为准。

- 支持 OpenWrt、ImmortalWrt，以及官方服务和 ImmortalWrt KyaruCloud 服务选择。
- 支持软件包、根文件系统大小、软件源和签名公钥定制。
- 在当前页面按系统分别保留首次启动脚本草稿。
- 简体中文、繁体中文界面共用中文示例注释，其他语言回退英文；切换语言保留已有草稿。
- 完善 ImmortalWrt 示例，提供可选语言、主题和时区设置，校验网络配置并明确返回失败；第三方软件源按实际部署另行配置。
- 更新响应式界面，保持构建请求绑定服务和设备，并兼容选择分享链接。
- 增加经过检查的网站 ZIP、仅 develop 部署的 Pages，以及 Pages/Release Telegram 汇总。
- 采用 Wrt Selector 名称及独立的 W 与路由节点图标，提供对应的英文和简体中文文档。

## 上游历史

原有 OpenWrt 发布记录以原文保存在 [English changelog 的上游历史部分](CHANGELOG.md#upstream-history)，用于追溯来源；其中部分描述对应二次开发之前的行为。
