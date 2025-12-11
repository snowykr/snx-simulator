main:
    LDA $3, 64($0)
    LDA $1, 3($0)
    BAL $2, foo
    HLT
foo:
    LDA $3, 254($3)
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
    LDA $1, 255($1)
    BAL $2, foo
    LDA $3, 255($3)
    ST  $1, 0($3)
    LD  $1, 2($3)
    LDA $1, 254($1)
    BAL $2, foo
    LD  $2, 0($3)
    LDA $3, 1($3)
    ADD $1, $1, $2
    BAL $0, foo1
