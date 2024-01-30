`timescale 1ns / 1ps

module falafel_lsu_wrapper
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    //----------- alloc request ------------//
    input  logic    alloc_req_val_i,
    output logic    alloc_req_rdy_o,
    input  lsu_op_e alloc_req_op_i,
    input  word_t   alloc_req_addr_i,
    input  word_t   alloc_req_word_i,
    input  word_t   alloc_req_block_size_i,
    input  word_t   alloc_req_block_next_ptr_i,

    //----------- alloc response -----------//
    output logic  alloc_rsp_val_o,
    input  logic  alloc_rsp_rdy_i,
    output word_t alloc_rsp_word_o,
    output word_t alloc_rsp_block_size_o,
    output word_t alloc_rsp_block_next_ptr_o,

    //----------- memory request -----------//
    output logic              mem_req_val_o,       // req valid
    input  logic              mem_req_rdy_i,       // mem ready
    output logic              mem_req_is_write_i,  // 1 for write, 0 for read
    output logic [DATA_W-1:0] mem_req_addr_o,      // address
    output logic [DATA_W-1:0] mem_req_data_o,      // write data

    //----------- memory response ------------//
    input  logic              mem_rsp_val_i,  // resp valid
    output logic              mem_rsp_rdy_o,  // falafel ready
    input  logic [DATA_W-1:0] mem_rsp_data_i  // resp data

);

  free_block_t rsp_block;

  falafel_lsu i_falafel_lsu (
      .clk_i,
      .rst_ni,
      .alloc_req_val_i,
      .alloc_req_rdy_o,
      .alloc_req_op_i,
      .alloc_req_addr_i,
      .alloc_req_word_i,
      .alloc_req_block_i({alloc_req_block_size_i, alloc_req_block_next_ptr_i}),
      .alloc_rsp_val_o,
      .alloc_rsp_rdy_i,
      .alloc_rsp_word_o,
      .alloc_rsp_block_o(rsp_block),
      .mem_req_val_o,
      .mem_req_rdy_i,
      .mem_req_is_write_i,
      .mem_req_addr_o,
      .mem_req_data_o,
      .mem_rsp_val_i,
      .mem_rsp_rdy_o,
      .mem_rsp_data_i
  );

  assign alloc_rsp_block_size_o = rsp_block.size;
  assign alloc_rsp_block_next_ptr_o = rsp_block.next_ptr;
endmodule
