from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tradingbotsuite.v2.collectors.historical_dataset import (
    HistoricalPerpDatasetConfig,
    collect_historical_perp_dataset,
)
from tradingbotsuite.v2.venues.contracts import VenueRawRequest, VenueRawResponse
from tradingbotsuite.v2.venues.hyperliquid import (
    HYPERLIQUID_CANDLE_SNAPSHOT_SOURCE,
    HYPERLIQUID_META_AND_ASSET_CTXS_SOURCE,
    HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID,
    HyperliquidInfoFetchResult,
    hyperliquid_public_info_capability,
)


def test_collect_historical_perp_dataset_writes_archive_report_and_binance_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result = collect_historical_perp_dataset(
        config,
        hyperliquid_client=_FakeHyperliquidClient(),
        binance_fetcher=_fake_binance_fetcher,
    )

    assert result.accepted_research_ready is False
    assert result.universe_mode == "current_labeled_sandbox"
    assert result.evidence_mode == "sandbox_diagnostic"
    assert result.universe_eligible_count == 2
    assert result.selected_instrument_count == 2
    assert result.collected_instrument_count == 2
    assert result.technical_coverage_pass_count == 2
    assert result.min_coverage_ratio == 1.0
    assert result.binance_pass_count == 1
    assert result.binance_skipped_count == 1
    assert result.funding_collected_count == 2
    assert Path(result.report_path).exists()

    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["accepted_research_ready"] is False
    assert "current_public_universe_not_historical_asof" in report["caveats"]
    assert {row["instrument_id"] for row in report["instrument_summaries"]} == {
        "hyperliquid:perp:BTC",
        "hyperliquid:perp:ETH",
    }
    assert all(row["technical_coverage_pass"] for row in report["instrument_summaries"])
    assert all(row["funding_status"] == "collected" for row in report["instrument_summaries"])
    assert {row["status"] for row in report["binance_validation"]} == {"passed", "skipped"}


def test_historical_perp_dataset_config_rejects_accepted_research_mode(tmp_path: Path) -> None:
    payload = _config(tmp_path).model_dump()
    payload["evidence_mode"] = "accepted_research"
    with pytest.raises(ValueError, match="sandbox_diagnostic"):
        HistoricalPerpDatasetConfig(**payload)


def test_collect_historical_perp_dataset_accepts_trusted_intraday_records_file(tmp_path: Path) -> None:
    trusted_root = tmp_path / "trusted-hyperliquid-candles"
    trusted_root.mkdir()
    _write_trusted_candle_records(trusted_root / "BTC_1h.jsonl", coin="BTC")
    _write_trusted_candle_records(trusted_root / "ETH_1h.jsonl", coin="ETH")
    config = _config(
        tmp_path,
        end_ts=datetime(2024, 1, 1, 3, tzinfo=UTC),
        timeframe="1h",
        candle_source="trusted_records",
        trusted_candle_records_root=str(trusted_root),
    )

    result = collect_historical_perp_dataset(
        config,
        hyperliquid_client=_FakeTrustedRecordsHyperliquidClient(),
        binance_fetcher=_fake_binance_fetcher,
    )

    assert result.candle_source == "trusted_records"
    assert result.accepted_research_ready is False
    assert result.collected_instrument_count == 2
    assert result.technical_coverage_pass_count == 2
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert {row["candle_source"] for row in report["instrument_summaries"]} == {"trusted_records"}
    assert {row["source_row_count"] for row in report["instrument_summaries"]} == {3}
    assert {row["trusted_records_file_row_count"] for row in report["instrument_summaries"]} == {4}
    assert all(row["trusted_records_file_sha256"] for row in report["instrument_summaries"])


def test_trusted_intraday_records_file_template_must_stay_inside_root(tmp_path: Path) -> None:
    trusted_root = tmp_path / "trusted-hyperliquid-candles"
    trusted_root.mkdir()
    config = _config(
        tmp_path,
        end_ts=datetime(2024, 1, 1, 3, tzinfo=UTC),
        timeframe="1h",
        candle_source="trusted_records",
        trusted_candle_records_root=str(trusted_root),
        trusted_candle_records_template="../{coin}_{timeframe}.jsonl",
        coins=("BTC",),
        max_instruments=0,
    )

    result = collect_historical_perp_dataset(
        config,
        hyperliquid_client=_FakeTrustedRecordsHyperliquidClient(),
        binance_fetcher=_fake_binance_fetcher,
    )

    assert result.collected_instrument_count == 0
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["instrument_summaries"][0]["status"] == "skipped"
    assert "collection_failed:path escapes configured root" in report["instrument_summaries"][0]["reason"]


def test_trusted_intraday_records_mode_requires_a_root(tmp_path: Path) -> None:
    payload = _config(tmp_path).model_dump()
    payload["candle_source"] = "trusted_records"
    with pytest.raises(ValueError, match="trusted_candle_records_root"):
        HistoricalPerpDatasetConfig(**payload)


def _config(
    tmp_path: Path,
    *,
    end_ts: datetime | None = None,
    timeframe: str = "1d",
    candle_source: str = "public_api",
    trusted_candle_records_root: str | None = None,
    trusted_candle_records_template: str = "{coin}_{timeframe}.jsonl",
    coins: tuple[str, ...] = (),
    max_instruments: int = 2,
) -> HistoricalPerpDatasetConfig:
    return HistoricalPerpDatasetConfig(
        output_root=str(tmp_path / "out"),
        archive_root=str(tmp_path / "out" / "archive"),
        run_id="unit-historical-perps",
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=end_ts or datetime(2024, 1, 4, tzinfo=UTC),
        timeframe=timeframe,
        asof_date=date(2026, 6, 22),
        max_instruments=max_instruments,
        coins=coins,
        candle_source=candle_source,
        trusted_candle_records_root=trusted_candle_records_root,
        trusted_candle_records_template=trusted_candle_records_template,
        validate_binance=True,
        include_funding=True,
    )


