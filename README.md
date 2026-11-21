# libpython-linkcheck

Warn when an imported Python extension directly links to libpython on Linux.

On Linux, CPython extension modules should **not** link against libpython:
the interpreter that loads them already provides every `Py*` symbol. An
extension with `libpython3.X.so.1.0` in its `DT_NEEDED` entries requires that
exact library at load time. Under an interpreter without a shared libpython (a
statically linked build, such as Debian's and Ubuntu's `/usr/bin/python3`), it
either fails with "cannot open shared object file" or loads a second, separate
copy of the runtime. The manylinux policies forbid such links for these reasons.

`libpython-linkcheck` installs a CPython audit hook that inspects each
extension module's shared object right **before** CPython loads it, and issues
a `LibpythonLinkWarning` if the object's own `DT_NEEDED` entries name libpython.

## Install

```sh
pip install libpython-linkcheck
```

The import name is `libpython_linkcheck`. It is pure Python, with no dependencies.

## Usage

```python
import libpython_linkcheck

libpython_linkcheck.enable()  # once, as early as possible

import some_extension  # warns if some_extension's .so has DT_NEEDED libpython
```

The warning names the module, the file, and the matching dependency, and
points at the line that did the import:

```text
app.py:5: LibpythonLinkWarning: extension module 'some_extension' links directly to libpython: /venv/lib/python3.15/site-packages/some_extension.cpython-315-x86_64-linux-gnu.so has DT_NEEDED libpython3.15.so.1.0
```

`enable()` returns `True` if it installed the hook and `False` if a hook was
already active in this interpreter. Calling it again is harmless and never
produces duplicate warnings. `is_enabled()` reports whether the hook is
active. Audit hooks cannot be removed, so the hook stays active until the
interpreter exits.

### Controlling the warning

`LibpythonLinkWarning` is a `RuntimeWarning` subclass, and all the normal
warning filters apply. With an `error` filter, the import raises
`LibpythonLinkWarning` before the shared object is loaded, so none of its code
(not even ELF constructors) runs.

In code (after `import libpython_linkcheck`):

```python
import warnings
from libpython_linkcheck import LibpythonLinkWarning

# Fail such imports instead of warning:
warnings.filterwarnings("error", category=LibpythonLinkWarning)
# Silence one known extension (the message starts with "extension module '<name>'"):
warnings.filterwarnings(
    "ignore", message=r"extension module 'legacy\._speedups'", category=LibpythonLinkWarning
)
```

The warning instance carries `.module` (the fully qualified module name),
`.filename` (the shared object), and `.needed` (a tuple of the matching
`DT_NEEDED` entries).

On the command line:

| Option | Effect |
| --- | --- |
| `python -Werror ...` | every warning, including this one, is an error |
| `python -W error::RuntimeWarning ...` | runtime warnings, including this one, are errors |
| `python -W "error:extension module 'foo._ext'" ...` | this warning is an error for one module (message prefix, matched literally) |
| `python -W error::libpython_linkcheck.LibpythonLinkWarning ...` | this warning is an error (see the note below) |
| `PYTHONWARNINGS=...` | same as `-W` |

**Note:** CPython resolves the category of a `-W` or `PYTHONWARNINGS` entry
during startup, before site-packages is on `sys.path`. For a normally
installed package that fails, and CPython itself prints
`Invalid -W option ignored: invalid module name: 'libpython_linkcheck'`.
When `enable()` installs the hook, it applies those dropped entries, in their
original order, so the filter does take effect for every import after
`enable()`. These entries then take precedence over filters added before
`enable()` was called. The other forms in the table work without this step.

### Checking files without importing them

```sh
python -m libpython_linkcheck build/lib*/mypkg/*.so
```

prints `FILE: DT_NEEDED libpython...` for each offending file. The exit status
is 0 if no file links libpython, 1 if any does, and 2 if a file could not be
read or is not ELF. From Python, `libpython_linkcheck.libpython_dependencies(path)`
returns the matching entries as a list.

