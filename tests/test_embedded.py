"""The embedder entry point: LibpythonLinkcheck_Install() before Py_BytesMain().

tests/fixtures/launcher.c is built into a `python` executable the way an
embedding application or a CPython distribution (e.g. python-build-standalone)
would integrate src/csrc. Its hook is runtime-wide, needs no Python package,
and must work under -I -S.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from extbuild import IS_LINUX, build_launcher
from pyrun import STARTUP_NOTICE, SUBINTERPRETER_HELPER, impl_env, make_venv, run_python

pytestmark = pytest.mark.skipif(not IS_LINUX, reason="the embedded hook is tested on Linux")

PROBE = "libpython_linkcheck.probe"
CATEGORY = "libpython_linkcheck.LibpythonLinkWarning"


@pytest.fixture(scope="session")
def launcher(tmp_path_factory) -> Path:
    return build_launcher(tmp_path_factory.mktemp("launcher"))


@pytest.fixture
def isolated(launcher, exts, tmp_path):
    """Run code in the launcher under -I -S, with the fixtures on sys.path."""

    def run(code, *flags, env=None):
        prelude = f"import sys\nsys.path.insert(0, {str(exts.dir)!r})\n"
        return run_python(
            prelude + code, "-I", "-S", *flags, workdir=tmp_path, env=env, executable=launcher
        )

    return run


@pytest.fixture
def venv_launcher(launcher, tmp_path) -> Path:
    """The launcher placed in a fresh venv that can import this package."""
    venv = make_venv(tmp_path / "venv")
    exe = venv.python.with_name("python-linkcheck")
    shutil.copy2(launcher, exe)
    return exe


def test_isolated_warns_without_importing_any_package(isolated, exts):
    code = """
import linked_ext
print(sorted(m for m in ("site", "libpython_linkcheck") if m in sys.modules))
"""
    r = isolated(code)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "[]\n"
    assert r.ctor == ["linked_ext"]
    ext = exts.linked
    assert r.link_warnings == [
        f"<string>:4: LibpythonLinkWarning: extension module 'linked_ext' links directly to "
        f"libpython: {ext.path} has DT_NEEDED {ext.expected_libpython[0]}"
    ]


def test_isolated_werror_stops_load_before_elf_constructor(isolated, exts):
    r = isolated("import linked_ext\n", "-Werror")
    assert r.returncode == 1
    assert r.ctor == []
    assert r.stderr.splitlines()[-1].startswith(
        f"{CATEGORY}: extension module 'linked_ext' links directly to libpython: "
    )


def test_isolated_stable_abi_and_control(isolated):
    r = isolated("import unlinked_ext\nimport abi3_linked_ext\n", "-W", "error::RuntimeWarning")
    assert r.returncode == 1
    assert r.ctor == ["unlinked_ext"]
    assert "has DT_NEEDED libpython3.so" in r.stderr.splitlines()[-1]


def test_isolated_probe_reports_embedded_hook(isolated):
    code = f"""
found = []
sys.audit({PROBE!r}, found)
((kind, category),) = found
print(kind, category.__module__, category.__qualname__, issubclass(category, RuntimeWarning))
"""
    r = isolated(code, "-Werror")
    assert (r.returncode, r.stdout, r.stderr) == (
        0,
        "embedded libpython_linkcheck LibpythonLinkWarning True\n",
        "",
    )


def test_install_twice_installs_one_hook(isolated):
    code = f"""
found = []
sys.audit({PROBE!r}, found)
print([kind for kind, _ in found])
import linked_ext
"""
    r = isolated(code, "-W", "always", env={"LINKCHECK_LAUNCHER_INSTALL_TWICE": "1"})
    assert r.returncode == 0, r.stderr
    assert r.stdout == "['embedded']\n"
    assert len(r.link_warnings) == 1


def test_enable_after_embedded_hook_installs_nothing(venv_launcher, exts, tmp_path, hook_impl):
    code = f"""
import sys
import libpython_linkcheck as m
assert m.is_enabled()
assert m.enable() is False
found = []
sys.audit({PROBE!r}, found)
print([kind for kind, _ in found], found[0][1] is m.LibpythonLinkWarning)
import linked_ext
"""
    r = run_python(
        code,
        "-W",
        "always",
        path=[exts.dir],
        workdir=tmp_path,
        env=impl_env(hook_impl),
        executable=venv_launcher,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout == "['embedded'] True\n"
    assert len(r.link_warnings) == 1, r.stderr


def test_embedded_warning_uses_the_package_category(venv_launcher, exts, tmp_path, hook_impl):
    code = """
import libpython_linkcheck as m
from libpython_linkcheck import _elf
try:
    import linked_ext
