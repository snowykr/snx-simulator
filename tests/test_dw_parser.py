from snx.ast import DirectiveKind
from snx.parser import parse


def test_parses_labeled_dw_signed_decimal_list() -> None:
    result = parse("table: DW 1, -2, +3\n")

    assert result.program is not None
    assert result.diagnostics == []

    line = result.program.lines[0]
    assert line.label is not None
    assert line.label.name == "TABLE"
    assert line.instruction is None
    assert line.directive is not None
    assert line.directive.kind is DirectiveKind.DW
    assert line.directive.keyword == "DW"
    assert line.directive.values == (1, -2, 3)
    assert line.directive.text == "DW 1, -2, +3"


def test_parses_unlabeled_dw_signed_decimal_list() -> None:
    result = parse("dw -7, 0, +12\n")

    assert result.program is not None
    assert result.diagnostics == []

    line = result.program.lines[0]
    assert line.label is None
    assert line.instruction is None
    assert line.directive is not None
    assert line.directive.kind is DirectiveKind.DW
    assert line.directive.keyword == "dw"
    assert line.directive.values == (-7, 0, 12)
    assert line.content is line.directive


def test_dw_requires_at_least_one_initializer() -> None:
    result = parse("DW\n")

    assert result.program is not None
    assert [d.code for d in result.diagnostics] == ["P007"]
    assert (
        result.diagnostics[0].message
        == "DW requires one or more signed decimal initializers"
    )

    line = result.program.lines[0]
    assert line.instruction is None
    assert line.directive is None


def test_dw_rejects_hex_literal_in_v1() -> None:
    result = parse("DW 0x10\n")

    assert result.program is not None
    assert [d.code for d in result.diagnostics] == ["P007"]
    assert (
        result.diagnostics[0].message
        == "DW requires one or more signed decimal initializers"
    )

    line = result.program.lines[0]
    assert line.instruction is None
    assert line.directive is None


def test_rejects_label_with_parenthesized_suffix() -> None:
    result = parse("LD $1, table($2)\n")

    assert result.program is not None
    assert [d.code for d in result.diagnostics] == ["P003"]
    assert result.diagnostics[0].message == "Unexpected token: '('"

    line = result.program.lines[0]
    assert line.instruction is not None
    assert line.directive is None
