from __future__ import annotations

import json
import math
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HMM_KNN_MONITORING_REPORT_VERSION = "v2-hmm-knn-monitoring-report-1"
_FEATURE_OUTAGE_THRESHOLD = 0.20
_REGIME_DRIFT_WARN_THRESHOLD = 0.35
_ENTROPY_WARN_THRESHOLD = 0.78
_NO_TRADE_WARN_THRESHOLD = 0.50
_NEIGHBOR_QUALITY_WARN_THRESHOLD = 0.25


def monitor_hmm_knn_artifact(manifest_path: Path) -> Path:
    """Write an observe-only monitoring report for an HMM/KNN research artifact."""
    manifest_path = manifest_path.expanduser()
    manifest = _read_json(manifest_path)
    if not manifest.get("research_only"):
        raise ValueError("HMM/KNN monitoring only supports research_only artifacts")

    required_paths = {
        "regime_posteriors": _resolve_artifact_path(manifest_path, manifest, "regime_posteriors_path"),
        "knn_predictions": _resolve_artifact_path(manifest_path, manifest, "knn_predictions_path"),
        "meta_predictions": _resolve_artifact_path(manifest_path, manifest, "meta_predictions_path"),
        "neighbor_diagnostics": _resolve_artifact_path(manifest_path, manifest, "neighbor_diagnostics_path"),
        "metrics": _resolve_artifact_path(manifest_path, manifest, "metrics_path"),
    }
    missing = {name: str(path) for name, path in required_paths.items() if not path.exists()}
    if missing:
        raise FileNotFoundError(f"HMM/KNN monitoring missing required artifact files: {missing}")

    regimes = pd.read_parquet(required_paths["regime_posteriors"])
    knn = pd.read_parquet(required_paths["knn_predictions"])
    meta = pd.read_parquet(required_paths["meta_predictions"])
    diagnostics = pd.read_csv(required_paths["neighbor_diagnostics"])
    metrics = _read_json(required_paths["metrics"])
    config = _read_optional_config(manifest_path, manifest)

    alerts: list[dict[str, Any]] = []
    feature_outages = _feature_outages(meta, config, alerts)
    entropy = _entropy_summary(regimes, alerts)
    regime_drift = _regime_drift(regimes, alerts)
    neighbor_quality = _neighbor_quality(knn, diagnostics, config, alerts)
    funding = _funding_summary(meta, alerts)
    calibration = _calibration_decay(meta, alerts)

    report = {
        "monitoring_report_version": HMM_KNN_MONITORING_REPORT_VERSION,
        "research_only": True,
        "promotion_ready": False,
        "observe_only": True,
        "artifact_identity": {
            "manifest_path": str(manifest_path),
            "artifact_manifest_sha256": _file_sha256(manifest_path),
            "artifact_manifest_version": manifest.get("artifact_manifest_version"),
            "plan_version": manifest.get("plan_version"),
            "plan_sha256": manifest.get("plan_sha256"),
            "symbol": manifest.get("symbol"),
            "asset_scope": manifest.get("asset_scope"),
            "row_count": manifest.get("row_count"),
            "config_path": manifest.get("config_path"),
            "dataset_path": manifest.get("dataset_path"),
        },
        "artifact_files": {name: str(path) for name, path in required_paths.items()},
        "source_metrics": {
            "research_only": bool(metrics.get("research_only")),
            "promotion_ready": bool(metrics.get("promotion_ready")),
            "promotion_failures": metrics.get("promotion_failures", []),
        },
        "feature_outages": feature_outages,
        "entropy_no_trade": entropy,
        "regime_distribution_drift": regime_drift,
        "neighbor_quality": neighbor_quality,
        "funding_costs": funding,
        "calibration_decay": calibration,
        "live_vs_replay_mismatch": "not_available",
        "alerts": alerts,
    }
    report_path = manifest_path.parent / "monitoring_report.json"
    report_path.write_text(json.dumps(_json_safe(report), indent=2, sort_keys=True), encoding="utf-8")
    return report_path


