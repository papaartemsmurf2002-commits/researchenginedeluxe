from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.core.features import RESEARCH_FEATURE_COLUMNS
from tradingbotsuite.research.config import ResearchPlan
from tradingbotsuite.research.live_readiness import research_artifact_boundary_metadata
from tradingbotsuite.research.modeling import fit_model_and_calibrator, score_frame, validate_training_sources


def _bucket_calibration(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bucket, bucket_frame in frame.groupby("confidence_bucket", dropna=False):
        if len(bucket_frame) == 0:
            continue
        rows.append(
            {
                "confidence_bucket": bucket,
                "row_count": len(bucket_frame),
                "mean_probability": float(bucket_frame["accept_probability"].mean()),
                "mean_label": float(bucket_frame["label_accept"].mean()),
                "absolute_error": abs(float(bucket_frame["accept_probability"].mean()) - float(bucket_frame["label_accept"].mean())),
            }
        )
    return pd.DataFrame(rows)


def _mean_absolute_calibration_error(frame: pd.DataFrame) -> float | None:
    calibration = _bucket_calibration(frame)
    if calibration.empty:
        return None
    return float(calibration["absolute_error"].mean())


def _profit_factor(pnl_series: pd.Series) -> float | None:
    gross_profit = float(pnl_series[pnl_series > 0].sum())
    gross_loss = abs(float(pnl_series[pnl_series < 0].sum()))
    if gross_loss == 0:
        return None if gross_profit == 0 else math.inf
    return gross_profit / gross_loss


def _comparison_metrics(frame: pd.DataFrame, accept_mask: pd.Series, fee_bps: float, slippage_bps: float) -> dict[str, Any]:
    selected = frame.loc[accept_mask].copy()
    if selected.empty:
        return {
            "trade_count": 0,
            "expectancy_after_cost": 0.0,
            "profit_factor": None,
            "tp_before_sl_rate": 0.0,
            "rejection_rate": 1.0,
            "basis_entry_bps_mean": None,
            "basis_exit_bps_mean": None,
        }
    total_cost_bps = fee_bps + slippage_bps
    selected["pnl_after_cost"] = selected["label_pnl_multiple"].astype(float) - (total_cost_bps / 10000.0)
    return {
        "trade_count": int(len(selected)),
        "expectancy_after_cost": float(selected["pnl_after_cost"].mean()),
        "profit_factor": _profit_factor(selected["pnl_after_cost"]),
        "tp_before_sl_rate": float((selected["label_exit_reason"] == "take_profit").mean()),
        "rejection_rate": float(1.0 - (len(selected) / len(frame))),
        "basis_entry_bps_mean": (
            float(selected["basis_bps"].dropna().mean()) if "basis_bps" in selected.columns and selected["basis_bps"].notna().any() else None
        ),
        "basis_exit_bps_mean": None,
    }


def _confidence_bucket_summary(frame: pd.DataFrame) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for bucket, bucket_frame in frame.groupby("confidence_bucket", dropna=False):
        accepted_frame = bucket_frame.loc[bucket_frame["accepted_by_model"].astype(bool)]
        summary.append(
            {
                "confidence_bucket": bucket,
                "row_count": int(len(bucket_frame)),
                "accepted_count": int(len(accepted_frame)),
                "accept_rate": float(len(accepted_frame) / len(bucket_frame)) if len(bucket_frame) else 0.0,
                "mean_probability": float(bucket_frame["accept_probability"].mean()),
                "label_rate": float(bucket_frame["label_accept"].mean()),
            }
        )
    return summary


def _acceptance_rate_stability(scored_slices: list[pd.DataFrame]) -> dict[str, Any]:
    per_split_rates = [
        float(scored_slice["accepted_by_model"].astype(bool).mean())
        for scored_slice in scored_slices
        if len(scored_slice) > 0
    ]
    if not per_split_rates:
        return {"per_split_acceptance_rate": [], "spread": None, "mean": None}
    return {
        "per_split_acceptance_rate": per_split_rates,
        "spread": max(per_split_rates) - min(per_split_rates),
        "mean": sum(per_split_rates) / len(per_split_rates),
    }


def replay_eval(artifact_manifest_path: Path, plan: ResearchPlan) -> Path:
    manifest = json.loads(artifact_manifest_path.read_text(encoding="utf-8"))
    artifact_dir = artifact_manifest_path.parent
    frame = pd.read_parquet(Path(manifest["dataset_path"])).sort_values("signal_bar_time_ms").reset_index(drop=True)
    validate_training_sources(frame)
    feature_columns = list(manifest.get("feature_columns") or RESEARCH_FEATURE_COLUMNS)
    initial_train = max(plan.evaluation.min_training_rows, int(len(frame) * plan.evaluation.train_fraction))
    calibration_size = max(plan.evaluation.min_calibration_rows, int(len(frame) * plan.evaluation.calibration_fraction))
    remaining = max(len(frame) - initial_train - calibration_size, 0)
    split_size = max(1, remaining // max(plan.evaluation.walk_forward_splits, 1)) if remaining > 0 else 1

    scored_slices: list[pd.DataFrame] = []
    walk_forward_summaries: list[dict[str, Any]] = []
    total_latency_ms = 0.0
    split_index = 0
    train_end = initial_train
    while train_end + calibration_size < len(frame) and split_index < plan.evaluation.walk_forward_splits:
        calibration_end = train_end + calibration_size
        test_end = len(frame) if split_index == plan.evaluation.walk_forward_splits - 1 else min(len(frame), calibration_end + split_size)
        train_frame = frame.iloc[:train_end].copy()
        calibration_frame = frame.iloc[train_end:calibration_end].copy()
        test_frame = frame.iloc[calibration_end:test_end].copy()
        if test_frame.empty:
            break
        model, calibrator = fit_model_and_calibrator(
            train_frame=train_frame,
            calibration_frame=calibration_frame,
            feature_columns=feature_columns,
            plan=plan,
        )
        start = time.perf_counter()
        scored_slice = score_frame(test_frame, model=model, calibrator=calibrator, feature_columns=feature_columns, plan=plan)
        total_latency_ms += (time.perf_counter() - start) * 1000.0
        scored_slices.append(scored_slice)
        split_metrics = _comparison_metrics(
            scored_slice,
            scored_slice["accepted_by_model"].astype(bool),
            plan.evaluation.fee_bps,
            plan.evaluation.slippage_bps,
        )
        split_baseline_metrics = _comparison_metrics(
            scored_slice,
            scored_slice["v1_baseline_accept"].astype(bool),
            plan.evaluation.fee_bps,
            plan.evaluation.slippage_bps,
        )
        walk_forward_summaries.append(
            {
                "split_index": split_index,
                "train_rows": len(train_frame),
                "calibration_rows": len(calibration_frame),
                "test_rows": len(test_frame),
                "train_end_time_ms": int(train_frame["signal_bar_time_ms"].iloc[-1]),
                "calibration_start_time_ms": int(calibration_frame["signal_bar_time_ms"].iloc[0]),
                "calibration_end_time_ms": int(calibration_frame["signal_bar_time_ms"].iloc[-1]),
                "test_start_time_ms": int(test_frame["signal_bar_time_ms"].iloc[0]),
                "test_end_time_ms": int(test_frame["signal_bar_time_ms"].iloc[-1]),
                "v2_expectancy_after_cost": split_metrics["expectancy_after_cost"],
                "baseline_expectancy_after_cost": split_baseline_metrics["expectancy_after_cost"],
                "trade_count": split_metrics["trade_count"],
            }
        )
        train_end = test_end
        split_index += 1

    if not scored_slices:
        raise ValueError("walk-forward evaluation could not produce any out-of-sample rows")
    scored = pd.concat(scored_slices, ignore_index=True)
    latency_ms = total_latency_ms / max(len(scored), 1)

    calibration_frame = _bucket_calibration(scored)
    (artifact_dir / "calibration.csv").write_text(calibration_frame.to_csv(index=False), encoding="utf-8")
    scored[
        ["signal_id", "signal_bar_time_ms", "accept_probability", "accepted_by_model", "label_accept", "label_exit_reason"]
    ].to_csv(artifact_dir / "rejected_vs_accepted.csv", index=False)

    comparison = {
        "v1_directional_entry_only": _comparison_metrics(
            scored,
            pd.Series([True] * len(scored)),
            plan.evaluation.fee_bps,
            plan.evaluation.slippage_bps,
        ),
        "v1_microstructure_baseline": _comparison_metrics(
            scored,
            scored["v1_baseline_accept"].astype(bool),
            plan.evaluation.fee_bps,
            plan.evaluation.slippage_bps,
        ),
        "v2_meta_label_acceptance": _comparison_metrics(
            scored,
            scored["accepted_by_model"].astype(bool),
            plan.evaluation.fee_bps,
            plan.evaluation.slippage_bps,
        ),
    }
    confidence_bucket_summary = _confidence_bucket_summary(scored)
    acceptance_rate_stability = _acceptance_rate_stability(scored_slices)
    mean_absolute_calibration_error = _mean_absolute_calibration_error(scored)
    improved_split_ratio = (
        sum(
            1
            for split in walk_forward_summaries
            if split["v2_expectancy_after_cost"] > split["baseline_expectancy_after_cost"]
        )
        / len(walk_forward_summaries)
    )
    promotion_failures: list[str] = []
    v2_metrics = comparison["v2_meta_label_acceptance"]
    baseline_metrics = comparison["v1_microstructure_baseline"]
    if v2_metrics["trade_count"] < plan.promotion.min_trade_count:
        promotion_failures.append("insufficient_trade_count")
    if v2_metrics["expectancy_after_cost"] < (
        baseline_metrics["expectancy_after_cost"] + plan.promotion.min_expectancy_improvement
    ):
        promotion_failures.append("expectancy_improvement_below_threshold")
    if mean_absolute_calibration_error is None:
        promotion_failures.append("missing_calibration_error")
    elif mean_absolute_calibration_error > plan.promotion.max_mean_absolute_calibration_error:
        promotion_failures.append("calibration_error_too_high")
    if improved_split_ratio < plan.promotion.min_improved_split_ratio:
        promotion_failures.append("insufficient_split_consistency")
    promotion_failures = list(dict.fromkeys([*promotion_failures, "research_only_not_live_promotable"]))

    metrics = {
        **research_artifact_boundary_metadata(),
        "model_version": manifest["model_version"],
        "calibration_version": manifest["calibration_version"],
        "artifact_manifest_version": manifest.get("artifact_manifest_version"),
        "row_count": int(len(scored)),
        "latency_ms_per_row": round(latency_ms, 6),
        "walk_forward_summaries": walk_forward_summaries,
        "comparison": comparison,
        "confidence_bucket_summary": confidence_bucket_summary,
        "acceptance_rate_stability": acceptance_rate_stability,
        "calibration_error_by_bucket": calibration_frame.to_dict(orient="records"),
        "mean_absolute_calibration_error": mean_absolute_calibration_error,
        "improved_split_ratio": improved_split_ratio,
        "promotion_failures": promotion_failures,
    }
    metrics_path = artifact_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return metrics_path
