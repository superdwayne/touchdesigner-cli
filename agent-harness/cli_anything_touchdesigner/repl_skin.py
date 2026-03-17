"""Unified REPL interface for cli-anything-touchdesigner.

Provides a branded, interactive shell with command history, styled prompts,
progress indicators, and standardized formatting — consistent with the
CLI-Anything ecosystem's ReplSkin pattern.
"""

import cmd
import os
import readline
import shlex
import sys
from typing import Optional

import click

from . import __version__
from .project import ProjectManager, TDProject
from .operators import find_type, get_families, get_types, suggest_operators
from .network import NetworkBuilder, TEMPLATES
from .connection import TDConnection, DEFAULT_PORT
from .formatter import Formatter


BANNER = f"""\
╔══════════════════════════════════════════════════╗
║  cli-anything-touchdesigner v{__version__:<18s} ║
║  TouchDesigner CLI for AI Agents                 ║
╚══════════════════════════════════════════════════╝
"""

HELP_TEXT = """\
Commands:
  project new <name>             Create a new project
  project open <path>            Open an existing project
  project save [path]            Save current project
  project info                   Show project info
  project list                   List open projects
  project switch <name>          Switch active project

  op add <family> <type> <name>  Add an operator
  op remove <path>               Remove an operator
  op list [--family <FAM>]       List operators
  op info <path>                 Show operator details
  op set <path> <param> <value>  Set parameter value
  op get <path> <param>          Get parameter value
  op flag <path> <flag> <bool>   Set operator flag
  op types [family]              List available operator types
  op suggest <description>       Get operator suggestions

  net connect <from> <to>        Connect two operators
  net disconnect <from> <to>     Disconnect operators
  net list [op_path]             List connections
  net template <name> [args]     Build from template
  net templates                  List available templates

  render <output> [options]      Render current project
  export script <output>         Export as TD Python script
  export json <output>           Export project as JSON

  live bootstrap [--port N]       Print TD receiver script (one-time setup)
  live ping                      Check if TD receiver is reachable
  live push                      Push current project to TD in real time
  live render [output] [options] Render a frame from running TD instance
  live send <script.py>          Send a script file to TD
  live status                    Show live connection status

  undo                           Undo last change
  redo                           Redo last undone change
  status                         Show backend status
  help                           Show this help
  exit / quit                    Exit REPL
"""


