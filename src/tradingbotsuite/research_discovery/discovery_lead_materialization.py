from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

import pandas as pd

from tradingbotsuite.data.historical_data_catalog import normalize_operator_run_artifact_paths
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.artifact_keys import (
    effective_trial_key,
    entry_event_signature_hash,
    prediction_signature_hash,
    stable_payload_sha256,
)
from tradingbotsuite.research_discovery.state import atomic_write_json, read_trial_record


DISCOVERY_LEAD_MATERIALIZATION_VERSION = "discovery-lead-materialization-v1"
DISCOVERY_LEAD_MATERIALIZATION_MANIFEST_VERSION = "discovery-lead-materialization-manifest-v1"
DISCOVERY_LEAD_MATERIALIZATION_ARTIFACT_VERSION = "discovery-lead-materialization-artifacts-v1"

MATERIALIZED_DISCOVERY_LEAD_STRATEGY_FAMILY = "frozen_knn_entry_lead_v1"
MATERIALIZATION_SCOPE = "descriptor_only_requires_cycle_backtest_evidence"

REQUIRED_DOWNSTREAM_GATES = (
    "cycle_backtest_required",
    "cycle_ranking_required",
    "research_candidate_gate_required",
    "baseline_comparator_required",
    "no_trade_comparator_required",
    "exit_lab_required",
    "multiple_testing_required",
    "validation_floor_required",
    "candidate_pack_eligibility_required",
)


