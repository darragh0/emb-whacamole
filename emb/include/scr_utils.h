#pragma once

#include <stdbool.h>
#include <stdio.h>

/** @brief Screen utilities for the Whac-A-Mole serial console output */

#define RED "\033[91m"
#define GRN "\033[92m"
#define YEL "\033[93m"
#define BLU "\033[94m"
#define MAG "\033[95m"
#define CYN "\033[96m"
#define WHT "\033[97m"

#define BLD "\033[1m"
#define DIM "\033[2m"
#define ITL "\033[3m"

#define RST "\033[0m"

/** @brief Hide cursor */
static inline void curhide(void) { printf("\033[?25l"); }

/** @brief Clear screen */
static inline void cls(void) { printf("\033[2J\033[H"); }

/**
 * @brief Print error message
 *
 * @param msg Message to print
 */
void eprintf(const char* const msg);
