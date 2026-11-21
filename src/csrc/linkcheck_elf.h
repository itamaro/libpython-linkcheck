/*
 * libpython-linkcheck: read an ELF object's own DT_NEEDED entries.
 *
 * Plain C99 + POSIX; does not include Python.h, so it can be compiled into
 * an embedding application as well as the extension module. Behavior
 * matches the pure-Python reader in libpython_linkcheck/_elf.py, which the
 * test suite checks differentially.
 */
#ifndef LIBPYTHON_LINKCHECK_ELF_H
#define LIBPYTHON_LINKCHECK_ELF_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    LPC_OK = 0,
    LPC_ERR_OS = 1,        /* open/read failed; errno is set */
    LPC_ERR_NOT_ELF = 2,   /* no ELF magic */
    LPC_ERR_MALFORMED = 3, /* truncated or inconsistent ELF data */
    LPC_ERR_NOMEM = 4,
} lpc_status;

/* The DT_NEEDED entries of one object: `count` NUL-terminated strings stored
   back to back in `data` (`size` bytes in total). */
typedef struct {
    char *data;
    size_t size;
    size_t count;
} lpc_needed;

/* Read the DT_NEEDED entries of the ELF object at `path`, in order.
   On LPC_OK, `out` owns a buffer to release with lpc_needed_free() (an
   object without a dynamic segment yields count == 0). On error, `out` is
   empty and `*detail` (if not NULL) points to a static description. */
lpc_status lpc_read_needed(const char *path, lpc_needed *out, const char **detail);

void lpc_needed_free(lpc_needed *needed);

/* Internal, exposed for tests: add `len` to `*total`. Returns 0, or -1 and
   leaves `*total` unchanged if the sum does not fit in size_t. */
int lpc_size_add(size_t *total, size_t len);

/* Return 1 if a DT_NEEDED entry names a libpython shared library (matched on
   its final path component), else 0. Same rule as is_libpython() in
   _elf.py: libpython<digits>[.<digits>][a-z]*.so[.<digits>]* */
int lpc_is_libpython(const char *name);

#ifdef __cplusplus
}
#endif

#endif /* LIBPYTHON_LINKCHECK_ELF_H */
