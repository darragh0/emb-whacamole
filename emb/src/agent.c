#include "agent.h"
#include "mxc_errors.h"
#include "mxc_sys.h"
#include "rtos_queues.h"
#include "utils.h"
#include <stdbool.h>
#include <stdio.h>

static const char* const OUTCOME_STR[] = {"hit", "miss", "late"};

volatile bool identify_requested = false;

#define DEVICE_ID_LEN 10

static const char* get_device_id(void) {
    static char id[DEVICE_ID_LEN + 1];
    static bool already_called = false;

    if (already_called) return id;

    uint8_t usn[MXC_SYS_USN_LEN];
    if (MXC_SYS_GetUSN(usn, NULL) != E_SUCCESS) return NULL;

    snprintf(
        id,
        sizeof(id),
        "%02x%02x%02x%02x%02x",
        usn[MXC_SYS_USN_LEN - 5],
        usn[MXC_SYS_USN_LEN - 4],
        usn[MXC_SYS_USN_LEN - 3],
        usn[MXC_SYS_USN_LEN - 2],
        usn[MXC_SYS_USN_LEN - 1]
    );

    already_called = true;
    return id;
}

static void send_identify(void) {
    const char* device_id = get_device_id();
    if (device_id == NULL) return;
    printf("{\"event_type\":\"identify\",\"device_id\":\"%s\"}\n", device_id);
    fflush(stdout);
}

static void send_event_json(const game_event_t* const event) {
    switch (event->type) {
        case EVENT_SESSION_START:
            printf("{\"event_type\":\"session_start\"}\n");
            break;

        case EVENT_POP_RESULT:
            printf(
                "{\"event_type\":\"pop_result\",\"mole_id\":%u,\"outcome\":\"%s\","
                "\"reaction_ms\":%u,\"lives\":%u,\"lvl\":%u,\"pop\":%u,\"pops_total\":%u}\n",
                event->data.pop.mole,
                OUTCOME_STR[event->data.pop.outcome],
                event->data.pop.reaction_ms,
                event->data.pop.lives,
                event->data.pop.level,
                event->data.pop.pop_index,
                event->data.pop.pops_total
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
        if (identify_requested) {
            identify_requested = false;
            send_identify();
        }

        while (xQueueReceive(event_queue, &event, pdMS_TO_TICKS(10)) == pdTRUE)
            send_event_json(&event);

        MS_SLEEP(10);
    }
}
