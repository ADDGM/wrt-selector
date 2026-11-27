"""Exercise the first-boot example with mocked router commands, never a router."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


TEMPLATES = Path(__file__).resolve().parents[2] / "www/uci-defaults"
OPTIONS = (
    "root_password", "lan_ip_address", "wlan_name", "wlan_password",
    "pppoe_username", "pppoe_password",
)
MOCK_COMMANDS = r'''
uci() {
  printf '%s\n' "$*" >> "$MOCK_CALLS"
  if [ -n "$MOCK_FAIL" ] && [ "$*" = "$MOCK_FAIL" ]; then return 1; fi
  case "$*" in
    '-q get system.@system[0]') [ "$MOCK_SYSTEM" = 1 ] ;;
    '-q get luci.main') [ "$MOCK_LUCI" = 1 ] ;;
    '-q get network.lan') [ "$MOCK_LAN" = 1 ] ;;
    '-q get network.lan.netmask') [ "$MOCK_NETMASK" = 1 ] ;;
    '-q get network.wan') [ "$MOCK_WAN" = 1 ] ;;
    '-q get wireless.@wifi-device[0]'|'-q get wireless.@wifi-iface[0]') [ "$MOCK_WIFI" = 1 ] ;;
    *) return 0 ;;
  esac
}
passwd() {
  cat > "$MOCK_PASSWORD_INPUT"
  [ "$MOCK_PASSWORD_FAIL" = 0 ]
}
logger() { printf '%s\n' "$*" >> "$MOCK_SYSLOG"; }
sync() { :; }
# Fail closed if package or download commands are introduced into the example.
apk() { printf 'unexpected apk\n' >> "$MOCK_CALLS"; return 99; }
opkg() { printf 'unexpected opkg\n' >> "$MOCK_CALLS"; return 99; }
curl() { printf 'unexpected curl\n' >> "$MOCK_CALLS"; return 99; }
wget() { printf 'unexpected wget\n' >> "$MOCK_CALLS"; return 99; }
'''


class FirstBootDefaultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = shutil.which("sh")
        if not cls.shell and os.name == "nt":
            git = shutil.which("git")
            candidate = Path(git).resolve().parents[1] / "usr/bin/sh.exe" if git else None
            if candidate and candidate.is_file():
                cls.shell = str(candidate)
        if not cls.shell:
            raise unittest.SkipTest("A POSIX shell (or Git for Windows) is required")

    def run_example(self, options=None, *, template="immortalwrt.sh", argon=False, **overrides):
        with tempfile.TemporaryDirectory(prefix="wrt-firstboot-test-") as directory:
            root = Path(directory)
            if argon:
                (root / "argon").mkdir()
            source = (TEMPLATES / template).read_text(encoding="utf-8")
            source = source.replace("/tmp/setup.log", "./setup.log")
            source = source.replace("[ -d /www/luci-static/argon ]",
                                    "[ -d " + shlex.quote((root / "argon").as_posix()) + " ]")
            self.assertNotIn("/tmp/setup.log", source)
            assignments = "\n".join(f"{key}={shlex.quote(value)}" for key, value in (options or {}).items())
            # A command appended after the example must run only on success, with output in setup.log.
            script = root / "example.sh"
            script.write_text(MOCK_COMMANDS + "\n" + assignments + "\n" + source +
                              '\nprintf "appended-output\\n"\n',
                              encoding="utf-8", newline="\n")
            environment = {key: value for key, value in os.environ.items() if key not in OPTIONS}
            environment["PATH"] = str(Path(self.shell).parent) + os.pathsep + environment.get("PATH", "")
            environment.update({
                "MOCK_CALLS": (root / "calls").as_posix(),
                "MOCK_SYSLOG": (root / "syslog").as_posix(),
                "MOCK_PASSWORD_INPUT": (root / "password-input").as_posix(),
                "MOCK_FAIL": "", "MOCK_PASSWORD_FAIL": "0",
                "MOCK_LUCI": "1", "MOCK_LAN": "1", "MOCK_WAN": "1",
                "MOCK_NETMASK": "1", "MOCK_WIFI": "1", "MOCK_SYSTEM": "1",
            })
            environment.update(overrides)
            run = subprocess.run([self.shell, script.as_posix()], env=environment, cwd=root,
                                 capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(run.stdout, "", run.stderr)
            log = (root / "setup.log").read_text(encoding="utf-8")
            self.assertEqual("appended-output" in log.splitlines(), run.returncode == 0, log)
            self.assertNotIn("command not found", log)
            if os.name != "nt":
                self.assertEqual((root / "setup.log").stat().st_mode & 0o777, 0o600)
            files = {name: (root / name).read_text(encoding="utf-8") if (root / name).exists() else ""
                     for name in ("calls", "syslog", "password-input")}
            self.assertNotIn("unexpected", files["calls"])
            return run.returncode, log, files

    def test_real_variants_apply_the_same_personal_settings_and_localize_logs(self):
        for stem, tag in [("setup", "openwrt-firstboot"), ("immortalwrt", "immortalwrt-firstboot")]:
            for suffix, done, error in [("", "First-boot configuration complete", "Error: "),
                                        (".zh-cn", "首次启动配置执行完成", "错误：")]:
                template = stem + suffix + ".sh"
                with self.subTest(template=template):
                    code, log, files = self.run_example(template=template, argon=True)
                    self.assertEqual(code, 0)
                    self.assertIn(f"-t {tag} {done}", files["syslog"])
                    self.assertIn(done, log)
                    self.assertIn("luci.main.lang=zh_cn", files["calls"])
                    self.assertIn("luci.main.mediaurlbase=/luci-static/argon", files["calls"])
                    self.assertEqual(files["calls"].count("commit luci"), 1)
                    self.assertIn("system.@system[0].zonename=Asia/Shanghai", files["calls"])
                    self.assertIn("system.@system[0].timezone=CST-8", files["calls"])
                    self.assertNotRegex(files["calls"], r"network\.|wireless\.")
                    self.assertEqual(files["password-input"], "")
                    code, log, files = self.run_example(template=template, MOCK_FAIL="commit luci")
                    self.assertEqual(code, 1)
                    self.assertIn(error, log)
                    self.assertIn(error, files["syslog"])
                    self.assertNotIn(done, log)

    def test_missing_optional_components_are_skipped(self):
        code, log, files = self.run_example(MOCK_LUCI="0", MOCK_SYSTEM="0")
        self.assertEqual(code, 0)
        self.assertNotIn("commit", files["calls"])
        self.assertIn("LuCI configuration not found", log)
        self.assertIn("System configuration not found", log)
        code, log, files = self.run_example()
        self.assertEqual(code, 0)
        self.assertNotIn("mediaurlbase", files["calls"])
        self.assertIn("Argon not found", log)

    def test_lan_cidr_only_removes_an_existing_legacy_netmask(self):
        for address, netmask, removed in [("192.168.10.1", "1", False),
                                          ("192.168.10.1/24", "1", True),
                                          ("192.168.10.1/24", "0", False)]:
            with self.subTest(address=address, netmask=netmask):
                code, _, files = self.run_example({"lan_ip_address": address}, MOCK_NETMASK=netmask)
                self.assertEqual(code, 0)
                self.assertEqual("-q delete network.lan.netmask" in files["calls"], removed)
                self.assertIn("commit network", files["calls"])

    def test_invalid_lan_is_rejected_before_any_network_write(self):
        for address in ["[IP]", "[IP]/24", "256.1.1.1/24", "192.168.1", "192.168.1.1/33", "192.168.1.1/",
                        "192.168.1.1/24/1", "192.168.1.1\n192.168.2.1"]:
            with self.subTest(address=address):
                code, _, files = self.run_example({"lan_ip_address": address})
                self.assertEqual(code, 1)
                self.assertNotIn("set network.", files["calls"])

    def test_credentials_reach_commands_but_not_logs(self):
        secret = "test secret;$literal"
        code, log, files = self.run_example({"root_password": secret, "wlan_name": "Test WiFi",
                                             "wlan_password": secret, "pppoe_username": "test-user",
                                             "pppoe_password": secret})
        self.assertEqual(code, 0)
        self.assertEqual(files["password-input"], secret + "\n" + secret + "\n")
        self.assertIn("commit wireless", files["calls"])
        self.assertIn("network.wan.proto=pppoe", files["calls"])
        self.assertNotIn(secret, log + files["syslog"])
        self.assertNotIn("test-user", log + files["syslog"])

    def test_unrequested_or_unusable_wireless_and_pppoe_are_skipped(self):
        cases = [({"wlan_name": "Test WiFi", "wlan_password": "long-password"}, {"MOCK_WIFI": "0"}),
                 ({"wlan_name": "Test WiFi"}, {}),
                 ({"wlan_name": "Test WiFi", "wlan_password": "short"}, {}),
                 ({"wlan_name": "x" * 33, "wlan_password": "long-password"}, {}),
                 ({"wlan_name": "Test", "wlan_password": "x" * 64}, {}),
                 ({"pppoe_username": "test-user"}, {})]
        for options, flags in cases:
            with self.subTest(options=options, flags=flags):
                code, _, files = self.run_example(options, **flags)
                self.assertEqual(code, 0)
                self.assertNotRegex(files["calls"], r"set (wireless|network)\.")

    def test_command_failures_are_not_reported_as_success(self):
        cases = [({"root_password": "test-pass"}, {"MOCK_PASSWORD_FAIL": "1"}),
                 ({}, {"MOCK_FAIL": "set luci.main.lang=zh_cn"}),
                 ({}, {"MOCK_FAIL": "commit system"}),
                 ({"lan_ip_address": "192.168.10.1/24"}, {"MOCK_FAIL": "-q delete network.lan.netmask"}),
                 ({"lan_ip_address": "192.168.10.1"}, {"MOCK_LAN": "0"}),
                 ({"pppoe_username": "test-user", "pppoe_password": "test-pass"}, {"MOCK_WAN": "0"})]
        for options, flags in cases:
            with self.subTest(options=list(options), flags=flags):
                code, log, files = self.run_example(options, **flags)
                self.assertEqual(code, 1)
                self.assertNotIn("First-boot configuration complete", log)
                self.assertIn("Error: ", log)
                if "set luci" in flags.get("MOCK_FAIL", ""):
                    self.assertNotIn("commit luci", files["calls"])


if __name__ == "__main__":
    unittest.main()
