"""Differential tests: the C implementation must match the Python one exactly.

A corpus of synthetic ELF objects (every layout, every truncation, and
seeded random corruptions) is run through the pure-Python reader, the
``_native`` extension module, and a standalone harness built with
AddressSanitizer and UndefinedBehaviorSanitizer.
"""

from __future__ import annotations

import os
import random
import struct
import subprocess
import sysconfig
from pathlib import Path

import pytest
from elfbuild import DT_SONAME, ElfSpec, build_elf
from extbuild import IS_LINUX, compiler, readelf_dynamic_symbols
from pyrun import OWN_GIL_SUBINTERPRETER_HELPER, impl_env, run_python

from libpython_linkcheck import _elf

NATIVE_SRC = Path(__file__).resolve().parent.parent / "src" / "csrc"
HARNESS_SRC = Path(__file__).resolve().parent / "native" / "elfcheck.c"
SIZECHECK_SRC = Path(__file__).resolve().parent / "native" / "sizecheck.c"
STATUS = {"ok": 0, "os": 1, "not-elf": 2, "malformed": 3}

# Deselected (not skipped) by conftest.py when the C implementation is not built.
native = pytest.mark.requires_native


def base_images() -> list[bytes]:
    names = [b"libpython3.12.so.1.0", b"libm.so.6", b"/opt/lib/libpython3.so", b"libc.so.6"]
    images = []
    for bits in (32, 64):
        for little in (True, False):
            images.append(build_elf(ElfSpec(needed=names, bits=bits, little=little)))
            images.append(build_elf(ElfSpec(needed=names[:1], bits=bits, pn_xnum=True)))
    images.append(build_elf(ElfSpec(needed=names, strsz=False)))
    images.append(build_elf(ElfSpec(needed=names, extra_dyn=[(DT_SONAME, 1)])))
    images.append(build_elf(ElfSpec(needed=[b"lib\xff.so", b""])))
    images.append(build_elf(ElfSpec(needed=names, dynamic=False)))
    return images


def mutations(image: bytes, rng: random.Random, count: int) -> list[bytes]:
    out = []
    boundary = [0, 1, 0x7F, 0xFF, 0xFFFF, 0xFFFFFFFF, 2**64 - 1, len(image), len(image) + 1]
    for _ in range(count):
        data = bytearray(image)
        for _ in range(rng.randint(1, 4)):
            pos = rng.randrange(len(data))
            kind = rng.random()
            if kind < 0.4:
                data[pos] = rng.randrange(256)
            else:
                width = rng.choice([2, 4, 8])
                pos = min(pos, len(data) - width)
                value = rng.choice(boundary) & ((1 << (8 * width)) - 1)
                data[pos : pos + width] = struct.pack({2: "<H", 4: "<I", 8: "<Q"}[width], value)
        out.append(bytes(data))
    return out


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> list[Path]:
    root = tmp_path_factory.mktemp("corpus")
    rng = random.Random(20261121)
    blobs = [b"", b"\x7fELF", b"not elf at all"]
    for image in base_images():
        blobs.append(image)
        blobs.extend(image[:cut] for cut in range(0, len(image), 3))
        blobs.extend(mutations(image, rng, 300))
    paths = []
    for i, blob in enumerate(blobs):
        p = root / f"{i:05d}.so"
        p.write_bytes(blob)
        paths.append(p)
    (root / "dir.so").mkdir()
    paths += [root / "dir.so", root / "missing.so"]
    return paths


def python_result(path: Path) -> tuple[int, tuple[tuple[bytes, int], ...]]:
    try:
        names = _elf.py_read_needed(path)
    except _elf.NotELFError:
        return STATUS["not-elf"], ()
    except _elf.ELFError:
        return STATUS["malformed"], ()
    except OSError:
        return STATUS["os"], ()
    return STATUS["ok"], tuple((os.fsencode(n), int(_elf.py_is_libpython(n))) for n in names)


def test_corpus_exercises_every_outcome(corpus):
    outcomes = {python_result(p)[0] for p in corpus}
    assert outcomes == set(STATUS.values())
    found = sum(1 for p in corpus if python_result(p)[1])
    assert found > 100


@native
def test_native_is_the_default_implementation():
    assert _elf.IMPLEMENTATION == "native"


