from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.promotion.artifact_validator import load_artifact_manifest, validate_artifact_for_live_input
from tradingbotsuite.research.live_readiness import DEFAULT_WEBHOOK_SECRET_VALUES, RESEARCH_JOB_NAMES


LIVE_PREFLIGHT_VERSION = "live-preflight-stage10-v1"
LIVE_RESEARCH_COMMANDS = frozenset(RESEARCH_JOB_NAMES) | frozenset(
    {
        "benchmark-research-experiment",
        "build-dataset",
        "calibrate-model",
        "collect-binance-bars",
        "fetch-binance-vision",
        "fetch-crypto-lake",
        "monitor-hmm-knn",
        "replay-eval",
        "replay-hmm-knn",
        "run-hmm-knn-experiments",
        "train-model",
        "write-hmm-knn-sweep-datasets",
    }
)


class LivePreflightError(RuntimeError):
    def __init__(self, report: "LivePreflightReport") -> None:
        self.report = report
        super().__init__("live preflight failed: " + ", ".join(report.blockers))


@dataclass(frozen=True, slots=True)
class LivePreflightReport:
    preflight_version: str
    runtime_mode: str
    command: str | None
    passed: bool
    blockers: tuple[str, ...]
    checks: tuple[dict[str, Any], ...]
    live_basis_checks: dict[str, Any]
    execution_journal_evidence: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def build_live_preflight_report(
    config: AppConfig,
    *,
    command: str | None = None,
    artifact_manifest_path: Path | None = None,
    execution_journal_evidence: Mapping[str, Any] | None = None,
) -> LivePreflightReport:
    artifact_path = artifact_manifest_path or config.research.artifact_manifest_path
    checks = [
        _check_webhook_secret(config),
        _check_operator_secret(config),
        _check_risk_caps(config),
        _check_hyperliquid_live_config(config),
        _check_reconciliation_capability(config),
        _check_research_command(config, command),
        _check_research_artifact(artifact_path),
        _check_basis_surfaces(config),
        _check_execution_journal_evidence(execution_journal_evidence),
    ]
    active_checks = checks if config.runtime_mode == RuntimeMode.LIVE else []
    blockers = tuple(reason for check in active_checks if not check["passed"] for reason in check["reasons"])
    return LivePreflightReport(
        preflight_version=LIVE_PREFLIGHT_VERSION,
        runtime_mode=str(config.runtime_mode),
        command=command,
        passed=not blockers,
        blockers=blockers,
        checks=tuple(active_checks),
        live_basis_checks={
            "binance_surface": "market_data_health",
            "hyperliquid_surface": "execution_health.basis_health",
            "max_basis_bps": str(config.hyperliquid.max_basis_bps),
            "max_spread_bps": str(config.strategy.max_spread_bps),
        },
        execution_journal_evidence=dict(execution_journal_evidence or {}),
    )


def assert_live_preflight(
    config: AppConfig,
    *,
    command: str | None = None,
    artifact_manifest_path: Path | None = None,
    execution_journal_evidence: Mapping[str, Any] | None = None,
) -> LivePreflightReport:
    report = build_live_preflight_report(
        config,
        command=command,
        artifact_manifest_path=artifact_manifest_path,
        execution_journal_evidence=execution_journal_evidence,
    )
    if not report.passed:
        raise LivePreflightError(report)
    return report


def assert_research_command_not_live(config: AppConfig, command: str) -> None:
    normalized = str(command or "").strip().lower()
    if config.runtime_mode == RuntimeMode.LIVE and normalized in LIVE_RESEARCH_COMMANDS:
        report = build_live_preflight_report(config, command=command)
        blockers = (*report.blockers, f"live_runtime_rejects_research_command:{normalized}")
        raise LivePreflightError(
            LivePreflightReport(
                preflight_version=report.preflight_version,
                runtime_mode=report.runtime_mode,
                command=command,
                passed=False,
                blockers=tuple(dict.fromkeys(blockers)),
                checks=report.checks,
                live_basis_checks=report.live_basis_checks,
                execution_journal_evidence=report.execution_journal_evidence,
            )
        )


