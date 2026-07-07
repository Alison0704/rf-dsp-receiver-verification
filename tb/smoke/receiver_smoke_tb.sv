`timescale 1ns/1ps
`default_nettype none

module receiver_smoke_tb;

    logic clk;
    logic rst_n;
    logic in_valid;

    logic signed [15:0] i_in;
    logic signed [15:0] q_in;

    logic out_valid;
    logic signed [31:0] fir_acc_i;
    logic signed [31:0] fir_acc_q;
    logic signed [15:0] fir_i;
    logic signed [15:0] fir_q;
    logic bit_msb;
    logic bit_lsb;

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

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    task automatic drive_sample(
        input logic signed [15:0] sample_i,
        input logic signed [15:0] sample_q
    );
        begin
            @(negedge clk);
            in_valid = 1'b1;
            i_in = sample_i;
            q_in = sample_q;
        end
    endtask

    initial begin
        $dumpfile("results/receiver_top.vcd");
        $dumpvars(0, receiver_smoke_tb);

        rst_n = 1'b0;
        in_valid = 1'b0;
        i_in = 16'sd0;
        q_in = 16'sd0;

        repeat (2) @(posedge clk);

        @(negedge clk);
        rst_n = 1'b1;

        drive_sample( 16'sd1000,  16'sd1000);
        drive_sample(-16'sd1000,  16'sd1000);
        drive_sample(-16'sd1000, -16'sd1000);
        drive_sample( 16'sd1000, -16'sd1000);
        drive_sample( 16'sd0,     16'sd1000);
        drive_sample(-16'sd1000,  16'sd0);
        drive_sample( 16'sd0,    -16'sd1000);
        drive_sample( 16'sd1000,  16'sd0);

        @(negedge clk);
        in_valid = 1'b0;
        i_in = 16'sd0;
        q_in = 16'sd0;

        repeat (3) @(posedge clk);

        $finish;
    end

endmodule

`default_nettype wire
