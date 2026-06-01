from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

import numpy as np
import pandas as pd

from tradingbotsuite.backtesting.splits import WalkForwardSplit, training_positions_for_split
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.neighbor_cache import (
    ExactNeighborCache,
    ExactNeighborCacheRecord,
    exact_neighbor_cache_identity,
    exact_neighbor_cache_key,
)
from tradingbotsuite.research_discovery.snapshots import atomic_write_json
from tradingbotsuite.research_discovery.spec import SUPPORTED_REGIME_MODES, regime_mode_settings


KNN_STUDY_SPEC_VERSION = "discovery-knn-study-spec-v1"
KNN_STUDY_MANIFEST_VERSION = "discovery-knn-study-manifest-v1"
KNN_STUDY_ENGINE_VERSION = "discovery-regime-local-knn-study-v1"
KNN_PREDICTION_COLUMNS = (
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
)
REQUIRED_HMM_COLUMNS = (
    "top_regime_label",
    "regime_no_trade",
    "hmm_fit_end_row",
    "source_row_index",
)
SUPPORTED_DISTANCE_METRICS = ("euclidean", "manhattan", "cosine")
LABEL_HORIZON_RE = re.compile(r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>bars?|b|m|min|minute|minutes|h|hour|hours|d|day|days)\s*$")


