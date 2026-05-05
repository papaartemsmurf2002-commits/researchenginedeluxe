from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from threading import Lock
from typing import Any

from tradingbotsuite.optimization.candidate import CandidateConfig, CandidateResult


@dataclass(slots=True)
class CandidateCache:
    dataset_hash: str
    feature_hash: str
    engine_version: str
    validation_hash: str
    _results: dict[str, CandidateResult] = field(default_factory=dict)
    _hits: int = 0
    _misses: int = 0
    _writes: int = 0
    _lock: Any = field(default_factory=Lock, init=False, repr=False)

    def key_for(self, config: CandidateConfig) -> str:
        payload = {
            "dataset_hash": self.dataset_hash,
            "feature_hash": self.feature_hash,
            "engine_version": self.engine_version,
            "validation_hash": self.validation_hash,
            "candidate": config.to_payload(),
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()

    def get(self, config: CandidateConfig) -> CandidateResult | None:
        key = self.key_for(config)
        with self._lock:
            result = self._results.get(key)
            if result is None:
                self._misses += 1
                return None
            self._hits += 1
            return result

    def put(self, result: CandidateResult) -> str:
        key = self.key_for(result.config)
        with self._lock:
            self._results[key] = result
            self._writes += 1
        return key

    def telemetry_snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "hits": int(self._hits),
                "misses": int(self._misses),
                "writes": int(self._writes),
                "size": int(len(self._results)),
            }

    def to_payload(self) -> dict[str, Any]:
        telemetry = self.telemetry_snapshot()
        return {
            "dataset_hash": self.dataset_hash,
            "feature_hash": self.feature_hash,
            "engine_version": self.engine_version,
            "validation_hash": self.validation_hash,
            "size": telemetry["size"],
            "hits": telemetry["hits"],
            "misses": telemetry["misses"],
            "writes": telemetry["writes"],
            "hit_rate": _hit_rate(telemetry["hits"], telemetry["misses"]),
            "keys": sorted(self._results),
        }


def _hit_rate(hits: int, misses: int) -> float:
    total = hits + misses
    if total <= 0:
        return 0.0
    return float(hits / total)
