from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.archive.hashing import (
    canonical_json_hash,
    file_sha256,
    manifest_rows_hash,
)
from tradingbotsuite.v2.archive.schemas import ArchiveConfig, ArchiveLayer
from tradingbotsuite.v2.backtest_engine.artifacts import (
    EngineLane,
    MissingDataPolicy,
    RunArtifactRef,
    RunManifest,
    RunStatus,
    ValidationStatus,
)
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.costs.models import CostModelConfig
from tradingbotsuite.v2.lead_book.schemas import LeadBookRow, LeadState
from tradingbotsuite.v2.ledger.schemas import LedgerRow
from tradingbotsuite.v2.security.path_policy import PathPolicy, resolve_within_root
from tradingbotsuite.v2.universe.models import UniverseConfig, UniverseMode
from tradingbotsuite.v2.validation.policies import LockboxPolicy, ValidationConfig


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def test_canonical_json_hash_is_stable() -> None:
    left = {"b": [2, 1], "a": {"z": True, "y": None}}
    right = {"a": {"y": None, "z": True}, "b": [2, 1]}

    assert canonical_json_hash(left) == canonical_json_hash(right)
    assert manifest_rows_hash([{"id": "2"}, {"id": "1"}]) == manifest_rows_hash(
        [{"id": "1"}, {"id": "2"}]
    )


def test_file_sha256_matches_known_fixture(tmp_path) -> None:
    fixture = tmp_path / "fixture.txt"
    fixture.write_bytes(b"abc")

    assert (
        file_sha256(fixture)
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_archive_config_validates_defaults() -> None:
    config = ArchiveConfig()

    assert config.archive_root == "data/archive"
    assert config.hash_algorithm == "sha256"
    assert config.layers == (
        ArchiveLayer.RAW,
        ArchiveLayer.BRONZE,
        ArchiveLayer.SILVER,
        ArchiveLayer.GOLD,
    )


def test_path_policy_rejects_parent_traversal(tmp_path) -> None:
    root = tmp_path / "archive"
    root.mkdir()

    inside = resolve_within_root(root, "raw/file.jsonl")
    assert inside == root.resolve() / "raw" / "file.jsonl"

    policy = PathPolicy(root=root)
    assert policy.resolve("silver/panel.parquet") == root.resolve() / "silver" / "panel.parquet"

    with pytest.raises(ValueError, match="escapes configured root"):
        resolve_within_root(root, "../escape.json")


def test_run_manifest_requires_research_only_boundary() -> None:
    manifest = _run_manifest()
    assert manifest.research_only is True
    assert manifest.promotion_ready is False

    with pytest.raises(ValidationError):
        _run_manifest(run_id="run-2", promotion_ready=True)


def test_initial_schema_models_validate_defaults() -> None:
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    universe = UniverseConfig()
    validation = ValidationConfig()
    cost = CostModelConfig()
    ledger = LedgerRow(
        run_id="run-1",
        archive_snapshot_id="archive-snap",
        universe_snapshot_id="universe-snap",
        strategy_spec_hash=HEX_C,
        cost_model_id=cost.cost_model_id,
    )
    lead = LeadBookRow(
        lead_id="lead-1",
        created_at=aware,
        created_by_type="agent",
        created_by_id="agent",
        source_type="manual_hypothesis",
        source_artifact_path="manual://lead-1",
        source_artifact_sha256=HEX_A,
        strategy_family="example",
        economic_thesis="schema smoke",
        venue_scope="hyperliquid",
        universe_scope="as_of",
        instrument_scope=("BTC",),
        data_window_start=aware,
        data_window_end=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        data_source="manual",
        cost_assumptions="manifested",
        funding_assumptions="manifested",
        slippage_assumptions="manifested",
        fill_assumptions="research_only",
        roi_observed=0.0,
        roi_projected=0.0,
        roi_projection_assumptions="schema smoke, not a claim",
        why_interesting="schema smoke",
        trade_count_summary={"avg_trades_per_month": 5.0, "total_trades": 30},
        monthly_stability_summary={"usable_months": 6, "losing_months_12m": 0},
        pnl_concentration_summary={
            "top_2_trades_profit_share": 0.0,
            "best_month_profit_share": 0.0,
        },
    )

    assert universe.mode == UniverseMode.AS_OF
    assert universe.min_day_notional_usd == 5_000_000
    assert validation.lockbox_policy == LockboxPolicy()
    assert cost.funding_required is True
    assert ledger.promotion_ready is False
    assert lead.state == LeadState.IDEA_ONLY
    assert lead.agent_approval_status.value == "not_reviewed"


def test_utc_helpers_require_timezone_aware_values() -> None:
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert ensure_utc(aware).tzinfo is UTC
    assert utc_isoformat(aware) == "2026-01-01T12:00:00Z"

    with pytest.raises(ValueError, match="timezone-aware"):
        ensure_utc(datetime(2026, 1, 1, 12, 0))


def _run_manifest(run_id: str = "run-1", **updates) -> RunManifest:
    payload = {
        "run_id": run_id,
        "experiment_id": "experiment-1",
        "trial_index": 0,
        "agent_or_user": "agent",
        "status": RunStatus.FAILED,
        "engine_lane": EngineLane.VECTORIZED,
        "git_sha": "test-git-sha",
        "environment_hash": HEX_A,
        "strategy_id": "strategy-1",
        "strategy_version": "0.1.0",
        "strategy_hash": HEX_B,
        "strategy_spec_hash": HEX_B,
        "params_hash": HEX_C,
        "archive_snapshot_id": "archive-snap",
        "universe_snapshot_id": "universe-snap",
        "data_manifest_id": "data-manifest",
        "data_manifest_hash": HEX_A,
        "validation_manifest_hash": HEX_B,
        "cost_manifest_hash": HEX_C,
        "universe_mode": "as_of",
        "venue_scope": "hyperliquid",
        "instrument_count": 2,
        "timeframe": "1h",
        "backtest_start": datetime(2026, 1, 1, tzinfo=UTC),
        "backtest_end": datetime(2026, 1, 2, tzinfo=UTC),
        "usable_months": 0,
        "lockbox_policy_id": "dynamic_full_calendar_months_v1",
        "data_coverage_min": 0.98,
        "cost_model_id": "costs-v1",
        "cost_model_hash": HEX_A,
        "validation_policy_id": "validation-v1",
        "validation_status": ValidationStatus.FAIL,
        "missing_data_policy": MissingDataPolicy.FAIL_CLOSED,
        "price_basis": "next_bar_open",
        "failure_reason": "schema smoke",
        "artifacts": {
            name: RunArtifactRef(name=name, path=f"{name}.json", sha256=HEX_A)
            for name in (
                "strategy_spec",
                "params",
                "data_manifest",
                "validation_manifest",
                "cost_manifest",
                "cost_stress",
                "metrics",
                "equity_curve",
                "daily_returns",
                "trades",
                "positions",
                "per_instrument_metrics",
                "fold_metrics",
                "log",
            )
        },
    }
    payload.update(updates)
    return RunManifest(**payload)
