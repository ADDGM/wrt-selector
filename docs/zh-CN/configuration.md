# 部署配置

[English](../en/configuration.md) · [返回首页](../../README.zh-CN.md)

部署前编辑 [`www/config.js`](../../www/config.js)。网站使用原生 HTML/CSS/JavaScript，无需前端编译。配置会公开发送给浏览器；Telegram 凭证只能放在 GitHub Actions Secrets，不能写在这里。

## 系统与构建服务

`asu_services` 按 `distribution` 字符串对服务分组。每个服务必须使用所属系统对应的固件元数据和下载源。

```javascript
asu_services: [
  {
    id: "openwrt",
    distribution: "OpenWrt",
    name: "OpenWrt (official)",
    url: "https://sysupgrade.openwrt.org",
    image_url: "https://downloads.openwrt.org",
    rootfs_size_mb_max: 1024,
  },
],
```

这是现有 `config` 对象的片段。仓库已配置 OpenWrt 官方、ImmortalWrt 官方和 ImmortalWrt KyaruCloud 服务，请保留需要的条目。

| 字段 | 含义 |
| --- | --- |
| `id` | 唯一且稳定的服务标识，用于 `asu` 分享参数 |
| `distribution` | 系统显示名、分组名，也是首次启动草稿和模板的键 |
| `name` | 服务显示名 |
| `url` | ASU 基础地址 |
| `image_url` | 匹配的固件元数据和下载基础地址 |
| `rootfs_size_mb_max` | 表单允许的大小上限 |
| `versions`、`default_version` | 可选，覆盖固件源版本索引 |
| `show_snapshots` | 是否在目录中加入快照版本 |
| `info_url` | 可选，覆盖设备信息链接 |
| `asu_extra_packages` | 覆盖全局额外软件包，`[]` 表示不添加 |

服务基础地址必须是 HTTP(S)，不能包含凭证、查询参数或片段。没有有效 `asu` 分享参数时，`asu_url` 决定初始服务。切换系统时选中该组配置的默认服务，或该组第一个服务。

兼容 ID `immortalwrt` 代表 KyaruCloud，`immortalwrt-official` 代表 ImmortalWrt 官方服务。仅修改显示名时不要变更 ID。两者当前都使用 `https://downloads.immortalwrt.org`，并将额外软件包覆盖为空；OpenWrt 使用全局默认的 `luci` 和 `luci-app-attendedsysupgrade`。

不配置 `asu_services` 时仍兼容单服务字段：`asu_url`、`image_url`、`versions`、`default_version`，以及可选的 `asu_rootfs_size_mb_max`（默认 1024）。服务未指定系统时继承顶层 `distribution`，再回退到 `OpenWrt`；增加其他系统时请明确填写。

## 构建默认值

| 配置 | 默认值或行为 |
| --- | --- |
| `asu_rootfs_size_mb` | 可选的初始大小，留空采用设备默认值 |
| `asu_repositories` | 软件源名称到仓库 URL 的映射，按后端要求使用 opkg 目录或 APK 索引 |
| `asu_repositories_mode` | 默认 `append`，`replace` 只使用填写的软件源 |
| `asu_repository_keys` | 完整软件源签名公钥列表 |
| `asu_extra_packages` | 额外软件包，可被单服务配置覆盖 |

软件源 URL 支持 `{openwrt_branch}`、`{openwrt_version}`、`{target}`、`{subtarget}`。例如版本 `24.10.3`、目标 `ramips/mt7621` 会分别解析为 `24.10`、`24.10.3`、`ramips`、`mt7621`。使用 ImmortalWrt 时也沿用这些占位符名称。

表单由这些值初始化。在页面中删除预设行后，后续请求不再包含该行；刷新页面恢复部署默认值。只有存在自定义软件源时才发送模式字段。最终接受哪些软件源和公钥由所选后端决定，允许列表和构建可用性可能独立于本站变化。

## 构建阶段与设备运行时的软件源

