# HMM Multi-KNN Source Log

This source log condenses the workbook `crypto_hmm_multi_knn_production_matrix (1).xlsx`.

For preserved local source filenames, including the Cyrillic DOCX name and ASCII alias, see `HMM_MULTI_KNN_INPUT_LOOKUP.md`.

## Production Matrix Sources

| Source label | URL | Use in plan | Caveat |
| --- | --- | --- | --- |
| HMM crypto regime forecasting 2025 | https://link.springer.com/article/10.1007/s42521-024-00123-2 | Supports regime-switching framing for crypto | Adapt forecasting evidence to trade decisions carefully |
| Regime-aware HMM Bitcoin 2026 | https://link.springer.com/article/10.1007/s10614-026-11338-3 | Supports BTC regime classification and hybrid forecasting | Daily BTC evidence, not direct intraday perp proof |
| BTC HMM macro covariates 2025 | https://www.mdpi.com/2227-7390/13/10/1577 | Supports covariates and non-homogeneous HMM direction | Longer horizon than Phase 1 |
| Bayesian HMM crypto predictability 2022 | https://doi.org/10.1016/j.ribaf.2021.101554 | Supports state-dependent crypto predictors | Older but useful foundation |
| Lorentzian metric classifier 2016 | https://doi.org/10.1016/j.patrec.2016.09.006 | Supports Lorentzian distance as robust classifier metric | Not trading-specific |
| Lorentzian Classification TradingView | https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/ | Practitioner blueprint for log-Lorentzian KNN and filters | Community script, not production validation |
| WaveTrend 3D TradingView | https://www.tradingview.com/script/clUzC70G-WaveTrend-3D/ | WT3D feature family and oscillator design | Needs independent backtest |
| WaveTrend 3D Python implementation | https://github.com/artnaz/wavetrend-3d | Reference implementation for later parity checks | Must verify against Pine before trusting |
| Feature selection technical indicators crypto 2025 | https://www.techscience.com/cmc/v83n2/60595/html | Supports broad feature selection and walk-forward discipline | Daily horizons |
| CUSUM + triple barrier crypto 2025 | https://link.springer.com/article/10.1186/s40854-025-00866-w | Supports path-dependent labels and CUSUM event sampling | Must adapt to perp fees and funding |
| News sentiment BTC ETH futures 2026 | https://link.springer.com/article/10.1007/s11147-025-09223-6 | Supports later sentiment layer and BTC/ETH futures context | Slower signal frequency |
| Perpetual futures primer Coinbase | https://www.coinbase.com/institutional/research-insights/research/market-intelligence/a-primer-on-perpetual-futures | Supports funding and perp market structure | Industry source |
| Perpetual futures fundamentals | https://arxiv.org/abs/2212.06888 | Supports funding mechanics | Not an alpha model |
| Order flow and cryptocurrency returns 2026 | https://doi.org/10.1016/j.finmar.2026.101047 | Supports order-flow and nonlinear ML features | Data access can be hard |
| Cross-cryptocurrency return predictability 2024 | https://doi.org/10.1016/j.jedc.2024.104863 | Supports ETH Phase 2 BTC-lead features | Cross-section evidence needs BTC/ETH validation |
| ML crypto model comparison 2025 | https://link.springer.com/article/10.1007/s44163-025-00519-y | Supports XGBoost/GBM meta-labeling benchmark | Daily selected assets |
| NN BTC ETH trading 2026 | https://link.springer.com/article/10.1007/s00500-025-10980-7 | Supports multi-asset BTC/ETH validation | Buy-only simulation |
| HMM-SVM-MKL regime classifier 2025 | https://link.springer.com/article/10.1007/s11009-025-10148-8 | Supports hybrid generative/discriminative regime models | Equities, not crypto perps |
| GMM + KNN/RF market movement 2024 | https://arxiv.org/abs/2409.03762 | Supports unsupervised filtering before KNN/RF | Preprint |

## Dependency Notes

- `hmmlearn==0.3.3` is selected for the first Gaussian HMM research backend.
- The package is an optional research dependency because the normal runtime should not require HMM tooling.
- The PyPI page notes limited maintenance; if Python 3.14 wheel support blocks local installation, use a Python 3.12 research environment rather than changing the model design.
- XGBoost is selected as the first meta-labeler and is isolated under the `research` extra.
- LightGBM remains a documented alternative if XGBoost fails locally or future benchmarking justifies switching.

## Validation Notes

- Repo-wide pytest collection uses `addopts = "--import-mode=importlib"` in `pyproject.toml` because this repository currently has duplicate test module basenames in both `tests/` and `tests/tradingbotsuite/`.
- The importlib-mode decision was validated by the Backtest Agent with `$env:PYTHONPATH='src'; python -m pytest -q`; the mid-development readiness scorecard reported `383 passed in 146.44s`.
- CLI/E2E fixture validation runs `research-hmm-knn` followed by `monitor-hmm-knn` through `python -m tradingbotsuite.main` using synthetic BTC data and temporary output paths; it verifies expected artifacts and observe-only monitoring flags.
- Synthetic artifact smoke validation used the real `research-hmm-knn` CLI with the production config and a temporary BTC dataset, then audited generated regime, KNN, meta, and monitoring artifacts.
- `monitor-hmm-knn --manifest <artifact_manifest.json>` generated an observe-only `monitoring_report.json`; warning alerts remain research diagnostics and do not change live trading state.
- Final live-boundary review and readiness scorecard confirmed HMM/KNN docs, commands, artifacts, and UI summaries remain research-only and do not modify live execution, sizing, gates, Hyperliquid behavior, safety behavior, or operator live controls. No positive expectancy or live-readiness claim exists yet.

Checked dependency references:

- https://pypi.org/project/hmmlearn/
- https://xgboost.readthedocs.io/en/stable/install.html
- https://pypi.org/project/lightgbm/
