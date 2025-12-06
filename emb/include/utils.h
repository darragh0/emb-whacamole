/** @brief Miscellaneous utilities **/

#pragma once

#include "FreeRTOS.h"
#include "task.h"
#include <stdint.h>

#define TF(b) ((b) ? "true" : "false")

#define MS_SLEEP(ms) vTaskDelay(pdMS_TO_TICKS(ms))

/**
 * @brief Get the next random number
 *
 * @param state Random number generator state
 *
 * @return Next random number
 */
uint32_t next_rand(uint32_t* const state);

/**
 * @brief Print error message to stderr
 *
 * @param msg Error message
 * @param errno Error number/code
 */
void eputs(const char* const msg, const long errno);
