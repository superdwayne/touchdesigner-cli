"""Real-time TCP connection to a running TouchDesigner instance.

Sends Python code over a TCP socket to a listener DAT running inside TD,
enabling live execution without copy-pasting into the textport.

Default port: 9005
Protocol: Send Python source terminated by a null byte (\\x00).
TD-side listener exec()s each received payload.
"""

import json
import os
import socket
import tempfile
import time
from typing import List, Optional


# Shared error log path — TD writes errors here, CLI reads them back
ERROR_LOG_PATH = os.path.join(tempfile.gettempdir(), "td_cli_errors.log")


# The Python code that runs inside TouchDesigner to create the TCP listener.
# {port} is replaced at generation time.  The entire block is wrapped in
# exec() so TD's line-by-line textport can handle it as one statement.
_TD_RECEIVER_CODE = """\
import socket, threading, traceback, json, time as _time
_td_run = run
_ERR_LOG = '{error_log}'
def _wrap_with_errors(code):
    return (
        'import traceback as _tb\\n'
        'try:\\n'
        + ''.join('    ' + ln + '\\n' for ln in code.splitlines()) +
        'except Exception:\\n'
        '    _err = _tb.format_exc()\\n'
        '    print("[td-cli] ERROR: " + _err)\\n'
        '    with open("' + _ERR_LOG + '", "a") as _ef:\\n'
        '        _ef.write(str(_time.time()) + " | " + _err + "\\\\n---\\\\n")\\n'
    )
def _serve():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(('127.0.0.1', {port}))
    except OSError as e:
        print('[td-cli] ERROR: ' + str(e))
        return
    srv.listen(1)
    print('[td-cli] Listening on 127.0.0.1:{port}')
    while True:
        try:
            conn, addr = srv.accept()
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\\x00' in data:
                    data = data.split(b'\\x00')[0]
                    break
            code = data.decode('utf-8', errors='replace')
            if code.strip():
                _td_run(_wrap_with_errors(code), delayFrames=1)
                print('[td-cli] Queued script (' + str(len(code)) + ' bytes)')
                conn.sendall(b'{{"status":"ok"}}' + b'\\x00')
            conn.close()
        except Exception as e:
            print('[td-cli] Connection error: ' + str(e))
t = threading.Thread(target=_serve, daemon=True)
t.start()
print('[td-cli] Receiver started on port {port}')
print('[td-cli] Error log: ' + _ERR_LOG)
"""


# Keep this for backwards-compat with tests that import it
TD_RECEIVER_SCRIPT = _TD_RECEIVER_CODE


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9005
SEND_TIMEOUT = 10  # seconds


