`timescale 1ns / 1ps

`ifndef ALLOCATOR_PKG
`define ALLOCATOR_PKG
package allocator_pkg;

  typedef enum integer {
    LOCK,
    UNLOCK,
    LOAD,
    SET_INSERT_ADDR,
    INSERT,
    DELETE
  } lsu_op_e;

  typedef struct packed {
    logic [63:0] addr;
    logic [63:0] size;
    logic [63:0] next_addr;
  } header_data_t;

  typedef struct packed {
    header_data_t header_data;
    logic val;
    lsu_op_e lsu_op;
  } header_data_req_t;

  typedef struct packed {
    header_data_t header_data;
    logic val;
  } header_data_rsp_t;


  localparam logic [63:0] DATA_W = 64;
  localparam logic [63:0] BLOCK_NEXT_ADDR_OFFSET = 8;
  localparam int WORD_SIZE = 8;
  localparam logic [63:0] EMPTY_KEY = '0;

endpackage
`endif
