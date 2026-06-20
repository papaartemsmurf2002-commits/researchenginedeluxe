from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import require_sandbox_boundary, sandbox_boundary_metadata
from tradingbotsuite.research_sandbox.integrity import require_sandbox_artifact_integrity


ANALYSIS_REPORT_NAME = "analysis_summary.json"
SANDBOX_ANALYSIS_BUCKET_ROLLUP_VERSION = 1
SANDBOX_ANALYSIS_BUCKET_ROLLUP_LIMIT_PER_TYPE = 50
SANDBOX_ANALYSIS_BUCKET_ROLLUP_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("venue", ("venue",)),
    ("family", ("family",)),
    ("exit_profile", ("exit_profile",)),
    ("exit_variant", ("exit_variant_id",)),
    ("filter_variant", ("filter_variant_id",)),
    ("venue_family", ("venue", "family")),
)


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_path(run_dir: Path, manifest: dict[str, Any], key: str, fallback_name: str) -> Path:
    artifacts = manifest.get("artifacts", {})
    raw = artifacts.get(key) if isinstance(artifacts, dict) else None
    if raw:
        candidate = Path(str(raw))
        if not candidate.is_absolute():
            candidate = run_dir / candidate
        if candidate.exists():
            return candidate
    fallback = run_dir / fallback_name
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"sandbox analysis missing artifact {key}: {fallback}")


def _parse_json_cell(value: Any, *, default: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _boundary_columns_ok(frame: pd.DataFrame) -> bool:
    required = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "sandbox_only": True,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
    }
    for column, expected in required.items():
        if column not in frame.columns:
            return False
        if set(frame[column].dropna().astype(bool).unique()) != {expected}:
            return False
    return True


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame.columns:
        return {}
    counts = frame[column].fillna("missing").astype(str).value_counts()
    return {str(key): int(value) for key, value in counts.items()}


