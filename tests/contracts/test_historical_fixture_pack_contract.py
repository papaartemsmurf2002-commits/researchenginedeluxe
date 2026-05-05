from __future__ import annotations

from argparse import Namespace
import json
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.data.historical_fixture_pack import (
    HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION,
    assert_valid_historical_fixture_pack_manifest,
    build_provider_kline_fixture_pack,
    validate_historical_fixture_pack_manifest,
)
from tradingbotsuite.main import _run_build_historical_fixture_pack_command
from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset
from tradingbotsuite.research.market_data import collect_binance_usdm_context


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKED_IN_FIXTURE_MANIFEST = REPO_ROOT / "data" / "research" / "fixtures" / "btcusdt_v1" / "fixture_pack_manifest.json"
REMOVED_CHART_SOURCE = "trading" + "view"
REMOVED_CHART_SOURCE_FLAG = REMOVED_CHART_SOURCE + "_source_used"
REMOVED_CHART_EXPORT_SOURCE = REMOVED_CHART_SOURCE + "_" + "chart" + "_export"
REMOVED_CHART_SOURCE_NOT_ALLOWED = REMOVED_CHART_SOURCE + "_source_not_allowed"


def _write_fixture_pack(tmp_path: Path, **manifest_updates: object) -> Path:
    pack_dir = tmp_path / "fixture_pack"
    pack_dir.mkdir(parents=True, exist_ok=True)
    cycle = build_hmm_knn_sweep_dataset(row_count=96, variant="balanced")
    cycle_path = pack_dir / "cycle_dataset.parquet"
    cycle.to_parquet(cycle_path, index=False)
    bars = pd.DataFrame(
        {
            "event_time_ms": cycle["signal_bar_time_ms"],
            "symbol": cycle["symbol"],
            "interval": "15m",
            "open_price": cycle["signal_bar_open"],
            "high_price": cycle["signal_bar_high"],
            "low_price": cycle["signal_bar_low"],
            "close_price": cycle["signal_bar_close"],
            "volume": cycle["signal_bar_volume"],
        }
    )
    bars_path = pack_dir / "bars_15m.parquet"
    bars.to_parquet(bars_path, index=False)
    manifest: dict[str, object] = {
        "manifest_version": HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "fixture_id": "btcusdt-local-offline-v1",
        "symbol": "BTCUSDT",
        "base_interval": "15m",
        "cycle_dataset": {
            "path": "cycle_dataset.parquet",
            "sha256": f"sha256:{_file_sha256(cycle_path)}",
            "row_count": len(cycle),
            "time_field": "signal_bar_time_ms",
        },
        "families": {
            "bars": {
                "path": "bars_15m.parquet",
                "data_family": "kline",
                "interval": "15m",
                "event_time_field": "event_time_ms",
                "sha256": f"sha256:{_file_sha256(bars_path)}",
                "row_count": len(bars),
                "required": True,
                "columns": list(bars.columns),
            }
        },
    }
    manifest.update(manifest_updates)
    manifest_path = pack_dir / "fixture_pack_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def test_historical_fixture_pack_accepts_minimal_btc_pack(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)

    assert validation.valid is True
    assert validation.errors == ()
    assert validation.fixture_id == "btcusdt-local-offline-v1"
    assert validation.row_count == 96
    assert validation.cycle_dataset_path == manifest_path.parent / "cycle_dataset.parquet"
    assert assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path).valid is True


