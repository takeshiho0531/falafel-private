`timescale 1ns / 1ps

module falafel_input_parser_wrapper
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    //--------------- request ---------------//
    input  logic              req_val_i,
    output logic              req_rdy_o,
    input  logic [DATA_W-1:0] req_data_i,

    //----------- fifo interfaces ------------//
    input  logic              alloc_fifo_full_i,
    output logic              alloc_fifo_write_o,
    output logic [DATA_W-1:0] alloc_fifo_din_o,
    input  logic              free_fifo_full_i,
    output logic              free_fifo_write_o,
    output logic [DATA_W-1:0] free_fifo_din_o,

    //----------- memory response ------------//
    output word_t free_list_ptr_o

);

  config_regs_t config_regs;

  falafel_input_parser i_falafel_input_parser (
      .clk_i,
      .rst_ni,
      .req_val_i,
      .req_rdy_o,
      .req_data_i,
      .alloc_fifo_full_i,
      .alloc_fifo_write_o,
      .alloc_fifo_din_o,
      .free_fifo_full_i,
      .free_fifo_write_o,
      .free_fifo_din_o,
      .config_o(config_regs)
  );

  assign free_list_ptr_o = config_regs.free_list_ptr;
endmodule
