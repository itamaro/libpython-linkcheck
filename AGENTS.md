# AGENTS.md

Canonical guide for coding agents (and humans) working on this repository.
`CLAUDE.md` is a symlink to this file; edit `AGENTS.md` only.

Keep this guide current: any commit that changes a workflow documented here
(commands, CI, release steps, policies) updates this file in the same commit.

## Project

- Distribution name: `libpython-linkcheck`. Import name: `libpython_linkcheck`.
- Goal: warn when a Python extension module about to be imported has a
  `DT_NEEDED` entry naming libpython (extensions should not link libpython
  on Linux; the interpreter provides those symbols).
- Layout: `src/libpython_linkcheck/` (package), `src/csrc/` (C sources,
  shipped in the sdist only), `tests/` (pytest), `autoenable/` (the opt-in
  `libpython-linkcheck-autoenable` distribution: a `.pth` + `.start` pair;
  built and checked by `make dist`, never published by the release workflow;
  its version is kept equal to `_version.py`),
  `ci/` (scripts shared by `make` and GitHub Actions), `.github/workflows/`.
- Two implementations of the same behavior:
  - C (`src/csrc/`): `linkcheck_elf.[ch]` is plain
    C99 + POSIX (no `Python.h`) so embedders can compile it;
    `_nativemodule.c` is the `libpython_linkcheck._native` extension.
    Built by `setup.py` on POSIX unless `LIBPYTHON_LINKCHECK_PURE=1`.
  - Pure Python (`_elf.py`, `_hook.py`): the fallback when `_native` is not
    built (the `py3-none-any` wheel) and the oracle for differential tests.
  `linkcheck_hook.[ch]` is the audit hook in C, shared by `_native` (the hook
  `enable()` installs) and the embedder entry point declared in
  `libpython_linkcheck.h`. That entry point (`LibpythonLinkcheck_Install()`,
  which calls `PySys_AddAuditHook()`) lives in `linkcheck_embed.c`, which only
  embedders compile; `_native` must not link it.
  Any behavior change must be made in both; `tests/test_native.py` compares
  the readers on a fuzzed corpus, in-process and in an ASan/UBSan-built
  harness, and the subprocess behavior tests run once per implementation
  (`LIBPYTHON_LINKCHECK_IMPLEMENTATION=python` forces the pure one).
- C style: `.clang-format` (checked by `make lint`). Test builds compile the
  C code with `-Wall -Wextra -Wshadow -Wstrict-prototypes -Werror`.
- Supported: CPython 3.12 (oldest) through 3.15 (newest), Linux/ELF.
  Tests must cover the oldest and newest supported versions.
- License: MIT (`LICENSE`). Build backend: setuptools (PEP 517, `pyproject.toml`).
- The version lives in `src/libpython_linkcheck/_version.py`. Between
  releases it is `<next>.dev0`.

## Branch and commit policy

- Work directly on `main`. Do not open PRs for your own changes.
- Make small, self-contained commits. Each commit must pass the checks
  relevant to it (see below) *on the exact tree being committed* before you
  commit. Fix failures first; never commit known-broken code.
- Push each tested commit to `origin/main` (`git push origin main`).
  Never force-push `main` and never rewrite pushed history.
- After pushing, watch CI for that commit (see "CI expectations") and fix
  any regression with a new commit.
- Preserve existing work: check `git status` before starting and do not
  discard uncommitted changes you did not make.
- Commit messages: short imperative summary line, then a body explaining
  why when it is not obvious.

## One-time setup (macOS development machine)

- Install [uv](https://docs.astral.sh/uv/) (used by `make lint`/`make format`
  to run the pinned Ruff) and Podman.
- Podman needs a running machine; the default rootless machine is enough:

  ```sh
  podman machine init      # once
  podman machine start     # after each reboot
  ```

  `make test-linux` bind-mounts the checkout read-only, so the checkout must
  be under a path the Podman machine shares (the default shares `/Users`).
  Images (`docker.io/library/python:<ver>-trixie`) are pulled on first use,
  and a named volume `linkcheck-pip-cache` is created to cache pip downloads.
- Nothing else is needed on the host: compilers, `readelf`, and Python
  headers come from the container image.

## Local checks

All targets work from a fresh checkout. Every target exits non-zero on failure.

