import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_site import build_site
from check_commits import check_commits, validate_subject
from release_notes import release_notes
from release_content import SECTIONS, load_content, render_markdown, validate_links
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
        self.git("remote", "add", "origin", "https://github.com/example/selector.git")
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
        for tag in ("site-v1.0.0", "site-v1.1.0", "site-v1.2.3"):
            for language, sections in SECTIONS.items():
                path = self.root / f"docs/releases/{tag}.{language}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "Version overview\n\n[License](../../LICENSE)\n\n" +
                    "\n\n".join(f"## {section}\n\n- Reviewed content." for section in sections),
                    encoding="utf-8", newline="\r\n",
                )
        self.git("add", ".github", "docs")
        self.git("commit", "-qm", "ci: 建立测试基线")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.root), *args], stderr=subprocess.PIPE
        ).decode("utf-8").strip()

    def assert_full_changelog_range(self, notes, start, tag):
        expected = f"https://github.com/example/selector/compare/{start}...{tag}"
        for heading in ("完整更新日志", "Full changelog"):
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}\n", notes)
                section = notes.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
                links = re.findall(r"\]\((https://github\.com/example/selector/compare/[^)]+)\)", section)
                self.assertEqual(links, [expected])

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
        build_site(self.root, "site-v1.2.3")
        notes = release_notes(self.root, "site-v1.2.3")
        self.assertIn("建立测试基线", notes)
        self.assertNotIn("Original upstream history", notes)
        self.assertIn("不包含路由器固件", notes)
        self.assert_full_changelog_range(notes, self.base, "site-v1.2.3")
        self.git("commit", "--allow-empty", "-qm", "fix: 标签之后的改动")
        with self.assertRaisesRegex(ValueError, "同一提交"):
            release_notes(self.root, "site-v1.2.3")

    def test_release_notes_start_after_previous_tag(self):
        self.git("tag", "site-v1.0.0")
        self.git("commit", "--allow-empty", "-qm", "feat: 添加新选项")
        self.git("tag", "site-v1.1.0")
        build_site(self.root, "site-v1.1.0")
        notes = release_notes(self.root, "site-v1.1.0")
        self.assertIn("添加新选项", notes)
        self.assertNotIn("建立测试基线", notes)

        self.assert_full_changelog_range(notes, self.git("rev-parse", "site-v1.0.0"), "site-v1.1.0")

    def test_release_notes_cli_generates_full_range(self):
        self.git("tag", "-a", "site-v1.0.0", "-m", "Previous release")
        previous = self.git("rev-parse", "site-v1.0.0^{commit}")
        self.git("commit", "--allow-empty", "-qm", "feat: 新的个人功能")
        upstream = self.sync_upstream()
        build_site(self.root, "site-v1.1.0")
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ("release_notes.py", "release_content.py", "workflow_utils.py"):
            shutil.copyfile(Path(__file__).resolve().parents[2] / "scripts" / name, scripts / name)
        output = self.root / "build/release-notes.md"
        command = [sys.executable, "-B", str(scripts / "release_notes.py"),
                   "--tag", "site-v1.1.0", "--upstream-ref", upstream,
                   "--repository", "example/selector",
                   "--output", str(output)]
        for preview in (True, False):
            with self.subTest(preview=preview):
                if not preview:
                    self.git("tag", "-a", "site-v1.1.0", "-m", "Current release")
                before = self.git("tag", "--list")
                with patch.dict("os.environ", {"GITHUB_REPOSITORY": "ci-owner/ci-project"}):
                    subprocess.run(command + (["--preview"] if preview else []), cwd=self.root,
                                   check=True, capture_output=True)
                notes = output.read_text(encoding="utf-8")
                self.assert_full_changelog_range(notes, previous, "site-v1.1.0")
                self.assertIn("新的个人功能", notes)
                self.assertNotIn("Future upstream", notes)
                self.assertEqual("Local preview:" in notes, preview)
                self.assertEqual(self.git("tag", "--list"), before)
        full_history = self.git("log", "--format=%H", f"{previous}...site-v1.1.0")
        self.assertIn(upstream, full_history)
        self.assertNotIn(previous, full_history)

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
        build_site(self.root, "site-v1.1.0")
        notes = release_notes(self.root, "site-v1.1.0", upstream_ref=upstream)
        self.assertIn("新的个人功能", notes)
        self.assertNotIn("Future upstream", notes)
        self.assertNotIn("建立测试基线", notes)
        self.assertIn(upstream, notes)
        self.assertEqual(build_site(self.root).name, "firmware-selector-site-v1.1.0.zip")

    def test_bilingual_notes_use_real_package_and_context(self):
        self.git("tag", "site-v1.2.3")
        archive = build_site(self.root, "site-v1.2.3")
        notes = release_notes(self.root, "site-v1.2.3", run_url="https://github.com/example/selector/actions/runs/123")
        self.assertIn(hashlib.sha256(archive.read_bytes()).hexdigest(), notes)
        self.assertIn(f"{archive.stat().st_size:,}", notes)
        self.assertIn('id="release-en"', notes)
        self.assertIn("](#user-content-release-en)", notes)
        self.assertIn("blob/site-v1.2.3/LICENSE", notes)
        self.assertIn("/actions/runs/123", notes)
        self.assertIn("/releases/download/site-v1.2.3/release-notes.md", notes)
        self.assertNotIn("185 项", notes)
        with self.assertRaisesRegex(ValueError, "本仓库"):
            release_notes(self.root, "site-v1.2.3", run_url="https://github.com/other/repo/actions/runs/123")

    def test_release_requires_both_versioned_languages(self):
        self.git("rm", "docs/releases/site-v1.2.3.en.md")
        self.git("commit", "-qm", "docs: 测试缺少英文说明")
        self.git("tag", "site-v1.2.3")
        with self.assertRaisesRegex(ValueError, "标签内缺少"):
            release_notes(self.root, "site-v1.2.3")

    def test_formal_content_is_read_from_tag_not_working_tree(self):
        self.git("tag", "site-v1.2.3")
        build_site(self.root, "site-v1.2.3")
        path = self.root / "docs/releases/site-v1.2.3.en.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nUncommitted editorial change.\n", encoding="utf-8")
        self.assertNotIn("Uncommitted editorial change.", release_notes(self.root, "site-v1.2.3"))
        preview = release_notes(self.root, "site-v1.2.3", preview=True)
        self.assertIn("Uncommitted editorial change.", preview)
        self.assertIn("Local preview", preview)

    def test_preview_needs_no_tag_and_preserves_code_examples(self):
        path = self.root / "docs/releases/site-v1.2.3.en.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n\n```md\n[example](missing.md)\n```\n", encoding="utf-8")
        build_site(self.root, "site-v1.2.3")
        before = self.git("tag", "--list")
        notes = release_notes(self.root, "site-v1.2.3", preview=True)
        self.assertIn("[example](missing.md)", notes)
        self.assert_full_changelog_range(notes, self.base, "site-v1.2.3")
        self.assertEqual(self.git("tag", "--list"), before)

    def test_placeholders_sections_and_missing_document_links_fail(self):
        path = self.root / "docs/releases/site-v1.2.3.en.md"
        original = path.read_text(encoding="utf-8")
        target = self.git("rev-parse", "HEAD")
        for text, message in [
            (original + "\nTODO", "占位"),
            (original.replace("## Known limitations", "## Other"), "缺少章节"),
            (original.replace("## Highlights\n\n- Reviewed content.", "## Highlights"), "章节不能为空"),
            (original + "\n[missing](absent.md)", "缺少"),
            (original + "\n[reference]: ../en/usage.md", "内联"),
        ]:
            with self.subTest(message=message):
                path.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    load_content(self.root, target, "site-v1.2.3", "en", "example/selector", preview=True)

    def test_corrupt_package_and_metadata_block_notes(self):
        self.git("tag", "site-v1.2.3")
        archive = build_site(self.root, "site-v1.2.3")
        archive.write_bytes(archive.read_bytes() + b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            release_notes(self.root, "site-v1.2.3")
        build_site(self.root, "site-v1.2.3")
        info = self.root / "build/build-info.json"
        data = json.loads(info.read_text())
        data["source_sha"] = self.base
        info.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "构建信息"):
            release_notes(self.root, "site-v1.2.3")

    def test_dirty_site_cannot_be_used_for_formal_notes(self):
        self.git("tag", "site-v1.2.3")
        (self.root / "www/index.css").write_text("body { color: blue; }")
        build_site(self.root, "site-v1.2.3")
        with self.assertRaisesRegex(ValueError, "干净"):
            release_notes(self.root, "site-v1.2.3")
        self.assertIn("Local preview", release_notes(self.root, "site-v1.2.3", preview=True))

    def test_rendered_anchor_and_planned_asset_links(self):
        target = self.git("rev-parse", "HEAD")
        args = (self.root, target, "site-v1.2.3", "example/selector", {"release-notes.md"})
        markdown = '[English](#user-content-release-en)\n<h2 id="release-en">English</h2>'
        html = '<a href="#user-content-release-en">English</a><h2 id="user-content-release-en">English</h2>'
        self.assertEqual(validate_links(markdown, *args, rendered_html=html), 1)
        with self.assertRaisesRegex(ValueError, "锚点不存在"):
            validate_links("[English](#english-release-notes)", *args)
        with self.assertRaisesRegex(ValueError, "渲染丢失"):
            validate_links(markdown, *args, rendered_html="<h2>English</h2>")
        with self.assertRaisesRegex(ValueError, "资产链接不存在"):
            validate_links("[zip](https://github.com/example/selector/releases/download/site-v1.2.3/wrong.zip)", *args)
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            validate_links("[bad](javascript:alert)", *args)

    def test_markdown_api_uses_stdin_and_reports_failure(self):
        with patch("release_content.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "<h2>English</h2>", "")
            self.assertEqual(render_markdown("## English", "example/selector"), "<h2>English</h2>")
            self.assertEqual(json.loads(run.call_args.kwargs["input"])["context"], "example/selector")
            self.assertIn("--input", run.call_args.args[0])
            run.return_value = subprocess.CompletedProcess([], 1, "", "credential detail")
            with self.assertRaisesRegex(ValueError, "GitHub Markdown"):
                render_markdown("## English", "example/selector")

    def test_commit_titles_are_escaped_and_prerelease_type_is_explicit(self):
        self.git("commit", "--allow-empty", "-qm", "fix: 修复 [标题](https://example.invalid) 与 #42")
        tag = "site-v1.2.3-rc.1"
        for language in SECTIONS:
            source = self.root / f"docs/releases/site-v1.2.3.{language}.md"
            shutil.copyfile(source, self.root / f"docs/releases/{tag}.{language}.md")
        self.git("add", "docs")
        self.git("commit", "-qm", "docs: 准备预发布内容")
        self.git("tag", tag)
        build_site(self.root, tag)
        notes = release_notes(self.root, tag)
        self.assertIn("预发布 / Prerelease", notes)
        self.assertIn(r"\[标题\]", notes)
        target = self.git("rev-parse", "HEAD")
        self.assertEqual(validate_links(
            "Fix #42", self.root, target, tag, "example/selector", set(),
            rendered_html='<p>Fix <a href="https://github.com/example/selector/issues/42">#42</a></p>',
        ), 1)

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
