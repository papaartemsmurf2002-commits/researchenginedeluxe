from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from tradingbotsuite import main
from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research.data_pipeline import (
    ArchiveBackedResearchClient,
    archive_provider_descriptors,
    prepare_hmm_knn_research_data,
)
from tradingbotsuite.research.market_journal import read_market_journal_for_replay


def _write_kline_csv(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
                "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                "60000,101,102,100,101.5,2,119999,203,20,1,101,0",
                "0,100,101,99,100.5,1,59999,100,10,0.5,50,0",
            ]
        ),
        encoding="utf-8",
    )


def _write_spec(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _base_spec(tmp_path: Path, **updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "version": "test-provider-pipeline",
        "asset_scope": ["BTCUSDT"],
        "output_dir": str(tmp_path / "pipeline_out"),
        "providers": [],
        "dataset_stage": {"enabled": False},
        "evidence_stage": {"enabled": False},
    }
    payload.update(updates)
    return payload


def test_archive_provider_descriptors_cover_expected_contract_sources() -> None:
    descriptors = {descriptor["source_name"]: descriptor for descriptor in archive_provider_descriptors()}

    assert set(descriptors) == {"binance_vision", "crypto_lake", "hyperliquid_archive"}
    assert descriptors["binance_vision"]["implemented_for_ingestion"] is True
    assert descriptors["crypto_lake"]["implemented_for_ingestion"] is False
    assert descriptors["hyperliquid_archive"]["implemented_for_ingestion"] is False


def test_prepare_hmm_knn_research_data_intake_writes_provider_journal_and_quality_manifests(tmp_path: Path) -> None:
    source_path = tmp_path / "BTCUSDT-1m-klines.csv"
    _write_kline_csv(source_path)
    spec_path = _write_spec(
        tmp_path / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            providers=[
                {
                    "source_name": "binance_vision",
                    "enabled": True,
                    "inputs": [
                        {
                            "path": source_path.name,
                            "symbol": "BTCUSDT",
                            "data_family": "kline",
                            "interval": "1m",
                        }
                    ],
                },
                {"source_name": "crypto_lake", "enabled": True, "symbol": "BTCUSDT", "data_family": "trade"},
                {
                    "source_name": "hyperliquid_archive",
                    "enabled": True,
                    "symbol": "BTCUSDT",
                    "data_family": "order_event",
                },
            ],
        ),
    )

    result = prepare_hmm_knn_research_data(spec_path=spec_path, stage="intake")

    intake = json.loads(result.intake_manifest_path.read_text(encoding="utf-8"))
    quality = json.loads(result.data_quality_report_path.read_text(encoding="utf-8"))
    journal_manifest = json.loads(result.market_journal_manifest_path.read_text(encoding="utf-8"))
    replayed = read_market_journal_for_replay(
        result.output_dir / "market_journal.jsonl",
        manifest_path=result.market_journal_manifest_path,
    )

    assert intake["research_only"] is True
    assert intake["observe_only"] is True
    assert intake["promotion_ready"] is False
    assert intake["stage_status"]["intake"]["status"] == "completed"
    assert intake["stage_status"]["intake"]["archive_manifest_count"] == 3
    assert {provider["status"] for provider in intake["providers"]} == {
        "completed",
        "not_implemented_for_ingestion",
    }
    unsupported_manifests = [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for provider in intake["providers"]
        if provider["status"] == "not_implemented_for_ingestion"
        for path in provider["manifest_paths"]
    ]
    assert {manifest["source_name"] for manifest in unsupported_manifests} == {
        "crypto_lake",
        "hyperliquid_archive",
    }
    assert all(manifest["ingestion_status"] == "not_implemented_for_ingestion" for manifest in unsupported_manifests)
    assert all(manifest["zero_filled_fields"] == [] for manifest in unsupported_manifests)
    assert journal_manifest["event_count"] == 2
    assert journal_manifest["event_counts_by_family"] == {"kline": 2}
    assert [(event["source_event_time_ms"], event["normalized_payload"]["open_time_ms"]) for event in replayed] == [
        (0, 0),
        (60_000, 60_000),
    ]
    assert all(event["local_receive_time_ms"] is None for event in replayed)
    assert quality["research_only"] is True
    assert quality["observe_only"] is True
    assert quality["promotion_ready"] is False
    assert quality["manifest_count"] == 4
    assert quality["zero_row_manifest_count"] == 2
    assert quality["non_promotable_count"] == 4


