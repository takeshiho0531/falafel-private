`include "falafel_pkg.sv"

module falafel_core
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,
    input logic is_alloc_i,
    input logic [DATA_W-1:0] size_to_allocate_i,
    input logic [DATA_W-1:0] addr_to_free_i,
    input logic req_alloc_valid_i,
    output logic core_ready_o,
    input logic lsu_ready_i,
    input header_data_rsp_t rsp_from_lsu_i,
    output header_data_req_t req_to_lsu_o
);

  typedef enum integer {
    IDLE,
    REQ_ACQUIRE_LOCK,
    REQ_RELEASE_LOCK,
    REQ_LOAD_HEADER,
    ALLOC_CMP_SIZE,
    REQ_ALLOC_INSERT_NEW_HEADER,
    REQ_ALLOC_UPDATE_OLD_HEADER,
    REQ_DELETE_HEADER,
    FREE_SEARCH_POS,
    FREE_JUDGE_MERGE,
    FREE_REQ_LOAD_TO_FILL_HEADER,
    REQ_FREE_INSERT_HEADER,
    WAIT_RSP_FROM_LSU,
    FREE_REQ_LOAD_RIGHT,
    REQ_FREE_MERGE_WITH_RIGHT_INSERT,
    REQ_FREE_MERGE_RIGHT_DELETE
  } core_state_e;

  typedef enum integer {
    CORE_REQ_UPDATE,
    CORE_REQ_DELETE,
    CORE_REQ_INSERT,
    CORE_REQ_RELEASE,
    CORE_REQ_LOAD_HEADER,
    CORE_REQ_ACQUIRE_LOCK,
    CORE_REQ_LOAD_FILL_HEADER,
    CORE_REQ_LOAD_RIGHT_HEADER,
    CORE_REQ_MERGE_RIGHT_INSERT
  } core_op_e;


  core_state_e state_d, state_q;
  core_op_e core_op_d, core_op_q;
  logic is_alloc_d, is_alloc_q;  // 1: alloc, 0: free
  logic [DATA_W-1:0] size_to_allocate_d, size_to_allocate_q;
  logic [DATA_W-1:0] addr_to_free_d, addr_to_free_q;

  header_data_t header_data_from_lsu_d, header_data_from_lsu_q;
  header_data_t prev_header_data_d, prev_header_data_q;
  header_data_t curr_header_data_d, curr_header_data_q;
  header_data_t header_data_to_update_d, header_data_to_update_q;
  header_data_t header_data_to_insert_d, header_data_to_insert_q;
  header_data_t header_data_prev_d, header_data_prev_q;
  header_data_t best_fit_header_data_d, best_fit_header_data_q;
  header_data_t best_fit_header_prev_data_d, best_fit_header_prev_data_q;
  logic [DATA_W-1:0] smallest_diff_d, smallest_diff_q;
  header_data_t fill_header_req;
  header_data_t fill_header_d, fill_header_q;
  header_data_t right_header_req;
  header_data_t right_header_d, right_header_q;
  logic does_merge_with_right, does_merge_with_left;
  header_data_t merged_header;
  header_data_t header_in_used_in_delete;

  task automatic send_req_to_lsu(input header_data_t header_data_i, input req_lsu_op_e lsu_op_i,
                                 output header_data_req_t req_to_lsu_o);
    req_to_lsu_o.header_data = header_data_i;
    req_to_lsu_o.lsu_op = lsu_op_i;
    req_to_lsu_o.val = 1;
  endtask

  always_comb begin : core_fsm
    state_d = state_q;
    size_to_allocate_d = size_to_allocate_q;
    addr_to_free_d = addr_to_free_q;

    req_to_lsu_o = '0;
    header_data_to_update_d = header_data_to_update_q;
    header_data_to_insert_d = header_data_to_insert_q;
    header_data_prev_d = header_data_prev_q;
    curr_header_data_d = curr_header_data_q;
    prev_header_data_d = prev_header_data_q;
    core_ready_o = 0;
    core_op_d = core_op_q;
    header_data_from_lsu_d = header_data_from_lsu_q;
    best_fit_header_data_d = best_fit_header_data_q;
    best_fit_header_prev_data_d = best_fit_header_prev_data_q;
    smallest_diff_d = smallest_diff_q;
    fill_header_req = '0;
    fill_header_d = fill_header_q;
    right_header_req = '0;
    right_header_d = right_header_q;
    does_merge_with_left = 0;
    does_merge_with_right = 0;
    merged_header = '0;
    header_in_used_in_delete = '0;

    unique case (state_q)
      IDLE: begin
        is_alloc_d = 0;
        size_to_allocate_d = '0;
        addr_to_free_d = '0;
        req_to_lsu_o = '0;
        header_data_to_update_d = '0;
        header_data_to_insert_d = '0;
        header_data_prev_d = '0;
        curr_header_data_d = '0;
        prev_header_data_d = '0;
        core_ready_o = 1;
        header_data_from_lsu_d = '0;
        best_fit_header_data_d = '0;
        best_fit_header_prev_data_d = '0;
        smallest_diff_d = {DATA_W{1'b1}};
        fill_header_d = '0;
        right_header_d = '0;

        if (req_alloc_valid_i) begin
          is_alloc_d = is_alloc_i ? 1 : 0;
          size_to_allocate_d = req_alloc_valid_i ? size_to_allocate_i : '0;
          addr_to_free_d = addr_to_free_i;
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
      /*
      CMP_SIZE: begin
        core_ready_o = 1;
        if (header_data_from_lsu_q.size < size_to_allocate_q) begin
          prev_header_data_d = header_data_from_lsu_q;
          curr_header_data_d.addr = header_data_from_lsu_q.next_addr;
          state_d = REQ_LOAD_HEADER;
        end else begin
          header_data_prev_d.addr = prev_header_data_q.addr;
          if (header_data_from_lsu_q.size - size_to_allocate_q >= MIN_ALLOC_SIZE) begin
            state_d = REQ_INSERT_NEW_HEADER;
            header_data_to_insert_d.addr = header_data_from_lsu_q.addr + 64 + size_to_allocate_q;  // TODO
            header_data_to_insert_d.size = header_data_from_lsu_q.size - size_to_allocate_q;
            header_data_to_insert_d.next_addr = header_data_from_lsu_q.next_addr;
            header_data_prev_d.next_addr = header_data_to_insert_d.addr;
          end else begin
            header_data_prev_d.next_addr = header_data_from_lsu_q.next_addr;
            state_d = REQ_DELETE_HEADER;
          end
        end
      end
      */
      ALLOC_CMP_SIZE: begin
        core_ready_o = 1;
        if ((header_data_from_lsu_q.size >= size_to_allocate_q) &&
      ((header_data_from_lsu_q.size - size_to_allocate_q) < smallest_diff_q)) begin
          best_fit_header_data_d = header_data_from_lsu_q;
          best_fit_header_prev_data_d = prev_header_data_q;
          smallest_diff_d = header_data_from_lsu_q.size - size_to_allocate_q;
        end

        if (header_data_from_lsu_q.next_addr != '0) begin
          prev_header_data_d = header_data_from_lsu_q;
          curr_header_data_d.addr = header_data_from_lsu_q.next_addr;
          state_d = REQ_LOAD_HEADER;
        end else begin
          if (best_fit_header_data_d.next_addr != '0) begin
            header_data_prev_d.addr = best_fit_header_prev_data_q.addr;
            if (best_fit_header_data_q.size - size_to_allocate_q >= MIN_ALLOC_SIZE) begin
              state_d = REQ_ALLOC_UPDATE_OLD_HEADER;
              header_data_to_update_d.addr = best_fit_header_data_q.addr;
              header_data_to_update_d.size = size_to_allocate_q;  // TODO
              header_data_to_update_d.next_addr = '0;
              header_data_to_insert_d.addr = best_fit_header_data_q.addr + 64 + size_to_allocate_q;  // TODO
              header_data_to_insert_d.size = best_fit_header_data_q.size - size_to_allocate_q;
              header_data_to_insert_d.next_addr = best_fit_header_data_q.next_addr;
              header_data_prev_d.next_addr = header_data_to_insert_d.addr;
            end else begin
              header_data_to_update_d.next_addr = '0;
              header_data_prev_d.next_addr = best_fit_header_data_q.next_addr;
              state_d = REQ_DELETE_HEADER;
            end
          end else begin
            header_data_prev_d.addr = best_fit_header_prev_data_d.addr;
            if (best_fit_header_data_d.size - size_to_allocate_q >= MIN_ALLOC_SIZE) begin
              state_d = REQ_ALLOC_UPDATE_OLD_HEADER;
              header_data_to_update_d.addr = best_fit_header_data_d.addr;
              header_data_to_update_d.size = size_to_allocate_q;  // TODO
              header_data_to_update_d.next_addr = '0;
              header_data_to_insert_d.addr = best_fit_header_data_d.addr + 64 + size_to_allocate_q;  // TODO
              header_data_to_insert_d.size = best_fit_header_data_d.size - size_to_allocate_q;
              header_data_to_insert_d.next_addr = best_fit_header_data_d.next_addr;
              header_data_prev_d.next_addr = header_data_to_insert_d.addr;
            end else begin
              header_data_to_update_d.next_addr = '0;
              header_data_prev_d.next_addr = best_fit_header_data_d.next_addr;
              state_d = REQ_DELETE_HEADER;
            end
          end
        end
      end
      REQ_ALLOC_UPDATE_OLD_HEADER: begin
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_data_i(header_data_to_update_q), .lsu_op_i(UPDATE),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_REQ_UPDATE;
        end
      end
      REQ_ALLOC_INSERT_NEW_HEADER: begin
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_data_i(header_data_to_insert_q), .lsu_op_i(ALLOC_INSERT),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_REQ_INSERT;
        end
      end
      REQ_DELETE_HEADER: begin
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_data_i(header_data_prev_q), .lsu_op_i(DELETE),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_REQ_DELETE;
        end
      end
      FREE_SEARCH_POS: begin
        // if ((addr_to_free_q > header_data_from_lsu_q.addr) &&
        // ((addr_to_free_q < header_data_from_lsu_q.next_addr) |
        // (header_data_from_lsu_q.next_addr == '0))) begin
        if ((addr_to_free_q > header_data_from_lsu_q.addr) &&
        (addr_to_free_q < header_data_from_lsu_q.next_addr)) begin
          curr_header_data_d = header_data_from_lsu_q;
          state_d = FREE_REQ_LOAD_TO_FILL_HEADER;

        end else begin
          curr_header_data_d.addr = header_data_from_lsu_q.next_addr;
          state_d = REQ_LOAD_HEADER;
        end
      end
      FREE_REQ_LOAD_TO_FILL_HEADER: begin
        fill_header_req.addr = addr_to_free_q;
        send_req_to_lsu(.header_data_i(fill_header_req), .lsu_op_i(LOAD),
                        .req_to_lsu_o(req_to_lsu_o));
        if (lsu_ready_i) begin
          core_op_d = CORE_REQ_LOAD_FILL_HEADER;
          state_d   = WAIT_RSP_FROM_LSU;
        end
      end
      FREE_JUDGE_MERGE: begin
        fill_header_d = header_data_from_lsu_q;
        if (addr_to_free_q + BLOCK_HEADER_SIZE + fill_header_d.size
        == curr_header_data_q.next_addr) begin
          does_merge_with_right = 1;
          state_d = FREE_REQ_LOAD_RIGHT;
        end
        if (curr_header_data_q.addr + BLOCK_HEADER_SIZE + curr_header_data_q.size
        == addr_to_free_q) begin
          does_merge_with_left = 1;
        end
        if (!does_merge_with_left && !does_merge_with_right) begin
          header_data_to_insert_d.addr = addr_to_free_q;
          header_data_to_insert_d.next_addr = header_data_from_lsu_q.next_addr;
          header_data_prev_d.addr = header_data_from_lsu_q.addr;
          header_data_prev_d.next_addr = header_data_to_insert_d.addr;
          state_d = REQ_FREE_INSERT_HEADER;
        end
      end
      FREE_REQ_LOAD_RIGHT: begin
        right_header_req.addr = curr_header_data_q.next_addr;
        send_req_to_lsu(.header_data_i(right_header_req), .lsu_op_i(LOAD),
                        .req_to_lsu_o(req_to_lsu_o));
        if (lsu_ready_i) begin
          core_op_d = CORE_REQ_LOAD_RIGHT_HEADER;
          state_d   = WAIT_RSP_FROM_LSU;
        end
      end
      REQ_FREE_MERGE_WITH_RIGHT_INSERT: begin
        right_header_d = header_data_from_lsu_q;
        merged_header.addr = addr_to_free_q;
        merged_header.next_addr = right_header_d.next_addr;
        merged_header.size = right_header_d.size + fill_header_q.size;
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_data_i(merged_header), .lsu_op_i(ALLOC_INSERT),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_REQ_MERGE_RIGHT_INSERT;
        end
      end
      REQ_FREE_MERGE_RIGHT_DELETE: begin
        if (lsu_ready_i) begin
          header_in_used_in_delete = curr_header_data_q;
          header_in_used_in_delete.next_addr = addr_to_free_q;
          send_req_to_lsu(.header_data_i(header_in_used_in_delete), .lsu_op_i(DELETE),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_REQ_DELETE;
        end
      end
      REQ_FREE_INSERT_HEADER: begin
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_data_i(header_data_to_insert_q), .lsu_op_i(FREE_INSERT),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_REQ_INSERT;
        end
      end
      REQ_RELEASE_LOCK: begin
        send_req_to_lsu(.header_data_i('0), .lsu_op_i(UNLOCK), .req_to_lsu_o(req_to_lsu_o));
        state_d   = WAIT_RSP_FROM_LSU;
        core_op_d = CORE_REQ_RELEASE;
      end
      WAIT_RSP_FROM_LSU: begin
        core_ready_o = 1;
        if (rsp_from_lsu_i.val) begin
          unique case (core_op_q)
            CORE_REQ_ACQUIRE_LOCK: begin
              curr_header_data_d.addr = 'h10;
              state_d = REQ_LOAD_HEADER;
            end
            CORE_REQ_LOAD_HEADER: begin
              header_data_from_lsu_d = rsp_from_lsu_i.header_data;
              if (is_alloc_q) begin
                state_d = ALLOC_CMP_SIZE;
              end else begin
                state_d = FREE_SEARCH_POS;
              end
            end
            CORE_REQ_LOAD_FILL_HEADER: begin
              header_data_from_lsu_d = rsp_from_lsu_i.header_data;
              state_d = FREE_JUDGE_MERGE;
            end
            CORE_REQ_LOAD_RIGHT_HEADER: begin
              header_data_from_lsu_d = rsp_from_lsu_i.header_data;
              state_d = REQ_FREE_MERGE_WITH_RIGHT_INSERT;
            end
            CORE_REQ_MERGE_RIGHT_INSERT: state_d = REQ_FREE_MERGE_RIGHT_DELETE;
            CORE_REQ_DELETE: state_d = REQ_RELEASE_LOCK;
            CORE_REQ_UPDATE: state_d = REQ_ALLOC_INSERT_NEW_HEADER;
            CORE_REQ_INSERT: state_d = REQ_DELETE_HEADER;
            CORE_REQ_RELEASE: state_d = IDLE;
          endcase
        end
      end

      default: ;
    endcase
  end

  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      state_q <= IDLE;
      is_alloc_q <= 0;
      size_to_allocate_q <= '0;
      addr_to_free_q <= '0;
      header_data_to_update_q <= '0;
      header_data_to_insert_q <= '0;
      header_data_prev_q <= '0;
      curr_header_data_q <= 0;
      prev_header_data_q <= 0;
      header_data_from_lsu_q <= '0;
      core_op_q <= CORE_REQ_RELEASE;
      best_fit_header_data_q <= '0;
      best_fit_header_prev_data_q <= '0;
      smallest_diff_q <= '0;
      fill_header_q <= '0;
      right_header_q <= '0;
    end else begin
      state_q <= state_d;
      is_alloc_q <= is_alloc_d;
      size_to_allocate_q <= size_to_allocate_d;
      addr_to_free_q <= addr_to_free_d;
      header_data_to_update_q <= header_data_to_update_d;
      header_data_to_insert_q <= header_data_to_insert_d;
      header_data_prev_q <= header_data_prev_d;
      curr_header_data_q <= curr_header_data_d;
      prev_header_data_q <= prev_header_data_d;
      core_op_q <= core_op_d;
      header_data_from_lsu_q <= header_data_from_lsu_d;
      best_fit_header_data_q <= best_fit_header_data_d;
      best_fit_header_prev_data_q <= best_fit_header_prev_data_d;
      smallest_diff_q <= smallest_diff_d;
      fill_header_q <= fill_header_d;
      right_header_q <= right_header_d;
    end
  end

endmodule
