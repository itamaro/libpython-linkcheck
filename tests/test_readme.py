"""Run the README's copy-paste demo and compare with its documented output."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest
from extbuild import IS_LINUX

README = Path(__file__).resolve().parent.parent / "README.md"
DOC_SUFFIX = ".cpython-315-x86_64-linux-gnu.so"
DOC_SONAME = "libpython3.15.so.1.0"


def fenced_block_after(text: str, marker: str) -> str:
    start = text.index(marker)
    m = re.compile(r"^```[a-z]*\n(.*?)^```$", re.M | re.S).search(text, start)
    assert m, f"no fenced block after {marker!r}"
    return m.group(1)


def test_readme_demo_block_is_present():
    text = README.read_text()
    assert "pip install libpython-linkcheck" in fenced_block_after(text, "<!-- readme-demo")


@pytest.mark.skipif(not IS_LINUX, reason="the README demo builds a Linux extension")
def test_readme_demo(tmp_path):
    text = README.read_text()
    script = fenced_block_after(text, "<!-- readme-demo")
    expected = fenced_block_after(text, "Expected output")
    # The package under test is already installed in this interpreter's venv.
    script = "\n".join(ln for ln in script.splitlines() if not ln.startswith("pip install"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    # `python` is this venv's interpreter; `python3-config` must describe the
    # same build (a venv has none, and the one on PATH may belong to a
    # different interpreter, e.g. the GIL-enabled one next to a free-threaded
    # build).
    bindir = tmp_path / "bin"
    bindir.mkdir()
    config = Path(sysconfig.get_config_var("BINDIR")) / (
        f"python{sysconfig.get_config_var('LDVERSION')}-config"
    )
    # A wrapper, not a symlink: the script derives its prefix from $0.
    wrapper = bindir / "python3-config"
    wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(str(config))} "$@"\n')
    wrapper.chmod(0o755)
    env["PATH"] = os.pathsep.join([os.path.dirname(sys.executable), str(bindir), env["PATH"]])
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        # The demo module does not declare Py_mod_gil; keep CPython's
        # "GIL has been enabled" notice out of the compared output.
        env["PYTHON_GIL"] = "0"
    # stderr merged into stdout, as a terminal shows it.
    proc = subprocess.run(
        ["sh", "-e", "-c", script],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout
    actual = proc.stdout
    actual = actual.replace(str(tmp_path / "demo"), "/demo")
    actual = actual.replace(sysconfig.get_config_var("EXT_SUFFIX"), DOC_SUFFIX)
    actual = actual.replace(sysconfig.get_config_var("INSTSONAME"), DOC_SONAME)
    # Collapse traceback frames, which differ between Python versions.
    actual = re.sub(r"(Traceback \(most recent call last\):\n)(?:  .*\n)+", r"\1  ...\n", actual)
    assert actual == expected
