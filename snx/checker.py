from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from snx.ast import IRProgram, Program
from snx.cfg import (
    CFG,
    build_cfg,
    find_reachable_pcs,
    find_infinite_loop_sccs,
)
from snx.constants import DEFAULT_REG_COUNT
from snx.dataflow import (
    DataflowResult,
    analyze_dataflow,
)
from snx.diagnostics import (
    Diagnostic,
    DiagnosticCollector,
    Severity,
    SourceSpan,
)

if TYPE_CHECKING:
    pass


@dataclass(slots=True)
class CheckResult:
    program: Program | None
    ir: IRProgram | None
    cfg: CFG | None
    dataflow: DataflowResult | None
    diagnostics: list[Diagnostic]

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


class StaticChecker:
    def __init__(
        self,
        program: Program,
        ir: IRProgram,
        diagnostics: DiagnosticCollector,
        *,
        reg_count: int = DEFAULT_REG_COUNT,
    ) -> None:
        self._program = program
        self._ir = ir
        self._diagnostics = diagnostics
        self._reg_count = reg_count
        self._cfg: CFG | None = None
        self._dataflow: DataflowResult | None = None
        self._line_spans: dict[int, SourceSpan] = {}
        self._pc_to_line: dict[int, int] = {}
        
        self._build_line_mappings()

    def _build_line_mappings(self) -> None:
        pc = 0
        for line in self._program.lines:
            if line.instruction is not None:
                self._pc_to_line[pc] = line.line_no
                if line.instruction.span:
                    self._line_spans[line.line_no] = line.instruction.span
                pc += 1

    def check(self) -> CheckResult:
        self._cfg = build_cfg(self._ir)
        
        self._check_cfg_issues()
        
        self._dataflow = analyze_dataflow(
            self._ir,
            self._cfg,
            reg_count=self._reg_count,
        )
        
        self._check_dataflow_issues()
        
        return CheckResult(
            program=self._program,
            ir=self._ir,
            cfg=self._cfg,
            dataflow=self._dataflow,
            diagnostics=self._diagnostics.diagnostics,
        )

    def _check_cfg_issues(self) -> None:
        if self._cfg is None:
            return
        
        reachable = find_reachable_pcs(self._cfg, self._cfg.entry_pc)
        all_pcs = set()
        for block in self._cfg.blocks.values():
            for inst in block.instructions:
                all_pcs.add(inst.pc)
        
        unreachable = all_pcs - reachable
        for pc in sorted(unreachable):
            line_no = self._pc_to_line.get(pc)
            if line_no is not None:
                span = self._line_spans.get(line_no)
                if span:
                    labels_at_pc = self._cfg.reverse_labels.get(pc, [])
                    if labels_at_pc:
                        label_str = ", ".join(labels_at_pc)
                        self._diagnostics.add_warning(
                            "W001",
                            f"Unreachable code at label '{label_str}'",
                            span,
                        )
                    else:
                        self._diagnostics.add_warning(
                            "W001",
                            "Unreachable code",
                            span,
                        )
        
        infinite_sccs = find_infinite_loop_sccs(self._cfg)
        reported_lines: set[int] = set()
        
        for scc in infinite_sccs:
            min_pc = min(scc)
            line_no = self._pc_to_line.get(min_pc)
            if line_no is not None and line_no not in reported_lines:
                reported_lines.add(line_no)
                span = self._line_spans.get(line_no)
                if span:
                    labels_in_scc = []
                    for pc in scc:
                        labels_in_scc.extend(self._cfg.reverse_labels.get(pc, []))
                    
                    if labels_in_scc:
                        label_str = ", ".join(sorted(set(labels_in_scc)))
                        self._diagnostics.add_error(
                            "C010",
                            f"Infinite loop detected: no path to HLT from '{label_str}'",
                            span,
                        )
                    else:
                        self._diagnostics.add_error(
                            "C010",
                            "Infinite loop detected: no path to HLT",
                            span,
                        )

    def _check_dataflow_issues(self) -> None:
        if self._dataflow is None:
            return
        
        for issue in self._dataflow.issues:
            line_no = self._pc_to_line.get(issue.pc)
            if line_no is None:
                continue
            
            span = self._line_spans.get(line_no)
            if span is None:
                span = SourceSpan(line_no, 1, line_no, 1)
            
            if issue.severity == "error":
                self._diagnostics.add_error(
                    issue.code,
                    issue.message,
                    span,
                )
            else:
                self._diagnostics.add_warning(
                    issue.code,
                    issue.message,
                    span,
                )


def check_program(
    program: Program,
    ir: IRProgram,
    diagnostics: DiagnosticCollector | None = None,
    *,
    reg_count: int = DEFAULT_REG_COUNT,
) -> CheckResult:
    if diagnostics is None:
        diagnostics = DiagnosticCollector()
    
    checker = StaticChecker(program, ir, diagnostics, reg_count=reg_count)
    return checker.check()
