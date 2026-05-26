from __future__ import annotations

import json
import math
import os
import platform
import subprocess
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from tradingbotsuite.backtesting import cuda_runtime_evidence
from tradingbotsuite.config import AppConfig
from tradingbotsuite.research.live_readiness import research_artifact_boundary_metadata

HARDWARE_UTILIZATION_REPORT_VERSION = "hardware-utilization-study-readiness-v1"
CPU_SATURATION_PROBE_VERSION = "cpu-process-pool-saturation-v1"
GPU_MATRIX_PROBE_VERSION = "cupy-gpu-matrix-throughput-v1"
SATURATION_TARGET_PERCENT = 80.0
DEFAULT_CPU_SECONDS = 3.0
DEFAULT_GPU_SECONDS = 3.0
DEFAULT_MATRIX_SIZE = 1024
MIN_PROBE_SECONDS = 0.1
MAX_CPU_SECONDS = 120.0
MAX_GPU_SECONDS = 120.0
MIN_MATRIX_SIZE = 64
MAX_MATRIX_SIZE = 8192
WINDOWS_PROCESS_POOL_MAX_WORKERS = 61
MAX_EXPLICIT_CPU_WORKERS = 256


@dataclass(frozen=True, slots=True)
class HardwareUtilizationBenchmarkResult:
    output_dir: Path
    report_path: Path


