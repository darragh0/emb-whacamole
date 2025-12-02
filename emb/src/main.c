/** @brief Shows a pretty LED pattern on startup, then maps button presses to LEDs */

#include <stdint.h>
#include <stdio.h>

#include "io_expander.h"
#include "mxc_errors.h"
#include "stdbool.h"
#include "utils.h"

/* random num generator with simple xorshift so no stdlib/time is required */
static uint32_t rng_state = 0xDEADBEEF;
static uint32_t next_rand(void)
{
    uint32_t x = rng_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    rng_state = x;
    return x;
}


static void random_button_lightup(void)
{
    while (true) {
        int target = (int)(next_rand() % BUTTON_COUNT);

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
    printf("\n=== \x1b[96mButton-to-LED Mapper\x1b[0m ===\n\n");

    if (io_expander_init() != E_SUCCESS) {
        printf("\x1b[91merror\x1b[0m: failed to init MAX7325\n");
        return -1;
    }

    make_leds_look_pretty_n_shi(250, 500);

    
    random_button_lightup();
    return 0;
}
