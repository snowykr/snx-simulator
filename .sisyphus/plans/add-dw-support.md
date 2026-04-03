# Add DW Directive Support to SN/X Simulator

## TL;DR
> **Summary**: Add a conventional `DW` assembler directive to the SN/X toolchain as a **DMEM-only initialized-data feature** that fits the repository's split instruction/data architecture instead of forcing data words into executable PC slots.
> **Deliverables**:
> - DW-aware lexer/parser/AST/analysis pipeline
> - Typed code/data symbol resolution and compile-time data image
> - Simulator DMEM preloading from compiled DW data
> - Pytest + CI coverage for parser, analyzer, simulator, API, and CLI flows
> - Updated assembly-language/API documentation for DW semantics
> **Effort**: Large
> **Parallel**: YES - 7 waves
> **Critical Path**: 2 → 3 → 4 → 5 → 6 → 8

## Context
### Original Request
- Issue #8: `Add DW Support`
- User requirement: preserve the general `DW` concept, but implement it in a way that matches this repository's SN/X architecture.

### Interview Summary
- Repository context establishes this is an assembler/static-analyzer/simulator, not an editor (`README.md:3-10`).
- Current grammar only supports labels + instructions; no directives exist (`docs/assembly-language.md:7-10`, `docs/assembly-language.md:45-80`).
- Current compile pipeline is instruction-only: parse → analyze → optional static checks (`snx/compiler.py:54-120`).
- Runtime model already separates executable instructions from data memory (`snx/simulator.py:37-52`, `snx/simulator.py:142-153`).
- No repo test harness or CI test job exists yet (`pyproject.toml:1-26`, `.github/workflows/publish.yml:1-52`).

### Metis Review (gaps addressed)
- Locked v1 to **DW only**; explicitly excluded generic directive work (`ORG`, `DB`, macros, expressions, strings).
- Chose **DMEM-only** semantics to avoid fighting the existing split IMEM/DMEM architecture.
- Chose **typed symbol resolution** so code labels and data labels cannot be confused.
- Added explicit misuse diagnostics for cross-domain references.
- Added mandatory pytest/CI setup so feature verification is automated from the first implementation slice.

## Work Objectives
### Core Objective
Implement `DW` as an initialized data directive that allocates sequential 16-bit DMEM words, binds an optional label to the first allocated word, and makes those data labels usable in absolute-address instruction contexts without changing executable PC sequencing.

### Deliverables
- Parser support for `DW value[, value, ...]` on normal source lines
- AST/IR/compiler support for directive nodes, typed symbols, and compiled initial data image
- Analyzer support for separate code-PC and data-address counters
- Address-resolution rules that allow data labels in absolute address positions and reject cross-domain misuse
- Simulator preloading of compiled DW data into `memory` and `get_memory_init_flags()`
- Pytest suite and CI job covering parser, analyzer, simulator, API, and CLI behavior
- Updated docs describing DW syntax, semantics, limits, and architectural adaptation

### Definition of Done (verifiable conditions with commands)
- `python -m pytest tests/test_dw_parser.py -q`
- `python -m pytest tests/test_dw_analyzer.py -q`
- `python -m pytest tests/test_dw_simulator.py -q`
- `python -m pytest tests/test_dw_api.py -q`
- `python -m pytest tests/test_cli_dw.py -q`
- `python -m pytest -q`

