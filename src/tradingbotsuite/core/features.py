from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from tradingbotsuite.core.math import BAR_INTERVAL_MS, atr_wilder
from tradingbotsuite.core.models import Bar, SignalDirection

RESEARCH_FEATURE_VERSION = "v2-btc-acceptance-2"
FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000
TREND_FILTER_ER_LENGTH = 24
TREND_FILTER_CHOP_LENGTH = 14
TREND_FILTER_SLOPE_WINDOW = 24
TREND_FILTER_RANGE_WINDOW = 24

RESEARCH_FEATURE_COLUMNS = [
    "direction_long",
    "atr",
    "hurst",
    "efficiency_ratio",
    "choppiness",
    "slope_atr",
    "directional_slope_atr",
    "plus_di",
    "minus_di",
    "directional_di_spread",
    "range_width",
    "primary_signed_imbalance_ratio",
    "primary_sqrt_signed_imbalance_ratio",
    "primary_trade_sign_acf_lag1",
    "primary_flow_price_alignment_bps",
    "primary_impact_efficiency_bps_per_sqrt_notional",
    "top_of_book_imbalance",
    "queue_imbalance_l1",
    "queue_imbalance_l5",
    "queue_imbalance_l10",
    "spread_bps",
    "basis_bps",
    "funding_rate",
    "funding_rate_change",
    "time_to_next_funding_hours",
    "open_interest",
    "open_interest_change",
    "open_interest_change_pct",
    "open_interest_value",
    "premium_basis_rate",
    "premium_basis_abs",
    "premium_close",
    "realized_volatility",
    "atr_percentile",
    "volatility_shock_zscore",
    "volatility_shock_flag",
    "session_hour_sin",
    "session_hour_cos",
    "session_weekday",
    "session_asia",
    "session_europe",
    "session_us",
    "missing_hurst",
    "missing_efficiency_ratio",
    "missing_choppiness",
    "missing_slope_atr",
    "missing_directional_di_spread",
    "missing_range_width",
    "missing_primary_signed_imbalance_ratio",
    "missing_primary_sqrt_signed_imbalance_ratio",
    "missing_primary_trade_sign_acf_lag1",
    "missing_primary_flow_price_alignment_bps",
    "missing_primary_impact_efficiency_bps_per_sqrt_notional",
    "missing_top_of_book_imbalance",
    "missing_queue_imbalance_l1",
    "missing_queue_imbalance_l5",
    "missing_queue_imbalance_l10",
    "missing_spread_bps",
    "missing_basis_bps",
    "missing_funding_rate",
    "missing_funding_rate_change",
    "missing_time_to_next_funding_hours",
    "missing_open_interest",
    "missing_open_interest_change",
    "missing_open_interest_change_pct",
    "missing_open_interest_value",
    "missing_premium_basis_rate",
    "missing_premium_basis_abs",
    "missing_premium_close",
    "missing_realized_volatility",
    "missing_atr_percentile",
    "missing_volatility_shock_zscore",
]


@dataclass(frozen=True, slots=True)
class VolatilityFeatureConfig:
    realized_vol_window_bars: int
    atr_percentile_window_bars: int
    volatility_shock_window_bars: int
    volatility_shock_zscore_threshold: float


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _decimal_from_float(value: float | None, *, precision: int = 10) -> Decimal | None:
    if value is None or not math.isfinite(value):
        return None
    return Decimal(str(round(value, precision)))


