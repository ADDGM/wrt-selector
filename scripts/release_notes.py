"""Generate Chinese release notes from an existing, checked-out tag."""

import argparse
import re
from pathlib import Path

from workflow_utils import ROOT, baseline, configure_console, git, require_ancestor, require_project_source, resolve_ref, upstream_snapshot, validate_tag


GROUPS = {
    "feat": "新功能", "fix": "问题修复", "style": "界面调整",
    "docs": "文档", "test": "测试", "ci": "持续集成",
    "build": "构建与依赖", "refactor": "代码重构", "perf": "性能优化",
    "chore": "维护", "revert": "回退",
}


def release_notes(root, tag, previous="", upstream_ref="main", develop_ref="develop"):
    validate_tag(tag)
    target = resolve_ref(root, "refs/tags/" + tag)
    if target != resolve_ref(root, "HEAD"):
        raise ValueError("当前检出必须与发布标签指向同一提交")
    policy_base = baseline(root)
    upstream = upstream_snapshot(root, upstream_ref)
    require_project_source(root, target, upstream, develop_ref)
    if not previous:
        try:
            previous = git(root, "describe", "--tags", "--match", "site-v[0-9]*", "--abbrev=0", target + "^")
        except ValueError:
            previous = policy_base
    start = resolve_ref(root, previous)
    require_ancestor(root, start, target)
    commits = git(root, "log", "--no-merges", "--reverse", "--format=%h %s",
                  start + ".." + target, "--not", policy_base, upstream).splitlines()
    groups = {}
    for commit in commits:
        sha, subject = commit.split(" ", 1)
        kind = re.match(r"([a-z]+)(?:\([^)]*\))?!?: ", subject)
        group = GROUPS.get(kind.group(1), "其他调整") if kind else "其他调整"
        subject = re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", subject)
        groups.setdefault(group, []).append(f"- {subject} (`{sha}`)")
    lines = [f"# 固件选择器 {tag}", "", f"源码提交：`{target}`", "",
             f"排除的上游镜像提交：`{upstream}`", "",
             "发布包是可部署的静态选择器网站，解压到 Web 根目录即可使用。",
             "它不包含路由器固件，也不会自动提交 ASU 构建。", ""]
    if not groups:
        lines.extend(["本版本没有新的非合并提交。", ""])
    for group, entries in groups.items():
        lines.extend([f"## {group}", "", *entries, ""])
    lines.extend(["## 文件校验", "", "使用同名 `.zip.sha256` 校验文件验证 ZIP；源码版本见 `build-info.json`。", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--previous", default="")
    parser.add_argument("--upstream-ref", default="main")
    parser.add_argument("--develop-ref", default="develop")
    parser.add_argument("--output", default="build/release-notes.zh-CN.md")
    args = parser.parse_args()
    try:
        content = release_notes(ROOT, args.tag, args.previous, args.upstream_ref, args.develop_ref)
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        print(destination)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")