@dataclass(frozen=True, slots=True)
class DiscoveryLeadMaterializationSpec:
    max_candidates: int = 24
    max_per_entry_signature: int = 2
    min_final_score: float | None = None
    strategy_family: str = MATERIALIZED_DISCOVERY_LEAD_STRATEGY_FAMILY
    materialization_scope: str = MATERIALIZATION_SCOPE

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DiscoveryLeadMaterializationSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("discovery lead materialization spec must be a JSON object")
        min_final_score_raw = payload.get("min_final_score")
        min_final_score = None if min_final_score_raw in {None, ""} else float(min_final_score_raw)
        return cls(
            max_candidates=max(0, int(payload.get("max_candidates", 24))),
            max_per_entry_signature=max(1, int(payload.get("max_per_entry_signature", 2))),
            min_final_score=min_final_score,
            strategy_family=str(payload.get("strategy_family") or MATERIALIZED_DISCOVERY_LEAD_STRATEGY_FAMILY),
            materialization_scope=str(payload.get("materialization_scope") or MATERIALIZATION_SCOPE),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "max_candidates": int(self.max_candidates),
            "max_per_entry_signature": int(self.max_per_entry_signature),
            "min_final_score": self.min_final_score,
            "strategy_family": self.strategy_family,
            "materialization_scope": self.materialization_scope,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryLeadMaterializationResult:
    manifest: dict[str, Any]
    materialized_leads: pd.DataFrame
    candidate_specs: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class DiscoveryLeadMaterializationArtifactResult:
    output_dir: Path
    manifest_path: Path
    materialized_leads_path: Path
    candidate_specs_path: Path


def materialize_discovery_leads_from_manifest(
    discovery_manifest_path: Path,
    *,
    spec: DiscoveryLeadMaterializationSpec | None = None,
) -> DiscoveryLeadMaterializationResult:
    discovery_manifest_path = Path(discovery_manifest_path).expanduser().resolve()
    effective_spec = spec or DiscoveryLeadMaterializationSpec()
    manifest = _read_discovery_manifest(discovery_manifest_path)
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    interesting_path = _required_existing_path(required_outputs, "interesting_candidates")
    trials_dir = _required_existing_path(required_outputs, "trials")
    if not trials_dir.is_dir():
        raise ValueError(f"discovery trials path is not a directory: {trials_dir}")
    interesting = pd.read_parquet(interesting_path)
    source_manifest_sha = _file_sha256(discovery_manifest_path)
    source_ledger_sha = _file_sha256(interesting_path)
    selected, skipped_by_signature, skipped_by_budget = _select_leads(interesting, spec=effective_spec)
    rows: list[dict[str, Any]] = []
    candidate_specs: list[dict[str, Any]] = []
    for record in selected:
        trial = _read_source_trial(
            trials_dir=trials_dir,
            trial_id=str(record.get("trial_id") or ""),
            expected_record_sha256=str(record.get("record_sha256") or ""),
        )
        row = _materialized_row(
            ledger_record=record,
            trial_payload=trial.to_payload(),
            discovery_manifest=manifest,
            source_discovery_manifest_sha256=source_manifest_sha,
            source_discovery_ledger_sha256=source_ledger_sha,
            spec=effective_spec,
        )
        rows.append(row)
        candidate_specs.append(_candidate_spec_from_row(row, spec=effective_spec))
    materialized = pd.DataFrame(rows, columns=_materialized_lead_columns())
    manifest_payload = {
        "discovery_lead_materialization_manifest_version": DISCOVERY_LEAD_MATERIALIZATION_MANIFEST_VERSION,
        "discovery_lead_materialization_version": DISCOVERY_LEAD_MATERIALIZATION_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec": effective_spec.to_payload(),
        "spec_sha256": stable_payload_sha256(effective_spec.to_payload()),
        "source_discovery_manifest_path": str(discovery_manifest_path),
        "source_discovery_manifest_sha256": source_manifest_sha,
        "source_interesting_candidates_path": str(interesting_path),
        "source_interesting_candidates_sha256": source_ledger_sha,
        "source_trials_dir": str(trials_dir),
        "source_symbol": str(manifest.get("symbol") or ""),
        "source_timeframe": str(manifest.get("timeframe") or ""),
        "input_candidate_row_count": int(len(interesting)),
        "materialized_candidate_count": int(len(materialized)),
        "skipped_by_entry_signature_cap": int(skipped_by_signature),
        "skipped_by_materialization_budget": int(skipped_by_budget),
        "required_downstream_gates": list(REQUIRED_DOWNSTREAM_GATES),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "claim_scope": "materialized_discovery_lead_descriptors_only_no_backtest_or_pack_claim",
        "summary": _summary(
            materialized,
            skipped_by_signature=skipped_by_signature,
            skipped_by_budget=skipped_by_budget,
        ),
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest_payload["materialized_leads_frame_sha256"] = _frame_hash(materialized)
    manifest_payload["candidate_specs_sha256"] = _candidate_specs_hash(candidate_specs)
    return DiscoveryLeadMaterializationResult(
        manifest=manifest_payload,
        materialized_leads=materialized,
        candidate_specs=tuple(candidate_specs),
    )


def write_discovery_lead_materialization_artifacts(
    output_dir: Path,
    result: DiscoveryLeadMaterializationResult,
) -> DiscoveryLeadMaterializationArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "discovery_lead_materialization_manifest.json"
    materialized_leads_path = output_dir / "materialized_discovery_leads.parquet"
    candidate_specs_path = output_dir / "materialization_candidate_specs.jsonl"
    _assert_new_artifact_paths(manifest_path, materialized_leads_path, candidate_specs_path)
    _atomic_write_parquet(result.materialized_leads, materialized_leads_path)
    _atomic_write_jsonl(candidate_specs_path, result.candidate_specs)
    manifest = dict(result.manifest)
    manifest["artifact_version"] = DISCOVERY_LEAD_MATERIALIZATION_ARTIFACT_VERSION
    manifest["required_outputs"] = {
        "discovery_lead_materialization_manifest": str(manifest_path),
        "materialized_discovery_leads": str(materialized_leads_path),
        "materialization_candidate_specs": str(candidate_specs_path),
    }
    manifest["materialized_discovery_leads_sha256"] = _file_sha256(materialized_leads_path)
    manifest["materialization_candidate_specs_sha256"] = _file_sha256(candidate_specs_path)
    validation_reasons = validate_discovery_lead_materialization_manifest(manifest)
    if validation_reasons:
        raise ValueError("invalid discovery lead materialization manifest: " + "|".join(validation_reasons))
    atomic_write_json(manifest_path, manifest)
    return DiscoveryLeadMaterializationArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        materialized_leads_path=materialized_leads_path,
        candidate_specs_path=candidate_specs_path,
    )


def validate_discovery_lead_materialization_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("discovery_lead_materialization_manifest_version") != DISCOVERY_LEAD_MATERIALIZATION_MANIFEST_VERSION:
        reasons.append("discovery_lead_materialization_manifest_version_required")
    if manifest.get("discovery_lead_materialization_version") != DISCOVERY_LEAD_MATERIALIZATION_VERSION:
        reasons.append("discovery_lead_materialization_version_required")
    if manifest.get("research_only") is not True:
        reasons.append("research_only_must_be_true")
    if manifest.get("observe_only") is not True:
        reasons.append("observe_only_must_be_true")
    if manifest.get("promotion_ready") is not False:
        reasons.append("promotion_ready_must_be_false")
    if manifest.get("candidate_pack_written") is not False:
        reasons.append("candidate_pack_written_must_be_false")
    if manifest.get("candidate_pack_paths") not in ([], ()):
        reasons.append("candidate_pack_paths_must_be_empty")
    for field in ("live_fetch_used", "order_placement_used", "runtime_mode_changed"):
        if manifest.get(field) is not False:
            reasons.append(f"{field}_must_be_false")
    gates = manifest.get("required_downstream_gates")
    if list(gates or []) != list(REQUIRED_DOWNSTREAM_GATES):
        reasons.append("required_downstream_gates_mismatch")
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    for key in (
        "discovery_lead_materialization_manifest",
        "materialized_discovery_leads",
        "materialization_candidate_specs",
    ):
        if key not in required_outputs:
            reasons.append(f"required_output_missing:{key}")
    return reasons


def _select_leads(
    interesting: pd.DataFrame,
    *,
    spec: DiscoveryLeadMaterializationSpec,
) -> tuple[list[dict[str, Any]], int, int]:
    if interesting.empty or spec.max_candidates <= 0:
        return [], 0, int(len(interesting))
    frame = interesting.copy()
    for column in ("final_score", "score", "independent_event_count", "trade_count"):
        if column not in frame.columns:
            frame[column] = 0.0
    frame["_sort_candidate_id"] = frame.get("candidate_id", "").astype(str)
    if spec.min_final_score is not None:
        score = pd.to_numeric(frame["final_score"], errors="coerce").fillna(pd.to_numeric(frame["score"], errors="coerce"))
        frame = frame.loc[score >= float(spec.min_final_score)].copy()
    frame["_final_score_sort"] = pd.to_numeric(frame["final_score"], errors="coerce").fillna(float("-inf"))
    frame["_score_sort"] = pd.to_numeric(frame["score"], errors="coerce").fillna(float("-inf"))
    frame["_event_sort"] = pd.to_numeric(frame["independent_event_count"], errors="coerce").fillna(0)
    frame["_trade_sort"] = pd.to_numeric(frame["trade_count"], errors="coerce").fillna(0)
    frame = frame.sort_values(
        ["_final_score_sort", "_score_sort", "_event_sort", "_trade_sort", "_sort_candidate_id"],
        ascending=[False, False, False, False, True],
        kind="mergesort",
    )
    selected: list[dict[str, Any]] = []
    signature_counts: dict[str, int] = {}
    skipped_by_signature = 0
    skipped_by_budget = 0
    for record in frame.to_dict("records"):
        signature = entry_event_signature_hash(record)
        current_count = signature_counts.get(signature, 0)
        if current_count >= spec.max_per_entry_signature:
            skipped_by_signature += 1
            continue
        signature_counts[signature] = current_count + 1
        if len(selected) >= spec.max_candidates:
            skipped_by_budget += 1
            continue
        selected.append(record)
    return selected, skipped_by_signature, skipped_by_budget


def _materialized_row(
    *,
    ledger_record: Mapping[str, Any],
    trial_payload: Mapping[str, Any],
    discovery_manifest: Mapping[str, Any],
    source_discovery_manifest_sha256: str,
    source_discovery_ledger_sha256: str,
    spec: DiscoveryLeadMaterializationSpec,
) -> dict[str, Any]:
    trial_inner = trial_payload.get("payload") if isinstance(trial_payload.get("payload"), Mapping) else {}
    merged = {**dict(ledger_record), **dict(trial_inner)}
    discovery_candidate_id = str(ledger_record.get("candidate_id") or trial_payload.get("candidate_id") or "")
    source_record_sha256 = str(ledger_record.get("record_sha256") or trial_payload.get("record_sha256") or "")
    prediction_signature = prediction_signature_hash(merged)
    entry_signature = entry_event_signature_hash(merged)
    effective_key = effective_trial_key(merged)
    materialized_payload = {
        "version": DISCOVERY_LEAD_MATERIALIZATION_VERSION,
        "strategy_family": spec.strategy_family,
        "materialization_scope": spec.materialization_scope,
        "source_discovery_manifest_sha256": source_discovery_manifest_sha256,
        "source_record_sha256": source_record_sha256,
        "source_discovery_candidate_id": discovery_candidate_id,
        "prediction_signature_hash": prediction_signature,
        "entry_event_signature_hash": entry_signature,
        "effective_trial_key": effective_key,
    }
    materialized_candidate_id = f"mat-{stable_payload_sha256(materialized_payload)[:32]}"
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "materialization_status": "descriptor_only",
        "materialization_scope": spec.materialization_scope,
        "materialized_candidate_id": materialized_candidate_id,
        "materialized_candidate_family": spec.strategy_family,
        "source_discovery_manifest_sha256": source_discovery_manifest_sha256,
        "source_discovery_ledger_sha256": source_discovery_ledger_sha256,
        "source_run_id": str(trial_payload.get("run_id") or discovery_manifest.get("run_id") or ""),
        "source_trial_id": str(trial_payload.get("trial_id") or ledger_record.get("trial_id") or ""),
        "source_attempt_id": str(trial_payload.get("attempt_id") or ledger_record.get("attempt_id") or ""),
        "source_trial_index": int(trial_payload.get("trial_index") or ledger_record.get("trial_index") or 0),
        "source_discovery_candidate_id": discovery_candidate_id,
        "source_candidate_family": str(ledger_record.get("candidate_family") or trial_payload.get("candidate_family") or ""),
        "source_record_sha256": source_record_sha256,
        "symbol": str(discovery_manifest.get("symbol") or ""),
        "timeframe": str(discovery_manifest.get("timeframe") or ""),
        "feature_column_set_id": str(merged.get("feature_column_set_id") or ""),
        "registered_feature_set_id": str(merged.get("registered_feature_set_id") or ""),
        "regime_mode": str(merged.get("regime_mode") or ""),
        "regime_detector_type": str(merged.get("regime_detector_type") or ""),
        "label_horizon": str(merged.get("label_horizon") or ""),
        "distance_metric": str(merged.get("distance_metric") or ""),
        "k": _optional_int(merged.get("k")) or 0,
        "min_neighbor_count": _optional_int(merged.get("min_neighbor_count")) or 0,
        "probability_threshold": _optional_float(merged.get("probability_threshold")),
        "expected_value_threshold": _optional_float(merged.get("expected_value_threshold")),
        "min_neighbor_agreement": _optional_float(merged.get("min_neighbor_agreement")),
        "min_distance_quality": _optional_float(merged.get("min_distance_quality")),
        "vote_margin_threshold": _optional_float(merged.get("vote_margin_threshold")),
        "prediction_signature_hash": prediction_signature,
        "entry_event_signature_hash": entry_signature,
        "effective_trial_key": effective_key,
        "final_score": _optional_float(merged.get("final_score")),
        "discovery_screen_score_v2": _optional_float(merged.get("discovery_screen_score_v2")),
        "trade_count": _optional_int(merged.get("trade_count")) or 0,
        "accepted_bar_count": _optional_int(merged.get("accepted_bar_count")) or 0,
        "independent_event_count": _optional_int(merged.get("independent_event_count")) or 0,
        "long_independent_event_count": _optional_int(merged.get("long_independent_event_count")) or 0,
        "short_independent_event_count": _optional_int(merged.get("short_independent_event_count")) or 0,
        "overlap_ratio": _optional_float(merged.get("overlap_ratio")),
        "side_collapse_ratio": _optional_float(merged.get("side_collapse_ratio")),
        "signal_rate": _optional_float(merged.get("signal_rate")),
        "realized_expectancy": _optional_float(merged.get("realized_expectancy")),
        "independent_event_expectancy": _optional_float(merged.get("independent_event_expectancy")),
        "candidate_pack_written": False,
        "candidate_pack_eligible": False,
        "required_downstream_gates": "|".join(REQUIRED_DOWNSTREAM_GATES),
        "missing_evidence": "|".join(REQUIRED_DOWNSTREAM_GATES),
    }


