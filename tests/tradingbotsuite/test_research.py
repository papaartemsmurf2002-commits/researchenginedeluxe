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
from tradingbotsuite.research.dataset import ResearchDatasetBuilder
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

    fake_client = FakeResearchClient()
    builder = ResearchDatasetBuilder(config=config, plan=plan, store=store, candle_client=fake_client)
    result = await builder.build()
    frame = pd.read_parquet(result.dataset_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.row_count == 2
    assert "source" in frame.columns
    assert "label_version" in frame.columns
    assert "funding_rate" in frame.columns
    assert "rule_acceptance_total_score" in frame.columns
    assert "rule_acceptance_accept_candidate" in frame.columns
    assert frame.iloc[0]["label_accept"] == 1
    assert manifest["row_count"] == 2
    assert manifest["symbol"] == "BTCUSDT"
    assert manifest["feature_version"] == "v2-btc-acceptance-2"
    assert manifest["label_version"] == "triple_barrier_live_parity_v1"
    assert manifest["source_counts"] == {"tradingview": 2}
    assert manifest["source_mode_counts"] == {"tradingview": 2}
    assert manifest["class_balance"]["label_accept_1"] == 2
    assert manifest["planned_split_summary"]["walk_forward_splits"] == plan.evaluation.walk_forward_splits
    assert "missing_feature_rates" in manifest
    assert fake_client.range_calls == 1


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
