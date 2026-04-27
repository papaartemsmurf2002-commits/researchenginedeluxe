from __future__ import annotations

import copy
import json
import threading
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from tradingbot.config import load_app_config
from tradingbot.indicators import normalize_frame
from tradingbot.lorentz import LorentzianClassifier
from tradingbot.models import AppConfig, StrategyConfig


BOOL_FIELDS = {
    "use_dynamic_exits",
    "use_volatility_filter",
    "use_regime_filter",
    "use_adx_filter",
    "use_ema_filter",
    "use_sma_filter",
    "use_kernel_filter",
    "use_kernel_smoothing",
    "allow_long",
    "allow_short",
    "block_early_signal_flips",
}
INT_FIELDS = {
    "neighbors_count",
    "max_bars_back",
    "feature_count",
    "ema_period",
    "sma_period",
    "adx_threshold",
    "kernel_lookback",
    "kernel_regression_level",
    "kernel_lag",
    "min_signal_persistence_bars",
    "min_bars_between_entries",
}
FLOAT_FIELDS = {"regime_threshold", "kernel_relative_weight", "min_prediction_magnitude"}
SHAPE_MARKER_COLUMNS = {"Buy", "Sell", "StopBuy", "StopSell"}
TRUE_MARKER_STRINGS = {"true", "t", "1", "yes", "y"}
FALSE_MARKER_STRINGS = {"false", "f", "0", "no", "n", "nan", "none", "null", ""}
TV_LONG_ENTRY_COLUMNS = ("start_long_trade_tv", "startLongTrade", "Buy")
TV_SHORT_ENTRY_COLUMNS = ("start_short_trade_tv", "startShortTrade", "Sell")
RAW_TV_LONG_ENTRY_COLUMNS = ("Buy", "start_long_trade", "startLongTrade")
RAW_TV_SHORT_ENTRY_COLUMNS = ("Sell", "start_short_trade", "startShortTrade")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float):
        return None if not np.isfinite(value) else value
    if pd.isna(value):
        return None
    return value


def _timestamp_series(frame: pd.DataFrame) -> pd.Series:
    if "timestamp" in frame.columns:
        raw = frame["timestamp"]
    elif "time" in frame.columns:
        raw = frame["time"]
    elif "open_time" in frame.columns:
        raw = frame["open_time"]
    else:
        raw = frame.iloc[:, 0]
    if pd.api.types.is_numeric_dtype(raw):
        max_timestamp = float(raw.dropna().max()) if raw.notna().any() else 0.0
        unit = "ms" if max_timestamp > 10_000_000_000 else "s"
        return pd.to_datetime(raw, unit=unit, utc=True)
    return pd.to_datetime(raw, utc=True)


def _resolve_market_csv_path(path: str | Path) -> Path:
    csv_path = Path(path)
    if not csv_path.exists() and csv_path.suffix == "":
        csv_path = csv_path.with_suffix(".csv")
    return csv_path


