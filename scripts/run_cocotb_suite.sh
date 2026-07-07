#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

WAVES="${WAVES:-1}"

TEST_MODULES=(
    test_receiver
    test_receiver_stalls
    test_receiver_random
    test_receiver_reset
    test_receiver_coverage
)

mkdir -p \
    "${PROJECT_ROOT}/build/cocotb" \
    "${PROJECT_ROOT}/results"

echo
echo "Cocotb Receiver Test Suite"
echo "=========================="
echo

for test_module in "${TEST_MODULES[@]}"; do
    build_directory="${PROJECT_ROOT}/build/cocotb/${test_module}"
    result_file="${PROJECT_ROOT}/results/${test_module}.xml"

    echo "Running: ${test_module}"
    echo "----------------------------------------"

    rm -rf "${build_directory}"
    rm -f "${PROJECT_ROOT}/tb/cocotb/results.xml"
    rm -f "${result_file}"

    make -C "${PROJECT_ROOT}/tb/cocotb" \
        COCOTB_TEST_MODULES="${test_module}" \
        SIM_BUILD="${build_directory}" \
        WAVES="${WAVES}"

    if [[ -f "${PROJECT_ROOT}/tb/cocotb/results.xml" ]]; then
        cp \
            "${PROJECT_ROOT}/tb/cocotb/results.xml" \
            "${result_file}"
    fi

    echo
done

echo "========================================"
echo "COCOTB SUITE RESULT: PASS"
echo "========================================"