### Must Have
- `DW` is case-insensitive and parsed as a directive, not an opcode.
- Supported v1 syntax: `DW <signed-decimal>[, <signed-decimal> ...]` with optional leading `label:` on the same line.
- Each initializer occupies one 16-bit DMEM word; values are stored modulo 16 bits via the existing word model.
- Data allocation uses a dedicated DMEM address counter starting at `0`; executable PC numbering remains instruction-only.
- Labels on instruction lines resolve to code targets; labels on DW lines resolve to data addresses.
- Bare data labels are accepted only in absolute address operand contexts for `LD`, `ST`, and `LDA`, where they lower to `$0`-based absolute addresses.
- `BZ` and label-form `BAL` require code labels only.
- Duplicate identifiers remain illegal across the whole program, even if one occurrence would otherwise be code-scoped and the other data-scoped.
- Cross-domain label misuse is a compile-time error with stable diagnostic codes/messages.
- Simulator memory is preinitialized from compiled DW data before the first instruction executes, and the corresponding memory-init flags are set.
- Existing instruction encoding behavior remains unchanged for instruction-only programs.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- Must NOT introduce `DB`, `ORG`, expressions, strings, char literals, hex/binary literals, `DUP`, macros, or a generic directive framework in this issue.
- Must NOT change executable PC counting to include DW lines.
- Must NOT collapse the current split instruction/data architecture into a unified execution memory model.
- Must NOT silently allow code-label/data-label interchange.
- Must NOT mutate public behavior of instruction-only programs beyond additive metadata/API fields needed for DW.

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: **tests-after** with `pytest` (newly added in this work)
- QA policy: Every task has agent-executed scenarios
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`
- Evidence directory policy: create `.sisyphus/evidence/` on first verification-producing task if it does not already exist

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: 1) pytest/CI scaffold
Wave 2: 2) compiler-model extensions
Wave 3: 3) parser support
Wave 4: 4) analyzer data-allocation core
Wave 5: 5) operand/domain resolution
Wave 6: 6) simulator preload + 7) API/encoding compatibility
Wave 7: 8) docs + CLI/end-to-end regression

### Dependency Matrix (full, all tasks)
- 1 blocks 2-8 by establishing the test/CI harness.
- 2 blocks 3-7 by introducing directive/data-image model surfaces.
- 3 blocks 4-5 by making DW syntax available to downstream phases.
- 4 blocks 5-7 by creating typed symbols and compiled data-address accounting.
- 5 blocks 6-8 by defining how data labels are consumed and diagnosed.
- 6 depends on 2, 4, 5.
- 7 depends on 2, 4, 5.
- 8 depends on 1-7.

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 1 task → `unspecified-high`
- Wave 2 → 1 task → `deep`
- Wave 3 → 1 task → `unspecified-high`
- Wave 4 → 1 task → `deep`
- Wave 5 → 1 task → `deep`
- Wave 6 → 2 tasks → `unspecified-high`
- Wave 7 → 1 task → `writing`
- Final Verification → 4 tasks → `oracle`, `unspecified-high`, `deep`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Establish pytest + CI DW verification baseline

  **What to do**: Add a repo-native test harness before feature work lands. Update `pyproject.toml` to carry a dev/test dependency strategy compatible with `uv`, create `tests/` with a smoke suite that covers the current instruction-only compile/run path, and add a dedicated GitHub Actions workflow that runs `python -m pytest -q` on pushes/PRs. Keep the publish workflow intact; add a separate test workflow rather than overloading `.github/workflows/publish.yml`.
  **Must NOT do**: Do not modify runtime logic in this task. Do not tie tests to network access, PyPI publish steps, or manual CLI output inspection.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: small cross-cutting repo setup plus automated verification
  - Skills: `[]` — no special skill required
  - Omitted: `['playwright']` — no browser/UI surface exists

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2, 3, 4, 5, 6, 7, 8] | Blocked By: []

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `pyproject.toml:1-26` — current packaging metadata; place dev/test configuration here instead of adding a second project manifest
  - Pattern: `.github/workflows/publish.yml:1-52` — existing workflow style; add a separate test workflow rather than mixing publish and test responsibilities
  - Pattern: `snx/compiler.py:96-120` — canonical compile entrypoint to exercise in smoke tests
  - Pattern: `snx/simulator.py:57-105` — canonical simulator constructors to exercise in smoke tests
  - Pattern: `snx/runner.py:38-93` — end-to-end CLI flow to mirror in later CLI tests

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m pytest tests/test_smoke_existing.py -q` passes
  - [ ] `python -m pytest tests/test_smoke_existing.py::test_invalid_opcode_reports_error -q` passes
  - [ ] `python - <<'PY'
from pathlib import Path
text = Path('.github/workflows/test.yml').read_text(encoding='utf-8')
assert 'pytest -q' in text
assert 'uv sync --dev' in text or 'uv run' in text
print('workflow ok')
PY` passes

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Existing instruction-only smoke path stays green
    Tool: Bash
    Steps: run `python -m pytest tests/test_smoke_existing.py -q`
    Expected: exit code 0; evidence shows compile+simulate smoke coverage runs under pytest
    Evidence: .sisyphus/evidence/task-1-pytest-baseline.txt

  Scenario: Negative smoke case is asserted, not manual
    Tool: Bash
    Steps: run `python -m pytest tests/test_smoke_existing.py::test_invalid_opcode_reports_error -q`
    Expected: exit code 0; test proves invalid source is reported as a compiler error
    Evidence: .sisyphus/evidence/task-1-pytest-baseline-negative.txt
  ```

  **Commit**: YES | Message: `test(ci): add pytest harness for dw coverage` | Files: [`pyproject.toml`, `.github/workflows/test.yml`, `tests/test_smoke_existing.py`]

- [x] 2. Extend compiler models for directives, typed symbols, and initial data image

  **What to do**: Introduce the structural model changes DW needs before parser/analyzer work lands. Add AST types for directive-bearing lines (for v1, only `DW`), extend IR/compile-result structures so compiled output can carry: (a) executable instructions, (b) typed symbol tables or equivalent typed symbol metadata, and (c) a deterministic initial DMEM image. Preserve backward compatibility for instruction-only callers by keeping existing methods usable and making new DW metadata additive.
  **Must NOT do**: Do not parse DW syntax yet in this task. Do not preload simulator memory yet. Do not break `encode_program(ir_program)` for instruction-only programs.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: this is the central architecture seam shared by parser, analyzer, simulator, and API consumers
  - Skills: `[]` — no special skill required
  - Omitted: `['playwright']` — no browser/UI surface exists

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [3, 4, 5, 6, 7, 8] | Blocked By: [1]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `snx/ast.py:35-104` — current AST/IR models only represent labels, operands, instructions, and instruction-only IR
  - Pattern: `snx/compiler.py:17-120` — `CompileResult` is the public aggregation point for parser/analyzer/checker outputs
  - Pattern: `snx/__init__.py:1-59` — public API re-exports that may need additive exposure of new compile metadata
  - Pattern: `docs/python-api.md:34-66` — documented `CompileResult` contract that must stay coherent after new fields are added
  - Pattern: `docs/architecture.md:15-18` — SN/X is 16-bit and split between instruction/data memory concepts; the model must reflect that rather than unified PC allocation

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m pytest tests/test_dw_api.py::test_compile_result_exposes_initial_data_image -q` passes
  - [ ] `python -m pytest tests/test_dw_api.py::test_compile_result_exposes_typed_symbols -q` passes
  - [ ] `python -m pytest tests/test_dw_api.py::test_instruction_only_program_retains_compatible_compile_result_shape -q` passes

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Instruction-only compile result remains backward compatible
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_api.py::test_instruction_only_program_retains_compatible_compile_result_shape -q`
    Expected: exit code 0; legacy instruction-only compile path still exposes working `ir`, diagnostics helpers, and no DW-specific breakage
    Evidence: .sisyphus/evidence/task-2-compile-model-compat.txt

  Scenario: New compile metadata is available for DW-aware consumers
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_api.py::test_compile_result_exposes_initial_data_image -q tests/test_dw_api.py::test_compile_result_exposes_typed_symbols -q`
    Expected: exit code 0; compile result carries deterministic data-image and typed symbol metadata for downstream analyzer/simulator use
    Evidence: .sisyphus/evidence/task-2-compile-model-dw.txt
  ```

  **Commit**: NO | Message: `feat(parser): add dw directive syntax and compiler data model` | Files: [`snx/ast.py`, `snx/compiler.py`, `snx/__init__.py`, `tests/test_dw_api.py`]

- [x] 3. Parse `DW` lines and signed-decimal initializer lists

  **What to do**: Extend lexer/parser behavior so `DW` is recognized as a directive line and lowered into the new AST representation. Support the v1 grammar exactly: optional `label:` followed by case-insensitive `DW` and one or more comma-separated signed decimal integers. Preserve the existing tokenizer rules for decimal numbers, commas, identifiers, and comments; do not add hex, strings, char literals, or expression parsing. Add a stable parse diagnostic for invalid or missing DW initializer lists (`P007`: `DW requires one or more signed decimal initializers`).
  **Must NOT do**: Do not accept `0x10`, `'A'`, `1+2`, or empty `DW`. Do not reinterpret `DW` as an opcode. Do not require dot-prefixed directives.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: localized grammar/parser work with precise failure modes
  - Skills: `[]` — no special skill required
  - Omitted: `['playwright']` — no browser/UI surface exists

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [4, 5, 6, 7, 8] | Blocked By: [1, 2]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `snx/tokenizer.py:79-166` — existing tokenization of identifiers, signed decimal numbers, commas, comments, and invalid characters
  - Pattern: `snx/parser.py:92-164` — line parsing and operand-list parsing entry points that need directive branching
  - Pattern: `docs/assembly-language.md:7-10` — current line model (label + instruction + comment) that must be expanded to mention directives
  - Pattern: `docs/assembly-language.md:45-80` — grammar section that must be updated to include DW without widening beyond v1 scope
  - External: `https://learn.microsoft.com/en-us/cpp/assembler/masm/dw?view=msvc-170` — authoritative conventional `DW` reference for comma-separated initializers and label binding
  - External: `https://www.nasm.us/doc/nasm03.html` — authoritative reference confirming `dw` as initialized data, not reserved space

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m pytest tests/test_dw_parser.py::test_parses_labeled_dw_signed_decimal_list -q` passes
  - [ ] `python -m pytest tests/test_dw_parser.py::test_parses_unlabeled_dw_signed_decimal_list -q` passes
  - [ ] `python -m pytest tests/test_dw_parser.py::test_dw_requires_at_least_one_initializer -q` passes
  - [ ] `python -m pytest tests/test_dw_parser.py::test_dw_rejects_hex_literal_in_v1 -q` passes

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Labeled and unlabeled DW parse under the narrow v1 grammar
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_parser.py::test_parses_labeled_dw_signed_decimal_list -q tests/test_dw_parser.py::test_parses_unlabeled_dw_signed_decimal_list -q`
    Expected: exit code 0; parser produces DW directive nodes with the exact integer initializer list in source order
    Evidence: .sisyphus/evidence/task-3-dw-parser-happy.txt

  Scenario: Unsupported or missing DW initializers fail deterministically
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_parser.py::test_dw_requires_at_least_one_initializer -q tests/test_dw_parser.py::test_dw_rejects_hex_literal_in_v1 -q`
    Expected: exit code 0; invalid DW forms produce stable parser diagnostics and do not fall through as instructions
    Evidence: .sisyphus/evidence/task-3-dw-parser-negative.txt
  ```

  **Commit**: YES | Message: `feat(parser): add dw directive syntax and compiler data model` | Files: [`snx/tokenizer.py`, `snx/parser.py`, `snx/ast.py`, `tests/test_dw_parser.py`, `tests/test_dw_api.py`]

