module falafel_core
  import falafel_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,
    input config_regs_t falafel_config,

    //----------- fifo interfaces ------------//
    input  logic              alloc_fifo_empty_i,
    output logic              alloc_fifo_read_o,
    input  logic [DATA_W-1:0] alloc_fifo_dout_i,

    input  logic              free_fifo_empty_i,
    output logic              free_fifo_read_o,
    input  logic [DATA_W-1:0] free_fifo_dout_i,

    input  logic              resp_fifo_full_i,
    output logic              resp_fifo_write_o,
    output logic [DATA_W-1:0] resp_fifo_din_o,

    //----------- memory request -----------//
    input  logic              mem_req_rdy_i,       // mem ready
    output logic              mem_req_val_o,       // req valid
    output logic              mem_req_is_write_i,  // 1 for write, 0 for read
    output logic [DATA_W-1:0] mem_req_addr_o,      // address
    output logic [DATA_W-1:0] mem_req_data_o,      // write data

    //----------- memory response ------------//
    input  logic              mem_rsp_val_i,  // resp valid
    output logic              mem_rsp_rdy_o,  // falafel ready
    input  logic [DATA_W-1:0] mem_rsp_data_i, // resp data

    //----------- fifo interfaces ------------//
    output logic  sbrk_req_val_o,
    input  logic  sbrk_rsp_val_i,
    input  word_t sbrk_rsp_ptr_o
);


  typedef enum integer {
    STATE_INIT,
    STATE_IDLE,

    STATE_ALLOC_CHECK_SIZE,
    STATE_ALLOC_LOAD_FREE_PTR,
    STATE_ALLOC_WAIT_FREE_PTR,
    STATE_ALLOC_LOAD_BLOCK,
    STATE_ALLOC_WAIT_BLOCK,
    STATE_ALLOC_PROCESS_BLOCK,
    STATE_ALLOC_CALC_SPLIT,
    STATE_ALLOC_STORE_NEW_BLOCK,
    STATE_ALLOC_WAIT_STORE,
    STATE_ALLOC_UPDATE_OLD_BLOCK,
    STATE_ALLOC_WAIT_UPDATE,
    STATE_ALLOC_REMOVE_FREELIST,
    STATE_ALLOC_WAIT_REMOVE,
    STATE_WRITE_RESPONSE,

    STATE_SBRK,
    STATE_WRITE_ERROR
  } core_state_e;


  // Internal signals
  core_state_e state_d, state_q;
  word_t alloc_size_d, alloc_size_q;
  word_t alloc_ptr_d, alloc_ptr_q;
  word_t freelist_ptr_d, freelist_ptr_q;

  logic change_block_d, change_block_q;

  word_t buffered_word_d, buffered_word_q;
  free_block_t buffered_block_d, buffered_block_q;
  word_t current_block_ptr_d, current_block_ptr_q;
  word_t prev_block_ptr_d, prev_block_ptr_q;  // pointer to previous block's next_ptr
  word_t next_block_ptr_d, next_block_ptr_q;  // pointer to next block
  word_t target_block_ptr_d, target_block_ptr_q;  // pointer to next block

  localparam SEL_REAL_BLOCK = 1'b0;  // when loading an actual block
  localparam SEL_FAKE_BLOCK = 1'b1;  // when loading the free ptr we cast it to a block
  logic        sel_block;

  // LSU signals
  logic        lsu_req_val;  // request valid
  logic        lsu_req_rdy;  // request ready
  lsu_op_e     lsu_req_op;  // request operation type
  word_t       lsu_req_addr;  // request addr
  word_t       lsu_req_word;  // request data for word ops
  free_block_t lsu_req_block;  // request data for block ops

  logic        lsu_rsp_val;  // response valid
  logic        lsu_rsp_rdy;  // response ready
  word_t       lsu_rsp_word;  // response data for word ops
  free_block_t lsu_rsp_block;  // response data for block ops

  // block parser signals
  free_block_t bp_block;
  word_t       bp_requested_size;
  logic        bp_is_null;  // is block next_ptr null
  logic        bp_is_big_enough;  // is block big enough
  word_t       bp_next_ptr;  // next block ptr


  free_block_t fake_block;
  assign fake_block = {word_t'(0), lsu_rsp_word};

  assign buffered_word_d = (lsu_rsp_val && lsu_rsp_rdy) ? lsu_rsp_word : buffered_word_q;
  assign buffered_block_d = change_block_d ? {buffered_block_q.size, current_block_ptr_q + BLOCK_HEADER_SIZE + alloc_size_q}
                          : ((lsu_rsp_val && lsu_rsp_rdy) ? ((sel_block == SEL_FAKE_BLOCK) ? fake_block : lsu_rsp_block) : buffered_block_q);
  assign current_block_ptr_d = (lsu_req_val && lsu_req_rdy) ? lsu_req_addr : current_block_ptr_q;
  // assign prev_block_ptr_d = (lsu_req_val && lsu_req_rdy) ? current_block_ptr_q : prev_block_ptr_q;

  assign bp_block = buffered_block_q;
  assign bp_requested_size = alloc_size_q;


  always_comb begin
    state_d = state_q;

    alloc_size_d = alloc_size_q;
    alloc_ptr_d = alloc_ptr_q;
    freelist_ptr_d = freelist_ptr_q;

    sel_block = SEL_REAL_BLOCK;
    change_block_d = 1'b0;

    prev_block_ptr_d = prev_block_ptr_q;
    next_block_ptr_d = next_block_ptr_q;
    target_block_ptr_d = target_block_ptr_q;

    lsu_req_val = 1'b0;
    lsu_rsp_rdy = 1'b0;
    lsu_req_op = LSU_OP_LOAD_WORD;
    lsu_req_addr = NULL_PTR;
    // TOOD: lsu_req_word
    // TOOD: lsu_req_block

    alloc_fifo_read_o = 1'b0;
    free_fifo_read_o = 1'b0;
    resp_fifo_write_o = 1'b0;

    sbrk_req_val_o = 1'b0;

    unique case (state_q)
      STATE_INIT: begin
        state_d = STATE_IDLE;
      end

      STATE_IDLE: begin
        if (!alloc_fifo_empty_i) begin
          state_d = STATE_ALLOC_CHECK_SIZE;

          alloc_fifo_read_o = 1'b1;
          alloc_size_d = alloc_fifo_dout_i;

        end else if (!free_fifo_empty_i) begin
          free_fifo_read_o = 1'b1;
          // TODO
        end
      end

      STATE_ALLOC_CHECK_SIZE: begin
        if (|alloc_size_q) begin
          state_d = STATE_ALLOC_LOAD_FREE_PTR;
          alloc_size_d = align_size(alloc_size_q, BLOCK_ALIGNMENT);
        end else begin
          state_d = STATE_WRITE_RESPONSE;
          alloc_ptr_d = NULL_PTR;
        end
      end

      STATE_ALLOC_LOAD_FREE_PTR: begin
        lsu_req_val  = 1'b1;
        lsu_req_addr = falafel_config.free_list_ptr;
        lsu_req_op   = LSU_OP_LOAD_WORD;

        if (lsu_req_rdy) begin
          state_d = STATE_ALLOC_WAIT_FREE_PTR;
        end
      end

      STATE_ALLOC_WAIT_FREE_PTR: begin
        lsu_rsp_rdy = 1'b1;

        if (lsu_rsp_val) begin
          sel_block = SEL_FAKE_BLOCK;
          state_d   = STATE_ALLOC_PROCESS_BLOCK;
        end
      end

      STATE_ALLOC_LOAD_BLOCK: begin
        lsu_req_val  = 1'b1;
        lsu_req_addr = next_block_ptr_q;
        lsu_req_op   = LSU_OP_LOAD_BLOCK;

        if (lsu_req_rdy) begin
          state_d = STATE_ALLOC_WAIT_BLOCK;

          prev_block_ptr_d = current_block_ptr_q;
        end
      end

      STATE_ALLOC_WAIT_BLOCK: begin
        lsu_rsp_rdy = 1'b1;

        if (lsu_rsp_val) begin
          sel_block = SEL_REAL_BLOCK;
          state_d   = STATE_ALLOC_PROCESS_BLOCK;
        end
      end

      STATE_ALLOC_PROCESS_BLOCK: begin
        if (bp_is_big_enough) begin
          state_d = STATE_ALLOC_CALC_SPLIT;
        end else if (bp_is_null) begin
          state_d = STATE_SBRK;
        end else begin
          next_block_ptr_d = bp_next_ptr;
          state_d = STATE_ALLOC_LOAD_BLOCK;
        end
      end

      STATE_ALLOC_CALC_SPLIT: begin
        state_d = STATE_ALLOC_STORE_NEW_BLOCK;

        if ((buffered_block_q.size - alloc_size_q) > MIN_ALLOC_SIZE) begin
          state_d = STATE_ALLOC_STORE_NEW_BLOCK;
          alloc_ptr_d = current_block_ptr_q + WORD_SIZE;
        end else begin
          state_d = STATE_ALLOC_REMOVE_FREELIST;
          alloc_ptr_d = current_block_ptr_q + WORD_SIZE;
        end
      end

      STATE_ALLOC_STORE_NEW_BLOCK: begin
        lsu_req_val = 1'b1;
        lsu_req_addr = current_block_ptr_q + BLOCK_HEADER_SIZE + alloc_size_q;
        lsu_req_op = LSU_OP_STORE_BLOCK;
        lsu_req_block = {
          (buffered_block_q.size - alloc_size_q) - BLOCK_HEADER_SIZE, buffered_block_q.next_ptr
        };

        if (lsu_req_rdy) begin
          state_d = STATE_ALLOC_WAIT_STORE;

          // Update this internal register so that STATE_ALLOC_REMOVE_FREELIST
          // gets the correct value of next_ptr
          change_block_d = 1'b1;
        end
      end

      STATE_ALLOC_WAIT_STORE: begin
        lsu_rsp_rdy = 1'b1;

        if (lsu_rsp_val) begin
          state_d = STATE_ALLOC_REMOVE_FREELIST;
          change_block_d = 1'b1;
        end
      end

      STATE_ALLOC_REMOVE_FREELIST: begin
        lsu_req_val  = 1'b1;
        lsu_req_addr = prev_block_ptr_q + WORD_SIZE;
        lsu_req_op   = LSU_OP_STORE_WORD;
        if (change_block_q) lsu_req_word = current_block_ptr_q;
        else lsu_req_word = buffered_block_q.next_ptr;

        if (lsu_req_rdy) begin
          state_d = STATE_ALLOC_WAIT_REMOVE;
        end
      end

      STATE_ALLOC_WAIT_REMOVE: begin
        lsu_rsp_rdy = 1'b1;

        if (lsu_rsp_val) begin
          state_d = STATE_WRITE_RESPONSE;
        end
      end

      STATE_WRITE_RESPONSE: begin
        if (!resp_fifo_full_i) begin
          state_d = STATE_IDLE;
          resp_fifo_write_o = 1'b1;
          resp_fifo_din_o = alloc_ptr_q;
        end
      end

      STATE_SBRK: begin
        // TODO: size
        sbrk_req_val_o = 1'b1;

        if (sbrk_rsp_val_i) begin
          // TODO
        end
      end

      default: ;
    endcase
  end


  falafel_lsu i_falafel_lsu (
      .clk_i,
      .rst_ni,

      .alloc_req_val_i  (lsu_req_val),
      .alloc_req_rdy_o  (lsu_req_rdy),
      .alloc_req_op_i   (lsu_req_op),
      .alloc_req_addr_i (lsu_req_addr),
      .alloc_req_word_i (lsu_req_word),
      .alloc_req_block_i(lsu_req_block),
      .alloc_rsp_val_o  (lsu_rsp_val),
      .alloc_rsp_rdy_i  (lsu_rsp_rdy),
      .alloc_rsp_word_o (lsu_rsp_word),
      .alloc_rsp_block_o(lsu_rsp_block),

      .mem_req_rdy_i,
      .mem_req_val_o,
      .mem_req_is_write_i,
      .mem_req_addr_o,
      .mem_req_data_o,
      .mem_rsp_val_i,
      .mem_rsp_rdy_o,
      .mem_rsp_data_i
  );


  falafel_block_parser i_falafel_block_parser (
      .block_i         (bp_block),
      .requested_size_i(bp_requested_size),
      .is_null_o       (bp_is_null),
      .is_big_enough_o (bp_is_big_enough),
      .next_block_ptr  (bp_next_ptr)
  );



  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      state_q <= STATE_INIT;
      alloc_size_q <= '0;
      alloc_ptr_q <= NULL_PTR;
      freelist_ptr_q <= NULL_PTR;
      buffered_word_q <= '0;
      buffered_block_q <= '0;
      current_block_ptr_q <= NULL_PTR;
      prev_block_ptr_q <= '0;
      next_block_ptr_q <= '0;
      target_block_ptr_q <= '0;
      change_block_q <= 1'b0;
    end else begin
      state_q <= state_d;
      alloc_size_q <= alloc_size_d;
      alloc_ptr_q <= alloc_ptr_d;
      freelist_ptr_q <= freelist_ptr_d;
      buffered_word_q <= buffered_word_d;
      buffered_block_q <= buffered_block_d;
      current_block_ptr_q <= current_block_ptr_d;
      prev_block_ptr_q <= prev_block_ptr_d;
      next_block_ptr_q <= next_block_ptr_d;
      target_block_ptr_q <= target_block_ptr_d;
      change_block_q <= change_block_d;
    end
  end

endmodule
