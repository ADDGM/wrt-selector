"""Package tracked website files without changing the source configuration."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from workflow_utils import ROOT, configure_console, git, resolve_ref


MARKER = "firmware-selector-build-v1\n"


def build_site(root=ROOT, version=""):
    root = Path(root).resolve()
    source_sha = resolve_ref(root, "HEAD")
    version = version or git(root, "describe", "--tags", "--match", "site-v[0-9]*", "--always", "HEAD")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,99}", version):
        raise ValueError("版本标识只能包含字母、数字、点、下划线、加号和连字符")
    entries = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--stage", "-z", "--", "www/"]
    ).decode("utf-8").split("\0")
    files = {}
    for entry in filter(None, entries):
        metadata, name = entry.split("\t", 1)
        mode, _, stage = metadata.split()
        source = root / name
        if mode not in {"100644", "100755"} or stage != "0" or source.is_symlink():
            raise ValueError(f"不支持未合并文件或符号链接：{name}")
        if not source.resolve().is_relative_to(root / "www"):
            raise ValueError(f"站点文件越界：{name}")
        files[name.removeprefix("www/")] = source.read_bytes()
    for required in ("index.html", "index.css", "config.js", "js/main.js"):
        if required not in files:
            raise ValueError(f"站点缺少文件：{required}")
    main = files["js/main.js"].decode("utf-8")
    if main.count('"%GIT_VERSION%"') != 1:
        raise ValueError("main.js 必须包含唯一的版本占位符")
    files["js/main.js"] = main.replace('"%GIT_VERSION%"', json.dumps(version)).encode()
    files["LICENSE"] = (root / "LICENSE").read_bytes()
    timestamp = int(git(root, "show", "-s", "--format=%ct", "HEAD"))
    info = {
        "version": version,
        "source_sha": source_sha,
        "source_dirty": bool(git(root, "status", "--porcelain", "--untracked-files=no", "--", "www/", "LICENSE")),
        "source_date": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
    }
    files["build-info.json"] = (json.dumps(info, indent=2) + "\n").encode()
    output = root / "build"
    site = output / "site"
    marker = output / ".firmware-selector-build"
    archive = output / f"firmware-selector-{version}.zip"
    outputs = (output, site, marker, archive, archive.with_suffix(".zip.sha256"), output / "build-info.json")
    if any(path.is_symlink() or not path.resolve().is_relative_to(root) for path in outputs):
        raise ValueError("构建输出不能是符号链接")
    if site.exists():
        if not marker.is_file() or marker.read_text() != MARKER:
            raise ValueError("build/site 不是本工具生成的目录，拒绝覆盖")
        shutil.rmtree(site)
    site.mkdir(parents=True)
    marker.write_text(MARKER)
    zip_date = datetime.fromtimestamp(max(timestamp, 315532800), timezone.utc).timetuple()[:6]
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        for name, data in sorted(files.items()):
            destination = site / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            item = ZipInfo(name, zip_date)
            item.create_system = 3
            item.compress_type = ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            bundle.writestr(item, data)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{checksum}  {archive.name}\n", encoding="utf-8", newline="\n"
    )
    (output / "build-info.json").write_bytes(files["build-info.json"])
    return archive


if __name__ == "__main__":
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="")
    args = parser.parse_args()
    try:
        print(build_site(version=args.version))
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")