def _rma(values: list[float], length: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if length <= 0 or len(values) < length:
        return result
    seed = sum(values[:length]) / length
    result[length - 1] = seed
    previous = seed
    for index in range(length, len(values)):
        previous = ((previous * (length - 1)) + values[index]) / length
        result[index] = previous
    return result


def _rma_optional(values: list[float | None], length: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    valid_indices = [index for index, value in enumerate(values) if value is not None]
    if length <= 0 or len(valid_indices) < length:
        return result
    seed_indices = valid_indices[:length]
    seed_index = seed_indices[-1]
    seed = sum(float(values[index]) for index in seed_indices) / length
    result[seed_index] = seed
    previous = seed
    for index in range(seed_index + 1, len(values)):
        value = values[index]
        if value is None:
            continue
        previous = ((previous * (length - 1)) + value) / length
        result[index] = previous
    return result


def compute_efficiency_ratio(bars: list[Bar], length: int) -> Decimal | None:
    if length <= 0 or len(bars) <= length:
        return None
    closes = [float(bar.close) for bar in bars]
    current = len(closes) - 1
    net_change = abs(closes[current] - closes[current - length])
    path = sum(abs(closes[index] - closes[index - 1]) for index in range(current - length + 1, current + 1))
    if path <= 0:
        return Decimal("0")
    return _decimal_from_float(max(0.0, min(1.0, net_change / path)), precision=6)


def compute_choppiness(bars: list[Bar], length: int) -> Decimal | None:
    if length <= 1 or len(bars) < length:
        return None
    denominator = math.log10(length)
    if denominator <= 0:
        return None
    window = bars[-length:]
    tr_sum = 0.0
    previous_close: Decimal | None = None
    for bar in window:
        if previous_close is None:
            tr_sum += float(bar.high - bar.low)
        else:
            tr_sum += max(
                float(bar.high - bar.low),
                abs(float(bar.high - previous_close)),
                abs(float(bar.low - previous_close)),
            )
        previous_close = bar.close
    high = max(float(bar.high) for bar in window)
    low = min(float(bar.low) for bar in window)
    range_width = high - low
    if range_width <= 0 or tr_sum <= 0:
        return None
    value = 100.0 * math.log10(tr_sum / range_width) / denominator
    return _decimal_from_float(value, precision=6)


def compute_slope_atr(bars: list[Bar], *, window: int, atr: Decimal) -> Decimal | None:
    if window <= 1 or len(bars) < window or atr <= 0:
        return None
    closes = [float(bar.close) for bar in bars[-window:]]
    x_values = list(range(window))
    x_mean = sum(x_values) / window
    x_denom = sum((x - x_mean) ** 2 for x in x_values)
    if x_denom <= 0:
        return None
    y_mean = sum(closes) / window
    slope_per_bar = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, closes)) / x_denom
    return _decimal_from_float((slope_per_bar * window) / float(atr), precision=6)


def compute_range_width(bars: list[Bar], length: int) -> Decimal | None:
    if length <= 1 or len(bars) < length:
        return None
    window = bars[-length:]
    latest_close = window[-1].close
    if latest_close <= 0:
        return None
    width = max(bar.high for bar in window) - min(bar.low for bar in window)
    return _decimal_from_float(float(width / latest_close), precision=6)


def compute_di_snapshot(bars: list[Bar], length: int) -> tuple[Decimal | None, Decimal | None]:
    if length <= 0 or len(bars) < (length + 1):
        return None, None
    plus_dm = [0.0]
    minus_dm = [0.0]
    true_ranges = [float(bars[0].high - bars[0].low)]
    previous = bars[0]
    for current in bars[1:]:
        up_move = float(current.high - previous.high)
        down_move = float(previous.low - current.low)
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        true_ranges.append(
            max(
                float(current.high - current.low),
                abs(float(current.high - previous.close)),
                abs(float(current.low - previous.close)),
            )
        )
        previous = current
    tr_rma = _rma(true_ranges, length)
    plus_rma = _rma(plus_dm, length)
    minus_rma = _rma(minus_dm, length)
    if tr_rma[-1] in {None, 0} or plus_rma[-1] is None or minus_rma[-1] is None:
        return None, None
    plus_di = 100.0 * plus_rma[-1] / tr_rma[-1]
    minus_di = 100.0 * minus_rma[-1] / tr_rma[-1]
    return _decimal_from_float(plus_di, precision=6), _decimal_from_float(minus_di, precision=6)