def _read_market_csv(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(_resolve_market_csv_path(path), low_memory=False)
    frame = raw.copy()
    if "timestamp" not in frame.columns:
        frame["timestamp"] = _timestamp_series(frame)
    if "volume" not in frame.columns:
        frame["volume"] = 0.0
    if "symbol" not in frame.columns:
        frame["symbol"] = "BTC"
    return raw, normalize_frame(frame)


def _marker_bool(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().any():
        if column in SHAPE_MARKER_COLUMNS:
            return numeric.notna()
        return numeric.fillna(0).ne(0)
    strings = values.fillna("").astype(str).str.strip().str.lower()
    if column in SHAPE_MARKER_COLUMNS:
        return ~(strings.isin(FALSE_MARKER_STRINGS))
    return strings.isin(TRUE_MARKER_STRINGS)


def _first_existing_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    return next((column for column in candidates if column in frame.columns), None)


def _tv_entry_bool(frame: pd.DataFrame, side: str, *, raw_export: bool = False) -> pd.Series:
    if side == "long":
        candidates = RAW_TV_LONG_ENTRY_COLUMNS if raw_export else TV_LONG_ENTRY_COLUMNS
    elif side == "short":
        candidates = RAW_TV_SHORT_ENTRY_COLUMNS if raw_export else TV_SHORT_ENTRY_COLUMNS
    else:
        raise ValueError("side must be 'long' or 'short'")
    column = _first_existing_column(frame, candidates)
    if column is None:
        return pd.Series(False, index=frame.index, dtype=bool)
    return _marker_bool(frame, column)


def _tv_entry_price_column(frame: pd.DataFrame, side: str, *, raw_export: bool = False) -> str | None:
    marker_column = "Buy" if side == "long" else "Sell"
    return marker_column if marker_column in frame.columns else None


def _tv_entry_source_columns(frame: pd.DataFrame) -> dict[str, str | None]:
    return {
        "long": _first_existing_column(frame, TV_LONG_ENTRY_COLUMNS),
        "short": _first_existing_column(frame, TV_SHORT_ENTRY_COLUMNS),
    }


def _apply_overrides(config: AppConfig, symbol: str, overrides: dict[str, Any]) -> AppConfig:
    bundle = copy.deepcopy(config)
    strategy = bundle.strategies[symbol]
    for field in BOOL_FIELDS:
        if field in overrides:
            setattr(strategy, field, bool(overrides[field]))
    for field in INT_FIELDS:
        if field in overrides and overrides[field] not in (None, ""):
            setattr(strategy, field, int(overrides[field]))
    for field in FLOAT_FIELDS:
        if field in overrides and overrides[field] not in (None, ""):
            setattr(strategy, field, float(overrides[field]))
    if "source" in overrides:
        strategy.source = str(overrides["source"])
    if "lc_parity_mode" in overrides:
        strategy.lc_parity_mode = str(overrides["lc_parity_mode"])
    if "features" in overrides:
        features = []
        for item in list(overrides["features"])[:5]:
            features.append((str(item["name"]).upper(), int(item["param_a"]), int(item["param_b"])))
        if features:
            strategy.feature_definitions = features
            strategy.feature_count = min(int(overrides.get("feature_count", len(features))), len(features))
    return bundle


def _default_overrides(strategy: StrategyConfig) -> dict[str, Any]:
    payload = asdict(strategy)
    payload["features"] = [
        {"name": name, "param_a": int(param_a), "param_b": int(param_b)}
        for name, param_a, param_b in strategy.feature_definitions[: strategy.feature_count]
    ]
    return payload


def _series_value(row: pd.Series, column: str, default: Any = None) -> Any:
    if column not in row.index:
        return default
    value = row[column]
    if pd.isna(value):
        return default
    return value


def _event_price(row: pd.Series, action: str, side: str, marker_column: str | None = None) -> float:
    if marker_column and marker_column in row.index and pd.notna(row[marker_column]):
        return float(row[marker_column])
    if action == "entry" and side == "long" and "low" in row.index:
        return float(row["low"])
    if action == "entry" and side == "short" and "high" in row.index:
        return float(row["high"])
    if action == "exit" and side == "long" and "high" in row.index:
        return float(row["high"])
    if action == "exit" and side == "short" and "low" in row.index:
        return float(row["low"])
    return float(row["close"])


def _count_bool(values: pd.Series) -> int:
    return int(values.fillna(False).astype(bool).sum())


def _match_count_with_tolerance(
    frame: pd.DataFrame,
    py_long: pd.Series,
    py_short: pd.Series,
    tv_long: pd.Series,
    tv_short: pd.Series,
    tolerance_bars: int,
) -> tuple[int, int, int]:
    def events(long_values: pd.Series, short_values: pd.Series) -> list[tuple[int, str]]:
        output: list[tuple[int, str]] = []
        for position, idx in enumerate(frame.index):
            if bool(long_values.loc[idx]):
                output.append((position, "long"))
            if bool(short_values.loc[idx]):
                output.append((position, "short"))
        return output

    py_events = events(py_long, py_short)
    tv_events = events(tv_long, tv_short)
    unused_py = set(range(len(py_events)))
    matched = 0
    tolerance = max(int(tolerance_bars), 0)
    for tv_pos, tv_side in tv_events:
        candidates = [
            py_idx
            for py_idx in unused_py
            if py_events[py_idx][1] == tv_side and abs(py_events[py_idx][0] - tv_pos) <= tolerance
        ]
        if not candidates:
            continue
        best = min(candidates, key=lambda py_idx: (abs(py_events[py_idx][0] - tv_pos), py_events[py_idx][0]))
        unused_py.remove(best)
        matched += 1
    return matched, len(tv_events) - matched, len(unused_py)


def _kernel_diff_summary(merged: pd.DataFrame) -> dict[str, Any] | None:
    tv_column = "Kernel Regression Estimate" if "Kernel Regression Estimate" in merged.columns else "yhat1_tv"
    if tv_column not in merged.columns:
        return None
    py = pd.to_numeric(merged["yhat1"], errors="coerce")
    tv = pd.to_numeric(merged[tv_column], errors="coerce")
    mask = py.notna() & tv.notna()
    if not bool(mask.any()):
        return None
    diff = (py[mask] - tv[mask]).abs()
    return {
        "overlap_rows": int(mask.sum()),
        "mean_abs_error": float(diff.mean()),
        "max_abs_error": float(diff.max()),
    }


def _build_marker_mismatches(merged: pd.DataFrame, max_items: int = 300, *, include_exits: bool = False) -> list[dict[str, Any]]:
    comparisons = [
        ("long", "start_long_trade", "long entry"),
        ("short", "start_short_trade", "short entry"),
    ]
    if include_exits:
        comparisons.extend(
            [
                ("StopBuy", "end_long_trade", "long exit"),
                ("StopSell", "end_short_trade", "short exit"),
            ]
        )
    mismatches: list[dict[str, Any]] = []
    for side, py_column, label in comparisons:
        py = merged[py_column].fillna(False).astype(bool) if py_column in merged.columns else pd.Series(False, index=merged.index)
        tv = _tv_entry_bool(merged, side)
        diff_indexes = merged.index[py.ne(tv)]
        for index in diff_indexes:
            row = merged.loc[index]
            mismatches.append(
                {
                    "timestamp": row["timestamp"],
                    "bar_index": int(index),
                    "kind": label,
                    "python": bool(py.loc[index]),
                    "tradingview": bool(tv.loc[index]),
                    "prediction": _series_value(row, "prediction"),
                    "signal": _series_value(row, "signal"),
                    "bars_held": _series_value(row, "bars_held"),
                }
            )
            if len(mismatches) >= max_items:
                return mismatches
    return mismatches


def _entry_window(merged: pd.DataFrame, mode: str, sample_size: int, sample_offset: int) -> pd.DataFrame:
    tv_buy = _tv_entry_bool(merged, "long")
    tv_sell = _tv_entry_bool(merged, "short")
    entry_indexes = [int(index) for index in merged.index[tv_buy | tv_sell]]
    if mode == "full" or not entry_indexes:
        return merged
    if mode == "latest":
        selected = entry_indexes[-max(int(sample_size), 1) :]
    elif mode == "sample":
        start = max(int(sample_offset), 0)
        selected = entry_indexes[start : start + max(int(sample_size), 1)]
    else:
        raise ValueError("UI window mode must be 'sample', 'full', or 'latest'.")
    if not selected:
        return merged.iloc[0:0].copy()
    pad = 20
    start_index = max(min(selected) - pad, 0)
    end_index = min(max(selected) + pad, len(merged) - 1)
    return merged.loc[start_index:end_index].copy()


def _latest_tradingview_entries(merged: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    raw_export = "start_long_trade_tv" not in merged.columns and "start_short_trade_tv" not in merged.columns
    buy_markers = _tv_entry_bool(merged, "long", raw_export=raw_export)
    sell_markers = _tv_entry_bool(merged, "short", raw_export=raw_export)
    buy_price_column = _tv_entry_price_column(merged, "long", raw_export=raw_export)
    sell_price_column = _tv_entry_price_column(merged, "short", raw_export=raw_export)
    for index in merged.index[buy_markers | sell_markers]:
        row = merged.loc[index]
        if bool(buy_markers.loc[index]):
            entries.append(
                {
                    "timestamp": row["timestamp"],
                    "bar_index": int(index),
                    "side": "long",
                    "price": _event_price(row, "entry", "long", buy_price_column),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
            )
        if bool(sell_markers.loc[index]):
            entries.append(
                {
                    "timestamp": row["timestamp"],
                    "bar_index": int(index),
                    "side": "short",
                    "price": _event_price(row, "entry", "short", sell_price_column),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
            )
    return entries[-limit:]


def _append_decisions(
    decisions: list[dict[str, Any]],
    row: pd.Series,
    *,
    source: str,
    action: str,
    side: str,
    column: str,
    marker_column: str | None = None,
) -> None:
    value = _marker_bool(pd.DataFrame([row]), column).iloc[0] if source == "tradingview" else bool(row.get(column, False))
    if not value:
        return
    decisions.append(
        {
            "source": source,
            "action": action,
            "side": side,
            "bar_index": int(row.name),
            "timestamp": row["timestamp"],
            "time_ms": int(pd.Timestamp(row["timestamp"]).timestamp() * 1000),
            "price": _event_price(row, action, side, marker_column),
        }
    )


def build_lc_diagnostics_payload(
    csv_path: str | Path,
    app_config: AppConfig,
    symbol: str,
    overrides: dict[str, Any] | None = None,
    max_chart_points: int = 5000,
    window_mode: str = "full",
    sample_size: int = 100,
    sample_offset: int = 0,
    tolerance_bars: int = 1,
    include_last_bar: bool = False,
) -> dict[str, Any]:
    """Run LC against a local CSV and return browser-chart diagnostics."""
    symbol = symbol.upper()
    if symbol not in app_config.strategies:
        raise ValueError(f"Unknown symbol '{symbol}'. Available: {', '.join(sorted(app_config.strategies))}")
    raw, base = _read_market_csv(csv_path)
    active_config = _apply_overrides(app_config, symbol, overrides or {})
    strategy = active_config.strategies[symbol]
    signal_frame = LorentzianClassifier().generate(base, strategy)

    tv_frame = raw.copy()
    tv_frame["timestamp"] = _timestamp_series(tv_frame)
    tv_frame = tv_frame.sort_values("timestamp").reset_index(drop=True)
    merged = signal_frame.merge(tv_frame, on="timestamp", how="left", suffixes=("", "_tv"))
    if not include_last_bar and len(merged):
        newest_export_ts = tv_frame["timestamp"].max()
        merged = merged[merged["timestamp"] < newest_export_ts].reset_index(drop=True)
    max_bars_back_index = (
        max(len(merged) - 1 - int(strategy.max_bars_back), 0)
        if len(merged) - 1 >= int(strategy.max_bars_back)
        else 0
    )
    comparison_frame = _entry_window(merged, window_mode, sample_size, sample_offset)

    py_buy = comparison_frame["start_long_trade"].fillna(False).astype(bool)
    py_sell = comparison_frame["start_short_trade"].fillna(False).astype(bool)
    raw_py_buy = comparison_frame["raw_start_long_trade"].fillna(False).astype(bool) if "raw_start_long_trade" in comparison_frame else py_buy
    raw_py_sell = comparison_frame["raw_start_short_trade"].fillna(False).astype(bool) if "raw_start_short_trade" in comparison_frame else py_sell
    py_stop_buy = comparison_frame["end_long_trade"].fillna(False).astype(bool)
    py_stop_sell = comparison_frame["end_short_trade"].fillna(False).astype(bool)
    tv_buy = _tv_entry_bool(comparison_frame, "long")
    tv_sell = _tv_entry_bool(comparison_frame, "short")
    tv_stop_buy = _marker_bool(comparison_frame, "StopBuy")
    tv_stop_sell = _marker_bool(comparison_frame, "StopSell")

    limit = len(comparison_frame) if int(max_chart_points) <= 0 else max(20, min(int(max_chart_points), len(comparison_frame)))
    chart_frame = comparison_frame.tail(limit).copy()
    bars: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for index, row in chart_frame.iterrows():
        bars.append(
            {
                "bar_index": int(index),
                "timestamp": row["timestamp"],
                "time_ms": int(pd.Timestamp(row["timestamp"]).timestamp() * 1000),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "f1": _series_value(row, "f1"),
                "f2": _series_value(row, "f2"),
                "f3": _series_value(row, "f3"),
                "f4": _series_value(row, "f4"),
                "f5": _series_value(row, "f5"),
                "prediction": _series_value(row, "prediction"),
                "signal": _series_value(row, "signal"),
                "bars_held": _series_value(row, "bars_held"),
                "yhat1": _series_value(row, "yhat1"),
                "tv_yhat1": _series_value(row, "Kernel Regression Estimate", _series_value(row, "yhat1_tv")),
            }
        )
        _append_decisions(decisions, row, source="python", action="entry", side="long", column="start_long_trade")
        _append_decisions(decisions, row, source="python", action="entry", side="short", column="start_short_trade")
        tv_long_column = _tv_entry_price_column(chart_frame, "long")
        tv_short_column = _tv_entry_price_column(chart_frame, "short")
        if bool(_tv_entry_bool(pd.DataFrame([row]), "long").iloc[0]):
            decisions.append(
                {
                    "source": "tradingview",
                    "action": "entry",
                    "side": "long",
                    "bar_index": int(row.name),
                    "timestamp": row["timestamp"],
                    "time_ms": int(pd.Timestamp(row["timestamp"]).timestamp() * 1000),
                    "price": _event_price(row, "entry", "long", tv_long_column),
                }
            )
        if bool(_tv_entry_bool(pd.DataFrame([row]), "short").iloc[0]):
            decisions.append(
                {
                    "source": "tradingview",
                    "action": "entry",
                    "side": "short",
                    "bar_index": int(row.name),
                    "timestamp": row["timestamp"],
                    "time_ms": int(pd.Timestamp(row["timestamp"]).timestamp() * 1000),
                    "price": _event_price(row, "entry", "short", tv_short_column),
                }
            )

    mismatches = _build_marker_mismatches(comparison_frame)
    relaxed_match_count, relaxed_missing_count, relaxed_extra_count = _match_count_with_tolerance(
        comparison_frame,
        py_buy,
        py_sell,
        tv_buy,
        tv_sell,
        tolerance_bars,
    )
    entry_mismatch_count = relaxed_missing_count + relaxed_extra_count
    exact_entry_mismatch_count = int(sum(py_buy.ne(tv_buy)) + sum(py_sell.ne(tv_sell)))
    exit_mismatch_count = int(sum(py_stop_buy.ne(tv_stop_buy)) + sum(py_stop_sell.ne(tv_stop_sell)))
    first_timestamp = merged["timestamp"].iloc[0] if len(merged) else None
    last_timestamp = merged["timestamp"].iloc[-1] if len(merged) else None
    comparison_start = comparison_frame["timestamp"].iloc[0] if len(comparison_frame) else None
    comparison_end = comparison_frame["timestamp"].iloc[-1] if len(comparison_frame) else None
    payload = {
        "settings": _default_overrides(strategy),
        "summary": {
            "csv_path": str(csv_path),
            "symbol": symbol,
            "rows": int(len(merged)),
            "chart_rows": int(len(chart_frame)),
            "requested_chart_rows": int(limit),
            "data_source": "TV/export OHLC candles; exported markers are comparison overlays only",
            "first_timestamp": first_timestamp,
            "last_timestamp": last_timestamp,
            "last_close": float(merged["close"].iloc[-1]) if len(merged) else None,
            "window_mode": window_mode,
            "sample_size": int(sample_size),
            "sample_offset": int(sample_offset),
            "tolerance_bars": int(max(tolerance_bars, 0)),
            "include_last_bar": bool(include_last_bar),
            "comparison_start": comparison_start,
            "comparison_end": comparison_end,
            "max_bars_back_index": max_bars_back_index,
            "max_bars_back_timestamp": (
                merged["timestamp"].iloc[max_bars_back_index]
                if len(merged) and 0 <= max_bars_back_index < len(merged)
                else None
            ),
            "python_counts": {
                "buy": _count_bool(py_buy),
                "sell": _count_bool(py_sell),
                "stop_buy": _count_bool(py_stop_buy),
                "stop_sell": _count_bool(py_stop_sell),
            },
            "stability_counts": {
                "raw_buy": _count_bool(raw_py_buy),
                "raw_sell": _count_bool(raw_py_sell),
                "final_buy": _count_bool(py_buy),
                "final_sell": _count_bool(py_sell),
                "suppressed": max(
                    _count_bool(raw_py_buy) + _count_bool(raw_py_sell) - _count_bool(py_buy) - _count_bool(py_sell),
                    0,
                ),
            },
            "tradingview_counts": {
                "buy": _count_bool(tv_buy),
                "sell": _count_bool(tv_sell),
                "stop_buy": _count_bool(tv_stop_buy),
                "stop_sell": _count_bool(tv_stop_sell),
            },
            "tradingview_entry_columns": _tv_entry_source_columns(comparison_frame),
            "marker_mismatch_count": entry_mismatch_count,
            "entry_mismatch_count": entry_mismatch_count,
            "exact_entry_mismatch_count": exact_entry_mismatch_count,
            "matched_entry_count": relaxed_match_count,
            "missing_entry_count": relaxed_missing_count,
            "extra_entry_count": relaxed_extra_count,
            "exit_mismatch_count_ignored": exit_mismatch_count,
            "total_marker_mismatch_count_with_exits": entry_mismatch_count + exit_mismatch_count,
            "first_marker_mismatch": mismatches[0] if mismatches else None,
            "kernel_diff": _kernel_diff_summary(merged),
        },
        "chart": {"bars": bars, "decisions": decisions},
        "mismatches": mismatches,
        "latest_tradingview_entries": _latest_tradingview_entries(merged),
    }
    return _json_safe(payload)


def build_lc_defaults_payload(
    csv_path: str | Path,
    app_config: AppConfig,
    symbol: str,
    max_chart_points: int = 5000,
    window_mode: str = "full",
    sample_size: int = 100,
    sample_offset: int = 0,
    tolerance_bars: int = 1,
    include_last_bar: bool = False,
) -> dict[str, Any]:
    """Return fast UI defaults without running the LC classifier.

    Large TradingView exports can take a long time to simulate. The browser
    needs config and dataset metadata immediately, then the user explicitly
    starts the expensive diagnostic pass.
    """
    symbol = symbol.upper()
    if symbol not in app_config.strategies:
        raise ValueError(f"Unknown symbol '{symbol}'. Available: {', '.join(sorted(app_config.strategies))}")
    csv_file = _resolve_market_csv_path(csv_path)
    raw = pd.read_csv(csv_file, low_memory=False)
    frame = raw.copy()
    frame["timestamp"] = _timestamp_series(frame)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    first_timestamp = frame["timestamp"].iloc[0] if len(frame) else None
    last_timestamp = frame["timestamp"].iloc[-1] if len(frame) else None
    strategy = app_config.strategies[symbol]
    last_closed_index = max(len(frame) - 2, 0) if len(frame) else 0
    max_bars_back_index = max(last_closed_index - int(strategy.max_bars_back), 0) if last_closed_index >= int(strategy.max_bars_back) else 0
    tv_buy = _tv_entry_bool(frame, "long", raw_export=True)
    tv_sell = _tv_entry_bool(frame, "short", raw_export=True)
    tv_stop_buy = _marker_bool(frame, "StopBuy")
    tv_stop_sell = _marker_bool(frame, "StopSell")
    limit = len(frame) if int(max_chart_points) <= 0 else max(20, min(int(max_chart_points), len(frame)))
    empty_counts = {"buy": 0, "sell": 0, "stop_buy": 0, "stop_sell": 0}
    payload = {
        "settings": _default_overrides(app_config.strategies[symbol]),
        "summary": {
            "csv_path": str(csv_file),
            "symbol": symbol,
            "rows": int(len(frame)),
            "chart_rows": 0,
            "requested_chart_rows": int(limit),
            "data_source": "TV/export OHLC candles; click Run validation to compute Python LC markers",
            "first_timestamp": first_timestamp,
            "last_timestamp": last_timestamp,
            "last_close": float(frame["close"].iloc[-1]) if len(frame) and "close" in frame.columns else None,
            "window_mode": window_mode,
            "sample_size": int(sample_size),
            "sample_offset": int(sample_offset),
            "tolerance_bars": int(max(tolerance_bars, 0)),
            "include_last_bar": bool(include_last_bar),
            "comparison_start": None,
            "comparison_end": None,
            "max_bars_back_index": int(max_bars_back_index),
            "max_bars_back_timestamp": frame["timestamp"].iloc[max_bars_back_index] if len(frame) else None,
            "python_counts": empty_counts,
            "stability_counts": {"raw_buy": 0, "raw_sell": 0, "final_buy": 0, "final_sell": 0, "suppressed": 0},
            "tradingview_counts": {
                "buy": _count_bool(tv_buy),
                "sell": _count_bool(tv_sell),
                "stop_buy": _count_bool(tv_stop_buy),
                "stop_sell": _count_bool(tv_stop_sell),
            },
            "tradingview_entry_columns": {
                "long": _first_existing_column(frame, RAW_TV_LONG_ENTRY_COLUMNS),
                "short": _first_existing_column(frame, RAW_TV_SHORT_ENTRY_COLUMNS),
            },
            "marker_mismatch_count": 0,
            "entry_mismatch_count": 0,
            "exact_entry_mismatch_count": 0,
            "matched_entry_count": 0,
            "missing_entry_count": 0,
            "extra_entry_count": 0,
            "exit_mismatch_count_ignored": 0,
            "total_marker_mismatch_count_with_exits": 0,
            "first_marker_mismatch": None,
            "kernel_diff": None,
        },
        "chart": {"bars": [], "decisions": []},
        "mismatches": [],
        "latest_tradingview_entries": _latest_tradingview_entries(frame),
    }
    return _json_safe(payload)


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LC Diagnostics</title>
<style>
:root{--bg:#101418;--panel:#171d23;--line:#2d3943;--text:#e6edf3;--muted:#8b949e;--up:#2bd47d;--dn:#ff5964;--py:#67b7ff;--tv:#ffd166}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:13px/1.4 Consolas,Menlo,monospace}
header{padding:14px 18px;border-bottom:1px solid var(--line);display:flex;gap:14px;align-items:center;flex-wrap:wrap}
h1{font-size:16px;margin:0}button,input,select{background:#0d1117;color:var(--text);border:1px solid #3b4651;border-radius:6px;padding:7px 9px;font:inherit}button{cursor:pointer}button:hover{border-color:#6aa6df}
.wrap{display:grid;grid-template-columns:360px 1fr;min-height:calc(100vh - 58px)}
.side{border-right:1px solid var(--line);background:var(--panel);padding:14px;overflow:auto}
.main{padding:12px;overflow:hidden}.group{border:1px solid var(--line);border-radius:8px;margin-bottom:12px;padding:10px}.group h2{font-size:13px;margin:0 0 8px;color:#b8c7d9}
label{display:grid;grid-template-columns:1fr 120px;gap:8px;align-items:center;margin:7px 0}.check{grid-template-columns:24px 1fr}input[type=checkbox]{width:16px;height:16px}
.feature{display:grid;grid-template-columns:70px 1fr 1fr;gap:6px;margin:6px 0}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}.stat{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px}.stat b{display:block;font-size:18px}
#chart{width:100%;height:610px;background:#0c1116;border:1px solid var(--line);border-radius:8px;touch-action:none;cursor:grab;user-select:none}#chart.dragging{cursor:grabbing}.toolbar{display:flex;gap:8px;align-items:center;margin:8px 0;flex-wrap:wrap}
table{width:100%;border-collapse:collapse;margin-top:10px}th,td{border-bottom:1px solid var(--line);padding:6px;text-align:left;white-space:nowrap}th{color:#b8c7d9}.muted{color:var(--muted)}.err{color:#ff8b8b}.ok{color:#9be9a8}
</style>
</head>
<body>
<header><h1>LC Validation</h1><span class="muted">Full-export TradingView marker validation. Settings are read from the YAML config.</span></header>
<div class="wrap">
<aside class="side">
<div class="group">
<h2>Validation Input</h2>
<label>CSV path <input id="csvPath"></label>
<label>Symbol <input id="symbol"></label>
<label>Tolerance bars <input id="toleranceBars" type="number" min="0" max="3" value="1"></label>
<label class="check"><input id="includeLastBar" type="checkbox"><span>Include newest candle</span></label>
<button id="runBtn">Run validation</button>
<div id="status" class="muted"></div>
</div>
<div class="group">
<h2>Core Settings</h2>
<label>Source <select id="source"><option>close</option><option>hlc3</option><option>ohlc4</option><option>open</option><option>high</option><option>low</option></select></label>
<label>Neighbors <input id="neighbors_count" type="number" min="1" max="100"></label>
<label>Max bars back <input id="max_bars_back" type="number" min="50"></label>
<label>Feature count <input id="feature_count" type="number" min="1" max="5"></label>
<label>Min prediction <input id="min_prediction_magnitude" type="number" min="0" step="1"></label>
<label>Confirm bars <input id="min_signal_persistence_bars" type="number" min="1" max="20"></label>
<label>Entry cooldown <input id="min_bars_between_entries" type="number" min="0" max="100"></label>
<label class="check"><input id="block_early_signal_flips" type="checkbox"><span>Block early flips</span></label>
</div>
<div class="group">
<h2>Features</h2>
<div id="features"></div>
</div>
<div class="group">
<h2>Filters</h2>
<label class="check"><input id="use_dynamic_exits" type="checkbox"><span>Dynamic exits</span></label>
<label class="check"><input id="use_volatility_filter" type="checkbox"><span>Volatility filter</span></label>
<label class="check"><input id="use_regime_filter" type="checkbox"><span>Regime filter</span></label>
<label class="check"><input id="use_adx_filter" type="checkbox"><span>ADX filter</span></label>
<label class="check"><input id="use_ema_filter" type="checkbox"><span>EMA filter</span></label>
<label class="check"><input id="use_sma_filter" type="checkbox"><span>SMA filter</span></label>
<label class="check"><input id="use_kernel_filter" type="checkbox"><span>Trade with kernel</span></label>
<label class="check"><input id="use_kernel_smoothing" type="checkbox"><span>Kernel smoothing</span></label>
</div>
<div class="group">
<h2>Kernel</h2>
<label>Lookback <input id="kernel_lookback" type="number" min="1"></label>
<label>Relative weight <input id="kernel_relative_weight" type="number" step="0.1"></label>
<label>Regression <input id="kernel_regression_level" type="number" min="0"></label>
<label>Lag <input id="kernel_lag" type="number" min="1"></label>
</div>
<div class="group">
<h2>Locked Baseline</h2>
<div id="configSummary" class="muted"></div>
</div>
</aside>
<main class="main">
<div class="stats" id="stats"></div>
<div class="toolbar">
<button id="zoomIn">Zoom in</button><button id="zoomOut">Zoom out</button><button id="resetZoom">Reset</button>
<span class="muted">Blue triangles = Python simulated entries. Yellow diamonds = TradingView exported Buy/Sell. Purple line = max-bars-back boundary.</span>
</div>
<svg id="chart"></svg>
<h2 class="muted">Entry mismatches only</h2>
<table><thead><tr><th>Time</th><th>Kind</th><th>Python</th><th>TV</th><th>Prediction</th><th>Signal</th><th>Bars held</th></tr></thead><tbody id="mismatches"></tbody></table>
<h2 class="muted">Latest TradingView entries from export</h2>
<table><thead><tr><th>Time</th><th>Side</th><th>Marker price</th><th>Open</th><th>High</th><th>Low</th><th>Close</th></tr></thead><tbody id="latestEntries"></tbody></table>
</main>
</div>
<script>
let state={payload:null,viewStart:0,viewEnd:0,drag:false,dragX:0};
const $=id=>document.getElementById(id);
const num=id=>Number($(id).value);
const bool=id=>$(id).checked;
function featureRow(i,f){return `<div class="feature"><select id="f${i}n">${["RSI","WT","CCI","ADX"].map(x=>`<option ${x===f.name?"selected":""}>${x}</option>`).join("")}</select><input id="f${i}a" type="number" value="${f.param_a}"><input id="f${i}b" type="number" value="${f.param_b}"></div>`}
function featureText(s){return (s.features||[]).map((f,i)=>`${i+1}. ${f.name}(${f.param_a},${f.param_b})`).join("<br>")}
function fillSettings(p){$("csvPath").value=p.summary.csv_path;$("symbol").value=p.summary.symbol;$("includeLastBar").checked=!!p.summary.include_last_bar;$("toleranceBars").value=p.summary.tolerance_bars??1;const s=p.settings;$("source").value=s.source;for(const k of ["neighbors_count","max_bars_back","feature_count","kernel_lookback","kernel_relative_weight","kernel_regression_level","kernel_lag","min_prediction_magnitude","min_signal_persistence_bars","min_bars_between_entries"])$(k).value=s[k];for(const k of ["use_dynamic_exits","use_volatility_filter","use_regime_filter","use_adx_filter","use_ema_filter","use_sma_filter","use_kernel_filter","use_kernel_smoothing","block_early_signal_flips"])$(k).checked=!!s[k];$("features").innerHTML=s.features.map((f,i)=>featureRow(i+1,f)).join("");$("configSummary").innerHTML=`Mode: <b>${s.lc_parity_mode}</b><br>Full export rows: <b>${p.summary.rows}</b><br>Max-bars-back: <b>${p.summary.max_bars_back_index}</b><br>${p.summary.max_bars_back_timestamp||""}<br>Features:<br>${featureText(s)}`}
function readOverrides(){let features=[];for(let i=1;i<=5;i++)features.push({name:$(`f${i}n`).value,param_a:num(`f${i}a`),param_b:num(`f${i}b`)});let o={features,source:$("source").value};for(const k of ["neighbors_count","max_bars_back","feature_count","kernel_lookback","kernel_regression_level","kernel_lag","min_signal_persistence_bars","min_bars_between_entries"])o[k]=num(k);for(const k of ["kernel_relative_weight","min_prediction_magnitude"])o[k]=num(k);for(const k of ["use_dynamic_exits","use_volatility_filter","use_regime_filter","use_adx_filter","use_ema_filter","use_sma_filter","use_kernel_filter","use_kernel_smoothing","block_early_signal_flips"])o[k]=bool(k);return o}
async function postJSON(url,body){const r=await fetch(url,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw Error(j.error||r.statusText);return j}
async function loadDefaults(){try{$("status").textContent="loading settings...";const r=await fetch("/api/defaults");const p=await r.json();if(!r.ok)throw Error(p.error||r.statusText);state.payload=p;fillSettings(p);resetView();renderAll();$("status").innerHTML='<span class="ok">settings loaded; full export validation is selected</span>'}catch(e){$("status").innerHTML=`<span class="err">${e.message}</span>`}}
async function runSimulation(){try{$("status").textContent="running full-export validation...";const p=await postJSON("/api/simulate",{csv_path:$("csvPath").value,symbol:$("symbol").value,max_chart_points:0,window_mode:"full",sample_size:0,sample_offset:0,tolerance_bars:num("toleranceBars"),include_last_bar:bool("includeLastBar"),overrides:readOverrides()});state.payload=p;fillSettings(p);resetView();renderAll();$("status").innerHTML='<span class="ok">validation complete</span>'}catch(e){$("status").innerHTML=`<span class="err">${e.message}</span>`}}
function resetView(){const n=state.payload.chart.bars.length;state.viewStart=0;state.viewEnd=Math.max(0,n-1)}
function renderStats(){const s=state.payload.summary;const k=s.kernel_diff;const st=s.stability_counts||{},cols=s.tradingview_entry_columns||{};const items=[["Rows",s.rows],["Compared range",`${s.comparison_start||"not run"} -> ${s.comparison_end||""}`],["Tolerance",`${s.tolerance_bars} bar`],["Entry mismatch",s.entry_mismatch_count],["Exact mismatch",s.exact_entry_mismatch_count],["Matched/miss/extra",`${s.matched_entry_count}/${s.missing_entry_count}/${s.extra_entry_count}`],["TV buy/sell",`${s.tradingview_counts.buy}/${s.tradingview_counts.sell}`],["Python buy/sell",`${s.python_counts.buy}/${s.python_counts.sell}`],["TV columns",`${cols.long||"none"} / ${cols.short||"none"}`],["Python raw/final",`${(st.raw_buy||0)+(st.raw_sell||0)} -> ${(st.final_buy||0)+(st.final_sell||0)}`],["Kernel MAE",k?k.mean_abs_error.toExponential(2):"n/a"],["MBB index",s.max_bars_back_index],["MBB time",s.max_bars_back_timestamp||"n/a"],["Export last",s.last_timestamp]];$("stats").innerHTML=items.map(x=>`<div class="stat"><span class="muted">${x[0]}</span><b>${x[1]}</b></div>`).join("")}
function renderMismatches(){const rows=state.payload.mismatches.slice(0,80).map(m=>`<tr class="mismatch-row" data-bar="${m.bar_index}"><td>${m.timestamp}</td><td>${m.kind}</td><td>${m.python}</td><td>${m.tradingview}</td><td>${m.prediction??""}</td><td>${m.signal??""}</td><td>${m.bars_held??""}</td></tr>`).join("");$("mismatches").innerHTML=rows||'<tr><td colspan="7" class="ok">No marker mismatches in compared columns</td></tr>';document.querySelectorAll(".mismatch-row").forEach(row=>row.onclick=()=>focusBar(Number(row.dataset.bar)))}
function renderLatestEntries(){const rows=(state.payload.latest_tradingview_entries||[]).slice().reverse().map(e=>`<tr><td>${e.timestamp}</td><td>${e.side}</td><td>${e.price}</td><td>${e.open}</td><td>${e.high}</td><td>${e.low}</td><td>${e.close}</td></tr>`).join("");$("latestEntries").innerHTML=rows||'<tr><td colspan="7">No TradingView Buy/Sell entries found in export</td></tr>'}
function renderChart(){
const svg=$("chart"),bars=state.payload.chart.bars.slice(state.viewStart,state.viewEnd+1);svg.innerHTML="";
if(!bars.length){const e=document.createElementNS("http://www.w3.org/2000/svg","text");e.setAttribute("x",24);e.setAttribute("y",36);e.setAttribute("fill","#8b949e");e.textContent="Settings loaded. Click Run validation to draw candles and markers.";svg.appendChild(e);return}
const W=svg.clientWidth,H=svg.clientHeight,left=56,right=14,top=24,bottom=62,plotW=Math.max(1,W-left-right),plotH=Math.max(1,H-top-bottom);
const hi=Math.max(...bars.map(b=>b.high),...bars.map(b=>b.yhat1??-Infinity),...bars.map(b=>b.tv_yhat1??-Infinity));
const lo=Math.min(...bars.map(b=>b.low),...bars.map(b=>b.yhat1??Infinity),...bars.map(b=>b.tv_yhat1??Infinity));
const x=i=>left+i*plotW/Math.max(1,bars.length-1),y=v=>top+plotH-(v-lo)*plotH/Math.max(1e-9,hi-lo);
const add=(tag,a)=>{const e=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const k in a)e.setAttribute(k,a[k]);svg.appendChild(e);return e};
const fmtTime=ms=>{const d=new Date(ms);return `${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`};
for(let i=0;i<6;i++){const yy=top+i*plotH/5;add("line",{x1:left,y1:yy,x2:W-right,y2:yy,stroke:"#1d2730"});add("text",{x:6,y:yy+4,fill:"#8b949e","font-size":10}).textContent=(hi-(hi-lo)*i/5).toFixed(1)}
const tickCount=Math.min(8,Math.max(2,Math.floor(W/150)));
for(let i=0;i<tickCount;i++){const bi=Math.round(i*(bars.length-1)/Math.max(1,tickCount-1)),xx=x(bi);add("line",{x1:xx,y1:top,x2:xx,y2:top+plotH,stroke:"#18212a"});add("line",{x1:xx,y1:top+plotH,x2:xx,y2:top+plotH+5,stroke:"#52606d"});add("text",{x:xx,y:H-24,fill:"#b8c7d9","font-size":11,"text-anchor":i===0?"start":i===tickCount-1?"end":"middle"}).textContent=fmtTime(bars[bi].time_ms)}
add("line",{x1:left,y1:top+plotH,x2:W-right,y2:top+plotH,stroke:"#52606d"});
const boundary=state.payload.summary.max_bars_back_index;
if(boundary>=bars[0].bar_index&&boundary<=bars[bars.length-1].bar_index){const bi=bars.findIndex(b=>b.bar_index>=boundary),xx=x(Math.max(0,bi));add("line",{x1:xx,y1:top,x2:xx,y2:top+plotH,stroke:"#c084fc","stroke-width":1.5,"stroke-dasharray":"4 4"});add("text",{x:xx+5,y:top+13,fill:"#d8b4fe","font-size":11}).textContent="max bars back"}
bars.forEach((b,i)=>{const xx=x(i),c=b.close>=b.open?"var(--up)":"var(--dn)",w=Math.max(1,Math.min(9,plotW/bars.length*.62));add("line",{x1:xx,y1:y(b.high),x2:xx,y2:y(b.low),stroke:c});add("rect",{x:xx-w/2,y:Math.min(y(b.open),y(b.close)),width:w,height:Math.max(1,Math.abs(y(b.close)-y(b.open))),fill:c})});
drawLine(bars,"yhat1","#67b7ff","");drawLine(bars,"tv_yhat1","#ffd166","5 4");
state.payload.chart.decisions.filter(d=>d.bar_index>=bars[0].bar_index&&d.bar_index<=bars[bars.length-1].bar_index).forEach(d=>{const i=bars.findIndex(b=>b.bar_index===d.bar_index);if(i<0)return;const xx=x(i),yy=y(d.price),col=d.source==="python"?"#67b7ff":"#ffd166";if(d.source==="python"){const up=d.side==="long";const p=up?`${xx},${yy-10} ${xx-7},${yy+6} ${xx+7},${yy+6}`:`${xx},${yy+10} ${xx-7},${yy-6} ${xx+7},${yy-6}`;add("polygon",{points:p,fill:col,stroke:"#0b1220","stroke-width":1})}else{add("rect",{x:xx-5,y:yy-5,width:10,height:10,fill:"none",stroke:col,"stroke-width":2,transform:`rotate(45 ${xx} ${yy})`})}});
function drawLine(bs,key,col,dash){let pts=bs.map((b,i)=>b[key]==null?null:[x(i),y(b[key])]).filter(Boolean);if(pts.length>1)add("polyline",{points:pts.map(p=>p.join(",")).join(" "),fill:"none",stroke:col,"stroke-width":1.5,"stroke-dasharray":dash})}
}
function renderAll(){renderStats();renderMismatches();renderLatestEntries();renderChart()}
function zoom(f){const n=state.payload.chart.bars.length,mid=(state.viewStart+state.viewEnd)/2,span=Math.max(30,(state.viewEnd-state.viewStart+1)*f);state.viewStart=Math.max(0,Math.round(mid-span/2));state.viewEnd=Math.min(n-1,Math.round(mid+span/2));renderChart()}
function panBars(delta){const n=state.payload.chart.bars.length,span=state.viewEnd-state.viewStart,shift=Math.max(-span,Math.min(span,delta));let a=state.viewStart+shift,b=state.viewEnd+shift;if(a<0){b-=a;a=0}if(b>=n){a-=b-n+1;b=n-1}state.viewStart=Math.max(0,a);state.viewEnd=Math.max(state.viewStart,b);renderChart()}
function focusBar(barIndex){const bars=state.payload.chart.bars;if(!bars.length)return;const pos=bars.findIndex(b=>b.bar_index===barIndex);if(pos<0)return;const span=Math.max(80,Math.min(240,state.viewEnd-state.viewStart+1||160));state.viewStart=Math.max(0,pos-Math.floor(span/2));state.viewEnd=Math.min(bars.length-1,state.viewStart+span);renderChart()}
$("runBtn").onclick=runSimulation;$("zoomIn").onclick=()=>zoom(.7);$("zoomOut").onclick=()=>zoom(1.4);$("resetZoom").onclick=()=>{resetView();renderChart()};$("chart").addEventListener("wheel",e=>{e.preventDefault();zoom(e.deltaY>0?1.2:.8)});$("chart").addEventListener("pointerdown",e=>{state.drag=true;state.dragX=e.clientX;state.dragCarry=0;$("chart").classList.add("dragging");$("chart").setPointerCapture(e.pointerId)});$("chart").addEventListener("pointermove",e=>{if(!state.drag||!state.payload)return;const span=state.viewEnd-state.viewStart+1,plotW=Math.max(1,$("chart").clientWidth-70),dx=e.clientX-state.dragX;state.dragX=e.clientX;state.dragCarry+=(dx*span/plotW);const shift=Math.trunc(-state.dragCarry);if(shift){panBars(shift);state.dragCarry+=shift}});$("chart").addEventListener("pointerup",e=>{state.drag=false;state.dragCarry=0;$("chart").classList.remove("dragging");$("chart").releasePointerCapture(e.pointerId)});$("chart").addEventListener("pointerleave",()=>{state.drag=false;$("chart").classList.remove("dragging")});window.addEventListener("resize",renderChart);loadDefaults();
</script>
</body>
</html>"""


class _DiagnosticsServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        *,
        app_config: AppConfig,
        symbol: str,
        csv_path: str,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.app_config = app_config
        self.symbol = symbol.upper()
        self.csv_path = csv_path


class _DiagnosticsHandler(BaseHTTPRequestHandler):
    server: _DiagnosticsServer

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(_json_safe(payload), default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self) -> None:
        body = HTML_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/ui", "/diagnostics"}:
            self._send_html()
            return
        if path == "/api/defaults":
            try:
                payload = build_lc_defaults_payload(
                    self.server.csv_path,
                    self.server.app_config,
                    self.server.symbol,
                    max_chart_points=0,
                )
                self._send_json(payload)
            except Exception as exc:  # pragma: no cover - exercised through browser usage.
                self._send_json({"error": str(exc)}, status=500)
            return
        self._send_json({"error": f"Not found: {path}"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/simulate":
            self._send_json({"error": f"Not found: {path}"}, status=404)
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            request = json.loads(body or "{}")
            csv_path = request.get("csv_path") or self.server.csv_path
            symbol = str(request.get("symbol") or self.server.symbol).upper()
            max_chart_points = int(request.get("max_chart_points") or 0)
            payload = build_lc_diagnostics_payload(
                csv_path,
                self.server.app_config,
                symbol,
                overrides=request.get("overrides") or {},
                max_chart_points=max_chart_points,
                window_mode=str(request.get("window_mode") or "full"),
                sample_size=int(request.get("sample_size") or 100),
                sample_offset=int(request.get("sample_offset") or 0),
                tolerance_bars=int(request["tolerance_bars"]) if "tolerance_bars" in request else 1,
                include_last_bar=bool(request.get("include_last_bar", False)),
            )
            self._send_json(payload)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)


def serve_diagnostics_ui(
    *,
    config_path: str | Path,
    symbol: str = "BTC",
    csv_path: str | Path = "btcusdt",
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    config_file = Path(config_path)
    if not config_file.exists():
        raise SystemExit(f"Config file not found: {config_file}")
    csv_file = _resolve_market_csv_path(csv_path)
    if not csv_file.exists():
        raise SystemExit(f"CSV file not found: {csv_file}")
    app_config = load_app_config(config_file)
    server = _DiagnosticsServer(
        (host, int(port)),
        _DiagnosticsHandler,
        app_config=app_config,
        symbol=symbol,
        csv_path=str(csv_file),
    )
    url = f"http://{host}:{int(port)}/"
    print(json.dumps({"status": "serving", "url": url, "csv_path": str(csv_file), "symbol": symbol.upper()}, indent=2))
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
