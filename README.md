# SN-X Simulator

## Overview

SN-X Simulator is a Python toolchain (assembler, static analyzer, and simulator) for the **SN/X architecture**, a 16-bit educational RISC processor designed by **Naohiko Shimizu**.

This document includes a concise technical summary of the SN/X architecture and this Python implementation.

## Requirements

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv)

## Installation

1. Install uv (if not already installed)
   ```bash
   pip install uv
   ```
2. Create and activate a virtual environment
   ```bash
   uv venv
   source .venv/bin/activate
   ```
3. Install project dependencies
   ```bash
   uv pip install -e .
   ```

## Running the Sample Program

Run the main script to run static analysis and, if there are no errors, execute a sample assembly program and view the trace table:
```bash
uv run python main.py
```

The script will first print the static analysis result (errors and warnings). If any errors are reported, execution is aborted before the simulator runs.

## Static Analysis and Diagnostics

The SN-X toolchain performs several static checks before executing a program, similar in spirit to `go build` or `cargo check`:

- **Syntax and basic semantics**: unknown instructions, invalid operand counts/types, register index bounds, undefined or duplicate labels.
- **Memory bounds checking**: absolute addresses (`base == $0`) that exceed `mem_size` are flagged as errors (code `M001`).
- **Control-flow analysis (CFG)**: builds a control-flow graph to identify unreachable code and certain obvious infinite loops (regions of code with no path to `HLT`).
- **Dataflow analysis**: tracks initialization state of registers/memory and return-address usage to detect:
  - reads from uninitialized or potentially uninitialized memory,
  - return jumps that do not use a valid return address.

These checks are integrated into the compiler and simulator:

- `compile_program(source: str, *, reg_count: int = DEFAULT_REG_COUNT, mem_size: int = DEFAULT_MEM_SIZE, run_static_checks: bool = True)`
  - parses and analyzes the source program,
  - runs static analysis by default,
  - returns a `CompileResult` containing:
    - `program`: high-level AST (`Program`) or `None` on failure,
    - `ir`: lowered `IRProgram` or `None` if analysis failed,
    - `diagnostics`: list of all errors and warnings,
    - `reg_count`: the register count used for static analysis (default: 4),
    - `mem_size`: the memory size used for static analysis (default: 2^16),
    - `cfg`: the control-flow graph (when static checks are enabled),
    - `dataflow`: dataflow analysis result (when static checks are enabled).
  - helper methods:
    - `has_errors()` / `has_warnings()`
    - `format_diagnostics()` to pretty-print diagnostics.

- Default constants are defined in `snx/constants.py`:
  - `DEFAULT_REG_COUNT = 4`
  - `DEFAULT_MEM_SIZE = 2 ** 16` (65536 words, matching full SN/X architecture)

Example: running static checks from Python without executing the simulator:

```python
from snx import compile_program

source = """
main:
    LDA $3, 64($0)
    LDA $1, 3($0)
    BAL $2, foo
    HLT
foo:
    HLT
"""

result = compile_program(source)

print(result.format_diagnostics())
if result.has_errors():
    raise SystemExit(1)
```

- `SNXSimulator.from_compile_result(result: CompileResult, *, mem_size: int = DEFAULT_MEM_SIZE, trace_callback=None, input_fn=None, output_fn=None)`
  - creates a simulator from an existing `CompileResult`,
  - raises `ValueError` if the result contains errors or has no IR,
  - uses `result.reg_count` to configure the simulator's register count.

- `SNXSimulator.from_source(source: str, *, reg_count: int = DEFAULT_REG_COUNT, mem_size: int = DEFAULT_MEM_SIZE, trace_callback=None, input_fn=None, output_fn=None)`
  - convenience method that internally calls `compile_program` then `from_compile_result`,
  - raises `ValueError` if compilation or static analysis reports any errors.

### Recommended Pattern: Compile Once, Reuse IR

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

## SN/X Architecture Overview

SN/X (Simple 16-bit Non-Pipeline Processor) is a strictly 16-bit RISC processor designed for educational purposes.

### Key Specifications

- **Designer:** Naohiko Shimizu
- **Data Width:** 16-bit
- **Address Space:** 16-bit (2^16 words) for both Instruction Memory (IMEM) and Data Memory (DMEM)
- **Addressing:** Word addressing (address increment of 1 = 16-bit move)
- **Registers:** 4 General Purpose Registers (16-bit): `$0`, `$1`, `$2`, `$3`
  - **Note:** `$0` can store values like any other register, but when used as a **base register** in memory addressing (e.g., `LD $1, 10($0)`), it is treated as constant `0`. This means `Imm($0)` becomes an absolute address.
