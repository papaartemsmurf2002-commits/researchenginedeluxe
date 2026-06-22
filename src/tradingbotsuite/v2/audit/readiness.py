# V2-AUDIT-ID: V2-AUD-COMPLETE-002
# V2-CONTRACTS: docs/contracts/autonomous_readiness_contract.md, docs/contracts/audit_report_contract.md
# V2-BOUNDARY: research_only, autonomous_readiness_gate, blocker_report, no_live_imports
# V2-OWNER: v2_audit
"""Autonomous research-readiness audit gate."""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.audit.schemas import AuditBlockerReport, AuditReportStatus
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.config.time import ensure_utc, utc_now
from tradingbotsuite.v2.lead_book import LeadBookStore
from tradingbotsuite.v2.ledger import read_ledger
from tradingbotsuite.v2.security.boundary import require_research_boundary

AUTONOMOUS_READINESS_EVIDENCE_SCHEMA_VERSION = "autonomous_readiness_evidence_v1"
AUTONOMOUS_READINESS_REPORT_SCHEMA_VERSION = "autonomous_readiness_report_v1"

REQUIRED_AUTONOMOUS_READINESS_KEYS: tuple[str, ...] = (
    "repo.clean_git_tree",
    "repo.baseline_committed_and_pushed",
    "repo.current_control_docs_authoritative",
    "validation.python_3_11_pinned",
    "validation.compile_passed",
    "validation.contracts_passed",
    "validation.v2_tests_passed",
    "validation.full_suite_authoritative_passed",
    "audit.high_risk_chunks_independently_audited",
    "audit.p0_blockers_open_false",
    "audit.p1_blockers_open_false",
    "known_issues.issue_r106_026_resolved_or_ci_authority_documented",
    "known_issues.issue_r106_020_closed_with_regression_tests",
    "data.hyperliquid_universe_snapshots_operational",
    "data.archive_collectors_operational",
    "data.coverage_reports_operational",
    "data.archive_snapshot_ids_required",
    "data.universe_snapshot_ids_required",
    "backtest_data.rejects_pre_2024",
    "backtest_data.rejects_under_6_months",
    "backtest_data.rejects_lockbox_overlap",
    "backtest_data.enforces_coverage_0_98",
    "backtest_data.supports_asof_universe",
    "strategy_engine.declarative_specs_supported",
    "strategy_engine.python_plugins_protocol_guarded",
    "strategy_engine.vectorized_engine_available",
    "strategy_engine.event_driven_engine_available",
    "strategy_engine.strategy_exit_semantics_locked",
    "ledger.append_only",
    "ledger.failed_trials_logged",
    "ledger.manual_spreadsheet_editing_forbidden",
    "ledger.gross_and_net_metrics_required",
    "ledger.base_conservative_severe_costs_required",
    "leadbook.agents_can_create_rows",
    "leadbook.human_inspection_required_for_deep_validation",
    "leadbook.diminishing_returns_warning",
    "leadbook.profit_concentration_check",
    "leadbook.minimum_trade_frequency_check",
    "leadbook.monthly_stability_check",
    "workers.dedicated_workers",
    "workers.durable_job_store",
    "workers.collector_gaps_logged",
    "workers.asgi_not_blocked_by_jobs",
    "boundaries.research_only",
    "boundaries.paper_live_order_sizing_runtime_forbidden",
    "boundaries.no_touch_paths_enforced",
    "boundaries.artifact_boundary_invariant_centralized",
)

REQUIRED_CYCLE_JOB_KINDS: tuple[str, ...] = (
    "universe_refresh",
    "recent_candle_bootstrap",
    "coverage_audit",
    "strategy_queue_scan",
    "vectorized_backtest",
    "validation_gate",
    "ledger_append_export",
    "lead_book_upsert",
    "audit_check",
)

REQUIRED_CYCLE_AUDIT_JOB_KINDS: tuple[str, ...] = tuple(
    kind for kind in REQUIRED_CYCLE_JOB_KINDS if kind != "audit_check"
)

