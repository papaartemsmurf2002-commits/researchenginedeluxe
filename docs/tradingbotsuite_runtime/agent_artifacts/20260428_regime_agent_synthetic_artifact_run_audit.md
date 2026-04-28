# Agent name

Regime Agent

# Task received

Independently audit one synthetic `research-hmm-knn` artifact run after the pytest config change. Use a temp output directory and verify regime posterior, no-trade, and entropy fields.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_hmm_regime_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_pytest_import_mode_fix.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `tests/tradingbotsuite/test_hmm_knn.py`
- Generated artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\regime_posteriors.parquet`
- Generated artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1\artifact_manifest.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_synthetic_artifact_run_audit.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-ChildItem -Force docs\tradingbotsuite_runtime\agent_artifacts
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_regime_agent_hmm_regime_audit.md
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_backtest_agent_pytest_import_mode_fix.md
```

Synthetic dataset generation:

```powershell
$env:PYTHONPATH='src;.'; @'
import json
import tempfile
from pathlib import Path

from tests.tradingbotsuite.test_hmm_knn import _synthetic_dataset

root = Path(tempfile.mkdtemp(prefix='hmm_knn_artifact_audit_'))
dataset = root / 'synthetic_btcusdt_hmm_knn.parquet'
output = root / 'research_output'
frame = _synthetic_dataset(row_count=180)
frame.to_parquet(dataset, index=False)
print(json.dumps({'root': str(root), 'dataset': str(dataset), 'output': str(output), 'rows': len(frame)}, indent=2))
'@ | python -
```

Exact dataset result:

```json
{
  "root": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o",
  "dataset": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\synthetic_btcusdt_hmm_knn.parquet",
  "output": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output",
  "rows": 180
}
```

CLI artifact run:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main research-hmm-knn --config configs/v2_btc_hmm_multi_knn_research.json --dataset "C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\synthetic_btcusdt_hmm_knn.parquet" --output-dir "C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output"
```

Exact CLI result:

```json
{
  "output_dir": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output\\v2-btc-hmm-multi-knn-1",
  "artifact_manifest_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output\\v2-btc-hmm-multi-knn-1\\artifact_manifest.json",
  "metrics_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output\\v2-btc-hmm-multi-knn-1\\walk_forward_metrics.json",
  "regime_posteriors_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output\\v2-btc-hmm-multi-knn-1\\regime_posteriors.parquet",
  "knn_predictions_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output\\v2-btc-hmm-multi-knn-1\\knn_predictions.parquet",
  "meta_predictions_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output\\v2-btc-hmm-multi-knn-1\\meta_predictions.parquet",
  "neighbor_diagnostics_path": "C:\\Users\\papaa\\AppData\\Local\\Temp\\hmm_knn_artifact_audit_p4o_uo8o\\research_output\\v2-btc-hmm-multi-knn-1\\neighbor_diagnostics.csv"
}
```

# Decisions made

- Used the real `research-hmm-knn` CLI with the production config and a temporary synthetic BTC parquet, not pytest.
- Reused the existing `_synthetic_dataset` helper because no ready HMM/KNN parquet fixture was present under `tests` or `data`.
- Confirmed the generated manifest is BTC-only and research-only: `symbol` is `BTCUSDT`, `asset_scope` is `["BTCUSDT"]`, and `research_only` is `true`.
- Confirmed the generated `regime_posteriors.parquet` has 48 rows and 18 columns.
- Confirmed posterior columns are present: `regime_p_0`, `regime_p_1`, `regime_p_2`, and `regime_p_3`.
- Confirmed posterior probabilities are normalized: row posterior sums have min `1.0` and max `1.0`.
- Confirmed entropy field is present and finite: `posterior_entropy` min and max are both `5.979470570797252e-11` on this synthetic run.
- Confirmed no-trade fields are present: `recent_regime_flip` and `regime_no_trade`.
- Observed `recent_regime_flip` count `0` and `regime_no_trade` count `0` on this synthetic run. This is acceptable because the synthetic fixture produced highly certain posterior assignments rather than uncertain transition rows.
- Confirmed train-fit marker integrity: every scored row has `hmm_fit_end_row < source_row_index`.
- Observed generated top regime labels `range_chop` and `shock_transition`.
- Confirmed backend reporting: manifest dependency `hmm_backend` is `["gaussian_mixture_fallback"]` and `hmmlearn_available` is `false` in this environment.

# Assumptions

- A synthetic audit run is allowed to have no regime no-trade rows if posterior confidence is high; the audit requirement is that the fields exist and are populated consistently.
- The temporary path is sufficient for handoff because the task requested a temp output directory.
- The Gaussian mixture fallback is expected here because optional `hmmlearn` is not installed in the active environment.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this run.

# Handoff notes for other agents

- The synthetic artifact run confirms regime artifact schema and backend metadata at the CLI artifact level, not only through unit tests.
- This specific synthetic dataset did not exercise uncertain posterior no-trade rows. Unit coverage for uncertain posterior no-trade behavior remains in `tests/tradingbotsuite/test_hmm_knn.py`.
- The artifact output directory is `C:\Users\papaa\AppData\Local\Temp\hmm_knn_artifact_audit_p4o_uo8o\research_output\v2-btc-hmm-multi-knn-1`.
