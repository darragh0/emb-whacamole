/**
 * @file pause.c
 * @brief Pause/resume control using FreeRTOS task notifications and ISR
 *
 * Demonstrates key FreeRTOS patterns:
 * 1. Task Notifications - Lightweight synchronization (faster than queues/semaphores)
 * 2. ISR-safe operations - xTaskNotifyFromISR() with yield handling
 * 3. Task suspend/resume - Direct task control using handles
 * 4. Interrupt-driven I/O - UART RX interrupt triggers pause logic
 *
 * Architecture:
 * UART RX Interrupt ('P' received) -> xTaskNotifyFromISR() -> Pause Task wakes
 * Pause Task -> vTaskSuspend()/vTaskResume() -> Game Task paused/resumed
 */

#include "pause.h"
#include "board.h"
#include "nvic_table.h"
#include "portmacro.h"
#include "uart.h"
#include <stdbool.h>
#include <stdint.h>

// Task handles for suspend/resume operations
// Must be static globals so ISR and pause_task can access them
static TaskHandle_t game_task_handle;   // Handle to game task (for suspend/resume)
static TaskHandle_t pause_task_handle;  // Handle to pause task (for notifications)
static bool paused = false;             // Current pause state

/**
 * @brief UART RX interrupt handler - Triggers pause on 'P' character
 *
 * ISR Safety Rules:
 * - Must be fast - Don't do heavy work in ISR context
 * - Use FromISR() variants - Regular FreeRTOS calls are NOT ISR-safe
 * - Handle task yields - Higher priority task may become ready
 *
 * Task Notification Pattern:
 * Instead of using a queue or semaphore (which have overhead), we use
 * direct task notifications. This is the fastest FreeRTOS synchronization
 * primitive (~45% faster than binary semaphores).
 *
 * @note This ISR is registered in pause_init() via MXC_NVIC_SetVector()
 */
void UART_Handler(void) {
    mxc_uart_regs_t* uart = MXC_UART_GET_UART(CONSOLE_UART);

    // Clear interrupt flags to prevent re-triggering
    uint32_t flags = MXC_UART_GetFlags(uart);
    MXC_UART_ClearFlags(uart, flags);

    // Process all available characters in RX FIFO
    while (MXC_UART_GetRXFIFOAvailable(uart) > 0) {
        int c = MXC_UART_ReadCharacterRaw(uart);

        // 'P' command toggles pause state
        if (c == 'P') {
            BaseType_t woken = pdFALSE;  // OUT: Set to pdTRUE if task should yield

            /**
             * xTaskNotifyFromISR() - Wake pause_task immediately
             *
             * Parameters:
             * - pause_task_handle: Task to notify
             * - 0: Notification value (unused, we just need wake signal)
             * - eNoAction: Don't modify task's notification value
             * - &woken: Set if higher-priority task became ready
             *
             * This unblocks pause_task from xTaskNotifyWait().
             * Since pause_task has highest priority (4), it will preempt current task.
             */
            xTaskNotifyFromISR(pause_task_handle, 0, eNoAction, &woken);

            /**
             * portYIELD_FROM_ISR() - Trigger context switch if needed
             *
             * If woken == pdTRUE, a higher priority task is now ready.
             * This macro requests immediate context switch after ISR returns.
             * Without this, the task switch would be delayed until next tick.
             */
            portYIELD_FROM_ISR(woken);
        }
    }
}

/**
 * @brief Pause task - Highest priority task that toggles game pause state
 *
 * Task Behavior:
 * - Blocks indefinitely waiting for notification from UART ISR
 * - When notified, toggles game task between suspended/running
 * - Returns to blocked state until next notification
 *
 * Priority: configMAX_PRIORITIES - 1 (Priority 4)
 * This is the highest priority task, ensuring immediate response to pause commands.
 * When notification arrives from ISR, this task preempts all others.
 *
 * @param param Unused task parameter (required by FreeRTOS task signature)
 */
static void pause_task(void* const param) {
    (void)param;  // Suppress unused parameter warning

    // Task main loop - never exits
    while (true) {
        /**
         * xTaskNotifyWait() - Block until notification received
         *
         * Parameters:
         * - 0: Don't clear bits on entry
         * - 0: Don't clear bits on exit
         * - NULL: Don't retrieve notification value (we don't use it)
         * - portMAX_DELAY: Wait forever (no timeout)
         *
         * This puts the task in Blocked state, consuming no CPU.
         * Task only consumes CPU when UART interrupt sends notification.
         * More efficient than polling or using a queue.
         */
        xTaskNotifyWait(0, 0, NULL, portMAX_DELAY);

        // Notification received - Toggle pause state
        if (paused) {
            // Resume game task - Moves it from Suspended to Ready state
            // Game will start running again on next scheduler tick
            vTaskResume(game_task_handle);
            paused = false;
        } else {
            // Suspend game task - Removes it from scheduler
            // Game task stops executing immediately, even if higher priority than others
            // Only way to wake it is vTaskResume() - tick interrupts won't wake it
            vTaskSuspend(game_task_handle);
            paused = true;
        }

        // Loop back to xTaskNotifyWait() - Block until next pause command
    }
}

/**
 * @brief Initialize pause system: Create task, configure UART interrupt
 *
 * Setup sequence:
 * 1. Store game task handle for suspend/resume operations
 * 2. Create highest-priority pause task
 * 3. Configure UART to interrupt on RX character
 * 4. Register ISR and enable interrupt in NVIC
 *
 * @param game_handle Handle to game task (obtained from xTaskCreate in main.c)
 * @return E_SUCCESS on success, error code otherwise
 */
BaseType_t pause_init(const TaskHandle_t game_handle) {
    // Store game task handle so pause_task can suspend/resume it
    game_task_handle = game_handle;

    // Create pause task with highest priority
    // Stack: configMINIMAL_STACK_SIZE (128 words) is sufficient - task does minimal work
    // Priority: configMAX_PRIORITIES - 1 ensures immediate response to pause commands
    BaseType_t err = xTaskCreate(
        pause_task,                  // Task function
        "Pause",                     // Name for debugging
        configMINIMAL_STACK_SIZE,    // Stack size (minimal - task is simple)
        NULL,                        // No parameters
        configMAX_PRIORITIES - 1,    // Highest priority (Priority 4)
        &pause_task_handle           // OUT: Handle for task notifications
    );

    if (err != pdPASS) return err;

    // Configure UART hardware for RX interrupts
    mxc_uart_regs_t* uart = MXC_UART_GET_UART(CONSOLE_UART);

    // Trigger interrupt when 1 byte is in RX FIFO (immediate response)
    if ((err = MXC_UART_SetRXThreshold(uart, 1)) != E_SUCCESS) return err;

    // Enable RX threshold interrupt (fires when FIFO >= threshold)
    if ((err = MXC_UART_EnableInt(uart, MXC_F_UART_INT_EN_RX_THD)) != E_SUCCESS) return err;

    // Register our ISR in interrupt vector table
    // MXC_NVIC_SetVector() updates vector table to point to UART_Handler()
    MXC_NVIC_SetVector(MXC_UART_GET_IRQ(CONSOLE_UART), UART_Handler);

    // Enable UART interrupt in NVIC (ARM Cortex-M interrupt controller)
    NVIC_EnableIRQ(MXC_UART_GET_IRQ(CONSOLE_UART));

    return E_SUCCESS;
}
