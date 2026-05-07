from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from tradingbotsuite.backtesting.splits import WalkForwardSplit
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.snapshots import atomic_write_json


HMM_MATERIALIZATION_SPEC_VERSION = "discovery-hmm-materialization-spec-v1"
HMM_MATERIALIZATION_MANIFEST_VERSION = "discovery-hmm-materialization-manifest-v1"
HMM_MATERIALIZER_VERSION = "discovery-hmm-materializer-v1"
HMM_POSTERIOR_COLUMNS = (
    "top_regime_label",
    "max_regime_probability",
    "posterior_entropy",
    "recent_regime_flip",
    "regime_no_trade",
    "hmm_fit_end_row",
    "source_row_index",
    "hmm_model_id",
    "hmm_feature_pack_id",
    "hmm_split_id",
)
SEMANTIC_REGIME_LABELS = ("range_chop", "bull_trend", "bear_trend", "shock_transition")


@dataclass(frozen=True, slots=True)
class HmmMaterializationSpec:
    feature_columns: tuple[str, ...]
    n_states: int = 4
    posterior_threshold: float = 0.60
    entropy_threshold: float = 0.78
    flip_cooldown_bars: int = 2
    min_training_rows: int = 32
    random_state: int = 73
    max_iter: int = 100
    covariance_type: str = "diag"
    hmm_feature_pack_id: str = "discovery_hmm_price_state_v1"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "HmmMaterializationSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("HMM materialization spec must be a JSON object")
        columns = tuple(str(item).strip() for item in payload.get("feature_columns") or () if str(item).strip())
        spec = cls(
            feature_columns=columns,
            n_states=int(payload.get("n_states", 4)),
            posterior_threshold=float(payload.get("posterior_threshold", 0.60)),
            entropy_threshold=float(payload.get("entropy_threshold", 0.78)),
            flip_cooldown_bars=int(payload.get("flip_cooldown_bars", 2)),
            min_training_rows=int(payload.get("min_training_rows", 32)),
            random_state=int(payload.get("random_state", 73)),
            max_iter=int(payload.get("max_iter", 100)),
            covariance_type=str(payload.get("covariance_type", "diag")).strip(),
            hmm_feature_pack_id=str(payload.get("hmm_feature_pack_id", "discovery_hmm_price_state_v1")).strip(),
        )
        validate_hmm_materialization_spec(spec)
        return spec

    @classmethod
    def from_path(cls, path: Path) -> "HmmMaterializationSpec":
        payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8-sig"))
        return cls.from_payload(payload)

    def to_payload(self) -> dict[str, Any]:
        return {
            "spec_version": HMM_MATERIALIZATION_SPEC_VERSION,
            "feature_columns": list(self.feature_columns),
            "n_states": self.n_states,
            "posterior_threshold": self.posterior_threshold,
            "entropy_threshold": self.entropy_threshold,
            "flip_cooldown_bars": self.flip_cooldown_bars,
            "min_training_rows": self.min_training_rows,
            "random_state": self.random_state,
            "max_iter": self.max_iter,
            "covariance_type": self.covariance_type,
            "hmm_feature_pack_id": self.hmm_feature_pack_id,
        }

    def spec_sha256(self) -> str:
        encoded = json.dumps(self.to_payload(), sort_keys=True, allow_nan=False).encode("utf-8")
        return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class HmmMaterializationResult:
    frame: pd.DataFrame
    manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class HmmMaterializationArtifactResult:
    output_dir: Path
    manifest_path: Path
    regime_posteriors_path: Path
    split_summary_path: Path


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

    def to_payload(self) -> dict[str, Any]:
        return {
            "columns": list(self.columns),
            "median": [float(item) for item in self.median],
            "scale": [float(item) for item in self.scale],
            "fit_scope": "train_split_only",
        }


