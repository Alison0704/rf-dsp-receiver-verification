PYTHON := .venv/bin/python

RTL_SOURCES := \
	rtl/fir_filter.sv \
	rtl/qpsk_demapper.sv \
	rtl/receiver_top.sv

.PHONY: help setup cpp compare-cpp rtl-check sim compare-rtl test regression reports waveform-path clean

help:
	@echo "RF/DSP Receiver Verification"
	@echo
	@echo "Available targets:"
	@echo "  make setup          Create the Python environment"
	@echo "  make cpp            Build and run the C++ receiver model"
	@echo "  make compare-cpp    Compare C++ results against MATLAB"
	@echo "  make rtl-check      Compile-check the SystemVerilog RTL"
	@echo "  make sim            Run cocotb verification and assertions"
	@echo "  make compare-rtl    Compare RTL results against MATLAB"
	@echo "  make test           Run Python verification tests"
	@echo "  make regression     Run the complete verification regression"
	@echo "  make reports        Display generated comparison reports"
	@echo "  make waveform-path  Locate generated waveform files"
	@echo "  make clean          Remove generated artifacts"

setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

cpp:
	$(MAKE) -C cpp run

compare-cpp:
	$(PYTHON) scripts/compare_models.py

rtl-check:
	@mkdir -p build
	iverilog \
		-g2012 \
		-Wall \
		-Wimplicit \
		-s receiver_top \
		-o build/receiver_top.vvp \
		$(RTL_SOURCES)

sim:
	$(MAKE) -C tb/cocotb WAVES=1

compare-rtl:
	$(PYTHON) scripts/compare_rtl.py

test:
	$(PYTHON) -m pytest -v

regression:
	./scripts/run_regression.sh

reports:
	@echo "C++ versus MATLAB"
	@echo "=================="
	@cat results/cpp_vs_matlab.txt
	@echo
	@echo "RTL versus MATLAB"
	@echo "=================="
	@cat results/rtl_vs_matlab.txt

waveform-path:
	@find build/cocotb \
		-type f \
		\( -name "*.fst" -o -name "*.vcd" \) \
		-print

clean:
	$(MAKE) -C cpp clean
	$(MAKE) -C tb/cocotb clean
	rm -rf build
	rm -f results/rtl_output.csv
	rm -f results/cpp_vs_matlab.txt
	rm -f results/rtl_vs_matlab.txt
