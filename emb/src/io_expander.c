#include "io_expander.h"
#include <i2c.h>
#include <mxc_errors.h>
#include <stdbool.h>
#include <stdint.h>

/**
 * @brief Send a single byte over I2C
 *
 * @param addr I2C address
 * @param buf Byte to send
 * @param write true to write, false to read
 *
 * @return E_SUCCESS on success, else error code
 * @see mxc_errors.h
 */
static int mk_i2c_master_tx(const unsigned int addr, uint8_t* const buf, const bool write) {
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
    int err = MXC_I2C_Init(I2C_MASTER, true, 0);
    if (err != E_SUCCESS) return err;

    err = MXC_I2C_SetFrequency(I2C_MASTER, I2C_FREQ);
    if (err < 0) {
        MXC_I2C_Shutdown(I2C_MASTER);
        return err;
    }

    // Wake up buttons/leds
    uint8_t initial_btn_state = BTN_HW_STATE;
    err = mk_i2c_master_tx(ADDR_IN, &initial_btn_state, true);
    if (err != E_SUCCESS) {
        MXC_I2C_Shutdown(I2C_MASTER);
        return err;
    }

    uint8_t initial_led_state = LED_HW_STATE;
    return mk_i2c_master_tx(ADDR_OUT, &initial_led_state, true);
}

int io_expander_deinit(void) { return MXC_I2C_Shutdown(I2C_MASTER); }

int io_expander_read_btns(uint8_t* const button_state) {
    return mk_i2c_master_tx(ADDR_IN, button_state, false);
}

int io_expander_write_leds(uint8_t led_pattern) {
    return mk_i2c_master_tx(ADDR_OUT, &led_pattern, true);
}
