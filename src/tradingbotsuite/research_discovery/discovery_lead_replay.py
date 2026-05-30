from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.data.historical_data_catalog import normalize_operator_run_artifact_paths
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.manifests import DISCOVERY_RUN_MANIFEST_VERSION
from tradingbotsuite.research_discovery.snapshots import atomic_write_json
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec
from tradingbotsuite.research_discovery.state import read_trial_record


DISCOVERY_LEAD_REPLAY_SPEC_VERSION = "discovery-lead-replay-spec-v1"
DISCOVERY_REPLAY_ENTRY_SIGNAL_MANIFEST_VERSION = "discovery-replay-entry-signal-manifest-v1"
DISCOVERY_REPLAY_ENTRY_SIGNAL_VERSION = "discovery-replay-entry-signal-v1"


@dataclass(frozen=True, slots=True)
class DiscoveryLeadReplaySpecResult:
    spec_payload: dict[str, Any]
    source_materialization_manifest: Mapping[str, Any]
    materialized_leads: pd.DataFrame


@dataclass(frozen=True, slots=True)
class DiscoveryLeadReplaySpecArtifactResult:
    spec_path: Path
    spec_payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DiscoveryReplayEntrySignalResult:
    manifest: dict[str, Any]
    signals: pd.DataFrame


@dataclass(frozen=True, slots=True)
class DiscoveryReplayEntrySignalArtifactResult:
    output_dir: Path
    manifest_path: Path
    signals_path: Path


def build_discovery_lead_replay_spec(
    *,
    materialization_manifest_path: str | Path,
    run_id: str,
    output_dir: str | Path,
    research_output_dir: str | Path | None = None,
    max_candidates: int | None = None,
) -> DiscoveryLeadReplaySpecResult:
    """Build an explicit discovery replay spec from WPR106-30 materialized leads."""

    materialization_path = Path(materialization_manifest_path).expanduser().resolve()
    materialization_manifest = _read_json_normalized(materialization_path)
    required_outputs = _required_outputs(materialization_manifest)
    materialized_leads_path = _required_existing_path(required_outputs, "materialized_discovery_leads")
    materialized = pd.read_parquet(materialized_leads_path)
    if max_candidates is not None:
        materialized = materialized.head(max(0, int(max_candidates))).copy()
    if materialized.empty:
        raise ValueError("materialized discovery leads are empty")

    source_discovery_manifest_path = _required_existing_path(
        {"source_discovery_manifest_path": materialization_manifest.get("source_discovery_manifest_path")},
        "source_discovery_manifest_path",
    )
    source_discovery_manifest = _read_json_normalized(source_discovery_manifest_path)
    source_outputs = _required_outputs(source_discovery_manifest)
    source_resolved_spec_path = _required_existing_path(source_outputs, "discovery_spec_resolved")
    source_resolved_spec = _read_json_normalized(source_resolved_spec_path)
    source_trials_dir = _required_existing_path(
        {"source_trials_dir": materialization_manifest.get("source_trials_dir")},
        "source_trials_dir",
    )
    if not source_trials_dir.is_dir():
        raise ValueError(f"source discovery trials path is not a directory: {source_trials_dir}")

    templates = [
        _replay_template_from_row(
            row,
            source_trials_dir=source_trials_dir,
        )
        for row in materialized.to_dict("records")
    ]
    materialized_feature_column_set_ids = tuple(
        sorted(
            {
                str(row.get("feature_column_set_id") or "")
                for row in materialized.to_dict("records")
                if str(row.get("feature_column_set_id") or "").strip()
            }
        )
    )
    source_feature_column_set_ids = tuple(
        str(item)
        for item in source_resolved_spec.get("feature_column_set_ids") or ()
        if str(item).strip()
    )
    feature_column_set_ids = _ordered_unique((*source_feature_column_set_ids, *materialized_feature_column_set_ids))
    output_path = Path(output_dir).expanduser().resolve()
    research_root = (
        Path(research_output_dir).expanduser().resolve()
        if research_output_dir is not None
        else (Path.cwd() / "data" / "research").resolve()
    )
    spec_payload = {
        **dict(source_resolved_spec),
        "spec_version": DISCOVERY_LEAD_REPLAY_SPEC_VERSION,
        "run_id": str(run_id),
        "symbol": str(materialization_manifest.get("source_symbol") or source_discovery_manifest.get("symbol") or "").upper(),
        "timeframe": str(materialization_manifest.get("source_timeframe") or source_discovery_manifest.get("timeframe") or ""),
        "research_output_dir": str(research_root),
        "output_dir": str(output_path),
        "feature_column_set_ids": list(feature_column_set_ids or source_resolved_spec.get("feature_column_set_ids") or ()),
        "budget": {
            **dict(source_resolved_spec.get("budget") or {}),
            "max_trials": int(len(templates)),
            "trial_batch_size": int(max(1, len(templates))),
        },
        "execution": {
            "max_workers": 1,
            "executor": "thread",
            "persist_trial_artifacts": "predictions_only",
        },
        "trial_templates": templates,
        "replay_metadata": {
            "replay_spec_version": DISCOVERY_LEAD_REPLAY_SPEC_VERSION,
            "source_materialization_manifest_path": str(materialization_path),
            "source_materialization_manifest_sha256": _file_sha256(materialization_path),
            "source_discovery_manifest_path": str(source_discovery_manifest_path),
            "source_discovery_manifest_sha256": _file_sha256(source_discovery_manifest_path),
            "materialized_leads_path": str(materialized_leads_path),
            "materialized_leads_sha256": _file_sha256(materialized_leads_path),
            "materialized_candidate_count": int(len(materialized)),
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "candidate_pack_written": False,
        },
    }
    # Validate with the active contract before writing the spec.
    DiscoveryRunSpec.from_payload(spec_payload, spec_path=Path("discovery_lead_replay_spec.json"))
    return DiscoveryLeadReplaySpecResult(
        spec_payload=_json_safe(spec_payload),
        source_materialization_manifest=materialization_manifest,
        materialized_leads=materialized,
    )


