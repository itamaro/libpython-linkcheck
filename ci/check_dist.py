"""Verify the contents and metadata of built distributions.

Usage: python ci/check_dist.py REPO_ROOT DIST_DIR [--native-wheels]

Checks that:
* there is exactly one sdist, and at least one wheel, named for the current version;
* the sdist contains every file needed to build and test (all of src/ and
  tests/, the build configuration, README and LICENSE) and nothing from
  repository-only tooling;
* each wheel contains every package file, no tests, and correct metadata;
* the pure-Python wheel is tagged py3-none-any;
* each native wheel is tagged manylinux_2_28 for one CPython build, and none
  of its shared objects has a DT_NEEDED entry for libpython (checked with
  this repository's own pure-Python reader);
* with --native-wheels, the native wheels are exactly the expected set.
"""

from __future__ import annotations

import ast
import email.parser
import re
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

DIST_NAME = "libpython-linkcheck"
PROJECT = "libpython_linkcheck"
SDIST_REQUIRED_TOP = [
    "pyproject.toml",
    "setup.py",
    "README.md",
    "LICENSE",
    "MANIFEST.in",
    "PKG-INFO",
]
#: CPython builds and architectures that get a native wheel ([tool.cibuildwheel]).
NATIVE_PYTHONS = ["cp311", "cp312", "cp313", "cp314", "cp314t", "cp315", "cp315t"]
NATIVE_ARCHES = ["x86_64", "aarch64"]
NATIVE_TAG = re.compile(r"(cp3\d+)-(cp3\d+t?)-manylinux_2_28_(x86_64|aarch64)")
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


def check_wheel(repo: Path, wheel: Path, version: str) -> str | None:
    """Check one wheel; return "<abi>-<arch>" for a native wheel, None if pure."""
    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
        dist_info = f"{PROJECT}-{version}.dist-info"
        for path in tracked_files(repo, f"src/{PROJECT}"):
            arcname = path.removeprefix("src/")
            if arcname not in names:
                fail(f"{wheel.name} is missing {arcname}")
        sources = sorted(n for n in names if n.endswith((".c", ".h")))
        if sources:
            fail(f"{wheel.name} contains C sources: {sources}")
        stray = sorted(n for n in names if not n.startswith((f"{PROJECT}/", f"{dist_info}/")))
        if stray:
            fail(f"{wheel.name} contains files outside the package: {stray}")
        if f"{dist_info}/licenses/LICENSE" not in names:
            fail(f"{wheel.name} does not contain licenses/LICENSE")
        check_metadata(zf.read(f"{dist_info}/METADATA"), version, wheel.name)
        wheel_meta = email.parser.BytesParser().parsebytes(zf.read(f"{dist_info}/WHEEL"))
        tags = wheel_meta.get_all("Tag", [])
        shared = sorted(n for n in names if n.endswith(".so") or ".so." in n)
        if not shared:
            if tags != ["py3-none-any"]:
                fail(f"{wheel.name}: pure-Python wheel has tags {tags}")
            print(f"check_dist: {wheel.name}: {len(names)} files OK")
            return None
        if len(tags) != 1 or not (m := NATIVE_TAG.fullmatch(tags[0])):
            fail(f"{wheel.name}: native wheel tags {tags} are not one manylinux_2_28 CPython tag")
        if [n for n in shared if not n.startswith(f"{PROJECT}/_native.")]:
            fail(f"{wheel.name}: unexpected shared objects {shared} (vendored libraries?)")
        with tempfile.TemporaryDirectory() as tmp:
            for name in shared:
                path = Path(zf.extract(name, tmp))
                needed = py_read_needed(path)
                if [n for n in needed if py_is_libpython(n)]:
                    fail(f"{wheel.name}: {name} links libpython: DT_NEEDED {needed}")
                print(f"check_dist: {wheel.name}: {name}: DT_NEEDED {needed}")
    abi = m.group(2)
    print(f"check_dist: {wheel.name}: {len(names)} files OK")
    return f"{abi}-{m.group(3)}"


def main() -> None:
    repo, dist = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    expect_native = "--native-wheels" in sys.argv[3:]
    # The repository's own pure-Python reader checks the shipped objects.
    sys.path.insert(0, str(repo / "src"))
    global py_read_needed, py_is_libpython  # noqa: PLW0603
    from libpython_linkcheck._elf import py_is_libpython, py_read_needed  # noqa: PLC0415

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
    native, pure = [], 0
    for wheel in wheels:
        if not wheel.name.startswith(f"{PROJECT}-{version}-"):
            fail(f"wheel {wheel.name} does not match version {version}")
        key = check_wheel(repo, wheel, version)
        if key is None:
            pure += 1
        else:
            native.append(key)
    if pure != 1:
        fail(f"expected exactly one pure-Python wheel, found {pure}")
    if len(native) != len(set(native)):
        fail(f"duplicate native wheels: {sorted(native)}")
    if expect_native:
        expected = {f"{py}-{arch}" for py in NATIVE_PYTHONS for arch in NATIVE_ARCHES}
        if set(native) != expected:
            fail(
                f"native wheels: missing {sorted(expected - set(native))}, "
                f"unexpected {sorted(set(native) - expected)}"
            )
    print(f"check_dist: {len(native)} native wheels, 1 pure-Python wheel, 1 sdist OK")


if __name__ == "__main__":
    main()
