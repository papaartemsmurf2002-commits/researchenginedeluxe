from pathlib import Path

import numpy as np
import pandas as pd

from tradingbot.config import default_app_config, load_app_config
from tradingbot.backtest import Backtester
from tradingbot.features_tv import ema, filter_volatility, n_adx, n_cci, n_rsi, n_wt, rma, rsi
from tradingbot.kernels_tv import gaussian, rational_quadratic
from tradingbot.lc_marker_research import run_marker_research
from tradingbot.lorentz import LorentzianClassifier
from tradingbot.lorentz_tv import _pine_round
from tradingbot.parity import _bool_marker, _match_entry_events, _normalize_tv_export, generate_parity_dump, merge_tv_exports, run_entry_parity_check, run_parity_check
from tradingbot.tv_backtest import run_tv_backtest


def _make_frame(periods: int = 80) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=periods, freq="15min", tz="UTC")
    closes = [100 + i * 0.5 + ((-1) ** i) * 0.3 for i in range(periods)]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes,
            "high": [value + 0.8 for value in closes],
            "low": [value - 0.8 for value in closes],
            "close": closes,
            "volume": [100 + (i % 4) * 25 for i in range(periods)],
            "symbol": ["BTC"] * periods,
        }
    )


def test_tv_feature_helpers_are_normalized():
    frame = _make_frame()
    rsi_feature = n_rsi(frame["close"], 14, 1)
    cci_feature = n_cci(frame["close"], 23, 1)
    wt_feature = n_wt((frame["high"] + frame["low"] + frame["close"]) / 3.0, 10, 11)
    adx_feature = n_adx(frame["high"], frame["low"], frame["close"], 27)

    for series in [rsi_feature, cci_feature, wt_feature, adx_feature]:
        cleaned = series.dropna()
        assert not cleaned.empty
        assert (cleaned >= -1e-9).all()
        assert (cleaned <= 1.0 + 1e-9).all()


def test_pine_helpers_preserve_warmup_na_values():
    values = pd.Series([1, 2, 3, 4, 5, 6], dtype=float)

    assert pd.isna(rma(values, 4).iloc[2])
    assert pd.notna(rma(values, 4).iloc[3])
    assert pd.isna(rsi(values, 4).iloc[3])
    assert pd.isna(ema(values, 4).iloc[2])
    assert ema(values, 4).iloc[3] == 2.5


def test_wavetrend_warmup_matches_tradingview_diagnostic_export():
    tv_path = Path("data/parity/tv_lc_17_18_merged_diagnostics_overlap.csv")
    if not tv_path.exists():
        return
    export = pd.read_csv(tv_path)
    source = (export["high"] + export["low"] + export["close"]) / 3.0

    wt_feature = n_wt(source, 10, 11)

    for idx in [0, 19, 30]:
        assert pd.isna(wt_feature.iloc[idx])
        assert pd.isna(export.loc[idx, "f2"])
    for idx in [31, 32, 57, 613, 1999, 9120]:
        assert np.isclose(wt_feature.iloc[idx], export.loc[idx, "f2"], atol=1e-9)


def test_source_guided_kernels_produce_series():
    frame = _make_frame()
    rq = rational_quadratic(frame["close"], 20, 8.0, 10)
    gs = gaussian(frame["close"], 18, 10)

    assert len(rq) == len(frame)
    assert len(gs) == len(frame)
    assert rq.notna().any()
    assert gs.notna().any()


def test_tv_backtest_counts_simple_trade():
    frame = _make_frame(8)
    signal_frame = frame.copy()
    signal_frame["start_long_trade"] = [False, True, False, False, False, False, False, False]
    signal_frame["end_long_trade"] = [False, False, True, False, False, False, False, False]
    signal_frame["start_short_trade"] = False
    signal_frame["end_short_trade"] = False
    signal_frame["is_early_signal_flip"] = False

    result = run_tv_backtest(signal_frame, max_bars_back_index=0, use_worst_case=True)

    assert result.summary["total_wins"] == 1.0
    assert result.summary["total_losses"] == 0.0
    assert result.summary["total_trades"] == 1.0
    assert result.summary["win_rate"] == 1.0


