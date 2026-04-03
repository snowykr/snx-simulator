# Static Analysis

The SN/X toolchain performs several static checks before executing a program, similar in spirit to `go build` or `cargo check`.

## Overview

Static analysis is integrated into the compiler and runs by default when you call `compile_program()`. It catches errors and potential issues at compile time, before execution begins.

## Checks Performed

### Syntax and Basic Semantics

- Unknown instructions
- Invalid operand counts/types
- `DW` requires one or more decimal integer initializers (**Error code:** `P007`)
- Register index bounds
- Undefined or duplicate labels
- Domain-sensitive code/data label resolution: Labels are strictly partitioned into CODE (instruction targets) and DATA (DW locations).

`IRProgram.labels` remains the code-label map used for branch encoding, while the analyzer tracks both CODE and DATA labels in its typed symbol table. Bare labels are accepted only in operand positions that explicitly support them:

- `LD`, `ST`, and `LDA` accept bare DATA labels in their address operand and lower them to absolute `$0`-based addresses.
- `BZ` and label-form `BAL` require bare CODE labels.
- Numeric address operands keep their existing behavior unchanged.

Bare DATA labels in `LD`/`ST`/`LDA` must also fit the signed 8-bit I-type immediate range (`-128..127`) after lowering to a `$0`-based absolute address. If the resolved DATA address falls outside that range, compilation fails instead of silently wrapping the effective address.

Using a CODE label (an instruction label) where a DATA address is required (e.g., in `LD $1, main`) is a compile-time error.

**Error code:** `S007`

Using a DATA label (a `DW` label) where a CODE target is required (e.g., in `BZ $1, my_data`) is a compile-time error.

**Error code:** `S008`

Using a bare DATA label in `LD`/`ST`/`LDA` when its resolved absolute DMEM address cannot be encoded in the SN/X signed 8-bit I-type immediate field is a compile-time error.

**Error code:** `S009`

### Memory Bounds Checking

For `LD`/`ST` with absolute addresses (`base == $0`) that exceed `mem_size`, an error is flagged at compile time.

**Error code:** `M001`

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

> **Note:** `LDA` is not checked since it only computes an address without accessing memory.

For `DW` initializers, the analyzer uses a separate data-address counter that starts at `0` and advances independently of executable instruction PCs. If a `DW` word would be allocated at or beyond the configured `mem_size`, compilation fails before execution.

**Error code:** `M002`

If a `DW` initializer does not fit the 16-bit word model (that is, it falls outside the non-truncating `-32768..65535` range), it is normalized modulo 16 bits and reported as a warning.

**Warning code:** `I002`

### Control-Flow Analysis (CFG)

Builds a control-flow graph to identify:
- Unreachable code
- Obvious infinite loops (regions of code with no path to `HLT`)

### Dataflow Analysis

Tracks initialization state of registers/memory and return-address usage to detect:
- Reads from uninitialized or potentially uninitialized memory
- Return jumps that do not use a valid return address

## Diagnostic Codes

| Code | Severity | Description |
|------|----------|-------------|
| M001 | Error | Memory address exceeds configured `mem_size` |
| M002 | Error | DW allocation address exceeds configured `mem_size` |
| S007 | Error | CODE label used in a DATA-address operand context |
| S008 | Error | DATA label used in a CODE-target operand context |
| S009 | Error | Bare DATA label address exceeds the signed 8-bit I-type range |
| P007 | Error | DW requires one or more decimal integer initializers |
| I001 | Warning | Immediate value truncated to 8 bits |
| I002 | Warning | DW initializer normalized to the 16-bit word model |
| B001 | Warning | Branch target exceeds 10-bit limit |

## Using Static Analysis

### From CLI

The CLI automatically runs static analysis and displays diagnostics:

```bash
snx program.s
```

The command will:
1. Parse and compile the assembly source
2. Run static analysis (errors and warnings)
3. If no errors, execute the program and display a trace table

### From Python

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

### Disabling Static Checks

If needed, you can disable static analysis:

```python
result = compile_program(source, run_static_checks=False)
```

When disabled, `cfg` and `dataflow` fields in `CompileResult` will be `None`.

## Related Documentation

- [Python API](python-api.md) for full API reference
- [Architecture](architecture.md) for memory model details
