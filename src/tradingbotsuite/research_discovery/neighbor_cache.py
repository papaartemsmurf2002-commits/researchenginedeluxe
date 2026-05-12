from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence


NEIGHBOR_CACHE_VERSION = "exact-neighbor-cache-v1"


@dataclass(frozen=True, slots=True)
class ExactNeighborCacheRecord:
    cache_key: str
    identity: Mapping[str, Any]
    row_records: tuple[Mapping[str, Any], ...]

    @property
    def row_count(self) -> int:
        return len(self.row_records)

    def to_payload(self) -> dict[str, Any]:
        return {
            "neighbor_cache_version": NEIGHBOR_CACHE_VERSION,
            "cache_key": self.cache_key,
            "identity": dict(self.identity),
            "row_count": self.row_count,
        }


class ExactNeighborCache:
    def __init__(self) -> None:
        self._records: dict[str, ExactNeighborCacheRecord] = {}
        self._lock = threading.Lock()
        self.lookups = 0
        self.hits = 0
        self.misses = 0
        self.writes = 0

    def get(self, cache_key: str) -> ExactNeighborCacheRecord | None:
        with self._lock:
            self.lookups += 1
            record = self._records.get(cache_key)
            if record is None:
                self.misses += 1
                return None
            self.hits += 1
            return record

    def put(self, record: ExactNeighborCacheRecord) -> ExactNeighborCacheRecord:
        with self._lock:
            existing = self._records.get(record.cache_key)
            if existing is not None:
                return existing
            self._records[record.cache_key] = record
            self.writes += 1
            return record

    def summary(self) -> dict[str, Any]:
        lookups = max(1, self.lookups)
        return {
            "neighbor_cache_version": NEIGHBOR_CACHE_VERSION,
            "enabled": True,
            "lookups": int(self.lookups),
            "hits": int(self.hits),
            "misses": int(self.misses),
            "writes": int(self.writes),
            "record_count": int(len(self._records)),
            "hit_rate": float(self.hits / lookups),
        }


def exact_neighbor_cache_identity(
    *,
    feature_column_set_id: str,
    feature_columns: Sequence[str],
    label_horizon: str,
    label_horizon_bars: int,
    split_id: str,
    regime_mode: str,
    regime_detector_type: str,
    regime_gate_enabled: bool,
    same_regime_neighbor_pool_enabled: bool,
    distance_metric: str,
    selection_k_limit: int,
    train_source_min: int | None,
    train_source_max: int | None,
    validation_source_min: int | None,
    validation_source_max: int | None,
    safe_train_source_max: int | None,
    train_row_count: int,
    validation_row_count: int,
    source_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "neighbor_cache_version": NEIGHBOR_CACHE_VERSION,
        "feature_column_set_id": str(feature_column_set_id),
        "feature_columns": [str(column) for column in feature_columns],
        "label_horizon": str(label_horizon),
        "label_horizon_bars": int(label_horizon_bars),
        "split_id": str(split_id),
        "regime_mode": str(regime_mode),
        "regime_detector_type": str(regime_detector_type),
        "regime_gate_enabled": bool(regime_gate_enabled),
        "same_regime_neighbor_pool_enabled": bool(same_regime_neighbor_pool_enabled),
        "distance_metric": str(distance_metric),
        "selection_k_limit": int(selection_k_limit),
        "train_source_min": train_source_min,
        "train_source_max": train_source_max,
        "validation_source_min": validation_source_min,
        "validation_source_max": validation_source_max,
        "safe_train_source_max": safe_train_source_max,
        "train_row_count": int(train_row_count),
        "validation_row_count": int(validation_row_count),
        "source_identity": dict(source_identity or {}),
    }


def exact_neighbor_cache_key(identity: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(dict(identity), sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")
    ).hexdigest()
