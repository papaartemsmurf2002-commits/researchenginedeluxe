from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from tradingbotsuite.research_sandbox.boundary import sandbox_boundary_metadata
from tradingbotsuite.research_sandbox.identity import deterministic_trial_id
from tradingbotsuite.research_sandbox.spec import (
    ALLOWED_EXIT_PROFILES,
    ExitVariant,
    FilterVariant,
    SandboxRunSpec,
    StrategyCatalogRow,
    VenueArchiveDescriptor,
)
from tradingbotsuite.research_sandbox.strategy_blueprints import (
    BLUEPRINT_PARAM_KEY,
    blueprint_signal_cache_key,
    materialize_strategy_signals,
    resolve_materialized_signal_column,
)


_BARRIER_EXIT_ENTRY_BATCH_SIZE = 8192


@dataclass(frozen=True)
class FixedHoldSweepConfig:
    holding_periods: tuple[int, ...]
    round_trip_cost_bps: float
    min_trades: int


@dataclass(frozen=True)
class _PreparedMarketArrays:
    close: np.ndarray
    high: np.ndarray | None
    low: np.ndarray | None
    entry_dates: np.ndarray


@dataclass(frozen=True)
class TrialResult:
    trial_id: str
    run_id: str
    hypothesis_id: str
    family: str
    source_id: str
    venue: str
    symbol: str
    data_family: str
    signal_column: str
    side: str
    holding_period: int
    exit_profile: str
    exit_variant_id: str
    filter_variant_id: str
    trade_count: int
    active_days: int
    gross_return_sum: float
    net_return_sum: float
    avg_trade_return: float
    win_rate: float
    max_drawdown: float
    score: float
    rank: int | None = None
    status: str = "blocked"
    rejection_reasons: tuple[str, ...] = ()
    market_start: str | None = None
    market_end: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_rank(self, rank: int) -> "TrialResult":
        return TrialResult(**{**self.__dict__, "rank": rank})

    def to_payload(self) -> dict[str, Any]:
        return {
            **sandbox_boundary_metadata(),
            "trial_id": self.trial_id,
            "run_id": self.run_id,
            "hypothesis_id": self.hypothesis_id,
            "family": self.family,
            "source_id": self.source_id,
            "venue": self.venue,
            "symbol": self.symbol,
            "data_family": self.data_family,
            "signal_column": self.signal_column,
            "side": self.side,
            "holding_period": self.holding_period,
            "exit_profile": self.exit_profile,
            "exit_variant_id": self.exit_variant_id,
            "filter_variant_id": self.filter_variant_id,
            "trade_count": self.trade_count,
            "active_days": self.active_days,
            "gross_return_sum": self.gross_return_sum,
            "net_return_sum": self.net_return_sum,
            "avg_trade_return": self.avg_trade_return,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "score": self.score,
            "rank": self.rank,
            "status": self.status,
            "rejection_reasons": list(self.rejection_reasons),
            "market_start": self.market_start,
            "market_end": self.market_end,
            "metadata": self.metadata,
        }


def _effective_window_bounds(
    spec: SandboxRunSpec,
    venue: VenueArchiveDescriptor | None = None,
) -> tuple[pd.Timestamp, pd.Timestamp, bool]:
    start_date = spec.data_window.start
    end_date = spec.data_window.end
    if venue is not None:
        start_date = max(start_date, venue.window.start)
        end_date = min(end_date, venue.window.end)
    start = pd.Timestamp(start_date, tz="UTC")
    end_exclusive = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    return start, end_exclusive, end_date >= start_date


def _effective_window_key(
    *,
    spec: SandboxRunSpec,
    venue: VenueArchiveDescriptor,
) -> tuple[str, str]:
    start, end_exclusive, has_overlap = _effective_window_bounds(spec, venue)
    if not has_overlap:
        return ("no_overlap", "no_overlap")
    return (start.date().isoformat(), (end_exclusive - pd.Timedelta(days=1)).date().isoformat())


