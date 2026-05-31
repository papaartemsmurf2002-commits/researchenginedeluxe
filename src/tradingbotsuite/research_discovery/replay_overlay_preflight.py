from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import pandas as pd

from tradingbotsuite.data.historical_data_catalog import normalize_operator_run_artifact_paths
from tradingbotsuite.optimization.candidate import CandidateConfig
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_cycle.spec import HistoricalResearchCycleSpec, RESEARCH_CYCLE_SPEC_VERSION
from tradingbotsuite.research_discovery.snapshots import atomic_write_json
from tradingbotsuite.research_discovery.state import read_trial_record
from tradingbotsuite.strategies.parameters import (
    allowed_parameter_names,
    allowed_parameter_values,
    defaults_for_holding_window,
)
from tradingbotsuite.strategies.registry import get_strategy_plugin


REPLAY_OVERLAY_CYCLE_PREFLIGHT_VERSION = "replay-overlay-cycle-spec-preflight-v1"
REPLAY_OVERLAY_CYCLE_PREFLIGHT_POLICY = (
    "exact_replay_parameters_must_fit_current_historical_cycle_strategy_domain_no_silent_substitution"
)
REPLAY_OVERLAY_CYCLE_SPEC_DRAFT_VERSION = "replay-overlay-cycle-spec-draft-v1"
REPLAY_OVERLAY_CYCLE_SPEC_DRAFT_POLICY = (
    "emit_singleton_historical_cycle_overlay_specs_only_for_representable_exact_1h_replay_rows"
)
DEFAULT_REPLAY_OVERLAY_STRATEGY_ID = "hmm_knn_local_analog_filter_v2"
DEFAULT_REPLAY_OVERLAY_FEATURE_SET_ID = "features_perp_context_v2"
REPLAY_OVERLAY_KIND = "hmm_knn_local_analog_v2"
_BASE_CYCLE_OPERATOR_WRAPPER_KEYS = frozenset(
    {
        "operator_job_id",
        "operator_original_spec_path",
        "operator_overwrite_protection",
    }
)

_SOURCE_TO_HISTORICAL_PARAMETER_NAMES = {
    "probability_threshold": "probability_threshold",
    "expected_value_threshold": "expected_value_threshold",
    "min_neighbor_count": "min_neighbor_count",
    "min_neighbor_agreement": "min_neighbor_agreement",
    "min_distance_quality": "min_neighbor_distance_quality",
    "min_neighbor_distance_quality": "min_neighbor_distance_quality",
    "vote_margin_threshold": "min_vote_margin",
    "min_vote_margin": "min_vote_margin",
    "event_spacing_bars": "spacing_bars",
    "spacing_bars": "spacing_bars",
}


@dataclass(frozen=True, slots=True)
class ReplayOverlayCyclePreflightResult:
    manifest: dict[str, Any]
    rows: pd.DataFrame


@dataclass(frozen=True, slots=True)
class ReplayOverlayCyclePreflightArtifactResult:
    output_dir: Path
    manifest_path: Path
    rows_path: Path


@dataclass(frozen=True, slots=True)
class ReplayOverlayCycleSpecDraftResult:
    manifest: dict[str, Any]
    rows: pd.DataFrame
    spec_payloads: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ReplayOverlayCycleSpecDraftArtifactResult:
    output_dir: Path
    manifest_path: Path
    rows_path: Path
    spec_paths: tuple[Path, ...]


