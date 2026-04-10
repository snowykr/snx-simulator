from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snx.diagnostics import SourceSpan


class Opcode(Enum):
    ADD = auto()
    AND = auto()
    SUB = auto()
    SLT = auto()
    NOT = auto()
    SR = auto()
    HLT = auto()
    LD = auto()
    ST = auto()
    LDA = auto()
    IN = auto()
    OUT = auto()
    BZ = auto()
    BAL = auto()

    @classmethod
    def from_str(cls, s: str) -> Opcode | None:
        try:
            return cls[s.upper()]
        except KeyError:
            return None


class DirectiveKind(Enum):
    DW = auto()


class SymbolKind(Enum):
    CODE = auto()
    DATA = auto()


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
class DirectiveNode:
    kind: DirectiveKind
    keyword: str
    values: tuple[int, ...]
    text: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class TypedSymbol:
    name: str
    kind: SymbolKind
    address: int
    original: str | None = None
    span: SourceSpan | None = None


@dataclass(frozen=True, slots=True)
class DataImageWord:
    address: int
    value: int
    source_line: int | None = None


@dataclass(frozen=True, slots=True)
class Line:
    line_no: int
    label: LabelDef | None
    instruction: InstructionNode | None
    raw: str
    directive: DirectiveNode | None = None

    @property
    def content(self) -> InstructionNode | DirectiveNode | None:
        if self.directive is not None:
            return self.directive
        return self.instruction


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
    typed_symbols: dict[str, TypedSymbol] = field(default_factory=dict)
    initial_data_image: tuple[DataImageWord, ...] = ()
