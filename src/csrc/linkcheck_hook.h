/*
 * libpython-linkcheck: audit hook logic shared by the _native extension
 * module and the embedding entry point (internal header).
 */
#ifndef LIBPYTHON_LINKCHECK_HOOK_H
#define LIBPYTHON_LINKCHECK_HOOK_H

#include <Python.h>

/* The C API version the including file may rely on: the Limited API floor
   when building for the Stable ABI (Py_TARGET_ABI3T sets Py_LIMITED_API
   too), else the headers' own version. Choose APIs and slots with this, so
   that newer headers never add newer dependencies to a Stable ABI build. */
#if defined(Py_LIMITED_API)
#define LPC_TARGET_API (Py_LIMITED_API + 0)
#else
#define LPC_TARGET_API PY_VERSION_HEX
#endif

/* Name of the audit event used to ask whether a hook is installed. Each
   hook appends (kind, category) to the list passed as its only argument. */
#define LPC_PROBE_EVENT "libpython_linkcheck.probe"

/* Handle one audit event. `kind` identifies the caller in probe replies
   ("native" for the per-interpreter hook, "embedded" for the runtime hook).
   Returns 0, or -1 with an exception set when a warning filter turned the
   warning into an error (which aborts the import). */
int lpc_audit(const char *event, PyObject *args, const char *kind);

/* Return a new reference to this interpreter's LibpythonLinkWarning class,
   creating it on first use. */
PyObject *lpc_get_category(void);

#endif /* LIBPYTHON_LINKCHECK_HOOK_H */
