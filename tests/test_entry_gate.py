from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tradingbotsuite.research.entry_gate import (
    ChartBar,
    ChartSignal,
    GOLDILOCKS_GATE_FAMILY,
    GateDecision,
    GateParameters,
    IndicatorCache,
    SimulationSettings,
    candidate_grid,
    fixed_research_exit_settings,
    heavy_candidate_grid_count,
    heavy_candidate_grid,
    optimizer_exit_settings,
    prepare_ohlcv_enriched_bars,
    preferred_research_exit_settings,
    decide_signal,
    load_chart_export,
    run_entry_gate_optimizer,
    run_entry_gate_preflight,
    run_entry_gate_research,
    sampled_heavy_candidate_grid,
    simulate_trades,
)


def _trend_bars(count: int = 140) -> list[ChartBar]:
    bars: list[ChartBar] = []
    price = 100.0
    for index in range(count):
        open_price = price
        close_price = price + 1.0
        bars.append(
            ChartBar(
                time_ms=1_700_000_000_000 + index * 900_000,
                open=open_price,
                high=close_price + 0.5,
                low=open_price - 0.5,
                close=close_price,
            )
        )
        price = close_price
    return bars


def _bars_from_returns(returns: list[float], start: float = 100.0) -> list[ChartBar]:
    bars = [ChartBar(1_700_000_000_000, start, start, start, start)]
    price = start
    for index, log_return in enumerate(returns, start=1):
        open_price = price
        price = price * math.exp(log_return)
        high = max(open_price, price) * 1.001
        low = min(open_price, price) * 0.999
        bars.append(ChartBar(1_700_000_000_000 + index * 900_000, open_price, high, low, price))
    return bars


def _params() -> GateParameters:
    return GateParameters()


def test_lag1_autocorrelation_flags_alternating_and_trending_returns() -> None:
    alternating = IndicatorCache(_bars_from_returns([0.004 if index % 2 == 0 else -0.004 for index in range(120)]))
    trending = IndicatorCache(_bars_from_returns([0.0005 + index * 0.00002 for index in range(120)]))
    constant = IndicatorCache(_bars_from_returns([0.001 for _ in range(120)]))

    assert alternating.lag1_autocorrelation(14)[80] < -0.2
    assert trending.lag1_autocorrelation(14)[80] > 0.1
    assert constant.lag1_autocorrelation(14)[80] is None


def test_hvr_flags_compression_and_expansion() -> None:
    compressed_returns = [0.01 if index % 2 == 0 else -0.01 for index in range(70)] + [0.0005 if index % 2 == 0 else -0.0005 for index in range(10)]
    expanded_returns = [0.0005 if index % 2 == 0 else -0.0005 for index in range(70)] + [0.01 if index % 2 == 0 else -0.01 for index in range(10)]

    compressed = IndicatorCache(_bars_from_returns(compressed_returns)).historical_volatility_ratio(6, 60)[-1]
    expanded = IndicatorCache(_bars_from_returns(expanded_returns)).historical_volatility_ratio(6, 60)[-1]

    assert compressed is not None and compressed < 0.5
    assert expanded is not None and expanded > 0.75


def test_efficiency_ratio_matches_independent_reference() -> None:
    bars = _bars_from_returns([0.002, 0.003, -0.001, 0.004, 0.002, 0.001], start=100.0)
    values = IndicatorCache(bars).efficiency_ratio(4)
    index = 5
    closes = [bar.close for bar in bars]
    net_change = abs(closes[index] - closes[index - 4])
    path = sum(abs(closes[row] - closes[row - 1]) for row in range(index - 4 + 1, index + 1))

    assert values[index] == pytest.approx(net_change / path)


def test_daily_vwap_resets_at_utc_midnight_and_uses_current_bar_only() -> None:
    base = 1_704_067_200_000  # 2024-01-01 00:00:00 UTC
    bars = [
        ChartBar(base, 100.0, 102.0, 99.0, 101.0, 10.0),
        ChartBar(base + 900_000, 101.0, 103.0, 100.0, 102.0, 20.0),
        ChartBar(base + 86_400_000, 110.0, 112.0, 109.0, 111.0, 5.0),
    ]
    vwap = IndicatorCache(bars).daily_vwap()
    first_typical = (102.0 + 99.0 + 101.0) / 3.0
    second_typical = (103.0 + 100.0 + 102.0) / 3.0
    reset_typical = (112.0 + 109.0 + 111.0) / 3.0

    assert vwap[0] == pytest.approx(first_typical)
    assert vwap[1] == pytest.approx(((first_typical * 10.0) + (second_typical * 20.0)) / 30.0)
    assert vwap[2] == pytest.approx(reset_typical)


