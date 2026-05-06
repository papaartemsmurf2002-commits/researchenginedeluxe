# WPR69-01 Operator Research Tab Expansion

Stage: R69 operator research tab expansion
Owner: Codex Research Agent
Status: closed
Created: 2026-05-06

## Goal

Expand the operator UI Research tab so it clearly represents the full research
branch, not only HMM/KNN. Add compact explanations for provider intake,
fixtures, features, strategies, backtests/exits, optimizer/stability gates,
candidate packs, and research-only boundaries. Add lightweight chart panels
inspired by the legacy `tradingbot` backtest profitability/equity concept,
using current research artifacts instead of legacy TradingView/export paths.

## Allowed paths

```text
src/tradingbotsuite/operator_console.py
src/tradingbotsuite/web/templates/research.html
tests/tradingbotsuite/test_operator_ui.py
docs/work_packets/WPR69-01-operator-research-tab-expansion.md
docs/stage_reports/STAGE_R69_OPERATOR_RESEARCH_TAB_EXPANSION_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- UI/artifact summary changes only.
- Do not change operator command behavior, research execution behavior, live
  execution behavior, promotion behavior, generated artifacts, or checked
  evidence.
- Do not use TradingView exports.
- Charts must be read-only summaries of existing artifacts.
- Research outputs must remain `research_only`, `observe_only`, and
  `promotion_ready: false` unless an existing artifact already says otherwise.

## Review checklist

- Research tab explains all main research tracks.
- Page no longer looks like HMM/KNN is the only research system.
- Profitability chart is based on current research-cycle/model metrics.
- Historical research-cycle artifacts appear in `/api/operator/research/artifacts`.
- No live command endpoints are introduced on the Research page.
- Existing HMM/KNN monitoring, shadow diagnostics, and Stage 13 diagnostics stay visible.

## Exit validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
```

## Close evidence

- Expanded `/ui/research` with full research-track explanations for data
  intake, feature lab, strategy tests, backtests/exits, optimizer/gates, and
  promotion boundary.
- Preserved the older V2 signal-history model workflow but labeled it as legacy
  V2 model flow so it no longer looks like the whole research system.
- Added read-only canvas chart panels for profitability, candidate mix, gate
  status, and holding-window evidence.
- Added `historical_research_cycle` artifact summaries to
  `/api/operator/research/artifacts` by reading existing cycle manifest,
  rankings, gate report, and holding-window parquet outputs.
- Added tests for historical-cycle profitability summaries and for the expanded
  Research page content.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
    - 27 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py -q`
    - 43 passed
  - Research page embedded script parse check passed with Node.
  - `git diff --check`
