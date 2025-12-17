/** @brief Game logic **/

#pragma once

#include <stdbool.h>

#define LVLS 8
#define LIVES 5
#define RNG_INIT_STATE 0xDEADBEEF

/** @brief Outcome of a single mole pop */
typedef enum {
    POP_HIT,
    POP_MISS,
    POP_LATE,
} pop_outcome_t;

void game_task(void* const param);
