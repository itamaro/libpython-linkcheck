#!/bin/sh
# Build the sdist and pure-Python wheel into ./dist, and the autoenable
# companion's sdist and wheel into ./autoenable-dist, validate them, and
# smoke-test installing each one into a fresh venv outside the checkout.
#
# Each wheel is built *from its sdist* (python -m build's default), which
# proves the sdist contains everything needed to build.
#
# Environment:
#   PYTHON   interpreter to build and smoke-test with (default: python3)
#   OUTDIR   output directory (default: dist)
#   AUTOENABLE_OUTDIR  output directory for the companion (default: autoenable-dist)
#   SKIP_BUILD=1  only check/smoke-test artifacts already in the output directories
set -eu

repo=$(cd "$(dirname "$0")/.." && pwd)
python=${PYTHON:-python3}
outdir=${OUTDIR:-dist}
case "$outdir" in /*) ;; *) outdir=$repo/$outdir ;; esac
autoenable_outdir=${AUTOENABLE_OUTDIR:-autoenable-dist}
case "$autoenable_outdir" in /*) ;; *) autoenable_outdir=$repo/$autoenable_outdir ;; esac

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

# The opt-in autoenable companion, a separate project on PyPI: kept out of
# $outdir, which holds only libpython-linkcheck's own distributions.
echo "--- autoenable"
if [ "${SKIP_BUILD:-0}" != 1 ]; then
    rm -rf "$autoenable_outdir"
    "$tools" -m build --outdir "$autoenable_outdir" "$repo/autoenable"
fi
"$tools" -m twine check --strict "$autoenable_outdir"/*
"$tools" "$repo/ci/check_autoenable.py" "$repo" "$autoenable_outdir"
rm -rf "$work/smoke"
"$python" -m venv "$work/smoke"
"$work/smoke/bin/python" -m pip --disable-pip-version-check -q install --no-index \
    "$outdir"/*-py3-none-any.whl "$autoenable_outdir"/*.whl
(cd "$work" && "$work/smoke/bin/python" -I -c '
import sys
assert "libpython_linkcheck" in sys.modules, "not imported at startup"
import libpython_linkcheck
assert libpython_linkcheck.is_enabled(), "not enabled at startup"
assert not libpython_linkcheck.enable()
print("autoenable smoke OK: enabled at startup on", sys.version.split()[0])
')
echo "dist OK: $(ls "$outdir" "$autoenable_outdir" | tr '\n' ' ')"
