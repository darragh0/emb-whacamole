#include "telemetry.h"
#include <stdio.h>

void send_game_event_stub(uint8_t level,
                          uint32_t pop_index,
                          const char* outcome,
                          uint32_t reaction_ms,
                          uint8_t lives_left) {
    /* TODO: enqueue this payload to an MQTT publishing task. */
    printf("[telemetry] pop=%lu level=%u outcome=%s reaction_ms=%lu lives_left=%u\n",
           (unsigned long)pop_index,
           level,
           outcome,
           (unsigned long)reaction_ms,
           lives_left);
}

void send_status_stub(const char* state, uint8_t level, uint32_t pop_index, uint8_t lives_left) {
    /* TODO: publish heartbeat/status over MQTT every few seconds. */
    printf("[status] state=%s level=%u pop_index=%lu lives_left=%u\n",
           state,
           level,
           (unsigned long)pop_index,
           lives_left);
}
