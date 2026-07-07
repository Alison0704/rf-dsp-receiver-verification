"""Directed functional coverage for the fixed-point QPSK receiver."""

import json
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge, Timer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

JSON_REPORT = PROJECT_ROOT / "results" / "functional_coverage.json"
TEXT_REPORT = PROJECT_ROOT / "results" / "functional_coverage.txt"


def signed(signal) -> int:
    """Read a signed SystemVerilog signal."""
    return signal.value.to_signed()


def unsigned(signal) -> int:
    """Read an unsigned SystemVerilog signal."""
    return int(signal.value)


def capture_outputs(dut) -> dict[str, int]:
    """Capture the receiver outputs."""
    return {
        "out_valid": unsigned(dut.out_valid),
        "fir_acc_i": signed(dut.fir_acc_i),
        "fir_acc_q": signed(dut.fir_acc_q),
        "fir_i": signed(dut.fir_i),
        "fir_q": signed(dut.fir_q),
        "bit_msb": unsigned(dut.bit_msb),
        "bit_lsb": unsigned(dut.bit_lsb),
    }


async def reset_receiver(dut) -> None:
    """Apply asynchronous reset and leave the DUT ready for input."""
    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0
    dut.rst_n.value = 0

    await Timer(1, unit="ns")
    await ReadOnly()

    outputs = capture_outputs(dut)

    assert outputs == {
        "out_valid": 0,
        "fir_acc_i": 0,
        "fir_acc_q": 0,
        "fir_i": 0,
        "fir_q": 0,
        "bit_msb": 0,
        "bit_lsb": 0,
    }

    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)

    dut.rst_n.value = 1


async def drive_constant_symbol(
    dut,
    i_value: int,
    q_value: int,
    expected_msb: int,
    expected_lsb: int,
) -> dict[str, int]:
    """Drive five identical samples to create one complete FIR window."""
    final_output = {}

    for sample_number in range(5):
        dut.in_valid.value = 1
        dut.i_in.value = i_value
        dut.q_in.value = q_value

        await RisingEdge(dut.clk)
        await ReadOnly()

        output = capture_outputs(dut)

        expected_valid = int(sample_number == 4)

        assert output["out_valid"] == expected_valid, (
            f"Sample {sample_number}: expected out_valid="
            f"{expected_valid}, actual={output['out_valid']}"
        )

        if sample_number < 4:
            assert output["bit_msb"] == 0
            assert output["bit_lsb"] == 0
        else:
            # Five identical samples and coefficients summing to nine
            # produce a normalized output equal to the input value.
            assert output["fir_i"] == i_value
            assert output["fir_q"] == q_value
            assert output["bit_msb"] == expected_msb
            assert output["bit_lsb"] == expected_lsb

            final_output = output

        await FallingEdge(dut.clk)

    return final_output


async def insert_stall(dut) -> None:
    """Insert a cycle where input buses must be ignored."""
    previous = capture_outputs(dut)

    dut.in_valid.value = 0
    dut.i_in.value = 12345
    dut.q_in.value = -12345

    await RisingEdge(dut.clk)
    await ReadOnly()

    stalled = capture_outputs(dut)

    assert stalled["out_valid"] == 0
    assert stalled["bit_msb"] == 0
    assert stalled["bit_lsb"] == 0

    for field in ("fir_acc_i", "fir_acc_q", "fir_i", "fir_q"):
        assert stalled[field] == previous[field], (
            f"{field} changed during a stall"
        )

    await FallingEdge(dut.clk)


