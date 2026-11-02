"""Exercise the first-boot example with mocked router commands, never a router."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


TEMPLATE = Path(__file__).resolve().parents[2] / "www/uci-defaults/immortalwrt.sh"
OPTIONS = (
    "root_password", "lan_ip_address", "wlan_name", "wlan_password",
    "pppoe_username", "pppoe_password", "luci_language", "use_argon",
    "system_zonename", "system_timezone",
)
MOCK_COMMANDS = r'''
uci() {
  printf '%s\n' "$*" >> "$MOCK_CALLS"
  if [ -n "$MOCK_FAIL" ] && [ "$*" = "$MOCK_FAIL" ]; then return 1; fi
  case "$*" in
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


class ImmortalWrtDefaultsTest(unittest.TestCase):
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

    def run_example(self, options=None, *, argon=False, **overrides):
        with tempfile.TemporaryDirectory(prefix="wrt-firstboot-test-") as directory:
            root = Path(directory)
            if argon:
                (root / "argon").mkdir()
            source = TEMPLATE.read_text(encoding="utf-8")
            source = source.replace("/tmp/setup.log", (root / "setup.log").as_posix())
            source = source.replace("[ -d /www/luci-static/argon ]",
                                    "[ -d " + shlex.quote((root / "argon").as_posix()) + " ]")
            self.assertNotIn("/tmp/setup.log", source)
            assignments = "\n".join(f"{key}={shlex.quote(value)}" for key, value in (options or {}).items())
            # Options and mocks are in the caller, as when the example is appended.
            script = root / "example.sh"
            script.write_text(MOCK_COMMANDS + "\n" + assignments + "\n" + source +
                              '\nresult=$?\nprintf "caller-output\\n"\nexit "$result"\n',
                              encoding="utf-8", newline="\n")
            environment = {key: value for key, value in os.environ.items() if key not in OPTIONS}
            environment["PATH"] = str(Path(self.shell).parent) + os.pathsep + environment.get("PATH", "")
            environment.update({
                "MOCK_CALLS": (root / "calls").as_posix(),
                "MOCK_SYSLOG": (root / "syslog").as_posix(),
                "MOCK_PASSWORD_INPUT": (root / "password-input").as_posix(),
                "MOCK_FAIL": "", "MOCK_PASSWORD_FAIL": "0",
                "MOCK_LUCI": "1", "MOCK_LAN": "1", "MOCK_WAN": "1",
                "MOCK_NETMASK": "1", "MOCK_WIFI": "1",
            })
            environment.update(overrides)
            run = subprocess.run([self.shell, script.as_posix()], env=environment,
                                 capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(run.stdout, "caller-output\n", run.stderr)
            log = (root / "setup.log").read_text(encoding="utf-8")
            self.assertNotIn("command not found", log)
            if os.name != "nt":
                self.assertEqual((root / "setup.log").stat().st_mode & 0o777, 0o600)
            files = {name: (root / name).read_text(encoding="utf-8") if (root / name).exists() else ""
                     for name in ("calls", "syslog", "password-input")}
            self.assertNotIn("unexpected", files["calls"])
            return run.returncode, log, files

    def test_default_example_does_not_change_configuration(self):
        code, log, files = self.run_example(MOCK_WIFI="0", MOCK_LUCI="0")
        self.assertEqual(code, 0)
        self.assertEqual(files["calls"], "")
        self.assertEqual(files["password-input"], "")
        self.assertIn("All requested first-boot settings completed", log)

    def test_luci_language_and_installed_theme_commit_once(self):
        code, _, files = self.run_example({"luci_language": "zh_cn", "use_argon": "1"}, argon=True)
        self.assertEqual(code, 0)
        self.assertIn("luci.main.lang=zh_cn", files["calls"])
        self.assertIn("luci.main.mediaurlbase=/luci-static/argon", files["calls"])
        self.assertEqual(files["calls"].count("-q commit luci"), 1)

    def test_missing_optional_luci_or_theme_is_skipped(self):
        code, log, files = self.run_example({"luci_language": "zh_cn", "use_argon": "1"}, MOCK_LUCI="0")
        self.assertEqual(code, 0)
        self.assertNotIn("-q set", files["calls"])
        self.assertIn("LuCI is not installed", log)
        code, log, files = self.run_example({"luci_language": "zh_cn", "use_argon": "1"})
        self.assertEqual(code, 0)
        self.assertNotIn("mediaurlbase", files["calls"])
        self.assertEqual(files["calls"].count("-q commit luci"), 1)
        self.assertIn("Argon is not installed", log)

    def test_timezone_requires_both_values(self):
        code, _, files = self.run_example({"system_zonename": "Asia/Shanghai", "system_timezone": "CST-8"})
        self.assertEqual(code, 0)
        self.assertIn("system.@system[0].timezone=CST-8", files["calls"])
        self.assertIn("-q commit system", files["calls"])
        code, _, files = self.run_example({"system_zonename": "Asia/Shanghai"})
        self.assertEqual(code, 1)
        self.assertNotIn("-q set", files["calls"])

    def test_lan_cidr_only_removes_an_existing_legacy_netmask(self):
        for address, netmask, removed in [("192.168.10.1", "1", False),
                                          ("192.168.10.1/24", "1", True),
                                          ("192.168.10.1/24", "0", False)]:
            with self.subTest(address=address, netmask=netmask):
                code, _, files = self.run_example({"lan_ip_address": address}, MOCK_NETMASK=netmask)
                self.assertEqual(code, 0)
                self.assertEqual("-q delete network.lan.netmask" in files["calls"], removed)
                self.assertIn("-q commit network", files["calls"])

    def test_invalid_lan_is_rejected_before_any_network_write(self):
        for address in ["256.1.1.1/24", "192.168.1", "192.168.1.1/33", "192.168.1.1/",
                        "192.168.1.1/24/1", "192.168.1.1\n192.168.2.1"]:
            with self.subTest(address=address):
                code, _, files = self.run_example({"lan_ip_address": address})
                self.assertEqual(code, 1)
                self.assertNotIn("-q set", files["calls"])

    def test_credentials_reach_commands_but_not_logs(self):
        secret = "test secret;$literal"
        code, log, files = self.run_example({"root_password": secret, "wlan_name": "Test WiFi",
                                             "wlan_password": secret, "pppoe_username": "test-user",
                                             "pppoe_password": secret})
        self.assertEqual(code, 0)
        self.assertEqual(files["password-input"], secret + "\n" + secret + "\n")
        self.assertIn("-q commit wireless", files["calls"])
        self.assertIn("network.wan.proto=pppoe", files["calls"])
        self.assertNotIn(secret, log + files["syslog"])
        self.assertNotIn("test-user", log + files["syslog"])

    def test_missing_interfaces_and_partial_credentials_fail(self):
        cases = [({"wlan_name": "Test WiFi", "wlan_password": "long-password"}, {"MOCK_WIFI": "0"}),
                 ({"wlan_name": "Test WiFi"}, {}),
                 ({"wlan_name": "Test WiFi", "wlan_password": "short"}, {}),
                 ({"wlan_name": "x" * 33, "wlan_password": "long-password"}, {}),
                 ({"pppoe_username": "test-user"}, {}),
                 ({"pppoe_username": "test-user", "pppoe_password": "test-pass"}, {"MOCK_WAN": "0"}),
                 ({"lan_ip_address": "192.168.10.1/24"}, {"MOCK_LAN": "0"})]
        for options, flags in cases:
            with self.subTest(options=list(options), flags=flags):
                code, _, files = self.run_example(options, **flags)
                self.assertEqual(code, 1)
                self.assertNotIn("-q set", files["calls"])

    def test_command_failures_are_not_reported_as_success(self):
        cases = [({"root_password": "test-pass"}, {"MOCK_PASSWORD_FAIL": "1"}),
                 ({"luci_language": "zh_cn"}, {"MOCK_FAIL": "-q set luci.main.lang=zh_cn"}),
                 ({"luci_language": "zh_cn"}, {"MOCK_FAIL": "-q commit luci"}),
                 ({"lan_ip_address": "192.168.10.1/24"}, {"MOCK_FAIL": "-q delete network.lan.netmask"})]
        for options, flags in cases:
            with self.subTest(options=list(options), flags=flags):
                code, log, files = self.run_example(options, **flags)
                self.assertEqual(code, 1)
                self.assertNotIn("All requested first-boot settings completed", log)
                self.assertIn("may retry", log)
                if "set luci" in flags.get("MOCK_FAIL", ""):
                    self.assertNotIn("-q commit luci", files["calls"])


if __name__ == "__main__":
    unittest.main()
