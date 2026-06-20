from __future__ import annotations

import csv
import json
import math
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from tradingbotsuite.research.hmm_knn_experiments import run_hmm_knn_experiment_matrix
from tradingbotsuite.research.knn_four_bar import (
    FOUR_BAR_DATASET_VERSION,
    FourBarDatasetBuildResult,
    build_four_bar_knn_dataset_from_binance_archive,
    build_four_bar_knn_dataset_from_fixture,
)
from tradingbotsuite.research.live_readiness import (
    build_research_boundary_report,
    research_boundary_metadata,
    research_boundary_passed,
)


FOUR_BAR_KNN_LARGER_VALIDATION_VERSION = "wpr106-77-four-bar-knn-larger-validation-v1"
FOUR_BAR_KNN_LARGER_VALIDATION_MANIFEST_VERSION = "wpr106-77-four-bar-knn-larger-validation-manifest-v1"
FOUR_BAR_KNN_LARGER_VALIDATION_SUMMARY_VERSION = "wpr106-77-four-bar-knn-larger-validation-summary-v1"
FOUR_BAR_KNN_LARGER_VALIDATION_DEFAULT_SAMPLE_ROWS_PER_INTERVAL = 8_000
FOUR_BAR_ARCHIVE_MAPPING_VERSION = "wpr106-79-local-binance-archive-four-bar-mapper-v1"
FOUR_BAR_ARCHIVE_MAPPING_MANIFEST_VERSION = "wpr106-79-local-binance-archive-four-bar-mapper-manifest-v1"
FOUR_BAR_ARCHIVE_MAPPING_DEFAULT_START_MONTH = "2024-01"
FOUR_BAR_ARCHIVE_MAPPING_DEFAULT_END_MONTH = "2024-12"
FOUR_BAR_KNN_LARGER_VALIDATION_COST_STRESS_BPS = (10.0, 12.5, 15.0, 17.5, 20.0, 25.0, 30.0, 40.0, 50.0, 75.0, 100.0)
FOUR_BAR_KNN_LARGER_VALIDATION_GATE = {
    "min_trade_count": 150,
    "min_trades_per_split": 40,
    "min_positive_split_checks": 3,
    "min_profit_factor": 1.05,
    "min_cost_stress_survival_rate": 0.70,
    "max_single_split_pnl_share": 0.60,
}


@dataclass(frozen=True, slots=True)
class FourBarKnnLargerValidationResult:
    output_dir: Path
    manifest_path: Path
    summary_json_path: Path
    summary_csv_path: Path
    command_path: Path

    def to_payload(self) -> dict[str, object]:
        return {
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "summary_json_path": str(self.summary_json_path),
            "summary_csv_path": str(self.summary_csv_path),
            "command_path": str(self.command_path),
        }


@dataclass(frozen=True, slots=True)
class FourBarArchiveMappingResult:
    output_dir: Path
    manifest_path: Path
    summary_json_path: Path
    command_path: Path
    matrix_command_path: Path

    def to_payload(self) -> dict[str, object]:
        return {
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "summary_json_path": str(self.summary_json_path),
            "command_path": str(self.command_path),
            "matrix_command_path": str(self.matrix_command_path),
        }


