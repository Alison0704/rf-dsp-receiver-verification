#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON="${PROJECT_ROOT}/.venv/bin/python"
COCOTB_CONFIG="${PROJECT_ROOT}/.venv/bin/cocotb-config"

export PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"

echo
echo "RF/DSP Receiver Verification Regression"
echo "========================================"
echo "Project: ${PROJECT_ROOT}"
echo

if [[ ! -x "${PYTHON}" ]]; then
    echo "ERROR: Python virtual environment was not found."
    echo "Create it with:"
    echo
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  python -m pip install -r requirements.txt"
    exit 1
fi

if [[ ! -x "${COCOTB_CONFIG}" ]]; then
    echo "ERROR: cocotb is not installed in .venv."
    echo
    echo "Run:"
    echo "  source .venv/bin/activate"
    echo "  python -m pip install -r requirements.txt"
    exit 1
fi

if ! command -v iverilog >/dev/null 2>&1; then
    echo "ERROR: iverilog was not found."
    exit 1
fi

if ! command -v vvp >/dev/null 2>&1; then
    echo "ERROR: vvp was not found."
    exit 1
fi

mkdir -p \
    "${PROJECT_ROOT}/build" \
    "${PROJECT_ROOT}/results"

echo "[1/5] Building and running the C++ reference model"
make -C "${PROJECT_ROOT}/cpp" clean
make -C "${PROJECT_ROOT}/cpp" run

echo
echo "[2/5] Comparing C++ against MATLAB"
cd "${PROJECT_ROOT}"
"${PYTHON}" scripts/compare_models.py

echo
echo "[3/5] Checking SystemVerilog RTL syntax"
iverilog \
    -g2012 \
    -Wall \
    -Wimplicit \
    -s receiver_top \
    -o "${PROJECT_ROOT}/build/receiver_top.vvp" \
    "${PROJECT_ROOT}/rtl/fir_filter.sv" \
    "${PROJECT_ROOT}/rtl/qpsk_demapper.sv" \
    "${PROJECT_ROOT}/rtl/receiver_top.sv"

echo
echo "[4/5] Running cocotb verification and RTL assertions"
WAVES=1 "${PROJECT_ROOT}/scripts/run_cocotb_suite.sh"

echo
echo "[5/5] Comparing RTL output against MATLAB"
cd "${PROJECT_ROOT}"
"${PYTHON}" scripts/compare_rtl.py

echo
echo "========================================"
echo "REGRESSION RESULT: PASS"
echo "========================================"
echo
echo "Generated artifacts:"
echo "  results/cpp_vs_matlab.txt"
echo "  results/rtl_vs_matlab.txt"
echo "  results/rtl_output.csv"
echo
echo "Waveform files:"
find "${PROJECT_ROOT}/build/cocotb" \
    -type f \
    \( -name "*.fst" -o -name "*.vcd" \) \
    -print 2>/dev/null || true
