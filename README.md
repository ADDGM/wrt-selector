<img src="www/logo.svg" width="64" height="64" alt="" />

# Wrt Selector

[简体中文](README.zh-CN.md) | English

**Select and customize OpenWrt and ImmortalWrt firmware in one place.**

Wrt Selector is a static web frontend maintained by ADDGM, based on the
[OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org).
It adds distribution and build-service selection, editable build options and
separate first-boot script drafts for each distribution.

[Open the website](https://addgm.github.io/wrt-selector/) ·
[Releases](https://github.com/ADDGM/wrt-selector/releases) ·
[Report an issue](https://github.com/ADDGM/wrt-selector/issues)

## What it provides

- **Two distributions, three services:** OpenWrt official, ImmortalWrt official and ImmortalWrt KyaruCloud, each using its matching firmware catalog.
- **Device and version selection:** search by model, inspect image details, follow the correct download source and share a selection link.
- **Custom firmware requests:** edit packages, root filesystem size, software feeds and signing public keys before submitting to ASU.
- **First-boot scripts:** insert a system-specific example and keep separate OpenWrt/ImmortalWrt drafts while the page remains open.
- **Responsive interface:** desktop/mobile layouts, light/dark styling and the inherited browser language selector.
- **Deployable website packages:** checked ZIP releases, GitHub Pages deployment and optional Telegram workflow summaries.

The website delegates firmware builds to the selected external ASU service.
A Wrt Selector release ZIP contains **the website**, not router firmware.
Device support, accepted feeds and build availability depend on that service.

## Quick start

Use the hosted website for normal operation. To run your own copy:

```sh
git clone https://github.com/ADDGM/wrt-selector.git
cd wrt-selector
python -m http.server 8000
```

Open [http://localhost:8000/www/](http://localhost:8000/www/).
Python 3 is sufficient to serve the site; there is no frontend build step.
Edit [www/config.js](www/config.js) to configure your deployment.

## Documentation

| Guide | Contents |
| --- | --- |
| [Usage](docs/en/usage.md) | Downloads, custom builds, scripts, sharing and troubleshooting |
| [Configuration](docs/en/configuration.md) | Services, packages, feeds, templates and custom metadata sources |
| [Development](docs/en/development.md) | Local checks, browser tests, source layout and upstream integration |
| [Deployment and releases](docs/en/deployment.md) | Static hosting, ZIPs, GitHub Actions, Pages and Telegram |
| [Changelog](CHANGELOG.md) | This project's version summaries and preserved upstream history |
| [Acknowledgements](docs/en/acknowledgements.md) | Upstream projects, implementation references and service operators |

Chinese equivalents are available from each page's language link.
The personal version series starts at **`site-v1.0.0`**. Check the
[Releases page](https://github.com/ADDGM/wrt-selector/releases) for publication status and downloads.
Personal `site-v*` versions are separate from upstream `v*` versions.

## Development

Use Node.js 22/24 and Yarn Classic 1.x for checks:

```sh
yarn install --frozen-lockfile
npm run check
python -B -m unittest discover -s tests/tooling -p "test_*.py" -v
```

`develop` is the project default branch. `main` mirrors upstream;
only updates already merged into upstream `main` are integrated.
See the [development guide](docs/en/development.md) before contributing.

## Upstream and license

This is an independently maintained derivative, not the official OpenWrt or
ImmortalWrt selector. Thanks to the OpenWrt Firmware Selector contributors,
ImmortalWrt and the ASU service operators. Upstream translations and history
are retained; the upstream demo does not include this fork's extensions.

The project retains the upstream [CC0 1.0 Universal license](LICENSE).
See [Acknowledgements](docs/en/acknowledgements.md) for the specific projects and services referenced.
