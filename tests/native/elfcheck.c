/*
 * Test harness: run the C DT_NEEDED reader on every path read from stdin
 * (one per line) and print one result line per path:
 *
 *     <status>[ <hex(name)>:<is_libpython>]...
 *
 * Built with -fsanitize=address,undefined by tests/test_native.py so memory
 * errors in linkcheck_elf.c abort the run.
 */
#include <stdio.h>
#include <string.h>

#include "linkcheck_elf.h"

int
main(void)
{
    char path[4096];
    while (fgets(path, sizeof(path), stdin) != NULL) {
        path[strcspn(path, "\n")] = '\0';
        lpc_needed needed;
        const char *detail = NULL;
        lpc_status st = lpc_read_needed(path, &needed, &detail);
        printf("%d", (int)st);
        if (st == LPC_OK) {
            const char *p = needed.data;
            for (size_t i = 0; i < needed.count; i++) {
                size_t len = strlen(p);
                putchar(' ');
                for (size_t j = 0; j < len; j++) {
                    printf("%02x", (unsigned char)p[j]);
                }
                printf(":%d", lpc_is_libpython(p));
                p += len + 1;
            }
            lpc_needed_free(&needed);
        }
        putchar('\n');
    }
    return 0;
}
