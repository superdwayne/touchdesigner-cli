"""Tests for network builder and templates."""

import pytest

from cli_anything_touchdesigner.network import NetworkBuilder, TEMPLATES
from cli_anything_touchdesigner.project import TDProject


class TestNetworkBuilder:
    """Unit tests for NetworkBuilder."""

    def setup_method(self):
        self.proj = TDProject(name="test")
        self.builder = NetworkBuilder(self.proj)

    def test_add_chain(self):
        ops = [
            ("noise1", "TOP", "noiseTOP", None),
            ("level1", "TOP", "levelTOP", None),
            ("null1", "TOP", "nullTOP", None),
        ]
        created = self.builder.add_chain(ops)
        assert len(created) == 3
        assert len(self.proj.connections) == 2

    def test_add_chain_no_auto_connect(self):
        ops = [
            ("noise1", "TOP", "noiseTOP", None),
            ("null1", "TOP", "nullTOP", None),
        ]
        created = self.builder.add_chain(ops, auto_connect=False)
        assert len(created) == 2
        assert len(self.proj.connections) == 0

    def test_add_chain_cross_family_skips_connection(self):
        ops = [
            ("noise1", "TOP", "noiseTOP", None),
            ("lfo1", "CHOP", "lfoCHOP", None),
        ]
        created = self.builder.add_chain(ops)
        assert len(created) == 2
        assert len(self.proj.connections) == 0  # cross-family skipped

    def test_build_audio_reactive(self):
        created = self.builder.build_audio_reactive()
        assert len(created) >= 8
        families = {op["family"] for op in created}
        assert "CHOP" in families
        assert "TOP" in families

    def test_build_feedback_loop(self):
        created = self.builder.build_feedback_loop()
        assert len(created) >= 5
        # Should have multiple connections for the feedback loop
        assert len(self.proj.connections) >= 4

    def test_build_3d_scene(self):
        created = self.builder.build_3d_scene()
        families = {op["family"] for op in created}
        assert "COMP" in families
        assert "TOP" in families
        assert "SOP" in families

    def test_build_3d_scene_geometries(self):
        for geo in ["box", "sphere", "grid", "torus"]:
            proj = TDProject(name="test")
            builder = NetworkBuilder(proj)
            created = builder.build_3d_scene(geometry=geo)
            assert len(created) >= 5

    def test_build_particle_system(self):
        created = self.builder.build_particle_system()
        assert len(created) >= 4
        families = {op["family"] for op in created}
        assert "POP" in families

    def test_build_instancing(self):
        created = self.builder.build_instancing(count=50)
        assert len(created) >= 5
        families = {op["family"] for op in created}
        assert "CHOP" in families
        assert "COMP" in families

    def test_build_glsl_shader(self):
        created = self.builder.build_glsl_shader()
        assert len(created) >= 4
        families = {op["family"] for op in created}
        assert "TOP" in families
        assert "DAT" in families

    def test_build_glsl_shader_custom_code(self):
        code = "out vec4 fragColor;\nvoid main() { fragColor = vec4(1,0,0,1); }"
        created = self.builder.build_glsl_shader(shader_code=code)
        # Find the DAT with shader code
        dats = [op for op in created if op["family"] == "DAT"]
        assert len(dats) == 1
        assert dats[0]["parameters"]["text"] == code

    def test_build_osc_receiver(self):
        created = self.builder.build_osc_receiver(port=9000)
        assert len(created) >= 3
        osc_in = [op for op in created if "osc" in op["name"].lower()]
        assert len(osc_in) >= 1

    def test_build_osc_receiver_custom_port(self):
        created = self.builder.build_osc_receiver(port=8888)
        osc_ops = [op for op in created if op["type"] == "oscinCHOP"]
        assert len(osc_ops) == 1
        assert osc_ops[0]["parameters"]["port"] == 8888

    def test_build_video_mixer(self):
        created = self.builder.build_video_mixer(input_count=3)
        movie_ins = [op for op in created if op["type"] == "moviefileinTOP"]
        assert len(movie_ins) == 3

    def test_build_video_mixer_connections(self):
        created = self.builder.build_video_mixer(input_count=2)
        assert len(self.proj.connections) >= 3

    def test_custom_parent(self):
        self.proj.add_operator("base1", "COMP", "baseCOMP")
        created = self.builder.build_feedback_loop(parent="/project1/base1")
        for op in created:
            assert op["parent"] == "/project1/base1"


class TestTemplates:
    """Test template registry."""

    def test_all_templates_listed(self):
        assert "audio-reactive" in TEMPLATES
        assert "feedback-loop" in TEMPLATES
        assert "3d-scene" in TEMPLATES
        assert "particle-system" in TEMPLATES
        assert "instancing" in TEMPLATES
        assert "glsl-shader" in TEMPLATES
        assert "osc-receiver" in TEMPLATES
        assert "video-mixer" in TEMPLATES

    def test_templates_have_descriptions(self):
        for name, desc in TEMPLATES.items():
            assert isinstance(desc, str)
            assert len(desc) > 10, f"Template '{name}' has short description"
