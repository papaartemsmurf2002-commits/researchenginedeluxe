# WPR106-162 Component Pocket Portfolio Overlap Audit

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Run a May-blind follow-up to WPR106-161 that tests whether pre-May-defined
component pockets can become more stable as small equal-sleeve portfolios once
overlap and active trade rates are accounted for. WPR106-161 showed that
component pockets were less bad than matched controls but still row-level
rejected. This packet builds fixed portfolios from those pre-May-selected
pocket rows and matched controls using only pre-May evidence, then benchmarks
May 2026 after the portfolios are frozen.

Portfolio construction and selection use 2024-01-01 through 2026-04-30 only.
May 2026 is fully excluded from portfolio generation, scoring, overlap
diagnostics, exposure caps, ranking, and selection. May 2026 is used only as a
fixed benchmark holdout after selected portfolios are fixed.

## Allowed Paths

- `docs/work_packets/WPR106-162-component-pocket-portfolio-overlap-audit.md`
- `docs/stage_reports/STAGE_R106_COMPONENT_POCKET_PORTFOLIO_OVERLAP_AUDIT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_162_component_pocket_portfolio_overlap_audit/**`

## Inputs

- Read-only WPR106-161 selected component-pocket rows, matched-control rows,
  and selected/control pre-May and May trade details under
  `data/research/wpr106_161_pre_may_component_pocket_control_audit/**`.

## Method

- Load WPR106-161 component-pocket and matched-control rows.
- Compute pre-May row daily/monthly returns from trade details.
- Generate deterministic equal-sleeve portfolios separately for component
  pockets and matched controls, using only pre-May row metrics:
  - quality-ranked portfolios;
  - low-correlation portfolios;
  - low same-day-overlap portfolios;
  - mixed packet/family portfolios;
  - 2-, 3-, 4-, 6-, and 8-sleeve variants where enough sleeves exist.
- Score portfolios only from pre-May return, losing-month counts, best-month
  concentration, drop-best-month robustness, daily overlap diagnostics,
  active trade rates, drawdown, and packet/family diversity.
- Select fixed portfolios with packet/family/source exposure caps.
- Replay the fixed selected portfolios on May 2026 only after selection.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_162_component_pocket_portfolio_overlap_audit/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write generated portfolio rankings, selected pre-May portfolios, selected
  portfolio pre-May trades/daily/monthly artifacts, May benchmark artifacts,
  summary, and stage report.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

WPR106-162 generated 660 May-blind equal-sleeve portfolios from WPR106-161
component-pocket and matched-control rows, selected 72 fixed pre-May portfolios
under source and construction caps, and benchmarked the fixed set on May 2026
only after selection.

May rejected every selected portfolio: component-pocket portfolios had 0
positive, 39 negative, and 0 flat rows, with best -0.005600, worst -0.069842,
median -0.029799, and mean -0.030960; matched controls had 0 positive, 33
negative, and 0 flat rows, with best -0.009271, worst -0.103368, median
-0.054215, and mean -0.048921. Component pockets remained less bad than
controls, but neither group is candidate-ready, portfolio-ready, or
promotion-ready.

The run wrote research-only artifacts under
`data/research/wpr106_162_component_pocket_portfolio_overlap_audit/**`. It did
not write a candidate pack, paper/live artifact, live config, order path,
sizing change, CUDA speedup claim, or promotion claim. Focused script compile,
package compile, and contracts passed; contracts reported 460 passed.