## Try it

This builds an extension that links libpython and imports it with the hook
enabled. Copy and paste into a shell in a `python:3.15` container
(`podman run --rm -it docker.io/library/python:3.15-trixie bash`, or use `docker`):

<!-- readme-demo: the block below is executed by tests/test_readme.py -->
```sh
pip install libpython-linkcheck
mkdir demo && cd demo
cat > linked.c <<'EOF'
#include <Python.h>
static struct PyModuleDef def = {PyModuleDef_HEAD_INIT, "linked", NULL, 0, NULL};
PyMODINIT_FUNC PyInit_linked(void) { return PyModuleDef_Init(&def); }
EOF
cc -shared -fPIC $(python3-config --includes) linked.c \
    -o linked$(python3-config --extension-suffix) \
    -Wl,--no-as-needed $(python3-config --ldflags --embed)

# 1. Warns, then loads the module:
python -c 'import libpython_linkcheck; libpython_linkcheck.enable(); import linked; print("loaded", linked)'
# 2. With -Werror, the import fails before the shared object is loaded:
python -Werror -c 'import libpython_linkcheck; libpython_linkcheck.enable(); import linked' || echo "exit status $?"
# 3. Check the file without importing it:
python -m libpython_linkcheck linked*.so || echo "exit status $?"
```

Expected output (paths and versions vary):

```text
<string>:1: LibpythonLinkWarning: extension module 'linked' links directly to libpython: /demo/linked.cpython-315-x86_64-linux-gnu.so has DT_NEEDED libpython3.15.so.1.0
loaded <module 'linked' from '/demo/linked.cpython-315-x86_64-linux-gnu.so'>
Traceback (most recent call last):
  ...
libpython_linkcheck.LibpythonLinkWarning: extension module 'linked' links directly to libpython: /demo/linked.cpython-315-x86_64-linux-gnu.so has DT_NEEDED libpython3.15.so.1.0
exit status 1
linked.cpython-315-x86_64-linux-gnu.so: DT_NEEDED libpython3.15.so.1.0
exit status 1
```

## What the 0.1.0a1 alpha supports

Supported and tested:

- CPython 3.11 through 3.15 on Linux (x86_64 and aarch64, glibc).
- Explicit activation: call `libpython_linkcheck.enable()` in each interpreter
  that should be checked. Only extension modules imported **after** that call
  are inspected.
- Every extension module loaded through the import system
  (`importlib.machinery.ExtensionFileLoader`, which also serves
  `importlib.util.spec_from_file_location` and similar).
- Only the extension's **own** `DT_NEEDED` entries; dependencies of its
  dependencies are not inspected.
- libpython names recognized: versioned (`libpython3.12.so.1.0`,
  `libpython3.12.so`), Stable ABI (`libpython3.so`), free-threaded
  (`libpython3.13t.so.1.0`), and ABI-flagged (`libpython3.12d.so.1.0`)
  names, including entries that carry a directory.
- Standard warning filters, `-Werror`, and `catch_warnings()`.
- Objects that cannot be read or parsed are skipped silently, so that
  CPython's own loader reports the real error.

Not covered yet:

- Automatic activation (`sitecustomize`, `.pth` files, or a hook installed
  by an embedding application before `Py_Initialize()`).
- Subinterpreters: a Python audit hook belongs to the interpreter that
  installed it, so `enable()` must be called in each one. This is not yet tested.
- Free-threaded interpreters: their libpython names are recognized, but the
  hook has not yet been tested running on a free-threaded build.
- Shared libraries opened with `ctypes` or `dlopen()` directly, and extension
  modules that were already loaded before `enable()`.
- Other platforms: `enable()` works, but non-ELF files (Mach-O, PE) are never
  reported. Other ELF platforms are untested.

## License

MIT
