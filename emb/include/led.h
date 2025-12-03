#pragma once

#include <stdint.h>

#define LED_COUNT 8

/** @brief LED-related utilities */

/**
 * @brief Update led_pattern to turn on a given LED
 * @note Call `io_expander_write_leds(uint8_t)` to write to the chip
 *
 * @param led Which LED (0-7)
 * @param led_pattern Updated LED pattern with given LED turned on
 */
void led_on(const uint8_t led, uint8_t* const led_pattern);

/**
 * @brief Update led_pattern to turn off a given LED
 * @note Call `io_expander_write_leds(uint8_t)` to write to the chip
 *
 * @param led Which LED (0-7)
 * @param led_pattern Updated LED pattern with given LED turned off
 */
void led_off(const uint8_t led, uint8_t* const led_pattern);

/** @brief Update led_pattern to turn off all LEDs */
void all_led_off(uint8_t* const led_pattern);
