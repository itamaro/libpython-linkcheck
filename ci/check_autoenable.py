"""Check the wheel of the opt-in autoenable distribution (autoenable/).

Usage: python ci/check_autoenable.py REPO_ROOT WHEEL

* its version, and its pinned libpython-linkcheck dependency, equal
  libpython-linkcheck's __version__;
* it contains exactly the two startup files (byte-identical to autoenable/)
  at the root of site-packages, plus its .dist-info with the MIT LICENSE.
"""

import email.parser
import sys
import zipfile
from pathlib import Path

from check_dist import fail, read_version

PROJECT = "libpython_linkcheck_autoenable"
STARTUP_FILES = [f"{PROJECT}.pth", f"{PROJECT}.start"]


def main() -> None:
    repo, wheel = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    version = read_version(repo)
    if wheel.name != f"{PROJECT}-{version}-py3-none-any.whl":
        fail(f"{wheel.name}: expected {PROJECT}-{version}-py3-none-any.whl")
    if (repo / "autoenable" / "LICENSE").read_bytes() != (repo / "LICENSE").read_bytes():
        fail("autoenable/LICENSE differs from LICENSE")
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
        meta = email.parser.BytesParser().parsebytes(zf.read(f"{dist_info}/METADATA"))
    requires = meta.get_all("Requires-Dist", [])
    if requires != [f"libpython-linkcheck=={version}"]:
        fail(f"{wheel.name}: Requires-Dist {requires}")
    print(f"check_autoenable: {wheel.name} OK")


if __name__ == "__main__":
    main()