class TDConnection:
    """TCP client that pushes Python code to a running TouchDesigner instance."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ping(self, timeout: float = 2.0) -> bool:
        """Return True if the TD receiver is reachable."""
        try:
            with self._connect(timeout=timeout) as sock:
                sock.sendall(b'print("[td-cli] pong")\x00')
                resp = self._recv(sock, timeout=timeout)
                return b"ok" in resp
        except (ConnectionRefusedError, OSError, socket.timeout):
            return False

    def send_script(self, script: str, timeout: float = SEND_TIMEOUT) -> dict:
        """Send a Python script to TD and return the response.

        Returns:
            dict with keys: success (bool), message (str), raw (str).
        """
        if not script.strip():
            return {"success": False, "message": "Empty script", "raw": ""}

        try:
            with self._connect(timeout=timeout) as sock:
                payload = script.encode("utf-8") + b"\x00"
                sock.sendall(payload)
                resp = self._recv(sock, timeout=timeout)
                return self._parse_response(resp)
        except ConnectionRefusedError:
            return {
                "success": False,
                "message": (
                    f"Connection refused on {self.host}:{self.port}. "
                    "Is the TD receiver running? Use 'td-cli live bootstrap' to set it up."
                ),
                "raw": "",
            }
        except socket.timeout:
            return {
                "success": False,
                "message": f"Timeout after {timeout}s waiting for TD response.",
                "raw": "",
            }
        except OSError as e:
            return {"success": False, "message": str(e), "raw": ""}

    def push_project(self, project, timeout: float = SEND_TIMEOUT) -> dict:
        """Generate a TD script from a TDProject and send it live.

        Splits operator creation and connections into two separate sends
        so TD has a frame to register new operators before wiring them.

        Args:
            project: A TDProject instance.
            timeout: Socket timeout in seconds.

        Returns:
            dict with execution result.
        """
        script = project.generate_td_script()
        lines = [
            ln for ln in script.splitlines()
            if not ln.strip().startswith("project.save(")
        ]

        # Split into creation lines and connection lines
        create_lines = []
        connect_lines = []
        in_connections = False
        for ln in lines:
            if ln.strip() == "# Connections":
                in_connections = True
            if in_connections:
                connect_lines.append(ln)
            else:
                create_lines.append(ln)

        # Phase 1: create all operators
        result = self.send_script("\n".join(create_lines), timeout=timeout)
        if not result["success"]:
            return result

        if connect_lines:
            # Small delay to let TD register operators for one frame
            time.sleep(0.15)
            # Phase 2: wire connections
            result = self.send_script("\n".join(connect_lines), timeout=timeout)

        return result

    def query_params(self, op_type: str, parent: str = "/project1", timeout: float = SEND_TIMEOUT) -> dict:
        """Ask a running TD instance for valid parameters on an operator type.

        Creates a temp operator, reads its par names, then deletes it.
        Returns dict with success, params (list of param names), or error.
        """
        script = (
            "import json as _json\n"
            f"_tmp = op('{parent}').create('{op_type}', '__td_cli_query_tmp__')\n"
            "_params = [p.name for p in _tmp.pars()]\n"
            "_tmp.destroy()\n"
            "_dat = op('{parent}').create('textDAT', '__td_cli_result__')\n"
            "_dat.text = _json.dumps(_params)\n"
        )
        result = self.send_script(script, timeout=timeout)
        if not result["success"]:
            return result

        # Give TD a frame to execute
        time.sleep(0.2)

        # Read the result DAT
        read_script = (
            "import json as _json\n"
            f"_dat = op('{parent}/__td_cli_result__')\n"
            "if _dat:\n"
            "    print(_dat.text)\n"
            "    _dat.destroy()\n"
        )
        return self.send_script(read_script, timeout=timeout)

    def query_op_types(self, parent: str = "/project1", timeout: float = SEND_TIMEOUT) -> dict:
        """Ask TD for all available operator types it supports."""
        script = (
            "import json as _json\n"
            f"_dat = op('{parent}').create('textDAT', '__td_cli_result__')\n"
            "_types = []\n"
            "for family in ['TOP', 'CHOP', 'SOP', 'DAT', 'COMP', 'MAT']:\n"
            "    for t in dir(td):\n"
            "        if t.endswith(family) and t[0].islower():\n"
            "            _types.append(t)\n"
            "_dat.text = _json.dumps(sorted(_types))\n"
        )
        return self.send_script(script, timeout=timeout)

    # ------------------------------------------------------------------
    # Bootstrap helper
    # ------------------------------------------------------------------

    @staticmethod
    def get_bootstrap_script(port: int = DEFAULT_PORT) -> str:
        """Return the TD-side receiver script with the given port baked in.

        The code is wrapped in exec() so TD's textport (which executes
        line-by-line) treats the entire block as a single statement.
        """
        code = _TD_RECEIVER_CODE.replace("{port}", str(port))
        code = code.replace("{error_log}", ERROR_LOG_PATH.replace("\\", "/"))
        # Escape backslashes and quotes for embedding inside exec("...")
        escaped = code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return 'exec("' + escaped + '")'

    # ------------------------------------------------------------------
    # Error feedback
    # ------------------------------------------------------------------

    @staticmethod
    def read_errors(since: float = 0, clear: bool = False) -> List[str]:
        """Read TD execution errors from the shared error log.

        Args:
            since: Only return errors with timestamp > since (unix epoch).
            clear: If True, delete the log file after reading.

        Returns:
            List of error strings.
        """
        if not os.path.isfile(ERROR_LOG_PATH):
            return []

        with open(ERROR_LOG_PATH, "r") as f:
            content = f.read()

        if clear:
            try:
                os.unlink(ERROR_LOG_PATH)
            except OSError:
                pass

        if not content.strip():
            return []

        errors = []
        for block in content.split("\n---\n"):
            block = block.strip()
            if not block:
                continue
            # Parse timestamp if filtering
            if since and " | " in block:
                ts_str = block.split(" | ", 1)[0]
                try:
                    ts = float(ts_str)
                    if ts <= since:
                        continue
                    block = block.split(" | ", 1)[1]
                except ValueError:
                    pass
            elif since and " | " in block:
                block = block.split(" | ", 1)[1]
            else:
                # No timestamp prefix
                pass
            errors.append(block)
        return errors

    @staticmethod
    def clear_errors():
        """Delete the shared error log."""
        if os.path.isfile(ERROR_LOG_PATH):
            os.unlink(ERROR_LOG_PATH)

    # ------------------------------------------------------------------
    # Render helper
    # ------------------------------------------------------------------

    @staticmethod
    def generate_render_script(
        output_path: str,
        top_path: str = "/project1/out1",
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Generate a Python script that runs inside TD to render a TOP to an image file.

        Args:
            output_path: Absolute path for the output image.
            top_path: TD operator path of the TOP to render.
            width: Output width in pixels.
            height: Output height in pixels.

        Returns:
            Python source code string to send via send_script().
        """
        return (
            "import json as _json\n"
            f"_top = op('{top_path}')\n"
            "if _top is None:\n"
            f"    print(_json.dumps({{'status':'error','message':'TOP not found: {top_path}'}}))\n"
            "else:\n"
            f"    _top.par.resolutionw = {width}\n"
            f"    _top.par.resolutionh = {height}\n"
            f"    _top.save('{output_path}')\n"
            f"    print(_json.dumps({{'status':'ok','message':'Rendered to {output_path}'}}))\n"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _connect(self, timeout: float = SEND_TIMEOUT) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((self.host, self.port))
        return sock

    def _recv(self, sock: socket.socket, timeout: float = SEND_TIMEOUT) -> bytes:
        """Receive until null byte or connection close."""
        sock.settimeout(timeout)
        data = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
            if b"\x00" in data:
                data = data.split(b"\x00")[0]
                break
        return data

    @staticmethod
    def _parse_response(raw: bytes) -> dict:
        text = raw.decode("utf-8", errors="replace").strip()
        try:
            parsed = json.loads(text)
            return {
                "success": parsed.get("status") == "ok",
                "message": parsed.get("message", "OK"),
                "raw": text,
            }
        except (json.JSONDecodeError, ValueError):
            # Non-JSON response — treat non-empty as success
            return {
                "success": bool(text),
                "message": text or "No response from TD",
                "raw": text,
            }
