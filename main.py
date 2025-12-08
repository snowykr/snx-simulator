from snx import SNXSimulator
from snx.trace import format_trace_header, format_trace_row, format_trace_separator

SAMPLE_PROGRAM = """
main:
    LDA $3, 64($0)
    LDA $1, 3($0)
    BAL $2, foo
    HLT

foo:
    LDA $3, -2($3)
    ST  $2, 0($3)
    ST  $1, 1($3)
    LDA $0, 2($0)
    SLT $0, $1, $0
    BZ  $0, foo2
foo1:
    LD  $2, 0($3)
    LDA $3, 2($3)
    BAL $2, 0($2)
foo2:
    LDA $1, -1($1)
    BAL $2, foo
    LDA $3, -1($3)
    ST  $1, 0($3)
    LD  $1, 2($3)
    LDA $1, -2($1)
    BAL $2, foo
    LD  $2, 0($3)
    LDA $3, 1($3)
    ADD $1, $1, $2
    BAL $0, foo1
"""


def main() -> None:
    def trace_printer(pc: int, inst_raw: str, regs: list[int]) -> None:
        init_flags = sim.get_reg_init_flags()
        print(format_trace_row(pc, inst_raw, regs, init_flags))

    sim = SNXSimulator.from_source(SAMPLE_PROGRAM, trace_callback=trace_printer)

    print(format_trace_header())
    print(format_trace_separator())

    sim.run()


if __name__ == "__main__":
    main()