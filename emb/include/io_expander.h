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

#define I2C_MASTER MXC_I2C2
#define I2C_FREQ MXC_I2C_STD_MODE

#define ADDR_IN 0x68  // Buttons
#define ADDR_OUT 0x58 // LEDs

#define LED_HW_STATE 0x00
#define BTN_HW_STATE 0xFF

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
