"""Operator definitions and factory for TouchDesigner operator families.

Provides a registry of all standard TD operator types organized by family,
plus helper functions for creating operators with sensible defaults.
"""

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Operator type registry – maps family → list of (type_key, display_name, defaults)
# ---------------------------------------------------------------------------

OPERATOR_REGISTRY: Dict[str, List[dict]] = {
    "TOP": [
        {"type": "noiseTOP", "label": "Noise", "defaults": {}},
        {"type": "compositeTOP", "label": "Composite", "defaults": {}},
        {"type": "feedbackTOP", "label": "Feedback", "defaults": {}},
        {"type": "glslTOP", "label": "GLSL", "defaults": {}},
        {"type": "renderTOP", "label": "Render", "defaults": {}},
        {"type": "moviefileinTOP", "label": "Movie File In", "defaults": {}},
        {"type": "nullTOP", "label": "Null", "defaults": {}},
        {"type": "transformTOP", "label": "Transform", "defaults": {}},
        {"type": "levelTOP", "label": "Level", "defaults": {}},
        {"type": "blurTOP", "label": "Blur", "defaults": {}},
        {"type": "switchTOP", "label": "Switch", "defaults": {}},
        {"type": "selectTOP", "label": "Select", "defaults": {}},
        {"type": "resolutionTOP", "label": "Resolution", "defaults": {}},
        {"type": "cropTOP", "label": "Crop", "defaults": {}},
        {"type": "flipTOP", "label": "Flip", "defaults": {}},
        {"type": "hsvTOP", "label": "HSV Adjust", "defaults": {}},
        {"type": "rampTOP", "label": "Ramp", "defaults": {}},
        {"type": "textTOP", "label": "Text", "defaults": {}},
        {"type": "circleTOP", "label": "Circle", "defaults": {}},
        {"type": "rectangleTOP", "label": "Rectangle", "defaults": {}},
        {"type": "choptoTOP", "label": "CHOP to", "defaults": {}},
        {"type": "edgeTOP", "label": "Edge", "defaults": {}},
        {"type": "displaceTOP", "label": "Displace", "defaults": {}},
        {"type": "cacheTOP", "label": "Cache", "defaults": {}},
        {"type": "overTOP", "label": "Over", "defaults": {}},
        {"type": "addTOP", "label": "Add", "defaults": {}},
        {"type": "multiplyTOP", "label": "Multiply", "defaults": {}},
        {"type": "constantTOP", "label": "Constant", "defaults": {}},
        {"type": "lookupTOP", "label": "Lookup", "defaults": {}},
        {"type": "reorderTOP", "label": "Reorder", "defaults": {}},
        {"type": "rgbaTOP", "label": "RGBA", "defaults": {}},
        {"type": "tileTOP", "label": "Tile", "defaults": {}},
        {"type": "mirrorTOP", "label": "Mirror", "defaults": {}},
        {"type": "soptoTOP", "label": "SOP to", "defaults": {}},
        {"type": "dattoTOP", "label": "DAT to", "defaults": {}},
    ],
    "CHOP": [
        {"type": "audiofileinCHOP", "label": "Audio File In", "defaults": {}},
        {"type": "lfoCHOP", "label": "LFO", "defaults": {}},
        {"type": "mathCHOP", "label": "Math", "defaults": {}},
        {"type": "filterCHOP", "label": "Filter", "defaults": {}},
        {"type": "oscinCHOP", "label": "OSC In", "defaults": {}},
        {"type": "oscoutCHOP", "label": "OSC Out", "defaults": {}},
        {"type": "midiinCHOP", "label": "MIDI In", "defaults": {}},
        {"type": "noiseCHOP", "label": "Noise", "defaults": {}},
        {"type": "nullCHOP", "label": "Null", "defaults": {}},
        {"type": "constantCHOP", "label": "Constant", "defaults": {}},
        {"type": "selectCHOP", "label": "Select", "defaults": {}},
        {"type": "switchCHOP", "label": "Switch", "defaults": {}},
        {"type": "mergeCHOP", "label": "Merge", "defaults": {}},
        {"type": "countCHOP", "label": "Count", "defaults": {}},
        {"type": "timerCHOP", "label": "Timer", "defaults": {}},
        {"type": "patternCHOP", "label": "Pattern", "defaults": {}},
        {"type": "audiospectrumCHOP", "label": "Audio Spectrum", "defaults": {}},
        {"type": "audiodevinCHOP", "label": "Audio Device In", "defaults": {}},
        {"type": "audiodevoutCHOP", "label": "Audio Device Out", "defaults": {}},
        {"type": "renameCHOP", "label": "Rename", "defaults": {}},
        {"type": "speedCHOP", "label": "Speed", "defaults": {}},
        {"type": "lagCHOP", "label": "Lag", "defaults": {}},
        {"type": "triggerCHOP", "label": "Trigger", "defaults": {}},
        {"type": "envelopeCHOP", "label": "Envelope", "defaults": {}},
        {"type": "analyzeCHOP", "label": "Analyze", "defaults": {}},
        {"type": "limitCHOP", "label": "Limit", "defaults": {}},
        {"type": "trailCHOP", "label": "Trail", "defaults": {}},
        {"type": "holdCHOP", "label": "Hold", "defaults": {}},
        {"type": "deleteCHOP", "label": "Delete", "defaults": {}},
        {"type": "shuffleCHOP", "label": "Shuffle", "defaults": {}},
        {"type": "fanCHOP", "label": "Fan", "defaults": {}},
        {"type": "choptoTOP", "label": "CHOP to TOP", "defaults": {}},
    ],
    "SOP": [
        {"type": "sphereSOP", "label": "Sphere", "defaults": {}},
        {"type": "boxSOP", "label": "Box", "defaults": {}},
        {"type": "gridSOP", "label": "Grid", "defaults": {}},
        {"type": "circleSOP", "label": "Circle", "defaults": {}},
        {"type": "lineSOP", "label": "Line", "defaults": {}},
        {"type": "torusSOP", "label": "Torus", "defaults": {}},
        {"type": "noiseSOP", "label": "Noise", "defaults": {}},
        {"type": "transformSOP", "label": "Transform", "defaults": {}},
        {"type": "copySOP", "label": "Copy", "defaults": {}},
        {"type": "mergeSOP", "label": "Merge", "defaults": {}},
        {"type": "nullSOP", "label": "Null", "defaults": {}},
        {"type": "switchSOP", "label": "Switch", "defaults": {}},
        {"type": "selectSOP", "label": "Select", "defaults": {}},
        {"type": "scriptSOP", "label": "Script", "defaults": {}},
        {"type": "subdivideSOP", "label": "Subdivide", "defaults": {}},
        {"type": "facetSOP", "label": "Facet", "defaults": {}},
        {"type": "tubeSOP", "label": "Tube", "defaults": {}},
        {"type": "metaballSOP", "label": "Metaball", "defaults": {}},
        {"type": "springSOP", "label": "Spring", "defaults": {}},
        {"type": "sortSOP", "label": "Sort", "defaults": {}},
        {"type": "deleteSOP", "label": "Delete", "defaults": {}},
        {"type": "convertSOP", "label": "Convert", "defaults": {}},
        {"type": "trailSOP", "label": "Trail", "defaults": {}},
        {"type": "scatterSOP", "label": "Scatter", "defaults": {}},
    ],
    "DAT": [
        {"type": "textDAT", "label": "Text", "defaults": {}},
        {"type": "tableDAT", "label": "Table", "defaults": {}},
        {"type": "scriptDAT", "label": "Script", "defaults": {}},
        {"type": "selectDAT", "label": "Select", "defaults": {}},
        {"type": "nullDAT", "label": "Null", "defaults": {}},
        {"type": "fifoDAT", "label": "FIFO", "defaults": {}},
        {"type": "webDAT", "label": "Web", "defaults": {}},
        {"type": "webserverDAT", "label": "Web Server", "defaults": {}},
        {"type": "oscinDAT", "label": "OSC In", "defaults": {}},
        {"type": "tcpipDAT", "label": "TCP/IP", "defaults": {}},
        {"type": "serialDAT", "label": "Serial", "defaults": {}},
        {"type": "mergeDAT", "label": "Merge", "defaults": {}},
        {"type": "switchDAT", "label": "Switch", "defaults": {}},
        {"type": "executeDAT", "label": "Execute", "defaults": {}},
        {"type": "chopexecuteDAT", "label": "CHOP Execute", "defaults": {}},
        {"type": "datexecuteDAT", "label": "DAT Execute", "defaults": {}},
        {"type": "convertDAT", "label": "Convert", "defaults": {}},
        {"type": "evaluateDAT", "label": "Evaluate", "defaults": {}},
        {"type": "jsonDAT", "label": "JSON", "defaults": {}},
    ],
    "COMP": [
        {"type": "containerCOMP", "label": "Container", "defaults": {}},
        {"type": "baseCOMP", "label": "Base", "defaults": {}},
        {"type": "geometryCOMP", "label": "Geometry", "defaults": {}},
        {"type": "cameraCOMP", "label": "Camera", "defaults": {}},
        {"type": "lightCOMP", "label": "Light", "defaults": {}},
        {"type": "animationCOMP", "label": "Animation", "defaults": {}},
        {"type": "buttonCOMP", "label": "Button", "defaults": {}},
        {"type": "sliderCOMP", "label": "Slider", "defaults": {}},
        {"type": "fieldCOMP", "label": "Field", "defaults": {}},
        {"type": "listCOMP", "label": "List", "defaults": {}},
        {"type": "windowCOMP", "label": "Window", "defaults": {}},
        {"type": "replicatorCOMP", "label": "Replicator", "defaults": {}},
        {"type": "selectCOMP", "label": "Select", "defaults": {}},
        {"type": "nullCOMP", "label": "Null", "defaults": {}},
        {"type": "panelexecuteCOMP", "label": "Panel Execute", "defaults": {}},
    ],
    "MAT": [
        {"type": "phongMAT", "label": "Phong", "defaults": {}},
        {"type": "pbrMAT", "label": "PBR", "defaults": {}},
        {"type": "glslMAT", "label": "GLSL", "defaults": {}},
        {"type": "constantMAT", "label": "Constant", "defaults": {}},
        {"type": "wireframeMAT", "label": "Wireframe", "defaults": {}},
        {"type": "depthMAT", "label": "Depth", "defaults": {}},
        {"type": "normalMAT", "label": "Normal Map", "defaults": {}},
        {"type": "pointspriteMAT", "label": "Point Sprite", "defaults": {}},
    ],
    "POP": [
        {"type": "popGeneratePOP", "label": "POP Generate", "defaults": {}},
        {"type": "popForcePOP", "label": "POP Force", "defaults": {}},
        {"type": "popAttribPOP", "label": "POP Attrib", "defaults": {}},
        {"type": "popNoisePOP", "label": "POP Noise", "defaults": {}},
        {"type": "popKillPOP", "label": "POP Kill", "defaults": {}},
        {"type": "popRenderPOP", "label": "POP Render", "defaults": {}},
    ],
}


