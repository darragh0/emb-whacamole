#include "agent.h"
#include "game.h"
#include "io_expander.h"
#include "pause.h"
#include "rtos_queues.h"
#include "task.h"
#include "utils.h"
#include <mxc_errors.h>

// Task priorities: Game is higher so it runs without blocking on agent
#define GAME_TASK_PRIORITY (tskIDLE_PRIORITY + 3)
#define AGENT_TASK_PRIORITY (tskIDLE_PRIORITY + 2)
#define TASK_STACK_SIZE (configMINIMAL_STACK_SIZE * 2)

#define INIT_SUCCESS 0

/** @brief Initialize hardware & RTOS tasks */
static long init_all(void) {
    long err;
    TaskHandle_t game_handle;

    // Init IO expander before creating tasks
    if ((err = io_expander_init()) != E_SUCCESS) {
        eputs("failed to init MAX7325", err);
        return err;
    }

    // Create queues for inter-task communication
    if ((err = rtos_queues_init()) != RTOS_QUEUES_OK) {
        eputs("failed to create queues", err);
        return err;
    }

    // Create game task (real-time game logic)
    if ((err = xTaskCreate(game_task, "Game", TASK_STACK_SIZE, NULL, GAME_TASK_PRIORITY,
                           &game_handle)) != pdPASS) {
        eputs("failed to create Game task", err);
        return -1;
    }

    // Create agent task (UART communication -- lower priority)
    if ((err = xTaskCreate(agent_task, "Agent", TASK_STACK_SIZE, NULL, AGENT_TASK_PRIORITY, NULL))
        != pdPASS) {
        eputs("failed to create Agent task", err);
        return -1;
    }

    // Init pause system (UART interrupt + pause task)
    pause_init(game_handle);

    return INIT_SUCCESS;
}

int main(void) {
    // Delay loop to prevent bricking
    for (volatile int _i = 0; _i < 0x3FFFFF; _i++);

    long err = init_all();
    if (err != INIT_SUCCESS) return err;

    vTaskStartScheduler();
}
