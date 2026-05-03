from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.promotion.artifact_validator import (
    PromotionCandidateValidationResult,
    load_promotion_candidate_manifest,
    validate_promotion_candidate_for_shadow,
)


SHADOW_LOADER_VERSION = "shadow-loader-stage11-v1"


class ShadowLoaderError(RuntimeError):
    def __init__(self, report: "ShadowLoaderReport") -> None:
        self.report = report
        super().__init__("shadow loader rejected candidate: " + ", ".join(report.blockers))


@dataclass(frozen=True, slots=True)
class ShadowComparisonInputs:
    available_features: tuple[str, ...] = ()
    observed_market: Mapping[str, Any] | None = None
    observed_timing: Mapping[str, Any] | None = None
    feature_drift: Mapping[str, Any] | None = None
    calibration_drift: Mapping[str, Any] | None = None
    skip_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ShadowLoaderReport:
    loader_version: str
    manifest_path: Path
    artifact_type: str
    runtime_mode: str
    permitted: bool
    blockers: tuple[str, ...]
    validator_reasons: tuple[str, ...]
    feature_availability: dict[str, Any]
    replay_fill_assumptions_vs_observed: dict[str, Any]
    timing_drift: dict[str, Any]
    feature_drift: dict[str, Any]
    calibration_drift: dict[str, Any]
    skip_reasons: tuple[str, ...]
    execution_intents_created: bool = False
    runtime_mode_changed: bool = False

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["manifest_path"] = str(self.manifest_path)
        return payload


@dataclass(frozen=True, slots=True)
class ShadowLoadedCandidate:
    manifest: Mapping[str, Any]
    validation: PromotionCandidateValidationResult
    report: ShadowLoaderReport


def build_shadow_loader_report(
    config: AppConfig,
    manifest_path: Path | str,
    *,
    comparison_inputs: ShadowComparisonInputs | Mapping[str, Any] | None = None,
) -> ShadowLoaderReport:
    path = Path(manifest_path)
    candidate = load_promotion_candidate_manifest(path)
    manifest = candidate.payload
    validation = validate_promotion_candidate_for_shadow(candidate)
    inputs = _normalize_inputs(comparison_inputs)

    blockers: list[str] = []
    if config.runtime_mode != RuntimeMode.SHADOW:
        blockers.append(f"shadow_loader_requires_shadow_runtime:{config.runtime_mode}")
    if not _manifest_permits_shadow_runtime(manifest):
        blockers.append("candidate_manifest_does_not_permit_shadow_runtime")
    blockers.extend(f"validator_rejected_candidate:{reason}" for reason in validation.reasons)

    feature_availability, feature_skips = _feature_availability(manifest, inputs.available_features)
    replay_comparison, replay_skips = _replay_fill_assumptions_vs_observed(manifest, inputs.observed_market or {})
    timing_drift, timing_skips = _timing_drift(manifest, inputs.observed_timing or {})
    feature_drift, feature_drift_skips = _drift_report(manifest, inputs.feature_drift or {}, "feature_drift")
    calibration_drift, calibration_drift_skips = _drift_report(
        manifest,
        inputs.calibration_drift or {},
        "calibration_drift",
    )

    skip_reasons = tuple(
        dict.fromkeys(
            (
                *inputs.skip_reasons,
                *feature_skips,
                *replay_skips,
                *timing_skips,
                *feature_drift_skips,
                *calibration_drift_skips,
                *blockers,
            )
        )
    )
    return ShadowLoaderReport(
        loader_version=SHADOW_LOADER_VERSION,
        manifest_path=path,
        artifact_type=_artifact_type(manifest),
        runtime_mode=str(config.runtime_mode),
        permitted=not blockers,
        blockers=tuple(blockers),
        validator_reasons=validation.reasons,
        feature_availability=feature_availability,
        replay_fill_assumptions_vs_observed=replay_comparison,
        timing_drift=timing_drift,
        feature_drift=feature_drift,
        calibration_drift=calibration_drift,
        skip_reasons=skip_reasons,
    )


def load_shadow_promotion_candidate(
    config: AppConfig,
    manifest_path: Path | str,
    *,
    comparison_inputs: ShadowComparisonInputs | Mapping[str, Any] | None = None,
) -> ShadowLoadedCandidate:
    path = Path(manifest_path)
    candidate = load_promotion_candidate_manifest(path)
    manifest = candidate.payload
    validation = validate_promotion_candidate_for_shadow(candidate)
    report = build_shadow_loader_report(config, path, comparison_inputs=comparison_inputs)
    if not report.permitted:
        raise ShadowLoaderError(report)
    return ShadowLoadedCandidate(manifest=manifest, validation=validation, report=report)


