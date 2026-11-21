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
#   CFLAGS                   extra C flags; -Werror is always added when the
#                            C extension is compiled from source
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
"$venv_python" - <<'EOF'
import sys
import libpython_linkcheck

where = libpython_linkcheck.__file__
if "site-packages" not in where:
    sys.exit(f"libpython_linkcheck imported from {where}, not the installed copy")
from libpython_linkcheck import _elf
print(f"Testing libpython_linkcheck {libpython_linkcheck.__version__} from {where}"
      f" ({_elf.IMPLEMENTATION} implementation)")
if _elf._native is not None:
    print(f"C extension: {_elf._native.__file__}")
print(f"Python {sys.version} on {sys.platform}")
EOF

# -P: do not put the CWD on sys.path, so only the installed package is importable.
cd "$work/src"
exec "$venv_python" -P -m pytest -p no:cacheprovider tests "$@"
