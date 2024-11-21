`include "allocator_pkg.sv"

module lsu_wrapper
  import allocator_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    input logic req_metadata_val_i,
    input logic req_metadata_is_first_metadata_i,
    input lsu_op_e req_metadata_which_req_i,
    input logic [DATA_W-1:0] req_metadata_metadata_add_i,
    input logic [DATA_W-1:0] req_metadata_metadata_size_i,
    input logic [DATA_W-1:0] req_metadata_metadata_next_addr_i,
    output logic rsp_metadata_val_o,
    output logic [DATA_W-1:0] rsp_metadata_metadata_addr_o,
    output logic [DATA_W-1:0] rsp_metadata_metadata_size_o,
    output logic [DATA_W-1:0] rsp_metadata_metadata_next_addr_o,
    input logic core_rdy_i,

    output logic              mem_req_val_o,
    input  logic              mem_req_rdy_i,
    output logic              mem_req_is_write_o,
    output logic [DATA_W-1:0] mem_req_addr_o,
    output logic [DATA_W-1:0] mem_req_data_o,
    output logic              mem_req_is_cas_o,

    input  logic              mem_rsp_val_i,
    output logic              mem_rsp_rdy_o,
    input  logic [DATA_W-1:0] mem_rsp_data_i
);

  header_data_req_t req_metadata;
  header_data_rsp_t rsp_metadata;

  assign req_metadata.val = req_metadata_val_i;
  assign req_metadata.lsu_op = req_metadata_which_req_i;
  assign req_metadata.header_data.addr = req_metadata_metadata_add_i;
  assign req_metadata.header_data.size = req_metadata_metadata_size_i;
  assign req_metadata.header_data.next_addr = req_metadata_metadata_next_addr_i;

  assign rsp_metadata_val_o = rsp_metadata.val;
  assign rsp_metadata_metadata_addr_o = rsp_metadata.header_data.addr;
  assign rsp_metadata_metadata_size_o = rsp_metadata.header_data.size;
  assign rsp_metadata_metadata_next_addr_o = rsp_metadata.header_data.next_addr;


  lsu i_lsu (
      .clk_i,
      .rst_ni,
      .core_req_header_data_i(req_metadata),
      .core_rsp_header_data_o(rsp_metadata),
      .core_rdy_i(1),
      .lsu_ready_o(  /**/),

      .mem_req_val_o,
      .mem_req_rdy_i,
      .mem_req_is_write_o,
      .mem_req_addr_o,
      .mem_req_data_o,
      .mem_req_is_cas_o,

      .mem_rsp_val_i,
      .mem_rsp_rdy_o,
      .mem_rsp_data_i
  );

endmodule