def compute_realized_volatility(closes: list[Decimal], window_bars: int) -> Decimal | None:
    if window_bars <= 1 or len(closes) < window_bars + 1:
        return None
    window = closes[-(window_bars + 1) :]
    returns = []
    for previous, current in zip(window, window[1:]):
        if previous <= 0 or current <= 0:
            return None
        returns.append(math.log(float(current / previous)))
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    return Decimal(str(round(math.sqrt(max(variance, 0.0)), 10)))


def compute_atr_percentile(bars: list[Bar], *, atr_length: int, percentile_window_bars: int) -> Decimal | None:
    if percentile_window_bars <= 1 or len(bars) < (atr_length + percentile_window_bars):
        return None
    atr_series: list[Decimal] = []
    start_index = len(bars) - percentile_window_bars
    for index in range(start_index, len(bars)):
        subset = bars[: index + 1]
        if len(subset) >= atr_length + 1:
            atr_series.append(atr_wilder(subset, atr_length))
    if not atr_series:
        return None
    current = atr_series[-1]
    le_count = sum(1 for value in atr_series if value <= current)
    return Decimal(str(round(le_count / len(atr_series), 6)))


def compute_volatility_shock(
    closes: list[Decimal],
    *,
    window_bars: int,
    zscore_threshold: float,
) -> tuple[Decimal | None, bool]:
    if window_bars <= 2 or len(closes) < (window_bars * 2):
        return None, False
    realized_values: list[float] = []
    for end_index in range(window_bars + 1, len(closes) + 1):
        value = compute_realized_volatility(closes[:end_index], window_bars)
        if value is not None:
            realized_values.append(float(value))
    if len(realized_values) < window_bars + 1:
        return None, False
    current = realized_values[-1]
    history = realized_values[-(window_bars + 1) : -1]
    if len(history) < 2:
        return None, False
    mean = sum(history) / len(history)
    variance = sum((value - mean) ** 2 for value in history) / (len(history) - 1)
    if variance <= 0:
        return Decimal("0"), False
    zscore = (current - mean) / math.sqrt(variance)
    return Decimal(str(round(zscore, 6))), zscore >= zscore_threshold


def session_features(timestamp_ms: int) -> dict[str, Any]:
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
    hour = dt.hour + (dt.minute / 60)
    radians = (hour / 24.0) * 2.0 * math.pi
    return {
        "session_hour_utc": dt.hour,
        "session_weekday": dt.weekday(),
        "session_hour_sin": round(math.sin(radians), 6),
        "session_hour_cos": round(math.cos(radians), 6),
        "session_asia": 1 if 0 <= dt.hour < 8 else 0,
        "session_europe": 1 if 7 <= dt.hour < 16 else 0,
        "session_us": 1 if 13 <= dt.hour < 22 else 0,
    }


def infer_time_to_next_funding_ms(timestamp_ms: int) -> int:
    remainder = timestamp_ms % FUNDING_INTERVAL_MS
    delta = FUNDING_INTERVAL_MS - remainder if remainder != 0 else FUNDING_INTERVAL_MS
    return timestamp_ms + delta


def confidence_bucket(probability: float, thresholds: list[float]) -> str:
    ordered = sorted(float(value) for value in thresholds)
    if not ordered:
        return "unscored"
    if probability < ordered[0]:
        return "very_low"
    if len(ordered) == 1 or probability < ordered[1]:
        return "low"
    if len(ordered) == 2 or probability < ordered[2]:
        return "medium"
    return "high"


def size_multiplier_candidate(probability: float, thresholds: list[float], values: list[float]) -> float:
    best = 0.0
    for threshold, value in zip(thresholds, values, strict=False):
        if probability >= float(threshold):
            best = float(value)
    return best


