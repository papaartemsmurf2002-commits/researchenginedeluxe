from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.snapshots import atomic_write_json


WPR10647_REPLAY_EVIDENCE_MANIFEST_VERSION = "wpr106-47-replay-evidence-and-controls-v1"
WPR10647_REPLAY_EVIDENCE_POLICY = (
    "separate_full_exit_lab_window_scope_and_negative_control_evidence_no_candidate_claim"
)
WPR10648_NEGATIVE_CONTROL_MANIFEST_VERSION = "wpr106-48-negative-control-artifacts-v1"
WPR10648_NEGATIVE_CONTROL_POLICY = (
    "first_class_negative_controls_are_control_only_and_not_candidate_evidence"
)
NEGATIVE_CONTROL_KINDS = (
    "shuffled_labels",
    "shifted_context",
    "no_knn_baseline",
    "no_regime_baseline",
)
WPR10648_CONTROL_FAMILIES = (
    "shuffled_labels",
    "shifted_context",
    "no_knn_overlay",
    "no_regime_backend",
)
_CONTROL_FAMILY_ALIASES = {
    "no_knn_baseline": "no_knn_overlay",
    "no_regime_baseline": "no_regime_backend",
}
_CONTROL_MISSING_REASONS = {
    "shuffled_labels": "shuffled_label_control_artifact_missing",
    "shifted_context": "shifted_context_control_artifact_missing",
    "no_knn_baseline": "no_knn_baseline_artifact_missing",
    "no_regime_baseline": "no_regime_baseline_artifact_missing",
}


@dataclass(frozen=True, slots=True)
class WPR10647SymbolEvidenceInput:
    symbol: str
    preflight_manifest_path: Path
    preflight_rows_path: Path
    spec_draft_manifest_path: Path | None = None
    spec_draft_rows_path: Path | None = None
    exit_lab_manifest_path: Path | None = None
    cycle_manifest_paths: tuple[Path, ...] = ()
    modern_window_profile_paths: tuple[Path, ...] = ()
    control_artifact_paths: Mapping[str, Path] | None = None


@dataclass(frozen=True, slots=True)
class WPR10647ReplayEvidenceResult:
    manifest: Mapping[str, Any]
    exit_lab_rows: pd.DataFrame
    window_rows: pd.DataFrame
    negative_control_rows: pd.DataFrame


@dataclass(frozen=True, slots=True)
class WPR10647ReplayEvidenceArtifactResult:
    output_dir: Path
    manifest_path: Path
    exit_lab_rows_path: Path
    window_rows_path: Path
    negative_control_rows_path: Path


@dataclass(frozen=True, slots=True)
class WPR10648NegativeControlInput:
    symbol: str
    source_manifest_path: Path
    source_rows_path: Path
    replay_profile_path: Path | None = None
    validation_manifest_path: Path | None = None
    modern_window_profile_path: Path | None = None
    require_modern_window_evidence: bool = False
    deterministic_seed: int = 10648
    shift_size: int = 1


@dataclass(frozen=True, slots=True)
class WPR10648NegativeControlResult:
    manifest: Mapping[str, Any]
    control_rows: pd.DataFrame


@dataclass(frozen=True, slots=True)
class WPR10648NegativeControlArtifactResult:
    output_dir: Path
    manifest_path: Path
    control_rows_path: Path


