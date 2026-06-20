from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

from tradingbotsuite import main
from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.core.models import DecisionAction, DecisionPacket, RuntimeMode, SignalDirection, SignalIntent
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research.data_pipeline import (
    ArchiveBackedResearchClient,
    archive_provider_descriptors,
    prepare_hmm_knn_research_data,
)
from tradingbotsuite.research.deterministic_datasets import write_hmm_knn_sweep_dataset
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


def _write_many_kline_csv(path: Path, *, row_count: int = 520) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    start_ms = 1712649600000
    price = 70000.0
    for index in range(row_count):
        open_price = price
        close_price = price + 55.0
        high_price = max(open_price, close_price) + 80.0
        low_price = min(open_price, close_price) - 80.0
        open_time_ms = start_ms + (index * 900_000)
        close_time_ms = open_time_ms + 899_999
        rows.append(
            {
                "open_time": open_time_ms,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": 10 + index,
                "close_time": close_time_ms,
                "quote_asset_volume": 1000 + index,
                "number_of_trades": 100 + index,
                "taker_buy_base_asset_volume": 5,
                "taker_buy_quote_asset_volume": 500,
                "ignore": 0,
            }
        )
        price = close_price
    path.write_text(
        "\n".join(
            [
                "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
                "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                *[
                    ",".join(str(row[field]) for field in row)
                    for row in rows
                ],
            ]
        ),
        encoding="utf-8",
    )
    return rows


async def _seed_external_signal_signals(db_path: Path, bars: list[dict[str, object]]) -> None:
    store = SQLiteStore(db_path)
    await store.initialize()
    for offset, time_index in enumerate(range(400, 446), start=1):
        direction = SignalDirection.LONG if offset % 2 else SignalDirection.SHORT
        signal = SignalIntent(
            signal_id=f"pipeline-signal-{offset}",
            source="research_signal",
            symbol="BTCUSDT",
            direction=direction,
            signal_bar_time_ms=int(bars[time_index]["open_time"]),
            received_time_ms=int(bars[time_index]["close_time"]) + 1,
            raw_payload={"source_mode": "signal_export", "strategy_version": "fixture-v1"},
        )
        await store.reserve_signal(signal)
        await store.update_signal_decision(signal, accepted=True, rejection_reason=None)
        await store.save_decision_packet(
            DecisionPacket(
                signal=signal,
                mode=RuntimeMode.PAPER,
                action=DecisionAction.ACCEPT,
                accepted=True,
                feature_snapshot={
                    "microstructure": {
                        "spread_bps": "3.0",
                        "top_of_book_imbalance": "0.12" if direction == SignalDirection.LONG else "-0.12",
                        "queue_imbalance_l5": "0.08" if direction == SignalDirection.LONG else "-0.08",
                        "windows": {
                            "20": {
                                "signed_ratio": "0.20" if direction == SignalDirection.LONG else "-0.20",
                                "sqrt_signed_ratio": "0.15" if direction == SignalDirection.LONG else "-0.15",
                            }
                        },
                    },
                    "basis": {"basis_bps": "2.0"},
                },
            ),
            signal.received_time_ms,
        )


