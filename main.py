from snx import SNXSimulator
from snx.trace import format_trace_header, format_trace_row, format_trace_separator

SAMPLE_PROGRAM = """
main:
    LDA $3, 64($0)  ; 초기 SP 설정
    LDA $1, 3($0)   ; 입력값 x=3 설정
    BAL $2, foo     ; foo 호출
    HLT             ; 종료
foo:
    LDA $3, -2($3)
    ST  $2, 0($3)
    ST  $1, 1($3)
    LDA $0, 2($0)   ; 상수 2
    SLT $0, $1, $0  ; x < 2 ?
    BZ  $0, foo2
foo1:
    LD  $2, 0($3)
    LDA $3, 2($3)
    BAL $2, 0($2)   ; 리턴 (BAL $0이 아니라 보통 $2 레지스터 값으로 복귀)
foo2:
    LDA $1, -1($1)
    BAL $2, foo
    LDA $3, -1($3)  ; PUSH result
    ST  $1, 0($3)
    LD  $1, 2($3)   ; x 복구 (offset 주의)
    LDA $1, -2($1)
    BAL $2, foo
    LD  $2, 0($3)   ; POP result
    LDA $3, 1($3)
    ADD $1, $1, $2
    BAL $0, foo1    ; 에필로그 점프
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