def build_wpr10647_replay_evidence(
    *,
    symbol_inputs: Sequence[WPR10647SymbolEvidenceInput],
    packet_id: str = "WPR106-47",
) -> WPR10647ReplayEvidenceResult:
    exit_lab_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    negative_control_rows: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    for item in symbol_inputs:
        symbol = str(item.symbol).upper()
        preflight_manifest = _read_json(item.preflight_manifest_path)
        preflight = pd.read_parquet(item.preflight_rows_path)
        spec_rows = _read_optional_frame(item.spec_draft_rows_path)
        exit_lab_manifest, exit_lab_gates = _exit_lab_evidence(item.exit_lab_manifest_path)
        exit_lab_rows.extend(
            _exit_lab_rows(
                symbol=symbol,
                preflight=preflight,
                exit_lab_manifest_path=item.exit_lab_manifest_path,
                exit_lab_manifest=exit_lab_manifest,
                exit_lab_gates=exit_lab_gates,
            )
        )
        window_rows.extend(
            _window_rows(
                symbol=symbol,
                preflight_manifest_path=item.preflight_manifest_path,
                preflight_manifest=preflight_manifest,
                preflight_rows_path=item.preflight_rows_path,
                preflight=preflight,
                spec_draft_manifest_path=item.spec_draft_manifest_path,
                spec_draft_rows_path=item.spec_draft_rows_path,
                spec_rows=spec_rows,
                cycle_manifest_paths=item.cycle_manifest_paths,
                modern_window_profile_paths=item.modern_window_profile_paths,
            )
        )
        negative_control_rows.extend(
            _negative_control_rows(
                symbol=symbol,
                preflight=preflight,
                control_artifact_paths=item.control_artifact_paths or {},
            )
        )
        source_summaries.append(
            {
                "symbol": symbol,
                "preflight_manifest_path": str(Path(item.preflight_manifest_path).resolve()),
                "preflight_manifest_sha256": _file_sha256(item.preflight_manifest_path),
                "preflight_rows_path": str(Path(item.preflight_rows_path).resolve()),
                "preflight_rows_sha256": _file_sha256(item.preflight_rows_path),
                "spec_draft_manifest_path": str(Path(item.spec_draft_manifest_path).resolve())
                if item.spec_draft_manifest_path is not None
                else None,
                "spec_draft_manifest_sha256": _file_sha256(item.spec_draft_manifest_path)
                if item.spec_draft_manifest_path is not None and item.spec_draft_manifest_path.exists()
                else None,
                "exit_lab_manifest_path": str(Path(item.exit_lab_manifest_path).resolve())
                if item.exit_lab_manifest_path is not None
                else None,
                "exit_lab_manifest_sha256": _file_sha256(item.exit_lab_manifest_path)
                if item.exit_lab_manifest_path is not None and item.exit_lab_manifest_path.exists()
                else None,
                "cycle_manifest_count": int(len(item.cycle_manifest_paths)),
                "modern_window_profile_count": int(len(item.modern_window_profile_paths)),
                "control_artifact_count": int(len(item.control_artifact_paths or {})),
            }
        )

    exit_frame = pd.DataFrame(exit_lab_rows, columns=_exit_lab_columns())
    window_frame = pd.DataFrame(window_rows, columns=_window_columns())
    control_frame = pd.DataFrame(negative_control_rows, columns=_negative_control_columns())
    manifest = {
        "wpr10647_replay_evidence_manifest_version": WPR10647_REPLAY_EVIDENCE_MANIFEST_VERSION,
        "wpr10647_replay_evidence_policy": WPR10647_REPLAY_EVIDENCE_POLICY,
        "packet_id": str(packet_id),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_summaries": source_summaries,
        "symbol_count": int(len(source_summaries)),
        "full_replay_lead_count": int(len(exit_frame)),
        "full_replay_exit_lab_status_counts": _status_counts(exit_frame, "exit_lab_gate_status"),
        "window_scope_status_counts": _status_counts(window_frame, "window_status"),
        "negative_control_row_count": int(len(control_frame)),
        "negative_control_status_counts": _status_counts(control_frame, "control_status"),
        "negative_control_kind_counts": _status_counts(control_frame, "control_kind"),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "claim_scope": "research_only_theory_separated_audit_no_live_paper_promotion_or_candidate_ready_claim",
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["full_replay_exit_lab_rows_frame_sha256"] = _frame_hash(exit_frame)
    manifest["window_comparison_rows_frame_sha256"] = _frame_hash(window_frame)
    manifest["negative_control_rows_frame_sha256"] = _frame_hash(control_frame)
    return WPR10647ReplayEvidenceResult(
        manifest=_json_safe(manifest),
        exit_lab_rows=exit_frame,
        window_rows=window_frame,
        negative_control_rows=control_frame,
    )


def write_wpr10647_replay_evidence_artifacts(
    *,
    output_dir: str | Path,
    result: WPR10647ReplayEvidenceResult,
) -> WPR10647ReplayEvidenceArtifactResult:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "wpr10647_replay_evidence_manifest.json"
    exit_path = output / "wpr10647_full_replay_exit_lab_rows.parquet"
    window_path = output / "wpr10647_window_comparison_rows.parquet"
    controls_path = output / "wpr10647_negative_control_rows.parquet"
    _assert_new_artifact_paths(manifest_path, exit_path, window_path, controls_path)
    _atomic_write_parquet(result.exit_lab_rows, exit_path)
    _atomic_write_parquet(result.window_rows, window_path)
    _atomic_write_parquet(result.negative_control_rows, controls_path)
    manifest = dict(result.manifest)
    manifest["required_outputs"] = {
        "wpr10647_replay_evidence_manifest": str(manifest_path),
        "full_replay_exit_lab_rows": str(exit_path),
        "window_comparison_rows": str(window_path),
        "negative_control_rows": str(controls_path),
    }
    manifest["full_replay_exit_lab_rows_sha256"] = _file_sha256(exit_path)
    manifest["window_comparison_rows_sha256"] = _file_sha256(window_path)
    manifest["negative_control_rows_sha256"] = _file_sha256(controls_path)
    reasons = validate_wpr10647_replay_evidence_manifest(manifest)
    if reasons:
        raise ValueError("invalid WPR106-47 replay evidence manifest: " + "|".join(reasons))
    atomic_write_json(manifest_path, _json_safe(manifest))
    return WPR10647ReplayEvidenceArtifactResult(
        output_dir=output,
        manifest_path=manifest_path,
        exit_lab_rows_path=exit_path,
        window_rows_path=window_path,
        negative_control_rows_path=controls_path,
    )


def build_wpr10648_negative_control_artifacts(
    *,
    symbol_inputs: Sequence[WPR10648NegativeControlInput],
    packet_id: str = "WPR106-48",
) -> WPR10648NegativeControlResult:
    control_rows: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    for item in symbol_inputs:
        source_manifest_path = Path(item.source_manifest_path).expanduser().resolve()
        source_rows_path = Path(item.source_rows_path).expanduser().resolve()
        source_manifest = _read_json(source_manifest_path)
        source_rows = pd.read_parquet(source_rows_path)
        symbol = str(item.symbol or source_manifest.get("symbol") or "").upper()
        common_reasons = _control_common_reasons(
            source_manifest=source_manifest,
            replay_profile_path=item.replay_profile_path,
            validation_manifest_path=item.validation_manifest_path,
            modern_window_profile_path=item.modern_window_profile_path,
            require_modern_window_evidence=item.require_modern_window_evidence,
        )
        rows, family_summaries = _wpr10648_control_rows_for_symbol(
            symbol=symbol,
            source_manifest_path=source_manifest_path,
            source_rows_path=source_rows_path,
            source_manifest=source_manifest,
            source_rows=source_rows,
            common_reasons=common_reasons,
            deterministic_seed=item.deterministic_seed,
            shift_size=item.shift_size,
            replay_profile_path=item.replay_profile_path,
            validation_manifest_path=item.validation_manifest_path,
            modern_window_profile_path=item.modern_window_profile_path,
        )
        control_rows.extend(rows)
        source_summaries.append(
            {
                "symbol": symbol,
                "source_manifest_path": str(source_manifest_path),
                "source_manifest_sha256": _file_sha256(source_manifest_path),
                "source_rows_path": str(source_rows_path),
                "source_rows_sha256": _file_sha256(source_rows_path),
                "source_row_count": int(len(source_rows)),
                "replay_profile_path": str(Path(item.replay_profile_path).expanduser().resolve())
                if item.replay_profile_path is not None
                else "",
                "replay_profile_sha256": _file_sha256(item.replay_profile_path)
                if item.replay_profile_path is not None and Path(item.replay_profile_path).exists()
                else "",
                "validation_manifest_path": str(Path(item.validation_manifest_path).expanduser().resolve())
                if item.validation_manifest_path is not None
                else "",
                "validation_manifest_sha256": _file_sha256(item.validation_manifest_path)
                if item.validation_manifest_path is not None and Path(item.validation_manifest_path).exists()
                else "",
                "modern_window_profile_path": str(Path(item.modern_window_profile_path).expanduser().resolve())
                if item.modern_window_profile_path is not None
                else "",
                "modern_window_profile_sha256": _file_sha256(item.modern_window_profile_path)
                if item.modern_window_profile_path is not None and Path(item.modern_window_profile_path).exists()
                else "",
                "require_modern_window_evidence": bool(item.require_modern_window_evidence),
                "deterministic_seed": int(item.deterministic_seed),
                "shift_size": int(item.shift_size),
                "family_summaries": family_summaries,
            }
        )
    control_frame = pd.DataFrame(control_rows, columns=_wpr10648_control_columns())
    manifest = {
        "wpr10648_negative_control_manifest_version": WPR10648_NEGATIVE_CONTROL_MANIFEST_VERSION,
        "wpr10648_negative_control_policy": WPR10648_NEGATIVE_CONTROL_POLICY,
        "packet_id": str(packet_id),
        "artifact_family": "negative_control",
        "control_only": True,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "control_families": list(WPR10648_CONTROL_FAMILIES),
        "source_summaries": source_summaries,
        "symbol_count": int(len(source_summaries)),
        "control_row_count": int(len(control_frame)),
        "control_status_counts": _status_counts(control_frame, "control_status"),
        "control_family_counts": _status_counts(control_frame, "control_family"),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "claim_scope": "negative_controls_only_not_candidate_evidence_no_live_paper_or_promotion_claim",
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["control_rows_frame_sha256"] = _frame_hash(control_frame)
    return WPR10648NegativeControlResult(manifest=_json_safe(manifest), control_rows=control_frame)


def write_wpr10648_negative_control_artifacts(
    *,
    output_dir: str | Path,
    result: WPR10648NegativeControlResult,
) -> WPR10648NegativeControlArtifactResult:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "wpr10648_negative_control_manifest.json"
    rows_path = output / "wpr10648_negative_control_rows.parquet"
    _assert_new_artifact_paths(manifest_path, rows_path)
    _atomic_write_parquet(result.control_rows, rows_path)
    manifest = dict(result.manifest)
    manifest["required_outputs"] = {
        "wpr10648_negative_control_manifest": str(manifest_path),
        "wpr10648_negative_control_rows": str(rows_path),
    }
    manifest["control_rows_sha256"] = _file_sha256(rows_path)
    reasons = validate_wpr10648_negative_control_manifest(manifest)
    if reasons:
        raise ValueError("invalid WPR106-48 negative control manifest: " + "|".join(reasons))
    atomic_write_json(manifest_path, _json_safe(manifest))
    return WPR10648NegativeControlArtifactResult(
        output_dir=output,
        manifest_path=manifest_path,
        control_rows_path=rows_path,
    )


def validate_wpr10647_replay_evidence_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("wpr10647_replay_evidence_manifest_version") != WPR10647_REPLAY_EVIDENCE_MANIFEST_VERSION:
        reasons.append("wpr10647_replay_evidence_manifest_version_required")
    if manifest.get("wpr10647_replay_evidence_policy") != WPR10647_REPLAY_EVIDENCE_POLICY:
        reasons.append("wpr10647_replay_evidence_policy_mismatch")
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
    outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    for key in (
        "wpr10647_replay_evidence_manifest",
        "full_replay_exit_lab_rows",
        "window_comparison_rows",
        "negative_control_rows",
    ):
        if key not in outputs:
            reasons.append(f"required_output_missing:{key}")
    return reasons


def validate_wpr10648_negative_control_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("wpr10648_negative_control_manifest_version") != WPR10648_NEGATIVE_CONTROL_MANIFEST_VERSION:
        reasons.append("wpr10648_negative_control_manifest_version_required")
    if manifest.get("wpr10648_negative_control_policy") != WPR10648_NEGATIVE_CONTROL_POLICY:
        reasons.append("wpr10648_negative_control_policy_mismatch")
    if manifest.get("artifact_family") != "negative_control":
        reasons.append("artifact_family_must_be_negative_control")
    if manifest.get("control_only") is not True:
        reasons.append("control_only_must_be_true")
    if manifest.get("candidate_evidence") is not False:
        reasons.append("candidate_evidence_must_be_false")
    if manifest.get("candidate_pack_eligible") is not False:
        reasons.append("candidate_pack_eligible_must_be_false")
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
    families = tuple(str(item) for item in manifest.get("control_families") or ())
    if families != WPR10648_CONTROL_FAMILIES:
        reasons.append("control_families_must_match_wpr10648_contract")
    outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    for key in ("wpr10648_negative_control_manifest", "wpr10648_negative_control_rows"):
        if key not in outputs:
            reasons.append(f"required_output_missing:{key}")
    return reasons


def _control_common_reasons(
    *,
    source_manifest: Mapping[str, Any],
    replay_profile_path: Path | None,
    validation_manifest_path: Path | None,
    modern_window_profile_path: Path | None,
    require_modern_window_evidence: bool,
) -> list[str]:
    reasons: list[str] = []
    if source_manifest.get("research_only") is not True:
        reasons.append("source_manifest_research_only_required")
    if source_manifest.get("observe_only") is not True:
        reasons.append("source_manifest_observe_only_required")
    if source_manifest.get("promotion_ready") is not False:
        reasons.append("source_manifest_promotion_ready_must_be_false")
    if source_manifest.get("candidate_pack_written") is not False:
        reasons.append("source_manifest_candidate_pack_written_must_be_false")
    if not _exact_replay_lineage(source_manifest):
        reasons.append("exact_replay_lineage_missing")
    if replay_profile_path is None or not Path(replay_profile_path).exists():
        reasons.append("replay_profile_provenance_missing")
    if validation_manifest_path is None or not Path(validation_manifest_path).exists():
        reasons.append("validation_manifest_missing")
    if require_modern_window_evidence and (
        modern_window_profile_path is None or not Path(modern_window_profile_path).exists()
    ):
        reasons.append("modern_window_evidence_required")
    return list(dict.fromkeys(reasons))


def _wpr10648_control_rows_for_symbol(
    *,
    symbol: str,
    source_manifest_path: Path,
    source_rows_path: Path,
    source_manifest: Mapping[str, Any],
    source_rows: pd.DataFrame,
    common_reasons: Sequence[str],
    deterministic_seed: int,
    shift_size: int,
    replay_profile_path: Path | None,
    validation_manifest_path: Path | None,
    modern_window_profile_path: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    label_summary = _shuffled_label_summary(source_rows, seed=deterministic_seed)
    context_summary = _shifted_context_summary(source_rows, shift_size=shift_size)
    source_manifest_sha = _file_sha256(source_manifest_path)
    source_rows_sha = _file_sha256(source_rows_path)
    replay_profile_resolved = _resolved_existing_path(replay_profile_path)
    validation_manifest_resolved = _resolved_existing_path(validation_manifest_path)
    modern_profile_resolved = _resolved_existing_path(modern_window_profile_path)
    lineage = _exact_replay_lineage(source_manifest)
    rows: list[dict[str, Any]] = []
    family_summaries: dict[str, Any] = {}
    for family in WPR10648_CONTROL_FAMILIES:
        family_reasons = _family_specific_control_reasons(
            family,
            label_summary=label_summary,
            context_summary=context_summary,
        )
        reasons = list(dict.fromkeys([*common_reasons, *family_reasons]))
        family_summaries[family] = {
            "control_status": "available" if not reasons else "blocked",
            "control_reasons": reasons,
        }
        for lead in source_rows.fillna("").to_dict("records"):
            rows.append(
                {
                    "artifact_family": "negative_control",
                    "evidence_scope": "wpr10648_first_class_negative_control",
                    "symbol": symbol,
                    "materialized_candidate_id": str(lead.get("materialized_candidate_id") or lead.get("candidate_id") or ""),
                    "generated_candidate_id": str(lead.get("generated_candidate_id") or ""),
                    "source_trial_id": str(lead.get("source_trial_id") or lead.get("trial_id") or ""),
                    "source_record_sha256": str(lead.get("source_record_sha256") or lead.get("record_sha256") or ""),
                    "control_family": family,
                    "control_status": "available" if not reasons else "blocked",
                    "control_reasons": "|".join(reasons),
                    "deterministic_seed": int(deterministic_seed),
                    "source_manifest_path": str(source_manifest_path),
                    "source_manifest_sha256": source_manifest_sha,
                    "source_rows_path": str(source_rows_path),
                    "source_rows_sha256": source_rows_sha,
                    "replay_profile_path": str(replay_profile_resolved or ""),
                    "replay_profile_sha256": _file_sha256(replay_profile_resolved) if replay_profile_resolved else "",
                    "validation_manifest_path": str(validation_manifest_resolved or ""),
                    "validation_manifest_sha256": (
                        _file_sha256(validation_manifest_resolved) if validation_manifest_resolved else ""
                    ),
                    "modern_window_profile_path": str(modern_profile_resolved or ""),
                    "modern_window_profile_sha256": _file_sha256(modern_profile_resolved) if modern_profile_resolved else "",
                    "exact_replay_lineage_sha256": _stable_hash(lineage) if lineage else "",
                    "source_label_hash": label_summary["source_label_hash"],
                    "shuffled_label_hash": label_summary["shuffled_label_hash"],
                    "label_distribution_match": bool(label_summary["label_distribution_match"]),
                    "derangement_rate": float(label_summary["derangement_rate"]),
                    "shift_size": int(shift_size),
                    "edge_row_drop_count": int(context_summary["edge_row_drop_count"]),
                    "shifted_context_source_hash": context_summary["source_hash"],
                    "shifted_context_output_hash": context_summary["output_hash"],
                    "monotonic_timestamp_validation": bool(context_summary["monotonic_timestamp_validation"]),
                    "overlay_used": False if family == "no_knn_overlay" else None,
                    "knn_artifact_input": "" if family == "no_knn_overlay" else None,
                    "regime_model_backend": "none" if family == "no_regime_backend" else None,
                    "hmm_artifact_dependency": "" if family == "no_regime_backend" else None,
                    "control_only": True,
                    "candidate_evidence": False,
                    "candidate_pack_eligible": False,
                    "candidate_pack_written": False,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
            )
    return rows, family_summaries


def _family_specific_control_reasons(
    family: str,
    *,
    label_summary: Mapping[str, Any],
    context_summary: Mapping[str, Any],
) -> list[str]:
    if family == "shuffled_labels":
        return list(label_summary.get("reasons") or ())
    if family == "shifted_context":
        return list(context_summary.get("reasons") or ())
    if family in {"no_knn_overlay", "no_regime_backend"}:
        return []
    return [f"unknown_control_family:{family}"]


def _shuffled_label_summary(frame: pd.DataFrame, *, seed: int) -> dict[str, Any]:
    label_column = _first_existing_column(
        frame,
        ("label", "target_label", "prediction_label", "directional_label", "realized_direction", "label_value"),
    )
    if label_column is None:
        return {
            "source_label_hash": "",
            "shuffled_label_hash": "",
            "label_distribution_match": False,
            "derangement_rate": 0.0,
            "reasons": ["source_label_column_missing"],
        }
    labels = [str(value) for value in frame[label_column].fillna("").tolist()]
    reasons: list[str] = []
    if len(labels) <= 1:
        reasons.append("shuffled_label_source_too_small")
        order = list(range(len(labels)))
    else:
        order = list(pd.Series(range(len(labels))).sample(frac=1, random_state=int(seed)).tolist())
        if order == list(range(len(labels))):
            order = order[1:] + order[:1]
    shuffled = [labels[index] for index in order]
    derangement_rate = (
        sum(1 for position, source_index in enumerate(order) if position != source_index) / len(order)
        if order
        else 0.0
    )
    distribution_match = _value_counts(labels) == _value_counts(shuffled)
    if not distribution_match:
        reasons.append("shuffled_label_distribution_mismatch")
    if len(labels) > 1 and derangement_rate <= 0.0:
        reasons.append("shuffled_label_derangement_missing")
    return {
        "source_label_hash": _stable_hash(labels),
        "shuffled_label_hash": _stable_hash(shuffled),
        "label_distribution_match": distribution_match,
        "derangement_rate": derangement_rate,
        "reasons": reasons,
    }


def _shifted_context_summary(frame: pd.DataFrame, *, shift_size: int) -> dict[str, Any]:
    timestamp_column = _first_existing_column(
        frame,
        ("timestamp_ms", "bar_time_ms", "event_time_ms", "open_time_ms", "timestamp"),
    )
    reasons: list[str] = []
    if timestamp_column is None:
        reasons.append("source_timestamp_column_missing")
        monotonic = False
    else:
        timestamps = pd.to_numeric(frame[timestamp_column], errors="coerce")
        monotonic = bool(timestamps.notna().all() and timestamps.is_monotonic_increasing)
        if not monotonic:
            reasons.append("source_timestamp_not_monotonic")
    shift = max(1, int(shift_size))
    if len(frame) <= shift:
        reasons.append("shifted_context_source_too_small")
    context_columns = [
        column
        for column in frame.columns
        if "context" in str(column).lower()
        or str(column)
        in {
            "feature_column_set_id",
            "regime_mode",
            "regime_detector_type",
            "regime_model_backend",
            "distance_metric",
            "k",
        }
    ]
    if not context_columns:
        context_columns = [column for column in ("candidate_id", "materialized_candidate_id", "source_trial_id") if column in frame.columns]
    source_payload = frame.loc[:, context_columns].fillna("").astype(str).to_dict("records") if context_columns else []
    shifted_payload = (
        frame.loc[:, context_columns].shift(shift).dropna(how="all").fillna("").astype(str).to_dict("records")
        if context_columns and len(frame) > shift
        else []
    )
    return {
        "source_hash": _stable_hash(source_payload) if source_payload else "",
        "output_hash": _stable_hash(shifted_payload) if shifted_payload else "",
        "edge_row_drop_count": min(shift, len(frame)),
        "monotonic_timestamp_validation": monotonic,
        "reasons": list(dict.fromkeys(reasons)),
    }


def _exact_replay_lineage(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    lineage = source_manifest.get("exact_replay_lineage")
    if isinstance(lineage, Mapping) and lineage:
        return dict(lineage)
    replay_spec_path = str(source_manifest.get("source_replay_spec_path") or "")
    discovery_manifest_path = str(source_manifest.get("source_discovery_manifest_path") or "")
    if replay_spec_path and discovery_manifest_path:
        return {
            "source_replay_spec_path": replay_spec_path,
            "source_replay_spec_sha256": str(source_manifest.get("source_replay_spec_sha256") or ""),
            "source_discovery_manifest_path": discovery_manifest_path,
            "source_discovery_manifest_sha256": str(source_manifest.get("source_discovery_manifest_sha256") or ""),
        }
    replay_metadata = source_manifest.get("replay_metadata")
    if isinstance(replay_metadata, Mapping):
        replay_path = str(replay_metadata.get("source_materialization_manifest_path") or "")
        discovery_path = str(replay_metadata.get("source_discovery_manifest_path") or "")
        if replay_path and discovery_path:
            return {
                "source_materialization_manifest_path": replay_path,
                "source_materialization_manifest_sha256": str(
                    replay_metadata.get("source_materialization_manifest_sha256") or ""
                ),
                "source_discovery_manifest_path": discovery_path,
                "source_discovery_manifest_sha256": str(
                    replay_metadata.get("source_discovery_manifest_sha256") or ""
                ),
            }
    return {}


def _resolved_existing_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    candidate = Path(path).expanduser().resolve()
    return candidate if candidate.exists() else None


def _first_existing_column(frame: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    columns = set(str(column) for column in frame.columns)
    for column in candidates:
        if column in columns:
            return column
    return None


def _value_counts(values: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def _exit_lab_rows(
    *,
    symbol: str,
    preflight: pd.DataFrame,
    exit_lab_manifest_path: Path | None,
    exit_lab_manifest: Mapping[str, Any] | None,
    exit_lab_gates: pd.DataFrame | None,
) -> list[dict[str, Any]]:
    gate_lookup = _gate_lookup(exit_lab_gates)
    rows: list[dict[str, Any]] = []
    for lead in preflight.fillna("").to_dict("records"):
        materialized_id = str(lead.get("materialized_candidate_id") or "")
        gate = gate_lookup.get(materialized_id)
        reasons: list[str] = []
        if exit_lab_manifest is None:
            reasons.append("exit_lab_manifest_missing")
        if exit_lab_gates is None:
            reasons.append("exit_lab_candidate_gates_missing")
        if gate is None:
            reasons.append("exit_lab_candidate_gate_row_missing")
        gate_reasons = str((gate or {}).get("exit_lab_reasons") or "")
        if gate_reasons:
            reasons.extend(reason for reason in gate_reasons.split("|") if reason)
        rows.append(
            {
                "evidence_scope": "full_48_exact_replay_exit_lab",
                "symbol": symbol,
                "materialized_candidate_id": materialized_id,
                "generated_candidate_id": str(lead.get("generated_candidate_id") or ""),
                "source_trial_id": str(lead.get("source_trial_id") or ""),
                "source_discovery_candidate_id": str(lead.get("source_discovery_candidate_id") or ""),
                "source_record_sha256": str(lead.get("source_record_sha256") or ""),
                "exit_lab_manifest_path": str(Path(exit_lab_manifest_path).resolve()) if exit_lab_manifest_path is not None else "",
                "exit_lab_candidate_gate_found": gate is not None,
                "exit_lab_status": str((gate or {}).get("exit_lab_status") or "blocked"),
                "exit_lab_gate_status": str((gate or {}).get("exit_lab_gate_status") or "blocked"),
                "exit_lab_reasons": "|".join(dict.fromkeys(reasons)),
                "exit_lab_best_family": str((gate or {}).get("exit_lab_best_family") or ""),
                "fixed_holding_score_delta": _safe_float((gate or {}).get("fixed_holding_score_delta")),
                "candidate_pack_written": False,
                "candidate_pack_eligible": False,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return rows


def _window_rows(
    *,
    symbol: str,
    preflight_manifest_path: Path,
    preflight_manifest: Mapping[str, Any],
    preflight_rows_path: Path,
    preflight: pd.DataFrame,
    spec_draft_manifest_path: Path | None,
    spec_draft_rows_path: Path | None,
    spec_rows: pd.DataFrame | None,
    cycle_manifest_paths: tuple[Path, ...],
    modern_window_profile_paths: tuple[Path, ...],
) -> list[dict[str, Any]]:
    representable_count = int(preflight["representable_by_current_historical_cycle_contract"].sum()) if "representable_by_current_historical_cycle_contract" in preflight else 0
    drafted_count = int(spec_rows["spec_generation_status"].astype(str).eq("drafted").sum()) if spec_rows is not None and "spec_generation_status" in spec_rows else 0
    rows = [
        {
            "evidence_scope": "full_window_replay_overlay",
            "symbol": symbol,
            "window_status": "available",
            "window_reasons": "",
            "preflight_manifest_path": str(Path(preflight_manifest_path).resolve()),
            "preflight_manifest_sha256": _file_sha256(preflight_manifest_path),
            "preflight_rows_path": str(Path(preflight_rows_path).resolve()),
            "preflight_rows_sha256": _file_sha256(preflight_rows_path),
            "spec_draft_manifest_path": str(Path(spec_draft_manifest_path).resolve()) if spec_draft_manifest_path is not None else "",
            "spec_draft_rows_path": str(Path(spec_draft_rows_path).resolve()) if spec_draft_rows_path is not None else "",
            "modern_window_profile_path": "",
            "modern_window_profile_sha256": "",
            "source_trial_count": int(preflight_manifest.get("source_trial_count") or len(preflight)),
            "representable_candidate_count": representable_count,
            "overlay_cycle_spec_draft_count": drafted_count,
            "cycle_manifest_count": int(len(cycle_manifest_paths)),
            "candidate_pack_written": False,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }
    ]
    if modern_window_profile_paths:
        for path in modern_window_profile_paths:
            rows.append(
                {
                    "evidence_scope": "modern_window_replay_overlay",
                    "symbol": symbol,
                    "window_status": "available",
                    "window_reasons": "",
                    "preflight_manifest_path": "",
                    "preflight_manifest_sha256": "",
                    "preflight_rows_path": "",
                    "preflight_rows_sha256": "",
                    "spec_draft_manifest_path": "",
                    "spec_draft_rows_path": "",
                    "modern_window_profile_path": str(Path(path).resolve()),
                    "modern_window_profile_sha256": _file_sha256(path),
                    "source_trial_count": 0,
                    "representable_candidate_count": 0,
                    "overlay_cycle_spec_draft_count": 0,
                    "cycle_manifest_count": 0,
                    "candidate_pack_written": False,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
            )
    else:
        rows.append(
            {
                "evidence_scope": "modern_window_replay_overlay",
                "symbol": symbol,
                "window_status": "blocked",
                "window_reasons": "modern_window_profile_artifact_missing",
                "preflight_manifest_path": "",
                "preflight_manifest_sha256": "",
                "preflight_rows_path": "",
                "preflight_rows_sha256": "",
                "spec_draft_manifest_path": "",
                "spec_draft_rows_path": "",
                "modern_window_profile_path": "",
                "modern_window_profile_sha256": "",
                "source_trial_count": 0,
                "representable_candidate_count": 0,
                "overlay_cycle_spec_draft_count": 0,
                "cycle_manifest_count": 0,
                "candidate_pack_written": False,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return rows


def _negative_control_rows(
    *,
    symbol: str,
    preflight: pd.DataFrame,
    control_artifact_paths: Mapping[str, Path],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    artifact_status = {
        control_kind: _negative_control_artifact_status(control_kind, control_artifact_paths.get(control_kind))
        for control_kind in NEGATIVE_CONTROL_KINDS
    }
    for lead in preflight.fillna("").to_dict("records"):
        for control_kind in NEGATIVE_CONTROL_KINDS:
            artifact_path = control_artifact_paths.get(control_kind)
            control_status, control_reasons, artifact_sha = artifact_status[control_kind]
            rows.append(
                {
                    "evidence_scope": "negative_control_and_leakage_stress",
                    "symbol": symbol,
                    "materialized_candidate_id": str(lead.get("materialized_candidate_id") or ""),
                    "generated_candidate_id": str(lead.get("generated_candidate_id") or ""),
                    "source_trial_id": str(lead.get("source_trial_id") or ""),
                    "control_kind": control_kind,
                    "control_status": control_status,
                    "control_reasons": control_reasons,
                    "control_artifact_path": str(Path(artifact_path).resolve()) if artifact_path is not None else "",
                    "control_artifact_sha256": artifact_sha,
                    "control_only": True,
                    "candidate_pack_eligible": False,
                    "candidate_pack_written": False,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
            )
    return rows


def _negative_control_artifact_status(control_kind: str, artifact_path: Path | None) -> tuple[str, str, str]:
    if artifact_path is None:
        return "blocked", _CONTROL_MISSING_REASONS[control_kind], ""
    path = Path(artifact_path).expanduser().resolve()
    if not path.exists():
        return "blocked", "negative_control_artifact_path_missing", ""
    artifact_sha = _file_sha256(path)
    try:
        manifest = _read_json(path)
    except ValueError:
        return "blocked", "negative_control_artifact_invalid_json", artifact_sha
    validation_reasons = validate_wpr10648_negative_control_manifest(manifest)
    if validation_reasons:
        return "blocked", "|".join(validation_reasons), artifact_sha
    outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    rows_path = outputs.get("wpr10648_negative_control_rows")
    if not rows_path or not Path(str(rows_path)).exists():
        return "blocked", "negative_control_rows_missing", artifact_sha
    rows_path = Path(str(rows_path)).expanduser().resolve()
    expected_rows_sha = str(manifest.get("control_rows_sha256") or "")
    actual_rows_sha = _file_sha256(rows_path)
    if not expected_rows_sha:
        return "blocked", "negative_control_rows_sha256_required", artifact_sha
    if expected_rows_sha != actual_rows_sha:
        return "blocked", "negative_control_rows_sha256_mismatch", artifact_sha
    try:
        control_rows = pd.read_parquet(rows_path)
    except Exception:
        return "blocked", "negative_control_rows_invalid_parquet", artifact_sha
    canonical_kind = _CONTROL_FAMILY_ALIASES.get(control_kind, control_kind)
    if "control_family" not in control_rows.columns:
        return "blocked", "negative_control_rows_family_column_missing", artifact_sha
    matches = control_rows.loc[control_rows["control_family"].astype(str).eq(canonical_kind)].copy()
    if matches.empty:
        return "blocked", f"negative_control_family_missing:{canonical_kind}", artifact_sha
    boundary_reasons = _negative_control_row_boundary_reasons(matches)
    if boundary_reasons:
        return "blocked", "|".join(boundary_reasons), artifact_sha
    if "control_status" in matches.columns and matches["control_status"].astype(str).eq("available").any():
        return "available", "", artifact_sha
    reasons: list[str] = ["first_class_negative_control_artifact_blocked"]
    if "control_reasons" in matches.columns:
        for raw in matches["control_reasons"].fillna("").astype(str).tolist():
            reasons.extend(reason for reason in raw.split("|") if reason)
    return "blocked", "|".join(dict.fromkeys(reasons)), artifact_sha


def _negative_control_row_boundary_reasons(rows: pd.DataFrame) -> list[str]:
    checks = {
        "artifact_family": "negative_control",
        "control_only": True,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "candidate_pack_written": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    reasons: list[str] = []
    for column, expected in checks.items():
        if column not in rows.columns:
            reasons.append(f"negative_control_rows_{column}_missing")
            continue
        values = rows[column]
        if isinstance(expected, bool):
            if not values.map(_bool_matches(expected)).all():
                reasons.append(f"negative_control_rows_{column}_must_be_{str(expected).lower()}")
        elif not values.fillna("").astype(str).eq(str(expected)).all():
            reasons.append(f"negative_control_rows_{column}_must_be_{expected}")
    return reasons


def _bool_matches(expected: bool):
    expected_text = str(expected).lower()

    def _matches(value: Any) -> bool:
        if isinstance(value, bool) or value.__class__.__name__ == "bool_":
            return bool(value) is expected
        return str(value).strip().lower() == expected_text

    return _matches


def _exit_lab_evidence(path: Path | None) -> tuple[Mapping[str, Any] | None, pd.DataFrame | None]:
    if path is None or not Path(path).exists():
        return None, None
    manifest = _read_json(path)
    outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    gates_path = outputs.get("discovery_exit_lab_candidate_gates") or outputs.get("frozen_entry_exit_lab_candidate_gates")
    if not gates_path or not Path(str(gates_path)).exists():
        return manifest, None
    return manifest, pd.read_parquet(Path(str(gates_path)))


def _gate_lookup(gates: pd.DataFrame | None) -> dict[str, Mapping[str, Any]]:
    if gates is None or gates.empty:
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for row in gates.fillna("").to_dict("records"):
        for column in ("entry_candidate_id", "candidate_id"):
            candidate_id = str(row.get(column) or "")
            if candidate_id and candidate_id not in result:
                result[candidate_id] = row
    return result


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _read_optional_frame(path: Path | None) -> pd.DataFrame | None:
    if path is None or not Path(path).exists():
        return None
    return pd.read_parquet(path)


def _status_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {
        str(key): int(value)
        for key, value in frame[column].fillna("").astype(str).value_counts(dropna=False).sort_index().items()
    }


def _safe_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def _exit_lab_columns() -> list[str]:
    return [
        "evidence_scope",
        "symbol",
        "materialized_candidate_id",
        "generated_candidate_id",
        "source_trial_id",
        "source_discovery_candidate_id",
        "source_record_sha256",
        "exit_lab_manifest_path",
        "exit_lab_candidate_gate_found",
        "exit_lab_status",
        "exit_lab_gate_status",
        "exit_lab_reasons",
        "exit_lab_best_family",
        "fixed_holding_score_delta",
        "candidate_pack_written",
        "candidate_pack_eligible",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _window_columns() -> list[str]:
    return [
        "evidence_scope",
        "symbol",
        "window_status",
        "window_reasons",
        "preflight_manifest_path",
        "preflight_manifest_sha256",
        "preflight_rows_path",
        "preflight_rows_sha256",
        "spec_draft_manifest_path",
        "spec_draft_rows_path",
        "modern_window_profile_path",
        "modern_window_profile_sha256",
        "source_trial_count",
        "representable_candidate_count",
        "overlay_cycle_spec_draft_count",
        "cycle_manifest_count",
        "candidate_pack_written",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _negative_control_columns() -> list[str]:
    return [
        "evidence_scope",
        "symbol",
        "materialized_candidate_id",
        "generated_candidate_id",
        "source_trial_id",
        "control_kind",
        "control_status",
        "control_reasons",
        "control_artifact_path",
        "control_artifact_sha256",
        "control_only",
        "candidate_pack_eligible",
        "candidate_pack_written",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _wpr10648_control_columns() -> list[str]:
    return [
        "artifact_family",
        "evidence_scope",
        "symbol",
        "materialized_candidate_id",
        "generated_candidate_id",
        "source_trial_id",
        "source_record_sha256",
        "control_family",
        "control_status",
        "control_reasons",
        "deterministic_seed",
        "source_manifest_path",
        "source_manifest_sha256",
        "source_rows_path",
        "source_rows_sha256",
        "replay_profile_path",
        "replay_profile_sha256",
        "validation_manifest_path",
        "validation_manifest_sha256",
        "modern_window_profile_path",
        "modern_window_profile_sha256",
        "exact_replay_lineage_sha256",
        "source_label_hash",
        "shuffled_label_hash",
        "label_distribution_match",
        "derangement_rate",
        "shift_size",
        "edge_row_drop_count",
        "shifted_context_source_hash",
        "shifted_context_output_hash",
        "monotonic_timestamp_validation",
        "overlay_used",
        "knn_artifact_input",
        "regime_model_backend",
        "hmm_artifact_dependency",
        "control_only",
        "candidate_evidence",
        "candidate_pack_eligible",
        "candidate_pack_written",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    payload = {
        "columns": list(frame.columns),
        "rows": frame.fillna("").to_dict("records"),
    }
    return sha256(json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            return str(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _assert_new_artifact_paths(*paths: Path) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise ValueError("refusing to overwrite existing WPR106-47 replay evidence artifacts: " + ",".join(existing))


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        frame.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
