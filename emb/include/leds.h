#pragma once

#include "io_expander.h"
#include <stdint.h>

#define LED_COUNT 8

extern const uint8_t LED_MAP[];

/** @brief LED-related utilities */

/**
 * @brief Update led_pattern to turn on a given LED
 * @note Call `io_expander_write_leds(uint8_t)` to write to the chip
 *
 * @param led Which LED (0-7)
 * @param led_pattern Updated LED pattern with given LED turned on
 */
static inline void led_on(const uint8_t led, uint8_t* const led_pattern) {
    // (1 << pin)         -> Gets the one bit we want
    // |                  -> Turns switch ON without turning others off
    *led_pattern |= (1 << LED_MAP[led]);
}

/**
 * @brief Update led_pattern to turn off a given LED
 * @note Call `io_expander_write_leds(uint8_t)` to write to the chip
 *
 * @param led Which LED (0-7)
 * @param led_pattern Updated LED pattern with given LED turned off
 */
static inline void led_off(const uint8_t led, uint8_t* const led_pattern) {
    // ~(1 << pin)        -> Gets the one bit we want
    // &                  -> Turns switch OFF without turning others on
    *led_pattern &= ~(1 << LED_MAP[led]);
}

/** @brief Write all LEDs to off (hardware state) */
static inline void led_hw_write(void) { io_expander_write_leds(LED_HW_STATE); }

/**
 * @brief Flash pattern for a given number of ms
 *
 * @param led_pattern Pattern to flash
 * @param n_flashes How many times to flash
 * @param ms How many ms to flash for each time
 */
void led_flash(uint8_t led_pattern, const uint8_t n_flashes, const uint32_t ms);
