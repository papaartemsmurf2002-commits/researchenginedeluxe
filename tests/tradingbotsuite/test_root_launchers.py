from __future__ import annotations

import sys
from pathlib import Path

from tradingbotsuite.config import AppConfig, OperatorUIConfig, ResearchConfig
from tradingbotsuite.core.models import RuntimeMode


def _config_with_nondefault_sections(tmp_path: Path) -> AppConfig:
    return AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        research=ResearchConfig(
            output_dir=tmp_path / "research",
            config_path=tmp_path / "research_config.json",
            artifact_manifest_path=tmp_path / "artifact_manifest.json",
        ),
        operator_ui=OperatorUIConfig(
            enabled=True,
            secret="operator-secret",
            session_cookie_name="operator-session",
        ),
    )


def test_root_run_manual_runtime_override_preserves_full_config(monkeypatch, tmp_path: Path) -> None:
    import run_manual

    base_config = _config_with_nondefault_sections(tmp_path)
    captured: dict[str, AppConfig] = {}

    async def fake_run_manual_shell(config: AppConfig) -> None:
        captured["config"] = config

    monkeypatch.setattr(run_manual.AppConfig, "from_env", classmethod(lambda cls: base_config))
    monkeypatch.setattr(run_manual, "assert_live_preflight", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_manual, "run_manual_shell", fake_run_manual_shell)
    monkeypatch.setattr(sys, "argv", ["run_manual.py", "live"])

    run_manual.main()

    config = captured["config"]
    assert config.runtime_mode == RuntimeMode.LIVE
    assert config.research == base_config.research
    assert config.operator_ui == base_config.operator_ui
    assert config.webhook == base_config.webhook
    assert config.strategy == base_config.strategy
    assert config.binance == base_config.binance
    assert config.hyperliquid == base_config.hyperliquid


def test_main_manual_runtime_override_preserves_full_config(monkeypatch, tmp_path: Path) -> None:
    from tradingbotsuite import main

    base_config = _config_with_nondefault_sections(tmp_path)
    monkeypatch.setattr(sys, "argv", ["tradingbot", "manual", "--mode", "shadow"])

    args = main.parse_args()
    assert args.command == "manual"

    overridden = main._config_with_runtime_mode(base_config, args.mode)
    assert overridden.runtime_mode == RuntimeMode.SHADOW
    assert overridden.research == base_config.research
    assert overridden.operator_ui == base_config.operator_ui
    assert overridden.webhook == base_config.webhook
    assert overridden.strategy == base_config.strategy
    assert overridden.binance == base_config.binance
    assert overridden.hyperliquid == base_config.hyperliquid


def test_main_research_config_override_preserves_operator_ui_and_other_sections(tmp_path: Path) -> None:
    from tradingbotsuite import main

    base_config = _config_with_nondefault_sections(tmp_path)
    override_path = tmp_path / "override_research_config.json"

    overridden = main._config_with_research_config_path(base_config, str(override_path))

    assert overridden.runtime_mode == base_config.runtime_mode
    assert overridden.research.output_dir == base_config.research.output_dir
    assert overridden.research.config_path == override_path
    assert overridden.research.artifact_manifest_path == base_config.research.artifact_manifest_path
    assert overridden.operator_ui == base_config.operator_ui
    assert overridden.webhook == base_config.webhook
    assert overridden.strategy == base_config.strategy
    assert overridden.binance == base_config.binance
    assert overridden.hyperliquid == base_config.hyperliquid
