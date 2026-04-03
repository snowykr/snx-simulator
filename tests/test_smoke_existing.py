from snx import SNXSimulator, compile_program


def test_instruction_only_program_compiles_and_runs() -> None:
    source = """
main:
    LDA $1, 5($0)
    HLT
"""

    result = compile_program(source)

    assert not result.has_errors()
    assert result.ir is not None

    sim = SNXSimulator.from_compile_result(result)
    sim.run()

    assert sim.regs[1] == 5
    assert sim.pc == 2
    assert sim.running is False
    assert sim.get_reg_init_flags()[1] is True
    assert not any(sim.get_memory_init_flags())


def test_invalid_opcode_reports_error() -> None:
    result = compile_program("BOGUS $1, 5($0)\n")

    assert result.has_errors()
    assert result.ir is None
    assert any(d.code == "S001" for d in result.diagnostics)
    assert "Unknown instruction: 'BOGUS'" in result.format_diagnostics()
