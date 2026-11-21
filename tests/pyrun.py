"""Run Python code in a fresh interpreter, as a user would.

Audit hooks cannot be removed, so every behavior test runs in a subprocess.
"""

from __future__ import annotations

import os
import subprocess
import sys
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


def run_python(
    code: str,
    *flags: str,
    path: Sequence[Path] = (),
    workdir: Path,
    env: dict[str, str] | None = None,
) -> Result:
    log = workdir / "ctor.log"
    log.unlink(missing_ok=True)
    child_env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    if path:
        child_env["PYTHONPATH"] = os.pathsep.join(map(str, path))
    child_env["LINKCHECK_FIXTURE_CTOR_LOG"] = str(log)
    child_env.update(env or {})
    proc = subprocess.run(
        [sys.executable, *flags, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env=child_env,
        cwd=workdir,
        timeout=120,
        check=False,
    )
    ctor = log.read_text().splitlines() if log.exists() else []
    return Result(proc.returncode, proc.stdout, proc.stderr, ctor)
