# V2-AUDIT-ID: V2-AUD-AUTONOMY-001
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md
# V2-BOUNDARY: research_only, sandbox_diagnostic, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_autonomy
"""Fixture-backed v2 autonomy dry-run loop."""

from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.backtest_engine import BacktestRunConfig, RunStatus, run_vectorized_backtest
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.ledger import LedgerAppendRequest, append_run_to_ledger
from tradingbotsuite.v2.lead_book import LeadBookStore, create_lead_from_source
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads, parse_strategy_spec, validate_strategy_spec

from tradingbotsuite.v2.autonomy.schemas import (
    AutonomyBlockerReport,
    AutonomyDryRunConfig,
    AutonomyDryRunManifest,
    AutonomyDryRunResult,
    AutonomyLoopStatus,
    AutonomyStepResult,
    AutonomyStepStatus,
)

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_FIXTURE_BLOCKERS = (
    "fixture_dry_run_non_evidence",
    "real_hyperliquid_archive_operation_required",
)
_REQUIRED_NEXT_ACTIONS = (
    "refresh_hyperliquid_universe_from_allowed_source",
    "collect_or_backfill_archive_market_data",
    "run_accepted_research_coverage_and_quality_audit",
    "rerun_strategy_backtests_from_archive_snapshots",
)
_INSTRUMENTS = (
    "hyperliquid:perp:BTC",
    "hyperliquid:perp:ETH",
    "hyperliquid:perp:SOL",
)


class AutonomyLoopError(ValueError):
    """Raised when the autonomy dry-run cannot be built safely."""