def test_parity_check_matches_self_generated_export():
    frame = _make_frame(120)
    config = default_app_config()
    signal_frame = LorentzianClassifier().generate(frame, config.strategies["BTC"])
    max_bars_back_index = max(len(signal_frame) - 1 - config.strategies["BTC"].max_bars_back, 0) if len(signal_frame) - 1 >= config.strategies["BTC"].max_bars_back else 0
    tv_frame = run_tv_backtest(signal_frame, max_bars_back_index, config.backtest.use_worst_case).frame
    export = tv_frame[
        [
            "timestamp",
            "f1",
            "f2",
            "f3",
            "f4",
            "f5",
            "yhat1",
            "yhat2",
            "prediction",
            "signal",
            "bars_held",
            "start_long_trade",
            "start_short_trade",
            "end_long_trade",
            "end_short_trade",
            "is_early_signal_flip",
            "is_bullish",
            "is_bearish",
            "tv_total_wins",
            "tv_total_losses",
            "tv_total_trades",
            "tv_total_early_signal_flips",
            "tv_win_loss_ratio",
            "tv_win_rate",
        ]
    ].copy()

    result = run_parity_check(frame, export, config, "BTC")

    assert result.matched is True
    assert result.first_divergence is None


def test_tv_export_marker_parser_separates_shape_markers_from_diagnostics():
    timestamps = pd.date_range("2026-01-01", periods=4, freq="15min", tz="UTC")
    export = pd.DataFrame(
        {
            "time": [int(timestamp.timestamp()) for timestamp in timestamps],
            "startLongTrade": [0, 1, "0", "1"],
            "startShortTrade": ["0", "1", "", None],
            "Buy": ["", 100.5, None, 101.0],
            "StopBuy": [np.nan, 0.0, "", "102.0"],
        }
    )

    normalized = _normalize_tv_export(export)

    assert normalized["start_long_trade"].tolist() == [False, True, False, True]
    assert normalized["start_short_trade"].tolist() == [False, True, False, False]
    assert normalized["end_long_trade"].tolist() == [False, True, False, True]
    assert _bool_marker(normalized, "Buy").tolist() == [False, True, False, True]


def test_numeric_diagnostic_marker_zero_is_false():
    frame = pd.DataFrame({"start_long_trade_tv": [0, 1, np.nan, "0", "1"]})

    assert _bool_marker(frame, "start_long_trade_tv").tolist() == [False, True, False, False, True]


def test_pine_round_uses_half_up_semantics_for_ann_pivot():
    assert _pine_round(4.5) == 5
    assert _pine_round(7.5) == 8
    assert _pine_round(10.5) == 11


def test_pine_exact_training_label_polarity_is_literal_pine():
    frame = _make_frame(12)
    frame.loc[4, "close"] = frame.loc[0, "close"] + 10
    config = default_app_config()

    signal_frame = LorentzianClassifier().generate(frame, config.strategies["BTC"])

    assert signal_frame.loc[4, "y_train"] == -1


def test_parity_check_reports_first_divergence_subsystem():
    frame = _make_frame(120)
    config = default_app_config()
    export = generate_parity_dump(frame, config, "BTC")[["timestamp", "f1", "prediction"]].copy()
    valid_index = int(export["f1"].first_valid_index())
    export.loc[valid_index, "f1"] = float(export.loc[valid_index, "f1"]) + 0.5

    result = run_parity_check(frame, export, config, "BTC", column_group="features")

    assert result.matched is False
    assert result.first_divergence is not None
    assert result.first_divergence["column"] == "f1"
    assert result.first_divergence["subsystem"] == "feature_helper"


def test_btc_kernel_fixture_matches_export_defaults_after_warmup():
    base_path = Path("data/parity/binance_btcusdt_p_off_base_with_prehistory.csv")
    tv_path = Path("BINANCE_BTCUSDT.P.csv")
    if not base_path.exists() or not tv_path.exists():
        return
    base = pd.read_csv(base_path)
    base["timestamp"] = pd.to_datetime(base["timestamp"], utc=True)
    export = pd.read_csv(tv_path)
    config = load_app_config("examples/btc_tv_off_parity.yaml")
    strategy = config.strategies["BTC"]
    strategy.kernel_lookback = 8
    strategy.kernel_relative_weight = 8.0
    strategy.kernel_regression_level = 25

    result = run_parity_check(base, export, config, "BTC", column_group="kernel", tolerance=0.01, skip_rows=26)

    assert result.matched is True
    assert result.first_divergence is None
    assert "yhat1" in result.compared_columns


