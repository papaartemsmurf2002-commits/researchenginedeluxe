from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.backtest_data import (
    BacktestDataRequest,
    BacktestDataService,
    BacktestEvidenceMode,
)
from tradingbotsuite.v2.config.defaults import DEFAULT_PRIMARY_VENUE
from tradingbotsuite.v2.universe.hyperliquid import load_universe_rows
from tradingbotsuite.v2.venues import (
    VenueAdapterCapability,
    binance_usdm_fixture_capability,
    write_binance_usdm_fixture_archive,
)


START = datetime(2024, 1, 1, tzinfo=UTC)
END = datetime(2024, 7, 1, tzinfo=UTC)
ASOF = date(2024, 1, 1)
INSTRUMENT = "binance:perp:BTCUSDT"


def test_venue_adapter_capability_rejects_private_order_and_sizing_flags() -> None:
    capability = binance_usdm_fixture_capability()

    assert capability.venue == "binance"
    assert capability.default_primary_venue is False
    assert capability.supports_bars is True
    assert capability.supports_funding is True
    assert capability.order_placement_allowed is False
    assert capability.sizing_allowed is False
    assert capability.runtime_mode_change_allowed is False

    payload = capability.model_dump()
    payload["order_placement_allowed"] = True
    with pytest.raises(ValueError, match="order_placement_allowed"):
        VenueAdapterCapability.model_validate(payload)


def test_binance_fixture_adapter_writes_cross_venue_provenance(tmp_path) -> None:
    result = _build_binance_fixture(tmp_path)
    layout = ArchiveLayout(tmp_path / "archive")
    manifest_rows = ArchiveManifestStore(layout).load_file_manifest()
    universe_rows = load_universe_rows(layout.root)

    assert result.capability.access_mode == "fixture_only"
    assert result.raw_response.venue == "binance"
    assert result.raw_response.row_count == len(_bar_rows()) + len(_funding_rows())
    assert {row.venue for row in manifest_rows} == {"binance"}
    assert {row.datatype for row in manifest_rows} >= {"cross_venue_fixture_bundle", "bars", "funding"}
    assert any(row.file_id == result.bar_file_id and row.instrument_id == INSTRUMENT for row in manifest_rows)
    assert any(row.file_id == result.funding_file_id and row.instrument_id == INSTRUMENT for row in manifest_rows)
    assert [row.venue for row in universe_rows] == ["binance"]
    assert universe_rows[0].instrument_id == INSTRUMENT
    assert universe_rows[0].accepted_research_evidence_allowed is True


def test_backtest_data_service_loads_binance_bars_and_funding(tmp_path) -> None:
    result = _build_binance_fixture(tmp_path)
    archive_root = tmp_path / "archive"
    service = BacktestDataService(archive_root)
    bars = service.load_panel(
        BacktestDataRequest(
            archive_root=str(archive_root),
            archive_snapshot_id=result.archive_snapshot_id,
            universe_snapshot_id=result.universe_snapshot_id,
            venue="binance",
            instrument_id=INSTRUMENT,
            family="bars",
            timeframe="1d",
            start_ts=START,
            end_ts=END,
            requested_fields=("ts", "venue", "instrument_id", "close", "venue_provenance"),
            evidence_mode=BacktestEvidenceMode.ACCEPTED_RESEARCH,
        ),
        asof_date=date(2026, 6, 21),
    )
    funding = service.load_panel(
        BacktestDataRequest(
            archive_root=str(archive_root),
            archive_snapshot_id=result.archive_snapshot_id,
            universe_snapshot_id=result.universe_snapshot_id,
            venue="binance",
            instrument_id=INSTRUMENT,
            family="funding",
            timeframe="8h",
            start_ts=START,
            end_ts=END,
            requested_fields=("ts", "venue", "instrument_id", "funding_rate", "mark_price", "venue_provenance"),
            evidence_mode=BacktestEvidenceMode.ACCEPTED_RESEARCH,
        ),
        asof_date=date(2026, 6, 21),
    )

    assert bars.reported_row_count == 182
    assert bars.rows[0]["venue"] == "binance"
    assert bars.rows[0]["instrument_id"] == INSTRUMENT
    assert bars.rows[0]["venue_provenance"] == "binance_usdm_fixture_v1"
    assert funding.reported_row_count == 546
    assert funding.rows[0]["venue"] == "binance"
    assert funding.rows[0]["instrument_id"] == INSTRUMENT
    assert funding.rows[0]["venue_provenance"] == "binance_usdm_fixture_v1"
    assert funding.data_manifest.venue == "binance"


def test_hyperliquid_default_remains_primary_venue() -> None:
    assert DEFAULT_PRIMARY_VENUE == "hyperliquid"
    assert binance_usdm_fixture_capability().default_primary_venue is False


def _build_binance_fixture(tmp_path):
    return write_binance_usdm_fixture_archive(
        archive_root=tmp_path / "archive",
        bars=_bar_rows(),
        funding_rows=_funding_rows(),
        start_ts=START,
        end_ts=END,
        asof_date=ASOF,
        instrument_id=INSTRUMENT,
        venue_symbol="BTCUSDT",
    )


def _bar_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = START
    index = 0
    while current < END:
        close = 40_000.0 + index
        rows.append(
            {
                "ts": current.isoformat().replace("+00:00", "Z"),
                "end_ts": (current + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "open": close - 10.0,
                "high": close + 50.0,
                "low": close - 50.0,
                "close": close,
                "volume": 1_000.0 + index,
                "trade_count": 100 + index,
            }
        )
        current += timedelta(days=1)
        index += 1
    return rows


def _funding_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = START
    index = 0
    while current < END:
        rows.append(
            {
                "ts": current.isoformat().replace("+00:00", "Z"),
                "end_ts": (current + timedelta(hours=8)).isoformat().replace("+00:00", "Z"),
                "funding_rate": 0.0001 if index % 2 == 0 else -0.00005,
                "mark_price": 40_000.0 + (index * 0.5),
                "volume": 1.0,
            }
        )
        current += timedelta(hours=8)
        index += 1
    return rows
