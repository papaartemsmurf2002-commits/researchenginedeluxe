# Agent Workstreams

Use these boundaries when several agents work in parallel.

## LC Core Agent

Owns:

- `src/tradingbot/features_tv.py`
- `src/tradingbot/kernels_tv.py`
- `src/tradingbot/lorentz_tv.py`
- `src/tradingbot/tv_backtest.py`
- LC-focused tests in `tests/test_tv_parity.py`

Do not change UI, data providers, or live execution in the same patch.

## Parity Tooling Agent

Owns:

- `src/tradingbot/parity.py`
- `src/tradingbot/lc_marker_research.py`
- `docs/lc_lorentzian_diagnostic_*_export.pine`
- `docs/PARITY_WORKFLOW.md`

Keep generated CSV exports out of Git.

## UI Agent

Owns:

- `src/tradingbot/ui.py`
- `tests/test_ui_diagnostics.py`
- `docs/UI_VALIDATION.md`

The UI may call the classifier and parity helpers, but must not mutate config files or live state.

## Data And Backtest Agent

Owns:

- `src/tradingbot/data/`
- `src/tradingbot/backtest.py`
- `src/tradingbot/optimization.py`
- `src/tradingbot/risk.py`
- `tests/test_data_manager.py`
- `tests/test_strategy_flow.py`

Keep provider/cache behavior independent from parity fixtures.

## Execution Agent

Owns:

- `src/tradingbot/live.py`
- `src/tradingbot/data/hyperliquid.py`
- execution-related config fields in `src/tradingbot/models.py`

Live trading must remain disabled by default.

## Documentation Agent

Owns:

- `README.md`
- `docs/`
- `examples/`
- `references/`

Documentation changes should include the exact command needed to verify the documented behavior.
