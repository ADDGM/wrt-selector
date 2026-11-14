# Agent Note: 官方主标签的精确安全策略

Status: implemented

## Problem

官方主版本标签提交 `ebc1c069350d6e6c7e91a8e6d8f7c33914d0f062` 的运行 43594405791 中，Semgrep 任务 132445775419 正常完成扫描，却因 29 处官方主标签触发通用可变标签规则而失败：230 条规则扫描 23 个文件，29 项发现全部属于 `yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag`。`--error` 使任务返回 1，Pages 因依赖门禁未部署。此前仅审查第三方未固定 SHA 规则，不能代表整组 GitHub Actions 规则允许官方标签。

用户继续选择官方主标签，并批准为已审核的具体引用建立例外。这是对可变依赖的风险接受，不是误报，也不表示标签与完整 SHA 同等安全；不能通过关闭全部安全扫描掩盖冲突。

## Decision

`.github/semgrep/action-reference-policy.yaml` 是本项目 Action 引用策略的单一权威。规则 `project-action-reference-must-be-reviewed` 沿用被替换规则的 `steps` 内 `uses` 范围，仅允许以下 7 个精确组合，不按整个 `actions/` 命名空间放行：

| Action | 批准主标签 |
| --- | --- |
| actions/checkout | v7 |
| actions/setup-node | v6 |
| actions/setup-python | v6 |
| actions/upload-artifact | v7 |
| actions/download-artifact | v8 |
| actions/upload-pages-artifact | v5 |
| actions/deploy-pages | v5 |

其他远程 Action step 必须固定为完整 40 位小写十六进制提交 SHA。白名单和 SHA 引用使用整值锚定，不接受伪造仓库、其他主版本、小版本标签、分支、尾缀、空白或换行后的附加文本。本地 `./` Action 和 `docker://` 引用保持原规则排除边界；本规则不扩展到 job-level reusable workflow，也不替代容器安全检查。

`.github/workflows/project-quality.yml` 的同一 Semgrep 扫描命令保留 `p/javascript`、`p/python`、`p/github-actions`，增加本地规则，并仅通过 `--exclude-rule` 排除上述完整旧规则 ID。`--error`、`--strict`、SARIF 输出上传以及 `www scripts .github/workflows/project-*.yml` 范围保持不变。规则加载或扫描错误仍阻断任务，不能单独关闭原规则却遗漏替代规则。

同一 Semgrep 任务在正式扫描前运行 `semgrep scan --test --strict --metrics off --disable-version-check .github/semgrep`，真实测试失败即阻断后续扫描。`.github/semgrep/action-reference-policy.test.yaml` 存放带 `ruleid`/`ok` 注释的真实引擎正反例；样例不位于可执行工作流目录。`tests/tooling/test_action_policy.py` 只检查工作流接线和范围，不用 Python 正则模拟规则匹配。

既有 `semgrep/semgrep:1.183.0@sha256:2e45517a85e13a9cca14a2a00df6bb48affd66b8ebfae1b0991cd57578362fb0` 镜像及其他安全工具不变。不新增项目依赖、工作流、机器人或扫描服务，不改变触发、权限、第三方 Action SHA、产物验证、部署依赖及上游隔离。

## Related notes

已按 Action、主标签、SHA、Semgrep 与安全门禁关键词审计活跃 proposed/implemented 笔记；当前无 rejected 目录，不为本次审计创建空目录。

- [官方 GitHub Actions 采用主版本标签](2026-11-14-action-major-tags.md)：部分重叠并互链。本篇接管此前“不改变安全规则”的边界；主标签选择仍成立，旧 Verification 保留当时未执行完整扫描的事实，不改写历史证据。
- [统一站点构建、中文提交与 GitHub 发布工作流](2026-10-31-project-workflows.md)：部分重叠。Registry 三组规则与发现/错误阻断契约仍成立，本篇定义新增的本地替代规则；原始 SHA 选择及产物链证据仍保留。
- [上游工作流隔离](2026-11-03-upstream-workflow-isolation.md)：相关边界不变，扫描和修改只覆盖个人 `project-*`，不改上游三份工作流。
- [Pages 自动部署](2026-11-03-pages-auto-deploy.md)：相关边界不变，质量与测试成功仍是部署前提。
- [Telegram 通知](2026-11-03-telegram-notifications.md)：相关边界不变，仍如实汇总成功、失败与跳过。
- [发布说明自动生成](2026-11-04-release-notes-automation.md)及[默认本地检查](2026-10-30-default-checks.md)：与本次策略无关，只有历史 SHA 或验证词汇命中，不修改。

