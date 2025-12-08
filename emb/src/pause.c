#include "pause.h"
#include "board.h"
#include "nvic_table.h"
#include "portmacro.h"
#include "uart.h"
#include <stdbool.h>
#include <stdint.h>

static TaskHandle_t game_task_handle;
static TaskHandle_t pause_task_handle;
static bool paused = false;

void UART_Handler(void) {
    mxc_uart_regs_t* uart = MXC_UART_GET_UART(CONSOLE_UART);
    uint32_t flags = MXC_UART_GetFlags(uart);
    MXC_UART_ClearFlags(uart, flags);

    while (MXC_UART_GetRXFIFOAvailable(uart) > 0) {
        int c = MXC_UART_ReadCharacterRaw(uart);
        if (c == 'P') {
            BaseType_t woken = pdFALSE;
            xTaskNotifyFromISR(pause_task_handle, 0, eNoAction, &woken);
            portYIELD_FROM_ISR(woken);
        }
    }
}

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

BaseType_t pause_init(const TaskHandle_t game_handle) {
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
