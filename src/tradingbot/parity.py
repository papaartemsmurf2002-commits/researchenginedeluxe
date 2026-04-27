from __future__ import annotations

import json
import copy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tradingbot.lorentz import LorentzianClassifier
from tradingbot.models import AppConfig
from tradingbot.tv_backtest import run_tv_backtest


@dataclass(slots=True)
class ParityCheckResult:
    matched: bool
    compared_columns: list[str]
    first_divergence: dict | None
    missing_columns: list[str]
    tv_stats: dict[str, float]
    compared_rows: int = 0
    included_last_bar: bool = True
    preflight: dict[str, Any] | None = None
    report_files: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class EntryParityResult:
    matched: bool
    symbol: str
    mode: str
    compared_rows: int
    tv_entry_count: int
    python_entry_count: int
    matched_entry_count: int
    missing_entry_count: int
    extra_entry_count: int
    entry_match_rate: float
    ignored_exit_mismatch_count: int
    included_last_bar: bool
    tolerance_bars: int
    sample_size: int
    sample_offset: int
    sample_entry_count: int
    comparison_start: str | None
    comparison_end: str | None
    first_mismatch: dict[str, Any] | None
    mismatches: list[dict[str, Any]]
    stability_counts: dict[str, int] = field(default_factory=dict)
    hypothesis_rankings: list[dict[str, Any]] = field(default_factory=list)
    feature_probe_rankings: list[dict[str, Any]] = field(default_factory=list)
    report_files: dict[str, str] = field(default_factory=dict)


_COLUMN_SYNONYMS = {
    "timestamp": ["timestamp", "time", "Time"],
    "open": ["open", "Open"],
    "high": ["high", "High"],
    "low": ["low", "Low"],
    "close": ["close", "Close"],
    "volume": ["volume", "Volume"],
    "f1": ["f1", "feature_1"],
    "f2": ["f2", "feature_2"],
    "f3": ["f3", "feature_3"],
    "f4": ["f4", "feature_4"],
    "f5": ["f5", "feature_5"],
    "y_train": ["y_train", "yTrain", "training_label"],
    "yhat1": ["yhat1", "kernel_estimate_1", "Kernel Regression Estimate"],
    "yhat2": ["yhat2", "kernel_estimate_2"],
    "prediction": ["prediction"],
    "signal": ["signal"],
    "bars_held": ["bars_held", "barsHeld"],
    "signal_change": ["signal_change", "signalChange"],
    "bar_index": ["bar_index", "barIndex"],
    "last_bar_index": ["last_bar_index", "lastBarIndex"],
    "max_bars_back_index": ["max_bars_back_index", "maxBarsBackIndex"],
    "is_new_buy_signal": ["is_new_buy_signal", "isNewBuySignal"],
    "is_new_sell_signal": ["is_new_sell_signal", "isNewSellSignal"],
    "start_long_trade": ["start_long_trade", "startLongTrade", "Buy"],
    "start_short_trade": ["start_short_trade", "startShortTrade", "Sell"],
    "end_long_trade": ["end_long_trade", "endLongTrade", "StopBuy"],
    "end_short_trade": ["end_short_trade", "endShortTrade", "StopSell"],
    "is_early_signal_flip": ["is_early_signal_flip", "isEarlySignalFlip"],
    "is_bullish": ["is_bullish", "isBullish"],
    "is_bearish": ["is_bearish", "isBearish"],
    "alert_bullish": ["alert_bullish", "alertBullish"],
    "alert_bearish": ["alert_bearish", "alertBearish"],
    "volatility_filter": ["volatility_filter", "volatilityFilter"],
    "regime_filter": ["regime_filter", "regimeFilter"],
    "adx_filter": ["adx_filter", "adxFilter"],
    "filter_all": ["filter_all", "filterAll"],
    "ann_window_start": ["ann_window_start", "annWindowStart"],
    "ann_window_end": ["ann_window_end", "annWindowEnd"],
    "ann_considered_count": ["ann_considered_count", "annConsideredCount"],
    "ann_accepted_count": ["ann_accepted_count", "annAcceptedCount"],
    "neighbor_index_state": ["neighbor_index_state", "neighborIndexState"],
    "neighbor_label_state": ["neighbor_label_state", "neighborLabelState"],
    "accepted_index_state": ["accepted_index_state", "acceptedIndexState"],
    "accepted_label_state": ["accepted_label_state", "acceptedLabelState"],
    "neighbor_index_last": ["neighbor_index_last", "neighborIndexLast"],
    "neighbor_label_last": ["neighbor_label_last", "neighborLabelLast"],
    "distance_last": ["distance_last", "distanceLast"],
    "distance_state": ["distance_state", "distanceState"],
    "prediction_state": ["prediction_state", "predictionState"],
    "tv_total_wins": ["tv_total_wins", "totalWins"],
    "tv_total_losses": ["tv_total_losses", "totalLosses"],
    "tv_total_trades": ["tv_total_trades", "totalTrades"],
    "tv_total_early_signal_flips": ["tv_total_early_signal_flips", "totalEarlySignalFlips"],
    "tv_win_loss_ratio": ["tv_win_loss_ratio", "winLossRatio"],
    "tv_win_rate": ["tv_win_rate", "winRate"],
}
_NEIGHBOR_TAIL_COLUMNS: list[str] = []
for _tail_offset in range(10):
    _index_column = f"neighbor_index_tail_{_tail_offset}"
    _label_column = f"neighbor_label_tail_{_tail_offset}"
    _distance_column = f"neighbor_distance_tail_{_tail_offset}"
    _COLUMN_SYNONYMS[_index_column] = [_index_column, f"neighborIndexTail{_tail_offset}"]
    _COLUMN_SYNONYMS[_label_column] = [_label_column, f"neighborLabelTail{_tail_offset}"]
    _COLUMN_SYNONYMS[_distance_column] = [_distance_column, f"neighborDistanceTail{_tail_offset}"]
    _NEIGHBOR_TAIL_COLUMNS.extend([_index_column, _label_column, _distance_column])