def _candidate_spec_from_row(
    row: Mapping[str, Any],
    *,
    spec: DiscoveryLeadMaterializationSpec,
) -> dict[str, Any]:
    return {
        "materialized_candidate_id": str(row.get("materialized_candidate_id") or ""),
        "materialized_candidate_family": str(row.get("materialized_candidate_family") or spec.strategy_family),
        "materialization_version": DISCOVERY_LEAD_MATERIALIZATION_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_pack_written": False,
        "candidate_pack_eligible": False,
        "claim_scope": "descriptor_only_not_backtested_not_ranked_not_candidate_pack_evidence",
        "source": {
            "discovery_candidate_id": str(row.get("source_discovery_candidate_id") or ""),
            "trial_id": str(row.get("source_trial_id") or ""),
            "record_sha256": str(row.get("source_record_sha256") or ""),
            "discovery_manifest_sha256": str(row.get("source_discovery_manifest_sha256") or ""),
            "entry_event_signature_hash": str(row.get("entry_event_signature_hash") or ""),
            "prediction_signature_hash": str(row.get("prediction_signature_hash") or ""),
            "effective_trial_key": str(row.get("effective_trial_key") or ""),
        },
        "candidate_descriptor": {
            "strategy_family": spec.strategy_family,
            "entry_policy": "frozen_knn_entry_lead",
            "symbol": str(row.get("symbol") or ""),
            "timeframe": str(row.get("timeframe") or ""),
            "feature_column_set_id": str(row.get("feature_column_set_id") or ""),
            "registered_feature_set_id": str(row.get("registered_feature_set_id") or ""),
            "regime_mode": str(row.get("regime_mode") or ""),
            "regime_detector_type": str(row.get("regime_detector_type") or ""),
            "label_horizon": str(row.get("label_horizon") or ""),
            "distance_metric": str(row.get("distance_metric") or ""),
            "k": int(row.get("k") or 0),
            "min_neighbor_count": int(row.get("min_neighbor_count") or 0),
            "probability_threshold": _json_scalar(row.get("probability_threshold")),
            "expected_value_threshold": _json_scalar(row.get("expected_value_threshold")),
            "min_neighbor_agreement": _json_scalar(row.get("min_neighbor_agreement")),
            "min_distance_quality": _json_scalar(row.get("min_distance_quality")),
            "vote_margin_threshold": _json_scalar(row.get("vote_margin_threshold")),
        },
        "screening_metrics": {
            "final_score": _json_scalar(row.get("final_score")),
            "independent_event_count": int(row.get("independent_event_count") or 0),
            "overlap_ratio": _json_scalar(row.get("overlap_ratio")),
            "side_collapse_ratio": _json_scalar(row.get("side_collapse_ratio")),
            "signal_rate": _json_scalar(row.get("signal_rate")),
            "independent_event_expectancy": _json_scalar(row.get("independent_event_expectancy")),
        },
        "required_downstream_gates": list(REQUIRED_DOWNSTREAM_GATES),
        "next_empirical_packet": "run_cycle_backtest_and_gate_evidence_for_materialized_discovery_leads",
    }


