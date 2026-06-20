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


def test_rapid_strategy_sandbox_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="run-rapid-strategy-sandbox",
        spec=str(tmp_path / "missing_spec.json"),
        strategy_catalog=str(tmp_path / "missing_catalog.csv"),
        venue_archives=str(tmp_path / "missing_venues.json"),
        market_data=str(tmp_path / "missing_market.csv"),
        output_dir=str(outside_root),
        min_request_score=0.0,
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_rapid_strategy_sandbox_command(args)

    assert not outside_root.exists()


def test_audit_rapid_strategy_sandbox_archives_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="audit-rapid-strategy-sandbox-archives",
        venue_archives=str(tmp_path / "missing_venues.json"),
        market_data=None,
        output_dir=str(outside_root),
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_audit_rapid_strategy_sandbox_archives_command(args)

    assert not outside_root.exists()


def test_summarize_rapid_strategy_sandbox_archive_coverage_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="summarize-rapid-strategy-sandbox-archive-coverage",
        venue_archives=str(tmp_path / "missing_venues.json"),
        market_data=None,
        output_dir=str(outside_root),
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_summarize_rapid_strategy_sandbox_archive_coverage_command(args)

    assert not outside_root.exists()


def test_build_rapid_strategy_sandbox_archive_manifest_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="build-rapid-strategy-sandbox-archive-manifest",
        archive_root=[str(tmp_path / "missing_archive_root")],
        output_dir=str(outside_root),
        venue=None,
        symbol=None,
        data_family=None,
        interval=None,
        max_files=100,
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_build_rapid_strategy_sandbox_archive_manifest_command(args)

    assert not outside_root.exists()


def test_build_rapid_strategy_sandbox_strategy_catalog_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="build-rapid-strategy-sandbox-strategy-catalog",
        catalog_root=[str(tmp_path / "missing_catalog_root")],
        output_dir=str(outside_root),
        max_files=100,
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_build_rapid_strategy_sandbox_strategy_catalog_command(args)

    assert not outside_root.exists()


def test_run_rapid_strategy_sandbox_iteration_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="run-rapid-strategy-sandbox-iteration",
        spec=None,
        strategy_catalog=None,
        catalog_root=[str(tmp_path / "missing_catalog_root")],
        venue_archives=None,
        archive_root=[str(tmp_path / "missing_archive_root")],
        output_dir=str(outside_root),
        run_id=None,
        window_start="2024-01-01",
        window_end="2024-12-31",
        holding_periods="1",
        round_trip_cost_bps=8.0,
        min_trades=5,
        max_evidence_requests=10,
        rank_top_n=100,
        min_request_score=0.0,
        catalog_max_files=100,
        archive_max_files=100,
        archive_venue=None,
        archive_symbol=None,
        archive_data_family=None,
        archive_interval=None,
        leaderboard_max_runs=100,
        leaderboard_top_n=100,
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_rapid_strategy_sandbox_iteration_command(args)

    assert not outside_root.exists()


def test_preflight_rapid_strategy_sandbox_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="preflight-rapid-strategy-sandbox",
        spec=str(tmp_path / "missing_spec.json"),
        strategy_catalog=str(tmp_path / "missing_catalog.csv"),
        venue_archives=str(tmp_path / "missing_venues.json"),
        market_data=None,
        output_dir=str(outside_root),
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_preflight_rapid_strategy_sandbox_command(args)

    assert not outside_root.exists()


def test_summarize_rapid_strategy_sandbox_rejects_run_dir_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="summarize-rapid-strategy-sandbox",
        run_dir=str(outside_root),
        top_n=10,
        no_write_report=False,
    )

    with pytest.raises(ValueError, match="run_dir must stay inside the configured research output directory"):
        main._run_summarize_rapid_strategy_sandbox_command(args)

    assert not outside_root.exists()


def test_rapid_strategy_sandbox_suite_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="run-rapid-strategy-sandbox-suite",
        suite=str(tmp_path / "missing_suite.json"),
        output_dir=str(outside_root),
        top_n=None,
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_rapid_strategy_sandbox_suite_command(args)

    assert not outside_root.exists()


def test_summarize_rapid_strategy_sandbox_hypotheses_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="summarize-rapid-strategy-sandbox-hypotheses",
        run_dir=str(outside_root),
        suite_dir=None,
        no_write_report=False,
    )

    with pytest.raises(ValueError, match="run_dir must stay inside the configured research output directory"):
        main._run_summarize_rapid_strategy_sandbox_hypotheses_command(args)

    assert not outside_root.exists()


def test_export_rapid_strategy_sandbox_validation_requests_rejects_output_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    run_dir = research_root / "sandbox" / "run"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="export-rapid-strategy-sandbox-validation-requests",
        run_dir=str(run_dir),
        suite_dir=None,
        output_dir=str(outside_root),
    )

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_export_rapid_strategy_sandbox_validation_requests_command(args)

    assert not outside_root.exists()


def test_preflight_rapid_strategy_sandbox_validation_requests_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    bundle_path = research_root / "bundle" / "strict_validation_request_bundle.json"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="preflight-rapid-strategy-sandbox-validation-requests",
        bundle=str(outside_root / "strict_validation_request_bundle.json"),
        output_dir=None,
    )

    with pytest.raises(ValueError, match="bundle must stay inside the configured research output directory"):
        main._run_preflight_rapid_strategy_sandbox_validation_requests_command(args)

    args.bundle = str(bundle_path)
    args.output_dir = str(outside_root)

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_preflight_rapid_strategy_sandbox_validation_requests_command(args)

    assert not outside_root.exists()


