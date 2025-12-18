/**
 * @file uart_cmd.c
 * @brief UART command handler using FreeRTOS task notifications and ISR
 *
 * Commands:
 * - P: Toggle pause (via task notification)
 * - R: Reset game
 * - S: Start game
 * - 1-8: Set level
 * - I: Identify (respond with device ID)
 * - D: Disconnect (mark agent as disconnected, start buffering events)
 *
 * Architecture:
 * UART RX Interrupt -> command dispatch -> task notification or queue
 */

#include "uart_cmd.h"
#include "agent.h"
#include "board.h"
#include "nvic_table.h"
#include "portmacro.h"
#include "rtos_queues.h"
#include "uart.h"
#include <stdbool.h>
#include <stdint.h>

static TaskHandle_t game_task_handle;
static TaskHandle_t pause_task_handle;
static bool paused = false;

/**
 * @brief UART interrupt handler
 * @note reads commands from UART and sends them to game task
 */
void UART_Handler(void) {
    mxc_uart_regs_t* uart = MXC_UART_GET_UART(CONSOLE_UART);
    BaseType_t woken = pdFALSE;

    uint32_t flags = MXC_UART_GetFlags(uart);
    MXC_UART_ClearFlags(uart, flags);

    while (MXC_UART_GetRXFIFOAvailable(uart) > 0) {
        int c = MXC_UART_ReadCharacterRaw(uart);

        // Any command (except D) refreshes connection timeout
        if (c != 'D') {
            last_command_tick = xTaskGetTickCount();
        }

        switch (c) {
            case 'P':
                xTaskNotifyFromISR(pause_task_handle, 0, eNoAction, &woken);
                break;

            case 'D':
                // Disconnect command - mark agent as disconnected (start buffering)
                agent_connected = false;
                break;

            case 'R': {
                const cmd_msg_t cmd = {.type = CMD_RESET};
                xQueueSendFromISR(cmd_queue, &cmd, &woken);
                break;
            }

            case 'S': {
                const cmd_msg_t cmd = {.type = CMD_START};
                xQueueSendFromISR(cmd_queue, &cmd, &woken);
                break;
            }

            case '1' ... '8': {
                const cmd_msg_t cmd = {
                    .type = CMD_SET_LEVEL,
                    .level = (uint8_t)(c - '0'),
                };
                xQueueSendFromISR(cmd_queue, &cmd, &woken);
                break;
            }

            case 'I':
                identify_requested = true;
                break;

            default:
                break;
        }
    }

    portYIELD_FROM_ISR(woken);
}

/** @brief FreeRTOS task to resume/suspend game task */
static void pause_task(void* const param) {
    (void)param;

    while (true) {
        xTaskNotifyWait(0, 0, NULL, portMAX_DELAY);

        if (paused) {
            vTaskResume(game_task_handle);
            paused = false;
        } else {
            vTaskSuspend(game_task_handle);
            paused = true;
        }
    }
}

const BaseType_t uart_cmd_init(const TaskHandle_t game_handle) {
    game_task_handle = game_handle;

    BaseType_t err = xTaskCreate(
        pause_task,
        "Pause",
        configMINIMAL_STACK_SIZE,
        NULL,
        configMAX_PRIORITIES - 1,
        &pause_task_handle
    );
    if (err != pdPASS) return err;

    mxc_uart_regs_t* uart = MXC_UART_GET_UART(CONSOLE_UART);

    if ((err = MXC_UART_SetRXThreshold(uart, 1)) != E_SUCCESS) return err;
    if ((err = MXC_UART_EnableInt(uart, MXC_F_UART_INT_EN_RX_THD)) != E_SUCCESS) return err;

    MXC_NVIC_SetVector(MXC_UART_GET_IRQ(CONSOLE_UART), UART_Handler);
    NVIC_EnableIRQ(MXC_UART_GET_IRQ(CONSOLE_UART));

    return E_SUCCESS;
}
