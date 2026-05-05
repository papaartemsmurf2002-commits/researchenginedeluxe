from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


FEATURE_CACHE_VERSION = "research-feature-cache-v1"


@dataclass(frozen=True, slots=True)
class FeatureCacheIdentity:
    dataset_sha256: str
    feature_set_id: str
    feature_manifest_sha256: str
    builder_version: str
    interval_ms: int
    source_column_mapping: Mapping[str, str]
    split_id: str | None = None
    require_continuous: bool = True
    fixture_family_context_sha256: str | None = None

    def key(self) -> str:
        return sha256(_canonical_json(self.to_payload()).encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, Any]:
        return {
            "cache_version": FEATURE_CACHE_VERSION,
            "dataset_sha256": self.dataset_sha256,
            "feature_set_id": self.feature_set_id,
            "feature_manifest_sha256": self.feature_manifest_sha256,
            "builder_version": self.builder_version,
            "interval_ms": int(self.interval_ms),
            "source_column_mapping": dict(sorted(self.source_column_mapping.items())),
            "split_id": self.split_id,
            "require_continuous": bool(self.require_continuous),
            "fixture_family_context_sha256": self.fixture_family_context_sha256,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }


def feature_cache_paths(cache_root: Path, identity: FeatureCacheIdentity) -> tuple[Path, Path]:
    root = Path(cache_root).expanduser() / identity.key()
    return root / "features.parquet", root / "feature_cache_manifest.json"


def load_feature_cache_artifact(cache_root: Path, identity: FeatureCacheIdentity) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    feature_path, manifest_path = feature_cache_paths(cache_root, identity)
    if not feature_path.exists() or not manifest_path.exists():
        return None
    manifest = read_feature_cache_manifest(manifest_path)
    if manifest.get("feature_cache_key") != identity.key():
        return None
    if manifest.get("cache_version") != FEATURE_CACHE_VERSION:
        return None
    for key, expected_value in identity.to_payload().items():
        if manifest.get(key) != expected_value:
            return None
    if manifest.get("feature_path") != str(feature_path):
        return None
    if manifest.get("feature_artifact_sha256") != _file_sha256(feature_path):
        return None
    feature_columns = tuple(str(column) for column in manifest.get("feature_columns", ()))
    availability_columns = tuple(str(column) for column in manifest.get("availability_columns", ()))
    if not feature_columns or not availability_columns:
        return None
    feature_manifest = manifest.get("feature_manifest")
    if not isinstance(feature_manifest, Mapping):
        return None
    if feature_manifest.get("manifest_sha256") != identity.feature_manifest_sha256:
        return None
    if feature_manifest.get("feature_set_id") != identity.feature_set_id:
        return None
    if tuple(str(column) for column in feature_manifest.get("feature_columns", ())) != feature_columns:
        return None
    if tuple(str(column) for column in feature_manifest.get("availability_columns", ())) != availability_columns:
        return None
    frame = pd.read_parquet(feature_path)
    if int(manifest.get("row_count", -1)) != int(len(frame)):
        return None
    required_columns = {"bar_time_ms", "feature_time_ms", *feature_columns, *availability_columns}
    if not required_columns.issubset(set(frame.columns)):
        return None
    if manifest.get("feature_frame_sha256") != _frame_sha256(frame):
        return None
    return frame, manifest


def write_feature_cache_artifact(
    cache_root: Path,
    identity: FeatureCacheIdentity,
    *,
    frame: pd.DataFrame,
    feature_columns: tuple[str, ...],
    availability_columns: tuple[str, ...],
    feature_manifest: Mapping[str, Any],
    availability_report: Mapping[str, Any],
    materialization_scope: str,
    fixture_family_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    feature_path, manifest_path = feature_cache_paths(cache_root, identity)
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(feature_path, index=False)
    write_feature_cache_manifest(
        manifest_path,
        identity,
        row_count=len(frame),
        feature_path=feature_path,
        feature_frame_sha256=_frame_sha256(frame),
        feature_artifact_sha256=_file_sha256(feature_path),
        feature_columns=feature_columns,
        availability_columns=availability_columns,
        feature_manifest=feature_manifest,
        availability_report=availability_report,
        materialization_scope=materialization_scope,
        fixture_family_context=fixture_family_context,
    )
    return read_feature_cache_manifest(manifest_path)


def read_feature_cache_manifest(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_feature_cache_manifest(
    path: Path,
    identity: FeatureCacheIdentity,
    *,
    row_count: int,
    feature_path: Path | None = None,
    feature_frame_sha256: str | None = None,
    feature_artifact_sha256: str | None = None,
    feature_columns: tuple[str, ...] = (),
    availability_columns: tuple[str, ...] = (),
    feature_manifest: Mapping[str, Any] | None = None,
    availability_report: Mapping[str, Any] | None = None,
    materialization_scope: str | None = None,
    fixture_family_context: Mapping[str, Any] | None = None,
) -> None:
    payload = {
        **identity.to_payload(),
        "feature_cache_key": identity.key(),
        "row_count": int(row_count),
        "feature_path": str(feature_path) if feature_path is not None else None,
        "feature_frame_sha256": feature_frame_sha256,
        "feature_artifact_sha256": feature_artifact_sha256,
        "feature_columns": list(feature_columns),
        "availability_columns": list(availability_columns),
        "feature_manifest": dict(feature_manifest or {}),
        "availability_report": dict(availability_report or {}),
        "materialization_scope": materialization_scope,
        "fixture_family_context": dict(fixture_family_context or {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_sha256(frame: pd.DataFrame) -> str:
    if frame.empty:
        return sha256(_canonical_json({"columns": list(frame.columns), "rows": []}).encode("utf-8")).hexdigest()
    normalized = frame.reindex(sorted(frame.columns), axis=1)
    payload = normalized.to_csv(index=False, lineterminator="\n", float_format="%.12g")
    return sha256(payload.encode("utf-8")).hexdigest()


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":") if indent is None else None, indent=indent, default=str)
