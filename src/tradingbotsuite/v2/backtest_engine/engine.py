# V2-AUDIT-ID: V2-AUD-BTENG-001
# V2-CONTRACTS: docs/contracts/backtest_engine_contract.md, docs/contracts/run_artifact_contract.md
# V2-BOUNDARY: research_only, vectorized_backtest, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_backtest_engine
"""Initial v2 vectorized backtest engine and artifact writer."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.backtest_engine.artifacts import (
    BacktestMetrics,
    BacktestRunConfig,
    BacktestRunResult,
    EngineLane,
    MissingDataPolicy,
    RunArtifactRef,
    RunManifest,
    RunStatus,
    StrategyContext,
    ValidationStatus,
)
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.costs.models import (
    CostModelConfig,
    CostStressScenario,
    build_cost_manifest,
    calculate_cost_breakdown,
    scenario_multiplier,
)
from tradingbotsuite.v2.strategy_specs import (
    SignalFrame,
    StrategySpec,
    compile_signal_frame,
    parse_strategy_spec,
)
from tradingbotsuite.v2.validation.walk_forward import monthly_validation_fold_windows

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


class BacktestEngineError(ValueError):
    """Raised when a v2 backtest cannot be simulated safely."""


def run_vectorized_backtest(
    *,
    config: BacktestRunConfig | Mapping[str, Any],
    strategy_spec: StrategySpec | Mapping[str, Any],
    panel_rows: Iterable[Mapping[str, Any]],
    params: Mapping[str, Any] | None = None,
) -> BacktestRunResult:
    parsed_config = (
        config if isinstance(config, BacktestRunConfig) else BacktestRunConfig.model_validate(config)
    )
    parsed_spec = parse_strategy_spec(strategy_spec)
    materialized_panel = [dict(row) for row in panel_rows]
    run_id = parsed_config.run_id or _deterministic_run_id(
        parsed_config,
        parsed_spec,
        params or {},
        materialized_panel,
    )
    run_dir = _run_dir(parsed_config.output_root, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        if parsed_config.engine_lane != EngineLane.VECTORIZED:
            raise BacktestEngineError(f"unsupported vectorized lane: {parsed_config.engine_lane.value}")
        if parsed_config.require_net_metrics is not True:
            raise BacktestEngineError("gross_only_metrics_rejected")
        signal_frame = compile_signal_frame(parsed_spec, materialized_panel)
        simulation = _simulate_vectorized(
            parsed_config,
            parsed_spec,
            signal_frame,
            materialized_panel,
            run_id=run_id,
            cost_scenario=CostStressScenario.BASE,
        )
        stress_rows = _cost_stress_rows(
            config=parsed_config,
            base_simulation=simulation,
        )
        simulation.cost_stress = stress_rows
        return _write_run_artifacts(
            config=parsed_config,
            strategy_spec=parsed_spec,
            params=dict(params or {}),
            panel_rows=materialized_panel,
            run_id=run_id,
            run_dir=run_dir,
            status=RunStatus.SUCCEEDED,
            simulation=simulation,
        )
    except Exception as exc:
        return _write_failure_artifacts(
            config=parsed_config,
            strategy_spec=parsed_spec,
            params=dict(params or {}),
            panel_rows=materialized_panel,
            run_id=run_id,
            run_dir=run_dir,
            engine_lane=EngineLane.VECTORIZED,
            failure_reason=str(exc),
        )


def run_event_driven_placeholder(
    *,
    config: BacktestRunConfig | Mapping[str, Any],
    strategy_spec: StrategySpec | Mapping[str, Any],
    panel_rows: Iterable[Mapping[str, Any]],
    params: Mapping[str, Any] | None = None,
) -> BacktestRunResult:
    parsed_config = (
        config if isinstance(config, BacktestRunConfig) else BacktestRunConfig.model_validate(config)
    ).model_copy(update={"engine_lane": EngineLane.EVENT_DRIVEN})
    parsed_spec = parse_strategy_spec(strategy_spec)
    materialized_panel = [dict(row) for row in panel_rows]
    run_id = parsed_config.run_id or _deterministic_run_id(
        parsed_config,
        parsed_spec,
        params or {},
        materialized_panel,
    )
    run_dir = _run_dir(parsed_config.output_root, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    return _write_failure_artifacts(
        config=parsed_config,
        strategy_spec=parsed_spec,
        params=dict(params or {}),
        panel_rows=materialized_panel,
        run_id=run_id,
        run_dir=run_dir,
        engine_lane=EngineLane.EVENT_DRIVEN,
        failure_reason="event_driven_engine_placeholder_blocked",
    )


def run_event_driven_backtest(
    *,
    config: BacktestRunConfig | Mapping[str, Any],
    strategy_spec: StrategySpec | Mapping[str, Any],
    panel_rows: Iterable[Mapping[str, Any]],
    microstructure_rows: Iterable[Mapping[str, Any]] | None = None,
    params: Mapping[str, Any] | None = None,
) -> BacktestRunResult:
    parsed_config = (
        config if isinstance(config, BacktestRunConfig) else BacktestRunConfig.model_validate(config)
    ).model_copy(update={"engine_lane": EngineLane.EVENT_DRIVEN})
    parsed_spec = parse_strategy_spec(strategy_spec)
    materialized_panel = [dict(row) for row in panel_rows]
    run_id = parsed_config.run_id or _deterministic_run_id(
        parsed_config,
        parsed_spec,
        params or {},
        materialized_panel,
    )
    run_dir = _run_dir(parsed_config.output_root, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        if parsed_config.require_net_metrics is not True:
            raise BacktestEngineError("gross_only_metrics_rejected")
        event_queue = _normalize_microstructure_events(microstructure_rows or ())
        _reject_undocumented_maker_assumption(parsed_config, parsed_spec)
        signal_frame = compile_signal_frame(parsed_spec, materialized_panel)
        simulation = _simulate_vectorized(
            parsed_config,
            parsed_spec,
            signal_frame,
            materialized_panel,
            run_id=run_id,
            cost_scenario=CostStressScenario.BASE,
        )
        stress_rows = _cost_stress_rows(
            config=parsed_config,
            base_simulation=simulation,
        )
        simulation.cost_stress = stress_rows
        return _write_run_artifacts(
            config=parsed_config,
            strategy_spec=parsed_spec,
            params=dict(params or {}),
            panel_rows=materialized_panel,
            run_id=run_id,
            run_dir=run_dir,
            status=RunStatus.SUCCEEDED,
            simulation=simulation,
        )
    except Exception as exc:
        return _write_failure_artifacts(
            config=parsed_config,
            strategy_spec=parsed_spec,
            params=dict(params or {}),
            panel_rows=materialized_panel,
            run_id=run_id,
            run_dir=run_dir,
            engine_lane=EngineLane.EVENT_DRIVEN,
            failure_reason=str(exc),
        )


def recompute_metrics_from_run_manifest(
    *,
    run_dir: str | Path,
    panel_rows: Iterable[Mapping[str, Any]],
) -> BacktestMetrics:
    root = Path(run_dir)
    manifest = RunManifest.model_validate(_read_json(root / "run_manifest.json"))
    spec = StrategySpec.model_validate(_read_json(root / manifest.artifacts["strategy_spec"].path))
    config = BacktestRunConfig(
        run_id=manifest.run_id,
        experiment_id=manifest.experiment_id,
        trial_index=manifest.trial_index,
        agent_or_user=manifest.agent_or_user,
        output_root=str(root.parent),
        archive_snapshot_id=manifest.archive_snapshot_id,
        universe_snapshot_id=manifest.universe_snapshot_id,
        data_manifest_id=manifest.data_manifest_id,
        data_manifest_hash=manifest.data_manifest_hash,
        validation_manifest_hash=manifest.validation_manifest_hash,
        cost_manifest_hash=manifest.cost_manifest_hash,
        validation_policy_id=manifest.validation_policy_id,
        cost_model_id=manifest.cost_model_id,
        account_notional_usd=manifest.account_notional_usd,
        engine_lane=manifest.engine_lane,
        missing_data_policy=manifest.missing_data_policy,
        lockbox_policy_id=manifest.lockbox_policy_id,
        lockbox_start=manifest.lockbox_start,
        lockbox_end=manifest.lockbox_end,
        data_coverage_min=manifest.data_coverage_min,
        universe_mode=manifest.universe_mode,
        venue_scope=manifest.venue_scope,
        git_sha=manifest.git_sha,
        environment_hash=manifest.environment_hash,
        cost_model=_cost_model_from_manifest(root, manifest),
    )
    if manifest.engine_lane != EngineLane.VECTORIZED:
        raise BacktestEngineError("only vectorized runs can be recomputed")
    signal_frame = compile_signal_frame(spec, panel_rows)
    simulation = _simulate_vectorized(
        config,
        spec,
        signal_frame,
        [dict(row) for row in panel_rows],
        run_id=manifest.run_id,
        cost_scenario=CostStressScenario.BASE,
    )
    return simulation.metrics


class _SimulationResult:
    def __init__(
        self,
        *,
        metrics: BacktestMetrics,
        equity_curve: list[dict[str, Any]],
        daily_returns: list[dict[str, Any]],
        trades: list[dict[str, Any]],
        positions: list[dict[str, Any]],
        per_instrument_metrics: list[dict[str, Any]],
        fold_metrics: list[dict[str, Any]],
        cost_stress: list[dict[str, Any]],
        context: StrategyContext,
    ) -> None:
        self.metrics = metrics
        self.equity_curve = equity_curve
        self.daily_returns = daily_returns
        self.trades = trades
        self.positions = positions
        self.per_instrument_metrics = per_instrument_metrics
        self.fold_metrics = fold_metrics
        self.cost_stress = cost_stress
        self.context = context


def _simulate_vectorized(
    config: BacktestRunConfig,
    strategy_spec: StrategySpec,
    signal_frame: SignalFrame,
    panel_rows: list[dict[str, Any]],
    *,
    run_id: str,
    cost_scenario: CostStressScenario,
) -> _SimulationResult:
    cost_model = _effective_cost_model(config)
    rows = [_PanelRow(row) for row in panel_rows]
    if not rows:
        raise BacktestEngineError("panel_rows_empty")
    rows.sort(key=lambda row: (row.ts, row.instrument_id))
    instruments = tuple(sorted({row.instrument_id for row in rows}))
    _enforce_common_clock(rows, instruments, config.missing_data_policy)
    signal_by_key = {
        (row.ts, row.instrument_id): row
        for row in signal_frame.rows
    }
    rows_by_instrument: dict[str, list[_PanelRow]] = defaultdict(list)
    for row in rows:
        rows_by_instrument[row.instrument_id].append(row)
    previous_target_by_instrument = {instrument_id: 0.0 for instrument_id in instruments}
    gross_equity = config.initial_equity
    net_equity = config.initial_equity
    positions: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []
    per_instrument_totals: dict[str, dict[str, float]] = {
        instrument_id: {
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "fee_cost": 0.0,
            "spread_cost": 0.0,
            "slippage_cost": 0.0,
            "impact_cost": 0.0,
            "transaction_cost": 0.0,
            "funding_pnl": 0.0,
            "turnover": 0.0,
            "trade_count": 0.0,
            "capacity_blocked_count": 0.0,
        }
        for instrument_id in instruments
    }
    timestamps = sorted({row.ts for row in rows})
    row_lookup = {(row.ts, row.instrument_id): row for row in rows}
    prior_row_by_instrument: dict[str, _PanelRow | None] = {instrument_id: None for instrument_id in instruments}
    for ts in timestamps:
        timestamp_positions: list[dict[str, Any]] = []
        gross_return = 0.0
        net_return = 0.0
        turnover = 0.0
        fee_cost_total = 0.0
        spread_cost_total = 0.0
        slippage_cost_total = 0.0
        impact_cost_total = 0.0
        transaction_cost_total = 0.0
        funding_total = 0.0
        gross_exposure = 0.0
        capacity_blocked_count = 0
        for instrument_id in instruments:
            panel_row = row_lookup[(ts, instrument_id)]
            signal = signal_by_key.get((ts, instrument_id))
            previous_weight = previous_target_by_instrument[instrument_id]
            applied_weight = previous_weight
            target_weight = signal.target_weight if signal is not None else 0.0
            price_return = _price_return(strategy_spec.execution.price_basis.value, panel_row, prior_row_by_instrument[instrument_id])
            gross_pnl = applied_weight * price_return
            weight_turnover = abs(target_weight - previous_weight)
            funding_rate = _funding_rate(panel_row)
            if funding_rate is None:
                if cost_model.funding_required or cost_model.funding_missing_policy == "fail":
                    raise BacktestEngineError("funding_required_missing")
                funding_rate = 0.0
            cost_breakdown = calculate_cost_breakdown(
                config=cost_model,
                weight_delta=weight_turnover,
                applied_weight=applied_weight,
                funding_rate=funding_rate,
                volume_notional=_volume_notional(panel_row),
                observed_spread_bps=_observed_spread_bps(panel_row),
                scenario=cost_scenario,
            )
            if cost_breakdown.capacity_blocked:
                reason = cost_breakdown.capacity_reason or "liquidity_participation_blocked"
                raise BacktestEngineError(
                    f"{reason}: {instrument_id} {utc_isoformat(ts)} participation={cost_breakdown.participation_rate:.12g} cap={cost_breakdown.max_volume_participation:.12g}"
                )
            funding_pnl = cost_breakdown.funding_pnl
            fee_cost = cost_breakdown.fee_cost
            spread_cost = cost_breakdown.spread_cost
            slippage_cost = cost_breakdown.slippage_cost
            impact_cost = cost_breakdown.impact_cost
            transaction_cost = cost_breakdown.total_transaction_cost
            net_pnl = gross_pnl + cost_breakdown.net_pnl_adjustment
            side = "long" if applied_weight > 0 else "short" if applied_weight < 0 else "flat"
            position = {
                "ts": utc_isoformat(ts),
                "instrument_id": instrument_id,
                "applied_weight": applied_weight,
                "target_weight": target_weight,
                "signal": signal.signal if signal is not None else 0.0,
                "side": side,
                "price_basis": strategy_spec.execution.price_basis.value,
                "price_return": price_return,
                "gross_pnl": gross_pnl,
                "funding_pnl": funding_pnl,
                "funding_rate": funding_rate,
                "account_notional_usd": cost_breakdown.account_notional_usd,
                "trade_notional_usd": cost_breakdown.trade_notional_usd,
                "fee_cost": fee_cost,
                "spread_cost": spread_cost,
                "slippage_cost": slippage_cost,
                "impact_cost": impact_cost,
                "transaction_cost": transaction_cost,
                "volume_notional": cost_breakdown.volume_notional,
                "participation_rate": cost_breakdown.participation_rate,
                "capacity_blocked": cost_breakdown.capacity_blocked,
                "capacity_reason": cost_breakdown.capacity_reason,
                "cost_scenario": cost_scenario.value,
                "net_pnl": net_pnl,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_evidence": False,
                "candidate_pack_eligible": False,
                "live_signal": False,
                "paper_signal": False,
                "sizing_instruction": False,
                "order_placement_instruction": False,
                "runtime_mode_change": False,
            }
            timestamp_positions.append(position)
            if weight_turnover > 0:
                trades.append(
                    {
                        "ts": utc_isoformat(ts),
                        "instrument_id": instrument_id,
                        "from_weight": previous_weight,
                        "to_weight": target_weight,
                        "turnover": weight_turnover,
                        "account_notional_usd": cost_breakdown.account_notional_usd,
                        "trade_notional_usd": cost_breakdown.trade_notional_usd,
                        "side": "long" if target_weight > 0 else "short" if target_weight < 0 else "flat",
                        "price_basis": strategy_spec.execution.price_basis.value,
                        "fee_cost": fee_cost,
                        "spread_cost": spread_cost,
                        "slippage_cost": slippage_cost,
                        "impact_cost": impact_cost,
                        "transaction_cost": transaction_cost,
                        "participation_rate": cost_breakdown.participation_rate,
                        "capacity_blocked": cost_breakdown.capacity_blocked,
                        "capacity_reason": cost_breakdown.capacity_reason,
                        "cost_scenario": cost_scenario.value,
                        "research_only": True,
                        "observe_only": True,
                        "promotion_ready": False,
                        "candidate_evidence": False,
                        "candidate_pack_eligible": False,
                        "live_signal": False,
                        "paper_signal": False,
                        "sizing_instruction": False,
                        "order_placement_instruction": False,
                        "runtime_mode_change": False,
                    }
                )
                per_instrument_totals[instrument_id]["trade_count"] += 1
            gross_return += gross_pnl
            net_return += net_pnl
            turnover += weight_turnover
            fee_cost_total += fee_cost
            spread_cost_total += spread_cost
            slippage_cost_total += slippage_cost
            impact_cost_total += impact_cost
            transaction_cost_total += transaction_cost
            funding_total += funding_pnl
            capacity_blocked_count += 1 if cost_breakdown.capacity_blocked else 0
            gross_exposure += abs(applied_weight)
            per_instrument_totals[instrument_id]["gross_pnl"] += gross_pnl
            per_instrument_totals[instrument_id]["net_pnl"] += net_pnl
            per_instrument_totals[instrument_id]["fee_cost"] += fee_cost
            per_instrument_totals[instrument_id]["spread_cost"] += spread_cost
            per_instrument_totals[instrument_id]["slippage_cost"] += slippage_cost
            per_instrument_totals[instrument_id]["impact_cost"] += impact_cost
            per_instrument_totals[instrument_id]["transaction_cost"] += transaction_cost
            per_instrument_totals[instrument_id]["funding_pnl"] += funding_pnl
            per_instrument_totals[instrument_id]["turnover"] += weight_turnover
            per_instrument_totals[instrument_id]["capacity_blocked_count"] += (
                1 if cost_breakdown.capacity_blocked else 0
            )
            previous_target_by_instrument[instrument_id] = target_weight
            prior_row_by_instrument[instrument_id] = panel_row
        gross_equity *= 1.0 + gross_return
        net_equity *= 1.0 + net_return
        positions.extend(timestamp_positions)
        equity_curve.append(
            {
                "ts": utc_isoformat(ts),
                "gross_return": gross_return,
                "net_return": net_return,
                "gross_equity": gross_equity,
                "net_equity": net_equity,
                "turnover": turnover,
                "fee_cost": fee_cost_total,
                "spread_cost": spread_cost_total,
                "slippage_cost": slippage_cost_total,
                "impact_cost": impact_cost_total,
                "transaction_cost": transaction_cost_total,
                "funding_pnl": funding_total,
                "capacity_blocked_count": capacity_blocked_count,
                "cost_scenario": cost_scenario.value,
                "gross_exposure": gross_exposure,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    daily_returns = _daily_returns(equity_curve)
    per_instrument_metrics = [
        {
            "instrument_id": instrument_id,
            **totals,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }
        for instrument_id, totals in sorted(per_instrument_totals.items())
    ]
    fold_metrics = _fold_metrics(
        equity_curve=equity_curve,
        full_window_start=timestamps[0],
        full_window_end=timestamps[-1],
        gross_return=gross_equity - config.initial_equity,
        net_return=net_equity - config.initial_equity,
    )
    total_fee = sum(row["fee_cost"] for row in positions)
    total_spread = sum(row["spread_cost"] for row in positions)
    total_slippage = sum(row["slippage_cost"] for row in positions)
    total_impact = sum(row["impact_cost"] for row in positions)
    total_transaction_cost = sum(row["transaction_cost"] for row in positions)
    metrics = BacktestMetrics(
        run_id=run_id,
        status=RunStatus.SUCCEEDED,
        gross_return=gross_equity - config.initial_equity,
        net_return=net_equity - config.initial_equity,
        gross_equity_final=gross_equity,
        net_equity_final=net_equity,
        total_fee_cost=total_fee,
        total_spread_cost=total_spread,
        total_slippage_cost=total_slippage,
        total_impact_cost=total_impact,
        total_transaction_cost=total_transaction_cost,
        total_funding_pnl=sum(row["funding_pnl"] for row in positions),
        total_turnover=sum(row["turnover"] for row in trades),
        trade_count=len(trades),
        position_row_count=len(positions),
        capacity_blocked_count=sum(1 for row in positions if row["capacity_blocked"]),
        gross_only=False,
    )
    context = StrategyContext(
        run_id=run_id,
        experiment_id=config.experiment_id,
        trial_index=config.trial_index,
        archive_snapshot_id=config.archive_snapshot_id,
        universe_snapshot_id=config.universe_snapshot_id,
        data_manifest_id=config.data_manifest_id,
        validation_policy_id=config.validation_policy_id,
        cost_model_id=config.cost_model_id,
        timeframe=strategy_spec.inputs.timeframe,
        venue_scope=config.venue_scope,
        universe_mode=config.universe_mode,
        instrument_count=len(instruments),
        backtest_start=timestamps[0],
        backtest_end=timestamps[-1],
        lockbox_policy_id=config.lockbox_policy_id,
        lockbox_start=config.lockbox_start,
        lockbox_end=config.lockbox_end,
        data_coverage_min=config.data_coverage_min,
    )
    return _SimulationResult(
        metrics=metrics,
        equity_curve=equity_curve,
        daily_returns=daily_returns,
        trades=trades,
        positions=positions,
        per_instrument_metrics=per_instrument_metrics,
        fold_metrics=fold_metrics,
        cost_stress=[],
        context=context,
    )


def _cost_stress_rows(
    *,
    config: BacktestRunConfig,
    base_simulation: _SimulationResult,
) -> list[dict[str, Any]]:
    cost_model = _effective_cost_model(config)
    rows: list[dict[str, Any]] = []
    simulations_by_scenario: dict[CostStressScenario, BacktestMetrics] = {
        CostStressScenario.BASE: base_simulation.metrics
    }
    for scenario in config.cost_stress_scenarios:
        if scenario == CostStressScenario.BASE:
            continue
        simulations_by_scenario[scenario] = _stress_metrics_from_base(
            base_simulation,
            scenario=scenario,
            run_id=base_simulation.metrics.run_id,
        )
    base_net = base_simulation.metrics.net_return
    for scenario in config.cost_stress_scenarios:
        metrics = simulations_by_scenario[scenario]
        cost_fragile_warning = scenario != CostStressScenario.BASE and base_net > 0.0 and metrics.net_return <= 0.0
        rows.append(
            {
                "scenario_id": scenario.value,
                "cost_model_id": cost_model.cost_model_id,
                "cost_model_hash": cost_model.config_hash,
                "cost_multiplier": scenario_multiplier(scenario),
                "gross_return": metrics.gross_return,
                "net_return": metrics.net_return,
                "gross_equity_final": metrics.gross_equity_final,
                "net_equity_final": metrics.net_equity_final,
                "total_fee_cost": metrics.total_fee_cost,
                "total_spread_cost": metrics.total_spread_cost,
                "total_slippage_cost": metrics.total_slippage_cost,
                "total_impact_cost": metrics.total_impact_cost,
                "total_transaction_cost": metrics.total_transaction_cost,
                "total_funding_pnl": metrics.total_funding_pnl,
                "total_turnover": metrics.total_turnover,
                "trade_count": metrics.trade_count,
                "capacity_blocked_count": metrics.capacity_blocked_count,
                "cost_fragile_warning": cost_fragile_warning,
                "cost_dependent_failure": cost_fragile_warning,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return rows


def _stress_metrics_from_base(
    base_simulation: _SimulationResult,
    *,
    scenario: CostStressScenario,
    run_id: str,
) -> BacktestMetrics:
    multiplier = scenario_multiplier(scenario)
    base = base_simulation.metrics
    initial_equity = (
        base.gross_equity_final / (1.0 + base.gross_return)
        if base.gross_return > -1.0
        else 1.0
    )
    gross_equity = initial_equity
    net_equity = initial_equity
    for row in base_simulation.equity_curve:
        gross_return = float(row["gross_return"])
        funding_pnl = float(row["funding_pnl"])
        transaction_cost = float(row["transaction_cost"]) * multiplier
        gross_equity *= 1.0 + gross_return
        net_equity *= 1.0 + gross_return + funding_pnl - transaction_cost
    return BacktestMetrics(
        run_id=run_id,
        status=RunStatus.SUCCEEDED,
        gross_return=gross_equity - initial_equity,
        net_return=net_equity - initial_equity,
        gross_equity_final=gross_equity,
        net_equity_final=net_equity,
        total_fee_cost=base.total_fee_cost * multiplier,
        total_spread_cost=base.total_spread_cost * multiplier,
        total_slippage_cost=base.total_slippage_cost * multiplier,
        total_impact_cost=base.total_impact_cost * multiplier,
        total_transaction_cost=base.total_transaction_cost * multiplier,
        total_funding_pnl=base.total_funding_pnl,
        total_turnover=base.total_turnover,
        trade_count=base.trade_count,
        position_row_count=base.position_row_count,
        capacity_blocked_count=base.capacity_blocked_count,
        gross_only=False,
    )


def _fold_metrics(
    *,
    equity_curve: list[dict[str, Any]],
    full_window_start: datetime,
    full_window_end: datetime,
    gross_return: float,
    net_return: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for start, end in monthly_validation_fold_windows(full_window_start, full_window_end):
        fold_rows = [
            row
            for row in equity_curve
            if start <= _parse_timestamp(row["ts"]) < end
        ]
        if not fold_rows:
            continue
        rows.append(
            {
                "fold_id": f"month-{start.year:04d}-{start.month:02d}",
                "fold_family": "monthly_validation",
                "start_ts": utc_isoformat(start),
                "end_ts": utc_isoformat(end),
                "gross_return": _compound_return(fold_rows, "gross_return"),
                "net_return": _compound_return(fold_rows, "net_return"),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    rows.append(
        {
            "fold_id": "full_window",
            "fold_family": "diagnostic",
            "start_ts": utc_isoformat(full_window_start),
            "end_ts": utc_isoformat(full_window_end),
            "gross_return": gross_return,
            "net_return": net_return,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }
    )
    return rows


def _compound_return(rows: list[dict[str, Any]], field: str) -> float:
    equity = 1.0
    for row in rows:
        equity *= 1.0 + float(row[field])
    return equity - 1.0


def _normalize_microstructure_events(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        missing = [field for field in ("ts", "instrument_id", "event_type") if field not in row]
        if missing:
            raise BacktestEngineError(
                f"event_microstructure_row_missing_fields:{index}:{','.join(missing)}"
            )
        event_type = str(row["event_type"]).lower()
        if event_type not in {"trade", "bbo", "l2"}:
            raise BacktestEngineError(f"unsupported_microstructure_event_type:{event_type}")
        event = dict(row)
        event["ts"] = _parse_timestamp(row["ts"])
        event["instrument_id"] = str(row["instrument_id"])
        event["event_type"] = event_type
        event["sequence"] = int(row.get("sequence", index))
        events.append(event)
    if not events:
        raise BacktestEngineError("event_microstructure_rows_required")
    has_book_context = any(event["event_type"] in {"bbo", "l2"} for event in events)
    if not has_book_context:
        raise BacktestEngineError("event_microstructure_bbo_or_l2_required")
    return sorted(events, key=lambda event: (event["ts"], event["instrument_id"], event["sequence"]))


def _reject_undocumented_maker_assumption(
    config: BacktestRunConfig,
    strategy_spec: StrategySpec,
) -> None:
    cost_model = config.cost_model
    queue_model_documented = bool(cost_model and cost_model.queue_model_documented)
    markers = " ".join(
        [
            config.cost_model_id.lower(),
            strategy_spec.execution.fee_model.lower(),
            "" if cost_model is None else cost_model.fee_side.lower(),
        ]
    )
    if ("maker" in markers or "mixed" in markers) and not queue_model_documented:
        raise BacktestEngineError("maker_assumption_requires_queue_model")


class _PanelRow:
    def __init__(self, row: Mapping[str, Any]) -> None:
        self.row = dict(row)
        self.ts = _parse_timestamp(row["ts"])
        self.instrument_id = str(row["instrument_id"])

    def numeric(self, field: str) -> float | None:
        value = self.row.get(field)
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed


def _enforce_common_clock(
    rows: list[_PanelRow],
    instruments: tuple[str, ...],
    policy: MissingDataPolicy,
) -> None:
    if policy != MissingDataPolicy.FAIL_CLOSED:
        raise BacktestEngineError(f"unsupported_missing_data_policy: {policy.value}")
    by_ts: dict[datetime, set[str]] = defaultdict(set)
    for row in rows:
        by_ts[row.ts].add(row.instrument_id)
    expected = set(instruments)
    for ts, observed in by_ts.items():
        missing = sorted(expected - observed)
        if missing:
            raise BacktestEngineError(
                f"missing_data_policy_fail_closed: {utc_isoformat(ts)} missing {','.join(missing)}"
            )


def _price_return(price_basis: str, row: _PanelRow, previous_row: _PanelRow | None) -> float:
    if price_basis == "next_bar_open":
        open_price = row.numeric("open")
        close_price = row.numeric("close")
        if open_price is None or close_price is None or open_price <= 0:
            raise BacktestEngineError("pnl_price_missing_for_next_bar_open")
        return (close_price / open_price) - 1.0
    if previous_row is None:
        return 0.0
    if price_basis == "close":
        previous = previous_row.numeric("close")
        current = row.numeric("close")
    elif price_basis == "mark":
        previous = previous_row.numeric("mark_price")
        current = row.numeric("mark_price")
    elif price_basis == "oracle":
        previous = previous_row.numeric("oracle_price")
        current = row.numeric("oracle_price")
    else:
        raise BacktestEngineError(f"unsupported_price_basis: {price_basis}")
    if previous is None or current is None or previous <= 0:
        raise BacktestEngineError(f"pnl_price_missing_for_{price_basis}")
    return (current / previous) - 1.0


def _funding_rate(row: _PanelRow) -> float | None:
    funding = row.numeric("funding")
    if funding is None:
        funding = row.numeric("funding_rate")
    return funding


def _volume_notional(row: _PanelRow) -> float | None:
    for field in ("volume_notional", "volume_usd", "dollar_volume", "notional_volume"):
        value = row.numeric(field)
        if value is not None:
            return value
    volume = row.numeric("volume")
    if volume is None:
        return None
    close = row.numeric("close")
    if close is not None and close > 0.0:
        return volume * close
    return volume


def _observed_spread_bps(row: _PanelRow) -> float | None:
    spread_bps = row.numeric("spread_bps")
    if spread_bps is not None:
        return spread_bps
    spread = row.numeric("spread")
    if spread is None:
        return None
    units = _spread_units(row)
    if units in {"bps", "bp", "basis_point", "basis_points"}:
        return spread
    if units in {"fraction", "decimal", "ratio", "return_fraction"}:
        return spread * 10_000.0
    if units in {"price", "quote", "absolute", "usd"}:
        close = row.numeric("close") or row.numeric("mark_price") or row.numeric("oracle_price")
        if close is not None and close > 0.0:
            return (spread / close) * 10_000.0
        return None
    if spread <= 1.0:
        return spread * 10_000.0
    return spread


def _spread_units(row: _PanelRow) -> str | None:
    for field in ("spread_units", "spread_unit", "spread_value_units"):
        value = row.row.get(field)
        if value is not None:
            normalized = str(value).strip().lower()
            if normalized:
                return normalized
    return None


def _effective_cost_model(config: BacktestRunConfig) -> CostModelConfig:
    if config.cost_model is not None:
        return config.cost_model
    return CostModelConfig(
        cost_model_id=config.cost_model_id,
        fee_bps=config.fee_bps,
        spread_bps=config.spread_bps,
        slippage_bps=config.slippage_bps,
        impact_bps=config.impact_bps,
        account_notional_usd=config.account_notional_usd,
        max_volume_participation=config.max_volume_participation,
        stress_scenarios=config.cost_stress_scenarios,
    )


def _cost_model_from_manifest(root: Path, manifest: RunManifest) -> CostModelConfig:
    cost_ref = manifest.artifacts.get("cost_manifest")
    if cost_ref is None:
        raise BacktestEngineError("run_manifest_missing_cost_manifest_ref")
    payload = _read_json(root / cost_ref.path)
    config_payload = payload.get("cost_model_config")
    if not isinstance(config_payload, dict):
        raise BacktestEngineError("cost_manifest_missing_cost_model_config")
    return CostModelConfig.model_validate(config_payload)


def _daily_returns(equity_curve: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in equity_curve:
        by_day[_parse_timestamp(row["ts"]).date()].append(row)
    daily: list[dict[str, Any]] = []
    for day, rows in sorted(by_day.items()):
        gross = 1.0
        net = 1.0
        for row in rows:
            gross *= 1.0 + float(row["gross_return"])
            net *= 1.0 + float(row["net_return"])
        daily.append(
            {
                "date": day.isoformat(),
                "gross_return": gross - 1.0,
                "net_return": net - 1.0,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return daily


def _write_run_artifacts(
    *,
    config: BacktestRunConfig,
    strategy_spec: StrategySpec,
    params: dict[str, Any],
    panel_rows: list[dict[str, Any]],
    run_id: str,
    run_dir: Path,
    status: RunStatus,
    simulation: _SimulationResult,
) -> BacktestRunResult:
    artifacts = _write_common_artifacts(
        run_dir=run_dir,
        strategy_spec=strategy_spec,
        params=params,
        panel_rows=panel_rows,
        validation_manifest=_validation_manifest(config, status=status),
        cost_manifest=_cost_manifest(config, cost_stress=simulation.cost_stress),
        metrics=simulation.metrics.model_dump(mode="json"),
        equity_curve=simulation.equity_curve,
        daily_returns=simulation.daily_returns,
        trades=simulation.trades,
        positions=simulation.positions,
        per_instrument_metrics=simulation.per_instrument_metrics,
        fold_metrics=simulation.fold_metrics,
        cost_stress=simulation.cost_stress,
        log_lines=[f"run_id={run_id}", "status=succeeded", f"engine_lane={config.engine_lane.value}"],
    )
    manifest = _manifest(
        config=config,
        strategy_spec=strategy_spec,
        params=params,
        run_id=run_id,
        status=status,
        context=simulation.context,
        metrics=simulation.metrics,
        artifacts=artifacts,
        failure_reason=None,
    )
    _write_json(run_dir / "run_manifest.json", manifest.model_dump(mode="json"))
    artifacts["run_manifest"] = _artifact_ref(run_dir, run_dir / "run_manifest.json", "run_manifest")
    return BacktestRunResult(
        run_dir=str(run_dir),
        manifest=manifest.model_copy(update={"artifacts": {key: value for key, value in artifacts.items() if key != "run_manifest"}}),
        metrics=simulation.metrics,
    )


def _write_failure_artifacts(
    *,
    config: BacktestRunConfig,
    strategy_spec: StrategySpec,
    params: dict[str, Any],
    panel_rows: list[dict[str, Any]],
    run_id: str,
    run_dir: Path,
    engine_lane: EngineLane,
    failure_reason: str,
) -> BacktestRunResult:
    timestamps = [_parse_timestamp(row["ts"]) for row in panel_rows if "ts" in row] or [datetime.now(tz=UTC)]
    instruments = sorted({str(row.get("instrument_id", "unknown")) for row in panel_rows}) or ["unknown"]
    metrics = {
        "schema_version": V2_SCHEMA_VERSION,
        "run_id": run_id,
        "status": RunStatus.FAILED.value,
        "failure_reason": failure_reason,
        "gross_only": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    artifacts = _write_common_artifacts(
        run_dir=run_dir,
        strategy_spec=strategy_spec,
        params=params,
        panel_rows=panel_rows,
        validation_manifest=_validation_manifest(config, status=RunStatus.FAILED, failure_reason=failure_reason),
        cost_manifest=_cost_manifest(config, cost_stress=[]),
        metrics=metrics,
        equity_curve=[],
        daily_returns=[],
        trades=[],
        positions=[],
        per_instrument_metrics=[],
        fold_metrics=[],
        cost_stress=[],
        log_lines=[f"run_id={run_id}", f"status=failed", f"failure_reason={failure_reason}", f"engine_lane={engine_lane.value}"],
    )
    context = StrategyContext(
        run_id=run_id,
        experiment_id=config.experiment_id,
        trial_index=config.trial_index,
        archive_snapshot_id=config.archive_snapshot_id,
        universe_snapshot_id=config.universe_snapshot_id,
        data_manifest_id=config.data_manifest_id,
        validation_policy_id=config.validation_policy_id,
        cost_model_id=config.cost_model_id,
        timeframe=strategy_spec.inputs.timeframe,
        venue_scope=config.venue_scope,
        universe_mode=config.universe_mode,
        instrument_count=len(instruments),
        backtest_start=min(timestamps),
        backtest_end=max(timestamps) if max(timestamps) > min(timestamps) else min(timestamps) + timedelta(hours=1),
        lockbox_policy_id=config.lockbox_policy_id,
        lockbox_start=config.lockbox_start,
        lockbox_end=config.lockbox_end,
        data_coverage_min=config.data_coverage_min,
    )
    manifest = _manifest(
        config=config.model_copy(update={"engine_lane": engine_lane}),
        strategy_spec=strategy_spec,
        params=params,
        run_id=run_id,
        status=RunStatus.FAILED,
        context=context,
        metrics=None,
        artifacts=artifacts,
        failure_reason=failure_reason,
    )
    _write_json(run_dir / "run_manifest.json", manifest.model_dump(mode="json"))
    return BacktestRunResult(run_dir=str(run_dir), manifest=manifest, metrics=None)


def _write_common_artifacts(
    *,
    run_dir: Path,
    strategy_spec: StrategySpec,
    params: dict[str, Any],
    panel_rows: list[dict[str, Any]],
    validation_manifest: dict[str, Any],
    cost_manifest: dict[str, Any],
    metrics: dict[str, Any],
    equity_curve: list[dict[str, Any]],
    daily_returns: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    per_instrument_metrics: list[dict[str, Any]],
    fold_metrics: list[dict[str, Any]],
    cost_stress: list[dict[str, Any]],
    log_lines: list[str],
) -> dict[str, RunArtifactRef]:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, RunArtifactRef] = {}
    artifacts["strategy_spec"] = _write_json_artifact(run_dir, "strategy_spec.json", strategy_spec.model_dump(mode="json"), "strategy_spec")
    artifacts["params"] = _write_json_artifact(run_dir, "params.json", params, "params")
    artifacts["data_manifest"] = _write_json_artifact(run_dir, "data_manifest.json", _data_manifest(panel_rows), "data_manifest")
    artifacts["validation_manifest"] = _write_json_artifact(run_dir, "validation_manifest.json", validation_manifest, "validation_manifest")
    artifacts["cost_manifest"] = _write_json_artifact(run_dir, "cost_manifest.json", cost_manifest, "cost_manifest")
    artifacts["metrics"] = _write_json_artifact(run_dir, "metrics.json", metrics, "metrics")
    artifacts["equity_curve"] = _write_parquet_artifact(run_dir, "equity_curve.parquet", equity_curve, "equity_curve", _equity_schema())
    artifacts["daily_returns"] = _write_parquet_artifact(run_dir, "daily_returns.parquet", daily_returns, "daily_returns", _daily_schema())
    artifacts["trades"] = _write_parquet_artifact(run_dir, "trades.parquet", trades, "trades", _trades_schema())
    artifacts["positions"] = _write_parquet_artifact(run_dir, "positions.parquet", positions, "positions", _positions_schema())
    artifacts["per_instrument_metrics"] = _write_parquet_artifact(run_dir, "per_instrument_metrics.parquet", per_instrument_metrics, "per_instrument_metrics", _per_instrument_schema())
    artifacts["fold_metrics"] = _write_parquet_artifact(run_dir, "fold_metrics.parquet", fold_metrics, "fold_metrics", _fold_schema())
    artifacts["cost_stress"] = _write_parquet_artifact(run_dir, "cost_stress.parquet", cost_stress, "cost_stress", _cost_stress_schema())
    log_path = logs_dir / "log.txt"
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    artifacts["log"] = _artifact_ref(run_dir, log_path, "log")
    return artifacts


def _manifest(
    *,
    config: BacktestRunConfig,
    strategy_spec: StrategySpec,
    params: dict[str, Any],
    run_id: str,
    status: RunStatus,
    context: StrategyContext,
    metrics: BacktestMetrics | None,
    artifacts: dict[str, RunArtifactRef],
    failure_reason: str | None,
) -> RunManifest:
    params_hash = _canonical_json_hash(params)
    return RunManifest(
        run_id=run_id,
        experiment_id=config.experiment_id,
        trial_index=config.trial_index,
        agent_or_user=config.agent_or_user,
        status=status,
        engine_lane=config.engine_lane,
        git_sha=config.git_sha if config.git_sha != "unknown" else _git_sha(),
        environment_hash=config.environment_hash or _environment_hash(),
        strategy_id=strategy_spec.strategy_id,
        strategy_version=strategy_spec.version,
        strategy_hash=strategy_spec.spec_hash,
        strategy_spec_hash=strategy_spec.spec_hash,
        params_hash=params_hash,
        archive_snapshot_id=config.archive_snapshot_id,
        universe_snapshot_id=config.universe_snapshot_id,
        data_manifest_id=config.data_manifest_id,
        data_manifest_hash=config.data_manifest_hash,
        validation_manifest_hash=config.validation_manifest_hash,
        cost_manifest_hash=config.cost_manifest_hash,
        universe_mode=config.universe_mode,
        venue_scope=config.venue_scope,
        instrument_count=context.instrument_count,
        timeframe=strategy_spec.inputs.timeframe,
        backtest_start=context.backtest_start,
        backtest_end=context.backtest_end,
        usable_months=_usable_months(context.backtest_start, context.backtest_end),
        lockbox_policy_id=config.lockbox_policy_id,
        lockbox_start=config.lockbox_start,
        lockbox_end=config.lockbox_end,
        data_coverage_min=config.data_coverage_min,
        cost_model_id=config.cost_model_id,
        cost_model_hash=_effective_cost_model(config).config_hash,
        account_notional_usd=_effective_cost_model(config).account_notional_usd,
        validation_policy_id=config.validation_policy_id,
        validation_status=ValidationStatus.PASS if status == RunStatus.SUCCEEDED else ValidationStatus.FAIL,
        missing_data_policy=config.missing_data_policy,
        price_basis=strategy_spec.execution.price_basis.value,
        failure_reason=failure_reason,
        metrics=metrics,
        artifacts=artifacts,
    )


def _data_manifest(panel_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": V2_SCHEMA_VERSION,
        "row_count": len(panel_rows),
        "panel_hash": _canonical_json_hash(panel_rows),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _validation_manifest(
    config: BacktestRunConfig,
    *,
    status: RunStatus,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": V2_SCHEMA_VERSION,
        "validation_policy_id": config.validation_policy_id,
        "status": "pass" if status == RunStatus.SUCCEEDED else "fail",
        "missing_data_policy": config.missing_data_policy.value,
        "failure_reason": failure_reason,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _cost_manifest(config: BacktestRunConfig, *, cost_stress: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = build_cost_manifest(
        config=_effective_cost_model(config),
        stress_rows=tuple(cost_stress),
    )
    manifest["gross_and_net_required"] = config.require_net_metrics
    manifest["phase"] = "phase12_cost_funding_slippage_impact_capacity"
    return manifest


def _write_json_artifact(run_dir: Path, filename: str, payload: Any, name: str) -> RunArtifactRef:
    path = run_dir / filename
    _write_json(path, payload)
    return _artifact_ref(run_dir, path, name)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_parquet_artifact(
    run_dir: Path,
    filename: str,
    rows: list[dict[str, Any]],
    name: str,
    schema: pa.Schema,
) -> RunArtifactRef:
    path = run_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema) if rows else pa.Table.from_pylist([], schema=schema)
    pq.write_table(table, path, compression="zstd")
    return _artifact_ref(run_dir, path, name, row_count=len(rows))


def _artifact_ref(run_dir: Path, path: Path, name: str, row_count: int | None = None) -> RunArtifactRef:
    return RunArtifactRef(
        name=name,
        path=path.relative_to(run_dir).as_posix(),
        sha256=_file_sha256(path),
        row_count=row_count,
    )


def _run_dir(output_root: str | Path, run_id: str) -> Path:
    if not _SAFE_RUN_ID.fullmatch(run_id):
        raise BacktestEngineError(f"unsafe_run_id: {run_id}")
    root = Path(output_root).resolve()
    run_dir = (root / run_id).resolve()
    if not str(run_dir).startswith(str(root)):
        raise BacktestEngineError("run_dir_escapes_output_root")
    return run_dir


def _deterministic_run_id(
    config: BacktestRunConfig,
    strategy_spec: StrategySpec,
    params: Mapping[str, Any],
    panel_rows: list[dict[str, Any]],
) -> str:
    identity = {
        "experiment_id": config.experiment_id,
        "trial_index": config.trial_index,
        "archive_snapshot_id": config.archive_snapshot_id,
        "universe_snapshot_id": config.universe_snapshot_id,
        "data_manifest_id": config.data_manifest_id,
        "strategy_spec_hash": strategy_spec.spec_hash,
        "params_hash": _canonical_json_hash(params),
        "panel_hash": _canonical_json_hash(panel_rows),
        "engine_lane": config.engine_lane.value,
        "cost_model_id": config.cost_model_id,
        "cost_model_hash": _effective_cost_model(config).config_hash,
    }
    return "run-" + _canonical_json_hash(identity)[:24]


def _canonical_json_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _environment_hash() -> str:
    payload = {
        "python": sys.version,
        "platform": platform.platform(),
        "schema_version": V2_SCHEMA_VERSION,
    }
    return _canonical_json_hash(payload)


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return os.environ.get("GIT_SHA", "unknown")
    if result.returncode == 0:
        return result.stdout.strip() or "unknown"
    return os.environ.get("GIT_SHA", "unknown")


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, str):
        return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    raise BacktestEngineError(f"unsupported timestamp value: {value!r}")


def _usable_months(start: datetime, end: datetime) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def _equity_schema() -> pa.Schema:
    return pa.schema(
        [
            ("ts", pa.string()),
            ("gross_return", pa.float64()),
            ("net_return", pa.float64()),
            ("gross_equity", pa.float64()),
            ("net_equity", pa.float64()),
            ("turnover", pa.float64()),
            ("fee_cost", pa.float64()),
            ("spread_cost", pa.float64()),
            ("slippage_cost", pa.float64()),
            ("impact_cost", pa.float64()),
            ("transaction_cost", pa.float64()),
            ("funding_pnl", pa.float64()),
            ("capacity_blocked_count", pa.int64()),
            ("cost_scenario", pa.string()),
            ("gross_exposure", pa.float64()),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
        ]
    )


def _daily_schema() -> pa.Schema:
    return pa.schema(
        [
            ("date", pa.string()),
            ("gross_return", pa.float64()),
            ("net_return", pa.float64()),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
        ]
    )


def _trades_schema() -> pa.Schema:
    return pa.schema(
        [
            ("ts", pa.string()),
            ("instrument_id", pa.string()),
            ("from_weight", pa.float64()),
            ("to_weight", pa.float64()),
            ("turnover", pa.float64()),
            ("account_notional_usd", pa.float64()),
            ("trade_notional_usd", pa.float64()),
            ("side", pa.string()),
            ("price_basis", pa.string()),
            ("fee_cost", pa.float64()),
            ("spread_cost", pa.float64()),
            ("slippage_cost", pa.float64()),
            ("impact_cost", pa.float64()),
            ("transaction_cost", pa.float64()),
            ("participation_rate", pa.float64()),
            ("capacity_blocked", pa.bool_()),
            ("capacity_reason", pa.string()),
            ("cost_scenario", pa.string()),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
            ("candidate_evidence", pa.bool_()),
            ("candidate_pack_eligible", pa.bool_()),
            ("live_signal", pa.bool_()),
            ("paper_signal", pa.bool_()),
            ("sizing_instruction", pa.bool_()),
            ("order_placement_instruction", pa.bool_()),
            ("runtime_mode_change", pa.bool_()),
        ]
    )


def _positions_schema() -> pa.Schema:
    return pa.schema(
        [
            ("ts", pa.string()),
            ("instrument_id", pa.string()),
            ("applied_weight", pa.float64()),
            ("target_weight", pa.float64()),
            ("signal", pa.float64()),
            ("side", pa.string()),
            ("price_basis", pa.string()),
            ("price_return", pa.float64()),
            ("gross_pnl", pa.float64()),
            ("funding_pnl", pa.float64()),
            ("funding_rate", pa.float64()),
            ("account_notional_usd", pa.float64()),
            ("trade_notional_usd", pa.float64()),
            ("fee_cost", pa.float64()),
            ("spread_cost", pa.float64()),
            ("slippage_cost", pa.float64()),
            ("impact_cost", pa.float64()),
            ("transaction_cost", pa.float64()),
            ("volume_notional", pa.float64()),
            ("participation_rate", pa.float64()),
            ("capacity_blocked", pa.bool_()),
            ("capacity_reason", pa.string()),
            ("cost_scenario", pa.string()),
            ("net_pnl", pa.float64()),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
            ("candidate_evidence", pa.bool_()),
            ("candidate_pack_eligible", pa.bool_()),
            ("live_signal", pa.bool_()),
            ("paper_signal", pa.bool_()),
            ("sizing_instruction", pa.bool_()),
            ("order_placement_instruction", pa.bool_()),
            ("runtime_mode_change", pa.bool_()),
        ]
    )


def _per_instrument_schema() -> pa.Schema:
    return pa.schema(
        [
            ("instrument_id", pa.string()),
            ("gross_pnl", pa.float64()),
            ("net_pnl", pa.float64()),
            ("fee_cost", pa.float64()),
            ("spread_cost", pa.float64()),
            ("slippage_cost", pa.float64()),
            ("impact_cost", pa.float64()),
            ("transaction_cost", pa.float64()),
            ("funding_pnl", pa.float64()),
            ("turnover", pa.float64()),
            ("trade_count", pa.float64()),
            ("capacity_blocked_count", pa.float64()),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
        ]
    )


def _fold_schema() -> pa.Schema:
    return pa.schema(
        [
            ("fold_id", pa.string()),
            ("fold_family", pa.string()),
            ("start_ts", pa.string()),
            ("end_ts", pa.string()),
            ("gross_return", pa.float64()),
            ("net_return", pa.float64()),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
        ]
    )


def _cost_stress_schema() -> pa.Schema:
    return pa.schema(
        [
            ("scenario_id", pa.string()),
            ("cost_model_id", pa.string()),
            ("cost_model_hash", pa.string()),
            ("cost_multiplier", pa.float64()),
            ("gross_return", pa.float64()),
            ("net_return", pa.float64()),
            ("gross_equity_final", pa.float64()),
            ("net_equity_final", pa.float64()),
            ("total_fee_cost", pa.float64()),
            ("total_spread_cost", pa.float64()),
            ("total_slippage_cost", pa.float64()),
            ("total_impact_cost", pa.float64()),
            ("total_transaction_cost", pa.float64()),
            ("total_funding_pnl", pa.float64()),
            ("total_turnover", pa.float64()),
            ("trade_count", pa.int64()),
            ("capacity_blocked_count", pa.int64()),
            ("cost_fragile_warning", pa.bool_()),
            ("cost_dependent_failure", pa.bool_()),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
        ]
    )
