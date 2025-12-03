#pragma once

#include <stdbool.h>
#include <stdint.h>

/** @brief Button-related utilities **/

#define BTN_COUNT 8

/**
 * @brief Check if a button is pressed
 *
 * @param btn Button to check (0-7)
 * @param hardware_state Button state from last read
 *
 * @return true if pressed, false if not
 * @see io_expander_read_btns
 */
bool is_btn_pressed(const uint8_t btn, const uint8_t hardware_state);
