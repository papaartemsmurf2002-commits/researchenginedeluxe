# V2-AUDIT-ID: V2-AUD-LEDGER-001
# V2-CONTRACTS: docs/contracts/ledger_contract.md
# V2-BOUNDARY: research_only, append_only_ledger, generated_exports_only, no_live_imports
# V2-OWNER: v2_ledger
"""Append-only experiment ledger service for v2 run manifests."""

from __future__ import annotations

import csv
import json
import math
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import median
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.backtest_engine.artifacts import BacktestMetrics, RunManifest, RunStatus
from tradingbotsuite.v2.config.time import utc_isoformat
from tradingbotsuite.v2.ledger.schemas import (
    LEDGER_SCHEMA_VERSION,
    LeaderboardRow,
    LedgerAppendRequest,
    LedgerRow,
)


class LedgerError(ValueError):
    """Raised when a ledger append/export/read operation is invalid."""


def append_run_to_ledger(request: LedgerAppendRequest | dict[str, Any]) -> LedgerRow:
    parsed_request = (
        request if isinstance(request, LedgerAppendRequest) else LedgerAppendRequest.model_validate(request)
    )
    manifest_path = Path(parsed_request.run_manifest_path).resolve()
    ledger_path = Path(parsed_request.ledger_path).resolve()
    if not manifest_path.exists():
        raise LedgerError("run_manifest_missing")
    raw_manifest = _read_json(manifest_path)
    if "validation_status" not in raw_manifest:
        raise LedgerError("validation_status_missing")
    try:
        manifest = RunManifest.model_validate(raw_manifest)
    except Exception as exc:  # pydantic errors are intentionally surfaced as ledger validation failures.
        raise LedgerError(f"invalid_run_manifest: {exc}") from exc
    _validate_manifest_for_ledger(manifest, parsed_request.evidence_mode)
    validation_manifest_path: Path | None = None
    validation_manifest: dict[str, Any] | None = None
    if parsed_request.validation_manifest_path:
        validation_manifest_path = Path(parsed_request.validation_manifest_path).resolve()
        validation_manifest = _read_validation_gate_manifest(
            validation_manifest_path,
            manifest=manifest,
            manifest_path=manifest_path,
        )
    part_index = _read_valid_ledger_part_index(ledger_path)
    ledger_index = None if part_index is not None else _read_valid_ledger_index(ledger_path)
    if part_index is not None and manifest.run_id in part_index["run_ids"]:
        raise LedgerError(f"duplicate_run_id: {manifest.run_id}")
    if ledger_index is not None and manifest.run_id in ledger_index["run_ids"]:
        raise LedgerError(f"duplicate_run_id: {manifest.run_id}")
    rows: list[LedgerRow] = []
    if part_index is None and ledger_index is None:
        rows = read_ledger(ledger_path)
        if any(row.run_id == manifest.run_id for row in rows):
            raise LedgerError(f"duplicate_run_id: {manifest.run_id}")
        next_index = len(rows)
        part_index = _bootstrap_ledger_part_index(
            ledger_path,
            compacted_path=ledger_path if ledger_path.exists() else None,
            rows=rows,
        )
    elif part_index is not None:
        next_index = int(part_index["row_count"])
    else:
        next_index = int(ledger_index["row_count"])
        part_index = _bootstrap_ledger_part_index(
            ledger_path,
            compacted_path=ledger_path,
            rows=None,
            row_count=int(ledger_index["row_count"]),
            run_ids=dict(ledger_index["run_ids"]),
        )
    row = ledger_row_from_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        validation_manifest=validation_manifest,
        validation_manifest_path=validation_manifest_path,
        ledger_index=next_index,
        evidence_mode=parsed_request.evidence_mode,
        notes=parsed_request.notes,
    )
    row = row.model_copy(update={"row_hash": ledger_row_hash(row)})
    if part_index is None or not _append_ledger_row_part(ledger_path, row, part_index):
        if ledger_index is None or not _append_ledger_row_with_index(ledger_path, row, ledger_index):
            _write_ledger_rows(ledger_path, [*rows, row])
    return row


