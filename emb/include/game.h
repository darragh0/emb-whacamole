#pragma once

/** @brief Whac-A-Mole game entry point */

/** @brief Pop outcome states */
typedef enum {
    POP_HIT,
    POP_MISS,
    POP_LATE,
} pop_outcome_t;

/** @brief Welcome message */
void welcome(void);

/** @brief Await start of game (wait until any button pressed) */
int await_start(void);

/** @brief Run the complete game (all levels) */
void game_run(void);
