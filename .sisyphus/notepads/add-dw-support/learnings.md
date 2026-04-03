
- Task 1 established the first repo-native pytest harness by adding a `dependency-groups.dev` entry in `pyproject.toml`; `uv sync --dev` is now the matching local/CI install path for tests.
- The current instruction-only happy path is cleanly exercised through the public API pair `compile_program(...)` and `SNXSimulator.from_compile_result(...)`, so smoke coverage can stay stable while DW support is added later.
- Invalid opcodes currently surface parser/compiler diagnostic code `S001` with an `Unknown instruction: '...` message, which is a stable negative smoke assertion for baseline coverage.
- Existing label names in compiled IR are normalized to uppercase (`main` becomes `MAIN`), so DW-facing compatibility tests should assert normalized symbol keys rather than source-case spellings.
- The safest additive seam for Task 2 is `IRProgram` plus `CompileResult`: new DW metadata can live alongside instruction-only fields without changing `IRProgram.instructions` or `encode_program(ir_program)` consumers.
- Task 3 can stay parser-only because the existing tokenizer already recognizes signed decimal literals (`+3`, `-2`) and case-normalized identifiers, so `DW` support only needs a parser branch before opcode lookup rather than new token kinds or hex parsing.
- Rejecting invalid `DW` forms is most stable when the parser treats any non-`EOL` trailing token after a signed-decimal comma list as a single `P007` failure; this cleanly rejects `DW`, `DW 1,`, `DW 0x10`, and `DW 1+2` without letting the line masquerade as an instruction.
- Task 4 keeps `IRProgram.labels` instruction-only for existing branch/encoding consumers, while `IRProgram.typed_symbols` becomes the global namespace that carries both code and data labels with distinct kinds.
- DW allocation works cleanly as a source-order side pass in the analyzer: instruction lines advance `code_pc`, DW lines advance `data_addr`, and `initial_data_image` can be built deterministically without changing instruction emission order.
- Task 5 fits cleanly in the analyzer by broadening the operand spec for `LD`/`ST`/`LDA` to admit bare label operands, then resolving them semantically by typed symbol kind before IR emission; this preserves parser behavior while keeping the lowering decision context-sensitive.
- Lowering valid DATA labels to `AddressOperand(offset=<data_addr>, base=$0)` inside `InstructionIR` lets existing memory-bounds and encoding paths keep treating them as ordinary absolute addresses, so no `encoding.py` changes were required.
- The stable cross-domain diagnostics split naturally by operand role: DATA-address contexts report `S007` for CODE labels, while CODE-target contexts (`BZ` and label-form `BAL`) report `S008` for DATA labels.
- Task 6 fits entirely inside `SNXSimulator.__init__`: preloading each `IRProgram.initial_data_image` word through the existing `_set_mem(...)` path initializes both DMEM contents and `get_memory_init_flags()` before the first instruction without changing the instruction tuple or `step()` logic.
- Task 7 can stay API-compatibility-only in tests because `encode_program(ir_program)` already iterates just `IRProgram.instructions`, so additive DW metadata on `typed_symbols` and `initial_data_image` does not affect executable output bytes.
- `parse_code()` still delegates through `compile_program(...)` but materializes only the analyzed instruction list plus `dict(ir.labels)`, which keeps DATA labels and DW image metadata out of its legacy two-tuple contract.

## Task 8 Refinement - Label Syntax
- The SN/X parser currently ignores trailing parenthesized registers after a label reference (e.g., `my_data($0)`). 
- To avoid confusion and align with the intended contract, examples and tests now strictly use bare labels (e.g., `my_data`) for `LD`, `ST`, and `LDA`.
- Dataflow analysis correctly accounts for `DW` preloaded data by initializing the corresponding stack slots (address 1000+) in the entry state.

## Final Review Correction - Bare Label Syntax
- Confirmed that the assembler implements bare data-label syntax for `LD/ST/LDA`.
- All documentation (README.md, docs/assembly-language.md) and tests (tests/test_cli_dw.py) have been verified to use `LD $1, my_data` instead of `LD $1, my_data($0)`.
- Python API documentation now includes `typed_symbols` and `initial_data_image` in the `CompileResult` section.

## Static Analysis Documentation Fix
- Updated `docs/static-analysis.md` to include `P007` diagnostic code for invalid `DW` initializers.
- Corrected `S007` example to use bare-label syntax (`LD $1, main`) instead of the accidental `label($reg)` form.
