/*
 * libpython-linkcheck: read an ELF object's own DT_NEEDED entries.
 *
 * Follows the loader's view: program headers, PT_DYNAMIC, and DT_STRTAB
 * translated to a file offset through the PT_LOAD segments. Section headers
 * are only consulted for the PN_XNUM program header count. Every read is
 * bounds-checked against the file size with overflow-safe arithmetic.
 */
#ifndef _FILE_OFFSET_BITS
#define _FILE_OFFSET_BITS 64
#endif
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include "linkcheck_elf.h"

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define LPC_PT_LOAD 1
#define LPC_PT_DYNAMIC 2
#define LPC_PN_XNUM 0xFFFF
#define LPC_DT_NULL 0
#define LPC_DT_NEEDED 1
#define LPC_DT_STRTAB 5
#define LPC_DT_STRSZ 10

typedef struct {
    int fd;
    uint64_t size;
    int is64;
    int big_endian;
    const char *detail;
} reader;

typedef struct {
    uint64_t vaddr;
    uint64_t offset;
    uint64_t filesz;
} load_segment;

static uint64_t
get_uint(const reader *r, const unsigned char *p, int width)
{
    uint64_t v = 0;
    for (int i = 0; i < width; i++) {
        int shift = r->big_endian ? 8 * (width - 1 - i) : 8 * i;
        v |= (uint64_t)p[i] << shift;
    }
    return v;
}

/* Read exactly `len` bytes at `off`. Returns LPC_MALFORMED if the range is
   outside the file. */
static lpc_status
read_at(reader *r, uint64_t off, uint64_t len, unsigned char *buf)
{
    if (off > r->size || len > r->size - off) {
        r->detail = "read outside the file; truncated or corrupt ELF";
        return LPC_ERR_MALFORMED;
    }
    uint64_t done = 0;
    while (done < len) {
        ssize_t n = pread(r->fd, buf + done, (size_t)(len - done), (off_t)(off + done));
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            return LPC_ERR_OS;
        }
        if (n == 0) {
            r->detail = "short read; file changed while reading";
            return LPC_ERR_MALFORMED;
        }
        done += (uint64_t)n;
    }
    return LPC_OK;
}

/* Allocate and read `len` bytes at `off` (len may be 0). */
static lpc_status
read_alloc(reader *r, uint64_t off, uint64_t len, unsigned char **out)
{
    *out = NULL;
    if (off > r->size || len > r->size - off) {
        r->detail = "read outside the file; truncated or corrupt ELF";
        return LPC_ERR_MALFORMED;
    }
    if (len > SIZE_MAX - 1) {
        return LPC_ERR_NOMEM;
    }
    unsigned char *buf = malloc((size_t)len + 1);
    if (buf == NULL) {
        return LPC_ERR_NOMEM;
    }
    lpc_status st = read_at(r, off, len, buf);
    if (st != LPC_OK) {
        free(buf);
        return st;
    }
    *out = buf;
    return LPC_OK;
}

