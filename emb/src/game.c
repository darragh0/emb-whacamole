#include "game.h"
#include "btns.h"
#include "io_expander.h"
#include "leds.h"
#include "scr_utils.h"
#include "utils.h"
#include <stdio.h>

static uint8_t lives;
static uint32_t rng_state;

static const uint8_t POPS_PER_LVL[8] = {[0 ... 7] = 10};
static const uint16_t POP_DURATIONS[8] = {1500, 1250, 1000, 750, 600, 500, 350, 250};

/** @brief Flash all LEDs twice for LATE/MISS */
static inline void feedback_late_or_miss(void) { led_flash(0xFF, 1, 100); }

/** @brief Flash all LEDs 3 times for GAME OVER */
static inline void feedback_game_over(void) { led_flash(0xFF, 3, 500); }

/** @brief Flash all LEDs 100 times for WIN */
static void feedback_win(void) { led_flash(0xFF, 100, 50); }

/** @brief Display level number with N LEDs */
static void lvl_show(const uint8_t lvl_idx) {
    uint8_t num_leds = lvl_idx + 1;
    uint8_t led_pattern = 0x00;

    for (uint8_t i = 0; i < num_leds; i++) led_on(i, &led_pattern);

    MS_SLEEP(1000);
    led_flash(led_pattern, 3, 500);
    MS_SLEEP(500);
}

/**
 * @brief Random delay between pops (250-1000ms)
 *
 * @param rng_state RNG state
 */
static void pop_wait_delay(uint32_t* const rng_state) {
    uint32_t delay = 250 + (next_rand(rng_state) % 751);
    MS_SLEEP(delay);
}

/**
 * @brief Execute a single pop, return outcome
 *
 * @param lvl_idx Level index
 * @param rng_state RNG state
 */
static pop_outcome_t pop_do(const uint8_t lvl_idx, uint32_t* const rng_state) {
    uint16_t duration_ms = POP_DURATIONS[lvl_idx];
    uint8_t target_led = next_rand(rng_state) % LED_COUNT;

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
    const uint8_t poll_interval = 10;

    while (elapsed < duration_ms) {
        io_expander_read_btns(&btn_state);

        // Check if any button pressed
        if (btn_state != BTN_HW_STATE) {
            led_hw_write();
            return is_btn_pressed(target_led, btn_state) ? POP_HIT : POP_MISS;
        }

        MS_SLEEP(poll_interval);
        elapsed += poll_interval;
    }

    // Timeout - turn off LED
    led_hw_write();
    return POP_LATE;
}

/**
 * @brief Run a single level
 *
 * @param lvl_idx Level index
 * @param pops Number of pops for this level
 */
static void game_run_level(const uint8_t lvl_idx, const uint8_t pops) {
    lvl_show(lvl_idx);

    for (int pop = 0; pop < pops; pop++) {
        pop_wait_delay(&rng_state);

        pop_outcome_t outcome = pop_do(lvl_idx, &rng_state);
        printf("  %sPop %s%02d%s :: ", ITL, GRN, pop + 1, RST);
        switch (outcome) {
            case POP_HIT:
                printf("%s[HIT]%s\n", GRN, RST);
                continue;
            case POP_MISS:
                printf("%s[MISS]", RED);
                goto err;
            case POP_LATE:
                printf("%s[LATE]", YEL);
                goto err;
        }

    err:
        lives--;
        printf("%s   %s(Lives: %s%d%s%s)%s\n", RST, DIM, YEL, lives, RST, DIM, RST);
        feedback_late_or_miss();
        if (lives == 0) return;
    }
}

void welcome(void) {
    curhide();
    cls();
    fflush(stdout);
    printf("===== %sWhac-A-Mole%s =====\n\n", CYN, RST);
    printf("%s%sAwaiting button press ...%s\n", ITL, CYN, RST);
}

int await_start(void) {
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
    lives = 5;
    rng_state = 0xDEADBEEF;

    for (uint8_t lvl = 0; lvl < 1; lvl++) {
        printf("\n%sLevel %d%s (Lives: %s%d%s)\n", GRN, lvl + 1, RST, YEL, lives, RST);
        game_run_level(lvl, POPS_PER_LVL[lvl]);

        if (lives == 0) {
            printf("\n%sGame Over!%s (Reached %sLevel %d%s)\n", RED, RST, GRN, lvl + 1, RST);
            feedback_game_over();
            return;
        }
    }

    printf("\nCongratulations! Completed all 8 levels with %s%d%s lives remaining!\n", GRN, lives, RST);
    feedback_win();
}