@native
@pytest.mark.skipif(not IS_LINUX, reason="readelf inspects ELF objects")
def test_extension_does_not_register_a_runtime_hook():
    """The embedder entry point (linkcheck_embed.c) is not part of _native.

    The extension installs its hook per interpreter with sys.addaudithook();
    PySys_AddAuditHook() is not part of the Limited API.
    """
    defined, undefined = readelf_dynamic_symbols(_elf._native.__file__)
    assert "PyUnicode_FSConverter" in undefined  # readelf sees the C API imports
    assert "PySys_AddAuditHook" not in undefined
    assert "LibpythonLinkcheck_Install" not in defined


@native
@pytest.mark.skipif(not IS_LINUX, reason="the fixtures are Linux extension modules")
def test_extension_loads_in_an_own_gil_subinterpreter(exts, tmp_path):
    """_native declares per-interpreter GIL support, and its hook works there.

    The control proves the subinterpreter enforces that declaration.
    """
    sub = f"""
import sys, warnings
sys.path.insert(0, {str(exts.dir)!r})
try:
    import main_only_ext
except ImportError:
    print("control refused", flush=True)
import libpython_linkcheck as m
from libpython_linkcheck import _elf, _native
same_file = _native.__file__ == {_elf._native.__file__!r}
print("native:", _elf._native is _native, same_file, flush=True)
print("enabled:", m.enable(), m.LibpythonLinkWarning is _native.category(), flush=True)
warnings.simplefilter("error")
try:
    import linked_ext
except m.LibpythonLinkWarning as w:
    print("blocked:", w.module, flush=True)
import unlinked_ext
print("loaded:", unlinked_ext.hello(), flush=True)
"""
    code = OWN_GIL_SUBINTERPRETER_HELPER + f"run_in_own_gil_subinterpreter({sub!r})\n"
    r = run_python(code, workdir=tmp_path, env=impl_env("native"))
    assert (r.returncode, r.stderr) == (0, ""), r.stderr
    assert r.stdout == (
        "control refused\n"
        "native: True True\n"
        "enabled: True True\n"
        "blocked: linked_ext\n"
        "loaded: unlinked_ext\n"
    )
    assert "linked_ext" not in r.ctor


@native
@pytest.mark.skipif(not IS_LINUX, reason="the fixtures are Linux extension modules")
def test_extension_keeps_the_gil_disabled(exts, tmp_path):
    """On a free-threaded build the GIL starts disabled and stays disabled.

    An extension without Py_mod_gil would re-enable it when imported. This
    runs without PYTHON_GIL or -X gil, so the default applies. On a
    GIL-enabled build the state is simply unchanged.
    """
    code = f"""
import sys, sysconfig, warnings
sys.path.insert(0, {str(exts.dir)!r})
gil = getattr(sys, "_is_gil_enabled", lambda: True)  # 3.13+; 3.12 always has the GIL
states = [gil()]
from libpython_linkcheck import _native
states.append(gil())
import libpython_linkcheck as m
assert m.enable()
states.append(gil())
warnings.simplefilter("always")
import linked_ext, unlinked_ext
found = []
sys.audit("libpython_linkcheck.probe", found)
states.append(gil())
print(bool(sysconfig.get_config_var("Py_GIL_DISABLED")), states, len(found))
"""
    r = run_python(code, workdir=tmp_path, env=impl_env("native"))
    assert r.returncode == 0, r.stderr
    free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    assert r.stdout == f"{free_threaded} {[not free_threaded] * 4} 1\n"
    assert len(r.link_warnings) == 1, r.stderr


@native
def test_extension_matches_python_reader(corpus):
    for path in corpus:
        expected = python_result(path)
        try:
            status, value = _elf._native.read_needed(path)
        except OSError:
            status, value = STATUS["os"], ()
        if status == 0:
            value = tuple((os.fsencode(n), int(_elf._native.is_libpython(n))) for n in value)
        else:
            value = ()
        assert (status, value) == expected, path