static lpc_status
parse(reader *r, lpc_needed *out)
{
    unsigned char ident[16];
    unsigned char ehdr[48];
    lpc_status st;

    if (r->size < 16) {
        r->detail = "not an ELF file";
        return LPC_ERR_NOT_ELF;
    }
    if ((st = read_at(r, 0, 16, ident)) != LPC_OK) {
        return st;
    }
    if (memcmp(ident,
               "\x7f"
               "ELF",
               4) != 0) {
        r->detail = "not an ELF file";
        return LPC_ERR_NOT_ELF;
    }
    if (ident[5] == 1) {
        r->big_endian = 0;
    }
    else if (ident[5] == 2) {
        r->big_endian = 1;
    }
    else {
        r->detail = "unknown ELF data encoding";
        return LPC_ERR_MALFORMED;
    }
    if (ident[4] == 2) {
        r->is64 = 1;
    }
    else if (ident[4] == 1) {
        r->is64 = 0;
    }
    else {
        r->detail = "unknown ELF class";
        return LPC_ERR_MALFORMED;
    }

    /* Field layout after e_ident (offsets relative to byte 16). */
    const int w = r->is64 ? 8 : 4;
    const uint64_t ehdr_size = r->is64 ? 48 : 36;
    const uint64_t phdr_size = r->is64 ? 56 : 32;
    const uint64_t dyn_size = r->is64 ? 16 : 8;
    const uint64_t sh_info_offset = r->is64 ? 44 : 28;
    if ((st = read_at(r, 16, ehdr_size, ehdr)) != LPC_OK) {
        return st;
    }
    const unsigned char *p = ehdr + 8; /* skip e_type, e_machine, e_version */
    p += w;                            /* e_entry */
    uint64_t phoff = get_uint(r, p, w);
    p += w;
    uint64_t shoff = get_uint(r, p, w);
    p += w;
    p += 4 + 2; /* e_flags, e_ehsize */
    uint64_t phentsize = get_uint(r, p, 2);
    uint64_t phnum = get_uint(r, p + 2, 2);
    uint64_t shentsize = get_uint(r, p + 4, 2);

    if (phnum == LPC_PN_XNUM) {
        unsigned char word[4];
        if (shoff == 0 || shentsize < sh_info_offset + 4) {
            r->detail = "e_phnum is PN_XNUM but there is no section header 0";
            return LPC_ERR_MALFORMED;
        }
        if (shoff > UINT64_MAX - sh_info_offset) {
            r->detail = "read outside the file; truncated or corrupt ELF";
            return LPC_ERR_MALFORMED;
        }
        if ((st = read_at(r, shoff + sh_info_offset, 4, word)) != LPC_OK) {
            return st;
        }
        phnum = get_uint(r, word, 4);
    }
    if (phnum == 0) {
        return LPC_OK;
    }
    if (phentsize < phdr_size) {
        r->detail = "e_phentsize is smaller than a program header";
        return LPC_ERR_MALFORMED;
    }

    unsigned char *table = NULL;
    unsigned char *dyn = NULL;
    unsigned char *strtab = NULL;
    load_segment *loads = NULL;
    size_t nloads = 0;

    /* phentsize <= 0xFFFF and phnum <= 0xFFFFFFFF: no overflow. */
    if ((st = read_alloc(r, phoff, phentsize * phnum, &table)) != LPC_OK) {
        goto done;
    }
    loads = calloc((size_t)phnum, sizeof(*loads));
    if (loads == NULL) {
        st = LPC_ERR_NOMEM;
        goto done;
    }
    int have_dynamic = 0;
    uint64_t dyn_offset = 0, dyn_filesz = 0;
    for (uint64_t i = 0; i < phnum; i++) {
        const unsigned char *ph = table + i * phentsize;
        uint64_t p_type = get_uint(r, ph, 4);
        uint64_t p_offset, p_vaddr, p_filesz;
        if (r->is64) {
            p_offset = get_uint(r, ph + 8, 8);
            p_vaddr = get_uint(r, ph + 16, 8);
            p_filesz = get_uint(r, ph + 32, 8);
        }
        else {
            p_offset = get_uint(r, ph + 4, 4);
            p_vaddr = get_uint(r, ph + 8, 4);
            p_filesz = get_uint(r, ph + 16, 4);
        }
        if (p_type == LPC_PT_LOAD) {
            loads[nloads].vaddr = p_vaddr;
            loads[nloads].offset = p_offset;
            loads[nloads].filesz = p_filesz;
            nloads++;
        }
        else if (p_type == LPC_PT_DYNAMIC && !have_dynamic) {
            have_dynamic = 1;
            dyn_offset = p_offset;
            dyn_filesz = p_filesz;
        }
    }
    if (!have_dynamic) {
        st = LPC_OK; /* statically linked: no DT_NEEDED */
        goto done;
    }

    if ((st = read_alloc(r, dyn_offset, dyn_filesz, &dyn)) != LPC_OK) {
        goto done;
    }
    uint64_t ndyn = dyn_filesz / dyn_size;
    uint64_t nneeded = 0, strtab_vaddr = 0, strsz = 0;
    int have_strtab = 0, have_strsz = 0;
    for (uint64_t i = 0; i < ndyn; i++) {
        const unsigned char *d = dyn + i * dyn_size;
        uint64_t tag = get_uint(r, d, w);
        uint64_t val = get_uint(r, d + w, w);
        if (tag == LPC_DT_NULL) {
            break;
        }
        if (tag == LPC_DT_NEEDED) {
            nneeded++;
        }
        else if (tag == LPC_DT_STRTAB) {
            strtab_vaddr = val;
            have_strtab = 1;
        }
        else if (tag == LPC_DT_STRSZ) {
            strsz = val;
            have_strsz = 1;
        }
    }
    if (nneeded == 0) {
        st = LPC_OK;
        goto done;
    }
    if (!have_strtab) {
        r->detail = "DT_NEEDED present but no DT_STRTAB";
        st = LPC_ERR_MALFORMED;
        goto done;
    }

    uint64_t strtab_offset = 0, strtab_len = 0;
    size_t j;
    for (j = 0; j < nloads; j++) {
        const load_segment *seg = &loads[j];
        if (strtab_vaddr >= seg->vaddr && strtab_vaddr - seg->vaddr < seg->filesz) {
            uint64_t delta = strtab_vaddr - seg->vaddr;
            if (seg->offset > UINT64_MAX - delta) {
                r->detail = "read outside the file; truncated or corrupt ELF";
                st = LPC_ERR_MALFORMED;
                goto done;
            }
            strtab_offset = seg->offset + delta;
            if (!have_strsz) {
                strsz = seg->filesz - delta; /* to the end of the segment */
            }
            break;
        }
    }
    if (j == nloads) {
        r->detail = "DT_STRTAB address is not in any PT_LOAD segment";
        st = LPC_ERR_MALFORMED;
        goto done;
    }
    /* Clamp to the end of the file, as the Python reader does. */
    strtab_len = strsz;
    if (strtab_offset <= r->size && strtab_len > r->size - strtab_offset) {
        strtab_len = r->size - strtab_offset;
    }
    if ((st = read_alloc(r, strtab_offset, strtab_len, &strtab)) != LPC_OK) {
        goto done;
    }

    /* Second pass: copy the names. */
    size_t total = 0;
    for (int pass = 0; pass < 2; pass++) {
        size_t pos = 0;
        for (uint64_t i = 0; i < ndyn; i++) {
            const unsigned char *d = dyn + i * dyn_size;
            uint64_t tag = get_uint(r, d, w);
            uint64_t val = get_uint(r, d + w, w);
            if (tag == LPC_DT_NULL) {
                break;
            }
            if (tag != LPC_DT_NEEDED) {
                continue;
            }
            const unsigned char *nul = NULL;
            if (val < strtab_len) {
                nul = memchr(strtab + val, '\0', (size_t)(strtab_len - val));
            }
            if (nul == NULL) {
                r->detail = "DT_NEEDED string offset is outside DT_STRTAB";
                st = LPC_ERR_MALFORMED;
                goto done;
            }
            size_t len = (size_t)(nul - (strtab + val)) + 1;
            if (pass == 0) {
                total += len;
            }
            else {
                memcpy(out->data + pos, strtab + val, len);
                pos += len;
                out->count++;
            }
        }
        if (pass == 0) {
            out->data = malloc(total ? total : 1);
            if (out->data == NULL) {
                st = LPC_ERR_NOMEM;
                goto done;
            }
            out->size = total;
        }
    }
    st = LPC_OK;

done:
    free(table);
    free(loads);
    free(dyn);
    free(strtab);
    if (st != LPC_OK) {
        lpc_needed_free(out);
    }
    return st;
}

