from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.core.acceptance import default_rule_acceptance_settings, evaluate_rule_acceptance
from tradingbotsuite.core.engine import TradingEngine
from tradingbotsuite.core.features import RESEARCH_FEATURE_COLUMNS, build_extended_feature_snapshot, numeric_feature_map
from tradingbotsuite.core.models import Bar, DecisionPacket, DecisionAction, RuntimeMode, SignalDirection, SignalIntent
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research.config import load_research_plan
from tradingbotsuite.research.dataset import (
    ResearchDatasetBuilder,
    _funding_paid_or_received,
    _label_from_future_bars,
    classify_label_entry_source,
    label_intervals_overlap,
    purged_train_indices_for_label_intervals,
    simulate_executable_entry_fill,
)
from tradingbotsuite.research.hmm_knn import run_hmm_knn_research
from tradingbotsuite.research.inference import AcceptanceScorer
from tradingbotsuite.research.modeling import calibrate_model, train_base_model
from tradingbotsuite.research.evaluation import replay_eval


def _make_bar(time_ms: int, open_price: Decimal, close_price: Decimal) -> dict:
    high = max(open_price, close_price) + Decimal("20")
    low = min(open_price, close_price) - Decimal("20")
    return {
        "time_ms": time_ms,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close_price,
        "volume": Decimal("100"),
    }


def _trend_bars(count: int = 80) -> list[Bar]:
    bars: list[Bar] = []
    price = Decimal("70000")
    start_ms = 1712649600000
    for index in range(count):
        open_price = price
        close_price = price + Decimal("25")
        bars.append(Bar(**_make_bar(start_ms + (index * 900_000), open_price, close_price)))
        price = close_price
    return bars


def _write_hmm_knn_test_config(tmp_path: Path) -> Path:
    payload = json.loads(Path("configs/v2_btc_hmm_multi_knn_research.json").read_text(encoding="utf-8"))
    payload["version"] = "test-hmm-knn-from-dataset-builder"
    payload["hmm"]["n_states"] = 3
    payload["hmm"]["posterior_threshold"] = 0.45
    payload["hmm"]["entropy_threshold"] = 0.95
    payload["knn"]["primary_k"] = 12
    payload["knn"]["k_values"] = [8, 12]
    payload["knn"]["min_neighbor_count"] = 3
    payload["evaluation"]["min_training_rows"] = 32
    payload["evaluation"]["walk_forward_splits"] = 2
    payload["evaluation"]["purge_embargo_bars"] = 2
    payload["acceptance"]["min_trade_count"] = 1
    config_path = tmp_path / "hmm_knn_config.json"
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


def test_funding_paid_or_received_uses_trade_direction_sign() -> None:
    funding_rate = Decimal("0.0008")
    time_in_trade_hours = Decimal("4")

    long_funding = _funding_paid_or_received(
        direction=SignalDirection.LONG,
        funding_rate=funding_rate,
        time_in_trade_hours=time_in_trade_hours,
    )
    short_funding = _funding_paid_or_received(
        direction=SignalDirection.SHORT,
        funding_rate=funding_rate,
        time_in_trade_hours=time_in_trade_hours,
    )

    assert long_funding == Decimal("-0.00040")
    assert short_funding == Decimal("0.00040")
    assert _funding_paid_or_received(
        direction=SignalDirection.LONG,
        funding_rate=None,
        time_in_trade_hours=time_in_trade_hours,
    ) is None


def test_label_mfe_mae_stop_at_actual_exit_bar() -> None:
    outcome = _label_from_future_bars(
        signal_direction=SignalDirection.LONG,
        entry_price=Decimal("100"),
        atr=Decimal("10"),
        tp_price=Decimal("110"),
        sl_price=Decimal("90"),
        signal_bar_time_ms=0,
        future_bars=[
            Bar(time_ms=900_000, open=Decimal("100"), high=Decimal("111"), low=Decimal("98"), close=Decimal("110"), volume=Decimal("1")),
            Bar(time_ms=1_800_000, open=Decimal("110"), high=Decimal("150"), low=Decimal("50"), close=Decimal("120"), volume=Decimal("1")),
        ],
        vertical_barrier_time_ms=24 * 900_000,
    )

    assert outcome is not None
    assert str(outcome.exit_reason) == "take_profit"
    assert outcome.exit_time_ms == 1_800_000
    assert outcome.time_in_trade == Decimal("0.25")
    assert outcome.time_in_trade_bars == 1
    assert outcome.max_favorable_excursion == Decimal("1.1")
    assert outcome.max_adverse_excursion == Decimal("0.2")


def test_label_entry_source_classification_requires_executable_metadata() -> None:
    signal_close = classify_label_entry_source(
        "signal_bar_close",
        {"entry_latency_ms": 250, "entry_slippage_bps": "5"},
    )
    next_open_without_latency = classify_label_entry_source(
        "next_bar_open_plus_configured_slippage",
        {"entry_slippage_bps": "5"},
    )
    simulated_fill = classify_label_entry_source(
        "simulated_fill",
        {"decision_latency_ms": 120, "entry_slippage_bps": "4"},
    )

    assert signal_close.promotable is False
    assert signal_close.reason == "signal_bar_close_is_diagnostic_not_executable"
    assert next_open_without_latency.promotable is False
    assert next_open_without_latency.missing_required_metadata == ("latency",)
    assert simulated_fill.promotable is True
    assert simulated_fill.reason == "executable_entry_metadata_complete"


