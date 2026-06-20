from __future__ import annotations

import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.analytics import summarize_sandbox_run
from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.intake import (
    load_sandbox_run_spec,
    load_strategy_catalog,
    load_venue_archive_descriptors,
)
from tradingbotsuite.research_sandbox.market_data import SandboxMarketDataCache
from tradingbotsuite.research_sandbox.paths import resolve_under_root, validate_safe_path_component
from tradingbotsuite.research_sandbox.preflight import preflight_sandbox_compatibility
from tradingbotsuite.research_sandbox.runner import SandboxRunResult, run_sandbox_archive_sweep
from tradingbotsuite.research_sandbox.spec import SandboxRunSpec, StrategyCatalogRow, VenueArchiveDescriptor


SUITE_MANIFEST_NAME = "suite_manifest.json"
SUITE_INDEX_JSON_NAME = "suite_index.json"
SUITE_INDEX_PARQUET_NAME = "suite_index.parquet"
SUITE_EVIDENCE_REQUESTS_JSON_NAME = "suite_evidence_requests.json"
SUITE_EVIDENCE_REQUESTS_PARQUET_NAME = "suite_evidence_requests.parquet"


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


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
        raise ValueError("sandbox suite spec must be a JSON object")
    return payload


def _check_optional_boundary(payload: dict[str, Any], *, payload_name: str) -> None:
    guard_keys = {
        *SANDBOX_BOUNDARY_FLAGS,
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    }
    if not any(key in payload for key in guard_keys):
        return
    merged = sandbox_boundary_metadata()
    for key in guard_keys:
        if key in payload:
            merged[key] = payload[key]
    require_sandbox_boundary(merged, payload_name=payload_name)


def _safe_identifier(value: Any, *, field_name: str) -> str:
    return validate_safe_path_component(value, field_name=field_name)


def _resolve_case_path(value: Any, *, base_dir: Path, field_name: str, required: bool = True) -> Path | None:
    if value is None or value == "":
        if required:
            raise ValueError(f"sandbox suite case requires {field_name}")
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split("|") if item.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return (str(value),)


@dataclass(frozen=True)
class SandboxSuiteCase:
    case_id: str
    spec_path: Path
    strategy_catalog_path: Path
    venue_archives_path: Path
    market_data_path: Path | None = None
    min_request_score: float = 0.0
    label: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _safe_identifier(self.case_id, field_name="case_id"))
        object.__setattr__(self, "spec_path", Path(self.spec_path))
        object.__setattr__(self, "strategy_catalog_path", Path(self.strategy_catalog_path))
        object.__setattr__(self, "venue_archives_path", Path(self.venue_archives_path))
        if self.market_data_path is not None:
            object.__setattr__(self, "market_data_path", Path(self.market_data_path))
        object.__setattr__(self, "min_request_score", float(self.min_request_score))
        object.__setattr__(self, "tags", tuple(self.tags))

    def to_payload(self) -> dict[str, Any]:
        return {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_suite_case",
            "case_id": self.case_id,
            "label": self.label,
            "description": self.description,
            "tags": list(self.tags),
            "spec_path": str(self.spec_path),
            "strategy_catalog_path": str(self.strategy_catalog_path),
            "venue_archives_path": str(self.venue_archives_path),
            "market_data_path": str(self.market_data_path) if self.market_data_path is not None else None,
            "min_request_score": self.min_request_score,
        }


@dataclass(frozen=True)
class SandboxSuiteSpec:
    suite_id: str
    cases: tuple[SandboxSuiteCase, ...]
    description: str = ""
    top_n: int = 5

    def __post_init__(self) -> None:
        object.__setattr__(self, "suite_id", _safe_identifier(self.suite_id, field_name="suite_id"))
        cases = tuple(self.cases)
        if not cases:
            raise ValueError("sandbox suite requires at least one case")
        case_ids = [case.case_id for case in cases]
        duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
        if duplicates:
            raise ValueError(f"sandbox suite case_id values must be unique: {', '.join(duplicates)}")
        if self.top_n <= 0:
            raise ValueError("sandbox suite top_n must be positive")
        object.__setattr__(self, "cases", cases)

    def to_payload(self) -> dict[str, Any]:
        return {
            **sandbox_boundary_metadata(),
            "artifact_family": "rapid_strategy_iteration_sandbox_suite_spec",
            "suite_id": self.suite_id,
            "description": self.description,
            "top_n": self.top_n,
            "case_count": len(self.cases),
            "cases": [case.to_payload() for case in self.cases],
        }


