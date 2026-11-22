"""Build configuration for the optional C implementation.

All metadata lives in pyproject.toml. This file only declares the
``libpython_linkcheck._native`` extension module, which is built on POSIX
platforms unless ``LIBPYTHON_LINKCHECK_PURE=1`` is set (then the package
is pure Python and uses its Python implementation).

The build interpreter selects the ABI (see ``native_target``):

- GIL-enabled CPython: the Stable ABI with a 3.12 floor, an ``.abi3.so``
  in a ``cp312-abi3`` wheel that every later GIL-enabled CPython loads;
- free-threaded CPython 3.15+: abi3t (PEP 803), an ``.abi3t.so`` in a
  ``cp315-abi3.abi3t`` wheel for GIL-enabled and free-threaded 3.15+;
- free-threaded CPython 3.14: the full C API (no Stable ABI exists there),
  a ``cp314-cp314t`` wheel.
"""

import os
import sys
import sysconfig

from setuptools import Extension, setup

CSRC = "src/csrc"

#: (define_macros, bdist_wheel py_limited_api) per target.
TARGETS = {
    "abi3": ([("Py_LIMITED_API", "0x030C0000")], "cp312"),
    "abi3t": ([("Py_TARGET_ABI3T", "0x030F0000")], "cp315"),
    "full": ([], None),
}


def native_target() -> str:
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        return "abi3t" if sys.version_info >= (3, 15) else "full"
    return "abi3"


def ext_modules(target: str) -> list[Extension]:
    macros, limited = TARGETS[target]
    return [
        Extension(
            "libpython_linkcheck._native",
            # linkcheck_embed.c is for embedders only: it calls
            # PySys_AddAuditHook(), which the Limited API does not provide.
            sources=[
                f"{CSRC}/_nativemodule.c",
                f"{CSRC}/linkcheck_hook.c",
                f"{CSRC}/linkcheck_elf.c",
            ],
            depends=[
                f"{CSRC}/linkcheck_elf.h",
                f"{CSRC}/linkcheck_hook.h",
                f"{CSRC}/libpython_linkcheck.h",
            ],
            define_macros=macros,
            py_limited_api=limited is not None,
            extra_compile_args=["-Wall", "-Wextra", "-Wshadow", "-Wstrict-prototypes"],
        )
    ]


if os.environ.get("LIBPYTHON_LINKCHECK_PURE") == "1" or os.name != "posix":
    setup(ext_modules=[])
else:
    target = native_target()
    limited = TARGETS[target][1]
    options = {"bdist_wheel": {"py_limited_api": limited}} if limited else {}
    setup(ext_modules=ext_modules(target), options=options)
