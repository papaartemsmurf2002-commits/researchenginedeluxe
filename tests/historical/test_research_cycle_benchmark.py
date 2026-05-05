from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tradingbotsuite import main
from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research_cycle import write_research_cycle_benchmark_report
from tradingbotsuite.research_cycle.benchmark import (
    BENCHMARK_THRESHOLDS,
    BENCHMARK_TIERS,
    _benchmark_gate,
    _write_benchmark_spec,
)


def test_research_cycle_benchmark_report_contains_research_only_gate_metrics(tmp_path: Path) -> None:
    result = write_research_cycle_benchmark_report(
        output_dir=tmp_path / "benchmarks" / "small",
        tier="small",
        repeat=2,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    run = report["runs"][0]

    assert report["benchmark_report_version"] == "historical-research-cycle-benchmark-v1"
    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["promotion_ready"] is False
    assert report["tier"] == "small"
    assert report["tier_dimensions"]["row_count"] == 120
    assert report["regression_threshold_policy"]["min_candidate_backtests_per_minute_mean"] > 0.0
    assert report["repeat"] == 2
    assert len(report["runs"]) == 2
    assert run["rows_per_second"] > 0.0
    assert run["candidate_backtests_per_minute"] > 0.0
    assert run["feature_rows_per_second"] > 0.0
    assert isinstance(run["tracemalloc_memory_peak_bytes"], int)
    assert report["cycle_repeat_tracemalloc_memory_peak_bytes"] >= run["tracemalloc_memory_peak_bytes"]
    assert run["memory_measurement"]["scope"] == "historical_cycle_repeat_python_tracemalloc_peak_bytes"
    assert run["memory_measurement"]["phase"] == "main_historical_cycle_repeats_only"
    assert run["memory_measurement"]["measurement_phase"] == "main_historical_cycle_repeats_only"
    assert run["memory_measurement"]["rss_measured"] is False
    assert run["memory_measurement"]["benchmark_wide_memory_measured"] is False
    assert report["memory_measurement"]["claim_scope"] == "repeat_phase_python_allocation_guardrail_not_benchmark_wide_or_total_process_memory"
    assert report["memory_measurement"]["benchmark_wide_memory_measured"] is False
    assert report["artifact_overhead"]["file_count"] > 0
    assert report["artifact_overhead"]["total_bytes"] > 0
    assert report["artifact_overhead"]["bytes_per_candidate_backtest"] > 0.0
    assert report["artifact_overhead"]["scope"] == "benchmark_directory_after_all_benchmark_artifacts_exist"
    assert report["artifact_overhead"]["measurement_phase"] == "post_backend_comparison_and_final_report_write"
    assert report["artifact_overhead"]["includes_backend_comparison"] is True
    assert report["artifact_overhead"]["backend_comparison_file_count"] > 0
    assert report["artifact_overhead"]["backend_comparison_bytes"] > 0
    assert report["artifact_overhead"]["includes_final_report"] is True
    assert report["artifact_overhead"]["final_report_bytes"] == result.report_path.stat().st_size
    assert report["artifact_overhead"]["section_file_counts"]["backend_comparison"] > 0
    assert report["artifact_overhead"]["section_file_counts"]["research_cycle_benchmark_report.json"] == 1
    assert "cache_speedup" not in report
    feature_cache_reuse = report["feature_cache_reuse"]
    assert feature_cache_reuse["measured"] is True
    assert feature_cache_reuse["evidence_type"] == "feature_cache_reuse"
    assert feature_cache_reuse["scope"] == "feature_build_cache"
    assert feature_cache_reuse["backtest_cache_measured"] is False
    assert feature_cache_reuse["speed_claimed"] is False
    assert feature_cache_reuse["timing_observation_scope"] == "observed_local_cold_vs_warm_timing_not_regression_gate_or_speed_claim"
    assert feature_cache_reuse["cold_misses"] > 0
    assert feature_cache_reuse["warm_hits"] >= feature_cache_reuse["cold_misses"]
    assert feature_cache_reuse["cold_build_complete"] is True
    assert feature_cache_reuse["warm_reuse_complete"] is True
    assert feature_cache_reuse["cold_elapsed_seconds"] > 0.0
    assert feature_cache_reuse["warm_elapsed_seconds"] > 0.0
    assert feature_cache_reuse["feature_output_hashes_match"] is True
    assert report["backtest_identity_repeat_consistent"]["measured"] is True
    assert report["backtest_identity_repeat_consistent"]["backtest_cache_measured"] is False
    assert report["backtest_identity_repeat_consistent"]["cache_policy"] == "identity_only_no_execution_cache"
    assert report["backtest_identity_repeat_consistent"]["cache_keys_consistent"] is True
    assert report["backtest_identity_repeat_consistent"]["result_hashes_consistent"] is True
    assert report["backtest_identity_repeat_consistent"]["ranking_identity_consistent"] is True
    optimizer_parallel = report["optimizer_parallel_speedup"]
    assert optimizer_parallel["measured"] is True
    assert optimizer_parallel["research_only"] is True
    assert optimizer_parallel["observe_only"] is True
    assert optimizer_parallel["promotion_ready"] is False
    assert optimizer_parallel["scope"] == "optimizer_candidate_evaluator_parallelism"
    assert optimizer_parallel["synthetic_evaluator"] is True
    assert optimizer_parallel["historical_cycle_backtest_parallel_measured"] is False
    assert optimizer_parallel["backtest_execution_cache_measured"] is False
    assert optimizer_parallel["repeat"] == 3
    assert optimizer_parallel["parallel_workers"] > optimizer_parallel["serial_workers"]
    assert optimizer_parallel["possible_active_parallel_workers"] == optimizer_parallel["parallel_workers"]
    assert len(optimizer_parallel["serial_elapsed_seconds_samples"]) == optimizer_parallel["repeat"]
    assert len(optimizer_parallel["parallel_elapsed_seconds_samples"]) == optimizer_parallel["repeat"]
    assert optimizer_parallel["speedup_factor"] > 0.0
    assert optimizer_parallel["result_hashes_equal"] is True
    assert optimizer_parallel["stability_region_hashes_equal"] is True
    assert optimizer_parallel["serial_total_candidates"] == optimizer_parallel["parallel_total_candidates"]
    assert optimizer_parallel["serial_effective_candidates"] == optimizer_parallel["parallel_effective_candidates"]
    comparison = report["reference_vs_vector_backend_comparison"]
    assert comparison["measured"] is True
    assert comparison["research_only"] is True
    assert comparison["observe_only"] is True
    assert comparison["promotion_ready"] is False
    assert comparison["scope"] == "fixed_holding_primary_bar_historical_cycle"
    assert comparison["speed_claimed"] is False
    assert comparison["claim_scope"] == "local_synthetic_runtime_observation_not_speedup_or_production_claim"
    assert comparison["default_backend_verified"] == "reference"
    assert len(comparison["pairs"]) == report["repeat"]
    pair = comparison["pairs"][0]
    assert pair["candidate_backtest_count_equal"] is True
    assert pair["row_count_processed_equal"] is True
    assert pair["candidate_ids_equal"] is True
    assert pair["evaluation_scope_counts_equal"] is True
    assert pair["behavioral_artifact_hashes_equal"] is True
    assert pair["reference"]["backend_used_counts"] == {"reference": pair["reference"]["candidate_backtest_count"]}
    assert pair["vector"]["backend_used_counts"] == {"vector_fixed_holding": pair["vector"]["candidate_backtest_count"]}
    assert pair["vector"]["vector_scope_counts"] == {"fixed_holding_primary_bar": pair["vector"]["candidate_backtest_count"]}
    assert pair["vector"]["fallback_count"] == 0
    assert pair["reference"]["backtest_runtime_ms_sum"] > 0.0
    assert pair["vector"]["backtest_runtime_ms_sum"] > 0.0
    assert pair["observed_runtime_ratio_reference_over_vector"] > 0.0
    benchmark_gate = report["benchmark_gate"]
    assert benchmark_gate["research_only"] is True
    assert benchmark_gate["observe_only"] is True
    assert benchmark_gate["promotion_ready"] is False
    assert benchmark_gate["scope"] == "historical_research_cycle_local_synthetic"
    assert benchmark_gate["claim_scope"] == "regression_guardrail_not_live_or_profit_claim"
    assert benchmark_gate["evidence_complete"] is True
    assert benchmark_gate["passed"] is True
    assert benchmark_gate["failure_reasons"] == []
    assert benchmark_gate["skipped_reasons"] == []
    assert benchmark_gate["incomplete_evidence_reasons"] == []
    assert {check["status"] for check in benchmark_gate["checks"]} == {"passed"}
    check_names = {check["name"] for check in benchmark_gate["checks"]}
    assert {
        "rows_per_second_mean",
        "candidate_backtests_per_minute_mean",
        "tracemalloc_memory_peak_bytes",
        "artifact_bytes_per_candidate_backtest",
        "artifact_overhead_includes_backend_comparison",
        "artifact_overhead_includes_final_report",
        "deterministic_repeat_consistent",
        "backtest_identity_repeat_consistent",
        "feature_cache_reuse_measured",
        "feature_output_hashes_match",
        "optimizer_parallel_result_equivalence",
        "optimizer_parallel_timing_measured",
        "reference_vs_vector_backend_comparison_measured",
        "reference_vs_vector_behavioral_equivalence",
        "vector_supported_scope_used",
        "vector_speed_claim_not_made",
        "live_fetch_used",
        "order_placement_used",
        "backtest_cache_lookup_used",
        "backtest_cache_hit",
        "execution_cache_reuse_enabled",
    } <= check_names
    assert run["backtest_identity"]["cache_policy"] == "identity_only_no_execution_cache"
    assert run["backtest_identity"]["cache_lookup_used"] is False
    assert run["backtest_identity"]["cache_hit"] is False
    assert run["backtest_identity"]["execution_cache_reuse_enabled"] is False
    assert run["backtest_identity"]["ranking_identity_sha256"]
    assert run["live_fetch_used"] is False
    assert run["order_placement_used"] is False
    assert report["live_fetch_used"] is False
    assert report["order_placement_used"] is False
    assert isinstance(report["deterministic_repeat_hash"], str)
    assert report["deterministic_repeat_consistent"] is True
    assert Path(run["research_cycle_manifest_path"]).exists()


def test_research_cycle_benchmark_cleans_stale_repeat_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "benchmarks" / "stale"
    write_research_cycle_benchmark_report(
        output_dir=output_dir,
        tier="small",
        repeat=2,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    result = write_research_cycle_benchmark_report(
        output_dir=output_dir,
        tier="small",
        repeat=1,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert report["repeat"] == 1
    assert not (output_dir / "runs" / "repeat_01").exists()
    assert report["benchmark_gate"]["passed"] is False
    assert report["benchmark_gate"]["evidence_complete"] is False
    assert report["benchmark_gate"]["incomplete_evidence_reasons"] == []
    assert "repeat_count_below_determinism_evidence_requirement" in report["benchmark_gate"]["skipped_reasons"]


def test_research_cycle_benchmark_gate_reports_failed_thresholds() -> None:
    gate = _benchmark_gate(
        tier_id="small",
        repeat_count=2,
        summary={
            "rows_per_second_mean": 0.0,
            "candidate_backtests_per_minute_mean": 0.0,
        },
        tracemalloc_memory_peak_bytes=10 * 1024 * 1024 * 1024,
        artifact_overhead={
            "bytes_per_candidate_backtest": 100 * 1024 * 1024,
            "includes_backend_comparison": True,
            "includes_final_report": True,
        },
        feature_cache_reuse={"measured": False, "feature_output_hashes_match": False},
        backtest_identity={
            "cache_keys_consistent": False,
            "result_hashes_consistent": False,
            "ranking_identity_consistent": False,
        },
        deterministic_repeat_consistent=False,
        optimizer_parallel_speedup={
            "result_hashes_equal": False,
            "stability_region_hashes_equal": False,
            "speedup_factor": 0.0,
            "serial_elapsed_seconds_median": 0.0,
            "parallel_elapsed_seconds_median": 0.0,
        },
        live_fetch_used=True,
        order_placement_used=True,
        backtest_cache_lookup_used=True,
        backtest_cache_hit=True,
        execution_cache_reuse_enabled=True,
        backend_comparison={
            "measured": True,
            "speed_claimed": True,
            "pairs": [
                {
                    "candidate_backtest_count_equal": False,
                    "row_count_processed_equal": False,
                    "candidate_ids_equal": False,
                    "evaluation_scope_counts_equal": False,
                    "behavioral_artifact_hashes_equal": False,
                    "vector": {
                        "fallback_count": 1,
                        "backend_used_counts": {"reference": 1},
                        "candidate_backtest_count": 1,
                        "vector_scope_counts": {},
                    },
                }
            ],
        },
    )

    assert gate["passed"] is False
    assert gate["evidence_complete"] is True
    assert gate["incomplete_evidence_reasons"] == []
    assert gate["failure_reasons"]
    assert "rows_per_second_mean_threshold_failed" in gate["failure_reasons"]
    assert "missing_artifact_overhead_backend_comparison_evidence" not in gate["failure_reasons"]
    assert "missing_artifact_overhead_final_report_evidence" not in gate["failure_reasons"]
    assert "missing_reference_vs_vector_backend_comparison_evidence" not in gate["failure_reasons"]
    assert "failed" in {check["status"] for check in gate["checks"]}


def test_research_cycle_benchmark_gate_marks_missing_required_evidence_incomplete() -> None:
    gate = _benchmark_gate(
        tier_id="small",
        repeat_count=2,
        summary={
            "rows_per_second_mean": 10.0,
            "candidate_backtests_per_minute_mean": 10.0,
        },
        tracemalloc_memory_peak_bytes=1024,
        artifact_overhead={
            "bytes_per_candidate_backtest": 1.0,
            "includes_backend_comparison": False,
            "includes_final_report": False,
        },
        feature_cache_reuse={"measured": True, "feature_output_hashes_match": True},
        backtest_identity={
            "cache_keys_consistent": True,
            "result_hashes_consistent": True,
            "ranking_identity_consistent": True,
        },
        deterministic_repeat_consistent=True,
        optimizer_parallel_speedup={
            "measured": True,
            "result_hashes_equal": True,
            "stability_region_hashes_equal": True,
            "speedup_factor": 1.0,
            "serial_elapsed_seconds_median": 1.0,
            "parallel_elapsed_seconds_median": 1.0,
        },
        live_fetch_used=False,
        order_placement_used=False,
        backtest_cache_lookup_used=False,
        backtest_cache_hit=False,
        execution_cache_reuse_enabled=False,
        backend_comparison={"measured": False, "speed_claimed": False, "pairs": []},
    )

    assert gate["passed"] is False
    assert gate["evidence_complete"] is False
    assert gate["skipped_reasons"] == []
    assert set(gate["incomplete_evidence_reasons"]) == {
        "missing_artifact_overhead_backend_comparison_evidence",
        "missing_artifact_overhead_final_report_evidence",
        "missing_reference_vs_vector_backend_comparison_evidence",
    }


def test_research_cycle_benchmark_cli_command_fails_on_incomplete_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "write_research_cycle_benchmark_report",
        _fake_benchmark_writer(
            tmp_path,
            passed=False,
            evidence_complete=False,
            skipped_reasons=["repeat_count_below_determinism_evidence_requirement"],
        ),
    )

    with pytest.raises(ValueError, match="benchmark_historical_research_cycle_gate_failed"):
        main._run_benchmark_historical_research_cycle_command(
            argparse.Namespace(
                tier="small",
                output_dir=str(tmp_path / "cli-benchmark"),
                repeat=1,
                allow_failed_gate=False,
            )
        )


def test_research_cycle_benchmark_cli_command_allows_report_only_failed_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "write_research_cycle_benchmark_report",
        _fake_benchmark_writer(
            tmp_path,
            passed=False,
            evidence_complete=False,
            skipped_reasons=["repeat_count_below_determinism_evidence_requirement"],
        ),
    )

    payload = main._run_benchmark_historical_research_cycle_command(
        argparse.Namespace(
            tier="small",
            output_dir=str(tmp_path / "cli-benchmark"),
            repeat=1,
            allow_failed_gate=True,
        )
    )

    assert Path(str(payload["benchmark_report_path"])).exists()
    assert Path(str(payload["output_dir"])).exists()
    assert payload["benchmark_gate_passed"] is False
    assert payload["evidence_complete"] is False
    assert payload["failure_reasons"] == []
    assert payload["skipped_reasons"] == ["repeat_count_below_determinism_evidence_requirement"]
    assert payload["incomplete_evidence_reasons"] == []


def test_research_cycle_benchmark_cli_payload_exposes_passed_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "write_research_cycle_benchmark_report",
        _fake_benchmark_writer(tmp_path, passed=True, evidence_complete=True),
    )

    payload = main._run_benchmark_historical_research_cycle_command(
        argparse.Namespace(
            tier="small",
            output_dir=str(tmp_path / "cli-benchmark"),
            repeat=2,
            allow_failed_gate=False,
        )
    )

    assert payload["benchmark_gate_passed"] is True
    assert payload["evidence_complete"] is True
    assert payload["failure_reasons"] == []
    assert payload["skipped_reasons"] == []
    assert payload["incomplete_evidence_reasons"] == []
    assert payload["repeat"] == 2


