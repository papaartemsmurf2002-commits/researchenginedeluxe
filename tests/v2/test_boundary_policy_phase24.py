from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.autonomy import AutonomyStepResult
from tradingbotsuite.v2.backtest_data import BacktestDataRequest
from tradingbotsuite.v2.backtest_engine import BacktestMetrics, RunStatus
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.lead_book.schemas import LeadBookRow
from tradingbotsuite.v2.ledger.schemas import LedgerRow
from tradingbotsuite.v2.security import (
    ResearchBoundaryError,
    boundary_violation_reasons,
    require_research_boundary,
    research_boundary_defaults,
)
from tradingbotsuite.v2.strategy_specs import SignalRow, example_strategy_payloads, validate_strategy_spec


def test_central_boundary_policy_matches_canonical_defaults() -> None:
    defaults = research_boundary_defaults()

    assert defaults == dict(RESEARCH_BOUNDARY)
    assert boundary_violation_reasons(defaults) == ()

    with pytest.raises(ResearchBoundaryError, match="promotion_ready_must_be_false"):
        require_research_boundary({**defaults, "promotion_ready": True}, context="unit")

    missing = dict(defaults)
    del missing["runtime_mode_change"]
    assert "runtime_mode_change_missing" in boundary_violation_reasons(missing)


def test_autonomy_step_uses_central_boundary_policy() -> None:
    with pytest.raises(ValidationError, match="live_signal_must_be_false"):
        AutonomyStepResult(
            name="blocked-step",
            status="blocked",
            live_signal=True,
        )


def test_backtest_data_request_uses_central_boundary_policy() -> None:
    with pytest.raises(ValidationError, match="candidate_pack_eligible_must_be_false"):
        BacktestDataRequest(
            archive_root="archive",
            archive_snapshot_id="a" * 64,
            universe_snapshot_id="b" * 64,
            venue="hyperliquid",
            instrument_id="hyperliquid:perp:SOL",
            timeframe="1d",
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 7, 1, tzinfo=UTC),
            candidate_pack_eligible=True,
        )


def test_backtest_metrics_uses_central_boundary_policy() -> None:
    with pytest.raises(ValidationError, match="paper_signal_must_be_false"):
        BacktestMetrics(
            run_id="run-boundary",
            status=RunStatus.SUCCEEDED,
            gross_return=0.1,
            net_return=0.08,
            gross_equity_final=1.1,
            net_equity_final=1.08,
            total_fee_cost=0.01,
            total_spread_cost=0.01,
            total_slippage_cost=0.01,
            total_impact_cost=0.01,
            total_transaction_cost=0.04,
            total_funding_pnl=0.0,
            total_turnover=1.0,
            trade_count=10,
            position_row_count=20,
            paper_signal=True,
        )


def test_ledger_row_uses_central_boundary_policy() -> None:
    with pytest.raises(ValidationError, match="runtime_mode_change_must_be_false"):
        LedgerRow(
            run_id="ledger-boundary",
            archive_snapshot_id="archive-snapshot",
            universe_snapshot_id="universe-snapshot",
            strategy_spec_hash="c" * 64,
            cost_model_id="cost-model",
            runtime_mode_change=True,
        )


def test_lead_book_row_uses_central_boundary_policy() -> None:
    with pytest.raises(ValidationError, match="sizing_instruction_must_be_false"):
        LeadBookRow(
            lead_id="lead-boundary",
            created_at=datetime(2024, 7, 1, tzinfo=UTC),
            created_by_type="agent",
            created_by_id="agent-1",
            source_type="unit_test",
            source_artifact_path="source.json",
            source_artifact_sha256="d" * 64,
            strategy_family="funding_carry",
            economic_thesis="boundary validation test",
            venue_scope="hyperliquid",
            universe_scope="as_of",
            instrument_scope=("hyperliquid:perp:SOL",),
            data_window_start=datetime(2024, 1, 1, tzinfo=UTC),
            data_window_end=datetime(2024, 7, 1, tzinfo=UTC),
            data_source="unit_test",
            cost_assumptions="manifested_cost_model",
            funding_assumptions="manifested_funding_model",
            slippage_assumptions="manifested_slippage_model",
            fill_assumptions="research_fill_assumptions_only",
            roi_observed=0.0,
            roi_projected=0.0,
            roi_projection_assumptions="not a claim",
            why_interesting="boundary validation",
            trade_count_summary={"avg_trades_per_month": 6.0, "total_trades": 36},
            monthly_stability_summary={"usable_months": 6},
            pnl_concentration_summary={"top_2_trades_profit_share": 0.0},
            sizing_instruction=True,
        )


def test_strategy_spec_and_signal_row_use_central_boundary_policy() -> None:
    payload = example_strategy_payloads()["hl_funding_carry_v1"]
    payload = {**payload, "candidate_evidence": True}
    result = validate_strategy_spec(payload)

    assert result.ok is False
    assert any("candidate_evidence_must_be_false" in error for error in result.errors)

    with pytest.raises(ValidationError, match="order_placement_instruction_must_be_false"):
        SignalRow(
            strategy_id="hl_funding_carry_v1",
            spec_hash="e" * 64,
            ts=datetime(2024, 1, 1, tzinfo=UTC),
            instrument_id="hyperliquid:perp:SOL",
            signal=1.0,
            target_weight=0.05,
            side="long",
            reason="unit_test",
            order_placement_instruction=True,
        )
