# Agent Note: Wrt Selector 命名与双语文档

Status: implemented

## Problem

项目已扩展为双系统、三服务的固件选择与定制界面，README 却混合上游安装说明和后续补充，截图仍是上游页面。GitHub About 使用上游简介与官方站点地址，无法准确表达当前项目。用户要求重写文档、修改 About，并确认展示名 Wrt Selector、仓库名 wrt-selector 和中英文支持。

## Decision

Wrt Selector 是项目展示名，目标仓库为 ADDGM/wrt-selector，默认 Pages 地址为 https://addgm.github.io/wrt-selector/。网页 title、品牌、反馈和源码入口，以及 Release/TG 展示名统一使用该名称。title 使用稳定品牌，不由上游翻译键重新覆盖。页面的设备、版本、构建和翻译逻辑保持现有契约。

项目使用独立的几何 W 与单路由节点标识，替换上游无线标志。深蓝底 `#102d40`、浅色线条 `#f5f9fc` 和青蓝节点 `#35c5df` 沿用现有蓝色工具界面的方向，不增加动画。`www/logo.svg` 是彩色母版，同时用于页头、两份 README 和现代浏览器 favicon；`www/logo-monochrome.svg` 提供透明镂空的单色图形并接入 mask-icon。页头标志作为 aria-hidden 的 CSS 背景，由旁边的项目名称承担链接名称，明确宽高避免加载后位移；用自动外边距代替空白 flex 占位元素，给窄屏语言按钮留出空间。HTML-Proofer 默认拒绝空 alt，故使用装饰性背景，不关闭检查或重复提供相同的可访问名称。

`www/favicon.ico` 保留兼容入口，包含从同一 SVG 栅格化的 16、32、48 像素 PNG 条目。修改母版后需重导出这三个尺寸并更新 ICO；单色版的路径、节点与圆角同批同步。它们都是本地静态文件，不增加字体、图标库或图像处理运行时依赖。Prettier 2 不自动识别 SVG，单独排版时使用 `node node_modules/prettier/bin-prettier.js --parser html --write www/logo.svg www/logo-monochrome.svg`。Safari 固定标签页的实际着色由浏览器处理，未做 Safari 实机验收。

README.md 是英文入口，README.zh-CN.md 是中文入口；docs/en 和 docs/zh-CN 下同名的 usage、configuration、development、deployment 各自承担使用、配置、开发和部署说明。每对文档互链，行为、命令、默认值和限制同批同步。个人更新记录提供两种语言，旧上游更新记录保留原文；版本摘要可以提前准备，实际发布状态统一指向 GitHub Releases，远端验证前不宣称已经发布，避免正式标签中的文档永久保留“准备中”字样。

公开文档明确本项目是独立维护的二次开发，保留 OpenWrt 来源及 CC0 许可证。双语 acknowledgements 列出用户明确指定的四项参考：CzBiX/openwrt-firmware-selector、EkkoG/ofs-next、openwrt/firmware-selector-openwrt-org、immortalwrt/firmware-selector-immortalwrt-org，分别说明配置入口、高级构建选项、直接上游和系统配置的参考用途。已有 Projectmem 记录提供 CzBiX 配置、ofs-next 容量/公钥与 KyaruCloud 核对依据。OpenWrt ASU 和服务维护者另列为基础设施，不能用依赖列表替代用户的参考项目清单。原上游截图不再作为本项目界面展示。面向普通使用者的入口不包含本机 Agent/索引配置，也不把选择器 ZIP 描述为路由器固件。

GitHub About 使用双语简介：OpenWrt & ImmortalWrt firmware selector with multiple ASU services, custom packages, feeds and first-boot scripts. 支持多构建服务、软件包、软件源和首次启动脚本定制的固件选择器。主页指向个人 Pages；主题采用 openwrt、immortalwrt、firmware-selector、asu、imagebuilder、javascript、github-pages。

