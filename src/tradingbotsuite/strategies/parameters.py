from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class SignalDensityControls:
    min_signal_rate: float = 0.0
    max_signal_rate: float = 1.0
    max_turnover: float = 1.0

    def to_payload(self) -> dict[str, float]:
        return {
            "min_signal_rate": float(self.min_signal_rate),
            "max_signal_rate": float(self.max_signal_rate),
            "max_turnover": float(self.max_turnover),
        }


@dataclass(frozen=True, slots=True)
class StrategyParameterMetadata:
    strategy_id: str
    default_parameters: Mapping[str, Any] = field(default_factory=dict)
    parameter_space: Mapping[str, tuple[Any, ...]] = field(default_factory=dict)
    holding_window_overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    additional_allowed_parameter_values: Mapping[str, Mapping[str, tuple[Any, ...]]] = field(default_factory=dict)
    signal_density: SignalDensityControls = field(default_factory=SignalDensityControls)
    failure_modes: tuple[str, ...] = ()

    def defaults_for_holding_window(self, holding_window: str) -> dict[str, Any]:
        return {
            **dict(self.default_parameters),
            **dict(self.holding_window_overrides.get(holding_window, {})),
        }

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["parameter_space"] = {
            key: list(values)
            for key, values in self.parameter_space.items()
        }
        payload["additional_allowed_parameter_values"] = {
            holding_window: {
                key: list(values)
                for key, values in parameter_values.items()
            }
            for holding_window, parameter_values in self.additional_allowed_parameter_values.items()
        }
        payload["signal_density"] = self.signal_density.to_payload()
        return payload


