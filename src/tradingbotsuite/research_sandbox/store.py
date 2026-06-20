from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import require_sandbox_boundary, sandbox_boundary_metadata
from tradingbotsuite.research_sandbox.evidence_request import EvidenceRequestDescriptor
from tradingbotsuite.research_sandbox.fast_backtest import TrialResult
from tradingbotsuite.research_sandbox.paths import resolve_under_root
from tradingbotsuite.research_sandbox.spec import SandboxRunSpec, StrategyCatalogRow, VenueArchiveDescriptor


@dataclass(frozen=True)
class SandboxArtifacts:
    run_dir: Path
    manifest_path: Path
    summary_parquet_path: Path
    rankings_parquet_path: Path
    evidence_requests_json_path: Path
    evidence_requests_parquet_path: Path

    def to_payload(self) -> dict[str, str]:
        return {
            "run_dir": str(self.run_dir),
            "manifest_path": str(self.manifest_path),
            "summary_parquet_path": str(self.summary_parquet_path),
            "rankings_parquet_path": str(self.rankings_parquet_path),
            "evidence_requests_json_path": str(self.evidence_requests_json_path),
            "evidence_requests_parquet_path": str(self.evidence_requests_parquet_path),
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


def _market_sources_from_results(results: list[TrialResult]) -> list[dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for result in results:
        source = result.metadata.get("market_source")
        if not isinstance(source, dict):
            continue
        key = json.dumps(source, sort_keys=True, default=_json_default)
        sources[key] = source
    return [sources[key] for key in sorted(sources)]


def _file_integrity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "byte_size": path.stat().st_size}


class ResultStore:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root).expanduser().resolve()

    def write_run(
        self,
        *,
        spec: SandboxRunSpec,
        strategies: list[StrategyCatalogRow],
        venues: list[VenueArchiveDescriptor],
        results: list[TrialResult],
        evidence_requests: list[EvidenceRequestDescriptor],
    ) -> SandboxArtifacts:
        strategy_payloads = [strategy.to_payload() for strategy in strategies]
        venue_payloads = [venue.to_payload() for venue in venues]
        result_payloads = [result.to_payload() for result in results]
        request_payloads = [request.to_payload() for request in evidence_requests]
        for payload in [spec.to_payload(), *strategy_payloads, *venue_payloads, *result_payloads, *request_payloads]:
            require_sandbox_boundary(payload, payload_name="sandbox_result_store_payload")

        run_dir = resolve_under_root(self.output_root, spec.run_id, path_name="sandbox run output directory")
        run_dir.mkdir(parents=True, exist_ok=False)

        summary_path = run_dir / "summary.parquet"
        rankings_path = run_dir / "rankings.parquet"
        requests_json_path = run_dir / "evidence_requests.json"
        requests_parquet_path = run_dir / "evidence_requests.parquet"
        manifest_path = run_dir / "manifest.json"

        summary_frame = pd.DataFrame([_row_for_parquet(payload) for payload in result_payloads])
        if summary_frame.empty:
            summary_frame = pd.DataFrame(columns=["trial_id", "run_id", "status", "score"])
        summary_frame.to_parquet(summary_path, index=False)

        rankings_frame = summary_frame.sort_values(["rank"], na_position="last") if "rank" in summary_frame.columns else summary_frame
        rankings_frame.to_parquet(rankings_path, index=False)

        request_rows = [_row_for_parquet(payload) for payload in request_payloads]
        requests_frame = pd.DataFrame(request_rows)
        if requests_frame.empty:
            requests_frame = pd.DataFrame(columns=["request_id", "source_run_id", "source_trial_id"])
        requests_frame.to_parquet(requests_parquet_path, index=False)
        requests_json_path.write_text(
            json.dumps(request_payloads, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )

        artifacts = SandboxArtifacts(
            run_dir=run_dir,
            manifest_path=manifest_path,
            summary_parquet_path=summary_path,
            rankings_parquet_path=rankings_path,
            evidence_requests_json_path=requests_json_path,
            evidence_requests_parquet_path=requests_parquet_path,
        )
        artifact_integrity = {
            "summary_parquet": _file_integrity(summary_path),
            "rankings_parquet": _file_integrity(rankings_path),
            "evidence_requests_json": _file_integrity(requests_json_path),
            "evidence_requests_parquet": _file_integrity(requests_parquet_path),
        }
        manifest = {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_run",
            "spec": spec.to_payload(),
            "strategy_catalog": strategy_payloads,
            "venue_archives": venue_payloads,
            "market_sources": _market_sources_from_results(results),
            "artifacts": artifacts.to_payload(),
            "artifact_integrity": artifact_integrity,
            "result_count": len(results),
            "screened_count": sum(1 for result in results if result.status == "screened"),
            "rejected_count": sum(1 for result in results if result.status == "rejected"),
            "blocked_count": sum(1 for result in results if result.status == "blocked"),
            "evidence_request_count": len(evidence_requests),
        }
        require_sandbox_boundary(manifest, payload_name="sandbox_manifest")
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        return artifacts
