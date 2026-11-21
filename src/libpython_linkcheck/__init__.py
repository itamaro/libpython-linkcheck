"""Warn when an imported Python extension directly links to libpython."""

from ._elf import ELFError, libpython_dependencies
from ._version import __version__

__all__ = ["ELFError", "__version__", "libpython_dependencies"]
