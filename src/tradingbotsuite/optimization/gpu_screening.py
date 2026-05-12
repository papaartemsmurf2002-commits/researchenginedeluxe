from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np


CUDA_SCREENING_BATCH_VERSION = "cuda-screening-batch-v1"
CUDA_SCREENING_SCOPE = "cuda_screening_batch_v1"
SCREENING_ONLY_POLICY = "screening_only"


@dataclass(frozen=True, slots=True)
class CudaScreeningBatchResult:
    cpu_scores: np.ndarray
    cpu_top_k_indices: np.ndarray
    cpu_top_k_scores: np.ndarray
    gpu_scores: np.ndarray | None
    gpu_top_k_indices: np.ndarray | None
    gpu_top_k_scores: np.ndarray | None
    evidence: dict[str, Any]

    def to_payload(self, *, include_scores: bool = False) -> dict[str, Any]:
        payload = {
            "evidence": dict(self.evidence),
            "cpu_top_k_indices": self.cpu_top_k_indices.tolist(),
            "cpu_top_k_scores": self.cpu_top_k_scores.tolist(),
            "gpu_top_k_indices": self.gpu_top_k_indices.tolist() if self.gpu_top_k_indices is not None else None,
            "gpu_top_k_scores": self.gpu_top_k_scores.tolist() if self.gpu_top_k_scores is not None else None,
        }
        if include_scores:
            payload["cpu_scores"] = self.cpu_scores.tolist()
            payload["gpu_scores"] = self.gpu_scores.tolist() if self.gpu_scores is not None else None
        return payload


