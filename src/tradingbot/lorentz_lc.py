from __future__ import annotations

import numpy as np
import pandas as pd

from tradingbot.indicators import adx_filter, ema, feature_series, gaussian, normalize_frame, ohlc4, rational_quadratic, regime_filter, sma, volatility_filter
from tradingbot.models import StrategyConfig


def _bars_since(condition: pd.Series) -> pd.Series:
    result = []
    last_true_index: int | None = None
    for idx, value in enumerate(condition.fillna(False).tolist()):
        if value:
            last_true_index = idx
            result.append(0.0)
        elif last_true_index is None:
            result.append(np.nan)
        else:
            result.append(float(idx - last_true_index))
    return pd.Series(result, index=condition.index, dtype=float)


def _crossover(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left > right) & (left.shift(1) <= right.shift(1))


def _crossunder(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left < right) & (left.shift(1) >= right.shift(1))


def _shift_bool(series: pd.Series, periods: int) -> pd.Series:
    values = series.to_numpy(dtype=bool, na_value=False)
    return pd.Series(values, index=series.index, dtype=bool).shift(periods, fill_value=False).astype(bool)


def _half_up_round(value: float) -> int:
    value = float(value)
    if not np.isfinite(value):
        return 0
    if value >= 0:
        return int(np.floor(value + 0.5))
    return int(np.ceil(value - 0.5))


def _canonical_lc_mode(mode: str) -> str:
    if mode in {
        "static",
        "research_marker_tuned",
        "research_ann_modulo_0",
        "research_ann_modulo_1",
        "research_ann_modulo_2",
        "research_ann_modulo_3",
        "research_label_inverted",
        "research_label_forward",
        "research_label_forward_inverted",
        "research_barsheld_start0",
    }:
        return "static"
    if mode in {"rolling_research", "research_ann_rolling"}:
        return "rolling_research"
    raise ValueError(
        "StrategyConfig.lc_mode must be one of: "
        "static, rolling_research, research_ann_modulo_0..3, research_ann_rolling, "
        "research_marker_tuned, research_label_inverted, research_label_forward, "
        "research_label_forward_inverted, research_barsheld_start0."
    )


def _training_labels(source: pd.Series, mode: str) -> np.ndarray:
    if mode == "research_label_inverted":
        labels = np.where(source.shift(4) < source, 1, np.where(source.shift(4) > source, -1, 0))
    elif mode == "research_label_forward":
        labels = np.where(source.shift(-4) > source, 1, np.where(source.shift(-4) < source, -1, 0))
    elif mode == "research_label_forward_inverted":
        labels = np.where(source.shift(-4) > source, -1, np.where(source.shift(-4) < source, 1, 0))
    else:
        labels = np.where(source.shift(4) < source, -1, np.where(source.shift(4) > source, 1, 0))
    return np.nan_to_num(labels, nan=0).astype(int)


def _accept_modulo(modulo_index: int, mode: str) -> bool:
    remainder = int(modulo_index) % 4
    if mode in {"research_marker_tuned", "research_ann_modulo_0"}:
        return remainder == 0
    if mode == "research_ann_modulo_1":
        return remainder == 1
    if mode == "research_ann_modulo_2":
        return remainder == 2
    if mode == "research_ann_modulo_3":
        return remainder == 3
    return bool(remainder)


def _confirmed_entries(candidate: pd.Series, confirmation_bars: int) -> tuple[pd.Series, pd.Series]:
    bars = max(int(confirmation_bars), 1)
    candidate = candidate.fillna(False).astype(bool)
    if bars <= 1:
        return candidate, pd.Series(True, index=candidate.index, dtype=bool)
    confirmed = candidate.rolling(bars, min_periods=bars).sum().eq(bars).astype(bool)
    previous_confirmed = _shift_bool(confirmed, 1)
    first_confirmed = confirmed & ~previous_confirmed
    return first_confirmed.fillna(False), confirmed.fillna(False)


