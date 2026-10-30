# Agent Note: ASU 高级构建选项

Status: implemented

## Problem

现有页面只能编辑软件包与首次启动脚本。软件源和签名公钥仅能通过部署配置传入，根文件系统大小没有入口。用户需要在页面上控制这三项，并保持现有静态站点架构。

## Decision

页面提供可空的根文件系统大小整数输入、可增删的软件源名称/地址列表、可增删的签名公钥列表及追加/替换模式。大小留空时省略请求字段；软件源默认追加；显式配置 replace 时保留该初值。软件源与公钥行为与用户于 2026-10-30 确认的方案一致。最初采用的固定 1024 上限已由[构建服务选择](2026-10-30-asu-service-selection.md)的分服务上限接管，该篇记录新的理由与兼容边界。

`www/js/build-options.js` 集中处理初值、表单与校验，`www/js/asu.js` 复用其请求转换。`www/config.js` 只提供初值，删除预设行后不得重新合并回来。软件源保留现有版本/平台占位符，名称重复或不完整的行阻止提交。签名公钥保持多行文本，由构建服务验证其加密格式。表单仅在 POST 前读取，轮询 GET 不重读或重验表单。

## Evidence

- [ofs-next CustomBuild.vue](https://github.com/EkkoG/ofs-next/blob/a131a090aa8425d7b2f1b6ec004eaafc79278e06/src/components/CustomBuild.vue)：rootfs_size_mb、repositories、repository_keys；公钥输入明确标为 usign。
- [CzBiX CustomBuild.vue](https://github.com/CzBiX/openwrt-firmware-selector/blob/2d5ff6d973b9b2e9533989cf3fb7c4216d53fb73/src/components/CustomBuild.vue)：rootfs_size_mb。
- 2026-10-30 读取 [当前 ASU OpenAPI](https://sysupgrade.openwrt.org/openapi.json)：rootfs_size_mb 为 1..1024 整数；repositories_mode 服务端默认 replace，支持显式 append。
- `ofs-next` 的默认构建地址为 `https://sysupgrade.kyarucloud.moe`，该第三方服务实时 OpenAPI 上限为 4096；其页面 2048 限制不能作为官方 ASU 的限制依据。CzBiX 默认官方 ASU，可由 `VITE_ASU_URL` 覆盖。
- 活跃笔记检索：此前不存在 `.agents/notes/`，无重叠或被取代的笔记。

## Alternatives considered

- 迁入参考项目的 Vue 组件：可复用丰富的界面与状态管理，但会引入框架和构建链；本次只有三个明确功能，保留原生模块更易维护。
- 沿用软件源只读部署配置：实现最少且便于站点控制，但用户仍无法在页面上自定义或删除预设，不能满足本次需求。
- 照搬参考页面的 2048 上限：有利于兼容部分私有服务，但当前配置服务明确只允许 1024，采用实际接口上限。

## Verification

- `node --test "tests/js/*.test.js"`：142 项通过，包含 15 项新增测试；覆盖大小边界/留空、追加/替换、占位符、多行公钥、重复名称/非法地址、预设移除、无效输入保留下载链接和轮询不重读表单。
- ESLint 与相关前端/测试文件通过格式检查。原有全量格式差异及后续配置冲突由[默认检查配置](../process/2026-10-30-default-checks.md)统一处理，当前 `npm run check` 可直接执行完整检查。
- Playwright 浏览器模拟完整设备数据和 ASU 响应，验证 3 次实际页面 POST：512 MiB + 追加 + 两份多行公钥、全部清空后字段省略、1024 MiB + 替换。配置初值、增删行、重复名称/非法地址拦截、中英文切换、375px 手机与 1280px 桌面布局通过，无 pageerror。
- 浏览器验证最初等待 option 可见导致脚本超时；改为等待机型处理器就绪后通过，未修改产品代码。所有 ASU POST 均由测试路由模拟，未占用官方构建队列。
- 项目使用 Node.js 24，可直接运行本地技能的三个 TypeScript 验证脚本，无需新增 tsx 依赖。

## Consequences

用户能直接编辑构建参数，页面与部署预设复用一套校验，保持静态部署方式。代价是新增表单和中英文文案需要维护；新增文案在其他语言中尚未翻译。

大小参数受目标平台的镜像布局约束，不会增加设备物理存储。服务选择、上限和对应目录由[构建服务选择](2026-10-30-asu-service-selection.md)约束。真实构建与实际镜像分区大小尚未验证，模拟请求不作为真实产物证据。replace 会覆盖构建服务已有软件源，页面明确说明该行为。