- **Pipeline:** Non-pipelined (sequential execution)
- **PC:** 16-bit Program Counter (not directly accessible by programmer)

### Instruction Formats

All instructions are 16-bit fixed length.

| Type | Assembly | Bit Layout (15→0) |
|------|----------|-------------------|
| **R** | `OP R1, R2, R3` | `OP(4) \| Src1(2) \| Src2(2) \| Dest(2) \| Unused(6)` |
| **R1** | `OP R1, R2` | `OP(4) \| Src(2) \| Unused(2) \| Dest(2) \| Unused(6)` |
| **R0** | `OP` | `OP(4) \| Unused(12)` |
| **I** | `OP R1, Imm(R2)` | `OP(4) \| Dest(2) \| Base(2) \| Imm(8)` |

### Full Instruction Set

| Opcode | Mnemonic | Type | Operation |
|:------:|:---------|:----:|:----------|
| `0x0` | **ADD** | R | `R1 = R2 + R3` |
| `0x1` | **AND** | R | `R1 = R2 & R3` |
| `0x2` | **SUB** | R | `R1 = R2 - R3` |
| `0x3` | **SLT** | R | `R1 = (R2 < R3) ? 1 : 0` |
| `0x4` | **NOT** | R1 | `R1 = ~R2` |
| `0x6` | **SR** | R1 | `R1 = R2 >> 1` |
| `0x7` | **HLT** | R0 | Halt processor |
| `0x8` | **LD** | I | `R1 = MEM[Base + Imm]` |
| `0x9` | **ST** | I | `MEM[Base + Imm] = R1` |
| `0xA` | **LDA** | I | `R1 = Base + Imm` (load address / immediate) |
| `0xC` | **IN** | I | `R1 = Input_Port` |
| `0xD` | **OUT** | I | `Output_Port = R1` |
| `0xE` | **BZ** | I | `if (R1 == 0) PC = PC + Imm` (branch if zero) |
| `0xF` | **BAL** | I | `R1 = PC + 1; PC = PC + Imm` (branch and link) |

**Branch Instructions:**
- **BZ:** Branches to target label if the condition register equals zero.
- **BAL:** Saves return address (`PC + 1`) into link register, then jumps to target. Used for function calls; return is typically `BAL $x, 0($link_reg)`.

### Simulator Implementation Status

This simulator implements the **complete SN/X instruction set**:

`ADD`, `AND`, `SUB`, `SLT`, `NOT`, `SR`, `HLT`, `LD`, `ST`, `LDA`, `IN`, `OUT`, `BZ`, `BAL`

### 16-bit Word Model

