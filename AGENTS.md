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
  `libpython-linkcheck-autoenable` companion project: a `.pth` + `.start`
  pair, built and checked by `make dist` into `autoenable-dist/`; its
  version, and its exact dependency on the core, are kept equal to
  `_version.py`),
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
- Wheel matrix (x86_64 and aarch64, `manylinux_2_28`; `setup.py` picks the
  target from the build interpreter, `[tool.cibuildwheel]` builds one per
  row, `ci/check_dist.py` and `ci/check_abi.py` enforce it):

  | Wheel tag | Built on | C target | Extension file | Serves |
  | --- | --- | --- | --- | --- |
  | `cp312-abi3` | 3.12 | Limited API, `Py_LIMITED_API=0x030C0000`, `PyInit__native` | `_native.abi3.so` | GIL-enabled 3.12+ (pip prefers the 3.15 wheel on 3.15+) |
  | `cp314-cp314t` | 3.14t | full API, `PyInit__native` | `_native.cpython-314t-<arch>-linux-gnu.so` | free-threaded 3.14 |
  | `cp315-abi3.abi3t` | 3.15t | abi3t, `Py_TARGET_ABI3T=0x030F0000`, `PyModExport__native` (PEP 793) | `_native.abi3t-<arch>-linux-gnu.so` | GIL-enabled and free-threaded 3.15+ |
  | `py3-none-any` | any | none (pure Python) | none | everything else |

  The C code chooses APIs and slots with `LPC_TARGET_API` (the Limited API
  floor, else the headers' version), never the headers' version alone, so
  newer headers cannot add newer dependencies to a Stable ABI build.
  Building the 3.15 wheel needs setuptools >= 84.2.1 (`build-system.requires`).
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
| `make dist` | `ci/build-dist.sh`: build the sdist, then the pure-Python wheel from the sdist (`LIBPYTHON_LINKCHECK_PURE=1`), `twine check --strict`, `ci/check_dist.py` content/metadata checks, and install-and-import smoke tests of each artifact from outside the checkout (installing the sdist compiles the C implementation). Also builds the `autoenable/` companion's sdist, and its universal wheel from that sdist, into `autoenable-dist/`, runs `twine check --strict` and `ci/check_autoenable.py` on them (exact contents, version and dependency pin), and checks that installing the wheel enables the hook at startup. |
| `make wheels` | Native wheels for the host architecture into `wheelhouse/`: cibuildwheel (pinned in the `wheels` dependency group, configured in `[tool.cibuildwheel]`) in Podman builds the three wheels of the matrix in `manylinux_2_28`, runs `auditwheel show`/`repair --only-plat --plat manylinux_2_28_<arch>`, audits each with `ci/check_abi.py` (every imported CPython symbol is in the Stable ABI of the wheel's Python tag, per CPython's pinned `Misc/stable_abi.toml`; no `PySys_AddAuditHook`; the right entry point; abi3audit `--strict` on `cp312-abi3`), and runs `ci/wheel_smoke.py` (native implementation, `_native` has no libpython `DT_NEEDED`, the GIL stays disabled on free-threaded builds, the hook blocks a synthetic linked object). On an Apple silicon Mac this builds aarch64; CI builds x86_64 too. |
| `make check` | `lint` + `test` + `test-linux` + `dist`. |
| `make test-autoenable-install` | The companion as users install it (`ci/test-autoenable-install.sh`): in fresh `python:<ver>-trixie` containers (`AUTOENABLE_PYTHONS="3.12 3.15t"`; `t` uses the free-threaded build of `make test-linux-freethreaded`), a fresh venv installs only `libpython-linkcheck-autoenable` by project name from `wheelhouse/`, `dist/` and `autoenable-dist/` (`--no-index`), so pip must resolve the pinned core to the matrix wheel; then `ci/autoenable_install_check.py` checks that a fresh launch has the native hook enabled at startup (and that it blocks a synthetic linked extension), that `-S` skips activation, and that after uninstalling only the companion the core is still installed and the next launch has no hook. Run `make wheels dist` first. |
| `make verify-pypi VERSION=<v>` | Post-release: from production PyPI with no pip cache, install `<v>` in fresh containers and run the README demo (`LINUX_PYTHONS`), then run the companion install test above against `libpython-linkcheck-autoenable==<v>` (`AUTOENABLE_PYTHONS`). |

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
  `make wheels dist test-autoenable-install` when the companion or how the
  distributions install changes, and `make test-linux`.
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
  - `build`: the sdist and pure-Python wheel, and the companion's sdist and
    wheel, which it uploads separately as the `autoenable` artifact
    (`ci/build-dist.sh`);
  - `wheels`: native manylinux_2_28 wheels for x86_64 and aarch64
    (cibuildwheel; same configuration as `make wheels`);
  - `check`: `twine check --strict`, `ci/check_dist.py --native-wheels`
    on all files together (exactly the wheel matrix above for both
    architectures, with its WHEEL tags, `Root-Is-Purelib: false` and
    extension file names, one pure wheel, one sdist, no libpython
    `DT_NEEDED` in any shipped object), and `ci/check_abi.py` on every
    native wheel, then upload them as the `dist` artifact;
  - `abi3-new-headers`: builds the abi3 wheel from the sdist with CPython
    3.15's headers and checks it with `ci/check_abi.py` (the 3.12 floor must
    hold whatever headers compile it);
  - `test`: the Linux suite against those exact files: the same
    `cp312-abi3` wheel on 3.12, 3.13, 3.14 and 3.15 × x86_64/aarch64, the
    `cp315-abi3.abi3t` wheel on 3.15 × both, the whole set installed by
    project name on 3.12, 3.14 and 3.15 (x86_64) and 3.15 (aarch64), the
    `abi3-new-headers` wheel on 3.12, and the pure wheel and the sdist on
    3.12 and 3.15;
  - `test-freethreaded`: on free-threaded 3.14t and 3.15t, the
    `cp314-cp314t` and `cp315-abi3.abi3t` wheels as files on x86_64 and
    aarch64, and the set by project name on x86_64;
  - `test-autoenable`: `ci/test-autoenable-install.sh` (see
    `make test-autoenable-install`) on 3.12 and free-threaded 3.15t
    (x86_64), installing only the companion by project name from the `dist`
    and `autoenable` artifacts.

  `ci/run-tests.sh` fails unless the installed WHEEL tags are the expected
  ones: a wheel file's own; for a directory, the matrix wheel for that
  interpreter; for a source tree or sdist, the target `setup.py` builds
  (`cp312-abi3` on every GIL-enabled CPython). The suite covers the
  artifact behaviors end to end on each of these: warning attribution to
  the importing line, an error filter aborting the import before the ELF
  constructor runs, the embedded launcher under `-I -S`, `_native` in an
  own-GIL subinterpreter, the GIL staying disabled on free-threaded builds,
  and one category class under concurrent first use.

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
`publish` and `publish-autoenable` jobs get `id-token: write`; checkouts use
`persist-credentials: false`.

