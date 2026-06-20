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
from tradingbotsuite.research_sandbox.integrity import require_sandbox_artifact_integrity


HYPOTHESIS_FALSIFICATION_JSON_NAME = "hypothesis_falsification.json"
HYPOTHESIS_FALSIFICATION_PARQUET_NAME = "hypothesis_falsification.parquet"
SUITE_HYPOTHESIS_FALSIFICATION_JSON_NAME = "suite_hypothesis_falsification.json"
SUITE_HYPOTHESIS_FALSIFICATION_PARQUET_NAME = "suite_hypothesis_falsification.parquet"


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_path(base_dir: Path, manifest: dict[str, Any], key: str, fallback_name: str) -> Path:
    artifacts = manifest.get("artifacts", {})
    raw = artifacts.get(key) if isinstance(artifacts, dict) else None
    if raw:
        candidate = Path(str(raw))
        if not candidate.is_absolute():
            candidate = base_dir / candidate
        if candidate.exists():
            return candidate
    fallback = base_dir / fallback_name
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"sandbox falsification missing artifact {key}: {fallback}")


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


def _boundary_columns_ok(frame: pd.DataFrame) -> bool:
    for column, expected in SANDBOX_BOUNDARY_FLAGS.items():
        if column not in frame.columns:
            return False
        if set(frame[column].dropna().astype(bool).unique()) != {expected}:
            return False
    return True


def _safe_int(value: Any) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    return int(value)


