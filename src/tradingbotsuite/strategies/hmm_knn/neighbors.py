from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class NeighborPoolDiagnostics:
    query_regime: int
    candidate_count: int
    selected_count: int
    fallback_used: bool

    def to_payload(self) -> dict[str, int | bool]:
        return {
            "query_regime": int(self.query_regime),
            "candidate_count": int(self.candidate_count),
            "selected_count": int(self.selected_count),
            "fallback_used": bool(self.fallback_used),
        }


def select_neighbor_positions(
    distances: np.ndarray,
    *,
    candidate_positions: np.ndarray,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    if len(candidate_positions) == 0:
        return np.asarray([], dtype=int), np.asarray([], dtype=float)
    candidate_distances = distances[candidate_positions]
    order = np.argsort(candidate_distances)
    selected = candidate_positions[order[: min(int(k), len(order))]]
    return selected.astype(int), candidate_distances[order[: min(int(k), len(order))]].astype(float)
