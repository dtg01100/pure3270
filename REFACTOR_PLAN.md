# Pure3270 Strict Typing & Lint Remediation Plan

Goal: Reach a clean pre-commit run (black, isort, flake8, mypy, bandit, pylint) **without** relaxing existing strictness (aside from removing clearly invalid disables) while preserving runtime behavior and RFC alignment.

## Guiding Principles
- Do NOT introduce behavior changes unless fixing objectively dead / unreachable code.
- Keep each commit scoped to a logical phase (aid review + bisectability).
- Prefer adding minimal, correct type hints over broad `# type: ignore`.
- Remove duplicated / unreachable code blocks instead of annotating them.
- When unsure of intent of suspicious logic, isolate behind helper with a TODO comment instead of deleting.
- Maintain RFC-first correctness for protocol paths (Negotiator / DataStream / Handler).

## Error Surface Snapshot (Condensed)
Categories extracted from `logs/mypy_core.txt` & pylint snapshot:
- Missing return / arg annotations (`no-untyped-def`).
- Python 3.10 union syntax (`X | Y`) conflicting with configured `python_version = 3.8`.
- Unreachable / duplicated method definitions (session, data_stream, negotiator, tn3270_handler).
- Incorrect attribute assumptions (e.g., `TN3270Handler._ascii_mode`, writer possibly None, parser lifecycle).
- Overly permissive dynamic attributes (`Attribute defined outside __init__`).
- Tests: missing `pytest` stubs (solution: targeted ignore or lightweight `typing`-only stub).
- Structural parser code returning `Any` or mutating inconsistent types.

## Phase Overview
| Phase | Focus | Primary Files | Expected Reduction |
|-------|-------|---------------|--------------------|
| 1 | Negotiator structural cleanup | `pure3270/protocol/negotiator.py` | Attr-defined & no-untyped-def subset (-25 to -35) |
| 2 | TN3270Handler normalization | `pure3270/protocol/tn3270_handler.py` | Attr-defined & duplicate / unreachable (-35 to -45) |
| 3 | AsyncSession context manager + minimal session prune (pass 1) | `pure3270/session.py` | Remove obvious unreachable & duplicates (-20) |
| 4 | Emulation primitives typing | `emulation/{buffer_writer,printer_buffer,ebcdic,screen_buffer}.py` | Annotation & arg-type (-40 to -50) |
| 5 | Protocol parsing core (data_stream, vt100_parser, printer) | `protocol/data_stream.py`, `protocol/vt100_parser.py`, `protocol/printer.py` | Reduce unknown/Any/unreachable (-45 to -55) |
| 6 | Utilities & errors tightening | `protocol/utils.py`, `protocol/errors.py`, `protocol/ssl_wrapper.py` | Fix run/loop arg types, Callable generics (-10) |
| 7 | Patch / wrapper minimal annotations | `patching/s3270_wrapper.py`, `patching/patching.py` | -8 to -12 |
| 8 | Test typing strategy | `tests/` | Introduce `mypy.ini` section or add `typing.TYPE_CHECKING` guards (-30+ import-not-found) |
| 9 | Final pass & polish | All | Zero residual errors |

## Detailed Phase Tasks

### Phase 1: Negotiator
1. Remove re-import clusters; consolidate imports at top.
2. Replace Python 3.10 union syntax with `Optional[...]` / `Union[...]`.
3. Add explicit fields in `__init__` for attributes later accessed (writer, screen_buffer, parser, recorder, etc.).
4. Ensure `_ascii_mode` state transitions are encapsulated; add return annotations (`-> None`, `-> bytes`).
5. Fix `__await__` misuse (either implement proper awaitable pattern or remove if accidental artifact).
6. Replace multiple `logger.info` f-strings spanning lines with single formatted calls (cleanup readability, not logic change).
7. Mark any unreachable code for deletion (remove if truly dead, retain with TODO if uncertain).

Acceptance: mypy reductions for negotiator-specific errors; no new flake8 issues.

