`include "falafel_pkg.sv"

module core_wrapper
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,
    input [DATA_W-1:0] size_to_allocate_i,
    input logic req_alloc_valid_i,
    output logic core_ready_o,

    output logic metadata_req_val_o,
    output logic metadata_req_is_first_metadata_o,
    output [DATA_W-1:0] metadata_req_size_o,
    output [DATA_W-1:0] metadata_req_addr_o,
    output [DATA_W-1:0] metadata_req_next_addr_o,
    output int metadata_req_which_req_o,

    input logic metadata_rsp_val_i,
    input [DATA_W-1:0] metadata_rsp_size_i,
    input [DATA_W-1:0] metadata_rsp_addr_i,
    input [DATA_W-1:0] metadata_rsp_next_addr_i
);

  header_data_req_t metadata_req;
  header_data_rsp_t metadata_rsp;

  assign metadata_req_val_o = metadata_req.val;
  assign metadata_req_size_o = metadata_req.header_data.size;
  assign metadata_req_addr_o = metadata_req.header_data.addr;
  assign metadata_req_next_addr_o = metadata_req.header_data.next_addr;
  assign metadata_req_which_req_o = metadata_req.lsu_op;

  assign metadata_rsp.val = metadata_rsp_val_i;
  assign metadata_rsp.header_data.size = metadata_rsp_size_i;
  assign metadata_rsp.header_data.addr = metadata_rsp_addr_i;
  assign metadata_rsp.header_data.next_addr = metadata_rsp_next_addr_i;

  core i_core (
      .clk_i,
      .rst_ni,
      .size_to_allocate_i,
      .req_alloc_valid_i,
      .core_ready_o,
      .rsp_from_lsu_i(metadata_rsp),
      .req_to_lsu_o(metadata_req),
      .lsu_ready_i(1)
  );

endmodule
