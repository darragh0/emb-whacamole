#pragma once

#include "mxc_delay.h"

#define MS_SLEEP(ms) MXC_Delay(MXC_DELAY_MSEC(ms))
#define S_SLEEP(s) MXC_Delay(MXC_DELAY_SEC(s))
