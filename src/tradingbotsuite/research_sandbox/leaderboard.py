from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.discovery import bounded_discover_files
from tradingbotsuite.research_sandbox.integrity import require_sandbox_artifact_integrity


SANDBOX_GLOBAL_LEADERBOARD_JSON_NAME = "sandbox_global_leaderboard.json"
SANDBOX_GLOBAL_LEADERBOARD_PARQUET_NAME = "sandbox_global_leaderboard.parquet"
SANDBOX_GLOBAL_BUCKET_LEADERBOARD_PARQUET_NAME = "sandbox_global_bucket_leaderboard.parquet"
SANDBOX_GLOBAL_BUCKET_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("venue", ("venue",)),
    ("symbol", ("symbol",)),
    ("venue_symbol", ("venue", "symbol")),
    ("family", ("family",)),
    ("exit_profile", ("exit_profile",)),
    ("exit_variant", ("exit_variant_id",)),
    ("filter_variant", ("filter_variant_id",)),
    ("venue_family", ("venue", "family")),
)
SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_CONTEXT_LIMIT = 50


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


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


def _dict_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _boundary_columns_ok(frame: pd.DataFrame) -> bool:
    for column, expected in SANDBOX_BOUNDARY_FLAGS.items():
        if column not in frame.columns:
            return False
        if set(frame[column].dropna().astype(bool).unique()) != {expected}:
            return False
    return True


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
    raise FileNotFoundError(f"sandbox leaderboard missing artifact {key}: {fallback}")


def _safe_int(value: Any) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    return int(value)


