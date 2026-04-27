import pandas as pd
import pytest

from tradingbot.backtest import Backtester
from tradingbot.config import default_app_config
from tradingbot.lorentz import LorentzianClassifier
from tradingbot.market_structure import MarketStructureEngine
from tradingbot.optimization import WalkForwardOptimizer
from tradingbot.order_blocks import OrderBlockEngine


def _make_frame(freq: str, periods: int) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=periods, freq=freq, tz="UTC")
    closes = [100 + i * 0.4 + ((-1) ** i) * 0.2 for i in range(periods)]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes,
            "high": [value + 0.7 for value in closes],
            "low": [value - 0.7 for value in closes],
            "close": closes,
            "volume": [100 + (i % 5) * 10 for i in range(periods)],
            "symbol": ["BTC"] * periods,
        }
    )


def test_lorentz_and_backtest_smoke():
    base = _make_frame("15min", 140)
    config = default_app_config()

    lorentz = LorentzianClassifier().generate(base, config.strategies["BTC"])
    assert "start_long_trade" in lorentz.columns
    assert "end_short_trade" in lorentz.columns

    events = MarketStructureEngine().generate(base, config.strategies["BTC"])
    timeline = OrderBlockEngine().process(base, events, config.strategies["BTC"])
    assert isinstance(timeline.blocks, list)

    report = Backtester().run(base, None, config, "BTC")
    assert "net_profit" in report.metrics
    assert report.metrics["final_equity"] > 0
    assert report.blocks == []


def test_optimizer_includes_baseline_comparison():
    base = _make_frame("15min", 240)
    config = default_app_config()
    config.optimization.minimum_trades = 1
    config.optimization.parallel_workers = 1
    config.optimization.shortlist_size = 2
    config.optimization.search_space = {
        "neighbors_count": [6, 8],
        "feature_1.param_a": [13, 14],
        "risk.risk_per_trade": [0.005, 0.01],
    }

    result = WalkForwardOptimizer().optimize(base, None, config, "BTC")

    assert result.baseline_report.symbol == "BTC"
    assert "baseline_net_profit" in result.comparison_to_baseline
    assert "optimized_net_profit" in result.comparison_to_baseline
    assert result.candidate_count == 8
    assert result.shortlisted_candidate_count == 2
    assert len(result.prescreen_top_candidates) == 2
    assert set(result.search_space.keys()) == {"neighbors_count", "feature_1.param_a", "risk.risk_per_trade"}
    for change in result.changed_fields:
        assert change["field"] in {"neighbors_count", "feature_1.param_a", "risk.risk_per_trade"}


def test_default_optimizer_search_space_is_feature_only():
    config = default_app_config()

    search_space = WalkForwardOptimizer()._search_space(config, "BTC")

    assert search_space
    assert all(key.startswith("feature_") for key in search_space)


def test_backtester_uses_confirm_candles_for_subcandle_execution():
    base = _make_frame("15min", 4)
    confirm = _make_frame("5min", 12)
    config = default_app_config()
    config.risk.use_fixed_stop_loss = True
    config.risk.fixed_stop_loss_pct = 0.5
    config.backtest.slow_reference_mode = True

    signal_frame = base.copy()
    signal_frame["f1"] = 0.0
    signal_frame["f2"] = 0.0
    signal_frame["f3"] = 0.0
    signal_frame["f4"] = 0.0
    signal_frame["f5"] = 0.0
    signal_frame["prediction"] = 0.0
    signal_frame["signal"] = 0
    signal_frame["bars_held"] = 0
    signal_frame["is_early_signal_flip"] = False
    signal_frame["yhat1"] = base["close"]
    signal_frame["yhat2"] = base["close"]
    signal_frame["kernel_estimate"] = base["close"]
    signal_frame["alert_bullish"] = False
    signal_frame["alert_bearish"] = False
    signal_frame["is_bullish"] = True
    signal_frame["is_bearish"] = True
    signal_frame["volatility_filter"] = True
    signal_frame["regime_filter"] = True
    signal_frame["adx_filter"] = True
    signal_frame["filter_all"] = True
    signal_frame["start_long_trade"] = [True, False, False, False]
    signal_frame["start_short_trade"] = [False, False, False, False]
    signal_frame["end_long_trade"] = [False, True, False, False]
    signal_frame["end_short_trade"] = [False, False, False, False]
    signal_frame["atr_stop"] = base["close"]

    backtester = Backtester()
    backtester.lorentz = type(
        "StubLorentz",
        (),
        {"generate": lambda self, df, strategy: signal_frame.iloc[: len(df)].copy()},
    )()
    report = backtester.run(base, confirm, config, "BTC")

    assert len(report.trades) == 1
    trade = report.trades[0]
    assert trade.entry_timestamp == confirm.iloc[0]["timestamp"]
    assert trade.exit_timestamp == confirm.iloc[3]["timestamp"]
    assert trade.entry_price == pytest.approx(float(confirm.iloc[0]["close"]))
    assert trade.exit_price == pytest.approx(float(confirm.iloc[3]["close"]))
