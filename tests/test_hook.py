"""Hook behavior that does not need a loadable extension (runs on every platform).

A synthetic ELF object that names libpython is placed where CPython will try
to load it as an extension module. The hook inspects it before dlopen();
dlopen() itself then fails (it is not a loadable object for this machine),
which CPython reports as an ImportError.
"""

from __future__ import annotations

import importlib.machinery
import re
from pathlib import Path

import pytest
from elfbuild import ElfSpec, build_elf
from pyrun import STARTUP_NOTICE, impl_env, run_python

import libpython_linkcheck
from libpython_linkcheck._hook import _parse_warnoption

SUFFIX = importlib.machinery.EXTENSION_SUFFIXES[0]
CATEGORY = "libpython_linkcheck.LibpythonLinkWarning"
ENABLE = "import libpython_linkcheck\nlibpython_linkcheck.enable()\n"


@pytest.fixture
def ext_dir(tmp_path):
    d = tmp_path / "exts"
    d.mkdir()
    (d / f"fake_linked{SUFFIX}").write_bytes(
        build_elf(ElfSpec(needed=[b"libpython3.14t.so.1.0", b"libc.so.6"]))
    )
    (d / f"fake_unlinked{SUFFIX}").write_bytes(build_elf(ElfSpec(needed=[b"libc.so.6"])))
    (d / f"not_elf{SUFFIX}").write_bytes(b"this is not an object file\n")
    corrupt = bytearray(build_elf(ElfSpec(needed=[b"libpython3.so"])))
    (d / f"corrupt_elf{SUFFIX}").write_bytes(bytes(corrupt[:70]))
    return d


@pytest.fixture
def py(ext_dir, tmp_path, hook_impl):
    def run(code, *flags, path=(), env=None):
        env = {**impl_env(hook_impl), **(env or {})}
        return run_python(code, *flags, path=[ext_dir, *path], workdir=tmp_path, env=env)

    return run


def test_public_api():
    assert set(libpython_linkcheck.__all__) == {
        "ELFError",
        "LibpythonLinkWarning",
        "__version__",
        "enable",
        "is_enabled",
        "libpython_dependencies",
    }
    w = libpython_linkcheck.LibpythonLinkWarning
    assert issubclass(w, RuntimeWarning)
    assert w.__module__ == "libpython_linkcheck"
    assert (w.module, w.filename, w.needed) == (None, None, ())


