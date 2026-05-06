# Stage R70 Operator Research Product Redesign Report

Date: 2026-05-06
Work packet: `docs/work_packets/WPR70-01-operator-research-product-redesign.md`

## Summary

R70 redesigns the operator UI Research tab as a current-branch research control
room. The page now explains what an operator is about to run, when to use it,
what it tests, and where evidence appears.

This stage is limited to the UI template and focused operator UI test coverage.
It does not change provider execution, experiment execution, historical-cycle
execution, live execution, promotion behavior, generated artifacts, or
research-only boundaries.

## Implementation

- Replaced the older generic/diagnostic-heavy layout in
  `src/tradingbotsuite/web/templates/research.html` with:
  - an explicit Research Control Room header and research-only boundary chips,
  - operator-intent tiles,
  - provider pipeline presets and stage buttons,
  - inline explanations for `intake`, `dataset`, `evidence`, and `all`,
  - research experiment presets with editable spec paths,
  - historical-cycle review presets with exact terminal commands,
  - current evidence-flow explanation,
  - profitability, candidate mix, gate status, and holding-window charts,
  - latest status, shadow diagnostics, Stage 13 readiness, HMM/KNN monitoring,
    jobs, and artifact review.
- Moved older signal-history build/train/calibrate/replay controls into
  advanced diagnostics so they are not presented as the main research path.
- Removed rendered legacy and TradingView wording from the Research page.
- Strengthened `tests/tradingbotsuite/test_operator_ui.py` to assert the new
  product surface, explained current controls, historical-cycle command, and
  absence of legacy/TradingView/live-control language.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
```

Passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py -q
```

Passed: 43 passed.

```powershell
@'
const fs = require("fs");
const html = fs.readFileSync("src/tradingbotsuite/web/templates/research.html", "utf8");
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(match => match[1]);
for (const code of blocks) new Function(code);
console.log("ok", blocks.length);
'@ | node
```

Passed: `ok 1`.

```powershell
git diff --check
```

Passed.

## Boundary

No live command endpoints, mode switches, manual-signal controls, smoke-live
controls, promotion shortcuts, or live adapter behavior were added. Research
artifacts remain observe-only unless a later promotion process changes them.
