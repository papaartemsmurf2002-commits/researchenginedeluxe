from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from tradingbotsuite.strategies._helpers import RuleBasedStrategy, RuleSignal, confidence_from_strength, spaced_indices

REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS = (
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
    "top_regime_label",
    "max_regime_probability",
    "posterior_entropy",
    "recent_regime_flip",
    "regime_no_trade",
    "hmm_fit_end_row",
    "source_row_index",
)


@dataclass(frozen=True, slots=True)
class _AnalogParams:
    probability_threshold: float
    expected_value_threshold: float
    min_neighbor_count: int
    min_neighbor_agreement: float
    min_neighbor_distance_quality: float
    min_vote_margin: float
    posterior_threshold: float
    entropy_threshold: float
    spacing_bars: int


class HmmKnnLocalAnalogFilterStrategy(RuleBasedStrategy):
    strategy_id = "hmm_knn_local_analog_filter_v2"
    strategy_version = "v1"
    allowed_holding_periods = ("4h", "12h", "24h", "72h", "1h")
    required_feature_sets = ("features_perp_context_v2",)

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        if not _has_required_columns(frame):
            return []
        params = _params_from_config(self.config)
        if params is None:
            return []

        signals: list[RuleSignal] = []
        for index in spaced_indices(frame, params.spacing_bars):
            row = frame.iloc[index]
            routed = _local_analog_signal(row, params)
            if routed is None:
                continue
            side, strength = routed
            signals.append(RuleSignal(index, side, strength, confidence_from_strength(strength)))
        return signals


def _has_required_columns(frame: pd.DataFrame) -> bool:
    return set(REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS) <= set(frame.columns)


def _params_from_config(config: dict[str, Any]) -> _AnalogParams | None:
    probability_threshold = _config_float(config, "probability_threshold", 0.55, positive=True)
    expected_value_threshold = _config_float(config, "expected_value_threshold", 0.0)
    min_neighbor_count = _config_int(config, "min_neighbor_count", 8, positive=True)
    min_neighbor_agreement = _config_float(config, "min_neighbor_agreement", 0.55, positive=True)
    min_neighbor_distance_quality = _config_float(config, "min_neighbor_distance_quality", 0.05, non_negative=True)
    min_vote_margin = _config_float(config, "min_vote_margin", 0.05, non_negative=True)
    posterior_threshold = _config_float(config, "posterior_threshold", 0.60, positive=True)
    entropy_threshold = _config_float(config, "entropy_threshold", 0.78, positive=True)
    spacing_bars = _config_int(config, "spacing_bars", 12, positive=True)
    values: tuple[float | int | None, ...] = (
        probability_threshold,
        expected_value_threshold,
        min_neighbor_count,
        min_neighbor_agreement,
        min_neighbor_distance_quality,
        min_vote_margin,
        posterior_threshold,
        entropy_threshold,
        spacing_bars,
    )
    if any(value is None for value in values):
        return None
    if probability_threshold is None or probability_threshold > 1.0:
        return None
    if min_neighbor_agreement is None or min_neighbor_agreement > 1.0:
        return None
    if min_neighbor_distance_quality is None or min_neighbor_distance_quality > 1.0:
        return None
    if min_vote_margin is None or min_vote_margin > 1.0:
        return None
    if posterior_threshold is None or posterior_threshold > 1.0:
        return None
    if entropy_threshold is None or entropy_threshold > 1.0:
        return None
    return _AnalogParams(
        probability_threshold=float(probability_threshold),
        expected_value_threshold=float(expected_value_threshold),
        min_neighbor_count=int(min_neighbor_count),
        min_neighbor_agreement=float(min_neighbor_agreement),
        min_neighbor_distance_quality=float(min_neighbor_distance_quality),
        min_vote_margin=float(min_vote_margin),
        posterior_threshold=float(posterior_threshold),
        entropy_threshold=float(entropy_threshold),
        spacing_bars=int(spacing_bars),
    )


