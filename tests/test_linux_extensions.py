"""End-to-end tests with real compiled extension modules (Linux only).

Fixtures (see extbuild.py) are compiled for the running interpreter:
``linked_ext`` links the versioned libpython, ``abi3_linked_ext`` links the
Stable ABI ``libpython3.so``, and ``unlinked_ext`` is the unlinked control.
Their ELF constructors log to a file, so the tests can tell whether the
dynamic loader ever mapped them.
"""

from __future__ import annotations

import shutil
import sysconfig

import pytest
from extbuild import IS_LINUX, Exts, readelf_needed
from pyrun import run_python

from libpython_linkcheck._elf import is_libpython, read_needed

pytestmark = pytest.mark.skipif(not IS_LINUX, reason="ELF extension loading is Linux-only")

ENABLE = "import libpython_linkcheck\nlibpython_linkcheck.enable()\n"
CATEGORY = "libpython_linkcheck.LibpythonLinkWarning"


@pytest.fixture
def py(exts: Exts, tmp_path):
    def run(code, *flags, path=()):
        return run_python(code, *flags, path=[*path, exts.dir], workdir=tmp_path)

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
