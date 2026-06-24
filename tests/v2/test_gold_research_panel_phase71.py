from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources import (
    CostClass,
    CoverageLabel,
    DataFamilyCoverageReport,
    GoldResearchPanelFeatureRef,
    GoldResearchPanelInputValue,
    GoldResearchPanelRow,
    assemble_gold_research_panel_rows,
    build_gold_research_panel_manifest,
    evaluate_data_family_coverage_gate,
)
from tradingbotsuite.v2.data_sources.schemas import CoverageWindow, ExpectedBuckets


UNIVERSE_REF = "manifests/universe/universe_test.json"
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
ARCHIVE_REF = "manifests/archive/archive_test.json"


def test_gold_research_panel_row_assembly_builds_deterministic_rows() -> None:
    manifest = _ready_manifest(
        _feature_ref("hl_close", "candles_1m"),
        _feature_ref("hl_trade_imbalance", "trades"),
    )
    values = [
        _input_value("hl_close", "candles_1m", 1_704_067_200_000, 100.0),
        _input_value("hl_trade_imbalance", "trades", 1_704_067_200_000, 0.25),
        _input_value("hl_close", "candles_1m", 1_704_067_260_000, 101.0),
        _input_value("hl_trade_imbalance", "trades", 1_704_067_260_000, -0.1),
    ]

    result = assemble_gold_research_panel_rows(manifest=manifest, input_values=values)
    rebuilt = assemble_gold_research_panel_rows(manifest=manifest, input_values=values)

    assert result.assembly_ready is True
    assert result.assembly_id == rebuilt.assembly_id
    assert result.feature_columns == ("hl_close", "hl_trade_imbalance")
    assert result.row_count == 2
    assert result.rows[0].values == {"hl_close": 100.0, "hl_trade_imbalance": 0.25}
    assert result.rows[0].coverage_flags == {"candles_1m": True, "trades": True}
    assert result.accepted_historical_coverage_proof is False


def test_gold_research_panel_row_assembly_allows_nullable_missing_values() -> None:
    manifest = _ready_manifest(
        _feature_ref("hl_trade_imbalance", "trades"),
        _feature_ref("hl_funding_rate", "funding", nullable=True),
    )

    result = assemble_gold_research_panel_rows(
        manifest=manifest,
        input_values=[
            _input_value("hl_trade_imbalance", "trades", 1_704_067_200_000, 0.2)
        ],
    )

    assert result.assembly_ready is True
    assert result.row_count == 1
    assert result.rows[0].values == {"hl_funding_rate": None, "hl_trade_imbalance": 0.2}
    assert result.rows[0].coverage_flags == {"funding": False, "trades": True}


def test_gold_research_panel_row_assembly_blocks_missing_non_nullable_value() -> None:
    manifest = _ready_manifest(
        _feature_ref("hl_close", "candles_1m"),
        _feature_ref("hl_trade_imbalance", "trades"),
    )

    result = assemble_gold_research_panel_rows(
        manifest=manifest,
        input_values=[_input_value("hl_close", "candles_1m", 1_704_067_200_000, 100.0)],
    )

    assert result.assembly_ready is False
    assert result.row_count == 0
    assert result.blocker_reasons == ("missing_required_column_value",)


def test_gold_research_panel_row_assembly_blocks_duplicate_column_timestamp() -> None:
    manifest = _ready_manifest(_feature_ref("hl_close", "candles_1m"))

    result = assemble_gold_research_panel_rows(
        manifest=manifest,
        input_values=[
            _input_value("hl_close", "candles_1m", 1_704_067_200_000, 100.0),
            _input_value("hl_close", "candles_1m", 1_704_067_200_000, 101.0),
        ],
    )

    assert result.assembly_ready is False
    assert result.row_count == 0
    assert result.blocker_reasons == ("duplicate_column_timestamp",)


