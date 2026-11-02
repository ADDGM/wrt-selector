# Agent Note: develop 推送通过检查后自动部署 Pages

Status: implemented

## Problem

原会话最后要求 Pages 随推送自动更新，现有工作流只有手动入口。直接增加 push 会与独立监听 develop 的测试、质量工作流重复执行同一套检查。2026-11-03 读取 GitHub API 确认仓库尚未启用 Pages，因此本地 YAML 完成不等于网站已部署。

## Decision

`project-pages.yml` 统一承接 develop push，保留 workflow_dispatch。source 任务只接受 `refs/heads/develop`，继续验证个人源码并固定上游镜像 SHA。quality 和 test 复用现有工作流，显式使用本次 `github.sha`，质量检查使用已固定的上游 SHA；推送的中文提交范围仍来自原始 before/head 事件。

`project-ci.yml` 与 `project-quality.yml` 移除独立 push，保留目标为 develop 的 PR、手动运行与 workflow_call。每次 develop 推送执行一套完整检查，PR 继续检查合并结果并使用原始 base/head 范围。Release 仍复用原有入口，无需复制检查或构建步骤。

deploy 必须等待 quality 和 test 成功，下载同一次运行中的 website-package，校验 SHA256 后展开，再上传 Pages artifact 并部署。仅部署任务持有 pages/write 和 id-token/write，检查任务维持 contents/read。任何检查失败均阻断本次部署，已发布网站继续保留。

Pages 使用带分支引用的并发组，cancel-in-progress=false：同分支不取消正在运行的部署，等待中的旧运行由新运行替换。分支隔离使误选其他分支的手动任务不能挤掉 develop 的等待任务。该机制不承诺发布每一个中间提交；持续快速推送时以当前运行和最后一个等待运行为主，失败后需要修复或重跑。

首次启用需把仓库 Pages 发布源设为 GitHub Actions，并允许 github-pages 环境从 develop 部署。工作流不会自行扩大环境权限或启用上游工作流；线上生效以远端运行及网站内容为证据。

## Related notes

本轮按 Pages、project-pages、手动部署检索活跃笔记：[项目工作流](2026-10-31-project-workflows.md)与本篇部分重叠，保留统一 ZIP、质量门禁及发布理由，手动 Pages 策略由本篇取代；[上游工作流隔离](2026-11-03-upstream-workflow-isolation.md)部分重叠，保留 main/develop 分工、独立文件路径和上游提交排除，仅推送入口编排由本篇接管。两篇均反向链接本篇，不归档仍有效的决定。[默认检查](2026-10-30-default-checks.md)只持有检查入口与代码风格，功能和浏览器测试笔记也无须改动；未发现需拒绝或删除的过时提案。

## Alternatives considered

- 只给 Pages 加 push：改动最少，独立 CI 状态名保持原样；但每次推送会重复安装依赖并执行 Firefox、Node、扫描与打包。统一调用能保留现有检查实现，同时去掉重复运行。
- 等独立 CI 完成后用 workflow_run 下载跨运行 artifact：能保留现有 push 入口并复用已完成产物；但还需关联同一 SHA 的质量工作流、核验触发来源并增加跨运行下载权限。当前单仓库站点用同一次运行内的 needs 和 artifact 足以表达依赖。
- 保持手动 Pages：上线时机可控，适合固定稳定版；当前明确需要 develop 推送后更新，因此保留手动入口作为重跑方式，不再作为唯一部署入口。

## Verification

- actionlint 1.7.12 校验四份个人工作流通过；Windows 工具 ZIP 与官方 SHA256 一致。本地未安装 ShellCheck/Pyflakes，本轮配置修改未改动内嵌脚本。
- 通过 js-yaml 解析实际配置并用 Node 断言验证 7 种 push/PR 触发场景，以及手动分支限制、同 SHA 复用、9 个检查任务失败阻断、同运行 artifact、并发隔离和部署权限。
- `python -B -m unittest discover -s tests/tooling -p "test_*.py" -v` 的 16 项工具回归通过，覆盖上游合并、发布来源、构建和提交范围。
- 笔记树、格式与归档三项门禁通过，共 7 篇活跃笔记、0 篇归档；Git 差异空白检查通过。
- 本次未修改站点运行时代码或测试实现，未重新安装 Firefox；远端 Pages 尚未启用，本地改动尚未提交或推送，自动部署上线及网站内容仍须远端验证。

## Consequences

develop 推送检查通过后可自动更新网站，PR、其他分支和上游镜像推送不部署。代价是推送检查在 Actions 中归属 Pages 运行，若禁用该工作流，develop 的自动检查也停止；需要保持它启用。当前 API 确认 develop 没有分支保护；以后增加必需检查时，应选择新的实际检查名称。网站会跟随开发分支；若未来需要稳定站点，应重新讨论部署分支或标签策略。

Pages 启用和环境保护是外部配置，工作流文件无法证明它们已生效。检查中的远端服务故障会阻止新版本上线，当前已发布页面不受影响。