def map_local_binance_archive_four_bar_datasets(
    *,
    output_dir: Path,
    archive_root: Path | None = None,
    start_month: str = FOUR_BAR_ARCHIVE_MAPPING_DEFAULT_START_MONTH,
    end_month: str = FOUR_BAR_ARCHIVE_MAPPING_DEFAULT_END_MONTH,
    sample_rows_per_interval: int = FOUR_BAR_KNN_LARGER_VALIDATION_DEFAULT_SAMPLE_ROWS_PER_INTERVAL,
    matrix_workers: int = 1,
    force: bool = False,
) -> FourBarArchiveMappingResult:
    """Map the existing local Binance archive into four-bar validation datasets."""

    if sample_rows_per_interval < 20:
        raise ValueError("sample_rows_per_interval must be at least 20")
    if matrix_workers < 1:
        raise ValueError("matrix_workers must be at least 1")

    repo_root = _repo_root()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_root = (
        archive_root
        or repo_root / "data" / "research" / "historical_data_cache" / "binance_vision_public_archive" / "downloads"
    ).expanduser().resolve()
    started_at_ms = int(time.time() * 1000)
    started_perf = time.perf_counter()

    command_path = output_dir / "run_map_binance_archive_four_bar_datasets.ps1"
    matrix_command_path = output_dir / "run_archive_four_bar_knn_validation_matrix.ps1"
    _write_archive_mapping_command(
        command_path,
        output_dir=output_dir,
        archive_root=archive_root,
        start_month=start_month,
        end_month=end_month,
        sample_rows_per_interval=sample_rows_per_interval,
        matrix_workers=matrix_workers,
        force=force,
    )

    datasets: dict[str, dict[str, Any]] = {}
    specs: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for symbol, base_config_path in (
        ("BTCUSDT", repo_root / "configs" / "research" / "no_rsi_knn_four_bar_btcusdt_r106_v1.json"),
        ("ETHUSDT", repo_root / "configs" / "research" / "no_rsi_knn_four_bar_ethusdt_r106_v1.json"),
    ):
        dataset_name = f"{symbol.lower()}_no_rsi_four_bar_binance_archive_{start_month}_to_{end_month}_{sample_rows_per_interval}_dataset.parquet"
        dataset_path = output_dir / "datasets" / dataset_name
        manifest_path = output_dir / "datasets" / f"{Path(dataset_name).stem}_manifest.json"
        try:
            if not force and dataset_path.exists() and manifest_path.exists():
                manifest = _read_json(manifest_path)
                dataset_result = FourBarDatasetBuildResult(
                    dataset_path=dataset_path,
                    manifest_path=manifest_path,
                    row_count=int(manifest.get("row_count") or 0),
                    dataset_sha256=str(manifest.get("dataset_sha256") or _file_sha256(dataset_path)),
                    manifest_sha256=_file_sha256(manifest_path),
                )
            else:
                dataset_result = build_four_bar_knn_dataset_from_binance_archive(
                    archive_root=archive_root,
                    output_dir=output_dir / "datasets",
                    symbol=symbol,
                    start_month=start_month,
                    end_month=end_month,
                    dataset_name=dataset_name,
                    max_rows_per_interval=sample_rows_per_interval,
                )
            dataset_manifest = _read_json(dataset_result.manifest_path)
            spec_path = _write_validation_spec(
                output_dir=output_dir / "specs",
                symbol=symbol,
                base_config_path=base_config_path,
                dataset_path=dataset_result.dataset_path,
            )
            datasets[symbol] = {
                **dataset_result.to_payload(),
                "dataset_version": FOUR_BAR_DATASET_VERSION,
                "source": "local_binance_vision_archive",
                "archive_root": str(archive_root),
                "start_month": start_month,
                "end_month": end_month,
            }
            specs[symbol] = {
                "spec_path": str(spec_path),
                "spec_sha256": _file_sha256(spec_path),
                "base_config_path": str(base_config_path),
                "dataset_path": str(dataset_result.dataset_path),
            }
            records.append(
                {
                    "symbol": symbol,
                    "row_count": int(dataset_result.row_count),
                    "dataset_path": str(dataset_result.dataset_path),
                    "manifest_path": str(dataset_result.manifest_path),
                    "base_intervals": dataset_manifest.get("base_intervals") or {},
                    "archive_period_start": start_month,
                    "archive_period_end": end_month,
                    "ready_for_matrix_replay": int(dataset_result.row_count) >= 150,
                    "promotion_ready": False,
                    "research_only": True,
                    "observe_only": True,
                }
            )
        except Exception as exc:
            errors.append({"symbol": symbol, "error": f"{type(exc).__name__}: {exc}"})

    _write_archive_matrix_command(
        matrix_command_path,
        specs=specs,
        output_dir=output_dir,
        workers=matrix_workers,
    )
    matrix_execution = _archive_matrix_execution_state(
        output_dir=output_dir,
        matrix_command_path=matrix_command_path,
        symbols=tuple(specs.keys()),
        force=force,
    )
    summary_json_path = output_dir / "four_bar_archive_mapping_summary.json"
    summary_payload = {
        "summary_version": FOUR_BAR_ARCHIVE_MAPPING_MANIFEST_VERSION,
        "archive_mapping_version": FOUR_BAR_ARCHIVE_MAPPING_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "phase_selected": "map_existing_larger_local_btc_eth_archive",
        "venue_intake_design_implemented": False,
        "archive_root": str(archive_root),
        "start_month": start_month,
        "end_month": end_month,
        "sample_rows_per_interval": int(sample_rows_per_interval),
        "records": records,
        "errors": errors,
        "matrix_replay_command_path": str(matrix_command_path),
        "matrix_execution": matrix_execution,
        "next_step": {
            "decision": "inspect_archive_backed_four_bar_validation_matrix"
            if matrix_execution.get("status") == "completed"
            else "run_archive_backed_four_bar_validation_matrix",
            "reason": "matrix_replay_completed_with_research_boundary_checks"
            if matrix_execution.get("status") == "completed"
            else "archive_mapping_writes_datasets_and_specs_only; matrix_execution_can_be_long",
        },
    }
    summary_json_path.write_text(_canonical_json(summary_payload, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "manifest_version": FOUR_BAR_ARCHIVE_MAPPING_MANIFEST_VERSION,
        "experiment_manifest_version": FOUR_BAR_ARCHIVE_MAPPING_MANIFEST_VERSION,
        "archive_mapping_version": FOUR_BAR_ARCHIVE_MAPPING_VERSION,
        "validation_version": FOUR_BAR_KNN_LARGER_VALIDATION_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "started_at_ms": started_at_ms,
        "runtime_seconds": round(time.perf_counter() - started_perf, 6),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "candidate_pack_written": False,
        "paper_artifact_written": False,
        "live_artifact_written": False,
        "order_placement_used": False,
        "position_sizing_used": False,
        "runtime_mode_changed": False,
        "phase_selected": "map_existing_larger_local_btc_eth_archive",
        "venue_intake_design_implemented": False,
        "archive_root": str(archive_root),
        "start_month": start_month,
        "end_month": end_month,
        "sample_rows_per_interval": int(sample_rows_per_interval),
        "matrix_workers": int(matrix_workers),
        "force": bool(force),
        "datasets": datasets,
        "specs": specs,
        "records": records,
        "errors": errors,
        "summary_json_path": str(summary_json_path),
        "command_path": str(command_path),
        "matrix_command_path": str(matrix_command_path),
        "matrix_execution": matrix_execution,
    }
    boundary_report = build_research_boundary_report(experiment_manifest=manifest)
    manifest["research_boundary"] = {
        "passed": bool(boundary_report["passed"]),
        "blockers": boundary_report["blockers"],
    }
    manifest_path = output_dir / "four_bar_archive_mapping_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return FourBarArchiveMappingResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        summary_json_path=summary_json_path,
        command_path=command_path,
        matrix_command_path=matrix_command_path,
    )