def test_hvp_uses_no_future_bars() -> None:
    bars = _bars_from_returns([0.001 + (index % 5) * 0.0002 for index in range(80)])
    mutated = list(bars)
    mutated[-1] = ChartBar(mutated[-1].time_ms, mutated[-1].open, mutated[-1].high * 3.0, mutated[-1].low / 3.0, mutated[-1].close * 2.0)
    original = IndicatorCache(bars).historical_volatility_percentile(6, 20)[50]
    changed_future = IndicatorCache(mutated).historical_volatility_percentile(6, 20)[50]

    assert original is not None
    assert original == changed_future


def test_goldilocks_gate_passes_all_enabled_components() -> None:
    bars = []
    price = 100.0
    base = 1_704_067_200_000
    for index in range(80):
        open_price = price
        price *= 1.002
        bars.append(ChartBar(base + index * 900_000, open_price, price * 1.001, open_price * 0.999, price, 100.0 + index))
    signal = ChartSignal(70, 71, bars[70].time_ms, "long", bars[70].low, bars[71].open, 72)
    params = GateParameters(
        gate_family=GOLDILOCKS_GATE_FAMILY,
        er_window=10,
        er_min=0.10,
        hv_window_bars=6,
        hvp_lookback_bars=20,
        hvp_min=0.0,
        hvp_max=100.0,
        vwap_margin_bps=0.0,
    )

    decision = decide_signal(IndicatorCache(bars), signal, params)

    assert decision.accepted
    assert decision.reason == "pass_goldilocks"
    assert decision.components["efficiency_ratio"] is not None
    assert decision.components["daily_vwap"] is not None
    assert decision.components["hvp"] is not None


def test_goldilocks_missing_selected_component_is_reported_separately() -> None:
    bars = _trend_bars(80)
    signal = ChartSignal(70, 71, bars[70].time_ms, "long", bars[70].low, bars[71].open, 72)
    params = GateParameters(
        gate_family=GOLDILOCKS_GATE_FAMILY,
        use_er=False,
        use_vwap=True,
        use_hvp=False,
    )

    decision = decide_signal(IndicatorCache(bars), signal, params)

    assert not decision.accepted
    assert decision.reason == "insufficient_goldilocks_history"


def test_ohlcv_cache_merge_marks_mismatched_bars_unavailable(tmp_path) -> None:
    bars = [
        ChartBar(1_704_067_200_000, 100.0, 101.0, 99.0, 100.5),
        ChartBar(1_704_068_100_000, 100.5, 101.5, 100.0, 101.0),
    ]
    start_ms = bars[0].time_ms
    end_ms = bars[-1].time_ms
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_path = cache_dir / f"BTCUSDT_15m_{start_ms}_{end_ms}.json"
    rows = [
        {"time_ms": bars[0].time_ms, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10.0},
        {"time_ms": bars[1].time_ms, "open": 110.0, "high": 111.0, "low": 109.0, "close": 110.5, "volume": 20.0},
    ]
    cache_path.write_text(json.dumps(rows, separators=(",", ":"), sort_keys=True), encoding="utf-8")

    enriched, coverage = prepare_ohlcv_enriched_bars(
        bars,
        symbol="BTCUSDT",
        gate_family=GOLDILOCKS_GATE_FAMILY,
        ohlcv_cache_policy="cache-only",
        ohlcv_cache_dir=cache_dir,
        required_warmup_bars=0,
    )

    assert coverage is not None
    assert coverage.cache_status == "hit"
    assert coverage.ohlc_mismatch_count == 1
    assert enriched[0].volume == pytest.approx(10.0)
    assert enriched[1].volume is None


def test_ohlcv_cache_accepts_partial_warmup_when_chart_window_is_covered(tmp_path) -> None:
    bars = [
        ChartBar(1_704_067_200_000, 100.0, 101.0, 99.0, 100.5),
        ChartBar(1_704_068_100_000, 100.5, 101.5, 100.0, 101.0),
    ]
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_path = cache_dir / f"BTCUSDT_15m_{bars[0].time_ms}_{bars[-1].time_ms}.json"
    rows = [
        {"time_ms": bars[0].time_ms, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10.0},
        {"time_ms": bars[1].time_ms, "open": 100.5, "high": 101.5, "low": 100.0, "close": 101.0, "volume": 20.0},
    ]
    cache_path.write_text(json.dumps(rows, separators=(",", ":"), sort_keys=True), encoding="utf-8")

    enriched, coverage = prepare_ohlcv_enriched_bars(
        bars,
        symbol="BTCUSDT",
        gate_family=GOLDILOCKS_GATE_FAMILY,
        ohlcv_cache_policy="cache-only",
        ohlcv_cache_dir=cache_dir,
        required_warmup_bars=10,
    )

    assert coverage is not None
    assert coverage.cache_status == "hit"
    assert coverage.requested_start_ms < bars[0].time_ms
    assert coverage.requested_end_ms == bars[-1].time_ms
    assert [bar.volume for bar in enriched] == [10.0, 20.0]


