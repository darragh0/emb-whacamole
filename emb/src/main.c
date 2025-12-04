/**
 * @brief Whac-A-Mole game.
 *
 * @details
 * There are 8 levels, each with 10 pops (a pop is when an LED lights up for a given duration).
 * You start of with 5 lives.
 *
 * The duration of a pop ranges from 1500ms (lowest/easiest level) to 250ms (highest/hardest level).
 * Your goal is to hit the corresponding button in time.
 *
 * Pop result:
 *   1. HIT:        Hit the corresponding button in time
 *   2. MISS:       Hit the wrong button                                        (-1 life)
 *   3. LATE:       Hit the corresponding button late OR did nothing in time    (-1 life)
 *
 * The game ends when you run out of lives or when you complete all 8 levels successfully.
 */

#include "game.h"
#include "io_expander.h"
#include "mxc_errors.h"
#include "scr_utils.h"

int main(void) {
    welcome();

    int errno = io_expander_init();
    if (errno != E_SUCCESS) {
        eprintf("failed to init MAX7325\n");
        return errno;
    }

    await_start();
    game_run();

    return io_expander_deinit();
}