def _safe_float(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    return float(value)


def _unique_values(frame: pd.DataFrame, column: str) -> list[Any]:
    if column not in frame.columns:
        return []
    values: list[Any] = []
    for value in frame[column].dropna().tolist():
        item = value.item() if hasattr(value, "item") else value
        if item not in values:
            values.append(item)
    return sorted(values, key=lambda item: str(item))


def _count_reasons(frame: pd.DataFrame, *, status: str | None = None) -> dict[str, int]:
    if "rejection_reasons" not in frame.columns:
        return {}
    source = frame if status is None or "status" not in frame.columns else frame[frame["status"].astype(str) == status]
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


def _load_run_inputs(
    run_dir: str | Path,
    *,
    suite_id: str | None = None,
    case_id: str | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    run_path = Path(run_dir)
    manifest_path = run_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"sandbox run manifest not found: {manifest_path}")
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError("sandbox run manifest must be a JSON object")
    require_sandbox_boundary(manifest, payload_name="sandbox_falsification_manifest")
    require_sandbox_artifact_integrity(run_path, payload_name="sandbox_falsification_source")

    rankings_path = _artifact_path(run_path, manifest, "rankings_parquet_path", "rankings.parquet")
    evidence_json_path = _artifact_path(run_path, manifest, "evidence_requests_json_path", "evidence_requests.json")
    rankings = pd.read_parquet(rankings_path)
    if not _boundary_columns_ok(rankings):
        raise ValueError("sandbox rankings parquet is missing required non-promotable boundary columns")
    rankings = rankings.copy()
    rankings["source_run_dir"] = str(run_path)
    rankings["source_manifest_path"] = str(manifest_path)
    if suite_id is not None:
        rankings["suite_id"] = suite_id
    if case_id is not None:
        rankings["case_id"] = case_id

    evidence_payload = _load_json(evidence_json_path)
    if not isinstance(evidence_payload, list):
        raise ValueError("sandbox evidence_requests.json must contain a list")
    evidence_requests: list[dict[str, Any]] = []
    for request in evidence_payload:
        if not isinstance(request, dict):
            raise ValueError("sandbox evidence request entries must be objects")
        require_sandbox_boundary(request, payload_name="sandbox_falsification_evidence_request")
        enriched = dict(request)
        if suite_id is not None:
            enriched["suite_id"] = suite_id
        if case_id is not None:
            enriched["case_id"] = case_id
        enriched["source_run_dir"] = str(run_path)
        enriched["source_manifest_path"] = str(manifest_path)
        evidence_requests.append(enriched)
    return manifest, rankings, evidence_requests


def _best_row(group: pd.DataFrame) -> dict[str, Any]:
    ordered = group.copy()
    if "rank" in ordered.columns:
        ordered = ordered.sort_values("rank", na_position="last")
    elif "score" in ordered.columns:
        ordered = ordered.sort_values("score", ascending=False)
    return ordered.iloc[0].to_dict() if not ordered.empty else {}


def _decision(*, screened_count: int, rejected_count: int, blocked_count: int, request_ids: list[str]) -> tuple[str, str]:
    if request_ids:
        return "request_strict_validation", "one_or_more_screened_trials_emitted_sandbox_evidence_requests"
    if blocked_count > 0 and rejected_count == 0 and screened_count == 0:
        return "blocked_missing_inputs", "all_trials_blocked_before_sandbox_metric_evidence"
    if rejected_count > 0 and blocked_count == 0 and screened_count == 0:
        return "falsified_in_sandbox", "all_completed_trials_failed_sandbox_screening"
    if screened_count > 0:
        return "screened_positive_without_request", "screened_trials_exist_but_request_threshold_or_limit_blocked_handoff"
    return "mixed_or_inconclusive", "sandbox_trials_have_mixed_or_insufficient_outcomes"


def _hypothesis_rows(
    rankings: pd.DataFrame,
    *,
    evidence_requests: list[dict[str, Any]],
    scope: str,
    suite_id: str | None = None,
) -> list[dict[str, Any]]:
    if rankings.empty:
        return []
    request_ids = _request_trial_ids(evidence_requests)
    group_columns = [column for column in ("hypothesis_id", "family") if column in rankings.columns]
    if not group_columns:
        raise ValueError("sandbox rankings require hypothesis_id or family for falsification")
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
        decision, reason = _decision(
            screened_count=screened_count,
            rejected_count=rejected_count,
            blocked_count=blocked_count,
            request_ids=matching_requests,
        )
        best = _best_row(group)
        row = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_hypothesis_falsification_row",
            "scope": scope,
            "suite_id": suite_id,
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
            "case_ids": _unique_values(group, "case_id"),
            "run_ids": _unique_values(group, "run_id"),
            "source_run_dirs": _unique_values(group, "source_run_dir"),
            "result_count": int(len(group)),
            "screened_count": screened_count,
            "rejected_count": rejected_count,
            "blocked_count": blocked_count,
            "best_trial_id": str(best.get("trial_id")) if best.get("trial_id") is not None else None,
            "best_rank": _safe_int(best.get("rank")),
            "best_status": str(best.get("status")) if best.get("status") is not None else None,
            "best_score": _safe_float(best.get("score")),
            "best_net_return_sum": _safe_float(best.get("net_return_sum")),
            "best_trade_count": _safe_int(best.get("trade_count")),
            "best_active_days": _safe_int(best.get("active_days")),
            "best_venue": str(best.get("venue")) if best.get("venue") is not None else None,
            "best_symbol": str(best.get("symbol")) if best.get("symbol") is not None else None,
            "best_exit_variant_id": str(best.get("exit_variant_id")) if best.get("exit_variant_id") is not None else None,
            "best_filter_variant_id": str(best.get("filter_variant_id")) if best.get("filter_variant_id") is not None else None,
            "evidence_request_count": len(matching_requests),
            "evidence_request_trial_ids": matching_requests,
            "blocked_reason_counts": _count_reasons(group, status="blocked"),
            "rejected_reason_counts": _count_reasons(group, status="rejected"),
            "all_reason_counts": _count_reasons(group),
            "falsification_decision": decision,
            "decision_reason": reason,
        }
        require_sandbox_boundary(row, payload_name="sandbox_hypothesis_falsification_row")
        rows.append(row)
    return sorted(rows, key=lambda row: (_decision_rank(str(row["falsification_decision"])), -float(row["best_score"]), str(row["hypothesis_id"])))


def _decision_rank(decision: str) -> int:
    order = {
        "request_strict_validation": 0,
        "screened_positive_without_request": 1,
        "mixed_or_inconclusive": 2,
        "falsified_in_sandbox": 3,
        "blocked_missing_inputs": 4,
    }
    return order.get(decision, 99)


def _decision_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("falsification_decision", "missing"))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (_decision_rank(item[0]), item[0])))


