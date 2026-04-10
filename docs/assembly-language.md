# SN/X Assembly Language

This document defines the syntax of the SN/X assembly language.

## Informal Overview

An SN/X assembly program consists of lines. Each line may contain:
- An optional **label definition** (an identifier followed by `:`)
- An optional **instruction or directive**
- An optional **comment** (starting with `;` and extending to the end of the line)

Empty lines and comment-only lines are allowed.

## Lexical Grammar

The lexer splits the input into the following token kinds:

| Token Kind | Description                                      | Examples            |
|------------|--------------------------------------------------|---------------------|
| IDENT      | Identifiers for labels and mnemonics             | `main`, `LDA`, `foo`|
| NUMBER     | Signed decimal integers                          | `42`, `-3`, `+10`   |
| REGISTER   | Register names (`$` followed by digits)          | `$0`, `$2`, `$3`    |
| COMMA      | `,`                                              |                     |
| COLON      | `:`                                              |                     |
| LPAREN     | `(`                                              |                     |
| RPAREN     | `)`                                              |                     |
| EOL        | End-of-line marker (produced for each newline)   |                     |
| EOF        | End-of-file marker                               |                     |

Comments start with `;` and continue to the end of the line. They are discarded by the lexer.

In EBNF notation:

```ebnf
identifier  = letter , { letter | digit | "_" } ;
number      = [ "+" | "-" ] , digit , { digit } ;
register    = "$" , digit , { digit } ;

letter      = "A".."Z" | "a".."z" ;
digit       = "0".."9" ;
```

Identifiers and mnemonics are case-insensitive; they are normalized to uppercase internally.

## Concrete Syntax Grammar (BNF / CFG)

The following context-free grammar (CFG), written in BNF, defines the concrete syntax of the SN/X assembly language:

```bnf
<program>           ::= <line>* <eof>

<line>              ::= [<label-def>] [<instruction> | <directive>] <eol>

<label-def>         ::= <identifier> ":"

<instruction>       ::= <mnemonic> [<operand-list>]

<directive>         ::= "DW" <dw-initializer-list>

<dw-initializer-list> ::= NUMBER ("," NUMBER)*

<mnemonic>          ::= <identifier>

<operand-list>      ::= <operand> ("," <operand>)*

<operand>           ::= <register-operand>
                      | <address-operand>
                      | <label-ref-operand>

<register-operand>  ::= REGISTER

<address-operand>   ::= NUMBER "(" REGISTER ")"
                      | NUMBER

<label-ref-operand> ::= <identifier>

<eol>               ::= EOL | <eof>
<eof>               ::= EOF
```

**Notes:**
- When `<address-operand>` is written as just `NUMBER` (without parentheses), the base register defaults to `$0`.
- `<mnemonic>` is matched against the supported opcodes (`ADD`, `AND`, `SUB`, `SLT`, `NOT`, `SR`, `HLT`, `LD`, `ST`, `LDA`, `IN`, `OUT`, `BZ`, `BAL`). Unknown mnemonics produce a diagnostic error.
- Labels and mnemonics are case-insensitive.
- `DW` defines one or more 16-bit data words in DMEM. It accepts decimal integer literals written with the same optional-sign `NUMBER` syntax as the rest of the language. Any initializer already representable as a single 16-bit word (`-32768..65535`) is stored without `I002`; values outside that range are normalized modulo 16 bits with warning `I002`.
- A label on a `DW` line binds to the first allocated data address for that line.
- `DW` is DMEM-only. Source-order allocation starts at address 0 and is preloaded into the simulator memory before execution.
- Bare identifiers are domain-sensitive: `LD`, `ST`, and `LDA` accept bare DATA labels in their address slot and lower them to `$0`-based addresses when the resolved DMEM address is representable by SN/X's signed 8-bit I-type immediate semantics without changing the effective 16-bit address (that is, addresses `0..127` and `65408..65535`); `BZ` and label-form `BAL` accept bare CODE labels only.
- Bare DATA labels are not general-purpose shorthand for all address-like operands. In particular, `BAL $r, DATA_LABEL` is rejected instead of being reinterpreted as a data jump.
- Bare DATA labels whose resolved DMEM address would change under `$0`-based signed-imm8 encoding are rejected at compile time (`S009`) instead of silently assembling to a different address.
- Typed Label Example:
  ```asm
  main:
      LD $1, my_val      ; OK: LD uses DATA label 'my_val'
      OUT $1
      BZ $1, main        ; OK: BZ uses CODE label 'main'
      HLT
  my_val:
      DW 100, -1, 42     ; Allocates DMEM[0]=100, DMEM[1]=-1, DMEM[2]=42
  ```

## Operand Types by Instruction

| Instruction | Operand 1       | Operand 2                  | Operand 3       |
|-------------|-----------------|----------------------------|-----------------|
| ADD         | Register        | Register                   | Register        |
| AND         | Register        | Register                   | Register        |
| SUB         | Register        | Register                   | Register        |
| SLT         | Register        | Register                   | Register        |
| NOT         | Register        | Register                   |                 |
| SR          | Register        | Register                   |                 |
| HLT         |                 |                            |                 |
| LD          | Register        | Address                    |                 |
| ST          | Register        | Address                    |                 |
| LDA         | Register        | Address                    |                 |
| IN          | Register        |                            |                 |
| OUT         | Register        |                            |                 |
| BZ          | Register        | Label                      |                 |
| BAL         | Register        | Label or Address           |                 |

## Related Documentation

- [Architecture](architecture.md) for instruction encoding and ISA details
- [Static Analysis](static-analysis.md) for diagnostic codes
