from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.lead_book import (
    LeadBookError,
    LeadBookRow,
    LeadBookStore,
    LeadState,
    approve_after_human_inspection,
    complete_human_inspection,
    create_lead_from_source,
    evaluate_lead_gates,
    request_deep_validation,
)


def test_agent_can_create_lead_with_source_hash(tmp_path) -> None:
    source = _source_artifact(tmp_path)
    store = LeadBookStore(tmp_path / "lead_book.parquet")

    lead = _lead(source)
    store.upsert(lead)
    csv_path = store.export_csv(tmp_path / "lead_book.csv")

    assert lead.source_artifact_sha256 == file_sha256(source)
    assert store.read()[0].lead_id == lead.lead_id
    assert "promotion_ready" in csv_path.read_text(encoding="utf-8")
    assert lead.promotion_ready is False


def test_lead_cannot_deep_validate_without_human_inspection_completed(tmp_path) -> None:
    lead = _lead(_source_artifact(tmp_path))

    with pytest.raises(LeadBookError, match="deep_validation_requires_human_inspection_completed"):
        request_deep_validation(lead)


def test_agent_approval_requires_human_inspection(tmp_path) -> None:
    lead = _lead(_source_artifact(tmp_path))

    with pytest.raises(LeadBookError, match="agent_approval_requires_human_inspection"):
        approve_after_human_inspection(lead, approving_agent_id="agent-1")

    inspected = complete_human_inspection(lead, inspected_by="human-1", notes="reviewed")
    approved = approve_after_human_inspection(inspected, approving_agent_id="agent-1")
    requested = request_deep_validation(approved)
    assert requested.state == LeadState.DEEP_VALIDATION_REQUESTED


def test_lead_schema_requires_roi_observed_and_projected(tmp_path) -> None:
    payload = _lead(_source_artifact(tmp_path)).model_dump()
    del payload["roi_observed"]

    with pytest.raises(ValidationError):
        LeadBookRow.model_validate(payload)

    payload = _lead(_source_artifact(tmp_path)).model_dump()
    del payload["roi_projected"]
    with pytest.raises(ValidationError):
        LeadBookRow.model_validate(payload)


def test_roi_projection_marked_not_claim(tmp_path) -> None:
    payload = _lead(_source_artifact(tmp_path)).model_dump()
    payload["roi_projection_is_not_claim"] = False

    with pytest.raises(ValidationError, match="roi_projection_is_not_claim"):
        LeadBookRow.model_validate(payload)


def test_six_losing_months_fails_lead_gate(tmp_path) -> None:
    lead = _lead(_source_artifact(tmp_path), monthly={"usable_months": 12, "losing_months_12m": 6})

    result = evaluate_lead_gates(lead)

    assert result.status.value == "fail"
    assert "six_losing_months_in_year_failed" in result.failures


def test_profit_concentration_warning_and_fail_thresholds(tmp_path) -> None:
    warning_lead = _lead(
        _source_artifact(tmp_path, "warning.txt"),
        pnl={"top_2_trades_profit_share": 0.4, "best_month_profit_share": 0.2},
    )
    fail_lead = _lead(
        _source_artifact(tmp_path, "fail.txt"),
        pnl={"top_2_trades_profit_share": 0.6, "best_month_profit_share": 0.2},
    )

    warning = evaluate_lead_gates(warning_lead)
    failure = evaluate_lead_gates(fail_lead)

    assert warning.status.value == "warning"
    assert "top_2_trades_profit_share_warning" in warning.warnings
    assert failure.status.value == "fail"
    assert "top_2_trades_profit_share_failed" in failure.failures


def test_minimum_five_trades_per_month_gate(tmp_path) -> None:
    lead = _lead(_source_artifact(tmp_path), trades={"avg_trades_per_month": 4.9, "total_trades": 30})

    result = evaluate_lead_gates(lead)

    assert result.status.value == "fail"
    assert "minimum_five_trades_per_month_failed" in result.failures


def test_diminishing_returns_warning_is_recorded(tmp_path) -> None:
    lead = _lead(_source_artifact(tmp_path)).model_copy(update={"diminishing_returns_warning": True})

    result = evaluate_lead_gates(lead)

    assert result.status.value == "warning"
    assert "diminishing_returns_warning" in result.warnings


def test_pre_2024_fallback_absent_marks_failed_lead(tmp_path) -> None:
    lead = _lead(
        _source_artifact(tmp_path),
        data_window_start=datetime(2023, 7, 1, tzinfo=UTC),
        data_window_end=datetime(2024, 7, 1, tzinfo=UTC),
    )

    assert lead.state == LeadState.DEEP_VALIDATION_REJECTED
    assert "pre_2024_fallback_absent" in lead.known_blockers


def _source_artifact(tmp_path: Path, name: str = "source.txt") -> Path:
    path = tmp_path / name
    path.write_text("research source artifact\n", encoding="utf-8")
    return path


def _lead(
    source: Path,
    *,
    trades: dict | None = None,
    monthly: dict | None = None,
    pnl: dict | None = None,
    data_window_start: datetime | None = None,
    data_window_end: datetime | None = None,
):
    return create_lead_from_source(
        source_artifact_path=source,
        source_type="sandbox_run",
        strategy_family="momentum",
        economic_thesis="cross-sectional continuation after liquidity filter",
        created_by_id="agent-1",
        instrument_scope=("BTC", "ETH"),
        data_window_start=data_window_start or datetime(2024, 1, 1, tzinfo=UTC),
        data_window_end=data_window_end or datetime(2024, 7, 1, tzinfo=UTC),
        roi_observed=0.12,
        roi_projected=0.08,
        roi_projection_assumptions="same costed regime, not a claim",
        why_interesting="costed return with follow-up validation gap",
        trade_count_summary=trades or {"avg_trades_per_month": 6.0, "total_trades": 36},
        monthly_stability_summary=monthly or {"usable_months": 6, "losing_months_12m": 2},
        pnl_concentration_summary=pnl or {
            "top_2_trades_profit_share": 0.2,
            "best_month_profit_share": 0.2,
        },
    )
