<div align="center">

# 🚀 Installation Guide

### Get `cli-anything-touchdesigner` running in under 2 minutes

</div>

---

## 📦 What You're Installing

| Component | Description |
|-----------|-------------|
| `cli-anything-touchdesigner` | Main CLI command — full TouchDesigner control from your terminal |
| `td-cli` | Shorthand alias — does exactly the same thing, fewer keystrokes |
| 103+ operator types | All 7 TD families: TOP, CHOP, SOP, DAT, COMP, MAT, POP |
| 8 network templates | Audio-reactive, feedback loops, 3D scenes, particles, and more |
| Interactive REPL | Branded shell for live agent sessions |

---

## ✅ Prerequisites

| Requirement | Version | Required? | Notes |
|-------------|---------|:---------:|-------|
| **Python** | 3.9+ | Yes | Check with `python3 --version` |
| **pip** | Any | Yes | Comes with Python |
| **git** | Any | Yes | Check with `git --version` |
| **TouchDesigner** | 2023+ | No | Only needed for rendering. Everything else works without it. |

> **Don't have Python?**
> - **macOS**: `brew install python`
> - **Windows**: Download from [python.org](https://www.python.org/downloads/)
> - **Linux**: `sudo apt install python3 python3-venv python3-pip`

---

## 🖥️ Installation by Platform

### macOS / Linux

```bash
# 1. Clone the repository
git clone https://github.com/superdwayne/touchdesigner-cli.git

# 2. Navigate to the package
cd touchdesigner-cli/agent-harness

# 3. Create a virtual environment
python3 -m venv .venv

# 4. Activate it
source .venv/bin/activate

# 5. Install (with dev/test dependencies)
pip install -e ".[dev]"

# 6. Verify
cli-anything-touchdesigner --version
```

### Windows (PowerShell)

```powershell
# 1. Clone the repository
git clone https://github.com/superdwayne/touchdesigner-cli.git

# 2. Navigate to the package
cd touchdesigner-cli\agent-harness

# 3. Create a virtual environment
python -m venv .venv

# 4. Activate it
.venv\Scripts\Activate.ps1

# 5. Install (with dev/test dependencies)
pip install -e ".[dev]"

# 6. Verify
cli-anything-touchdesigner --version
```

### Windows (CMD)

```cmd
git clone https://github.com/superdwayne/touchdesigner-cli.git
cd touchdesigner-cli\agent-harness
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e ".[dev]"
cli-anything-touchdesigner --version
```

---

## ⚡ One-Liner Install

For the impatient — copy, paste, done:

**macOS / Linux:**
```bash
git clone https://github.com/superdwayne/touchdesigner-cli.git && cd touchdesigner-cli/agent-harness && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]" && cli-anything-touchdesigner --version
```

**Windows PowerShell:**
```powershell
git clone https://github.com/superdwayne/touchdesigner-cli.git; cd touchdesigner-cli\agent-harness; python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -e ".[dev]"; cli-anything-touchdesigner --version
```

---

## ✅ Verify Your Installation

After installing, run these three commands to confirm everything works:

```bash
# 1. Check the CLI is on PATH
cli-anything-touchdesigner --version
# Expected: cli-anything-touchdesigner, version 1.0.0

# 2. Check available commands
cli-anything-touchdesigner --help
# Expected: Usage info with project, op, net, export, render, status

# 3. Check TouchDesigner backend detection
cli-anything-touchdesigner status
# Expected: Shows whether TD is found on your system

# 4. Run the test suite to confirm everything works
pytest -v
# Expected: 117 passed
```

If all four work, you're ready to go.

---

## 🔌 Optional: TouchDesigner Setup

TouchDesigner is **only needed for rendering**. Everything else — project management, operator configuration, network building, script generation — works without it.

If you want rendering support:

1. **Download** TouchDesigner from [derivative.ca](https://derivative.ca/download)
2. **Install** it to the default location for your platform
3. The CLI will **auto-discover** it:

| Platform | Auto-detected Path |
|----------|-------------------|
| macOS | `/Applications/Derivative/TouchDesigner.app/` |
| Windows | `C:\Program Files\Derivative\TouchDesigner\` |
| Linux | `/opt/Derivative/TouchDesigner/` |

**Custom install location?** Set an environment variable:

```bash
# macOS / Linux — add to ~/.zshrc or ~/.bashrc
export TOUCHDESIGNER_PATH="/your/custom/path/TouchDesigner"

# Windows — set in System Environment Variables or PowerShell
$env:TOUCHDESIGNER_PATH = "C:\Your\Custom\Path\TouchDesigner.exe"
```

Verify detection:
```bash
cli-anything-touchdesigner status
```

---

## 🔄 Updating

```bash
cd touchdesigner-cli
git pull origin main
cd agent-harness
pip install -e ".[dev]"
```

---

## 🗑️ Uninstalling

```bash
pip uninstall cli-anything-touchdesigner
# Then optionally delete the repo folder
```

---

## ❓ Troubleshooting

<details>
<summary><strong>"command not found: cli-anything-touchdesigner"</strong></summary>

Your virtual environment isn't activated. Run:
```bash
source touchdesigner-cli/agent-harness/.venv/bin/activate   # macOS/Linux
# or
touchdesigner-cli\agent-harness\.venv\Scripts\Activate.ps1  # Windows
```

</details>

<details>
<summary><strong>"externally-managed-environment" error</strong></summary>

You're trying to install without a virtual environment. Modern Python (3.12+) requires venvs:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

</details>

<details>
<summary><strong>"No module named click"</strong></summary>

The package wasn't installed properly. Re-run:
```bash
pip install -e ".[dev]"
```

</details>

<details>
<summary><strong>Tests fail</strong></summary>

Make sure you installed with dev dependencies:
```bash
pip install -e ".[dev]"    # Note the [dev] part
pytest -v
```

</details>

<details>
<summary><strong>TouchDesigner not detected</strong></summary>

The CLI works fine without TD — you just can't render. If you need rendering:
```bash
# Set the path manually
export TOUCHDESIGNER_PATH="/path/to/your/TouchDesigner"
cli-anything-touchdesigner status
```

</details>

---

<div align="center">

**Next step:** Read the [Agent Integration Guide](AGENTS.md) to connect this CLI to your AI agent.

[Back to README](../README.md)

</div>
