`timescale 1ns/1ps
`default_nettype none

module qpsk_demapper (
    input  logic                 symbol_valid,
    input  logic signed [15:0]   symbol_i,
    input  logic signed [15:0]   symbol_q,

    output logic                 bit_msb,
    output logic                 bit_lsb
);

    /*
     * QPSK hard-decision mapping:
     *
     * I >= 0, Q >= 0  -> 00
     * I <  0, Q >= 0  -> 01
     * I <  0, Q <  0  -> 11
     * I >= 0, Q <  0  -> 10
     *
     * Zero is treated as positive.
     */

    always_comb begin
        bit_msb = 1'b0;
        bit_lsb = 1'b0;

        if (symbol_valid) begin
            bit_msb = symbol_q < 16'sd0;
            bit_lsb = symbol_i < 16'sd0;
        end
    end

endmodule

`default_nettype wire