def read_ledger(ledger_path: str | Path) -> list[LedgerRow]:
    path = Path(ledger_path)
    part_index = _read_valid_ledger_part_index(path)
    if part_index is not None:
        return _read_ledger_parts(path, part_index)
    if not path.exists():
        return []
    table = pq.read_table(path)
    rows = [LedgerRow.model_validate(row) for row in table.to_pylist()]
    for index, row in enumerate(rows):
        if row.ledger_index != index:
            raise LedgerError(f"ledger_index_mismatch: expected={index} observed={row.ledger_index}")
        expected_hash = ledger_row_hash(row)
        if row.row_hash != expected_hash:
            raise LedgerError(f"ledger_row_hash_mismatch: {row.run_id}")
    return rows


def compact_ledger_parts(ledger_path: str | Path, output_path: str | Path | None = None) -> Path:
    path = Path(ledger_path).resolve()
    rows = read_ledger(path)
    output = Path(output_path).resolve() if output_path is not None else _ledger_part_root(path) / "compacted" / "current.parquet"
    _write_ledger_rows(output, rows)
    part_index = _read_valid_ledger_part_index(path)
    if part_index is None:
        part_index = _bootstrap_ledger_part_index(
            path,
            compacted_path=output,
            rows=rows,
        )
    else:
        _write_ledger_part_index(
            path,
            row_count=len(rows),
            run_ids={row.run_id: row.ledger_index for row in rows},
            compacted_path=output,
            parts=[],
        )
    return output


