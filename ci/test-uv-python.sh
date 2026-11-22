#!/bin/sh
# Run ci/run-tests.sh on a uv-managed CPython (python-build-standalone),
# inside a docker.io/library/python:<ver>-trixie container (for cc and
# readelf).
#
# Its layout differs from the Debian-style images: the executable is linked
# statically although a shared libpython is shipped (Py_ENABLE_SHARED=1),
# and the installation is relocatable. Used by `make test-linux-uv-python`
# and the CI `uv-python` job.
#
# uv and the CPython build are pinned: a uv release fixes the
# python-build-standalone release and the sha256 of each download, which uv
# verifies.
#
# Environment:
#   UV_VERSION   default 0.13.9
#   UV_PYTHON    CPython version to install (default 3.12.16)
set -eu

uv_version=${UV_VERSION:-0.13.9}
uv_python=${UV_PYTHON:-3.12.16}
here=$(cd "$(dirname "$0")" && pwd)

tools=$(mktemp -d "${TMPDIR:-/tmp}/uv-tools.XXXXXX")
trap 'rm -rf "$tools"' EXIT INT TERM
python3 -m venv "$tools/venv"
"$tools/venv/bin/python" -m pip --disable-pip-version-check -q install "uv==$uv_version"
uv=$tools/venv/bin/uv

UV_PYTHON_INSTALL_DIR=${UV_PYTHON_INSTALL_DIR:-$tools/python}
export UV_PYTHON_INSTALL_DIR
"$uv" python install --no-bin "$uv_python"
PYTHON=$("$uv" python find --managed-python --no-python-downloads "$uv_python")
export PYTHON
echo "uv $uv_version, $PYTHON"
readelf --dynamic --wide "$(readlink -f "$PYTHON")" | grep NEEDED || true

# Not exec: the trap must remove $tools after the tests.
sh "$here/run-tests.sh" "$@"
