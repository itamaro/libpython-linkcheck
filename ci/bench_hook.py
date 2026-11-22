"""Measure the audit hook's overhead.

Usage: python ci/bench_hook.py

Runs each scenario in a fresh interpreter (audit hooks cannot be removed)
with no hook, with the pure-Python hook, and with the hook of the installed
implementation (the C one when `_native` is available), and prints the
best-of-repeats time per operation:

- an unrelated audit event (the fast path every hook call takes);
- an "import" event without a filename (what every pure-Python import
  raises);
- a clean extension import: an extension that does not link libpython,
  removed from sys.modules and imported again, so the hook reads its ELF
  headers each time.

Needs a C compiler and Python headers (it builds the test fixtures), so run
it on Linux: `make bench-linux` runs it through ci/run-tests.sh
(LINKCHECK_BENCH=1) against the installed package.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = Path(__file__).resolve().parent.parent / "tests"

SCENARIOS = {
    "unrelated event": (
        "audit = sys.audit\ndef op():\n    audit('bench.unrelated', 1, 'x')\n",
        200_000,
    ),
    "import event, no file": (
        "audit = sys.audit\ndef op():\n    audit('import', 'm', None, None, None, None)\n",
        200_000,
    ),
    "clean extension import": (
        "import importlib, unlinked_ext\n"
        "modules = sys.modules\n"
        "def op():\n"
        "    del modules['unlinked_ext']\n"
        "    importlib.import_module('unlinked_ext')\n",
        5_000,
    ),
}

RUNNER = """
import sys, time
sys.path.insert(0, {ext_dir!r})
mode = {mode!r}
if mode != "none":
    import libpython_linkcheck
    from libpython_linkcheck import _elf
    assert libpython_linkcheck.enable()
    assert _elf.IMPLEMENTATION == mode, (_elf.IMPLEMENTATION, mode)
{setup}
n = {n}
best = float("inf")
for _ in range(7):
    t0 = time.perf_counter_ns()
    for _ in range(n):
        op()
    best = min(best, (time.perf_counter_ns() - t0) / n)
print(best)
"""


def run(mode: str, setup: str, n: int, ext_dir: Path) -> float:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env.pop("LIBPYTHON_LINKCHECK_IMPLEMENTATION", None)
    if mode == "python":
        env["LIBPYTHON_LINKCHECK_IMPLEMENTATION"] = "python"
    code = RUNNER.format(ext_dir=str(ext_dir), mode=mode, setup=setup, n=n)
    out = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, env=env, check=False
    )
    if out.returncode != 0:
        sys.exit(f"benchmark {mode!r} failed:\n{out.stdout}{out.stderr}")
    return float(out.stdout)


def main() -> None:
    sys.path.insert(0, str(TESTS))
    from extbuild import build_fixtures  # noqa: PLC0415 (needs the tests on sys.path)

    from libpython_linkcheck import _elf  # noqa: PLC0415

    modes = ["none", "python"] + (["native"] if _elf.IMPLEMENTATION == "native" else [])
    native = _elf._native.__file__ if _elf._native else None
    print(f"Python {sys.version.split()[0]} ({sys.implementation.cache_tag}); _native: {native}")
    results: dict[str, dict[str, float]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        exts = build_fixtures(Path(tmp))
        for name, (setup, n) in SCENARIOS.items():
            results[name] = {mode: run(mode, setup, n, exts.dir) for mode in modes}
    print(f"{'ns per operation':<24}" + "".join(f"{m:>10}" for m in modes) + "  (overhead)")
    for name, row in results.items():
        cells = "".join(f"{row[m]:>10.0f}" for m in modes)
        over = "  ".join(f"{m} +{row[m] - row['none']:.0f}" for m in modes[1:])
        print(f"{name:<24}{cells}  ({over})")


if __name__ == "__main__":
    main()
