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
        self._step_x = 250
        self._step_y = 0
        self._row_height = 200
        self._template_gap = 350
        self._row_start_y = 0

        # Auto-detect starting Y from existing operators so new templates
        # never overlap with what's already in the project.
        self._auto_offset_from_existing()

    def _auto_offset_from_existing(self):
        """Set starting Y below all existing operators in the project."""
        max_y = -self._template_gap
        for op in self.project.operators.values():
            pos = op.get("position", [0, 0])
            if pos[1] > max_y:
                max_y = pos[1]
        if self.project.operators:
            self._next_y = max_y + self._template_gap
            self._row_start_y = self._next_y

    def _advance_position(self) -> List[int]:
        """Return the next position and advance the cursor."""
        pos = [self._next_x, self._next_y]
        self._next_x += self._step_x
        return pos

    def _new_row(self):
        """Move to a new row in the network layout."""
        self._next_x = 0
        self._next_y += self._row_height

    def _start_template(self):
        """Called at the start of each template to position below previous content."""
        max_y = self._row_start_y - self._template_gap
        for op in self.project.operators.values():
            pos = op.get("position", [0, 0])
            if pos[1] > max_y:
                max_y = pos[1]
        self._next_x = 0
        self._next_y = max_y + self._template_gap if self.project.operators else 0
        self._row_start_y = self._next_y

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
        self._start_template()

        chop_ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("ar_audioIn", "CHOP", "audiofileinCHOP", {"file": audio_file}),
            ("ar_spectrum", "CHOP", "audiospectrumCHOP", {}),
            ("ar_math", "CHOP", "mathCHOP", {"gain": 2.0}),
            ("ar_null_chop", "CHOP", "nullCHOP", {}),
        ]
        chop_chain = self.add_chain(chop_ops, parent)

        self._new_row()
        top_ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("ar_chopTo", "TOP", "choptoTOP", {}),
            ("ar_noise", "TOP", "noiseTOP", {"amp": 1.0}),
            ("ar_comp", "TOP", "compositeTOP", {"operand": "multiply"}),
            ("ar_level", "TOP", "levelTOP", {"brightness1": 1.5}),
            ("ar_out", "TOP", "nullTOP", {}),
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
        self._start_template()

        ops: List[Tuple[str, str, str, Optional[dict]]] = [
            ("fb_noise", "TOP", "noiseTOP", {"type": "random", "amp": 0.05}),
            ("fb_comp", "TOP", "compositeTOP", {"operand": "add"}),
            ("fb_transform", "TOP", "transformTOP", {"sx": 0.99, "sy": 0.99, "rz": 0.5}),
            ("fb_level", "TOP", "levelTOP", {"opacity": 0.98}),
            ("fb_feedback", "TOP", "feedbackTOP", {}),
            ("fb_out", "TOP", "nullTOP", {}),
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
        self._start_template()
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
        self._start_template()

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
        self._start_template()
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
        self._start_template()

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

    def build_disintegration(
        self,
        geometry: str = "sphere",
        parent: str = "/project1",
    ) -> List[dict]:
        """Build a disintegration effect — geometry breaks apart with noise and feedback.

        Chain: Geometry COMP (with noise SOP displacement) → Render TOP →
               Edge detect → Composite with feedback loop → Level → Output
        """
        self._start_template()
        created = []

        geo_types = {
            "sphere": "sphereSOP",
            "box": "boxSOP",
            "grid": "gridSOP",
            "torus": "torusSOP",
        }
        sop_type = geo_types.get(geometry, "sphereSOP")

        # Row 1: 3D scene components
        geo = self.project.add_operator(
            "dis_geo", "COMP", "geometryCOMP", parent, self._advance_position()
        )
        created.append(geo)

        cam = self.project.add_operator(
            "dis_cam", "COMP", "cameraCOMP", parent, self._advance_position()
        )
        created.append(cam)

        light = self.project.add_operator(
            "dis_light", "COMP", "lightCOMP", parent, self._advance_position()
        )
        created.append(light)

        # Row 2: Render + edge + noise texture
        self._new_row()
        render = self.project.add_operator(
            "dis_render", "TOP", "renderTOP", parent, self._advance_position()
        )
        created.append(render)

        edge = self.project.add_operator(
            "dis_edge", "TOP", "edgeTOP", parent, self._advance_position()
        )
        created.append(edge)
        self.project.connect(render["path"], edge["path"])

        noise_tex = self.project.add_operator(
            "dis_noise_tex", "TOP", "noiseTOP", parent, self._advance_position()
        )
        created.append(noise_tex)

        # Row 3: Compositing + feedback loop
        self._new_row()
        comp = self.project.add_operator(
            "dis_comp", "TOP", "compositeTOP", parent, self._advance_position()
        )
        created.append(comp)
        # edge + noise texture composited
        self.project.connect(edge["path"], comp["path"], to_index=0)
        self.project.connect(noise_tex["path"], comp["path"], to_index=1)

        feedback = self.project.add_operator(
            "dis_feedback", "TOP", "feedbackTOP", parent, self._advance_position()
        )
        created.append(feedback)

        transform = self.project.add_operator(
            "dis_transform", "TOP", "transformTOP", parent, self._advance_position()
        )
        created.append(transform)

        # Row 4: Final mix + output
        self._new_row()
        mix = self.project.add_operator(
            "dis_mix", "TOP", "compositeTOP", parent, self._advance_position()
        )
        created.append(mix)
        # comp + feedback trail
        self.project.connect(comp["path"], mix["path"], to_index=0)
        self.project.connect(feedback["path"], mix["path"], to_index=1)

        level = self.project.add_operator(
            "dis_level", "TOP", "levelTOP", parent, self._advance_position()
        )
        created.append(level)
        self.project.connect(mix["path"], level["path"])

        # Feedback loop: level → transform → feedback
        self.project.connect(level["path"], transform["path"])
        self.project.connect(transform["path"], feedback["path"])

        out = self.project.add_operator(
            "dis_out", "TOP", "nullTOP", parent, self._advance_position()
        )
        created.append(out)
        self.project.connect(level["path"], out["path"])

        # SOP inside geometry COMP: base shape + noise displacement
        sop = self.project.add_operator(
            f"dis_{geometry}", "SOP", sop_type, geo["path"], [0, 0]
        )
        created.append(sop)

        noise_sop = self.project.add_operator(
            "dis_noise_sop", "SOP", "noiseSOP", geo["path"], [250, 0]
        )
        created.append(noise_sop)
        self.project.connect(sop["path"], noise_sop["path"])

        null_sop = self.project.add_operator(
            "dis_null_sop", "SOP", "nullSOP", geo["path"], [500, 0]
        )
        created.append(null_sop)
        self.project.connect(noise_sop["path"], null_sop["path"])

        return created

    def build_osc_receiver(
        self,
        port: int = 7000,
        parent: str = "/project1",
    ) -> List[dict]:
        """Build an OSC input chain for external control."""
        self._start_template()

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
        self._start_template()
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
    "disintegration": "Geometry disintegration with noise displacement, edge detection, and feedback trails",
}
