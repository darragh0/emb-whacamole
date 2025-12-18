#include "game.h"
#include "btns.h"
#include "io_expander.h"
#include "leds.h"
#include "rtos_queues.h"
#include "utils.h"
#include <stdint.h>

static uint8_t lives;
static uint32_t rng_state;
static uint8_t requested_level_idx = 0;
static bool level_change_pending = false;
static bool reset_requested = false;
static bool start_requested = false;
static bool reset_abort_session = false;

static const uint8_t POPS_PER_LVL[8] = {[0 ... 7] = 10};
static const uint16_t POP_DURATIONS[8] = {1500, 1250, 1000, 750, 600, 500, 350, 275};

static void emit_session_start(void) {
    const game_event_t event = {.type = EVENT_SESSION_START};
    xQueueSend(event_queue, &event, 0);
}

static void emit_pop_result(
    const uint8_t mole,
    const pop_outcome_t outcome,
    const uint16_t reaction_ms,
    const uint8_t lvl,
    const uint8_t pop_idx,
    const uint8_t pops_total
) {
    const game_event_t event = {
        .type = EVENT_POP_RESULT,
        .data.pop = {
            .mole = mole,
            .outcome = outcome,
            .reaction_ms = reaction_ms,
            .lives = lives,
            .level = lvl + 1,
            .pop_index = pop_idx,
            .pops_total = pops_total,
        },
    };
    xQueueSend(event_queue, &event, 0);
}

static void emit_level_complete(const uint8_t lvl) {
    const game_event_t event = {
        .type = EVENT_LEVEL_COMPLETE,
        .data.level_complete.level = lvl + 1,
    };
    xQueueSend(event_queue, &event, 0);
}

static void emit_session_end(const bool won) {
    const game_event_t event = {
        .type = EVENT_SESSION_END,
        .data.session_end.won = won,
    };
    xQueueSend(event_queue, &event, 0);
}

static void drain_cmd_queue(void) {
    if (!cmd_queue) return;

    cmd_msg_t cmd;
    while (xQueueReceive(cmd_queue, &cmd, 0) == pdTRUE) {
        switch (cmd.type) {
            case CMD_SET_LEVEL:
                if (cmd.level >= 1 && cmd.level <= LVLS) {
                    requested_level_idx = cmd.level - 1;
                    level_change_pending = true;
                }
                break;
            case CMD_RESET:
                reset_requested = true;
                level_change_pending = false;
                requested_level_idx = 0;
                start_requested = false;
                break;
            case CMD_START:
                start_requested = true;
                break;
        }
    }
}

/** @brief Reset the game state and optionally abort the current session */
static void apply_reset_state(const bool abort_session) {
    reset_requested = false;
    level_change_pending = false;
    start_requested = false;
    requested_level_idx = 0;
    lives = LIVES;
    rng_state = RNG_INIT_STATE;
    reset_abort_session = abort_session;
}

/** @brief Return true if start was requested (skip waiting for button press) */
static inline bool consume_start_request(void) {
    const bool start_now = start_requested;
    start_requested = false;
    return start_now;
}

static inline uint8_t requested_level_or_default(void) {
    return (requested_level_idx < LVLS) ? requested_level_idx : 0;
}

static inline bool should_switch_level(const uint8_t current_level_idx) {
    return level_change_pending && requested_level_idx < LVLS
           && requested_level_idx != current_level_idx;
}

static inline uint8_t consume_requested_level(void) {
    level_change_pending = false;
    return requested_level_or_default();
}

static inline void feedback_late_or_miss(void) { led_flash(0xFF, 1, 100); }
static inline void feedback_game_over(void) { led_flash(0xFF, 3, 500); }
static inline void feedback_win(void) { led_flash(0xFF, 100, 50); }

static void lvl_show(const uint8_t lvl_idx) {
    const uint8_t num_leds = lvl_idx + 1;
    uint8_t led_pattern = 0x00;

    for (uint8_t i = 0; i < num_leds; i++) led_on(i, &led_pattern);

    MS_SLEEP(1000);
    led_flash(led_pattern, 3, 500);
    MS_SLEEP(500);
}

static void pop_wait_delay(uint32_t* const rng_state) {
    const uint32_t delay = 250 + (next_rand(rng_state) % 751);
    MS_SLEEP(delay);
}

