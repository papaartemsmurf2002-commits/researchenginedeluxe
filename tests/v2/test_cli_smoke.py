from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tradingbotsuite.v2.cli.main import build_parser
from tradingbotsuite.v2.config.settings import default_settings


ROOT = Path(__file__).resolve().parents[2]


def test_v2_cli_help_states_research_only_boundary() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    normalized_help = " ".join(help_text.split())

    assert "Research-only" in normalized_help
    assert "Non-live" in normalized_help
    assert "non-paper" in normalized_help
    assert "no order placement" in normalized_help
    assert "no sizing instructions" in normalized_help


def test_v2_cli_module_help_runs() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-m", "tradingbotsuite.v2.cli.main", "--help"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Research-only" in result.stdout
    assert "Non-live" in result.stdout
    assert "no order placement" in result.stdout


def test_default_v2_settings_match_phase1_scope() -> None:
    settings = default_settings()

    assert settings.primary_venue == "hyperliquid"
    assert settings.market_type == "perpetual"
    assert settings.min_day_notional_usd == 5_000_000
    assert settings.coverage_min == 0.98
    assert settings.min_usable_months == 6
    assert settings.preferred_usable_months == 12