def _write_report(
    *,
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
    json_path: Path,
    parquet_path: Path,
) -> dict[str, Any]:
    for row in rows:
        require_sandbox_boundary(row, payload_name="sandbox_hypothesis_falsification_row")
    frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=["hypothesis_id", "falsification_decision", *SANDBOX_BOUNDARY_FLAGS])
    frame.to_parquet(parquet_path, index=False)
    final_payload = {**payload, "hypothesis_falsification_parquet_path": str(parquet_path)}
    final_payload["hypotheses"] = rows
    require_sandbox_boundary(final_payload, payload_name="sandbox_hypothesis_falsification_payload")
    json_path.write_text(
        json.dumps({**final_payload, "hypothesis_falsification_json_path": str(json_path)}, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    final_payload["hypothesis_falsification_json_path"] = str(json_path)
    return final_payload


def summarize_sandbox_hypotheses(
    run_dir: str | Path,
    *,
    write_report: bool = True,
) -> dict[str, Any]:
    run_path = Path(run_dir)
    manifest, rankings, evidence_requests = _load_run_inputs(run_path)
    rows = _hypothesis_rows(rankings, evidence_requests=evidence_requests, scope="run")
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_hypothesis_falsification",
        "scope": "run",
        "run_dir": str(run_path),
        "source_manifest_path": str(run_path / "manifest.json"),
        "run_id": manifest.get("spec", {}).get("run_id") if isinstance(manifest.get("spec"), dict) else None,
        "result_count": int(len(rankings)),
        "hypothesis_count": len(rows),
        "decision_counts": _decision_counts(rows),
        "evidence_request_count": len(evidence_requests),
        "hypotheses": rows,
        "hypothesis_falsification_json_path": None,
        "hypothesis_falsification_parquet_path": None,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_hypothesis_falsification_payload")
    if not write_report:
        return payload
    return _write_report(
        payload=payload,
        rows=rows,
        json_path=run_path / HYPOTHESIS_FALSIFICATION_JSON_NAME,
        parquet_path=run_path / HYPOTHESIS_FALSIFICATION_PARQUET_NAME,
    )


def _suite_index_rows(suite_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    index_path = _artifact_path(suite_dir, manifest, "suite_index_json_path", "suite_index.json")
    payload = _load_json(index_path)
    if not isinstance(payload, dict):
        raise ValueError("sandbox suite index must be a JSON object")
    require_sandbox_boundary(payload, payload_name="sandbox_suite_falsification_index")
    rows = payload.get("cases")
    if not isinstance(rows, list):
        raise ValueError("sandbox suite index requires cases list")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("sandbox suite index case rows must be objects")
        require_sandbox_boundary(row, payload_name="sandbox_suite_falsification_index_row")
    return rows


def summarize_sandbox_suite_hypotheses(
    suite_dir: str | Path,
    *,
    write_report: bool = True,
) -> dict[str, Any]:
    suite_path = Path(suite_dir)
    manifest_path = suite_path / "suite_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"sandbox suite manifest not found: {manifest_path}")
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError("sandbox suite manifest must be a JSON object")
    require_sandbox_boundary(manifest, payload_name="sandbox_suite_falsification_manifest")
    require_sandbox_artifact_integrity(suite_path, payload_name="sandbox_suite_falsification_source")
    suite_spec = manifest.get("suite_spec", {})
    suite_id = str(suite_spec.get("suite_id")) if isinstance(suite_spec, dict) and suite_spec.get("suite_id") is not None else None

    frames: list[pd.DataFrame] = []
    evidence_requests: list[dict[str, Any]] = []
    skipped_case_count = 0
    for row in _suite_index_rows(suite_path, manifest):
        run_dir = row.get("run_dir")
        case_id = row.get("case_id")
        if run_dir is None:
            if row.get("case_status") == "blocked_by_preflight":
                skipped_case_count += 1
                continue
            raise ValueError("sandbox suite index row missing run_dir")
        _run_manifest, rankings, requests = _load_run_inputs(run_dir, suite_id=suite_id, case_id=str(case_id) if case_id is not None else None)
        frames.append(rankings)
        evidence_requests.extend(requests)
    rankings = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    rows = _hypothesis_rows(rankings, evidence_requests=evidence_requests, scope="suite", suite_id=suite_id)
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_suite_hypothesis_falsification",
        "scope": "suite",
        "suite_id": suite_id,
        "suite_dir": str(suite_path),
        "source_suite_manifest_path": str(manifest_path),
        "case_count": int(manifest.get("case_count", 0)),
        "skipped_case_count": skipped_case_count,
        "source_run_count": len(frames),
        "result_count": int(len(rankings)),
        "hypothesis_count": len(rows),
        "decision_counts": _decision_counts(rows),
        "evidence_request_count": len(evidence_requests),
        "hypotheses": rows,
        "hypothesis_falsification_json_path": None,
        "hypothesis_falsification_parquet_path": None,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_suite_hypothesis_falsification_payload")
    if not write_report:
        return payload
    return _write_report(
        payload=payload,
        rows=rows,
        json_path=suite_path / SUITE_HYPOTHESIS_FALSIFICATION_JSON_NAME,
        parquet_path=suite_path / SUITE_HYPOTHESIS_FALSIFICATION_PARQUET_NAME,
    )
