"""Smoke test for an installed native wheel (cibuildwheel's test step).

Usage: python ci/wheel_smoke.py PROJECT_DIR

Runs inside the manylinux build image, whose interpreters have no shared
libpython, so the real-extension suite cannot run here; it runs later
against the same repaired wheels in python:<ver>-trixie containers.
"""

import importlib.machinery
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

import libpython_linkcheck
from libpython_linkcheck import _elf

sys.path.insert(0, str(Path(sys.argv[1]) / "tests"))
from elfbuild import ElfSpec, build_elf

if _elf.IMPLEMENTATION != "native":
    sys.exit(f"expected the native implementation, got {_elf.IMPLEMENTATION!r}")

# The checker itself must not link libpython.
native_so = _elf._native.__file__
needed = libpython_linkcheck._elf.read_needed(native_so)
if libpython_linkcheck.libpython_dependencies(native_so):
    sys.exit(f"{native_so} links libpython: {needed}")
print(f"{Path(native_so).name}: DT_NEEDED {needed}")

if sysconfig.get_config_var("Py_GIL_DISABLED") and sys._is_gil_enabled():
    sys.exit("importing libpython_linkcheck re-enabled the GIL")

with tempfile.TemporaryDirectory() as tmp:
    suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    elf = build_elf(ElfSpec(needed=[b"libpython3.so", b"libc.so.6"]))
    (Path(tmp) / f"fake_linked{suffix}").write_bytes(elf)
    code = (
        "import libpython_linkcheck as m, sys\n"
        "assert m.enable() and not m.enable()\n"
        f"sys.path.insert(0, {tmp!r})\n"
        "try:\n"
        "    import fake_linked\n"
        "except m.LibpythonLinkWarning as w:\n"
        "    print('blocked', w.module, w.needed)\n"
        "import _ctypes, _ssl, _sqlite3\n"  # real stdlib extensions: none links libpython
    )
    out = subprocess.run(
        [sys.executable, "-Werror", "-c", code], capture_output=True, text=True, check=False
    )
    if out.returncode != 0 or out.stdout != "blocked fake_linked ('libpython3.so',)\n":
        sys.exit(f"hook smoke test failed:\n{out.stdout}{out.stderr}")

print(f"wheel smoke OK: {libpython_linkcheck.__version__} on {sys.version.split()[0]}")
