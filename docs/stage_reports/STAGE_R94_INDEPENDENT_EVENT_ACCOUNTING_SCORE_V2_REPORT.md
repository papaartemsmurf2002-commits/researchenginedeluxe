# Stage R94 Independent Event Accounting And Score V2 Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR94-02-independent-event-accounting-score-v2.md`

## Summary

WPR94-02 stopped discovery from ranking dense overlapping bar-level KNN
acceptances as independent executable trades. The discovery runner now applies
deterministic same-symbol event suppression over the label horizon and ranks
real discovery trials with a versioned screen score.

Implemented:

- Added `event_accounting.py` with deterministic independent-event accounting:
  accepted rows are ordered by symbol/source row/decision order, the first
  event is kept, and same-symbol follow-on rows are suppressed until the label
  horizon spacing has elapsed.
- Added trial and ledger metrics:
  `accepted_bar_count`, `independent_event_count`,
  `suppressed_overlap_count`, `overlap_ratio`, `event_signal_rate`,
  `side_collapse_ratio`, `near_signal_ceiling`,
  `long_independent_event_count`, `short_independent_event_count`,
  `event_spacing_bars`, and `independent_event_expectancy`.
- Added `discovery_screen_score_v2` and mapped `score`/`final_score` to that
  versioned score for real discovery trials.
- Kept `legacy_density_score` as diagnostic evidence only.
- Made score-v2 quality and vote-margin terms event-based, so dense overlapping
  rows cannot inflate score through diagnostic columns.
- Added blocker reasons for insufficient independent events, excessive overlap,
  near-ceiling signal density, one-side collapse, and discovery expectancy
  floors.
- Added `discovery_score_policy_version: discovery-screen-score-v2` to real
  discovery trial payloads and ledgers, plus resume rejection for old real
  records that lack the current policy.
- Updated the candidate-pack bridge ledger contract and integrity checks to
  include the new event-accounting and score-v2 fields.
- Added run-manifest disclosure for the event-accounting policy.

## Boundary Notes

- Research outputs remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- No live order placement, live config writes, runtime mode changes, candidate
  promotion, or sizing behavior was added.
- Candidate-pack bridge behavior remains observe-only and pack-writing remains
  disabled.
- KNN remains a local analog/filter/evidence layer; this packet only changes
  discovery accounting and ranking.

## Review Notes

Subagent review found one P1 issue before closure: score v2 still used
bar-level accepted-row quality and vote-margin averages. The fix moved those
terms onto the independent event set and added regression coverage proving
dense overlapping rows no longer improve `discovery_screen_score_v2`.

## Validation

Passed:

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

## Next Packet

Continue the R94 roadmap with WPR94-03 mandatory exit-lab gate. Candidate-pack
bridge eligibility should require exit-lab evidence, comparator evidence,
no-regime baseline evidence when a regime is claimed, and validation evidence
before a discovery lead can be treated as candidate-ready.