def test_simulate_executable_entry_fill_requires_latency_price_time_and_cost_metadata() -> None:
    incomplete = simulate_executable_entry_fill(
        signal_bar_open_time_ms=0,
        signal_bar_close_time_ms=900_000,
        signal_bar_open=Decimal("100"),
        signal_bar_close=Decimal("101"),
        next_bar_open_time_ms=900_000,
        next_bar_open=Decimal("102"),
        decision_latency_ms=50,
        order_placement_latency_ms=None,
        slippage_bps=Decimal("5"),
        direction=SignalDirection.LONG,
    )
    missing_cost = simulate_executable_entry_fill(
        signal_bar_open_time_ms=0,
        signal_bar_close_time_ms=900_000,
        signal_bar_open=Decimal("100"),
        signal_bar_close=Decimal("101"),
        next_bar_open_time_ms=900_000,
        next_bar_open=Decimal("102"),
        decision_latency_ms=50,
        order_placement_latency_ms=75,
        slippage_bps=None,
        direction=SignalDirection.LONG,
    )
    complete = simulate_executable_entry_fill(
        signal_bar_open_time_ms=0,
        signal_bar_close_time_ms=900_000,
        signal_bar_open=Decimal("100"),
        signal_bar_close=Decimal("101"),
        next_bar_open_time_ms=900_000,
        next_bar_open=Decimal("102"),
        decision_latency_ms=50,
        order_placement_latency_ms=75,
        slippage_bps=Decimal("5"),
        direction=SignalDirection.LONG,
    )
    classification = classify_label_entry_source(complete.source, complete.metadata)

    assert incomplete.promotable is False
    assert incomplete.reason == "simulated_fill_metadata_incomplete"
    assert incomplete.missing_required_metadata == ("order_placement_latency_ms",)
    assert incomplete.fill_price is None
    assert missing_cost.promotable is False
    assert missing_cost.missing_required_metadata == ("slippage_bps",)
    assert complete.promotable is True
    assert complete.reason == "simulated_fill_metadata_complete"
    assert complete.fill_time_ms == 900_125
    assert complete.fill_price == Decimal("102") * Decimal("1.0005")
    assert classification.promotable is True
    assert classification.reason == "executable_entry_metadata_complete"


def test_label_interval_overlap_shows_fixed_bar_purge_is_insufficient_for_7d_horizon() -> None:
    bar_ms = 15 * 60 * 1000
    seven_days_ms = 7 * 24 * 60 * 60 * 1000
    train_label_start_ms = 0
    train_label_end_ms = seven_days_ms
    fixed_eight_bar_embargo_start_ms = 8 * bar_ms
    validation_label_end_ms = fixed_eight_bar_embargo_start_ms + (6 * 60 * 60 * 1000)

    assert fixed_eight_bar_embargo_start_ms > 0
    assert label_intervals_overlap(
        train_label_start_ms,
        train_label_end_ms,
        fixed_eight_bar_embargo_start_ms,
        validation_label_end_ms,
    )


def test_purged_train_indices_use_7d_label_interval_overlap_not_fixed_bar_count() -> None:
    bar_ms = 15 * 60 * 1000
    seven_days_ms = 7 * 24 * 60 * 60 * 1000
    train_intervals = [
        (0, seven_days_ms),
        (seven_days_ms + bar_ms, seven_days_ms + (4 * bar_ms)),
        (seven_days_ms + (10 * bar_ms), seven_days_ms + (12 * bar_ms)),
    ]
    test_intervals = [
        (8 * bar_ms, 8 * bar_ms + (6 * 60 * 60 * 1000)),
        (seven_days_ms + (4 * bar_ms), seven_days_ms + (5 * bar_ms)),
    ]

    assert purged_train_indices_for_label_intervals(train_intervals, test_intervals, embargo_ms=0) == [0]
    assert purged_train_indices_for_label_intervals(train_intervals, test_intervals, embargo_ms=bar_ms) == [0, 1]


@pytest.mark.asyncio
async def test_extended_feature_snapshot_tracks_missingness(sample_bars) -> None:
    snapshot = build_extended_feature_snapshot(
        signal_direction=SignalDirection.LONG,
        signal_time_ms=sample_bars[-1].time_ms,
        latest_bar=sample_bars[-1],
        bars=sample_bars[-40:],
        atr=Decimal("100"),
        atr_length=14,
        hurst=None,
        microstructure=None,
        basis_snapshot=None,
        funding_context=None,
        open_interest_context=None,
        premium_context=None,
        primary_window_seconds=20,
        volatility_config=type("cfg", (), {
            "realized_vol_window_bars": 20,
            "atr_percentile_window_bars": 20,
            "volatility_shock_window_bars": 20,
            "volatility_shock_zscore_threshold": 2.0,
        })(),
    )
    numeric = numeric_feature_map(snapshot)
    assert snapshot["missing"]["funding_rate"] is True
    assert snapshot["missing"]["open_interest"] is True
    assert numeric["missing_funding_rate"] == 1.0
    assert numeric["missing_open_interest"] == 1.0


def test_extended_feature_snapshot_includes_trend_and_rule_acceptance_fields() -> None:
    bars = _trend_bars()
    snapshot = build_extended_feature_snapshot(
        signal_direction=SignalDirection.LONG,
        signal_time_ms=bars[-1].time_ms,
        latest_bar=bars[-1],
        bars=bars,
        atr=Decimal("100"),
        atr_length=14,
        hurst=Decimal("0.6"),
        microstructure={
            "spread_bps": "3.0",
            "top_of_book_imbalance": "0.15",
            "trade_flow_available": True,
            "top_of_book_available": True,
            "windows": {
                "20": {
                    "signed_ratio": "0.10",
                    "sqrt_signed_ratio": "0.08",
                    "trade_sign_acf_lag1": "-0.25",
                    "flow_price_alignment_bps": "1.5",
                    "impact_efficiency_bps_per_sqrt_notional": "0.003",
                }
            },
        },
        basis_snapshot={"basis_bps": "2.0"},
        funding_context={"funding_rate": "-0.00005", "funding_rate_change": "0.00001", "time_to_next_funding_ms": 7_200_000},
        open_interest_context=None,
        premium_context={"basis_rate": "0.0001", "basis": "7", "premium_close": "0.0001"},
        primary_window_seconds=20,
        volatility_config=type(
            "cfg",
            (),
            {
                "realized_vol_window_bars": 20,
                "atr_percentile_window_bars": 20,
                "volatility_shock_window_bars": 20,
                "volatility_shock_zscore_threshold": 2.0,
            },
        )(),
    )
    rule = evaluate_rule_acceptance(snapshot, default_rule_acceptance_settings())

    assert snapshot["efficiency_ratio"] is not None
    assert snapshot["choppiness"] is not None
    assert snapshot["directional_slope_atr"] is not None
    assert snapshot["directional_di_spread"] is not None
    assert snapshot["range_width"] is not None
    assert snapshot["spread_bps"] == "3.0"
    assert snapshot["primary_sqrt_signed_imbalance_ratio"] == "0.08"
    assert snapshot["primary_trade_sign_acf_lag1"] == "-0.25"
    assert snapshot["primary_flow_price_alignment_bps"] == "1.5"
    assert snapshot["primary_impact_efficiency_bps_per_sqrt_notional"] == "0.003"
    assert numeric_feature_map(snapshot)["primary_sqrt_signed_imbalance_ratio"] == 0.08
    assert rule["status"] == "scored"
    assert rule["core_pass"] is True
    assert rule["accept_candidate"] is True