def test_btc_1k_marker_export_kernel_matches_after_warmup():
    tv_path = Path("C:/Users/papaa/Downloads/BINANCE_BTCUSDT.P, 15 (14).csv")
    if not tv_path.exists():
        return
    export = pd.read_csv(tv_path)
    base = export[["time", "open", "high", "low", "close"]].copy()
    base["timestamp"] = pd.to_datetime(base["time"], unit="s", utc=True)
    base["volume"] = 0.0
    base["symbol"] = "BTC"
    config = load_app_config("examples/btc_lc_close_10_1000.yaml")

    result = run_parity_check(base, export, config, "BTC", column_group="kernel", tolerance=0.01, skip_rows=26)

    assert result.matched is True
    assert result.first_divergence is None
    assert "yhat1" in result.compared_columns


def test_kernel_preflight_detects_active_config_export_mismatch():
    base_path = Path("data/parity/binance_btcusdt_p_off_base_with_prehistory.csv")
    export_path = Path("BINANCE_BTCUSDT.P.csv")
    if not base_path.exists() or not export_path.exists():
        return
    base = pd.read_csv(base_path)
    base["timestamp"] = pd.to_datetime(base["timestamp"], utc=True)
    export = pd.read_csv(export_path)
    config = load_app_config("examples/btc_tv_off_parity.yaml")
    config.strategies["BTC"].kernel_lookback = 20

    result = run_parity_check(
        base,
        export,
        config,
        "BTC",
        column_group="kernel",
        tolerance=0.01,
        skip_rows=26,
        kernel_preflight=True,
    )

    assert result.matched is False
    assert result.first_divergence is not None
    assert result.first_divergence["reason"] == "config_export_mismatch"
    assert result.preflight is not None
    assert result.preflight["status"] == "config_export_mismatch"
    assert result.preflight["best_candidate"]["label"] == "original_lc_defaults"


def test_parity_dump_includes_ann_diagnostics():
    frame = _make_frame(120)
    config = default_app_config()

    dump = generate_parity_dump(frame, config, "BTC")

    for column in [
        "y_train",
        "bar_index",
        "last_bar_index",
        "max_bars_back_index",
        "ann_window_start",
        "ann_window_end",
        "neighbor_index_state",
        "neighbor_label_state",
        "neighbor_label_last",
        "distance_last",
        "neighbor_index_tail_0",
        "neighbor_label_tail_0",
        "neighbor_distance_tail_0",
        "neighbor_index_tail_9",
        "neighbor_label_tail_9",
        "neighbor_distance_tail_9",
        "is_new_buy_signal",
        "is_new_sell_signal",
    ]:
        assert column in dump.columns


def test_tv_export_neighbor_tail_columns_are_normalized():
    export = pd.DataFrame(
        {
            "time": [int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())],
            "barIndex": [123],
            "lastBarIndex": [456],
            "maxBarsBackIndex": [100],
            "isNewBuySignal": [1],
            "isNewSellSignal": [0],
            "neighborIndexTail0": [11],
            "neighborLabelTail0": [1],
            "neighborDistanceTail0": [0.25],
            "neighborIndexTail9": [99],
            "neighborLabelTail9": [-1],
            "neighborDistanceTail9": [1.25],
        }
    )

    normalized = _normalize_tv_export(export)

    assert normalized.loc[0, "bar_index"] == 123
    assert normalized.loc[0, "last_bar_index"] == 456
    assert normalized.loc[0, "max_bars_back_index"] == 100
    assert normalized.loc[0, "is_new_buy_signal"] == 1
    assert normalized.loc[0, "is_new_sell_signal"] == 0
    assert normalized.loc[0, "neighbor_index_tail_0"] == 11
    assert normalized.loc[0, "neighbor_label_tail_0"] == 1
    assert normalized.loc[0, "neighbor_distance_tail_0"] == 0.25
    assert normalized.loc[0, "neighbor_index_tail_9"] == 99
    assert normalized.loc[0, "neighbor_label_tail_9"] == -1
    assert normalized.loc[0, "neighbor_distance_tail_9"] == 1.25


