# Python API

This document describes how to use SN/X Simulator as a Python library.

## Installation

```bash
uv add snx-simulator
# or
pip install snx-simulator
```

## Quick Example

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

## `compile_program`

```python
compile_program(
    source: str,
    *,
    reg_count: int = DEFAULT_REG_COUNT,
    mem_size: int = DEFAULT_MEM_SIZE,
    run_static_checks: bool = True
) -> CompileResult
```

Parses and analyzes the source program.

**Parameters:**
- `source`: SN/X assembly source code as a string.
- `reg_count`: Number of registers for static analysis (default: 4).
- `mem_size`: Memory size for static analysis (default: 2^16 = 65536).
- `run_static_checks`: Whether to run static analysis (default: `True`).

**Returns:** `CompileResult` containing:
- `program`: High-level AST (`Program`) or `None` on failure.
- `ir`: Lowered `IRProgram` or `None` if analysis failed.
- `diagnostics`: List of all errors and warnings.
- `reg_count`: The register count used for static analysis.
- `mem_size`: The memory size used for static analysis.
- `cfg`: The control-flow graph (when static checks are enabled).
- `dataflow`: Dataflow analysis result (when static checks are enabled).
- `typed_symbols`: A dictionary mapping label names to `TypedSymbol` objects, containing domain (CODE/DATA) and address information.
- `initial_data_image`: A tuple of `DataImageWord` objects representing the initial DMEM state preloaded from `DW` directives.

**Helper methods:**
- `has_errors()`: Returns `True` if any error diagnostics exist.
- `has_warnings()`: Returns `True` if any warning diagnostics exist.
- `format_diagnostics()`: Returns a formatted string of all diagnostics.

**Default constants** are defined in `snx/constants.py`:
- `DEFAULT_REG_COUNT = 4`
- `DEFAULT_MEM_SIZE = 2 ** 16` (65536 words)

## `SNXSimulator`

### `SNXSimulator.from_compile_result`

```python
SNXSimulator.from_compile_result(
    result: CompileResult,
    *,
    mem_size: int = DEFAULT_MEM_SIZE,
    trace_callback=None,
    input_fn=None,
    output_fn=None,
    oob_callback=None
) -> SNXSimulator
```

Creates a simulator from an existing `CompileResult`.

- Raises `ValueError` if the result contains errors or has no IR.
- Uses `result.reg_count` to configure the simulator's register count.
- **Preloads DMEM** with initial data images from `DW` directives if present.

### `SNXSimulator.from_source`

```python
SNXSimulator.from_source(
    source: str,
    *,
    reg_count: int = DEFAULT_REG_COUNT,
    mem_size: int = DEFAULT_MEM_SIZE,
    trace_callback=None,
    input_fn=None,
    output_fn=None,
    oob_callback=None
) -> SNXSimulator
```

Convenience method that internally calls `compile_program` then `from_compile_result`.

- Raises `ValueError` if compilation or static analysis reports any errors.

## Recommended Pattern: Compile Once, Reuse IR

When you want to display diagnostics before running the simulator, use `compile_program` followed by `from_compile_result` to avoid compiling twice:

```python
from snx import compile_program, SNXSimulator

source = """
main:
    LDA $1, 5($0)
    HLT
"""

result = compile_program(source)
print(result.format_diagnostics())

if result.has_errors():
    raise SystemExit(1)

sim = SNXSimulator.from_compile_result(result)
sim.run()
print(f"Final registers: {sim.regs}")
```

## I/O Callbacks

The simulator supports `IN` and `OUT` instructions via callback functions:

```python
from snx import SNXSimulator

def my_input() -> int:
    return int(input("Enter value: "))

def my_output(value: int) -> None:
    print(f"Output: {value}")

sim = SNXSimulator.from_source(source, input_fn=my_input, output_fn=my_output)
sim.run()

print(sim.get_output_buffer())
```

- **IN:** Reads a 16-bit value from `input_fn()`. Returns 0 if no callback is set.
- **OUT:** Writes a 16-bit value via `output_fn()`. Values are also stored in an internal buffer accessible via `get_output_buffer()`.

## OOB Callback

For dynamic addresses, out-of-bounds access cannot be detected at compile time. Use `oob_callback` to receive notifications:

```python
from snx import SNXSimulator

def log_oob(kind, addr, pc, inst_text, mem_size):
    print(f"[OOB] {kind} at addr={addr} (pc={pc}): {inst_text}")

sim = SNXSimulator.from_source(
    source,
    mem_size=128,
    oob_callback=log_oob,
)
sim.run()
```

**Callback signature:**
```python
def oob_callback(
    kind: str,      # "load" or "store"
    addr: int,      # Effective address (16-bit masked)
    pc: int,        # Program counter of the instruction
    inst_text: str, # Original assembly text
    mem_size: int,  # Current memory size
) -> None: ...
```

See [Static Analysis](static-analysis.md) for details on compile-time memory checks.
