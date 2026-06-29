# V2-AUDIT-ID: V2-AUD-BTENG-006
# V2-CONTRACTS: docs/contracts/backtest_engine_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_vectorized_backtest, archive_snapshot_reads, no_live_imports
# V2-OWNER: v2_backtest_engine
"""Durable worker job handlers for v2 backtest engines."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
import re
import time
from typing import Any

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.backtest_data.schemas import BacktestDataRequest, BacktestEvidenceMode
from tradingbotsuite.v2.backtest_data.service import BacktestDataService
from tradingbotsuite.v2.archive_inventory import ArtifactMode
from tradingbotsuite.v2.backtest_engine.artifacts import BacktestRunConfig, EngineLane
from tradingbotsuite.v2.backtest_engine.engine import run_vectorized_backtest
from tradingbotsuite.v2.config.time import utc_isoformat
from tradingbotsuite.v2.costs.models import CostModelConfig
from tradingbotsuite.v2.strategy_specs import (
    StrategySpec,
    load_strategy_spec_file,
    parse_strategy_spec,
    validate_strategy_spec,
)
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobRecord, WorkerRunResult

_SECRET_NAME_RE = re.compile(
    r"(^\.env$|secret|credential|private|token|password|wallet|api[_-]?key)",
    re.IGNORECASE,
)
_STRATEGY_SPEC_FILE_SUFFIXES = (".json", ".yaml", ".yml")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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
    requested_lane = EngineLane(str(spec.get("engine_lane", EngineLane.VECTORIZED.value)))
    if requested_lane not in {EngineLane.VECTORIZED, EngineLane.FAST_VECTORIZED}:
        raise ValueError(f"unsupported durable backtest engine_lane: {requested_lane}")
    strategy_payload, strategy_source_refs = _strategy_payload_and_refs(spec)

    validation = validate_strategy_spec(strategy_payload)
    if not validation.ok:
        raise ValueError("strategy_spec_validation_failed: " + "; ".join(validation.errors))
    strategy_spec = parse_strategy_spec(strategy_payload)
    cost_model = _cost_model(spec)
    data_request = _data_request(spec, strategy_spec=strategy_spec, cost_model=cost_model)
    asof_date = _optional_date(spec.get("asof_date"))
    data_service = BacktestDataService(data_request.archive_root)
    benchmark_enabled = bool(spec.get("benchmark_enabled", False))
    data_load_start = time.perf_counter()
    if requested_lane == EngineLane.FAST_VECTORIZED:
        data_slice = data_service.load_panel_columnar(
            data_request,
            asof_date=asof_date,
            write_manifest=bool(spec.get("write_data_manifest", True)),
        )
        panel_rows = None
        panel_table = data_slice.table
    else:
        data_slice = data_service.load_panel(
            data_request,
            asof_date=asof_date,
            write_manifest=bool(spec.get("write_data_manifest", True)),
        )
        panel_rows = _json_safe_rows(data_slice.rows)
        panel_table = None
    data_load_seconds = max(0.0, time.perf_counter() - data_load_start)
    data_manifest = data_slice.data_manifest.model_dump(mode="json")
    data_manifest_hash = canonical_json_hash(data_manifest)
    _verify_expected_data_refs(
        spec,
        archive_snapshot_id=data_slice.archive_snapshot_id,
        universe_snapshot_id=data_slice.universe_snapshot_id,
        coverage_report_id=data_slice.coverage_report_id,
        data_manifest_id=data_slice.data_manifest.data_manifest_id,
        data_manifest_hash=data_manifest_hash,
    )
    run_config = _run_config(
        spec,
        job=job,
        data_request=data_request,
        strategy_spec=strategy_spec,
        cost_model=cost_model,
        data_manifest=data_manifest,
        engine_lane=requested_lane,
    )
    if benchmark_enabled:
        run_config = run_config.model_copy(
            update={
                "benchmark_enabled": True,
                "benchmark_observations": {
                    **run_config.benchmark_observations,
                    "data_load_seconds": data_load_seconds,
                },
            }
        )
    result = run_vectorized_backtest(
        config=run_config,
        strategy_spec=strategy_spec,
        panel_rows=panel_rows,
        panel_table=panel_table,
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
        strategy_source_refs=strategy_source_refs,
        benchmark_observations=result.manifest.benchmark_observations,
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
        instrument_ids=_instrument_ids(spec),
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
    engine_lane: EngineLane,
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
    if data_request.evidence_mode == BacktestEvidenceMode.ACCEPTED_RESEARCH:
        cost_model = cost_model.model_copy(update={"spread_observation_policy": "accepted_research_strict"})
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
        engine_lane=engine_lane,
        artifact_mode=ArtifactMode(str(spec.get("artifact_mode", ArtifactMode.FULL.value))),
        benchmark_enabled=bool(spec.get("benchmark_enabled", False)),
        benchmark_observations=_benchmark_observations(spec),
        fast_lane_policy_id=str(spec.get("fast_lane_policy_id", "fast_lane_reference_authority_v1")),
        reference_engine_authority=bool(spec.get("reference_engine_authority", True)),
        reference_audit_sample_rate=float(spec.get("reference_audit_sample_rate", 0.0)),
        speedup_claimed=bool(spec.get("speedup_claimed", False)),
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


def _strategy_payload_and_refs(spec: Mapping[str, Any]) -> tuple[Mapping[str, Any], tuple[str, ...]]:
    has_inline = "strategy_spec" in spec and spec.get("strategy_spec") is not None
    has_file = "strategy_spec_file" in spec and spec.get("strategy_spec_file") is not None
    if has_inline and has_file:
        raise ValueError("vectorized backtest job spec must not provide both strategy_spec and strategy_spec_file")
    if has_file:
        path = _strategy_spec_file_path(spec.get("strategy_spec_file"))
        expected_sha = spec.get("strategy_spec_file_sha256")
        if not isinstance(expected_sha, str) or not _SHA256_RE.fullmatch(expected_sha):
            raise ValueError("strategy_spec_file_sha256 is required for strategy_spec_file intake")
        actual_sha = file_sha256(path)
        if actual_sha.lower() != expected_sha.lower():
            raise ValueError("strategy_spec_file_sha256 mismatch")
        payload = load_strategy_spec_file(path)
        return payload, (
            "strategy_spec_source=file",
            f"strategy_spec_file={path}",
            f"strategy_spec_file_sha256={actual_sha}",
        )
    strategy_payload = spec.get("strategy_spec")
    if not isinstance(strategy_payload, Mapping):
        raise ValueError("vectorized backtest job spec requires inline strategy_spec object or SHA-checked strategy_spec_file")
    return strategy_payload, ("strategy_spec_source=inline",)


def _verify_expected_data_refs(
    spec: Mapping[str, Any],
    *,
    archive_snapshot_id: str,
    universe_snapshot_id: str,
    coverage_report_id: str,
    data_manifest_id: str,
    data_manifest_hash: str,
) -> None:
    expected = {
        "expected_archive_snapshot_id": archive_snapshot_id,
        "expected_universe_snapshot_id": universe_snapshot_id,
        "expected_coverage_report_id": coverage_report_id,
        "expected_data_manifest_id": data_manifest_id,
        "expected_data_manifest_hash": data_manifest_hash,
    }
    for key, actual in expected.items():
        value = spec.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            raise ValueError(f"{key} must be a non-empty string when provided")
        if value != actual:
            raise ValueError(f"backtest_data_ref_mismatch:{key}:expected={value}:actual={actual}")


def _strategy_spec_file_path(value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("strategy_spec_file must be a non-empty string when provided")
    path = Path(value)
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise ValueError("strategy_spec_file name is reserved for secrets or local state")
    if path.suffix.lower() not in _STRATEGY_SPEC_FILE_SUFFIXES:
        raise ValueError(
            "strategy_spec_file must use one of these suffixes: "
            + ",".join(_STRATEGY_SPEC_FILE_SUFFIXES)
        )
    resolved = path.resolve(strict=False)
    if not resolved.exists():
        raise ValueError(f"strategy_spec_file missing: {path}")
    if not resolved.is_file():
        raise ValueError(f"strategy_spec_file must be a file: {path}")
    return resolved


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
    strategy_source_refs: tuple[str, ...],
    benchmark_observations: Mapping[str, float] | None = None,
) -> tuple[str, ...]:
    refs = [
        "job_kind=vectorized_backtest",
        f"engine_lane={run_config.engine_lane.value}",
        f"artifact_mode={run_config.artifact_mode.value}",
        f"job_id={job.job_id}",
        f"run_id={run_config.run_id}",
        f"run_status={status}",
        f"run_manifest_path={result_path}",
        f"run_manifest_sha256={file_sha256(result_path)}",
        f"strategy_id={strategy_spec.strategy_id}",
        f"strategy_spec_hash={strategy_spec.spec_hash}",
        *strategy_source_refs,
        f"archive_snapshot_id={data_request.archive_snapshot_id}",
        f"universe_snapshot_id={data_request.universe_snapshot_id}",
        f"data_manifest_id={data_manifest_id}",
        f"data_manifest_hash={run_config.data_manifest_hash}",
        f"coverage_report_id={coverage_report_id}",
        f"evidence_mode={data_request.evidence_mode.value}",
        f"instrument_id={data_request.instrument_id}",
        f"instrument_ids={','.join(data_request.instrument_ids)}",
        f"start_ts={utc_isoformat(data_request.start_ts)}",
        f"end_ts={utc_isoformat(data_request.end_ts)}",
    ]
    if gross_return is not None:
        refs.append(f"gross_return={gross_return:.12f}")
    if net_return is not None:
        refs.append(f"net_return={net_return:.12f}")
    if failure_reason:
        refs.append(f"run_failure_reason={failure_reason}")
    for name, value in sorted((benchmark_observations or {}).items()):
        refs.append(f"benchmark_{name}={float(value):.12f}")
    return tuple(refs)


def _benchmark_observations(spec: Mapping[str, Any]) -> dict[str, float]:
    raw = spec.get("benchmark_observations", {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError("benchmark_observations must be an object when provided")
    observations: dict[str, float] = {}
    for key, value in raw.items():
        numeric = float(value)
        if numeric < 0.0:
            raise ValueError("benchmark_observations values must be non-negative")
        observations[str(key)] = numeric
    return observations


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


def _instrument_ids(spec: Mapping[str, Any]) -> tuple[str, ...]:
    raw = spec.get("instrument_ids")
    if raw is None:
        return (_required_str(spec, "instrument_id"),)
    if isinstance(raw, str):
        raise ValueError("instrument_ids must be a list of instrument ids")
    normalized: list[str] = []
    for item in raw:
        text = str(item).strip()
        if not text:
            raise ValueError("instrument_ids must not contain empty values")
        if text not in normalized:
            normalized.append(text)
    if not normalized:
        raise ValueError("instrument_ids must not be empty when provided")
    primary = _required_str(spec, "instrument_id")
    if primary not in normalized:
        normalized.insert(0, primary)
    return tuple(normalized)


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