def test_research_cycle_benchmark_cli_tiers_come_from_registry(monkeypatch) -> None:
    assert "medium" in BENCHMARK_TIERS
    assert "medium" in BENCHMARK_THRESHOLDS
    assert "provider_latest_month" in BENCHMARK_TIERS
    assert "provider_latest_month" in BENCHMARK_THRESHOLDS
    assert BENCHMARK_TIERS["medium"]["row_count"] > BENCHMARK_TIERS["small"]["row_count"]

    monkeypatch.setattr(
        sys,
        "argv",
        ["tradingbot", "benchmark-historical-research-cycle", "--tier", "provider_latest_month"],
    )

    args = main.parse_args()

    assert args.tier == "provider_latest_month"
    assert args.repeat == 2


def test_research_cycle_benchmark_provider_tier_writes_non_synthetic_spec(tmp_path: Path) -> None:
    tier_config = {
        **BENCHMARK_TIERS["provider_latest_month"],
        "dataset_manifest_path": str(tmp_path / "fixture_pack_manifest.json"),
    }

    spec_path = _write_benchmark_spec(
        tmp_path / "provider-benchmark",
        tier_id="provider_latest_month",
        tier_config=tier_config,
    )
    payload = json.loads(spec_path.read_text(encoding="utf-8"))

    assert payload["data"] == {
        "dataset_manifest_paths": [str((tmp_path / "fixture_pack_manifest.json").resolve())],
        "synthetic_fixture": False,
    }
    assert "synthetic_row_count" not in payload["data"]
    assert "synthetic_variant" not in payload["data"]


