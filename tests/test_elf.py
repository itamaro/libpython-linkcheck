"""Unit tests for the DT_NEEDED reader and libpython name matching."""

from __future__ import annotations

import os
import shutil
import sys
import sysconfig
from pathlib import Path

import pytest
from elfbuild import DT_SONAME, ElfSpec, build_elf, dynamic_offset
from extbuild import IS_LINUX, readelf_needed

from libpython_linkcheck import ELFError, libpython_dependencies
from libpython_linkcheck._elf import NotELFError


def write(tmp_path: Path, data: bytes, name: str = "obj.so") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("bits", [32, 64])
@pytest.mark.parametrize("little", [True, False], ids=["le", "be"])
def test_reads_needed_in_order(impl, tmp_path, bits, little):
    names = [b"libpython3.12.so.1.0", b"libm.so.6", b"libc.so.6"]
    path = write(tmp_path, build_elf(ElfSpec(needed=names, bits=bits, little=little)))
    assert impl.read_needed(path) == [n.decode() for n in names]
    assert libpython_dependencies(path) == ["libpython3.12.so.1.0"]


@pytest.mark.parametrize("bits", [32, 64])
def test_pn_xnum_program_header_count(impl, tmp_path, bits):
    spec = ElfSpec(needed=[b"libpython3.so"], bits=bits, pn_xnum=True)
    assert impl.read_needed(write(tmp_path, build_elf(spec))) == ["libpython3.so"]


def test_other_dynamic_tags_are_ignored(impl, tmp_path):
    spec = ElfSpec(needed=[b"libc.so.6"], extra_dyn=[(DT_SONAME, 1), (0x6FFFFEF5, 0)])
    assert impl.read_needed(write(tmp_path, build_elf(spec))) == ["libc.so.6"]


def test_no_dynamic_segment_means_no_dependencies(impl, tmp_path):
    path = write(tmp_path, build_elf(ElfSpec(needed=[b"libpython3.so"], dynamic=False)))
    assert impl.read_needed(path) == []


def test_dynamic_without_needed(impl, tmp_path):
    assert impl.read_needed(write(tmp_path, build_elf(ElfSpec()))) == []


def test_bytes_path_and_pathlike(impl, tmp_path):
    path = write(tmp_path, build_elf(ElfSpec(needed=[b"libpython3.15t.so.1.0"])))
    assert impl.read_needed(os.fsencode(path)) == ["libpython3.15t.so.1.0"]
    assert libpython_dependencies(str(path)) == ["libpython3.15t.so.1.0"]


def test_undecodable_name_round_trips(impl, tmp_path):
    raw = b"lib\xffodd.so"
    path = write(tmp_path, build_elf(ElfSpec(needed=[raw])))
    (name,) = impl.read_needed(path)
    assert os.fsencode(name) == raw


@pytest.mark.parametrize(
    "data",
    [b"", b"\x7fEL", b"MZ\x90\x00" + bytes(60), b"#!/bin/sh\n", b"\xcf\xfa\xed\xfe" + bytes(60)],
    ids=["empty", "short-magic", "pe", "script", "macho"],
)
def test_not_elf(impl, tmp_path, data):
    with pytest.raises(NotELFError):
        impl.read_needed(write(tmp_path, data))


def test_not_elf_is_elf_error_is_value_error():
    assert issubclass(NotELFError, ELFError)
    assert issubclass(ELFError, ValueError)


def test_missing_file(impl, tmp_path):
    with pytest.raises(FileNotFoundError):
        impl.read_needed(tmp_path / "missing.so")


@pytest.mark.parametrize(("byte_index", "value"), [(4, 3), (5, 0)], ids=["class", "data"])
def test_bad_ident(impl, tmp_path, byte_index, value):
    data = bytearray(build_elf(ElfSpec(needed=[b"libc.so.6"])))
    data[byte_index] = value
    with pytest.raises(ELFError, match="unknown ELF"):
        impl.read_needed(write(tmp_path, bytes(data)))


@pytest.mark.parametrize("bits", [32, 64])
def test_every_truncation_is_handled(impl, tmp_path, bits):
    """No prefix of a valid object may crash the parser with a non-ELFError."""
    data = build_elf(ElfSpec(needed=[b"libpython3.12.so.1.0", b"libc.so.6"], bits=bits))
    for cut in range(len(data)):
        path = write(tmp_path, data[:cut])
        try:
            result = impl.read_needed(path)
        except ELFError:
            continue
        # A truncated object may still parse if the cut only removed data
        # the reader never needs; it must then report a subset of the real entries.
        assert set(result) <= {"libpython3.12.so.1.0", "libc.so.6"}


def test_strtab_outside_load_segments(impl, tmp_path):
    spec = ElfSpec(needed=[b"libc.so.6"], strtab_vaddr_override=0x10)
    with pytest.raises(ELFError, match="not in any PT_LOAD"):
        impl.read_needed(write(tmp_path, build_elf(spec)))


