from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_artifacts.candidate_pack import evaluate_research_candidate_gate
from tradingbotsuite.research_discovery.manifests import DISCOVERY_RUN_MANIFEST_VERSION
from tradingbotsuite.research_discovery.snapshots import atomic_write_json
from tradingbotsuite.research_discovery.state import read_trial_record


DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION = "discovery-candidate-pack-bridge-v1"
DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION = "discovery-candidate-pack-eligibility-v1"

LIVE_ADJACENT_VERSION_FIELDS = frozenset(
    {
        "promotion_candidate_manifest_version",
        "paper_run_manifest_version",
        "shadow_run_archive_manifest_version",
        "testnet_validation_manifest_version",
        "live_run_manifest_version",
    }
)


@dataclass(frozen=True, slots=True)
class DiscoveryCandidatePackBridgeResult:
    discovery_manifest_path: Path
    cycle_manifest_path: Path | None
    manifest: Mapping[str, Any]
    eligibility: pd.DataFrame
    rejections_markdown: str


@dataclass(frozen=True, slots=True)
class DiscoveryCandidatePackBridgeArtifactResult:
    output_dir: Path
    manifest_path: Path
    eligibility_path: Path
    rejections_path: Path


def evaluate_discovery_candidate_pack_eligibility(
    *,
    discovery_manifest_path: Path,
    cycle_manifest_path: Path | None = None,
    candidate_id_map: Mapping[str, str] | None = None,
) -> DiscoveryCandidatePackBridgeResult:
    discovery_manifest_path = Path(discovery_manifest_path).expanduser().resolve()
    cycle_manifest_resolved = Path(cycle_manifest_path).expanduser().resolve() if cycle_manifest_path is not None else None
    candidate_map = {str(key): str(value) for key, value in dict(candidate_id_map or {}).items()}
    manifest = _read_json(discovery_manifest_path)
    global_reasons = _discovery_manifest_reasons(manifest, discovery_manifest_path)
    required_outputs = manifest.get("required_outputs") if isinstance(manifest.get("required_outputs"), Mapping) else {}
    state_payload = _read_required_json(required_outputs.get("run_state"), global_reasons, "run_state")
    if state_payload is not None:
        global_reasons.extend(_run_state_reasons(state_payload, required_outputs, manifest))
    interesting = _read_required_frame(required_outputs.get("interesting_candidates"), global_reasons, "interesting_candidates")
    blocked = _read_required_frame(required_outputs.get("blocked_candidates"), global_reasons, "blocked_candidates")
    filter_blockers = _read_required_frame(required_outputs.get("filter_blockers"), global_reasons, "filter_blockers")

    rows: list[dict[str, Any]] = []
    if interesting is not None and not interesting.empty:
        blocked_ids = _candidate_ids(blocked)
        filter_blocked_ids = _candidate_ids(filter_blockers)
        for record in interesting.to_dict("records"):
            discovery_candidate_id = str(record.get("candidate_id") or "")
            research_candidate_id = candidate_map.get(discovery_candidate_id, discovery_candidate_id)
            reasons = list(global_reasons)
            if not discovery_candidate_id:
                reasons.append("discovery_candidate_id_required")
            if discovery_candidate_id in blocked_ids:
                reasons.append("candidate_present_in_blocked_candidates")
            if discovery_candidate_id in filter_blocked_ids:
                reasons.append("candidate_present_in_filter_blockers")
            gate_status = "not_evaluated"
            gate_reasons: tuple[str, ...] = ()
            if cycle_manifest_resolved is None:
                reasons.append("historical_cycle_manifest_required")
            elif not cycle_manifest_resolved.exists():
                reasons.append("historical_cycle_manifest_missing")
            else:
                gate = evaluate_research_candidate_gate(
                    cycle_manifest_path=cycle_manifest_resolved,
                    candidate_id=research_candidate_id,
                )
                gate_status = gate.status
                gate_reasons = gate.reasons
                if not gate.passed:
                    reasons.extend(f"research_candidate_gate:{reason}" for reason in gate.reasons)
            reasons = list(dict.fromkeys(reasons))
            rows.append(
                {
                    "discovery_candidate_id": discovery_candidate_id,
                    "research_candidate_id": research_candidate_id,
                    "eligible_for_existing_candidate_pack_validator": bool(not reasons),
                    "bridge_status": "eligible" if not reasons else "blocked",
                    "bridge_reasons": "|".join(reasons),
                    "research_candidate_gate_status": gate_status,
                    "research_candidate_gate_reasons": "|".join(gate_reasons),
                    "discovery_run_id": str(manifest.get("run_id") or ""),
                    "cycle_manifest_path": str(cycle_manifest_resolved) if cycle_manifest_resolved is not None else "",
                    "candidate_pack_written": False,
                    "candidate_pack_paths": "",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                }
            )
    eligibility = pd.DataFrame(rows, columns=_eligibility_columns())
    summary = _summary(eligibility, global_reasons)
    bridge_manifest = {
        "discovery_candidate_pack_bridge_version": DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "bridge_scope": "discovery_to_existing_research_candidate_pack_validator_eligibility_only",
        "claim_scope": "audit_only_no_pack_write_no_live_or_promotion_claim",
        "source_discovery_manifest_path": str(discovery_manifest_path),
        "source_discovery_manifest_sha256": _file_sha256(discovery_manifest_path) if discovery_manifest_path.exists() else None,
        "source_cycle_manifest_path": str(cycle_manifest_resolved) if cycle_manifest_resolved is not None else None,
        "source_cycle_manifest_sha256": (
            _file_sha256(cycle_manifest_resolved)
            if cycle_manifest_resolved is not None and cycle_manifest_resolved.exists()
            else None
        ),
        "candidate_id_map": candidate_map,
        "summary": summary,
        "global_reasons": list(dict.fromkeys(global_reasons)),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
        "required_outputs": {},
    }
    validation_reasons = validate_discovery_candidate_pack_bridge_manifest(bridge_manifest)
    if validation_reasons:
        raise ValueError("invalid discovery candidate pack bridge manifest: " + "|".join(validation_reasons))
    return DiscoveryCandidatePackBridgeResult(
        discovery_manifest_path=discovery_manifest_path,
        cycle_manifest_path=cycle_manifest_resolved,
        manifest=bridge_manifest,
        eligibility=eligibility,
        rejections_markdown=_rejections_markdown(eligibility, global_reasons),
    )


