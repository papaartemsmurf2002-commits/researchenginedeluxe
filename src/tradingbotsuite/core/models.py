from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuntimeMode(StrEnum):
    SHADOW = "shadow"
    PAPER = "paper"
    LIVE = "live"


class SignalDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class DecisionAction(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    IGNORE = "ignore"
    FLIP = "flip"
    EXIT = "exit"


class ExecutionIntentType(StrEnum):
    ENTER = "enter"
    CLOSE = "close"
    CANCEL = "cancel"
    PROTECTIVE_TP = "protective_tp"
    PROTECTIVE_SL = "protective_sl"


class ExecutionStatus(StrEnum):
    INTENDED = "intended"
    ACKED = "acked"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class TradeStatus(StrEnum):
    FLAT = "flat"
    OPEN = "open"
    PENDING_OPEN = "pending_open"
    PENDING_CLOSE = "pending_close"
    SAFE_MODE = "safe_mode"


class ExitReason(StrEnum):
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_BARRIER = "time_barrier"
    ADVERSE_SELECTION = "adverse_selection"
    ALPHA_DECAY = "alpha_decay"
    FLIP = "flip"
    SAFE_MODE = "safe_mode"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class SafeModeReason(StrEnum):
    NONE = "none"
    STALE_MARKET_DATA = "stale_market_data"
    HEARTBEAT_LOSS = "heartbeat_loss"
    POSITION_AMBIGUITY = "position_ambiguity"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"
    RECONCILIATION_STALE = "reconciliation_stale"
    BASIS_DISLOCATION = "basis_dislocation"
    ORDER_TIMEOUT = "order_timeout"
    ACCOUNT_NOT_CONFIGURED = "account_not_configured"


class SafetyState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    SAFE_MODE = "safe_mode"
    BLOCKED = "blocked"


class ModelBase(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class Bar(ModelBase):
    time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal("0")


class SignalIntent(ModelBase):
    signal_id: str
    source: str = "external_signal"
    symbol: str
    direction: SignalDirection
    signal_bar_time_ms: int
    received_time_ms: int
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class DecisionPacket(ModelBase):
    signal: SignalIntent
    mode: RuntimeMode
    action: DecisionAction
    accepted: bool
    rejection_reason: str | None = None
    intended_size: Decimal = Decimal("0")
    entry_reference_price: Decimal | None = None
    atr: Decimal | None = None
    tp_price: Decimal | None = None
    sl_price: Decimal | None = None
    vertical_barrier_time_ms: int | None = None
    confidence_bucket: str = "bootstrap"
    model_version: str = "phase1-bootstrap"
    calibration_version: str = "phase1-none"
    feature_snapshot: dict[str, Any] = Field(default_factory=dict)


class PositionState(ModelBase):
    symbol: str
    status: TradeStatus
    direction: SignalDirection | None = None
    position_size: Decimal = Decimal("0")
    entry_price: Decimal | None = None
    entry_time_ms: int | None = None
    entry_bar_time_ms: int | None = None
    entry_atr: Decimal | None = None
    hurst_at_entry: Decimal | None = None
    imbalance_at_entry: Decimal | None = None
    tp_price: Decimal | None = None
    sl_price: Decimal | None = None
    vertical_barrier_time_ms: int | None = None
    entry_order_cloid: str | None = None
    tp_order_cloid: str | None = None
    sl_order_cloid: str | None = None
    last_exchange_reconcile_ms: int | None = None
    last_exit_reason: ExitReason | None = None
    last_updated_ms: int | None = None


class ExecutionIntent(ModelBase):
    intent_id: str
    mode: RuntimeMode
    intent_type: ExecutionIntentType
    symbol: str
    direction: SignalDirection | None = None
    size: Decimal = Decimal("0")
    reference_price: Decimal | None = None
    trigger_price: Decimal | None = None
    reduce_only: bool = False
    cloid: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionReport(ModelBase):
    intent_id: str
    intent_type: ExecutionIntentType
    status: ExecutionStatus
    symbol: str
    exchange_order_id: str | None = None
    cloid: str | None = None
    filled_price: Decimal | None = None
    filled_size: Decimal | None = None
    message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ActionTicket(ModelBase):
    ticket_id: str
    signal_id: str
    mode: RuntimeMode
    symbol: str
    decision_time_ms: int
    action_type: str
    readable_summary: str
    features_json: dict[str, Any] = Field(default_factory=dict)
    intended_orders_json: list[dict[str, Any]] = Field(default_factory=list)
    rationale_json: dict[str, Any] = Field(default_factory=dict)


class SafetyStatus(ModelBase):
    in_safe_mode: bool
    state: SafetyState = SafetyState.HEALTHY
    reason: SafeModeReason = SafeModeReason.NONE
    reason_code: str | None = None
    detail: str = ""
    recommended_action: str | None = None
    updated_time_ms: int


class ReconcileState(ModelBase):
    symbol: str
    exchange_position_size: Decimal = Decimal("0")
    exchange_side: SignalDirection | None = None
    open_order_cloids: list[str] = Field(default_factory=list)