## Release procedure

**Publishing requires explicit authorization from the maintainer for that
specific version.** Authorization for one release is not standing permission
for later ones. Without it, prepare the release commit and stop for review.

One tag releases two PyPI projects with the same version:
`libpython-linkcheck` (the core) and `libpython-linkcheck-autoenable` (the
opt-in companion, which pins that exact core version). Both use PyPI Trusted
Publishing with the same trust: owner `itamaro`, repository
`libpython-linkcheck`, workflow `release.yml`, GitHub environment `pypi`. No
API tokens are stored anywhere.

1. Release commit: set `__version__` in `src/libpython_linkcheck/_version.py`
   to the release version (e.g. `0.1.0a1`), set the same version and the
   exact dependency pin (`libpython-linkcheck==<version>`) in
   `autoenable/pyproject.toml`, and add the release notes to `CHANGELOG.md`.
2. On that exact tree, run locally:
   ```sh
   make check
   make test-linux PACKAGE=dist/libpython_linkcheck-<version>-py3-none-any.whl
   make test-linux PACKAGE=dist/libpython_linkcheck-<version>.tar.gz
   make wheels && make test-linux PACKAGE=wheelhouse LINUX_PYTHONS="3.12 3.13 3.14 3.15"
   make test-linux PACKAGE=wheelhouse/libpython_linkcheck-<version>-cp312-abi3-manylinux_2_28_<arch>.whl LINUX_PYTHONS="3.12 3.13 3.14 3.15"
   make test-linux-freethreaded PACKAGE=wheelhouse FT_PYTHON=3.14
   make test-linux-freethreaded PACKAGE=wheelhouse FT_PYTHON=3.15
   make test-autoenable-install
   ```
   (`make check` runs `make dist`, which builds and smoke-tests the core's
   sdist and pure wheel and the companion's sdist and wheel.)
3. Commit, push to `main`, and wait until CI for that commit is green.
4. Tag that commit and push the tag:
   ```sh
   git tag -a v<version> -m "libpython-linkcheck <version>" <sha>
   git push origin v<version>
   ```
5. `.github/workflows/release.yml` checks the tag equals `v` + `__version__`
   (and the companion's version and pin), and is on `main`, builds and tests
   the artifacts once (`dist.yml`), then uploads those exact files
   (environment `pypi`): the `publish` job uploads the `dist` artifact
   (the core), then `publish-autoenable` uploads the `autoenable` artifact
   (the companion). Follow it with `gh run watch`. If the companion's upload
   fails after the core's succeeded, fix the cause (e.g. its Trusted
   Publisher) and use "Re-run failed jobs" on that run
   (`gh run rerun <run-id> --failed`): it re-runs only `publish-autoenable`,
   with the same artifact. Never re-run the whole workflow, which would
   rebuild the files.
6. Confirm PyPI serves exactly the workflow's artifacts: compare the sha256
   of `gh run download <run-id> -n dist` with
   `https://pypi.org/pypi/libpython-linkcheck/<version>/json`, and of
   `gh run download <run-id> -n autoenable` with
   `https://pypi.org/pypi/libpython-linkcheck-autoenable/<version>/json`.
   Then verify from clean containers: `make verify-pypi VERSION=<version>`
   installs the release from production PyPI (no cache) on 3.12 and 3.15
   and runs the README "Try it" block (no mounts), then installs only
   `libpython-linkcheck-autoenable==<version>` on 3.12 and 3.15t and runs the
   companion install test.
7. Post-release commit: bump `_version.py`, and the version and pin in
   `autoenable/pyproject.toml`, to the next `.dev0` version and open a new
   "Unreleased" section in `CHANGELOG.md`.

Never re-tag or delete a published version; PyPI does not allow re-uploading
a version. Fix forward with a new version.
