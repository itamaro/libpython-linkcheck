# Changelog

## Unreleased

- Tested on uv-managed CPython (python-build-standalone) 3.11, 3.12 and
  3.15, whose executable is linked statically although a shared libpython
  ships alongside.
- A `-W` / `PYTHONWARNINGS` entry naming `libpython_linkcheck.LibpythonLinkWarning`
  that CPython dropped at startup is now applied with the precedence of its
  position: later options, and filters the program installed before
  `enable()`, still override it. Previously `enable()` put it in front of
  every filter.
- `enable()` also applies such entries when it finds a hook that is already
  installed, such as one registered with `LibpythonLinkcheck_Install()`
  (once per interpreter). The README documents which filters work with
  the embedded hook alone.
- Recognize libpython copies bundled into wheels by auditwheel, such as
  `libpython3-dc2fd5ae.10.so.1.0` (needed by the extensions in the
  `cohere==2.1.0` cp310 wheel), and the unversioned `libpython.so`.
## 0.1.0a2 (2026-11-21)

Second alpha: a C implementation, native wheels, an embedding API, and opt-in
automatic activation. See the README for the exact scope.

- C implementation (`libpython_linkcheck._native`) of the `DT_NEEDED`
  reader and of the audit hook; `enable()` uses it when available. The
  pure-Python implementation remains the fallback and is tested against the
  C one (fuzzed corpus, also under ASan/UBSan).
  `LIBPYTHON_LINKCHECK_IMPLEMENTATION=python` forces the pure-Python one.
- Native `manylinux_2_28` wheels for x86_64 and aarch64 (CPython 3.11–3.15,
  plus free-threaded 3.14t and 3.15t), alongside the pure-Python wheel.
- Embedding API: `LibpythonLinkcheck_Install()` (`src/csrc/libpython_linkcheck.h`)
  registers a runtime-wide hook before Python starts. It covers every
  interpreter, needs no Python package, and works under `-I -S`.
- `LibpythonLinkWarning` is one class per interpreter, shared by every hook
  and every copy of the module. A later `enable()` detects any installed
  hook, including the embedded one, and installs nothing.
- Opt-in automatic activation: `autoenable/` builds
  `libpython-linkcheck-autoenable` (not published), a matching `.pth` file
  (3.11–3.14) and PEP 829 `.start` file (3.15+) that call `enable()` at
  startup. The README documents each activation path and what it covers.
- Newly tested: free-threaded 3.14t and 3.15t (from source and from the
  native wheels); `sitecustomize`, `usercustomize`, the `.pth` / `.start`
  pair, and all of them combined; `-I` and `-S`; subinterpreters
  (`enable()` is per interpreter, the embedded hook covers all of them);
  re-initialization after `Py_FinalizeEx()`.

## 0.1.0a1 (2026-11-21)

First alpha. Explicit activation only; see the README for the exact scope.

- `libpython_linkcheck.enable()` installs an idempotent CPython audit hook.
  Before CPython loads an extension module, the hook reads the shared
  object's own `DT_NEEDED` entries and issues `LibpythonLinkWarning` (a
  `RuntimeWarning`) if one names libpython: versioned, Stable ABI
  (`libpython3.so`), free-threaded, or ABI-flagged names. The warning
  carries `module`, `filename`, and `needed`, respects warning filters,
  and with `-Werror` stops the import before the object is loaded.
- `-W` / `PYTHONWARNINGS` entries naming `LibpythonLinkWarning`, which
  CPython drops at startup, are applied by `enable()`.
- `is_enabled()` and `libpython_dependencies(path)`.
- `python -m libpython_linkcheck FILE...` reports files that link libpython.
