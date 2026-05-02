from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_root_launchers_delegate_through_live_preflight() -> None:
    for launcher in ("run_server.py", "run_manual.py", "run_live_smoke.py"):
        source = _read(launcher)
        assert "assert_live_preflight" in source


def test_root_manual_launcher_uses_canonical_runtime_mode_override() -> None:
    source = _read("run_manual.py")

    assert "from tradingbotsuite.main import _config_with_runtime_mode" in source
    assert "_config_with_runtime_mode(config, sys.argv[1])" in source


def test_canonical_cli_guards_live_research_commands() -> None:
    source = _read("src/tradingbotsuite/main.py")

    assert "assert_research_command_not_live" in source
    assert "_config_for_command(args.command)" in source
    assert 'command="serve"' in source

