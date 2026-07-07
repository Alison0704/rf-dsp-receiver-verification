"""Compare captured RTL outputs against the MATLAB golden reference."""

import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MATLAB_PATH = PROJECT_ROOT / "vectors" / "matlab_expected.csv"
RTL_PATH = PROJECT_ROOT / "results" / "rtl_output.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "rtl_vs_matlab.txt"

FIELDS = [
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


def read_csv(path: Path) -> list[dict[str, int]]:
    """Read a receiver-results CSV as integer-valued rows."""
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")

        missing_fields = set(FIELDS) - set(reader.fieldnames)

        if missing_fields:
            raise ValueError(
                f"{path} is missing fields: {sorted(missing_fields)}"
            )

        rows = []

        for row_number, row in enumerate(reader, start=2):
            try:
                rows.append(
                    {
                        field: int(float(row[field]))
                        for field in FIELDS
                    }
                )
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid numeric value in {path}, "
                    f"row {row_number}: {error}"
                ) from error

    return rows


def main() -> int:
    """Compare every captured RTL field against MATLAB."""
    matlab_rows = read_csv(MATLAB_PATH)
    rtl_rows = read_csv(RTL_PATH)

    report = [
        "RTL versus MATLAB Receiver Comparison",
        "=" * 40,
        f"MATLAB rows: {len(matlab_rows)}",
        f"RTL rows:    {len(rtl_rows)}",
        "",
    ]

    if len(matlab_rows) != len(rtl_rows):
        report.extend(
            [
                "RESULT: FAIL",
                "The CSV files contain different row counts.",
            ]
        )

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            "\n".join(report) + "\n",
            encoding="utf-8",
        )

        print("\n".join(report))
        return 1

    mismatch_counts = {field: 0 for field in FIELDS}
    mismatch_details = []

    for matlab_row, rtl_row in zip(matlab_rows, rtl_rows):
        sample_index = matlab_row["sample_index"]

        for field in FIELDS:
            expected = matlab_row[field]
            actual = rtl_row[field]

            if expected != actual:
                mismatch_counts[field] += 1

                if len(mismatch_details) < 20:
                    mismatch_details.append(
                        f"Sample {sample_index}, {field}: "
                        f"MATLAB={expected}, RTL={actual}"
                    )

    total_mismatches = sum(mismatch_counts.values())

    matlab_valid = sum(
        row["output_valid"] for row in matlab_rows
    )

    rtl_valid = sum(
        row["output_valid"] for row in rtl_rows
    )

    report.extend(
        [
            f"MATLAB valid outputs: {matlab_valid}",
            f"RTL valid outputs:    {rtl_valid}",
            "",
            "Mismatch summary",
            "-" * 40,
        ]
    )

    for field in FIELDS:
        report.append(
            f"{field:<14}: {mismatch_counts[field]}"
        )

    report.extend(
        [
            "",
            f"Total field mismatches: {total_mismatches}",
        ]
    )

    if mismatch_details:
        report.extend(
            [
                "",
                "First mismatches",
                "-" * 40,
                *mismatch_details,
            ]
        )

    if total_mismatches == 0:
        report.extend(
            [
                "",
                "RESULT: PASS",
                "The RTL output matches the MATLAB golden reference.",
            ]
        )
        exit_code = 0
    else:
        report.extend(
            [
                "",
                "RESULT: FAIL",
                "The RTL output differs from the MATLAB reference.",
            ]
        )
        exit_code = 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )

    print("\n".join(report))
    print(f"\nReport saved to {REPORT_PATH}")

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
