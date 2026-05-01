from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

HMM_KNN_FEATURE_PACKS = {
    "full_context_wt3d": (
        "direction_long",
        "efficiency_ratio",
        "choppiness",
        "directional_slope_atr",
        "directional_di_spread",
        "range_width",
        "primary_signed_imbalance_ratio",
        "primary_sqrt_signed_imbalance_ratio",
        "top_of_book_imbalance",
        "queue_imbalance_l5",
        "spread_bps",
        "basis_bps",
        "funding_rate",
        "funding_rate_change",
        "open_interest_change_pct",
        "premium_basis_rate",
        "realized_volatility",
        "atr_percentile",
        "volatility_shock_zscore",
        "wt3d_fast",
        "wt3d_normal",
        "wt3d_slow",
        "wt3d_fast_normal_spread",
        "wt3d_normal_slow_spread",
        "wt3d_slope",
        "wt3d_acceleration",
        "wt3d_reversal_intensity",
        "wt3d_mtf_agreement",
    ),
    "full_context_no_wt3d": (
        "direction_long",
        "efficiency_ratio",
        "choppiness",
        "directional_slope_atr",
        "directional_di_spread",
        "range_width",
        "primary_signed_imbalance_ratio",
        "primary_sqrt_signed_imbalance_ratio",
        "top_of_book_imbalance",
        "queue_imbalance_l5",
        "spread_bps",
        "basis_bps",
        "funding_rate",
        "funding_rate_change",
        "open_interest_change_pct",
        "premium_basis_rate",
        "realized_volatility",
        "atr_percentile",
        "volatility_shock_zscore",
    ),
    "price_trend_vol": (
        "direction_long",
        "efficiency_ratio",
        "choppiness",
        "directional_slope_atr",
        "directional_di_spread",
        "range_width",
        "realized_volatility",
        "atr_percentile",
        "volatility_shock_zscore",
    ),
    "perp_context_only": (
        "basis_bps",
        "funding_rate",
        "funding_rate_change",
        "open_interest_change_pct",
        "premium_basis_rate",
    ),
    "microstructure_context": (
        "primary_signed_imbalance_ratio",
        "primary_sqrt_signed_imbalance_ratio",
        "top_of_book_imbalance",
        "queue_imbalance_l5",
        "spread_bps",
    ),
}


@dataclass(frozen=True, slots=True)
class HmmKnnPluginConfig:
    feature_pack: str = "full_context_no_wt3d"
    distance: str = "lorentzian"
    regime_backend: str = "gaussian_mixture_fallback"
    same_regime_only: bool = True
    k: int = 32
    weighting: str = "inverse_distance"
    thresholds: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "HmmKnnPluginConfig":
        return cls(
            feature_pack=str(payload.get("feature_pack", "full_context_no_wt3d")),
            distance=str(payload.get("distance", "lorentzian")),
            regime_backend=str(payload.get("regime_backend", "gaussian_mixture_fallback")),
            same_regime_only=bool(payload.get("same_regime_only", True)),
            k=int(payload.get("k", 32)),
            weighting=str(payload.get("weighting", "inverse_distance")),
            thresholds={str(key): float(value) for key, value in dict(payload.get("thresholds", {})).items()},
        )


def resolve_feature_columns(feature_pack: str) -> tuple[str, ...]:
    key = str(feature_pack)
    if key not in HMM_KNN_FEATURE_PACKS:
        raise ValueError(f"unknown_hmm_knn_feature_pack:{feature_pack}")
    return HMM_KNN_FEATURE_PACKS[key]
