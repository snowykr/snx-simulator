from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from snx.ast import (
    AddressOperand,
    DataImageWord,
    DirectiveKind,
    DirectiveNode,
    InstructionIR,
    InstructionNode,
    IRProgram,
    LabelDef,
    LabelRefOperand,
    Opcode,
    Operand,
    Program,
    RegisterOperand,
    SymbolKind,
    TypedSymbol,
)
from snx.constants import DEFAULT_MEM_SIZE, DEFAULT_REG_COUNT
from snx.word import IMM8_MAX_SIGNED, IMM8_MIN_SIGNED, WORD_MASK, normalize_imm8, word
from snx.diagnostics import Diagnostic, DiagnosticCollector, RelatedInfo, SourceSpan

if TYPE_CHECKING:
    pass


OperandTypeSpec = type[Operand] | tuple[type[Operand], ...]


OPCODE_OPERAND_SPEC: dict[Opcode, tuple[int, tuple[OperandTypeSpec, ...]]] = {
    Opcode.ADD: (3, (RegisterOperand, RegisterOperand, RegisterOperand)),
    Opcode.AND: (3, (RegisterOperand, RegisterOperand, RegisterOperand)),
    Opcode.SUB: (3, (RegisterOperand, RegisterOperand, RegisterOperand)),
    Opcode.SLT: (3, (RegisterOperand, RegisterOperand, RegisterOperand)),
    Opcode.NOT: (2, (RegisterOperand, RegisterOperand)),
    Opcode.SR: (2, (RegisterOperand, RegisterOperand)),
    Opcode.HLT: (0, ()),
    Opcode.LD: (2, (RegisterOperand, (AddressOperand, LabelRefOperand))),
    Opcode.ST: (2, (RegisterOperand, (AddressOperand, LabelRefOperand))),
    Opcode.LDA: (2, (RegisterOperand, (AddressOperand, LabelRefOperand))),
    Opcode.IN: (1, (RegisterOperand,)),
    Opcode.OUT: (1, (RegisterOperand,)),
    Opcode.BZ: (2, (RegisterOperand, LabelRefOperand)),
    Opcode.BAL: (2, (RegisterOperand, (LabelRefOperand, AddressOperand))),
}


@dataclass(slots=True)
class AnalysisResult:
    program: Program
    ir: IRProgram | None
    diagnostics: list[Diagnostic]