def _normalize_inputs(inputs: ShadowComparisonInputs | Mapping[str, Any] | None) -> ShadowComparisonInputs:
    if inputs is None:
        return ShadowComparisonInputs()
    if isinstance(inputs, ShadowComparisonInputs):
        return inputs
    return ShadowComparisonInputs(
        available_features=tuple(str(item) for item in inputs.get("available_features", ())),
        observed_market=_mapping_or_none(inputs.get("observed_market")),
        observed_timing=_mapping_or_none(inputs.get("observed_timing")),
        feature_drift=_mapping_or_none(inputs.get("feature_drift")),
        calibration_drift=_mapping_or_none(inputs.get("calibration_drift")),
        skip_reasons=tuple(str(item) for item in inputs.get("skip_reasons", ())),
    )


def _mapping_or_none(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _artifact_type(manifest: Mapping[str, Any]) -> str:
    for key in (
        "promotion_candidate_manifest_version",
        "artifact_manifest_version",
        "experiment_manifest_version",
        "experiment_run_manifest_version",
        "backtest_manifest_version",
        "dataset_manifest_version",
    ):
        if manifest.get(key):
            return key.removesuffix("_version")
    return "unknown"


def _manifest_permits_shadow_runtime(manifest: Mapping[str, Any]) -> bool:
    declared_modes = _runtime_modes(manifest.get("runtime_modes") or manifest.get("allowed_runtime_modes"))
    if declared_modes:
        return RuntimeMode.SHADOW.value in declared_modes
    declared_mode = manifest.get("runtime_mode") or manifest.get("allowed_runtime_mode")
    if declared_mode is None:
        return True
    return str(declared_mode).strip().lower() == RuntimeMode.SHADOW.value


def _runtime_modes(value: Any) -> set[str]:
    if value is None or isinstance(value, (str, bytes)):
        return set()
    if isinstance(value, Iterable):
        return {str(item).strip().lower() for item in value if str(item).strip()}
    return set()


def _feature_availability(manifest: Mapping[str, Any], available_features: Iterable[str]) -> tuple[dict[str, Any], tuple[str, ...]]:
    required = tuple(dict.fromkeys(_feature_names(_first_present(manifest, ("required_features", "feature_names")))))
    if not required:
        feature_section = manifest.get("features")
        if isinstance(feature_section, Mapping):
            required = tuple(
                dict.fromkeys(
                    _feature_names(
                        _first_present(
                            feature_section,
                            ("required", "required_features", "names", "feature_names"),
                        )
                    )
                )
            )
    if not required:
        feature_manifest = manifest.get("feature_manifest")
        if isinstance(feature_manifest, Mapping):
            required = tuple(
                dict.fromkeys(
                    _feature_names(
                        _first_present(
                            feature_manifest,
                            ("required_features", "features", "feature_names", "names"),
                        )
                    )
                )
            )

    available = tuple(dict.fromkeys(str(item) for item in available_features))
    required_set = set(required)
    available_set = set(available)
    missing = tuple(feature for feature in required if feature not in available_set)
    extra = tuple(feature for feature in available if feature not in required_set)
    coverage_ratio = 1.0 if not required else (len(required) - len(missing)) / len(required)
    skip_reasons = []
    if not required:
        skip_reasons.append("missing_required_feature_list")
    skip_reasons.extend(f"missing_feature:{feature}" for feature in missing)
    return (
        {
            "required": required,
            "available": available,
            "missing": missing,
            "extra": extra,
            "coverage_ratio": coverage_ratio,
            "all_required_available": not missing and bool(required),
        },
        tuple(skip_reasons),
    )


def _feature_names(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return tuple(str(key) for key, enabled in value.items() if enabled is not False)
    if isinstance(value, Iterable):
        names: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                name = item.get("name") or item.get("feature") or item.get("feature_name")
                if name:
                    names.append(str(name))
            else:
                names.append(str(item))
        return tuple(names)
    return ()


def _replay_fill_assumptions_vs_observed(
    manifest: Mapping[str, Any],
    observed_market: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    assumptions = _nested_mapping(
        manifest,
        (
            ("replay_fill_assumptions",),
            ("fill_assumptions",),
            ("replay", "fill_assumptions"),
            ("backtest", "fill_assumptions"),
        ),
    )
    metric_rules = {
        "spread_bps": "observed_lte_assumed",
        "basis_bps": "observed_lte_assumed",
        "depth_levels": "observed_gte_assumed",
        "depth_notional": "observed_gte_assumed",
    }
    metrics: dict[str, Any] = {}
    skip_reasons: list[str] = []
    for metric, rule in metric_rules.items():
        assumed = _number_or_none(assumptions.get(metric))
        observed = _number_or_none(observed_market.get(metric))
        if assumed is None:
            skip_reasons.append(f"missing_replay_fill_assumption:{metric}")
        if observed is None:
            skip_reasons.append(f"missing_observed_market:{metric}")
        metrics[metric] = {
            "assumed": assumed,
            "observed": observed,
            "drift": None if assumed is None or observed is None else observed - assumed,
            "breached": _comparison_breached(assumed, observed, rule),
            "rule": rule,
        }
    return ({"metrics": metrics, "breached": any(item["breached"] for item in metrics.values())}, tuple(skip_reasons))


def _timing_drift(manifest: Mapping[str, Any], observed_timing: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    assumptions = _nested_mapping(
        manifest,
        (
            ("timing_assumptions",),
            ("timing",),
            ("replay", "timing"),
        ),
    )
    expected_latency_ms = _number_or_none(
        _first_present(assumptions, ("expected_latency_ms", "latency_ms", "max_latency_ms"))
    )
    observed_latency_ms = _number_or_none(observed_timing.get("latency_ms"))
    max_drift_ms = _number_or_none(
        observed_timing.get("max_drift_ms")
        if "max_drift_ms" in observed_timing
        else _first_present(assumptions, ("max_drift_ms", "allowed_drift_ms"))
    )

    expected_time_ms = _number_or_none(observed_timing.get("expected_event_time_ms"))
    observed_time_ms = _number_or_none(observed_timing.get("observed_event_time_ms"))
    event_drift_ms = None if expected_time_ms is None or observed_time_ms is None else observed_time_ms - expected_time_ms
    latency_drift_ms = None if expected_latency_ms is None or observed_latency_ms is None else observed_latency_ms - expected_latency_ms
    drift_candidates = [abs(value) for value in (latency_drift_ms, event_drift_ms) if value is not None]
    max_abs_drift_ms = max(drift_candidates) if drift_candidates else None

    skip_reasons = []
    if expected_latency_ms is None and expected_time_ms is None:
        skip_reasons.append("missing_timing_assumption")
    if observed_latency_ms is None and observed_time_ms is None:
        skip_reasons.append("missing_observed_timing")

    return (
        {
            "expected_latency_ms": expected_latency_ms,
            "observed_latency_ms": observed_latency_ms,
            "latency_drift_ms": latency_drift_ms,
            "expected_event_time_ms": expected_time_ms,
            "observed_event_time_ms": observed_time_ms,
            "event_drift_ms": event_drift_ms,
            "max_abs_drift_ms": max_abs_drift_ms,
            "max_allowed_drift_ms": max_drift_ms,
            "breached": False if max_abs_drift_ms is None or max_drift_ms is None else max_abs_drift_ms > max_drift_ms,
        },
        tuple(skip_reasons),
    )


def _drift_report(manifest: Mapping[str, Any], observed: Mapping[str, Any], name: str) -> tuple[dict[str, Any], tuple[str, ...]]:
    thresholds = _nested_mapping(
        manifest,
        (
            ("drift_thresholds", name),
            (name, "thresholds"),
            (name + "_thresholds",),
        ),
    )
    max_abs = _number_or_none(observed.get("max_abs"))
    threshold = _number_or_none(
        observed.get("threshold")
        if "threshold" in observed
        else _first_present(thresholds, ("max_abs", "max_abs_delta", "max_abs_zscore", "max_brier_delta"))
    )
    skip_reasons = []
    if not observed:
        skip_reasons.append(f"missing_{name}_observation")
    if max_abs is None:
        skip_reasons.append(f"missing_{name}_max_abs")
    if threshold is None:
        skip_reasons.append(f"missing_{name}_threshold")
    return (
        {
            "metrics": dict(observed),
            "max_abs": max_abs,
            "threshold": threshold,
            "breached": False if max_abs is None or threshold is None else max_abs > threshold,
        },
        tuple(skip_reasons),
    )


def _nested_mapping(manifest: Mapping[str, Any], paths: tuple[tuple[str, ...], ...]) -> Mapping[str, Any]:
    for path in paths:
        current: Any = manifest
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                current = None
                break
            current = current[key]
        if isinstance(current, Mapping):
            return current
    return {}


def _first_present(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _number_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _comparison_breached(assumed: float | None, observed: float | None, rule: str) -> bool:
    if assumed is None or observed is None:
        return False
    if rule == "observed_lte_assumed":
        return observed > assumed
    if rule == "observed_gte_assumed":
        return observed < assumed
    return False