def test_archive_backed_research_client_excludes_future_bars_and_preserves_missing_context(tmp_path: Path) -> None:
    source_path = tmp_path / "BTCUSDT-1m-klines.csv"
    _write_kline_csv(source_path)
    spec_path = _write_spec(
        tmp_path / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            providers=[
                {
                    "source_name": "binance_vision",
                    "inputs": [
                        {
                            "path": source_path.name,
                            "symbol": "BTCUSDT",
                            "data_family": "kline",
                            "interval": "1m",
                        }
                    ],
                }
            ],
        ),
    )
    result = prepare_hmm_knn_research_data(spec_path=spec_path, stage="intake")
    intake = json.loads(result.intake_manifest_path.read_text(encoding="utf-8"))
    archive_manifests = [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for path in intake["archive_manifest_paths"]
    ]
    client = ArchiveBackedResearchClient(archive_manifests)

    bars = asyncio.run(
        client.fetch_historical_closed_bar_range("BTCUSDT", start_time_ms=0, end_time_ms=0, interval="1m")
    )
    funding_context = asyncio.run(client.fetch_funding_context("BTCUSDT", as_of_ms=60_000))

    assert [bar.time_ms for bar in bars] == [0]
    assert funding_context["missing_funding_context"] is True
    assert funding_context["context_source"] == "archive_backed_research_client"
    assert client.coverage_summary()["bar_series"] == {"BTCUSDT:1m": 2}


def test_prepare_hmm_knn_research_data_dataset_stage_reports_no_signal_failure(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            dataset_stage={
                "enabled": True,
                "research_config": "configs/v2_btc_research.json",
                "db_path": str(tmp_path / "empty.sqlite3"),
            },
        ),
    )

    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="dataset",
        app_config=AppConfig(
            db_path=tmp_path / "empty.sqlite3",
            research=ResearchConfig(output_dir=tmp_path / "research"),
        ),
    )

    intake = json.loads(result.intake_manifest_path.read_text(encoding="utf-8"))

    assert result.dataset_manifest_path is None
    assert intake["stage_status"]["dataset"]["status"] == "failed"
    assert intake["stage_status"]["dataset"]["error_type"] == "ValueError"
    assert "no signals found for BTCUSDT" in intake["stage_status"]["dataset"]["error"]


def test_prepare_hmm_knn_research_data_evidence_stage_skips_without_dataset(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            evidence_stage={
                "enabled": True,
                "hmm_knn_config": "configs/v2_btc_hmm_multi_knn_research.json",
            },
        ),
    )

    result = prepare_hmm_knn_research_data(spec_path=spec_path, stage="evidence")
    intake = json.loads(result.intake_manifest_path.read_text(encoding="utf-8"))

    assert result.evidence_manifest_path is None
    assert intake["stage_status"]["dataset"]["status"] == "skipped"
    assert intake["stage_status"]["evidence"] == {
        "status": "skipped",
        "reason": "dataset_not_available",
    }


def test_prepare_hmm_knn_research_data_cli_command_runs_intake(tmp_path: Path, monkeypatch) -> None:
    spec_path = _write_spec(tmp_path / "pipeline_spec.json", _base_spec(tmp_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tradingbot",
            "prepare-hmm-knn-research-data",
            "--spec",
            str(spec_path),
            "--stage",
            "intake",
        ],
    )

    args = main.parse_args()
    payload = main._run_prepare_hmm_knn_research_data_command(args)

    assert payload["output_dir"] == str(tmp_path / "pipeline_out")
    assert Path(str(payload["data_intake_manifest_path"])).exists()
    assert Path(str(payload["data_quality_report_path"])).exists()
    assert Path(str(payload["market_journal_manifest_path"])).exists()
