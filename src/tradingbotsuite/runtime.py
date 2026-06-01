from __future__ import annotations

from tradingbotsuite.adapters.binance import BinanceCandleClient
from tradingbotsuite.adapters.execution import make_execution_adapter
from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.engine import TradingEngine
from tradingbotsuite.live.preflight import assert_live_preflight
from tradingbotsuite.live.shadow_loader import load_shadow_promotion_candidate
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.promotion.artifact_validator import load_artifact_manifest, validate_artifact_for_runtime_mode
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
    shadow_promotion_report = None
    artifact_path = config.research.artifact_manifest_path
    if artifact_path is not None and artifact_path.exists():
        manifest = load_artifact_manifest(artifact_path)
        validation = validate_artifact_for_runtime_mode(
            manifest,
            runtime_mode=config.runtime_mode,
            manifest_path=artifact_path,
        )
        if not validation.allowed:
            raise ValueError("runtime artifact rejected: " + ", ".join(validation.reasons))
        if manifest.get("promotion_candidate_manifest_version"):
            loaded_candidate = load_shadow_promotion_candidate(config, artifact_path)
            shadow_promotion_report = loaded_candidate.report.to_payload()
        else:
            scorer = AcceptanceScorer.from_manifest_path(artifact_path)
    return TradingEngine(
        config,
        store,
        candle_client,
        execution_adapter,
        trace_sink=trace_sink,
        scorer=scorer,
        shadow_promotion_report=shadow_promotion_report,
    )