def test_rule_acceptance_rejects_basis_dislocation_and_wide_spread() -> None:
    bars = _trend_bars()
    snapshot = build_extended_feature_snapshot(
        signal_direction=SignalDirection.LONG,
        signal_time_ms=bars[-1].time_ms,
        latest_bar=bars[-1],
        bars=bars,
        atr=Decimal("100"),
        atr_length=14,
        hurst=Decimal("0.6"),
        microstructure={
            "spread_bps": "20.0",
            "top_of_book_imbalance": "0.15",
            "trade_flow_available": True,
            "top_of_book_available": True,
            "windows": {"20": {"signed_ratio": "0.10"}},
        },
        basis_snapshot={"basis_bps": "30.0"},
        funding_context={"funding_rate": "0.0002", "funding_rate_change": "0.00001", "time_to_next_funding_ms": 600_000},
        open_interest_context=None,
        premium_context={"basis_rate": "0.0004", "basis": "25", "premium_close": "0.0004"},
        primary_window_seconds=20,
        volatility_config=type(
            "cfg",
            (),
            {
                "realized_vol_window_bars": 20,
                "atr_percentile_window_bars": 20,
                "volatility_shock_window_bars": 20,
                "volatility_shock_zscore_threshold": 2.0,
            },
        )(),
    )
    rule = evaluate_rule_acceptance(snapshot, default_rule_acceptance_settings())

    assert rule["perp_pass"] is False
    assert rule["liquidity_hard_fail"] is True
    assert rule["accept_candidate"] is False
    assert "basis_dislocation" in rule["reasons"]
    assert "wide_spread" in rule["reasons"]


