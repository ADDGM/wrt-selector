#!/bin/sh
# ImmortalWrt 首次启动示例。只取消需要项的注释，并修改相应设置。
# 留空或不设置的变量会保留设备现有配置。
# 使用只读镜像与 overlay 时，脚本原件会保留在 /rom/etc/uci-defaults/；
# 执行成功后仅在 overlay 中隐藏，恢复出厂设置可能再次执行。
# 脚本中的密码会发送给构建服务，并永久包含在固件中。
# 建议首次登录后再通过 LuCI 设置密码等凭据。
#
# root_password=""
# 24.10 及更早版本使用裸 IPv4 地址，保留现有网络掩码：
# lan_ip_address="192.168.10.1"
# 25.12 及之后请使用 CIDR；只有 CIDR 输入会移除旧网络掩码：
# lan_ip_address="192.168.10.1/24"
# 没有无线网卡的 x86 设备不需要配置无线网络。
# wlan_name="ImmortalWrt"
# wlan_password=""
# pppoe_username=""
# pppoe_password=""
# 可选：LuCI 语言、已安装的 Argon 主题和系统时区：
# luci_language="zh_cn"
# use_argon="1"
# system_zonename="Asia/Shanghai"
# system_timezone="CST-8"

# 追加到其他脚本时，将日志、辅助函数和退出状态限制在子 shell 内。
# 本示例不下载或安装软件包，也不重启服务。
(
  umask 077
  exec >/tmp/setup.log 2>&1
  chmod 0600 /tmp/setup.log || exit 1
  LC_ALL=C
  export LC_ALL
  iwrt_status=0

  iwrt_log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
    logger -t immortalwrt-firstboot "$1" 2>/dev/null || :
  }

  iwrt_error() {
    iwrt_status=1
    iwrt_log "ERROR: $1"
  }

  iwrt_ipv4() {
    case "$1" in ''|*[!0-9./]*) return 1 ;; esac
    awk -v address="$1" 'BEGIN {
      n = split(address, parts, "/")
      if (n > 2 || (n == 2 && (parts[2] !~ /^[0-9]+$/ || parts[2] > 32))) exit 1
      if (split(parts[1], octets, /\./) != 4) exit 1
      for (i = 1; i <= 4; i++)
        if (octets[i] !~ /^[0-9]+$/ || length(octets[i]) > 3 || octets[i] > 255) exit 1
    }'
  }

  iwrt_log "Starting ImmortalWrt first-boot settings"

  # 仅在已安装 LuCI 时配置语言和主题，并合并提交。
  if [ -n "${luci_language:-}" ] || [ "${use_argon:-0}" = "1" ]; then
    if uci -q get luci.main >/dev/null; then
      iwrt_luci_ok=1
      iwrt_luci_changed=0
      if [ -n "${luci_language:-}" ]; then
        uci -q set "luci.main.lang=$luci_language" || iwrt_luci_ok=0
        iwrt_luci_changed=1
      fi
      if [ "${use_argon:-0}" = "1" ]; then
        if [ -d /www/luci-static/argon ]; then
          uci -q set luci.main.mediaurlbase='/luci-static/argon' || iwrt_luci_ok=0
          iwrt_luci_changed=1
        else
          iwrt_log "Argon is not installed; keeping the current theme"
        fi
      fi
      if [ "$iwrt_luci_ok" = "0" ]; then
        iwrt_error "Could not set LuCI options"
      elif [ "$iwrt_luci_changed" = "1" ]; then
        if uci -q commit luci; then
          iwrt_log "LuCI options saved"
        else
          iwrt_error "Could not save LuCI options"
        fi
      fi
    else
      iwrt_log "LuCI is not installed; skipping language and theme"
    fi
  fi

  if [ -n "${system_zonename:-}" ] || [ -n "${system_timezone:-}" ]; then
    if [ -z "${system_zonename:-}" ] || [ -z "${system_timezone:-}" ]; then
      iwrt_error "Set both system_zonename and system_timezone"
    elif uci -q get 'system.@system[0]' >/dev/null &&
         uci -q set "system.@system[0].zonename=$system_zonename" &&
         uci -q set "system.@system[0].timezone=$system_timezone" &&
         uci -q commit system; then
      iwrt_log "System timezone saved"
    else
      iwrt_error "Could not configure the system timezone"
    fi
  fi

  if [ -n "${root_password:-}" ]; then
    if printf '%s\n%s\n' "$root_password" "$root_password" | passwd root >/dev/null 2>&1; then
      iwrt_log "Root password saved"
    else
      iwrt_error "Could not set the root password"
    fi
  fi

  if [ -n "${lan_ip_address:-}" ]; then
    if ! iwrt_ipv4 "$lan_ip_address"; then
      iwrt_error "LAN requires an IPv4 address with an optional /0 to /32 prefix"
    elif ! uci -q get network.lan >/dev/null; then
      iwrt_error "LAN interface not found"
    else
      iwrt_lan_ok=1
      uci -q set "network.lan.ipaddr=$lan_ip_address" || iwrt_lan_ok=0
      case "$lan_ip_address" in
        */*)
          if [ "$iwrt_lan_ok" = "1" ] && uci -q get network.lan.netmask >/dev/null; then
            uci -q delete network.lan.netmask || iwrt_lan_ok=0
          fi
          ;;
      esac
      if [ "$iwrt_lan_ok" = "1" ] && uci -q commit network; then
        iwrt_log "LAN address saved"
      else
        iwrt_error "Could not save LAN settings"
      fi
    fi
  fi

  if [ -n "${wlan_name:-}" ] || [ -n "${wlan_password:-}" ]; then
    if [ -z "${wlan_name:-}" ] || [ -z "${wlan_password:-}" ]; then
      iwrt_error "Set both wlan_name and wlan_password"
    elif [ "${#wlan_name}" -gt 32 ] || [ "${#wlan_password}" -lt 8 ] || [ "${#wlan_password}" -gt 63 ]; then
      iwrt_error "Wi-Fi needs an SSID of at most 32 bytes and a password of 8 to 63 bytes"
    elif uci -q get 'wireless.@wifi-device[0]' >/dev/null &&
         uci -q get 'wireless.@wifi-iface[0]' >/dev/null &&
         uci -q set 'wireless.@wifi-device[0].disabled=0' &&
         uci -q set 'wireless.@wifi-iface[0].disabled=0' &&
         uci -q set 'wireless.@wifi-iface[0].encryption=psk2' &&
         uci -q set "wireless.@wifi-iface[0].ssid=$wlan_name" >/dev/null 2>&1 &&
         uci -q set "wireless.@wifi-iface[0].key=$wlan_password" >/dev/null 2>&1 &&
         uci -q commit wireless; then
      iwrt_log "First wireless interface configured"
    else
      iwrt_error "Wireless interface missing or configuration failed"
    fi
  fi

  if [ -n "${pppoe_username:-}" ] || [ -n "${pppoe_password:-}" ]; then
    if [ -z "${pppoe_username:-}" ] || [ -z "${pppoe_password:-}" ]; then
      iwrt_error "Set both pppoe_username and pppoe_password"
    elif uci -q get network.wan >/dev/null &&
         uci -q set network.wan.proto=pppoe &&
         uci -q set "network.wan.username=$pppoe_username" >/dev/null 2>&1 &&
         uci -q set "network.wan.password=$pppoe_password" >/dev/null 2>&1 &&
         uci -q commit network; then
      iwrt_log "PPPoE settings saved"
    else
      iwrt_error "WAN interface missing or PPPoE configuration failed"
    fi
  fi

  sync || iwrt_error "Could not flush filesystem changes"
  if [ "$iwrt_status" = "0" ]; then
    iwrt_log "All requested first-boot settings completed"
  else
    iwrt_log "Some settings failed; uci-defaults may retry this script on the next boot"
  fi
  exit "$iwrt_status"
)
