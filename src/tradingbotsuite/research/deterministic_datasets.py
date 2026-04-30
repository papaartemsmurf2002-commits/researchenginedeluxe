from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from tradingbotsuite.research.dataset import LABEL_OUTCOME_COLUMNS, LABEL_VERSION

DETERMINISTIC_SWEEP_DATASET_VERSION = "v2-btc-hmm-knn-deterministic-sweep-dataset-1"
DETERMINISTIC_SWEEP_VARIANTS = ("balanced", "sparse_context")
BTC_SYMBOL = "BTCUSDT"
BAR_INTERVAL_MS = 900_000


@dataclass(frozen=True, slots=True)
class DeterministicSweepDatasetResult:
    variant: str
    parquet_path: Path
    csv_path: Path
    manifest_path: Path
    row_count: int
    parquet_sha256: str
    csv_sha256: str
    logical_sha256: str


def build_hmm_knn_sweep_dataset(*, row_count: int = 240, variant: str = "balanced") -> pd.DataFrame:
    """Build an offline deterministic BTC dataset for repeatable HMM/KNN sweeps."""

    if variant not in DETERMINISTIC_SWEEP_VARIANTS:
        raise ValueError(f"variant must be one of {', '.join(DETERMINISTIC_SWEEP_VARIANTS)}")
    if row_count < 80:
        raise ValueError("row_count must be at least 80 for walk-forward HMM/KNN sweeps")

    rows: list[dict[str, Any]] = []
    start_ms = 1_712_649_600_000
    price = 70_000.0
    regime_span = max(row_count // 4, 1)
    for index in range(row_count):
        regime = min(index // regime_span, 3)
        position_in_regime = index % regime_span
        direction = "long" if index % 2 == 0 else "short"
        direction_sign = 1.0 if direction == "long" else -1.0
        regime_payload = _regime_payload(regime=regime, position=position_in_regime)
        drift = float(regime_payload["drift"])
        price = max(1.0, price + drift)
        label_accept = _label_accept(regime=regime, index=index)
        gross_return = 0.012 if label_accept else -0.008
        funding_paid_or_received = _funding_paid_or_received(regime=regime, direction=direction)
        fees_bps = 5.0
        slippage_bps = 5.0
        net_return = gross_return - ((fees_bps + slippage_bps) / 10_000.0) + funding_paid_or_received
        signal_time_ms = start_ms + (index * BAR_INTERVAL_MS)
        label_bars = 8 + (index % 9)
        exit_time_ms = signal_time_ms + (label_bars * BAR_INTERVAL_MS)
        spread_bps = 2.5 + (regime * 1.8)
        signed_flow = 0.32 if drift > 0 else (-0.32 if drift < 0 else 0.0)
        top_of_book = 0.18 if drift > 0 else (-0.18 if drift < 0 else 0.0)
        queue_l5 = 0.14 if drift > 0 else (-0.14 if drift < 0 else 0.0)
        basis_bps = 1.5 + (regime * 1.2)
        premium_basis_rate = basis_bps / 10_000.0
        open_interest_change_pct = 0.035 if regime in {1, 3} else -0.018
        funding_rate = 0.00008 if regime == 1 else (-0.00005 if regime == 2 else 0.00001)
        row = {
            "signal_id": f"det-sweep-{variant}-{index:04d}",
            "source": "external_signal",
            "source_mode": "deterministic_fixture",
            "strategy_version": DETERMINISTIC_SWEEP_DATASET_VERSION,
            "symbol": BTC_SYMBOL,
            "asset_symbol": BTC_SYMBOL,
            "direction": direction,
            "direction_long": 1.0 if direction == "long" else 0.0,
            "signal_bar_time_ms": signal_time_ms,
            "received_time_ms": signal_time_ms + 1_000,
            "signal_bar_open_time_ms": signal_time_ms,
            "signal_bar_close_time_ms": signal_time_ms + BAR_INTERVAL_MS,
            "signal_bar_open": price - (drift / 2.0),
            "signal_bar_high": price + abs(drift) + 35.0,
            "signal_bar_low": price - abs(drift) - 35.0,
            "signal_bar_close": price,
            "signal_bar_volume": 1_000.0 + (index % 24) * 15.0,
            "historical_feature_end_time_ms": signal_time_ms,
            "label_future_start_time_ms": signal_time_ms + BAR_INTERVAL_MS,
            "label_future_end_time_ms": exit_time_ms,
            "label_future_bar_count": label_bars,
            "feature_version": "v2-btc-acceptance-2",
            "label_version": LABEL_VERSION,
            "model_version": "observe_only",
            "calibration_version": "none",
            "entry_price": price,
            "entry_price_source": "deterministic_fixture_signal_close",
            "tp_price": price * (1.0 + 0.01 * direction_sign),
            "sl_price": price * (1.0 - 0.008 * direction_sign),
            "label_interval_start_ms": signal_time_ms + BAR_INTERVAL_MS,
            "label_interval_end_ms": exit_time_ms,
            "label_exit_reason": "take_profit" if label_accept else "stop_loss",
            "label_accept": label_accept,
            "label_pnl_multiple": 1.25 if label_accept else -0.85,
            "label_exit_price": price * (1.0 + (gross_return * direction_sign)),
            "label_exit_time_ms": exit_time_ms,
            "gross_return": gross_return,
            "fees_bps": fees_bps,
            "slippage_bps": slippage_bps,
            "funding_paid_or_received": funding_paid_or_received,
            "time_in_trade": label_bars * 0.25,
            "time_in_trade_bars": label_bars,
            "max_adverse_excursion": 0.22 + (0.04 * (index % 5)),
            "max_favorable_excursion": 0.55 + (0.08 * (index % 7)),
            "barrier_hit_type": "take_profit" if label_accept else "stop_loss",
            "realized_net_return_after_costs": net_return,
            "efficiency_ratio": float(regime_payload["efficiency_ratio"]),
            "choppiness": float(regime_payload["choppiness"]),
            "directional_slope_atr": float(regime_payload["slope"]) * direction_sign,
            "directional_di_spread": float(regime_payload["slope"]) * 20.0,
            "range_width": float(regime_payload["range_width"]),
            "primary_signed_imbalance_ratio": signed_flow,
            "primary_sqrt_signed_imbalance_ratio": signed_flow ** 0.5 if signed_flow > 0 else -((-signed_flow) ** 0.5),
            "primary_trade_sign_acf_lag1": 0.18 if regime in {1, 2} else -0.08,
            "primary_flow_price_alignment_bps": signed_flow * 8.0,
            "primary_impact_efficiency_bps_per_sqrt_notional": 0.0025 + (regime * 0.0004),
            "top_of_book_imbalance": top_of_book,
            "queue_imbalance_l1": top_of_book * 0.8,
            "queue_imbalance_l5": queue_l5,
            "queue_imbalance_l10": queue_l5 * 0.75,
            "spread_bps": spread_bps,
            "basis_bps": basis_bps,
            "funding_rate": funding_rate,
            "funding_rate_change": 0.00001 if index % 2 == 0 else -0.000006,
            "open_interest": 100_000.0 + (index * 25.0),
            "open_interest_change": 75.0 if open_interest_change_pct > 0 else -40.0,
            "open_interest_change_pct": open_interest_change_pct,
            "open_interest_value": (100_000.0 + (index * 25.0)) * price,
            "premium_basis_rate": premium_basis_rate,
            "premium_basis_abs": price * premium_basis_rate,
            "premium_close": premium_basis_rate,
            "mark_price": price * (1.0 + premium_basis_rate),
            "index_price": price,
            "realized_volatility": float(regime_payload["realized_volatility"]),
            "atr_percentile": float(regime_payload["atr_percentile"]),
            "volatility_shock_zscore": float(regime_payload["volatility_shock_zscore"]),
            "raw_signal_payload_json": "{}",
            "feature_snapshot_json": "{}",
            "microstructure_context_json": "{}",
            "funding_context_json": "{}",
            "open_interest_context_json": "{}",
            "premium_context_json": "{}",
            "basis_context_json": "{}",
            "decision_context_present": True,
        }
        _add_raw_and_missing_context(row, variant=variant)
        rows.append(row)

    frame = pd.DataFrame(rows).sort_values(["signal_bar_time_ms", "signal_id"]).reset_index(drop=True)
    return frame[sorted(frame.columns)]


def write_hmm_knn_sweep_dataset(
    *,
    output_dir: Path,
    row_count: int = 240,
    variant: str = "balanced",
) -> DeterministicSweepDatasetResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = build_hmm_knn_sweep_dataset(row_count=row_count, variant=variant)
    stem = f"btcusdt_hmm_knn_sweep_{variant}"
    parquet_path = output_dir / f"{stem}.parquet"
    csv_path = output_dir / f"{stem}.csv"
    manifest_path = output_dir / f"{stem}_manifest.json"

    frame.to_parquet(parquet_path, index=False, compression=None)
    frame.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.12g")
    logical_sha256 = _frame_logical_sha256(frame)
    parquet_sha256 = _file_sha256(parquet_path)
    csv_sha256 = _file_sha256(csv_path)
    missing_feature_rates = {
        column: float(frame[column].mean())
        for column in frame.columns
        if column.startswith("missing_")
    }
    manifest = {
        "dataset_manifest_version": DETERMINISTIC_SWEEP_DATASET_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "symbol": BTC_SYMBOL,
        "asset_scope": [BTC_SYMBOL],
        "variant": variant,
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "parquet_path": str(parquet_path),
        "csv_path": str(csv_path),
        "parquet_sha256": parquet_sha256,
        "csv_sha256": csv_sha256,
        "logical_sha256": logical_sha256,
        "label_version": LABEL_VERSION,
        "label_outcome_fields": [column for column in LABEL_OUTCOME_COLUMNS if column in frame.columns],
        "missing_feature_rates": missing_feature_rates,
        "raw_context_available_counts": _raw_context_available_counts(frame),
        "exchange_context_summary": _exchange_context_summary(frame),
        "source_counts": {"external_signal": int(len(frame))},
        "source_mode_counts": {"deterministic_fixture": int(len(frame))},
        "time_span": {
            "first_signal_time_ms": int(frame["signal_bar_time_ms"].min()),
            "last_signal_time_ms": int(frame["signal_bar_time_ms"].max()),
            "bar_interval_ms": BAR_INTERVAL_MS,
        },
        "determinism": {
            "no_random_inputs": True,
            "sorted_rows": ["signal_bar_time_ms", "signal_id"],
            "sorted_columns": True,
            "logical_hash_basis": "canonical csv payload",
            "live_fetch_used": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return DeterministicSweepDatasetResult(
        variant=variant,
        parquet_path=parquet_path,
        csv_path=csv_path,
        manifest_path=manifest_path,
        row_count=len(frame),
        parquet_sha256=parquet_sha256,
        csv_sha256=csv_sha256,
        logical_sha256=logical_sha256,
    )


def write_hmm_knn_sweep_datasets(
    *,
    output_dir: Path,
    row_count: int = 240,
    variants: Iterable[str] = DETERMINISTIC_SWEEP_VARIANTS,
) -> list[DeterministicSweepDatasetResult]:
    return [
        write_hmm_knn_sweep_dataset(output_dir=output_dir, row_count=row_count, variant=variant)
        for variant in variants
    ]


def _regime_payload(*, regime: int, position: int) -> dict[str, float]:
    cycle = (position % 12) / 12.0
    if regime == 0:
        return {
            "drift": -4.0 if position % 2 else 5.0,
            "efficiency_ratio": 0.22 + cycle * 0.05,
            "choppiness": 62.0 + cycle * 4.0,
            "slope": 0.04,
            "range_width": 0.009,
            "realized_volatility": 0.0045,
            "atr_percentile": 0.28,
            "volatility_shock_zscore": 0.25,
        }
    if regime == 1:
        return {
            "drift": 34.0 + cycle * 8.0,
            "efficiency_ratio": 0.68 + cycle * 0.08,
            "choppiness": 29.0 - cycle * 3.0,
            "slope": 0.72,
            "range_width": 0.015,
            "realized_volatility": 0.009,
            "atr_percentile": 0.64,
            "volatility_shock_zscore": 0.55,
        }
    if regime == 2:
        return {
            "drift": -31.0 - cycle * 7.0,
            "efficiency_ratio": 0.63 + cycle * 0.07,
            "choppiness": 32.0 - cycle * 2.0,
            "slope": 0.66,
            "range_width": 0.017,
            "realized_volatility": 0.011,
            "atr_percentile": 0.70,
            "volatility_shock_zscore": 0.75,
        }
    return {
        "drift": 95.0 if position % 2 == 0 else -105.0,
        "efficiency_ratio": 0.45 + cycle * 0.10,
        "choppiness": 43.0 + cycle * 5.0,
        "slope": 0.12,
        "range_width": 0.044,
        "realized_volatility": 0.034,
        "atr_percentile": 0.93,
        "volatility_shock_zscore": 3.2,
    }


def _label_accept(*, regime: int, index: int) -> int:
    if regime == 0:
        return 1 if index % 4 in {0, 1} else 0
    if regime == 1:
        return 1 if index % 5 != 0 else 0
    if regime == 2:
        return 1 if index % 5 == 0 else 0
    return 1 if index % 3 == 0 else 0


def _funding_paid_or_received(*, regime: int, direction: str) -> float:
    base = 0.00004 if regime == 1 else (-0.00003 if regime == 2 else 0.000005)
    return -base if direction == "long" else base


def _add_raw_and_missing_context(row: dict[str, Any], *, variant: str) -> None:
    context_fields = (
        "basis_bps",
        "funding_rate",
        "funding_rate_change",
        "open_interest",
        "open_interest_change",
        "open_interest_change_pct",
        "open_interest_value",
        "premium_basis_rate",
        "premium_basis_abs",
        "premium_close",
        "mark_price",
        "index_price",
        "primary_signed_imbalance_ratio",
        "primary_sqrt_signed_imbalance_ratio",
        "top_of_book_imbalance",
        "queue_imbalance_l1",
        "queue_imbalance_l5",
        "queue_imbalance_l10",
        "spread_bps",
    )
    sparse_missing = {
        "basis_bps",
        "open_interest",
        "open_interest_change",
        "open_interest_change_pct",
        "open_interest_value",
        "premium_basis_rate",
        "premium_basis_abs",
        "premium_close",
        "mark_price",
        "index_price",
        "primary_signed_imbalance_ratio",
        "primary_sqrt_signed_imbalance_ratio",
        "top_of_book_imbalance",
        "queue_imbalance_l1",
        "queue_imbalance_l5",
        "queue_imbalance_l10",
        "spread_bps",
    }
    for field in context_fields:
        raw_field = f"raw_{field}"
        missing_field = f"missing_{field}"
        is_missing = variant == "sparse_context" and field in sparse_missing
        row[raw_field] = None if is_missing else row.get(field)
        row[missing_field] = 1.0 if is_missing else 0.0
        if is_missing:
            row[field] = 0.0


def _frame_logical_sha256(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n", float_format="%.12g")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _raw_context_available_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = {
        column: int(frame[column].notna().sum())
        for column in frame.columns
        if column.startswith("raw_")
    }
    counts["decision_context_present"] = int(frame["decision_context_present"].astype(bool).sum())
    return counts


def _exchange_context_summary(frame: pd.DataFrame) -> dict[str, Any]:
    families = {
        "funding_context": ("raw_funding_rate", "raw_funding_rate_change"),
        "open_interest_context": (
            "raw_open_interest",
            "raw_open_interest_change",
            "raw_open_interest_change_pct",
            "raw_open_interest_value",
        ),
        "premium_context": (
            "raw_premium_basis_rate",
            "raw_premium_basis_abs",
            "raw_premium_close",
            "raw_mark_price",
            "raw_index_price",
        ),
        "basis_context": ("raw_basis_bps",),
        "microstructure_context": (
            "raw_primary_signed_imbalance_ratio",
            "raw_primary_sqrt_signed_imbalance_ratio",
            "raw_top_of_book_imbalance",
            "raw_queue_imbalance_l1",
            "raw_queue_imbalance_l5",
            "raw_queue_imbalance_l10",
            "raw_spread_bps",
        ),
    }
    row_count = int(len(frame))
    summary: dict[str, Any] = {}
    for family, raw_fields in families.items():
        available_counts = {
            field: int(frame[field].notna().sum())
            for field in raw_fields
            if field in frame.columns
        }
        successful_count = min(available_counts.values()) if available_counts else 0
        unavailable_count = row_count - successful_count
        summary[family] = {
            "rows_with_context": successful_count,
            "field_available_counts": available_counts,
            "source_counts": {
                "deterministic_fixture": successful_count,
                **({"unavailable_fixture": unavailable_count} if unavailable_count else {}),
            },
            "attempted_count": row_count,
            "successful_count": successful_count,
            "unavailable_count": unavailable_count,
            "error_count": 0,
            "backoff_count": 0,
            "current_only_fallback_count": 0,
            "live_fetch_used": False,
        }
    return summary


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
