`include "allocator_pkg.sv"

module lsu
  import allocator_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    input header_data_req_t core_req_header_data_i,
    output header_data_rsp_t core_rsp_header_data_o,
    input logic core_rdy_i,
    output logic lsu_ready_o,

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
    input  logic [DATA_W-1:0] mem_rsp_data_i  // resp data // different from original falafel
);

  typedef enum integer {
    IDLE,
    LOAD_KEY,
    WAIT_LOAD_KEY,
    LOCK_DO_CAS,
    LOCK_WAIT_CAS,
    LOAD_SIZE,
    RECV_RSP_ON_SIZE_FROM_MEM_LOAD,
    LOAD_NEXT_ADDR,
    RECV_RSP_ON_NEXT_ADDR_FROM_MEM_LOAD,
    STORE_UPDATED_SIZE,
    RECV_RSP_ON_SIZE_FROM_MEM_UPDATE,
    STORE_UPDATED_NEXT_ADDR,
    RECV_RSP_ON_NEXT_ADDR_FROM_MEM_UPDATE,
    SEND_RSP_TO_CORE
  } lsu_state_e;

  lsu_state_e state_q, state_d;
  header_data_req_t req_header_data_q, req_header_data_d;
  header_data_rsp_t rsp_header_data_q, rsp_header_data_d;
  lsu_op_e lsu_op_q, lsu_op_d;
  logic [DATA_W-1:0] load_addr_q, load_addr_d;

  /*
  // task automatic send_mem_load_req(logic req_val_i, logic [DATA_W-1:0] addr_to_send_i);
  //   mem_req_val_o = req_val_i;
  //   mem_req_addr_o = addr_to_send_i;
  //   mem_req_is_write_o = 0;
  // endtask

  // task automatic send_mem_store_word_req(logic req_val_i, logic [DATA_W-1:0] addr_to_send_i,
  //                                        logic [DATA_W-1:0] data_to_send_i);
  //   mem_req_val_o = req_val_i;
  //   mem_req_addr_o = addr_to_send_i;
  //   mem_req_data_o = data_to_send_i;
  //   mem_req_is_write_o = 1;
  // endtask
*/

  always_comb begin : lsu_fsm
    state_d = state_q;
    req_header_data_d = req_header_data_q;
    rsp_header_data_d = rsp_header_data_q;
    lsu_op_d = lsu_op_q;
    lsu_ready_o = 0;
    mem_req_is_cas_o = 0;
    mem_req_val_o = 0;
    core_rsp_header_data_o.val = 0;
    load_addr_d = load_addr_q;

    unique case (state_q)
      IDLE: begin
        lsu_ready_o = 1;  // TODO other states
        // core_rsp_header_data_o.val = 0;
        if (core_req_header_data_i.val) begin
          // lsu_ready_o = 0;
          req_header_data_d = core_req_header_data_i;
          mem_rsp_rdy_o = 0;

          unique case (core_req_header_data_i.lsu_op)
            LOCK: state_d = LOAD_KEY;
            // UNLOCK:
            LOAD: begin
              state_d  = LOAD_SIZE;
              lsu_op_d = LOAD;
            end
            INSERT: begin
              state_d  = STORE_UPDATED_SIZE;
              lsu_op_d = INSERT;
            end
            DELETE: begin
              state_d  = STORE_UPDATED_NEXT_ADDR;
              lsu_op_d = DELETE;
            end
            default: assert (0);
          endcase
        end
      end
      LOAD_KEY: begin
        if (mem_req_rdy_i) begin
          // send_mem_load_req(.req_val_i(req_header_data_q.val),
          //                   .addr_to_send_i(req_header_data_q.header_data.addr));
          mem_req_val_o = req_header_data_q.val;
          mem_req_addr_o = req_header_data_q.header_data.addr;
          mem_req_is_write_o = 0;
          state_d = WAIT_LOAD_KEY;
        end
      end
      WAIT_LOAD_KEY: begin
        mem_req_val_o = 0;
        mem_rsp_rdy_o = 1;
        if (mem_rsp_val_i) begin
          if (mem_rsp_data_i == EMPTY_KEY) state_d = LOCK_DO_CAS;
          else state_d = LOAD_KEY;
        end
      end
      LOCK_DO_CAS: begin
        mem_req_is_cas_o = 1'b1;
        mem_req_data_o = '0;  // TODO lock id
        mem_req_val_o = 1;
        if (mem_req_rdy_i) begin
          state_d = LOCK_WAIT_CAS;
        end
      end
      LOCK_WAIT_CAS: begin
        mem_req_val_o = 0;
        mem_rsp_rdy_o = 1;
        if (mem_rsp_val_i) begin
          if (mem_rsp_data_i == 0) state_d = SEND_RSP_TO_CORE;  // we have taken the key
          else state_d = LOAD_KEY;
        end
      end
      LOAD_SIZE: begin
        if (mem_req_rdy_i) begin
          // send_mem_load_req(.req_val_i(req_header_data_q.val),
          //                   .addr_to_send_i(req_header_data_q.header_data.addr));
          mem_req_val_o = req_header_data_q.val;
          mem_req_addr_o = req_header_data_q.header_data.addr;
          // load_addr_d = req_header_data_q.header_data.addr;
          mem_req_is_write_o = 0;
          state_d = RECV_RSP_ON_SIZE_FROM_MEM_LOAD;
        end
      end
      RECV_RSP_ON_SIZE_FROM_MEM_LOAD: begin
        mem_req_val_o = 0;
        mem_rsp_rdy_o = 1;
        if (mem_rsp_val_i) begin
          state_d = LOAD_NEXT_ADDR;
          rsp_header_data_d.header_data.size = mem_rsp_data_i;
        end
      end
      LOAD_NEXT_ADDR: begin
        if (mem_req_rdy_i) begin
          state_d = RECV_RSP_ON_NEXT_ADDR_FROM_MEM_LOAD;
          // send_mem_load_req(
          //     .req_val_i(req_header_data_q.val),
          //     .addr_to_send_i(req_header_data_q.header_data.addr + BLOCK_NEXT_ADDR_OFFSET));
          mem_req_val_o = req_header_data_q.val;
          mem_req_addr_o = req_header_data_q.header_data.addr + BLOCK_NEXT_ADDR_OFFSET;
          mem_req_is_write_o = 0;
        end
      end
      RECV_RSP_ON_NEXT_ADDR_FROM_MEM_LOAD: begin
        mem_rsp_rdy_o = 1;
        if (mem_rsp_val_i) begin
          state_d = SEND_RSP_TO_CORE;
          rsp_header_data_d.val = mem_rsp_val_i;
          rsp_header_data_d.header_data.next_addr = mem_rsp_data_i;
        end
      end
      STORE_UPDATED_SIZE: begin
        if (mem_req_rdy_i) begin
          // send_mem_store_word_req(.req_val_i(req_header_data_q.val),
          //                         .addr_to_send_i(req_header_data_q.header_data.addr),
          //                         .data_to_send_i(req_header_data_q.header_data.size));
          // task automatic send_mem_store_word_req(logic req_val_i, logic [DATA_W-1:0] addr_to_send_i,
          //                                        logic [DATA_W-1:0] data_to_send_i);
          mem_req_val_o = req_header_data_q.val;
          mem_req_addr_o = req_header_data_q.header_data.addr;
          mem_req_data_o = req_header_data_q.header_data.size;
          mem_req_is_write_o = 1;

          if (lsu_op_q == INSERT) begin
            state_d = RECV_RSP_ON_SIZE_FROM_MEM_UPDATE;
          end else begin
            state_d = RECV_RSP_ON_NEXT_ADDR_FROM_MEM_UPDATE;
          end
        end
      end
      RECV_RSP_ON_SIZE_FROM_MEM_UPDATE: begin
        mem_rsp_rdy_o = 1;
        if (mem_rsp_val_i) begin
          rsp_header_data_d.val = mem_rsp_val_i;
          state_d = STORE_UPDATED_NEXT_ADDR;
        end
      end
      STORE_UPDATED_NEXT_ADDR: begin
        if (mem_req_rdy_i) begin
          // send_mem_store_word_req(
          //     .req_val_i(req_header_data_q.val),
          //     .addr_to_send_i(req_header_data_q.header_data.addr + BLOCK_NEXT_ADDR_OFFSET),
          //     .data_to_send_i(req_header_data_q.header_data.next_addr));
          mem_req_val_o = req_header_data_q.val;
          mem_req_addr_o = req_header_data_q.header_data.addr + BLOCK_NEXT_ADDR_OFFSET;
          mem_req_data_o = req_header_data_q.header_data.next_addr;
          mem_req_is_write_o = 1;
          state_d = RECV_RSP_ON_NEXT_ADDR_FROM_MEM_UPDATE;
        end
      end

      RECV_RSP_ON_NEXT_ADDR_FROM_MEM_UPDATE: begin
        mem_rsp_rdy_o = 1;
        if (mem_rsp_val_i) begin
          rsp_header_data_d.val = mem_rsp_val_i;
          state_d = SEND_RSP_TO_CORE;
        end
      end

      SEND_RSP_TO_CORE: begin
        core_rsp_header_data_o = rsp_header_data_q;
        core_rsp_header_data_o.header_data.addr = req_header_data_q.header_data.addr;
        core_rsp_header_data_o.val = 1;
        if (core_rdy_i) begin
          lsu_ready_o = 1;
          state_d = IDLE;
        end
      end
      // default: ;
    endcase
  end

  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      state_q <= IDLE;
      req_header_data_q <= '0;
      rsp_header_data_q <= '0;
      lsu_op_q <= LOCK;
    end else begin
      state_q <= state_d;
      req_header_data_q <= req_header_data_d;
      rsp_header_data_q <= rsp_header_data_d;
      lsu_op_q <= lsu_op_d;
    end
  end

endmodule
