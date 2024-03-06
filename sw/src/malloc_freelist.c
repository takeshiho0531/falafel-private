// Most the code code below has been modified from
// https://github.com/embeddedartistry/embedded-resources/tree/master
// with some modifications to the alloc_node_t struct

#include <stdint.h>
#include <stdio.h>

#ifndef align_up
#define align_up(num, align) (((num) + ((align)-1)) & ~((align)-1))
#endif

typedef struct alloc_node {
  size_t size;

  union {
    char *block;
    struct alloc_node *next;
  };
} alloc_node_t;

static inline void list_add_(alloc_node_t *n, alloc_node_t *prev,
                             alloc_node_t *next) {
  n->next = next;
  prev->next = n;
}

static inline void list_del_(alloc_node_t *prev, alloc_node_t *n) {
  prev->next = n->next;
}

/* #define ALLOC_HEADER_SZ offsetof(alloc_node_t, block) */
#define ALLOC_HEADER_SZ 8 // TODO

#define MIN_REQ_SZ 32
#define MIN_ALLOC_SZ ALLOC_HEADER_SZ + MIN_REQ_SZ

static void defrag_free_list(void);

alloc_node_t *free_list = NULL;

void *get_free() { return &free_list; }

void defrag_free_list(void) {
  alloc_node_t *prev_block = NULL;
  alloc_node_t *current_block = free_list;

  while (current_block) {
    if (current_block->next) {
      alloc_node_t *next_block = current_block->next;

      if ((uintptr_t)(void *)current_block->block + current_block->size ==
          (uintptr_t)next_block) {

        current_block->next = next_block->next;
        current_block->size += next_block->size + ALLOC_HEADER_SZ;
      }
    }

    if (prev_block) {
      if ((uintptr_t)(void *)prev_block->block + prev_block->size ==
          (uintptr_t)current_block) {

        prev_block->next = current_block->next;
        prev_block->size += current_block->size + ALLOC_HEADER_SZ;
      }
    }

    prev_block = current_block;
    current_block = current_block->next;
  }
}

void *fl_malloc(size_t size) {
  void *ptr = NULL;
  alloc_node_t *blk = free_list;
  alloc_node_t *prev = NULL;

  if (size > 0) {
    size = align_up(size, sizeof(void *));
    if (size < MIN_REQ_SZ)
      size = MIN_REQ_SZ;

    while (blk) {
      if (blk->size >= size) {
        ptr = &blk->block;
        break;
      }

      blk = blk->next;
      prev = blk;
    }

    if (ptr) {
      if ((blk->size - size) >= MIN_ALLOC_SZ) {
        alloc_node_t *new_blk;
        new_blk = (alloc_node_t *)((uintptr_t)(&blk->block) + size);
        new_blk->size = blk->size - size - ALLOC_HEADER_SZ;
        blk->size = size;

        list_add_(new_blk, blk, blk->next);
      }

      if (prev)
        prev->next = blk->next;
      else
        free_list = blk->next;
    }
  }

  return ptr;
}

void fl_free(void *ptr) {
  alloc_node_t *blk = NULL;
  alloc_node_t *prev = NULL;
  alloc_node_t *free_blk;

  if (ptr) {
    blk = (alloc_node_t *)((char *)ptr - 8);

    prev = NULL;
    free_blk = free_list;

    while (free_blk) {
      if (free_blk > blk) {
        if (prev)
          list_add_(blk, prev, free_blk);
        else {
          blk->next = free_blk;
          free_list = blk;
        }

        goto blockadded;
      }

      prev = free_blk;
      free_blk = free_blk->next;
    }

    if (free_list)
      free_blk->next = blk;
    else
      free_list = blk;

    blk->next = NULL;
  blockadded:
    defrag_free_list();
  }
}

void malloc_addblock(void *addr, size_t size) {
  alloc_node_t *blk;

  // let's align the start address of our block to the next pointer aligned
  // number
  blk = (void *)align_up((uintptr_t)addr, sizeof(void *));

  // calculate actual size - remove our alignment and our header space from the
  // availability
  blk->size = (uintptr_t)addr + size - (uintptr_t)blk - ALLOC_HEADER_SZ;

  /* list_add(&blk->node, &free_list); */
  fl_free(&blk->block);
}
