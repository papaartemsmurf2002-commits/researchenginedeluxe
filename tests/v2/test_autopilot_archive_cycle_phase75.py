from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from tradingbotsuite.v2.archive import ArchiveLayer, ArchiveLayout, ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.autonomy import (
    AutopilotArchiveCycleConfig,
    load_autopilot_cycle_spec,
    plan_autopilot_research_cycle,
    run_autopilot_cycle_plan,
    write_autopilot_archive_cycle_spec,
)
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode
from tradingbotsuite.v2.lead_book import LeadBookStore
from tradingbotsuite.v2.ledger import read_ledger
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads, validate_strategy_spec
from tradingbotsuite.v2.universe.hyperliquid import refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobStatus

INSTRUMENT = "hyperliquid:perp:BTC"


def test_archive_cycle_spec_runs_existing_ref_bounded_chain(tmp_path) -> None:
    fixture = _accepted_archive_fixture(tmp_path)
    strategy_root = _write_strategy_root(tmp_path)
    result = write_autopilot_archive_cycle_spec(
        AutopilotArchiveCycleConfig(
            output_root=str(tmp_path / "archive-cycle"),
            run_id="cycle-archive-pass",
            archive_root=str(fixture["archive_root"]),
            strategy_root=str(strategy_root),
            archive_snapshot_id=fixture["archive_snapshot_id"],
            universe_snapshot_id=fixture["universe_snapshot_id"],
            asof_date=date(2026, 6, 21),
            requested_fields=(
                "ts",
                "instrument_id",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "funding",
                "coverage_ratio",
            ),
        )
    )
    spec = _read_json(Path(result.cycle_spec_path))

    assert result.declared_job_count == 9
    assert result.declared_binding_count == 17
    assert result.expected_audit_blockers == ()
    assert spec["run_id"] == "cycle-archive-pass"
    assert [job["kind"] for job in spec["jobs"]] == [
        "universe_refresh",
        "recent_candle_bootstrap",
        "coverage_audit",
        "strategy_queue_scan",
        "backtest_data_load",
        "vectorized_backtest",
        "validation_gate",
        "ledger_append_export",
        "lead_book_upsert",
    ]
    jobs = {job["kind"]: job for job in spec["jobs"]}
    assert jobs["universe_refresh"]["input_spec"]["source"] == "existing_ref"
    assert jobs["recent_candle_bootstrap"]["input_spec"]["source"] == "existing_ref"
    assert jobs["coverage_audit"]["input_spec"]["evidence_mode"] == "accepted_research"
    assert jobs["strategy_queue_scan"]["input_spec"]["strategy_root"] == str(strategy_root.resolve())
    assert jobs["strategy_queue_scan"]["input_spec"]["require_single_accepted"] is True
    assert "strategy_spec_file" not in jobs["vectorized_backtest"]["input_spec"]
    assert "strategy_spec" not in jobs["vectorized_backtest"]["input_spec"]
    assert jobs["lead_book_upsert"]["input_spec"]["known_blockers"] == []
    assert jobs["lead_book_upsert"]["input_spec"]["missing_evidence"] == []
    serialized_jobs = json.dumps(spec["jobs"], sort_keys=True)
    assert "public_api" not in serialized_jobs
    assert "payload_file" not in serialized_jobs
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
    execution = run_autopilot_cycle_plan(
        plan.plan_manifest_path,
        worker_id="archive-cycle-runner",
    )
    manifest = _read_json(Path(execution.execution_manifest_path))
    report = _read_json(Path(plan.audit_report_path))

    assert execution.status.value == "completed"
    assert execution.executed_job_count == 10
    assert execution.skipped_job_count == 0
    assert execution.audit_attempted is True
    assert manifest["accepted_research_ready"] is False
    assert manifest["promotion_ready"] is False
    assert all(job["action"] == "ran" for job in manifest["job_executions"])
    assert all(job["status_after"] == "succeeded" for job in manifest["job_executions"])
    assert "fixture_cycle_non_evidence" not in report["blocker_reasons"]
    assert "public_api_recent_window_non_evidence" not in report["blocker_reasons"]
    assert report["status"] == "pass"
    assert report["blocker_reasons"] == []
    assert report["accepted_research_ready"] is False

    store = WorkerJobStore(result.suggested_job_store_path)
    assert all(job.status == WorkerJobStatus.SUCCEEDED for job in store.list_jobs())
    universe_job = store.load_job("JOB-cycle-archive-pass-universe")
    archive_ref_job = store.load_job("JOB-cycle-archive-pass-archive-ref")
    strategy_queue_job = store.load_job("JOB-cycle-archive-pass-strategy-queue")
    backtest_data_job = store.load_job("JOB-cycle-archive-pass-backtest-data")
    backtest_job = store.load_job("JOB-cycle-archive-pass-backtest")
    lead_job = store.load_job("JOB-cycle-archive-pass-lead")
    assert universe_job is not None
    assert archive_ref_job is not None
    assert strategy_queue_job is not None
    assert backtest_data_job is not None
    assert backtest_job is not None
    assert lead_job is not None
    assert "source_mode=existing_ref" in universe_job.output_refs
    assert "source_mode=existing_ref" in archive_ref_job.output_refs
    assert f"archive_snapshot_id={fixture['archive_snapshot_id']}" in archive_ref_job.output_refs
    assert "accepted_count=1" in strategy_queue_job.output_refs
    assert any(ref.startswith("data_manifest_id=") for ref in backtest_data_job.output_refs)
    assert "strategy_spec_source=file" in backtest_job.output_refs
    assert any(ref.startswith("known_blockers=") for ref in lead_job.output_refs)

    ledger_rows = read_ledger(Path(result.ledger_path))
    assert len(ledger_rows) == 1
    assert ledger_rows[0].evidence_mode == "accepted_research"
    assert ledger_rows[0].promotion_ready is False
    assert ledger_rows[0].candidate_evidence is False

    leads = LeadBookStore(result.lead_book_path).read()
    assert len(leads) == 1
    lead = leads[0]
    assert lead.promotion_ready is False
    assert lead.candidate_evidence is False
    assert lead.source_artifact_path == str(Path(result.ledger_path).resolve())


