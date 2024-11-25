`timescale 1ns / 1ps

`ifndef FALAFEL_PKG
`define FALAFEL_PKG
package falafel_pkg;

  typedef enum integer {
    LOCK,
    UNLOCK,
    LOAD,
    UPDATE,
    INSERT,
    DELETE
  } req_lsu_op_e;

  typedef struct packed {
    logic [63:0] size;
    logic [63:0] next_addr;
  } header_t;

  typedef struct packed {
    logic [63:0] addr;
    logic [63:0] size;
    logic [63:0] next_addr;
  } header_data_t;

  typedef struct packed {
    header_data_t header_data;
    logic val;
    req_lsu_op_e lsu_op;
  } header_data_req_t;

  typedef struct packed {
    header_data_t header_data;
    logic val;
  } header_data_rsp_t;

  typedef logic [DATA_W-1:0] word_t;
  localparam logic [63:0] DATA_W = 64;
  localparam logic [63:0] BLOCK_NEXT_ADDR_OFFSET = 8;
  localparam int WORD_SIZE = 8;
  localparam logic [63:0] EMPTY_KEY = '0;
  localparam [63:0] BLOCK_HEADER_SIZE = (64'($bits(header_t)) / 64'($bits(word_t)) - 1) * WORD_SIZE;
  localparam word_t MIN_PAYLOAD_SIZE = 32;
  localparam word_t MIN_ALLOC_SIZE = BLOCK_HEADER_SIZE + MIN_PAYLOAD_SIZE;

endpackage
`endif
