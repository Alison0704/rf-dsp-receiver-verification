`timescale 1ns/1ps
`default_nettype none

module fir_filter (
    input  logic                    clk,
    input  logic                    rst_n,

    input  logic                    in_valid,
    input  logic signed [15:0]      i_in,
    input  logic signed [15:0]      q_in,

    output logic                    out_valid,
    output logic signed [31:0]      fir_acc_i,
    output logic signed [31:0]      fir_acc_q,
    output logic signed [15:0]      fir_i,
    output logic signed [15:0]      fir_q
);

    /*
     * Five-tap FIR coefficients:
     *
     *     [1, 2, 3, 2, 1] / 9
     *
     * The current input is tap 0. Four previous accepted
     * samples are stored in the delay line.
     */

    logic signed [15:0] i_delay_1;
    logic signed [15:0] i_delay_2;
    logic signed [15:0] i_delay_3;
    logic signed [15:0] i_delay_4;

    logic signed [15:0] q_delay_1;
    logic signed [15:0] q_delay_2;
    logic signed [15:0] q_delay_3;
    logic signed [15:0] q_delay_4;

    logic signed [31:0] next_acc_i;
    logic signed [31:0] next_acc_q;

    logic [2:0] accepted_count;

    /*
     * Calculate the FIR accumulator using the current input
     * and the four stored samples.
     */
    always_comb begin
        next_acc_i =
              ($signed(i_in)      * 32'sd1)
            + ($signed(i_delay_1) * 32'sd2)
            + ($signed(i_delay_2) * 32'sd3)
            + ($signed(i_delay_3) * 32'sd2)
            + ($signed(i_delay_4) * 32'sd1);

        next_acc_q =
              ($signed(q_in)      * 32'sd1)
            + ($signed(q_delay_1) * 32'sd2)
            + ($signed(q_delay_2) * 32'sd3)
            + ($signed(q_delay_3) * 32'sd2)
            + ($signed(q_delay_4) * 32'sd1);
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            i_delay_1 <= 16'sd0;
            i_delay_2 <= 16'sd0;
            i_delay_3 <= 16'sd0;
            i_delay_4 <= 16'sd0;

            q_delay_1 <= 16'sd0;
            q_delay_2 <= 16'sd0;
            q_delay_3 <= 16'sd0;
            q_delay_4 <= 16'sd0;

            accepted_count <= 3'd0;

            out_valid <= 1'b0;

            fir_acc_i <= 32'sd0;
            fir_acc_q <= 32'sd0;

            fir_i <= 16'sd0;
            fir_q <= 16'sd0;
        end else begin
            out_valid <= 1'b0;

            if (in_valid) begin
                /*
                 * Preserve the unnormalized accumulator for
                 * comparison with the MATLAB and C++ models.
                 */
                fir_acc_i <= next_acc_i;
                fir_acc_q <= next_acc_q;

                /*
                 * Four previous samples are required before the
                 * first complete five-tap result is valid.
                 */
                if (accepted_count == 3'd4) begin
                    out_valid <= 1'b1;

                    /*
                     * Signed division truncates toward zero,
                     * matching MATLAB fix() and C++ integer division.
                     */
                    fir_i <= next_acc_i / 32'sd9;
                    fir_q <= next_acc_q / 32'sd9;
                end

                /*
                 * Saturate the counter once the FIR delay line
                 * contains four previous samples.
                 */
                if (accepted_count < 3'd4) begin
                    accepted_count <= accepted_count + 3'd1;
                end

                /*
                 * Advance the delay line only when an input
                 * sample is accepted.
                 */
                i_delay_4 <= i_delay_3;
                i_delay_3 <= i_delay_2;
                i_delay_2 <= i_delay_1;
                i_delay_1 <= i_in;

                q_delay_4 <= q_delay_3;
                q_delay_3 <= q_delay_2;
                q_delay_2 <= q_delay_1;
                q_delay_1 <= q_in;
            end
        end
    end

endmodule

`default_nettype wire
