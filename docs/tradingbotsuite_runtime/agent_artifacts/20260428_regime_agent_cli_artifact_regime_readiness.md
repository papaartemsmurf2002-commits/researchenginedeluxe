# Agent name

Regime Agent

# Task received

Objective: validate regime behavior in the CLI/E2E artifact, not only unit tests.

Requested commands:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
rg -n "regime_posteriors.parquet|posterior_entropy|max_regime_probability|regime_no_trade|hmm_fit_end_row" docs/tradingbotsuite_runtime/agent_artifacts src tests
```

Requested tasks:

- Inspect the CLI/E2E artifact from Backtest Agent.
- Confirm `regime_posteriors.parquet` has valid posterior sums, entropy, no-trade flags, backend, split id, and train fit boundary fields.
- Report whether the smoke artifact has enough regime diversity or is only a contract smoke.

# Files read

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_cli_e2e_fixture_validation.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_synthetic_cli_artifact_audit.md`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- Generated CLI/E2E artifact: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_cli_e2e_regime_readiness_b1hc2ipj\research_output\test-hmm-knn\regime_posteriors.parquet`
- Generated CLI/E2E manifest: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_cli_e2e_regime_readiness_b1hc2ipj\research_output\test-hmm-knn\artifact_manifest.json`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_cli_artifact_regime_readiness.md`

# Commands/tests run

Requested test command:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Exact result:

```text
.......................                                                  [100%]
23 passed in 12.63s
```

Requested search:

```powershell
rg -n "regime_posteriors.parquet|posterior_entropy|max_regime_probability|regime_no_trade|hmm_fit_end_row" docs/tradingbotsuite_runtime/agent_artifacts src tests
```

The search found the implementation, monitoring, unit/E2E tests, model docs, and prior artifacts that mention these fields. Key current test locations include:

- `tests/tradingbotsuite/test_hmm_knn.py:500` for `max_regime_probability`
- `tests/tradingbotsuite/test_hmm_knn.py:501` for `posterior_entropy`
- `tests/tradingbotsuite/test_hmm_knn.py:502` for `regime_no_trade`
- `tests/tradingbotsuite/test_hmm_knn.py:503` for `hmm_fit_end_row`
- `tests/tradingbotsuite/test_hmm_knn.py:590` for `hmm_fit_end_row < source_row_index`

Backtest Agent artifact inspection:

```powershell
Get-Content docs\tradingbotsuite_runtime\agent_artifacts\20260428_backtest_agent_cli_e2e_fixture_validation.md
Get-Content tests\tradingbotsuite\test_hmm_knn.py | Select-Object -Skip 705 -First 100
```

Fresh reproduction of the Backtest CLI/E2E path for direct parquet inspection:

```powershell
$env:PYTHONPATH='src;.'; @'
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from tests.tradingbotsuite.test_hmm_knn import _synthetic_dataset, _write_test_config