def validate_hmm_materialization_spec(spec: HmmMaterializationSpec) -> None:
    if not spec.feature_columns:
        raise ValueError("feature_columns must contain at least one column")
    if len(set(spec.feature_columns)) != len(spec.feature_columns):
        raise ValueError("feature_columns must not contain duplicates")
    if spec.n_states < 2:
        raise ValueError("n_states must be at least 2")
    if spec.posterior_threshold <= 0.0 or spec.posterior_threshold > 1.0:
        raise ValueError("posterior_threshold must be between 0 and 1")
    if spec.entropy_threshold <= 0.0 or spec.entropy_threshold > 1.0:
        raise ValueError("entropy_threshold must be between 0 and 1")
    if spec.flip_cooldown_bars < 0:
        raise ValueError("flip_cooldown_bars must be non-negative")
    if spec.min_training_rows < spec.n_states:
        raise ValueError("min_training_rows must be at least n_states")
    if spec.max_iter <= 0:
        raise ValueError("max_iter must be positive")
    if spec.covariance_type not in {"full", "tied", "diag", "spherical"}:
        raise ValueError("covariance_type must be one of full, tied, diag, spherical")
    if not spec.hmm_feature_pack_id:
        raise ValueError("hmm_feature_pack_id must not be empty")


def materialize_split_safe_hmm_regimes(
    frame: pd.DataFrame,
    *,
    splits: Sequence[WalkForwardSplit],
    spec: HmmMaterializationSpec,
) -> HmmMaterializationResult:
    validate_hmm_materialization_spec(spec)
    missing = [column for column in spec.feature_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"hmm_materialization_missing_feature_columns:{','.join(missing)}")
    ordered = frame.reset_index(drop=True).copy()
    source_index = _source_row_index(ordered)
    result = _empty_result(ordered, source_index=source_index, spec=spec)
    split_records: list[dict[str, Any]] = []

    for split_number, split in enumerate(splits, start=1):
        validation_positions = _validation_positions(split, row_count=len(ordered))
        if not validation_positions:
            continue
        fit_end_position = int(split.train_end_index)
        if fit_end_position < int(split.train_start_index) or fit_end_position < 0:
            split_records.append(_blocked_split_record(split, reason="no_training_rows", validation_count=len(validation_positions)))
            continue
        train = ordered.iloc[int(split.train_start_index) : fit_end_position + 1].copy()
        train = train.dropna(subset=list(spec.feature_columns), how="all")
        if len(train) < spec.min_training_rows:
            split_records.append(
                _blocked_split_record(
                    split,
                    reason="insufficient_training_rows",
                    validation_count=len(validation_positions),
                    train_row_count=len(train),
                )
            )
            continue
        train_source_max = int(source_index.iloc[fit_end_position])
        safe_positions = [position for position in validation_positions if int(source_index.iloc[position]) > train_source_max]
        if len(safe_positions) != len(validation_positions):
            split_records.append(
                _blocked_split_record(
                    split,
                    reason="validation_source_rows_not_after_fit_end",
                    validation_count=len(validation_positions),
                    train_row_count=len(train),
                )
            )
            continue
        scaler = _TrainOnlyScaler.fit(train, spec.feature_columns)
        train_matrix = scaler.transform(train)
        validation = ordered.iloc[safe_positions].copy()
        validation_matrix = scaler.transform(validation)
        model = _fit_gaussian_regime_model(train_matrix, spec=spec)
        train_posterior = model.predict_proba(train_matrix)
        validation_posterior = model.predict_proba(validation_matrix)
        labels = _semantic_state_labels(train, train_posterior, spec=spec)
        model_id = _model_id(
            split=split,
            spec=spec,
            scaler=scaler,
            train_source_max=train_source_max,
            state_labels=labels,
        )
        _assign_posterior_rows(
            result,
            positions=safe_positions,
            source_index=source_index,
            posterior=validation_posterior,
            state_labels=labels,
            split_id=str(split.split_id),
            fit_end_row=train_source_max,
            model_id=model_id,
            spec=spec,
        )
        split_records.append(
            {
                "split_id": str(split.split_id),
                "status": "materialized",
                "train_row_count": int(len(train)),
                "validation_row_count": int(len(safe_positions)),
                "hmm_fit_end_row": train_source_max,
                "hmm_model_id": model_id,
                "scaler": scaler.to_payload(),
                "state_labels": {str(key): value for key, value in labels.items()},
            }
        )

    manifest = {
        "hmm_materialization_manifest_version": HMM_MATERIALIZATION_MANIFEST_VERSION,
        "materializer_version": HMM_MATERIALIZER_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec": spec.to_payload(),
        "spec_sha256": spec.spec_sha256(),
        "row_count": int(len(result)),
        "materialized_row_count": int((pd.to_numeric(result["hmm_fit_end_row"], errors="coerce") >= 0).sum()),
        "split_count": int(len(splits)),
        "split_records": split_records,
        "required_output_columns": list(HMM_POSTERIOR_COLUMNS),
        "split_safety_rule": "hmm_fit_end_row < source_row_index",
        "split_safety_passed": bool(_split_safety_passed(result)),
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    return HmmMaterializationResult(frame=result, manifest=manifest)


def write_hmm_materialization_artifacts(
    output_dir: Path,
    result: HmmMaterializationResult,
) -> HmmMaterializationArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    regime_posteriors_path = output_dir / "regime_posteriors.parquet"
    split_summary_path = output_dir / "hmm_split_summary.parquet"
    manifest_path = output_dir / "hmm_materialization_manifest.json"
    result.frame.to_parquet(regime_posteriors_path, index=False)
    pd.DataFrame(result.manifest.get("split_records") or []).to_parquet(split_summary_path, index=False)
    manifest = dict(result.manifest)
    manifest["required_outputs"] = {
        "hmm_materialization_manifest": str(manifest_path),
        "regime_posteriors": str(regime_posteriors_path),
        "hmm_split_summary": str(split_summary_path),
    }
    manifest["regime_posteriors_sha256"] = _file_sha256(regime_posteriors_path)
    manifest["hmm_split_summary_sha256"] = _file_sha256(split_summary_path)
    atomic_write_json(manifest_path, manifest)
    return HmmMaterializationArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        regime_posteriors_path=regime_posteriors_path,
        split_summary_path=split_summary_path,
    )