def test_full_diagnostic_pine_export_stays_within_plot_budget():
    root = Path(__file__).resolve().parents[1]
    active_prefixes = (
        "plot(",
        "plotshape(",
        "plotchar(",
        "plotarrow(",
        "plotbar(",
        "plotcandle(",
        "alertcondition(",
        "bgcolor(",
        "barcolor(",
        "fill(",
    )

    for relative_path, expected_limit in [
        ("docs/lc_lorentzian_diagnostic_export.pine", 64),
        ("docs/lc_lorentzian_diagnostic_core_export.pine", 64),
        ("docs/lc_lorentzian_diagnostic_ann_export.pine", 64),
    ]:
        text = (root / relative_path).read_text(encoding="utf-8")
        plot_count = sum(1 for line in text.splitlines() if line.startswith(active_prefixes))
        assert plot_count <= expected_limit
        assert "alertcondition(" not in "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))

    text = (root / "docs/lc_lorentzian_diagnostic_export.pine").read_text(encoding="utf-8")
    for expected in [
        "var neighborIndexes = array.new_int(0)",
        "annAcceptedCount += 1",
        'plot(annAcceptedCount, "annAcceptedCount"',
        'plot(neighborIndexFromEnd(0), "neighborIndexTail0"',
        'plot(neighborLabelFromEnd(9), "neighborLabelTail9"',
        'plot(neighborDistanceFromEnd(9), "neighborDistanceTail9"',
    ]:
        assert expected in text


def test_merge_tv_exports_combines_split_diagnostics_by_timestamp():
    core = pd.DataFrame(
        {
            "time": [int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())],
            "f1": [0.5],
            "prediction": [2],
            "startLongTrade": [1],
        }
    )
    ann = pd.DataFrame(
        {
            "time": [int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())],
            "prediction": [np.nan],
            "neighborIndexTail0": [42],
            "neighborDistanceTail0": [0.75],
        }
    )

    merged = merge_tv_exports(core, ann)

    assert list(merged["timestamp"]) == [pd.Timestamp("2026-01-01", tz="UTC")]
    assert merged.loc[0, "f1"] == 0.5
    assert merged.loc[0, "prediction"] == 2
    assert bool(merged.loc[0, "start_long_trade"])
    assert merged.loc[0, "neighbor_index_tail_0"] == 42
    assert merged.loc[0, "neighbor_distance_tail_0"] == 0.75


def test_merge_tv_exports_drops_conflicting_realtime_overlap_rows():
    stable_time = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
    live_time = int(pd.Timestamp("2026-01-01 00:15", tz="UTC").timestamp())
    core = pd.DataFrame(
        {
            "time": [stable_time, live_time],
            "close": [100.0, 101.0],
            "prediction": [2, 4],
        }
    )
    ann = pd.DataFrame(
        {
            "time": [stable_time, live_time],
            "close": [100.0, 99.0],
            "prediction": [2, 0],
            "neighborIndexTail0": [42, 70],
        }
    )

    merged = merge_tv_exports(core, ann)

    assert merged["timestamp"].tolist() == [pd.Timestamp("2026-01-01", tz="UTC")]
    assert merged.loc[0, "neighbor_index_tail_0"] == 42


def test_lorentzian_ann_skips_na_feature_distances():
    frame = _make_frame(60)
    config = default_app_config()

    dump = generate_parity_dump(frame, config, "BTC")

    first_feature_ready = int(dump[["f1", "f2", "f3", "f4", "f5"]].dropna().index.min())
    assert dump.loc[: first_feature_ready - 1, "current_feature_has_na"].all()
    assert dump.loc[: first_feature_ready - 1, "ann_accepted_count"].sum() == 0


def test_entry_parity_ignores_exits_and_last_bar_by_default():
    frame = _make_frame(120)
    config = default_app_config()
    export = generate_parity_dump(frame, config, "BTC")[["timestamp", "start_long_trade", "start_short_trade", "end_long_trade", "end_short_trade"]].copy()
    export["Buy"] = export["start_long_trade"]
    export["Sell"] = export["start_short_trade"]
    export["StopBuy"] = ~export["end_long_trade"].astype(bool)
    export["StopSell"] = ~export["end_short_trade"].astype(bool)
    export = export[["timestamp", "Buy", "Sell", "StopBuy", "StopSell"]]
    export.loc[len(export) - 1, "Buy"] = not bool(export.loc[len(export) - 1, "Buy"])

    result = run_entry_parity_check(frame, export, config, "BTC", mode="full", run_hypotheses=False)

    assert result.matched is True
    assert result.ignored_exit_mismatch_count > 0


