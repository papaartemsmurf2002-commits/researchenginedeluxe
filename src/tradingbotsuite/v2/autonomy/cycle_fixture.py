# V2-AUDIT-ID: V2-AUD-AUTONOMY-008
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, sandbox_diagnostic_fixture, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_autonomy
"""Fixture-backed bounded autopilot cycle spec writer."""

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


FIXTURE_CYCLE_CONFIG_SCHEMA_VERSION = "autopilot_fixture_cycle_config_v1"
FIXTURE_CYCLE_RESULT_SCHEMA_VERSION = "autopilot_fixture_cycle_result_v1"
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


class AutopilotFixtureCycleConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = FIXTURE_CYCLE_CONFIG_SCHEMA_VERSION
    output_root: str = Field(min_length=1)
    run_id: str = Field(default="autopilot-fixture-cycle", pattern=r"^[A-Za-z0-9_.-]+$")
    venue: str = "hyperliquid"
    instrument_id: str = "hyperliquid:perp:BTC"
    coin: str = "BTC"
    timeframe: str = "1d"
    start_ts: datetime = Field(default_factory=lambda: datetime(2024, 1, 1, tzinfo=UTC))
    end_ts: datetime = Field(default_factory=lambda: datetime(2024, 8, 1, tzinfo=UTC))
    asof_date: date = date(2024, 1, 1)
    min_day_notional_usd: int = Field(default=5_000_000, ge=1)
    coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
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
            raise ValueError("fixture cycle evidence_mode must be sandbox_diagnostic")
        return normalized

    @model_validator(mode="after")
    def _validate_fixture_cycle(self) -> "AutopilotFixtureCycleConfig":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if self.timeframe != "1d":
            raise ValueError("fixture cycle currently supports timeframe=1d only")
        require_research_boundary(self, context="autopilot fixture cycle config")
        return self


class AutopilotFixtureCycleSpecResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = FIXTURE_CYCLE_RESULT_SCHEMA_VERSION
    run_id: str = Field(min_length=1)
    cycle_spec_path: str = Field(min_length=1)
    fixture_root: str = Field(min_length=1)
    universe_payload_file: str = Field(min_length=1)
    candle_records_file: str = Field(min_length=1)
    archive_root: str = Field(min_length=1)
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
    def _validate_result(self) -> "AutopilotFixtureCycleSpecResult":
        require_research_boundary(self, context="autopilot fixture cycle result")
        return self