def test_ohlcv_coverage_uses_selected_hvp_windows() -> None:
    bars = []
    base = 1_704_067_200_000
    price = 100.0
    for index in range(40):
        open_price = price
        price *= 1.001 + (0.0001 if index % 2 == 0 else -0.00005)
        bars.append(
            ChartBar(
                base + index * 900_000,
                open_price,
                max(open_price, price) * 1.001,
                min(open_price, price) * 0.999,
                price,
                100.0 + index,
            )
        )

    _enriched, coverage = prepare_ohlcv_enriched_bars(
        bars,
        symbol="BTCUSDT",
        gate_family=GOLDILOCKS_GATE_FAMILY,
        ohlcv_cache_policy="off",
        hvp_coverage_window_bars=3,
        hvp_coverage_lookback_bars=5,
    )

    assert coverage is not None
    assert coverage.cache_status == "disabled"
    assert coverage.hvp_available_count > 0


def test_dsp_cycle_ratio_detects_cycle_more_than_trend() -> None:
    cyclical_returns = [math.sin(index * 2.0 * math.pi / 8.0) * 0.004 for index in range(180)]
    trending_returns = [0.001 + index * 0.000002 for index in range(180)]
    cyclical_cache = IndicatorCache(_bars_from_returns(cyclical_returns))
    trending_cache = IndicatorCache(_bars_from_returns(trending_returns))

    cycle_ratio = cyclical_cache.dsp_cycle_ratio(4, 16)[-1]
    trend_ratio = trending_cache.dsp_cycle_ratio(4, 16)[-1]

    assert cycle_ratio is not None and cycle_ratio > 0.55
    assert trend_ratio is None or trend_ratio < cycle_ratio


def test_gate_no_lookahead_for_future_bar_changes() -> None:
    bars = _bars_from_returns([0.002 if index % 3 else -0.001 for index in range(140)])
    mutated = list(bars)
    mutated[-1] = ChartBar(mutated[-1].time_ms, mutated[-1].open, mutated[-1].high + 10_000, mutated[-1].low - 10_000, mutated[-1].close)
    signal = ChartSignal(90, 91, bars[90].time_ms, "long", bars[90].low, bars[91].open, 92)

    original = decide_signal(IndicatorCache(bars), signal, _params())
    changed_future = decide_signal(IndicatorCache(mutated), signal, _params())

    assert original.gate_score == changed_future.gate_score
    assert original.components == changed_future.components


def test_simulator_uses_worst_case_same_bar_sl_first() -> None:
    bars = [
        ChartBar(1, 100.0, 100.0, 100.0, 100.0),
        ChartBar(2, 100.0, 100.6, 99.4, 100.0),
    ]
    signal = ChartSignal(0, 1, 1, "long", 100.0, 100.0, 2)
    decision = GateDecision(signal, True, 1.0, "pass", False, False, {})
    trades = simulate_trades(
        bars,
        [decision],
        SimulationSettings(entry_slippage_bps=0.0, exit_slippage_bps=0.0, fee_bps=0.0),
    )

    assert len(trades) == 1
    assert trades[0].reason == "sl"
    assert trades[0].exit_price == pytest.approx(99.5)
    assert trades[0].pnl_quote == pytest.approx(-0.005)


def test_simulator_reverse_signal_closes_and_opens_next_side() -> None:
    bars = [
        ChartBar(1, 100.0, 100.1, 99.9, 100.0),
        ChartBar(2, 100.0, 100.1, 99.9, 100.0),
        ChartBar(3, 101.0, 101.1, 100.9, 101.0),
        ChartBar(4, 101.0, 101.1, 100.9, 101.0),
    ]
    long_signal = ChartSignal(0, 1, 1, "long", 100.0, 100.0, 2)
    short_signal = ChartSignal(1, 2, 2, "short", 101.0, 101.0, 3)
    decisions = [
        GateDecision(long_signal, True, 1.0, "pass", False, False, {}),
        GateDecision(short_signal, True, 1.0, "pass", False, False, {}),
    ]
    trades = simulate_trades(
        bars,
        decisions,
        SimulationSettings(take_profit_pct=0.50, stop_loss_pct=0.50, entry_slippage_bps=0.0, exit_slippage_bps=0.0, fee_bps=0.0),
    )

    assert trades[0].reason == "reverse"
    assert trades[0].exit_index == 2
    assert trades[1].direction == "short"