def write_discovery_candidate_pack_eligibility(
    *,
    output_dir: Path,
    result: DiscoveryCandidatePackBridgeResult,
) -> DiscoveryCandidatePackBridgeArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "candidate_pack_eligibility_manifest.json"
    eligibility_path = output_dir / "candidate_pack_eligibility.parquet"
    rejections_path = output_dir / "candidate_pack_bridge_rejections.md"
    result.eligibility.to_parquet(eligibility_path, index=False)
    rejections_path.write_text(result.rejections_markdown, encoding="utf-8")
    manifest = dict(result.manifest)
    manifest["eligibility_artifact_version"] = DISCOVERY_CANDIDATE_PACK_ELIGIBILITY_VERSION
    manifest["required_outputs"] = {
        "candidate_pack_eligibility_manifest": str(manifest_path),
        "candidate_pack_eligibility": str(eligibility_path),
        "candidate_pack_bridge_rejections": str(rejections_path),
    }
    manifest["candidate_pack_eligibility_sha256"] = _file_sha256(eligibility_path)
    manifest["candidate_pack_bridge_rejections_sha256"] = _file_sha256(rejections_path)
    validation_reasons = validate_discovery_candidate_pack_bridge_manifest(manifest)
    if validation_reasons:
        raise ValueError("invalid discovery candidate pack bridge manifest: " + "|".join(validation_reasons))
    atomic_write_json(manifest_path, manifest)
    return DiscoveryCandidatePackBridgeArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        eligibility_path=eligibility_path,
        rejections_path=rejections_path,
    )


