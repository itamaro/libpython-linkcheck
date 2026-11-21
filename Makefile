# Local developer entry points. See AGENTS.md for when to run each target.

PYTHON ?= python3
PODMAN ?= podman
# Oldest and newest supported CPython; CI also runs everything in between.
LINUX_PYTHONS ?= 3.11 3.15
LINUX_IMAGE ?= docker.io/library/python
LINUX_VARIANT ?= trixie
# Optional: a wheel or sdist (relative to the repo root) to test instead of
# the source tree, e.g. `make test-linux PACKAGE=dist/foo.whl`.
PACKAGE ?=
RUFF ?= uv run --isolated --only-group lint ruff

.PHONY: help check lint format test test-linux dist clean

help:
	@echo "make lint        Ruff lint + format check"
	@echo "make format      Apply Ruff formatting and safe fixes"
	@echo "make test        Run the test suite with \$$PYTHON on this machine"
	@echo "make test-linux  Run the required Linux suite in Podman ($(LINUX_PYTHONS))"
	@echo "make dist        Build sdist + wheel, twine check, smoke-test both"
	@echo "make check       lint + test + test-linux + dist"

check: lint test test-linux dist

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) check --fix .
	$(RUFF) format .

test:
	PYTHON=$(PYTHON) PACKAGE=$(PACKAGE) sh ci/run-tests.sh

test-linux:
	@set -e; for v in $(LINUX_PYTHONS); do \
	    echo "=== Linux tests: $(LINUX_IMAGE):$$v-$(LINUX_VARIANT) ==="; \
	    $(PODMAN) run --rm --pull=missing \
	        -e LINKCHECK_REQUIRE_LINUX=1 \
	        -e PACKAGE=$(if $(PACKAGE),/src/$(PACKAGE)) \
	        -v "$(CURDIR)":/src:ro \
	        -v linkcheck-pip-cache:/root/.cache/pip \
	        $(LINUX_IMAGE):$$v-$(LINUX_VARIANT) sh /src/ci/run-tests.sh; \
	done

dist:
	PYTHON=$(PYTHON) sh ci/build-dist.sh

clean:
	rm -rf build dist src/*.egg-info .pytest_cache .ruff_cache