def test_export_rapid_strategy_sandbox_venue_expansion_requests_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    catalog_path = research_root / "catalog" / "sandbox_artifact_catalog.json"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="export-rapid-strategy-sandbox-venue-expansion-requests",
        catalog=str(outside_root / "sandbox_artifact_catalog.json"),
        worklist=None,
        output_dir=None,
    )

    with pytest.raises(ValueError, match="catalog must stay inside the configured research output directory"):
        main._run_export_rapid_strategy_sandbox_venue_expansion_requests_command(args)

    args.catalog = str(catalog_path)
    args.worklist = str(outside_root / "worklist.parquet")

    with pytest.raises(ValueError, match="worklist must stay inside the configured research output directory"):
        main._run_export_rapid_strategy_sandbox_venue_expansion_requests_command(args)

    args.worklist = None
    args.output_dir = str(outside_root)

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_export_rapid_strategy_sandbox_venue_expansion_requests_command(args)

    assert not outside_root.exists()


def test_index_rapid_strategy_sandbox_artifacts_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="index-rapid-strategy-sandbox-artifacts",
        root_dir=str(outside_root),
        output_dir=None,
        max_files=100,
        no_write_report=False,
    )

    with pytest.raises(ValueError, match="root_dir must stay inside the configured research output directory"):
        main._run_index_rapid_strategy_sandbox_artifacts_command(args)

    assert not outside_root.exists()


def test_index_rapid_strategy_sandbox_iterations_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="index-rapid-strategy-sandbox-iterations",
        root_dir=str(outside_root),
        output_dir=None,
        max_files=100,
        no_write_report=False,
    )

    with pytest.raises(ValueError, match="root_dir must stay inside the configured research output directory"):
        main._run_index_rapid_strategy_sandbox_iterations_command(args)

    args.root_dir = str(research_root)
    args.output_dir = str(outside_root)

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_index_rapid_strategy_sandbox_iterations_command(args)

    assert not outside_root.exists()


def test_show_rapid_strategy_sandbox_next_action_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"
    inside_catalog = research_root / "catalog" / "sandbox_artifact_catalog.json"
    inside_index = research_root / "index" / "sandbox_iteration_index.json"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="show-rapid-strategy-sandbox-next-action",
        output_root=str(outside_root),
        artifact_catalog=None,
        iteration_index=None,
        output_dir=None,
        max_files=100,
        limit=5,
        no_write_report=False,
    )

    with pytest.raises(ValueError, match="output_root must stay inside the configured research output directory"):
        main._run_show_rapid_strategy_sandbox_next_action_command(args)

    args.output_root = None
    args.artifact_catalog = [str(outside_root / "sandbox_artifact_catalog.json")]

    with pytest.raises(ValueError, match="artifact_catalog must stay inside the configured research output directory"):
        main._run_show_rapid_strategy_sandbox_next_action_command(args)

    args.artifact_catalog = [str(inside_catalog)]
    args.iteration_index = [str(outside_root / "sandbox_iteration_index.json")]

    with pytest.raises(ValueError, match="iteration_index must stay inside the configured research output directory"):
        main._run_show_rapid_strategy_sandbox_next_action_command(args)

    args.iteration_index = [str(inside_index)]
    args.output_dir = str(outside_root)

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_show_rapid_strategy_sandbox_next_action_command(args)

    assert not outside_root.exists()


def test_summarize_rapid_strategy_sandbox_throughput_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="summarize-rapid-strategy-sandbox-throughput",
        root_dir=str(outside_root),
        output_dir=None,
        max_files=100,
        limit=5,
        no_write_report=False,
    )

    with pytest.raises(ValueError, match="root_dir must stay inside the configured research output directory"):
        main._run_summarize_rapid_strategy_sandbox_throughput_command(args)

    args.root_dir = str(research_root)
    args.output_dir = str(outside_root)

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_summarize_rapid_strategy_sandbox_throughput_command(args)

    assert not outside_root.exists()


def test_rank_rapid_strategy_sandbox_artifacts_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="rank-rapid-strategy-sandbox-artifacts",
        root_dir=str(outside_root),
        output_dir=None,
        max_runs=100,
        top_n=10,
        no_write_report=False,
    )

    with pytest.raises(ValueError, match="root_dir must stay inside the configured research output directory"):
        main._run_rank_rapid_strategy_sandbox_artifacts_command(args)

    args.root_dir = str(research_root)
    args.output_dir = str(outside_root)

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_rank_rapid_strategy_sandbox_artifacts_command(args)

    assert not outside_root.exists()


def test_verify_rapid_strategy_sandbox_artifacts_rejects_paths_outside_research_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    inside_target = research_root / "sandbox" / "run"
    outside_root = tmp_path / "outside"

    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    args = argparse.Namespace(
        command="verify-rapid-strategy-sandbox-artifacts",
        target=str(outside_root),
        output_dir=None,
        no_write_report=False,
    )

    with pytest.raises(ValueError, match="target must stay inside the configured research output directory"):
        main._run_verify_rapid_strategy_sandbox_artifacts_command(args)

    args.target = str(inside_target)
    args.output_dir = str(outside_root)

    with pytest.raises(ValueError, match="output_dir must stay inside the configured research output directory"):
        main._run_verify_rapid_strategy_sandbox_artifacts_command(args)

    assert not outside_root.exists()


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