class Analyzer:
    def __init__(
        self,
        program: Program,
        diagnostics: DiagnosticCollector,
        *,
        reg_count: int = DEFAULT_REG_COUNT,
        mem_size: int = DEFAULT_MEM_SIZE,
    ) -> None:
        self._program: Program = program
        self._diagnostics: DiagnosticCollector = diagnostics
        self._reg_count: int = reg_count
        self._mem_size: int = mem_size
        self._labels: dict[str, int] = {}
        self._typed_symbols: dict[str, TypedSymbol] = {}
        self._symbol_spans: dict[str, SourceSpan] = {}
        self._instructions: list[InstructionIR] = []
        self._initial_data_image: list[DataImageWord] = []

    def analyze(self) -> AnalysisResult:
        if self._diagnostics.has_errors():
            return AnalysisResult(
                program=self._program,
                ir=None,
                diagnostics=self._diagnostics.diagnostics,
            )

        self._build_label_table()

        if self._diagnostics.has_errors():
            return AnalysisResult(
                program=self._program,
                ir=None,
                diagnostics=self._diagnostics.diagnostics,
            )

        self._analyze_instructions()

        if self._diagnostics.has_errors():
            return AnalysisResult(
                program=self._program,
                ir=None,
                diagnostics=self._diagnostics.diagnostics,
            )

        ir = IRProgram(
            instructions=tuple(self._instructions),
            labels=dict(self._labels),
            typed_symbols=dict(self._typed_symbols),
            initial_data_image=tuple(self._initial_data_image),
        )
        return AnalysisResult(
            program=self._program,
            ir=ir,
            diagnostics=self._diagnostics.diagnostics,
        )

    def _build_label_table(self) -> None:
        code_pc = 0
        data_addr = 0
        pending_labels: list[LabelDef] = []

        for line in self._program.lines:
            if line.label is not None:
                pending_labels.append(line.label)

            if line.directive is not None:
                self._define_pending_labels(
                    pending_labels,
                    kind=SymbolKind.DATA,
                    address=data_addr,
                )
                pending_labels.clear()
                if line.directive.kind is DirectiveKind.DW:
                    data_addr = self._allocate_dw_words(
                        line.line_no, line.directive, data_addr
                    )
                continue

            if line.instruction is not None:
                self._define_pending_labels(
                    pending_labels,
                    kind=SymbolKind.CODE,
                    address=code_pc,
                )
                pending_labels.clear()
                code_pc += 1
                continue

        self._define_pending_labels(
            pending_labels,
            kind=SymbolKind.CODE,
            address=code_pc,
        )

    def _analyze_instructions(self) -> None:
        pc = 0
        for line in self._program.lines:
            if line.instruction is None:
                continue

            inst = line.instruction
            if inst.opcode is None:
                pc += 1
                continue

            self._check_operand_spec(inst, line.line_no)
            resolved_operands = self._resolve_operands(inst, line.line_no)
            self._check_register_bounds(resolved_operands, line.line_no)
            self._check_branch_target_range(
                inst.opcode, resolved_operands, line.line_no
            )
            self._check_memory_bounds(inst.opcode, resolved_operands, line.line_no)
            self._check_immediate_range(inst.opcode, resolved_operands, line.line_no)

            if self._diagnostics.has_errors():
                pc += 1
                continue

            inst_ir = InstructionIR(
                opcode=inst.opcode,
                operands=resolved_operands,
                text=inst.text,
                pc=pc,
            )
            self._instructions.append(inst_ir)
            pc += 1

    def _resolve_operands(
        self, inst: InstructionNode, line_no: int
    ) -> tuple[Operand, ...]:
        resolved_operands: list[Operand] = []
        opcode = inst.opcode

        for index, operand in enumerate(inst.operands):
            if not isinstance(operand, LabelRefOperand):
                resolved_operands.append(operand)
                continue

            if opcode in (Opcode.LD, Opcode.ST, Opcode.LDA) and index == 1:
                resolved_operands.append(
                    self._resolve_data_address_label(operand, line_no)
                )
                continue

            if opcode in (Opcode.BZ, Opcode.BAL) and index == 1:
                self._require_code_label(operand, line_no)

            resolved_operands.append(operand)

        return tuple(resolved_operands)

    def _resolve_data_address_label(
        self, operand: LabelRefOperand, line_no: int
    ) -> Operand:
        symbol = self._typed_symbols.get(operand.name)
        if symbol is None:
            self._diagnostics.add_line_error(
                line_no,
                "S004",
                f"Undefined label: '{operand.original}'",
                operand.span,
            )
            return operand

        if symbol.kind is SymbolKind.CODE:
            self._diagnostics.add_line_error(
                line_no,
                "S007",
                f"Code label '{operand.original}' cannot be used as a data address",
                operand.span,
            )
            return operand

        if not IMM8_MIN_SIGNED <= symbol.address <= IMM8_MAX_SIGNED:
            self._diagnostics.add_line_error(
                line_no,
                "S009",
                (
                    f"Data label '{operand.original}' at address {symbol.address} cannot be used "
                    f"as a bare absolute address; SN/X I-type immediates are limited to "
                    f"{IMM8_MIN_SIGNED}..{IMM8_MAX_SIGNED}"
                ),
                operand.span,
            )
            return operand

        return AddressOperand(
            text=operand.text,
            span=operand.span,
            offset=symbol.address,
            base=RegisterOperand(
                text="$0",
                span=operand.span,
                index=0,
            ),
        )

    def _require_code_label(self, operand: LabelRefOperand, line_no: int) -> None:
        symbol = self._typed_symbols.get(operand.name)
        if symbol is None:
            self._diagnostics.add_line_error(
                line_no,
                "S004",
                f"Undefined label: '{operand.original}'",
                operand.span,
            )
            return

        if symbol.kind is SymbolKind.DATA:
            self._diagnostics.add_line_error(
                line_no,
                "S008",
                f"Data label '{operand.original}' cannot be used as a code target",
                operand.span,
            )

    def _define_symbol(
        self,
        name: str,
        *,
        original: str,
        span: SourceSpan,
        kind: SymbolKind,
        address: int,
    ) -> None:
        if name in self._typed_symbols:
            prev_span = self._symbol_spans[name]
            self._diagnostics.add_error(
                "S006",
                f"Duplicate label definition: '{original}'",
                span,
                (RelatedInfo("Previous definition", prev_span),),
            )
            return

        symbol = TypedSymbol(
            name=name,
            kind=kind,
            address=address,
            original=original,
            span=span,
        )
        self._typed_symbols[name] = symbol
        self._symbol_spans[name] = span
        if kind is SymbolKind.CODE:
            self._labels[name] = address

    def _define_pending_labels(
        self,
        pending_labels: list[LabelDef],
        *,
        kind: SymbolKind,
        address: int,
    ) -> None:
        for label in pending_labels:
            self._define_symbol(
                label.name,
                original=label.original,
                span=label.span,
                kind=kind,
                address=address,
            )

    def _allocate_dw_words(
        self, line_no: int, directive: DirectiveNode, start_addr: int
    ) -> int:
        data_addr = start_addr
        for value in directive.values:
            if data_addr >= self._mem_size:
                self._diagnostics.add_line_error(
                    line_no,
                    "M002",
                    f"DW allocation address {data_addr} (0x{data_addr:04X}) is out of bounds (mem_size={self._mem_size})",
                    directive.span,
                )
            normalized = word(value)
            if normalized != value:
                self._diagnostics.add_line_warning(
                    line_no,
                    "I002",
                    f"DW initializer {value} will be stored as 16-bit word {normalized} (0x{normalized:04X})",
                    directive.span,
                )
            if data_addr < self._mem_size:
                self._initial_data_image.append(
                    DataImageWord(
                        address=data_addr,
                        value=normalized,
                        source_line=line_no,
                    )
                )
            data_addr += 1
        return data_addr

    def _check_operand_spec(self, inst: InstructionNode, line_no: int) -> None:
        if inst.opcode is None:
            return

        spec = OPCODE_OPERAND_SPEC.get(inst.opcode)
        if spec is None:
            return

        expected_count, expected_types = spec
        actual_count = len(inst.operands)

        if actual_count != expected_count:
            self._diagnostics.add_line_error(
                line_no,
                "S002",
                f"'{inst.opcode.name}' requires {expected_count} operand(s), but {actual_count} provided.",
                inst.span,
            )
            return

        for i, (operand, expected_type) in enumerate(
            zip(inst.operands, expected_types)
        ):
            if isinstance(expected_type, tuple):
                if not isinstance(operand, expected_type):
                    type_names = " or ".join(t.__name__ for t in expected_type)
                    self._diagnostics.add_line_error(
                        line_no,
                        "S003",
                        f"Operand {i + 1} of '{inst.opcode.name}' must be of type {type_names}.",
                        operand.span,
                    )
            else:
                if not isinstance(operand, expected_type):
                    self._diagnostics.add_line_error(
                        line_no,
                        "S003",
                        f"Operand {i + 1} of '{inst.opcode.name}' must be of type {expected_type.__name__}.",
                        operand.span,
                    )

    def _check_register_bounds(
        self, operands: tuple[Operand, ...], line_no: int
    ) -> None:
        for operand in operands:
            if isinstance(operand, RegisterOperand):
                if operand.index < 0 or operand.index >= self._reg_count:
                    self._diagnostics.add_line_error(
                        line_no,
                        "S005",
                        f"Register index out of range: {operand.text} (valid: $0-${self._reg_count - 1})",
                        operand.span,
                    )
            elif isinstance(operand, AddressOperand):
                if operand.base.index < 0 or operand.base.index >= self._reg_count:
                    self._diagnostics.add_line_error(
                        line_no,
                        "S005",
                        f"Register index out of range: {operand.base.text} (valid: $0-${self._reg_count - 1})",
                        operand.base.span,
                    )

    def _check_branch_target_range(
        self, opcode: Opcode, operands: tuple[Operand, ...], line_no: int
    ) -> None:
        if opcode not in (Opcode.BZ, Opcode.BAL):
            return

        for operand in operands:
            if not isinstance(operand, LabelRefOperand):
                continue

            if operand.name not in self._labels:
                continue

            target_pc = self._labels[operand.name]
            if target_pc >= 1024:
                self._diagnostics.add_line_warning(
                    line_no,
                    "B001",
                    f"Branch target '{operand.original}' has PC {target_pc}, which exceeds "
                    f"the 10-bit branch field limit (0-1023); encoding will overflow into "
                    f"opcode/register bits (matching original snxasm behavior)",
                    operand.span,
                )

    def _check_memory_bounds(
        self, opcode: Opcode, operands: tuple[Operand, ...], line_no: int
    ) -> None:
        if opcode not in (Opcode.LD, Opcode.ST):
            return

        for operand in operands:
            if not isinstance(operand, AddressOperand):
                continue

            if operand.base.index != 0:
                continue

            eff_offset = normalize_imm8(operand.offset)
            ea = eff_offset & WORD_MASK
            if ea >= self._mem_size:
                self._diagnostics.add_line_error(
                    line_no,
                    "M001",
                    f"Memory address {ea} (0x{ea:04X}) is out of bounds "
                    f"(mem_size={self._mem_size})",
                    operand.span,
                )

    def _check_immediate_range(
        self, opcode: Opcode, operands: tuple[Operand, ...], line_no: int
    ) -> None:
        if opcode in (Opcode.BZ,):
            return

        if opcode == Opcode.BAL:
            if len(operands) >= 2 and isinstance(operands[1], LabelRefOperand):
                return

        for operand in operands:
            if not isinstance(operand, AddressOperand):
                continue

            offset = operand.offset
            norm = normalize_imm8(offset)
            if norm != offset:
                self._diagnostics.add_line_warning(
                    line_no,
                    "I001",
                    f"Immediate value {offset} will be encoded as 8-bit and interpreted as {norm} (0x{norm & 0xFF:02X})",
                    operand.span,
                )


def analyze(
    program: Program,
    diagnostics: DiagnosticCollector | None = None,
    *,
    reg_count: int = DEFAULT_REG_COUNT,
    mem_size: int = DEFAULT_MEM_SIZE,
) -> AnalysisResult:
    if diagnostics is None:
        diagnostics = DiagnosticCollector()

    analyzer = Analyzer(program, diagnostics, reg_count=reg_count, mem_size=mem_size)
    return analyzer.analyze()
