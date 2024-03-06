#include "malloc_freelist.h"
#include <stdio.h>
#include <stdlib.h>

int main() {

#define INIT_SIZE (1 << 16)
  void *init_block = malloc(INIT_SIZE);

  malloc_addblock(init_block, INIT_SIZE);

  void *ptr = fl_malloc(5);
  printf("added block\n");
  printf("malloc(5) = %p\n", ptr);
  printf("malloc(2340) = %p\n", fl_malloc(2340));
  fl_free(ptr);
  ptr = fl_malloc(5);
  printf("malloc(5) = %p\n", ptr);

  ptr = fl_malloc(5);
  printf("malloc(5) = %p\n", ptr);

  return 0;
}
