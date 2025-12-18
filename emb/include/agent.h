/**
 * @brief Agent task: handles UART communication with Python bridge (agent/)
 *
 * - Reads events from event_queue, sends as JSON over UART
 * - Responds to identify (b"I") requests from bridge
 */

#pragma once

#include "rtos_queues.h"
#include <stdbool.h>

#define DEVICE_ID_LEN 10

/** @brief Lock-free SPSC ring buffer for offline event storage */
typedef struct {
    game_event_t events[EVENT_BUFFER_SIZE];
    volatile uint8_t head; // next write pos (producer only)
    volatile uint8_t tail; // next read pos (consumer only)
} event_ring_buffer_t;

/** @brief Set by UART ISR when identify command received */
extern volatile bool identify_requested;

/** @brief FreeRTOS task entry point */
void agent_task(void* param);
