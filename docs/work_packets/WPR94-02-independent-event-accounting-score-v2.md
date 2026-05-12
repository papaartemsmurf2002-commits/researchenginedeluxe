# WPR94-02 Independent Event Accounting And Score V2

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Stop ranking dense overlapping bar-level KNN signals as if they were independent
executable trades. Add deterministic independent-event accounting and a
versioned discovery screen score while preserving the legacy density score as
diagnostic evidence.

## Allowed Paths

- `docs/work_packets/WPR94-02-independent-event-accounting-score-v2.md`
- `docs/stage_reports/STAGE_R94_INDEPENDENT_EVENT_ACCOUNTING_SCORE_V2_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/research_discovery/event_accounting.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `src/tradingbotsuite/research_discovery/manifests.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `tests/research_discovery/**`

## Scope

- Add independent event accounting for accepted discovery rows:
  - sort by source/decision order
  - accept the first event
  - suppress same-symbol follow-on events until the label horizon or configured
    minimum spacing has elapsed
  - record suppressed-overlap counts and side-separated independent counts
- Add trial/ledger metrics:
  - `accepted_bar_count`
  - `independent_event_count`
  - `overlap_ratio`
  - `event_signal_rate`
  - `side_collapse_ratio`
  - `near_signal_ceiling`
  - `long_independent_event_count`
  - `short_independent_event_count`
  - `legacy_density_score`
  - `discovery_screen_score_v2`
- Keep existing `final_score` compatible by mapping it to
  `discovery_screen_score_v2` after the new metrics are present.
- Add blocker reasons for insufficient independent events, excessive overlap,
  signal-rate ceiling proximity, and one-side collapse.
- Keep all outputs research-only and observe-only.

## Non-Goals

- No exit-lab changes.
- No candidate-pack promotion or candidate-pack writing.
- No new strategy plugins.
- No feature/filter ablation changes.
- No live trading behavior, live config writes, order placement, promotion
  readiness, or sizing logic changes.
- No UI redesign.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_event_accounting.py tests\research_discovery\test_discovery_runner.py tests\research_discovery\test_candidate_pack_bridge.py -q
```

## Validation Result

Passed on 2026-05-12:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_event_accounting.py tests\research_discovery\test_discovery_runner.py tests\research_discovery\test_candidate_pack_bridge.py -q
# 35 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 95 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Exit Evidence

- Dense overlapping accepted KNN rows now collapse into deterministic
  independent events before `trade_count`, `realized_expectancy`,
  `gross_realized_return`, `score`, and `final_score` are calculated.
- `final_score` now maps to the versioned `discovery_screen_score_v2`; the
  legacy bar-density score is retained only as `legacy_density_score`.
- Score v2 quality and vote-margin terms use independent events, not all
  accepted bars.
- Ledgers, trial payloads, run manifests, and the candidate-pack bridge carry
  the new event-accounting and score-policy fields.
- Resume fails closed for old real discovery trial records missing
  `discovery_score_policy_version: discovery-screen-score-v2`.
- Research-only boundaries remain unchanged; no live execution, promotion,
  live config, order placement, or sizing behavior was touched.
