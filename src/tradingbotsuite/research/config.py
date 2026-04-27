from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DatasetSettings:
    bar_lookback: int
    future_bar_limit: int
    premium_interval: str
    open_interest_period: str
    open_interest_lookback_points: int
    funding_history_limit: int
    agg_trade_window_seconds: int


@dataclass(frozen=True, slots=True)
class FeatureSettings:
    realized_vol_window_bars: int
    atr_percentile_window_bars: int
    volatility_shock_window_bars: int
    volatility_shock_zscore_threshold: float


@dataclass(frozen=True, slots=True)
class AcceptanceFilterSettings:
    core_score_threshold: float
    perp_score_floor: float
    total_score_threshold: float
    slope_minimum: float
    er_minimum: float
    di_spread_minimum: float
    chop_maximum: float
    corridor_width_minimum: float
    basis_soft_bps: float
    basis_hard_bps: float
    premium_soft_rate: float
    funding_adverse_threshold: float
    near_funding_minutes: int
    liquidity_soft_spread_bps: float
    liquidity_hard_spread_bps: float
    signed_support_threshold: float
    book_support_threshold: float


@dataclass(frozen=True, slots=True)
class ModelSettings:
    probability_threshold: float
    confidence_bucket_thresholds: list[float]
    size_multiplier_thresholds: list[float]
    size_multiplier_values: list[float]
    random_state: int
    max_iter: int


@dataclass(frozen=True, slots=True)
class EvaluationSettings:
    walk_forward_splits: int
    train_fraction: float
    calibration_fraction: float
    min_training_rows: int
    min_calibration_rows: int
    fee_bps: float
    slippage_bps: float


@dataclass(frozen=True, slots=True)
class ExitSupervisionSettings:
    adverse_selection_enabled: bool
    adverse_selection_window_bars: int
    adverse_selection_min_favorable_excursion_atr: float
    adverse_selection_signed_imbalance_flip_threshold: float
    adverse_selection_book_imbalance_flip_threshold: float
    alpha_decay_enabled: bool
    alpha_decay_recheck_bars: int
    alpha_decay_viability_threshold: float


@dataclass(frozen=True, slots=True)
class PromotionSettings:
    min_expectancy_improvement: float
    min_trade_count: int
    max_mean_absolute_calibration_error: float
    min_improved_split_ratio: float


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    version: str
    symbol: str
    dataset: DatasetSettings
    features: FeatureSettings
    acceptance_filter: AcceptanceFilterSettings
    model: ModelSettings
    evaluation: EvaluationSettings
    exit_supervision: ExitSupervisionSettings
    promotion: PromotionSettings

    def to_payload(self) -> dict:
        return {
            "version": self.version,
            "symbol": self.symbol,
            "dataset": asdict(self.dataset),
            "features": asdict(self.features),
            "acceptance_filter": asdict(self.acceptance_filter),
            "model": asdict(self.model),
            "evaluation": asdict(self.evaluation),
            "exit_supervision": asdict(self.exit_supervision),
            "promotion": asdict(self.promotion),
        }

    def plan_sha256(self) -> str:
        return sha256(json.dumps(self.to_payload(), sort_keys=True).encode("utf-8")).hexdigest()


def load_research_plan(path: Path) -> ResearchPlan:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ResearchPlan(
        version=str(payload["version"]),
        symbol=str(payload["symbol"]).upper(),
        dataset=DatasetSettings(**payload["dataset"]),
        features=FeatureSettings(**payload["features"]),
        acceptance_filter=AcceptanceFilterSettings(**payload["acceptance_filter"]),
        model=ModelSettings(**payload["model"]),
        evaluation=EvaluationSettings(**payload["evaluation"]),
        exit_supervision=ExitSupervisionSettings(**payload["exit_supervision"]),
        promotion=PromotionSettings(**payload["promotion"]),
    )
