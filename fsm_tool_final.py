# fsm_tool_final.py
import os
import re
import ast
import sys
import math
import matplotlib

matplotlib.use("Agg")

from sympy import symbols, SOPform, simplify_logic
from sympy.logic.boolalg import And, Or, Not
import schemdraw
import schemdraw.logic as lg
import schemdraw.elements as elm


#helpers for logic synthesis

def bits_needed_for_sequence(seq):
    maxv = max(seq) if seq else 0
    return max(1, maxv.bit_length())

def tuple_from_int(val, bits):
    return tuple((val >> k) & 1 for k in range(bits))

def normalize_expr_to_ops(expr):
    """Return expression string in simplified DNF using ~,&,|."""
    if expr is True:
        return "1"
    if expr is False:
        return "0"
    try:
        expr_dnf = simplify_logic(expr, form="dnf")
    except Exception:
        expr_dnf = expr
    s = str(expr_dnf).replace(" ", "")
    s = s.replace("True", "1").replace("False", "0")
    return s

#derive eqn
def derive_equations(sequence, ff_type):
    ff_type = ff_type.upper()
    if ff_type not in ("D", "T", "JK", "SR"):
        raise ValueError("Flip-flop must be one of D,T,JK,SR")

    bits = bits_needed_for_sequence(sequence)
    Q = symbols(" ".join([f"Q{i}" for i in range(bits)]))

#mapping present to next
    trans = {sequence[i]: sequence[(i + 1) % len(sequence)] for i in range(len(sequence))}
    used_present = set(sequence)
    next_on = [[] for _ in range(bits)]
    next_dc = [[] for _ in range(bits)]

    for code in range(1 << bits):
        pt = tuple_from_int(code, bits)
        if code in used_present:
            nxt = trans[code]
            nxt_tuple = tuple_from_int(nxt, bits)
            for i in range(bits):
                if nxt_tuple[i] == 1:
                    next_on[i].append(list(pt))
        else:
            for i in range(bits):
                next_dc[i].append(list(pt))

    next_expr = []
    for i in range(bits):
        if next_on[i]:
            expr_i = SOPform(Q, next_on[i], next_dc[i])
        else:
            expr_i = And()  # False
        next_expr.append(expr_i)

    eq_strings = {}
    if ff_type == "D":
        for i in range(bits):
            eq_strings[f"D{i}"] = normalize_expr_to_ops(next_expr[i])
    elif ff_type == "T":
        for i in range(bits):
            Qi = Q[i]
            Ni = next_expr[i]
            xor_expr = Or(And(Qi, Not(Ni)), And(Not(Qi), Ni))
            eq_strings[f"T{i}"] = normalize_expr_to_ops(xor_expr)
    elif ff_type == "JK":
        for i in range(bits):
            Qi = Q[i]
            Ni = next_expr[i]
            J = And(Not(Qi), Ni)
            K = And(Qi, Not(Ni))
            eq_strings[f"J{i}"] = normalize_expr_to_ops(J)
            eq_strings[f"K{i}"] = normalize_expr_to_ops(K)
    elif ff_type == "SR":
        for i in range(bits):
            Qi = Q[i]
            Ni = next_expr[i]
            S = And(Not(Qi), Ni)
            R = And(Qi, Not(Ni))
            eq_strings[f"S{i}"] = normalize_expr_to_ops(S)
            eq_strings[f"R{i}"] = normalize_expr_to_ops(R)

    return {"bits": bits, "eqs": eq_strings, "trans": trans}

class ExprToGate(ast.NodeVisitor):
    def __init__(self, drawing):
        self.d = drawing
        self.next_y = 0

    def _new_input(self, label):
        y = float(self.next_y)
        dot = self.d.add(elm.Dot().label(label, loc='left').at((0.0, y)))
        self.next_y -= 2
        return dot

    def visit_Name(self, node):
        return self._new_input(node.id)

    def visit_Constant(self, node):
        val = node.value
        return self._new_input(str(val))

    def visit_UnaryOp(self, node):
    
        if isinstance(node.op, ast.Invert):
            child = self.visit(node.operand)
            child_end = getattr(child, "end", (0.0, float(self.next_y)))
            gate = self.d.add(lg.Not().at(child_end))
            try:
                self.d += elm.Line().at(child.end).to(gate.in1)
            except Exception:
                pass
            return gate
        raise NotImplementedError(f"Unsupported unary op: {ast.dump(node)}")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        left_end = getattr(left, "end", (0.0, float(self.next_y)))
        right_end = getattr(right, "end", (0.0, float(self.next_y - 1)))
        x = max(float(left_end[0]), float(right_end[0])) + 3.0
        y = (float(left_end[1]) + float(right_end[1])) / 2.0

        if isinstance(node.op, ast.BitAnd):
            g = self.d.add(lg.And().at((x, y)))
        elif isinstance(node.op, ast.BitOr):
            g = self.d.add(lg.Or().at((x, y)))
        else:
            raise NotImplementedError(f"Unsupported binary op: {ast.dump(node)}")
        try:
            if hasattr(g, "in1") and hasattr(left, "end"):
                self.d += elm.Line().at(left.end).to(g.in1)
        except Exception:
            pass
        try:
            if hasattr(g, "in2") and hasattr(right, "end"):
                self.d += elm.Line().at(right.end).to(g.in2)
        except Exception:
            pass

        return g


