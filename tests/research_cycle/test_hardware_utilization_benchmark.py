from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from tradingbotsuite import main
from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research_cycle.hardware_benchmark import write_hardware_utilization_report


def test_hardware_utilization_report_contains_research_boundary_and_recommendations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_cpu_probe(
        *,
        workers: int,
        logical_cpu_count: int,
        physical_cpu_count: int | None,
        duration_seconds: float,
    ) -> dict[str, object]:
        return {
            "probe_succeeded": True,
            "active_workers": workers,
            "logical_cpu_count": logical_cpu_count,
            "physical_cpu_count": physical_cpu_count,
            "process_cpu_percent_of_worker_capacity": 98.0,
            "process_cpu_percent_of_logical_capacity": 98.0,
            "worker_capacity_saturation_status": "saturated",
            "logical_capacity_saturation_status": "saturated",
            "fallback_reason": "",
        }

    def fake_gpu_probe(*, matrix_size: int, duration_seconds: float) -> dict[str, object]:
        return {
            "probe_succeeded": True,
            "gpu_execution_status": "cupy_matrix_probe_executed",
            "approx_gflops_per_second": 1234.5,
            "runtime_evidence": {"available": True, "gpu_name": "Fake CUDA GPU"},
            "fallback_reason": "",
        }

    monkeypatch.setattr(
        "tradingbotsuite.research_cycle.hardware_benchmark._run_cpu_saturation_probe",
        fake_cpu_probe,
    )
    monkeypatch.setattr(
        "tradingbotsuite.research_cycle.hardware_benchmark._run_gpu_matrix_probe",
        fake_gpu_probe,
    )
    monkeypatch.setattr(
        "tradingbotsuite.research_cycle.hardware_benchmark._environment_payload",
        lambda *, logical_cpu_count, physical_cpu_count: {
            "logical_cpu_count": logical_cpu_count,
            "physical_cpu_count": physical_cpu_count,
        },
    )

    result = write_hardware_utilization_report(
        output_dir=tmp_path / "hardware",
        cpu_workers=2,
        cpu_seconds=0.1,
        gpu_seconds=0.1,
        matrix_size=64,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert report["hardware_utilization_report_version"] == "hardware-utilization-study-readiness-v1"
    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["promotion_ready"] is False
    assert report["live_signal_input"] is False
    assert report["live_execution_input"] is False
    assert report["position_sizing_input"] is False
    assert report["candidate_acceptance_allowed"] is False
    assert report["speed_claimed"] is False
    assert report["cpu_probe"]["process_cpu_percent_of_logical_capacity"] == 98.0
    assert report["gpu_probe"]["gpu_execution_status"] == "cupy_matrix_probe_executed"
    assert report["recommendations"]["best_option"] == "hybrid_process_pool_cpu_plus_cuda_supported_fixed_holding"
    assert report["recommendations"]["selected_cpu_saturation_target_met"] is True
    assert report["prolonged_study_readiness"]["cpu_worker_saturation_target_met"] is True
    assert report["prolonged_study_readiness"]["ready_for_long_cpu_bound_research"] is True


def test_hardware_utilization_report_marks_below_target_cpu_not_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_cpu_probe(
        *,
        workers: int,
        logical_cpu_count: int,
        physical_cpu_count: int | None,
        duration_seconds: float,
    ) -> dict[str, object]:
        return {
            "probe_succeeded": True,
            "active_workers": workers,
            "logical_cpu_count": logical_cpu_count,
            "physical_cpu_count": physical_cpu_count,
            "process_cpu_percent_of_worker_capacity": 69.0,
            "process_cpu_percent_of_logical_capacity": 69.0,
            "worker_capacity_saturation_status": "below_target",
            "logical_capacity_saturation_status": "below_target",
            "fallback_reason": "",
        }

    monkeypatch.setattr(
        "tradingbotsuite.research_cycle.hardware_benchmark._run_cpu_saturation_probe",
        fake_cpu_probe,
    )
    monkeypatch.setattr(
        "tradingbotsuite.research_cycle.hardware_benchmark._run_gpu_matrix_probe",
        lambda *, matrix_size, duration_seconds: {
            "probe_succeeded": True,
            "gpu_execution_status": "cupy_matrix_probe_executed",
            "runtime_evidence": {"available": True},
            "fallback_reason": "",
        },
    )
    monkeypatch.setattr(
        "tradingbotsuite.research_cycle.hardware_benchmark._environment_payload",
        lambda *, logical_cpu_count, physical_cpu_count: {},
    )

    result = write_hardware_utilization_report(
        output_dir=tmp_path / "hardware",
        cpu_workers=2,
        cpu_seconds=0.1,
        gpu_seconds=0.1,
        matrix_size=64,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))

    assert report["recommendations"]["best_option"] == (
        "cpu_process_pool_below_saturation_target_recheck_worker_count_or_system_load"
    )
    assert report["recommendations"]["selected_cpu_saturation_target_met"] is False
    assert "cpu_process_pool_worker_capacity_below_saturation_target" in report["recommendations"]["non_blocking_warnings"]
    assert report["prolonged_study_readiness"]["cpu_worker_saturation_target_met"] is False
    assert report["prolonged_study_readiness"]["ready_for_long_cpu_bound_research"] is False


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"cpu_seconds": 0.01}, "cpu_seconds"),
        ({"cpu_seconds": 121.0}, "cpu_seconds"),
        ({"gpu_seconds": 0.01}, "gpu_seconds"),
        ({"gpu_seconds": 121.0}, "gpu_seconds"),
        ({"matrix_size": 63}, "matrix_size"),
        ({"matrix_size": 8193}, "matrix_size"),
        ({"cpu_workers": 0}, "cpu_workers"),
    ],
)
def test_hardware_utilization_report_rejects_invalid_inputs(
    tmp_path: Path,
    overrides: dict[str, object],
    match: str,
) -> None:
    output_dir = tmp_path / "hardware"
    params = {
        "output_dir": output_dir,
        "cpu_workers": 1,
        "cpu_seconds": 0.1,
        "gpu_seconds": 0.1,
        "matrix_size": 64,
        "app_config": AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    }
    params.update(overrides)

    with pytest.raises(ValueError, match=match):
        write_hardware_utilization_report(**params)

    assert not output_dir.exists()


