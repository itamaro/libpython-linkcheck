# Changelog

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
