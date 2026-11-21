"""The audit hook that inspects extension modules before they are loaded."""

from __future__ import annotations

import contextlib
import os
import re
import sys
import threading
import warnings
from typing import Any

from . import _elf
from ._elf import libpython_dependencies

#: Audit event used to ask "is a libpython-linkcheck hook installed here?".
#: Every hook appends ``(kind, category)`` to the list passed as the event's
#: only argument: kind is "python" (this module's hook), "native" (the C hook
#: installed by enable()) or "embedded" (the runtime-wide C hook registered by
#: an embedding application with LibpythonLinkcheck_Install()). This lets
#: enable() detect any of them, and lets every hook in an interpreter share
#: one warning category, without relying on module globals.
PROBE_EVENT = "libpython_linkcheck.probe"

_enable_lock = threading.Lock()


def _probe() -> list[tuple[str, Any]]:
    found: list[Any] = []
    sys.audit(PROBE_EVENT, found)
    # 0.1.0a1 answered with a bare "python" string.
    return [e if isinstance(e, tuple) and len(e) == 2 else (str(e), None) for e in found]


def _adopted_category() -> type[RuntimeWarning] | None:
    for _, category in _probe():
        if isinstance(category, type) and issubclass(category, RuntimeWarning):
            return category
    return None


class _PyLibpythonLinkWarning(RuntimeWarning):
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
_PyLibpythonLinkWarning.__module__ = "libpython_linkcheck"
_PyLibpythonLinkWarning.__qualname__ = _PyLibpythonLinkWarning.__name__ = "LibpythonLinkWarning"

# One class per interpreter, shared by every hook: the C implementation keeps
# it in the interpreter's state dict; without it, adopt the class of a hook
# that is already installed (e.g. by an embedding application).
LibpythonLinkWarning: type[RuntimeWarning]
if _elf._native is not None:
    LibpythonLinkWarning = _elf._native.category()
else:
    LibpythonLinkWarning = _adopted_category() or _PyLibpythonLinkWarning


def _make_warning(module: str, filename: str, needed: list[str]) -> RuntimeWarning:
    warning: Any = LibpythonLinkWarning(
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
        args[0].append(("python", LibpythonLinkWarning))


# How -W / PYTHONWARNINGS entries can spell the category.
_CATEGORY_NAMES = frozenset(
    {"libpython_linkcheck.LibpythonLinkWarning", "libpython_linkcheck._hook.LibpythonLinkWarning"}
)
_ACTIONS = ("default", "always", "all", "ignore", "module", "once", "error")
#: Set on the (per-interpreter) category once the dropped options are applied.
_APPLIED_MARK = "_libpython_linkcheck_warnoptions_applied"

_Filter = tuple[str, Any, type, Any, int]


def _split_warnoption(arg: str) -> tuple[str, str, str, str, int] | None:
    """Split a -W option like warnings._setoption does, without resolving the category.

    Returns (action, message regex, category name, module regex, lineno), or
    None if the option is invalid.
    """
    parts = [s.strip() for s in arg.split(":")]
    if len(parts) > 5:
        return None
    parts += [""] * (5 - len(parts))
    action, message, category, module, lineno = parts
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
        category,
        re.escape(module) + r"\Z" if module else "",
        line,
    )


def _parse_warnoption(arg: str) -> tuple[str, str, str, int] | None:
    """Parse a -W option naming LibpythonLinkWarning.

    Returns (action, message regex, module regex, lineno), or None if the
    option does not name this category or is invalid.
    """
    split = _split_warnoption(arg)
    if split is None or split[2] not in _CATEGORY_NAMES:
        return None
    action, message, _, module, lineno = split
    return action, message, module, lineno


def _resolve_category(name: str) -> type | None:
    """The class a -W category names, without importing anything.

    CPython imported every module it could while processing the options at
    startup, so a category that resolved then is reachable through builtins
    or sys.modules now.
    """
    if not name:
        return Warning
    if name in _CATEGORY_NAMES:
        return LibpythonLinkWarning
    module_name, _, attr = name.rpartition(".")
    module = sys.modules.get(module_name) if module_name else sys.modules.get("builtins")
    category = getattr(module, attr, None)
    return category if isinstance(category, type) and issubclass(category, Warning) else None


def _option_filter(arg: str) -> tuple[bool, _Filter] | None:
    """(names our category?, the warnings.filters entry the option produces)."""
    split = _split_warnoption(arg)
    if split is None:
        return None
    action, message, category_name, module, lineno = split
    category = _resolve_category(category_name)
    if category is None:
        return None
    item = (
        action,
        re.compile(message, re.I) if message else None,
        category,
        re.compile(module) if module else None,
        lineno,
    )
    return category_name in _CATEGORY_NAMES, item