仓库改名与发布衔接处理：更新 origin，保留 upstream 官方地址及本地目录，核对默认 develop、Pages 环境和工作流状态，并在推送后验证新站点。GitHub 仓库链接有重定向，旧项目 Pages 地址没有重定向，不能把它当作仍可用的分享入口。个人 site-v 标签、firmware-selector- 产物前缀及旧 asu 服务 ID 保留，避免显示名称变化扩大成协议迁移。

## Related notes

按项目名、文档、发布和上游检索活跃笔记：[上游隔离](2026-11-03-upstream-workflow-isolation.md)部分重叠并互链，只同步个人仓库名称；[项目工作流](2026-10-31-project-workflows.md)、[Pages 自动部署](2026-11-03-pages-auto-deploy.md)和 [TG 通知](2026-11-03-telegram-notifications.md)保持各自行为契约，本篇负责展示名、双语入口和地址切换。功能与本机工具笔记不被取代，没有需删除或归档的旧提案。

## Alternatives considered

- 保留上游仓库名，仅补 README：改动少且不改变地址，但 About、页面反馈和仓库身份仍容易被当作上游站点；用户选择首发前统一改名。
- README 中并排堆放两种语言及全部配置：单文件容易查找，但内容过长、导航和更新难以对齐；采用双入口与对应指南，保留每页切换链接。
- 同时重命名产物、版本前缀和服务 ID：名称完全统一，但没有新增功能，会扩大构建契约和旧链接迁移；保留技术标识，只调整展示身份及仓库地址。
- 路由器轮廓加勾选：能直接表达固件选择，但在 16 像素下细节更拥挤，也不如 W 与项目名称关联明确；采用几何 W 与单节点，并保持独立于具体固件系统。

## Verification

图标接入后的 `npm run check` 通过 ESLint、Prettier 与 185 项 JS 测试。浏览器在 320、375、1440 像素、明暗主题和中英文共 12 组条件下验证页头图像加载、无元素重叠或横向溢出，pageerror 为 0；彩色/单色 SVG 和 ICO 均返回 200。目视检查真实页头、16 像素版本和单色透明镂空效果。静态检查确认 61 个原有 ID 保留、资源链接有效、SVG 不含脚本/外部图像、ICO 的三帧尺寸与 PNG 载荷有效。验证使用模拟固件目录，不发起构建请求。PNG 预览保存在仓库外的本地可视化目录，网站仅使用正式 SVG/ICO。

首次推送运行 41524216263 暴露 HTML-Proofer 的 Images 检查拒绝空 alt；此前的结构和浏览器检查没有复现这一规则。页头改用装饰性背景。Firefox 的其余六项回归通过，旧单服务用例仍断言原项目标题，因此同步为用户确认的 Wrt Selector，保留其目录及多语言断言。后续以同一远端 HTML 与 Firefox 检查通过为准，不能把本地检查替代这两项门禁。

核对 config.js、HTML、工作流及脚本中的实际能力，配对文档检查相对链接、锚点和代码示例一致性。179 项 JavaScript 测试、ESLint/格式检查通过，HTML 的 61 个原有 ID 保留；浏览器在 390px 中文和 1440px 英文下核验稳定品牌、反馈/源码链接且无横向溢出，外部请求被拦截，没有提交构建。5 份工作流通过 actionlint，笔记三项门禁通过；临时 actionlint 目录与浏览器日志已清理，浏览器及本地服务关闭。README/CHANGELOG 不把准备中的 site-v1.0.0 当作已发布。仓库改名、About 修改、新 Pages 地址、Release 资产和真实 TG 接收仍需远端交付验证，本地实现不代表已上线。

## Consequences

使用者可以从准确的双语入口及独立图标识别项目，维护者可按主题更新文档，同时保留上游来源和兼容接口。代价是每次行为变更需要同步两种语言，图标修改需同步单色版和 ICO；改名会改变默认 Pages 地址，旧网站链接需要更新。当前自动生成的提交明细仍沿用中文提交标题，用户版本摘要由双语更新记录承载。