def test_archive_cycle_cli_writes_existing_ref_spec(tmp_path, capsys) -> None:
    fixture = _accepted_archive_fixture(tmp_path)
    strategy_root = _write_strategy_root(tmp_path)

    exit_code = main(
        [
            "autopilot",
            "archive-cycle-spec",
            "--output-root",
            str(tmp_path / "cli-archive-cycle"),
            "--run-id",
            "cycle-archive-cli",
            "--archive-root",
            str(fixture["archive_root"]),
            "--strategy-root",
            str(strategy_root),
            "--archive-snapshot-id",
            fixture["archive_snapshot_id"],
            "--universe-snapshot-id",
            fixture["universe_snapshot_id"],
            "--asof-date",
            "2026-06-21",
        ]
    )
    output = capsys.readouterr().out
    values = dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)

    assert exit_code == 0
    assert values["source_mode"] == "existing_ref"
    assert values["evidence_mode"] == "accepted_research"
    assert values["accepted_research_ready"] == "false"
    assert values["promotion_ready"] == "false"
    assert values["declared_job_count"] == "9"
    assert values["declared_binding_count"] == "17"
    assert Path(values["cycle_spec"]).exists()
    assert values["archive_snapshot_id"] == fixture["archive_snapshot_id"]
    assert values["universe_snapshot_id"] == fixture["universe_snapshot_id"]


def _accepted_archive_fixture(tmp_path: Path) -> dict[str, str | Path]:
    archive_root = tmp_path / "archive"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 8, 1, tzinfo=UTC)
    rows = _daily_rows(start_ts, end_ts)
    write_parquet_rows(
        layout=layout,
        store=store,
        rows=rows,
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date=start_ts.date().isoformat(),
        timeframe="1d",
        job_id="job-archive-cycle-silver",
        source_file_ids=("source-archive-cycle",),
        instrument_id=INSTRUMENT,
    )
    report = coverage_report_for_bars(
        rows,
        venue="hyperliquid",
        instrument_id=INSTRUMENT,
        timeframe="1d",
        start_ts=start_ts,
        end_ts=end_ts,
        evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
    )
    CoverageManifestStore(layout).append_coverage_report(report)
    snapshot = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope="hyperliquid",
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=[report.model_dump(mode="json")],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="archive_ref_cycle_fixture",
    )
    universe = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_universe_payload(),
        asof_date=date(2024, 1, 1),
        mode=UniverseMode.AS_OF,
    )
    return {
        "archive_root": archive_root,
        "archive_snapshot_id": snapshot.archive_snapshot_id,
        "universe_snapshot_id": universe.snapshot_id,
    }


def _write_strategy_root(tmp_path: Path) -> Path:
    strategy_root = tmp_path / "strategy_specs"
    strategy_root.mkdir()
    payload = json.loads(json.dumps(example_strategy_payloads()["hl_funding_carry_v1"]))
    payload["strategy_id"] = "hl_archive_cycle_funding_carry_v1"
    payload["inputs"]["timeframe"] = "1d"
    payload["inputs"]["fields"] = ["close", "funding", "volume", "coverage_ratio"]
    payload["logic"]["lookback_bars"] = 1
    payload["logic"]["entry_threshold"] = 0.0001
    payload["logic"]["filters"] = {"min_volume": 1000, "min_coverage": 0.98}
    payload["risk"]["rebalance"] = "1d"
    payload["validation"]["min_backtest_months"] = 6
    payload["validation"]["evidence_mode"] = "accepted_research"
    payload["validation"]["universe_mode"] = "as_of"
    validation = validate_strategy_spec(payload)
    assert validation.ok, validation.errors
    (strategy_root / "archive_funding_carry.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return strategy_root


def _daily_rows(start_ts: datetime, end_ts: datetime) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start_ts
    index = 0
    while current < end_ts:
        close = 200.0 - (index * 0.2) - ((index % 7) * 0.1)
        rows.append(
            {
                "venue": "hyperliquid",
                "instrument_id": INSTRUMENT,
                "timeframe": "1d",
                "ts": current.isoformat().replace("+00:00", "Z"),
                "end_ts": (current + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "open": close - 0.15,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 100_000.0 + index,
                "trade_count": index + 1,
                "funding": 0.002,
                "funding_rate": 0.002,
                "open_interest": 5_000_000.0 + index,
                "mark_price": close,
                "oracle_price": close,
                "spread": 0.001,
                "coverage_ratio": 1.0,
                "source_timeframe": "1d",
                "source_file_id": "f" * 64,
                "source_layer": "bronze",
                "normalization_warnings": (),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
        current += timedelta(days=1)
        index += 1
    return rows


def _universe_payload() -> list[object]:
    return [
        {
            "universe": [
                {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
                {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
            ]
        },
        [
            {
                "dayNtlVlm": "100000000",
                "openInterest": "1000",
                "markPx": "60000",
                "funding": "0.00001",
            },
            {
                "dayNtlVlm": "1000",
                "openInterest": "10",
                "markPx": "100",
                "funding": "0.0",
            },
        ],
    ]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
