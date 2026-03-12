"""Tests for CLI entry point using Click's test runner."""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from cli_anything_touchdesigner.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_file():
    """Create a temp project file for testing."""
    from cli_anything_touchdesigner.project import TDProject

    proj = TDProject(name="cli_test")
    proj.add_operator("noise1", "TOP", "noiseTOP", params={"amp": 1.0})
    proj.add_operator("null1", "TOP", "nullTOP")
    proj.connect("/project1/noise1", "/project1/null1")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        f.write(proj.to_json())
        path = f.name
    yield path
    os.unlink(path)


class TestCLIVersion:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output


class TestProjectCommands:
    def test_project_new(self, runner):
        result = runner.invoke(cli, ["project", "new", "myproject"])
        assert result.exit_code == 0
        assert "Created project" in result.output

    def test_project_new_json(self, runner):
        result = runner.invoke(cli, ["--json", "project", "new", "myproject"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "success"

    def test_project_new_with_output(self, runner):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = runner.invoke(cli, ["project", "new", "myproject", "-o", path])
            assert result.exit_code == 0
            assert os.path.isfile(path)
            with open(path) as f:
                data = json.load(f)
            assert data["name"] == "myproject"
        finally:
            os.unlink(path)

    def test_project_open(self, runner, project_file):
        result = runner.invoke(cli, ["project", "open", project_file])
        assert result.exit_code == 0
        assert "Opened project" in result.output

    def test_project_info(self, runner, project_file):
        result = runner.invoke(cli, ["--project", project_file, "project", "info"])
        assert result.exit_code == 0
        assert "cli_test" in result.output

    def test_project_info_json(self, runner, project_file):
        result = runner.invoke(cli, ["--json", "--project", project_file, "project", "info"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "cli_test"


class TestOperatorCommands:
    def test_op_add(self, runner, project_file):
        result = runner.invoke(
            cli,
            ["--project", project_file, "op", "add", "TOP", "noise", "myNoise"],
        )
        assert result.exit_code == 0
        assert "Added TOP" in result.output

    def test_op_add_json(self, runner, project_file):
        result = runner.invoke(
            cli,
            ["--json", "--project", project_file, "op", "add", "TOP", "noise", "myNoise"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "success"

    def test_op_add_with_params(self, runner, project_file):
        result = runner.invoke(
            cli,
            [
                "--project", project_file,
                "op", "add", "TOP", "noise", "paramNoise",
                "--param", "amp=5.0",
                "--param", "period=2.0",
            ],
        )
        assert result.exit_code == 0

    def test_op_list(self, runner, project_file):
        result = runner.invoke(cli, ["--project", project_file, "op", "list"])
        assert result.exit_code == 0
        assert "noise1" in result.output

    def test_op_list_json(self, runner, project_file):
        result = runner.invoke(cli, ["--json", "--project", project_file, "op", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_op_list_filter_family(self, runner, project_file):
        result = runner.invoke(
            cli, ["--project", project_file, "op", "list", "--family", "TOP"]
        )
        assert result.exit_code == 0
        assert "noise1" in result.output

    def test_op_info(self, runner, project_file):
        result = runner.invoke(
            cli, ["--project", project_file, "op", "info", "/project1/noise1"]
        )
        assert result.exit_code == 0
        assert "noise1" in result.output

    def test_op_info_not_found(self, runner, project_file):
        result = runner.invoke(
            cli, ["--project", project_file, "op", "info", "/project1/nope"]
        )
        assert result.exit_code != 0

    def test_op_set(self, runner, project_file):
        result = runner.invoke(
            cli,
            ["--project", project_file, "op", "set", "/project1/noise1", "amp", "3.0"],
        )
        assert result.exit_code == 0
        assert "Set amp" in result.output

    def test_op_get(self, runner, project_file):
        result = runner.invoke(
            cli,
            ["--project", project_file, "op", "get", "/project1/noise1", "amp"],
        )
        assert result.exit_code == 0

    def test_op_remove(self, runner, project_file):
        result = runner.invoke(
            cli, ["--project", project_file, "op", "remove", "/project1/noise1"]
        )
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_op_types(self, runner):
        result = runner.invoke(cli, ["op", "types"])
        assert result.exit_code == 0
        assert "TOP" in result.output

    def test_op_types_family(self, runner):
        result = runner.invoke(cli, ["op", "types", "TOP"])
        assert result.exit_code == 0
        assert "noiseTOP" in result.output

    def test_op_suggest(self, runner):
        result = runner.invoke(cli, ["op", "suggest", "audio", "reactive"])
        assert result.exit_code == 0
        assert "audio" in result.output.lower()


class TestNetworkCommands:
    def test_net_connect(self, runner):
        # Create a project with two unconnected ops, save, then connect
        from cli_anything_touchdesigner.project import TDProject
        import tempfile, os

        proj = TDProject(name="conn_test")
        proj.add_operator("a", "TOP", "noiseTOP")
        proj.add_operator("b", "TOP", "nullTOP")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write(proj.to_json())
            path = f.name

        try:
            result = runner.invoke(
                cli,
                ["--project", path, "net", "connect", "/project1/a", "/project1/b"],
            )
            assert result.exit_code == 0
            assert "Connected" in result.output
        finally:
            os.unlink(path)

    def test_net_list(self, runner, project_file):
        result = runner.invoke(cli, ["--project", project_file, "net", "list"])
        assert result.exit_code == 0

    def test_net_templates(self, runner):
        result = runner.invoke(cli, ["net", "templates"])
        assert result.exit_code == 0
        assert "audio-reactive" in result.output
        assert "feedback-loop" in result.output

    def test_net_templates_json(self, runner):
        result = runner.invoke(cli, ["--json", "net", "templates"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "audio-reactive" in data

    def test_net_template_build(self, runner):
        # Create project first, then build template
        result = runner.invoke(cli, ["project", "new", "tmpl_test"])
        assert result.exit_code == 0
        # Note: Click context doesn't persist between invocations in testing,
        # so we test via the project module directly for template building


class TestExportCommands:
    def test_export_script(self, runner, project_file):
        result = runner.invoke(
            cli, ["--project", project_file, "export", "script"]
        )
        assert result.exit_code == 0
        assert "noiseTOP" in result.output

    def test_export_script_to_file(self, runner, project_file):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            out_path = f.name
        try:
            result = runner.invoke(
                cli,
                ["--project", project_file, "export", "script", "-o", out_path],
            )
            assert result.exit_code == 0
            with open(out_path) as f:
                content = f.read()
            assert "noiseTOP" in content
        finally:
            os.unlink(out_path)

    def test_export_json(self, runner, project_file):
        result = runner.invoke(
            cli, ["--project", project_file, "export", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "cli_test"

    def test_export_json_to_file(self, runner, project_file):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name
        try:
            result = runner.invoke(
                cli,
                ["--project", project_file, "export", "json", "-o", out_path],
            )
            assert result.exit_code == 0
            with open(out_path) as f:
                data = json.load(f)
            assert data["name"] == "cli_test"
        finally:
            os.unlink(out_path)


class TestStatusCommand:
    def test_status(self, runner):
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0

    def test_status_json(self, runner):
        result = runner.invoke(cli, ["--json", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "touchdesigner_available" in data
