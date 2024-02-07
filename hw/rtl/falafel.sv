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

  localparam NUM_OP_FIFO_ENTRIES = 4;

  // Alloc and Free fifos
  logic alloc_fifo_write_en;
  logic alloc_fifo_read_en;
  logic alloc_fifo_full;
  logic alloc_fifo_empty;
  logic [DATA_W-1:0] alloc_fifo_din;
  logic [DATA_W-1:0] alloc_fifo_dout;
  logic free_fifo_write_en;
  logic free_fifo_read_en;
  logic free_fifo_full;
  logic free_fifo_empty;
  logic [DATA_W-1:0] free_fifo_din;
  logic [DATA_W-1:0] free_fifo_dout;
  logic resp_fifo_write_en;
  logic resp_fifo_read_en;
  logic resp_fifo_full;
  logic resp_fifo_empty;
  logic [DATA_W-1:0] resp_fifo_din;
  logic [DATA_W-1:0] resp_fifo_dout;

  logic sbrk_req_val;
  logic sbrk_rsp_val;
  word_t sbrk_rsp_ptr;

  assign sbrk_rsp_val = 1'b0;
  assign sbrk_rsp_ptr = NULL_PTR;

  // Config registers
  config_regs_t config_regs;

  falafel_input_parser i_falafel_input_parser (
      .clk_i,
      .rst_ni,

      .req_val_i (req_val_i),
      .req_rdy_o (req_rdy_o),
      .req_data_i(req_data_i),

      .alloc_fifo_full_i (alloc_fifo_full),
      .alloc_fifo_write_o(alloc_fifo_write_en),
      .alloc_fifo_din_o  (alloc_fifo_din),
      .free_fifo_full_i  (free_fifo_full),
      .free_fifo_write_o (free_fifo_write_en),
      .free_fifo_din_o   (free_fifo_din),

      .config_o(config_regs)
  );

  falafel_core i_falafel_core (
      .clk_i,
      .rst_ni,
      .falafel_config_i  (config_regs),
      .alloc_fifo_empty_i(alloc_fifo_empty),
      .alloc_fifo_read_o (alloc_fifo_read_en),
      .alloc_fifo_dout_i (alloc_fifo_dout),
      .free_fifo_empty_i (free_fifo_empty),
      .free_fifo_read_o  (free_fifo_read_en),
      .free_fifo_dout_i  (free_fifo_dout),
      .resp_fifo_full_i  (resp_fifo_full),
      .resp_fifo_write_o (resp_fifo_write_en),
      .resp_fifo_din_o   (resp_fifo_din),
      .mem_req_rdy_i,
      .mem_req_val_o,
      .mem_req_is_write_i,
      .mem_req_addr_o,
      .mem_req_data_o,
      .mem_rsp_val_i     (mem_resp_val_i),
      .mem_rsp_rdy_o     (mem_resp_rdy_o),
      .mem_rsp_data_i    (mem_resp_data_i),
      .sbrk_req_val_o    (sbrk_req_val),
      .sbrk_rsp_val_i    (sbrk_rsp_val),
      .sbrk_rsp_ptr_o    (sbrk_rsp_ptr)
  );

  falafel_fifo #(
      .DATA_W(DATA_W),
      .NUM_ENTRIES(NUM_OP_FIFO_ENTRIES)
  ) i_alloc_fifo (
      .clk_i,
      .rst_ni,
      .write_i(alloc_fifo_write_en),
      .read_i (alloc_fifo_read_en),
      .full_o (alloc_fifo_full),
      .empty_o(alloc_fifo_empty),
      .din_i  (alloc_fifo_din),
      .dout_o (alloc_fifo_dout)
  );

  falafel_fifo #(
      .DATA_W(DATA_W),
      .NUM_ENTRIES(NUM_OP_FIFO_ENTRIES)
  ) i_free_fifo (
      .clk_i,
      .rst_ni,
      .write_i(free_fifo_write_en),
      .read_i (free_fifo_read_en),
      .full_o (free_fifo_full),
      .empty_o(free_fifo_empty),
      .din_i  (free_fifo_din),
      .dout_o (free_fifo_dout)
  );

  falafel_fifo #(
      .DATA_W(DATA_W),
      .NUM_ENTRIES(NUM_OP_FIFO_ENTRIES)
  ) i_resp_fifo (
      .clk_i,
      .rst_ni,
      .write_i(resp_fifo_write_en),
      .read_i (resp_fifo_read_en),
      .full_o (resp_fifo_full),
      .empty_o(resp_fifo_empty),
      .din_i  (resp_fifo_din),
      .dout_o (resp_fifo_dout)
  );

  falafel_output_fsm i_falafel_output_fsm (
      .clk_i,
      .rst_ni,

      .rsp_rdy_i (resp_rdy_i),
      .rsp_val_o (resp_val_o),
      .rsp_data_o(resp_data_o),

      .resp_fifo_empty_i(resp_fifo_empty),
      .resp_fifo_read_o (resp_fifo_read_en),
      .resp_fifo_dout_i (resp_fifo_dout)
  );
endmodule
