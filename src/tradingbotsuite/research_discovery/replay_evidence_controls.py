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
NEGATIVE_CONTROL_KINDS = (
    "shuffled_labels",
    "shifted_context",
    "no_knn_baseline",
    "no_regime_baseline",
)
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
    for lead in preflight.fillna("").to_dict("records"):
        for control_kind in NEGATIVE_CONTROL_KINDS:
            artifact_path = control_artifact_paths.get(control_kind)
            artifact_exists = artifact_path is not None and Path(artifact_path).exists()
            rows.append(
                {
                    "evidence_scope": "negative_control_and_leakage_stress",
                    "symbol": symbol,
                    "materialized_candidate_id": str(lead.get("materialized_candidate_id") or ""),
                    "generated_candidate_id": str(lead.get("generated_candidate_id") or ""),
                    "source_trial_id": str(lead.get("source_trial_id") or ""),
                    "control_kind": control_kind,
                    "control_status": "available" if artifact_exists else "blocked",
                    "control_reasons": "" if artifact_exists else _CONTROL_MISSING_REASONS[control_kind],
                    "control_artifact_path": str(Path(artifact_path).resolve()) if artifact_path is not None else "",
                    "control_artifact_sha256": _file_sha256(artifact_path) if artifact_exists else "",
                    "control_only": True,
                    "candidate_pack_eligible": False,
                    "candidate_pack_written": False,
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
            )
    return rows


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
