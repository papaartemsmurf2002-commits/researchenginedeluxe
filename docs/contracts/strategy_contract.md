# Strategy Contract

Strategy research must be plugin-shaped and independent from the backtest engine core.

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
