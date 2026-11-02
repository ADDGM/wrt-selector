"""Validate new human-authored commit subjects without rewriting upstream."""

import argparse
import re

from workflow_utils import ROOT, baseline, configure_console, git, require_ancestor, resolve_ref, upstream_snapshot


SUBJECT_PATTERN = re.compile(
    r"(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\([a-z0-9][a-z0-9._/-]*\))?!?: (\S.*)\Z"
)
BOTS = {"dependabot[bot]", "renovate[bot]", "github-actions[bot]"}


def validate_subject(subject):
    match = SUBJECT_PATTERN.fullmatch(subject)
    if not match:
        return "须使用 type(scope): 中文标题，scope 可省略"
    if len(subject) > 72:
        return "提交标题不能超过 72 个字符"
    if not re.search(r"[\u3400-\u9fff]", match.group(1)):
        return "标题正文须包含中文"
    return None


def check_commits(root=ROOT, base="", head="HEAD", upstream_ref="main"):
    head = resolve_ref(root, head or "HEAD")
    policy_base = baseline(root)
    require_ancestor(root, policy_base, head)
    upstream = upstream_snapshot(root, upstream_ref)
    if not base or set(base) == {"0"}:
        base = policy_base
    else:
        base = resolve_ref(root, base)
    commits = git(root, "rev-list", "--reverse", "--no-merges", head,
                  "^" + base, "^" + policy_base, "^" + upstream).splitlines()
    failures = []
    for commit in commits:
        author, subject = git(root, "show", "-s", "--format=%an%n%s", commit).split("\n", 1)
        if author in BOTS:
            continue
        problem = validate_subject(subject)
        if problem:
            failures.append(f"{commit[:8]} {subject}: {problem}")
    if failures:
        raise ValueError("\n".join(failures))
    return len(commits)


if __name__ == "__main__":
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--upstream-ref", default="main")
    args = parser.parse_args()
    try:
        count = check_commits(base=args.base, head=args.head, upstream_ref=args.upstream_ref)
        print(f"提交规范通过：检查 {count} 条个人非合并提交")
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")