STRATEGY_PARAMETER_METADATA: dict[str, StrategyParameterMetadata] = {
    "baseline_no_trade": StrategyParameterMetadata(
        strategy_id="baseline_no_trade",
        failure_modes=("no_trade_comparator",),
    ),
    "trend_following_v1": StrategyParameterMetadata(
        strategy_id="trend_following_v1",
        default_parameters={
            "slope_threshold": 0.12,
            "max_choppiness": 58.0,
            "funding_penalty_threshold": 0.00025,
            "spacing_bars": 12,
        },
        parameter_space={
            "slope_threshold": (0.08, 0.12, 0.16),
            "max_choppiness": (52.0, 58.0, 64.0),
            "spacing_bars": (8, 12, 16),
        },
        holding_window_overrides={
            "4h": {"spacing_bars": 8, "slope_threshold": 0.10},
            "12h": {"spacing_bars": 10},
            "72h": {"spacing_bars": 18, "slope_threshold": 0.16},
            "7d": {"spacing_bars": 24, "slope_threshold": 0.18},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.005, max_signal_rate=0.35, max_turnover=0.35),
        failure_modes=("trend_below_slope_threshold", "trend_choppiness_filter", "funding_penalty_filter"),
    ),
    "baseline_trend": StrategyParameterMetadata(
        strategy_id="baseline_trend",
        default_parameters={
            "slope_threshold": 0.12,
            "max_choppiness": 58.0,
            "funding_penalty_threshold": 0.00025,
            "spacing_bars": 12,
        },
        parameter_space={
            "slope_threshold": (0.08, 0.12, 0.16),
            "spacing_bars": (8, 12, 16),
        },
        signal_density=SignalDensityControls(min_signal_rate=0.005, max_signal_rate=0.35, max_turnover=0.35),
        failure_modes=("trend_below_slope_threshold", "trend_choppiness_filter"),
    ),
    "volatility_breakout_v1": StrategyParameterMetadata(
        strategy_id="volatility_breakout_v1",
        default_parameters={
            "shock_threshold": 1.0,
            "atr_percentile_threshold": 0.45,
            "spacing_bars": 10,
        },
        parameter_space={
            "shock_threshold": (0.7, 1.0, 1.3),
            "atr_percentile_threshold": (0.25, 0.45, 0.65),
            "spacing_bars": (8, 10, 14),
        },
        holding_window_overrides={
            "1h": {"spacing_bars": 6, "atr_percentile_threshold": 0.55},
            "4h": {"spacing_bars": 8},
            "72h": {"spacing_bars": 18, "shock_threshold": 1.3},
            "7d": {"spacing_bars": 24, "shock_threshold": 1.5},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.003, max_signal_rate=0.30, max_turnover=0.30),
        failure_modes=("breakout_low_volatility_shock", "breakout_low_atr_percentile", "breakout_flat_slope"),
    ),
    "range_reversion_v1": StrategyParameterMetadata(
        strategy_id="range_reversion_v1",
        default_parameters={
            "choppiness_threshold": 55.0,
            "stretch_threshold": 0.10,
            "spacing_bars": 8,
        },
        parameter_space={
            "choppiness_threshold": (50.0, 55.0, 60.0),
            "stretch_threshold": (0.04, 0.08, 0.12),
            "spacing_bars": (6, 8, 12),
        },
        holding_window_overrides={
            "1h": {"spacing_bars": 6, "stretch_threshold": 0.06},
            "4h": {"spacing_bars": 8},
            "12h": {"spacing_bars": 10},
            "24h": {"spacing_bars": 12, "stretch_threshold": 0.12},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.005, max_signal_rate=0.40, max_turnover=0.40),
        failure_modes=("range_low_choppiness", "range_insufficient_stretch"),
    ),
    "funding_basis_v1": StrategyParameterMetadata(
        strategy_id="funding_basis_v1",
        default_parameters={
            "funding_threshold": 0.00004,
            "basis_bps_threshold": 1.0,
            "spacing_bars": 12,
        },
        parameter_space={
            "funding_threshold": (0.00003, 0.00004, 0.00006),
            "basis_bps_threshold": (0.8, 1.0, 1.5),
            "spacing_bars": (8, 12, 16),
        },
        holding_window_overrides={
            "4h": {"spacing_bars": 8},
            "12h": {"spacing_bars": 10},
            "72h": {"spacing_bars": 18},
            "7d": {"spacing_bars": 24},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.002, max_signal_rate=0.25, max_turnover=0.25),
        failure_modes=("funding_basis_below_threshold", "funding_basis_momentum_conflict"),
    ),
    "perp_basis_convergence_v2": StrategyParameterMetadata(
        strategy_id="perp_basis_convergence_v2",
        default_parameters={
            "basis_vol_threshold": 10.0,
            "premium_z_threshold": 1.25,
            "min_edge_bps": 5.0,
            "funding_policy": "require_aligned_or_neutral",
            "spacing_bars": 12,
        },
        parameter_space={
            "basis_vol_threshold": (8.0, 10.0, 12.0),
            "premium_z_threshold": (1.0, 1.25, 1.5),
            "min_edge_bps": (2.5, 5.0, 7.5),
            "funding_policy": ("require_aligned_or_neutral", "carry_adjusted"),
            "spacing_bars": (8, 12, 16),
        },
        holding_window_overrides={
            "4h": {"spacing_bars": 8, "min_edge_bps": 2.5},
            "12h": {"spacing_bars": 10},
            "72h": {"spacing_bars": 18, "basis_vol_threshold": 12.0},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.001, max_signal_rate=0.20, max_turnover=0.20),
        failure_modes=(
            "perp_context_quality_invalid",
            "perp_basis_below_threshold",
            "perp_premium_z_below_threshold",
            "perp_edge_below_cost_floor",
            "perp_funding_policy_filter",
        ),
    ),
    "funding_crowding_fade_v2": StrategyParameterMetadata(
        strategy_id="funding_crowding_fade_v2",
        default_parameters={
            "funding_z_threshold": 1.25,
            "funding_rate_abs_bps_threshold": 0.4,
            "premium_confirmation_bps": 2.5,
            "min_edge_bps": 1.0,
            "oi_confirmation_z_min": 0.25,
            "funding_momentum_policy": "against_fade_filter",
            "spacing_bars": 12,
        },
        parameter_space={
            "funding_z_threshold": (1.0, 1.25, 1.5),
            "funding_rate_abs_bps_threshold": (0.3, 0.4, 0.6),
            "premium_confirmation_bps": (1.5, 2.5, 4.0),
            "min_edge_bps": (0.5, 1.0, 1.5),
            "oi_confirmation_z_min": (0.0, 0.25, 0.5),
            "funding_momentum_policy": ("ignore", "against_fade_filter", "require_reversal"),
            "spacing_bars": (8, 12, 16),
        },
        holding_window_overrides={
            "4h": {"spacing_bars": 8, "min_edge_bps": 0.25},
            "12h": {"spacing_bars": 10, "min_edge_bps": 0.75},
            "72h": {"spacing_bars": 18, "funding_z_threshold": 1.5, "premium_confirmation_bps": 4.0},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.001, max_signal_rate=0.25, max_turnover=0.25),
        failure_modes=(
            "perp_context_quality_invalid",
            "funding_crowding_below_threshold",
            "premium_crowding_below_threshold",
            "oi_confirmation_missing",
            "funding_momentum_against_fade",
            "funding_edge_below_floor",
        ),
    ),
    "oi_flow_breakout_v2": StrategyParameterMetadata(
        strategy_id="oi_flow_breakout_v2",
        default_parameters={
            "oi_delta_z_threshold": 1.0,
            "oi_delta_min_notional": 0.0,
            "premium_confirmation_bps": 5.0,
            "premium_slope_min_bps": 0.0,
            "flow_z_threshold": 0.75,
            "flow_confirmation_policy": "optional_when_missing",
            "spacing_bars": 12,
        },
        parameter_space={
            "oi_delta_z_threshold": (0.75, 1.0, 1.5),
            "oi_delta_min_notional": (0.0, 5_000_000.0, 25_000_000.0),
            "premium_confirmation_bps": (3.0, 5.0, 7.0),
            "premium_slope_min_bps": (0.0, 0.025, 0.05),
            "flow_z_threshold": (0.5, 0.75, 1.0),
            "flow_confirmation_policy": ("ignore", "optional_when_missing", "require_when_present", "required"),
            "spacing_bars": (8, 12, 16),
        },
        holding_window_overrides={
            "4h": {"spacing_bars": 8},
            "12h": {"spacing_bars": 10},
            "72h": {"spacing_bars": 18, "oi_delta_z_threshold": 1.25, "premium_confirmation_bps": 7.0},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.001, max_signal_rate=0.25, max_turnover=0.25),
        failure_modes=(
            "perp_context_quality_invalid",
            "oi_expansion_below_threshold",
            "premium_breakout_confirmation_missing",
            "premium_slope_filter",
            "flow_confirmation_missing_or_misaligned",
        ),
    ),
    "funding_window_timing_v1": StrategyParameterMetadata(
        strategy_id="funding_window_timing_v1",
        default_parameters={
            "funding_z_threshold": 1.0,
            "funding_rate_abs_bps_threshold": 0.4,
            "premium_confirmation_bps": 2.5,
            "entry_window_h": 1.0,
            "window_mode": "pre_funding",
            "funding_momentum_policy": "avoid_acceleration",
            "oi_confirmation_z_min": 0.0,
            "spacing_bars": 4,
        },
        parameter_space={
            "funding_z_threshold": (1.0, 1.25, 1.5),
            "funding_rate_abs_bps_threshold": (0.3, 0.4, 0.6),
            "premium_confirmation_bps": (1.5, 2.5, 4.0),
            "entry_window_h": (0.5, 1.0, 2.0),
            "window_mode": ("pre_funding", "post_funding", "both"),
            "funding_momentum_policy": ("ignore", "avoid_acceleration", "require_reversal"),
            "oi_confirmation_z_min": (0.0, 0.25, 0.5),
            "spacing_bars": (4, 8, 12),
        },
        holding_window_overrides={
            "4h": {"spacing_bars": 4, "entry_window_h": 1.0},
            "12h": {"spacing_bars": 8},
            "72h": {"spacing_bars": 12, "entry_window_h": 2.0, "funding_z_threshold": 1.25},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.001, max_signal_rate=0.25, max_turnover=0.25),
        failure_modes=(
            "perp_context_quality_invalid",
            "outside_funding_window",
            "funding_below_threshold",
            "premium_crowding_below_threshold",
            "funding_momentum_filter",
            "oi_confirmation_missing",
        ),
    ),
    "hmm_routed_alpha_sleeves_v2": StrategyParameterMetadata(
        strategy_id="hmm_routed_alpha_sleeves_v2",
        default_parameters={
            "posterior_threshold": 0.60,
            "entropy_threshold": 0.78,
            "basis_bps_threshold": 6.0,
            "premium_z_threshold": 1.0,
            "funding_z_threshold": 1.0,
            "oi_delta_z_threshold": 0.75,
            "oi_delta_min_notional": 0.0,
            "premium_slope_min_bps": 0.0,
            "flow_alignment_z_min": 0.0,
            "min_edge_bps": 1.0,
            "spacing_bars": 12,
        },
        parameter_space={
            "posterior_threshold": (0.55, 0.60, 0.65),
            "entropy_threshold": (0.70, 0.78, 0.85),
            "basis_bps_threshold": (4.0, 6.0, 8.0),
            "premium_z_threshold": (0.75, 1.0, 1.25),
            "funding_z_threshold": (0.75, 1.0, 1.25),
            "oi_delta_z_threshold": (0.5, 0.75, 1.0),
            "oi_delta_min_notional": (0.0, 5_000_000.0, 25_000_000.0),
            "premium_slope_min_bps": (0.0, 0.025, 0.05),
            "flow_alignment_z_min": (0.0, 0.25, 0.5),
            "min_edge_bps": (0.5, 1.0, 2.5),
            "spacing_bars": (8, 12, 16),
        },
        holding_window_overrides={
            "4h": {"spacing_bars": 8, "min_edge_bps": 0.5},
            "12h": {"spacing_bars": 10},
            "72h": {"spacing_bars": 18, "posterior_threshold": 0.65},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.001, max_signal_rate=0.25, max_turnover=0.25),
        failure_modes=(
            "hmm_router_missing_split_safe_posteriors",
            "hmm_router_non_prior_fit_posteriors",
            "hmm_router_low_posterior_confidence",
            "hmm_router_high_posterior_entropy",
            "hmm_router_recent_regime_flip",
            "hmm_router_regime_no_trade",
            "hmm_router_unknown_or_shock_regime",
            "perp_context_quality_invalid",
            "hmm_router_sleeve_filter",
        ),
    ),
    "hmm_knn_local_analog_filter_v2": StrategyParameterMetadata(
        strategy_id="hmm_knn_local_analog_filter_v2",
        default_parameters={
            "probability_threshold": 0.55,
            "expected_value_threshold": 0.0,
            "min_neighbor_count": 8,
            "min_neighbor_agreement": 0.55,
            "min_neighbor_distance_quality": 0.05,
            "min_vote_margin": 0.05,
            "posterior_threshold": 0.60,
            "entropy_threshold": 0.78,
            "spacing_bars": 12,
        },
        parameter_space={
            "probability_threshold": (0.55, 0.60, 0.65),
            "expected_value_threshold": (0.0, 0.0005, 0.001),
            "min_neighbor_count": (8, 12, 16),
            "min_neighbor_agreement": (0.55, 0.60, 0.65),
            "min_neighbor_distance_quality": (0.05, 0.10, 0.20),
            "min_vote_margin": (0.05, 0.10, 0.20),
            "posterior_threshold": (0.55, 0.60, 0.65),
            "entropy_threshold": (0.70, 0.78, 0.85),
            "spacing_bars": (8, 12, 16),
        },
        holding_window_overrides={
            "4h": {"spacing_bars": 8, "min_neighbor_count": 8},
            "12h": {"spacing_bars": 10},
            "72h": {"spacing_bars": 18, "posterior_threshold": 0.65},
        },
        additional_allowed_parameter_values={
            "1h": {
                "probability_threshold": (0.48, 0.50, 0.52, 0.55, 0.58, 0.62),
                "expected_value_threshold": (-0.0004, -0.0002, 0.0, 0.0002),
                "min_neighbor_count": (2, 3, 4, 5),
                "min_neighbor_agreement": (0.48, 0.50, 0.52, 0.55, 0.60),
                "min_neighbor_distance_quality": (0.0, 0.005, 0.01),
                "min_vote_margin": (0.0, 0.02, 0.03, 0.05),
                "spacing_bars": (4,),
            },
        },
        signal_density=SignalDensityControls(min_signal_rate=0.001, max_signal_rate=0.25, max_turnover=0.25),
        failure_modes=(
            "hmm_knn_missing_split_safe_predictions",
            "hmm_knn_non_prior_fit_posteriors",
            "hmm_knn_future_neighbor_boundary",
            "hmm_knn_not_accepted",
            "hmm_knn_low_probability",
            "hmm_knn_low_expected_value",
            "hmm_knn_insufficient_neighbors",
            "hmm_knn_low_neighbor_agreement",
            "hmm_knn_low_distance_quality",
            "hmm_knn_regime_no_trade",
            "hmm_knn_recent_regime_flip",
        ),
    ),
    "liquidation_absorption_classifier_v1": StrategyParameterMetadata(
        strategy_id="liquidation_absorption_classifier_v1",
        default_parameters={
            "notional_z_threshold": 1.25,
            "imbalance_abs_threshold": 0.65,
            "reclaim_bps_threshold": 15.0,
            "min_event_count": 3.0,
            "max_event_age_h": 1.0,
            "allow_latest_window_context": False,
            "spacing_bars": 4,
        },
        parameter_space={
            "notional_z_threshold": (1.0, 1.25, 1.5),
            "imbalance_abs_threshold": (0.5, 0.65, 0.8),
            "reclaim_bps_threshold": (10.0, 15.0, 25.0),
            "min_event_count": (1.0, 3.0, 5.0),
            "max_event_age_h": (0.25, 0.5, 1.0),
            "allow_latest_window_context": (False,),
            "spacing_bars": (1, 4, 8),
        },
        holding_window_overrides={
            "1h": {"spacing_bars": 1, "max_event_age_h": 0.5},
            "4h": {"spacing_bars": 4},
            "12h": {"spacing_bars": 8, "notional_z_threshold": 1.5},
            "24h": {"spacing_bars": 12, "notional_z_threshold": 1.5, "reclaim_bps_threshold": 25.0},
        },
        signal_density=SignalDensityControls(min_signal_rate=0.001, max_signal_rate=0.20, max_turnover=0.20),
        failure_modes=(
            "liquidation_context_missing_or_not_provider_backed",
            "liquidation_latest_window_context_blocked",
            "liquidation_notional_below_threshold",
            "liquidation_imbalance_below_threshold",
            "liquidation_reclaim_below_threshold",
            "liquidation_event_too_old",
        ),
    ),
    "regime_adaptive_v1": StrategyParameterMetadata(
        strategy_id="regime_adaptive_v1",
        default_parameters={"spacing_bars": 12},
        parameter_space={"spacing_bars": (8, 12, 16)},
        holding_window_overrides={"4h": {"spacing_bars": 8}, "7d": {"spacing_bars": 24}},
        signal_density=SignalDensityControls(min_signal_rate=0.002, max_signal_rate=0.30, max_turnover=0.30),
        failure_modes=("regime_adaptive_no_active_regime", "regime_adaptive_funding_filter"),
    ),
    "hmm_knn_diagnostic_v1": StrategyParameterMetadata(
        strategy_id="hmm_knn_diagnostic_v1",
        default_parameters={
            "probability_threshold": 0.55,
            "expected_value_threshold": 0.0,
            "spacing_bars": 8,
        },
        parameter_space={
            "probability_threshold": (0.55, 0.60, 0.65),
            "expected_value_threshold": (0.0, 0.0005, 0.001),
            "spacing_bars": (6, 8, 12),
        },
        holding_window_overrides={"1h": {"spacing_bars": 6}, "7d": {"spacing_bars": 24}},
        signal_density=SignalDensityControls(min_signal_rate=0.002, max_signal_rate=0.30, max_turnover=0.30),
        failure_modes=("hmm_knn_regime_no_trade", "hmm_knn_probability_below_threshold", "hmm_knn_expected_value_filter"),
    ),
    "lc_reference_v1": StrategyParameterMetadata(
        strategy_id="lc_reference_v1",
        default_parameters={"slope_threshold": 0.10, "spacing_bars": 12},
        parameter_space={
            "slope_threshold": (0.08, 0.10, 0.12),
            "spacing_bars": (8, 12, 16),
        },
        holding_window_overrides={"1h": {"spacing_bars": 6}, "7d": {"spacing_bars": 24}},
        signal_density=SignalDensityControls(min_signal_rate=0.002, max_signal_rate=0.35, max_turnover=0.35),
        failure_modes=("lc_reference_below_slope_threshold",),
    ),
}