@pytest.mark.asyncio
async def test_research_dataset_builder_writes_parquet_and_manifest(app_config, tmp_path) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "research.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32, stale_bar_after_ms=10_000_000_000),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=ResearchConfig(output_dir=tmp_path / "research", config_path=Path("configs/v2_btc_research.json")),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    bars = []
    price = Decimal("70000")
    start_ms = 1712649600000
    for index in range(80):
        open_price = price
        close_price = price + Decimal("15") if index < 60 else price + Decimal("80")
        bar_payload = _make_bar(start_ms + (index * 900_000), open_price, close_price)
        from tradingbotsuite.core.models import Bar

        bars.append(Bar(**bar_payload))
        price = close_price

    for offset, time_index in enumerate((59, 60), start=1):
        signal = SignalIntent(
            signal_id=f"research-{offset}",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            tv_bar_time_ms=bars[time_index].time_ms,
            received_time_ms=bars[time_index].time_ms + 900_000,
            raw_payload={},
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
                    "microstructure": {"windows": {"20": {"signed_ratio": "0.2"}}, "top_of_book_imbalance": "0.15"},
                    "basis": {"basis_bps": "2.5"},
                },
            ),
            signal.received_time_ms,
        )

    class FakeResearchClient:
        def __init__(self) -> None:
            self.range_calls = 0
            self.context_calls: list[tuple[str, int]] = []

        async def fetch_historical_closed_bar_range(self, symbol: str, *, start_time_ms: int, end_time_ms: int, interval: str = "15m"):
            self.range_calls += 1
            return [bar for bar in bars if start_time_ms <= bar.time_ms <= end_time_ms]

        async def fetch_historical_closed_bars(self, symbol: str, *, limit: int, end_time_ms: int | None = None, interval: str = "15m"):
            eligible = [bar for bar in bars if end_time_ms is None or (bar.time_ms + 899_999) <= end_time_ms]
            return eligible[-limit:]

        async def fetch_future_closed_bars(self, symbol: str, *, start_time_ms: int, limit: int, interval: str = "15m"):
            eligible = [bar for bar in bars if bar.time_ms >= start_time_ms]
            return eligible[:limit]

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            self.context_calls.append(("funding", as_of_ms))
            return {
                "funding_rate": "0.0001",
                "funding_rate_change": "0.00002",
                "time_to_next_funding_ms": 1_800_000,
                "source": "fundingRate",
            }

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            self.context_calls.append(("open_interest", as_of_ms))
            return {
                "open_interest": "1000",
                "open_interest_change": "50",
                "open_interest_change_pct": "0.05",
                "open_interest_value": "70500000",
                "current_open_interest": "999999",
                "source": "openInterestHist",
            }

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            self.context_calls.append(("premium", as_of_ms))
            return {
                "mark_price": "70521",
                "index_price": "70500",
                "basis_rate": "0.0003",
                "basis": "21",
                "premium_close": "0.0002",
                "source": "premiumIndexKlines",
            }

    fake_client = FakeResearchClient()
    builder = ResearchDatasetBuilder(config=config, plan=plan, store=store, candle_client=fake_client)
    result = await builder.build()
    frame = pd.read_parquet(result.dataset_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.row_count == 2
    assert "source" in frame.columns
    assert "label_version" in frame.columns
    assert "funding_rate" in frame.columns
    assert "raw_funding_rate" in frame.columns
    assert "signal_bar_open" in frame.columns
    assert "signal_bar_close_time_ms" in frame.columns
    assert "rule_acceptance_total_score" in frame.columns
    assert "rule_acceptance_accept_candidate" in frame.columns
    assert frame.iloc[0]["label_accept"] == 1
    assert (frame["signal_bar_open_time_ms"] == frame["tv_bar_time_ms"]).all()
    assert (frame["historical_feature_end_time_ms"] <= frame["tv_bar_time_ms"]).all()
    assert (frame["label_future_start_time_ms"] > frame["tv_bar_time_ms"]).all()
    assert (frame["label_interval_start_ms"] == frame["signal_bar_close_time_ms"]).all()
    assert (frame["label_interval_end_ms"] == frame["label_exit_time_ms"]).all()
    assert frame["entry_price_source"].tolist() == ["signal_bar_close", "signal_bar_close"]
    assert frame["entry_price_source_promotable"].tolist() == [False, False]
    assert set(frame["entry_price_source_reason"]) == {"signal_bar_close_is_diagnostic_not_executable"}
    assert frame.iloc[0]["raw_open_interest"] == 1000.0
    assert frame.iloc[0]["open_interest"] == 1000.0
    assert frame.iloc[0]["raw_mark_price"] == 70521.0
    assert manifest["missing_feature_rates"]["missing_funding_rate"] == 0.0
    assert manifest["missing_feature_rates"]["missing_open_interest"] == 0.0
    assert manifest["missing_feature_rates"]["missing_premium_close"] == 0.0
    assert manifest["row_count"] == 2
    assert manifest["research_only"] is True
    assert manifest["asset_scope"] == ["BTCUSDT"]
    assert manifest["symbol"] == "BTCUSDT"
    assert manifest["feature_version"] == "v2-btc-acceptance-2"
    assert manifest["label_version"] == "triple_barrier_live_parity_v1"
    assert manifest["label_interval_fields"] == ["label_interval_start_ms", "label_interval_end_ms"]
    assert manifest["entry_price_source_summary"]["source_counts"] == {"signal_bar_close": 2}
    assert manifest["entry_price_source_summary"]["non_promotable_label_row_count"] == 2
    assert manifest["entry_price_source_summary"]["all_label_entry_sources_promotable"] is False
    assert manifest["source_counts"] == {"tradingview": 2}
    assert manifest["source_mode_counts"] == {"tradingview": 2}
    assert manifest["class_balance"]["label_accept_1"] == 2
    assert manifest["planned_split_summary"]["walk_forward_splits"] == plan.evaluation.walk_forward_splits
    assert "missing_feature_rates" in manifest
    assert manifest["exchange_context_summary"]["funding_context"]["source_counts"] == {"fundingRate": 2}
    assert manifest["exchange_context_summary"]["open_interest_context"]["source_counts"] == {"openInterestHist": 2}
    assert manifest["exchange_context_summary"]["premium_context"]["source_counts"] == {"premiumIndexKlines": 2}
    assert manifest["raw_context_available_counts"]["raw_funding_rate"] == 2
    assert manifest["raw_context_available_counts"]["raw_open_interest"] == 2
    assert manifest["raw_context_available_counts"]["raw_premium_close"] == 2
    assert manifest["raw_context_available_counts"]["decision_context_present"] == 2
    assert sorted(fake_client.context_calls) == sorted(
        [
            ("funding", bars[59].time_ms),
            ("funding", bars[60].time_ms),
            ("open_interest", bars[59].time_ms),
            ("open_interest", bars[60].time_ms),
            ("premium", bars[59].time_ms),
            ("premium", bars[60].time_ms),
        ]
    )
    assert fake_client.range_calls == 1


@pytest.mark.asyncio
async def test_research_dataset_builder_uses_promotable_simulated_fill_metadata(app_config, tmp_path) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "simulated-fill.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32, stale_bar_after_ms=10_000_000_000),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=ResearchConfig(output_dir=tmp_path / "research", config_path=Path("configs/v2_btc_research.json")),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    bars = []
    price = Decimal("70000")
    start_ms = 1712649600000
    for index in range(82):
        open_price = price
        close_price = price + Decimal("15") if index < 60 else price + Decimal("80")
        bars.append(Bar(**_make_bar(start_ms + (index * 900_000), open_price, close_price)))
        price = close_price

    payloads = [
        {
            "next_bar_time_ms": bars[60].time_ms,
            "next_bar_open": str(bars[60].open),
            "decision_latency_ms": 50,
            "order_placement_latency_ms": 75,
            "entry_slippage_bps": "5",
        },
        {
            "next_bar_time_ms": bars[61].time_ms,
            "next_bar_open": str(bars[61].open),
            "entry_slippage_bps": "5",
        },
    ]
    for offset, (time_index, raw_payload) in enumerate(zip((59, 60), payloads, strict=True), start=1):
        signal = SignalIntent(
            signal_id=f"sim-fill-{offset}",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            tv_bar_time_ms=bars[time_index].time_ms,
            received_time_ms=bars[time_index].time_ms + 900_000,
            raw_payload=raw_payload,
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
                    "microstructure": {"windows": {"20": {"signed_ratio": "0.2"}}, "top_of_book_imbalance": "0.15"},
                    "basis": {"basis_bps": "2.5"},
                },
            ),
            signal.received_time_ms,
        )

    class FakeResearchClient:
        async def fetch_historical_closed_bar_range(self, symbol: str, *, start_time_ms: int, end_time_ms: int, interval: str = "15m"):
            return [bar for bar in bars if start_time_ms <= bar.time_ms <= end_time_ms]

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            return {"funding_rate": "0.0001", "funding_rate_change": "0.00002", "time_to_next_funding_ms": 1_800_000}

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            return {"open_interest": "1000", "open_interest_change": "50", "open_interest_change_pct": "0.05", "open_interest_value": "70500000"}

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            return {"mark_price": "70521", "index_price": "70500", "basis_rate": "0.0003", "basis": "21", "premium_close": "0.0002"}

    result = await ResearchDatasetBuilder(config=config, plan=plan, store=store, candle_client=FakeResearchClient()).build()
    frame = pd.read_parquet(result.dataset_path).sort_values("signal_id").reset_index(drop=True)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    simulated = frame.iloc[0]
    diagnostic = frame.iloc[1]
    expected_fill_price = bars[60].open * Decimal("1.0005")

    assert simulated["signal_id"] == "sim-fill-1"
    assert simulated["entry_price_source"] == "simulated_fill"
    assert bool(simulated["entry_price_source_promotable"]) is True
    assert simulated["entry_price_source_reason"] == "executable_entry_metadata_complete"
    assert simulated["entry_price"] == pytest.approx(float(expected_fill_price))
    assert simulated["label_interval_start_ms"] == simulated["signal_bar_close_time_ms"] + 125

    assert diagnostic["signal_id"] == "sim-fill-2"
    assert diagnostic["entry_price_source"] == "signal_bar_close"
    assert bool(diagnostic["entry_price_source_promotable"]) is False
    assert diagnostic["entry_price_source_reason"] == "signal_bar_close_is_diagnostic_not_executable"
    assert diagnostic["entry_price"] == diagnostic["signal_bar_close"]
    assert diagnostic["label_interval_start_ms"] == diagnostic["signal_bar_close_time_ms"]

    assert manifest["entry_price_source_summary"]["source_counts"] == {"signal_bar_close": 1, "simulated_fill": 1}
    assert manifest["entry_price_source_summary"]["classification_counts"] == {"executable_style": 1, "signal_bar_close": 1}
    assert manifest["entry_price_source_summary"]["promotable_label_row_count"] == 1
    assert manifest["entry_price_source_summary"]["non_promotable_label_row_count"] == 1


