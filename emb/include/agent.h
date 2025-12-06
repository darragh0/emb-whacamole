/**
 * @details
 * Agent task: handles UART communication with Python bridge
 *
 * - Reads events from event_queue, sends as JSON over UART
 * - Reads JSON commands from UART, pushes to cmd_queue
 */

#pragma once

/** @brief FreeRTOS task entry point */
void agent_task(void* param);
