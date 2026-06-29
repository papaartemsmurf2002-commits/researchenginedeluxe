# WPR106-560 - V2 development strategy after final audit decisions

Status: self_checked
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Combine the uploaded final-code-audit document, the WPR106-559 repo inspection
findings, and the user's follow-up policy decisions into one comprehensive
Markdown development strategy.

This is a docs-only strategy packet. It must not change source behavior,
generated evidence, candidate packs, paper/live/order/sizing/runtime behavior,
or promotion status.

## User decisions incorporated

- Trade-frequency gate means average trades per usable month.
- Losing-month gate allows up to 4 losing months per year.
- Fold count is derived from the tested timeline using one-month folds, capped
  at 4 folds; `fold_count=1` may pass only when the tested timeline cannot
  support more folds.
- Account notional should default to USD 10,000 rather than requiring every run
  to declare one manually.
- Spread unit handling should be lenient-prefer explicit units, with a default
  realistic spread assumption of 5 bps / 0.05 percent when a default is needed.
- Usable months keep the existing calendar-delta interpretation.
- `bybit_inverse` in Bybit index planning is intentional source-family naming.

## Allowed paths

- `docs/work_packets/WPR106-560-v2-development-strategy-after-final-audit-decisions.md`
- `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29.md`
- `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29.docx`
- `docs/audit/V2_DEVELOPMENT_STRATEGY_AFTER_FINAL_AUDIT_DECISIONS_2026_06_29.md`

## No-touch review

- No live/runtime, order-placement, sizing, promotion, candidate-pack truth,
  generated evidence, or legacy GUI paths are in scope.
- This packet may reference future source changes but must not implement them.
- The strategy must preserve the canonical v2 research-only invariant.

## Validation target

For this docs-only packet:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

## Outputs

- `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29.md`
- `docs/audit/V2_FINAL_CODE_AUDIT_CRITICAL_REVIEW_AND_CHANGE_PLAN_2026_06_29.docx`
- `docs/audit/V2_DEVELOPMENT_STRATEGY_AFTER_FINAL_AUDIT_DECISIONS_2026_06_29.md`

## Validation evidence

Completed on 2026-06-29:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
# 4 passed, 1 Starlette/httpx deprecation warning

$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_contract_docs.py -q
# 2 passed, 1 Starlette/httpx deprecation warning

git diff --check
# passed with pre-existing LF-to-CRLF working-copy warnings on unrelated dirty files
```

Follow-up account-notional correction:

```powershell
stale account-notional default search across audit/work-packet Markdown
# no matches

DOCX text extraction
# no stale previous account-notional text found; USD 10,000 text present
# visual DOCX render not completed: render_docx.py, soffice, and libreoffice were unavailable
```

## Summary

This packet records the combined development strategy after user decisions:
average trades per usable month, 4 losing months/year, timeline-derived
monthly folds capped at 4, USD 10,000 default account-notional capacity math,
5 bps default spread fallback, existing calendar-delta usable months, and
intentional Bybit index source-family naming.

No source behavior, generated evidence, candidate-pack, paper/live/order/
sizing/runtime, promotion, or known-issues state was changed.
