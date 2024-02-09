#include "malloc_freelist.h"
#include <stdio.h>
#include <stdlib.h>

int main() {

#define INIT_SIZE (1 << 16)
  void *init_block = malloc(INIT_SIZE);

  malloc_addblock(init_block, INIT_SIZE);

  printf("malloc(5) = %p\n", fl_malloc(5));

  return 0;
}