def test_entry_parity_allows_one_bar_tolerance():
    python_events = [{"position": 10, "timestamp": pd.Timestamp("2026-01-01"), "side": "long", "row": pd.Series(dtype=float)}]
    tv_events = [{"position": 11, "timestamp": pd.Timestamp("2026-01-01 00:15"), "side": "long", "row": pd.Series(dtype=float)}]

    exact_matches, exact_missing, exact_extra = _match_entry_events(python_events, tv_events, 0)
    relaxed_matches, relaxed_missing, relaxed_extra = _match_entry_events(python_events, tv_events, 1)

    assert exact_matches == []
    assert len(exact_missing) == 1
    assert len(exact_extra) == 1
    assert len(relaxed_matches) == 1
    assert relaxed_missing == []
    assert relaxed_extra == []


def test_entry_parity_feature_probes_report_single_parameter_changes():
    frame = _make_frame(120)
    config = default_app_config()
    export = generate_parity_dump(frame, config, "BTC")[["timestamp", "start_long_trade", "start_short_trade"]].copy()

    result = run_entry_parity_check(frame, export, config, "BTC", mode="full", run_hypotheses=False, run_feature_probes=True)

    assert result.feature_probe_rankings
    assert all("field" in item and "old_value" in item and "new_value" in item for item in result.feature_probe_rankings)


def test_marker_research_harness_scores_self_generated_markers():
    frame = _make_frame(120)
    config = default_app_config()
    export = generate_parity_dump(frame, config, "BTC")[["timestamp", "open", "high", "low", "close", "start_long_trade", "start_short_trade"]].copy()

    report = run_marker_research(frame, export, config, "BTC", max_candidates=1)

    assert report.rankings
    assert report.best_exact is not None
    assert report.best_exact.exact_matched_entry_count == report.best_exact.tv_entry_count
    assert report.matched_exact is True


def test_signal_stability_threshold_can_suppress_entries():
    frame = _make_frame(160)
    config = default_app_config()
    strategy = config.strategies["BTC"]
    strategy.use_volatility_filter = False
    strategy.use_kernel_filter = False
    strategy.min_prediction_magnitude = 999.0

    dump = LorentzianClassifier().generate(frame, strategy)

    assert not dump["prediction_strength_ok"].any()
    assert not dump["start_long_trade"].any()
    assert not dump["start_short_trade"].any()


def test_entry_cooldown_never_increases_marker_count():
    frame = _make_frame(240)
    config = default_app_config()
    strategy = config.strategies["BTC"]
    strategy.use_volatility_filter = False
    strategy.use_kernel_filter = False
    strategy.min_bars_between_entries = 12

    dump = LorentzianClassifier().generate(frame, strategy)
    raw_count = int(dump["raw_start_long_trade"].sum() + dump["raw_start_short_trade"].sum())
    final_count = int(dump["start_long_trade"].sum() + dump["start_short_trade"].sum())

    assert final_count <= raw_count


def test_intrabar_partial_signal_uses_canonical_classifier():
    frame = _make_frame(80)
    config = default_app_config()
    strategy = config.strategies["BTC"]
    strategy.lc_parity_mode = "tv_marker_tuned"
    strategy.min_prediction_magnitude = 4.0
    strategy.min_signal_persistence_bars = 2
    strategy.min_bars_between_entries = 4
    strategy.block_early_signal_flips = True
    feature_names = [f"f{i + 1}" for i in range(strategy.feature_count)]

    actual = Backtester()._evaluate_partial_signal(frame, pd.DataFrame(), strategy, feature_names)
    expected = LorentzianClassifier().generate(frame, strategy).iloc[-1]

    for column in ["prediction", "signal", "start_long_trade", "start_short_trade", "entry_stability_ok"]:
        assert actual[column] == expected[column]


def test_volatility_filter_runs():
    frame = _make_frame()
    result = filter_volatility(frame, 1, 10, True)
    assert len(result) == len(frame)