### Phase 2: TN3270Handler
1. Move late imports (inspect, etc.) to top unless causing cycles.
2. Define all mutable attributes inside `__init__` (reader, writer, negotiator, _transport, _negotiation_trace, etc.).
3. Remove duplicate `_transport` reassignments and contradictory error-handling blocks.
4. Replace broad `except:` + immediate raise with narrower exception or inline propagation.
5. Add return types to public async methods (`connect`, `read`, `send`, etc.).
6. Resolve unused `type: ignore` by either adding real types or deleting stale code references.

Acceptance: attr-defined errors for handler eliminated; unreachable blocks removed.

### Phase 3: Session (Pass 1 Structural)
1. Delete copy-pasted duplicated methods and obviously unreachable blocks flagged by mypy.
2. Normalize naming (`_async_session` artifacts?)—remove phantom references.
3. Introduce `AsyncSession.__aenter__/__aexit__` (close semantics) + mirror in `Session` for uniform examples.
4. Limit modifications to structural clarity; deeper typing deferred to Phase 10.

Acceptance: Unreachable statement count significantly reduced; example trace works with context manager.

### Phase 4: Emulation Primitives
1. Add `-> None` return types where mutators.
2. Provide concrete generics: `List[int]`, `Dict[int, bytes]`, etc.
3. Replace pipe unions with `Union` / `Optional`.
4. Address incorrect `bytes(...)` argument usage by explicit conversions.
5. Remove unreachable code branches (e.g., after returns) and annotate constructor fields.

Acceptance: All emulation modules free of `no-untyped-def`, `no-any-return`, `arg-type` errors.

### Phase 5: Protocol Parsing Core
1. Introduce base parser protocol / ABC for dynamic parser assignments to avoid `BaseParser` vs `None` conflicts.
2. Convert switching logic to typed discriminated operations (keep runtime identical).
3. Annotate parsed structure (e.g., `attrs: Dict[int, int]`).
4. Replace multi-step unreachable code paths with early returns or deletions.
5. Add typed dataclass / NamedTuple where repeated tuple shapes exist (e.g., header fields) if helpful.

Acceptance: Major cluster of union-attr / Incompatible assignment errors reduced to zero.

### Phase 6: Utilities & Errors
1. Add return and arg types for utility scheduling functions.
2. Replace `Callable` bare with generics (`Callable[..., None]`).
3. Adjust loop.run wrappers to acceptable typed coroutine signatures.
4. Fix ssl wrapper optional return mismatch.

Acceptance: utils/errors/ssl wrapper no outstanding mypy errors.

### Phase 7: Patching Layer
1. Annotate public interface methods; use `Any` only at module boundary where dynamic patching inevitable.
2. Consolidate patch tracking dict types.

Acceptance: No `no-untyped-def` in patching modules.

### Phase 8: Tests Typing Strategy
Option A (faster): Add `[[tool.mypy.overrides]]` style or `[mypy-tests.*] ignore_missing_imports = True` and allow untyped defs (already partially present).
Option B (selective stubs): Provide `typing.TYPE_CHECKING` guards + minimal `pytest` stub (only if beneficial).
We'll adopt Option A and prune unreachable lines in tests flagged by mypy.

Acceptance: Tests produce zero blocking errors (import-not-found resolved by ignore). Real logic errors (attr-defined misuse) addressed.

### Phase 9: Final Pass & Polish
1. Remove lingering `# type: ignore` not required.
2. Re-run pre-commit; address residual lint (pylint) if newly introduced.
3. Ensure README / examples still accurate (trace + context manager).

### Phase 10: (Optional Stretch) Incremental Strictness Re-Enable
If desired, selectively re-add stricter mypy flags file-by-file (e.g., `disallow_untyped_defs = True` for protocol after stabilization).

## Risk Mitigation
- Commit after each phase; avoid mixing structural deletions with type additions.
- Run quick smoke + negotiation trace tests after phases 1–3, 5.
- If ambiguity in semantics arises, add `# TODO(typing): clarify X` instead of guessing.

## Immediate Next Action
Proceed with Phase 1 (Negotiator cleanup) implementing items listed; then re-run mypy to measure delta and document counts in `logs/mypy_phase1.txt`.

---
Document version: v1 (will update if scope shifts).
