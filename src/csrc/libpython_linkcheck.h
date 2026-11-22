/*
 * libpython-linkcheck embedding API.
 *
 * Lets an application that embeds CPython (or a CPython distribution such as
 * python-build-standalone, in its `python` executable) check every extension
 * module before it is loaded, from the very start of the runtime and without
 * importing any Python package.
 *
 * Build: compile these files into the program, which links libpython, with
 * src/csrc on the include path:
 *
 *     src/csrc/linkcheck_embed.c  (this entry point; full C API)
 *     src/csrc/linkcheck_hook.c   (the hook logic shared with the package)
 *     src/csrc/linkcheck_elf.c    (plain C99 + POSIX)
 *     src/csrc/linkcheck_elf.h, linkcheck_hook.h, libpython_linkcheck.h
 *
 * Use:
 *
 *     #include "libpython_linkcheck.h"
 *
 *     int main(int argc, char **argv) {
 *         if (LibpythonLinkcheck_Install() < 0) { ... }
 *         return Py_BytesMain(argc, argv);
 *     }
 *
 * The hook is a runtime-wide C audit hook (PySys_AddAuditHook), so it covers
 * the main interpreter and every subinterpreter, and it is active even under
 * `-I -S`. It issues `libpython_linkcheck.LibpythonLinkWarning` (a
 * RuntimeWarning subclass, created per interpreter and shared with the Python
 * package) through the normal warnings machinery. A later
 * `libpython_linkcheck.enable()` call detects it and installs nothing.
 */
#ifndef LIBPYTHON_LINKCHECK_H
#define LIBPYTHON_LINKCHECK_H

#ifdef __cplusplus
extern "C" {
#endif

#define LIBPYTHON_LINKCHECK_API_VERSION 1

/* Register the hook. Call from the main thread before Py_Initialize*(),
   Py_InitializeFromConfig(), Py_Main() or Py_BytesMain(). Calling it again
   in the same runtime is a no-op; after Py_Finalize*() it may be called
   again before the next initialization. Returns 0 on success, -1 on
   failure (out of memory). */
int LibpythonLinkcheck_Install(void);

#ifdef __cplusplus
}
#endif

#endif /* LIBPYTHON_LINKCHECK_H */