def _summary(
    materialized: pd.DataFrame,
    *,
    skipped_by_signature: int,
    skipped_by_budget: int,
) -> dict[str, Any]:
    return {
        "materialized_candidate_count": int(len(materialized)),
        "descriptor_only_count": int(len(materialized)),
        "candidate_pack_written": False,
        "candidate_pack_eligible_count": 0,
        "promotion_ready": False,
        "skipped_by_entry_signature_cap": int(skipped_by_signature),
        "skipped_by_materialization_budget": int(skipped_by_budget),
        "required_downstream_gate_count": int(len(REQUIRED_DOWNSTREAM_GATES)),
        "status": "descriptor_only_not_backtested",
    }


def _read_discovery_manifest(path: Path) -> dict[str, Any]:
    resolved_path = Path(path).expanduser().resolve()
    payload = _read_json_raw(resolved_path)
    return normalize_operator_run_artifact_paths(payload, artifact_path=resolved_path, anchor_root=resolved_path.parent)


def _read_source_trial(
    *,
    trials_dir: Path,
    trial_id: str,
    expected_record_sha256: str,
):
    if not trial_id:
        raise ValueError("source discovery trial_id is required")
    trial_path = trials_dir / f"{trial_id}.json"
    if not trial_path.exists():
        raise ValueError(f"source discovery trial record missing: {trial_path}")
    trial = read_trial_record(trial_path)
    actual_hash = str(trial.to_payload().get("record_sha256") or "")
    if expected_record_sha256 and actual_hash != expected_record_sha256:
        raise ValueError(f"source discovery trial record hash mismatch: {trial_path}")
    return trial


