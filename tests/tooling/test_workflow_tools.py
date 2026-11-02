import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_site import build_site
from check_commits import check_commits, validate_subject
from release_notes import release_notes
from workflow_utils import require_project_source, upstream_snapshot, validate_tag


class WorkflowToolsTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="firmware-selector-tools-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git("init", "-q", "--initial-branch=main")
        self.git("config", "user.name", "Test Maintainer")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.autocrlf", "false")
        for name, content in {
            "www/index.html": "<script src='js/main.js'></script>",
            "www/index.css": "body { color: black; }",
            "www/config.js": 'var config = {asu_url: "https://example.invalid"};',
            "www/js/main.js": 'const version = "%GIT_VERSION%";',
            "www/uci-defaults/setup.sh": "#!/bin/sh\nexit 0\n",
            "LICENSE": "Test license\n",
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "Original upstream history")
        self.base = self.git("rev-parse", "HEAD")
        self.git("switch", "-qc", "develop")
        (self.root / ".github").mkdir()
        (self.root / ".github/commit-policy-baseline.txt").write_text(self.base)
        self.git("add", ".github")
        self.git("commit", "-qm", "ci: 建立测试基线")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.root), *args], stderr=subprocess.PIPE
        ).decode("utf-8").strip()

    def test_subject_contract(self):
        for subject in ("fix(tooling): 修复默认检查", "feat!: 调整构建契约", "ci: 增加测试"):
            self.assertIsNone(validate_subject(subject))
        for subject in ("fix(): 修复检查", "fix: English only", "修复检查", "feat: " + "字" * 73):
            self.assertIsNotNone(validate_subject(subject))

    def test_only_new_commits_are_checked(self):
        self.assertEqual(check_commits(self.root, base="0" * 40), 1)
        self.git("commit", "--allow-empty", "-qm", "fix: 修复构建")
        self.assertEqual(check_commits(self.root), 2)
        self.git("commit", "--allow-empty", "-qm", "unstructured English change")
        with self.assertRaisesRegex(ValueError, "unstructured"):
            check_commits(self.root)

    def test_dependency_bot_exemption(self):
        self.git("commit", "--allow-empty", "-qm", "build(deps): bump a dependency",
                 "--author=dependabot[bot] <bot@example.invalid>")
        self.assertEqual(check_commits(self.root), 2)

    def test_site_contents_version_and_checksum(self):
        original = (self.root / "www/js/main.js").read_bytes()
        config = (self.root / "www/config.js").read_bytes()
        (self.root / "www/local-secret.txt").write_text("must not be packaged")
        archive = build_site(self.root, "v1.2.3")
        first_archive = archive.read_bytes()
        with ZipFile(archive) as bundle:
            self.assertNotIn("local-secret.txt", bundle.namelist())
            self.assertNotIn(".github/commit-policy-baseline.txt", bundle.namelist())
            self.assertIn("uci-defaults/setup.sh", bundle.namelist())
            self.assertEqual(bundle.read("config.js"), config)
            self.assertIn(b'"v1.2.3"', bundle.read("js/main.js"))
            info = json.loads(bundle.read("build-info.json"))
            self.assertEqual(info["source_sha"], self.git("rev-parse", "HEAD"))
            self.assertFalse(info["source_dirty"])
        self.assertEqual((self.root / "www/js/main.js").read_bytes(), original)
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(
            archive.with_suffix(".zip.sha256").read_bytes(),
            f"{checksum}  {archive.name}\n".encode("utf-8"),
        )
        self.assertEqual(build_site(self.root, "v1.2.3").read_bytes(), first_archive)

    def test_rebuild_removes_obsolete_site_files(self):
        build_site(self.root, "v1.2.3")
        self.git("rm", "www/uci-defaults/setup.sh")
        build_site(self.root, "v1.2.4")
        self.assertFalse((self.root / "build/site/uci-defaults/setup.sh").exists())

    def test_tagless_and_dirty_preview(self):
        (self.root / "www/index.css").write_text("body { color: blue; }")
        archive = build_site(self.root)
        self.assertEqual(archive.name, f"firmware-selector-{self.git('rev-parse', '--short', 'HEAD')}.zip")
        with ZipFile(archive) as bundle:
            self.assertTrue(json.loads(bundle.read("build-info.json"))["source_dirty"])
            self.assertIn(b"blue", bundle.read("index.css"))

    def test_explicit_base_limits_commit_range(self):
        self.git("commit", "--allow-empty", "-qm", "Old English title")
        start = self.git("rev-parse", "HEAD")
        self.git("commit", "--allow-empty", "-qm", "fix: 本次修复")
        self.assertEqual(check_commits(self.root, base=start), 1)

    def test_refuses_unowned_output_and_unsafe_versions(self):
        sentinel = self.root / "build/site/keep.txt"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("user file")
        with self.assertRaisesRegex(ValueError, "拒绝覆盖"):
            build_site(self.root, "v1.2.3")
        self.assertEqual(sentinel.read_text(), "user file")
        with self.assertRaises(ValueError):
            build_site(self.root, '../../outside";alert(1)')

    def test_missing_version_marker_fails(self):
        (self.root / "www/js/main.js").write_text("const version = 'old';")
        with self.assertRaisesRegex(ValueError, "版本占位符"):
            build_site(self.root, "v1.2.3")

    def test_release_tags_and_source_match(self):
        for tag in ("site-v1.2.3", "site-v1.2.3-beta.1", "site-v1.2.3-rc.0"):
            self.assertEqual(validate_tag(tag), tag)
        for tag in ("v1.2.3", "site-v01.2.3", "site-v1.2", "site-v1.2.3-rc.01", "--help", "site-v1.2.3\nextra"):
            with self.assertRaises(ValueError):
                validate_tag(tag)
        self.git("tag", "site-v1.2.3")
        notes = release_notes(self.root, "site-v1.2.3")
        self.assertIn("建立测试基线", notes)
        self.assertNotIn("Original upstream history", notes)
        self.assertIn("不包含路由器固件", notes)
        self.git("commit", "--allow-empty", "-qm", "fix: 标签之后的改动")
        with self.assertRaisesRegex(ValueError, "同一提交"):
            release_notes(self.root, "site-v1.2.3")

    def test_release_notes_start_after_previous_tag(self):
        self.git("tag", "site-v1.0.0")
        self.git("commit", "--allow-empty", "-qm", "feat: 添加新选项")
        self.git("tag", "site-v1.1.0")
        notes = release_notes(self.root, "site-v1.1.0")
        self.assertIn("添加新选项", notes)
        self.assertNotIn("建立测试基线", notes)

    def sync_upstream(self):
        self.git("switch", "-q", "main")
        self.git("commit", "--allow-empty", "-qm", "fix: Future upstream English change")
        self.git("tag", "v99.0.0")
        snapshot = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "develop")
        self.git("merge", "--no-ff", "-qm", "Merge upstream main", "main")
        return snapshot

    def test_future_upstream_commits_are_excluded_but_personal_commits_are_checked(self):
        upstream = self.sync_upstream()
        self.git("commit", "--allow-empty", "-qm", "feat: 个人改动")
        self.assertEqual(check_commits(self.root, upstream_ref=upstream), 2)
        with self.assertRaisesRegex(ValueError, "Future upstream"):
            check_commits(self.root, upstream_ref=self.base)
        self.git("commit", "--allow-empty", "-qm", "fix: Personal English change")
        with self.assertRaisesRegex(ValueError, "Personal English"):
            check_commits(self.root)

    def test_release_and_build_ignore_upstream_tags_and_commits(self):
        self.git("tag", "site-v1.0.0")
        self.git("commit", "--allow-empty", "-qm", "feat: 新的个人功能")
        upstream = self.sync_upstream()
        self.git("tag", "site-v1.1.0")
        notes = release_notes(self.root, "site-v1.1.0", upstream_ref=upstream)
        self.assertIn("新的个人功能", notes)
        self.assertNotIn("Future upstream", notes)
        self.assertNotIn("建立测试基线", notes)
        self.assertIn(upstream, notes)
        self.assertEqual(build_site(self.root).name, "firmware-selector-site-v1.1.0.zip")

    def test_main_to_develop_pr_runs_tool_from_merged_checkout(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ("check_commits.py", "workflow_utils.py"):
            shutil.copyfile(Path(__file__).resolve().parents[2] / "scripts" / name, scripts / name)
        self.git("add", "scripts")
        self.git("commit", "-qm", "ci: 加入个人检查脚本")
        pr_base = self.git("rev-parse", "HEAD")
        upstream = self.sync_upstream()
        missing = subprocess.run(["git", "-C", str(self.root), "cat-file", "-e", "main:scripts/check_commits.py"], capture_output=True)
        self.assertNotEqual(missing.returncode, 0)
        result = subprocess.run([
            sys.executable, "-B", str(scripts / "check_commits.py"),
            "--base", pr_base, "--head", "main", "--upstream-ref", upstream,
        ], capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 条个人非合并提交", result.stdout)

    def test_missing_or_unrelated_upstream_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, "找不到上游镜像"):
            check_commits(self.root, upstream_ref="missing")
        self.git("checkout", "-q", "--orphan", "unrelated")
        self.git("commit", "-qm", "Unrelated root")
        self.git("switch", "-q", "develop")
        with self.assertRaisesRegex(ValueError, "同一条上游历史"):
            upstream_snapshot(self.root, "unrelated")

    def test_pure_upstream_and_unmerged_feature_cannot_be_published(self):
        upstream = self.sync_upstream()
        with self.assertRaisesRegex(ValueError, "纯上游"):
            require_project_source(self.root, upstream, upstream)
        with self.assertRaisesRegex(ValueError, "纯上游"):
            require_project_source(self.root, self.base, self.base)
        self.git("switch", "-qc", "feature")
        self.git("commit", "--allow-empty", "-qm", "feat: 未合并功能")
        self.git("tag", "site-v2.0.0")
        with self.assertRaisesRegex(ValueError, "合入 develop"):
            release_notes(self.root, "site-v2.0.0")


if __name__ == "__main__":
    unittest.main()
