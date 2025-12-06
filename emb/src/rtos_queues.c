#include "rtos_queues.h"

QueueHandle_t event_queue = NULL;
QueueHandle_t cmd_queue = NULL;

int8_t rtos_queues_init(void) {
    event_queue = xQueueCreate(EVENT_QUEUE_LENGTH, sizeof(game_event_t));
    cmd_queue = xQueueCreate(CMD_QUEUE_LENGTH, sizeof(agent_command_t));

    if (!event_queue || !cmd_queue) return -1;
    return 0;
}
