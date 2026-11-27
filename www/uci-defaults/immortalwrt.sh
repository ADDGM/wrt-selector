#!/bin/sh
# ImmortalWrt first-boot configuration script
#
# On firmware with a read-only base and an overlay, the original stays in /rom/etc/uci-defaults/.
# After a successful run the script is hidden only in the current overlay; a factory reset runs it again.
# Passwords, Wi-Fi keys and PPPoE credentials entered here are sent to the online build service and remain in the firmware.
# Prefer setting credentials in LuCI after the first login. Uncomment only the settings you want to change.
#
# ==========================================
# Basic settings
# ==========================================
#
# Many x86 routers have no wireless hardware. Leave these settings blank to skip Wi-Fi.
# wlan_name="ImmortalWrt"
# wlan_password=""
#
# Leave blank to keep the root password. Avoid weak passwords such as password or 123456.
# root_password=""
#
# Leave the LAN address unchanged unless needed. Uncomment only the line for your version:
# 24.10 and earlier: use an IPv4 address and keep the existing netmask.
# lan_ip_address="192.168.10.1"
# 25.12 and later: use CIDR notation; /24 is equivalent to 255.255.255.0.
# lan_ip_address="192.168.10.1/24"
#
# Leave blank to keep the current WAN configuration. Devices using DHCP do not need these settings.
# pppoe_username=""
# pppoe_password=""

# ==========================================
# Logging
# ==========================================
# Write a fresh log to /tmp/setup.log, readable and writable only by root.
# ------------------------------------------
export LC_ALL=C
setup_log=$(mktemp /tmp/setup.log.XXXXXX) || exit 1
exec >"$setup_log" 2>&1
mv -fT "$setup_log" /tmp/setup.log || exit 1
log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
  logger -t immortalwrt-firstboot "$1" 2>/dev/null || :
}
fail() { log "Error: $1"; exit 1; }
log "Starting first-boot configuration"

# ==========================================
# Set the root password
# ==========================================
if [ -n "${root_password:-}" ]; then
  printf '%s\n%s\n' "$root_password" "$root_password" | passwd root >/dev/null 2>&1 || fail "Could not set the root password"
  log "Root password set"
fi

# ==========================================
# Configure the LAN address
# ==========================================
# More options: https://openwrt.org/docs/guide-user/base-system/basic-networking
# ------------------------------------------
if [ -n "${lan_ip_address:-}" ]; then
  if ! printf '%s\n' "$lan_ip_address" | awk -F '[./]' '
    /^[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+(\/[0-9]+)?$/ {
      ok = (NF == 4 || $5+0 <= 32)
      for (i = 1; i <= 4; i++) if (length($i) > 3 || $i+0 > 255) ok = 0
    }
    END { exit !(NR == 1 && ok) }'; then
    fail "Invalid LAN address: use an IPv4 address, optionally followed by a /0 to /32 prefix"
  fi
  uci -q get network.lan >/dev/null || fail "network.lan not found"
  uci set network.lan.ipaddr="$lan_ip_address" || fail "Could not set the LAN address"
  case "$lan_ip_address" in
    */*) if uci -q get network.lan.netmask >/dev/null; then
           uci -q delete network.lan.netmask || fail "Could not remove the old netmask"
         fi ;;
  esac
  uci commit network || fail "Could not save the LAN configuration"
  log "LAN address set to $lan_ip_address"
fi

# ==========================================
# Configure Wi-Fi (only the first radio and interface, as in the upstream example)
# ==========================================
# More options: https://openwrt.org/docs/guide-user/network/wifi/basic#wi-fi_interfaces
# ------------------------------------------
if [ -n "${wlan_name:-}" ] && [ -n "${wlan_password:-}" ]; then
  if [ "${#wlan_password}" -lt 8 ]; then
    log "Wi-Fi password is shorter than 8 bytes; skipping Wi-Fi"
  elif [ "${#wlan_name}" -gt 32 ] || [ "${#wlan_password}" -gt 63 ]; then
    log "SSID exceeds 32 bytes or password exceeds 63 bytes; skipping Wi-Fi"
  elif ! uci -q get 'wireless.@wifi-device[0]' >/dev/null || ! uci -q get 'wireless.@wifi-iface[0]' >/dev/null; then
    log "Wireless radio or interface not found; skipping Wi-Fi"
  else
    uci set "wireless.@wifi-iface[0].ssid=$wlan_name" &&
    uci -q set "wireless.@wifi-iface[0].key=$wlan_password" &&
    uci set 'wireless.@wifi-iface[0].encryption=psk2' &&
    uci set 'wireless.@wifi-iface[0].disabled=0' &&
    uci set 'wireless.@wifi-device[0].disabled=0' &&
    uci commit wireless || fail "Could not save the wireless configuration"
    log "Wi-Fi configured"
  fi
fi

# ==========================================
# Configure PPPoE
# ==========================================
# More options: https://openwrt.org/docs/guide-user/network/wan/wan_interface_protocols#protocol_pppoe_ppp_over_ethernet
# ------------------------------------------
if [ -n "${pppoe_username:-}" ] && [ -n "${pppoe_password:-}" ]; then
  uci -q get network.wan >/dev/null || fail "network.wan not found"
  uci -q set network.wan.username="$pppoe_username" &&
  uci -q set network.wan.password="$pppoe_password" &&
  uci set network.wan.proto='pppoe' &&
  uci commit network || fail "Could not save the PPPoE configuration"
  log "PPPoE configured"
fi

# ==========================================
# Personal settings: Simplified Chinese in LuCI and the Argon theme. No language packs or themes are installed.
# ==========================================
if uci -q get luci.main >/dev/null; then
  # Set the default LuCI language to Simplified Chinese.
  uci set luci.main.lang='zh_cn' || fail "Could not set the LuCI language"

  # Switch themes only if the Argon assets are present.
  if [ -d /www/luci-static/argon ]; then
    uci set luci.main.mediaurlbase='/luci-static/argon' || fail "Could not set the Argon theme"
  else
    log "Argon not found; keeping the current theme"
  fi

  # Save the language and theme in one commit.
  uci commit luci || fail "Could not save the LuCI configuration"
  log "LuCI configuration saved; default language set to Simplified Chinese"
else
  log "LuCI configuration not found; skipping language and theme settings"
fi

# ==========================================
# Personal settings: Shanghai time zone
# ==========================================
if uci -q get 'system.@system[0]' >/dev/null; then
  uci set 'system.@system[0].zonename=Asia/Shanghai' &&
  uci set 'system.@system[0].timezone=CST-8' &&
  uci commit system || fail "Could not save the time zone configuration"
  log "System time zone set to Asia/Shanghai"
else
  log "System configuration not found; skipping time zone settings"
fi

sync || fail "Could not flush changes to disk"
log "First-boot configuration complete"
