# libpython-linkcheck-autoenable

Opt-in companion of
[libpython-linkcheck](https://pypi.org/project/libpython-linkcheck/), which
warns when an imported Python extension module links directly to libpython.
Installing it enables the check in every interpreter that processes the
`site-packages` directory it is installed in: at startup,
`libpython_linkcheck.enable()` runs before `sitecustomize` and any user code.

```sh
pip install libpython-linkcheck-autoenable
```

It depends on the exact matching version of `libpython-linkcheck`, released
together with it, so pip installs that too. Installing `libpython-linkcheck`
alone never activates anything; to stop activating it, uninstall only this
companion (`pip uninstall libpython-linkcheck-autoenable`).

It installs two files at the root of `site-packages`:

- `libpython_linkcheck_autoenable.pth`, whose `import` line runs
  `libpython_linkcheck._autoenable()` on Python 3.12–3.14;
- `libpython_linkcheck_autoenable.start`, a [PEP 829](https://peps.python.org/pep-0829/)
  entry point (`libpython_linkcheck:_autoenable`) for Python 3.15 and later.
  Its presence disables the `.pth` file's import line, so it runs once.

`_autoenable()` is `enable()`, except that a dropped
`-W error::libpython_linkcheck.LibpythonLinkWarning` keeps the precedence of
its position among the `-W` options (see "Controlling the warning" in the
main README), as long as no `.pth` or `.start` file processed before it
changed the warning filters.

It does nothing under `-S` (no `site`), and it cannot inspect extension
modules imported by `.pth` files that are processed before it.
