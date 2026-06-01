from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from tradingbotsuite.config import AppConfig, HyperliquidConfig, ResearchConfig, StrategyConfig, WebhookConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.live.preflight import LivePreflightError, assert_live_preflight
from tradingbotsuite.promotion.artifact_validator import (
    load_artifact_manifest,
    validate_artifact_for_live_input,
    validate_artifact_for_runtime_mode,
)
from tradingbotsuite.runtime import build_engine


def _research_manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "artifact_manifest_version": "stage7-research-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "intended_use": "research_observe_only",
                "live_signal_input": False,
                "position_sizing_input": False,
                "live_execution_input": False,
            }
        ),
        encoding="utf-8",
    )
    return path


def _safe_live_config(tmp_path: Path, artifact_manifest_path: Path | None = None) -> AppConfig:
    return AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        db_path=tmp_path / "live.sqlite3",
        webhook=WebhookConfig(secret="live-webhook-secret"),
        strategy=StrategyConfig(max_daily_loss_quote=Decimal("25"), max_open_risk_notional=Decimal("100")),
        hyperliquid=HyperliquidConfig(
            base_url="https://api.hyperliquid-testnet.xyz",
            account_address="0x1111111111111111111111111111111111111111",
            private_key="0x" + "2" * 64,
            enable_live=True,
        ),
        research=ResearchConfig(artifact_manifest_path=artifact_manifest_path),
    )


def test_artifact_validator_rejects_research_only_artifact_for_live_input(tmp_path: Path) -> None:
    manifest_path = _research_manifest(tmp_path / "artifact_manifest.json")

    result = validate_artifact_for_live_input(load_artifact_manifest(manifest_path), manifest_path=manifest_path)

    assert not result.allowed
    assert "research_only_artifact_rejected_for_live_input" in result.reasons
    assert "observe_only_artifact_rejected_for_live_input" in result.reasons
    assert "promotion_ready_false_or_missing" in result.reasons


@pytest.mark.parametrize("runtime_mode", [RuntimeMode.LIVE, RuntimeMode.PAPER, RuntimeMode.SHADOW])
def test_artifact_validator_rejects_minimal_unknown_promoted_manifest_for_runtime_modes(
    tmp_path: Path,
    runtime_mode: RuntimeMode,
) -> None:
    manifest_path = tmp_path / "minimal_manifest.json"
    manifest_path.write_text(
        json.dumps({"artifact_manifest_version": "unknown-v1", "promotion_ready": True}),
        encoding="utf-8",
    )

    result = validate_artifact_for_runtime_mode(
        load_artifact_manifest(manifest_path),
        runtime_mode=runtime_mode,
        manifest_path=manifest_path,
    )

    assert not result.allowed
    if runtime_mode == RuntimeMode.LIVE:
        assert "live_signal_input_required_for_live_input" in result.reasons
        assert "runtime_mode_missing_or_ambiguous" in result.reasons
    elif runtime_mode == RuntimeMode.PAPER:
        assert "paper_runtime_artifact_loading_not_supported" in result.reasons
    else:
        assert "shadow_runtime_requires_promotion_candidate" in result.reasons


def test_live_preflight_rejects_research_manifest_as_live_input(tmp_path: Path) -> None:
    manifest_path = _research_manifest(tmp_path / "artifact_manifest.json")

    with pytest.raises(LivePreflightError) as exc_info:
        assert_live_preflight(_safe_live_config(tmp_path, manifest_path), command="serve")

    blockers = exc_info.value.report.blockers
    assert "runtime_artifact_rejected:research_only_artifact_rejected_for_live_input" in blockers
    assert "runtime_artifact_rejected:research_intended_use_rejected:research_observe_only" in blockers


def test_preflight_checks_artifacts_in_paper_and_shadow_modes(tmp_path: Path) -> None:
    manifest_path = _research_manifest(tmp_path / "artifact_manifest.json")

    paper_config = replace(_safe_live_config(tmp_path, manifest_path), runtime_mode=RuntimeMode.PAPER)
    shadow_config = replace(_safe_live_config(tmp_path, manifest_path), runtime_mode=RuntimeMode.SHADOW)

    with pytest.raises(LivePreflightError) as paper_exc:
        assert_live_preflight(paper_config, command="serve")
    with pytest.raises(LivePreflightError) as shadow_exc:
        assert_live_preflight(shadow_config, command="serve")

    assert "runtime_artifact_rejected:paper_runtime_artifact_loading_not_supported" in paper_exc.value.report.blockers
    assert "runtime_artifact_rejected:shadow_runtime_requires_promotion_candidate" in shadow_exc.value.report.blockers


def test_runtime_rejects_research_artifact_before_scorer_can_load(tmp_path: Path) -> None:
    manifest_path = _research_manifest(tmp_path / "artifact_manifest.json")
    config = replace(_safe_live_config(tmp_path), research=ResearchConfig(artifact_manifest_path=manifest_path))

    with pytest.raises(LivePreflightError):
        build_engine(config)

