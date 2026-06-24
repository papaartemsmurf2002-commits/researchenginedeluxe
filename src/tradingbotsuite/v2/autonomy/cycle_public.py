# V2-AUDIT-ID: V2-AUD-AUTONOMY-009
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, public_api_diagnostic_spec, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_autonomy
"""Public-API diagnostic bounded autopilot cycle spec writer."""

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
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads, validate_strategy_spec

PUBLIC_CYCLE_CONFIG_SCHEMA_VERSION = "autopilot_public_candle_cycle_config_v1"
PUBLIC_CYCLE_RESULT_SCHEMA_VERSION = "autopilot_public_candle_cycle_result_v1"
PUBLIC_CYCLE_MIN_SPAN_DAYS = 180
PUBLIC_CYCLE_MAX_PUBLIC_CANDLES_PER_PAGE = 5_000

_JOB_INPUT_BOUNDARY_KEYS = frozenset(
    {
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    }
)


class AutopilotPublicCandleCycleConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = PUBLIC_CYCLE_CONFIG_SCHEMA_VERSION
    output_root: str = Field(min_length=1)
    run_id: str = Field(default="autopilot-public-candle-cycle", pattern=r"^[A-Za-z0-9_.-]+$")
    venue: str = "hyperliquid"
    instrument_id: str = "hyperliquid:perp:BTC"
    coin: str = "BTC"
    timeframe: str = "1d"
    start_ts: datetime = Field(default_factory=lambda: datetime(2024, 1, 1, tzinfo=UTC))
    end_ts: datetime = Field(default_factory=lambda: datetime(2024, 8, 1, tzinfo=UTC))
    asof_date: date = Field(default_factory=date.today)
    min_day_notional_usd: int = Field(default=5_000_000, ge=1)
    coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
    public_info_url: str = Field(default="https://api.hyperliquid.xyz/info", min_length=1)
    public_info_timeout: float = Field(default=20.0, gt=0.0)
    max_public_info_pages: int = Field(default=50, ge=1, le=1_000)
    max_candles_per_public_page: int = Field(
        default=PUBLIC_CYCLE_MAX_PUBLIC_CANDLES_PER_PAGE,
        ge=1,
        le=PUBLIC_CYCLE_MAX_PUBLIC_CANDLES_PER_PAGE,
    )
    created_by_id: str = "codex-manager-agent"
    evidence_mode: str = "sandbox_diagnostic"
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
    def _sandbox_only(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized != "sandbox_diagnostic":
            raise ValueError("public diagnostic cycle evidence_mode must be sandbox_diagnostic")
        return normalized

    @model_validator(mode="after")
    def _validate_public_cycle(self) -> "AutopilotPublicCandleCycleConfig":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if self.end_ts - self.start_ts < timedelta(days=PUBLIC_CYCLE_MIN_SPAN_DAYS):
            raise ValueError(
                f"public diagnostic cycle window must span at least {PUBLIC_CYCLE_MIN_SPAN_DAYS} days"
            )
        require_research_boundary(self, context="autopilot public candle cycle config")
        return self


class AutopilotPublicCandleCycleSpecResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = PUBLIC_CYCLE_RESULT_SCHEMA_VERSION
    run_id: str = Field(min_length=1)
    cycle_spec_path: str = Field(min_length=1)
    archive_root: str = Field(min_length=1)
    backtest_output_root: str = Field(min_length=1)
    ledger_path: str = Field(min_length=1)
    lead_book_path: str = Field(min_length=1)
    suggested_plan_output_root: str = Field(min_length=1)
    suggested_job_store_path: str = Field(min_length=1)
    public_info_url: str = Field(min_length=1)
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
    def _validate_result(self) -> "AutopilotPublicCandleCycleSpecResult":
        require_research_boundary(self, context="autopilot public candle cycle result")
        return self


def write_autopilot_public_candle_cycle_spec(
    config: AutopilotPublicCandleCycleConfig | dict[str, Any],
) -> AutopilotPublicCandleCycleSpecResult:
    parsed = (
        config
        if isinstance(config, AutopilotPublicCandleCycleConfig)
        else AutopilotPublicCandleCycleConfig.model_validate(config)
    )
    root = Path(parsed.output_root).resolve(strict=False)
    run_root = (root / parsed.run_id).resolve(strict=False)
    try:
        run_root.relative_to(root)
    except ValueError as exc:
        raise ValueError("public diagnostic cycle output root escapes requested output_root") from exc

    archive_root = run_root / "archive"
    strategy_root = run_root / "strategy_specs"
    strategy_queue_output_root = run_root / "strategy_queue"
    backtest_output_root = run_root / "backtests"
    ledger_path = run_root / "ledger" / "experiment_ledger.parquet"
    lead_book_path = run_root / "lead_book" / "lead_book.parquet"
    plan_output_root = run_root / "plans"
    job_store_path = run_root / "jobs.sqlite"
    run_root.mkdir(parents=True, exist_ok=True)
    strategy_root.mkdir(parents=True, exist_ok=True)
    strategy_spec_file = strategy_root / "public_diagnostic_mean_reversion.json"
    strategy_spec_file.write_text(
        json.dumps(_public_strategy_spec(parsed), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

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
    return AutopilotPublicCandleCycleSpecResult(
        run_id=parsed.run_id,
        cycle_spec_path=str(cycle_spec_path),
        archive_root=str(archive_root),
        backtest_output_root=str(backtest_output_root),
        ledger_path=str(ledger_path),
        lead_book_path=str(lead_book_path),
        suggested_plan_output_root=str(plan_output_root),
        suggested_job_store_path=str(job_store_path),
        public_info_url=parsed.public_info_url,
        declared_job_count=len(validated.jobs),
        declared_binding_count=len(validated.bindings),
        expected_audit_blockers=_expected_blockers(),
    )


def _cycle_spec_payload(
    config: AutopilotPublicCandleCycleConfig,
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
    candles_job_id = f"JOB-{run_id}-candles"
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
            "run_public_api_cycle_only_as_diagnostic",
            "replace_current_universe_with_historical_asof_universe_evidence",
            "prove_accepted_historical_coverage_before_readiness",
            "run_independent_completion_audit_before_autonomous_ready",
            "preserve_research_only_non_promotable_outputs",
        ],
        "jobs": [
            {
                "job_id": universe_job_id,
                "kind": "universe_refresh",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "source": "public_api",
                    "public_info_url": config.public_info_url,
                    "public_info_timeout": config.public_info_timeout,
                    "asof_date": config.asof_date.isoformat(),
                    "min_day_notional_usd": config.min_day_notional_usd,
                    "mode": "current_labeled_sandbox",
                },
            },
            {
                "job_id": candles_job_id,
                "kind": "recent_candle_bootstrap",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "source": "public_api",
                    "public_info_url": config.public_info_url,
                    "public_info_timeout": config.public_info_timeout,
                    "venue": config.venue,
                    "instrument_id": config.instrument_id,
                    "coin": config.coin,
                    "timeframe": config.timeframe,
                    "date": config.start_ts.date().isoformat(),
                    "run_id": f"{run_id}-public-candles",
                    "start_ts": start,
                    "end_ts": end,
                    "derive_timeframes": [],
                    "create_snapshot": True,
                    "max_public_info_pages": config.max_public_info_pages,
                    "max_candles_per_public_page": config.max_candles_per_public_page,
                },
            },
            {
                "job_id": coverage_job_id,
                "kind": "coverage_audit",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "venue": config.venue,
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
                    "max_files": 10,
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
                    "family": "bars",
                    "timeframe": config.timeframe,
                    "start_ts": start,
                    "end_ts": end,
                    "asof_date": config.asof_date.isoformat(),
                    "evidence_mode": config.evidence_mode,
                    "requested_fields": _public_requested_fields(),
                },
            },
            {
                "job_id": backtest_job_id,
                "kind": "vectorized_backtest",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "output_root": str(backtest_output_root),
                    "run_id": f"{run_id}-backtest",
                    "experiment_id": f"{run_id}-public-diagnostic-cycle",
                    "trial_index": 0,
                    "agent_or_user": config.created_by_id,
                    "venue": config.venue,
                    "instrument_id": config.instrument_id,
                    "timeframe": config.timeframe,
                    "start_ts": start,
                    "end_ts": end,
                    "asof_date": config.asof_date.isoformat(),
                    "evidence_mode": config.evidence_mode,
                    "universe_mode": "current",
                    "cost_model": _public_cost_model(),
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
                        "public API diagnostic cycle row; current-universe/recent-window "
                        "output is not accepted research evidence"
                    ),
                },
            },
            {
                "job_id": lead_job_id,
                "kind": "lead_book_upsert",
                "input_spec": {
                    "lead_book_path": str(lead_book_path),
                    "source_type": "autopilot_public_api_diagnostic_ledger",
                    "strategy_family": "public_api_diagnostic_mean_reversion",
                    "economic_thesis": (
                        "Public API diagnostic row proves durable public intake wiring only; "
                        "it is not a strategy-quality or readiness claim."
                    ),
                    "created_by_id": config.created_by_id,
                    "instrument_scope": [config.instrument_id],
                    "venue_scope": config.venue,
                    "universe_scope": "current_public_api_diagnostic",
                    "data_window_start": start,
                    "data_window_end": end,
                    "data_source": "public_api_diagnostic_archive",
                    "roi_observed": 0.0,
                    "roi_projected": 0.0,
                    "roi_projection_assumptions": (
                        "projection is disabled for public diagnostic wiring proof"
                    ),
                    "roi_projection_confidence": "low",
                    "why_interesting": (
                        "Durable worker chain can be run against public Hyperliquid "
                        "universe and candle APIs, then audited as diagnostic evidence."
                    ),
                    "trade_count_summary": {"avg_trades_per_month": 0.0, "total_trades": 0},
                    "monthly_stability_summary": {
                        "usable_months": 0,
                        "losing_months_12m": 0,
                        "positive_months_12m": 0,
                    },
                    "pnl_concentration_summary": {
                        "top_2_trades_profit_share": 0.0,
                        "best_month_profit_share": 0.0,
                    },
                    "known_blockers": list(_expected_blockers()),
                    "missing_evidence": [
                        "historical_asof_universe_snapshot",
                        "accepted_historical_candle_coverage",
                        "independent_completion_audit",
                        "authoritative_full_suite_validation",
                    ],
                    "required_next_validation": [
                        "replace_public_current_universe_with_historical_asof_universe",
                        "prove_coverage_against_accepted_archive_snapshot",
                        "independent_completion_audit",
                        "authoritative_full_suite_validation",
                    ],
                    "notes": (
                        "Non-promotable public API diagnostic cycle; do not use as "
                        "accepted research, candidate-pack, paper/live, sizing, order, "
                        "runtime, or promotion evidence."
                    ),
                },
            },
        ],
        "bindings": [
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
                "source_job_id": candles_job_id,
                "target_job_id": coverage_job_id,
                "target_input_path": "archive_snapshot_id",
                "source_ref_prefix": "archive_snapshot_id=",
            },
            {
                "source_job_id": candles_job_id,
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
        ],
    }


