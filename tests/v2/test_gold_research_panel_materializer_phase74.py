from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources import (
    CostClass,
    CoverageLabel,
    DataFamilyCoverageReport,
    GoldPanelMaterializerResult,
    GoldPanelPreflightResult,
    GoldResearchPanelInputValue,
    TradeBarInputRow,
    materialize_gold_research_panels,
    preflight_gold_research_panels,
    reconstruct_orderflow_features_from_trades,
)
from tradingbotsuite.v2.data_sources.schemas import CoverageWindow, ExpectedBuckets


UNIVERSE_REF = "manifests/universe/universe_test.json"
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
ARCHIVE_REF = "manifests/archive/archive_test.json"


def test_gold_panel_materializer_writes_all_ready_symbols(tmp_path: Path) -> None:
    preflight = _ready_preflight("BTC", "ETH")
    inputs = {
        symbol: _input_values_for_symbol(preflight, symbol, timestamps=(1_704_067_200_000, 1_704_067_260_000))
        for symbol in preflight.symbols
    }

    result = materialize_gold_research_panels(
        archive_root=tmp_path,
        preflight_result=preflight,
        input_values_by_symbol=inputs,
        job_id="gold-materializer-test-job",
    )

    assert result.all_symbols_materialized is True
    assert result.materialized_symbol_count == 2
    assert result.blocked_symbol_count == 0
    assert result.row_count == 4
    assert len(result.write_ids) == 2
    assert len(result.gold_panel_refs) == 2
    assert result.accepted_historical_coverage_proof is False
    assert result.candidate_pack_eligible is False
    assert (tmp_path / "manifests" / "file_manifest.parquet").exists()

    for ref in result.gold_panel_refs:
        panel_path = tmp_path / ref
        assert panel_path.exists()
        rows = pq.read_table(panel_path).to_pylist()
        assert len(rows) == 2
        assert all(row["coverage_flag_trades"] is True for row in rows)


def test_gold_panel_materializer_blocks_missing_symbol_inputs_before_writes(tmp_path: Path) -> None:
    preflight = _ready_preflight("BTC", "ETH")

    result = materialize_gold_research_panels(
        archive_root=tmp_path,
        preflight_result=preflight,
        input_values_by_symbol={
            "BTC": _input_values_for_symbol(preflight, "BTC", timestamps=(1_704_067_200_000,))
        },
        job_id="gold-materializer-test-job",
    )

    assert result.all_symbols_materialized is False
    assert result.materialized_symbol_count == 0
    assert result.blocked_symbol_count == 2
    assert "empty_feature_values" in result.blocker_reasons
    assert "materializer_not_all_symbols_ready" in result.symbol_results[0].blocker_reasons
    assert not (tmp_path / "gold").exists()
    assert not result.gold_panel_refs


def test_gold_panel_materializer_blocks_missing_source_row_hash_before_writes(tmp_path: Path) -> None:
    preflight = _ready_preflight("BTC")
    inputs = {
        "BTC": tuple(
            value.model_copy(update={"source_row_hash": None})
            for value in _input_values_for_symbol(preflight, "BTC", timestamps=(1_704_067_200_000,))
        )
    }

    result = materialize_gold_research_panels(
        archive_root=tmp_path,
        preflight_result=preflight,
        input_values_by_symbol=inputs,
        job_id="gold-materializer-test-job",
    )

    assert result.all_symbols_materialized is False
    assert result.materialized_symbol_count == 0
    assert result.blocker_reasons == ("missing_source_row_hash",)
    assert result.symbol_results[0].row_count == 1
    assert not (tmp_path / "gold").exists()


def test_gold_panel_materializer_blocks_unready_preflight_before_partial_write(tmp_path: Path) -> None:
    preflight = preflight_gold_research_panels(
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

    result = materialize_gold_research_panels(
        archive_root=tmp_path,
        preflight_result=preflight,
        input_values_by_symbol={
            "BTC": _input_values_for_symbol(preflight, "BTC", timestamps=(1_704_067_200_000,)),
            "ETH": _input_values_for_symbol(preflight, "ETH", timestamps=(1_704_067_200_000,)),
        },
        job_id="gold-materializer-test-job",
    )

    assert preflight.all_symbols_ready is False
    assert result.all_symbols_materialized is False
    assert result.materialized_symbol_count == 0
    assert "preflight_all_symbols_not_ready" in result.blocker_reasons
    assert "coverage_gate_not_passed" in result.blocker_reasons
    assert not (tmp_path / "gold").exists()


def test_gold_panel_materializer_rejects_unknown_symbol_and_boundary_override(tmp_path: Path) -> None:
    preflight = _ready_preflight("BTC")
    with pytest.raises(ValueError, match="symbols outside preflight"):
        materialize_gold_research_panels(
            archive_root=tmp_path,
            preflight_result=preflight,
            input_values_by_symbol={
                "ETH": _input_values_for_symbol(preflight, "BTC", timestamps=(1_704_067_200_000,))
            },
            job_id="gold-materializer-test-job",
        )

    result = materialize_gold_research_panels(
        archive_root=tmp_path / "boundary",
        preflight_result=preflight,
        input_values_by_symbol={
            "BTC": _input_values_for_symbol(preflight, "BTC", timestamps=(1_704_067_200_000,))
        },
        job_id="gold-materializer-test-job",
    )
    payload = result.model_dump()
    payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        GoldPanelMaterializerResult(**payload)


def _ready_preflight(*symbols: str) -> GoldPanelPreflightResult:
    return preflight_gold_research_panels(
        coverage_reports=[_coverage_report(symbol, "trades") for symbol in symbols],
        feature_reports=[_orderflow_report(symbol) for symbol in symbols],
        symbols=symbols,
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )


def _input_values_for_symbol(
    preflight: GoldPanelPreflightResult,
    symbol: str,
    *,
    timestamps: tuple[int, ...],
) -> tuple[GoldResearchPanelInputValue, ...]:
    symbol_result = next(item for item in preflight.symbol_results if item.symbol == symbol)
    values: list[GoldResearchPanelInputValue] = []
    for timestamp in timestamps:
        for index, ref in enumerate(symbol_result.feature_refs):
            values.append(
                GoldResearchPanelInputValue(
                    column_name=ref.column_name,
                    family=ref.family,
                    feature_report_id=ref.feature_report_id,
                    timestamp_ms=timestamp,
                    value=float(index + 1),
                    source_row_hash=("b" * 63) + str(index % 10),
                )
            )
    return tuple(values)


def _coverage_report(symbol: str, family: str) -> DataFamilyCoverageReport:
    return DataFamilyCoverageReport(
        coverage_report_id=f"coverage-{symbol.lower()}-{family}",
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol=symbol,
        family=family,
        venue="hyperliquid",
        source_ids=("hyperliquid_ws_trades",),
        source_cost_classes=(CostClass.ZERO_COST_PUBLIC,),
        labels=(CoverageLabel.NATIVE_HYPERLIQUID,),
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


def _orderflow_report(symbol: str):
    return reconstruct_orderflow_features_from_trades(
        trade_rows=[
            _trade_row(symbol=symbol, timestamp_ms=1_000, side="buy"),
            _trade_row(symbol=symbol, timestamp_ms=2_000, side="sell"),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        bucket_seconds=60,
    )


def _trade_row(
    *,
    symbol: str,
    timestamp_ms: int,
    side: str,
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
