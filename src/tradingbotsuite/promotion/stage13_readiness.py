from __future__ import annotations

import json
import time
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

PAPER_RUN_MANIFEST_VERSION = "paper-run-manifest-v1"
SHADOW_RUN_ARCHIVE_MANIFEST_VERSION = "shadow-run-archive-manifest-v1"
TESTNET_VALIDATION_MANIFEST_VERSION = "testnet-validation-manifest-v1"
STAGE13_READINESS_REPORT_VERSION = "stage13-readiness-report-v1"
STAGE12_EVIDENCE_VALIDATION_VERSION = "stage12-oos-stress-evidence-validation-v1"

NON_LIVE_FLAGS = {
    "operator_control_input": False,
    "live_execution_input": False,
    "runtime_control_input": False,
    "live_signal_input": False,
    "position_sizing_input": False,
}

REQUIRED_EXECUTION_JOURNAL_EVENTS = frozenset(
    {
        "deterministic_cloid",
        "order_intent",
        "order_filled",
        "order_cancel_requested",
        "reconciliation",
        "schedule_cancel_set",
    }
)


@dataclass(frozen=True, slots=True)
class ReadinessValidationResult:
    passed: bool
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PaperRunManifest:
    run_id: str
    symbol: str = "BTCUSDT"
    manifest_version: str = PAPER_RUN_MANIFEST_VERSION
    runtime_mode: str = "paper"
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    completed: bool = False
    started_at_ms: int | None = None
    ended_at_ms: int | None = None
    decision_count: int = 0
    accepted_trade_count: int = 0
    validation_split_count: int = 0
    archived_paths: tuple[str, ...] = ()
    review_report_path: str | None = None
    operator_control_input: bool = False
    live_execution_input: bool = False
    runtime_control_input: bool = False
    live_signal_input: bool = False
    position_sizing_input: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ShadowRunArchiveManifest:
    run_id: str
    symbol: str = "BTCUSDT"
    manifest_version: str = SHADOW_RUN_ARCHIVE_MANIFEST_VERSION
    runtime_mode: str = "shadow"
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    completed: bool = False
    decision_count: int = 0
    feature_parity_passed: bool = False
    skip_reasons: Mapping[str, int] | None = None
    timing_drift: Mapping[str, Any] | None = None
    spread_basis_depth_drift: Mapping[str, Any] | None = None
    calibration_drift: Mapping[str, Any] | None = None
    archived_paths: tuple[str, ...] = ()
    review_report_path: str | None = None
    operator_control_input: bool = False
    live_execution_input: bool = False
    runtime_control_input: bool = False
    live_signal_input: bool = False
    position_sizing_input: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TestnetValidationManifest:
    validation_id: str
    symbol: str = "BTCUSDT"
    manifest_version: str = TESTNET_VALIDATION_MANIFEST_VERSION
    runtime_mode: str = "testnet"
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    completed: bool = False
    account_preflight_passed: bool = False
    order_path_validated: bool = False
    reconciliation_validated: bool = False
    schedule_cancel_validated: bool = False
    dead_man_cancel_validated: bool = False
    deterministic_cloids_validated: bool = False
    execution_journal_evidence: Mapping[str, Any] | None = None
    archived_paths: tuple[str, ...] = ()
    rollback_runbook_path: str | None = None
    human_approval_artifact_path: str | None = None
    operator_control_input: bool = False
    live_execution_input: bool = False
    runtime_control_input: bool = False
    live_signal_input: bool = False
    position_sizing_input: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Stage13ReadinessReport:
    manifest_version: str
    generated_at_ms: int
    stage: str
    ready: bool
    blocked: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    manifest_paths: Mapping[str, str]
    checks: Mapping[str, Any]
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    operator_control_input: bool = False
    live_execution_input: bool = False
    runtime_control_input: bool = False
    live_signal_input: bool = False
    position_sizing_input: bool = False
    live_canary_authorized: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Stage13PlanResult:
    output_dir: Path
    paper_manifest_template_path: Path
    shadow_archive_manifest_template_path: Path
    testnet_validation_manifest_template_path: Path
    readiness_report_path: Path
    rollback_runbook_checklist_path: Path
    operator_readiness_checklist_path: Path


