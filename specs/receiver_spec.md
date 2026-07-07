# RF/DSP Receiver Specification

## 1. Purpose

This project implements and verifies a fixed-point QPSK receiver using:

- MATLAB as the golden reference model
- C++ as a bit-accurate software model
- SystemVerilog as the RTL implementation
- cocotb as the RTL verification environment

All implementations use the same input vectors, coefficients, fixed-point arithmetic rules, and demapper mapping.

## 2. Receiver Interface

### Inputs

| Signal | Width | Description |
|---|---:|---|
| `clk` | 1 | Rising-edge clock |
| `rst_n` | 1 | Active-low asynchronous reset |
| `in_valid` | 1 | Indicates that `i_in` and `q_in` contain an accepted sample |
| `i_in` | 16 | Signed in-phase input sample |
| `q_in` | 16 | Signed quadrature input sample |

### Outputs

| Signal | Width | Description |
|---|---:|---|
| `out_valid` | 1 | Indicates a valid FIR and demapper output |
| `fir_acc_i` | 32 | Unnormalized I-channel FIR accumulator |
| `fir_acc_q` | 32 | Unnormalized Q-channel FIR accumulator |
| `fir_i` | 16 | Normalized I-channel FIR output |
| `fir_q` | 16 | Normalized Q-channel FIR output |
| `bit_msb` | 1 | Demapped most-significant bit |
| `bit_lsb` | 1 | Demapped least-significant bit |

## 3. FIR Filter

The receiver contains two identical five-tap FIR filters:

- One filter processes the I channel.
- One filter processes the Q channel.

### Coefficients

The FIR coefficients are:

    [1, 2, 3, 2, 1] / 9

### Equation

For either the I or Q channel:

    y[n] = (
        x[n]
      + 2*x[n-1]
      + 3*x[n-2]
      + 2*x[n-3]
      + x[n-4]
    ) / 9

The unnormalized accumulator is:

    accumulator[n] =
        x[n]
      + 2*x[n-1]
      + 3*x[n-2]
      + 2*x[n-3]
      + x[n-4]

The normalized output is:

    output[n] = accumulator[n] / 9

### Arithmetic rules

- Input samples are signed 16-bit integers.
- FIR accumulators are signed 32-bit integers.
- Normalized outputs are signed 16-bit integers.
- Division by 9 truncates toward zero.
- The RTL arithmetic must match MATLAB `fix()` behavior.
- The RTL arithmetic must match signed C++ integer division.
- No rounding is applied.
- No saturation is required for the current vector set.

## 4. Input Acceptance

A sample is accepted on a rising clock edge when:

    in_valid == 1

When `in_valid` is high:

- `i_in` and `q_in` are accepted.
- The I and Q delay lines advance.
- The FIR accumulators are updated.
- The accepted-sample counter advances until it reaches four previous samples.

When `in_valid` is low:

- The delay lines do not advance.
- The FIR accumulator registers remain unchanged.
- The normalized FIR outputs remain unchanged.
- `out_valid` is low.

## 5. FIR Valid Timing

A complete five-tap FIR window requires:

- The current input sample
- Four previously accepted input samples

Therefore:

- Accepted sample 1 produces no valid output.
- Accepted sample 2 produces no valid output.
- Accepted sample 3 produces no valid output.
- Accepted sample 4 produces no valid output.
- Accepted sample 5 produces the first valid output.

The first valid condition is:

    accepted_sample_count >= 5

After initialization:

    out_valid = in_valid

This applies only after the FIR delay line contains four previous accepted samples.

## 6. QPSK Demapper

The demapper performs hard decisions using the signs of `fir_i` and `fir_q`.

| I condition | Q condition | `bit_msb` | `bit_lsb` | Symbol |
|---|---|---:|---:|---|
| `I >= 0` | `Q >= 0` | 0 | 0 | 00 |
| `I < 0` | `Q >= 0` | 0 | 1 | 01 |
| `I < 0` | `Q < 0` | 1 | 1 | 11 |
| `I >= 0` | `Q < 0` | 1 | 0 | 10 |

The bit equations are:

    bit_msb = fir_q < 0
    bit_lsb = fir_i < 0