def _public_strategy_spec(config: AutopilotPublicCandleCycleConfig) -> dict[str, Any]:
    payload = json.loads(json.dumps(example_strategy_payloads()["hl_mean_reversion_v1"]))
    payload["strategy_id"] = "hl_public_diagnostic_mean_reversion_v1"
    payload["inputs"]["timeframe"] = config.timeframe
    payload["inputs"]["fields"] = ["close", "volume"]
    payload["logic"]["lookback_bars"] = 2
    payload["logic"]["entry_threshold"] = 0.1
    payload["logic"]["exit_threshold"] = 0.0
    payload["logic"]["filters"] = {"min_volume": 1000}
    payload["risk"]["rebalance"] = config.timeframe
    payload["validation"]["min_backtest_months"] = 6
    payload["validation"]["evidence_mode"] = "sandbox_diagnostic"
    payload["validation"]["universe_mode"] = "current"
    validation = validate_strategy_spec(payload)
    if not validation.ok:
        raise ValueError("public diagnostic strategy spec failed validation: " + "; ".join(validation.errors))
    return {
        key: value
        for key, value in payload.items()
        if key not in _JOB_INPUT_BOUNDARY_KEYS
    }


def _public_requested_fields() -> list[str]:
    return ["ts", "instrument_id", "close", "volume", "open"]


def _public_cost_model() -> dict[str, Any]:
    return {
        "cost_model_id": "public_diagnostic_conservative_hyperliquid_taker_v1",
        "fee_side": "taker",
        "fee_bps": 6.0,
        "spread_bps": 2.0,
        "slippage_bps": 3.0,
        "impact_bps": 1.0,
        "max_volume_participation": 0.05,
        "slippage_model_id": "volume_participation_v1",
        "impact_model_id": "impact_v1",
        "funding_required": False,
        "funding_source": "public_candle_diagnostic_no_funding",
        "funding_missing_policy": "explicit_zero",
        "liquidity_stress_required": True,
        "ranking_allowed": True,
        "queue_model_documented": False,
        "stress_scenarios": ["base", "stress_2x", "stress_3x"],
    }


def _expected_blockers() -> tuple[str, ...]:
    return (
        "public_api_current_universe_not_historical_asof",
        "public_api_recent_window_non_evidence",
        "accepted_historical_coverage_proof_required",
        "independent_completion_audit_required",
        "authoritative_full_suite_validation_required",
    )
