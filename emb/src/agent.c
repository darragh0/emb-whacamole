#include "agent.h"
#include "mxc_errors.h"
#include "mxc_sys.h"
#include "rtos_queues.h"
#include "utils.h"
#include <stdbool.h>
#include <stdio.h>

static const char* const OUTCOME_STR[] = {"hit", "miss", "late"};

volatile bool identify_requested = false;

// Agent connection state (used by uart_cmd.c for timeout tracking)
volatile bool agent_connected = false;
volatile TickType_t last_cmd_tick = 0;
static event_ring_buffer_t evbuf;

static void send_event_json(const game_event_t* const event);

void evbuf_init(void) {
    evbuf.head = 0;
    evbuf.tail = 0;
    evbuf.count = 0;
}

/** @brief Push event to ring buffer. On overflow, oldest event is silently dropped. */
void evbuf_push(const game_event_t* const event) {
    evbuf.events[evbuf.head] = *event;
    evbuf.head = (evbuf.head + 1) % EVENT_BUFFER_SIZE;
    if (evbuf.count < EVENT_BUFFER_SIZE) {
        evbuf.count++;
    } else {
        evbuf.tail = (evbuf.tail + 1) % EVENT_BUFFER_SIZE;
    }
}

const bool evbuf_pop(game_event_t* const event) {
    if (evbuf.count == 0) return false;
    *event = evbuf.events[evbuf.tail];
    evbuf.tail = (evbuf.tail + 1) % EVENT_BUFFER_SIZE;
    evbuf.count--;
    return true;
}

uint8_t evbuf_count(void) { return evbuf.count; }

void evbuf_flush(void) {
    game_event_t event;
    while (evbuf_pop(&event)) send_event_json(&event);
}

/** @brief Get unique device ID from chip's serial number (last 5 bytes, most distinct). */
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

    evbuf_init();
    game_event_t event;

    while (true) {
        // Check for timeout -> mark disconnected
        if (agent_connected
            && (xTaskGetTickCount() - last_cmd_tick) > pdMS_TO_TICKS(AGENT_TIMEOUT_MS)) {
            agent_connected = false;
        }

        // Handle identify request from bridge (marks connection)
        if (identify_requested) {
            identify_requested = false;
            agent_connected = true;
            last_cmd_tick = xTaskGetTickCount();
            send_identify();
            evbuf_flush();
        }

        // Drain event queue
        while (xQueueReceive(event_queue, &event, pdMS_TO_TICKS(10)) == pdTRUE) {
            if (agent_connected) {
                send_event_json(&event);
            } else {
                evbuf_push(&event);
            }
        }

        MS_SLEEP(10);
    }
}
