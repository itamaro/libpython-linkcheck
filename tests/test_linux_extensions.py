"""End-to-end tests with real compiled extension modules (Linux only).

Fixtures (see extbuild.py) are compiled for the running interpreter:
``linked_ext`` links the versioned libpython, ``abi3_linked_ext`` links the
Stable ABI ``libpython3.so``, and ``unlinked_ext`` is the unlinked control.
Their ELF constructors log to a file, so the tests can tell whether the
dynamic loader ever mapped them.
"""

from __future__ import annotations

import shutil
import sys
import sysconfig

import pytest
from extbuild import IS_LINUX, Exts, readelf_needed
from pyrun import STARTUP_NOTICE, SUBINTERPRETER_HELPER, impl_env, package_parent, run_python

from libpython_linkcheck._elf import is_libpython, read_needed

pytestmark = pytest.mark.skipif(not IS_LINUX, reason="ELF extension loading is Linux-only")

ENABLE = "import libpython_linkcheck\nlibpython_linkcheck.enable()\n"
CATEGORY = "libpython_linkcheck.LibpythonLinkWarning"


@pytest.fixture
def py(exts: Exts, tmp_path, hook_impl):
    def run(code, *flags, path=()):
        return run_python(
            code, *flags, path=[*path, exts.dir], workdir=tmp_path, env=impl_env(hook_impl)
        )

    return run


def message(ext) -> str:
    return (
        f"extension module {ext.name!r} links directly to libpython: "
        f"{ext.path} has DT_NEEDED {', '.join(ext.expected_libpython)}"
    )


def test_fixture_dt_needed_entries(exts: Exts):
    """The fixtures really have (or lack) libpython in their own DT_NEEDED."""
    assert shutil.which("readelf"), "readelf (binutils) is required for the Linux suite"
    for ext in exts:
        needed = readelf_needed(str(ext.path))
        assert read_needed(ext.path) == needed
        assert tuple(n for n in needed if is_libpython(n)) == ext.expected_libpython
    assert sysconfig.get_config_var("INSTSONAME") in readelf_needed(str(exts.linked.path))
    assert "libpython3.so" in readelf_needed(str(exts.abi3.path))
    assert not [n for n in readelf_needed(str(exts.unlinked.path)) if "python" in n]