def _resolve_artifact_path(manifest_path: Path, manifest: dict[str, Any], key: str) -> Path:
    raw = manifest.get(key)
    if not raw:
        return manifest_path.parent / f"<missing:{key}>"
    path = Path(str(raw))
    if path.is_absolute():
        return path
    parent_candidate = manifest_path.parent / path
    return parent_candidate if parent_candidate.exists() else path


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_config(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    raw = manifest.get("config_path")
    if not raw:
        return {}
    path = Path(str(raw))
    if not path.is_absolute():
        parent_candidate = manifest_path.parent / path
        path = parent_candidate if parent_candidate.exists() else path
    if not path.exists():
        return {}
    return _read_json(path)


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _feature_outages(frame: pd.DataFrame, config: dict[str, Any], alerts: list[dict[str, Any]]) -> dict[str, Any]:
    hmm_features = list(((config.get("hmm") or {}).get("emission_features") or []))
    knn_features = list(((config.get("knn") or {}).get("feature_columns") or []))
    features = list(dict.fromkeys([*hmm_features, *knn_features]))
    rows: dict[str, dict[str, Any]] = {}
    high_outage: list[str] = []
    for feature in features:
        if feature not in frame.columns:
            rows[feature] = {"present": False, "missing_or_nonfinite_rate": 1.0}
            high_outage.append(feature)
            continue
        series = pd.to_numeric(frame[feature], errors="coerce")
        rate = float((series.isna() | ~np.isfinite(series)).mean()) if len(series) else 0.0
        rows[feature] = {"present": True, "missing_or_nonfinite_rate": rate}
        if rate > _FEATURE_OUTAGE_THRESHOLD:
            high_outage.append(feature)
    if high_outage:
        _append_alert(
            alerts,
            severity="warn",
            code="feature_outage",
            message="Configured HMM/KNN feature columns are missing or degraded in meta_predictions.",
            details={"features": high_outage[:20], "threshold": _FEATURE_OUTAGE_THRESHOLD},
        )
    return {
        "configured_feature_count": len(features),
        "high_outage_feature_count": len(high_outage),
        "outage_threshold": _FEATURE_OUTAGE_THRESHOLD,
        "features": rows,
    }


def _entropy_summary(frame: pd.DataFrame, alerts: list[dict[str, Any]]) -> dict[str, Any]:
    entropy = _numeric(frame, "posterior_entropy")
    no_trade = _bool_rate(frame, "regime_no_trade")
    recent_flip = _bool_rate(frame, "recent_regime_flip")
    result = {
        "row_count": int(len(frame)),
        "posterior_entropy_mean": _mean(entropy),
        "posterior_entropy_p95": _quantile(entropy, 0.95),
        "regime_no_trade_rate": no_trade,
        "recent_regime_flip_rate": recent_flip,
        "by_split": _split_numeric_summary(frame, ["posterior_entropy"], ["regime_no_trade", "recent_regime_flip"]),
    }
    if result["posterior_entropy_p95"] is not None and result["posterior_entropy_p95"] > _ENTROPY_WARN_THRESHOLD:
        _append_alert(alerts, severity="warn", code="high_posterior_entropy", message="Posterior entropy is elevated.", details=result)
    if no_trade is not None and no_trade > _NO_TRADE_WARN_THRESHOLD:
        _append_alert(alerts, severity="warn", code="high_no_trade_rate", message="Regime no-trade rate is elevated.", details=result)
    return result


def _regime_drift(frame: pd.DataFrame, alerts: list[dict[str, Any]]) -> dict[str, Any]:
    if "top_regime_label" not in frame.columns:
        return {"available": False, "reason": "top_regime_label_missing", "splits": []}
    split_column = "walk_forward_split" if "walk_forward_split" in frame.columns else None
    split_values = sorted(frame[split_column].dropna().unique().tolist()) if split_column else [0]
    distributions: list[dict[str, Any]] = []
    baseline: dict[str, float] | None = None
    for split in split_values:
        split_frame = frame.loc[frame[split_column] == split] if split_column else frame
        distribution = _category_distribution(split_frame["top_regime_label"])
        if baseline is None:
            baseline = distribution
        drift = _total_variation_distance(baseline, distribution)
        distributions.append({"split": int(split), "distribution": distribution, "drift_from_baseline": drift})
    max_drift = max((float(item["drift_from_baseline"]) for item in distributions), default=0.0)
    if max_drift > _REGIME_DRIFT_WARN_THRESHOLD:
        _append_alert(
            alerts,
            severity="warn",
            code="regime_distribution_drift",
            message="Regime distribution drift exceeds the observe-only warning threshold.",
            details={"max_drift": max_drift, "threshold": _REGIME_DRIFT_WARN_THRESHOLD},
        )
    return {"available": True, "baseline_split": distributions[0]["split"] if distributions else None, "max_drift": max_drift, "splits": distributions}


def _neighbor_quality(
    knn: pd.DataFrame,
    diagnostics: pd.DataFrame,
    config: dict[str, Any],
    alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    min_neighbor_count = int(((config.get("knn") or {}).get("min_neighbor_count") or 0))
    quality = _numeric(knn, "neighbor_distance_quality")
    neighbor_count = _numeric(knn, "neighbor_count")
    insufficient = None
    if "knn_skip_reason" in knn.columns:
        insufficient = float(knn["knn_skip_reason"].fillna("").astype(str).str.contains("insufficient|no_same_regime", regex=True).mean())
    elif len(neighbor_count):
        insufficient = float((neighbor_count < min_neighbor_count).mean())
    diagnostic_coverage = _diagnostic_coverage(knn, diagnostics)
    result = {
        "row_count": int(len(knn)),
        "neighbor_distance_quality_mean": _mean(quality),
        "neighbor_distance_quality_p05": _quantile(quality, 0.05),
        "neighbor_count_mean": _mean(neighbor_count),
        "neighbor_count_min": _min(neighbor_count),
        "min_neighbor_count": min_neighbor_count,
        "insufficient_neighbor_rate": insufficient,
        "diagnostic_coverage_rate": diagnostic_coverage,
        "skip_reasons": _value_counts(knn, "knn_skip_reason"),
    }
    low_quality = result["neighbor_distance_quality_p05"]
    if low_quality is not None and low_quality < _NEIGHBOR_QUALITY_WARN_THRESHOLD:
        _append_alert(alerts, severity="warn", code="low_neighbor_quality", message="Neighbor distance quality is low.", details=result)
    if insufficient is not None and insufficient > 0.0:
        _append_alert(alerts, severity="warn", code="insufficient_neighbors", message="Some KNN rows lack enough same-regime neighbors.", details=result)
    return result


def _funding_summary(frame: pd.DataFrame, alerts: list[dict[str, Any]]) -> dict[str, Any]:
    columns = ["funding_rate", "funding_paid_or_received", "expected_net_return_after_costs"]
    result = {"available_columns": [column for column in columns if column in frame.columns], "columns": {}}
    for column in columns:
        values = _numeric(frame, column)
        if len(values):
            result["columns"][column] = {
                "mean": _mean(values),
                "min": _min(values),
                "max": _max(values),
                "p95_abs": _quantile(values.abs(), 0.95),
            }
    if "funding_rate" not in frame.columns and "funding_paid_or_received" not in frame.columns:
        _append_alert(alerts, severity="info", code="funding_not_available", message="Funding columns are not available in meta_predictions.", details={})
    return result


def _calibration_decay(frame: pd.DataFrame, alerts: list[dict[str, Any]]) -> dict[str, Any]:
    if "label_accept" not in frame.columns:
        return {"available": False, "reason": "label_accept_missing", "models": {}}
    labels = pd.to_numeric(frame["label_accept"], errors="coerce")
    result = {"available": True, "models": {}}
    for name, probability_column in [("meta", "meta_probability"), ("knn", "p_up_barrier")]:
        if probability_column not in frame.columns:
            result["models"][name] = {"available": False, "reason": f"{probability_column}_missing"}
            continue
        probabilities = pd.to_numeric(frame[probability_column], errors="coerce")
        valid = labels.notna() & probabilities.notna()
        if not valid.any():
            result["models"][name] = {"available": False, "reason": "no_valid_probability_label_pairs"}
            continue
        scored = frame.loc[valid, ["walk_forward_split"]].copy() if "walk_forward_split" in frame.columns else pd.DataFrame(index=frame.index[valid])
        scored["label"] = labels.loc[valid].astype(float)
        scored["probability"] = probabilities.loc[valid].astype(float).clip(0.0, 1.0)
        result["models"][name] = {
            "available": True,
            "row_count": int(len(scored)),
            "overall_brier_score": _brier(scored["probability"], scored["label"]),
            "by_split": _brier_by_split(scored),
            "buckets": _calibration_buckets(scored),
        }
    return result


def _diagnostic_coverage(knn: pd.DataFrame, diagnostics: pd.DataFrame) -> float | None:
    if len(knn) == 0:
        return None
    if diagnostics.empty:
        return 0.0
    if "signal_id" in knn.columns and "signal_id" in diagnostics.columns:
        return float(diagnostics["signal_id"].dropna().nunique() / max(knn["signal_id"].dropna().nunique(), 1))
    identity = [column for column in ("tv_bar_time_ms", "direction", "symbol") if column in knn.columns and column in diagnostics.columns]
    if not identity:
        return None
    return float(diagnostics.drop_duplicates(identity).shape[0] / len(knn.drop_duplicates(identity)))


def _split_numeric_summary(frame: pd.DataFrame, numeric_columns: list[str], bool_columns: list[str]) -> list[dict[str, Any]]:
    if "walk_forward_split" not in frame.columns:
        return []
    rows: list[dict[str, Any]] = []
    for split, split_frame in frame.groupby("walk_forward_split", dropna=False):
        row: dict[str, Any] = {"split": int(split), "row_count": int(len(split_frame))}
        for column in numeric_columns:
            values = _numeric(split_frame, column)
            row[f"{column}_mean"] = _mean(values)
            row[f"{column}_p95"] = _quantile(values, 0.95)
        for column in bool_columns:
            row[f"{column}_rate"] = _bool_rate(split_frame, column)
        rows.append(row)
    return rows


def _category_distribution(series: pd.Series) -> dict[str, float]:
    values = series.fillna("missing").astype(str)
    total = max(len(values), 1)
    return {str(key): float(value / total) for key, value in values.value_counts().sort_index().items()}


def _total_variation_distance(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    return float(0.5 * sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys))


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame.columns:
        return {}
    return {str(key): int(value) for key, value in frame[column].fillna("none").astype(str).value_counts().sort_index().items()}


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(dtype=float)
    values = pd.to_numeric(frame[column], errors="coerce")
    return values.loc[values.notna() & np.isfinite(values)].astype(float)


def _bool_rate(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame.columns or len(frame) == 0:
        return None
    return float(frame[column].fillna(False).astype(bool).mean())


def _mean(values: pd.Series) -> float | None:
    return None if values.empty else float(values.mean())


def _min(values: pd.Series) -> float | None:
    return None if values.empty else float(values.min())


def _max(values: pd.Series) -> float | None:
    return None if values.empty else float(values.max())


def _quantile(values: pd.Series, quantile: float) -> float | None:
    return None if values.empty else float(values.quantile(quantile))


def _brier(probabilities: pd.Series, labels: pd.Series) -> float:
    return float(np.mean(np.square(probabilities.astype(float).to_numpy() - labels.astype(float).to_numpy())))


def _brier_by_split(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if "walk_forward_split" not in frame.columns:
        return []
    rows: list[dict[str, Any]] = []
    for split, split_frame in frame.groupby("walk_forward_split", dropna=False):
        rows.append(
            {
                "split": int(split),
                "row_count": int(len(split_frame)),
                "brier_score": _brier(split_frame["probability"], split_frame["label"]),
            }
        )
    return rows


def _calibration_buckets(frame: pd.DataFrame) -> list[dict[str, Any]]:
    bins = np.linspace(0.0, 1.0, 6)
    bucket = pd.cut(frame["probability"], bins=bins, include_lowest=True, duplicates="drop")
    rows: list[dict[str, Any]] = []
    for interval, bucket_frame in frame.groupby(bucket, observed=False):
        if bucket_frame.empty:
            continue
        rows.append(
            {
                "bucket": str(interval),
                "row_count": int(len(bucket_frame)),
                "mean_probability": float(bucket_frame["probability"].mean()),
                "actual_rate": float(bucket_frame["label"].mean()),
            }
        )
    return rows


def _append_alert(
    alerts: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    details: dict[str, Any],
) -> None:
    alerts.append({"severity": severity, "code": code, "message": message, "observe_only": True, "details": details})


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value
