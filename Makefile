# Local developer entry points. See AGENTS.md for when to run each target.

PYTHON ?= python3
PODMAN ?= podman
# Oldest and newest supported CPython; CI also runs everything in between.
LINUX_PYTHONS ?= 3.12 3.15
LINUX_IMAGE ?= docker.io/library/python
LINUX_VARIANT ?= trixie
# Optional: a wheel or sdist (relative to the repo root) to test instead of
# the source tree, e.g. `make test-linux PACKAGE=dist/foo.whl`.
PACKAGE ?=
RUFF ?= uv run --isolated --only-group lint ruff
CLANG_FORMAT ?= uv run --isolated --only-group lint clang-format
ZIZMOR ?= uv run --isolated --only-group lint zizmor
C_SOURCES = $(wildcard src/csrc/*.[ch] tests/fixtures/*.c tests/native/*.c)

.PHONY: help check lint format test test-linux test-linux-freethreaded test-linux-uv-python bench-linux dist wheels verify-pypi clean

help:
	@echo "make lint        Ruff lint + format check, clang-format check"
	@echo "make format      Apply Ruff formatting and safe fixes"
	@echo "make test        Run the test suite with \$$PYTHON on this machine"
	@echo "make test-linux  Run the required Linux suite in Podman ($(LINUX_PYTHONS))"
	@echo "make dist        Build sdist + wheel, twine check, smoke-test both"
	@echo "make check       lint + test + test-linux + dist"
	@echo "make bench-linux       audit-hook overhead benchmark in Linux containers (BENCH_PYTHONS)"
	@echo "make test-linux-uv-python  Linux suite on uv-managed (python-build-standalone) CPythons (UV_PYTHONS)"
	@echo "make test-linux-freethreaded  Linux suite on a free-threaded CPython built from source (FT_PYTHON=3.15)"
	@echo "make wheels      Build + repair native manylinux wheels for this machine's arch (cibuildwheel + Podman)"
	@echo "make test-autoenable-install  Install the built companion by name in fresh 3.12 / 3.15t containers (after make wheels dist)"
	@echo "make verify-pypi VERSION=x  Install x from PyPI in fresh containers: README demo + companion install test"

check: lint test test-linux dist

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(CLANG_FORMAT) --dry-run --Werror $(C_SOURCES)
	$(ZIZMOR) --offline .github/workflows

format:
	$(RUFF) check --fix .
	$(RUFF) format .
	$(CLANG_FORMAT) -i $(C_SOURCES)

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

# The audit-hook overhead benchmark (ci/bench_hook.py), same install as test-linux.
BENCH_PYTHONS ?= 3.12 3.15
bench-linux:
	@set -e; for v in $(BENCH_PYTHONS); do \
	    echo "=== Hook benchmark: $(LINUX_IMAGE):$$v-$(LINUX_VARIANT) ==="; \
	    $(PODMAN) run --rm --pull=missing -e LINKCHECK_BENCH=1 \
	        -e PACKAGE=$(if $(PACKAGE),/src/$(PACKAGE)) \
	        -v "$(CURDIR)":/src:ro \
	        -v linkcheck-pip-cache:/root/.cache/pip \
	        $(LINUX_IMAGE):$$v-$(LINUX_VARIANT) sh /src/ci/run-tests.sh; \
	done

dist:
	PYTHON=$(PYTHON) sh ci/build-dist.sh

# The Linux suite on a free-threaded CPython of the image's exact release,
# built from verified source once and cached in the linkcheck-python-ft volume.
FT_PYTHON ?= 3.15
test-linux-freethreaded:
	$(PODMAN) run --rm --pull=missing \
		-e LINKCHECK_REQUIRE_LINUX=1 -e PACKAGE=$(if $(PACKAGE),/src/$(PACKAGE)) \
		-v "$(CURDIR)":/src:ro \
		-v linkcheck-python-ft:/opt/python-ft \
		-v linkcheck-pip-cache:/root/.cache/pip \
		$(LINUX_IMAGE):$(FT_PYTHON)-$(LINUX_VARIANT) \
		sh /src/ci/test-freethreaded.sh

# The Linux suite on uv-managed CPython builds (python-build-standalone:
# statically linked executable, shipped shared libpython, relocatable prefix).
# Keep UV_PYTHONS in sync with the uv-python job in .github/workflows/ci.yml.
UV_PYTHONS ?= 3.12.16 3.15.2
test-linux-uv-python:
	@set -e; for v in $(UV_PYTHONS); do \
	    echo "=== Linux tests: uv-managed CPython $$v ==="; \
	    $(PODMAN) run --rm --pull=missing \
	        -e LINKCHECK_REQUIRE_LINUX=1 -e UV_PYTHON=$$v \
	        -e PACKAGE=$(if $(PACKAGE),/src/$(PACKAGE)) \
	        -v "$(CURDIR)":/src:ro \
	        -v linkcheck-pip-cache:/root/.cache/pip \
	        -v linkcheck-uv-cache:/root/.cache/uv \
	        $(LINUX_IMAGE):3.15-$(LINUX_VARIANT) sh /src/ci/test-uv-python.sh; \
	done

# Native wheels for the host architecture into wheelhouse/ (CI builds both).
CIBUILDWHEEL ?= uv run --isolated --only-group wheels cibuildwheel
wheels:
	CIBW_CONTAINER_ENGINE=$(PODMAN) $(CIBUILDWHEEL) --platform linux --output-dir wheelhouse

# Install the built autoenable companion by project name in a fresh venv per
# interpreter ("t" = free-threaded, built from source like
# test-linux-freethreaded), from the local wheelhouse/, dist/ and
# autoenable-dist/ only (run `make wheels dist` first). Keep
# AUTOENABLE_PYTHONS in sync with the test-autoenable job in dist.yml.
AUTOENABLE_PYTHONS ?= 3.12 3.15t
AUTOENABLE_FIND_LINKS ?= wheelhouse dist autoenable-dist
test-autoenable-install:
	@set -e; for v in $(AUTOENABLE_PYTHONS); do \
	    case $$v in *t) ft=1; image=$${v%t} ;; *) ft=0; image=$$v ;; esac; \
	    $(PODMAN) run --rm --pull=missing -e FREETHREADED=$$ft \
	        -e FIND_LINKS="$(foreach d,$(AUTOENABLE_FIND_LINKS),/src/$(d))" \
	        -v "$(CURDIR)":/src:ro \
	        -v linkcheck-python-ft:/opt/python-ft \
	        $(LINUX_IMAGE):$$image-$(LINUX_VARIANT) sh /src/ci/test-autoenable-install.sh; \
	done

verify-pypi:
	VERSION=$(VERSION) PODMAN=$(PODMAN) PYTHONS="$(LINUX_PYTHONS)" \
		AUTOENABLE_PYTHONS="$(AUTOENABLE_PYTHONS)" sh ci/verify-pypi.sh

clean:
	rm -rf build dist autoenable-dist wheelhouse src/*.egg-info .pytest_cache .ruff_cache