没有完全吸收的旧篇，也没有需要删除、reject 或归档的过时提案。

## Alternatives considered

- 恢复全部完整 SHA：依赖身份更明确，可复现性和审查边界更强，也直接满足原规则；但违背用户本次保留官方主标签的明确选择。遇到标签回归或更严格供应链要求时优先重访此方案。
- 关闭 GitHub Actions 规则包或放行全部官方命名空间：实现最简单、以后标签升级无需改列表；但会放过未审核 Action/主版本，前者还丢失其他安全检查，超出批准范围。
- 在每一处官方引用旁写 `nosemgrep`：例外贴近使用位置，审阅单个 step 很直观；但 29 处重复注解会把同一策略分散到五个文件，新增引用容易漂移。集中规则和真实正反例更便于维护精确边界。

## Verification

- 已有本机 Semgrep native core **1.178.0** 在正常批准的本地文件扫描中匹配 41 个真实 YAML 样例：26 个应报全部命中，15 个应允许全部无告警，无缺失、额外命中或解析错误。覆盖全部批准组合、未审核主版本、第三方标签/分支、伪造命名空间、子路径、引号/注释、短 SHA、无引用及尾缀等边界。
- 同一现有 native core 对 5 个 `project-*` 工作流逐文件运行本地规则，均为 0 发现、0 错误。使用 `-json_nodots` 避免进度点污染 JSON；core 的显式 `-lang yaml` 调用按单文件执行。这不是 Registry 三组规则的完整扫描。
- `python -B -X utf8 -m unittest discover -s tests/tooling -p "test_*.py" -v`：48 项通过，其中新增 3 项检查规则组合、唯一排除 ID、真实测试先于扫描、固定镜像及不可软失败等接线。现有 js-yaml 成功解析 5 个工作流和 2 个规则/样例 YAML。
- 本机 Semgrep CLI 的旧 Python 启动器仍损坏；没有修全局安装或引入项目依赖。上述旧版本 core 检查不能代替固定 CI **1.183.0** 的 `--test` 入口或完整 Registry 组合验收，#0050 与云端失败 #0051 仍保持开放。
- 本轮不重复上一次包/线上验收，不宣称 actionlint、ShellCheck 或 Pyflakes 已在本轮运行。没有本轮提交、推送、标签、Release 或部署；新的云端验收需要另行发布授权。

## Consequences

例外集中在一个精确规则中，既满足已批准的官方主标签偏好，又保留其他远程 Action 的完整 SHA 要求和其余安全扫描。未来任何新 Action 或跨主版本升级都必须重新审核、更新白名单并补正反例；不能只修改工作流再扩大命名空间豁免。

主标签可被移动，仓库提交不变也可能运行不同的依赖代码。SHA/产物摘要、其他扫描规则和现有最小权限不能消除这一接受的风险。规则只检查 Action step 引用形态，不提供 Action 代码审计或全面供应链保障。

本地替代规则带来维护成本：更新 Semgrep/Registry 时需要复核上游旧规则 ID、范围及替代关系，避免上游改名造成重新告警，或误以为有其他规则接管。回归测试必须继续与扫描使用同一 CI 镜像；云端完整门禁尚未通过前不能宣布部署恢复。

采用单点规则与既有任务复用，符合 KISS/DRY；不引入额外依赖、更新服务或超出 step 引用范围的策略，符合 YAGNI。保留真实回归测试与决策证据，临时验证脚本和下载不作为长期产物；用户原有 `.gitignore` 修改不属于本次修复。