def test_runner_exit_trails_after_activation_to_capture_larger_move() -> None:
    bars = [
        ChartBar(1, 100.0, 100.0, 100.0, 100.0),
        ChartBar(2, 100.0, 100.6, 100.0, 100.5),
        ChartBar(3, 100.5, 102.0, 101.0, 101.8),
        ChartBar(4, 101.8, 101.9, 101.6, 101.7),
    ]
    signal = ChartSignal(0, 1, 1, "long", 100.0, 100.0, 2)
    decision = GateDecision(signal, True, 1.0, "pass", False, False, {})
    trades = simulate_trades(
        bars,
        [decision],
        SimulationSettings(
            exit_mode="runner",
            entry_slippage_bps=0.0,
            exit_slippage_bps=0.0,
            fee_bps=0.0,
        ),
    )

    assert len(trades) == 1
    assert trades[0].reason == "runner_trailing_stop"
    assert trades[0].exit_price == pytest.approx(102.0 * 0.997)
    assert trades[0].pnl_quote > 0.005


def test_candidate_grid_is_bounded_to_expected_count() -> None:
    assert len(candidate_grid()) == 622_080
    assert optimizer_exit_settings("fixed") == fixed_research_exit_settings()
    assert optimizer_exit_settings("runner") == preferred_research_exit_settings()
    assert heavy_candidate_grid_count() == len(candidate_grid())
    assert isinstance(next(heavy_candidate_grid()), GateParameters)


def test_heavy_candidate_grid_can_be_restricted_to_selected_components() -> None:
    unrestricted_count = heavy_candidate_grid_count(("acf", "hvr", "dsp"))
    restricted_count = heavy_candidate_grid_count(("acf", "hvr"))
    assert restricted_count < unrestricted_count
    params = next(heavy_candidate_grid(("acf", "hvr")))
    assert params.use_acf is True
    assert params.use_hvr is True
    assert params.use_dsp is False


def test_sampled_heavy_candidate_grid_spans_parameter_range() -> None:
    sampled = list(sampled_heavy_candidate_grid(("acf", "hvr", "dsp"), max_candidates=10))
    assert len(sampled) == 10
    assert len({candidate.key() for candidate in sampled}) == 10
    assert {candidate.use_acf for candidate in sampled} == {True}
    assert {candidate.use_hvr for candidate in sampled} == {True}
    assert {candidate.use_dsp for candidate in sampled} == {True}
    assert min(candidate.acf_window for candidate in sampled) < max(candidate.acf_window for candidate in sampled)
    assert min(candidate.hvr_long_window for candidate in sampled) < max(candidate.hvr_long_window for candidate in sampled)
    assert min(candidate.dsp_cycle_ratio_threshold for candidate in sampled) < max(candidate.dsp_cycle_ratio_threshold for candidate in sampled)


def test_gate_rejects_when_no_regime_components_are_enabled() -> None:
    bars = _trend_bars()
    signal = ChartSignal(100, 101, bars[100].time_ms, "long", bars[100].low, bars[101].open, 102)
    disabled = GateParameters(
        use_acf=False,
        use_hvr=False,
        use_dsp=False,
    )

    decision = decide_signal(IndicatorCache(bars), signal, disabled)

    assert decision.gate_score is None
    assert not decision.accepted


def test_entry_gate_research_smoke_on_current_export(tmp_path) -> None:
    source_path = Path("BINANCE_BTCUSDT.P, 15 (2).csv")
    if not source_path.exists():
        pytest.skip("local TradingView chart export is not present")

    bars, signals, metadata = load_chart_export(source_path)
    assert len(bars) == 13_925
    assert len(signals) == 1_173
    assert metadata["signal_count"] == 1_173

    result = run_entry_gate_research(
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="kernel_v1_test",
        output_dir=tmp_path,
        max_candidates=128,
    )
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["baseline"]["trade_count"] > 0
    assert metrics["candidate_count"] == 128
    assert Path(metrics["artifacts"]["grid_results"]).exists()


