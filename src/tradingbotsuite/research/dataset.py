from __future__ import annotations

import asyncio
import hashlib
import json
from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.adapters.binance import BinanceCandleClient
from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.acceptance import RuleAcceptanceSettings, evaluate_rule_acceptance
from tradingbotsuite.core.features import (
    RESEARCH_FEATURE_COLUMNS,
    VolatilityFeatureConfig,
    bar_close_time_ms,
    build_extended_feature_snapshot,
    label_position_pnl_multiple,
    numeric_feature_map,
)
from tradingbotsuite.core.math import BAR_INTERVAL_MS, atr_wilder, build_barriers, build_vertical_barrier, evaluate_exit_on_bar, hurst_exponent
from tradingbotsuite.core.models import Bar, ExitReason, PositionState, SignalDirection, TradeStatus
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research.config import ResearchPlan

DATASET_MANIFEST_VERSION = "v2-dataset-manifest-1"
LABEL_VERSION = "triple_barrier_live_parity_v1"
LABEL_OUTCOME_COLUMNS = [
    "gross_return",
    "fees_bps",
    "slippage_bps",
    "funding_paid_or_received",
    "time_in_trade",
    "max_adverse_excursion",
    "max_favorable_excursion",
    "barrier_hit_type",
]
RESEARCH_SIGNAL_SOURCES = {
    "tradingview",
    "tradingview_chart_export",
    "tradingview_strategy_export",
    "tradingview_alert_log",
}
BTC_PHASE_1_SYMBOL = "BTCUSDT"
CONTEXT_MANIFEST_FIELDS = {
    "funding_context": (
        "funding_rate",
        "funding_rate_change",
        "time_to_next_funding_ms",
    ),
    "open_interest_context": (
        "open_interest",
        "open_interest_change",
        "open_interest_change_pct",
        "open_interest_value",
    ),
    "premium_context": (
        "mark_price",
        "index_price",
        "basis",
        "basis_rate",
        "premium_close",
    ),
}


@dataclass(frozen=True, slots=True)
class DatasetBuildResult:
    dataset_path: Path
    manifest_path: Path
    row_count: int


@dataclass(frozen=True, slots=True)
class LabelOutcome:
    exit_reason: ExitReason
    pnl_multiple: Decimal
    gross_return: Decimal
    exit_price: Decimal
    exit_time_ms: int
    time_in_trade: Decimal
    time_in_trade_bars: int
    max_adverse_excursion: Decimal
    max_favorable_excursion: Decimal
    barrier_hit_type: str


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decimal_or_none(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _signed_return_fraction(*, direction: SignalDirection, entry_price: Decimal, exit_price: Decimal) -> Decimal:
    if entry_price <= 0:
        return Decimal("0")
    if direction == SignalDirection.LONG:
        return (exit_price - entry_price) / entry_price
    return (entry_price - exit_price) / entry_price


def _funding_paid_or_received(
    *,
    direction: SignalDirection,
    funding_rate: Decimal | None,
    time_in_trade_hours: Decimal,
) -> Decimal | None:
    if funding_rate is None:
        return None
    direction_sign = Decimal("1") if direction == SignalDirection.LONG else Decimal("-1")
    funding_cost = direction_sign * funding_rate * (time_in_trade_hours / Decimal("8"))
    return -funding_cost


def _mfe_mae_update(
    *,
    direction: SignalDirection,
    entry_price: Decimal,
    atr: Decimal,
    bar: Bar,
    current_mfe: Decimal,
    current_mae: Decimal,
) -> tuple[Decimal, Decimal]:
    if atr <= 0:
        return current_mfe, current_mae
    if direction == SignalDirection.LONG:
        favorable = (bar.high - entry_price) / atr
        adverse = (entry_price - bar.low) / atr
    else:
        favorable = (entry_price - bar.low) / atr
        adverse = (bar.high - entry_price) / atr
    return max(current_mfe, favorable, Decimal("0")), max(current_mae, adverse, Decimal("0"))


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload or {}, default=str, sort_keys=True)


