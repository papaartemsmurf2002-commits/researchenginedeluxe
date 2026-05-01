from __future__ import annotations

from typing import Callable

import numpy as np

DistanceFunction = Callable[[np.ndarray, np.ndarray, np.ndarray | None], np.ndarray]


def log_lorentzian_distance_matrix(query: np.ndarray, train: np.ndarray, scales: np.ndarray | None = None) -> np.ndarray:
    query, train, scales = _validated_inputs(query, train, scales)
    diff = np.abs(query[:, None, :] - train[None, :, :]) / scales.reshape(1, 1, -1)
    return np.log1p(diff).sum(axis=2)


def euclidean_robust_z_distance_matrix(query: np.ndarray, train: np.ndarray, scales: np.ndarray | None = None) -> np.ndarray:
    query, train, scales = _validated_inputs(query, train, scales)
    diff = (query[:, None, :] - train[None, :, :]) / scales.reshape(1, 1, -1)
    return np.sqrt(np.square(diff).sum(axis=2))


def cosine_distance_matrix(query: np.ndarray, train: np.ndarray, scales: np.ndarray | None = None) -> np.ndarray:
    query, train, scales = _validated_inputs(query, train, scales)
    query = query / scales.reshape(1, -1)
    train = train / scales.reshape(1, -1)
    numerator = query @ train.T
    query_norm = np.linalg.norm(query, axis=1).reshape(-1, 1)
    train_norm = np.linalg.norm(train, axis=1).reshape(1, -1)
    similarity = numerator / np.maximum(query_norm * train_norm, 1e-12)
    return 1.0 - np.clip(similarity, -1.0, 1.0)


DISTANCE_FUNCTIONS: dict[str, DistanceFunction] = {
    "lorentzian": log_lorentzian_distance_matrix,
    "log_lorentzian": log_lorentzian_distance_matrix,
    "euclidean_robust_z": euclidean_robust_z_distance_matrix,
    "cosine": cosine_distance_matrix,
}


def resolve_distance_function(distance: str) -> DistanceFunction:
    key = str(distance).strip().lower()
    if key not in DISTANCE_FUNCTIONS:
        raise ValueError(f"unsupported_hmm_knn_distance:{distance}")
    return DISTANCE_FUNCTIONS[key]


def _validated_inputs(
    query: np.ndarray,
    train: np.ndarray,
    scales: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    query = np.asarray(query, dtype=float)
    train = np.asarray(train, dtype=float)
    if query.ndim == 1:
        query = query.reshape(1, -1)
    if train.ndim != 2 or query.ndim != 2 or query.shape[1] != train.shape[1]:
        raise ValueError("query and train matrices must be 2-D with matching feature counts")
    if scales is None:
        scales = np.ones(train.shape[1], dtype=float)
    scales = np.asarray(scales, dtype=float)
    if scales.ndim != 1 or len(scales) != train.shape[1] or np.any(~np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError("distance scales must be finite positive values for every feature")
    return query, train, scales
