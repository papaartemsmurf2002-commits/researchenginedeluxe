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
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.integrity import require_sandbox_artifact_integrity


STRICT_VALIDATION_REQUEST_BUNDLE_JSON_NAME = "strict_validation_request_bundle.json"
STRICT_VALIDATION_REQUEST_BUNDLE_PARQUET_NAME = "strict_validation_request_bundle.parquet"
SUITE_STRICT_VALIDATION_REQUEST_BUNDLE_JSON_NAME = "suite_strict_validation_request_bundle.json"
SUITE_STRICT_VALIDATION_REQUEST_BUNDLE_PARQUET_NAME = "suite_strict_validation_request_bundle.parquet"
STRICT_VALIDATION_COMMAND = "run-historical-research-cycle"
STRICT_VALIDATION_ENTRYPOINT = "existing_historical_research_cycle"
DESCRIPTOR_EXECUTION_MODE = "descriptor_only_no_execution"


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
    raise FileNotFoundError(f"sandbox validation bundle missing artifact {key}: {fallback}")


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _as_dict_list(payload: Any, *, payload_name: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError(f"{payload_name} must contain a list")
    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"{payload_name} entries must be objects")
        require_sandbox_boundary(item, payload_name=payload_name)
        rows.append(dict(item))
    return rows


def _request_sort_key(request: dict[str, Any]) -> tuple[float, int, str]:
    metrics = request.get("source_metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    score = float(metrics.get("score", 0.0) or 0.0)
    rank = int(metrics.get("rank", 10**9) or 10**9)
    request_id = str(request.get("request_id", ""))
    return (-score, rank, request_id)


def _dedupe_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for request in sorted(requests, key=_request_sort_key):
        key_payload = {
            "requested_validation": request.get("requested_validation"),
            "source_run_id": request.get("source_run_id"),
            "source_trial_id": request.get("source_trial_id"),
            "hypothesis_id": request.get("hypothesis_id"),
            "venue": request.get("venue"),
            "symbol": request.get("symbol"),
        }
        key = digest_payload(key_payload, prefix="sbxhandoffkey", length=24)
        if key not in deduped:
            deduped[key] = {**request, "dedupe_key": key}
    return list(deduped.values())


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _market_source_container_fields(source_market_source: dict[str, Any]) -> dict[str, Any]:
    container_metadata = source_market_source.get("container_member_metadata", {}) or {}
    if not isinstance(container_metadata, dict):
        container_metadata = {}

    def source_value(key: str, default: Any = None) -> Any:
        if key in source_market_source:
            return source_market_source.get(key)
        return container_metadata.get(key, default)

    selected_sample = source_value("selected_member_name_sample", [])
    if not isinstance(selected_sample, (list, tuple)):
        selected_sample = []
    suffix_counts = source_value("available_member_suffix_counts", {})
    if not isinstance(suffix_counts, dict):
        suffix_counts = {}
    return {
        "source_container_member_metadata": container_metadata,
        "source_container_kind": source_value("container_kind"),
        "source_selected_member_suffix": source_value("selected_member_suffix"),
        "source_selected_member_count": _safe_int(source_value("selected_member_count")),
        "source_selected_member_name_sample": [str(name) for name in selected_sample],
        "source_selected_member_names_truncated": bool(source_value("selected_member_names_truncated", False)),
        "source_available_member_suffix_counts": {str(key): _safe_int(value) for key, value in suffix_counts.items()},
        "source_available_member_suffix_count": _safe_int(source_value("available_member_suffix_count")),
        "source_loadable_member_count": _safe_int(source_value("loadable_member_count")),
    }


def _descriptor_row(
    request: dict[str, Any],
    *,
    bundle_id: str,
    source_scope: str,
    source_dir: Path,
    source_manifest_path: Path,
) -> dict[str, Any]:
    required_evidence = request.get("required_evidence", [])
    if not isinstance(required_evidence, list):
        required_evidence = []
    source_metrics = request.get("source_metrics", {})
    if not isinstance(source_metrics, dict):
        source_metrics = {}
    source_trial_context = request.get("source_trial_context", {})
    if not isinstance(source_trial_context, dict):
        source_trial_context = {}
    source_market_source = source_trial_context.get("market_source", {})
    if not isinstance(source_market_source, dict):
        source_market_source = {}
    source_container_fields = _market_source_container_fields(source_market_source)
    descriptor_identity = {
        "bundle_id": bundle_id,
        "dedupe_key": request.get("dedupe_key"),
        "source_request_id": request.get("request_id"),
        "source_trial_id": request.get("source_trial_id"),
        "requested_validation": request.get("requested_validation"),
    }
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "sandbox_strict_validation_request_descriptor",
        "bundle_id": bundle_id,
        "descriptor_id": digest_payload(descriptor_identity, prefix="sbxstrict", length=24),
        "dedupe_key": request.get("dedupe_key"),
        "source_scope": source_scope,
        "source_dir": str(source_dir),
        "source_manifest_path": str(source_manifest_path),
        "source_request_id": request.get("request_id"),
        "source_run_id": request.get("source_run_id"),
        "source_trial_id": request.get("source_trial_id"),
        "suite_id": request.get("suite_id"),
        "case_id": request.get("case_id"),
        "hypothesis_id": request.get("hypothesis_id"),
        "family": request.get("family"),
        "venue": request.get("venue"),
        "symbol": request.get("symbol"),
        "reason": request.get("reason"),
        "requested_validation": request.get("requested_validation", "strict_research_cycle_request"),
        "strict_validation_entrypoint": STRICT_VALIDATION_ENTRYPOINT,
        "strict_validation_command": STRICT_VALIDATION_COMMAND,
        "execution_mode": DESCRIPTOR_EXECUTION_MODE,
        "descriptor_only": True,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "required_evidence": required_evidence,
        "source_metrics": source_metrics,
        "source_trial_context": source_trial_context,
        "source_venue_descriptor_id": source_trial_context.get("venue_descriptor_id"),
        "source_market_start": source_trial_context.get("market_start"),
        "source_market_end": source_trial_context.get("market_end"),
        "source_market_source": source_market_source,
        **source_container_fields,
        "source_run_dir": request.get("source_run_dir"),
        "source_request_payload": request,
    }
    require_sandbox_boundary(row, payload_name="sandbox_strict_validation_request_descriptor")
    return row


