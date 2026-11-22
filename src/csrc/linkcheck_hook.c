/*
 * libpython-linkcheck: the audit hook, in C.
 *
 * Mirrors libpython_linkcheck/_hook.py. CPython raises
 * ("import", name, filename, None, None, None) from _imp.create_dynamic
 * immediately before it dlopen()s an extension module; importlib's own
 * "import" event passes filename=None. On a match we read the object's own
 * DT_NEEDED entries and, if one names libpython, issue LibpythonLinkWarning
 * attributed to the code that executed the import.
 */
#define PY_SSIZE_T_CLEAN
#include "linkcheck_hook.h"

#include <string.h>

#include "linkcheck_elf.h"

#define CATEGORY_NAME "libpython_linkcheck.LibpythonLinkWarning"

PyDoc_STRVAR(category_doc,
             "An extension module about to be loaded has a DT_NEEDED entry for libpython.\n\n"
             "Instances raised by the hook carry three attributes: ``module`` (the\n"
             "fully qualified name of the extension module being imported),\n"
             "``filename`` (the path of the shared object CPython is about to load),\n"
             "and ``needed`` (a tuple of the object's own DT_NEEDED entries that name\n"
             "libpython).");

PyObject *
lpc_get_category(void)
{
    PyObject *dict = PyInterpreterState_GetDict(PyInterpreterState_Get());
    if (dict == NULL) {
        if (!PyErr_Occurred()) {
            PyErr_SetString(PyExc_RuntimeError, "no per-interpreter dict");
        }
        return NULL;
    }
    PyObject *category = NULL;
#if PY_VERSION_HEX >= 0x030D0000
    if (PyDict_GetItemStringRef(dict, CATEGORY_NAME, &category) < 0) {
        return NULL;
    }
    if (category != NULL) {
        return category;
    }
#else
    category = PyDict_GetItemString(dict, CATEGORY_NAME);
    if (category != NULL) {
        return Py_NewRef(category);
    }
#endif
    PyObject *attrs = Py_BuildValue("{sOsOs()}", "module", Py_None, "filename", Py_None, "needed");
    if (attrs == NULL) {
        return NULL;
    }
    PyObject *created =
        PyErr_NewExceptionWithDoc(CATEGORY_NAME, category_doc, PyExc_RuntimeWarning, attrs);
    Py_DECREF(attrs);
    if (created == NULL) {
        return NULL;
    }
    PyObject *key = PyUnicode_FromString(CATEGORY_NAME);
    if (key == NULL) {
        Py_DECREF(created);
        return NULL;
    }
    /* Keep whichever class won a concurrent creation race. */
#if PY_VERSION_HEX >= 0x030D0000
    if (PyDict_SetDefaultRef(dict, key, created, &category) < 0) {
        category = NULL;
    }
#else
    category = PyDict_SetDefault(dict, key, created);
    Py_XINCREF(category);
#endif
    Py_DECREF(key);
    Py_DECREF(created);
    return category;
}

/* Same rule as CPython's warnings machinery for importlib frames. */
static int
is_internal_frame(PyFrameObject *frame)
{
    PyCodeObject *code = PyFrame_GetCode(frame);
    int internal = 0;
    if (PyUnicode_Check(code->co_filename)) {
        const char *s = PyUnicode_AsUTF8(code->co_filename);
        if (s == NULL) {
            PyErr_Clear();
        }
        else {
            internal = strstr(s, "importlib") != NULL && strstr(s, "_bootstrap") != NULL;
        }
    }
    Py_DECREF(code);
    return internal;
}

/* The stacklevel that makes the warnings machinery attribute the warning to
   the first non-importlib frame. When the innermost frame is internal,
   CPython steps back one frame per level without skipping, so count them. */
static int
import_site_stacklevel(void)
{
    PyFrameObject *frame = PyThreadState_GetFrame(PyThreadState_Get());
    int level = 1;
    while (frame != NULL && is_internal_frame(frame)) {
        PyFrameObject *back = PyFrame_GetBack(frame);
        Py_DECREF(frame);
        frame = back;
        level++;
    }
    Py_XDECREF(frame);
    return level;
}

