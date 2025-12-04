#include "scr_utils.h"
#include "utils.h"
#include <stdio.h>

void eprintf(const char* const msg) {
    fprintf(stderr, "%s%s%s", RED, msg, RST);
    MS_SLEEP(500);
}