def _market_window(
    frame: pd.DataFrame,
    spec: SandboxRunSpec,
    venue: VenueArchiveDescriptor | None = None,
) -> pd.DataFrame:
    if "timestamp" not in frame.columns:
        raise ValueError("sandbox market_frame requires a timestamp column")
    if "close" not in frame.columns:
        raise ValueError("sandbox market_frame requires a close column")
    market = frame.copy()
    market["timestamp"] = pd.to_datetime(market["timestamp"], utc=True)
    start, end_exclusive, has_overlap = _effective_window_bounds(spec, venue)
    if not has_overlap:
        return market.iloc[0:0].copy().reset_index(drop=True)
    market = market[(market["timestamp"] >= start) & (market["timestamp"] < end_exclusive)]
    market = market.sort_values("timestamp").reset_index(drop=True)
    close = pd.to_numeric(market["close"], errors="coerce")
    market = market[np.isfinite(close.to_numpy(dtype=float))].reset_index(drop=True)
    market["close"] = pd.to_numeric(market["close"], errors="coerce").astype(float)
    return market


def _prepared_market_arrays(market: pd.DataFrame, *, include_ohlc: bool) -> _PreparedMarketArrays:
    timestamps = pd.to_datetime(market["timestamp"], utc=True)
    return _PreparedMarketArrays(
        close=market["close"].to_numpy(dtype=float, copy=False),
        high=(
            pd.to_numeric(market["high"], errors="coerce").to_numpy(dtype=float)
            if include_ohlc and "high" in market.columns
            else None
        ),
        low=(
            pd.to_numeric(market["low"], errors="coerce").to_numpy(dtype=float)
            if include_ohlc and "low" in market.columns
            else None
        ),
        entry_dates=timestamps.dt.date.to_numpy(),
    )


def _blocked_result(
    *,
    run_spec: SandboxRunSpec,
    strategy: StrategyCatalogRow,
    venue: VenueArchiveDescriptor,
    holding_period: int,
    exit_variant: ExitVariant,
    filter_variant: FilterVariant,
    reasons: list[str],
    metadata: dict[str, Any] | None = None,
) -> TrialResult:
    metadata_payload = _result_metadata(
        run_spec=run_spec,
        strategy=strategy,
        exit_variant=exit_variant,
        filter_variant=filter_variant,
    )
    if metadata:
        metadata_payload.update(metadata)
    return TrialResult(
        trial_id=deterministic_trial_id(
            run_spec=run_spec,
            strategy=strategy,
            venue=venue,
            holding_period=holding_period,
            extra={"exit_variant": exit_variant.to_payload(), "filter_variant": filter_variant.to_payload()},
        ),
        run_id=run_spec.run_id,
        hypothesis_id=strategy.hypothesis_id,
        family=strategy.family,
        source_id=strategy.source_id,
        venue=venue.venue,
        symbol=venue.symbol,
        data_family=venue.data_family,
        signal_column=strategy.signal_column,
        side=strategy.side,
        holding_period=holding_period,
        exit_profile=exit_variant.exit_profile,
        exit_variant_id=exit_variant.variant_id,
        filter_variant_id=filter_variant.variant_id,
        trade_count=0,
        active_days=0,
        gross_return_sum=0.0,
        net_return_sum=0.0,
        avg_trade_return=0.0,
        win_rate=0.0,
        max_drawdown=0.0,
        score=-1.0,
        status="blocked",
        rejection_reasons=tuple(reasons),
        metadata=metadata_payload,
    )


