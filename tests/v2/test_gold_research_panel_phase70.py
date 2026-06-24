from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources import (
    CostClass,
    CoverageLabel,
    DataFamilyCoverageReport,
    GoldResearchPanelFeatureRef,
    GoldResearchPanelManifest,
    build_gold_research_panel_manifest,
    evaluate_data_family_coverage_gate,
)
from tradingbotsuite.v2.data_sources.schemas import CoverageWindow, ExpectedBuckets


UNIVERSE_REF = "manifests/universe/universe_test.json"
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
ARCHIVE_REF = "manifests/archive/archive_test.json"


def test_gold_research_panel_manifest_passes_with_gate_and_feature_refs() -> None:
    gate = _coverage_gate("candles_1m", "trades")
    feature_refs = [
        _feature_ref("hl_close", "candles_1m"),
        _feature_ref("hl_trade_imbalance", "trades"),
    ]

    manifest = build_gold_research_panel_manifest(
        coverage_gate=gate,
        feature_refs=feature_refs,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )
    rebuilt = build_gold_research_panel_manifest(
        coverage_gate=gate,
        feature_refs=feature_refs,
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    assert manifest.panel_ready is True
    assert manifest.panel_id == rebuilt.panel_id
    assert manifest.coverage_gate_id == gate.gate_id
    assert manifest.coverage_report_ids == gate.report_ids
    assert manifest.required_families == ("candles_1m", "trades")
    assert manifest.coverage_flags == {"candles_1m": True, "trades": True}
    assert manifest.minimum_feature_row_count == 12
    assert manifest.accepted_historical_coverage_proof is False
    assert manifest.candidate_pack_eligible is False
    assert manifest.promotion_ready is False


def test_gold_research_panel_manifest_blocks_failed_coverage_gate() -> None:
    gate = evaluate_data_family_coverage_gate(
        coverage_reports=[_coverage_report("trades")],
        required_families=["trades", "bbo"],
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

    assert manifest.panel_ready is False
    assert manifest.missing_feature_families == ("bbo",)
    assert manifest.coverage_flags == {"bbo": False, "trades": False}
    assert "coverage_gate_not_passed" in manifest.blocker_reasons
    assert "missing_required_feature_family" in manifest.blocker_reasons


def test_gold_research_panel_manifest_blocks_missing_archive_snapshot_ref() -> None:
    gate = _coverage_gate("trades", archive_snapshot_ref=None)

    manifest = build_gold_research_panel_manifest(
        coverage_gate=gate,
        feature_refs=[_feature_ref("hl_trade_imbalance", "trades")],
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    assert gate.passed is True
    assert manifest.panel_ready is False
    assert manifest.blocker_reasons == ("missing_archive_snapshot_ref",)


def test_gold_research_panel_manifest_blocks_empty_feature_refs() -> None:
    gate = _coverage_gate("trades")

    manifest = build_gold_research_panel_manifest(
        coverage_gate=gate,
        feature_refs=[],
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    assert manifest.panel_ready is False
    assert manifest.missing_feature_families == ("trades",)
    assert manifest.blocker_reasons == (
        "empty_feature_refs",
        "missing_required_feature_family",
    )


def test_gold_research_panel_manifest_blocks_feature_family_not_covered_by_gate() -> None:
    gate = _coverage_gate("trades")

    manifest = build_gold_research_panel_manifest(
        coverage_gate=gate,
        feature_refs=[
            _feature_ref("hl_trade_imbalance", "trades"),
            _feature_ref("hl_bbo_spread_bps", "bbo"),
        ],
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    assert manifest.panel_ready is False
    assert manifest.uncovered_feature_families == ("bbo",)
    assert manifest.blocker_reasons == ("feature_family_not_covered_by_gate",)


def test_gold_research_panel_manifest_rejects_feature_ref_context_mismatch() -> None:
    gate = _coverage_gate("trades")

    with pytest.raises(ValueError, match="source_registry_ref mismatch"):
        build_gold_research_panel_manifest(
            coverage_gate=gate,
            feature_refs=[
                _feature_ref(
                    "hl_trade_imbalance",
                    "trades",
                    source_registry_ref="manifests/source_registry/other.json",
                )
            ],
            panel_name="hl_research_panel_1m",
            interval="1m",
        )


def test_gold_research_panel_feature_ref_rejects_external_native_label() -> None:
    with pytest.raises(ValidationError, match="external feature refs cannot use native_hyperliquid"):
        _feature_ref(
            "binance_usdm_vwap",
            "trades",
            coverage_label=CoverageLabel.NATIVE_HYPERLIQUID,
            native_to_hyperliquid=False,
        )


def test_gold_research_panel_manifest_boundary_validation_fails_closed() -> None:
    manifest = build_gold_research_panel_manifest(
        coverage_gate=_coverage_gate("trades"),
        feature_refs=[_feature_ref("hl_trade_imbalance", "trades")],
        panel_name="hl_research_panel_1m",
        interval="1m",
    )

    payload = manifest.model_dump()
    payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        GoldResearchPanelManifest(**payload)


def _coverage_gate(
    *families: str,
    archive_snapshot_ref: str | None = ARCHIVE_REF,
):
    return evaluate_data_family_coverage_gate(
        coverage_reports=[
            _coverage_report(family, archive_snapshot_ref=archive_snapshot_ref)
            for family in families
        ],
        required_families=families,
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol="BTC",
    )


def _coverage_report(
    family: str,
    *,
    archive_snapshot_ref: str | None = ARCHIVE_REF,
) -> DataFamilyCoverageReport:
    return DataFamilyCoverageReport(
        coverage_report_id=f"coverage-btc-{family}",
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=archive_snapshot_ref,
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
    source_registry_ref: str = SOURCE_REGISTRY_REF,
    coverage_label: CoverageLabel = CoverageLabel.NATIVE_HYPERLIQUID,
    native_to_hyperliquid: bool = True,
) -> GoldResearchPanelFeatureRef:
    return GoldResearchPanelFeatureRef(
        column_name=column_name,
        family=family,
        feature_report_id=("f" * 63) + column_name[-1],
        source_registry_ref=source_registry_ref,
        symbol_map_ref=SYMBOL_MAP_REF,
        source_ids=("hyperliquid_info_meta_asset_ctxs",),
        venue="hyperliquid",
        venue_symbol="BTC",
        coverage_label=coverage_label,
        row_count=12,
        row_manifest_hash="a" * 64,
        nullable=False,
        coverage_flag_column=f"coverage_flag_{family}",
        native_to_hyperliquid=native_to_hyperliquid,
    )
