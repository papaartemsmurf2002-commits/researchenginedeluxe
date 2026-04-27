from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from tradingbotsuite.core.features import RESEARCH_FEATURE_COLUMNS, confidence_bucket, numeric_feature_map, size_multiplier_candidate
from tradingbotsuite.research.config import ResearchPlan, load_research_plan


class AcceptanceScorer:
    def __init__(self, manifest: dict[str, Any], plan: ResearchPlan, model: Any, calibrator: Any, *, manifest_sha256: str):
        self.manifest = manifest
        self.plan = plan
        self.model = model
        self.calibrator = calibrator
        self.feature_columns = list(manifest.get("feature_columns") or RESEARCH_FEATURE_COLUMNS)
        self.manifest_sha256 = manifest_sha256

    @classmethod
    def from_manifest_path(cls, manifest_path: Path) -> "AcceptanceScorer":
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(manifest_text)
        artifact_dir = manifest_path.parent
        plan = load_research_plan(artifact_dir / manifest["plan_file"])
        with (artifact_dir / manifest["model_file"]).open("rb") as handle:
            model = pickle.load(handle)
        with (artifact_dir / manifest["calibrator_file"]).open("rb") as handle:
            calibrator = pickle.load(handle)
        return cls(
            manifest,
            plan,
            model,
            calibrator,
            manifest_sha256=hashlib.sha256(manifest_text.encode("utf-8")).hexdigest(),
        )

    def score_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        snapshot_feature_version = snapshot.get("feature_version")
        manifest_feature_version = self.manifest.get("feature_version")
        if (
            snapshot_feature_version is not None
            and manifest_feature_version is not None
            and str(snapshot_feature_version) != str(manifest_feature_version)
        ):
            raise ValueError(
                f"feature_version_mismatch snapshot={snapshot_feature_version} artifact={manifest_feature_version}"
            )
        features = numeric_feature_map(snapshot)
        row = np.array([[features.get(column, 0.0) for column in self.feature_columns]], dtype=float)
        base_probability = float(self.model.predict_proba(row)[0, 1])
        accept_probability = float(self.calibrator.predict(row, np.array([base_probability], dtype=float))[0])
        return {
            "observe_only": True,
            "accept_probability": round(accept_probability, 6),
            "base_probability": round(base_probability, 6),
            "confidence_bucket": confidence_bucket(accept_probability, self.plan.model.confidence_bucket_thresholds),
            "size_multiplier_candidate": round(
                size_multiplier_candidate(
                    accept_probability,
                    self.plan.model.size_multiplier_thresholds,
                    self.plan.model.size_multiplier_values,
                ),
                6,
            ),
            "feature_columns": self.feature_columns,
            "model_version": self.manifest["model_version"],
            "calibration_version": self.manifest["calibration_version"],
            "probability_threshold": self.plan.model.probability_threshold,
            "artifact_manifest_version": self.manifest.get("artifact_manifest_version") or self.manifest.get("train_manifest_version"),
            "artifact_manifest_sha256": self.manifest_sha256,
            "scoring_fallback_reason": None,
        }