@pytest.mark.asyncio
async def test_research_dataset_builder_preserves_missing_exchange_context(app_config, tmp_path) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "missing.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32, stale_bar_after_ms=10_000_000_000),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=ResearchConfig(output_dir=tmp_path / "research", config_path=Path("configs/v2_btc_research.json")),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    bars = []
    price = Decimal("70000")
    start_ms = 1712649600000
    for index in range(75):
        open_price = price
        close_price = price + Decimal("15") if index < 60 else price + Decimal("80")
        bars.append(Bar(**_make_bar(start_ms + (index * 900_000), open_price, close_price)))
        price = close_price

    signal = SignalIntent(
        signal_id="missing-context-1",
        symbol="BTCUSDT",
        direction=SignalDirection.LONG,
        tv_bar_time_ms=bars[59].time_ms,
        received_time_ms=bars[59].time_ms + 900_000,
        raw_payload={},
    )
    await store.reserve_signal(signal)
    await store.update_signal_decision(signal, accepted=True, rejection_reason=None)
    await store.save_decision_packet(
        DecisionPacket(
            signal=signal,
            mode=RuntimeMode.PAPER,
            action=DecisionAction.ACCEPT,
            accepted=True,
            feature_snapshot={},
        ),
        signal.received_time_ms,
    )

    class MissingContextClient:
        async def fetch_historical_closed_bar_range(self, symbol: str, *, start_time_ms: int, end_time_ms: int, interval: str = "15m"):
            return [bar for bar in bars if start_time_ms <= bar.time_ms <= end_time_ms]

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            return {"funding_rate": None, "funding_rate_change": None, "source": "fundingRate", "source_error": "rate_limit"}

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            return {"open_interest": None, "open_interest_change_pct": None, "source": "openInterestHist", "backoff_until_ms": as_of_ms + 1000}

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            return {"basis_rate": None, "basis": None, "premium_close": None, "source": "premiumIndexKlines"}

    result = await ResearchDatasetBuilder(config=config, plan=plan, store=store, candle_client=MissingContextClient()).build()
    frame = pd.read_parquet(result.dataset_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    row = frame.iloc[0]
    assert pd.isna(row["raw_funding_rate"])
    assert pd.isna(row["raw_funding_rate_change"])
    assert pd.isna(row["raw_time_to_next_funding_ms"])
    assert row["funding_rate"] == 0.0
    assert row["funding_rate_change"] == 0.0
    assert row["time_to_next_funding_hours"] == 0.0
    assert row["missing_funding_rate"] == 1.0
    assert row["missing_funding_rate_change"] == 1.0
    assert row["missing_time_to_next_funding_hours"] == 1.0
    assert pd.isna(row["raw_open_interest"])
    assert pd.isna(row["raw_open_interest_change"])
    assert pd.isna(row["raw_open_interest_change_pct"])
    assert pd.isna(row["raw_open_interest_value"])
    assert row["open_interest"] == 0.0
    assert row["open_interest_change"] == 0.0
    assert row["open_interest_change_pct"] == 0.0
    assert row["open_interest_value"] == 0.0
    assert row["missing_open_interest"] == 1.0
    assert row["missing_open_interest_change"] == 1.0
    assert row["missing_open_interest_change_pct"] == 1.0
    assert row["missing_open_interest_value"] == 1.0
    assert pd.isna(row["raw_premium_basis_rate"])
    assert pd.isna(row["raw_premium_basis_abs"])
    assert pd.isna(row["raw_premium_close"])
    assert row["premium_basis_rate"] == 0.0
    assert row["premium_basis_abs"] == 0.0
    assert row["premium_close"] == 0.0
    assert row["missing_premium_basis_rate"] == 1.0
    assert row["missing_premium_basis_abs"] == 1.0
    assert row["missing_premium_close"] == 1.0
    assert manifest["missing_feature_rates"]["missing_funding_rate"] == 1.0
    assert manifest["missing_feature_rates"]["missing_open_interest"] == 1.0
    assert manifest["missing_feature_rates"]["missing_premium_close"] == 1.0
    assert manifest["raw_context_available_counts"]["raw_funding_rate"] == 0
    assert manifest["raw_context_available_counts"]["raw_open_interest"] == 0
    assert manifest["raw_context_available_counts"]["raw_premium_close"] == 0
    assert manifest["exchange_context_summary"]["funding_context"]["field_available_counts"]["funding_rate"] == 0
    assert manifest["exchange_context_summary"]["open_interest_context"]["field_available_counts"]["open_interest"] == 0
    assert manifest["exchange_context_summary"]["premium_context"]["field_available_counts"]["premium_close"] == 0
    assert manifest["exchange_context_summary"]["funding_context"]["rows_with_source_error"] == 1
    assert manifest["exchange_context_summary"]["open_interest_context"]["rows_with_backoff"] == 1


def test_research_model_pipeline_and_shadow_scoring(app_config, tmp_path, sample_bars) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    dataset_path = tmp_path / "dataset.parquet"
    rows = []
    for index in range(120):
        label = 1 if index % 2 == 0 else 0
        row = {column: 0.0 for column in RESEARCH_FEATURE_COLUMNS}
        row.update(
            {
                "signal_id": f"sig-{index}",
                "symbol": "BTCUSDT",
                "direction": "long" if label else "short",
                "tv_bar_time_ms": 1712649600000 + (index * 900_000),
                "received_time_ms": 1712649600000 + (index * 900_000) + 1000,
                "feature_version": "v2-btc-acceptance-2",
                "model_version": "observe_only",
                "calibration_version": "none",
                "v1_baseline_accept": index % 3 == 0,
                "v1_rejection_reason": None,
                "entry_price": 70000.0,
                "tp_price": 70100.0,
                "sl_price": 69900.0,
                "label_exit_reason": "take_profit" if label else "stop_loss",
                "label_accept": label,
                "label_pnl_multiple": 1.5 if label else -1.0,
                "basis_bps": 2.0,
                "primary_signed_imbalance_ratio": 0.45 if label else -0.45,
                "top_of_book_imbalance": 0.2 if label else -0.2,
                "funding_rate": 0.0001 if label else -0.00005,
                "open_interest_change_pct": 0.05 if label else -0.03,
                "premium_basis_rate": 0.0003 if label else -0.0002,
                "realized_volatility": 0.01 + (0.002 * label),
                "atr_percentile": 0.7 if label else 0.3,
                "session_us": 1.0 if label else 0.0,
            }
        )
        rows.append(row)
    pd.DataFrame(rows).to_parquet(dataset_path, index=False)

    output_dir = tmp_path / "artifacts"
    train_artifacts = train_base_model(dataset_path, plan, output_dir)
    artifact_manifest_path = calibrate_model(train_artifacts.manifest_path, plan)
    metrics_path = replay_eval(artifact_manifest_path, plan)
    scorer = AcceptanceScorer.from_manifest_path(artifact_manifest_path)
    score = scorer.score_snapshot(
        {
            "direction": "long",
            "atr": "120",
            "hurst": "0.6",
            "primary_signed_imbalance_ratio": "0.35",
            "top_of_book_imbalance": "0.22",
            "queue_imbalance_l1": "0.10",
            "queue_imbalance_l5": "0.08",
            "queue_imbalance_l10": "0.06",
            "basis": {"basis_bps": "2.0"},
            "funding_context": {"funding_rate": "0.0001", "funding_rate_change": "0.00001", "time_to_next_funding_ms": 1000},
            "open_interest_context": {"open_interest": "1000", "open_interest_change": "50", "open_interest_change_pct": "0.05", "open_interest_value": "70000000"},
            "premium_context": {"basis_rate": "0.0003", "basis": "21", "premium_close": "0.0002"},
            "realized_volatility": "0.012",
            "atr_percentile": "0.72",
            "volatility_shock_zscore": "1.5",
            "volatility_shock_flag": False,
            "session_hour_sin": 0.1,
            "session_hour_cos": 0.9,
            "session_weekday": 2,
            "session_asia": 0,
            "session_europe": 0,
            "session_us": 1,
            "missing": {},
        }
    )

    assert artifact_manifest_path.exists()
    assert metrics_path.exists()
    assert score["accept_probability"] >= 0.0
    assert score["model_version"].startswith(plan.version)
    assert score["artifact_manifest_version"] == "v2-artifact-manifest-1"

    config = AppConfig(
        runtime_mode=RuntimeMode.SHADOW,
        db_path=tmp_path / "shadow.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=ResearchConfig(
            output_dir=output_dir,
            config_path=Path("configs/v2_btc_research.json"),
            artifact_manifest_path=artifact_manifest_path,
        ),
    )
    store = SQLiteStore(config.db_path)

    class FakeCandles:
        async def start_market_streams(self, symbols: list[str]):
            return None

        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            extended = sample_bars * 2
            return extended[-limit:]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {
                "healthy": True,
                "mid_price": "70580",
                "top_of_book_imbalance": "0.25",
                "queue_imbalance_l1": "0.10",
                "queue_imbalance_l5": "0.08",
                "queue_imbalance_l10": "0.06",
                "windows": {"20": {"signed_ratio": "0.2"}},
            }

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return (sample_bars * 2)[-1]

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            return {"funding_rate": "0.0001", "funding_rate_change": "0.00002", "time_to_next_funding_ms": 1_800_000}

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            return {
                "open_interest": "1000",
                "open_interest_change": "50",
                "open_interest_change_pct": "0.05",
                "open_interest_value": "70500000",
            }

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            return {"basis_rate": "0.0003", "basis": "21", "premium_close": "0.0002"}

    class ShadowAdapter:
        mode = RuntimeMode.SHADOW

        async def start_user_streams(self):
            return None

        def get_stream_status(self):
            return {"enabled": False, "started": False}

        async def execute(self, intents):
            return []

        async def shutdown(self):
            return None

    engine = TradingEngine(config, store, FakeCandles(), ShadowAdapter(), scorer=scorer, clock=lambda: 1712665800000)

    async def _run() -> None:
        await engine.initialize()
        packet, _, _ = await engine.handle_signal(
            SignalIntent(
                signal_id="shadow-score-1",
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                tv_bar_time_ms=1712662200000,
                received_time_ms=1712665800000,
                raw_payload={},
            )
        )
        assert "v2_acceptance" in packet.feature_snapshot
        assert packet.model_version.startswith(plan.version)
        assert packet.feature_snapshot["v2_acceptance"]["status"] == "scored"

    import asyncio

    asyncio.run(_run())