def _write_spec(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _base_spec(tmp_path: Path, **updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "version": "test-provider-pipeline",
        "asset_scope": ["BTCUSDT"],
        "output_dir": str(tmp_path / "research" / "pipeline_out"),
        "providers": [],
        "dataset_stage": {"enabled": False},
        "evidence_stage": {"enabled": False},
    }
    payload.update(updates)
    return payload


def _pipeline_app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(research=ResearchConfig(output_dir=tmp_path / "research"))


def _write_fast_hmm_knn_config(path: Path) -> Path:
    payload = json.loads(Path("configs/v2_btc_hmm_multi_knn_research.json").read_text(encoding="utf-8"))
    payload["version"] = "test-pipeline-hmm-knn"
    payload["hmm"]["n_states"] = 3
    payload["hmm"]["posterior_threshold"] = 0.45
    payload["hmm"]["entropy_threshold"] = 0.95
    payload["knn"]["primary_k"] = 12
    payload["knn"]["k_values"] = [8, 12]
    payload["knn"]["min_neighbor_count"] = 3
    payload["evaluation"]["min_training_rows"] = 36
    payload["evaluation"]["walk_forward_splits"] = 2
    payload["evaluation"]["purge_embargo_bars"] = 2
    payload["acceptance"]["min_trade_count"] = 1
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_archive_provider_descriptors_cover_expected_contract_sources() -> None:
    descriptors = {descriptor["source_name"]: descriptor for descriptor in archive_provider_descriptors()}

    assert set(descriptors) == {"binance_vision", "bybit_archive", "crypto_lake", "hyperliquid_archive", "okx_archive"}
    assert descriptors["binance_vision"]["implemented_for_ingestion"] is True
    assert descriptors["bybit_archive"]["implemented_for_ingestion"] is False
    assert descriptors["crypto_lake"]["implemented_for_ingestion"] is True
    assert descriptors["hyperliquid_archive"]["implemented_for_ingestion"] is False
    assert descriptors["okx_archive"]["implemented_for_ingestion"] is False


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
                    "source_name": "bybit_archive",
                    "enabled": True,
                    "symbol": "BTCUSDT",
                    "data_family": "trade",
                },
                {
                    "source_name": "hyperliquid_archive",
                    "enabled": True,
                    "symbol": "BTCUSDT",
                    "data_family": "order_event",
                },
            ],
        ),
    )

    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="intake",
        app_config=_pipeline_app_config(tmp_path),
    )

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
        "no_inputs",
        "not_implemented_for_ingestion",
    }
    unsupported_manifests = [
        json.loads(Path(path).read_text(encoding="utf-8"))
        for provider in intake["providers"]
        if provider["status"] == "not_implemented_for_ingestion"
        for path in provider["manifest_paths"]
    ]
    assert {manifest["source_name"] for manifest in unsupported_manifests} == {
        "bybit_archive",
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


def test_prepare_hmm_knn_research_data_intake_ingests_crypto_lake_export(tmp_path: Path) -> None:
    source_path = tmp_path / "crypto_lake_candles.csv"
    source_path.write_text(
        "\n".join(
            [
                "origin_time,exchange,symbol,open,high,low,close,volume,received_time",
                "2024-01-01T00:00:00+00:00,BINANCE,BTC-USDT-PERP,100,101,99,100.5,10,2024-01-01T00:00:01+00:00",
                "2024-01-01T00:01:00+00:00,BINANCE,BTC-USDT-PERP,100.5,102,100,101.5,12,2024-01-01T00:01:01+00:00",
            ]
        ),
        encoding="utf-8",
    )
    spec_path = _write_spec(
        tmp_path / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            providers=[
                {
                    "source_name": "crypto_lake",
                    "inputs": [
                        {
                            "path": source_path.name,
                            "symbol": "BTCUSDT",
                            "provider_symbol": "BTC-USDT-PERP",
                            "data_family": "kline",
                            "interval": "1m",
                        }
                    ],
                }
            ],
        ),
    )

    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="intake",
        app_config=_pipeline_app_config(tmp_path),
    )
    intake = json.loads(result.intake_manifest_path.read_text(encoding="utf-8"))
    quality = json.loads(result.data_quality_report_path.read_text(encoding="utf-8"))
    journal_manifest = json.loads(result.market_journal_manifest_path.read_text(encoding="utf-8"))
    provider_manifest = json.loads(Path(intake["archive_manifest_paths"][0]).read_text(encoding="utf-8"))

    assert intake["providers"][0]["status"] == "completed"
    assert provider_manifest["source_name"] == "crypto_lake"
    assert provider_manifest["row_count"] == 2
    assert provider_manifest["receive_time_field"] == "receive_time_ms"
    assert quality["source_counts"]["crypto_lake"] == 1
    assert journal_manifest["event_count"] == 2
    assert journal_manifest["event_counts_by_source"] == {"crypto_lake": 2}


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
    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="intake",
        app_config=_pipeline_app_config(tmp_path),
    )
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

    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="evidence",
        app_config=_pipeline_app_config(tmp_path),
    )
    intake = json.loads(result.intake_manifest_path.read_text(encoding="utf-8"))

    assert result.evidence_manifest_path is None
    assert intake["stage_status"]["dataset"]["status"] == "skipped"
    assert intake["stage_status"]["evidence"] == {
        "status": "skipped",
        "reason": "dataset_not_available",
    }


