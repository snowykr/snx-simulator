from snx import SymbolKind, compile_program
from snx.ast import AddressOperand


def test_data_label_binds_to_first_allocated_word() -> None:
    source = """
start:
    HLT
table: DW 7, 8, 9
"""

    result = compile_program(source, run_static_checks=False)

    assert not result.has_errors()
    assert result.ir is not None
    assert result.typed_symbols["TABLE"].kind is SymbolKind.DATA
    assert result.typed_symbols["TABLE"].address == 0
    assert result.initial_data_image == (
        result.ir.initial_data_image[0],
        result.ir.initial_data_image[1],
        result.ir.initial_data_image[2],
    )
    assert [word.address for word in result.initial_data_image] == [0, 1, 2]
    assert [word.value for word in result.initial_data_image] == [7, 8, 9]


def test_code_pc_is_instruction_only_when_dw_lines_are_interleaved() -> None:
    source = """
start:
    LDA $1, 0($0)
table: DW 99, 100
middle:
    OUT $1
tail:
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert not result.has_errors()
    assert result.ir is not None
    assert [inst.pc for inst in result.ir.instructions] == [0, 1, 2]
    assert result.ir.labels == {"START": 0, "MIDDLE": 1, "TAIL": 2}
    assert result.typed_symbols["START"].kind is SymbolKind.CODE
    assert result.typed_symbols["MIDDLE"].kind is SymbolKind.CODE
    assert result.typed_symbols["TAIL"].kind is SymbolKind.CODE
    assert result.typed_symbols["TABLE"].kind is SymbolKind.DATA
    assert result.typed_symbols["TABLE"].address == 0
    assert [word.address for word in result.initial_data_image] == [0, 1]
    assert [word.value for word in result.initial_data_image] == [99, 100]


def test_duplicate_identifier_across_code_and_data_reports_s006() -> None:
    source = """
value:
    HLT
VALUE: DW 1
"""

    result = compile_program(source, run_static_checks=False)

    assert result.has_errors()
    assert result.ir is None
    assert [diag.code for diag in result.diagnostics] == ["S006"]
    assert result.diagnostics[0].message == "Duplicate label definition: 'VALUE'"


def test_dw_out_of_bounds_reports_m002() -> None:
    source = """
table: DW 1, 2, 3
main:
    HLT
"""

    result = compile_program(source, mem_size=2, run_static_checks=False)

    assert result.has_errors()
    assert result.ir is None
    m002 = [diag for diag in result.diagnostics if diag.code == "M002"]
    assert len(m002) == 1
    assert (
        m002[0].message
        == "DW allocation address 2 (0x0002) is out of bounds (mem_size=2)"
    )


def test_dw_word_truncation_reports_i002() -> None:
    source = """
table: DW 65536
main:
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert not result.has_errors()
    assert result.ir is not None
    i002 = [diag for diag in result.diagnostics if diag.code == "I002"]
    assert len(i002) == 1
    assert (
        i002[0].message
        == "DW initializer 65536 will be stored as 16-bit word 0 (0x0000)"
    )
    assert result.typed_symbols["TABLE"].kind is SymbolKind.DATA
    assert result.initial_data_image[0].address == 0
    assert result.initial_data_image[0].value == 0


def test_signed_dw_values_in_16bit_range_do_not_report_i002() -> None:
    for value, expected_word in (
        (-32768, 0x8000),
        (-1, 0xFFFF),
        (32768, 0x8000),
        (65535, 0xFFFF),
    ):
        source = f"""
table: DW {value}
main:
    HLT
"""

        result = compile_program(source, run_static_checks=False)

        assert not result.has_errors()
        assert result.ir is not None
        assert [diag.code for diag in result.diagnostics] == []
        assert result.initial_data_image[0].value == expected_word


def test_dw_signed_underflow_reports_i002() -> None:
    source = """
table: DW -32769
main:
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert not result.has_errors()
    assert result.ir is not None
    i002 = [diag for diag in result.diagnostics if diag.code == "I002"]
    assert len(i002) == 1
    assert (
        i002[0].message
        == "DW initializer -32769 will be stored as 16-bit word 32767 (0x7FFF)"
    )
    assert result.initial_data_image[0].value == 0x7FFF


def test_ld_accepts_data_label_as_absolute_address() -> None:
    source = """
