"""Verify the contents and metadata of built distributions.

Usage: python ci/check_dist.py REPO_ROOT DIST_DIR

Checks that:
* there is exactly one sdist, and at least one wheel, named for the current version;
* the sdist contains every file needed to build and test (all of src/ and
  tests/, the build configuration, README and LICENSE) and nothing from
  repository-only tooling;
* each wheel contains every package file, no tests, and correct metadata.
"""

from __future__ import annotations

import ast
import email.parser
import sys
import tarfile
import zipfile
from pathlib import Path

DIST_NAME = "libpython-linkcheck"
PROJECT = "libpython_linkcheck"
SDIST_REQUIRED_TOP = ["pyproject.toml", "README.md", "LICENSE", "MANIFEST.in", "PKG-INFO"]
SDIST_FORBIDDEN_PREFIXES = [".github/", ".git/", "CLAUDE.md", "AGENTS.md", "Makefile", "ci/"]


def fail(msg: str) -> None:
    print(f"check_dist: FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def read_version(repo: Path) -> str:
    tree = ast.parse((repo / "src" / PROJECT / "_version.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == "__version__":
            return ast.literal_eval(node.value)
    fail("no __version__ in _version.py")
    raise AssertionError


def tracked_files(repo: Path, top: str) -> set[str]:
    out = set()
    for path in (repo / top).rglob("*"):
        if path.is_dir() or "__pycache__" in path.parts or path.suffix in {".pyc", ".so"}:
            continue
        out.add(path.relative_to(repo).as_posix())
    return out


def check_metadata(raw: bytes, version: str, where: str) -> None:
    msg = email.parser.BytesParser().parsebytes(raw)
    expected = {
        "Name": DIST_NAME,
        "Version": version,
        "Requires-Python": ">=3.11",
        "License-Expression": "MIT",
    }
    for key, value in expected.items():
        if msg.get(key) != value:
            fail(f"{where}: {key} is {msg.get(key)!r}, expected {value!r}")
    if "LICENSE" not in msg.get_all("License-File", []):
        fail(f"{where}: LICENSE not declared as License-File")


def check_sdist(repo: Path, sdist: Path, version: str) -> None:
    prefix = f"{PROJECT}-{version}/"
    with tarfile.open(sdist) as tf:
        members = {m.name: m for m in tf.getmembers()}
        for m in members.values():
            if not m.name.startswith(prefix.rstrip("/")):
                fail(f"sdist member outside {prefix}: {m.name}")
            if m.issym() or m.islnk():
                fail(f"sdist contains a link: {m.name}")
        names = {n[len(prefix) :] for n, m in members.items() if m.isfile()}
        required = set(SDIST_REQUIRED_TOP)
        required |= tracked_files(repo, "src") | tracked_files(repo, "tests")
        missing = sorted(required - names)
        if missing:
            fail(f"sdist is missing: {missing}")
        forbidden = sorted(n for n in names for p in SDIST_FORBIDDEN_PREFIXES if n.startswith(p))
        if forbidden:
            fail(f"sdist contains repository-only files: {forbidden}")
        pkg_info = tf.extractfile(prefix + "PKG-INFO")
        assert pkg_info is not None
        check_metadata(pkg_info.read(), version, sdist.name)
    print(f"check_dist: {sdist.name}: {len(names)} files OK")


def check_wheel(repo: Path, wheel: Path, version: str) -> None:
    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
        dist_info = f"{PROJECT}-{version}.dist-info"
        for path in tracked_files(repo, f"src/{PROJECT}"):
            arcname = path.removeprefix("src/")
            if arcname.endswith((".c", ".h")):
                continue
            if arcname not in names:
                fail(f"{wheel.name} is missing {arcname}")
        stray = sorted(n for n in names if not n.startswith((f"{PROJECT}/", f"{dist_info}/")))
        if stray:
            fail(f"{wheel.name} contains files outside the package: {stray}")
        if f"{dist_info}/licenses/LICENSE" not in names:
            fail(f"{wheel.name} does not contain licenses/LICENSE")
        check_metadata(zf.read(f"{dist_info}/METADATA"), version, wheel.name)
        wheel_meta = email.parser.BytesParser().parsebytes(zf.read(f"{dist_info}/WHEEL"))
        tags = wheel_meta.get_all("Tag", [])
        has_native = any(n.endswith(".so") for n in names)
        if not has_native and tags != ["py3-none-any"]:
            fail(f"{wheel.name}: pure-Python wheel has tags {tags}")
    print(f"check_dist: {wheel.name}: {len(names)} files OK")


def main() -> None:
    repo, dist = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    version = read_version(repo)
    sdists = sorted(dist.glob("*.tar.gz"))
    wheels = sorted(dist.glob("*.whl"))
    others = sorted(p.name for p in dist.iterdir() if p not in sdists and p not in wheels)
    if len(sdists) != 1:
        fail(f"expected exactly one sdist in {dist}, found {[p.name for p in sdists]}")
    if not wheels:
        fail(f"no wheels in {dist}")
    if others:
        fail(f"unexpected files in {dist}: {others}")
    if sdists[0].name != f"{PROJECT}-{version}.tar.gz":
        fail(f"sdist {sdists[0].name} does not match version {version}")
    check_sdist(repo, sdists[0], version)
    for wheel in wheels:
        if not wheel.name.startswith(f"{PROJECT}-{version}-"):
            fail(f"wheel {wheel.name} does not match version {version}")
        check_wheel(repo, wheel, version)


if __name__ == "__main__":
    main()
