from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class EventKind(str, Enum):
    BOS = "BOS"
    CHOCH = "CHoCH"
    CHOCH_PLUS = "CHoCH+"


class StructureScope(str, Enum):
    INTERNAL = "internal"
    SWING = "swing"


class ExitReason(str, Enum):
    LORENTZ = "lorentz_exit"
    RISK = "risk_exit"
    ORDER_BLOCK = "order_block_exit"
    END_OF_TEST = "end_of_test"


@dataclass(slots=True)
class Bar:
    timestamp: Any
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str


@dataclass(slots=True)
class FeatureVector:
    f1: float
    f2: float
    f3: float | None = None
    f4: float | None = None
    f5: float | None = None


@dataclass(slots=True)
class LorentzSignalState:
    prediction: float
    signal: int
    start_long_trade: bool
    start_short_trade: bool
    end_long_trade: bool
    end_short_trade: bool
    kernel_estimate: float
    is_bullish: bool
    is_bearish: bool


@dataclass(slots=True)
class MarketStructureEvent:
    index: int
    timestamp: Any
    kind: EventKind
    scope: StructureScope
    side: Side
    pivot_index: int
    pivot_price: float
    breakout_price: float


@dataclass(slots=True)
class OrderBlock:
    block_id: str
    created_index: int
    created_timestamp: Any
    scope: StructureScope
    side: Side
    top: float
    bottom: float
    midpoint: float
    anchor_index: int
    anchor_volume: float
    relevance_pct: float = 0.0
    mitigated_index: int | None = None
    touched_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.mitigated_index is None


@dataclass(slots=True)
class PositionState:
    side: Side
    entry_index: int
    entry_timestamp: Any
    entry_price: float
    quantity: float
    stop_price: float
    symbol: str
    open_reason: str
    pending_close_reason: str | None = None
    pending_order_block_id: str | None = None
    pending_order_block_side: Side | None = None
    pending_created_at: Any | None = None


@dataclass(slots=True)
class StrategyConfig:
    symbol: str = "BTC"
    source: str = "close"
    neighbors_count: int = 8
    max_bars_back: int = 4000
    feature_count: int = 5
    feature_definitions: list[tuple[str, int, int]] = field(
        default_factory=lambda: [
            ("RSI", 14, 1),
            ("WT", 10, 11),
            ("CCI", 23, 1),
            ("ADX", 27, 1),
            ("RSI", 8, 1),
        ]
    )
    color_compression: int = 1
    use_dynamic_exits: bool = True
    use_volatility_filter: bool = True
    use_regime_filter: bool = False
    use_adx_filter: bool = False
    regime_threshold: float = -0.1
    adx_threshold: int = 20
    use_ema_filter: bool = False
    ema_period: int = 200
    use_sma_filter: bool = False
    sma_period: int = 200
    use_kernel_filter: bool = True
    show_kernel_estimate: bool = True
    use_kernel_smoothing: bool = False
    kernel_lookback: int = 20
    kernel_relative_weight: float = 8.0
    kernel_regression_level: int = 10
    kernel_lag: int = 2
    use_order_block_exits: bool = False
    internal_lookback: int = 5
    swing_lookback: int = 50
    market_structure_mode: str = "manual"
    order_block_filter: str = "None"
    order_block_mitigation: str = "Absolute"
    order_block_position: str = "Precise"
    order_block_overlap: bool = True
    order_block_overlap_method: str = "Previous"
    order_block_relevance_pct: float = 10.0
    use_swing_order_blocks: bool = True
    base_timeframe: str = "15m"
    confirm_timeframe: str = "5m"
    allow_long: bool = True
    allow_short: bool = True
    fee_bps: float = 2.5
    slippage_bps: float = 1.0
    funding_rate_per_bar: float = 0.0
    lc_mode: str = "static"
    neighbor_diagnostics: int = 8
    min_prediction_magnitude: float = 0.0
    min_signal_persistence_bars: int = 1
    min_bars_between_entries: int = 0
    block_early_signal_flips: bool = False


@dataclass(slots=True)
class RiskConfig:
    initial_equity: float = 10_000.0
    risk_per_trade: float = 0.01
    leverage_cap: float = 3.0
    use_fixed_stop_loss: bool = False
    fixed_stop_loss_pct: float = 0.0055
    atr_stop_period: int = 14
    atr_stop_multiplier: float = 1.5
    min_stop_distance_pct: float = 0.003


@dataclass(slots=True)
class ExecutionConfig:
    rest_base_url: str = "https://api.hyperliquid.xyz"
    websocket_url: str = "wss://api.hyperliquid.xyz/ws"
    testnet: bool = False
    account_address: str | None = None
    secret_key: str | None = None
    state_path: str = "state/live_state.json"
    enable_live_trading: bool = False
    dead_mans_switch_secs: int = 30
    poll_seconds: int = 5


@dataclass(slots=True)
class BacktestConfig:
    use_worst_case: bool = False
    use_subcandle_execution: bool = True
    execution_timeframe_primary: str = "5m"
    execution_timeframe_fallback: str = "5m"
    execution_timeframe_policy: str = "best_effort"
    slow_reference_mode: bool = False
    enforce_close_only_entries: bool = True
    allow_same_bar_flip: bool = False
    min_trades: int = 5


@dataclass(slots=True)
class DataConfig:
    cache_dir: str = "data/cache"
    validate_reference_exchange: bool = True
    max_close_deviation_pct: float = 0.75
    min_validation_overlap_rows: int = 100


@dataclass(slots=True)
class OptimizationConfig:
    objective: str = "net_profit"
    train_days: int = 60
    validation_days: int = 14
    step_days: int = 14
    prescreen_bars: int = 500
    shortlist_size: int = 10
    minimum_trades: int = 10
    max_drawdown_pct: float = 25.0
    max_consecutive_losses: int = 6
    max_candidates_per_stage: int = 0
    parallel_workers: int = 0
    search_space: dict[str, list[Any]] = field(default_factory=dict)


@dataclass(slots=True)
class TradeResult:
    symbol: str
    side: Side
    entry_timestamp: Any
    exit_timestamp: Any
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    net_pnl: float
    return_pct: float
    exit_reason: ExitReason
    bars_held: int


@dataclass(slots=True)
class AppConfig:
    strategies: dict[str, StrategyConfig]
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data: DataConfig = field(default_factory=DataConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["strategies"] = {symbol: asdict(cfg) for symbol, cfg in self.strategies.items()}
        return raw

    def ensure_state_dir(self) -> None:
        Path(self.execution.state_path).parent.mkdir(parents=True, exist_ok=True)