def _simulate(items: list[_Filter]) -> list[_Filter]:
    """The filter list that inserting *items* in order produces (front first).

    Like warnings.filterwarnings(): each item moves to the front, replacing an
    equal entry. CPython applies -W options this way, so the last one wins.
    """
    out: list[_Filter] = []
    for item in items:
        if item in out:
            out.remove(item)
        out.insert(0, item)
    return out


def _find(filters: list[Any], block: list[_Filter]) -> int:
    n = len(block)
    return next((i for i in range(len(filters) - n + 1) if filters[i : i + n] == block), -1)


def _apply_dropped_warnoptions() -> None:
    """Apply -W / PYTHONWARNINGS entries for our category that CPython dropped.

    CPython resolves the categories named in warning options during startup,
    before ``site`` puts site-packages on sys.path. For a normally installed
    copy of this package that fails, and CPython prints "Invalid -W option
    ignored: invalid module name: 'libpython_linkcheck'" and drops the entry.

    Apply such entries now, with the precedence they would have had: CPython
    inserts the options at the front of warnings.filters in order, so each
    one overrides the options before it. The startup options are located in
    warnings.filters and replaced by the full set, so a recovered entry sits
    behind later options and ahead of earlier ones. Filters the program added
    since startup stay in front. If the startup options cannot be located
    (there were none besides ours, or the program reset or edited the
    filters), the recovered entries are appended, behind every existing
    filter; CPython's default filters never match a RuntimeWarning, so this
    still applies them unless the program has its own policy.

    Runs once per interpreter. Entries that took effect at startup (the
    package was importable before site, e.g. on PYTHONPATH) are left alone.
    """
    if getattr(LibpythonLinkWarning, _APPLIED_MARK, False):
        return
    entries = [e for e in map(_option_filter, sys.warnoptions) if e is not None]
    ours = [item for is_ours, item in entries if is_ours]
    if ours:
        desired = _simulate([item for _, item in entries])
        startup = _simulate([item for is_ours, item in entries if not is_ours])
        lock = getattr(warnings, "_lock", None)  # 3.14+
        with lock if lock is not None else contextlib.nullcontext():
            get_filters = getattr(warnings, "_get_filters", None)
            filters = get_filters() if get_filters is not None else warnings.filters
            if _find(filters, desired) >= 0:
                pass  # already in effect
            elif startup and (pos := _find(filters, startup)) >= 0:
                filters[pos : pos + len(startup)] = desired
            else:
                filters.extend(item for item in _simulate(ours) if item not in filters)
            mutated = getattr(warnings, "_filters_mutated_lock_held", None)
            if mutated is None:
                mutated = warnings._filters_mutated  # type: ignore[attr-defined]
            mutated()
    setattr(LibpythonLinkWarning, _APPLIED_MARK, True)


def _installed_hooks() -> list[str]:
    """Kinds of the libpython-linkcheck hooks active in this interpreter."""
    return [kind for kind, _ in _probe()]


def is_enabled() -> bool:
    """Return True if a libpython-linkcheck audit hook is active in this interpreter."""
    return bool(_installed_hooks())


def enable() -> bool:
    """Install the libpython-linkcheck audit hook in the current interpreter.

    Idempotent: if a hook is already active (installed by any earlier call,
    including one made through a different copy of this module, or by an
    embedding application with ``LibpythonLinkcheck_Install()``), nothing is
    installed and False is returned. Returns True if this call installed it.

    The first call in an interpreter also applies any ``-W`` or
    ``PYTHONWARNINGS`` entries naming
    ``libpython_linkcheck.LibpythonLinkWarning`` that CPython could not
    resolve at startup, with the precedence their position gives them (see
    the README).

    Audit hooks cannot be removed, so the hook stays active for the lifetime
    of the interpreter. Raises RuntimeError if another audit hook prevented
    the installation.
    """
    with _enable_lock:
        installed = False
        if not is_enabled():
            native = _elf._native
            sys.addaudithook(_audit_hook if native is None else native.audit_hook)
            if not is_enabled():
                # sys.addaudithook() silently skips the hook if an existing hook
                # raised a RuntimeError subclass for the "sys.addaudithook" event.
                raise RuntimeError(
                    "another audit hook prevented libpython-linkcheck from installing"
                )
            installed = True
        _apply_dropped_warnoptions()
        return installed
