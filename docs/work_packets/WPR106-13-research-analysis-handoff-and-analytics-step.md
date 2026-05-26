# WPR106-13 Research Analysis Handoff And Analytics Step

Status: complete

## Scope

Create a repeatable analysis artifact step for completed BTC/ETH research
outputs and write a next-agent handoff that turns the current operator feedback
into concrete R106/R107 research direction. The immediate target is the
completed BTC R106 historical cycle plus finalized exact discovery output, so
ETH discovery is not started blindly without knowing what artifacts will be
useful at the end.

## Allowed paths

- `src/tradingbotsuite/research_discovery/analysis_report.py`
- `tests/research_discovery/test_analysis_report.py`
- `docs/stage_reports/STAGE_R106_RESEARCH_ANALYTICS_NEXT_AGENT_HANDOFF.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR106-13-research-analysis-handoff-and-analytics-step.md`

## Constraints

- Preserve research-only, observe-only, and `promotion_ready: false` semantics.
- Do not place orders, change live runtime mode, or write live configuration.
- Do not delete or rewrite completed BTC cycle/discovery evidence.
- Treat analysis as evidence review and experiment planning, not a trading
  promotion claim.
- Keep generated reports deterministic and reproducible from manifest paths.

## Acceptance

- A local analysis helper can summarize historical-cycle rankings, gate
  blockers, exact-discovery KNN/filter settings, blocked reasons, and data
  windows into machine-readable JSON and operator-readable Markdown.
- The BTC R106 artifacts can be analyzed without rerunning compute.
- The handoff documents the current facts: fixed-holding-only BTC cycle, exact
  discovery leads, missing simple-runner exit lab, orderflow not used by the
  active specs, modern-window concern, overfit/holdout limitations, and the
  next one-button research objective.
- Focused tests cover grouping, blocker aggregation, and nullable/missing field
  handling in the analysis helper.
- Stage ledger and known-issue registry reflect the new analysis gap and
  evidence.

## Closure

- Added `tradingbotsuite.research_discovery.analysis_report`, a deterministic
  research-only analysis helper that reads existing historical-cycle and
  exact-discovery outputs and writes `research_analysis.json` plus
  `research_analysis.md`.
- The helper summarizes pure ROI, trade-level Sortino when aggregate trade
  ledgers are present, feature-set/strategy/exit/holding-window performance,
  split evidence, gate blockers, discovery KNN/filter settings, discovery
  blockers, and top interesting rows.
- Generated the current BTC analysis under
  `data/research/operator_runs/analysis/r106_btc_current_analysis`.
- Added
  `docs/stage_reports/STAGE_R106_RESEARCH_ANALYTICS_NEXT_AGENT_HANDOFF.md`,
  which compiles the operator's direction into a next-agent plan for a
  one-button BTC/ETH research autopilot, mandatory post-run analytics,
  modern-window profiles, frozen-entry exit labs, simple-runner policy work,
  run-to-run comparisons, provider/catalog expansion, and UI progress polish.
- Registered `ISSUE-R106-002` for the remaining missing master workflow and
  analytics wiring.
- Validation:
  `python -m compileall -q src\tradingbotsuite` passed.
  `PYTHONPATH=src python -m pytest tests\research_discovery\test_analysis_report.py -q`
  passed with 2 tests.
  `PYTHONPATH=src python -m pytest tests\contracts -q` passed with 427 tests.
