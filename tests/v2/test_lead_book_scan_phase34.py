from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.lead_book import (
    LeadBookError,
    LeadBookScanConfig,
    LeadBookStore,
    LeadState,
    approve_after_human_inspection,
    complete_human_inspection,
    create_lead_from_source,
    request_deep_validation,
    scan_lead_book_queue,
)


def test_lead_book_scan_writes_manifest_for_multiple_states(tmp_path: Path) -> None:
    lead_book_path = tmp_path / "lead_book.parquet"
    store = LeadBookStore(lead_book_path)
    sandbox = _lead(tmp_path, "sandbox", state=LeadState.SANDBOX_SCREENED)
    deep = _deep_validation_requested_lead(tmp_path)
    idea = _lead(tmp_path, "idea", state=LeadState.IDEA_ONLY)
    for lead in (sandbox, deep, idea):
        store.upsert(lead)

    result = scan_lead_book_queue(
        LeadBookScanConfig(
            lead_book_path=str(lead_book_path),
            output_path=str(tmp_path / "scan" / "lead_book_scan.json"),
            states=(LeadState.SANDBOX_SCREENED, LeadState.DEEP_VALIDATION_REQUESTED),
        )
    )
    manifest = json.loads(Path(result.scan_manifest_path).read_text(encoding="utf-8"))

    assert result.total_lead_count == 3
    assert result.matched_count == 2
    assert result.returned_count == 2
    assert result.blocker_reasons == ()
    assert {item["lead_id"] for item in manifest["items"]} == {sandbox.lead_id, deep.lead_id}
    assert manifest["matched_state_counts"] == {
        "deep_validation_requested": 1,
        "sandbox_screened": 1,
    }
    assert manifest["accepted_research_ready"] is False
    assert manifest["boundary_flags"] == RESEARCH_BOUNDARY
    assert all(manifest[key] == value for key, value in RESEARCH_BOUNDARY.items())
    assert [lead.state for lead in LeadBookStore(lead_book_path).read()] == [
        LeadState.DEEP_VALIDATION_REQUESTED,
        LeadState.IDEA_ONLY,
        LeadState.SANDBOX_SCREENED,
    ]


def test_lead_book_scan_missing_lead_book_writes_blocker_manifest(tmp_path: Path) -> None:
    result = scan_lead_book_queue(
        {
            "lead_book_path": str(tmp_path / "missing" / "lead_book.parquet"),
            "output_path": str(tmp_path / "scan.json"),
            "states": ["sandbox_screened"],
        }
    )
    manifest = json.loads(Path(result.scan_manifest_path).read_text(encoding="utf-8"))

    assert result.matched_count == 0
    assert result.returned_count == 0
    assert result.blocker_reasons == ("lead_book_missing", "no_matching_lead_book_rows")
    assert manifest["lead_book_exists"] is False
    assert manifest["blocker_count"] == 2
    assert manifest["accepted_research_ready"] is False


def test_lead_book_scan_rejects_secret_like_output_before_write(tmp_path: Path) -> None:
    with pytest.raises(LeadBookError, match="output_path_secret_like_path"):
        scan_lead_book_queue(
            {
                "lead_book_path": str(tmp_path / "lead_book.parquet"),
                "output_path": str(tmp_path / "secret" / "scan.json"),
                "states": ["sandbox_screened"],
            }
        )
    assert not (tmp_path / "secret").exists()


def test_leadbook_scan_cli_prints_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lead_book_path = tmp_path / "lead_book.parquet"
    store = LeadBookStore(lead_book_path)
    lead = _lead(tmp_path, "cli", state=LeadState.SANDBOX_SCREENED)
    store.upsert(lead)
    output_path = tmp_path / "lead_book_scan.json"

    exit_code = main(
        [
            "leadbook",
            "scan",
            "--lead-book",
            str(lead_book_path),
            "--status",
            "sandbox_screened,deep_validation_requested",
            "--output-path",
            str(output_path),
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output_path.exists()
    assert f"lead_book_scan_manifest={output_path.resolve(strict=False)}" in output
    assert "matched_count=1" in output
    assert "accepted_research_ready=false" in output
    assert "promotion_ready=false" in output


def _lead(root: Path, label: str, *, state: LeadState):
    source = root / f"{label}.json"
    source.write_text(json.dumps({"label": label}) + "\n", encoding="utf-8")
    lead = create_lead_from_source(
        source_artifact_path=source,
        source_type="ledger_row",
        strategy_family=f"family-{label}",
        economic_thesis=f"thesis-{label}",
        created_by_id="test-agent",
        instrument_scope=("hyperliquid:perp:BTC",),
        data_window_start=datetime(2024, 1, 1, tzinfo=UTC),
        data_window_end=datetime(2024, 8, 1, tzinfo=UTC),
        roi_observed=0.1,
        roi_projected=0.2,
        roi_projection_assumptions="projection_not_claim",
        why_interesting="queue scan fixture",
        trade_count_summary={"avg_trades_per_month": 8.0, "total_trades": 56},
        monthly_stability_summary={
            "usable_months": 7,
            "losing_months_12m": 1,
            "positive_months_12m": 6,
        },
        pnl_concentration_summary={
            "top_2_trades_profit_share": 0.1,
            "best_month_profit_share": 0.2,
        },
        lead_id=f"LEAD-{label}",
    )
    return lead.model_copy(update={"state": state})


def _deep_validation_requested_lead(root: Path):
    lead = _lead(root, "deep", state=LeadState.IDEA_ONLY)
    lead = complete_human_inspection(
        lead,
        inspected_by="human-reviewer",
        notes="human inspected fixture lead",
    )
    lead = approve_after_human_inspection(lead, approving_agent_id="agent-reviewer")
    return request_deep_validation(lead)
