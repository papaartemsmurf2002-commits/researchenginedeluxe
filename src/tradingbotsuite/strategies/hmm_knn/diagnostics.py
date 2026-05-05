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
    feature_variant: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "neighbor_pool_size_by_regime": _neighbor_pool_size_by_regime(neighbor_diagnostics),
        "neighbor_pool_diagnostics_by_regime": _neighbor_pool_diagnostics_by_regime(neighbor_diagnostics),
        "fallback_rate_by_regime": _fallback_rate_by_regime(neighbor_diagnostics),
        "insufficient_pool_rate": _insufficient_pool_rate(neighbor_diagnostics),
        "compatible_mode_usage": _compatible_mode_usage(neighbor_diagnostics),
        "neighbor_distance_quality_distribution": _quality_distribution(neighbor_diagnostics),
        "accepted_rows_by_regime": _accepted_rows_by_regime(meta_predictions),
        "no_trade_reason_breakdown": _no_trade_reason_breakdown(meta_predictions, regime_posteriors),
        "feature_missingness_by_accepted_rejected_row": _feature_missingness_by_outcome(meta_predictions, feature_columns),
        "feature_variant_summary": dict(feature_variant or _feature_variant_summary(feature_columns)),
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


def _neighbor_pool_diagnostics_by_regime(neighbor_diagnostics: pd.DataFrame) -> dict[str, dict[str, float | int | str | None]]:
    required = {"query_regime", "candidate_count_before_regime_filter", "candidate_count_after_regime_filter", "selected_neighbor_count"}
    if neighbor_diagnostics.empty or not required.issubset(neighbor_diagnostics.columns):
        return {}
    result: dict[str, dict[str, float | int | str | None]] = {}
    primary = neighbor_diagnostics
    if "is_primary" in primary.columns:
        primary = primary.loc[primary["is_primary"].astype(bool)]
    primary = primary.drop_duplicates(subset=[column for column in ("source_row_index", "k", "weighting") if column in primary.columns])
    for regime, group in primary.groupby("query_regime", dropna=False):
        key = "missing" if pd.isna(regime) else str(int(regime))
        before = pd.to_numeric(group["candidate_count_before_regime_filter"], errors="coerce")
        after = pd.to_numeric(group["candidate_count_after_regime_filter"], errors="coerce")
        selected = pd.to_numeric(group["selected_neighbor_count"], errors="coerce")
        result[key] = {
            "row_count": int(len(group)),
            "candidate_count_before_mean": float(before.mean()) if len(before) else 0.0,
            "candidate_count_after_mean": float(after.mean()) if len(after) else 0.0,
            "selected_count_mean": float(selected.mean()) if len(selected) else 0.0,
            "insufficient_pool_count": int((group.get("knn_skip_reason") == "insufficient_neighbors").sum()) if "knn_skip_reason" in group else 0,
            "regime_match_mode": _first_non_null(group.get("regime_match_mode")),
        }
    return dict(sorted(result.items()))


def _fallback_rate_by_regime(neighbor_diagnostics: pd.DataFrame) -> dict[str, float]:
    if neighbor_diagnostics.empty or {"query_regime", "fallback_used"}.difference(neighbor_diagnostics.columns):
        return {}
    primary = neighbor_diagnostics
    if "is_primary" in primary.columns:
        primary = primary.loc[primary["is_primary"].astype(bool)]
    primary = primary.drop_duplicates(subset=[column for column in ("source_row_index", "k", "weighting") if column in primary.columns])
    return {
        ("missing" if pd.isna(regime) else str(int(regime))): float(group["fallback_used"].astype(bool).mean())
        for regime, group in primary.groupby("query_regime", dropna=False)
    }


def _insufficient_pool_rate(neighbor_diagnostics: pd.DataFrame) -> float:
    if neighbor_diagnostics.empty or "knn_skip_reason" not in neighbor_diagnostics.columns:
        return 0.0
    primary = neighbor_diagnostics
    if "is_primary" in primary.columns:
        primary = primary.loc[primary["is_primary"].astype(bool)]
    primary = primary.drop_duplicates(subset=[column for column in ("source_row_index", "k", "weighting") if column in primary.columns])
    if primary.empty:
        return 0.0
    return float(primary["knn_skip_reason"].eq("insufficient_neighbors").mean())


def _compatible_mode_usage(neighbor_diagnostics: pd.DataFrame) -> dict[str, Any]:
    if neighbor_diagnostics.empty or "regime_match_mode" not in neighbor_diagnostics.columns:
        return {"used": False, "row_count": 0}
    primary = neighbor_diagnostics
    if "is_primary" in primary.columns:
        primary = primary.loc[primary["is_primary"].astype(bool)]
    compatible = primary.loc[primary["regime_match_mode"].astype(str) == "compatible"]
    compatible = compatible.drop_duplicates(subset=[column for column in ("source_row_index", "k", "weighting") if column in compatible.columns])
    return {
        "used": bool(len(compatible)),
        "row_count": int(len(compatible)),
        "compatible_regime_labels": sorted(
            label
            for label in set(",".join(compatible.get("compatible_regime_labels", pd.Series(dtype=str)).dropna().astype(str)).split(","))
            if label
        ),
    }


def _feature_variant_summary(feature_columns: list[str]) -> dict[str, Any]:
    return {
        "feature_set_variant_id": "inline_feature_columns",
        "feature_set_source": "inline_config",
        "feature_count": int(len(feature_columns)),
        "wt3d_enabled": any(column.startswith("wt3d_") for column in feature_columns),
        "missingness_columns_present": [column for column in feature_columns if column.startswith("missing_")],
    }


def _first_non_null(series: pd.Series | None) -> str | None:
    if series is None:
        return None
    non_null = series.dropna()
    if non_null.empty:
        return None
    return str(non_null.iloc[0])


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