def test_prepare_hmm_knn_research_data_stage_all_writes_pipeline_summary(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            dataset_stage={
                "enabled": True,
                "research_config": "configs/v2_btc_research.json",
                "db_path": str(tmp_path / "empty.sqlite3"),
            },
            evidence_stage={
                "enabled": True,
                "hmm_knn_config": "configs/v2_btc_hmm_multi_knn_research.json",
                "write_monitoring": True,
            },
        ),
    )

    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="all",
        app_config=AppConfig(
            db_path=tmp_path / "empty.sqlite3",
            research=ResearchConfig(output_dir=tmp_path / "research"),
        ),
    )
    summary = json.loads(result.pipeline_summary_path.read_text(encoding="utf-8"))

    assert summary["research_only"] is True
    assert summary["observe_only"] is True
    assert summary["promotion_ready"] is False
    assert summary["stage_requested"] == "all"
    assert summary["artifact_links"]["data_intake_manifest_path"] == str(result.intake_manifest_path)
    assert summary["artifact_links"]["data_quality_report_path"] == str(result.data_quality_report_path)
    assert summary["artifact_links"]["market_journal_manifest_path"] == str(result.market_journal_manifest_path)
    assert summary["stage_status"]["intake"]["status"] == "completed"
    assert summary["stage_status"]["dataset"]["status"] == "failed"
    assert summary["stage_status"]["evidence"] == {"status": "skipped", "reason": "dataset_not_available"}
    assert summary["conclusion"]["status"] == "inconclusive"
    assert any(reason["code"] == "dataset_failed" for reason in summary["top_failure_reasons"])
    assert result.dataset_manifest_path is None
    assert result.evidence_manifest_path is None


