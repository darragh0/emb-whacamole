#include <btn.h>
#include <stdbool.h>
#include <stdint.h>

// Weird ahh board pins are scrambled
// "Button 0" is actually connected to "Pin 6" 🫩
const uint8_t BTN_MAP[] = {
    [0] = 6,
    [1] = 4,
    [2] = 2,
    [3] = 1,
    [4] = 7,
    [5] = 5,
    [6] = 3,
    [7] = 0,
};

bool is_btn_pressed(const uint8_t btn, uint8_t hardware_state) {
    if (btn >= sizeof(BTN_MAP)) return 0;

    uint8_t pin = BTN_MAP[btn];

    // `!` flip cos active low
    //
    // (1 << pin)            -> Gets the one bit we want
    // hardware_state & ..   -> Ignores all other bits
    return !(hardware_state & (1 << pin));
}
