`timescale 1ns / 1ps

`ifndef FALAFEL_PKG
`define FALAFEL_PKG
package falafel_pkg;

  typedef enum integer {
    LOCK,
    UNLOCK,
    LOAD,
    EDIT_SIZE_AND_NEXT_ADDR,
    EDIT_NEXT_ADDR
  } req_lsu_op_e;

  // typedef struct packed {
  //   logic [63:0] size;
  //   logic [63:0] next_addr;
  // } header_t;

    localparam unsigned DATA_W = 64;

  typedef struct packed {
    logic [DATA_W-1:0] addr;
    logic [DATA_W-1:0] size;
    logic [DATA_W-1:0] next_addr;
  } header_t;

  typedef struct packed {
    logic [DATA_W-1:0] size;
    logic [DATA_W-1:0] next_addr;
  } header_net_t;

  typedef struct packed {
    header_t header;
    logic val;
    req_lsu_op_e lsu_op;
  } header_req_t;

  typedef struct packed {
    header_t header;
    logic val;
  } header_rsp_t;

  typedef logic [DATA_W-1:0] word_t;
  localparam logic [DATA_W-1:0] BLOCK_NEXT_ADDR_OFFSET = DATA_W / 8;
  localparam logic [DATA_W-1:0] EMPTY_KEY = '0;
  localparam logic [DATA_W-1:0] BLOCK_HEADER_SIZE = 64'($bits(header_net_t)) / 64'd8;
  localparam logic [DATA_W-1:0] MIN_PAYLOAD_SIZE = 0;  // TODO
  localparam logic [DATA_W-1:0] MIN_ALLOC_SIZE = BLOCK_HEADER_SIZE + MIN_PAYLOAD_SIZE;

endpackage
`endif
