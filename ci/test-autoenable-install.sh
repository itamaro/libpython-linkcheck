#!/bin/sh
# Install the autoenable companion as a user would, in a fresh venv inside a
# docker.io/library/python image, and check (ci/autoenable_install_check.py):
#   1. installing only libpython-linkcheck-autoenable by project name pulls
#      in the exact core version it pins, and a fresh launch has the native
#      hook enabled at startup, from the wheel this interpreter should get;
#   2. -S skips activation;
#   3. after uninstalling only the companion, the core is still installed,
#      and the next launch has no hook.
#
# Used by `make test-autoenable-install` and the dist workflow (built files)
# and by `make verify-pypi` (production PyPI).
#
# Environment:
#   FIND_LINKS      space-separated directories of built distributions (core and
#                   companion): install from them only (pip --no-index)
#   VERSION         without FIND_LINKS: install this version from production
#                   PyPI, without a cache
#   FREETHREADED=1  use a free-threaded build of the image's CPython
#                   (ci/build-freethreaded.sh), else the image's python3
set -eu

here=$(cd "$(dirname "$0")" && pwd)
if [ "${FREETHREADED:-0}" = 1 ]; then
    python=$(sh "$here/build-freethreaded.sh")
else
    python=python3
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/linkcheck-autoenable.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
"$python" -m venv "$work/venv"
py=$work/venv/bin/python
pip() { "$py" -m pip --disable-pip-version-check --no-cache-dir "$@"; }

if [ -n "${FIND_LINKS:-}" ]; then
    set -- --no-index
    for dir in $FIND_LINKS; do
        set -- "$@" --find-links "$dir"
    done
    echo "=== $("$py" -VV): libpython-linkcheck-autoenable from $FIND_LINKS"
    pip install -q "$@" libpython-linkcheck-autoenable
else
    : "${VERSION:?set FIND_LINKS or VERSION}"
    echo "=== $("$py" -VV): libpython-linkcheck-autoenable==$VERSION from PyPI"
    pip install -q "libpython-linkcheck-autoenable==$VERSION"
fi
pip list --format=freeze | grep -i '^libpython'

# From an empty directory, with -I: nothing from the checkout or PYTHON*
# variables gets in, and site-packages is the venv's only.
cd "$work"
"$py" -I "$here/autoenable_install_check.py" active
"$py" -I -S "$here/autoenable_install_check.py" no-site
pip uninstall -q -y libpython-linkcheck-autoenable
pip show -q libpython-linkcheck
"$py" -I "$here/autoenable_install_check.py" uninstalled
echo "autoenable install OK"
