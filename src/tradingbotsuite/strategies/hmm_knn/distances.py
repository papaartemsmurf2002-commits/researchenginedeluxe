from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

DistanceFunction = Callable[[np.ndarray, np.ndarray, np.ndarray | None], np.ndarray]


@dataclass(frozen=True, slots=True)
class DistanceMetric:
    id: str
    display_name: str
    aliases: tuple[str, ...]
    feature_scale_mode: str
    supports_backend: tuple[str, ...]
    function: DistanceFunction

    def to_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "aliases": list(self.aliases),
            "feature_scale_mode": self.feature_scale_mode,
            "supports_backend": list(self.supports_backend),
        }


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


DISTANCE_METRICS: dict[str, DistanceMetric] = {
    "lorentzian": DistanceMetric(
        id="lorentzian",
        display_name="Log Lorentzian",
        aliases=("log_lorentzian",),
        feature_scale_mode="robust_z_or_supplied_scale",
        supports_backend=("cpu", "auto", "cupy"),
        function=log_lorentzian_distance_matrix,
    ),
    "euclidean_robust_z": DistanceMetric(
        id="euclidean_robust_z",
        display_name="Euclidean Robust Z",
        aliases=(),
        feature_scale_mode="robust_z_or_supplied_scale",
        supports_backend=("cpu",),
        function=euclidean_robust_z_distance_matrix,
    ),
    "cosine": DistanceMetric(
        id="cosine",
        display_name="Cosine",
        aliases=(),
        feature_scale_mode="robust_z_or_supplied_scale",
        supports_backend=("cpu",),
        function=cosine_distance_matrix,
    ),
}
DISTANCE_ALIASES: dict[str, str] = {
    metric.id: metric.id
    for metric in DISTANCE_METRICS.values()
} | {
    alias: metric.id
    for metric in DISTANCE_METRICS.values()
    for alias in metric.aliases
}
DISTANCE_FUNCTIONS: dict[str, DistanceFunction] = {
    name: DISTANCE_METRICS[metric_id].function
    for name, metric_id in DISTANCE_ALIASES.items()
}


def available_distance_metrics() -> dict[str, dict[str, object]]:
    return {
        metric_id: DISTANCE_METRICS[metric_id].to_payload()
        for metric_id in sorted(DISTANCE_METRICS)
    }


def resolve_distance_metric(distance: str) -> DistanceMetric:
    key = str(distance).strip().lower()
    metric_id = DISTANCE_ALIASES.get(key)
    if metric_id is None:
        raise ValueError(f"unsupported_hmm_knn_distance:{distance}")
    return DISTANCE_METRICS[metric_id]


def resolve_distance_function(distance: str) -> DistanceFunction:
    return resolve_distance_metric(distance).function


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
