#include "agent.h"
#include "rtos_queues.h"
#include "utils.h"
#include <stdio.h>

static const char* const OUTCOME_STR[] = {"hit", "miss", "late"};

/**
 * @brief Send a game event as JSON over UART
 *
 * @param event Event to send
 */
static void send_event_json(const game_event_t* event) {
    switch (event->type) {
        case EVENT_SESSION_START:
            printf("{\"event_type\":\"session_start\",\"time\":%lu}\n", event->timestamp);
            break;

        case EVENT_POP_RESULT:
            printf(
                "{\"event_type\":\"pop_result\",\"mole_id\":%u,\"outcome\":\"%s\","
                "\"reaction_ms\":"
                "%"
                "u,\"lives\":%u,\"lvl\":%u}\n",
                event->data.pop.mole,
                OUTCOME_STR[event->data.pop.outcome],
                event->data.pop.reaction_ms,
                event->data.pop.lives,
                event->data.pop.level
            );
            break;

        case EVENT_LEVEL_COMPLETE:
            printf(
                "{\"event_type\":\"lvl_complete\",\"lvl\":%u}\n", event->data.level_complete.level
            );
            break;

        case EVENT_SESSION_END:
            printf(
                "{\"event_type\":\"session_end\",\"win\":%s}\n", TF(event->data.session_end.won)
            );
            break;
    }
    fflush(stdout);
}

void agent_task(void* const param) {
    (void)param;
    game_event_t event;

    while (true) {
        while (xQueueReceive(event_queue, &event, pdMS_TO_TICKS(10)) == pdTRUE)
            send_event_json(&event);
        MS_SLEEP(10);
    }
}
