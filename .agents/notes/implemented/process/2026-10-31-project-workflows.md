# Agent Note: 统一站点构建、中文提交与 GitHub 发布工作流

Status: implemented

## Problem

二次开发仓库需要能直接部署的网站包和可追溯的发布。原工作流在 main 推送时自动部署 Pages，在 stable 推送时把文件传到固定的 OpenWrt 官方服务器，不符合当前仓库的发布目标。两个部署步骤浅克隆后直接调用 `git describe --tags`，无标签时会失败；stable 还把口令写入 `.rsync_password` 却从 `.rsync_pass` 读取。部署步骤各自用 sed 改配置，容易与双系统、多构建服务设置分离。

用户要求 Git 信息保留 Conventional Commits 前缀并使用中文标题，也选择站点 ZIP/GitHub Release 与手动 Pages。桌面的 PHP/WordPress 工作流具有检查、质量、发布三类分工，但运行环境与本项目的静态 HTML/CSS/JavaScript 不同。

Pages 的成功运行 43187627434 暴露了旧版 Action 的 Node20 弃用警告；固定 SHA 本身不会自动更新运行时，需要维护个人发布链而不是依赖平台强制切换。

## Decision

项目采用四份主工作流，并由[Telegram 通知](2026-11-03-telegram-notifications.md)提供共用通知入口：测试和质量检查可被 Release 与 Pages 复用，构建只有 `scripts/build_site.py` 一个入口。个人版本通过标签发布 Release；原先的手动 Pages 选择由[Pages 自动部署](2026-11-03-pages-auto-deploy.md)部分取代，改为 develop 推送后检查并部署，保留手动入口。初始实现覆盖 main/develop 并使用 v 标签；用户明确 main 是纯上游镜像后，个人文件名和标签命名由[上游工作流隔离](2026-11-03-upstream-workflow-isolation.md)接管。旧官方 rsync 文件保留为禁用的上游内容，个人流程不依赖其目标或口令。

测试覆盖 Node 22/24 的原有检查入口、Python 工具、HTML 站内链接与 Firefox 页面回归。HTML 检查关闭外链检查，避免上游网站临时故障阻断静态包发布。Firefox 沿用真实页面与模拟元数据/ASU 的已有用例，只安装 Firefox，保存 JUnit 和控制台日志。用例自行创建 context，因此不声称 pytest 的自动 tracing 能捕获这些 context。

HTML 标题按页面 h1、构建及下载区 h2、自定义选项 h3 连续分级；CSS 与下载标题的脚本选择器随标签同步。固件源与构建服务链接沿用页面已有的 `href="#"` 占位方式，脚本在显示字段前写入真实地址。HTML 检查保留缺失 href 检测，不为动态内容放宽全站规则；真实链接与服务切换由 Firefox 回归检查。

中文提交检查保留 `.github/commit-policy-baseline.txt` 的初始上游边界，未来同步的上游范围由[上游工作流隔离](2026-11-03-upstream-workflow-isolation.md)接管。标题采用 `type(scope): 中文说明`，scope 可省略，最长 72 字符；已知依赖机器人与真实 merge commit 豁免。PR 使用 base/head，push 使用 before/head，首次推送或本地默认检查使用完整二次开发范围。旧的上游英文历史保持原样。

质量工作流使用 actionlint 与 Semgrep；安全发现及扫描错误都阻断发布。初始决定把个人工作流的外部 Action 固定到核实过的完整 SHA；此引用策略现由[官方 Action 主版本标签](2026-11-14-action-major-tags.md)部分取代，下文保留当时的核验依据。actionlint 下载仍验证 SHA256，Semgrep 仍固定镜像版本与摘要。SARIF 作为普通 Actions 产物保存，不要求 fork PR 提供 `security-events: write`。规则集仍来自 Semgrep Registry，因此规则变化和服务故障需要维护者排查。内嵌 Bash 的中文文案通过环境变量提供，避免扫描器解析 Unicode 字符串时出现内部错误。

### Action 运行时与产物完整性

2026-11-12 的运行时维护采用以下决定：个人 Pages 与 Release 使用已核验的 Node24 Action，继续固定完整提交 SHA，而不是漂移的主版本标签。该引用策略已由[官方 Action 主版本标签](2026-11-14-action-major-tags.md)部分取代；下表保留当时核验的版本和提交，运行时升级及下文的产物完整性约束仍有效：

