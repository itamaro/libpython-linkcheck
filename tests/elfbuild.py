"""Build minimal synthetic ELF shared objects for parser unit tests.

Layout: [ELF header][program headers][.dynstr][.dynamic][section header 0?]
mapped by one PT_LOAD at a non-zero base address, so DT_STRTAB must be
translated from a virtual address to a file offset.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

DT_NULL, DT_NEEDED, DT_STRTAB, DT_STRSZ, DT_SONAME = 0, 1, 5, 10, 14
PT_LOAD, PT_DYNAMIC, PT_NOTE = 1, 2, 4
BASE = 0x400000


@dataclass
class ElfSpec:
    needed: list[bytes] = field(default_factory=list)
    bits: int = 64
    little: bool = True
    dynamic: bool = True
    strtab: bool = True
    strsz: bool = True
    pn_xnum: bool = False
    strtab_vaddr_override: int | None = None
    extra_dyn: list[tuple[int, int]] = field(default_factory=list)
    extra_note_phdr: bool = True


def build_elf(spec: ElfSpec) -> bytes:  # noqa: PLR0912
    e = "<" if spec.little else ">"
    is64 = spec.bits == 64
    ehsize = 64 if is64 else 52
    phentsize = 56 if is64 else 32
    shentsize = 64 if is64 else 40

    phdr_types = []
    if spec.extra_note_phdr:
        phdr_types.append(PT_NOTE)
    phdr_types.append(PT_LOAD)
    if spec.dynamic:
        phdr_types.append(PT_DYNAMIC)
    phnum = len(phdr_types)
    phoff = ehsize

    strtab = bytearray(b"\0")
    offsets = []
    for name in spec.needed:
        offsets.append(len(strtab))
        strtab += name + b"\0"
    strtab_off = phoff + phnum * phentsize
    dyn_off = (strtab_off + len(strtab) + 7) & ~7

    entries = [(DT_NEEDED, off) for off in offsets]
    if spec.strtab:
        vaddr = spec.strtab_vaddr_override
        entries.append((DT_STRTAB, BASE + strtab_off if vaddr is None else vaddr))
    if spec.strsz:
        entries.append((DT_STRSZ, len(strtab)))
    entries += spec.extra_dyn
    entries.append((DT_NULL, 0))
    dyn = b"".join(struct.pack(e + ("qQ" if is64 else "iI"), t, v) for t, v in entries)

    shoff = dyn_off + len(dyn) if spec.pn_xnum else 0
    total = shoff + shentsize if spec.pn_xnum else dyn_off + len(dyn)

    out = bytearray(total)
    ident = b"\x7fELF" + bytes([2 if is64 else 1, 1 if spec.little else 2, 1]) + bytes(9)
    e_phnum = 0xFFFF if spec.pn_xnum else phnum
    hdr_fmt = e + ("HHIQQQIHHHHHH" if is64 else "HHIIIIIHHHHHH")
    hdr = struct.pack(
        hdr_fmt,
        3,  # ET_DYN
        0x3E if is64 else 0x03,
        1,
        0,
        phoff,
        shoff,
        0,
        ehsize,
        phentsize,
        e_phnum,
        shentsize if spec.pn_xnum else 0,
        0,  # e_shnum
        0,
    )
    out[0:16] = ident
    out[16 : 16 + len(hdr)] = hdr

    for i, p_type in enumerate(phdr_types):
        if p_type == PT_LOAD:
            p_offset, p_vaddr, p_filesz = 0, BASE, total
        elif p_type == PT_DYNAMIC:
            p_offset, p_vaddr, p_filesz = dyn_off, BASE + dyn_off, len(dyn)
        else:
            p_offset, p_vaddr, p_filesz = 0, 0, 0
        if is64:
            ph = struct.pack(e + "IIQQQQQQ", p_type, 4, p_offset, p_vaddr, p_vaddr, p_filesz,
                             p_filesz, 8)  # fmt: skip
        else:
            ph = struct.pack(e + "IIIIIIII", p_type, p_offset, p_vaddr, p_vaddr, p_filesz,
                             p_filesz, 4, 4)  # fmt: skip
        out[phoff + i * phentsize : phoff + (i + 1) * phentsize] = ph

    out[strtab_off : strtab_off + len(strtab)] = strtab
    out[dyn_off : dyn_off + len(dyn)] = dyn

    if spec.pn_xnum:
        # Section header 0 carries the real program header count in sh_info.
        if is64:
            sh0 = struct.pack(e + "IIQQQQIIQQ", 0, 0, 0, 0, 0, 0, 0, phnum, 0, 0)
        else:
            sh0 = struct.pack(e + "IIIIIIIIII", 0, 0, 0, 0, 0, 0, 0, phnum, 0, 0)
        out[shoff : shoff + shentsize] = sh0
    return bytes(out)


def dynamic_offset(data: bytes) -> int:
    """File offset of the .dynamic contents in an image produced by build_elf."""
    is64 = data[4] == 2
    e = "<" if data[5] == 1 else ">"
    phoff = struct.unpack_from(e + ("Q" if is64 else "I"), data, 32 if is64 else 28)[0]
    phentsize, phnum = struct.unpack_from(e + "HH", data, 54 if is64 else 42)
    for i in range(phnum):
        base = phoff + i * phentsize
        p_type = struct.unpack_from(e + "I", data, base)[0]
        if p_type == PT_DYNAMIC:
            return struct.unpack_from(e + ("Q" if is64 else "I"), data, base + (8 if is64 else 4))[
                0
            ]
    raise ValueError("no PT_DYNAMIC")
