"""Run Python code in a fresh interpreter, as a user would.

Audit hooks cannot be removed, so every behavior test runs in a subprocess.
"""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str
    #: Module names logged by fixture ELF constructors, in load order.
    ctor: list[str]

    @property
    def link_warnings(self) -> list[str]:
        """Lines of stderr that display a LibpythonLinkWarning."""
        return [ln for ln in self.stderr.splitlines() if ": LibpythonLinkWarning: " in ln]

    @property
    def stderr_lines(self) -> list[str]:
        """stderr without CPython's startup notice for -W options naming our category."""
        return [ln for ln in self.stderr.splitlines() if ln != STARTUP_NOTICE]


#: Printed by CPython itself when a -W option names a category from a package
#: that is not importable before site-packages is on sys.path. enable() then
#: applies the option (see _hook._apply_dropped_warnoptions).
STARTUP_NOTICE = "Invalid -W option ignored: invalid module name: 'libpython_linkcheck'"


#: Runs *code* in a fresh subinterpreter of the current interpreter.
SUBINTERPRETER_HELPER = """
def run_in_subinterpreter(code):
    try:
        import _interpreters as interpreters  # 3.13+
    except ImportError:
        import _xxsubinterpreters as interpreters  # 3.12
    interp = interpreters.create()
    try:
        interpreters.run_string(interp, code)
    finally:
        interpreters.destroy(interp)
"""


#: Runs *code* in a fresh subinterpreter with its own GIL, which loads only
#: extensions that declare per-interpreter GIL support.
OWN_GIL_SUBINTERPRETER_HELPER = """
def run_in_own_gil_subinterpreter(code):
    try:
        import _interpreters as interpreters  # 3.13+
    except ImportError:
        import _xxsubinterpreters as interpreters  # 3.12: isolated means its own GIL
        interp = interpreters.create(isolated=True)
    else:
        config = interpreters.new_config("isolated")
        assert config.gil == "own" and config.check_multi_interp_extensions, config
        interp = interpreters.create(config)
    try:
        failure = interpreters.run_string(interp, code)  # 3.13+ returns, 3.12 raises
        if failure is not None:
            raise RuntimeError(f"subinterpreter failed: {failure}")
    finally:
        interpreters.destroy(interp)
"""


@dataclass(frozen=True)
class Venv:
    python: Path
    site_packages: Path


def package_parent() -> Path:
    """The directory the package under test is imported from (site-packages)."""
    import libpython_linkcheck  # noqa: PLC0415

    return Path(libpython_linkcheck.__file__).resolve().parent.parent


def make_venv(dest: Path) -> Venv:
    """A fresh venv (no pip) whose site-packages can import this package.

    A ``_linkcheck_tests.pth`` path entry (sorted before any activation file)
    points at the directory the package under test was imported from.
    """
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(dest)], check=True)
    site = Path(sysconfig.get_path("purelib", vars={"base": str(dest), "platbase": str(dest)}))
    (site / "_linkcheck_tests.pth").write_text(f"{package_parent()}\n")
    return Venv(dest / "bin" / "python", site)


def impl_env(hook_impl: str) -> dict[str, str]:
    """Environment that selects *hook_impl* ("python" or "native") in a child."""
    return {"LIBPYTHON_LINKCHECK_IMPLEMENTATION": "python"} if hook_impl == "python" else {}


def run_python(
    code: str,
    *flags: str,
    path: Sequence[Path] = (),
    workdir: Path,
    env: dict[str, str] | None = None,
    executable: str | os.PathLike[str] = sys.executable,
) -> Result:
    log = workdir / "ctor.log"
    log.unlink(missing_ok=True)
    child_env = {
        k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "LIBPYTHON_LINKCHECK_"))
    }
    if path:
        child_env["PYTHONPATH"] = os.pathsep.join(map(str, path))
    child_env["LINKCHECK_FIXTURE_CTOR_LOG"] = str(log)
    child_env.update(env or {})
    proc = subprocess.run(
        [os.fspath(executable), *flags, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env=child_env,
        cwd=workdir,
        timeout=120,
        check=False,
    )
    ctor = log.read_text().splitlines() if log.exists() else []
    return Result(proc.returncode, proc.stdout, proc.stderr, ctor)
