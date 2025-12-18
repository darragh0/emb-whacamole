/**
 * @brief Agent task: handles UART communication with Python bridge (agent/)
 *
 * - Reads events from event_queue, sends as JSON over UART
 * - Responds to identify (b"I") requests from bridge
 */

#pragma once

#include <stdbool.h>

/** @brief Set by UART ISR when identify command received */
extern volatile bool identify_requested;

/** @brief FreeRTOS task entry point */
void agent_task(void* param);