except m.LibpythonLinkWarning as w:
    print(_elf.IMPLEMENTATION, w.module, w.needed)
"""
    r = run_python(
        code,
        "-Werror",
        path=[exts.dir],
        workdir=tmp_path,
        env=impl_env(hook_impl),
        executable=venv_launcher,
    )
    assert (r.returncode, r.stderr) == (0, ""), r.stderr
    assert r.stdout == f"{hook_impl} linked_ext {exts.linked.expected_libpython!r}\n"
    assert r.ctor == []


def test_embedded_hook_covers_subinterpreters(isolated, exts):
    sub = f"""
import sys, warnings
sys.path.insert(0, {str(exts.dir)!r})
found = []
sys.audit({PROBE!r}, found)
print("sub probe:", [kind for kind, _ in found], flush=True)
warnings.simplefilter("error")
try:
    import linked_ext
except Warning as w:
    print("sub blocked:", type(w).__module__, type(w).__name__, w.module, flush=True)
"""
    code = SUBINTERPRETER_HELPER + f"run_in_subinterpreter({sub!r})\n"
    r = isolated(code, "-Werror")
    assert (r.returncode, r.stderr) == (0, ""), r.stderr
    assert r.stdout == (
        "sub probe: ['embedded']\n"
        "sub blocked: libpython_linkcheck LibpythonLinkWarning linked_ext\n"
    )
    assert r.ctor == []


def test_hook_survives_reinitialization(launcher, exts, tmp_path):
    lifetime = f"""
import sys, warnings
sys.path.insert(0, {str(exts.dir)!r})
warnings.simplefilter("always")
found = []
sys.audit({PROBE!r}, found)
print("hooks:", [kind for kind, _ in found], flush=True)
import linked_ext
"""
    env = {
        k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "LIBPYTHON_LINKCHECK"))
    }
    env.update(LINKCHECK_LAUNCHER_REINIT="1", PYTHONNOUSERSITE="1")
    proc = subprocess.run(
        [str(launcher), lifetime, lifetime],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "hooks: ['embedded']\nhooks: ['embedded']\n"
    assert proc.stderr.count(": LibpythonLinkWarning: ") == 2, proc.stderr


# --- -W options with the embedded hook ------------------------------------------------


def test_isolated_runtime_warning_option_blocks_the_load(isolated):
    """Without the package, -W error::RuntimeWarning is the way to make it an error."""
    r = isolated("import linked_ext\n", "-W", "error::RuntimeWarning")
    assert r.returncode == 1
    assert r.ctor == []
    assert r.stderr.splitlines()[-1].startswith(f"{CATEGORY}: extension module 'linked_ext' ")


def test_isolated_category_option_cannot_be_resolved(isolated):
    """Documented limitation: no importable package, so CPython drops the option."""
    r = isolated("import linked_ext\n", "-W", f"error::{CATEGORY}")
    assert r.returncode == 0, r.stderr
    assert r.ctor == ["linked_ext"]
    assert STARTUP_NOTICE in r.stderr.splitlines()
    assert len(r.link_warnings) == 1


def run_in_venv_launcher(venv_launcher, exts, tmp_path, hook_impl, code, *flags):
    return run_python(
        code,
        *flags,
        path=[exts.dir],
        workdir=tmp_path,
        env=impl_env(hook_impl),
        executable=venv_launcher,
    )


ENABLE_THEN_IMPORT = f"""
import sys, warnings
import libpython_linkcheck as m
print(m.enable(), m.enable(), flush=True)
found = []
sys.audit({PROBE!r}, found)
print([kind for kind, _ in found], sum(f[2] is m.LibpythonLinkWarning for f in warnings.filters),
      flush=True)
import linked_ext
"""


def test_enable_applies_category_option_after_embedded_hook(
    venv_launcher, exts, tmp_path, hook_impl
):
    r = run_in_venv_launcher(
        venv_launcher, exts, tmp_path, hook_impl, ENABLE_THEN_IMPORT, "-W", f"error::{CATEGORY}"
    )
    assert r.returncode == 1, r.stderr
    assert r.stdout == "False False\n['embedded'] 1\n"
    assert r.ctor == []
    assert r.stderr.splitlines()[-1].startswith(f"{CATEGORY}: extension module 'linked_ext' ")


def test_enable_keeps_option_precedence_with_embedded_hook(
    venv_launcher, exts, tmp_path, hook_impl
):
    r = run_in_venv_launcher(
        venv_launcher,
        exts,
        tmp_path,
        hook_impl,
        ENABLE_THEN_IMPORT,
        "-W",
        f"error::{CATEGORY}",
        "-W",
        "ignore",
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout == "False False\n['embedded'] 1\n"
    assert r.ctor == ["linked_ext"]
    assert r.link_warnings == []
