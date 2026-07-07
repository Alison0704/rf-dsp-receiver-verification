"""Verify receiver behavior when input-valid stalls occur."""

import csv
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "vectors" / "input_samples.csv"
EXPECTED_FILE = PROJECT_ROOT / "vectors" / "matlab_expected.csv"

COMPARED_FIELDS = [
    "output_valid",
    "fir_acc_i",
    "fir_acc_q",
    "fir_i",
    "fir_q",
    "bit_msb",
    "bit_lsb",
]

STABLE_FIELDS = [
    "fir_acc_i",
    "fir_acc_q",
    "fir_i",
    "fir_q",
]


def read_csv(path: Path) -> list[dict[str, int]]:
    """Read a numeric CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        return [
            {
                name: int(float(value))
                for name, value in row.items()
                if name is not None and value not in (None, "")
            }
            for row in reader
        ]


def signed(signal) -> int:
    """Read a two's-complement signal as an integer."""
    return signal.value.to_signed()


def unsigned(signal) -> int:
    """Read a logic signal as an unsigned integer."""
    return int(signal.value)


def capture_outputs(dut) -> dict[str, int]:
    """Capture the receiver output signals."""
    return {
        "output_valid": unsigned(dut.out_valid),
        "fir_acc_i": signed(dut.fir_acc_i),
        "fir_acc_q": signed(dut.fir_acc_q),
        "fir_i": signed(dut.fir_i),
        "fir_q": signed(dut.fir_q),
        "bit_msb": unsigned(dut.bit_msb),
        "bit_lsb": unsigned(dut.bit_lsb),
    }


@cocotb.test()
async def test_receiver_with_input_stalls(dut):
    """Verify accepted-sample behavior with inserted stall cycles."""
    input_rows = read_csv(INPUT_FILE)
    expected_rows = read_csv(EXPECTED_FILE)

    assert len(input_rows) == len(expected_rows)

    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)

    dut.rst_n.value = 1

    total_stalls = 0

    for position, (input_row, expected_row) in enumerate(
        zip(input_rows, expected_rows)
    ):
        # Drive one accepted input sample.
        dut.in_valid.value = 1
        dut.i_in.value = input_row["i_in"]
        dut.q_in.value = input_row["q_in"]

        await RisingEdge(dut.clk)
        await ReadOnly()

        actual = capture_outputs(dut)

        for field in COMPARED_FIELDS:
            assert actual[field] == expected_row[field], (
                f"Accepted sample {input_row['sample_index']}, "
                f"{field}: expected={expected_row[field]}, "
                f"actual={actual[field]}"
            )

        previous_outputs = actual.copy()

        await FallingEdge(dut.clk)

        # Insert one stall after every fourth sample.
        stall_cycles = 1 if position % 4 == 3 else 0

        # Insert longer stalls at two selected positions.
        if position in (10, 20):
            stall_cycles = 2

        for _ in range(stall_cycles):
            total_stalls += 1

            dut.in_valid.value = 0

            # Change the input buses to prove they are ignored
            # while in_valid is low.
            dut.i_in.value = 12345
            dut.q_in.value = -12345

            await RisingEdge(dut.clk)
            await ReadOnly()

            stalled = capture_outputs(dut)

            assert stalled["output_valid"] == 0, (
                "out_valid must be zero during an input stall"
            )

            assert stalled["bit_msb"] == 0
            assert stalled["bit_lsb"] == 0

            for field in STABLE_FIELDS:
                assert stalled[field] == previous_outputs[field], (
                    f"{field} changed during an input stall: "
                    f"before={previous_outputs[field]}, "
                    f"after={stalled[field]}"
                )

            await FallingEdge(dut.clk)

    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert unsigned(dut.out_valid) == 0

    dut._log.info(
        "Verified %d accepted samples with %d inserted stall cycles",
        len(input_rows),
        total_stalls,
    )
