# WPR106-559 - V2 final code audit critical review and change plan

Status: self_checked
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Critically review the user-provided `V2 Final Code Audit (1).docx` against the
current repository state, inspect the important v2 code/math/performance
surfaces, validate the claims that can be validated locally, and produce a
final review document outlining project changes and manual-review questions.

This packet is documentation/audit output only unless a P0/P1 blocker is found.
It must not change source behavior, generated research evidence, candidate
packs, paper/live/order/sizing/runtime behavior, or promotion status.

## Inputs

- `C:\Users\papaa\Downloads\V2 Final Code Audit (1).docx`
- `docs/RESEARCH_AGENT_QUICKSTART.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- Current v2 source, tests, manifests, and validation commands.

## Allowed paths

- `docs/work_packets/WPR106-559-v2-final-code-audit-critical-review-and-change-plan.md`
- `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29.md`
- `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29.docx`
- `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29_rendered/**`
- `docs/KNOWN_ISSUES.md` only if a blocking P0/P1 risk is discovered and must be registered.

## No-touch review

- Live/runtime, order-placement, sizing, promotion, candidate-pack truth, old
  generated evidence, and legacy GUI paths are not in scope for modification.
- This packet may inspect those boundaries but must not alter them.
- It must not write or rewrite generated strategy/backtest evidence.
- It must preserve the canonical research-only invariant.

## Review plan

1. Extract and summarize the uploaded DOCX, including any explicit claims,
   recommendations, and ambiguities.
2. Inspect current v2 code and tests across security boundary, data/archive,
   OF-style materialization, backtest data, strategy specs, backtest engine,
   costs, validation, ledger, Lead Book, workers/autonomy, CLI/UI, and import
   boundaries.
3. Validate math and performance claims using local manifests and focused
   commands where feasible; use Binance public market-data tooling only for
   spot checks, not as a replacement for manifest-backed evidence.
4. Record questionable or human-decision items for later manual GitHub review.
5. Produce a final DOCX and Markdown audit/change-plan artifact.

## Validation target

For this docs/audit packet, run:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

Broaden focused tests if source code changes become necessary.

## Review outputs

- Markdown report:
  `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29.md`
- DOCX report:
  `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29.docx`
- Manual review issue:
  `https://github.com/papaartemsmurf2002-commits/researchenginedeluxe/issues/4`

## Validation evidence

Completed on 2026-06-29:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
# 4 passed, 1 Starlette/httpx deprecation warning

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_contract_docs.py -q
# 2 passed, 1 Starlette/httpx deprecation warning

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_cost_models_phase12.py tests\v2\test_validation_worker_phase32.py tests\v2\test_backtest_engine_phase11.py -q
# 18 passed, 1 Starlette/httpx deprecation warning

git diff --check
# passed with pre-existing LF-to-CRLF working-copy warnings on unrelated dirty files
```

DOCX QA:

- `render_docx.py` could not run because LibreOffice/`soffice.exe` is not
  installed in the bundled or system paths.
- A Microsoft Word COM export fallback was attempted, but the hidden export
  instance hung while an interactive Word session already had the uploaded
  source audit document open. The hidden export process was terminated; the
  user's visible Word process was left untouched.
- Structural DOCX QA passed: XML parses cleanly, 221 nonempty paragraphs,
  0 tables, no relationship/XML parse errors.
- Accessibility audit passed with 0 high, 0 medium, and 0 low findings after
  regenerating the DOCX without custom hyperlink OOXML.

## Findings summary

- No live/order/sizing/runtime/promotion/candidate-pack boundary breach was
  found.
- The uploaded audit's main validation and performance concerns are supported.
- `docs/KNOWN_ISSUES.md` was not changed because the findings are scoped
  hardening items and manual policy decisions unless the orchestrator chooses
  to classify stricter accepted-validation semantics as an open P1 blocker.
