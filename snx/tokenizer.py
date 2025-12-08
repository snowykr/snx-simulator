from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from snx.diagnostics import DiagnosticCollector, SourceSpan


class TokenKind(Enum):
    IDENT = auto()
    NUMBER = auto()
    REGISTER = auto()
    COMMA = auto()
    COLON = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOL = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    lexeme: str
    normalized: str
    line: int
    column: int

    @property
    def span(self) -> SourceSpan:
        end_col = self.column + len(self.lexeme)
        return SourceSpan(self.line, self.column, self.line, end_col)


class Tokenizer:
    def __init__(self, source: str, diagnostics: DiagnosticCollector) -> None:
        self._source = source
        self._diagnostics = diagnostics
        self._pos = 0
        self._line = 1
        self._col = 1
        self._tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while not self._at_end():
            self._scan_token()
        self._add_token(TokenKind.EOF, "", "")
        return self._tokens

    def _at_end(self) -> bool:
        return self._pos >= len(self._source)

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self._source[self._pos]

    def _peek_next(self) -> str:
        if self._pos + 1 >= len(self._source):
            return "\0"
        return self._source[self._pos + 1]

    def _advance(self) -> str:
        ch = self._source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _add_token(self, kind: TokenKind, lexeme: str, normalized: str) -> None:
        col = self._col - len(lexeme)
        if col < 1:
            col = 1
        self._tokens.append(Token(kind, lexeme, normalized, self._line, col))

    def _scan_token(self) -> None:
        ch = self._peek()

        if ch == "\n":
            self._add_token(TokenKind.EOL, "\n", "\n")
            self._advance()
            return

        if ch in " \t\r":
            self._advance()
            return

        if ch == ";":
            while not self._at_end() and self._peek() != "\n":
                self._advance()
            return

        if ch == ",":
            self._advance()
            self._add_token(TokenKind.COMMA, ",", ",")
            return

        if ch == ":":
            self._advance()
            self._add_token(TokenKind.COLON, ":", ":")
            return

        if ch == "(":
            self._advance()
            self._add_token(TokenKind.LPAREN, "(", "(")
            return

        if ch == ")":
            self._advance()
            self._add_token(TokenKind.RPAREN, ")", ")")
            return

        if ch == "$":
            self._scan_register()
            return

        if ch.isdigit() or (ch in "+-" and self._peek_next().isdigit()):
            self._scan_number()
            return

        if ch.isalpha() or ch == "_":
            self._scan_identifier()
            return

        start_col = self._col
        self._advance()
        span = SourceSpan(self._line, start_col, self._line, start_col + 1)
        self._diagnostics.add_error("L001", f"잘못된 문자: '{ch}'", span)

    def _scan_register(self) -> None:
        start_col = self._col
        lexeme = self._advance()

        if not self._peek().isdigit():
            span = SourceSpan(self._line, start_col, self._line, self._col)
            self._diagnostics.add_error("L002", "레지스터 번호가 필요합니다.", span)
            self._add_token(TokenKind.REGISTER, lexeme, lexeme.upper())
            return

        while self._peek().isdigit():
            lexeme += self._advance()

        self._add_token(TokenKind.REGISTER, lexeme, lexeme.upper())

    def _scan_number(self) -> None:
        start_col = self._col
        lexeme = ""

        if self._peek() in "+-":
            lexeme += self._advance()

        while self._peek().isdigit():
            lexeme += self._advance()

        self._add_token(TokenKind.NUMBER, lexeme, lexeme)

    def _scan_identifier(self) -> None:
        start_col = self._col
        lexeme = ""

        while self._peek().isalnum() or self._peek() == "_":
            lexeme += self._advance()

        self._add_token(TokenKind.IDENT, lexeme, lexeme.upper())


def tokenize(source: str, diagnostics: DiagnosticCollector) -> list[Token]:
    tokenizer = Tokenizer(source, diagnostics)
    return tokenizer.tokenize()
