# TradingView Archive Map: research/v3-experimental-engine

Date: 2026-05-01
Stage: Stage 1 - Repo cartography

## Summary

The research branch already removed the active TradingView source pipeline and many Pine/parity surfaces. Remaining mentions are mainly historical, label names, and boundary tests. Stage 1 does not move files; it records what must stay legacy-only.

## Removed or no longer active

| Surface | Status |
| --- | --- |
| Active TradingView chart-export importer commands | Removed from `src/tradingbotsuite/main.py` on this branch. |
| `src/tradingbotsuite/research/tradingview_import.py` | Removed on this branch. |
| `tradingbot` parity commands such as `parity-check`, `entry-parity`, `merge-tv-exports`, `marker-research` | Removed on this branch. |
| `features_tv.py`, `kernels_tv.py`, `lorentz_tv.py`, `tv_backtest.py`, `parity.py`, `lc_marker_research.py` names | Replaced or removed from active command surface on this branch. |
| Pine export docs in root `docs/` | Not present on this branch except historical agent references. |

## Remaining references

| Path | Classification | Notes |
| --- | --- | --- |
| `README.md` | Branch statement | Says legacy vendor-specific import, chart replay, parity diagnostics, and source-script references were removed. |
| `tests/test_removed_source_boundaries.py` | Contract seed | Verifies removed source names and commands remain absent. |
| `src/tradingbotsuite/research/dataset.py` | Label name legacy | `LABEL_VERSION = "triple_barrier_live_parity_v1"` includes `parity` text but refers to live-like fill/label parity, not TradingView parity. |
| `tests/tradingbotsuite/test_hmm_knn.py`, `tests/tradingbotsuite/test_research.py` | Label version assertions | Preserve current label contract name. |
| `docs/tradingbotsuite_runtime/agent_artifacts/**` | Historical evidence | Contains prior agent memos that mention parity, TradingView, WT3D, and label contracts. Keep as archived evidence. |

## Archive recommendation

Stage 2 documentation should state:

- TradingView/Pine/parity code is not an active research pipeline on `research/v3-experimental-engine`.
- Historical docs under `docs/tradingbotsuite_runtime/agent_artifacts/` are retained as evidence, not active workflow instructions.
- `tests/test_removed_source_boundaries.py` should remain until a stronger import-boundary contract replaces it.
- Label names containing `parity` may remain until Stage 2/3 contract versioning decides whether to rename them without breaking existing artifacts.

## Do not reintroduce without explicit approval

- TradingView CSV import as canonical data input.
- Pine export scripts as active pipeline dependencies.
- Marker-only fitting or marker-parity tuning.
- TradingView parity commands in the active CLI.
- Any docs that imply TradingView output is a promotion-ready live signal.