- [x] 4. Build separate code-PC and data-address allocation in analysis

  **What to do**: Change analysis from “instruction-only labels” to typed symbol allocation. Introduce separate counters: `code_pc` increments only for executable instructions, and `data_addr` increments only for DW initializers. Define source-order policy explicitly: code and data may be interleaved in source, but each domain advances only its own counter, so a DW line never shifts executable PCs and an instruction line never consumes DMEM allocation. Label binding rules: an instruction-line label binds to the current `code_pc`; a DW-line label binds to the first `data_addr` allocated by that line. Add `M002` for DW data that would allocate at or beyond configured `mem_size`, and add `I002` when a DW initializer is normalized to the 16-bit word model.
  **Must NOT do**: Do not use one untyped `labels: dict[str, int]` for both domains. Do not let DW lines affect branch target PCs. Do not skip bounds/wrap diagnostics for DW initializers.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: address allocation and symbol typing are the main semantic pivot of the feature
  - Skills: `[]` — no special skill required
  - Omitted: `['playwright']` — no browser/UI surface exists

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [5, 6, 7, 8] | Blocked By: [1, 2, 3]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `snx/analyzer.py:87-109` — current label table increments only when a line has an instruction; this must split into code/data domains while preserving single-namespace duplicate detection
  - Pattern: `snx/analyzer.py:110-135` — current IR instruction emission is instruction-only and should remain so for executable PC sequencing
  - Pattern: `snx/compiler.py:54-93` — analyzer output feeds the rest of the pipeline; typed symbols/data image must be returned here
  - Pattern: `snx/constants.py:1-2` — `DEFAULT_MEM_SIZE` drives DW allocation bounds when `mem_size` is not overridden
  - Pattern: `snx/diagnostics.py:48-131` — add new stable diagnostics using the existing collector conventions
  - Pattern: `docs/architecture.md:134-148` — compile-time memory bounds behavior already exists for absolute `LD`/`ST`; mirror that discipline for DW allocation

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_data_label_binds_to_first_allocated_word -q` passes
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_code_pc_is_instruction_only_when_dw_lines_are_interleaved -q` passes
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_duplicate_identifier_across_code_and_data_reports_s006 -q` passes
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_dw_out_of_bounds_reports_m002 -q` passes
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_dw_word_truncation_reports_i002 -q` passes

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Interleaved source preserves separate code and data counters
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_analyzer.py::test_data_label_binds_to_first_allocated_word -q tests/test_dw_analyzer.py::test_code_pc_is_instruction_only_when_dw_lines_are_interleaved -q tests/test_dw_analyzer.py::test_duplicate_identifier_across_code_and_data_reports_s006 -q`
    Expected: exit code 0; data labels receive DMEM addresses, code labels keep instruction PCs, interleaving source order does not cross-shift domains, and duplicate identifiers remain illegal across both domains
    Evidence: .sisyphus/evidence/task-4-dw-analysis-happy.txt

  Scenario: Static DW limits fail before execution
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_analyzer.py::test_dw_out_of_bounds_reports_m002 -q tests/test_dw_analyzer.py::test_dw_word_truncation_reports_i002 -q`
    Expected: exit code 0; overflowing allocation emits `M002` and 16-bit normalization emits `I002`
    Evidence: .sisyphus/evidence/task-4-dw-analysis-negative.txt
  ```

  **Commit**: NO | Message: `feat(analyzer): add typed dw symbols and address resolution` | Files: [`snx/analyzer.py`, `snx/compiler.py`, `snx/diagnostics.py`, `tests/test_dw_analyzer.py`, `docs/static-analysis.md`]

