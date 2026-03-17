"""Live dashboard server for cli-anything-touchdesigner.

Serves a visual network editor that shows operators, connections, and
lets you run CLI commands — all updating in real-time.
"""

import json
import os
import sys

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add parent to path so we can import the CLI package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli_anything_touchdesigner.project import ProjectManager, TDProject
from cli_anything_touchdesigner.network import NetworkBuilder, TEMPLATES
from cli_anything_touchdesigner.operators import get_families, get_types, suggest_operators, find_type

app = Flask(__name__, static_folder="static")
CORS(app)

manager = ProjectManager()
PROJECT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard_project.json")


def get_or_create_project():
    proj = manager.active_project
    if proj is None:
        if os.path.isfile(PROJECT_FILE):
            proj = manager.open_project(PROJECT_FILE)
        else:
            proj = manager.new_project("LiveDashboard")
            proj.save(PROJECT_FILE)
    return proj


def save_project():
    proj = manager.active_project
    if proj:
        proj.save(PROJECT_FILE)


# --- Static files ---

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/generative")
def generative():
    return send_from_directory("static", "generative.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# --- API ---

@app.route("/api/project", methods=["GET"])
def api_project():
    proj = get_or_create_project()
    return jsonify(proj.to_dict())


@app.route("/api/project/info", methods=["GET"])
def api_project_info():
    proj = get_or_create_project()
    return jsonify(proj.info())


@app.route("/api/project/new", methods=["POST"])
def api_project_new():
    data = request.json or {}
    name = data.get("name", "Untitled")
    global manager
    manager = ProjectManager()
    proj = manager.new_project(name)
    proj.save(PROJECT_FILE)
    return jsonify({"status": "success", "info": proj.info()})


@app.route("/api/op/add", methods=["POST"])
def api_op_add():
    proj = get_or_create_project()
    data = request.json
    family = data.get("family", "TOP")
    op_type = data.get("type", "nullTOP")
    name = data.get("name", "op1")
    parent = data.get("parent", "/project1")
    position = data.get("position", [0, 0])
    params = data.get("params", {})

    type_info = find_type(family, op_type)
    if type_info:
        resolved = type_info["type"]
        merged = dict(type_info["defaults"])
        merged.update(params)
        params = merged
    else:
        resolved = op_type

    try:
        op = proj.add_operator(name, family, resolved, parent, position, params)
        save_project()
        return jsonify({"status": "success", "operator": op})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/op/remove", methods=["POST"])
def api_op_remove():
    proj = get_or_create_project()
    data = request.json
    path = data.get("path")
    if proj.remove_operator(path):
        save_project()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404


@app.route("/api/op/set", methods=["POST"])
def api_op_set():
    proj = get_or_create_project()
    data = request.json
    path = data.get("path")
    param = data.get("param")
    value = data.get("value")
    if proj.set_parameter(path, param, value):
        save_project()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404


@app.route("/api/net/connect", methods=["POST"])
def api_net_connect():
    proj = get_or_create_project()
    data = request.json
    try:
        conn = proj.connect(data["from"], data["to"],
                            data.get("from_index", 0), data.get("to_index", 0))
        save_project()
        return jsonify({"status": "success", "connection": conn})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/net/disconnect", methods=["POST"])
def api_net_disconnect():
    proj = get_or_create_project()
    data = request.json
    if proj.disconnect(data["from"], data["to"]):
        save_project()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404


@app.route("/api/net/template", methods=["POST"])
def api_net_template():
    proj = get_or_create_project()
    data = request.json
    template_name = data.get("template")
    builder = NetworkBuilder(proj)

    template_map = {
        "audio-reactive": lambda: builder.build_audio_reactive(
            audio_file=data.get("audio_file", "")),
        "feedback-loop": lambda: builder.build_feedback_loop(),
        "3d-scene": lambda: builder.build_3d_scene(
            geometry=data.get("geometry", "box")),
        "particle-system": lambda: builder.build_particle_system(),
        "instancing": lambda: builder.build_instancing(
            count=data.get("count", 100)),
        "glsl-shader": lambda: builder.build_glsl_shader(
            shader_code=data.get("shader_code", "")),
        "osc-receiver": lambda: builder.build_osc_receiver(
            port=data.get("port", 7000)),
        "video-mixer": lambda: builder.build_video_mixer(
            input_count=data.get("input_count", 2)),
    }

    func = template_map.get(template_name)
    if not func:
        return jsonify({"status": "error", "message": f"Unknown template: {template_name}"}), 400

    created = func()
    save_project()
    return jsonify({
        "status": "success",
        "operators_created": len(created),
        "operators": [o["path"] for o in created],
    })


@app.route("/api/net/templates", methods=["GET"])
def api_net_templates():
    return jsonify(TEMPLATES)


@app.route("/api/op/types", methods=["GET"])
def api_op_types():
    family = request.args.get("family")
    if family:
        return jsonify(get_types(family))
    result = {}
    for fam in get_families():
        result[fam] = get_types(fam)
    return jsonify(result)


@app.route("/api/op/suggest", methods=["GET"])
def api_op_suggest():
    desc = request.args.get("q", "")
    return jsonify(suggest_operators(desc))


@app.route("/api/export/script", methods=["GET"])
def api_export_script():
    proj = get_or_create_project()
    return jsonify({"script": proj.generate_td_script()})


@app.route("/api/undo", methods=["POST"])
def api_undo():
    proj = get_or_create_project()
    if proj.undo():
        save_project()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Nothing to undo"})


@app.route("/api/redo", methods=["POST"])
def api_redo():
    proj = get_or_create_project()
    if proj.redo():
        save_project()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Nothing to redo"})


@app.route("/api/project/clear", methods=["POST"])
def api_project_clear():
    proj = get_or_create_project()
    proj.operators.clear()
    proj.connections.clear()
    proj._mark_dirty()
    save_project()
    return jsonify({"status": "success"})


if __name__ == "__main__":
    print("\n  🎛️  TouchDesigner CLI Dashboard")
    print("  ────────────────────────────────")
    print("  http://localhost:5555\n")
    app.run(host="0.0.0.0", port=5555, debug=False)
