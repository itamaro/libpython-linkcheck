"""Check the distributions of the opt-in autoenable companion (autoenable/).

Usage: python ci/check_autoenable.py REPO_ROOT DIR

DIR must hold exactly its sdist and its universal wheel, and:

* their version, and their exact libpython-linkcheck dependency, equal
  libpython-linkcheck's __version__;
* the wheel contains exactly the two startup files (byte-identical to
  autoenable/) at the root of site-packages, plus its .dist-info with the
  MIT LICENSE;
* the sdist contains exactly those files, README.md, LICENSE,
  pyproject.toml and .gitignore (byte-identical to autoenable/), plus PKG-INFO.
"""

import email.message
import email.parser
import sys
import tarfile
import zipfile
from pathlib import Path

from check_dist import fail, read_version

PROJECT = "libpython_linkcheck_autoenable"
STARTUP_FILES = [f"{PROJECT}.pth", f"{PROJECT}.start"]
#: hatchling always ships the nearest .gitignore, so autoenable/ has its own.
SDIST_FILES = sorted([*STARTUP_FILES, ".gitignore", "LICENSE", "README.md", "pyproject.toml"])


def check_metadata(name: str, meta: email.message.Message, version: str) -> None:
    if meta["Name"] != "libpython-linkcheck-autoenable" or meta["Version"] != version:
        fail(f"{name}: Name {meta['Name']!r}, Version {meta['Version']!r}")
    requires = meta.get_all("Requires-Dist", [])
    if requires != [f"libpython-linkcheck=={version}"]:
        fail(f"{name}: Requires-Dist {requires}")


def check_wheel(repo: Path, wheel: Path, version: str) -> None:
    dist_info = f"{PROJECT}-{version}.dist-info"
    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
        payload = sorted(n for n in names if not n.startswith(f"{dist_info}/"))
        if payload != STARTUP_FILES:
            fail(f"{wheel.name}: payload {payload}, expected {STARTUP_FILES}")
        for name in STARTUP_FILES:
            if zf.read(name) != (repo / "autoenable" / name).read_bytes():
                fail(f"{wheel.name}: {name} differs from autoenable/{name}")
        if f"{dist_info}/licenses/LICENSE" not in names:
            fail(f"{wheel.name}: no licenses/LICENSE")
        wheel_meta = email.parser.BytesParser().parsebytes(zf.read(f"{dist_info}/WHEEL"))
        meta = email.parser.BytesParser().parsebytes(zf.read(f"{dist_info}/METADATA"))
    if wheel_meta.get_all("Tag") != ["py3-none-any"] or wheel_meta["Root-Is-Purelib"] != "true":
        fail(f"{wheel.name}: WHEEL Tag {wheel_meta.get_all('Tag')}")
    check_metadata(wheel.name, meta, version)


def check_sdist(repo: Path, sdist: Path, version: str) -> None:
    root = f"{PROJECT}-{version}"
    with tarfile.open(sdist) as tf:
        members = {m.name: m for m in tf.getmembers() if m.isfile()}
        names = sorted(n.removeprefix(f"{root}/") for n in members)
        if names != sorted([*SDIST_FILES, "PKG-INFO"]):
            fail(f"{sdist.name}: files {names}")
        for name in SDIST_FILES:
            data = tf.extractfile(members[f"{root}/{name}"]).read()  # type: ignore[union-attr]
            if data != (repo / "autoenable" / name).read_bytes():
                fail(f"{sdist.name}: {name} differs from autoenable/{name}")
        pkg_info = tf.extractfile(members[f"{root}/PKG-INFO"]).read()  # type: ignore[union-attr]
    check_metadata(sdist.name, email.parser.BytesParser().parsebytes(pkg_info), version)


def main() -> None:
    repo, directory = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    version = read_version(repo)
    if (repo / "autoenable" / "LICENSE").read_bytes() != (repo / "LICENSE").read_bytes():
        fail("autoenable/LICENSE differs from LICENSE")
    wheel_name, sdist_name = f"{PROJECT}-{version}-py3-none-any.whl", f"{PROJECT}-{version}.tar.gz"
    found = sorted(p.name for p in directory.iterdir())
    if found != sorted([wheel_name, sdist_name]):
        fail(f"{directory}: {found}, expected {sdist_name} and {wheel_name}")
    check_wheel(repo, directory / wheel_name, version)
    check_sdist(repo, directory / sdist_name, version)
    print(f"check_autoenable: {sdist_name} and {wheel_name} OK")


if __name__ == "__main__":
    main()
