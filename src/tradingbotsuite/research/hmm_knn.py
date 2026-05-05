from __future__ import annotations

import importlib
import json
import math
import time
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.mixture import GaussianMixture

from tradingbotsuite.core.math import BAR_INTERVAL_MS
from tradingbotsuite.research.dataset import LABEL_OUTCOME_COLUMNS, LABEL_VERSION
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.strategies.hmm_knn.artifacts import benchmark_against_stage6_baselines
from tradingbotsuite.strategies.hmm_knn.config import resolve_feature_columns
from tradingbotsuite.strategies.hmm_knn.diagnostics import build_hmm_knn_artifact_diagnostics
from tradingbotsuite.strategies.hmm_knn.distances import (
    DISTANCE_FUNCTIONS,
    available_distance_metrics,
    resolve_distance_function,
    resolve_distance_metric,
)
from tradingbotsuite.strategies.hmm_knn.neighbors import (
    build_neighbor_pool,
    resolve_regime_match_mode,
    select_neighbor_positions,
)

try:  # optional research extra
    from hmmlearn.hmm import GaussianHMM
except Exception:  # pragma: no cover - depends on optional environment
    GaussianHMM = None

try:  # optional research extra
    import xgboost as _xgboost
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - depends on optional environment
    _xgboost = None
    XGBClassifier = None

HMM_KNN_ARTIFACT_MANIFEST_VERSION = "v2-hmm-knn-artifact-manifest-1"
HMM_KNN_METRICS_VERSION = "v2-hmm-knn-walk-forward-metrics-1"
HMM_KNN_FEATURE_VERSION = "v2-btc-hmm-knn-features-1"
WT3D_FEATURE_COLUMNS = [
    "wt3d_fast",
    "wt3d_normal",
    "wt3d_slow",
    "wt3d_fast_normal_spread",
    "wt3d_normal_slow_spread",
    "wt3d_slope",
    "wt3d_acceleration",
    "wt3d_bars_since_cross",
    "wt3d_reversal_intensity",
    "wt3d_mtf_agreement",
]
KNN_OUTPUT_COLUMNS = [
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
]


@dataclass(frozen=True, slots=True)
class RegimeDefinition:
    id: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class HmmSettings:
    n_states: int
    posterior_threshold: float
    entropy_threshold: float
    flip_cooldown_bars: int
    random_state: int
    max_iter: int
    covariance_type: str
    backend: str
    emission_features: list[str]


@dataclass(frozen=True, slots=True)
class Wt3dSettings:
    price_column: str
    fast_length: int
    normal_length: int
    slow_length: int
    slope_lag: int
    reversal_zone: float
    mtf_slow_window: int


@dataclass(frozen=True, slots=True)
class KnnSettings:
    distance: str
    k_values: list[int]
    primary_k: int
    neighbor_weighting: list[str]
    primary_weighting: str
    same_regime_only: bool
    allow_cross_regime_fallback: bool
    time_decay_half_life_bars: int
    min_neighbor_count: int
    vote_probability_threshold: float
    expected_value_threshold: float
    feature_columns: list[str]
    distance_backend: str = "cpu"
    feature_pack: str | None = None
    regime_match_mode: str | None = None
    compatible_regimes: dict[str, list[str]] | None = None


@dataclass(frozen=True, slots=True)
class LabelSettings:
    event_sampling: str
    label_column: str
    pnl_column: str
    horizons: list[str]
    primary_horizon: str
    include_mfe_mae: bool
    include_barrier_type: bool


@dataclass(frozen=True, slots=True)
class MetaModelSettings:
    backend: str
    fallback_backend: str
    probability_threshold: float
    random_state: int
    n_estimators: int
    max_depth: int
    learning_rate: float
    device: str = "cpu"
    tree_method: str = "hist"


@dataclass(frozen=True, slots=True)
class HmmKnnEvaluationSettings:
    walk_forward_splits: int
    train_fraction: float
    min_training_rows: int
    fee_bps: float
    slippage_bps: float
    funding_cost_enabled: bool
    purge_embargo_bars: int


@dataclass(frozen=True, slots=True)
class HmmKnnAcceptanceSettings:
    research_only: bool
    min_trade_count: int
    min_expectancy_after_cost: float
    max_single_split_pnl_share: float
    require_long_short_breakout: bool


