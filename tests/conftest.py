"""Shared pytest configuration.

Set ``LINKCHECK_REQUIRE_LINUX=1`` (as ``ci/run-tests.sh`` does for the Linux
suite) to make the run fail unless it is on Linux and *no* test was skipped.
A skipped Linux test does not validate ELF or loader behavior.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest
from extbuild import IS_LINUX, BuildError, Exts, build_fixtures

from libpython_linkcheck import _elf

REQUIRE_LINUX = os.environ.get("LINKCHECK_REQUIRE_LINUX") == "1"
#: Set by ci/run-tests.sh unless testing a pure-Python wheel.
REQUIRE_NATIVE = os.environ.get("LINKCHECK_REQUIRE_NATIVE") == "1"

_skipped: list[str] = []


def pytest_configure(config: pytest.Config) -> None:
    if REQUIRE_LINUX and not sys.platform.startswith("linux"):
        raise pytest.UsageError(f"LINKCHECK_REQUIRE_LINUX=1 but sys.platform is {sys.platform!r}")


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.skipped and not hasattr(report, "wasxfail"):
        _skipped.append(report.nodeid)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if REQUIRE_LINUX and _skipped and exitstatus == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter) -> None:
    if REQUIRE_LINUX and _skipped:
        terminalreporter.section("LINKCHECK_REQUIRE_LINUX", red=True)
        terminalreporter.write_line("Skipped tests are failures in the required Linux suite:")
        for nodeid in _skipped:
            terminalreporter.write_line(f"  {nodeid}")


@pytest.fixture(scope="session")
def exts(tmp_path_factory: pytest.TempPathFactory) -> Exts:
    """The real fixture extension modules, compiled once per session (Linux only)."""
    if not IS_LINUX:
        pytest.skip("real ELF extension fixtures are only built on Linux")
    try:
        return build_fixtures(tmp_path_factory.mktemp("exts"))
    except BuildError as e:
        if REQUIRE_LINUX:
            pytest.fail(f"could not build fixture extensions:\n{e}")
        pytest.skip(f"could not build fixture extensions: {e}")


def _implementations() -> list[str]:
    if _elf._native is not None or REQUIRE_NATIVE:
        return ["python", "native"]
    return ["python"]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _elf._native is not None or REQUIRE_NATIVE:
        return
    keep, drop = [], []
    for item in items:
        (drop if item.get_closest_marker("requires_native") else keep).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "impl" in metafunc.fixturenames:
        metafunc.parametrize("impl", _implementations(), indirect=True)
    if "hook_impl" in metafunc.fixturenames:
        metafunc.parametrize("hook_impl", _implementations(), indirect=True)


@pytest.fixture
def hook_impl(request: pytest.FixtureRequest) -> str:
    """Hook implementation for subprocess tests: "python" or "native"."""
    return request.param


@pytest.fixture
def impl(request: pytest.FixtureRequest) -> SimpleNamespace:
    """One reader implementation: ``impl.read_needed`` and ``impl.is_libpython``."""
    if request.param == "python":
        return SimpleNamespace(
            name="python", read_needed=_elf.py_read_needed, is_libpython=_elf.py_is_libpython
        )
    if _elf._native is None:
        pytest.fail("LINKCHECK_REQUIRE_NATIVE=1 but libpython_linkcheck._native is not built")
    return SimpleNamespace(
        name="native", read_needed=_elf._native_read_needed, is_libpython=_elf._native.is_libpython
    )