def validate_discovery_candidate_pack_bridge_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("discovery_candidate_pack_bridge_version") != DISCOVERY_CANDIDATE_PACK_BRIDGE_VERSION:
        reasons.append("discovery_candidate_pack_bridge_version_required")
    if manifest.get("research_only") is not True:
        reasons.append("research_only_must_be_true")
    if manifest.get("observe_only") is not True:
        reasons.append("observe_only_must_be_true")
    if manifest.get("promotion_ready") is not False:
        reasons.append("promotion_ready_must_be_false")
    for field in (
        "live_signal_input",
        "position_sizing_input",
        "operator_control_input",
        "live_execution_input",
        "runtime_control_input",
        "live_fetch_used",
        "order_placement_used",
        "runtime_mode_changed",
    ):
        if manifest.get(field) is not False:
            reasons.append(f"{field}_must_be_false")
    if manifest.get("candidate_pack_written") is not False:
        reasons.append("candidate_pack_written_must_be_false")
    if list(manifest.get("candidate_pack_paths") or []) != []:
        reasons.append("candidate_pack_paths_must_be_empty")
    if any(field in manifest for field in LIVE_ADJACENT_VERSION_FIELDS):
        reasons.append("live_or_promotion_manifest_version_forbidden")
    return reasons


def _discovery_manifest_reasons(manifest: Mapping[str, Any], path: Path) -> list[str]:
    reasons: list[str] = []
    if manifest.get("discovery_run_manifest_version") != DISCOVERY_RUN_MANIFEST_VERSION:
        reasons.append("discovery_run_manifest_version_required")
    reasons.extend(_research_boundary_reasons(manifest, "discovery_manifest"))
    if manifest.get("candidate_pack_written") is not False:
        reasons.append("discovery_manifest_candidate_pack_written_must_be_false")
    if list(manifest.get("candidate_pack_paths") or []) != []:
        reasons.append("discovery_manifest_candidate_pack_paths_must_be_empty")
    if not path.exists():
        reasons.append("discovery_manifest_missing")
    required_outputs = manifest.get("required_outputs")
    if not isinstance(required_outputs, Mapping):
        reasons.append("discovery_manifest_required_outputs_required")
    return reasons


