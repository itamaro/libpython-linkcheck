# libpython-linkcheck-autoenable

Installing this distribution enables
[libpython-linkcheck](https://pypi.org/project/libpython-linkcheck/) in every
interpreter that processes the `site-packages` directory it is installed in:
at startup, `libpython_linkcheck.enable()` runs before `sitecustomize` and
any user code.

It installs two files at the root of `site-packages`:

- `libpython_linkcheck_autoenable.pth`, whose `import` line runs
  `libpython_linkcheck._autoenable()` on Python 3.12–3.14;
- `libpython_linkcheck_autoenable.start`, a [PEP 829](https://peps.python.org/pep-0829/)
  entry point (`libpython_linkcheck:_autoenable`) for Python 3.15 and later.
  Its presence disables the `.pth` file's import line, so it runs once.

`_autoenable()` is `enable()`, except that a dropped
`-W error::libpython_linkcheck.LibpythonLinkWarning` keeps the precedence of
its position among the `-W` options (see "Controlling the warning" in the
main README). Its version must equal the package's, which the dependency pins.

It does nothing under `-S` (no `site`), and it cannot inspect extension
modules imported by `.pth` files that are processed before it.