def _local_analog_signal(row: pd.Series, params: _AnalogParams) -> tuple[str, float] | None:
    if not _split_safe_hmm_row(row) or not _split_safe_neighbor_row(row):
        return None
    accepted_by_knn = _bool_flag(row.get("accepted_by_knn"))
    regime_no_trade = _bool_flag(row.get("regime_no_trade"))
    recent_regime_flip = _bool_flag(row.get("recent_regime_flip"))
    if accepted_by_knn is not True or regime_no_trade is None or recent_regime_flip is None:
        return None
    if regime_no_trade or recent_regime_flip:
        return None
    if not _knn_skip_reason_clear(row.get("knn_skip_reason")):
        return None

    posterior_probability = _finite_float(row.get("max_regime_probability"))
    posterior_entropy = _finite_float(row.get("posterior_entropy"))
    if posterior_probability is None or posterior_entropy is None:
        return None
    if posterior_probability < params.posterior_threshold or posterior_entropy > params.entropy_threshold:
        return None

    p_up = _bounded_unit(row.get("p_up_barrier"))
    p_down = _bounded_unit(row.get("p_down_barrier"))
    expected_value = _finite_float(row.get("expected_net_return_after_costs"))
    agreement = _bounded_unit(row.get("neighbor_agreement"))
    distance_quality = _bounded_unit(row.get("neighbor_distance_quality"))
    neighbor_count = _integer_marker(row.get("neighbor_count"))
    vote_margin = _bounded_unit(row.get("knn_vote_margin"))
    if None in {p_up, p_down, expected_value, agreement, distance_quality, neighbor_count, vote_margin}:
        return None
    if int(neighbor_count) < params.min_neighbor_count:
        return None
    if float(expected_value) < params.expected_value_threshold:
        return None
    if float(agreement) < params.min_neighbor_agreement or float(distance_quality) < params.min_neighbor_distance_quality:
        return None
    if float(vote_margin) < params.min_vote_margin:
        return None
    probability = max(float(p_up), float(p_down))
    if probability < params.probability_threshold:
        return None
    side = "long" if float(p_up) >= float(p_down) else "short"
    strength = _bounded_strength(
        max(
            probability,
            float(agreement),
            float(distance_quality),
            posterior_probability,
            float(vote_margin),
        )
    )
    return side, strength


def _split_safe_hmm_row(row: pd.Series) -> bool:
    fit_end = _integer_marker(row.get("hmm_fit_end_row"))
    source_row = _integer_marker(row.get("source_row_index"))
    return fit_end is not None and source_row is not None and fit_end >= 0 and source_row >= 0 and fit_end < source_row


def _split_safe_neighbor_row(row: pd.Series) -> bool:
    min_source = _integer_marker(row.get("neighbor_min_source_index"))
    max_source = _integer_marker(row.get("neighbor_max_source_index"))
    source_row = _integer_marker(row.get("source_row_index"))
    fit_end = _integer_marker(row.get("hmm_fit_end_row"))
    if min_source is None or max_source is None or source_row is None or fit_end is None:
        return False
    if min_source < 0 or max_source < 0 or source_row < 0 or fit_end < 0:
        return False
    return min_source <= max_source <= fit_end < source_row


def _knn_skip_reason_clear(value: Any) -> bool:
    if value is None or pd.isna(value):
        return True
    normalized = str(value).strip().lower()
    return normalized in {"", "none", "nan", "null"}


def _bool_flag(value: Any) -> bool | None:
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
    numeric = _finite_float(value)
    if numeric == 0.0:
        return False
    if numeric == 1.0:
        return True
    return None


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if value is None or pd.isna(value):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _bounded_unit(value: Any) -> float | None:
    parsed = _finite_float(value)
    if parsed is None or parsed < 0.0 or parsed > 1.0:
        return None
    return parsed


def _config_float(
    config: dict[str, Any],
    key: str,
    default: float,
    *,
    positive: bool = False,
    non_negative: bool = False,
) -> float | None:
    value = _finite_float(config.get(key, default))
    if value is None:
        return None
    if positive and value <= 0.0:
        return None
    if non_negative and value < 0.0:
        return None
    return value


def _config_int(config: dict[str, Any], key: str, default: int, *, positive: bool = False) -> int | None:
    value = _finite_float(config.get(key, default))
    if value is None:
        return None
    integer = int(value)
    if float(integer) != value:
        return None
    if positive and integer <= 0:
        return None
    return integer


def _integer_marker(value: Any) -> int | None:
    parsed = _finite_float(value)
    if parsed is None:
        return None
    integer = int(parsed)
    if float(integer) != parsed:
        return None
    return integer


def _bounded_strength(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(max(0.01, min(1.0, value)))