def test_checked_in_btcusdt_fixture_pack_manifest_validates() -> None:
    manifest = json.loads(CHECKED_IN_FIXTURE_MANIFEST.read_text(encoding="utf-8"))

    validation = assert_valid_historical_fixture_pack_manifest(
        manifest,
        manifest_path=CHECKED_IN_FIXTURE_MANIFEST,
    )

    assert validation.valid is True
    assert validation.fixture_id == "btcusdt-v1-checked-in-binance-usdm-klines"
    assert validation.row_count == manifest["cycle_dataset"]["row_count"]
    assert 96 <= int(validation.row_count or 0) <= 240
    assert validation.cycle_dataset_path == CHECKED_IN_FIXTURE_MANIFEST.parent / "cycle_dataset.parquet"
    assert validation.lower_timeframe_dataset_path is None
    assert validation.lower_timeframe_row_count is None
    assert validation.to_payload()["lower_timeframe_family"] == {}
    assert validation.to_payload()["optional_context_families"] == {}
    assert manifest["source"]["source_name"] == "binance_rest"
    assert manifest["source"]["source_raw"] == "binance_usdm_klines"
    assert manifest["source"]["data_family"] == "kline"
    assert manifest["source"]["source_sha256"] == "ff86ed71921ddaead3a58a6205e4d4b04917960f1a1bd1a9d4c2ef6dbb97ec2e"
    assert manifest["derivation"][REMOVED_CHART_SOURCE_FLAG] is False
    assert manifest["derivation"]["synthetic_source_used"] is False
    assert set(manifest["omitted_optional_families"]) == {
        "lower_timeframe_bars",
        "funding_rate",
        "premium_index",
        "open_interest",
        "agg_trade",
    }
    cycle = pd.read_parquet(validation.cycle_dataset_path)
    assert set(cycle["source_provider"]) == {"binance_rest"}
    assert set(cycle["source_provider_raw"]) == {"binance_usdm_klines"}
    assert set(cycle["source_data_family"]) == {"kline"}
    assert cycle["source_row_index"].is_monotonic_increasing
    assert pd.to_numeric(cycle["source_row_index"]).diff().dropna().eq(1).all()
    assert int(cycle["source_row_index"].min()) == manifest["derivation"]["source_start_row_index"]
    assert int(cycle["source_row_index"].max()) == manifest["derivation"]["source_end_row_index"]
    assert int(cycle["time_ms"].min()) == manifest["derivation"]["first_time_ms"]
    assert int(cycle["time_ms"].max()) == manifest["derivation"]["last_time_ms"]
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False


def test_provider_kline_fixture_pack_builder_accepts_binance_usdm_cache_manifest(tmp_path: Path) -> None:
    source_path = tmp_path / "BTCUSDT_15m_provider_cache.json"
    rows = _provider_kline_rows(row_count=12)
    source_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")
    source_manifest_path = tmp_path / "BTCUSDT_15m_provider_cache.manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "source": "binance_usdm_klines",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "row_count": len(rows),
                "first_time_ms": rows[0]["time_ms"],
                "last_time_ms": rows[-1]["time_ms"],
                "sha256": _file_sha256(source_path),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = build_provider_kline_fixture_pack(
        source_manifest_path=source_manifest_path,
        output_dir=tmp_path / "fixture_pack",
        fixture_id="btcusdt-provider-builder-test",
        row_limit=5,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=result.manifest_path)
    cycle = pd.read_parquet(result.cycle_dataset_path)

    assert result.fixture_id == "btcusdt-provider-builder-test"
    assert validation.row_count == 5
    assert manifest["source"]["source_name"] == "binance_rest"
    assert manifest["source"]["source_raw"] == "binance_usdm_klines"
    assert manifest["derivation"][REMOVED_CHART_SOURCE_FLAG] is False
    assert manifest["derivation"]["synthetic_source_used"] is False
    assert manifest["source"]["source_sha256"] == _file_sha256(source_path)
    assert set(cycle["source_provider"]) == {"binance_rest"}
    assert set(cycle["source_provider_raw"]) == {"binance_usdm_klines"}
    assert cycle["source_row_index"].tolist() == [7, 8, 9, 10, 11]
    assert validation.to_payload()["optional_context_families"] == {}
    assert f"{REMOVED_CHART_SOURCE} export" not in " ".join(_string_values(manifest)).lower()