_ENTRY_EXIT_MARKER_COLUMNS = {
    "start_long_trade",
    "start_short_trade",
    "end_long_trade",
    "end_short_trade",
}
_SHAPE_MARKER_ALIASES = {"Buy", "Sell", "StopBuy", "StopSell"}
_TRUE_STRINGS = {"true", "t", "1", "yes", "y"}
_FALSE_STRINGS = {"false", "f", "0", "no", "n", "nan", "none", "null", ""}

_COLUMN_GROUPS = {
    "features": ["f1", "f2", "f3", "f4", "f5"],
    "kernel": ["yhat1", "yhat2", "is_bullish", "is_bearish", "alert_bullish", "alert_bearish"],
    "ann": [
        "y_train",
        "prediction",
        "bar_index",
        "last_bar_index",
        "max_bars_back_index",
        "ann_window_start",
        "ann_window_end",
        "ann_considered_count",
        "ann_accepted_count",
        "neighbor_index_state",
        "neighbor_label_state",
        "accepted_index_state",
        "accepted_label_state",
        "neighbor_index_last",
        "neighbor_label_last",
        "distance_last",
        *_NEIGHBOR_TAIL_COLUMNS,
        "distance_state",
        "prediction_state",
    ],
    "signals": [
        "signal",
        "bars_held",
        "signal_change",
        "is_new_buy_signal",
        "is_new_sell_signal",
        "start_long_trade",
        "start_short_trade",
        "end_long_trade",
        "end_short_trade",
        "is_early_signal_flip",
        "volatility_filter",
        "regime_filter",
        "adx_filter",
        "filter_all",
    ],
    "stats": [
        "tv_total_wins",
        "tv_total_losses",
        "tv_total_trades",
        "tv_total_early_signal_flips",
        "tv_win_loss_ratio",
        "tv_win_rate",
    ],
}

_SUBSYSTEMS = {
    "f1": "feature_helper",
    "f2": "feature_helper",
    "f3": "feature_helper",
    "f4": "feature_helper",
    "f5": "feature_helper",
    "y_train": "ann_model",
    "prediction": "ann_model",
    "bar_index": "ann_model",
    "last_bar_index": "ann_model",
    "max_bars_back_index": "ann_model",
    "ann_window_start": "ann_model",
    "ann_window_end": "ann_model",
    "ann_considered_count": "ann_model",
    "ann_accepted_count": "ann_model",
    "neighbor_index_state": "ann_model",
    "neighbor_label_state": "ann_model",
    "accepted_index_state": "ann_model",
    "accepted_label_state": "ann_model",
    "neighbor_index_last": "ann_model",
    "neighbor_label_last": "ann_model",
    "distance_last": "ann_model",
    "distance_state": "ann_model",
    "prediction_state": "ann_model",
    "signal": "signal_logic",
    "bars_held": "signal_logic",
    "signal_change": "signal_logic",
    "is_new_buy_signal": "signal_logic",
    "is_new_sell_signal": "signal_logic",
    "start_long_trade": "signal_logic",
    "start_short_trade": "signal_logic",
    "end_long_trade": "signal_logic",
    "end_short_trade": "signal_logic",
    "is_early_signal_flip": "signal_logic",
    "volatility_filter": "feature_filter",
    "regime_filter": "feature_filter",
    "adx_filter": "feature_filter",
    "filter_all": "feature_filter",
    "yhat1": "kernel_helper",
    "yhat2": "kernel_helper",
    "is_bullish": "kernel_helper",
    "is_bearish": "kernel_helper",
    "alert_bullish": "kernel_helper",
    "alert_bearish": "kernel_helper",
    "tv_total_wins": "backtest_semantics",
    "tv_total_losses": "backtest_semantics",
    "tv_total_trades": "backtest_semantics",
    "tv_total_early_signal_flips": "backtest_semantics",
    "tv_win_loss_ratio": "backtest_semantics",
    "tv_win_rate": "backtest_semantics",
}
for _tail_column in _NEIGHBOR_TAIL_COLUMNS:
    _SUBSYSTEMS[_tail_column] = "ann_model"


def _marker_values_to_bool(values: pd.Series, *, shape_marker: bool) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)

    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().any():
        if shape_marker:
            return numeric.notna()
        return numeric.fillna(0).ne(0)

    strings = values.fillna("").astype(str).str.strip().str.lower()
    if shape_marker:
        return ~(strings.isin(_FALSE_STRINGS))

    result = strings.isin(_TRUE_STRINGS)
    numeric_strings = pd.to_numeric(strings, errors="coerce")
    numeric_mask = numeric_strings.notna()
    result.loc[numeric_mask] = numeric_strings.loc[numeric_mask].ne(0)
    return result.fillna(False).astype(bool)


def _normalize_tv_export(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    source_alias_by_canonical: dict[str, str] = {}
    for canonical, aliases in _COLUMN_SYNONYMS.items():
        for alias in aliases:
            if alias in normalized.columns:
                normalized = normalized.rename(columns={alias: canonical})
                source_alias_by_canonical[canonical] = alias
                break
    if "timestamp" in normalized.columns:
        if pd.api.types.is_numeric_dtype(normalized["timestamp"]):
            max_timestamp = float(normalized["timestamp"].dropna().max()) if normalized["timestamp"].notna().any() else 0.0
            unit = "ms" if max_timestamp > 10_000_000_000 else "s"
            normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], unit=unit, utc=True)
        else:
            normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], utc=True)
    for marker_column in _ENTRY_EXIT_MARKER_COLUMNS:
        if marker_column in normalized.columns:
            source_alias = source_alias_by_canonical.get(marker_column, marker_column)
            normalized[marker_column] = _marker_values_to_bool(
                normalized[marker_column],
                shape_marker=source_alias in _SHAPE_MARKER_ALIASES,
            )
    for column in normalized.columns:
        if normalized[column].dtype == object:
            lowered = normalized[column].astype(str).str.lower()
            if lowered.isin(["true", "false"]).all():
                normalized[column] = lowered.eq("true")
    return normalized


