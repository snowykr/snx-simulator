from __future__ import annotations

from typing import TYPE_CHECKING

from snx.ast import (
    AddressOperand,
    InstructionIR,
    IRProgram,
    LabelRefOperand,
    Opcode,
    RegisterOperand,
)
from snx.word import IMM8_MASK, word

if TYPE_CHECKING:
    pass

OPCODE_TO_INT: dict[Opcode, int] = {
    Opcode.ADD: 0x0,
    Opcode.AND: 0x1,
    Opcode.SUB: 0x2,
    Opcode.SLT: 0x3,
    Opcode.NOT: 0x4,
    Opcode.SR: 0x6,
    Opcode.HLT: 0x7,
    Opcode.LD: 0x8,
    Opcode.ST: 0x9,
    Opcode.LDA: 0xA,
    Opcode.IN: 0xC,
    Opcode.OUT: 0xD,
    Opcode.BZ: 0xE,
    Opcode.BAL: 0xF,
}

INT_TO_OPCODE: dict[int, Opcode] = {v: k for k, v in OPCODE_TO_INT.items()}

LABEL_PC_MASK = 0x3FF


class EncodingError(Exception):
    pass


def encode_instruction(inst: InstructionIR, labels: dict[str, int]) -> int:
    opcode = inst.opcode
    operands = inst.operands
    op_int = OPCODE_TO_INT[opcode]

    if opcode in (Opcode.ADD, Opcode.AND, Opcode.SUB, Opcode.SLT):
        dest = operands[0]
        src1 = operands[1]
        src2 = operands[2]
        if not (isinstance(dest, RegisterOperand) and
                isinstance(src1, RegisterOperand) and
                isinstance(src2, RegisterOperand)):
            raise EncodingError(f"Invalid operands for R-type instruction: {inst.text}")
        return (
            (op_int << 12) |
            (src1.index << 10) |
            (src2.index << 8) |
            (dest.index << 6)
        )

    elif opcode in (Opcode.NOT, Opcode.SR):
        dest = operands[0]
        src = operands[1]
        if not (isinstance(dest, RegisterOperand) and isinstance(src, RegisterOperand)):
            raise EncodingError(f"Invalid operands for R1-type instruction: {inst.text}")
        return (
            (op_int << 12) |
            (src.index << 10) |
            (dest.index << 6)
        )

    elif opcode == Opcode.HLT:
        return op_int << 12

    elif opcode in (Opcode.LD, Opcode.ST, Opcode.LDA):
        dest = operands[0]
        addr_op = operands[1]
        if not (isinstance(dest, RegisterOperand) and isinstance(addr_op, AddressOperand)):
            raise EncodingError(f"Invalid operands for I-type instruction: {inst.text}")
        imm8 = addr_op.offset & IMM8_MASK
        return (
            (op_int << 12) |
            (dest.index << 10) |
            (addr_op.base.index << 8) |
            imm8
        )

    elif opcode == Opcode.IN:
        dest = operands[0]
        if not isinstance(dest, RegisterOperand):
            raise EncodingError(f"Invalid operands for IN instruction: {inst.text}")
        return (
            (op_int << 12) |
            (dest.index << 10)
        )

    elif opcode == Opcode.OUT:
        src = operands[0]
        if not isinstance(src, RegisterOperand):
            raise EncodingError(f"Invalid operands for OUT instruction: {inst.text}")
        return (
            (op_int << 12) |
            (src.index << 10)
        )

    elif opcode == Opcode.BZ:
        cond_reg = operands[0]
        label_op = operands[1]
        if not (isinstance(cond_reg, RegisterOperand) and isinstance(label_op, LabelRefOperand)):
            raise EncodingError(f"Invalid operands for BZ instruction: {inst.text}")
        label_pc = labels.get(label_op.name, 0)
        # NOTE: This uses addition (not bitwise OR) intentionally to match the
        # original snxasm branch encoding, including overflow behavior when
        # the target PC exceeds the 10-bit field (see README: "Branch Encoding and Program Length Limit").
        return word(
            (op_int << 12) +
            (cond_reg.index << 10) +
            label_pc
        )

    elif opcode == Opcode.BAL:
        link_reg = operands[0]
        target_op = operands[1]
        if not isinstance(link_reg, RegisterOperand):
            raise EncodingError(f"Invalid operands for BAL instruction: {inst.text}")

        if isinstance(target_op, LabelRefOperand):
            label_pc = labels.get(target_op.name, 0)
            # NOTE: This also uses addition intentionally to preserve snxasm's
            # original BAL label encoding semantics, including overflow into
            # opcode/register bits for large PCs (see README).
            return word(
                (op_int << 12) +
                (link_reg.index << 10) +
                label_pc
            )
        elif isinstance(target_op, AddressOperand):
            imm8 = target_op.offset & IMM8_MASK
            return (
                (op_int << 12) |
                (link_reg.index << 10) |
                (target_op.base.index << 8) |
                imm8
            )
        else:
            raise EncodingError(f"Invalid target operand for BAL instruction: {inst.text}")

    else:
        raise EncodingError(f"Unknown opcode: {opcode}")


