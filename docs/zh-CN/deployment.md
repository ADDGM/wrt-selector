# 部署、发版与通知

[English](../en/deployment.md) · [返回首页](../../README.zh-CN.md)

## 静态托管

可以把 `www/` 中的内容部署到任意静态 Web 服务器，也可以将 Release ZIP 解压到站点根目录，确保 `index.html` 位于部署根目录。部署前按[配置指南](configuration.md)修改 `config.js`。使用自定义域名时，将 `CNAME` 纳入 `www/` 的 Git 跟踪文件。

**Release ZIP 是选择器网站包，不是路由器固件。** 固件下载和定制构建由选定的外部服务提供，部署本站不会提交 ASU 构建。

## 本地打包

准备 Python 3.11+ 与 Git，在仓库根目录运行：

```sh
python scripts/build_site.py
```

产物包括：

| 路径 | 内容 |
| --- | --- |
| `build/site/` | 展开的可部署网站 |
| `build/firmware-selector-<版本>.zip` | 网站 ZIP |
| `build/firmware-selector-<版本>.zip.sha256` | SHA256 校验文件 |
| `build/build-info.json` | 版本、源码 SHA、源码日期和未提交标记 |

Wrt Selector 改名后沿用通用的 `firmware-selector-` 产物前缀。版本默认取个人 `site-v*` 标签描述，没有个人标签时回退到短提交 SHA。`--version site-v1.0.0` 只指定预览版本，不会创建标签或发布版本。

ZIP 只包含 Git 跟踪的 `www/` 文件、许可证和构建信息；保留原有配置，只在产物中替换版本占位符。已跟踪的本地网站改动会进入预览包，并设置 `source_dirty`；正式版本要求标签对应的网站源码干净。未跟踪的部署文件需先纳入 Git。相同源码、版本和构建环境生成相同 ZIP。重复构建会替换工具管理的 `build/site/`，不要在其中保存手工修改，临时预览使用完成后应清理。

## 工作流分工

| 工作流 | 触发条件 | 结果 |
| --- | --- | --- |
| `project-pages.yml` | 推送 `develop`，或在 `develop` 手动运行 | 核验源码、调用质量/测试、部署本次产物、通知 |
| `project-ci.yml` | 目标为 `develop` 的 PR、手动或复用调用 | Node 22/24、Python 工具、HTML、Firefox 测试，通过后生成 `website-package` |
| `project-quality.yml` | 目标为 `develop` 的 PR、手动或复用调用 | 提交规范、actionlint、Semgrep |
| `project-release.yml` | 推送 `site-v*` 标签，或手动指定已有标签 | 解析源码、调用质量/测试、创建 Release、通知 |
| `project-notify.yml` | 仅由 Pages 或 Release 复用调用 | 尝试发送一条汇总结果 |

`develop` 推送由 Pages 统一组织检查，CI 和质量不重复监听推送。PR 只检查，不部署。HTML 检查不依赖外部网站可用性；Semgrep 使用远端规则，发现问题或扫描错误都会使质量检查失败。SARIF 作为产物保存，不要求 Code Scanning 写权限。依赖采用 `yarn install --frozen-lockfile` 安装。

上游的 `test.yml`、`static-main.yml`、`static-stable.yml` 保留原文件，必须在自己仓库的 Actions 设置中保持**禁用**。同步时注意上游是否新增工作流。本项目采用 `project-*` 文件名，不需要 `RSYNC_USER` 或 `RSYNC_PASSWORD`。

## GitHub Pages

将仓库默认分支设为 `develop`，在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**，并将 `github-pages` 环境的部署规则限制为 `develop`。

推送 `develop` 后，工作流检查并部署同一次运行、同一源码 SHA 的 ZIP。检查失败保留原部署。手动部署也必须选择 `develop`；`main`、其他分支、标签和 PR 不部署。同分支运行串行，正在执行的运行继续，新的排队运行可能替换较旧的等待运行。

本项目目标仓库为 [ADDGM/wrt-selector](https://github.com/ADDGM/wrt-selector)，默认 Pages 地址为 [https://addgm.github.io/wrt-selector/](https://addgm.github.io/wrt-selector/)。仓库改名时同步更新 About 主页和本地 `origin`，随后重新部署并验证新地址。GitHub 会重定向仓库链接，但**不会重定向旧项目的 Pages 地址**。`upstream` 继续指向 OpenWrt，规则见 [GitHub 改名文档](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository)。

## 正式发版

个人版本使用 `site-vX.Y.Z`、`site-vX.Y.Z-beta.N` 或 `site-vX.Y.Z-rc.N`。上游 `v*` 标签不用于个人发布。标签必须包含本项目工作流和脚本，指向已合入 `develop` 的个人源码，不能指向纯上游提交。只推送本次需要发布的标签，不要批量推送上游标签。

推送有效标签会触发发布，手动入口接受已存在标签。通过测试和质量检查后发布 ZIP、校验文件及构建信息。Beta/RC 标记为预发布，不作为 latest。已有 Release 不覆盖；运行中断后先检查发布状态再决定如何重试，不要移动已发布标签。

工具按类型整理从上一个可达 `site-v` 标签以来的个人提交，并排除固定的上游快照。自动生成的提交明细目前保留中文提交标题；面向使用者的中英文版本摘要同步维护在[中文更新记录](../../CHANGELOG.zh-CN.md)和 [English changelog](../../CHANGELOG.md)。写权限仅授予使用 `GITHUB_TOKEN` 的发布任务。

## Telegram

在 **Settings → Secrets and variables → Actions → Secrets** 中配置：

| Secret | 内容 |
| --- | --- |
| `TELEGRAM_TOKEN` | 机器人令牌 |
| `TELEGRAM_TO` | 目标聊天 ID 或频道用户名 |

机器人必须有权向目标发送消息。Pages 汇总源码核验、质量检查、测试打包和部署；Release 汇总标签/源码核验、质量检查、测试打包和发布。消息展示成功、失败、取消或未执行状态、源码 SHA 和 Actions 链接；成功时附带站点或 Release 链接。独立检查和 PR 不发通知。

缺少凭证时明确记录跳过。发送错误会记录原因，但不改变原工作流结果。客户端使用纯文本、20 秒超时且不自动重试，避免超时后重复发送；不输出令牌、聊天 ID 或原始错误响应。只有 Telegram 返回 `ok: true` 才表示 API 已接受，不代表接收者已读。

取消通知是尽力执行，平台强制终止可能阻止发送；手动重跑可能再次通知。Secret 名称存在不代表凭证或聊天权限已验证。本地测试使用模拟，不联系 Telegram：

```sh
python -B -m unittest discover -s tests/tooling -p "test_notify_telegram.py" -v
```
