`timescale 1ns / 1ps

package falafel_pkg;
  // Falafel static configuration parameters
  localparam unsigned DATA_W = 64;

  // Constants
  typedef logic [DATA_W-1:0] word_t;

  localparam word_t NULL_PTR = '0;
  localparam word_t WORD_SIZE = 8;
  localparam word_t BLOCK_ALIGNMENT = WORD_SIZE;

  // Opcodes
  localparam word_t REQ_ACCESS_REGISTER = 0;
  localparam word_t REQ_ALLOC_MEM = 1;
  localparam word_t REQ_FREE_MEM = 2;

  // Configuration registers addresses
  localparam FREE_LIST_PTR_ADDR = 'h10;

  // Internal configuration registers
  typedef struct packed {
    // logic is_on;
    logic [DATA_W-1:0] free_list_ptr;
  } config_regs_t;


  // Internal types
  typedef struct packed {
    word_t size;
    word_t next_ptr;
  } free_block_t;

  // verilator lint_off WIDTHEXPAND
  localparam word_t BLOCK_HEADER_SIZE = ($bits(free_block_t) / $bits(word_t) - 1) * WORD_SIZE;
  // verilator lint_on WIDTHEXPAND
  localparam word_t MIN_PAYLOAD_SIZE = 32;
  localparam word_t MIN_ALLOC_SIZE = BLOCK_HEADER_SIZE + MIN_PAYLOAD_SIZE;
  localparam word_t BLOCK_NEXT_PTR_OFFSET = 8;

  typedef enum {
    LSU_OP_STORE_WORD = 0,
    LSU_OP_LOAD_WORD = 1,
    LSU_OP_STORE_BLOCK = 2,
    LSU_OP_LOAD_BLOCK = 3,
    LSU_OP_LOCK = 4,
    LSU_OP_UNLOCK = 5
  } lsu_op_e;

  // Errors
  localparam ERR_NOMEM = -1;

  // Functions
  function word_t align_size(word_t size, word_t alignment);
    if (size < MIN_PAYLOAD_SIZE) size = MIN_PAYLOAD_SIZE;

    return (size + (alignment - 1)) & ~(alignment - 1);
  endfunction
endpackage