@dataclass(frozen=True)
class SandboxSuiteArtifacts:
    suite_dir: Path
    suite_manifest_path: Path
    suite_index_json_path: Path
    suite_index_parquet_path: Path
    suite_evidence_requests_json_path: Path
    suite_evidence_requests_parquet_path: Path

    def to_payload(self) -> dict[str, str]:
        return {
            "suite_dir": str(self.suite_dir),
            "suite_manifest_path": str(self.suite_manifest_path),
            "suite_index_json_path": str(self.suite_index_json_path),
            "suite_index_parquet_path": str(self.suite_index_parquet_path),
            "suite_evidence_requests_json_path": str(self.suite_evidence_requests_json_path),
            "suite_evidence_requests_parquet_path": str(self.suite_evidence_requests_parquet_path),
        }


@dataclass(frozen=True)
class SandboxSuiteCaseResult:
    case: SandboxSuiteCase
    run: SandboxRunResult | None
    analysis: dict[str, Any]
    preflight: dict[str, Any]


@dataclass(frozen=True)
class SandboxSuiteRunResult:
    artifacts: SandboxSuiteArtifacts
    case_results: list[SandboxSuiteCaseResult]
    index_rows: list[dict[str, Any]]
    evidence_requests: list[dict[str, Any]]


@dataclass(frozen=True)
class _SuiteCaseExecution:
    case_index: int
    case_payload: dict[str, Any]
    case_result: SandboxSuiteCaseResult
    index_row: dict[str, Any]
    evidence_requests: list[dict[str, Any]]


@dataclass
class _SuiteInputCache:
    spec_cache: dict[str, SandboxRunSpec] = field(default_factory=dict)
    strategy_catalog_cache: dict[str, tuple[StrategyCatalogRow, ...]] = field(default_factory=dict)
    venue_archives_cache: dict[str, tuple[VenueArchiveDescriptor, ...]] = field(default_factory=dict)

    @staticmethod
    def _key(path: str | Path) -> str:
        return str(Path(path).expanduser().resolve())

    def load_spec(self, path: str | Path) -> SandboxRunSpec:
        key = self._key(path)
        spec = self.spec_cache.get(key)
        if spec is None:
            spec = load_sandbox_run_spec(Path(key))
            self.spec_cache[key] = spec
        return spec

    def load_strategy_catalog(self, path: str | Path) -> list[StrategyCatalogRow]:
        key = self._key(path)
        rows = self.strategy_catalog_cache.get(key)
        if rows is None:
            rows = tuple(load_strategy_catalog(Path(key)))
            self.strategy_catalog_cache[key] = rows
        return list(rows)

    def load_venue_archives(self, path: str | Path) -> list[VenueArchiveDescriptor]:
        key = self._key(path)
        rows = self.venue_archives_cache.get(key)
        if rows is None:
            rows = tuple(load_venue_archive_descriptors(Path(key)))
            self.venue_archives_cache[key] = rows
        return list(rows)


def _case_from_payload(payload: dict[str, Any], *, base_dir: Path) -> SandboxSuiteCase:
    _check_optional_boundary(payload, payload_name="sandbox_suite_case_spec")
    spec_path = _resolve_case_path(
        payload.get("spec_path", payload.get("spec")),
        base_dir=base_dir,
        field_name="spec_path",
    )
    strategy_catalog_path = _resolve_case_path(
        payload.get("strategy_catalog_path", payload.get("strategy_catalog")),
        base_dir=base_dir,
        field_name="strategy_catalog_path",
    )
    venue_archives_path = _resolve_case_path(
        payload.get("venue_archives_path", payload.get("venue_archives")),
        base_dir=base_dir,
        field_name="venue_archives_path",
    )
    market_data_path = _resolve_case_path(
        payload.get("market_data_path", payload.get("market_data")),
        base_dir=base_dir,
        field_name="market_data_path",
        required=False,
    )
    if spec_path is None or strategy_catalog_path is None or venue_archives_path is None:
        raise ValueError("sandbox suite case requires spec, strategy_catalog, and venue_archives")
    return SandboxSuiteCase(
        case_id=str(payload.get("case_id", payload.get("id", ""))),
        label=str(payload.get("label", "")),
        description=str(payload.get("description", "")),
        tags=_string_tuple(payload.get("tags")),
        spec_path=spec_path,
        strategy_catalog_path=strategy_catalog_path,
        venue_archives_path=venue_archives_path,
        market_data_path=market_data_path,
        min_request_score=float(payload.get("min_request_score", 0.0)),
    )


