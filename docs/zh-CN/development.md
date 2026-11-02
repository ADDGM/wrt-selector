# 开发与上游同步

[English](../en/development.md) · [返回首页](../../README.zh-CN.md)

## 本地运行

在仓库根目录执行：

```sh
python -m http.server 8000
```

打开 [localhost:8000/www/](http://localhost:8000/www/)。直接运行 `www/` 不需要 Node 依赖或前端打包。执行代码检查时使用与 CI 一致的 Node.js 22 或 24、Yarn Classic 1.x：

```sh
yarn install --frozen-lockfile
npm run check
```

依赖以已跟踪的 `yarn.lock` 为准。`npm run` 只调用脚本，不要通过 `npm install` 生成第二份锁文件。本机编辑器、Agent 和代码索引工具不属于网站依赖。

## 检查命令

| 命令 | 覆盖范围 |
| --- | --- |
| `npm run check` | ESLint、Prettier 和 JavaScript 单元测试 |
| `npm run lint` | 浏览器 JavaScript 检查 |
| `npm run format:check` | 网站格式检查 |
| `npm run test:unit` | JavaScript 单元测试 |
| `npm run test:coverage` | 单元测试与覆盖率 |
| `python -B -m unittest discover -s tests/tooling -p "test_*.py" -v` | 构建、发版、提交规范及 Telegram 模拟测试 |
| `python scripts/check_commits.py` | 相对上游镜像的个人提交标题 |

日常命令直接使用仓库配置，无需附加环境变量。ESLint 使用 `.eslintrc.json`；Prettier 保持上游 2.x 风格：分号、双引号、2 空格、80 列、ES5 尾逗号与 LF。翻译 JSON 沿用 `.prettierignore` 排除规则。

首次启动示例测试使用 POSIX `sh`，需要时会自动识别 Git for Windows。路由器命令均为模拟，文件输出只进入可清理的临时目录，不会修改主机或路由器设置。

### 浏览器回归

使用 Python 3.11+，激活虚拟环境，并保持 8000 端口可用：

```sh
python -m pip install -r tests/requirements.txt
python -m playwright install firefox
python -m pytest tests/test_spa.py tests/test_services.py --simplehttpserver-directory ./
```

测试加载真实本地页面、配置和脚本模板，并拦截元数据及 ASU 响应，覆盖服务选择、容量限制、软件源与公钥、脚本、重试和设备选择竞态，不提交真实固件构建。它不能证明外部服务此刻可用。用例自行创建 context，因此 pytest-playwright 自动 tracing 不会捕获这些 context；CI 保留 JUnit 结果和控制台日志。

临时测试环境和预览包使用完成后应清理，回归测试源码和仍待验收的证据应保留。

## 仓库结构

| 路径 | 职责 |
| --- | --- |
| `www/` | 可部署网站、配置、翻译及脚本模板 |
| `www/js/` | 目录、设备选择、ASU 选项/请求和界面模块 |
| `tests/js/` | JavaScript 单元测试 |
| `tests/tooling/` | Python 工作流工具测试 |
| `tests/test_spa.py`、`tests/test_services.py` | Firefox 回归 |
| `scripts/` | 网站打包、发布说明、提交检查及 Telegram 客户端 |
| `.github/workflows/project-*.yml` | 本项目检查、部署、发版和通知 |
| `docs/en/`、`docs/zh-CN/` | 对应的公开双语文档 |

## 分支与上游

- `upstream` 指向 [OpenWrt 官方仓库](https://github.com/openwrt/firmware-selector-openwrt-org)。
- `origin` 指向 [ADDGM/wrt-selector](https://github.com/ADDGM/wrt-selector)。
- `main` 镜像上游 `main`，不放个人改动。
- `develop` 是本项目默认分支，用于二次开发和集成。

只同步**已经合入上游 `main`** 的变更，不提前纳入尚未合并的 PR。先更新镜像，再合入 `develop` 并保留个人修改。这是维护约定，不是后台自动同步服务。

个人提交使用 Conventional Commits 前缀与中文说明，标题最多 72 个字符，例如 `fix(selector): 修复切换服务后的设备状态`。初始上游历史、当前上游快照可达的提交、真实合并提交及支持的依赖机器人提交不强制中文。CI 用 PR 合并结果中的工具检查 PR 提交，因此 `main` → `develop` 的集成也能运行个人脚本。

## 文档与翻译维护

同步维护 `README.md` / `README.zh-CN.md`、`CHANGELOG.md` / `CHANGELOG.zh-CN.md`，以及两种语言目录下的同名指南。行为、命令、默认值和限制在同一批改动中同步两种语言；可以提前准备版本摘要，但实际发布状态应链接到 GitHub Releases，远端验证前不能宣称已经发布。

浏览器继续保留 `www/langs/` 中的上游翻译。本分支界面及文档变更请通过[本项目 Issues 与 Pull Requests](https://github.com/ADDGM/wrt-selector)提交；上游 [Weblate](https://hosted.weblate.org/projects/openwrt/firmware-wizard/) 维护上游词条，不维护本分支新增行为或文档。保留 [CC0 许可证](../../LICENSE)及上游来源说明。
