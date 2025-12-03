#include "utils.h"
#include <scr_utils.h>
#include <stdarg.h>
#include <stdio.h>

void curhide(void) { printf("\033[?25l"); }

void cls(void) { printf("\033[2J"); }

void cprintf(const char* msg, int n_clrs, ...) {
    va_list args;
    va_start(args, n_clrs);
    for (int i = 0; i < n_clrs; i++) {
        printf("%s", va_arg(args, const char*));
    }
    printf("%s%s", msg, RST);
    va_end(args);
}

void eprintf(const char* msg) {
    fprintf(stderr, "%s%s%s", RED, msg, RST);
    MS_SLEEP(500);
}
