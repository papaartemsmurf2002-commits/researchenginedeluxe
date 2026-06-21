# V2-AUDIT-ID: V2-AUD-VAL-001
# V2-CONTRACTS: docs/contracts/validation_contract.md
# V2-BOUNDARY: research_only, overfit_diagnostics, no_live_imports
# V2-OWNER: v2_validation
"""Trial-family and overfit diagnostics for v2 sweeps."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from statistics import median

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc


class TrialResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    run_id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    family_id: str = Field(min_length=1)
    net_return: float
    fold_returns: tuple[float, ...] = ()
    validation_status: str = "pass"
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_trial(self) -> "TrialResult":
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("trial results must preserve the v2 research boundary")
        return self


class SweepCompletenessReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    experiment_id: str = Field(min_length=1)
    expected_trial_count: int = Field(ge=0)
    observed_trial_count: int = Field(ge=0)
    missing_trial_ids: tuple[str, ...] = ()
    unexpected_trial_ids: tuple[str, ...] = ()
    complete: bool
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False


class TrialFamilyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    experiment_id: str = Field(min_length=1)
    family_id: str = Field(min_length=1)
    trial_count: int = Field(ge=0)
    fold_count: int = Field(ge=0)
    best_run_id: str | None = None
    best_net_return: float | None = None
    median_net_return: float | None = None
    best_vs_median_gap: float | None = None
    pbo_score: float | None = Field(default=None, ge=0.0, le=1.0)
    pbo_diagnostic_ran: bool = False
    large_weak_family_warning: bool = False
    fold_stability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    validation_status: str
    blocker_reasons: tuple[str, ...] = ()
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False


def check_sweep_completeness(
    *,
    experiment_id: str,
    expected_trial_ids: Iterable[str],
    observed_trial_ids: Iterable[str],
) -> SweepCompletenessReport:
    if not experiment_id:
        raise ValueError("sweep experiment_id is required")
    expected = set(expected_trial_ids)
    observed = set(observed_trial_ids)
    missing = tuple(sorted(expected - observed))
    unexpected = tuple(sorted(observed - expected))
    return SweepCompletenessReport(
        experiment_id=experiment_id,
        expected_trial_count=len(expected),
        observed_trial_count=len(observed),
        missing_trial_ids=missing,
        unexpected_trial_ids=unexpected,
        complete=not missing and not unexpected,
    )


def require_complete_sweep(report: SweepCompletenessReport) -> None:
    if not report.complete:
        raise ValueError("sweep_trial_logging_incomplete")


def trial_family_report(
    trials: Iterable[TrialResult | dict],
    *,
    min_trials_for_pbo: int = 6,
    large_family_threshold: int = 20,
) -> TrialFamilyReport:
    parsed = [trial if isinstance(trial, TrialResult) else TrialResult.model_validate(trial) for trial in trials]
    if not parsed:
        raise ValueError("trial family report requires trials")
    experiment_ids = {trial.experiment_id for trial in parsed}
    if "" in experiment_ids or len(experiment_ids) != 1:
        raise ValueError("validation_rejects_missing_or_mixed_experiment_id_for_sweep")
    family_ids = {trial.family_id for trial in parsed}
    if len(family_ids) != 1:
        raise ValueError("trial family report requires one family_id")
    sorted_trials = sorted(parsed, key=lambda trial: (trial.net_return, trial.run_id), reverse=True)
    best = sorted_trials[0]
    returns = [trial.net_return for trial in parsed]
    median_return = float(median(returns))
    fold_count = max((len(trial.fold_returns) for trial in parsed), default=0)
    pbo_score = None
    pbo_ran = len(parsed) >= min_trials_for_pbo and fold_count >= 2
    if pbo_ran:
        pbo_score = _pbo_score(parsed, best)
    large_weak_warning = len(parsed) >= large_family_threshold and median_return <= 0.0 and best.net_return > 0.0
    stability_score = None
    if best.fold_returns:
        stability_score = sum(1 for value in best.fold_returns if value > 0.0) / len(best.fold_returns)
    blockers: list[str] = []
    if large_weak_warning:
        blockers.append("large_weak_family_best_result_warning")
    if pbo_score is not None and pbo_score >= 0.5:
        blockers.append("pbo_overfit_warning")
    return TrialFamilyReport(
        experiment_id=parsed[0].experiment_id,
        family_id=parsed[0].family_id,
        trial_count=len(parsed),
        fold_count=fold_count,
        best_run_id=best.run_id,
        best_net_return=best.net_return,
        median_net_return=median_return,
        best_vs_median_gap=best.net_return - median_return,
        pbo_score=pbo_score,
        pbo_diagnostic_ran=pbo_ran,
        large_weak_family_warning=large_weak_warning,
        fold_stability_score=stability_score,
        validation_status="warning" if blockers else "pass",
        blocker_reasons=tuple(blockers),
    )


def reject_post_lockbox_parameter_tuning(*, tuned_at: datetime, lockbox_start: datetime) -> None:
    tuned = ensure_utc(tuned_at)
    lockbox = ensure_utc(lockbox_start)
    if tuned >= lockbox:
        raise ValueError("post_lockbox_parameter_tuning_rejected")


def _pbo_score(trials: list[TrialResult], best: TrialResult) -> float:
    fold_count = len(best.fold_returns)
    bottom_half_count = 0
    for fold_index in range(fold_count):
        fold_values = [
            trial.fold_returns[fold_index]
            for trial in trials
            if len(trial.fold_returns) > fold_index
        ]
        if not fold_values:
            continue
        sorted_values = sorted(fold_values)
        best_fold_value = best.fold_returns[fold_index]
        rank = sorted_values.index(best_fold_value)
        if rank < len(sorted_values) / 2:
            bottom_half_count += 1
    return bottom_half_count / fold_count if fold_count else 0.0
