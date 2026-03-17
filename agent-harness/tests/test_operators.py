"""Tests for operator registry and helpers."""

import pytest

from cli_anything_touchdesigner.operators import (
    OPERATOR_REGISTRY,
    find_type,
    get_defaults,
    get_families,
    get_types,
    suggest_operators,
)


class TestOperatorRegistry:
    """Unit tests for operator registry."""

    def test_all_families_present(self):
        families = get_families()
        assert "TOP" in families
        assert "CHOP" in families
        assert "SOP" in families
        assert "DAT" in families
        assert "COMP" in families
        assert "MAT" in families
        assert "POP" in families

    def test_get_types_top(self):
        types = get_types("TOP")
        assert len(types) > 10
        type_keys = [t["type"] for t in types]
        assert "noiseTOP" in type_keys
        assert "compositeTOP" in type_keys
        assert "renderTOP" in type_keys

    def test_get_types_chop(self):
        types = get_types("CHOP")
        assert len(types) > 10
        type_keys = [t["type"] for t in types]
        assert "lfoCHOP" in type_keys
        assert "oscinCHOP" in type_keys

    def test_get_types_sop(self):
        types = get_types("SOP")
        assert len(types) > 5
        type_keys = [t["type"] for t in types]
        assert "sphereSOP" in type_keys
        assert "boxSOP" in type_keys

    def test_get_types_dat(self):
        types = get_types("DAT")
        assert len(types) > 5
        type_keys = [t["type"] for t in types]
        assert "textDAT" in type_keys
        assert "tableDAT" in type_keys

    def test_get_types_comp(self):
        types = get_types("COMP")
        assert len(types) > 5
        type_keys = [t["type"] for t in types]
        assert "geometryCOMP" in type_keys
        assert "cameraCOMP" in type_keys

    def test_get_types_mat(self):
        types = get_types("MAT")
        assert len(types) > 3
        type_keys = [t["type"] for t in types]
        assert "pbrMAT" in type_keys
        assert "glslMAT" in type_keys

    def test_get_types_pop(self):
        types = get_types("POP")
        assert len(types) > 3
        type_keys = [t["type"] for t in types]
        assert "popGeneratePOP" in type_keys

    def test_get_types_case_insensitive(self):
        assert get_types("top") == get_types("TOP")
        assert get_types("chop") == get_types("CHOP")

    def test_get_types_invalid_family(self):
        assert get_types("INVALID") == []

    def test_find_type_by_key(self):
        result = find_type("TOP", "noiseTOP")
        assert result is not None
        assert result["type"] == "noiseTOP"
        assert result["label"] == "Noise"

    def test_find_type_by_label(self):
        result = find_type("TOP", "Noise")
        assert result is not None
        assert result["type"] == "noiseTOP"

    def test_find_type_case_insensitive(self):
        result = find_type("top", "noisetop")
        assert result is not None
        assert result["type"] == "noiseTOP"

    def test_find_type_fuzzy(self):
        result = find_type("TOP", "render")
        assert result is not None
        assert result["type"] == "renderTOP"

    def test_find_type_not_found(self):
        result = find_type("TOP", "definitelynotarealtype")
        assert result is None

    def test_get_defaults(self):
        defaults = get_defaults("TOP", "noiseTOP")
        assert isinstance(defaults, dict)

    def test_get_defaults_not_found(self):
        assert get_defaults("TOP", "nonexistent") == {}

    def test_all_types_have_required_fields(self):
        for family, types in OPERATOR_REGISTRY.items():
            for t in types:
                assert "type" in t, f"Missing 'type' in {family}: {t}"
                assert "label" in t, f"Missing 'label' in {family}: {t}"
                assert "defaults" in t, f"Missing 'defaults' in {family}: {t}"
                assert isinstance(t["defaults"], dict)


class TestSuggestOperators:
    """Unit tests for operator suggestions."""

    def test_audio_suggestions(self):
        suggestions = suggest_operators("audio reactive visualization")
        types = [s["type"] for s in suggestions]
        assert "audiofileinCHOP" in types
        assert "audiospectrumCHOP" in types

    def test_3d_suggestions(self):
        suggestions = suggest_operators("3d rendering scene")
        types = [s["type"] for s in suggestions]
        assert "geometryCOMP" in types
        assert "cameraCOMP" in types
        assert "renderTOP" in types

    def test_noise_suggestions(self):
        suggestions = suggest_operators("generative noise pattern")
        types = [s["type"] for s in suggestions]
        assert "noiseTOP" in types

    def test_particle_suggestions(self):
        suggestions = suggest_operators("particle system emit")
        types = [s["type"] for s in suggestions]
        assert "popGeneratePOP" in types

    def test_shader_suggestions(self):
        suggestions = suggest_operators("custom glsl shader")
        types = [s["type"] for s in suggestions]
        assert "glslTOP" in types

    def test_osc_suggestions(self):
        suggestions = suggest_operators("osc controller input")
        types = [s["type"] for s in suggestions]
        assert "oscinCHOP" in types

    def test_video_suggestions(self):
        suggestions = suggest_operators("video playback media")
        types = [s["type"] for s in suggestions]
        assert "moviefileinTOP" in types

    def test_feedback_suggestions(self):
        suggestions = suggest_operators("feedback trail echo")
        types = [s["type"] for s in suggestions]
        assert "feedbackTOP" in types

    def test_text_suggestions(self):
        suggestions = suggest_operators("text data table")
        types = [s["type"] for s in suggestions]
        assert "textDAT" in types
        assert "tableDAT" in types

    def test_default_suggestions(self):
        suggestions = suggest_operators("something completely random xyz")
        assert len(suggestions) > 0
