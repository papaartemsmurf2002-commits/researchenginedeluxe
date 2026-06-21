# V2-AUDIT-ID: V2-AUD-XVENUE-001
# V2-CONTRACTS: docs/contracts/venue_adapter_contract.md, docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, fixture_only_public_market_data, no_order_or_sizing
# V2-OWNER: v2_venues
"""Fixture-only Binance USDT-M market-data adapter for v2 cross-venue tests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tradingbotsuite.v2.archive.hashing import manifest_rows_hash
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode
from tradingbotsuite.v2.universe.models import (
    AssetContextSnapshotRow,
    InstrumentCatalogRow,
    UniverseMode,
    UniverseSnapshotRow,
)
from tradingbotsuite.v2.universe.store import append_universe_tables
from tradingbotsuite.v2.venues.contracts import (
    VenueAdapterCapability,
    VenueRawRequest,
    VenueRawResponse,
)


class BinanceFixtureArchiveResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability: VenueAdapterCapability
    raw_request: VenueRawRequest
    raw_response: VenueRawResponse
    raw_file_id: str = Field(min_length=64, max_length=64)
    bar_file_id: str = Field(min_length=64, max_length=64)
    funding_file_id: str = Field(min_length=64, max_length=64)
    bar_coverage_report_id: str = Field(min_length=64, max_length=64)
    funding_coverage_report_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    instrument_id: str
    venue: str = "binance"
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False


def binance_usdm_fixture_capability() -> VenueAdapterCapability:
    return VenueAdapterCapability(
        adapter_id="binance_usdm_fixture_v1",
        venue="binance",
        market_types=("perp", "usdt_m"),
        access_mode="fixture_only",
        supports_bars=True,
        supports_funding=True,
        supports_trades=False,
        supports_bbo=False,
        supports_l2=False,
        supports_official_s3=True,
        rate_limit_policy="not_applicable_fixture",
        default_primary_venue=False,
    )


def write_binance_usdm_fixture_archive(
    *,
    archive_root: str | Path,
    bars: Iterable[Mapping[str, Any]],
    funding_rows: Iterable[Mapping[str, Any]],
    start_ts: datetime,
    end_ts: datetime,
    asof_date: date,
    instrument_id: str = "binance:perp:BTCUSDT",
    venue_symbol: str = "BTCUSDT",
    timeframe: str = "1d",
    funding_timeframe: str = "8h",
    day_ntl_vlm_usd: float = 50_000_000.0,
    min_day_notional_usd: float = 5_000_000.0,
    usable_months: int = 6,
    min_usable_months: int = 6,
) -> BinanceFixtureArchiveResult:
    start = ensure_utc(start_ts)
    end = ensure_utc(end_ts)
    capability = binance_usdm_fixture_capability()
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    materialized_bars = _normalize_bar_rows(
        bars,
        instrument_id=instrument_id,
        timeframe=timeframe,
    )
    materialized_funding = _normalize_funding_rows(
        funding_rows,
        instrument_id=instrument_id,
        funding_timeframe=funding_timeframe,
    )
    raw_payload = {
        "venue": capability.venue,
        "adapter_id": capability.adapter_id,
        "instrument_id": instrument_id,
        "venue_symbol": venue_symbol,
        "bars": materialized_bars,
        "funding": materialized_funding,
    }
    raw_request = VenueRawRequest.build(
        adapter_id=capability.adapter_id,
        venue=capability.venue,
        source="fixture/binance_usdm/bars_funding",
        params={
            "instrument_id": instrument_id,
            "venue_symbol": venue_symbol,
            "timeframe": timeframe,
            "funding_timeframe": funding_timeframe,
            "start_ts": utc_isoformat(start),
            "end_ts": utc_isoformat(end),
        },
    )
    raw_response = VenueRawResponse.build(
        request=raw_request,
        payload=raw_payload,
        row_count=len(materialized_bars) + len(materialized_funding),
        rate_limit_metadata={"mode": "fixture_only"},
    )
    run_id = f"binance-fixture-{raw_response.response_id[:16]}"
    raw_file = RawJsonlZstdWriter(layout, store).write_records(
        records=[raw_payload],
        venue=capability.venue,
        datatype="cross_venue_fixture_bundle",
        date=asof_date.isoformat(),
        run_id=run_id,
        job_id=run_id,
        adapter_id=capability.adapter_id,
        source_endpoint_or_subscription=raw_request.source,
        symbols=(instrument_id,),
        start_ts=start,
        end_ts=end,
        instrument_id=instrument_id,
        timeframe=timeframe,
        filename="bars_funding_fixture",
    )
    bar_file = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[
            {
                **row,
                "source_file_id": raw_file.file_id,
                "source_layer": ArchiveLayer.RAW.value,
            }
            for row in materialized_bars
        ],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue=capability.venue,
        datatype="bars",
        date=asof_date.isoformat(),
        timeframe=timeframe,
        job_id=run_id,
        source_file_ids=(raw_file.file_id,),
        instrument_id=instrument_id,
    )
    funding_file = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[
            {
                **row,
                "source_file_id": raw_file.file_id,
                "source_layer": ArchiveLayer.RAW.value,
            }
            for row in materialized_funding
        ],
        layer=ArchiveLayer.SILVER,
        dataset="funding",
        venue=capability.venue,
        datatype="funding",
        date=asof_date.isoformat(),
        timeframe=funding_timeframe,
        job_id=run_id,
        source_file_ids=(raw_file.file_id,),
        instrument_id=instrument_id,
    )
    coverage_store = CoverageManifestStore(layout)
    bar_coverage = coverage_report_for_bars(
        materialized_bars,
        venue=capability.venue,
        instrument_id=instrument_id,
        family="bars",
        timeframe=timeframe,
        start_ts=start,
        end_ts=end,
        evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
    )
    funding_coverage = coverage_report_for_bars(
        materialized_funding,
        venue=capability.venue,
        instrument_id=instrument_id,
        family="funding",
        timeframe=funding_timeframe,
        start_ts=start,
        end_ts=end,
        volume_field="volume",
        price_field="mark_price",
        funding_field="funding_rate",
        evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
    )
    coverage_store.append_coverage_report(bar_coverage)
    coverage_store.append_coverage_report(funding_coverage)
    universe_snapshot_id = _write_binance_universe(
        layout=layout,
        instrument_id=instrument_id,
        venue_symbol=venue_symbol,
        asof_date=asof_date,
        raw_payload_sha256=raw_response.raw_payload_sha256,
        raw_file_id=raw_file.file_id,
        day_ntl_vlm_usd=day_ntl_vlm_usd,
        min_day_notional_usd=min_day_notional_usd,
        usable_months=usable_months,
        min_usable_months=min_usable_months,
        coverage_ratio=min(bar_coverage.coverage_ratio, funding_coverage.coverage_ratio),
        coverage_min=bar_coverage.coverage_min,
        last_bar=materialized_bars[-1],
        last_funding=materialized_funding[-1],
    )
    snapshot = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope=capability.venue,
        start_ts=start,
        end_ts=end,
        coverage_rows=[bar_coverage.model_dump(mode="json"), funding_coverage.model_dump(mode="json")],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="binance_usdm_fixture_cross_venue_phase19",
    )
    return BinanceFixtureArchiveResult(
        capability=capability,
        raw_request=raw_request,
        raw_response=raw_response,
        raw_file_id=raw_file.file_id,
        bar_file_id=bar_file.file_id,
        funding_file_id=funding_file.file_id,
        bar_coverage_report_id=bar_coverage.coverage_report_id,
        funding_coverage_report_id=funding_coverage.coverage_report_id,
        universe_snapshot_id=universe_snapshot_id,
        archive_snapshot_id=snapshot.archive_snapshot_id,
        instrument_id=instrument_id,
    )


def _normalize_bar_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    instrument_id: str,
    timeframe: str,
) -> list[dict[str, Any]]:
    materialized = [dict(row) for row in rows]
    if not materialized:
        raise ValueError("binance fixture bars are required")
    normalized: list[dict[str, Any]] = []
    for row in materialized:
        ts = _parse_ts(row["ts"])
        end_ts = _parse_ts(row.get("end_ts") or row["ts"])
        close = float(row["close"])
        normalized.append(
            {
                "venue": "binance",
                "instrument_id": instrument_id,
                "timeframe": timeframe,
                "ts": utc_isoformat(ts),
                "end_ts": utc_isoformat(end_ts),
                "open": float(row.get("open", close)),
                "high": float(row.get("high", close)),
                "low": float(row.get("low", close)),
                "close": close,
                "volume": float(row.get("volume", 1.0)),
                "trade_count": int(row.get("trade_count", 0)),
                "source_timeframe": timeframe,
                "normalization_warnings": tuple(row.get("normalization_warnings", ())),
                "venue_provenance": "binance_usdm_fixture_v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return sorted(normalized, key=lambda item: (item["ts"], item["instrument_id"]))


def _normalize_funding_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    instrument_id: str,
    funding_timeframe: str,
) -> list[dict[str, Any]]:
    materialized = [dict(row) for row in rows]
    if not materialized:
        raise ValueError("binance fixture funding rows are required")
    normalized: list[dict[str, Any]] = []
    for row in materialized:
        ts = _parse_ts(row["ts"])
        end_ts = _parse_ts(row.get("end_ts") or row["ts"])
        mark_price = float(row.get("mark_price", row.get("close", 1.0)))
        normalized.append(
            {
                "venue": "binance",
                "instrument_id": instrument_id,
                "timeframe": funding_timeframe,
                "ts": utc_isoformat(ts),
                "end_ts": utc_isoformat(end_ts),
                "funding_rate": float(row["funding_rate"]),
                "funding": float(row["funding_rate"]),
                "mark_price": mark_price,
                "close": mark_price,
                "volume": float(row.get("volume", 1.0)),
                "venue_provenance": "binance_usdm_fixture_v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return sorted(normalized, key=lambda item: (item["ts"], item["instrument_id"]))


def _write_binance_universe(
    *,
    layout: ArchiveLayout,
    instrument_id: str,
    venue_symbol: str,
    asof_date: date,
    raw_payload_sha256: str,
    raw_file_id: str,
    day_ntl_vlm_usd: float,
    min_day_notional_usd: float,
    usable_months: int,
    min_usable_months: int,
    coverage_ratio: float,
    coverage_min: float,
    last_bar: Mapping[str, Any],
    last_funding: Mapping[str, Any],
) -> str:
    asof_ts = datetime.combine(asof_date, datetime.min.time(), tzinfo=UTC)
    instrument = InstrumentCatalogRow(
        instrument_id=instrument_id,
        venue="binance",
        venue_symbol=venue_symbol,
        canonical_symbol=venue_symbol,
        market_type="perp",
        base_asset=venue_symbol.removesuffix("USDT"),
        quote_asset="USDT",
        settle_asset="USDT",
        first_seen_ts=asof_ts,
        last_seen_ts=asof_ts,
        status="active",
        source_snapshot_id=raw_file_id,
    )
    context = AssetContextSnapshotRow(
        instrument_id=instrument_id,
        venue_symbol=venue_symbol,
        day_ntl_vlm_usd=day_ntl_vlm_usd,
        open_interest=None,
        mark_px=float(last_bar["close"]),
        oracle_px=float(last_bar["close"]),
        funding=float(last_funding["funding_rate"]),
        raw_context={"source": "binance_usdm_fixture_v1"},
    )
    eligible_volume = day_ntl_vlm_usd >= min_day_notional_usd
    eligible_coverage = coverage_ratio >= coverage_min
    eligible_history = usable_months >= min_usable_months
    eligible = eligible_volume and eligible_coverage and eligible_history
    exclusion_reason = None if eligible else "cross_venue_fixture_eligibility_failed"
    row = UniverseSnapshotRow(
        snapshot_id="0" * 64,
        asof_date=asof_date,
        venue="binance",
        universe_rule_id="binance_usdm_fixture_day_ntl_vlm_gte_5m_v1",
        universe_mode=UniverseMode.AS_OF,
        instrument_id=instrument_id,
        day_ntl_vlm_usd=day_ntl_vlm_usd,
        open_interest=None,
        mark_px=float(last_bar["close"]),
        oracle_px=float(last_bar["close"]),
        funding=float(last_funding["funding_rate"]),
        eligible_volume=eligible_volume,
        eligible_coverage=eligible_coverage,
        eligible_history=eligible_history,
        eligible_status=True,
        eligible_hip3_metadata=True,
        eligible=eligible,
        exclusion_reason=exclusion_reason,
        evidence_scope="accepted_research",
        accepted_research_evidence_allowed=eligible,
        raw_payload_sha256=raw_payload_sha256,
        raw_file_id=raw_file_id,
    )
    snapshot_id = manifest_rows_hash([row.model_dump(mode="json", exclude={"snapshot_id", "created_at"})])
    row = row.model_copy(update={"snapshot_id": snapshot_id})
    append_universe_tables(layout=layout, instruments=[instrument], contexts=[context], rows=[row])
    return snapshot_id


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, str):
        return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    raise ValueError(f"unsupported timestamp value: {value!r}")
