from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from tradingbotsuite.backtesting.splits import WalkForwardSplit
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.snapshots import atomic_write_json


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
    feature_column_set_id: str = "price_trend_vol"
    label_horizon: str = "4h"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "KnnStudySpec":
        if not isinstance(payload, Mapping):
            raise ValueError("KNN study spec must be a JSON object")
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
            same_regime_only=bool(payload.get("same_regime_only", True)),
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
        median = np.nanmedian(matrix, axis=0)
        q75 = np.nanpercentile(matrix, 75, axis=0)
        q25 = np.nanpercentile(matrix, 25, axis=0)
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


def materialize_regime_local_knn_predictions(
    frame: pd.DataFrame,
    *,
    splits: Sequence[WalkForwardSplit],
    spec: KnnStudySpec,
) -> KnnStudyResult:
    validate_knn_study_spec(spec)
    missing = [column for column in (*spec.feature_columns, spec.label_column, spec.pnl_column, *REQUIRED_HMM_COLUMNS) if column not in frame.columns]
    if missing:
        raise ValueError(f"knn_study_missing_columns:{','.join(missing)}")
    ordered = frame.reset_index(drop=True).copy()
    result = _empty_result(ordered)
    diagnostics: list[dict[str, Any]] = []
    split_records: list[dict[str, Any]] = []

    for split in splits:
        validation_positions = _validation_positions(split, row_count=len(ordered))
        if not validation_positions:
            continue
        train_positions = list(range(max(0, int(split.train_start_index)), max(-1, int(split.train_end_index)) + 1))
        if not train_positions:
            split_records.append(_blocked_split_record(split, reason="no_training_rows", validation_count=len(validation_positions)))
            continue
        train = ordered.iloc[train_positions].copy()
        train = train.dropna(subset=[spec.label_column, spec.pnl_column], how="any")
        if len(train) < spec.min_neighbor_count:
            split_records.append(
                _blocked_split_record(
                    split,
                    reason="insufficient_labeled_training_rows",
                    validation_count=len(validation_positions),
                    train_row_count=len(train),
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

        for position in validation_positions:
            row = ordered.iloc[position]
            prediction, row_diagnostics = _predict_row(
                row,
                train_matrix=train_matrix,
                train_source=train_source,
                train_regimes=train_regimes,
                labels=labels,
                pnl=pnl,
                scaler=scaler,
                spec=spec,
                split_id=str(split.split_id),
            )
            for key, value in prediction.items():
                result.loc[position, key] = value
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
        "split_safety_rule": "neighbor_min_source_index <= neighbor_max_source_index <= hmm_fit_end_row < source_row_index",
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
    result.frame.to_parquet(predictions_path, index=False)
    result.neighbor_diagnostics.to_parquet(diagnostics_path, index=False)
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
    if source_row is None or fit_end is None or fit_end < 0 or fit_end >= source_row:
        return _skip_prediction("unsafe_hmm_split_row"), []
    if bool(row.get("regime_no_trade")):
        return _skip_prediction("hmm_regime_no_trade"), []
    query_regime = str(row.get("top_regime_label") or "")
    candidate_mask = train_source <= fit_end
    if spec.same_regime_only:
        candidate_mask = candidate_mask & (train_regimes == query_regime)
    candidate_indices = np.where(candidate_mask)[0]
    if len(candidate_indices) < spec.min_neighbor_count:
        return _skip_prediction("insufficient_regime_neighbors"), []

    query_matrix = scaler.transform(pd.DataFrame([row], columns=row.index))[0]
    distances = _distances(query_matrix, train_matrix[candidate_indices], metric=spec.distance_metric)
    order = np.argsort(distances, kind="mergesort")[: min(spec.k, len(candidate_indices))]
    selected = candidate_indices[order]
    selected_distances = distances[order]
    selected_labels = labels[selected]
    selected_pnl = pnl[selected]
    p_up = float(selected_labels.mean())
    p_down = float(1.0 - p_up)
    expected_value = float(selected_pnl.mean())
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
    diagnostics = [
        {
            "split_id": split_id,
            "source_row_index": int(source_row),
            "neighbor_source_index": int(train_source[index]),
            "neighbor_rank": int(rank + 1),
            "neighbor_distance": float(selected_distances[rank]),
            "neighbor_regime": str(train_regimes[index]),
            "query_regime": query_regime,
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


def _blocked_split_record(
    split: WalkForwardSplit,
    *,
    reason: str,
    validation_count: int,
    train_row_count: int = 0,
) -> dict[str, Any]:
    return {
        "split_id": str(split.split_id),
        "status": "blocked",
        "reason": reason,
        "train_row_count": int(train_row_count),
        "validation_row_count": int(validation_count),
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
