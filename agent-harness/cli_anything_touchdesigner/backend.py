"""Backend wrapper for TouchDesigner headless/batch execution.

Discovers TouchDesigner installation and executes Python scripts via
TouchDesigner's batch mode (TouchDesignerBatch or TouchDesigner -b).
"""

import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class TouchDesignerBackend:
    """Manages communication with TouchDesigner's batch/headless runtime."""

    # Common installation paths by platform
    _SEARCH_PATHS = {
        "Darwin": [
            "/Applications/Derivative/TouchDesigner.app/Contents/MacOS/TouchDesigner",
            "/Applications/TouchDesigner.app/Contents/MacOS/TouchDesigner",
        ],
        "Windows": [
            r"C:\Program Files\Derivative\TouchDesigner\bin\TouchDesigner.exe",
            r"C:\Program Files\Derivative\TouchDesigner099\bin\TouchDesigner099.exe",
        ],
        "Linux": [
            "/opt/Derivative/TouchDesigner/bin/TouchDesigner",
            "/usr/local/bin/TouchDesigner",
        ],
    }

    _BATCH_SEARCH_PATHS = {
        "Darwin": [
            "/Applications/Derivative/TouchDesigner.app/Contents/MacOS/TouchDesignerBatch",
        ],
        "Windows": [
            r"C:\Program Files\Derivative\TouchDesigner\bin\TouchDesignerBatch.exe",
            r"C:\Program Files\Derivative\TouchDesigner099\bin\TouchDesignerBatch099.exe",
        ],
        "Linux": [
            "/opt/Derivative/TouchDesigner/bin/TouchDesignerBatch",
        ],
    }

    def __init__(self, td_path: Optional[str] = None):
        self._td_path = td_path
        self._batch_path: Optional[str] = None
        self._version: Optional[str] = None

    @property
    def td_path(self) -> Optional[str]:
        if self._td_path is None:
            self._td_path = self._discover_td()
        return self._td_path

    @property
    def batch_path(self) -> Optional[str]:
        if self._batch_path is None:
            self._batch_path = self._discover_td_batch()
        return self._batch_path

    def _discover_td(self) -> Optional[str]:
        """Find TouchDesigner executable on this system."""
        # Check environment variable first
        env_path = os.environ.get("TOUCHDESIGNER_PATH")
        if env_path and os.path.isfile(env_path):
            return env_path

        # Check PATH
        which_result = shutil.which("TouchDesigner")
        if which_result:
            return which_result

        # Check common installation paths
        system = platform.system()
        for path in self._SEARCH_PATHS.get(system, []):
            if os.path.isfile(path):
                return path

        return None

    def _discover_td_batch(self) -> Optional[str]:
        """Find TouchDesignerBatch executable on this system."""
        env_path = os.environ.get("TOUCHDESIGNER_BATCH_PATH")
        if env_path and os.path.isfile(env_path):
            return env_path

        which_result = shutil.which("TouchDesignerBatch")
        if which_result:
            return which_result

        system = platform.system()
        for path in self._BATCH_SEARCH_PATHS.get(system, []):
            if os.path.isfile(path):
                return path

        return None

    def is_available(self) -> bool:
        """Check if TouchDesigner is available on this system."""
        return self.td_path is not None or self.batch_path is not None

    def get_executable(self) -> str:
        """Return the best available TD executable path."""
        if self.batch_path:
            return self.batch_path
        if self.td_path:
            return self.td_path
        raise RuntimeError(
            "TouchDesigner not found. Install TouchDesigner or set "
            "TOUCHDESIGNER_PATH / TOUCHDESIGNER_BATCH_PATH environment variable."
        )

    def get_version(self) -> Optional[str]:
        """Query TouchDesigner version."""
        if self._version:
            return self._version
        try:
            exe = self.get_executable()
            result = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._version = result.stdout.strip() or result.stderr.strip()
            return self._version
        except Exception:
            return None

    def execute_script(
        self,
        script: str,
        toe_file: Optional[str] = None,
        timeout: int = 120,
        capture_json: bool = True,
    ) -> dict:
        """Execute a Python script inside TouchDesigner's runtime.

        Args:
            script: Python code to execute inside TD.
            toe_file: Optional .toe file to open before running script.
            timeout: Max seconds to wait.
            capture_json: If True, expect script to write JSON to a temp file.

        Returns:
            dict with keys: success, output, error, data (parsed JSON if any).
        """
        exe = self.get_executable()
        result_file = None

        try:
            # Create temp script file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as f:
                script_path = f.name
                if capture_json:
                    result_file = script_path.replace(".py", "_result.json")
                    # Wrap script to capture output as JSON
                    wrapped = (
                        f"import json, sys\n"
                        f"_result_path = {result_file!r}\n"
                        f"try:\n"
                        f"    _output = {{}}\n"
                        f"    {self._indent_script(script)}\n"
                        f"    with open(_result_path, 'w') as _rf:\n"
                        f"        json.dump(_output, _rf)\n"
                        f"except Exception as e:\n"
                        f"    with open(_result_path, 'w') as _rf:\n"
                        f'        json.dump({{"error": str(e)}}, _rf)\n'
                        f"finally:\n"
                        f"    project.quit()\n"
                    )
                    f.write(wrapped)
                else:
                    f.write(script + "\nproject.quit()\n")

            # Build command
            cmd = [exe]
            if toe_file:
                cmd.append(toe_file)
            cmd.extend(["-m", script_path])

            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )

            # Parse results
            data = {}
            if capture_json and result_file and os.path.isfile(result_file):
                with open(result_file) as rf:
                    data = json.load(rf)

            return {
                "success": proc.returncode == 0 and "error" not in data,
                "output": proc.stdout,
                "error": proc.stderr or data.get("error", ""),
                "data": data,
                "returncode": proc.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"TouchDesigner execution timed out after {timeout}s",
                "data": {},
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "data": {},
                "returncode": -1,
            }
        finally:
            # Cleanup temp files
            for path in [script_path, result_file]:
                if path and os.path.isfile(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass

    def render_toe(
        self,
        toe_file: str,
        output_path: str,
        top_path: str = "/project1/out1",
        width: int = 1920,
        height: int = 1080,
        frames: int = 1,
    ) -> dict:
        """Render a frame or sequence from a .toe file.

        Args:
            toe_file: Path to .toe project file.
            output_path: Output image/video path.
            top_path: Operator path to render from.
            width: Output width.
            height: Output height.
            frames: Number of frames to render.

        Returns:
            dict with execution result.
        """
        script = f"""
import os
top = op('{top_path}')
if top is None:
    _output['error'] = 'Operator not found: {top_path}'
else:
    top.par.resolutionw = {width}
    top.par.resolutionh = {height}
    top.save('{output_path}')
    _output['rendered'] = True
    _output['path'] = '{output_path}'
    _output['size'] = os.path.getsize('{output_path}')
    _output['resolution'] = [{width}, {height}]
"""
        return self.execute_script(script, toe_file=toe_file)

    @staticmethod
    def _indent_script(script: str) -> str:
        """Indent a script block for wrapping inside try/except."""
        lines = script.strip().split("\n")
        return "\n    ".join(lines)


# Singleton instance
_backend: Optional[TouchDesignerBackend] = None


def get_backend(td_path: Optional[str] = None) -> TouchDesignerBackend:
    """Get or create the singleton backend instance."""
    global _backend
    if _backend is None:
        _backend = TouchDesignerBackend(td_path=td_path)
    return _backend