| Command | What it does |
| --- | --- |
| `make lint` | `ruff check`, `ruff format --check`, `clang-format --dry-run --Werror` on all C sources, and `zizmor --offline` on `.github/workflows` (versions pinned in the `lint` group of `pyproject.toml`) |
| `make format` | Apply Ruff fixes and formatting |
| `make test` | Native run on this machine: fresh venv, install the package, pytest. `PYTHON=python3.15 make test` to pick an interpreter. Linux-only tests skip on macOS. |
| `make test-linux` | **The required Linux suite.** Runs `ci/run-tests.sh` inside `python:<ver>-trixie` containers for the oldest and newest supported Python (`LINUX_PYTHONS="3.12 3.15"`). Builds the C fixtures inside the container. Sets `LINKCHECK_REQUIRE_LINUX=1`, which turns any skipped test into a failure. |
| `make test-linux LINUX_PYTHONS=3.13` | Same, for specific versions. |
| `make test-linux PACKAGE=dist/<file>` | Run the Linux suite against a built wheel or sdist instead of the source tree. |
| `make test-linux-uv-python` | The Linux suite on uv-managed CPython builds from python-build-standalone (`UV_PYTHONS="3.12.16 3.15.2"`), whose executable is linked statically although a shared libpython ships alongside, in a relocatable prefix. `ci/test-uv-python.sh` installs the pinned uv (which pins and verifies the downloads) in a `python:3.15-trixie` container and runs `ci/run-tests.sh` with that interpreter. |
| `make test-linux-freethreaded` | The Linux suite on a free-threaded CPython (`FT_PYTHON=3.15` by default; also `3.14`): `ci/test-freethreaded.sh` builds the image's exact CPython release with `--disable-gil --enable-shared` from the python.org tarball, verified against the image's `PYTHON_SHA256` (`ci/build-freethreaded.sh`), caches it in the `linkcheck-python-ft` volume (the first run takes about 10 minutes), and checks that importing the package keeps the GIL disabled. Accepts `PACKAGE` like `test-linux`. |
| `make test-linux PACKAGE=wheelhouse` | Same, against a directory of wheels: pip installs the one matching each container's interpreter (`--no-index --only-binary`). |
| `make bench-linux` | The audit-hook overhead benchmark (`ci/bench_hook.py`, via `ci/run-tests.sh` with `LINKCHECK_BENCH=1`) in `python:<ver>-trixie` containers (`BENCH_PYTHONS="3.12 3.15"`): ns per unrelated audit event, per filename-less `import` event, and per clean extension re-import, with no hook, the pure-Python hook, and the C hook. Accepts `PACKAGE` like `test-linux`. Run it before and after changes to the hook's hot path and report both. |
| `make dist` | `ci/build-dist.sh`: build the sdist, then the pure-Python wheel from the sdist (`LIBPYTHON_LINKCHECK_PURE=1`), `twine check --strict`, `ci/check_dist.py` content/metadata checks, and install-and-import smoke tests of each artifact from outside the checkout (installing the sdist compiles the C implementation). Also builds the `autoenable/` wheel into a scratch directory, checks it (`ci/check_autoenable.py`), and checks that installing it enables the hook at startup. |
| `make wheels` | Native wheels for the host architecture into `wheelhouse/`: cibuildwheel (pinned in the `wheels` dependency group, configured in `[tool.cibuildwheel]`) in Podman builds each CPython in `manylinux_2_28`, runs `auditwheel show`/`repair --only-plat --plat manylinux_2_28_<arch>`, and runs `ci/wheel_smoke.py` (native implementation, `_native` has no libpython `DT_NEEDED`, the GIL stays disabled on free-threaded builds, the hook blocks a synthetic linked object). On an Apple silicon Mac this builds aarch64; CI builds x86_64 too. |
| `make check` | `lint` + `test` + `test-linux` + `dist`. |
| `make verify-pypi VERSION=<v>` | Post-release: install `<v>` from production PyPI in fresh containers and run the README demo. |

`ci/run-tests.sh` is the single test entry point for `make` and GitHub
Actions. It copies the checkout to a scratch directory, installs the package
(non-editable) into a fresh venv, and runs pytest against the *installed* copy.
It adds `-Werror` to `CFLAGS` and sets `LINKCHECK_REQUIRE_NATIVE=1` (the C
implementation must be importable and is tested) unless `PACKAGE` is the
pure-Python wheel.

### Which checks to run before committing

- Always: `make lint`.
- Python code or tests: `make test` and `make test-linux`.
- The audit hook, ELF inspection, native code, the fixtures, or anything
  about how extensions load: `make test-linux` is mandatory, and
  `make test-linux-freethreaded` for C or threading changes, and
  `make test-linux-uv-python` for changes to fixtures, the launcher, or
  anything that depends on how the interpreter is built or installed. A skipped Linux
  test on macOS does not validate these changes.
- Packaging (`pyproject.toml`, `MANIFEST.in`, `ci/*`, workflows): `make lint`
  (zizmor checks the workflows), `make dist`,
  `make wheels` plus `make test-linux PACKAGE=wheelhouse` when the native
  build or wheel configuration changes,
  and `make test-linux`.
- Docs only: `make lint`. If README changes, also `make dist` (it is the
  PyPI long description checked by `twine check --strict`) and
  `make test-linux`: `tests/test_readme.py` runs the README's "Try it" block
  and compares the result with its "Expected output" block, so keep them in sync.
- Release commits: everything in "Release procedure" below.

## CI expectations

