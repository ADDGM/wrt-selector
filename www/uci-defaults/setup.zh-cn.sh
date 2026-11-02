# 注意！脚本会作为固件的一部分保留在 /rom/etc/uci-defaults/ 中。
# 取消相应行的注释以应用设置：
#
# wlan_name="OpenWrt"
# wlan_password="12345678"
#
# root_password=""
#
# 24.10 及更早版本的网络掩码默认是 255.255.255.0：
# lan_ip_address="192.168.1.1"
#
# 25.12 及之后请务必使用 CIDR 表示法：
# lan_ip_address="192.168.1.1/24"
#
# pppoe_username=""
# pppoe_password=""

# 记录可能出现的错误
exec >/tmp/setup.log 2>&1

if [ -n "$root_password" ]; then
  (echo "$root_password"; sleep 1; echo "$root_password") | passwd > /dev/null
fi

# 配置局域网（LAN）
# 更多选项：https://openwrt.org/docs/guide-user/base-system/basic-networking
if [ -n "$lan_ip_address" ]; then
  uci set network.lan.ipaddr="$lan_ip_address"
  uci commit network
fi

# 配置无线网络（WLAN）
# 更多选项：https://openwrt.org/docs/guide-user/network/wifi/basic#wi-fi_interfaces
if [ -n "$wlan_name" -a -n "$wlan_password" -a ${#wlan_password} -ge 8 ]; then
  uci set wireless.@wifi-device[0].disabled='0'
  uci set wireless.@wifi-iface[0].disabled='0'
  uci set wireless.@wifi-iface[0].encryption='psk2'
  uci set wireless.@wifi-iface[0].ssid="$wlan_name"
  uci set wireless.@wifi-iface[0].key="$wlan_password"
  uci commit wireless
fi

# 配置 PPPoE 拨号
# 更多选项：https://openwrt.org/docs/guide-user/network/wan/wan_interface_protocols#protocol_pppoe_ppp_over_ethernet
if [ -n "$pppoe_username" -a "$pppoe_password" ]; then
  uci set network.wan.proto=pppoe
  uci set network.wan.username="$pppoe_username"
  uci set network.wan.password="$pppoe_password"
  uci commit network
fi

echo "All done!"
