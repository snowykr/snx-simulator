# SN/X Simulator

A Python toolchain (assembler, static analyzer, and simulator) for the **SN/X architecture**, a 16-bit educational RISC processor described in Naohiko Shimizu (清水尚彦)'s book *コンピュータ設計の基礎知識*.

## Features

- **Complete SN/X instruction set** — ADD, AND, SUB, SLT, NOT, SR, HLT, LD, ST, LDA, IN, OUT, BZ, BAL
- **Integrated static analysis** — CFG, dataflow analysis, memory bounds checking
- **CLI + Python API** — Use from command line or as a library
- **snxasm compatible** — Produces identical binary output to the original assembler

## Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [CLI Usage](#cli-usage)
- [Python API](#python-api)
- [Documentation](#documentation)
- [License](#license)

## Requirements

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended)
- [pipx](https://pipx.pypa.io/) (optional)

## Quick Start

**Option 1 — One-off execution (no install):**

```bash
# via uv (recommended)
uvx --from snx-simulator snx sample.s

# via pipx
pipx run --spec snx-simulator snx sample.s
```

**Option 2 — Global install (recommended for CLI usage):**

```bash
# via uv (recommended)
uv tool install snx-simulator

snx sample.s
```

```bash
# via pipx
pipx install snx-simulator

snx sample.s
```

**Option 3 — Install via pip (for an existing Python environment / venv):**

```bash
pip install snx-simulator
snx sample.s
```

## Installation

### Install uv (Recommended)

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Global Installation (uv)

Install `snx` as a system-wide command:

```bash
uv tool install snx-simulator
```

Or from a local clone (for development):

```bash
git clone https://github.com/snowykr/snx-simulator.git
cd snx-simulator
uv tool install .
```

If `snx` is not found after installation:

```bash
uv tool update-shell
```

To uninstall:

```bash
uv tool uninstall snx-simulator
```

### Global Installation (pipx)

Install `snx` as a system-wide command:

```bash
pipx install snx-simulator
```

If `snx` is not found after installation:

```bash
pipx ensurepath
```

To uninstall:

```bash
pipx uninstall snx-simulator
```

### Install via pip

```bash
pip install snx-simulator
```

### Project-local / Development Setup

For IDE integration or contributing:

```bash
git clone https://github.com/snowykr/snx-simulator.git
cd snx-simulator
uv sync
```

Then run with:

```bash
uv run snx sample.s
```

Or activate the virtual environment:

```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
snx sample.s
```

## CLI Usage

```
snx [-h] [-V] PATH
```

| Option | Description |
|--------|-------------|
| `PATH` | Path to an SN/X assembly source file (`.s`) |
| `-h, --help` | Show help message |
| `-V, --version` | Show version number |

**Examples:**

```bash
snx sample.s
snx path/to/program.s
uv run snx sample.s
```

The CLI will:
1. Parse and compile the assembly source
2. Run static analysis (errors and warnings)
3. If no errors, execute the program and display a trace table

## Python API

```python
from snx import compile_program, SNXSimulator

source = """
main:
    LDA $1, 5($0)
    HLT
"""

result = compile_program(source)
if result.has_errors():
    print(result.format_diagnostics())
    raise SystemExit(1)

sim = SNXSimulator.from_compile_result(result)
sim.run()
print(f"Final registers: {sim.regs}")
```

See [Python API documentation](https://github.com/snowykr/snx-simulator/blob/main/docs/python-api.md) for full reference.

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](https://github.com/snowykr/snx-simulator/blob/main/docs/architecture.md) | SN/X processor specifications, instruction formats, ISA reference |
| [Assembly Language](https://github.com/snowykr/snx-simulator/blob/main/docs/assembly-language.md) | Syntax, grammar, operand types |
| [Python API](https://github.com/snowykr/snx-simulator/blob/main/docs/python-api.md) | Library usage, `compile_program`, `SNXSimulator` |
| [Static Analysis](https://github.com/snowykr/snx-simulator/blob/main/docs/static-analysis.md) | Diagnostic codes, CFG, dataflow analysis |

## License

This project is open source. See the [LICENSE](LICENSE) file for details.