def test_research_cycle_benchmark_resolves_relative_output_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(
        BENCHMARK_TIERS,
        "small",
        {
            **BENCHMARK_TIERS["small"],
            "row_count": 80,
            "strategies": ["baseline_no_trade"],
            "top_regions_to_refine": 1,
        },
    )

    result = write_research_cycle_benchmark_report(
        output_dir=Path("relative-benchmark"),
        tier="small",
        repeat=1,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    run_output = Path(report["runs"][0]["output_dir"])
    spec_payload = json.loads(Path(report["runs"][0]["spec_path"]).read_text(encoding="utf-8"))

    assert result.output_dir == (tmp_path / "relative-benchmark").resolve()
    assert result.report_path == result.output_dir / "research_cycle_benchmark_report.json"
    assert run_output.is_absolute()
    assert Path(spec_payload["output_dir"]).is_absolute()
    assert "relative-benchmark/runs/repeat_00/relative-benchmark" not in run_output.as_posix()


def test_research_cycle_benchmark_provider_gate_uses_provider_scope() -> None:
    gate = _benchmark_gate(
        tier_id="provider_latest_month",
        repeat_count=2,
        summary={
            "rows_per_second_mean": 10.0,
            "candidate_backtests_per_minute_mean": 10.0,
        },
        tracemalloc_memory_peak_bytes=1024,
        artifact_overhead={
            "bytes_per_candidate_backtest": 1.0,
            "includes_backend_comparison": True,
            "includes_final_report": True,
        },
        feature_cache_reuse={"measured": True, "feature_output_hashes_match": True},
        backtest_identity={
            "cache_keys_consistent": True,
            "result_hashes_consistent": True,
            "ranking_identity_consistent": True,
        },
        deterministic_repeat_consistent=True,
        optimizer_parallel_speedup={
            "measured": True,
            "result_hashes_equal": True,
            "stability_region_hashes_equal": True,
            "speedup_factor": 1.0,
            "serial_elapsed_seconds_median": 1.0,
            "parallel_elapsed_seconds_median": 1.0,
        },
        live_fetch_used=False,
        order_placement_used=False,
        backtest_cache_lookup_used=False,
        backtest_cache_hit=False,
        execution_cache_reuse_enabled=False,
        backend_comparison={
            "measured": True,
            "speed_claimed": False,
            "pairs": [
                {
                    "candidate_backtest_count_equal": True,
                    "row_count_processed_equal": True,
                    "candidate_ids_equal": True,
                    "evaluation_scope_counts_equal": True,
                    "behavioral_artifact_hashes_equal": True,
                    "vector": {
                        "fallback_count": 0,
                        "backend_used_counts": {"vector_fixed_holding": 1},
                        "candidate_backtest_count": 1,
                        "vector_scope_counts": {"fixed_holding_primary_bar": 1},
                    },
                }
            ],
        },
    )

    assert gate["passed"] is True
    assert gate["benchmark_data_scope"] == "local_provider_fixture_pack"
    assert gate["scope"] == "historical_research_cycle_local_provider_fixture_pack"
    assert gate["profile_version"] == "historical-research-cycle-provider-fixture-thresholds-v1"


def test_research_cycle_benchmark_medium_tier_bounded_execution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setitem(
        BENCHMARK_TIERS,
        "medium",
        {
            "row_count": 80,
            "holding_windows": ["4h"],
            "feature_sets": ["features_price_trend_vol"],
            "strategies": ["baseline_no_trade", "trend_following_v1"],
            "min_splits": 2,
            "top_regions_to_refine": 1,
        },
    )

    result = write_research_cycle_benchmark_report(
        output_dir=tmp_path / "benchmarks" / "medium",
        tier="medium",
        repeat=2,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert report["tier"] == "medium"
    assert report["repeat"] == 2
    assert report["tier_dimensions"]["row_count"] == 80
    assert len(report["runs"]) == 2
    assert report["benchmark_gate"]["evidence_complete"] is True
    assert report["benchmark_gate"]["passed"] is True
    assert report["benchmark_gate"]["incomplete_evidence_reasons"] == []
    assert report["feature_cache_reuse"]["measured"] is True
    assert report["artifact_overhead"]["includes_backend_comparison"] is True
    assert report["artifact_overhead"]["includes_final_report"] is True
    assert report["reference_vs_vector_backend_comparison"]["measured"] is True


def _fake_benchmark_writer(
    tmp_path: Path,
    *,
    passed: bool,
    evidence_complete: bool,
    failure_reasons: list[str] | None = None,
    skipped_reasons: list[str] | None = None,
):
    def _write_report(*, output_dir=None, tier="small", repeat=1, app_config=None):
        _ = app_config
        target = Path(output_dir) if output_dir is not None else tmp_path / "benchmark"
        target.mkdir(parents=True, exist_ok=True)
        report_path = target / "research_cycle_benchmark_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "tier": tier,
                    "repeat": repeat,
                    "benchmark_gate": {
                        "passed": passed,
                        "evidence_complete": evidence_complete,
                        "failure_reasons": list(failure_reasons or []),
                        "skipped_reasons": list(skipped_reasons or []),
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(output_dir=target, report_path=report_path)

    return _write_report
