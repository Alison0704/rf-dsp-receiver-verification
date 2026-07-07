"""Compare C++ receiver outputs against the MATLAB golden reference."""

import csv
import sys
from pathlib import Path


MATLAB_PATH = Path("vectors/matlab_expected.csv")
CPP_PATH = Path("vectors/cpp_expected.csv")
REPORT_PATH = Path("results/cpp_vs_matlab.txt")

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
    """Read receiver results and convert all fields to integers."""
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")

        missing = set(FIELDS) - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"{path} is missing columns: {sorted(missing)}"
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
    """Compare all MATLAB and C++ output fields."""
    matlab_rows = read_csv(MATLAB_PATH)
    cpp_rows = read_csv(CPP_PATH)

    report_lines = [
        "C++ versus MATLAB Receiver Comparison",
        "=" * 40,
        f"MATLAB rows: {len(matlab_rows)}",
        f"C++ rows:    {len(cpp_rows)}",
        "",
    ]

    if len(matlab_rows) != len(cpp_rows):
        report_lines.append("FAIL: CSV row counts differ.")
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            "\n".join(report_lines) + "\n",
            encoding="utf-8",
        )
        print("\n".join(report_lines))
        return 1

    mismatch_counts = {field: 0 for field in FIELDS}
    mismatch_details: list[str] = []

    for row_index, (matlab_row, cpp_row) in enumerate(
        zip(matlab_rows, cpp_rows)
    ):
        sample_index = matlab_row["sample_index"]

        for field in FIELDS:
            expected = matlab_row[field]
            actual = cpp_row[field]

            if expected != actual:
                mismatch_counts[field] += 1

                if len(mismatch_details) < 20:
                    mismatch_details.append(
                        f"Sample {sample_index}, {field}: "
                        f"MATLAB={expected}, C++={actual}"
                    )

    total_mismatches = sum(mismatch_counts.values())

    report_lines.extend(
        [
            "Mismatch summary",
            "-" * 40,
        ]
    )

    for field in FIELDS:
        report_lines.append(
            f"{field:<14}: {mismatch_counts[field]}"
        )

    report_lines.extend(
        [
            "",
            f"Total field mismatches: {total_mismatches}",
        ]
    )

    if mismatch_details:
        report_lines.extend(
            [
                "",
                "First mismatches",
                "-" * 40,
                *mismatch_details,
            ]
        )

    if total_mismatches == 0:
        report_lines.extend(
            [
                "",
                "RESULT: PASS",
                "The C++ model matches the MATLAB golden reference.",
            ]
        )
        exit_code = 0
    else:
        report_lines.extend(
            [
                "",
                "RESULT: FAIL",
                "The C++ model differs from the MATLAB reference.",
            ]
        )
        exit_code = 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(report_lines))
    print(f"\nReport saved to {REPORT_PATH}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
