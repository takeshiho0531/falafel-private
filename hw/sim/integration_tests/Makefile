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
	$(PWD)/falafel_wrapper.sv \

THREADS ?= 1

SIM ?= verilator
EXTRA_ARGS += --trace-fst --trace-structs -Wno-width --threads $(THREADS)

VERILOG_SOURCES += $(SRCS)
TOPLEVEL_LANG := verilog

TOPLEVEL = falafel_wrapper
MODULE = test_falafel

PYTHONPATH:="$(FALAFEL_PROJECT_ROOT)/hw/sim/cocotb_common"

# PROJECT_ROOT = os.environ["FALAFEL_PROJECT_ROOT"]
# RTL_DIR = os.environ["FALAFEL_RTL_DIR"]
# SIM_DIR = PROJECT_ROOT + '/hw/sim'
# INCLUDE_DIR = RTL_DIR + "/include/"
# sys.path.insert(0, SIM_DIR + '/cocotb_common')

include $(shell cocotb-config --makefiles)/Makefile.sim
