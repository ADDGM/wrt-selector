<img src="www/logo.svg" width="64" height="64" alt="" />

# Wrt Selector

简体中文 | [English](README.md)

**在同一个页面选择并定制 OpenWrt 与 ImmortalWrt 固件。**

Wrt Selector 由 ADDGM 基于
[OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org)
二次开发并独立维护，加入了系统与构建服务选择、可编辑的构建选项，以及按系统独立保存的首次启动脚本草稿。

[在线使用](https://addgm.github.io/wrt-selector/) ·
[版本发布](https://github.com/ADDGM/wrt-selector/releases) ·
[问题反馈](https://github.com/ADDGM/wrt-selector/issues)

## 主要功能

- **双系统、三套服务**：OpenWrt 官方、ImmortalWrt 官方、ImmortalWrt KyaruCloud，各自使用匹配的固件目录。
- **设备和版本选择**：搜索型号、查看镜像详情、访问对应下载源，并分享当前选择链接。
- **在线定制固件**：编辑软件包、根文件系统大小、软件源与签名公钥，再提交给 ASU。
- **首次启动脚本**：按系统插入示例，在当前页面内分别保留 OpenWrt 和 ImmortalWrt 草稿。
- **响应式界面**：适配桌面与移动端，提供明暗样式并保留上游多语言选择。
- **网站打包与部署**：经过检查的 ZIP 发布、GitHub Pages 部署，以及可选的 Telegram 工作流汇总。

网站将固件构建交给选定的外部 ASU 服务。
Wrt Selector Release ZIP 包含的是**网站本身**，不是路由器固件。
设备支持、软件源限制与构建可用性取决于对应服务。

## 快速开始

日常使用可直接访问在线网站。本地运行：

```sh
git clone https://github.com/ADDGM/wrt-selector.git
cd wrt-selector
python -m http.server 8000
```

打开 [http://localhost:8000/www/](http://localhost:8000/www/)。
仅运行网站需要 Python 3，无需前端编译。
部署配置位于 [www/config.js](www/config.js)。

## 文档导航

| 指南 | 内容 |
| --- | --- |
| [使用指南](docs/zh-CN/usage.md) | 下载、定制构建、脚本、分享和常见问题 |
| [配置指南](docs/zh-CN/configuration.md) | 服务、软件包、软件源、模板和自建元数据源 |
| [开发指南](docs/zh-CN/development.md) | 本地检查、浏览器测试、代码结构和上游集成 |
| [部署与发版](docs/zh-CN/deployment.md) | 静态托管、ZIP、GitHub Actions、Pages 和 Telegram |
| [更新记录](CHANGELOG.zh-CN.md) | 本项目版本摘要及上游历史入口 |
| [鸣谢](docs/zh-CN/acknowledgements.md) | 上游项目、实现参考及服务维护者 |

每篇文档顶部均提供对应的英文链接。
个人版本序列从 **`site-v1.0.0`** 开始；实际发布状态和下载以
[Releases 页面](https://github.com/ADDGM/wrt-selector/releases)为准。
个人 `site-v*` 版本与上游 `v*` 版本分别维护。

## 参与开发

代码检查使用 Node.js 22/24 和 Yarn Classic 1.x：

```sh
yarn install --frozen-lockfile
npm run check
python -B -m unittest discover -s tests/tooling -p "test_*.py" -v
```

`develop` 是本项目默认分支，`main` 镜像上游；
只集成已经合入上游 `main` 的更新。
参与前请阅读[开发指南](docs/zh-CN/development.md)。

## 上游与许可证

本项目是独立维护的二次开发版本，不是 OpenWrt 或 ImmortalWrt 官方选择器。
感谢 OpenWrt Firmware Selector 贡献者、ImmortalWrt 和各 ASU 服务维护者。
仓库保留上游翻译与历史；上游演示站不包含本分支的扩展功能。

项目沿用上游的 [CC0 1.0 Universal 许可证](LICENSE)。
具体参考项目及服务来源见[鸣谢](docs/zh-CN/acknowledgements.md)。
