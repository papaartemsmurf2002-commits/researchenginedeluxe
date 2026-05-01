from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from tradingbotsuite.strategies.hmm_knn.meta import compare_knn_and_meta


def build_hmm_knn_artifact_diagnostics(
    *,
    meta_predictions: pd.DataFrame,
    regime_posteriors: pd.DataFrame,
    neighbor_diagnostics: pd.DataFrame,
    feature_columns: list[str],
) -> dict[str, Any]:
    return {
        "neighbor_pool_size_by_regime": _neighbor_pool_size_by_regime(neighbor_diagnostics),
        "neighbor_distance_quality_distribution": _quality_distribution(neighbor_diagnostics),
        "accepted_rows_by_regime": _accepted_rows_by_regime(meta_predictions),
        "no_trade_reason_breakdown": _no_trade_reason_breakdown(meta_predictions, regime_posteriors),
        "feature_missingness_by_accepted_rejected_row": _feature_missingness_by_outcome(meta_predictions, feature_columns),
        "knn_only_vs_meta_filter": compare_knn_and_meta(meta_predictions),
        "wt3d_vs_no_wt_ablation": _wt3d_ablation_status(feature_columns),
    }


def _neighbor_pool_size_by_regime(neighbor_diagnostics: pd.DataFrame) -> dict[str, int]:
    if neighbor_diagnostics.empty or "query_regime" not in neighbor_diagnostics.columns:
        return {}
    populated = neighbor_diagnostics.dropna(subset=["neighbor_source_index"])
    return {
        str(int(regime)): int(group["neighbor_source_index"].nunique())
        for regime, group in populated.groupby("query_regime")
    }


def _quality_distribution(neighbor_diagnostics: pd.DataFrame) -> dict[str, float | None]:
    if neighbor_diagnostics.empty or "neighbor_distance_quality" not in neighbor_diagnostics.columns:
        return {"p05": None, "p50": None, "p95": None}
    quality = pd.to_numeric(neighbor_diagnostics["neighbor_distance_quality"], errors="coerce").dropna()
    if quality.empty:
        return {"p05": None, "p50": None, "p95": None}
    return {
        "p05": float(np.percentile(quality, 5)),
        "p50": float(np.percentile(quality, 50)),
        "p95": float(np.percentile(quality, 95)),
    }


def _accepted_rows_by_regime(meta_predictions: pd.DataFrame) -> dict[str, dict[str, int]]:
    if meta_predictions.empty or "top_regime_label" not in meta_predictions.columns:
        return {}
    result: dict[str, dict[str, int]] = {}
    for regime, group in meta_predictions.groupby("top_regime_label", dropna=False):
        key = "missing" if pd.isna(regime) else str(regime)
        result[key] = {
            "row_count": int(len(group)),
            "accepted_by_knn": int(group.get("accepted_by_knn", pd.Series([False] * len(group))).astype(bool).sum()),
            "accepted_by_meta": int(group.get("accepted_by_meta", pd.Series([False] * len(group))).astype(bool).sum()),
        }
    return dict(sorted(result.items()))


def _no_trade_reason_breakdown(meta_predictions: pd.DataFrame, regime_posteriors: pd.DataFrame) -> dict[str, int]:
    result = {
        "low_regime_probability": 0,
        "high_regime_entropy": 0,
        "recent_regime_flip": 0,
        "knn_skip": 0,
        "meta_filter_rejected": 0,
    }
    if not regime_posteriors.empty:
        if {"regime_no_trade", "max_regime_probability"}.issubset(regime_posteriors.columns):
            no_trade = regime_posteriors["regime_no_trade"].astype(bool)
            result["low_regime_probability"] = int((no_trade & (pd.to_numeric(regime_posteriors["max_regime_probability"], errors="coerce") < 0.6)).sum())
        if {"regime_no_trade", "posterior_entropy"}.issubset(regime_posteriors.columns):
            no_trade = regime_posteriors["regime_no_trade"].astype(bool)
            result["high_regime_entropy"] = int((no_trade & (pd.to_numeric(regime_posteriors["posterior_entropy"], errors="coerce") > 0.78)).sum())
        if "recent_regime_flip" in regime_posteriors.columns:
            result["recent_regime_flip"] = int(regime_posteriors["recent_regime_flip"].astype(bool).sum())
    if not meta_predictions.empty:
        if "knn_skip_reason" in meta_predictions.columns:
            result["knn_skip"] = int(meta_predictions["knn_skip_reason"].notna().sum())
        if {"accepted_by_knn", "accepted_by_meta"}.issubset(meta_predictions.columns):
            result["meta_filter_rejected"] = int((meta_predictions["accepted_by_knn"].astype(bool) & ~meta_predictions["accepted_by_meta"].astype(bool)).sum())
    return result


def _feature_missingness_by_outcome(meta_predictions: pd.DataFrame, feature_columns: list[str]) -> dict[str, dict[str, float]]:
    missing_columns = [f"missing_{column}" for column in feature_columns if f"missing_{column}" in meta_predictions.columns]
    if not missing_columns:
        return {"accepted": {}, "rejected": {}}
    accepted = meta_predictions["accepted_by_meta"].astype(bool) if "accepted_by_meta" in meta_predictions.columns else pd.Series([False] * len(meta_predictions))
    return {
        "accepted": _missing_rates(meta_predictions.loc[accepted], missing_columns),
        "rejected": _missing_rates(meta_predictions.loc[~accepted], missing_columns),
    }


def _missing_rates(frame: pd.DataFrame, missing_columns: list[str]) -> dict[str, float]:
    if frame.empty:
        return {column: 0.0 for column in missing_columns}
    return {column: float(pd.to_numeric(frame[column], errors="coerce").fillna(0.0).mean()) for column in missing_columns}


def _wt3d_ablation_status(feature_columns: list[str]) -> dict[str, Any]:
    wt_columns = [column for column in feature_columns if column.startswith("wt3d_")]
    return {
        "configured_with_wt3d": bool(wt_columns),
        "wt3d_feature_count": int(len(wt_columns)),
        "paired_no_wt_required": bool(wt_columns),
        "paired_no_wt_feature_pack": "full_context_no_wt3d",
    }