@dataclass(frozen=True, slots=True)
class HmmKnnResearchPlan:
    version: str
    asset_scope: list[str]
    symbol: str
    dataset_path: str | None
    regimes: list[RegimeDefinition]
    hmm: HmmSettings
    wt3d: Wt3dSettings
    knn: KnnSettings
    labels: LabelSettings
    meta_model: MetaModelSettings
    evaluation: HmmKnnEvaluationSettings
    acceptance: HmmKnnAcceptanceSettings

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    def plan_sha256(self) -> str:
        return sha256(json.dumps(self.to_payload(), sort_keys=True).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HmmKnnResearchResult:
    output_dir: Path
    artifact_manifest_path: Path
    metrics_path: Path
    regime_posteriors_path: Path
    knn_predictions_path: Path
    meta_predictions_path: Path
    neighbor_diagnostics_path: Path


@dataclass(frozen=True, slots=True)
class RobustScalerState:
    columns: list[str]
    median: np.ndarray
    scale: np.ndarray

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        matrix = _numeric_feature_matrix(frame, self.columns)
        matrix = np.where(np.isnan(matrix), self.median.reshape(1, -1), matrix)
        return (matrix - self.median) / self.scale


def load_hmm_knn_plan(path: Path) -> HmmKnnResearchPlan:
    payload = json.loads(path.read_text(encoding="utf-8"))
    knn_payload = dict(payload["knn"])
    if knn_payload.get("feature_pack"):
        knn_payload["feature_columns"] = list(resolve_feature_columns(str(knn_payload["feature_pack"])))
    plan = HmmKnnResearchPlan(
        version=str(payload["version"]),
        asset_scope=[str(symbol).upper() for symbol in payload["asset_scope"]],
        symbol=str(payload["symbol"]).upper(),
        dataset_path=payload.get("dataset_path"),
        regimes=[RegimeDefinition(**item) for item in payload["regimes"]],
        hmm=HmmSettings(**payload["hmm"]),
        wt3d=Wt3dSettings(**payload["wt3d"]),
        knn=KnnSettings(**knn_payload),
        labels=LabelSettings(**payload["labels"]),
        meta_model=MetaModelSettings(**payload["meta_model"]),
        evaluation=HmmKnnEvaluationSettings(**payload["evaluation"]),
        acceptance=HmmKnnAcceptanceSettings(**payload["acceptance"]),
    )
    _validate_knn_settings(plan)
    return plan


def _validate_knn_settings(plan: HmmKnnResearchPlan) -> None:
    try:
        metric = resolve_distance_metric(plan.knn.distance)
    except ValueError as exc:
        raise ValueError(f"knn.distance must be one of: {', '.join(sorted(DISTANCE_FUNCTIONS))}") from exc
    if plan.knn.distance_backend not in {"cpu", "auto", "cupy"}:
        raise ValueError("knn.distance_backend must be one of: cpu, auto, cupy")
    if plan.knn.distance_backend not in metric.supports_backend:
        raise ValueError(f"knn.distance_backend {plan.knn.distance_backend} is not supported by {metric.id}")
    _resolved_knn_regime_match_mode(plan)
    if not plan.knn.k_values:
        raise ValueError("knn.k_values must contain at least one k value")
    if any(int(k) <= 0 for k in plan.knn.k_values):
        raise ValueError("knn.k_values must contain only positive integers")
    if int(plan.knn.primary_k) not in {int(k) for k in plan.knn.k_values}:
        raise ValueError("knn.primary_k must be included in knn.k_values")
    allowed_weighting = {"inverse_distance", "softmax"}
    configured_weighting = set(plan.knn.neighbor_weighting)
    if not configured_weighting or configured_weighting - allowed_weighting:
        raise ValueError("knn.neighbor_weighting must contain only inverse_distance or softmax")
    if plan.knn.primary_weighting not in configured_weighting:
        raise ValueError("knn.primary_weighting must be included in knn.neighbor_weighting")


def _resolved_knn_regime_match_mode(plan: HmmKnnResearchPlan) -> str:
    return resolve_regime_match_mode(
        regime_match_mode=plan.knn.regime_match_mode,
        same_regime_only=bool(plan.knn.same_regime_only),
        allow_cross_regime_fallback=bool(plan.knn.allow_cross_regime_fallback),
    )


def _numeric_feature_matrix(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    matrix_frame = frame.reindex(columns=columns).apply(pd.to_numeric, errors="coerce")
    matrix = matrix_frame.to_numpy(dtype=float, copy=True)
    matrix[~np.isfinite(matrix)] = np.nan
    return matrix


def _nan_stat_by_column(matrix: np.ndarray, statistic: str) -> np.ndarray:
    values: list[float] = []
    for column_index in range(matrix.shape[1]):
        column = matrix[:, column_index]
        column = column[np.isfinite(column)]
        if len(column) == 0:
            values.append(0.0)
        elif statistic == "median":
            values.append(float(np.median(column)))
        elif statistic == "q75":
            values.append(float(np.percentile(column, 75)))
        elif statistic == "q25":
            values.append(float(np.percentile(column, 25)))
        else:  # pragma: no cover - internal guard
            raise ValueError(f"unsupported statistic {statistic}")
    return np.asarray(values, dtype=float)


def robust_scaler_fit(frame: pd.DataFrame, columns: list[str]) -> RobustScalerState:
    matrix = _numeric_feature_matrix(frame, columns)
    median = _nan_stat_by_column(matrix, "median")
    q75 = _nan_stat_by_column(matrix, "q75")
    q25 = _nan_stat_by_column(matrix, "q25")
    scale = q75 - q25
    if np.any(~np.isfinite(scale)) or np.any(scale <= 0):
        scale = np.where(np.isfinite(scale) & (scale > 0), scale, 1.0)
    return RobustScalerState(columns=list(columns), median=median, scale=scale)


def _import_cupy() -> Any | None:
    try:
        return importlib.import_module("cupy")
    except Exception:
        return None


def _cupy_lorentzian_smoke(cupy: Any) -> None:
    sample = cupy.asarray([[0.0, 1.0]], dtype=float)
    result = cupy.log1p(cupy.abs(sample)).sum(axis=1)
    if hasattr(cupy, "asnumpy"):
        cupy.asnumpy(result)
    elif hasattr(result, "get"):
        result.get()


def _resolve_lorentzian_distance_backend(requested_backend: str) -> str:
    requested = str(requested_backend or "cpu").strip().lower()
    if requested not in {"cpu", "auto", "cupy"}:
        raise ValueError("knn.distance_backend must be one of: cpu, auto, cupy")
    if requested == "cpu":
        return "cpu"
    cupy = _import_cupy()
    if cupy is None:
        if requested == "auto":
            return "cpu"
        raise RuntimeError("CuPy Lorentzian backend requested, but cupy is not importable")
    try:
        _cupy_lorentzian_smoke(cupy)
    except Exception as exc:
        if requested == "auto":
            return "cpu"
        raise RuntimeError("CuPy Lorentzian backend requested, but a CuPy smoke test failed") from exc
    return "cupy"


def _cupy_available() -> bool:
    return _resolve_lorentzian_distance_backend("auto") == "cupy"


def _knn_distance_backend_report(requested_backend: str) -> dict[str, Any]:
    requested = str(requested_backend or "cpu").strip().lower()
    try:
        resolved = _resolve_lorentzian_distance_backend(requested)
        error = None
    except RuntimeError as exc:
        resolved = "unavailable"
        error = str(exc)
    return {
        "knn_distance_backend_requested": requested,
        "knn_distance_backend": resolved,
        "cupy_available": resolved == "cupy" if requested == "auto" else _cupy_available(),
        "cupy_error": error,
    }


def _numpy_lorentzian_distance_matrix(query: np.ndarray, train: np.ndarray, scales: np.ndarray) -> np.ndarray:
    diff = np.abs(query[:, None, :] - train[None, :, :]) / scales.reshape(1, 1, -1)
    return np.log1p(diff).sum(axis=2)


def _cupy_lorentzian_distance_matrix(query: np.ndarray, train: np.ndarray, scales: np.ndarray, cupy: Any) -> np.ndarray:
    query_gpu = cupy.asarray(query, dtype=float)
    train_gpu = cupy.asarray(train, dtype=float)
    scales_gpu = cupy.asarray(scales, dtype=float)
    diff = cupy.abs(query_gpu[:, None, :] - train_gpu[None, :, :]) / scales_gpu.reshape(1, 1, -1)
    distances = cupy.log1p(diff).sum(axis=2)
    if hasattr(cupy, "asnumpy"):
        return np.asarray(cupy.asnumpy(distances), dtype=float)
    if hasattr(distances, "get"):
        return np.asarray(distances.get(), dtype=float)
    return np.asarray(distances, dtype=float)


def lorentzian_distance_matrix(
    query: np.ndarray,
    train: np.ndarray,
    scales: np.ndarray | None = None,
    *,
    backend: str = "cpu",
) -> np.ndarray:
    query = np.asarray(query, dtype=float)
    train = np.asarray(train, dtype=float)
    if query.ndim == 1:
        query = query.reshape(1, -1)
    if train.ndim != 2 or query.ndim != 2 or query.shape[1] != train.shape[1]:
        raise ValueError("query and train matrices must be 2-D with matching feature counts")
    if scales is None:
        scales = np.ones(train.shape[1], dtype=float)
    scales = np.asarray(scales, dtype=float)
    if scales.ndim != 1 or len(scales) != train.shape[1] or np.any(~np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError("Lorentzian scales must be finite positive values for every feature")
    requested = str(backend or "cpu").strip().lower()
    if requested not in {"cpu", "auto", "cupy"}:
        raise ValueError("knn.distance_backend must be one of: cpu, auto, cupy")
    if requested == "cpu":
        return _numpy_lorentzian_distance_matrix(query, train, scales)
    cupy = _import_cupy()
    if cupy is None:
        if requested == "auto":
            return _numpy_lorentzian_distance_matrix(query, train, scales)
        raise RuntimeError("CuPy Lorentzian backend requested, but cupy is not importable")
    try:
        return _cupy_lorentzian_distance_matrix(query, train, scales, cupy)
    except Exception as exc:
        if requested == "auto":
            return _numpy_lorentzian_distance_matrix(query, train, scales)
        raise RuntimeError("CuPy Lorentzian backend requested, but distance calculation failed") from exc


def build_wt3d_features(frame: pd.DataFrame, settings: Wt3dSettings) -> pd.DataFrame:
    price_column = settings.price_column if settings.price_column in frame.columns else "entry_price"
    if price_column not in frame.columns:
        price = pd.Series(np.arange(len(frame), dtype=float), index=frame.index)
    else:
        price = frame[price_column].astype(float).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)

    def oscillator(length: int) -> pd.Series:
        length = max(int(length), 2)
        basis = price.ewm(span=length, adjust=False, min_periods=1).mean()
        deviation = (price - basis).abs().ewm(span=length, adjust=False, min_periods=1).mean()
        raw = (price - basis) / deviation.replace(0.0, np.nan)
        return np.tanh(raw.fillna(0.0) / 3.0)

    features = pd.DataFrame(index=frame.index)
    features["wt3d_fast"] = oscillator(settings.fast_length)
    features["wt3d_normal"] = oscillator(settings.normal_length)
    features["wt3d_slow"] = oscillator(settings.slow_length)
    features["wt3d_fast_normal_spread"] = features["wt3d_fast"] - features["wt3d_normal"]
    features["wt3d_normal_slow_spread"] = features["wt3d_normal"] - features["wt3d_slow"]
    lag = max(int(settings.slope_lag), 1)
    features["wt3d_slope"] = features["wt3d_normal"].diff(lag).fillna(0.0)
    features["wt3d_acceleration"] = features["wt3d_slope"].diff(lag).fillna(0.0).clip(-2.0, 2.0)
    cross = np.sign(features["wt3d_fast_normal_spread"]).diff().fillna(0.0).ne(0.0)
    bars_since_cross: list[int] = []
    last_cross: int | None = None
    for row_index, crossed in enumerate(cross.tolist()):
        if bool(crossed):
            last_cross = row_index
            bars_since_cross.append(0)
        elif last_cross is None:
            bars_since_cross.append(row_index + 1)
        else:
            bars_since_cross.append(row_index - last_cross)
    features["wt3d_bars_since_cross"] = bars_since_cross
    zone = max(float(settings.reversal_zone), 0.01)
    features["wt3d_reversal_intensity"] = (features["wt3d_normal"].abs() - zone).clip(lower=0.0)
    slow_context = features["wt3d_slow"].rolling(max(int(settings.mtf_slow_window), 1), min_periods=1).mean().shift(1).fillna(0.0)
    features["wt3d_mtf_agreement"] = np.sign(features["wt3d_normal"]) * np.sign(slow_context)
    return features.loc[:, WT3D_FEATURE_COLUMNS]


class RegimeModel:
    def __init__(self, *, backend: str, model: Any, n_states: int, state_labels: dict[int, str]):
        self.backend = backend
        self.model = model
        self.n_states = n_states
        self.state_labels = state_labels

    def posterior(self, matrix: np.ndarray) -> np.ndarray:
        if len(matrix) == 0:
            return np.empty((0, self.n_states))
        if self.backend == "hmmlearn":
            return _normalize_posterior(self._hmm_online_posterior(matrix), self.n_states)
        probabilities = self.model.predict_proba(matrix)
        return _normalize_posterior(probabilities, self.n_states)

    def _hmm_online_posterior(self, matrix: np.ndarray) -> np.ndarray:
        log_likelihood = self.model._compute_log_likelihood(matrix)
        start = np.asarray(self.model.startprob_, dtype=float)
        trans = np.asarray(self.model.transmat_, dtype=float)
        alpha = start / max(start.sum(), 1e-12)
        rows: list[np.ndarray] = []
        for row in log_likelihood:
            emission = np.exp(row - np.max(row))
            alpha = alpha * emission
            alpha = alpha / max(alpha.sum(), 1e-12)
            rows.append(alpha.copy())
            alpha = alpha @ trans
            alpha = alpha / max(alpha.sum(), 1e-12)
        return np.vstack(rows)


def _normalize_posterior(probabilities: np.ndarray, n_states: int) -> np.ndarray:
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.ndim != 2:
        raise ValueError("regime posterior probabilities must be a 2-D matrix")
    if probabilities.shape[1] < n_states:
        padded = np.zeros((len(probabilities), n_states), dtype=float)
        padded[:, : probabilities.shape[1]] = probabilities
        probabilities = padded
    elif probabilities.shape[1] > n_states:
        probabilities = probabilities[:, :n_states]
    probabilities = np.where(np.isfinite(probabilities), probabilities, 0.0)
    row_sums = probabilities.sum(axis=1, keepdims=True)
    uncertain = row_sums[:, 0] <= 0.0
    if uncertain.any():
        probabilities[uncertain, :] = 1.0 / max(n_states, 1)
        row_sums = probabilities.sum(axis=1, keepdims=True)
    return probabilities / np.maximum(row_sums, 1e-12)


def _fit_regime_model(train_matrix: np.ndarray, train_frame: pd.DataFrame, plan: HmmKnnResearchPlan) -> RegimeModel:
    n_states = min(max(int(plan.hmm.n_states), 1), max(len(train_matrix), 1))
    requested = plan.hmm.backend
    if requested == "deterministic_rule_baseline":
        model = _DeterministicMatrixRegimeModel(n_states=n_states)
        posterior = model.predict_proba(train_matrix)
        state_labels = _label_states(train_frame, posterior, n_states, plan)
        return RegimeModel(backend="deterministic_rule_baseline", model=model, n_states=n_states, state_labels=state_labels)
    use_hmmlearn = requested in {"auto", "hmmlearn"} and GaussianHMM is not None and len(train_matrix) >= n_states * 3
    if use_hmmlearn:
        model = GaussianHMM(
            n_components=n_states,
            covariance_type=plan.hmm.covariance_type,
            n_iter=plan.hmm.max_iter,
            random_state=plan.hmm.random_state,
        )
        model.fit(train_matrix)
        backend = "hmmlearn"
        posterior = RegimeModel(backend=backend, model=model, n_states=n_states, state_labels={}).posterior(train_matrix)
    else:
        model = GaussianMixture(n_components=n_states, covariance_type="diag", random_state=plan.hmm.random_state, max_iter=plan.hmm.max_iter)
        model.fit(train_matrix)
        backend = "gaussian_mixture_fallback"
        posterior = model.predict_proba(train_matrix)
    state_labels = _label_states(train_frame, posterior, n_states, plan)
    return RegimeModel(backend=backend, model=model, n_states=n_states, state_labels=state_labels)


class _DeterministicMatrixRegimeModel:
    def __init__(self, *, n_states: int):
        self.n_states = int(n_states)

    def predict_proba(self, matrix: np.ndarray) -> np.ndarray:
        matrix = np.asarray(matrix, dtype=float)
        posterior = np.zeros((len(matrix), self.n_states), dtype=float)
        if len(matrix) == 0:
            return posterior
        slope = matrix[:, 0] if matrix.shape[1] else np.zeros(len(matrix))
        vol = matrix[:, 2] if matrix.shape[1] > 2 else np.zeros(len(matrix))
        for row_index, (slope_value, vol_value) in enumerate(zip(slope, vol, strict=False)):
            if self.n_states == 1:
                state = 0
            elif vol_value >= 1.5 and self.n_states >= 4:
                state = 3
            elif slope_value >= 0.0 and self.n_states >= 2:
                state = 1
            elif self.n_states >= 3:
                state = 2
            else:
                state = 0
            posterior[row_index, min(state, self.n_states - 1)] = 1.0
        return posterior


def _label_states(train_frame: pd.DataFrame, posterior: np.ndarray, n_states: int, plan: HmmKnnResearchPlan) -> dict[int, str]:
    hard_state = posterior.argmax(axis=1) if len(posterior) else np.array([], dtype=int)
    stats: list[dict[str, float]] = []
    for state in range(n_states):
        rows = train_frame.iloc[np.where(hard_state == state)[0]]
        stats.append(
            {
                "state": state,
                "slope": float(rows.get("directional_slope_atr", pd.Series([0.0])).astype(float).mean()) if len(rows) else 0.0,
                "vol": float(rows.get("realized_volatility", pd.Series([0.0])).astype(float).mean()) if len(rows) else 0.0,
                "chop": float(rows.get("choppiness", pd.Series([50.0])).astype(float).mean()) if len(rows) else 50.0,
            }
        )
    labels = {state: plan.regimes[min(state, len(plan.regimes) - 1)].name for state in range(n_states)}
    if n_states >= 4:
        shock = max(stats, key=lambda item: (item["vol"], item["chop"], -item["state"]))["state"]
        bull = max((item for item in stats if item["state"] != shock), key=lambda item: (item["slope"], -item["state"]))["state"]
        bear = min((item for item in stats if item["state"] not in {shock, bull}), key=lambda item: (item["slope"], item["state"]))["state"]
        for item in stats:
            if item["state"] not in {shock, bull, bear}:
                labels[item["state"]] = "range_chop"
        labels[shock] = "shock_transition"
        labels[bull] = "bull_trend"
        labels[bear] = "bear_trend"
    return labels


def _posterior_frame(
    *,
    base_frame: pd.DataFrame,
    posterior: np.ndarray,
    model: RegimeModel,
    plan: HmmKnnResearchPlan,
    split_index: int,
    fit_end_index: int,
) -> pd.DataFrame:
    top_state = posterior.argmax(axis=1) if len(posterior) else np.array([], dtype=int)
    top_probability = posterior.max(axis=1) if len(posterior) else np.array([], dtype=float)
    safe_posterior = np.clip(posterior, 1e-12, 1.0)
    entropy = -np.sum(safe_posterior * np.log(safe_posterior), axis=1) / math.log(max(model.n_states, 2))
    recent_flip = np.zeros(len(base_frame), dtype=bool)
    last_flip: int | None = None
    for idx in range(1, len(top_state)):
        if top_state[idx] != top_state[idx - 1]:
            last_flip = idx
        if last_flip is not None and idx - last_flip <= plan.hmm.flip_cooldown_bars:
            recent_flip[idx] = True
    result = base_frame.loc[:, [column for column in ("signal_id", "symbol", "direction", "signal_bar_time_ms") if column in base_frame.columns]].copy()
    for state in range(model.n_states):
        result[f"regime_p_{state}"] = posterior[:, state]
    result["top_regime"] = top_state
    result["top_regime_label"] = [model.state_labels.get(int(state), f"state_{state}") for state in top_state]
    result["max_regime_probability"] = top_probability
    result["posterior_entropy"] = entropy
    result["recent_regime_flip"] = recent_flip
    result["regime_no_trade"] = (
        (result["max_regime_probability"] < plan.hmm.posterior_threshold)
        | (result["posterior_entropy"] > plan.hmm.entropy_threshold)
        | result["recent_regime_flip"].astype(bool)
    )
    result["regime_model_backend"] = model.backend
    result["walk_forward_split"] = split_index
    result["source_row_index"] = base_frame.index.astype(int)
    result["hmm_fit_end_row"] = fit_end_index
    return result


def _knn_combinations(plan: HmmKnnResearchPlan, *, include_sweep: bool) -> list[tuple[int, str]]:
    if not include_sweep:
        return [(int(plan.knn.primary_k), plan.knn.primary_weighting)]
    return [(int(k), weighting) for k in plan.knn.k_values for weighting in plan.knn.neighbor_weighting]


def _neighbor_weights(
    distances: np.ndarray,
    indices: np.ndarray,
    current_index: int,
    plan: HmmKnnResearchPlan,
    weighting: str,
) -> np.ndarray:
    if weighting == "softmax":
        base = np.exp(-(distances - distances.min()))
    else:
        base = 1.0 / np.maximum(distances, 1e-9)
    half_life = max(int(plan.knn.time_decay_half_life_bars), 1)
    age = np.maximum(current_index - indices, 0)
    decay = np.power(0.5, age / half_life)
    weights = base * decay
    total = weights.sum()
    return weights / total if total > 0 else np.full(len(weights), 1.0 / max(len(weights), 1))


def _knn_predict(
    *,
    train_matrix: np.ndarray,
    test_matrix: np.ndarray,
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    train_regimes: pd.Series,
    test_regimes: pd.Series,
    train_regime_labels: pd.Series | None = None,
    test_regime_labels: pd.Series | None = None,
    plan: HmmKnnResearchPlan,
    include_sweep: bool = True,
    distance_backend: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = train_frame[plan.labels.label_column].astype(float).to_numpy()
    pnl = train_frame[plan.labels.pnl_column].astype(float).to_numpy()
    train_indices = train_frame.index.to_numpy(dtype=int)
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    sweep_rows: list[dict[str, Any]] = []
    regime_match_mode = _resolved_knn_regime_match_mode(plan)
    train_regime_values = train_regimes.astype(int).to_numpy()
    train_regime_label_values = train_regime_labels.astype(str).to_numpy() if train_regime_labels is not None else None
    resolved_distance_backend = distance_backend or _resolve_lorentzian_distance_backend(plan.knn.distance_backend)
    distance_metric = resolve_distance_metric(plan.knn.distance)
    if distance_metric.id == "lorentzian":
        distance_matrix = lorentzian_distance_matrix(test_matrix, train_matrix, backend=resolved_distance_backend)
    else:
        distance_matrix = distance_metric.function(test_matrix, train_matrix, None)
    combinations = _knn_combinations(plan, include_sweep=include_sweep)
    effective_same_regime_only = _effective_same_regime_only(regime_match_mode)
    for local_index, (_, test_row) in enumerate(test_frame.iterrows()):
        current_regime = int(test_regimes.iloc[local_index])
        current_regime_label = (
            str(test_regime_labels.iloc[local_index])
            if test_regime_labels is not None and not pd.isna(test_regime_labels.iloc[local_index])
            else None
        )
        pool = build_neighbor_pool(
            train_regimes=train_regime_values,
            train_regime_labels=train_regime_label_values,
            query_regime=current_regime,
            query_regime_label=current_regime_label,
            regime_match_mode=regime_match_mode,
            compatible_regimes=plan.knn.compatible_regimes or {},
        )
        primary_row: dict[str, Any] | None = None
        for k, weighting in combinations:
            is_primary = k == int(plan.knn.primary_k) and weighting == plan.knn.primary_weighting
            selected_positions, selected_distances = select_neighbor_positions(
                distance_matrix[local_index],
                candidate_positions=pool.candidate_positions,
                k=k,
            )
            pool_diagnostics = pool.diagnostics.with_selected_count(len(selected_positions))
            pool_payload = _knn_pool_payload(pool_diagnostics)
            if len(pool.candidate_positions) == 0:
                row = _empty_knn_row(test_row, reason=pool.diagnostics.skip_reason or "no_neighbors")
            elif len(selected_positions) < plan.knn.min_neighbor_count:
                row = _empty_knn_row(test_row, reason="insufficient_neighbors", neighbor_count=len(selected_positions))
            else:
                weights = _neighbor_weights(selected_distances, train_indices[selected_positions], int(test_row.name), plan, weighting)
                p_up = float(np.dot(weights, labels[selected_positions]))
                p_down = 1.0 - p_up
                gross_expected = float(np.dot(weights, pnl[selected_positions]))
                funding_cost = _funding_cost(test_row, plan)
                expected_net = gross_expected - ((plan.evaluation.fee_bps + plan.evaluation.slippage_bps) / 10000.0) - funding_cost
                agreement = max(p_up, p_down)
                quality = 1.0 / (1.0 + float(np.average(selected_distances, weights=weights)))
                accepted = (
                    p_up >= plan.knn.vote_probability_threshold
                    and expected_net >= plan.knn.expected_value_threshold
                    and agreement >= plan.knn.vote_probability_threshold
                )
                row = {
                    **_identity_payload(test_row),
                    "p_up_barrier": p_up,
                    "p_down_barrier": p_down,
                    "expected_net_return_after_costs": expected_net,
                    "neighbor_agreement": agreement,
                    "neighbor_distance_quality": quality,
                    "neighbor_count": int(len(selected_positions)),
                    "neighbor_min_source_index": int(train_indices[selected_positions].min()),
                    "neighbor_max_source_index": int(train_indices[selected_positions].max()),
                    "knn_vote_margin": abs(p_up - 0.5) * 2.0,
                    "accepted_by_knn": bool(accepted),
                    "knn_skip_reason": None,
                }
                for rank, (position, distance, weight) in enumerate(zip(selected_positions[:10], selected_distances[:10], weights[:10], strict=False), start=1):
                    diagnostics.append(
                        {
                            **_identity_payload(test_row),
                            **pool_payload,
                            "k": int(k),
                            "weighting": weighting,
                            "is_primary": bool(is_primary),
                            "same_regime_only": bool(effective_same_regime_only),
                            "configured_same_regime_only": bool(plan.knn.same_regime_only),
                            "knn_skip_reason": None,
                            "source_row_index": int(test_row.name),
                            "neighbor_rank": rank,
                            "neighbor_source_index": int(train_indices[position]),
                            "neighbor_distance": float(distance),
                            "neighbor_distance_quality": quality,
                            "neighbor_weight": float(weight),
                            "neighbor_label_accept": float(labels[position]),
                            "neighbor_label_pnl_multiple": float(pnl[position]),
                            "neighbor_regime": int(train_regimes.iloc[position]),
                        }
                    )
            row = {**row, **pool_payload}
            sweep_row = {
                **row,
                "k": int(k),
                "weighting": weighting,
                "is_primary": bool(is_primary),
                "same_regime_only": bool(effective_same_regime_only),
                "configured_same_regime_only": bool(plan.knn.same_regime_only),
                "source_row_index": int(test_row.name),
                plan.labels.label_column: test_row.get(plan.labels.label_column),
                plan.labels.pnl_column: test_row.get(plan.labels.pnl_column),
                "gross_return": test_row.get("gross_return", test_row.get(plan.labels.pnl_column)),
                "funding_paid_or_received": test_row.get("funding_paid_or_received", -_funding_cost(test_row, plan)),
            }
            sweep_rows.append(sweep_row)
            if row["knn_skip_reason"] is not None:
                diagnostics.append(
                    {
                        **_identity_payload(test_row),
                        **pool_payload,
                        "k": int(k),
                        "weighting": weighting,
                        "is_primary": bool(is_primary),
                        "same_regime_only": bool(effective_same_regime_only),
                        "configured_same_regime_only": bool(plan.knn.same_regime_only),
                        "knn_skip_reason": row["knn_skip_reason"],
                        "source_row_index": int(test_row.name),
                        "neighbor_rank": None,
                        "neighbor_source_index": None,
                        "neighbor_distance": None,
                        "neighbor_distance_quality": None,
                        "neighbor_weight": None,
                        "neighbor_label_accept": None,
                        "neighbor_label_pnl_multiple": None,
                        "neighbor_regime": None,
                    }
                )
            if is_primary:
                primary_row = row
        rows.append(primary_row or _empty_knn_row(test_row, reason="primary_combination_not_evaluated"))
    return pd.DataFrame(rows), pd.DataFrame(diagnostics), pd.DataFrame(sweep_rows)


def _knn_pool_payload(diagnostics: Any) -> dict[str, Any]:
    payload = diagnostics.to_payload()
    payload["selected_neighbor_count"] = payload.pop("selected_count")
    payload["neighbor_pool_skip_reason"] = payload.pop("skip_reason")
    return payload


def _effective_same_regime_only(regime_match_mode: str) -> bool:
    return regime_match_mode in {"same", "same_with_all_fallback"}


def _feature_set_variant_payload(*, plan: HmmKnnResearchPlan, dataset: pd.DataFrame) -> dict[str, Any]:
    missingness_columns = sorted(column for column in dataset.columns if column.startswith("missing_"))
    variant_id = plan.knn.feature_pack or "inline_feature_columns"
    payload = {
        "feature_set_variant_id": variant_id,
        "feature_set_source": "registered_feature_pack" if plan.knn.feature_pack else "inline_config",
        "feature_pack": plan.knn.feature_pack,
        "feature_columns": list(plan.knn.feature_columns),
        "feature_count": int(len(plan.knn.feature_columns)),
        "wt3d_enabled": any(column.startswith("wt3d_") for column in plan.knn.feature_columns),
        "missingness_columns_present": missingness_columns,
    }
    identity_payload = {
        "feature_pack": payload["feature_pack"],
        "feature_columns": payload["feature_columns"],
        "missingness_columns_present": missingness_columns,
    }
    payload["feature_set_variant_sha256"] = sha256(json.dumps(identity_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def _identity_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "signal_id": row.get("signal_id"),
        "symbol": row.get("symbol"),
        "direction": row.get("direction"),
        "signal_bar_time_ms": int(row.get("signal_bar_time_ms", 0)),
    }


def _empty_knn_row(row: pd.Series, *, reason: str, neighbor_count: int = 0) -> dict[str, Any]:
    return {
        **_identity_payload(row),
        "p_up_barrier": 0.5,
        "p_down_barrier": 0.5,
        "expected_net_return_after_costs": 0.0,
        "neighbor_agreement": 0.0,
        "neighbor_distance_quality": 0.0,
        "neighbor_count": int(neighbor_count),
        "neighbor_min_source_index": None,
        "neighbor_max_source_index": None,
        "knn_vote_margin": 0.0,
        "accepted_by_knn": False,
        "knn_skip_reason": reason,
    }


def _funding_cost(row: pd.Series, plan: HmmKnnResearchPlan) -> float:
    if not plan.evaluation.funding_cost_enabled or "funding_rate" not in row:
        return 0.0
    try:
        funding_rate = float(row.get("funding_rate") or 0.0)
    except (TypeError, ValueError):
        return 0.0
    direction_sign = 1.0 if str(row.get("direction", "")).lower() == "long" or float(row.get("direction_long", 0.0)) >= 0.5 else -1.0
    horizon_hours = _horizon_hours(plan.labels.primary_horizon)
    return direction_sign * funding_rate * (horizon_hours / 8.0)


def _horizon_hours(value: str) -> float:
    lowered = value.strip().lower()
    if lowered.endswith("h"):
        return float(lowered[:-1])
    if lowered.endswith("d"):
        return float(lowered[:-1]) * 24.0
    return 24.0


def _fit_meta_model(train_frame: pd.DataFrame, feature_columns: list[str], labels: pd.Series, plan: HmmKnnResearchPlan) -> tuple[Any, str]:
    if labels.nunique() < 2:
        return _ConstantProbabilityModel(float(labels.mean() if len(labels) else 0.0)), "constant"
    if plan.meta_model.backend == "xgboost" and XGBClassifier is not None:
        device = _resolve_xgboost_device(plan)
        model = XGBClassifier(
            n_estimators=plan.meta_model.n_estimators,
            max_depth=plan.meta_model.max_depth,
            learning_rate=plan.meta_model.learning_rate,
            random_state=plan.meta_model.random_state,
            eval_metric="logloss",
            tree_method=plan.meta_model.tree_method,
            device=device,
        )
        backend = "xgboost_cuda" if device == "cuda" else "xgboost"
    else:
        model = RandomForestClassifier(
            n_estimators=plan.meta_model.n_estimators,
            max_depth=plan.meta_model.max_depth,
            random_state=plan.meta_model.random_state,
            class_weight="balanced",
        )
        backend = "random_forest_fallback"
    model.fit(train_frame.reindex(columns=feature_columns, fill_value=0.0).fillna(0.0).astype(float), labels.astype(int))
    return model, backend


def _resolve_xgboost_device(plan: HmmKnnResearchPlan) -> str:
    requested = str(getattr(plan.meta_model, "device", "cpu") or "cpu").strip().lower()
    if requested == "auto":
        return "cuda" if _xgboost_cuda_dependency_report()["xgboost_cuda_available"] else "cpu"
    if requested in {"cuda", "gpu"}:
        return "cuda"
    return "cpu"


def _xgboost_cuda_dependency_report() -> dict[str, Any]:
    if XGBClassifier is None or _xgboost is None:
        return {
            "xgboost_cuda_available": False,
            "xgboost_cuda_detection": "xgboost_unavailable",
        }
    build_info_func = getattr(_xgboost, "build_info", None)
    if not callable(build_info_func):
        return {
            "xgboost_cuda_available": False,
            "xgboost_cuda_detection": "build_info_unavailable",
        }
    try:
        build_info = dict(build_info_func() or {})
    except Exception as exc:  # pragma: no cover - defensive optional dependency guard
        return {
            "xgboost_cuda_available": False,
            "xgboost_cuda_detection": "build_info_error",
            "xgboost_cuda_error": str(exc),
        }
    cuda_keys = {
        str(key): value
        for key, value in build_info.items()
        if "CUDA" in str(key).upper() or "NCCL" in str(key).upper()
    }
    cuda_available = any(
        _xgboost_build_info_value_enabled(value)
        for key, value in cuda_keys.items()
        if key.upper() in {"USE_CUDA", "USE_NCCL"} or "CUDA" in key.upper()
    )
    report: dict[str, Any] = {
        "xgboost_cuda_available": bool(cuda_available),
        "xgboost_cuda_detection": "build_info",
    }
    if cuda_keys:
        report["xgboost_cuda_build_info"] = cuda_keys
    return report


def _xgboost_build_info_value_enabled(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized not in {"", "0", "false", "off", "no", "none", "disabled", "not_found", "unknown"}
    return bool(value)


def _leakage_safe_meta_knn_features(
    *,
    train_frame: pd.DataFrame,
    train_posterior: pd.DataFrame,
    feature_scaler: RobustScalerState,
    plan: HmmKnnResearchPlan,
) -> pd.DataFrame:
    full_matrix = feature_scaler.transform(train_frame)
    rows: list[dict[str, Any]] = []
    embargo = max(int(plan.evaluation.purge_embargo_bars), 0)
    for local_index, (_, row) in enumerate(train_frame.iterrows()):
        candidate_end = max(local_index - embargo, 0)
        if candidate_end <= 0:
            payload = _empty_knn_row(row, reason="insufficient_meta_training_history")
            payload["meta_knn_oof_available"] = False
            rows.append(payload)
            continue
        knn_frame, _, _ = _knn_predict(
            train_matrix=full_matrix[:candidate_end],
            test_matrix=full_matrix[local_index : local_index + 1],
            train_frame=train_frame.iloc[:candidate_end],
            test_frame=train_frame.iloc[[local_index]],
            train_regimes=train_posterior["top_regime"].iloc[:candidate_end],
            test_regimes=train_posterior["top_regime"].iloc[[local_index]],
            train_regime_labels=(
                train_posterior["top_regime_label"].iloc[:candidate_end]
                if "top_regime_label" in train_posterior.columns
                else None
            ),
            test_regime_labels=(
                train_posterior["top_regime_label"].iloc[[local_index]]
                if "top_regime_label" in train_posterior.columns
                else None
            ),
            plan=plan,
            include_sweep=False,
        )
        payload = knn_frame.iloc[0].to_dict()
        payload["meta_knn_oof_available"] = payload.get("knn_skip_reason") is None
        rows.append(payload)
    result = pd.DataFrame(rows)
    result["meta_knn_feature_source"] = "prior_train_rows_with_embargo"
    return result


def _meta_training_summary(train_meta_frame: pd.DataFrame, backend: str, plan: HmmKnnResearchPlan) -> dict[str, Any]:
    valid_mask = train_meta_frame.get("meta_knn_oof_available", pd.Series([False] * len(train_meta_frame))).astype(bool)
    labels = train_meta_frame[plan.labels.label_column].astype(int) if plan.labels.label_column in train_meta_frame else pd.Series(dtype=int)
    return {
        "row_count": int(len(train_meta_frame)),
        "oof_knn_available_rows": int(valid_mask.sum()),
        "oof_knn_unavailable_rows": int((~valid_mask).sum()) if len(valid_mask) else 0,
        "label_class_count": int(labels.nunique()) if len(labels) else 0,
        "label_positive_count": int((labels == 1).sum()) if len(labels) else 0,
        "label_negative_count": int((labels == 0).sum()) if len(labels) else 0,
        "backend": backend,
    }


class _ConstantProbabilityModel:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, matrix: Any) -> np.ndarray:
        count = len(matrix)
        positive = np.full(count, self.probability)
        return np.column_stack([1.0 - positive, positive])


def _prepare_dataset(dataset_path: Path, plan: HmmKnnResearchPlan) -> pd.DataFrame:
    frame = pd.read_parquet(dataset_path).sort_values("signal_bar_time_ms").reset_index(drop=True)
    if plan.symbol not in set(frame["symbol"].astype(str).str.upper()):
        raise ValueError(f"dataset does not contain configured symbol {plan.symbol}")
    frame = frame.loc[frame["symbol"].astype(str).str.upper() == plan.symbol].reset_index(drop=True)
    if plan.labels.label_column not in frame.columns or plan.labels.pnl_column not in frame.columns:
        raise ValueError("dataset must contain label_accept and label_pnl_multiple compatible columns")
    wt3d = build_wt3d_features(frame, plan.wt3d)
    for column in wt3d.columns:
        frame[column] = wt3d[column]
    frame["hmm_knn_feature_version"] = HMM_KNN_FEATURE_VERSION
    if "gross_return" not in frame.columns:
        frame["gross_return"] = frame[plan.labels.pnl_column].astype(float)
    if "fees_bps" not in frame.columns:
        frame["fees_bps"] = float(plan.evaluation.fee_bps)
    if "slippage_bps" not in frame.columns:
        frame["slippage_bps"] = float(plan.evaluation.slippage_bps)
    if "funding_paid_or_received" not in frame.columns:
        frame["funding_paid_or_received"] = frame.apply(lambda row: -_funding_cost(row, plan), axis=1)
    gross_return = pd.to_numeric(frame["gross_return"], errors="coerce").fillna(0.0)
    fees_bps = pd.to_numeric(frame["fees_bps"], errors="coerce").fillna(float(plan.evaluation.fee_bps))
    slippage_bps = pd.to_numeric(frame["slippage_bps"], errors="coerce").fillna(float(plan.evaluation.slippage_bps))
    funding_paid_or_received = pd.to_numeric(frame["funding_paid_or_received"], errors="coerce").fillna(0.0)
    frame["realized_net_return_after_costs"] = (
        gross_return
        - ((fees_bps + slippage_bps) / 10000.0)
        + funding_paid_or_received
    )
    if "time_in_trade" not in frame.columns:
        frame["time_in_trade"] = pd.Series([None] * len(frame))
    if "max_adverse_excursion" not in frame.columns:
        frame["max_adverse_excursion"] = pd.Series([None] * len(frame))
    if "max_favorable_excursion" not in frame.columns:
        frame["max_favorable_excursion"] = pd.Series([None] * len(frame))
    if "barrier_hit_type" not in frame.columns:
        frame["barrier_hit_type"] = frame.get("label_exit_reason", pd.Series(["unknown"] * len(frame)))
    return frame


def _resolve_dataset_path(plan: HmmKnnResearchPlan, output_dir: Path, explicit_dataset_path: Path | None) -> Path:
    if explicit_dataset_path is not None:
        return explicit_dataset_path
    if plan.dataset_path:
        return Path(plan.dataset_path)
    candidates = sorted(output_dir.rglob(f"{plan.symbol.lower()}_dataset.parquet"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(
            f"no {plan.symbol.lower()}_dataset.parquet found under {output_dir}; run build-dataset or pass --dataset"
        )
    return candidates[0]


def run_hmm_knn_research(
    *,
    config_path: Path,
    output_dir: Path,
    dataset_path: Path | None = None,
) -> HmmKnnResearchResult:
    plan = load_hmm_knn_plan(config_path)
    resolved_dataset_path = _resolve_dataset_path(plan, output_dir, dataset_path)
    frame = _prepare_dataset(resolved_dataset_path, plan)
    if len(frame) < plan.evaluation.min_training_rows + plan.evaluation.walk_forward_splits:
        raise ValueError("dataset is too small for HMM/KNN walk-forward research")

    output_path = output_dir / plan.version
    output_path.mkdir(parents=True, exist_ok=True)
    split_frames = _walk_forward_frames(frame, plan)
    all_regimes: list[pd.DataFrame] = []
    all_knn: list[pd.DataFrame] = []
    all_meta: list[pd.DataFrame] = []
    all_diagnostics: list[pd.DataFrame] = []
    all_knn_sweeps: list[pd.DataFrame] = []
    split_metrics: list[dict[str, Any]] = []
    meta_training_summaries: list[dict[str, Any]] = []
    knn_distance_backend = _resolve_lorentzian_distance_backend(plan.knn.distance_backend)
    start_time = time.perf_counter()
    meta_feature_columns = [
        "p_up_barrier",
        "expected_net_return_after_costs",
        "neighbor_agreement",
        "neighbor_distance_quality",
        "knn_vote_margin",
        "max_regime_probability",
        "posterior_entropy",
        *[column for column in plan.knn.feature_columns if column in frame.columns],
    ]

    for split_index, (train_frame, test_frame) in enumerate(split_frames):
        hmm_scaler = robust_scaler_fit(train_frame, plan.hmm.emission_features)
        regime_model = _fit_regime_model(hmm_scaler.transform(train_frame), train_frame, plan)
        train_posterior = _posterior_frame(
            base_frame=train_frame,
            posterior=regime_model.posterior(hmm_scaler.transform(train_frame)),
            model=regime_model,
            plan=plan,
            split_index=split_index,
            fit_end_index=int(train_frame.index.max()),
        )
        test_posterior = _posterior_frame(
            base_frame=test_frame,
            posterior=regime_model.posterior(hmm_scaler.transform(test_frame)),
            model=regime_model,
            plan=plan,
            split_index=split_index,
            fit_end_index=int(train_frame.index.max()),
        )
        feature_scaler = robust_scaler_fit(train_frame, plan.knn.feature_columns)
        knn_frame, diagnostics, knn_sweep = _knn_predict(
            train_matrix=feature_scaler.transform(train_frame),
            test_matrix=feature_scaler.transform(test_frame),
            train_frame=train_frame,
            test_frame=test_frame,
            train_regimes=train_posterior["top_regime"],
            test_regimes=test_posterior["top_regime"],
            train_regime_labels=train_posterior["top_regime_label"],
            test_regime_labels=test_posterior["top_regime_label"],
            plan=plan,
            distance_backend=knn_distance_backend,
        )
        test_scoring = test_frame.reset_index(drop=True).copy()
        meta_frame = pd.concat(
            [
                test_scoring,
                test_posterior.reset_index(drop=True).drop(columns=[column for column in test_scoring.columns if column in test_posterior.columns], errors="ignore"),
                knn_frame.reset_index(drop=True).drop(columns=[column for column in test_scoring.columns if column in knn_frame.columns], errors="ignore"),
            ],
            axis=1,
        )
        train_knn_frame = _leakage_safe_meta_knn_features(
            train_frame=train_frame,
            train_posterior=train_posterior,
            feature_scaler=feature_scaler,
            plan=plan,
        )
        train_meta_frame = pd.concat(
            [
                train_frame.reset_index(drop=True),
                train_posterior.reset_index(drop=True).drop(columns=[column for column in train_frame.columns if column in train_posterior.columns], errors="ignore"),
                train_knn_frame.reset_index(drop=True).drop(columns=[column for column in train_frame.columns if column in train_knn_frame.columns], errors="ignore"),
            ],
            axis=1,
        )
        model, backend = _fit_meta_model(train_meta_frame, meta_feature_columns, train_meta_frame[plan.labels.label_column], plan)
        meta_training_summary = _meta_training_summary(train_meta_frame, backend, plan)
        meta_training_summaries.append({**meta_training_summary, "split_index": split_index})
        meta_prob = model.predict_proba(meta_frame.reindex(columns=meta_feature_columns, fill_value=0.0).fillna(0.0).astype(float))[:, 1]
        meta_frame["meta_probability"] = meta_prob
        meta_frame["meta_model_backend"] = backend
        meta_frame["accepted_by_meta"] = (
            (meta_frame["meta_probability"] >= plan.meta_model.probability_threshold)
            & meta_frame["accepted_by_knn"].astype(bool)
            & ~meta_frame["regime_no_trade"].astype(bool)
        )
        all_regimes.append(test_posterior)
        all_knn.append(knn_frame.assign(walk_forward_split=split_index))
        all_meta.append(meta_frame)
        if not diagnostics.empty:
            all_diagnostics.append(diagnostics.assign(walk_forward_split=split_index))
        if not knn_sweep.empty:
            all_knn_sweeps.append(knn_sweep.assign(walk_forward_split=split_index))
        split_metrics.append(_split_metrics(meta_frame, split_index, plan, meta_training_summary=meta_training_summary))

    regime_posteriors = pd.concat(all_regimes, ignore_index=True)
    knn_predictions = pd.concat(all_knn, ignore_index=True)
    meta_predictions = pd.concat(all_meta, ignore_index=True)
    neighbor_diagnostics = pd.concat(all_diagnostics, ignore_index=True) if all_diagnostics else pd.DataFrame()
    knn_sweep_results = pd.concat(all_knn_sweeps, ignore_index=True) if all_knn_sweeps else pd.DataFrame()
    feature_set_variant = _feature_set_variant_payload(plan=plan, dataset=frame)

    regime_posteriors_path = output_path / "regime_posteriors.parquet"
    knn_predictions_path = output_path / "knn_predictions.parquet"
    meta_predictions_path = output_path / "meta_predictions.parquet"
    neighbor_diagnostics_path = output_path / "neighbor_diagnostics.csv"
    metrics_path = output_path / "walk_forward_metrics.json"
    artifact_manifest_path = output_path / "artifact_manifest.json"
    regime_posteriors.to_parquet(regime_posteriors_path, index=False)
    knn_predictions.to_parquet(knn_predictions_path, index=False)
    meta_predictions.to_parquet(meta_predictions_path, index=False)
    neighbor_diagnostics.to_csv(neighbor_diagnostics_path, index=False)

    metrics = _overall_metrics(meta_predictions, split_metrics, plan, knn_sweep=knn_sweep_results)
    artifact_diagnostics = build_hmm_knn_artifact_diagnostics(
        meta_predictions=meta_predictions,
        regime_posteriors=regime_posteriors,
        neighbor_diagnostics=neighbor_diagnostics,
        feature_columns=list(plan.knn.feature_columns),
        feature_variant=feature_set_variant,
    )
    stage6_baseline_benchmark = benchmark_against_stage6_baselines(
        dataset_path=resolved_dataset_path,
        output_dir=output_path / "stage6_baseline_benchmarks",
        symbol=plan.symbol,
    )
    metrics["artifact_diagnostics"] = artifact_diagnostics
    metrics["stage6_baseline_benchmark"] = stage6_baseline_benchmark
    metrics["feature_set_variant"] = feature_set_variant
    metrics["metrics_version"] = HMM_KNN_METRICS_VERSION
    metrics["latency_ms_per_row"] = round(((time.perf_counter() - start_time) * 1000.0) / max(len(meta_predictions), 1), 6)
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    xgboost_dependency_report = _xgboost_cuda_dependency_report()
    manifest = {
        "artifact_manifest_version": HMM_KNN_ARTIFACT_MANIFEST_VERSION,
        "plan_version": plan.version,
        "plan_sha256": plan.plan_sha256(),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "symbol": plan.symbol,
        "asset_scope": plan.asset_scope,
        "config_path": str(config_path),
        "dataset_path": str(resolved_dataset_path),
        "row_count": int(len(meta_predictions)),
        "feature_version": HMM_KNN_FEATURE_VERSION,
        "feature_pack": plan.knn.feature_pack,
        "feature_columns": list(plan.knn.feature_columns),
        "feature_set_variant_id": feature_set_variant["feature_set_variant_id"],
        "feature_set_variant_sha256": feature_set_variant["feature_set_variant_sha256"],
        "feature_set_source": feature_set_variant["feature_set_source"],
        "feature_count": feature_set_variant["feature_count"],
        "wt3d_enabled": feature_set_variant["wt3d_enabled"],
        "missingness_columns_present": feature_set_variant["missingness_columns_present"],
        "wt3d_feature_columns": list(WT3D_FEATURE_COLUMNS),
        "label_version": str(meta_predictions["label_version"].iloc[0]) if "label_version" in meta_predictions.columns and len(meta_predictions) else LABEL_VERSION,
        "label_horizons": list(plan.labels.horizons),
        "primary_label_horizon": plan.labels.primary_horizon,
        "label_outcome_fields": [column for column in LABEL_OUTCOME_COLUMNS if column in meta_predictions.columns],
        "knn_settings": {
            "distance": plan.knn.distance,
            "available_distances": sorted(DISTANCE_FUNCTIONS),
            "available_distance_metrics": available_distance_metrics(),
            "distance_metric": resolve_distance_metric(plan.knn.distance).to_payload(),
            "k_values": [int(k) for k in plan.knn.k_values],
            "primary_k": int(plan.knn.primary_k),
            "neighbor_weighting": list(plan.knn.neighbor_weighting),
            "primary_weighting": plan.knn.primary_weighting,
            "same_regime_only": bool(_effective_same_regime_only(_resolved_knn_regime_match_mode(plan))),
            "configured_same_regime_only": bool(plan.knn.same_regime_only),
            "allow_cross_regime_fallback": bool(plan.knn.allow_cross_regime_fallback),
            "regime_match_mode": _resolved_knn_regime_match_mode(plan),
            "compatible_regimes": plan.knn.compatible_regimes or {},
            "distance_backend": plan.knn.distance_backend,
        },
        "regime_posteriors_path": str(regime_posteriors_path),
        "knn_predictions_path": str(knn_predictions_path),
        "meta_predictions_path": str(meta_predictions_path),
        "neighbor_diagnostics_path": str(neighbor_diagnostics_path),
        "metrics_path": str(metrics_path),
        "dependencies": {
            "hmm_backend": sorted(meta_predictions["regime_model_backend"].dropna().unique().tolist()),
            "meta_backend": sorted(meta_predictions["meta_model_backend"].dropna().unique().tolist()),
            "hmmlearn_available": GaussianHMM is not None,
            "xgboost_available": XGBClassifier is not None,
            "cupy_available": _cupy_available(),
            "knn_distance_backend": knn_distance_backend,
            "knn_distance_backend_requested": plan.knn.distance_backend,
            **xgboost_dependency_report,
        },
        "meta_validation": {
            "training_summaries": meta_training_summaries,
            "promotion_failures": metrics["promotion_failures"],
        },
        "artifact_diagnostics": artifact_diagnostics,
        "stage6_baseline_benchmark": stage6_baseline_benchmark,
        "outputs": {
            "regime_posteriors": "posterior probabilities, entropy, top regime, and no-trade flags",
            "knn_predictions": "regime-local pluggable-distance KNN probabilities, EV, agreement, and distance quality",
            "meta_predictions": "XGBoost/fallback meta probabilities and accepted_by_meta research decisions",
            "neighbor_diagnostics": "top neighbor ranks, distances, weights, labels, and regimes",
        },
    }
    artifact_manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return HmmKnnResearchResult(
        output_dir=output_path,
        artifact_manifest_path=artifact_manifest_path,
        metrics_path=metrics_path,
        regime_posteriors_path=regime_posteriors_path,
        knn_predictions_path=knn_predictions_path,
        meta_predictions_path=meta_predictions_path,
        neighbor_diagnostics_path=neighbor_diagnostics_path,
    )


def _walk_forward_frames(frame: pd.DataFrame, plan: HmmKnnResearchPlan) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    initial_train = max(plan.evaluation.min_training_rows, int(len(frame) * plan.evaluation.train_fraction))
    remaining = max(len(frame) - initial_train, 0)
    split_size = max(1, remaining // max(plan.evaluation.walk_forward_splits, 1))
    splits: list[tuple[pd.DataFrame, pd.DataFrame]] = []
    train_end = initial_train
    for split_index in range(plan.evaluation.walk_forward_splits):
        test_start = min(len(frame), train_end + max(plan.evaluation.purge_embargo_bars, 0))
        if {"label_exit_time_ms", "signal_bar_time_ms"}.issubset(frame.columns) and train_end > 0:
            train_label_end = pd.to_numeric(frame.iloc[:train_end]["label_exit_time_ms"], errors="coerce").dropna()
            if not train_label_end.empty:
                first_allowed_time_ms = int(train_label_end.max()) + (max(plan.evaluation.purge_embargo_bars, 0) * BAR_INTERVAL_MS)
                candidate_positions = np.where(frame["signal_bar_time_ms"].astype(int).to_numpy() > first_allowed_time_ms)[0]
                candidate_positions = candidate_positions[candidate_positions >= train_end]
                if len(candidate_positions):
                    test_start = max(test_start, int(candidate_positions[0]))
                else:
                    break
        test_end = len(frame) if split_index == plan.evaluation.walk_forward_splits - 1 else min(len(frame), test_start + split_size)
        if test_start >= test_end:
            break
        splits.append((frame.iloc[:train_end].copy(), frame.iloc[test_start:test_end].copy()))
        train_end = test_end
    return splits


def _split_metrics(
    frame: pd.DataFrame,
    split_index: int,
    plan: HmmKnnResearchPlan,
    *,
    meta_training_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "split_index": split_index,
        "row_count": int(len(frame)),
        "knn": _strategy_metrics(frame, frame["accepted_by_knn"].astype(bool), plan),
        "meta": _strategy_metrics(frame, frame["accepted_by_meta"].astype(bool), plan),
        "meta_training": meta_training_summary,
        "regime_no_trade_rate": float(frame["regime_no_trade"].astype(bool).mean()) if len(frame) else 0.0,
    }


def _strategy_metrics(frame: pd.DataFrame, accept_mask: pd.Series, plan: HmmKnnResearchPlan) -> dict[str, Any]:
    selected = frame.loc[accept_mask].copy()
    no_trade_rate = float(1.0 - (len(selected) / len(frame))) if len(frame) else 0.0
    if selected.empty:
        return {
            "trade_count": 0,
            "expectancy_after_cost": 0.0,
            "profit_factor": None,
            "long_count": 0,
            "short_count": 0,
            "accepted_rate": 0.0,
            "no_trade_rate": no_trade_rate,
            "realized_pnl_total": 0.0,
            "expected_value_mean": None,
            "gross_return_mean": None,
            "funding_paid_or_received_mean": None,
            "fee_bps": float(plan.evaluation.fee_bps),
            "slippage_bps": float(plan.evaluation.slippage_bps),
            "funding_cost_enabled": bool(plan.evaluation.funding_cost_enabled),
            "tp_before_sl_rate": 0.0,
            "pnl_source": "realized_label_return_after_fee_slippage_funding",
        }
    pnl = _realized_pnl_after_cost(selected, plan)
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = abs(float(pnl[pnl < 0].sum()))
    direction = selected.get("direction", pd.Series([""] * len(selected))).astype(str).str.lower()
    return {
        "trade_count": int(len(selected)),
        "expectancy_after_cost": float(pnl.mean()),
        "profit_factor": None if gross_loss == 0 and gross_profit == 0 else (math.inf if gross_loss == 0 else gross_profit / gross_loss),
        "long_count": int((direction == "long").sum()),
        "short_count": int((direction == "short").sum()),
        "accepted_rate": float(len(selected) / len(frame)) if len(frame) else 0.0,
        "no_trade_rate": no_trade_rate,
        "realized_pnl_total": float(pnl.sum()),
        "expected_value_mean": (
            float(selected["expected_net_return_after_costs"].astype(float).mean())
            if "expected_net_return_after_costs" in selected.columns
            else None
        ),
        "gross_return_mean": float(_gross_return(selected, plan).mean()),
        "funding_paid_or_received_mean": float(_funding_paid_or_received(selected, plan).mean()),
        "fee_bps": float(plan.evaluation.fee_bps),
        "slippage_bps": float(plan.evaluation.slippage_bps),
        "funding_cost_enabled": bool(plan.evaluation.funding_cost_enabled),
        "tp_before_sl_rate": float(selected[plan.labels.label_column].astype(float).mean()),
        "pnl_source": "realized_label_return_after_fee_slippage_funding",
    }


def _gross_return(frame: pd.DataFrame, plan: HmmKnnResearchPlan) -> pd.Series:
    if "gross_return" in frame.columns:
        return pd.to_numeric(frame["gross_return"], errors="coerce").fillna(0.0).astype(float)
    return pd.to_numeric(frame[plan.labels.pnl_column], errors="coerce").fillna(0.0).astype(float)


def _funding_paid_or_received(frame: pd.DataFrame, plan: HmmKnnResearchPlan) -> pd.Series:
    if "funding_paid_or_received" in frame.columns:
        return pd.to_numeric(frame["funding_paid_or_received"], errors="coerce").fillna(0.0).astype(float)
    if not plan.evaluation.funding_cost_enabled:
        return pd.Series([0.0] * len(frame), index=frame.index, dtype=float)
    return frame.apply(lambda row: -_funding_cost(row, plan), axis=1).astype(float)


def _realized_pnl_after_cost(frame: pd.DataFrame, plan: HmmKnnResearchPlan) -> pd.Series:
    total_cost = (float(plan.evaluation.fee_bps) + float(plan.evaluation.slippage_bps)) / 10000.0
    return _gross_return(frame, plan) - total_cost + _funding_paid_or_received(frame, plan)


def _strategy_split_diagnostics(split_metrics: list[dict[str, Any]], strategy: str, plan: HmmKnnResearchPlan) -> dict[str, Any]:
    populated_splits = [split for split in split_metrics if split[strategy]["trade_count"] > 0]
    positive_split_ratio = (
        sum(1 for split in populated_splits if split[strategy]["expectancy_after_cost"] > plan.acceptance.min_expectancy_after_cost)
        / len(populated_splits)
        if populated_splits
        else 0.0
    )
    split_abs_pnl = [abs(float(split[strategy]["realized_pnl_total"])) for split in split_metrics]
    total_abs_pnl = sum(split_abs_pnl)
    max_single_split_pnl_share = max(split_abs_pnl) / total_abs_pnl if total_abs_pnl > 0 else 0.0
    return {
        "positive_split_ratio": positive_split_ratio,
        "max_single_split_pnl_share": max_single_split_pnl_share,
    }


def _strategy_promotion_failures(
    *,
    strategy_name: str,
    metrics: dict[str, Any],
    split_diagnostics: dict[str, Any],
    plan: HmmKnnResearchPlan,
) -> list[str]:
    failures: list[str] = []
    if metrics["trade_count"] < plan.acceptance.min_trade_count:
        failures.append(f"{strategy_name}_insufficient_trade_count")
    if metrics["expectancy_after_cost"] < plan.acceptance.min_expectancy_after_cost:
        failures.append(f"{strategy_name}_expectancy_after_cost_below_threshold")
    if split_diagnostics["max_single_split_pnl_share"] > plan.acceptance.max_single_split_pnl_share:
        failures.append(f"{strategy_name}_single_split_dominates_pnl")
    if plan.acceptance.require_long_short_breakout and (metrics["long_count"] == 0 or metrics["short_count"] == 0):
        failures.append(f"{strategy_name}_missing_long_short_breakout")
    return failures


def _meta_validation_failures(split_metrics: list[dict[str, Any]], plan: HmmKnnResearchPlan) -> list[str]:
    failures: list[str] = []
    if len(split_metrics) < 2:
        failures.append("insufficient_evaluated_splits")
    meta_training = [split.get("meta_training", {}) for split in split_metrics]
    if any(int(summary.get("label_class_count", 0)) < 2 for summary in meta_training):
        failures.append("insufficient_meta_training_class_diversity")
    minimum_oof_rows = max(int(plan.knn.min_neighbor_count), 2)
    if any(int(summary.get("oof_knn_available_rows", 0)) < minimum_oof_rows for summary in meta_training):
        failures.append("insufficient_meta_training_oof_rows")
    if any(str(summary.get("backend")) == "constant" for summary in meta_training):
        failures.append("constant_meta_model_backend")
    return failures


def _knn_sweep_metrics(knn_sweep: pd.DataFrame, plan: HmmKnnResearchPlan) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "distance": plan.knn.distance,
        "configured_k_values": [int(k) for k in plan.knn.k_values],
        "configured_weighting": list(plan.knn.neighbor_weighting),
        "primary_k": int(plan.knn.primary_k),
        "primary_weighting": plan.knn.primary_weighting,
        "same_regime_only": bool(plan.knn.same_regime_only),
        "allow_cross_regime_fallback": bool(plan.knn.allow_cross_regime_fallback),
        "distance_backend_requested": plan.knn.distance_backend,
        "distance_backend": _resolve_lorentzian_distance_backend(plan.knn.distance_backend),
        "results": [],
    }
    if knn_sweep.empty:
        return summary
    for (k, weighting), group in knn_sweep.groupby(["k", "weighting"], sort=True):
        accepted_mask = group["accepted_by_knn"].astype(bool)
        skip_counts = {
            str(reason): int(count)
            for reason, count in group["knn_skip_reason"].fillna("none").value_counts(dropna=False).sort_index().items()
        }
        summary["results"].append(
            {
                "k": int(k),
                "weighting": str(weighting),
                "is_primary": bool(int(k) == int(plan.knn.primary_k) and str(weighting) == plan.knn.primary_weighting),
                "metrics": _strategy_metrics(group, accepted_mask, plan),
                "fallback_rate": float(group["fallback_used"].astype(bool).mean()) if "fallback_used" in group.columns and len(group) else 0.0,
                "skip_reasons": skip_counts,
            }
        )
    return summary


def _overall_metrics(
    frame: pd.DataFrame,
    split_metrics: list[dict[str, Any]],
    plan: HmmKnnResearchPlan,
    *,
    knn_sweep: pd.DataFrame | None = None,
) -> dict[str, Any]:
    knn_sweep = knn_sweep if knn_sweep is not None else pd.DataFrame()
    meta = _strategy_metrics(frame, frame["accepted_by_meta"].astype(bool), plan)
    knn = _strategy_metrics(frame, frame["accepted_by_knn"].astype(bool), plan)
    meta_split_diagnostics = _strategy_split_diagnostics(split_metrics, "meta", plan)
    knn_split_diagnostics = _strategy_split_diagnostics(split_metrics, "knn", plan)
    failures: list[str] = ["research_only_not_live_promotable"]
    failures.extend(
        _strategy_promotion_failures(
            strategy_name="meta",
            metrics=meta,
            split_diagnostics=meta_split_diagnostics,
            plan=plan,
        )
    )
    failures.extend(
        _strategy_promotion_failures(
            strategy_name="knn",
            metrics=knn,
            split_diagnostics=knn_split_diagnostics,
            plan=plan,
        )
    )
    failures.extend(_meta_validation_failures(split_metrics, plan))
    if meta["trade_count"] > 0 and knn["trade_count"] > 0 and meta["expectancy_after_cost"] <= knn["expectancy_after_cost"]:
        failures.append("meta_filter_did_not_improve_pure_knn")
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "promotion_failures": sorted(set(failures)),
        "evaluation_basis": {
            "return_column": "gross_return" if "gross_return" in frame.columns else plan.labels.pnl_column,
            "fee_bps": float(plan.evaluation.fee_bps),
            "slippage_bps": float(plan.evaluation.slippage_bps),
            "funding_cost_enabled": bool(plan.evaluation.funding_cost_enabled),
            "pnl_source": "realized_label_return_after_fee_slippage_funding",
        },
        "row_count": int(len(frame)),
        "comparison": {
            "hmm_regime_lorentzian_knn": knn,
            "hmm_knn_meta_model": meta,
        },
        "knn_sweep": _knn_sweep_metrics(knn_sweep, plan),
        "walk_forward_summaries": split_metrics,
        "meta_validation": {
            "training_summaries": [split.get("meta_training", {}) for split in split_metrics],
            "failure_reasons": sorted(set(_meta_validation_failures(split_metrics, plan))),
        },
        "positive_split_ratio": meta_split_diagnostics["positive_split_ratio"],
        "positive_split_ratio_by_strategy": {
            "hmm_regime_lorentzian_knn": knn_split_diagnostics["positive_split_ratio"],
            "hmm_knn_meta_model": meta_split_diagnostics["positive_split_ratio"],
        },
        "max_single_split_pnl_share": meta_split_diagnostics["max_single_split_pnl_share"],
        "max_single_split_pnl_share_by_strategy": {
            "hmm_regime_lorentzian_knn": knn_split_diagnostics["max_single_split_pnl_share"],
            "hmm_knn_meta_model": meta_split_diagnostics["max_single_split_pnl_share"],
        },
        "no_trade_rate_by_strategy": {
            "hmm_regime_lorentzian_knn": knn["no_trade_rate"],
            "hmm_knn_meta_model": meta["no_trade_rate"],
        },
        "regime_summary": frame.groupby("top_regime_label", dropna=False).size().to_dict(),
        "horizon_summary": {horizon: "configured" for horizon in plan.labels.horizons},
    }


def replay_hmm_knn_artifact(manifest_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("research_only"):
        raise ValueError("HMM/KNN artifacts must remain research_only")
    metrics_path = Path(manifest["metrics_path"])
    if not metrics_path.exists():
        raise FileNotFoundError(metrics_path)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["research_only"] = True
    metrics["observe_only"] = True
    metrics["promotion_ready"] = False
    metrics.update(research_boundary_metadata())
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return metrics_path