def test_provider_kline_fixture_pack_builder_accepts_collector_jsonl_manifest(tmp_path: Path) -> None:
    data_path = tmp_path / "collector_bars.jsonl"
    rows = _provider_kline_rows(row_count=8)
    data_path.write_text(
        "".join(json.dumps({**row, "open": str(row["open"])}, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    source_manifest_path = tmp_path / "collector_bars.manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "source": "binance_usdm_klines",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_family": "kline",
                "data_path": str(data_path),
                "row_count": len(rows),
                "sha256": _file_sha256(data_path),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = build_provider_kline_fixture_pack(
        source_manifest_path=source_manifest_path,
        output_dir=tmp_path / "fixture_pack",
        row_limit=3,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=result.manifest_path)

    assert validation.valid is True
    assert validation.row_count == 3
    assert result.source_data_sha256 == _file_sha256(data_path)
    assert manifest["cycle_dataset"]["row_count"] == 3


def test_provider_kline_fixture_pack_builder_rejects_removed_chart_manifest(tmp_path: Path) -> None:
    source_path = tmp_path / "legacy_tv.json"
    source_path.write_text(json.dumps(_provider_kline_rows(row_count=4), sort_keys=True), encoding="utf-8")
    source_manifest_path = tmp_path / "legacy_tv.manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "source": REMOVED_CHART_EXPORT_SOURCE,
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_family": "kline",
                "data_path": str(source_path),
                "row_count": 4,
                "sha256": _file_sha256(source_path),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=REMOVED_CHART_SOURCE_NOT_ALLOWED):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
        )


def test_provider_kline_fixture_pack_builder_rejects_synthetic_provenance(tmp_path: Path) -> None:
    source_path = tmp_path / "synthetic_provider_like.json"
    source_path.write_text(json.dumps(_provider_kline_rows(row_count=4), sort_keys=True), encoding="utf-8")
    source_manifest_path = tmp_path / "synthetic_provider_like.manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "source": "binance_usdm_klines",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_family": "kline",
                "data_path": str(source_path),
                "row_count": 4,
                "sha256": _file_sha256(source_path),
                "derivation": {"source": "synthetic_generator"},
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="synthetic_source_not_allowed"):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
        )


def test_provider_kline_fixture_pack_builder_rejects_row_interval_mismatch(tmp_path: Path) -> None:
    source_path = tmp_path / "mismatched_interval.json"
    rows = _provider_kline_rows(row_count=4)
    rows[2]["interval"] = "1h"
    source_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")
    source_manifest_path = tmp_path / "mismatched_interval.manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "source": "binance_usdm_klines",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_family": "kline",
                "data_path": str(source_path),
                "row_count": 4,
                "sha256": _file_sha256(source_path),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="provider_kline_interval_mismatch:1h:15m"):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
        )


def test_provider_kline_fixture_pack_builder_rejects_row_count_mismatch(tmp_path: Path) -> None:
    source_path = tmp_path / "mismatched_row_count.json"
    rows = _provider_kline_rows(row_count=4)
    source_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")
    source_manifest_path = tmp_path / "mismatched_row_count.manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "source": "binance_usdm_klines",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_family": "kline",
                "data_path": str(source_path),
                "row_count": 5,
                "sha256": _file_sha256(source_path),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="provider_kline_source_row_count_mismatch:5:4"):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
        )


def test_build_historical_fixture_pack_cli_payload_is_research_only(tmp_path: Path) -> None:
    source_path = tmp_path / "BTCUSDT_15m_provider_cache.json"
    rows = _provider_kline_rows(row_count=7)
    source_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")
    source_manifest_path = tmp_path / "BTCUSDT_15m_provider_cache.manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "source": "binance_usdm_klines",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "row_count": len(rows),
                "sha256": _file_sha256(source_path),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    payload = _run_build_historical_fixture_pack_command(
        Namespace(
            source_manifest=str(source_manifest_path),
            output_dir=str(tmp_path / "fixture_pack"),
            fixture_id="btcusdt-cli-builder-test",
            row_limit=4,
            slice_mode="tail",
        )
    )

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["fixture_id"] == "btcusdt-cli-builder-test"
    assert payload["row_count"] == 4
    assert Path(payload["manifest_path"]).exists()
    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=Path(payload["manifest_path"])).valid is True