def export_ledger(
    *,
    ledger_path: str | Path,
    output_path: str | Path,
    export_format: str,
) -> Path:
    rows = read_ledger(ledger_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = export_format.strip().lower()
    if normalized == "csv":
        _write_csv(output, rows)
        return output
    if normalized == "xlsx":
        _write_xlsx(output, rows)
        return output
    raise LedgerError(f"unsupported_ledger_export_format: {export_format}")


def leaderboard(
    *,
    ledger_path: str | Path,
    require_validation_pass: bool = True,
    exclude_sandbox: bool = True,
    rank: str = "composite_v1",
) -> list[LeaderboardRow]:
    if rank != "composite_v1":
        raise LedgerError(f"unsupported_leaderboard_rank: {rank}")
    ledger_rows = read_ledger(ledger_path)
    family_counts = _family_counts(ledger_rows)
    family_medians = _family_medians(ledger_rows)
    eligible: list[tuple[float, LedgerRow, int, float | None, bool]] = []
    for row in ledger_rows:
        if row.row_status != RunStatus.SUCCEEDED.value:
            continue
        if row.net_return is None:
            continue
        if row.gross_only:
            continue
        if require_validation_pass and row.validation_status != "pass":
            continue
        if exclude_sandbox and row.evidence_mode == "sandbox_diagnostic":
            continue
        if row.universe_mode == "current":
            continue
        if row.live_signal or row.paper_signal or row.sizing_instruction or row.order_placement_instruction:
            continue
        family_key = _family_key(row)
        trial_count = family_counts[family_key]
        family_median = family_medians.get(family_key)
        overfit_warning = bool(
            (trial_count >= 20 and family_median is not None and family_median <= 0.0 and row.net_return > 0.0)
            or (row.pbo_score is not None and row.pbo_score >= 0.5)
        )
        max_drawdown = abs(row.max_drawdown or 0.0)
        composite_score = row.net_return - (0.25 * max_drawdown)
        if row.cost_fragile_warning:
            composite_score -= 0.05
        if row.fold_stability_score is not None:
            composite_score -= max(0.0, 0.5 - row.fold_stability_score) * 0.1
        if overfit_warning:
            composite_score -= 0.05
        eligible.append((composite_score, row, trial_count, family_median, overfit_warning))
    ranked = sorted(
        eligible,
        key=lambda item: (
            item[0],
            item[1].net_return if item[1].net_return is not None else float("-inf"),
            item[1].run_id,
        ),
        reverse=True,
    )
    return [
        LeaderboardRow(
            rank=index,
            run_id=row.run_id,
            experiment_id=row.experiment_id,
            strategy_id=row.strategy_id,
            net_return=float(row.net_return),
            gross_return=row.gross_return,
            max_drawdown=row.max_drawdown,
            composite_score=score,
            validation_status=row.validation_status,
            evidence_mode=row.evidence_mode,
            trial_count=trial_count,
            fold_count=row.fold_count,
            fold_stability_score=row.fold_stability_score,
            overfit_warning=overfit_warning,
        )
        for index, (score, row, trial_count, _family_median, overfit_warning) in enumerate(ranked, start=1)
    ]


def ledger_row_from_manifest(
    *,
    manifest: RunManifest,
    manifest_path: Path,
    validation_manifest: dict[str, Any] | None = None,
    validation_manifest_path: Path | None = None,
    ledger_index: int,
    evidence_mode: str,
    notes: str = "",
) -> LedgerRow:
    metrics = manifest.metrics
    cost_manifest = _read_artifact_json(manifest_path.parent, manifest, "cost_manifest")
    fold_count, fold_stability_score = _fold_summary(manifest_path.parent, manifest)
    if validation_manifest is not None:
        fold_count = int(validation_manifest.get("fold_count", fold_count))
        if validation_manifest.get("fold_stability_score") is not None:
            fold_stability_score = float(validation_manifest["fold_stability_score"])
    max_drawdown = _max_drawdown(manifest_path.parent, manifest)
    days = max(1.0, (manifest.backtest_end - manifest.backtest_start).total_seconds() / 86_400.0)
    annualized_return = _annualized_return(metrics.net_return, days) if metrics is not None else None
    calmar = None
    if annualized_return is not None and max_drawdown is not None and max_drawdown < 0.0:
        calmar = annualized_return / abs(max_drawdown)
    validation_status = _validation_status(manifest, validation_manifest)
    blocker_reasons = _blocker_reasons(manifest, validation_manifest)
    resolved_validation_manifest_path = (
        str(validation_manifest_path)
        if validation_manifest_path is not None
        else _artifact_path(manifest, "validation_manifest")
    )
    return LedgerRow(
        ledger_index=ledger_index,
        run_id=manifest.run_id,
        experiment_id=manifest.experiment_id,
        trial_index=manifest.trial_index,
        agent_or_user=manifest.agent_or_user,
        created_at=manifest.created_at,
        row_status=manifest.status.value,
        evidence_mode=evidence_mode,
        git_sha=manifest.git_sha,
        environment_hash=manifest.environment_hash,
        strategy_id=manifest.strategy_id,
        strategy_version=manifest.strategy_version,
        strategy_hash=manifest.strategy_hash,
        params_hash=manifest.params_hash,
        strategy_lane=manifest.strategy_lane,
        archive_snapshot_id=manifest.archive_snapshot_id,
        universe_snapshot_id=manifest.universe_snapshot_id,
        feature_snapshot_id=manifest.data_manifest_id,
        universe_mode=manifest.universe_mode,
        venue_scope=manifest.venue_scope,
        instrument_count=manifest.instrument_count,
        timeframe=manifest.timeframe,
        backtest_start=manifest.backtest_start,
        backtest_end=manifest.backtest_end,
        usable_months=manifest.usable_months,
        lockbox_policy_id=manifest.lockbox_policy_id,
        lockbox_start=manifest.lockbox_start,
        lockbox_end=manifest.lockbox_end,
        data_coverage_min=manifest.data_coverage_min,
        strategy_spec_hash=manifest.strategy_spec_hash,
        cost_model_id=manifest.cost_model_id,
        cost_model_hash=manifest.cost_model_hash,
        gross_return=None if metrics is None else metrics.gross_return,
        validation_status=validation_status,
        net_return=None if metrics is None else metrics.net_return,
        roi_observed=None if metrics is None else metrics.net_return,
        annualized_return=annualized_return,
        annualized_vol=None,
        sharpe=None,
        sortino=None,
        max_drawdown=max_drawdown,
        calmar=calmar,
        turnover=None if metrics is None else metrics.total_turnover,
        avg_daily_trades=None if metrics is None else metrics.trade_count / days,
        fee_paid=None if metrics is None else metrics.total_fee_cost,
        funding_pnl=None if metrics is None else metrics.total_funding_pnl,
        slippage_cost=None if metrics is None else metrics.total_slippage_cost,
        impact_cost=None if metrics is None else metrics.total_impact_cost,
        walk_forward_pass=validation_status == "pass",
        pbo_score=None,
        trial_count=1,
        fold_count=fold_count,
        fold_stability_score=fold_stability_score,
        family_median_net_return=None,
        best_vs_median_gap=None,
        failure_reason=manifest.failure_reason,
        minimum_trade_frequency_pass=None if metrics is None else metrics.trade_count > 0,
        cost_fragile_warning=_cost_fragile_warning(cost_manifest)
        or bool(validation_manifest and validation_manifest.get("cost_fragile_warning")),
        artifact_path=str(manifest_path),
        artifact_sha256=file_sha256(manifest_path),
        validation_manifest_path=resolved_validation_manifest_path,
        metrics_path=_artifact_path(manifest, "metrics"),
        notes=notes,
        gross_only=False if metrics is None else metrics.gross_only,
        blocker_reasons=blocker_reasons,
        research_only=manifest.research_only,
        observe_only=manifest.observe_only,
        promotion_ready=manifest.promotion_ready,
        candidate_evidence=manifest.candidate_evidence,
        candidate_pack_eligible=manifest.candidate_pack_eligible,
        live_signal=manifest.live_signal,
        paper_signal=manifest.paper_signal,
        sizing_instruction=manifest.sizing_instruction,
        order_placement_instruction=manifest.order_placement_instruction,
        runtime_mode_change=manifest.runtime_mode_change,
    )


def ledger_row_hash(row: LedgerRow) -> str:
    payload = row.model_dump(mode="json", exclude={"row_hash"})
    return canonical_json_hash(payload)


def _validate_manifest_for_ledger(manifest: RunManifest, evidence_mode: str) -> None:
    if not manifest.research_only or not manifest.observe_only or manifest.promotion_ready:
        raise LedgerError("run_manifest_boundary_violation")
    if manifest.status == RunStatus.SUCCEEDED and manifest.metrics is None:
        raise LedgerError("metrics_missing")
    if manifest.metrics is not None and manifest.metrics.gross_only:
        raise LedgerError("gross_only_metrics_rejected")
    if evidence_mode == "accepted_research":
        earliest = datetime(2024, 1, 1, tzinfo=UTC)
        if manifest.backtest_start < earliest:
            raise LedgerError("backtest_start_before_2024")
        if manifest.usable_months < 6:
            raise LedgerError("usable_months_below_accepted_floor")
        if manifest.universe_mode == "current":
            raise LedgerError("current_universe_cannot_be_accepted_research")
        if _windows_overlap(
            manifest.backtest_start,
            manifest.backtest_end,
            manifest.lockbox_start,
            manifest.lockbox_end,
        ):
            raise LedgerError("run_overlaps_lockbox")


def _write_ledger_rows(path: Path, rows: list[LedgerRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payloads = [row.model_dump(mode="json") for row in rows]
    table = pa.Table.from_pylist(payloads, schema=_ledger_schema())
    pq.write_table(table, path, compression="zstd")
    _write_ledger_index(
        path,
        row_count=len(rows),
        run_ids={row.run_id: row.ledger_index for row in rows},
    )


def _append_ledger_row_with_index(
    path: Path,
    row: LedgerRow,
    index: dict[str, Any],
) -> bool:
    try:
        row_count = int(index["row_count"])
        if row.ledger_index != row_count:
            return False
        row_table = pa.Table.from_pylist([row.model_dump(mode="json")], schema=_ledger_schema())
        if path.exists():
            table = pq.read_table(path)
            if table.num_rows != row_count:
                return False
            table = pa.concat_tables([table, row_table], promote_options="default")
        else:
            if row_count != 0:
                return False
            table = row_table
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path, compression="zstd")
        run_ids = dict(index["run_ids"])
        run_ids[row.run_id] = row.ledger_index
        _write_ledger_index(path, row_count=row_count + 1, run_ids=run_ids)
        return True
    except Exception:
        return False


def _append_ledger_row_part(
    path: Path,
    row: LedgerRow,
    index: dict[str, Any],
) -> bool:
    try:
        row_count = int(index["row_count"])
        if row.ledger_index != row_count:
            return False
        if row.run_id in index["run_ids"]:
            raise LedgerError(f"duplicate_run_id: {row.run_id}")
        part_dir = _ledger_part_root(path) / "parts"
        part_dir.mkdir(parents=True, exist_ok=True)
        part_path = part_dir / f"ledger_part_{row.ledger_index:06d}.parquet"
        table = pa.Table.from_pylist([row.model_dump(mode="json")], schema=_ledger_schema())
        pq.write_table(table, part_path, compression="zstd")
        part_ref = {
            "path": str(part_path),
            "sha256": file_sha256(part_path),
            "start_index": row.ledger_index,
            "row_count": 1,
            "run_ids": [row.run_id],
        }
        run_ids = dict(index["run_ids"])
        run_ids[row.run_id] = row.ledger_index
        parts = [*index.get("parts", ()), part_ref]
        _append_ledger_log(
            path,
            {
                "event": "append_part",
                "run_id": row.run_id,
                "ledger_index": row.ledger_index,
                "row_hash": row.row_hash,
                "part_path": str(part_path),
                "part_sha256": part_ref["sha256"],
                "created_at": utc_isoformat(datetime.now(tz=UTC)),
            },
        )
        _write_ledger_part_index(
            path,
            row_count=row_count + 1,
            run_ids=run_ids,
            compacted_path=index.get("compacted_path"),
            parts=parts,
        )
        return True
    except LedgerError:
        raise
    except Exception:
        return False


def _read_ledger_parts(path: Path, index: dict[str, Any]) -> list[LedgerRow]:
    tables: list[pa.Table] = []
    compacted_path = index.get("compacted_path")
    if compacted_path:
        compacted = Path(str(compacted_path))
        if compacted.exists():
            tables.append(pq.read_table(compacted))
    for part in index.get("parts", ()):
        part_path = Path(str(part["path"]))
        if not part_path.exists():
            raise LedgerError(f"ledger_part_missing: {part_path}")
        if file_sha256(part_path) != part.get("sha256"):
            raise LedgerError(f"ledger_part_hash_mismatch: {part_path}")
        tables.append(pq.read_table(part_path))
    if not tables:
        return []
    table = pa.concat_tables(tables, promote_options="default")
    if table.num_rows > 1:
        order = pa.compute.sort_indices(table, sort_keys=[("ledger_index", "ascending")])
        table = table.take(order)
    rows = [LedgerRow.model_validate(row) for row in table.to_pylist()]
    for row_index, row in enumerate(rows):
        if row.ledger_index != row_index:
            raise LedgerError(f"ledger_index_mismatch: expected={row_index} observed={row.ledger_index}")
        expected_hash = ledger_row_hash(row)
        if row.row_hash != expected_hash:
            raise LedgerError(f"ledger_row_hash_mismatch: {row.run_id}")
    if len(rows) != int(index["row_count"]):
        raise LedgerError("ledger_part_index_row_count_mismatch")
    return rows


def _bootstrap_ledger_part_index(
    path: Path,
    *,
    compacted_path: Path | None,
    rows: list[LedgerRow] | None,
    row_count: int | None = None,
    run_ids: dict[str, int] | None = None,
) -> dict[str, Any]:
    if rows is not None:
        row_count = len(rows)
        run_ids = {row.run_id: row.ledger_index for row in rows}
    if compacted_path is None and not path.exists():
        _write_empty_ledger_placeholder(path)
        compacted_path = path
    resolved_count = int(row_count or 0)
    resolved_run_ids = dict(run_ids or {})
    _write_ledger_part_index(
        path,
        row_count=resolved_count,
        run_ids=resolved_run_ids,
        compacted_path=compacted_path,
        parts=[],
    )
    return {
        "row_count": resolved_count,
        "run_ids": resolved_run_ids,
        "compacted_path": None if compacted_path is None else str(compacted_path),
        "parts": [],
    }


def _write_empty_ledger_placeholder(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist([], schema=_ledger_schema())
    pq.write_table(table, path, compression="zstd")


def _read_valid_ledger_index(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    index_path = _ledger_index_path(path)
    if not index_path.exists():
        return None
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "ledger_index_v1":
            return None
        if int(payload.get("parquet_size_bytes", -1)) != path.stat().st_size:
            return None
        if int(payload.get("parquet_mtime_ns", -1)) != path.stat().st_mtime_ns:
            return None
        row_count = int(payload["row_count"])
        run_ids = {
            str(run_id): int(ledger_index)
            for run_id, ledger_index in dict(payload["run_ids"]).items()
        }
    except Exception:
        return None
    if row_count < 0 or any(index < 0 for index in run_ids.values()):
        return None
    return {"row_count": row_count, "run_ids": run_ids}


def _read_valid_ledger_part_index(path: Path) -> dict[str, Any] | None:
    index_path = _ledger_index_path(path)
    if not index_path.exists():
        return None
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "ledger_part_index_v1":
            return None
        row_count = int(payload["row_count"])
        run_ids = {
            str(run_id): int(ledger_index)
            for run_id, ledger_index in dict(payload["run_ids"]).items()
        }
        compacted_path = payload.get("compacted_path")
        parts = list(payload.get("parts", ()))
    except Exception:
        return None
    if row_count < 0 or any(index < 0 for index in run_ids.values()):
        return None
    if len(run_ids) != row_count:
        return None
    return {
        "row_count": row_count,
        "run_ids": run_ids,
        "compacted_path": compacted_path,
        "parts": parts,
    }


def _write_ledger_part_index(
    path: Path,
    *,
    row_count: int,
    run_ids: dict[str, int],
    compacted_path: str | Path | None,
    parts: list[dict[str, Any]],
) -> None:
    payload = {
        "schema_version": "ledger_part_index_v1",
        "ledger_path": str(path),
        "storage_mode": "append_parts",
        "row_count": row_count,
        "run_ids": dict(sorted(run_ids.items(), key=lambda item: item[1])),
        "compacted_path": None if compacted_path is None else str(compacted_path),
        "parts": parts,
        "append_log_path": str(_ledger_append_log_path(path)),
    }
    _write_json_atomic(_ledger_index_path(path), payload)


def _append_ledger_log(path: Path, payload: dict[str, Any]) -> None:
    log_path = _ledger_append_log_path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _ledger_part_root(path: Path) -> Path:
    return path.with_suffix(".parts")


def _ledger_append_log_path(path: Path) -> Path:
    return _ledger_part_root(path) / "append_log.jsonl"


def _write_ledger_index(path: Path, *, row_count: int, run_ids: dict[str, int]) -> None:
    if not path.exists():
        return
    stat = path.stat()
    payload = {
        "schema_version": "ledger_index_v1",
        "ledger_path": str(path),
        "row_count": row_count,
        "run_ids": dict(sorted(run_ids.items(), key=lambda item: item[1])),
        "parquet_size_bytes": stat.st_size,
        "parquet_mtime_ns": stat.st_mtime_ns,
    }
    _write_json_atomic(_ledger_index_path(path), payload)


def _ledger_index_path(path: Path) -> Path:
    return path.with_suffix(".index.json")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def _write_csv(path: Path, rows: list[LedgerRow]) -> None:
    payloads = [_export_payload(row) for row in rows]
    fieldnames = list(_export_columns())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(payloads)


def _write_xlsx(path: Path, rows: list[LedgerRow]) -> None:
    columns = list(_export_columns())
    values = [columns, *[[str(_export_payload(row).get(column, "")) for column in columns] for row in rows]]
    sheet_xml = _worksheet_xml(values)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _xlsx_content_types())
        archive.writestr("_rels/.rels", _xlsx_root_rels())
        archive.writestr("xl/workbook.xml", _xlsx_workbook())
        archive.writestr("xl/_rels/workbook.xml.rels", _xlsx_workbook_rels())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _export_payload(row: LedgerRow) -> dict[str, Any]:
    payload = row.model_dump(mode="json")
    payload["blocker_reasons"] = ";".join(row.blocker_reasons)
    return payload


def _export_columns() -> tuple[str, ...]:
    return tuple(LedgerRow.model_fields)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_validation_gate_manifest(
    path: Path,
    *,
    manifest: RunManifest,
    manifest_path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise LedgerError("validation_manifest_missing")
    raw = _read_json(path)
    if raw.get("schema_version") != "validation_gate_manifest_v1":
        raise LedgerError("invalid_validation_manifest_schema")
    if raw.get("run_id") != manifest.run_id:
        raise LedgerError("validation_manifest_run_id_mismatch")
    if raw.get("run_manifest_sha256") != file_sha256(manifest_path):
        raise LedgerError("validation_manifest_run_manifest_sha256_mismatch")
    status = str(raw.get("validation_status", "")).strip().lower()
    if status not in {"pass", "fail"}:
        raise LedgerError("validation_manifest_status_invalid")
    blockers = raw.get("blocker_reasons", ())
    if not isinstance(blockers, list):
        raise LedgerError("validation_manifest_blocker_reasons_invalid")
    if status == "pass" and blockers:
        raise LedgerError("validation_manifest_pass_with_blockers")
    if status == "fail" and not blockers:
        raise LedgerError("validation_manifest_fail_without_blockers")
    if not bool(raw.get("research_only")) or not bool(raw.get("observe_only")):
        raise LedgerError("validation_manifest_boundary_violation")
    for forbidden in (
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    ):
        if bool(raw.get(forbidden)):
            raise LedgerError("validation_manifest_boundary_violation")
    return raw


def _read_artifact_json(root: Path, manifest: RunManifest, name: str) -> dict[str, Any]:
    ref = manifest.artifacts.get(name)
    if ref is None:
        return {}
    path = root / ref.path
    if not path.exists():
        return {}
    return _read_json(path)


def _artifact_path(manifest: RunManifest, name: str) -> str:
    ref = manifest.artifacts.get(name)
    return "" if ref is None else ref.path


def _cost_fragile_warning(cost_manifest: dict[str, Any]) -> bool:
    sensitivity = cost_manifest.get("cost_sensitivity")
    if not isinstance(sensitivity, dict):
        return False
    return bool(sensitivity.get("cost_fragile_warning")) or bool(
        sensitivity.get("cost_dependent_failure")
    )


def _family_key(row: LedgerRow) -> tuple[str, str]:
    return (row.experiment_id, row.strategy_id)


def _family_counts(rows: Iterable[LedgerRow]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = _family_key(row)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _family_medians(rows: Iterable[LedgerRow]) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        if row.net_return is None:
            continue
        grouped.setdefault(_family_key(row), []).append(row.net_return)
    return {key: float(median(values)) for key, values in grouped.items() if values}


def _fold_summary(root: Path, manifest: RunManifest) -> tuple[int, float | None]:
    ref = manifest.artifacts.get("fold_metrics")
    if ref is None:
        return 0, None
    path = root / ref.path
    if not path.exists():
        return 0, None
    rows = pq.read_table(path).to_pylist()
    rows = _monthly_validation_rows(rows)
    if not rows:
        return 0, None
    net_returns = [float(row["net_return"]) for row in rows if row.get("net_return") is not None]
    if not net_returns:
        return len(rows), None
    positive = sum(1 for value in net_returns if value > 0.0)
    return len(rows), positive / len(net_returns)


def _monthly_validation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if str(row.get("fold_family", "monthly_validation")).strip().lower() == "monthly_validation"
        and str(row.get("fold_id", "")).strip().lower() != "full_window"
    ]


def _max_drawdown(root: Path, manifest: RunManifest) -> float | None:
    ref = manifest.artifacts.get("equity_curve")
    if ref is None:
        return None
    path = root / ref.path
    if not path.exists():
        return None
    rows = pq.read_table(path).to_pylist()
    peak: float | None = None
    max_drawdown = 0.0
    for row in rows:
        equity = row.get("net_equity")
        if equity is None:
            continue
        equity = float(equity)
        peak = equity if peak is None else max(peak, equity)
        if peak and peak > 0.0:
            max_drawdown = min(max_drawdown, (equity / peak) - 1.0)
    return max_drawdown


def _annualized_return(net_return: float, days: float) -> float | None:
    if net_return <= -1.0:
        return None
    try:
        value = (1.0 + net_return) ** (365.0 / max(days, 1.0)) - 1.0
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def _validation_status(
    manifest: RunManifest,
    validation_manifest: dict[str, Any] | None,
) -> str:
    if validation_manifest is not None:
        return str(validation_manifest["validation_status"]).strip().lower()
    return manifest.validation_status.value


def _blocker_reasons(
    manifest: RunManifest,
    validation_manifest: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if manifest.failure_reason:
        reasons.append(manifest.failure_reason)
    if manifest.status != RunStatus.SUCCEEDED:
        reasons.append(f"run_status_{manifest.status.value}")
    status = _validation_status(manifest, validation_manifest)
    if status != "pass":
        reasons.append(f"validation_status_{status}")
    if validation_manifest is not None:
        reasons.extend(str(reason) for reason in validation_manifest.get("blocker_reasons", ()))
    return tuple(dict.fromkeys(reasons))


def _windows_overlap(
    left_start: datetime,
    left_end: datetime,
    right_start: datetime | None,
    right_end: datetime | None,
) -> bool:
    if right_start is None or right_end is None:
        return False
    return max(left_start, right_start) < min(left_end, right_end)


def _ledger_schema() -> pa.Schema:
    return pa.schema(
        [
            ("schema_version", pa.string()),
            ("ledger_index", pa.int64()),
            ("row_hash", pa.string()),
            ("run_id", pa.string()),
            ("experiment_id", pa.string()),
            ("trial_index", pa.int64()),
            ("agent_or_user", pa.string()),
            ("created_at", pa.string()),
            ("row_status", pa.string()),
            ("evidence_mode", pa.string()),
            ("git_sha", pa.string()),
            ("environment_hash", pa.string()),
            ("strategy_id", pa.string()),
            ("strategy_version", pa.string()),
            ("strategy_hash", pa.string()),
            ("params_hash", pa.string()),
            ("strategy_lane", pa.string()),
            ("archive_snapshot_id", pa.string()),
            ("universe_snapshot_id", pa.string()),
            ("feature_snapshot_id", pa.string()),
            ("universe_mode", pa.string()),
            ("venue_scope", pa.string()),
            ("instrument_count", pa.int64()),
            ("timeframe", pa.string()),
            ("backtest_start", pa.string()),
            ("backtest_end", pa.string()),
            ("usable_months", pa.int64()),
            ("lockbox_policy_id", pa.string()),
            ("lockbox_start", pa.string()),
            ("lockbox_end", pa.string()),
            ("data_coverage_min", pa.float64()),
            ("strategy_spec_hash", pa.string()),
            ("cost_model_id", pa.string()),
            ("cost_model_hash", pa.string()),
            ("gross_return", pa.float64()),
            ("validation_status", pa.string()),
            ("net_return", pa.float64()),
            ("roi_observed", pa.float64()),
            ("annualized_return", pa.float64()),
            ("annualized_vol", pa.float64()),
            ("sharpe", pa.float64()),
            ("sortino", pa.float64()),
            ("max_drawdown", pa.float64()),
            ("calmar", pa.float64()),
            ("turnover", pa.float64()),
            ("avg_daily_trades", pa.float64()),
            ("fee_paid", pa.float64()),
            ("funding_pnl", pa.float64()),
            ("slippage_cost", pa.float64()),
            ("impact_cost", pa.float64()),
            ("walk_forward_pass", pa.bool_()),
            ("pbo_score", pa.float64()),
            ("trial_count", pa.int64()),
            ("fold_count", pa.int64()),
            ("fold_stability_score", pa.float64()),
            ("family_median_net_return", pa.float64()),
            ("best_vs_median_gap", pa.float64()),
            ("failure_reason", pa.string()),
            ("diminishing_returns_warning", pa.bool_()),
            ("profit_concentration_warning", pa.bool_()),
            ("minimum_trade_frequency_pass", pa.bool_()),
            ("monthly_stability_pass", pa.bool_()),
            ("cost_fragile_warning", pa.bool_()),
            ("survivorship_bias_status", pa.string()),
            ("artifact_path", pa.string()),
            ("artifact_sha256", pa.string()),
            ("validation_manifest_path", pa.string()),
            ("metrics_path", pa.string()),
            ("notes", pa.string()),
            ("gross_only", pa.bool_()),
            ("blocker_reasons", pa.list_(pa.string())),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
            ("candidate_evidence", pa.bool_()),
            ("candidate_pack_eligible", pa.bool_()),
            ("live_signal", pa.bool_()),
            ("paper_signal", pa.bool_()),
            ("sizing_instruction", pa.bool_()),
            ("order_placement_instruction", pa.bool_()),
            ("runtime_mode_change", pa.bool_()),
        ]
    )


def _worksheet_xml(values: list[list[str]]) -> str:
    rows_xml: list[str] = []
    for row_index, row_values in enumerate(values, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row_values, start=1):
            ref = f"{_column_name(column_index)}{row_index}"
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        rows_xml.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(rows_xml)
        + "</sheetData></worksheet>"
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _xlsx_content_types() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )


def _xlsx_root_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _xlsx_workbook() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="ledger" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )


def _xlsx_workbook_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
