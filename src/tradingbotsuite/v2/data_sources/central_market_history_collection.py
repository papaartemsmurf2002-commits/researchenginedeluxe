# V2-AUDIT-ID: V2-AUD-DATASRC-061, V2-AUD-DATASRC-069
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md, docs/contracts/autonomous_readiness_contract.md
# V2-BOUNDARY: research_only, central_market_history_store, no_live_imports
# V2-OWNER: v2_data_sources
"""Bounded public/archive collection helpers for central market history."""

from __future__ import annotations

import csv
import gzip
import io
import json
import threading
import zipfile
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_now
from tradingbotsuite.v2.data_sources.central_market_history import (
    CENTRAL_MARKET_HISTORY_DEFAULT_ROOT,
    CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
    CentralMarketHistoryFamily,
    CentralMarketHistoryRow,
    CentralMarketHistorySourceMetadata,
    CentralMarketHistoryWriteResult,
    central_market_history_row_from_event,
    central_market_history_row_from_ohlcv,
    write_central_market_history_batch,
    write_central_market_history_event_payload_batch,
)
from tradingbotsuite.v2.security.boundary import require_research_boundary

CENTRAL_MARKET_HISTORY_MAX_BYTES = 300 * 1024**3
BINANCE_VISION_BASE_URL = "https://data.binance.vision/data"
BYBIT_PUBLIC_BASE_URL = "https://public.bybit.com"
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
_COLLECTION_PROGRESS_LOCK = threading.Lock()


class CentralMarketHistorySourceKind(str, Enum):
    BINANCE_KLINE_ZIP = "binance_kline_zip"
    BINANCE_AGG_TRADES_ZIP = "binance_agg_trades_zip"
    BINANCE_TRADES_ZIP = "binance_trades_zip"
    BINANCE_BOOK_DEPTH_ZIP = "binance_book_depth_zip"
    BINANCE_BOOK_TICKER_ZIP = "binance_book_ticker_zip"
    BYBIT_TRADING_GZIP = "bybit_trading_gzip"
    BYBIT_INDEX_GZIP = "bybit_index_gzip"
    BYBIT_MT4_KLINE_GZIP = "bybit_mt4_kline_gzip"
    BYBIT_KLINE_API_JSON = "bybit_kline_api_json"
    HYPERLIQUID_CANDLES_JSON = "hyperliquid_candles_json"
    HYPERLIQUID_METADATA_JSON = "hyperliquid_metadata_json"


class CentralMarketHistoryBudgetReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    report_type: str = "central_market_history_storage_budget"
    root_ref: str = Field(min_length=1)
    max_bytes: int = Field(gt=0)
    current_bytes: int = Field(ge=0)
    planned_bytes: int = Field(ge=0)
    remaining_bytes: int
    within_budget: bool
    created_at: datetime = Field(default_factory=utc_now)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_budget(self) -> "CentralMarketHistoryBudgetReport":
        require_research_boundary(self, context="central market-history storage budget")
        expected_remaining = self.max_bytes - self.current_bytes - self.planned_bytes
        if self.remaining_bytes != expected_remaining:
            raise ValueError("remaining_bytes must equal max-current-planned")
        if self.within_budget != (expected_remaining >= 0):
            raise ValueError("within_budget does not match remaining_bytes")
        return self


class CentralMarketHistorySourcePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    provider: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_kind: CentralMarketHistorySourceKind
    url: str = Field(min_length=1)
    raw_ref: str = Field(min_length=1)
    normalized_symbol: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    timeframe: str | None = None
    family: CentralMarketHistoryFamily
    expected_bytes: int | None = Field(default=None, ge=0)
    normalized_row_limit: int | None = Field(default=None, ge=1)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("provider", "source_id")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("normalized_symbol", "venue_symbol")
    @classmethod
    def _strip_upper(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("timeframe")
    @classmethod
    def _strip_timeframe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _validate_plan(self) -> "CentralMarketHistorySourcePlan":
        require_research_boundary(self, context="central market-history source plan")
        if self.family == CentralMarketHistoryFamily.OHLCV and not self.timeframe:
            raise ValueError("OHLCV source plans require timeframe")
        return self


class CentralMarketHistoryProbeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    provider: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_kind: CentralMarketHistorySourceKind
    url: str = Field(min_length=1)
    normalized_symbol: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    timeframe: str | None = None
    status: str = Field(min_length=1)
    http_status: int | None = Field(default=None, ge=100, le=599)
    bytes: int | None = Field(default=None, ge=0)
    raw_ref: str | None = None
    raw_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    row_count: int = Field(default=0, ge=0)
    reason: str | None = None
    as_of: datetime = Field(default_factory=utc_now)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("as_of")
    @classmethod
    def _utc_as_of(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_probe(self) -> "CentralMarketHistoryProbeRecord":
        require_research_boundary(self, context="central market-history probe record")
        return self


class CentralMarketHistoryDiscoveryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    report_type: str = "central_market_history_source_discovery_report"
    report_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    root_ref: str = Field(min_length=1)
    budget_report: CentralMarketHistoryBudgetReport
    probe_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    probes: tuple[CentralMarketHistoryProbeRecord, ...] = ()
    blockers: tuple[CentralMarketHistoryProbeRecord, ...] = ()
    central_batch_manifest_ref: str | None = None
    centralized_market_history_ready: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> "CentralMarketHistoryDiscoveryReport":
        require_research_boundary(self, context="central market-history discovery report")
        if self.probe_count != len(self.probes):
            raise ValueError("probe_count must equal probes length")
        if self.blocker_count != len(self.blockers):
            raise ValueError("blocker_count must equal blockers length")
        if self.completed_count != sum(1 for probe in self.probes if probe.status in {"downloaded", "cache_hit"}):
            raise ValueError("completed_count must match completed probes")
        expected_id = central_market_history_discovery_report_id_for(self)
        if self.report_id != expected_id:
            raise ValueError("report_id does not match discovery report")
        return self


class CentralMarketHistoryBatchPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    run_id: str = Field(min_length=1)
    source_plans: tuple[CentralMarketHistorySourcePlan, ...] = Field(min_length=1)
    notes: tuple[str, ...] = ()
    coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
    equivalence_tolerance: float = Field(default=0.05, ge=0.0)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_batch_plan(self) -> "CentralMarketHistoryBatchPlan":
        require_research_boundary(self, context="central market-history batch plan")
        return self


class CentralMarketHistoryCollectionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    result_type: str = "central_market_history_collection_result"
    run_id: str = Field(min_length=1)
    probe_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    parsed_row_count: int = Field(ge=0)
    manifest_ref: str | None = None
    manifest_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    quality_report_ref: str | None = None
    discovery_report_ref: str | None = None
    telemetry_ref: str | None = None
    existing_batch: bool = False
    statuses: tuple[str, ...] = ()
    centralized_market_history_ready: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("created_at")
    @classmethod
    def _utc_created_at(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_collection_result(self) -> "CentralMarketHistoryCollectionResult":
        require_research_boundary(self, context="central market-history collection result")
        return self


class CentralMarketHistoryCollectionLedgerEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    provider: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    family: CentralMarketHistoryFamily
    normalized_symbol: str = Field(min_length=1)
    venue_symbol: str | None = None
    timeframe: str | None = None
    start: str = Field(min_length=1)
    end: str = Field(min_length=1)
    status: str = Field(min_length=1)
    source_count: int = Field(ge=0)
    collected_source_count: int = Field(ge=0)
    unavailable_source_count: int = Field(default=0, ge=0)
    budget_blocked_source_count: int = Field(default=0, ge=0)
    unsupported_source_count: int = Field(default=0, ge=0)
    operator_gated_source_count: int = Field(default=0, ge=0)
    parsed_row_count: int = Field(default=0, ge=0)
    normalized_row_limit: int | None = Field(default=None, ge=1)
    raw_archive_complete: bool = False
    normalized_archive_complete: bool = False
    backtest_usable: bool = False
    partial_data_testing_allowed: bool = False
    strategy_must_call_off_if_required: bool = True
    reason: str = Field(min_length=1)
    manifest_refs: tuple[str, ...] = ()
    discovery_report_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("provider", "source_id")
    @classmethod
    def _lower_tokens(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("normalized_symbol", "venue_symbol")
    @classmethod
    def _upper_tokens(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped.upper() if stripped else None

    @field_validator("timeframe")
    @classmethod
    def _normalize_timeframe_token(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _validate_entry(self) -> "CentralMarketHistoryCollectionLedgerEntry":
        require_research_boundary(self, context="central market-history collection ledger entry")
        if self.status not in {
            "collected",
            "partial",
            "unavailable",
            "budget_blocked",
            "unsupported",
            "operator_gated",
        }:
            raise ValueError("unsupported collection ledger status")
        if self.collected_source_count > self.source_count:
            raise ValueError("collected_source_count cannot exceed source_count")
        blocked_total = (
            self.collected_source_count
            + self.unavailable_source_count
            + self.budget_blocked_source_count
            + self.unsupported_source_count
            + self.operator_gated_source_count
        )
        if blocked_total > self.source_count:
            raise ValueError("ledger source counts cannot exceed source_count")
        if self.normalized_archive_complete and not self.raw_archive_complete:
            raise ValueError("normalized archive cannot be complete when raw archive is incomplete")
        if self.backtest_usable and not self.normalized_archive_complete:
            raise ValueError("backtest usable entries require complete normalized archives")
        if self.strategy_must_call_off_if_required and self.backtest_usable:
            raise ValueError("backtest usable entries cannot require strategy call-off")
        if self.partial_data_testing_allowed and self.backtest_usable:
            raise ValueError("partial-data testing entries cannot also be complete backtest usable entries")
        return self


class CentralMarketHistoryCollectionLedger(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    report_type: str = "central_market_history_collection_ledger"
    ledger_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    root_ref: str = Field(min_length=1)
    entries: tuple[CentralMarketHistoryCollectionLedgerEntry, ...] = ()
    entry_count: int = Field(ge=0)
    collected_entry_count: int = Field(ge=0)
    partial_entry_count: int = Field(ge=0)
    unavailable_entry_count: int = Field(ge=0)
    budget_blocked_entry_count: int = Field(ge=0)
    unsupported_entry_count: int = Field(ge=0)
    operator_gated_entry_count: int = Field(ge=0)
    backtest_usable_entry_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("created_at")
    @classmethod
    def _utc_created_at(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_ledger(self) -> "CentralMarketHistoryCollectionLedger":
        require_research_boundary(self, context="central market-history collection ledger")
        if self.entry_count != len(self.entries):
            raise ValueError("entry_count must equal entries length")
        if self.collected_entry_count != sum(1 for entry in self.entries if entry.status == "collected"):
            raise ValueError("collected_entry_count does not match entries")
        if self.partial_entry_count != sum(1 for entry in self.entries if entry.status == "partial"):
            raise ValueError("partial_entry_count does not match entries")
        if self.unavailable_entry_count != sum(1 for entry in self.entries if entry.status == "unavailable"):
            raise ValueError("unavailable_entry_count does not match entries")
        if self.budget_blocked_entry_count != sum(1 for entry in self.entries if entry.status == "budget_blocked"):
            raise ValueError("budget_blocked_entry_count does not match entries")
        if self.unsupported_entry_count != sum(1 for entry in self.entries if entry.status == "unsupported"):
            raise ValueError("unsupported_entry_count does not match entries")
        if self.operator_gated_entry_count != sum(1 for entry in self.entries if entry.status == "operator_gated"):
            raise ValueError("operator_gated_entry_count does not match entries")
        if self.backtest_usable_entry_count != sum(1 for entry in self.entries if entry.backtest_usable):
            raise ValueError("backtest_usable_entry_count does not match entries")
        expected_id = central_market_history_collection_ledger_id_for(self)
        if self.ledger_id != expected_id:
            raise ValueError("ledger_id does not match collection ledger")
        return self


def central_market_history_tree_bytes(root: str | Path) -> int:
    root_path = Path(root)
    if not root_path.exists():
        return 0
    return sum(path.stat().st_size for path in root_path.rglob("*") if path.is_file())


def central_market_history_budget_report(
    root: str | Path = CENTRAL_MARKET_HISTORY_DEFAULT_ROOT,
    *,
    max_bytes: int = CENTRAL_MARKET_HISTORY_MAX_BYTES,
    planned_bytes: int = 0,
) -> CentralMarketHistoryBudgetReport:
    root_path = Path(root).resolve(strict=False)
    current = central_market_history_tree_bytes(root_path)
    remaining = max_bytes - current - planned_bytes
    return CentralMarketHistoryBudgetReport(
        root_ref=str(root_path),
        max_bytes=max_bytes,
        current_bytes=current,
        planned_bytes=planned_bytes,
        remaining_bytes=remaining,
        within_budget=remaining >= 0,
    )


def require_central_market_history_budget(
    root: str | Path = CENTRAL_MARKET_HISTORY_DEFAULT_ROOT,
    *,
    max_bytes: int = CENTRAL_MARKET_HISTORY_MAX_BYTES,
    planned_bytes: int = 0,
) -> CentralMarketHistoryBudgetReport:
    report = central_market_history_budget_report(root, max_bytes=max_bytes, planned_bytes=planned_bytes)
    if not report.within_budget:
        raise ValueError(
            "central market-history storage budget exceeded: "
            f"current={report.current_bytes} planned={report.planned_bytes} max={report.max_bytes}"
        )
    return report


def build_binance_monthly_kline_plan(
    *,
    market: str,
    normalized_symbol: str,
    venue_symbol: str,
    interval: str,
    period: str,
    raw_prefix: str,
) -> CentralMarketHistorySourcePlan:
    market_token = market.strip().lower()
    if market_token not in {"futures_um", "spot"}:
        raise ValueError("market must be futures_um or spot")
    if market_token == "futures_um":
        provider = "binance_usdm"
        market_path = "futures/um"
    else:
        provider = "binance_spot"
        market_path = "spot"
    venue = venue_symbol.strip().upper()
    interval = interval.strip()
    url = f"{BINANCE_VISION_BASE_URL}/{market_path}/monthly/klines/{venue}/{interval}/{venue}-{interval}-{period}.zip"
    return CentralMarketHistorySourcePlan(
        provider=provider,
        source_id=f"binance_vision_{market_token}_monthly_klines_archive",
        source_kind=CentralMarketHistorySourceKind.BINANCE_KLINE_ZIP,
        url=url,
        raw_ref=f"{raw_prefix}/binance_vision/{market_token}/monthly/klines/{venue}/{interval}/{venue}-{interval}-{period}.zip",
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        timeframe=interval,
        family=CentralMarketHistoryFamily.OHLCV,
    )


def build_binance_daily_agg_trades_plan(
    *,
    market: str,
    normalized_symbol: str,
    venue_symbol: str,
    day: str,
    raw_prefix: str,
    normalized_row_limit: int | None = None,
) -> CentralMarketHistorySourcePlan:
    market_token = market.strip().lower()
    if market_token not in {"futures_um", "spot"}:
        raise ValueError("market must be futures_um or spot")
    if market_token == "futures_um":
        provider = "binance_usdm"
        market_path = "futures/um"
    else:
        provider = "binance_spot"
        market_path = "spot"
    venue = venue_symbol.strip().upper()
    url = f"{BINANCE_VISION_BASE_URL}/{market_path}/daily/aggTrades/{venue}/{venue}-aggTrades-{day}.zip"
    return CentralMarketHistorySourcePlan(
        provider=provider,
        source_id=f"binance_vision_{market_token}_daily_agg_trades_archive",
        source_kind=CentralMarketHistorySourceKind.BINANCE_AGG_TRADES_ZIP,
        url=url,
        raw_ref=f"{raw_prefix}/binance_vision/{market_token}/daily/aggTrades/{venue}/{venue}-aggTrades-{day}.zip",
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        family=CentralMarketHistoryFamily.ORDERFLOW,
        normalized_row_limit=normalized_row_limit,
    )


def build_binance_daily_trades_plan(
    *,
    market: str,
    normalized_symbol: str,
    venue_symbol: str,
    day: str,
    raw_prefix: str,
    normalized_row_limit: int | None = None,
) -> CentralMarketHistorySourcePlan:
    market_token = market.strip().lower()
    if market_token not in {"futures_um", "spot"}:
        raise ValueError("market must be futures_um or spot")
    if market_token == "futures_um":
        provider = "binance_usdm"
        market_path = "futures/um"
    else:
        provider = "binance_spot"
        market_path = "spot"
    venue = venue_symbol.strip().upper()
    url = f"{BINANCE_VISION_BASE_URL}/{market_path}/daily/trades/{venue}/{venue}-trades-{day}.zip"
    return CentralMarketHistorySourcePlan(
        provider=provider,
        source_id=f"binance_vision_{market_token}_daily_trades_archive",
        source_kind=CentralMarketHistorySourceKind.BINANCE_TRADES_ZIP,
        url=url,
        raw_ref=f"{raw_prefix}/binance_vision/{market_token}/daily/trades/{venue}/{venue}-trades-{day}.zip",
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        family=CentralMarketHistoryFamily.TRADE,
        normalized_row_limit=normalized_row_limit,
    )


def build_binance_daily_book_depth_plan(
    *,
    normalized_symbol: str,
    venue_symbol: str,
    day: str,
    raw_prefix: str,
    normalized_row_limit: int | None = None,
) -> CentralMarketHistorySourcePlan:
    venue = venue_symbol.strip().upper()
    url = f"{BINANCE_VISION_BASE_URL}/futures/um/daily/bookDepth/{venue}/{venue}-bookDepth-{day}.zip"
    return CentralMarketHistorySourcePlan(
        provider="binance_usdm",
        source_id="binance_vision_futures_um_daily_book_depth_archive",
        source_kind=CentralMarketHistorySourceKind.BINANCE_BOOK_DEPTH_ZIP,
        url=url,
        raw_ref=f"{raw_prefix}/binance_vision/futures_um/daily/bookDepth/{venue}/{venue}-bookDepth-{day}.zip",
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        family=CentralMarketHistoryFamily.BOOK,
        normalized_row_limit=normalized_row_limit,
    )


def build_binance_daily_book_ticker_plan(
    *,
    normalized_symbol: str,
    venue_symbol: str,
    day: str,
    raw_prefix: str,
    normalized_row_limit: int | None = None,
) -> CentralMarketHistorySourcePlan:
    venue = venue_symbol.strip().upper()
    url = f"{BINANCE_VISION_BASE_URL}/futures/um/daily/bookTicker/{venue}/{venue}-bookTicker-{day}.zip"
    return CentralMarketHistorySourcePlan(
        provider="binance_usdm",
        source_id="binance_vision_futures_um_daily_book_ticker_archive",
        source_kind=CentralMarketHistorySourceKind.BINANCE_BOOK_TICKER_ZIP,
        url=url,
        raw_ref=f"{raw_prefix}/binance_vision/futures_um/daily/bookTicker/{venue}/{venue}-bookTicker-{day}.zip",
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        family=CentralMarketHistoryFamily.BOOK,
        normalized_row_limit=normalized_row_limit,
    )


def build_bybit_public_trading_plan(
    *,
    normalized_symbol: str,
    venue_symbol: str,
    day: str,
    raw_prefix: str,
    normalized_row_limit: int | None = None,
) -> CentralMarketHistorySourcePlan:
    venue = venue_symbol.strip().upper()
    url = f"{BYBIT_PUBLIC_BASE_URL}/trading/{venue}/{venue}{day}.csv.gz"
    return CentralMarketHistorySourcePlan(
        provider="bybit_linear",
        source_id="bybit_public_archive_trading",
        source_kind=CentralMarketHistorySourceKind.BYBIT_TRADING_GZIP,
        url=url,
        raw_ref=f"{raw_prefix}/bybit_public/trading/{venue}/{venue}{day}.csv.gz",
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        family=CentralMarketHistoryFamily.TRADE,
        normalized_row_limit=normalized_row_limit,
    )


def build_bybit_spot_monthly_trades_plan(
    *,
    normalized_symbol: str,
    venue_symbol: str,
    period: str,
    raw_prefix: str,
    normalized_row_limit: int | None = None,
) -> CentralMarketHistorySourcePlan:
    venue = venue_symbol.strip().upper()
    token = period.strip()
    filename = f"{venue}-{token}.csv.gz"
    return CentralMarketHistorySourcePlan(
        provider="bybit_spot",
        source_id="bybit_public_archive_spot_monthly_trades",
        source_kind=CentralMarketHistorySourceKind.BYBIT_TRADING_GZIP,
        url=f"{BYBIT_PUBLIC_BASE_URL}/spot/{venue}/{filename}",
        raw_ref=f"{raw_prefix}/bybit_public/spot/{venue}/{filename}",
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        family=CentralMarketHistoryFamily.TRADE,
        normalized_row_limit=normalized_row_limit,
    )


def build_bybit_index_plan(
    *,
    normalized_symbol: str,
    venue_symbol: str,
    day: str,
    index_kind: str,
    raw_prefix: str,
    normalized_row_limit: int | None = None,
) -> CentralMarketHistorySourcePlan:
    venue = venue_symbol.strip().upper()
    kind = index_kind.strip().lower()
    if kind == "premium_index":
        filename = f"{venue}{day}_premium_index.csv.gz"
        source_id = "bybit_public_archive_premium_index"
    elif kind == "spot_index":
        filename = f"{venue}{day}_index_price.csv.gz"
        source_id = "bybit_public_archive_spot_index"
    else:
        raise ValueError("index_kind must be premium_index or spot_index")
    url = f"{BYBIT_PUBLIC_BASE_URL}/{kind}/{venue}/{filename}"
    return CentralMarketHistorySourcePlan(
        provider="bybit_inverse",
        source_id=source_id,
        source_kind=CentralMarketHistorySourceKind.BYBIT_INDEX_GZIP,
        url=url,
        raw_ref=f"{raw_prefix}/bybit_public/{kind}/{venue}/{filename}",
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        timeframe="1m",
        family=CentralMarketHistoryFamily.METADATA,
        normalized_row_limit=normalized_row_limit,
    )


def build_bybit_mt4_kline_plan(
    *,
    normalized_symbol: str,
    venue_symbol: str,
    mt4_interval: str,
    period: str,
    raw_prefix: str,
) -> CentralMarketHistorySourcePlan:
    venue = venue_symbol.strip().upper()
    interval = mt4_interval.strip()
    start = datetime.strptime(period, "%Y-%m").replace(tzinfo=UTC)
    end_day = monthrange(start.year, start.month)[1]
    start_token = f"{start:%Y-%m}-01"
    end_token = f"{start:%Y-%m}-{end_day:02d}"
    url = (
        f"{BYBIT_PUBLIC_BASE_URL}/kline_for_metatrader4/{venue}/{start.year}/"
        f"{venue}_{interval}_{start_token}_{end_token}.csv.gz"
    )
    timeframe = f"{interval}m"
    return CentralMarketHistorySourcePlan(
        provider="bybit_linear",
        source_id="bybit_public_archive_kline_for_metatrader4",
        source_kind=CentralMarketHistorySourceKind.BYBIT_MT4_KLINE_GZIP,
        url=url,
        raw_ref=(
            f"{raw_prefix}/bybit_public/kline_for_metatrader4/{venue}/{start.year}/"
            f"{venue}_{interval}_{start_token}_{end_token}.csv.gz"
        ),
        normalized_symbol=normalized_symbol,
        venue_symbol=venue,
        timeframe=timeframe,
        family=CentralMarketHistoryFamily.OHLCV,
    )


def download_source_plan(
    plan: CentralMarketHistorySourcePlan,
    *,
    root: str | Path = CENTRAL_MARKET_HISTORY_DEFAULT_ROOT,
    max_bytes: int = CENTRAL_MARKET_HISTORY_MAX_BYTES,
    client: httpx.Client | None = None,
    timeout: float = 60.0,
    _budget_guard: "_CentralMarketHistoryBudgetGuard | None" = None,
) -> CentralMarketHistoryProbeRecord:
    root_path = Path(root).resolve(strict=False)
    raw_path = _safe_child(root_path, plan.raw_ref)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.name.endswith(".part"):
        return _probe_from_plan(plan, status="partial_ref_rejected", reason="raw_ref_must_not_end_with_part")
    if raw_path.exists():
        try:
            _validate_source_file(plan, raw_path)
        except ValueError:
            raw_path.unlink(missing_ok=True)
        else:
            size = raw_path.stat().st_size
            require_central_market_history_budget(root_path, max_bytes=max_bytes, planned_bytes=0)
            return _probe_from_plan(
                plan,
                status="cache_hit",
                bytes=size,
                raw_ref=_relative_ref(root_path, raw_path),
                raw_sha256=file_sha256(raw_path),
            )

    part_path = raw_path.with_name(raw_path.name + ".part")
    part_path.unlink(missing_ok=True)
    budget_guard = _budget_guard or _CentralMarketHistoryBudgetGuard(root_path, max_bytes)
    own_client = client is None
    http = client or httpx.Client(follow_redirects=True, timeout=timeout)
    reserved_bytes = 0
    try:
        head_status: int | None = None
        content_length: int | None = None
        try:
            head = http.head(plan.url)
            head_status = head.status_code
            content_length = _content_length(head.headers)
            if head.status_code >= 400:
                return _probe_from_plan(
                    plan,
                    status="http_error",
                    http_status=head.status_code,
                    bytes=content_length,
                    reason=f"http_status:{head.status_code}",
                )
        except httpx.HTTPError as exc:
                return _probe_from_plan(plan, status="probe_error", reason=type(exc).__name__)

        if content_length is not None:
            if not budget_guard.reserve(content_length):
                return _probe_from_plan(
                    plan,
                    status="budget_blocked",
                    http_status=head_status,
                    bytes=content_length,
                    reason=f"raw_file_exceeds_remaining_budget:{content_length}",
                )
            reserved_bytes = content_length

        try:
            with http.stream("GET", plan.url) as response:
                if response.status_code >= 400:
                    return _probe_from_plan(
                        plan,
                        status="http_error",
                        http_status=response.status_code,
                        bytes=_content_length(response.headers),
                        reason=f"http_status:{response.status_code}",
                    )
                written = 0
                with part_path.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        if not chunk:
                            continue
                        if content_length is None:
                            if not budget_guard.reserve(len(chunk)):
                                handle.close()
                                part_path.unlink(missing_ok=True)
                                return _probe_from_plan(
                                    plan,
                                    status="budget_blocked",
                                    http_status=response.status_code,
                                    bytes=written,
                                    reason="download_would_exceed_total_budget",
                                )
                            reserved_bytes += len(chunk)
                        elif written + len(chunk) > reserved_bytes:
                            additional = written + len(chunk) - reserved_bytes
                            if not budget_guard.reserve(additional):
                                handle.close()
                                part_path.unlink(missing_ok=True)
                                return _probe_from_plan(
                                    plan,
                                    status="budget_blocked",
                                    http_status=response.status_code,
                                    bytes=written,
                                    reason="download_would_exceed_total_budget",
                                )
                            reserved_bytes += additional
                        written += len(chunk)
                        handle.write(chunk)
        except httpx.HTTPError as exc:
            part_path.unlink(missing_ok=True)
            return _probe_from_plan(plan, status="download_error", reason=type(exc).__name__)

        try:
            _validate_source_file(plan, part_path, allow_part=True)
        except ValueError as exc:
            part_path.unlink(missing_ok=True)
            return _probe_from_plan(plan, status="download_error", bytes=written, reason=str(exc))
        part_path.replace(raw_path)
        budget_guard.commit(reserved_bytes=reserved_bytes, actual_bytes=raw_path.stat().st_size)
        reserved_bytes = 0
        return _probe_from_plan(
            plan,
            status="downloaded",
            http_status=200,
            bytes=raw_path.stat().st_size,
            raw_ref=_relative_ref(root_path, raw_path),
            raw_sha256=file_sha256(raw_path),
        )
    finally:
        if reserved_bytes:
            budget_guard.release(reserved_bytes)
        part_path.unlink(missing_ok=True)
        if own_client:
            http.close()


def download_source_plans_parallel(
    plans: Sequence[CentralMarketHistorySourcePlan],
    *,
    root: str | Path = CENTRAL_MARKET_HISTORY_DEFAULT_ROOT,
    max_bytes: int = CENTRAL_MARKET_HISTORY_MAX_BYTES,
    concurrency: int = 4,
    timeout: float = 60.0,
    progress_path: str | Path | None = None,
) -> tuple[CentralMarketHistoryProbeRecord, ...]:
    if concurrency <= 0:
        raise ValueError("concurrency must be positive")
    root_path = Path(root).resolve(strict=False)
    ordered_plans = tuple(plans)
    if not ordered_plans:
        return ()
    guard = _CentralMarketHistoryBudgetGuard(root_path, max_bytes)
    progress = Path(progress_path).resolve(strict=False) if progress_path else None
    _append_progress(
        progress,
        event="download_batch_started",
        total=len(ordered_plans),
        concurrency=min(concurrency, len(ordered_plans)),
        root_ref=str(root_path),
        max_bytes=max_bytes,
    )
    results: dict[int, CentralMarketHistoryProbeRecord] = {}
    with ThreadPoolExecutor(max_workers=min(concurrency, len(ordered_plans))) as executor:
        futures = {}
        for index, plan in enumerate(ordered_plans):
            _append_progress(progress, event="download_started", index=index, raw_ref=plan.raw_ref, url=plan.url)
            futures[
                executor.submit(
                    download_source_plan,
                    plan,
                    root=root_path,
                    max_bytes=max_bytes,
                    timeout=timeout,
                    _budget_guard=guard,
                )
            ] = (index, plan)
        completed = 0
        for future in as_completed(futures):
            index, plan = futures[future]
            try:
                probe = future.result()
            except Exception as exc:  # noqa: BLE001 - source discovery must preserve worker anomalies as blockers.
                probe = _probe_from_plan(plan, status="worker_error", reason=type(exc).__name__)
            results[index] = probe
            completed += 1
            _append_progress(
                progress,
                event="download_completed",
                index=index,
                completed=completed,
                total=len(ordered_plans),
                status=probe.status,
                raw_ref=probe.raw_ref,
                bytes=probe.bytes,
                reason=probe.reason,
            )
    ordered_results = tuple(results[index] for index in range(len(ordered_plans)))
    _append_progress(
        progress,
        event="download_batch_completed",
        total=len(ordered_results),
        completed=sum(1 for probe in ordered_results if probe.status in {"downloaded", "cache_hit"}),
        blockers=sum(1 for probe in ordered_results if probe.status not in {"downloaded", "cache_hit"}),
    )
    return ordered_results


def collect_central_market_history_batch(
    *,
    root: str | Path,
    batch_plan: CentralMarketHistoryBatchPlan,
    max_bytes: int = CENTRAL_MARKET_HISTORY_MAX_BYTES,
    download_concurrency: int = 4,
    timeout: float = 60.0,
    telemetry_ref: str | None = None,
) -> CentralMarketHistoryCollectionResult:
    return collect_central_market_history_batches(
        root=root,
        batch_plans=(batch_plan,),
        max_bytes=max_bytes,
        download_concurrency=download_concurrency,
        timeout=timeout,
        telemetry_ref=telemetry_ref,
    )[0]


def collect_central_market_history_batches(
    *,
    root: str | Path,
    batch_plans: Sequence[CentralMarketHistoryBatchPlan],
    max_bytes: int = CENTRAL_MARKET_HISTORY_MAX_BYTES,
    download_concurrency: int = 4,
    timeout: float = 60.0,
    telemetry_ref: str | None = None,
) -> tuple[CentralMarketHistoryCollectionResult, ...]:
    root_path = Path(root).resolve(strict=False)
    if download_concurrency <= 0:
        raise ValueError("download_concurrency must be positive")
    parsed_batch_plans = tuple(batch_plans)
    if not parsed_batch_plans:
        return ()
    telemetry_path = _telemetry_path(root_path, telemetry_ref)
    _append_progress(
        telemetry_path,
        event="collection_started",
        root_ref=str(root_path),
        batch_count=len(parsed_batch_plans),
        max_bytes=max_bytes,
        download_concurrency=download_concurrency,
    )

    existing_by_run_id: dict[str, CentralMarketHistoryCollectionResult] = {}
    pending_batches: list[CentralMarketHistoryBatchPlan] = []
    for batch in parsed_batch_plans:
        existing = _existing_collection_result_for_run_id(root_path, batch.run_id, telemetry_path)
        if existing is None:
            pending_batches.append(batch)
        else:
            existing_by_run_id[batch.run_id] = existing
            _append_progress(telemetry_path, event="batch_skipped_existing", run_id=batch.run_id)

    plan_by_key: dict[tuple[str, str, str], CentralMarketHistorySourcePlan] = {}
    for batch in pending_batches:
        for plan in batch.source_plans:
            plan_by_key.setdefault(_source_plan_key(plan), plan)
    downloaded_by_key: dict[tuple[str, str, str], CentralMarketHistoryProbeRecord] = {}
    if plan_by_key:
        download_results = download_source_plans_parallel(
            tuple(plan_by_key.values()),
            root=root_path,
            max_bytes=max_bytes,
            concurrency=download_concurrency,
            timeout=timeout,
            progress_path=telemetry_path,
        )
        downloaded_by_key = {
            _source_plan_key(plan): probe
            for plan, probe in zip(tuple(plan_by_key.values()), download_results, strict=True)
        }

    results_by_run_id: dict[str, CentralMarketHistoryCollectionResult] = dict(existing_by_run_id)
    for batch in pending_batches:
        _append_progress(telemetry_path, event="batch_started", run_id=batch.run_id, source_count=len(batch.source_plans))
        probes = tuple(downloaded_by_key[_source_plan_key(plan)] for plan in batch.source_plans)
        result = _collect_batch_from_downloaded_probes(
            root_path=root_path,
            batch_plan=batch,
            probes=probes,
            max_bytes=max_bytes,
            telemetry_path=telemetry_path,
        )
        results_by_run_id[batch.run_id] = result
        _append_progress(
            telemetry_path,
            event="batch_completed",
            run_id=batch.run_id,
            manifest_ref=result.manifest_ref,
            parsed_row_count=result.parsed_row_count,
            blockers=result.blocker_count,
        )
    ordered = tuple(results_by_run_id[batch.run_id] for batch in parsed_batch_plans)
    _append_progress(
        telemetry_path,
        event="collection_completed",
        batch_count=len(ordered),
        ready_count=sum(1 for result in ordered if result.centralized_market_history_ready),
        existing_count=sum(1 for result in ordered if result.existing_batch),
    )
    return ordered


def rows_from_source_plan(
    plan: CentralMarketHistorySourcePlan,
    *,
    raw_path: str | Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    path = Path(raw_path)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_KLINE_ZIP:
        return rows_from_binance_kline_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_AGG_TRADES_ZIP:
        return rows_from_binance_agg_trades_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_TRADES_ZIP:
        return rows_from_binance_trades_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_BOOK_DEPTH_ZIP:
        return rows_from_binance_book_depth_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_BOOK_TICKER_ZIP:
        return rows_from_binance_book_ticker_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BYBIT_TRADING_GZIP:
        return rows_from_bybit_trading_gzip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BYBIT_INDEX_GZIP:
        return rows_from_bybit_index_gzip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BYBIT_MT4_KLINE_GZIP:
        return rows_from_bybit_mt4_kline_gzip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BYBIT_KLINE_API_JSON:
        return rows_from_bybit_kline_api_json(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.HYPERLIQUID_CANDLES_JSON:
        return rows_from_hyperliquid_candles_json(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    return ()


def rows_from_binance_kline_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    rows: list[CentralMarketHistoryRow] = []
    for values in _csv_rows_from_zip(path):
        if len(values) < 6 or not _looks_numeric(values[0]):
            continue
        rows.append(
            central_market_history_row_from_ohlcv(
                provider=plan.provider,
                source_id=plan.source_id,
                source_access_mode="zero_cost_public_archive",
                normalized_symbol=plan.normalized_symbol,
                venue_symbol=plan.venue_symbol,
                timestamp=_archive_timestamp_ms(values[0]),
                timeframe=plan.timeframe or "",
                open=float(values[1]),
                high=float(values[2]),
                low=float(values[3]),
                close=float(values[4]),
                volume=float(values[5]),
                quote_volume=_optional_float_at(values, 7),
                trade_count=_optional_float_at(values, 8),
                raw_fields={},
                provenance_refs=(raw_ref,),
                raw_ref=raw_ref,
                raw_sha256=raw_sha256,
            )
        )
        if plan.normalized_row_limit and len(rows) >= plan.normalized_row_limit:
            break
    return tuple(rows)


def rows_from_binance_agg_trades_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    rows: list[CentralMarketHistoryRow] = []
    for values in _csv_rows_from_zip(path):
        if len(values) < 6 or not _looks_numeric(values[0]):
            continue
        rows.append(
            central_market_history_row_from_event(
                provider=plan.provider,
                source_id=plan.source_id,
                source_access_mode="zero_cost_public_archive",
                family=CentralMarketHistoryFamily.ORDERFLOW,
                normalized_symbol=plan.normalized_symbol,
                venue_symbol=plan.venue_symbol,
                timestamp=_archive_timestamp_ms(values[5]),
                event_id=str(values[0]),
                numeric_fields={
                    "price": float(values[1]),
                    "quantity": float(values[2]),
                    "first_trade_id": float(values[3]),
                    "last_trade_id": float(values[4]),
                    "is_buyer_maker": 1.0 if str(values[6]).lower() == "true" else 0.0,
                },
                raw_fields={"source_url": plan.url, "csv": values},
                provenance_refs=(raw_ref,),
                raw_ref=raw_ref,
                raw_sha256=raw_sha256,
            )
        )
        if plan.normalized_row_limit and len(rows) >= plan.normalized_row_limit:
            break
    return tuple(rows)


def rows_from_binance_trades_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    return tuple(_row_from_event_payload(payload) for payload in payloads_from_binance_trades_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256))


def rows_from_binance_book_depth_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    return tuple(_row_from_event_payload(payload) for payload in payloads_from_binance_book_depth_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256))


def rows_from_binance_book_ticker_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    return tuple(_row_from_event_payload(payload) for payload in payloads_from_binance_book_ticker_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256))


def payloads_from_source_plan(
    plan: CentralMarketHistorySourcePlan,
    *,
    raw_path: str | Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow | Mapping[str, Any], ...]:
    path = Path(raw_path)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_AGG_TRADES_ZIP:
        return payloads_from_binance_agg_trades_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_TRADES_ZIP:
        return payloads_from_binance_trades_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_BOOK_DEPTH_ZIP:
        return payloads_from_binance_book_depth_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    if plan.source_kind == CentralMarketHistorySourceKind.BINANCE_BOOK_TICKER_ZIP:
        return payloads_from_binance_book_ticker_zip(plan, path=path, raw_ref=raw_ref, raw_sha256=raw_sha256)
    return rows_from_source_plan(plan, raw_path=raw_path, raw_ref=raw_ref, raw_sha256=raw_sha256)


def payloads_from_binance_agg_trades_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for values in _csv_rows_from_zip(path):
        if len(values) < 7 or not _looks_numeric(values[0]):
            continue
        rows.append(
            _event_payload(
                plan=plan,
                family=CentralMarketHistoryFamily.ORDERFLOW,
                timestamp=_archive_timestamp_ms(values[5]),
                event_id=str(values[0]),
                numeric_fields={
                    "price": float(values[1]),
                    "quantity": float(values[2]),
                    "first_trade_id": float(values[3]),
                    "last_trade_id": float(values[4]),
                    "is_buyer_maker": 1.0 if str(values[6]).lower() == "true" else 0.0,
                },
                raw_fields={"source_url": plan.url, "csv": values},
                raw_ref=raw_ref,
                raw_sha256=raw_sha256,
            )
        )
        if plan.normalized_row_limit and len(rows) >= plan.normalized_row_limit:
            break
    return tuple(rows)


def payloads_from_binance_trades_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for record in _csv_dict_rows_from_zip(
        path,
        default_headers=("id", "price", "qty", "quote_qty", "time", "is_buyer_maker"),
    ):
        trade_id = str(record.get("id") or "").strip()
        timestamp = record.get("time")
        if not trade_id or timestamp is None:
            continue
        rows.append(
            _event_payload(
                plan=plan,
                family=CentralMarketHistoryFamily.TRADE,
                timestamp=_archive_timestamp_ms(timestamp),
                event_id=trade_id,
                numeric_fields={
                    "price": float(record["price"]),
                    "quantity": float(record["qty"]),
                    "quote_quantity": float(record.get("quote_qty") or 0.0),
                    "is_buyer_maker": 1.0 if str(record.get("is_buyer_maker")).lower() == "true" else 0.0,
                },
                raw_fields={},
                raw_ref=raw_ref,
                raw_sha256=raw_sha256,
            )
        )
        if plan.normalized_row_limit and len(rows) >= plan.normalized_row_limit:
            break
    return tuple(rows)


def payloads_from_binance_book_depth_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[Mapping[str, Any], ...]:
    grouped: dict[str, dict[str, float]] = {}
    for record in _csv_dict_rows_from_zip(
        path,
        default_headers=("timestamp", "percentage", "depth", "notional"),
    ):
        timestamp = str(record.get("timestamp") or "").strip()
        percentage = str(record.get("percentage") or "").strip()
        if not timestamp or not percentage:
            continue
        fields = grouped.setdefault(timestamp, {"band_count": 0.0})
        token = percentage.replace("-", "neg_").replace(".", "_")
        fields[f"depth_pct_{token}"] = float(record["depth"])
        fields[f"notional_pct_{token}"] = float(record["notional"])
        fields["band_count"] += 1.0
    rows: list[Mapping[str, Any]] = []
    for timestamp, fields in sorted(grouped.items()):
        pct_values = [
            float(key.removeprefix("depth_pct_").replace("neg_", "-").replace("_", "."))
            for key in fields
            if key.startswith("depth_pct_")
        ]
        if pct_values:
            fields["min_depth_pct"] = min(pct_values)
            fields["max_depth_pct"] = max(pct_values)
        rows.append(
            _event_payload(
                plan=plan,
                family=CentralMarketHistoryFamily.BOOK,
                timestamp=_binance_archive_timestamp_ms(timestamp),
                event_id=timestamp,
                numeric_fields=fields,
                raw_fields={},
                raw_ref=raw_ref,
                raw_sha256=raw_sha256,
            )
        )
        if plan.normalized_row_limit and len(rows) >= plan.normalized_row_limit:
            break
    return tuple(rows)


def payloads_from_binance_book_ticker_zip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for record in _csv_dict_rows_from_zip(
        path,
        default_headers=(
            "update_id",
            "best_bid_price",
            "best_bid_qty",
            "best_ask_price",
            "best_ask_qty",
            "transaction_time",
            "event_time",
        ),
    ):
        update_id = str(record.get("update_id") or "").strip()
        timestamp = record.get("transaction_time") or record.get("event_time")
        if not update_id or timestamp is None:
            continue
        bid = float(record["best_bid_price"])
        ask = float(record["best_ask_price"])
        rows.append(
            _event_payload(
                plan=plan,
                family=CentralMarketHistoryFamily.BOOK,
                timestamp=_archive_timestamp_ms(timestamp),
                event_id=update_id,
                numeric_fields={
                    "update_id": float(update_id),
                    "best_bid_price": bid,
                    "best_bid_qty": float(record["best_bid_qty"]),
                    "best_ask_price": ask,
                    "best_ask_qty": float(record["best_ask_qty"]),
                    "spread": ask - bid,
                    "mid_price": (ask + bid) / 2.0,
                    "event_time_ms": float(record.get("event_time") or 0.0),
                },
                raw_fields={},
                raw_ref=raw_ref,
                raw_sha256=raw_sha256,
            )
        )
        if plan.normalized_row_limit and len(rows) >= plan.normalized_row_limit:
            break
    return tuple(rows)


def rows_from_bybit_trading_gzip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    rows: list[CentralMarketHistoryRow] = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            timestamp = _bybit_timestamp_ms(record.get("timestamp"))
            side = str(record.get("side") or "").lower()
            quantity = float(record.get("size") or record.get("volume") or 0.0)
            price = float(record.get("price") or 0.0)
            rows.append(
                central_market_history_row_from_event(
                    provider=plan.provider,
                    source_id=plan.source_id,
                    source_access_mode="zero_cost_public_archive",
                    family=CentralMarketHistoryFamily.TRADE,
                    normalized_symbol=plan.normalized_symbol,
                    venue_symbol=plan.venue_symbol,
                    timestamp=timestamp,
                    event_id=str(record.get("trdMatchID") or record.get("id") or ""),
                    numeric_fields={
                        "price": price,
                        "quantity": quantity,
                        "side": 1.0 if side == "buy" else -1.0 if side == "sell" else 0.0,
                        "gross_value": float(record.get("grossValue") or price * quantity),
                    },
                    raw_fields=dict(record),
                    provenance_refs=(raw_ref,),
                    raw_ref=raw_ref,
                    raw_sha256=raw_sha256,
                )
            )
            if plan.normalized_row_limit and len(rows) >= plan.normalized_row_limit:
                break
    return tuple(rows)


def rows_from_bybit_index_gzip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    rows: list[CentralMarketHistoryRow] = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            start_at = record.get("start_at")
            if start_at is None:
                continue
            timestamp_ms = _archive_timestamp_ms(start_at)
            period = _optional_float(record.get("period"))
            numeric_fields = {
                "open": float(record.get("open") or 0.0),
                "high": float(record.get("high") or 0.0),
                "low": float(record.get("low") or 0.0),
                "close": float(record.get("close") or 0.0),
            }
            if period is not None:
                numeric_fields["period_minutes"] = period
            rows.append(
                central_market_history_row_from_event(
                    provider=plan.provider,
                    source_id=plan.source_id,
                    source_access_mode="zero_cost_public_archive",
                    family=CentralMarketHistoryFamily.METADATA,
                    normalized_symbol=plan.normalized_symbol,
                    venue_symbol=plan.venue_symbol,
                    timestamp=timestamp_ms,
                    event_id=f"{plan.venue_symbol}:{start_at}",
                    numeric_fields=numeric_fields,
                    raw_fields=dict(record),
                    provenance_refs=(raw_ref,),
                    raw_ref=raw_ref,
                    raw_sha256=raw_sha256,
                )
            )
            if plan.normalized_row_limit and len(rows) >= plan.normalized_row_limit:
                break
    return tuple(rows)


def rows_from_bybit_mt4_kline_gzip(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    rows: list[CentralMarketHistoryRow] = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        for values in reader:
            if len(values) < 6:
                continue
            timestamp = datetime.strptime(values[0], "%Y.%m.%d %H:%M").replace(tzinfo=UTC)
            rows.append(
                central_market_history_row_from_ohlcv(
                    provider=plan.provider,
                    source_id=plan.source_id,
                    source_access_mode="zero_cost_public_archive",
                    normalized_symbol=plan.normalized_symbol,
                    venue_symbol=plan.venue_symbol,
                    timestamp=timestamp,
                    timeframe=plan.timeframe or "",
                    open=float(values[1]),
                    high=float(values[2]),
                    low=float(values[3]),
                    close=float(values[4]),
                    volume=float(values[5]),
                    raw_fields={"source_url": plan.url, "csv": values},
                    provenance_refs=(raw_ref,),
                    raw_ref=raw_ref,
                    raw_sha256=raw_sha256,
                )
            )
    return tuple(rows)


def rows_from_bybit_kline_api_json(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = payload.get("result", {}).get("list", []) if isinstance(payload, Mapping) else []
    rows: list[CentralMarketHistoryRow] = []
    for values in data:
        if len(values) < 6:
            continue
        rows.append(
            central_market_history_row_from_ohlcv(
                provider=plan.provider,
                source_id=plan.source_id,
                source_access_mode="zero_cost_public_api",
                normalized_symbol=plan.normalized_symbol,
                venue_symbol=plan.venue_symbol,
                timestamp=int(float(values[0])),
                timeframe=plan.timeframe or "",
                open=float(values[1]),
                high=float(values[2]),
                low=float(values[3]),
                close=float(values[4]),
                volume=float(values[5]),
                quote_volume=_optional_float_at(values, 6),
                raw_fields={"source_url": plan.url, "row": values},
                provenance_refs=(raw_ref,),
                raw_ref=raw_ref,
                raw_sha256=raw_sha256,
            )
        )
    return tuple(rows)


def rows_from_hyperliquid_candles_json(
    plan: CentralMarketHistorySourcePlan,
    *,
    path: Path,
    raw_ref: str,
    raw_sha256: str,
) -> tuple[CentralMarketHistoryRow, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = payload if isinstance(payload, list) else payload.get("candles", [])
    rows: list[CentralMarketHistoryRow] = []
    for record in data:
        if not isinstance(record, Mapping):
            continue
        timestamp = record.get("t") or record.get("time") or record.get("timestamp")
        if timestamp is None:
            continue
        rows.append(
            central_market_history_row_from_ohlcv(
                provider=plan.provider,
                source_id=plan.source_id,
                source_access_mode="zero_cost_public_api",
                normalized_symbol=plan.normalized_symbol,
                venue_symbol=plan.venue_symbol,
                timestamp=int(float(timestamp)),
                timeframe=plan.timeframe or "",
                open=float(record.get("o")),
                high=float(record.get("h")),
                low=float(record.get("l")),
                close=float(record.get("c")),
                volume=float(record.get("v")),
                trade_count=_optional_float(record.get("n")),
                raw_fields=dict(record),
                provenance_refs=(raw_ref,),
                raw_ref=raw_ref,
                raw_sha256=raw_sha256,
            )
        )
    return tuple(rows)


def write_central_market_history_discovery_report(
    *,
    root: str | Path,
    run_id: str,
    probes: Sequence[CentralMarketHistoryProbeRecord],
    central_batch_manifest_ref: str | None = None,
    centralized_market_history_ready: bool = False,
    max_bytes: int = CENTRAL_MARKET_HISTORY_MAX_BYTES,
) -> Path:
    root_path = Path(root).resolve(strict=False)
    manifest_dir = root_path / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    budget = central_market_history_budget_report(root_path, max_bytes=max_bytes)
    blockers = tuple(probe for probe in probes if probe.status not in {"downloaded", "cache_hit"})
    partial = {
        "run_id": run_id,
        "root_ref": str(root_path),
        "budget_report": budget,
        "probe_count": len(probes),
        "completed_count": sum(1 for probe in probes if probe.status in {"downloaded", "cache_hit"}),
        "blocker_count": len(blockers),
        "probes": tuple(probes),
        "blockers": blockers,
        "central_batch_manifest_ref": central_batch_manifest_ref,
        "centralized_market_history_ready": centralized_market_history_ready,
    }
    report = CentralMarketHistoryDiscoveryReport(
        **partial,
        report_id=central_market_history_discovery_report_id_from_payload(partial),
    )
    token = report.report_id[:12]
    path = manifest_dir / f"{run_id}-source_discovery_report-{token}.json"
    _write_json(path, report.model_dump(mode="json"))
    sha_path = path.with_suffix(path.suffix + ".sha256")
    sha_path.write_text(file_sha256(path) + "\n", encoding="utf-8")
    return path


def write_central_market_history_collection_ledger(
    *,
    root: str | Path,
    run_id: str,
    entries: Sequence[CentralMarketHistoryCollectionLedgerEntry],
    notes: Sequence[str] = (),
) -> Path:
    root_path = Path(root).resolve(strict=False)
    manifest_dir = root_path / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    entry_tuple = tuple(entries)
    partial = {
        "run_id": run_id,
        "root_ref": str(root_path),
        "entries": entry_tuple,
        "entry_count": len(entry_tuple),
        "collected_entry_count": sum(1 for entry in entry_tuple if entry.status == "collected"),
        "partial_entry_count": sum(1 for entry in entry_tuple if entry.status == "partial"),
        "unavailable_entry_count": sum(1 for entry in entry_tuple if entry.status == "unavailable"),
        "budget_blocked_entry_count": sum(1 for entry in entry_tuple if entry.status == "budget_blocked"),
        "unsupported_entry_count": sum(1 for entry in entry_tuple if entry.status == "unsupported"),
        "operator_gated_entry_count": sum(1 for entry in entry_tuple if entry.status == "operator_gated"),
        "backtest_usable_entry_count": sum(1 for entry in entry_tuple if entry.backtest_usable),
        "notes": tuple(notes),
    }
    ledger = CentralMarketHistoryCollectionLedger(
        **partial,
        ledger_id=central_market_history_collection_ledger_id_from_payload(partial),
    )
    token = ledger.ledger_id[:12]
    path = manifest_dir / f"{run_id}-collection_ledger-{token}.json"
    _write_json(path, ledger.model_dump(mode="json"))
    sha_path = path.with_suffix(path.suffix + ".sha256")
    sha_path.write_text(file_sha256(path) + "\n", encoding="utf-8")
    return path


def _collect_batch_from_downloaded_probes(
    *,
    root_path: Path,
    batch_plan: CentralMarketHistoryBatchPlan,
    probes: Sequence[CentralMarketHistoryProbeRecord],
    max_bytes: int,
    telemetry_path: Path | None,
) -> CentralMarketHistoryCollectionResult:
    parsed_rows: list[CentralMarketHistoryRow | Mapping[str, Any]] = []
    parsed_probes: list[CentralMarketHistoryProbeRecord] = []
    source_metadata: list[CentralMarketHistorySourceMetadata] = []
    for plan, probe in zip(batch_plan.source_plans, probes, strict=True):
        if probe.status not in {"downloaded", "cache_hit"} or not probe.raw_ref or not probe.raw_sha256:
            parsed_probes.append(probe)
            continue
        raw_path = _safe_child(root_path, probe.raw_ref)
        try:
            rows = payloads_from_source_plan(plan, raw_path=raw_path, raw_ref=probe.raw_ref, raw_sha256=probe.raw_sha256)
        except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, gzip.BadGzipFile) as exc:
            parsed_probes.append(probe.model_copy(update={"status": "parse_error", "reason": type(exc).__name__}))
            continue
        parsed_rows.extend(rows)
        parsed_probes.append(probe.model_copy(update={"row_count": len(rows)}))
        if rows:
            source_metadata.append(
                CentralMarketHistorySourceMetadata(
                    provider=plan.provider,
                    source_id=plan.source_id,
                    source_access_mode=_source_access_mode_for_plan(plan),
                    source_ref=plan.url,
                    official_public_source=True,
                    raw_ref=probe.raw_ref,
                    raw_sha256=probe.raw_sha256,
                    notes=(
                        "official no-paid central market-history collection",
                        "parallel_download_atomic_part",
                        *batch_plan.notes,
                    ),
                )
            )

    write_result: CentralMarketHistoryWriteResult | None = None
    if parsed_rows:
        require_central_market_history_budget(root_path, max_bytes=max_bytes)
        if _all_non_ohlcv_rows(parsed_rows):
            write_result = write_central_market_history_event_payload_batch(
                root=root_path,
                run_id=batch_plan.run_id,
                rows=parsed_rows,
                source_metadata=source_metadata,
                coverage_min=batch_plan.coverage_min,
            )
        else:
            write_result = write_central_market_history_batch(
                root=root_path,
                run_id=batch_plan.run_id,
                rows=_rows_for_standard_writer(parsed_rows),
                source_metadata=source_metadata,
                coverage_min=batch_plan.coverage_min,
                equivalence_tolerance=batch_plan.equivalence_tolerance,
            )

    discovery_report = write_central_market_history_discovery_report(
        root=root_path,
        run_id=batch_plan.run_id,
        probes=tuple(parsed_probes),
        central_batch_manifest_ref=write_result.manifest_ref if write_result else None,
        centralized_market_history_ready=bool(write_result and write_result.centralized_market_history_ready),
        max_bytes=max_bytes,
    )
    statuses = tuple(probe.status for probe in parsed_probes)
    return CentralMarketHistoryCollectionResult(
        run_id=batch_plan.run_id,
        probe_count=len(parsed_probes),
        completed_count=sum(1 for probe in parsed_probes if probe.status in {"downloaded", "cache_hit"}),
        blocker_count=sum(1 for probe in parsed_probes if probe.status not in {"downloaded", "cache_hit"}),
        parsed_row_count=len(parsed_rows),
        manifest_ref=write_result.manifest_ref if write_result else None,
        manifest_sha256=write_result.manifest_sha256 if write_result else None,
        quality_report_ref=write_result.quality_report_ref if write_result else None,
        discovery_report_ref=_relative_ref(root_path, discovery_report),
        telemetry_ref=_relative_ref(root_path, telemetry_path) if telemetry_path else None,
        statuses=statuses,
        centralized_market_history_ready=bool(write_result and write_result.centralized_market_history_ready),
    )


def _existing_collection_result_for_run_id(
    root_path: Path,
    run_id: str,
    telemetry_path: Path | None,
) -> CentralMarketHistoryCollectionResult | None:
    append_path = root_path / "manifests" / "append_manifest.jsonl"
    if not append_path.exists():
        return None
    rows = [json.loads(line) for line in append_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in reversed(rows):
        if row.get("run_id") != run_id:
            continue
        manifest_ref = str(row.get("manifest_ref") or "")
        manifest_path = _safe_child(root_path, manifest_ref)
        if not manifest_path.exists():
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        quality = manifest.get("quality_report", {})
        return CentralMarketHistoryCollectionResult(
            run_id=run_id,
            probe_count=0,
            completed_count=0,
            blocker_count=0,
            parsed_row_count=int(manifest.get("input_row_count") or 0),
            manifest_ref=manifest_ref,
            manifest_sha256=row.get("manifest_sha256"),
            quality_report_ref=manifest.get("quality_report_ref"),
            telemetry_ref=_relative_ref(root_path, telemetry_path) if telemetry_path else None,
            existing_batch=True,
            statuses=("already_collected",),
            centralized_market_history_ready=bool(quality.get("centralized_market_history_ready")),
        )
    return None


class _CentralMarketHistoryBudgetGuard:
    def __init__(self, root: Path, max_bytes: int) -> None:
        self._root = root
        self._max_bytes = max_bytes
        self._lock = threading.Lock()
        self._current_bytes = central_market_history_tree_bytes(root)
        self._reserved_bytes = 0

    def reserve(self, amount: int) -> bool:
        if amount < 0:
            raise ValueError("budget reservation amount must be non-negative")
        with self._lock:
            if self._current_bytes + self._reserved_bytes + amount > self._max_bytes:
                return False
            self._reserved_bytes += amount
            return True

    def release(self, amount: int) -> None:
        if amount <= 0:
            return
        with self._lock:
            self._reserved_bytes = max(0, self._reserved_bytes - amount)

    def commit(self, *, reserved_bytes: int, actual_bytes: int) -> None:
        with self._lock:
            self._reserved_bytes = max(0, self._reserved_bytes - max(0, reserved_bytes))
            self._current_bytes += max(0, actual_bytes)


def _validate_source_file(plan: CentralMarketHistorySourcePlan, path: Path, *, allow_part: bool = False) -> None:
    if not path.exists() or (path.name.endswith(".part") and not allow_part):
        raise ValueError("partial_or_missing_source_file")
    if path.stat().st_size <= 0:
        raise ValueError("empty_source_file")
    if plan.source_kind in {
        CentralMarketHistorySourceKind.BINANCE_KLINE_ZIP,
        CentralMarketHistorySourceKind.BINANCE_AGG_TRADES_ZIP,
        CentralMarketHistorySourceKind.BINANCE_TRADES_ZIP,
        CentralMarketHistorySourceKind.BINANCE_BOOK_DEPTH_ZIP,
        CentralMarketHistorySourceKind.BINANCE_BOOK_TICKER_ZIP,
    }:
        try:
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    raise ValueError("zip_crc_failed")
                names = [name for name in archive.namelist() if not name.endswith("/")]
                if len(names) != 1:
                    raise ValueError("zip_member_count_invalid")
        except zipfile.BadZipFile as exc:
            raise ValueError("zip_integrity_failed") from exc
        return
    if plan.source_kind in {
        CentralMarketHistorySourceKind.BYBIT_TRADING_GZIP,
        CentralMarketHistorySourceKind.BYBIT_INDEX_GZIP,
        CentralMarketHistorySourceKind.BYBIT_MT4_KLINE_GZIP,
    }:
        try:
            with gzip.open(path, "rb") as handle:
                while handle.read(1024 * 1024):
                    pass
        except (OSError, gzip.BadGzipFile) as exc:
            raise ValueError("gzip_integrity_failed") from exc
        return
    if plan.source_kind in {
        CentralMarketHistorySourceKind.BYBIT_KLINE_API_JSON,
        CentralMarketHistorySourceKind.HYPERLIQUID_CANDLES_JSON,
        CentralMarketHistorySourceKind.HYPERLIQUID_METADATA_JSON,
    }:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("json_integrity_failed") from exc


def _source_access_mode_for_plan(plan: CentralMarketHistorySourcePlan) -> str:
    if plan.source_kind in {
        CentralMarketHistorySourceKind.BYBIT_KLINE_API_JSON,
        CentralMarketHistorySourceKind.HYPERLIQUID_CANDLES_JSON,
        CentralMarketHistorySourceKind.HYPERLIQUID_METADATA_JSON,
    }:
        return "zero_cost_public_api"
    return "zero_cost_public_archive"


def _source_plan_key(plan: CentralMarketHistorySourcePlan) -> tuple[str, str, str]:
    return (plan.provider, plan.source_id, plan.raw_ref)


def _telemetry_path(root_path: Path, telemetry_ref: str | None) -> Path:
    ref = telemetry_ref or f"manifests/central_market_history_collection_progress-{utc_now():%Y%m%dT%H%M%SZ}.jsonl"
    return _safe_child(root_path, ref)


def _append_progress(path: Path | None, **payload: Any) -> None:
    if path is None:
        return
    record = {
        "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
        "created_at": utc_now().isoformat(),
        **payload,
        **RESEARCH_BOUNDARY,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with _COLLECTION_PROGRESS_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_json_ready(record), sort_keys=True, ensure_ascii=True) + "\n")


def central_market_history_discovery_report_id_for(report: CentralMarketHistoryDiscoveryReport) -> str:
    return central_market_history_discovery_report_id_from_payload(
        report.model_dump(mode="json", exclude={"report_id", "created_at"})
    )


def central_market_history_discovery_report_id_from_payload(payload: Mapping[str, Any]) -> str:
    probes = payload.get("probes", ())
    probe_payloads = [
        probe.model_dump(mode="json") if isinstance(probe, CentralMarketHistoryProbeRecord) else probe
        for probe in probes
    ]
    budget = payload["budget_report"]
    budget_payload = budget.model_dump(mode="json") if isinstance(budget, CentralMarketHistoryBudgetReport) else budget
    return canonical_json_hash(
        {
            "report_type": "central_market_history_source_discovery_report",
            "run_id": payload["run_id"],
            "root_ref": payload["root_ref"],
            "budget": {
                "max_bytes": budget_payload["max_bytes"],
                "current_bytes": budget_payload["current_bytes"],
                "planned_bytes": budget_payload["planned_bytes"],
                "remaining_bytes": budget_payload["remaining_bytes"],
                "within_budget": budget_payload["within_budget"],
            },
            "probe_count": payload["probe_count"],
            "completed_count": payload["completed_count"],
            "blocker_count": payload["blocker_count"],
            "probes": probe_payloads,
            "central_batch_manifest_ref": payload.get("central_batch_manifest_ref"),
            "centralized_market_history_ready": payload.get("centralized_market_history_ready", False),
        }
    )


def central_market_history_collection_ledger_id_for(report: CentralMarketHistoryCollectionLedger) -> str:
    return central_market_history_collection_ledger_id_from_payload(
        report.model_dump(mode="json", exclude={"ledger_id", "created_at"})
    )


def central_market_history_collection_ledger_id_from_payload(payload: Mapping[str, Any]) -> str:
    entries = payload.get("entries", ())
    entry_payloads = [
        entry.model_dump(mode="json") if isinstance(entry, CentralMarketHistoryCollectionLedgerEntry) else entry
        for entry in entries
    ]
    return canonical_json_hash(
        {
            "report_type": "central_market_history_collection_ledger",
            "run_id": payload["run_id"],
            "root_ref": payload["root_ref"],
            "entries": entry_payloads,
            "entry_count": payload["entry_count"],
            "collected_entry_count": payload["collected_entry_count"],
            "partial_entry_count": payload["partial_entry_count"],
            "unavailable_entry_count": payload["unavailable_entry_count"],
            "budget_blocked_entry_count": payload["budget_blocked_entry_count"],
            "unsupported_entry_count": payload["unsupported_entry_count"],
            "operator_gated_entry_count": payload["operator_gated_entry_count"],
            "backtest_usable_entry_count": payload["backtest_usable_entry_count"],
            "notes": tuple(payload.get("notes", ())),
        }
    )


def month_periods(start: str, end: str) -> tuple[str, ...]:
    start_dt = datetime.strptime(start, "%Y-%m").replace(tzinfo=UTC)
    end_dt = datetime.strptime(end, "%Y-%m").replace(tzinfo=UTC)
    if end_dt < start_dt:
        raise ValueError("end period must not be before start")
    periods: list[str] = []
    current = start_dt
    while current <= end_dt:
        periods.append(current.strftime("%Y-%m"))
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        current = current.replace(year=year, month=month)
    return tuple(periods)


def date_periods(start: str, end: str) -> tuple[str, ...]:
    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=UTC)
    end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=UTC)
    if end_dt < start_dt:
        raise ValueError("end date must not be before start")
    periods: list[str] = []
    current = start_dt
    while current <= end_dt:
        periods.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return tuple(periods)


def _probe_from_plan(
    plan: CentralMarketHistorySourcePlan,
    *,
    status: str,
    http_status: int | None = None,
    bytes: int | None = None,
    raw_ref: str | None = None,
    raw_sha256: str | None = None,
    row_count: int = 0,
    reason: str | None = None,
) -> CentralMarketHistoryProbeRecord:
    return CentralMarketHistoryProbeRecord(
        provider=plan.provider,
        source_id=plan.source_id,
        source_kind=plan.source_kind,
        url=plan.url,
        normalized_symbol=plan.normalized_symbol,
        venue_symbol=plan.venue_symbol,
        timeframe=plan.timeframe,
        status=status,
        http_status=http_status,
        bytes=bytes,
        raw_ref=raw_ref,
        raw_sha256=raw_sha256,
        row_count=row_count,
        reason=reason,
    )


def _csv_rows_from_zip(path: Path) -> Iterable[list[str]]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if len(names) != 1:
            raise ValueError("expected a single CSV member in Binance Vision archive")
        with archive.open(names[0]) as member:
            text = io.TextIOWrapper(member, encoding="utf-8", errors="replace", newline="")
            yield from csv.reader(text)


def _csv_dict_rows_from_zip(path: Path, *, default_headers: Sequence[str]) -> Iterable[dict[str, str]]:
    iterator = iter(_csv_rows_from_zip(path))
    try:
        first = next(iterator)
    except StopIteration:
        return
    if first and not _looks_numeric(first[0]):
        headers = [str(item).strip() for item in first]
    else:
        headers = [str(item).strip() for item in default_headers]
        yield {headers[index]: value for index, value in enumerate(first[: len(headers)])}
    for values in iterator:
        if not values:
            continue
        yield {headers[index]: value for index, value in enumerate(values[: len(headers)])}


def _event_payload(
    *,
    plan: CentralMarketHistorySourcePlan,
    family: CentralMarketHistoryFamily,
    timestamp: int,
    event_id: str,
    numeric_fields: Mapping[str, float],
    raw_fields: Mapping[str, Any],
    raw_ref: str,
    raw_sha256: str,
) -> Mapping[str, Any]:
    return {
        "provider": plan.provider,
        "source_id": plan.source_id,
        "source_access_mode": "zero_cost_public_archive",
        "family": family.value,
        "normalized_symbol": plan.normalized_symbol,
        "venue_symbol": plan.venue_symbol,
        "timeframe": plan.timeframe,
        "timestamp_ms": timestamp,
        "event_id": event_id,
        "numeric_fields": dict(numeric_fields),
        "raw_fields": dict(raw_fields),
        "provenance_refs": [raw_ref],
        "raw_ref": raw_ref,
        "raw_sha256": raw_sha256,
    }


def _row_from_event_payload(payload: Mapping[str, Any]) -> CentralMarketHistoryRow:
    return central_market_history_row_from_event(
        provider=str(payload["provider"]),
        source_id=str(payload["source_id"]),
        source_access_mode=str(payload["source_access_mode"]),
        family=str(payload["family"]),
        normalized_symbol=str(payload["normalized_symbol"]),
        venue_symbol=str(payload.get("venue_symbol") or ""),
        timeframe=payload.get("timeframe"),
        timestamp=int(payload["timestamp_ms"]),
        event_id=None if payload.get("event_id") is None else str(payload.get("event_id")),
        numeric_fields=dict(payload.get("numeric_fields") or {}),
        raw_fields=dict(payload.get("raw_fields") or {}),
        provenance_refs=tuple(str(item) for item in payload.get("provenance_refs") or ()),
        raw_ref=None if payload.get("raw_ref") is None else str(payload.get("raw_ref")),
        raw_sha256=None if payload.get("raw_sha256") is None else str(payload.get("raw_sha256")),
    )


def _all_non_ohlcv_rows(rows: Sequence[CentralMarketHistoryRow | Mapping[str, Any]]) -> bool:
    for row in rows:
        if isinstance(row, CentralMarketHistoryRow):
            if row.family == CentralMarketHistoryFamily.OHLCV:
                return False
            continue
        if CentralMarketHistoryFamily(str(row["family"])) == CentralMarketHistoryFamily.OHLCV:
            return False
    return True


def _rows_for_standard_writer(rows: Sequence[CentralMarketHistoryRow | Mapping[str, Any]]) -> tuple[CentralMarketHistoryRow | Mapping[str, Any], ...]:
    converted: list[CentralMarketHistoryRow | Mapping[str, Any]] = []
    for row in rows:
        if isinstance(row, CentralMarketHistoryRow):
            converted.append(row)
            continue
        if CentralMarketHistoryFamily(str(row["family"])) == CentralMarketHistoryFamily.OHLCV:
            converted.append(row)
        else:
            converted.append(_row_from_event_payload(row))
    return tuple(converted)


def _content_length(headers: Mapping[str, str]) -> int | None:
    raw = headers.get("content-length") or headers.get("Content-Length")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _looks_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_float_at(values: Sequence[Any], index: int) -> float | None:
    if len(values) <= index:
        return None
    return _optional_float(values[index])


def _bybit_timestamp_ms(value: Any) -> int:
    if value is None:
        raise ValueError("Bybit trade timestamp is missing")
    timestamp = float(value)
    if timestamp > 10_000_000_000:
        return int(timestamp)
    return int(timestamp * 1000)


def _archive_timestamp_ms(value: Any) -> int:
    timestamp = float(value)
    if timestamp > 10_000_000_000_000:
        return int(timestamp / 1000)
    if timestamp < 10_000_000_000:
        return int(timestamp * 1000)
    return int(timestamp)


def _binance_archive_timestamp_ms(value: Any) -> int:
    raw = str(value).strip()
    if _looks_numeric(raw):
        return _archive_timestamp_ms(raw)
    return int(datetime.fromisoformat(raw.replace(" ", "T")).replace(tzinfo=UTC).timestamp() * 1000)


def _safe_child(root: Path, ref: str) -> Path:
    normalized = ref.replace("\\", "/").lstrip("/")
    path = (root / normalized).resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("central market-history raw ref escapes root") from exc
    return path


def _relative_ref(root: Path, path: Path) -> str:
    return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_ready(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return ensure_utc(value).isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    return value
