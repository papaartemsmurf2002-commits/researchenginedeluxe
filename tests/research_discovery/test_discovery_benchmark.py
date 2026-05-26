from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

from tradingbotsuite import main
from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research.command_registry import RESEARCH_COMMANDS
from tradingbotsuite.research_discovery.benchmark import (
    DISCOVERY_BENCHMARK_REPORT_VERSION,
    DISCOVERY_BENCHMARK_TIERS,
    DiscoveryBenchmarkResult,
    _discovery_benchmark_gate,
    write_discovery_benchmark_report,
)


def _app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(research=ResearchConfig(output_dir=tmp_path / "research"))


def test_discovery_benchmark_report_contains_research_only_gate_metrics(tmp_path: Path) -> None:
    result = write_discovery_benchmark_report(
        output_dir=tmp_path / "benchmarks" / "quick",
        tier="quick",
        repeat=1,
        app_config=_app_config(tmp_path),
    )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    gate = report["benchmark_gate"]
    run = report["runs"][0]

    assert report["discovery_benchmark_report_version"] == DISCOVERY_BENCHMARK_REPORT_VERSION
    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["promotion_ready"] is False
    assert report["candidate_pack_written"] is False
    assert report["live_fetch_used"] is False
    assert report["order_placement_used"] is False
    assert report["tier"] == "quick"
    assert gate["research_only"] is True
    assert gate["observe_only"] is True
    assert gate["promotion_ready"] is False
    assert gate["passed"] is True
    assert gate["evidence_complete"] is True
    assert gate["failure_reasons"] == []
    assert run["resume_ledger_hash_equal"] is True
    assert run["snapshot_integrity_passed"] is True
    assert run["resumed"]["completed_trial_count"] == DISCOVERY_BENCHMARK_TIERS["quick"]["max_trials"]
    assert run["resumed"]["snapshot_integrity"]["passed"] is True
    assert run["resumed"]["trial_integrity"]["passed"] is True
    assert run["resumed"]["compute_telemetry"]["telemetry_version"] == "discovery-compute-telemetry-v2"
    assert run["resumed"]["compute_telemetry"]["active_workers"] >= 1
    assert run["resumed"]["compute_telemetry"]["logical_cpu_count"] >= 1
    assert run["resumed"]["compute_telemetry"]["process_cpu_percent_of_worker_capacity"] is not None
    assert run["resumed"]["compute_telemetry"]["processor_diagnostic_reasons"]


