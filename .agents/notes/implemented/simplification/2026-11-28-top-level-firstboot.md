# Agent Note: 首次启动示例按顶层脚本执行

Status: implemented

## Problem

原先为了便于拼接，示例用一对括号隔离日志和退出。用户将编辑框当作一份完整脚本，对照官方示例时这层缩进反而令人疑惑。选择器也不会自动在末尾追加命令。

## Decision

两种发行版的中英文模板都在脚本顶层执行。本决定只取代[官方样式与双语日志](../feature/2026-11-28-localized-firstboot-examples.md)中的子 shell 策略；该笔记继续负责语言、品牌和设备配置，[草稿规则](../feature/2026-10-30-uci-defaults-drafts.md)不变。[旧 ImmortalWrt 示例](../feature/2026-11-03-immortalwrt-firstboot-example.md)保留了隔离的原始理由。

## Alternatives considered

保留子 shell 可以让追加命令沿用原本的标准输出，但追加命令成功也可能掩盖前段失败。这不符合把示例作为单个脚本执行的预期。

## Consequences

手动追加的命令也会把输出写入 `/tmp/setup.log`；配置失败触发 `exit 1`，不会再运行后续命令。配置值、命令替换和凭据保护不变。

## Verification

用模拟路由器命令在模板末尾追加一行输出：旧模板输出到标准输出，新模板仅在成功时将其写入日志；模拟提交失败时保留非零退出码，不产生追加输出。四份 `sh -n`、7 组脚本测试和 185 项前端测试通过；未刷机。
