#pragma once

#include "FreeRTOS.h"
#include "portmacro.h"
#include "task.h"

/**
 * @brief Initialize UART command handler (interrupt + pause task)
 * @param game_handle Game task handle (for suspend/resume)
 * @return E_SUCCESS on success, else error code
 * @see mxc_errors.h
 */
const BaseType_t uart_cmd_init(TaskHandle_t game_handle);
