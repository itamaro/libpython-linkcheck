#!/bin/sh
# Run ci/run-tests.sh on a free-threaded CPython built by
# ci/build-freethreaded.sh (inside a docker.io/library/python image).
# Used by `make test-linux-freethreaded` and the CI `freethreaded` job.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
PYTHON=$(sh "$here/build-freethreaded.sh")
export PYTHON
exec sh "$here/run-tests.sh" "$@"