def _run_state_reasons(
    state_payload: Mapping[str, Any],
    required_outputs: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(_research_boundary_reasons(state_payload, "run_state"))
    if state_payload.get("status") != "completed":
        reasons.append("discovery_run_state_must_be_completed")
    if str(state_payload.get("run_id") or "") != str(manifest.get("run_id") or ""):
        reasons.append("discovery_run_state_run_id_mismatch")
    trials_dir_raw = required_outputs.get("trials")
    if not trials_dir_raw:
        reasons.append("discovery_trials_dir_required")
        return reasons
    trials_dir = Path(str(trials_dir_raw))
    if not trials_dir.exists():
        reasons.append("discovery_trials_dir_missing")
        return reasons
    completed_ids = [str(item) for item in state_payload.get("completed_trial_ids") or []]
    hashes = dict(state_payload.get("completed_trial_hashes") or {})
    for trial_id in completed_ids:
        trial_path = trials_dir / f"{trial_id}.json"
        if not trial_path.exists():
            reasons.append(f"discovery_trial_record_missing:{trial_id}")
            continue
        try:
            record = read_trial_record(trial_path)
        except ValueError:
            reasons.append(f"discovery_trial_record_hash_mismatch:{trial_id}")
            continue
        expected_hash = str(hashes.get(trial_id) or "")
        actual_hash = str(record.to_payload().get("record_sha256") or "")
        if not expected_hash:
            reasons.append(f"discovery_trial_state_hash_required:{trial_id}")
        elif expected_hash != actual_hash:
            reasons.append(f"discovery_trial_state_hash_mismatch:{trial_id}")
        if record.status != "completed":
            reasons.append(f"discovery_trial_status_not_completed:{trial_id}")
    return reasons


def _read_required_json(raw_path: Any, reasons: list[str], name: str) -> dict[str, Any] | None:
    if not raw_path:
        reasons.append(f"{name}_path_required")
        return None
    path = Path(str(raw_path))
    if not path.exists():
        reasons.append(f"{name}_path_missing")
        return None
    try:
        payload = _read_json(path)
    except ValueError:
        reasons.append(f"{name}_invalid_json")
        return None
    return payload


def _read_required_frame(raw_path: Any, reasons: list[str], name: str) -> pd.DataFrame | None:
    if not raw_path:
        reasons.append(f"{name}_path_required")
        return None
    path = Path(str(raw_path))
    if not path.exists():
        reasons.append(f"{name}_path_missing")
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        reasons.append(f"{name}_invalid_parquet")
        return None


def _research_boundary_reasons(payload: Mapping[str, Any], prefix: str) -> list[str]:
    reasons: list[str] = []
    if any(field in payload for field in LIVE_ADJACENT_VERSION_FIELDS):
        reasons.append(f"{prefix}_live_or_promotion_manifest_version_forbidden")
    if payload.get("research_only") is not True:
        reasons.append(f"{prefix}_research_only_required")
    if payload.get("observe_only") is not True:
        reasons.append(f"{prefix}_observe_only_required")
    if payload.get("promotion_ready") is not False:
        reasons.append(f"{prefix}_promotion_ready_must_be_false")
    for field in (
        "live_signal_input",
        "position_sizing_input",
        "operator_control_input",
        "live_execution_input",
        "runtime_control_input",
        "live_fetch_used",
        "order_placement_used",
        "runtime_mode_changed",
    ):
        if field in payload and payload.get(field) is not False:
            reasons.append(f"{prefix}_{field}_must_be_false")
    return reasons


def _candidate_ids(frame: pd.DataFrame | None) -> set[str]:
    if frame is None or frame.empty or "candidate_id" not in frame.columns:
        return set()
    return {str(value) for value in frame["candidate_id"].dropna().tolist() if str(value)}


def _summary(eligibility: pd.DataFrame, global_reasons: list[str]) -> dict[str, Any]:
    eligible_count = int(eligibility["eligible_for_existing_candidate_pack_validator"].sum()) if not eligibility.empty else 0
    blocked_count = int(len(eligibility) - eligible_count)
    return {
        "candidate_count": int(len(eligibility)),
        "eligible_count": eligible_count,
        "blocked_count": blocked_count,
        "global_reason_count": int(len(dict.fromkeys(global_reasons))),
        "candidate_pack_written": False,
        "promotion_ready": False,
    }


def _rejections_markdown(eligibility: pd.DataFrame, global_reasons: list[str]) -> str:
    lines = [
        "# Discovery Candidate Pack Bridge Rejections",
        "",
        "Research-only eligibility report. No candidate packs are written by this bridge.",
        "",
    ]
    if global_reasons:
        lines.extend(["## Global Reasons", ""])
        lines.extend(f"- {reason}" for reason in dict.fromkeys(global_reasons))
        lines.append("")
    blocked = eligibility.loc[~eligibility["eligible_for_existing_candidate_pack_validator"]] if not eligibility.empty else eligibility
    lines.extend(["## Blocked Candidates", ""])
    if blocked.empty:
        lines.append("- None")
    else:
        for row in blocked.to_dict("records"):
            reasons = str(row.get("bridge_reasons") or "blocked").replace("|", ", ")
            lines.append(f"- {row.get('discovery_candidate_id')} -> {row.get('research_candidate_id')}: {reasons}")
    lines.append("")
    return "\n".join(lines)


def _eligibility_columns() -> list[str]:
    return [
        "discovery_candidate_id",
        "research_candidate_id",
        "eligible_for_existing_candidate_pack_validator",
        "bridge_status",
        "bridge_reasons",
        "research_candidate_gate_status",
        "research_candidate_gate_reasons",
        "discovery_run_id",
        "cycle_manifest_path",
        "candidate_pack_written",
        "candidate_pack_paths",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
