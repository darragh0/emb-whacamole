/** @brief Shows a pretty LED pattern on startup, then maps button presses to LEDs */

#include <stdint.h>
#include <stdio.h>

#include "io_expander.h"
#include "mxc_errors.h"
#include "stdbool.h"
#include "utils.h"

static void printbin(uint8_t x) {
    for (int i = 7; i >= 0; i--) {
        putchar(((x >> i) & 1) + '0');
        if (i == 4) putchar(' ');
    }
}

int main(void) {
    printf("\n=== \x1b[96mButton-to-LED Mapper\x1b[0m ===\n\n");

    if (io_expander_init() != E_SUCCESS) {
        printf("\x1b[91merror\x1b[0m: failed to init MAX7325\n");
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
                    printf("\x1b[2m  Button state: ");
                    printbin(btn_state);
                    printf("\n  LED state:    ");
                    printbin(led_pattern);
                    printf("\x1b[0m\n\n");
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
