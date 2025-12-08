#include "game.h"
#include "btns.h"
#include "io_expander.h"
#include "leds.h"
#include "rtos_queues.h"
#include "utils.h"
#include <stdint.h>

static uint8_t lives;
static uint32_t rng_state;

static const uint8_t POPS_PER_LVL[8] = {[0 ... 7] = 10};
static const uint16_t POP_DURATIONS[8] = {1500, 1250, 1000, 750, 600, 500, 350, 275};

/** @brief Queue a session start event */
static void emit_session_start(void) {
    game_event_t event = {
        .type = EVENT_SESSION_START,
        .timestamp = xTaskGetTickCount(),
    };
    xQueueSend(event_queue, &event, 0);
}

/**
 * @brief Queue a pop result event
 *
 * @param mole Mole index
 * @param outcome Outcome of the pop
 * @param reaction_ms Reaction time in ms
 * @param lvl Current level
 */
static void
emit_pop_result(uint8_t mole, pop_outcome_t outcome, uint16_t reaction_ms, uint8_t lvl) {
    game_event_t event = {
        .type = EVENT_POP_RESULT,
        .timestamp = xTaskGetTickCount(),
        .data.pop = {
            .mole = mole,
            .outcome = outcome,
            .reaction_ms = reaction_ms,
            .lives = lives,
            .level = lvl + 1,
        },
    };
    xQueueSend(event_queue, &event, 0);
}

/**
 * @brief Queue a level complete event
 *
 * @param lvl Current level
 */
static void emit_level_complete(uint8_t lvl) {
    game_event_t event = {
        .type = EVENT_LEVEL_COMPLETE,
        .timestamp = xTaskGetTickCount(),
        .data.level_complete.level = lvl + 1,
    };
    xQueueSend(event_queue, &event, 0);
}

/**
 * @brief Queue a session end event
 *
 * @param won Whether session was won
 */
static void emit_session_end(bool won) {
    game_event_t event = {
        .type = EVENT_SESSION_END,
        .timestamp = xTaskGetTickCount(),
        .data.session_end.won = won,
    };
    xQueueSend(event_queue, &event, 0);
}

/** @brief Flash LEDs for late/miss feedback */
static inline void feedback_late_or_miss(void) { led_flash(0xFF, 1, 100); }

/** @brief Flash LEDs for game over feedback */
static inline void feedback_game_over(void) { led_flash(0xFF, 3, 500); }

/** @brief Flash LEDs for win feedback */
static inline void feedback_win(void) { led_flash(0xFF, 100, 50); }

/**
 * @brief Show level start animation
 *
 * @param lvl_idx Level index
 */
static void lvl_show(const uint8_t lvl_idx) {
    uint8_t num_leds = lvl_idx + 1;
    uint8_t led_pattern = 0x00;

    for (uint8_t i = 0; i < num_leds; i++) led_on(i, &led_pattern);

    MS_SLEEP(1000);
    led_flash(led_pattern, 3, 500);
    MS_SLEEP(500);
}

/** @brief Wait a random amount of time before next pop */
static void pop_wait_delay(uint32_t* const rng_state) {
    uint32_t delay = 250 + (next_rand(rng_state) % 751);
    MS_SLEEP(delay);
}

/**
 * @brief Execute a single pop logic
 *
 * @param lvl_idx Current level index
 * @param rng_state RNG state pointer
 * @param out_mole [out] Selected mole index
 * @param out_reaction_ms [out] Reaction time in ms
 * @return Outcome of the pop
 */
static pop_outcome_t pop_do(
    const uint8_t lvl_idx,
    uint32_t* const rng_state,
    uint8_t* out_mole,
    uint16_t* out_reaction_ms
) {
    uint16_t duration_ms = POP_DURATIONS[lvl_idx];
    uint8_t target_led = next_rand(rng_state) % LED_COUNT;
    *out_mole = target_led;

    // Button debounce: wait for all buttons released
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

    // Turn on target LED
    uint8_t led_pattern = 0;
    led_on(target_led, &led_pattern);
    io_expander_write_leds(led_pattern);

    // Poll loop with timeout
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

/** @brief Run a complete level */
static void game_run_level(const uint8_t lvl_idx, const uint8_t pops) {
    lvl_show(lvl_idx);

    for (int pop = 0; pop < pops; pop++) {
        pop_wait_delay(&rng_state);

        uint8_t mole;
        uint16_t reaction_ms;
        pop_outcome_t outcome = pop_do(lvl_idx, &rng_state, &mole, &reaction_ms);

        // printf("  Pop %02d :: ", pop + 1);
        switch (outcome) {
            case POP_HIT:
                // printf("[HIT]  %3d ms\n", reaction_ms);
                emit_pop_result(mole, outcome, reaction_ms, lvl_idx);
                continue;
            case POP_MISS:
                // printf("[MISS]");
                break;
            case POP_LATE:
                // printf("[LATE]");
                break;
        }

        lives--;
        emit_pop_result(mole, outcome, reaction_ms, lvl_idx);
        // printf("      (Lives: %d)\n", lives);
        feedback_late_or_miss();
        if (lives == 0) return;
    }

    emit_level_complete(lvl_idx);
}

int await_start(void) {
    // printf("Awaiting button press ...\n");

    uint8_t btn_state = BTN_HW_STATE;
    while (true) {
        uint8_t led_pattern = 0;
        for (int i = 0; i < 8; i++) {
            led_on(i, &led_pattern);
            io_expander_write_leds(led_pattern);

            for (int j = 0; j < 50; j++) {
                MS_SLEEP(10);

                int err = io_expander_read_btns(&btn_state);
                if (err != E_SUCCESS) return err;
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

void game_run(void) {
    lives = LIVES;
    rng_state = RNG_INIT_STATE;
    emit_session_start();

    for (uint8_t lvl = 0; lvl < LVLS; lvl++) {
        // printf("\nLevel %d  |  %d ms  |  Lives: %d\n", lvl + 1, duration_ms, lives);
        game_run_level(lvl, POPS_PER_LVL[lvl]);
        if (lives == 0) {
            // printf("\nGame Over! (Reached Level %d)\n", lvl + 1);
            emit_session_end(false);
            MS_SLEEP(500);
            feedback_game_over();
            return;
        }
    }

    // printf("\nCongratulations! Completed all %d levels with %d lives remaining!\n", LVLS, lives);
    emit_session_end(true);
    MS_SLEEP(500);
    feedback_win();
}

void game_task(void* const param) {
    (void)param;

    while (true) {
        await_start();
        game_run();
        MS_SLEEP(2000); // Pause before next game
    }
}