def test_provider_kline_fixture_pack_builder_includes_provider_context_manifests(tmp_path: Path) -> None:
    rows = _provider_kline_rows(row_count=10)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    context_manifest_paths = _write_provider_context_manifests(tmp_path, rows)

    result = build_provider_kline_fixture_pack(
        source_manifest_path=source_manifest_path,
        output_dir=tmp_path / "fixture_pack",
        fixture_id="btcusdt-provider-context-builder-test",
        row_limit=5,
        context_manifest_paths=context_manifest_paths,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=result.manifest_path)
    context_families = validation.to_payload()["optional_context_families"]

    assert set(context_families) == {"funding_rate", "premium_index", "open_interest", "agg_trade"}
    assert set(result.to_payload()["context_family_paths"]) == set(context_families)
    assert {record["data_family"] for record in manifest["source"]["context_sources"]} == set(context_families)
    assert set(manifest["omitted_optional_families"]) == {"lower_timeframe_bars"}
    assert manifest["derivation"]["context_families"] == ["agg_trade", "funding_rate", "open_interest", "premium_index"]
    for family, payload in context_families.items():
        family_path = Path(payload["path"])
        assert family_path.exists()
        assert payload["sha256"] == _file_sha256(family_path)
        family_frame = pd.read_parquet(family_path)
        assert {"event_time_ms", "symbol", "source_provider", "source_data_family"} <= set(family_frame.columns)
        assert set(family_frame["symbol"]) == {"BTCUSDT"}
        assert set(family_frame["source_data_family"]) == {family}
        assert int(family_frame["event_time_ms"].max()) <= rows[-1]["time_ms"]
    funding = pd.read_parquet(context_families["funding_rate"]["path"])
    assert funding["funding_rate"].max() < 0.5
    agg_trade = pd.read_parquet(context_families["agg_trade"]["path"])
    assert {"quote_volume", "taker_buy_quote_volume", "primary_signed_imbalance_ratio"} <= set(agg_trade.columns)


def test_build_historical_fixture_pack_cli_accepts_context_manifests(tmp_path: Path) -> None:
    rows = _provider_kline_rows(row_count=8)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    funding_manifest_path = _write_provider_context_manifest(
        tmp_path,
        "funding_rate",
        _provider_funding_context_rows(rows),
        source_name="crypto_lake",
    )
    open_interest_manifest_path = _write_provider_context_manifest(
        tmp_path,
        "open_interest",
        _provider_open_interest_context_rows(rows),
        source_name="crypto_lake",
    )

    payload = _run_build_historical_fixture_pack_command(
        Namespace(
            source_manifest=str(source_manifest_path),
            output_dir=str(tmp_path / "fixture_pack"),
            fixture_id="btcusdt-cli-context-builder-test",
            row_limit=4,
            slice_mode="tail",
            context_manifest=[str(funding_manifest_path), str(open_interest_manifest_path)],
        )
    )

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert set(payload["context_family_paths"]) == {"funding_rate", "open_interest"}
    manifest_path = Path(payload["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    assert set(validation.to_payload()["optional_context_families"]) == {"funding_rate", "open_interest"}
    assert set(manifest["omitted_optional_families"]) == {"lower_timeframe_bars", "premium_index", "agg_trade"}


def test_provider_kline_fixture_pack_builder_accepts_binance_usdm_rest_context_manifest(tmp_path: Path) -> None:
    rows = _provider_kline_rows(row_count=6)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    funding_manifest_path = _write_provider_context_manifest(
        tmp_path,
        "funding_rate",
        _provider_funding_context_rows(rows),
        source_name="binance_usdm_rest",
    )

    result = build_provider_kline_fixture_pack(
        source_manifest_path=source_manifest_path,
        output_dir=tmp_path / "fixture_pack",
        row_limit=4,
        context_manifest_paths=[funding_manifest_path],
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=result.manifest_path)
    context_families = validation.to_payload()["optional_context_families"]

    assert set(context_families) == {"funding_rate"}
    assert manifest["families"]["funding_rate"]["source_name"] == "binance_usdm_rest"
    assert manifest["source"]["context_sources"][0]["source_name"] == "binance_usdm_rest"


@pytest.mark.asyncio
async def test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest(tmp_path: Path) -> None:
    rows = _provider_kline_rows(row_count=6)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    funding = await collect_binance_usdm_context(
        symbol="BTCUSDT",
        data_family="funding_rate",
        start_time_ms=int(rows[0]["time_ms"]) - 60_000,
        end_time_ms=int(rows[-1]["time_ms"]),
        output_dir=tmp_path / "collected_context",
        fetcher=_FakeContextFetcher(
            [
                {
                    "symbol": "BTCUSDT",
                    "fundingRate": "0.0001",
                    "fundingTime": int(row["time_ms"]) - 60_000,
                    "markPrice": str(row["close"]),
                }
                for row in rows
            ]
        ),
    )

    result = build_provider_kline_fixture_pack(
        source_manifest_path=source_manifest_path,
        output_dir=tmp_path / "fixture_pack",
        row_limit=4,
        context_manifest_paths=[funding.manifest_path],
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=result.manifest_path)

    assert set(validation.to_payload()["optional_context_families"]) == {"funding_rate"}
    assert manifest["families"]["funding_rate"]["source_name"] == "binance_usdm_rest"


@pytest.mark.parametrize(
    ("manifest_update", "match"),
    [
        ({"source_name": REMOVED_CHART_EXPORT_SOURCE}, REMOVED_CHART_SOURCE_NOT_ALLOWED),
        ({"derivation": {"source": "synthetic_context"}}, "synthetic_source_not_allowed"),
    ],
)
def test_provider_kline_fixture_pack_builder_rejects_unsafe_context_manifests(
    tmp_path: Path,
    manifest_update: dict[str, object],
    match: str,
) -> None:
    rows = _provider_kline_rows(row_count=6)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    context_manifest_path = _write_provider_context_manifest(
        tmp_path,
        "funding_rate",
        _provider_funding_context_rows(rows),
        manifest_update=manifest_update,
    )

    with pytest.raises(ValueError, match=match):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
            context_manifest_paths=[context_manifest_path],
        )


def test_provider_kline_fixture_pack_builder_rejects_unsafe_context_rows(tmp_path: Path) -> None:
    rows = _provider_kline_rows(row_count=6)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    context_rows = _provider_funding_context_rows(rows)
    context_rows[0]["source"] = REMOVED_CHART_EXPORT_SOURCE
    context_manifest_path = _write_provider_context_manifest(
        tmp_path,
        "funding_rate",
        context_rows,
    )

    with pytest.raises(ValueError, match=f"{REMOVED_CHART_SOURCE_NOT_ALLOWED}_for_fixture_context_row:funding_rate"):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
            context_manifest_paths=[context_manifest_path],
        )