def _check(name: str, reasons: list[str]) -> dict[str, Any]:
    return {"name": name, "passed": not reasons, "severity": "blocker", "reasons": reasons}


def _check_webhook_secret(config: AppConfig) -> dict[str, Any]:
    secret = str(config.webhook.secret or "").strip().lower()
    reasons = ["default_or_missing_webhook_secret"] if secret in DEFAULT_WEBHOOK_SECRET_VALUES else []
    return _check("reject_default_webhook_secret", reasons)


def _check_operator_secret(config: AppConfig) -> dict[str, Any]:
    if not config.operator_ui.enabled:
        return _check("reject_default_operator_secret", [])
    secret = str(config.operator_ui.secret or "").strip().lower()
    reasons = ["default_or_missing_operator_secret"] if secret in DEFAULT_WEBHOOK_SECRET_VALUES else []
    return _check("reject_default_operator_secret", reasons)


def _check_risk_caps(config: AppConfig) -> dict[str, Any]:
    reasons = []
    if config.strategy.max_daily_loss_quote <= Decimal("0"):
        reasons.append("risk_cap_must_be_positive:max_daily_loss_quote")
    if config.strategy.max_open_risk_notional <= Decimal("0"):
        reasons.append("risk_cap_must_be_positive:max_open_risk_notional")
    return _check("reject_zero_or_disabled_risk_caps", reasons)


def _check_hyperliquid_live_config(config: AppConfig) -> dict[str, Any]:
    reasons = []
    if not config.hyperliquid.enable_live:
        reasons.append("hyperliquid_live_not_enabled")
    if not config.hyperliquid.account_address:
        reasons.append("missing_hyperliquid_account_address")
    if not config.hyperliquid.private_key:
        reasons.append("missing_hyperliquid_private_key")
    return _check("require_hyperliquid_account_and_signer", reasons)


def _check_reconciliation_capability(config: AppConfig) -> dict[str, Any]:
    reasons = []
    if config.strategy.max_reconcile_gap_ms <= 0:
        reasons.append("max_reconcile_gap_must_be_positive")
    return _check("require_reconciliation_capability", reasons)


def _check_research_command(config: AppConfig, command: str | None) -> dict[str, Any]:
    normalized = str(command or "").strip().lower()
    reasons = []
    if config.runtime_mode == RuntimeMode.LIVE and normalized in LIVE_RESEARCH_COMMANDS:
        reasons.append(f"live_runtime_rejects_research_command:{normalized}")
    return _check("reject_research_command_in_live_mode", reasons)


def _check_research_artifact(path: Path | None) -> dict[str, Any]:
    if path is None:
        return _check("reject_research_artifact_as_live_input", [])
    if not Path(path).exists():
        return _check("reject_research_artifact_as_live_input", [f"artifact_manifest_missing:{path}"])
    manifest = load_artifact_manifest(path)
    result = validate_artifact_for_live_input(manifest, manifest_path=Path(path))
    reasons = [f"live_artifact_rejected:{reason}" for reason in result.reasons]
    return _check("reject_research_artifact_as_live_input", reasons)


def _check_basis_surfaces(config: AppConfig) -> dict[str, Any]:
    reasons = []
    if config.hyperliquid.max_basis_bps <= Decimal("0"):
        reasons.append("hyperliquid_max_basis_bps_must_be_positive")
    if config.strategy.max_spread_bps <= Decimal("0"):
        reasons.append("strategy_max_spread_bps_must_be_positive")
    return _check("surface_binance_hyperliquid_basis_checks", reasons)


def _check_execution_journal_evidence(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    if not evidence:
        return _check("verify_execution_journal_evidence", [])
    required = {
        "deterministic_cloid",
        "order_intent",
        "order_filled",
        "order_cancel_requested",
        "reconciliation",
        "schedule_cancel_set",
    }
    event_types = {str(item) for item in evidence.get("event_types", ())}
    fields = {str(item) for item in evidence.get("evidence_fields", ())}
    present = event_types | fields
    reasons = [f"missing_execution_journal_evidence:{item}" for item in sorted(required - present)]
    return _check("verify_execution_journal_evidence", reasons)
