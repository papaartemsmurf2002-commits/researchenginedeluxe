from __future__ import annotations

from tradingbotsuite.research.live_readiness import (
    LIVE_READINESS_REPORT_VERSION,
    build_live_readiness_report,
)


def _future_config(**updates: object) -> dict[str, object]:
    config: dict[str, object] = {
        "runtime_mode": "LIVE",
        "job_type": "serve",
        "webhook": {"secret": "not-a-default-secret"},
        "operator_ui": {"secret": "not-a-default-operator-secret"},
        "hyperliquid": {
            "account_address": "0xabc",
            "private_key": "configured-outside-report",
        },
        "strategy": {
            "max_daily_loss_quote": "100",
            "max_open_risk_notional": "1000",
        },
    }
    config.update(updates)
    return config


def _future_evidence(**updates: object) -> dict[str, object]:
    evidence: dict[str, object] = {
        "deterministic_cloid": True,
        "reduce_only_exits": True,
        "schedule_cancel_dead_man_heartbeat": True,
        "reconciliation_before_live": True,
        "event_types": [
            "order_intent",
            "order_submitted",
            "order_filled",
            "schedule_cancel_set",
            "reconciliation",
        ],
    }
    evidence.update(updates)
    return evidence


def _blocker_codes(report: dict[str, object]) -> set[str]:
    return set(report["blockers"])  # type: ignore[arg-type]


def test_live_readiness_rejects_research_job_and_research_only_artifact() -> None:
    report = build_live_readiness_report(
        config=_future_config(job_type="research-hmm-knn"),
        artifacts=[
            {
                "artifact_manifest_version": "hmm-knn-test",
                "research_only": True,
                "observe_only": True,
                "promotion_target": "live",
            }
        ],
        execution_journal_evidence=_future_evidence(),
    )

    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["promotion_ready"] is False
    assert report["passed"] is False
    assert {
        "live_runtime_rejects_research_job:research-hmm-knn",
        "live_runtime_rejects_research_artifact:0",
        "research_only_artifact_not_live_promotable:0",
    }.issubset(_blocker_codes(report))


def test_live_readiness_rejects_default_webhook_missing_credentials_and_bad_risk_caps() -> None:
    report = build_live_readiness_report(
        config={
            "runtime_mode": "LIVE",
            "job_type": "serve",
            "webhook": {"secret": "change-me"},
            "hyperliquid": {},
            "strategy": {
                "max_daily_loss_quote": "0",
                "max_open_risk_notional": "-1",
            },
        },
        artifacts=[],
        execution_journal_evidence=_future_evidence(),
    )

    assert report["passed"] is False
    assert {
        "webhook_secret_missing_or_default",
        "missing_hyperliquid_account_indicator",
        "missing_hyperliquid_signing_credential_indicator",
        "risk_cap_must_be_positive:max_daily_loss_quote",
        "risk_cap_must_be_positive:max_open_risk_notional",
    }.issubset(_blocker_codes(report))


def test_live_readiness_rejects_missing_execution_journal_evidence() -> None:
    report = build_live_readiness_report(
        config=_future_config(),
        artifacts=[],
        execution_journal_evidence={
            "event_types": ["order_intent", "order_filled"],
        },
    )

    assert report["passed"] is False
    assert {
        "missing_execution_journal_evidence:deterministic_cloid",
        "missing_execution_journal_evidence:reduce_only_exits",
        "missing_execution_journal_evidence:schedule_cancel_dead_man_heartbeat",
        "missing_execution_journal_evidence:reconciliation_before_live",
        "missing_schedule_cancel_event_type_evidence",
        "missing_reconciliation_event_type_evidence",
    }.issubset(_blocker_codes(report))


def test_live_readiness_future_style_payload_passes_advisory_checks_but_never_promotes() -> None:
    report = build_live_readiness_report(
        payload={
            "config": _future_config(),
            "artifacts": [
                {
                    "artifact_manifest_version": "future-production-candidate",
                    "research_only": False,
                    "observe_only": False,
                    "promotion_target": "live",
                    "promotion_ready": True,
                }
            ],
            "execution_journal_evidence": _future_evidence(),
        }
    )

    assert report["live_readiness_report_version"] == LIVE_READINESS_REPORT_VERSION
    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["passed"] is True
    assert report["promotion_ready"] is False
    assert report["blockers"] == []
    assert all(check["passed"] is True for check in report["checks"])
    assert report["summary"] == {
        "runtime_mode": "live",
        "artifact_count": 1,
        "failed_check_count": 0,
        "passed_check_count": 6,
    }
