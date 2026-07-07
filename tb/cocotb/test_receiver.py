"""Compare the SystemVerilog receiver against the MATLAB reference."""

import csv
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "vectors" / "input_samples.csv"
EXPECTED_FILE = PROJECT_ROOT / "vectors" / "matlab_expected.csv"
RTL_OUTPUT_FILE = PROJECT_ROOT / "results" / "rtl_output.csv"

OUTPUT_FIELDS = [
    "sample_index",
    "i_in",
    "q_in",
    "output_valid",
    "fir_acc_i",
    "fir_acc_q",
    "fir_i",
    "fir_q",
    "bit_msb",
    "bit_lsb",
]

COMPARED_FIELDS = [
    "output_valid",
    "fir_acc_i",
    "fir_acc_q",
    "fir_i",
    "fir_q",
    "bit_msb",
    "bit_lsb",
]


def read_csv(path: Path) -> list[dict[str, int]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        rows = []

        for row_number, row in enumerate(reader, start=2):
            try:
                rows.append({
                    name: int(float(value))
                    for name, value in row.items()
                    if name is not None and value not in (None, "")
                })
            except ValueError as error:
                raise ValueError(
                    f"Invalid value in {path} at row {row_number}"
                ) from error

    return rows


def signed(signal) -> int:
    return signal.value.to_signed()


def unsigned(signal) -> int:
    return int(signal.value)


def write_results(rows: list[dict[str, int]]) -> None:
    RTL_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with RTL_OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


@cocotb.test()
async def test_receiver_against_matlab(dut):
    input_rows = read_csv(INPUT_FILE)
    expected_rows = read_csv(EXPECTED_FILE)

    assert len(input_rows) == len(expected_rows), (
        f"Input rows: {len(input_rows)}, "
        f"expected rows: {len(expected_rows)}"
    )

    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)

    dut.rst_n.value = 1

    captured_rows = []
    mismatches = []

    for input_row, expected_row in zip(input_rows, expected_rows):
        dut.in_valid.value = 1
        dut.i_in.value = input_row["i_in"]
        dut.q_in.value = input_row["q_in"]

        await RisingEdge(dut.clk)
        await ReadOnly()

        actual_row = {
            "sample_index": input_row["sample_index"],
            "i_in": input_row["i_in"],
            "q_in": input_row["q_in"],
            "output_valid": unsigned(dut.out_valid),
            "fir_acc_i": signed(dut.fir_acc_i),
            "fir_acc_q": signed(dut.fir_acc_q),
            "fir_i": signed(dut.fir_i),
            "fir_q": signed(dut.fir_q),
            "bit_msb": unsigned(dut.bit_msb),
            "bit_lsb": unsigned(dut.bit_lsb),
        }

        captured_rows.append(actual_row)

        for field in COMPARED_FIELDS:
            expected = expected_row[field]
            actual = actual_row[field]

            if actual != expected:
                mismatches.append(
                    f"Sample {input_row['sample_index']} "
                    f"{field}: expected={expected}, actual={actual}"
                )

        await FallingEdge(dut.clk)

    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0

    write_results(captured_rows)

    valid_outputs = sum(
        row["output_valid"] for row in captured_rows
    )

    dut._log.info(
        "Compared %d samples and %d valid outputs",
        len(captured_rows),
        valid_outputs,
    )

    dut._log.info(
        "Saved RTL output to %s",
        RTL_OUTPUT_FILE,
    )

    assert not mismatches, (
        f"\nDetected {len(mismatches)} mismatches:\n"
        + "\n".join(mismatches[:20])
    )
