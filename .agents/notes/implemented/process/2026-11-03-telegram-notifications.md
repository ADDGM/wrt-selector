# Agent Note: Pages 与 Release 共用 Telegram 汇总

Status: implemented

## Problem

桌面 Sakura 示例的 CI 与 Release 带 Telegram 通知，初次适配只迁移了检查、打包和发布分工。用户发现当前网站已上线但没有正式 Release，也收不到工作流通知。仓库已经存在 TELEGRAM_TO 和 TELEGRAM_TOKEN 两个 Secret 名称，当前脚本却没有使用它们。

## Decision

用户选择首发 site-v1.0.0 正式版，通知覆盖 Pages 和 Release。`project-notify.yml` 只供这两份工作流调用，每次运行结束尝试发送一次汇总；被复用的 CI 与质量工作流不单独通知。Pages 只在 develop 运行时通知，PR 和独立手动检查没有通知入口。

调用方以 always() 等待整组 needs，传递真实任务结果、目标源码 SHA、分支或标签和结果链接。可复用工作流内部任务和步骤同样显式使用 always()，后续步骤要求 checkout/setup 成功，避免默认 success() 在取消状态下跳过。状态按失败、取消、未知、未执行、全成功的顺序汇总，检查失败导致发布跳过时不能报成功。成功消息带实际网站或版本链接；失败消息仍保留 Actions 运行链接。Release 的提交 SHA 来自解析后的标签，而不是手动触发分支。展示名遵循 [Wrt Selector 命名](2026-11-03-project-identity.md)。

`scripts/notify_telegram.py` 用 Python 标准库 HTTPSConnection 向固定 api.telegram.org 的 sendMessage 发送 JSON，不跟随重定向，显式使用 ssl.create_default_context 验证证书和主机名。纯文本避免分支名、仓库名的 Markdown 转义问题。仅通知步骤接收明确传入的两项 Secret；不继承全部凭证，不添加第三方 Action 或依赖。缺少凭证明确跳过；仅 API 返回 ok=true 才确认发送。HTTP 错误只记录状态码，网络及输入错误使用固定描述，不输出令牌、聊天 ID、请求地址或原始响应正文。

Semgrep 的 httpsconnection-detected 审计规则无条件匹配该 API，用于提醒旧 Python 证书默认行为。通知环境固定 Python 3.11，客户端显式安全 TLS 上下文且测试断言 CERT_REQUIRED/check_hostname；仅这一调用行记录精确规则的 nosemgrep 误报豁免，其他规则与严格扫描继续生效。原先的通用 urlopen 实现因动态地址审计及重定向能力被替换。

通知作业允许失败，所以通知服务异常不改变检查、部署或发布结果。网络请求超时 20 秒，不自动重试，避免服务端已接收而客户端超时后的重复发送。整次运行被平台强制终止时只能尽力通知，不能承诺取消事件一定送达；手动重跑可以再次通知。

## Related notes

按 Telegram、通知、发布和 Release 检索活跃笔记：[项目工作流](2026-10-31-project-workflows.md)部分重叠并互链，保留统一 ZIP、质量门禁、标签和凭证权限规则，本篇接管补充通知的范围；[Pages 自动部署](2026-11-03-pages-auto-deploy.md)保留推送触发与去重规则，本篇只在整套检查后汇总。[上游隔离](2026-11-03-upstream-workflow-isolation.md)和本机工具记录无须调整，没有需要删除或归档的旧提案。

## Alternatives considered

- 直接复制示例 appleboy/telegram-action：配置熟悉、代码量少；但会增加 Docker Action 和额外依赖，示例 Markdown 还需要处理动态文本转义。当前已有 Python 工具环境，标准库足以完成一次请求，也便于模拟错误和检查凭证脱敏。
- CI、质量、Pages、Release 分别发消息：每份工作流都有独立结果，但 Pages 和 Release 复用前两者时会产生重复消息。用户选择由两个入口各发一条完整汇总。
- 通知失败就让整条流水线失败：能强制关注通知故障，但会把已经完成的网站部署或 Release 误判成未交付。采用允许失败的通知作业，并在日志和任务摘要说明发送结果。

## Verification

9 项模拟测试覆盖成功、失败、取消、跳过、缺 Secret、API 拒绝、HTTP 错误及重定向、网络超时、凭证脱敏、安全 TLS 和不联网的 dry-run，均通过且不使用真实 Telegram 凭证。原有 16 项工具回归及 5 份工作流 actionlint 通过；MCP Semgrep 1.183.0 没有有效发现或执行错误，仅保留上述有依据的单行审计忽略。笔记门禁通过。Secret 名称存在不代表权限可用，首次真实通知和 site-v1.0.0 发布以获授权后的远端执行为准。

## Consequences

通知汇总沿用现有工作流的真实结果，发布与 Pages 不再遗漏反馈；失败发送不会撤销已经成功的交付。代价是机器人可达性、目标聊天权限和凭证轮换需要维护，API 确认也不能证明收件人已读。首次发版仍必须创建已验证源码的个人标签，普通 develop 推送只更新 Pages。
