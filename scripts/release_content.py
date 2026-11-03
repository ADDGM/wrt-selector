"""Load versioned editorial content and validate Release Markdown links."""

import json
import posixpath
import re
import subprocess
from collections import Counter
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from workflow_utils import git, resolve_ref


SECTIONS = {
    "zh-CN": ("本版本重点", "运行环境", "使用与部署", "已知限制", "鸣谢"),
    "en": ("Highlights", "Requirements", "Usage and deployment", "Known limitations", "Acknowledgements"),
}
LINK = re.compile(r"(?<!\\)(!?\[[^\]\n]*\])\(([^\s)]+)\)")


def without_code(markdown):
    return re.sub(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$", "", markdown)


def source_text(root, target, path, preview=False):
    if preview:
        file = Path(root) / path
        if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(Path(root).resolve()):
            raise ValueError(f"缺少或不支持的说明文件：{path}")
        return file.read_text(encoding="utf-8")
    entry = git(root, "ls-tree", target, "--", path)
    if not entry.startswith(("100644 blob ", "100755 blob ")):
        raise ValueError(f"标签内缺少常规文件：{path}；请在打标签前提交说明")
    return git(root, "show", f"{target}:{path}").replace("\r\n", "\n")


def repository_name(root, repository=""):
    if not repository:
        remote = git(root, "remote", "get-url", "origin")
        match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?", remote)
        if not match:
            raise ValueError("无法从 origin 识别 GitHub 仓库；请使用 --repository owner/repo")
        repository = match[1]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("仓库名称须为 owner/repo")
    return repository


def load_content(root, target, tag, language, repository, preview=False):
    path = f"docs/releases/{tag}.{language}.md"
    content = source_text(root, target, path, preview).strip()
    plain = without_code(content)
    if re.search(r"\b(?:TODO|TBD)\b|\{\{|\}\}", content, re.I):
        raise ValueError(f"{path} 仍有模板占位内容")
    if re.search(r"^# ", plain, re.M):
        raise ValueError(f"{path} 不应重复版本总标题，请从简介和二级标题开始")
    for section in SECTIONS[language]:
        heading = re.search(rf"^## {re.escape(section)}[ \t]*$", plain, re.M)
        if not heading:
            raise ValueError(f"{path} 缺少章节：{section}")
        body = re.split(r"(?m)^## ", plain[heading.end():], maxsplit=1)[0]
        if not body.strip():
            raise ValueError(f"{path} 章节不能为空：{section}")
    if re.search(r"^\s*\[[^\]]+\]:", plain, re.M):
        raise ValueError(f"{path} 请使用内联 Markdown 链接，便于固定版本路径")
    if re.search(r"<(?:a|img)\b", plain, re.I):
        raise ValueError(f"{path} 请使用 Markdown 链接；页内导航由生成器维护")

    def rewrite(match):
        label, destination = match.groups()
        url = urlsplit(destination)
        if url.scheme or url.netloc or destination.startswith("#"):
            return match[0]
        relative = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(url.path)))
        if relative.startswith("../") or relative.startswith("/") or "\\" in relative:
            raise ValueError(f"说明链接越界：{destination}")
        source_text(root, target, relative, preview)
        if url.query or url.fragment:
            raise ValueError("版本文档请链接到整份文件，不附加查询或片段")
        return f"{label}(https://github.com/{repository}/blob/{tag}/{quote(relative)})"

    # Keep code examples literal; only rewrite links outside fenced blocks.
    pieces = re.split(r"(?ms)^((?:`{3,}|~{3,})[^\n]*\n.*?^(?:`{3,}|~{3,})\s*$)", content)
    return "".join(piece if i % 2 else LINK.sub(rewrite, piece) for i, piece in enumerate(pieces))


class RenderedLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("id", "name"):
            if attrs.get(key):
                self.targets.add(attrs[key])
        for key in ("href", "src"):
            if key in attrs:
                self.links.append(attrs[key])


def render_markdown(markdown, repository):
    result = subprocess.run(
        ["gh", "api", "--hostname", "github.com", "markdown", "--input", "-"],
        input=json.dumps({"text": markdown, "mode": "gfm", "context": repository}),
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    if result.returncode:
        raise ValueError("GitHub Markdown 渲染失败；请检查 gh 登录和 API 可用性")
    return result.stdout


def validate_links(markdown, root, target, tag, repository, assets, preview=False, rendered_html=None):
    plain = without_code(markdown)
    expected = [match[2] for match in LINK.finditer(plain)]
    # Offline checks model only our explicit anchors. CI also checks GitHub's real HTML.
    if rendered_html is None:
        ids = re.findall(r'<h2 id="([^"]+)">', plain)
        rendered_html = "".join(f'<h2 id="user-content-{escape(name)}"></h2>' for name in ids)
        rendered_html += "".join(f'<a href="{escape(url, quote=True)}"></a>' for url in expected)
    parsed = RenderedLinks()
    parsed.feed(rendered_html)
    if Counter(expected) - Counter(parsed.links):
        raise ValueError("GitHub 渲染丢失或改写了 Markdown 链接")
    prefix = f"/{repository}/"
    for link in set(parsed.links):
        url = urlsplit(link)
        if link.startswith("#"):
            if unquote(url.fragment) not in parsed.targets:
                raise ValueError(f"发布说明锚点不存在：{link}")
            continue
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            raise ValueError(f"发布说明链接必须是无凭证的 HTTPS 地址：{link}")
        if url.netloc != "github.com" or not url.path.startswith(prefix):
            continue
        route = unquote(url.path[len(prefix):])
        if route.startswith("blob/"):
            version, separator, path = route[5:].partition("/")
            if version != tag or not separator or url.fragment or url.query:
                raise ValueError(f"版本文档链接须指向本标签的完整文件：{link}")
            source_text(root, target, path, preview)
        elif route.startswith("commit/"):
            sha = route[7:]
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                raise ValueError(f"提交链接必须使用完整 SHA：{link}")
            resolve_ref(root, sha)
        elif route.startswith("compare/"):
            start, separator, end = route[8:].partition("...")
            if not separator or end != tag:
                raise ValueError(f"版本对比链接错误：{link}")
            resolve_ref(root, start)
        elif route.startswith("releases/download/"):
            version, separator, name = route[18:].partition("/")
            if version != tag or not separator or name not in assets:
                raise ValueError(f"发布资产链接不存在：{link}")
        elif route not in ("", "issues", "releases") and not re.fullmatch(r"(?:actions/runs|issues|pull)/[0-9]+", route):
            raise ValueError(f"未识别的本仓库链接：{link}")
    return len(parsed.links)
