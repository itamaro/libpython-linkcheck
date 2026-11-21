#!/bin/sh
# Build the sdist and wheel into ./dist, validate them, and smoke-test
# installing each one into a fresh venv outside the checkout.
#
# The wheel is built *from the sdist* (python -m build's default), which
# proves the sdist contains everything needed to build.
#
# Environment:
#   PYTHON   interpreter to build and smoke-test with (default: python3)
#   OUTDIR   output directory (default: dist)
#   SKIP_BUILD=1  only check/smoke-test artifacts already in $OUTDIR
set -eu

repo=$(cd "$(dirname "$0")/.." && pwd)
python=${PYTHON:-python3}
outdir=${OUTDIR:-dist}
case "$outdir" in /*) ;; *) outdir=$repo/$outdir ;; esac

work=$(mktemp -d "${TMPDIR:-/tmp}/linkcheck-dist.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM

"$python" -m venv "$work/tools"
tools=$work/tools/bin/python
"$tools" -m pip --disable-pip-version-check -q install --upgrade "pip>=25.1"
(cd "$repo" && "$tools" -m pip --disable-pip-version-check -q install --group dist)

if [ "${SKIP_BUILD:-0}" != 1 ]; then
    rm -rf "$outdir"
    # The wheel built here is the pure-Python one (py3-none-any), for
    # platforms without a native wheel; Linux wheels come from cibuildwheel.
    LIBPYTHON_LINKCHECK_PURE=1 "$tools" -m build --outdir "$outdir" "$repo"
fi

"$tools" -m twine check --strict "$outdir"/*
"$tools" "$repo/ci/check_dist.py" "$repo" "$outdir"

# Smoke-test each artifact in its own venv (installing the sdist compiles
# the C implementation), from a directory outside the
# checkout, with -I so neither the CWD nor PYTHON* variables leak in.
for artifact in "$outdir"/*.whl "$outdir"/*.tar.gz; do
    name=$(basename "$artifact")
    echo "--- smoke test: $name"
    rm -rf "$work/smoke"
    "$python" -m venv "$work/smoke"
    "$work/smoke/bin/python" -m pip --disable-pip-version-check -q install "$artifact"
    case "$name" in
        *-py3-none-any.whl) expect=python ;;
        *.tar.gz) expect=native ;; # built from source on this POSIX host
        *) expect=native ;;
    esac
    (cd "$work" && LINKCHECK_EXPECT_IMPLEMENTATION=$expect "$work/smoke/bin/python" -I "$repo/ci/smoke.py")
done

# The opt-in autoenable distribution: built and checked here, but kept out
# of $outdir so the release never publishes it.
echo "--- autoenable"
"$tools" -m build --wheel --outdir "$work/autoenable" "$repo/autoenable"
"$tools" "$repo/ci/check_autoenable.py" "$repo" "$work"/autoenable/*.whl
rm -rf "$work/smoke"
"$python" -m venv "$work/smoke"
"$work/smoke/bin/python" -m pip --disable-pip-version-check -q install --no-index \
    "$outdir"/*-py3-none-any.whl "$work"/autoenable/*.whl
(cd "$work" && "$work/smoke/bin/python" -I -c '
import sys
assert "libpython_linkcheck" in sys.modules, "not imported at startup"
import libpython_linkcheck
assert libpython_linkcheck.is_enabled(), "not enabled at startup"
assert not libpython_linkcheck.enable()
print("autoenable smoke OK: enabled at startup on", sys.version.split()[0])
')
echo "dist OK: $(ls "$outdir" | tr '\n' ' ')"
