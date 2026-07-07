`timescale 1ns/1ps
`default_nettype none

module receiver_assertions (
    input logic                    clk,
    input logic                    rst_n,
    input logic                    in_valid,

    input logic                    out_valid,
    input logic signed [31:0]      fir_acc_i,
    input logic signed [31:0]      fir_acc_q,
    input logic signed [15:0]      fir_i,
    input logic signed [15:0]      fir_q,
    input logic                    bit_msb,
    input logic                    bit_lsb
);

    integer accepted_count;

    logic signed [31:0] previous_fir_acc_i;
    logic signed [31:0] previous_fir_acc_q;
    logic signed [15:0] previous_fir_i;
    logic signed [15:0] previous_fir_q;

    logic previous_values_available;
    logic expected_out_valid;

    /*
     * These assertions sample the receiver outputs one nanosecond
     * after each rising edge. This allows sequential assignments
     * and combinational demapper logic to settle first.
     */
    always @(posedge clk) begin
        if (!rst_n) begin
            accepted_count = 0;

            #1;

            assert (out_valid === 1'b0)
                else $fatal(
                    1,
                    "ASSERTION FAILED: out_valid must be zero during reset"
                );

            assert (fir_acc_i === 32'sd0)
                else $fatal(
                    1,
                    "ASSERTION FAILED: fir_acc_i must reset to zero"
                );

            assert (fir_acc_q === 32'sd0)
                else $fatal(
                    1,
                    "ASSERTION FAILED: fir_acc_q must reset to zero"
                );

            assert (fir_i === 16'sd0)
                else $fatal(
                    1,
                    "ASSERTION FAILED: fir_i must reset to zero"
                );

            assert (fir_q === 16'sd0)
                else $fatal(
                    1,
                    "ASSERTION FAILED: fir_q must reset to zero"
                );

            assert (
                bit_msb === 1'b0 &&
                bit_lsb === 1'b0
            )
                else $fatal(
                    1,
                    "ASSERTION FAILED: demapper bits must reset to zero"
                );

            previous_fir_acc_i = fir_acc_i;
            previous_fir_acc_q = fir_acc_q;
            previous_fir_i = fir_i;
            previous_fir_q = fir_q;

            previous_values_available = 1'b1;
        end else begin
            /*
             * Count accepted input samples. Saturate at five because
             * five samples are enough to fill the complete FIR window.
             */
            if (in_valid && accepted_count < 5) begin
                accepted_count = accepted_count + 1;
            end

            expected_out_valid =
                in_valid && (accepted_count >= 5);

            #1;

            /*
             * The fifth accepted input produces the first valid
             * five-tap FIR output. Once initialized, out_valid follows
             * in_valid.
             */
            assert (out_valid === expected_out_valid)
                else $fatal(
                    1,
                    "ASSERTION FAILED: out_valid=%0b expected=%0b accepted_count=%0d",
                    out_valid,
                    expected_out_valid,
                    accepted_count
                );

            /*
             * When a symbol is valid, the output bits must represent
             * the signs of the filtered Q and I components.
             */
            if (out_valid) begin
                assert (bit_msb === (fir_q < 16'sd0))
                    else $fatal(
                        1,
                        "ASSERTION FAILED: bit_msb does not match fir_q sign"
                    );

                assert (bit_lsb === (fir_i < 16'sd0))
                    else $fatal(
                        1,
                        "ASSERTION FAILED: bit_lsb does not match fir_i sign"
                    );
            end else begin
                /*
                 * The demapper drives zeros when symbol_valid is low.
                 */
                assert (
                    bit_msb === 1'b0 &&
                    bit_lsb === 1'b0
                )
                    else $fatal(
                        1,
                        "ASSERTION FAILED: demapper bits must be zero when output is invalid"
                    );
            end

            /*
             * The FIR registers must not change during an input stall.
             */
            if (
                !in_valid &&
                previous_values_available
            ) begin
                assert (fir_acc_i === previous_fir_acc_i)
                    else $fatal(
                        1,
                        "ASSERTION FAILED: fir_acc_i changed during input stall"
                    );

                assert (fir_acc_q === previous_fir_acc_q)
                    else $fatal(
                        1,
                        "ASSERTION FAILED: fir_acc_q changed during input stall"
                    );

                assert (fir_i === previous_fir_i)
                    else $fatal(
                        1,
                        "ASSERTION FAILED: fir_i changed during input stall"
                    );

                assert (fir_q === previous_fir_q)
                    else $fatal(
                        1,
                        "ASSERTION FAILED: fir_q changed during input stall"
                    );
            end

            previous_fir_acc_i = fir_acc_i;
            previous_fir_acc_q = fir_acc_q;
            previous_fir_i = fir_i;
            previous_fir_q = fir_q;

            previous_values_available = 1'b1;
        end
    end

endmodule

`default_nettype wire
