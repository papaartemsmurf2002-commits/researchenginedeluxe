from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from tradingbotsuite.features.registry import manifest_from_preset


DISCOVERY_FEATURE_COLUMN_SET_MANIFEST_VERSION = "discovery-feature-column-set-manifest-v1"
DISCOVERY_FEATURE_COLUMN_SET_VERSION = "v1"
DEFAULT_MAX_ENABLED_DIMENSIONS = 8
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True, slots=True)
class DiscoveryFeatureColumnSet:
    feature_column_set_id: str
    registered_feature_set_id: str
    columns: tuple[str, ...]
    scaler_policy: str = "train_only_robust_zscore"
    clamp_policy: str = "train_only_clip_5_95"
    maximum_dimensions: int = DEFAULT_MAX_ENABLED_DIMENSIONS
    required_comparator_set: str | None = None
    allowed_experimental_additions: tuple[str, ...] = ()
    enabled: bool = True
    disabled_reason: str = ""
    role: str = "knn_feature_matrix"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DiscoveryFeatureColumnSet":
        if not isinstance(payload, Mapping):
            raise ValueError("feature_column_sets entries must be JSON objects")
        columns = tuple(str(item).strip() for item in payload.get("columns") or () if str(item).strip())
        additions = tuple(
            str(item).strip()
            for item in payload.get("allowed_experimental_additions") or ()
            if str(item).strip()
        )
        required_comparator = payload.get("required_comparator_set")
        return cls(
            feature_column_set_id=str(payload.get("feature_column_set_id") or "").strip(),
            registered_feature_set_id=str(payload.get("registered_feature_set_id") or "").strip(),
            columns=columns,
            scaler_policy=str(payload.get("scaler_policy", "train_only_robust_zscore")).strip(),
            clamp_policy=str(payload.get("clamp_policy", "train_only_clip_5_95")).strip(),
            maximum_dimensions=int(payload.get("maximum_dimensions", DEFAULT_MAX_ENABLED_DIMENSIONS)),
            required_comparator_set=(
                str(required_comparator).strip()
                if required_comparator is not None and str(required_comparator).strip()
                else None
            ),
            allowed_experimental_additions=additions,
            enabled=bool(payload.get("enabled", True)),
            disabled_reason=str(payload.get("disabled_reason", "")).strip(),
            role=str(payload.get("role", "knn_feature_matrix")).strip() or "knn_feature_matrix",
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "feature_column_set_id": self.feature_column_set_id,
            "registered_feature_set_id": self.registered_feature_set_id,
            "columns": list(self.columns),
            "scaler_policy": self.scaler_policy,
            "clamp_policy": self.clamp_policy,
            "maximum_dimensions": self.maximum_dimensions,
            "required_comparator_set": self.required_comparator_set,
            "allowed_experimental_additions": list(self.allowed_experimental_additions),
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason,
            "role": self.role,
        }

    @property
    def contains_wt3d(self) -> bool:
        return any(column.startswith("wt3d_") for column in self.columns)


@dataclass(frozen=True, slots=True)
class DiscoveryFeatureColumnSetManifest:
    manifest_id: str
    feature_column_sets: tuple[DiscoveryFeatureColumnSet, ...]
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    notes: tuple[str, ...] = ()
    manifest_sha256: str = ""

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DiscoveryFeatureColumnSetManifest":
        if not isinstance(payload, Mapping):
            raise ValueError("discovery feature-column set manifest must be a JSON object")
        sets = tuple(
            DiscoveryFeatureColumnSet.from_payload(item)
            for item in payload.get("feature_column_sets") or ()
        )
        manifest = cls(
            manifest_id=str(payload.get("manifest_id") or "discovery_feature_column_sets_v4").strip(),
            feature_column_sets=sets,
            research_only=bool(payload.get("research_only", True)),
            observe_only=bool(payload.get("observe_only", True)),
            promotion_ready=bool(payload.get("promotion_ready", False)),
            notes=tuple(str(item) for item in payload.get("notes") or ()),
            manifest_sha256=str(payload.get("manifest_sha256") or ""),
        )
        validate_feature_column_set_manifest(manifest)
        expected_hash = stable_feature_column_set_hash(manifest.to_payload(include_hash=False))
        if manifest.manifest_sha256 and manifest.manifest_sha256 != expected_hash:
            raise ValueError("feature column set manifest hash mismatch")
        return DiscoveryFeatureColumnSetManifest(
            manifest_id=manifest.manifest_id,
            feature_column_sets=manifest.feature_column_sets,
            research_only=manifest.research_only,
            observe_only=manifest.observe_only,
            promotion_ready=manifest.promotion_ready,
            notes=manifest.notes,
            manifest_sha256=manifest.manifest_sha256 or expected_hash,
        )

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "manifest_version": DISCOVERY_FEATURE_COLUMN_SET_MANIFEST_VERSION,
            "manifest_id": self.manifest_id,
            "feature_column_set_version": DISCOVERY_FEATURE_COLUMN_SET_VERSION,
            "research_only": self.research_only,
            "observe_only": self.observe_only,
            "promotion_ready": self.promotion_ready,
            "notes": list(self.notes),
            "feature_column_sets": [item.to_payload() for item in self.feature_column_sets],
        }
        if include_hash:
            payload["manifest_sha256"] = self.manifest_sha256 or stable_feature_column_set_hash(payload)
        return payload

    @property
    def enabled_sets(self) -> tuple[DiscoveryFeatureColumnSet, ...]:
        return tuple(item for item in self.feature_column_sets if item.enabled)

    def set_by_id(self) -> dict[str, DiscoveryFeatureColumnSet]:
        return {item.feature_column_set_id: item for item in self.feature_column_sets}


