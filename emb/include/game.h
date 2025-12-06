/** @brief Game logic **/

#pragma once

#include <stdbool.h>

#define LVLS 8
#define LIVES 5
#define RNG_INIT_STATE 0xDEADBEEF

/** @brief Outcome of a single mole pop */
typedef enum {
    POP_HIT = 0,
    POP_MISS = 1,
    POP_LATE = 2,
} pop_outcome_t;

// Pause state (set by agent task via cmd_queue)
extern volatile bool game_paused;

/** @brief Wait for start button press */
int await_start(void);

/** @brief Run main game loop */
void game_run(void);

/** @brief FreeRTOS task entry point (wraps welcome/await_start/game_run in a loop) **/
void game_task(void* param);