def test_discovery_benchmark_resume_integrity_matches_uninterrupted_run(tmp_path: Path) -> None:
    result = write_discovery_benchmark_report(
        output_dir=tmp_path / "benchmarks" / "standard",
        tier="standard",
        repeat=1,
        app_config=_app_config(tmp_path),
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    run = report["runs"][0]

    assert run["full"]["ledger_sha256"] == run["resumed"]["ledger_sha256"]
    assert run["full"]["completed_trial_ids"] == run["resumed"]["completed_trial_ids"]
    assert run["partial"]["status"] == "in_progress"
    assert run["resumed"]["status"] == "completed"
    assert run["full"]["snapshot_integrity"]["latest_summary"]["status"] == "completed"
    assert run["partial"]["snapshot_integrity"]["latest_summary"]["status"] == "in_progress"


def test_discovery_benchmark_gate_reports_failed_thresholds(tmp_path: Path) -> None:
    result = write_discovery_benchmark_report(
        output_dir=tmp_path / "benchmarks" / "gate",
        tier="quick",
        repeat=1,
        app_config=_app_config(tmp_path),
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    bad_run = dict(report["runs"][0])
    bad_run["resume_ledger_hash_equal"] = False

    gate = _discovery_benchmark_gate(
        tier_id="quick",
        tier_config=DISCOVERY_BENCHMARK_TIERS["quick"],
        repetitions=[bad_run],
        artifact_overhead={**report["artifact_overhead"], "bytes_per_completed_trial": 999999999.0},
    )

    assert gate["passed"] is False
    assert "resume_ledger_hash_equal_failed" in gate["failure_reasons"]
    assert "artifact_bytes_per_completed_trial_failed" in gate["failure_reasons"]


def test_discovery_benchmark_tiers_come_from_registry_and_config(monkeypatch) -> None:
    config_path = Path("configs/discovery/discovery_benchmark_tiers_v4.json")
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    assert sorted(DISCOVERY_BENCHMARK_TIERS) == ["deep", "quick", "standard"]
    assert sorted(payload["tiers"]) == sorted(DISCOVERY_BENCHMARK_TIERS)
    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert "benchmark-discovery-run" in RESEARCH_COMMANDS

    monkeypatch.setattr(sys, "argv", ["tradingbot", "benchmark-discovery-run", "--tier", "deep"])
    args = main.parse_args()

    assert args.tier == "deep"
    assert args.repeat == 1


def test_discovery_benchmark_cli_payload_exposes_passed_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(
        main,
        "write_discovery_benchmark_report",
        _fake_discovery_benchmark_writer(tmp_path, passed=True, evidence_complete=True),
    )

    payload = main._run_benchmark_discovery_command(
        argparse.Namespace(
            tier="quick",
            output_dir=str(tmp_path / "cli-benchmark"),
            repeat=1,
            allow_failed_gate=False,
        )
    )

    assert payload["benchmark_gate_passed"] is True
    assert payload["evidence_complete"] is True
    assert payload["failure_reasons"] == []
    assert payload["repeat"] == 1


def test_discovery_benchmark_cli_command_fails_on_failed_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(
        main,
        "write_discovery_benchmark_report",
        _fake_discovery_benchmark_writer(tmp_path, passed=False, evidence_complete=True, failure_reasons=["resume_ledger_hash_equal_failed"]),
    )

    with pytest.raises(ValueError, match="benchmark_discovery_run_gate_failed:resume_ledger_hash_equal_failed"):
        main._run_benchmark_discovery_command(
            argparse.Namespace(
                tier="quick",
                output_dir=str(tmp_path / "cli-benchmark"),
                repeat=1,
                allow_failed_gate=False,
            )
        )


def test_discovery_benchmark_cli_command_allows_report_only_failed_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(
        main,
        "write_discovery_benchmark_report",
        _fake_discovery_benchmark_writer(tmp_path, passed=False, evidence_complete=False, skipped_reasons=["snapshot_integrity_missing"]),
    )

    payload = main._run_benchmark_discovery_command(
        argparse.Namespace(
            tier="quick",
            output_dir=str(tmp_path / "cli-benchmark"),
            repeat=1,
            allow_failed_gate=True,
        )
    )

    assert payload["benchmark_gate_passed"] is False
    assert payload["evidence_complete"] is False
    assert payload["skipped_reasons"] == ["snapshot_integrity_missing"]
    assert Path(str(payload["benchmark_report_path"])).exists()


def _fake_discovery_benchmark_writer(
    tmp_path: Path,
    *,
    passed: bool,
    evidence_complete: bool,
    failure_reasons: list[str] | None = None,
    skipped_reasons: list[str] | None = None,
    incomplete_evidence_reasons: list[str] | None = None,
):
    def fake_writer(*, output_dir=None, tier="quick", repeat=1, app_config=None):
        target = Path(output_dir) if output_dir is not None else tmp_path / "benchmark"
        target.mkdir(parents=True, exist_ok=True)
        report_path = target / "discovery_benchmark_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "tier": tier,
                    "repeat": repeat,
                    "benchmark_gate": {
                        "passed": passed,
                        "evidence_complete": evidence_complete,
                        "failure_reasons": failure_reasons or [],
                        "skipped_reasons": skipped_reasons or [],
                        "incomplete_evidence_reasons": incomplete_evidence_reasons or [],
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return DiscoveryBenchmarkResult(output_dir=target, report_path=report_path)

    return fake_writer
