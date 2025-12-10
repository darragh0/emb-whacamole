#include "agent.h"
#include "game.h"
#include "io_expander.h"
#include "pause.h"
#include "rtos_queues.h"
#include "task.h"
#include "utils.h"
#include <mxc_errors.h>

/**
 * FreeRTOS Task Priority Configuration
 *
 * Priority levels (higher number = higher priority):
 * - Pause Task: configMAX_PRIORITIES - 1 (Priority 4) - Highest priority for immediate response
 * - Game Task:  tskIDLE_PRIORITY + 3   (Priority 3) - Real-time game logic must not be blocked
 * - Agent Task: tskIDLE_PRIORITY + 2   (Priority 2) - Lower priority communication task
 * - Idle Task:  tskIDLE_PRIORITY       (Priority 0) - System idle task
 *
 * This priority scheme ensures:
 * 1. Pause commands preempt everything (safety/control)
 * 2. Game timing remains deterministic (5ms button polling)
 * 3. UART communication doesn't interfere with gameplay
 */
#define GAME_TASK_PRIORITY (tskIDLE_PRIORITY + 3)
#define AGENT_TASK_PRIORITY (tskIDLE_PRIORITY + 2)
#define TASK_STACK_SIZE (configMINIMAL_STACK_SIZE * 2)  // 256 words per task

#define INIT_SUCCESS 0

/**
 * @brief Initialize hardware & create FreeRTOS tasks
 *
 * Initialization sequence is critical:
 * 1. Hardware (I2C expander) - Must be ready before tasks use it
 * 2. FreeRTOS queues - Tasks will block on these queues
 * 3. Game task - Produces events to queue
 * 4. Agent task - Consumes events from queue
 * 5. Pause system - Needs game_handle to suspend/resume game task
 *
 * @return INIT_SUCCESS on success, error code otherwise
 */
static long init_all(void) {
    long err;
    TaskHandle_t game_handle;  // Handle needed for task suspend/resume in pause.c

    // Initialize I2C GPIO expander (MAX7325) for buttons and LEDs
    // This must complete before any task tries to read buttons or control LEDs
    if ((err = io_expander_init()) != E_SUCCESS) {
        eputs("failed to init MAX7325", err);
        return err;
    }

    // Create FreeRTOS queues for inter-task communication
    // event_queue: Game task (producer) -> Agent task (consumer)
    // Implements producer-consumer pattern with thread-safe FIFO
    if ((err = rtos_queues_init()) != RTOS_QUEUES_OK) {
        eputs("failed to create queues", err);
        return err;
    }

    // Create game task - Real-time control thread
    // xTaskCreate() allocates stack from FreeRTOS heap and adds task to ready list
    // Task will start running after vTaskStartScheduler() is called
    if ((err = xTaskCreate(
             game_task,              // Task function pointer
             "Game",                 // Task name (for debugging)
             TASK_STACK_SIZE,        // Stack size in words
             NULL,                   // Task parameters (none)
             GAME_TASK_PRIORITY,     // Priority level (3)
             &game_handle            // OUT: Handle for task control (suspend/resume)
         ))
        != pdPASS) {
        eputs("failed to create Game task", err);
        return -1;
    }

    // Create agent task - UART communication thread (lower priority)
    // No handle needed since this task is never suspended
    if ((err = xTaskCreate(agent_task, "Agent", TASK_STACK_SIZE, NULL, AGENT_TASK_PRIORITY, NULL))
        != pdPASS) {
        eputs("failed to create Agent task", err);
        return -1;
    }

    // Initialize pause system:
    // - Creates highest-priority pause task (Priority 4)
    // - Configures UART interrupt to trigger task notification
    // - Stores game_handle for vTaskSuspend()/vTaskResume() operations
    if ((err = pause_init(game_handle)) != E_SUCCESS) {
        eputs("failed to init Pause ", err);
        return err;
    }

    return INIT_SUCCESS;
}

int main(void) {
    // Anti-brick delay - Gives debugger time to connect before code executes
    // Without this, rapid boot loops can lock out JTAG/SWD access
    for (volatile int _i = 0; _i < 0x3FFFFF; _i++);

    // Initialize all hardware and create FreeRTOS tasks
    long err = init_all();
    if (err != INIT_SUCCESS) return err;

    /**
     * Start FreeRTOS scheduler - This function never returns
     *
     * What happens when scheduler starts:
     * 1. Enables preemptive multitasking with 1ms tick (configTICK_RATE_HZ = 1000)
     * 2. Runs highest-priority ready task (Game task at priority 3)
     * 3. Context switches occur on:
     *    - Tick interrupt (1ms) - Checks for higher priority tasks
     *    - Task blocks (vTaskDelay, xQueueReceive, etc.) - Runs next ready task
     *    - ISR triggers higher priority task (UART interrupt -> Pause task)
     * 4. Idle task runs when all other tasks are blocked (cleans up deleted tasks)
     *
     * From this point, execution is managed by the scheduler, not by sequential code flow.
     */
    vTaskStartScheduler();

    // Should never reach here - vTaskStartScheduler() only returns if insufficient heap
    return -1;
}
