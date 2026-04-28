from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from tradingbotsuite.research.hmm_knn import run_hmm_knn_research
from tradingbotsuite.research.hmm_knn_monitoring import monitor_hmm_knn_artifact

HMM_KNN_EXPERIMENT_RUNNER_VERSION = "v2-hmm-knn-experiment-runner-1"
HMM_KNN_EXPERIMENT_MANIFEST_VERSION = "v2-hmm-knn-experiment-manifest-1"


@dataclass(frozen=True, slots=True)
class HmmKnnExperimentMatrixResult:
    output_dir: Path
    manifest_path: Path
    summary_path: Path


def run_hmm_knn_experiment_matrix(
    *,
    spec_path: Path,
    output_dir: Path,
    dataset_path: Path | None = None,
    cache_dir: Path | None = None,
    force: bool = False,
    write_monitoring: bool = True,
    fail_fast: bool = False,
) -> HmmKnnExperimentMatrixResult:
    """Run a research-only HMM/KNN experiment matrix with deterministic caching."""

    spec_path = spec_path.expanduser()
    spec = _read_json(spec_path)
    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_root = (cache_dir.expanduser() if cache_dir is not None else output_dir / "cache")
    cache_root.mkdir(parents=True, exist_ok=True)

    base_config_path = _resolve_required_path(spec_path, spec.get("base_config_path"), "base_config_path")
    resolved_dataset_path = dataset_path.expanduser() if dataset_path is not None else _resolve_required_path(spec_path, spec.get("dataset_path"), "dataset_path")
    base_config = _read_json(base_config_path)
    base_config_sha256 = _file_sha256(base_config_path)
    dataset_sha256 = _file_sha256(resolved_dataset_path)
    spec_sha256 = _file_sha256(spec_path)

    config_dir = output_dir / "generated_configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    experiments = sorted((spec.get("experiments") or []), key=lambda item: int(item.get("run_order", 0)))
    if not experiments:
        raise ValueError("experiment spec must contain at least one experiment")

    manifest_records: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    overall_status = "passed"
    started_at_ms = int(time.time() * 1000)

    for index, experiment in enumerate(experiments, start=1):
        slug = _safe_slug(str(experiment.get("slug") or experiment.get("name") or f"experiment-{index}"))
        mutations = experiment.get("mutations") or {}
        if not isinstance(mutations, dict):
            raise ValueError(f"experiment {slug} mutations must be an object")

        experiment_config = json.loads(json.dumps(base_config))
        _apply_mutations(experiment_config, mutations)
        base_version = str(base_config.get("version", "hmm-knn"))
        if str(experiment_config.get("version", "")) == base_version:
            experiment_config["version"] = f"{base_version}-{slug}"

        config_payload_sha256 = _payload_sha256(experiment_config)
        config_path = config_dir / f"{slug}.json"
        config_path.write_text(_canonical_json(experiment_config, indent=2) + "\n", encoding="utf-8")
        config_sha256 = _file_sha256(config_path)
        cache_key = _payload_sha256(
            {
                "runner_version": HMM_KNN_EXPERIMENT_RUNNER_VERSION,
                "dataset_sha256": dataset_sha256,
                "config_payload_sha256": config_payload_sha256,
            }
        )[:24]
        cache_status = "miss"
        artifact_manifest_path = cache_root / cache_key / str(experiment_config["version"]) / "artifact_manifest.json"
        monitoring_report_path: Path | None = None
        error: str | None = None

        try:
            if not force and _cached_artifact_complete(artifact_manifest_path, config_sha256=config_sha256, dataset_path=resolved_dataset_path):
                cache_status = "hit"
            else:
                result = run_hmm_knn_research(
                    config_path=config_path,
                    dataset_path=resolved_dataset_path,
                    output_dir=cache_root / cache_key,
                )
                artifact_manifest_path = result.artifact_manifest_path
                cache_status = "refresh" if force else "miss"

            if write_monitoring:
                monitoring_report_path = monitor_hmm_knn_artifact(artifact_manifest_path)
            metrics = _load_metrics(artifact_manifest_path)
            record_status = "passed"
        except Exception as exc:
            overall_status = "failed"
            record_status = "failed"
            metrics = {}
            error = f"{type(exc).__name__}: {exc}"
            if fail_fast:
                raise

        record = {
            "name": str(experiment.get("name") or slug),
            "slug": slug,
            "owning_agent": experiment.get("owning_agent"),
            "run_order": int(experiment.get("run_order", index)),
            "config_data_change": experiment.get("config_data_change"),
            "expected_metric_movement": experiment.get("expected_metric_movement"),
            "risk": experiment.get("risk"),
            "requires_new_data": bool(experiment.get("requires_new_data", False)),
            "can_run_on_current_artifacts": bool(experiment.get("can_run_on_current_artifacts", True)),
            "mutations": mutations,
            "status": record_status,
            "error": error,
            "cache_key": cache_key,
            "cache_status": cache_status,
            "config_path": str(config_path),
            "config_sha256": config_sha256,
            "config_payload_sha256": config_payload_sha256,
            "artifact_manifest_path": str(artifact_manifest_path) if error is None else None,
            "monitoring_report_path": str(monitoring_report_path) if monitoring_report_path is not None else None,
            "metrics_digest": _metrics_digest(metrics),
        }
        manifest_records.append(record)
        summary_rows.append(_summary_row(record))

    summary_path = output_dir / "experiment_summary.csv"
    _write_summary(summary_path, summary_rows)
    manifest_path = output_dir / "experiment_manifest.json"
    manifest = {
        "experiment_manifest_version": HMM_KNN_EXPERIMENT_MANIFEST_VERSION,
        "runner_version": HMM_KNN_EXPERIMENT_RUNNER_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "started_at_ms": started_at_ms,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "overall_status": overall_status,
        "name": spec.get("name") or spec_path.stem,
        "spec_path": str(spec_path),
        "spec_sha256": spec_sha256,
        "base_config_path": str(base_config_path),
        "base_config_sha256": base_config_sha256,
        "dataset_path": str(resolved_dataset_path),
        "dataset_sha256": dataset_sha256,
        "output_dir": str(output_dir),
        "cache_dir": str(cache_root),
        "force": bool(force),
        "write_monitoring": bool(write_monitoring),
        "summary_path": str(summary_path),
        "experiments": manifest_records,
    }
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return HmmKnnExperimentMatrixResult(output_dir=output_dir, manifest_path=manifest_path, summary_path=summary_path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _resolve_required_path(spec_path: Path, raw: object, field: str) -> Path:
    if raw is None or str(raw).strip() == "":
        raise ValueError(f"experiment spec must define {field}")
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = spec_path.parent / path
    return path


def _apply_mutations(payload: dict[str, Any], mutations: dict[str, Any]) -> None:
    for key, value in mutations.items():
        if "." in key:
            _set_dotted(payload, key, value)
        elif isinstance(value, dict) and isinstance(payload.get(key), dict):
            _merge_dict(payload[key], value)
        else:
            payload[key] = value


def _merge_dict(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_dict(target[key], value)
        else:
            target[key] = value


def _set_dotted(payload: dict[str, Any], dotted_key: str, value: Any) -> None:
    current: dict[str, Any] = payload
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        next_value = current.setdefault(part, {})
        if not isinstance(next_value, dict):
            raise ValueError(f"cannot set {dotted_key}: {part} is not an object")
        current = next_value
    current[parts[-1]] = value


def _cached_artifact_complete(artifact_manifest_path: Path, *, config_sha256: str, dataset_path: Path) -> bool:
    if not artifact_manifest_path.exists():
        return False
    try:
        manifest = _read_json(artifact_manifest_path)
    except Exception:
        return False
    if not manifest.get("research_only"):
        return False
    if str(manifest.get("dataset_path")) != str(dataset_path):
        return False
    config_path = Path(str(manifest.get("config_path", "")))
    if not config_path.exists() or _file_sha256(config_path) != config_sha256:
        return False
    for key in (
        "regime_posteriors_path",
        "knn_predictions_path",
        "meta_predictions_path",
        "neighbor_diagnostics_path",
        "metrics_path",
    ):
        raw = manifest.get(key)
        if raw is None or not _resolve_manifest_path(artifact_manifest_path, raw).exists():
            return False
    return True


def _resolve_manifest_path(manifest_path: Path, raw: object) -> Path:
    path = Path(str(raw))
    if path.is_absolute():
        return path
    parent_candidate = manifest_path.parent / path
    if parent_candidate.exists():
        return parent_candidate
    return path


def _load_metrics(artifact_manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(artifact_manifest_path)
    metrics_path = _resolve_manifest_path(artifact_manifest_path, manifest["metrics_path"])
    return _read_json(metrics_path)


def _metrics_digest(metrics: dict[str, Any]) -> dict[str, Any]:
    comparison = metrics.get("comparison") or {}
    knn = comparison.get("hmm_regime_lorentzian_knn") or {}
    meta = comparison.get("hmm_knn_meta_model") or {}
    return {
        "promotion_ready": metrics.get("promotion_ready"),
        "promotion_failures": metrics.get("promotion_failures") or [],
        "positive_split_ratio": metrics.get("positive_split_ratio"),
        "knn_trade_count": knn.get("trade_count"),
        "knn_expectancy_after_cost": knn.get("expectancy_after_cost"),
        "knn_profit_factor": knn.get("profit_factor"),
        "meta_trade_count": meta.get("trade_count"),
        "meta_expectancy_after_cost": meta.get("expectancy_after_cost"),
        "meta_profit_factor": meta.get("profit_factor"),
        "max_single_split_pnl_share_by_strategy": metrics.get("max_single_split_pnl_share_by_strategy") or {},
    }


def _summary_row(record: dict[str, Any]) -> dict[str, Any]:
    digest = record.get("metrics_digest") or {}
    split_share = digest.get("max_single_split_pnl_share_by_strategy") or {}
    return {
        "run_order": record.get("run_order"),
        "slug": record.get("slug"),
        "owning_agent": record.get("owning_agent"),
        "status": record.get("status"),
        "cache_status": record.get("cache_status"),
        "requires_new_data": record.get("requires_new_data"),
        "can_run_on_current_artifacts": record.get("can_run_on_current_artifacts"),
        "artifact_manifest_path": record.get("artifact_manifest_path"),
        "monitoring_report_path": record.get("monitoring_report_path"),
        "promotion_ready": digest.get("promotion_ready"),
        "knn_trade_count": digest.get("knn_trade_count"),
        "knn_expectancy_after_cost": digest.get("knn_expectancy_after_cost"),
        "knn_profit_factor": digest.get("knn_profit_factor"),
        "meta_trade_count": digest.get("meta_trade_count"),
        "meta_expectancy_after_cost": digest.get("meta_expectancy_after_cost"),
        "meta_profit_factor": digest.get("meta_profit_factor"),
        "positive_split_ratio": digest.get("positive_split_ratio"),
        "knn_max_single_split_pnl_share": split_share.get("hmm_regime_lorentzian_knn"),
        "meta_max_single_split_pnl_share": split_share.get("hmm_knn_meta_model"),
        "error": record.get("error"),
    }


def _write_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _safe_slug(value: str) -> str:
    chars = []
    for character in value.strip().lower():
        if character.isalnum():
            chars.append(character)
        elif character in {"-", "_", ".", " "}:
            chars.append("-")
    slug = "".join(chars).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "experiment"


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: dict[str, Any]) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(payload, indent=indent, separators=(",", ":") if indent is None else None, sort_keys=True)
