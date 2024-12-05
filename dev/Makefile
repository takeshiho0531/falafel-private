SIM ?= verilator
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += falafel_wrapper.sv

TOPLEVEL = falafel_wrapper

MODULE = test_falafel_wrapper

EXTRA_ARGS += --trace-fst --trace-structs

include $(shell cocotb-config --makefiles)/Makefile.sim

PYTHON=$(shell poetry run which python)