root = Path(tempfile.mkdtemp(prefix='hmm_knn_cli_e2e_regime_readiness_'))
config_path = _write_test_config(root)
dataset_path = root / 'dataset.parquet'
output_dir = root / 'research_output'
_synthetic_dataset().to_parquet(dataset_path, index=False)
env = {**os.environ, 'PYTHONPATH': str(Path('src').resolve())}
research = subprocess.run(
    [
        sys.executable,
        '-m',
        'tradingbotsuite.main',
        'research-hmm-knn',
        '--config',
        str(config_path),
        '--dataset',
        str(dataset_path),
        '--output-dir',
        str(output_dir),
    ],
    check=True,
    capture_output=True,
    text=True,
    env=env,
)
# Loaded regime_posteriors.parquet and artifact_manifest.json with pandas/json.
'@ | python -
```

# Decisions made

- Treated the Backtest Agent CLI/E2E artifact as the documented smoke path in `20260428_backtest_agent_cli_e2e_fixture_validation.md`.
- Reproduced that path with the same `_write_test_config` and `_synthetic_dataset` helpers because the pytest `tmp_path` artifact is intentionally temporary.
- Verified the generated CLI artifact directly from parquet rather than relying only on unit assertions.
- Did not change research code, live runtime code, execution behavior, sizing, gates, Hyperliquid behavior, safety behavior, or operator live controls.

# CLI/E2E regime artifact inspection

Generated artifact paths:

- Root: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_cli_e2e_regime_readiness_b1hc2ipj`
- Manifest: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_cli_e2e_regime_readiness_b1hc2ipj\research_output\test-hmm-knn\artifact_manifest.json`
- Regime parquet: `C:\Users\papaa\AppData\Local\Temp\hmm_knn_cli_e2e_regime_readiness_b1hc2ipj\research_output\test-hmm-knn\regime_posteriors.parquet`

Manifest summary:

- `research_only`: `true`
- `plan_version`: `test-hmm-knn`
- `symbol`: `BTCUSDT`
- `asset_scope`: `["BTCUSDT"]`
- `row_count`: `44`
- HMM backend: `["gaussian_mixture_fallback"]`
- `hmmlearn_available`: `false`

`regime_posteriors.parquet` summary:

- Shape: `44` rows x `17` columns.
- Posterior columns: `regime_p_0`, `regime_p_1`, `regime_p_2`.
- Required field check: no missing required regime fields.
- Posterior row sums: min `1.0`, max `1.0`, all close to `1.0`.
- `max_regime_probability`: min `1.0`, max `1.0`.
- `posterior_entropy`: finite for all rows, min `5.030167858294522e-11`, max `5.030167858294522e-11`.
- `regime_no_trade`: count `0`, rate `0.0`.
- `recent_regime_flip`: count `0`.
- `regime_model_backend`: `["gaussian_mixture_fallback"]`.
- `walk_forward_split`: splits `0` and `1`.
- Rows by split: split `0` has `24`, split `1` has `20`.
- Train-fit boundary: `hmm_fit_end_row < source_row_index` is true for all rows.

# Regime diversity assessment

The Backtest CLI/E2E smoke artifact has limited regime diversity:

- Unique numeric `top_regime` values: `[1, 2]`.
- Unique `top_regime_label` values: `bear_trend` and `bull_trend`.
- Label counts: `bear_trend: 24`, `bull_trend: 20`.
- It does not exercise `range_chop`, shock/transition, uncertain posterior, high entropy, recent flip, or no-trade regime rows.

Readiness conclusion:

- This artifact is a valid CLI/E2E contract smoke for artifact generation, schema, posterior normalization, backend recording, split id recording, and train-fit boundary fields.
- It is not enough to prove broad regime behavior or readiness because it only covers two confident trend labels and no no-trade/transition cases.
- Broader regime-readiness evidence should use a purpose-built fixture that forces at least range/chop, bull trend, bear trend, shock/transition, high-entropy uncertainty, and recent-flip rows.

# Assumptions

- The Backtest Agent CLI/E2E artifact refers to the reproducible test path added in `test_hmm_knn_cli_research_then_monitor_writes_expected_temp_artifacts`.
- Reproducing that path in a fresh temp directory is acceptable because the original pytest temp artifact is not meant to be a stable repo artifact.
- Zero no-trade rows in this smoke artifact is not a failure of the artifact contract, but it is a limitation for regime-readiness assessment.

# Open issues or blockers

None.

No issue was appended to `HMM_MULTI_KNN_AGENT_ISSUES.md` because the artifact is fit for contract smoke purposes; the diversity limitation is documented here as handoff guidance rather than a blocker.

# Handoff notes for other agents

- The CLI/E2E smoke path validates regime artifact shape and core numeric consistency through the real `research-hmm-knn` command path.
- Do not use this smoke artifact as evidence that all configured regime types or no-trade logic are exercised end-to-end.
- A future Regime/Backtest hardening task should add a dedicated E2E regime-diversity fixture if the supervisor wants CLI-level proof of no-trade, high entropy, flip cooldown, and shock/range states.
