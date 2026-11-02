"""Shared Git and version handling for local and GitHub Actions commands."""

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAG_PATTERN = re.compile(
    r"site-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:beta|rc)\.(?:0|[1-9][0-9]*))?\Z"
)


def configure_console():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")


def git(root, *args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], stderr=subprocess.PIPE
        ).decode("utf-8").strip()
    except subprocess.CalledProcessError as error:
        raise ValueError(error.stderr.decode("utf-8", errors="replace").strip()) from error


def resolve_ref(root, ref):
    return git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")


def baseline(root):
    ref = (Path(root) / ".github/commit-policy-baseline.txt").read_text().strip()
    return resolve_ref(root, ref)


def is_ancestor(root, ancestor, head):
    result = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, head],
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.returncode == 0


def require_ancestor(root, ancestor, head):
    if not is_ancestor(root, ancestor, head):
        raise ValueError("基线必须是目标提交的祖先")


def upstream_snapshot(root, ref="main"):
    try:
        snapshot = resolve_ref(root, ref)
    except ValueError as error:
        raise ValueError("找不到上游镜像；请先同步 main，或用 --upstream-ref 指定镜像提交") from error
    policy_base = baseline(root)
    if not (is_ancestor(root, policy_base, snapshot) or is_ancestor(root, snapshot, policy_base)):
        raise ValueError("上游镜像与二次开发基线不在同一条上游历史中")
    return snapshot


def require_project_source(root, target, upstream, develop="develop"):
    require_ancestor(root, baseline(root), target)
    if target == baseline(root) or is_ancestor(root, target, upstream):
        raise ValueError("不能发布纯上游提交")
    if not is_ancestor(root, target, resolve_ref(root, develop)):
        raise ValueError("发布提交必须已合入 develop")


def validate_tag(tag):
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("标签须为 site-vX.Y.Z、site-vX.Y.Z-beta.N 或 site-vX.Y.Z-rc.N")
    return tag
