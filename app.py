from flask import Flask, render_template, request, jsonify
import os
from fsm_tool_final import (
    derive_equations,
    draw_boolean,
    generate_verilog,
    generate_testbench
)

app = Flask(__name__)

OUTPUT_DIR = "static/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# -------------------- Landing Page --------------------
@app.route("/")
def home():
    return render_template("index.html")


# -------------------- Main Tool Page --------------------
@app.route("/tool")
def tool():
    return render_template("tool.html")


# -------------------- Backend API --------------------
@app.route("/generate", methods=["POST"])
def generate():
    data = request.json

    sequence = list(map(int, data["sequence"].split()))
    ff_type = data["ff_type"]

    result = derive_equations(sequence, ff_type)
    equations = result["eqs"]
    bits = result["bits"]

    images = []
    for name, expr in equations.items():
        img_path = f"{OUTPUT_DIR}/{name}.png"
        draw_boolean(expr, name, img_path)
        images.append(f"/{img_path}")

    verilog = generate_verilog(ff_type, list(equations.values()), bits, OUTPUT_DIR)
    testbench = generate_testbench(bits, OUTPUT_DIR)

    return jsonify({
        "equations": equations,
        "images": images,
        "verilog": verilog,
        "testbench": testbench
    })


# -------------------- App Entry --------------------
if __name__ == "__main__":
    app.run(debug=True)
