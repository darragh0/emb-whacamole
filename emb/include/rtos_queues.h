/**
 * @details
 * FreeRTOS queues for inter-task communication
 *
 * Two queues:
 * - event_queue:  Game task  -> Agent task (game events to send to cloud)
 * - cmd_queue:    Agent task -> Game task (commands from cloud, e.g. pause)
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

/** @brief Maximum commands in the command queue */
#define CMD_QUEUE_LENGTH 4

#define RTOS_QUEUES_OK 0
#define RTOS_QUEUES_ERR -1

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
    uint32_t timestamp; // xTaskGetTickCount() value
    union {
        struct {
            uint8_t mole;
            pop_outcome_t outcome;
            uint16_t reaction_ms;
            uint8_t lives;
            uint8_t level;
        } pop;
        struct {
            uint8_t level;
        } level_complete;
        struct {
            bool won; // true = win, false = loss
        } session_end;
    } data;
} game_event_t;

/** @brief Command types from agent to game */
typedef enum {
    CMD_PAUSE,
} command_type_t;

/** @brief Command structure (received from agent) */
typedef struct {
    command_type_t type;
} agent_command_t;

// Queue handles (extern - defined in rtos_queues.c)
extern QueueHandle_t event_queue;
extern QueueHandle_t cmd_queue;

/**
 * @brief Initialize queues
 *
 * @return RTOS_QUEUES_OK on success, RTOS_QUEUES_ERR on failure
 */
int8_t rtos_queues_init(void);