def test_provider_kline_fixture_pack_builder_rejects_duplicate_context_family(tmp_path: Path) -> None:
    rows = _provider_kline_rows(row_count=6)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    first_context = _write_provider_context_manifest(
        tmp_path / "first",
        "funding_rate",
        _provider_funding_context_rows(rows),
    )
    second_context = _write_provider_context_manifest(
        tmp_path / "second",
        "funding_rate",
        _provider_funding_context_rows(rows),
    )

    with pytest.raises(ValueError, match="duplicate_provider_context_family:funding_rate"):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
            context_manifest_paths=[first_context, second_context],
        )


def test_provider_kline_fixture_pack_builder_rejects_context_symbol_mismatch(tmp_path: Path) -> None:
    rows = _provider_kline_rows(row_count=6)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    context_manifest_path = _write_provider_context_manifest(
        tmp_path,
        "funding_rate",
        _provider_funding_context_rows(rows),
        manifest_update={"symbol": "ETHUSDT"},
    )

    with pytest.raises(ValueError, match="provider_context_symbol_mismatch:funding_rate:ETHUSDT:BTCUSDT"):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
            context_manifest_paths=[context_manifest_path],
        )


def test_provider_kline_fixture_pack_builder_rejects_unsupported_context_family(tmp_path: Path) -> None:
    rows = _provider_kline_rows(row_count=6)
    source_manifest_path = _write_provider_kline_manifest(tmp_path, rows)
    context_manifest_path = _write_provider_context_manifest(
        tmp_path,
        "trade",
        [
            {
                "event_time_ms": row["time_ms"] - 60_000,
                "symbol": "BTCUSDT",
                "price": row["close"],
                "quantity": 1.0,
            }
            for row in rows
        ],
    )

    with pytest.raises(ValueError, match="unsupported_provider_context_family:trade"):
        build_provider_kline_fixture_pack(
            source_manifest_path=source_manifest_path,
            output_dir=tmp_path / "fixture_pack",
            context_manifest_paths=[context_manifest_path],
        )