def _archive_matrix_execution_state(
    *,
    output_dir: Path,
    matrix_command_path: Path,
    symbols: tuple[str, ...],
    force: bool,
) -> dict[str, Any]:
    if force:
        return {
            "status": "not_run",
            "reason": "force_dataset_refresh_requested; replay_matrix_after_mapping",
            "command_path": str(matrix_command_path),
        }
    symbol_reports: dict[str, dict[str, Any]] = {}
    completed = 0
    for symbol in symbols:
        matrix_dir = output_dir / "matrices" / symbol.lower()
        manifest_path = matrix_dir / "experiment_manifest.json"
        summary_path = matrix_dir / "experiment_summary.csv"
        if not manifest_path.is_file():
            symbol_reports[symbol] = {
                "status": "not_run",
                "experiment_manifest_path": str(manifest_path),
                "summary_path": str(summary_path),
            }
            continue
        manifest = _read_json(manifest_path)
        experiments = manifest.get("experiments")
        experiment_rows = experiments if isinstance(experiments, list) else []
        passed = sum(1 for row in experiment_rows if isinstance(row, Mapping) and row.get("status") == "passed")
        failed = sum(1 for row in experiment_rows if isinstance(row, Mapping) and row.get("status") != "passed")
        boundary = manifest.get("research_boundary") if isinstance(manifest.get("research_boundary"), Mapping) else {}
        symbol_reports[symbol] = {
            "status": "completed",
            "experiment_manifest_path": str(manifest_path),
            "summary_path": str(summary_path),
            "experiment_count": int(len(experiment_rows)),
            "passed_count": int(passed),
            "failed_count": int(failed),
            "research_boundary_passed": bool(boundary.get("passed")),
            "promotion_ready": bool(manifest.get("promotion_ready")),
        }
        completed += 1
    if completed == len(symbol_reports) and symbol_reports:
        status = "completed"
        reason = "all_symbol_matrix_manifests_detected"
    elif completed:
        status = "partial"
        reason = "some_symbol_matrix_manifests_detected"
    else:
        status = "not_run"
        reason = "potentially_long_hmm_knn_walk_forward_compute_left_as_replay_command"
    return {
        "status": status,
        "reason": reason,
        "command_path": str(matrix_command_path),
        "symbols": symbol_reports,
        "interpretation_scope": "entry_quality_only_same_entry_fixed_four_bar_labels_exit_quality_separate",
        "profitability_claim": False,
        "promotion_ready": False,
    }


def run_four_bar_knn_larger_validation(
    *,
    output_dir: Path,
    btc_fixture_root: Path | None = None,
    eth_fixture_root: Path | None = None,
    btc_base_config_path: Path | None = None,
    eth_base_config_path: Path | None = None,
    sample_rows_per_interval: int = FOUR_BAR_KNN_LARGER_VALIDATION_DEFAULT_SAMPLE_ROWS_PER_INTERVAL,
    workers: int = 1,
    force: bool = False,
    write_monitoring: bool = True,
    skip_matrix: bool = False,
    require_public_archive_ready: bool = True,
) -> FourBarKnnLargerValidationResult:
    """Run the WPR106-76 selected no-RSI four-bar larger validation packet."""

    if sample_rows_per_interval < 20:
        raise ValueError("sample_rows_per_interval must be at least 20")
    if workers < 1:
        raise ValueError("workers must be at least 1")

    repo_root = _repo_root()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at_ms = int(time.time() * 1000)
    started_perf = time.perf_counter()

    btc_fixture_root = (btc_fixture_root or repo_root / "data" / "research" / "fixtures" / "btcusdt_public_archive_multi_window_v1").expanduser().resolve()
    eth_fixture_root = (eth_fixture_root or repo_root / "data" / "research" / "fixtures" / "ethusdt_public_archive_multi_window_v1").expanduser().resolve()
    btc_base_config_path = (btc_base_config_path or repo_root / "configs" / "research" / "no_rsi_knn_four_bar_btcusdt_r106_v1.json").expanduser().resolve()
    eth_base_config_path = (eth_base_config_path or repo_root / "configs" / "research" / "no_rsi_knn_four_bar_ethusdt_r106_v1.json").expanduser().resolve()

    command_path = output_dir / "run_four_bar_knn_larger_validation.ps1"
    _write_replay_command(
        command_path,
        output_dir=output_dir,
        btc_fixture_root=btc_fixture_root,
        eth_fixture_root=eth_fixture_root,
        sample_rows_per_interval=sample_rows_per_interval,
        workers=workers,
        force=force,
        write_monitoring=write_monitoring,
        skip_matrix=skip_matrix,
    )

    datasets: dict[str, dict[str, Any]] = {}
    specs: dict[str, dict[str, Any]] = {}
    matrices: dict[str, dict[str, Any]] = {}
    summary_records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for symbol, fixture_root, base_config_path in (
        ("BTCUSDT", btc_fixture_root, btc_base_config_path),
        ("ETHUSDT", eth_fixture_root, eth_base_config_path),
    ):
        try:
            dataset_result = _build_or_reuse_validation_dataset(
                fixture_root=fixture_root,
                output_dir=output_dir / "datasets",
                symbol=symbol,
                sample_rows_per_interval=sample_rows_per_interval,
                force=force,
                require_public_archive_ready=require_public_archive_ready,
            )
            datasets[symbol] = {
                **dataset_result.to_payload(),
                "fixture_root": str(fixture_root),
                "dataset_version": FOUR_BAR_DATASET_VERSION,
            }
            spec_path = _write_validation_spec(
                output_dir=output_dir / "specs",
                symbol=symbol,
                base_config_path=base_config_path,
                dataset_path=dataset_result.dataset_path,
            )
            specs[symbol] = {
                "spec_path": str(spec_path),
                "spec_sha256": _file_sha256(spec_path),
                "base_config_path": str(base_config_path),
                "dataset_path": str(dataset_result.dataset_path),
            }
            if skip_matrix:
                matrices[symbol] = {
                    "status": "skipped",
                    "reason": "skip_matrix_requested",
                    "spec_path": str(spec_path),
                    "dataset_path": str(dataset_result.dataset_path),
                }
                continue

            matrix_result = run_hmm_knn_experiment_matrix(
                spec_path=spec_path,
                dataset_path=dataset_result.dataset_path,
                output_dir=output_dir / "matrices" / symbol.lower(),
                cache_dir=output_dir / "cache" / symbol.lower(),
                force=force,
                write_monitoring=write_monitoring,
                max_workers=workers,
            )
            matrix_manifest = _read_json(matrix_result.manifest_path)
            matrices[symbol] = {
                "status": str(matrix_manifest.get("overall_status") or "unknown"),
                "manifest_path": str(matrix_result.manifest_path),
                "summary_path": str(matrix_result.summary_path),
                "output_dir": str(matrix_result.output_dir),
                "experiment_count": len(matrix_manifest.get("experiments") or []),
                "runtime_seconds": matrix_manifest.get("runtime_seconds"),
            }
            summary_records.extend(_analysis_records_for_matrix(symbol=symbol, matrix_manifest_path=matrix_result.manifest_path))
        except Exception as exc:
            errors.append({"symbol": symbol, "error": f"{type(exc).__name__}: {exc}"})
            matrices[symbol] = {"status": "failed", "error": errors[-1]["error"]}

    summary_json_path = output_dir / "four_bar_knn_larger_validation_summary.json"
    summary_csv_path = output_dir / "four_bar_knn_larger_validation_summary.csv"
    summary_payload = {
        "summary_version": FOUR_BAR_KNN_LARGER_VALIDATION_SUMMARY_VERSION,
        "validation_version": FOUR_BAR_KNN_LARGER_VALIDATION_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "decision_gates": dict(FOUR_BAR_KNN_LARGER_VALIDATION_GATE),
        "cost_stress_bps": list(FOUR_BAR_KNN_LARGER_VALIDATION_COST_STRESS_BPS),
        "records": summary_records,
        "gate_pass_records": [record for record in summary_records if record.get("passes_larger_validation_gate") is True],
        "next_phase": _next_phase(summary_records, skip_matrix=skip_matrix, errors=errors),
    }
    summary_json_path.write_text(_canonical_json(summary_payload, indent=2) + "\n", encoding="utf-8")
    _write_summary_csv(summary_csv_path, summary_records)

    manifest = {
        "manifest_version": FOUR_BAR_KNN_LARGER_VALIDATION_MANIFEST_VERSION,
        "experiment_manifest_version": FOUR_BAR_KNN_LARGER_VALIDATION_MANIFEST_VERSION,
        "validation_version": FOUR_BAR_KNN_LARGER_VALIDATION_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "started_at_ms": started_at_ms,
        "runtime_seconds": round(time.perf_counter() - started_perf, 6),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "candidate_pack_written": False,
        "paper_artifact_written": False,
        "live_artifact_written": False,
        "order_placement_used": False,
        "position_sizing_used": False,
        "runtime_mode_changed": False,
        "sample_rows_per_interval": int(sample_rows_per_interval),
        "workers": int(workers),
        "force": bool(force),
        "write_monitoring": bool(write_monitoring),
        "skip_matrix": bool(skip_matrix),
        "require_public_archive_ready": bool(require_public_archive_ready),
        "selected_validation_rows": _selected_validation_rows_payload(),
        "datasets": datasets,
        "specs": specs,
        "matrices": matrices,
        "errors": errors,
        "summary_json_path": str(summary_json_path),
        "summary_csv_path": str(summary_csv_path),
        "command_path": str(command_path),
        "next_phase": summary_payload["next_phase"],
    }
    boundary_report = build_research_boundary_report(experiment_manifest=manifest)
    manifest["research_boundary"] = {
        "passed": bool(boundary_report["passed"]),
        "blockers": boundary_report["blockers"],
    }
    if not research_boundary_passed(boundary_report):
        manifest["errors"].append({"symbol": "ALL", "error": f"research boundary failed: {boundary_report['blockers']}"})
    manifest_path = output_dir / "four_bar_knn_larger_validation_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return FourBarKnnLargerValidationResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        summary_json_path=summary_json_path,
        summary_csv_path=summary_csv_path,
        command_path=command_path,
    )