def test_gold_research_panel_row_assembly_blocks_unready_manifest() -> None:
    gate = evaluate_data_family_coverage_gate(
        coverage_reports=[],
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol="BTC",
    )
    manifest = build_gold_research_panel_manifest(
        coverage_gate=gate,
        feature_refs=[_feature_ref("hl_trade_imbalance", "trades")],
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    result = assemble_gold_research_panel_rows(
        manifest=manifest,
        input_values=[
            _input_value("hl_trade_imbalance", "trades", 1_704_067_200_000, 0.2)
        ],
    )

    assert manifest.panel_ready is False
    assert result.assembly_ready is False
    assert result.blocker_reasons == ("panel_manifest_not_ready",)


def test_gold_research_panel_row_assembly_rejects_unknown_column() -> None:
    manifest = _ready_manifest(_feature_ref("hl_close", "candles_1m"))

    with pytest.raises(ValueError, match="column_name is not in panel manifest"):
        assemble_gold_research_panel_rows(
            manifest=manifest,
            input_values=[
                GoldResearchPanelInputValue(
                    column_name="unknown_feature",
                    family="candles_1m",
                    feature_report_id="f" * 64,
                    timestamp_ms=1_704_067_200_000,
                    value=100.0,
                )
            ],
        )


def test_gold_research_panel_row_assembly_rejects_report_id_mismatch() -> None:
    manifest = _ready_manifest(_feature_ref("hl_close", "candles_1m"))

    with pytest.raises(ValueError, match="feature_report_id does not match"):
        assemble_gold_research_panel_rows(
            manifest=manifest,
            input_values=[
                GoldResearchPanelInputValue(
                    column_name="hl_close",
                    family="candles_1m",
                    feature_report_id="x" * 64,
                    timestamp_ms=1_704_067_200_000,
                    value=100.0,
                )
            ],
        )


def test_gold_research_panel_row_boundary_validation_fails_closed() -> None:
    manifest = _ready_manifest(_feature_ref("hl_close", "candles_1m"))
    result = assemble_gold_research_panel_rows(
        manifest=manifest,
        input_values=[_input_value("hl_close", "candles_1m", 1_704_067_200_000, 100.0)],
    )

    payload = result.rows[0].model_dump()
    payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        GoldResearchPanelRow(**payload)


def _ready_manifest(*feature_refs: GoldResearchPanelFeatureRef):
    families = tuple(sorted({ref.family for ref in feature_refs}))
    gate = evaluate_data_family_coverage_gate(
        coverage_reports=[_coverage_report(family) for family in families],
        required_families=families,
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol="BTC",
    )
    return build_gold_research_panel_manifest(
        coverage_gate=gate,
        feature_refs=feature_refs,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )


def _coverage_report(family: str) -> DataFamilyCoverageReport:
    return DataFamilyCoverageReport(
        coverage_report_id=f"coverage-btc-{family}",
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol="BTC",
        family=family,
        venue="hyperliquid",
        source_ids=("hyperliquid_info_meta_asset_ctxs",),
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


def _feature_ref(
    column_name: str,
    family: str,
    *,
    nullable: bool = False,
) -> GoldResearchPanelFeatureRef:
    return GoldResearchPanelFeatureRef(
        column_name=column_name,
        family=family,
        feature_report_id=_feature_report_id(column_name),
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        source_ids=("hyperliquid_info_meta_asset_ctxs",),
        venue="hyperliquid",
        venue_symbol="BTC",
        coverage_label=CoverageLabel.NATIVE_HYPERLIQUID,
        row_count=12,
        row_manifest_hash="a" * 64,
        nullable=nullable,
        coverage_flag_column=f"coverage_flag_{family}",
        native_to_hyperliquid=True,
    )


def _input_value(
    column_name: str,
    family: str,
    timestamp_ms: int,
    value: int | float | str | bool | None,
) -> GoldResearchPanelInputValue:
    return GoldResearchPanelInputValue(
        column_name=column_name,
        family=family,
        feature_report_id=_feature_report_id(column_name),
        timestamp_ms=timestamp_ms,
        value=value,
        source_row_hash="b" * 64,
    )


def _feature_report_id(column_name: str) -> str:
    return (column_name.encode("utf-8").hex() + ("f" * 64))[:64]
