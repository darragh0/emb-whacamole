#include "rtos_queues.h"

QueueHandle_t event_queue = NULL;

int8_t rtos_queues_init(void) {
    event_queue = xQueueCreate(EVENT_QUEUE_LENGTH, sizeof(game_event_t));
    if (!event_queue) return -1;
    return 0;
}