def draw_boolean(expr_str, out_name, filename):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    try:
        with schemdraw.Drawing(file=filename, show=False) as d:
            d.config(inches_per_unit=0.5)
            try:
                d.ax.set_xlim(0.0, 12.0)
                d.ax.set_ylim(-8.0, 4.0)
                d.ax.set_autoscale_on(False)
            except Exception:
                pass
            if expr_str.strip() in ("", "0"):
                inp = d.add(elm.Dot().label("0", loc='left').at((0.0, 0.0)))
                d += elm.Line().at(inp).tox(3.0)
                d += elm.Dot().at((3.0, 0.0)).label(out_name, loc='right')
                return

            if expr_str.strip() == "1":
                inp = d.add(elm.Dot().label("1", loc='left').at((0.0, 0.0)))
                d += elm.Line().at(inp).tox(3.0)
                d += elm.Dot().at((3.0, 0.0)).label(out_name, loc='right')
                return

            expr_clean = expr_str.replace(" ", "")
            node = ast.parse(expr_clean, mode="eval").body

            parser = ExprToGate(d)
            last = parser.visit(node)
            out_pos = getattr(last, "out", None)
            if out_pos is not None:
                try:
                    d += elm.Dot().at(out_pos).label(out_name, loc='right')
                except Exception:
                    d += elm.Label().label(f"{out_name}: {expr_str}")
            else:
                d += elm.Label().label(f"{out_name}: {expr_str}")
    except Exception as e:
        try:
            with schemdraw.Drawing(file=filename, show=False) as d:
                d.config(inches_per_unit=0.5)
                d.ax.set_xlim(0.0, 6.0)
                d.ax.set_ylim(-2.0, 2.0)
                d.ax.set_autoscale_on(False)
                d += elm.Label().label(f"{out_name} = {expr_str}\n(draw error: {e})")
        except Exception:
            with open(filename + ".txt", "w") as f:
                f.write(f"{out_name} = {expr_str}\nError drawing: {e}\n")

# verilog and testbench generation
def generate_verilog(ff_type, equations, num_ff, out_folder):
    verilog_code = f"""// Auto-generated FSM Counter ({ff_type} Flip-Flop)
module fsm_auto(input wire clk, input wire reset, output reg [{num_ff-1}:0] q);
always @(posedge clk or posedge reset) begin
    if (reset)
        q <= {num_ff}'b{'0'*num_ff};
    else begin
"""
    for i, eq in enumerate(equations):
        eq_logic = re.sub(r"Q(\d+)", r"q[\1]", eq)
        verilog_code += f"        q[{i}] <= {eq_logic};\n"

    verilog_code += """    end
end
endmodule
"""
    with open(f"{out_folder}/fsm_auto.v", "w") as f:
        f.write(verilog_code)
    print(f" Verilog module generated: {out_folder}/fsm_auto.v")
    return verilog_code


def generate_testbench(num_ff, out_folder):
    tb_code = f"""`timescale 1ns / 1ps
module tb_fsm_auto;
    reg clk, reset;
    wire [{num_ff-1}:0] q;

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
"""
    with open(f"{out_folder}/tb_fsm_auto.v", "w") as f:
        f.write(tb_code)
    print(f"Testbench generated: {out_folder}/tb_fsm_auto.v")
    return tb_code

#driver func
def main():
    seq_input = input("Enter state sequence (space seperated): ")
    ff_type = input("Enter FF type (D/T/JK/SR): ").upper()

    seq = [int(x) for x in seq_input.strip().split()]
    out_folder = "output"
    os.makedirs(out_folder, exist_ok=True)

    result = derive_equations(seq, ff_type)
    equations_dict = result["eqs"]
    num_ff = result["bits"]

    print("\n=== FF Excitation Equations ===")
    for name, eq in equations_dict.items():
        print(f"{name} = {eq}")

    print("\nGenerating gate-level schematics...")
    for name, expr in equations_dict.items():
        try:
            draw_boolean(expr, name, os.path.join(out_folder, f"{name}.png"))
            print(f"  -> {name}.png")
        except Exception as e:
            print(f"Diagram for {name} failed: {expr}  Error: {e}")
    generate_verilog(ff_type, list(equations_dict.values()), num_ff, out_folder)
    generate_testbench(num_ff, out_folder)

    print("\n All files generated successfully in 'output' folder:")
    print("   - Gate-level diagrams (.png)")
    print("   - Verilog module (fsm_auto.v)")
    print("   - Testbench (tb_fsm_auto.v)")


if __name__ == "__main__":
    main()