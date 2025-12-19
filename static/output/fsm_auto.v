// Auto-generated FSM Counter (JK Flip-Flop)
module fsm_auto(input wire clk, input wire reset, output reg [2:0] q);
always @(posedge clk or posedge reset) begin
    if (reset)
        q <= 3'b000;
    else begin
        q[0] <= q[2]&~q[0]&~q[1];
        q[1] <= q[0];
        q[2] <= q[0]&~q[1];
        q[3] <= q[1]&~q[0];
        q[4] <= ~q[1]&~q[2];
        q[5] <= q[1]&q[2];
    end
end
endmodule
