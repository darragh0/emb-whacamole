#include "rtos_queues.h"
#include "mxc_errors.h"

QueueHandle_t event_queue = NULL;
QueueHandle_t cmd_queue = NULL;

const int8_t rtos_queues_init(void) {
    event_queue = xQueueCreate(EVENT_QUEUE_LENGTH, sizeof(game_event_t));
    if (!event_queue) return -1;

    cmd_queue = xQueueCreate(CMD_QUEUE_LENGTH, sizeof(cmd_msg_t));
    if (!cmd_queue) {
        vQueueDelete(event_queue);
        event_queue = NULL;
        return -1;
    }

    return E_SUCCESS;
}