def build_extended_feature_snapshot(
    *,
    signal_direction: SignalDirection,
    signal_time_ms: int,
    latest_bar: Bar,
    bars: list[Bar],
    atr: Decimal,
    atr_length: int,
    hurst: Decimal | None,
    microstructure: dict[str, Any] | None,
    basis_snapshot: dict[str, Any] | None,
    funding_context: dict[str, Any] | None,
    open_interest_context: dict[str, Any] | None,
    premium_context: dict[str, Any] | None,
    primary_window_seconds: int,
    volatility_config: VolatilityFeatureConfig,
) -> dict[str, Any]:
    closes = [bar.close for bar in bars]
    efficiency_ratio = compute_efficiency_ratio(bars, TREND_FILTER_ER_LENGTH)
    choppiness = compute_choppiness(bars, TREND_FILTER_CHOP_LENGTH)
    slope_atr = compute_slope_atr(bars, window=TREND_FILTER_SLOPE_WINDOW, atr=atr)
    range_width = compute_range_width(bars, TREND_FILTER_RANGE_WINDOW)
    plus_di, minus_di = compute_di_snapshot(bars, atr_length)
    direction_sign = Decimal("1") if signal_direction == SignalDirection.LONG else Decimal("-1")
    directional_slope_atr = (slope_atr * direction_sign) if slope_atr is not None else None
    directional_di_spread = ((plus_di - minus_di) * direction_sign) if plus_di is not None and minus_di is not None else None
    realized_volatility = compute_realized_volatility(closes, volatility_config.realized_vol_window_bars)
    atr_percentile = compute_atr_percentile(
        bars,
        atr_length=atr_length,
        percentile_window_bars=volatility_config.atr_percentile_window_bars,
    )
    volatility_shock_zscore, volatility_shock_flag = compute_volatility_shock(
        closes,
        window_bars=volatility_config.volatility_shock_window_bars,
        zscore_threshold=volatility_config.volatility_shock_zscore_threshold,
    )
    session = session_features(signal_time_ms)
    primary_window = (microstructure or {}).get("windows", {}).get(str(primary_window_seconds), {})

    snapshot: dict[str, Any] = {
        "feature_version": RESEARCH_FEATURE_VERSION,
        "direction": str(signal_direction),
        "latest_bar_time_ms": latest_bar.time_ms,
        "latest_close": str(latest_bar.close),
        "bar_count": len(bars),
        "atr": str(atr),
        "hurst": str(hurst) if hurst is not None else None,
        "efficiency_ratio": str(efficiency_ratio) if efficiency_ratio is not None else None,
        "choppiness": str(choppiness) if choppiness is not None else None,
        "slope_atr": str(slope_atr) if slope_atr is not None else None,
        "directional_slope_atr": str(directional_slope_atr) if directional_slope_atr is not None else None,
        "plus_di": str(plus_di) if plus_di is not None else None,
        "minus_di": str(minus_di) if minus_di is not None else None,
        "directional_di_spread": str(directional_di_spread) if directional_di_spread is not None else None,
        "range_width": str(range_width) if range_width is not None else None,
        "primary_signed_imbalance_ratio": primary_window.get("signed_ratio"),
        "primary_sqrt_signed_imbalance_ratio": primary_window.get("sqrt_signed_ratio"),
        "primary_trade_sign_acf_lag1": primary_window.get("trade_sign_acf_lag1"),
        "primary_flow_price_alignment_bps": primary_window.get("flow_price_alignment_bps"),
        "primary_impact_efficiency_bps_per_sqrt_notional": primary_window.get("impact_efficiency_bps_per_sqrt_notional"),
        "top_of_book_imbalance": (microstructure or {}).get("top_of_book_imbalance"),
        "queue_imbalance_l1": (microstructure or {}).get("queue_imbalance_l1"),
        "queue_imbalance_l5": (microstructure or {}).get("queue_imbalance_l5"),
        "queue_imbalance_l10": (microstructure or {}).get("queue_imbalance_l10"),
        "spread_bps": (microstructure or {}).get("spread_bps"),
        "microstructure": microstructure,
        "basis": basis_snapshot,
        "funding_context": funding_context,
        "open_interest_context": open_interest_context,
        "premium_context": premium_context,
        "realized_volatility": str(realized_volatility) if realized_volatility is not None else None,
        "atr_percentile": str(atr_percentile) if atr_percentile is not None else None,
        "volatility_shock_zscore": str(volatility_shock_zscore) if volatility_shock_zscore is not None else None,
        "volatility_shock_flag": volatility_shock_flag,
        **session,
    }

    missing = {
        "hurst": hurst is None,
        "efficiency_ratio": efficiency_ratio is None,
        "choppiness": choppiness is None,
        "slope_atr": slope_atr is None,
        "directional_di_spread": directional_di_spread is None,
        "range_width": range_width is None,
        "primary_signed_imbalance_ratio": snapshot["primary_signed_imbalance_ratio"] is None,
        "primary_sqrt_signed_imbalance_ratio": snapshot["primary_sqrt_signed_imbalance_ratio"] is None,
        "primary_trade_sign_acf_lag1": snapshot["primary_trade_sign_acf_lag1"] is None,
        "primary_flow_price_alignment_bps": snapshot["primary_flow_price_alignment_bps"] is None,
        "primary_impact_efficiency_bps_per_sqrt_notional": snapshot["primary_impact_efficiency_bps_per_sqrt_notional"] is None,
        "top_of_book_imbalance": snapshot["top_of_book_imbalance"] is None,
        "queue_imbalance_l1": snapshot["queue_imbalance_l1"] is None,
        "queue_imbalance_l5": snapshot["queue_imbalance_l5"] is None,
        "queue_imbalance_l10": snapshot["queue_imbalance_l10"] is None,
        "spread_bps": snapshot["spread_bps"] is None,
        "basis_bps": basis_snapshot is None or basis_snapshot.get("basis_bps") is None,
        "funding_rate": funding_context is None or funding_context.get("funding_rate") is None,
        "funding_rate_change": funding_context is None or funding_context.get("funding_rate_change") is None,
        "time_to_next_funding_hours": funding_context is None or funding_context.get("time_to_next_funding_ms") is None,
        "open_interest": open_interest_context is None or open_interest_context.get("open_interest") is None,
        "open_interest_change": open_interest_context is None or open_interest_context.get("open_interest_change") is None,
        "open_interest_change_pct": open_interest_context is None or open_interest_context.get("open_interest_change_pct") is None,
        "open_interest_value": open_interest_context is None or open_interest_context.get("open_interest_value") is None,
        "premium_basis_rate": premium_context is None or premium_context.get("basis_rate") is None,
        "premium_basis_abs": premium_context is None or premium_context.get("basis") is None,
        "premium_close": premium_context is None or premium_context.get("premium_close") is None,
        "realized_volatility": realized_volatility is None,
        "atr_percentile": atr_percentile is None,
        "volatility_shock_zscore": volatility_shock_zscore is None,
    }
    snapshot["missing"] = missing
    return snapshot


