from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from tradingbotsuite.research.command_registry import RESEARCH_COMMANDS

LIVE_READINESS_REPORT_VERSION = "hmm-multi-knn-live-readiness-contract-v1"
RESEARCH_BOUNDARY_REPORT_VERSION = "hmm-multi-knn-research-boundary-contract-v1"

RESEARCH_JOB_NAMES = RESEARCH_COMMANDS
DEFAULT_WEBHOOK_SECRET_VALUES = frozenset({"", "change-me", "changeme", "default", "secret", "test", "todo"})
REQUIRED_RISK_CAP_FIELDS = (
    "max_daily_loss_quote",
    "max_open_risk_notional",
)
REQUIRED_EXECUTION_JOURNAL_EVIDENCE = (
    "deterministic_cloid",
    "reduce_only_exits",
    "schedule_cancel_dead_man_heartbeat",
    "reconciliation_before_live",
)
NON_LIVE_INPUT_FLAGS = (
    "live_signal_input",
    "position_sizing_input",
    "operator_control_input",
    "live_execution_input",
    "runtime_control_input",
)
LIVE_OUTPUT_FIELDS = (
    "live_signal_path",
    "signal_output_path",
    "position_sizing_path",
    "sizing_output_path",
    "execution_intents_path",
    "orders_path",
    "runtime_control_path",
)
RESEARCH_INTENDED_USES = frozenset({"research", "research_only", "observe_only", "research_observe_only"})


@dataclass(frozen=True, slots=True)
class LiveReadinessInput:
    config: Mapping[str, Any]
    artifacts: tuple[Mapping[str, Any], ...]
    execution_journal_evidence: Mapping[str, Any]


