"""Tests for ``python -m libpython_linkcheck``."""

from __future__ import annotations

import subprocess
import sys

import pytest
from elfbuild import ElfSpec, build_elf
from extbuild import IS_LINUX


def cli(*args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "libpython_linkcheck", *map(str, args)],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )


@pytest.fixture
def objs(tmp_path):
    (tmp_path / "linked.so").write_bytes(
        build_elf(ElfSpec(needed=[b"libpython3.so", b"libpython3.15.so.1.0", b"libc.so.6"]))
    )
    (tmp_path / "clean.so").write_bytes(build_elf(ElfSpec(needed=[b"libc.so.6"])))
    (tmp_path / "text.so").write_text("not ELF\n")
    return tmp_path


def test_clean(objs):
    r = cli("clean.so", cwd=objs)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


def test_linked(objs):
    r = cli("clean.so", "linked.so", cwd=objs)
    assert (r.returncode, r.stderr) == (1, "")
    assert r.stdout == "linked.so: DT_NEEDED libpython3.so, libpython3.15.so.1.0\n"


@pytest.mark.parametrize("bad", ["text.so", "missing.so"])
def test_errors_take_precedence(objs, bad):
    r = cli("linked.so", bad, cwd=objs)
    assert r.returncode == 2
    assert r.stdout.startswith("linked.so: DT_NEEDED")
    assert r.stderr.startswith(f"{bad}: error: ")


def test_usage_error(tmp_path):
    r = cli(cwd=tmp_path)
    assert r.returncode == 2
    assert "usage: python -m libpython_linkcheck" in r.stderr


@pytest.mark.skipif(not IS_LINUX, reason="real ELF extension fixtures are Linux-only")
def test_real_fixtures(exts, tmp_path):
    r = cli(exts.linked.path, exts.abi3.path, exts.unlinked.path, cwd=tmp_path)
    assert r.returncode == 1, r.stderr
    assert r.stdout.splitlines() == [
        f"{exts.linked.path}: DT_NEEDED {exts.linked.expected_libpython[0]}",
        f"{exts.abi3.path}: DT_NEEDED libpython3.so",
    ]
