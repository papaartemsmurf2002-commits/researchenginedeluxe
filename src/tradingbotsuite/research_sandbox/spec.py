from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from tradingbotsuite.research_sandbox.boundary import sandbox_boundary_metadata
from tradingbotsuite.research_sandbox.paths import validate_safe_path_component


MIN_SANDBOX_DATE = date(2024, 1, 1)
ALLOWED_VENUES = frozenset({"binance_usdm", "okx", "bybit", "hyperliquid", "local_manifest"})
VENUE_ALIASES: dict[str, str] = {
    "binance": "binance_usdm",
    "binancefutures": "binance_usdm",
    "binancefuture": "binance_usdm",
    "binanceperp": "binance_usdm",
    "binanceperps": "binance_usdm",
    "binanceum": "binance_usdm",
    "binanceusd": "binance_usdm",
    "binanceusdm": "binance_usdm",
    "binanceusdlinear": "binance_usdm",
    "binanceusdmargin": "binance_usdm",
    "binanceusdmswap": "binance_usdm",
    "um": "binance_usdm",
    "usdm": "binance_usdm",
    "okex": "okx",
    "okx": "okx",
    "okxperp": "okx",
    "okxperps": "okx",
    "okxperpetual": "okx",
    "okxswap": "okx",
    "bybit": "bybit",
    "bybitlinear": "bybit",
    "bybitperp": "bybit",
    "bybitperps": "bybit",
    "bybitperpetual": "bybit",
    "bybitusdm": "bybit",
    "bybitusdt": "bybit",
    "bybitusdtlinear": "bybit",
    "hl": "hyperliquid",
    "hlperp": "hyperliquid",
    "hlperps": "hyperliquid",
    "hyperliquid": "hyperliquid",
    "hyperliquidperp": "hyperliquid",
    "hyperliquidperps": "hyperliquid",
    "hyperliquidperpetual": "hyperliquid",
}
ALLOWED_DATA_FAMILIES = frozenset(
    {
        "kline",
        "trade",
        "agg_trade",
        "funding",
        "open_interest",
        "mark_index",
        "l2_book",
        "asset_context",
        "mixed",
    }
)
ALLOWED_EXIT_PROFILES = frozenset({"fixed_hold", "target_only", "stop_only", "target_stop_conservative"})


class ValidationProfile(StrEnum):
    SCRATCH = "scratch"
    SANDBOX_FAST = "sandbox_fast"
    SCREENING_REQUEST_ONLY = "screening_request_only"


def _coerce_date(value: date | datetime | str, *, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError as exc:
            raise ValueError(f"{field_name} must be ISO date or datetime") from exc
    raise TypeError(f"{field_name} must be date, datetime, or ISO string")


def _normalized_identity_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def canonical_venue(value: str) -> str:
    normalized = _normalized_identity_token(value)
    venue = VENUE_ALIASES.get(normalized)
    if venue is None and normalized in {_normalized_identity_token(item) for item in ALLOWED_VENUES}:
        venue = next(item for item in ALLOWED_VENUES if _normalized_identity_token(item) == normalized)
    if venue is None:
        joined = ", ".join(sorted(ALLOWED_VENUES))
        raise ValueError(f"unsupported sandbox venue: {value}; expected one of: {joined}")
    return venue


def _stable_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value.as_posix())
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _stable_jsonable(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_stable_jsonable(item) for item in value]
    return value


@dataclass(frozen=True)
class DataWindow:
    start: date | datetime | str
    end: date | datetime | str

    def __post_init__(self) -> None:
        start = _coerce_date(self.start, field_name="start")
        end = _coerce_date(self.end, field_name="end")
        if start < MIN_SANDBOX_DATE:
            raise ValueError("sandbox data windows must start on or after 2024-01-01")
        if end < start:
            raise ValueError("sandbox data window end must be on or after start")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    def to_payload(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}