class TouchDesignerREPL(cmd.Cmd):
    """Interactive REPL for TouchDesigner CLI."""

    intro = click.style(BANNER, fg="magenta", bold=True)

    def __init__(self, json_mode: bool = False):
        super().__init__()
        self.manager = ProjectManager()
        self.fmt = Formatter(json_mode=json_mode)
        self._update_prompt()
        # History file
        self._history_file = os.path.expanduser("~/.td_cli_history")
        try:
            readline.read_history_file(self._history_file)
        except FileNotFoundError:
            pass
        readline.set_history_length(1000)

    def _update_prompt(self):
        proj = self.manager.active_project
        if proj:
            dirty = "*" if proj.is_dirty else ""
            self.prompt = click.style(
                f"td[{proj.name}]{dirty}> ", fg="magenta", bold=True
            )
        else:
            self.prompt = click.style("td> ", fg="magenta", bold=True)

    def postcmd(self, stop, line):
        self._update_prompt()
        return stop

    def postloop(self):
        try:
            readline.write_history_file(self._history_file)
        except OSError:
            pass

    def default(self, line):
        """Handle unknown commands."""
        self.fmt.error(f"Unknown command: {line}")
        self.fmt.info("Type 'help' for available commands.")

    def emptyline(self):
        pass

    # ------------------------------------------------------------------
    # Project commands
    # ------------------------------------------------------------------

    def do_project(self, arg):
        """Project management commands."""
        parts = shlex.split(arg) if arg else []
        if not parts:
            self.fmt.error("Usage: project <new|open|save|info|list|switch> [args]")
            return

        subcmd = parts[0]

        if subcmd == "new":
            if len(parts) < 2:
                self.fmt.error("Usage: project new <name> [--type <type>]")
                return
            name = parts[1]
            ptype = "standard"
            if "--type" in parts:
                idx = parts.index("--type")
                if idx + 1 < len(parts):
                    ptype = parts[idx + 1]
            proj = self.manager.new_project(name, ptype)
            self.fmt.success(f"Created project: {name}", proj.info())

        elif subcmd == "open":
            if len(parts) < 2:
                self.fmt.error("Usage: project open <path>")
                return
            try:
                proj = self.manager.open_project(parts[1])
                self.fmt.success(f"Opened project: {proj.name}", proj.info())
            except Exception as e:
                self.fmt.error(f"Failed to open project: {e}")

        elif subcmd == "save":
            path = parts[1] if len(parts) > 1 else None
            try:
                self.manager.save_project(path)
                self.fmt.success(f"Saved project" + (f" to {path}" if path else ""))
            except Exception as e:
                self.fmt.error(f"Failed to save: {e}")

        elif subcmd == "info":
            proj = self.manager.active_project
            if proj:
                self.fmt.project_info(proj.info())
            else:
                self.fmt.error("No active project")

        elif subcmd == "list":
            names = self.manager.list_projects()
            if names:
                for n in names:
                    marker = " ← active" if n == (self.manager._active or "") else ""
                    click.echo(f"  {n}{click.style(marker, fg='green')}")
            else:
                self.fmt.info("No open projects")

        elif subcmd == "switch":
            if len(parts) < 2:
                self.fmt.error("Usage: project switch <name>")
                return
            if self.manager.switch_project(parts[1]):
                self.fmt.success(f"Switched to: {parts[1]}")
            else:
                self.fmt.error(f"Project not found: {parts[1]}")

        elif subcmd == "close":
            name = parts[1] if len(parts) > 1 else None
            if self.manager.close_project(name):
                self.fmt.success("Closed project")
            else:
                self.fmt.error("No project to close")

        else:
            self.fmt.error(f"Unknown project command: {subcmd}")

    def do_op(self, arg):
        """Operator management commands."""
        parts = shlex.split(arg) if arg else []
        if not parts:
            self.fmt.error("Usage: op <add|remove|list|info|set|get|flag|types|suggest> [args]")
            return

        proj = self.manager.active_project
        if not proj and parts[0] not in ("types", "suggest"):
            self.fmt.error("No active project. Use 'project new <name>' first.")
            return

        subcmd = parts[0]

        if subcmd == "add":
            if len(parts) < 4:
                self.fmt.error("Usage: op add <family> <type> <name> [--parent <path>] [--param key=val ...]")
                return
            family, op_type, name = parts[1], parts[2], parts[3]
            parent = "/project1"
            params = {}

            i = 4
            while i < len(parts):
                if parts[i] == "--parent" and i + 1 < len(parts):
                    parent = parts[i + 1]
                    i += 2
                elif parts[i] == "--param" and i + 1 < len(parts):
                    kv = parts[i + 1]
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        try:
                            v = float(v) if "." in v else int(v)
                        except ValueError:
                            pass
                        params[k] = v
                    i += 2
                else:
                    i += 1

            # Resolve type
            type_info = find_type(family, op_type)
            if type_info:
                resolved_type = type_info["type"]
                # Merge defaults with provided params
                merged = dict(type_info["defaults"])
                merged.update(params)
                params = merged
            else:
                resolved_type = op_type

            try:
                op = proj.add_operator(name, family, resolved_type, parent, params=params)
                self.fmt.success(f"Added {family}: {name}")
                self.fmt.operator_summary(op)
            except ValueError as e:
                self.fmt.error(str(e))

        elif subcmd == "remove":
            if len(parts) < 2:
                self.fmt.error("Usage: op remove <path>")
                return
            if proj.remove_operator(parts[1]):
                self.fmt.success(f"Removed: {parts[1]}")
            else:
                self.fmt.error(f"Operator not found: {parts[1]}")

        elif subcmd == "list":
            family = None
            parent = None
            i = 1
            while i < len(parts):
                if parts[i] == "--family" and i + 1 < len(parts):
                    family = parts[i + 1]
                    i += 2
                elif parts[i] == "--parent" and i + 1 < len(parts):
                    parent = parts[i + 1]
                    i += 2
                else:
                    i += 1

            ops = proj.list_operators(family=family, parent=parent)
            if ops:
                headers = ["Name", "Family", "Type", "Path"]
                rows = [[o["name"], o["family"], o["type"], o["path"]] for o in ops]
                self.fmt.table(headers, rows, title="Operators")
            else:
                self.fmt.info("No operators")

        elif subcmd == "info":
            if len(parts) < 2:
                self.fmt.error("Usage: op info <path>")
                return
            op = proj.get_operator(parts[1])
            if op:
                self.fmt.operator_summary(op)
            else:
                self.fmt.error(f"Operator not found: {parts[1]}")

        elif subcmd == "set":
            if len(parts) < 4:
                self.fmt.error("Usage: op set <path> <param> <value>")
                return
            path, param, value = parts[1], parts[2], parts[3]
            try:
                value = float(value) if "." in value else int(value)
            except ValueError:
                pass
            if proj.set_parameter(path, param, value):
                self.fmt.success(f"Set {param}={value} on {path}")
            else:
                self.fmt.error(f"Operator not found: {path}")

        elif subcmd == "get":
            if len(parts) < 3:
                self.fmt.error("Usage: op get <path> <param>")
                return
            val = proj.get_parameter(parts[1], parts[2])
            if val is not None:
                self.fmt.data({parts[2]: val})
            else:
                self.fmt.error(f"Parameter not found: {parts[2]}")

        elif subcmd == "flag":
            if len(parts) < 4:
                self.fmt.error("Usage: op flag <path> <flag> <true|false>")
                return
            value = parts[3].lower() in ("true", "1", "yes", "on")
            if proj.set_flag(parts[1], parts[2], value):
                self.fmt.success(f"Set {parts[2]}={value} on {parts[1]}")
            else:
                self.fmt.error(f"Failed to set flag")

        elif subcmd == "types":
            family = parts[1] if len(parts) > 1 else None
            if family:
                types = get_types(family)
                if types:
                    headers = ["Type", "Label"]
                    rows = [[t["type"], t["label"]] for t in types]
                    self.fmt.table(headers, rows, title=f"{family.upper()} Operators")
                else:
                    self.fmt.error(f"Unknown family: {family}")
            else:
                for fam in get_families():
                    types = get_types(fam)
                    click.echo(click.style(f"  {fam}", bold=True) + f" ({len(types)} types)")

        elif subcmd == "suggest":
            if len(parts) < 2:
                self.fmt.error("Usage: op suggest <description>")
                return
            desc = " ".join(parts[1:])
            suggestions = suggest_operators(desc)
            headers = ["Family", "Type", "Reason"]
            rows = [[s["family"], s["type"], s["reason"]] for s in suggestions]
            self.fmt.table(headers, rows, title="Suggested Operators")

        else:
            self.fmt.error(f"Unknown op command: {subcmd}")

    def do_net(self, arg):
        """Network / connection commands."""
        parts = shlex.split(arg) if arg else []
        if not parts:
            self.fmt.error("Usage: net <connect|disconnect|list|template|templates> [args]")
            return

        proj = self.manager.active_project
        if not proj and parts[0] != "templates":
            self.fmt.error("No active project.")
            return

        subcmd = parts[0]

        if subcmd == "connect":
            if len(parts) < 3:
                self.fmt.error("Usage: net connect <from_path> <to_path> [--from-index N] [--to-index N]")
                return
            from_idx, to_idx = 0, 0
            i = 3
            while i < len(parts):
                if parts[i] == "--from-index" and i + 1 < len(parts):
                    from_idx = int(parts[i + 1])
                    i += 2
                elif parts[i] == "--to-index" and i + 1 < len(parts):
                    to_idx = int(parts[i + 1])
                    i += 2
                else:
                    i += 1
            try:
                conn = proj.connect(parts[1], parts[2], from_idx, to_idx)
                self.fmt.success(f"Connected: {parts[1]} → {parts[2]}")
            except ValueError as e:
                self.fmt.error(str(e))

        elif subcmd == "disconnect":
            if len(parts) < 3:
                self.fmt.error("Usage: net disconnect <from_path> <to_path>")
                return
            if proj.disconnect(parts[1], parts[2]):
                self.fmt.success(f"Disconnected: {parts[1]} ↛ {parts[2]}")
            else:
                self.fmt.error("Connection not found")

        elif subcmd == "list":
            op_path = parts[1] if len(parts) > 1 else None
            conns = proj.list_connections(op_path)
            if conns:
                headers = ["From", "To", "Out Idx", "In Idx"]
                rows = [
                    [c["from"], c["to"], str(c["from_index"]), str(c["to_index"])]
                    for c in conns
                ]
                self.fmt.table(headers, rows, title="Connections")
            else:
                self.fmt.info("No connections")

        elif subcmd == "template":
            if len(parts) < 2:
                self.fmt.error("Usage: net template <name> [--arg val ...]")
                return
            template_name = parts[1]
            builder = NetworkBuilder(proj)
            kwargs = {}

            # Parse template-specific args
            i = 2
            while i < len(parts):
                if parts[i].startswith("--") and i + 1 < len(parts):
                    key = parts[i][2:].replace("-", "_")
                    val = parts[i + 1]
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                    kwargs[key] = val
                    i += 2
                else:
                    i += 1

            template_map = {
                "audio-reactive": builder.build_audio_reactive,
                "feedback-loop": builder.build_feedback_loop,
                "3d-scene": builder.build_3d_scene,
                "particle-system": builder.build_particle_system,
                "instancing": builder.build_instancing,
                "glsl-shader": builder.build_glsl_shader,
                "osc-receiver": builder.build_osc_receiver,
                "video-mixer": builder.build_video_mixer,
                "disintegration": builder.build_disintegration,
            }

            func = template_map.get(template_name)
            if func:
                try:
                    created = func(**kwargs)
                    self.fmt.success(
                        f"Built template '{template_name}' ({len(created)} operators)"
                    )
                except TypeError as e:
                    self.fmt.error(f"Invalid args for template: {e}")
            else:
                self.fmt.error(
                    f"Unknown template: {template_name}. Use 'net templates' to list."
                )

        elif subcmd == "templates":
            headers = ["Template", "Description"]
            rows = [[k, v] for k, v in TEMPLATES.items()]
            self.fmt.table(headers, rows, title="Network Templates")

        else:
            self.fmt.error(f"Unknown net command: {subcmd}")

    def do_render(self, arg):
        """Render the current project."""
        parts = shlex.split(arg) if arg else []
        proj = self.manager.active_project
        if not proj:
            self.fmt.error("No active project.")
            return

        from .backend import get_backend

        backend = get_backend()
        if not backend.is_available():
            # Try live connection before falling back to script output
            conn = TDConnection()
            if conn.ping():
                import os
                self.fmt.info("TD batch not available — using live connection for render...")
                output = parts[0] if parts else "output.png"
                output_abs = os.path.abspath(output)
                script = TDConnection.generate_render_script(
                    output_path=output_abs, top_path="/project1/out1",
                )
                result = conn.send_script(script, timeout=30)
                if result["success"]:
                    self.fmt.success(f"Rendered: {output_abs}", result)
                else:
                    self.fmt.error(f"Render failed: {result['message']}")
                return
            self.fmt.warning(
                "TouchDesigner not found. Generating render script instead."
            )
            script = proj.generate_td_script()
            self.fmt.info("Generated TD Python script:")
            click.echo(script)
            return

        output = parts[0] if parts else "output.png"
        self.fmt.info(f"Rendering to {output}...")
        result = backend.render_toe(
            toe_file="",
            output_path=output,
        )
        if result.get("success"):
            self.fmt.success(f"Rendered: {output}", result.get("data"))
        else:
            self.fmt.error(f"Render failed: {result.get('error')}")

    def do_export(self, arg):
        """Export project in various formats."""
        parts = shlex.split(arg) if arg else []
        proj = self.manager.active_project
        if not proj:
            self.fmt.error("No active project.")
            return

        if not parts:
            self.fmt.error("Usage: export <script|json> <output_path>")
            return

        subcmd = parts[0]
        output = parts[1] if len(parts) > 1 else None

        if subcmd == "script":
            script = proj.generate_td_script()
            if output:
                with open(output, "w") as f:
                    f.write(script)
                self.fmt.success(f"Exported TD script: {output}")
            else:
                click.echo(script)

        elif subcmd == "json":
            data = proj.to_json()
            if output:
                with open(output, "w") as f:
                    f.write(data)
                self.fmt.success(f"Exported JSON: {output}")
            else:
                click.echo(data)

        else:
            self.fmt.error(f"Unknown export format: {subcmd}")

    def do_live(self, arg):
        """Real-time connection to a running TouchDesigner instance."""
        parts = shlex.split(arg) if arg else []
        if not parts:
            self.fmt.error(
                "Usage: live <bootstrap|ping|push|render|send|status> [args]"
            )
            return

        subcmd = parts[0]
        # Parse --host / --port from trailing args
        host, port = "127.0.0.1", DEFAULT_PORT
        i = 1
        while i < len(parts):
            if parts[i] == "--host" and i + 1 < len(parts):
                host = parts[i + 1]
                i += 2
            elif parts[i] == "--port" and i + 1 < len(parts):
                port = int(parts[i + 1])
                i += 2
            else:
                i += 1

        conn = TDConnection(host=host, port=port)

        if subcmd == "bootstrap":
            output = None
            copy_clip = False
            j = 1
            while j < len(parts):
                if parts[j] == "--copy":
                    copy_clip = True
                    j += 1
                elif parts[j] == "-o" and j + 1 < len(parts):
                    output = parts[j + 1]
                    j += 2
                else:
                    j += 1
            script = TDConnection.get_bootstrap_script(port)
            if output:
                with open(output, "w") as f:
                    f.write(script)
                self.fmt.success(f"Bootstrap script written to {output}")
            elif copy_clip:
                try:
                    import subprocess
                    proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    proc.communicate(script.encode())
                    self.fmt.success(
                        "Bootstrap script copied to clipboard. "
                        "Paste it into TD's textport."
                    )
                except FileNotFoundError:
                    click.echo(script)
                    self.fmt.warning(
                        "pbcopy not found — script printed above."
                    )
            else:
                click.echo(script)
                self.fmt.info(
                    f"Paste the script above into TD's textport "
                    f"to start the receiver on port {port}."
                )

        elif subcmd == "ping":
            if conn.ping():
                self.fmt.success(
                    f"TD receiver is live at {conn.host}:{conn.port}"
                )
            else:
                self.fmt.error(
                    f"Cannot reach TD at {conn.host}:{conn.port}. "
                    "Run 'live bootstrap' first."
                )

        elif subcmd == "push":
            proj = self.manager.active_project
            if not proj:
                self.fmt.error("No active project.")
                return
            self.fmt.info(
                f"Pushing '{proj.name}' to TD at {conn.host}:{conn.port}..."
            )
            result = conn.push_project(proj)
            if result["success"]:
                self.fmt.success("Project pushed to TouchDesigner")
            else:
                self.fmt.error(f"Push failed: {result['message']}")

        elif subcmd == "send":
            if len(parts) < 2:
                self.fmt.error("Usage: live send <script_file>")
                return
            script_file = parts[1]
            try:
                with open(script_file) as f:
                    script = f.read()
            except FileNotFoundError:
                self.fmt.error(f"File not found: {script_file}")
                return
            self.fmt.info(
                f"Sending {script_file} to TD at {conn.host}:{conn.port}..."
            )
            result = conn.send_script(script)
            if result["success"]:
                self.fmt.success("Script executed in TouchDesigner")
            else:
                self.fmt.error(f"Send failed: {result['message']}")

        elif subcmd == "render":
            import os
            output = "output.png"
            top_path = "/project1/out1"
            width, height = 1920, 1080
            timeout = 30.0
            j = 1
            while j < len(parts):
                if parts[j] == "--top" and j + 1 < len(parts):
                    top_path = parts[j + 1]
                    j += 2
                elif parts[j] == "--width" and j + 1 < len(parts):
                    width = int(parts[j + 1])
                    j += 2
                elif parts[j] == "--height" and j + 1 < len(parts):
                    height = int(parts[j + 1])
                    j += 2
                elif parts[j] == "--timeout" and j + 1 < len(parts):
                    timeout = float(parts[j + 1])
                    j += 2
                elif not parts[j].startswith("--") and parts[j] not in (host, str(port)):
                    output = parts[j]
                    j += 1
                else:
                    j += 1
            output_abs = os.path.abspath(output)
            script = TDConnection.generate_render_script(
                output_path=output_abs, top_path=top_path,
                width=width, height=height,
            )
            self.fmt.info(
                f"Sending render command to TD at {conn.host}:{conn.port}..."
            )
            result = conn.send_script(script, timeout=timeout)
            if result["success"]:
                self.fmt.success(f"Rendered: {output_abs}", result)
            else:
                self.fmt.error(f"Render failed: {result['message']}")

        elif subcmd == "status":
            reachable = conn.ping()
            if reachable:
                label = click.style("CONNECTED", fg="green")
            else:
                label = click.style("OFFLINE", fg="red")
            click.echo(f"  TD Receiver: {label} ({conn.host}:{conn.port})")

        else:
            self.fmt.error(f"Unknown live command: {subcmd}")

    def do_undo(self, arg):
        """Undo the last change."""
        proj = self.manager.active_project
        if proj and proj.undo():
            self.fmt.success("Undone")
        else:
            self.fmt.warning("Nothing to undo")

    def do_redo(self, arg):
        """Redo the last undone change."""
        proj = self.manager.active_project
        if proj and proj.redo():
            self.fmt.success("Redone")
        else:
            self.fmt.warning("Nothing to redo")

    def do_status(self, arg):
        """Show backend status."""
        from .backend import get_backend

        backend = get_backend()
        available = backend.is_available()
        conn = TDConnection()
        live_ok = conn.ping()
        self.fmt.data({
            "touchdesigner_available": available,
            "td_path": backend.td_path,
            "batch_path": backend.batch_path,
            "version": backend.get_version() if available else None,
            "live_connection": live_ok,
            "live_endpoint": f"{conn.host}:{conn.port}",
            "active_project": self.manager._active,
            "open_projects": self.manager.list_projects(),
        })

    def do_help(self, arg):
        """Show help text."""
        click.echo(HELP_TEXT)

    def do_exit(self, arg):
        """Exit the REPL."""
        click.echo("Goodbye! 👋")
        return True

    def do_quit(self, arg):
        """Exit the REPL."""
        return self.do_exit(arg)

    do_EOF = do_exit


def start_repl(json_mode: bool = False):
    """Launch the interactive REPL."""
    repl = TouchDesignerREPL(json_mode=json_mode)
    try:
        repl.cmdloop()
    except KeyboardInterrupt:
        click.echo("\nGoodbye! 👋")
