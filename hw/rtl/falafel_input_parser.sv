`timescale 1ns / 1ps

module falafel_input_parser
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

    //------------- config regs --------------//
    output config_regs_t config_o
);

  typedef enum logic [2:0] {
    STATE_IDLE,
    STATE_PARSE_INPUT,
    STATE_WRITE_CONFIG_REG_DATA,
    STATE_WRITE_ALLOC_FIFO,
    STATE_WRITE_FREE_FIFO
  } input_state_e;

  input_state_e input_state_d, input_state_q;

  // Input flops
  logic [DATA_W-1:0] req_data_buffer_d, req_data_buffer_q;

  // Config registers
  logic config_reg_write;
  logic [DATA_W-1:0] config_reg_data;
  logic [DATA_W-1:0] config_reg_addr;

  input_req_t input_req;
  config_req_t config_req;

  assign input_req = input_req_t'(req_data_buffer_q);
  assign config_req = config_req_t'(req_data_buffer_q);

  assign req_data_buffer_d = (req_val_i && req_rdy_o) ? req_data_i : req_data_buffer_q;

  assign config_reg_addr = 64'(config_req.addr);
  assign config_reg_data = req_data_i;

  assign alloc_fifo_din_o = req_data_i;
  assign free_fifo_din_o = req_data_i;

  always_comb begin
    input_state_d = input_state_q;
    req_rdy_o = 1'b0;

    alloc_fifo_write_o = 1'b0;
    free_fifo_write_o = 1'b0;

    config_reg_write = 1'b0;

    unique case (input_state_q)
      STATE_IDLE: begin
        req_rdy_o = 1'b1;

        if (req_val_i) begin
          input_state_d = STATE_PARSE_INPUT;
        end
      end

      STATE_PARSE_INPUT: begin
        unique case (input_req.opcode)
          REQ_ACCESS_REGISTER: input_state_d = STATE_WRITE_CONFIG_REG_DATA;
          REQ_ALLOC_MEM: input_state_d = STATE_WRITE_ALLOC_FIFO;
          REQ_FREE_MEM: input_state_d = STATE_WRITE_FREE_FIFO;
          default: assert (0);
        endcase
      end

      STATE_WRITE_CONFIG_REG_DATA: begin
        req_rdy_o = 1'b1;

        if (req_val_i && req_rdy_o) begin
          input_state_d = STATE_IDLE;
          config_reg_write = 1'b1;
        end
      end

      STATE_WRITE_ALLOC_FIFO: begin
        req_rdy_o = !alloc_fifo_full_i;

        if (req_val_i && req_rdy_o) begin
          input_state_d = STATE_IDLE;
          alloc_fifo_write_o = 1'b1;
        end
      end

      STATE_WRITE_FREE_FIFO: begin
        req_rdy_o = !free_fifo_full_i;

        if (req_val_i && req_rdy_o) begin
          input_state_d = STATE_IDLE;
          free_fifo_write_o = 1'b1;
        end
      end

      default: ;
    endcase
  end

  falafel_config_regs i_falafel_config_registers (
      .clk_i,
      .rst_ni,
      .write_i (config_reg_write),
      .addr_i  (config_reg_addr),
      .data_i  (config_reg_data),
      .config_o(config_o)
  );


  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      input_state_q <= STATE_IDLE;
      req_data_buffer_q <= '0;
    end else begin
      input_state_q <= input_state_d;
      req_data_buffer_q <= req_data_buffer_d;
    end
  end
endmodule
