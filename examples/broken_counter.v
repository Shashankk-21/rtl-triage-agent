module broken_counter (
    input wire clk,
    input wire reset,
    output reg [3:0] count
);
always @(posedge clk) begin
    if (reset)
        count <= 4'b0;
    else
        count <= count + 1'b1;
end
endmodule
