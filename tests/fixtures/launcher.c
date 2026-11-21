/*
 * Test launcher: a `python` executable built the way an embedder (for
 * example python-build-standalone) would integrate libpython-linkcheck:
 * register the hook, then hand over to CPython's normal main.
 *
 * Test-only modes, selected by environment variables:
 *   LINKCHECK_LAUNCHER_INSTALL_TWICE=1  call LibpythonLinkcheck_Install() twice
 *   LINKCHECK_LAUNCHER_REINIT=1         treat each argument as Python code to
 *                                       run in its own Py_Initialize() /
 *                                       Py_FinalizeEx() lifetime
 */
#include <Python.h>

#include <stdio.h>
#include <stdlib.h>

#include "libpython_linkcheck.h"

static int
run_lifetimes(int argc, char **argv)
{
    for (int i = 1; i < argc; i++) {
        if (LibpythonLinkcheck_Install() < 0) {
            return 120;
        }
        Py_Initialize();
        int rc = PyRun_SimpleString(argv[i]);
        if (Py_FinalizeEx() < 0 || rc != 0) {
            return 1;
        }
    }
    return 0;
}

int
main(int argc, char **argv)
{
    if (getenv("LINKCHECK_LAUNCHER_REINIT") != NULL) {
        return run_lifetimes(argc, argv);
    }
    if (LibpythonLinkcheck_Install() < 0) {
        fputs("LibpythonLinkcheck_Install() failed\n", stderr);
        return 120;
    }
    if (getenv("LINKCHECK_LAUNCHER_INSTALL_TWICE") != NULL && LibpythonLinkcheck_Install() < 0) {
        return 120;
    }
    return Py_BytesMain(argc, argv);
}