static pop_outcome_t pop_do(
    const uint8_t lvl_idx,
    uint32_t* const rng_state,
    uint8_t* out_mole,
    uint16_t* out_reaction_ms
) {
    const uint16_t duration_ms = POP_DURATIONS[lvl_idx];
    const uint8_t target_led = next_rand(rng_state) % LED_COUNT;
    *out_mole = target_led;

    // Debounce: wait for all buttons released (active-low, 0xFF = released)
    uint8_t btn_state;
    uint16_t db_time = 0;
    do {
        io_expander_read_btns(&btn_state);
        if (btn_state != BTN_HW_STATE) {
            MS_SLEEP(10);
            db_time += 10;
            if (db_time > 50) break;
        }
    } while (btn_state != BTN_HW_STATE);

    uint8_t led_pattern = 0;
    led_on(target_led, &led_pattern);
    io_expander_write_leds(led_pattern);

    // Poll buttons at 5ms intervals until hit or timeout
    uint16_t elapsed = 0;
    const uint8_t poll_interval = 5;

    while (elapsed < duration_ms) {
        io_expander_read_btns(&btn_state);

        if (btn_state != BTN_HW_STATE) {
            *out_reaction_ms = elapsed;
            led_hw_write();
            return is_btn_pressed(target_led, btn_state) ? POP_HIT : POP_MISS;
        }

        MS_SLEEP(poll_interval);
        elapsed += poll_interval;
    }

    *out_reaction_ms = duration_ms;
    led_hw_write();
    return POP_LATE;
}

static void game_run_level(const uint8_t lvl_idx, const uint8_t pops) {
    lvl_show(lvl_idx);

    for (int pop = 0; pop < pops; pop++) {
        drain_cmd_queue();
        if (reset_requested) {
            apply_reset_state(true);
            return;
        }
        if (should_switch_level(lvl_idx)) return;

        pop_wait_delay(&rng_state);
        drain_cmd_queue();
        if (reset_requested) {
            apply_reset_state(true);
            return;
        }
        if (should_switch_level(lvl_idx)) return;

        uint8_t mole;
        uint16_t reaction_ms;
        pop_outcome_t outcome = pop_do(lvl_idx, &rng_state, &mole, &reaction_ms);

        if (outcome == POP_HIT) {
            emit_pop_result(mole, outcome, reaction_ms, lvl_idx, pop + 1, pops);
        } else {
            lives--;
            emit_pop_result(mole, outcome, reaction_ms, lvl_idx, pop + 1, pops);
            feedback_late_or_miss();
            if (lives == 0) return;
        }

        if (reset_requested) {
            apply_reset_state(true);
            return;
        }
        if (should_switch_level(lvl_idx)) return;
    }

    emit_level_complete(lvl_idx);
}

/** @brief Wait for the user to start the game, showing "loading" LED pattern */
static int await_start(void) {
    uint8_t btn_state = BTN_HW_STATE;

restart_idle:

    while (true) {
        drain_cmd_queue();
        if (reset_requested) {
            apply_reset_state(false); // No session to abort
            continue;
        }
        if (consume_start_request()) goto success;

        uint8_t led_pattern = 0;
        for (int i = 0; i < 8; i++) {
            led_on(i, &led_pattern);
            io_expander_write_leds(led_pattern);

            for (int j = 0; j < 50; j++) {
                MS_SLEEP(10);
                drain_cmd_queue();
                if (reset_requested) {
                    apply_reset_state(false);
                    goto restart_idle;
                }
                if (consume_start_request()) goto success;

                int err = io_expander_read_btns(&btn_state);
                if (err != E_SUCCESS) return err;
                // If any button is pressed, start game
                if (btn_state != BTN_HW_STATE) goto success;
            }

            led_off(i, &led_pattern);
        }

        io_expander_write_leds(led_pattern);
    }

success:

    led_hw_write();
    return E_SUCCESS;
}

static void game_run(void) {
    lives = LIVES;
    rng_state = RNG_INIT_STATE;
    drain_cmd_queue();
    if (reset_requested) {
        apply_reset_state(false);
        return;
    }

    uint8_t lvl = requested_level_or_default();
    level_change_pending = false;
    start_requested = false;
    emit_session_start();

    while (lvl < LVLS) {
        game_run_level(lvl, POPS_PER_LVL[lvl]);
        if (reset_abort_session) {
            emit_session_end(false);
            reset_abort_session = false;
            return;
        }
        if (lives == 0) {
            emit_session_end(false);
            MS_SLEEP(500);
            feedback_game_over();
            return;
        }

        drain_cmd_queue();
        if (reset_requested) {
            apply_reset_state(true);
            emit_session_end(false);
            reset_abort_session = false;
            return;
        }
        if (level_change_pending) {
            const uint8_t target_lvl = consume_requested_level();
            if (target_lvl != lvl) {
                lvl = target_lvl;
                continue;
            }
        }

        lvl++;
    }

    if (reset_requested) {
        apply_reset_state(true);
        emit_session_end(false);
        reset_abort_session = false;
        return;
    }

    emit_session_end(true);
    MS_SLEEP(500);
    feedback_win();
}

void game_task(void* const param) {
    (void)param;

    while (true) {
        await_start();
        game_run();
        if (reset_abort_session) {
            reset_abort_session = false;
            continue;
        }
        MS_SLEEP(2000);
    }
}
