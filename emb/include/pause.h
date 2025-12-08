#pragma once

#include "FreeRTOS.h"
#include "portmacro.h"
#include "task.h"

/**
 * @brief Initialize the pause system (UART interrupt + pause task)
 *
 * @param game_handle Game task handle
 *
 * @return E_SUCCESS on success, else error code
 * @see mxc_errors.h
 */
BaseType_t pause_init(const TaskHandle_t game_handle);