def _required_existing_path(required_outputs: Mapping[str, Any], key: str) -> Path:
    raw_path = required_outputs.get(key)
    if not raw_path:
        raise ValueError(f"discovery required output missing: {key}")
    path = Path(str(raw_path)).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"discovery required output path missing for {key}: {path}")
    return path


def _materialized_lead_columns() -> list[str]:
    return [
        "research_only",
        "observe_only",
        "promotion_ready",
        "materialization_status",
        "materialization_scope",
        "materialized_candidate_id",
        "materialized_candidate_family",
        "source_discovery_manifest_sha256",
        "source_discovery_ledger_sha256",
        "source_run_id",
        "source_trial_id",
        "source_attempt_id",
        "source_trial_index",
        "source_discovery_candidate_id",
        "source_candidate_family",
        "source_record_sha256",
        "symbol",
        "timeframe",
        "feature_column_set_id",
        "registered_feature_set_id",
        "regime_mode",
        "regime_detector_type",
        "label_horizon",
        "distance_metric",
        "k",
        "min_neighbor_count",
        "probability_threshold",
        "expected_value_threshold",
        "min_neighbor_agreement",
        "min_distance_quality",
        "vote_margin_threshold",
        "prediction_signature_hash",
        "entry_event_signature_hash",
        "effective_trial_key",
        "final_score",
        "discovery_screen_score_v2",
        "trade_count",
        "accepted_bar_count",
        "independent_event_count",
        "long_independent_event_count",
        "short_independent_event_count",
        "overlap_ratio",
        "side_collapse_ratio",
        "signal_rate",
        "realized_expectancy",
        "independent_event_expectancy",
        "candidate_pack_written",
        "candidate_pack_eligible",
        "required_downstream_gates",
        "missing_evidence",
    ]


def _optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number) or number in {float("inf"), float("-inf")}:
        return None
    return number


def _optional_int(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if pd.isna(value) or value in {float("inf"), float("-inf")}:
            return None
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return _json_scalar(value.item())
        except (TypeError, ValueError):
            pass
    return value


def _candidate_specs_hash(candidate_specs: Iterable[Mapping[str, Any]]) -> str:
    digest = sha256()
    for payload in candidate_specs:
        digest.update(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return stable_payload_sha256({"columns": list(frame.columns), "rows": []})
    rows = frame.fillna("").to_dict("records")
    return stable_payload_sha256({"columns": list(frame.columns), "rows": rows})


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_raw(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _assert_new_artifact_paths(*paths: Path) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise ValueError("refusing to overwrite existing discovery lead materialization artifacts: " + ",".join(existing))


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        frame.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _atomic_write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False))
                handle.write("\n")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