def test_train_model_rejects_manual_signal_sources(tmp_path) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    dataset_path = tmp_path / "dirty_dataset.parquet"
    pd.DataFrame(
        [
            {
                "signal_id": "manual-test-1",
                "source": "manual-cli",
                "symbol": "BTCUSDT",
                "tv_bar_time_ms": 1712649600000,
                "label_accept": 1,
            }
        ]
    ).to_parquet(dataset_path, index=False)

    with pytest.raises(ValueError, match="non-TrainingView research sources"):
        train_base_model(dataset_path, plan, tmp_path / "artifacts")


@pytest.mark.asyncio
async def test_research_dataset_builder_is_deterministic(app_config, tmp_path) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "deterministic.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32, stale_bar_after_ms=10_000_000_000),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=ResearchConfig(output_dir=tmp_path / "research", config_path=Path("configs/v2_btc_research.json")),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    bars = []
    price = Decimal("70000")
    start_ms = 1712649600000
    for index in range(90):
        open_price = price
        close_price = price + Decimal("20") if index < 70 else price + Decimal("65")
        from tradingbotsuite.core.models import Bar

        bars.append(Bar(**_make_bar(start_ms + (index * 900_000), open_price, close_price)))
        price = close_price

    for offset, time_index in enumerate((60, 61, 62), start=1):
        signal = SignalIntent(
            signal_id=f"det-{offset}",
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            tv_bar_time_ms=bars[time_index].time_ms,
            received_time_ms=bars[time_index].time_ms + 900_000,
            raw_payload={"source": "fixture"},
        )
        await store.reserve_signal(signal)
        await store.update_signal_decision(signal, accepted=True, rejection_reason=None)
        await store.save_decision_packet(
            DecisionPacket(
                signal=signal,
                mode=RuntimeMode.PAPER,
                action=DecisionAction.ACCEPT,
                accepted=True,
                feature_snapshot={"microstructure": {"windows": {"20": {"signed_ratio": "0.2"}}, "top_of_book_imbalance": "0.15"}},
            ),
            signal.received_time_ms,
        )

    class FakeResearchClient:
        async def fetch_historical_closed_bar_range(self, symbol: str, *, start_time_ms: int, end_time_ms: int, interval: str = "15m"):
            return [bar for bar in bars if start_time_ms <= bar.time_ms <= end_time_ms]

        async def fetch_historical_closed_bars(self, symbol: str, *, limit: int, end_time_ms: int | None = None, interval: str = "15m"):
            eligible = [bar for bar in bars if end_time_ms is None or (bar.time_ms + 899_999) <= end_time_ms]
            return eligible[-limit:]

        async def fetch_future_closed_bars(self, symbol: str, *, start_time_ms: int, limit: int, interval: str = "15m"):
            eligible = [bar for bar in bars if bar.time_ms >= start_time_ms]
            return eligible[:limit]

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            return {"funding_rate": "0.0001", "funding_rate_change": "0.00002", "time_to_next_funding_ms": 1_800_000}

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            return {"open_interest": "1000", "open_interest_change": "50", "open_interest_change_pct": "0.05", "open_interest_value": "70500000"}

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            return {"basis_rate": "0.0003", "basis": "21", "premium_close": "0.0002"}

    builder = ResearchDatasetBuilder(config=config, plan=plan, store=store, candle_client=FakeResearchClient())
    first = await builder.build()
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    second = await builder.build()
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))

    assert first_manifest["dataset_sha256"] == second_manifest["dataset_sha256"]
    assert first_manifest["source_mode_counts"] == second_manifest["source_mode_counts"]
    assert first_manifest["planned_split_summary"] == second_manifest["planned_split_summary"]


