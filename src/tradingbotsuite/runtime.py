from __future__ import annotations

from tradingbotsuite.adapters.binance import BinanceCandleClient
from tradingbotsuite.adapters.execution import make_execution_adapter
from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.engine import TradingEngine
from tradingbotsuite.live.preflight import assert_live_preflight
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research.inference import AcceptanceScorer


def build_engine(config: AppConfig, trace_sink=None) -> TradingEngine:
    assert_live_preflight(config, command="serve")
    store = SQLiteStore(config.db_path)
    candle_client = BinanceCandleClient(
        config.binance.base_url,
        ws_base_url=config.binance.ws_base_url,
        ws_stale_after_ms=config.binance.ws_stale_after_ms,
        depth_update_speed_ms=config.binance.depth_update_speed_ms,
        depth_snapshot_limit=config.binance.depth_snapshot_limit,
        depth_required_levels=config.binance.depth_required_levels,
        depth_resync_min_interval_ms=config.binance.depth_resync_min_interval_ms,
        depth_snapshot_default_backoff_ms=config.binance.depth_snapshot_default_backoff_ms,
        depth_max_buffer_events=config.binance.depth_max_buffer_events,
        depth_reconnect_backoff_ms=config.binance.depth_reconnect_backoff_ms,
        depth_reconnect_max_backoff_ms=config.binance.depth_reconnect_max_backoff_ms,
        websocket_planned_reconnect_ms=config.binance.websocket_planned_reconnect_ms,
        websocket_planned_reconnect_jitter_ms=config.binance.websocket_planned_reconnect_jitter_ms,
        rest_weight_budget_pct=config.binance.rest_weight_budget_pct,
    )
    execution_adapter = make_execution_adapter(
        config.runtime_mode,
        entry_slippage_bps=config.strategy.entry_slippage_bps,
        exit_slippage_bps=config.strategy.exit_slippage_bps,
        price_tick=config.strategy.price_tick,
        size_step=config.strategy.size_step,
        hyperliquid_config=config.hyperliquid,
    )
    scorer = None
    if config.research.artifact_manifest_path is not None and config.research.artifact_manifest_path.exists():
        scorer = AcceptanceScorer.from_manifest_path(config.research.artifact_manifest_path)
    return TradingEngine(
        config,
        store,
        candle_client,
        execution_adapter,
        trace_sink=trace_sink,
        scorer=scorer,
    )
