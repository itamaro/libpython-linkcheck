"""The audit hook that inspects extension modules before they are loaded."""

from __future__ import annotations

import os
import re
import sys
import threading
import warnings
from typing import Any

from ._elf import libpython_dependencies

#: Audit event used to ask "is a libpython-linkcheck hook installed here?".
#: Every hook implementation appends an identifier to the list passed as the
#: event's only argument. This lets ``enable()`` detect a hook installed by
#: another copy of this module (or, in future, by native code) without relying
#: on module globals.
PROBE_EVENT = "libpython_linkcheck.probe"

_enable_lock = threading.Lock()


class LibpythonLinkWarning(RuntimeWarning):
    """An extension module about to be loaded has a DT_NEEDED entry for libpython.

    Instances raised by the hook carry three attributes:

    ``module``
        The fully qualified name of the extension module being imported.
    ``filename``
        The path of the shared object CPython is about to load.
    ``needed``
        A tuple of the object's own DT_NEEDED entries that name libpython.
    """

    module: str | None = None
    filename: str | None = None
    needed: tuple[str, ...] = ()


# Report the public location in tracebacks and warning filters.
LibpythonLinkWarning.__module__ = "libpython_linkcheck"


def _make_warning(module: str, filename: str, needed: list[str]) -> LibpythonLinkWarning:
    warning = LibpythonLinkWarning(
        f"extension module {module!r} links directly to libpython: "
        f"{filename} has DT_NEEDED {', '.join(needed)}"
    )
    warning.module = module
    warning.filename = filename
    warning.needed = tuple(needed)
    return warning


def _check_extension(module: Any, filename: Any) -> None:
    try:
        filename = os.fsdecode(filename)
        needed = libpython_dependencies(filename)
    except Exception:
        # Not ELF, unreadable, or malformed: never let the checker itself
        # break an import. CPython's own loader reports real problems.
        return
    if needed:
        # Raised outside the try block so that warning filters set to "error"
        # (e.g. -Werror) propagate and abort the import before dlopen().
        # stacklevel=3 skips this function and the hook; the warnings
        # machinery then skips importlib's frames to reach the import site.
        warnings.warn(_make_warning(str(module), filename, needed), stacklevel=3)


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    if event == "import":
        # _imp.create_dynamic raises ("import", name, filename, None, None, None)
        # immediately before it dlopen()s an extension module. The importlib
        # event for every import passes filename=None and sys.path instead.
        if len(args) == 5 and args[1] is not None and args[2] is None:
            _check_extension(args[0], args[1])
    elif event == PROBE_EVENT and args and isinstance(args[0], list):
        args[0].append("python")


# How -W / PYTHONWARNINGS entries can spell the category.
_CATEGORY_NAMES = frozenset(
    {"libpython_linkcheck.LibpythonLinkWarning", "libpython_linkcheck._hook.LibpythonLinkWarning"}
)
_ACTIONS = ("default", "always", "all", "ignore", "module", "once", "error")


def _parse_warnoption(arg: str) -> tuple[str, str, str, int] | None:
    """Parse a -W option naming LibpythonLinkWarning like warnings._setoption does.

    Returns (action, message regex, module regex, lineno), or None if the
    option does not name this category or is invalid.
    """
    parts = [s.strip() for s in arg.split(":")]
    if len(parts) > 5:
        return None
    parts += [""] * (5 - len(parts))
    action, message, category, module, lineno = parts
    if category not in _CATEGORY_NAMES:
        return None
    if not action:
        action = "default"
    else:
        action = next((a for a in _ACTIONS if a.startswith(action)), "")
        if not action:
            return None
        if action == "all" and sys.version_info < (3, 14):
            action = "always"  # "all" was an alias before 3.14
    try:
        line = int(lineno) if lineno else 0
    except ValueError:
        return None
    if line < 0:
        return None
    return (
        action,
        re.escape(message) if message else "",
        re.escape(module) + r"\Z" if module else "",
        line,
    )


def _apply_dropped_warnoptions() -> None:
    """Apply -W / PYTHONWARNINGS entries for our category that CPython dropped.

    CPython resolves the categories named in warning options during startup,
    before ``site`` puts site-packages on sys.path. For a normally installed
    copy of this package that fails, and CPython prints "Invalid -W option
    ignored: invalid module name: 'libpython_linkcheck'" and drops the entry.
    Apply such entries now, in their original order. Entries that did take
    effect (e.g. the package was on PYTHONPATH) are left alone.
    """
    for arg in sys.warnoptions:
        parsed = _parse_warnoption(arg)
        if parsed is None:
            continue
        action, message, module, lineno = parsed
        item = (
            action,
            re.compile(message, re.I) if message else None,
            LibpythonLinkWarning,
            re.compile(module) if module else None,
            lineno,
        )
        if item not in warnings.filters:
            warnings.filterwarnings(action, message, LibpythonLinkWarning, module, lineno)


def _installed_hooks() -> list[str]:
    found: list[str] = []
    sys.audit(PROBE_EVENT, found)
    return found


def is_enabled() -> bool:
    """Return True if a libpython-linkcheck audit hook is active in this interpreter."""
    return bool(_installed_hooks())


def enable() -> bool:
    """Install the libpython-linkcheck audit hook in the current interpreter.

    Idempotent: if a hook is already active (installed by any earlier call,
    including one made through a different copy of this module), nothing is
    installed and False is returned. Returns True if this call installed it.

    When it installs the hook, it also applies any ``-W`` or ``PYTHONWARNINGS``
    entries naming ``libpython_linkcheck.LibpythonLinkWarning`` that CPython
    could not resolve at startup (see the README).

    Audit hooks cannot be removed, so the hook stays active for the lifetime
    of the interpreter. Raises RuntimeError if another audit hook prevented
    the installation.
    """
    with _enable_lock:
        if is_enabled():
            return False
        sys.addaudithook(_audit_hook)
        if not is_enabled():
            # sys.addaudithook() silently skips the hook if an existing hook
            # raised a RuntimeError subclass for the "sys.addaudithook" event.
            raise RuntimeError("another audit hook prevented libpython-linkcheck from installing")
        _apply_dropped_warnoptions()
        return True
