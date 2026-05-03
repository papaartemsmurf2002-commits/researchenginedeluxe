from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

SHADOW_ONLY_INTENDED_USES = frozenset(
    {
        "shadow",
        "shadow_only",
        "shadow_only_promotion_candidate",
        "promotion_shadow_only",
    }
)

EVIDENCE_FLOOR_FIELDS = (
    "min_trade_count",
    "min_expectancy_improvement",
    "max_mean_absolute_calibration_error",
    "min_improved_split_ratio",
)

STAGE11_EVIDENCE_FLOOR_VERSION = "stage11-plan-evidence-floors-v1"


@dataclass(frozen=True, slots=True)
class ArtifactValidationResult:
    allowed: bool
    reasons: tuple[str, ...]
    manifest_path: Path | None = None
    artifact_type: str = "unknown"


@dataclass(frozen=True, slots=True)
class PromotionCandidateManifest:
    payload: Mapping[str, Any]
    manifest_path: Path | None = None

    @property
    def candidate_id(self) -> str:
        candidate_id = str(self.payload.get("candidate_id") or "").strip()
        return candidate_id or "unknown"


@dataclass(frozen=True, slots=True)
class PromotionCandidateValidationResult:
    allowed: bool
    reasons: tuple[str, ...]
    manifest_path: Path | None = None
    candidate_id: str = "unknown"
    target: str = "shadow"
    artifact_type: str = "unknown"


def load_artifact_manifest(path: Path | str) -> dict[str, Any]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact manifest must be a JSON object: {manifest_path}")
    return payload


def load_promotion_candidate_manifest(path: Path | str) -> PromotionCandidateManifest:
    manifest_path = Path(path)
    return PromotionCandidateManifest(payload=load_artifact_manifest(manifest_path), manifest_path=manifest_path)