- [x] 5. Resolve label domains by operand context and reject cross-domain misuse

  **What to do**: Implement operand-resolution rules that make DW useful without changing the current architectural split. Bare identifiers used in `LD`, `ST`, and `LDA` address positions must accept **data labels only** and lower them to absolute `$0`-based addresses. `BZ` and label-form `BAL` must accept **code labels only**. Numeric address operands continue to work exactly as today. Emit stable semantic errors for misuse: `S007` when a code label is used where a data address is required, and `S008` when a data label is used where a code target is required. Keep `BAL` address-form semantics unchanged; do not make bare data labels legal BAL targets.
  **Must NOT do**: Do not allow bare labels in every operand slot. Do not permit `BAL $r, DATA_LABEL` as a shorthand for a data jump. Do not break current numeric-address parsing or branch-label encoding.

  **Recommended Agent Profile**:
  - Category: `deep` — Reason: operand semantics now depend on both syntax and typed symbol domain
  - Skills: `[]` — no special skill required
  - Omitted: `['playwright']` — no browser/UI surface exists

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [6, 7, 8] | Blocked By: [1, 2, 3, 4]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `snx/parser.py:166-248` — bare identifiers currently become `LabelRefOperand`; downstream semantic lowering must distinguish code vs data intent
  - Pattern: `snx/analyzer.py:137-175` — current operand-type validation only recognizes branch labels for `BZ`/`BAL`
  - Pattern: `snx/analyzer.py:195-226` — existing label-reference checks and branch-target-range checks that must stay code-label-specific
  - Pattern: `docs/assembly-language.md:82-99` — instruction operand categories that need DW-aware clarification in docs/tests
  - Pattern: `snx/encoding.py:109-149` — branch/BAL label encoding must remain instruction-label-based only

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_ld_accepts_data_label_as_absolute_address -q` passes
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_lda_accepts_data_label_as_absolute_address -q` passes
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_branch_to_data_label_reports_s008 -q` passes
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_ld_with_code_label_reports_s007 -q` passes
  - [ ] `python -m pytest tests/test_dw_analyzer.py::test_bal_label_form_rejects_data_labels -q` passes

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Data labels resolve in absolute-address instruction contexts only
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_analyzer.py::test_ld_accepts_data_label_as_absolute_address -q tests/test_dw_analyzer.py::test_lda_accepts_data_label_as_absolute_address -q`
    Expected: exit code 0; analyzer lowers bare data labels to `$0`-based absolute addresses for `LD`/`ST`/`LDA`-style address contexts
    Evidence: .sisyphus/evidence/task-5-label-resolution-happy.txt

  Scenario: Cross-domain label misuse is rejected deterministically
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_analyzer.py::test_branch_to_data_label_reports_s008 -q tests/test_dw_analyzer.py::test_ld_with_code_label_reports_s007 -q tests/test_dw_analyzer.py::test_bal_label_form_rejects_data_labels -q`
    Expected: exit code 0; misuse cases emit the exact domain-error diagnostics and do not silently coerce symbols across domains
    Evidence: .sisyphus/evidence/task-5-label-resolution-negative.txt
  ```

  **Commit**: YES | Message: `feat(analyzer): add typed dw symbols and address resolution` | Files: [`snx/analyzer.py`, `snx/ast.py`, `snx/compiler.py`, `snx/encoding.py`, `tests/test_dw_analyzer.py`, `docs/assembly-language.md`, `docs/static-analysis.md`]

- [x] 6. Preload simulator DMEM from compiled DW data image

  **What to do**: Consume the compiled initial-data image in simulator construction so DW data exists before the first instruction executes. `SNXSimulator.from_compile_result()` and `SNXSimulator.from_source()` must preload `memory[address]` and set the corresponding `_mem_initialized[address]` flags for every compiled DW word. Preserve current execution semantics for all instructions and keep instruction fetch/execution operating over the existing executable instruction tuple, not unified memory. Ensure data-only programs and mixed code+DW programs both initialize cleanly.
  **Must NOT do**: Do not convert instructions into DMEM contents. Do not delay DW initialization until runtime `step()`. Do not clear or overwrite preloaded DW words unless the program later executes an `ST` to the same address.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: contained runtime change with strong regression risk around initialization behavior
  - Skills: `[]` — no special skill required
  - Omitted: `['playwright']` — no browser/UI surface exists

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [8] | Blocked By: [1, 2, 4, 5]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `snx/simulator.py:37-52` — current memory/init-flag initialization path; preload should happen here or in constructors before execution begins
  - Pattern: `snx/simulator.py:57-105` — compile-result/source constructors where DW preload must be centralized
  - Pattern: `snx/simulator.py:142-167` — existing memory write/load/output helpers; preloaded words must look indistinguishable from already-initialized memory
  - Pattern: `snx/simulator.py:281-285` — public initialization-flag API that must reflect DW preloads
  - Pattern: `docs/python-api.md:72-110` — simulator constructor docs that must remain truthful after preload behavior is added

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m pytest tests/test_dw_simulator.py::test_dw_initializes_memory_before_execution -q` passes
  - [ ] `python -m pytest tests/test_dw_simulator.py::test_dw_sets_memory_init_flags_before_execution -q` passes
  - [ ] `python -m pytest tests/test_dw_simulator.py::test_store_can_overwrite_preloaded_dw_word -q` passes
  - [ ] `python -m pytest tests/test_dw_simulator.py::test_data_only_program_preloads_without_crashing -q` passes

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Preloaded DW data is visible to the first LD
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_simulator.py::test_dw_initializes_memory_before_execution -q tests/test_dw_simulator.py::test_dw_sets_memory_init_flags_before_execution -q`
    Expected: exit code 0; simulator starts with DW data already present in memory and marked initialized before the first instruction executes
    Evidence: .sisyphus/evidence/task-6-simulator-preload-happy.txt

  Scenario: Runtime stores still own the final memory value
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_simulator.py::test_store_can_overwrite_preloaded_dw_word -q tests/test_dw_simulator.py::test_data_only_program_preloads_without_crashing -q`
    Expected: exit code 0; preloaded DW state survives startup but can still be overwritten by `ST`, and programs with only DW data do not crash constructors or `run()`
    Evidence: .sisyphus/evidence/task-6-simulator-preload-edge.txt
  ```

  **Commit**: YES | Message: `feat(simulator): preload dw data image into memory` | Files: [`snx/simulator.py`, `tests/test_dw_simulator.py`, `tests/test_dw_api.py`]

- [x] 7. Preserve encoding/public API compatibility while surfacing DW metadata

  **What to do**: Keep the repo's current executable-output contract intact for instruction programs while documenting and testing the DW adaptation. `encode_program()` must continue encoding executable instructions only; it must not emit DW data words into the instruction stream. `parse_code()` must remain instruction-focused with the same return-shape contract; DW-specific metadata belongs on `CompileResult`/IR, not in a breaking `parse_code()` signature change. Add or update API tests so consumers can read typed symbols and the initial data image from `CompileResult`/IR without losing existing instruction-encoding behavior. If helper types or exports are added, keep them additive and update `__all__` consistently.
  **Must NOT do**: Do not make encoded program length include DW entries. Do not break `parse_code()`, `encode_program()`, or existing imports for callers that assemble instruction-only programs.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: compatibility-sensitive API/encoding seam with moderate surface area
  - Skills: `[]` — no special skill required
  - Omitted: `['playwright']` — no browser/UI surface exists

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [8] | Blocked By: [1, 2, 4, 5]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `snx/encoding.py:44-161` — current instruction encoding contract; preserve instruction-only behavior
  - Pattern: `snx/parser.py:263-282` — `parse_code()` helper currently returns instruction list + labels and must remain instruction-only; expose DW metadata elsewhere additively
  - Pattern: `snx/__init__.py:1-59` — any new exports must remain additive and coherent
  - Pattern: `README.md:179-200` — public example path through `compile_program` and `SNXSimulator.from_compile_result`
  - Pattern: `docs/python-api.md:34-110` — API docs that must explain new compile metadata without contradicting instruction encoding behavior

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m pytest tests/test_dw_api.py::test_encode_program_ignores_dw_data_image -q` passes
  - [ ] `python -m pytest tests/test_dw_api.py::test_instruction_only_encoding_is_unchanged -q` passes
  - [ ] `python -m pytest tests/test_dw_api.py::test_parse_code_remains_instruction_focused -q` passes

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: Instruction encoding remains instruction-only
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_api.py::test_encode_program_ignores_dw_data_image -q tests/test_dw_api.py::test_instruction_only_encoding_is_unchanged -q`
    Expected: exit code 0; DW metadata does not leak into encoded instruction output and legacy encoding stays byte-for-byte stable
    Evidence: .sisyphus/evidence/task-7-api-encoding-happy.txt

  Scenario: Helper API compatibility is preserved
    Tool: Bash
    Steps: run `python -m pytest tests/test_dw_api.py::test_parse_code_remains_instruction_focused -q`
    Expected: exit code 0; helper APIs keep their existing return-shape expectations for instruction-only consumers
    Evidence: .sisyphus/evidence/task-7-api-encoding-edge.txt
  ```

  **Commit**: NO | Message: `docs(dw): document directive semantics and examples` | Files: [`snx/encoding.py`, `snx/parser.py`, `snx/__init__.py`, `tests/test_dw_api.py`]

