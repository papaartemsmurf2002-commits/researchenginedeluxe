# Stage R106 Repo State Research Performance Correlation Audit Report

Date: 2026-06-18
Packet: WPR106-227
Status: closed

## Scope

This packet audited the current local checkout, observable GitHub/local
difference, local WPR106 research artifacts, recorded performance, and
correlation diagnostics. It produced an agent-readable report and spreadsheet.

No strategy search, source-code behavior change, generated artifact rewrite,
candidate pack, paper/live artifact, sizing change, runtime-mode change, live
configuration write, or promotion claim was made.

## Repo State

- Local branch: `main`
- Local `HEAD`: `0be5e0d5892443df1e34804f3a819c26f9c5ed03`
- Fetched `origin/main`:
  `3f4b45ce3f8ecca3e21def076d99ddca5db4ecf0`
- Fresh advertised GitHub `main` from `git ls-remote`:
  `3f4b45ce3f8ecca3e21def076d99ddca5db4ecf0`
- Ahead/behind versus fetched `origin/main`: `0 1`
- Remote-only commit:
  `3f4b45c docs: add Harvard Algorithmic Trading repomix transfer report`
- Remote-only file:
  `docs/external_repo_analysis/harvard_algorithmic_trading_ai_repomix_transfer.md`
  with 1,029 insertions.
- Working tree at extraction time: 57 tracked changed files, 388 untracked
  files, and a fetched-origin diff shortstat of 58 files changed, 10,927
  insertions, 1,555 deletions.

## Artifact Coverage

- WPR106 data directories scanned: 144.
- Summary JSON files normalized: 142.
- Parquet result files read: 213.
- Detail/top-performance rows written: 3,698.
- Correlation diagnostics written: 218.
- Stage R106 reports inventoried: 212.

## Output Artifacts

- `docs/research_knowledge/WPR106-227-repo-state-research-performance-correlation-audit.md`
- `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/repo_research_performance_correlation_audit.xlsx`
- `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/research_audit_data.json`
- `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/research_summary_rows.csv`
- `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/research_detail_rows.csv`
- `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/research_correlation_rows.csv`
- `outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/stage_report_inventory.csv`

## Lead Decision

When hard promotion gates and broad month-stability requirements are ignored,
the strongest research-only leads are:

1. WPR106-146 ETH relative-strength KNN trade-veto overlay.
2. WPR106-214 transparent motif replacement portfolio.
3. WPR106-221 transparent motif active fallback repair.
4. WPR106-222 directional KNN source-level gating.
5. Narrow diagnostic follow-ups from WPR106-180, WPR106-209, and WPR106-186.

The highest raw pre-May pockets, especially WPR106-139 and WPR106-220-derived
selectors, are weaker than their raw return suggests because fixed May replay
and correlation diagnostics show transfer failure.

## Validation

Commands run:

```powershell
python outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/extract_research_audit.py
& 'C:\Users\papaa\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/build_research_audit_workbook.mjs
```

Validation results:

- Extractor completed and wrote normalized JSON/CSV evidence.
- Workbook export completed successfully with seven sheets.
- Workbook previews rendered.
- Workbook formula/error scan matched 0 entries.

## Boundary

All outputs remain `research_only`, `observe_only`, and `promotion_ready:
false`. This packet is evidence organization and interpretation only, not a
candidate-ready, portfolio-ready, paper-ready, live-ready, sizing, runtime, or
promotion artifact.
