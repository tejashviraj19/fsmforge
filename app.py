from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from fsm_tool_final import derive_equations, draw_boolean, generate_verilog, generate_testbench

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "static", "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- TOOL PAGE ----------------
@app.route("/tool")
def tool():
    return render_template("tool.html")

# ---------------- GENERATE LOGIC ----------------
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
        img_path = os.path.join(OUTPUT_DIR, f"{name}.png")
        draw_boolean(expr, name, img_path)
        images.append(f"/static/output/{name}.png")

    # Save Verilog
    verilog_code = generate_verilog(ff_type, list(equations.values()), bits, OUTPUT_DIR)
    with open(os.path.join(OUTPUT_DIR, "fsm_auto.v"), "w") as f:
        f.write(verilog_code)

    # Save Testbench
    testbench_code = generate_testbench(bits, OUTPUT_DIR)
    with open(os.path.join(OUTPUT_DIR, "tb_fsm_auto.v"), "w") as f:
        f.write(testbench_code)

    return jsonify({
        "equations": equations,
        "images": images
    })

# ---------------- DOWNLOAD ROUTES ----------------
@app.route("/download/verilog")
def download_verilog():
    return send_from_directory(
        OUTPUT_DIR,
        "fsm_auto.v",
        as_attachment=True
    )

@app.route("/download/testbench")
def download_testbench():
    return send_from_directory(
        OUTPUT_DIR,
        "tb_fsm_auto.v",
        as_attachment=True
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
