from snx import SNXSimulator, compile_program


def test_dw_initializes_memory_before_execution() -> None:
    source = """
table: DW 7, 8
main:
    LD $1, table
    HLT
"""

    result = compile_program(source)

    assert not result.has_errors()
    assert result.ir is not None

    sim = SNXSimulator.from_compile_result(result)

    assert sim.memory[0] == 7
    assert sim.memory[1] == 8
    assert sim.regs[1] == 0

    _ = sim.step()

    assert sim.regs[1] == 7


def test_dw_sets_memory_init_flags_before_execution() -> None:
    source = """
table: DW 11, 12
main:
    HLT
"""

    sim = SNXSimulator.from_source(source)

    flags = sim.get_memory_init_flags()

    assert flags[0] is True
    assert flags[1] is True
    assert not any(flags[2:])


def test_store_can_overwrite_preloaded_dw_word() -> None:
    source = """
table: DW 7
main:
    LDA $1, 99($0)
    ST $1, table
    LD $2, table
    HLT
"""

    sim = SNXSimulator.from_source(source)

    assert sim.memory[0] == 7

    sim.run()

    assert sim.memory[0] == 99
    assert sim.regs[2] == 99
    assert sim.get_memory_init_flags()[0] is True


def test_data_only_program_preloads_without_crashing() -> None:
    source = """
table: DW 3, 4, 5
"""

    sim = SNXSimulator.from_source(source)

    assert sim.instructions == ()
    assert sim.memory[:3] == [3, 4, 5]
    assert sim.get_memory_init_flags()[:3] == (True, True, True)

    sim.run()

    assert sim.running is False
    assert sim.pc == 0


def test_dw_preload_oob_callback_does_not_crash_with_smaller_runtime_mem() -> None:
    source = """
table: DW 7, 8, 9
main:
    HLT
"""

    result = compile_program(source, mem_size=4)

    assert not result.has_errors()

    calls: list[tuple[str, int, int, str, int]] = []

    def on_oob(
        kind: str, addr: int, current_pc: int, current_inst_text: str, mem_size: int
    ) -> None:
        calls.append((kind, addr, current_pc, current_inst_text, mem_size))

    sim = SNXSimulator.from_compile_result(result, mem_size=2, oob_callback=on_oob)

    assert sim.memory[:2] == [7, 8]
    assert sim.get_memory_init_flags()[:2] == (True, True)
    assert calls == [("store", 2, 0, "", 2)]
