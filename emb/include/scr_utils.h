#pragma once

#include <stdbool.h>

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
#define UND "\033[4m"

#define RST "\033[0m"

/** @brief Hide cursor */
void curhide(void);

/** @brief Clear screen */
void cls(void);

/**
 * @brief Print a message in a given color/style
 *
 * @param msg Message to print
 * @param n_clrs No. of colors/styles to print
 * @param ... Colors/styles
 *
 * @see macros in scr_utils.h
 */
void cprintf(const char* msg, int n_clrs, ...);

/**
 * @brief Print error message
 *
 * @param msg Message to print
 */
void eprintf(const char* const msg);