def build_stage13_readiness_report(
    *,
    paper_manifest: Mapping[str, Any] | None = None,
    shadow_archive_manifest: Mapping[str, Any] | None = None,
    testnet_validation_manifest: Mapping[str, Any] | None = None,
    human_approval: Mapping[str, Any] | None = None,
    rollback_runbook: Mapping[str, Any] | None = None,
    manifest_paths: Mapping[str, str] | None = None,
) -> Stage13ReadinessReport:
    checks = {
        "paper_run_archive": validate_paper_run_manifest(paper_manifest).to_payload(),
        "shadow_run_archive": validate_shadow_run_archive_manifest(shadow_archive_manifest).to_payload(),
        "testnet_validation": validate_testnet_validation_manifest(testnet_validation_manifest).to_payload(),
        "human_approval": validate_human_approval(human_approval).to_payload(),
        "rollback_runbook": validate_rollback_runbook(rollback_runbook).to_payload(),
    }
    blockers = tuple(
        reason
        for check in checks.values()
        if not bool(check["passed"])
        for reason in check["reasons"]
    )
    warnings = tuple(
        warning
        for check in checks.values()
        for warning in check.get("warnings", ())
    )
    return Stage13ReadinessReport(
        manifest_version=STAGE13_READINESS_REPORT_VERSION,
        generated_at_ms=int(time.time() * 1000),
        stage="13",
        ready=not blockers,
        blocked=bool(blockers),
        blockers=blockers,
        warnings=warnings,
        required_artifacts=(
            PAPER_RUN_MANIFEST_VERSION,
            SHADOW_RUN_ARCHIVE_MANIFEST_VERSION,
            TESTNET_VALIDATION_MANIFEST_VERSION,
            "human-approval-artifact",
            "rollback-runbook-checklist",
        ),
        manifest_paths=dict(manifest_paths or {}),
        checks=checks,
    )


