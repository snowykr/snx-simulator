from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from snx.ast import (
    AddressOperand,
    InstructionIR,
    InstructionNode,
    IRProgram,
    LabelRefOperand,
    Line,
    Opcode,
    Operand,
    Program,
    RegisterOperand,
)
from snx.diagnostics import DiagnosticCollector, RelatedInfo, SourceSpan

if TYPE_CHECKING:
    pass


OPCODE_OPERAND_SPEC: dict[Opcode, tuple[int, tuple[type, ...]]] = {
    Opcode.ADD: (3, (RegisterOperand, RegisterOperand, RegisterOperand)),
    Opcode.AND: (3, (RegisterOperand, RegisterOperand, RegisterOperand)),
    Opcode.SLT: (3, (RegisterOperand, RegisterOperand, RegisterOperand)),
    Opcode.NOT: (2, (RegisterOperand, RegisterOperand)),
    Opcode.SR: (2, (RegisterOperand, RegisterOperand)),
    Opcode.LDA: (2, (RegisterOperand, AddressOperand)),
    Opcode.LD: (2, (RegisterOperand, AddressOperand)),
    Opcode.ST: (2, (RegisterOperand, AddressOperand)),
    Opcode.BZ: (2, (RegisterOperand, LabelRefOperand)),
    Opcode.BAL: (2, (RegisterOperand, (LabelRefOperand, AddressOperand))),
    Opcode.HLT: (0, ()),
}


@dataclass(slots=True)
class AnalysisResult:
    program: Program
    ir: IRProgram | None
    diagnostics: list


class Analyzer:
    def __init__(self, program: Program, diagnostics: DiagnosticCollector, *, reg_count: int = 4) -> None:
        self._program = program
        self._diagnostics = diagnostics
        self._reg_count = reg_count
        self._labels: dict[str, int] = {}
        self._label_spans: dict[str, SourceSpan] = {}
        self._instructions: list[InstructionIR] = []

    def analyze(self) -> AnalysisResult:
        self._build_label_table()
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
        )
        return AnalysisResult(
            program=self._program,
            ir=ir,
            diagnostics=self._diagnostics.diagnostics,
        )

    def _build_label_table(self) -> None:
        pc = 0
        for line in self._program.lines:
            if line.label is not None:
                label_name = line.label.name
                if label_name in self._labels:
                    prev_span = self._label_spans[label_name]
                    self._diagnostics.add_error(
                        "S006",
                        f"Duplicate label definition: '{line.label.original}'",
                        line.label.span,
                        (RelatedInfo(
                            "Previous definition",
                            prev_span,
                        ),),
                    )
                else:
                    self._labels[label_name] = pc
                    self._label_spans[label_name] = line.label.span

            if line.instruction is not None:
                pc += 1

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
            self._check_register_bounds(inst, line.line_no)
            self._check_label_refs(inst, line.line_no)

            inst_ir = InstructionIR(
                opcode=inst.opcode,
                operands=inst.operands,
                text=inst.text,
                pc=pc,
            )
            self._instructions.append(inst_ir)
            pc += 1

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

        for i, (operand, expected_type) in enumerate(zip(inst.operands, expected_types)):
            if isinstance(expected_type, tuple):
                if not isinstance(operand, expected_type):
                    type_names = " or ".join(t.__name__ for t in expected_type)
                    self._diagnostics.add_line_error(
                        line_no,
                        "S003",
                        f"Operand {i+1} of '{inst.opcode.name}' must be of type {type_names}.",
                        operand.span,
                    )
            else:
                if not isinstance(operand, expected_type):
                    self._diagnostics.add_line_error(
                        line_no,
                        "S003",
                        f"Operand {i+1} of '{inst.opcode.name}' must be of type {expected_type.__name__}.",
                        operand.span,
                    )

    def _check_register_bounds(self, inst: InstructionNode, line_no: int) -> None:
        for operand in inst.operands:
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

    def _check_label_refs(self, inst: InstructionNode, line_no: int) -> None:
        for operand in inst.operands:
            if isinstance(operand, LabelRefOperand):
                if operand.name not in self._labels:
                    self._diagnostics.add_line_error(
                        line_no,
                        "S004",
                        f"Undefined label: '{operand.original}'",
                        operand.span,
                    )


def analyze(
    program: Program,
    diagnostics: DiagnosticCollector | None = None,
    *,
    reg_count: int = 4,
) -> AnalysisResult:
    if diagnostics is None:
        diagnostics = DiagnosticCollector()

    analyzer = Analyzer(program, diagnostics, reg_count=reg_count)
    return analyzer.analyze()
