"""Compile the C fixture extension modules for the running interpreter.

Fixtures are built into a pytest temporary directory at test time. They are
never part of the package, the wheel, or any wheel repair step.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path

FIXTURE_SRC = Path(__file__).parent / "fixtures" / "extmod.c"
IS_LINUX = sys.platform.startswith("linux")


def readelf_needed(path: str | Path) -> list[str]:
    """DT_NEEDED entries according to binutils' readelf (the independent oracle)."""
    out = subprocess.run(
        ["readelf", "--dynamic", "--wide", str(path)], capture_output=True, text=True, check=True
    ).stdout
    return re.findall(r"\(NEEDED\)\s+Shared library: \[(.*)\]", out)


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class Ext:
    name: str
    path: Path
    #: The libpython DT_NEEDED entries the linker was asked to record.
    expected_libpython: tuple[str, ...]


@dataclass(frozen=True)
class Exts:
    dir: Path
    #: Linked to the versioned libpython (e.g. libpython3.15.so.1.0).
    linked: Ext
    #: Linked to the Stable ABI forwarding library libpython3.so.
    abi3: Ext
    #: Control: not linked to libpython at all.
    unlinked: Ext

    def __iter__(self):
        return iter((self.linked, self.abi3, self.unlinked))


def compiler() -> list[str]:
    return shlex.split(os.environ.get("CC") or "cc")


def build_fixtures(outdir: Path) -> Exts:
    cfg = sysconfig.get_config_vars()
    if not cfg.get("Py_ENABLE_SHARED"):
        raise BuildError("the interpreter has no shared libpython to link fixtures against")
    libdir = cfg["LIBDIR"]
    soname = cfg["INSTSONAME"]
    suffix = cfg["EXT_SUFFIX"]
    include = sysconfig.get_paths()["include"]
    common = [
        *compiler(),
        "-shared",
        "-fPIC",
        "-O1",
        "-std=gnu11",
        "-Wall",
        "-Wextra",
        "-Werror",
        f"-I{include}",
    ]
    # --no-as-needed makes the linker record libpython even if a future
    # toolchain default (--as-needed) would consider it unused. The tests
    # still assert the resulting DT_NEEDED entries independently.
    link_libpython = ["-Wl,--no-as-needed", f"-L{libdir}", f"-Wl,-rpath,{libdir}"]

    def build(name: str, link: list[str], expected: tuple[str, ...]) -> Ext:
        out = outdir / f"{name}{suffix}"
        cmd = [*common, f"-DMODNAME={name}", str(FIXTURE_SRC), "-o", str(out), *link]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or proc.stderr.strip():
            raise BuildError(f"{shlex.join(cmd)}\n{proc.stdout}{proc.stderr}")
        return Ext(name, out, expected)

    return Exts(
        dir=outdir,
        linked=build("linked_ext", [*link_libpython, f"-lpython{cfg['LDVERSION']}"], (soname,)),
        abi3=build("abi3_linked_ext", [*link_libpython, "-lpython3"], ("libpython3.so",)),
        unlinked=build("unlinked_ext", ["-Wl,--as-needed"], ()),
    )
