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
    GoldResearchPanelFeatureRef,
    GoldResearchPanelInputValue,
    GoldResearchPanelWriteResult,
    assemble_gold_research_panel_rows,
    build_gold_research_panel_manifest,
    evaluate_data_family_coverage_gate,
    write_gold_research_panel_artifacts,
)
from tradingbotsuite.v2.data_sources.schemas import CoverageWindow, ExpectedBuckets


UNIVERSE_REF = "manifests/universe/universe_test.json"
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
ARCHIVE_REF = "manifests/archive/archive_test.json"


def test_gold_research_panel_artifact_write_persists_rows_and_manifest(tmp_path: Path) -> None:
    assembly = _ready_assembly()

    result = write_gold_research_panel_artifacts(
        archive_root=tmp_path,
        assembly_result=assembly,
        job_id="gold-panel-test-job",
    )

    panel_path = tmp_path / result.gold_panel_ref
    manifest_path = tmp_path / result.assembly_manifest_ref
    assert panel_path.exists()
    assert manifest_path.exists()
    assert result.row_count == 2
    assert result.gold_panel_file_id == result.gold_panel_sha256
    assert result.accepted_historical_coverage_proof is False
    assert result.candidate_pack_eligible is False

    rows = pq.read_table(panel_path).to_pylist()
    assert len(rows) == 2
    assert rows[0]["panel_id"] == assembly.panel_id
    assert rows[0]["coverage_flag_candles_1m"] is True
    assert rows[0]["coverage_flag_trades"] is True
    assert rows[0]["hl_close"] == 100.0
    assert (tmp_path / "manifests" / "file_manifest.parquet").exists()


def test_gold_research_panel_artifact_write_rejects_blocked_assembly(tmp_path: Path) -> None:
    assembly = assemble_gold_research_panel_rows(
        manifest=_ready_manifest(
            _feature_ref("hl_close", "candles_1m"),
            _feature_ref("hl_trade_imbalance", "trades"),
        ),
        input_values=[_input_value("hl_close", "candles_1m", 1_704_067_200_000, 100.0)],
    )

    with pytest.raises(ValueError, match="assembly result is not ready"):
        write_gold_research_panel_artifacts(
            archive_root=tmp_path,
            assembly_result=assembly,
            job_id="gold-panel-test-job",
        )
    assert not (tmp_path / "gold").exists()


def test_gold_research_panel_artifact_write_rejects_unsafe_dataset(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsafe archive partition value"):
        write_gold_research_panel_artifacts(
            archive_root=tmp_path,
            assembly_result=_ready_assembly(),
            job_id="gold-panel-test-job",
            dataset="../bad",
        )


def test_gold_research_panel_artifact_write_rejects_duplicate_write(tmp_path: Path) -> None:
    assembly = _ready_assembly()
    write_gold_research_panel_artifacts(
        archive_root=tmp_path,
        assembly_result=assembly,
        job_id="gold-panel-test-job",
    )

    with pytest.raises(FileExistsError):
        write_gold_research_panel_artifacts(
            archive_root=tmp_path,
            assembly_result=assembly,
            job_id="gold-panel-test-job",
        )


def test_gold_research_panel_write_result_boundary_validation_fails_closed(tmp_path: Path) -> None:
    result = write_gold_research_panel_artifacts(
        archive_root=tmp_path,
        assembly_result=_ready_assembly(),
        job_id="gold-panel-test-job",
    )

    payload = result.model_dump()
    payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        GoldResearchPanelWriteResult(**payload)


def _ready_assembly():
    manifest = _ready_manifest(
        _feature_ref("hl_close", "candles_1m"),
        _feature_ref("hl_trade_imbalance", "trades"),
    )
    return assemble_gold_research_panel_rows(
        manifest=manifest,
        input_values=[
            _input_value("hl_close", "candles_1m", 1_704_067_200_000, 100.0),
            _input_value("hl_trade_imbalance", "trades", 1_704_067_200_000, 0.25),
            _input_value("hl_close", "candles_1m", 1_704_067_260_000, 101.0),
            _input_value("hl_trade_imbalance", "trades", 1_704_067_260_000, -0.1),
        ],
    )


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


def _feature_ref(column_name: str, family: str) -> GoldResearchPanelFeatureRef:
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
        nullable=False,
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