def test_historical_fixture_pack_rejects_missing_path_hash_mismatch_and_unsafe_flags(tmp_path: Path) -> None:
    missing_path = _write_fixture_pack(
        tmp_path / "missing",
        cycle_dataset={"path": "missing.parquet", "sha256": "sha256:bad", "row_count": 96},
    )
    mismatch_path = _write_fixture_pack(
        tmp_path / "hash",
        cycle_dataset={"path": "cycle_dataset.parquet", "sha256": "sha256:bad", "row_count": 96},
    )
    unsafe_path = _write_fixture_pack(tmp_path / "unsafe", research_only=False, promotion_ready=True)

    missing = validate_historical_fixture_pack_manifest(json.loads(missing_path.read_text(encoding="utf-8")), manifest_path=missing_path)
    mismatch = validate_historical_fixture_pack_manifest(json.loads(mismatch_path.read_text(encoding="utf-8")), manifest_path=mismatch_path)
    unsafe = validate_historical_fixture_pack_manifest(json.loads(unsafe_path.read_text(encoding="utf-8")), manifest_path=unsafe_path)

    assert missing.valid is False
    assert any(error.startswith("cycle_dataset_path_missing") for error in missing.errors)
    assert mismatch.valid is False
    assert "cycle_dataset_sha256_mismatch" in mismatch.errors
    assert unsafe.valid is False
    assert "fixture_pack_must_be_research_only" in unsafe.errors
    assert "fixture_pack_must_not_be_promotion_ready" in unsafe.errors


def test_historical_fixture_pack_rejects_unsafe_fixture_provenance(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"] = REMOVED_CHART_EXPORT_SOURCE
    manifest["derivation"] = {REMOVED_CHART_SOURCE_FLAG: True, "synthetic_source_used": True}

    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)

    assert validation.valid is False
    assert f"fixture_pack_{REMOVED_CHART_SOURCE_NOT_ALLOWED}" in validation.errors
    assert "fixture_pack_synthetic_source_not_allowed" in validation.errors


def test_historical_fixture_pack_rejects_required_family_without_hash_or_schema_evidence(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["families"]["bars"].pop("sha256")
    manifest["families"]["bars"].pop("columns")

    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)

    assert validation.valid is False
    assert "family_bars_sha256_required" in validation.errors
    assert "family_bars_columns_required" in validation.errors


def test_historical_fixture_pack_validates_optional_family_entries(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    optional_frames = {
        "funding_rate": pd.DataFrame(
            {"event_time_ms": [1, 2], "symbol": ["BTCUSDT", "BTCUSDT"], "funding_rate": [0.1, 0.2]}
        ),
        "premium_index": pd.DataFrame(
            {
                "event_time_ms": [1, 2],
                "symbol": ["BTCUSDT", "BTCUSDT"],
                "mark_price": [101.0, 102.0],
                "index_price": [100.0, 100.0],
            }
        ),
        "open_interest": pd.DataFrame(
            {"event_time_ms": [1, 2], "symbol": ["BTCUSDT", "BTCUSDT"], "open_interest": [1000.0, 1020.0]}
        ),
        "agg_trade": pd.DataFrame(
            {
                "event_time_ms": [1, 2],
                "symbol": ["BTCUSDT", "BTCUSDT"],
                "taker_buy_quote_volume": [60.0, 70.0],
                "quote_volume": [100.0, 120.0],
            }
        ),
    }
    for family, optional in optional_frames.items():
        path = manifest_path.parent / f"{family}.parquet"
        optional.to_parquet(path, index=False)
        manifest["families"][family] = {
            "path": path.name,
            "data_family": family,
            "required": False,
            "sha256": f"sha256:{_file_sha256(path)}",
            "row_count": len(optional),
            "columns": list(optional.columns),
        }
    lower = _lower_timeframe_bars()
    lower_path = manifest_path.parent / "lower_timeframe_bars.parquet"
    lower.to_parquet(lower_path, index=False)
    manifest["families"]["lower_timeframe_bars"] = {
        "path": lower_path.name,
        "data_family": "lower_timeframe_bars",
        "interval": "1m",
        "event_time_field": "bar_time_ms",
        "required": False,
        "sha256": f"sha256:{_file_sha256(lower_path)}",
        "row_count": len(lower),
        "columns": list(lower.columns),
    }

    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)

    assert validation.valid is True
    assert validation.errors == ()
    assert validation.lower_timeframe_dataset_path == lower_path
    assert validation.lower_timeframe_row_count == len(lower)
    assert validation.to_payload()["lower_timeframe_family"]["sha256"] == _file_sha256(lower_path)
    context_families = validation.to_payload()["optional_context_families"]
    assert set(context_families) == {"funding_rate", "premium_index", "open_interest", "agg_trade"}
    assert context_families["funding_rate"]["path"] == str(manifest_path.parent / "funding_rate.parquet")
    assert context_families["funding_rate"]["event_time_field"] == "event_time_ms"
    assert context_families["funding_rate"]["sha256"] == _file_sha256(manifest_path.parent / "funding_rate.parquet")


