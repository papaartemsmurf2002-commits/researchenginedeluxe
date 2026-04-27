from __future__ import annotations

from pathlib import Path

from tradingbotsuite.adapters.binance import BinanceCandleClient
from tradingbotsuite.config import AppConfig
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research.config import ResearchPlan, load_research_plan
from tradingbotsuite.research.dataset import DatasetBuildResult, ResearchDatasetBuilder
from tradingbotsuite.research.evaluation import replay_eval
from tradingbotsuite.research.modeling import calibrate_model, train_base_model


async def build_dataset(config: AppConfig, *, plan: ResearchPlan | None = None) -> DatasetBuildResult:
    resolved_plan = plan or load_research_plan(config.research.config_path)
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
    try:
        builder = ResearchDatasetBuilder(
            config=config,
            plan=resolved_plan,
            store=store,
            candle_client=candle_client,
        )
        return await builder.build()
    finally:
        await candle_client.close()


def train_model(config: AppConfig, *, dataset_path: Path, plan: ResearchPlan | None = None) -> Path:
    resolved_plan = plan or load_research_plan(config.research.config_path)
    artifacts = train_base_model(dataset_path, resolved_plan, config.research.output_dir)
    return artifacts.manifest_path


def calibrate_model_artifact(config: AppConfig, *, train_manifest_path: Path, plan: ResearchPlan | None = None) -> Path:
    resolved_plan = plan or load_research_plan(config.research.config_path)
    return calibrate_model(train_manifest_path, resolved_plan)


def replay_eval_artifact(config: AppConfig, *, artifact_manifest_path: Path, plan: ResearchPlan | None = None) -> Path:
    resolved_plan = plan or load_research_plan(config.research.config_path)
    return replay_eval(artifact_manifest_path, resolved_plan)