def metadata_for_strategy(strategy_id: str) -> StrategyParameterMetadata:
    canonical_id = "trend_following_v1" if strategy_id == "baseline_trend" else strategy_id
    return STRATEGY_PARAMETER_METADATA.get(canonical_id, StrategyParameterMetadata(strategy_id=strategy_id))


def defaults_for_holding_window(strategy_id: str, holding_window: str) -> dict[str, Any]:
    return metadata_for_strategy(strategy_id).defaults_for_holding_window(holding_window)


def signal_density_controls(strategy_id: str) -> SignalDensityControls:
    return metadata_for_strategy(strategy_id).signal_density


def strategy_parameter_manifest(strategy_ids: tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    payloads: list[dict[str, Any]] = []
    for strategy_id in strategy_ids:
        if strategy_id in seen:
            continue
        seen.add(strategy_id)
        payloads.append(metadata_for_strategy(strategy_id).to_payload())
    return payloads


def allowed_parameter_names(strategy_id: str) -> set[str]:
    metadata = metadata_for_strategy(strategy_id)
    additional_names: set[str] = set()
    for values_by_name in metadata.additional_allowed_parameter_values.values():
        additional_names.update(values_by_name)
    return set(metadata.default_parameters) | set(metadata.parameter_space) | additional_names


def strategy_metadata_sha256(strategy_id: str) -> str:
    return sha256(
        json.dumps(
            metadata_for_strategy(strategy_id).to_payload(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def allowed_parameter_values(strategy_id: str, holding_window: str, parameter_name: str) -> tuple[Any, ...]:
    metadata = metadata_for_strategy(strategy_id)
    values = list(metadata.parameter_space.get(parameter_name, ()))
    defaults = metadata.defaults_for_holding_window(holding_window)
    if parameter_name in defaults and defaults[parameter_name] not in values:
        values.append(defaults[parameter_name])
    for scoped_values in (
        metadata.additional_allowed_parameter_values.get("*", {}),
        metadata.additional_allowed_parameter_values.get(holding_window, {}),
    ):
        for value in scoped_values.get(parameter_name, ()):
            if value not in values:
                values.append(value)
    return tuple(values)


def search_parameter_space_for_holding_window(strategy_id: str, holding_window: str) -> dict[str, tuple[Any, ...]]:
    metadata = metadata_for_strategy(strategy_id)
    defaults = metadata.defaults_for_holding_window(holding_window)
    space: dict[str, tuple[Any, ...]] = {}
    for name in sorted(set(metadata.parameter_space) | set(defaults)):
        values = list(metadata.parameter_space.get(name, ()))
        if name in defaults and defaults[name] not in values:
            values.append(defaults[name])
        if values:
            space[name] = tuple(values)
    return space
