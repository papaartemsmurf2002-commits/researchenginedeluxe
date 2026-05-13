from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from tradingbotsuite.core.features import RESEARCH_FEATURE_COLUMNS, confidence_bucket, size_multiplier_candidate
from tradingbotsuite.research.config import ResearchPlan
from tradingbotsuite.research.live_readiness import research_artifact_boundary_metadata

TRAIN_MANIFEST_VERSION = "v2-train-manifest-1"
ARTIFACT_MANIFEST_VERSION = "v2-artifact-manifest-1"
ALLOWED_TRAINING_SOURCES = {
    "external_signal",
    "research_signal",
    "provider_signal",
}


class _BaseCalibrator:
    method: str

    def predict(self, features: np.ndarray, base_probabilities: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class IsotonicCalibrator(_BaseCalibrator):
    method = "isotonic"

    def __init__(self, model: IsotonicRegression):
        self.model = model

    def predict(self, features: np.ndarray, base_probabilities: np.ndarray) -> np.ndarray:
        return self.model.predict(base_probabilities)


class PlattCalibrator(_BaseCalibrator):
    method = "platt"

    def __init__(self, model: LogisticRegression):
        self.model = model

    def predict(self, features: np.ndarray, base_probabilities: np.ndarray) -> np.ndarray:
        logits = np.log(np.clip(base_probabilities, 1e-6, 1 - 1e-6) / np.clip(1 - base_probabilities, 1e-6, 1 - 1e-6))
        return self.model.predict_proba(logits.reshape(-1, 1))[:, 1]


@dataclass(frozen=True, slots=True)
class TrainArtifacts:
    artifact_dir: Path
    manifest_path: Path


def _dataset_features(frame: pd.DataFrame, feature_columns: list[str]) -> np.ndarray:
    return frame.loc[:, feature_columns].fillna(0.0).astype(float).to_numpy()


def validate_training_sources(frame: pd.DataFrame) -> None:
    if "source" not in frame.columns:
        return
    sources = {str(source) for source in frame["source"].dropna().unique()}
    disallowed = sorted(sources - ALLOWED_TRAINING_SOURCES)
    if disallowed:
        raise ValueError(
            "dataset contains non-approved research sources and is unsafe for model training: "
            + ", ".join(disallowed)
        )


def fit_model_and_calibrator(
    *,
    train_frame: pd.DataFrame,
    calibration_frame: pd.DataFrame,
    feature_columns: list[str],
    plan: ResearchPlan,
) -> tuple[Any, _BaseCalibrator]:
    if len(train_frame) < plan.evaluation.min_training_rows:
        raise ValueError("insufficient rows for training")
    train_labels = train_frame["label_accept"].astype(int).to_numpy()
    if len(set(train_labels.tolist())) < 2:
        raise ValueError("training data needs both classes")

    model = LogisticRegression(
        max_iter=plan.model.max_iter,
        random_state=plan.model.random_state,
        class_weight="balanced",
    )
    model.fit(_dataset_features(train_frame, feature_columns), train_labels)

    if len(calibration_frame) < plan.evaluation.min_calibration_rows:
        raise ValueError("insufficient rows for calibration")
    calibration_labels = calibration_frame["label_accept"].astype(int).to_numpy()
    if len(set(calibration_labels.tolist())) < 2:
        raise ValueError("calibration data needs both classes")
    base_probabilities = model.predict_proba(_dataset_features(calibration_frame, feature_columns))[:, 1]
    if len(calibration_frame) >= max(30, plan.evaluation.min_calibration_rows):
        calibrator: _BaseCalibrator = IsotonicCalibrator(IsotonicRegression(out_of_bounds="clip").fit(base_probabilities, calibration_labels))
    else:
        platt = LogisticRegression(max_iter=plan.model.max_iter, random_state=plan.model.random_state)
        logits = np.log(np.clip(base_probabilities, 1e-6, 1 - 1e-6) / np.clip(1 - base_probabilities, 1e-6, 1 - 1e-6))
        platt.fit(logits.reshape(-1, 1), calibration_labels)
        calibrator = PlattCalibrator(platt)
    return model, calibrator


def train_base_model(dataset_path: Path, plan: ResearchPlan, output_dir: Path) -> TrainArtifacts:
    frame = pd.read_parquet(dataset_path).sort_values("signal_bar_time_ms").reset_index(drop=True)
    validate_training_sources(frame)
    feature_columns = [column for column in RESEARCH_FEATURE_COLUMNS if column in frame.columns]
    split_index = max(plan.evaluation.min_training_rows, int(len(frame) * plan.evaluation.train_fraction))
    train_frame = frame.iloc[:split_index].copy()
    calibration_end = split_index + max(plan.evaluation.min_calibration_rows, int(len(frame) * plan.evaluation.calibration_fraction))
    calibration_frame = frame.iloc[split_index:calibration_end].copy()
    if len(calibration_frame) < plan.evaluation.min_calibration_rows:
        calibration_frame = frame.iloc[split_index:].copy()
    model, _ = fit_model_and_calibrator(
        train_frame=train_frame,
        calibration_frame=calibration_frame,
        feature_columns=feature_columns,
        plan=plan,
    )

    artifact_dir = output_dir / f"{plan.version}-{frame['symbol'].iloc[0].lower()}-artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)

    plan_payload = plan.to_payload()
    (artifact_dir / "plan.json").write_text(json.dumps(plan_payload, indent=2, sort_keys=True), encoding="utf-8")

    manifest = {
        "train_manifest_version": TRAIN_MANIFEST_VERSION,
        **research_artifact_boundary_metadata(),
        "plan_file": "plan.json",
        "dataset_path": str(dataset_path),
        "feature_columns": feature_columns,
        "feature_version": str(frame["feature_version"].iloc[0]) if "feature_version" in frame.columns else "unknown",
        "label_version": str(frame["label_version"].iloc[0]) if "label_version" in frame.columns else "unknown",
        "model_file": model_path.name,
        "model_version": f"{plan.version}-logreg",
        "train_rows": len(train_frame),
        "calibration_rows_planned": len(calibration_frame),
        "total_rows": len(frame),
        "split_index": split_index,
        "plan_sha256": plan.plan_sha256(),
    }
    manifest_path = artifact_dir / "train_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return TrainArtifacts(artifact_dir=artifact_dir, manifest_path=manifest_path)


def calibrate_model(train_manifest_path: Path, plan: ResearchPlan) -> Path:
    manifest = json.loads(train_manifest_path.read_text(encoding="utf-8"))
    artifact_dir = train_manifest_path.parent
    frame = pd.read_parquet(Path(manifest["dataset_path"])).sort_values("signal_bar_time_ms").reset_index(drop=True)
    validate_training_sources(frame)
    feature_columns = list(manifest["feature_columns"])
    split_index = int(manifest["split_index"])
    calibration_end = split_index + max(plan.evaluation.min_calibration_rows, int(len(frame) * plan.evaluation.calibration_fraction))
    calibration_frame = frame.iloc[split_index:calibration_end].copy()
    if len(calibration_frame) < plan.evaluation.min_calibration_rows:
        calibration_frame = frame.iloc[split_index:].copy()
    train_frame = frame.iloc[:split_index].copy()
    model, calibrator = fit_model_and_calibrator(
        train_frame=train_frame,
        calibration_frame=calibration_frame,
        feature_columns=feature_columns,
        plan=plan,
    )

    calibrator_path = artifact_dir / "calibrator.pkl"
    with calibrator_path.open("wb") as handle:
        pickle.dump(calibrator, handle)

    full_manifest = {
        **manifest,
        **research_artifact_boundary_metadata(),
        "artifact_manifest_version": ARTIFACT_MANIFEST_VERSION,
        "calibrator_file": calibrator_path.name,
        "calibration_method": calibrator.method,
        "calibration_version": f"{plan.version}-{calibrator.method}",
        "calibration_rows": len(calibration_frame),
    }
    full_manifest_path = artifact_dir / "artifact_manifest.json"
    full_manifest_path.write_text(json.dumps(full_manifest, indent=2, sort_keys=True), encoding="utf-8")
    return full_manifest_path


def score_frame(frame: pd.DataFrame, *, model: Any, calibrator: _BaseCalibrator, feature_columns: list[str], plan: ResearchPlan) -> pd.DataFrame:
    features = _dataset_features(frame, feature_columns)
    base_probabilities = model.predict_proba(features)[:, 1]
    probabilities = calibrator.predict(features, base_probabilities)
    scored = frame.copy()
    scored["base_probability"] = base_probabilities
    scored["accept_probability"] = probabilities
    scored["confidence_bucket"] = [
        confidence_bucket(float(probability), plan.model.confidence_bucket_thresholds) for probability in probabilities
    ]
    scored["size_multiplier_candidate"] = [
        size_multiplier_candidate(float(probability), plan.model.size_multiplier_thresholds, plan.model.size_multiplier_values)
        for probability in probabilities
    ]
    scored["accepted_by_model"] = scored["accept_probability"] >= plan.model.probability_threshold
    return scored
