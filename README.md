<div align="center">

# 🎛️ cli-touchdesigner

### Make TouchDesigner Agent-Native

**One CLI to create, manage, and render TouchDesigner projects — built for AI agents, automation pipelines, and headless workflows.**

Part of the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) ecosystem

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Tests: 117 passing](https://img.shields.io/badge/tests-117_passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](#-running-tests)
[![TouchDesigner](https://img.shields.io/badge/TouchDesigner-2025-FF6B35?style=for-the-badge)](https://derivative.ca)

---

**103+ Operators** · **8 Network Templates** · **Interactive REPL** · **JSON Output** · **Script Export**

[**Installation Guide**](agent-harness/docs/INSTALL.md) · [**Agent Integration Guide**](agent-harness/docs/AGENTS.md)

</div>

---

## 📋 Table of Contents

- [Why This Exists](#-why-this-exists)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Agent Integration](#-agent-integration)
- [REPL Mode](#-repl-mode)
- [Operator Families](#-operator-families)
- [Network Templates](#-network-templates)
- [JSON Mode for Agents](#-json-mode-for-agents)
- [Running Tests](#-running-tests)
- [Architecture](#-architecture)
- [TouchDesigner Backend](#-touchdesigner-backend)
- [License](#-license)

---

## 💡 Why This Exists

Today's creative software serves humans. Tomorrow's users will be **AI agents**.

TouchDesigner is one of the most powerful real-time visual programming environments — but it's locked behind a GUI. This CLI bridges the gap, letting agents like **Claude Code**, **Cursor**, **Copilot**, and any automation pipeline drive TouchDesigner programmatically.

> **No GUI required.** Build operator networks, configure parameters, generate TD scripts — all from the command line.

---

## 🚀 Installation

### Prerequisites

- **Python 3.9+**
- **TouchDesigner** _(optional — needed only for rendering; project management works standalone)_

### Step 1: Clone the repo

```bash
git clone https://github.com/superdwayne/touchdesigner-cli.git
cd touchdesigner-cli/agent-harness
```

### Step 2: Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### Step 3: Install the package

```bash
pip install -e ".[dev]"
```

> **Windows users:** If you hit a `UnicodeDecodeError`, run `$env:PYTHONUTF8="1"` (PowerShell) or `set PYTHONUTF8=1` (CMD) before the pip install command.

> This installs the CLI as `cli-anything-touchdesigner` and the shorthand `td-cli` on your PATH (inside the venv).

### Step 4: Verify it works

```bash
cli-anything-touchdesigner --version
# cli-anything-touchdesigner, version 1.0.0

cli-anything-touchdesigner --help
# Usage: cli-anything-touchdesigner [OPTIONS] COMMAND [ARGS]...

cli-anything-touchdesigner status
# Shows TouchDesigner backend detection status
```

<details>
<summary><strong>⚡ One-liner install (copy-paste)</strong></summary>

```bash
git clone https://github.com/superdwayne/touchdesigner-cli.git && \
cd touchdesigner-cli/agent-harness && \
python3 -m venv .venv && \
source .venv/bin/activate && \
pip install -e ".[dev]" && \
cli-anything-touchdesigner --version
```

</details>

> **Detailed platform-specific instructions (macOS, Linux, Windows):** [**docs/INSTALL.md**](agent-harness/docs/INSTALL.md)

---

## ⚡ Quick Start

### Create a project and build a network

```bash
# 1. Create a new project
cli-anything-touchdesigner project new MyVisuals -o myvisuals.json

# 2. Add operators
cli-anything-touchdesigner --project myvisuals.json op add TOP noise noise1 --param amp=2.0
cli-anything-touchdesigner --project myvisuals.json op add TOP level level1
cli-anything-touchdesigner --project myvisuals.json op add TOP null out1

# 3. Connect them into a chain
cli-anything-touchdesigner --project myvisuals.json net connect /project1/noise1 /project1/level1
cli-anything-touchdesigner --project myvisuals.json net connect /project1/level1 /project1/out1

# 4. Export as a TouchDesigner Python script
cli-anything-touchdesigner --project myvisuals.json export script -o setup.py
```

### Build entire networks with one command

```bash
# Audio-reactive visualization
cli-anything-touchdesigner --project myvisuals.json net template audio-reactive --audio-file music.wav

# Feedback loop
cli-anything-touchdesigner --project myvisuals.json net template feedback-loop

# 3D scene with sphere geometry
cli-anything-touchdesigner --project myvisuals.json net template 3d-scene --geometry sphere

# GPU particle system
cli-anything-touchdesigner --project myvisuals.json net template particle-system

# Custom GLSL shader chain
cli-anything-touchdesigner --project myvisuals.json net template glsl-shader

# List all available templates
cli-anything-touchdesigner net templates
```

### Get smart operator suggestions

```bash
cli-anything-touchdesigner op suggest audio reactive visuals
# ┌──────────────────────────────────────────────────────────┐
# │  Family  Type               Reason                       │
# │  CHOP    audiofileinCHOP    Load audio file              │
# │  CHOP    audiospectrumCHOP  Analyze frequency spectrum   │
# │  CHOP    mathCHOP           Scale/offset audio values    │
# │  TOP     choptoTOP          Convert audio data to texture│
# └──────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Integration

This CLI is designed to be used by **AI agents**. Full guide: **[docs/AGENTS.md](agent-harness/docs/AGENTS.md)**

### Works with every major agent platform

| Platform | How It Works |
|----------|-------------|
| **Claude Code** | Discovers via `which` and `--help`. Add hints to `CLAUDE.md`. |
| **Cursor** | Add to `.cursorrules` for automatic discovery. |
| **Windsurf** | Add to `.windsurfrules` or global rules. |
| **Copilot CLI** | Suggests commands from `??` queries. |
| **LangChain** | Wrap as a `@tool` — [example in AGENTS.md](agent-harness/docs/AGENTS.md#-custom-agents-python). |
| **CrewAI** | Wrap as a `@tool` — [example in AGENTS.md](agent-harness/docs/AGENTS.md#-custom-agents-python). |
| **MCP Server** | Expose as MCP tools — [example in AGENTS.md](agent-harness/docs/AGENTS.md#-mcp-server-integration). |
| **Any language** | Shell out + parse JSON — [Node/Go/Rust examples](agent-harness/docs/AGENTS.md#-custom-agents-any-language). |

### Minimal agent prompt (copy-paste into your agent)

```
You have access to `cli-anything-touchdesigner`, a CLI for building TouchDesigner projects.

Key commands:
  cli-anything-touchdesigner --json project new <name> -o <file.json>
  cli-anything-touchdesigner --json --project <file> op add <FAMILY> <type> <name>
  cli-anything-touchdesigner --json --project <file> net template <template_name>
  cli-anything-touchdesigner --json --project <file> net connect <from> <to>
  cli-anything-touchdesigner --json --project <file> export script -o <output.py>
  cli-anything-touchdesigner op suggest <description>

Families: TOP, CHOP, SOP, DAT, COMP, MAT, POP
Templates: audio-reactive, feedback-loop, 3d-scene, particle-system,
           instancing, glsl-shader, osc-receiver, video-mixer

Always use --json for structured output.
```

> **Full integration guide with code examples for every platform:** **[docs/AGENTS.md](agent-harness/docs/AGENTS.md)**

---

## 🎮 REPL Mode

Run the CLI without a subcommand to enter **interactive mode** — perfect for AI agent sessions:

```
$ cli-anything-touchdesigner

╔══════════════════════════════════════════════════╗
║  cli-anything-touchdesigner v1.0.0              ║
║  TouchDesigner CLI for AI Agents                 ║
╚══════════════════════════════════════════════════╝

td> project new LiveShow
✓ Created project: LiveShow

td[LiveShow]> net template audio-reactive --audio-file set.wav
✓ Built template 'audio-reactive' (9 operators)

td[LiveShow]*> op list
  Name          Family  Type               Path
  ─────────     ──────  ────               ────
  audioIn1      CHOP    audiofileinCHOP    /project1/audioIn1
  spectrum1     CHOP    audiospectrumCHOP  /project1/spectrum1
  math1         CHOP    mathCHOP           /project1/math1
  null_chop1    CHOP    nullCHOP           /project1/null_chop1
  chopTo1       TOP     choptoTOP          /project1/chopTo1
  noise1        TOP     noiseTOP           /project1/noise1
  comp1         TOP     compositeTOP       /project1/comp1
  level1        TOP     levelTOP           /project1/level1
  out1          TOP     nullTOP            /project1/out1

td[LiveShow]*> op set /project1/noise1 amp 3.0
✓ Set amp=3.0 on /project1/noise1

td[LiveShow]*> export script -o live_setup.py
✓ Exported TD script: live_setup.py

td[LiveShow]*> exit
Goodbye! 👋
```

> The `*` after the project name means there are unsaved changes. REPL supports full **command history** (up/down arrows) and **undo/redo**.

---

## 🎨 Operator Families

All **7 TouchDesigner operator families** are supported with **103+ operator types**:

| Family | Color | Purpose | Types |
|:------:|:-----:|---------|:-----:|
| 🟣 **TOP** | Purple | Texture/image processing on GPU | 21 |
| 🟢 **CHOP** | Green | Channel data — audio, animation, control signals | 22 |
| 🔵 **SOP** | Blue | 3D surface & geometry operations | 16 |
| 🔷 **DAT** | Teal | Text, tables, scripts, networking | 16 |
| ⚪ **COMP** | Gray | Components — containers, 3D objects, UI | 14 |
| 🟡 **MAT** | Yellow | Materials & shaders for 3D rendering | 8 |
| 🩷 **POP** | Pink | GPU-accelerated particles & point data | 6 |

```bash
# List all families and counts
cli-anything-touchdesigner op types

# List all operator types in a family
cli-anything-touchdesigner op types TOP
cli-anything-touchdesigner op types CHOP
cli-anything-touchdesigner op types POP
```

---

## 🧩 Network Templates

Pre-built operator networks for common TouchDesigner workflows:

| Template | Description | Operators |
|----------|-------------|:---------:|
| `audio-reactive` | Audio File In → Spectrum → Math → CHOP to TOP → Composite | 9 |
| `feedback-loop` | Noise → Composite ← Feedback ← Transform ← Level (loop) | 6 |
| `3d-scene` | Geometry + Camera + Light → Render TOP → Null | 6 |
| `particle-system` | POP Generate → Force → Noise → Attrib → Render | 5 |
| `instancing` | Noise CHOPs (tx/ty/tz) → Merge → Geometry COMP | 6 |
| `glsl-shader` | Noise → GLSL TOP → Level → Null + shader DAT | 5 |
| `osc-receiver` | OSC In → Select → Filter → Null | 4 |
| `video-mixer` | Movie File In ×N → Switch → Composite → Null | 5+ |

```bash
# Build any template
cli-anything-touchdesigner --project my.json net template feedback-loop

# Customize with options
cli-anything-touchdesigner --project my.json net template 3d-scene --geometry torus
cli-anything-touchdesigner --project my.json net template instancing --count 500
cli-anything-touchdesigner --project my.json net template video-mixer --input-count 4
cli-anything-touchdesigner --project my.json net template osc-receiver --port 9000
```

---

## 🤖 JSON Mode for Agents

Every command supports `--json` for structured machine-readable output — ideal for AI agents:

```bash
# Create a project
cli-anything-touchdesigner --json project new AgentProject
```
```json
{
  "status": "success",
  "message": "Created project: AgentProject",
  "data": {
    "name": "AgentProject",
    "type": "standard",
    "operators": 0,
    "connections": 0,
    "families": {},
    "resolution": [1920, 1080],
    "fps": 60,
    "modified": false
  }
}
```

```bash
# List operators
cli-anything-touchdesigner --json --project myvisuals.json op list
```
```json
[
  {"name": "noise1", "family": "TOP", "type": "noiseTOP", "path": "/project1/noise1"},
  {"name": "null1", "family": "TOP", "type": "nullTOP", "path": "/project1/null1"}
]
```

```bash
# Get operator suggestions
cli-anything-touchdesigner --json op suggest particle effects
```
```json
[
  {"family": "POP", "type": "popGeneratePOP", "reason": "Generate particles"},
  {"family": "POP", "type": "popForcePOP", "reason": "Apply forces to particles"},
  {"family": "POP", "type": "popRenderPOP", "reason": "Render particles"}
]
```

---

## 🧪 Running Tests

The project includes **117 comprehensive tests** covering all modules:

### Quick run

```bash
cd agent-harness
source .venv/bin/activate
pytest -v
```

### Expected output

```
tests/test_cli.py       ...  28 passed
tests/test_operators.py ...  29 passed
tests/test_network.py   ...  22 passed
tests/test_project.py   ...  38 passed

========================= 117 passed =========================
```

### With coverage

```bash
pytest --cov=cli_anything_touchdesigner --cov-report=term-missing -v
```

### Run specific tests

```bash
pytest tests/test_project.py -v     # Project management tests
pytest tests/test_operators.py -v   # Operator registry tests
pytest tests/test_network.py -v     # Network builder tests
pytest tests/test_cli.py -v         # CLI integration tests
```

### Test breakdown

| Test File | Tests | What It Covers |
|-----------|:-----:|----------------|
| `test_project.py` | 38 | Project CRUD, undo/redo, save/load, connections, flags |
| `test_operators.py` | 29 | Operator registry, type lookup, defaults, suggestions |
| `test_network.py` | 22 | Templates, chain building, custom parents, all 8 templates |
| `test_cli.py` | 28 | CLI commands, JSON output, export, status, end-to-end |

---

## 🏗️ Architecture

```
touchdesigner-cli/
└── agent-harness/
    ├── cli_anything_touchdesigner/
    │   ├── __init__.py        # Package metadata & version
    │   ├── cli.py             # Click CLI — all subcommands + entry point
    │   ├── project.py         # Project/session state with undo/redo
    │   ├── operators.py       # 103+ operator types across 7 families
    │   ├── network.py         # Network builder + 8 pre-built templates
    │   ├── backend.py         # TouchDesigner process discovery & execution
    │   ├── formatter.py       # Human-readable tables + JSON output
    │   └── repl_skin.py       # Interactive REPL with history & prompts
    │
    ├── tests/
    │   ├── test_project.py    # 38 tests — project management
    │   ├── test_operators.py  # 29 tests — operator registry
    │   ├── test_network.py    # 22 tests — network templates
    │   └── test_cli.py        # 28 tests — CLI integration
    │
    ├── docs/
    │   ├── INSTALL.md         # Detailed installation guide
    │   └── AGENTS.md          # Agent integration guide
    │
    ├── setup.py               # Legacy setup config
    ├── pyproject.toml         # Modern Python packaging
    └── README.md              # Package README
```

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Authentic Integration** | Generates valid TD Python scripts. Delegates to real TouchDesigner for rendering. Builds interfaces _to_ software, not replacements. |
| **Dual Interaction** | Stateful REPL for interactive agent sessions + subcommand interface for scripting and pipelines. |
| **Agent-Native** | `--json` on every command. Self-describing via `--help`. Discoverable via `which`. |
| **Zero Compromise** | Real TD required for rendering. No toy implementations. Tests fail (not skip) when backends are missing. |

---

## 🔌 TouchDesigner Backend

The CLI **auto-discovers** TouchDesigner on your system:

| Platform | Search Paths |
|----------|-------------|
| **macOS** | `/Applications/Derivative/TouchDesigner.app/` |
| **Windows** | `C:\Program Files\Derivative\TouchDesigner\` |
| **Linux** | `/opt/Derivative/TouchDesigner/` |

You can also set environment variables:

```bash
export TOUCHDESIGNER_PATH="/path/to/TouchDesigner"
export TOUCHDESIGNER_BATCH_PATH="/path/to/TouchDesignerBatch"
```

> **TouchDesigner is optional.** Project management, operator configuration, network building, and script generation all work without TD installed. You only need TD for rendering.

---

## 🗺️ Command Reference

```
cli-anything-touchdesigner
├── project
│   ├── new <name>                Create a new project
│   ├── open <path>               Open an existing project
│   ├── save [-o path]            Save current project
│   └── info                      Show project info
│
├── op
│   ├── add <family> <type> <name>   Add an operator
│   ├── remove <path>                Remove an operator
│   ├── list [--family FAM]          List operators
│   ├── info <path>                  Show operator details
│   ├── set <path> <param> <val>     Set parameter
│   ├── get <path> <param>           Get parameter
│   ├── flag <path> <flag> <bool>    Set operator flag
│   ├── types [family]               List available types
│   └── suggest <description...>     Get smart suggestions
│
├── net
│   ├── connect <from> <to>          Connect operators
│   ├── disconnect <from> <to>       Disconnect operators
│   ├── list [op_path]               List connections
│   ├── template <name> [options]    Build from template
│   └── templates                    List all templates
│
├── export
│   ├── script [-o path]             Export TD Python script
│   └── json [-o path]               Export project as JSON
│
├── render <output> [options]         Render via TouchDesigner
└── status                            Show backend status
```

---

## 📄 License

MIT — use it however you want.

---

<div align="center">

**Built with the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology**

_Making TouchDesigner agent-native, one command at a time._

</div>
