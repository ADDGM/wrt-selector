"""Guard CI wiring; actual matching is tested by Semgrep against YAML fixtures."""

import re
import shlex
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RULE = ".github/semgrep/action-reference-policy.yaml"
REPLACED_RULE = (
    "yaml.github-actions.security.github-actions-mutable-action-tag."
    "github-actions-mutable-action-tag"
)


class ActionPolicyWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (ROOT / ".github/workflows/project-quality.yml").read_text(
            encoding="utf-8"
        )

    def command(self, name):
        # Deliberately guard the checked-in folded-run step shape, not all YAML.
        match = re.search(
            rf"^      - name: {re.escape(name)}\n(.*?)(?=^      - |\Z)",
            self.workflow,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, name)
        block = match.group(1)
        self.assertRegex(block, r"\A        run: >-\n(?:          [^\n]+\n)+\Z")
        return shlex.split(" ".join(block.splitlines()[1:]))

    def test_scan_keeps_registry_rules_and_loads_replacement_atomically(self):
        self.assertTrue((ROOT / RULE).is_file())
        self.assertEqual(self.command("扫描网站、工具与工作流"), [
            "semgrep", "scan", "--config", "p/javascript", "--config", "p/python",
            "--config", "p/github-actions", "--config", RULE,
            "--exclude-rule", REPLACED_RULE,
            "--error", "--strict", "--metrics", "off", "--sarif", "--output",
            "semgrep.sarif", "www", "scripts", ".github/workflows/project-*.yml",
        ])

    def test_real_rule_tests_run_before_scan_and_cannot_be_soft_failed(self):
        self.assertEqual(self.command("测试 Action 引用安全规则"), [
            "semgrep", "scan", "--test", "--strict", "--metrics", "off",
            "--disable-version-check", ".github/semgrep",
        ])
        job = self.workflow.split("\n  semgrep:\n", 1)[1]
        self.assertLess(job.index("测试 Action 引用安全规则"), job.index("扫描网站、工具与工作流"))
        self.assertNotIn("continue-on-error", job)
        self.assertIn(
            "semgrep/semgrep:1.183.0@sha256:"
            "2e45517a85e13a9cca14a2a00df6bb48affd66b8ebfae1b0991cd57578362fb0",
            job,
        )

    def test_regression_fixtures_are_present_and_not_executable_workflows(self):
        fixture = ROOT / ".github/semgrep/action-reference-policy.test.yaml"
        self.assertNotEqual(fixture.parent, ROOT / ".github/workflows")
        text = fixture.read_text(encoding="utf-8")
        self.assertIn("# ruleid: project-action-reference-must-be-reviewed", text)
        self.assertIn("# ok: project-action-reference-must-be-reviewed", text)
        self.assertNotIn("# todoruleid:", text)
        self.assertNotIn("# todook:", text)


if __name__ == "__main__":
    unittest.main()