def _safe_float(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    return float(value)


def _optional_scalar(value: Any) -> Any:
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


def _bucket_key(columns: tuple[str, ...], values: dict[str, Any]) -> str:
    parts: list[str] = []
    for column in columns:
        value = values.get(column)
        parts.append(f"{column}={'missing' if value is None else value}")
    return "|".join(parts)


def _unique_values(frame: pd.DataFrame, column: str) -> list[Any]:
    if column not in frame.columns:
        return []
    values: list[Any] = []
    for value in frame[column].dropna().tolist():
        item = value.item() if hasattr(value, "item") else value
        if item not in values:
            values.append(item)
    return sorted(values, key=lambda item: str(item))


def _reason_counts(frame: pd.DataFrame, *, status: str | None = None) -> dict[str, int]:
    if "rejection_reasons" not in frame.columns:
        return {}
    source = frame
    if status is not None and "status" in frame.columns:
        source = frame[frame["status"].fillna("missing").astype(str) == status]
    counts: dict[str, int] = {}
    for value in source["rejection_reasons"]:
        reasons = _parse_json_cell(value, default=[])
        if not isinstance(reasons, list):
            continue
        for reason in reasons:
            key = str(reason)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _request_trial_ids(evidence_requests: list[dict[str, Any]]) -> set[str]:
    return {
        str(request["source_trial_id"])
        for request in evidence_requests
        if isinstance(request, dict) and request.get("source_trial_id") is not None
    }


def _requests_by_trial_id(
    evidence_requests: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    requests_by_trial: dict[str, list[dict[str, Any]]] = {}
    for request in evidence_requests:
        if not isinstance(request, dict) or request.get("source_trial_id") is None:
            continue
        requests_by_trial.setdefault(str(request["source_trial_id"]), []).append(request)
    for requests in requests_by_trial.values():
        requests.sort(
            key=lambda request: (
                str(request.get("source_run_dir") or ""),
                str(request.get("source_manifest_path") or ""),
                str(request.get("request_id") or ""),
            )
        )
    return requests_by_trial


def _compact_market_source(market_source: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "routing_mode",
        "descriptor_id",
        "venue",
        "symbol",
        "data_family",
        "interval",
        "data_path",
        "shared_market_data_path",
        "container_kind",
        "selected_member_suffix",
        "selected_member_count",
        "loadable_member_count",
    )
    return {
        key: market_source.get(key)
        for key in keys
        if market_source.get(key) not in (None, "", [], {})
    }


def _evidence_request_source_context(request: dict[str, Any]) -> dict[str, Any]:
    source_trial_context = _dict_value(request.get("source_trial_context"))
    source_metrics = _dict_value(request.get("source_metrics"))
    market_source = _dict_value(source_trial_context.get("market_source"))
    compact_market_source = _compact_market_source(market_source)
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_global_evidence_request_source_context",
        "source_request_id": request.get("request_id"),
        "source_run_id": request.get("source_run_id")
        or source_trial_context.get("source_run_id"),
        "source_trial_id": request.get("source_trial_id")
        or source_trial_context.get("source_trial_id"),
        "source_run_dir": request.get("source_run_dir"),
        "source_manifest_path": request.get("source_manifest_path"),
        "source_requested_validation": request.get("requested_validation"),
        "source_required_evidence": _list_value(request.get("required_evidence")),
        "source_reason": request.get("reason"),
        "hypothesis_id": request.get("hypothesis_id")
        or source_trial_context.get("hypothesis_id"),
        "family": request.get("family") or source_trial_context.get("family"),
        "venue": request.get("venue") or source_trial_context.get("venue"),
        "symbol": request.get("symbol") or source_trial_context.get("symbol"),
        "data_family": source_trial_context.get("data_family"),
        "source_id": source_trial_context.get("source_id"),
        "side": source_trial_context.get("side"),
        "signal_column": source_trial_context.get("signal_column"),
        "holding_period": _safe_int(source_trial_context.get("holding_period")),
        "exit_profile": source_trial_context.get("exit_profile"),
        "exit_variant_id": source_trial_context.get("exit_variant_id"),
        "filter_variant_id": source_trial_context.get("filter_variant_id"),
        "source_market_start": source_trial_context.get("market_start"),
        "source_market_end": source_trial_context.get("market_end"),
        "source_status": source_trial_context.get("status"),
        "source_rejection_reasons": _list_value(
            source_trial_context.get("rejection_reasons")
        ),
        "source_metric_rank": _safe_int(source_metrics.get("rank")),
        "source_metric_score": _safe_float(source_metrics.get("score")),
        "source_metric_net_return_sum": _safe_float(
            source_metrics.get("net_return_sum")
        ),
        "source_metric_trade_count": _safe_int(source_metrics.get("trade_count")),
        "source_metric_active_days": _safe_int(source_metrics.get("active_days")),
        "source_venue_descriptor_id": source_trial_context.get(
            "venue_descriptor_id"
        )
        or market_source.get("descriptor_id"),
        "source_routing_mode": compact_market_source.get("routing_mode"),
        "source_data_path": compact_market_source.get("data_path"),
        "source_container_kind": compact_market_source.get("container_kind"),
        "source_selected_member_suffix": compact_market_source.get(
            "selected_member_suffix"
        ),
        "source_selected_member_count": _safe_int(
            compact_market_source.get("selected_member_count")
        ),
        "source_market_source": compact_market_source,
        "source_execution_assumptions": _dict_value(
            source_trial_context.get("execution_assumptions")
        ),
        "descriptor_only": True,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
    }
    require_sandbox_boundary(
        row,
        payload_name="sandbox_global_leaderboard_evidence_request_source_context",
    )
    return row


def _evidence_request_source_contexts(
    matching_request_ids: list[str],
    requests_by_trial_id: dict[str, list[dict[str, Any]]],
    *,
    limit: int = SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_CONTEXT_LIMIT,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for trial_id in matching_request_ids:
        matches = requests_by_trial_id.get(str(trial_id), [])
        if not matches:
            continue
        contexts.append(_evidence_request_source_context(matches[0]))
        if len(contexts) >= limit:
            break
    return contexts


def _discover_run_manifests(root_dir: Path, *, max_runs: int) -> tuple[list[Path], bool]:
    return bounded_discover_files(
        [root_dir],
        max_files=max_runs,
        missing_root_message="sandbox leaderboard root not found",
        accepted_names=("manifest.json",),
    )


def _load_run_rows(manifest_path: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    run_dir = manifest_path.parent
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"sandbox run manifest must be a JSON object: {manifest_path}")
    require_sandbox_boundary(manifest, payload_name="sandbox_leaderboard_manifest")
    if manifest.get("artifact_family") != "rapid_strategy_iteration_sandbox_run":
        return pd.DataFrame(), []
    require_sandbox_artifact_integrity(manifest_path, payload_name="sandbox_leaderboard_source")

    rankings_path = _artifact_path(run_dir, manifest, "rankings_parquet_path", "rankings.parquet")
    evidence_path = _artifact_path(run_dir, manifest, "evidence_requests_json_path", "evidence_requests.json")
    rankings = pd.read_parquet(rankings_path)
    if not _boundary_columns_ok(rankings):
        raise ValueError("sandbox rankings parquet is missing required non-promotable boundary columns")
    rankings = rankings.copy()
    run_id = manifest.get("spec", {}).get("run_id") if isinstance(manifest.get("spec"), dict) else None
    rankings["source_run_dir"] = str(run_dir)
    rankings["source_manifest_path"] = str(manifest_path)
    rankings["source_rankings_parquet_path"] = str(rankings_path)
    rankings["source_run_id"] = str(run_id) if run_id is not None else None

    evidence_payload = _load_json(evidence_path)
    if not isinstance(evidence_payload, list):
        raise ValueError("sandbox evidence_requests.json must contain a list")
    evidence_requests: list[dict[str, Any]] = []
    for request in evidence_payload:
        if not isinstance(request, dict):
            raise ValueError("sandbox evidence request entries must be objects")
        require_sandbox_boundary(request, payload_name="sandbox_leaderboard_evidence_request")
        enriched = dict(request)
        enriched["source_run_dir"] = str(run_dir)
        enriched["source_manifest_path"] = str(manifest_path)
        evidence_requests.append(enriched)
    return rankings, evidence_requests


def _best_row(group: pd.DataFrame) -> dict[str, Any]:
    if group.empty:
        return {}
    ordered = group.copy()
    sort_columns: list[str] = []
    ascending: list[bool] = []
    if "score" in ordered.columns:
        sort_columns.append("score")
        ascending.append(False)
    if "net_return_sum" in ordered.columns:
        sort_columns.append("net_return_sum")
        ascending.append(False)
    if "rank" in ordered.columns:
        sort_columns.append("rank")
        ascending.append(True)
    if sort_columns:
        ordered = ordered.sort_values(sort_columns, ascending=ascending, na_position="last")
    return ordered.iloc[0].to_dict()


def _decision(
    *,
    screened_count: int,
    rejected_count: int,
    blocked_count: int,
    request_ids: list[str],
) -> tuple[str, str]:
    if request_ids:
        return "request_strict_validation", "one_or_more_trials_emitted_sandbox_evidence_requests"
    if screened_count > 0:
        return "screened_positive_without_request", "screened_trials_exist_without_request_handoff"
    if blocked_count > 0 and rejected_count == 0:
        return "blocked_missing_inputs", "all_observed_trials_blocked_before_metric_evidence"
    if rejected_count > 0 and blocked_count == 0:
        return "falsified_in_sandbox", "all_observed_trials_failed_sandbox_screening"
    return "mixed_or_inconclusive", "observed_trials_have_mixed_or_insufficient_outcomes"


def _decision_rank(decision: str) -> int:
    order = {
        "request_strict_validation": 0,
        "screened_positive_without_request": 1,
        "mixed_or_inconclusive": 2,
        "falsified_in_sandbox": 3,
        "blocked_missing_inputs": 4,
    }
    return order.get(decision, 99)


def _leaderboard_rows(rankings: pd.DataFrame, evidence_requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if rankings.empty:
        return []
    request_ids = _request_trial_ids(evidence_requests)
    requests_by_trial_id = _requests_by_trial_id(evidence_requests)
    group_columns = [column for column in ("hypothesis_id", "family") if column in rankings.columns]
    if not group_columns:
        raise ValueError("sandbox rankings require hypothesis_id or family for global leaderboard")
    rows: list[dict[str, Any]] = []
    for group_key, group in rankings.groupby(group_columns, dropna=False):
        key_values = group_key if isinstance(group_key, tuple) else (group_key,)
        key = dict(zip(group_columns, key_values, strict=False))
        statuses = group["status"].fillna("missing").astype(str) if "status" in group.columns else pd.Series(dtype=str)
        screened_count = int((statuses == "screened").sum())
        rejected_count = int((statuses == "rejected").sum())
        blocked_count = int((statuses == "blocked").sum())
        trial_ids = {str(value) for value in group.get("trial_id", pd.Series(dtype=object)).dropna().tolist()}
        matching_requests = sorted(trial_ids.intersection(request_ids))
        request_source_contexts = _evidence_request_source_contexts(
            matching_requests,
            requests_by_trial_id,
        )
        decision, reason = _decision(
            screened_count=screened_count,
            rejected_count=rejected_count,
            blocked_count=blocked_count,
            request_ids=matching_requests,
        )
        best = _best_row(group)
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_global_leaderboard_row",
            "hypothesis_id": str(key.get("hypothesis_id", "missing")),
            "family": str(key.get("family", "missing")),
            "source_ids": _unique_values(group, "source_id"),
            "sides": _unique_values(group, "side"),
            "venues_tested": _unique_values(group, "venue"),
            "symbols_tested": _unique_values(group, "symbol"),
            "data_families_tested": _unique_values(group, "data_family"),
            "holding_periods_tested": _unique_values(group, "holding_period"),
            "exit_profiles_tested": _unique_values(group, "exit_profile"),
            "exit_variant_ids_tested": _unique_values(group, "exit_variant_id"),
            "filter_variant_ids_tested": _unique_values(group, "filter_variant_id"),
            "run_ids": _unique_values(group, "run_id"),
            "source_run_ids": _unique_values(group, "source_run_id"),
            "source_run_dirs": _unique_values(group, "source_run_dir"),
            "source_manifest_paths": _unique_values(group, "source_manifest_path"),
            "run_count": len(_unique_values(group, "source_run_dir")),
            "result_count": int(len(group)),
            "screened_count": screened_count,
            "rejected_count": rejected_count,
            "blocked_count": blocked_count,
            "best_trial_id": str(best.get("trial_id")) if best.get("trial_id") is not None else None,
            "best_run_id": str(best.get("run_id")) if best.get("run_id") is not None else None,
            "best_source_run_dir": str(best.get("source_run_dir")) if best.get("source_run_dir") is not None else None,
            "best_status": str(best.get("status")) if best.get("status") is not None else None,
            "best_rank": _safe_int(best.get("rank")),
            "best_score": _safe_float(best.get("score")),
            "best_net_return_sum": _safe_float(best.get("net_return_sum")),
            "best_trade_count": _safe_int(best.get("trade_count")),
            "best_active_days": _safe_int(best.get("active_days")),
            "best_win_rate": _safe_float(best.get("win_rate")),
            "best_max_drawdown": _safe_float(best.get("max_drawdown")),
            "best_venue": str(best.get("venue")) if best.get("venue") is not None else None,
            "best_symbol": str(best.get("symbol")) if best.get("symbol") is not None else None,
            "best_exit_variant_id": str(best.get("exit_variant_id")) if best.get("exit_variant_id") is not None else None,
            "best_filter_variant_id": str(best.get("filter_variant_id")) if best.get("filter_variant_id") is not None else None,
            "evidence_request_count": len(matching_requests),
            "evidence_request_trial_ids": matching_requests,
            "evidence_request_source_context_count": len(request_source_contexts),
            "evidence_request_source_context_limit": SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_CONTEXT_LIMIT,
            "evidence_request_source_contexts_truncated": len(matching_requests)
            > len(request_source_contexts),
            "evidence_request_source_contexts": request_source_contexts,
            "blocked_reason_counts": _reason_counts(group, status="blocked"),
            "rejected_reason_counts": _reason_counts(group, status="rejected"),
            "all_reason_counts": _reason_counts(group),
            "leaderboard_decision": decision,
            "decision_reason": reason,
        }
        require_sandbox_boundary(row, payload_name="sandbox_global_leaderboard_row")
        rows.append(row)

    rows = sorted(
        rows,
        key=lambda row: (
            _decision_rank(str(row["leaderboard_decision"])),
            -float(row["best_score"]),
            -int(row["run_count"]),
            str(row["hypothesis_id"]),
        ),
    )
    for index, row in enumerate(rows, start=1):
        row["leaderboard_rank"] = index
    return rows


def _positive_net_count(frame: pd.DataFrame) -> int:
    if "net_return_sum" not in frame.columns:
        return 0
    return int((pd.to_numeric(frame["net_return_sum"], errors="coerce") > 0.0).sum())


def _status_count(statuses: pd.Series, status: str) -> int:
    return int((statuses == status).sum())


def _bucket_leaderboard_rows(
    rankings: pd.DataFrame,
    evidence_requests: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if rankings.empty:
        return []
    request_ids = _request_trial_ids(evidence_requests)
    rows: list[dict[str, Any]] = []
    for bucket_type, columns in SANDBOX_GLOBAL_BUCKET_GROUPS:
        available = tuple(column for column in columns if column in rankings.columns)
        if len(available) != len(columns):
            continue
        for group_key, group in rankings.groupby(list(columns), dropna=False):
            key_values = group_key if isinstance(group_key, tuple) else (group_key,)
            bucket_values = {
                column: _optional_scalar(value)
                for column, value in zip(columns, key_values, strict=True)
            }
            statuses = (
                group["status"].fillna("missing").astype(str)
                if "status" in group.columns
                else pd.Series(dtype=str)
            )
            screened_count = _status_count(statuses, "screened")
            rejected_count = _status_count(statuses, "rejected")
            blocked_count = _status_count(statuses, "blocked")
            trial_ids = {
                str(value)
                for value in group.get("trial_id", pd.Series(dtype=object)).dropna().tolist()
            }
            matching_requests = sorted(trial_ids.intersection(request_ids))
            decision, reason = _decision(
                screened_count=screened_count,
                rejected_count=rejected_count,
                blocked_count=blocked_count,
                request_ids=matching_requests,
            )
            best = _best_row(group)
            row = {
                **sandbox_boundary_metadata(),
                "artifact_family": "rapid_strategy_iteration_sandbox_global_bucket_leaderboard_row",
                "bucket_type": bucket_type,
                "bucket_key": _bucket_key(columns, bucket_values),
                "bucket_columns": list(columns),
                "bucket_values": bucket_values,
                "hypotheses_tested": _unique_values(group, "hypothesis_id"),
                "families_tested": _unique_values(group, "family"),
                "venues_tested": _unique_values(group, "venue"),
                "symbols_tested": _unique_values(group, "symbol"),
                "exit_profiles_tested": _unique_values(group, "exit_profile"),
                "exit_variant_ids_tested": _unique_values(group, "exit_variant_id"),
                "filter_variant_ids_tested": _unique_values(group, "filter_variant_id"),
                "source_run_ids": _unique_values(group, "source_run_id"),
                "source_run_dirs": _unique_values(group, "source_run_dir"),
                "source_manifest_paths": _unique_values(group, "source_manifest_path"),
                "run_count": len(_unique_values(group, "source_run_dir")),
                "result_count": int(len(group)),
                "screened_count": screened_count,
                "rejected_count": rejected_count,
                "blocked_count": blocked_count,
                "positive_net_result_count": _positive_net_count(group),
                "best_trial_id": str(best.get("trial_id")) if best.get("trial_id") is not None else None,
                "best_run_id": str(best.get("run_id")) if best.get("run_id") is not None else None,
                "best_source_run_dir": (
                    str(best.get("source_run_dir")) if best.get("source_run_dir") is not None else None
                ),
                "best_status": str(best.get("status")) if best.get("status") is not None else None,
                "best_rank": _safe_int(best.get("rank")),
                "best_score": _safe_float(best.get("score")),
                "best_net_return_sum": _safe_float(best.get("net_return_sum")),
                "best_trade_count": _safe_int(best.get("trade_count")),
                "best_active_days": _safe_int(best.get("active_days")),
                "best_win_rate": _safe_float(best.get("win_rate")),
                "best_max_drawdown": _safe_float(best.get("max_drawdown")),
                "best_hypothesis_id": (
                    str(best.get("hypothesis_id")) if best.get("hypothesis_id") is not None else None
                ),
                "best_family": str(best.get("family")) if best.get("family") is not None else None,
                "best_venue": str(best.get("venue")) if best.get("venue") is not None else None,
                "best_symbol": str(best.get("symbol")) if best.get("symbol") is not None else None,
                "best_exit_profile": (
                    str(best.get("exit_profile")) if best.get("exit_profile") is not None else None
                ),
                "best_exit_variant_id": (
                    str(best.get("exit_variant_id")) if best.get("exit_variant_id") is not None else None
                ),
                "best_filter_variant_id": (
                    str(best.get("filter_variant_id")) if best.get("filter_variant_id") is not None else None
                ),
                "evidence_request_count": len(matching_requests),
                "evidence_request_trial_ids": matching_requests,
                "blocked_reason_counts": _reason_counts(group, status="blocked"),
                "rejected_reason_counts": _reason_counts(group, status="rejected"),
                "all_reason_counts": _reason_counts(group),
                "bucket_leaderboard_decision": decision,
                "decision_reason": reason,
                "strict_validation_authorized": False,
                "candidate_pack_write_authorized": False,
            }
            require_sandbox_boundary(
                row,
                payload_name="sandbox_global_bucket_leaderboard_row",
            )
            rows.append(row)

    rows = sorted(
        rows,
        key=lambda row: (
            _decision_rank(str(row["bucket_leaderboard_decision"])),
            -int(row["evidence_request_count"]),
            -int(row["screened_count"]),
            -int(row["positive_net_result_count"]),
            -float(row["best_score"]),
            -int(row["run_count"]),
            str(row["bucket_type"]),
            str(row["bucket_key"]),
        ),
    )
    for index, row in enumerate(rows, start=1):
        row["bucket_leaderboard_rank"] = index
    return rows


def build_sandbox_global_leaderboard(
    root_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    max_runs: int = 5000,
    top_n: int = 100,
    write_report: bool = True,
) -> dict[str, Any]:
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError(f"sandbox global leaderboard root not found: {root_path}")
    if not root_path.is_dir():
        raise ValueError(f"sandbox global leaderboard root must be a directory: {root_path}")
    root_path = root_path.resolve()
    manifests, truncated = _discover_run_manifests(root_path, max_runs=max_runs)
    ranking_frames: list[pd.DataFrame] = []
    evidence_requests: list[dict[str, Any]] = []
    skipped_manifests: list[str] = []
    for manifest_path in manifests:
        rankings, requests = _load_run_rows(manifest_path)
        if rankings.empty:
            skipped_manifests.append(str(manifest_path))
            continue
        ranking_frames.append(rankings)
        evidence_requests.extend(requests)

    rankings = pd.concat(ranking_frames, ignore_index=True) if ranking_frames else pd.DataFrame()
    rows = _leaderboard_rows(rankings, evidence_requests)
    bucket_rows = _bucket_leaderboard_rows(rankings, evidence_requests)
    decision_counts: dict[str, int] = {}
    for row in rows:
        decision = str(row["leaderboard_decision"])
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
    bucket_decision_counts: dict[str, int] = {}
    for row in bucket_rows:
        decision = str(row["bucket_leaderboard_decision"])
        bucket_decision_counts[decision] = bucket_decision_counts.get(decision, 0) + 1

    destination = Path(output_dir).resolve() if output_dir is not None else root_path
    json_path = destination / SANDBOX_GLOBAL_LEADERBOARD_JSON_NAME
    parquet_path = destination / SANDBOX_GLOBAL_LEADERBOARD_PARQUET_NAME
    bucket_parquet_path = destination / SANDBOX_GLOBAL_BUCKET_LEADERBOARD_PARQUET_NAME
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_global_leaderboard",
        "root_dir": str(root_path),
        "output_dir": str(destination),
        "leaderboard_json_path": str(json_path) if write_report else None,
        "leaderboard_parquet_path": str(parquet_path) if write_report else None,
        "bucket_leaderboard_parquet_path": str(bucket_parquet_path) if write_report else None,
        "max_runs": max_runs,
        "top_n": top_n,
        "truncated": truncated,
        "run_manifest_count": len(manifests),
        "source_run_count": len(ranking_frames),
        "skipped_manifest_count": len(skipped_manifests),
        "skipped_manifests": skipped_manifests,
        "result_count": int(len(rankings)),
        "hypothesis_count": len(rows),
        "bucket_count": len(bucket_rows),
        "evidence_request_count": len(evidence_requests),
        "decision_counts": dict(sorted(decision_counts.items())),
        "bucket_decision_counts": dict(sorted(bucket_decision_counts.items())),
        "top_hypotheses": rows[:top_n],
        "top_buckets": bucket_rows[:top_n],
    }
    require_sandbox_boundary(payload, payload_name="sandbox_global_leaderboard")
    if write_report:
        destination.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
        if frame.empty:
            frame = pd.DataFrame(
                columns=[
                    "hypothesis_id",
                    "leaderboard_decision",
                    "evidence_request_source_contexts",
                    *SANDBOX_BOUNDARY_FLAGS,
                ]
            )
        frame.to_parquet(parquet_path, index=False)
        bucket_frame = pd.DataFrame([_row_for_parquet(row) for row in bucket_rows])
        if bucket_frame.empty:
            bucket_frame = pd.DataFrame(
                columns=["bucket_type", "bucket_leaderboard_decision", *SANDBOX_BOUNDARY_FLAGS]
            )
        bucket_frame.to_parquet(bucket_parquet_path, index=False)
        json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
    return payload
