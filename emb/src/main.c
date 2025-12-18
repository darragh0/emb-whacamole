#include "agent.h"
#include "game.h"
#include "io_expander.h"
#include "rtos_queues.h"
#include "task.h"
#include "uart_cmd.h"
#include "utils.h"
#include <mxc_errors.h>

#define GAME_TASK_PRIORITY (tskIDLE_PRIORITY + 2)
#define AGENT_TASK_PRIORITY (tskIDLE_PRIORITY + 1)
#define TASK_STACK_SIZE (configMINIMAL_STACK_SIZE * 2) // 256 words per task

#define INIT_SUCCESS 0
#define TRY_INIT(expr, ok, msg, on_fail)                                                           \
    do {                                                                                           \
        err = (expr);                                                                              \
        if (err != (ok)) {                                                                         \
            eputs((msg), err);                                                                     \
            on_fail;                                                                               \
        }                                                                                          \
    } while (0)

/** @brief Initialize all tasks and peripherals */
static long init_all(void) {
    long err;
    TaskHandle_t game_handle;

    TRY_INIT(io_expander_init(), E_SUCCESS, "failed to init MAX7325", return err);
    TRY_INIT(rtos_queues_init(), RTOS_QUEUES_OK, "failed to create queues", goto cleanup);
    TRY_INIT(uart_cmd_init(game_handle), E_SUCCESS, "failed to init uart_cmd", goto cleanup);
    TRY_INIT(
        xTaskCreate(game_task, "Game", TASK_STACK_SIZE, NULL, GAME_TASK_PRIORITY, &game_handle),
        pdPASS,
        "failed to create Game task",
        goto cleanup
    );
    TRY_INIT(
        xTaskCreate(agent_task, "Agent", TASK_STACK_SIZE, NULL, AGENT_TASK_PRIORITY, NULL),
        pdPASS,
        "failed to create Agent task",
        goto cleanup
    );

    return INIT_SUCCESS;

cleanup:
    io_expander_deinit();
    return err;
}

int main(void) {
    // Anti-brick delay: allows debugger to connect before code runs
    for (volatile int _i = 0; _i < 0x3FFFFF; _i++);

    long err = init_all();
    if (err != INIT_SUCCESS) return err;

    vTaskStartScheduler();
    return -1;
}
