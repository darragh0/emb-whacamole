#include "io_expander.h"
#include <led.h>
#include <stdint.h>

// Weird ahh board pins are scrambled
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

void led_on(const uint8_t led, uint8_t* const led_pattern) {
    if (led < sizeof LED_MAP) {
        uint8_t pin = LED_MAP[led];
        // (1 << pin)         -> Gets the one bit we want
        // |                  -> Turns switch ON without turning others off
        *led_pattern |= (1 << pin);
    }
}

void led_off(const uint8_t led, uint8_t* const led_pattern) {
    if (led < sizeof LED_MAP) {
        uint8_t pin = LED_MAP[led];
        // ~(1 << pin)        -> Gets the one bit we want
        // &                  -> Turns switch OFF without turning others on
        *led_pattern &= ~(1 << pin);
    }
}

void all_led_off(uint8_t* const led_pattern) { *led_pattern = LED_HW_STATE; }
