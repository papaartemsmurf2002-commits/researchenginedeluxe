from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


TELEMETRY_VERSION = "discovery-compute-telemetry-v1"


@dataclass(frozen=True, slots=True)
class TelemetrySession:
    wall_started: float
    process_started: float
    tracing_started_here: bool


def start_telemetry_session() -> TelemetrySession:
    tracing_started_here = False
    if not tracemalloc.is_tracing():
        tracemalloc.start()
        tracing_started_here = True
    return TelemetrySession(
        wall_started=time.perf_counter(),
        process_started=time.process_time(),
        tracing_started_here=tracing_started_here,
    )


def build_compute_telemetry(
    *,
    session: TelemetrySession,
    output_dir: Path,
    completed_records: Iterable[Any],
    active_workers: int,
    executed_this_call: int,
    artifact_write_seconds: float,
    feature_cache_summary: Mapping[str, Any] | None = None,
    neighbor_cache_summary: Mapping[str, Any] | None = None,
    stage_wall_seconds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    wall_seconds = max(0.0, time.perf_counter() - session.wall_started)
    process_cpu_seconds = max(0.0, time.process_time() - session.process_started)
    current_bytes, peak_bytes = tracemalloc.get_traced_memory() if tracemalloc.is_tracing() else (0, 0)
    records = list(completed_records)
    payload = {
        "telemetry_version": TELEMETRY_VERSION,
        "wall_time_seconds": float(wall_seconds),
        "process_cpu_seconds": float(process_cpu_seconds),
        "process_cpu_percent_single_core": float((process_cpu_seconds / wall_seconds) * 100.0) if wall_seconds > 0 else None,
        "process_cpu_percent": float((process_cpu_seconds / wall_seconds) * 100.0) if wall_seconds > 0 else None,
        "python_tracemalloc_current_bytes": int(current_bytes),
        "python_tracemalloc_peak_bytes": int(peak_bytes),
        "memory_peak_bytes": int(peak_bytes),
        "memory_peak_available": bool(tracemalloc.is_tracing()),
        "active_workers": int(active_workers),
        "executed_trials_this_call": int(executed_this_call),
        "trials_per_minute": float(executed_this_call / max(wall_seconds / 60.0, 1e-12)),
        "wall_time_seconds_by_stage": {
            str(key): float(max(0.0, value))
            for key, value in sorted(dict(stage_wall_seconds or {}).items())
        },
        "cache_hit_rates": {
            "feature_materialization": _feature_cache_hit_rate(feature_cache_summary),
            "label_split": _bool_payload_hit_rate(records, "label_split_cache_hit"),
            "gmm_regime": _bool_payload_hit_rate(records, "hmm_cache_hit"),
            "neighbor": _neighbor_hit_rate(neighbor_cache_summary, records),
        },
        "cache_counts": {
            "feature_materialization": dict(feature_cache_summary or {}),
            "neighbor": dict(neighbor_cache_summary or {"enabled": False}),
            "label_split": _bool_payload_counts(records, "label_split_cache_hit"),
            "gmm_regime": _bool_payload_counts(records, "hmm_cache_hit"),
        },
        "artifact_write_time_seconds_observed": float(max(0.0, artifact_write_seconds)),
        "artifact_write_time_scope": "runner_state_ledgers_snapshots_trials_and_manifests",
        "artifact_file_count": 0,
        "artifact_bytes_written": 0,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    artifact_counts = _artifact_counts(output_dir)
    payload.update(artifact_counts)
    return payload


def stop_telemetry_session(session: TelemetrySession) -> None:
    if session.tracing_started_here and tracemalloc.is_tracing():
        tracemalloc.stop()


def _bool_payload_counts(records: list[Any], field: str) -> dict[str, int]:
    observed = [record for record in records if field in getattr(record, "payload", {})]
    hits = sum(1 for record in observed if bool(getattr(record, "payload", {}).get(field)))
    total = len(observed)
    return {"observed": int(total), "hits": int(hits), "misses": int(max(0, total - hits))}


def _bool_payload_hit_rate(records: list[Any], field: str) -> float | None:
    counts = _bool_payload_counts(records, field)
    if counts["observed"] == 0:
        return None
    return float(counts["hits"] / counts["observed"])


def _feature_cache_hit_rate(summary: Mapping[str, Any] | None) -> float | None:
    if not summary:
        return None
    total = int(summary.get("requested_feature_column_set_count") or 0)
    if total <= 0:
        return None
    return float(int(summary.get("registered_feature_set_reuse_count") or 0) / total)


def _neighbor_hit_rate(summary: Mapping[str, Any] | None, records: list[Any]) -> float | None:
    if summary and int(summary.get("lookups") or 0) > 0:
        return float(summary.get("hit_rate") or 0.0)
    return _bool_payload_hit_rate(records, "neighbor_cache_hit")


def _artifact_counts(output_dir: Path) -> dict[str, int]:
    file_count = 0
    byte_count = 0
    root = Path(output_dir)
    if root.exists():
        for path in root.rglob("*"):
            if path.is_file():
                file_count += 1
                try:
                    byte_count += int(path.stat().st_size)
                except OSError:
                    pass
    return {"artifact_file_count": int(file_count), "artifact_bytes_written": int(byte_count)}
