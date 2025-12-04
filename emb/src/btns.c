#include "btns.h"
#include <stdbool.h>
#include <stdint.h>

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
