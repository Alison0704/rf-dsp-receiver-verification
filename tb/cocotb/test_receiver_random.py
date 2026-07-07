"""Deterministic randomized verification for the QPSK receiver."""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge


RANDOM_SEED = 20260707
NUMBER_OF_CYCLES = 200

FIR_COEFFICIENTS = [1, 2, 3, 2, 1]
FIR_DIVISOR = 9


def truncate_toward_zero(value: int, divisor: int) -> int:
    """Perform signed integer division with truncation toward zero."""
    magnitude = abs(value) // divisor
    return -magnitude if value < 0 else magnitude


def signed(signal) -> int:
    """Read a signed SystemVerilog signal."""
    return signal.value.to_signed()


def unsigned(signal) -> int:
    """Read an unsigned SystemVerilog signal."""
    return int(signal.value)


def capture_outputs(dut) -> dict[str, int]:
    """Capture all receiver outputs."""
    return {
        "out_valid": unsigned(dut.out_valid),
        "fir_acc_i": signed(dut.fir_acc_i),
        "fir_acc_q": signed(dut.fir_acc_q),
        "fir_i": signed(dut.fir_i),
        "fir_q": signed(dut.fir_q),
        "bit_msb": unsigned(dut.bit_msb),
        "bit_lsb": unsigned(dut.bit_lsb),
    }


class ReceiverReferenceModel:
    """Cycle-accurate software model of the RTL receiver."""

    def __init__(self) -> None:
        self.delay_i = [0, 0, 0, 0, 0]
        self.delay_q = [0, 0, 0, 0, 0]

        self.accepted_samples = 0

        self.fir_acc_i = 0
        self.fir_acc_q = 0
        self.fir_i = 0
        self.fir_q = 0

    def step(
        self,
        in_valid: int,
        i_in: int,
        q_in: int,
    ) -> dict[str, int]:
        """Advance the model by one rising clock edge."""
        out_valid = 0
        bit_msb = 0
        bit_lsb = 0

        if in_valid:
            self.delay_i = [i_in, *self.delay_i[:4]]
            self.delay_q = [q_in, *self.delay_q[:4]]

            self.fir_acc_i = sum(
                sample * coefficient
                for sample, coefficient in zip(
                    self.delay_i,
                    FIR_COEFFICIENTS,
                )
            )

            self.fir_acc_q = sum(
                sample * coefficient
                for sample, coefficient in zip(
                    self.delay_q,
                    FIR_COEFFICIENTS,
                )
            )

            self.accepted_samples += 1

            if self.accepted_samples >= 5:
                out_valid = 1

                self.fir_i = truncate_toward_zero(
                    self.fir_acc_i,
                    FIR_DIVISOR,
                )

                self.fir_q = truncate_toward_zero(
                    self.fir_acc_q,
                    FIR_DIVISOR,
                )

                bit_msb = int(self.fir_q < 0)
                bit_lsb = int(self.fir_i < 0)

        return {
            "out_valid": out_valid,
            "fir_acc_i": self.fir_acc_i,
            "fir_acc_q": self.fir_acc_q,
            "fir_i": self.fir_i,
            "fir_q": self.fir_q,
            "bit_msb": bit_msb,
            "bit_lsb": bit_lsb,
        }


@cocotb.test()
async def test_receiver_randomized(dut):
    """Compare randomized RTL behavior against a Python model."""
    random_generator = random.Random(RANDOM_SEED)
    reference = ReceiverReferenceModel()

    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)

    dut.rst_n.value = 1

    directed_samples = [
        (1, 0, 0),
        (1, 32767, 32767),
        (1, -32768, -32768),
        (1, 32767, -32768),
        (1, -32768, 32767),
        (0, 12345, -12345),
        (1, 1, -1),
        (1, -1, 1),
    ]

    cycles = list(directed_samples)

    while len(cycles) < NUMBER_OF_CYCLES:
        in_valid = int(random_generator.random() < 0.70)

        i_in = random_generator.randint(-32768, 32767)
        q_in = random_generator.randint(-32768, 32767)

        cycles.append((in_valid, i_in, q_in))

    accepted_count = 0
    stall_count = 0
    valid_output_count = 0

    for cycle_number, (in_valid, i_in, q_in) in enumerate(cycles):
        dut.in_valid.value = in_valid
        dut.i_in.value = i_in
        dut.q_in.value = q_in

        expected = reference.step(
            in_valid=in_valid,
            i_in=i_in,
            q_in=q_in,
        )

        await RisingEdge(dut.clk)
        await ReadOnly()

        actual = capture_outputs(dut)

        if in_valid:
            accepted_count += 1
        else:
            stall_count += 1

        if actual["out_valid"]:
            valid_output_count += 1

        for field, expected_value in expected.items():
            actual_value = actual[field]

            assert actual_value == expected_value, (
                f"Cycle {cycle_number}, {field} mismatch: "
                f"in_valid={in_valid}, "
                f"i_in={i_in}, "
                f"q_in={q_in}, "
                f"expected={expected_value}, "
                f"actual={actual_value}"
            )

        await FallingEdge(dut.clk)

    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()

    final_output = capture_outputs(dut)

    assert final_output["out_valid"] == 0
    assert final_output["bit_msb"] == 0
    assert final_output["bit_lsb"] == 0

    dut._log.info(
        "Random seed: %d",
        RANDOM_SEED,
    )

    dut._log.info(
        "Verified %d cycles: %d accepted, %d stalls, %d valid outputs",
        NUMBER_OF_CYCLES,
        accepted_count,
        stall_count,
        valid_output_count,
    )
