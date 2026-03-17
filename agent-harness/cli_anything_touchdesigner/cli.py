"""Click-based CLI entry point for cli-anything-touchdesigner.

Provides both subcommand interface for scripting/pipelines and REPL mode
for interactive agent sessions. Every command supports --json for machine
consumption.
"""

import json
import os
import sys
from typing import Optional

import click

from . import __version__
from .backend import get_backend
from .connection import TDConnection, DEFAULT_HOST, DEFAULT_PORT
from .formatter import Formatter
from .network import NetworkBuilder, TEMPLATES
from .operators import find_type, get_families, get_types, suggest_operators
from .project import ProjectManager, TDProject


# ---------------------------------------------------------------------------
# Shared state via Click context
# ---------------------------------------------------------------------------

class CLIState:
    def __init__(self):
        self.manager = ProjectManager()
        self.fmt = Formatter()
        self.project_path: Optional[str] = None

    def require_project(self) -> TDProject:
        proj = self.manager.active_project
        if proj is None:
            if self.project_path and os.path.isfile(self.project_path):
                proj = self.manager.open_project(self.project_path)
            else:
                self.fmt.error("No active project. Create one with 'project new' first.")
                sys.exit(1)
        return proj

    def auto_save(self):
        """Save the active project back to disk if --project was used."""
        proj = self.manager.active_project
        if proj and self.project_path and proj.is_dirty:
            proj.save(self.project_path)


pass_state = click.make_pass_decorator(CLIState, ensure=True)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output JSON for machine consumption.")
@click.option("--project", "project_path", type=click.Path(), help="Project file to load.")
@click.version_option(__version__, prog_name="cli-anything-touchdesigner")
@click.pass_context
def cli(ctx, json_mode, project_path):
    """TouchDesigner CLI for AI Agents.

    Run without a subcommand to enter interactive REPL mode.
    """
    state = CLIState()
    state.fmt = Formatter(json_mode=json_mode)
    state.project_path = project_path
    ctx.obj = state

    if project_path and os.path.isfile(project_path):
        try:
            state.manager.open_project(project_path)
        except Exception as e:
            state.fmt.error(f"Failed to load project: {e}")

    # Auto-save project after command completes
    ctx.call_on_close(state.auto_save)

    # Enter REPL if no subcommand
    if ctx.invoked_subcommand is None:
        from .repl_skin import start_repl
        start_repl(json_mode=json_mode)


# ---------------------------------------------------------------------------
# project commands
# ---------------------------------------------------------------------------

@cli.group()
@pass_state
def project(state):
    """Project management commands."""
    pass


@project.command("new")
@click.argument("name")
@click.option("--type", "project_type", default="standard", help="Project type.")
@click.option("-o", "--output", type=click.Path(), help="Save path.")
@pass_state
def project_new(state, name, project_type, output):
    """Create a new TouchDesigner project."""
    proj = state.manager.new_project(name, project_type)
    if output:
        proj.save(output)
    state.fmt.success(f"Created project: {name}", proj.info())


@project.command("open")
@click.argument("path", type=click.Path(exists=True))
@pass_state
def project_open(state, path):
    """Open an existing project file."""
    try:
        proj = state.manager.open_project(path)
        state.fmt.success(f"Opened project: {proj.name}", proj.info())
    except Exception as e:
        state.fmt.error(f"Failed to open: {e}")
        sys.exit(1)


@project.command("save")
@click.option("-o", "--output", type=click.Path(), help="Output path.")
@pass_state
def project_save(state, output):
    """Save the current project."""
    try:
        state.manager.save_project(output)
        state.fmt.success("Project saved" + (f" to {output}" if output else ""))
    except Exception as e:
        state.fmt.error(f"Save failed: {e}")
        sys.exit(1)


@project.command("info")
@pass_state
def project_info(state):
    """Show project information."""
    proj = state.require_project()
    state.fmt.project_info(proj.info())


