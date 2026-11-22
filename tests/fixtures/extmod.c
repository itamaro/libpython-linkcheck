/*
 * Test fixture extension module. Compiled at test time (never shipped) as
 * several modules that differ only in name and in how they are linked:
 *
 *   cc -shared -fPIC -DMODNAME=<name> extmod.c ... [-lpython3.X | -lpython3]
 *
 * The ELF constructor runs when the dynamic loader maps the object, before
 * PyInit_<name>. It appends the module name to $LINKCHECK_FIXTURE_CTOR_LOG,
 * which lets tests prove whether dlopen() happened at all.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdio.h>
#include <stdlib.h>

#ifndef MODNAME
#error "compile with -DMODNAME=<module name>"
#endif

#define LINKCHECK_STR_(x) #x
#define LINKCHECK_STR(x) LINKCHECK_STR_(x)
#define LINKCHECK_CAT_(a, b) a##b
#define LINKCHECK_CAT(a, b) LINKCHECK_CAT_(a, b)
#define MODNAME_STR LINKCHECK_STR(MODNAME)

__attribute__((constructor)) static void
linkcheck_fixture_ctor(void)
{
    const char *log = getenv("LINKCHECK_FIXTURE_CTOR_LOG");
    if (log == NULL) {
        return;
    }
    FILE *f = fopen(log, "a");
    if (f != NULL) {
        fputs(MODNAME_STR "\n", f);
        fclose(f);
    }
}

static PyObject *
hello(PyObject *Py_UNUSED(module), PyObject *Py_UNUSED(ignored))
{
    return PyUnicode_FromString(MODNAME_STR);
}

static PyMethodDef methods[] = {
    {"hello", hello, METH_NOARGS, "Return the module name."},
    {NULL, NULL, 0, NULL},
};

static PyModuleDef_Slot slots[] = {
    {Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
#if PY_VERSION_HEX >= 0x030D0000
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL},
};

static struct PyModuleDef moduledef = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = MODNAME_STR,
    .m_doc = "libpython-linkcheck test fixture",
    .m_size = 0,
    .m_methods = methods,
    .m_slots = slots,
};

PyMODINIT_FUNC
LINKCHECK_CAT(PyInit_, MODNAME)(void)
{
    return PyModuleDef_Init(&moduledef);
}