def run_autonomy_dry_run(
    config: AutonomyDryRunConfig | dict[str, Any],
) -> AutonomyDryRunResult:
    parsed = config if isinstance(config, AutonomyDryRunConfig) else AutonomyDryRunConfig.model_validate(config)
    run_root = _run_root(parsed.output_root, parsed.run_id)
    fixture_root = run_root / "fixtures"
    backtest_root = run_root / "backtests"
    ledger_path = run_root / "ledger.parquet"
    lead_book_path = run_root / "lead_book.parquet"
    manifest_path = run_root / "autonomy_manifest.json"
    blocker_report_path = run_root / "blocker_report.json"
    run_root.mkdir(parents=True, exist_ok=True)
    fixture_root.mkdir(parents=True, exist_ok=True)

    steps: list[AutonomyStepResult] = []
    blocker_reasons: list[str] = list(_FIXTURE_BLOCKERS)
    artifact_paths: dict[str, str] = {}

    panel_rows = _fixture_panel_rows()
    panel_hash = canonical_json_hash(panel_rows)
    backtest_start = "2024-01-01T00:00:00Z"
    backtest_end = "2024-07-01T00:00:00Z"

    universe_payload = {
        "schema_version": "autonomy_fixture_universe_v1",
        "snapshot_id": f"{parsed.run_id}-fixture-universe",
        "venue": "hyperliquid",
        "market_type": "perp",
        "universe_mode": "as_of",
        "asof_date": "2024-01-01",
        "eligible_instruments": list(_INSTRUMENTS),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    universe_path = _write_json(fixture_root / "universe_fixture.json", universe_payload)
    artifact_paths["universe_fixture"] = str(universe_path)
    steps.append(
        AutonomyStepResult(
            name="universe_fixture",
            status=AutonomyStepStatus.PASSED,
            artifact_path=str(universe_path),
            details={
                "snapshot_id": universe_payload["snapshot_id"],
                "instrument_count": len(_INSTRUMENTS),
                "universe_mode": "as_of",
            },
        )
    )

    archive_payload = {
        "schema_version": "autonomy_fixture_archive_v1",
        "archive_snapshot_id": f"{parsed.run_id}-fixture-archive",
        "data_manifest_id": f"{parsed.run_id}-fixture-data",
        "venue_scope": "hyperliquid",
        "start_ts": backtest_start,
        "end_ts": backtest_end,
        "panel_row_count": len(panel_rows),
        "panel_hash": panel_hash,
        "source": "generated_autonomy_fixture",
        "evidence_mode": parsed.evidence_mode,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    archive_path = _write_json(fixture_root / "archive_fixture_manifest.json", archive_payload)
    artifact_paths["archive_fixture"] = str(archive_path)
    steps.append(
        AutonomyStepResult(
            name="archive_fixture",
            status=AutonomyStepStatus.PASSED,
            artifact_path=str(archive_path),
            details={
                "archive_snapshot_id": archive_payload["archive_snapshot_id"],
                "data_manifest_id": archive_payload["data_manifest_id"],
                "panel_row_count": len(panel_rows),
            },
        )
    )

    coverage_payload = {
        "schema_version": "autonomy_fixture_coverage_v1",
        "coverage_floor": 0.98,
        "coverage_ratio_min": 1.0,
        "quality_status": "pass",
        "evidence_mode": parsed.evidence_mode,
        "lockbox_policy_id": "dynamic_full_calendar_months_v1",
        "lockbox_excluded": True,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    coverage_path = _write_json(fixture_root / "coverage_fixture.json", coverage_payload)
    artifact_paths["coverage_fixture"] = str(coverage_path)
    steps.append(
        AutonomyStepResult(
            name="coverage_fixture",
            status=AutonomyStepStatus.PASSED,
            artifact_path=str(coverage_path),
            details={
                "coverage_floor": 0.98,
                "coverage_ratio_min": 1.0,
                "quality_status": "pass",
            },
        )
    )

    strategy_payload = _strategy_payload(parsed.strategy_id)
    validation_result = validate_strategy_spec(strategy_payload)
    if not validation_result.ok:
        blocker_reasons.extend(validation_result.errors)
        steps.append(
            AutonomyStepResult(
                name="strategy_spec_validation",
                status=AutonomyStepStatus.FAILED,
                details={"errors": list(validation_result.errors)},
                blocker_reasons=validation_result.errors,
            )
        )
        status = AutonomyLoopStatus.FAILED
    else:
        status = AutonomyLoopStatus.COMPLETED_WITH_BLOCKERS
        steps.append(
            AutonomyStepResult(
                name="strategy_spec_validation",
                status=AutonomyStepStatus.PASSED,
                details={
                    "strategy_id": validation_result.strategy_id,
                    "spec_hash": validation_result.spec_hash,
                    "evidence_mode": parsed.evidence_mode,
                },
            )
        )

    spec = parse_strategy_spec(strategy_payload)
    backtest_run_id = f"{parsed.run_id}-backtest"
    backtest_result = run_vectorized_backtest(
        config=BacktestRunConfig(
            run_id=backtest_run_id,
            experiment_id="autonomy-dry-run",
            trial_index=0,
            output_root=str(backtest_root),
            archive_snapshot_id=str(archive_payload["archive_snapshot_id"]),
            universe_snapshot_id=str(universe_payload["snapshot_id"]),
            data_manifest_id=str(archive_payload["data_manifest_id"]),
            data_manifest_hash=canonical_json_hash(archive_payload),
            validation_manifest_hash=canonical_json_hash(coverage_payload),
            cost_manifest_hash=canonical_json_hash(
                {
                    "cost_model_id": "conservative_hyperliquid_taker_v1",
                    "cost_stress_scenarios": ("base", "stress_2x", "stress_3x"),
                }
            ),
            universe_mode="as_of",
            venue_scope="hyperliquid",
            data_coverage_min=0.98,
            git_sha="autonomy-dry-run",
        ),
        strategy_spec=spec,
        panel_rows=panel_rows,
    )
    run_manifest_path = Path(backtest_result.run_dir) / "run_manifest.json"
    artifact_paths["backtest_run_manifest"] = str(run_manifest_path)
    steps.append(
        AutonomyStepResult(
            name="backtest",
            status=AutonomyStepStatus.PASSED
            if backtest_result.manifest.status == RunStatus.SUCCEEDED
            else AutonomyStepStatus.FAILED,
            artifact_path=str(run_manifest_path),
            details={
                "run_id": backtest_result.manifest.run_id,
                "status": backtest_result.manifest.status.value,
                "validation_status": backtest_result.manifest.validation_status.value,
                "usable_months": backtest_result.manifest.usable_months,
                "data_coverage_min": backtest_result.manifest.data_coverage_min,
            },
            blocker_reasons=()
            if backtest_result.manifest.status == RunStatus.SUCCEEDED
            else (backtest_result.manifest.failure_reason or "backtest_failed",),
        )
    )
    if backtest_result.manifest.status != RunStatus.SUCCEEDED:
        status = AutonomyLoopStatus.FAILED
        blocker_reasons.append(backtest_result.manifest.failure_reason or "backtest_failed")

    ledger_row = append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(run_manifest_path),
            ledger_path=str(ledger_path),
            evidence_mode=parsed.evidence_mode,
            notes="autonomy dry-run; fixture_dry_run_non_evidence; real archive operation required",
        )
    )
    artifact_paths["ledger"] = str(ledger_path)
    steps.append(
        AutonomyStepResult(
            name="ledger_append",
            status=AutonomyStepStatus.PASSED,
            artifact_path=str(ledger_path),
            details={
                "run_id": ledger_row.run_id,
                "ledger_index": ledger_row.ledger_index,
                "row_status": ledger_row.row_status,
                "evidence_mode": ledger_row.evidence_mode,
            },
        )
    )

    if backtest_result.metrics is None:
        status = AutonomyLoopStatus.FAILED
        blocker_reasons.append("backtest_metrics_missing")
        steps.append(
            AutonomyStepResult(
                name="lead_book_update",
                status=AutonomyStepStatus.BLOCKED,
                details={"reason": "backtest_metrics_missing"},
                blocker_reasons=("backtest_metrics_missing",),
            )
        )
    else:
        lead = create_lead_from_source(
            source_artifact_path=run_manifest_path,
            source_type="autonomy_dry_run",
            strategy_family=spec.strategy_family,
            economic_thesis="Fixture-backed loop check for research-only strategy evaluation plumbing.",
            created_by_id=parsed.created_by_id,
            instrument_scope=_INSTRUMENTS,
            data_window_start=backtest_result.manifest.backtest_start,
            data_window_end=backtest_result.manifest.backtest_end,
            data_source="generated_autonomy_fixture",
            roi_observed=backtest_result.metrics.net_return,
            roi_projected=0.0,
            roi_projection_assumptions="Fixture dry-run projection is not a claim and is not accepted evidence.",
            why_interesting="Exercises universe, archive, coverage, strategy spec, backtest, ledger, Lead Book, and blocker-report wiring.",
            trade_count_summary={
                "avg_trades_per_month": backtest_result.metrics.trade_count
                / max(1, backtest_result.manifest.usable_months),
                "total_trades": backtest_result.metrics.trade_count,
            },
            monthly_stability_summary={
                "usable_months": backtest_result.manifest.usable_months,
                "losing_months_12m": 0,
                "positive_months_12m": min(12, backtest_result.manifest.usable_months),
            },
            pnl_concentration_summary={
                "top_2_trades_profit_share": 0.0,
                "best_month_profit_share": 0.0,
            },
            known_blockers=tuple(blocker_reasons),
            missing_evidence=("real_hyperliquid_archive_snapshot", "accepted_research_coverage_manifest"),
            required_next_validation=_REQUIRED_NEXT_ACTIONS,
            notes="Autonomy dry-run lead only; non-promotable and sandbox diagnostic.",
        )
        lead = lead.model_copy(
            update={
                "archive_snapshot_id": str(archive_payload["archive_snapshot_id"]),
                "universe_snapshot_id": str(universe_payload["snapshot_id"]),
                "feature_snapshot_id": str(archive_payload["data_manifest_id"]),
            }
        )
        LeadBookStore(lead_book_path).upsert(lead)
        blocker_reasons.extend(lead.known_blockers)
        artifact_paths["lead_book"] = str(lead_book_path)
        steps.append(
            AutonomyStepResult(
                name="lead_book_update",
                status=AutonomyStepStatus.PASSED,
                artifact_path=str(lead_book_path),
                details={
                    "lead_id": lead.lead_id,
                    "state": lead.state.value,
                    "promotion_ready": lead.promotion_ready,
                    "known_blockers": list(lead.known_blockers),
                },
            )
        )

    blocker_reasons = list(dict.fromkeys(blocker_reasons))
    if status != AutonomyLoopStatus.FAILED and blocker_reasons:
        status = AutonomyLoopStatus.COMPLETED_WITH_BLOCKERS
    report = AutonomyBlockerReport(
        run_id=parsed.run_id,
        status=status,
        blocker_reasons=tuple(blocker_reasons),
        required_next_actions=_REQUIRED_NEXT_ACTIONS,
    )
    _write_json(blocker_report_path, report.model_dump(mode="json"))
    artifact_paths["blocker_report"] = str(blocker_report_path)
    steps.append(
        AutonomyStepResult(
            name="blocker_report",
            status=AutonomyStepStatus.PASSED,
            artifact_path=str(blocker_report_path),
            details={
                "blocker_count": len(report.blocker_reasons),
                "accepted_research_ready": report.accepted_research_ready,
            },
            blocker_reasons=report.blocker_reasons,
        )
    )

    manifest = AutonomyDryRunManifest(
        run_id=parsed.run_id,
        status=status,
        strategy_id=spec.strategy_id,
        backtest_run_id=backtest_run_id,
        output_root=str(run_root),
        backtest_run_dir=backtest_result.run_dir,
        ledger_path=str(ledger_path),
        lead_book_path=str(lead_book_path),
        blocker_report_path=str(blocker_report_path),
        artifact_paths=artifact_paths,
        steps=tuple(steps),
        decisions_made=(
            "fixture_data_is_sandbox_diagnostic_not_accepted_research",
            "dry_run_outputs_are_written_only_under_requested_output_root",
            "lead_book_row_is_non_promotable_and_carries_missing_real_evidence_blockers",
        ),
        blocker_reasons=report.blocker_reasons,
        boundary_flags=dict(RESEARCH_BOUNDARY),
    )
    _write_json(manifest_path, manifest.model_dump(mode="json"))
    return AutonomyDryRunResult(
        status=status,
        manifest_path=str(manifest_path),
        blocker_report_path=str(blocker_report_path),
        ledger_path=str(ledger_path),
        lead_book_path=str(lead_book_path),
        backtest_run_dir=backtest_result.run_dir,
        blocker_reasons=report.blocker_reasons,
    )


def _run_root(output_root: str | Path, run_id: str) -> Path:
    if not _SAFE_RUN_ID.fullmatch(run_id):
        raise AutonomyLoopError(f"unsafe_run_id: {run_id}")
    root = Path(output_root).resolve()
    run_root = (root / run_id).resolve()
    try:
        run_root.relative_to(root)
    except ValueError as exc:
        raise AutonomyLoopError("autonomy_run_root_escapes_output_root") from exc
    return run_root


def _strategy_payload(strategy_id: str) -> dict[str, Any]:
    examples = example_strategy_payloads()
    if strategy_id not in examples:
        raise AutonomyLoopError(f"unknown_strategy_id: {strategy_id}")
    payload = json.loads(json.dumps(examples[strategy_id]))
    payload["validation"]["evidence_mode"] = "sandbox_diagnostic"
    return payload


def _fixture_panel_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 7, 1, tzinfo=UTC)
    bases = {
        "hyperliquid:perp:BTC": 42_000.0,
        "hyperliquid:perp:ETH": 2_300.0,
        "hyperliquid:perp:SOL": 95.0,
    }
    current = start
    hour_index = 0
    while current <= end:
        for offset, instrument_id in enumerate(_INSTRUMENTS):
            base = bases[instrument_id]
            trend = 1.0 + (hour_index * 0.00002 * (offset + 1))
            wave = math.sin((hour_index / 18.0) + offset)
            open_price = base * trend * (1.0 + 0.01 * wave)
            close = open_price * (1.0 + 0.0015 * math.sin((hour_index / 7.0) + offset))
            high = max(open_price, close) * 1.002
            low = min(open_price, close) * 0.998
            funding_sign = 1.0 if ((hour_index // 12) + offset) % 2 == 0 else -1.0
            funding_rate = funding_sign * (0.00015 + (offset * 0.00003))
            rows.append(
                {
                    "ts": current.isoformat().replace("+00:00", "Z"),
                    "instrument_id": instrument_id,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": 5_000_000.0 + (hour_index * 1000.0) + (offset * 100_000.0),
                    "funding": funding_rate,
                    "funding_rate": funding_rate,
                    "open_interest": 50_000_000.0 + (offset * 5_000_000.0),
                    "mark_price": close,
                    "oracle_price": close,
                    "spread": 0.001,
                    "coverage_ratio": 1.0,
                }
            )
        current += timedelta(hours=1)
        hour_index += 1
    return rows


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return path