def write_hardware_utilization_report(
    *,
    output_dir: Path | None = None,
    cpu_workers: int | None = None,
    cpu_seconds: float = DEFAULT_CPU_SECONDS,
    gpu_seconds: float = DEFAULT_GPU_SECONDS,
    matrix_size: int = DEFAULT_MATRIX_SIZE,
    app_config: AppConfig | None = None,
) -> HardwareUtilizationBenchmarkResult:
    config = app_config or AppConfig.from_env()
    resolved_output_dir = output_dir or _default_output_dir(config)
    resolved_cpu_seconds = _probe_seconds_value(
        cpu_seconds,
        field_name="cpu_seconds",
        maximum=MAX_CPU_SECONDS,
    )
    resolved_gpu_seconds = _probe_seconds_value(
        gpu_seconds,
        field_name="gpu_seconds",
        maximum=MAX_GPU_SECONDS,
    )
    resolved_matrix_size = _matrix_size_value(matrix_size)

    logical_cpu_count = _logical_cpu_count()
    physical_cpu_count = _physical_cpu_count()
    resolved_workers = _resolve_cpu_workers(
        cpu_workers,
        logical_cpu_count=logical_cpu_count,
        physical_cpu_count=physical_cpu_count,
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    cpu_probe = _run_cpu_saturation_probe(
        workers=resolved_workers,
        logical_cpu_count=logical_cpu_count,
        physical_cpu_count=physical_cpu_count,
        duration_seconds=resolved_cpu_seconds,
    )
    gpu_probe = _run_gpu_matrix_probe(
        matrix_size=resolved_matrix_size,
        duration_seconds=resolved_gpu_seconds,
    )
    recommendations = _build_recommendations(cpu_probe=cpu_probe, gpu_probe=gpu_probe)
    cpu_worker_saturated = bool(
        cpu_probe.get("probe_succeeded") and cpu_probe.get("worker_capacity_saturation_status") == "saturated"
    )
    cpu_logical_saturated = bool(
        cpu_probe.get("probe_succeeded") and cpu_probe.get("logical_capacity_saturation_status") == "saturated"
    )
    report = {
        "hardware_utilization_report_version": HARDWARE_UTILIZATION_REPORT_VERSION,
        **research_artifact_boundary_metadata(),
        "diagnostic_only": True,
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
        "live_config_writes_allowed": False,
        "candidate_acceptance_allowed": False,
        "speed_claimed": False,
        "claim_scope": "local_hardware_saturation_diagnostic_not_live_readiness_or_profit_claim",
        "created_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": _environment_payload(
            logical_cpu_count=logical_cpu_count,
            physical_cpu_count=physical_cpu_count,
        ),
        "cpu_probe": cpu_probe,
        "gpu_probe": gpu_probe,
        "recommendations": recommendations,
        "prolonged_study_readiness": {
            "selected_cpu_saturation_target": "worker_capacity",
            "cpu_worker_saturation_target_met": cpu_worker_saturated,
            "cpu_logical_saturation_target_met": cpu_logical_saturated,
            "ready_for_long_cpu_bound_research": cpu_worker_saturated,
            "ready_for_cuda_diagnostic_research": bool(gpu_probe.get("probe_succeeded")),
            "preferred_backends": recommendations["preferred_backends"],
            "blocking_reasons": recommendations["blocking_reasons"],
            "non_blocking_warnings": recommendations["non_blocking_warnings"],
        },
    }
    report_path = resolved_output_dir / "hardware_utilization_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return HardwareUtilizationBenchmarkResult(output_dir=resolved_output_dir, report_path=report_path)


def _default_output_dir(config: AppConfig) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return Path(config.research.output_dir) / "operator_runs" / "hardware_utilization" / timestamp


def _logical_cpu_count() -> int:
    return int(os.cpu_count() or 1)


def _physical_cpu_count() -> int | None:
    if platform.system().lower() == "windows":
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if completed.returncode == 0:
                value = int(float(completed.stdout.strip()))
                return value if value > 0 else None
        except Exception:
            return None
    return None


def _resolve_cpu_workers(
    cpu_workers: int | None,
    *,
    logical_cpu_count: int,
    physical_cpu_count: int | None,
) -> int:
    explicit_request = cpu_workers is not None
    requested = int(cpu_workers) if explicit_request else int(physical_cpu_count or logical_cpu_count)
    if requested <= 0:
        raise ValueError("cpu_workers must be greater than zero")
    if platform.system().lower() == "windows":
        if requested > WINDOWS_PROCESS_POOL_MAX_WORKERS:
            if explicit_request:
                raise ValueError(f"cpu_workers must be at most {WINDOWS_PROCESS_POOL_MAX_WORKERS} on Windows")
            requested = WINDOWS_PROCESS_POOL_MAX_WORKERS
    elif explicit_request and requested > MAX_EXPLICIT_CPU_WORKERS:
        raise ValueError(f"cpu_workers must be at most {MAX_EXPLICIT_CPU_WORKERS}")
    return max(1, requested)


def _probe_seconds_value(value: float, *, field_name: str, maximum: float) -> float:
    resolved = float(value)
    if not math.isfinite(resolved) or resolved < MIN_PROBE_SECONDS or resolved > maximum:
        raise ValueError(f"{field_name} must be a finite value between {MIN_PROBE_SECONDS:g} and {maximum:g} seconds")
    return resolved


def _matrix_size_value(value: int) -> int:
    resolved = int(value)
    if resolved < MIN_MATRIX_SIZE or resolved > MAX_MATRIX_SIZE:
        raise ValueError(f"matrix_size must be between {MIN_MATRIX_SIZE} and {MAX_MATRIX_SIZE}")
    return resolved


def _run_cpu_saturation_probe(
    *,
    workers: int,
    logical_cpu_count: int,
    physical_cpu_count: int | None,
    duration_seconds: float,
) -> dict[str, Any]:
    resolved_duration = float(duration_seconds)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_cpu_saturation_worker, worker_index, resolved_duration)
                for worker_index in range(workers)
            ]
            for future in as_completed(futures):
                results.append(future.result())
    except Exception as exc:
        wall_seconds = max(time.perf_counter() - started, 1e-9)
        return {
            "probe_version": CPU_SATURATION_PROBE_VERSION,
            "probe_succeeded": False,
            "duration_seconds_requested": resolved_duration,
            "wall_seconds": wall_seconds,
            "active_workers": workers,
            "logical_cpu_count": logical_cpu_count,
            "fallback_reason": "cpu_process_pool_probe_failed",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }
    total_wall_seconds = max(time.perf_counter() - started, 1e-9)
    worker_window_wall_seconds = max((float(item.get("wall_seconds") or 0.0) for item in results), default=total_wall_seconds)
    worker_window_wall_seconds = max(worker_window_wall_seconds, 1e-9)
    sum_worker_cpu_seconds = sum(float(item.get("process_cpu_seconds") or 0.0) for item in results)
    operations = sum(int(item.get("operations") or 0) for item in results)
    worker_capacity_seconds = worker_window_wall_seconds * max(workers, 1)
    logical_capacity_seconds = worker_window_wall_seconds * max(logical_cpu_count, 1)
    worker_capacity_percent = _safe_percent(sum_worker_cpu_seconds, worker_capacity_seconds)
    logical_capacity_percent = _safe_percent(sum_worker_cpu_seconds, logical_capacity_seconds)
    return {
        "probe_version": CPU_SATURATION_PROBE_VERSION,
        "probe_succeeded": True,
        "duration_seconds_requested": resolved_duration,
        "wall_seconds": round(total_wall_seconds, 6),
        "worker_window_wall_seconds": round(worker_window_wall_seconds, 6),
        "process_start_and_dispatch_overhead_seconds": round(max(total_wall_seconds - worker_window_wall_seconds, 0.0), 6),
        "active_workers": int(workers),
        "logical_cpu_count": int(logical_cpu_count),
        "physical_cpu_count": int(physical_cpu_count) if physical_cpu_count is not None else None,
        "worker_results": sorted(results, key=lambda item: int(item.get("worker_index", 0))),
        "sum_worker_cpu_seconds": round(sum_worker_cpu_seconds, 6),
        "worker_capacity_seconds": round(worker_capacity_seconds, 6),
        "logical_capacity_seconds": round(logical_capacity_seconds, 6),
        "process_cpu_percent_of_worker_capacity": worker_capacity_percent,
        "process_cpu_percent_of_logical_capacity": logical_capacity_percent,
        "operations": int(operations),
        "operations_per_worker_window_second": round(operations / worker_window_wall_seconds, 6),
        "operations_per_total_second": round(operations / total_wall_seconds, 6),
        "saturation_target_percent": SATURATION_TARGET_PERCENT,
        "worker_capacity_saturation_status": (
            "saturated" if worker_capacity_percent >= SATURATION_TARGET_PERCENT else "below_target"
        ),
        "logical_capacity_saturation_status": (
            "saturated" if logical_capacity_percent >= SATURATION_TARGET_PERCENT else "below_target"
        ),
        "backend": "concurrent.futures.ProcessPoolExecutor",
        "fallback_reason": "",
    }


