from __future__ import annotations

import csv
import gzip
import io
import json
import zipfile
from pathlib import Path

import pytest

import tradingbotsuite.v2.data_sources.central_market_history_collection as cmhc
from tradingbotsuite.v2.data_sources import (
    CENTRAL_MARKET_HISTORY_MAX_BYTES,
    CentralMarketHistoryBatchPlan,
    CentralMarketHistoryCollectionLedgerEntry,
    CentralMarketHistoryFamily,
    build_binance_daily_agg_trades_plan,
    build_binance_daily_book_depth_plan,
    build_binance_daily_book_ticker_plan,
    build_binance_daily_trades_plan,
    build_binance_monthly_kline_plan,
    build_bybit_public_trading_plan,
    central_market_history_budget_report,
    collect_central_market_history_batch,
    download_source_plan,
    require_central_market_history_budget,
    rows_from_binance_kline_zip,
    rows_from_binance_book_depth_zip,
    rows_from_binance_book_ticker_zip,
    rows_from_binance_trades_zip,
    rows_from_bybit_trading_gzip,
    write_central_market_history_discovery_report,
    build_bybit_mt4_kline_plan,
    build_bybit_index_plan,
    build_bybit_spot_monthly_trades_plan,
    rows_from_bybit_index_gzip,
    write_central_market_history_collection_ledger,
)


def test_central_market_history_default_cap_is_300_gib() -> None:
    assert CENTRAL_MARKET_HISTORY_MAX_BYTES == 300 * 1024**3


