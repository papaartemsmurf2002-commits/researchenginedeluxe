from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from tradingbotsuite.strategies._helpers import (
    RuleBasedStrategy,
    RuleSignal,
    confidence_from_strength,
    numeric,
    session_allowed_indices,
    spaced_indices,
)


_REGIME_FILTER_VALUES = frozenset({"trend", "range", "shock", "unknown", "missing"})
_VOLATILITY_BUCKET_FILTER_VALUES = frozenset({"low", "medium", "high", "missing"})


@dataclass(frozen=True, slots=True)
class _SparseCandidate:
    row_index: int
    side: str
    score: float


@dataclass(frozen=True, slots=True)
class _FlowConfirmationContext:
    policy: str
    threshold: float = 0.0
    count_z_min: float = -10.0
    source_present: pd.Series | None = None
    context_missing: pd.Series | None = None
    latest_window: pd.Series | None = None
    signed_flow: pd.Series | None = None
    count_z: pd.Series | None = None


class SparseEventFilterStrategy(RuleBasedStrategy):
    strategy_id = "sparse_event_filter_v1"
    strategy_version = "v1"
    allowed_holding_periods = ("24h", "72h")
    required_feature_sets = ("features_price_trend_vol", "features_price_perp_aggflow_no_wt")

    def _signals(self, frame: pd.DataFrame) -> list[RuleSignal]:
        base_model = str(self.config.get("base_model", "trend_following")).strip().lower()
        if base_model == "volatility_breakout":
            candidates = self._volatility_candidates(frame)
        elif base_model == "trend_following":
            candidates = self._trend_candidates(frame)
        else:
            return []

        flow_context = self._flow_context(frame)
        candidates = [candidate for candidate in candidates if self._flow_confirmed(flow_context, candidate)]
        candidates = self._filter_allowed_session(frame, candidates)
        side_filter_stage = str(self.config.get("side_filter_stage", "pre_selection")).strip().lower()
        if side_filter_stage not in {"pre_selection", "post_selection"}:
            return []
        if side_filter_stage == "pre_selection":
            candidates = self._filter_allowed_sides(candidates)
        candidates = self._filter_allowed_market_context(frame, candidates)
        candidates = self._top_score_candidates(candidates)
        candidates = self._apply_cooldown_and_side_balance(candidates)
        if side_filter_stage == "post_selection":
            candidates = self._filter_allowed_sides(candidates)
        return [
            RuleSignal(
                candidate.row_index,
                candidate.side,
                min(1.0, max(0.01, candidate.score)),
                confidence_from_strength(candidate.score),
            )
            for candidate in candidates
        ]

    def _trend_candidates(self, frame: pd.DataFrame) -> list[_SparseCandidate]:
        threshold = float(self.config.get("slope_threshold", 0.12))
        max_chop = float(self.config.get("max_choppiness", 58.0))
        funding_penalty = float(self.config.get("funding_penalty_threshold", 0.00025))
        min_score = float(self.config.get("min_score", 0.0))
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 1)))
        slope = numeric(frame, "directional_slope_atr")
        chop = numeric(frame, "choppiness", 50.0)
        funding = numeric(frame, "funding_rate")
        candidates: list[_SparseCandidate] = []
        for index in allowed:
            raw = float(slope.iloc[index])
            chop_value = float(chop.iloc[index])
            if abs(raw) < threshold or chop_value > max_chop:
                continue
            side = "long" if raw > 0.0 else "short"
            funding_value = float(funding.iloc[index])
            if side == "long" and funding_value > funding_penalty:
                continue
            if side == "short" and funding_value < -funding_penalty:
                continue
            score = abs(raw) * max(0.05, (100.0 - max(0.0, chop_value)) / 100.0)
            if score < min_score:
                continue
            candidates.append(_SparseCandidate(index, side, score))
        return candidates

    def _volatility_candidates(self, frame: pd.DataFrame) -> list[_SparseCandidate]:
        shock_threshold = float(self.config.get("shock_threshold", 1.0))
        atr_threshold = float(self.config.get("atr_percentile_threshold", 0.45))
        min_score = float(self.config.get("min_score", 0.0))
        allowed = spaced_indices(frame, int(self.config.get("spacing_bars", 1)))
        shock = numeric(frame, "volatility_shock_zscore")
        atr = numeric(frame, "atr_percentile")
        slope = numeric(frame, "directional_slope_atr")
        candidates: list[_SparseCandidate] = []
        for index in allowed:
            shock_value = float(shock.iloc[index])
            atr_value = float(atr.iloc[index])
            raw_slope = float(slope.iloc[index])
            if shock_value < shock_threshold or atr_value < atr_threshold or raw_slope == 0.0:
                continue
            score = shock_value * max(0.0, atr_value) * max(0.5, min(2.0, abs(raw_slope) / 0.12))
            if score < min_score:
                continue
            side = "long" if raw_slope > 0.0 else "short"
            candidates.append(_SparseCandidate(index, side, score))
        return candidates

    def _filter_allowed_sides(self, candidates: list[_SparseCandidate]) -> list[_SparseCandidate]:
        allowed_sides = str(self.config.get("allowed_sides", "both")).strip().lower()
        if allowed_sides == "both":
            return candidates
        if allowed_sides in {"long", "short"}:
            return [candidate for candidate in candidates if candidate.side == allowed_sides]
        return []

    def _filter_allowed_session(self, frame: pd.DataFrame, candidates: list[_SparseCandidate]) -> list[_SparseCandidate]:
        allowed = session_allowed_indices(frame, self.config)
        return [candidate for candidate in candidates if candidate.row_index in allowed]

    def _filter_allowed_market_context(self, frame: pd.DataFrame, candidates: list[_SparseCandidate]) -> list[_SparseCandidate]:
        allowed_regimes = self._allowed_values("allowed_regimes", _REGIME_FILTER_VALUES)
        allowed_volatility_buckets = self._allowed_values("allowed_volatility_buckets", _VOLATILITY_BUCKET_FILTER_VALUES)
        if allowed_regimes == set() or allowed_volatility_buckets == set():
            return []
        if allowed_regimes is None and allowed_volatility_buckets is None:
            return candidates

        regimes = self._regime_labels(frame) if allowed_regimes is not None else None
        volatility_buckets = self._volatility_bucket_labels(frame) if allowed_volatility_buckets is not None else None
        if allowed_regimes is not None and regimes is None:
            return []
        if allowed_volatility_buckets is not None and volatility_buckets is None:
            return []

        filtered: list[_SparseCandidate] = []
        for candidate in candidates:
            if regimes is not None and str(regimes.iloc[candidate.row_index]).lower() not in allowed_regimes:
                continue
            if (
                volatility_buckets is not None
                and str(volatility_buckets.iloc[candidate.row_index]).lower() not in allowed_volatility_buckets
            ):
                continue
            filtered.append(candidate)
        return filtered

    def _allowed_values(self, key: str, valid_values: frozenset[str]) -> set[str] | None:
        raw = str(self.config.get(key, "any")).strip().lower()
        if raw in {"", "*", "all", "any", "off"}:
            return None
        values = {item.strip() for item in raw.replace("|", ",").replace(";", ",").split(",") if item.strip()}
        if not values or not values <= valid_values:
            return set()
        return values

    def _regime_labels(self, frame: pd.DataFrame) -> pd.Series | None:
        for column in ("validation_regime", "top_regime_label", "regime"):
            if column in frame.columns:
                labels = frame[column].fillna("unknown").astype(str).str.strip().str.lower()
                return labels.mask(labels == "", "unknown")
        if "volatility_shock_zscore" not in frame.columns and "directional_slope_atr" not in frame.columns:
            return None
        volatility = (
            pd.to_numeric(frame["volatility_shock_zscore"], errors="coerce")
            if "volatility_shock_zscore" in frame.columns
            else pd.Series([float("nan")] * len(frame), index=frame.index)
        )
        slope = (
            pd.to_numeric(frame["directional_slope_atr"], errors="coerce")
            if "directional_slope_atr" in frame.columns
            else pd.Series([float("nan")] * len(frame), index=frame.index)
        )
        labels: list[str] = []
        for volatility_value, slope_value in zip(volatility.tolist(), slope.tolist()):
            if pd.notna(volatility_value) and abs(float(volatility_value)) >= 2.0:
                labels.append("shock")
            elif pd.notna(slope_value) and abs(float(slope_value)) >= 0.04:
                labels.append("trend")
            elif pd.notna(slope_value) or pd.notna(volatility_value):
                labels.append("range")
            else:
                labels.append("unknown")
        return pd.Series(labels, index=frame.index)

    def _volatility_bucket_labels(self, frame: pd.DataFrame) -> pd.Series | None:
        if "realized_volatility" in frame.columns:
            values = pd.to_numeric(frame["realized_volatility"], errors="coerce")
        elif "atr_percentile" in frame.columns:
            values = pd.to_numeric(frame["atr_percentile"], errors="coerce")
        else:
            return None
        labels: list[str] = []
        for value in values.tolist():
            if pd.isna(value):
                labels.append("missing")
            elif float(value) < 0.006:
                labels.append("low")
            elif float(value) < 0.015:
                labels.append("medium")
            else:
                labels.append("high")
        return pd.Series(labels, index=frame.index)

    def _flow_context(self, frame: pd.DataFrame) -> _FlowConfirmationContext:
        policy = str(self.config.get("flow_confirmation", "off")).strip().lower()
        if policy == "off":
            return _FlowConfirmationContext(policy=policy)
        if policy not in {"aligned", "contrarian"}:
            return _FlowConfirmationContext(policy=policy)
        return _FlowConfirmationContext(
            policy=policy,
            threshold=float(self.config.get("flow_abs_threshold", 0.0)),
            count_z_min=float(self.config.get("flow_count_z_min", -10.0)),
            source_present=numeric(frame, "quality_aggtrade_source_present"),
            context_missing=numeric(frame, "quality_aggtrade_context_missing", 1.0),
            latest_window=numeric(frame, "quality_aggtrade_latest_window_diagnostic"),
            signed_flow=numeric(frame, "agg_signed_quote_imbalance"),
            count_z=numeric(frame, "agg_trade_count_zscore"),
        )

    def _flow_confirmed(self, flow_context: _FlowConfirmationContext, candidate: _SparseCandidate) -> bool:
        if flow_context.policy == "off":
            return True
        if flow_context.policy not in {"aligned", "contrarian"}:
            return False
        if (
            flow_context.source_present is None
            or flow_context.context_missing is None
            or flow_context.latest_window is None
            or flow_context.signed_flow is None
            or flow_context.count_z is None
        ):
            return False
        source_present = flow_context.source_present.iloc[candidate.row_index]
        context_missing = flow_context.context_missing.iloc[candidate.row_index]
        latest_window = flow_context.latest_window.iloc[candidate.row_index]
        if float(source_present) < 0.5 or float(context_missing) > 0.5 or float(latest_window) > 0.5:
            return False
        signed_flow = float(flow_context.signed_flow.iloc[candidate.row_index])
        count_z = float(flow_context.count_z.iloc[candidate.row_index])
        if count_z < flow_context.count_z_min:
            return False
        direction = 1.0 if candidate.side == "long" else -1.0
        aligned_flow = signed_flow * direction
        if flow_context.policy == "aligned":
            return aligned_flow >= flow_context.threshold
        return aligned_flow <= -flow_context.threshold

    def _top_score_candidates(self, candidates: list[_SparseCandidate]) -> list[_SparseCandidate]:
        top_n = max(1, int(self.config.get("top_n_per_window", 1)))
        window_bars = max(1, int(self.config.get("score_window_bars", 96)))
        by_window: dict[int, list[_SparseCandidate]] = {}
        for candidate in candidates:
            by_window.setdefault(candidate.row_index // window_bars, []).append(candidate)
        selected: list[_SparseCandidate] = []
        for window_id in sorted(by_window):
            ranked = sorted(by_window[window_id], key=lambda item: (-item.score, item.row_index, item.side))
            selected.extend(ranked[:top_n])
        return sorted(selected, key=lambda item: item.row_index)

    def _apply_cooldown_and_side_balance(self, candidates: list[_SparseCandidate]) -> list[_SparseCandidate]:
        cooldown_bars = max(0, int(self.config.get("cooldown_bars", 0)))
        max_side_share = min(1.0, max(0.5, float(self.config.get("max_side_share", 1.0))))
        side_balance_min_trades = max(0, int(self.config.get("side_balance_min_trades", 0)))
        counts = {"long": 0, "short": 0}
        accepted: list[_SparseCandidate] = []
        last_index: int | None = None
        for candidate in candidates:
            if last_index is not None and candidate.row_index - last_index < cooldown_bars:
                continue
            prospective_total = len(accepted) + 1
            prospective_side_count = counts[candidate.side] + 1
            if (
                max_side_share < 1.0
                and len(accepted) >= side_balance_min_trades
                and prospective_side_count / prospective_total > max_side_share
            ):
                continue
            accepted.append(candidate)
            counts[candidate.side] += 1
            last_index = candidate.row_index
        return accepted