def write_coverage_report(coverage: dict) -> None:
    """Write machine-readable and human-readable coverage reports."""
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)

    JSON_REPORT.write_text(
        json.dumps(coverage, indent=2) + "\n",
        encoding="utf-8",
    )

    symbol_bins = coverage["symbol_bins"]
    special_bins = coverage["special_bins"]
    protocol_bins = coverage["protocol_bins"]

    covered_symbol_bins = sum(
        count > 0 for count in symbol_bins.values()
    )

    covered_special_bins = sum(
        count > 0 for count in special_bins.values()
    )

    covered_protocol_bins = sum(
        count > 0 for count in protocol_bins.values()
    )

    total_bins = (
        len(symbol_bins)
        + len(special_bins)
        + len(protocol_bins)
    )

    covered_bins = (
        covered_symbol_bins
        + covered_special_bins
        + covered_protocol_bins
    )

    percentage = 100.0 * covered_bins / total_bins

    lines = [
        "RF/DSP Receiver Functional Coverage",
        "=" * 40,
        "",
        "QPSK symbol bins",
        "-" * 40,
    ]

    for name, count in symbol_bins.items():
        lines.append(f"{name:<24}: {count}")

    lines.extend(
        [
            "",
            "Special-value bins",
            "-" * 40,
        ]
    )

    for name, count in special_bins.items():
        lines.append(f"{name:<24}: {count}")

    lines.extend(
        [
            "",
            "Protocol bins",
            "-" * 40,
        ]
    )

    for name, count in protocol_bins.items():
        lines.append(f"{name:<24}: {count}")

    lines.extend(
        [
            "",
            f"Covered bins: {covered_bins}/{total_bins}",
            f"Functional coverage: {percentage:.1f}%",
            "",
            "RESULT: PASS" if covered_bins == total_bins else "RESULT: FAIL",
        ]
    )

    TEXT_REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


@cocotb.test()
async def test_receiver_functional_coverage(dut):
    """Exercise and record all required functional coverage bins."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    coverage = {
        "symbol_bins": {
            "symbol_00": 0,
            "symbol_01": 0,
            "symbol_11": 0,
            "symbol_10": 0,
        },
        "special_bins": {
            "i_equals_zero": 0,
            "q_equals_zero": 0,
            "maximum_positive": 0,
            "minimum_negative": 0,
        },
        "protocol_bins": {
            "asynchronous_reset": 0,
            "first_valid_on_fifth": 0,
            "input_stall": 0,
        },
    }

    test_cases = [
        {
            "name": "symbol_00",
            "i": 1000,
            "q": 1000,
            "msb": 0,
            "lsb": 0,
        },
        {
            "name": "symbol_01",
            "i": -1000,
            "q": 1000,
            "msb": 0,
            "lsb": 1,
        },
        {
            "name": "symbol_11",
            "i": -1000,
            "q": -1000,
            "msb": 1,
            "lsb": 1,
        },
        {
            "name": "symbol_10",
            "i": 1000,
            "q": -1000,
            "msb": 1,
            "lsb": 0,
        },
        {
            "name": "zero_i",
            "i": 0,
            "q": 1000,
            "msb": 0,
            "lsb": 0,
        },
        {
            "name": "zero_q",
            "i": -1000,
            "q": 0,
            "msb": 0,
            "lsb": 1,
        },
        {
            "name": "numeric_extremes",
            "i": 32767,
            "q": -32768,
            "msb": 1,
            "lsb": 0,
        },
    ]

    for test_case in test_cases:
        await reset_receiver(dut)

        coverage["protocol_bins"]["asynchronous_reset"] += 1

        output = await drive_constant_symbol(
            dut,
            i_value=test_case["i"],
            q_value=test_case["q"],
            expected_msb=test_case["msb"],
            expected_lsb=test_case["lsb"],
        )

        coverage["protocol_bins"]["first_valid_on_fifth"] += 1

        symbol_name = (
            f"symbol_{output['bit_msb']}{output['bit_lsb']}"
        )

        coverage["symbol_bins"][symbol_name] += 1

        if test_case["i"] == 0:
            coverage["special_bins"]["i_equals_zero"] += 1

        if test_case["q"] == 0:
            coverage["special_bins"]["q_equals_zero"] += 1

        if (
            test_case["i"] == 32767
            or test_case["q"] == 32767
        ):
            coverage["special_bins"]["maximum_positive"] += 1

        if (
            test_case["i"] == -32768
            or test_case["q"] == -32768
        ):
            coverage["special_bins"]["minimum_negative"] += 1

        await insert_stall(dut)
        coverage["protocol_bins"]["input_stall"] += 1

    write_coverage_report(coverage)

    for category in coverage.values():
        for bin_name, count in category.items():
            assert count > 0, f"Uncovered functional bin: {bin_name}"

    dut._log.info(
        "Functional coverage report saved to %s",
        TEXT_REPORT,
    )