def test_historical_fixture_pack_rejects_context_family_without_symbol_time_hash_or_row_count(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    funding = pd.DataFrame({"funding_rate": [0.1, 0.2]})
    funding_path = manifest_path.parent / "funding_rate.parquet"
    funding.to_parquet(funding_path, index=False)
    manifest["families"]["funding_rate"] = {
        "path": funding_path.name,
        "required": False,
        "columns": list(funding.columns),
    }

    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)

    assert validation.valid is False
    assert "family_funding_rate_row_count_required" in validation.errors
    assert "family_funding_rate_sha256_required" in validation.errors
    assert "family_funding_rate_columns_missing:event_time_ms,symbol" in validation.errors
    assert validation.to_payload()["optional_context_families"] == {}


def test_historical_fixture_pack_rejects_context_family_without_data_family(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    funding = pd.DataFrame({"event_time_ms": [1, 2], "symbol": ["BTCUSDT", "BTCUSDT"], "funding_rate": [0.1, 0.2]})
    funding_path = manifest_path.parent / "funding_rate.parquet"
    funding.to_parquet(funding_path, index=False)
    manifest["families"]["funding_rate"] = {
        "path": funding_path.name,
        "required": False,
        "sha256": f"sha256:{_file_sha256(funding_path)}",
        "row_count": len(funding),
        "columns": list(funding.columns),
    }

    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)

    assert validation.valid is False
    assert "family_funding_rate_data_family_required" in validation.errors
    assert validation.to_payload()["optional_context_families"] == {}


def test_historical_fixture_pack_rejects_context_family_without_supported_columns_or_matching_family(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    agg_trade = pd.DataFrame({"event_time_ms": [1, 2], "symbol": ["BTCUSDT", "BTCUSDT"], "value": [0.1, 0.2]})
    agg_path = manifest_path.parent / "agg_trade.parquet"
    agg_trade.to_parquet(agg_path, index=False)
    manifest["families"]["agg_trade"] = {
        "path": agg_path.name,
        "data_family": "funding_rate",
        "required": False,
        "sha256": f"sha256:{_file_sha256(agg_path)}",
        "row_count": len(agg_trade),
        "columns": list(agg_trade.columns),
    }

    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)

    assert validation.valid is False
    assert "family_agg_trade_data_family_mismatch:funding_rate:agg_trade" in validation.errors
    assert "family_agg_trade_unsupported_context_columns" in validation.errors
    assert validation.to_payload()["optional_context_families"] == {}


def test_historical_fixture_pack_rejects_lower_timeframe_bars_without_ohlc_or_hash(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lower = pd.DataFrame({"event_time_ms": [1, 2], "symbol": ["BTCUSDT", "BTCUSDT"], "value": [0.1, 0.2]})
    lower_path = manifest_path.parent / "lower_timeframe_bars.parquet"
    lower.to_parquet(lower_path, index=False)
    manifest["families"]["lower_timeframe_bars"] = {
        "path": lower_path.name,
        "data_family": "lower_timeframe_bars",
        "interval": "1m",
        "event_time_field": "bar_time_ms",
        "required": False,
        "columns": list(lower.columns),
    }

    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)

    assert validation.valid is False
    assert "family_lower_timeframe_bars_sha256_required" in validation.errors
    assert "family_lower_timeframe_bars_row_count_required" in validation.errors
    assert "family_lower_timeframe_bars_columns_missing:bar_time_ms,close,high,low,open" in validation.errors
    assert validation.lower_timeframe_dataset_path is None


def _lower_timeframe_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bar_time_ms": [1_712_649_600_000, 1_712_649_660_000],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "open": [100.0, 100.2],
            "high": [100.5, 100.6],
            "low": [99.8, 100.0],
            "close": [100.2, 100.4],
            "volume": [1.0, 1.1],
        }
    )


def _provider_kline_rows(*, row_count: int) -> list[dict[str, object]]:
    start = 1_712_649_600_000
    rows: list[dict[str, object]] = []
    for index in range(row_count):
        open_price = 100.0 + index
        rows.append(
            {
                "time_ms": start + (index * 15 * 60_000),
                "open": open_price,
                "high": open_price + 2.0,
                "low": open_price - 1.0,
                "close": open_price + 0.5,
                "volume": 10.0 + index,
            }
        )
    return rows


