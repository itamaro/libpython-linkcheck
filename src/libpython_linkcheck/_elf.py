"""Minimal, dependency-free reader for an ELF object's own DT_NEEDED entries.

The reader follows the dynamic loader's view of the file: program headers,
the PT_DYNAMIC segment, and DT_STRTAB translated to a file offset through the
PT_LOAD segments. It does not use section headers, so it works on objects
whose section table was stripped. Every read is bounds-checked against the
file size; malformed input raises :class:`ELFError`, never ``struct.error``
or ``IndexError``.

Only the object's *own* DT_NEEDED entries are reported. Transitive
dependencies are deliberately ignored.
"""

from __future__ import annotations

import os
import re
import struct
from typing import BinaryIO

ELF_MAGIC = b"\x7fELF"

_ELFCLASS32 = 1
_ELFCLASS64 = 2
_ELFDATA2LSB = 1
_ELFDATA2MSB = 2

_PT_LOAD = 1
_PT_DYNAMIC = 2
_PN_XNUM = 0xFFFF

_DT_NULL = 0
_DT_NEEDED = 1
_DT_STRTAB = 5
_DT_STRSZ = 10

# Matches the file name of every libpython variant CPython has shipped:
#   libpython3.so               Stable ABI forwarding library
#   libpython3.12.so.1.0        versioned (the SONAME of --enable-shared builds)
#   libpython3.13t.so.1.0       free-threaded
#   libpython3.12d.so, ...7m.so ABI-flagged (debug, pymalloc) builds
#   libpython2.7.so.1.0         legacy
_LIBPYTHON_RE = re.compile(r"libpython[0-9]+(?:\.[0-9]+)?[a-z]*\.so(?:\.[0-9]+)*")


class ELFError(ValueError):
    """The file is not a well-formed ELF object."""


class NotELFError(ELFError):
    """The file does not start with the ELF magic number."""


def is_libpython(needed: str) -> bool:
    """Return True if a DT_NEEDED entry names a libpython shared library.

    Entries containing a path (``/usr/lib/libpython3.12.so.1.0``) are matched
    on their final component.
    """
    return _LIBPYTHON_RE.fullmatch(needed.rpartition("/")[2]) is not None


def read_needed(path: str | os.PathLike[str] | os.PathLike[bytes] | bytes) -> list[str]:
    """Return the DT_NEEDED entries of the ELF object at *path*, in order.

    Returns an empty list for an ELF object without a dynamic segment.
    Raises :class:`NotELFError` if the file is not ELF, :class:`ELFError` if it
    is malformed, and :class:`OSError` if it cannot be read.
    """
    with open(path, "rb") as f:
        return _read_needed(f)


def libpython_dependencies(
    path: str | os.PathLike[str] | os.PathLike[bytes] | bytes,
) -> list[str]:
    """Return the DT_NEEDED entries of the ELF object at *path* that name libpython."""
    return [name for name in read_needed(path) if is_libpython(name)]


