#include "board.h"
#include "led.h"
#include "mxc_delay.h"
#include "mxc_device.h"
#include "pb.h"
#include <stdint.h>
#include <stdio.h>

int main(void) {
  int count = 0;

  printf("Hello World!\n");

  while (1) {
    LED_On(LED_RED);
    MXC_Delay(500000);
    LED_Off(LED_RED);
    MXC_Delay(500000);
    printf("count = %d\n", count++);
  }
}
