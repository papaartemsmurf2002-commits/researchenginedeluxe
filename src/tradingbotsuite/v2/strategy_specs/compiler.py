# V2-AUDIT-ID: V2-AUD-STRAT-001
# V2-CONTRACTS: docs/contracts/strategy_spec_contract.md
# V2-BOUNDARY: research_only, deterministic_signal_frame, no_live_imports
# V2-OWNER: v2_strategy_specs
"""Deterministic declarative spec to signal-frame compiler."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.strategy_specs.registry import StrategySignalType
from tradingbotsuite.v2.strategy_specs.schemas import (
    SignalFrame,
    SignalRow,
    StrategySpec,
)
from tradingbotsuite.v2.strategy_specs.validator import parse_strategy_spec

_TIMEFRAME_RE = re.compile(r"^(?P<count>[1-9][0-9]*)(?P<unit>[mhd])$")


def compile_signal_frame(
    spec: StrategySpec | Mapping[str, Any],
    panel_rows: Iterable[Mapping[str, Any]],
) -> SignalFrame:
    parsed = parse_strategy_spec(spec)
    rows = _normalize_panel_rows(panel_rows, parsed)
    by_instrument = _history_by_instrument(rows)
    lookback = _lookback_bars(parsed)
    if parsed.logic.signal_type in {
        StrategySignalType.CROSS_SECTIONAL_RANK,
        StrategySignalType.LIQUIDITY_FILTERED,
    }:
        signal_rows = _compile_rank_signals(parsed, rows, by_instrument, lookback)
    elif parsed.logic.signal_type == StrategySignalType.VOL_ADJUSTED_TREND:
        signal_rows = _compile_vol_adjusted_trend_signals(parsed, rows, by_instrument, lookback)
    else:
        signal_rows = [
            _compile_single_instrument_signal(parsed, row, by_instrument[row.instrument_id], lookback)
            for row in rows
        ]
    signal_rows = sorted(signal_rows, key=lambda row: (row.ts, row.instrument_id))
    return SignalFrame(
        strategy_id=parsed.strategy_id,
        spec_hash=parsed.spec_hash,
        rows=tuple(signal_rows),
        row_count=len(signal_rows),
    )


class _PanelRow:
    def __init__(self, raw: Mapping[str, Any], *, ts: datetime, instrument_id: str) -> None:
        self.raw = raw
        self.ts = ts
        self.instrument_id = instrument_id
        self.history_index = -1

    def value(self, field: str) -> Any:
        return self.raw.get(field)


def _normalize_panel_rows(
    rows: Iterable[Mapping[str, Any]],
    spec: StrategySpec,
) -> list[_PanelRow]:
    required_fields = {"ts", "instrument_id", *spec.inputs.fields}
    normalized: list[_PanelRow] = []
    for index, row in enumerate(rows):
        missing = sorted(field for field in required_fields if field not in row)
        if missing:
            raise ValueError(f"panel row {index} missing fields: {','.join(missing)}")
        normalized.append(
            _PanelRow(
                row,
                ts=_parse_timestamp(row["ts"]),
                instrument_id=str(row["instrument_id"]),
            )
        )
    return sorted(normalized, key=lambda row: (row.ts, row.instrument_id))


def _history_by_instrument(rows: list[_PanelRow]) -> dict[str, list[_PanelRow]]:
    by_instrument: dict[str, list[_PanelRow]] = defaultdict(list)
    for row in rows:
        by_instrument[row.instrument_id].append(row)
    sorted_history: dict[str, list[_PanelRow]] = {}
    for instrument_id, instrument_rows in by_instrument.items():
        ordered = sorted(instrument_rows, key=lambda row: row.ts)
        for index, row in enumerate(ordered):
            row.history_index = index
        sorted_history[instrument_id] = ordered
    return sorted_history


def _lookback_bars(spec: StrategySpec) -> int:
    if spec.logic.lookback_bars is not None:
        return spec.logic.lookback_bars
    assert spec.logic.lookback_hours is not None
    step_hours = _timeframe_hours(spec.inputs.timeframe)
    return max(1, int(spec.logic.lookback_hours / step_hours))


def _timeframe_hours(timeframe: str) -> float:
    match = _TIMEFRAME_RE.fullmatch(timeframe)
    if not match:
        raise ValueError(f"unsupported strategy timeframe: {timeframe}")
    count = int(match.group("count"))
    unit = match.group("unit")
    if unit == "m":
        return count / 60
    if unit == "h":
        return float(count)
    if unit == "d":
        return float(count * 24)
    raise ValueError(f"unsupported strategy timeframe unit: {unit}")


def _compile_rank_signals(
    spec: StrategySpec,
    rows: list[_PanelRow],
    by_instrument: dict[str, list[_PanelRow]],
    lookback: int,
) -> list[SignalRow]:
    by_ts: dict[datetime, list[_PanelRow]] = defaultdict(list)
    for row in rows:
        by_ts[row.ts].append(row)
    signals: list[SignalRow] = []
    for ts in sorted(by_ts):
        scored: list[tuple[float, _PanelRow]] = []
        filtered: list[tuple[_PanelRow, str]] = []
        for row in sorted(by_ts[ts], key=lambda item: item.instrument_id):
            filter_reason = _filter_reason(spec, row)
            if filter_reason is not None:
                filtered.append((row, filter_reason))
                continue
            score = _metric_score(spec, row, by_instrument[row.instrument_id], lookback)
            if score is None:
                filtered.append((row, "insufficient_history"))
                continue
            scored.append((score, row))
        long_rows: set[str] = set()
        short_rows: set[str] = set()
        if scored:
            scored = sorted(scored, key=lambda item: (item[0], item[1].instrument_id))
            if spec.logic.rank_direction == "reversion":
                if spec.logic.long_top_quantile is not None:
                    count = max(1, int(math.ceil(len(scored) * spec.logic.long_top_quantile)))
                    long_rows = {row.instrument_id for _score, row in scored[:count]}
                if spec.logic.short_bottom_quantile is not None:
                    count = max(1, int(math.ceil(len(scored) * spec.logic.short_bottom_quantile)))
                    short_rows = {row.instrument_id for _score, row in scored[-count:]}
            else:
                if spec.logic.short_bottom_quantile is not None:
                    count = max(1, int(math.ceil(len(scored) * spec.logic.short_bottom_quantile)))
                    short_rows = {row.instrument_id for _score, row in scored[:count]}
                if spec.logic.long_top_quantile is not None:
                    count = max(1, int(math.ceil(len(scored) * spec.logic.long_top_quantile)))
                    long_rows = {row.instrument_id for _score, row in scored[-count:]}
        active_count = len(long_rows | short_rows)
        weight = _active_weight(spec, active_count)
        score_by_instrument = {row.instrument_id: score for score, row in scored}
        for _score, row in scored:
            if row.instrument_id in long_rows and row.instrument_id not in short_rows:
                signals.append(_signal_row(spec, row, signal=1.0, weight=weight, score=score_by_instrument[row.instrument_id], reason="rank_long"))
            elif row.instrument_id in short_rows and row.instrument_id not in long_rows:
                signals.append(_signal_row(spec, row, signal=-1.0, weight=-weight, score=score_by_instrument[row.instrument_id], reason="rank_short"))
            else:
                signals.append(_signal_row(spec, row, signal=0.0, weight=0.0, score=score_by_instrument[row.instrument_id], reason="rank_middle"))
        for row, reason in filtered:
            signals.append(_signal_row(spec, row, signal=0.0, weight=0.0, score=None, reason=reason))
    return signals


def _compile_single_instrument_signal(
    spec: StrategySpec,
    row: _PanelRow,
    history: list[_PanelRow],
    lookback: int,
) -> SignalRow:
    filter_reason = _filter_reason(spec, row)
    if filter_reason is not None:
        return _signal_row(spec, row, signal=0.0, weight=0.0, score=None, reason=filter_reason)
    if spec.logic.signal_type == StrategySignalType.MEAN_REVERSION:
        score = _zscore(row, history, lookback)
        threshold = spec.logic.entry_threshold if spec.logic.entry_threshold is not None else 1.0
        if score is None:
            return _signal_row(spec, row, signal=0.0, weight=0.0, score=None, reason="insufficient_history")
        if score <= -threshold:
            return _signal_row(spec, row, signal=1.0, weight=_active_weight(spec, 1), score=score, reason="mean_reversion_long")
        if score >= threshold:
            return _signal_row(spec, row, signal=-1.0, weight=-_active_weight(spec, 1), score=score, reason="mean_reversion_short")
        return _signal_row(spec, row, signal=0.0, weight=0.0, score=score, reason="mean_reversion_flat")
    if spec.logic.signal_type == StrategySignalType.FUNDING_CARRY:
        score = _numeric(row.value("funding"))
        if score is None:
            score = _numeric(row.value("funding_rate"))
        threshold = spec.logic.entry_threshold if spec.logic.entry_threshold is not None else 0.0
        if score is None:
            return _signal_row(spec, row, signal=0.0, weight=0.0, score=None, reason="funding_missing")
        if score > threshold:
            return _signal_row(spec, row, signal=-1.0, weight=-_active_weight(spec, 1), score=score, reason="funding_carry_short")
        if score < -threshold:
            return _signal_row(spec, row, signal=1.0, weight=_active_weight(spec, 1), score=score, reason="funding_carry_long")
        return _signal_row(spec, row, signal=0.0, weight=0.0, score=score, reason="funding_carry_flat")
    if spec.logic.signal_type == StrategySignalType.VOLATILITY_BREAKOUT:
        prior = _prior_rows(row, history, lookback)
        if len(prior) < lookback:
            return _signal_row(spec, row, signal=0.0, weight=0.0, score=None, reason="insufficient_history")
        close = _numeric(row.value("close"))
        if close is None:
            return _signal_row(spec, row, signal=0.0, weight=0.0, score=None, reason="close_missing")
        high = max(_numeric(item.value("high")) or _numeric(item.value("close")) or close for item in prior)
        low = min(_numeric(item.value("low")) or _numeric(item.value("close")) or close for item in prior)
        if close > high:
            return _signal_row(spec, row, signal=1.0, weight=_active_weight(spec, 1), score=close - high, reason="breakout_long")
        if close < low:
            return _signal_row(spec, row, signal=-1.0, weight=-_active_weight(spec, 1), score=close - low, reason="breakout_short")
        return _signal_row(spec, row, signal=0.0, weight=0.0, score=0.0, reason="breakout_flat")
    return _signal_row(spec, row, signal=0.0, weight=0.0, score=None, reason="unsupported_signal_type")


def _compile_vol_adjusted_trend_signals(
    spec: StrategySpec,
    rows: list[_PanelRow],
    by_instrument: dict[str, list[_PanelRow]],
    lookback: int,
) -> list[SignalRow]:
    by_ts: dict[datetime, list[_PanelRow]] = defaultdict(list)
    for row in rows:
        by_ts[row.ts].append(row)
    threshold = spec.logic.entry_threshold if spec.logic.entry_threshold is not None else 1.0
    target_volatility = _parameter_float(spec, "target_volatility_per_bar", default=0.002)
    signals: list[SignalRow] = []
    for ts in sorted(by_ts):
        active: list[tuple[_PanelRow, float, float, float, str]] = []
        inactive: list[tuple[_PanelRow, float | None, str]] = []
        for row in sorted(by_ts[ts], key=lambda item: item.instrument_id):
            filter_reason = _filter_reason(spec, row)
            if filter_reason is not None:
                inactive.append((row, None, filter_reason))
                continue
            scored = _vol_adjusted_trend_score(
                spec,
                row,
                by_instrument[row.instrument_id],
                lookback,
            )
            if scored is None:
                inactive.append((row, None, "insufficient_history"))
                continue
            score, realized_volatility = scored
            if abs(score) < threshold:
                inactive.append((row, score, "vol_adjusted_trend_flat"))
                continue
            direction = 1.0 if score > 0 else -1.0
            raw_weight = _vol_target_weight(
                spec,
                realized_volatility=realized_volatility,
                target_volatility=target_volatility,
            )
            if raw_weight <= 0.0:
                inactive.append((row, score, "vol_adjusted_trend_zero_weight"))
                continue
            reason = "vol_adjusted_trend_long" if direction > 0 else "vol_adjusted_trend_short"
            active.append((row, score, direction, raw_weight, reason))
        total_gross = sum(item[3] for item in active)
        gross_scale = 1.0 if total_gross <= spec.risk.max_gross_leverage else spec.risk.max_gross_leverage / total_gross
        for row, score, direction, raw_weight, reason in active:
            weight = direction * raw_weight * gross_scale
            signals.append(_signal_row(spec, row, signal=direction, weight=weight, score=score, reason=reason))
        for row, score, reason in inactive:
            signals.append(_signal_row(spec, row, signal=0.0, weight=0.0, score=score, reason=reason))
    return signals


def _vol_adjusted_trend_score(
    spec: StrategySpec,
    row: _PanelRow,
    history: list[_PanelRow],
    lookback: int,
) -> tuple[float, float] | None:
    mode = spec.logic.rank_metric or "return_over_volatility"
    if mode == "breakout_over_atr":
        return _breakout_over_atr_score(spec, row, history, lookback)
    return _return_over_volatility_score(spec, row, history, lookback)


def _return_over_volatility_score(
    spec: StrategySpec,
    row: _PanelRow,
    history: list[_PanelRow],
    lookback: int,
) -> tuple[float, float] | None:
    prior = _prior_rows(row, history, lookback)
    if len(prior) < lookback:
        return None
    current_close = _numeric(row.value("close"))
    base_close = _numeric(prior[0].value("close"))
    if current_close is None or base_close is None or base_close <= 0:
        return None
    vol_lookback = _parameter_int(spec, "volatility_lookback_bars", default=max(lookback, 24))
    realized_volatility = _realized_volatility(row, history, vol_lookback)
    if realized_volatility is None:
        return None
    realized_volatility = max(realized_volatility, _volatility_floor(spec))
    return ((current_close / base_close) - 1.0) / realized_volatility, realized_volatility


def _breakout_over_atr_score(
    spec: StrategySpec,
    row: _PanelRow,
    history: list[_PanelRow],
    lookback: int,
) -> tuple[float, float] | None:
    prior = _prior_rows(row, history, lookback)
    if len(prior) < lookback:
        return None
    close = _numeric(row.value("close"))
    if close is None:
        return None
    channel_high = max(_numeric(item.value("high")) or _numeric(item.value("close")) or close for item in prior)
    channel_low = min(_numeric(item.value("low")) or _numeric(item.value("close")) or close for item in prior)
    atr_lookback = _parameter_int(spec, "atr_lookback_bars", default=max(lookback, 24))
    atr = _average_true_range(row, history, atr_lookback)
    if atr is None:
        return None
    atr = max(atr, close * _volatility_floor(spec))
    if close > channel_high:
        return (close - channel_high) / atr, atr / close
    if close < channel_low:
        return (close - channel_low) / atr, atr / close
    return 0.0, atr / close


def _metric_score(
    spec: StrategySpec,
    row: _PanelRow,
    history: list[_PanelRow],
    lookback: int,
) -> float | None:
    metric = spec.logic.rank_metric or "return"
    if metric == "funding":
        funding = _numeric(row.value("funding"))
        if funding is not None:
            return funding
        return _numeric(row.value("funding_rate"))
    if metric == "volume":
        return _numeric(row.value("volume"))
    if metric == "volatility":
        return _realized_volatility(row, history, lookback)
    prior = _prior_rows(row, history, lookback)
    if len(prior) < lookback:
        return None
    current_close = _numeric(row.value("close"))
    base_close = _numeric(prior[0].value("close"))
    if current_close is None or base_close is None or base_close <= 0:
        return None
    return (current_close / base_close) - 1.0


def _zscore(row: _PanelRow, history: list[_PanelRow], lookback: int) -> float | None:
    prior = _prior_rows(row, history, lookback)
    if len(prior) < lookback:
        return None
    values = [_numeric(item.value("close")) for item in prior]
    values = [value for value in values if value is not None]
    close = _numeric(row.value("close"))
    if len(values) < lookback or close is None:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (close - mean) / std


def _realized_volatility(row: _PanelRow, history: list[_PanelRow], lookback: int) -> float | None:
    prior = _prior_rows(row, history, lookback)
    if len(prior) < lookback:
        return None
    closes = [_numeric(item.value("close")) for item in [*prior, row]]
    closes = [value for value in closes if value is not None and value > 0]
    if len(closes) < 2:
        return None
    returns = [(closes[index] / closes[index - 1]) - 1.0 for index in range(1, len(closes))]
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / len(returns)
    return math.sqrt(variance)


def _average_true_range(row: _PanelRow, history: list[_PanelRow], lookback: int) -> float | None:
    prior = _prior_rows(row, history, lookback)
    if len(prior) < lookback:
        return None
    ordered = [*prior, row]
    ranges: list[float] = []
    for index in range(1, len(ordered)):
        current = ordered[index]
        previous = ordered[index - 1]
        high = _numeric(current.value("high")) or _numeric(current.value("close"))
        low = _numeric(current.value("low")) or _numeric(current.value("close"))
        previous_close = _numeric(previous.value("close"))
        if high is None or low is None or previous_close is None:
            continue
        ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    if not ranges:
        return None
    return sum(ranges) / len(ranges)


def _prior_rows(row: _PanelRow, history: list[_PanelRow], lookback: int) -> list[_PanelRow]:
    if row.history_index >= 0:
        start = max(0, row.history_index - lookback)
        return history[start:row.history_index]
    prior = [item for item in history if item.ts < row.ts]
    return prior[-lookback:]


def _filter_reason(spec: StrategySpec, row: _PanelRow) -> str | None:
    filters = spec.logic.filters
    if "min_coverage" in filters:
        coverage = _numeric(row.value("coverage_ratio"))
        if coverage is None or coverage < float(filters["min_coverage"]):
            return "filtered_min_coverage"
    if "max_funding_abs" in filters:
        funding = _numeric(row.value("funding"))
        if funding is None:
            funding = _numeric(row.value("funding_rate"))
        if funding is None or abs(funding) > float(filters["max_funding_abs"]):
            return "filtered_max_funding_abs"
    if "min_volume" in filters:
        volume = _numeric(row.value("volume"))
        if volume is None or volume < float(filters["min_volume"]):
            return "filtered_min_volume"
    if "min_open_interest" in filters:
        open_interest = _numeric(row.value("open_interest"))
        if open_interest is None or open_interest < float(filters["min_open_interest"]):
            return "filtered_min_open_interest"
    if "max_spread" in filters:
        spread = _numeric(row.value("spread"))
        if spread is None or spread > float(filters["max_spread"]):
            return "filtered_max_spread"
    return None


def _signal_row(
    spec: StrategySpec,
    row: _PanelRow,
    *,
    signal: float,
    weight: float,
    score: float | None,
    reason: str,
) -> SignalRow:
    side = "long" if signal > 0 else "short" if signal < 0 else "flat"
    return SignalRow(
        strategy_id=spec.strategy_id,
        spec_hash=spec.spec_hash,
        ts=row.ts,
        instrument_id=row.instrument_id,
        signal=signal,
        target_weight=weight,
        side=side,
        score=score,
        reason=reason,
    )


def _active_weight(spec: StrategySpec, active_count: int) -> float:
    if active_count <= 0:
        return 0.0
    return min(spec.risk.max_instrument_weight, spec.risk.max_gross_leverage / active_count)


def _vol_target_weight(
    spec: StrategySpec,
    *,
    realized_volatility: float,
    target_volatility: float,
) -> float:
    if realized_volatility <= 0.0 or target_volatility <= 0.0:
        return 0.0
    return min(spec.risk.max_instrument_weight, target_volatility / realized_volatility)


def _volatility_floor(spec: StrategySpec) -> float:
    return _parameter_float(spec, "volatility_floor", default=0.0001)


def _parameter_int(spec: StrategySpec, key: str, *, default: int) -> int:
    raw = spec.parameters.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, value)


def _parameter_float(spec: StrategySpec, key: str, *, default: float) -> float:
    raw = spec.parameters.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return max(0.0, value)


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, str):
        return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    raise ValueError(f"unsupported timestamp value: {value!r}")