def test_entry_gate_optimizer_keeps_top_five_on_current_export(tmp_path) -> None:
    source_path = Path("BINANCE_BTCUSDT.P, 15 (2).csv")
    if not source_path.exists():
        pytest.skip("local TradingView chart export is not present")

    result = run_entry_gate_optimizer(
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="kernel_v1_optimizer_smoke",
        output_dir=tmp_path,
        max_gate_candidates=16,
        exit_profile="runner",
        top_n=5,
    )
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["evaluated_count"] == 16
    assert metrics["exit_profile"] == "runner"
    assert len(metrics["top5"]) == 5
    assert len({row["param_key"] for row in metrics["top5"]}) == 5
    assert len(metrics["top5_by_return"]) == 5
    assert len(metrics["top5_by_profit_factor"]) == 5
    assert len(metrics["top5_by_winrate"]) == 5
    assert Path(metrics["artifacts"]["top_results"]).exists()
    assert Path(metrics["artifacts"]["top_return_results"]).exists()
    assert Path(metrics["artifacts"]["top_profit_factor_results"]).exists()
    assert Path(metrics["artifacts"]["top_winrate_results"]).exists()


def test_entry_gate_optimizer_output_identity_includes_exit_profile_on_current_export(tmp_path) -> None:
    source_path = Path("BINANCE_BTCUSDT.P, 15 (2).csv")
    if not source_path.exists():
        pytest.skip("local TradingView chart export is not present")

    runner = run_entry_gate_optimizer(
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="same_strategy_name",
        output_dir=tmp_path,
        max_gate_candidates=16,
        exit_profile="runner",
        top_n=5,
    )
    fixed = run_entry_gate_optimizer(
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="same_strategy_name",
        output_dir=tmp_path,
        max_gate_candidates=16,
        exit_profile="fixed",
        top_n=5,
    )
    runner_metrics = json.loads(runner.metrics_path.read_text(encoding="utf-8"))
    fixed_metrics = json.loads(fixed.metrics_path.read_text(encoding="utf-8"))

    assert runner.output_dir != fixed.output_dir
    assert "runner" in runner.output_dir.name
    assert "fixed" in fixed.output_dir.name
    assert runner_metrics["exit_profile"] == "runner"
    assert fixed_metrics["exit_profile"] == "fixed"


def test_entry_gate_optimizer_respects_allowed_components_on_current_export(tmp_path) -> None:
    source_path = Path("BINANCE_BTCUSDT.P, 15 (2).csv")
    if not source_path.exists():
        pytest.skip("local TradingView chart export is not present")

    result = run_entry_gate_optimizer(
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="kernel_v1_optimizer_allowed_components",
        output_dir=tmp_path,
        max_gate_candidates=8,
        exit_profile="fixed",
        top_n=3,
        allowed_components=("acf", "hvr"),
    )
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["exit_profile"] == "fixed"
    assert metrics["allowed_components"] == ["acf", "hvr"]
    for row in metrics["top5"]:
        assert row["use_acf"] is True
        assert row["use_hvr"] is True
        assert row["use_dsp"] is False


def test_entry_gate_optimizer_parallel_matches_serial_count_on_current_export(tmp_path) -> None:
    source_path = Path("BINANCE_BTCUSDT.P, 15 (2).csv")
    if not source_path.exists():
        pytest.skip("local TradingView chart export is not present")

    result = run_entry_gate_optimizer(
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="kernel_v1_optimizer_parallel_smoke",
        output_dir=tmp_path,
        max_gate_candidates=12,
        exit_profile="runner",
        top_n=5,
        workers=2,
    )
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["evaluated_count"] == 12
    assert metrics["workers"] == 2
    assert metrics["effective_workers"] == 2
    assert len(metrics["top5"]) == 5


def test_entry_gate_preflight_tests_components_individually_on_current_export(tmp_path) -> None:
    source_path = Path("BINANCE_BTCUSDT.P, 15 (2).csv")
    if not source_path.exists():
        pytest.skip("local TradingView chart export is not present")

    result = run_entry_gate_preflight(
        path=source_path,
        symbol="BTCUSDT",
        strategy_version="kernel_v1_preflight_smoke",
        output_dir=tmp_path,
        settings=preferred_research_exit_settings(),
    )
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["component_count"] == 3
    assert metrics["candidate_count"] > 3
    assert {row["component"] for row in metrics["best_by_component"]} == {
        "acf",
        "hvr",
        "dsp",
    }
    assert Path(metrics["artifacts"]["preflight_component_results"]).exists()