@pytest.mark.asyncio
async def test_hmm_knn_research_consumes_dataset_builder_output(app_config, tmp_path) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    config = AppConfig(
        runtime_mode=RuntimeMode.PAPER,
        db_path=tmp_path / "hmm_dataset.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32, stale_bar_after_ms=10_000_000_000),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=ResearchConfig(output_dir=tmp_path / "research", config_path=Path("configs/v2_btc_research.json")),
    )
    store = SQLiteStore(config.db_path)
    await store.initialize()

    bars = []
    price = Decimal("70000")
    start_ms = 1712649600000
    for index in range(125):
        open_price = price
        close_price = price + Decimal("55")
        bars.append(Bar(**_make_bar(start_ms + (index * 900_000), open_price, close_price)))
        price = close_price

    for offset, time_index in enumerate(range(50, 96), start=1):
        direction = SignalDirection.LONG if offset % 2 else SignalDirection.SHORT
        signal = SignalIntent(
            signal_id=f"hmm-data-{offset}",
            symbol="BTCUSDT",
            direction=direction,
            tv_bar_time_ms=bars[time_index].time_ms,
            received_time_ms=bars[time_index].time_ms + 900_000,
            raw_payload={"source_mode": "chart_export", "strategy_version": "fixture-v1"},
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

    class HmmDatasetClient:
        async def fetch_historical_closed_bar_range(self, symbol: str, *, start_time_ms: int, end_time_ms: int, interval: str = "15m"):
            return [bar for bar in bars if start_time_ms <= bar.time_ms <= end_time_ms]

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            return {"funding_rate": "0.00008", "funding_rate_change": "0.00001", "time_to_next_funding_ms": 1_800_000, "source": "fundingRate"}

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            return {"open_interest": "1000", "open_interest_change": "20", "open_interest_change_pct": "0.02", "open_interest_value": "70500000", "source": "openInterestHist"}

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            return {"mark_price": "70521", "index_price": "70500", "basis_rate": "0.0003", "basis": "21", "premium_close": "0.0002", "source": "premiumIndexKlines"}

    dataset_result = await ResearchDatasetBuilder(config=config, plan=plan, store=store, candle_client=HmmDatasetClient()).build()
    frame = pd.read_parquet(dataset_result.dataset_path)
    assert frame["label_accept"].nunique() == 2
    required_label_fields = [
        "gross_return",
        "fees_bps",
        "slippage_bps",
        "funding_paid_or_received",
        "time_in_trade",
        "max_adverse_excursion",
        "max_favorable_excursion",
        "barrier_hit_type",
        "label_exit_time_ms",
        "realized_net_return_after_costs",
    ]
    dataset_required_label_fields = [field for field in required_label_fields if field != "realized_net_return_after_costs"]
    assert set(dataset_required_label_fields).issubset(frame.columns)
    assert {"take_profit", "stop_loss"}.issubset(set(frame["barrier_hit_type"]))
    for field in dataset_required_label_fields:
        assert frame[field].notna().any(), field

    result = run_hmm_knn_research(
        config_path=_write_hmm_knn_test_config(tmp_path),
        dataset_path=dataset_result.dataset_path,
        output_dir=tmp_path / "hmm_artifacts",
    )
    manifest = json.loads(result.artifact_manifest_path.read_text(encoding="utf-8"))
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    meta = pd.read_parquet(result.meta_predictions_path)

    assert manifest["research_only"] is True
    assert manifest["dataset_path"] == str(dataset_result.dataset_path)
    assert metrics["research_only"] is True
    assert set(required_label_fields).issubset(meta.columns)
    for field in required_label_fields:
        assert meta[field].notna().any(), field
    assert meta["max_adverse_excursion"].gt(0.0).any()
    assert meta["max_favorable_excursion"].gt(0.0).any()
    assert meta["time_in_trade"].gt(0.0).any()


def test_replay_eval_is_deterministic_and_has_promotion_reasons(tmp_path) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    dataset_path = tmp_path / "dataset.parquet"
    rows = []
    for index in range(140):
        label = 1 if index % 2 == 0 else 0
        row = {column: 0.0 for column in RESEARCH_FEATURE_COLUMNS}
        row.update(
            {
                "signal_id": f"rep-{index}",
                "source": "tradingview",
                "symbol": "BTCUSDT",
                "direction": "long" if label else "short",
                "tv_bar_time_ms": 1712649600000 + (index * 900_000),
                "received_time_ms": 1712649600000 + (index * 900_000) + 1000,
                "feature_version": "v2-btc-acceptance-2",
                "label_version": "triple_barrier_live_parity_v1",
                "model_version": "observe_only",
                "calibration_version": "none",
                "v1_baseline_accept": index % 3 == 0,
                "v1_rejection_reason": None,
                "entry_price": 70000.0,
                "tp_price": 70100.0,
                "sl_price": 69900.0,
                "label_exit_reason": "take_profit" if label else "stop_loss",
                "label_accept": label,
                "label_pnl_multiple": 1.2 if label else -1.0,
                "basis_bps": 1.5,
                "primary_signed_imbalance_ratio": 0.4 if label else -0.4,
                "top_of_book_imbalance": 0.15 if label else -0.15,
                "funding_rate": 0.0001 if label else -0.00005,
                "open_interest_change_pct": 0.05 if label else -0.03,
                "premium_basis_rate": 0.0003 if label else -0.0002,
                "realized_volatility": 0.01 + (0.002 * label),
                "atr_percentile": 0.7 if label else 0.3,
                "session_us": 1.0 if label else 0.0,
            }
        )
        rows.append(row)
    pd.DataFrame(rows).to_parquet(dataset_path, index=False)

    output_dir = tmp_path / "artifacts"
    train_artifacts = train_base_model(dataset_path, plan, output_dir)
    artifact_manifest_path = calibrate_model(train_artifacts.manifest_path, plan)
    first_metrics_path = replay_eval(artifact_manifest_path, plan)
    first_metrics = json.loads(first_metrics_path.read_text(encoding="utf-8"))
    second_metrics_path = replay_eval(artifact_manifest_path, plan)
    second_metrics = json.loads(second_metrics_path.read_text(encoding="utf-8"))

    assert {key: value for key, value in first_metrics.items() if key != "latency_ms_per_row"} == {
        key: value for key, value in second_metrics.items() if key != "latency_ms_per_row"
    }
    assert "promotion_failures" in first_metrics
    assert "mean_absolute_calibration_error" in first_metrics
    assert "confidence_bucket_summary" in first_metrics
    assert first_metrics["walk_forward_summaries"][0]["train_end_time_ms"] < first_metrics["walk_forward_summaries"][0]["test_start_time_ms"]


def test_shadow_scoring_safe_skip_on_feature_version_mismatch(app_config, tmp_path, sample_bars) -> None:
    plan = load_research_plan(Path("configs/v2_btc_research.json"))
    dataset_path = tmp_path / "dataset.parquet"
    rows = []
    for index in range(120):
        label = 1 if index % 2 == 0 else 0
        row = {column: 0.0 for column in RESEARCH_FEATURE_COLUMNS}
        row.update(
            {
                "signal_id": f"skip-{index}",
                "source": "tradingview",
                "symbol": "BTCUSDT",
                "direction": "long" if label else "short",
                "tv_bar_time_ms": 1712649600000 + (index * 900_000),
                "received_time_ms": 1712649600000 + (index * 900_000) + 1000,
                "feature_version": "v2-btc-acceptance-2",
                "label_version": "triple_barrier_live_parity_v1",
                "model_version": "observe_only",
                "calibration_version": "none",
                "v1_baseline_accept": True,
                "v1_rejection_reason": None,
                "entry_price": 70000.0,
                "tp_price": 70100.0,
                "sl_price": 69900.0,
                "label_exit_reason": "take_profit" if label else "stop_loss",
                "label_accept": label,
                "label_pnl_multiple": 1.2 if label else -1.0,
            }
        )
        rows.append(row)
    pd.DataFrame(rows).to_parquet(dataset_path, index=False)

    output_dir = tmp_path / "artifacts"
    train_artifacts = train_base_model(dataset_path, plan, output_dir)
    artifact_manifest_path = calibrate_model(train_artifacts.manifest_path, plan)
    scorer = AcceptanceScorer.from_manifest_path(artifact_manifest_path)
    scorer.manifest["feature_version"] = "mismatched-feature-version"

    config = AppConfig(
        runtime_mode=RuntimeMode.SHADOW,
        db_path=tmp_path / "shadow-skip.sqlite3",
        webhook=app_config.webhook,
        strategy=replace(app_config.strategy, hurst_window_bars=32),
        binance=app_config.binance,
        hyperliquid=app_config.hyperliquid,
        research=ResearchConfig(
            output_dir=output_dir,
            config_path=Path("configs/v2_btc_research.json"),
            artifact_manifest_path=artifact_manifest_path,
        ),
    )
    store = SQLiteStore(config.db_path)

    class FakeCandles:
        async def start_market_streams(self, symbols: list[str]):
            return None

        async def fetch_recent_closed_bars(self, symbol: str, limit: int):
            extended = sample_bars * 2
            return extended[-limit:]

        async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True):
            return (sample_bars * 2)[-1]

        async def get_microstructure_snapshot(self, symbol: str, *, windows_seconds, now_ms):
            return {"healthy": True, "mid_price": "70580", "top_of_book_imbalance": "0.25", "windows": {"20": {"signed_ratio": "0.2"}}}

        async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8):
            return {"funding_rate": "0.0001", "funding_rate_change": "0.00002", "time_to_next_funding_ms": 1_800_000}

        async def fetch_open_interest_context(self, symbol: str, *, as_of_ms: int, period: str = "5m", lookback_points: int = 13):
            return {"open_interest": "1000", "open_interest_change": "50", "open_interest_change_pct": "0.05", "open_interest_value": "70500000"}

        async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m"):
            return {"basis_rate": "0.0003", "basis": "21", "premium_close": "0.0002"}

        async def close(self):
            return None

    class ShadowAdapter:
        mode = RuntimeMode.SHADOW

        async def start_user_streams(self):
            return None

        def get_stream_status(self):
            return {"enabled": False, "started": False}

        async def execute(self, intents):
            return []

        async def shutdown(self):
            return None

    engine = TradingEngine(config, store, FakeCandles(), ShadowAdapter(), scorer=scorer, clock=lambda: 1712665800000)

    async def _run() -> None:
        await engine.initialize()
        packet, _, _ = await engine.handle_signal(
            SignalIntent(
                signal_id="shadow-score-skip-1",
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                tv_bar_time_ms=1712662200000,
                received_time_ms=1712665800000,
                raw_payload={},
            )
        )
        assert packet.feature_snapshot["v2_acceptance"]["status"] == "skipped"
        assert "feature_version_mismatch" in packet.feature_snapshot["v2_acceptance"]["scoring_fallback_reason"]

    import asyncio

    asyncio.run(_run())
