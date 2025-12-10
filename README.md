# SN-X Simulator

## Overview

SN-X Simulator is a CPU simulator implementing the SN/X architecture in Python.

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
- **Control-flow analysis (CFG)**: builds a control-flow graph to identify unreachable code and certain obvious infinite loops (regions of code with no path to `HLT`).
- **Dataflow analysis**: tracks initialization state of registers/memory and return-address usage to detect:
  - reads from uninitialized or potentially uninitialized memory,
  - return jumps that do not use a valid return address.

These checks are integrated into the compiler and simulator:

- `compile_program(source: str, *, reg_count: int = DEFAULT_REG_COUNT, run_static_checks: bool = True)`
  - parses and analyzes the source program,
  - runs static analysis by default,
  - returns a `CompileResult` containing:
    - `program`: high-level AST (`Program`) or `None` on failure,
    - `ir`: lowered `IRProgram` or `None` if analysis failed,
    - `diagnostics`: list of all errors and warnings,
    - `reg_count`: the register count used for static analysis (default: 4),
    - `cfg`: the control-flow graph (when static checks are enabled),
    - `dataflow`: dataflow analysis result (when static checks are enabled).
  - helper methods:
    - `has_errors()` / `has_warnings()`
    - `format_diagnostics()` to pretty-print diagnostics.

- Default constants are defined in `snx/constants.py`:
  - `DEFAULT_REG_COUNT = 4`
  - `DEFAULT_MEM_SIZE = 128`

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

- `SNXSimulator.from_compile_result(result: CompileResult, *, mem_size: int = DEFAULT_MEM_SIZE, trace_callback=None)`
  - creates a simulator from an existing `CompileResult`,
  - raises `ValueError` if the result contains errors or has no IR,
  - uses `result.reg_count` to configure the simulator's register count.

- `SNXSimulator.from_source(source: str, *, reg_count: int = DEFAULT_REG_COUNT, mem_size: int = DEFAULT_MEM_SIZE, trace_callback=None)`
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

## Architecture and Instruction Summary

- **Registers**: `$0`–`$3`. Register `$0` is treated as zero when used as a base in address calculations.
- **Memory**: A fixed 128-word array.
- **Instructions**: Supports `LDA`, `LD`, `ST`, `ADD`, `AND`, `SLT`, `NOT`, `SR`, `BZ`, `BAL`, `HLT`.
- **Trace**: Each step outputs PC, instruction, and register state in a table format.

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
- `<mnemonic>` is matched against the supported opcodes (`ADD`, `AND`, `SLT`, `NOT`, `SR`, `LDA`, `LD`, `ST`, `BZ`, `BAL`, `HLT`). Unknown mnemonics produce a diagnostic error.
- Labels and mnemonics are case-insensitive.

### Operand Types by Instruction

| Instruction | Operand 1       | Operand 2                  | Operand 3       |
|-------------|-----------------|----------------------------|-----------------|
| ADD         | Register        | Register                   | Register        |
| AND         | Register        | Register                   | Register        |
| SLT         | Register        | Register                   | Register        |
| NOT         | Register        | Register                   |                 |
| SR          | Register        | Register                   |                 |
| LDA         | Register        | Address                    |                 |
| LD          | Register        | Address                    |                 |
| ST          | Register        | Address                    |                 |
| BZ          | Register        | Label                      |                 |
| BAL         | Register        | Label or Address           |                 |
| HLT         |                 |                            |                 |
