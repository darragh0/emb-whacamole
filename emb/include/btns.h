/** @brief Button-related utilities **/

#pragma once

#include <stdbool.h>
#include <stdint.h>

#define BTN_COUNT 8

/**
 * @brief Map logical button index (0-7) to hardware pin number
 * @note 0-3 are on top row, 4-7 are on bottom (left to right)
 */
extern const uint8_t BTN_MAP[];

/**
 * @brief Check if a button is pressed
 * @param btn Button to check (0-7)
 * @param btn_state Button state from last read
 *
 * @return true if pressed, false if not
 */
static inline const bool is_btn_pressed(const uint8_t btn, const uint8_t btn_state) {
    // `!` flip cos active low
    //
    // (1 << pin)            -> Gets the one bit we want
    // hardware_state & ...  -> Ignores all other bits
    return !(btn_state & (1 << BTN_MAP[btn]));
}
