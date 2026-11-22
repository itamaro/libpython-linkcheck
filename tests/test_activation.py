"""Activation paths: sitecustomize, usercustomize, and .pth / .start files.

Every case runs a fresh interpreter in a fresh venv (or with a private user
site directory) and imports the real linked fixture. The .pth / .start pair
is the one the opt-in autoenable/ distribution installs.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from extbuild import IS_LINUX, Exts
from pyrun import STARTUP_NOTICE, Result, Venv, impl_env, make_venv, package_parent, run_python

pytestmark = pytest.mark.skipif(not IS_LINUX, reason="activation is tested on Linux")

AUTOENABLE = Path(__file__).resolve().parent.parent / "autoenable"
PTH = "libpython_linkcheck_autoenable.pth"
START = "libpython_linkcheck_autoenable.start"
HAS_START_FILES = sys.version_info >= (3, 15)  # PEP 829
CUSTOMIZE = "import libpython_linkcheck\nlibpython_linkcheck.enable()\n"

#: Report the active hooks, then import the linked fixture.
REPORT_AND_IMPORT = """
import sys
found = []
sys.audit("libpython_linkcheck.probe", found)
print([kind for kind, _ in found], flush=True)
import linked_ext
"""


@pytest.fixture
def venv(tmp_path) -> Venv:
    return make_venv(tmp_path / "venv")


@pytest.fixture
def run(venv: Venv, exts: Exts, tmp_path, hook_impl):
    def run(code=REPORT_AND_IMPORT, *flags, env=None) -> Result:
        return run_python(
            code,
            *flags,
            path=[exts.dir],
            workdir=tmp_path,
            env={**impl_env(hook_impl), **(env or {})},
            executable=venv.python,
        )

    return run


def install_autoenable(site: Path, *names: str) -> None:
    for name in names or (PTH, START):
        shutil.copy2(AUTOENABLE / name, site / name)


def assert_blocked(r: Result, kinds: list[str]) -> None:
    assert r.returncode == 1, r.stderr
    assert r.stdout == f"{kinds}\n"
    assert r.ctor == []
    assert r.stderr.splitlines()[-1].startswith(
        "libpython_linkcheck.LibpythonLinkWarning: extension module 'linked_ext' "
    )


def test_nothing_is_active_by_default(run):
    r = run(REPORT_AND_IMPORT, "-Werror")
    assert (r.returncode, r.stdout, r.ctor) == (0, "[]\n", ["linked_ext"]), r.stderr


def test_sitecustomize(run, venv, hook_impl):
    (venv.site_packages / "sitecustomize.py").write_text(CUSTOMIZE)
    assert_blocked(run(REPORT_AND_IMPORT, "-Werror"), [hook_impl])


def test_sitecustomize_with_category_filter_on_the_command_line(run, venv, hook_impl):
    """-W naming our category is dropped by CPython at startup; enable() restores it."""
    (venv.site_packages / "sitecustomize.py").write_text(CUSTOMIZE)
    r = run(REPORT_AND_IMPORT, "-W", "error::libpython_linkcheck.LibpythonLinkWarning")
    assert_blocked(r, [hook_impl])


CATEGORY = "libpython_linkcheck.LibpythonLinkWarning"


def startup_env(exts: Exts, startup: str) -> dict[str, str]:
    """Make the package importable at startup ("resolved"), or not ("dropped")."""
    return {"PYTHONPATH": f"{package_parent()}:{exts.dir}"} if startup == "resolved" else {}


@pytest.mark.parametrize("startup", ["resolved", "dropped"])
@pytest.mark.parametrize(
    "flags",
    [
        ("-W", "ignore", "-W", f"error::{CATEGORY}"),
        # The module field is anchored as this CPython anchors it (\Z, or \z on 3.14+).
        ("-W", "ignore:::__main__", "-W", f"error::{CATEGORY}"),
        ("-W", f"error::{CATEGORY}:__main__", "-W", "ignore::UserWarning:__main__"),
        # A /regex/ message (3.15+; earlier versions match it literally).
        ("-W", "ignore", "-W", f"error:/^extension module /:{CATEGORY}"),
    ],
    ids=["ignore", "ignore-main", "error-main", "message-regex"],
)
def test_autoenable_keeps_option_precedence(run, venv, exts, hook_impl, *, flags, startup):
    """The autoenable files run before sitecustomize and program code, so a
    recovered entry gets the precedence of its position, exactly as when
    CPython resolves it at startup."""
    install_autoenable(venv.site_packages)
    r = run(REPORT_AND_IMPORT, *flags, env=startup_env(exts, startup))
    assert (STARTUP_NOTICE in r.stderr.splitlines()) is (startup == "dropped"), r.stderr
    if "/" in flags[-1] and sys.version_info < (3, 15):
        assert r.returncode == 0, r.stderr
        assert (r.stdout, r.ctor) == (f"{[hook_impl]}\n", ["linked_ext"])
    else:
        assert_blocked(r, [hook_impl])


@pytest.mark.parametrize("startup", ["resolved", "dropped"])
def test_sitecustomize_filters_keep_precedence(run, venv, exts, hook_impl, startup):
    """sitecustomize may set its own policy before enable(), and the filter
    list cannot tell its simplefilter("ignore") from -W ignore: it wins."""
    (venv.site_packages / "sitecustomize.py").write_text(
        "import warnings\nwarnings.simplefilter('ignore')\n" + CUSTOMIZE
    )
    flags = ("-W", "ignore", "-W", f"error::{CATEGORY}")
    r = run(REPORT_AND_IMPORT, *flags, env=startup_env(exts, startup))
    assert (STARTUP_NOTICE in r.stderr.splitlines()) is (startup == "dropped"), r.stderr
    assert r.returncode == 0, r.stderr
    assert (r.stdout, r.ctor) == (f"{[hook_impl]}\n", ["linked_ext"])
    assert r.link_warnings == []


def test_usercustomize(exts: Exts, tmp_path, hook_impl):
    # User site directories are disabled in venvs, so use the interpreter the
    # test venv was created from, with a private user base.
    base = Path(sys._base_executable)
    userbase = tmp_path / "userbase"
    env = {**impl_env(hook_impl), "PYTHONUSERBASE": str(userbase)}
    usersite = Path(
        subprocess.run(
            [base, "-c", "import site; print(site.getusersitepackages())"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    usersite.mkdir(parents=True)
    (usersite / "_linkcheck_tests.pth").write_text(f"{package_parent()}\n")
    (usersite / "usercustomize.py").write_text(CUSTOMIZE)
    r = run_python(
        REPORT_AND_IMPORT, "-Werror", path=[exts.dir], workdir=tmp_path, env=env, executable=base
    )
    assert_blocked(r, [hook_impl])
    # -s disables the user site directory, and with it usercustomize.
    r = run_python(
        REPORT_AND_IMPORT,
        "-s",
        "-Werror",
        path=[exts.dir],
        workdir=tmp_path,
        env=env,
        executable=base,
    )
    assert (r.returncode, r.stdout, r.ctor) == (0, "[]\n", ["linked_ext"]), r.stderr


def test_pth_import_line_alone(run, venv, hook_impl):
    install_autoenable(venv.site_packages, PTH)
    assert_blocked(run(REPORT_AND_IMPORT, "-Werror"), [hook_impl])


def test_start_file_alone(run, venv, hook_impl):
    install_autoenable(venv.site_packages, START)
    r = run(REPORT_AND_IMPORT, "-Werror")
    if HAS_START_FILES:
        assert_blocked(r, [hook_impl])
    else:  # ignored before 3.15
        assert (r.returncode, r.stdout, r.ctor) == (0, "[]\n", ["linked_ext"]), r.stderr


def test_matching_pth_and_start_enable_once(run, venv, hook_impl):
    """The shipped pair: the .start disables the .pth import line on 3.15+."""
    install_autoenable(venv.site_packages)
    code = (
        "import libpython_linkcheck\n"
        "print('enable() in user code:', libpython_linkcheck.enable())\n" + REPORT_AND_IMPORT
    )
    r = run(code, "-W", "always")
    assert r.returncode == 0, r.stderr
    assert r.stdout == f"enable() in user code: False\n['{hook_impl}']\n"
    assert len(r.link_warnings) == 1, r.stderr
    assert r.ctor == ["linked_ext"]


def test_every_activation_path_at_once(run, venv, hook_impl):
    install_autoenable(venv.site_packages)
    (venv.site_packages / "sitecustomize.py").write_text(
        "import libpython_linkcheck\nprint('sitecustomize:', libpython_linkcheck.enable())\n"
    )
    code = "import libpython_linkcheck\nlibpython_linkcheck.enable()\n" + REPORT_AND_IMPORT
    r = run(code, "-W", "always")
    assert r.returncode == 0, r.stderr
    # .pth/.start run before sitecustomize, so the latter finds the hook.
    assert r.stdout == f"sitecustomize: False\n['{hook_impl}']\n"
    assert len(r.link_warnings) == 1, r.stderr


def test_isolated_mode_keeps_site_packages_activation(run, venv, exts, hook_impl):
    install_autoenable(venv.site_packages)
    code = f"import sys\nsys.path.insert(0, {str(exts.dir)!r})\n" + REPORT_AND_IMPORT
    assert_blocked(run(code, "-I", "-Werror"), [hook_impl])


def test_no_site_disables_site_packages_activation(run, venv, exts):
    """Under -S only a hook installed by the executable applies (test_embedded.py)."""
    install_autoenable(venv.site_packages)
    (venv.site_packages / "sitecustomize.py").write_text(CUSTOMIZE)
    code = f"import sys\nsys.path.insert(0, {str(exts.dir)!r})\n" + REPORT_AND_IMPORT
    r = run(code, "-S", "-Werror")
    assert (r.returncode, r.stdout, r.ctor) == (0, "[]\n", ["linked_ext"]), r.stderr
