from __future__ import annotations

from dataclasses import dataclass

from snx.ast import (
    AddressOperand,
    InstructionNode,
    LabelDef,
    LabelRefOperand,
    Line,
    Opcode,
    Operand,
    Program,
    RegisterOperand,
)
from snx.diagnostics import DiagnosticCollector, SourceSpan
from snx.tokenizer import Token, TokenKind, tokenize


@dataclass(frozen=True, slots=True)
class Instruction:
    opcode: str
    operands: tuple[str, ...]
    raw: str


@dataclass(slots=True)
class ParseResult:
    program: Program | None
    diagnostics: list


class Parser:
    def __init__(self, tokens: list[Token], source_lines: list[str], diagnostics: DiagnosticCollector) -> None:
        self._tokens = tokens
        self._source_lines = source_lines
        self._diagnostics = diagnostics
        self._pos = 0

    def parse_program(self) -> Program:
        lines: list[Line] = []
        current_line_no = 1

        while not self._at_end():
            if self._check(TokenKind.EOF):
                break

            line = self._parse_line(current_line_no)
            lines.append(line)

            if self._check(TokenKind.EOL):
                self._advance()
                current_line_no += 1
            elif not self._check(TokenKind.EOF):
                current_line_no += 1

        return Program(tuple(lines))

    def _at_end(self) -> bool:
        return self._pos >= len(self._tokens) or self._current().kind == TokenKind.EOF

    def _current(self) -> Token:
        if self._pos >= len(self._tokens):
            return self._tokens[-1]
        return self._tokens[self._pos]

    def _peek(self, offset: int = 0) -> Token:
        idx = self._pos + offset
        if idx >= len(self._tokens):
            return self._tokens[-1]
        return self._tokens[idx]

    def _check(self, kind: TokenKind) -> bool:
        return self._current().kind == kind

    def _advance(self) -> Token:
        tok = self._current()
        if not self._at_end():
            self._pos += 1
        return tok

    def _consume(self, kind: TokenKind, error_code: str, error_msg: str) -> Token | None:
        if self._check(kind):
            return self._advance()
        tok = self._current()
        self._diagnostics.add_line_error(
            tok.line, error_code, error_msg, tok.span
        )
        return None

    def _parse_line(self, line_no: int) -> Line:
        raw = self._source_lines[line_no - 1] if line_no <= len(self._source_lines) else ""

        label: LabelDef | None = None
        instruction: InstructionNode | None = None
        comment: str | None = None

        if self._check(TokenKind.IDENT) and self._peek(1).kind == TokenKind.COLON:
            label = self._parse_label_def()

        if self._check(TokenKind.IDENT):
            instruction = self._parse_instruction()

        while not self._check(TokenKind.EOL) and not self._check(TokenKind.EOF):
            self._advance()

        return Line(line_no, label, instruction, comment, raw)

    def _parse_label_def(self) -> LabelDef:
        ident_tok = self._advance()
        colon_tok = self._advance()
        span = SourceSpan(ident_tok.line, ident_tok.column, colon_tok.line, colon_tok.column + 1)
        return LabelDef(name=ident_tok.normalized, original=ident_tok.lexeme, span=span)

    def _parse_instruction(self) -> InstructionNode:
        opcode_tok = self._advance()
        opcode = Opcode.from_str(opcode_tok.normalized)

        if opcode is None:
            self._diagnostics.add_line_error(
                opcode_tok.line,
                "S001",
                f"Unknown instruction: '{opcode_tok.lexeme}'",
                opcode_tok.span,
            )

        operands = self._parse_operands()

        text = opcode_tok.lexeme
        if operands:
            text += " " + ", ".join(op.text for op in operands)

        span = SourceSpan(
            opcode_tok.line,
            opcode_tok.column,
            self._current().line,
            self._current().column,
        )

        return InstructionNode(
            opcode=opcode,
            opcode_text=opcode_tok.lexeme,
            operands=tuple(operands),
            text=text,
            span=span,
        )

    def _parse_operands(self) -> list[Operand]:
        operands: list[Operand] = []

        if self._check(TokenKind.EOL) or self._check(TokenKind.EOF):
            return operands

        operand = self._parse_operand()
        if operand:
            operands.append(operand)

        while self._check(TokenKind.COMMA):
            self._advance()
            operand = self._parse_operand()
            if operand:
                operands.append(operand)

        return operands

    def _parse_operand(self) -> Operand | None:
        if self._check(TokenKind.REGISTER):
            return self._parse_register_operand()

        if self._check(TokenKind.NUMBER):
            return self._parse_address_operand()

        if self._check(TokenKind.IDENT):
            return self._parse_label_ref_operand()

        tok = self._current()
        if not self._check(TokenKind.EOL) and not self._check(TokenKind.EOF) and not self._check(TokenKind.COMMA):
            self._diagnostics.add_line_error(
                tok.line,
                "P003",
                f"Unexpected token: '{tok.lexeme}'",
                tok.span,
            )
            self._advance()
        return None

    def _parse_register_operand(self) -> RegisterOperand:
        tok = self._advance()
        try:
            index = int(tok.lexeme[1:])
        except ValueError:
            index = 0
            self._diagnostics.add_line_error(
                tok.line,
                "P004",
                f"Invalid register format: '{tok.lexeme}'",
                tok.span,
            )
        return RegisterOperand(text=tok.lexeme, span=tok.span, index=index)

    def _parse_address_operand(self) -> AddressOperand | None:
        offset_tok = self._advance()
        try:
            offset = int(offset_tok.lexeme)
        except ValueError:
            offset = 0
            self._diagnostics.add_line_error(
                offset_tok.line,
                "P005",
                f"Invalid offset format: '{offset_tok.lexeme}'",
                offset_tok.span,
            )

        if not self._consume(TokenKind.LPAREN, "P002", "'(' is required."):
            span = SourceSpan(offset_tok.line, offset_tok.column, offset_tok.line, offset_tok.column + len(offset_tok.lexeme))
            base = RegisterOperand(text="$0", span=span, index=0)
            return AddressOperand(text=offset_tok.lexeme, span=span, offset=offset, base=base)

        if not self._check(TokenKind.REGISTER):
            tok = self._current()
            self._diagnostics.add_line_error(
                tok.line,
                "P006",
                "Register is required.",
                tok.span,
            )
            span = SourceSpan(offset_tok.line, offset_tok.column, tok.line, tok.column)
            base = RegisterOperand(text="$0", span=tok.span, index=0)
            return AddressOperand(text=offset_tok.lexeme, span=span, offset=offset, base=base)

        base = self._parse_register_operand()

        rparen_tok = self._current()
        if not self._consume(TokenKind.RPAREN, "P002", "')' is required."):
            pass

        text = f"{offset_tok.lexeme}({base.text})"
        span = SourceSpan(offset_tok.line, offset_tok.column, rparen_tok.line, rparen_tok.column + 1)
        return AddressOperand(text=text, span=span, offset=offset, base=base)

    def _parse_label_ref_operand(self) -> LabelRefOperand:
        tok = self._advance()
        return LabelRefOperand(
            text=tok.lexeme,
            span=tok.span,
            name=tok.normalized,
            original=tok.lexeme,
        )


def parse(source: str, diagnostics: DiagnosticCollector | None = None) -> ParseResult:
    if diagnostics is None:
        diagnostics = DiagnosticCollector()

    source_lines = source.split("\n")
    tokens = tokenize(source, diagnostics)
    parser = Parser(tokens, source_lines, diagnostics)
    program = parser.parse_program()

    return ParseResult(program=program, diagnostics=diagnostics.diagnostics)


def parse_code(code_str: str, *, reg_count: int = 4) -> tuple[list[Instruction], dict[str, int]]:
    from snx.compiler import compile_program

    result = compile_program(code_str, reg_count=reg_count)

    if result.ir is None:
        return [], {}

    ir = result.ir
    instructions: list[Instruction] = []
    for inst_ir in ir.instructions:
        operand_strs = tuple(op.text for op in inst_ir.operands)
        instructions.append(Instruction(
            opcode=inst_ir.opcode.name,
            operands=operand_strs,
            raw=inst_ir.text,
        ))

    labels = dict(ir.labels)
    return instructions, labels
