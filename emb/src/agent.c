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
#include "rtos_queues.h"
#include "utils.h"
#include <stdio.h>

// Outcome enum -> string mapping for JSON serialization
static const char* const OUTCOME_STR[] = {"hit", "miss", "late"};

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
 * for event delivery to the cloud.
 *
 * @param event Pointer to game event structure (copied from queue)
 */
static void send_event_json(const game_event_t* const event) {
    // Serialize event based on type
    switch (event->type) {
        case EVENT_SESSION_START:
            // Game session starting - no additional data
            printf("{\"event_type\":\"session_start\"}\n");
            break;

        case EVENT_POP_RESULT:
            // Individual mole pop result with all game state
            printf(
                "{\"event_type\":\"pop_result\",\"mole_id\":%u,\"outcome\":\"%s\","
                "\"reaction_ms\":%u,\"lives\":%u,\"lvl\":%u,\"pop\":%u,\"pops_total\":%u}\n",
                event->data.pop.mole,                  // Which LED/button (0-7)
                OUTCOME_STR[event->data.pop.outcome],  // hit/miss/late
                event->data.pop.reaction_ms,           // Player reaction time
                event->data.pop.lives,                 // Remaining lives
                event->data.pop.level,                 // Current level (1-8)
                event->data.pop.pop_index,             // Pop number in level
                event->data.pop.pops_total             // Total pops in level (10)
            );
            break;

        case EVENT_LEVEL_COMPLETE:
            // Level successfully completed
            printf(
                "{\"event_type\":\"lvl_complete\",\"lvl\":%u}\n", event->data.level_complete.level
            );
            break;

        case EVENT_SESSION_END:
            // Game over - win or loss
            printf(
                "{\"event_type\":\"session_end\",\"win\":%s}\n", TF(event->data.session_end.won)
            );
            break;
    }

    // Force immediate transmission - Don't wait for buffer to fill
    // This ensures low-latency event delivery to cloud backend
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
    (void)param;  // Suppress unused parameter warning

    game_event_t event;  // Stack-allocated event buffer for queue copy

    // Task main loop - never exits
    while (true) {
        /**
         * Drain event queue burst:
         * Inner while loop processes all pending events before sleeping.
         * This batches UART transmissions for efficiency when events arrive
         * in rapid succession (e.g., during level transitions).
         *
         * xQueueReceive() behavior:
         * - Blocks for up to 10ms if queue is empty
         * - Returns pdTRUE if event was received, pdFALSE on timeout
         * - Copies event data from queue to &event (pass-by-value)
         * - Automatically handles synchronization with game_task
         */
        while (xQueueReceive(event_queue, &event, pdMS_TO_TICKS(10)) == pdTRUE) {
            // Event received from queue - Send as JSON over UART
            send_event_json(&event);

            // Loop continues until queue is empty or timeout
            // If game produces events faster than UART can send, queue will
            // buffer them up to EVENT_QUEUE_LENGTH (32 events). If queue
            // fills, game_task will block briefly on xQueueSend().
        }

        /**
         * Sleep for 10ms before checking queue again
         *
         * vTaskDelay() puts task in Blocked state, allowing other tasks to run.
         * When 10ms elapses, task returns to Ready state and scheduler will
         * run it when no higher-priority tasks are ready.
         *
         * This sleep prevents busy-waiting on empty queue, reducing CPU usage
         * when system is idle (no game events being generated).
         */
        MS_SLEEP(10);
    }
}
