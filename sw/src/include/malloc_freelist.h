// Most the code code below has been modified from
// https://github.com/embeddedartistry/embedded-resources/tree/master

#ifndef __MALLOC_FREELIST_H_
#define __MALLOC_FREELIST_H_

#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif //__cplusplus

/**
 * Initialize malloc with a memory address and pool size
 */
void malloc_addblock(void *addr, size_t size);

/**
 * Free-list malloc implementation
 */
void *fl_malloc(size_t size);

/**
 * Corresponding free-list free implementation
 */
void fl_free(void *ptr);

void *get_free();

#ifdef __cplusplus
}
#endif //__cplusplus

#endif //__MALLOC_FREELIST_H_
