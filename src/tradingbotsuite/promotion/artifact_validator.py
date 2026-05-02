from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ArtifactValidationResult:
    allowed: bool
    reasons: tuple[str, ...]
    manifest_path: Path | None = None
    artifact_type: str = "unknown"


def load_artifact_manifest(path: Path | str) -> dict[str, Any]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact manifest must be a JSON object: {manifest_path}")
    return payload


def validate_artifact_for_live_input(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> ArtifactValidationResult:
    reasons: list[str] = []
    artifact_type = _artifact_type(manifest)
    if manifest.get("research_only") is True:
        reasons.append("research_only_artifact_rejected_for_live_input")
    if manifest.get("observe_only") is True:
        reasons.append("observe_only_artifact_rejected_for_live_input")
    if manifest.get("promotion_ready") is not True:
        reasons.append("promotion_ready_false_or_missing")
    intended_use = str(manifest.get("intended_use") or "").strip().lower()
    if intended_use in {"research", "research_only", "observe_only", "research_observe_only"}:
        reasons.append(f"research_intended_use_rejected:{intended_use}")
    if manifest.get("live_signal_input") is False:
        reasons.append("manifest_declares_not_live_signal_input")
    if manifest.get("position_sizing_input") is False:
        reasons.append("manifest_declares_not_position_sizing_input")
    if manifest.get("live_execution_input") is False:
        reasons.append("manifest_declares_not_live_execution_input")
    return ArtifactValidationResult(
        allowed=not reasons,
        reasons=tuple(reasons),
        manifest_path=manifest_path,
        artifact_type=artifact_type,
    )


def _artifact_type(manifest: Mapping[str, Any]) -> str:
    for key in (
        "artifact_manifest_version",
        "experiment_manifest_version",
        "experiment_run_manifest_version",
        "backtest_manifest_version",
        "dataset_manifest_version",
    ):
        if manifest.get(key):
            return key.removesuffix("_version")
    return "unknown"