def _group_counts(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    available = [column for column in columns if column in frame.columns]
    if not available:
        return []
    grouped = frame.groupby(available, dropna=False).size().reset_index(name="count")
    rows: list[dict[str, Any]] = []
    for record in grouped.to_dict(orient="records"):
        rows.append({str(key): (None if pd.isna(value) else value) for key, value in record.items()})
    return sorted(rows, key=lambda row: (-int(row["count"]), tuple(str(row.get(column, "")) for column in available)))


def _scalar_value(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return value
    return value


def _as_float(value: Any) -> float | None:
    value = _scalar_value(value)
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return numeric


def _as_int(value: Any) -> int | None:
    value = _scalar_value(value)
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return int(numeric)


def _best_group_row(frame: pd.DataFrame) -> dict[str, Any] | None:
    if frame.empty:
        return None
    sortable = frame.copy()
    if "rank" in sortable.columns:
        sortable["_sandbox_sort_rank"] = pd.to_numeric(sortable["rank"], errors="coerce")
        sortable = sortable.sort_values("_sandbox_sort_rank", na_position="last")
    else:
        sort_columns = [column for column in ("score", "net_return_sum", "trade_count") if column in sortable.columns]
        if sort_columns:
            for column in sort_columns:
                sortable[column] = pd.to_numeric(sortable[column], errors="coerce")
            sortable = sortable.sort_values(sort_columns, ascending=[False] * len(sort_columns), na_position="last")
    return sortable.head(1).drop(columns=["_sandbox_sort_rank"], errors="ignore").to_dict(orient="records")[0]


def _bucket_key(columns: tuple[str, ...], values: dict[str, Any]) -> str:
    parts: list[str] = []
    for column in columns:
        value = values.get(column)
        parts.append(f"{column}={'missing' if value is None else value}")
    return "|".join(parts)


def _status_count(frame: pd.DataFrame, status: str) -> int:
    if "status" not in frame.columns:
        return 0
    return int((frame["status"].fillna("missing").astype(str) == status).sum())


def _positive_net_count(frame: pd.DataFrame) -> int:
    if "net_return_sum" not in frame.columns:
        return 0
    return int((pd.to_numeric(frame["net_return_sum"], errors="coerce") > 0.0).sum())


def _requested_trial_count(frame: pd.DataFrame, requested_trial_ids: set[str]) -> int:
    if "trial_id" not in frame.columns or not requested_trial_ids:
        return 0
    return int(frame["trial_id"].fillna("").astype(str).isin(requested_trial_ids).sum())


def _analysis_bucket_rollups(
    rankings: pd.DataFrame,
    *,
    evidence_request_trial_ids: list[str],
    limit_per_type: int = SANDBOX_ANALYSIS_BUCKET_ROLLUP_LIMIT_PER_TYPE,
) -> list[dict[str, Any]]:
    if rankings.empty:
        return []
    requested_trial_ids = {str(trial_id) for trial_id in evidence_request_trial_ids if trial_id is not None}
    boundary = sandbox_boundary_metadata()
    rollups: list[dict[str, Any]] = []
    for rollup_type, columns in SANDBOX_ANALYSIS_BUCKET_ROLLUP_GROUPS:
        available = tuple(column for column in columns if column in rankings.columns)
        if len(available) != len(columns):
            continue
        group_rows: list[dict[str, Any]] = []
        for raw_values, group in rankings.groupby(list(columns), dropna=False, sort=True):
            if not isinstance(raw_values, tuple):
                raw_values = (raw_values,)
            bucket_values = {
                column: _scalar_value(value)
                for column, value in zip(columns, raw_values, strict=True)
            }
            best = _best_group_row(group)
            status_counts = _value_counts(group, "status")
            row = {
                **boundary,
                "rollup_version": SANDBOX_ANALYSIS_BUCKET_ROLLUP_VERSION,
                "rollup_type": rollup_type,
                "bucket_key": _bucket_key(columns, bucket_values),
                "bucket_values": bucket_values,
                "result_count": int(len(group)),
                "screened_count": _status_count(group, "screened"),
                "rejected_count": _status_count(group, "rejected"),
                "blocked_count": _status_count(group, "blocked"),
                "status_counts": status_counts,
                "positive_net_result_count": _positive_net_count(group),
                "evidence_request_count": _requested_trial_count(group, requested_trial_ids),
                "strict_validation_authorized": False,
                "candidate_pack_authorized": False,
                "best_rank": _as_int(best.get("rank")) if best else None,
                "best_trial_id": str(best.get("trial_id")) if best and best.get("trial_id") is not None else None,
                "best_hypothesis_id": (
                    str(best.get("hypothesis_id")) if best and best.get("hypothesis_id") is not None else None
                ),
                "best_family": str(best.get("family")) if best and best.get("family") is not None else None,
                "best_venue": str(best.get("venue")) if best and best.get("venue") is not None else None,
                "best_symbol": str(best.get("symbol")) if best and best.get("symbol") is not None else None,
                "best_exit_profile": (
                    str(best.get("exit_profile")) if best and best.get("exit_profile") is not None else None
                ),
                "best_exit_variant_id": (
                    str(best.get("exit_variant_id")) if best and best.get("exit_variant_id") is not None else None
                ),
                "best_filter_variant_id": (
                    str(best.get("filter_variant_id")) if best and best.get("filter_variant_id") is not None else None
                ),
                "best_status": str(best.get("status")) if best and best.get("status") is not None else None,
                "best_score": _as_float(best.get("score")) if best else None,
                "best_net_return_sum": _as_float(best.get("net_return_sum")) if best else None,
                "best_trade_count": _as_int(best.get("trade_count")) if best else None,
            }
            group_rows.append(row)
        group_rows = sorted(
            group_rows,
            key=lambda row: (
                -int(row["evidence_request_count"]),
                -int(row["screened_count"]),
                -int(row["positive_net_result_count"]),
                -(float(row["best_score"]) if row["best_score"] is not None else float("-inf")),
                int(row["best_rank"]) if row["best_rank"] is not None else 10**12,
                row["bucket_key"],
            ),
        )
        rollups.extend(group_rows[:limit_per_type])
    return rollups


def _rejection_reason_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    if "rejection_reasons" not in frame.columns:
        return counts
    for value in frame["rejection_reasons"]:
        reasons = _parse_json_cell(value, default=[])
        if not isinstance(reasons, list):
            continue
        for reason in reasons:
            key = str(reason)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _top_rows(frame: pd.DataFrame, *, top_n: int) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    sort_columns = [column for column in ("rank", "score", "net_return_sum") if column in frame.columns]
    top = frame.copy()
    if "rank" in top.columns:
        top = top.sort_values("rank", na_position="last")
    elif sort_columns:
        top = top.sort_values(sort_columns, ascending=[False] * len(sort_columns))
    keep_columns = [
        "rank",
        "trial_id",
        "hypothesis_id",
        "family",
        "venue",
        "symbol",
        "side",
        "holding_period",
        "exit_profile",
        "exit_variant_id",
        "filter_variant_id",
        "status",
        "score",
        "trade_count",
        "active_days",
        "net_return_sum",
        "win_rate",
        "max_drawdown",
        "rejection_reasons",
        "metadata",
    ]
    rows: list[dict[str, Any]] = []
    for record in top.head(top_n)[[column for column in keep_columns if column in top.columns]].to_dict(orient="records"):
        parsed = dict(record)
        parsed["rejection_reasons"] = _parse_json_cell(parsed.get("rejection_reasons"), default=[])
        parsed["metadata"] = _parse_json_cell(parsed.get("metadata"), default={})
        rows.append(parsed)
    return rows


def summarize_sandbox_run(
    run_dir: str | Path,
    *,
    top_n: int = 10,
    write_report: bool = True,
) -> dict[str, Any]:
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    run_path = Path(run_dir)
    manifest_path = run_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"sandbox run manifest not found: {manifest_path}")
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError("sandbox manifest must be a JSON object")
    require_sandbox_boundary(manifest, payload_name="sandbox_analysis_manifest")
    require_sandbox_artifact_integrity(run_path, payload_name="sandbox_analysis_source")

    rankings_path = _artifact_path(run_path, manifest, "rankings_parquet_path", "rankings.parquet")
    evidence_json_path = _artifact_path(run_path, manifest, "evidence_requests_json_path", "evidence_requests.json")
    rankings = pd.read_parquet(rankings_path)
    if not _boundary_columns_ok(rankings):
        raise ValueError("sandbox rankings parquet is missing required non-promotable boundary columns")
    evidence_requests = _load_json(evidence_json_path)
    if not isinstance(evidence_requests, list):
        raise ValueError("sandbox evidence_requests.json must contain a list")
    for request in evidence_requests:
        if isinstance(request, dict):
            require_sandbox_boundary(request, payload_name="sandbox_analysis_evidence_request")

    evidence_request_trial_ids = [
        str(request.get("source_trial_id"))
        for request in evidence_requests
        if isinstance(request, dict) and request.get("source_trial_id") is not None
    ]
    analysis_bucket_rollups = _analysis_bucket_rollups(rankings, evidence_request_trial_ids=evidence_request_trial_ids)

    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_analysis",
        "run_dir": str(run_path),
        "source_manifest_path": str(manifest_path),
        "rankings_parquet_path": str(rankings_path),
        "evidence_requests_json_path": str(evidence_json_path),
        "run_id": manifest.get("spec", {}).get("run_id") if isinstance(manifest.get("spec"), dict) else None,
        "result_count": int(len(rankings)),
        "status_counts": _value_counts(rankings, "status"),
        "venue_counts": _value_counts(rankings, "venue"),
        "family_counts": _value_counts(rankings, "family"),
        "exit_profile_counts": _value_counts(rankings, "exit_profile"),
        "filter_variant_counts": _value_counts(rankings, "filter_variant_id"),
        "venue_status_summary": _group_counts(rankings, ["venue", "status"]),
        "family_status_summary": _group_counts(rankings, ["family", "status"]),
        "exit_status_summary": _group_counts(rankings, ["exit_profile", "status"]),
        "rejection_reason_counts": _rejection_reason_counts(rankings),
        "analysis_bucket_rollup_version": SANDBOX_ANALYSIS_BUCKET_ROLLUP_VERSION,
        "analysis_bucket_rollup_limit_per_type": SANDBOX_ANALYSIS_BUCKET_ROLLUP_LIMIT_PER_TYPE,
        "analysis_bucket_rollup_count": len(analysis_bucket_rollups),
        "analysis_bucket_rollups": analysis_bucket_rollups,
        "market_sources": manifest.get("market_sources", []),
        "top_results": _top_rows(rankings, top_n=top_n),
        "evidence_request_count": int(len(evidence_requests)),
        "evidence_request_trial_ids": evidence_request_trial_ids,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_analysis_payload")
    if write_report:
        report_path = run_path / ANALYSIS_REPORT_NAME
        report_path.write_text(
            json.dumps({**payload, "analysis_report_path": str(report_path)}, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        payload["analysis_report_path"] = str(report_path)
    else:
        payload["analysis_report_path"] = None
    return payload
