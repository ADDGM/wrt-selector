Wrt Selector `site-v1.1.0` helps OpenWrt and ImmortalWrt users answer two questions: which image to download, and what the device will change on first boot if you include the `uci-defaults` example. This is a release of the selector website, not router firmware.

[Use online](https://addgm.github.io/wrt-selector/) · [Usage guide](../en/usage.md)

## Highlights

- **Whole-disk images and root filesystems.** On x86, choose `COMBINED` for legacy BIOS boot or `COMBINED-EFI` for UEFI boot. A standalone `ROOTFS` cannot boot on its own. Choose it only when deploying a separate root partition with a matching kernel. When the selector can identify the format, it explains that ext4 is directly writable, while a SquashFS base system is read-only and normally stores configuration changes in a writable overlay.
- **First installation, upgrades and recovery.** The Factory and Sysupgrade descriptions distinguish installing from vendor firmware from upgrading an existing compatible system. An `initramfs` recovery image can boot temporarily in RAM without installing the system to flash. The selector recognizes `zImage` and `uImage` as kernels and explains how to match flash capacity or regional suffixes on Broadcom BCM63xx CFE images. It does not recommend an unrecognized file as a generic LuCI upgrade image.
- **First-boot examples use one language for comments, logs and errors.** When you insert the example, the Simplified and Traditional Chinese interfaces share the selected distribution’s Chinese script. Every other interface language defaults to its English script. Switching languages leaves your draft intact. The interface language menu also adds Azerbaijani from upstream.

## Requirements

Use a modern browser with JavaScript enabled and network access to the selected distribution’s download catalogue. Custom firmware builds also require access to the selected online build service. Self-hosting requires only a static HTTP(S) server, not Node.js or a firmware toolchain.

## Usage and deployment

1. **Check the model and hardware revision before downloading.** Writing a raw `.img` to a physical disk overwrites its partitions. Attach virtual disk files to a VM instead. Follow the installation guide for the exact device.
2. **Review the script before requesting a build.** The editor starts empty. If you include the built-in example unchanged, it sets LuCI to Simplified Chinese and the system time zone to `Asia/Shanghai` on first boot when the respective configurations exist. It switches to Argon only if already installed; it installs neither the theme nor a language pack. **The English script applies the same settings.** To preserve the device’s language or time zone, remove the corresponding section before requesting the build. The example leaves the root password, Wi-Fi, PPPoE and LAN address unchanged by default; `192.168.10.1` and `192.168.10.1/24` are both commented out.
3. **Self-hosted upgrades from `site-v1.0.1` need no configuration-format migration.** Back up your custom `config.js` and first-boot templates. Verify the website ZIP against its SHA-256 checksum, extract its contents to the web root, then merge your changes and refresh cached assets. Updating the website does not change devices already deployed. See the [configuration guide](../en/configuration.md) and [deployment guide](../en/deployment.md).

## Known limitations

- Image descriptions cannot verify device compatibility. If a specific translation is missing, the selector shows generic guidance in the current language, or just the image type if neither translation exists. Automated checks do not replace flashing and first-boot tests on the actual hardware.
- Root passwords, Wi-Fi keys and PPPoE credentials written into a first-boot script are sent to the online build service and remain in the firmware. Set them in LuCI after the first login instead, and do not distribute firmware containing personal credentials.

## Acknowledgements

Thanks to the [OpenWrt Firmware Selector](https://github.com/openwrt/firmware-selector-openwrt-org) project and its translators, and to the [ImmortalWrt Firmware Selector](https://github.com/immortalwrt/firmware-selector-immortalwrt-org) project for its first-boot example. ADDGM maintains Wrt Selector independently. See the [full acknowledgements](../en/acknowledgements.md) and the [CC0 1.0 license](../../LICENSE).