lpc_status
lpc_read_needed(const char *path, lpc_needed *out, const char **detail)
{
    reader r = {.fd = -1, .detail = NULL};
    struct stat sb;
    lpc_status st;

    out->data = NULL;
    out->size = 0;
    out->count = 0;
    if (detail != NULL) {
        *detail = NULL;
    }
    do {
        r.fd = open(path, O_RDONLY | O_CLOEXEC);
    } while (r.fd < 0 && errno == EINTR);
    if (r.fd < 0) {
        return LPC_ERR_OS;
    }
    if (fstat(r.fd, &sb) != 0) {
        int saved = errno;
        close(r.fd);
        errno = saved;
        return LPC_ERR_OS;
    }
    if (S_ISDIR(sb.st_mode)) {
        close(r.fd);
        errno = EISDIR;
        return LPC_ERR_OS;
    }
    r.size = sb.st_size < 0 ? 0 : (uint64_t)sb.st_size;
    errno = 0;
    st = parse(&r, out);
    int saved = errno;
    close(r.fd);
    errno = saved;
    if (detail != NULL) {
        *detail = r.detail;
    }
    return st;
}

void
lpc_needed_free(lpc_needed *needed)
{
    free(needed->data);
    needed->data = NULL;
    needed->size = 0;
    needed->count = 0;
}

static int
is_digit(char c)
{
    return c >= '0' && c <= '9';
}

int
lpc_is_libpython(const char *name)
{
    const char *base = strrchr(name, '/');
    const char *s = base ? base + 1 : name;

    if (strncmp(s, "libpython", 9) != 0) {
        return 0;
    }
    s += 9;
    if (!is_digit(*s)) {
        return 0;
    }
    while (is_digit(*s)) {
        s++;
    }
    if (s[0] == '.' && is_digit(s[1])) {
        s++;
        while (is_digit(*s)) {
            s++;
        }
    }
    while (*s >= 'a' && *s <= 'z') {
        s++;
    }
    if (strncmp(s, ".so", 3) != 0) {
        return 0;
    }
    s += 3;
    while (*s == '.') {
        s++;
        if (!is_digit(*s)) {
            return 0;
        }
        while (is_digit(*s)) {
            s++;
        }
    }
    return *s == '\0';
}
