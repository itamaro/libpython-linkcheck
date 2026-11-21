"""Warn when an imported Python extension directly links to libpython.

Call :func:`enable` to install an audit hook in the current interpreter.
Before CPython loads an extension module, the hook reads the shared object's
own DT_NEEDED entries and issues a :class:`LibpythonLinkWarning` if one of
them names libpython. The warning goes through the normal warnings
machinery, so filters apply; with ``-Werror`` the import fails before the
object is loaded.
"""

from ._elf import ELFError, libpython_dependencies
from ._hook import LibpythonLinkWarning, enable, is_enabled
from ._version import __version__

__all__ = [
    "ELFError",
    "LibpythonLinkWarning",
    "__version__",
    "enable",
    "is_enabled",
    "libpython_dependencies",
]
