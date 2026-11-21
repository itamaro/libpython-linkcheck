/*
 * libpython_linkcheck._native: the C implementation used by the package
 * when available. The pure-Python modules remain as a fallback.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <errno.h>

#include "linkcheck_elf.h"

PyDoc_STRVAR(read_needed_doc,
             "read_needed(path, /)\n--\n\n"
             "Return (0, [names]) with the DT_NEEDED entries of the ELF object at path,\n"
             "(2, detail) if it is not ELF, or (3, detail) if it is malformed.\n"
             "Raises OSError if it cannot be read.");

static PyObject *
native_read_needed(PyObject *Py_UNUSED(module), PyObject *path)
{
    PyObject *encoded = NULL;
    if (!PyUnicode_FSConverter(path, &encoded)) {
        return NULL;
    }
    lpc_needed needed;
    const char *detail = NULL;
    lpc_status st;
    int saved_errno;
    Py_BEGIN_ALLOW_THREADS
        st = lpc_read_needed(PyBytes_AS_STRING(encoded), &needed, &detail);
        saved_errno = errno;
    Py_END_ALLOW_THREADS
    Py_DECREF(encoded);

    switch (st) {
    case LPC_OK: {
        PyObject *names = PyList_New(0);
        if (names == NULL) {
            lpc_needed_free(&needed);
            return NULL;
        }
        const char *p = needed.data;
        for (size_t i = 0; i < needed.count; i++) {
            size_t len = strlen(p);
            PyObject *name = PyUnicode_DecodeFSDefaultAndSize(p, (Py_ssize_t)len);
            if (name == NULL || PyList_Append(names, name) < 0) {
                Py_XDECREF(name);
                Py_DECREF(names);
                lpc_needed_free(&needed);
                return NULL;
            }
            Py_DECREF(name);
            p += len + 1;
        }
        lpc_needed_free(&needed);
        return Py_BuildValue("(iN)", 0, names);
    }
    case LPC_ERR_OS:
        errno = saved_errno;
        return PyErr_SetFromErrnoWithFilenameObject(PyExc_OSError, path);
    case LPC_ERR_NOMEM:
        return PyErr_NoMemory();
    case LPC_ERR_NOT_ELF:
    case LPC_ERR_MALFORMED:
    default:
        return Py_BuildValue("(is)", (int)st, detail ? detail : "malformed ELF");
    }
}

PyDoc_STRVAR(is_libpython_doc,
             "is_libpython(name, /)\n--\n\n"
             "Return True if a DT_NEEDED entry names a libpython shared library.");

static PyObject *
native_is_libpython(PyObject *Py_UNUSED(module), PyObject *name)
{
    PyObject *encoded = NULL;
    if (!PyUnicode_FSConverter(name, &encoded)) {
        return NULL;
    }
    int result = lpc_is_libpython(PyBytes_AS_STRING(encoded));
    Py_DECREF(encoded);
    return PyBool_FromLong(result);
}

static PyMethodDef native_methods[] = {
    {"read_needed", native_read_needed, METH_O, read_needed_doc},
    {"is_libpython", native_is_libpython, METH_O, is_libpython_doc},
    {NULL, NULL, 0, NULL},
};

static PyModuleDef_Slot native_slots[] = {
#if PY_VERSION_HEX >= 0x030C0000
    {Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
#endif
#if PY_VERSION_HEX >= 0x030D0000
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL},
};

static struct PyModuleDef native_module = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "libpython_linkcheck._native",
    .m_doc = "C implementation of libpython-linkcheck.",
    .m_size = 0,
    .m_methods = native_methods,
    .m_slots = native_slots,
};

PyMODINIT_FUNC
PyInit__native(void)
{
    return PyModuleDef_Init(&native_module);
}