def _cpu_saturation_worker(worker_index: int, duration_seconds: float) -> dict[str, Any]:
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    deadline = start_wall + float(duration_seconds)
    operations = 0
    checksum = (int(worker_index) + 1) * 2654435761
    accumulator = 0.0
    while time.perf_counter() < deadline:
        for _ in range(10_000):
            checksum = (checksum * 1664525 + 1013904223) & 0xFFFFFFFF
            accumulator += math.sqrt(float((checksum & 0x3FF) + 1))
        operations += 10_000
    return {
        "worker_index": int(worker_index),
        "wall_seconds": round(time.perf_counter() - start_wall, 6),
        "process_cpu_seconds": round(time.process_time() - start_cpu, 6),
        "operations": int(operations),
        "checksum": int(checksum),
        "accumulator_mod": round(accumulator % 1_000_000.0, 6),
    }


def _run_gpu_matrix_probe(*, matrix_size: int, duration_seconds: float) -> dict[str, Any]:
    runtime_evidence = cuda_runtime_evidence()
    resolved_duration = float(duration_seconds)
    base = {
        "probe_version": GPU_MATRIX_PROBE_VERSION,
        "runtime_evidence": runtime_evidence,
        "matrix_size_requested": int(matrix_size),
        "duration_seconds_requested": resolved_duration,
        "diagnostic_only": True,
        "candidate_acceptance_allowed": False,
        "speed_claimed": False,
    }
    if not bool(runtime_evidence.get("available")):
        return {
            **base,
            "probe_succeeded": False,
            "gpu_execution_status": "fallback_cpu_or_vector_only",
            "fallback_reason": str(runtime_evidence.get("unavailable_reason") or "cuda_runtime_unavailable"),
        }
    cupy = None
    values = left = right = warmup = result = None
    try:
        cupy = _load_cupy()
        resolved_size, size_notes = _resolve_gpu_matrix_size(
            int(matrix_size),
            free_bytes=runtime_evidence.get("memory_free_bytes"),
        )
        with cupy.cuda.Device(0):
            values = cupy.arange(resolved_size * resolved_size, dtype=cupy.float32).reshape(
                resolved_size,
                resolved_size,
            )
            left = (values % cupy.float32(997.0)) / cupy.float32(997.0)
            right = ((values.T + cupy.float32(3.0)) % cupy.float32(991.0)) / cupy.float32(991.0)
            cupy.cuda.Stream.null.synchronize()
            warmup = left @ right
            cupy.cuda.Stream.null.synchronize()
            del warmup
            warmup = None
            iterations = 0
            started = time.perf_counter()
            while True:
                result = left @ right
                iterations += 1
                cupy.cuda.Stream.null.synchronize()
                if time.perf_counter() - started >= resolved_duration:
                    break
            wall_seconds = max(time.perf_counter() - started, 1e-9)
            checksum = float(cupy.asnumpy(result[0, 0])) if result is not None else 0.0
            memory_pool_used = int(cupy.get_default_memory_pool().used_bytes())
            free_bytes, total_bytes = cupy.cuda.Device(0).mem_info
            values = left = right = result = None
            _free_cupy_memory_pools(cupy)
    except Exception as exc:
        values = left = right = warmup = result = None
        if cupy is not None:
            _free_cupy_memory_pools(cupy)
        return {
            **base,
            "probe_succeeded": False,
            "gpu_execution_status": "cuda_matrix_probe_failed",
            "fallback_reason": "cupy_matrix_probe_failed",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }
    flops = 2.0 * float(resolved_size) ** 3 * float(iterations)
    return {
        **base,
        "probe_succeeded": True,
        "gpu_execution_status": "cupy_matrix_probe_executed",
        "fallback_reason": "",
        "matrix_size": int(resolved_size),
        "matrix_size_notes": size_notes,
        "iterations": int(iterations),
        "wall_seconds": round(wall_seconds, 6),
        "approx_flop_count": int(flops),
        "approx_gflops_per_second": round(flops / wall_seconds / 1_000_000_000.0, 6),
        "result_checksum_sample": round(checksum, 6),
        "memory_pool_used_bytes": memory_pool_used,
        "memory_free_bytes_after": int(free_bytes),
        "memory_total_bytes_after": int(total_bytes),
    }


