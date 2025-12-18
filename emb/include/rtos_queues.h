/**
 * @details
 * FreeRTOS queues for inter-task communication
 *
 * Two queues:
 * - event_queue:  Game task  -> Agent task (game events to send to dashboard)
 * - cmd_queue:    Agent task -> Game task (commands from dashboard, e.g. pause)
 */

#pragma once

#include "FreeRTOS.h"
#include "game.h"
#include "queue.h"
#include "semphr.h"
#include <stdbool.h>
#include <stdint.h>

/** @brief Maximum events in the event queue */
#define EVENT_QUEUE_LENGTH 32
#define CMD_QUEUE_LENGTH 8

/** @brief Offline event buffer size (~1 game session worth) */
#define EVENT_BUFFER_SIZE 100
/** @brief Agent connection timeout (ms) - mark disconnected if no command received */
#define AGENT_TIMEOUT_MS 60000

#define RTOS_QUEUES_OK 0
#define RTOS_QUEUES_ERR -1

/** @brief Commands coming from dashboard */
typedef enum {
    CMD_SET_LEVEL = 0,
    CMD_RESET,
    CMD_START,
} cmd_type_t;

typedef struct {
    cmd_type_t type;
    uint8_t level;  // 1-8 for CMD_SET_LEVEL (unused for other cmds)
} cmd_msg_t;

/** @brief Type of event sent from game to agent */
typedef enum {
    EVENT_SESSION_START,
    EVENT_POP_RESULT,
    EVENT_LEVEL_COMPLETE,
    EVENT_SESSION_END,
} event_type_t;

/** @brief Game event structure */
typedef struct {
    event_type_t type;
    union {
        struct {
            uint8_t mole;
            pop_outcome_t outcome;
            uint16_t reaction_ms;
            uint8_t lives;
            uint8_t level;
            uint8_t pop_index;
            uint8_t pops_total;
        } pop;
        struct {
            uint8_t level;
        } level_complete;
        struct {
            bool won; // true = win, false = loss
        } session_end;
    } data;
} game_event_t;

// Queue handles (extern - defined in rtos_queues.c)
extern QueueHandle_t event_queue;
extern QueueHandle_t cmd_queue;

// Agent connection state (extern - defined in agent.c)
extern volatile bool agent_connected;
extern volatile TickType_t last_command_tick;

/**
 * @brief Initialize queues
 *
 * @return RTOS_QUEUES_OK on success, RTOS_QUEUES_ERR on failure
 */
int8_t rtos_queues_init(void);

/**
 * @brief Initialize offline event buffer
 */
void event_buffer_init(void);

/**
 * @brief Push event to offline buffer (ring buffer - overwrites oldest if full)
 * @param event Event to push
 */
void event_buffer_push(const game_event_t* event);

/**
 * @brief Pop event from offline buffer
 * @param event Output event
 * @return true if event was popped, false if buffer empty
 */
bool event_buffer_pop(game_event_t* event);

/**
 * @brief Get number of events in offline buffer
 * @return Event count
 */
uint8_t event_buffer_count(void);

/**
 * @brief Flush all buffered events via UART (called on reconnect)
 */
void event_buffer_flush(void);