@pytest.mark.skipif(not IS_LINUX, reason="sanitizer harness is built on Linux")
def test_sanitized_harness_matches_python_reader(corpus, tmp_path):
    exe = tmp_path / "elfcheck"
    cmd = [
        *compiler(),
        "-std=c11",
        "-g",
        "-O1",
        "-fno-omit-frame-pointer",
        "-fsanitize=address,undefined",
        "-fno-sanitize-recover=all",
        "-Wall",
        "-Wextra",
        "-Wshadow",
        "-Werror",
        f"-I{NATIVE_SRC}",
        str(HARNESS_SRC),
        str(NATIVE_SRC / "linkcheck_elf.c"),
        "-o",
        str(exe),
    ]
    subprocess.run(cmd, check=True)
    proc = subprocess.run(
        [str(exe)],
        input="".join(f"{p}\n" for p in corpus),
        capture_output=True,
        text=True,
        env={**os.environ, "ASAN_OPTIONS": "detect_leaks=1:abort_on_error=0"},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    assert proc.stderr == ""
    lines = proc.stdout.splitlines()
    assert len(lines) == len(corpus)
    for path, line in zip(corpus, lines, strict=True):
        status, *entries = line.split(" ")
        got = (
            int(status),
            tuple((bytes.fromhex(h), int(flag)) for h, flag in (e.split(":") for e in entries)),
        )
        assert got == python_result(path), path


@pytest.mark.skipif(not IS_LINUX, reason="sanitizer harness is built on Linux")
def test_total_name_size_overflow_is_detected(tmp_path):
    """The reader sums the lengths of all DT_NEEDED names before allocating.

    Entries may share one string, so the string table's size does not bound
    the sum; lpc_size_add() rejects a sum that does not fit in size_t. The
    boundary is tested directly, without allocating anything large.
    """
    exe = tmp_path / "sizecheck"
    cmd = [
        *compiler(),
        "-std=c11",
        "-O1",
        "-fsanitize=address,undefined",
        "-fno-sanitize-recover=all",
        "-Wall",
        "-Wextra",
        "-Wshadow",
        "-Werror",
        f"-I{NATIVE_SRC}",
        str(SIZECHECK_SRC),
        str(NATIVE_SRC / "linkcheck_elf.c"),
        "-o",
        str(exe),
    ]
    subprocess.run(cmd, check=True)
    proc = subprocess.run([str(exe)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.startswith("sizecheck OK"), proc.stdout


@pytest.mark.parametrize(
    "name",
    [
        "",
        "libpython",
        "libpython3",
        "libpython3.",
        "libpython3.so.",
        "libpython3.so.1.",
        "libpython3.12..so",
        "libpython3.12t",
        "libpython3.12T.so",
        "libpython33.so.1.2.3.4",
        "a/b/libpython3.so",
        "libpython3.so/",
        "/libpython3.so",
        "libpython3.1x.so",
        "libpython3.12-dbg.so",
        "libpython3-dc2fd5ae.10.so.1.0",
        "libpython3-dc2fd5ae",
        "libpython3-dc2fd5ae.",
        "libpython3-dc2fd5a",
        "libpython3-dc2fd5ae.so",
        "libpython-dc2fd5ae.so",
        "libpython-dc2fd5ae.10.so",
        "libpython-.so",
        "libpython3-.so",
        "libpython.so",
        "libpython.so.1",
    ],
)
@native
def test_is_libpython_edge_cases_match(name):
    assert _elf._native.is_libpython(name) == _elf.py_is_libpython(name)


@native
def test_is_libpython_random_strings_match():
    rng = random.Random(7)
    alphabet = "libpython3.12so/td-_"
    for _ in range(20000):
        name = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 24)))
        if rng.random() < 0.5:
            name = "libpython" + name
        assert _elf._native.is_libpython(name) == _elf.py_is_libpython(name), name


@native
def test_is_libpython_random_bundled_names_match():
    """Random variations of auditwheel-renamed SONAMEs around the hash."""
    rng = random.Random(11)
    pieces = ["", "3", "2", "3.10", ".10", "m", "t", "-", ".so", ".1", ".0", ".", "x"]
    hexdigits = "0123456789abcdefABg"
    for _ in range(20000):
        digest = "".join(rng.choice(hexdigits) for _ in range(rng.choice([7, 8, 8, 8, 9])))
        name = "libpython" + "".join(rng.choice(pieces) for _ in range(rng.randint(0, 2)))
        name += "-" + digest + "".join(rng.choice(pieces) for _ in range(rng.randint(0, 5)))
        assert _elf._native.is_libpython(name) == _elf.py_is_libpython(name), name
