from __future__ import annotations

from dataclasses import dataclass

from snx.analyzer import analyze
from snx.ast import IRProgram, Program
from snx.diagnostics import Diagnostic, DiagnosticCollector, Severity
from snx.parser import parse


@dataclass(slots=True)
class CompileResult:
    program: Program | None
    ir: IRProgram | None
    diagnostics: list[Diagnostic]

    def has_errors(self) -> bool:
        return any(d.severity == Severity.ERROR for d in self.diagnostics)


def _compile_internal(
    source: str,
    diagnostics: DiagnosticCollector,
    *,
    reg_count: int = 4,
) -> tuple[Program | None, IRProgram | None]:
    parse_result = parse(source, diagnostics)

    if parse_result.program is None:
        return None, None

    analysis_result = analyze(parse_result.program, diagnostics, reg_count=reg_count)

    return analysis_result.program, analysis_result.ir


def compile_program(
    source: str,
    *,
    reg_count: int = 4,
) -> CompileResult:
    diagnostics = DiagnosticCollector()
    program, ir = _compile_internal(source, diagnostics, reg_count=reg_count)

    return CompileResult(
        program=program,
        ir=ir,
        diagnostics=diagnostics.diagnostics,
    )
