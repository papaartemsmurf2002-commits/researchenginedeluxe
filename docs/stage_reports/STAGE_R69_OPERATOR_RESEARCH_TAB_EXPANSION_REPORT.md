# Stage R69 Operator Research Tab Expansion Report

Date: 2026-05-06
Work packet: `docs/work_packets/WPR69-01-operator-research-tab-expansion.md`

## Summary

R69 expands the operator UI Research tab so it represents the full research
branch instead of reading like a mostly HMM/KNN page.

This stage is limited to UI explanations and read-only artifact summaries. It
does not change operator command behavior, research execution behavior, live
execution behavior, promotion behavior, generated artifacts, or checked
evidence.

## Implementation

- Expanded `src/tradingbotsuite/web/templates/research.html` with:
  - research-track explanations,
  - clear separation between provider pipeline, research experiment, and legacy
    V2 signal-history model flow,
  - read-only profitability chart,
  - candidate mix chart,
  - gate status chart,
  - holding-window chart.
- Added `historical_research_cycle` summaries in
  `src/tradingbotsuite/operator_console.py` by reading existing
  `research_cycle_manifest.json`, `candidate_rankings.parquet`,
  `candidate_gate_report.parquet`, and `metrics_by_holding_window.parquet`.
- Kept HMM/KNN monitoring, shadow diagnostics, Stage 13 readiness, jobs, and
  artifact cards visible.
- Preserved the Research page boundary: no live command endpoints, mode
  switches, manual-signal buttons, smoke-live controls, or promotion controls
  were added.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
```

Passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
```

Passed: 27 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py -q
```

Passed: 43 passed.

```powershell
node -e "const fs=require('fs'); const html=fs.readFileSync('src/tradingbotsuite/web/templates/research.html','utf8'); const blocks=[...html.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)].map(m=>m[1]); for (const [i,code] of blocks.entries()) { new Function(code); } console.log('ok', blocks.length);"
```

Passed: `ok 1`.

```powershell
git diff --check
```

Passed.

## Next Gate

No further work is required for this request. If the UI later needs live browser
visual QA, open a separate scoped packet to run a local server and capture
desktop/mobile screenshots.
