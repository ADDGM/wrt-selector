# Development and upstream sync

[简体中文](../zh-CN/development.md) · [Home](../../README.md)

## Run locally

From the repository root:

```sh
python -m http.server 8000
```

Open [localhost:8000/www/](http://localhost:8000/www/). Serving `www/` requires no Node dependencies or bundling. To run code checks, use Node.js 22 or 24 and Yarn Classic 1.x, matching CI:

```sh
yarn install --frozen-lockfile
npm run check
```

The tracked `yarn.lock` is the dependency source of truth. `npm run` only invokes scripts; do not create a second lockfile with `npm install`. Local editor/agent/indexing tools are not website dependencies.

## Checks

| Command | Coverage |
| --- | --- |
| `npm run check` | ESLint, Prettier and JavaScript unit tests |
| `npm run lint` | Browser JavaScript lint |
| `npm run format:check` | Website formatting |
| `npm run test:unit` | JavaScript unit tests |
| `npm run test:coverage` | Unit tests with coverage |
| `python -B -m unittest discover -s tests/tooling -p "test_*.py" -v` | Build, release, commit-policy and mocked Telegram tests |
| `python scripts/check_commits.py` | Personal commit titles relative to the upstream mirror |

These everyday commands use repository configuration directly; no extra environment variables are required. ESLint uses `.eslintrc.json`. Prettier follows the upstream 2.x style: semicolons, double quotes, two spaces, 80 columns, ES5 trailing commas and LF. Translation JSON remains excluded by `.prettierignore`.

First-boot example tests use a POSIX `sh`; Git for Windows is detected automatically when needed. Router commands are mocked and file output stays in disposable temporary directories, so these tests do not change host or router settings.

### Browser tests

Use Python 3.11+ in an activated virtual environment and keep port 8000 available:

```sh
python -m pip install -r tests/requirements.txt
python -m playwright install firefox
python -m pytest tests/test_spa.py tests/test_services.py --simplehttpserver-directory ./
```

Tests load the real local page, configuration and script templates. Metadata and ASU responses are intercepted: the suite covers service selection, size limits, feeds/keys, scripts, retries and selection races without submitting real firmware builds. It does not prove that external build services are currently available. Contexts are created directly, so pytest-playwright's automatic tracing does not capture them. CI retains JUnit results and console logs.

Remove disposable test environments and generated preview packages after use. Keep regression-test source and evidence still needed for acceptance.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `www/` | Deployable website, configuration, translations and script templates |
| `www/js/` | Catalog, device selection, ASU options/requests and UI modules |
| `tests/js/` | JavaScript unit tests |
| `tests/tooling/` | Python workflow-tool tests |
| `tests/test_spa.py`, `tests/test_services.py` | Firefox regressions |
| `scripts/` | Site packaging, release notes, commit checks and Telegram client |
| `.github/workflows/project-*.yml` | This project's checks, deployment, release and notification |
| `docs/en/`, `docs/zh-CN/` | Paired public documentation |

## Branches and upstream

- `upstream` points to [OpenWrt's repository](https://github.com/openwrt/firmware-selector-openwrt-org).
- `origin` points to [ADDGM/wrt-selector](https://github.com/ADDGM/wrt-selector).
- `main` mirrors upstream `main`; it contains no personal changes.
- `develop` is the default branch for this project's development and integration.

Only integrate changes already merged into **upstream `main`**. An open upstream PR is not an update to merge early. Update the mirror first, then merge it into `develop` while preserving project changes. This is a maintenance policy, not an automatic sync service.

Use Conventional Commits with a Chinese summary, at most 72 characters, for example `fix(selector): 修复切换服务后的设备状态`. Existing upstream history, commits reachable from the upstream snapshot, real merge commits and supported dependency-bot commits are exempt from the Chinese-summary rule. CI checks PR commits using tools from the merged checkout, so a `main` → `develop` integration can use project scripts.

## Documentation and translations

Keep `README.md` / `README.zh-CN.md`, `CHANGELOG.md` / `CHANGELOG.zh-CN.md`, and same-named guides under both language folders in sync. Change behavior, commands, defaults and limitations in both languages in the same change. Version overviews may be prepared before publication; link to GitHub Releases for actual status and never claim a release is published before verifying it.

The browser retains upstream translations in `www/langs/`. Contribute this fork's UI and documentation changes through [its issues and pull requests](https://github.com/ADDGM/wrt-selector). Upstream's [Weblate project](https://hosted.weblate.org/projects/openwrt/firmware-wizard/) maintains upstream strings, not this fork's new behavior or documentation. Preserve the [CC0 license](../../LICENSE) and upstream attribution.