def cuda_screening_batch_v1(
    feature_matrix: Any,
    query_candidate_matrix: Any,
    *,
    top_k: int = 10,
    tensor_core_policy: str = SCREENING_ONLY_POLICY,
    enable_gpu: bool = True,
    score_atol: float = 1e-4,
    score_rtol: float = 1e-4,
) -> CudaScreeningBatchResult:
    """Diagnostic-only CPU/GPU matrix screening with exact CPU reference.

    Scores are `query_candidate_matrix @ feature_matrix.T`. CPU reference uses
    float64. The optional CuPy path uses float32 matmul only when explicitly
    scoped to screening, and never produces candidate-gate acceptance evidence.
    """

    started = time.perf_counter()
    features = _as_numeric_matrix(feature_matrix, name="feature_matrix")
    queries = _as_numeric_matrix(query_candidate_matrix, name="query_candidate_matrix")
    if features.shape[1] != queries.shape[1]:
        raise ValueError(
            "feature_matrix and query_candidate_matrix must have the same column count: "
            f"{features.shape[1]} != {queries.shape[1]}"
        )
    resolved_top_k = int(max(0, min(int(top_k), features.shape[0])))
    cpu_scores = queries @ features.T
    cpu_top_indices, cpu_top_scores = _top_k(cpu_scores, resolved_top_k)
    evidence: dict[str, Any] = _base_evidence(
        features=features,
        queries=queries,
        cpu_scores=cpu_scores,
        cpu_top_indices=cpu_top_indices,
        top_k=resolved_top_k,
        tensor_core_policy=tensor_core_policy,
    )
    gpu_scores: np.ndarray | None = None
    gpu_top_indices: np.ndarray | None = None
    gpu_top_scores: np.ndarray | None = None

    if not enable_gpu:
        evidence.update(
            {
                "gpu_execution_status": "not_requested",
                "fallback_reason": "gpu_screening_disabled",
                "parity_status": "not_checked_gpu_not_requested",
            }
        )
    elif tensor_core_policy != SCREENING_ONLY_POLICY:
        evidence.update(
            {
                "gpu_execution_status": "not_executed",
                "fallback_reason": "tensor_core_policy_not_screening_only",
                "parity_status": "not_checked_policy_not_screening_only",
            }
        )
    else:
        gpu_scores, gpu_top_indices, gpu_top_scores, gpu_evidence = _cupy_screening_scores(
            features,
            queries,
            cpu_scores=cpu_scores,
            cpu_top_indices=cpu_top_indices,
            top_k=resolved_top_k,
            score_atol=float(score_atol),
            score_rtol=float(score_rtol),
        )
        evidence.update(gpu_evidence)

    evidence["elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 6)
    return CudaScreeningBatchResult(
        cpu_scores=cpu_scores,
        cpu_top_k_indices=cpu_top_indices,
        cpu_top_k_scores=cpu_top_scores,
        gpu_scores=gpu_scores,
        gpu_top_k_indices=gpu_top_indices,
        gpu_top_k_scores=gpu_top_scores,
        evidence=evidence,
    )


def merge_wpr97_screening_counters(
    counters: Mapping[str, Any],
    *,
    tensorcore_screened_count: int = 0,
    gpu_exact_screened_count: int = 0,
    cpu_reference_validated_count: int = 0,
    parity_rechecked_count: int = 0,
    mismatch_count: int = 0,
) -> dict[str, Any]:
    """Merge WPR97 screening counters without removing existing R96 keys."""

    merged = dict(counters)
    additions = {
        "tensorcore_screened_count": int(tensorcore_screened_count),
        "gpu_exact_screened_count": int(gpu_exact_screened_count),
        "cpu_reference_validated_count": int(cpu_reference_validated_count),
        "parity_rechecked_count": int(parity_rechecked_count),
        "mismatch_count": int(mismatch_count),
    }
    for key, value in additions.items():
        merged[key] = int(merged.get(key, 0) or 0) + value
    return merged


def _cupy_screening_scores(
    features: np.ndarray,
    queries: np.ndarray,
    *,
    cpu_scores: np.ndarray,
    cpu_top_indices: np.ndarray,
    top_k: int,
    score_atol: float,
    score_rtol: float,
) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None, dict[str, Any]]:
    runtime_evidence = _cuda_runtime_evidence()
    if not bool(runtime_evidence.get("available")):
        return (
            None,
            None,
            None,
            {
                "tensor_core_used": False,
                "gpu_execution_status": "fallback_cpu_reference",
                "fallback_reason": str(runtime_evidence.get("unavailable_reason") or "cuda_runtime_unavailable"),
                "parity_status": "not_checked_gpu_unavailable",
                "top_k_overlap": None,
                "gpu_runtime_evidence": runtime_evidence,
            },
        )
    try:
        cupy = _load_cupy()
        features_gpu = cupy.asarray(features.astype(np.float32, copy=False))
        queries_gpu = cupy.asarray(queries.astype(np.float32, copy=False))
        gpu_scores = cupy.asnumpy(queries_gpu @ features_gpu.T).astype(np.float64, copy=False)
    except Exception as exc:
        return (
            None,
            None,
            None,
            {
                "tensor_core_used": False,
                "gpu_execution_status": "fallback_cpu_reference",
                "fallback_reason": "cuda_screening_matmul_failed",
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "parity_status": "not_checked_gpu_execution_failed",
                "top_k_overlap": None,
                "gpu_runtime_evidence": runtime_evidence,
            },
        )
    gpu_top_indices, gpu_top_scores = _top_k(gpu_scores, top_k)
    parity = _parity_evidence(
        cpu_scores=cpu_scores,
        gpu_scores=gpu_scores,
        cpu_top_indices=cpu_top_indices,
        gpu_top_indices=gpu_top_indices,
        score_atol=score_atol,
        score_rtol=score_rtol,
    )
    return (
        gpu_scores,
        gpu_top_indices,
        gpu_top_scores,
        {
            "tensor_core_used": True,
            "tensor_core_verification_status": "gpu_float32_matmul_executed_tensorcore_eligible_not_kernel_traced",
            "gpu_execution_status": "cuda_screening_executed",
            "fallback_reason": "",
            "gpu_runtime_evidence": runtime_evidence,
            **parity,
        },
    )


def _base_evidence(
    *,
    features: np.ndarray,
    queries: np.ndarray,
    cpu_scores: np.ndarray,
    cpu_top_indices: np.ndarray,
    top_k: int,
    tensor_core_policy: str,
) -> dict[str, Any]:
    return {
        "screening_evidence_version": CUDA_SCREENING_BATCH_VERSION,
        "name": CUDA_SCREENING_SCOPE,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "diagnostic_only": True,
        "position_sizing_input": False,
        "live_signal_input": False,
        "order_placement_used": False,
        "candidate_acceptance_allowed": False,
        "final_trade_accounting": False,
        "tensor_core_used": False,
        "tensor_core_scope": CUDA_SCREENING_SCOPE,
        "tensor_core_verification_status": "not_executed",
        "precision_policy": "cpu_float64_reference_gpu_float32_tf32_style_matmul_screening_only",
        "determinism_policy": "finite_2d_numeric_inputs_cpu_float64_reference_stable_tie_break_by_column_index",
        "tensor_core_policy": str(tensor_core_policy),
        "feature_row_count": int(features.shape[0]),
        "query_candidate_count": int(queries.shape[0]),
        "feature_column_count": int(features.shape[1]),
        "top_k": int(top_k),
        "cpu_reference_validated": True,
        "cpu_reference_score_hash": _array_sha256(cpu_scores),
        "cpu_reference_top_k_hash": _array_sha256(cpu_top_indices),
        "parity_status": "not_checked",
        "top_k_overlap": None,
        "gpu_execution_status": "not_executed",
        "fallback_reason": "",
    }


