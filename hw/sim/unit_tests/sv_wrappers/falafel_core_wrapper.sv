`timescale 1ns / 1ps

module falafel_core_wrapper
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    input logic [DATA_W-1:0] falafel_config_free_list_ptr,

    //----------- fifo interfaces ------------//
    input  logic              alloc_fifo_empty_i,
    output logic              alloc_fifo_read_o,
    input  logic [DATA_W-1:0] alloc_fifo_dout_i,

    input  logic              free_fifo_empty_i,
    output logic              free_fifo_read_o,
    input  logic [DATA_W-1:0] free_fifo_dout_i,

    input  logic              resp_fifo_full_i,
    output logic              resp_fifo_write_o,
    output logic [DATA_W-1:0] resp_fifo_din_o,

    //----------- memory request -----------//
    input  logic              mem_req_rdy_i,       // mem ready
    output logic              mem_req_val_o,       // req valid
    output logic              mem_req_is_write_i,  // 1 for write, 0 for read
    output logic [DATA_W-1:0] mem_req_addr_o,      // address
    output logic [DATA_W-1:0] mem_req_data_o,      // write data

    //----------- memory response ------------//
    input  logic              mem_rsp_val_i,  // resp valid
    output logic              mem_rsp_rdy_o,  // falafel ready
    input  logic [DATA_W-1:0] mem_rsp_data_i, // resp data

    //----------- fifo interfaces ------------//
    output logic              sbrk_req_val_o,
    input  logic              sbrk_rsp_val_i,
    input  logic [DATA_W-1:0] sbrk_rsp_ptr_o

);

  config_regs_t falafel_config;

  falafel_core i_falafel_core (
      .clk_i,
      .rst_ni,
      .falafel_config(falafel_config),
      .alloc_fifo_empty_i,
      .alloc_fifo_read_o,
      .alloc_fifo_dout_i,
      .free_fifo_empty_i,
      .free_fifo_read_o,
      .free_fifo_dout_i,
      .resp_fifo_full_i,
      .resp_fifo_write_o,
      .resp_fifo_din_o,
      .mem_req_rdy_i,
      .mem_req_val_o,
      .mem_req_is_write_i,
      .mem_req_addr_o,
      .mem_req_data_o,
      .mem_rsp_val_i,
      .mem_rsp_rdy_o,
      .mem_rsp_data_i,
      .sbrk_req_val_o,
      .sbrk_rsp_val_i,
      .sbrk_rsp_ptr_o
  );

  assign falafel_config.free_list_ptr = falafel_config_free_list_ptr;
endmodule