@dataclass(frozen=True, slots=True)
class KnnStudySpec:
    feature_columns: tuple[str, ...]
    label_column: str = "label_up"
    pnl_column: str = "label_return"
    k: int = 8
    distance_metric: str = "euclidean"
    probability_threshold: float = 0.55
    expected_value_threshold: float = 0.0
    min_neighbor_count: int = 4
    min_neighbor_agreement: float = 0.55
    min_distance_quality: float = 0.01
    vote_margin_threshold: float = 0.05
    same_regime_only: bool = True
    regime_mode: str = "gmm_same_regime_neighbors"
    regime_detector_type: str = "gmm"
    regime_model_backend: str = "sklearn.mixture.GaussianMixture"
    regime_gate_enabled: bool = True
    same_regime_neighbor_pool_enabled: bool = True
    true_hmm_backend_used: bool = False
    feature_column_set_id: str = "price_trend_vol"
    label_horizon: str = "4h"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "KnnStudySpec":
        if not isinstance(payload, Mapping):
            raise ValueError("KNN study spec must be a JSON object")
        legacy_same_regime_only = _bool_value(payload.get("same_regime_only", True))
        regime_mode = str(
            payload.get("regime_mode")
            or ("gmm_same_regime_neighbors" if legacy_same_regime_only else "gmm_all_regime_neighbors_with_gate")
        ).strip().lower()
        settings = regime_mode_settings(regime_mode)
        spec = cls(
            feature_columns=tuple(str(item).strip() for item in payload.get("feature_columns") or () if str(item).strip()),
            label_column=str(payload.get("label_column", "label_up")).strip(),
            pnl_column=str(payload.get("pnl_column", "label_return")).strip(),
            k=int(payload.get("k", 8)),
            distance_metric=str(payload.get("distance_metric", "euclidean")).strip().lower(),
            probability_threshold=float(payload.get("probability_threshold", 0.55)),
            expected_value_threshold=float(payload.get("expected_value_threshold", 0.0)),
            min_neighbor_count=int(payload.get("min_neighbor_count", 4)),
            min_neighbor_agreement=float(payload.get("min_neighbor_agreement", 0.55)),
            min_distance_quality=float(payload.get("min_distance_quality", 0.01)),
            vote_margin_threshold=float(payload.get("vote_margin_threshold", 0.05)),
            same_regime_only=_bool_value(payload.get("same_regime_only", settings.same_regime_only)),
            regime_mode=settings.regime_mode,
            regime_detector_type=str(payload.get("regime_detector_type", settings.regime_detector_type)).strip().lower(),
            regime_model_backend=str(payload.get("regime_model_backend", settings.regime_model_backend)).strip(),
            regime_gate_enabled=_bool_value(payload.get("regime_gate_enabled", settings.regime_gate_enabled)),
            same_regime_neighbor_pool_enabled=_bool_value(
                payload.get("same_regime_neighbor_pool_enabled", settings.same_regime_neighbor_pool_enabled)
            ),
            true_hmm_backend_used=_bool_value(payload.get("true_hmm_backend_used", settings.true_hmm_backend_used)),
            feature_column_set_id=str(payload.get("feature_column_set_id", "price_trend_vol")).strip(),
            label_horizon=str(payload.get("label_horizon", "4h")).strip(),
        )
        validate_knn_study_spec(spec)
        return spec

    @classmethod
    def from_path(cls, path: Path) -> "KnnStudySpec":
        payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8-sig"))
        return cls.from_payload(payload)

    def to_payload(self) -> dict[str, Any]:
        return {
            "spec_version": KNN_STUDY_SPEC_VERSION,
            "feature_columns": list(self.feature_columns),
            "label_column": self.label_column,
            "pnl_column": self.pnl_column,
            "k": self.k,
            "distance_metric": self.distance_metric,
            "probability_threshold": self.probability_threshold,
            "expected_value_threshold": self.expected_value_threshold,
            "min_neighbor_count": self.min_neighbor_count,
            "min_neighbor_agreement": self.min_neighbor_agreement,
            "min_distance_quality": self.min_distance_quality,
            "vote_margin_threshold": self.vote_margin_threshold,
            "same_regime_only": self.same_regime_only,
            "regime_mode": self.regime_mode,
            "regime_detector_type": self.regime_detector_type,
            "regime_model_backend": self.regime_model_backend,
            "regime_gate_enabled": self.regime_gate_enabled,
            "same_regime_neighbor_pool_enabled": self.same_regime_neighbor_pool_enabled,
            "true_hmm_backend_used": self.true_hmm_backend_used,
            "feature_column_set_id": self.feature_column_set_id,
            "label_horizon": self.label_horizon,
        }

    def spec_sha256(self) -> str:
        return sha256(json.dumps(self.to_payload(), sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class KnnStudyResult:
    frame: pd.DataFrame
    manifest: dict[str, Any]
    neighbor_diagnostics: pd.DataFrame


@dataclass(frozen=True, slots=True)
class KnnStudyArtifactResult:
    output_dir: Path
    manifest_path: Path
    predictions_path: Path
    neighbor_diagnostics_path: Path


@dataclass(frozen=True, slots=True)
class _TrainOnlyScaler:
    columns: tuple[str, ...]
    median: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, frame: pd.DataFrame, columns: Sequence[str]) -> "_TrainOnlyScaler":
        matrix = _numeric_matrix(frame, columns)
        median = _safe_column_nanmedian(matrix)
        q75 = _safe_column_nanpercentile(matrix, 75)
        q25 = _safe_column_nanpercentile(matrix, 25)
        scale = q75 - q25
        median = np.where(np.isfinite(median), median, 0.0)
        scale = np.where(np.isfinite(scale) & (scale > 1e-12), scale, 1.0)
        return cls(columns=tuple(columns), median=median.astype(float), scale=scale.astype(float))

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        matrix = _numeric_matrix(frame, self.columns)
        matrix = np.where(np.isfinite(matrix), matrix, self.median.reshape(1, -1))
        return (matrix - self.median.reshape(1, -1)) / self.scale.reshape(1, -1)


def validate_knn_study_spec(spec: KnnStudySpec) -> None:
    if not spec.feature_columns:
        raise ValueError("feature_columns must contain at least one column")
    if len(set(spec.feature_columns)) != len(spec.feature_columns):
        raise ValueError("feature_columns must not contain duplicates")
    if not spec.label_column or not spec.pnl_column:
        raise ValueError("label_column and pnl_column are required")
    if spec.k <= 0:
        raise ValueError("k must be positive")
    if spec.min_neighbor_count <= 0:
        raise ValueError("min_neighbor_count must be positive")
    if spec.min_neighbor_count > spec.k:
        raise ValueError("min_neighbor_count must be <= k")
    if spec.distance_metric not in SUPPORTED_DISTANCE_METRICS:
        raise ValueError(f"distance_metric must be one of: {', '.join(SUPPORTED_DISTANCE_METRICS)}")
    for field_name, value in {
        "probability_threshold": spec.probability_threshold,
        "min_neighbor_agreement": spec.min_neighbor_agreement,
        "min_distance_quality": spec.min_distance_quality,
        "vote_margin_threshold": spec.vote_margin_threshold,
    }.items():
        if value < 0.0 or value > 1.0:
            raise ValueError(f"{field_name} must be between 0 and 1")
    if not spec.feature_column_set_id:
        raise ValueError("feature_column_set_id must not be empty")
    if spec.regime_mode not in SUPPORTED_REGIME_MODES:
        raise ValueError(f"regime_mode must be one of: {', '.join(SUPPORTED_REGIME_MODES)}")
    settings = regime_mode_settings(spec.regime_mode)
    if spec.regime_detector_type != settings.regime_detector_type:
        raise ValueError("regime_detector_type must match regime_mode")
    if spec.regime_model_backend != settings.regime_model_backend:
        raise ValueError("regime_model_backend must match regime_mode")
    if spec.regime_gate_enabled != settings.regime_gate_enabled:
        raise ValueError("regime_gate_enabled must match regime_mode")
    if spec.same_regime_neighbor_pool_enabled != settings.same_regime_neighbor_pool_enabled:
        raise ValueError("same_regime_neighbor_pool_enabled must match regime_mode")
    if spec.same_regime_only != spec.same_regime_neighbor_pool_enabled:
        raise ValueError("same_regime_only must match same_regime_neighbor_pool_enabled")
    if spec.true_hmm_backend_used:
        raise ValueError("true_hmm_backend_used must be false for discovery KNN studies")


def _safe_column_nanmedian(matrix: np.ndarray) -> np.ndarray:
    return np.array([_finite_percentile(matrix[:, index], 50) for index in range(matrix.shape[1])], dtype=float)


def _safe_column_nanpercentile(matrix: np.ndarray, percentile: float) -> np.ndarray:
    return np.array([_finite_percentile(matrix[:, index], percentile) for index in range(matrix.shape[1])], dtype=float)


def _finite_percentile(values: np.ndarray, percentile: float) -> float:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan")
    return float(np.percentile(finite, percentile))


def materialize_regime_local_knn_predictions(
    frame: pd.DataFrame,
    *,
    splits: Sequence[WalkForwardSplit],
    spec: KnnStudySpec,
    neighbor_cache: ExactNeighborCache | None = None,
    neighbor_cache_k_limit: int | None = None,
    source_identity: Mapping[str, Any] | None = None,
    include_neighbor_diagnostics: bool = True,
) -> KnnStudyResult:
    validate_knn_study_spec(spec)
    missing = [column for column in (*spec.feature_columns, spec.label_column, spec.pnl_column, *REQUIRED_HMM_COLUMNS) if column not in frame.columns]
    if missing:
        raise ValueError(f"knn_study_missing_columns:{','.join(missing)}")
    ordered = frame.reset_index(drop=True).copy()
    result = _empty_result(ordered)
    diagnostics: list[dict[str, Any]] = []
    split_records: list[dict[str, Any]] = []
    label_horizon_bars = _label_horizon_bars(ordered, spec.label_horizon)

    for split in splits:
        validation_positions = _validation_positions(split, row_count=len(ordered))
        if not validation_positions:
            continue
        train_positions = training_positions_for_split(split, row_count=len(ordered))
        if not train_positions:
            split_records.append(_blocked_split_record(split, reason="no_training_rows", validation_count=len(validation_positions)))
            continue
        train = ordered.iloc[train_positions].copy()
        validation_source_min = int(
            pd.to_numeric(ordered.iloc[validation_positions]["source_row_index"], errors="raise")
            .astype("int64")
            .min()
        )
        train_source = pd.to_numeric(train["source_row_index"], errors="raise").astype("int64")
        safe_train_source_max = validation_source_min - label_horizon_bars - 1
        horizon_safe_train = train.loc[train_source <= safe_train_source_max].copy()
        label_horizon_dropped = int(len(train) - len(horizon_safe_train))
        train = horizon_safe_train.dropna(subset=[spec.label_column, spec.pnl_column], how="any")
        if len(train) < spec.min_neighbor_count:
            split_records.append(
                _blocked_split_record(
                    split,
                    reason="insufficient_labeled_training_rows",
                    validation_count=len(validation_positions),
                    train_row_count=len(train),
                    label_horizon_bars=label_horizon_bars,
                    label_horizon_dropped_count=label_horizon_dropped,
                )
            )
            continue
        scaler = _TrainOnlyScaler.fit(train, spec.feature_columns)
        train_matrix = scaler.transform(train)
        train_source = pd.to_numeric(train["source_row_index"], errors="raise").astype("int64").to_numpy()
        train_regimes = train["top_regime_label"].astype(str).to_numpy()
        labels = pd.to_numeric(train[spec.label_column], errors="coerce").fillna(0.0).clip(0.0, 1.0).to_numpy(dtype=float)
        pnl = pd.to_numeric(train[spec.pnl_column], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        materialized_count = 0
        validation = ordered.iloc[validation_positions].copy()
        validation_matrix = scaler.transform(validation)
        validation_source_rows = [_int_marker(value) for value in validation["source_row_index"].to_numpy()]
        validation_fit_ends = [_int_marker(value) for value in validation["hmm_fit_end_row"].to_numpy()]
        validation_no_trade = validation["regime_no_trade"].map(bool).to_numpy()
        validation_regimes = validation["top_regime_label"].astype(str).to_numpy()
        selection_k_limit = max(int(spec.k), int(neighbor_cache_k_limit or spec.k))
        neighbor_cache_key = ""
        neighbor_cache_hit = False
        neighbor_search_engine = "rowwise_exact_numpy"
        if neighbor_cache is not None:
            identity = exact_neighbor_cache_identity(
                feature_column_set_id=spec.feature_column_set_id,
                feature_columns=spec.feature_columns,
                label_horizon=spec.label_horizon,
                label_horizon_bars=label_horizon_bars,
                split_id=str(split.split_id),
                regime_mode=spec.regime_mode,
                regime_detector_type=spec.regime_detector_type,
                regime_gate_enabled=spec.regime_gate_enabled,
                same_regime_neighbor_pool_enabled=spec.same_regime_neighbor_pool_enabled,
                distance_metric=spec.distance_metric,
                selection_k_limit=selection_k_limit,
                train_source_min=_array_min_int(train_source),
                train_source_max=_array_max_int(train_source),
                validation_source_min=_list_min_int(validation_source_rows),
                validation_source_max=_list_max_int(validation_source_rows),
                safe_train_source_max=int(safe_train_source_max),
                train_row_count=len(train),
                validation_row_count=len(validation_positions),
                source_identity=source_identity,
            )
            neighbor_cache_key = exact_neighbor_cache_key(identity)
            cached_neighbors = neighbor_cache.get(neighbor_cache_key)
            if cached_neighbors is None:
                row_neighbor_records, neighbor_search_engine = _precompute_neighbor_records(
                    validation_source_rows=validation_source_rows,
                    validation_fit_ends=validation_fit_ends,
                    validation_no_trade=validation_no_trade,
                    validation_regimes=validation_regimes,
                    validation_matrix=validation_matrix,
                    train_matrix=train_matrix,
                    train_source=train_source,
                    train_regimes=train_regimes,
                    spec=spec,
                    selection_k_limit=selection_k_limit,
                )
                cached_neighbors = ExactNeighborCacheRecord(
                    cache_key=neighbor_cache_key,
                    identity=identity,
                    row_records=row_neighbor_records,
                )
                cached_neighbors = neighbor_cache.put(cached_neighbors)
            else:
                neighbor_cache_hit = True
                neighbor_search_engine = "exact_neighbor_cache"
            row_neighbor_records = tuple(cached_neighbors.row_records)
        else:
            row_neighbor_records, neighbor_search_engine = _precompute_neighbor_records(
                validation_source_rows=validation_source_rows,
                validation_fit_ends=validation_fit_ends,
                validation_no_trade=validation_no_trade,
                validation_regimes=validation_regimes,
                validation_matrix=validation_matrix,
                train_matrix=train_matrix,
                train_source=train_source,
                train_regimes=train_regimes,
                spec=spec,
                selection_k_limit=selection_k_limit,
            )

        for offset, position in enumerate(validation_positions):
            prediction, row_diagnostics = _predict_from_selected_neighbors(
                row_neighbor_records[offset],
                train_source=train_source,
                train_regimes=train_regimes,
                labels=labels,
                pnl=pnl,
                spec=spec,
                split_id=str(split.split_id),
                include_diagnostics=include_neighbor_diagnostics,
            )
            for key, value in prediction.items():
                result.loc[position, key] = value
            if include_neighbor_diagnostics:
                diagnostics.extend(row_diagnostics)
            if prediction["knn_skip_reason"] == "":
                materialized_count += 1
        split_records.append(
            {
                "split_id": str(split.split_id),
                "status": "materialized",
                "train_row_count": int(len(train)),
                "validation_row_count": int(len(validation_positions)),
                "accepted_prediction_count": int(materialized_count),
                "label_horizon_bars": int(label_horizon_bars),
                "label_horizon_dropped_count": int(label_horizon_dropped),
                "safe_train_source_max": int(safe_train_source_max),
                "neighbor_cache_enabled": neighbor_cache is not None,
                "neighbor_cache_hit": bool(neighbor_cache_hit),
                "neighbor_cache_key": neighbor_cache_key,
                "neighbor_cache_selection_k_limit": int(selection_k_limit),
                "neighbor_search_engine": neighbor_search_engine,
            }
        )

    diagnostics_frame = pd.DataFrame(diagnostics, columns=_diagnostic_columns())
    manifest = {
        "knn_study_manifest_version": KNN_STUDY_MANIFEST_VERSION,
        "knn_study_engine_version": KNN_STUDY_ENGINE_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec": spec.to_payload(),
        "spec_sha256": spec.spec_sha256(),
        "row_count": int(len(result)),
        "prediction_row_count": int(result["knn_skip_reason"].eq("").sum()),
        "accepted_prediction_count": int(result["accepted_by_knn"].astype(bool).sum()),
        "neighbor_diagnostic_count": int(len(diagnostics_frame)),
        "split_count": int(len(splits)),
        "split_records": split_records,
        "required_output_columns": list(KNN_PREDICTION_COLUMNS),
        "regime_mode": spec.regime_mode,
        "regime_detector_type": spec.regime_detector_type,
        "regime_model_backend": spec.regime_model_backend,
        "regime_gate_enabled": spec.regime_gate_enabled,
        "same_regime_neighbor_pool_enabled": spec.same_regime_neighbor_pool_enabled,
        "true_hmm_backend_used": spec.true_hmm_backend_used,
        "prediction_engine": "split_local_vectorized_validation_v1",
        "neighbor_selection_engine": "deterministic_partition_topk_v1",
        "neighbor_cache_policy": {
            "enabled": neighbor_cache is not None,
            "identity_scope": "feature_set_split_horizon_regime_distance_source",
            "thresholds_excluded_from_identity": True,
            "selection_k_limit": int(max(int(spec.k), int(neighbor_cache_k_limit or spec.k))),
            "exact_knn_parity_required": True,
        },
        "neighbor_cache_hit_count": int(sum(1 for record in split_records if record.get("neighbor_cache_hit") is True)),
        "neighbor_cache_lookup_count": int(sum(1 for record in split_records if record.get("neighbor_cache_enabled") is True)),
        "neighbor_diagnostics_included": bool(include_neighbor_diagnostics),
        "split_safety_rule": "neighbor_min_source_index <= neighbor_max_source_index <= hmm_fit_end_row < source_row_index",
        "label_safety_rule": "training_label_source_row_index + label_horizon_bars < validation_source_row_index",
        "label_horizon_bars": int(label_horizon_bars),
        "split_safety_passed": bool(_split_safety_passed(result)),
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    return KnnStudyResult(frame=result, manifest=manifest, neighbor_diagnostics=diagnostics_frame)


def write_knn_study_artifacts(output_dir: Path, result: KnnStudyResult) -> KnnStudyArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "knn_predictions.parquet"
    diagnostics_path = output_dir / "neighbor_diagnostics.parquet"
    manifest_path = output_dir / "knn_study_manifest.json"
    _assert_new_artifact_paths(predictions_path, diagnostics_path, manifest_path)
    _atomic_write_parquet(result.frame, predictions_path)
    _atomic_write_parquet(result.neighbor_diagnostics, diagnostics_path)
    manifest = dict(result.manifest)
    manifest["required_outputs"] = {
        "knn_study_manifest": str(manifest_path),
        "knn_predictions": str(predictions_path),
        "neighbor_diagnostics": str(diagnostics_path),
    }
    manifest["knn_predictions_sha256"] = _file_sha256(predictions_path)
    manifest["neighbor_diagnostics_sha256"] = _file_sha256(diagnostics_path)
    atomic_write_json(manifest_path, manifest)
    return KnnStudyArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        predictions_path=predictions_path,
        neighbor_diagnostics_path=diagnostics_path,
    )


def _predict_row(
    row: pd.Series,
    *,
    train_matrix: np.ndarray,
    train_source: np.ndarray,
    train_regimes: np.ndarray,
    labels: np.ndarray,
    pnl: np.ndarray,
    scaler: _TrainOnlyScaler,
    spec: KnnStudySpec,
    split_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_row = _int_marker(row.get("source_row_index"))
    fit_end = _int_marker(row.get("hmm_fit_end_row"))
    query_regime = str(row.get("top_regime_label") or "")
    query_matrix = scaler.transform(pd.DataFrame([row], columns=row.index))[0]
    return _predict_precomputed_row(
        source_row=source_row,
        fit_end=fit_end,
        no_trade=bool(row.get("regime_no_trade")),
        query_regime=query_regime,
        query_matrix=query_matrix,
        train_matrix=train_matrix,
        train_source=train_source,
        train_regimes=train_regimes,
        labels=labels,
        pnl=pnl,
        spec=spec,
        split_id=split_id,
    )


def _predict_precomputed_row(
    *,
    source_row: int | None,
    fit_end: int | None,
    no_trade: bool,
    query_regime: str,
    query_matrix: np.ndarray,
    train_matrix: np.ndarray,
    train_source: np.ndarray,
    train_regimes: np.ndarray,
    labels: np.ndarray,
    pnl: np.ndarray,
    spec: KnnStudySpec,
    split_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selected = _select_precomputed_neighbors(
        source_row=source_row,
        fit_end=fit_end,
        no_trade=no_trade,
        query_regime=query_regime,
        query_matrix=query_matrix,
        train_matrix=train_matrix,
        train_source=train_source,
        train_regimes=train_regimes,
        spec=spec,
        selection_k_limit=spec.k,
    )
    return _predict_from_selected_neighbors(
        selected,
        train_source=train_source,
        train_regimes=train_regimes,
        labels=labels,
        pnl=pnl,
        spec=spec,
        split_id=split_id,
        include_diagnostics=True,
    )


def _select_precomputed_neighbors(
    *,
    source_row: int | None,
    fit_end: int | None,
    no_trade: bool,
    query_regime: str,
    query_matrix: np.ndarray,
    train_matrix: np.ndarray,
    train_source: np.ndarray,
    train_regimes: np.ndarray,
    spec: KnnStudySpec,
    selection_k_limit: int,
) -> dict[str, Any]:
    if source_row is None or fit_end is None or fit_end < 0 or fit_end >= source_row:
        return _neighbor_skip_record(source_row=source_row, query_regime=query_regime, reason="unsafe_hmm_split_row")
    if spec.regime_gate_enabled and no_trade:
        return _neighbor_skip_record(source_row=source_row, query_regime=query_regime, reason="hmm_regime_no_trade")
    candidate_mask = train_source <= fit_end
    if spec.same_regime_neighbor_pool_enabled:
        candidate_mask = candidate_mask & (train_regimes == query_regime)
    candidate_indices = np.where(candidate_mask)[0]
    if len(candidate_indices) == 0:
        reason = "insufficient_regime_neighbors" if spec.same_regime_neighbor_pool_enabled else "insufficient_neighbors"
        return _neighbor_skip_record(source_row=source_row, query_regime=query_regime, reason=reason)

    distances = _distances(query_matrix, train_matrix[candidate_indices], metric=spec.distance_metric)
    order = _stable_topk_distance_order(distances, k=selection_k_limit)
    selected = candidate_indices[order]
    selected_distances = distances[order]
    return {
        "source_row": int(source_row),
        "query_regime": str(query_regime),
        "skip_reason": "",
        "selected_indices": [int(index) for index in selected],
        "selected_distances": [float(distance) for distance in selected_distances],
    }


def _precompute_neighbor_records(
    *,
    validation_source_rows: Sequence[int | None],
    validation_fit_ends: Sequence[int | None],
    validation_no_trade: np.ndarray,
    validation_regimes: np.ndarray,
    validation_matrix: np.ndarray,
    train_matrix: np.ndarray,
    train_source: np.ndarray,
    train_regimes: np.ndarray,
    spec: KnnStudySpec,
    selection_k_limit: int,
) -> tuple[tuple[Mapping[str, Any], ...], str]:
    batched = _select_precomputed_neighbors_batched(
        validation_source_rows=validation_source_rows,
        validation_fit_ends=validation_fit_ends,
        validation_no_trade=validation_no_trade,
        validation_regimes=validation_regimes,
        validation_matrix=validation_matrix,
        train_matrix=train_matrix,
        train_source=train_source,
        train_regimes=train_regimes,
        spec=spec,
        selection_k_limit=selection_k_limit,
    )
    if batched is not None:
        return batched, "sklearn_nearest_neighbors_exact_batch"
    return (
        tuple(
            _select_precomputed_neighbors(
                source_row=validation_source_rows[offset],
                fit_end=validation_fit_ends[offset],
                no_trade=bool(validation_no_trade[offset]),
                query_regime=str(validation_regimes[offset]),
                query_matrix=validation_matrix[offset],
                train_matrix=train_matrix,
                train_source=train_source,
                train_regimes=train_regimes,
                spec=spec,
                selection_k_limit=selection_k_limit,
            )
            for offset in range(len(validation_source_rows))
        ),
        "rowwise_exact_numpy",
    )


def _select_precomputed_neighbors_batched(
    *,
    validation_source_rows: Sequence[int | None],
    validation_fit_ends: Sequence[int | None],
    validation_no_trade: np.ndarray,
    validation_regimes: np.ndarray,
    validation_matrix: np.ndarray,
    train_matrix: np.ndarray,
    train_source: np.ndarray,
    train_regimes: np.ndarray,
    spec: KnnStudySpec,
    selection_k_limit: int,
) -> tuple[Mapping[str, Any], ...] | None:
    if len(validation_source_rows) == 0:
        return ()
    fit_ends = [int(value) for value in validation_fit_ends if value is not None]
    if len(fit_ends) != len(validation_fit_ends) or len(set(fit_ends)) != 1:
        return None
    fit_end = fit_ends[0]
    if fit_end < 0:
        return None
    try:
        from sklearn.neighbors import NearestNeighbors
    except Exception:
        return None

    records: list[Mapping[str, Any] | None] = [None] * len(validation_source_rows)
    eligible_offsets: list[int] = []
    for offset, source_row in enumerate(validation_source_rows):
        query_regime = str(validation_regimes[offset])
        if source_row is None or fit_end >= int(source_row):
            records[offset] = _neighbor_skip_record(
                source_row=source_row,
                query_regime=query_regime,
                reason="unsafe_hmm_split_row",
            )
            continue
        if spec.regime_gate_enabled and bool(validation_no_trade[offset]):
            records[offset] = _neighbor_skip_record(
                source_row=source_row,
                query_regime=query_regime,
                reason="hmm_regime_no_trade",
            )
            continue
        eligible_offsets.append(offset)

    candidate_base = train_source <= fit_end
    if not np.any(candidate_base):
        for offset in eligible_offsets:
            records[offset] = _neighbor_skip_record(
                source_row=validation_source_rows[offset],
                query_regime=str(validation_regimes[offset]),
                reason="insufficient_neighbors",
            )
        return tuple(record for record in records if record is not None)

    if spec.same_regime_neighbor_pool_enabled:
        groups: dict[str, list[int]] = {}
        for offset in eligible_offsets:
            groups.setdefault(str(validation_regimes[offset]), []).append(offset)
    else:
        groups = {"": eligible_offsets}

    for query_regime, offsets in groups.items():
        if not offsets:
            continue
        candidate_mask = candidate_base
        if spec.same_regime_neighbor_pool_enabled:
            candidate_mask = candidate_mask & (train_regimes == query_regime)
        candidate_indices = np.flatnonzero(candidate_mask)
        if len(candidate_indices) == 0:
            reason = "insufficient_regime_neighbors" if spec.same_regime_neighbor_pool_enabled else "insufficient_neighbors"
            for offset in offsets:
                records[offset] = _neighbor_skip_record(
                    source_row=validation_source_rows[offset],
                    query_regime=str(validation_regimes[offset]),
                    reason=reason,
                )
            continue

        n_neighbors = min(max(1, int(selection_k_limit)), len(candidate_indices))
        estimator = NearestNeighbors(
            n_neighbors=n_neighbors,
            metric=spec.distance_metric,
            algorithm="auto",
            n_jobs=1,
        )
        estimator.fit(train_matrix[candidate_indices])
        distances, neighbor_positions = estimator.kneighbors(validation_matrix[offsets], return_distance=True)
        for row_index, offset in enumerate(offsets):
            selected_indices = candidate_indices[neighbor_positions[row_index]]
            selected_distances = distances[row_index]
            order = np.lexsort((selected_indices, selected_distances))
            ordered_indices = selected_indices[order][:selection_k_limit]
            ordered_distances = selected_distances[order][:selection_k_limit]
            records[offset] = {
                "source_row": int(validation_source_rows[offset]),
                "query_regime": str(validation_regimes[offset]),
                "skip_reason": "",
                "selected_indices": [int(index) for index in ordered_indices],
                "selected_distances": [float(distance) for distance in ordered_distances],
            }

    if any(record is None for record in records):
        return None
    return tuple(record for record in records if record is not None)


def _neighbor_skip_record(*, source_row: int | None, query_regime: str, reason: str) -> dict[str, Any]:
    return {
        "source_row": source_row,
        "query_regime": str(query_regime),
        "skip_reason": str(reason),
        "selected_indices": [],
        "selected_distances": [],
    }


def _predict_from_selected_neighbors(
    selected_record: Mapping[str, Any],
    *,
    train_source: np.ndarray,
    train_regimes: np.ndarray,
    labels: np.ndarray,
    pnl: np.ndarray,
    spec: KnnStudySpec,
    split_id: str,
    include_diagnostics: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    skip_reason = str(selected_record.get("skip_reason") or "")
    if skip_reason:
        return _skip_prediction(skip_reason), []
    selected = np.array([int(index) for index in selected_record.get("selected_indices", ())], dtype=int)[: spec.k]
    selected_distances = np.array(
        [float(distance) for distance in selected_record.get("selected_distances", ())],
        dtype=float,
    )[: spec.k]
    if len(selected) < spec.min_neighbor_count:
        reason = "insufficient_regime_neighbors" if spec.same_regime_neighbor_pool_enabled else "insufficient_neighbors"
        return _skip_prediction(reason), []
    selected_labels = labels[selected]
    selected_pnl = pnl[selected]
    p_up = float(selected_labels.mean())
    p_down = float(1.0 - p_up)
    implied_side = "long" if p_up >= p_down else "short"
    raw_expected_return = float(selected_pnl.mean())
    expected_value = raw_expected_return if implied_side == "long" else -raw_expected_return
    probability = max(p_up, p_down)
    agreement = probability
    vote_margin = abs(p_up - p_down)
    distance_quality = _distance_quality(selected_distances)
    neighbor_sources = train_source[selected]
    accepted = (
        len(selected) >= spec.min_neighbor_count
        and probability >= spec.probability_threshold
        and expected_value >= spec.expected_value_threshold
        and agreement >= spec.min_neighbor_agreement
        and distance_quality >= spec.min_distance_quality
        and vote_margin >= spec.vote_margin_threshold
    )
    skip_reason = "" if accepted else _rejection_reason(
        probability=probability,
        expected_value=expected_value,
        agreement=agreement,
        distance_quality=distance_quality,
        vote_margin=vote_margin,
        spec=spec,
    )
    prediction = {
        "p_up_barrier": p_up,
        "p_down_barrier": p_down,
        "expected_net_return_after_costs": expected_value,
        "neighbor_agreement": agreement,
        "neighbor_distance_quality": distance_quality,
        "neighbor_count": int(len(selected)),
        "neighbor_min_source_index": int(neighbor_sources.min()),
        "neighbor_max_source_index": int(neighbor_sources.max()),
        "knn_vote_margin": vote_margin,
        "accepted_by_knn": bool(accepted),
        "knn_skip_reason": skip_reason,
    }
    diagnostics = []
    if include_diagnostics:
        diagnostics = [
            {
                "split_id": split_id,
                "source_row_index": int(selected_record["source_row"]),
                "neighbor_source_index": int(train_source[index]),
                "neighbor_rank": int(rank + 1),
                "neighbor_distance": float(selected_distances[rank]),
                "neighbor_regime": str(train_regimes[index]),
                "query_regime": str(selected_record.get("query_regime") or ""),
                "label_value": float(labels[index]),
                "pnl_value": float(pnl[index]),
                "feature_column_set_id": spec.feature_column_set_id,
                "distance_metric": spec.distance_metric,
            }
            for rank, index in enumerate(selected)
        ]
    return prediction, diagnostics


def _empty_result(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["p_up_barrier"] = np.nan
    result["p_down_barrier"] = np.nan
    result["expected_net_return_after_costs"] = np.nan
    result["neighbor_agreement"] = np.nan
    result["neighbor_distance_quality"] = np.nan
    result["neighbor_count"] = 0
    result["neighbor_min_source_index"] = -1
    result["neighbor_max_source_index"] = -1
    result["knn_vote_margin"] = np.nan
    result["accepted_by_knn"] = False
    result["knn_skip_reason"] = "not_evaluated"
    return result


def _skip_prediction(reason: str) -> dict[str, Any]:
    return {
        "p_up_barrier": np.nan,
        "p_down_barrier": np.nan,
        "expected_net_return_after_costs": np.nan,
        "neighbor_agreement": np.nan,
        "neighbor_distance_quality": np.nan,
        "neighbor_count": 0,
        "neighbor_min_source_index": -1,
        "neighbor_max_source_index": -1,
        "knn_vote_margin": np.nan,
        "accepted_by_knn": False,
        "knn_skip_reason": reason,
    }


def _rejection_reason(
    *,
    probability: float,
    expected_value: float,
    agreement: float,
    distance_quality: float,
    vote_margin: float,
    spec: KnnStudySpec,
) -> str:
    if probability < spec.probability_threshold:
        return "probability_below_threshold"
    if expected_value < spec.expected_value_threshold:
        return "expected_value_below_threshold"
    if agreement < spec.min_neighbor_agreement:
        return "neighbor_agreement_below_threshold"
    if distance_quality < spec.min_distance_quality:
        return "distance_quality_below_threshold"
    if vote_margin < spec.vote_margin_threshold:
        return "vote_margin_below_threshold"
    return "not_accepted"


def _distances(query: np.ndarray, matrix: np.ndarray, *, metric: str) -> np.ndarray:
    diff = matrix - query.reshape(1, -1)
    if metric == "euclidean":
        return np.sqrt(np.sum(diff * diff, axis=1))
    if metric == "manhattan":
        return np.sum(np.abs(diff), axis=1)
    if metric == "cosine":
        numerator = matrix @ query
        denominator = np.linalg.norm(matrix, axis=1) * max(float(np.linalg.norm(query)), 1e-12)
        return 1.0 - (numerator / np.maximum(denominator, 1e-12))
    raise ValueError(f"unsupported distance metric: {metric}")


def _stable_topk_distance_order(distances: np.ndarray, *, k: int) -> np.ndarray:
    limit = min(max(0, int(k)), len(distances))
    if limit == 0:
        return np.array([], dtype=int)
    if limit >= len(distances):
        return np.argsort(distances, kind="mergesort")
    kth_distance = float(np.partition(distances, limit - 1)[limit - 1])
    if not math.isfinite(kth_distance):
        return np.argsort(distances, kind="mergesort")[:limit]
    reduced = np.flatnonzero(distances <= kth_distance)
    reduced_order = np.argsort(distances[reduced], kind="mergesort")
    return reduced[reduced_order][:limit]


def _distance_quality(distances: np.ndarray) -> float:
    if len(distances) == 0 or not np.isfinite(distances).all():
        return 0.0
    mean_distance = float(np.mean(distances))
    return float(1.0 / (1.0 + max(mean_distance, 0.0)))


def _validation_positions(split: WalkForwardSplit, *, row_count: int) -> list[int]:
    if split.validation_indices is not None:
        return [int(position) for position in split.validation_indices if 0 <= int(position) < row_count]
    start = max(0, int(split.validation_start_index))
    end = min(row_count - 1, int(split.validation_end_index))
    if end < start:
        return []
    return list(range(start, end + 1))


def _label_horizon_bars(frame: pd.DataFrame, label_horizon: str) -> int:
    normalized = str(label_horizon or "").strip().lower()
    match = LABEL_HORIZON_RE.match(normalized)
    if not match:
        raise ValueError(f"unsupported label_horizon: {label_horizon}")
    value = float(match.group("value"))
    unit = match.group("unit")
    if value <= 0.0 or not math.isfinite(value):
        raise ValueError("label_horizon must be positive")
    if unit in {"b", "bar", "bars"}:
        return max(1, int(math.ceil(value)))
    horizon_ms = _duration_ms(value, unit)
    bar_ms = _infer_bar_duration_ms(frame)
    return max(1, int(math.ceil(horizon_ms / bar_ms)))


def _duration_ms(value: float, unit: str) -> float:
    if unit in {"m", "min", "minute", "minutes"}:
        return value * 60_000.0
    if unit in {"h", "hour", "hours"}:
        return value * 3_600_000.0
    if unit in {"d", "day", "days"}:
        return value * 86_400_000.0
    raise ValueError(f"unsupported label_horizon unit: {unit}")


def _infer_bar_duration_ms(frame: pd.DataFrame) -> float:
    for column in ("bar_time_ms", "timestamp_ms", "open_time_ms", "time_ms"):
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce").dropna().sort_values(kind="mergesort")
        diffs = values.diff().dropna()
        diffs = diffs[diffs > 0]
        if not diffs.empty:
            duration = float(diffs.median())
            if math.isfinite(duration) and duration > 0.0:
                return duration
    raise ValueError("label_horizon time units require a monotonic millisecond bar-time column")


def _numeric_matrix(frame: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
    values = frame.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return values.to_numpy(dtype=float)


def _int_marker(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or not parsed.is_integer():
        return None
    return int(parsed)


def _array_min_int(values: np.ndarray) -> int | None:
    return int(np.min(values)) if len(values) else None


def _array_max_int(values: np.ndarray) -> int | None:
    return int(np.max(values)) if len(values) else None


def _list_min_int(values: Sequence[int | None]) -> int | None:
    finite = [int(value) for value in values if value is not None]
    return min(finite) if finite else None


def _list_max_int(values: Sequence[int | None]) -> int | None:
    finite = [int(value) for value in values if value is not None]
    return max(finite) if finite else None


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _blocked_split_record(
    split: WalkForwardSplit,
    *,
    reason: str,
    validation_count: int,
    train_row_count: int = 0,
    label_horizon_bars: int | None = None,
    label_horizon_dropped_count: int = 0,
) -> dict[str, Any]:
    return {
        "split_id": str(split.split_id),
        "status": "blocked",
        "reason": reason,
        "train_row_count": int(train_row_count),
        "validation_row_count": int(validation_count),
        "label_horizon_bars": int(label_horizon_bars) if label_horizon_bars is not None else None,
        "label_horizon_dropped_count": int(label_horizon_dropped_count),
    }


def _split_safety_passed(frame: pd.DataFrame) -> bool:
    evaluated = frame[frame["knn_skip_reason"].ne("not_evaluated") & (pd.to_numeric(frame["neighbor_count"], errors="coerce") > 0)]
    if evaluated.empty:
        return True
    min_source = pd.to_numeric(evaluated["neighbor_min_source_index"], errors="coerce")
    max_source = pd.to_numeric(evaluated["neighbor_max_source_index"], errors="coerce")
    fit_end = pd.to_numeric(evaluated["hmm_fit_end_row"], errors="coerce")
    source_row = pd.to_numeric(evaluated["source_row_index"], errors="coerce")
    return bool(((min_source <= max_source) & (max_source <= fit_end) & (fit_end < source_row)).all())


def _diagnostic_columns() -> list[str]:
    return [
        "split_id",
        "source_row_index",
        "neighbor_source_index",
        "neighbor_rank",
        "neighbor_distance",
        "neighbor_regime",
        "query_regime",
        "label_value",
        "pnl_value",
        "feature_column_set_id",
        "distance_metric",
    ]


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_new_artifact_paths(*paths: Path) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise ValueError("refusing to overwrite existing KNN study artifacts: " + ",".join(existing))


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        frame.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