def load_sandbox_suite_spec(path: str | Path) -> SandboxSuiteSpec:
    suite_path = Path(path).expanduser()
    if not suite_path.is_absolute():
        suite_path = suite_path.resolve()
    payload = _load_json_object(suite_path)
    _check_optional_boundary(payload, payload_name="sandbox_suite_spec")
    raw_cases = payload.get("cases", payload.get("suite_cases"))
    if not isinstance(raw_cases, list):
        raise ValueError("sandbox suite spec requires a cases list")
    cases = tuple(_case_from_payload(dict(case), base_dir=suite_path.parent) for case in raw_cases)
    return SandboxSuiteSpec(
        suite_id=str(payload.get("suite_id", payload.get("id", ""))),
        description=str(payload.get("description", "")),
        top_n=int(payload.get("top_n", 5)),
        cases=cases,
    )


def _case_index_row(
    *,
    suite: SandboxSuiteSpec,
    case: SandboxSuiteCase,
    run: SandboxRunResult,
    analysis: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    require_sandbox_boundary(analysis, payload_name="sandbox_suite_case_analysis")
    status_counts = dict(analysis.get("status_counts", {}) or {})
    top_results = list(analysis.get("top_results", []) or [])
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_suite_case_index",
        "suite_id": suite.suite_id,
        "case_id": case.case_id,
        "label": case.label,
        "description": case.description,
        "tags": list(case.tags),
        "case_status": "completed",
        "run_id": analysis.get("run_id"),
        "run_dir": str(run.artifacts.run_dir),
        "manifest_path": str(run.artifacts.manifest_path),
        "rankings_parquet_path": str(run.artifacts.rankings_parquet_path),
        "analysis_report_path": analysis.get("analysis_report_path"),
        **_preflight_index_fields(preflight),
        "result_count": int(analysis.get("result_count", 0)),
        "screened_count": int(status_counts.get("screened", 0)),
        "rejected_count": int(status_counts.get("rejected", 0)),
        "blocked_count": int(status_counts.get("blocked", 0)),
        "status_counts": status_counts,
        "venue_counts": dict(analysis.get("venue_counts", {}) or {}),
        "family_counts": dict(analysis.get("family_counts", {}) or {}),
        "exit_profile_counts": dict(analysis.get("exit_profile_counts", {}) or {}),
        "filter_variant_counts": dict(analysis.get("filter_variant_counts", {}) or {}),
        "rejection_reason_counts": dict(analysis.get("rejection_reason_counts", {}) or {}),
        "market_sources": list(analysis.get("market_sources", []) or []),
        "top_trial_ids": [str(row.get("trial_id")) for row in top_results if isinstance(row, dict) and row.get("trial_id")],
        "top_result_count": len(top_results),
        "evidence_request_count": int(analysis.get("evidence_request_count", 0)),
        "evidence_request_trial_ids": list(analysis.get("evidence_request_trial_ids", []) or []),
        "min_request_score": case.min_request_score,
    }
    require_sandbox_boundary(row, payload_name="sandbox_suite_case_index_row")
    return row


