from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snx.diagnostics import SourceSpan


class Opcode(Enum):
    ADD = auto()
    AND = auto()
    SLT = auto()
    NOT = auto()
    SR = auto()
    LDA = auto()
    LD = auto()
    ST = auto()
    BZ = auto()
    BAL = auto()
    HLT = auto()

    @classmethod
    def from_str(cls, s: str) -> Opcode | None:
        try:
            return cls[s.upper()]
        except KeyError:
            return None


@dataclass(frozen=True, slots=True)
class LabelDef:
    name: str
    original: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Operand:
    text: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class RegisterOperand(Operand):
    index: int


@dataclass(frozen=True, slots=True)
class AddressOperand(Operand):
    offset: int
    base: RegisterOperand


@dataclass(frozen=True, slots=True)
class LabelRefOperand(Operand):
    name: str
    original: str


# not in use for now
@dataclass(frozen=True, slots=True)
class ImmediateOperand(Operand):
    value: int


@dataclass(frozen=True, slots=True)
class InstructionNode:
    opcode: Opcode | None
    opcode_text: str
    operands: tuple[Operand, ...]
    text: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Line:
    line_no: int
    label: LabelDef | None
    instruction: InstructionNode | None
    raw: str


@dataclass(frozen=True, slots=True)
class Program:
    lines: tuple[Line, ...]


@dataclass(frozen=True, slots=True)
class InstructionIR:
    opcode: Opcode
    operands: tuple[Operand, ...]
    text: str
    pc: int


@dataclass(frozen=True, slots=True)
class IRProgram:
    instructions: tuple[InstructionIR, ...]
    labels: dict[str, int]
