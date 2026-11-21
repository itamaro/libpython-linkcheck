"""Smoke test for an installed libpython-linkcheck distribution.

Run with ``python -I`` from outside the checkout. It must not rely on any
test-only dependency.
"""

import importlib.metadata
import os
import sys
import sysconfig
from pathlib import Path

import libpython_linkcheck

location = Path(libpython_linkcheck.__file__).resolve()
purelib = Path(sysconfig.get_path("purelib")).resolve()
platlib = Path(sysconfig.get_path("platlib")).resolve()
if not (location.is_relative_to(purelib) or location.is_relative_to(platlib)):
    sys.exit(f"imported from {location}, expected the installed copy under {purelib}")

version = importlib.metadata.version("libpython-linkcheck")
if libpython_linkcheck.__version__ != version:
    sys.exit(f"__version__ {libpython_linkcheck.__version__!r} != metadata {version!r}")

from libpython_linkcheck import _elf  # noqa: E402

expected = os.environ.get("LINKCHECK_EXPECT_IMPLEMENTATION")
if expected and expected != _elf.IMPLEMENTATION:
    sys.exit(f"implementation is {_elf.IMPLEMENTATION!r}, expected {expected!r}")

print(f"smoke OK: libpython-linkcheck {version} ({_elf.IMPLEMENTATION}) at {location.parent}")
