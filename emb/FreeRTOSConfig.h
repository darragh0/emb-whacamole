/** @brief FreeRTOS config (simplified from MaximSDK's FreeRTOSDemo) */

#pragma once

#include "max32655.h"

// Clock: use internal primary oscillator frequency
#define configCPU_CLOCK_HZ ((uint32_t)IPO_FREQ)

// Tick rate: 1000 Hz = 1ms per tick
#define configTICK_RATE_HZ ((portTickType)1000)

// Memory: 26KB heap should be plenty
#define configTOTAL_HEAP_SIZE ((size_t)(26 * 1024))

// Stack: 128 words minimum, we'll use 256 for our tasks
#define configMINIMAL_STACK_SIZE ((uint16_t)128)

// Priorities: 5 levels (0-4), higher number = higher priority
#define configMAX_PRIORITIES 5

// Scheduler: preemptive (higher priority tasks interrupt lower)
#define configUSE_PREEMPTION 1

// Features we need
#define configUSE_MUTEXES 1
#define configSUPPORT_DYNAMIC_ALLOCATION 1

// Features we don't need
#define configUSE_IDLE_HOOK 0
#define configUSE_TICK_HOOK 0
#define configUSE_CO_ROUTINES 0
#define configUSE_16_BIT_TICKS 0
#define configUSE_TRACE_FACILITY 0
#define configUSE_STATS_FORMATTING_FUNCTIONS 0

// API functions to include
#define INCLUDE_vTaskPrioritySet 0
#define INCLUDE_vTaskDelete 0
#define INCLUDE_vTaskSuspend 1
#define INCLUDE_vTaskDelayUntil 1
#define INCLUDE_uxTaskPriorityGet 0
#define INCLUDE_vTaskDelay 1

// Interrupt priorities (ARM Cortex-M4 specific)
#define configPRIO_BITS __NVIC_PRIO_BITS
#define configKERNEL_INTERRUPT_PRIORITY ((unsigned char)7 << (8 - configPRIO_BITS))
#define configMAX_SYSCALL_INTERRUPT_PRIORITY ((unsigned char)5 << (8 - configPRIO_BITS))

// Map FreeRTOS handlers to CMSIS names
#define vPortSVCHandler SVC_Handler
#define xPortPendSVHandler PendSV_Handler
#define xPortSysTickHandler SysTick_Handler

// Required by FreeRTOS+CLI but we don't use it
#define configCOMMAND_INT_MAX_OUTPUT_SIZE 1
