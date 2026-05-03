from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from tradingbotsuite.config import AppConfig, HyperliquidConfig, StrategyConfig, WebhookConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.live.preflight import LivePreflightError, assert_live_preflight, build_live_preflight_report


def _safe_live_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "live.sqlite3",
        webhook=WebhookConfig(secret="live-webhook-secret"),
        strategy=StrategyConfig(
            max_daily_loss_quote=Decimal("25"),
            max_open_risk_notional=Decimal("100"),
            max_spread_bps=Decimal("25"),
        ),
        hyperliquid=HyperliquidConfig(
            base_url="https://api.hyperliquid-testnet.xyz",
            account_address="0x1111111111111111111111111111111111111111",
            private_key="0x" + "2" * 64,
            enable_live=True,
            max_basis_bps=Decimal("75"),
        ),
    )


def test_live_preflight_fails_closed_on_default_unsafe_live_config() -> None:
    config = replace(AppConfig(), runtime_mode=RuntimeMode.LIVE)

    with pytest.raises(LivePreflightError) as exc_info:
        assert_live_preflight(config, command="serve")

    blockers = set(exc_info.value.report.blockers)
    assert "default_or_missing_webhook_secret" in blockers
    assert "risk_cap_must_be_positive:max_daily_loss_quote" in blockers
    assert "risk_cap_must_be_positive:max_open_risk_notional" in blockers
    assert "hyperliquid_live_not_enabled" in blockers
    assert "missing_hyperliquid_account_address" in blockers
    assert "missing_hyperliquid_private_key" in blockers


def test_live_preflight_passes_safe_testnet_config_and_surfaces_basis_checks(tmp_path: Path) -> None:
    report = assert_live_preflight(_safe_live_config(tmp_path), command="smoke-live")

    assert report.passed
    assert report.live_basis_checks["binance_surface"] == "market_data_health"
    assert report.live_basis_checks["hyperliquid_surface"] == "execution_health.basis_health"
    assert report.live_basis_checks["max_basis_bps"] == "75"


@pytest.mark.parametrize("command", ["run-hmm-knn-experiments", "plan-feature-ablation", "plan-stage12-research"])
def test_live_preflight_rejects_research_command_even_when_other_live_checks_pass(tmp_path: Path, command: str) -> None:
    with pytest.raises(LivePreflightError) as exc_info:
        assert_live_preflight(_safe_live_config(tmp_path), command=command)

    assert f"live_runtime_rejects_research_command:{command}" in exc_info.value.report.blockers


def test_execution_journal_evidence_contract_reports_missing_live_order_evidence(tmp_path: Path) -> None:
    report = build_live_preflight_report(
        _safe_live_config(tmp_path),
        command="serve",
        execution_journal_evidence={"event_types": ["order_intent"], "evidence_fields": ["deterministic_cloid"]},
    )

    assert not report.passed
    assert "missing_execution_journal_evidence:reconciliation" in report.blockers
    assert "missing_execution_journal_evidence:schedule_cancel_set" in report.blockers
