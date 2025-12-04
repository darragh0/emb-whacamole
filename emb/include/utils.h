#pragma once

#include <mxc_delay.h>

#define MS_SLEEP(ms) MXC_Delay(MXC_DELAY_MSEC(ms))
#define S_SLEEP(s) MXC_Delay(MXC_DELAY_SEC(s))

/**
 * @brief Random number generator using simple xorshift
 *
 * @param state Random number generator state
 *
 * @return Random number
 * */
uint32_t next_rand(uint32_t* const state);
