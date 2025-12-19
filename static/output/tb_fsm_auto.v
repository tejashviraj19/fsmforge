`timescale 1ns / 1ps
module tb_fsm_auto;
    reg clk, reset;
    wire [2:0] q;

    fsm_auto uut (.clk(clk), .reset(reset), .q(q));

    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    initial begin
        reset = 1;
        #10 reset = 0;
        #200 $finish;
    end

    initial begin
        $monitor("Time=%0t | q=%b", $time, q);
    end
endmodule
