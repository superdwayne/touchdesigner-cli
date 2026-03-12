"""Output formatting utilities for human-readable and JSON output.

Provides consistent formatting across all CLI commands with support
for --json flag for machine consumption.
"""

import json
import sys
from typing import Any, Dict, List, Optional

import click


class Formatter:
    """Handles output formatting for both human and machine consumption."""

    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode

    def success(self, message: str, data: Optional[dict] = None):
        """Print a success message."""
        if self.json_mode:
            output = {"status": "success", "message": message}
            if data:
                output["data"] = data
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(click.style("✓ ", fg="green", bold=True) + message)

    def error(self, message: str, data: Optional[dict] = None):
        """Print an error message."""
        if self.json_mode:
            output = {"status": "error", "message": message}
            if data:
                output["data"] = data
            click.echo(json.dumps(output, indent=2), err=True)
        else:
            click.echo(click.style("✗ ", fg="red", bold=True) + message, err=True)

    def warning(self, message: str):
        """Print a warning message."""
        if self.json_mode:
            click.echo(json.dumps({"status": "warning", "message": message}))
        else:
            click.echo(click.style("⚠ ", fg="yellow", bold=True) + message)

    def info(self, message: str):
        """Print an info message."""
        if self.json_mode:
            pass  # Skip info in JSON mode
        else:
            click.echo(click.style("ℹ ", fg="blue") + message)

    def data(self, obj: Any):
        """Print structured data."""
        if self.json_mode:
            click.echo(json.dumps(obj, indent=2, default=str))
        else:
            if isinstance(obj, dict):
                self._print_dict(obj)
            elif isinstance(obj, list):
                self._print_list(obj)
            else:
                click.echo(str(obj))

    def table(self, headers: List[str], rows: List[List[str]], title: Optional[str] = None):
        """Print a formatted table."""
        if self.json_mode:
            result = []
            for row in rows:
                result.append(dict(zip(headers, row)))
            click.echo(json.dumps(result, indent=2))
            return

        if title:
            click.echo()
            click.echo(click.style(title, bold=True))
            click.echo(click.style("─" * len(title), dim=True))

        if not rows:
            click.echo("  (empty)")
            return

        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        # Header
        header_line = "  ".join(
            click.style(h.ljust(col_widths[i]), bold=True)
            for i, h in enumerate(headers)
        )
        click.echo(f"  {header_line}")
        separator = "  ".join("─" * w for w in col_widths)
        click.echo(f"  {click.style(separator, dim=True)}")

        # Rows
        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                width = col_widths[i] if i < len(col_widths) else 20
                cells.append(str(cell).ljust(width))
            click.echo(f"  {'  '.join(cells)}")

    def operator_summary(self, op: dict):
        """Print a formatted operator summary."""
        if self.json_mode:
            click.echo(json.dumps(op, indent=2))
            return

        family_colors = {
            "TOP": "magenta",
            "CHOP": "green",
            "SOP": "blue",
            "DAT": "cyan",
            "COMP": "white",
            "MAT": "yellow",
            "POP": "bright_magenta",
        }
        family = op.get("family", "")
        color = family_colors.get(family, "white")

        click.echo(
            click.style(f"  [{family}] ", fg=color, bold=True)
            + click.style(op.get("name", ""), bold=True)
            + click.style(f" ({op.get('type', '')})", dim=True)
        )
        click.echo(f"    Path: {op.get('path', '')}")
        params = op.get("parameters", {})
        if params:
            param_strs = [f"{k}={v}" for k, v in list(params.items())[:5]]
            click.echo(f"    Params: {', '.join(param_strs)}")

    def project_info(self, info: dict):
        """Print formatted project information."""
        if self.json_mode:
            click.echo(json.dumps(info, indent=2))
            return

        click.echo()
        click.echo(click.style(f"  Project: {info['name']}", bold=True))
        click.echo(f"  Type: {info.get('type', 'standard')}")
        click.echo(f"  Operators: {info.get('operators', 0)}")
        click.echo(f"  Connections: {info.get('connections', 0)}")
        res = info.get("resolution")
        if res:
            click.echo(f"  Resolution: {res[0]}×{res[1]}")
        click.echo(f"  FPS: {info.get('fps', 60)}")
        families = info.get("families", {})
        if families:
            parts = [f"{k}: {v}" for k, v in sorted(families.items())]
            click.echo(f"  Families: {', '.join(parts)}")
        if info.get("modified"):
            click.echo(click.style("  (modified)", fg="yellow"))
        click.echo()

    def _print_dict(self, d: dict, indent: int = 2):
        """Pretty-print a dictionary."""
        for key, value in d.items():
            prefix = " " * indent
            if isinstance(value, dict):
                click.echo(f"{prefix}{click.style(str(key), bold=True)}:")
                self._print_dict(value, indent + 2)
            elif isinstance(value, list):
                click.echo(f"{prefix}{click.style(str(key), bold=True)}: [{len(value)} items]")
            else:
                click.echo(f"{prefix}{click.style(str(key), bold=True)}: {value}")

    def _print_list(self, items: list):
        """Pretty-print a list."""
        for i, item in enumerate(items):
            if isinstance(item, dict):
                click.echo(f"  [{i}]")
                self._print_dict(item, indent=4)
            else:
                click.echo(f"  [{i}] {item}")
