# libpython-linkcheck-autoenable

Installing this distribution enables
[libpython-linkcheck](https://pypi.org/project/libpython-linkcheck/) in every
interpreter that processes the `site-packages` directory it is installed in:
at startup, `libpython_linkcheck.enable()` runs before any user code.

It installs two files at the root of `site-packages`:

- `libpython_linkcheck_autoenable.pth`, whose `import` line runs `enable()`
  on Python 3.11–3.14;
- `libpython_linkcheck_autoenable.start`, a [PEP 829](https://peps.python.org/pep-0829/)
  entry point (`libpython_linkcheck:enable`) for Python 3.15 and later. Its
  presence disables the `.pth` file's import line, so `enable()` runs once.

It does nothing under `-S` (no `site`), and it cannot inspect extension
modules imported by `.pth` files that are processed before it.
