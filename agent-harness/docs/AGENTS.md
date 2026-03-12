<div align="center">

# 🤖 Agent Integration Guide

### Connect `cli-anything-touchdesigner` to Your AI Agent

**Claude Code · Cursor · Windsurf · Copilot · OpenClaw · Custom Agents**

</div>

---

## 🧠 How Agents Use This CLI

AI agents interact with software through **text commands** and **structured JSON output**. This CLI is purpose-built for that pattern:

```
┌─────────────┐     CLI command      ┌──────────────────────┐     TD script     ┌────────────────┐
│   AI Agent  │ ──────────────────→  │  td-cli              │ ───────────────→  │  TouchDesigner │
│  (LLM)      │ ←──────────────────  │  (this tool)         │ ←───────────────  │  (rendering)   │
└─────────────┘     JSON response    └──────────────────────┘     .toe file     └────────────────┘
```

**Every command** returns structured JSON with `--json`. Agents never need to parse human-readable tables — they get clean data they can reason over.

---

## 📋 Table of Contents

- [Claude Code](#-claude-code)
- [Cursor / Windsurf / AI IDEs](#-cursor--windsurf--ai-ides)
- [GitHub Copilot CLI](#-github-copilot-cli)
- [Custom Agents (Python)](#-custom-agents-python)
- [Custom Agents (Any Language)](#-custom-agents-any-language)
- [MCP Server Integration](#-mcp-server-integration)
- [Agent Prompt Templates](#-agent-prompt-templates)
- [Real-World Workflows](#-real-world-workflows)
- [Tips for Agent Developers](#-tips-for-agent-developers)

---

## 🟣 Claude Code

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) can run shell commands directly. After installing the CLI, Claude Code can use it immediately.

### Setup

Make sure the CLI is installed and accessible in your terminal:

```bash
# In your project directory
cd touchdesigner-cli/agent-harness
source .venv/bin/activate
which cli-anything-touchdesigner
# Should print a path — Claude Code can now use it
```

### How Claude Code discovers the CLI

Claude Code uses `which` and `--help` to discover tools:

```bash
which cli-anything-touchdesigner    # → confirms it's on PATH
cli-anything-touchdesigner --help   # → discovers all commands
cli-anything-touchdesigner op types # → discovers all operator types
```

### Example conversation with Claude Code

> **You:** Build me an audio-reactive TouchDesigner project that responds to bass frequencies

> **Claude Code runs:**
> ```bash
> cli-anything-touchdesigner --json project new BassReactive -o bass.json
> cli-anything-touchdesigner --json --project bass.json net template audio-reactive --audio-file input.wav
> cli-anything-touchdesigner --json --project bass.json op set /project1/spectrum1 highfreq 200
> cli-anything-touchdesigner --json --project bass.json op add TOP blur blur1 --param size=20
> cli-anything-touchdesigner --json --project bass.json net connect /project1/comp1 /project1/blur1
> cli-anything-touchdesigner --json --project bass.json export script -o bass_setup.py
> ```

### Add to your Claude Code system prompt

If you want to hint Claude Code to use this tool, add this to your project's `CLAUDE.md` or system instructions:

```markdown
## Available Tools

### TouchDesigner CLI
This project has `cli-anything-touchdesigner` installed for building
TouchDesigner projects from the command line.

Key commands:
- `cli-anything-touchdesigner --json project new <name> -o <file>` — Create projects
- `cli-anything-touchdesigner --json --project <file> op add <family> <type> <name>` — Add operators
- `cli-anything-touchdesigner --json --project <file> net template <template>` — Build from templates
- `cli-anything-touchdesigner --json --project <file> net connect <from> <to>` — Wire operators
- `cli-anything-touchdesigner --json --project <file> export script -o <file>` — Export TD script
- `cli-anything-touchdesigner op suggest <description>` — Get operator recommendations
- `cli-anything-touchdesigner net templates` — List network templates

Always use `--json` for structured output. Always use `--project <file>` to target a project.
```

---

## 🔵 Cursor / Windsurf / AI IDEs

AI-powered IDEs like **Cursor**, **Windsurf**, and **Cody** can run terminal commands on your behalf. The setup is the same — install the CLI and the agent discovers it.

### Setup for Cursor

1. Install the CLI in your project (see [INSTALL.md](INSTALL.md))
2. Open the project in Cursor
3. Add rules to `.cursorrules` in your project root:

```markdown
# .cursorrules

## TouchDesigner CLI

When asked to build TouchDesigner projects, use the `cli-anything-touchdesigner` CLI tool.

### Installation
The CLI is installed in `agent-harness/.venv/`. Activate with:
source agent-harness/.venv/bin/activate

### Usage Pattern
Always use --json flag for structured output:
cli-anything-touchdesigner --json <command>

### Available Templates
audio-reactive, feedback-loop, 3d-scene, particle-system,
instancing, glsl-shader, osc-receiver, video-mixer

### Operator Families
TOP (textures), CHOP (channels), SOP (geometry), DAT (data),
COMP (components), MAT (materials), POP (particles)
```

### Setup for Windsurf (Cascade)

Add to your global rules or `.windsurfrules`:

```markdown
## TouchDesigner CLI

`cli-anything-touchdesigner` is available for building TD projects.
Always activate the venv first: source agent-harness/.venv/bin/activate
Always use --json for machine-readable output.
Use `op suggest <description>` to find the right operators.
Use `net template <name>` to scaffold common workflows.
```

---

## 🟢 GitHub Copilot CLI

GitHub Copilot can suggest and run CLI commands. After installation, Copilot can invoke the CLI in terminal sessions:

```bash
# Copilot sees the CLI is available and can suggest:
?? create a touchdesigner project with a feedback loop

# Copilot generates:
cli-anything-touchdesigner project new FeedbackDemo -o demo.json
cli-anything-touchdesigner --project demo.json net template feedback-loop
cli-anything-touchdesigner --project demo.json export script -o demo_setup.py
```

---

## 🐍 Custom Agents (Python)

Build your own agent that uses the CLI as a tool. Here's a complete example:

### Using subprocess (simplest)

```python
import json
import subprocess

def td_cli(command: str, json_mode: bool = True) -> dict:
    """Run a td-cli command and return parsed output."""
    cmd = ["cli-anything-touchdesigner"]
    if json_mode:
        cmd.append("--json")
    cmd.extend(command.split())

    result = subprocess.run(cmd, capture_output=True, text=True)

    if json_mode and result.stdout.strip():
        return json.loads(result.stdout)
    return {"output": result.stdout, "error": result.stderr}


# --- Example: Build an audio-reactive project ---

# Create project
td_cli("project new AudioViz -o project.json")

# Build template
td_cli("--project project.json net template audio-reactive")

# Tweak parameters
td_cli("--project project.json op set /project1/noise1 amp 3.0")

# Get project info
info = td_cli("--project project.json project info")
print(f"Project has {info['operators']} operators")

# Export script
td_cli("--project project.json export script -o setup_td.py")
```

### Using as a Python library (direct import)

```python
from cli_anything_touchdesigner.project import ProjectManager
from cli_anything_touchdesigner.network import NetworkBuilder
from cli_anything_touchdesigner.operators import suggest_operators

# Create project
mgr = ProjectManager()
proj = mgr.new_project("AgentProject")

# Get operator suggestions from natural language
suggestions = suggest_operators("audio reactive particle visuals")
for s in suggestions:
    print(f"  {s['family']}: {s['type']} — {s['reason']}")

# Build a network from template
builder = NetworkBuilder(proj)
builder.build_audio_reactive(audio_file="music.wav")
builder.build_particle_system()

# Inspect the result
print(f"Operators: {len(proj.operators)}")
print(f"Connections: {len(proj.connections)}")

# Export
proj.save("agent_project.json")
script = proj.generate_td_script()
with open("setup_td.py", "w") as f:
    f.write(script)
```

### LangChain Tool

```python
from langchain.tools import tool
import subprocess, json

@tool
def touchdesigner_cli(command: str) -> str:
    """Run a TouchDesigner CLI command. Use this to create TD projects,
    add operators (TOP/CHOP/SOP/DAT/COMP/MAT/POP), connect networks,
    build from templates, and export scripts.

    Examples:
    - "project new MyViz -o viz.json"
    - "--project viz.json op add TOP noise noise1"
    - "--project viz.json net template audio-reactive"
    - "--project viz.json export script -o setup.py"
    - "op suggest audio reactive"
    - "net templates"
    """
    cmd = ["cli-anything-touchdesigner", "--json"] + command.split()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout or result.stderr

# Use in your LangChain agent
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
agent = initialize_agent(
    tools=[touchdesigner_cli],
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
)
agent.run("Create a TouchDesigner project with a 3D scene and particle system")
```

### CrewAI Tool

```python
from crewai.tools import tool
import subprocess, json

@tool("TouchDesigner CLI")
def td_tool(command: str) -> str:
    """Build TouchDesigner projects via CLI. Supports: project management,
    operator creation (TOP/CHOP/SOP/DAT/COMP/MAT/POP), network connections,
    templates (audio-reactive, feedback-loop, 3d-scene, particle-system,
    instancing, glsl-shader, osc-receiver, video-mixer), and script export."""
    cmd = ["cli-anything-touchdesigner", "--json"] + command.split()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout or result.stderr
```

---

## 🌐 Custom Agents (Any Language)

The CLI works from **any language** that can run shell commands and parse JSON.

### Node.js / TypeScript

```typescript
import { execSync } from 'child_process';

function tdCli(command: string): any {
  const result = execSync(
    `cli-anything-touchdesigner --json ${command}`,
    { encoding: 'utf-8' }
  );
  return JSON.parse(result);
}

// Create project
const project = tdCli('project new MyViz -o viz.json');
console.log(project); // { status: "success", data: { ... } }

// Build template
tdCli('--project viz.json net template feedback-loop');

// Export
tdCli('--project viz.json export script -o setup.py');
```

### Go

```go
package main

import (
    "encoding/json"
    "os/exec"
)

func tdCli(args ...string) (map[string]interface{}, error) {
    fullArgs := append([]string{"--json"}, args...)
    out, err := exec.Command("cli-anything-touchdesigner", fullArgs...).Output()
    if err != nil {
        return nil, err
    }
    var result map[string]interface{}
    json.Unmarshal(out, &result)
    return result, nil
}
```

### Rust

```rust
use std::process::Command;
use serde_json::Value;

fn td_cli(args: &[&str]) -> Result<Value, Box<dyn std::error::Error>> {
    let mut cmd_args = vec!["--json"];
    cmd_args.extend_from_slice(args);

    let output = Command::new("cli-anything-touchdesigner")
        .args(&cmd_args)
        .output()?;

    let json: Value = serde_json::from_slice(&output.stdout)?;
    Ok(json)
}
```

---

## 🔗 MCP Server Integration

You can wrap the CLI as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server so any MCP-compatible agent can use it:

### Quick MCP server (Python)

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import subprocess, json

server = Server("touchdesigner-cli")

@server.tool()
async def td_project_new(name: str, output: str = "") -> str:
    """Create a new TouchDesigner project."""
    cmd = ["cli-anything-touchdesigner", "--json", "project", "new", name]
    if output:
        cmd.extend(["-o", output])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@server.tool()
async def td_op_add(project: str, family: str, op_type: str, name: str) -> str:
    """Add an operator to a TouchDesigner project."""
    cmd = [
        "cli-anything-touchdesigner", "--json",
        "--project", project,
        "op", "add", family, op_type, name,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@server.tool()
async def td_net_template(project: str, template: str) -> str:
    """Build a network from a pre-built template.
    Templates: audio-reactive, feedback-loop, 3d-scene, particle-system,
    instancing, glsl-shader, osc-receiver, video-mixer"""
    cmd = [
        "cli-anything-touchdesigner", "--json",
        "--project", project,
        "net", "template", template,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@server.tool()
async def td_op_suggest(description: str) -> str:
    """Suggest operators for a workflow description."""
    cmd = [
        "cli-anything-touchdesigner", "--json",
        "op", "suggest",
    ] + description.split()
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@server.tool()
async def td_export_script(project: str, output: str) -> str:
    """Export a project as a TouchDesigner Python script."""
    cmd = [
        "cli-anything-touchdesigner", "--json",
        "--project", project,
        "export", "script", "-o", output,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout
```

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "touchdesigner": {
      "command": "python",
      "args": ["path/to/td_mcp_server.py"]
    }
  }
}
```

---

## 📝 Agent Prompt Templates

Copy-paste these into your agent's system prompt to give it full TouchDesigner CLI capabilities.

### Minimal (add to any agent)

```
You have access to `cli-anything-touchdesigner`, a CLI for building TouchDesigner projects.

Key commands:
  cli-anything-touchdesigner --json project new <name> -o <file.json>
  cli-anything-touchdesigner --json --project <file.json> op add <FAMILY> <type> <name>
  cli-anything-touchdesigner --json --project <file.json> net connect <from_path> <to_path>
  cli-anything-touchdesigner --json --project <file.json> net template <template_name>
  cli-anything-touchdesigner --json --project <file.json> export script -o <output.py>

Families: TOP, CHOP, SOP, DAT, COMP, MAT, POP
Templates: audio-reactive, feedback-loop, 3d-scene, particle-system,
           instancing, glsl-shader, osc-receiver, video-mixer

Always use --json for structured output.
```

### Full (comprehensive agent prompt)

```
## TouchDesigner CLI Tool

You have `cli-anything-touchdesigner` installed — a CLI for programmatically building
TouchDesigner projects. Use it whenever asked about real-time visuals, VJ setups,
interactive installations, audio-reactive art, projection mapping, or generative visuals.

### Workflow
1. Create a project:       --json project new <name> -o project.json
2. Add operators:           --json --project project.json op add <FAMILY> <type> <name>
3. Connect them:            --json --project project.json net connect <from> <to>
4. Or use a template:       --json --project project.json net template <template>
5. Tweak parameters:        --json --project project.json op set <path> <param> <value>
6. Export TD script:        --json --project project.json export script -o setup.py

### Operator Families (103+ types)
- TOP  — Textures/images on GPU (Noise, GLSL, Render, Composite, Feedback, Level, Blur...)
- CHOP — Channels/signals (LFO, Audio File In, OSC In, MIDI In, Math, Filter, Timer...)
- SOP  — 3D geometry (Sphere, Box, Grid, Noise, Transform, Copy, Merge...)
- DAT  — Data/text (Text, Table, Script, Web Server, OSC In, TCP/IP...)
- COMP — Components (Geometry, Camera, Light, Container, Window, Replicator...)
- MAT  — Materials (PBR, Phong, GLSL, Constant, Wireframe...)
- POP  — Particles on GPU (Generate, Force, Noise, Attrib, Kill, Render)

### Templates
- audio-reactive  — Audio → Spectrum → Visuals
- feedback-loop   — Classic feedback with transform + decay
- 3d-scene        — Geometry + Camera + Light → Render
- particle-system — GPU particles via POPs
- instancing      — Efficient multi-copy GPU rendering
- glsl-shader     — Custom pixel shader chain
- osc-receiver    — External control input
- video-mixer     — Multi-source video mixing

### Smart Suggestions
Ask for recommendations: cli-anything-touchdesigner --json op suggest <description>
Example: op suggest "audio reactive particles" → returns relevant operators

### Rules
- Always use --json flag
- Always use --project <file> to target a specific project
- Operator paths look like /project1/operatorName
- Same-family operators connect to each other (TOP→TOP, CHOP→CHOP, etc.)
```

---

## 🎯 Real-World Workflows

### Workflow 1: Agent builds a live VJ setup

```bash
# Agent creates project
cli-anything-touchdesigner --json project new LiveVJ -o vj.json

# Agent scaffolds the video mixer
cli-anything-touchdesigner --json --project vj.json net template video-mixer --input-count 4

# Agent adds audio-reactive layer
cli-anything-touchdesigner --json --project vj.json net template audio-reactive

# Agent adds a feedback loop for trails
cli-anything-touchdesigner --json --project vj.json net template feedback-loop

# Agent adds OSC control
cli-anything-touchdesigner --json --project vj.json net template osc-receiver --port 8000

# Agent exports the TD script
cli-anything-touchdesigner --json --project vj.json export script -o vj_setup.py
```

### Workflow 2: Agent creates an interactive installation

```bash
# Agent creates project
cli-anything-touchdesigner --json project new Installation -o install.json

# Agent builds 3D scene
cli-anything-touchdesigner --json --project install.json net template 3d-scene --geometry sphere

# Agent adds particle overlay
cli-anything-touchdesigner --json --project install.json net template particle-system

# Agent adds sensor input via OSC
cli-anything-touchdesigner --json --project install.json net template osc-receiver --port 7000

# Agent configures output window
cli-anything-touchdesigner --json --project install.json op add COMP window window1 --param winw=3840 --param winh=1080

# Agent exports
cli-anything-touchdesigner --json --project install.json export script -o installation.py
cli-anything-touchdesigner --json --project install.json export json -o installation.json
```

### Workflow 3: Agent iterates on a GLSL shader

```bash
# Agent scaffolds shader chain
cli-anything-touchdesigner --json project new ShaderLab -o shader.json
cli-anything-touchdesigner --json --project shader.json net template glsl-shader

# Agent writes custom shader code to the project
cli-anything-touchdesigner --json --project shader.json op set /project1/glsl_code text \
  "out vec4 fragColor;
   void main() {
     vec2 uv = vUV.st;
     vec3 col = 0.5 + 0.5*cos(iTime + uv.xyx + vec3(0,2,4));
     fragColor = TDOutputSwizzle(vec4(col, 1.0));
   }"

# Agent adjusts resolution
cli-anything-touchdesigner --json --project shader.json op set /project1/glsl1 outputresolution custom
cli-anything-touchdesigner --json --project shader.json op set /project1/glsl1 resolutionw 1920
cli-anything-touchdesigner --json --project shader.json op set /project1/glsl1 resolutionh 1080
```

---

## 💡 Tips for Agent Developers

### 1. Always use `--json`

```bash
# Good — agent gets structured data
cli-anything-touchdesigner --json op list

# Bad — agent has to parse human-readable tables
cli-anything-touchdesigner op list
```

### 2. Use `op suggest` before building

Let the CLI recommend operators instead of hardcoding:

```bash
cli-anything-touchdesigner --json op suggest "audio reactive particles with trails"
# Returns a ranked list of relevant operators
```

### 3. Use templates as starting points

Templates create 4-9 connected operators in one command. Start with a template and customize:

```bash
cli-anything-touchdesigner --json --project p.json net template audio-reactive
cli-anything-touchdesigner --json --project p.json op set /project1/noise1 amp 5.0
```

### 4. Chain commands for complex builds

```bash
# Create → Template → Customize → Export — all in sequence
cli-anything-touchdesigner --json project new P -o p.json && \
cli-anything-touchdesigner --json --project p.json net template feedback-loop && \
cli-anything-touchdesigner --json --project p.json op set /project1/transform1 rz 1.5 && \
cli-anything-touchdesigner --json --project p.json export script -o setup.py
```

### 5. Use the REPL for interactive sessions

If your agent framework supports long-running terminal sessions:

```bash
cli-anything-touchdesigner
# Agent now has a persistent session with undo/redo
```

### 6. Export both JSON and script

- **JSON** = portable project state (reload later, inspect programmatically)
- **Script** = paste directly into TouchDesigner's Python console

```bash
cli-anything-touchdesigner --json --project p.json export json -o project_state.json
cli-anything-touchdesigner --json --project p.json export script -o td_setup.py
```

---

<div align="center">

### Ready to build?

Install the CLI: **[Installation Guide](INSTALL.md)** · Full reference: **[README](../README.md)**

---

**Built with the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology**

_Making TouchDesigner agent-native, one command at a time._

</div>
