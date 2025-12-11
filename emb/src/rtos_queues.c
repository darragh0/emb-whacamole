/**
 * @file rtos_queues.c
 * @brief FreeRTOS queue initialization for inter-task communication
 *
 * Implements producer-consumer pattern using FreeRTOS queues:
 * - Producer: game_task (emits game events)
 * - Consumer: agent_task (serializes events to UART)
 *
 * FreeRTOS queues provide thread-safe FIFO with automatic blocking:
 * - xQueueSend() blocks producer if queue is full
 * - xQueueReceive() blocks consumer if queue is empty
 * - No manual mutexes needed - queue operations are atomic
 */

#include "rtos_queues.h"

/**
 * Global queue handle for game events
 * Must be global so both game_task and agent_task can access it
 * NULL until initialized by rtos_queues_init()
 */
QueueHandle_t event_queue = NULL;
QueueHandle_t cmd_queue = NULL;

/**
 * @brief Initialize FreeRTOS queues for the application
 *
 * Creates event_queue with capacity for EVENT_QUEUE_LENGTH items.
 * Each item is sizeof(game_event_t) bytes.
 *
 * Queue behavior:
 * - FIFO ordering - Events are consumed in the order they were produced
 * - Copy semantics - Data is copied into/out of queue (no pointers)
 * - Bounded capacity - Prevents unbounded memory growth
 * - Thread-safe - Can be accessed from multiple tasks without corruption
 *
 * Memory allocation:
 * Queue storage is allocated from FreeRTOS heap (configTOTAL_HEAP_SIZE).
 * Total bytes = EVENT_QUEUE_LENGTH * sizeof(game_event_t) + queue overhead
 *
 * @return 0 on success, -1 if queue creation fails (out of heap memory)
 */
int8_t rtos_queues_init(void) {
    // xQueueCreate() allocates queue storage from FreeRTOS heap
    // Returns NULL if insufficient heap memory available
    event_queue = xQueueCreate(EVENT_QUEUE_LENGTH, sizeof(game_event_t));
    if (!event_queue) return -1;  // RTOS_QUEUES_ERROR

    cmd_queue = xQueueCreate(CMD_QUEUE_LENGTH, sizeof(cmd_msg_t));
    if (!cmd_queue) return -1;

    return 0;  // RTOS_QUEUES_OK
}
