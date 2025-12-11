/**
 * @brief Agent task: handles UART communication with Python bridge
 *
 * - Reads events from event_queue, sends as JSON over UART
 * - Responds to identify requests from bridge
 */

#pragma once

#include <stdbool.h>

/** @brief Set by UART ISR when 'I' command received */
extern volatile bool identify_requested;

/** @brief FreeRTOS task entry point */
void agent_task(void* param);
