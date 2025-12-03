#include "game.h"
#include "io_expander.h"
#include "led.h"
#include "scr_utils.h"
#include "utils.h"
#include <stdio.h>

int await_start(void) {
    uint8_t btn_state = BTN_HW_STATE;
    while (true) {
        uint8_t led_pattern = 0;
        for (int i = 0; i < 8; i++) {
            led_on(i, &led_pattern);
            io_expander_write_leds(led_pattern);

            for (int j = 0; j < 50; j++) {
                MS_SLEEP(10);

                int err = io_expander_read_btns(&btn_state);
                if (err != E_SUCCESS) return err;
                if (btn_state != BTN_HW_STATE) goto start;
            }

            led_off(i, &led_pattern);
        }

        io_expander_write_leds(led_pattern);
    }

start:
    printf("Starting game!\n");
    return E_SUCCESS;
}

void welcome(void) {
    curhide();
    cls();
    printf("===== ");
    cprintf("Whac-A-Mole", 2, BLD, CYN);
    printf("=====\n\nAwaiting button press ...\n");
}
