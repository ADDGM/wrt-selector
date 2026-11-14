# Agent Note: 官方 GitHub Actions 采用主版本标签

Status: implemented

## Problem

固定 Action 完整 SHA 能保留依赖身份，但不会自动获得同一主版本的运行时和修复更新。Pages 运行 43187627434 的 Node20 弃用告警已经触发一次人工升级；若继续维持全部 SHA，后续每次维护仍需要逐项核验和修改引用。用户希望减少这类维护，并明确选择官方 Action 使用主版本标签，而不是在本轮接入依赖更新机器人。

## Decision

仅 5 个个人工作流中的 29 处 GitHub 官方 `actions/*` 引用使用已核验的主版本标签：

| Action | 主版本标签 | 2026-11-14 核验标签所指提交 |
| --- | --- | --- |
| actions/checkout | v7 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| actions/setup-node | v6 | `249970729cb0ef3589644e2896645e5dc5ba9c38` |
| actions/setup-python | v6 | `ece7cb06caefa5fff74198d8649806c4678c61a1` |
| actions/upload-artifact | v7 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| actions/download-artifact | v8 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` |
| actions/upload-pages-artifact | v5 | `fc324d3547104276b827a68afc52ff2a11cc49c9` |
| actions/deploy-pages | v5 | `368f82528645a54fb793d4d04e342629a3f51346` |

核验使用各官方仓库的 Git tag API；这是实施时点的快照，不是对未来标签目标的保证。7 种标签当时均指向修改前工作区所用 SHA，因此本轮只改变引用策略，保留此前 Pages 三处及 Release 一处的 Node24 升级。移除引用末尾重复的版本注释，避免主标签移动后注释误导。

适用文件和官方引用数分别为 `project-ci.yml`（12）、`project-notify.yml`（2）、`project-pages.yml`（5）、`project-quality.yml`（5）、`project-release.yml`（5），均位于 `.github/workflows/`。不引入统一变量、额外工作流或依赖管理配置。

第三方 `anishathalye/proof-html` 仍固定到 `f060b7619c2410bd85d970459a60ef431cf47ed5`；Semgrep 镜像仍固定 `1.183.0@sha256:2e45517a85e13a9cca14a2a00df6bb48affd66b8ebfae1b0991cd57578362fb0`。actionlint 下载摘要校验、download-artifact 的摘要不符即失败、ZIP 校验、最小权限、secret 处理和本地可复用工作流引用均保持不变。上游 `test.yml`、`static-main.yml`、`static-stable.yml` 不纳入修改。

同主版本更新由 Action 维护者移动标签后在后续运行中生效，不是仓库定时任务或机器人自动提交；主标签不会自行从 v8 改为 v9。未来跨主版本或 Node 运行时迁移仍需检查兼容性。本轮不启用 Dependabot、Renovate 或自动合并，也不提交、推送、部署。

## Related notes

本次对活跃笔记按 Action、SHA、主版本、Dependabot、Renovate 和工作流关键词审计：

- [统一站点构建、中文提交与 GitHub 发布工作流](2026-10-31-project-workflows.md)：部分重叠。本篇接管官方 Action 引用策略；旧篇保留固定 SHA 的历史选择、运行时证据、产物完整性和发布契约，并反向链接本篇，不归档、不改写成相反的旧决定。
- [上游工作流隔离](2026-11-03-upstream-workflow-isolation.md)：相关边界不变，main 纯上游和个人工作流隔离继续适用。
- [Pages 自动部署](2026-11-03-pages-auto-deploy.md)：相关边界不变，不改变 develop 推送的复用、串行部署或去重机制。
- [Telegram 通知](2026-11-03-telegram-notifications.md)：相关边界不变，只调整官方 Action 引用，不改变通知时序或凭证处理。

没有完全吸收的笔记或需要 reject/归档的过时提案；其他功能笔记与本次引用策略无关。

## Alternatives considered

- 保留全部 SHA 并人工维护：依赖身份明确、便于审计和复现，但不能满足用户减少官方 Action 日常引用更新的选择；第三方仍沿用这一方式。
- SHA 加 Dependabot：保留固定依赖并由更新 PR 提供审查入口；需要新增配置并验证只覆盖个人工作流、排除上游文件。用户此次选择主标签，不扩大为机器人接入任务。
- SHA 加 Renovate：同样可提供更新 PR 和细粒度匹配，但需要额外配置与运行/安装维护；当前目标不需要引入另一条更新链。
- 包括第三方在内全部使用主标签：形式最统一，但扩大可变依赖的信任范围，也与现有 Semgrep 第三方固定 SHA 规则冲突；用户只批准官方 `actions/*` 的例外。

## Verification

- 本地精确替换断言每文件 12/2/5/5/5，共 29 处；使用现有 js-yaml 解析修改前后 YAML，在旧对象中只替换对应 `steps[].uses` 后严格深比较相等。触发、权限、任务依赖、脚本和产物输入输出没有改变。
- `python -B -m unittest discover -s tests/tooling -p "test_*.py" -v`：45 项工具测试通过，覆盖提交范围、发布说明、站点包、通知和 UCI 示例等既有契约。
- actionlint 1.7.12 的 Windows 包及校验清单均与官方 Release 摘要相符；ZIP SHA256 为 `6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9`。显式检查上述 5 个工作流通过；本机未运行 ShellCheck/Pyflakes，不等同完整云端门禁。
- 对[Semgrep 官方第三方 Action 规则](https://github.com/semgrep/semgrep-rules/blob/a5ad1714f00c9f7fde980cab0ea1d6dc6d414fd2/yaml/github-actions/security/audit/third-party-action-not-pinned-to-commit-sha.yml)的源码审查确认匹配器排除 `actions/`、`github/`、本地 Action、完整 SHA 与固定容器摘要。这只是规则范围核对，不是扫描结果。本机 Semgrep 因启动器引用已移除的 Python 3.11.15 无法启动；备用扫描服务加载规则超时，合成规则测试又被审批拒绝且未执行。完整 Semgrep 扫描尚未完成，问题记录为 #0050；不放宽仓库安全门禁。
- 从项目根目录使用已有 tsx 缓存运行 verify-agent-note-tree.ts、verify-agent-note-format.ts 和 verify-archived-agent-notes.ts，笔记结构、相对链接和归档封印三门禁通过；未新增项目依赖。
- 本次没有远端 Actions 运行，也未验证新引用在云端的运行时告警、Pages 部署或 Release；43187627434 仅是引用升级前的成功基线。

## Consequences

官方 Action 同一主版本的维护更新不再要求仓库逐次修改 SHA，代价是主标签可移动：即使仓库提交不变，未来运行解析到的 Action 代码也可能不同。此选择扩大了对官方维护者和标签保护的信任，产物摘要校验不能替代对 Action 本身的信任。

遇到标签回归、供应链风险、严格重现/审计要求，或日常更新需要人工批准时，应重访固定 SHA 加依赖更新 PR 的方案。第三方 SHA、工具版本和跨主版本迁移仍要定期维护；本次不是一次性免维护承诺。

采用直接引用而非新增抽象或机器人，保持 KISS/YAGNI；不复制构建和部署逻辑，保持既有复用契约。上游工作流、用户 `.gitignore`、依赖清单与锁文件保持原样，后续提交和云端验收需要单独授权。
