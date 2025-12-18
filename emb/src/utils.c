#include "utils.h"
#include <stdint.h>
#include <stdio.h>

uint32_t next_rand(uint32_t* const state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

const void eputs(const char* const msg, const long errno) {
    fprintf(stderr, "error: %s (%ld)\n", msg, errno);
}