def _tail_value(state: tuple[int, ...] | tuple[float, ...], offset: int) -> float:
    if offset < len(state):
        return float(state[-1 - offset])
    return float("nan")


def _apply_entry_cooldown(
    start_long: pd.Series,
    start_short: pd.Series,
    cooldown_bars: int,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    cooldown = max(int(cooldown_bars), 0)
    if cooldown <= 0:
        allowed = pd.Series(True, index=start_long.index, dtype=bool)
        return start_long.fillna(False), start_short.fillna(False), allowed

    long_values = start_long.fillna(False).astype(bool).to_numpy()
    short_values = start_short.fillna(False).astype(bool).to_numpy()
    accepted_long = np.zeros(len(start_long), dtype=bool)
    accepted_short = np.zeros(len(start_short), dtype=bool)
    allowed_values = np.ones(len(start_long), dtype=bool)
    last_entry_index: int | None = None

    for idx, (long_signal, short_signal) in enumerate(zip(long_values, short_values, strict=False)):
        candidate = bool(long_signal or short_signal)
        if not candidate:
            continue
        allowed = last_entry_index is None or (idx - last_entry_index) > cooldown
        allowed_values[idx] = allowed
        if not allowed:
            continue
        accepted_long[idx] = bool(long_signal)
        accepted_short[idx] = bool(short_signal)
        last_entry_index = idx

    return (
        pd.Series(accepted_long, index=start_long.index, dtype=bool),
        pd.Series(accepted_short, index=start_short.index, dtype=bool),
        pd.Series(allowed_values, index=start_long.index, dtype=bool),
    )


class LorentzianClassifier:
    def generate(self, df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
        frame = normalize_frame(df)
        requested_lc_mode = getattr(config, "lc_mode", "static")
        lc_mode = _canonical_lc_mode(requested_lc_mode)
        adx_zero_previous_on_first_bar = True
        feature_names = [f"f{i + 1}" for i in range(config.feature_count)]
        for idx, (name, param_a, param_b) in enumerate(config.feature_definitions[: config.feature_count]):
            frame[feature_names[idx]] = feature_series(
                frame,
                name,
                param_a,
                param_b,
                adx_zero_previous_on_first_bar=adx_zero_previous_on_first_bar,
            )

        feature_matrix = frame[feature_names].to_numpy(dtype=float)
        source = frame[config.source].astype(float)
        y_train_series = _training_labels(source, requested_lc_mode)

        frame["volatility_filter"] = volatility_filter(frame, config.use_volatility_filter).fillna(False)
        frame["regime_filter"] = regime_filter(frame, config.regime_threshold, config.use_regime_filter).fillna(False)
        frame["adx_filter"] = adx_filter(frame, config.adx_threshold, config.use_adx_filter).fillna(False)
        filter_all = frame["volatility_filter"] & frame["regime_filter"] & frame["adx_filter"]

        frame["ema_value"] = ema(frame["close"], config.ema_period) if config.use_ema_filter else np.nan
        frame["sma_value"] = sma(frame["close"], config.sma_period) if config.use_sma_filter else np.nan
        is_ema_uptrend = pd.Series(True, index=frame.index) if not config.use_ema_filter else (frame["close"] > frame["ema_value"])
        is_ema_downtrend = pd.Series(True, index=frame.index) if not config.use_ema_filter else (frame["close"] < frame["ema_value"])
        is_sma_uptrend = pd.Series(True, index=frame.index) if not config.use_sma_filter else (frame["close"] > frame["sma_value"])
        is_sma_downtrend = pd.Series(True, index=frame.index) if not config.use_sma_filter else (frame["close"] < frame["sma_value"])

        max_bars_back_index = max(len(frame) - 1 - config.max_bars_back, 0) if len(frame) - 1 >= config.max_bars_back else 0

        predictions = np.zeros(len(frame), dtype=float)
        signals = np.zeros(len(frame), dtype=int)
        bars_held = np.zeros(len(frame), dtype=int)
        predictions_array: list[int] = []
        distances_array: list[float] = []
        neighbor_indices_array: list[int] = []
        prediction_states: list[tuple[int, ...]] = []
        distance_states: list[tuple[float, ...]] = []
        neighbor_index_states: list[tuple[int, ...]] = []
        accepted_index_states: list[tuple[int, ...]] = []
        accepted_label_states: list[tuple[int, ...]] = []
        current_feature_has_na_values = np.zeros(len(frame), dtype=bool)
        ann_window_start_values = np.zeros(len(frame), dtype=int)
        ann_window_end_values = np.zeros(len(frame), dtype=int)
        ann_considered_values = np.zeros(len(frame), dtype=int)
        ann_accepted_values = np.zeros(len(frame), dtype=int)
        current_prediction = 0.0
        current_signal = 0
        min_prediction_magnitude = max(float(getattr(config, "min_prediction_magnitude", 0.0)), 0.0)

        active_feature_count = min(config.feature_count, feature_matrix.shape[1])
        for current_idx in range(len(frame)):
            last_distance = -1.0
            size = min(config.max_bars_back - 1, current_idx)
            size_loop = min(config.max_bars_back - 1, size)
            if current_idx >= max_bars_back_index:
                current_features = feature_matrix[current_idx, :active_feature_count]
                current_feature_has_na_values[current_idx] = bool(np.isnan(current_features).any())
                if lc_mode == "rolling_research":
                    window_start = max(0, current_idx - size_loop)
                    historical_indices = np.arange(window_start, current_idx + 1, dtype=int)
                else:
                    window_start = 0
                    historical_indices = np.arange(0, size_loop + 1, dtype=int)
                historical_features = feature_matrix[historical_indices, :active_feature_count]
                distance_components = np.log1p(np.abs(current_features - historical_features))
                valid_distances = np.isfinite(distance_components).all(axis=1)
                distances = np.where(valid_distances, distance_components.sum(axis=1), np.nan)
                ann_window_start_values[current_idx] = int(window_start)
                ann_window_end_values[current_idx] = int(historical_indices[-1]) if len(historical_indices) else int(window_start)
                ann_considered_values[current_idx] = int(len(historical_indices))
                accepted_this_bar = 0
                accepted_indices_this_bar: list[int] = []
                accepted_labels_this_bar: list[int] = []
                for relative_idx, distance in enumerate(distances):
                    historical_idx = int(historical_indices[relative_idx])
                    modulo_index = relative_idx if lc_mode == "rolling_research" else historical_idx
                    if np.isfinite(distance) and distance >= last_distance and _accept_modulo(modulo_index, requested_lc_mode):
                        last_distance = float(distance)
                        distances_array.append(last_distance)
                        label = _half_up_round(float(y_train_series[historical_idx]))
                        predictions_array.append(label)
                        neighbor_indices_array.append(historical_idx)
                        accepted_indices_this_bar.append(historical_idx)
                        accepted_labels_this_bar.append(label)
                        accepted_this_bar += 1
                        if len(predictions_array) > config.neighbors_count:
                            pivot = _half_up_round(config.neighbors_count * 3 / 4)
                            pivot = min(max(pivot, 0), len(distances_array) - 1)
                            last_distance = distances_array[pivot]
                            distances_array.pop(0)
                            predictions_array.pop(0)
                            neighbor_indices_array.pop(0)
                ann_accepted_values[current_idx] = accepted_this_bar
                current_prediction = float(sum(predictions_array))
                accepted_index_states.append(tuple(accepted_indices_this_bar))
                accepted_label_states.append(tuple(accepted_labels_this_bar))
            else:
                accepted_index_states.append(tuple())
                accepted_label_states.append(tuple())
            predictions[current_idx] = current_prediction

            long_prediction_ok = current_prediction > 0 and (
                min_prediction_magnitude <= 0.0 or current_prediction >= min_prediction_magnitude
            )
            short_prediction_ok = current_prediction < 0 and (
                min_prediction_magnitude <= 0.0 or abs(current_prediction) >= min_prediction_magnitude
            )
            if long_prediction_ok and bool(filter_all.iloc[current_idx]):
                current_signal = 1
            elif short_prediction_ok and bool(filter_all.iloc[current_idx]):
                current_signal = -1
            signals[current_idx] = current_signal

            if current_idx == 0 and requested_lc_mode == "research_barsheld_start0":
                bars_held[current_idx] = 0
            elif current_idx == 0:
                bars_held[current_idx] = 1
            else:
                bars_held[current_idx] = 0 if signals[current_idx] != signals[current_idx - 1] else bars_held[current_idx - 1] + 1
            prediction_states.append(tuple(predictions_array))
            distance_states.append(tuple(distances_array))
            neighbor_index_states.append(tuple(neighbor_indices_array))

        signal_series = pd.Series(signals, index=frame.index, dtype=int)
        signal_change = pd.Series(False, index=frame.index, dtype=bool)
        if len(signal_series) > 1:
            signal_change.iloc[1:] = signal_series.iloc[1:].to_numpy() != signal_series.iloc[:-1].to_numpy()

        is_held_four = pd.Series(bars_held, index=frame.index, dtype=int).eq(4)
        is_held_less_than_four = pd.Series(bars_held, index=frame.index, dtype=int).between(1, 3)
        is_early_signal_flip = signal_change & (
            _shift_bool(signal_change, 1) | _shift_bool(signal_change, 2) | _shift_bool(signal_change, 3)
        )
        is_buy_signal = signal_series.eq(1) & is_ema_uptrend.fillna(False) & is_sma_uptrend.fillna(False)
        is_sell_signal = signal_series.eq(-1) & is_ema_downtrend.fillna(False) & is_sma_downtrend.fillna(False)
        is_last_signal_buy = signal_series.shift(4).eq(1) & _shift_bool(is_ema_uptrend, 4) & _shift_bool(is_sma_uptrend, 4)
        is_last_signal_sell = signal_series.shift(4).eq(-1) & _shift_bool(is_ema_downtrend, 4) & _shift_bool(is_sma_downtrend, 4)
        raw_is_new_buy = is_buy_signal & signal_change
        raw_is_new_sell = is_sell_signal & signal_change
        confirmation_bars = max(int(getattr(config, "min_signal_persistence_bars", 1)), 1)
        signal_has_changed = signal_change.fillna(False).astype(bool).cumsum().gt(0)
        is_new_buy, long_persistence_ok = _confirmed_entries(is_buy_signal & signal_has_changed, confirmation_bars)
        is_new_sell, short_persistence_ok = _confirmed_entries(is_sell_signal & signal_has_changed, confirmation_bars)
        if confirmation_bars <= 1:
            is_new_buy = raw_is_new_buy
            is_new_sell = raw_is_new_sell
            long_persistence_ok = is_buy_signal
            short_persistence_ok = is_sell_signal

        yhat1 = rational_quadratic(frame[config.source], config.kernel_lookback, config.kernel_relative_weight, config.kernel_regression_level)
        yhat2 = gaussian(frame[config.source], max(config.kernel_lookback - config.kernel_lag, 1), config.kernel_regression_level)
        was_bearish_rate = yhat1.shift(2) > yhat1.shift(1)
        was_bullish_rate = yhat1.shift(2) < yhat1.shift(1)
        is_bearish_rate = yhat1.shift(1) > yhat1
        is_bullish_rate = yhat1.shift(1) < yhat1
        is_bearish_change = is_bearish_rate & was_bullish_rate
        is_bullish_change = is_bullish_rate & was_bearish_rate
        is_bullish_cross_alert = _crossover(yhat2, yhat1).fillna(False)
        is_bearish_cross_alert = _crossunder(yhat2, yhat1).fillna(False)
        is_bullish_smooth = (yhat2 >= yhat1).fillna(False)
        is_bearish_smooth = (yhat2 <= yhat1).fillna(False)
        alert_bullish = is_bullish_cross_alert if config.use_kernel_smoothing else is_bullish_change.fillna(False)
        alert_bearish = is_bearish_cross_alert if config.use_kernel_smoothing else is_bearish_change.fillna(False)
        bullish_kernel = (is_bullish_smooth if config.use_kernel_smoothing else is_bullish_rate.fillna(False)) if config.use_kernel_filter else pd.Series(True, index=frame.index)
        bearish_kernel = (is_bearish_smooth if config.use_kernel_smoothing else is_bearish_rate.fillna(False)) if config.use_kernel_filter else pd.Series(True, index=frame.index)

        prediction_strength_ok = (
            pd.Series(True, index=frame.index, dtype=bool)
            if min_prediction_magnitude <= 0.0
            else pd.Series(np.abs(predictions) >= min_prediction_magnitude, index=frame.index, dtype=bool)
        )
        stability_ok = prediction_strength_ok.copy()
        if bool(getattr(config, "block_early_signal_flips", False)):
            stability_ok &= ~is_early_signal_flip.fillna(False)
        start_long_raw = is_new_buy & bullish_kernel.fillna(False) & is_ema_uptrend.fillna(False) & is_sma_uptrend.fillna(False)
        start_short_raw = is_new_sell & bearish_kernel.fillna(False) & is_ema_downtrend.fillna(False) & is_sma_downtrend.fillna(False)
        start_long = start_long_raw & stability_ok
        start_short = start_short_raw & stability_ok
        start_long, start_short, entry_cooldown_ok = _apply_entry_cooldown(
            start_long,
            start_short,
            int(getattr(config, "min_bars_between_entries", 0)),
        )

        bars_since_red_entry = _bars_since(start_short)
        bars_since_red_exit = _bars_since(alert_bullish)
        bars_since_green_entry = _bars_since(start_long)
        bars_since_green_exit = _bars_since(alert_bearish)
        is_valid_short_exit = (bars_since_red_exit > bars_since_red_entry).fillna(False)
        is_valid_long_exit = (bars_since_green_exit > bars_since_green_entry).fillna(False)
        end_long_dynamic = is_bearish_change.fillna(False) & _shift_bool(is_valid_long_exit, 1)
        end_short_dynamic = is_bullish_change.fillna(False) & _shift_bool(is_valid_short_exit, 1)
        end_long_strict = ((is_held_four & is_last_signal_buy) | (is_held_less_than_four & is_new_sell & is_last_signal_buy)) & _shift_bool(start_long, 4)
        end_short_strict = ((is_held_four & is_last_signal_sell) | (is_held_less_than_four & is_new_buy & is_last_signal_sell)) & _shift_bool(start_short, 4)
        dynamic_valid = (not config.use_ema_filter) and (not config.use_sma_filter) and (not config.use_kernel_smoothing)
        end_long = end_long_dynamic if config.use_dynamic_exits and dynamic_valid else end_long_strict
        end_short = end_short_dynamic if config.use_dynamic_exits and dynamic_valid else end_short_strict

        result = frame[["timestamp", "symbol", "open", "high", "low", "close", "volume"]].copy()
        result["f1"] = frame["f1"] if "f1" in frame else np.nan
        result["f2"] = frame["f2"] if "f2" in frame else np.nan
        result["f3"] = frame["f3"] if "f3" in frame else np.nan
        result["f4"] = frame["f4"] if "f4" in frame else np.nan
        result["f5"] = frame["f5"] if "f5" in frame else np.nan
        result["y_train"] = y_train_series
        result["prediction"] = predictions
        result["signal"] = signals
        result["bars_held"] = bars_held
        result["signal_change"] = signal_change.fillna(False)
        result["bar_index"] = np.arange(len(frame), dtype=int)
        result["last_bar_index"] = int(len(frame) - 1)
        result["max_bars_back_index"] = int(max_bars_back_index)
        result["is_new_buy_signal"] = raw_is_new_buy.fillna(False)
        result["is_new_sell_signal"] = raw_is_new_sell.fillna(False)
        result["is_early_signal_flip"] = is_early_signal_flip.fillna(False)
        result["prediction_strength_ok"] = prediction_strength_ok.fillna(False)
        result["long_persistence_ok"] = long_persistence_ok.fillna(False)
        result["short_persistence_ok"] = short_persistence_ok.fillna(False)
        result["entry_stability_ok"] = stability_ok.fillna(False)
        result["entry_cooldown_ok"] = entry_cooldown_ok.fillna(False)
        result["raw_start_long_trade"] = start_long_raw.fillna(False)
        result["raw_start_short_trade"] = start_short_raw.fillna(False)
        result["yhat1"] = yhat1
        result["yhat2"] = yhat2
        result["kernel_estimate"] = yhat1
        result["alert_bullish"] = alert_bullish.fillna(False)
        result["alert_bearish"] = alert_bearish.fillna(False)
        result["is_bullish"] = bullish_kernel.fillna(False)
        result["is_bearish"] = bearish_kernel.fillna(False)
        result["volatility_filter"] = frame["volatility_filter"].fillna(False)
        result["regime_filter"] = frame["regime_filter"].fillna(False)
        result["adx_filter"] = frame["adx_filter"].fillna(False)
        result["filter_all"] = filter_all.fillna(False)
        result["ema_uptrend"] = is_ema_uptrend.fillna(False)
        result["ema_downtrend"] = is_ema_downtrend.fillna(False)
        result["sma_uptrend"] = is_sma_uptrend.fillna(False)
        result["sma_downtrend"] = is_sma_downtrend.fillna(False)
        result["is_valid_long_exit"] = is_valid_long_exit.fillna(False)
        result["is_valid_short_exit"] = is_valid_short_exit.fillna(False)
        result["prediction_state"] = prediction_states
        result["distance_state"] = distance_states
        result["neighbor_index_state"] = neighbor_index_states
        result["neighbor_label_state"] = prediction_states
        result["accepted_index_state"] = accepted_index_states
        result["accepted_label_state"] = accepted_label_states
        result["current_feature_has_na"] = current_feature_has_na_values
        result["neighbor_index_last"] = [state[-1] if state else np.nan for state in neighbor_index_states]
        result["neighbor_label_last"] = [state[-1] if state else np.nan for state in prediction_states]
        result["distance_last"] = [state[-1] if state else np.nan for state in distance_states]
        diagnostic_tail_count = max(10, int(getattr(config, "neighbor_diagnostics", 10)))
        for tail_offset in range(diagnostic_tail_count):
            result[f"neighbor_index_tail_{tail_offset}"] = [
                _tail_value(state, tail_offset) for state in neighbor_index_states
            ]
            result[f"neighbor_label_tail_{tail_offset}"] = [
                _tail_value(state, tail_offset) for state in prediction_states
            ]
            result[f"neighbor_distance_tail_{tail_offset}"] = [
                _tail_value(state, tail_offset) for state in distance_states
            ]
        result["ann_window_start"] = ann_window_start_values
        result["ann_window_end"] = ann_window_end_values
        result["ann_considered_count"] = ann_considered_values
        result["ann_accepted_count"] = ann_accepted_values
        result["lc_mode"] = requested_lc_mode
        result["lc_mode_resolved"] = lc_mode
        result["start_long_trade"] = start_long.fillna(False) & config.allow_long
        result["start_short_trade"] = start_short.fillna(False) & config.allow_short
        result["end_long_trade"] = end_long.fillna(False)
        result["end_short_trade"] = end_short.fillna(False)
        result["atr_stop"] = ohlc4(frame)
        return result