# ---------------------------------------------------------------------------
# op (operator) commands
# ---------------------------------------------------------------------------

@cli.group()
@pass_state
def op(state):
    """Operator management commands."""
    pass


@op.command("add")
@click.argument("family")
@click.argument("op_type")
@click.argument("name")
@click.option("--parent", default="/project1", help="Parent component path.")
@click.option("--param", multiple=True, help="Parameter as key=value.")
@click.option("--x", type=int, default=0, help="X position.")
@click.option("--y", type=int, default=0, help="Y position.")
@pass_state
def op_add(state, family, op_type, name, parent, param, x, y):
    """Add an operator to the project."""
    proj = state.require_project()

    # Parse parameters
    params = {}
    for p in param:
        if "=" in p:
            k, v = p.split("=", 1)
            try:
                v = float(v) if "." in v else int(v)
            except ValueError:
                pass
            params[k] = v

    # Resolve type
    type_info = find_type(family, op_type)
    if type_info:
        resolved_type = type_info["type"]
        merged = dict(type_info["defaults"])
        merged.update(params)
        params = merged
    else:
        resolved_type = op_type

    try:
        operator = proj.add_operator(
            name=name,
            family=family,
            op_type=resolved_type,
            parent=parent,
            position=[x, y],
            params=params,
        )
        state.fmt.success(f"Added {family.upper()}: {name} ({resolved_type})", operator)
    except ValueError as e:
        state.fmt.error(str(e))
        sys.exit(1)


@op.command("remove")
@click.argument("path")
@pass_state
def op_remove(state, path):
    """Remove an operator."""
    proj = state.require_project()
    if proj.remove_operator(path):
        state.fmt.success(f"Removed: {path}")
    else:
        state.fmt.error(f"Operator not found: {path}")
        sys.exit(1)


@op.command("list")
@click.option("--family", help="Filter by operator family.")
@click.option("--parent", help="Filter by parent path.")
@pass_state
def op_list(state, family, parent):
    """List operators in the project."""
    proj = state.require_project()
    ops = proj.list_operators(family=family, parent=parent)
    if state.fmt.json_mode:
        state.fmt.data(ops)
    else:
        headers = ["Name", "Family", "Type", "Path"]
        rows = [[o["name"], o["family"], o["type"], o["path"]] for o in ops]
        state.fmt.table(headers, rows, title="Operators")


@op.command("info")
@click.argument("path")
@pass_state
def op_info(state, path):
    """Show operator details."""
    proj = state.require_project()
    operator = proj.get_operator(path)
    if operator:
        if state.fmt.json_mode:
            state.fmt.data(operator)
        else:
            state.fmt.operator_summary(operator)
    else:
        state.fmt.error(f"Operator not found: {path}")
        sys.exit(1)


@op.command("set")
@click.argument("path")
@click.argument("param_name")
@click.argument("value")
@pass_state
def op_set(state, path, param_name, value):
    """Set a parameter value on an operator."""
    proj = state.require_project()
    try:
        value = float(value) if "." in value else int(value)
    except ValueError:
        pass
    if proj.set_parameter(path, param_name, value):
        state.fmt.success(f"Set {param_name}={value} on {path}")
    else:
        state.fmt.error(f"Operator not found: {path}")
        sys.exit(1)


@op.command("get")
@click.argument("path")
@click.argument("param_name")
@pass_state
def op_get(state, path, param_name):
    """Get a parameter value from an operator."""
    proj = state.require_project()
    val = proj.get_parameter(path, param_name)
    if val is not None:
        state.fmt.data({param_name: val})
    else:
        state.fmt.error(f"Parameter '{param_name}' not found on {path}")
        sys.exit(1)


@op.command("flag")
@click.argument("path")
@click.argument("flag_name")
@click.argument("value", type=bool)
@pass_state
def op_flag(state, path, flag_name, value):
    """Set an operator flag (bypass, lock, viewer, render, display)."""
    proj = state.require_project()
    if proj.set_flag(path, flag_name, value):
        state.fmt.success(f"Set {flag_name}={value} on {path}")
    else:
        state.fmt.error(f"Failed to set flag on {path}")
        sys.exit(1)


