"""Network builder for TouchDesigner operator chains.

Provides high-level helpers for constructing common TD network patterns
(audio-reactive, feedback loops, 3D scenes, etc.) as composable templates.
"""

from typing import Any, Dict, List, Optional, Tuple

from .project import TDProject


class NetworkBuilder:
    """Builds operator networks from templates and descriptions."""

    def __init__(self, project: TDProject):
        self.project = project
        self._next_x = 0
        self._next_y = 0
        self._step_x = 200
        self._step_y = 0

    def _advance_position(self) -> List[int]:
        """Return the next position and advance the cursor."""
        pos = [self._next_x, self._next_y]
        self._next_x += self._step_x
        return pos

    def _new_row(self):
        """Move to a new row in the network layout."""
        self._next_x = 0
        self._next_y += 150

    def add_chain(
        self,
        ops: List[Tuple[str, str, str, Optional[dict]]],
        parent: str = "/project1",
        auto_connect: bool = True,
    ) -> List[dict]:
        """Add a chain of operators and optionally connect them sequentially.

        Args:
            ops: List of (name, family, op_type, params) tuples.
            parent: Parent component path.
            auto_connect: Wire each operator to the next.

        Returns:
            List of created operator dicts.
        """
        created = []
        for name, family, op_type, params in ops:
            pos = self._advance_position()
            op = self.project.add_operator(
                name=name,
                family=family,
                op_type=op_type,
                parent=parent,
                position=pos,
                params=params or {},
            )
            created.append(op)

        if auto_connect and len(created) > 1:
            for i in range(len(created) - 1):
                try:
                    self.project.connect(
                        created[i]["path"], created[i + 1]["path"]
                    )
                except ValueError:
                    # Cross-family connections not allowed; skip silently
                    pass

        return created

    # ------------------------------------------------------------------
    # Pre-built templates
    # ------------------------------------------------------------------

    def build_audio_reactive(
        self,
        audio_file: str = "",
        parent: str = "/project1",
    ) -> List[dict]:
        """Build an audio-reactive visualization chain.

        Chain: Audio File In → Audio Spectrum → Math → CHOP to TOP → Noise TOP (composite)
        """
        self._next_x = 0
        self._next_y = 0

        chop_ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("audioIn1", "CHOP", "audiofileinCHOP", {"file": audio_file}),
            ("spectrum1", "CHOP", "audiospectrumCHOP", {}),
            ("math1", "CHOP", "mathCHOP", {"gain": 2.0}),
            ("null_chop1", "CHOP", "nullCHOP", {}),
        ]
        chop_chain = self.add_chain(chop_ops, parent)

        self._new_row()
        top_ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("chopTo1", "TOP", "choptoTOP", {}),
            ("noise1", "TOP", "noiseTOP", {"amp": 1.0}),
            ("comp1", "TOP", "compositeTOP", {"operand": "multiply"}),
            ("level1", "TOP", "levelTOP", {"brightness1": 1.5}),
            ("out1", "TOP", "nullTOP", {}),
        ]
        top_chain = self.add_chain(top_ops, parent)

        return chop_chain + top_chain

    def build_feedback_loop(
        self,
        parent: str = "/project1",
    ) -> List[dict]:
        """Build a classic feedback loop pattern.

        Chain: Noise → Composite ← Feedback ← Level ← (loops back to Composite)
        """
        self._next_x = 0
        self._next_y = 0

        ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("noise1", "TOP", "noiseTOP", {"type": "random", "amp": 0.05}),
            ("comp1", "TOP", "compositeTOP", {"operand": "add"}),
            ("transform1", "TOP", "transformTOP", {"sx": 0.99, "sy": 0.99, "rz": 0.5}),
            ("level1", "TOP", "levelTOP", {"opacity": 0.98}),
            ("feedback1", "TOP", "feedbackTOP", {}),
            ("out1", "TOP", "nullTOP", {}),
        ]
        chain = self.add_chain(ops, parent, auto_connect=False)

        # Manual wiring for feedback loop
        paths = [op["path"] for op in chain]
        # noise → comp input 0
        self.project.connect(paths[0], paths[1], 0, 0)
        # feedback → comp input 1
        self.project.connect(paths[4], paths[1], 0, 1)
        # comp → transform
        self.project.connect(paths[1], paths[2])
        # transform → level
        self.project.connect(paths[2], paths[3])
        # level → feedback (target)
        self.project.connect(paths[3], paths[4])
        # comp → out (display)
        self.project.connect(paths[1], paths[5])

        return chain

    def build_3d_scene(
        self,
        geometry: str = "box",
        parent: str = "/project1",
    ) -> List[dict]:
        """Build a basic 3D rendering scene.

        Components: Geometry + Camera + Light → Render TOP
        """
        self._next_x = 0
        self._next_y = 0
        created = []

        geo_types = {
            "box": ("boxSOP", {}),
            "sphere": ("sphereSOP", {"rows": 30, "cols": 30}),
            "grid": ("gridSOP", {"rows": 20, "cols": 20}),
            "torus": ("torusSOP", {"rows": 20, "cols": 20}),
        }
        sop_type, sop_params = geo_types.get(geometry, ("boxSOP", {}))

        # SOP inside geo1
        geo = self.project.add_operator(
            "geo1", "COMP", "geometryCOMP", parent, self._advance_position()
        )
        created.append(geo)

        cam = self.project.add_operator(
            "cam1", "COMP", "cameraCOMP", parent, self._advance_position(),
            {"tx": 0, "ty": 1, "tz": 5},
        )
        created.append(cam)

        light = self.project.add_operator(
            "light1", "COMP", "lightCOMP", parent, self._advance_position(),
            {"lighttype": "point", "tx": 2, "ty": 3, "tz": 2},
        )
        created.append(light)

        self._new_row()

        render = self.project.add_operator(
            "render1", "TOP", "renderTOP", parent, self._advance_position(),
            {"resolutionw": 1920, "resolutionh": 1080},
        )
        created.append(render)

        out = self.project.add_operator(
            "out1", "TOP", "nullTOP", parent, self._advance_position(),
        )
        created.append(out)
        self.project.connect(render["path"], out["path"])

        # Add the SOP inside geo
        sop = self.project.add_operator(
            f"{geometry}1", "SOP", sop_type, geo["path"],
            [0, 0], sop_params,
        )
        created.append(sop)

        return created

    def build_particle_system(
        self,
        parent: str = "/project1",
    ) -> List[dict]:
        """Build a GPU-accelerated particle system using POPs."""
        self._next_x = 0
        self._next_y = 0

        pop_ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("popGen1", "POP", "popGeneratePOP", {"birthrate": 500}),
            ("popForce1", "POP", "popForcePOP", {}),
            ("popNoise1", "POP", "popNoisePOP", {"amp": 0.3}),
            ("popAttrib1", "POP", "popAttribPOP", {}),
            ("popRender1", "POP", "popRenderPOP", {}),
        ]
        return self.add_chain(pop_ops, parent)

    def build_instancing(
        self,
        geometry: str = "sphere",
        count: int = 100,
        parent: str = "/project1",
    ) -> List[dict]:
        """Build a GPU instancing setup."""
        self._next_x = 0
        self._next_y = 0
        created = []

        # CHOP chain for instance transforms
        chop_ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("noise_tx", "CHOP", "noiseCHOP", {"type": "sparse", "amp": 5, "channels": f"tx[0-{count-1}]"}),
            ("noise_ty", "CHOP", "noiseCHOP", {"type": "sparse", "amp": 5, "channels": f"ty[0-{count-1}]"}),
            ("noise_tz", "CHOP", "noiseCHOP", {"type": "sparse", "amp": 5, "channels": f"tz[0-{count-1}]"}),
            ("merge1", "CHOP", "mergeCHOP", {}),
            ("null_inst", "CHOP", "nullCHOP", {}),
        ]
        chop_chain = self.add_chain(chop_ops, parent, auto_connect=False)
        # Connect noise → merge
        for i in range(3):
            self.project.connect(chop_chain[i]["path"], chop_chain[3]["path"], 0, i)
        self.project.connect(chop_chain[3]["path"], chop_chain[4]["path"])
        created.extend(chop_chain)

        self._new_row()

        geo = self.project.add_operator(
            "geo_inst", "COMP", "geometryCOMP", parent, self._advance_position(),
            {"instancechop": chop_chain[4]["path"]},
        )
        created.append(geo)

        return created

    def build_glsl_shader(
        self,
        shader_code: str = "",
        parent: str = "/project1",
    ) -> List[dict]:
        """Build a GLSL shader chain: Noise → GLSL → Level → Null."""
        self._next_x = 0
        self._next_y = 0

        default_shader = (
            "out vec4 fragColor;\n"
            "void main() {\n"
            "    vec4 color = texture(sTD2DInputs[0], vUV.st);\n"
            "    color.rgb = 1.0 - color.rgb;\n"
            "    fragColor = TDOutputSwizzle(color);\n"
            "}\n"
        )

        ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("noise1", "TOP", "noiseTOP", {"amp": 1.0, "period": 2.0}),
            ("glsl1", "TOP", "glslTOP", {"pixeldat": "glsl_code"}),
            ("level1", "TOP", "levelTOP", {}),
            ("out1", "TOP", "nullTOP", {}),
        ]
        chain = self.add_chain(ops, parent)

        # Add shader code DAT
        self._new_row()
        shader_dat = self.project.add_operator(
            "glsl_code", "DAT", "textDAT", parent, self._advance_position(),
            {"text": shader_code or default_shader},
        )
        chain.append(shader_dat)

        return chain

    def build_osc_receiver(
        self,
        port: int = 7000,
        parent: str = "/project1",
    ) -> List[dict]:
        """Build an OSC input chain for external control."""
        self._next_x = 0
        self._next_y = 0

        ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("oscIn1", "CHOP", "oscinCHOP", {"port": port}),
            ("select1", "CHOP", "selectCHOP", {}),
            ("filter1", "CHOP", "filterCHOP", {"filtertype": "lowpass", "cutofffreq": 5}),
            ("null_osc", "CHOP", "nullCHOP", {}),
        ]
        return self.add_chain(ops, parent)

    def build_video_mixer(
        self,
        input_count: int = 2,
        parent: str = "/project1",
    ) -> List[dict]:
        """Build a multi-input video mixer."""
        self._next_x = 0
        self._next_y = 0
        created = []

        inputs = []
        for i in range(input_count):
            inp = self.project.add_operator(
                f"movieIn{i+1}", "TOP", "moviefileinTOP", parent,
                self._advance_position(), {"file": ""},
            )
            inputs.append(inp)
            created.append(inp)

        self._new_row()

        switch = self.project.add_operator(
            "switch1", "TOP", "switchTOP", parent,
            self._advance_position(), {"index": 0},
        )
        created.append(switch)

        for i, inp in enumerate(inputs):
            self.project.connect(inp["path"], switch["path"], 0, i)

        comp = self.project.add_operator(
            "comp1", "TOP", "compositeTOP", parent,
            self._advance_position(), {"operand": "over"},
        )
        created.append(comp)
        self.project.connect(switch["path"], comp["path"])

        out = self.project.add_operator(
            "out1", "TOP", "nullTOP", parent, self._advance_position(),
        )
        created.append(out)
        self.project.connect(comp["path"], out["path"])

        return created


# Available template names and descriptions
TEMPLATES = {
    "audio-reactive": "Audio-reactive visualization (audio → spectrum → visuals)",
    "feedback-loop": "Classic feedback loop with transform and decay",
    "3d-scene": "Basic 3D scene with geometry, camera, light, and render",
    "particle-system": "GPU-accelerated particle system using POPs",
    "instancing": "GPU instancing for rendering many copies efficiently",
    "glsl-shader": "Custom GLSL shader chain with input",
    "osc-receiver": "OSC input chain for external control",
    "video-mixer": "Multi-input video mixer with switch and composite",
}
