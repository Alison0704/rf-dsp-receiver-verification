"""Verify asynchronous reset and receiver recovery during operation."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge, Timer


FIR_COEFFICIENTS = [1, 2, 3, 2, 1]
FIR_DIVISOR = 9


def truncate_toward_zero(value: int, divisor: int) -> int:
    magnitude = abs(value) // divisor
    return -magnitude if value < 0 else magnitude


def signed(signal) -> int:
    return signal.value.to_signed()


def unsigned(signal) -> int:
    return int(signal.value)


def capture_outputs(dut) -> dict[str, int]:
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
    """Cycle-accurate receiver reference model."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
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


async def drive_samples(
    dut,
    reference: ReceiverReferenceModel,
    samples: list[tuple[int, int]],
    phase_name: str,
) -> None:
    """Drive and check a sequence of accepted samples."""
    for sample_number, (i_in, q_in) in enumerate(samples):
        dut.in_valid.value = 1
        dut.i_in.value = i_in
        dut.q_in.value = q_in

        expected = reference.step(
            in_valid=1,
            i_in=i_in,
            q_in=q_in,
        )

        await RisingEdge(dut.clk)
        await ReadOnly()

        actual = capture_outputs(dut)

        for field, expected_value in expected.items():
            assert actual[field] == expected_value, (
                f"{phase_name}, sample {sample_number}, "
                f"{field}: expected={expected_value}, "
                f"actual={actual[field]}"
            )

        await FallingEdge(dut.clk)


@cocotb.test()
async def test_receiver_midstream_reset(dut):
    """Reset an active receiver and verify clean recovery."""
    reference = ReceiverReferenceModel()

    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initial reset.
    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)

    dut.rst_n.value = 1

    samples_before_reset = [
        (1000, 1000),
        (-1000, 1000),
        (-1000, -1000),
        (1000, -1000),
        (2000, 500),
        (-500, -2000),
    ]

    await drive_samples(
        dut,
        reference,
        samples_before_reset,
        "before reset",
    )

    # Six accepted samples should have produced two valid outputs.
    assert reference.accepted_samples == 6

    # Assert reset between clock edges while the receiver is active.
    dut.in_valid.value = 0
    dut.i_in.value = 1234
    dut.q_in.value = -1234
    dut.rst_n.value = 0

    await Timer(1, unit="ns")
    await ReadOnly()

    reset_outputs = capture_outputs(dut)

    expected_reset_outputs = {
        "out_valid": 0,
        "fir_acc_i": 0,
        "fir_acc_q": 0,
        "fir_i": 0,
        "fir_q": 0,
        "bit_msb": 0,
        "bit_lsb": 0,
    }

    assert reset_outputs == expected_reset_outputs, (
        "Receiver outputs were not cleared by asynchronous reset:\n"
        f"Expected: {expected_reset_outputs}\n"
        f"Actual:   {reset_outputs}"
    )

    reference.reset()

    # Hold reset for two complete cycles.
    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)

    dut.rst_n.value = 1

    samples_after_reset = [
        (3000, -1000),
        (1000, 2000),
        (-2000, 3000),
        (-3000, -1000),
        (500, 500),
        (-500, 1000),
    ]

    await drive_samples(
        dut,
        reference,
        samples_after_reset,
        "after reset",
    )

    assert reference.accepted_samples == 6

    # Stop input traffic and verify the valid pulse drops.
    dut.in_valid.value = 0
    dut.i_in.value = 0
    dut.q_in.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()

    final_outputs = capture_outputs(dut)

    assert final_outputs["out_valid"] == 0
    assert final_outputs["bit_msb"] == 0
    assert final_outputs["bit_lsb"] == 0

    dut._log.info(
        "Mid-stream asynchronous reset and receiver recovery verified"
    )