def test_prepare_hmm_knn_research_data_stage_all_runs_relative_evidence_matrix(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "fixtures" / "datasets", row_count=120)
    config_path = _write_fast_hmm_knn_config(tmp_path / "fixtures" / "hmm_knn_config.json")
    experiment_spec_path = _write_spec(
        tmp_path / "fixtures" / "experiment_spec.json",
        {
            "name": "pipeline fixture matrix",
            "base_config_path": config_path.name,
            "experiments": [
                {
                    "name": "small k softmax",
                    "slug": "small-k-softmax",
                    "owning_agent": "KNN",
                    "run_order": 1,
                    "requires_new_data": False,
                    "can_run_on_current_artifacts": True,
                    "mutations": {
                        "knn.primary_k": 8,
                        "knn.k_values": [8, 12],
                        "knn.primary_weighting": "softmax",
                        "knn.neighbor_weighting": ["softmax"],
                    },
                }
            ],
        },
    )
    spec_path = _write_spec(
        tmp_path / "fixtures" / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            providers=[],
            dataset_stage={"enabled": False},
            evidence_stage={
                "enabled": True,
                "dataset_path": str(Path("datasets") / dataset.parquet_path.name),
                "experiment_spec": experiment_spec_path.name,
                "workers": 1,
                "write_monitoring": True,
            },
        ),
    )

    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="all",
        app_config=_pipeline_app_config(tmp_path),
    )
    intake = json.loads(result.intake_manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(result.pipeline_summary_path.read_text(encoding="utf-8"))
    evidence = json.loads(Path(str(summary["artifact_links"]["evidence_manifest_path"])).read_text(encoding="utf-8"))

    assert result.dataset_manifest_path is None
    assert result.evidence_manifest_path is not None
    assert intake["stage_status"]["dataset"] == {"status": "skipped", "reason": "dataset_stage_disabled"}
    assert intake["stage_status"]["evidence"]["status"] == "completed"
    assert intake["stage_status"]["evidence"]["mode"] == "experiment_matrix"
    assert summary["stage_status"]["evidence"]["manifest_path"] == str(result.evidence_manifest_path)
    assert summary["artifact_links"]["evidence_manifest_path"] == str(result.evidence_manifest_path)
    assert summary["evidence"]["available"] is True
    assert summary["evidence"]["mode"] == "experiment_matrix"
    assert summary["evidence"]["experiment_count"] == 1
    assert summary["evidence"]["effective_workers"] == 1
    assert summary["conclusion"]["status"] in {"supported", "rejected", "inconclusive"}
    assert evidence["experiment_manifest_version"] == "v2-hmm-knn-experiment-manifest-1"
    assert evidence["spec_path"] == str(experiment_spec_path)
    assert evidence["dataset_path"] == str(dataset.parquet_path.resolve())
    assert Path(evidence["summary_path"]).exists()
    assert Path(evidence["experiments"][0]["monitoring_report_path"]).exists()


def test_prepare_hmm_knn_research_data_resolves_stage_paths_relative_to_spec_before_cwd(
    tmp_path: Path,
    monkeypatch,
) -> None:
    spec_dir = tmp_path / "fixtures"
    cwd_dir = tmp_path / "cwd"
    spec_dataset = write_hmm_knn_sweep_dataset(output_dir=spec_dir / "datasets", row_count=120)
    write_hmm_knn_sweep_dataset(output_dir=cwd_dir / "datasets", row_count=150)
    config_path = _write_fast_hmm_knn_config(spec_dir / "hmm_knn_config.json")
    experiment_spec_path = _write_spec(
        spec_dir / "experiment_spec.json",
        {
            "name": "pipeline fixture matrix",
            "base_config_path": config_path.name,
            "experiments": [
                {
                    "name": "small k softmax",
                    "slug": "small-k-softmax",
                    "owning_agent": "KNN",
                    "run_order": 1,
                    "requires_new_data": False,
                    "can_run_on_current_artifacts": True,
                    "mutations": {"knn.primary_k": 8, "knn.k_values": [8, 12]},
                }
            ],
        },
    )
    spec_path = _write_spec(
        spec_dir / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            providers=[],
            dataset_stage={"enabled": False},
            evidence_stage={
                "enabled": True,
                "dataset_path": str(Path("datasets") / spec_dataset.parquet_path.name),
                "experiment_spec": experiment_spec_path.name,
                "workers": 1,
                "write_monitoring": True,
            },
        ),
    )
    monkeypatch.chdir(cwd_dir)

    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="all",
        app_config=_pipeline_app_config(tmp_path),
    )
    summary = json.loads(result.pipeline_summary_path.read_text(encoding="utf-8"))
    evidence = json.loads(Path(str(summary["artifact_links"]["evidence_manifest_path"])).read_text(encoding="utf-8"))

    assert evidence["dataset_path"] == str(spec_dataset.parquet_path.resolve())