- [x] 8. Document DW semantics and add end-to-end CLI regressions

  **What to do**: Update the human-facing surfaces so implementation semantics are discoverable and verifiable. Extend `docs/assembly-language.md` with DW grammar, narrow v1 literal rules, domain-specific label behavior, and examples. Update `docs/python-api.md`, `docs/static-analysis.md`, and README snippets to mention the initial data image / simulator preload behavior where relevant. Add end-to-end CLI tests that run the normal `snx` execution path against temporary assembly files containing DW and assert both success and failure output paths. Prefer test fixtures created inside pytest temp directories instead of editing `sample.s`.
  **Must NOT do**: Do not broaden docs to unsupported directives. Do not handwave over the split address-space model. Do not rely on manual README review as verification.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: docs-heavy task with supporting CLI regression coverage
  - Skills: `[]` — no special skill required
  - Omitted: `['playwright']` — no browser/UI surface exists

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [] | Blocked By: [1, 2, 3, 4, 5, 6, 7]

  **References** (executor has NO interview context — be exhaustive):
  - Pattern: `README.md:174-198` — current CLI/API narrative that should mention DW-compatible compile/run behavior without overexplaining internals
  - Pattern: `docs/assembly-language.md:7-10` and `docs/assembly-language.md:45-99` — existing syntax/grammar and operand sections to extend for directives and domain-sensitive label rules
  - Pattern: `docs/python-api.md:34-110` — `CompileResult` and simulator constructor docs to update with initial-data-image/preload semantics
  - Pattern: `docs/static-analysis.md:51-57` — diagnostic code table that must include new DW-related diagnostics (`P007`, `S007`, `S008`, `M002`, `I002`)
  - Pattern: `snx/cli.py:40-65` and `snx/runner.py:38-93` — the real CLI path to exercise in end-to-end tests

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -m pytest tests/test_cli_dw.py::test_cli_executes_program_with_dw_data -q` passes
  - [ ] `python -m pytest tests/test_cli_dw.py::test_cli_reports_cross_domain_label_error_for_dw_program -q` passes
  - [ ] `python - <<'PY'