def _conflicting_merge_timestamps(left: pd.DataFrame, right: pd.DataFrame, overlap: list[str]) -> set[pd.Timestamp]:
    if not overlap:
        return set()
    aligned = left[["timestamp", *overlap]].merge(
        right[["timestamp", *overlap]],
        on="timestamp",
        how="inner",
        suffixes=("_left", "_right"),
    )
    if aligned.empty:
        return set()

    conflict_mask = pd.Series(False, index=aligned.index, dtype=bool)
    for column in overlap:
        left_values = aligned[f"{column}_left"]
        right_values = aligned[f"{column}_right"]
        both_present = left_values.notna() & right_values.notna()
        if not bool(both_present.any()):
            continue

        left_numeric = pd.to_numeric(left_values, errors="coerce")
        right_numeric = pd.to_numeric(right_values, errors="coerce")
        both_numeric = both_present & left_numeric.notna() & right_numeric.notna()
        numeric_conflicts = both_numeric & ~pd.Series(
            np.isclose(left_numeric.astype(float), right_numeric.astype(float), atol=1e-9, rtol=0.0, equal_nan=True),
            index=aligned.index,
        )
        text_present = both_present & ~both_numeric
        text_conflicts = text_present & (
            left_values.fillna("").astype(str).str.strip() != right_values.fillna("").astype(str).str.strip()
        )
        conflict_mask |= numeric_conflicts | text_conflicts

    return set(pd.to_datetime(aligned.loc[conflict_mask, "timestamp"], utc=True))


def merge_tv_exports(*frames: pd.DataFrame) -> pd.DataFrame:
    if not frames:
        raise ValueError("At least one TradingView export is required.")

    normalized_frames = [_normalize_tv_export(frame) for frame in frames]
    for idx, frame in enumerate(normalized_frames, start=1):
        if "timestamp" not in frame.columns:
            raise ValueError(f"TradingView export #{idx} has no timestamp/time column.")

    merged = normalized_frames[0].copy()
    for incoming in normalized_frames[1:]:
        overlap = [column for column in incoming.columns if column != "timestamp" and column in merged.columns]
        conflicts = _conflicting_merge_timestamps(merged, incoming, overlap)
        if conflicts:
            merged = merged[~merged["timestamp"].isin(conflicts)].copy()
            incoming = incoming[~incoming["timestamp"].isin(conflicts)].copy()
        merged = merged.merge(incoming, on="timestamp", how="outer", suffixes=("", "__incoming"))
        for column in overlap:
            incoming_column = f"{column}__incoming"
            if incoming_column in merged.columns:
                merged[column] = merged[column].combine_first(merged[incoming_column])
                merged = merged.drop(columns=[incoming_column])
    ordered_columns = ["timestamp", *[column for column in merged.columns if column != "timestamp"]]
    return merged[ordered_columns].sort_values("timestamp").reset_index(drop=True)