def write_autopilot_fixture_cycle_spec(
    config: AutopilotFixtureCycleConfig | dict[str, Any],
) -> AutopilotFixtureCycleSpecResult:
    parsed = (
        config
        if isinstance(config, AutopilotFixtureCycleConfig)
        else AutopilotFixtureCycleConfig.model_validate(config)
    )
    root = Path(parsed.output_root).resolve(strict=False)
    run_root = (root / parsed.run_id).resolve(strict=False)
    try:
        run_root.relative_to(root)
    except ValueError as exc:
        raise ValueError("fixture cycle output root escapes requested output_root") from exc

    fixture_root = run_root / "fixtures"
    archive_root = run_root / "archive"
    backtest_output_root = run_root / "backtests"
    ledger_path = run_root / "ledger" / "experiment_ledger.parquet"
    lead_book_path = run_root / "lead_book" / "lead_book.parquet"
    plan_output_root = run_root / "plans"
    job_store_path = run_root / "jobs.sqlite"
    fixture_root.mkdir(parents=True, exist_ok=True)

    universe_payload_file = fixture_root / "hyperliquid_universe_payload.json"
    candle_records_file = fixture_root / "daily_candles.jsonl"
    universe_payload_file.write_text(
        json.dumps(_universe_payload(parsed), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    candle_records_file.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in _daily_candle_rows(parsed)),
        encoding="utf-8",
    )

    cycle_spec = _cycle_spec_payload(
        parsed,
        archive_root=archive_root,
        backtest_output_root=backtest_output_root,
        fixture_root=fixture_root,
        universe_payload_file=universe_payload_file,
        candle_records_file=candle_records_file,
        ledger_path=ledger_path,
        lead_book_path=lead_book_path,
    )
    validated = AutopilotCyclePlanConfig.model_validate(cycle_spec)
    cycle_spec_path = run_root / "cycle_spec.json"
    cycle_spec_path.write_text(
        json.dumps(validated.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return AutopilotFixtureCycleSpecResult(
        run_id=parsed.run_id,
        cycle_spec_path=str(cycle_spec_path),
        fixture_root=str(fixture_root),
        universe_payload_file=str(universe_payload_file),
        candle_records_file=str(candle_records_file),
        archive_root=str(archive_root),
        backtest_output_root=str(backtest_output_root),
        ledger_path=str(ledger_path),
        lead_book_path=str(lead_book_path),
        suggested_plan_output_root=str(plan_output_root),
        suggested_job_store_path=str(job_store_path),
        declared_job_count=len(validated.jobs),
        declared_binding_count=len(validated.bindings),
        expected_audit_blockers=(
            "sandbox_diagnostic_non_evidence",
            "fixture_cycle_non_evidence",
            "real_hyperliquid_archive_operation_required",
            "independent_completion_audit_required",
            "missing_evidence:real_hyperliquid_archive_operation",
            "missing_evidence:independent_completion_audit",
        ),
    )


def _cycle_spec_payload(
    config: AutopilotFixtureCycleConfig,
    *,
    archive_root: Path,
    backtest_output_root: Path,
    fixture_root: Path,
    universe_payload_file: Path,
    candle_records_file: Path,
    ledger_path: Path,
    lead_book_path: Path,
) -> dict[str, Any]:
    run_id = config.run_id
    universe_job_id = f"JOB-{run_id}-universe"
    candles_job_id = f"JOB-{run_id}-candles"
    coverage_job_id = f"JOB-{run_id}-coverage"
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
            "replace_fixture_inputs_with_real_hyperliquid_archive_operation",
            "run_independent_completion_audit_before_autonomous_ready",
            "preserve_research_only_non_promotable_outputs",
        ],
        "jobs": [
            {
                "job_id": universe_job_id,
                "kind": "universe_refresh",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "payload_file": str(universe_payload_file),
                    "asof_date": config.asof_date.isoformat(),
                    "min_day_notional_usd": config.min_day_notional_usd,
                    "mode": "as_of",
                },
            },
            {
                "job_id": candles_job_id,
                "kind": "recent_candle_bootstrap",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "trusted_source_root": str(fixture_root),
                    "records_file": candle_records_file.name,
                    "records_format": "jsonl",
                    "max_records_file_bytes": 5_000_000,
                    "venue": config.venue,
                    "instrument_id": config.instrument_id,
                    "timeframe": config.timeframe,
                    "date": config.start_ts.date().isoformat(),
                    "run_id": f"{run_id}-candles",
                    "start_ts": start,
                    "end_ts": end,
                    "derive_timeframes": [],
                    "create_snapshot": True,
                    "source_endpoint_or_subscription": "fixture/autopilot/daily_candles",
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
                "job_id": backtest_job_id,
                "kind": "vectorized_backtest",
                "input_spec": {
                    "archive_root": str(archive_root),
                    "output_root": str(backtest_output_root),
                    "run_id": f"{run_id}-backtest",
                    "experiment_id": f"{run_id}-fixture-cycle",
                    "trial_index": 0,
                    "agent_or_user": config.created_by_id,
                    "venue": config.venue,
                    "instrument_id": config.instrument_id,
                    "timeframe": config.timeframe,
                    "start_ts": start,
                    "end_ts": end,
                    "asof_date": config.asof_date.isoformat(),
                    "evidence_mode": config.evidence_mode,
                    "universe_mode": "as_of",
                    "strategy_spec": _fixture_strategy_spec(),
                    "cost_model": _fixture_cost_model(),
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
                    "notes": "autopilot fixture cycle sandbox diagnostic row; not accepted evidence",
                },
            },
            {
                "job_id": lead_job_id,
                "kind": "lead_book_upsert",
                "input_spec": {
                    "lead_book_path": str(lead_book_path),
                    "source_type": "autopilot_fixture_cycle_ledger",
                    "strategy_family": "fixture_mean_reversion",
                    "economic_thesis": "Fixture row proves worker-chain wiring only and is not a performance claim.",
                    "created_by_id": config.created_by_id,
                    "instrument_scope": [config.instrument_id],
                    "venue_scope": config.venue,
                    "universe_scope": "as_of_fixture",
                    "data_window_start": start,
                    "data_window_end": end,
                    "data_source": "generated_fixture_archive",
                    "roi_observed": 0.0,
                    "roi_projected": 0.0,
                    "roi_projection_assumptions": "projection is disabled for fixture-cycle wiring proof",
                    "roi_projection_confidence": "low",
                    "why_interesting": "Durable worker chain completed from fixture universe through archive, backtest, ledger, and Lead Book.",
                    "trade_count_summary": {"avg_trades_per_month": 0.0, "total_trades": 0},
                    "monthly_stability_summary": {
                        "usable_months": 7,
                        "losing_months_12m": 0,
                        "positive_months_12m": 0,
                    },
                    "pnl_concentration_summary": {
                        "top_2_trades_profit_share": 0.0,
                        "best_month_profit_share": 0.0,
                    },
                    "known_blockers": [
                        "fixture_cycle_non_evidence",
                        "real_hyperliquid_archive_operation_required",
                        "independent_completion_audit_required",
                    ],
                    "missing_evidence": [
                        "real_hyperliquid_archive_operation",
                        "independent_completion_audit",
                    ],
                    "required_next_validation": [
                        "replace_fixture_inputs_with_real_archive",
                        "independent_completion_audit",
                    ],
                    "notes": "Non-promotable sandbox diagnostic fixture cycle; do not use as research performance evidence.",
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
                "target_job_id": backtest_job_id,
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
                "target_job_id": backtest_job_id,
                "target_input_path": "archive_snapshot_id",
                "source_ref_prefix": "archive_snapshot_id=",
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


def _fixture_strategy_spec() -> dict[str, Any]:
    payload = json.loads(json.dumps(example_strategy_payloads()["hl_mean_reversion_v1"]))
    payload["strategy_id"] = "hl_fixture_mean_reversion_v1"
    payload["inputs"]["timeframe"] = "1d"
    payload["inputs"]["fields"] = ["close", "volume"]
    payload["logic"]["lookback_bars"] = 2
    payload["logic"]["entry_threshold"] = 0.1
    payload["logic"]["exit_threshold"] = 0.0
    payload["logic"]["filters"] = {"min_volume": 1000}
    payload["risk"]["rebalance"] = "1d"
    payload["validation"]["min_backtest_months"] = 6
    payload["validation"]["evidence_mode"] = "sandbox_diagnostic"
    validation = validate_strategy_spec(payload)
    if not validation.ok:
        raise ValueError("fixture strategy spec failed validation: " + "; ".join(validation.errors))
    return {
        key: value
        for key, value in payload.items()
        if key not in _JOB_INPUT_BOUNDARY_KEYS
    }


def _fixture_cost_model() -> dict[str, Any]:
    return {
        "cost_model_id": "fixture_explicit_zero_funding_v1",
        "fee_side": "taker",
        "fee_bps": 6.0,
        "spread_bps": 2.0,
        "slippage_bps": 3.0,
        "impact_bps": 1.0,
        "max_volume_participation": 0.05,
        "slippage_model_id": "volume_participation_v1",
        "impact_model_id": "impact_v1",
        "funding_required": False,
        "funding_source": "fixture_candle_archive_no_funding",
        "funding_missing_policy": "explicit_zero",
        "liquidity_stress_required": True,
        "ranking_allowed": True,
        "queue_model_documented": False,
        "stress_scenarios": ["base", "stress_2x", "stress_3x"],
    }


def _universe_payload(config: AutopilotFixtureCycleConfig) -> list[Any]:
    coin = config.coin
    return [
        {
            "universe": [
                {"name": coin, "szDecimals": 5, "maxLeverage": 50},
                {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
            ]
        },
        [
            {
                "dayNtlVlm": str(max(config.min_day_notional_usd * 20, 100_000_000)),
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


def _daily_candle_rows(config: AutopilotFixtureCycleConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current = config.start_ts
    index = 0
    while current < config.end_ts:
        close = 100.0 + (0.08 * index) + ((index % 9) * 0.12)
        if index % 17 == 0:
            close -= 0.75
        open_price = close - 0.2
        rows.append(
            {
                "venue": config.venue,
                "instrument_id": config.instrument_id,
                "coin": config.coin,
                "timeframe": config.timeframe,
                "ts": utc_isoformat(current),
                "end_ts": utc_isoformat(current + timedelta(days=1)),
                "open": round(open_price, 8),
                "high": round(max(open_price, close) + 0.75, 8),
                "low": round(min(open_price, close) - 0.75, 8),
                "close": round(close, 8),
                "volume": 100_000.0 + (index * 10.0),
                "trade_count": 100 + index,
            }
        )
        current += timedelta(days=1)
        index += 1
    return rows
