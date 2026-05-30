from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.state import atomic_write_json
from tradingbotsuite.research_discovery.state import read_trial_record


DISCOVERY_MULTIPLE_TESTING_VERSION = "discovery-multiple-testing-stability-v1"
DISCOVERY_MULTIPLE_TESTING_MANIFEST_VERSION = "discovery-multiple-testing-stability-manifest-v1"
DISCOVERY_MULTIPLE_TESTING_ARTIFACT_VERSION = "discovery-multiple-testing-stability-artifacts-v1"


@dataclass(frozen=True, slots=True)
class DiscoveryMultipleTestingSpec:
    declared_search_space: int
    max_sampled_fraction: float = 1.0
    min_sampled_fraction_for_candidate_ready: float = 0.01
    max_effective_trial_count_without_stability: int = 250
    min_stability_neighborhood_size: int = 3
    max_best_candidate_concentration: float = 0.50
    max_split_window_concentration: float = 0.60
    max_side_concentration: float = 0.90
    latest_window_only: bool = False

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DiscoveryMultipleTestingSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("multiple-testing spec must be a JSON object")
        return cls(
            declared_search_space=max(0, int(payload.get("declared_search_space") or 0)),
            max_sampled_fraction=float(payload.get("max_sampled_fraction", 1.0)),
            min_sampled_fraction_for_candidate_ready=float(payload.get("min_sampled_fraction_for_candidate_ready", 0.01)),
            max_effective_trial_count_without_stability=max(0, int(payload.get("max_effective_trial_count_without_stability", 250))),
            min_stability_neighborhood_size=max(0, int(payload.get("min_stability_neighborhood_size", 3))),
            max_best_candidate_concentration=float(payload.get("max_best_candidate_concentration", 0.50)),
            max_split_window_concentration=float(payload.get("max_split_window_concentration", 0.60)),
            max_side_concentration=float(payload.get("max_side_concentration", 0.90)),
            latest_window_only=bool(payload.get("latest_window_only", False)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "declared_search_space": int(self.declared_search_space),
            "max_sampled_fraction": float(self.max_sampled_fraction),
            "min_sampled_fraction_for_candidate_ready": float(self.min_sampled_fraction_for_candidate_ready),
            "max_effective_trial_count_without_stability": int(self.max_effective_trial_count_without_stability),
            "min_stability_neighborhood_size": int(self.min_stability_neighborhood_size),
            "max_best_candidate_concentration": float(self.max_best_candidate_concentration),
            "max_split_window_concentration": float(self.max_split_window_concentration),
            "max_side_concentration": float(self.max_side_concentration),
            "latest_window_only": bool(self.latest_window_only),
        }


@dataclass(frozen=True, slots=True)
class DiscoveryMultipleTestingResult:
    manifest: dict[str, Any]
    candidate_gates: pd.DataFrame


@dataclass(frozen=True, slots=True)
class DiscoveryMultipleTestingArtifactResult:
    output_dir: Path
    manifest_path: Path
    candidate_gates_path: Path


def build_discovery_multiple_testing_report(
    candidates: pd.DataFrame,
    *,
    spec: DiscoveryMultipleTestingSpec,
) -> DiscoveryMultipleTestingResult:
    candidate_gates = _candidate_gates(candidates, spec=spec)
    manifest = {
        "multiple_testing_manifest_version": DISCOVERY_MULTIPLE_TESTING_MANIFEST_VERSION,
        "multiple_testing_version": DISCOVERY_MULTIPLE_TESTING_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec": spec.to_payload(),
        "spec_sha256": _stable_hash(spec.to_payload()),
        "input_candidate_row_count": int(len(candidates)),
        "candidate_gate_row_count": int(len(candidate_gates)),
        "summary": _summary(candidate_gates),
        "claim_scope": "screen_leads_only_until_multiple_testing_and_validation_gates_complete",
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["candidate_gates_sha256"] = _frame_hash(candidate_gates)
    return DiscoveryMultipleTestingResult(manifest=manifest, candidate_gates=candidate_gates)


def build_discovery_multiple_testing_report_from_manifest(
    discovery_manifest_path: Path,
    *,
    spec: DiscoveryMultipleTestingSpec | None = None,
) -> DiscoveryMultipleTestingResult:
    discovery_manifest_path = Path(discovery_manifest_path).expanduser().resolve()
    manifest = _read_json(discovery_manifest_path)
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    interesting_path = Path(str(required_outputs.get("interesting_candidates") or ""))
    interesting = pd.read_parquet(interesting_path) if interesting_path.exists() else pd.DataFrame()
    interesting = _normalized_manifest_candidates(interesting)
    declared = _declared_search_space_from_discovery(manifest, required_outputs, interesting)
    source_sha = _file_sha256(discovery_manifest_path)
    if not interesting.empty:
        interesting["source_discovery_manifest_sha256"] = source_sha
    base_spec = spec or DiscoveryMultipleTestingSpec(declared_search_space=0)
    effective_spec = replace(
        base_spec,
        declared_search_space=int(base_spec.declared_search_space or declared),
        latest_window_only=bool(base_spec.latest_window_only or _manifest_latest_window_only(manifest)),
    )
    result = build_discovery_multiple_testing_report(interesting, spec=effective_spec)
    enriched_manifest = dict(result.manifest)
    enriched_manifest.update(
        {
            "source_discovery_manifest_path": str(discovery_manifest_path),
            "source_discovery_manifest_sha256": source_sha,
            "source_discovery_ledger_sha256s": _ledger_sha256s(required_outputs),
            "declared_search_space_source": "discovery_manifest_or_trial_records",
        }
    )
    gates = result.candidate_gates.copy()
    enriched_manifest["candidate_gates_sha256"] = _frame_hash(gates)
    return DiscoveryMultipleTestingResult(manifest=enriched_manifest, candidate_gates=gates)


def write_discovery_multiple_testing_artifacts(
    output_dir: Path,
    result: DiscoveryMultipleTestingResult,
) -> DiscoveryMultipleTestingArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "discovery_multiple_testing_manifest.json"
    candidate_gates_path = output_dir / "discovery_multiple_testing_candidate_gates.parquet"
    result.candidate_gates.to_parquet(candidate_gates_path, index=False)
    manifest = dict(result.manifest)
    manifest["artifact_version"] = DISCOVERY_MULTIPLE_TESTING_ARTIFACT_VERSION
    manifest["required_outputs"] = {
        "discovery_multiple_testing_manifest": str(manifest_path),
        "discovery_multiple_testing_candidate_gates": str(candidate_gates_path),
    }
    manifest["discovery_multiple_testing_candidate_gates_sha256"] = _file_sha256(candidate_gates_path)
    atomic_write_json(manifest_path, manifest)
    return DiscoveryMultipleTestingArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        candidate_gates_path=candidate_gates_path,
    )


def _candidate_gates(candidates: pd.DataFrame, *, spec: DiscoveryMultipleTestingSpec) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sampled_count = int(len(candidates))
    declared = max(0, int(spec.declared_search_space))
    sampled_fraction = float(sampled_count / declared) if declared else 0.0
    effective_trial_count = int(_effective_trial_count(candidates, sampled_count))
    total_positive_score = max(_positive_score_sum(candidates), 1e-12)
    stability_neighborhood_sizes = _stability_neighborhood_sizes(candidates)
    for index, record in enumerate(candidates.to_dict("records")):
        candidate_id = str(record.get("candidate_id") or "")
        score = _score(record)
        best_concentration = max(0.0, score) / total_positive_score
        configured_stability = _optional_int(record.get("stability_neighborhood_size"))
        stability_neighborhood_size = (
            configured_stability
            if configured_stability is not None
            else stability_neighborhood_sizes[index]
            if index < len(stability_neighborhood_sizes)
            else 0
        )
        split_concentration = _float_value(record, "split_window_concentration", _float_value(record, "max_single_split_pnl_share", 0.0))
        side_concentration = _float_value(record, "side_concentration", _float_value(record, "side_collapse_ratio", 0.0))
        reasons = _gate_reasons(
            record,
            spec=spec,
            declared_search_space=declared,
            sampled_fraction=sampled_fraction,
            effective_trial_count=effective_trial_count,
            best_candidate_concentration=best_concentration,
            stability_neighborhood_size=stability_neighborhood_size,
            split_window_concentration=split_concentration,
            side_concentration=side_concentration,
        )
        rows.append(
            {
                "candidate_id": candidate_id,
                "record_sha256": str(record.get("record_sha256") or ""),
                "source_discovery_manifest_sha256": str(record.get("source_discovery_manifest_sha256") or ""),
                "multiple_testing_status": "passed" if not reasons else "blocked",
                "multiple_testing_reasons": "|".join(reasons),
                "declared_search_space": declared,
                "sampled_candidate_count": sampled_count,
                "sampled_fraction": sampled_fraction,
                "effective_trial_count": effective_trial_count,
                "best_candidate_concentration": best_concentration,
                "stability_neighborhood_size": stability_neighborhood_size,
                "split_window_concentration": split_concentration,
                "side_concentration": side_concentration,
                "latest_window_only_penalty": bool(spec.latest_window_only or _truthy(record.get("latest_window_only"))),
                "research_maturity": "screen_lead" if reasons else "screen_worthy_lead",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return pd.DataFrame(rows, columns=_candidate_gate_columns())


def _gate_reasons(
    record: Mapping[str, Any],
    *,
    spec: DiscoveryMultipleTestingSpec,
    declared_search_space: int,
    sampled_fraction: float,
    effective_trial_count: int,
    best_candidate_concentration: float,
    stability_neighborhood_size: int,
    split_window_concentration: float,
    side_concentration: float,
) -> list[str]:
    reasons: list[str] = []
    if declared_search_space <= 0:
        reasons.append("declared_search_space_required")
    if sampled_fraction < spec.min_sampled_fraction_for_candidate_ready:
        reasons.append("sampled_fraction_below_candidate_ready_floor")
    if sampled_fraction > spec.max_sampled_fraction:
        reasons.append("sampled_fraction_above_configured_ceiling")
    if effective_trial_count > spec.max_effective_trial_count_without_stability and stability_neighborhood_size < spec.min_stability_neighborhood_size:
        reasons.append("effective_trial_count_requires_stability_neighborhood")
    if stability_neighborhood_size < spec.min_stability_neighborhood_size:
        reasons.append("stability_neighborhood_size_below_floor")
    if best_candidate_concentration > spec.max_best_candidate_concentration:
        reasons.append("best_candidate_concentration_above_ceiling")
    if best_candidate_concentration > spec.max_best_candidate_concentration and stability_neighborhood_size <= 1:
        reasons.append("isolated_top_score_large_grid")
    if split_window_concentration <= 0.0:
        reasons.append("split_window_concentration_required")
    if split_window_concentration > spec.max_split_window_concentration:
        reasons.append("split_window_concentration_above_ceiling")
    if side_concentration <= 0.0:
        reasons.append("side_concentration_required")
    if side_concentration > spec.max_side_concentration:
        reasons.append("side_concentration_above_ceiling")
    if bool(spec.latest_window_only or _truthy(record.get("latest_window_only"))):
        reasons.append("latest_window_only_evidence")
    return list(dict.fromkeys(reasons))


def _effective_trial_count(candidates: pd.DataFrame, sampled_count: int) -> int:
    if candidates.empty:
        return 0
    if "effective_trial_count" in candidates.columns:
        values = pd.to_numeric(candidates["effective_trial_count"], errors="coerce").dropna()
        if not values.empty:
            return int(max(0, values.max()))
    identity_columns = [
        column
        for column in (
            "feature_column_set_id",
            "regime_mode",
            "label_horizon",
            "distance_metric",
            "k",
            "min_neighbor_count",
            "exit_policy_id",
        )
        if column in candidates.columns
    ]
    if not identity_columns:
        return int(sampled_count)
    return int(candidates.loc[:, identity_columns].drop_duplicates().shape[0])


def _stability_neighborhood_size(record: Mapping[str, Any], candidates: pd.DataFrame) -> int:
    configured = _optional_int(record.get("stability_neighborhood_size"))
    if configured is not None:
        return configured
    if candidates.empty:
        return 0
    keys = [
        column
        for column in ("feature_column_set_id", "regime_mode", "label_horizon", "distance_metric", "exit_policy_id")
        if column in candidates.columns
    ]
    if not keys:
        return 1
    mask = pd.Series([True] * len(candidates), index=candidates.index)
    for key in keys:
        mask &= candidates[key].astype(str).eq(str(record.get(key) or ""))
    return int(mask.sum())


def _stability_neighborhood_sizes(candidates: pd.DataFrame) -> list[int]:
    if candidates.empty:
        return []
    keys = [
        column
        for column in ("feature_column_set_id", "regime_mode", "label_horizon", "distance_metric", "exit_policy_id")
        if column in candidates.columns
    ]
    if not keys:
        return [1] * len(candidates)
    key_frame = candidates.loc[:, keys].fillna("").astype(str)
    key_tuples = [tuple(values) for values in key_frame.itertuples(index=False, name=None)]
    counts = Counter(key_tuples)
    return [int(counts[key]) for key in key_tuples]


def _positive_score_sum(candidates: pd.DataFrame) -> float:
    if candidates.empty:
        return 0.0
    scores = [_score(row) for row in candidates.to_dict("records")]
    return float(sum(max(0.0, score) for score in scores))


def _score(record: Mapping[str, Any]) -> float:
    for key in ("discovery_screen_score_v2", "final_score", "score"):
        value = _optional_float(record.get(key))
        if value is not None:
            return value
    return 0.0


def _summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"candidate_count": 0, "passed_count": 0, "blocked_count": 0}
    passed = int(frame["multiple_testing_status"].astype(str).eq("passed").sum())
    return {
        "candidate_count": int(len(frame)),
        "passed_count": passed,
        "blocked_count": int(len(frame) - passed),
    }


def _candidate_gate_columns() -> list[str]:
    return [
        "candidate_id",
        "record_sha256",
        "source_discovery_manifest_sha256",
        "multiple_testing_status",
        "multiple_testing_reasons",
        "declared_search_space",
        "sampled_candidate_count",
        "sampled_fraction",
        "effective_trial_count",
        "best_candidate_concentration",
        "stability_neighborhood_size",
        "split_window_concentration",
        "side_concentration",
        "latest_window_only_penalty",
        "research_maturity",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _normalized_manifest_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    frame = candidates.copy()
    if frame.empty:
        return frame
    if "side_concentration" not in frame.columns:
        if "side_collapse_ratio" in frame.columns:
            values = pd.to_numeric(frame["side_collapse_ratio"], errors="coerce")
            frame["side_concentration"] = values.where(values > 0.0)
    return frame


def _declared_search_space_from_discovery(
    manifest: Mapping[str, Any],
    required_outputs: Mapping[str, Any],
    candidates: pd.DataFrame,
) -> int:
    if "search_space_total_combinations" in candidates.columns:
        values = pd.to_numeric(candidates["search_space_total_combinations"], errors="coerce").dropna()
        if not values.empty:
            return int(max(0, values.max()))
    budget = manifest.get("budget") if isinstance(manifest.get("budget"), Mapping) else {}
    max_trials = int(budget.get("max_trials") or 0)
    if max_trials:
        return int(max_trials)
    counts = manifest.get("counts") if isinstance(manifest.get("counts"), Mapping) else {}
    completed = int(counts.get("completed_trials") or 0)
    if completed:
        return int(max(completed, len(candidates)))
    trials_dir_raw = required_outputs.get("trials")
    if trials_dir_raw:
        totals: list[int] = []
        for path in Path(str(trials_dir_raw)).glob("*.json"):
            try:
                record = read_trial_record(path)
            except ValueError:
                continue
            total = _optional_int(dict(record.payload or {}).get("search_space_total_combinations"))
            if total is not None:
                totals.append(total)
        if totals:
            return int(max(totals))
    resolved_spec_raw = required_outputs.get("discovery_spec_resolved")
    if resolved_spec_raw and Path(str(resolved_spec_raw)).exists():
        payload = _read_json(Path(str(resolved_spec_raw)))
        templates = payload.get("trial_templates") if isinstance(payload.get("trial_templates"), list) else []
        spec_budget = payload.get("budget") if isinstance(payload.get("budget"), Mapping) else {}
        spec_max_trials = int(spec_budget.get("max_trials") or 0)
        if templates:
            return int(max(1, len(templates)))
        if spec_max_trials:
            return int(spec_max_trials)
    return int(len(candidates))


def _manifest_latest_window_only(manifest: Mapping[str, Any]) -> bool:
    data_evidence = manifest.get("data_evidence")
    encoded = json.dumps(data_evidence, sort_keys=True, default=str).lower() if data_evidence is not None else ""
    return "latest_window_only" in encoded or "latest-window" in encoded


def _ledger_sha256s(required_outputs: Mapping[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in ("interesting_candidates", "blocked_candidates", "filter_blockers"):
        raw_path = required_outputs.get(name)
        if raw_path and Path(str(raw_path)).exists():
            hashes[name] = _file_sha256(Path(str(raw_path)))
    return hashes


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _optional_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if pd.notna(parsed) and abs(parsed) != float("inf") else None


def _float_value(record: Mapping[str, Any], key: str, default: float) -> float:
    parsed = _optional_float(record.get(key))
    return float(default) if parsed is None else float(parsed)


def _optional_int(value: Any) -> int | None:
    parsed = _optional_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return _stable_hash({"columns": list(frame.columns), "rows": []})
    rows = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
    return _stable_hash({"columns": list(frame.columns), "rows": rows})


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