def validate_stage12_oos_stress_evidence(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping_or_empty(evidence)
    reasons: list[str] = []
    if not payload:
        reasons.append("stage12_evidence_manifest_required")
    if payload.get("in_sample_only") is True:
        reasons.append("in_sample_only_evidence_rejected")
    evidence_scope = str(payload.get("evidence_scope") or payload.get("validation_scope") or "").lower()
    if payload.get("out_of_sample") is not True and "oos" not in evidence_scope and "out_of_sample" not in evidence_scope:
        reasons.append("out_of_sample_evidence_required")
    if payload.get("stress_evidence") is not True and not _sequence_or_empty(payload.get("stress_periods")):
        reasons.append("stress_evidence_required")
    if payload.get("synthetic_fixture") is True and payload.get("real_market_archive") is not True:
        reasons.append("synthetic_fixture_without_real_archive_rejected")

    event_rows = _mapping_or_empty(payload.get("event_rows_by_asset"))
    power_exception = _has_text(payload.get("power_analysis_exception"))
    if not event_rows and not power_exception:
        reasons.append("event_rows_by_asset_required")
    for asset, count in event_rows.items():
        if _integer(count) < 10_000 and not power_exception:
            reasons.append(f"event_rows_floor_not_met:{asset}")
    if payload.get("uses_regime_model") is True:
        regime_rows = _mapping_or_empty(payload.get("regime_rows"))
        if not regime_rows:
            reasons.append("regime_rows_required")
        for regime, count in regime_rows.items():
            if _integer(count) < 1_000:
                reasons.append(f"regime_rows_floor_not_met:{regime}")
    labeled = _mapping_or_empty(payload.get("labeled_trades_by_side"))
    for side in ("long", "short"):
        if _integer(labeled.get(side)) < 300:
            reasons.append(f"labeled_trades_floor_not_met:{side}")
    accepted_splits = _mapping_or_empty(payload.get("accepted_trades_by_validation_split"))
    if len(accepted_splits) < 6:
        reasons.append("walk_forward_split_floor_not_met")
    for split, count in accepted_splits.items():
        if _integer(count) < 50:
            reasons.append(f"accepted_trades_floor_not_met:{split}")
    if len(_sequence_or_empty(payload.get("volatility_regimes"))) < 2:
        reasons.append("multiple_volatility_regimes_required")
    if _decimal(payload.get("costed_expectancy_after_fees_slippage_funding")) <= Decimal("0"):
        reasons.append("positive_costed_expectancy_required")
    if _decimal(payload.get("max_split_pnl_share"), default=Decimal("1")) >= Decimal("0.50"):
        reasons.append("single_split_pnl_dominance")
    side_outcomes = _mapping_or_empty(payload.get("side_outcomes"))
    if "long" not in side_outcomes or "short" not in side_outcomes:
        reasons.append("side_outcomes_must_include_long_and_short")
    if payload.get("slippage_stress_passed") is not True:
        reasons.append("slippage_stress_must_pass")
    if payload.get("funding_stress_passed") is not True:
        reasons.append("funding_stress_must_pass")
    missingness = _decimal(payload.get("feature_missingness_max_rate"), default=Decimal("1"))
    threshold = _decimal(payload.get("feature_missingness_threshold"), default=Decimal("0"))
    if threshold <= Decimal("0") or missingness > threshold:
        reasons.append("feature_missingness_floor_not_met")
    if payload.get("wt3d_claimed") is True and payload.get("wt3d_ablation_passed") is not True:
        reasons.append("wt3d_ablation_must_pass_when_claimed")
    return {
        "validation_version": STAGE12_EVIDENCE_VALIDATION_VERSION,
        "passed": not reasons,
        "reasons": reasons,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def validate_paper_run_manifest(payload: Mapping[str, Any] | None) -> ReadinessValidationResult:
    manifest = _mapping_or_empty(payload)
    reasons = _common_manifest_reasons(manifest, PAPER_RUN_MANIFEST_VERSION, "paper_run_manifest")
    if str(manifest.get("runtime_mode") or "").lower() != "paper":
        reasons.append("paper_run_manifest:runtime_mode_must_be_paper")
    if manifest.get("completed") is not True:
        reasons.append("paper_run_manifest:completed_archive_required")
    if _integer(manifest.get("decision_count")) <= 0:
        reasons.append("paper_run_manifest:decision_count_required")
    if _integer(manifest.get("accepted_trade_count")) <= 0:
        reasons.append("paper_run_manifest:accepted_trade_count_required")
    if _integer(manifest.get("validation_split_count")) < 1:
        reasons.append("paper_run_manifest:validation_split_count_required")
    if not _sequence_or_empty(manifest.get("archived_paths")):
        reasons.append("paper_run_manifest:archived_paths_required")
    if not _has_text(manifest.get("review_report_path")):
        reasons.append("paper_run_manifest:review_report_path_required")
    return ReadinessValidationResult(passed=not reasons, reasons=tuple(reasons))


def validate_shadow_run_archive_manifest(payload: Mapping[str, Any] | None) -> ReadinessValidationResult:
    manifest = _mapping_or_empty(payload)
    reasons = _common_manifest_reasons(manifest, SHADOW_RUN_ARCHIVE_MANIFEST_VERSION, "shadow_archive_manifest")
    if str(manifest.get("runtime_mode") or "").lower() != "shadow":
        reasons.append("shadow_archive_manifest:runtime_mode_must_be_shadow")
    if manifest.get("completed") is not True:
        reasons.append("shadow_archive_manifest:completed_archive_required")
    if _integer(manifest.get("decision_count")) <= 0:
        reasons.append("shadow_archive_manifest:decision_count_required")
    if manifest.get("feature_parity_passed") is not True:
        reasons.append("shadow_archive_manifest:feature_parity_required")
    for field in ("skip_reasons", "timing_drift", "spread_basis_depth_drift", "calibration_drift"):
        if not isinstance(manifest.get(field), Mapping):
            reasons.append(f"shadow_archive_manifest:{field}_required")
    if not _sequence_or_empty(manifest.get("archived_paths")):
        reasons.append("shadow_archive_manifest:archived_paths_required")
    if not _has_text(manifest.get("review_report_path")):
        reasons.append("shadow_archive_manifest:review_report_path_required")
    return ReadinessValidationResult(passed=not reasons, reasons=tuple(reasons))


def validate_testnet_validation_manifest(payload: Mapping[str, Any] | None) -> ReadinessValidationResult:
    manifest = _mapping_or_empty(payload)
    reasons = _common_manifest_reasons(manifest, TESTNET_VALIDATION_MANIFEST_VERSION, "testnet_validation_manifest")
    if str(manifest.get("runtime_mode") or "").lower() != "testnet":
        reasons.append("testnet_validation_manifest:runtime_mode_must_be_testnet")
    if manifest.get("completed") is not True:
        reasons.append("testnet_validation_manifest:completed_archive_required")
    for field in (
        "account_preflight_passed",
        "order_path_validated",
        "reconciliation_validated",
        "schedule_cancel_validated",
        "dead_man_cancel_validated",
        "deterministic_cloids_validated",
    ):
        if manifest.get(field) is not True:
            reasons.append(f"testnet_validation_manifest:{field}_required")
    journal_result = verify_execution_journal_evidence(_mapping_or_empty(manifest.get("execution_journal_evidence")))
    reasons.extend(f"testnet_validation_manifest:{reason}" for reason in journal_result.reasons)
    if not _sequence_or_empty(manifest.get("archived_paths")):
        reasons.append("testnet_validation_manifest:archived_paths_required")
    if not _has_text(manifest.get("rollback_runbook_path")):
        reasons.append("testnet_validation_manifest:rollback_runbook_path_required")
    if not _has_text(manifest.get("human_approval_artifact_path")):
        reasons.append("testnet_validation_manifest:human_approval_artifact_path_required")
    return ReadinessValidationResult(passed=not reasons, reasons=tuple(reasons))


def verify_execution_journal_evidence(evidence: Mapping[str, Any] | None) -> ReadinessValidationResult:
    payload = _mapping_or_empty(evidence)
    event_types = {str(item) for item in _sequence_or_empty(payload.get("event_types"))}
    fields = {str(item) for item in _sequence_or_empty(payload.get("evidence_fields"))}
    present = event_types | fields | {key for key, value in payload.items() if _truthy(value)}
    reasons = tuple(f"missing_execution_journal_evidence:{item}" for item in sorted(REQUIRED_EXECUTION_JOURNAL_EVENTS - present))
    return ReadinessValidationResult(passed=not reasons, reasons=reasons)


def validate_human_approval(payload: Mapping[str, Any] | None) -> ReadinessValidationResult:
    approval = _mapping_or_empty(payload)
    reasons: list[str] = []
    if approval.get("approved") is not True:
        reasons.append("human_approval:approved_true_required")
    if not _has_text(approval.get("approval_id")):
        reasons.append("human_approval:approval_id_required")
    if not _has_text(approval.get("approved_by")):
        reasons.append("human_approval:approved_by_required")
    return ReadinessValidationResult(passed=not reasons, reasons=tuple(reasons))


def validate_rollback_runbook(payload: Mapping[str, Any] | None) -> ReadinessValidationResult:
    runbook = _mapping_or_empty(payload)
    reasons: list[str] = []
    for field in ("kill_switch_checked", "revert_branch_identified", "cancel_all_orders_step", "post_rollback_reconciliation_step"):
        if runbook.get(field) is not True:
            reasons.append(f"rollback_runbook:{field}_required")
    return ReadinessValidationResult(passed=not reasons, reasons=tuple(reasons))


def validate_asset_scope_for_requested_symbol(manifest: Mapping[str, Any], requested_symbol: str) -> ReadinessValidationResult:
    normalized = requested_symbol.upper()
    scope = _asset_scope(manifest)
    reasons: list[str] = []
    if scope and normalized not in scope:
        reasons.append(f"artifact_asset_scope_rejected:{normalized}_not_in_{','.join(sorted(scope))}")
    if normalized.startswith("ETH") and scope and scope <= {"BTCUSDT", "BTC"}:
        reasons.append("btc_only_artifact_rejected_for_eth")
    return ReadinessValidationResult(passed=not reasons, reasons=tuple(reasons))


def summarize_shadow_archive(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "operator_control_input": False,
        "live_execution_input": False,
        "runtime_control_input": False,
        "symbol": manifest.get("symbol"),
        "decision_count": manifest.get("decision_count", 0),
        "feature_parity_passed": bool(manifest.get("feature_parity_passed")),
        "skip_reasons": dict(_mapping_or_empty(manifest.get("skip_reasons"))),
        "timing_drift": dict(_mapping_or_empty(manifest.get("timing_drift"))),
        "spread_basis_depth_drift": dict(_mapping_or_empty(manifest.get("spread_basis_depth_drift"))),
        "calibration_drift": dict(_mapping_or_empty(manifest.get("calibration_drift"))),
        "validation": validate_shadow_run_archive_manifest(manifest).to_payload(),
    }


def write_stage13_readiness_plan(output_dir: Path) -> Stage13PlanResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    paper_template = PaperRunManifest(run_id="paper-run-id-required").to_payload()
    shadow_template = ShadowRunArchiveManifest(run_id="shadow-run-id-required").to_payload()
    testnet_template = TestnetValidationManifest(validation_id="testnet-validation-id-required").to_payload()
    manifest_paths = {
        "paper_run_manifest": str(output_dir / "paper_run_manifest.template.json"),
        "shadow_run_archive_manifest": str(output_dir / "shadow_run_archive_manifest.template.json"),
        "testnet_validation_manifest": str(output_dir / "testnet_validation_manifest.template.json"),
    }
    readiness = build_stage13_readiness_report(
        paper_manifest=paper_template,
        shadow_archive_manifest=shadow_template,
        testnet_validation_manifest=testnet_template,
        human_approval={},
        rollback_runbook={},
        manifest_paths=manifest_paths,
    )
    paper_path = output_dir / "paper_run_manifest.template.json"
    shadow_path = output_dir / "shadow_run_archive_manifest.template.json"
    testnet_path = output_dir / "testnet_validation_manifest.template.json"
    readiness_path = output_dir / "stage13_readiness_report.json"
    rollback_path = output_dir / "rollback_runbook_checklist.md"
    operator_path = output_dir / "operator_readiness_checklist.md"

    _write_json(paper_path, paper_template)
    _write_json(shadow_path, shadow_template)
    _write_json(testnet_path, testnet_template)
    _write_json(readiness_path, readiness.to_payload())
    rollback_path.write_text(_rollback_checklist_text(), encoding="utf-8")
    operator_path.write_text(_operator_checklist_text(readiness), encoding="utf-8")
    return Stage13PlanResult(
        output_dir=output_dir,
        paper_manifest_template_path=paper_path,
        shadow_archive_manifest_template_path=shadow_path,
        testnet_validation_manifest_template_path=testnet_path,
        readiness_report_path=readiness_path,
        rollback_runbook_checklist_path=rollback_path,
        operator_readiness_checklist_path=operator_path,
    )


def _common_manifest_reasons(manifest: Mapping[str, Any], expected_version: str, prefix: str) -> list[str]:
    reasons: list[str] = []
    version = manifest.get("manifest_version") or manifest.get(f"{prefix}_version")
    if version != expected_version:
        reasons.append(f"{prefix}:manifest_version_must_be_{expected_version}")
    if manifest.get("research_only") is not True:
        reasons.append(f"{prefix}:research_only_must_be_true")
    if manifest.get("observe_only") is not True:
        reasons.append(f"{prefix}:observe_only_must_be_true")
    if manifest.get("promotion_ready") is not False:
        reasons.append(f"{prefix}:promotion_ready_must_be_false")
    for field, expected in NON_LIVE_FLAGS.items():
        if manifest.get(field) is not expected:
            reasons.append(f"{prefix}:{field}_must_be_false")
    return reasons


def _asset_scope(manifest: Mapping[str, Any]) -> set[str]:
    raw_scope = manifest.get("asset_scope") or manifest.get("symbols") or manifest.get("symbol")
    if raw_scope is None:
        return set()
    if isinstance(raw_scope, str):
        values: Iterable[Any] = (raw_scope,)
    elif isinstance(raw_scope, Iterable):
        values = raw_scope
    else:
        values = (raw_scope,)
    return {str(item).strip().upper() for item in values if str(item).strip()}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _rollback_checklist_text() -> str:
    return """# Stage 13 Rollback Runbook Checklist

- [ ] Human approval artifact attached and reviewed.
- [ ] Kill switch path checked without changing runtime mode.
- [ ] Revert branch or commit identified.
- [ ] Cancel-all-orders procedure documented for operator review.
- [ ] Post-rollback reconciliation procedure documented.
- [ ] Dead-man or scheduled-cancel evidence archived.

This checklist is a planning artifact only. It does not authorize live canary execution.
"""


def _operator_checklist_text(readiness: Stage13ReadinessReport) -> str:
    blockers = "\n".join(f"- {reason}" for reason in readiness.blockers)
    return f"""# Stage 13 Readiness Checklist

Status: blocked

Required archives:
- Paper run manifest and review report.
- Shadow run archive and review report.
- Testnet validation manifest.
- Human approval artifact.
- Rollback runbook checklist.

Current blockers:
{blockers}

No runtime mode switches, order controls, or live canary controls are exposed by this checklist.
"""


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence_or_empty(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(value)
    return (value,)


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _integer(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _decimal(value: Any, *, default: Decimal = Decimal("0")) -> Decimal:
    if isinstance(value, bool):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"false", "0", "no", "none", "null"}
    return bool(value)
