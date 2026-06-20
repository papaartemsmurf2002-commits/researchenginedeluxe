from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import require_sandbox_boundary, sandbox_boundary_metadata
from tradingbotsuite.research_sandbox.paths import resolve_manifest_child_path


SANDBOX_ARTIFACT_INTEGRITY_REPORT_JSON_NAME = "artifact_integrity_report.json"
SANDBOX_ARTIFACT_INTEGRITY_REPORT_PARQUET_NAME = "artifact_integrity_report.parquet"

_RUN_ARTIFACT_PATH_KEYS = {
    "summary_parquet": "summary_parquet_path",
    "rankings_parquet": "rankings_parquet_path",
    "evidence_requests_json": "evidence_requests_json_path",
    "evidence_requests_parquet": "evidence_requests_parquet_path",
}
_SUITE_ARTIFACT_PATH_KEYS = {
    "suite_index_json": "suite_index_json_path",
    "suite_index_parquet": "suite_index_parquet_path",
    "suite_evidence_requests_json": "suite_evidence_requests_json_path",
    "suite_evidence_requests_parquet": "suite_evidence_requests_parquet_path",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _file_integrity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "byte_size": path.stat().st_size}


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("sandbox artifact manifest must be a JSON object")
    return payload


def _resolve_existing_manifest(target: str | Path) -> Path:
    target_path = Path(target).expanduser()
    if not target_path.is_absolute():
        target_path = target_path.resolve()
    if target_path.is_file():
        return target_path.resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"sandbox artifact target not found: {target_path}")
    if not target_path.is_dir():
        raise ValueError(f"sandbox artifact target must be a directory or manifest file: {target_path}")
    candidates = [path for path in (target_path / "manifest.json", target_path / "suite_manifest.json") if path.exists()]
    if not candidates:
        raise FileNotFoundError(f"sandbox artifact manifest not found under: {target_path}")
    if len(candidates) > 1:
        raise ValueError(f"sandbox artifact target has multiple manifests: {target_path}")
    return candidates[0].resolve()


def _artifact_path_keys(manifest: Mapping[str, Any]) -> tuple[str, dict[str, str]]:
    artifact_family = str(manifest.get("artifact_family") or "")
    if artifact_family == "rapid_strategy_iteration_sandbox_run":
        return "run", _RUN_ARTIFACT_PATH_KEYS
    if artifact_family == "rapid_strategy_iteration_sandbox_suite_run":
        return "suite", _SUITE_ARTIFACT_PATH_KEYS
    raise ValueError(f"unsupported sandbox artifact manifest family: {artifact_family or '<missing>'}")


def _resolve_artifact_path(raw_path: Any, *, manifest_path: Path) -> Path:
    return resolve_manifest_child_path(
        raw_path,
        manifest_path=manifest_path,
        path_name="sandbox manifest child artifact path",
    )


def _metadata_value(metadata: Mapping[str, Any], key: str) -> Any:
    value = metadata.get(key)
    if value is None:
        return None
    if isinstance(value, str) and value == "":
        return None
    return value


def _expected_byte_size(value: Any, *, artifact_key: str, reasons: list[str]) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        reasons.append(f"invalid_expected_byte_size:{artifact_key}")
        return None


def _integrity_row(
    *,
    source_scope: str,
    source_manifest_path: Path,
    artifact_key: str,
    artifact_path_key: str,
    artifacts: Mapping[str, Any],
    integrity_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    expected_metadata = integrity_metadata.get(artifact_key)
    if not isinstance(expected_metadata, Mapping):
        expected_metadata = {}
        reasons.append(f"missing_integrity_metadata:{artifact_key}")

    expected_sha256 = _metadata_value(expected_metadata, "sha256")
    expected_byte_size = _metadata_value(expected_metadata, "byte_size")
    if expected_sha256 is None:
        reasons.append(f"missing_expected_sha256:{artifact_key}")
    if expected_byte_size is None:
        reasons.append(f"missing_expected_byte_size:{artifact_key}")
    expected_byte_size_int = _expected_byte_size(expected_byte_size, artifact_key=artifact_key, reasons=reasons)

    raw_artifact_path = artifacts.get(artifact_path_key)
    artifact_path: Path | None = None
    actual_sha256: str | None = None
    actual_byte_size: int | None = None
    if raw_artifact_path is None or raw_artifact_path == "":
        reasons.append(f"missing_artifact_path:{artifact_path_key}")
    else:
        try:
            artifact_path = _resolve_artifact_path(raw_artifact_path, manifest_path=source_manifest_path)
        except ValueError:
            reasons.append(f"artifact_path_outside_manifest_dir:{artifact_key}")
        else:
            if not artifact_path.exists() or not artifact_path.is_file():
                reasons.append(f"missing_artifact_file:{artifact_key}")
            else:
                actual_integrity = _file_integrity(artifact_path)
                actual_sha256 = str(actual_integrity["sha256"])
                actual_byte_size = int(actual_integrity["byte_size"])
                if expected_sha256 is not None and str(expected_sha256) != actual_sha256:
                    reasons.append(f"sha256_mismatch:{artifact_key}")
                if expected_byte_size_int is not None and expected_byte_size_int != actual_byte_size:
                    reasons.append(f"byte_size_mismatch:{artifact_key}")

    has_mismatch = any(reason.startswith(("sha256_mismatch", "byte_size_mismatch")) for reason in reasons)
    status = "matched" if not reasons else "mismatched" if has_mismatch else "missing"
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_integrity_row",
        "source_scope": source_scope,
        "source_manifest_path": str(source_manifest_path),
        "artifact_key": artifact_key,
        "artifact_path_key": artifact_path_key,
        "artifact_path": str(artifact_path) if artifact_path is not None else None,
        "expected_sha256": str(expected_sha256) if expected_sha256 is not None else None,
        "actual_sha256": actual_sha256,
        "expected_byte_size": expected_byte_size_int,
        "actual_byte_size": actual_byte_size,
        "status": status,
        "reasons": reasons,
    }
    require_sandbox_boundary(row, payload_name="sandbox_artifact_integrity_row")
    return row