def get_families() -> List[str]:
    """Return list of available operator families."""
    return list(OPERATOR_REGISTRY.keys())


def get_types(family: str) -> List[dict]:
    """Return available operator types for a family."""
    family = family.upper()
    return OPERATOR_REGISTRY.get(family, [])


def find_type(family: str, label_or_type: str) -> Optional[dict]:
    """Find an operator type by label or type key (case-insensitive)."""
    family = family.upper()
    types = OPERATOR_REGISTRY.get(family, [])
    label_or_type_lower = label_or_type.lower()
    for t in types:
        if t["type"].lower() == label_or_type_lower:
            return t
        if t["label"].lower() == label_or_type_lower:
            return t
    # Fuzzy: check if label_or_type is contained in the type or label
    for t in types:
        if label_or_type_lower in t["type"].lower() or label_or_type_lower in t["label"].lower():
            return t
    return None


def get_defaults(family: str, op_type: str) -> dict:
    """Return default parameters for an operator type."""
    info = find_type(family, op_type)
    if info:
        return dict(info["defaults"])
    return {}


def suggest_operators(description: str) -> List[dict]:
    """Suggest operators based on a natural-language description.

    Simple keyword matching for common TD workflows.
    """
    desc = description.lower()
    suggestions = []

    # Audio-reactive
    if any(w in desc for w in ["audio", "music", "sound", "beat"]):
        suggestions.extend([
            {"family": "CHOP", "type": "audiofileinCHOP", "reason": "Load audio file"},
            {"family": "CHOP", "type": "audiospectrumCHOP", "reason": "Analyze frequency spectrum"},
            {"family": "CHOP", "type": "mathCHOP", "reason": "Scale/offset audio values"},
            {"family": "TOP", "type": "choptoTOP", "reason": "Convert audio data to texture"},
        ])

    # 3D rendering
    if any(w in desc for w in ["3d", "render", "scene", "geometry", "mesh"]):
        suggestions.extend([
            {"family": "COMP", "type": "geometryCOMP", "reason": "Geometry container"},
            {"family": "COMP", "type": "cameraCOMP", "reason": "Camera for scene"},
            {"family": "COMP", "type": "lightCOMP", "reason": "Scene lighting"},
            {"family": "TOP", "type": "renderTOP", "reason": "Render the 3D scene"},
        ])

    # Noise / generative
    if any(w in desc for w in ["noise", "generative", "procedural", "random"]):
        suggestions.extend([
            {"family": "TOP", "type": "noiseTOP", "reason": "GPU noise texture"},
            {"family": "CHOP", "type": "noiseCHOP", "reason": "Noise channels for animation"},
            {"family": "SOP", "type": "noiseSOP", "reason": "Deform geometry with noise"},
        ])

    # Video / media
    if any(w in desc for w in ["video", "movie", "media", "playback", "film"]):
        suggestions.extend([
            {"family": "TOP", "type": "moviefileinTOP", "reason": "Load video/image file"},
            {"family": "TOP", "type": "compositeTOP", "reason": "Composite video layers"},
            {"family": "TOP", "type": "levelTOP", "reason": "Color correction"},
        ])

    # Particles
    if any(w in desc for w in ["particle", "points", "emit", "pop"]):
        suggestions.extend([
            {"family": "POP", "type": "popGeneratePOP", "reason": "Generate particles"},
            {"family": "POP", "type": "popForcePOP", "reason": "Apply forces to particles"},
            {"family": "POP", "type": "popRenderPOP", "reason": "Render particles"},
        ])

    # Shader / GLSL
    if any(w in desc for w in ["shader", "glsl", "gpu", "fragment", "pixel"]):
        suggestions.extend([
            {"family": "TOP", "type": "glslTOP", "reason": "Custom GLSL pixel shader"},
            {"family": "MAT", "type": "glslMAT", "reason": "Custom GLSL material"},
        ])

    # OSC / MIDI
    if any(w in desc for w in ["osc", "midi", "controller", "sensor"]):
        suggestions.extend([
            {"family": "CHOP", "type": "oscinCHOP", "reason": "Receive OSC messages"},
            {"family": "CHOP", "type": "midiinCHOP", "reason": "Receive MIDI input"},
        ])

    # Text / data
    if any(w in desc for w in ["text", "data", "table", "csv", "script"]):
        suggestions.extend([
            {"family": "DAT", "type": "textDAT", "reason": "Store/edit text"},
            {"family": "DAT", "type": "tableDAT", "reason": "Tabular data"},
            {"family": "TOP", "type": "textTOP", "reason": "Render text to texture"},
        ])

    # Disintegration / deconstruction
    if any(w in desc for w in ["disintegrat", "deconstruct", "dissolve", "scatter", "explode", "shatter"]):
        suggestions.extend([
            {"family": "SOP", "type": "scatterSOP", "reason": "Convert mesh to point cloud"},
            {"family": "SOP", "type": "noiseSOP", "reason": "Displace points for dissolution"},
            {"family": "SOP", "type": "sortSOP", "reason": "Randomize point order for staggered effect"},
            {"family": "MAT", "type": "glslMAT", "reason": "Custom GLSL for per-point displacement + fade"},
            {"family": "CHOP", "type": "lfoCHOP", "reason": "Drive disintegration progress over time"},
            {"family": "TOP", "type": "renderTOP", "reason": "Render the disintegrating scene"},
        ])

    # Feedback
    if any(w in desc for w in ["feedback", "trail", "echo", "delay"]):
        suggestions.extend([
            {"family": "TOP", "type": "feedbackTOP", "reason": "Create visual feedback loop"},
            {"family": "TOP", "type": "compositeTOP", "reason": "Blend feedback with source"},
            {"family": "TOP", "type": "levelTOP", "reason": "Fade feedback over time"},
        ])

    if not suggestions:
        suggestions = [
            {"family": "TOP", "type": "nullTOP", "reason": "General-purpose null (output)"},
            {"family": "CHOP", "type": "constantCHOP", "reason": "Control values"},
        ]

    return suggestions