def _as_numeric_matrix(values: Any, *, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a 2D numeric matrix")
    try:
        matrix = array.astype(np.float64, copy=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not np.isfinite(matrix).all():
        raise ValueError(f"{name} must contain only finite numeric values")
    return np.ascontiguousarray(matrix)


def _top_k(scores: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
    rows = int(scores.shape[0])
    k = int(max(0, min(top_k, scores.shape[1])))
    if k == 0:
        return np.empty((rows, 0), dtype=np.int64), np.empty((rows, 0), dtype=np.float64)
    indices = np.empty((rows, k), dtype=np.int64)
    values = np.empty((rows, k), dtype=np.float64)
    tie_breaker = np.arange(scores.shape[1], dtype=np.int64)
    for row_index, row in enumerate(scores):
        order = np.lexsort((tie_breaker, -row))
        selected = order[:k].astype(np.int64, copy=False)
        indices[row_index, :] = selected
        values[row_index, :] = row[selected]
    return indices, values


def _parity_evidence(
    *,
    cpu_scores: np.ndarray,
    gpu_scores: np.ndarray,
    cpu_top_indices: np.ndarray,
    gpu_top_indices: np.ndarray,
    score_atol: float,
    score_rtol: float,
) -> dict[str, Any]:
    diff = np.abs(cpu_scores - gpu_scores)
    denom = np.maximum(np.abs(cpu_scores), 1e-12)
    max_abs_diff = float(diff.max()) if diff.size else 0.0
    max_rel_diff = float((diff / denom).max()) if diff.size else 0.0
    overlap_values: list[float] = []
    exact_top_k_matches = 0
    for cpu_row, gpu_row in zip(cpu_top_indices, gpu_top_indices):
        cpu_set = set(int(value) for value in cpu_row)
        gpu_set = set(int(value) for value in gpu_row)
        if cpu_set == gpu_set:
            exact_top_k_matches += 1
        if not cpu_set and not gpu_set:
            overlap_values.append(1.0)
            continue
        overlap_values.append(len(cpu_set & gpu_set) / max(len(cpu_set | gpu_set), 1))
    min_overlap = min(overlap_values) if overlap_values else 1.0
    mean_overlap = sum(overlap_values) / max(len(overlap_values), 1)
    score_tolerance_passed = bool(np.allclose(cpu_scores, gpu_scores, atol=score_atol, rtol=score_rtol))
    top_k_passed = exact_top_k_matches == int(cpu_top_indices.shape[0])
    if top_k_passed and score_tolerance_passed:
        parity_status = "passed"
    elif top_k_passed:
        parity_status = "top_k_overlap_passed_score_diff_exceeded"
    else:
        parity_status = "mismatch"
    return {
        "parity_status": parity_status,
        "parity_rechecked": True,
        "score_atol": float(score_atol),
        "score_rtol": float(score_rtol),
        "max_abs_diff": max_abs_diff,
        "max_rel_diff": max_rel_diff,
        "top_k_overlap": {
            "query_count": int(cpu_top_indices.shape[0]),
            "top_k": int(cpu_top_indices.shape[1]),
            "exact_match_count": int(exact_top_k_matches),
            "mean_overlap": float(mean_overlap),
            "min_overlap": float(min_overlap),
        },
        "mismatch_count": int(cpu_top_indices.shape[0] - exact_top_k_matches),
    }


def _cuda_runtime_evidence() -> dict[str, Any]:
    from tradingbotsuite.backtesting import cuda_runtime_evidence

    return dict(cuda_runtime_evidence())


def _load_cupy() -> Any:
    from tradingbotsuite.backtesting.cuda_engine import _load_cupy as load_cupy

    return load_cupy()


def _array_sha256(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("utf-8"))
    digest.update(str(array.shape).encode("utf-8"))
    digest.update(array.tobytes())
    return digest.hexdigest()