def _empty_result(frame: pd.DataFrame, *, source_index: pd.Series, spec: HmmMaterializationSpec) -> pd.DataFrame:
    result = frame.copy()
    for state in range(spec.n_states):
        result[f"regime_p_{state}"] = np.nan
    result["top_regime_label"] = "unknown"
    result["max_regime_probability"] = np.nan
    result["posterior_entropy"] = np.nan
    result["recent_regime_flip"] = True
    result["regime_no_trade"] = True
    result["hmm_fit_end_row"] = -1
    result["source_row_index"] = source_index.astype("int64")
    result["hmm_model_id"] = ""
    result["hmm_feature_pack_id"] = spec.hmm_feature_pack_id
    result["hmm_split_id"] = ""
    return result


def _assign_posterior_rows(
    result: pd.DataFrame,
    *,
    positions: Sequence[int],
    source_index: pd.Series,
    posterior: np.ndarray,
    state_labels: Mapping[int, str],
    split_id: str,
    fit_end_row: int,
    model_id: str,
    spec: HmmMaterializationSpec,
) -> None:
    top_state = posterior.argmax(axis=1) if len(posterior) else np.array([], dtype=int)
    top_probability = posterior.max(axis=1) if len(posterior) else np.array([], dtype=float)
    safe_posterior = np.clip(posterior, 1e-12, 1.0)
    entropy = -np.sum(safe_posterior * np.log(safe_posterior), axis=1) / math.log(max(spec.n_states, 2))
    recent_flip = _recent_flip_flags(top_state, cooldown=spec.flip_cooldown_bars)
    for local_index, position in enumerate(positions):
        for state in range(spec.n_states):
            result.loc[position, f"regime_p_{state}"] = float(posterior[local_index, state])
        result.loc[position, "top_regime_label"] = state_labels.get(int(top_state[local_index]), f"state_{top_state[local_index]}")
        result.loc[position, "max_regime_probability"] = float(top_probability[local_index])
        result.loc[position, "posterior_entropy"] = float(entropy[local_index])
        result.loc[position, "recent_regime_flip"] = bool(recent_flip[local_index])
        result.loc[position, "regime_no_trade"] = bool(
            top_probability[local_index] < spec.posterior_threshold
            or entropy[local_index] > spec.entropy_threshold
            or recent_flip[local_index]
        )
        result.loc[position, "hmm_fit_end_row"] = int(fit_end_row)
        result.loc[position, "source_row_index"] = int(source_index.iloc[position])
        result.loc[position, "hmm_model_id"] = model_id
        result.loc[position, "hmm_feature_pack_id"] = spec.hmm_feature_pack_id
        result.loc[position, "hmm_split_id"] = split_id


def _fit_gaussian_regime_model(matrix: np.ndarray, *, spec: HmmMaterializationSpec) -> GaussianMixture:
    model = GaussianMixture(
        n_components=spec.n_states,
        covariance_type=spec.covariance_type,
        random_state=spec.random_state,
        max_iter=spec.max_iter,
    )
    model.fit(matrix)
    return model


