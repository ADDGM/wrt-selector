#!/bin/sh
# OpenWrt 首次启动配置脚本
#
# 在使用只读层和 overlay 的固件中，原件保留在 /rom/etc/uci-defaults/。
# 执行成功后只在当前 overlay 中隐藏；恢复出厂设置后会再次执行。
# 这里填写的密码、Wi-Fi 密钥和 PPPoE 凭据会发给在线构建服务，也会留在固件中。
# 建议首次登录后通过 LuCI 设置。需要自定义时，再取消下面对应行的注释。
#
# ==========================================
# 用户自定义基础变量
# ==========================================
#
# x86 软路由通常没有无线网卡，留空即不配置无线。
# wlan_name="OpenWrt"
# wlan_password=""
#
# 留空表示不修改 root 密码。不要使用 password、123456 等弱密码。
# root_password=""
#
# LAN 地址默认不改。需要修改时，按版本只启用一行：
# 24.10 及更早版本：使用 IPv4 地址，保留原有网络掩码。
# lan_ip_address="192.168.10.1"
# 25.12 及之后：使用 CIDR 表示法，/24 相当于 255.255.255.0。
# lan_ip_address="192.168.10.1/24"
#
# 留空即保留现有 WAN 配置；使用 DHCP 的设备无需填写。
# pppoe_username=""
# pppoe_password=""

# ==========================================
# 日志初始化
# ==========================================
# 记录到 /tmp/setup.log；每次新建仅 root 可读写的日志。
# ------------------------------------------
export LC_ALL=C
setup_log=$(mktemp /tmp/setup.log.XXXXXX) || exit 1
exec >"$setup_log" 2>&1
mv -fT "$setup_log" /tmp/setup.log || exit 1
log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
  logger -t openwrt-firstboot "$1" 2>/dev/null || :
}
fail() { log "错误：$1"; exit 1; }
log "开始执行首次启动配置"

# ==========================================
# 设置 root 密码
# ==========================================
if [ -n "${root_password:-}" ]; then
  printf '%s\n%s\n' "$root_password" "$root_password" | passwd root >/dev/null 2>&1 || fail "root 密码设置失败"
  log "root 密码设置成功"
fi

# ==========================================
# 配置 LAN 地址
# ==========================================
# 更多选项: https://openwrt.org/docs/guide-user/base-system/basic-networking
# ------------------------------------------
if [ -n "${lan_ip_address:-}" ]; then
  if ! printf '%s\n' "$lan_ip_address" | awk -F '[./]' '
    /^[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+(\/[0-9]+)?$/ {
      ok = (NF == 4 || $5+0 <= 32)
      for (i = 1; i <= 4; i++) if (length($i) > 3 || $i+0 > 255) ok = 0
    }
    END { exit !(NR == 1 && ok) }'; then
    fail "LAN 地址无效：请填写 IPv4 地址，可附带 /0 至 /32 前缀"
  fi
  uci -q get network.lan >/dev/null || fail "未找到 network.lan"
  uci set network.lan.ipaddr="$lan_ip_address" || fail "无法设置 LAN 地址"
  case "$lan_ip_address" in
    */*) if uci -q get network.lan.netmask >/dev/null; then
           uci -q delete network.lan.netmask || fail "无法移除旧网络掩码"
         fi ;;
  esac
  uci commit network || fail "无法保存 LAN 配置"
  log "LAN 地址已设置为 $lan_ip_address"
fi

# ==========================================
# 配置无线网络（沿用官方示例，只设置第一组无线设备和接口）
# ==========================================
# 更多选项: https://openwrt.org/docs/guide-user/network/wifi/basic#wi-fi_interfaces
# ------------------------------------------
if [ -n "${wlan_name:-}" ] && [ -n "${wlan_password:-}" ]; then
  if [ "${#wlan_password}" -lt 8 ]; then
    log "无线密码不足 8 位，跳过无线配置"
  elif [ "${#wlan_name}" -gt 32 ] || [ "${#wlan_password}" -gt 63 ]; then
    log "无线名称超过 32 字节或密码超过 63 字节，跳过无线配置"
  elif ! uci -q get 'wireless.@wifi-device[0]' >/dev/null || ! uci -q get 'wireless.@wifi-iface[0]' >/dev/null; then
    log "未找到无线设备或接口，跳过无线配置"
  else
    uci set "wireless.@wifi-iface[0].ssid=$wlan_name" &&
    uci -q set "wireless.@wifi-iface[0].key=$wlan_password" &&
    uci set 'wireless.@wifi-iface[0].encryption=psk2' &&
    uci set 'wireless.@wifi-iface[0].disabled=0' &&
    uci set 'wireless.@wifi-device[0].disabled=0' &&
    uci commit wireless || fail "无法保存无线配置"
    log "无线网络已配置"
  fi
fi

# ==========================================
# 配置 PPPoE
# ==========================================
# 更多选项: https://openwrt.org/docs/guide-user/network/wan/wan_interface_protocols#protocol_pppoe_ppp_over_ethernet
# ------------------------------------------
if [ -n "${pppoe_username:-}" ] && [ -n "${pppoe_password:-}" ]; then
  uci -q get network.wan >/dev/null || fail "未找到 network.wan"
  uci -q set network.wan.username="$pppoe_username" &&
  uci -q set network.wan.password="$pppoe_password" &&
  uci set network.wan.proto='pppoe' &&
  uci commit network || fail "无法保存 PPPoE 配置"
  log "PPPoE 已配置"
fi

# ==========================================
# 个性化：LuCI 简体中文和 Argon 主题。脚本不安装语言包或主题。
# ==========================================
if uci -q get luci.main >/dev/null; then
  # 设置 LuCI 默认语言为简体中文。
  uci set luci.main.lang='zh_cn' || fail "无法设置 LuCI 语言"

  # 仅当 Argon 静态文件真实存在时才切换主题。
  if [ -d /www/luci-static/argon ]; then
    uci set luci.main.mediaurlbase='/luci-static/argon' || fail "无法设置 Argon 主题"
  else
    log "未找到 Argon，保留当前主题"
  fi

  # 一次性保存语言和主题，避免重复提交。
  uci commit luci || fail "无法保存 LuCI 配置"
  log "已保存 LuCI 配置，默认语言设为简体中文"
else
  log "未找到 LuCI 配置，跳过语言和主题设置"
fi

# ==========================================
# 个性化：上海时区
# ==========================================
if uci -q get 'system.@system[0]' >/dev/null; then
  uci set 'system.@system[0].zonename=Asia/Shanghai' &&
  uci set 'system.@system[0].timezone=CST-8' &&
  uci commit system || fail "无法保存时区配置"
  log "系统时区已设置为 Asia/Shanghai"
else
  log "未找到系统配置，跳过时区设置"
fi

sync || fail "未能同步到磁盘"
log "首次启动配置执行完成"
