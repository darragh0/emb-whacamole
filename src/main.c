/** @brief Shows a pretty LED pattern on startup, then maps button presses to LEDs */

#include <stdint.h>
#include <stdio.h>

#include "io_expander.h"
#include "mxc_errors.h"
#include "stdbool.h"
#include "utils.h"

int main(void) {
    printf("\n\x1b[92m=== \x1b[1;96mButton-to-LED Mapper \x1b[0;92m===\x1b[0m\n");

    if (io_expander_init() != E_SUCCESS) {
        printf("Failed to init MAX7325\n");
        return -1;
    }

    make_leds_look_pretty_n_shi(250, 500);

    int btns_pressed[8] = {false};
    while (true) {
        uint8_t btn_state = 0;
        if (io_expander_read_btns(&btn_state) != E_SUCCESS) break;

        uint8_t led_pattern = 0;
        for (int i = 0; i < BUTTON_COUNT; i++) {
            if (is_btn_pressed(i, btn_state)) {
                led_on(i, &led_pattern);
                if (!btns_pressed[i]) {
                    btns_pressed[i] = true;
                    printf("Button \x1b[96m%d\x1b[0m pressed\n", i);
                }
            } else {
                btns_pressed[i] = false;
            }
        }
        io_expander_write_leds(led_pattern);

        MS_SLEEP(50);
    }

    return 0;
}