def verify_sandbox_artifact_integrity(
    target: str | Path,
    *,
    output_dir: str | Path | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    manifest_path = _resolve_existing_manifest(target)
    manifest = _load_json_object(manifest_path)
    require_sandbox_boundary(manifest, payload_name="sandbox_artifact_integrity_source_manifest")
    source_scope, artifact_path_keys = _artifact_path_keys(manifest)

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        artifacts = {}
    integrity_metadata = manifest.get("artifact_integrity")
    if not isinstance(integrity_metadata, Mapping):
        integrity_metadata = {}

    rows = [
        _integrity_row(
            source_scope=source_scope,
            source_manifest_path=manifest_path,
            artifact_key=artifact_key,
            artifact_path_key=artifact_path_key,
            artifacts=artifacts,
            integrity_metadata=integrity_metadata,
        )
        for artifact_key, artifact_path_key in artifact_path_keys.items()
    ]
    matched_count = sum(1 for row in rows if row["status"] == "matched")
    mismatched_count = sum(1 for row in rows if row["status"] == "mismatched")
    missing_count = sum(1 for row in rows if row["status"] == "missing")
    report_dir = Path(output_dir).expanduser() if output_dir is not None else manifest_path.parent
    if output_dir is not None and not report_dir.is_absolute():
        report_dir = report_dir.resolve()

    report_json_path = report_dir / SANDBOX_ARTIFACT_INTEGRITY_REPORT_JSON_NAME
    report_parquet_path = report_dir / SANDBOX_ARTIFACT_INTEGRITY_REPORT_PARQUET_NAME
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_integrity_verification",
        "source_scope": source_scope,
        "source_manifest_path": str(manifest_path),
        "source_dir": str(manifest_path.parent),
        "verification_status": "passed" if matched_count == len(rows) else "failed",
        "checked_artifact_count": len(rows),
        "verified_artifact_count": matched_count,
        "mismatched_artifact_count": mismatched_count,
        "missing_artifact_count": missing_count,
        "failed_artifact_count": mismatched_count + missing_count,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "report_written": bool(write_report),
        "report_json_path": str(report_json_path) if write_report else None,
        "report_parquet_path": str(report_parquet_path) if write_report else None,
        "rows": rows,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_artifact_integrity_report")

    if write_report:
        report_dir.mkdir(parents=True, exist_ok=True)
        report_json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        report_frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
        if report_frame.empty:
            report_frame = pd.DataFrame(columns=["artifact_key", "status"])
        report_frame.to_parquet(report_parquet_path, index=False)
    return payload


def require_sandbox_artifact_integrity(
    target: str | Path,
    *,
    payload_name: str = "sandbox_artifact_source",
) -> dict[str, Any]:
    report = verify_sandbox_artifact_integrity(target, write_report=False)
    if report.get("verification_status") == "passed":
        return report

    failed_keys: list[str] = []
    failed_reasons: list[str] = []
    for row in report.get("rows", []):
        if not isinstance(row, Mapping) or row.get("status") == "matched":
            continue
        artifact_key = row.get("artifact_key")
        if artifact_key is not None:
            failed_keys.append(str(artifact_key))
        reasons = row.get("reasons", [])
        if isinstance(reasons, list):
            failed_reasons.extend(str(reason) for reason in reasons)

    key_detail = ",".join(sorted(set(failed_keys))) or "unknown_artifact"
    reason_detail = ",".join(sorted(set(failed_reasons))) or "integrity_verification_failed"
    raise ValueError(
        f"{payload_name} failed sandbox artifact integrity: "
        f"failed_artifacts={key_detail}; reasons={reason_detail}"
    )
