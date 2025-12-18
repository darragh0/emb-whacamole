/**
 * @file agent.c
 * @brief Agent task - UART communication (queue consumer)
 *
 * This task implements the consumer side of the producer-consumer pattern:
 * - Producer: game_task sends events to event_queue
 * - Consumer: agent_task reads events from event_queue and sends over UART
 *
 * Priority Design:
 * Agent task runs at lower priority (2) than game task (3), ensuring that
 * UART communication never blocks real-time game logic. If queue fills up,
 * game_task will block briefly, but this is acceptable since it means the
 * game is generating events faster than UART can transmit them.
 *
 * Communication Protocol:
 * Events are serialized to JSON format and sent over UART (stdout).
 * The Python agent bridge receives these messages and forwards to MQTT broker.
 */

#include "agent.h"
#include "mxc_sys.h"
#include "rtos_queues.h"
#include "utils.h"
#include <stdbool.h>
#include <stdio.h>

// Outcome enum -> string mapping for JSON serialization
static const char* const OUTCOME_STR[] = {"hit", "miss", "late"};

// Set by UART ISR when 'I' command received
volatile bool identify_requested = false;

// Agent connection state (used by uart_cmd.c for timeout tracking)
volatile bool agent_connected = false;
volatile TickType_t last_command_tick = 0;

// Ring buffer for offline event storage
typedef struct {
    game_event_t events[EVENT_BUFFER_SIZE];
    uint8_t head;   // next write position
    uint8_t tail;   // next read position
    uint8_t count;  // current item count
} event_ring_buffer_t;

static event_ring_buffer_t event_buffer;

// Forward declaration for flush
static void send_event_json(const game_event_t* event);

void event_buffer_init(void) {
    event_buffer.head = 0;
    event_buffer.tail = 0;
    event_buffer.count = 0;
}

void event_buffer_push(const game_event_t* event) {
    event_buffer.events[event_buffer.head] = *event;
    event_buffer.head = (event_buffer.head + 1) % EVENT_BUFFER_SIZE;
    if (event_buffer.count < EVENT_BUFFER_SIZE) {
        event_buffer.count++;
    } else {
        // Overwrite oldest - advance tail
        event_buffer.tail = (event_buffer.tail + 1) % EVENT_BUFFER_SIZE;
    }
}

bool event_buffer_pop(game_event_t* event) {
    if (event_buffer.count == 0) return false;
    *event = event_buffer.events[event_buffer.tail];
    event_buffer.tail = (event_buffer.tail + 1) % EVENT_BUFFER_SIZE;
    event_buffer.count--;
    return true;
}

uint8_t event_buffer_count(void) {
    return event_buffer.count;
}

void event_buffer_flush(void) {
    game_event_t event;
    while (event_buffer_pop(&event)) {
        send_event_json(&event);
    }
}

/**
 * @brief Serialize game event to JSON and send over UART
 *
 * JSON Protocol:
 * Each event is a single-line JSON object terminated with newline.
 * The Python agent bridge parses these JSON lines and forwards to MQTT.
 *
 * UART Buffering:
 * printf() writes to UART TX buffer, fflush() ensures data is transmitted
 * immediately rather than waiting for buffer to fill. This reduces latency
 * for event delivery to the dashboard.
 *
 * @param event Pointer to game event structure (copied from queue)
 */

#define DEVID_LEN 10

static const char* get_devid(void) {
    static char id[DEVID_LEN + 1];
    static bool initialized = false;

    if (initialized) return id;

    uint8_t usn[MXC_SYS_USN_LEN];
    if (MXC_SYS_GetUSN(usn, NULL) != E_NO_ERROR) return NULL;

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

    initialized = true;
    return id;
}

static void send_identify(void) {
    const char* device_id = get_devid();
    if (!device_id) return;
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

/**
 * @brief Agent task - Drain event queue and send events over UART
 *
 * Task Behavior:
 * 1. Block on queue for up to 10ms waiting for events
 * 2. If event received, send it as JSON over UART
 * 3. Continue draining queue until empty or timeout
 * 4. Sleep for 10ms before checking queue again
 *
 * Queue Consumer Pattern:
 * xQueueReceive() copies data from queue to local variable. This is
 * thread-safe - no race conditions even though game_task is also
 * accessing the queue (via xQueueSend). FreeRTOS handles synchronization.
 *
 * Priority & Blocking:
 * Agent runs at priority 2 (lower than game at priority 3). When agent
 * blocks on xQueueReceive(), game task can run. This ensures UART I/O
 * never delays real-time game logic.
 *
 * Timeout Strategy:
 * 10ms timeout prevents agent from blocking forever if no events arrive.
 * The MS_SLEEP(10) after draining gives other tasks CPU time and reduces
 * unnecessary queue checking when system is idle.
 *
 * @param param Unused task parameter (required by FreeRTOS task signature)
 */
void agent_task(void* const param) {
    (void)param;

    event_buffer_init();
    game_event_t event;

    while (true) {
        // Check for timeout -> mark disconnected
        if (agent_connected &&
            (xTaskGetTickCount() - last_command_tick) > pdMS_TO_TICKS(AGENT_TIMEOUT_MS)) {
            agent_connected = false;
        }

        // Handle identify request from bridge (marks connection)
        if (identify_requested) {
            identify_requested = false;
            agent_connected = true;
            last_command_tick = xTaskGetTickCount();
            event_buffer_flush();  // Flush buffered events on reconnect
            send_identify();
        }

        // Drain event queue
        while (xQueueReceive(event_queue, &event, pdMS_TO_TICKS(10)) == pdTRUE) {
            if (agent_connected) {
                send_event_json(&event);
            } else {
                event_buffer_push(&event);
            }
        }

        MS_SLEEP(10);
    }
}