| Action | 版本 | 固定提交 | 使用位置 |
| --- | --- | --- | --- |
| actions/download-artifact | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` | Pages、Release |
| actions/upload-pages-artifact | v5.0.0 | `fc324d3547104276b827a68afc52ff2a11cc49c9` | Pages |
| actions/deploy-pages | v5.0.1 | `368f82528645a54fb793d4d04e342629a3f51346` | Pages |

运行时依据为各固定提交的官方定义：[download-artifact](https://github.com/actions/download-artifact/blob/9000827ccba6bdab643e8b6fd33ac0654aef8333/action.yml)、[upload-pages-artifact](https://github.com/actions/upload-pages-artifact/blob/fc324d3547104276b827a68afc52ff2a11cc49c9/action.yml)、[deploy-pages](https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/action.yml)。其中 upload-pages-artifact 是 composite，内部固定 upload-artifact v7.0.0 的 Node24 实现；不能只检查外层 Action 是否声明 Node 运行时。

下载仍按 `website-package` 名称分别落到 `package/` 和 `build/`，沿用上传端默认 ZIP 包装，不设置 `skip-decompress`。download-artifact v8 的 `digest-mismatch` 默认 `error`，摘要不符必须阻断部署或发布，不降级为警告；站点 ZIP 自身的 SHA256 校验同时保留。Pages 上传保留隐藏文件默认排除，不开启 `include-hidden-files`；`github-pages` 产物名、`page_url` 输出、最小权限、触发条件、串行部署与通知逻辑均不改变。

Node24 Action 要求 runner 至少 2.327.1；项目继续使用已有 GitHub 托管 `ubuntu-latest`，不添加强制运行时环境变量，也不因本次维护改 runner 标签。上游保留工作流、中文标题范围与业务代码不属于本次升级范围。

### 构建与发布契约

打包只读取 Git 索引中的常规 `www/` 文件，不收集未跟踪的本地文件，拒绝符号链接、未合并文件和越界路径；额外带入许可证及 `build-info.json`。配置原样复制，版本只在产物的唯一占位符中替换。版本描述只匹配个人 `site-v` 标签，无个人标签仍可回退到提交短 SHA。ZIP 根目录直接是网页，可部署到静态 Web 服务器，包内不是路由器固件。

构建信息记录版本、源码 SHA、站点源码是否修改和提交时间。ZIP 使用排序后的文件与提交时间；同一源码、版本和环境可复现。只清理带本工具标识的 `build/site`，防止把用户已有目录当缓存；每个 ZIP 附带 SHA256。校验文本固定 LF，避免 Windows 默认 CRLF 被 Linux 的 `sha256sum` 解释为文件名的一部分。自定义配置文件必须先纳入 Git 索引才能进入产物，本地修改进入预览包并标记 `source_dirty`。

Release 接受已存在的 `site-vX.Y.Z`、`site-vX.Y.Z-beta.N` 和 `site-vX.Y.Z-rc.N` 个人标签，先解析固定 SHA，再对该 SHA 执行测试、质量检查和打包。发布前核验包摘要、版本、源码 SHA 和干净站点状态，按上游隔离策略排除初始历史与后续同步的上游提交。[双语发布说明](2026-11-04-release-notes-automation.md)接管正文组成与渲染链接检查：每版本中英文内容结合动态提交和产物信息，release-notes.md 同时用于正文与下载资产。预发布不成为 latest。已有 Release 明确失败，不静默覆盖资产；中断后的残留发布需要维护者检查。

只有 Release 上传任务获得 `contents: write`，只有 Pages 部署任务获得 `pages: write` 和 `id-token: write`。同一标签发布以及 Pages 部署不相互取消。Pages 使用同一 ZIP，校验后展开并部署，不另行改配置；部署来源在仓库 Settings 中选 GitHub Actions，环境允许的分支由仓库管理员设置。

## Related notes

活跃笔记按工作流、默认检查、发布、部署关键词审计：[默认检查](2026-10-30-default-checks.md)与本篇部分重叠并互链。旧篇保留 ESLint/Prettier 风格与 Git 换行决定，本篇持有完整 CI/Release/Pages 契约；其他功能与测试笔记不改变各自决定，没有完全吸收或过时提案需要归档。

## Alternatives considered

- 保留原 main/stable 自动部署：改动量少，但 main 自动部署违背手动 Pages 选择，stable 固定官方服务器也不是当前项目的发布目标。
- 直接复制桌面三个工作流：已有中文发布和质量检查可参考，但 PHP/WordPress 安装、主题 ZIP 和通知配置与本项目无关。保留分工，使用原生站点与现有 Node/Firefox 测试。
- Release 和 Pages 各写构建命令：单文件内更直观，却会复制版本、配置与文件收集逻辑；共用构建脚本和可复用检查，避免两种部署拿到不同网站内容。
- 逐条改写上游英文提交：能让整条历史满足中文规范，但会改变共享历史且与本轮需求不符。基线之后启用规范，保留已有上游历史。

- 2026-11-12 的运行时备选——保留旧 SHA 并依赖平台强制 Node24：变更最少且本次部署已经成功，但旧 Action 本身仍声明弃用运行时，警告与平台兼容行为会继续成为维护负担；改为升级经核验的固定 SHA，不增加运行时覆盖开关。

## Verification

### 初始工作流基线

- `npm run check` 的 ESLint、格式和 179 项 JavaScript 测试通过。
- 11 项工具测试覆盖提交范围、机器人豁免、无标签版本、源码配置保留、未跟踪文件排除、摘要及 LF、重复构建、陈旧输出、版本输入与发布说明范围。
- 实际 Windows 构建生成 ZIP、SHA256 和构建信息，由 Git Bash 的 `sha256sum --check` 与 `unzip` 校验、展开成功，源码版本占位符与服务配置保持不变。
- Semgrep 1.183.0 使用未登录社区规则和严格参数扫描，SARIF 记录零发现、执行成功、无执行通知；此前 26 处可变 Action 标签已固定为完整 SHA。
- actionlint 1.7.12 本地配置校验与 17 段内嵌脚本的真实 Bash 语法检查通过；本机未配置 ShellCheck，其附加检查仍由 CI 完成。
- 本轮没有运行远端 Actions、创建标签、发布 Release 或部署 Pages。Firefox 原有 7 项已验证基线保留，锁定依赖已做可解析性检查；未在本轮重新安装浏览器。

### Node24 引用维护（2026-11-12）

- `python -B -m unittest discover -s tests/tooling -p "test_*.py" -v` 的 45 项工具测试通过，覆盖上游提交排除、Release 说明与产物契约等现有行为。
- actionlint 1.7.12 经官方 SHA256 核验后检查全部 5 个 `project-*` 工作流通过；本机这次未运行 ShellCheck/Pyflakes，不能等同于远端完整质量门禁。
- 用现有 js-yaml 解析 HEAD 与工作区两份 YAML，仅替换预期的 4 个 `uses` 后对象严格相等；所有个人工作流的外部 Action 仍固定 40 位 SHA，`git diff --check` 通过。
- 本次只完成本地引用修改和验证，未提交、推送或部署；运行 43187627434 是升级前的成功基线，不是新引用的云端验收。新版 Action 在云端的下载、Pages 发布、Release 与告警消除仍需对应运行确认。

## Consequences

新版下载器在产物摘要不匹配时直接失败，比旧版警告更严格；出现此类失败时需查明产物或传输问题，而不是放宽完整性校验。当时固定完整 SHA 带来的人工更新成本由[官方 Action 主版本标签](2026-11-14-action-major-tags.md)重新取舍；未来若切换到自托管 runner，仍需单独核验 Node24 的最低 runner 版本。

同一套检查与产物同时服务日常开发、版本发布和 Pages 部署，中文提交形成可读的中文变更说明，也移除了官方服务器账号依赖。Release 和手动 Pages 会重新执行全部检查；develop 推送则由 Pages 统一调用一次，具体触发与去重契约见[Pages 自动部署](2026-11-03-pages-auto-deploy.md)。首次运行需要下载 Firefox、Python 依赖与扫描规则；第三方 Action SHA、工具版本和官方 Action 的主版本迁移仍需定期维护，具体引用策略见[官方 Action 主版本标签](2026-11-14-action-major-tags.md)。

手动操作的工作流必须先出现在默认分支，发布标签必须包含工作流与脚本。上传后的真实权限、GitHub Pages 环境和容器执行情况只能由远端首次运行确认，本地静态校验不代表远端发布成功。用户后续明确要求的 TG 汇总由[Telegram 通知](2026-11-03-telegram-notifications.md)补齐；若未来需要服务器推送，再按明确目标添加，不保留闲置凭证与发布分支。
