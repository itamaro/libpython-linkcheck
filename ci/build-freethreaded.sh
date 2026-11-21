#!/bin/sh
# Build a free-threaded (--disable-gil), shared-libpython CPython inside a
# docker.io/library/python:<ver>-trixie container, for the same release as
# the image's own interpreter, and print the path of its executable.
#
# The source tarball is verified against the image's PYTHON_SHA256. The
# result is reused if PREFIX already contains it (a cache volume locally,
# actions/cache in CI).
#
# Environment:
#   PREFIX   install prefix (default: /opt/python-ft/$PYTHON_VERSION)
set -eu

: "${PYTHON_VERSION:?run this in a docker.io/library/python image}"
: "${PYTHON_SHA256:?run this in a docker.io/library/python image}"
prefix=${PREFIX:-/opt/python-ft/$PYTHON_VERSION}
minor=$(echo "$PYTHON_VERSION" | cut -d. -f1,2)
exe=$prefix/bin/python${minor}t

if [ -x "$exe" ] && "$exe" -c 'import sys; sys.exit(sys._is_gil_enabled())' 2>/dev/null; then
    echo "$exe"
    exit 0
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/python-ft.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
tarball=$work/Python-$PYTHON_VERSION.tar.xz
python3 - "$PYTHON_VERSION" "$tarball" <<'PY' >&2
import sys, urllib.request
version, dest = sys.argv[1:]
base = version.split("a")[0].split("b")[0].split("rc")[0]
url = f"https://www.python.org/ftp/python/{base}/Python-{version}.tar.xz"
print(f"downloading {url}")
urllib.request.urlretrieve(url, dest)
PY
echo "$PYTHON_SHA256  $tarball" | sha256sum -c - >&2
tar -xJf "$tarball" -C "$work"
(
    cd "$work/Python-$PYTHON_VERSION"
    ./configure --quiet --disable-gil --enable-shared --without-ensurepip \
        --prefix="$prefix" LDFLAGS="-Wl,-rpath,$prefix/lib"
    make -s -j"$(nproc)"
    make -s install
) >"$work/build.log" 2>&1 || { tail -50 "$work/build.log" >&2; exit 1; }
"$exe" -m ensurepip --default-pip >&2
"$exe" -c 'import sys, sysconfig; assert sysconfig.get_config_var("Py_GIL_DISABLED") and not sys._is_gil_enabled()' >&2
echo "$exe"
