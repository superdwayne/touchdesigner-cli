"""Tests for project management module."""

import json
import os
import tempfile

import pytest

from cli_anything_touchdesigner.project import TDProject, ProjectManager


class TestTDProject:
    """Unit tests for TDProject."""

    def test_create_project(self):
        proj = TDProject(name="test", project_type="standard")
        assert proj.name == "test"
        assert proj.project_type == "standard"
        assert len(proj.operators) == 0
        assert len(proj.connections) == 0
        assert not proj.is_dirty

    def test_add_operator(self):
        proj = TDProject(name="test")
        op = proj.add_operator("noise1", "TOP", "noiseTOP")
        assert op["name"] == "noise1"
        assert op["family"] == "TOP"
        assert op["type"] == "noiseTOP"
        assert op["path"] == "/project1/noise1"
        assert proj.is_dirty

    def test_add_operator_invalid_family(self):
        proj = TDProject(name="test")
        with pytest.raises(ValueError, match="Invalid operator family"):
            proj.add_operator("bad1", "INVALID", "someTOP")

    def test_add_operator_with_params(self):
        proj = TDProject(name="test")
        op = proj.add_operator(
            "noise1", "TOP", "noiseTOP",
            params={"amp": 2.0, "period": 0.5},
        )
        assert op["parameters"]["amp"] == 2.0
        assert op["parameters"]["period"] == 0.5

    def test_add_operator_with_position(self):
        proj = TDProject(name="test")
        op = proj.add_operator("noise1", "TOP", "noiseTOP", position=[100, 200])
        assert op["position"] == [100, 200]

    def test_remove_operator(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        assert proj.remove_operator("/project1/noise1")
        assert len(proj.operators) == 0

    def test_remove_nonexistent_operator(self):
        proj = TDProject(name="test")
        assert not proj.remove_operator("/project1/nope")

    def test_remove_operator_removes_connections(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        proj.add_operator("null1", "TOP", "nullTOP")
        proj.connect("/project1/noise1", "/project1/null1")
        assert len(proj.connections) == 1
        proj.remove_operator("/project1/noise1")
        assert len(proj.connections) == 0

    def test_get_operator(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        op = proj.get_operator("/project1/noise1")
        assert op is not None
        assert op["name"] == "noise1"

    def test_get_operator_not_found(self):
        proj = TDProject(name="test")
        assert proj.get_operator("/project1/nope") is None

    def test_list_operators(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        proj.add_operator("lfo1", "CHOP", "lfoCHOP")
        proj.add_operator("null1", "TOP", "nullTOP")

        all_ops = proj.list_operators()
        assert len(all_ops) == 3

        tops = proj.list_operators(family="TOP")
        assert len(tops) == 2

        chops = proj.list_operators(family="CHOP")
        assert len(chops) == 1

    def test_set_parameter(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        assert proj.set_parameter("/project1/noise1", "amp", 5.0)
        assert proj.operators["/project1/noise1"]["parameters"]["amp"] == 5.0

    def test_set_parameter_nonexistent_op(self):
        proj = TDProject(name="test")
        assert not proj.set_parameter("/project1/nope", "amp", 1.0)

    def test_get_parameter(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP", params={"amp": 3.0})
        assert proj.get_parameter("/project1/noise1", "amp") == 3.0

    def test_get_parameter_not_found(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        assert proj.get_parameter("/project1/noise1", "nonexistent") is None

    def test_connect_operators(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        proj.add_operator("null1", "TOP", "nullTOP")
        conn = proj.connect("/project1/noise1", "/project1/null1")
        assert conn["from"] == "/project1/noise1"
        assert conn["to"] == "/project1/null1"
        assert len(proj.connections) == 1

    def test_connect_cross_family_raises(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        proj.add_operator("lfo1", "CHOP", "lfoCHOP")
        with pytest.raises(ValueError, match="Cannot connect"):
            proj.connect("/project1/noise1", "/project1/lfo1")

    def test_connect_nonexistent_source(self):
        proj = TDProject(name="test")
        proj.add_operator("null1", "TOP", "nullTOP")
        with pytest.raises(ValueError, match="Source operator not found"):
            proj.connect("/project1/nope", "/project1/null1")

    def test_disconnect(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        proj.add_operator("null1", "TOP", "nullTOP")
        proj.connect("/project1/noise1", "/project1/null1")
        assert proj.disconnect("/project1/noise1", "/project1/null1")
        assert len(proj.connections) == 0

    def test_disconnect_nonexistent(self):
        proj = TDProject(name="test")
        assert not proj.disconnect("/a", "/b")

    def test_list_connections(self):
        proj = TDProject(name="test")
        proj.add_operator("a", "TOP", "noiseTOP")
        proj.add_operator("b", "TOP", "nullTOP")
        proj.add_operator("c", "TOP", "levelTOP")
        proj.connect("/project1/a", "/project1/b")
        proj.connect("/project1/b", "/project1/c")

        all_conns = proj.list_connections()
        assert len(all_conns) == 2

        b_conns = proj.list_connections("/project1/b")
        assert len(b_conns) == 2  # b is both source and destination

    def test_set_flag(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        assert proj.set_flag("/project1/noise1", "bypass", True)
        assert proj.operators["/project1/noise1"]["flags"]["bypass"] is True

    def test_set_flag_invalid(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        assert not proj.set_flag("/project1/noise1", "nonexistent", True)

    def test_undo_redo(self):
        proj = TDProject(name="test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        assert len(proj.operators) == 1

        proj.add_operator("null1", "TOP", "nullTOP")
        assert len(proj.operators) == 2

        assert proj.undo()
        assert len(proj.operators) == 1

        assert proj.redo()
        assert len(proj.operators) == 2

    def test_undo_empty_stack(self):
        proj = TDProject(name="test")
        assert not proj.undo()

    def test_redo_empty_stack(self):
        proj = TDProject(name="test")
        assert not proj.redo()

    def test_save_and_load(self):
        proj = TDProject(name="save_test")
        proj.add_operator("noise1", "TOP", "noiseTOP", params={"amp": 2.0})
        proj.add_operator("null1", "TOP", "nullTOP")
        proj.connect("/project1/noise1", "/project1/null1")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            proj.save(path)
            loaded = TDProject.load(path)
            assert loaded.name == "save_test"
            assert len(loaded.operators) == 2
            assert len(loaded.connections) == 1
            assert loaded.operators["/project1/noise1"]["parameters"]["amp"] == 2.0
        finally:
            os.unlink(path)

    def test_to_json(self):
        proj = TDProject(name="json_test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        data = json.loads(proj.to_json())
        assert data["name"] == "json_test"
        assert "/project1/noise1" in data["operators"]

    def test_info(self):
        proj = TDProject(name="info_test")
        proj.add_operator("noise1", "TOP", "noiseTOP")
        proj.add_operator("lfo1", "CHOP", "lfoCHOP")
        info = proj.info()
        assert info["name"] == "info_test"
        assert info["operators"] == 2
        assert info["families"]["TOP"] == 1
        assert info["families"]["CHOP"] == 1

    def test_generate_td_script(self):
        proj = TDProject(name="script_test")
        proj.add_operator("noise1", "TOP", "noiseTOP", params={"amp": 1.0})
        proj.add_operator("null1", "TOP", "nullTOP")
        proj.connect("/project1/noise1", "/project1/null1")

        script = proj.generate_td_script()
        assert "noiseTOP" in script
        assert "nullTOP" in script
        assert "inputConnectors" in script

    def test_metadata(self):
        proj = TDProject(name="meta_test")
        assert proj.metadata["fps"] == 60
        assert proj.metadata["resolution"] == [1920, 1080]


class TestProjectManager:
    """Unit tests for ProjectManager."""

    def test_new_project(self):
        mgr = ProjectManager()
        proj = mgr.new_project("test")
        assert proj.name == "test"
        assert mgr.active_project is proj

    def test_multiple_projects(self):
        mgr = ProjectManager()
        mgr.new_project("a")
        mgr.new_project("b")
        assert mgr.active_project.name == "b"
        assert set(mgr.list_projects()) == {"a", "b"}

    def test_switch_project(self):
        mgr = ProjectManager()
        mgr.new_project("a")
        mgr.new_project("b")
        assert mgr.switch_project("a")
        assert mgr.active_project.name == "a"

    def test_switch_nonexistent(self):
        mgr = ProjectManager()
        assert not mgr.switch_project("nope")

    def test_close_project(self):
        mgr = ProjectManager()
        mgr.new_project("a")
        mgr.new_project("b")
        assert mgr.close_project("a")
        assert "a" not in mgr.list_projects()
        assert mgr.active_project.name == "b"

    def test_close_active_project(self):
        mgr = ProjectManager()
        mgr.new_project("a")
        mgr.new_project("b")
        mgr.close_project("b")
        assert mgr.active_project.name == "a"

    def test_close_last_project(self):
        mgr = ProjectManager()
        mgr.new_project("only")
        mgr.close_project("only")
        assert mgr.active_project is None

    def test_save_and_open(self):
        mgr = ProjectManager()
        proj = mgr.new_project("persist_test")
        proj.add_operator("noise1", "TOP", "noiseTOP")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            mgr.save_project(path)

            mgr2 = ProjectManager()
            loaded = mgr2.open_project(path)
            assert loaded.name == "persist_test"
            assert len(loaded.operators) == 1
        finally:
            os.unlink(path)
