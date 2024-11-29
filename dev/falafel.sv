`timescale 1ns / 1ps
`include "falafel_pkg.sv"

module falafel
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,
    input logic is_alloc_i,
    input logic [DATA_W-1:0] addr_to_free_i,
    input logic [DATA_W-1:0] size_to_allocate_i,
    input logic req_alloc_valid_i,

    //----------- memory request ------------//
    output logic              mem_req_val_o,       // req valid
    input  logic              mem_req_rdy_i,       // mem ready
    output logic              mem_req_is_write_o,  // 1 for write, 0 for read
    output logic              mem_req_is_cas_o,    // 1 for cas, 0 for write
    output logic [DATA_W-1:0] mem_req_addr_o,      // address
    output logic [DATA_W-1:0] mem_req_data_o,      // write data
    // output logic [DATA_W-1:0] mem_req_cas_exp_o,   // compare & swap expected value

    //----------- memory response ------------//
    input  logic              mem_rsp_val_i,  // resp valid
    output logic              mem_rsp_rdy_o,  // falafel ready
    input  logic [DATA_W-1:0] mem_rsp_data_i
);

  header_data_req_t core_req_header_data;
  header_data_rsp_t core_rsp_header_data;
  logic core_ready;
  logic lsu_ready;

  falafel_core i_core (
      .clk_i,
      .rst_ni,
      .is_alloc_i,
      .addr_to_free_i,
      .size_to_allocate_i,
      .req_alloc_valid_i,
      .core_ready_o(core_ready),
      .lsu_ready_i(lsu_ready),
      .rsp_from_lsu_i(core_rsp_header_data),
      .req_to_lsu_o(core_req_header_data)
  );

  falafel_lsu i_lsu (
      .clk_i,
      .rst_ni,
      .core_req_header_data_i(core_req_header_data),
      .core_rsp_header_data_o(core_rsp_header_data),
      .core_rdy_i(core_ready),
      .lsu_ready_o(lsu_ready),

      //----------- memory request ------------//
      .mem_req_val_o,  // req valid
      .mem_req_rdy_i,  // mem ready
      .mem_req_is_write_o,  // 1 for write, 0 for read
      .mem_req_is_cas_o,  // 1 for cas, 0 for write
      .mem_req_addr_o,  // address
      .mem_req_data_o,  // write data
      // output logic [DATA_W-1:0] mem_req_cas_exp_o,   // compare & swap expected value

      //----------- memory response ------------//
      .mem_rsp_val_i,  // resp valid
      .mem_rsp_rdy_o,  // falafel ready
      .mem_rsp_data_i
  );
endmodule