table: DW 7
main:
    LD $1, table
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert not result.has_errors()
    assert result.ir is not None
    operand = result.ir.instructions[0].operands[1]
    assert isinstance(operand, AddressOperand)
    assert operand.offset == 0
    assert operand.base.index == 0


def test_split_line_dw_label_resolves_as_data_address() -> None:
    source = """
table:
    DW 7
main:
    LD $1, table
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert not result.has_errors()
    assert result.ir is not None
    assert result.typed_symbols["TABLE"].kind is SymbolKind.DATA
    assert result.typed_symbols["TABLE"].address == 0
    operand = result.ir.instructions[0].operands[1]
    assert isinstance(operand, AddressOperand)
    assert operand.offset == 0
    assert operand.base.index == 0


def test_consecutive_split_line_labels_alias_same_dw_address() -> None:
    source = """
first:
second:
    DW 9
main:
    LD $1, first
    LD $2, second
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert not result.has_errors()
    assert result.ir is not None
    assert result.typed_symbols["FIRST"].kind is SymbolKind.DATA
    assert result.typed_symbols["SECOND"].kind is SymbolKind.DATA
    assert result.typed_symbols["FIRST"].address == 0
    assert result.typed_symbols["SECOND"].address == 0
    first_operand = result.ir.instructions[0].operands[1]
    second_operand = result.ir.instructions[1].operands[1]
    assert isinstance(first_operand, AddressOperand)
    assert isinstance(second_operand, AddressOperand)
    assert first_operand.offset == 0
    assert second_operand.offset == 0


def test_lda_accepts_data_label_as_absolute_address() -> None:
    source = """
pad: DW 11
table: DW 22
main:
    LDA $1, table
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert not result.has_errors()
    assert result.ir is not None
    operand = result.ir.instructions[0].operands[1]
    assert isinstance(operand, AddressOperand)
    assert operand.offset == 1
    assert operand.base.index == 0


def test_data_label_outside_imm8_absolute_range_reports_s009() -> None:
    source = "main:\n    LD $1, table\n    HLT\n"
    source += "\n".join(f"d{i}: DW {i}" for i in range(130))
    source += "\ntable: DW 999\n"

    result = compile_program(source, run_static_checks=False)

    assert result.has_errors()
    assert result.ir is None
    assert [diag.code for diag in result.diagnostics] == ["S009"]
    assert result.diagnostics[0].message == (
        "Data label 'table' at address 130 cannot be used as a bare absolute "
        "address; SN/X I-type immediates are limited to -128..127"
    )


def test_branch_to_data_label_reports_s008() -> None:
    source = """
table: DW 1
main:
    BZ $1, table
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert result.has_errors()
    assert result.ir is None
    assert [diag.code for diag in result.diagnostics] == ["S008"]
    assert result.diagnostics[0].message == (
        "Data label 'table' cannot be used as a code target"
    )


def test_ld_with_code_label_reports_s007() -> None:
    source = """
main:
    LD $1, done
done:
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert result.has_errors()
    assert result.ir is None
    assert [diag.code for diag in result.diagnostics] == ["S007"]
    assert result.diagnostics[0].message == (
        "Code label 'done' cannot be used as a data address"
    )


def test_bal_label_form_rejects_data_labels() -> None:
    source = """
table: DW 1
main:
    BAL $2, table
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert result.has_errors()
    assert result.ir is None
    assert [diag.code for diag in result.diagnostics] == ["S008"]
    assert result.diagnostics[0].message == (
        "Data label 'table' cannot be used as a code target"
    )


def test_malformed_split_line_dw_reports_only_p007() -> None:
    source = """
table:
    DW
main:
    LD $1, table
    HLT
"""

    result = compile_program(source, run_static_checks=False)

    assert result.has_errors()
    assert result.ir is None
    assert [diag.code for diag in result.diagnostics] == ["P007"]
    assert result.diagnostics[0].message == (
        "DW requires one or more signed decimal initializers"
    )
