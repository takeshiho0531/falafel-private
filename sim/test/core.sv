`include "allocator_pkg.sv"

module core
  import allocator_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,
    input [DATA_W-1:0] size_to_allocate_i,
    input logic req_alloc_valid_i,
    output logic core_ready_o,
    input logic lsu_ready_i,
    input header_data_rsp_t rsp_from_lsu_i,
    output header_data_req_t req_to_lsu_o
);

  typedef enum integer {
    IDLE,
    REQ_ACQUIRE_LOCK,
    RELEASE_LOCK,
    REQ_FIRST_HEADER,
    LOAD_FIRST_HEADER,
    REQ_LOAD_HEADER,
    CMP_SIZE,
    REQ_INSERT_NEW_HEADER,
    REQ_DELETE_HEADER,
    WAIT_RSP_FROM_LSU
  } core_state_e;

  typedef enum integer {
    CORE_REQ_DELETE,
    CORE_REQ_INSERT,
    CORE_REQ_RELEASE,
    CORE_REQ_LOAD_HEADER,
    CORE_REQ_ACQUIRE_LOCK
  } core_op_e;


  core_state_e state_d, state_q;
  core_op_e core_op_d, core_op_q;
  logic [DATA_W-1:0] size_to_allocate_d, size_to_allocate_q;
  header_data_t header_data_from_lsu_d, header_data_from_lsu_q;
  header_data_t prev_header_data_d, prev_header_data_q;
  header_data_t curr_header_data_d, curr_header_data_q;
  header_data_t header_data_to_insert_d, header_data_to_insert_q;
  header_data_t header_data_prev_d, header_data_prev_q;

  task automatic send_req_to_lsu(input header_data_t header_data_i, input req_lsu_op_e lsu_op_i,
                                 output header_data_req_t req_to_lsu_o);
    req_to_lsu_o.header_data = header_data_i;
    req_to_lsu_o.lsu_op = lsu_op_i;
    req_to_lsu_o.val = 1;
  endtask

  always_comb begin : core_fsm
    state_d = state_q;
    size_to_allocate_d = size_to_allocate_q;
    req_to_lsu_o = '0;
    header_data_to_insert_d = header_data_to_insert_q;
    header_data_prev_d = header_data_prev_q;
    curr_header_data_d = curr_header_data_q;
    prev_header_data_d = prev_header_data_q;
    core_ready_o = 0;
    core_op_d = core_op_q;
    header_data_from_lsu_d = header_data_from_lsu_q;

    unique case (state_q)
      IDLE: begin
        size_to_allocate_d = 0;
        req_to_lsu_o = '0;
        header_data_to_insert_d = '0;
        header_data_prev_d = '0;
        curr_header_data_d = '0;
        prev_header_data_d = '0;
        core_ready_o = 1;
        header_data_from_lsu_d = '0;
        core_ready_o = 1;

        if (req_alloc_valid_i) begin
          size_to_allocate_d = size_to_allocate_i;
          state_d = REQ_ACQUIRE_LOCK;
          core_ready_o = 0;
        end
      end
      REQ_ACQUIRE_LOCK: begin
        send_req_to_lsu(.header_data_i('0), .lsu_op_i(LOCK), .req_to_lsu_o(req_to_lsu_o));
        if (lsu_ready_i) begin
          core_op_d = CORE_REQ_ACQUIRE_LOCK;
          state_d   = WAIT_RSP_FROM_LSU;
        end
      end
      REQ_LOAD_HEADER: begin
        send_req_to_lsu(.header_data_i(curr_header_data_q), .lsu_op_i(LOAD),
                        .req_to_lsu_o(req_to_lsu_o));
        if (lsu_ready_i) begin
          core_op_d = CORE_REQ_LOAD_HEADER;
          state_d   = WAIT_RSP_FROM_LSU;
        end
      end
      CMP_SIZE: begin
        core_ready_o = 1;
        if (header_data_from_lsu_q.size < size_to_allocate_q) begin
          prev_header_data_d = header_data_from_lsu_q;
          curr_header_data_d.addr = header_data_from_lsu_q.next_addr;
          state_d = REQ_LOAD_HEADER;
        end else begin  // TODO
          state_d = REQ_INSERT_NEW_HEADER;
          header_data_to_insert_d.addr = header_data_from_lsu_q.addr + 64 + size_to_allocate_q;  // TODO
          header_data_to_insert_d.size = header_data_from_lsu_q.size - size_to_allocate_q;
          header_data_to_insert_d.next_addr = header_data_from_lsu_q.next_addr;
          header_data_prev_d.addr = prev_header_data_q.addr;
          header_data_prev_d.next_addr = header_data_to_insert_d.addr;
        end
      end
      REQ_INSERT_NEW_HEADER: begin
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_data_i(header_data_to_insert_d), .lsu_op_i(INSERT),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_REQ_INSERT;
          // core_ready_o = 0;
        end
      end
      REQ_DELETE_HEADER: begin
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_data_i(header_data_prev_q), .lsu_op_i(DELETE),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_REQ_DELETE;
          // core_ready_o = 0;
        end
      end
      RELEASE_LOCK: begin
        core_ready_o = 0;
        send_req_to_lsu(.header_data_i('0), .lsu_op_i(UNLOCK), .req_to_lsu_o(req_to_lsu_o));
        state_d   = WAIT_RSP_FROM_LSU;
        core_op_d = CORE_REQ_RELEASE;
      end
      WAIT_RSP_FROM_LSU: begin
        core_ready_o = 1;
        if (rsp_from_lsu_i.val) begin
          if (core_op_q == CORE_REQ_ACQUIRE_LOCK) begin
            curr_header_data_d.addr = 'h10;
            state_d = REQ_LOAD_HEADER;
          end
          if (core_op_q == CORE_REQ_LOAD_HEADER) begin
            header_data_from_lsu_d = rsp_from_lsu_i.header_data;
            state_d = CMP_SIZE;
          end
          if (core_op_q == CORE_REQ_DELETE) begin
            state_d = RELEASE_LOCK;
          end
          if (core_op_q == CORE_REQ_INSERT) begin
            state_d = REQ_DELETE_HEADER;
          end
          if (core_op_q == CORE_REQ_RELEASE) begin
            state_d = IDLE;
          end
        end
      end

      default: ;
    endcase
  end

  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      state_q <= IDLE;
      size_to_allocate_q <= '0;
      header_data_to_insert_q <= '0;
      header_data_prev_q <= '0;
      curr_header_data_q <= 0;
      prev_header_data_q <= 0;
      header_data_from_lsu_q <= '0;
      core_op_q <= CORE_REQ_RELEASE;
    end else begin
      state_q <= state_d;
      size_to_allocate_q <= size_to_allocate_d;
      header_data_to_insert_q <= header_data_to_insert_d;
      header_data_prev_q <= header_data_prev_d;
      curr_header_data_q <= curr_header_data_d;
      prev_header_data_q <= prev_header_data_d;
      core_op_q <= core_op_d;
      header_data_from_lsu_q <= header_data_from_lsu_d;
    end
  end

endmodule
