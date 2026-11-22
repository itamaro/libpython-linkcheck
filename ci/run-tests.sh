#!/bin/sh
# Install libpython-linkcheck into a fresh venv and run the pytest suite
# against the installed copy (never against the source tree).
#
# This is the single test entry point used by `make test`, `make test-linux`
# (inside Podman) and GitHub Actions.
#
# Environment:
#   PYTHON                   interpreter used to create the venv (default: python3)
#   PACKAGE                  what to install: a wheel, an sdist, a source
#                            directory, or a directory of wheels (pip picks the
#                            one for this interpreter; e.g. cibuildwheel's
#                            wheelhouse/) (default: a scratch copy of this checkout)
#   LINKCHECK_REQUIRE_LINUX  set to 1 to fail unless running on Linux with no
#                            skipped tests (the Linux suite sets this)
#   LINKCHECK_REQUIRE_NATIVE 1 (default) to require the C implementation;
#                            defaults to 0 when PACKAGE is a pure-Python wheel
#
# Before pytest it checks the installed wheel's tags: PACKAGE's own for a
# wheel file, the wheel matrix entry for this interpreter for a directory
# (what pip should pick by project name), and the setup.py target for a
# source tree or sdist.
#   CFLAGS                   extra C flags; -Werror is always added when the
#                            C extension is compiled from source
#   LINKCHECK_BENCH          set to 1 to run ci/bench_hook.py (the hook overhead
#                            benchmark) against the installed package instead of
#                            pytest
#
# Extra arguments are passed to pytest. The exit status is pytest's.
set -eu

repo=$(cd "$(dirname "$0")/.." && pwd)
python=${PYTHON:-python3}

work=$(mktemp -d "${TMPDIR:-/tmp}/linkcheck-tests.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM

# Copy the checkout so nothing is ever written into it (it may be a read-only
# bind mount) and so tests cannot accidentally import from the source tree.
mkdir "$work/src"
tar -C "$repo" \
    --exclude=./.git --exclude=./.venv --exclude=./dist --exclude=./build \
    --exclude='*.egg-info' --exclude=__pycache__ --exclude=.pytest_cache \
    --exclude=.ruff_cache -cf - . | tar -C "$work/src" -xf -

if [ -n "${PACKAGE:-}" ]; then
    case "$PACKAGE" in
        /*) package=$PACKAGE ;;
        *) package=$(pwd)/$PACKAGE ;;
    esac
else
    package=$work/src
fi

case "$package" in
    *-py3-none-any.whl) : "${LINKCHECK_REQUIRE_NATIVE:=0}" ;;
    *) : "${LINKCHECK_REQUIRE_NATIVE:=1}" ;;
esac
export LINKCHECK_REQUIRE_NATIVE
# Compiler warnings in the C implementation are errors in every test build.
CFLAGS="${CFLAGS:-} -Werror"
export CFLAGS

"$python" -m venv "$work/venv"
venv_python=$work/venv/bin/python
pip() { "$venv_python" -m pip --disable-pip-version-check -q "$@"; }

# Dependency groups (pip install --group) need pip >= 25.1.
pip install --upgrade "pip>=25.1"
if [ -d "$package" ] && [ ! -e "$package/pyproject.toml" ]; then
    pip install --no-index --find-links "$package" --only-binary :all: libpython-linkcheck
else
    pip install "$package"
fi
(cd "$work/src" && pip install --group test)

cd "$work"
LINKCHECK_PACKAGE=$package "$venv_python" - <<'EOF'
import os
import sys
import sysconfig
from importlib.metadata import distribution

import libpython_linkcheck

where = libpython_linkcheck.__file__
if "site-packages" not in where:
    sys.exit(f"libpython_linkcheck imported from {where}, not the installed copy")
from libpython_linkcheck import _elf
print(f"Testing libpython_linkcheck {libpython_linkcheck.__version__} from {where}"
      f" ({_elf.IMPLEMENTATION} implementation)")
if _elf._native is not None:
    print(f"C extension: {_elf._native.__file__}")
import sysconfig
if sysconfig.get_config_var("Py_GIL_DISABLED"):
    libpython_linkcheck.enable()
    if sys._is_gil_enabled():
        sys.exit("importing libpython_linkcheck re-enabled the GIL")
    print("free-threaded build: the GIL stays disabled")
print(f"Python {sys.version} on {sys.platform}")

# Which wheel got installed: a wheel file as itself; from a directory, the
# one pip should pick for this interpreter (the wheel matrix in AGENTS.md);
# from source, the target setup.py builds for it.
package = os.environ["LINKCHECK_PACKAGE"]
free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
if package.endswith(".whl"):
    expected = "-".join(os.path.basename(package).split("-")[2:4])
elif free_threaded:
    expected = "cp315-abi3.abi3t" if sys.version_info >= (3, 15) else "cp314-cp314t"
elif os.path.isdir(package) and not os.path.exists(os.path.join(package, "pyproject.toml")):
    expected = "cp315-abi3.abi3t" if sys.version_info >= (3, 15) else "cp312-abi3"
else:
    expected = "cp312-abi3"
python_tag, abis = expected.split("-")
wheel = distribution("libpython-linkcheck").read_text("WHEEL") or ""
installed = sorted(
    line.split(": ", 1)[1].rsplit("-", 1)[0] for line in wheel.splitlines() if line.startswith("Tag: ")
)
if installed != sorted(f"{python_tag}-{abi}" for abi in abis.split(".")):
    sys.exit(f"installed a wheel tagged {installed}, expected {expected}")
print(f"Installed wheel: {expected}")
EOF

# -P: do not put the CWD on sys.path, so only the installed package is importable.
# Not exec: the shell must survive pytest so its EXIT trap removes $work.
# Under set -e a failing pytest exits the shell with pytest's status, and the
# trap preserves it.
cd "$work/src"
if [ "${LINKCHECK_BENCH:-0}" = 1 ]; then
    "$venv_python" -P ci/bench_hook.py
else
    # --basetemp keeps pytest's tmp_path directories inside $work as well.
    "$venv_python" -P -m pytest -p no:cacheprovider --basetemp "$work/pytest" tests "$@"
fi
