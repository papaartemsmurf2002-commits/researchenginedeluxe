from __future__ import annotations

from typing import Any

import numpy as np
import pytest

import tradingbotsuite.optimization.gpu_screening as gpu_screening
from tradingbotsuite.optimization import cuda_screening_batch_v1


class _FakeCupy:
    __version__ = "fake-cupy-screening-test"

    @staticmethod
    def asarray(value: Any) -> np.ndarray:
        return np.asarray(value)

    @staticmethod
    def asnumpy(value: Any) -> np.ndarray:
        return np.asarray(value)


def test_cuda_screening_batch_is_diagnostic_only_cpu_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gpu_screening,
        "_cuda_runtime_evidence",
        lambda: {
            "available": False,
            "unavailable_reason": "cupy_unavailable",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        },
    )

    result = cuda_screening_batch_v1(
        [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]],
        [[1.0, 0.0]],
        top_k=2,
        tensor_core_policy="screening_only",
    )

    assert result.cpu_top_k_indices.tolist() == [[0, 2]]
    assert result.gpu_scores is None
    evidence = result.evidence
    assert evidence["research_only"] is True
    assert evidence["observe_only"] is True
    assert evidence["promotion_ready"] is False
    assert evidence["diagnostic_only"] is True
    assert evidence["position_sizing_input"] is False
    assert evidence["candidate_acceptance_allowed"] is False
    assert evidence["final_trade_accounting"] is False
    assert evidence["tensor_core_used"] is False
    assert evidence["gpu_execution_status"] == "fallback_cpu_reference"
    assert evidence["fallback_reason"] == "cupy_unavailable"


def test_cuda_screening_batch_fake_gpu_matches_cpu_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gpu_screening,
        "_cuda_runtime_evidence",
        lambda: {
            "available": True,
            "gpu_name": "Fake TensorCore Device",
            "compute_capability": "12.0",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        },
    )
    monkeypatch.setattr(gpu_screening, "_load_cupy", lambda: _FakeCupy())

    result = cuda_screening_batch_v1(
        [[1.0, 0.0, 0.0], [0.4, 0.5, 0.1], [0.0, 1.0, 0.0]],
        [[0.9, 0.1, 0.0], [0.0, 1.0, 0.0]],
        top_k=2,
        tensor_core_policy="screening_only",
        score_atol=1e-6,
        score_rtol=1e-6,
    )

    assert result.gpu_scores is not None
    assert result.cpu_top_k_indices.tolist() == result.gpu_top_k_indices.tolist()
    evidence = result.evidence
    assert evidence["tensor_core_used"] is True
    assert evidence["tensor_core_scope"] == "cuda_screening_batch_v1"
    assert evidence["gpu_execution_status"] == "cuda_screening_executed"
    assert evidence["parity_status"] == "passed"
    assert evidence["mismatch_count"] == 0


def test_cuda_screening_batch_rejects_nonfinite_and_policy_mismatch() -> None:
    with pytest.raises(ValueError, match="feature_matrix must contain only finite numeric values"):
        cuda_screening_batch_v1([[1.0, float("nan")]], [[1.0, 0.0]])

    result = cuda_screening_batch_v1(
        [[1.0, 0.0]],
        [[1.0, 0.0]],
        tensor_core_policy="disabled",
    )

    assert result.evidence["tensor_core_used"] is False
    assert result.evidence["gpu_execution_status"] == "not_executed"
    assert result.evidence["fallback_reason"] == "tensor_core_policy_not_screening_only"
    assert result.evidence["parity_status"] == "not_checked_policy_not_screening_only"