def encode_program(ir_program: IRProgram) -> tuple[int, ...]:
    labels = ir_program.labels
    result: list[int] = []
    for inst in ir_program.instructions:
        encoded = encode_instruction(inst, labels)
        result.append(encoded)
    return tuple(result)


def decode_word(word: int) -> dict:
    word = word & 0xFFFF
    op_int = (word >> 12) & 0xF
    opcode = INT_TO_OPCODE.get(op_int)

    if opcode is None:
        return {"opcode": None, "raw": word}

    if opcode in (Opcode.ADD, Opcode.AND, Opcode.SUB, Opcode.SLT):
        src1 = (word >> 10) & 0x3
        src2 = (word >> 8) & 0x3
        dest = (word >> 6) & 0x3
        return {
            "opcode": opcode,
            "type": "R",
            "dest": dest,
            "src1": src1,
            "src2": src2,
        }

    elif opcode in (Opcode.NOT, Opcode.SR):
        src = (word >> 10) & 0x3
        dest = (word >> 6) & 0x3
        return {
            "opcode": opcode,
            "type": "R1",
            "dest": dest,
            "src": src,
        }

    elif opcode == Opcode.HLT:
        return {
            "opcode": opcode,
            "type": "R0",
        }

    elif opcode in (Opcode.LD, Opcode.ST, Opcode.LDA):
        dest = (word >> 10) & 0x3
        base = (word >> 8) & 0x3
        imm = word & 0xFF
        return {
            "opcode": opcode,
            "type": "I",
            "dest": dest,
            "base": base,
            "imm": imm,
        }

    elif opcode == Opcode.IN:
        dest = (word >> 10) & 0x3
        return {
            "opcode": opcode,
            "type": "I",
            "dest": dest,
        }

    elif opcode == Opcode.OUT:
        src = (word >> 10) & 0x3
        return {
            "opcode": opcode,
            "type": "I",
            "src": src,
        }

    elif opcode == Opcode.BZ:
        cond_reg = (word >> 10) & 0x3
        target = word & 0x3FF
        return {
            "opcode": opcode,
            "type": "I",
            "cond_reg": cond_reg,
            "target": target,
        }

    elif opcode == Opcode.BAL:
        link_reg = (word >> 10) & 0x3
        base = (word >> 8) & 0x3
        imm_or_target = word & 0xFF
        target_10bit = word & 0x3FF
        return {
            "opcode": opcode,
            "type": "I",
            "link_reg": link_reg,
            "base": base,
            "imm": imm_or_target,
            "target_10bit": target_10bit,
        }

    return {"opcode": opcode, "raw": word}


def format_hex(words: tuple[int, ...], words_per_line: int = 8) -> str:
    lines: list[str] = []
    for i in range(0, len(words), words_per_line):
        chunk = words[i:i + words_per_line]
        line = " ".join(f"{w:04X}" for w in chunk)
        lines.append(line)
    return "\n".join(lines)


def format_intel_hex(words: tuple[int, ...]) -> str:
    lines: list[str] = []
    for i, w in enumerate(words):
        byte_count = 2
        address = i
        record_type = 0
        data_high = (w >> 8) & 0xFF
        data_low = w & 0xFF
        checksum = (
            -(byte_count + (address >> 8) + (address & 0xFF) + record_type + data_low + data_high)
        ) & 0xFF
        line = f":{byte_count:02X}{address:04X}{record_type:02X}{w:04X}{checksum:02X}"
        lines.append(line)
    lines.append(":00000001FF")
    return "\n".join(lines)
