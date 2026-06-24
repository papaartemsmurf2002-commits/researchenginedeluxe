from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources import (
    CostClass,
    CoverageLabel,
    DataFamilyCoverageGateResult,
    DataFamilyCoverageReport,
    evaluate_data_family_coverage_gate,
)
from tradingbotsuite.v2.data_sources.schemas import CoverageWindow, ExpectedBuckets


UNIVERSE_REF = "manifests/universe/universe_test.json"
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
ARCHIVE_REF = "manifests/archive/archive_test.json"


def test_data_family_coverage_gate_passes_when_all_required_families_are_accepted() -> None:
    gate = evaluate_data_family_coverage_gate(
        coverage_reports=[
            _coverage_report("candles_1m"),
            _coverage_report("trades"),
            _coverage_report("funding"),
        ],
        required_families=["funding", "trades", "candles_1m"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol="BTC",
    )

    assert gate.passed is True
    assert gate.required_families == ("candles_1m", "funding", "trades")
    assert gate.blocker_reasons == ()
    assert set(gate.accepted_family_report_ids) == {"candles_1m", "funding", "trades"}
    assert gate.accepted_historical_coverage_proof is False
    assert gate.candidate_pack_eligible is False


def test_data_family_coverage_gate_blocks_missing_required_family() -> None:
    gate = evaluate_data_family_coverage_gate(
        coverage_reports=[_coverage_report("trades")],
        required_families=["trades", "bbo"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol="BTC",
    )

    assert gate.passed is False
    assert gate.missing_families == ("bbo",)
    assert gate.blocker_reasons == ("missing_required_family",)


def test_data_family_coverage_gate_blocks_rejected_required_family() -> None:
    gate = evaluate_data_family_coverage_gate(
        coverage_reports=[
            _coverage_report(
                "l2_snapshots",
                accepted=False,
                coverage_ratio=0.5,
                reason=("coverage_ratio_below_min",),
            )
        ],
        required_families=["l2_snapshots"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol="BTC",
    )

    assert gate.passed is False
    assert gate.rejected_families == ("l2_snapshots",)
    assert gate.blocker_reasons == ("rejected_required_family",)


def test_data_family_coverage_gate_blocks_empty_reports() -> None:
    gate = evaluate_data_family_coverage_gate(
        coverage_reports=[],
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol="BTC",
    )

    assert gate.passed is False
    assert gate.missing_families == ("trades",)
    assert gate.blocker_reasons == ("empty_coverage_reports", "missing_required_family")


def test_data_family_coverage_gate_rejects_context_mismatch() -> None:
    with pytest.raises(ValueError, match="symbol mismatch"):
        evaluate_data_family_coverage_gate(
            coverage_reports=[_coverage_report("trades", symbol="ETH")],
            required_families=["trades"],
            universe_snapshot_ref=UNIVERSE_REF,
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
            archive_snapshot_ref=ARCHIVE_REF,
            symbol="BTC",
        )


def test_data_family_coverage_gate_rejects_empty_required_family_set() -> None:
    with pytest.raises(ValueError, match="required_families must not be empty"):
        evaluate_data_family_coverage_gate(
            coverage_reports=[_coverage_report("trades")],
            required_families=[],
            universe_snapshot_ref=UNIVERSE_REF,
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
            archive_snapshot_ref=ARCHIVE_REF,
            symbol="BTC",
        )


def test_data_family_coverage_gate_boundary_validation_fails_closed() -> None:
    gate = evaluate_data_family_coverage_gate(
        coverage_reports=[_coverage_report("trades")],
        required_families=["trades"],
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol="BTC",
    )

    payload = gate.model_dump()
    payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        DataFamilyCoverageGateResult(**payload)


def _coverage_report(
    family: str,
    *,
    symbol: str = "BTC",
    accepted: bool = True,
    coverage_ratio: float = 1.0,
    reason: tuple[str, ...] = (),
) -> DataFamilyCoverageReport:
    return DataFamilyCoverageReport(
        coverage_report_id=f"coverage-{symbol.lower()}-{family}",
        universe_snapshot_ref=UNIVERSE_REF,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        archive_snapshot_ref=ARCHIVE_REF,
        symbol=symbol,
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
        observed_buckets=1 if coverage_ratio else 0,
        coverage_ratio=coverage_ratio,
        coverage_min=0.98,
        accepted_for_research_reporting=accepted,
        reason=reason,
    )
