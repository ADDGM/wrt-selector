# Agent Note: 隔离上游同步与二次开发工作流

Status: implemented

## Problem

用户明确 main 用于同步上游，develop 承载个人二次开发。初始工作流适配按 main/develop 都是项目分支设计，没有覆盖纯上游镜像场景。只修改 develop 的触发规则，不能控制 main 上的旧测试及自动 Pages 工作流；固定历史基线也不能排除未来新增的英文上游提交。

本地 fetch/merge 不会产生 GitHub push 事件；此处处理同步结果推送到用户仓库后的执行。用户仓库原名为 ADDGM/firmware-selector-openwrt-org，现采用 [Wrt Selector 命名](2026-11-03-project-identity.md)，目标为 ADDGM/wrt-selector；父仓库仍是 OpenWrt 官方项目。

## Decision

用户确认保持 main 纯上游镜像、develop 个人开发的两分支分工，版本用标签与 Release 固定。默认分支约定为 develop，使个人说明和手动工作流可用；远端首次拥有 develop 后再切换。同步上游时先更新并推送 main，再合并到 develop。origin 指向个人仓库，upstream 指向官方仓库；本地 main 保持跟踪 upstream/main。

个人工作流使用 project-ci.yml、project-quality.yml、project-release.yml、project-pages.yml 独立路径，复用引用同步更名。上游 test.yml、static-main.yml、static-stable.yml 保留上游内容，减少后续同步的文件差异；用户已在自己的仓库禁用三者，2026-11-03 API 实测均为 disabled_manually。个人 actionlint/Semgrep 只检查 project-*.yml 中的工作流，已停用的上游文件不承担个人质量门禁。不在镜像 main 上添加禁用提交，也不依赖只修改 name 显示名称。

个人日常检查只自动响应 develop push 与目标分支为 develop 的 PR；Pages 只接受 develop。原先两份检查独立监听 push、Pages 仅手动的触发策略由[Pages 自动部署](2026-11-03-pages-auto-deploy.md)部分取代：develop 推送统一由 Pages 调用检查并部署，PR 仍直接运行两份检查。PR 的 branches 过滤目标分支，因此 main 向 develop 提交上游集成 PR 仍执行测试。镜像分支负责保留上游，集成到个人版本后必须验证兼容性。

PR 检查工具从合并结果读取，提交范围显式传入 base/head。原提交任务直接检出 PR head，纯上游 main 向 develop 的 PR 会找不到个人新增的 scripts/check_commits.py；检出合并结果保留个人工具，又不把合并目标分支的其他提交当作本次 PR 新增内容。

中文提交检查和发布说明同时排除初始历史基线与纯上游镜像的可达提交。普通本地命令读取 main，CI 读取 origin/main；Release 和 Pages 固定同一镜像 SHA 传入后续质量检查，Release 说明也记录并使用此 SHA。镜像不存在或与初始历史无关时失败，不退回只检查旧基线；镜像暂时落后初始基线时，两者的排除范围取并集。镜像须保持纯上游，不能用它豁免个人不规范提交。

个人标签使用 site-vX.Y.Z、site-vX.Y.Z-beta.N、site-vX.Y.Z-rc.N，与上游 v 标签分开。Release 验证目标已合入 develop 且不属于纯上游历史；未合并功能分支不能发布。普通构建只识别 site-v 个人标签，无个人标签时使用提交短 SHA。仅 beta/rc 后缀标记 prerelease，site-v 前缀中的连字符不影响正式版判断。

## Related notes

活跃笔记审计：[项目工作流](2026-10-31-project-workflows.md)部分重叠并互链，本篇接管工作流身份、个人标签和上游提交排除策略，ZIP/Release 及统一验证继续适用；[Pages 自动部署](2026-11-03-pages-auto-deploy.md)接管 develop 推送与 Pages 的触发编排，保留本篇镜像隔离约束；[默认检查](2026-10-30-default-checks.md)保留其风格决定。功能笔记无关，没有应归档或删除的过时提案。

## Alternatives considered

- 增加 upstream-sync 镜像分支，main 作为个人稳定版、develop 作为开发版：稳定与开发内容长期并行时职责清楚，默认分支也能展示正式版本；当前还没有独立稳定分支需求，会增加一次晋升合并和维护面。仅改变镜像名称仍不能阻止上游不限分支的 push 工作流。
- 仅在本地保留上游远程跟踪引用，不推送镜像分支：本地 fetch 不触发 GitHub Actions，减少远端镜像维护；但不能满足希望在自己的 GitHub 仓库保留独立上游同步分支的使用方式。
- 在镜像 main 内删除或修改工作流：能直接改变触发，但会使镜像偏离上游，后续合并还需维护这些差异。仓库侧禁用现有上游工作流与独立个人文件路径更适合保留纯镜像。
- 仅为当前 develop 工作流增加 branches 过滤：改动最少，但同一路径在 main 上的旧内容仍可能触发，而且无法解决未来上游英文提交被误拦的问题。

## Verification

- 16 项 Python 工具测试通过，覆盖未来上游英文提交合入后的豁免、个人英文标题拒绝、旧镜像快照不能冒充新快照、上游标签/说明排除，以及纯上游和未合入 develop 的源码拒绝发布。
- 临时 Git 仓库模拟 main 无个人检查脚本、develop 有脚本的真实合并，使用合并结果运行 CLI 且显式传入 PR base/head，上游集成范围正确报告零个人提交。
- 本地 main 与远端 origin/main 两种镜像引用均通过现有三条个人提交检查，actionlint 1.7.12 对四份个人工作流校验通过。
- API 核实个人仓库管理员权限及三条旧工作流的禁用状态。远端当时只有 main，默认仍为 main；develop 首次推送及默认分支切换属于交付步骤，不能由本地校验替代。远端 Actions、Release 与 Pages 实际执行需单独确认。

## Consequences

上游未来新增工作流文件时，旧工作流的禁用状态不会自动覆盖新增文件，同步前仍需检查 .github/workflows 变动。GitHub 的仓库级禁用、默认分支和 Pages 环境属于外部状态，本地 YAML 检查不能确认其生效。

默认分支改为 develop 后，网页上的默认展示与部分操作入口会随之变化；同步时需要明确选择 main。若将来需要稳定网站长期停留在一个版本、同时持续开发下一版本，再考虑启用个人稳定 main 与独立镜像分支。
