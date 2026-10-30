# Agent Note: 保留原仓库风格并统一默认检查

Status: implemented

## Problem

新增 `.eslintrc.js` 优先于原 `.eslintrc.json`，引用本项目未安装且不需要的 Vue 插件，导致默认 ESLint 无法启动。新增 Prettier 配置使用无分号、单引号、100 列等不同风格，使 14 个网页文件未通过格式检查。此前只能用额外参数绕开配置，无法保证日常命令和 CI 一致。

本机 `core.autocrlf=true` 还会在检出时把原有 LF 转成 CRLF。恢复原有 Prettier 2 配置后，仅 autocomplete.js、translation.js、utils.js 的换行差异仍触发报错；只整理工作区不能防止下一次检出再次出现。

## Decision

用户确认保留原仓库代码风格，修复默认检查配置。

- 删除重复的 `.eslintrc.js`，以原 `.eslintrc.json` 为唯一 ESLint 配置，增加 `root: true` 限定规则继承边界。沿用浏览器环境、ES2020 模块语法及 `www/config.js` 的脚本例外。
- `prettier.config.cjs` 显式记录原 Prettier 2 默认风格：分号、双引号、2 空格、80 列、ES5 尾逗号和 LF。原有翻译 JSON 排除规则继续适用。
- `.gitattributes` 只对 `www/` 下的 JavaScript、CSS、HTML 指定 `text eol=lf`，使 Windows 检出结果与格式检查一致。图片等其他资源不匹配这些规则。
- `package.json` 提供 `lint`、`format:check` 与组合 `check`，后者依次运行 ESLint、Prettier 和现有 JavaScript 单测。README 给出不需要环境变量或替代配置参数的日常命令。
- CI 使用同一组检查脚本，并将 ESLint、Prettier、Git 换行配置、package.json 和 yarn.lock 纳入触发路径。单测覆盖率与 Firefox 测试继续使用既有步骤。

## Alternatives considered

- 继续使用 `--no-eslintrc` 与 `--no-config`：能立即完成单次验证，但默认命令与 CI 仍失败，后续维护者还需记住绕过参数。
- 安装 Vue 插件使错误消失：可以满足现有引用，却给原生 JavaScript 页面引入不相关的规则和依赖，不能解决格式风格冲突。
- 按新增 Prettier 配置重排全项目：能统一格式，但会改变原有代码风格；用户明确选择保留原风格。
- 使用 `endOfLine: auto` 或修改全局 Git 设置：前者允许不同检出使用不同换行，后者影响其他仓库。采用项目内精确的 Git 属性固定受检查源码的 LF。

## Verification

- `npm run check` 通过：默认 ESLint、全量 `www/` 格式检查和 现有 JavaScript 单测全部通过。
- 三个整理文件的语法树去除位置与原始字面量格式后，与修改前 SHA-256 完全一致；Git 内容 diff 也无逻辑差异，变化仅为工作区换行。
- `git check-attr` 验证根目录 config.js 与嵌套 JS、CSS、HTML 均使用 LF，logo.svg 和 favicon.ico 未匹配；`git ls-files --eol` 确认受检查的已跟踪文件在索引与工作区均为 LF。
- CI 使用的 `yarn run lint` 与 `yarn run format:check` 均通过；YAML 解析、两个事件的配置触发路径及 package 脚本引用检查通过。

## Consequences

本地和 CI 复用检查入口，原生页面继续保持原风格，消除了额外绕过配置参数。Git 属性使受检查源码固定使用 LF；新增格式规则或检查范围时，维护者需同步调整配置、Git 属性与触发路径。

本次只修改检查工具及换行，不改变页面行为或依赖版本。此前 7 项 Firefox 测试通过的功能基线继续适用；本次不重新安装浏览器环境。云端 CI 尚未触发，不能将本地通过等同于已发布或已完成远端流水线。