def _semantic_state_labels(
    train: pd.DataFrame,
    posterior: np.ndarray,
    *,
    spec: HmmMaterializationSpec,
) -> dict[int, str]:
    top_state = posterior.argmax(axis=1) if len(posterior) else np.array([], dtype=int)
    stats: list[dict[str, float | int]] = []
    for state in range(spec.n_states):
        rows = train.iloc[np.where(top_state == state)[0]]
        stats.append(
            {
                "state": state,
                "slope": _mean_or_default(rows, "directional_slope_atr", 0.0),
                "vol": _mean_or_default(rows, "realized_volatility", 0.0),
                "chop": _mean_or_default(rows, "choppiness", 50.0),
            }
        )
    labels = {state: SEMANTIC_REGIME_LABELS[min(state, len(SEMANTIC_REGIME_LABELS) - 1)] for state in range(spec.n_states)}
    if spec.n_states >= 4:
        shock = int(max(stats, key=lambda item: (float(item["vol"]), float(item["chop"]), -int(item["state"])))["state"])
        bull = int(max((item for item in stats if int(item["state"]) != shock), key=lambda item: (float(item["slope"]), -int(item["state"])))["state"])
        bear = int(min((item for item in stats if int(item["state"]) not in {shock, bull}), key=lambda item: (float(item["slope"]), int(item["state"])))["state"])
        labels = {state: "range_chop" for state in range(spec.n_states)}
        labels[shock] = "shock_transition"
        labels[bull] = "bull_trend"
        labels[bear] = "bear_trend"
    return labels


def _validation_positions(split: WalkForwardSplit, *, row_count: int) -> list[int]:
    if split.validation_indices is not None:
        return [int(position) for position in split.validation_indices if 0 <= int(position) < row_count]
    start = max(0, int(split.validation_start_index))
    end = min(row_count - 1, int(split.validation_end_index))
    if end < start:
        return []
    return list(range(start, end + 1))


def _source_row_index(frame: pd.DataFrame) -> pd.Series:
    if "source_row_index" in frame.columns:
        series = pd.to_numeric(frame["source_row_index"], errors="raise").astype("int64")
        if not series.is_monotonic_increasing:
            raise ValueError("source_row_index must be monotonic increasing")
        return series.reset_index(drop=True)
    return pd.Series(range(len(frame)), dtype="int64")


def _numeric_matrix(frame: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
    values = frame.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return values.to_numpy(dtype=float)


def _recent_flip_flags(top_state: np.ndarray, *, cooldown: int) -> np.ndarray:
    recent_flip = np.zeros(len(top_state), dtype=bool)
    last_flip: int | None = None
    for index in range(1, len(top_state)):
        if top_state[index] != top_state[index - 1]:
            last_flip = index
        if last_flip is not None and index - last_flip <= cooldown:
            recent_flip[index] = True
    return recent_flip


def _mean_or_default(frame: pd.DataFrame, column: str, default: float) -> float:
    if column not in frame.columns or frame.empty:
        return default
    value = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).mean()
    if pd.isna(value):
        return default
    return float(value)


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
        "hmm_fit_end_row": None,
        "hmm_model_id": "",
    }


def _model_id(
    *,
    split: WalkForwardSplit,
    spec: HmmMaterializationSpec,
    scaler: _TrainOnlyScaler,
    train_source_max: int,
    state_labels: Mapping[int, str],
) -> str:
    payload = {
        "split_id": split.split_id,
        "spec_sha256": spec.spec_sha256(),
        "train_source_max": int(train_source_max),
        "scaler": scaler.to_payload(),
        "state_labels": {str(key): value for key, value in state_labels.items()},
        "backend": "gaussian_mixture",
    }
    digest = sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()
    return f"gaussian_mixture:{digest[:16]}"


def _split_safety_passed(frame: pd.DataFrame) -> bool:
    materialized = frame[pd.to_numeric(frame["hmm_fit_end_row"], errors="coerce") >= 0]
    if materialized.empty:
        return True
    fit_end = pd.to_numeric(materialized["hmm_fit_end_row"], errors="coerce")
    source_row = pd.to_numeric(materialized["source_row_index"], errors="coerce")
    return bool((fit_end < source_row).all())


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