def test_enable_is_idempotent_and_reported(py, hook_impl):
    code = """
import sys
import libpython_linkcheck as m
from libpython_linkcheck import _elf
assert not m.is_enabled()
assert m.enable() is True
assert m.is_enabled()
assert m.enable() is False
found = []
sys.audit("libpython_linkcheck.probe", found)
((kind, category),) = found
assert category is m.LibpythonLinkWarning
print(_elf.IMPLEMENTATION, kind)
"""
    r = py(code, "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (0, f"{hook_impl} {hook_impl}\n", "")


def test_category_is_shared_by_module_copies(py):
    code = """
import sys
import libpython_linkcheck as first
first.enable()
for name in [m for m in sys.modules if m.split(".")[0] == "libpython_linkcheck"]:
    del sys.modules[name]
import libpython_linkcheck as second
assert second is not first
assert second.LibpythonLinkWarning is first.LibpythonLinkWarning
w = second.LibpythonLinkWarning
print(w.__module__, w.__qualname__, issubclass(w, RuntimeWarning))
"""
    r = py(code, "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (
        0,
        "libpython_linkcheck LibpythonLinkWarning True\n",
        "",
    )


def test_warns_before_loading(py, ext_dir):
    code = (
        ENABLE
        + """
try:
    import fake_linked
except ImportError:
    print("dlopen failed")
"""
    )
    r = py(code)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "dlopen failed\n"
    assert r.link_warnings == [
        "<string>:5: LibpythonLinkWarning: extension module 'fake_linked' links directly to "
        f"libpython: {ext_dir / f'fake_linked{SUFFIX}'} has DT_NEEDED libpython3.14t.so.1.0"
    ]


RAISE_OR_LOAD = (
    ENABLE
    + """
try:
    import fake_linked
except libpython_linkcheck.LibpythonLinkWarning as w:
    print("raised", w.module, w.needed)
except ImportError:
    print("dlopen failed")
"""
)
RAISED = "raised fake_linked ('libpython3.14t.so.1.0',)\n"


def test_error_filter_raises_instead_of_loading(py):
    r = py(RAISE_OR_LOAD, "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (0, RAISED, "")


def test_category_option_dropped_at_startup_is_applied_by_enable(py):
    r = py(RAISE_OR_LOAD, "-W", f"error::{CATEGORY}")
    assert r.returncode == 0, r.stderr
    assert r.stdout == RAISED
    # CPython itself reports the option as ignored at startup; enable() applies it.
    assert r.stderr.splitlines() == [STARTUP_NOTICE]


def test_pythonwarnings_category_is_applied_by_enable(py):
    r = py(RAISE_OR_LOAD, env={"PYTHONWARNINGS": f"error::{CATEGORY}"})
    assert (r.returncode, r.stdout, r.stderr_lines) == (0, RAISED, [])


def test_dropped_options_keep_their_order(py):
    r = py(RAISE_OR_LOAD, "-W", f"ignore::{CATEGORY}", "-W", f"error::{CATEGORY}")
    assert (r.returncode, r.stdout, r.stderr_lines) == (0, RAISED, [])
    r = py(RAISE_OR_LOAD, "-W", f"error::{CATEGORY}", "-W", f"ignore::{CATEGORY}")
    assert (r.returncode, r.stdout, r.stderr_lines) == (0, "dlopen failed\n", [])


def test_options_resolved_at_startup_are_not_duplicated(py):
    """With the package importable before site (PYTHONPATH), CPython applies the option."""
    package_parent = Path(libpython_linkcheck.__file__).parent.parent
    code = (
        "import warnings\n"
        + ENABLE
        + "print(sum(f[2] is libpython_linkcheck.LibpythonLinkWarning for f in warnings.filters))"
    )
    r = py(code, "-W", f"error::{CATEGORY}", path=[package_parent])
    assert (r.returncode, r.stdout, r.stderr) == (0, "1\n", "")


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        (f"error::{CATEGORY}", ("error", "", "", 0)),
        (f"e::{CATEGORY}", ("error", "", "", 0)),
        (f"::{CATEGORY}", ("default", "", "", 0)),
        (f" ignore : x.y : {CATEGORY} : a.b : 7 ", ("ignore", re.escape("x.y"), r"a\.b\Z", 7)),
        ("error::libpython_linkcheck._hook.LibpythonLinkWarning", ("error", "", "", 0)),
        (f"bogus::{CATEGORY}", None),
        (f"error::{CATEGORY}:m:-1", None),
        (f"error::{CATEGORY}:m:x", None),
        (f"error::{CATEGORY}:m:1:extra", None),
        ("error::RuntimeWarning", None),
        ("error", None),
    ],
)
def test_parse_warnoption(arg, expected):
    assert _parse_warnoption(arg) == expected


@pytest.mark.parametrize("name", ["fake_unlinked", "not_elf", "corrupt_elf"])
def test_uninspectable_or_clean_objects_only_fail_in_the_loader(py, name):
    code = (
        ENABLE
        + f"""
try:
    import {name}
except ImportError as e:
    assert not isinstance(e, Warning)
    print("ImportError")
"""
    )
    r = py(code, "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (0, "ImportError\n", "")


def test_without_enable_nothing_is_inspected(py):
    r = py("try:\n    import fake_linked\nexcept ImportError:\n    print('ok')\n", "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (0, "ok\n", "")


def test_pure_python_and_builtin_imports_unaffected(py):
    r = py(ENABLE + "import json, decimal, sqlite3, ctypes\nprint('ok')\n", "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (0, "ok\n", "")


def test_blocked_installation_raises(py):
    code = """
import sys
def deny(event, args):
    if event == "sys.addaudithook":
        raise RuntimeError("denied")
sys.addaudithook(deny)
import libpython_linkcheck
try:
    libpython_linkcheck.enable()
except RuntimeError as e:
    print("RuntimeError:", e)
print(libpython_linkcheck.is_enabled())
"""
    r = py(code)
    assert r.returncode == 0, r.stderr
    assert r.stdout == (
        "RuntimeError: another audit hook prevented libpython-linkcheck from installing\nFalse\n"
    )
