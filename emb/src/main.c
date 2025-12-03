/** @brief Shows a pretty LED pattern on startup, then maps button presses to LEDs */

#include <stdint.h>
#include <stdio.h>

#include "game.h"
#include "io_expander.h"
#include "mxc_errors.h"
#include "scr_utils.h"
#include "stdbool.h"
#include "utils.h"

static void random_button_lightup(void) {
    uint32_t rng = 0xDEADBEEF;

    while (true) {
        int target = (int)(next_rand(&rng) % BUTTON_COUNT);

        uint8_t led_pattern = 0;
        led_on(target, &led_pattern);
        if (io_expander_write_leds(led_pattern) != E_SUCCESS) return;

        printf("Whack-a-mole: light at %d\n", target);

        /* poll until the target button is pressed */
        while (true) {
            uint8_t btn_state = 0;
            if (io_expander_read_btns(&btn_state) != E_SUCCESS) return;

            if (is_btn_pressed(target, btn_state)) {

                io_expander_write_leds(0);
                printf("Hit %d\n", target);
                MS_SLEEP(120);
                break;
            }

            MS_SLEEP(30);
        }
    }
}

int main(void) {
    welcome();

    int errno = io_expander_init();
    if (errno != E_SUCCESS) {
        eprintf("failed to init MAX7325\n");
        return -1;
    }

    await_start();
    random_button_lightup();

    io_expander_deinit();
    return 0;
}