All register and memory values are strictly 16-bit words (0x0000–0xFFFF):
- Arithmetic operations wrap around on overflow/underflow.
- `SLT` compares values as signed 16-bit integers (two's complement).
- Effective addresses are computed as 16-bit values.

### I/O Model

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

### Memory in This Simulator

- **Architecture spec:** 2^16 words each for IMEM and DMEM.
- **Simulator default:** 2^16 words (65536) data memory, matching the full SN/X architecture.
- **Configurable:** Use `mem_size` parameter to reduce memory size for testing or constrained environments.

#### Reduced Memory Mode

When `mem_size < 2^16`, the simulator operates in "reduced memory mode":

- **Static analysis:** For `LD`/`ST` with absolute addresses (`base == $0`) that exceed `mem_size`, an error is flagged at compile time (error code `M001`). Note: `LDA` is not checked since it only computes an address without accessing memory.
- **Runtime behavior:**
  - **LD:** Reading from an out-of-bounds address returns 0.
  - **ST:** Writing to an out-of-bounds address is silently ignored (no-op).

Example with reduced memory (static error):

```python
from snx import compile_program

source = """
main:
    LD $1, 1000($0)  ; Error: address 1000 exceeds mem_size=128
    HLT
"""

result = compile_program(source, mem_size=128)
print(result.format_diagnostics())  # Shows M001 error
```

#### OOB Callback (Runtime Hook)

For dynamic addresses (where `base != $0`), out-of-bounds access cannot be detected at compile time. You can use the `oob_callback` parameter to receive notifications when OOB access occurs at runtime:

```python
from snx import SNXSimulator

def log_oob(kind, addr, pc, inst_text, mem_size):
    print(f"[OOB] {kind} at addr={addr} (pc={pc}): {inst_text}")

source = """
main:
    LDA $1, 200($0)   ; $1 = 200 (no OOB check for LDA)
    LD $2, 0($1)      ; Runtime OOB: addr=200 > mem_size=128
    HLT
"""

sim = SNXSimulator.from_source(
    source,
    mem_size=128,
    oob_callback=log_oob,
)
sim.run()
# Output: [OOB] load at addr=200 (pc=1): LD $2, 0($1)
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

**Behavior:**
- If `oob_callback` is `None` (default), OOB access is handled silently (LD returns 0, ST is no-op).
- If `oob_callback` is set, it is called before the default behavior.
- If the callback raises an exception, the simulator stops immediately.

### Trace Output

Each simulation step outputs PC, instruction text, and register state in a table format.

## SN/X Assembly Syntax

This section defines the syntax of the SN/X assembly language.

### Informal Overview

An SN/X assembly program consists of lines. Each line may contain:
- An optional **label definition** (an identifier followed by `:`)
- An optional **instruction** (a mnemonic followed by operands)
- An optional **comment** (starting with `;` and extending to the end of the line)

Empty lines and comment-only lines are allowed.

### Lexical Grammar

The lexer splits the input into the following token kinds:

| Token Kind | Description                                      | Examples            |
|------------|--------------------------------------------------|---------------------|
| IDENT      | Identifiers for labels and mnemonics             | `main`, `LDA`, `foo`|
| NUMBER     | Signed decimal integers                          | `42`, `-3`, `+10`   |
| REGISTER   | Register names (`$` followed by digits)          | `$0`, `$2`, `$3`    |
| COMMA      | `,`                                              |                     |
| COLON      | `:`                                              |                     |
| LPAREN     | `(`                                              |                     |
| RPAREN     | `)`                                              |                     |
| EOL        | End-of-line marker (produced for each newline)   |                     |
| EOF        | End-of-file marker                               |                     |

Comments start with `;` and continue to the end of the line. They are discarded by the lexer.

In EBNF notation:

```ebnf
identifier  = letter , { letter | digit | "_" } ;
number      = [ "+" | "-" ] , digit , { digit } ;
register    = "$" , digit , { digit } ;

letter      = "A".."Z" | "a".."z" ;
digit       = "0".."9" ;
```

Identifiers and mnemonics are case-insensitive; they are normalized to uppercase internally.

### Concrete Syntax Grammar (BNF / CFG)

The following context-free grammar (CFG), written in BNF, defines the concrete syntax of the SN/X assembly language:

```bnf
<program>           ::= <line>* <eof>

<line>              ::= [<label-def>] [<instruction>] <eol>

<label-def>         ::= <identifier> ":"

<instruction>       ::= <mnemonic> [<operand-list>]

<mnemonic>          ::= <identifier>

<operand-list>      ::= <operand> ("," <operand>)*

<operand>           ::= <register-operand>
                      | <address-operand>
                      | <label-ref-operand>

<register-operand>  ::= REGISTER

<address-operand>   ::= NUMBER "(" REGISTER ")"
                      | NUMBER

<label-ref-operand> ::= <identifier>

<eol>               ::= EOL | <eof>
<eof>               ::= EOF
```

**Notes:**
- When `<address-operand>` is written as just `NUMBER` (without parentheses), the base register defaults to `$0`.
- `<mnemonic>` is matched against the supported opcodes (`ADD`, `AND`, `SUB`, `SLT`, `NOT`, `SR`, `HLT`, `LD`, `ST`, `LDA`, `IN`, `OUT`, `BZ`, `BAL`). Unknown mnemonics produce a diagnostic error.
- Labels and mnemonics are case-insensitive.

### Operand Types by Instruction

| Instruction | Operand 1       | Operand 2                  | Operand 3       |
|-------------|-----------------|----------------------------|-----------------|
| ADD         | Register        | Register                   | Register        |
| AND         | Register        | Register                   | Register        |
| SUB         | Register        | Register                   | Register        |
| SLT         | Register        | Register                   | Register        |
| NOT         | Register        | Register                   |                 |
| SR          | Register        | Register                   |                 |
| HLT         |                 |                            |                 |
| LD          | Register        | Address                    |                 |
| ST          | Register        | Address                    |                 |
| LDA         | Register        | Address                    |                 |
| IN          | Register        |                            |                 |
| OUT         | Register        |                            |                 |
| BZ          | Register        | Label                      |                 |
| BAL         | Register        | Label or Address           |                 |