def _write_bundle(
    *,
    requests: list[dict[str, Any]],
    source_scope: str,
    source_dir: Path,
    source_manifest_path: Path,
    output_dir: Path,
    json_name: str,
    parquet_name: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for request in requests:
        require_sandbox_boundary(request, payload_name="sandbox_validation_bundle_source_request")
    deduped = _dedupe_requests(requests)
    bundle_id = digest_payload(
        {
            "source_scope": source_scope,
            "source_manifest_path": str(source_manifest_path),
            "request_ids": sorted(str(request.get("request_id")) for request in deduped),
        },
        prefix="sbxstrictbundle",
        length=24,
    )
    rows = [
        _descriptor_row(
            request,
            bundle_id=bundle_id,
            source_scope=source_scope,
            source_dir=source_dir,
            source_manifest_path=source_manifest_path,
        )
        for request in deduped
    ]
    json_path = output_dir / json_name
    parquet_path = output_dir / parquet_name
    frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=["bundle_id", "descriptor_id", "source_request_id", *SANDBOX_BOUNDARY_FLAGS])
    frame.to_parquet(parquet_path, index=False)
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_strict_validation_request_bundle",
        "bundle_id": bundle_id,
        "source_scope": source_scope,
        "source_dir": str(source_dir),
        "source_manifest_path": str(source_manifest_path),
        "strict_validation_entrypoint": STRICT_VALIDATION_ENTRYPOINT,
        "strict_validation_command": STRICT_VALIDATION_COMMAND,
        "execution_mode": DESCRIPTOR_EXECUTION_MODE,
        "descriptor_only": True,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "request_count": len(requests),
        "deduped_request_count": len(rows),
        "duplicates_removed": len(requests) - len(rows),
        "bundle_json_path": str(json_path),
        "bundle_parquet_path": str(parquet_path),
        "descriptors": rows,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_strict_validation_request_bundle")
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return payload


def export_sandbox_validation_request_bundle(
    run_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    run_path = Path(run_dir)
    manifest_path = run_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"sandbox run manifest not found: {manifest_path}")
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError("sandbox run manifest must be a JSON object")
    require_sandbox_boundary(manifest, payload_name="sandbox_validation_bundle_manifest")
    require_sandbox_artifact_integrity(run_path, payload_name="sandbox_validation_bundle_source")
    requests_path = _artifact_path(run_path, manifest, "evidence_requests_json_path", "evidence_requests.json")
    requests = _as_dict_list(_load_json(requests_path), payload_name="sandbox_validation_bundle_evidence_requests")
    return _write_bundle(
        requests=requests,
        source_scope="run",
        source_dir=run_path,
        source_manifest_path=manifest_path,
        output_dir=Path(output_dir) if output_dir is not None else run_path,
        json_name=STRICT_VALIDATION_REQUEST_BUNDLE_JSON_NAME,
        parquet_name=STRICT_VALIDATION_REQUEST_BUNDLE_PARQUET_NAME,
    )


def export_sandbox_suite_validation_request_bundle(
    suite_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    suite_path = Path(suite_dir)
    manifest_path = suite_path / "suite_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"sandbox suite manifest not found: {manifest_path}")
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError("sandbox suite manifest must be a JSON object")
    require_sandbox_boundary(manifest, payload_name="sandbox_suite_validation_bundle_manifest")
    require_sandbox_artifact_integrity(suite_path, payload_name="sandbox_suite_validation_bundle_source")
    requests_path = _artifact_path(suite_path, manifest, "suite_evidence_requests_json_path", "suite_evidence_requests.json")
    requests = _as_dict_list(_load_json(requests_path), payload_name="sandbox_suite_validation_bundle_evidence_requests")
    return _write_bundle(
        requests=requests,
        source_scope="suite",
        source_dir=suite_path,
        source_manifest_path=manifest_path,
        output_dir=Path(output_dir) if output_dir is not None else suite_path,
        json_name=SUITE_STRICT_VALIDATION_REQUEST_BUNDLE_JSON_NAME,
        parquet_name=SUITE_STRICT_VALIDATION_REQUEST_BUNDLE_PARQUET_NAME,
    )