def validate_artifact_for_live_input(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> ArtifactValidationResult:
    reasons: list[str] = []
    artifact_type = _artifact_type(manifest)
    if _is_promotion_candidate_manifest(manifest):
        reasons.append("promotion_candidate_rejected_for_live_input")
    if manifest.get("research_only") is True:
        reasons.append("research_only_artifact_rejected_for_live_input")
    if manifest.get("observe_only") is True:
        reasons.append("observe_only_artifact_rejected_for_live_input")
    if manifest.get("promotion_ready") is not True:
        reasons.append("promotion_ready_false_or_missing")
    intended_use = str(manifest.get("intended_use") or "").strip().lower()
    if intended_use in {"research", "research_only", "observe_only", "research_observe_only"}:
        reasons.append(f"research_intended_use_rejected:{intended_use}")
    if manifest.get("live_signal_input") is False:
        reasons.append("manifest_declares_not_live_signal_input")
    if manifest.get("position_sizing_input") is False:
        reasons.append("manifest_declares_not_position_sizing_input")
    if manifest.get("live_execution_input") is False:
        reasons.append("manifest_declares_not_live_execution_input")
    return ArtifactValidationResult(
        allowed=not reasons,
        reasons=tuple(reasons),
        manifest_path=manifest_path,
        artifact_type=artifact_type,
    )


def validate_promotion_candidate_for_shadow(
    manifest: PromotionCandidateManifest | Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> PromotionCandidateValidationResult:
    payload, resolved_path = _candidate_payload_and_path(manifest, manifest_path)
    reasons: list[str] = []
    candidate_id = str(payload.get("candidate_id") or "").strip()

    _require_non_empty(payload, "promotion_candidate_manifest_version", reasons)
    _require_non_empty(payload, "candidate_id", reasons)
    _require_non_empty(payload, "source_artifact_manifest_path", reasons)
    _require_non_empty(payload, "dataset_manifest_hash", reasons)
    _require_non_empty(payload, "feature_manifest_hash", reasons)
    _require_non_empty(payload, "strategy_version", reasons)

    if payload.get("research_only") is not True:
        reasons.append("research_only_must_be_true_for_shadow_candidate")
    if payload.get("observe_only") is not True:
        reasons.append("observe_only_must_be_true_for_shadow_candidate")
    if payload.get("promotion_ready") is not False:
        reasons.append("promotion_ready_must_remain_false_for_shadow_candidate")
    if payload.get("shadow_only") is not True:
        reasons.append("shadow_only_must_be_true")

    intended_use = str(payload.get("intended_use") or "").strip().lower()
    if intended_use not in SHADOW_ONLY_INTENDED_USES:
        reasons.append("intended_use_must_be_shadow_only")

    if payload.get("live_signal_input") is not False:
        reasons.append("candidate_must_not_be_live_signal_input")
    if payload.get("position_sizing_input") is not False:
        reasons.append("candidate_must_not_be_position_sizing_input")
    if payload.get("live_execution_input") is not False:
        reasons.append("candidate_must_not_be_live_execution_input")
    if "operator_control_input" in payload and payload.get("operator_control_input") is not False:
        reasons.append("candidate_must_not_be_operator_control_input")
    if "runtime_control_input" in payload and payload.get("runtime_control_input") is not False:
        reasons.append("candidate_must_not_be_runtime_control_input")

    _require_mapping(payload, "cost_assumptions", reasons)
    _require_mapping(payload, "side_metrics", reasons)
    _require_mapping(payload, "regime_metrics", reasons)
    _require_mapping(payload, "feature_missingness_summary", reasons)
    _require_list(payload, "validation_split_summary", reasons)
    _require_list(payload, "non_promotable_reasons", reasons)
    _require_list(payload, "operator_visible_skip_reasons", reasons)

    promotion_failures = payload.get("promotion_failures")
    if promotion_failures not in (None, []):
        reasons.append("promotion_failures_must_be_empty_for_shadow_acceptance")

    floors = _evidence_floors(payload, reasons)
    evidence = _evidence_payload(payload, reasons)
    if floors is not None and evidence is not None:
        _validate_evidence_floors(floors, evidence, reasons)
        _validate_stage11_evidence_floors(evidence, reasons)

    return PromotionCandidateValidationResult(
        allowed=not reasons,
        reasons=tuple(reasons),
        manifest_path=resolved_path,
        candidate_id=candidate_id or "unknown",
        target="shadow",
        artifact_type=_artifact_type(payload),
    )


def validate_promotion_candidate_for_live_input(
    manifest: PromotionCandidateManifest | Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> ArtifactValidationResult:
    payload, resolved_path = _candidate_payload_and_path(manifest, manifest_path)
    return validate_artifact_for_live_input(payload, manifest_path=resolved_path)


def _artifact_type(manifest: Mapping[str, Any]) -> str:
    for key in (
        "promotion_candidate_manifest_version",
        "artifact_manifest_version",
        "experiment_manifest_version",
        "experiment_run_manifest_version",
        "backtest_manifest_version",
        "dataset_manifest_version",
        "manifest_version",
    ):
        if manifest.get(key):
            return key.removesuffix("_version")
    return "unknown"


def _is_promotion_candidate_manifest(manifest: Mapping[str, Any]) -> bool:
    for key in ("promotion_candidate_manifest_version", "artifact_manifest_version", "intended_use"):
        value = str(manifest.get(key) or "").strip().lower()
        if "promotion_candidate" in value or "promotion-candidate" in value:
            return True
    return False


def _candidate_payload_and_path(
    manifest: PromotionCandidateManifest | Mapping[str, Any],
    manifest_path: Path | None,
) -> tuple[Mapping[str, Any], Path | None]:
    if isinstance(manifest, PromotionCandidateManifest):
        return manifest.payload, manifest_path or manifest.manifest_path
    return manifest, manifest_path


def _require_non_empty(payload: Mapping[str, Any], field: str, reasons: list[str]) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        reasons.append(f"{field}_required")


def _require_mapping(payload: Mapping[str, Any], field: str, reasons: list[str]) -> None:
    value = payload.get(field)
    if not isinstance(value, Mapping):
        reasons.append(f"{field}_required")


def _require_list(payload: Mapping[str, Any], field: str, reasons: list[str]) -> None:
    value = payload.get(field)
    if not isinstance(value, list):
        reasons.append(f"{field}_required")


def _evidence_floors(payload: Mapping[str, Any], reasons: list[str]) -> Mapping[str, Any] | None:
    floors = payload.get("evidence_floors")
    if floors is None:
        plan = payload.get("plan") or payload.get("research_plan") or payload.get("promotion_plan")
        if isinstance(plan, Mapping):
            floors = plan.get("evidence_floors") or plan.get("promotion")
    if floors is None:
        floors = payload.get("promotion")
    if not isinstance(floors, Mapping):
        reasons.append("evidence_floors_required")
        return None
    return floors


def _evidence_payload(payload: Mapping[str, Any], reasons: list[str]) -> Mapping[str, Any] | None:
    evidence = payload.get("evidence") or payload.get("metrics") or payload.get("metrics_digest")
    if not isinstance(evidence, Mapping):
        reasons.append("evidence_required")
        return None
    return evidence


def _validate_evidence_floors(floors: Mapping[str, Any], evidence: Mapping[str, Any], reasons: list[str]) -> None:
    floor_values: dict[str, float] = {}
    for field in EVIDENCE_FLOOR_FIELDS:
        value = _number(floors, field, f"evidence_floor:{field}", reasons)
        if value is not None:
            floor_values[field] = value
    if len(floor_values) != len(EVIDENCE_FLOOR_FIELDS):
        return

    trade_count = _evidence_number(evidence, "trade_count", reasons)
    expectancy = _evidence_number(evidence, "expectancy_after_cost", reasons)
    baseline_expectancy = _evidence_number(evidence, "baseline_expectancy_after_cost", reasons)
    calibration_error = _evidence_number(evidence, "mean_absolute_calibration_error", reasons)
    improved_split_ratio = _evidence_number(evidence, "improved_split_ratio", reasons)

    if trade_count is not None and trade_count < floor_values["min_trade_count"]:
        reasons.append("insufficient_trade_count")
    if (
        expectancy is not None
        and baseline_expectancy is not None
        and expectancy < baseline_expectancy + floor_values["min_expectancy_improvement"]
    ):
        reasons.append("expectancy_improvement_below_floor")
    if calibration_error is not None and calibration_error > floor_values["max_mean_absolute_calibration_error"]:
        reasons.append("calibration_error_above_floor")
    if improved_split_ratio is not None and improved_split_ratio < floor_values["min_improved_split_ratio"]:
        reasons.append("improved_split_ratio_below_floor")


def _validate_stage11_evidence_floors(evidence: Mapping[str, Any], reasons: list[str]) -> None:
    power_exception = _has_text(evidence.get("power_analysis_exception"))
    event_rows = evidence.get("event_rows_by_asset")
    if not isinstance(event_rows, Mapping):
        if not power_exception:
            reasons.append("event_rows_by_asset_required")
    else:
        for asset, count in event_rows.items():
            if _integer(count) < 10_000 and not power_exception:
                reasons.append(f"event_rows_floor_not_met:{asset}")

    if evidence.get("uses_regime_model") is True:
        regime_rows = evidence.get("regime_rows")
        if not isinstance(regime_rows, Mapping):
            reasons.append("regime_rows_required")
        else:
            for regime, count in regime_rows.items():
                if _integer(count) < 1_000:
                    reasons.append(f"regime_rows_floor_not_met:{regime}")

    labeled = evidence.get("labeled_trades_by_side")
    if not isinstance(labeled, Mapping):
        reasons.append("labeled_trades_by_side_required")
    else:
        for side in ("long", "short"):
            if _integer(labeled.get(side)) < 300:
                reasons.append(f"labeled_trades_floor_not_met:{side}")

    accepted_splits = evidence.get("accepted_trades_by_validation_split")
    if not isinstance(accepted_splits, Mapping):
        reasons.append("accepted_trades_by_validation_split_required")
    else:
        if len(accepted_splits) < 6:
            reasons.append("walk_forward_split_floor_not_met")
        for split, count in accepted_splits.items():
            if _integer(count) < 50:
                reasons.append(f"accepted_trades_floor_not_met:{split}")

    regimes = evidence.get("volatility_regimes")
    if not isinstance(regimes, list) or len(regimes) < 2:
        reasons.append("multiple_volatility_regimes_required")
    stress_periods = evidence.get("stress_periods")
    if not isinstance(stress_periods, list) or not stress_periods:
        reasons.append("stress_period_required")
    if _decimal(evidence.get("costed_expectancy_after_fees_slippage_funding")) <= Decimal("0"):
        reasons.append("positive_costed_expectancy_required")
    if _decimal(evidence.get("max_split_pnl_share"), default=Decimal("1")) >= Decimal("0.50"):
        reasons.append("single_split_pnl_dominance")
    side_outcomes = evidence.get("side_outcomes")
    if not isinstance(side_outcomes, Mapping) or "long" not in side_outcomes or "short" not in side_outcomes:
        reasons.append("side_outcomes_must_include_long_and_short")
    if evidence.get("slippage_stress_passed") is not True:
        reasons.append("slippage_stress_must_pass")
    if evidence.get("funding_stress_passed") is not True:
        reasons.append("funding_stress_must_pass")
    missingness = _decimal(evidence.get("feature_missingness_max_rate"), default=Decimal("1"))
    threshold = _decimal(evidence.get("feature_missingness_threshold"), default=Decimal("0"))
    if threshold <= Decimal("0") or missingness > threshold:
        reasons.append("feature_missingness_floor_not_met")
    if evidence.get("wt3d_claimed") is True and evidence.get("wt3d_ablation_passed") is not True:
        reasons.append("wt3d_ablation_must_pass_when_claimed")


def _evidence_number(evidence: Mapping[str, Any], field: str, reasons: list[str]) -> float | None:
    if field in evidence:
        return _number(evidence, field, f"evidence:{field}", reasons)
    comparison = evidence.get("comparison")
    if not isinstance(comparison, Mapping):
        reasons.append(f"evidence:{field}_required")
        return None
    if field == "trade_count":
        parent = "v2_meta_label_acceptance"
        nested_field = "trade_count"
    elif field == "expectancy_after_cost":
        parent = "v2_meta_label_acceptance"
        nested_field = "expectancy_after_cost"
    elif field == "baseline_expectancy_after_cost":
        parent = "v1_microstructure_baseline"
        nested_field = "expectancy_after_cost"
    else:
        reasons.append(f"evidence:{field}_required")
        return None

    nested = comparison.get(parent)
    if not isinstance(nested, Mapping) or nested_field not in nested:
        reasons.append(f"evidence:{field}_required")
        return None
    return _number(nested, nested_field, f"evidence:{field}", reasons)


def _number(payload: Mapping[str, Any], field: str, reason_field: str, reasons: list[str]) -> float | None:
    if field not in payload:
        reasons.append(f"{reason_field}_required")
        return None
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        reasons.append(f"{reason_field}_must_be_number")
        return None
    return float(value)


def _has_text(value: object) -> bool:
    return str(value or "").strip() != ""


def _integer(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _decimal(value: object, *, default: Decimal = Decimal("0")) -> Decimal:
    if isinstance(value, bool):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default
