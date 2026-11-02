# Deployment, releases and notifications

[简体中文](../zh-CN/deployment.md) · [Home](../../README.md)

## Static hosting

Serve the contents of `www/` using any static web server, or extract a release ZIP into its document root. `index.html` must be at the deployed root. Configure services in [`config.js`](configuration.md) before deployment. A custom domain's `CNAME` must be tracked under `www/` to enter the package.

**Release ZIPs contain the selector website, not router firmware.** Firmware downloads and custom builds are provided by the selected external service. Deploying this site does not submit ASU builds.

## Build a site package

With Python 3.11+ and Git available, run from the repository root:

```sh
python scripts/build_site.py
```

The output includes:

| Path | Contents |
| --- | --- |
| `build/site/` | Extracted deployable site |
| `build/firmware-selector-<version>.zip` | Site ZIP |
| `build/firmware-selector-<version>.zip.sha256` | SHA256 checksum |
| `build/build-info.json` | Version, source SHA, source date and dirty flag |

The generic `firmware-selector-` artifact prefix is retained across the Wrt Selector rename. Version detection uses personal `site-v*` tags, falling back to the short commit SHA. `--version site-v1.0.0` sets a preview version; it does not create a tag or publish a release.

Only Git-tracked `www/` files, the license and build information enter the ZIP. Configuration is preserved; the version placeholder is replaced only in the output. Tracked local site changes enter a preview and set `source_dirty`; formal releases require clean tagged site source. Untracked deployment files must be added to Git first. Identical source, version and build environment produce the same ZIP. Rebuilding replaces the tool-owned `build/site/`; keep manual work elsewhere and remove disposable previews after use.

## Workflow responsibilities

| Workflow | Trigger | Result |
| --- | --- | --- |
| `project-pages.yml` | Push to `develop`, or manual on `develop` | Verify source, call quality/tests, deploy their package, notify |
| `project-ci.yml` | PR targeting `develop`, manual or reusable call | Node 22/24, Python tools, HTML and Firefox tests, then `website-package` |
| `project-quality.yml` | PR targeting `develop`, manual or reusable call | Commit policy, actionlint and Semgrep |
| `project-release.yml` | Push a `site-v*` tag, or manual with an existing tag | Resolve source, call quality/tests, create Release, notify |
| `project-notify.yml` | Reusable call from Pages or Release only | One attempt to send the combined result |

Pages owns `develop` push checks; CI and quality do not also listen to pushes. PRs check changes without deploying. HTML checks skip external availability; Semgrep uses remote rules, and findings or scan errors fail quality. SARIF is saved as an artifact without requiring Code Scanning write permission. Dependencies install with `yarn install --frozen-lockfile`.

The upstream `test.yml`, `static-main.yml` and `static-stable.yml` remain upstream files and must stay **disabled in the fork's Actions settings**. Review newly introduced upstream workflows during sync. Personal workflows use `project-*` filenames; no `RSYNC_USER` or `RSYNC_PASSWORD` is needed.

## GitHub Pages

Set the fork's default branch to `develop`. In **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**. Allow only `develop` in the `github-pages` environment deployment rules.

Pushing `develop` runs the checks and deploys the ZIP from the same run and source SHA. Failed checks leave the previous deployment intact. Manual deployment also requires `develop`; `main`, other branches, tags and PRs do not deploy. Runs for the same branch are serialized; active runs continue, while a newer queued run can replace an older pending run.

The repository's destination is [ADDGM/wrt-selector](https://github.com/ADDGM/wrt-selector), with the default Pages URL [https://addgm.github.io/wrt-selector/](https://addgm.github.io/wrt-selector/). When renaming a repository, update its About homepage and local `origin`, then redeploy and verify the new URL. GitHub redirects repository links but **does not redirect old project Pages URLs**. Keep `upstream` pointed at OpenWrt. See [GitHub's rename documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository).

## Formal releases

Personal versions use `site-vX.Y.Z`, `site-vX.Y.Z-beta.N` or `site-vX.Y.Z-rc.N`. Upstream `v*` tags are not personal releases. A release tag must contain project workflows/scripts and point to personal source already integrated into `develop`, not a pure upstream commit. Push only the intended tag, not every upstream tag.

Pushing a valid tag triggers the release workflow; the manual entry accepts an existing tag. Tests and quality run before ZIP, checksum and build information are published. Beta/RC versions are prereleases and not latest. Existing releases are never overwritten. After an interrupted run, inspect the release before retrying, and do not move a published tag.

The release tool groups personal commits since the previous reachable `site-v` tag and excludes a fixed upstream snapshot. Generated commit details currently retain Chinese commit summaries. English and Chinese user-facing version summaries are maintained in [the changelog](../../CHANGELOG.md) and [中文更新记录](../../CHANGELOG.zh-CN.md). Write access is limited to the publish job using `GITHUB_TOKEN`.

## Telegram

In **Settings → Secrets and variables → Actions → Secrets**, configure:

| Secret | Value |
| --- | --- |
| `TELEGRAM_TOKEN` | Bot token |
| `TELEGRAM_TO` | Target chat ID or channel username |

The bot must be allowed to send messages to that target. Pages summarizes source verification, quality, tests/package and deployment; Release summarizes tag/source verification, quality, tests/package and publication. Messages show success, failure, cancellation or skipped work, the source SHA and Actions link. Successful runs also include the site/release link. Standalone checks and PRs do not notify.

Missing secrets produce an explicit skip. Delivery errors are logged without changing the original workflow result. The client uses plain text, a 20-second timeout and no automatic retry, avoiding duplicate sends after ambiguous timeouts. It does not log tokens, chat IDs or raw error responses. Only Telegram `ok: true` confirms API acceptance, not that a recipient read the message.

Cancellation notification is best effort; platform force-termination can prevent it. Manual reruns may send another message. Secret names being present does not validate credentials or chat permissions. Local tests use mocks and never contact Telegram:

```sh
python -B -m unittest discover -s tests/tooling -p "test_notify_telegram.py" -v
```
