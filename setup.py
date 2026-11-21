"""Build configuration for the optional C implementation.

All metadata lives in pyproject.toml. This file only declares the
``libpython_linkcheck._native`` extension module, which is built on POSIX
platforms unless ``LIBPYTHON_LINKCHECK_PURE=1`` is set (then the package
is pure Python and uses its Python implementation).
"""

import os

from setuptools import Extension, setup

CSRC = "src/csrc"


def ext_modules():
    if os.environ.get("LIBPYTHON_LINKCHECK_PURE") == "1" or os.name != "posix":
        return []
    return [
        Extension(
            "libpython_linkcheck._native",
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
            extra_compile_args=["-Wall", "-Wextra", "-Wshadow", "-Wstrict-prototypes"],
        )
    ]


setup(ext_modules=ext_modules())
