from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Instruction:
    opcode: str
    operands: tuple[str, ...]
    raw: str


def parse_code(code_str: str) -> tuple[list[Instruction], dict[str, int]]:
    instructions: list[Instruction] = []
    labels: dict[str, int] = {}
    actual_line_idx = 0

    for line in code_str.strip().split("\n"):
        line = line.split(";")[0].strip()
        if not line:
            continue

        if ":" in line:
            label_part, code_part = line.split(":", 1)
            labels[label_part.strip()] = actual_line_idx
            line = code_part.strip()

        if not line:
            continue

        opcode_parts = line.split(None, 1)
        opcode = opcode_parts[0].upper()
        operand_segment = opcode_parts[1] if len(opcode_parts) > 1 else ""

        operands: list[str] = []
        if operand_segment:
            for raw_operand in operand_segment.split(","):
                sanitized = re.sub(r"\s+", "", raw_operand.strip())
                if sanitized:
                    operands.append(sanitized)

        operands_tuple = tuple(operands)

        instructions.append(
            Instruction(opcode=opcode, operands=operands_tuple, raw=line)
        )
        actual_line_idx += 1

    return instructions, labels
