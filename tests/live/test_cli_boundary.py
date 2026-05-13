from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_exposes_canonical_tradingbotsuite_console_script() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    scripts = pyproject["project"]["scripts"]
    assert scripts["tradingbotsuite"] == "tradingbotsuite.cli:main"
    assert scripts["tradingbot"] == "tradingbot.cli:main"


def test_tradingbotsuite_console_wrapper_reaches_canonical_help(monkeypatch, capsys) -> None:
    from tradingbotsuite import cli

    monkeypatch.setattr(sys, "argv", ["tradingbotsuite", "--help"])

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 0
    assert "Trading Bot Suite" in capsys.readouterr().out


def test_boundary_contract_lists_research_command_registry() -> None:
    from tradingbotsuite.research.command_registry import RESEARCH_COMMANDS

    contract = (ROOT / "docs" / "contracts" / "boundary_contract.md").read_text(encoding="utf-8")
    missing = sorted(command for command in RESEARCH_COMMANDS if f"`{command}`" not in contract)

    assert missing == []


def test_direct_research_cli_output_dir_values_use_shared_resolver() -> None:
    source = (ROOT / "src" / "tradingbotsuite" / "main.py").read_text(encoding="utf-8")

    assert "Path(args.output_dir)" not in source
    assert "_resolve_research_output_dir(args.output_dir" in source


def test_research_cli_output_dir_rejects_outside_configured_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"
    called = False

    def fail_if_called(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("writer should not be called for rejected output_dir")

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    monkeypatch.setattr(main, "ingest_crypto_lake_archive", fail_if_called)

    args = argparse.Namespace(
        command="fetch-crypto-lake",
        symbol="BTCUSDT",
        data_family="liquidation",
        path=str(tmp_path / "source" / "crypto.csv"),
        start_time=None,
        end_time=None,
        exchange=None,
        table=None,
        provider_symbol=None,
        interval=None,
        output_dir=str(outside_root),
        strict=False,
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_fetch_crypto_lake_command(args)

    assert called is False
    assert not outside_root.exists()


def test_research_cli_output_dir_inside_root_keeps_source_path_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    source_path = tmp_path / "source" / "crypto.csv"
    output_dir = (research_root / "provider_ingest").resolve()
    output_dir_arg = "provider_ingest"
    captured: dict[str, object] = {}

    def fake_ingest_crypto_lake_archive(path, **kwargs):
        captured["path"] = path
        captured.update(kwargs)
        return argparse.Namespace(
            output_dir=output_dir,
            data_path=output_dir / "data.jsonl",
            manifest_path=output_dir / "manifest.json",
            row_count=1,
            gap_count=0,
            duplicate_count=0,
            content_hash="sha256:content",
            source_hash="sha256:source",
        )

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    monkeypatch.setattr(main, "ingest_crypto_lake_archive", fake_ingest_crypto_lake_archive)

    args = argparse.Namespace(
        command="fetch-crypto-lake",
        symbol="BTCUSDT",
        data_family="liquidation",
        path=str(source_path),
        start_time=None,
        end_time=None,
        exchange=None,
        table=None,
        provider_symbol="BTC-USDT-PERP",
        interval=None,
        output_dir=output_dir_arg,
        strict=False,
    )

    payload = main._run_fetch_crypto_lake_command(args)

    assert captured["path"] == source_path
    assert captured["output_dir"] == output_dir
    assert payload["manifest_path"] == str(output_dir / "manifest.json")


def test_research_cli_default_output_dir_uses_configured_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    payload = main._run_plan_stage13_readiness_command(argparse.Namespace(output_dir=None))
    output_dir = Path(str(payload["output_dir"]))

    assert output_dir == (research_root / "stage13" / "readiness").resolve()
    assert Path(str(payload["readiness_report_path"])).exists()
