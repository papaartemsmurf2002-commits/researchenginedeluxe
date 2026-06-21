# V2-AUDIT-ID: V2-AUD-BTENG-006
# V2-CONTRACTS: docs/contracts/backtest_engine_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_vectorized_backtest, archive_snapshot_reads, no_live_imports
# V2-OWNER: v2_backtest_engine
"""Durable worker job handlers for v2 backtest engines."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.backtest_data import (
    BacktestDataRequest,
    BacktestDataService,
    BacktestEvidenceMode,
)
from tradingbotsuite.v2.backtest_engine.artifacts import BacktestRunConfig, EngineLane
from tradingbotsuite.v2.backtest_engine.engine import run_vectorized_backtest
from tradingbotsuite.v2.config.time import utc_isoformat
from tradingbotsuite.v2.costs.models import CostModelConfig
from tradingbotsuite.v2.strategy_specs import (
    StrategySpec,
    parse_strategy_spec,
    validate_strategy_spec,
)
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobRecord, WorkerRunResult


def run_backtest_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    if job.kind not in {WorkerJobKind.BACKTEST, WorkerJobKind.VECTORIZED_BACKTEST}:
        raise ValueError(f"unsupported backtest job kind: {job.kind.value}")
    return _run_vectorized_backtest_job(job=job, store=store, worker_id=worker_id)


def _run_vectorized_backtest_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = dict(job.input_spec)
    requested_lane = str(spec.get("engine_lane", EngineLane.VECTORIZED.value))
    if requested_lane != EngineLane.VECTORIZED.value:
        raise ValueError(f"unsupported durable backtest engine_lane: {requested_lane}")
    if "strategy_spec_file" in spec:
        raise ValueError("strategy_spec_file intake is not supported for durable backtest jobs")
    strategy_payload = spec.get("strategy_spec")
    if not isinstance(strategy_payload, Mapping):
        raise ValueError("vectorized backtest job spec requires inline strategy_spec object")

    validation = validate_strategy_spec(strategy_payload)
    if not validation.ok:
        raise ValueError("strategy_spec_validation_failed: " + "; ".join(validation.errors))
    strategy_spec = parse_strategy_spec(strategy_payload)
    cost_model = _cost_model(spec)
    data_request = _data_request(spec, strategy_spec=strategy_spec, cost_model=cost_model)
    asof_date = _optional_date(spec.get("asof_date"))
    data_slice = BacktestDataService(data_request.archive_root).load_panel(
        data_request,
        asof_date=asof_date,
        write_manifest=bool(spec.get("write_data_manifest", True)),
    )
    panel_rows = _json_safe_rows(data_slice.rows)
    run_config = _run_config(
        spec,
        job=job,
        data_request=data_request,
        strategy_spec=strategy_spec,
        cost_model=cost_model,
        data_manifest=data_slice.data_manifest.model_dump(mode="json"),
    )
    result = run_vectorized_backtest(
        config=run_config,
        strategy_spec=strategy_spec,
        panel_rows=panel_rows,
        params=dict(spec.get("params", {})),
    )
    run_manifest_path = Path(result.run_dir) / "run_manifest.json"
    output_refs = _output_refs(
        job=job,
        result_path=run_manifest_path,
        strategy_spec=strategy_spec,
        data_request=data_request,
        run_config=run_config,
        data_manifest_id=data_slice.data_manifest.data_manifest_id,
        coverage_report_id=data_slice.coverage_report_id,
        status=result.manifest.status.value,
        failure_reason=result.manifest.failure_reason,
        gross_return=None if result.metrics is None else result.metrics.gross_return,
        net_return=None if result.metrics is None else result.metrics.net_return,
    )
    archive_refs = (
        f"archive_snapshot_id={data_slice.archive_snapshot_id}",
        f"universe_snapshot_id={data_slice.universe_snapshot_id}",
        f"data_manifest_id={data_slice.data_manifest.data_manifest_id}",
        f"coverage_report_id={data_slice.coverage_report_id}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="vectorized_backtest_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _data_request(
    spec: Mapping[str, Any],
    *,
    strategy_spec: StrategySpec,
    cost_model: CostModelConfig,
) -> BacktestDataRequest:
    return BacktestDataRequest(
        archive_root=_required_str(spec, "archive_root"),
        archive_snapshot_id=_required_str(spec, "archive_snapshot_id"),
        universe_snapshot_id=_required_str(spec, "universe_snapshot_id"),
        venue=str(spec.get("venue") or strategy_spec.market_scope.venue),
        instrument_id=_required_str(spec, "instrument_id"),
        family=str(spec.get("family", "bars")),
        timeframe=str(spec.get("timeframe") or strategy_spec.inputs.timeframe),
        start_ts=_parse_datetime(_required_str(spec, "start_ts")),
        end_ts=_parse_datetime(_required_str(spec, "end_ts")),
        warmup_start_ts=_optional_datetime(spec.get("warmup_start_ts")),
        requested_fields=_requested_fields(spec, strategy_spec=strategy_spec, cost_model=cost_model),
        evidence_mode=BacktestEvidenceMode(str(spec.get("evidence_mode", BacktestEvidenceMode.ACCEPTED_RESEARCH.value))),
        exclude_lockbox=not bool(spec.get("include_lockbox", False)),
    )


def _run_config(
    spec: Mapping[str, Any],
    *,
    job: WorkerJobRecord,
    data_request: BacktestDataRequest,
    strategy_spec: StrategySpec,
    cost_model: CostModelConfig,
    data_manifest: dict[str, Any],
) -> BacktestRunConfig:
    validation_payload = {
        "validation_config": data_request.validation_config.model_dump(mode="json"),
        "evidence_mode": data_request.evidence_mode.value,
        "exclude_lockbox": data_request.exclude_lockbox,
        "requested_window": {
            "start_ts": utc_isoformat(data_request.start_ts),
            "end_ts": utc_isoformat(data_request.end_ts),
            "warmup_start_ts": None
            if data_request.warmup_start_ts is None
            else utc_isoformat(data_request.warmup_start_ts),
        },
    }
    cost_payload = {
        "cost_model_config": cost_model.model_dump(mode="json"),
        "cost_stress_scenarios": tuple(
            str(item.value if hasattr(item, "value") else item)
            for item in cost_model.stress_scenarios
        ),
    }
    return BacktestRunConfig(
        run_id=str(spec.get("run_id") or f"{job.job_id}-run"),
        experiment_id=str(spec.get("experiment_id", "worker-vectorized-backtest")),
        trial_index=int(spec.get("trial_index", 0)),
        agent_or_user=str(spec.get("agent_or_user", "worker")),
        output_root=_required_str(spec, "output_root"),
        archive_snapshot_id=data_request.archive_snapshot_id,
        universe_snapshot_id=data_request.universe_snapshot_id,
        data_manifest_id=str(data_manifest["data_manifest_id"]),
        data_manifest_hash=canonical_json_hash(data_manifest),
        validation_manifest_hash=canonical_json_hash(validation_payload),
        cost_manifest_hash=canonical_json_hash(cost_payload),
        validation_policy_id=data_request.validation_config.validation_policy_id,
        cost_model_id=cost_model.cost_model_id,
        cost_model=cost_model,
        engine_lane=EngineLane.VECTORIZED,
        lockbox_policy_id=data_request.validation_config.lockbox_policy.policy_id,
        lockbox_start=None if data_manifest.get("lockbox_start_ts") is None else _parse_datetime(str(data_manifest["lockbox_start_ts"])),
        lockbox_end=None if data_manifest.get("lockbox_end_ts") is None else _parse_datetime(str(data_manifest["lockbox_end_ts"])),
        data_coverage_min=float(data_manifest["coverage_min"]),
        universe_mode=str(spec.get("universe_mode", strategy_spec.validation.universe_mode.value)),
        venue_scope=data_request.venue,
        git_sha=str(spec.get("git_sha", "unknown")),
        environment_hash=spec.get("environment_hash"),
    )


def _cost_model(spec: Mapping[str, Any]) -> CostModelConfig:
    payload = spec.get("cost_model")
    if payload is None:
        return CostModelConfig()
    if not isinstance(payload, Mapping):
        raise ValueError("cost_model must be an object when provided")
    return CostModelConfig.model_validate(payload)


def _requested_fields(
    spec: Mapping[str, Any],
    *,
    strategy_spec: StrategySpec,
    cost_model: CostModelConfig,
) -> tuple[str, ...]:
    fields: list[str] = []
    requested = spec.get("requested_fields", ())
    if isinstance(requested, str):
        raise ValueError("requested_fields must be a list of field names")
    for field in requested:
        fields.append(str(field))
    fields.extend(["ts", "instrument_id", *strategy_spec.inputs.fields])
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


def _output_refs(
    *,
    job: WorkerJobRecord,
    result_path: Path,
    strategy_spec: StrategySpec,
    data_request: BacktestDataRequest,
    run_config: BacktestRunConfig,
    data_manifest_id: str,
    coverage_report_id: str,
    status: str,
    failure_reason: str | None,
    gross_return: float | None,
    net_return: float | None,
) -> tuple[str, ...]:
    refs = [
        "job_kind=vectorized_backtest",
        "engine_lane=vectorized",
        f"job_id={job.job_id}",
        f"run_id={run_config.run_id}",
        f"run_status={status}",
        f"run_manifest_path={result_path}",
        f"run_manifest_sha256={file_sha256(result_path)}",
        f"strategy_id={strategy_spec.strategy_id}",
        f"strategy_spec_hash={strategy_spec.spec_hash}",
        f"archive_snapshot_id={data_request.archive_snapshot_id}",
        f"universe_snapshot_id={data_request.universe_snapshot_id}",
        f"data_manifest_id={data_manifest_id}",
        f"data_manifest_hash={run_config.data_manifest_hash}",
        f"coverage_report_id={coverage_report_id}",
        f"evidence_mode={data_request.evidence_mode.value}",
        f"start_ts={utc_isoformat(data_request.start_ts)}",
        f"end_ts={utc_isoformat(data_request.end_ts)}",
    ]
    if gross_return is not None:
        refs.append(f"gross_return={gross_return:.12f}")
    if net_return is not None:
        refs.append(f"net_return={net_return:.12f}")
    if failure_reason:
        refs.append(f"run_failure_reason={failure_reason}")
    return tuple(refs)


def _json_safe_rows(rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    return [_json_safe_mapping(row) for row in rows]


def _json_safe_mapping(row: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            output[key] = utc_isoformat(value)
        else:
            output[key] = value
    return output


def _required_str(spec: Mapping[str, Any], key: str) -> str:
    value = spec.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"vectorized backtest job spec requires {key}")
    return value


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return _parse_datetime(str(value))


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("vectorized backtest timestamps must include timezone")
    return parsed


def _optional_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))
