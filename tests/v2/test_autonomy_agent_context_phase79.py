from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

from tradingbotsuite.v2.autonomy import (
    agent_context_to_json,
    build_autonomous_research_agent_context,
    write_autonomous_research_agent_context,
)
from tradingbotsuite.v2.cli.main import main


def test_agent_context_fallback_lists_project_symbols_and_guardrails(tmp_path: Path) -> None:
    context = build_autonomous_research_agent_context(
        repo_root=tmp_path,
        asof_date=date(2026, 6, 27),
    )

    assert context.schema_version == "autonomous_research_agent_context_v1"
    assert context.project_symbol_count == 29
    assert {"BTC", "ETH", "SOL", "KPEPE", "XPL"}.issubset(context.project_symbols)
    assert context.dynamic_lockbox_month == "2026-05"
    assert context.ordinary_iteration_end_exclusive == "2026-05-01T00:00:00+00:00"
    assert context.autonomous_research_ready is False
    assert context.candidate_or_live_ready is False
    assert context.promotion_ready is False
    assert context.order_placement_instruction is False
    assert context.first_files_to_read[:2] == (
        "AGENTS.md",
        "docs/RESEARCH_AGENT_QUICKSTART.md",
    )
    assert "docs/ORCHESTRATOR_STAGE_LEDGER.md" not in context.first_files_to_read

    kpepe = next(instrument for instrument in context.instruments if instrument.symbol == "KPEPE")
    assert kpepe.binance_usdm_symbol == "1000PEPEUSDT"
    assert kpepe.bar_1m_status == "report_missing"

    rules = {rule.rule_id: rule for rule in context.no_paid_public_collection_rules}
    assert rules["official_public_no_paid_archives"].allowed is True
    assert rules["paid_requester_pays_or_credentials"].allowed is False
    assert any("work packet" in item for item in context.self_repair_policy.must_open_or_update_work_packet)
    assert any("candidate" in use for lane in context.data_lanes for use in lane.blocked_uses)


def test_agent_context_reads_local_reports_and_readiness(tmp_path: Path) -> None:
    _write_project_report(tmp_path)
    _write_materialization_report(tmp_path)
    _write_readiness_report(tmp_path)

    context = build_autonomous_research_agent_context(
        repo_root=tmp_path,
        run_id="context-test",
        asof_date=date(2026, 6, 27),
    )

    assert context.run_id == "context-test"
    assert context.autonomous_research_ready is True
    assert context.manager_readiness_status == "autonomous_research_ready"
    assert context.project_symbols == ("BTC", "ETH")
    assert context.project_symbol_count == 2

    btc = next(instrument for instrument in context.instruments if instrument.symbol == "BTC")
    assert btc.backtest_usable is True
    assert btc.bar_1m_status == "ready"
    assert btc.first_collected_month == "2024-01"
    assert btc.last_collected_month == "2026-05"

    refs = {ref.label: ref for ref in context.report_refs}
    assert refs["wpr106_546_project_1m_bar_validation"].status == "ready"
    assert refs["wpr106_546_project_1m_bar_validation"].facts["verified_row_count"] == 123
    assert refs["wpr106_552_of_style_feature_materialization"].facts["feature_row_count"] == 456
    assert refs["wpr106_556_autonomous_readiness_report"].facts["blocker_count"] == 0

    payload = json.loads(agent_context_to_json(context))
    assert payload["boundary_flags"]["research_only"] is True
    assert payload["boundary_flags"]["promotion_ready"] is False


def test_agent_context_write_rejects_secret_like_output_path(tmp_path: Path) -> None:
    context = build_autonomous_research_agent_context(repo_root=tmp_path)

    with pytest.raises(ValueError, match="secret-like"):
        write_autonomous_research_agent_context(context, tmp_path / "secret" / "context.json")


def test_agent_context_cli_prints_json_and_optionally_writes(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "out" / "agent_context.json"

    exit_code = main(
        [
            "autonomy",
            "agent-context",
            "--repo-root",
            str(tmp_path),
            "--asof-date",
            "2026-06-27",
            "--output-path",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["schema_version"] == "autonomous_research_agent_context_v1"
    assert payload["context_id"] == written["context_id"]
    assert payload["project_symbol_count"] == 29
    assert payload["promotion_ready"] is False


def _write_project_report(root: Path) -> None:
    path = root / (
        "data/research/central_market_history/manifests/"
        "wpr106-546-project-needed-1m-current-lifecycle-validation-report.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "all_project_symbols_backtest_usable_1m": True,
        "project_symbol_count": 2,
        "partial_file_count": 0,
        "normalized_manifest_verification": {
            "verified_manifest_count": 2,
            "verified_row_count": 123,
        },
        "project_rows": [
            {
                "symbol": "BTC",
                "venue_symbol": "BTCUSDT",
                "backtest_usable": True,
                "first_collected_month": "2024-01",
                "last_collected_month": "2026-05",
                "manifest_count": 29,
                "strategy_must_call_off_if_required": False,
                "verification_failures": [],
            },
            {
                "symbol": "ETH",
                "venue_symbol": "ETHUSDT",
                "backtest_usable": True,
                "first_collected_month": "2024-01",
                "last_collected_month": "2026-05",
                "manifest_count": 29,
                "strategy_must_call_off_if_required": False,
                "verification_failures": [],
            },
        ],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_materialization_report(root: Path) -> None:
    path = root / (
        "data/research/of_style_feature_materialization/wpr106_552/manifests/"
        "wpr106-552-of-style-feature-materialization-report.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "final_audit_data_ready": True,
        "archive_source_count": 1000,
        "materialized_source_count": 10,
        "input_row_count": 789,
        "feature_row_count": 456,
        "blocked_source_count": 0,
        "blocker_reasons": [],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_readiness_report(root: Path) -> None:
    path = root / "data/research/wpr106_556_autonomous_readiness/autonomous_readiness_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "autonomous_research_ready",
        "autonomous_research_ready": True,
        "blocker_count": 0,
        "report_id": "a" * 64,
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