class _Reader:
    def __init__(self, f: BinaryIO) -> None:
        self._f = f
        self.size = os.fstat(f.fileno()).st_size

    def read(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ELFError(
                f"read of {length} bytes at offset {offset} is outside the file "
                f"({self.size} bytes); truncated or corrupt ELF"
            )
        self._f.seek(offset)
        data = self._f.read(length)
        if len(data) != length:
            raise ELFError("short read; file changed while reading")
        return data


class _Layout:
    """Struct layouts for one ELF class/byte order."""

    def __init__(self, ident: bytes) -> None:
        ei_class, ei_data = ident[4], ident[5]
        if ei_data == _ELFDATA2LSB:
            e = "<"
        elif ei_data == _ELFDATA2MSB:
            e = ">"
        else:
            raise ELFError(f"unknown ELF data encoding {ei_data}")
        self.word = struct.Struct(e + "I")
        if ei_class == _ELFCLASS64:
            self.ehdr = struct.Struct(e + "HHIQQQIHHHHHH")
            self.phdr = struct.Struct(e + "IIQQQQQQ")
            self.dyn = struct.Struct(e + "qQ")
            # positions of (p_type, p_offset, p_vaddr, p_filesz) in a phdr
            self.ph_fields = (0, 2, 3, 5)
            self.sh_info_offset = 44
        elif ei_class == _ELFCLASS32:
            self.ehdr = struct.Struct(e + "HHIIIIIHHHHHH")
            self.phdr = struct.Struct(e + "IIIIIIII")
            self.dyn = struct.Struct(e + "iI")
            self.ph_fields = (0, 1, 2, 4)
            self.sh_info_offset = 28
        else:
            raise ELFError(f"unknown ELF class {ei_class}")


def _read_needed(f: BinaryIO) -> list[str]:
    ident = f.read(16)
    if len(ident) < 16 or ident[:4] != ELF_MAGIC:
        raise NotELFError("not an ELF file")
    layout = _Layout(ident)
    r = _Reader(f)
    loads, dynamic = _segments(r, layout)
    if dynamic is None:
        return []  # statically linked: no DT_NEEDED
    needed_offsets, strtab_vaddr, strsz = _dynamic_entries(r.read(*dynamic), layout)
    if not needed_offsets:
        return []
    if strtab_vaddr is None:
        raise ELFError("DT_NEEDED present but no DT_STRTAB")
    strtab = _string_table(r, loads, strtab_vaddr, strsz)
    names = []
    for off in needed_offsets:
        end = strtab.find(b"\0", off)
        if off >= len(strtab) or end < 0:
            raise ELFError(f"DT_NEEDED string offset {off} is outside DT_STRTAB")
        names.append(os.fsdecode(strtab[off:end]))
    return names


def _segments(
    r: _Reader, layout: _Layout
) -> tuple[list[tuple[int, int, int]], tuple[int, int] | None]:
    """Return ([(vaddr, offset, filesz) for PT_LOAD], (offset, filesz) of PT_DYNAMIC)."""
    (_, _, _, _, phoff, shoff, _, _, phentsize, phnum, shentsize, _, _) = layout.ehdr.unpack(
        r.read(16, layout.ehdr.size)
    )
    if phnum == _PN_XNUM:
        # The real count is in sh_info of section header 0.
        if shoff == 0 or shentsize < layout.sh_info_offset + 4:
            raise ELFError("e_phnum is PN_XNUM but there is no section header 0")
        (phnum,) = layout.word.unpack(r.read(shoff + layout.sh_info_offset, 4))
    if phnum == 0:
        return [], None
    if phentsize < layout.phdr.size:
        raise ELFError(f"e_phentsize {phentsize} is smaller than a program header")
    table = r.read(phoff, phentsize * phnum)
    loads: list[tuple[int, int, int]] = []
    dynamic: tuple[int, int] | None = None
    t_i, off_i, va_i, sz_i = layout.ph_fields
    for i in range(phnum):
        fields = layout.phdr.unpack_from(table, i * phentsize)
        if fields[t_i] == _PT_LOAD:
            loads.append((fields[va_i], fields[off_i], fields[sz_i]))
        elif fields[t_i] == _PT_DYNAMIC and dynamic is None:
            dynamic = (fields[off_i], fields[sz_i])
    return loads, dynamic


def _dynamic_entries(data: bytes, layout: _Layout) -> tuple[list[int], int | None, int | None]:
    """Return (DT_NEEDED string offsets, DT_STRTAB address, DT_STRSZ)."""
    needed: list[int] = []
    strtab: int | None = None
    strsz: int | None = None
    for tag, val in layout.dyn.iter_unpack(data[: len(data) - len(data) % layout.dyn.size]):
        if tag == _DT_NULL:
            break
        if tag == _DT_NEEDED:
            needed.append(val)
        elif tag == _DT_STRTAB:
            strtab = val
        elif tag == _DT_STRSZ:
            strsz = val
    return needed, strtab, strsz


def _string_table(
    r: _Reader, loads: list[tuple[int, int, int]], vaddr: int, size: int | None
) -> bytes:
    for seg_vaddr, seg_offset, seg_filesz in loads:
        if seg_vaddr <= vaddr < seg_vaddr + seg_filesz:
            offset = vaddr - seg_vaddr + seg_offset
            if size is None:
                size = seg_offset + seg_filesz - offset
            return r.read(offset, min(size, max(r.size - offset, 0)))
    raise ELFError(f"DT_STRTAB address {vaddr:#x} is not in any PT_LOAD segment")