def _field_count_payload(frame: pd.DataFrame, *, prefix: str) -> dict[str, int]:
    return {
        column: int(frame[column].notna().sum())
        for column in frame.columns
        if column.startswith(prefix)
    }


def _context_manifest_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for context_name, field_names in CONTEXT_MANIFEST_FIELDS.items():
        contexts = [
            record.get(context_name)
            for record in records
            if isinstance(record.get(context_name), dict)
        ]
        source_counts: dict[str, int] = {}
        source_error_counts: dict[str, int] = {}
        current_source_error_counts: dict[str, int] = {}
        for context in contexts:
            source = str(context.get("source") or "unspecified")
            source_counts[source] = source_counts.get(source, 0) + 1
            source_error = context.get("source_error")
            if source_error is not None:
                key = str(source_error)
                source_error_counts[key] = source_error_counts.get(key, 0) + 1
            current_source_error = context.get("current_source_error")
            if current_source_error is not None:
                key = str(current_source_error)
                current_source_error_counts[key] = current_source_error_counts.get(key, 0) + 1

        summary[context_name] = {
            "rows_with_context": len(contexts),
            "source_counts": dict(sorted(source_counts.items())),
            "field_available_counts": {
                field_name: sum(1 for context in contexts if context.get(field_name) is not None)
                for field_name in field_names
            },
            "rows_with_source_error": sum(1 for context in contexts if context.get("source_error") is not None),
            "source_error_counts": dict(sorted(source_error_counts.items())),
            "current_source_error_counts": dict(sorted(current_source_error_counts.items())),
            "rows_with_backoff": sum(1 for context in contexts if context.get("backoff_until_ms") is not None),
        }
    return summary


def _label_from_future_bars(
    *,
    signal_direction: SignalDirection,
    entry_price: Decimal,
    atr: Decimal,
    tp_price: Decimal,
    sl_price: Decimal,
    signal_bar_time_ms: int,
    future_bars: list[Bar],
    vertical_barrier_time_ms: int,
) -> LabelOutcome | None:
    position = PositionState(
        symbol="BTCUSDT",
        status=TradeStatus.OPEN,
        direction=signal_direction,
        position_size=Decimal("1"),
        entry_price=entry_price,
        entry_time_ms=bar_close_time_ms(signal_bar_time_ms),
        entry_bar_time_ms=signal_bar_time_ms,
        entry_atr=atr,
        tp_price=tp_price,
        sl_price=sl_price,
        vertical_barrier_time_ms=vertical_barrier_time_ms,
    )
    max_favorable_excursion = Decimal("0")
    max_adverse_excursion = Decimal("0")
    for bars_held, bar in enumerate(future_bars, start=1):
        max_favorable_excursion, max_adverse_excursion = _mfe_mae_update(
            direction=signal_direction,
            entry_price=entry_price,
            atr=atr,
            bar=bar,
            current_mfe=max_favorable_excursion,
            current_mae=max_adverse_excursion,
        )
        exit_time_ms = bar_close_time_ms(bar.time_ms)
        exit_reason = evaluate_exit_on_bar(position, bar, exit_time_ms)
        if exit_reason is None:
            continue
        if exit_reason == ExitReason.TAKE_PROFIT:
            exit_price = tp_price
        elif exit_reason == ExitReason.STOP_LOSS:
            exit_price = sl_price
        else:
            exit_price = bar.close
        time_in_trade = Decimal(exit_time_ms - bar_close_time_ms(signal_bar_time_ms)) / Decimal(60 * 60 * 1000)
        return LabelOutcome(
            exit_reason=exit_reason,
            pnl_multiple=label_position_pnl_multiple(
                direction=signal_direction,
                entry_price=entry_price,
                exit_price=exit_price,
                atr=atr,
            ),
            gross_return=_signed_return_fraction(
                direction=signal_direction,
                entry_price=entry_price,
                exit_price=exit_price,
            ),
            exit_price=exit_price,
            exit_time_ms=exit_time_ms,
            time_in_trade=time_in_trade,
            time_in_trade_bars=bars_held,
            max_adverse_excursion=max_adverse_excursion,
            max_favorable_excursion=max_favorable_excursion,
            barrier_hit_type=str(exit_reason),
        )
    return None


