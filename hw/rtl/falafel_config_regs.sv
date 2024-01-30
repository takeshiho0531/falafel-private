module config_regs
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    input logic write_i,
    input logic [DATA_W-1:0] addr_i,
    input logic [DATA_W-1:0] data_i,

    output config_regs_t config_o
);

  config_regs_t config_d, config_q;

  always_comb begin
    config_d = config_q;

    if (write_i) begin
      unique case (addr_i)
        default: ;
      endcase
    end
  end

  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      config_q <= '0;
    end else begin
      config_q <= config_d;
    end
  end

  assign config_o = config_q;
endmodule
