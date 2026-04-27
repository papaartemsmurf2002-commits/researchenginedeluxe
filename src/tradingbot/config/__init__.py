from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from tradingbot.models import (
    AppConfig,
    BacktestConfig,
    DataConfig,
    ExecutionConfig,
    OptimizationConfig,
    RiskConfig,
    StrategyConfig,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
LORENTZ_SETTINGS_PATH = REPO_ROOT / "references" / "lorentzian-classification" / "settings.txt"


def _parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def baseline_btc_strategy_from_settings(path: str | Path = LORENTZ_SETTINGS_PATH) -> StrategyConfig:
    settings_path = Path(path)
    strategy = StrategyConfig(symbol="BTC", use_order_block_exits=False, use_swing_order_blocks=False)
    if not settings_path.exists():
        return strategy

    lines = [line.strip() for line in settings_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        if lowered.startswith("neighbors count -"):
            strategy.neighbors_count = int(line.split("-", 1)[1].strip())
        elif lowered.startswith("max bars back -"):
            strategy.max_bars_back = int(line.split("-", 1)[1].strip())
        elif lowered.startswith("color compression -"):
            strategy.color_compression = int(line.split("-", 1)[1].strip())
        elif lowered.startswith("show default exits -"):
            pass
        elif lowered.startswith("use dynamic exits -"):
            strategy.use_dynamic_exits = _parse_bool(line.split("-", 1)[1])
        elif lowered.startswith("feature count -"):
            strategy.feature_count = int(line.split("-", 1)[1].strip())
        elif lowered.startswith("use volatility filter -"):
            strategy.use_volatility_filter = _parse_bool(line.split("-", 1)[1])
        elif lowered.startswith("trade with kernel -"):
            strategy.use_kernel_filter = _parse_bool(line.split("-", 1)[1])
        elif lowered.startswith("show kernel estimate -"):
            strategy.show_kernel_estimate = _parse_bool(line.split("-", 1)[1])
        elif lowered.startswith("lookback window -"):
            strategy.kernel_lookback = int(line.split("-", 1)[1].strip())
        elif lowered.startswith("relative weighting -"):
            strategy.kernel_relative_weight = float(line.split("-", 1)[1].strip())
        elif lowered.startswith("regression level -"):
            strategy.kernel_regression_level = int(line.split("-", 1)[1].strip())
        elif lowered.startswith("enhance kerrnel smoothing lag -"):
            strategy.kernel_lag = int(line.split("-", 1)[1].strip())
        elif lowered.startswith("feature 1 -"):
            strategy.feature_definitions[0] = ("RSI", 14, 1)
        elif lowered.startswith("feature 2 -"):
            strategy.feature_definitions[1] = ("WT", 10, 11)
        elif lowered.startswith("feature 3 -"):
            strategy.feature_definitions[2] = ("CCI", 23, 1)
        elif lowered.startswith("feature 4 -"):
            strategy.feature_definitions[3] = ("ADX", 27, 1)
        elif lowered.startswith("feature 5 -"):
            strategy.feature_definitions[4] = ("RSI", 8, 1)
    return strategy


def default_app_config() -> AppConfig:
    btc = baseline_btc_strategy_from_settings()
    return AppConfig(strategies={"BTC": btc})


def _coerce_strategy(raw: dict[str, Any]) -> StrategyConfig:
    feature_definitions = raw.get("feature_definitions")
    if feature_definitions:
        raw["feature_definitions"] = [tuple(item) for item in feature_definitions]
    return StrategyConfig(**raw)


def load_app_config(path: str | Path) -> AppConfig:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    strategies = {symbol: _coerce_strategy(cfg) for symbol, cfg in payload["strategies"].items()}
    risk = RiskConfig(**payload.get("risk", {}))
    execution = ExecutionConfig(**payload.get("execution", {}))
    backtest = BacktestConfig(**payload.get("backtest", {}))
    data = DataConfig(**payload.get("data", {}))
    optimization = OptimizationConfig(**payload.get("optimization", {}))
    return AppConfig(
        strategies=strategies,
        risk=risk,
        execution=execution,
        backtest=backtest,
        data=data,
        optimization=optimization,
    )


def save_app_config(config: AppConfig, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "strategies": {symbol: asdict(cfg) for symbol, cfg in config.strategies.items()},
        "risk": asdict(config.risk),
        "execution": asdict(config.execution),
        "backtest": asdict(config.backtest),
        "data": asdict(config.data),
        "optimization": asdict(config.optimization),
    }
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
