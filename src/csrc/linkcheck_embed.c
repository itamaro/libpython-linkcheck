/*
 * libpython-linkcheck: the embedding entry point, LibpythonLinkcheck_Install().
 *
 * Only embedders compile this file (with the full C API, into a program that
 * links libpython). The libpython_linkcheck._native extension does not: it
 * registers the same callback logic (linkcheck_hook.c) per interpreter
 * through sys.addaudithook(), so it needs no PySys_AddAuditHook().
 */
#include <Python.h>

#include <string.h>

#include "libpython_linkcheck.h"
#include "linkcheck_hook.h"

/* Set while our runtime hook is registered. Only touched before
   initialization (LibpythonLinkcheck_Install) and at finalization. */
static int embedded_hook_installed = 0;

static int
embedded_hook(const char *event, PyObject *args, void *Py_UNUSED(user_data))
{
    if (strcmp(event, "cpython._PySys_ClearAuditHooks") == 0) {
        /* Py_Finalize*() is about to drop every C hook. */
        embedded_hook_installed = 0;
        return 0;
    }
    return lpc_audit(event, args, "embedded");
}

int
LibpythonLinkcheck_Install(void)
{
    if (embedded_hook_installed) {
        return 0;
    }
    if (PySys_AddAuditHook(embedded_hook, NULL) < 0) {
        return -1;
    }
    embedded_hook_installed = 1;
    return 0;
}