def _write_provider_kline_manifest(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "BTCUSDT_15m_provider_cache.json"
    source_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")
    source_manifest_path = tmp_path / "BTCUSDT_15m_provider_cache.manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "source": "binance_usdm_klines",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_family": "kline",
                "data_path": str(source_path),
                "row_count": len(rows),
                "sha256": _file_sha256(source_path),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return source_manifest_path


class _FakeContextFetcher:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    async def fetch_context_rows(
        self,
        *,
        symbol: str,
        data_family: str,
        start_time_ms: int,
        end_time_ms: int,
        interval: str,
    ) -> list[dict[str, object]]:
        return self.rows


def _write_provider_context_manifests(tmp_path: Path, rows: list[dict[str, object]]) -> list[Path]:
    return [
        _write_provider_context_manifest(tmp_path, "funding_rate", _provider_funding_context_rows(rows), source_name="crypto_lake"),
        _write_provider_context_manifest(tmp_path, "premium_index", _provider_premium_context_rows(rows), source_name="binance_vision"),
        _write_provider_context_manifest(tmp_path, "open_interest", _provider_open_interest_context_rows(rows), source_name="crypto_lake"),
        _write_provider_context_manifest(tmp_path, "agg_trade", _provider_agg_trade_context_rows(rows), source_name="binance_vision"),
    ]


def _write_provider_context_manifest(
    tmp_path: Path,
    family: str,
    rows: list[dict[str, object]],
    *,
    source_name: str = "binance_vision",
    manifest_update: dict[str, object] | None = None,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    data_path = tmp_path / f"{family}_context.jsonl"
    data_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "source_name": source_name,
        "symbol": "BTCUSDT",
        "data_family": family,
        "event_time_field": "event_time_ms",
        "data_path": str(data_path),
        "row_count": len(rows),
        "content_hash": f"sha256:{_file_sha256(data_path)}",
        "receive_time_unavailable_reason": "unit provider context fixture has no receive timestamps",
    }
    if manifest_update:
        manifest.update(manifest_update)
    manifest_path = tmp_path / f"{family}_context.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def _provider_funding_context_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    funding_rows = [
        {
            "event_time_ms": int(row["time_ms"]) - 60_000,
            "symbol": "BTCUSDT",
            "funding_rate": 0.0001 + (index * 0.000001),
        }
        for index, row in enumerate(rows)
    ]
    funding_rows.append(
        {
            "event_time_ms": int(rows[-1]["time_ms"]) + 60_000,
            "symbol": "BTCUSDT",
            "funding_rate": 0.999,
        }
    )
    return funding_rows


def _provider_premium_context_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "event_time_ms": int(row["time_ms"]) - 60_000,
            "symbol": "BTCUSDT",
            "mark_price": float(row["close"]) * (1.0 + 0.0002 + (index * 0.0000005)),
            "index_price": float(row["close"]),
            "premium_index": 0.0002 + (index * 0.0000005),
        }
        for index, row in enumerate(rows)
    ]


def _provider_open_interest_context_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "event_time_ms": int(row["time_ms"]) - 60_000,
            "symbol": "BTCUSDT",
            "open_interest": 100_000.0 + (index * 25.0),
        }
        for index, row in enumerate(rows)
    ]


def _provider_agg_trade_context_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    agg_rows: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        event_time_ms = int(row["time_ms"]) - 60_000
        price = float(row["close"])
        agg_rows.extend(
            [
                {
                    "event_time_ms": event_time_ms,
                    "symbol": "BTCUSDT",
                    "price": price,
                    "quantity": 1.0 + (index * 0.01),
                    "is_buyer_maker": False,
                    "top_of_book_imbalance": 0.15,
                    "spread_bps": 2.5,
                },
                {
                    "event_time_ms": event_time_ms,
                    "symbol": "BTCUSDT",
                    "price": price,
                    "quantity": 0.25,
                    "is_buyer_maker": True,
                    "top_of_book_imbalance": 0.12,
                    "spread_bps": 2.75,
                },
            ]
        )
    return agg_rows


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_string_values(item))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(_string_values(item))
        return strings
    return []