def numeric_feature_map(snapshot: dict[str, Any]) -> dict[str, float]:
    basis_snapshot = snapshot.get("basis") or {}
    funding_context = snapshot.get("funding_context") or {}
    open_interest_context = snapshot.get("open_interest_context") or {}
    premium_context = snapshot.get("premium_context") or {}
    missing = snapshot.get("missing") or {}

    def number(value: Any) -> float:
        parsed = _decimal(value)
        return float(parsed) if parsed is not None else 0.0

    feature_map = {
        "direction_long": 1.0 if str(snapshot.get("direction")) == str(SignalDirection.LONG) else 0.0,
        "atr": number(snapshot.get("atr")),
        "hurst": number(snapshot.get("hurst")),
        "efficiency_ratio": number(snapshot.get("efficiency_ratio")),
        "choppiness": number(snapshot.get("choppiness")),
        "slope_atr": number(snapshot.get("slope_atr")),
        "directional_slope_atr": number(snapshot.get("directional_slope_atr")),
        "plus_di": number(snapshot.get("plus_di")),
        "minus_di": number(snapshot.get("minus_di")),
        "directional_di_spread": number(snapshot.get("directional_di_spread")),
        "range_width": number(snapshot.get("range_width")),
        "primary_signed_imbalance_ratio": number(snapshot.get("primary_signed_imbalance_ratio")),
        "primary_sqrt_signed_imbalance_ratio": number(snapshot.get("primary_sqrt_signed_imbalance_ratio")),
        "primary_trade_sign_acf_lag1": number(snapshot.get("primary_trade_sign_acf_lag1")),
        "primary_flow_price_alignment_bps": number(snapshot.get("primary_flow_price_alignment_bps")),
        "primary_impact_efficiency_bps_per_sqrt_notional": number(snapshot.get("primary_impact_efficiency_bps_per_sqrt_notional")),
        "top_of_book_imbalance": number(snapshot.get("top_of_book_imbalance")),
        "queue_imbalance_l1": number(snapshot.get("queue_imbalance_l1")),
        "queue_imbalance_l5": number(snapshot.get("queue_imbalance_l5")),
        "queue_imbalance_l10": number(snapshot.get("queue_imbalance_l10")),
        "spread_bps": number(snapshot.get("spread_bps")),
        "basis_bps": number(basis_snapshot.get("basis_bps")),
        "funding_rate": number(funding_context.get("funding_rate")),
        "funding_rate_change": number(funding_context.get("funding_rate_change")),
        "time_to_next_funding_hours": (
            number(funding_context.get("time_to_next_funding_ms")) / (60.0 * 60.0 * 1000.0)
            if funding_context.get("time_to_next_funding_ms") is not None
            else 0.0
        ),
        "open_interest": number(open_interest_context.get("open_interest")),
        "open_interest_change": number(open_interest_context.get("open_interest_change")),
        "open_interest_change_pct": number(open_interest_context.get("open_interest_change_pct")),
        "open_interest_value": number(open_interest_context.get("open_interest_value")),
        "premium_basis_rate": number(premium_context.get("basis_rate")),
        "premium_basis_abs": number(premium_context.get("basis")),
        "premium_close": number(premium_context.get("premium_close")),
        "realized_volatility": number(snapshot.get("realized_volatility")),
        "atr_percentile": number(snapshot.get("atr_percentile")),
        "volatility_shock_zscore": number(snapshot.get("volatility_shock_zscore")),
        "volatility_shock_flag": 1.0 if snapshot.get("volatility_shock_flag") else 0.0,
        "session_hour_sin": float(snapshot.get("session_hour_sin") or 0.0),
        "session_hour_cos": float(snapshot.get("session_hour_cos") or 0.0),
        "session_weekday": float(snapshot.get("session_weekday") or 0.0),
        "session_asia": float(snapshot.get("session_asia") or 0.0),
        "session_europe": float(snapshot.get("session_europe") or 0.0),
        "session_us": float(snapshot.get("session_us") or 0.0),
    }
    for key in list(missing):
        feature_map[f"missing_{key}"] = 1.0 if missing.get(key) else 0.0
    for key in RESEARCH_FEATURE_COLUMNS:
        feature_map.setdefault(key, 0.0)
    return feature_map


def label_position_pnl_multiple(
    *,
    direction: SignalDirection,
    entry_price: Decimal,
    exit_price: Decimal,
    atr: Decimal,
) -> Decimal:
    if atr <= 0:
        return Decimal("0")
    signed_return = (exit_price - entry_price) if direction == SignalDirection.LONG else (entry_price - exit_price)
    return signed_return / atr


def bar_close_time_ms(bar_time_ms: int) -> int:
    return bar_time_ms + BAR_INTERVAL_MS
