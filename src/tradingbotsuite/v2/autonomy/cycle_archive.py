# V2-AUDIT-ID: V2-AUD-AUTONOMY-018
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, existing_archive_refs, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_autonomy
"""Existing archive-ref bounded autopilot cycle spec writer."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.autonomy.schemas import AutopilotCyclePlanConfig
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.security.boundary import require_research_boundary

ARCHIVE_CYCLE_CONFIG_SCHEMA_VERSION = "autopilot_archive_cycle_config_v1"
ARCHIVE_CYCLE_RESULT_SCHEMA_VERSION = "autopilot_archive_cycle_result_v1"
ARCHIVE_CYCLE_MIN_SPAN_DAYS = 180


class AutopilotArchiveCycleConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = ARCHIVE_CYCLE_CONFIG_SCHEMA_VERSION
    output_root: str = Field(min_length=1)
    run_id: str = Field(default="autopilot-archive-cycle", pattern=r"^[A-Za-z0-9_.-]+$")
    archive_root: str = Field(min_length=1)
    strategy_root: str = Field(min_length=1)
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    venue: str = "hyperliquid"
    instrument_id: str = "hyperliquid:perp:BTC"
    family: str = "bars"
    timeframe: str = "1d"
    start_ts: datetime = Field(default_factory=lambda: datetime(2024, 1, 1, tzinfo=UTC))
    end_ts: datetime = Field(default_factory=lambda: datetime(2024, 8, 1, tzinfo=UTC))
    asof_date: date = Field(default_factory=date.today)
    coverage_min: float = Field(default=0.98, ge=0.98, le=1.0)
    requested_fields: tuple[str, ...] = (
        "ts",
        "instrument_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "coverage_ratio",
    )
    strategy_max_files: int = Field(default=50, ge=1, le=10_000)
    created_by_id: str = "codex-manager-agent"
    evidence_mode: str = "accepted_research"
    strategy_family: str = "uploaded_declarative_strategy"
    economic_thesis: str = (
        "Local declarative strategy spec was tested by the bounded research loop "
        "against operator-supplied accepted archive refs."
    )
    lead_avg_trades_per_month: float = Field(default=6.0, ge=0.0)
    lead_total_trades: int = Field(default=42, ge=0)
    lead_usable_months: int = Field(default=6, ge=0)
    lead_losing_months_12m: int = Field(default=0, ge=0, le=12)
    lead_positive_months_12m: int = Field(default=6, ge=0, le=12)
    lead_top_2_trades_profit_share: float = Field(default=0.0, ge=0.0, le=1.0)
    lead_best_month_profit_share: float = Field(default=0.0, ge=0.0, le=1.0)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator("evidence_mode")
    @classmethod
    def _accepted_research_only(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized != "accepted_research":
            raise ValueError("archive ref cycle evidence_mode must be accepted_research")
        return normalized

    @field_validator("requested_fields")
    @classmethod
    def _requested_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("requested_fields must not be empty")
        normalized = tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
        if not normalized:
            raise ValueError("requested_fields must not be empty")
        return normalized

    @model_validator(mode="after")
    def _validate_archive_cycle(self) -> "AutopilotArchiveCycleConfig":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if self.end_ts - self.start_ts < timedelta(days=ARCHIVE_CYCLE_MIN_SPAN_DAYS):
            raise ValueError(
                f"archive ref cycle window must span at least {ARCHIVE_CYCLE_MIN_SPAN_DAYS} days"
            )
        if self.family != "bars":
            raise ValueError("archive ref cycle currently supports family=bars for vectorized backtests")
        require_research_boundary(self, context="autopilot archive ref cycle config")
        return self


class AutopilotArchiveCycleSpecResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = ARCHIVE_CYCLE_RESULT_SCHEMA_VERSION
    run_id: str = Field(min_length=1)
    cycle_spec_path: str = Field(min_length=1)
    archive_root: str = Field(min_length=1)
    strategy_root: str = Field(min_length=1)
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    backtest_output_root: str = Field(min_length=1)
    ledger_path: str = Field(min_length=1)
    lead_book_path: str = Field(min_length=1)
    suggested_plan_output_root: str = Field(min_length=1)
    suggested_job_store_path: str = Field(min_length=1)
    declared_job_count: int = Field(ge=1)
    declared_binding_count: int = Field(ge=0)
    expected_audit_blockers: tuple[str, ...] = ()
    boundary_flags: dict[str, bool] = Field(default_factory=lambda: dict(RESEARCH_BOUNDARY))
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_result(self) -> "AutopilotArchiveCycleSpecResult":
        require_research_boundary(self, context="autopilot archive ref cycle result")
        return self


def write_autopilot_archive_cycle_spec(
    config: AutopilotArchiveCycleConfig | dict[str, Any],
) -> AutopilotArchiveCycleSpecResult:
    parsed = (
        config
        if isinstance(config, AutopilotArchiveCycleConfig)
        else AutopilotArchiveCycleConfig.model_validate(config)
    )
    root = Path(parsed.output_root).resolve(strict=False)
    run_root = (root / parsed.run_id).resolve(strict=False)
    try:
        run_root.relative_to(root)
    except ValueError as exc:
        raise ValueError("archive ref cycle output root escapes requested output_root") from exc
    archive_root = Path(parsed.archive_root).resolve(strict=False)
    strategy_root = Path(parsed.strategy_root).resolve(strict=False)
    if not archive_root.is_dir():
        raise ValueError("archive ref cycle archive_root must be an existing directory")
    if not strategy_root.is_dir():
        raise ValueError("archive ref cycle strategy_root must be an existing directory")

    strategy_queue_output_root = run_root / "strategy_queue"
    backtest_output_root = run_root / "backtests"
    ledger_path = run_root / "ledger" / "experiment_ledger.parquet"
    lead_book_path = run_root / "lead_book" / "lead_book.parquet"
    plan_output_root = run_root / "plans"
    job_store_path = run_root / "jobs.sqlite"
    if _is_relative_to(strategy_queue_output_root.resolve(strict=False), strategy_root):
        raise ValueError("archive ref cycle strategy queue output must not be inside strategy_root")
    run_root.mkdir(parents=True, exist_ok=True)

    cycle_spec = _cycle_spec_payload(
        parsed,
        archive_root=archive_root,
        strategy_root=strategy_root,
        strategy_queue_output_root=strategy_queue_output_root,
        backtest_output_root=backtest_output_root,
        ledger_path=ledger_path,
        lead_book_path=lead_book_path,
    )
    validated = AutopilotCyclePlanConfig.model_validate(cycle_spec)
    cycle_spec_path = run_root / "cycle_spec.json"
    cycle_spec_path.write_text(
        json.dumps(validated.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return AutopilotArchiveCycleSpecResult(
        run_id=parsed.run_id,
        cycle_spec_path=str(cycle_spec_path),
        archive_root=str(archive_root),
        strategy_root=str(strategy_root),
        archive_snapshot_id=parsed.archive_snapshot_id,
        universe_snapshot_id=parsed.universe_snapshot_id,
        backtest_output_root=str(backtest_output_root),
        ledger_path=str(ledger_path),
        lead_book_path=str(lead_book_path),
        suggested_plan_output_root=str(plan_output_root),
        suggested_job_store_path=str(job_store_path),
        declared_job_count=len(validated.jobs),
        declared_binding_count=len(validated.bindings),
    )


def _cycle_spec_payload(
    config: AutopilotArchiveCycleConfig,
    *,
    archive_root: Path,
    strategy_root: Path,
    strategy_queue_output_root: Path,
    backtest_output_root: Path,
    ledger_path: Path,
    lead_book_path: Path,
) -> dict[str, Any]:
    run_id = config.run_id
    universe_job_id = f"JOB-{run_id}-universe"
    archive_ref_job_id = f"JOB-{run_id}-archive-ref"
    coverage_job_id = f"JOB-{run_id}-coverage"
    strategy_queue_job_id = f"JOB-{run_id}-strategy-queue"
    backtest_data_job_id = f"JOB-{run_id}-backtest-data"
    backtest_job_id = f"JOB-{run_id}-backtest"
    validation_job_id = f"JOB-{run_id}-validation"
    ledger_job_id = f"JOB-{run_id}-ledger"
    lead_job_id = f"JOB-{run_id}-lead"
    start = utc_isoformat(config.start_ts)
    end = utc_isoformat(config.end_ts)
    return {
        "schema_version": "autopilot_bounded_cycle_spec_v1",
        "run_id": run_id,
        "mode": "bounded",
        "max_jobs": 10,
        "audit_report_path": "audit_blocker_report.json",
        "required_next_actions": [
            "review_archive_ref_cycle_audit_report",
            "preserve_research_only_non_promotable_outputs",
            "resolve_reported_blockers_before_readiness_claims",
        ],
        "jobs": [
            {
                "job_id": universe_job_id,
                "kind": "universe_refresh",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "source": "existing_ref",
                    "universe_snapshot_id": config.universe_snapshot_id,
                    "instrument_id": config.instrument_id,
                    "mode": "as_of",
                    "evidence_mode": config.evidence_mode,
                },
            },
            {
                "job_id": archive_ref_job_id,
                "kind": "recent_candle_bootstrap",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "source": "existing_ref",
                    "archive_snapshot_id": config.archive_snapshot_id,
                    "venue": config.venue,
                    "instrument_id": config.instrument_id,
                    "family": config.family,
                    "timeframe": config.timeframe,
                    "start_ts": start,
                    "end_ts": end,
                },
            },
            {
                "job_id": coverage_job_id,
                "kind": "coverage_audit",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "venue": config.venue,
                    "family": config.family,
                    "timeframe": config.timeframe,
                    "start_ts": start,
                    "end_ts": end,
                    "coverage_min": config.coverage_min,
                    "evidence_mode": config.evidence_mode,
                    "eligible_only": True,
                    "write_quality_checks": True,
                },
            },
            {
                "job_id": strategy_queue_job_id,
                "kind": "strategy_queue_scan",
                "input_spec": {
                    "strategy_root": str(strategy_root),
                    "output_root": str(strategy_queue_output_root),
                    "run_id": f"{run_id}-strategy-queue",
                    "max_files": config.strategy_max_files,
                    "require_single_accepted": True,
                },
            },
            {
                "job_id": backtest_data_job_id,
                "kind": "backtest_data_load",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "venue": config.venue,
                    "instrument_id": config.instrument_id,
                    "family": config.family,
                    "timeframe": config.timeframe,
                    "start_ts": start,
                    "end_ts": end,
                    "asof_date": config.asof_date.isoformat(),
                    "evidence_mode": config.evidence_mode,
                    "requested_fields": list(config.requested_fields),
                },
            },
            {
                "job_id": backtest_job_id,
                "kind": "vectorized_backtest",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "output_root": str(backtest_output_root),
                    "run_id": f"{run_id}-backtest",
                    "experiment_id": f"{run_id}-archive-ref-cycle",
                    "trial_index": 0,
                    "agent_or_user": config.created_by_id,
                    "venue": config.venue,
                    "instrument_id": config.instrument_id,
                    "family": config.family,
                    "timeframe": config.timeframe,
                    "start_ts": start,
                    "end_ts": end,
                    "asof_date": config.asof_date.isoformat(),
                    "evidence_mode": config.evidence_mode,
                    "universe_mode": "as_of",
                    "requested_fields": list(config.requested_fields),
                    "cost_model": _archive_cost_model(),
                },
            },
            {
                "job_id": validation_job_id,
                "kind": "validation_gate",
                "input_spec": {
                    "evidence_mode": config.evidence_mode,
                },
            },
            {
                "job_id": ledger_job_id,
                "kind": "ledger_append_export",
                "input_spec": {
                    "ledger_path": str(ledger_path),
                    "evidence_mode": config.evidence_mode,
                    "notes": (
                        "archive-ref bounded research cycle row; non-promotable "
                        "research evidence only"
                    ),
                },
            },
            {
                "job_id": lead_job_id,
                "kind": "lead_book_upsert",
                "input_spec": {
                    "lead_book_path": str(lead_book_path),
                    "source_type": "autopilot_archive_ref_cycle_ledger",
                    "strategy_family": config.strategy_family,
                    "economic_thesis": config.economic_thesis,
                    "created_by_id": config.created_by_id,
                    "instrument_scope": [config.instrument_id],
                    "venue_scope": config.venue,
                    "universe_scope": "as_of_archive_ref",
                    "data_window_start": start,
                    "data_window_end": end,
                    "data_source": "existing_accepted_archive_ref",
                    "roi_observed": 0.0,
                    "roi_projected": 0.0,
                    "roi_projection_assumptions": (
                        "projection is disabled for archive-ref bounded research-cycle rows"
                    ),
                    "roi_projection_confidence": "low",
                    "why_interesting": (
                        "A local declarative strategy spec completed the bounded "
                        "research-only worker chain over accepted archive refs."
                    ),
                    "trade_count_summary": {
                        "avg_trades_per_month": config.lead_avg_trades_per_month,
                        "total_trades": config.lead_total_trades,
                    },
                    "monthly_stability_summary": {
                        "usable_months": config.lead_usable_months,
                        "losing_months_12m": config.lead_losing_months_12m,
                        "positive_months_12m": config.lead_positive_months_12m,
                    },
                    "pnl_concentration_summary": {
                        "top_2_trades_profit_share": config.lead_top_2_trades_profit_share,
                        "best_month_profit_share": config.lead_best_month_profit_share,
                    },
                    "known_blockers": [],
                    "missing_evidence": [],
                    "required_next_validation": [
                        "human_review_archive_ref_cycle_outputs",
                        "independent_reproducibility_check",
                    ],
                    "notes": (
                        "Non-promotable archive-ref bounded research row. Do not use "
                        "as candidate-pack, paper/live, sizing, order, runtime, or "
                        "promotion evidence."
                    ),
                },
            },
        ],
        "bindings": _standard_bindings(
            universe_job_id=universe_job_id,
            archive_ref_job_id=archive_ref_job_id,
            coverage_job_id=coverage_job_id,
            strategy_queue_job_id=strategy_queue_job_id,
            backtest_data_job_id=backtest_data_job_id,
            backtest_job_id=backtest_job_id,
            validation_job_id=validation_job_id,
            ledger_job_id=ledger_job_id,
            lead_job_id=lead_job_id,
        ),
    }


def _standard_bindings(
    *,
    universe_job_id: str,
    archive_ref_job_id: str,
    coverage_job_id: str,
    strategy_queue_job_id: str,
    backtest_data_job_id: str,
    backtest_job_id: str,
    validation_job_id: str,
    ledger_job_id: str,
    lead_job_id: str,
) -> list[dict[str, str]]:
    return [
        {
            "source_job_id": universe_job_id,
            "target_job_id": coverage_job_id,
            "target_input_path": "universe_snapshot_id",
            "source_ref_prefix": "universe_snapshot_id=",
        },
        {
            "source_job_id": universe_job_id,
            "target_job_id": backtest_data_job_id,
            "target_input_path": "universe_snapshot_id",
            "source_ref_prefix": "universe_snapshot_id=",
        },
        {
            "source_job_id": archive_ref_job_id,
            "target_job_id": coverage_job_id,
            "target_input_path": "archive_snapshot_id",
            "source_ref_prefix": "archive_snapshot_id=",
        },
        {
            "source_job_id": archive_ref_job_id,
            "target_job_id": backtest_data_job_id,
            "target_input_path": "archive_snapshot_id",
            "source_ref_prefix": "archive_snapshot_id=",
        },
        {
            "source_job_id": backtest_data_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "archive_snapshot_id",
            "source_ref_prefix": "archive_snapshot_id=",
        },
        {
            "source_job_id": backtest_data_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "universe_snapshot_id",
            "source_ref_prefix": "universe_snapshot_id=",
        },
        {
            "source_job_id": backtest_data_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "expected_archive_snapshot_id",
            "source_ref_prefix": "archive_snapshot_id=",
        },
        {
            "source_job_id": backtest_data_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "expected_universe_snapshot_id",
            "source_ref_prefix": "universe_snapshot_id=",
        },
        {
            "source_job_id": backtest_data_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "expected_coverage_report_id",
            "source_ref_prefix": "coverage_report_id=",
        },
        {
            "source_job_id": backtest_data_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "expected_data_manifest_id",
            "source_ref_prefix": "data_manifest_id=",
        },
        {
            "source_job_id": backtest_data_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "expected_data_manifest_hash",
            "source_ref_prefix": "data_manifest_hash=",
        },
        {
            "source_job_id": strategy_queue_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "strategy_spec_file",
            "source_ref_prefix": "accepted_spec_path=",
        },
        {
            "source_job_id": strategy_queue_job_id,
            "target_job_id": backtest_job_id,
            "target_input_path": "strategy_spec_file_sha256",
            "source_ref_prefix": "accepted_spec_sha256=",
        },
        {
            "source_job_id": backtest_job_id,
            "target_job_id": validation_job_id,
            "target_input_path": "run_manifest_path",
            "source_ref_prefix": "run_manifest_path=",
        },
        {
            "source_job_id": backtest_job_id,
            "target_job_id": ledger_job_id,
            "target_input_path": "run_manifest_path",
            "source_ref_prefix": "run_manifest_path=",
        },
        {
            "source_job_id": validation_job_id,
            "target_job_id": ledger_job_id,
            "target_input_path": "validation_manifest_path",
            "source_ref_prefix": "validation_manifest_path=",
        },
        {
            "source_job_id": ledger_job_id,
            "target_job_id": lead_job_id,
            "target_input_path": "source_artifact_path",
            "source_ref_prefix": "ledger_path=",
        },
    ]


def _archive_cost_model() -> dict[str, Any]:
    return {
        "cost_model_id": "archive_ref_conservative_hyperliquid_taker_v1",
        "fee_side": "taker",
        "fee_bps": 6.0,
        "spread_bps": 2.0,
        "slippage_bps": 3.0,
        "impact_bps": 1.0,
        "max_volume_participation": 0.05,
        "slippage_model_id": "volume_participation_v1",
        "impact_model_id": "impact_v1",
        "funding_required": False,
        "funding_source": "archive_ref_cycle_explicit_zero_funding",
        "funding_missing_policy": "explicit_zero",
        "liquidity_stress_required": True,
        "ranking_allowed": True,
        "queue_model_documented": False,
        "stress_scenarios": ["base", "stress_2x", "stress_3x"],
    }


def _is_relative_to(child: Path, root: Path) -> bool:
    try:
        child.relative_to(root)
    except ValueError:
        return False
    return True