def test_needed_without_strtab(impl, tmp_path):
    with pytest.raises(ELFError, match="no DT_STRTAB"):
        impl.read_needed(write(tmp_path, build_elf(ElfSpec(needed=[b"libc.so.6"], strtab=False))))


def test_missing_strsz_reads_to_segment_end(impl, tmp_path):
    spec = ElfSpec(needed=[b"libpython3.so"], strsz=False)
    assert impl.read_needed(write(tmp_path, build_elf(spec))) == ["libpython3.so"]


def test_needed_offset_outside_strtab(impl, tmp_path):
    data = bytearray(build_elf(ElfSpec(needed=[b"libc.so.6"])))
    off = dynamic_offset(bytes(data))
    data[off + 8 : off + 16] = (10_000).to_bytes(8, "little")  # first d_val
    with pytest.raises(ELFError, match="outside DT_STRTAB"):
        impl.read_needed(write(tmp_path, bytes(data)))


@pytest.mark.parametrize(
    "name",
    [
        "libpython3.so",
        "libpython3.11.so",
        "libpython3.11.so.1.0",
        "libpython3.15.so.1.0",
        "libpython3.13t.so.1.0",
        "libpython3.14t.so",
        "libpython3.14td.so.1.0",
        "libpython3.12d.so.1.0",
        "libpython3.7m.so.1.0",
        "libpython2.7.so.1.0",
        "libpython3.16.so.1.0",
        "/usr/local/lib/libpython3.12.so.1.0",
        "../lib/libpython3.so",
        # Bundled by auditwheel: "-<8 hex>" inserted at the first dot.
        "libpython3-dc2fd5ae.10.so.1.0",  # cohere==2.1.0, cp310 manylinux wheel
        "cohere.libs/libpython3-dc2fd5ae.10.so.1.0",
        "libpython3-0123abcd.so",
        "libpython3-0123abcd.6m.so.1.0",
        "libpython3-0123abcd.13t.so.1.0",
        "libpython-0123abcd.so",
        "libpython3.10.so.1.0",  # genicam==1.6.0
        "libpython3.6m.so.1.0",  # scanpy==0.4.4
        "libpython.so",  # unversioned
    ],
)
def test_is_libpython(impl, name):
    assert impl.is_libpython(name)


@pytest.mark.parametrize(
    "name",
    [
        "libc.so.6",
        "libpythonista.so",
        "libpython_helpers.so",
        "libpython3.10.so.backup",
        "libpython3-dc2fd5a.10.so.1.0",  # 7 hex digits
        "libpython3-dc2fd5ae0.10.so.1.0",  # 9
        "libpython3-DC2FD5AE.10.so.1.0",  # auditwheel's hashes are lowercase
        "libpython3-dc2fd5ag.10.so.1.0",
        "libpython3.10-dc2fd5ae.so.1.0",  # hash after the first dot
        "libpython-0123abcd3.so",
        "libpython3-0123abcd-0123abcd.so",
        "libcrypt-796a3fb8.so.2",
        "libpython3.12.a",
        "libpython3.12.so.bak",
        "libpython3-c.so",
        "libpypy3.11-c.so",
        "libpython3.12.dylib",
        "python3.12",
        "libboost_python312.so.1.83.0",
        "libpython3.12.so/other.so",
        "xlibpython3.so",
    ],
)
def test_is_not_libpython(impl, name):
    assert not impl.is_libpython(name)


# --- real objects, checked against binutils' readelf ---------------------------------------


def real_objects() -> list[str]:
    candidates = [sys.executable]
    libdir = sysconfig.get_config_var("LIBDIR") or ""
    for name in (sysconfig.get_config_var("INSTSONAME"), "libpython3.so"):
        if name:
            candidates.append(os.path.join(libdir, name))
    for mod in ("_ssl", "_ctypes", "_sqlite3", "math", "_decimal"):
        try:
            module = __import__(mod)
        except ImportError:
            continue
        if getattr(module, "__file__", None):
            candidates.append(module.__file__)
    return [os.path.realpath(p) for p in candidates if os.path.isfile(p)]


@pytest.mark.skipif(not IS_LINUX, reason="real ELF objects are only available on Linux")
def test_matches_readelf_on_real_objects(impl):
    assert shutil.which("readelf"), "readelf (binutils) is required for the Linux suite"
    objects = real_objects()
    assert len(objects) >= 3, objects
    for path in objects:
        assert impl.read_needed(path) == readelf_needed(path), path


@pytest.mark.skipif(not IS_LINUX, reason="real ELF objects are only available on Linux")
def test_real_interpreter_links_libpython_when_shared():
    """Sanity check of the oracle on the test images (--enable-shared builds)."""
    if not sysconfig.get_config_var("Py_ENABLE_SHARED"):
        pytest.skip("interpreter is not an --enable-shared build")
    soname = sysconfig.get_config_var("INSTSONAME")
    assert soname in libpython_dependencies(os.path.realpath(sys.executable))