def write_discovery_lead_replay_spec(
    spec_path: str | Path,
    result: DiscoveryLeadReplaySpecResult,
) -> DiscoveryLeadReplaySpecArtifactResult:
    spec_path = Path(spec_path).expanduser().resolve()
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(spec_path, _json_safe(result.spec_payload))
    return DiscoveryLeadReplaySpecArtifactResult(spec_path=spec_path, spec_payload=result.spec_payload)


def aggregate_discovery_replay_entry_signals(
    *,
    replay_discovery_manifest_path: str | Path,
) -> DiscoveryReplayEntrySignalResult:
    replay_manifest_path = Path(replay_discovery_manifest_path).expanduser().resolve()
    replay_manifest = _read_json_normalized(replay_manifest_path)
    if replay_manifest.get("discovery_run_manifest_version") != DISCOVERY_RUN_MANIFEST_VERSION:
        raise ValueError("replay discovery manifest version required")
    outputs = _required_outputs(replay_manifest)
    interesting_path = _required_existing_path(outputs, "interesting_candidates")
    trials_dir = _required_existing_path(outputs, "trials")
    interesting = pd.read_parquet(interesting_path)
    signal_frames: list[pd.DataFrame] = []
    candidates_with_signals: set[str] = set()
    missing_accounting = 0
    empty_signal_files = 0
    malformed_signal_files = 0
    for record in interesting.to_dict("records"):
        trial_id = str(record.get("trial_id") or "")
        trial_path = trials_dir / f"{trial_id}.json"
        if not trial_path.exists():
            missing_accounting += 1
            continue
        trial = read_trial_record(trial_path)
        trial_payload = trial.to_payload()
        record_sha = str(trial_payload.get("record_sha256") or "")
        inner = trial_payload.get("payload") if isinstance(trial_payload.get("payload"), Mapping) else {}
        accounting_manifest_path = inner.get("strategy_accounting_manifest_path")
        if not accounting_manifest_path:
            missing_accounting += 1
            continue
        accounting_manifest = _read_json_normalized(Path(str(accounting_manifest_path)))
        accounting_outputs = _required_outputs(accounting_manifest)
        signals_path = _required_existing_path(accounting_outputs, "strategy_signals")
        try:
            signals = pd.read_parquet(signals_path)
        except Exception:
            malformed_signal_files += 1
            continue
        if signals.empty:
            empty_signal_files += 1
            continue
        annotated = _annotated_entry_signals(
            signals,
            trial_payload=trial_payload,
            record_sha256=record_sha,
        )
        if annotated.empty:
            empty_signal_files += 1
            continue
        candidates_with_signals.add(str(trial.candidate_id))
        signal_frames.append(annotated)

    combined = (
        pd.concat(signal_frames, ignore_index=True)
        if signal_frames
        else pd.DataFrame(columns=_entry_signal_columns())
    )
    manifest = {
        "discovery_replay_entry_signal_manifest_version": DISCOVERY_REPLAY_ENTRY_SIGNAL_MANIFEST_VERSION,
        "discovery_replay_entry_signal_version": DISCOVERY_REPLAY_ENTRY_SIGNAL_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_replay_discovery_manifest_path": str(replay_manifest_path),
        "source_replay_discovery_manifest_sha256": _file_sha256(replay_manifest_path),
        "source_interesting_candidates_path": str(interesting_path),
        "source_interesting_candidates_sha256": _file_sha256(interesting_path),
        "source_trials_dir": str(trials_dir),
        "symbol": replay_manifest.get("symbol"),
        "timeframe": replay_manifest.get("timeframe"),
        "selected_lead_count": int(len(interesting)),
        "entry_signal_row_count": int(len(combined)),
        "candidate_with_signal_count": int(len(candidates_with_signals)),
        "missing_strategy_accounting_count": int(missing_accounting),
        "empty_strategy_signal_file_count": int(empty_signal_files),
        "malformed_strategy_signal_file_count": int(malformed_signal_files),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "claim_scope": "replayed_entry_signals_only_not_cycle_rankings_not_candidate_pack_evidence",
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    manifest["entry_signal_frame_sha256"] = _frame_hash(combined)
    return DiscoveryReplayEntrySignalResult(manifest=manifest, signals=combined)


def write_discovery_replay_entry_signal_artifacts(
    output_dir: str | Path,
    result: DiscoveryReplayEntrySignalResult,
) -> DiscoveryReplayEntrySignalArtifactResult:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    signals_path = output / "discovery_replay_entry_signals.parquet"
    manifest_path = output / "discovery_replay_entry_signal_manifest.json"
    result.signals.to_parquet(signals_path, index=False)
    manifest = dict(result.manifest)
    manifest["required_outputs"] = {
        "discovery_replay_entry_signal_manifest": str(manifest_path),
        "discovery_replay_entry_signals": str(signals_path),
    }
    manifest["discovery_replay_entry_signals_sha256"] = _file_sha256(signals_path)
    reasons = validate_discovery_replay_entry_signal_manifest(manifest)
    if reasons:
        raise ValueError("invalid discovery replay entry signal manifest: " + "|".join(reasons))
    atomic_write_json(manifest_path, _json_safe(manifest))
    return DiscoveryReplayEntrySignalArtifactResult(
        output_dir=output,
        manifest_path=manifest_path,
        signals_path=signals_path,
    )


def validate_discovery_replay_entry_signal_manifest(manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if manifest.get("discovery_replay_entry_signal_manifest_version") != DISCOVERY_REPLAY_ENTRY_SIGNAL_MANIFEST_VERSION:
        reasons.append("discovery_replay_entry_signal_manifest_version_required")
    if manifest.get("discovery_replay_entry_signal_version") != DISCOVERY_REPLAY_ENTRY_SIGNAL_VERSION:
        reasons.append("discovery_replay_entry_signal_version_required")
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
    for key in ("discovery_replay_entry_signal_manifest", "discovery_replay_entry_signals"):
        if key not in outputs:
            reasons.append(f"required_output_missing:{key}")
    return reasons


def _replay_template_from_row(
    row: Mapping[str, Any],
    *,
    source_trials_dir: Path,
) -> dict[str, Any]:
    source_trial_id = str(row.get("source_trial_id") or "")
    source_record_sha = str(row.get("source_record_sha256") or "")
    trial = read_trial_record(source_trials_dir / f"{source_trial_id}.json")
    trial_payload = trial.to_payload()
    actual_sha = str(trial_payload.get("record_sha256") or "")
    if source_record_sha and actual_sha != source_record_sha:
        raise ValueError(f"source trial record hash mismatch: {source_trial_id}")
    inner = trial_payload.get("payload") if isinstance(trial_payload.get("payload"), Mapping) else {}
    payload = {
        **dict(inner),
        "trial_kind": str(inner.get("trial_kind") or "regime_knn_entry_discovery"),
        "source_discovery_run_id": str(row.get("source_run_id") or trial_payload.get("run_id") or ""),
        "source_trial_id": source_trial_id,
        "source_discovery_candidate_id": str(row.get("source_discovery_candidate_id") or trial_payload.get("candidate_id") or ""),
        "source_record_sha256": source_record_sha,
        "source_prediction_signature_hash": str(row.get("prediction_signature_hash") or ""),
        "source_entry_event_signature_hash": str(row.get("entry_event_signature_hash") or ""),
        "source_effective_trial_key": str(row.get("effective_trial_key") or ""),
        "materialized_candidate_id": str(row.get("materialized_candidate_id") or ""),
        "materialized_candidate_family": str(row.get("materialized_candidate_family") or ""),
        "replay_spec_version": DISCOVERY_LEAD_REPLAY_SPEC_VERSION,
    }
    return {
        "trial_id": source_trial_id,
        "candidate_id": str(row.get("materialized_candidate_id") or trial_payload.get("candidate_id") or ""),
        "ledger_kind": "blocked",
        "candidate_family": str(row.get("source_candidate_family") or trial_payload.get("candidate_family") or "regime_knn_entry_discovery"),
        "score": float(row.get("final_score") or row.get("discovery_screen_score_v2") or 0.0),
        "blocker_code": "not_evaluated",
        "filter_blocker_code": "",
        "payload": _json_safe(payload),
    }


def _annotated_entry_signals(
    signals: pd.DataFrame,
    *,
    trial_payload: Mapping[str, Any],
    record_sha256: str,
) -> pd.DataFrame:
    frame = signals.copy()
    inner = trial_payload.get("payload") if isinstance(trial_payload.get("payload"), Mapping) else {}
    if "decision_time_ms" not in frame.columns:
        if "signal_time_ms" in frame.columns:
            frame["decision_time_ms"] = pd.to_numeric(frame["signal_time_ms"], errors="coerce")
        elif "bar_time_ms" in frame.columns:
            frame["decision_time_ms"] = pd.to_numeric(frame["bar_time_ms"], errors="coerce")
    if "signal_bar_time_ms" not in frame.columns and "decision_time_ms" in frame.columns:
        frame["signal_bar_time_ms"] = frame["decision_time_ms"]
    frame["candidate_id"] = str(trial_payload.get("candidate_id") or "")
    frame["trial_id"] = str(trial_payload.get("trial_id") or "")
    frame["record_sha256"] = str(record_sha256)
    frame["source_record_sha256"] = str(inner.get("source_record_sha256") or "")
    frame["source_discovery_candidate_id"] = str(inner.get("source_discovery_candidate_id") or "")
    frame["materialized_candidate_id"] = str(inner.get("materialized_candidate_id") or trial_payload.get("candidate_id") or "")
    frame["source_trial_id"] = str(inner.get("source_trial_id") or trial_payload.get("trial_id") or "")
    frame["research_only"] = True
    frame["observe_only"] = True
    frame["promotion_ready"] = False
    if "decision_time_ms" in frame.columns:
        frame = frame.loc[pd.to_numeric(frame["decision_time_ms"], errors="coerce").notna()].copy()
        frame["decision_time_ms"] = pd.to_numeric(frame["decision_time_ms"], errors="coerce").astype("int64")
    return frame.reindex(columns=_entry_signal_columns() + [column for column in frame.columns if column not in _entry_signal_columns()])


def _entry_signal_columns() -> list[str]:
    return [
        "candidate_id",
        "trial_id",
        "record_sha256",
        "source_record_sha256",
        "source_discovery_candidate_id",
        "materialized_candidate_id",
        "source_trial_id",
        "decision_time_ms",
        "signal_bar_time_ms",
        "signal_id",
        "signal_time_ms",
        "symbol",
        "side",
        "strength",
        "confidence",
        "signal_bar_close",
        "strategy_id",
        "feature_set_id",
        "skip_reason",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _ordered_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


def _read_json_normalized(path: Path) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    payload = _read_json_raw(resolved)
    return normalize_operator_run_artifact_paths(payload, artifact_path=resolved, anchor_root=resolved.parent)


def _read_json_raw(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"JSON object required: {path}")
    return dict(payload)


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


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    if pd.isna(value) if not isinstance(value, (str, bytes, bytearray, list, tuple, dict)) else False:
        return None
    return value


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    payload = frame.to_json(orient="table", index=False, date_format="iso")
    return sha256(payload.encode("utf-8")).hexdigest()
