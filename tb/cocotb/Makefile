SIM ?= icarus
TOPLEVEL_LANG ?= verilog
WAVES ?= 1

PROJECT_ROOT := $(abspath ../..)

VERILOG_SOURCES := \
	$(PROJECT_ROOT)/rtl/fir_filter.sv \
	$(PROJECT_ROOT)/rtl/qpsk_demapper.sv \
	$(PROJECT_ROOT)/rtl/receiver_top.sv \
	$(PROJECT_ROOT)/tb/assertions/receiver_assertions.sv \
	$(PROJECT_ROOT)/tb/assertions/receiver_verification_top.sv

COCOTB_TOPLEVEL := receiver_verification_top
COCOTB_TEST_MODULES := test_receiver

COMPILE_ARGS += -g2012
COMPILE_ARGS += -Wall
COMPILE_ARGS += -gsupported-assertions

SIM_BUILD := $(PROJECT_ROOT)/build/cocotb

include $(shell cocotb-config --makefiles)/Makefile.sim