def test_prepare_hmm_knn_research_data_stage_all_builds_dataset_from_sqlite_signals_and_archive_bars(tmp_path: Path) -> None:
    source_path = tmp_path / "fixtures" / "BTCUSDT-15m-klines.csv"
    source_path.parent.mkdir(parents=True)
    bars = _write_many_kline_csv(source_path)
    db_path = tmp_path / "signals.sqlite3"
    asyncio.run(_seed_external_signal_signals(db_path, bars))
    config_path = _write_fast_hmm_knn_config(tmp_path / "fixtures" / "hmm_knn_config.json")
    experiment_spec_path = _write_spec(
        tmp_path / "fixtures" / "experiment_spec.json",
        {
            "name": "sqlite signal pipeline matrix",
            "base_config_path": config_path.name,
            "experiments": [
                {
                    "name": "small k softmax",
                    "slug": "small-k-softmax",
                    "owning_agent": "KNN",
                    "run_order": 1,
                    "requires_new_data": False,
                    "can_run_on_current_artifacts": True,
                    "mutations": {
                        "knn.primary_k": 8,
                        "knn.k_values": [8, 12],
                        "knn.primary_weighting": "softmax",
                        "knn.neighbor_weighting": ["softmax"],
                    },
                }
            ],
        },
    )
    spec_path = _write_spec(
        tmp_path / "fixtures" / "pipeline_spec.json",
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
                            "interval": "15m",
                        }
                    ],
                }
            ],
            dataset_stage={
                "enabled": True,
                "research_config": "configs/v2_btc_research.json",
                "db_path": str(db_path),
            },
            evidence_stage={
                "enabled": True,
                "experiment_spec": experiment_spec_path.name,
                "workers": 1,
                "write_monitoring": True,
            },
        ),
    )

    result = prepare_hmm_knn_research_data(
        spec_path=spec_path,
        stage="all",
        app_config=AppConfig(
            db_path=db_path,
            research=ResearchConfig(output_dir=tmp_path / "research"),
        ),
    )
    summary = json.loads(result.pipeline_summary_path.read_text(encoding="utf-8"))
    dataset_manifest = json.loads(Path(str(summary["artifact_links"]["dataset_manifest_path"])).read_text(encoding="utf-8"))
    evidence = json.loads(Path(str(summary["artifact_links"]["evidence_manifest_path"])).read_text(encoding="utf-8"))

    assert summary["stage_status"]["dataset"]["status"] == "completed"
    assert summary["stage_status"]["evidence"]["status"] == "completed"
    assert dataset_manifest["source_counts"] == {"research_signal": 46}
    assert dataset_manifest["source_mode_counts"] == {"signal_export": 46}
    assert summary["stage_status"]["dataset"]["archive_client_coverage"]["bar_series"] == {"BTCUSDT:15m": 520}
    assert Path(dataset_manifest["dataset_path"]).exists()
    assert evidence["dataset_path"] == dataset_manifest["dataset_path"]


def test_prepare_hmm_knn_research_data_rejects_invalid_typed_provider_spec(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path / "pipeline_spec.json",
        _base_spec(
            tmp_path,
            providers=[
                {
                    "source_name": "binance_vision",
                    "inputs": [
                        {
                            "path": "BTCUSDT-1m-klines.csv",
                            "symbol": "BTCUSDT",
                        }
                    ],
                }
            ],
        ),
    )

    with pytest.raises(ValueError, match="data_family is required"):
        prepare_hmm_knn_research_data(
            spec_path=spec_path,
            stage="intake",
            app_config=_pipeline_app_config(tmp_path),
        )


def test_prepare_hmm_knn_research_data_rejects_output_outside_research_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside" / "pipeline_out"
    spec_path = _write_spec(
        tmp_path / "pipeline_spec.json",
        _base_spec(tmp_path, output_dir=str(outside)),
    )

    with pytest.raises(ValueError, match="pipeline output_dir must be inside"):
        prepare_hmm_knn_research_data(
            spec_path=spec_path,
            stage="intake",
            app_config=_pipeline_app_config(tmp_path),
        )

    assert not outside.exists()


def test_prepare_hmm_knn_research_data_cli_command_runs_intake(tmp_path: Path, monkeypatch) -> None:
    spec_path = _write_spec(tmp_path / "pipeline_spec.json", _base_spec(tmp_path))
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(tmp_path / "research"))
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

    assert payload["output_dir"] == str(tmp_path / "research" / "pipeline_out")
    assert Path(str(payload["data_intake_manifest_path"])).exists()
    assert Path(str(payload["data_quality_report_path"])).exists()
    assert Path(str(payload["market_journal_manifest_path"])).exists()
    assert Path(str(payload["pipeline_summary_path"])).exists()
