#pragma once

#include "FreeRTOS.h"
#include "game.h"
#include "queue.h"
#include "semphr.h"
#include <stdbool.h>
#include <stdint.h>

#define EVENT_QUEUE_LENGTH 32
#define CMD_QUEUE_LENGTH 8

#define RTOS_QUEUES_OK 0
#define RTOS_QUEUES_ERR -1

typedef enum {
    CMD_SET_LEVEL,
    CMD_RESET,
    CMD_START,
} cmd_type_t;

/** @brief Command sent to the game task */
typedef struct {
    cmd_type_t type;
    uint8_t level;
} cmd_msg_t;

typedef enum {
    EVENT_SESSION_START,
    EVENT_POP_RESULT,
    EVENT_LEVEL_COMPLETE,
    EVENT_SESSION_END,
} event_type_t;

/** @brief Event sent to the bridge/agent */
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
            bool won;
        } session_end;
    } data;
} game_event_t;

extern QueueHandle_t event_queue;
extern QueueHandle_t cmd_queue;

/**
 * @brief Initialize the FreeRTOS queues used by the game task
 * @return 0 on success, -1 on error
 */
const int8_t rtos_queues_init(void);
