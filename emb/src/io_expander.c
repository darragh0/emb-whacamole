#include "io_expander.h"

#include <stdint.h>

#include "i2c.h"
#include "mxc_errors.h"
#include "stdbool.h"

// Weird ahh board pins are scrambled, so these lists unscramble them :D
// "Button 0" is actually connected to "Pin 6" 🫩
static const uint8_t BTN_MAP[] = {
    [0] = 6,
    [1] = 4,
    [2] = 2,
    [3] = 1,
    [4] = 7,
    [5] = 5,
    [6] = 3,
    [7] = 0,
};

static const uint8_t LED_MAP[] = {
    [0] = 0,
    [1] = 2,
    [2] = 5,
    [3] = 7,
    [4] = 1,
    [5] = 3,
    [6] = 4,
    [7] = 6,
};

static int _mk_i2c_master_tx(unsigned int addr, uint8_t* buf, bool write) {
    mxc_i2c_req_t tx_details = {
        .i2c = I2C_MASTER,
        .addr = addr,
        .restart = 1,
    };

    if (write) {
        tx_details.tx_buf = buf;
        tx_details.tx_len = sizeof(uint8_t);
    } else {
        tx_details.rx_buf = buf;
        tx_details.rx_len = sizeof(uint8_t);
    }

    return MXC_I2C_MasterTransaction(&tx_details);
}

int io_expander_init(void) {
    int errno = MXC_I2C_Init(I2C_MASTER, true, 0);
    if (errno != E_SUCCESS) return errno;

    int errno2 = MXC_I2C_SetFrequency(I2C_MASTER, I2C_FREQ);
    if (errno2 < 0) {
        MXC_I2C_Shutdown(I2C_MASTER);
        return errno2;
    }

    // Wake up buttons/leds
    uint8_t initial_btn_state = BTN_HW_STATE;
    int errno3 = _mk_i2c_master_tx(ADDR_IN, &initial_btn_state, true);
    if (errno3 != E_SUCCESS) {
        MXC_I2C_Shutdown(I2C_MASTER);
        return errno3;
    }

    uint8_t initial_led_state = LED_HW_STATE;
    return _mk_i2c_master_tx(ADDR_OUT, &initial_led_state, true);
}

int io_expander_deinit(void) { return MXC_I2C_Shutdown(I2C_MASTER); }

int io_expander_read_btns(uint8_t* button_state) { return _mk_i2c_master_tx(ADDR_IN, button_state, false); }

int io_expander_write_leds(uint8_t led_pattern) { return _mk_i2c_master_tx(ADDR_OUT, &led_pattern, true); }

bool is_btn_pressed(const uint8_t btn, uint8_t hardware_state) {
    if (btn >= sizeof(BTN_MAP)) return 0;

    uint8_t pin = BTN_MAP[btn];

    // `!` flip cos active low
    //
    // (1 << pin)            -> Gets the one bit we want
    // hardware_state & ..   -> Ignores all other bits
    return !(hardware_state & (1 << pin));
}

void led_on(uint8_t led, uint8_t* led_pattern) {
    if (led < sizeof LED_MAP) {
        uint8_t pin = LED_MAP[led];
        // (1 << pin)         -> Gets the one bit we want
        // |                  -> Turns switch ON without turning others off
        *led_pattern |= (1 << pin);
    }
}

void led_off(uint8_t led, uint8_t* led_pattern) {
    if (led < sizeof LED_MAP) {
        uint8_t pin = LED_MAP[led];
        // ~(1 << pin)        -> Gets the one bit we want
        // &                  -> Turns switch OFF without turning others on
        *led_pattern &= ~(1 << pin);
    }
}

void all_led_off(uint8_t* led_pattern) { *led_pattern = LED_HW_STATE; }