from pathlib import Path
for rel in ["README.md", "docs/assembly-language.md", "docs/python-api.md", "docs/static-analysis.md"]:
    text = Path(rel).read_text(encoding="utf-8")
    assert "DW" in text, rel
print("docs mention DW")
PY` passes
  - [ ] `python -m pytest -q` passes

  **QA Scenarios** (MANDATORY — task incomplete without these):
  ```
  Scenario: CLI successfully runs a DW-backed program end to end
    Tool: Bash
    Steps: run `python -m pytest tests/test_cli_dw.py::test_cli_executes_program_with_dw_data -q`
    Expected: exit code 0; CLI compiles, analyzes, executes, and reports success for a temp-file assembly program that loads data from a DW label
    Evidence: .sisyphus/evidence/task-8-cli-docs-happy.txt

  Scenario: CLI surfaces DW misuse diagnostics and docs are updated coherently
    Tool: Bash
    Steps: run `python -m pytest tests/test_cli_dw.py::test_cli_reports_cross_domain_label_error_for_dw_program -q` and then run the inline Python docs assertion command from Acceptance Criteria
    Expected: exit code 0 for both commands; CLI emits deterministic failure for invalid DW symbol use and all required docs mention DW semantics
    Evidence: .sisyphus/evidence/task-8-cli-docs-negative.txt
  ```

  **Commit**: YES | Message: `docs(dw): document directive semantics and examples` | Files: [`README.md`, `docs/assembly-language.md`, `docs/python-api.md`, `docs/static-analysis.md`, `tests/test_cli_dw.py`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [x] F1. Plan Compliance Audit — oracle

  **What to do**: Dispatch an `oracle` review against the completed implementation plus this plan file. The oracle reviewer must verify that every changed source/test/doc/workflow file maps back to one or more planned tasks, that no planned must-have was skipped, and that no out-of-plan feature (for example `DB`, `ORG`, hex literal support, generic directive framework, unified memory execution) slipped in.
  **Acceptance Criteria**:
  - [ ] Oracle review returns approval with zero blockers
  - [ ] Oracle output explicitly confirms plan/task coverage for all changed files

  **QA Scenarios**:
  ```
  Scenario: Implemented files are traceable to planned tasks
    Tool: Bash + task(oracle)
    Steps: capture `git diff --stat`, `git diff --name-only`, and `python -m pytest -q`; provide those artifacts plus `.sisyphus/plans/add-dw-support.md` to oracle for compliance review
    Expected: oracle reports no unplanned source changes and no missed required deliverables
    Evidence: .sisyphus/evidence/f1-plan-compliance.txt
  ```

- [x] F2. Code Quality Review — unspecified-high

  **What to do**: Dispatch an `unspecified-high` reviewer to inspect the final diff for correctness, maintainability, diagnostic quality, and regression risk across parser, analyzer, simulator, API, and tests.
  **Acceptance Criteria**:
  - [ ] Reviewer finds zero blocking defects
  - [ ] Reviewer explicitly calls out parser/analyzer/simulator/API seams as acceptable

  **QA Scenarios**:
  ```
  Scenario: Cross-module code review passes without blockers
    Tool: Bash + task(unspecified-high)
    Steps: capture `git diff --stat`, `git diff`, and `python -m pytest -q`; provide them to the reviewer with emphasis on `snx/parser.py`, `snx/analyzer.py`, `snx/simulator.py`, `snx/compiler.py`, and docs/test changes
    Expected: reviewer approves with no blocking code-quality or regression findings
    Evidence: .sisyphus/evidence/f2-code-quality.txt
  ```

- [x] F3. End-to-End Runtime QA — unspecified-high

  **What to do**: Run agent-executed end-to-end verification of the shipped behavior. This is not human/manual QA; it is runtime validation using automated commands against the final test suite and CLI path.
  **Acceptance Criteria**:
  - [ ] `python -m pytest -q` passes
  - [ ] `python -m pytest tests/test_cli_dw.py -q` passes
  - [ ] Reviewer confirms the runtime behavior matches DW semantics described in docs

  **QA Scenarios**:
  ```
  Scenario: Full automated runtime verification passes
    Tool: Bash + task(unspecified-high)
    Steps: run `python -m pytest -q` and `python -m pytest tests/test_cli_dw.py -q`; provide results plus the final docs snippets to the reviewer for semantic verification
    Expected: all automated tests pass and reviewer confirms runtime behavior matches the documented DW rules
    Evidence: .sisyphus/evidence/f3-runtime-qa.txt
  ```

- [x] F4. Scope Fidelity Check — deep

  **What to do**: Dispatch a `deep` reviewer to confirm the implementation stayed inside the v1 box: DMEM-only DW, signed decimal initializers only, no new directives, no unified memory execution, no broken instruction-only compatibility, and no silent code/data label coercion.
  **Acceptance Criteria**:
  - [ ] Deep review returns approval with zero scope violations
  - [ ] Deep review explicitly confirms excluded features remain excluded

  **QA Scenarios**:
  ```
  Scenario: Final scope review confirms no hidden feature creep
    Tool: Bash + task(deep)
    Steps: capture `git diff --stat`, `git diff --name-only`, `python -m pytest -q`, and the final docs files; provide them to the deep reviewer with explicit instruction to check for forbidden scope expansion
    Expected: reviewer confirms the implementation is DMEM-only DW v1 with no DB/ORG/expressions/hex/unified-memory creep
    Evidence: .sisyphus/evidence/f4-scope-fidelity.txt
  ```

## Commit Strategy
- Commit 1: `test(ci): add pytest harness for dw coverage`
- Commit 2: `feat(parser): add dw directive syntax and compiler data model`
- Commit 3: `feat(analyzer): add typed dw symbols and address resolution`
- Commit 4: `feat(simulator): preload dw data image into memory`
- Commit 5: `docs(dw): document directive semantics and examples`

## Success Criteria
- DW programs compile without regressing instruction-only programs.
- Data labels resolve only in valid address contexts and fail loudly elsewhere.
- Simulator starts with DW data already resident in DMEM and marked initialized.
- CLI/API/docs all describe the same DW semantics.
- Repo-wide pytest and CI pass.
