from snx import (
    CompileResult,
    DataImageWord,
    SymbolKind,
    TypedSymbol,
    compile_program,
    encode_program,
    parse_code,
)
from snx.ast import IRProgram, InstructionIR, Opcode


def test_compile_result_exposes_initial_data_image() -> None:
    ir = IRProgram(
        instructions=(InstructionIR(opcode=Opcode.HLT, operands=(), text="HLT", pc=0),),
        labels={"main": 0},
        initial_data_image=(
            DataImageWord(address=0, value=0x1234, source_line=3),
            DataImageWord(address=1, value=0xFFFF, source_line=3),
        ),
    )

    result = CompileResult(program=None, ir=ir, diagnostics=[])

    assert result.initial_data_image == (
        DataImageWord(address=0, value=0x1234, source_line=3),
        DataImageWord(address=1, value=0xFFFF, source_line=3),
    )
    assert [word.address for word in result.initial_data_image] == [0, 1]
    assert [word.value for word in result.initial_data_image] == [0x1234, 0xFFFF]


def test_compile_result_exposes_typed_symbols() -> None:
    typed_symbols = {
        "main": TypedSymbol(
            name="main", kind=SymbolKind.CODE, address=0, original="main"
        ),
        "table": TypedSymbol(
            name="table", kind=SymbolKind.DATA, address=4, original="table"
        ),
    }
    ir = IRProgram(
        instructions=(InstructionIR(opcode=Opcode.HLT, operands=(), text="HLT", pc=0),),
        labels={"main": 0},
        typed_symbols=typed_symbols,
    )

    result = CompileResult(program=None, ir=ir, diagnostics=[])

    assert result.typed_symbols == typed_symbols
    assert result.typed_symbols["main"].kind is SymbolKind.CODE
    assert result.typed_symbols["table"].kind is SymbolKind.DATA
    assert result.typed_symbols["table"].address == 4


def test_instruction_only_program_retains_compatible_compile_result_shape() -> None:
    source = """
main:
    LDA $1, 5($0)
    HLT
"""

    result = compile_program(source)

    assert not result.has_errors()
    assert result.ir is not None
    assert result.ir.instructions[0].text == "LDA $1, 5($0)"
    assert result.ir.labels == {"MAIN": 0}
    assert result.typed_symbols["MAIN"].kind is SymbolKind.CODE
    assert result.typed_symbols["MAIN"].address == 0
    assert result.initial_data_image == ()


def test_encode_program_ignores_dw_data_image() -> None:
    source = """
table: DW 4660, -1
main:
    LDA $1, 5($0)
    HLT
"""

    result = compile_program(source)

    assert not result.has_errors()
    assert result.ir is not None
    assert result.initial_data_image == (
        DataImageWord(address=0, value=0x1234, source_line=2),
        DataImageWord(address=1, value=0xFFFF, source_line=2),
    )
    assert encode_program(result.ir) == (0xA405, 0x7000)


def test_instruction_only_encoding_is_unchanged() -> None:
    source = """
main:
    LDA $1, 5($0)
    HLT
"""

    result = compile_program(source)

    assert not result.has_errors()
    assert result.ir is not None

    baseline_ir = result.ir
    baseline_encoding = encode_program(baseline_ir)
    augmented_ir = IRProgram(
        instructions=baseline_ir.instructions,
        labels=dict(baseline_ir.labels),
        typed_symbols={
            **baseline_ir.typed_symbols,
            "TABLE": TypedSymbol(
                name="TABLE",
                kind=SymbolKind.DATA,
                address=0,
                original="table",
            ),
        },
        initial_data_image=(DataImageWord(address=0, value=0x1234, source_line=1),),
    )

    assert baseline_encoding == (0xA405, 0x7000)
    assert encode_program(augmented_ir) == baseline_encoding


def test_parse_code_remains_instruction_focused() -> None:
    source = """
table: DW 7
main:
    HLT
"""

    parsed = parse_code(source)

    assert isinstance(parsed, tuple)
    assert len(parsed) == 2

    instructions, labels = parsed

    assert [instruction.opcode for instruction in instructions] == ["HLT"]
    assert [instruction.raw for instruction in instructions] == ["HLT"]
    assert labels == {"MAIN": 0}
    assert "TABLE" not in labels
