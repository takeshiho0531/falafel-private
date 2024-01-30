module falafel
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    //--------------- request ---------------//
    input  logic              req_val_i,
    output logic              req_rdy_o,
    input  logic [DATA_W-1:0] req_data_i,

    //-------------- response ---------------//
    input  logic              resp_rdy_i,
    output logic              resp_val_o,
    output logic [DATA_W-1:0] resp_data_o,

    //----------- memory request ------------//
    input  logic              mem_req_rdy_i,       // mem ready
    output logic              mem_req_val_o,       // req valid
    output logic              mem_req_is_write_i,  // 1 for write, 0 for read
    output logic [DATA_W-1:0] mem_req_addr_o,      // address
    output logic [DATA_W-1:0] mem_req_data_o,      // write data

    //----------- memory response ------------//
    input  logic              mem_resp_val_i,  // resp valid
    output logic              mem_resp_rdy_o,  // falafel ready
    input  logic [DATA_W-1:0] mem_resp_data_i  // resp data
);

endmodule
