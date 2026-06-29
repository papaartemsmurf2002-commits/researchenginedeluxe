# V2-AUDIT-ID: V2-AUD-BTENG-081
# V2-CONTRACTS: docs/contracts/backtest_engine_contract.md, docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, archive_backed_benchmark, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_backtest_engine
"""Archive-backed reference/fast benchmark reports for v2 backtests."""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.archive_inventory import ArtifactMode
from tradingbotsuite.v2.backtest_data import (
    BacktestDataRequest,
    BacktestDataService,
    BacktestEvidenceMode,
)
from tradingbotsuite.v2.backtest_engine.artifacts import BacktestRunConfig, EngineLane
from tradingbotsuite.v2.backtest_engine.engine import run_vectorized_backtest
from tradingbotsuite.v2.backtest_engine.fast_lane import (
    FastLaneParityStatus,
    FastLaneParityReport,
    audit_fast_lane_parity,
)
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.costs.models import CostModelConfig
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.strategy_specs import (
    StrategySpec,
    compile_signal_frame,
    parse_strategy_spec,
)


class BenchmarkTier(str, Enum):
    SMOKE = "smoke"
    PANEL = "panel"
    SWEEP = "sweep"


_REQUIRED_BENCHMARK_OBSERVATIONS: frozenset[str] = frozenset(
    {
        "reference_runtime_seconds",
        "fast_runtime_seconds",
        "reference_data_load_seconds",
        "fast_data_load_seconds",
        "reference_artifact_write_seconds",
        "fast_artifact_write_seconds",
        "reference_memory_peak_bytes",
        "fast_memory_peak_bytes",
    }
)


class BacktestBenchmarkConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    benchmark_id: str = "archive_fast_lane_benchmark"
    benchmark_tier: BenchmarkTier = BenchmarkTier.SMOKE
    archive_root: str = Field(min_length=1)
    output_root: str = Field(min_length=1)
    report_path: str | None = None
    strategy_spec: dict[str, Any]
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    instrument_ids: tuple[str, ...] = ()
    family: str = "bars"
    timeframe: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    warmup_start_ts: datetime | None = None
    requested_fields: tuple[str, ...] = ()
    evidence_mode: BacktestEvidenceMode = BacktestEvidenceMode.ACCEPTED_RESEARCH
    asof_date: date | None = None
    include_lockbox: bool = False
    artifact_mode: ArtifactMode = ArtifactMode.METRICS_ONLY
    tolerance_abs: float = Field(default=1e-12, ge=0.0)
    claim_speedup: bool = False
    agent_or_user: str = "benchmark"
    git_sha: str = "unknown"
    environment_hash: str | None = Field(default=None, min_length=64, max_length=64)
    cost_model: CostModelConfig = Field(default_factory=CostModelConfig)
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

    @model_validator(mode="before")
    @classmethod
    def _normalize_instrument_ids(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        payload = dict(data)
        primary = str(payload.get("instrument_id", "")).strip()
        raw = payload.get("instrument_ids")
        if raw is None or raw == ():
            if primary:
                payload["instrument_ids"] = (primary,)
            return payload
        if isinstance(raw, str):
            raise ValueError("instrument_ids must be a list of instrument ids")
        normalized: list[str] = []
        for item in raw:
            text = str(item).strip()
            if text and text not in normalized:
                normalized.append(text)
        if primary and primary not in normalized:
            normalized.insert(0, primary)
        payload["instrument_ids"] = tuple(normalized)
        return payload

    @field_validator("start_ts", "end_ts", "warmup_start_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_config(self) -> "BacktestBenchmarkConfig":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if not self.instrument_ids:
            raise ValueError("instrument_ids must not be empty")
        if self.instrument_id != self.instrument_ids[0]:
            raise ValueError("instrument_id must match first instrument_ids entry")
        if self.benchmark_tier in {BenchmarkTier.PANEL, BenchmarkTier.SWEEP} and len(self.instrument_ids) < 2:
            raise ValueError(f"{self.benchmark_tier.value} benchmark tier requires at least two instruments")
        if self.benchmark_tier == BenchmarkTier.SWEEP and _window_days(self.start_ts, self.end_ts) < 30.0:
            raise ValueError("sweep benchmark tier requires a window of at least 30 days")
        require_research_boundary(self, context="backtest benchmark config")
        return self


class BacktestBenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "backtest_fast_lane_benchmark_report_v1"
    benchmark_report_id: str = Field(min_length=64, max_length=64)
    benchmark_id: str = Field(min_length=1)
    benchmark_tier: BenchmarkTier = BenchmarkTier.SMOKE
    strategy_id: str = Field(min_length=1)
    strategy_spec_hash: str = Field(min_length=64, max_length=64)
    artifact_mode: ArtifactMode
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    data_manifest_id: str = Field(min_length=64, max_length=64)
    data_manifest_hash: str = Field(min_length=64, max_length=64)
    row_count: int = Field(ge=0)
    reported_row_count: int = Field(ge=0)
    instrument_ids: tuple[str, ...] = ()
    instrument_count: int = Field(ge=1)
    start_ts: datetime
    end_ts: datetime
    benchmark_window_days: float = Field(gt=0.0)
    benchmark_scope: dict[str, Any] = Field(default_factory=dict)
    reference_run_id: str = Field(min_length=1)
    fast_run_id: str = Field(min_length=1)
    reference_run_manifest_ref: str = Field(min_length=1)
    fast_run_manifest_ref: str = Field(min_length=1)
    reference_run_manifest_sha256: str = Field(min_length=64, max_length=64)
    fast_run_manifest_sha256: str = Field(min_length=64, max_length=64)
    parity_report: FastLaneParityReport
    benchmark_observations: dict[str, float] = Field(default_factory=dict)
    measured_speedup_ratio: float | None = Field(default=None, ge=0.0)
    speedup_claimed: bool = False
    report_path: str | None = None
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

    @model_validator(mode="after")
    def _validate_report(self) -> "BacktestBenchmarkReport":
        if self.report_type != "backtest_fast_lane_benchmark_report_v1":
            raise ValueError("unexpected benchmark report type")
        if self.speedup_claimed and self.measured_speedup_ratio is None:
            raise ValueError("speedup claims require measured speedup evidence")
        if self.speedup_claimed and self.parity_report.status != FastLaneParityStatus.PASS:
            raise ValueError("speedup claims require passing reference/fast parity evidence")
        if any(value < 0.0 for value in self.benchmark_observations.values()):
            raise ValueError("benchmark observations must be non-negative")
        if self.instrument_count != len(self.instrument_ids):
            raise ValueError("instrument_count must match instrument_ids")
        if self.benchmark_tier in {BenchmarkTier.PANEL, BenchmarkTier.SWEEP} and self.instrument_count < 2:
            raise ValueError(f"{self.benchmark_tier.value} benchmark reports require at least two instruments")
        if self.benchmark_tier == BenchmarkTier.SWEEP and self.benchmark_window_days < 30.0:
            raise ValueError("sweep benchmark reports require a window of at least 30 days")
        missing = sorted(_REQUIRED_BENCHMARK_OBSERVATIONS - set(self.benchmark_observations))
        if missing:
            raise ValueError("benchmark report missing required observations: " + ",".join(missing))
        require_research_boundary(self, context="backtest benchmark report")
        return self


def run_archive_backtest_benchmark(
    config: BacktestBenchmarkConfig | Mapping[str, Any],
) -> BacktestBenchmarkReport:
    parsed = (
        config if isinstance(config, BacktestBenchmarkConfig) else BacktestBenchmarkConfig.model_validate(config)
    )
    strategy_spec = parse_strategy_spec(parsed.strategy_spec)
    requested_fields = parsed.requested_fields or _requested_fields_for_strategy(
        strategy_spec,
        cost_model=parsed.cost_model,
    )
    data_request = BacktestDataRequest(
        archive_root=parsed.archive_root,
        archive_snapshot_id=parsed.archive_snapshot_id,
        universe_snapshot_id=parsed.universe_snapshot_id,
        venue=parsed.venue,
        instrument_id=parsed.instrument_id,
        instrument_ids=parsed.instrument_ids,
        family=parsed.family,
        timeframe=parsed.timeframe,
        start_ts=parsed.start_ts,
        end_ts=parsed.end_ts,
        warmup_start_ts=parsed.warmup_start_ts,
        requested_fields=requested_fields,
        evidence_mode=parsed.evidence_mode,
        exclude_lockbox=not parsed.include_lockbox,
    )
    data_service = BacktestDataService(parsed.archive_root)
    row_load_start = time.perf_counter()
    row_slice = data_service.load_panel(
        data_request,
        asof_date=parsed.asof_date,
        write_manifest=False,
    )
    row_data_load_seconds = max(0.0, time.perf_counter() - row_load_start)
    columnar_load_start = time.perf_counter()
    columnar_slice = data_service.load_panel_columnar(
        data_request,
        asof_date=parsed.asof_date,
        write_manifest=False,
    )
    columnar_data_load_seconds = max(0.0, time.perf_counter() - columnar_load_start)
    row_panel = _json_safe_rows(row_slice.rows)
    signal_compile_start = time.perf_counter()
    signal_frame = compile_signal_frame(strategy_spec, row_panel)
    signal_compile_seconds = max(0.0, time.perf_counter() - signal_compile_start)
    data_manifest = row_slice.data_manifest.model_dump(mode="json")
    data_manifest_hash = canonical_json_hash(data_manifest)
    output_root = Path(parsed.output_root)
    benchmark_run_root = output_root / parsed.benchmark_id
    reference_config = _run_config(
        parsed,
        strategy_spec=strategy_spec,
        data_manifest=data_manifest,
        engine_lane=EngineLane.VECTORIZED,
        output_root=benchmark_run_root,
        run_id=f"{parsed.benchmark_id}-reference",
        benchmark_observations={
            "data_load_seconds": row_data_load_seconds,
            "signal_compile_seconds": signal_compile_seconds,
        },
    )
    fast_config = _run_config(
        parsed,
        strategy_spec=strategy_spec,
        data_manifest=data_manifest,
        engine_lane=EngineLane.FAST_VECTORIZED,
        output_root=benchmark_run_root,
        run_id=f"{parsed.benchmark_id}-fast",
        benchmark_observations={
            "data_load_seconds": columnar_data_load_seconds,
            "signal_compile_seconds": signal_compile_seconds,
        },
    )
    reference_result = run_vectorized_backtest(
        config=reference_config,
        strategy_spec=strategy_spec,
        panel_rows=row_panel,
        signal_frame=signal_frame,
    )
    fast_result = run_vectorized_backtest(
        config=fast_config,
        strategy_spec=strategy_spec,
        panel_table=columnar_slice.table,
        signal_frame=signal_frame,
    )
    parity_report = audit_fast_lane_parity(
        reference_manifest=reference_result.manifest,
        fast_manifest=fast_result.manifest,
        tolerance_abs=parsed.tolerance_abs,
        claim_speedup=parsed.claim_speedup,
    )
    benchmark_observations = _benchmark_observations(
        reference_result.manifest.benchmark_observations,
        fast_result.manifest.benchmark_observations,
        parity_report.benchmark_observations,
    )
    measured_speedup = benchmark_observations.get("speedup_ratio")
    reference_manifest_path = Path(reference_result.run_dir) / "run_manifest.json"
    fast_manifest_path = Path(fast_result.run_dir) / "run_manifest.json"
    payload = {
        "benchmark_id": parsed.benchmark_id,
        "benchmark_tier": parsed.benchmark_tier,
        "strategy_id": strategy_spec.strategy_id,
        "strategy_spec_hash": strategy_spec.spec_hash,
        "artifact_mode": parsed.artifact_mode,
        "archive_snapshot_id": row_slice.archive_snapshot_id,
        "universe_snapshot_id": row_slice.universe_snapshot_id,
        "data_manifest_id": row_slice.data_manifest.data_manifest_id,
        "data_manifest_hash": data_manifest_hash,
        "row_count": row_slice.data_manifest.row_count,
        "reported_row_count": row_slice.data_manifest.reported_row_count,
        "instrument_ids": row_slice.data_manifest.instrument_ids,
        "instrument_count": len(row_slice.data_manifest.instrument_ids),
        "start_ts": row_slice.data_manifest.start_ts,
        "end_ts": row_slice.data_manifest.end_ts,
        "benchmark_window_days": _window_days(parsed.start_ts, parsed.end_ts),
        "benchmark_scope": _benchmark_scope(
            parsed,
            row_count=row_slice.data_manifest.row_count,
            reported_row_count=row_slice.data_manifest.reported_row_count,
        ),
        "reference_run_id": reference_result.manifest.run_id,
        "fast_run_id": fast_result.manifest.run_id,
        "reference_run_manifest_ref": str(reference_manifest_path),
        "fast_run_manifest_ref": str(fast_manifest_path),
        "reference_run_manifest_sha256": file_sha256(reference_manifest_path),
        "fast_run_manifest_sha256": file_sha256(fast_manifest_path),
        "parity_report": parity_report,
        "benchmark_observations": benchmark_observations,
        "measured_speedup_ratio": measured_speedup,
        "speedup_claimed": parsed.claim_speedup,
        "report_path": _report_path(parsed),
    }
    report = BacktestBenchmarkReport(
        **payload,
        benchmark_report_id=_benchmark_report_id(payload),
    )
    if report.report_path is not None:
        _write_json(Path(report.report_path), report.model_dump(mode="json"))
    return report


def _run_config(
    config: BacktestBenchmarkConfig,
    *,
    strategy_spec: StrategySpec,
    data_manifest: dict[str, Any],
    engine_lane: EngineLane,
    output_root: Path,
    run_id: str,
    benchmark_observations: dict[str, float],
) -> BacktestRunConfig:
    validation_payload = {
        "validation_config": data_manifest.get("validation_config", {}),
        "evidence_mode": config.evidence_mode.value,
        "exclude_lockbox": not config.include_lockbox,
        "requested_window": {
            "start_ts": utc_isoformat(config.start_ts),
            "end_ts": utc_isoformat(config.end_ts),
            "warmup_start_ts": None
            if config.warmup_start_ts is None
            else utc_isoformat(config.warmup_start_ts),
        },
    }
    cost_model = (
        config.cost_model.model_copy(update={"spread_observation_policy": "accepted_research_strict"})
        if config.evidence_mode == BacktestEvidenceMode.ACCEPTED_RESEARCH
        else config.cost_model
    )
    cost_payload = {
        "cost_model_config": cost_model.model_dump(mode="json"),
        "cost_stress_scenarios": tuple(str(item.value) for item in cost_model.stress_scenarios),
    }
    return BacktestRunConfig(
        run_id=run_id,
        experiment_id=config.benchmark_id,
        trial_index=0 if engine_lane == EngineLane.VECTORIZED else 1,
        agent_or_user=config.agent_or_user,
        output_root=str(output_root),
        archive_snapshot_id=config.archive_snapshot_id,
        universe_snapshot_id=config.universe_snapshot_id,
        data_manifest_id=str(data_manifest["data_manifest_id"]),
        data_manifest_hash=canonical_json_hash(data_manifest),
        validation_manifest_hash=canonical_json_hash(validation_payload),
        cost_manifest_hash=canonical_json_hash(cost_payload),
        validation_policy_id="v2_default_validation_v1",
        cost_model_id=cost_model.cost_model_id,
        cost_model=cost_model,
        engine_lane=engine_lane,
        artifact_mode=config.artifact_mode,
        benchmark_enabled=True,
        benchmark_observations=benchmark_observations,
        speedup_claimed=False,
        lockbox_start=None
        if data_manifest.get("lockbox_start_ts") is None
        else ensure_utc(datetime.fromisoformat(str(data_manifest["lockbox_start_ts"]).replace("Z", "+00:00"))),
        lockbox_end=None
        if data_manifest.get("lockbox_end_ts") is None
        else ensure_utc(datetime.fromisoformat(str(data_manifest["lockbox_end_ts"]).replace("Z", "+00:00"))),
        data_coverage_min=float(data_manifest["coverage_min"]),
        universe_mode="as_of",
        venue_scope=config.venue,
        git_sha=config.git_sha,
        environment_hash=config.environment_hash,
    )


def _requested_fields_for_strategy(
    strategy_spec: StrategySpec,
    *,
    cost_model: CostModelConfig,
) -> tuple[str, ...]:
    fields = ["ts", "instrument_id", *strategy_spec.inputs.fields]
    price_basis = strategy_spec.execution.price_basis.value
    if price_basis == "next_bar_open":
        fields.extend(["open", "close"])
    elif price_basis == "close":
        fields.append("close")
    elif price_basis == "mark":
        fields.append("mark_price")
    elif price_basis == "oracle":
        fields.append("oracle_price")
    fields.append("volume")
    if cost_model.funding_required or cost_model.funding_missing_policy == "fail":
        fields.extend(["funding", "funding_rate"])
    if "max_spread" in strategy_spec.logic.filters:
        fields.append("spread")
    return tuple(dict.fromkeys(fields))


def _benchmark_observations(
    reference: Mapping[str, float],
    fast: Mapping[str, float],
    parity: Mapping[str, float],
) -> dict[str, float]:
    observations = dict(parity)
    for key, value in reference.items():
        observations[f"reference_{key}"] = float(value)
    for key, value in fast.items():
        observations[f"fast_{key}"] = float(value)
    reference_runtime = reference.get("reference_runtime_seconds")
    fast_runtime = fast.get("fast_runtime_seconds")
    if reference_runtime is not None and fast_runtime is not None and fast_runtime > 0.0:
        observations["speedup_ratio"] = float(reference_runtime) / float(fast_runtime)
    return dict(sorted(observations.items()))


def _report_path(config: BacktestBenchmarkConfig) -> str | None:
    if config.report_path:
        return str(Path(config.report_path))
    return str(Path(config.output_root) / config.benchmark_id / "benchmark_report.json")


def _benchmark_report_id(payload: Mapping[str, Any]) -> str:
    identity = {
        "schema_version": V2_SCHEMA_VERSION,
        "report_type": "backtest_fast_lane_benchmark_report_v1",
        "benchmark_id": payload["benchmark_id"],
        "benchmark_tier": str(payload["benchmark_tier"].value if hasattr(payload["benchmark_tier"], "value") else payload["benchmark_tier"]),
        "strategy_spec_hash": payload["strategy_spec_hash"],
        "artifact_mode": str(payload["artifact_mode"].value if hasattr(payload["artifact_mode"], "value") else payload["artifact_mode"]),
        "archive_snapshot_id": payload["archive_snapshot_id"],
        "universe_snapshot_id": payload["universe_snapshot_id"],
        "data_manifest_hash": payload["data_manifest_hash"],
        "reference_run_id": payload["reference_run_id"],
        "fast_run_id": payload["fast_run_id"],
        "parity_report_id": payload["parity_report"].parity_report_id
        if isinstance(payload["parity_report"], FastLaneParityReport)
        else payload["parity_report"]["parity_report_id"],
    }
    return canonical_json_hash(identity)


def _benchmark_scope(
    config: BacktestBenchmarkConfig,
    *,
    row_count: int,
    reported_row_count: int,
) -> dict[str, Any]:
    return {
        "tier": config.benchmark_tier.value,
        "instrument_count": len(config.instrument_ids),
        "requested_instrument_ids": config.instrument_ids,
        "window_days": _window_days(config.start_ts, config.end_ts),
        "artifact_mode": config.artifact_mode.value,
        "reference_lane": EngineLane.VECTORIZED.value,
        "fast_lane": EngineLane.FAST_VECTORIZED.value,
        "parity_required": True,
        "reference_engine_authority": True,
        "speedup_claim_policy": "measured_speedup_ratio_required",
        "required_observation_keys": tuple(sorted(_REQUIRED_BENCHMARK_OBSERVATIONS)),
        "row_count": int(row_count),
        "reported_row_count": int(reported_row_count),
    }


def _window_days(start_ts: datetime, end_ts: datetime) -> float:
    return max(0.0, (ensure_utc(end_ts) - ensure_utc(start_ts)).total_seconds() / 86_400.0)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(
        json.dumps(dict(payload), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def _json_safe_rows(rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        converted = dict(row)
        if isinstance(converted.get("ts"), datetime):
            converted["ts"] = utc_isoformat(converted["ts"])
        output.append(converted)
    return output
