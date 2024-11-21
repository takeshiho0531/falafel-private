SIM ?= verilator
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += allocator.sv

TOPLEVEL = allocator

MODULE = test_allocator

EXTRA_ARGS += --trace-fst --trace-structs

include $(shell cocotb-config --makefiles)/Makefile.sim

PYTHON=$(shell poetry run which python)