def _build_or_reuse_validation_dataset(
    *,
    fixture_root: Path,
    output_dir: Path,
    symbol: str,
    sample_rows_per_interval: int,
    force: bool,
    require_public_archive_ready: bool,
) -> FourBarDatasetBuildResult:
    dataset_name = f"{symbol.lower()}_no_rsi_four_bar_validation_{int(sample_rows_per_interval)}_dataset.parquet"
    dataset_path = output_dir / dataset_name
    manifest_path = output_dir / f"{Path(dataset_name).stem}_manifest.json"
    if not force and dataset_path.exists() and manifest_path.exists():
        manifest = _read_json(manifest_path)
        if (
            manifest.get("research_only") is True
            and manifest.get("observe_only") is True
            and manifest.get("promotion_ready") is False
            and str(manifest.get("symbol") or "").upper() == symbol.upper()
            and int(manifest.get("row_count") or 0) > 0
        ):
            return FourBarDatasetBuildResult(
                dataset_path=dataset_path,
                manifest_path=manifest_path,
                row_count=int(manifest["row_count"]),
                dataset_sha256=str(manifest.get("dataset_sha256") or _file_sha256(dataset_path)),
                manifest_sha256=_file_sha256(manifest_path),
            )

    return build_four_bar_knn_dataset_from_fixture(
        fixture_root=fixture_root,
        output_dir=output_dir,
        symbol=symbol,
        base_intervals=("15m", "1h"),
        dataset_name=dataset_name,
        max_rows_per_interval=sample_rows_per_interval,
        require_public_archive_ready=require_public_archive_ready,
    )