`.github/workflows/ci.yml` runs on every push to `main` and every pull request:

- `lint`: `make lint` (Ruff, clang-format, zizmor).
- `linux`: the required Linux suite (`ci/run-tests.sh`,
  `LINKCHECK_REQUIRE_LINUX=1`) in `python:<ver>-trixie` containers for
  3.12–3.15 on x86_64, plus 3.12 and 3.15 on aarch64.
- `uv-python`: the same suite on uv-managed (python-build-standalone)
  CPython 3.12.16 and 3.15.2 (x86_64).
- `freethreaded`: the same suite on free-threaded 3.14t and 3.15t
  (`ci/test-freethreaded.sh`; the source build is cached with `actions/cache`).
- `macos`: native test run on 3.12 and 3.15.
- `dist` (reusable `.github/workflows/dist.yml`), which builds every
  distribution once:
  - `build`: the sdist and pure-Python wheel (`ci/build-dist.sh`);
  - `wheels`: native manylinux_2_28 wheels for x86_64 and aarch64
    (cibuildwheel; same configuration as `make wheels`);
  - `check`: `twine check --strict` and `ci/check_dist.py --native-wheels`
    on all files together (exactly one native wheel per CPython build and
    architecture in `[tool.cibuildwheel]`, one pure wheel, one sdist, no
    libpython `DT_NEEDED` in any shipped object), then upload them as the
    `dist` artifact;
  - `test`: the Linux suite against those exact files: the native wheel on
    3.12–3.15 × x86_64/aarch64, and the pure wheel and the sdist on 3.12 and
    3.15;
  - `test-freethreaded`: the cp314t and cp315t native wheels on free-threaded
    builds (x86_64; aarch64 is covered locally by `make wheels` +
    `make test-linux-freethreaded PACKAGE=wheelhouse`).

All jobs must be green. After pushing, check the run for your commit:

```sh
gh run list --branch main --limit 5
gh run watch <run-id> --exit-status
```

Workflow conventions: actions are pinned to full commit SHAs with a version
comment; same-repository workflows are referenced as `$/...`, not `./...`;
every job has a `name:` (equal to its id unless it is a matrix job);
`${{ }}` expressions reach `run:` scripts only through `env:`;
every granted permission carries a comment saying why; the default token permission is `contents: read`; only the release
`publish` job gets `id-token: write`; checkouts use
`persist-credentials: false`.

## Release procedure

**Publishing requires explicit authorization from the maintainer for that
specific version.** Authorization for one release is not standing permission
for later ones. Without it, prepare the release commit and stop for review.

Publishing uses PyPI Trusted Publishing: PyPI project `libpython-linkcheck`,
owner `itamaro`, repository `libpython-linkcheck`, workflow `release.yml`,
GitHub environment `pypi`. No API tokens are stored anywhere.

1. Release commit: set `__version__` in `src/libpython_linkcheck/_version.py`
   to the release version (e.g. `0.1.0a1`), set the same version (and the
   pinned dependency) in `autoenable/pyproject.toml`, and add the release
   notes to `CHANGELOG.md`.
2. On that exact tree, run locally:
   ```sh
   make check
   make test-linux PACKAGE=dist/libpython_linkcheck-<version>-py3-none-any.whl
   make test-linux PACKAGE=dist/libpython_linkcheck-<version>.tar.gz
   make wheels && make test-linux PACKAGE=wheelhouse LINUX_PYTHONS="3.12 3.13 3.14 3.15"
   make test-linux-freethreaded PACKAGE=wheelhouse FT_PYTHON=3.14
   make test-linux-freethreaded PACKAGE=wheelhouse FT_PYTHON=3.15
   ```
   (`make check` runs `make dist`, which builds and smoke-tests both artifacts.)
3. Commit, push to `main`, and wait until CI for that commit is green.
4. Tag that commit and push the tag:
   ```sh
   git tag -a v<version> -m "libpython-linkcheck <version>" <sha>
   git push origin v<version>
   ```
5. `.github/workflows/release.yml` checks the tag equals `v` + `__version__`
   and is on `main`, builds and tests the artifacts once (`dist.yml`), then the
   `publish` job (environment `pypi`) uploads those exact files. Follow it with
   `gh run watch`.
6. Confirm PyPI serves exactly the workflow's artifact (compare sha256 of
   `gh run download <run-id> -n dist` with
   `https://pypi.org/pypi/libpython-linkcheck/<version>/json`), then verify
   from clean containers: `make verify-pypi VERSION=<version>` installs the
   release from production PyPI (no mounts, no cache) on 3.12 and 3.15 and
   runs the README "Try it" block.
7. Post-release commit: bump `_version.py` and `autoenable/pyproject.toml`
   to the next `.dev0` version and open a new "Unreleased" section in
   `CHANGELOG.md`.

Never re-tag or delete a published version; PyPI does not allow re-uploading
a version. Fix forward with a new version.
