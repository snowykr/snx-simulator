from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from snx.analyzer import analyze
from snx.ast import IRProgram, Program
from snx.constants import DEFAULT_REG_COUNT
from snx.diagnostics import Diagnostic, DiagnosticCollector, Severity
from snx.parser import parse

if TYPE_CHECKING:
    from snx.cfg import CFG
    from snx.dataflow import DataflowResult


@dataclass(slots=True)
class CompileResult:
    program: Program | None
    ir: IRProgram | None
    diagnostics: list[Diagnostic]
    reg_count: int = DEFAULT_REG_COUNT
    cfg: CFG | None = None
    dataflow: DataflowResult | None = None

    def has_errors(self) -> bool:
        return any(d.severity == Severity.ERROR for d in self.diagnostics)

    def has_warnings(self) -> bool:
        return any(d.severity == Severity.WARNING for d in self.diagnostics)

    def format_diagnostics(self) -> str:
        if not self.diagnostics:
            return "No issues found."
        
        lines = []
        errors = [d for d in self.diagnostics if d.severity == Severity.ERROR]
        warnings = [d for d in self.diagnostics if d.severity == Severity.WARNING]
        
        if errors:
            lines.append(f"=== {len(errors)} Error(s) ===")
            for d in errors:
                lines.append(str(d))
        
        if warnings:
            lines.append(f"=== {len(warnings)} Warning(s) ===")
            for d in warnings:
                lines.append(str(d))
        
        return "\n".join(lines)


def _compile_internal(
    source: str,
    diagnostics: DiagnosticCollector,
    *,
    reg_count: int = DEFAULT_REG_COUNT,
    run_static_checks: bool = True,
) -> tuple[Program | None, IRProgram | None, "CFG | None", "DataflowResult | None"]:
    parse_result = parse(source, diagnostics)

    if parse_result.program is None:
        return None, None, None, None

    analysis_result = analyze(parse_result.program, diagnostics, reg_count=reg_count)

    if analysis_result.ir is None:
        return analysis_result.program, None, None, None

    cfg = None
    dataflow = None

    if run_static_checks:
        from snx.checker import check_program
        
        check_result = check_program(
            analysis_result.program,
            analysis_result.ir,
            diagnostics,
            reg_count=reg_count,
        )
        cfg = check_result.cfg
        dataflow = check_result.dataflow

    return analysis_result.program, analysis_result.ir, cfg, dataflow


def compile_program(
    source: str,
    *,
    reg_count: int = DEFAULT_REG_COUNT,
    run_static_checks: bool = True,
) -> CompileResult:
    diagnostics = DiagnosticCollector()
    program, ir, cfg, dataflow = _compile_internal(
        source,
        diagnostics,
        reg_count=reg_count,
        run_static_checks=run_static_checks,
    )

    return CompileResult(
        program=program,
        ir=ir,
        diagnostics=diagnostics.diagnostics,
        reg_count=reg_count,
        cfg=cfg,
        dataflow=dataflow,
    )
