from __future__ import annotations

import sys
from pathlib import Path

from snx.compiler import compile_program
from snx.simulator import SNXSimulator
from snx.trace import format_trace_header, format_trace_row, format_trace_separator


def run_program_from_source(source: str, *, label: str | None = None) -> int:
    result = compile_program(source)

    print("=== Static Analysis Result ===")
    print(result.format_diagnostics())
    print()

    if result.has_errors():
        print("Build failed due to errors above.")
        return 1

    if result.has_warnings():
        print("Build succeeded with warnings.")
        print()

    sim: SNXSimulator | None = None

    def trace_printer(pc: int, inst_raw: str, regs: list[int]) -> None:
        assert sim is not None
        init_flags = sim.get_reg_init_flags()
        print(format_trace_row(pc, inst_raw, regs, init_flags))

    sim = SNXSimulator.from_compile_result(result, trace_callback=trace_printer)

    print("=== Execution Trace ===")
    print(format_trace_header())
    print(format_trace_separator())

    sim.run()

    print()
    print("=== Execution completed successfully ===")
    return 0


def run_program_from_file(path: Path | str) -> int:
    path = Path(path).expanduser()

    if not path.exists():
        print(f"error: file '{path}' not found", file=sys.stderr)
        return 1

    if not path.is_file():
        print(f"error: '{path}' is not a file", file=sys.stderr)
        return 1

    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        print(f"error: failed to read '{path}': {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"error: failed to read '{path}': {e}", file=sys.stderr)
        return 1

    return run_program_from_source(source, label=str(path))
