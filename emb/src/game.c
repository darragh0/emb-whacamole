/**
 * @file game.c
 * @brief Game task - Real-time Whack-A-Mole control logic
 *
 * Real-Time Characteristics:
 * - Button polling at 5ms intervals for low-latency response detection
 * - Deterministic timing using vTaskDelay() (FreeRTOS tick-based delays)
 * - Runs at priority 3 (higher than agent) to ensure timing isn't disrupted
 * - Millisecond-precision reaction time measurement
 *
 * Game Mechanics:
 * - 8 difficulty levels with decreasing pop durations (1500ms -> 275ms)
 * - 10 pops per level
 * - 5 lives total, lose 1 life per miss/late
 * - Random mole selection and inter-pop delays for unpredictability
 *
 * State Machine:
 * Ready State (await_start) -> Session Start -> For each level:
 *   -> Level animation -> For each pop:
 *     -> Random delay -> Pop mole -> Poll buttons -> Emit result
 *   -> Level complete
 * -> Session end (win/loss) -> Ready state
 *
 * Queue Producer Pattern:
 * game_task generates events and sends to event_queue via xQueueSend().
 * Events are consumed by agent_task and sent to cloud via UART.
 */

#include "game.h"
#include "btns.h"
#include "io_expander.h"
#include "leds.h"
#include "rtos_queues.h"
#include "utils.h"
#include <stdint.h>

// Game state variables
static uint8_t lives;       // Remaining lives (max 5)
static uint32_t rng_state;  // Xorshift RNG state for random numbers
static uint8_t requested_level_idx = 0;  // Latest level request (0-based, 1-8 from cloud)
static bool level_change_pending = false;  // New level command received
static bool reset_requested = false;       // Reset request pending
static bool start_requested = false;       // Start request pending (from cloud)
static bool reset_abort_session = false;   // Track if reset stopped an in-progress session

// Game difficulty configuration
static const uint8_t POPS_PER_LVL[8] = {[0 ... 7] = 10};  // 10 pops per level
static const uint16_t POP_DURATIONS[8] = {
    1500,  // Level 1: 1.5 seconds
    1250,  // Level 2: 1.25 seconds
    1000,  // Level 3: 1.0 seconds
    750,   // Level 4: 750ms
    600,   // Level 5: 600ms
    500,   // Level 6: 500ms
    350,   // Level 7: 350ms  (challenging)
    275    // Level 8: 275ms  (expert)
};

/**
 * @brief Queue a session start event
 *
 * FreeRTOS Queue Send Pattern:
 * xQueueSend() with timeout=0 means "don't block if queue is full".
 * In practice, queue rarely fills since agent drains faster than game produces.
 * If queue is full, event is dropped (acceptable for non-critical events).
 */
static void emit_session_start(void) {
    const game_event_t event = {.type = EVENT_SESSION_START};
    xQueueSend(event_queue, &event, 0);  // Non-blocking send
}

/**
 * @brief Queue a pop result event
 *
 * @param mole Mole index
 * @param outcome Outcome of the pop
 * @param reaction_ms Reaction time in ms
 * @param lvl Current level
 * @param pop_idx Current pop index (1-based)
 * @param pops_total Total pops in this level
 */
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

/**
 * @brief Queue a level complete event
 *
 * @param lvl Current level
 */
static void emit_level_complete(const uint8_t lvl) {
    const game_event_t event = {
        .type = EVENT_LEVEL_COMPLETE,
        .data.level_complete.level = lvl + 1,
    };
    xQueueSend(event_queue, &event, 0);
}

/**
 * @brief Queue a session end event
 *
 * @param won Whether session was won
 */
static void emit_session_end(const bool won) {
    const game_event_t event = {
        .type = EVENT_SESSION_END,
        .data.session_end.won = won,
    };
    xQueueSend(event_queue, &event, 0);
}

/** @brief Drain command queue and capture latest requested level */
static void drain_cmd_queue(void) {
    if (!cmd_queue) return;

    cmd_msg_t cmd;
    while (xQueueReceive(cmd_queue, &cmd, 0) == pdTRUE) {
        switch (cmd.type) {
            case CMD_SET_LEVEL:
                if (cmd.level >= 1 && cmd.level <= LVLS) {
                    requested_level_idx = cmd.level - 1;  // Convert to 0-based index
                    level_change_pending = true;          // Apply as soon as scheduler lets us run
                }
                break;
            case CMD_RESET:
                reset_requested = true;
                level_change_pending = false;  // Drop pending level changes on reset
                requested_level_idx = 0;
                start_requested = false;
                break;
            case CMD_START:
                start_requested = true;
                break;
        }
    }
}

/** @brief Apply reset request: clear pending commands and restore defaults */
static void apply_reset_state(const bool abort_session) {
    reset_requested = false;
    level_change_pending = false;
    start_requested = false;
    requested_level_idx = 0;
    lives = LIVES;
    rng_state = RNG_INIT_STATE;
    reset_abort_session = abort_session;
}

