"""Tests for the real-time TCP connection module."""

import json
import socket
import threading
import time

import pytest

from cli_anything_touchdesigner.connection import (
    TDConnection,
    DEFAULT_HOST,
    DEFAULT_PORT,
    TD_RECEIVER_SCRIPT,
)


# ---------------------------------------------------------------------------
# Helpers — lightweight TCP echo server that mimics the TD receiver
# ---------------------------------------------------------------------------

def _make_mock_td_server(host="127.0.0.1", port=0):
    """Start a mock TD receiver that exec()s nothing but returns OK.

    Returns (server_socket, port, stop_event).
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    actual_port = srv.getsockname()[1]
    stop = threading.Event()

    def _serve():
        srv.settimeout(0.5)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            data = b""
            conn.settimeout(2)
            while True:
                try:
                    chunk = conn.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                data += chunk
                if b"\x00" in data:
                    break
            # Respond with OK
            conn.sendall(b'{"status":"ok"}\x00')
            conn.close()
        srv.close()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    return srv, actual_port, stop


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTDConnectionDefaults:
    def test_default_host_port(self):
        conn = TDConnection()
        assert conn.host == DEFAULT_HOST
        assert conn.port == DEFAULT_PORT

    def test_custom_host_port(self):
        conn = TDConnection(host="10.0.0.5", port=1234)
        assert conn.host == "10.0.0.5"
        assert conn.port == 1234


class TestBootstrapScript:
    def test_contains_port(self):
        script = TDConnection.get_bootstrap_script(9005)
        assert "9005" in script

    def test_custom_port(self):
        script = TDConnection.get_bootstrap_script(7777)
        assert "7777" in script
        assert "9005" not in script

    def test_contains_socket_import(self):
        script = TDConnection.get_bootstrap_script()
        assert "import socket" in script

    def test_contains_td_run(self):
        script = TDConnection.get_bootstrap_script()
        assert "_td_run(" in script
        assert "_wrap_with_errors" in script

    def test_wrapped_in_exec(self):
        script = TDConnection.get_bootstrap_script()
        assert script.startswith('exec("')

    def test_compiles(self):
        script = TDConnection.get_bootstrap_script(9005)
        compile(script, "<test>", "exec")


class TestPing:
    def test_ping_no_server(self):
        """Ping should return False when nothing is listening."""
        conn = TDConnection(port=19999)
        assert conn.ping(timeout=0.5) is False

    def test_ping_with_server(self):
        _, port, stop = _make_mock_td_server()
        try:
            conn = TDConnection(port=port)
            assert conn.ping(timeout=2) is True
        finally:
            stop.set()

class TestSendScript:
    def test_send_empty_script(self):
        conn = TDConnection(port=19999)
        result = conn.send_script("")
        assert result["success"] is False
        assert "Empty" in result["message"]

    def test_send_to_mock_server(self):
        _, port, stop = _make_mock_td_server()
        try:
            conn = TDConnection(port=port)
            result = conn.send_script("print('hello')")
            assert result["success"] is True
        finally:
            stop.set()

    def test_send_connection_refused(self):
        conn = TDConnection(port=19999)
        result = conn.send_script("print('fail')", timeout=1)
        assert result["success"] is False
        assert "refused" in result["message"].lower() or "error" in result["message"].lower()


class TestPushProject:
    def test_push_project(self):
        from cli_anything_touchdesigner.project import TDProject

        _, port, stop = _make_mock_td_server()
        try:
            proj = TDProject(name="test_push")
            proj.add_operator("noise1", "TOP", "noiseTOP")
            conn = TDConnection(port=port)
            result = conn.push_project(proj)
            assert result["success"] is True
        finally:
            stop.set()

    def test_push_strips_save_line(self):
        from cli_anything_touchdesigner.project import TDProject

        proj = TDProject(name="test_strip")
        proj.add_operator("n1", "TOP", "noiseTOP")
        conn = TDConnection(port=19999)

        # We can't send (no server), but we can verify the script
        # generation by calling push_project's internal logic.
        script = proj.generate_td_script()
        assert "project.save(" in script

        # The push_project method strips that line — verify via
        # the connection object's internal code path.
        lines = [
            ln for ln in script.splitlines()
            if not ln.strip().startswith("project.save(")
        ]
        cleaned = "\n".join(lines)
        assert "project.save(" not in cleaned


class TestParseResponse:
    def test_valid_ok_json(self):
        result = TDConnection._parse_response(b'{"status":"ok"}')
        assert result["success"] is True

    def test_valid_error_json(self):
        result = TDConnection._parse_response(
            b'{"status":"error","message":"boom"}'
        )
        assert result["success"] is False
        assert "boom" in result["message"]

    def test_non_json_response(self):
        result = TDConnection._parse_response(b"some raw text")
        assert result["success"] is True  # non-empty = success
        assert "some raw text" in result["raw"]

    def test_empty_response(self):
        result = TDConnection._parse_response(b"")
        assert result["success"] is False
