from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


EXIT_POLICY_ENGINE_VERSION = "research-exit-policy-v1"


@dataclass(frozen=True, slots=True)
class ExitPolicyResult:
    exit_time_ms: int
    exit_price: float
    exit_reason: str
    barrier_hit_type: str
    max_adverse_excursion: float
    max_favorable_excursion: float
    time_in_trade_ms: int
    costs_applied: bool
    exit_policy_id: str
    approximate: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def fixed_holding_window_exit(
    *,
    entry_time_ms: int,
    exit_time_ms: int,
    exit_price: float,
    side: str,
    path_high: float,
    path_low: float,
    entry_price: float,
    costs_applied: bool,
    exit_reason: str = "holding_window",
) -> ExitPolicyResult:
    adverse, favorable = _mae_mfe(
        side=side,
        entry_price=entry_price,
        path_high=path_high,
        path_low=path_low,
    )
    return ExitPolicyResult(
        exit_time_ms=int(exit_time_ms),
        exit_price=float(exit_price),
        exit_reason=exit_reason,
        barrier_hit_type="time",
        max_adverse_excursion=adverse,
        max_favorable_excursion=favorable,
        time_in_trade_ms=int(exit_time_ms) - int(entry_time_ms),
        costs_applied=bool(costs_applied),
        exit_policy_id="fixed_holding_window",
        approximate=False,
    )


def close_only_barrier_exit(
    *,
    entry_time_ms: int,
    exit_time_ms: int,
    entry_price: float,
    exit_price: float,
    side: str,
    target_return: float,
    stop_return: float,
    path_high: float,
    path_low: float,
    costs_applied: bool,
    exit_policy_id: str = "close_only_barrier_foundation",
) -> ExitPolicyResult:
    side_multiplier = 1.0 if side.lower() == "long" else -1.0
    realized = ((float(exit_price) / float(entry_price)) - 1.0) * side_multiplier
    if realized >= float(target_return):
        reason = "close_only_target"
        hit_type = "target"
    elif realized <= -abs(float(stop_return)):
        reason = "close_only_stop"
        hit_type = "stop"
    else:
        reason = "holding_window"
        hit_type = "time"
    adverse, favorable = _mae_mfe(
        side=side,
        entry_price=entry_price,
        path_high=path_high,
        path_low=path_low,
    )
    return ExitPolicyResult(
        exit_time_ms=int(exit_time_ms),
        exit_price=float(exit_price),
        exit_reason=reason,
        barrier_hit_type=hit_type,
        max_adverse_excursion=adverse,
        max_favorable_excursion=favorable,
        time_in_trade_ms=int(exit_time_ms) - int(entry_time_ms),
        costs_applied=bool(costs_applied),
        exit_policy_id=exit_policy_id,
        approximate=True,
    )


def triple_barrier_exit_from_lower_timeframe(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    time_exit_ms: int,
    time_exit_price: float,
    target_return: float,
    stop_return: float,
    lower_timeframe_market_data: pd.DataFrame,
    costs_applied: bool,
    exit_policy_id: str = "triple_barrier_atr",
    symbol: str | None = None,
) -> ExitPolicyResult:
    if target_return <= 0.0:
        raise ValueError("target_return must be positive for triple-barrier exits")
    if stop_return <= 0.0:
        raise ValueError("stop_return must be positive for triple-barrier exits")
    lower = _lower_timeframe_slice(
        lower_timeframe_market_data,
        entry_time_ms=int(entry_time_ms),
        time_exit_ms=int(time_exit_ms),
        symbol=symbol,
    )
    if lower.empty:
        raise ValueError("lower timeframe sequence coverage missing for trade exit window")

    side_value = side.lower()
    if side_value not in {"long", "short"}:
        raise ValueError("side must be long or short for triple-barrier exits")
    target_price = float(entry_price) * (1.0 + float(target_return)) if side_value == "long" else float(entry_price) * (1.0 - float(target_return))
    stop_price = float(entry_price) * (1.0 - abs(float(stop_return))) if side_value == "long" else float(entry_price) * (1.0 + abs(float(stop_return)))
    path_high = float(lower["high"].max())
    path_low = float(lower["low"].min())

    for _, row in lower.iterrows():
        high = float(row["high"])
        low = float(row["low"])
        if side_value == "long":
            target_hit = high >= target_price
            stop_hit = low <= stop_price
        else:
            target_hit = low <= target_price
            stop_hit = high >= stop_price

        if target_hit or stop_hit:
            hit_time = int(row["bar_time_ms"])
            if stop_hit:
                barrier = "ambiguous_stop_conservative" if target_hit else "stop"
                reason = "triple_barrier_ambiguous_stop_conservative" if target_hit else "triple_barrier_stop"
                exit_price = stop_price
                approximate = bool(target_hit)
            else:
                barrier = "target"
                reason = "triple_barrier_target"
                exit_price = target_price
                approximate = False
            adverse, favorable = _mae_mfe(
                side=side,
                entry_price=entry_price,
                path_high=float(lower.loc[lower["bar_time_ms"] <= hit_time, "high"].max()),
                path_low=float(lower.loc[lower["bar_time_ms"] <= hit_time, "low"].min()),
            )
            return ExitPolicyResult(
                exit_time_ms=hit_time,
                exit_price=float(exit_price),
                exit_reason=reason,
                barrier_hit_type=barrier,
                max_adverse_excursion=adverse,
                max_favorable_excursion=favorable,
                time_in_trade_ms=hit_time - int(entry_time_ms),
                costs_applied=bool(costs_applied),
                exit_policy_id=exit_policy_id,
                approximate=approximate,
            )

    adverse, favorable = _mae_mfe(
        side=side,
        entry_price=entry_price,
        path_high=path_high,
        path_low=path_low,
    )
    return ExitPolicyResult(
        exit_time_ms=int(time_exit_ms),
        exit_price=float(time_exit_price),
        exit_reason="holding_window",
        barrier_hit_type="time",
        max_adverse_excursion=adverse,
        max_favorable_excursion=favorable,
        time_in_trade_ms=int(time_exit_ms) - int(entry_time_ms),
        costs_applied=bool(costs_applied),
        exit_policy_id=exit_policy_id,
        approximate=False,
    )


