"""Check that each native wheel's extension uses only the ABI its tags promise.

Usage: python ci/check_abi.py WHEEL...

cibuildwheel runs this as its audit command (on the host, which may be
macOS, so the ELF symbol tables are read here rather than with binutils),
and the CI `check` job runs it on every wheel. For each shared object:

- Limited API wheels (``cpXY-abi3``, ``cpXY-abi3.abi3t``): every CPython
  symbol it imports must be in the Stable ABI of version X.Y, according to
  CPython's Misc/stable_abi.toml (pinned below). The Python tag is the
  floor: an abi3 build for 3.12 must not use a function added in 3.13, even
  when compiled with newer headers.
- ``cpXY-abi3`` with X.Y < 3.15: the extension is named ``*.abi3.so``, the
  only Stable ABI suffix those versions import.
- Every native wheel: no PySys_AddAuditHook (the embedder entry point,
  src/csrc/linkcheck_embed.c, is not part of the extension), and the only
  exported CPython symbol is the module's entry point: PyModExport__native
  (PEP 793) for abi3t, PyInit__native otherwise.
- ``cpXY-abi3`` wheels are also checked by abi3audit --strict (independent
  of this script; it does not know abi3t or PEP 793 export hooks yet).
"""

from __future__ import annotations

import hashlib
import re
import struct
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

#: The Stable ABI manifest of the newest CPython the wheels target.
STABLE_ABI_URL = "https://raw.githubusercontent.com/python/cpython/v3.15.2/Misc/stable_abi.toml"
STABLE_ABI_SHA256 = "1ae07a111f5a3f5869df912cb44afb4f2ef9e49d889f84b4457c9ca3f5a402e5"

CPYTHON_SYMBOL = re.compile(r"_?Py[A-Z_]")
SHT_DYNSYM = 11
STB_GLOBAL, STB_WEAK = 1, 2


def fail(msg: str) -> None:
    print(f"check_abi: FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def stable_abi() -> dict[str, tuple[int, int]]:
    """Stable ABI functions and data on Linux -> the version that added them."""
    with urllib.request.urlopen(STABLE_ABI_URL, timeout=60) as resp:
        raw = resp.read()
    if hashlib.sha256(raw).hexdigest() != STABLE_ABI_SHA256:
        fail(f"{STABLE_ABI_URL} does not match the pinned sha256")
    manifest = tomllib.loads(raw.decode())
    symbols = {}
    for kind in ("function", "data"):
        for name, item in manifest[kind].items():
            if item.get("ifdef") == "MS_WINDOWS":
                continue
            major, minor = item["added"].split(".")
            symbols[name] = (int(major), int(minor))
    return symbols


def dynamic_symbols(image: bytes) -> tuple[set[str], set[str]]:
    """(exported, undefined) names in an ELF object's dynamic symbol table."""
    if image[:4] != b"\x7fELF":
        fail("not an ELF object")
    end = "<" if image[5] == 1 else ">"
    if image[4] == 2:  # ELFCLASS64
        (shoff,) = struct.unpack_from(end + "Q", image, 0x28)
        shentsize, shnum = struct.unpack_from(end + "HH", image, 0x3A)
        shdr, sym = end + "IIQQQQIIQQ", end + "IBBHQQ"
    else:
        (shoff,) = struct.unpack_from(end + "I", image, 0x20)
        shentsize, shnum = struct.unpack_from(end + "HH", image, 0x2E)
        shdr, sym = end + "IIIIIIIIII", end + "IIIBBH"
    sections = [struct.unpack_from(shdr, image, shoff + i * shentsize) for i in range(shnum)]
    exported: set[str] = set()
    undefined: set[str] = set()
    for _, sh_type, _, _, offset, size, link, _, _, entsize in sections:
        if sh_type != SHT_DYNSYM:
            continue
        str_offset = sections[link][4]
        for i in range(1, size // entsize):  # entry 0 is the null symbol
            fields = struct.unpack_from(sym, image, offset + i * entsize)
            if image[4] == 2:
                st_name, st_info, _, st_shndx, _, _ = fields
            else:
                st_name, _, _, st_info, _, st_shndx = fields
            start = str_offset + st_name
            name = image[start : image.index(b"\0", start)].decode()
            if st_shndx == 0:
                undefined.add(name)
            elif st_info >> 4 in {STB_GLOBAL, STB_WEAK}:
                exported.add(name)
    return exported, undefined


def check_wheel(wheel: Path, abi_symbols: dict[str, tuple[int, int]]) -> None:
    _, _, python, abi, _ = wheel.name.removesuffix(".whl").split("-")
    if not (m := re.fullmatch(r"cp3(\d+)", python)):
        fail(f"{wheel.name}: unexpected Python tag {python}")
    floor = (3, int(m.group(1)))
    limited = abi in {"abi3", "abi3.abi3t"}
    entry = "PyModExport__native" if abi == "abi3.abi3t" else "PyInit__native"
    with zipfile.ZipFile(wheel) as zf:
        shared = [n for n in zf.namelist() if n.endswith(".so")]
        if not shared:
            fail(f"{wheel.name}: no extension module")
        for name in shared:
            exported, undefined = dynamic_symbols(zf.read(name))
            imported = sorted(s for s in undefined if CPYTHON_SYMBOL.match(s))
            if not imported:
                fail(f"{wheel.name}: {name} imports no CPython symbols (unreadable?)")
            if "PySys_AddAuditHook" in imported:
                fail(f"{wheel.name}: {name} imports PySys_AddAuditHook (embedder-only)")
            own = sorted(s for s in exported if CPYTHON_SYMBOL.match(s))
            if own != [entry]:
                fail(f"{wheel.name}: {name} exports {own}, expected [{entry!r}]")
            # CPython accepts the platform-qualified .abi3-<platform>.so only
            # from 3.15; earlier versions load .abi3.so.
            if abi == "abi3" and floor < (3, 15) and not name.endswith(".abi3.so"):
                fail(f"{wheel.name}: CPython {floor[0]}.{floor[1]} cannot import {name}")
            if limited:
                outside = [s for s in imported if s not in abi_symbols]
                newer = [s for s in imported if s in abi_symbols and abi_symbols[s] > floor]
                if outside or newer:
                    fail(
                        f"{wheel.name}: {name} is not Stable ABI {floor[0]}.{floor[1]}: "
                        f"not in the Stable ABI {outside}, added later {newer}"
                    )
            target = f"Stable ABI {floor[0]}.{floor[1]}" if limited else "version-specific"
            print(
                f"check_abi: {wheel.name}: {name}: {len(imported)} CPython symbols, "
                f"{target}, exports {entry} OK"
            )
    if abi == "abi3":
        cmd = [sys.executable, "-m", "abi3audit", "--strict", "--report", str(wheel)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            fail(f"{wheel.name}: abi3audit failed:\n{proc.stdout}{proc.stderr}")
        print(f"check_abi: {wheel.name}: abi3audit --strict OK")


def main() -> None:
    wheels = [Path(p) for p in sys.argv[1:]]
    if not wheels:
        fail("usage: check_abi.py WHEEL...")
    abi_symbols = stable_abi()
    for wheel in wheels:
        check_wheel(wheel, abi_symbols)


if __name__ == "__main__":
    main()
