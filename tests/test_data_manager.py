from pathlib import Path

import pandas as pd
import pytest

from tradingbot.cli import _load_csv
from tradingbot.config import default_app_config
from tradingbot.data.manager import DataManager
from tradingbot.models import RiskConfig, Side
from tradingbot.risk import compute_initial_stop


class _FakeProvider:
    def __init__(self, frame: pd.DataFrame):
        self.frame = frame.copy()
        self.calls = 0

    def fetch_candles(self, symbol: str, interval: str, start_time_ms: int, end_time_ms: int) -> pd.DataFrame:
        self.calls += 1
        return self.frame.copy()

    def close(self) -> None:
        return None


def _make_frame(start: str, periods: int, freq: str, symbol: str = "BTC") -> pd.DataFrame:
    timestamps = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    prices = [100 + idx for idx in range(periods)]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices,
            "high": [price + 1 for price in prices],
            "low": [price - 1 for price in prices],
            "close": prices,
            "volume": [10] * periods,
            "symbol": [symbol] * periods,
        }
    )


def test_load_csv_placeholder_error():
    with pytest.raises(SystemExit) as exc:
        _load_csv("path\\to\\btc_15m.csv", symbol="BTC", timeframe="15m")
    assert "README placeholder" in str(exc.value)
    assert "fetch-data" in str(exc.value)


def test_load_csv_missing_file_error():
    with pytest.raises(SystemExit) as exc:
        _load_csv("missing.csv", symbol="BTC", timeframe="15m")
    assert "CSV file not found" in str(exc.value)
    assert "fetch-data" in str(exc.value)


def test_data_manager_merges_fallback_and_writes_cache(tmp_path: Path):
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    end = pd.Timestamp("2026-01-01T01:00:00Z")
    primary = _make_frame("2026-01-01T00:30:00Z", 3, "15min")
    fallback = _make_frame("2026-01-01T00:00:00Z", 2, "15min")
    manager = DataManager(
        output_dir=tmp_path,
        primary_provider=_FakeProvider(primary),
        fallback_provider=_FakeProvider(fallback),
    )

    resolution = manager.fetch_dataset("BTC", "15m", start, end, provider_policy="hyperliquid_fallback")

    saved = pd.read_csv(resolution.csv_path)
    assert resolution.csv_path.exists()
    assert resolution.metadata_path.exists()
    assert saved["timestamp"].iloc[0].startswith("2026-01-01 00:00:00")
    assert saved["timestamp"].iloc[-1].startswith("2026-01-01 01:00:00")
    assert len(saved) == 5
    assert len(resolution.providers) == 2
    assert resolution.gaps == []


def test_data_manager_reuses_cache_without_refresh(tmp_path: Path):
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    end = pd.Timestamp("2026-01-01T01:00:00Z")
    primary = _FakeProvider(_make_frame("2026-01-01T00:00:00Z", 5, "15min"))
    fallback = _FakeProvider(pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "symbol"]))
    manager = DataManager(output_dir=tmp_path, primary_provider=primary, fallback_provider=fallback)

    first = manager.resolve_dataset("BTC", "15m", start, end, force_refresh=True)
    second = manager.resolve_dataset("BTC", "15m", start, end, force_refresh=False)

    assert first.csv_path == second.csv_path
    assert primary.calls == 1


def test_default_config_is_btc_only_and_guardeer_disabled():
    config = default_app_config()
    assert list(config.strategies.keys()) == ["BTC"]
    assert config.strategies["BTC"].use_order_block_exits is False


def test_data_manager_raises_on_high_cross_exchange_deviation(tmp_path: Path):
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    end = pd.Timestamp("2026-01-01T01:00:00Z")
    primary = _make_frame("2026-01-01T00:00:00Z", 5, "15min")
    fallback = _make_frame("2026-01-01T00:00:00Z", 5, "15min")
    fallback["close"] = fallback["close"] * 1.10
    config = default_app_config()
    config.data.min_validation_overlap_rows = 1
    config.data.max_close_deviation_pct = 0.5
    manager = DataManager(output_dir=tmp_path, app_config=config, primary_provider=_FakeProvider(primary), fallback_provider=_FakeProvider(fallback))

    with pytest.raises(RuntimeError) as exc:
        manager.fetch_dataset("BTC", "15m", start, end, provider_policy="hyperliquid_only")

    assert "deviation" in str(exc.value)


def test_default_risk_config_disables_fixed_stop_loss():
    config = default_app_config()
    assert config.risk.use_fixed_stop_loss is False
    assert config.risk.fixed_stop_loss_pct == pytest.approx(0.0055)


def test_fixed_hard_stop_loss_uses_055_percent_when_enabled():
    frame = _make_frame("2026-01-01T00:00:00Z", 5, "15min")
    risk = RiskConfig(use_fixed_stop_loss=True, fixed_stop_loss_pct=0.0055)

    long_stop = compute_initial_stop(frame, 0, Side.LONG, risk)
    short_stop = compute_initial_stop(frame, 0, Side.SHORT, risk)

    assert long_stop == pytest.approx(100.0 * (1.0 - 0.0055))
    assert short_stop == pytest.approx(100.0 * (1.0 + 0.0055))