def _preflight_index_fields(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "preflight_id": preflight["preflight_id"],
        "preflight_json_path": preflight["preflight_json_path"],
        "preflight_parquet_path": preflight["preflight_parquet_path"],
        "preflight_output_dir": preflight["output_dir"],
        "preflight_row_count": preflight["row_count"],
        "preflight_status_counts": dict(preflight.get("status_counts", {}) or {}),
        "preflight_trial_estimate": preflight["trial_estimate"],
        "preflight_runnable_trial_estimate": preflight["runnable_trial_estimate"],
        "preflight_blocked_trial_estimate": preflight["blocked_trial_estimate"],
        "preflight_blocker_reason_counts": dict(preflight.get("blocker_reason_counts", {}) or {}),
    }


def _blocked_case_index_row(
    *,
    suite: SandboxSuiteSpec,
    case: SandboxSuiteCase,
    spec_payload: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_suite_case_index",
        "suite_id": suite.suite_id,
        "case_id": case.case_id,
        "label": case.label,
        "description": case.description,
        "tags": list(case.tags),
        "case_status": "blocked_by_preflight",
        "run_id": spec_payload.get("run_id"),
        "run_dir": None,
        "manifest_path": None,
        "rankings_parquet_path": None,
        "analysis_report_path": None,
        **_preflight_index_fields(preflight),
        "result_count": 0,
        "screened_count": 0,
        "rejected_count": 0,
        "blocked_count": 0,
        "status_counts": {"blocked_by_preflight": 1},
        "venue_counts": {},
        "family_counts": {},
        "exit_profile_counts": {},
        "filter_variant_counts": {},
        "rejection_reason_counts": {},
        "market_sources": [],
        "top_trial_ids": [],
        "top_result_count": 0,
        "evidence_request_count": 0,
        "evidence_request_trial_ids": [],
        "min_request_score": case.min_request_score,
    }
    require_sandbox_boundary(row, payload_name="sandbox_suite_case_index_row")
    return row


