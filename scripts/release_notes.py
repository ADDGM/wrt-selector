"""Compose bilingual release notes from versioned content and verified artifacts."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from release_content import load_content, render_markdown, repository_name, validate_links
from workflow_utils import ROOT, baseline, configure_console, git, require_ancestor, require_project_source, resolve_ref, upstream_snapshot, validate_tag


GROUPS = {
    "feat": ("新功能", "Features"), "fix": ("问题修复", "Fixes"),
    "style": ("界面调整", "Interface"), "docs": ("文档", "Documentation"),
    "test": ("测试", "Tests"), "ci": ("持续集成", "CI"),
    "build": ("构建与依赖", "Build and dependencies"),
    "refactor": ("代码重构", "Refactoring"), "perf": ("性能优化", "Performance"),
    "chore": ("维护", "Maintenance"), "revert": ("回退", "Reverts"),
}


def package_info(root, tag, target, preview, build_dir=None):
    directory = Path(build_dir) if build_dir else Path(root) / "build"
    name = f"firmware-selector-{tag}.zip"
    archive = directory / name
    try:
        checksum, filename = (directory / (name + ".sha256")).read_text(encoding="utf-8").split()
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        info = json.loads((directory / "build-info.json").read_text(encoding="utf-8"))
        with ZipFile(archive) as bundle:
            packaged_info = json.loads(bundle.read("build-info.json"))
            count = len(bundle.infolist())
            if bundle.testzip():
                raise ValueError("ZIP 文件完整性检查失败")
    except (OSError, BadZipFile, KeyError, json.JSONDecodeError) as error:
        raise ValueError("缺少或损坏的站点产物；请先运行 build_site.py --version <标签>") from error
    if filename != name or checksum != digest:
        raise ValueError("ZIP 文件名或 SHA-256 校验不匹配")
    if not isinstance(info, dict) or info != packaged_info or info.get("source_sha") != target or info.get("version") != tag:
        raise ValueError("构建信息与标签、源码或包内信息不一致")
    if type(info.get("source_dirty")) is not bool or (info["source_dirty"] and not preview):
        raise ValueError("正式发布要求干净的站点源码")
    return {"name": name, "sha256": digest, "bytes": archive.stat().st_size, "files": count}


def commit_sections(commits, repository, language):
    groups = {}
    for commit in commits:
        sha, subject = commit.split(" ", 1)
        kind = re.match(r"([a-z]+)(?:\([^)]*\))?!?: ", subject)
        group = GROUPS.get(kind[1], ("其他调整", "Other changes")) if kind else ("其他调整", "Other changes")
        subject = re.sub(r"([\\`*_{}\[\]<>|])", r"\\\1", subject)
        groups.setdefault(group[language], []).append(
            f"- {subject} ([`{sha[:8]}`](https://github.com/{repository}/commit/{sha}))"
        )
    if not groups:
        return "本版本没有新的个人非合并提交。\n" if language == 0 else "No new personal non-merge commits.\n"
    return "\n".join(f"### {group}\n\n" + "\n".join(entries) + "\n" for group, entries in groups.items())


def release_notes(root, tag, previous="", upstream_ref="main", develop_ref="develop", *,
                  repository="", run_url="", preview=False, build_dir=None, verify_rendered=False):
    root = Path(root)
    validate_tag(tag)
    target = resolve_ref(root, "HEAD" if preview else "refs/tags/" + tag)
    if target != resolve_ref(root, "HEAD"):
        raise ValueError("当前检出必须与发布标签指向同一提交")
    policy_base = baseline(root)
    upstream = upstream_snapshot(root, upstream_ref)
    require_project_source(root, target, upstream, develop_ref)
    if not previous:
        same_tag = tag in git(root, "tag", "--points-at", target).splitlines()
        try:
            previous = git(root, "describe", "--tags", "--match", "site-v[0-9]*",
                           "--abbrev=0", target + "^" if same_tag else target)
            validate_tag(previous)
        except ValueError:
            previous = policy_base
    start = resolve_ref(root, previous)
    require_ancestor(root, start, target)
    commits = git(root, "log", "--no-merges", "--reverse", "--format=%H %s",
                  start + ".." + target, "--not", policy_base, upstream).splitlines()
    repository = repository_name(root, repository)
    repo_url = f"https://github.com/{repository}"
    if run_url and not re.fullmatch(re.escape(repo_url) + r"/actions/runs/[0-9]+", run_url):
        raise ValueError("运行链接必须属于本仓库的 GitHub Actions")
    content = [load_content(root, target, tag, language, repository, preview) for language in ("zh-CN", "en")]
    package = package_info(root, tag, target, preview, build_dir)
    names = [package["name"], package["name"] + ".sha256", "build-info.json", "release-notes.md"]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    prerelease = "-beta." in tag or "-rc." in tag
    changed = len(git(root, "diff", "--name-only", start, target).splitlines())
    compare_url = f"{repo_url}/compare/{start}...{tag}"
    compare = f"[{previous}]({compare_url})"
    lines = [
        f"# Wrt Selector {tag}", "",
        "[简体中文](#user-content-release-zh-cn) · [English](#user-content-release-en)", "",
    ]
    if preview:
        lines += [
            "> 本地预览：说明取自工作区，未验证云端检查或发布；链接在标签/资产上传前可能尚不存在。",
            "> Local preview: working-tree content; cloud checks and publication are not verified. Tag/asset links may not exist yet.", "",
        ]
    for index, language in enumerate(("zh-CN", "en")):
        chinese = index == 0
        title = "简体中文发布说明" if chinese else "English release notes"
        lines += [f'<h2 id="release-{language.lower()}">{title}</h2>', ""]
        lines += ["## 发布信息" if chinese else "## Release information", ""]
        values = [
            ("版本 / Version", f"`{tag}` — " + ("预发布 / Prerelease" if prerelease else "正式版 / Stable")),
            ("源码 / Source", f"[`{target}`]({repo_url}/commit/{target})"),
            ("变更基线 / Baseline", compare),
            ("排除的上游 / Excluded upstream", f"[`{upstream}`]({repo_url}/commit/{upstream})"),
            ("个人提交 / Personal commits", str(len(commits))),
            ("区间变更文件 / Files in comparison", str(changed)),
            ("说明生成时间 / Notes generated", generated),
        ]
        lines += ["| 项目 / Item | 内容 / Value |", "| --- | --- |"]
        lines += [f"| {label} | {value} |" for label, value in values]
        lines += [""]
        if run_url:
            lines += [
                f"检查与构建结果见[本次工作流]({run_url})；实际发布时间以 Release 页面为准。" if chinese
                else f"See [this workflow]({run_url}) for check/build results; the Release page records the actual publication time.", "",
            ]
        else:
            lines += ["未提供云端运行记录，不据此宣称检查或发布完成。" if chinese
                      else "No cloud run was supplied; no claim of completed checks or publication is made.", ""]
        lines += [content[index], "", "## 更新记录" if chinese else "## Changes", ""]
        lines += ["仅列个人非合并提交，上游镜像历史已排除；区间文件对比可能包含合入的上游更新。" if chinese
                  else "Personal non-merge commits only; upstream history is excluded. File comparisons may include merged upstream updates. Commit titles retain their original Chinese.", ""]
        lines += [commit_sections(commits, repository, index), ""]
        lines += ["## 完整更新日志" if chinese else "## Full changelog", "",
                  f"[{previous} → {tag}]({compare_url})", "",
                  "查看此版本区间的全部提交与文件变更，包含合入的上游更新。" if chinese
                  else "View all commits and file changes between these versions, including merged upstream updates.", ""]
        lines += ["## 构建产物与校验" if chinese else "## Assets and verification", ""]
        lines += ["网站包不包含路由器固件，也不会自动提交 ASU 构建。" if chinese
                  else "The website ZIP is not router firmware and does not submit ASU builds.", ""]
        descriptions = (
            [f"静态网站，{package['bytes']:,} 字节 / {package['files']} 个文件", "ZIP 的 SHA-256 校验文件",
             "版本、源码 SHA、源码日期及未提交标记", "与本页正文一致的完整双语说明"]
            if chinese else
            [f"Static website, {package['bytes']:,} bytes / {package['files']} files", "ZIP SHA-256 checksum",
             "Version, source SHA/date and dirty flag", "Complete bilingual notes, identical to this body"]
        )
        lines += ["| 文件 / File | 用途 / Purpose |", "| --- | --- |"]
        lines += [f"| [{name}]({repo_url}/releases/download/{tag}/{name}) | {description} |"
                  for name, description in zip(names, descriptions)]
        lines += ["", f"SHA-256: `{package['sha256']}`", "",
                  "```sh", f"sha256sum -c {package['name']}.sha256", "```", "",
                  "```powershell", f'Get-FileHash -Algorithm SHA256 "{package["name"]}"', "```", ""]
        lines += ["GitHub 的 Source code 压缩包包含整个仓库；直接部署请使用上表网站 ZIP，核对校验值后将内容解压到 Web 根目录。" if chinese
                  else "GitHub Source code archives contain the full repository. For direct deployment, verify the website ZIP above and extract its contents into the web root.", ""]
    markdown = "\n".join(lines)
    if len(markdown) > 125000:
        raise ValueError("发布说明超过 125000 字符，请精简版本内容")
    validate_links(markdown, root, target, tag, repository, names, preview)
    if verify_rendered:
        html = render_markdown(markdown, repository)
        validate_links(markdown, root, target, tag, repository, names, preview, html)
    return markdown


if __name__ == "__main__":
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--previous", default="")
    parser.add_argument("--upstream-ref", default="main")
    parser.add_argument("--develop-ref", default="develop")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--run-url", default="")
    parser.add_argument("--build-dir", default="build")
    parser.add_argument("--preview", action="store_true", help="Use HEAD and working-tree notes without creating a tag or release")
    parser.add_argument("--verify-rendered-links", action="store_true", help="Check GitHub-rendered Markdown using authenticated gh")
    parser.add_argument("--output", default="build/release-notes.md")
    args = parser.parse_args()
    try:
        content = release_notes(
            ROOT, args.tag, args.previous, args.upstream_ref, args.develop_ref,
            repository=args.repository, run_url=args.run_url, build_dir=args.build_dir,
            preview=args.preview, verify_rendered=args.verify_rendered_links,
        )
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
        print(destination)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, str(error) + "\n")