def _load_cupy() -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="CUDA path could not be detected.*",
            category=UserWarning,
        )
        import cupy as cp  # type: ignore[import-not-found]

    return cp


def _free_cupy_memory_pools(cupy: Any) -> None:
    for getter_name in ("get_default_memory_pool", "get_default_pinned_memory_pool"):
        try:
            getattr(cupy, getter_name)().free_all_blocks()
        except Exception:
            continue


def _resolve_gpu_matrix_size(requested_size: int, *, free_bytes: Any) -> tuple[int, list[str]]:
    requested = _matrix_size_value(requested_size)
    notes: list[str] = []
    try:
        free = int(free_bytes)
    except (TypeError, ValueError):
        free = 0
    if free <= 0:
        return requested, notes
    estimated_bytes = requested * requested * 4 * 4
    budget = int(free * 0.35)
    if estimated_bytes <= budget:
        return requested, notes
    capped = max(64, int(math.sqrt(max(budget, 64 * 64 * 4 * 4) / 16.0)))
    notes.append(
        "matrix_size_capped_to_35_percent_of_reported_free_gpu_memory"
        if capped < requested
        else "matrix_size_memory_budget_checked"
    )
    return min(requested, capped), notes


def _safe_percent(numerator: float, denominator: float) -> float:
    return round((float(numerator) / max(float(denominator), 1e-9)) * 100.0, 6)


def _environment_payload(*, logical_cpu_count: int, physical_cpu_count: int | None) -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "logical_cpu_count": int(logical_cpu_count),
        "physical_cpu_count": int(physical_cpu_count) if physical_cpu_count is not None else None,
        "numpy_version": str(np.__version__),
        "thread_environment": {
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
            "NUMEXPR_NUM_THREADS": os.environ.get("NUMEXPR_NUM_THREADS"),
            "VECLIB_MAXIMUM_THREADS": os.environ.get("VECLIB_MAXIMUM_THREADS"),
        },
        "threadpool_info": _threadpool_info(),
        "nvidia_smi": _nvidia_smi_snapshot(),
    }


def _threadpool_info() -> list[dict[str, Any]]:
    try:
        from threadpoolctl import threadpool_info

        return [dict(item) for item in threadpool_info()]
    except Exception as exc:
        return [
            {
                "available": False,
                "reason": "threadpoolctl_unavailable",
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            }
        ]