/* Build the warning instance. Returns NULL (with an exception set) on failure. */
static PyObject *
make_warning(PyObject *name, PyObject *filename, PyObject *needed)
{
    PyObject *category = NULL, *module = NULL, *sep = NULL, *joined = NULL;
    PyObject *message = NULL, *warning = NULL, *needed_tuple = NULL;

    if ((category = lpc_get_category()) == NULL || (module = PyObject_Str(name)) == NULL ||
        (sep = PyUnicode_FromString(", ")) == NULL ||
        (joined = PyUnicode_Join(sep, needed)) == NULL) {
        goto done;
    }
    message = PyUnicode_FromFormat("extension module %R links directly to libpython: "
                                   "%U has DT_NEEDED %U",
                                   module, filename, joined);
    if (message == NULL || (warning = PyObject_CallOneArg(category, message)) == NULL ||
        (needed_tuple = PyList_AsTuple(needed)) == NULL) {
        goto done;
    }
    if (PyObject_SetAttrString(warning, "module", module) < 0 ||
        PyObject_SetAttrString(warning, "filename", filename) < 0 ||
        PyObject_SetAttrString(warning, "needed", needed_tuple) < 0) {
        Py_CLEAR(warning);
    }
done:
    Py_XDECREF(category);
    Py_XDECREF(module);
    Py_XDECREF(sep);
    Py_XDECREF(joined);
    Py_XDECREF(message);
    Py_XDECREF(needed_tuple);
    return warning;
}

static int
check_extension(PyObject *name, PyObject *filename_obj)
{
    PyObject *encoded = NULL;
    if (!PyUnicode_FSConverter(filename_obj, &encoded)) {
        PyErr_Clear(); /* never let the checker break an import */
        return 0;
    }
    lpc_needed needed;
    lpc_status st;
    Py_BEGIN_ALLOW_THREADS
        st = lpc_read_needed(PyBytes_AS_STRING(encoded), &needed, NULL);
    Py_END_ALLOW_THREADS
    if (st != LPC_OK) {
        /* Not ELF, unreadable, or malformed: CPython's loader reports real
           problems. */
        Py_DECREF(encoded);
        return 0;
    }

    int result = 0;
    PyObject *matches = NULL, *filename = NULL, *warning = NULL;
    const char *p = needed.data;
    for (size_t i = 0; i < needed.count; p += strlen(p) + 1, i++) {
        if (!lpc_is_libpython(p)) {
            continue;
        }
        if (matches == NULL && (matches = PyList_New(0)) == NULL) {
            goto error;
        }
        PyObject *s = PyUnicode_DecodeFSDefault(p);
        if (s == NULL || PyList_Append(matches, s) < 0) {
            Py_XDECREF(s);
            goto error;
        }
        Py_DECREF(s);
    }
    if (matches == NULL) {
        goto done;
    }
    filename =
        PyUnicode_DecodeFSDefaultAndSize(PyBytes_AS_STRING(encoded), PyBytes_GET_SIZE(encoded));
    if (filename == NULL || (warning = make_warning(name, filename, matches)) == NULL) {
        goto error;
    }
    /* _warnings.warn() accepts a Warning instance and applies the filters;
       an "error" action raises it here, which aborts the import before
       dlopen(). */
    PyObject *warnings_module = PyImport_ImportModule("_warnings");
    if (warnings_module == NULL) {
        goto error;
    }
    PyObject *res = PyObject_CallMethod(warnings_module, "warn", "OOi", warning, Py_None,
                                        import_site_stacklevel());
    Py_DECREF(warnings_module);
    if (res == NULL) {
        result = -1; /* propagate: a filter turned the warning into an error */
        goto done;
    }
    Py_DECREF(res);
    goto done;

error:
    PyErr_Clear();
done:
    Py_XDECREF(matches);
    Py_XDECREF(filename);
    Py_XDECREF(warning);
    Py_DECREF(encoded);
    lpc_needed_free(&needed);
    return result;
}

static int
answer_probe(PyObject *args, const char *kind)
{
    if (!PyTuple_Check(args) || PyTuple_GET_SIZE(args) < 1 ||
        !PyList_Check(PyTuple_GET_ITEM(args, 0))) {
        return 0;
    }
    PyObject *category = lpc_get_category();
    if (category == NULL) {
        return -1;
    }
    PyObject *entry = Py_BuildValue("(sN)", kind, category);
    if (entry == NULL) {
        return -1;
    }
    int rc = PyList_Append(PyTuple_GET_ITEM(args, 0), entry);
    Py_DECREF(entry);
    return rc;
}

int
lpc_audit(const char *event, PyObject *args, const char *kind)
{
    /* Cheap pre-check: this runs for every audit event. */
    if (event[0] != 'i' && event[0] != 'l') {
        return 0;
    }
    if (strcmp(event, "import") == 0) {
        if (!PyTuple_Check(args) || PyTuple_GET_SIZE(args) != 5) {
            return 0;
        }
        PyObject *filename = PyTuple_GET_ITEM(args, 1);
        if (filename == Py_None || PyTuple_GET_ITEM(args, 2) != Py_None) {
            return 0;
        }
        return check_extension(PyTuple_GET_ITEM(args, 0), filename);
    }
    if (strcmp(event, LPC_PROBE_EVENT) == 0) {
        return answer_probe(args, kind);
    }
    return 0;
}