def build_live_readiness_report(
    config: Mapping[str, Any] | None = None,
    artifacts: Iterable[Mapping[str, Any]] | None = None,
    execution_journal_evidence: Mapping[str, Any] | None = None,
    *,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a research-only live-readiness validation report.

    This function is intentionally disconnected from runtime. It inspects
    dictionaries supplied by tests, research jobs, or future artifact readers;
    it does not read env vars, mutate config, place orders, or toggle controls.
    """

    readiness_input = _coerce_input(
        config=config,
        artifacts=artifacts,
        execution_journal_evidence=execution_journal_evidence,
        payload=payload,
    )
    checks = [
        _check_live_rejects_research_jobs_and_artifacts(readiness_input),
        _check_research_artifacts_not_live_promotable(readiness_input),
        _check_webhook_secret(readiness_input),
        _check_hyperliquid_credentials(readiness_input),
        _check_risk_caps(readiness_input),
        _check_execution_journal_evidence(readiness_input),
    ]
    blockers = [
        reason
        for check in checks
        if not check["passed"]
        for reason in check["reasons"]
    ]
    return {
        "live_readiness_report_version": LIVE_READINESS_REPORT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "passed": not blockers,
        "checks": checks,
        "blockers": blockers,
        "summary": {
            "runtime_mode": _runtime_mode(readiness_input.config),
            "artifact_count": len(readiness_input.artifacts),
            "failed_check_count": sum(1 for check in checks if not check["passed"]),
            "passed_check_count": sum(1 for check in checks if check["passed"]),
        },
        "notes": [
            "Advisory research-side validation only.",
            "A passing report does not promote artifacts or enable live automation.",
            "Live runtime, Hyperliquid adapter behavior, sizing, and operator controls remain outside this module.",
        ],
    }


def build_research_boundary_report(
    *,
    artifact_manifest: Mapping[str, Any] | None = None,
    metrics: Mapping[str, Any] | None = None,
    monitoring_report: Mapping[str, Any] | None = None,
    experiment_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate that research artifacts cannot be mistaken for live inputs.

    This is a pure payload validator. It does not read files, connect to
    exchanges, load runtime config, or decide live promotion.
    """

    payloads = [
        ("artifact_manifest", artifact_manifest, _validate_research_artifact_manifest),
        ("metrics", metrics, _validate_research_metrics),
        ("monitoring_report", monitoring_report, _validate_monitoring_report),
        ("experiment_manifest", experiment_manifest, _validate_experiment_manifest),
    ]
    checks = [
        _boundary_check(name, validator(payload))
        for name, payload, validator in payloads
        if payload is not None
    ]
    blockers = [
        reason
        for check in checks
        if not check["passed"]
        for reason in check["reasons"]
    ]
    return {
        "research_boundary_report_version": RESEARCH_BOUNDARY_REPORT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "passed": not blockers,
        "checks": checks,
        "blockers": blockers,
    }


def research_boundary_passed(report: Mapping[str, Any]) -> bool:
    return bool(report.get("passed")) and report.get("research_only") is True and report.get("promotion_ready") is False


def research_boundary_metadata() -> dict[str, Any]:
    return {
        "intended_use": "research_observe_only",
        "live_signal_input": False,
        "position_sizing_input": False,
        "operator_control_input": False,
        "live_execution_input": False,
        "runtime_control_input": False,
    }


def research_artifact_boundary_metadata() -> dict[str, Any]:
    return {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
    }


def _coerce_input(
    *,
    config: Mapping[str, Any] | None,
    artifacts: Iterable[Mapping[str, Any]] | None,
    execution_journal_evidence: Mapping[str, Any] | None,
    payload: Mapping[str, Any] | None,
) -> LiveReadinessInput:
    if payload is not None:
        config = _mapping_or_empty(payload.get("config") or payload.get("runtime_config") or config)
        artifacts = payload.get("artifacts") or payload.get("artifact_manifests") or artifacts
        execution_journal_evidence = _mapping_or_empty(
            payload.get("execution_journal_evidence")
            or payload.get("journal_evidence")
            or execution_journal_evidence
        )

    artifact_items: tuple[Mapping[str, Any], ...]
    if artifacts is None:
        artifact_items = ()
    elif isinstance(artifacts, Mapping):
        artifact_items = (artifacts,)
    else:
        artifact_items = tuple(artifacts)
        if not all(isinstance(item, Mapping) for item in artifact_items):
            raise TypeError("artifacts must be mappings")

    return LiveReadinessInput(
        config=_mapping_or_empty(config),
        artifacts=artifact_items,
        execution_journal_evidence=_mapping_or_empty(execution_journal_evidence),
    )


def _check_live_rejects_research_jobs_and_artifacts(readiness_input: LiveReadinessInput) -> dict[str, Any]:
    reasons: list[str] = []
    live_mode = _runtime_mode(readiness_input.config) == "live"
    research_job = _research_job_name(readiness_input.config)
    research_jobs_allowed = _bool_at_any(
        readiness_input.config,
        (
            ("research_jobs_enabled",),
            ("allow_research_jobs",),
            ("research", "enabled_in_live"),
            ("operator", "allow_research_jobs"),
        ),
    )
    if live_mode and research_job in RESEARCH_JOB_NAMES:
        reasons.append(f"live_runtime_rejects_research_job:{research_job}")
    if live_mode and research_jobs_allowed:
        reasons.append("live_runtime_rejects_research_jobs_enabled")
    if live_mode:
        for index, artifact in enumerate(readiness_input.artifacts):
            if artifact.get("research_only") is True or artifact.get("observe_only") is True:
                reasons.append(f"live_runtime_rejects_research_artifact:{index}")
    return _check("live_rejects_research_jobs_and_artifacts", reasons)


def _check_research_artifacts_not_live_promotable(readiness_input: LiveReadinessInput) -> dict[str, Any]:
    reasons = [
        f"research_only_artifact_not_live_promotable:{index}"
        for index, artifact in enumerate(readiness_input.artifacts)
        if artifact.get("research_only") is True
        and str(artifact.get("promotion_target") or artifact.get("intended_use") or "live").lower() in {"live", "production", "live_promotion"}
    ]
    return _check("reject_research_only_artifacts_for_live_promotion", reasons)


def _check_webhook_secret(readiness_input: LiveReadinessInput) -> dict[str, Any]:
    secret = _first_present(
        readiness_input.config,
        (
            ("webhook_secret",),
            ("webhook", "secret"),
            ("operator_ui", "secret"),
            ("operator_ui", "webhook_secret"),
            ("operator", "webhook_secret"),
            ("security", "webhook_secret"),
        ),
    )
    normalized = str(secret).strip() if secret is not None else ""
    reasons = []
    if normalized.lower() in DEFAULT_WEBHOOK_SECRET_VALUES:
        reasons.append("webhook_secret_missing_or_default")
    return _check("reject_default_or_missing_webhook_secret", reasons)


def _check_hyperliquid_credentials(readiness_input: LiveReadinessInput) -> dict[str, Any]:
    hyperliquid = _mapping_or_empty(readiness_input.config.get("hyperliquid"))
    account_indicator = _first_present(
        hyperliquid,
        (
            ("account_address",),
            ("vault_address",),
            ("canonical_account_address",),
        ),
    )
    private_key_indicator = _first_present(
        hyperliquid,
        (
            ("private_key",),
            ("private_key_configured",),
            ("has_private_key",),
            ("signing_key_configured",),
            ("agent_wallet_configured",),
        ),
    )
    reasons = []
    if not _truthy(account_indicator):
        reasons.append("missing_hyperliquid_account_indicator")
    if not _truthy(private_key_indicator):
        reasons.append("missing_hyperliquid_signing_credential_indicator")
    return _check("reject_missing_hyperliquid_credential_indicators", reasons)


def _check_risk_caps(readiness_input: LiveReadinessInput) -> dict[str, Any]:
    reasons: list[str] = []
    for field_name in REQUIRED_RISK_CAP_FIELDS:
        value = _first_present(
            readiness_input.config,
            (
                ("risk", field_name),
                ("strategy", field_name),
                (field_name,),
            ),
        )
        numeric_value = _decimal_or_none(value)
        if numeric_value is None:
            reasons.append(f"missing_risk_cap:{field_name}")
        elif numeric_value <= Decimal("0"):
            reasons.append(f"risk_cap_must_be_positive:{field_name}")
    return _check("reject_zero_or_negative_risk_caps", reasons)


def _check_execution_journal_evidence(readiness_input: LiveReadinessInput) -> dict[str, Any]:
    evidence = readiness_input.execution_journal_evidence
    reasons = [
        f"missing_execution_journal_evidence:{field_name}"
        for field_name in REQUIRED_EXECUTION_JOURNAL_EVIDENCE
        if not _journal_evidence_present(evidence, field_name)
    ]
    event_types = {str(item) for item in _sequence_or_empty(evidence.get("event_types"))}
    if not ({"schedule_cancel_set", "schedule_cancel_triggered"} & event_types) and not _journal_evidence_present(
        evidence,
        "schedule_cancel_dead_man_heartbeat",
    ):
        reasons.append("missing_schedule_cancel_event_type_evidence")
    if "reconciliation" not in event_types and not _journal_evidence_present(evidence, "reconciliation_before_live"):
        reasons.append("missing_reconciliation_event_type_evidence")
    return _check("require_execution_journal_evidence_before_live_automation", reasons)


def _check(name: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": not reasons,
        "severity": "blocker",
        "reasons": reasons,
    }


def _boundary_check(name: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": not reasons,
        "severity": "blocker",
        "reasons": reasons,
    }


def _validate_research_artifact_manifest(payload: Mapping[str, Any]) -> list[str]:
    reasons = _validate_research_payload(payload, payload_name="artifact_manifest", require_observe_only=False)
    if not (
        payload.get("artifact_manifest_version")
        or payload.get("schema_version")
        or payload.get("experiment_manifest_version")
        or payload.get("experiment_run_manifest_version")
        or payload.get("pipeline_summary_version")
        or payload.get("data_pipeline_manifest_version")
        or payload.get("data_quality_report_version")
    ):
        reasons.append("artifact_manifest:missing_manifest_version")
    return reasons


def _validate_research_metrics(payload: Mapping[str, Any]) -> list[str]:
    return _validate_research_payload(payload, payload_name="metrics", require_observe_only=False)


def _validate_monitoring_report(payload: Mapping[str, Any]) -> list[str]:
    reasons = _validate_research_payload(payload, payload_name="monitoring_report", require_observe_only=True)
    if not payload.get("monitoring_report_version"):
        reasons.append("monitoring_report:missing_monitoring_report_version")
    for index, alert in enumerate(_sequence_or_empty(payload.get("alerts"))):
        if not isinstance(alert, Mapping):
            reasons.append(f"monitoring_report:alert_not_mapping:{index}")
        elif alert.get("observe_only") is not True:
            reasons.append(f"monitoring_report:alert_not_observe_only:{index}")
    return reasons


def _validate_experiment_manifest(payload: Mapping[str, Any]) -> list[str]:
    reasons = _validate_research_payload(payload, payload_name="experiment_manifest", require_observe_only=True)
    if not payload.get("experiment_manifest_version"):
        reasons.append("experiment_manifest:missing_experiment_manifest_version")
    for index, experiment in enumerate(_sequence_or_empty(payload.get("experiments"))):
        if not isinstance(experiment, Mapping):
            reasons.append(f"experiment_manifest:experiment_not_mapping:{index}")
            continue
        digest = _mapping_or_empty(experiment.get("metrics_digest"))
        if digest.get("promotion_ready") is True:
            reasons.append(f"experiment_manifest:experiment_metrics_promotion_ready:{index}")
        boundary = experiment.get("research_boundary")
        if isinstance(boundary, Mapping) and boundary.get("passed") is not True:
            reasons.append(f"experiment_manifest:experiment_boundary_failed:{index}")
    return reasons


def _validate_research_payload(
    payload: Mapping[str, Any],
    *,
    payload_name: str,
    require_observe_only: bool,
) -> list[str]:
    reasons: list[str] = []
    if payload.get("research_only") is not True:
        reasons.append(f"{payload_name}:research_only_must_be_true")
    if require_observe_only and payload.get("observe_only") is not True:
        reasons.append(f"{payload_name}:observe_only_must_be_true")
    if payload.get("promotion_ready") is True:
        reasons.append(f"{payload_name}:promotion_ready_must_remain_false")
    intended_use = str(payload.get("intended_use") or "").strip().lower()
    if intended_use and intended_use not in RESEARCH_INTENDED_USES:
        reasons.append(f"{payload_name}:intended_use_not_research:{intended_use}")
    if not intended_use:
        reasons.append(f"{payload_name}:missing_research_intended_use")
    for field_name in NON_LIVE_INPUT_FLAGS:
        if field_name not in payload:
            reasons.append(f"{payload_name}:missing_explicit_non_live_flag:{field_name}")
        elif payload.get(field_name) is not False:
            reasons.append(f"{payload_name}:non_live_flag_must_be_false:{field_name}")
    for field_name in LIVE_OUTPUT_FIELDS:
        if payload.get(field_name):
            reasons.append(f"{payload_name}:must_not_emit_live_output_field:{field_name}")
    return reasons


def _runtime_mode(config: Mapping[str, Any]) -> str:
    value = _first_present(config, (("runtime_mode",), ("mode",), ("environment",)))
    return str(value or "").strip().lower()


def _research_job_name(config: Mapping[str, Any]) -> str:
    value = _first_present(config, (("job_type",), ("command",), ("research", "job_type"), ("research", "command")))
    return str(value or "").strip().lower()


def _journal_evidence_present(evidence: Mapping[str, Any], field_name: str) -> bool:
    value = evidence.get(field_name)
    if _truthy(value):
        return True
    evidence_fields = set(str(item) for item in _sequence_or_empty(evidence.get("evidence_fields")))
    return field_name in evidence_fields


def _first_present(config: Mapping[str, Any], paths: tuple[tuple[str, ...], ...]) -> Any:
    for path in paths:
        value = _value_at_path(config, path)
        if value is not None:
            return value
    return None


def _bool_at_any(config: Mapping[str, Any], paths: tuple[tuple[str, ...], ...]) -> bool:
    return any(_truthy(_value_at_path(config, path)) for path in paths)


def _value_at_path(config: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = config
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("expected mapping")
    return value


def _sequence_or_empty(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(value)
    return (value,)


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"false", "0", "no", "none", "null"}
    return bool(value)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
