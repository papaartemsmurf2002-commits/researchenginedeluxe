# V2-AUDIT-ID: V2-AUD-CONTRACTS-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, utc_timestamps, no_live_imports
# V2-OWNER: v2_config
"""UTC timestamp helpers for v2."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("v2 timestamps must be timezone-aware UTC values")
    return value.astimezone(UTC)


def utc_isoformat(value: datetime) -> str:
    return ensure_utc(value).isoformat().replace("+00:00", "Z")
