SRCS := \
	$(FALAFEL_RTL_DIR)/include/falafel_pkg.sv \
	$(FALAFEL_RTL_DIR)/include/fifos/falafel_fifo_internal.sv \
	$(FALAFEL_RTL_DIR)/include/fifos/falafel_fifo.sv \
	$(FALAFEL_RTL_DIR)/falafel_config_regs.sv \
	$(FALAFEL_RTL_DIR)/falafel_input_buffer.sv \
	$(FALAFEL_RTL_DIR)/falafel_input_parser.sv \
	$(FALAFEL_RTL_DIR)/falafel_input_arbiter.sv \
	$(FALAFEL_RTL_DIR)/falafel_lsu.sv \
	$(FALAFEL_RTL_DIR)/core/falafel_block_parser.sv \
	$(FALAFEL_RTL_DIR)/core/falafel_core.sv \
	$(FALAFEL_RTL_DIR)/falafel_output_fsm.sv \
	$(FALAFEL_RTL_DIR)/falafel.sv \




.PHONY: linkt
lint: $(SRCS)
	verilator --lint-only -Wall $(SRCS)
