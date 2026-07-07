`timescale 1ns/1ps
`default_nettype none

module receiver_verification_top (
    input  logic                    clk,
    input  logic                    rst_n,

    input  logic                    in_valid,
    input  logic signed [15:0]      i_in,
    input  logic signed [15:0]      q_in,

    output logic                    out_valid,
    output logic signed [31:0]      fir_acc_i,
    output logic signed [31:0]      fir_acc_q,
    output logic signed [15:0]      fir_i,
    output logic signed [15:0]      fir_q,
    output logic                    bit_msb,
    output logic                    bit_lsb
);

    receiver_top dut (
        .clk       (clk),
        .rst_n     (rst_n),
        .in_valid  (in_valid),
        .i_in      (i_in),
        .q_in      (q_in),
        .out_valid (out_valid),
        .fir_acc_i (fir_acc_i),
        .fir_acc_q (fir_acc_q),
        .fir_i     (fir_i),
        .fir_q     (fir_q),
        .bit_msb   (bit_msb),
        .bit_lsb   (bit_lsb)
    );

    receiver_assertions checks (
        .clk       (clk),
        .rst_n     (rst_n),
        .in_valid  (in_valid),
        .out_valid (out_valid),
        .fir_acc_i (fir_acc_i),
        .fir_acc_q (fir_acc_q),
        .fir_i     (fir_i),
        .fir_q     (fir_q),
        .bit_msb   (bit_msb),
        .bit_lsb   (bit_lsb)
    );

endmodule

`default_nettype wire