def _nvidia_smi_snapshot() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        return {
            "available": False,
            "reason": "nvidia_smi_unavailable",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }
    if completed.returncode != 0:
        return {
            "available": False,
            "reason": "nvidia_smi_failed",
            "returncode": int(completed.returncode),
            "stderr": completed.stderr.strip(),
        }
    rows = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 5:
            rows.append(
                {
                    "name": parts[0],
                    "driver_version": parts[1],
                    "memory_total_mib": _int_or_none(parts[2]),
                    "memory_used_mib": _int_or_none(parts[3]),
                    "utilization_gpu_percent": _int_or_none(parts[4]),
                }
            )
    return {
        "available": True,
        "gpus": rows,
    }


def _int_or_none(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _build_recommendations(*, cpu_probe: dict[str, Any], gpu_probe: dict[str, Any]) -> dict[str, Any]:
    blocking_reasons: list[str] = []
    warnings_list: list[str] = []
    optimization_notes: list[str] = []
    preferred_backends: list[str] = []
    cpu_succeeded = bool(cpu_probe.get("probe_succeeded"))
    gpu_succeeded = bool(gpu_probe.get("probe_succeeded"))
    if not cpu_succeeded:
        blocking_reasons.append(str(cpu_probe.get("fallback_reason") or "cpu_probe_failed"))
    else:
        preferred_backends.extend(
            [
                "process_pool_for_pure_python_cpu_bound_sweeps",
                "vector_fixed_holding_for_supported_cpu_backtests",
            ]
        )
    if gpu_succeeded:
        preferred_backends.append("cuda_fixed_holding_or_cuda_batched_fixed_holding_when_scope_supported")
    else:
        warnings_list.append(str(gpu_probe.get("fallback_reason") or "gpu_probe_not_available"))

    worker_pct = float(cpu_probe.get("process_cpu_percent_of_worker_capacity") or 0.0)
    logical_pct = float(cpu_probe.get("process_cpu_percent_of_logical_capacity") or 0.0)
    active_workers = int(cpu_probe.get("active_workers") or 0)
    logical_cpu_count = int(cpu_probe.get("logical_cpu_count") or 0)
    cpu_worker_saturated = bool(cpu_succeeded and worker_pct >= SATURATION_TARGET_PERCENT)
    if cpu_succeeded and worker_pct < SATURATION_TARGET_PERCENT:
        warnings_list.append("cpu_process_pool_worker_capacity_below_saturation_target")
    if cpu_succeeded and active_workers >= logical_cpu_count > 0 and logical_pct < SATURATION_TARGET_PERCENT:
        warnings_list.append("cpu_logical_capacity_below_saturation_target_for_requested_worker_count")
    if cpu_succeeded and active_workers < logical_cpu_count and worker_pct >= SATURATION_TARGET_PERCENT:
        optimization_notes.append("physical_core_worker_count_saturated_without_hyperthread_oversubscription")

    return {
        "best_option": (
            "hardware_probe_blocked_until_cpu_process_pool_passes"
            if not cpu_succeeded
            else (
                "cpu_process_pool_below_saturation_target_recheck_worker_count_or_system_load"
                if not cpu_worker_saturated
                else (
                    "hybrid_process_pool_cpu_plus_cuda_supported_fixed_holding"
                    if gpu_succeeded
                    else "process_pool_cpu_plus_vector_fixed_holding_until_cuda_available"
                )
            )
        ),
        "preferred_backends": preferred_backends,
        "blocking_reasons": blocking_reasons,
        "non_blocking_warnings": list(dict.fromkeys(warnings_list)),
        "optimization_notes": list(dict.fromkeys(optimization_notes)),
        "selected_cpu_saturation_target": "worker_capacity",
        "selected_cpu_saturation_target_met": cpu_worker_saturated,
        "utilization_policy": (
            "Target near-saturation only for bounded CPU/GPU compute probes. "
            "Long research runs should surface I/O, artifact, scheduler, data-size, and GIL bottlenecks instead of hiding them."
        ),
        "oversubscription_policy": (
            "For nested joblib/OpenMP/BLAS phases, cap native library threads or worker counts so process workers do not multiply "
            "into more runnable threads than logical CPUs."
        ),
        "research_boundary_policy": "diagnostic_only_observe_only_no_live_or_promotion_claim",
    }
