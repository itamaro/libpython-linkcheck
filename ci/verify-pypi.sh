#!/bin/sh
# Post-release check: in a fresh container (no bind mounts, no pip cache),
# install libpython-linkcheck==$VERSION from production PyPI and run the
# README's "Try it" block, checking its key results.
#
# Usage: VERSION=0.1.0a1 ci/verify-pypi.sh   (or: make verify-pypi VERSION=...)
# Environment: PODMAN (default podman), PYTHONS (default "3.11 3.15").
set -eu

: "${VERSION:?set VERSION, e.g. VERSION=0.1.0a1}"
repo=$(cd "$(dirname "$0")/.." && pwd)
podman=${PODMAN:-podman}
pythons=${PYTHONS:-3.11 3.15}

work=$(mktemp -d "${TMPDIR:-/tmp}/linkcheck-verify.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM

# Extract the demo block that tests/test_readme.py also runs.
python3 - "$repo/README.md" > "$work/demo.sh" <<'EOF'
import re, sys
text = open(sys.argv[1]).read()
start = text.index("<!-- readme-demo")
print(re.compile(r"^```[a-z]*\n(.*?)^```$", re.M | re.S).search(text, start).group(1), end="")
EOF

for v in $pythons; do
    image=docker.io/library/python:$v-trixie
    echo "=== $image: libpython-linkcheck==$VERSION from PyPI"
    # shellcheck disable=SC2016  # expanded inside the container
    "$podman" run --rm -i --pull=newer -e VERSION="$VERSION" "$image" sh -c '
        set -e
        pip install -q --no-cache-dir --root-user-action=ignore \
            "libpython-linkcheck==$VERSION"
        python -c "import libpython_linkcheck as m; assert m.__version__ == \"$VERSION\", m.__version__"
        cd / && sh -e -s > /tmp/out 2>&1 || { cat /tmp/out; exit 1; }
        cat /tmp/out
        grep -q "^<string>:1: LibpythonLinkWarning: extension module .linked. links directly to libpython: " /tmp/out
        grep -q "^loaded <module .linked. from " /tmp/out
        grep -q "^libpython_linkcheck.LibpythonLinkWarning: extension module .linked. " /tmp/out
        test "$(grep -c "^exit status 1$" /tmp/out)" = 2
        grep -q "^linked\..*\.so: DT_NEEDED libpython" /tmp/out
        echo "verify OK: $(python -VV)"
    ' < "$work/demo.sh"
done
