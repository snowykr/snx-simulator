import sys

from snx import SNXSimulator, compile_program
from snx.trace import format_trace_header, format_trace_row, format_trace_separator

SAMPLE_PROGRAM = """
main:
    LDA $3, 64($0)  ; initialize SP
    LDA $1, 3($0)   ; set input x=3
    BAL $2, foo     ; call foo
    HLT             ; halt
foo:
    LDA $3, -2($3)
    ST  $2, 0($3)
    ST  $1, 1($3)
    LDA $0, 2($0)   ; constant 2
    SLT $0, $1, $0  ; x < 2 ?
    BZ  $0, foo2
foo1:
    LD  $2, 0($3)
    LDA $3, 2($3)
    BAL $2, 0($2)   ; return via $2
foo2:
    LDA $1, -1($1)
    BAL $2, foo
    LDA $3, -1($3)  ; push result
    ST  $1, 0($3)
    LD  $1, 2($3)   ; restore x
    LDA $1, -2($1)
    BAL $2, foo
    LD  $2, 0($3)   ; pop result
    LDA $3, 1($3)
    ADD $1, $1, $2
    BAL $0, foo1    ; jump to epilogue
"""


def main() -> None:
    result = compile_program(SAMPLE_PROGRAM)
    
    print("=== Static Analysis Result ===")
    print(result.format_diagnostics())
    print()
    
    if result.has_errors():
        print("Build failed due to errors above.")
        sys.exit(1)
    
    if result.has_warnings():
        print("Build succeeded with warnings.")
        print()
    
    def trace_printer(pc: int, inst_raw: str, regs: list[int]) -> None:
        init_flags = sim.get_reg_init_flags()
        print(format_trace_row(pc, inst_raw, regs, init_flags))

    sim = SNXSimulator.from_compile_result(result, trace_callback=trace_printer)

    print("=== Execution Trace ===")
    print(format_trace_header())
    print(format_trace_separator())

    sim.run()
    
    print()
    print("=== Execution completed successfully ===")


if __name__ == "__main__":
    main()