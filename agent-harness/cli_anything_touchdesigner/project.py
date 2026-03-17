"""Project/session management for TouchDesigner .toe files.

Manages project state as JSON, which can be rendered to .toe files
via the TouchDesigner backend, or manipulated independently for
agent-driven workflows.
"""

import copy
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class TDProject:
    """Represents a TouchDesigner project with operators, connections, and state."""

    def __init__(self, name: str = "untitled", project_type: str = "standard"):
        self.name = name
        self.project_type = project_type
        self.created_at = time.time()
        self.modified_at = time.time()
        self.operators: Dict[str, dict] = {}
        self.connections: List[dict] = []
        self.parameters: Dict[str, dict] = {}
        self.metadata: Dict[str, Any] = {
            "fps": 60,
            "resolution": [1920, 1080],
            "cook_rate": 60,
        }
        self._undo_stack: List[dict] = []
        self._redo_stack: List[dict] = []
        self._dirty = False

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def _mark_dirty(self):
        self._dirty = True
        self.modified_at = time.time()

    def _save_undo_state(self):
        """Snapshot current state for undo."""
        state = {
            "operators": copy.deepcopy(self.operators),
            "connections": copy.deepcopy(self.connections),
            "parameters": copy.deepcopy(self.parameters),
            "metadata": copy.deepcopy(self.metadata),
        }
        self._undo_stack.append(state)
        self._redo_stack.clear()
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        """Undo the last change."""
        if not self._undo_stack:
            return False
        current = {
            "operators": copy.deepcopy(self.operators),
            "connections": copy.deepcopy(self.connections),
            "parameters": copy.deepcopy(self.parameters),
            "metadata": copy.deepcopy(self.metadata),
        }
        self._redo_stack.append(current)
        state = self._undo_stack.pop()
        self.operators = state["operators"]
        self.connections = state["connections"]
        self.parameters = state["parameters"]
        self.metadata = state["metadata"]
        self._mark_dirty()
        return True

    def redo(self) -> bool:
        """Redo the last undone change."""
        if not self._redo_stack:
            return False
        current = {
            "operators": copy.deepcopy(self.operators),
            "connections": copy.deepcopy(self.connections),
            "parameters": copy.deepcopy(self.parameters),
            "metadata": copy.deepcopy(self.metadata),
        }
        self._undo_stack.append(current)
        state = self._redo_stack.pop()
        self.operators = state["operators"]
        self.connections = state["connections"]
        self.parameters = state["parameters"]
        self.metadata = state["metadata"]
        self._mark_dirty()
        return True

    def add_operator(
        self,
        name: str,
        family: str,
        op_type: str,
        parent: str = "/project1",
        position: Optional[List[int]] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Add an operator to the project.

        Args:
            name: Operator name (e.g., 'noise1').
            family: Operator family (TOP, CHOP, SOP, DAT, COMP, MAT, POP).
            op_type: Specific operator type (e.g., 'noiseTOP', 'audiofileinCHOP').
            parent: Parent component path.
            position: [x, y] position in the network editor.
            params: Initial parameter values.

        Returns:
            dict describing the created operator.
        """
        family = family.upper()
        valid_families = {"TOP", "CHOP", "SOP", "DAT", "COMP", "MAT", "POP"}
        if family not in valid_families:
            raise ValueError(
                f"Invalid operator family '{family}'. Must be one of: {valid_families}"
            )

        self._save_undo_state()

        path = f"{parent}/{name}"
        operator = {
            "name": name,
            "path": path,
            "family": family,
            "type": op_type,
            "parent": parent,
            "position": position or [0, 0],
            "parameters": params or {},
            "flags": {
                "bypass": False,
                "lock": False,
                "viewer": False,
                "render": family == "TOP",
                "display": False,
            },
            "created_at": time.time(),
        }
        self.operators[path] = operator
        self._mark_dirty()
        return operator

    def remove_operator(self, path: str) -> bool:
        """Remove an operator and its connections."""
        if path not in self.operators:
            return False
        self._save_undo_state()
        del self.operators[path]
        self.connections = [
            c
            for c in self.connections
            if c["from"] != path and c["to"] != path
        ]
        self._mark_dirty()
        return True

    def get_operator(self, path: str) -> Optional[dict]:
        """Get operator info by path."""
        return self.operators.get(path)

    def list_operators(
        self,
        family: Optional[str] = None,
        parent: Optional[str] = None,
    ) -> List[dict]:
        """List operators, optionally filtered by family or parent."""
        ops = list(self.operators.values())
        if family:
            family = family.upper()
            ops = [o for o in ops if o["family"] == family]
        if parent:
            ops = [o for o in ops if o["parent"] == parent]
        return ops

    def set_parameter(self, op_path: str, param_name: str, value: Any) -> bool:
        """Set a parameter value on an operator."""
        if op_path not in self.operators:
            return False
        self._save_undo_state()
        self.operators[op_path]["parameters"][param_name] = value
        self._mark_dirty()
        return True

    def get_parameter(self, op_path: str, param_name: str) -> Any:
        """Get a parameter value from an operator."""
        op = self.operators.get(op_path)
        if op is None:
            return None
        return op["parameters"].get(param_name)

    def connect(
        self,
        from_path: str,
        to_path: str,
        from_index: int = 0,
        to_index: int = 0,
    ) -> dict:
        """Connect two operators.

        Args:
            from_path: Source operator path.
            to_path: Destination operator path.
            from_index: Output index on source.
            to_index: Input index on destination.

        Returns:
            dict describing the connection.
        """
        if from_path not in self.operators:
            raise ValueError(f"Source operator not found: {from_path}")
        if to_path not in self.operators:
            raise ValueError(f"Destination operator not found: {to_path}")

        # Validate same family (TD only connects same family)
        from_family = self.operators[from_path]["family"]
        to_family = self.operators[to_path]["family"]
        if from_family != to_family:
            raise ValueError(
                f"Cannot connect {from_family} to {to_family}. "
                f"Operators must be in the same family."
            )

        self._save_undo_state()
        conn = {
            "from": from_path,
            "to": to_path,
            "from_index": from_index,
            "to_index": to_index,
        }
        self.connections.append(conn)
        self._mark_dirty()
        return conn

    def disconnect(self, from_path: str, to_path: str) -> bool:
        """Remove connection between two operators."""
        self._save_undo_state()
        before = len(self.connections)
        self.connections = [
            c
            for c in self.connections
            if not (c["from"] == from_path and c["to"] == to_path)
        ]
        if len(self.connections) < before:
            self._mark_dirty()
            return True
        return False

    def list_connections(
        self, op_path: Optional[str] = None
    ) -> List[dict]:
        """List connections, optionally filtered by operator path."""
        if op_path is None:
            return list(self.connections)
        return [
            c
            for c in self.connections
            if c["from"] == op_path or c["to"] == op_path
        ]

    def set_flag(self, op_path: str, flag: str, value: bool) -> bool:
        """Set an operator flag (bypass, lock, viewer, render, display)."""
        if op_path not in self.operators:
            return False
        if flag not in self.operators[op_path]["flags"]:
            return False
        self._save_undo_state()
        self.operators[op_path]["flags"][flag] = value
        self._mark_dirty()
        return True

    def to_dict(self) -> dict:
        """Serialize project to dict."""
        return {
            "name": self.name,
            "project_type": self.project_type,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "metadata": self.metadata,
            "operators": self.operators,
            "connections": self.connections,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize project to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: str):
        """Save project state to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())
        self._dirty = False

    @classmethod
    def load(cls, path: str) -> "TDProject":
        """Load project state from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        proj = cls(name=data["name"], project_type=data.get("project_type", "standard"))
        proj.created_at = data.get("created_at", time.time())
        proj.modified_at = data.get("modified_at", time.time())
        proj.metadata = data.get("metadata", {})
        proj.operators = data.get("operators", {})
        proj.connections = data.get("connections", [])
        return proj

    def info(self) -> dict:
        """Return summary information about the project."""
        family_counts = {}
        for op in self.operators.values():
            fam = op["family"]
            family_counts[fam] = family_counts.get(fam, 0) + 1

        return {
            "name": self.name,
            "type": self.project_type,
            "operators": len(self.operators),
            "connections": len(self.connections),
            "families": family_counts,
            "resolution": self.metadata.get("resolution"),
            "fps": self.metadata.get("fps"),
            "modified": self.is_dirty,
        }

    def generate_td_script(self) -> str:
        """Generate a TouchDesigner Python script that recreates this project.

        This script is meant to run inside TouchDesigner's Python environment.
        """
        lines = [
            "# Auto-generated by cli-anything-touchdesigner",
            f"# Project: {self.name}",
            "import td",
            "",
            f"project.cookRate = {self.metadata.get('cook_rate', 60)}",
            "",
        ]

        # Create operators
        for path, op in self.operators.items():
            parent = op["parent"]
            name = op["name"]
            op_type = op["type"]
            lines.append(f"# Create {op['family']}: {name}")
            lines.append(f"_op = op('{parent}').create('{op_type}', '{name}')")

            # Set position
            pos = op.get("position", [0, 0])
            lines.append(f"_op.nodeX = {pos[0]}")
            lines.append(f"_op.nodeY = {pos[1]}")

            # Set parameters (wrapped in try/except for resilience)
            for pname, pvalue in op.get("parameters", {}).items():
                if isinstance(pvalue, str):
                    lines.append(f"try:\n    _op.par.{pname} = {pvalue!r}\nexcept: pass")
                else:
                    lines.append(f"try:\n    _op.par.{pname} = {pvalue}\nexcept: pass")

            # Set flags
            flags = op.get("flags", {})
            if flags.get("bypass"):
                lines.append("_op.bypass = True")
            if flags.get("lock"):
                lines.append("_op.lock = True")
            if flags.get("viewer"):
                lines.append("_op.viewer = True")
            if flags.get("display"):
                lines.append("_op.display = True")
            if flags.get("render"):
                lines.append("_op.render = True")

            lines.append("")

        # Create connections
        if self.connections:
            lines.append("# Connections")
            for conn in self.connections:
                lines.append(
                    f"op('{conn['to']}').inputConnectors[{conn['to_index']}]"
                    f".connect(op('{conn['from']}').outputConnectors[{conn['from_index']}])"
                )
            lines.append("")

        # Save
        lines.append(f"project.save('{{output_path}}')")
        return "\n".join(lines)


class ProjectManager:
    """Manages multiple project sessions with undo/redo."""

    def __init__(self):
        self._projects: Dict[str, TDProject] = {}
        self._active: Optional[str] = None

    @property
    def active_project(self) -> Optional[TDProject]:
        if self._active and self._active in self._projects:
            return self._projects[self._active]
        return None

    def new_project(
        self, name: str, project_type: str = "standard"
    ) -> TDProject:
        """Create a new project and set it as active."""
        proj = TDProject(name=name, project_type=project_type)
        self._projects[name] = proj
        self._active = name
        return proj

    def open_project(self, path: str) -> TDProject:
        """Load a project from disk."""
        proj = TDProject.load(path)
        self._projects[proj.name] = proj
        self._active = proj.name
        return proj

    def save_project(self, path: Optional[str] = None, name: Optional[str] = None):
        """Save a project to disk."""
        proj = self._projects.get(name or self._active or "")
        if proj is None:
            raise ValueError("No project to save")
        if path is None:
            path = f"{proj.name}.json"
        proj.save(path)

    def switch_project(self, name: str) -> bool:
        if name in self._projects:
            self._active = name
            return True
        return False

    def list_projects(self) -> List[str]:
        return list(self._projects.keys())

    def close_project(self, name: Optional[str] = None) -> bool:
        target = name or self._active
        if target and target in self._projects:
            del self._projects[target]
            if self._active == target:
                remaining = list(self._projects.keys())
                self._active = remaining[0] if remaining else None
            return True
        return False
