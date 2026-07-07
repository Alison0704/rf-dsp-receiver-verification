"""Tests for the shared receiver vectors and generated model outputs."""

import csv
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = PROJECT_ROOT / "vectors" / "input_samples.csv"
MATLAB_PATH = PROJECT_ROOT / "vectors" / "matlab_expected.csv"
CPP_PATH = PROJECT_ROOT / "vectors" / "cpp_expected.csv"
RTL_PATH = PROJECT_ROOT / "results" / "rtl_output.csv"

INPUT_FIELDS = [
    "sample_index",
    "i_in",
    "q_in",
]

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

FIR_COEFFICIENTS = [1, 2, 3, 2, 1]
FIR_NORMALIZATION = 9


def read_csv(path: Path) -> tuple[list[str], list[dict[str, int]]]:
    """Read a CSV file and convert numeric values to integers."""
    assert path.exists(), f"Missing required file: {path}"

    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        assert reader.fieldnames is not None, (
            f"CSV has no header: {path}"
        )

        rows = []

        for row_number, row in enumerate(reader, start=2):
            try:
                rows.append(
                    {
                        field: int(float(value))
                        for field, value in row.items()
                        if field is not None and value not in (None, "")
                    }
                )
            except ValueError as error:
                pytest.fail(
                    f"Invalid numeric value in {path}, "
                    f"row {row_number}: {error}"
                )

    return list(reader.fieldnames), rows


def truncate_toward_zero(value: int, divisor: int) -> int:
    """Perform signed integer division with truncation toward zero."""
    magnitude = abs(value) // divisor
    return -magnitude if value < 0 else magnitude


def compare_output_files(
    expected_path: Path,
    actual_path: Path,
) -> None:
    """Compare two receiver-output CSV files exactly."""
    expected_fields, expected_rows = read_csv(expected_path)
    actual_fields, actual_rows = read_csv(actual_path)

    assert expected_fields == OUTPUT_FIELDS
    assert actual_fields == OUTPUT_FIELDS

    assert len(actual_rows) == len(expected_rows), (
        f"{actual_path} contains {len(actual_rows)} rows, "
        f"but {expected_path} contains {len(expected_rows)} rows."
    )

    for expected, actual in zip(expected_rows, actual_rows):
        assert actual == expected, (
            f"Mismatch at sample {expected['sample_index']}:\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )


def test_input_vector_schema_and_indices() -> None:
    """Check the input-vector structure and sample numbering."""
    fields, rows = read_csv(INPUT_PATH)

    assert fields == INPUT_FIELDS
    assert len(rows) == 32

    sample_indices = [
        row["sample_index"]
        for row in rows
    ]

    assert sample_indices == list(range(32))


def test_matlab_reference_schema_and_valid_timing() -> None:
    """Check the golden-output schema and FIR valid timing."""
    fields, rows = read_csv(MATLAB_PATH)

    assert fields == OUTPUT_FIELDS
    assert len(rows) == 32

    valid_values = [
        row["output_valid"]
        for row in rows
    ]

    assert valid_values[:4] == [0, 0, 0, 0]
    assert valid_values[4:] == [1] * 28
    assert sum(valid_values) == 28


def test_matlab_reference_fir_and_demapper() -> None:
    """Recompute the FIR and QPSK results independently in Python."""
    _, input_rows = read_csv(INPUT_PATH)
    _, matlab_rows = read_csv(MATLAB_PATH)

    assert len(input_rows) == len(matlab_rows)

    delay_i = [0, 0, 0, 0, 0]
    delay_q = [0, 0, 0, 0, 0]

    for position, (input_row, expected_row) in enumerate(
        zip(input_rows, matlab_rows)
    ):
        delay_i = [input_row["i_in"], *delay_i[:4]]
        delay_q = [input_row["q_in"], *delay_q[:4]]

        accumulator_i = sum(
            sample * coefficient
            for sample, coefficient in zip(
                delay_i,
                FIR_COEFFICIENTS,
            )
        )

        accumulator_q = sum(
            sample * coefficient
            for sample, coefficient in zip(
                delay_q,
                FIR_COEFFICIENTS,
            )
        )

        assert expected_row["sample_index"] == input_row["sample_index"]
        assert expected_row["i_in"] == input_row["i_in"]
        assert expected_row["q_in"] == input_row["q_in"]

        assert expected_row["fir_acc_i"] == accumulator_i
        assert expected_row["fir_acc_q"] == accumulator_q

        expected_valid = int(position >= 4)

        assert expected_row["output_valid"] == expected_valid

        if expected_valid:
            filtered_i = truncate_toward_zero(
                accumulator_i,
                FIR_NORMALIZATION,
            )

            filtered_q = truncate_toward_zero(
                accumulator_q,
                FIR_NORMALIZATION,
            )

            assert expected_row["fir_i"] == filtered_i
            assert expected_row["fir_q"] == filtered_q
            assert expected_row["bit_msb"] == int(filtered_q < 0)
            assert expected_row["bit_lsb"] == int(filtered_i < 0)
        else:
            assert expected_row["fir_i"] == 0
            assert expected_row["fir_q"] == 0
            assert expected_row["bit_msb"] == 0
            assert expected_row["bit_lsb"] == 0


def test_cpp_output_matches_matlab() -> None:
    """Check the generated C++ output when it is available."""
    if not CPP_PATH.exists():
        pytest.skip(
            "Run 'make cpp' to generate vectors/cpp_expected.csv"
        )

    compare_output_files(MATLAB_PATH, CPP_PATH)


def test_rtl_output_matches_matlab() -> None:
    """Check the captured RTL output when it is available."""
    if not RTL_PATH.exists():
        pytest.skip(
            "Run 'make sim' to generate results/rtl_output.csv"
        )

    compare_output_files(MATLAB_PATH, RTL_PATH)