页面把 `repositories`、`repositories_mode` 和 `repository_keys` 发送给 ASU。[已核对的 ASU 实现](https://github.com/openwrt/asu/blob/77c5636045b0aed0762727363be105b2a5fa47fd/asu/build.py#L98)把自定义公钥和源文件注入 **ImageBuilder 目录**，这不能证明它们也会成为刷机后设备的包管理器配置。首次启动脚本写入 `/etc/apk/repositories.d/`、`/etc/apk/keys/` 则用于**设备后续安装软件**，不能为此前的固件构建提供软件包。

API 支持字段，也不代表接受任意软件源。2026-11-03 核验时，OpenWrt 官方提供上述三个字段，但 `server.repository_allow_list` 为空；按[已核对的允许列表实现](https://github.com/openwrt/asu/blob/77c5636045b0aed0762727363be105b2a5fa47fd/asu/repositories.py#L6)，空名单不放行自定义软件源。ImmortalWrt 官方与 KyaruCloud 的元数据查询返回 HTTP 403，因此当前策略尚未核实。本次检查没有提交固件构建。

需要在构建时加入软件包，应使用后端允许的软件源。需要刷机后再安装时，应另行配置设备，或先核验后端产物是否已经包含所需源和公钥。ImmortalWrt 通用示例不内嵌 Cooluc 默认配置：APK 的 `openwrt-25.12` 源不能通用于 opkg 或其他版本，脱敏公钥和哈希占位符也不能作为可信依据，不应通过关闭签名校验让占位配置生效。

## 按设备追加软件包

将 [`www/device_packages.json.example`](../../www/device_packages.json.example) 复制为 `www/device_packages.json`，按设备 profile ID 配置软件包列表。文件缺失或无效时会忽略。首个逗号/下划线分隔符会尝试两种写法，因此 `tplink,archer-c7-v5` 可以匹配 `tplink_archer-c7-v5`。

预填顺序为：镜像默认包、profile 的 `device_packages`、当前服务生效的 `asu_extra_packages`、该可选映射。映射跨系统生效，请填写目标系统可用的软件包。需要打入 Release ZIP 时，必须将文件纳入 Git 跟踪。

## 首次启动模板

`uci_defaults_templates` 将系统名映射到单个模板 URL，或包含英文、简体中文 URL 的对象：

```javascript
uci_defaults_templates: {
  OpenWrt: {
    en: "uci-defaults/setup.sh",
    "zh-cn": "uci-defaults/setup.zh-cn.sh",
  },
  ImmortalWrt: {
    en: "uci-defaults/immortalwrt.sh",
    "zh-cn": "uci-defaults/immortalwrt.zh-cn.sh",
  },
},
```

键必须与 `asu_services` 的系统名完全一致。未配置的系统回退到模板按钮的 `data-link`。模板只在用户主动插入示例时加载，不自动预填或持久化草稿，详见[草稿行为](usage.md#首次启动脚本)。

`zh-cn` 和 `zh-tw` 界面都选择 `zh-cn` 键对应的中文 URL，其他语言都选择 `en`。缺少中文 URL 时回退到 `en`，无可用映射时再回退到 `data-link`。旧的单 URL 配置仍适用于所有语言。切换界面语言不会翻译或替换已有草稿。维护多语言模板时，只翻译注释，执行命令、示例赋值和日志文本需保持一致。

## 自行托管固件元数据

部署选择器不要求自行镜像固件或运行 ASU。需要使用自建固件源时，按 OpenWrt 下载目录结构提供元数据和镜像，并配置对应 `image_url`：

```text
<image_url>/.versions.json
<image_url>/releases/<version>/.overview.json
<image_url>/releases/<version>/targets/<target>/<subtarget>/profiles.json
<image_url>/releases/<version>/targets/<target>/<subtarget>/<image-file>
```

可选的 `.versions.json` 提供 `stable_version` 和 `versions_list`，也可由显式 `versions`、`default_version` 覆盖。版本目录下的 `.overview.json` 汇总设备，目标目录中的 `profiles.json` 提供镜像详情。编译固件时，在 `make menuconfig` 启用 **Global build settings → Create JSON info files per build image** 生成 JSON。

已有版本目录可在安装了 `find`、`jq` 的 POSIX shell 中生成索引：

```sh
VERSION_PATH="releases/24.10.3"
find "$VERSION_PATH" -iname profiles.json -exec cat {} + |
  jq -s '{release: .[0].version_number, profiles: [.[] | .target as $target | .profiles | to_entries[] | {id: .key, titles: .value.titles, target: $target}]}' > "$VERSION_PATH/.overview.json"
```

请换成实际存在且包含 `profiles.json` 的版本目录。跨域固件源需要适当的 CORS 响应头供浏览器访问；快照源需要对应的 snapshot 目录结构。元数据格式兼容，并不等于已经具备可用的 ImageBuilder/ASU 后端。