/** @brief Consume start request and return whether one was pending */
static inline bool consume_start_request(void) {
    const bool start_now = start_requested;
    start_requested = false;
    return start_now;
}

/** @brief Clamp requested level to valid range */
static inline uint8_t requested_level_or_default(void) {
    return (requested_level_idx < LVLS) ? requested_level_idx : 0;
}

/** @brief Whether a different level has been requested mid-session */
static inline bool should_switch_level(const uint8_t current_level_idx) {
    return level_change_pending && requested_level_idx < LVLS
        && requested_level_idx != current_level_idx;
}

/** @brief Consume pending level request and return the target */
static inline uint8_t consume_requested_level(void) {
    level_change_pending = false;
    return requested_level_or_default();
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
    const uint8_t num_leds = lvl_idx + 1;
    uint8_t led_pattern = 0x00;

    for (uint8_t i = 0; i < num_leds; i++) led_on(i, &led_pattern);

    MS_SLEEP(1000);
    led_flash(led_pattern, 3, 500);
    MS_SLEEP(500);
}

/** @brief Wait a random amount of time before next pop */
static void pop_wait_delay(uint32_t* const rng_state) {
    const uint32_t delay = 250 + (next_rand(rng_state) % 751);
    MS_SLEEP(delay);
}

/**
 * @brief Execute a single pop logic - REAL-TIME CRITICAL SECTION
 *
 * This function implements the core real-time control loop:
 * 1. Debounce buttons (wait for clean release)
 * 2. Turn on target LED (mole "pops up")
 * 3. Poll buttons at 5ms intervals for hit detection
 * 4. Measure reaction time with millisecond precision
 * 5. Classify outcome: HIT, MISS, or LATE
 *
 * Real-Time Constraints:
 * - 5ms polling interval for responsive button detection
 * - Must maintain timing accuracy regardless of other tasks
 * - Priority 3 ensures preemption of lower-priority tasks
 * - Uses vTaskDelay() for deterministic timing (tick-based)
 *
 * Timing Analysis:
 * - Shortest pop duration: 275ms (Level 8)
 * - Polling interval: 5ms
 * - Maximum detection latency: 5ms (one poll interval)
 * - Number of polls per pop: 275ms / 5ms = 55 polls (worst case)
 *
 * @param lvl_idx Current level index (0-7)
 * @param rng_state Pointer to RNG state (for random mole selection)
 * @param out_mole [OUT] Selected mole index (0-7)
 * @param out_reaction_ms [OUT] Player reaction time in milliseconds
 * @return Outcome: OUTCOME_HIT, OUTCOME_MISS, or OUTCOME_LATE
 */
