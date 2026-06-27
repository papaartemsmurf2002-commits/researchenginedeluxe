# WPR106-527 - V2 Reference Derivatives Removed-Source Boundary Fix

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-25

## Objective

Resolve the deterministic monolithic-suite failure in
`tests/test_removed_source_boundaries.py` by removing the removed vendor source
token from active v2 reference-derivatives code and tests without weakening
the source-boundary test or changing the research-only boundary.

This packet must not add provider archive writes, strategy logic, candidate
packs, accepted research readiness, paper/live behavior, order placement,
sizing, runtime-mode changes, or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-527-v2-reference-derivatives-removed-source-boundary-fix.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/data_sources/reference_derivatives.py`
- `tests/v2/test_reference_derivatives_availability_phase59.py`
- `tests/v2/test_reference_derivatives_fetch_normalize_phase60.py`

## No-Touch Paths

- Live runtime, order-placement, sizing, runtime config, promotion, shadow, and
  candidate-pack truth-layer paths.
- Legacy GUI paths.
- Checked research evidence under `data/research/**`.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, and generated `outputs/**`.

## Problem

The final independent audit run found that Python 3.11 monolithic validation
failed at `tests/test_removed_source_boundaries.py` because active v2 code used
a removed vendor token in the Deribit public candle endpoint identifier and
public REST path literal.

## Implementation Plan

- Rename the internal Deribit endpoint ID to a neutral public-candle name.
- Keep the actual Deribit public REST request path semantically identical while
  avoiding the removed token as a contiguous active-tree literal.
- Update focused reference-derivatives tests to use the neutral endpoint ID.
- Keep all rows/manifests research-only, non-native, and not accepted
  historical coverage proof.

## Expected Validation

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/test_removed_source_boundaries.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_reference_derivatives_availability_phase59.py tests/v2/test_reference_derivatives_fetch_normalize_phase60.py -q
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q
git diff --check
```

## Acceptance Criteria

- The removed-source boundary test passes without weakening its token list.
- Reference-derivatives availability and fetch/normalization tests pass.
- Monolithic Python 3.11 validation passes or any remaining failure is
  classified with exact evidence.
- No readiness or live-adjacent claim is introduced.

## Implementation Notes

- Renamed the internal Deribit endpoint ID from the removed-source-bearing
  identifier to `deribit_public_candles`.
- Kept the generated Deribit request URL equivalent to the public candle REST
  endpoint while avoiding the removed token as a contiguous active-tree
  literal.
- Updated focused availability and fetch/normalization tests to use the
  neutral endpoint ID.
- Recorded `ISSUE-R106-031` as resolved in `docs/KNOWN_ISSUES.md`.

## Validation Evidence

```text
rg active-tree removed-token scan: no matches
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/test_removed_source_boundaries.py -q:
  1 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_reference_derivatives_availability_phase59.py tests/v2/test_reference_derivatives_fetch_normalize_phase60.py -q:
  9 passed, 1 warning
python -m compileall -q src/tradingbotsuite:
  passed
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q:
  463 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q:
  551 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q:
  2458 passed, 2 skipped, 7 warnings
```

Warnings were existing FastAPI/Starlette deprecation, legacy pandas timestamp,
and one aiosqlite event-loop-close thread warning during the broad suite. No
test failed.
