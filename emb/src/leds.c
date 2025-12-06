#include "leds.h"
#include "io_expander.h"
#include "utils.h"
#include <stdint.h>

const uint8_t LED_MAP[] = {
    [0] = 0,
    [1] = 2,
    [2] = 5,
    [3] = 7,
    [4] = 1,
    [5] = 3,
    [6] = 4,
    [7] = 6,
};

void led_flash(const uint8_t led_pattern, const uint8_t n_flashes, const uint32_t ms) {
    for (uint8_t i = 0; i < n_flashes; i++) {
        io_expander_write_leds(led_pattern);
        MS_SLEEP(ms);
        io_expander_write_leds(LED_HW_STATE);
        MS_SLEEP(ms);
    }
}
