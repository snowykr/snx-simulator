from __future__ import annotations

from dataclasses import dataclass

from snx.analyzer import AnalysisResult, analyze
from snx.ast import IRProgram, Program
from snx.diagnostics import Diagnostic, DiagnosticCollector
from snx.parser import parse


@dataclass(slots=True)
class CompileResult:
    program: Program | None
    ir: IRProgram | None
    diagnostics: list[Diagnostic]

    def has_errors(self) -> bool:
        from snx.diagnostics import Severity
        return any(d.severity == Severity.ERROR for d in self.diagnostics)


def compile_program(
    source: str,
    *,
    reg_count: int = 4,
) -> CompileResult:
    diagnostics = DiagnosticCollector()

    parse_result = parse(source, diagnostics)

    if parse_result.program is None:
        return CompileResult(
            program=None,
            ir=None,
            diagnostics=diagnostics.diagnostics,
        )

    analysis_result = analyze(parse_result.program, diagnostics, reg_count=reg_count)

    return CompileResult(
        program=analysis_result.program,
        ir=analysis_result.ir,
        diagnostics=diagnostics.diagnostics,
    )
