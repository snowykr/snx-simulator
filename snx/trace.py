from __future__ import annotations

from typing import Sequence

from snx.constants import DEFAULT_REG_COUNT


def format_trace_header(reg_count: int = DEFAULT_REG_COUNT) -> str:
    reg_headers = " | ".join(f"${i:<2}" for i in range(reg_count))
    return f"| PC  | INST            | {reg_headers} |"


def format_trace_separator(reg_count: int = DEFAULT_REG_COUNT) -> str:
    reg_seps = " | ".join("---" for _ in range(reg_count))
    return f"| --- | --------------- | {reg_seps} |"


def format_trace_row(
    pc: int, inst_raw: str, regs: Sequence[int], reg_initialized: Sequence[bool]
) -> str:
    reg_display = (
        "*" if not reg_initialized[i] else str(regs[i]) for i in range(len(regs))
    )
    reg_vals = " | ".join(f"{val:<3}" for val in reg_display)
    return f"| {pc:<3} | {inst_raw:<15} | {reg_vals} |"