def _load_case_evidence_requests(case: SandboxSuiteCase, run: SandboxRunResult, suite_id: str) -> list[dict[str, Any]]:
    payload = json.loads(run.artifacts.evidence_requests_json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("sandbox evidence request artifact must contain a list")
    requests: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("sandbox evidence request entries must be objects")
        request = {
            **item,
            "suite_id": suite_id,
            "case_id": case.case_id,
            "source_run_dir": str(run.artifacts.run_dir),
            "source_manifest_path": str(run.artifacts.manifest_path),
        }
        require_sandbox_boundary(request, payload_name="sandbox_suite_evidence_request")
        requests.append(request)
    return requests


def _write_suite_artifacts(
    *,
    suite: SandboxSuiteSpec,
    artifacts: SandboxSuiteArtifacts,
    case_payloads: list[dict[str, Any]],
    index_rows: list[dict[str, Any]],
    evidence_requests: list[dict[str, Any]],
    max_workers: int,
    market_data_cache_scope: str,
    input_cache_scope: str,
) -> None:
    index_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_suite_index",
        "suite_id": suite.suite_id,
        "case_count": len(index_rows),
        "cases": index_rows,
    }
    require_sandbox_boundary(index_payload, payload_name="sandbox_suite_index")
    artifacts.suite_index_json_path.write_text(
        json.dumps(index_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )

    index_frame = pd.DataFrame([_row_for_parquet(row) for row in index_rows])
    if index_frame.empty:
        index_frame = pd.DataFrame(columns=["suite_id", "case_id", "run_id", *SANDBOX_BOUNDARY_FLAGS])
    index_frame.to_parquet(artifacts.suite_index_parquet_path, index=False)

    for request in evidence_requests:
        require_sandbox_boundary(request, payload_name="sandbox_suite_evidence_request")
    artifacts.suite_evidence_requests_json_path.write_text(
        json.dumps(evidence_requests, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    request_frame = pd.DataFrame([_row_for_parquet(request) for request in evidence_requests])
    if request_frame.empty:
        request_frame = pd.DataFrame(columns=["request_id", "source_run_id", "source_trial_id", *SANDBOX_BOUNDARY_FLAGS])
    request_frame.to_parquet(artifacts.suite_evidence_requests_parquet_path, index=False)

    preflight_blocker_counts: Counter[str] = Counter()
    preflight_status_counts: Counter[str] = Counter()
    for row in index_rows:
        preflight_blocker_counts.update(dict(row.get("preflight_blocker_reason_counts", {}) or {}))
        preflight_status_counts.update(dict(row.get("preflight_status_counts", {}) or {}))
    artifact_integrity = {
        "suite_index_json": _file_integrity(artifacts.suite_index_json_path),
        "suite_index_parquet": _file_integrity(artifacts.suite_index_parquet_path),
        "suite_evidence_requests_json": _file_integrity(artifacts.suite_evidence_requests_json_path),
        "suite_evidence_requests_parquet": _file_integrity(artifacts.suite_evidence_requests_parquet_path),
    }
    manifest = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_suite_run",
        "suite_spec": suite.to_payload(),
        "artifacts": artifacts.to_payload(),
        "artifact_integrity": artifact_integrity,
        "case_count": len(index_rows),
        "max_workers": int(max_workers),
        "market_data_cache_scope": market_data_cache_scope,
        "input_cache_scope": input_cache_scope,
        "completed_case_count": sum(1 for row in index_rows if row.get("case_status") == "completed"),
        "skipped_case_count": sum(1 for row in index_rows if row.get("case_status") == "blocked_by_preflight"),
        "preflight_trial_estimate": sum(int(row.get("preflight_trial_estimate", 0) or 0) for row in index_rows),
        "preflight_runnable_trial_estimate": sum(
            int(row.get("preflight_runnable_trial_estimate", 0) or 0) for row in index_rows
        ),
        "preflight_blocked_trial_estimate": sum(
            int(row.get("preflight_blocked_trial_estimate", 0) or 0) for row in index_rows
        ),
        "preflight_status_counts": dict(sorted(preflight_status_counts.items())),
        "preflight_blocker_reason_counts": dict(sorted(preflight_blocker_counts.items())),
        "screened_count": sum(int(row.get("screened_count", 0)) for row in index_rows),
        "rejected_count": sum(int(row.get("rejected_count", 0)) for row in index_rows),
        "blocked_count": sum(int(row.get("blocked_count", 0)) for row in index_rows),
        "result_count": sum(int(row.get("result_count", 0)) for row in index_rows),
        "evidence_request_count": len(evidence_requests),
        "case_specs": case_payloads,
        "case_index": index_rows,
    }
    require_sandbox_boundary(manifest, payload_name="sandbox_suite_manifest")
    artifacts.suite_manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )


def _run_suite_case(
    *,
    suite: SandboxSuiteSpec,
    case: SandboxSuiteCase,
    case_index: int,
    preflight_root: Path,
    runs_root: Path,
    summary_top_n: int,
    market_data_cache: SandboxMarketDataCache,
    input_cache: _SuiteInputCache,
) -> _SuiteCaseExecution:
    case_payload = case.to_payload()
    require_sandbox_boundary(case_payload, payload_name="sandbox_suite_case")
    spec = input_cache.load_spec(case.spec_path)
    strategies = input_cache.load_strategy_catalog(case.strategy_catalog_path)
    venues = input_cache.load_venue_archives(case.venue_archives_path)
    preflight = preflight_sandbox_compatibility(
        spec=spec,
        strategies=strategies,
        venues=venues,
        output_dir=preflight_root / case.case_id,
        shared_market_data_path=case.market_data_path,
        market_data_cache=market_data_cache,
    )
    if int(preflight["runnable_trial_estimate"]) <= 0:
        index_row = _blocked_case_index_row(
            suite=suite,
            case=case,
            spec_payload=spec.to_payload(),
            preflight=preflight,
        )
        case_result = SandboxSuiteCaseResult(case=case, run=None, analysis={}, preflight=_jsonable(preflight))
        return _SuiteCaseExecution(
            case_index=case_index,
            case_payload=case_payload,
            case_result=case_result,
            index_row=index_row,
            evidence_requests=[],
        )

    run = run_sandbox_archive_sweep(
        spec=spec,
        strategies=strategies,
        venues=venues,
        output_root=runs_root / case.case_id,
        shared_market_data_path=case.market_data_path,
        min_request_score=case.min_request_score,
        market_data_cache=market_data_cache,
    )
    analysis = summarize_sandbox_run(run.artifacts.run_dir, top_n=summary_top_n, write_report=True)
    case_result = SandboxSuiteCaseResult(case=case, run=run, analysis=_jsonable(analysis), preflight=_jsonable(preflight))
    index_row = _case_index_row(suite=suite, case=case, run=run, analysis=analysis, preflight=preflight)
    return _SuiteCaseExecution(
        case_index=case_index,
        case_payload=case_payload,
        case_result=case_result,
        index_row=index_row,
        evidence_requests=_load_case_evidence_requests(case, run, suite.suite_id),
    )


def run_sandbox_suite(
    *,
    suite: SandboxSuiteSpec,
    output_root: str | Path,
    top_n: int | None = None,
    max_workers: int = 1,
) -> SandboxSuiteRunResult:
    summary_top_n = int(top_n if top_n is not None else suite.top_n)
    if summary_top_n <= 0:
        raise ValueError("top_n must be positive")
    worker_count = int(max_workers)
    if worker_count <= 0:
        raise ValueError("max_workers must be positive")
    output_root_path = Path(output_root).expanduser().resolve()
    suite_dir = resolve_under_root(output_root_path, suite.suite_id, path_name="sandbox suite output directory")
    suite_dir.mkdir(parents=True, exist_ok=False)
    preflight_root = suite_dir / "preflights"
    preflight_root.mkdir(parents=True, exist_ok=False)
    runs_root = suite_dir / "runs"
    runs_root.mkdir(parents=True, exist_ok=False)

    artifacts = SandboxSuiteArtifacts(
        suite_dir=suite_dir,
        suite_manifest_path=suite_dir / SUITE_MANIFEST_NAME,
        suite_index_json_path=suite_dir / SUITE_INDEX_JSON_NAME,
        suite_index_parquet_path=suite_dir / SUITE_INDEX_PARQUET_NAME,
        suite_evidence_requests_json_path=suite_dir / SUITE_EVIDENCE_REQUESTS_JSON_NAME,
        suite_evidence_requests_parquet_path=suite_dir / SUITE_EVIDENCE_REQUESTS_PARQUET_NAME,
    )

    use_sequential_cache = worker_count == 1 or len(suite.cases) <= 1
    market_data_cache_scope = "suite_sequential" if use_sequential_cache else "case_local_parallel"
    input_cache_scope = "suite_sequential" if use_sequential_cache else "case_local_parallel"
    if use_sequential_cache:
        suite_market_data_cache = SandboxMarketDataCache()
        suite_input_cache = _SuiteInputCache()
        executions = [
            _run_suite_case(
                suite=suite,
                case=case,
                case_index=case_index,
                preflight_root=preflight_root,
                runs_root=runs_root,
                summary_top_n=summary_top_n,
                market_data_cache=suite_market_data_cache,
                input_cache=suite_input_cache,
            )
            for case_index, case in enumerate(suite.cases)
        ]
    else:
        with ThreadPoolExecutor(max_workers=min(worker_count, len(suite.cases))) as executor:
            futures = [
                executor.submit(
                    _run_suite_case,
                    suite=suite,
                    case=case,
                    case_index=case_index,
                    preflight_root=preflight_root,
                    runs_root=runs_root,
                    summary_top_n=summary_top_n,
                    market_data_cache=SandboxMarketDataCache(),
                    input_cache=_SuiteInputCache(),
                )
                for case_index, case in enumerate(suite.cases)
            ]
            executions = [future.result() for future in futures]
    executions = sorted(executions, key=lambda item: item.case_index)
    case_payloads = [item.case_payload for item in executions]
    case_results = [item.case_result for item in executions]
    index_rows = [item.index_row for item in executions]
    evidence_requests = [request for item in executions for request in item.evidence_requests]

    _write_suite_artifacts(
        suite=suite,
        artifacts=artifacts,
        case_payloads=case_payloads,
        index_rows=index_rows,
        evidence_requests=evidence_requests,
        max_workers=worker_count,
        market_data_cache_scope=market_data_cache_scope,
        input_cache_scope=input_cache_scope,
    )
    return SandboxSuiteRunResult(
        artifacts=artifacts,
        case_results=case_results,
        index_rows=index_rows,
        evidence_requests=evidence_requests,
    )
