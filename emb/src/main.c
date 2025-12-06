/** @brief Shows a pretty LED pattern on startup, then maps button presses to LEDs */

#include <stdint.h>
#include <stdio.h>

#include "btn.h"
#include "game.h"
#include "io_expander.h"
#include "led.h"
#include "mxc_errors.h"
#include "scr_utils.h"
#include "telemetry.h"
#include "stdbool.h"
#include "utils.h"

static void random_button_lightup(void) {
    uint32_t rng = 0xDEADBEEF;
    uint8_t level = 1;
    uint8_t lives_left = 5;
    uint32_t pop_index = 0;

    while (true) {
        int target = (int)(next_rand(&rng) % BTN_COUNT);

        uint8_t led_pattern = 0;
        led_on(target, &led_pattern);
        if (io_expander_write_leds(led_pattern) != E_SUCCESS) return;

        send_status_stub("playing", level, pop_index, lives_left);
        printf("Whack-a-mole: light at %d\n", target);

        /* poll until the target button is pressed */
        while (true) {
            uint8_t btn_state = 0;
            if (io_expander_read_btns(&btn_state) != E_SUCCESS) return;

            if (is_btn_pressed(target, btn_state)) {

                io_expander_write_leds(0);
                printf("Hit %d\n", target);
                send_game_event_stub(level, pop_index, "HIT", 0, lives_left);
                pop_index++;
                MS_SLEEP(120);
                break;
            }

            MS_SLEEP(30);
        }
    }
}

int main(void) {
    welcome();
    send_status_stub("idle", 0, 0, 5);

    int errno = io_expander_init();
    if (errno != E_SUCCESS) {
        eprintf("failed to init MAX7325\n");
        return -1;
    }

    await_start();
    random_button_lightup();

    return io_expander_deinit();
}
