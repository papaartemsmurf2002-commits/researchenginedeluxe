from __future__ import annotations

import time
from pathlib import Path

from tradingbotsuite.research_discovery.telemetry import TelemetrySession, build_compute_telemetry


def test_compute_telemetry_reports_normalized_processor_utilization(tmp_path: Path) -> None:
    session = TelemetrySession(
        wall_started=time.perf_counter() - 0.5,
        process_started=time.process_time(),
        tracing_started_here=False,
    )

    telemetry = build_compute_telemetry(
        session=session,
        output_dir=tmp_path,
        completed_records=[],
        active_workers=4,
        executed_this_call=8,
        artifact_write_seconds=0.2,
    )

    assert telemetry["telemetry_version"] == "discovery-compute-telemetry-v2"
    assert telemetry["logical_cpu_count"] >= 1
    assert telemetry["active_workers"] == 4
    assert telemetry["worker_capacity_cpu_seconds"] >= telemetry["wall_time_seconds"]
    assert telemetry["logical_capacity_cpu_seconds"] >= telemetry["wall_time_seconds"]
    assert telemetry["process_cpu_percent_of_worker_capacity"] is not None
    assert telemetry["process_cpu_percent_of_logical_capacity"] is not None
    assert telemetry["artifact_write_wall_time_share"] is not None
    assert telemetry["processor_utilization"]["active_workers"] == 4
    assert telemetry["processor_utilization"]["logical_cpu_count"] == telemetry["logical_cpu_count"]
    assert isinstance(telemetry["processor_utilization"]["diagnostic_reasons"], list)
    assert telemetry["processor_utilization"]["diagnostic_reasons"]


def test_compute_telemetry_prefers_observed_artifact_counts(tmp_path: Path) -> None:
    session = TelemetrySession(
        wall_started=time.perf_counter() - 0.5,
        process_started=time.process_time(),
        tracing_started_here=False,
    )

    telemetry = build_compute_telemetry(
        session=session,
        output_dir=tmp_path,
        completed_records=[],
        active_workers=2,
        executed_this_call=1,
        artifact_write_seconds=0.01,
        observed_artifact_counts={
            "artifact_file_count": 7,
            "artifact_bytes_written": 4096,
            "artifact_count_scope": "observed_parent_writes_this_call",
            "artifact_count_strategy": "recorded_artifact_write_paths_no_recursive_scan",
        },
    )

    assert telemetry["artifact_file_count"] == 7
    assert telemetry["artifact_bytes_written"] == 4096
    assert telemetry["artifact_count_scope"] == "observed_parent_writes_this_call"
    assert telemetry["artifact_count_strategy"] == "recorded_artifact_write_paths_no_recursive_scan"
