from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    def __str__(self) -> str:
        if self.start_line == self.end_line:
            return f"{self.start_line}:{self.start_col}-{self.end_col}"
        return f"{self.start_line}:{self.start_col}-{self.end_line}:{self.end_col}"


@dataclass(frozen=True, slots=True)
class RelatedInfo:
    message: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    severity: Severity
    span: SourceSpan
    related: tuple[RelatedInfo, ...] = ()

    def __str__(self) -> str:
        prefix = f"[{self.code}] {self.severity.value}: {self.message} at {self.span}"
        if self.related:
            related_strs = [f"  - {r.message} at {r.span}" for r in self.related]
            return prefix + "\n" + "\n".join(related_strs)
        return prefix


class DiagnosticCollector:
    def __init__(self) -> None:
        self._diagnostics: list[Diagnostic] = []
        self._line_primary: dict[int, Diagnostic] = {}

    @property
    def diagnostics(self) -> list[Diagnostic]:
        return list(self._diagnostics)

    def has_errors(self) -> bool:
        return any(d.severity == Severity.ERROR for d in self._diagnostics)

    def add(
        self,
        code: str,
        message: str,
        severity: Severity,
        span: SourceSpan,
        related: tuple[RelatedInfo, ...] = (),
    ) -> Diagnostic:
        diag = Diagnostic(
            code=code,
            message=message,
            severity=severity,
            span=span,
            related=related,
        )
        self._diagnostics.append(diag)
        return diag

    def add_error(
        self,
        code: str,
        message: str,
        span: SourceSpan,
        related: tuple[RelatedInfo, ...] = (),
    ) -> Diagnostic:
        return self.add(code, message, Severity.ERROR, span, related)

    def add_warning(
        self,
        code: str,
        message: str,
        span: SourceSpan,
        related: tuple[RelatedInfo, ...] = (),
    ) -> Diagnostic:
        return self.add(code, message, Severity.WARNING, span, related)

    def add_line_error(
        self,
        line: int,
        code: str,
        message: str,
        span: SourceSpan,
    ) -> Diagnostic:
        related: tuple[RelatedInfo, ...] = ()
        if line in self._line_primary:
            primary = self._line_primary[line]
            related = (
                RelatedInfo(
                    message=f"이 오류는 같은 줄의 이전 오류({primary.code})의 영향일 수 있습니다.",
                    span=primary.span,
                ),
            )
        diag = self.add_error(code, message, span, related)
        if line not in self._line_primary:
            self._line_primary[line] = diag
        return diag

    def get_line_primary(self, line: int) -> Diagnostic | None:
        return self._line_primary.get(line)

    def clear(self) -> None:
        self._diagnostics.clear()
        self._line_primary.clear()
