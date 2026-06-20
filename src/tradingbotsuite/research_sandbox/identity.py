from __future__ import annotations

import hashlib
import json
from typing import Any

from tradingbotsuite.research_sandbox.spec import SandboxRunSpec, StrategyCatalogRow, VenueArchiveDescriptor, stable_payload


def canonical_json(payload: Any) -> str:
    return json.dumps(stable_payload(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_payload(payload: Any, *, prefix: str, length: int = 20) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:length]}"


def deterministic_run_id(payload: Any, *, prefix: str = "sandbox") -> str:
    return digest_payload(payload, prefix=prefix, length=16)


def deterministic_trial_id(
    *,
    run_spec: SandboxRunSpec,
    strategy: StrategyCatalogRow,
    venue: VenueArchiveDescriptor,
    holding_period: int,
    extra: dict[str, Any] | None = None,
) -> str:
    payload = {
        "run_spec": {
            "data_window": run_spec.data_window.to_payload(),
            "validation_profile": run_spec.validation_profile.value,
            "round_trip_cost_bps": run_spec.round_trip_cost_bps,
            "min_trades": run_spec.min_trades,
            "rank_top_n": run_spec.rank_top_n,
        },
        "strategy": strategy.to_payload(),
        "venue": _logical_venue_identity(venue),
        "holding_period": int(holding_period),
        "extra": extra or {},
    }
    return digest_payload(payload, prefix="sbxtrial", length=24)


def _logical_venue_identity(venue: VenueArchiveDescriptor) -> dict[str, Any]:
    return {
        "descriptor_id": venue.descriptor_id,
        "venue": venue.venue,
        "symbol": venue.symbol,
        "data_family": venue.data_family,
        "window": venue.window.to_payload(),
        "interval": venue.interval,
        "source_access_mode": venue.source_access_mode,
        "checksum_policy": venue.checksum_policy,
        "diagnostic_only": venue.diagnostic_only,
        "source_integrity": _path_independent_integrity(venue.source_integrity),
    }


def _path_independent_integrity(source_integrity: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in stable_payload(source_integrity).items()
        if "path" not in str(key).lower() and "root" not in str(key).lower()
    }
