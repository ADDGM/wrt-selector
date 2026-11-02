# Using Wrt Selector

[简体中文](../zh-CN/usage.md) · [Home](../../README.md)

## Select and download

1. Open the [website](https://addgm.github.io/wrt-selector/).
2. Choose **Firmware distribution**, then one of its **Build services**.
3. Choose a version and search for your device. Select a matching suggestion.
4. Check the model, target and version before downloading an image. Use its description and the device's installation instructions to choose the correct image type.

The firmware source and **All Downloads** link follow the selected service. Version and device availability come from that source's metadata; a listed version does not guarantee that the build server can build it right now.

| Distribution | Build service | Configured root filesystem range |
| --- | --- | --- |
| OpenWrt | `sysupgrade.openwrt.org` | 1–1024 MiB |
| ImmortalWrt | `sysupgrade.immortalwrt.org` | 1–4096 MiB |
| ImmortalWrt | `sysupgrade.kyarucloud.moe` | 1–4096 MiB |

These are deployment settings, not live capability probes. Both ImmortalWrt services use ImmortalWrt metadata; they do not build OpenWrt revisions through this configuration.

## Customize an image

Open the customization area after selecting a device. Review the prefilled packages, edit the package list and, when needed, expand **Advanced build options**:

- **Root filesystem size**: leave empty for the device default, or enter a whole number within the displayed range. This changes the ImageBuilder root partition where the target supports it; it does not increase physical storage.
- **Custom software feeds**: provide a unique name and an HTTP(S) repository URL for each row. Depending on the package manager, this can be an opkg feed directory or an APK index such as `packages.adb`; follow the selected service's requirements. Empty rows are ignored; incomplete rows, duplicate names and invalid URLs prevent submission.
- **Feed mode**: **Append** preserves the ImageBuilder feeds. **Replace** uses only your feeds, so you must supply everything required by the selected packages.
- **Feed signing public keys**: add one complete public key per entry, keeping line breaks. These are feed verification keys, not TLS certificates or private keys. The server checks key formats and feed policies.

Click **Request build** to send the selected packages and options to the selected ASU server. The request also includes custom feed keys and the current first-boot script. Builds are performed by that external service; this website is its frontend.

Distribution, service, version and device controls are locked while a build is active. The request, status polling and resulting downloads remain attached to the service/device used at submission. Check the returned image details before flashing.

## First-boot scripts

The editor starts empty. **Insert example for this system** appends the selected distribution's example without rewriting your commands or inserting the same example twice. Review the example for your device and installed packages.

For both built-in examples, comments follow the interface language at insertion: Simplified Chinese (`zh-cn`) and Traditional Chinese (`zh-tw`) share the same Chinese comments; every other language uses English. Commands, sample values and runtime log messages stay the same. Changing the language leaves your draft untouched and cancels a pending insertion. To insert the other language, remove the existing example first; an intact example previously loaded in either language is not appended again.

Scripts are included in `/etc/uci-defaults/`. A script that returns success is removed; a nonzero result allows it to run again on a later boot. See the [OpenWrt UCI defaults guide](https://openwrt.org/docs/guide-developer/uci-defaults).

### ImmortalWrt example

The [ImmortalWrt template](../../www/uci-defaults/immortalwrt.sh) leaves all settings commented out. Uncomment and edit only what you need:

| Variables | Behavior |
| --- | --- |
| `root_password` | Set the root password; blank leaves it unchanged |
| `lan_ip_address` | Set an IPv4 address; CIDR removes an existing legacy netmask, while a bare address preserves it. Use CIDR for 25.12 and later |
| `wlan_name`, `wlan_password` | Configure the first radio/interface when both exist; use an SSID up to 32 bytes and a password of 8–63 bytes |
| `pppoe_username`, `pppoe_password` | Configure the existing WAN for PPPoE when both values are supplied |
| `luci_language`, `use_argon` | Optionally select a LuCI language and use Argon (`1`) if its files are already installed |
| `system_zonename`, `system_timezone` | Set both timezone values, for example `Asia/Shanghai` and `CST-8` |

Leave Wi-Fi variables unset on devices without wireless hardware. LuCI language/theme changes are saved together; missing LuCI or Argon is skipped. The template does not install themes, contact package servers or restart services. Requested setting failures return a nonzero status. Its logging runs in a subshell, so later custom commands keep their normal output; when appending more commands, preserve any failure status you want the complete script to return.

Logs are written to `/tmp/setup.log` with owner-only permissions and fixed status messages in the system log, without printing credentials. On read-only/overlay images, successful execution hides the script in the overlay while its original remains in `/rom`; a factory reset can run it again. Embedded passwords remain part of the firmware and are sent to the build service. Prefer setting credentials after first login.

The shared template does not preconfigure Cooluc or another third-party feed. Build-time feed settings and on-device feed settings serve different purposes; see [the configuration guide](configuration.md#build-time-and-on-device-feeds).

### Draft lifetime

Drafts are held only in the current page:

| Action | What happens |
| --- | --- |
| Switch OpenWrt ↔ ImmortalWrt | Save and restore a separate draft for each distribution |
| Switch between ImmortalWrt services | Keep the ImmortalWrt draft |
| Reload or leave the page | Clear all drafts |
| Share the selection link | Share the device/version/service, without the script draft |

Loading an example never replaces edits made while it is loading. A submitted build uses the draft captured at submission.

## Switch services and share selections

Switching distribution or service reloads its catalog and clears the selected device. Selecting another device prefills packages from that device and service. Advanced option edits remain in the page: check feed compatibility and the new size limit before building again.

Selection links include `asu=<service-id>`. The historical `asu=immortalwrt` ID selects **KyaruCloud**; `asu=immortalwrt-official` selects the **ImmortalWrt official** service. This compatibility is intentional. These IDs are unrelated to the GitHub repository name.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing device/version | Confirm the distribution and service, then check their firmware source |
| Catalog request fails | Read the displayed URL and HTTP status; metadata requests retry one transient failure, while build submissions do not retry automatically |
| Custom feed is rejected | Check package/architecture compatibility and the selected backend's current allow list |
| Size is rejected after switching service | Reduce it to the new limit or clear it |
| Draft disappears after reload | Drafts are intentionally not saved in browser storage; keep a separate copy if needed |
| `device_packages.json` is absent | This optional deployment file may be omitted; normal operation continues |

For website defects, [open an issue in Wrt Selector](https://github.com/ADDGM/wrt-selector/issues) with the service, device, version, error and reproduction steps. Remove credentials and private script content from reports.