def test_collection_ledger_records_backtest_usable_and_calloff_gaps(tmp_path: Path) -> None:
    root = tmp_path / "central_market_history"
    collected = CentralMarketHistoryCollectionLedgerEntry(
        provider="binance_usdm",
        source_id="binance_vision_usdm_monthly_klines_archive",
        family=CentralMarketHistoryFamily.OHLCV,
        normalized_symbol="BTC",
        venue_symbol="BTCUSDT",
        timeframe="1m",
        start="2024-01",
        end="2024-01",
        status="collected",
        source_count=1,
        collected_source_count=1,
        parsed_row_count=44640,
        raw_archive_complete=True,
        normalized_archive_complete=True,
        backtest_usable=True,
        strategy_must_call_off_if_required=False,
        reason="complete 1m bar archive",
        manifest_refs=("manifests/unit-btc-bars.json",),
    )
    gated = CentralMarketHistoryCollectionLedgerEntry(
        provider="hyperliquid",
        source_id="hyperliquid_official_s3_l2_book",
        family=CentralMarketHistoryFamily.BOOK,
        normalized_symbol="BTC",
        venue_symbol="BTC",
        timeframe="snapshot",
        start="2024-01-01",
        end="2024-01-31",
        status="operator_gated",
        source_count=31,
        collected_source_count=0,
        operator_gated_source_count=31,
        reason="requester-pays official S3 history requires explicit operator gate",
        notes=("strategy requiring historical L2 must call off unless operator supplies approved source refs",),
    )

    path = write_central_market_history_collection_ledger(
        root=root,
        run_id="unit-collection-ledger",
        entries=(collected, gated),
        notes=("unit-test",),
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["report_type"] == "central_market_history_collection_ledger"
    assert payload["entry_count"] == 2
    assert payload["collected_entry_count"] == 1
    assert payload["operator_gated_entry_count"] == 1
    assert payload["backtest_usable_entry_count"] == 1
    assert payload["entries"][0]["backtest_usable"] is True
    assert payload["entries"][1]["strategy_must_call_off_if_required"] is True
    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["order_placement_instruction"] is False
    assert path.with_suffix(path.suffix + ".sha256").exists()


def test_central_market_history_budget_counts_existing_tree_and_blocks_overflow(tmp_path: Path) -> None:
    root = tmp_path / "central_market_history"
    (root / "raw").mkdir(parents=True)
    (root / "raw" / "seed.bin").write_bytes(b"12345")

    report = central_market_history_budget_report(root, max_bytes=10, planned_bytes=4)

    assert report.current_bytes == 5
    assert report.remaining_bytes == 1
    assert report.within_budget is True
    assert report.research_only is True
    assert report.promotion_ready is False
    assert report.candidate_pack_eligible is False
    assert report.live_signal is False
    assert report.order_placement_instruction is False

    with pytest.raises(ValueError, match="storage budget exceeded"):
        require_central_market_history_budget(root, max_bytes=10, planned_bytes=6)


def test_download_source_plan_rejects_invalid_cache_and_uses_atomic_part(tmp_path: Path) -> None:
    root = tmp_path / "central_market_history"
    plan = build_binance_daily_agg_trades_plan(
        market="futures_um",
        normalized_symbol="BTC",
        venue_symbol="BTCUSDT",
        day="2024-01-01",
        raw_prefix="raw_sources/unit",
    )
    raw_path = root / plan.raw_ref
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(b"partial-not-a-zip")
    payload = _zip_bytes(
        "BTCUSDT-aggTrades-2024-01-01.csv",
        "1,42300.0,0.10,1,1,1704067200000,true\n",
    )

    probe = download_source_plan(plan, root=root, client=_FakeHttpClient(payload), max_bytes=1024 * 1024)

    assert probe.status == "downloaded"
    assert probe.raw_ref == plan.raw_ref
    assert probe.bytes == len(payload)
    assert zipfile.is_zipfile(raw_path)
    assert not raw_path.with_name(raw_path.name + ".part").exists()


def test_parallel_download_preserves_plan_order_and_writes_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "central_market_history"
    progress = root / "manifests" / "parallel-progress.jsonl"
    plans = tuple(
        build_binance_daily_agg_trades_plan(
            market="futures_um",
            normalized_symbol="BTC",
            venue_symbol="BTCUSDT",
            day=f"2024-01-0{day}",
            raw_prefix="raw_sources/unit",
        )
        for day in (1, 2, 3)
    )

    def fake_download(plan: object, **_: object) -> cmhc.CentralMarketHistoryProbeRecord:
        typed = plan  # keep the assertions simple for mypy-free test runtime.
        assert isinstance(typed, cmhc.CentralMarketHistorySourcePlan)
        return cmhc.CentralMarketHistoryProbeRecord(
            provider=typed.provider,
            source_id=typed.source_id,
            source_kind=typed.source_kind,
            url=typed.url,
            normalized_symbol=typed.normalized_symbol,
            venue_symbol=typed.venue_symbol,
            status="downloaded",
            bytes=10,
            raw_ref=typed.raw_ref,
            raw_sha256="a" * 64,
        )

    monkeypatch.setattr(cmhc, "download_source_plan", fake_download)

    probes = cmhc.download_source_plans_parallel(plans, root=root, concurrency=2, progress_path=progress)

    assert [probe.raw_ref for probe in probes] == [plan.raw_ref for plan in plans]
    records = [json.loads(line) for line in progress.read_text(encoding="utf-8").splitlines()]
    assert records[0]["event"] == "download_batch_started"
    assert records[-1]["event"] == "download_batch_completed"
    assert {record["event"] for record in records} >= {"download_started", "download_completed"}
    assert all(record["research_only"] is True for record in records)
    assert all(record["promotion_ready"] is False for record in records)


def test_parallel_download_converts_worker_exception_to_probe_blocker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "central_market_history"
    progress = root / "manifests" / "parallel-error-progress.jsonl"
    plans = tuple(
        build_binance_daily_agg_trades_plan(
            market="futures_um",
            normalized_symbol="BTC",
            venue_symbol="BTCUSDT",
            day=f"2024-01-0{day}",
            raw_prefix="raw_sources/unit",
        )
        for day in (1, 2)
    )

    def fake_download(plan: object, **_: object) -> cmhc.CentralMarketHistoryProbeRecord:
        typed = plan
        assert isinstance(typed, cmhc.CentralMarketHistorySourcePlan)
        if typed.raw_ref.endswith("2024-01-02.zip"):
            raise ValueError("boom")
        return cmhc.CentralMarketHistoryProbeRecord(
            provider=typed.provider,
            source_id=typed.source_id,
            source_kind=typed.source_kind,
            url=typed.url,
            normalized_symbol=typed.normalized_symbol,
            venue_symbol=typed.venue_symbol,
            status="downloaded",
            bytes=10,
            raw_ref=typed.raw_ref,
            raw_sha256="a" * 64,
        )

    monkeypatch.setattr(cmhc, "download_source_plan", fake_download)

    probes = cmhc.download_source_plans_parallel(plans, root=root, concurrency=2, progress_path=progress)

    assert [probe.status for probe in probes] == ["downloaded", "worker_error"]
    assert probes[1].reason == "ValueError"
    records = [json.loads(line) for line in progress.read_text(encoding="utf-8").splitlines()]
    assert any(record.get("status") == "worker_error" for record in records)


def test_binance_monthly_kline_zip_parser_normalizes_rows(tmp_path: Path) -> None:
    raw = tmp_path / "BTCUSDT-1h-2024-01.zip"
    with zipfile.ZipFile(raw, "w") as archive:
        archive.writestr(
            "BTCUSDT-1h-2024-01.csv",
            "\n".join(
                [
                    "1704067200000,42300,42400,42200,42350,12,1704070799999,508200,10,1,2,0",
                    "1704070800000000,42350,42500,42300,42400,8,1704074399999999,339200,7,1,2,0",
                ]
            )
            + "\n",
        )
    plan = build_binance_monthly_kline_plan(
        market="futures_um",
        normalized_symbol="BTC",
        venue_symbol="BTCUSDT",
        interval="1h",
        period="2024-01",
        raw_prefix="raw/downloads/unit",
    )

    rows = rows_from_binance_kline_zip(plan, path=raw, raw_ref="raw/BTC.zip", raw_sha256="a" * 64)

    assert len(rows) == 2
    row = rows[0]
    assert row.provider == "binance_usdm"
    assert row.family == CentralMarketHistoryFamily.OHLCV
    assert row.normalized_symbol == "BTC"
    assert row.venue_symbol == "BTCUSDT"
    assert row.timeframe == "1h"
    assert row.open == 42300.0
    assert row.quote_volume == 508200.0
    assert row.trade_count == 10.0
    assert row.raw_sha256 == "a" * 64
    assert rows[1].timestamp_ms == 1704070800000


def test_binance_of_style_zip_parsers_normalize_trades_depth_and_bbo(tmp_path: Path) -> None:
    raw_sha = "a" * 64
    trades = tmp_path / "AAVEUSDT-trades-2024-01-01.zip"
    depth = tmp_path / "AAVEUSDT-bookDepth-2024-01-01.zip"
    ticker = tmp_path / "AAVEUSDT-bookTicker-2024-01-01.zip"
    _write_zip(
        trades,
        "AAVEUSDT-trades-2024-01-01.csv",
        "id,price,qty,quote_qty,time,is_buyer_maker\n"
        "350343208,108.77,1.4,152.278,1704067203175,true\n",
    )
    _write_zip(
        depth,
        "AAVEUSDT-bookDepth-2024-01-01.csv",
        "timestamp,percentage,depth,notional\n"
        "2024-01-01 00:00:10,-5,11063.46100000,457379319.64167000\n",
    )
    _write_zip(
        ticker,
        "AAVEUSDT-bookTicker-2024-01-01.csv",
        "update_id,best_bid_price,best_bid_qty,best_ask_price,best_ask_qty,transaction_time,event_time\n"
        "3751157810854,108.76000000,11.70000000,108.78000000,8.90000000,1704067203177,1704067204218\n",
    )
    trades_plan = build_binance_daily_trades_plan(
        market="futures_um",
        normalized_symbol="AAVE",
        venue_symbol="AAVEUSDT",
        day="2024-01-01",
        raw_prefix="raw/downloads/unit",
    )
    depth_plan = build_binance_daily_book_depth_plan(
        normalized_symbol="AAVE",
        venue_symbol="AAVEUSDT",
        day="2024-01-01",
        raw_prefix="raw/downloads/unit",
    )
    ticker_plan = build_binance_daily_book_ticker_plan(
        normalized_symbol="AAVE",
        venue_symbol="AAVEUSDT",
        day="2024-01-01",
        raw_prefix="raw/downloads/unit",
    )

    trade_rows = rows_from_binance_trades_zip(trades_plan, path=trades, raw_ref="raw/trades.zip", raw_sha256=raw_sha)
    depth_rows = rows_from_binance_book_depth_zip(depth_plan, path=depth, raw_ref="raw/depth.zip", raw_sha256=raw_sha)
    ticker_rows = rows_from_binance_book_ticker_zip(ticker_plan, path=ticker, raw_ref="raw/ticker.zip", raw_sha256=raw_sha)

    assert trades_plan.url.endswith("/daily/trades/AAVEUSDT/AAVEUSDT-trades-2024-01-01.zip")
    assert depth_plan.url.endswith("/daily/bookDepth/AAVEUSDT/AAVEUSDT-bookDepth-2024-01-01.zip")
    assert ticker_plan.url.endswith("/daily/bookTicker/AAVEUSDT/AAVEUSDT-bookTicker-2024-01-01.zip")
    assert trade_rows[0].family == CentralMarketHistoryFamily.TRADE
    assert trade_rows[0].event_id == "350343208"
    assert trade_rows[0].numeric_fields["quote_quantity"] == 152.278
    assert depth_rows[0].family == CentralMarketHistoryFamily.BOOK
    assert depth_rows[0].timestamp_ms == 1704067210000
    assert depth_rows[0].numeric_fields["band_count"] == 1.0
    assert depth_rows[0].numeric_fields["depth_pct_neg_5"] == 11063.461
    assert depth_rows[0].numeric_fields["notional_pct_neg_5"] == 457379319.64167
    assert ticker_rows[0].family == CentralMarketHistoryFamily.BOOK
    assert ticker_rows[0].event_id == "3751157810854"
    assert ticker_rows[0].numeric_fields["spread"] == pytest.approx(0.02)
    assert ticker_rows[0].raw_sha256 == raw_sha


def test_collect_central_market_history_batch_appends_manifest_discovery_and_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "central_market_history"
    binance_plan = build_binance_daily_agg_trades_plan(
        market="futures_um",
        normalized_symbol="ETH",
        venue_symbol="ETHUSDT",
        day="2024-03-18",
        raw_prefix="raw_sources/unit",
    )
    bybit_plan = build_bybit_public_trading_plan(
        normalized_symbol="ETH",
        venue_symbol="ETHUSDT",
        day="2024-03-18",
        raw_prefix="raw_sources/unit",
    )
    _write_zip(root / binance_plan.raw_ref, "ETHUSDT-aggTrades-2024-03-18.csv", "1,3500.0,0.5,1,1,1710720000000,false\n")
    _write_gzip_csv(
        root / bybit_plan.raw_ref,
        [
            ["timestamp", "symbol", "side", "size", "price", "tickDirection", "trdMatchID", "grossValue"],
            ["1710720000.250", "ETHUSDT", "Buy", "0.25", "3501.0", "PlusTick", "bybit-1", "875.25"],
        ],
    )
    batch = CentralMarketHistoryBatchPlan(
        run_id="unit-parallel-march-collect",
        source_plans=(binance_plan, bybit_plan),
        notes=("unit-test",),
    )

    result = collect_central_market_history_batch(
        root=root,
        batch_plan=batch,
        download_concurrency=2,
        telemetry_ref="manifests/unit-parallel-march-progress.jsonl",
    )

    assert result.centralized_market_history_ready is True
    assert result.parsed_row_count == 2
    assert result.manifest_ref is not None
    assert result.discovery_report_ref is not None
    assert (root / result.manifest_ref).exists()
    assert (root / result.discovery_report_ref).exists()
    assert (root / "manifests" / "unit-parallel-march-progress.jsonl").exists()
    append_lines = (root / "manifests" / "append_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(append_lines) == 1

    rerun = collect_central_market_history_batch(
        root=root,
        batch_plan=batch,
        download_concurrency=2,
        telemetry_ref="manifests/unit-parallel-march-progress-rerun.jsonl",
    )

    assert rerun.existing_batch is True
    assert rerun.manifest_ref == result.manifest_ref
    assert len((root / "manifests" / "append_manifest.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_bybit_trading_gzip_parser_relaxes_trade_equality(tmp_path: Path) -> None:
    raw = tmp_path / "BTCUSDT2024-01-01.csv.gz"
    with gzip.open(raw, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "timestamp",
                "symbol",
                "side",
                "size",
                "price",
                "tickDirection",
                "trdMatchID",
                "grossValue",
                "homeNotional",
                "foreignNotional",
            ]
        )
        writer.writerow(["1704067200.2353", "BTCUSDT", "Sell", "0.002", "42324.90", "PlusTick", "abc", "8.4", "0.002", "84.6"])
    plan = build_bybit_public_trading_plan(
        normalized_symbol="BTC",
        venue_symbol="BTCUSDT",
        day="2024-01-01",
        raw_prefix="raw/downloads/unit",
    )

    rows = rows_from_bybit_trading_gzip(plan, path=raw, raw_ref="raw/BTC.csv.gz", raw_sha256="b" * 64)

    assert len(rows) == 1
    row = rows[0]
    assert row.provider == "bybit_linear"
    assert row.family == CentralMarketHistoryFamily.TRADE
    assert row.event_id == "abc"
    assert row.numeric_fields["price"] == 42324.90
    assert row.numeric_fields["quantity"] == 0.002
    assert row.numeric_fields["side"] == -1.0
    assert row.promotion_ready is False
    assert row.order_placement_instruction is False


def test_bybit_spot_gzip_parser_accepts_volume_and_millisecond_timestamp(tmp_path: Path) -> None:
    raw = tmp_path / "BTCUSDT-2024-01.csv.gz"
    with gzip.open(raw, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "timestamp", "price", "volume", "side"])
        writer.writerow(["1", "1704067200477", "42283.99", "0.042569", "sell"])
    plan = build_bybit_spot_monthly_trades_plan(
        normalized_symbol="BTC",
        venue_symbol="BTCUSDT",
        period="2024-01",
        raw_prefix="raw/downloads/unit",
    )

    rows = rows_from_bybit_trading_gzip(plan, path=raw, raw_ref="raw/BTC-spot.csv.gz", raw_sha256="c" * 64)

    assert plan.url.endswith("/spot/BTCUSDT/BTCUSDT-2024-01.csv.gz")
    assert len(rows) == 1
    row = rows[0]
    assert row.provider == "bybit_spot"
    assert row.timestamp_ms == 1704067200477
    assert row.event_id == "1"
    assert row.numeric_fields["quantity"] == 0.042569
    assert row.numeric_fields["side"] == -1.0


def test_bybit_mt4_kline_builder_uses_public_year_and_month_range_path() -> None:
    plan = build_bybit_mt4_kline_plan(
        normalized_symbol="BTC",
        venue_symbol="BTCUSDT",
        mt4_interval="15",
        period="2024-02",
        raw_prefix="raw/downloads/unit",
    )

    assert plan.url.endswith("/kline_for_metatrader4/BTCUSDT/2024/BTCUSDT_15_2024-02-01_2024-02-29.csv.gz")
    assert plan.raw_ref.endswith("BTCUSDT_15_2024-02-01_2024-02-29.csv.gz")
    assert plan.timeframe == "15m"


def test_bybit_index_gzip_parser_writes_metadata_rows(tmp_path: Path) -> None:
    raw = tmp_path / "BTCUSD2024-01-01_premium_index.csv.gz"
    with gzip.open(raw, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["start_at", "symbol", "period", "open", "high", "low", "close"])
        writer.writerow(["1704067200", "BTCUSD", "1", "0.00056", "0.00057", "0.00042", "0.00043"])
    plan = build_bybit_index_plan(
        normalized_symbol="BTC",
        venue_symbol="BTCUSD",
        day="2024-01-01",
        index_kind="premium_index",
        raw_prefix="raw/downloads/unit",
    )

    rows = rows_from_bybit_index_gzip(plan, path=raw, raw_ref="raw/BTC-index.csv.gz", raw_sha256="d" * 64)

    assert plan.url.endswith("/premium_index/BTCUSD/BTCUSD2024-01-01_premium_index.csv.gz")
    assert len(rows) == 1
    row = rows[0]
    assert row.provider == "bybit_inverse"
    assert row.family == CentralMarketHistoryFamily.METADATA
    assert row.timeframe is None
    assert row.timestamp_ms == 1704067200000
    assert row.numeric_fields["open"] == 0.00056
    assert row.numeric_fields["period_minutes"] == 1.0
    assert row.raw_sha256 == "d" * 64
    assert row.research_only is True
    assert row.promotion_ready is False
    assert row.order_placement_instruction is False


def test_discovery_report_writes_append_safe_boundary_payload(tmp_path: Path) -> None:
    root = tmp_path / "central_market_history"
    plan = build_bybit_public_trading_plan(
        normalized_symbol="BTC",
        venue_symbol="BTCUSDT",
        day="2024-01-01",
        raw_prefix="raw/downloads/unit",
    )
    probe = plan.model_copy(
        update={
            "research_only": True,
            "promotion_ready": False,
        }
    )
    # Use the public probe model via the download-independent helper shape.
    from tradingbotsuite.v2.data_sources.central_market_history_collection import CentralMarketHistoryProbeRecord

    record = CentralMarketHistoryProbeRecord(
        provider=probe.provider,
        source_id=probe.source_id,
        source_kind=probe.source_kind,
        url=probe.url,
        normalized_symbol=probe.normalized_symbol,
        venue_symbol=probe.venue_symbol,
        status="http_error",
        http_status=404,
        reason="http_status:404",
    )

    path = write_central_market_history_discovery_report(root=root, run_id="unit-discovery", probes=(record,))
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["live_signal"] is False
    assert payload["order_placement_instruction"] is False
    assert payload["probe_count"] == 1
    assert payload["blocker_count"] == 1
    assert path.with_suffix(path.suffix + ".sha256").exists()


class _FakeHttpClient:
    def __init__(self, payload: bytes, *, status_code: int = 200) -> None:
        self._payload = payload
        self._status_code = status_code

    def head(self, _: str) -> "_FakeResponse":
        return _FakeResponse(self._status_code, self._payload)

    def stream(self, _: str, __: str) -> "_FakeResponse":
        return _FakeResponse(self._status_code, self._payload)

    def close(self) -> None:
        return None


class _FakeResponse:
    def __init__(self, status_code: int, payload: bytes) -> None:
        self.status_code = status_code
        self.headers = {"content-length": str(len(payload))}
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def iter_bytes(self) -> object:
        midpoint = max(1, len(self._payload) // 2)
        yield self._payload[:midpoint]
        yield self._payload[midpoint:]


def _zip_bytes(name: str, body: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, body)
    return buffer.getvalue()


def _write_zip(path: Path, name: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, body)


def _write_gzip_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)
