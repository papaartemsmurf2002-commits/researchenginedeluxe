from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import pandas as pd


EXIT_POLICY_ENGINE_VERSION = "research-exit-policy-v1"
_KNN_EXIT_CONTEXT_COLUMNS = (
    "p_up_barrier",
    "p_down_barrier",
    "expected_net_return_after_costs",
    "neighbor_agreement",
    "neighbor_distance_quality",
    "neighbor_count",
    "neighbor_min_source_index",
    "neighbor_max_source_index",
    "knn_vote_margin",
    "accepted_by_knn",
    "knn_skip_reason",
    "hmm_fit_end_row",
    "source_row_index",
)
_GMM_DETECTOR_METADATA_COLUMNS = (
    "regime_detector_train_start_ms",
    "regime_detector_train_end_ms",
    "regime_detector_inference_start_ms",
    "regime_detector_inference_end_ms",
    "regime_detector_feature_version",
    "regime_detector_params_hash",
    "regime_detector_artifact_sha256",
)


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

    time_exit_row = lower.iloc[-1]
    actual_exit_time = int(time_exit_row["bar_time_ms"])
    if not _lower_timeframe_covers_horizon(lower, time_exit_ms=int(time_exit_ms)):
        raise ValueError("lower timeframe sequence coverage missing for scheduled exit horizon")
    adverse, favorable = _mae_mfe(
        side=side,
        entry_price=entry_price,
        path_high=path_high,
        path_low=path_low,
    )
    return ExitPolicyResult(
        exit_time_ms=actual_exit_time,
        exit_price=float(time_exit_row["close"]),
        exit_reason="holding_window",
        barrier_hit_type="time",
        max_adverse_excursion=adverse,
        max_favorable_excursion=favorable,
        time_in_trade_ms=actual_exit_time - int(entry_time_ms),
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
    if policy == "funding_aware_exit_v1":
        return _funding_aware_exit_v1(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            funding_threshold=_optional_positive_return(
                _param_float(params, "funding_threshold", None),
                default=0.00005,
            ),
            pre_funding_window_h=_optional_positive_return(
                _param_float(params, "pre_funding_window_h", None),
                default=1.0,
            ),
            min_expected_cost_bps=_optional_non_negative_float(
                _param_float(params, "min_expected_cost_bps", None),
                default=0.5,
                policy=policy,
                field="min_expected_cost_bps",
            ),
            edge_buffer_bps=_optional_non_negative_float(
                _param_float(params, "edge_buffer_bps", None),
                default=2.0,
                policy=policy,
                field="edge_buffer_bps",
            ),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "oi_contraction_exit_v1":
        return _oi_contraction_exit_v1(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            oi_delta_z_threshold=_optional_positive_return(
                _param_float(params, "oi_delta_z_threshold", None),
                default=1.0,
            ),
            min_oi_delta_abs=_optional_non_negative_float(
                _param_float(params, "min_oi_delta_abs", None),
                default=0.0,
                policy=policy,
                field="min_oi_delta_abs",
            ),
            max_unrealized_edge_bps=_optional_non_negative_float(
                _param_float(params, "max_unrealized_edge_bps", None),
                default=5.0,
                policy=policy,
                field="max_unrealized_edge_bps",
            ),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "basis_normalization_exit_v1":
        return _basis_normalization_exit_v1(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            normalization_threshold_bps=_optional_non_negative_float(
                _param_float(params, "normalization_threshold_bps", None),
                default=1.0,
                policy=policy,
                field="normalization_threshold_bps",
            ),
            min_entry_basis_abs_bps=_optional_non_negative_float(
                _param_float(params, "min_entry_basis_abs_bps", None),
                default=0.0,
                policy=policy,
                field="min_entry_basis_abs_bps",
            ),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "premium_normalization_exit_v1":
        return _premium_normalization_exit_v1(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            normalization_threshold_bps=_optional_non_negative_float(
                _param_float(params, "normalization_threshold_bps", None),
                default=1.0,
                policy=policy,
                field="normalization_threshold_bps",
            ),
            min_entry_premium_abs_bps=_optional_non_negative_float(
                _param_float(params, "min_entry_premium_abs_bps", None),
                default=0.0,
                policy=policy,
                field="min_entry_premium_abs_bps",
            ),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "gmm_transition_exit_v1":
        return _gmm_transition_exit_v1(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "knn_remaining_edge_exit_v1":
        return _knn_remaining_edge_exit_v1(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            min_remaining_edge_bps=_optional_non_negative_float(
                _param_float(params, "min_remaining_edge_bps", None),
                default=0.0,
                policy=policy,
                field="min_remaining_edge_bps",
            ),
            min_neighbor_count=_optional_positive_int(
                _param_float(params, "min_neighbor_count", None),
                default=1,
                policy=policy,
                field="min_neighbor_count",
            ),
            min_neighbor_agreement=_optional_unit_float(
                _param_float(params, "min_neighbor_agreement", None),
                default=0.0,
                policy=policy,
                field="min_neighbor_agreement",
            ),
            min_neighbor_distance_quality=_optional_unit_float(
                _param_float(params, "min_neighbor_distance_quality", None),
                default=0.0,
                policy=policy,
                field="min_neighbor_distance_quality",
            ),
            min_vote_margin=_optional_unit_float(
                _param_float(params, "min_vote_margin", None),
                default=0.0,
                policy=policy,
                field="min_vote_margin",
            ),
            costs_applied=costs_applied,
            exit_policy_id=policy,
            exit_reason=exit_reason,
        )
    if policy == "knn_dynamic_barriers_v1":
        return _knn_dynamic_barriers_v1(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            target_return=_optional_positive_return(
                _param_float(params, "target_return", target_return),
                default=0.01,
            ),
            stop_return=_optional_positive_return(
                _param_float(params, "stop_return", stop_return),
                default=0.01,
            ),
            min_target_return=_optional_positive_return(
                _param_float(params, "min_target_return", None),
                default=0.002,
            ),
            max_target_return=_optional_positive_return(
                _param_float(params, "max_target_return", None),
                default=0.05,
            ),
            min_stop_return=_optional_positive_return(
                _param_float(params, "min_stop_return", None),
                default=0.002,
            ),
            max_stop_return=_optional_positive_return(
                _param_float(params, "max_stop_return", None),
                default=0.05,
            ),
            target_edge_multiplier=_optional_non_negative_float(
                _param_float(params, "target_edge_multiplier", None),
                default=1.0,
                policy=policy,
                field="target_edge_multiplier",
            ),
            min_neighbor_count=_optional_positive_int(
                _param_float(params, "min_neighbor_count", None),
                default=1,
                policy=policy,
                field="min_neighbor_count",
            ),
            min_neighbor_agreement=_optional_unit_float(
                _param_float(params, "min_neighbor_agreement", None),
                default=0.0,
                policy=policy,
                field="min_neighbor_agreement",
            ),
            min_neighbor_distance_quality=_optional_unit_float(
                _param_float(params, "min_neighbor_distance_quality", None),
                default=0.0,
                policy=policy,
                field="min_neighbor_distance_quality",
            ),
            min_vote_margin=_optional_unit_float(
                _param_float(params, "min_vote_margin", None),
                default=0.0,
                policy=policy,
                field="min_vote_margin",
            ),
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
    if policy == "simple_runner_v1":
        return _simple_runner_exit(
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            side=side,
            path=path,
            activation_return=_optional_positive_return(
                _param_float(params, "activation_pct", target_return),
                default=0.01,
            ),
            runner_gap_return=_optional_positive_return(
                _param_float(params, "runner_gap_pct", stop_return),
                default=0.005,
            ),
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
    funding_rates = _funding_rate_series(path, exit_policy_id=exit_policy_id)
    side_value = side.lower()
    for index, row in path.iloc[1:].iterrows():
        funding = float(funding_rates.loc[index])
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


def _funding_aware_exit_v1(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    funding_threshold: float,
    pre_funding_window_h: float,
    min_expected_cost_bps: float,
    edge_buffer_bps: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    funding_rates = _funding_rate_series(path, exit_policy_id=exit_policy_id)
    time_to_next_h = _funding_time_to_next_hours(path, exit_policy_id=exit_policy_id)
    side_multiplier = _side_multiplier(side)
    side_value = side.lower()
    for index, row in path.iloc[1:].iterrows():
        funding = _optional_numeric(funding_rates.loc[index])
        hours_to_next = _optional_numeric(time_to_next_h.loc[index])
        close = _optional_numeric(row.get("close"))
        if funding is None or hours_to_next is None or close is None:
            continue
        if hours_to_next < 0.0 or hours_to_next > pre_funding_window_h:
            continue
        adverse = funding >= funding_threshold if side_value == "long" else funding <= -funding_threshold
        if not adverse:
            continue
        expected_cost_bps = abs(funding) * 10_000.0
        if expected_cost_bps < min_expected_cost_bps:
            continue
        unrealized_edge_bps = ((close / float(entry_price)) - 1.0) * side_multiplier * 10_000.0
        if unrealized_edge_bps <= expected_cost_bps + edge_buffer_bps:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="funding_aware_exit_v1",
                barrier_hit_type="funding_aware",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _oi_contraction_exit_v1(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    oi_delta_z_threshold: float,
    min_oi_delta_abs: float,
    max_unrealized_edge_bps: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    _require_columns(
        path,
        ("oi_notional", "oi_delta_1h", "oi_delta_z_7d", "quality_has_oi_gap"),
        exit_policy_id,
    )
    side_multiplier = _side_multiplier(side)
    for _, row in path.iloc[1:].iterrows():
        oi_notional = _optional_numeric(row.get("oi_notional"))
        oi_delta = _optional_numeric(row.get("oi_delta_1h"))
        oi_delta_z = _optional_numeric(row.get("oi_delta_z_7d"))
        oi_gap = _optional_numeric(row.get("quality_has_oi_gap"))
        close = _optional_numeric(row.get("close"))
        provider_backed = _optional_numeric(row.get("quality_provider_backed_all_required"))
        missing_context = (
            oi_notional is None
            or oi_delta is None
            or oi_delta_z is None
            or oi_gap is None
            or close is None
        )
        if missing_context:
            continue
        if oi_gap > 0.0:
            continue
        if "quality_provider_backed_all_required" in path.columns and (
            provider_backed is None or provider_backed <= 0.0
        ):
            continue
        if oi_delta > -min_oi_delta_abs:
            continue
        if oi_delta_z > -oi_delta_z_threshold:
            continue
        unrealized_edge_bps = ((close / float(entry_price)) - 1.0) * side_multiplier * 10_000.0
        if unrealized_edge_bps <= max_unrealized_edge_bps:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="oi_contraction_exit_v1",
                barrier_hit_type="oi_contraction",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _basis_normalization_exit_v1(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    normalization_threshold_bps: float,
    min_entry_basis_abs_bps: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    basis_bps = _basis_bps_series(path, exit_policy_id=exit_policy_id)
    side_multiplier = _side_multiplier(side)
    entry_basis = _optional_numeric(basis_bps.iloc[0])
    if entry_basis is None or not _premium_context_quality_allows(path.iloc[0], path):
        return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)
    entry_edge_bps = -side_multiplier * entry_basis
    if entry_edge_bps < min_entry_basis_abs_bps:
        return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)

    for index, row in path.iloc[1:].iterrows():
        if not _premium_context_quality_allows(row, path):
            continue
        current_basis = _optional_numeric(basis_bps.loc[index])
        if current_basis is None:
            continue
        remaining_edge_bps = -side_multiplier * current_basis
        if remaining_edge_bps <= normalization_threshold_bps:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="basis_normalization_exit_v1",
                barrier_hit_type="basis_normalization",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _premium_normalization_exit_v1(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    normalization_threshold_bps: float,
    min_entry_premium_abs_bps: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    premium_bps = _premium_bps_series(path, exit_policy_id=exit_policy_id)
    side_multiplier = _side_multiplier(side)
    entry_premium = _optional_numeric(premium_bps.iloc[0])
    if entry_premium is None or not _premium_context_quality_allows(path.iloc[0], path):
        return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)
    entry_edge_bps = -side_multiplier * entry_premium
    if entry_edge_bps < min_entry_premium_abs_bps:
        return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)

    for index, row in path.iloc[1:].iterrows():
        if not _premium_context_quality_allows(row, path):
            continue
        current_premium = _optional_numeric(premium_bps.loc[index])
        if current_premium is None:
            continue
        remaining_edge_bps = -side_multiplier * current_premium
        if remaining_edge_bps <= normalization_threshold_bps:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="premium_normalization_exit_v1",
                barrier_hit_type="premium_normalization",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _gmm_transition_exit_v1(
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
        raise ValueError("gmm_transition_exit_v1 requires top_regime_label or regime")
    _require_columns(path, ("hmm_fit_end_row", "source_row_index"), exit_policy_id)
    if not _gmm_detector_allows(path.iloc[0], path, required=True):
        raise ValueError("gmm_transition_exit_v1 requires gmm regime_detector_type")
    if not _gmm_detector_metadata_allows(path.iloc[0], path):
        raise ValueError("gmm_transition_exit_v1 requires GMM detector metadata")
    if not _split_safe_regime_row(path.iloc[0]):
        raise ValueError("gmm_transition_exit_v1 requires split-safe GMM regime context")
    entry_regime = _string_value(path.iloc[0].get(regime_column))
    if not entry_regime:
        raise ValueError("gmm_transition_exit_v1 requires non-empty entry GMM regime")

    for _, row in path.iloc[1:].iterrows():
        if not _gmm_detector_allows(row, path, required=False):
            continue
        if not _gmm_detector_metadata_allows(row, path):
            continue
        if not _split_safe_regime_row(row):
            continue
        regime = _string_value(row.get(regime_column))
        if not regime:
            continue
        recent_flip = _optional_bool_flag(row.get("recent_regime_flip")) if "recent_regime_flip" in path.columns else False
        regime_no_trade = _optional_bool_flag(row.get("regime_no_trade")) if "regime_no_trade" in path.columns else False
        if regime != entry_regime or recent_flip is True or regime_no_trade is True:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="gmm_transition_exit_v1",
                barrier_hit_type="gmm_regime_transition",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _knn_remaining_edge_exit_v1(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    min_remaining_edge_bps: float,
    min_neighbor_count: int,
    min_neighbor_agreement: float,
    min_neighbor_distance_quality: float,
    min_vote_margin: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    _require_columns(path, _KNN_EXIT_CONTEXT_COLUMNS, exit_policy_id)
    side_value = side.lower()
    for _, row in path.iloc[1:].iterrows():
        context = _knn_prediction_context(
            row,
            min_neighbor_count=min_neighbor_count,
            min_neighbor_agreement=min_neighbor_agreement,
            min_neighbor_distance_quality=min_neighbor_distance_quality,
            min_vote_margin=min_vote_margin,
            require_accepted=False,
        )
        if context is None:
            continue
        if (
            context["accepted"] is not True
            or context["skip_clear"] is not True
            or context["predicted_side"] != side_value
            or context["expected_edge_bps"] <= min_remaining_edge_bps
        ):
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="knn_remaining_edge_exit_v1",
                barrier_hit_type="knn_remaining_edge",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=False,
            )
    return _time_result(path.iloc[-1], entry_time_ms=entry_time_ms, entry_price=entry_price, side=side, path=path, costs_applied=costs_applied, exit_policy_id=exit_policy_id, exit_reason=exit_reason)


def _knn_dynamic_barriers_v1(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    target_return: float,
    stop_return: float,
    min_target_return: float,
    max_target_return: float,
    min_stop_return: float,
    max_stop_return: float,
    target_edge_multiplier: float,
    min_neighbor_count: int,
    min_neighbor_agreement: float,
    min_neighbor_distance_quality: float,
    min_vote_margin: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    _require_columns(path, _KNN_EXIT_CONTEXT_COLUMNS, exit_policy_id)
    if max_target_return < min_target_return:
        raise ValueError("knn_dynamic_barriers_v1 requires max_target_return >= min_target_return")
    if max_stop_return < min_stop_return:
        raise ValueError("knn_dynamic_barriers_v1 requires max_stop_return >= min_stop_return")
    side_multiplier = _side_multiplier(side)
    for _, row in path.iloc[1:].iterrows():
        context = _knn_prediction_context(
            row,
            min_neighbor_count=min_neighbor_count,
            min_neighbor_agreement=min_neighbor_agreement,
            min_neighbor_distance_quality=min_neighbor_distance_quality,
            min_vote_margin=min_vote_margin,
            require_accepted=True,
        )
        close = _optional_numeric(row.get("close"))
        if context is None or close is None:
            continue
        dynamic_target, dynamic_stop = _knn_dynamic_barrier_returns(
            context,
            target_return=target_return,
            stop_return=stop_return,
            min_target_return=min_target_return,
            max_target_return=max_target_return,
            min_stop_return=min_stop_return,
            max_stop_return=max_stop_return,
            target_edge_multiplier=target_edge_multiplier,
        )
        realized = ((close / float(entry_price)) - 1.0) * side_multiplier
        if realized >= dynamic_target:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="knn_dynamic_barriers_v1_target",
                barrier_hit_type="target",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=True,
            )
        if realized <= -dynamic_stop:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="knn_dynamic_barriers_v1_stop",
                barrier_hit_type="stop",
                costs_applied=costs_applied,
                exit_policy_id=exit_policy_id,
                approximate=True,
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


def _simple_runner_exit(
    *,
    entry_time_ms: int,
    entry_price: float,
    side: str,
    path: pd.DataFrame,
    activation_return: float,
    runner_gap_return: float,
    costs_applied: bool,
    exit_policy_id: str,
    exit_reason: str,
) -> ExitPolicyResult:
    side_multiplier = _side_multiplier(side)
    best_favorable = 0.0
    active = False
    for _, row in path.iloc[1:].iterrows():
        realized = ((float(row["close"]) / float(entry_price)) - 1.0) * side_multiplier
        best_favorable = max(best_favorable, realized)
        active = active or best_favorable >= activation_return
        if active and realized <= best_favorable - runner_gap_return:
            return _result_from_row(
                row,
                entry_time_ms=entry_time_ms,
                entry_price=entry_price,
                side=side,
                path=path.loc[path["bar_time_ms"] <= int(row["bar_time_ms"])],
                exit_reason="simple_runner_v1_trailing_gap",
                barrier_hit_type="runner_gap",
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


def _optional_non_negative_float(value: float | None, *, default: float, policy: str, field: str) -> float:
    if value is None:
        return float(default)
    if value < 0.0:
        raise ValueError(f"{policy} requires non-negative {field}")
    return float(value)


def _optional_positive_int(value: float | None, *, default: int, policy: str, field: str) -> int:
    if value is None:
        return int(default)
    integer = int(value)
    if float(integer) != float(value) or integer <= 0:
        raise ValueError(f"{policy} requires positive integer {field}")
    return integer


def _optional_unit_float(value: float | None, *, default: float, policy: str, field: str) -> float:
    if value is None:
        return float(default)
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{policy} requires {field} between 0 and 1")
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


def _basis_bps_series(path: pd.DataFrame, *, exit_policy_id: str) -> pd.Series:
    bps_column = _first_present_column(path, ("basis_bps",))
    if bps_column is not None:
        return pd.to_numeric(path[bps_column], errors="coerce")
    rate_column = _first_present_column(
        path,
        ("perp_mark_index_basis", "basis_rate", "premium_basis_rate"),
    )
    if rate_column is None:
        raise ValueError(
            f"{exit_policy_id} requires columns: basis_bps, perp_mark_index_basis, or premium_basis_rate"
        )
    return pd.to_numeric(path[rate_column], errors="coerce") * 10_000.0


def _premium_bps_series(path: pd.DataFrame, *, exit_policy_id: str) -> pd.Series:
    bps_column = _first_present_column(path, ("premium_bps",))
    if bps_column is not None:
        return pd.to_numeric(path[bps_column], errors="coerce")
    rate_column = _first_present_column(
        path,
        ("perp_premium", "premium_basis_rate", "premium_close", "premium_index"),
    )
    if rate_column is None:
        raise ValueError(
            f"{exit_policy_id} requires columns: perp_premium, premium_basis_rate, premium_close, or premium_index"
        )
    return pd.to_numeric(path[rate_column], errors="coerce") * 10_000.0


def _premium_context_quality_allows(row: pd.Series, path: pd.DataFrame) -> bool:
    missing_markers = (
        "quality_has_premium_gap",
        "missing_perp_mark_index_basis",
        "missing_perp_premium",
        "missing_basis_bps",
        "missing_premium_basis_rate",
    )
    for column in missing_markers:
        if column not in path.columns:
            continue
        marker = _optional_numeric(row.get(column))
        if marker is None or marker > 0.0:
            return False
    if "quality_provider_backed_all_required" in path.columns:
        provider_backed = _optional_numeric(row.get("quality_provider_backed_all_required"))
        if provider_backed is None or provider_backed <= 0.0:
            return False
    if "quality_latest_window_context_only" in path.columns:
        latest_window_context = _optional_numeric(row.get("quality_latest_window_context_only"))
        if latest_window_context is None or latest_window_context > 0.0:
            return False
    return True


def _gmm_detector_allows(row: pd.Series, path: pd.DataFrame, *, required: bool) -> bool:
    if "regime_detector_type" not in path.columns:
        return not required
    detector = _string_value(row.get("regime_detector_type"))
    return detector == "gmm"


def _gmm_detector_metadata_allows(row: pd.Series, path: pd.DataFrame) -> bool:
    if not set(_GMM_DETECTOR_METADATA_COLUMNS) <= set(path.columns):
        return False
    train_start = _integer_marker(row.get("regime_detector_train_start_ms"))
    train_end = _integer_marker(row.get("regime_detector_train_end_ms"))
    inference_start = _integer_marker(row.get("regime_detector_inference_start_ms"))
    inference_end = _integer_marker(row.get("regime_detector_inference_end_ms"))
    bar_time = _integer_marker(row.get("bar_time_ms"))
    if None in {train_start, train_end, inference_start, inference_end, bar_time}:
        return False
    if not (int(train_start) <= int(train_end) < int(inference_start) <= int(inference_end)):
        return False
    if int(bar_time) < int(inference_start) or int(bar_time) > int(inference_end):
        return False
    return (
        bool(_string_value(row.get("regime_detector_feature_version")))
        and bool(_string_value(row.get("regime_detector_params_hash")))
        and bool(_string_value(row.get("regime_detector_artifact_sha256")))
    )


def _split_safe_regime_row(row: pd.Series) -> bool:
    fit_end = _integer_marker(row.get("hmm_fit_end_row"))
    source_row = _integer_marker(row.get("source_row_index"))
    return fit_end is not None and source_row is not None and fit_end >= 0 and source_row >= 0 and fit_end < source_row


def _knn_prediction_context(
    row: pd.Series,
    *,
    min_neighbor_count: int,
    min_neighbor_agreement: float,
    min_neighbor_distance_quality: float,
    min_vote_margin: float,
    require_accepted: bool,
) -> dict[str, float | str | bool] | None:
    if not _split_safe_neighbor_row(row):
        return None
    p_up = _bounded_unit_value(row.get("p_up_barrier"))
    p_down = _bounded_unit_value(row.get("p_down_barrier"))
    expected_value = _optional_numeric(row.get("expected_net_return_after_costs"))
    agreement = _bounded_unit_value(row.get("neighbor_agreement"))
    distance_quality = _bounded_unit_value(row.get("neighbor_distance_quality"))
    neighbor_count = _integer_marker(row.get("neighbor_count"))
    vote_margin = _bounded_unit_value(row.get("knn_vote_margin"))
    accepted = _optional_bool_flag(row.get("accepted_by_knn"))
    skip_clear = _knn_skip_reason_clear(row.get("knn_skip_reason"))
    if None in {p_up, p_down, expected_value, agreement, distance_quality, neighbor_count, vote_margin, accepted}:
        return None
    if int(neighbor_count) < min_neighbor_count:
        return None
    if float(agreement) < min_neighbor_agreement:
        return None
    if float(distance_quality) < min_neighbor_distance_quality:
        return None
    if float(vote_margin) < min_vote_margin:
        return None
    if require_accepted and (accepted is not True or skip_clear is not True):
        return None
    predicted_side = "long" if float(p_up) >= float(p_down) else "short"
    return {
        "accepted": bool(accepted),
        "skip_clear": bool(skip_clear),
        "predicted_side": predicted_side,
        "probability": max(float(p_up), float(p_down)),
        "expected_edge_bps": float(expected_value) * 10_000.0,
        "expected_value": float(expected_value),
        "agreement": float(agreement),
        "distance_quality": float(distance_quality),
        "vote_margin": float(vote_margin),
    }


def _split_safe_neighbor_row(row: pd.Series) -> bool:
    min_source = _integer_marker(row.get("neighbor_min_source_index"))
    max_source = _integer_marker(row.get("neighbor_max_source_index"))
    fit_end = _integer_marker(row.get("hmm_fit_end_row"))
    source_row = _integer_marker(row.get("source_row_index"))
    if None in {min_source, max_source, fit_end, source_row}:
        return False
    return (
        int(min_source) >= 0
        and int(max_source) >= 0
        and int(fit_end) >= 0
        and int(source_row) >= 0
        and int(min_source) <= int(max_source) <= int(fit_end) < int(source_row)
    )


def _knn_skip_reason_clear(value: Any) -> bool:
    if value is None or pd.isna(value):
        return True
    normalized = str(value).strip().lower()
    return normalized in {"", "none", "nan", "null"}


def _knn_dynamic_barrier_returns(
    context: dict[str, float | str | bool],
    *,
    target_return: float,
    stop_return: float,
    min_target_return: float,
    max_target_return: float,
    min_stop_return: float,
    max_stop_return: float,
    target_edge_multiplier: float,
) -> tuple[float, float]:
    expected_value = float(context["expected_value"])
    edge_target = max(0.0, expected_value) * float(target_edge_multiplier)
    target = _clamp(max(float(target_return), edge_target), min_target_return, max_target_return)
    confidence = max(
        float(context["probability"]),
        float(context["agreement"]),
        float(context["distance_quality"]),
        float(context["vote_margin"]),
    )
    stop_scale = max(0.5, min(1.5, 1.5 - confidence))
    stop = _clamp(float(stop_return) * stop_scale, min_stop_return, max_stop_return)
    return target, stop


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return float(max(float(minimum), min(float(maximum), float(value))))


def _param_float(params: dict[str, Any], key: str, fallback: float | None) -> float | None:
    if key not in params or params[key] is None:
        return fallback
    return float(params[key])


def _first_present_column(frame: pd.DataFrame, columns: tuple[str, ...]) -> str | None:
    for column in columns:
        if column in frame.columns:
            return column
    return None


def _funding_time_to_next_hours(path: pd.DataFrame, *, exit_policy_id: str) -> pd.Series:
    hours_column = _first_present_column(
        path,
        ("cal_time_to_next_funding_h", "hours_to_next_funding"),
    )
    if hours_column is not None:
        return pd.to_numeric(path[hours_column], errors="coerce")
    ms_column = _first_present_column(path, ("time_to_next_funding_ms",))
    if ms_column is not None:
        return pd.to_numeric(path[ms_column], errors="coerce") / 3_600_000.0
    raise ValueError(
        f"{exit_policy_id} requires cal_time_to_next_funding_h, hours_to_next_funding, or time_to_next_funding_ms"
    )


def _funding_rate_series(path: pd.DataFrame, *, exit_policy_id: str) -> pd.Series:
    funding_column = _first_present_column(
        path,
        ("funding_rate", "perp_last_funding_rate", "last_funding_rate"),
    )
    if funding_column is None:
        raise ValueError(f"{exit_policy_id} requires columns: funding_rate")
    return pd.to_numeric(path[funding_column], errors="coerce")


def _optional_numeric(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _bounded_unit_value(value: object) -> float | None:
    numeric = _optional_numeric(value)
    if numeric is None or numeric < 0.0 or numeric > 1.0:
        return None
    return numeric


def _integer_marker(value: object) -> int | None:
    numeric = _optional_numeric(value)
    if numeric is None:
        return None
    integer = int(numeric)
    if float(integer) != numeric:
        return None
    return integer


def _optional_bool_flag(value: object) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        return None
    numeric = _optional_numeric(value)
    if numeric == 0.0:
        return False
    if numeric == 1.0:
        return True
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


def _lower_timeframe_covers_horizon(lower: pd.DataFrame, *, time_exit_ms: int) -> bool:
    horizon = int(time_exit_ms)
    times = (
        pd.to_numeric(lower["bar_time_ms"], errors="coerce")
        .dropna()
        .astype("int64")
        .drop_duplicates()
        .sort_values(kind="mergesort")
    )
    if times.empty:
        return False
    latest = int(times.iloc[-1])
    if latest == horizon:
        return True
    if latest > horizon:
        return False
    diffs = times.diff().dropna()
    positive_diffs = diffs.loc[diffs > 0]
    if positive_diffs.empty:
        return False
    expected_cadence_ms = int(positive_diffs.median())
    return horizon - latest <= expected_cadence_ms


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