@op.command("types")
@click.argument("family", required=False)
@pass_state
def op_types(state, family):
    """List available operator types."""
    if family:
        types = get_types(family)
        if state.fmt.json_mode:
            state.fmt.data(types)
        else:
            headers = ["Type", "Label"]
            rows = [[t["type"], t["label"]] for t in types]
            state.fmt.table(headers, rows, title=f"{family.upper()} Operators")
    else:
        result = {}
        for fam in get_families():
            types = get_types(fam)
            result[fam] = len(types)
        if state.fmt.json_mode:
            state.fmt.data(result)
        else:
            for fam, count in result.items():
                click.echo(f"  {click.style(fam, bold=True)}: {count} types")


@op.command("suggest")
@click.argument("description", nargs=-1, required=True)
@pass_state
def op_suggest(state, description):
    """Get operator suggestions for a workflow description."""
    desc = " ".join(description)
    suggestions = suggest_operators(desc)
    if state.fmt.json_mode:
        state.fmt.data(suggestions)
    else:
        headers = ["Family", "Type", "Reason"]
        rows = [[s["family"], s["type"], s["reason"]] for s in suggestions]
        state.fmt.table(headers, rows, title="Suggested Operators")


# ---------------------------------------------------------------------------
# net (network) commands
# ---------------------------------------------------------------------------

@cli.group()
@pass_state
def net(state):
    """Network / connection commands."""
    pass


@net.command("connect")
@click.argument("from_path")
@click.argument("to_path")
@click.option("--from-index", type=int, default=0, help="Output index.")
@click.option("--to-index", type=int, default=0, help="Input index.")
@pass_state
def net_connect(state, from_path, to_path, from_index, to_index):
    """Connect two operators."""
    proj = state.require_project()
    try:
        conn = proj.connect(from_path, to_path, from_index, to_index)
        state.fmt.success(f"Connected: {from_path} → {to_path}", conn)
    except ValueError as e:
        state.fmt.error(str(e))
        sys.exit(1)


@net.command("disconnect")
@click.argument("from_path")
@click.argument("to_path")
@pass_state
def net_disconnect(state, from_path, to_path):
    """Disconnect two operators."""
    proj = state.require_project()
    if proj.disconnect(from_path, to_path):
        state.fmt.success(f"Disconnected: {from_path} ↛ {to_path}")
    else:
        state.fmt.error("Connection not found")
        sys.exit(1)


@net.command("list")
@click.argument("op_path", required=False)
@pass_state
def net_list(state, op_path):
    """List connections."""
    proj = state.require_project()
    conns = proj.list_connections(op_path)
    if state.fmt.json_mode:
        state.fmt.data(conns)
    else:
        headers = ["From", "To", "Out Idx", "In Idx"]
        rows = [
            [c["from"], c["to"], str(c["from_index"]), str(c["to_index"])]
            for c in conns
        ]
        state.fmt.table(headers, rows, title="Connections")


