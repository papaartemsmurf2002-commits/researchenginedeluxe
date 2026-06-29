# V2-AUDIT-ID: V2-AUD-BTENG-080
# V2-CONTRACTS: docs/contracts/backtest_engine_contract.md, docs/contracts/run_artifact_contract.md
# V2-BOUNDARY: research_only, fast_lane_audit, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_backtest_engine
"""Fast-lane parity reports and reference rerun planning."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.archive_inventory import ArtifactMode
from tradingbotsuite.v2.backtest_engine.artifacts import EngineLane, RunManifest
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.security.boundary import require_research_boundary


class FastLaneParityStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"


class FullArtifactReplayVerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class FastLaneMetricDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric: str = Field(min_length=1)
    reference_value: float
    fast_value: float
    abs_diff: float = Field(ge=0.0)
    tolerance_abs: float = Field(ge=0.0)
    within_tolerance: bool


class FullArtifactReplayMetricDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric: str = Field(min_length=1)
    source_value: float
    replay_value: float
    abs_diff: float = Field(ge=0.0)
    tolerance_abs: float = Field(ge=0.0)
    within_tolerance: bool


class ReferenceRerunPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    rerun_plan_id: str = Field(min_length=64, max_length=64)
    source_run_id: str = Field(min_length=1)
    planned_run_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    requested_engine_lane: EngineLane = EngineLane.VECTORIZED
    requested_artifact_mode: ArtifactMode = ArtifactMode.FULL
    required_replay_manifest_ref: str = Field(min_length=1)
    required_data_manifest_id: str = Field(min_length=1)
    expected_data_manifest_hash: str = Field(min_length=64, max_length=64)
    expected_strategy_spec_hash: str = Field(min_length=64, max_length=64)
    expected_params_hash: str = Field(min_length=64, max_length=64)
    same_spec_data_config_required: bool = True
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_plan(self) -> "ReferenceRerunPlan":
        if self.requested_engine_lane != EngineLane.VECTORIZED:
            raise ValueError("reference rerun plans must use the vectorized reference lane")
        if self.requested_artifact_mode != ArtifactMode.FULL:
            raise ValueError("reference rerun plans must replay to full artifacts")
        require_research_boundary(self, context="fast-lane reference rerun plan")
        return self


class FullArtifactReplayPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    replay_plan_id: str = Field(min_length=64, max_length=64)
    source_run_id: str = Field(min_length=1)
    planned_run_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_engine_lane: EngineLane
    requested_engine_lane: EngineLane
    source_artifact_mode: ArtifactMode
    requested_artifact_mode: ArtifactMode = ArtifactMode.FULL
    required_replay_manifest_ref: str = Field(min_length=1)
    required_data_manifest_id: str = Field(min_length=1)
    expected_data_manifest_hash: str = Field(min_length=64, max_length=64)
    expected_strategy_spec_hash: str = Field(min_length=64, max_length=64)
    expected_params_hash: str = Field(min_length=64, max_length=64)
    expected_replay_identity_hash: str = Field(min_length=64, max_length=64)
    same_spec_data_config_required: bool = True
    reference_engine_authority: bool = True
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_plan(self) -> "FullArtifactReplayPlan":
        if self.source_artifact_mode == ArtifactMode.FULL:
            raise ValueError("full artifact replay plans require a light source artifact mode")
        if self.requested_artifact_mode != ArtifactMode.FULL:
            raise ValueError("full artifact replay plans must request full artifacts")
        if self.requested_engine_lane != self.source_engine_lane:
            raise ValueError("full artifact replay plans preserve the source engine lane")
        require_research_boundary(self, context="full-artifact replay plan")
        return self


class FastLaneParityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "fast_lane_parity_report_v1"
    parity_report_id: str = Field(min_length=64, max_length=64)
    status: FastLaneParityStatus
    reference_run_id: str = Field(min_length=1)
    fast_run_id: str = Field(min_length=1)
    tolerance_abs: float = Field(ge=0.0)
    metric_diffs: tuple[FastLaneMetricDiff, ...] = ()
    identity_mismatches: tuple[str, ...] = ()
    blocker_reasons: tuple[str, ...] = ()
    suspicious_result: bool = False
    rerun_plan: ReferenceRerunPlan | None = None
    benchmark_observations: dict[str, float] = Field(default_factory=dict)
    speedup_claimed: bool = False
    reference_engine_authority: bool = True
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> "FastLaneParityReport":
        if self.report_type != "fast_lane_parity_report_v1":
            raise ValueError("report_type must be fast_lane_parity_report_v1")
        if self.status == FastLaneParityStatus.PASS and self.suspicious_result:
            raise ValueError("passing parity reports cannot be suspicious")
        if self.status == FastLaneParityStatus.FAIL and self.rerun_plan is None:
            raise ValueError("failed fast-lane reports require a reference rerun plan")
        if any(value < 0.0 for value in self.benchmark_observations.values()):
            raise ValueError("benchmark observations must be non-negative")
        missing_speedup_evidence = _missing_speedup_claim_observations(self.benchmark_observations)
        if self.speedup_claimed and missing_speedup_evidence:
            raise ValueError(
                "speedup claims require measured benchmark evidence: "
                + ",".join(missing_speedup_evidence)
            )
        require_research_boundary(self, context="fast-lane parity report")
        return self


class FullArtifactReplayVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "full_artifact_replay_verification_v1"
    verification_id: str = Field(min_length=64, max_length=64)
    status: FullArtifactReplayVerificationStatus
    source_run_id: str = Field(min_length=1)
    replay_run_id: str = Field(min_length=1)
    source_engine_lane: EngineLane
    replay_engine_lane: EngineLane
    source_artifact_mode: ArtifactMode
    replay_artifact_mode: ArtifactMode
    tolerance_abs: float = Field(ge=0.0)
    identity_mismatches: tuple[str, ...] = ()
    replay_manifest_mismatches: tuple[str, ...] = ()
    metric_diffs: tuple[FullArtifactReplayMetricDiff, ...] = ()
    blocker_reasons: tuple[str, ...] = ()
    same_spec_data_config_verified: bool = False
    replay_manifest_identity_verified: bool = False
    metrics_verified: bool = False
    full_artifacts_verified: bool = False
    source_replay_identity_hash: str | None = Field(default=None, min_length=64, max_length=64)
    replay_replay_identity_hash: str | None = Field(default=None, min_length=64, max_length=64)
    reference_engine_authority: bool = True
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> "FullArtifactReplayVerification":
        if self.report_type != "full_artifact_replay_verification_v1":
            raise ValueError("unexpected full artifact replay verification report type")
        if self.status == FullArtifactReplayVerificationStatus.PASS:
            if self.blocker_reasons or self.identity_mismatches or self.replay_manifest_mismatches:
                raise ValueError("passing replay verification cannot include blockers or mismatches")
            if not (
                self.same_spec_data_config_verified
                and self.replay_manifest_identity_verified
                and self.metrics_verified
                and self.full_artifacts_verified
            ):
                raise ValueError("passing replay verification requires all verification flags")
        require_research_boundary(self, context="full-artifact replay verification")
        return self


_METRIC_FIELDS: tuple[str, ...] = (
    "gross_return",
    "net_return",
    "gross_equity_final",
    "net_equity_final",
    "total_fee_cost",
    "total_spread_cost",
    "total_slippage_cost",
    "total_impact_cost",
    "total_transaction_cost",
    "total_funding_pnl",
    "total_turnover",
    "trade_count",
    "position_row_count",
    "capacity_blocked_count",
)

_IDENTITY_FIELDS: tuple[str, ...] = (
    "strategy_spec_hash",
    "params_hash",
    "archive_snapshot_id",
    "universe_snapshot_id",
    "data_manifest_id",
    "data_manifest_hash",
    "validation_manifest_hash",
    "cost_manifest_hash",
    "cost_model_hash",
    "timeframe",
    "backtest_start",
    "backtest_end",
)


_FULL_REPLAY_IDENTITY_FIELDS: tuple[str, ...] = (
    "strategy_spec_hash",
    "params_hash",
    "archive_snapshot_id",
    "universe_snapshot_id",
    "data_manifest_id",
    "data_manifest_hash",
    "validation_manifest_hash",
    "cost_manifest_hash",
    "cost_model_id",
    "cost_model_hash",
    "universe_mode",
    "venue_scope",
    "instrument_count",
    "timeframe",
    "backtest_start",
    "backtest_end",
    "lockbox_policy_id",
    "lockbox_start",
    "lockbox_end",
    "data_coverage_min",
    "validation_policy_id",
    "missing_data_policy",
    "price_basis",
)


_REPLAY_MANIFEST_IDENTITY_FIELDS: tuple[str, ...] = (
    "strategy_spec_hash",
    "params_hash",
    "archive_snapshot_id",
    "universe_snapshot_id",
    "data_manifest_id",
    "data_manifest_hash",
    "validation_manifest_hash",
    "cost_manifest_hash",
    "engine_lane",
    "cost_model_id",
    "cost_model_hash",
    "panel_row_count",
    "panel_hash",
    "full_replay_requires_same_spec_data_config",
)


_FULL_ARTIFACTS: frozenset[str] = frozenset(
    {
        "strategy_spec",
        "params",
        "data_manifest",
        "validation_manifest",
        "cost_manifest",
        "metrics",
        "replay_manifest",
        "equity_curve",
        "daily_returns",
        "per_instrument_metrics",
        "fold_metrics",
        "cost_stress",
        "trades",
        "positions",
        "log",
    }
)

_SPEEDUP_CLAIM_REQUIRED_OBSERVATIONS: frozenset[str] = frozenset(
    {
        "speedup_ratio",
        "reference_runtime_seconds",
        "fast_runtime_seconds",
        "reference_data_load_seconds",
        "fast_data_load_seconds",
        "reference_artifact_write_seconds",
        "fast_artifact_write_seconds",
        "reference_memory_peak_bytes",
        "fast_memory_peak_bytes",
    }
)


def audit_fast_lane_parity(
    *,
    reference_manifest: RunManifest | Mapping[str, Any],
    fast_manifest: RunManifest | Mapping[str, Any],
    tolerance_abs: float = 1e-12,
    claim_speedup: bool = False,
) -> FastLaneParityReport:
    if tolerance_abs < 0.0:
        raise ValueError("tolerance_abs must be non-negative")
    reference = _parse_manifest(reference_manifest)
    fast = _parse_manifest(fast_manifest)
    blockers: list[str] = []
    if reference.engine_lane != EngineLane.VECTORIZED:
        blockers.append("reference_manifest_not_vectorized")
    if fast.engine_lane != EngineLane.FAST_VECTORIZED:
        blockers.append("fast_manifest_not_fast_vectorized")
    if reference.metrics is None:
        blockers.append("reference_metrics_missing")
    if fast.metrics is None:
        blockers.append("fast_metrics_missing")
    identity_mismatches = _identity_mismatches(reference, fast)
    blockers.extend(f"identity_mismatch:{field}" for field in identity_mismatches)

    metric_diffs: list[FastLaneMetricDiff] = []
    if not blockers and reference.metrics is not None and fast.metrics is not None:
        for metric in _METRIC_FIELDS:
            reference_value = float(getattr(reference.metrics, metric))
            fast_value = float(getattr(fast.metrics, metric))
            abs_diff = abs(reference_value - fast_value)
            metric_diffs.append(
                FastLaneMetricDiff(
                    metric=metric,
                    reference_value=reference_value,
                    fast_value=fast_value,
                    abs_diff=abs_diff,
                    tolerance_abs=tolerance_abs,
                    within_tolerance=abs_diff <= tolerance_abs,
                )
            )

    if blockers:
        status = FastLaneParityStatus.BLOCKED
    elif all(row.within_tolerance for row in metric_diffs):
        status = FastLaneParityStatus.PASS
    else:
        status = FastLaneParityStatus.FAIL

    benchmark_observations = _parity_benchmark_observations(reference, fast)
    suspicious = status != FastLaneParityStatus.PASS
    rerun_plan = None
    if suspicious and fast.engine_lane == EngineLane.FAST_VECTORIZED and "replay_manifest" in fast.artifacts:
        rerun_plan = build_reference_rerun_plan(
            fast,
            reason="fast_lane_parity_failed" if status == FastLaneParityStatus.FAIL else "fast_lane_parity_blocked",
        )
    payload = {
        "status": status.value,
        "reference_run_id": reference.run_id,
        "fast_run_id": fast.run_id,
        "tolerance_abs": tolerance_abs,
        "metric_diffs": tuple(row.model_dump(mode="json") for row in metric_diffs),
        "identity_mismatches": tuple(identity_mismatches),
        "blocker_reasons": tuple(blockers),
        "suspicious_result": suspicious,
        "rerun_plan": None if rerun_plan is None else rerun_plan.model_dump(mode="json"),
        "benchmark_observations": benchmark_observations,
        "speedup_claimed": claim_speedup,
        "reference_engine_authority": True,
    }
    return FastLaneParityReport(
        **payload,
        parity_report_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "report_type": "fast_lane_parity_report_v1",
                **payload,
            }
        ),
    )


def verify_full_artifact_replay(
    *,
    source_manifest: RunManifest | Mapping[str, Any],
    replay_manifest: RunManifest | Mapping[str, Any],
    source_replay_manifest: Mapping[str, Any] | None = None,
    full_replay_manifest: Mapping[str, Any] | None = None,
    tolerance_abs: float = 1e-12,
) -> FullArtifactReplayVerification:
    if tolerance_abs < 0.0:
        raise ValueError("tolerance_abs must be non-negative")
    source = _parse_manifest(source_manifest)
    replay = _parse_manifest(replay_manifest)
    blockers: list[str] = []
    identity_mismatches = list(_full_replay_identity_mismatches(source, replay))
    replay_manifest_mismatches: list[str] = []

    if source.artifact_mode == ArtifactMode.FULL:
        blockers.append("source_manifest_not_artifact_light")
    if replay.artifact_mode != ArtifactMode.FULL:
        blockers.append("replay_manifest_not_full_artifact_mode")
    if not source.replayable_to_full_artifacts:
        blockers.append("source_manifest_not_replayable_to_full_artifacts")
    if source.engine_lane != replay.engine_lane:
        identity_mismatches.append("engine_lane")
    missing_full_artifacts = sorted(_FULL_ARTIFACTS - set(replay.artifacts))
    blockers.extend(f"missing_full_artifact:{name}" for name in missing_full_artifacts)

    if source.metrics is None:
        blockers.append("source_metrics_missing")
    if replay.metrics is None:
        blockers.append("replay_metrics_missing")

    if source_replay_manifest is None or full_replay_manifest is None:
        blockers.append("replay_manifest_payloads_missing")
    else:
        replay_manifest_mismatches.extend(
            _replay_manifest_identity_mismatches(
                source_replay_manifest,
                full_replay_manifest,
            )
        )

    metric_diffs: list[FullArtifactReplayMetricDiff] = []
    if source.metrics is not None and replay.metrics is not None:
        for metric in _METRIC_FIELDS:
            source_value = float(getattr(source.metrics, metric))
            replay_value = float(getattr(replay.metrics, metric))
            abs_diff = abs(source_value - replay_value)
            metric_diffs.append(
                FullArtifactReplayMetricDiff(
                    metric=metric,
                    source_value=source_value,
                    replay_value=replay_value,
                    abs_diff=abs_diff,
                    tolerance_abs=tolerance_abs,
                    within_tolerance=abs_diff <= tolerance_abs,
                )
            )
        if not all(row.within_tolerance for row in metric_diffs):
            blockers.append("metrics_mismatch")

    status = (
        FullArtifactReplayVerificationStatus.PASS
        if not blockers and not identity_mismatches and not replay_manifest_mismatches
        else FullArtifactReplayVerificationStatus.FAIL
    )
    payload = {
        "status": status,
        "source_run_id": source.run_id,
        "replay_run_id": replay.run_id,
        "source_engine_lane": source.engine_lane,
        "replay_engine_lane": replay.engine_lane,
        "source_artifact_mode": source.artifact_mode,
        "replay_artifact_mode": replay.artifact_mode,
        "tolerance_abs": tolerance_abs,
        "identity_mismatches": tuple(dict.fromkeys(identity_mismatches)),
        "replay_manifest_mismatches": tuple(dict.fromkeys(replay_manifest_mismatches)),
        "metric_diffs": tuple(row.model_dump(mode="json") for row in metric_diffs),
        "blocker_reasons": tuple(dict.fromkeys(blockers)),
        "same_spec_data_config_verified": not identity_mismatches,
        "replay_manifest_identity_verified": source_replay_manifest is not None
        and full_replay_manifest is not None
        and not replay_manifest_mismatches,
        "metrics_verified": bool(metric_diffs) and all(row.within_tolerance for row in metric_diffs),
        "full_artifacts_verified": replay.artifact_mode == ArtifactMode.FULL and not missing_full_artifacts,
        "source_replay_identity_hash": source.replay_identity_hash,
        "replay_replay_identity_hash": replay.replay_identity_hash,
        "reference_engine_authority": source.reference_engine_authority and replay.reference_engine_authority,
    }
    return FullArtifactReplayVerification(
        **payload,
        verification_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "report_type": "full_artifact_replay_verification_v1",
                **_json_safe(payload),
            }
        ),
    )


def build_reference_rerun_plan(
    manifest: RunManifest | Mapping[str, Any],
    *,
    run_manifest_ref: str | Path | None = None,
    reason: str = "suspicious_fast_result_reference_audit",
) -> ReferenceRerunPlan:
    parsed = _parse_manifest(manifest)
    if parsed.engine_lane != EngineLane.FAST_VECTORIZED:
        raise ValueError("reference rerun plans can only be built from fast_vectorized manifests")
    replay_artifact = parsed.artifacts.get("replay_manifest")
    if replay_artifact is None:
        raise ValueError("fast manifest is missing replay_manifest artifact")
    replay_ref = replay_artifact.path
    if run_manifest_ref is not None:
        replay_ref = str(Path(run_manifest_ref).parent / replay_ref)
    planned_run_id = f"{parsed.run_id}-reference-audit"
    config_overrides = {
        "run_id": planned_run_id,
        "engine_lane": EngineLane.VECTORIZED.value,
        "artifact_mode": ArtifactMode.FULL.value,
        "expected_data_manifest_id": parsed.data_manifest_id,
        "expected_data_manifest_hash": parsed.data_manifest_hash,
        "expected_strategy_spec_hash": parsed.strategy_spec_hash,
        "expected_params_hash": parsed.params_hash,
        "reference_engine_authority": True,
        "speedup_claimed": False,
    }
    payload = {
        "source_run_id": parsed.run_id,
        "planned_run_id": planned_run_id,
        "reason": reason,
        "requested_engine_lane": EngineLane.VECTORIZED,
        "requested_artifact_mode": ArtifactMode.FULL,
        "required_replay_manifest_ref": replay_ref,
        "required_data_manifest_id": parsed.data_manifest_id,
        "expected_data_manifest_hash": parsed.data_manifest_hash,
        "expected_strategy_spec_hash": parsed.strategy_spec_hash,
        "expected_params_hash": parsed.params_hash,
        "same_spec_data_config_required": True,
        "config_overrides": config_overrides,
    }
    return ReferenceRerunPlan(
        **payload,
        rerun_plan_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "plan_type": "fast_lane_reference_rerun_plan_v1",
                **_json_safe(payload),
            }
        ),
    )


def build_full_artifact_replay_plan(
    manifest: RunManifest | Mapping[str, Any],
    *,
    run_manifest_ref: str | Path | None = None,
    reason: str = "artifact_light_full_replay",
) -> FullArtifactReplayPlan:
    parsed = _parse_manifest(manifest)
    if parsed.artifact_mode == ArtifactMode.FULL:
        raise ValueError("run manifest already has full artifact mode")
    if not parsed.replayable_to_full_artifacts:
        raise ValueError("run manifest is not replayable to full artifacts")
    replay_artifact = parsed.artifacts.get("replay_manifest")
    if replay_artifact is None:
        raise ValueError("run manifest is missing replay_manifest artifact")
    if parsed.replay_identity_hash is None:
        raise ValueError("run manifest is missing replay_identity_hash")
    replay_ref = replay_artifact.path
    if run_manifest_ref is not None:
        replay_ref = str(Path(run_manifest_ref).parent / replay_ref)
    planned_run_id = f"{parsed.run_id}-full-artifacts"
    config_overrides = {
        "run_id": planned_run_id,
        "engine_lane": parsed.engine_lane.value,
        "artifact_mode": ArtifactMode.FULL.value,
        "expected_data_manifest_id": parsed.data_manifest_id,
        "expected_data_manifest_hash": parsed.data_manifest_hash,
        "expected_strategy_spec_hash": parsed.strategy_spec_hash,
        "expected_params_hash": parsed.params_hash,
        "expected_replay_identity_hash": parsed.replay_identity_hash,
        "reference_engine_authority": parsed.reference_engine_authority,
        "speedup_claimed": False,
    }
    payload = {
        "source_run_id": parsed.run_id,
        "planned_run_id": planned_run_id,
        "reason": reason,
        "source_engine_lane": parsed.engine_lane,
        "requested_engine_lane": parsed.engine_lane,
        "source_artifact_mode": parsed.artifact_mode,
        "requested_artifact_mode": ArtifactMode.FULL,
        "required_replay_manifest_ref": replay_ref,
        "required_data_manifest_id": parsed.data_manifest_id,
        "expected_data_manifest_hash": parsed.data_manifest_hash,
        "expected_strategy_spec_hash": parsed.strategy_spec_hash,
        "expected_params_hash": parsed.params_hash,
        "expected_replay_identity_hash": parsed.replay_identity_hash,
        "same_spec_data_config_required": True,
        "reference_engine_authority": parsed.reference_engine_authority,
        "config_overrides": config_overrides,
    }
    return FullArtifactReplayPlan(
        **payload,
        replay_plan_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "plan_type": "full_artifact_replay_plan_v1",
                **_json_safe(payload),
            }
        ),
    )


def select_reference_audit_sample(
    run_ids: Sequence[str],
    *,
    sample_rate: float,
    seed: str = "fast_lane_reference_authority_v1",
    minimum_count: int = 1,
) -> tuple[str, ...]:
    if not 0.0 <= sample_rate <= 1.0:
        raise ValueError("sample_rate must be between 0 and 1")
    if minimum_count < 0:
        raise ValueError("minimum_count must be non-negative")
    unique_run_ids = tuple(sorted(dict.fromkeys(run_id for run_id in run_ids if run_id)))
    if sample_rate == 0.0 or not unique_run_ids:
        return ()
    ranked = sorted(
        (
            canonical_json_hash({"seed": seed, "run_id": run_id}),
            run_id,
        )
        for run_id in unique_run_ids
    )
    threshold = int(sample_rate * ((1 << 256) - 1))
    selected = {
        run_id
        for digest, run_id in ranked
        if int(digest, 16) <= threshold
    }
    for _digest, run_id in ranked:
        if len(selected) >= minimum_count:
            break
        selected.add(run_id)
    return tuple(sorted(selected))


def _parse_manifest(value: RunManifest | Mapping[str, Any]) -> RunManifest:
    return value if isinstance(value, RunManifest) else RunManifest.model_validate(value)


def _identity_mismatches(reference: RunManifest, fast: RunManifest) -> tuple[str, ...]:
    mismatches: list[str] = []
    for field in _IDENTITY_FIELDS:
        if getattr(reference, field) != getattr(fast, field):
            mismatches.append(field)
    return tuple(mismatches)


def _parity_benchmark_observations(reference: RunManifest, fast: RunManifest) -> dict[str, float]:
    observations: dict[str, float] = {}
    reference_runtime = reference.benchmark_observations.get("reference_runtime_seconds")
    fast_runtime = fast.benchmark_observations.get("fast_runtime_seconds")
    if reference_runtime is not None:
        observations["reference_runtime_seconds"] = reference_runtime
    if fast_runtime is not None:
        observations["fast_runtime_seconds"] = fast_runtime
    if reference_runtime is not None and fast_runtime is not None and fast_runtime > 0.0:
        observations["speedup_ratio"] = reference_runtime / fast_runtime
    for key in ("data_load_seconds", "artifact_write_seconds", "memory_peak_bytes"):
        ref_key = f"reference_{key}"
        fast_key = f"fast_{key}"
        if key in reference.benchmark_observations:
            observations[ref_key] = reference.benchmark_observations[key]
        if key in fast.benchmark_observations:
            observations[fast_key] = fast.benchmark_observations[key]
    return dict(sorted(observations.items()))


def _missing_speedup_claim_observations(observations: Mapping[str, float]) -> tuple[str, ...]:
    return tuple(sorted(_SPEEDUP_CLAIM_REQUIRED_OBSERVATIONS - set(observations)))


def _full_replay_identity_mismatches(source: RunManifest, replay: RunManifest) -> tuple[str, ...]:
    mismatches: list[str] = []
    for field in _FULL_REPLAY_IDENTITY_FIELDS:
        if getattr(source, field) != getattr(replay, field):
            mismatches.append(field)
    return tuple(mismatches)


def _replay_manifest_identity_mismatches(
    source_replay_manifest: Mapping[str, Any],
    full_replay_manifest: Mapping[str, Any],
) -> tuple[str, ...]:
    mismatches: list[str] = []
    for field in _REPLAY_MANIFEST_IDENTITY_FIELDS:
        if source_replay_manifest.get(field) != full_replay_manifest.get(field):
            mismatches.append(field)
    return tuple(mismatches)


def _json_safe(payload: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, Enum):
            safe[key] = value.value
        elif isinstance(value, Mapping):
            safe[key] = _json_safe(value)
        else:
            safe[key] = value
    return safe