def _stringify_state(value: Any) -> str:
    if isinstance(value, tuple | list):
        return "|".join(_stringify_state(item) for item in value)
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _make_csv_friendly(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in output.columns:
        if output[column].dtype == object:
            output[column] = output[column].map(_stringify_state)
    return output


def format_parity_dump_for_csv(frame: pd.DataFrame) -> pd.DataFrame:
    return _make_csv_friendly(frame)


def _columns_for_selection(selection: str) -> list[str]:
    if selection == "all":
        columns: list[str] = []
        for group_columns in _COLUMN_GROUPS.values():
            columns.extend(group_columns)
        return list(dict.fromkeys(columns))
    if selection not in _COLUMN_GROUPS:
        raise ValueError(f"Unsupported parity column group '{selection}'.")
    return _COLUMN_GROUPS[selection]


def generate_parity_dump(base_df: pd.DataFrame, app_config: AppConfig, symbol: str) -> pd.DataFrame:
    strategy = app_config.strategies[symbol]
    signal_frame = LorentzianClassifier().generate(base_df, strategy)
    max_bars_back_index = max(len(signal_frame) - 1 - strategy.max_bars_back, 0) if len(signal_frame) - 1 >= strategy.max_bars_back else 0
    return run_tv_backtest(signal_frame, max_bars_back_index, app_config.backtest.use_worst_case).frame


def _strategy_kernel_profile(app_config: AppConfig, symbol: str) -> dict[str, float | int]:
    strategy = app_config.strategies[symbol]
    return {
        "lookback": int(strategy.kernel_lookback),
        "relative_weight": float(strategy.kernel_relative_weight),
        "regression_level": int(strategy.kernel_regression_level),
    }


def _kernel_profile_key(profile: dict[str, float | int]) -> tuple[int, float, int]:
    return (int(profile["lookback"]), float(profile["relative_weight"]), int(profile["regression_level"]))


def _kernel_preflight_profiles(app_config: AppConfig, symbol: str) -> list[dict[str, Any]]:
    active = _strategy_kernel_profile(app_config, symbol)
    candidates = [
        {"label": "active", **active},
        {"label": "original_lc_defaults", "lookback": 8, "relative_weight": 8.0, "regression_level": 25},
        {"label": "settings_txt_snapshot", "lookback": 20, "relative_weight": 8.0, "regression_level": 10},
        {"label": "btc_marker_snapshot", "lookback": 6, "relative_weight": 20.0, "regression_level": 30},
    ]
    seen: set[tuple[int, float, int]] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        key = _kernel_profile_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _kernel_profile_stats(
    base_df: pd.DataFrame,
    expected: pd.DataFrame,
    app_config: AppConfig,
    symbol: str,
    profile: dict[str, Any],
    *,
    skip_rows: int,
    include_last_bar: bool = True,
) -> dict[str, Any]:
    probe_config = copy.deepcopy(app_config)
    strategy = probe_config.strategies[symbol]
    strategy.kernel_lookback = int(profile["lookback"])
    strategy.kernel_relative_weight = float(profile["relative_weight"])
    strategy.kernel_regression_level = int(profile["regression_level"])

    ours = generate_parity_dump(base_df, probe_config, symbol)[["timestamp", "yhat1"]]
    merged = ours.merge(expected[["timestamp", "yhat1"]], on="timestamp", how="inner", suffixes=("_py", "_tv"))
    if skip_rows > 0:
        merged = merged.iloc[skip_rows:].reset_index(drop=True)
    if not include_last_bar and not merged.empty:
        merged = merged.iloc[:-1].reset_index(drop=True)
    comparable = merged["yhat1_py"].notna() & merged["yhat1_tv"].notna()
    compared_rows = int(comparable.sum())
    summary = {
        "label": str(profile["label"]),
        "lookback": int(profile["lookback"]),
        "relative_weight": float(profile["relative_weight"]),
        "regression_level": int(profile["regression_level"]),
        "merged_rows": int(len(merged)),
        "compared_rows": compared_rows,
        "mean_abs_error": None,
        "max_abs_error": None,
    }
    if compared_rows == 0:
        return summary
    absolute_error = (merged.loc[comparable, "yhat1_py"].astype(float) - merged.loc[comparable, "yhat1_tv"].astype(float)).abs()
    summary["mean_abs_error"] = float(absolute_error.mean())
    summary["max_abs_error"] = float(absolute_error.max())
    return summary


def _run_kernel_config_preflight(
    base_df: pd.DataFrame,
    tv_export_df: pd.DataFrame,
    app_config: AppConfig,
    symbol: str,
    *,
    tolerance: float,
    skip_rows: int,
    include_last_bar: bool = True,
) -> dict[str, Any]:
    expected = _normalize_tv_export(tv_export_df)
    if "timestamp" not in expected.columns or "yhat1" not in expected.columns:
        return {
            "checked": False,
            "status": "missing_kernel_export",
            "reason": "TV export has no normalized timestamp/yhat1 kernel column.",
        }

    candidates = [
        _kernel_profile_stats(base_df, expected, app_config, symbol, profile, skip_rows=skip_rows, include_last_bar=include_last_bar)
        for profile in _kernel_preflight_profiles(app_config, symbol)
    ]
    active = next((candidate for candidate in candidates if candidate["label"] == "active"), candidates[0] if candidates else None)
    measurable = [candidate for candidate in candidates if candidate["mean_abs_error"] is not None]
    if not measurable or active is None:
        return {
            "checked": True,
            "status": "insufficient_data",
            "active": active,
            "best_candidate": None,
            "candidates": candidates,
        }

    best = min(measurable, key=lambda item: (float(item["mean_abs_error"]), float(item["max_abs_error"] or 0.0)))
    near_zero_threshold = max(float(tolerance), 0.01)
    active_mae = float(active["mean_abs_error"])
    best_mae = float(best["mean_abs_error"])
    status = "passed" if active_mae <= near_zero_threshold else "inconclusive"
    reason = None
    if (
        best["label"] != "active"
        and best_mae <= near_zero_threshold
        and active_mae > max(near_zero_threshold * 10.0, best_mae + near_zero_threshold)
    ):
        status = "config_export_mismatch"
        reason = "Exported yhat1 matches another kernel profile but not the active config."

    return {
        "checked": True,
        "status": status,
        "reason": reason,
        "threshold": near_zero_threshold,
        "active": active,
        "best_candidate": best,
        "candidates": candidates,
    }


def run_advanced_ta_compare(base_df: pd.DataFrame, app_config: AppConfig, symbol: str) -> dict[str, Any]:
    try:
        from advanced_ta import LorentzianClassification as AdvancedLorentzianClassification
    except Exception as exc:
        return {
            "available": False,
            "reason": f"advanced-ta is not installed or could not be imported: {exc}",
            "install": "pip install advanced-ta",
        }

    strategy = app_config.strategies[symbol]
    frame = base_df.copy()
    if "date" not in frame.columns:
        frame["date"] = frame["timestamp"] if "timestamp" in frame.columns else frame.index
    features = [
        AdvancedLorentzianClassification.Feature(name, param_a, param_b)
        for name, param_a, param_b in strategy.feature_definitions[: strategy.feature_count]
    ]
    settings = AdvancedLorentzianClassification.Settings(
        source=frame[strategy.source],
        neighborsCount=strategy.neighbors_count,
        maxBarsBack=strategy.max_bars_back,
        useDynamicExits=strategy.use_dynamic_exits,
        useEmaFilter=strategy.use_ema_filter,
        emaPeriod=strategy.ema_period,
        useSmaFilter=strategy.use_sma_filter,
        smaPeriod=strategy.sma_period,
    )
    kernel_filter = AdvancedLorentzianClassification.KernelFilter(
        useKernelSmoothing=strategy.use_kernel_smoothing,
        lookbackWindow=strategy.kernel_lookback,
        relativeWeight=strategy.kernel_relative_weight,
        regressionLevel=strategy.kernel_regression_level,
        crossoverLag=strategy.kernel_lag,
    )
    filter_settings = AdvancedLorentzianClassification.FilterSettings(
        useVolatilityFilter=strategy.use_volatility_filter,
        useRegimeFilter=strategy.use_regime_filter,
        useAdxFilter=strategy.use_adx_filter,
        regimeThreshold=strategy.regime_threshold,
        adxThreshold=strategy.adx_threshold,
        kernelFilter=kernel_filter,
    )
    advanced = AdvancedLorentzianClassification(frame, features=features, settings=settings, filterSettings=filter_settings).data
    ours = generate_parity_dump(base_df, app_config, symbol)
    if "timestamp" not in advanced.columns and "date" in advanced.columns:
        advanced = advanced.rename(columns={"date": "timestamp"})
    if "timestamp" in advanced.columns:
        advanced["timestamp"] = pd.to_datetime(advanced["timestamp"], utc=True)
    merged = ours.merge(advanced, on="timestamp", how="inner", suffixes=("_py", "_advanced_ta"))
    compared = {}
    for py_col, advanced_col in [
        ("prediction", "prediction"),
        ("signal", "signal"),
        ("bars_held", "barsHeld"),
        ("start_long_trade", "startLongTrade"),
        ("start_short_trade", "startShortTrade"),
        ("end_long_trade", "endLongTrade"),
        ("end_short_trade", "endShortTrade"),
    ]:
        left = f"{py_col}_py"
        right = f"{advanced_col}_advanced_ta"
        if left in merged.columns and right in merged.columns:
            compared[py_col] = int((merged[left].map(_stringify_state) == merged[right].map(_stringify_state)).sum())
    return {
        "available": True,
        "rows": int(len(merged)),
        "matched_counts_by_column": compared,
        "note": "advanced-ta is a research comparison only; it is not used as the production parity source.",
    }


def _bool_marker(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    base_column = column.removesuffix("_tv").removesuffix("_py")
    return _marker_values_to_bool(frame[column], shape_marker=base_column in _SHAPE_MARKER_ALIASES)


def _entry_set(frame: pd.DataFrame, long_column: str, short_column: str) -> set[tuple[pd.Timestamp, str]]:
    entries: set[tuple[pd.Timestamp, str]] = set()
    long_markers = _bool_marker(frame, long_column)
    short_markers = _bool_marker(frame, short_column)
    for idx, row in frame.iterrows():
        timestamp = pd.Timestamp(row["timestamp"])
        if bool(long_markers.loc[idx]):
            entries.add((timestamp, "long"))
        if bool(short_markers.loc[idx]):
            entries.add((timestamp, "short"))
    return entries


def _entry_events(frame: pd.DataFrame, long_column: str, short_column: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    long_markers = _bool_marker(frame, long_column)
    short_markers = _bool_marker(frame, short_column)
    for position, (idx, row) in enumerate(frame.iterrows()):
        timestamp = pd.Timestamp(row["timestamp"])
        if bool(long_markers.loc[idx]):
            events.append({"position": int(position), "timestamp": timestamp, "side": "long", "row": row})
        if bool(short_markers.loc[idx]):
            events.append({"position": int(position), "timestamp": timestamp, "side": "short", "row": row})
    return events


def _match_entry_events(
    python_events: list[dict[str, Any]],
    tv_events: list[dict[str, Any]],
    tolerance_bars: int,
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    tolerance = max(int(tolerance_bars), 0)
    unused_python = set(range(len(python_events)))
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    missing: list[dict[str, Any]] = []
    for tv_event in tv_events:
        candidates = [
            py_idx
            for py_idx in unused_python
            if python_events[py_idx]["side"] == tv_event["side"]
            and abs(int(python_events[py_idx]["position"]) - int(tv_event["position"])) <= tolerance
        ]
        if not candidates:
            missing.append(tv_event)
            continue
        best_idx = min(
            candidates,
            key=lambda py_idx: (
                abs(int(python_events[py_idx]["position"]) - int(tv_event["position"])),
                int(python_events[py_idx]["position"]),
            ),
        )
        unused_python.remove(best_idx)
        matches.append((python_events[best_idx], tv_event))
    extra = [python_events[py_idx] for py_idx in sorted(unused_python, key=lambda idx: python_events[idx]["position"])]
    return matches, missing, extra


def _entry_window_from_tv(
    merged: pd.DataFrame,
    *,
    mode: str,
    sample_size: int,
    sample_offset: int,
) -> tuple[pd.DataFrame, list[tuple[pd.Timestamp, str]]]:
    tv_entries = sorted(_entry_set(merged, "start_long_trade_tv", "start_short_trade_tv"), key=lambda item: (item[0], item[1]))
    if mode == "full" or not tv_entries:
        return merged, tv_entries
    if mode == "latest":
        selected = tv_entries[-sample_size:]
    elif mode == "sample":
        start = max(int(sample_offset), 0)
        selected = tv_entries[start : start + max(int(sample_size), 1)]
    else:
        raise ValueError("Entry parity mode must be 'sample', 'full', or 'latest'.")
    if not selected:
        return merged.iloc[0:0].copy(), []
    start_ts = selected[0][0]
    end_ts = selected[-1][0]
    window = merged[(merged["timestamp"] >= start_ts) & (merged["timestamp"] <= end_ts)].copy()
    return window, selected


def _feature_snapshot(row: pd.Series) -> dict[str, Any]:
    return {column: row[column] for column in ["f1", "f2", "f3", "f4", "f5"] if column in row.index}


def _classify_entry_mismatch(row: pd.Series, side: str, *, python_expected: bool, tv_expected: bool) -> str:
    if bool(row.get("current_feature_has_na", False)):
        return "feature_helper_na_warmup"
    prediction = row.get("prediction")
    signal = row.get("signal")
    if tv_expected and not python_expected:
        if side == "long" and (pd.isna(prediction) or float(prediction) <= 0):
            return "ann_model_prediction"
        if side == "short" and (pd.isna(prediction) or float(prediction) >= 0):
            return "ann_model_prediction"
        if side == "long" and int(signal) != 1:
            return "signal_logic"
        if side == "short" and int(signal) != -1:
            return "signal_logic"
        return "entry_gate"
    if python_expected and not tv_expected:
        return "extra_python_entry"
    return "unknown"


def _entry_mismatches(window: pd.DataFrame, max_items: int = 500) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    comparisons = [
        ("long", "start_long_trade_py", "start_long_trade_tv"),
        ("short", "start_short_trade_py", "start_short_trade_tv"),
    ]
    for _, row in window.iterrows():
        for side, py_column, tv_column in comparisons:
            py_value = bool(row.get(py_column, False))
            tv_value = bool(row.get(tv_column, False))
            if py_value == tv_value:
                continue
            mismatches.append(
                {
                    "timestamp": str(row["timestamp"]),
                    "side": side,
                    "python": py_value,
                    "tradingview": tv_value,
                    "prediction": _stringify_state(row.get("prediction")),
                    "signal": _stringify_state(row.get("signal")),
                    "bars_held": _stringify_state(row.get("bars_held")),
                    "features": _feature_snapshot(row),
                    "neighbor_indexes": _stringify_state(row.get("neighbor_index_state")),
                    "neighbor_labels": _stringify_state(row.get("neighbor_label_state")),
                    "accepted_indexes": _stringify_state(row.get("accepted_index_state")),
                    "accepted_labels": _stringify_state(row.get("accepted_label_state")),
                    "root_cause_candidate": _classify_entry_mismatch(row, side, python_expected=py_value, tv_expected=tv_value),
                }
            )
            if len(mismatches) >= max_items:
                return mismatches
    return mismatches


def _event_mismatches(missing: list[dict[str, Any]], extra: list[dict[str, Any]], max_items: int = 500) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for kind, events in [("missing_python_entry", missing), ("extra_python_entry", extra)]:
        for event in events:
            row = event["row"]
            side = str(event["side"])
            is_missing = kind == "missing_python_entry"
            mismatches.append(
                {
                    "timestamp": str(row["timestamp"]),
                    "side": side,
                    "python": not is_missing,
                    "tradingview": is_missing,
                    "prediction": _stringify_state(row.get("prediction")),
                    "signal": _stringify_state(row.get("signal")),
                    "bars_held": _stringify_state(row.get("bars_held")),
                    "features": _feature_snapshot(row),
                    "neighbor_indexes": _stringify_state(row.get("neighbor_index_state")),
                    "neighbor_labels": _stringify_state(row.get("neighbor_label_state")),
                    "accepted_indexes": _stringify_state(row.get("accepted_index_state")),
                    "accepted_labels": _stringify_state(row.get("accepted_label_state")),
                    "root_cause_candidate": _classify_entry_mismatch(
                        row,
                        side,
                        python_expected=not is_missing,
                        tv_expected=is_missing,
                    ),
                }
            )
            if len(mismatches) >= max_items:
                return mismatches
    return sorted(mismatches, key=lambda item: (item["timestamp"], item["side"]))


def _run_entry_parity_for_config(
    base_df: pd.DataFrame,
    tv_export_df: pd.DataFrame,
    app_config: AppConfig,
    symbol: str,
    *,
    mode: str,
    sample_size: int,
    sample_offset: int,
    include_last_bar: bool,
    tolerance_bars: int,
) -> tuple[EntryParityResult, pd.DataFrame]:
    ours = generate_parity_dump(base_df, app_config, symbol)
    expected = _normalize_tv_export(tv_export_df)
    merged = ours.merge(expected, on="timestamp", how="inner", suffixes=("_py", "_tv"))
    if not include_last_bar and not expected.empty:
        newest_export_ts = expected["timestamp"].max()
        merged = merged[merged["timestamp"] < newest_export_ts].reset_index(drop=True)
    window, selected_tv_entries = _entry_window_from_tv(merged, mode=mode, sample_size=sample_size, sample_offset=sample_offset)
    python_events = _entry_events(window, "start_long_trade_py", "start_short_trade_py")
    tv_events = _entry_events(window, "start_long_trade_tv", "start_short_trade_tv")
    matched_events, missing_events, extra_events = _match_entry_events(python_events, tv_events, tolerance_bars)
    mismatches = _event_mismatches(missing_events, extra_events)

    py_stop_buy = _bool_marker(window, "end_long_trade_py")
    py_stop_sell = _bool_marker(window, "end_short_trade_py")
    tv_stop_buy = _bool_marker(window, "end_long_trade_tv")
    tv_stop_sell = _bool_marker(window, "end_short_trade_tv")
    tv_count = len(tv_events)
    match_rate = float(len(matched_events) / tv_count) if tv_count else 1.0
    raw_py_long = _bool_marker(
        window,
        "raw_start_long_trade_py" if "raw_start_long_trade_py" in window else "raw_start_long_trade" if "raw_start_long_trade" in window else "start_long_trade_py",
    )
    raw_py_short = _bool_marker(
        window,
        "raw_start_short_trade_py" if "raw_start_short_trade_py" in window else "raw_start_short_trade" if "raw_start_short_trade" in window else "start_short_trade_py",
    )
    raw_entry_count = int(raw_py_long.sum() + raw_py_short.sum())
    final_entry_count = int(len(python_events))
    result = EntryParityResult(
        matched=not missing_events and not extra_events,
        symbol=symbol,
        mode=mode,
        compared_rows=int(len(window)),
        tv_entry_count=int(tv_count),
        python_entry_count=final_entry_count,
        matched_entry_count=int(len(matched_events)),
        missing_entry_count=int(len(missing_events)),
        extra_entry_count=int(len(extra_events)),
        entry_match_rate=match_rate,
        ignored_exit_mismatch_count=int(py_stop_buy.ne(tv_stop_buy).sum() + py_stop_sell.ne(tv_stop_sell).sum()),
        included_last_bar=include_last_bar,
        tolerance_bars=int(max(tolerance_bars, 0)),
        sample_size=int(sample_size),
        sample_offset=int(sample_offset),
        sample_entry_count=int(len(selected_tv_entries)),
        comparison_start=str(window["timestamp"].iloc[0]) if len(window) else None,
        comparison_end=str(window["timestamp"].iloc[-1]) if len(window) else None,
        first_mismatch=mismatches[0] if mismatches else None,
        mismatches=mismatches,
        stability_counts={
            "raw_buy": int(raw_py_long.sum()),
            "raw_sell": int(raw_py_short.sum()),
            "raw_total": raw_entry_count,
            "final_total": final_entry_count,
            "suppressed": max(raw_entry_count - final_entry_count, 0),
        },
    )
    return result, window


def _feature_parameter_probes(app_config: AppConfig, symbol: str, radius: int) -> list[tuple[AppConfig, dict[str, Any]]]:
    probes: list[tuple[AppConfig, dict[str, Any]]] = []
    strategy = app_config.strategies[symbol]
    feature_definitions = list(strategy.feature_definitions[: strategy.feature_count])
    for feature_idx, (name, param_a, param_b) in enumerate(feature_definitions):
        fields = [("param_a", 1, int(param_a))]
        if str(name).upper() != "ADX":
            fields.append(("param_b", 2, int(param_b)))
        for field_name, tuple_idx, old_value in fields:
            for delta in range(-abs(int(radius)), abs(int(radius)) + 1):
                if delta == 0:
                    continue
                new_value = max(1, old_value + delta)
                if new_value == old_value:
                    continue
                probe_config = copy.deepcopy(app_config)
                mutable_features = list(probe_config.strategies[symbol].feature_definitions)
                feature_tuple = list(mutable_features[feature_idx])
                feature_tuple[tuple_idx] = int(new_value)
                mutable_features[feature_idx] = tuple(feature_tuple)
                probe_config.strategies[symbol].feature_definitions = mutable_features
                probes.append(
                    (
                        probe_config,
                        {
                            "field": f"feature_{feature_idx + 1}.{field_name}",
                            "feature": str(name).upper(),
                            "old_value": int(old_value),
                            "new_value": int(new_value),
                            "delta": int(new_value - old_value),
                        },
                    )
                )
    return probes


def run_entry_parity_check(
    base_df: pd.DataFrame,
    tv_export_df: pd.DataFrame,
    app_config: AppConfig,
    symbol: str,
    *,
    mode: str = "sample",
    sample_size: int = 100,
    sample_offset: int = 0,
    include_last_bar: bool = False,
    tolerance_bars: int = 1,
    run_hypotheses: bool = True,
    run_feature_probes: bool = False,
    feature_probe_radius: int = 1,
    report_dir: str | Path | None = None,
) -> EntryParityResult:
    result, window = _run_entry_parity_for_config(
        base_df,
        tv_export_df,
        app_config,
        symbol,
        mode=mode,
        sample_size=sample_size,
        sample_offset=sample_offset,
        include_last_bar=include_last_bar,
        tolerance_bars=tolerance_bars,
    )
    rankings: list[dict[str, Any]] = []
    if run_hypotheses:
        for hypothesis_mode in [
            "research_marker_tuned",
            "pine_exact_static",
            "pine_exact_rolling_probe",
            "pine_exact_offset_probe",
            "pine_exact_adx_zero_prev_probe",
            "pine_exact_label_inverted_probe",
            "pine_exact_label_forward_probe",
            "pine_exact_label_forward_inverted_probe",
            "pine_exact_modulo_zero_probe",
            "pine_exact_modulo_one_probe",
            "pine_exact_modulo_two_probe",
            "pine_exact_modulo_three_probe",
        ]:
            probe_config = copy.deepcopy(app_config)
            probe_config.strategies[symbol].lc_parity_mode = hypothesis_mode
            probe_result, _probe_window = _run_entry_parity_for_config(
                base_df,
                tv_export_df,
                probe_config,
                symbol,
                mode=mode,
                sample_size=sample_size,
                sample_offset=sample_offset,
                include_last_bar=include_last_bar,
                tolerance_bars=tolerance_bars,
            )
            rankings.append(
                {
                    "lc_parity_mode": hypothesis_mode,
                    "entry_match_rate": probe_result.entry_match_rate,
                    "matched_entry_count": probe_result.matched_entry_count,
                    "tv_entry_count": probe_result.tv_entry_count,
                    "missing_entry_count": probe_result.missing_entry_count,
                    "extra_entry_count": probe_result.extra_entry_count,
                    "first_mismatch": probe_result.first_mismatch,
                }
            )
        rankings.sort(key=lambda item: (item["entry_match_rate"], -item["missing_entry_count"], -item["extra_entry_count"]), reverse=True)
    result.hypothesis_rankings = rankings
    feature_rankings: list[dict[str, Any]] = []
    if run_feature_probes:
        for probe_config, change in _feature_parameter_probes(app_config, symbol, feature_probe_radius):
            probe_result, _probe_window = _run_entry_parity_for_config(
                base_df,
                tv_export_df,
                probe_config,
                symbol,
                mode=mode,
                sample_size=sample_size,
                sample_offset=sample_offset,
                include_last_bar=include_last_bar,
                tolerance_bars=tolerance_bars,
            )
            feature_rankings.append(
                {
                    **change,
                    "entry_match_rate": probe_result.entry_match_rate,
                    "matched_entry_count": probe_result.matched_entry_count,
                    "tv_entry_count": probe_result.tv_entry_count,
                    "missing_entry_count": probe_result.missing_entry_count,
                    "extra_entry_count": probe_result.extra_entry_count,
                    "first_mismatch": probe_result.first_mismatch,
                }
            )
        feature_rankings.sort(key=lambda item: (item["entry_match_rate"], -item["missing_entry_count"], -item["extra_entry_count"]), reverse=True)
    result.feature_probe_rankings = feature_rankings

    if report_dir is not None:
        target = Path(report_dir)
        target.mkdir(parents=True, exist_ok=True)
        summary_path = target / f"{symbol.lower()}_entry_parity_summary.json"
        window_path = target / f"{symbol.lower()}_entry_parity_window.csv"
        _make_csv_friendly(window).to_csv(window_path, index=False)
        summary_path.write_text(json.dumps(asdict(result), indent=2, default=str), encoding="utf-8")
        result.report_files = {"summary": str(summary_path), "window": str(window_path)}
    return result


def run_parity_check(
    base_df: pd.DataFrame,
    tv_export_df: pd.DataFrame,
    app_config: AppConfig,
    symbol: str,
    *,
    tolerance: float = 1e-6,
    column_group: str = "all",
    report_dir: str | Path | None = None,
    skip_rows: int = 0,
    kernel_preflight: bool = False,
    include_last_bar: bool = True,
) -> ParityCheckResult:
    ours = generate_parity_dump(base_df, app_config, symbol)
    expected = _normalize_tv_export(tv_export_df)
    merged = ours.merge(expected, on="timestamp", how="inner", suffixes=("_py", "_tv"))
    if skip_rows > 0:
        merged = merged.iloc[skip_rows:].reset_index(drop=True)
    if not include_last_bar and not merged.empty:
        merged = merged.iloc[:-1].reset_index(drop=True)
    selected_columns = _columns_for_selection(column_group)
    preflight = (
        _run_kernel_config_preflight(
            base_df,
            tv_export_df,
            app_config,
            symbol,
            tolerance=tolerance,
            skip_rows=skip_rows,
            include_last_bar=include_last_bar,
        )
        if kernel_preflight
        else None
    )

    compared_columns: list[str] = []
    missing_columns: list[str] = []
    first_divergence: dict | None = None
    if preflight is not None and preflight.get("status") == "config_export_mismatch":
        first_divergence = {
            "timestamp": None,
            "column": "yhat1",
            "subsystem": "kernel_helper",
            "python_value": preflight.get("active"),
            "tv_value": preflight.get("best_candidate"),
            "tolerance": tolerance,
            "reason": "config_export_mismatch",
            "message": "Config/export mismatch: exported kernel estimate matches another kernel profile before the active config.",
        }
    else:
        for column in selected_columns:
            py_column = f"{column}_py"
            tv_column = f"{column}_tv"
            if py_column not in merged.columns or tv_column not in merged.columns:
                missing_columns.append(column)
                continue
            compared_columns.append(column)
            py_values = merged[py_column]
            tv_values = merged[tv_column]
            if pd.api.types.is_bool_dtype(py_values) or pd.api.types.is_bool_dtype(tv_values):
                mismatches = py_values.astype(bool) != tv_values.astype(bool)
            elif pd.api.types.is_numeric_dtype(py_values) and pd.api.types.is_numeric_dtype(tv_values):
                both_missing = py_values.isna() & tv_values.isna()
                close_enough = np.isclose(py_values.astype(float), tv_values.astype(float), atol=tolerance, rtol=0.0, equal_nan=True)
                mismatches = ~(both_missing | pd.Series(close_enough, index=merged.index))
            else:
                mismatches = py_values.map(_stringify_state) != tv_values.map(_stringify_state)
            if mismatches.any():
                mismatch_row = merged.loc[mismatches].iloc[0]
                first_divergence = {
                    "timestamp": str(mismatch_row["timestamp"]),
                    "column": column,
                    "subsystem": _SUBSYSTEMS.get(column, "unknown"),
                    "python_value": _stringify_state(mismatch_row[py_column]),
                    "tv_value": _stringify_state(mismatch_row[tv_column]),
                    "tolerance": tolerance,
                }
                break

    max_bars_back_index = max(len(ours) - 1 - app_config.strategies[symbol].max_bars_back, 0) if len(ours) - 1 >= app_config.strategies[symbol].max_bars_back else 0
    tv_stats = run_tv_backtest(ours, max_bars_back_index, app_config.backtest.use_worst_case).summary
    report_files: dict[str, str] = {}
    if report_dir is not None:
        target = Path(report_dir)
        target.mkdir(parents=True, exist_ok=True)
        python_dump_path = target / f"{symbol.lower()}_python_parity_dump.csv"
        merged_path = target / f"{symbol.lower()}_parity_merged.csv"
        summary_path = target / f"{symbol.lower()}_parity_summary.json"
        _make_csv_friendly(ours).to_csv(python_dump_path, index=False)
        _make_csv_friendly(merged).to_csv(merged_path, index=False)
        summary_payload = {
            "symbol": symbol,
            "matched": first_divergence is None,
            "compared_rows": int(len(merged)),
            "skip_rows": int(skip_rows),
            "included_last_bar": bool(include_last_bar),
            "compared_columns": compared_columns,
            "missing_columns": missing_columns,
            "first_divergence": first_divergence,
            "tv_stats": tv_stats,
            "preflight": preflight,
        }
        summary_path.write_text(json.dumps(summary_payload, indent=2, default=str), encoding="utf-8")
        report_files = {
            "python_dump": str(python_dump_path),
            "merged": str(merged_path),
            "summary": str(summary_path),
        }

    return ParityCheckResult(
        matched=first_divergence is None,
        compared_columns=compared_columns,
        first_divergence=first_divergence,
        missing_columns=missing_columns,
        tv_stats=tv_stats,
        compared_rows=int(len(merged)),
        included_last_bar=bool(include_last_bar),
        preflight=preflight,
        report_files=report_files,
    )
