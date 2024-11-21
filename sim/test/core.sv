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
    ALLOC_ACQUIRE_LOCK,
    ALLOC_RELEASE_LOCK,
    ALLOC_WAIT_RELEASE_LOCK,
    ALLOC_REQ_FIRST_HEADER,
    ALLOC_LOAD_FIRST_HEADER,
    ALLOC_LOAD_HEADER,
    ALLOC_CMP_SIZE,
    ALLOC_INSERT_NEW_HEADER,
    ALLOC_WAIT_INSERT,
    ALLOC_DELETE_HEADER,
    ALLOC_WAIT_DELETE
  } core_state_e;


  core_state_e state_d, state_q;
  logic [DATA_W-1:0] size_to_allocate_d, size_to_allocate_q;
  header_data_t first_header;
  header_data_t prev_header_data_d, prev_header_data_q;
  header_data_t curr_header_data_d, curr_header_data_q;
  header_data_t header_data_to_insert_d, header_data_to_insert_q;
  header_data_t header_data_prev_d, header_data_to_prev_q;
  header_data_t first_header_data;
  logic [DATA_W-1:0] remaining_size, remaining_size_q;
  logic [DATA_W-1:0] fit_addr_d, fit_addr_q;

  task automatic request_to_lsu(header_data_t header_data, lsu_op_e lsu_op);
    req_to_lsu_o.header_data = header_data;
    req_to_lsu_o.lsu_op = lsu_op;
    req_to_lsu_o.val = 1;
  endtask

  always_comb begin : core_fsm
    state_d = state_q;
    size_to_allocate_d = size_to_allocate_q;
    // req_to_lsu_o = '0;
    first_header = '0;
    header_data_to_insert_d = header_data_to_insert_q;
    header_data_prev_d = header_data_to_prev_q;
    curr_header_data_d = curr_header_data_q;
    prev_header_data_d = prev_header_data_q;
    fit_addr_d = fit_addr_q;
    remaining_size = remaining_size_q;
    core_ready_o = 0;

    unique case (state_q)
      IDLE: begin
        size_to_allocate_d = 0;
        req_to_lsu_o = '0;
        header_data_to_insert_d = '0;
        header_data_prev_d = '0;
        curr_header_data_d = '0;
        prev_header_data_d = '0;
        fit_addr_d = '0;
        remaining_size = '0;
        core_ready_o = 1;

        if (req_alloc_valid_i) begin
          size_to_allocate_d = size_to_allocate_i;
          request_to_lsu(.header_data('0), .lsu_op(LOCK));
          state_d = ALLOC_ACQUIRE_LOCK;
          core_ready_o = 0;
        end
      end
      ALLOC_ACQUIRE_LOCK: begin
        core_ready_o = 1;
        if (rsp_from_lsu_i.val) begin
          state_d = ALLOC_REQ_FIRST_HEADER;
          // core_ready_o = 0;
        end
      end
      ALLOC_REQ_FIRST_HEADER: begin
        if (lsu_ready_i) begin
          // core_ready_o = 0;
          req_to_lsu_o.header_data.addr = 'h10;
          req_to_lsu_o.lsu_op = LOAD;
          req_to_lsu_o.val = 1;
          state_d = ALLOC_LOAD_FIRST_HEADER;
        end
      end
      ALLOC_LOAD_FIRST_HEADER: begin
        core_ready_o = 1;
        if (rsp_from_lsu_i.val) begin
          first_header_data  = rsp_from_lsu_i.header_data;
          curr_header_data_d = first_header_data;
          if (curr_header_data_d.size > size_to_allocate_i) begin
            fit_addr_d = rsp_from_lsu_i.header_data.addr;
            state_d = ALLOC_DELETE_HEADER;
          end else begin
            prev_header_data_d = rsp_from_lsu_i.header_data;
            curr_header_data_d.addr = rsp_from_lsu_i.header_data.next_addr;
            state_d = ALLOC_LOAD_HEADER;
          end
        end
      end
      ALLOC_LOAD_HEADER: begin
        if (lsu_ready_i) begin
          request_to_lsu(.header_data(curr_header_data_q), .lsu_op(LOAD));
          state_d = ALLOC_CMP_SIZE;
          // core_ready_o = 0;
        end
      end
      ALLOC_CMP_SIZE: begin
        core_ready_o = 1;
        if (rsp_from_lsu_i.val) begin
          if (rsp_from_lsu_i.header_data.size < size_to_allocate_d) begin
            prev_header_data_d = rsp_from_lsu_i.header_data;
            curr_header_data_d.addr = rsp_from_lsu_i.header_data.next_addr;
            state_d = ALLOC_LOAD_HEADER;
          end else begin
            curr_header_data_d = rsp_from_lsu_i.header_data;
            header_data_prev_d = prev_header_data_q;
            fit_addr_d = rsp_from_lsu_i.header_data.addr;
            remaining_size = rsp_from_lsu_i.header_data.size - size_to_allocate_q;
            // if (remaining_size > {DATA_W{$bits(curr_header_data_d)}}) begin
            state_d = ALLOC_INSERT_NEW_HEADER;
            header_data_to_insert_d.addr = curr_header_data_q.addr + 64 + size_to_allocate_q;
            header_data_to_insert_d.size = remaining_size;
            header_data_to_insert_d.next_addr = curr_header_data_q.next_addr;
            header_data_prev_d.next_addr = header_data_to_insert_d.addr;
            // end
            // else begin // TODO
            //   state_d = ALLOC_DELETE_HEADER;
            // end
          end
        end
      end
      ALLOC_INSERT_NEW_HEADER: begin
        if (lsu_ready_i) begin
          request_to_lsu(.header_data(header_data_to_insert_d), .lsu_op(INSERT));
          state_d = ALLOC_WAIT_INSERT;
          // core_ready_o = 0;
        end
      end
      ALLOC_WAIT_INSERT: begin
        core_ready_o = 1;
        if (rsp_from_lsu_i.val) begin
          state_d = ALLOC_DELETE_HEADER;
        end
      end
      ALLOC_DELETE_HEADER: begin
        if (lsu_ready_i) begin
          request_to_lsu(.header_data(header_data_to_prev_q), .lsu_op(DELETE));
          state_d = ALLOC_WAIT_DELETE;
          // core_ready_o = 0;
        end
      end
      ALLOC_WAIT_DELETE: begin
        core_ready_o = 1;
        if (rsp_from_lsu_i.val) begin
          state_d = ALLOC_RELEASE_LOCK;
        end
      end
      ALLOC_RELEASE_LOCK: begin
        core_ready_o = 0;
        request_to_lsu(.header_data('0), .lsu_op(UNLOCK));
        state_d = ALLOC_WAIT_RELEASE_LOCK;
      end
      ALLOC_WAIT_RELEASE_LOCK: begin
        core_ready_o = 1;
        if (lsu_ready_i) begin
          state_d = IDLE;
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
      header_data_to_prev_q <= '0;
      curr_header_data_q <= 0;
      prev_header_data_q <= 0;
      fit_addr_q <= '0;
      remaining_size_q <= '0;
    end else begin
      state_q <= state_d;
      size_to_allocate_q <= size_to_allocate_d;
      header_data_to_insert_q <= header_data_to_insert_d;
      header_data_to_prev_q <= header_data_prev_d;
      curr_header_data_q <= curr_header_data_d;
      prev_header_data_q <= prev_header_data_d;
      fit_addr_q <= fit_addr_d;
      remaining_size_q <= remaining_size;
    end
  end

endmodule