@net.command("template")
@click.argument("template_name")
@click.option("--audio-file", default="", help="Audio file path (audio-reactive).")
@click.option("--geometry", default="box", help="Geometry type (3d-scene).")
@click.option("--count", type=int, default=100, help="Instance count (instancing).")
@click.option("--shader-code", default="", help="GLSL code (glsl-shader).")
@click.option("--port", type=int, default=7000, help="OSC port (osc-receiver).")
@click.option("--input-count", type=int, default=2, help="Input count (video-mixer).")
@click.option("--parent", default="/project1", help="Parent component path.")
@pass_state
def net_template(state, template_name, audio_file, geometry, count,
                 shader_code, port, input_count, parent):
    """Build a network from a pre-built template."""
    proj = state.require_project()
    builder = NetworkBuilder(proj)

    template_map = {
        "audio-reactive": lambda: builder.build_audio_reactive(
            audio_file=audio_file, parent=parent
        ),
        "feedback-loop": lambda: builder.build_feedback_loop(parent=parent),
        "3d-scene": lambda: builder.build_3d_scene(
            geometry=geometry, parent=parent
        ),
        "particle-system": lambda: builder.build_particle_system(parent=parent),
        "instancing": lambda: builder.build_instancing(
            geometry=geometry, count=count, parent=parent
        ),
        "glsl-shader": lambda: builder.build_glsl_shader(
            shader_code=shader_code, parent=parent
        ),
        "osc-receiver": lambda: builder.build_osc_receiver(
            port=port, parent=parent
        ),
        "video-mixer": lambda: builder.build_video_mixer(
            input_count=input_count, parent=parent
        ),
        "disintegration": lambda: builder.build_disintegration(
            geometry=geometry, parent=parent
        ),
    }

    func = template_map.get(template_name)
    if func is None:
        state.fmt.error(
            f"Unknown template: {template_name}. "
            f"Available: {', '.join(TEMPLATES.keys())}"
        )
        sys.exit(1)

    created = func()
    state.fmt.success(
        f"Built template '{template_name}' ({len(created)} operators)",
        {"operators": [o["path"] for o in created]},
    )


@net.command("templates")
@pass_state
def net_templates(state):
    """List available network templates."""
    if state.fmt.json_mode:
        state.fmt.data(TEMPLATES)
    else:
        headers = ["Template", "Description"]
        rows = [[k, v] for k, v in TEMPLATES.items()]
        state.fmt.table(headers, rows, title="Network Templates")