Zero is treated as positive.

Therefore:

    fir_i == 0 means bit_lsb == 0
    fir_q == 0 means bit_msb == 0

When `out_valid` is low:

    bit_msb = 0
    bit_lsb = 0

## 7. Reset Behaviour

The reset is active low.

While:

    rst_n == 0

the receiver must clear:

- I-channel delay registers
- Q-channel delay registers
- Accepted-sample counter
- FIR accumulator outputs
- Normalized FIR outputs
- `out_valid`
- `bit_msb`
- `bit_lsb`

Expected reset values are:

    out_valid = 0
    fir_acc_i = 0
    fir_acc_q = 0
    fir_i = 0
    fir_q = 0
    bit_msb = 0
    bit_lsb = 0

## 8. Reference Files

### Input vectors

The shared input file is:

    vectors/input_samples.csv

Required columns:

    sample_index,i_in,q_in

### MATLAB golden output

The MATLAB reference output is:

    vectors/matlab_expected.csv

Required columns:

    sample_index
    i_in
    q_in
    output_valid
    fir_acc_i
    fir_acc_q
    fir_i
    fir_q
    bit_msb
    bit_lsb

### C++ output

The C++ model output is:

    vectors/cpp_expected.csv

### RTL output

The cocotb testbench writes:

    results/rtl_output.csv

## 9. Current Dataset

The current deterministic vector set contains:

    32 input samples

Because the first four accepted inputs fill the FIR history, the dataset produces:

    28 valid five-tap FIR outputs

The comparison still checks all 32 rows, including:

- Invalid-output timing for the first four samples
- FIR accumulators
- Normalized FIR outputs
- Demapper outputs

## 10. Verification Architecture

The verification flow is:

    input_samples.csv
            |
            +--> MATLAB golden model
            |
            +--> C++ bit-accurate model
            |
            +--> SystemVerilog RTL through cocotb

The MATLAB output is the golden reference.

The C++ output is compared against MATLAB using:

    scripts/compare_models.py

The RTL output is compared against MATLAB:

- During simulation by the cocotb scoreboard
- After simulation by `scripts/compare_rtl.py`

## 11. Cocotb Scoreboard Requirements

The cocotb testbench must compare:

- `output_valid`
- `fir_acc_i`
- `fir_acc_q`
- `fir_i`
- `fir_q`
- `bit_msb`
- `bit_lsb`

The testbench must:

- Read `vectors/input_samples.csv`
- Read `vectors/matlab_expected.csv`
- Apply reset before driving samples
- Drive inputs before the active rising edge
- Capture outputs after signal updates settle
- Record all RTL results
- Write `results/rtl_output.csv`
- Fail when any mismatch is detected

## 12. Assertion Requirements

The assertion monitor must check:

- Outputs are cleared during reset.
- `out_valid` remains low during the first four accepted samples.
- The fifth accepted sample produces the first valid output.
- Demapper bits match the signs of the FIR outputs.
- Demapper bits are zero when the output is invalid.
- FIR output registers remain stable during input stalls.

Assertion failures must terminate the simulation.

## 13. Waveform Requirements

The cocotb simulation must generate an FST or VCD waveform.

Important signals include:

    clk
    rst_n
    in_valid
    i_in
    q_in
    out_valid
    fir_acc_i
    fir_acc_q
    fir_i
    fir_q
    bit_msb
    bit_lsb

Waveforms can be located with:

    make waveform-path

On macOS, the waveform can be opened using the configured terminal function:

    docker-gtkwave <waveform-path>

## 14. Pass Criteria

The project passes when all of the following conditions are satisfied:

    C++ versus MATLAB field mismatches = 0
    RTL versus MATLAB field mismatches = 0
    cocotb test failures = 0
    RTL assertion failures = 0
    SystemVerilog compilation errors = 0

The complete regression is run with:

    make regression

A successful run must report:

    REGRESSION RESULT: PASS

## 15. Generated Reports

The regression produces:

    results/cpp_vs_matlab.txt
    results/rtl_vs_matlab.txt
    results/rtl_output.csv

The reports can be displayed with:

    make reports