def _write_validation_spec(
    *,
    output_dir: Path,
    symbol: str,
    base_config_path: Path,
    dataset_path: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    symbol_lower = symbol.lower()
    spec_path = output_dir / f"{symbol_lower}_four_bar_knn_larger_validation_spec.json"
    payload = {
        "name": f"WPR106-77 {symbol} no-RSI four-bar larger validation",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "base_config_path": str(base_config_path),
        "dataset_path": str(dataset_path),
        "validation_version": FOUR_BAR_KNN_LARGER_VALIDATION_VERSION,
        "candidate_matrix_bounds": {
            "broad_grid_allowed": False,
            "selected_from_wpr106_76": True,
            "no_rsi_core": True,
            "unimplemented_venue_dependency_allowed": False,
        },
        "experiments": _validation_experiments(symbol),
    }
    spec_path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")
    return spec_path


def _validation_experiments(symbol: str) -> list[dict[str, Any]]:
    symbol_lower = symbol.lower()
    if symbol.upper() == "BTCUSDT":
        return [
            _experiment(
                symbol_lower=symbol_lower,
                name="BTC 15m 1h price vol flow Lorentzian inverse compatible",
                slug="btc-validation-15m-price-vol-flow-lorentzian-inverse-compatible",
                run_order=1,
                base_interval="15m",
                resolved_horizon="1h",
                feature_pack="price_vol_flow_no_rsi",
                distance="lorentzian",
                primary_k=21,
                weighting="inverse_distance",
                regime_match_mode="compatible",
                same_regime_only=False,
                allow_cross_regime_fallback=True,
                validation_selectors=["top_score_50_per_split", "top_score_40_per_split", "primary_knn"],
            ),
            _experiment(
                symbol_lower=symbol_lower,
                name="BTC 1h 4h price vol flow Lorentzian inverse compatible",
                slug="btc-validation-1h-price-vol-flow-lorentzian-inverse-compatible",
                run_order=2,
                base_interval="1h",
                resolved_horizon="4h",
                feature_pack="price_vol_flow_no_rsi",
                distance="lorentzian",
                primary_k=48,
                weighting="inverse_distance",
                regime_match_mode="compatible",
                same_regime_only=False,
                allow_cross_regime_fallback=True,
                validation_selectors=["primary_knn", "top_score_50_per_split"],
            ),
        ]
    if symbol.upper() == "ETHUSDT":
        return [
            _experiment(
                symbol_lower=symbol_lower,
                name="ETH 15m 1h price vol flow Lorentzian inverse compatible",
                slug="eth-validation-15m-price-vol-flow-lorentzian-inverse-compatible",
                run_order=1,
                base_interval="15m",
                resolved_horizon="1h",
                feature_pack="price_vol_flow_no_rsi",
                distance="lorentzian",
                primary_k=21,
                weighting="inverse_distance",
                regime_match_mode="compatible",
                same_regime_only=False,
                allow_cross_regime_fallback=True,
                validation_selectors=["transparent_trend_vol", "top_score_50_per_split", "primary_knn"],
            ),
            _experiment(
                symbol_lower=symbol_lower,
                name="ETH 1h 4h price path Lorentzian uniform same",
                slug="eth-validation-1h-price-path-lorentzian-uniform-same",
                run_order=2,
                base_interval="1h",
                resolved_horizon="4h",
                feature_pack="price_close_path_4bar",
                distance="lorentzian",
                primary_k=32,
                weighting="uniform",
                regime_match_mode="same",
                same_regime_only=True,
                allow_cross_regime_fallback=False,
                validation_selectors=["top_score_50_flow_aligned", "primary_knn"],
            ),
        ]
    raise ValueError("symbol must be BTCUSDT or ETHUSDT")


def _experiment(
    *,
    symbol_lower: str,
    name: str,
    slug: str,
    run_order: int,
    base_interval: str,
    resolved_horizon: str,
    feature_pack: str,
    distance: str,
    primary_k: int,
    weighting: str,
    regime_match_mode: str,
    same_regime_only: bool,
    allow_cross_regime_fallback: bool,
    validation_selectors: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "slug": slug,
        "owning_agent": "KNN",
        "run_order": run_order,
        "config_data_change": f"{symbol_lower} no-RSI larger validation row selected from WPR106-76 compact evidence.",
        "expected_metric_movement": "Scale compact lead on a larger deterministic fixture sample without changing exits or venue inputs.",
        "risk": "Still research-only sampled validation, not candidate-pack or promotion evidence.",
        "requires_new_data": False,
        "can_run_on_current_artifacts": True,
        "validation_selectors": validation_selectors,
        "four_bar_horizon": {
            "base_interval": base_interval,
            "horizon_bars": 4,
            "resolved_horizon": resolved_horizon,
            "diagnostic_only": False,
        },
        "comparison_baselines": ["no_trade", "fixed_four_bar_holding", "transparent_trend_vol"],
        "mutations": {
            "knn.feature_pack": feature_pack,
            "knn.distance": distance,
            "knn.primary_k": primary_k,
            "knn.neighbor_weighting": [weighting],
            "knn.primary_weighting": weighting,
            "knn.regime_match_mode": regime_match_mode,
            "knn.same_regime_only": same_regime_only,
            "knn.allow_cross_regime_fallback": allow_cross_regime_fallback,
            "labels.primary_horizon": resolved_horizon,
        },
    }


def _analysis_records_for_matrix(*, symbol: str, matrix_manifest_path: Path) -> list[dict[str, Any]]:
    matrix_manifest = _read_json(matrix_manifest_path)
    records: list[dict[str, Any]] = []
    for experiment in matrix_manifest.get("experiments") or []:
        if experiment.get("status") != "passed" or not experiment.get("artifact_manifest_path"):
            continue
        artifact_manifest_path = Path(str(experiment["artifact_manifest_path"]))
        artifact_manifest = _read_json(artifact_manifest_path)
        meta_path = _resolve_manifest_path(artifact_manifest_path, artifact_manifest["meta_predictions_path"])
        metrics_path = _resolve_manifest_path(artifact_manifest_path, artifact_manifest["metrics_path"])
        meta = pd.read_parquet(meta_path)
        metrics = _read_json(metrics_path)
        feature_pack = str(artifact_manifest.get("feature_pack") or "")
        base_interval = str((experiment.get("four_bar_horizon") or {}).get("base_interval") or _mode(meta.get("four_bar_base_interval")) or "")
        resolved_horizon = str((experiment.get("four_bar_horizon") or {}).get("resolved_horizon") or artifact_manifest.get("primary_label_horizon") or "")
        slug = str(experiment.get("slug") or artifact_manifest.get("plan_version") or artifact_manifest_path.parent.name)

        accepted = meta.loc[meta.get("accepted_by_knn", pd.Series(False, index=meta.index)).astype(bool)].copy()
        records.append(
            _metrics_record(
                symbol=symbol,
                slug=slug,
                base_interval=base_interval,
                resolved_horizon=resolved_horizon,
                selector="accepted_by_knn",
                label="primary_knn",
                frame=accepted,
                source_frame=meta,
                feature_pack=feature_pack,
                artifact_manifest_path=artifact_manifest_path,
                metrics=metrics,
            )
        )

        selectors = experiment.get("validation_selectors") or []
        if "top_score_50_per_split" in selectors:
            records.append(
                _metrics_record(
                    symbol=symbol,
                    slug=slug,
                    base_interval=base_interval,
                    resolved_horizon=resolved_horizon,
                    selector="top_expected_net_per_split_50",
                    label="top_score_50_per_split",
                    frame=_top_score_rows(meta, per_split=50),
                    source_frame=meta,
                    feature_pack=feature_pack,
                    artifact_manifest_path=artifact_manifest_path,
                )
            )
        if "top_score_40_per_split" in selectors:
            records.append(
                _metrics_record(
                    symbol=symbol,
                    slug=slug,
                    base_interval=base_interval,
                    resolved_horizon=resolved_horizon,
                    selector="top_expected_net_per_split_40",
                    label="top_score_40_per_split",
                    frame=_top_score_rows(meta, per_split=40),
                    source_frame=meta,
                    feature_pack=feature_pack,
                    artifact_manifest_path=artifact_manifest_path,
                )
            )
        if "top_score_50_flow_aligned" in selectors:
            records.append(
                _metrics_record(
                    symbol=symbol,
                    slug=slug,
                    base_interval=base_interval,
                    resolved_horizon=resolved_horizon,
                    selector="top_expected_net_flow_aligned_50",
                    label="top_score_50_flow_aligned",
                    frame=_top_score_rows(meta, per_split=50, flow_alignment="aligned"),
                    source_frame=meta,
                    feature_pack=feature_pack,
                    artifact_manifest_path=artifact_manifest_path,
                )
            )
        if "transparent_trend_vol" in selectors:
            records.append(
                _metrics_record(
                    symbol=symbol,
                    slug=slug,
                    base_interval=base_interval,
                    resolved_horizon=resolved_horizon,
                    selector="slope_side_atr_20_90_median_abs_slope",
                    label="transparent_trend_vol",
                    frame=_transparent_trend_vol_rows(meta),
                    source_frame=meta,
                    feature_pack="transparent_no_rsi_trend_vol",
                    artifact_manifest_path=artifact_manifest_path,
                )
            )
    return records


def _metrics_record(
    *,
    symbol: str,
    slug: str,
    base_interval: str,
    resolved_horizon: str,
    selector: str,
    label: str,
    frame: pd.DataFrame,
    source_frame: pd.DataFrame,
    feature_pack: str,
    artifact_manifest_path: Path,
    metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selected = frame.copy()
    if "validation_split" not in selected.columns:
        selected["validation_split"] = _split_series(selected)
    pnl = _realized_pnl(selected, total_cost_bps=10.0)
    split_column = _split_column(selected)
    split_net_returns = _split_values(selected, pnl, split_column=split_column)
    split_trade_counts = _split_counts(selected, split_column=split_column)
    gross_profit = float(pnl[pnl > 0].sum()) if len(pnl) else 0.0
    gross_loss = abs(float(pnl[pnl < 0].sum())) if len(pnl) else 0.0
    profit_factor = None if gross_loss == 0.0 and gross_profit == 0.0 else (math.inf if gross_loss == 0.0 else gross_profit / gross_loss)
    net_return = float(pnl.sum()) if len(pnl) else 0.0
    trade_count = int(len(selected))
    cost_survived = sum(1 for cost_bps in FOUR_BAR_KNN_LARGER_VALIDATION_COST_STRESS_BPS if float(_realized_pnl(selected, total_cost_bps=cost_bps).sum()) > 0.0)
    cost_total = len(FOUR_BAR_KNN_LARGER_VALIDATION_COST_STRESS_BPS)
    direction = selected.get("direction", pd.Series([], dtype=str)).astype(str).str.lower()
    split_abs = [abs(float(value)) for value in split_net_returns.values()]
    total_abs = sum(split_abs)
    max_split_share = max(split_abs) / total_abs if total_abs > 0.0 else 0.0
    min_trades_per_split = min(split_trade_counts.values()) if split_trade_counts else 0
    positive_split_checks = sum(1 for value in split_net_returns.values() if float(value) > 0.0)
    split_count = len(split_net_returns)
    source_row_count = int(len(source_frame))
    no_rsi_core = feature_pack in {"price_vol_flow_no_rsi", "price_close_path_4bar", "transparent_no_rsi_trend_vol"}
    unimplemented_venue_dependency = feature_pack == "perp_context_no_rsi"
    passes_gate = (
        trade_count >= FOUR_BAR_KNN_LARGER_VALIDATION_GATE["min_trade_count"]
        and (net_return / trade_count if trade_count else 0.0) > 0.0
        and net_return > 0.0
        and (profit_factor is not None and profit_factor > FOUR_BAR_KNN_LARGER_VALIDATION_GATE["min_profit_factor"])
        and min_trades_per_split >= FOUR_BAR_KNN_LARGER_VALIDATION_GATE["min_trades_per_split"]
        and positive_split_checks >= FOUR_BAR_KNN_LARGER_VALIDATION_GATE["min_positive_split_checks"]
        and (cost_survived / max(cost_total, 1)) >= FOUR_BAR_KNN_LARGER_VALIDATION_GATE["min_cost_stress_survival_rate"]
        and max_split_share <= FOUR_BAR_KNN_LARGER_VALIDATION_GATE["max_single_split_pnl_share"]
        and no_rsi_core
        and not unimplemented_venue_dependency
    )
    return {
        "symbol": symbol,
        "slug": slug,
        "base_interval": base_interval,
        "resolved_horizon": resolved_horizon,
        "selector": selector,
        "label": label,
        "feature_pack": feature_pack,
        "source_row_count": source_row_count,
        "trade_count": trade_count,
        "expectancy_after_cost": float(net_return / trade_count) if trade_count else 0.0,
        "net_return": net_return,
        "profit_factor": profit_factor,
        "positive_split_checks": positive_split_checks,
        "split_count": split_count,
        "min_trades_per_split": int(min_trades_per_split),
        "max_single_split_pnl_share": float(max_split_share),
        "cost_stress_survival_rate": float(cost_survived / max(cost_total, 1)),
        "cost_stress_survived": int(cost_survived),
        "cost_stress_total": int(cost_total),
        "long_count": int((direction == "long").sum()),
        "short_count": int((direction == "short").sum()),
        "split_net_returns": split_net_returns,
        "split_trade_counts": split_trade_counts,
        "no_rsi_core": bool(no_rsi_core),
        "unimplemented_venue_dependency": bool(unimplemented_venue_dependency),
        "passes_larger_validation_gate": bool(passes_gate),
        "artifact_manifest_path": str(artifact_manifest_path),
        "metrics_comparison": _primary_metrics_digest(metrics) if label == "primary_knn" and metrics is not None else None,
    }


def _top_score_rows(meta: pd.DataFrame, *, per_split: int, flow_alignment: str | None = None) -> pd.DataFrame:
    if meta.empty:
        return meta.copy()
    frame = meta.loc[meta.get("accepted_by_knn", pd.Series(False, index=meta.index)).astype(bool)].copy()
    if flow_alignment:
        signed = pd.to_numeric(frame.get("primary_signed_imbalance_ratio"), errors="coerce").fillna(0.0)
        direction = frame.get("direction", pd.Series("", index=frame.index)).astype(str).str.lower()
        aligned = ((direction == "long") & (signed >= 0.0)) | ((direction == "short") & (signed <= 0.0))
        if flow_alignment == "aligned":
            frame = frame.loc[aligned].copy()
        elif flow_alignment == "contrarian":
            frame = frame.loc[~aligned].copy()
        else:
            raise ValueError("flow_alignment must be aligned, contrarian, or None")
    if frame.empty:
        return frame
    frame["validation_split"] = _split_series(frame)
    score = pd.to_numeric(frame.get("expected_net_return_after_costs"), errors="coerce").fillna(-np.inf)
    frame["_validation_score"] = score
    pieces = []
    for _, group in frame.sort_values(["validation_split", "_validation_score"], ascending=[True, False]).groupby("validation_split", sort=True):
        pieces.append(group.head(per_split))
    return pd.concat(pieces, ignore_index=True).drop(columns=["_validation_score"], errors="ignore") if pieces else frame.head(0).copy()


def _transparent_trend_vol_rows(meta: pd.DataFrame) -> pd.DataFrame:
    if meta.empty:
        return meta.copy()
    frame = meta.copy()
    frame["validation_split"] = _split_series(frame)
    slope = pd.to_numeric(frame.get("directional_slope_atr"), errors="coerce").fillna(0.0)
    atr_pct = pd.to_numeric(frame.get("atr_percentile"), errors="coerce").fillna(0.5)
    direction = frame.get("direction", pd.Series("", index=frame.index)).astype(str).str.lower()
    side_aligned = ((direction == "long") & (slope > 0.0)) | ((direction == "short") & (slope < 0.0))
    atr_ok = (atr_pct >= 0.20) & (atr_pct <= 0.90)
    abs_slope = slope.abs()
    median_by_split = frame.assign(_abs_slope=abs_slope).groupby("validation_split")["_abs_slope"].transform("median")
    selected = frame.loc[side_aligned & atr_ok & (abs_slope >= median_by_split)].copy()
    return selected


def _split_series(frame: pd.DataFrame) -> pd.Series:
    if "walk_forward_split" in frame.columns:
        return pd.to_numeric(frame["walk_forward_split"], errors="coerce").fillna(0).astype(int)
    if frame.empty:
        return pd.Series([], dtype=int)
    ordered = frame.sort_values("signal_bar_time_ms" if "signal_bar_time_ms" in frame.columns else frame.index.name or frame.columns[0])
    split_ids = pd.Series(np.arange(len(ordered)) * 4 // max(len(ordered), 1), index=ordered.index, dtype=int)
    return split_ids.reindex(frame.index).fillna(0).astype(int)


def _split_column(frame: pd.DataFrame) -> str:
    if "validation_split" in frame.columns:
        return "validation_split"
    if "walk_forward_split" in frame.columns:
        return "walk_forward_split"
    return "validation_split"


def _split_values(frame: pd.DataFrame, pnl: pd.Series, *, split_column: str) -> dict[str, float]:
    if frame.empty:
        return {}
    split_ids = pd.to_numeric(frame.get(split_column, _split_series(frame)), errors="coerce").fillna(0).astype(int)
    rows = pd.DataFrame({"split": split_ids, "pnl": pnl})
    return {str(int(split_id)): float(group["pnl"].sum()) for split_id, group in rows.groupby("split", sort=True)}


def _split_counts(frame: pd.DataFrame, *, split_column: str) -> dict[str, int]:
    if frame.empty:
        return {}
    split_ids = pd.to_numeric(frame.get(split_column, _split_series(frame)), errors="coerce").fillna(0).astype(int)
    counts = split_ids.value_counts().sort_index()
    return {str(int(split_id)): int(value) for split_id, value in counts.items()}


def _realized_pnl(frame: pd.DataFrame, *, total_cost_bps: float) -> pd.Series:
    if frame.empty:
        return pd.Series([], dtype=float)
    if "gross_return" in frame.columns:
        gross = pd.to_numeric(frame["gross_return"], errors="coerce").fillna(0.0).astype(float)
    else:
        gross = pd.to_numeric(frame.get("label_pnl_multiple"), errors="coerce").fillna(0.0).astype(float)
    if "funding_paid_or_received" in frame.columns:
        funding = pd.to_numeric(frame["funding_paid_or_received"], errors="coerce").fillna(0.0).astype(float)
    else:
        funding = pd.Series([0.0] * len(frame), index=frame.index, dtype=float)
    return gross - (float(total_cost_bps) / 10000.0) + funding


def _primary_metrics_digest(metrics: Mapping[str, Any]) -> dict[str, Any]:
    comparison = metrics.get("comparison") if isinstance(metrics.get("comparison"), Mapping) else {}
    primary = comparison.get("hmm_regime_lorentzian_knn") if isinstance(comparison.get("hmm_regime_lorentzian_knn"), Mapping) else {}
    return {
        "trade_count": primary.get("trade_count"),
        "expectancy_after_cost": primary.get("expectancy_after_cost"),
        "profit_factor": primary.get("profit_factor"),
        "realized_pnl_total": primary.get("realized_pnl_total"),
    }


def _next_phase(records: list[dict[str, Any]], *, skip_matrix: bool, errors: list[dict[str, Any]]) -> dict[str, Any]:
    if skip_matrix:
        return {
            "decision": "larger_validation_pending",
            "reason": "matrix_execution_skipped",
        }
    if errors and not records:
        return {
            "decision": "blocked",
            "reason": "validation_matrix_failed",
            "errors": errors,
        }
    passed = [record for record in records if record.get("passes_larger_validation_gate") is True]
    primary = [record for record in passed if str(record.get("label")) == "primary_knn"]
    sparse = [record for record in passed if str(record.get("label")).startswith("top_score")]
    transparent = [record for record in passed if str(record.get("label")) == "transparent_trend_vol"]
    if primary:
        return {
            "decision": "larger_validation_followup",
            "reason": "primary_knn_row_survived_larger_validation_gate",
            "gate_pass_count": len(passed),
            "primary_gate_pass_count": len(primary),
        }
    if sparse:
        return {
            "decision": "sparse_entry_filter_packet",
            "reason": "top_score_selection_survived_but_primary_knn_did_not",
            "gate_pass_count": len(passed),
            "sparse_gate_pass_count": len(sparse),
        }
    if transparent:
        return {
            "decision": "transparent_baseline_review",
            "reason": "transparent_trend_vol_survived_without_knn_gate_pass",
            "gate_pass_count": len(passed),
            "transparent_gate_pass_count": len(transparent),
        }
    return {
        "decision": "venue_intake_feature_packet",
        "reason": "no_no_rsi_knn_or_filter_row_survived_larger_validation_gate",
        "gate_pass_count": 0,
    }


def _selected_validation_rows_payload() -> dict[str, list[dict[str, Any]]]:
    return {
        "BTCUSDT": _validation_experiments("BTCUSDT"),
        "ETHUSDT": _validation_experiments("ETHUSDT"),
    }


def _write_replay_command(
    path: Path,
    *,
    output_dir: Path,
    btc_fixture_root: Path,
    eth_fixture_root: Path,
    sample_rows_per_interval: int,
    workers: int,
    force: bool,
    write_monitoring: bool,
    skip_matrix: bool,
) -> None:
    args = [
        "python",
        "-m",
        "tradingbotsuite.main",
        "run-four-bar-knn-larger-validation",
        "--output-dir",
        _ps_quote(str(output_dir)),
        "--btc-fixture-root",
        _ps_quote(str(btc_fixture_root)),
        "--eth-fixture-root",
        _ps_quote(str(eth_fixture_root)),
        "--sample-rows-per-interval",
        str(int(sample_rows_per_interval)),
        "--workers",
        str(int(workers)),
    ]
    if force:
        args.append("--force")
    if not write_monitoring:
        args.append("--skip-monitor")
    note = "# Full validation command generated by the WPR106-77 runner.\n" if skip_matrix else ""
    path.write_text("$env:PYTHONPATH='src'\n" + note + " ".join(args) + "\n", encoding="utf-8")


def _write_archive_mapping_command(
    path: Path,
    *,
    output_dir: Path,
    archive_root: Path,
    start_month: str,
    end_month: str,
    sample_rows_per_interval: int,
    matrix_workers: int,
    force: bool,
) -> None:
    args = [
        "python",
        "-m",
        "tradingbotsuite.main",
        "map-binance-archive-four-bar-datasets",
        "--output-dir",
        _ps_quote(str(output_dir)),
        "--archive-root",
        _ps_quote(str(archive_root)),
        "--start-month",
        str(start_month),
        "--end-month",
        str(end_month),
        "--sample-rows-per-interval",
        str(int(sample_rows_per_interval)),
        "--matrix-workers",
        str(int(matrix_workers)),
    ]
    if force:
        args.append("--force")
    path.write_text("$env:PYTHONPATH='src'\n" + " ".join(args) + "\n", encoding="utf-8")


def _write_archive_matrix_command(
    path: Path,
    *,
    specs: Mapping[str, Mapping[str, Any]],
    output_dir: Path,
    workers: int,
) -> None:
    lines = ["$env:PYTHONPATH='src'"]
    if not specs:
        lines.append("# No archive-backed specs were written.")
    for symbol, payload in sorted(specs.items()):
        spec_path = payload.get("spec_path")
        dataset_path = payload.get("dataset_path")
        if not spec_path or not dataset_path:
            continue
        symbol_lower = str(symbol).lower()
        lines.append(
            " ".join(
                [
                    "python",
                    "-m",
                    "tradingbotsuite.main",
                    "run-hmm-knn-experiments",
                    "--spec",
                    _ps_quote(str(spec_path)),
                    "--dataset",
                    _ps_quote(str(dataset_path)),
                    "--output-dir",
                    _ps_quote(str(output_dir / "matrices" / symbol_lower)),
                    "--cache-dir",
                    _ps_quote(str(output_dir / "cache" / symbol_lower)),
                    "--workers",
                    str(int(workers)),
                    "--skip-monitor",
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ps_quote(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _write_summary_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "symbol",
        "slug",
        "base_interval",
        "resolved_horizon",
        "selector",
        "label",
        "feature_pack",
        "trade_count",
        "expectancy_after_cost",
        "net_return",
        "profit_factor",
        "positive_split_checks",
        "split_count",
        "min_trades_per_split",
        "max_single_split_pnl_share",
        "cost_stress_survival_rate",
        "cost_stress_survived",
        "cost_stress_total",
        "long_count",
        "short_count",
        "no_rsi_core",
        "unimplemented_venue_dependency",
        "passes_larger_validation_gate",
        "artifact_manifest_path",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key) for key in fieldnames})


def _resolve_manifest_path(manifest_path: Path, raw: object) -> Path:
    path = Path(str(raw))
    if path.is_absolute():
        return path
    candidate = manifest_path.parent / path
    if candidate.exists():
        return candidate
    return path


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _mode(series: Any) -> str | None:
    if series is None:
        return None
    values = pd.Series(series).dropna().astype(str)
    if values.empty:
        return None
    return str(values.mode().iloc[0])


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(payload, indent=indent, separators=(",", ":") if indent is None else None, sort_keys=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
