from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

REGIME_MATCH_MODES = frozenset({"same", "compatible", "all", "same_with_all_fallback"})


@dataclass(frozen=True, slots=True)
class NeighborPoolDiagnostics:
    query_regime: int
    query_regime_label: str | None
    regime_match_mode: str
    candidate_count_before_regime_filter: int
    candidate_count_after_regime_filter: int
    selected_count: int
    fallback_used: bool
    fallback_reason: str | None
    skip_reason: str | None
    compatible_regime_labels: tuple[str, ...]

    def with_selected_count(self, selected_count: int) -> "NeighborPoolDiagnostics":
        return NeighborPoolDiagnostics(
            query_regime=self.query_regime,
            query_regime_label=self.query_regime_label,
            regime_match_mode=self.regime_match_mode,
            candidate_count_before_regime_filter=self.candidate_count_before_regime_filter,
            candidate_count_after_regime_filter=self.candidate_count_after_regime_filter,
            selected_count=int(selected_count),
            fallback_used=self.fallback_used,
            fallback_reason=self.fallback_reason,
            skip_reason=self.skip_reason,
            compatible_regime_labels=self.compatible_regime_labels,
        )

    def to_payload(self) -> dict[str, int | bool | str | None]:
        return {
            "query_regime": int(self.query_regime),
            "query_regime_label": self.query_regime_label,
            "regime_match_mode": self.regime_match_mode,
            "candidate_count_before_regime_filter": int(self.candidate_count_before_regime_filter),
            "candidate_count_after_regime_filter": int(self.candidate_count_after_regime_filter),
            "selected_count": int(self.selected_count),
            "fallback_used": bool(self.fallback_used),
            "fallback_reason": self.fallback_reason,
            "skip_reason": self.skip_reason,
            "compatible_regime_labels": ",".join(self.compatible_regime_labels),
        }


@dataclass(frozen=True, slots=True)
class NeighborPool:
    candidate_positions: np.ndarray
    diagnostics: NeighborPoolDiagnostics


def resolve_regime_match_mode(
    *,
    regime_match_mode: str | None,
    same_regime_only: bool,
    allow_cross_regime_fallback: bool,
) -> str:
    if regime_match_mode is not None and str(regime_match_mode).strip():
        normalized = str(regime_match_mode).strip().lower()
        if normalized not in REGIME_MATCH_MODES:
            raise ValueError(f"knn.regime_match_mode must be one of: {', '.join(sorted(REGIME_MATCH_MODES))}")
        return normalized
    if same_regime_only:
        return "same_with_all_fallback" if allow_cross_regime_fallback else "same"
    return "all"


def build_neighbor_pool(
    *,
    train_regimes: np.ndarray,
    query_regime: int,
    regime_match_mode: str,
    train_regime_labels: np.ndarray | None = None,
    query_regime_label: str | None = None,
    compatible_regimes: Mapping[str, object] | None = None,
) -> NeighborPool:
    regimes = np.asarray(train_regimes, dtype=int)
    before_count = int(len(regimes))
    labels = _string_array(train_regime_labels)
    label = _safe_label(query_regime_label)
    mode = resolve_regime_match_mode(
        regime_match_mode=regime_match_mode,
        same_regime_only=regime_match_mode == "same",
        allow_cross_regime_fallback=regime_match_mode == "same_with_all_fallback",
    )
    fallback_used = False
    fallback_reason: str | None = None
    compatible_labels: tuple[str, ...] = ()

    if mode == "all":
        mask = np.ones(before_count, dtype=bool)
        skip_reason = "no_neighbors"
    elif mode == "same":
        mask = regimes == int(query_regime)
        skip_reason = "no_same_regime_neighbors"
    elif mode == "same_with_all_fallback":
        same_mask = regimes == int(query_regime)
        if same_mask.any():
            mask = same_mask
        else:
            mask = np.ones(before_count, dtype=bool)
            fallback_used = bool(before_count)
            fallback_reason = "same_regime_pool_empty"
        skip_reason = "no_same_regime_neighbors"
    else:
        compatible_labels = _compatible_regime_labels(
            query_regime=int(query_regime),
            query_regime_label=label,
            compatible_regimes=compatible_regimes or {},
        )
        if labels is not None and compatible_labels:
            mask = np.isin(labels, np.asarray(compatible_labels, dtype=object))
        else:
            mask = regimes == int(query_regime)
        skip_reason = "no_compatible_regime_neighbors"

    candidate_positions = np.where(mask)[0]
    after_count = int(len(candidate_positions))
    diagnostics = NeighborPoolDiagnostics(
        query_regime=int(query_regime),
        query_regime_label=label,
        regime_match_mode=mode,
        candidate_count_before_regime_filter=before_count,
        candidate_count_after_regime_filter=after_count,
        selected_count=0,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        skip_reason=None if after_count else skip_reason,
        compatible_regime_labels=compatible_labels,
    )
    return NeighborPool(candidate_positions=candidate_positions.astype(int), diagnostics=diagnostics)


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


def _string_array(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    result = np.asarray(values, dtype=object)
    return np.asarray([_safe_label(item) for item in result], dtype=object)


def _safe_label(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _compatible_regime_labels(
    *,
    query_regime: int,
    query_regime_label: str | None,
    compatible_regimes: Mapping[str, object],
) -> tuple[str, ...]:
    keys = [key for key in (query_regime_label, str(query_regime)) if key is not None]
    values: list[str] = []
    if query_regime_label is not None:
        values.append(query_regime_label)
    for key in keys:
        raw = compatible_regimes.get(str(key))
        if raw is None:
            continue
        if isinstance(raw, str):
            raw_values = [raw]
        else:
            try:
                raw_values = list(raw)  # type: ignore[arg-type]
            except TypeError:
                raw_values = [raw]
        for item in raw_values:
            label = _safe_label(item)
            if label is not None:
                values.append(label)
    deduped = tuple(dict.fromkeys(values))
    return deduped