static pop_outcome_t pop_do(
    const uint8_t lvl_idx,
    uint32_t* const rng_state,
    uint8_t* out_mole,
    uint16_t* out_reaction_ms
) {
    const uint16_t duration_ms = POP_DURATIONS[lvl_idx];  // Pop timeout for this level
    const uint8_t target_led = next_rand(rng_state) % LED_COUNT;  // Random mole (0-7)
    *out_mole = target_led;

    /**
     * Button Debouncing Phase:
     * Wait for all buttons to be released before starting pop.
     * This prevents accidental button holds from immediately triggering.
     *
     * Debounce Strategy:
     * - Poll button state every 10ms
     * - If any button pressed, wait another 10ms
     * - Timeout after 50ms to prevent indefinite blocking
     *
     * I2C Read: io_expander_read_btns() returns 0xFF when all released (active-low)
     */
    uint8_t btn_state;
    uint16_t db_time = 0;
    do {
        io_expander_read_btns(&btn_state);  // I2C read from MAX7325
        if (btn_state != BTN_HW_STATE) {    // BTN_HW_STATE = 0xFF (all released)
            MS_SLEEP(10);                   // vTaskDelay(10ms)
            db_time += 10;
            if (db_time > 50) break;        // Timeout: proceed anyway
        }
    } while (btn_state != BTN_HW_STATE);

    /**
     * LED Activation Phase:
     * Turn on target LED to indicate which mole "popped up".
     * Player must press corresponding button before timeout.
     */
    uint8_t led_pattern = 0;
    led_on(target_led, &led_pattern);          // Set bit in pattern
    io_expander_write_leds(led_pattern);       // I2C write to MAX7325

    /**
     * Real-Time Button Polling Loop:
     * This is the critical real-time section that determines game responsiveness.
     *
     * Polling Strategy:
     * - Read buttons every 5ms for low latency
     * - Track elapsed time for reaction measurement
     * - Exit immediately on correct button press (HIT)
     * - Exit on timeout (MISS or LATE depending on if any button pressed)
     *
     * Why 5ms interval?
     * - Fast enough for responsive gameplay (200 Hz sampling)
     * - Slow enough to avoid excessive I2C traffic
     * - Aligned with FreeRTOS tick period (1ms)
     */
    uint16_t elapsed = 0;  // Reaction time counter (in milliseconds)
    const uint8_t poll_interval = 5;  // Poll every 5ms

    /**
     * Polling Loop - Runs until timeout or button press
     *
     * Each iteration:
     * 1. Read button state via I2C (blocking operation, ~100us)
     * 2. Check if correct button was pressed
     * 3. Increment elapsed time counter
     * 4. vTaskDelay(5ms) - Yields to other tasks, ensuring deterministic timing
     *
     * FreeRTOS vTaskDelay() guarantees:
     * - Task blocks for exactly 5 ticks (5ms @ 1000 Hz tick rate)
     * - Other tasks (agent, idle) can run during this time
     * - No busy-waiting - CPU can enter low-power mode
     * - Timing is deterministic regardless of other task loads
     */
    while (elapsed < duration_ms) {
        io_expander_read_btns(&btn_state);  // I2C read (~100us)

        // Check if any button was pressed (active-low: 0xFF = all released)
        if (btn_state != BTN_HW_STATE) {
            // Button detected! Record reaction time
            *out_reaction_ms = elapsed;

            // Turn off all LEDs
            led_hw_write();  // Writes 0x00 to MAX7325

            // Determine outcome: HIT if correct button, MISS if wrong button
            // is_btn_pressed() checks if specific button bit is cleared (active-low)
            return is_btn_pressed(target_led, btn_state) ? POP_HIT : POP_MISS;
        }

        /**
         * vTaskDelay() - Yield CPU and wait for next poll interval
         *
         * This is the key to FreeRTOS real-time behavior:
         * - Puts task in Blocked state for poll_interval ticks (5ms)
         * - Scheduler can run other tasks (agent task, idle task)
         * - Task wakes up after exactly 5ms (tick-accurate timing)
         * - No busy-waiting means efficient CPU usage
         *
         * During this delay, agent_task can drain event queue and send UART,
         * ensuring game events are transmitted to cloud without blocking game logic.
         */
        MS_SLEEP(poll_interval);  // vTaskDelay(5) - Block for 5ms
        elapsed += poll_interval;  // Track total reaction time
    }

    // Timeout reached - No button pressed within duration
    *out_reaction_ms = duration_ms;  // Max reaction time
    led_hw_write();                   // Turn off LED
    return POP_LATE;                  // Player was too slow
}

/** @brief Run a complete level */
static void game_run_level(const uint8_t lvl_idx, const uint8_t pops) {
    lvl_show(lvl_idx);

    for (int pop = 0; pop < pops; pop++) {
        drain_cmd_queue();  // Keep up with cloud commands while playing
        if (reset_requested) {
            apply_reset_state(true);
            return;
        }
        if (should_switch_level(lvl_idx)) return;  // Jump to requested level ASAP

        pop_wait_delay(&rng_state);
        drain_cmd_queue();  // Capture requests that arrived during the delay
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

int await_start(void) {
    // printf("Awaiting button press ...\n");

    uint8_t btn_state = BTN_HW_STATE;
restart_idle:
    while (true) {
        drain_cmd_queue();  // Allow cloud level updates while idle
        if (reset_requested) {
            apply_reset_state(false);
            continue;  // Stay idle
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
    drain_cmd_queue();  // Capture latest requested start level before beginning
    if (reset_requested) {
        apply_reset_state(false);
        return;  // Reset requested before game starts - stay idle
    }
    uint8_t lvl = requested_level_or_default();  // Start at latest requested level
    level_change_pending = false;                // We just aligned start level
    start_requested = false;                     // Consume any start request
    emit_session_start();

    while (lvl < LVLS) {
        // printf("\nLevel %d  |  %d ms  |  Lives: %d\n", lvl + 1, duration_ms, lives);
        game_run_level(lvl, POPS_PER_LVL[lvl]);
        if (reset_abort_session) {
            emit_session_end(false);
            reset_abort_session = false;
            return;
        }
        if (lives == 0) {
            // printf("\nGame Over! (Reached Level %d)\n", lvl + 1);
            emit_session_end(false);
            MS_SLEEP(500);
            feedback_game_over();
            return;
        }

        drain_cmd_queue();             // Let queued requests while paused take effect immediately
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
                continue;  // Jump straight to requested level (no extra delay)
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

    // printf("\nCongratulations! Completed all %d levels with %d lives remaining!\n", LVLS, lives);
    emit_session_end(true);
    MS_SLEEP(500);
    feedback_win();
}

void game_task(void* const param) {
    (void)param;

    while (true) {
        drain_cmd_queue();
        await_start();
        drain_cmd_queue();
        game_run();
        drain_cmd_queue();
        if (reset_abort_session) {
            reset_abort_session = false;
            continue;  // Skip delay so reset returns to idle immediately
        }
        MS_SLEEP(2000); // Pause before next game
    }
}
