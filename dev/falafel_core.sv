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
    input header_rsp_t rsp_from_lsu_i,
    output header_req_t req_to_lsu_o
);

  typedef enum integer {
    IDLE,
    REQ_ACQUIRE_LOCK,
    REQ_RELEASE_LOCK,
    REQ_LOAD_HEADER,
    ALLOC_SEARCH_POS,
    REQ_CREATE_NEW_HEADER,
    REQ_ALLOC_ADJUST_ALLOCATED_HEADER,
    REQ_ADJUST_LINK,
    FREE_SEARCH_POS,
    FREE_CHECK_NEIGHBORS,
    WAIT_RSP_FROM_LSU,
    REQ_FREE_MERGE_RIGHT_HEADER
  } core_state_e;

  typedef enum integer {
    CORE_ADJUST_ALLOCATED_HEADER,
    CORE_ADJUST_LINK,
    CORE_CREATE_NEW_HEADER,
    CORE_RELEASE,
    CORE_LOAD_HEADER,
    CORE_ACQUIRE_LOCK,
    CORE_LOAD_FREE_TARGET_HEADER,
    CORE_LOAD_RIGHT_HEADER,
    CORE_MERGE_RIGHT
  } core_op_e;

  typedef enum integer {
    SEARCH,
    FREE_TARGET_HEADER,
    FREE_RIGHT_HEADER,
    FREE_LEFT_HEADER
  } load_type_t;

  core_state_e state_d, state_q;
  core_op_e core_op_d, core_op_q;
  logic is_alloc_d, is_alloc_q;  // 1: alloc, 0: free
  logic [DATA_W-1:0] size_to_allocate_d, size_to_allocate_q;
  logic [DATA_W-1:0] addr_to_free_d, addr_to_free_q;

  header_t header_from_lsu_d, header_from_lsu_q;
  header_t prev_header_d, prev_header_q;
  header_t curr_header_d, curr_header_q;
  header_t alloc_target_header_d, alloc_target_header_q;
  header_t header_to_create_d, header_to_create_q;
  header_t header_to_adjust_link_d, header_to_adjust_link_q;
  header_t best_fit_header_d, best_fit_header_q;
  header_t best_fit_header_prev_d, best_fit_header_prev_q;
  logic [DATA_W-1:0] smallest_diff_d, smallest_diff_q;
  header_t load_req_header;
  header_t fill_header_d, fill_header_q;
  header_t right_header_d, right_header_q;
  logic does_merge_with_right, does_merge_with_left;
  header_t merged_block_header;
  header_t header_to_adjust_link_free;
  load_type_t load_type_d, load_type_q;

  task automatic send_req_to_lsu(input header_t header_i, input req_lsu_op_e lsu_op_i,
                                 output header_req_t req_to_lsu_o);
    req_to_lsu_o.header = header_i;
    req_to_lsu_o.lsu_op = lsu_op_i;
    req_to_lsu_o.val = 1;
  endtask

  always_comb begin : core_fsm
    state_d = state_q;
    size_to_allocate_d = size_to_allocate_q;
    addr_to_free_d = addr_to_free_q;

    req_to_lsu_o = '0;
    alloc_target_header_d = alloc_target_header_q;
    header_to_create_d = header_to_create_q;
    header_to_adjust_link_d = header_to_adjust_link_q;
    curr_header_d = curr_header_q;
    prev_header_d = prev_header_q;
    core_ready_o = 0;
    core_op_d = core_op_q;
    header_from_lsu_d = header_from_lsu_q;
    best_fit_header_d = best_fit_header_q;
    best_fit_header_prev_d = best_fit_header_prev_q;
    smallest_diff_d = smallest_diff_q;
    load_req_header = '0;
    fill_header_d = fill_header_q;
    right_header_d = right_header_q;
    does_merge_with_left = 0;
    does_merge_with_right = 0;
    merged_block_header = '0;
    header_to_adjust_link_free = '0;
    load_type_d = load_type_q;

    unique case (state_q)
      IDLE: begin
        is_alloc_d = 0;
        size_to_allocate_d = '0;
        addr_to_free_d = '0;
        req_to_lsu_o = '0;
        alloc_target_header_d = '0;
        header_to_create_d = '0;
        header_to_adjust_link_d = '0;
        curr_header_d = '0;
        prev_header_d = '0;
        core_ready_o = 1;
        header_from_lsu_d = '0;
        best_fit_header_d = '0;
        best_fit_header_prev_d = '0;
        smallest_diff_d = {DATA_W{1'b1}};
        fill_header_d = '0;
        right_header_d = '0;
        load_type_d = SEARCH;

        if (req_alloc_valid_i) begin
          is_alloc_d = is_alloc_i ? 1 : 0;
          size_to_allocate_d = req_alloc_valid_i ? size_to_allocate_i : '0;
          addr_to_free_d = addr_to_free_i;
          state_d = REQ_ACQUIRE_LOCK;
          core_ready_o = 0;
        end
      end
      REQ_ACQUIRE_LOCK: begin
        send_req_to_lsu(.header_i('0), .lsu_op_i(LOCK), .req_to_lsu_o(req_to_lsu_o));
        if (lsu_ready_i) begin
          core_op_d = CORE_ACQUIRE_LOCK;
          state_d   = WAIT_RSP_FROM_LSU;
        end
      end
      REQ_LOAD_HEADER: begin
        unique case (load_type_q)
          SEARCH: begin
            load_req_header.addr = curr_header_q.addr;
            core_op_d = CORE_LOAD_HEADER;
          end
          FREE_TARGET_HEADER: begin
            load_req_header.addr = addr_to_free_q;
            core_op_d = CORE_LOAD_FREE_TARGET_HEADER;
          end
          FREE_RIGHT_HEADER: begin
            load_req_header.addr = curr_header_q.next_addr;
            core_op_d = CORE_LOAD_RIGHT_HEADER;
          end
          default: ;
        endcase
        send_req_to_lsu(.header_i(load_req_header), .lsu_op_i(LOAD), .req_to_lsu_o(req_to_lsu_o));
        if (lsu_ready_i) begin
          state_d = WAIT_RSP_FROM_LSU;
        end
      end
      /*
      CMP_SIZE: begin
        core_ready_o = 1;
        if (header_from_lsu_q.size < size_to_allocate_q) begin
          prev_header_d = header_from_lsu_q;
          curr_header_d.addr = header_from_lsu_q.next_addr;
          state_d = REQ_LOAD_HEADER;
        end else begin
          header_prev_d.addr = prev_header_q.addr;
          if (header_from_lsu_q.size - size_to_allocate_q >= MIN_ALLOC_SIZE) begin
            state_d = REQ_INSERT_NEW_HEADER;
            header_to_insert_d.addr = header_from_lsu_q.addr + 64 + size_to_allocate_q;  // TODO
            header_to_insert_d.size = header_from_lsu_q.size - size_to_allocate_q;
            header_to_insert_d.next_addr = header_from_lsu_q.next_addr;
            header_prev_d.next_addr = header_to_insert_d.addr;
          end else begin
            header_prev_d.next_addr = header_from_lsu_q.next_addr;
            state_d = REQ_DELETE_HEADER;
          end
        end
      end
      */
      ALLOC_SEARCH_POS: begin
        core_ready_o = 1;
        if ((header_from_lsu_q.size >= size_to_allocate_q) &&
      ((header_from_lsu_q.size - size_to_allocate_q) < smallest_diff_q)) begin
          best_fit_header_d = header_from_lsu_q;
          best_fit_header_prev_d = prev_header_q;
          smallest_diff_d = header_from_lsu_q.size - size_to_allocate_q;
        end

        if (header_from_lsu_q.next_addr != '0) begin
          prev_header_d = header_from_lsu_q;
          curr_header_d.addr = header_from_lsu_q.next_addr;
          state_d = REQ_LOAD_HEADER;
          load_type_d = SEARCH;
        end else begin
          if (best_fit_header_d.next_addr != '0) begin
            header_to_adjust_link_d.addr = best_fit_header_prev_q.addr;
            if (best_fit_header_q.size - size_to_allocate_q >= MIN_ALLOC_SIZE) begin
              state_d = REQ_ALLOC_ADJUST_ALLOCATED_HEADER;
              alloc_target_header_d.addr = best_fit_header_q.addr;
              alloc_target_header_d.size = size_to_allocate_q;  // TODO
              alloc_target_header_d.next_addr = '0;
              header_to_create_d.addr = best_fit_header_q.addr + 64 + size_to_allocate_q;  // TODO
              header_to_create_d.size = best_fit_header_q.size - size_to_allocate_q;
              header_to_create_d.next_addr = best_fit_header_q.next_addr;
              header_to_adjust_link_d.next_addr = header_to_create_d.addr;
            end else begin
              alloc_target_header_d.next_addr = '0;
              header_to_adjust_link_d.next_addr = best_fit_header_q.next_addr;
              state_d = REQ_ADJUST_LINK;
            end
          end else begin
            header_to_adjust_link_d.addr = best_fit_header_prev_d.addr;
            if (best_fit_header_d.size - size_to_allocate_q >= MIN_ALLOC_SIZE) begin
              state_d = REQ_ALLOC_ADJUST_ALLOCATED_HEADER;
              alloc_target_header_d.addr = best_fit_header_d.addr;
              alloc_target_header_d.size = size_to_allocate_q;  // TODO
              alloc_target_header_d.next_addr = '0;
              header_to_create_d.addr = best_fit_header_d.addr + 64 + size_to_allocate_q;  // TODO
              header_to_create_d.size = best_fit_header_d.size - size_to_allocate_q;
              header_to_create_d.next_addr = best_fit_header_d.next_addr;
              header_to_adjust_link_d.next_addr = header_to_create_d.addr;
            end else begin
              alloc_target_header_d.next_addr = '0;
              header_to_adjust_link_d.next_addr = best_fit_header_d.next_addr;
              state_d = REQ_ADJUST_LINK;
            end
          end
        end
      end
      REQ_ALLOC_ADJUST_ALLOCATED_HEADER: begin
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_i(alloc_target_header_q),
                          .lsu_op_i(EDIT_SIZE_AND_NEXT_ADDR),  // TODO
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_ADJUST_ALLOCATED_HEADER;
        end
      end
      REQ_CREATE_NEW_HEADER: begin
        if (lsu_ready_i) begin
          if (is_alloc_q) begin
            send_req_to_lsu(.header_i(header_to_create_q), .lsu_op_i(EDIT_SIZE_AND_NEXT_ADDR),
                            .req_to_lsu_o(req_to_lsu_o));
          end else begin
            send_req_to_lsu(.header_i(header_to_create_q), .lsu_op_i(EDIT_NEXT_ADDR),
                            .req_to_lsu_o(req_to_lsu_o));
          end

          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_CREATE_NEW_HEADER;
        end
      end
      REQ_ADJUST_LINK: begin
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_i(header_to_adjust_link_q), .lsu_op_i(EDIT_NEXT_ADDR),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_ADJUST_LINK;
        end
      end
      FREE_SEARCH_POS: begin
        // if ((addr_to_free_q > header_from_lsu_q.addr) &&
        // ((addr_to_free_q < header_from_lsu_q.next_addr) |
        // (header_from_lsu_q.next_addr == '0))) begin
        if ((addr_to_free_q > header_from_lsu_q.addr) &&
        (addr_to_free_q < header_from_lsu_q.next_addr)) begin
          curr_header_d = header_from_lsu_q;
          state_d = REQ_LOAD_HEADER;
          load_type_d = FREE_TARGET_HEADER;

        end else begin
          curr_header_d.addr = header_from_lsu_q.next_addr;
          state_d = REQ_LOAD_HEADER;
          load_type_d = SEARCH;
        end
      end
      FREE_CHECK_NEIGHBORS: begin
        fill_header_d = header_from_lsu_q;
        if (addr_to_free_q + BLOCK_HEADER_SIZE + fill_header_d.size
        == curr_header_q.next_addr) begin
          does_merge_with_right = 1;
          state_d = REQ_LOAD_HEADER;
          load_type_d = FREE_RIGHT_HEADER;
          header_to_adjust_link_d = curr_header_q;
          header_to_adjust_link_d.next_addr = addr_to_free_q;
        end
        if (curr_header_q.addr + BLOCK_HEADER_SIZE + curr_header_q.size == addr_to_free_q) begin
          does_merge_with_left = 1;
        end
        if (!does_merge_with_left && !does_merge_with_right) begin
          header_to_create_d.addr = addr_to_free_q;
          header_to_create_d.next_addr = header_from_lsu_q.next_addr;
          header_to_adjust_link_d.addr = header_from_lsu_q.addr;
          header_to_adjust_link_d.next_addr = header_to_create_d.addr;
          state_d = REQ_CREATE_NEW_HEADER;
        end
      end
      REQ_FREE_MERGE_RIGHT_HEADER: begin
        right_header_d = header_from_lsu_q;
        merged_block_header.addr = addr_to_free_q;
        merged_block_header.next_addr = right_header_d.next_addr;
        merged_block_header.size = right_header_d.size + fill_header_q.size;
        if (lsu_ready_i) begin
          send_req_to_lsu(.header_i(merged_block_header), .lsu_op_i(EDIT_SIZE_AND_NEXT_ADDR),
                          .req_to_lsu_o(req_to_lsu_o));
          state_d   = WAIT_RSP_FROM_LSU;
          core_op_d = CORE_MERGE_RIGHT;
        end
      end
      REQ_RELEASE_LOCK: begin
        send_req_to_lsu(.header_i('0), .lsu_op_i(UNLOCK), .req_to_lsu_o(req_to_lsu_o));
        state_d   = WAIT_RSP_FROM_LSU;
        core_op_d = CORE_RELEASE;
      end
      WAIT_RSP_FROM_LSU: begin
        core_ready_o = 1;
        if (rsp_from_lsu_i.val) begin
          unique case (core_op_q)
            CORE_ACQUIRE_LOCK: begin
              curr_header_d.addr = 'h10;
              state_d = REQ_LOAD_HEADER;
              load_type_d = SEARCH;
            end
            CORE_LOAD_HEADER: begin
              header_from_lsu_d = rsp_from_lsu_i.header;
              if (is_alloc_q) begin
                state_d = ALLOC_SEARCH_POS;
              end else begin
                state_d = FREE_SEARCH_POS;
              end
            end
            CORE_LOAD_FREE_TARGET_HEADER: begin
              header_from_lsu_d = rsp_from_lsu_i.header;
              state_d = FREE_CHECK_NEIGHBORS;
            end
            CORE_LOAD_RIGHT_HEADER: begin
              header_from_lsu_d = rsp_from_lsu_i.header;
              state_d = REQ_FREE_MERGE_RIGHT_HEADER;
            end
            CORE_MERGE_RIGHT: state_d = REQ_ADJUST_LINK;
            CORE_ADJUST_LINK: state_d = REQ_RELEASE_LOCK;
            CORE_ADJUST_ALLOCATED_HEADER: state_d = REQ_CREATE_NEW_HEADER;
            CORE_CREATE_NEW_HEADER: state_d = REQ_ADJUST_LINK;
            CORE_RELEASE: state_d = IDLE;
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
      alloc_target_header_q <= '0;
      header_to_create_q <= '0;
      header_to_adjust_link_q <= '0;
      curr_header_q <= 0;
      prev_header_q <= 0;
      header_from_lsu_q <= '0;
      core_op_q <= CORE_RELEASE;
      best_fit_header_q <= '0;
      best_fit_header_prev_q <= '0;
      smallest_diff_q <= '0;
      fill_header_q <= '0;
      right_header_q <= '0;
      load_type_q <= SEARCH;
    end else begin
      state_q <= state_d;
      is_alloc_q <= is_alloc_d;
      size_to_allocate_q <= size_to_allocate_d;
      addr_to_free_q <= addr_to_free_d;
      alloc_target_header_q <= alloc_target_header_d;
      header_to_create_q <= header_to_create_d;
      header_to_adjust_link_q <= header_to_adjust_link_d;
      curr_header_q <= curr_header_d;
      prev_header_q <= prev_header_d;
      core_op_q <= core_op_d;
      header_from_lsu_q <= header_from_lsu_d;
      best_fit_header_q <= best_fit_header_d;
      best_fit_header_prev_q <= best_fit_header_prev_d;
      smallest_diff_q <= smallest_diff_d;
      fill_header_q <= fill_header_d;
      right_header_q <= right_header_d;
      load_type_q <= load_type_d;
    end
  end

endmodule