# ---------------------------------------------------------------------------
# render command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("output", default="output.png")
@click.option("--top", default="/project1/out1", help="TOP operator path to render.")
@click.option("--width", type=int, default=1920, help="Output width.")
@click.option("--height", type=int, default=1080, help="Output height.")
@click.option("--frames", type=int, default=1, help="Number of frames.")
@pass_state
def render(state, output, top, width, height, frames):
    """Render output from the project via TouchDesigner."""
    proj = state.require_project()
    backend = get_backend()

    if not backend.is_available():
        # Try live connection before falling back to script output
        conn = TDConnection()
        if conn.ping():
            state.fmt.info("TD batch not available — using live connection for render...")
            output_abs = os.path.abspath(output)
            script = TDConnection.generate_render_script(
                output_path=output_abs, top_path=top, width=width, height=height,
            )
            result = conn.send_script(script, timeout=30)
            if result["success"]:
                state.fmt.success(f"Rendered: {output_abs}", result)
            else:
                state.fmt.error(f"Render failed: {result['message']}")
                sys.exit(1)
            return
        state.fmt.warning(
            "TouchDesigner not found. Generating render script instead."
        )
        script = proj.generate_td_script()
        click.echo(script)
        return

    result = backend.render_toe(
        toe_file="",
        output_path=output,
        top_path=top,
        width=width,
        height=height,
        frames=frames,
    )
    if result.get("success"):
        state.fmt.success(f"Rendered: {output}", result.get("data"))
    else:
        state.fmt.error(f"Render failed: {result.get('error')}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# export command
# ---------------------------------------------------------------------------

@cli.group()
@pass_state
def export(state):
    """Export project in various formats."""
    pass


@export.command("script")
@click.option("-o", "--output", type=click.Path(), help="Output file path.")
@pass_state
def export_script(state, output):
    """Export as a TouchDesigner Python script."""
    proj = state.require_project()
    script = proj.generate_td_script()
    if output:
        with open(output, "w") as f:
            f.write(script)
        state.fmt.success(f"Exported TD script: {output} ({len(script)} bytes)")
    else:
        click.echo(script)


@export.command("json")
@click.option("-o", "--output", type=click.Path(), help="Output file path.")
@pass_state
def export_json(state, output):
    """Export project as JSON."""
    proj = state.require_project()
    data = proj.to_json()
    if output:
        with open(output, "w") as f:
            f.write(data)
        state.fmt.success(f"Exported JSON: {output} ({len(data)} bytes)")
    else:
        click.echo(data)


# ---------------------------------------------------------------------------
# live commands  (real-time connection to running TD)
# ---------------------------------------------------------------------------

@cli.group()
@click.option("--host", default=DEFAULT_HOST, help="TD receiver host.")
@click.option("--port", type=int, default=DEFAULT_PORT, help="TD receiver port.")
@click.pass_context
def live(ctx, host, port):
    """Real-time connection to a running TouchDesigner instance."""
    ctx.ensure_object(CLIState)
    ctx.obj._td_conn = TDConnection(host=host, port=port)


def _get_conn(state) -> TDConnection:
    """Retrieve the TDConnection from CLI state."""
    return getattr(state, "_td_conn", TDConnection())


@live.command("bootstrap")
@click.option("--port", type=int, default=DEFAULT_PORT, help="Port for TD listener.")
@click.option("--copy", "copy_clip", is_flag=True, help="Copy script to clipboard.")
@click.option("-o", "--output", type=click.Path(), help="Write script to file.")
@pass_state
def live_bootstrap(state, port, copy_clip, output):
    """Print the one-time receiver script to paste into TouchDesigner.

    Run this once inside TD's textport (or a Text DAT) to start the
    TCP listener.  After that, the CLI can push code in real time.
    """
    script = TDConnection.get_bootstrap_script(port)

    if output:
        with open(output, "w") as f:
            f.write(script)
        state.fmt.success(f"Bootstrap script written to {output}")
    elif copy_clip:
        try:
            import subprocess
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(script.encode())
            state.fmt.success("Bootstrap script copied to clipboard. Paste it into TD's textport.")
        except FileNotFoundError:
            click.echo(script)
            state.fmt.warning("pbcopy not found — script printed above. Copy it manually.")
    else:
        click.echo(script)
        state.fmt.info(
            f"Paste the script above into TD's textport to start the receiver on port {port}."
        )


@live.command("ping")
@pass_state
def live_ping(state):
    """Check if the TouchDesigner receiver is reachable."""
    conn = _get_conn(state)
    if conn.ping():
        state.fmt.success(f"TD receiver is live at {conn.host}:{conn.port}")
    else:
        state.fmt.error(
            f"Cannot reach TD receiver at {conn.host}:{conn.port}. "
            "Run 'live bootstrap' and paste the script into TD first."
        )
        sys.exit(1)


@live.command("push")
@click.option("--timeout", type=float, default=10, help="Send timeout in seconds.")
@click.option("--clean", is_flag=True, help="Clear existing nodes before pushing.")
@pass_state
def live_push(state, timeout, clean):
    """Push the current project to TouchDesigner in real time."""
    import time as _time
    proj = state.require_project()
    conn = _get_conn(state)

    # Clear error log before push so we only see new errors
    TDConnection.clear_errors()

    if clean:
        state.fmt.info("Clearing existing nodes in /project1...")
        conn.send_script(
            "for c in op('/project1').children:\n    c.destroy()\n"
            "print('[td-cli] Cleared /project1')",
            timeout=timeout,
        )
        _time.sleep(0.2)

    state.fmt.info(f"Pushing project '{proj.name}' to TD at {conn.host}:{conn.port}...")
    push_time = _time.time()
    result = conn.push_project(proj, timeout=timeout)
    if not result["success"]:
        state.fmt.error(f"Push failed: {result['message']}")
        sys.exit(1)

    state.fmt.success("Project pushed to TouchDesigner", result)

    # Wait for TD to execute and check for errors
    _time.sleep(0.5)
    errors = TDConnection.read_errors(since=push_time)
    if errors:
        state.fmt.warning(f"TD reported {len(errors)} error(s) during execution:")
        for err in errors:
            click.echo(click.style("  " + err.replace("\n", "\n  "), fg="red"))
    else:
        state.fmt.info("No errors from TD.")


@live.command("query")
@click.argument("op_type")
@pass_state
def live_query(state, op_type):
    """Query a running TD for valid parameters on an operator type.

    Example: td-cli live query noiseTOP
    """
    conn = _get_conn(state)
    state.fmt.info(f"Querying TD for params on '{op_type}'...")
    result = conn.query_params(op_type)
    if result["success"]:
        state.fmt.success(f"Parameters for {op_type}", result)
    else:
        state.fmt.error(f"Query failed: {result['message']}")


@live.command("errors")
@click.option("--clear", is_flag=True, help="Clear the error log after reading.")
@pass_state
def live_errors(state, clear):
    """Read TD execution errors from the shared error log."""
    errors = TDConnection.read_errors(clear=clear)
    if errors:
        state.fmt.warning(f"{len(errors)} error(s) from TouchDesigner:")
        for i, err in enumerate(errors, 1):
            click.echo(click.style(f"  [{i}] ", fg="yellow") + err.replace("\n", "\n      "))
        if clear:
            state.fmt.info("Error log cleared.")
    else:
        state.fmt.success("No errors in log.")
        if clear:
            state.fmt.info("Error log cleared.")


@live.command("send")
@click.argument("script_file", type=click.Path(exists=True))
@click.option("--timeout", type=float, default=10, help="Send timeout in seconds.")
@pass_state
def live_send(state, script_file, timeout):
    """Send an arbitrary Python script file to TouchDesigner."""
    conn = _get_conn(state)
    with open(script_file) as f:
        script = f.read()
    state.fmt.info(f"Sending {script_file} to TD at {conn.host}:{conn.port}...")
    result = conn.send_script(script, timeout=timeout)
    if result["success"]:
        state.fmt.success("Script executed in TouchDesigner", result)
    else:
        state.fmt.error(f"Send failed: {result['message']}")
        sys.exit(1)


@live.command("render")
@click.argument("output", default="output.png")
@click.option("--top", default="/project1/out1", help="TOP operator path to render.")
@click.option("--width", type=int, default=1920, help="Output width.")
@click.option("--height", type=int, default=1080, help="Output height.")
@click.option("--timeout", type=float, default=30, help="Render timeout in seconds.")
@pass_state
def live_render(state, output, top, width, height, timeout):
    """Render a frame from a running TouchDesigner instance via the live connection."""
    conn = _get_conn(state)
    output_abs = os.path.abspath(output)
    script = TDConnection.generate_render_script(
        output_path=output_abs, top_path=top, width=width, height=height,
    )
    state.fmt.info(f"Sending render command to TD at {conn.host}:{conn.port}...")
    result = conn.send_script(script, timeout=timeout)
    if result["success"]:
        state.fmt.success(f"Rendered: {output_abs}", result)
    else:
        state.fmt.error(f"Render failed: {result['message']}")
        sys.exit(1)


@live.command("status")
@pass_state
def live_status(state):
    """Show the live connection status."""
    conn = _get_conn(state)
    reachable = conn.ping()
    info = {
        "host": conn.host,
        "port": conn.port,
        "reachable": reachable,
    }
    if state.fmt.json_mode:
        state.fmt.data(info)
    else:
        label = click.style("CONNECTED", fg="green") if reachable else click.style("OFFLINE", fg="red")
        click.echo(f"  TD Receiver: {label} ({conn.host}:{conn.port})")


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

@cli.command()
@pass_state
def status(state):
    """Show TouchDesigner backend status."""
    backend = get_backend()
    conn = TDConnection()
    available = backend.is_available()
    live_ok = conn.ping()
    info = {
        "touchdesigner_available": available,
        "td_path": backend.td_path,
        "batch_path": backend.batch_path,
        "version": backend.get_version() if available else None,
        "live_connection": live_ok,
        "live_host": conn.host,
        "live_port": conn.port,
    }
    state.fmt.data(info)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    cli()


if __name__ == "__main__":
    main()
