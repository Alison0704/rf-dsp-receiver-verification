# RF/DSP Receiver Modeling and Verification

A fixed-point QPSK receiver implemented and verified across MATLAB, C++, and SystemVerilog.

The project uses MATLAB as the golden reference model, C++ as an independent bit-accurate model, and cocotb to verify the RTL implementation.

## Project Goals

- Implement equivalent receiver behavior in MATLAB, C++, and RTL.
- Use shared deterministic input vectors across all implementations.
- Verify fixed-point FIR arithmetic and QPSK symbol demapping.
- Compare C++ and RTL outputs against the MATLAB reference.
- Add cycle-level RTL assertions.
- Generate CSV reports and simulation waveforms.
- Run the complete verification flow with one regression command.

## Receiver Pipeline

The receiver contains two main processing stages:

    Signed 16-bit I/Q samples
                |
                v
        Five-tap FIR filter
        [1, 2, 3, 2, 1] / 9
                |
                v
       QPSK hard-decision demapper
                |
                v
            Two output bits

The I and Q channels use identical FIR filters.

## QPSK Mapping

| Filtered I | Filtered Q | Output |
|---|---|---|
| `I >= 0` | `Q >= 0` | `00` |
| `I < 0` | `Q >= 0` | `01` |
| `I < 0` | `Q < 0` | `11` |
| `I >= 0` | `Q < 0` | `10` |

Zero is treated as positive.

## Repository Structure

    rf-dsp-receiver-verification/
    ├── Makefile
    ├── README.md
    ├── requirements.txt
    ├── specs/
    │   └── receiver_spec.md
    ├── matlab/
    │   ├── generate_vectors.m
    │   ├── receiver_reference.m
    │   ├── run_all.m
    │   └── plot_receiver_results.m
    ├── cpp/
    │   ├── receiver_model.cpp
    │   └── Makefile
    ├── rtl/
    │   ├── fir_filter.sv
    │   ├── qpsk_demapper.sv
    │   └── receiver_top.sv
    ├── tb/
    │   ├── cocotb/
    │   │   ├── Makefile
    │   │   └── test_receiver.py
    │   ├── assertions/
    │   │   ├── receiver_assertions.sv
    │   │   └── receiver_verification_top.sv
    │   └── smoke/
    │       └── receiver_smoke_tb.sv
    ├── vectors/
    │   ├── input_samples.csv
    │   ├── matlab_expected.csv
    │   ├── cpp_expected.csv
    │   └── receiver_results.mat
    ├── scripts/
    │   ├── compare_models.py
    │   ├── compare_rtl.py
    │   └── run_regression.sh
    ├── results/
    │   ├── cpp_vs_matlab.txt
    │   ├── rtl_vs_matlab.txt
    │   └── rtl_output.csv
    └── build/

Generated executable, build, waveform, and report files may not exist until the relevant commands are run.

## Tools

The project uses:

- MATLAB or MATLAB Online
- C++17 compiler
- GNU Make
- Python 3.11 or later
- cocotb
- Icarus Verilog
- GTKWave
- Docker and XQuartz for GTKWave on macOS

## Setup

Create the Python virtual environment and install cocotb:

    make setup

Alternatively:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

Verify the required tools:

    python3 --version
    c++ --version
    iverilog -V
    vvp -V
    cocotb-config --version

## MATLAB Golden Model

The MATLAB model generates the shared input vectors and golden receiver results.

Run in MATLAB or MATLAB Online:

    run_all

Generated files:

    input_samples.csv
    matlab_expected.csv
    receiver_results.mat

Place the downloaded files in:

    vectors/

The current dataset contains:

    32 input samples
    28 valid five-tap FIR outputs

The first four samples fill the FIR delay line.

## C++ Bit-Accurate Model

Build and run the C++ model:

    make cpp

The model reads:

    vectors/input_samples.csv

It writes:

    vectors/cpp_expected.csv

Compare the C++ output against MATLAB:

    make compare-cpp

Expected result:

    Total field mismatches: 0
    RESULT: PASS

The report is saved to:

    results/cpp_vs_matlab.txt

## RTL Syntax Check

Compile-check the SystemVerilog receiver:

    make rtl-check

The RTL consists of:

- `fir_filter.sv`
- `qpsk_demapper.sv`
- `receiver_top.sv`

A successful syntax check completes without compilation errors.

## Cocotb Verification

Run the cocotb testbench:

    make sim

The testbench:

- Applies reset.
- Reads the shared input CSV.
- Drives all I/Q samples into the RTL.
- Reads the MATLAB expected output.
- Compares every RTL output field.
- Runs the assertion monitor.
- Writes the captured RTL output to CSV.
- Generates a waveform.

Expected result:

    test_receiver_against_matlab passed

The captured output is written to:

    results/rtl_output.csv

## Independent RTL Comparison

Compare the captured RTL CSV against MATLAB:

    make compare-rtl

Expected result:

    Total field mismatches: 0
    RESULT: PASS

The report is saved to:

    results/rtl_vs_matlab.txt

## Full Regression

Run the complete verification flow:

    make regression

The regression performs:

1. Build and run the C++ receiver.
2. Compare C++ against MATLAB.
3. Compile-check the SystemVerilog RTL.
4. Run cocotb and the RTL assertions.
5. Compare captured RTL results against MATLAB.

A successful run ends with:

    REGRESSION RESULT: PASS

## Generated Reports

Display both comparison reports:

    make reports

Expected verification status:

    C++ versus MATLAB mismatches: 0
    RTL versus MATLAB mismatches: 0
    cocotb failures: 0
    RTL assertion failures: 0

## Waveforms

Locate the generated waveform:

    make waveform-path

The waveform may be stored as an FST or VCD file under:

    build/cocotb/

On macOS, open it using the configured Docker GTKWave function:

    docker-gtkwave build/cocotb/receiver_verification_top.fst

Use the exact path returned by:

    make waveform-path

Important signals:

- `clk`
- `rst_n`
- `in_valid`
- `i_in`
- `q_in`
- `out_valid`
- `fir_acc_i`
- `fir_acc_q`
- `fir_i`
- `fir_q`
- `bit_msb`
- `bit_lsb`

## Available Make Targets

Display all commands:

    make help

Main targets:

| Command | Description |
|---|---|
| `make setup` | Create the Python environment and install dependencies |
| `make cpp` | Build and run the C++ receiver |
| `make compare-cpp` | Compare C++ against MATLAB |
| `make rtl-check` | Compile-check the RTL |
| `make sim` | Run cocotb verification |
| `make compare-rtl` | Compare RTL against MATLAB |
| `make regression` | Run the complete verification flow |
| `make reports` | Display comparison reports |
| `make waveform-path` | Locate waveform files |
| `make clean` | Remove generated files |

## Verification Checks

The project verifies:

- Signed fixed-point FIR arithmetic
- Division truncation toward zero
- FIR valid-output timing
- QPSK quadrant mapping
- Zero treated as positive
- Reset behavior
- Stable FIR registers during input stalls
- MATLAB and C++ equivalence
- MATLAB and RTL equivalence
- Waveform generation

## Current Results

The deterministic regression is expected to produce:

    MATLAB input samples:       32
    Valid FIR outputs:          28
    C++ field mismatches:        0
    RTL field mismatches:        0
    Demapper mismatches:         0

## Cleaning Generated Files

Remove build artifacts and generated reports:

    make clean

The MATLAB golden vectors should be preserved or regenerated before running the full regression again.

## Specification

The complete receiver behavior and verification requirements are documented in:

    specs/receiver_spec.md
