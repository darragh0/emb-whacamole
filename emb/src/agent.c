#include "agent.h"
#include "board.h"
#include "rtos_queues.h"
#include "uart.h"
#include "utils.h"
#include <stdio.h>
#include <string.h>

#define RX_BUF_SIZE 128

static char rx_buffer[RX_BUF_SIZE];
static uint8_t rx_index = 0;

static const char* const OUTCOME_STR[] = {"hit", "miss", "late"};

/**
 * @brief Send a game event as JSON over UART
 *
 * @param event Event to send
 */
static void send_event_json(const game_event_t* event) {
    switch (event->type) {
        case EVENT_SESSION_START:
            printf("{\"event_type\":\"session_start\",\"time\":%lu}\n", event->timestamp);
            break;

        case EVENT_POP_RESULT:
            printf(
                "{\"event_type\":\"pop_result\",\"mole_id\":%u,\"outcome\":\"%s\","
                "\"reaction_ms\":"
                "%"
                "u,\"lives\":%u,\"lvl\":%u}\n",
                event->data.pop.mole,
                OUTCOME_STR[event->data.pop.outcome],
                event->data.pop.reaction_ms,
                event->data.pop.lives,
                event->data.pop.level
            );
            break;

        case EVENT_LEVEL_COMPLETE:
            printf(
                "{\"event_type\":\"level_complete\",\"lvl\":%u}\n", event->data.level_complete.level
            );
            break;

        case EVENT_SESSION_END:
            printf("{\"event_type\":\"session_end\",\"w\":%s}\n", TF(event->data.session_end.won));
            break;
    }
    fflush(stdout);
}

/**
 * @brief Process a complete line of JSON received from UART
 *
 * @param line Line to process
 */
static void process_rx_line(const char* line) {
    if (strstr(line, "\"c\":\"pause\"") != NULL) {
        agent_command_t cmd = {.type = CMD_PAUSE};
        xQueueSend(cmd_queue, &cmd, 0);
    }
}

/**
 * @brief Buffer incoming UART characters until a newline is found
 *
 * @param c Character to process
 */
static void process_rx_char(char ch) {
    if (ch == '\n' || ch == '\r') {
        if (rx_index > 0) {
            rx_buffer[rx_index] = '\0';
            process_rx_line(rx_buffer);
            rx_index = 0;
        }
    } else if (rx_index < RX_BUF_SIZE - 1) {
        rx_buffer[rx_index++] = ch;
    }
}

void agent_task(void* param) {
    (void)param;

    mxc_uart_regs_t* uart = MXC_UART_GET_UART(CONSOLE_UART);
    game_event_t event;

    while (true) {
        // Send pending events
        while (xQueueReceive(event_queue, &event, pdMS_TO_TICKS(10)) == pdTRUE)
            send_event_json(&event);

        // Check for incoming UART data
        while (MXC_UART_GetRXFIFOAvailable(uart) > 0) {
            int c = MXC_UART_ReadCharacter(uart);
            if (c >= 0) process_rx_char((char)c);
        }

        MS_SLEEP(10);
    }
}