class _FakeHyperliquidClient:
    def fetch_meta_and_asset_contexts(self) -> HyperliquidInfoFetchResult:
        payload = [
            {
                "universe": [
                    {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
                    {"name": "ETH", "szDecimals": 4, "maxLeverage": 50},
                    {"name": "TINY", "szDecimals": 2, "maxLeverage": 3},
                ]
            },
            [
                {"dayNtlVlm": "100000000", "markPx": "100", "oraclePx": "100", "funding": "0.0001"},
                {"dayNtlVlm": "50000000", "markPx": "200", "oraclePx": "200", "funding": "0.0001"},
                {"dayNtlVlm": "100", "markPx": "1", "oraclePx": "1", "funding": "0.0001"},
            ],
        ]
        return _fetch_result(
            source=HYPERLIQUID_META_AND_ASSET_CTXS_SOURCE,
            payload=payload,
            row_count=3,
            params={"type": "metaAndAssetCtxs"},
        )

    def fetch_candle_snapshot(
        self,
        *,
        coin: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> HyperliquidInfoFetchResult:
        rows: list[dict[str, Any]] = []
        current = start_time
        base = 100.0 if coin == "BTC" else 200.0
        index = 0
        while current < end_time:
            close = base + index
            rows.append(
                {
                    "t": int(current.timestamp() * 1000),
                    "T": int((current + timedelta(days=1)).timestamp() * 1000) - 1,
                    "s": coin,
                    "i": interval,
                    "o": str(close - 1.0),
                    "h": str(close + 1.0),
                    "l": str(close - 2.0),
                    "c": str(close),
                    "v": "10",
                    "n": 1,
                }
            )
            current += timedelta(days=1)
            index += 1
        return _fetch_result(
            source=HYPERLIQUID_CANDLE_SNAPSHOT_SOURCE,
            payload=rows,
            row_count=len(rows),
            params={"type": "candleSnapshot", "coin": coin},
        )

    def fetch_funding_history(
        self,
        *,
        coin: str,
        start_time: datetime,
        end_time: datetime,
    ) -> HyperliquidInfoFetchResult:
        if start_time > datetime(2024, 1, 1, tzinfo=UTC):
            rows: list[dict[str, Any]] = []
        else:
            rows = []
            current = start_time
            while current < end_time:
                rows.append(
                    {
                        "coin": coin,
                        "fundingRate": "0.0001",
                        "premium": "0.0002",
                        "time": int(current.timestamp() * 1000),
                    }
                )
                current += timedelta(hours=1)
        return _fetch_result(
            source="info/fundingHistory",
            payload=rows,
            row_count=len(rows),
            params={"type": "fundingHistory", "coin": coin},
        )


class _FakeTrustedRecordsHyperliquidClient(_FakeHyperliquidClient):
    def fetch_candle_snapshot(
        self,
        *,
        coin: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> HyperliquidInfoFetchResult:
        raise AssertionError("trusted_records mode must not call public candleSnapshot")


def _fetch_result(
    *,
    source: str,
    payload: Any,
    row_count: int,
    params: dict[str, Any],
) -> HyperliquidInfoFetchResult:
    capability = hyperliquid_public_info_capability()
    request = VenueRawRequest.build(
        adapter_id=HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID,
        venue="hyperliquid",
        source=source,
        params=params,
    )
    response = VenueRawResponse.build(
        request=request,
        payload=payload,
        row_count=row_count,
        rate_limit_metadata={"mode": "unit"},
    )
    return HyperliquidInfoFetchResult(
        capability=capability,
        raw_request=request,
        raw_response=response,
        payload=payload,
    )


def _write_trusted_candle_records(path: Path, *, coin: str) -> None:
    lines = [
        json.dumps(_trusted_candle_row(coin=coin, index=index, ts=datetime(2024, 1, 1, index, tzinfo=UTC)))
        for index in range(3)
    ]
    lines.append(json.dumps(_trusted_candle_row(coin=coin, index=99, ts=datetime(2024, 1, 2, tzinfo=UTC))))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _trusted_candle_row(*, coin: str, index: int, ts: datetime) -> dict[str, Any]:
    close = (100.0 if coin == "BTC" else 200.0) + index
    return {
        "t": int(ts.timestamp() * 1000),
        "T": int((ts + timedelta(hours=1)).timestamp() * 1000) - 1,
        "s": coin,
        "i": "1h",
        "o": str(close - 1.0),
        "h": str(close + 1.0),
        "l": str(close - 2.0),
        "c": str(close),
        "v": "10",
        "n": 1,
    }


def _fake_binance_fetcher(
    symbol: str,
    timeframe: str,
    start_ts: datetime,
    end_ts: datetime,
) -> list[dict[str, Any]]:
    if symbol != "BTCUSDT":
        return []
    rows: list[dict[str, Any]] = []
    current = start_ts
    index = 0
    while current < end_ts:
        close = 100.0 + index
        rows.append(
            {
                "ts": int(current.timestamp() * 1000),
                "open": close - 1.0,
                "high": close + 1.0,
                "low": close - 2.0,
                "close": close * 1.0001,
                "volume": 100.0,
            }
        )
        current += timedelta(days=1)
        index += 1
    return rows
