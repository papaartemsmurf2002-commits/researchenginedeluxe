# Strategy Contract

Strategy research must be plugin-shaped and independent from the backtest engine core.

Implementation:

- Contracts: `src/tradingbotsuite/strategies/contracts.py`
- Registry: `src/tradingbotsuite/strategies/registry.py`
- Baseline configs: `configs/strategies/*.json`
- Backtest integration: `src/tradingbotsuite/backtesting/engine.py`

## Plugin shape

```python
class StrategyPlugin:
    strategy_id: str
    strategy_version: str
    allowed_holding_periods: tuple[str, ...]
    required_feature_sets: tuple[str, ...]

    def prepare(self, train_context): ...
    def predict(self, feature_frame): ...
    def explain(self, prediction_frame): ...
```

## Signal frame

Required output columns:

- `signal_time_ms`
- `symbol`
- `side`
- `strength`
- `confidence`
- `target_holding_min_ms`
- `target_holding_max_ms`
- `entry_policy`
- `exit_policy_id`
- `feature_set_id`
- `model_version`
- `skip_reason`
- `research_only`

Allowed sides are `long`, `short`, and `flat`.

## Rules

- Holding windows must target roughly 1 hour to 1 week.
- Strategy plugins must not place orders.
- Strategy plugins must not import live execution adapters.
- Strategy claims require baseline comparison and out-of-sample evidence.
- Perp-context strategy rows with `quality_latest_window_context_only > 0`
  must fail closed before signal emission. Latest-window context can remain
  diagnostic source coverage, but it is not accepted strategy evidence.
- KNN/HMM must be a strategy plugin, not hardcoded into the backtest engine.
- WT3D inclusion must be controlled by `feature_set_id` / config, not by engine code.
