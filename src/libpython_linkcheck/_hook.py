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
#: Set on the (per-interpreter) category class, which every copy of this
#: module shares, once nothing is left to recover: CPython resolved the -W
#: entries naming it at startup, or enable() applied the dropped ones.
_DONE_MARK = "_libpython_linkcheck_warnoptions_done"
#: Modules holding CPython's warnings implementation (3.14+: _py_warnings).
_WARNINGS_MODULES = frozenset({"warnings", "_py_warnings"})
# How CPython's warnings._setoption() turns the message and module fields
# into regular expressions: 3.14 anchors a module with \z instead of \Z, and
# 3.15 takes a field enclosed in slashes as a regular expression.
_MODULE_END = r"\z" if sys.version_info >= (3, 14) else r"\Z"
_SLASH_REGEX_FIELDS = sys.version_info >= (3, 15)

_Filter = tuple[str, Any, type, Any, int]


def _imported_by_warning_options() -> bool:
    """True if CPython is importing this module to resolve a -W category.

    That happens at startup only when the package is importable before
    ``site`` runs (e.g. on PYTHONPATH); every option naming the category then
    took effect, and there is nothing to recover.
    """
    frame = sys._getframe(1)
    while frame is not None:
        if (
            frame.f_code.co_name == "_getcategory"
            and frame.f_globals.get("__name__") in _WARNINGS_MODULES
        ):
            return True
        frame = frame.f_back
    return False


def _called_from_site() -> bool:
    """True while ``site`` runs startup code (.pth / .start files, sitecustomize)."""
    site = sys.modules.get("site")
    if site is None:
        return False
    site_globals = vars(site)  # site is frozen, so compare globals, not file names
    frame = sys._getframe(1)
    while frame is not None:
        if frame.f_globals is site_globals:
            return True
        frame = frame.f_back
    return False


def _field_regex(text: str, *, module: bool) -> str:
    if _SLASH_REGEX_FIELDS and len(text) >= 2 and text[0] == text[-1] == "/":
        return text[1:-1]
    return re.escape(text) + (_MODULE_END if module else "")


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
    message = _field_regex(message, module=False) if message else ""
    module = _field_regex(module, module=True) if module else ""
    try:
        re.compile(message)
        re.compile(module)
    except re.error:
        return None  # CPython 3.15 reports an invalid regular expression
    return action, message, category, module, line


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


def _place_recovered(
    filters: list[Any], entries: list[tuple[bool, _Filter]], *, by_position: bool
) -> bool:
    """Insert the dropped entries for our category into *filters*; True if changed."""
    others = _simulate([item for is_ours, item in entries if not is_ours])
    missing = [
        item
        for item in _simulate([item for is_ours, item in entries if is_ours])
        if item not in filters  # an equal filter is already in effect
    ]
    if not missing:
        return False
    if by_position and others and (pos := _find(filters, others)) >= 0:
        # The filters are still the startup ones: give every option the
        # precedence of its position, as if CPython had resolved them all.
        everything = _simulate([item for _, item in entries])
        desired = [item for item in everything if item in others or item in missing]
        filters[pos : pos + len(others)] = desired
    else:
        # The program may have installed any of these filters itself, which
        # the list cannot tell from the startup ones: they all keep
        # precedence over the recovered entries, which go right behind the
        # last of them (or at the end).
        last = max((i for i, f in enumerate(filters) if f in others), default=len(filters) - 1)
        filters[last + 1 : last + 1] = missing
    return True


def _original_filters() -> list[Any] | None:
    """The interpreter's startup filter list, which catch_warnings() restores."""
    try:
        import _warnings  # noqa: PLC0415
    except ImportError:
        return None
    filters = getattr(_warnings, "filters", None)
    return filters if isinstance(filters, list) else None


def _apply_dropped_warnoptions(*, at_startup: bool = False) -> None:
    """Apply -W / PYTHONWARNINGS entries for our category that CPython dropped.

    CPython resolves the categories named in warning options during startup,
    before ``site`` puts site-packages on sys.path. For a normally installed
    copy of this package that fails, and CPython prints "Invalid -W option
    ignored: invalid module name: 'libpython_linkcheck'" and drops the entry.

    If the options resolved at startup (the package was importable then),
    nothing changes: they are in effect, in the order the program left them.

    Otherwise the first call in the interpreter adds each dropped entry,
    unless an equal filter is already there, to the filter list in effect
    and to the interpreter's original list if that is a different one (the
    call is inside ``catch_warnings()``, which restores the original on
    exit). That is where CPython would have put them; later lists are copies
    the program made, or its own, and are left alone, as is any filter the
    program removes later (``resetwarnings()``).

    *at_startup* (the autoenable entry point, from ``site``, before
    ``sitecustomize``) gives the entries the precedence of their position
    among the options. Otherwise the program may have installed filters
    equal to startup ones, which the list cannot tell apart: every filter
    equal to another startup option, and every filter in front of them,
    keeps precedence, and the entries go right behind them. CPython's
    default filters never match a RuntimeWarning.
    """
    category: Any = LibpythonLinkWarning
    if getattr(category, _DONE_MARK, False):
        return
    entries = [e for e in map(_option_filter, sys.warnoptions) if e is not None]
    if any(is_ours for is_ours, _ in entries):
        lock = getattr(warnings, "_lock", None)  # 3.14+
        with lock if lock is not None else contextlib.nullcontext():
            get_filters = getattr(warnings, "_get_filters", None)  # 3.14+: per-context lists
            current = get_filters() if get_filters is not None else warnings.filters
            targets = [current]
            original = _original_filters()
            if original is not None and original is not current:
                targets.append(original)
            changed = False
            for filters in targets:
                changed |= _place_recovered(filters, entries, by_position=at_startup)
            if changed:
                mutated = getattr(warnings, "_filters_mutated_lock_held", None)
                if mutated is None:
                    mutated = warnings._filters_mutated  # type: ignore[attr-defined]
                mutated()
    setattr(category, _DONE_MARK, True)


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
    resolve at startup, without overriding filters the program may have
    installed (see the README). Entries CPython did resolve are left as the
    program arranged them.

    Audit hooks cannot be removed, so the hook stays active for the lifetime
    of the interpreter. Raises RuntimeError if another audit hook prevented
    the installation.
    """
    return _enable(at_startup=False)


def _autoenable() -> bool:
    """enable() for the libpython-linkcheck-autoenable .pth / .start files.

    They run from ``site`` before ``sitecustomize`` and any program code, so
    dropped -W entries get the precedence of their position (see
    _apply_dropped_warnoptions). Called from anywhere else, this is enable().
    """
    return _enable(at_startup=_called_from_site())


def _enable(*, at_startup: bool) -> bool:
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
        _apply_dropped_warnoptions(at_startup=at_startup)
        return installed


# CPython imports this module during startup only to resolve a -W category.
# Record that on the interpreter's category, which every copy of the module
# shares, so enable() leaves the filters alone.
if _imported_by_warning_options():
    setattr(LibpythonLinkWarning, _DONE_MARK, True)