def preflight_replay_overlay_cycle_specs(
    *,
    replay_spec_path: str | Path,
    replay_discovery_manifest_path: str | Path,
    target_feature_set_id: str = DEFAULT_REPLAY_OVERLAY_FEATURE_SET_ID,
    strategy_id: str = DEFAULT_REPLAY_OVERLAY_STRATEGY_ID,
) -> ReplayOverlayCyclePreflightResult:
    """Preflight exact replay leads before candidate-scoped cycle overlays.

    This is a contract check only. It does not mutate historical-cycle specs,
    run backtests, write candidate packs, or approximate replay parameters.
    """

    replay_path = Path(replay_spec_path).expanduser().resolve()
    discovery_manifest_path = Path(replay_discovery_manifest_path).expanduser().resolve()
    replay_spec = _read_json_normalized(replay_path)
    discovery_manifest = _read_json_normalized(discovery_manifest_path)
    discovery_outputs = _required_outputs(discovery_manifest)
    interesting_path = _required_existing_path(discovery_outputs, "interesting_candidates")
    trials_dir = _required_existing_path(discovery_outputs, "trials")
    if not trials_dir.is_dir():
        raise ValueError(f"replay discovery trials path is not a directory: {trials_dir}")
    interesting = pd.read_parquet(interesting_path)
    symbol = str(discovery_manifest.get("symbol") or replay_spec.get("symbol") or "").upper()

    rows = [
        _preflight_row(
            ledger_record=record,
            replay_spec_path=replay_path,
            replay_spec_sha256=_file_sha256(replay_path),
            replay_discovery_manifest_path=discovery_manifest_path,
            replay_discovery_manifest_sha256=_file_sha256(discovery_manifest_path),
            trials_dir=trials_dir,
            symbol=symbol,
            target_feature_set_id=str(target_feature_set_id),
            strategy_id=str(strategy_id),
        )
        for record in interesting.to_dict("records")
    ]
    frame = pd.DataFrame(rows, columns=_preflight_columns())
    representable_count = int(frame["representable_by_current_historical_cycle_contract"].sum()) if not frame.empty else 0
    unrepresentable_count = int(len(frame) - representable_count)
    prediction_artifact_count = int(frame["overlay_predictions_exists"].sum()) if not frame.empty else 0
    prediction_manifest_count = int(frame["overlay_manifest_exists"].sum()) if not frame.empty else 0
    rejection_reason_counts = _reason_counts(frame)
    manifest = {
        "replay_overlay_cycle_preflight_manifest_version": REPLAY_OVERLAY_CYCLE_PREFLIGHT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "preflight_policy": REPLAY_OVERLAY_CYCLE_PREFLIGHT_POLICY,
        "symbol": symbol,
        "strategy_id": str(strategy_id),
        "target_historical_feature_set_id": str(target_feature_set_id),
        "source_replay_spec_path": str(replay_path),
        "source_replay_spec_sha256": _file_sha256(replay_path),
        "source_discovery_manifest_path": str(discovery_manifest_path),
        "source_discovery_manifest_sha256": _file_sha256(discovery_manifest_path),
        "source_interesting_candidates_path": str(interesting_path),
        "source_interesting_candidates_sha256": _file_sha256(interesting_path),
        "source_trials_dir": str(trials_dir),
        "source_trial_count": int(len(frame)),
        "prediction_artifact_count": prediction_artifact_count,
        "prediction_manifest_count": prediction_manifest_count,
        "representable_candidate_count": representable_count,
        "unrepresentable_candidate_count": unrepresentable_count,
        "rejection_reason_counts": rejection_reason_counts,
        "zero_representable_candidates_is_valid_evidence": representable_count == 0,
        "overlay_cycle_spec_draft_count": representable_count,
        "overlay_cycle_specs_emitted": [],
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "claim_scope": "exact_replay_overlay_preflight_only_no_backtest_rankings_or_candidate_pack_claim",
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["preflight_rows_frame_sha256"] = _frame_hash(frame)
    manifest["preflight_manifest_sha256_payload"] = _stable_hash(
        {key: value for key, value in manifest.items() if key != "preflight_manifest_sha256_payload"}
    )
    return ReplayOverlayCyclePreflightResult(manifest=_json_safe(manifest), rows=frame)


def write_replay_overlay_cycle_preflight_artifacts(
    output_dir: str | Path,
    result: ReplayOverlayCyclePreflightResult,
) -> ReplayOverlayCyclePreflightArtifactResult:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows_path = output / "replay_overlay_cycle_preflight_rows.parquet"
    manifest_path = output / "replay_overlay_cycle_preflight_manifest.json"
    _assert_new_artifact_paths(rows_path, manifest_path)
    _atomic_write_parquet(result.rows, rows_path)
    manifest = dict(result.manifest)
    manifest["required_outputs"] = {
        "preflight_manifest": str(manifest_path),
        "preflight_rows": str(rows_path),
    }
    manifest["preflight_rows_sha256"] = _file_sha256(rows_path)
    reasons = validate_replay_overlay_cycle_preflight_manifest(manifest)
    if reasons:
        raise ValueError("invalid replay overlay cycle preflight manifest: " + "|".join(reasons))
    atomic_write_json(manifest_path, _json_safe(manifest))
    return ReplayOverlayCyclePreflightArtifactResult(
        output_dir=output,
        manifest_path=manifest_path,
        rows_path=rows_path,
    )


def build_replay_overlay_cycle_spec_drafts(
    result: ReplayOverlayCyclePreflightResult,
    *,
    base_cycle_spec_path: str | Path | None = None,
    cycle_output_root: str | Path | None = None,
    required_holding_window: str | None = "1h",
    cycle_id_prefix: str = "replay-overlay-cycle",
) -> ReplayOverlayCycleSpecDraftResult:
    """Build research-only singleton historical-cycle overlay spec drafts.

    The preflight result remains fail-closed: this builder only consumes rows
    already marked representable and records blocked rows without producing
    spec payloads.
    """

    base_path = Path(base_cycle_spec_path).expanduser().resolve() if base_cycle_spec_path is not None else None
    base_payload = _base_cycle_payload(base_path)
    output_root = Path(cycle_output_root).expanduser().resolve() if cycle_output_root is not None else None
    draft_rows: list[dict[str, Any]] = []
    spec_payloads: list[dict[str, Any]] = []
    for row in result.rows.fillna("").to_dict("records"):
        draft_row, payload = _cycle_spec_draft_for_preflight_row(
            row,
            base_payload=base_payload,
            base_cycle_spec_path=base_path,
            cycle_output_root=output_root,
            required_holding_window=required_holding_window,
            cycle_id_prefix=str(cycle_id_prefix),
        )
        draft_rows.append(draft_row)
        if payload is not None:
            spec_payloads.append(payload)
    frame = pd.DataFrame(draft_rows, columns=[*_preflight_columns(), *_spec_draft_columns()])
    status_counts = _status_counts(frame, "spec_generation_status")
    manifest = {
        "replay_overlay_cycle_spec_draft_manifest_version": REPLAY_OVERLAY_CYCLE_SPEC_DRAFT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec_draft_policy": REPLAY_OVERLAY_CYCLE_SPEC_DRAFT_POLICY,
        "source_preflight_manifest_sha256_payload": _stable_hash(result.manifest),
        "source_preflight_rows_frame_sha256": _frame_hash(result.rows),
        "source_preflight_policy": result.manifest.get("preflight_policy"),
        "source_preflight_representable_candidate_count": int(
            result.manifest.get("representable_candidate_count", 0)
        ),
        "source_preflight_unrepresentable_candidate_count": int(
            result.manifest.get("unrepresentable_candidate_count", 0)
        ),
        "base_cycle_spec_path": str(base_path) if base_path is not None else None,
        "base_cycle_spec_sha256": _file_sha256(base_path) if base_path is not None else None,
        "cycle_output_root": str(output_root) if output_root is not None else None,
        "required_holding_window": required_holding_window,
        "source_trial_count": int(len(frame)),
        "overlay_cycle_spec_draft_count": int(len(spec_payloads)),
        "overlay_cycle_specs_emitted": [],
        "spec_generation_status_counts": status_counts,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "claim_scope": "exact_replay_overlay_spec_drafts_only_no_backtest_rankings_or_candidate_pack_claim",
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["spec_draft_rows_frame_sha256"] = _frame_hash(frame)
    manifest["spec_draft_manifest_sha256_payload"] = _stable_hash(
        {key: value for key, value in manifest.items() if key != "spec_draft_manifest_sha256_payload"}
    )
    return ReplayOverlayCycleSpecDraftResult(
        manifest=_json_safe(manifest),
        rows=frame,
        spec_payloads=tuple(_json_safe(payload) for payload in spec_payloads),
    )


def write_replay_overlay_cycle_spec_draft_artifacts(
    output_dir: str | Path,
    result: ReplayOverlayCycleSpecDraftResult,
) -> ReplayOverlayCycleSpecDraftArtifactResult:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows_path = output / "replay_overlay_cycle_spec_draft_rows.parquet"
    manifest_path = output / "replay_overlay_cycle_spec_draft_manifest.json"
    specs_dir = output / "historical_cycle_specs"
    spec_paths = tuple(specs_dir / f"{_safe_identifier(str(payload['cycle_id']))}.json" for payload in result.spec_payloads)
    _assert_new_artifact_paths(rows_path, manifest_path, *spec_paths)
    specs_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    for payload, path in zip(result.spec_payloads, spec_paths, strict=True):
        atomic_write_json(path, _json_safe(payload))
        written_paths.append(path)
    rows = result.rows.copy()
    path_by_cycle_id = {
        str(payload["cycle_id"]): str(path)
        for payload, path in zip(result.spec_payloads, spec_paths, strict=True)
    }
    if not rows.empty and "overlay_cycle_spec_draft_id" in rows.columns:
        rows["overlay_cycle_spec_path"] = rows["overlay_cycle_spec_draft_id"].map(path_by_cycle_id).fillna("")
    _atomic_write_parquet(rows, rows_path)
    manifest = dict(result.manifest)
    manifest["overlay_cycle_specs_emitted"] = [str(path) for path in written_paths]
    manifest["overlay_cycle_spec_sha256"] = {str(path): _file_sha256(path) for path in written_paths}
    manifest["required_outputs"] = {
        "spec_draft_manifest": str(manifest_path),
        "spec_draft_rows": str(rows_path),
        "historical_cycle_specs_dir": str(specs_dir),
        "historical_cycle_specs": [str(path) for path in written_paths],
    }
    manifest["spec_draft_rows_sha256"] = _file_sha256(rows_path)
    reasons = validate_replay_overlay_cycle_spec_draft_manifest(manifest)
    if reasons:
        raise ValueError("invalid replay overlay cycle spec draft manifest: " + "|".join(reasons))
    atomic_write_json(manifest_path, _json_safe(manifest))
    return ReplayOverlayCycleSpecDraftArtifactResult(
        output_dir=output,
        manifest_path=manifest_path,
        rows_path=rows_path,
        spec_paths=tuple(written_paths),
    )


def validate_replay_overlay_cycle_preflight_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("replay_overlay_cycle_preflight_manifest_version") != REPLAY_OVERLAY_CYCLE_PREFLIGHT_VERSION:
        reasons.append("replay_overlay_cycle_preflight_manifest_version_required")
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
    if manifest.get("preflight_policy") != REPLAY_OVERLAY_CYCLE_PREFLIGHT_POLICY:
        reasons.append("preflight_policy_mismatch")
    if "representable_candidate_count" not in manifest:
        reasons.append("representable_candidate_count_required")
    if "unrepresentable_candidate_count" not in manifest:
        reasons.append("unrepresentable_candidate_count_required")
    outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    for key in ("preflight_manifest", "preflight_rows"):
        if key not in outputs:
            reasons.append(f"required_output_missing:{key}")
    emitted = manifest.get("overlay_cycle_specs_emitted")
    if emitted not in ([], ()):
        reasons.append("overlay_cycle_specs_emitted_must_be_empty")
    return reasons


def validate_replay_overlay_cycle_spec_draft_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("replay_overlay_cycle_spec_draft_manifest_version") != REPLAY_OVERLAY_CYCLE_SPEC_DRAFT_VERSION:
        reasons.append("replay_overlay_cycle_spec_draft_manifest_version_required")
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
    if manifest.get("spec_draft_policy") != REPLAY_OVERLAY_CYCLE_SPEC_DRAFT_POLICY:
        reasons.append("spec_draft_policy_mismatch")
    try:
        draft_count = int(manifest.get("overlay_cycle_spec_draft_count", -1))
    except (TypeError, ValueError):
        draft_count = -1
        reasons.append("overlay_cycle_spec_draft_count_must_be_integer")
    emitted = manifest.get("overlay_cycle_specs_emitted")
    if not isinstance(emitted, list):
        reasons.append("overlay_cycle_specs_emitted_must_be_list")
        emitted = []
    if draft_count != len(emitted):
        reasons.append("overlay_cycle_spec_draft_count_must_match_emitted_specs")
    outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    for key in ("spec_draft_manifest", "spec_draft_rows", "historical_cycle_specs_dir", "historical_cycle_specs"):
        if key not in outputs:
            reasons.append(f"required_output_missing:{key}")
    if isinstance(outputs.get("historical_cycle_specs"), list) and len(outputs["historical_cycle_specs"]) != draft_count:
        reasons.append("required_output_historical_cycle_specs_count_mismatch")
    return reasons


def _preflight_row(
    *,
    ledger_record: Mapping[str, Any],
    replay_spec_path: Path,
    replay_spec_sha256: str,
    replay_discovery_manifest_path: Path,
    replay_discovery_manifest_sha256: str,
    trials_dir: Path,
    symbol: str,
    target_feature_set_id: str,
    strategy_id: str,
) -> dict[str, Any]:
    trial_id = str(ledger_record.get("trial_id") or "")
    trial = read_trial_record(trials_dir / f"{trial_id}.json")
    trial_payload = trial.to_payload()
    inner = trial_payload.get("payload") if isinstance(trial_payload.get("payload"), Mapping) else {}
    materialized_candidate_id = str(inner.get("materialized_candidate_id") or trial_payload.get("candidate_id") or "")
    label_horizon = str(inner.get("label_horizon") or ledger_record.get("label_horizon") or "")
    candidate_holding_window = label_horizon
    parameters = _historical_strategy_parameters(inner)
    reasons: list[str] = []
    reasons.extend(
        _strategy_support_reasons(
            strategy_id=strategy_id,
            feature_set_id=target_feature_set_id,
            holding_window=candidate_holding_window,
        )
    )
    parameter_allowed_values = _parameter_allowed_values(
        strategy_id=strategy_id,
        holding_window=candidate_holding_window,
        parameters=parameters,
    )
    reasons.extend(
        _parameter_domain_reasons(
            strategy_id=strategy_id,
            holding_window=candidate_holding_window,
            parameters=parameters,
            allowed_values=parameter_allowed_values,
        )
    )

    predictions_path = _optional_path(inner.get("knn_predictions_path"))
    manifest_path = _optional_path(inner.get("knn_manifest_path"))
    predictions_exists = predictions_path is not None and predictions_path.exists()
    manifest_exists = manifest_path is not None and manifest_path.exists()
    if not predictions_exists:
        reasons.append("materialized_prediction_overlay_missing_predictions")
    manifest_boundary_reasons = _overlay_manifest_boundary_reasons(
        manifest_path,
        expected_predictions_path=predictions_path,
    )
    reasons.extend(manifest_boundary_reasons)
    representable = not reasons
    generated_candidate_id = ""
    overlay_spec_json = ""
    if representable:
        generated_candidate_id = _generated_candidate_id(
            strategy_id=strategy_id,
            feature_set_id=target_feature_set_id,
            holding_window=candidate_holding_window,
            parameters=parameters,
        )
        overlay_spec_json = _stable_json(
            {
                "feature_set_id": target_feature_set_id,
                "kind": REPLAY_OVERLAY_KIND,
                "predictions_path": str(predictions_path),
                "manifest_path": str(manifest_path),
                "join_key": "source_row_index",
                "scope": "candidate",
                "candidate_cache_key": generated_candidate_id,
                "materialized_candidate_id": materialized_candidate_id,
            }
        )
    return {
        "preflight_row_version": REPLAY_OVERLAY_CYCLE_PREFLIGHT_VERSION,
        "symbol": str(inner.get("symbol") or ledger_record.get("symbol") or symbol).upper(),
        "source_replay_spec_path": str(replay_spec_path),
        "source_replay_spec_sha256": replay_spec_sha256,
        "source_discovery_manifest_path": str(replay_discovery_manifest_path),
        "source_discovery_manifest_sha256": replay_discovery_manifest_sha256,
        "materialized_candidate_id": materialized_candidate_id,
        "source_trial_id": str(inner.get("source_trial_id") or trial_id),
        "source_discovery_candidate_id": str(inner.get("source_discovery_candidate_id") or ledger_record.get("candidate_id") or ""),
        "source_record_sha256": str(inner.get("source_record_sha256") or trial_payload.get("record_sha256") or ""),
        "source_prediction_signature_hash": str(inner.get("source_prediction_signature_hash") or ""),
        "source_entry_event_signature_hash": str(inner.get("source_entry_event_signature_hash") or ""),
        "source_registered_feature_set_id": str(inner.get("registered_feature_set_id") or ""),
        "target_historical_feature_set_id": target_feature_set_id,
        "strategy_id": strategy_id,
        "label_horizon": label_horizon,
        "candidate_holding_window": candidate_holding_window,
        "parameters_json": _stable_json(parameters),
        "parameter_allowed_values_json": _stable_json(parameter_allowed_values),
        "representable_by_current_historical_cycle_contract": bool(representable),
        "generated_candidate_id": generated_candidate_id or None,
        "candidate_scoped_overlay_json": overlay_spec_json,
        "overlay_scope": "candidate",
        "overlay_predictions_path": str(predictions_path) if predictions_path is not None else None,
        "overlay_predictions_exists": bool(predictions_exists),
        "overlay_predictions_sha256": _file_sha256(predictions_path) if predictions_exists and predictions_path is not None else None,
        "overlay_manifest_path": str(manifest_path) if manifest_path is not None else None,
        "overlay_manifest_exists": bool(manifest_exists),
        "overlay_manifest_sha256": _file_sha256(manifest_path) if manifest_exists and manifest_path is not None else None,
        "preflight_reasons": "|".join(dict.fromkeys(reasons)),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_pack_written": False,
    }


def _historical_strategy_parameters(payload: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source_name, historical_name in _SOURCE_TO_HISTORICAL_PARAMETER_NAMES.items():
        if source_name not in payload:
            continue
        value = _json_scalar(payload.get(source_name))
        if value is None:
            continue
        result[historical_name] = value
    return dict(sorted(result.items()))


def _base_cycle_payload(base_cycle_spec_path: Path | None) -> dict[str, Any]:
    if base_cycle_spec_path is None:
        return HistoricalResearchCycleSpec.from_payload(
            {"cycle_id": "replay-overlay-cycle-template"},
            spec_path=Path("replay-overlay-cycle-template.json"),
        ).to_payload()
    payload = _read_json_normalized(base_cycle_spec_path)
    for key in _BASE_CYCLE_OPERATOR_WRAPPER_KEYS:
        payload.pop(key, None)
    return HistoricalResearchCycleSpec.from_payload(payload, spec_path=base_cycle_spec_path).to_payload()


def _cycle_spec_draft_for_preflight_row(
    row: Mapping[str, Any],
    *,
    base_payload: Mapping[str, Any],
    base_cycle_spec_path: Path | None,
    cycle_output_root: Path | None,
    required_holding_window: str | None,
    cycle_id_prefix: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    draft_row = dict(row)
    draft_row.update(
        {
            "spec_generation_status": "blocked",
            "spec_generation_reasons": "",
            "overlay_cycle_spec_draft_id": "",
            "overlay_cycle_spec_payload_json": "",
            "overlay_cycle_spec_sha256_payload": "",
            "overlay_cycle_spec_path": "",
        }
    )
    reasons: list[str] = []
    if _json_scalar(row.get("representable_by_current_historical_cycle_contract")) is not True:
        reasons.append("preflight_row_not_representable")
    holding_window = str(row.get("candidate_holding_window") or "")
    if required_holding_window is not None and holding_window != str(required_holding_window):
        reasons.append(f"holding_window_not_required_spec_generation_window:{holding_window}")
    candidate_cache_key = str(row.get("generated_candidate_id") or "")
    if not candidate_cache_key:
        reasons.append("candidate_cache_key_required")
    overlay = _parse_json_object(row.get("candidate_scoped_overlay_json"))
    if not overlay:
        reasons.append("candidate_scoped_overlay_required")
    elif str(overlay.get("candidate_cache_key") or "") != candidate_cache_key:
        reasons.append("candidate_scoped_overlay_candidate_cache_key_mismatch")
    parameters = _parse_json_object(row.get("parameters_json"))
    strategy_id = str(row.get("strategy_id") or "")
    feature_set_id = str(row.get("target_historical_feature_set_id") or "")
    if not strategy_id:
        reasons.append("strategy_id_required")
    if not feature_set_id:
        reasons.append("target_historical_feature_set_id_required")
    if not reasons:
        recalculated = _generated_candidate_id(
            strategy_id=strategy_id,
            feature_set_id=feature_set_id,
            holding_window=holding_window,
            parameters=parameters,
        )
        if recalculated != candidate_cache_key:
            reasons.append("candidate_cache_key_does_not_match_exact_parameters")
    if reasons:
        draft_row["spec_generation_status"] = "blocked"
        draft_row["spec_generation_reasons"] = "|".join(dict.fromkeys(reasons))
        return _json_safe(draft_row), None

    materialized_candidate_id = str(row.get("materialized_candidate_id") or candidate_cache_key[:12])
    cycle_id = _safe_identifier(f"{cycle_id_prefix}-{str(row.get('symbol') or '').lower()}-{materialized_candidate_id}-{candidate_cache_key[:12]}")
    payload = _historical_cycle_spec_payload(
        base_payload=base_payload,
        cycle_id=cycle_id,
        symbol=str(row.get("symbol") or base_payload.get("symbol") or "").upper(),
        holding_window=holding_window,
        strategy_id=strategy_id,
        feature_set_id=feature_set_id,
        parameters=parameters,
        overlay=overlay,
        cycle_output_root=cycle_output_root,
    )
    validation_path = (base_cycle_spec_path.parent if base_cycle_spec_path is not None else Path.cwd()) / f"{cycle_id}.json"
    HistoricalResearchCycleSpec.from_payload(payload, spec_path=validation_path)
    draft_row["spec_generation_status"] = "drafted"
    draft_row["overlay_cycle_spec_draft_id"] = cycle_id
    draft_row["overlay_cycle_spec_payload_json"] = _stable_json(payload)
    draft_row["overlay_cycle_spec_sha256_payload"] = _stable_hash(payload)
    return _json_safe(draft_row), payload


def _historical_cycle_spec_payload(
    *,
    base_payload: Mapping[str, Any],
    cycle_id: str,
    symbol: str,
    holding_window: str,
    strategy_id: str,
    feature_set_id: str,
    parameters: Mapping[str, Any],
    overlay: Mapping[str, Any],
    cycle_output_root: Path | None,
) -> dict[str, Any]:
    payload = dict(base_payload)
    output_dir = cycle_output_root / cycle_id if cycle_output_root is not None else None
    payload.update(
        {
            "spec_version": RESEARCH_CYCLE_SPEC_VERSION,
            "cycle_id": cycle_id,
            "symbol": symbol,
            "holding_windows": [holding_window],
            "features": {
                "feature_sets": [feature_set_id],
                "materialized_prediction_overlays": [_overlay_payload_for_cycle_spec(overlay)],
            },
            "strategies": [strategy_id],
            "optimizer": {
                "method_sequence": ["grid"],
                "max_candidates_per_strategy": 1,
                "top_regions_to_refine": 1,
                "search_spaces": [
                    {
                        "strategy_id": strategy_id,
                        "feature_set_id": feature_set_id,
                        "holding_window": holding_window,
                        "exit_policy_id": "fixed_holding_window",
                        "exit_policy_params": {},
                        "parameters": _singleton_parameter_space(parameters),
                    }
                ],
            },
            "exits": {
                "exit_policies": [
                    {
                        "exit_policy_id": "fixed_holding_window",
                        "exit_policy_params": {},
                        "target_return": None,
                        "stop_return": None,
                        "exit_policy_source": "replay_overlay_spec_draft_fixed_holding",
                    }
                ]
            },
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "candidate_pack_eligible": False,
            "candidate_pack_written": False,
            "live_config_writes_allowed": False,
            "order_placement_allowed": False,
            "sizing_policy_changed": False,
            "promotion_artifact_policy": "research_only_overlay_spec_draft_no_promotion",
            "maturity_label": "research_only_overlay_spec_draft",
            "work_packet": "WPR106-46",
        }
    )
    if output_dir is not None:
        payload["output_dir"] = str(output_dir)
    elif payload.get("output_dir") is not None:
        payload["output_dir"] = str(Path(str(payload["output_dir"])).expanduser().resolve().parent / cycle_id)
    return _json_safe(payload)


def _overlay_payload_for_cycle_spec(overlay: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scope": "candidate",
        "candidate_cache_key": str(overlay["candidate_cache_key"]),
        "materialized_candidate_id": str(overlay.get("materialized_candidate_id") or ""),
        "feature_set_id": str(overlay["feature_set_id"]),
        "kind": str(overlay.get("kind") or REPLAY_OVERLAY_KIND),
        "predictions_path": str(overlay["predictions_path"]),
        "manifest_path": str(overlay["manifest_path"]),
        "join_key": str(overlay.get("join_key") or "source_row_index"),
    }


def _singleton_parameter_space(parameters: Mapping[str, Any]) -> dict[str, list[Any]]:
    return {str(name): [_json_scalar(value)] for name, value in sorted(parameters.items())}


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if value in (None, ""):
        return {}
    parsed = json.loads(str(value))
    if not isinstance(parsed, Mapping):
        raise ValueError("JSON object required")
    return dict(parsed)


def _status_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    counts = frame[column].fillna("").astype(str).value_counts().to_dict()
    return {str(key): int(value) for key, value in sorted(counts.items())}


def _safe_identifier(value: str) -> str:
    normalized = str(value).strip().lower()
    chars = [char if char.isalnum() else "-" for char in normalized]
    collapsed = "-".join(part for part in "".join(chars).split("-") if part)
    return collapsed or "replay-overlay-cycle"


def _strategy_support_reasons(*, strategy_id: str, feature_set_id: str, holding_window: str) -> list[str]:
    try:
        get_strategy_plugin(
            strategy_id,
            config={
                "feature_set_id": feature_set_id,
                "holding_period": holding_window,
            },
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith(f"invalid_holding_period:{strategy_id}:"):
            return [f"label_horizon_not_supported_holding_window:{holding_window}"]
        if message.startswith(f"invalid_feature_set:{strategy_id}:"):
            return [f"target_feature_set_not_supported:{feature_set_id}"]
        return [f"strategy_not_supported:{strategy_id}"]
    return []


def _parameter_allowed_values(
    *,
    strategy_id: str,
    holding_window: str,
    parameters: Mapping[str, Any],
) -> dict[str, list[Any]]:
    return {
        name: [_json_scalar(value) for value in allowed_parameter_values(strategy_id, holding_window, name)]
        for name in sorted(parameters)
    }


def _parameter_domain_reasons(
    *,
    strategy_id: str,
    holding_window: str,
    parameters: Mapping[str, Any],
    allowed_values: Mapping[str, list[Any]],
) -> list[str]:
    reasons: list[str] = []
    known_names = allowed_parameter_names(strategy_id)
    for name, value in sorted(parameters.items()):
        if name not in known_names:
            reasons.append(f"parameter_not_in_historical_strategy_domain:{name}")
            continue
        values = tuple(allowed_values.get(name) or ())
        if values and not any(_values_equal(value, allowed) for allowed in values):
            reasons.append(f"parameter_value_outside_historical_strategy_domain:{name}={_reason_value(value)}")
    return reasons


def _overlay_manifest_boundary_reasons(
    path: Path | None,
    *,
    expected_predictions_path: Path | None,
) -> list[str]:
    if path is None or not path.exists():
        return ["materialized_prediction_overlay_missing_manifest"]
    manifest = _read_json_normalized(path)
    reasons: list[str] = []
    if manifest.get("research_only") is not True:
        reasons.append("materialized_prediction_overlay_manifest_research_only_required")
    if manifest.get("observe_only") is not True:
        reasons.append("materialized_prediction_overlay_manifest_observe_only_required")
    if manifest.get("promotion_ready") is not False:
        reasons.append("materialized_prediction_overlay_manifest_promotion_ready")
    if manifest.get("split_safety_passed") is False:
        reasons.append("materialized_prediction_overlay_manifest_split_safety_failed")
    outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    manifest_predictions_path = _optional_path(outputs.get("knn_predictions"))
    if expected_predictions_path is None:
        reasons.append("materialized_prediction_overlay_predictions_path_required")
    elif manifest_predictions_path is None:
        reasons.append("materialized_prediction_overlay_manifest_predictions_output_required")
    elif manifest_predictions_path != expected_predictions_path:
        reasons.append("materialized_prediction_overlay_manifest_predictions_path_mismatch")
    expected_sha = str(manifest.get("knn_predictions_sha256") or "")
    if expected_predictions_path is not None and expected_predictions_path.exists():
        actual_sha = _file_sha256(expected_predictions_path)
        if not expected_sha:
            reasons.append("materialized_prediction_overlay_manifest_predictions_sha_required")
        elif expected_sha != actual_sha:
            reasons.append("materialized_prediction_overlay_manifest_predictions_sha_mismatch")
    return reasons


def _generated_candidate_id(
    *,
    strategy_id: str,
    feature_set_id: str,
    holding_window: str,
    parameters: Mapping[str, Any],
) -> str:
    resolved = {
        **defaults_for_holding_window(strategy_id, holding_window),
        **dict(parameters),
    }
    return CandidateConfig(
        strategy_id=strategy_id,
        parameters=dict(sorted(resolved.items())),
        feature_set_id=feature_set_id,
        holding_window=holding_window,
        exit_policy_id="fixed_holding_window",
        exit_policy_params={},
    ).cache_key()


def _reason_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    if frame.empty or "preflight_reasons" not in frame.columns:
        return counts
    for raw in frame["preflight_reasons"].fillna("").astype(str):
        for reason in raw.split("|"):
            if not reason:
                continue
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _preflight_columns() -> list[str]:
    return [
        "preflight_row_version",
        "symbol",
        "source_replay_spec_path",
        "source_replay_spec_sha256",
        "source_discovery_manifest_path",
        "source_discovery_manifest_sha256",
        "materialized_candidate_id",
        "source_trial_id",
        "source_discovery_candidate_id",
        "source_record_sha256",
        "source_prediction_signature_hash",
        "source_entry_event_signature_hash",
        "source_registered_feature_set_id",
        "target_historical_feature_set_id",
        "strategy_id",
        "label_horizon",
        "candidate_holding_window",
        "parameters_json",
        "parameter_allowed_values_json",
        "representable_by_current_historical_cycle_contract",
        "generated_candidate_id",
        "candidate_scoped_overlay_json",
        "overlay_scope",
        "overlay_predictions_path",
        "overlay_predictions_exists",
        "overlay_predictions_sha256",
        "overlay_manifest_path",
        "overlay_manifest_exists",
        "overlay_manifest_sha256",
        "preflight_reasons",
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_pack_written",
    ]


def _spec_draft_columns() -> list[str]:
    return [
        "spec_generation_status",
        "spec_generation_reasons",
        "overlay_cycle_spec_draft_id",
        "overlay_cycle_spec_payload_json",
        "overlay_cycle_spec_sha256_payload",
        "overlay_cycle_spec_path",
    ]


def _read_json_normalized(path: Path) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"JSON object required: {resolved}")
    return normalize_operator_run_artifact_paths(dict(payload), artifact_path=resolved, anchor_root=resolved.parent)


def _required_outputs(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    outputs = manifest.get("required_outputs")
    return outputs if isinstance(outputs, Mapping) else {}


def _required_existing_path(required_outputs: Mapping[str, Any], key: str) -> Path:
    raw_path = required_outputs.get(key)
    if not raw_path:
        raise ValueError(f"required output missing: {key}")
    path = Path(str(raw_path)).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"required output path missing for {key}: {path}")
    return path


def _optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value)).expanduser().resolve()


def _values_equal(left: Any, right: Any) -> bool:
    left_value = _json_scalar(left)
    right_value = _json_scalar(right)
    if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
        return abs(float(left_value) - float(right_value)) <= 1e-12
    return left_value == right_value


def _reason_value(value: Any) -> str:
    safe = _json_scalar(value)
    if isinstance(safe, float) and safe.is_integer():
        return str(int(safe))
    return str(safe)


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


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return _json_scalar(value)


def _stable_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return _stable_hash({"columns": list(frame.columns), "rows": []})
    rows = frame.fillna("").to_dict("records")
    return _stable_hash({"columns": list(frame.columns), "rows": rows})


def _assert_new_artifact_paths(*paths: Path) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise ValueError("refusing to overwrite existing replay overlay preflight artifacts: " + ",".join(existing))


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        frame.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