@dataclass(frozen=True)
class VenueArchiveDescriptor:
    descriptor_id: str
    venue: str
    symbol: str
    data_family: str
    window: DataWindow
    manifest_path: Path | None = None
    data_path: Path | None = None
    interval: str | None = None
    source_access_mode: str = "archive_or_manifest"
    checksum_policy: str = "required_for_strict_evidence"
    diagnostic_only: bool = True
    source_integrity: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        venue = canonical_venue(self.venue)
        data_family = self.data_family.lower()
        if data_family not in ALLOWED_DATA_FAMILIES:
            raise ValueError(f"unsupported sandbox data family: {self.data_family}")
        if not self.descriptor_id.strip():
            raise ValueError("venue descriptor_id is required")
        if not self.symbol.strip():
            raise ValueError("venue symbol is required")
        object.__setattr__(self, "venue", venue)
        object.__setattr__(self, "data_family", data_family)
        if self.manifest_path is not None:
            object.__setattr__(self, "manifest_path", Path(self.manifest_path))
        if self.data_path is not None:
            object.__setattr__(self, "data_path", Path(self.data_path))
        object.__setattr__(self, "source_integrity", dict(self.source_integrity))
        object.__setattr__(self, "notes", tuple(self.notes))

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            **sandbox_boundary_metadata(),
            "descriptor_id": self.descriptor_id,
            "venue": self.venue,
            "symbol": self.symbol,
            "data_family": self.data_family,
            "window": self.window.to_payload(),
            "interval": self.interval,
            "source_access_mode": self.source_access_mode,
            "checksum_policy": self.checksum_policy,
            "diagnostic_only": self.diagnostic_only,
            "notes": list(self.notes),
        }
        if self.manifest_path is not None:
            payload["manifest_path"] = str(self.manifest_path)
        if self.data_path is not None:
            payload["data_path"] = str(self.data_path)
        if self.source_integrity:
            payload["source_integrity"] = _stable_jsonable(self.source_integrity)
        return payload


