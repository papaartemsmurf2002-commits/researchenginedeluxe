from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources import (
    CostClass,
    CoverageLabel,
    DataFamilyCoverageReport,
    DerivativesContextFeatureInputRow,
    GoldPanelPreflightResult,
    TradeBarInputRow,
    preflight_gold_research_panels,
    reconstruct_funding_oi_features_from_context_rows,
    reconstruct_orderflow_features_from_trades,
)
from tradingbotsuite.v2.data_sources.schemas import CoverageWindow, ExpectedBuckets


UNIVERSE_REF = "manifests/universe/universe_test.json"
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
ARCHIVE_REF = "manifests/archive/archive_test.json"


def test_gold_panel_preflight_aggregates_multi_symbol_coverage_and_feature_refs() -> None:
    coverage_reports = [
        _coverage_report("BTC", "trades"),
        _coverage_report("ETH", "trades"),
    ]
    feature_reports = [
        _orderflow_report("BTC"),
        _orderflow_report("ETH"),
    ]

    result = preflight_gold_research_panels(
        coverage_reports=coverage_reports,
        feature_reports=feature_reports,
        symbols=["ETH", "BTC"],
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )
    rebuilt = preflight_gold_research_panels(
        coverage_reports=coverage_reports,
        feature_reports=feature_reports,
        symbols=["BTC", "ETH"],
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    assert result.preflight_id == rebuilt.preflight_id
    assert result.symbols == ("BTC", "ETH")
    assert result.symbol_count == 2
    assert result.ready_symbol_count == 2
    assert result.blocked_symbol_count == 0
    assert result.all_symbols_ready is True
    assert result.accepted_historical_coverage_proof is False
    assert result.candidate_pack_eligible is False

    btc = result.symbol_results[0]
    assert btc.symbol == "BTC"
    assert btc.coverage_summary.coverage_gate_passed is True
    assert btc.coverage_summary.accepted_family_report_ids == {
        "trades": "coverage-btc-trades"
    }
    assert btc.panel_ready is True
    assert btc.gold_panel_manifest.panel_ready is True
    assert btc.gold_panel_manifest.coverage_flags == {"trades": True}
    assert "hl_trades_vwap" in {ref.column_name for ref in btc.feature_refs}
    assert {ref.family for ref in btc.feature_refs} == {"trades"}


def test_gold_panel_preflight_blocks_missing_symbol_coverage() -> None:
    result = preflight_gold_research_panels(
        coverage_reports=[_coverage_report("BTC", "trades")],
        feature_reports=[_orderflow_report("BTC"), _orderflow_report("ETH")],
        symbols=["BTC", "ETH"],
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    eth = next(item for item in result.symbol_results if item.symbol == "ETH")
    assert result.all_symbols_ready is False
    assert result.ready_symbol_count == 1
    assert result.blocked_symbol_count == 1
    assert eth.coverage_summary.coverage_report_count == 0
    assert eth.coverage_summary.missing_families == ("trades",)
    assert eth.coverage_summary.blocker_reasons == (
        "empty_coverage_reports",
        "missing_required_family",
    )
    assert "coverage_gate_not_passed" in eth.blocker_reasons
    assert eth.gold_panel_manifest.panel_ready is False


def test_gold_panel_preflight_blocks_feature_reports_with_reconstruction_blockers() -> None:
    blocked_report = _orderflow_report("BTC", missing_side=True)

    result = preflight_gold_research_panels(
        coverage_reports=[_coverage_report("BTC", "trades")],
        feature_reports=[blocked_report],
        symbols=["BTC"],
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    symbol = result.symbol_results[0]
    assert symbol.panel_ready is False
    assert symbol.accepted_feature_report_ids == ()
    assert symbol.feature_refs == ()
    assert f"feature_report_blocked:{blocked_report.feature_report_id}" in symbol.blocker_reasons
    assert "empty_feature_refs" in symbol.blocker_reasons
    assert "missing_required_feature_family" in symbol.blocker_reasons


def test_gold_panel_preflight_maps_context_feature_reports_by_required_family() -> None:
    context_report = reconstruct_funding_oi_features_from_context_rows(
        context_rows=[
            DerivativesContextFeatureInputRow(
                source_id="binance_usdm_public_derivatives_context",
                family="funding_rate_history",
                venue="binance",
                venue_symbol="BTCUSDT",
                hyperliquid_coin="BTC",
                market_type="perpetual",
                timestamp_ms=1_704_067_200_000,
                numeric_fields={"funding_rate": 0.0001, "mark_price": 42000.5},
                unit_fields={"funding_rate": "rate", "mark_price": "USDT"},
            )
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    result = preflight_gold_research_panels(
        coverage_reports=[
            _coverage_report(
                "BTC",
                "funding_rate_history",
                labels=(CoverageLabel.EXTERNAL_COMPARISON,),
                venue="binance",
            )
        ],
        feature_reports=[context_report],
        symbols=["BTC"],
        required_families=["funding_rate_history"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        panel_name="cross_venue_context_panel_1m",
        interval="1m",
    )

    symbol = result.symbol_results[0]
    columns = {ref.column_name: ref for ref in symbol.feature_refs}
    assert symbol.panel_ready is True
    assert set(columns) == {
        "binance_funding_rate_history_funding_rate",
        "binance_funding_rate_history_mark_price",
    }
    assert columns["binance_funding_rate_history_funding_rate"].family == "funding_rate_history"
    assert columns["binance_funding_rate_history_funding_rate"].coverage_label == CoverageLabel.EXTERNAL_COMPARISON
    assert columns["binance_funding_rate_history_funding_rate"].native_to_hyperliquid is False


def test_gold_panel_preflight_rejects_context_mismatch_and_boundary_overrides() -> None:
    with pytest.raises(ValueError, match="feature report source_registry_ref mismatch"):
        preflight_gold_research_panels(
            coverage_reports=[_coverage_report("BTC", "trades")],
            feature_reports=[
                _orderflow_report(
                    "BTC",
                    source_registry_ref="manifests/source_registry/other.json",
                )
            ],
            symbols=["BTC"],
            required_families=["trades"],
            universe_snapshot_ref=UNIVERSE_REF,
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
            archive_snapshot_ref=ARCHIVE_REF,
            panel_name="hl_research_panel_1m",
            interval="1m",
        )

    result = preflight_gold_research_panels(
        coverage_reports=[_coverage_report("BTC", "trades")],
        feature_reports=[_orderflow_report("BTC")],
        symbols=["BTC"],
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )
    payload = result.model_dump()
    payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        GoldPanelPreflightResult(**payload)


def _coverage_report(
    symbol: str,
    family: str,
    *,
    labels: tuple[CoverageLabel, ...] = (CoverageLabel.NATIVE_HYPERLIQUID,),
    venue: str = "hyperliquid",
) -> DataFamilyCoverageReport:
    return DataFamilyCoverageReport(
        coverage_report_id=f"coverage-{symbol.lower()}-{family}",
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol=symbol,
        family=family,
        venue=venue,
        source_ids=("hyperliquid_info_meta_asset_ctxs",),
        source_cost_classes=(CostClass.ZERO_COST_PUBLIC,),
        labels=labels,
        coverage_window=CoverageWindow(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        expected_buckets=ExpectedBuckets(bucket_seconds=60, count=1),
        observed_buckets=1,
        coverage_ratio=1.0,
        coverage_min=0.98,
        accepted_for_research_reporting=True,
    )


def _orderflow_report(
    symbol: str,
    *,
    source_registry_ref: str = SOURCE_REGISTRY_REF,
    missing_side: bool = False,
):
    return reconstruct_orderflow_features_from_trades(
        trade_rows=[
            _trade_row(symbol=symbol, timestamp_ms=1_000, side="buy"),
            _trade_row(symbol=symbol, timestamp_ms=2_000, side=None if missing_side else "sell"),
        ],
        source_registry_ref=source_registry_ref,
        symbol_map_ref=SYMBOL_MAP_REF,
        bucket_seconds=60,
    )


def _trade_row(
    *,
    symbol: str,
    timestamp_ms: int,
    side: str | None,
) -> TradeBarInputRow:
    return TradeBarInputRow(
        source_id="hyperliquid_ws_trades",
        venue="hyperliquid",
        venue_symbol=symbol,
        hyperliquid_coin=symbol,
        market_type="perpetual",
        source_timestamp_ms=timestamp_ms,
        price=100.0,
        quantity=1.0,
        side=side,
        native_to_hyperliquid=True,
    )
