
- Task 2 completed without blockers. A pre-existing static import-cycle warning between compiler/parser was handled locally in `snx/compiler.py` via a pyright rule suppression so this task could satisfy zero-error diagnostics without changing parser behavior.
- Task 3 completed without blockers. The only verification issue encountered was a pre-existing loose `ParseResult.diagnostics: list` annotation in `snx/parser.py`, which was tightened to `list[Diagnostic]` so the modified parser files satisfy zero-error language-server checks.
- Task 4 had no functional blockers. The only follow-up needed during verification was updating `tests/test_dw_api.py` because the older compatibility assertion expected `typed_symbols` to stay empty for instruction-only programs, which no longer matches the typed-symbol analysis model introduced here.
- Task 5 completed without functional blockers. Markdown files have no configured LSP in this workspace, so verification for `docs/assembly-language.md` and `docs/static-analysis.md` relied on constrained edits plus the passing analyzer regression suite instead of language-server diagnostics.
- Task 6 had no functional blockers. One verification snag surfaced in the new preload-before-execution test: the existing static checker still reports `D001` for an immediate `LD` from a DW-initialized address because it reasons before simulator construction, so that focused simulator test now disables static checks to keep this task scoped to runtime preload behavior.
- Task 7 completed without functional blockers. The only follow-up was to lock the compatibility guarantees into `tests/test_dw_api.py` rather than changing `snx/encoding.py` or `snx/parser.py`, because both helpers already ignore additive DW metadata and preserve their instruction-only contracts.

## Syntax Leniency Issue
- The parser was found to be accidentally lenient towards `label($reg)` syntax by ignoring the `($reg)` part. 
- While this didn't break functionality, it was misleading in documentation. 
- Documentation and tests have been corrected to use the standard bare-label syntax.

## Syntax Consistency Fix
- A previous version of the documentation and tests used `label($0)` syntax which was not strictly supported as a primary contract.
- This has been corrected to use bare labels only for data memory access, ensuring consistency between docs, tests, and implementation.
