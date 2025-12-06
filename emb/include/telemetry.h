#pragma once

#include <stdint.h>

/* Placeholder hooks to integrate MQTT-based telemetry without blocking gameplay.
 * Replace printf stubs with queue-to-MQTT-task once the transport is wired. */
void send_game_event_stub(uint8_t level,
                          uint32_t pop_index,
                          const char* outcome,
                          uint32_t reaction_ms,
                          uint8_t lives_left);

void send_status_stub(const char* state, uint8_t level, uint32_t pop_index, uint8_t lives_left);
