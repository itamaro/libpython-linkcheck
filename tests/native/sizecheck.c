/* Boundary tests for lpc_size_add(), the overflow check on the total size
   of the DT_NEEDED names. Exits 0 if every case passes. */
#include <stdint.h>
#include <stdio.h>

#include "linkcheck_elf.h"

static int failures = 0;

static void
check(size_t total, size_t len, int expect_rc, size_t expect_total)
{
    size_t t = total;
    int rc = lpc_size_add(&t, len);
    if (rc != expect_rc || t != expect_total) {
        printf("FAIL: lpc_size_add(%zu, %zu) -> rc=%d total=%zu, expected rc=%d total=%zu\n",
               total, len, rc, t, expect_rc, expect_total);
        failures++;
    }
}

int
main(void)
{
    check(0, 0, 0, 0);
    check(0, SIZE_MAX, 0, SIZE_MAX);
    check(SIZE_MAX, 0, 0, SIZE_MAX);
    check(SIZE_MAX - 5, 5, 0, SIZE_MAX);
    check(SIZE_MAX - 5, 6, -1, SIZE_MAX - 5);
    check(SIZE_MAX, 1, -1, SIZE_MAX);
    check(1, SIZE_MAX, -1, 1);
    check(SIZE_MAX / 2 + 1, SIZE_MAX / 2 + 1, -1, SIZE_MAX / 2 + 1);
    check(SIZE_MAX / 2, SIZE_MAX / 2 + 1, 0, SIZE_MAX);
    /* Repeated additions, as for many entries sharing one long string. */
    size_t t = 0;
    size_t len = SIZE_MAX / 3 + 1;
    int rcs[3];
    for (int i = 0; i < 3; i++) {
        rcs[i] = lpc_size_add(&t, len);
    }
    if (rcs[0] != 0 || rcs[1] != 0 || rcs[2] != -1 || t != 2 * len) {
        printf("FAIL: repeated additions: rcs=%d,%d,%d total=%zu\n", rcs[0], rcs[1], rcs[2], t);
        failures++;
    }
    if (failures == 0) {
        printf("sizecheck OK (size_t is %zu bits)\n", sizeof(size_t) * 8);
    }
    return failures != 0;
}
