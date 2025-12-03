#pragma once

#include <mxc_errors.h>
#include <stdbool.h>
#include <stdint.h>

/**
 * @brief io_expander = MAX7325 "Pin Multiplier" Chip
 *
 * This chip adds 16 new plugs (using I2C) with:
 * - 8 inputs pins (buttons)
 * - 8 output pins (LEDs)
 */

#define BUTTON_COUNT 8
#define LED_COUNT 8

#define I2C_MASTER MXC_I2C2
#define I2C_FREQ MXC_I2C_STD_MODE

#define ADDR_IN 0x68  // Buttons
#define ADDR_OUT 0x58 // LEDs

#define BTN_HW_STATE 0xFF // Active low -> 1 = released, 0 = pressed
#define LED_HW_STATE 0x00

/**
 * @brief Wake up the chip and get it ready
 *
 * @return E_SUCCESS on success, else error code
 * @see mxc_errors.h
 */
int io_expander_init(void);

/**
 * @brief Shutdown the I2C peripheral
 *
 * @return E_SUCCESS on success, else error code
 */
int io_expander_deinit(void);

/**
 * @brief Read button states
 * @param button_state To store updated button state in
 *
 * @return E_SUCCESS on success, else error code
 * @see mxc_errors.h
 */
int io_expander_read_btns(uint8_t* button_state);

/**
 * @brief Write LED ouputs
 *
 * @param led_pattern New LED state (e.g., 10000001 turns on the first and last LED)
 *
 * @return E_SUCCESS on success, else error code
 * @see mxc_errors.h
 */
int io_expander_write_leds(uint8_t led_pattern);

/**
 * @brief Check if a button is pressed
 *
 * @param btn Button to check (0-7)
 * @param hardware_state Button state from last read
 *
 * @return true if pressed, false if not
 * @see io_expander_read_btns
 */
bool is_btn_pressed(uint8_t btn, uint8_t hardware_state);

/**
 * @brief Update led_pattern to turn on a given LED
 * @note Call `io_expander_write_leds(uint8_t)` to write to the chip
 *
 * @param led Which LED (0-7)
 * @param led_pattern Updated LED pattern with given LED turned on
 */
void led_on(uint8_t led, uint8_t* led_pattern);

/**
 * @brief Update led_pattern to turn off a given LED
 * @note Call `io_expander_write_leds(uint8_t)` to write to the chip
 *
 * @param led Which LED (0-7)
 * @param led_pattern Updated LED pattern with given LED turned off
 */
void led_off(uint8_t led, uint8_t* led_pattern);

/** @brief Update led_pattern to turn off all LEDs */
void all_led_off(uint8_t* led_pattern);