REQUIRED_CYCLE_ARTIFACT_REF_PREFIXES: tuple[str, ...] = (
    "universe_snapshot_id=",
    "archive_snapshot_id=",
    "coverage_report_id",
    "strategy_queue_manifest_id=",
    "accepted_spec_path=",
    "accepted_spec_sha256=",
    "strategy_spec_hash=",
    "run_manifest_path=",
    "validation_manifest_path=",
    "validation_manifest_id=",
    "ledger_path=",
    "lead_book_path=",
)

_SECRET_NAME_RE = re.compile(
    r"(^\.env($|\.)|secret|credential|password|private|api[-_]?key|token)",
    re.IGNORECASE,
)


class AutonomousReadinessStatus(str, Enum):
    AUTONOMOUS_RESEARCH_READY = "autonomous_research_ready"
    BLOCKED = "blocked"


class ReadinessEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1)
    passed: bool = False
    evidence_ref: str = ""
    evidence_path: str | None = None
    notes: str = ""


class ReadinessCheckSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1)
    present: bool
    passed: bool
    evidence_ref: str = ""
    evidence_path: str | None = None
    blocker_reasons: tuple[str, ...] = ()


class AutonomousReadinessEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(
        default=AUTONOMOUS_READINESS_EVIDENCE_SCHEMA_VERSION,
        pattern=f"^{AUTONOMOUS_READINESS_EVIDENCE_SCHEMA_VERSION}$",
    )
    run_id: str = Field(min_length=1)
    created_at: datetime | None = None
    created_by_id: str = "codex-manager-agent"
    evidence_items: tuple[ReadinessEvidenceItem, ...] = ()
    cycle_execution_manifest_path: str | None = None
    final_audit_report_path: str | None = None
    ledger_path: str | None = None
    lead_book_path: str | None = None
    known_p0_open: int = Field(default=0, ge=0)
    known_p1_open: int = Field(default=0, ge=0)
    notes: str = ""
    boundary_flags: dict[str, bool] = Field(default_factory=lambda: dict(RESEARCH_BOUNDARY))
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("created_at")
    @classmethod
    def _utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_evidence(self) -> "AutonomousReadinessEvidence":
        keys = [item.key for item in self.evidence_items]
        if len(keys) != len(set(keys)):
            raise ValueError("readiness evidence item keys must be unique")
        require_research_boundary(self, context="autonomous readiness evidence")
        return self


class AutonomousReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(
        default=AUTONOMOUS_READINESS_REPORT_SCHEMA_VERSION,
        pattern=f"^{AUTONOMOUS_READINESS_REPORT_SCHEMA_VERSION}$",
    )
    report_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    created_at: datetime
    status: AutonomousReadinessStatus
    autonomous_research_ready: bool = False
    required_check_count: int = Field(ge=1)
    passed_check_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    blocker_reasons: tuple[str, ...] = ()
    required_check_keys: tuple[str, ...] = REQUIRED_AUTONOMOUS_READINESS_KEYS
    check_summaries: tuple[ReadinessCheckSummary, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    required_next_actions: tuple[str, ...] = ()
    boundary_flags: dict[str, bool] = Field(default_factory=lambda: dict(RESEARCH_BOUNDARY))
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("created_at")
    @classmethod
    def _utc_created_at(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_report(self) -> "AutonomousReadinessReport":
        if self.status == AutonomousReadinessStatus.AUTONOMOUS_RESEARCH_READY:
            if not self.autonomous_research_ready:
                raise ValueError("ready reports must set autonomous_research_ready")
            if self.blocker_reasons:
                raise ValueError("ready reports cannot contain blocker_reasons")
        else:
            if self.autonomous_research_ready:
                raise ValueError("blocked reports cannot set autonomous_research_ready")
            if not self.blocker_reasons:
                raise ValueError("blocked readiness reports require blocker_reasons")
        require_research_boundary(self, context="autonomous readiness report")
        return self


def load_autonomous_readiness_evidence(path: str | Path) -> AutonomousReadinessEvidence:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"readiness evidence cannot be read: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"readiness evidence is not valid JSON: {path}") from exc
    return AutonomousReadinessEvidence.model_validate(payload)


def run_autonomous_readiness_audit(
    evidence: AutonomousReadinessEvidence | dict[str, Any],
    *,
    output_path: str | Path,
) -> AutonomousReadinessReport:
    parsed = (
        evidence
        if isinstance(evidence, AutonomousReadinessEvidence)
        else AutonomousReadinessEvidence.model_validate(evidence)
    )
    check_summaries, check_blockers = _check_evidence_items(parsed)
    artifact_refs: list[str] = []
    artifact_blockers: list[str] = []
    artifact_blockers.extend(
        _check_cycle_execution(parsed.cycle_execution_manifest_path, artifact_refs)
    )
    artifact_blockers.extend(
        _check_final_audit_report(parsed.final_audit_report_path, artifact_refs)
    )
    artifact_blockers.extend(_check_ledger(parsed.ledger_path, artifact_refs))
    artifact_blockers.extend(_check_lead_book(parsed.lead_book_path, artifact_refs))
    issue_blockers = []
    if parsed.known_p0_open:
        issue_blockers.append(f"known_p0_open:{parsed.known_p0_open}")
    if parsed.known_p1_open:
        issue_blockers.append(f"known_p1_open:{parsed.known_p1_open}")

    blockers = _unique((*check_blockers, *artifact_blockers, *issue_blockers))
    status = (
        AutonomousReadinessStatus.BLOCKED
        if blockers
        else AutonomousReadinessStatus.AUTONOMOUS_RESEARCH_READY
    )
    passed_count = sum(1 for summary in check_summaries if summary.present and summary.passed)
    next_actions = _required_next_actions(blockers)
    identity = {
        "schema_version": AUTONOMOUS_READINESS_REPORT_SCHEMA_VERSION,
        "run_id": parsed.run_id,
        "status": status.value,
        "required_check_keys": list(REQUIRED_AUTONOMOUS_READINESS_KEYS),
        "check_summaries": [summary.model_dump(mode="json") for summary in check_summaries],
        "blocker_reasons": blockers,
        "artifact_refs": artifact_refs,
        "known_p0_open": parsed.known_p0_open,
        "known_p1_open": parsed.known_p1_open,
    }
    report = AutonomousReadinessReport(
        report_id=canonical_json_hash(identity),
        run_id=parsed.run_id,
        created_at=utc_now(),
        status=status,
        autonomous_research_ready=status == AutonomousReadinessStatus.AUTONOMOUS_RESEARCH_READY,
        required_check_count=len(REQUIRED_AUTONOMOUS_READINESS_KEYS),
        passed_check_count=passed_count,
        blocker_count=len(blockers),
        blocker_reasons=blockers,
        check_summaries=tuple(check_summaries),
        artifact_refs=tuple(artifact_refs),
        required_next_actions=next_actions,
    )
    _write_report(output_path, report)
    return report


def run_autonomous_readiness_audit_from_file(
    evidence_path: str | Path,
    *,
    output_path: str | Path,
) -> AutonomousReadinessReport:
    return run_autonomous_readiness_audit(
        load_autonomous_readiness_evidence(evidence_path),
        output_path=output_path,
    )


def _check_evidence_items(
    evidence: AutonomousReadinessEvidence,
) -> tuple[list[ReadinessCheckSummary], tuple[str, ...]]:
    by_key = {item.key: item for item in evidence.evidence_items}
    summaries: list[ReadinessCheckSummary] = []
    blockers: list[str] = []
    for key in REQUIRED_AUTONOMOUS_READINESS_KEYS:
        item = by_key.get(key)
        item_blockers: list[str] = []
        if item is None:
            item_blockers.append(f"missing_evidence:{key}")
            summaries.append(
                ReadinessCheckSummary(
                    key=key,
                    present=False,
                    passed=False,
                    blocker_reasons=tuple(item_blockers),
                )
            )
            blockers.extend(item_blockers)
            continue
        if not item.passed:
            item_blockers.append(f"check_failed:{key}")
        if not item.evidence_ref.strip():
            item_blockers.append(f"missing_evidence_ref:{key}")
        if item.evidence_path:
            path = Path(item.evidence_path).resolve(strict=False)
            if not path.exists():
                item_blockers.append(f"missing_evidence_path:{key}:{path}")
        summaries.append(
            ReadinessCheckSummary(
                key=key,
                present=True,
                passed=item.passed and not item_blockers,
                evidence_ref=item.evidence_ref,
                evidence_path=item.evidence_path,
                blocker_reasons=tuple(item_blockers),
            )
        )
        blockers.extend(item_blockers)
    extra = sorted(set(by_key) - set(REQUIRED_AUTONOMOUS_READINESS_KEYS))
    for key in extra:
        blockers.append(f"unexpected_evidence_key:{key}")
    return summaries, _unique(blockers)


def _check_cycle_execution(path_value: str | None, artifact_refs: list[str]) -> tuple[str, ...]:
    if not path_value:
        return ("missing_artifact:cycle_execution_manifest",)
    path = Path(path_value).resolve(strict=False)
    if not path.exists():
        return (f"missing_artifact_path:cycle_execution_manifest:{path}",)
    try:
        payload = _read_json(path)
    except ValueError as exc:
        return (f"unreadable_artifact:cycle_execution_manifest:{exc}",)
    artifact_refs.extend(_file_refs("cycle_execution_manifest", path))
    blockers: list[str] = []
    status = str(payload.get("status", "missing"))
    if status != "completed":
        blockers.append(f"cycle_execution_not_completed:{status}")
    if payload.get("audit_attempted") is not True:
        blockers.append("cycle_execution_audit_not_attempted")
    blocker_reasons = payload.get("blocker_reasons", ())
    if not isinstance(blocker_reasons, list):
        blockers.append("cycle_execution_blockers_invalid")
    else:
        blockers.extend(f"cycle_execution_blocker:{reason}" for reason in blocker_reasons if reason)
    kinds = {
        str(job.get("kind"))
        for job in payload.get("job_executions", ())
        if isinstance(job, dict)
    }
    for kind in REQUIRED_CYCLE_JOB_KINDS:
        if kind not in kinds:
            blockers.append(f"cycle_execution_missing_job_kind:{kind}")
    return _unique(blockers)


def _check_final_audit_report(path_value: str | None, artifact_refs: list[str]) -> tuple[str, ...]:
    if not path_value:
        return ("missing_artifact:final_audit_report",)
    path = Path(path_value).resolve(strict=False)
    if not path.exists():
        return (f"missing_artifact_path:final_audit_report:{path}",)
    try:
        report = AuditBlockerReport.model_validate(_read_json(path))
    except (ValueError, TypeError) as exc:
        return (f"invalid_artifact:final_audit_report:{exc}",)
    artifact_refs.extend(_file_refs("final_audit_report", path))
    blockers: list[str] = []
    if report.status != AuditReportStatus.PASS:
        blockers.append(f"final_audit_not_pass:{report.status.value}")
    blockers.extend(f"final_audit_blocker:{reason}" for reason in report.blocker_reasons)
    if report.accepted_research_ready:
        blockers.append("final_audit_invalid_accepted_research_ready_true")
    for kind in REQUIRED_CYCLE_AUDIT_JOB_KINDS:
        if kind not in report.required_successful_job_kinds:
            blockers.append(f"final_audit_missing_required_successful_job_kind:{kind}")
        if kind not in report.required_job_kind_order:
            blockers.append(f"final_audit_missing_required_job_kind_order:{kind}")
    blockers.extend(_job_order_blockers(report.required_job_kind_order))
    all_report_refs = (
        *report.artifact_refs,
        *(ref for summary in report.job_summaries for ref in summary.output_refs),
        *(ref for summary in report.job_summaries for ref in summary.archive_manifest_refs),
    )
    for prefix in REQUIRED_CYCLE_ARTIFACT_REF_PREFIXES:
        if prefix not in report.required_artifact_ref_prefixes:
            blockers.append(f"final_audit_missing_required_artifact_ref_prefix:{prefix}")
        if not any(ref.startswith(prefix) for ref in all_report_refs):
            blockers.append(f"final_audit_missing_artifact_ref_prefix:{prefix}")
    return _unique(blockers)


def _check_ledger(path_value: str | None, artifact_refs: list[str]) -> tuple[str, ...]:
    if not path_value:
        return ("missing_artifact:ledger",)
    path = Path(path_value).resolve(strict=False)
    if not path.exists():
        return (f"missing_artifact_path:ledger:{path}",)
    try:
        rows = read_ledger(path)
    except Exception as exc:
        return (f"invalid_artifact:ledger:{exc}",)
    artifact_refs.extend((*_file_refs("ledger", path), f"ledger_row_count={len(rows)}"))
    if not rows:
        return ("ledger_empty",)
    return ()


def _check_lead_book(path_value: str | None, artifact_refs: list[str]) -> tuple[str, ...]:
    if not path_value:
        return ("missing_artifact:lead_book",)
    path = Path(path_value).resolve(strict=False)
    if not path.exists():
        return (f"missing_artifact_path:lead_book:{path}",)
    try:
        rows = LeadBookStore(path).read()
    except Exception as exc:
        return (f"invalid_artifact:lead_book:{exc}",)
    artifact_refs.extend((*_file_refs("lead_book", path), f"lead_book_row_count={len(rows)}"))
    if not rows:
        return ("lead_book_empty",)
    return ()


def _file_refs(name: str, path: Path) -> tuple[str, str]:
    return (
        f"{name}_path={path}",
        f"{name}_sha256={file_sha256(path)}",
    )


def _job_order_blockers(required_order: tuple[str, ...]) -> tuple[str, ...]:
    positions = [required_order.index(kind) for kind in REQUIRED_CYCLE_AUDIT_JOB_KINDS if kind in required_order]
    if len(positions) != len(REQUIRED_CYCLE_AUDIT_JOB_KINDS):
        return ()
    if positions != sorted(positions):
        return ("final_audit_required_job_kind_order_drift",)
    return ()


def _required_next_actions(blockers: tuple[str, ...]) -> tuple[str, ...]:
    if not blockers:
        return ("preserve_research_only_boundary_after_autonomous_research_ready",)
    actions = [
        "resolve_readiness_blockers",
        "rerun_autonomous_readiness_audit",
        "do_not_claim_autonomous_research_ready_until_report_passes",
    ]
    if any("real_hyperliquid" in blocker or blocker.startswith("data.") for blocker in blockers):
        actions.append("provide_real_hyperliquid_archive_operation_evidence")
    if any("full_suite" in blocker or "python_3_11" in blocker for blocker in blockers):
        actions.append("provide_authoritative_python311_validation_evidence")
    if any("independently_audited" in blocker for blocker in blockers):
        actions.append("complete_independent_high_risk_chunk_audits")
    return tuple(dict.fromkeys(actions))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"{path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid_json") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected_json_object")
    return payload


def _write_report(path_value: str | Path, report: AutonomousReadinessReport) -> None:
    path = _validate_output_path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _validate_output_path(path_value: str | Path) -> Path:
    path = Path(path_value).resolve(strict=False)
    if path.suffix.lower() != ".json":
        raise ValueError("autonomous readiness report output must be a .json file")
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise ValueError("autonomous readiness report output path cannot be secret-like")
    return path


def _unique(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))