@dataclass(frozen=True, slots=True)
class FeatureColumnSetValidation:
    valid: bool
    errors: tuple[str, ...]


def load_feature_column_set_manifest(path: Path) -> DiscoveryFeatureColumnSetManifest:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8-sig"))
    return DiscoveryFeatureColumnSetManifest.from_payload(payload)


def validate_feature_column_set_manifest(
    manifest: DiscoveryFeatureColumnSetManifest,
    *,
    selected_ids: tuple[str, ...] | None = None,
) -> FeatureColumnSetValidation:
    errors: list[str] = []
    if manifest.research_only is not True:
        errors.append("feature_column_set_manifest_research_only_required")
    if manifest.observe_only is not True:
        errors.append("feature_column_set_manifest_observe_only_required")
    if manifest.promotion_ready is not False:
        errors.append("feature_column_set_manifest_promotion_ready_false_required")
    if not manifest.feature_column_sets:
        errors.append("feature_column_set_manifest_requires_sets")
    ids = [item.feature_column_set_id for item in manifest.feature_column_sets]
    if len(set(ids)) != len(ids):
        errors.append("duplicate_feature_column_set_id")
    by_id = manifest.set_by_id()
    enabled_non_wt = [item for item in manifest.enabled_sets if not item.contains_wt3d]

    for item in manifest.feature_column_sets:
        errors.extend(_validate_feature_column_set(item, by_id=by_id))
    if not enabled_non_wt:
        errors.append("at_least_one_enabled_non_wt_feature_column_set_required")
    if selected_ids is not None:
        unknown = sorted(set(selected_ids) - set(by_id))
        if unknown:
            errors.append(f"unknown_selected_feature_column_set:{','.join(unknown)}")
        disabled = sorted(item_id for item_id in selected_ids if item_id in by_id and not by_id[item_id].enabled)
        if disabled:
            errors.append(f"selected_feature_column_set_disabled:{','.join(disabled)}")
        selected = {item_id for item_id in selected_ids if item_id in by_id}
        missing_comparators = sorted(
            f"{item.feature_column_set_id}:{item.required_comparator_set}"
            for item_id in selected
            for item in (by_id[item_id],)
            if item.contains_wt3d
            and item.required_comparator_set
            and item.required_comparator_set not in selected
        )
        if missing_comparators:
            errors.append(
                "selected_wt3d_feature_column_set_requires_selected_comparator:"
                + ",".join(missing_comparators)
            )
    if errors:
        raise ValueError(";".join(errors))
    return FeatureColumnSetValidation(valid=True, errors=())


def stable_feature_column_set_hash(payload: Mapping[str, Any]) -> str:
    normalized = dict(payload)
    normalized.pop("manifest_sha256", None)
    encoded = json.dumps(normalized, sort_keys=True, default=str, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _validate_feature_column_set(
    item: DiscoveryFeatureColumnSet,
    *,
    by_id: Mapping[str, DiscoveryFeatureColumnSet],
) -> list[str]:
    errors: list[str] = []
    if not SAFE_ID_RE.match(item.feature_column_set_id):
        errors.append(f"invalid_feature_column_set_id:{item.feature_column_set_id}")
    if not item.registered_feature_set_id:
        errors.append(f"registered_feature_set_id_required:{item.feature_column_set_id}")
        return errors
    if not item.columns and item.enabled:
        errors.append(f"enabled_feature_column_set_requires_columns:{item.feature_column_set_id}")
    if len(set(item.columns)) != len(item.columns):
        errors.append(f"duplicate_columns:{item.feature_column_set_id}")
    if item.maximum_dimensions <= 0:
        errors.append(f"maximum_dimensions_must_be_positive:{item.feature_column_set_id}")
    if item.enabled and len(item.columns) > item.maximum_dimensions:
        errors.append(f"feature_column_set_exceeds_maximum_dimensions:{item.feature_column_set_id}")
    if item.enabled and item.maximum_dimensions > DEFAULT_MAX_ENABLED_DIMENSIONS:
        errors.append(f"enabled_feature_column_set_maximum_dimensions_too_large:{item.feature_column_set_id}")
    if not item.enabled and not item.disabled_reason:
        errors.append(f"disabled_feature_column_set_requires_reason:{item.feature_column_set_id}")
    if item.contains_wt3d and not item.required_comparator_set:
        errors.append(f"wt3d_feature_column_set_requires_comparator:{item.feature_column_set_id}")
    if item.required_comparator_set:
        comparator = by_id.get(item.required_comparator_set)
        if comparator is None:
            errors.append(f"missing_required_comparator:{item.feature_column_set_id}:{item.required_comparator_set}")
        elif comparator.contains_wt3d:
            errors.append(f"required_comparator_must_be_non_wt:{item.feature_column_set_id}")
    errors.extend(_unknown_registered_columns(item))
    return errors


def _unknown_registered_columns(item: DiscoveryFeatureColumnSet) -> list[str]:
    try:
        manifest = manifest_from_preset(item.registered_feature_set_id)
    except ValueError:
        return [f"unknown_registered_feature_set:{item.feature_column_set_id}:{item.registered_feature_set_id}"]
    missing = sorted(set(item.columns) - set(manifest.feature_columns))
    if missing:
        return [f"unknown_feature_columns:{item.feature_column_set_id}:{','.join(missing)}"]
    return []