def _result_metadata(
    *,
    run_spec: SandboxRunSpec,
    strategy: StrategyCatalogRow,
    exit_variant: ExitVariant,
    filter_variant: FilterVariant,
    market_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata_payload = {
        "entry_price_source": "next_bar_close",
        "exit_price_source": "fixed_hold_close" if exit_variant.exit_profile == "fixed_hold" else "primary_bar_ohlc_proxy",
        "same_bar_entry_exit_allowed": False,
        "round_trip_cost_bps": run_spec.round_trip_cost_bps,
        "exit_profile": exit_variant.exit_profile,
        "exit_variant_id": exit_variant.variant_id,
        "filter_variant_id": filter_variant.variant_id,
        "target_return": exit_variant.target_return,
        "stop_return": exit_variant.stop_return,
    }
    if exit_variant.exit_profile == "target_stop_conservative":
        metadata_payload["same_bar_target_stop_policy"] = "stop_first"
    if filter_variant.filter_column:
        metadata_payload["filter_variant"] = filter_variant.to_payload()
    if market_source:
        metadata_payload["market_source"] = market_source
    if strategy.params.get(BLUEPRINT_PARAM_KEY):
        metadata_payload["sandbox_blueprint_id"] = strategy.params[BLUEPRINT_PARAM_KEY]
        metadata_payload["sandbox_proxy_signal"] = bool(strategy.params.get("sandbox_proxy_signal", False))
        metadata_payload["sandbox_proxy_only"] = bool(strategy.params.get("sandbox_proxy_only", True))
        metadata_payload["strict_cycle_strategy_execution"] = False
        metadata_payload["candidate_evidence_from_proxy_allowed"] = False
        metadata_payload["proxy_strategy_policy"] = strategy.params.get(
            "proxy_strategy_policy",
            "proxy_only_diagnostic_not_strict_strategy_evidence",
        )
    return metadata_payload


def _strategy_exit_profile(strategy: StrategyCatalogRow) -> str:
    return str(strategy.exit_profile or "fixed_hold").strip().lower()


def _strategy_exit_variants(
    run_spec: SandboxRunSpec,
    strategy: StrategyCatalogRow,
) -> tuple[tuple[ExitVariant, ...], tuple[str, ...]]:
    profile = _strategy_exit_profile(strategy)
    if profile == "fixed_hold":
        return tuple(run_spec.exit_variants), ()
    if profile not in ALLOWED_EXIT_PROFILES:
        return (), (f"unsupported_strategy_exit_profile:{profile}",)
    matching = tuple(variant for variant in run_spec.exit_variants if variant.exit_profile == profile)
    if not matching:
        return (), (f"strategy_exit_profile_not_in_run_spec:{profile}",)
    return matching, ()


def _apply_filter(mask: np.ndarray, market: pd.DataFrame, *, column: str, minimum: float | None, maximum: float | None) -> np.ndarray:
    filt = pd.to_numeric(market[column], errors="coerce").to_numpy(dtype=float)
    finite = np.isfinite(filt)
    if minimum is not None:
        finite &= filt >= minimum
    if maximum is not None:
        finite &= filt <= maximum
    return mask & finite


def _signal_mask(market: pd.DataFrame, strategy: StrategyCatalogRow, filter_variant: FilterVariant) -> np.ndarray:
    signal_column = resolve_materialized_signal_column(market, strategy.signal_column)
    signal = pd.to_numeric(market[signal_column], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    mask = signal > 0.0
    if strategy.filter_column:
        mask = _apply_filter(
            mask,
            market,
            column=strategy.filter_column,
            minimum=strategy.filter_min,
            maximum=strategy.filter_max,
        )
    if filter_variant.filter_column:
        mask = _apply_filter(
            mask,
            market,
            column=filter_variant.filter_column,
            minimum=filter_variant.filter_min,
            maximum=filter_variant.filter_max,
        )
    return mask


def _signal_mask_cache_key(strategy: StrategyCatalogRow, filter_variant: FilterVariant) -> tuple[Any, ...]:
    signal_key = blueprint_signal_cache_key(strategy) or ("signal_column", strategy.signal_column)
    return (
        signal_key,
        strategy.filter_column,
        strategy.filter_min,
        strategy.filter_max,
        filter_variant.filter_column,
        filter_variant.filter_min,
        filter_variant.filter_max,
    )


def _signal_mask_inputs_available(market: pd.DataFrame, strategy: StrategyCatalogRow, filter_variant: FilterVariant) -> bool:
    if market.empty:
        return False
    signal_column = resolve_materialized_signal_column(market, strategy.signal_column)
    if signal_column not in market.columns:
        return False
    if strategy.filter_column and strategy.filter_column not in market.columns:
        return False
    if filter_variant.filter_column and filter_variant.filter_column not in market.columns:
        return False
    return True


def _cached_signal_mask(
    *,
    market: pd.DataFrame,
    strategy: StrategyCatalogRow,
    filter_variant: FilterVariant,
    mask_cache: dict[tuple[Any, ...], np.ndarray | None],
) -> np.ndarray | None:
    key = _signal_mask_cache_key(strategy, filter_variant)
    if key not in mask_cache:
        mask_cache[key] = (
            _signal_mask(market, strategy, filter_variant)
            if _signal_mask_inputs_available(market, strategy, filter_variant)
            else None
        )
    return mask_cache[key]


def _trial_metric_cache_key(
    *,
    strategy: StrategyCatalogRow,
    filter_variant: FilterVariant,
    exit_variant: ExitVariant,
    holding_period: int,
) -> tuple[int, int, int, int]:
    return (id(strategy), id(filter_variant), id(exit_variant), int(holding_period))


def _copy_result_for_venue(
    template: TrialResult,
    *,
    run_spec: SandboxRunSpec,
    strategy: StrategyCatalogRow,
    venue: VenueArchiveDescriptor,
    holding_period: int,
    exit_variant: ExitVariant,
    filter_variant: FilterVariant,
    market_source: dict[str, Any] | None,
) -> TrialResult:
    return TrialResult(
        trial_id=deterministic_trial_id(
            run_spec=run_spec,
            strategy=strategy,
            venue=venue,
            holding_period=holding_period,
            extra={"exit_variant": exit_variant.to_payload(), "filter_variant": filter_variant.to_payload()},
        ),
        run_id=run_spec.run_id,
        hypothesis_id=strategy.hypothesis_id,
        family=strategy.family,
        source_id=strategy.source_id,
        venue=venue.venue,
        symbol=venue.symbol,
        data_family=venue.data_family,
        signal_column=strategy.signal_column,
        side=strategy.side,
        holding_period=holding_period,
        exit_profile=exit_variant.exit_profile,
        exit_variant_id=exit_variant.variant_id,
        filter_variant_id=filter_variant.variant_id,
        trade_count=template.trade_count,
        active_days=template.active_days,
        gross_return_sum=template.gross_return_sum,
        net_return_sum=template.net_return_sum,
        avg_trade_return=template.avg_trade_return,
        win_rate=template.win_rate,
        max_drawdown=template.max_drawdown,
        score=template.score,
        status=template.status,
        rejection_reasons=template.rejection_reasons,
        market_start=template.market_start,
        market_end=template.market_end,
        metadata=_result_metadata(
            run_spec=run_spec,
            strategy=strategy,
            exit_variant=exit_variant,
            filter_variant=filter_variant,
            market_source=market_source,
        ),
    )


def _source_payload_for_venue(
    venue: VenueArchiveDescriptor,
    *,
    market_sources: Mapping[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if market_sources is not None and venue.descriptor_id in market_sources:
        return dict(market_sources[venue.descriptor_id])
    return {
        "routing_mode": "descriptor_data_path",
        "descriptor_id": venue.descriptor_id,
        "venue": venue.venue,
        "symbol": venue.symbol,
        "data_family": venue.data_family,
        "data_path": str(venue.data_path) if venue.data_path is not None else None,
    }


def _normalized_source_path(value: Any) -> str:
    return str(Path(str(value)).expanduser().resolve())


def _market_reuse_key(
    *,
    venue: VenueArchiveDescriptor,
    market_frame: pd.DataFrame,
    market_source: Mapping[str, Any],
    run_spec: SandboxRunSpec,
) -> tuple[str, str, str, str]:
    effective_window = _effective_window_key(spec=run_spec, venue=venue)
    shared_path = market_source.get("shared_market_data_path")
    if shared_path not in (None, ""):
        return ("shared_market_data_path", _normalized_source_path(shared_path), *effective_window)
    data_path = market_source.get("data_path")
    if data_path not in (None, ""):
        return ("data_path", _normalized_source_path(data_path), *effective_window)
    return ("frame_object", str(id(market_frame)), *effective_window)


def _drawdown(returns: np.ndarray) -> float:
    if returns.size == 0:
        return 0.0
    cumulative = np.cumsum(returns)
    peak = np.maximum.accumulate(cumulative)
    drawdown = cumulative - peak
    return float(abs(np.min(drawdown)))


def _run_one(
    *,
    market: pd.DataFrame,
    market_arrays: _PreparedMarketArrays,
    run_spec: SandboxRunSpec,
    strategy: StrategyCatalogRow,
    venue: VenueArchiveDescriptor,
    holding_period: int,
    exit_variant: ExitVariant,
    filter_variant: FilterVariant,
    market_source: dict[str, Any] | None = None,
    signal_mask: np.ndarray | None = None,
) -> TrialResult:
    missing: list[str] = []
    signal_column = resolve_materialized_signal_column(market, strategy.signal_column)
    if signal_column not in market.columns:
        missing.append(f"missing_signal_column:{strategy.signal_column}")
    if strategy.filter_column and strategy.filter_column not in market.columns:
        missing.append(f"missing_filter_column:{strategy.filter_column}")
    if filter_variant.filter_column and filter_variant.filter_column not in market.columns:
        missing.append(f"missing_filter_column:{filter_variant.filter_column}")
    if exit_variant.exit_profile != "fixed_hold":
        for column in ("high", "low"):
            if column not in market.columns:
                missing.append(f"missing_ohlc_column:{column}")
    if market.empty:
        missing.append("no_market_rows_in_2024_plus_window")
    if missing:
        return _blocked_result(
            run_spec=run_spec,
            strategy=strategy,
            venue=venue,
            holding_period=holding_period,
            exit_variant=exit_variant,
            filter_variant=filter_variant,
            reasons=missing,
            metadata={"market_source": market_source} if market_source else None,
        )

    close = market_arrays.close
    mask = signal_mask if signal_mask is not None else _signal_mask(market, strategy, filter_variant)
    signal_idx = np.flatnonzero(mask)
    entry_idx = signal_idx + 1
    exit_idx = entry_idx + int(holding_period)
    valid = exit_idx < len(close)
    entry_idx = entry_idx[valid]
    exit_idx = exit_idx[valid]
    if entry_idx.size == 0:
        return _blocked_result(
            run_spec=run_spec,
            strategy=strategy,
            venue=venue,
            holding_period=holding_period,
            exit_variant=exit_variant,
            filter_variant=filter_variant,
            reasons=["no_complete_fixed_hold_trades"],
            metadata={"market_source": market_source} if market_source else None,
        )

    entry = close[entry_idx]
    gross = _gross_returns(
        market_arrays=market_arrays,
        entry_idx=entry_idx,
        exit_idx=exit_idx,
        entry=entry,
        side=strategy.side,
        exit_variant=exit_variant,
    )
    round_trip_cost = run_spec.round_trip_cost_bps / 10000.0
    net = gross - round_trip_cost

    trade_count = int(net.size)
    active_days = int(len(set(market_arrays.entry_dates[entry_idx])))
    gross_sum = float(np.sum(gross))
    net_sum = float(np.sum(net))
    avg_return = float(np.mean(net))
    win_rate = float(np.mean(net > 0.0))
    max_drawdown = _drawdown(net)
    score = float(net_sum + (0.01 * win_rate) - (0.10 * max_drawdown))

    reasons: list[str] = []
    if trade_count < run_spec.min_trades:
        reasons.append("min_trades_not_met")
    if net_sum <= 0.0:
        reasons.append("non_positive_net_return_after_costs")
    status = "screened" if not reasons else "rejected"

    return TrialResult(
        trial_id=deterministic_trial_id(
            run_spec=run_spec,
            strategy=strategy,
            venue=venue,
            holding_period=holding_period,
            extra={"exit_variant": exit_variant.to_payload(), "filter_variant": filter_variant.to_payload()},
        ),
        run_id=run_spec.run_id,
        hypothesis_id=strategy.hypothesis_id,
        family=strategy.family,
        source_id=strategy.source_id,
        venue=venue.venue,
        symbol=venue.symbol,
        data_family=venue.data_family,
        signal_column=strategy.signal_column,
        side=strategy.side,
        holding_period=holding_period,
        exit_profile=exit_variant.exit_profile,
        exit_variant_id=exit_variant.variant_id,
        filter_variant_id=filter_variant.variant_id,
        trade_count=trade_count,
        active_days=active_days,
        gross_return_sum=gross_sum,
        net_return_sum=net_sum,
        avg_trade_return=avg_return,
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        score=score,
        status=status,
        rejection_reasons=tuple(reasons),
        market_start=market["timestamp"].iloc[0].isoformat(),
        market_end=market["timestamp"].iloc[-1].isoformat(),
        metadata=_result_metadata(
            run_spec=run_spec,
            strategy=strategy,
            exit_variant=exit_variant,
            filter_variant=filter_variant,
            market_source=market_source,
        ),
    )


def _gross_returns(
    *,
    market_arrays: _PreparedMarketArrays,
    entry_idx: np.ndarray,
    exit_idx: np.ndarray,
    entry: np.ndarray,
    side: str,
    exit_variant: ExitVariant,
) -> np.ndarray:
    close = market_arrays.close
    if exit_variant.exit_profile == "fixed_hold":
        exit_price = close[exit_idx]
    else:
        high = market_arrays.high
        low = market_arrays.low
        if high is None or low is None:
            raise ValueError("sandbox target/stop exits require prepared high/low arrays")
        exit_price = _barrier_exit_prices(
            close=close,
            high=high,
            low=low,
            entry_idx=entry_idx,
            exit_idx=exit_idx,
            entry=entry,
            side=side,
            exit_variant=exit_variant,
        )
    if side == "short":
        return entry / exit_price - 1.0
    return exit_price / entry - 1.0


def _barrier_exit_prices(
    *,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    entry_idx: np.ndarray,
    exit_idx: np.ndarray,
    entry: np.ndarray,
    side: str,
    exit_variant: ExitVariant,
) -> np.ndarray:
    if entry_idx.size == 0:
        return close[exit_idx].copy()

    entry_idx_int = entry_idx.astype(int, copy=False)
    exit_idx_int = exit_idx.astype(int, copy=False)
    batch_size = max(1, int(_BARRIER_EXIT_ENTRY_BATCH_SIZE))
    if entry_idx_int.size <= batch_size:
        return _barrier_exit_prices_for_batch(
            close=close,
            high=high,
            low=low,
            entry_idx=entry_idx_int,
            exit_idx=exit_idx_int,
            entry=entry,
            side=side,
            exit_variant=exit_variant,
        )

    exit_price = close[exit_idx_int].copy()
    for batch_start in range(0, entry_idx_int.size, batch_size):
        batch_end = min(batch_start + batch_size, entry_idx_int.size)
        exit_price[batch_start:batch_end] = _barrier_exit_prices_for_batch(
            close=close,
            high=high,
            low=low,
            entry_idx=entry_idx_int[batch_start:batch_end],
            exit_idx=exit_idx_int[batch_start:batch_end],
            entry=entry[batch_start:batch_end],
            side=side,
            exit_variant=exit_variant,
        )
    return exit_price


def _barrier_exit_prices_for_batch(
    *,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    entry_idx: np.ndarray,
    exit_idx: np.ndarray,
    entry: np.ndarray,
    side: str,
    exit_variant: ExitVariant,
) -> np.ndarray:
    exit_price = close[exit_idx].copy()
    if entry_idx.size == 0:
        return exit_price

    holding_lengths = exit_idx - entry_idx
    max_holding = int(np.max(holding_lengths)) if holding_lengths.size else 0
    if max_holding <= 0:
        return exit_price

    offsets = np.arange(1, max_holding + 1, dtype=int)
    valid_window = offsets[None, :] <= holding_lengths[:, None]
    window_indices = entry_idx[:, None] + offsets[None, :]
    safe_window_indices = np.where(valid_window, window_indices, exit_idx[:, None])
    high_window = high[safe_window_indices]
    low_window = low[safe_window_indices]

    target_return = exit_variant.target_return
    stop_return = exit_variant.stop_return
    target_hits = np.zeros(valid_window.shape, dtype=bool)
    stop_hits = np.zeros(valid_window.shape, dtype=bool)
    target_price = np.zeros(entry.shape, dtype=float)
    stop_price = np.zeros(entry.shape, dtype=float)

    if side == "short":
        if target_return is not None:
            target_price = entry * (1.0 - target_return)
            target_hits = low_window <= target_price[:, None]
        if stop_return is not None:
            stop_price = entry * (1.0 + stop_return)
            stop_hits = high_window >= stop_price[:, None]
    else:
        if target_return is not None:
            target_price = entry * (1.0 + target_return)
            target_hits = high_window >= target_price[:, None]
        if stop_return is not None:
            stop_price = entry * (1.0 - stop_return)
            stop_hits = low_window <= stop_price[:, None]

    target_hits &= valid_window
    stop_hits &= valid_window
    target_hit_any = np.any(target_hits, axis=1)
    stop_hit_any = np.any(stop_hits, axis=1)
    first_target = np.argmax(target_hits, axis=1)
    first_stop = np.argmax(stop_hits, axis=1)

    if exit_variant.exit_profile == "target_only":
        exit_price[target_hit_any] = target_price[target_hit_any]
    elif exit_variant.exit_profile == "stop_only":
        exit_price[stop_hit_any] = stop_price[stop_hit_any]
    elif exit_variant.exit_profile == "target_stop_conservative":
        no_hit_offset = max_holding + 1
        target_offset = np.where(target_hit_any, first_target, no_hit_offset)
        stop_offset = np.where(stop_hit_any, first_stop, no_hit_offset)
        stop_selected = stop_hit_any & (stop_offset <= target_offset)
        target_selected = target_hit_any & (target_offset < stop_offset)
        exit_price[stop_selected] = stop_price[stop_selected]
        exit_price[target_selected] = target_price[target_selected]
    return exit_price


def rank_results(results: list[TrialResult], *, top_n: int | None = None) -> list[TrialResult]:
    ordered = sorted(results, key=lambda item: (item.score, item.net_return_sum, item.trade_count), reverse=True)
    if top_n is not None:
        ordered = ordered[:top_n]
    return [item.with_rank(index + 1) for index, item in enumerate(ordered)]


def run_fixed_hold_sweep(
    *,
    market_frame: pd.DataFrame,
    run_spec: SandboxRunSpec,
    strategies: list[StrategyCatalogRow],
    venues: list[VenueArchiveDescriptor],
) -> list[TrialResult]:
    results: list[TrialResult] = []
    grouped_venues: dict[tuple[str, str], list[VenueArchiveDescriptor]] = {}
    for venue in venues:
        grouped_venues.setdefault(_effective_window_key(spec=run_spec, venue=venue), []).append(venue)
    for grouped in grouped_venues.values():
        first_venue = grouped[0]
        effective_window = _effective_window_key(spec=run_spec, venue=first_venue)
        market = materialize_strategy_signals(
            _market_window(market_frame, run_spec, first_venue),
            strategies,
            dedupe_blueprint_signals=True,
        )
        results.extend(
            _run_prepared_market_sweep(
                market=market,
                run_spec=run_spec,
                strategies=strategies,
                venues=grouped,
                market_source={
                    "routing_mode": "shared_market_frame",
                    "effective_window": {"start": effective_window[0], "end": effective_window[1]},
                },
                rank_top_n=None,
            )
        )
    return rank_results(results, top_n=run_spec.rank_top_n)


def _run_prepared_market_sweep(
    *,
    market: pd.DataFrame,
    run_spec: SandboxRunSpec,
    strategies: list[StrategyCatalogRow],
    venues: list[VenueArchiveDescriptor],
    market_source: dict[str, Any] | None,
    rank_top_n: int | None,
    market_sources_by_descriptor: Mapping[str, dict[str, Any]] | None = None,
) -> list[TrialResult]:
    results: list[TrialResult] = []
    signal_mask_cache: dict[tuple[Any, ...], np.ndarray | None] = {}
    trial_metric_cache: dict[tuple[int, int, int, int], TrialResult] = {}
    market_arrays = _prepared_market_arrays(
        market,
        include_ohlc=any(exit_variant.exit_profile != "fixed_hold" for exit_variant in run_spec.exit_variants),
    )
    for venue in venues:
        venue_market_source = (
            dict(market_sources_by_descriptor[venue.descriptor_id])
            if market_sources_by_descriptor is not None and venue.descriptor_id in market_sources_by_descriptor
            else market_source
        )
        for strategy in strategies:
            selected_exit_variants, strategy_exit_blockers = _strategy_exit_variants(run_spec, strategy)
            if strategy_exit_blockers:
                for filter_variant in run_spec.filter_variants:
                    for exit_variant in run_spec.exit_variants:
                        for holding_period in run_spec.holding_periods:
                            results.append(
                                _blocked_result(
                                    run_spec=run_spec,
                                    strategy=strategy,
                                    venue=venue,
                                    holding_period=holding_period,
                                    exit_variant=exit_variant,
                                    filter_variant=filter_variant,
                                    reasons=list(strategy_exit_blockers),
                                    metadata={"market_source": venue_market_source} if venue_market_source else None,
                                )
                            )
                continue
            for filter_variant in run_spec.filter_variants:
                signal_mask = _cached_signal_mask(
                    market=market,
                    strategy=strategy,
                    filter_variant=filter_variant,
                    mask_cache=signal_mask_cache,
                )
                for exit_variant in selected_exit_variants:
                    for holding_period in run_spec.holding_periods:
                        metric_key = _trial_metric_cache_key(
                            strategy=strategy,
                            filter_variant=filter_variant,
                            exit_variant=exit_variant,
                            holding_period=holding_period,
                        )
                        template = trial_metric_cache.get(metric_key)
                        if template is None:
                            result = _run_one(
                                market=market,
                                market_arrays=market_arrays,
                                run_spec=run_spec,
                                strategy=strategy,
                                venue=venue,
                                holding_period=holding_period,
                                exit_variant=exit_variant,
                                filter_variant=filter_variant,
                                market_source=venue_market_source,
                                signal_mask=signal_mask,
                            )
                            trial_metric_cache[metric_key] = result
                        else:
                            result = _copy_result_for_venue(
                                template,
                                run_spec=run_spec,
                                strategy=strategy,
                                venue=venue,
                                holding_period=holding_period,
                                exit_variant=exit_variant,
                                filter_variant=filter_variant,
                                market_source=venue_market_source,
                            )
                        results.append(result)
    return rank_results(results, top_n=rank_top_n)


def run_fixed_hold_sweep_for_venue_frames(
    *,
    market_frames: Mapping[str, pd.DataFrame],
    run_spec: SandboxRunSpec,
    strategies: list[StrategyCatalogRow],
    venues: list[VenueArchiveDescriptor],
    market_sources: Mapping[str, dict[str, Any]] | None = None,
    apply_rank_top_n: bool = True,
) -> list[TrialResult]:
    results: list[TrialResult] = []
    grouped_venues: dict[tuple[str, str], list[VenueArchiveDescriptor]] = {}
    source_payloads: dict[str, dict[str, Any]] = {}
    for venue in venues:
        if venue.descriptor_id not in market_frames:
            raise ValueError(f"missing market frame for venue descriptor: {venue.descriptor_id}")
        source_payload = _source_payload_for_venue(venue, market_sources=market_sources)
        effective_window = _effective_window_key(spec=run_spec, venue=venue)
        source_payload["effective_window"] = {"start": effective_window[0], "end": effective_window[1]}
        source_payloads[venue.descriptor_id] = source_payload
        reuse_key = _market_reuse_key(
            venue=venue,
            market_frame=market_frames[venue.descriptor_id],
            market_source=source_payload,
            run_spec=run_spec,
        )
        grouped_venues.setdefault(reuse_key, []).append(venue)

    for grouped in grouped_venues.values():
        first_venue = grouped[0]
        market = materialize_strategy_signals(
            _market_window(market_frames[first_venue.descriptor_id], run_spec, first_venue),
            strategies,
            dedupe_blueprint_signals=True,
        )
        results.extend(
            _run_prepared_market_sweep(
                market=market,
                run_spec=run_spec,
                strategies=strategies,
                venues=grouped,
                market_source=None,
                market_sources_by_descriptor={
                    venue.descriptor_id: source_payloads[venue.descriptor_id]
                    for venue in grouped
                },
                rank_top_n=None,
            )
        )
    return rank_results(results, top_n=run_spec.rank_top_n if apply_rank_top_n else None)
