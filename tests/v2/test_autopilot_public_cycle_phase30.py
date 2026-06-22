from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.autonomy import (
    AutopilotCyclePlanStatus,
    AutopilotPublicCandleCycleConfig,
    load_autopilot_cycle_spec,
    plan_autopilot_research_cycle,
    write_autopilot_public_candle_cycle_spec,
)
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.workers.job_store import WorkerJobStore


def test_public_candle_cycle_spec_enqueues_public_api_diagnostic_jobs(tmp_path) -> None:
    result = write_autopilot_public_candle_cycle_spec(
        AutopilotPublicCandleCycleConfig(
            output_root=str(tmp_path / "public-cycle"),
            run_id="public-cycle-pass",
            public_info_url="https://example.test/info",
            asof_date=date(2026, 6, 21),
        )
    )
    spec = _read_json(Path(result.cycle_spec_path))

    assert result.declared_job_count == 8
    assert result.declared_binding_count == 10
    assert "public_api_current_universe_not_historical_asof" in result.expected_audit_blockers
    assert [job["kind"] for job in spec["jobs"]] == [
        "universe_refresh",
        "recent_candle_bootstrap",
        "coverage_audit",
        "strategy_queue_scan",
        "vectorized_backtest",
        "validation_gate",
        "ledger_append_export",
        "lead_book_upsert",
    ]
    jobs = {job["kind"]: job for job in spec["jobs"]}
    universe_spec = jobs["universe_refresh"]["input_spec"]
    candle_spec = jobs["recent_candle_bootstrap"]["input_spec"]
    strategy_queue_spec = jobs["strategy_queue_scan"]["input_spec"]
    backtest_spec = jobs["vectorized_backtest"]["input_spec"]
    validation_spec = jobs["validation_gate"]["input_spec"]
    lead_spec = jobs["lead_book_upsert"]["input_spec"]

    assert universe_spec["source"] == "public_api"
    assert universe_spec["mode"] == "current"
    assert universe_spec["public_info_url"] == "https://example.test/info"
    assert candle_spec["source"] == "public_api"
    assert candle_spec["public_info_url"] == "https://example.test/info"
    assert candle_spec["max_candles_per_public_page"] == 5000
    assert "records" not in candle_spec
    assert "records_file" not in candle_spec
    assert "trusted_source_root" not in candle_spec
    strategy_files = sorted(Path(strategy_queue_spec["strategy_root"]).glob("*.json"))
    assert len(strategy_files) == 1
    strategy_payload = _read_json(strategy_files[0])
    assert strategy_queue_spec["require_single_accepted"] is True
    assert backtest_spec["evidence_mode"] == "sandbox_diagnostic"
    assert backtest_spec["universe_mode"] == "current"
    assert "strategy_spec" not in backtest_spec
    assert "strategy_spec_file" not in backtest_spec
    assert validation_spec["evidence_mode"] == "sandbox_diagnostic"
    assert "run_manifest_path" not in validation_spec
    assert strategy_payload["validation"]["evidence_mode"] == "sandbox_diagnostic"
    assert strategy_payload["validation"]["universe_mode"] == "current"
    assert lead_spec["universe_scope"] == "current_public_api_diagnostic"
    assert "public_api_recent_window_non_evidence" in lead_spec["known_blockers"]
    assert "accepted_historical_candle_coverage" in lead_spec["missing_evidence"]
    assert spec["required_next_actions"] == [
        "run_public_api_cycle_only_as_diagnostic",
        "replace_current_universe_with_historical_asof_universe_evidence",
        "prove_accepted_historical_coverage_before_readiness",
        "run_independent_completion_audit_before_autonomous_ready",
        "preserve_research_only_non_promotable_outputs",
    ]
    serialized_jobs = json.dumps(spec["jobs"], sort_keys=True)
    for unsafe_flag in (
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    ):
        assert f'"{unsafe_flag}": true' not in serialized_jobs

    config = load_autopilot_cycle_spec(result.cycle_spec_path)
    plan = plan_autopilot_research_cycle(
        config,
        output_root=result.suggested_plan_output_root,
        job_store_path=result.suggested_job_store_path,
        enqueue=True,
    )
    store = WorkerJobStore(result.suggested_job_store_path)
    queued_candles = store.load_job("JOB-public-cycle-pass-candles")

    assert plan.status == AutopilotCyclePlanStatus.ENQUEUED
    assert plan.planned_job_count == 9
    assert plan.enqueued_job_count == 9
    assert queued_candles is not None
    assert queued_candles.input_spec["source"] == "public_api"
    assert queued_candles.input_spec["public_info_url"] == "https://example.test/info"


def test_public_candle_cycle_spec_rejects_short_windows(tmp_path) -> None:
    with pytest.raises(ValidationError, match="at least 180 days"):
        AutopilotPublicCandleCycleConfig(
            output_root=str(tmp_path / "short-public-cycle"),
            run_id="short-public-cycle",
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 2, 1, tzinfo=UTC),
        )


def test_public_candle_cycle_cli_writes_spec_paths(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "autopilot",
            "public-candle-cycle-spec",
            "--output-root",
            str(tmp_path / "cli-public-cycle"),
            "--run-id",
            "public-cycle-cli",
            "--public-info-url",
            "https://example.test/info",
            "--asof-date",
            "2026-06-21",
        ]
    )
    output = capsys.readouterr().out
    lines = output.strip().splitlines()
    values = dict(
        line.split("=", 1)
        for line in lines
        if "=" in line and not line.startswith("expected_audit_blocker=")
    )
    blockers = [
        line.split("=", 1)[1]
        for line in lines
        if line.startswith("expected_audit_blocker=")
    ]

    assert exit_code == 0
    assert values["source_mode"] == "public_api"
    assert values["evidence_mode"] == "sandbox_diagnostic"
    assert values["accepted_research_ready"] == "false"
    assert values["promotion_ready"] == "false"
    assert values["declared_job_count"] == "8"
    assert values["declared_binding_count"] == "10"
    assert Path(values["cycle_spec"]).exists()
    assert values["public_info_url"] == "https://example.test/info"
    assert "public_api_current_universe_not_historical_asof" in blockers
    assert "authoritative_full_suite_validation_required" in blockers


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