class ResearchDatasetBuilder:
    def __init__(
        self,
        *,
        config: AppConfig,
        plan: ResearchPlan,
        store: SQLiteStore,
        candle_client: BinanceCandleClient,
    ):
        self.config = config
        self.plan = plan
        self.store = store
        self.candle_client = candle_client

    async def build(self) -> DatasetBuildResult:
        if self.plan.symbol.upper() != BTC_PHASE_1_SYMBOL:
            raise ValueError("Phase 1 research dataset builds are BTCUSDT-only")
        await self.store.initialize()
        all_rows = sorted(await self.store.list_research_signals(self.plan.symbol), key=lambda row: int(row["tv_bar_time_ms"]))
        rows = [row for row in all_rows if str(row["source"]) in RESEARCH_SIGNAL_SOURCES]
        rows = self._dedupe_research_signals(rows)
        if not rows:
            raise ValueError(f"no signals found for {self.plan.symbol}")

        records: list[dict[str, Any]] = []
        volatility_config = VolatilityFeatureConfig(
            realized_vol_window_bars=self.plan.features.realized_vol_window_bars,
            atr_percentile_window_bars=self.plan.features.atr_percentile_window_bars,
            volatility_shock_window_bars=self.plan.features.volatility_shock_window_bars,
            volatility_shock_zscore_threshold=self.plan.features.volatility_shock_zscore_threshold,
        )
        preloaded_bars, bar_times = await self._preload_bar_history(rows)
        contexts_by_signal_time = await self._prefetch_contexts(rows)
        for row in rows:
            signal_time_ms = int(row["tv_bar_time_ms"])
            raw_payload = row.get("raw_payload") or {}
            decision_packet = row.get("decision_packet") or {}
            decision_snapshot = decision_packet.get("feature_snapshot") or {}
            contexts = contexts_by_signal_time.get(signal_time_ms, {})
            bars = self._slice_historical_bars(preloaded_bars, bar_times, signal_time_ms)
            if len(bars) < max(self.config.strategy.atr_length + 1, self.config.strategy.hurst_window_bars):
                continue
            latest_bar = bars[-1]
            if latest_bar.time_ms != signal_time_ms:
                continue
            if latest_bar.time_ms > signal_time_ms:
                raise ValueError("historical feature bars include a future bar")
            direction = SignalDirection(str(row["direction"]))
            atr = atr_wilder(bars, self.config.strategy.atr_length)
            hurst = hurst_exponent([bar.close for bar in bars[-self.config.strategy.hurst_window_bars :]])
            funding_context = contexts.get("funding_context")
            open_interest_context = contexts.get("open_interest_context")
            premium_context = contexts.get("premium_context")
            microstructure_context = decision_snapshot.get("microstructure")
            basis_context = decision_snapshot.get("basis")
            feature_snapshot = build_extended_feature_snapshot(
                signal_direction=direction,
                signal_time_ms=signal_time_ms,
                latest_bar=latest_bar,
                bars=bars,
                atr=atr,
                atr_length=self.config.strategy.atr_length,
                hurst=hurst,
                microstructure=microstructure_context,
                basis_snapshot=basis_context,
                funding_context=funding_context,
                open_interest_context=open_interest_context,
                premium_context=premium_context,
                primary_window_seconds=self.config.strategy.microstructure_primary_window_seconds,
                volatility_config=volatility_config,
            )
            feature_snapshot["rule_acceptance"] = evaluate_rule_acceptance(
                feature_snapshot,
                RuleAcceptanceSettings(**asdict(self.plan.acceptance_filter)),
            )
            numeric_features = numeric_feature_map(feature_snapshot)
            normalized_entry_price = _decimal_or_none(raw_payload.get("normalized_entry_price"))
            entry_price = normalized_entry_price if normalized_entry_price is not None else latest_bar.close
            entry_price_source = str(raw_payload.get("entry_price_source") or "signal_bar_close")
            tp_price, sl_price = build_barriers(
                entry_price=entry_price,
                atr=atr,
                direction=direction,
                tp_multiple=self.config.strategy.take_profit_atr_multiple,
                sl_multiple=self.config.strategy.stop_loss_atr_multiple,
                price_tick=self.config.strategy.price_tick,
            )
            future_bars = self._slice_future_bars(preloaded_bars, bar_times, signal_time_ms)
            label_outcome = _label_from_future_bars(
                signal_direction=direction,
                entry_price=entry_price,
                atr=atr,
                tp_price=tp_price,
                sl_price=sl_price,
                signal_bar_time_ms=signal_time_ms,
                future_bars=future_bars,
                vertical_barrier_time_ms=build_vertical_barrier(signal_time_ms, self.config.strategy.time_barrier_bars),
            )
            if label_outcome is None:
                continue
            if future_bars and future_bars[0].time_ms <= signal_time_ms:
                raise ValueError("label future bars include the signal bar or an earlier bar")

            basis_bps = _decimal_or_none((basis_context or {}).get("basis_bps"))
            primary_window = (microstructure_context or {}).get("windows", {}).get(
                str(self.config.strategy.microstructure_primary_window_seconds),
                {},
            )
            funding_paid_or_received = _funding_paid_or_received(
                direction=direction,
                funding_rate=_decimal_or_none((funding_context or {}).get("funding_rate")),
                time_in_trade_hours=label_outcome.time_in_trade,
            )
            record = {
                "signal_id": row["signal_id"],
                "source": row["source"],
                "source_mode": str(raw_payload.get("source_mode") or row["source"]),
                "strategy_version": raw_payload.get("strategy_version"),
                "import_batch_id": raw_payload.get("import_batch_id"),
                "source_row_number": raw_payload.get("source_row_number"),
                "asset_symbol": row["symbol"],
                "symbol": row["symbol"],
                "direction": row["direction"],
                "tv_bar_time_ms": signal_time_ms,
                "received_time_ms": int(row["received_time_ms"]),
                "signal_bar_open_time_ms": latest_bar.time_ms,
                "signal_bar_close_time_ms": bar_close_time_ms(latest_bar.time_ms),
                "signal_bar_open": float(latest_bar.open),
                "signal_bar_high": float(latest_bar.high),
                "signal_bar_low": float(latest_bar.low),
                "signal_bar_close": float(latest_bar.close),
                "signal_bar_volume": float(latest_bar.volume),
                "historical_feature_end_time_ms": latest_bar.time_ms,
                "historical_feature_bar_count": len(bars),
                "label_future_start_time_ms": future_bars[0].time_ms if future_bars else None,
                "label_future_end_time_ms": future_bars[-1].time_ms if future_bars else None,
                "label_future_bar_count": len(future_bars),
                "feature_version": feature_snapshot["feature_version"],
                "label_version": LABEL_VERSION,
                "model_version": "observe_only",
                "calibration_version": "none",
                "v1_baseline_accept": bool(row.get("accepted")) if row.get("accepted") is not None else False,
                "v1_rejection_reason": row.get("rejection_reason"),
                "entry_price": float(entry_price),
                "entry_price_source": entry_price_source,
                "signal_marker_price": float(_decimal_or_none(raw_payload.get("signal_marker_price")) or 0) if raw_payload.get("signal_marker_price") is not None else None,
                "next_bar_open": float(_decimal_or_none(raw_payload.get("next_bar_open")) or 0) if raw_payload.get("next_bar_open") is not None else None,
                "tp_price": float(tp_price),
                "sl_price": float(sl_price),
                "label_exit_reason": str(label_outcome.exit_reason),
                "label_accept": 1 if label_outcome.exit_reason == ExitReason.TAKE_PROFIT else 0,
                "label_pnl_multiple": float(label_outcome.pnl_multiple),
                "label_exit_price": float(label_outcome.exit_price),
                "label_exit_time_ms": label_outcome.exit_time_ms,
                "gross_return": float(label_outcome.gross_return),
                "fees_bps": float(self.plan.evaluation.fee_bps),
                "slippage_bps": float(self.plan.evaluation.slippage_bps),
                "funding_paid_or_received": float(funding_paid_or_received) if funding_paid_or_received is not None else None,
                "time_in_trade": float(label_outcome.time_in_trade),
                "time_in_trade_bars": label_outcome.time_in_trade_bars,
                "max_adverse_excursion": float(label_outcome.max_adverse_excursion),
                "max_favorable_excursion": float(label_outcome.max_favorable_excursion),
                "barrier_hit_type": label_outcome.barrier_hit_type,
                "raw_basis_bps": float(basis_bps) if basis_bps is not None else None,
                "raw_funding_rate": float(_decimal_or_none((funding_context or {}).get("funding_rate"))) if (funding_context or {}).get("funding_rate") is not None else None,
                "raw_funding_rate_change": float(_decimal_or_none((funding_context or {}).get("funding_rate_change"))) if (funding_context or {}).get("funding_rate_change") is not None else None,
                "raw_time_to_next_funding_ms": (funding_context or {}).get("time_to_next_funding_ms"),
                "raw_open_interest": float(_decimal_or_none((open_interest_context or {}).get("open_interest"))) if (open_interest_context or {}).get("open_interest") is not None else None,
                "raw_open_interest_change": float(_decimal_or_none((open_interest_context or {}).get("open_interest_change"))) if (open_interest_context or {}).get("open_interest_change") is not None else None,
                "raw_open_interest_change_pct": float(_decimal_or_none((open_interest_context or {}).get("open_interest_change_pct"))) if (open_interest_context or {}).get("open_interest_change_pct") is not None else None,
                "raw_open_interest_value": float(_decimal_or_none((open_interest_context or {}).get("open_interest_value"))) if (open_interest_context or {}).get("open_interest_value") is not None else None,
                "raw_premium_basis_rate": float(_decimal_or_none((premium_context or {}).get("basis_rate"))) if (premium_context or {}).get("basis_rate") is not None else None,
                "raw_premium_basis_abs": float(_decimal_or_none((premium_context or {}).get("basis"))) if (premium_context or {}).get("basis") is not None else None,
                "raw_premium_close": float(_decimal_or_none((premium_context or {}).get("premium_close"))) if (premium_context or {}).get("premium_close") is not None else None,
                "raw_mark_price": float(_decimal_or_none((premium_context or {}).get("mark_price"))) if (premium_context or {}).get("mark_price") is not None else None,
                "raw_index_price": float(_decimal_or_none((premium_context or {}).get("index_price"))) if (premium_context or {}).get("index_price") is not None else None,
                "raw_primary_signed_imbalance_ratio": float(_decimal_or_none(primary_window.get("signed_ratio"))) if primary_window.get("signed_ratio") is not None else None,
                "raw_spread_bps": float(_decimal_or_none((microstructure_context or {}).get("spread_bps"))) if (microstructure_context or {}).get("spread_bps") is not None else None,
                "rule_acceptance_total_score": float((feature_snapshot.get("rule_acceptance") or {}).get("total_score") or 0.0),
                "rule_acceptance_core_score": float((feature_snapshot.get("rule_acceptance") or {}).get("core_score") or 0.0),
                "rule_acceptance_perp_score": float((feature_snapshot.get("rule_acceptance") or {}).get("perp_score") or 0.0),
                "rule_acceptance_accept_candidate": 1 if ((feature_snapshot.get("rule_acceptance") or {}).get("accept_candidate")) else 0,
                "rule_acceptance_liquidity_status": (feature_snapshot.get("rule_acceptance") or {}).get("liquidity_status"),
                "funding_context": funding_context,
                "open_interest_context": open_interest_context,
                "premium_context": premium_context,
            }
            record.update(numeric_features)
            record["feature_snapshot_json"] = _json_dumps(feature_snapshot)
            record["raw_signal_payload_json"] = _json_dumps(raw_payload)
            record["microstructure_context_json"] = _json_dumps(microstructure_context)
            record["basis_context_json"] = _json_dumps(basis_context)
            record["funding_context_json"] = _json_dumps(funding_context)
            record["open_interest_context_json"] = _json_dumps(open_interest_context)
            record["premium_context_json"] = _json_dumps(premium_context)
            record["decision_context_present"] = decision_snapshot != {}
            records.append(record)

        if not records:
            raise ValueError("dataset build produced no labeled rows")

        frame = pd.DataFrame(records).sort_values("tv_bar_time_ms").reset_index(drop=True)
        for column in RESEARCH_FEATURE_COLUMNS:
            if column not in frame.columns:
                frame[column] = 0.0
        missing_feature_rates = {
            column: float(frame[column].mean())
            for column in frame.columns
            if column.startswith("missing_")
        }
        source_counts = {
            str(source): int(count)
            for source, count in frame["source"].value_counts(dropna=False).sort_index().items()
        }
        source_mode_counts = {
            str(source): int(count)
            for source, count in frame["source_mode"].value_counts(dropna=False).sort_index().items()
        }
        strategy_version_counts = {
            str(strategy_version): int(count)
            for strategy_version, count in frame["strategy_version"].fillna("none").value_counts(dropna=False).sort_index().items()
        }
        class_balance = {
            "label_accept_0": int((frame["label_accept"] == 0).sum()),
            "label_accept_1": int((frame["label_accept"] == 1).sum()),
            "positive_rate": float(frame["label_accept"].mean()),
        }
        planned_split_summary = self._planned_split_summary(len(frame))
        exchange_context_summary = _context_manifest_summary(records)
        raw_context_available_counts = {
            **_field_count_payload(frame, prefix="raw_"),
            "decision_context_present": int(frame["decision_context_present"].sum()),
        }
        frame = frame.drop(columns=["funding_context", "open_interest_context", "premium_context"])

        output_dir = self.config.research.output_dir / self.plan.version
        output_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = output_dir / f"{self.plan.symbol.lower()}_dataset.parquet"
        frame.to_parquet(dataset_path, index=False)
        manifest = {
            "dataset_manifest_version": DATASET_MANIFEST_VERSION,
            "plan_version": self.plan.version,
            "plan_sha256": self.plan.plan_sha256(),
            "research_only": True,
            "symbol": self.plan.symbol,
            "asset_scope": [self.plan.symbol],
            "row_count": len(frame),
            "dataset_path": str(dataset_path),
            "dataset_sha256": _hash_file(dataset_path),
            "feature_version": frame["feature_version"].iloc[0],
            "label_version": LABEL_VERSION,
            "label_outcome_fields": [column for column in LABEL_OUTCOME_COLUMNS if column in frame.columns],
            "source_counts": source_counts,
            "source_mode_counts": source_mode_counts,
            "strategy_version_counts": strategy_version_counts,
            "class_balance": class_balance,
            "missing_feature_rates": missing_feature_rates,
            "raw_context_available_counts": raw_context_available_counts,
            "exchange_context_summary": exchange_context_summary,
            "planned_split_summary": planned_split_summary,
            "config": self.plan.to_payload(),
        }
        manifest_path = output_dir / "dataset_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return DatasetBuildResult(dataset_path=dataset_path, manifest_path=manifest_path, row_count=len(frame))

    async def _prefetch_contexts(self, rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        signal_times = sorted({int(row["tv_bar_time_ms"]) for row in rows})
        contexts_by_signal_time: dict[int, dict[str, Any]] = {}
        semaphore = asyncio.Semaphore(16)

        async def fetch_one(signal_time_ms: int) -> None:
            async with semaphore:
                funding_context = await self.candle_client.fetch_funding_context(
                    self.plan.symbol,
                    as_of_ms=signal_time_ms,
                    history_limit=self.plan.dataset.funding_history_limit,
                )
                open_interest_context = await self.candle_client.fetch_open_interest_context(
                    self.plan.symbol,
                    as_of_ms=signal_time_ms,
                    period=self.plan.dataset.open_interest_period,
                    lookback_points=self.plan.dataset.open_interest_lookback_points,
                )
                premium_context = await self.candle_client.fetch_premium_context(
                    self.plan.symbol,
                    as_of_ms=signal_time_ms,
                    interval=self.plan.dataset.premium_interval,
                )
                contexts_by_signal_time[signal_time_ms] = {
                    "funding_context": funding_context,
                    "open_interest_context": open_interest_context,
                    "premium_context": premium_context,
                }

        await asyncio.gather(*(fetch_one(signal_time_ms) for signal_time_ms in signal_times))
        return contexts_by_signal_time

    def _dedupe_research_signals(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: dict[tuple[Any, ...], dict[str, Any]] = {}
        passthrough: list[dict[str, Any]] = []
        for row in rows:
            raw_payload = row.get("raw_payload") or {}
            if raw_payload.get("source_mode") != "chart_export":
                passthrough.append(row)
                continue
            key = (
                row["symbol"],
                row["direction"],
                int(row["tv_bar_time_ms"]),
                raw_payload.get("strategy_version"),
            )
            current = selected.get(key)
            current_time = int((current or {}).get("raw_payload", {}).get("import_time_ms") or (current or {}).get("received_time_ms") or 0)
            row_time = int(raw_payload.get("import_time_ms") or row.get("received_time_ms") or 0)
            if current is None or row_time >= current_time:
                selected[key] = row
        return sorted(
            [*passthrough, *selected.values()],
            key=lambda row: (int(row["tv_bar_time_ms"]), str(row["signal_id"])),
        )

    def _planned_split_summary(self, row_count: int) -> dict[str, int]:
        train_rows = max(self.plan.evaluation.min_training_rows, int(row_count * self.plan.evaluation.train_fraction))
        calibration_rows = max(self.plan.evaluation.min_calibration_rows, int(row_count * self.plan.evaluation.calibration_fraction))
        evaluation_rows = max(row_count - train_rows - calibration_rows, 0)
        return {
            "train_rows": min(train_rows, row_count),
            "calibration_rows": min(calibration_rows, max(row_count - min(train_rows, row_count), 0)),
            "evaluation_rows": evaluation_rows,
            "walk_forward_splits": self.plan.evaluation.walk_forward_splits,
        }

    async def _preload_bar_history(self, rows: list[dict[str, Any]]) -> tuple[list[Bar], list[int]]:
        if not rows:
            return [], []
        first_signal_time_ms = int(rows[0]["tv_bar_time_ms"])
        last_signal_time_ms = int(rows[-1]["tv_bar_time_ms"])
        lookback_start_ms = first_signal_time_ms - ((self.plan.dataset.bar_lookback - 1) * BAR_INTERVAL_MS)
        future_end_open_time_ms = last_signal_time_ms + (
            min(self.plan.dataset.future_bar_limit, self.config.strategy.time_barrier_bars) * BAR_INTERVAL_MS
        )
        range_end_ms = future_end_open_time_ms + BAR_INTERVAL_MS - 1
        if hasattr(self.candle_client, "fetch_historical_closed_bar_range"):
            bars = await self.candle_client.fetch_historical_closed_bar_range(
                self.plan.symbol,
                start_time_ms=lookback_start_ms,
                end_time_ms=range_end_ms,
            )
        else:
            bars = await self.candle_client.fetch_historical_closed_bars(
                self.plan.symbol,
                limit=self.plan.dataset.bar_lookback,
                end_time_ms=first_signal_time_ms + BAR_INTERVAL_MS - 1,
            )
        bar_times = [bar.time_ms for bar in bars]
        return bars, bar_times

    def _slice_historical_bars(self, bars: list[Bar], bar_times: list[int], signal_time_ms: int) -> list[Bar]:
        end_index = bisect_right(bar_times, signal_time_ms)
        start_index = max(0, end_index - self.plan.dataset.bar_lookback)
        return bars[start_index:end_index]

    def _slice_future_bars(self, bars: list[Bar], bar_times: list[int], signal_time_ms: int) -> list[Bar]:
        future_limit = min(self.plan.dataset.future_bar_limit, self.config.strategy.time_barrier_bars)
        start_index = bisect_left(bar_times, signal_time_ms + BAR_INTERVAL_MS)
        return bars[start_index : start_index + future_limit]