def test_hardware_benchmark_cli_uses_research_output_resolver(tmp_path: Path, monkeypatch) -> None:
    research_root = tmp_path / "research"
    output_dir = research_root / "operator_runs" / "hardware"
    report_path = output_dir / "hardware_utilization_report.json"

    def fake_writer(**kwargs):
        output_dir.mkdir(parents=True)
        report_path.write_text(
            json.dumps(
                {
                    "cpu_probe": {
                        "probe_succeeded": True,
                        "process_cpu_percent_of_worker_capacity": 99.0,
                        "process_cpu_percent_of_logical_capacity": 99.0,
                    },
                    "gpu_probe": {
                        "probe_succeeded": False,
                        "gpu_execution_status": "fallback_cpu_or_vector_only",
                    },
                    "recommendations": {"best_option": "process_pool_cpu_plus_vector_fixed_holding_until_cuda_available"},
                }
            ),
            encoding="utf-8",
        )
        return argparse.Namespace(output_dir=output_dir, report_path=report_path)

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    monkeypatch.setattr(main, "write_hardware_utilization_report", fake_writer)
    result = main._run_benchmark_hardware_utilization_command(
        argparse.Namespace(
            output_dir="operator_runs/hardware",
            cpu_workers=1,
            cpu_seconds=0.1,
            gpu_seconds=0.1,
            matrix_size=64,
        )
    )

    assert result["output_dir"] == str(output_dir)
    assert result["hardware_utilization_report_path"] == str(report_path)
    assert result["cpu_probe_succeeded"] is True
    assert result["gpu_execution_status"] == "fallback_cpu_or_vector_only"