@dataclass(frozen=True)
class StrategyCatalogRow:
    hypothesis_id: str
    family: str
    signal_column: str
    side: str = "long"
    source_id: str = "manual_catalog"
    exit_profile: str = "fixed_hold"
    filter_column: str | None = None
    filter_min: float | None = None
    filter_max: float | None = None
    params: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        side = self.side.lower()
        if side not in {"long", "short"}:
            raise ValueError("sandbox strategy side must be 'long' or 'short'")
        if not self.hypothesis_id.strip():
            raise ValueError("strategy hypothesis_id is required")
        if not self.family.strip():
            raise ValueError("strategy family is required")
        if not self.signal_column.strip():
            raise ValueError("strategy signal_column is required")
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "params", dict(self.params))
        object.__setattr__(self, "tags", tuple(self.tags))

    def to_payload(self) -> dict[str, Any]:
        return {
            **sandbox_boundary_metadata(),
            "hypothesis_id": self.hypothesis_id,
            "family": self.family,
            "source_id": self.source_id,
            "signal_column": self.signal_column,
            "side": self.side,
            "exit_profile": self.exit_profile,
            "filter_column": self.filter_column,
            "filter_min": self.filter_min,
            "filter_max": self.filter_max,
            "params": _stable_jsonable(self.params),
            "tags": list(self.tags),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ExitVariant:
    variant_id: str
    exit_profile: str = "fixed_hold"
    target_return: float | None = None
    stop_return: float | None = None

    def __post_init__(self) -> None:
        if not self.variant_id.strip():
            raise ValueError("exit variant_id is required")
        profile = self.exit_profile.lower()
        if profile not in ALLOWED_EXIT_PROFILES:
            raise ValueError(f"unsupported sandbox exit_profile: {self.exit_profile}")
        if profile in {"target_only", "target_stop_conservative"} and self.target_return is None:
            raise ValueError(f"{profile} requires target_return")
        if profile in {"stop_only", "target_stop_conservative"} and self.stop_return is None:
            raise ValueError(f"{profile} requires stop_return")
        if self.target_return is not None and self.target_return <= 0:
            raise ValueError("target_return must be positive")
        if self.stop_return is not None and self.stop_return <= 0:
            raise ValueError("stop_return must be positive")
        object.__setattr__(self, "exit_profile", profile)

    def to_payload(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "exit_profile": self.exit_profile,
            "target_return": self.target_return,
            "stop_return": self.stop_return,
        }


@dataclass(frozen=True)
class FilterVariant:
    variant_id: str
    filter_column: str | None = None
    filter_min: float | None = None
    filter_max: float | None = None

    def __post_init__(self) -> None:
        if not self.variant_id.strip():
            raise ValueError("filter variant_id is required")
        if self.filter_column is not None and not self.filter_column.strip():
            raise ValueError("filter_column must be non-empty when supplied")
        if self.filter_min is not None:
            object.__setattr__(self, "filter_min", float(self.filter_min))
        if self.filter_max is not None:
            object.__setattr__(self, "filter_max", float(self.filter_max))
        if self.filter_min is not None and self.filter_max is not None and self.filter_max < self.filter_min:
            raise ValueError("filter_max must be greater than or equal to filter_min")

    def to_payload(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "filter_column": self.filter_column,
            "filter_min": self.filter_min,
            "filter_max": self.filter_max,
        }


def _coerce_exit_variant(value: ExitVariant | dict[str, Any] | str) -> ExitVariant:
    if isinstance(value, ExitVariant):
        return value
    if isinstance(value, str):
        return ExitVariant(variant_id=value, exit_profile=value)
    if isinstance(value, dict):
        return ExitVariant(
            variant_id=str(value.get("variant_id") or value.get("exit_profile") or "exit"),
            exit_profile=str(value.get("exit_profile", "fixed_hold")),
            target_return=float(value["target_return"]) if value.get("target_return") is not None else None,
            stop_return=float(value["stop_return"]) if value.get("stop_return") is not None else None,
        )
    raise TypeError("exit variants must be ExitVariant, mapping, or string")


def _coerce_filter_variant(value: FilterVariant | dict[str, Any] | str) -> FilterVariant:
    if isinstance(value, FilterVariant):
        return value
    if isinstance(value, str):
        return FilterVariant(variant_id=value)
    if isinstance(value, dict):
        return FilterVariant(
            variant_id=str(value.get("variant_id") or value.get("filter_column") or "filter"),
            filter_column=str(value["filter_column"]) if value.get("filter_column") is not None else None,
            filter_min=float(value["filter_min"]) if value.get("filter_min") is not None else None,
            filter_max=float(value["filter_max"]) if value.get("filter_max") is not None else None,
        )
    raise TypeError("filter variants must be FilterVariant, mapping, or string")


@dataclass(frozen=True)
class SandboxRunSpec:
    run_id: str
    data_window: DataWindow
    validation_profile: ValidationProfile = ValidationProfile.SANDBOX_FAST
    holding_periods: tuple[int, ...] = (1, 2, 4, 8)
    exit_variants: tuple[ExitVariant | dict[str, Any] | str, ...] = field(
        default_factory=lambda: (ExitVariant(variant_id="fixed_hold", exit_profile="fixed_hold"),)
    )
    filter_variants: tuple[FilterVariant | dict[str, Any] | str, ...] = field(
        default_factory=lambda: (FilterVariant(variant_id="base"),)
    )
    round_trip_cost_bps: float = 8.0
    min_trades: int = 5
    max_evidence_requests: int = 10
    rank_top_n: int = 100
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""

    def __post_init__(self) -> None:
        run_id = validate_safe_path_component(self.run_id, field_name="sandbox run_id")
        try:
            profile = ValidationProfile(self.validation_profile)
        except ValueError as exc:
            raise ValueError(f"unsupported sandbox validation_profile: {self.validation_profile}") from exc
        if not self.holding_periods:
            raise ValueError("at least one holding period is required")
        holding_periods = tuple(int(value) for value in self.holding_periods)
        if any(value <= 0 for value in holding_periods):
            raise ValueError("holding periods must be positive")
        exit_variants = tuple(_coerce_exit_variant(value) for value in self.exit_variants)
        if not exit_variants:
            raise ValueError("at least one exit variant is required")
        filter_variants = tuple(_coerce_filter_variant(value) for value in self.filter_variants)
        if not filter_variants:
            raise ValueError("at least one filter variant is required")
        if self.round_trip_cost_bps < 0:
            raise ValueError("round_trip_cost_bps must be non-negative")
        if self.min_trades < 0:
            raise ValueError("min_trades must be non-negative")
        if self.max_evidence_requests < 0:
            raise ValueError("max_evidence_requests must be non-negative")
        if self.rank_top_n <= 0:
            raise ValueError("rank_top_n must be positive")
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "validation_profile", profile)
        object.__setattr__(self, "holding_periods", holding_periods)
        object.__setattr__(self, "exit_variants", exit_variants)
        object.__setattr__(self, "filter_variants", filter_variants)
        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=timezone.utc))

    def to_payload(self) -> dict[str, Any]:
        return {
            **sandbox_boundary_metadata(),
            "run_id": self.run_id,
            "data_window": self.data_window.to_payload(),
            "validation_profile": self.validation_profile.value,
            "holding_periods": list(self.holding_periods),
            "exit_variants": [variant.to_payload() for variant in self.exit_variants],
            "filter_variants": [variant.to_payload() for variant in self.filter_variants],
            "round_trip_cost_bps": self.round_trip_cost_bps,
            "min_trades": self.min_trades,
            "max_evidence_requests": self.max_evidence_requests,
            "rank_top_n": self.rank_top_n,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
        }


def stable_payload(value: Any) -> Any:
    return _stable_jsonable(value)