def primary_bar_research_exit(
    *,
    entry_time_ms: int,
    time_exit_ms: int,
    time_exit_price: float,
    entry_price: float,
    side: str,
    primary_path: pd.DataFrame,
    costs_applied: bool,
    exit_policy_id: str,
    target_return: float | None = None,
    stop_return: float | None = None,
    policy_params: dict[str, Any] | None = None,
    exit_reason: str = "holding_window",
) -> ExitPolicyResult:
    policy = str(exit_policy_id).lower()
    params = dict(policy_params or {})
    path = _primary_exit_path(primary_path, entry_time_ms=entry_time_ms, time_exit_ms=time_exit_ms)
    if path.empty:
        raise ValueError("primary-bar sequence coverage missing for research exit policy")
    if policy == "volatility_scaled_barrier":
        return _primary_close_barrier_exit(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            target_return=_positive_return(_param_float(params, "target_return", target_return), "target_return", policy),
            stop_return=_positive_return(_param_float(params, "stop_return", stop_return), "stop_return", policy),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "regime_flip_exit":
        return _regime_flip_exit(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "funding_adverse_exit":
        return _funding_adverse_exit(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            threshold=_optional_positive_return(_param_float(params, "funding_threshold", target_return), default=0.00005),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "alpha_decay_exit":
        return _alpha_decay_exit(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            threshold=float(_param_float(params, "alpha_threshold", target_return) or 0.0),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "adverse_selection_exit":
        return _adverse_selection_exit(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            spread_threshold_bps=float(_param_float(params, "spread_threshold_bps", target_return) or 20.0),
            imbalance_threshold=float(_param_float(params, "imbalance_threshold", stop_return) or 0.1),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "trailing_atr_after_profit":
        return _trailing_after_profit_exit(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            activation_return=_optional_positive_return(_param_float(params, "activation_return", target_return), default=0.01),
            trail_return=_trail_return(path, _param_float(params, "trail_return", stop_return)),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "max_mae_stop":
        return _max_mae_stop_exit(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            stop_return=_positive_return(_param_float(params, "stop_return", stop_return), "stop_return", policy),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    raise ValueError(f"unsupported research exit policy: {exit_policy_id}")


def _primary_close_barrier_exit(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    target_return: float,
    stop_return: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    side_multiplier = _side_multiplier(side)
    for _, row in path.iloc[1:].iterrows():
        realized = ((float(row["close"]) / float(entry_price)) - 1.0) * side_multiplier
        if realized >= target_return:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason=f"{exit_policy_id}_target",
                barrier_hit_type="target",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=True,
            )
        if realized <= -stop_return:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason=f"{exit_policy_id}_stop",
                barrier_hit_type="stop",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=True,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _regime_flip_exit(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    regime_column = _first_present_column(path, ("top_regime_label", "regime"))
    if regime_column is None:
        raise ValueError("regime_flip_exit requires top_regime_label or regime")
    entry_regime = _string_value(path.iloc[0].get(regime_column))
    if not entry_regime:
        raise ValueError("regime_flip_exit requires non-empty entry regime")
    for _, row in path.iloc[1:].iterrows():
        regime = _string_value(row.get(regime_column))
        if regime and regime != entry_regime:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="regime_flip_exit",
                barrier_hit_type="regime_flip",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _funding_adverse_exit(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    threshold: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    _require_columns(path, ("funding_rate",), exit_policy_id)
    side_value = side.lower()
    for _, row in path.iloc[1:].iterrows():
        funding = float(row["funding_rate"])
        adverse = funding >= threshold if side_value == "long" else funding <= -threshold
        if adverse:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="funding_adverse_exit",
                barrier_hit_type="funding_adverse",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _alpha_decay_exit(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    threshold: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    _require_columns(path, ("directional_slope_atr",), exit_policy_id)
    side_value = side.lower()
    for _, row in path.iloc[1:].iterrows():
        slope = float(row["directional_slope_atr"])
        decayed = slope <= threshold if side_value == "long" else slope >= -threshold
        if decayed:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="alpha_decay_exit",
                barrier_hit_type="alpha_decay",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _adverse_selection_exit(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    spread_threshold_bps: float,
    imbalance_threshold: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    imbalance_column = _first_present_column(path, ("primary_signed_imbalance_ratio", "top_of_book_imbalance"))
    if imbalance_column is None:
        raise ValueError("adverse_selection_exit requires primary_signed_imbalance_ratio or top_of_book_imbalance")
    _require_columns(path, ("spread_bps",), exit_policy_id)
    side_value = side.lower()
    for _, row in path.iloc[1:].iterrows():
        spread = float(row["spread_bps"])
        imbalance = float(row[imbalance_column])
        adverse_imbalance = imbalance <= -imbalance_threshold if side_value == "long" else imbalance >= imbalance_threshold
        if spread >= spread_threshold_bps and adverse_imbalance:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="adverse_selection_exit",
                barrier_hit_type="adverse_selection",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _trailing_after_profit_exit(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    activation_return: float,
    trail_return: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    side_multiplier = _side_multiplier(side)
    best = 0.0
    active = False
    for _, row in path.iloc[1:].iterrows():
        realized = ((float(row["close"]) / float(entry_price)) - 1.0) * side_multiplier
        best = max(best, realized)
        active = active or best >= activation_return
        if active and realized <= best - trail_return:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="trailing_atr_after_profit",
                barrier_hit_type="trailing_stop",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=True,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _max_mae_stop_exit(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    stop_return: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    side_value = side.lower()
    stop_price = float(entry_price) * (1.0 - stop_return) if side_value == "long" else float(entry_price) * (1.0 + stop_return)
    for _, row in path.iloc[1:].iterrows():
        hit = float(row["low"]) <= stop_price if side_value == "long" else float(row["high"]) >= stop_price
        if hit:
            adverse, favorable = _mae_mfe(
                side=side,
                entry_price=entry_price,
                path_high=float(path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"]), "high"].max()),
                path_low=float(path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"]), "low"].min()),
            )
            return ExitPolicyResult(
                exit_time_ms=int(row["bar_time_ms"]),
                exit_price=float(stop_price),
                exit_reason="max_mae_stop",
                barrier_hit_type="stop",
                max_adverse_excursion=adverse,
                max_favorable_excursion=favorable,
                time_in_trade_ms=int(row["bar_time_ms"]) - int(entry_time_ms),
                costs_applied=bool(costs_applied),
                exit_policy_id=exit_policy_id,
                approximate=True,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _primary_exit_path(path: pd.DataFrame, *, entry_time_ms: int, time_exit_ms: int) -> pd.DataFrame:
    required = {"bar_time_ms", "high", "low", "close"}
    missing = sorted(required - set(path.columns))
    if missing:
        raise ValueError(f"primary-bar exit path missing required columns: {', '.join(missing)}")
    frame = path.copy()
    frame["bar_time_ms"] = pd.to_numeric(frame["bar_time_ms"], errors="coerce").astype("int64")
    for column in ("high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.loc[
        (frame["bar_time_ms"] >= int(entry_time_ms))
        & (frame["bar_time_ms"] <= int(time_exit_ms))
    ].sort_values("bar_time_ms", kind="mergesort").dropna(subset=["high", "low", "close"])


def _result_from_row(
    row: pd.Series,
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    exit_reason: str,
    barrier_hit_type: str,
    costs_applied: bool,
    exit_policy_id: str,
    approximate: bool,
) -> ExitPolicyResult:
    adverse, favorable = _mae_mfe(
        side=side,
        entry_price=entry_price,
        path_high=float(path["high"].max()),
        path_low=float(path["low"].min()),
    )
    return ExitPolicyResult(
        exit_time_ms=int(row["bar_time_ms"]),
        exit_price=float(row["close"]),
        exit_reason=exit_reason,
        barrier_hit_type=barrier_hit_type,
        max_adverse_excursion=adverse,
        max_favorable_excursion=favorable,
        time_in_trade_ms=int(row["bar_time_ms"]) - int(entry_time_ms),
        costs_applied=bool(costs_applied),
        exit_policy_id=exit_policy_id,
        approximate=bool(approximate),
    )


def _time_result(
    row: pd.Series,
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    return _result_from_row(
        row,
        entry_time_ms=entry_time_ms,
        entry_price=entry_price,
        side=side,
        path=path,
        exit_reason=exit_reason,
        barrier_hit_type="time",
        costs_applied=costs_applied,
        exit_policy_id=exit_policy_id,
        approximate=False,
    )


def _positive_return(value: float | None, field: str, policy: str) -> float:
    if value is None or value <= 0.0:
        raise ValueError(f"{policy} requires positive {field}")
    return float(value)


def _optional_positive_return(value: float | None, *, default: float) -> float:
    if value is None:
        return float(default)
    if value <= 0.0:
        raise ValueError("exit threshold must be positive")
    return float(value)


def _trail_return(path: pd.DataFrame, value: float | None) -> float:
    if value is not None:
        return _optional_positive_return(value, default=0.005)
    volatility_column = _first_present_column(path, ("realized_volatility", "atr_percentile"))
    if volatility_column is None:
        raise ValueError("trailing_atr_after_profit requires realized_volatility or atr_percentile when stop_return is omitted")
    volatility = pd.to_numeric(path[volatility_column], errors="coerce").dropna()
    if volatility.empty:
        raise ValueError("trailing_atr_after_profit requires finite volatility context")
    return float(max(0.002, min(0.05, float(volatility.iloc[0]))))


def _param_float(params: dict[str, Any], key: str, fallback: float | None) -> float | None:
    if key not in params or params[key] is None:
        return fallback
    return float(params[key])


def _first_present_column(frame: pd.DataFrame, columns: tuple[str, ...]) -> str | None:
    for column in columns:
        if column in frame.columns:
            return column
    return None


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], policy: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{policy} requires columns: {', '.join(missing)}")


def _string_value(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _side_multiplier(side: str) -> float:
    side_value = side.lower()
    if side_value not in {"long", "short"}:
        raise ValueError("side must be long or short for research exit policies")
    return 1.0 if side_value == "long" else -1.0


def _lower_timeframe_slice(
    frame: pd.DataFrame,
    *,
    entry_time_ms: int,
    time_exit_ms: int,
    symbol: str | None,
) -> pd.DataFrame:
    required = {"bar_time_ms", "high", "low", "close"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"lower timeframe market data missing required columns: {', '.join(missing)}")
    lower = frame.copy()
    if "symbol" in lower.columns:
        if not str(symbol or "").strip():
            raise ValueError("lower timeframe market data with symbol column requires symbol")
        lower = lower.loc[lower["symbol"].astype(str).str.upper() == str(symbol).upper()].copy()
    lower["bar_time_ms"] = pd.to_numeric(lower["bar_time_ms"], errors="coerce").astype("int64")
    for column in ("high", "low", "close"):
        lower[column] = pd.to_numeric(lower[column], errors="coerce")
    lower = lower.loc[
        (lower["bar_time_ms"] > int(entry_time_ms))
        & (lower["bar_time_ms"] <= int(time_exit_ms))
    ].copy()
    return lower.sort_values("bar_time_ms", kind="mergesort").dropna(subset=["high", "low", "close"])


def _mae_mfe(*, side: str, entry_price: float, path_high: float, path_low: float) -> tuple[float, float]:
    if entry_price <= 0:
        return 0.0, 0.0
    high_return = (float(path_high) / float(entry_price)) - 1.0
    low_return = (float(path_low) / float(entry_price)) - 1.0
    if side.lower() == "short":
        favorable = max(0.0, -low_return)
        adverse = max(0.0, high_return)
    else:
        favorable = max(0.0, high_return)
        adverse = max(0.0, -low_return)
    return float(adverse), float(favorable)