def test_linked_extension_loads_without_the_hook(py, exts):
    """Baseline: the linked fixture is loadable, so any block is the hook's doing."""
    r = py("import linked_ext\nprint(linked_ext.hello())", "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (0, "linked_ext\n", "")
    assert r.ctor == ["linked_ext"]


@pytest.mark.parametrize("which", ["linked", "abi3"])
def test_linked_extension_warns_and_loads(py, exts, which):
    ext = getattr(exts, which)
    r = py(ENABLE + f"import {ext.name}\nprint({ext.name}.hello())\n")
    assert r.returncode == 0, r.stderr
    assert r.stdout == f"{ext.name}\n"
    assert r.ctor == [ext.name]
    # Attributed to the user's import statement (line 3), not to importlib.
    assert r.link_warnings == [f"<string>:3: LibpythonLinkWarning: {message(ext)}"]


@pytest.mark.parametrize(
    "flags", [("-Werror",), ("-W", f"error::{CATEGORY}")], ids=["Werror", "W-category"]
)
def test_error_filter_stops_load_before_elf_constructor(py, exts, flags):
    r = py(ENABLE + "import linked_ext\n", *flags)
    assert r.returncode == 1
    assert r.ctor == [], "the ELF constructor ran: dlopen() was not prevented"
    assert r.stderr.splitlines()[-1] == f"{CATEGORY}: {message(exts.linked)}"


def test_error_filter_failure_is_catchable_and_not_cached(py, exts):
    code = (
        ENABLE
        + """
import sys, warnings
try:
    import linked_ext
except libpython_linkcheck.LibpythonLinkWarning as w:
    print(w.module, w.filename, ",".join(w.needed), sep="|")
assert "linked_ext" not in sys.modules
warnings.simplefilter("ignore")
import linked_ext
print(linked_ext.hello())
"""
    )
    r = py(code, "-Werror")
    assert r.returncode == 0, r.stderr
    ext = exts.linked
    assert r.stdout == f"linked_ext|{ext.path}|{ext.expected_libpython[0]}\nlinked_ext\n"
    assert r.ctor == ["linked_ext"]


def test_enable_twice_warns_once_with_always_filter(py):
    code = """
import libpython_linkcheck
assert libpython_linkcheck.enable() is True
assert libpython_linkcheck.enable() is False
import linked_ext
"""
    r = py(code, "-W", "always")
    assert r.returncode == 0, r.stderr
    assert len(r.link_warnings) == 1, r.stderr
    assert r.ctor == ["linked_ext"]


def test_enable_from_a_second_module_copy_warns_once(py):
    """Idempotency does not depend on module globals."""
    code = """
import sys
import libpython_linkcheck as first
assert first.enable() is True
for name in [m for m in sys.modules if m.split(".")[0] == "libpython_linkcheck"]:
    del sys.modules[name]
import libpython_linkcheck as second
assert second is not first
assert second.is_enabled()
assert second.enable() is False
import linked_ext
"""
    r = py(code, "-W", "always")
    assert r.returncode == 0, r.stderr
    assert len(r.link_warnings) == 1, r.stderr


def test_unlinked_control_imports_cleanly_under_werror(py):
    r = py(ENABLE + "import unlinked_ext\nprint(unlinked_ext.hello())\n", "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (0, "unlinked_ext\n", "")
    assert r.ctor == ["unlinked_ext"]


def test_ignore_filter(py):
    r = py(ENABLE + "import linked_ext\n", "-W", f"ignore::{CATEGORY}")
    assert (r.returncode, r.stderr_lines) == (0, [])
    assert r.ctor == ["linked_ext"]


def test_message_filter_targets_one_extension(py, exts):
    code = (
        ENABLE
        + """
import warnings
warnings.filterwarnings("error", message="extension module 'abi3_linked_ext'")
import linked_ext
try:
    import abi3_linked_ext
except libpython_linkcheck.LibpythonLinkWarning:
    print("blocked")
"""
    )
    r = py(code)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "blocked\n"
    assert r.link_warnings == [f"<string>:6: LibpythonLinkWarning: {message(exts.linked)}"]
    assert r.ctor == ["linked_ext"]


def test_module_filter_matches_the_importing_module(py):
    r = py(ENABLE + "import linked_ext\n", "-W", f"error::{CATEGORY}:__main__")
    assert r.returncode == 1
    assert r.ctor == []


def test_catch_warnings_record(py, exts):
    code = (
        ENABLE
        + """
import warnings
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    import linked_ext
(w,) = caught
assert w.category is libpython_linkcheck.LibpythonLinkWarning
m = w.message
print(m.module, m.filename, m.needed, w.filename, w.lineno, sep="|")
"""
    )
    r = py(code)
    assert r.returncode == 0, r.stderr
    ext = exts.linked
    assert r.stdout == f"linked_ext|{ext.path}|{ext.expected_libpython!r}|<string>|7\n"


def test_extension_in_a_package_reports_qualified_name(py, exts, tmp_path):
    pkg = tmp_path / "pkgroot" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    dest = pkg / exts.linked.path.name
    shutil.copy2(exts.linked.path, dest)
    r = py(ENABLE + "import pkg.linked_ext\n", path=[pkg.parent])
    assert r.returncode == 0, r.stderr
    (line,) = r.link_warnings
    assert f"extension module 'pkg.linked_ext' links directly to libpython: {dest} " in line


def test_spec_from_file_location(py, exts):
    code = (
        ENABLE
        + f"""
import importlib.util
spec = importlib.util.spec_from_file_location("renamed.linked_ext", {str(exts.linked.path)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(module.hello())
"""
    )
    r = py(code, "-W", "error::RuntimeWarning")
    assert r.returncode == 1
    assert r.ctor == []
    assert "LibpythonLinkWarning: extension module 'renamed.linked_ext'" in r.stderr


def test_enable_is_per_interpreter(py, exts, hook_impl):
    """A hook from enable() covers only its own interpreter, in either direction."""
    path = str(exts.dir)
    not_enabled = f"""
import sys
sys.path.insert(0, {path!r})
import libpython_linkcheck
print("sub before enable:", libpython_linkcheck.is_enabled(), flush=True)
import linked_ext
"""
    enabled = f"""
import sys
sys.path.insert(0, {path!r})
import libpython_linkcheck
from libpython_linkcheck import _elf
print("sub enable:", libpython_linkcheck.enable(), _elf.IMPLEMENTATION, flush=True)
import abi3_linked_ext
"""
    code = (
        SUBINTERPRETER_HELPER
        + ENABLE
        + f"run_in_subinterpreter({not_enabled!r})\n"
        + f"run_in_subinterpreter({enabled!r})\n"
        + "print('main still enabled:', libpython_linkcheck.is_enabled())\n"
    )
    r = py(code, "-W", "always")
    assert r.returncode == 0, r.stderr
    assert r.stdout == (
        f"sub before enable: False\nsub enable: True {hook_impl}\nmain still enabled: True\n"
    )
    (line,) = r.link_warnings
    assert "extension module 'abi3_linked_ext'" in line
    assert r.ctor == ["linked_ext", "abi3_linked_ext"]


# --- -W options for our category ----------------------------------------------------
#
# CPython applies -W / PYTHONWARNINGS entries in order, each in front of the
# previous ones, so the last one wins. An entry naming our category resolves
# at startup only if the package is importable then (here: on PYTHONPATH);
# otherwise CPython drops it and enable() recovers it. Each case runs both
# ways ("startup" fixture). Resolved, enable() must leave the policy CPython
# and the program established alone; dropped, it must not override filters
# the program may have installed.

IMPORT_LINKED = ENABLE + "import linked_ext\n"


@pytest.fixture(params=["resolved", "dropped"])
def startup(request, py):
    """Run with the category resolved by CPython at startup, or dropped."""
    resolved = request.param == "resolved"

    def run(code, *flags):
        r = py(code, *flags, path=[package_parent()] if resolved else [])
        assert (STARTUP_NOTICE in r.stderr.splitlines()) is not resolved, r.stderr
        return r

    run.resolved = resolved
    return run


def assert_loaded_silently(r):
    assert r.returncode == 0, r.stderr
    assert r.ctor == ["linked_ext"]
    assert r.link_warnings == []
    assert r.stderr_lines == []


def assert_blocked(r):
    assert r.returncode == 1, r.stderr
    assert r.ctor == []  # stopped before the ELF constructor ran
    assert r.stderr.splitlines()[-1].startswith(f"{CATEGORY}: extension module 'linked_ext' ")


def test_later_option_overrides_category_option(startup):
    assert_loaded_silently(startup(IMPORT_LINKED, "-W", f"error::{CATEGORY}", "-W", "ignore"))


def test_category_option_overrides_earlier_unrelated_option(startup):
    r = startup(IMPORT_LINKED, "-W", "ignore::UserWarning", "-W", f"error::{CATEGORY}")
    assert_blocked(r)


@pytest.mark.parametrize("earlier", ["ignore", "ignore:::__main__"])
def test_earlier_overlapping_option_keeps_precedence_over_recovery(startup, earlier):
    """Documented limit: after startup, a dropped entry cannot override an
    earlier option that also matches the warning, because the program could
    have installed the same filter itself (see the next test). Resolved, the
    later option wins. (From site it does too: see test_activation.py.)"""
    r = startup(IMPORT_LINKED, "-W", earlier, "-W", f"error::{CATEGORY}")
    if startup.resolved:
        assert_blocked(r)
    else:
        assert_loaded_silently(r)


def test_program_filter_keeps_precedence(startup):
    """The program's simplefilter("ignore") wins, whether or not the category
    resolved at startup, even though it equals the earlier -W ignore."""
    code = "import warnings\nwarnings.simplefilter('ignore')\n" + IMPORT_LINKED
    assert_loaded_silently(startup(code, "-W", "ignore", "-W", f"error::{CATEGORY}"))


def test_recovery_survives_catch_warnings(startup):
    """enable() inside catch_warnings() changes only that temporary filter list."""
    code = """
import warnings
import libpython_linkcheck
with warnings.catch_warnings():
    libpython_linkcheck.enable()
libpython_linkcheck.enable()
import linked_ext
"""
    assert_blocked(startup(code, "-W", f"error::{CATEGORY}"))


def test_message_regex_option(startup):
    """3.15 reads a message field enclosed in slashes as a regular expression;
    older versions match it literally, so it never matches this warning."""
    r = startup(IMPORT_LINKED, "-W", f"error:/^extension module /:{CATEGORY}")
    if sys.version_info >= (3, 15):
        assert_blocked(r)
    else:
        assert (r.returncode, r.ctor, len(r.link_warnings)) == (0, ["linked_ext"], 1), r.stderr


@pytest.mark.parametrize(
    ("pythonwarnings", "blocked"),
    [(f"error::{CATEGORY},ignore", False), (f"ignore::UserWarning,error::{CATEGORY}", True)],
)
def test_pythonwarnings_order_is_preserved(exts, tmp_path, hook_impl, pythonwarnings, blocked):
    r = run_python(
        IMPORT_LINKED,
        path=[exts.dir],
        workdir=tmp_path,
        env={**impl_env(hook_impl), "PYTHONWARNINGS": pythonwarnings},
    )
    if blocked:
        assert_blocked(r)
    else:
        assert_loaded_silently(r)


def test_command_line_overrides_recovered_pythonwarnings_entry(exts, tmp_path, hook_impl):
    """PYTHONWARNINGS entries come before -W options, so -W wins."""
    r = run_python(
        IMPORT_LINKED,
        "-W",
        "ignore",
        path=[exts.dir],
        workdir=tmp_path,
        env={**impl_env(hook_impl), "PYTHONWARNINGS": f"error::{CATEGORY}"},
    )
    assert_loaded_silently(r)


def test_filter_installed_before_enable_overrides_recovered_option(py):
    code = "import warnings\nwarnings.simplefilter('ignore')\n" + IMPORT_LINKED
    assert_loaded_silently(py(code, "-W", f"error::{CATEGORY}"))


def test_recovery_keeps_other_filters_and_is_applied_once(py, hook_impl):
    code = """
import sys, warnings
before = list(warnings.filters)
import libpython_linkcheck as m
assert m.enable() is True
after = list(warnings.filters)
assert m.enable() is False
# A fresh copy of the module finds the hook and must not apply anything again.
for name in [n for n in sys.modules if n.split(".")[0] == "libpython_linkcheck"]:
    del sys.modules[name]
import libpython_linkcheck as copy
assert copy.enable() is False
cat = m.LibpythonLinkWarning
ours = [f for f in after if f[2] is cat]
print(len(ours), ours[0][0], after.index(ours[0]))
print([f for f in after if f[2] is not cat] == before, list(warnings.filters) == after)
"""
    r = py(
        code,
        "-W",
        f"error::{CATEGORY}",
        "-W",
        "ignore::DeprecationWarning",
        "-W",
        "error::UserWarning",
    )
    assert r.returncode == 0, r.stderr
    # Behind the two later options, ahead of everything else; nothing else moved.
    assert r.stdout == "1 error 2\nTrue True\n"
