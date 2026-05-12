from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from tradingbotsuite.config import AppConfig


DISCOVERY_SPEC_VERSION = "discovery-run-spec-v1"
SUPPORTED_DISCOVERY_MODES = (
    "quick_smoke",
    "entry_discovery_standard",
    "hmm_regime_knn_lab",
    "perp_context_ablation",
    "filter_ablation_lab",
    "exit_lab",
    "deep_candidate_harvest",
    "promotion_gate_research_only",
)
SUPPORTED_REGIME_MODES = (
    "none",
    "gmm_gate_only",
    "gmm_same_regime_neighbors",
    "gmm_all_regime_neighbors_with_gate",
)
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True, slots=True)
class DiscoveryRegimeModeSettings:
    regime_mode: str
    regime_detector_type: str
    regime_gate_enabled: bool
    same_regime_neighbor_pool_enabled: bool
    true_hmm_backend_used: bool = False

    @property
    def same_regime_only(self) -> bool:
        return self.same_regime_neighbor_pool_enabled

    def to_payload(self) -> dict[str, Any]:
        return {
            "regime_mode": self.regime_mode,
            "regime_detector_type": self.regime_detector_type,
            "regime_gate_enabled": self.regime_gate_enabled,
            "same_regime_neighbor_pool_enabled": self.same_regime_neighbor_pool_enabled,
            "same_regime_only": self.same_regime_only,
            "true_hmm_backend_used": self.true_hmm_backend_used,
        }


def regime_mode_settings(regime_mode: str) -> DiscoveryRegimeModeSettings:
    normalized = str(regime_mode or "").strip().lower()
    if normalized == "none":
        return DiscoveryRegimeModeSettings(
            regime_mode="none",
            regime_detector_type="none",
            regime_gate_enabled=False,
            same_regime_neighbor_pool_enabled=False,
        )
    if normalized == "gmm_gate_only":
        return DiscoveryRegimeModeSettings(
            regime_mode="gmm_gate_only",
            regime_detector_type="gmm",
            regime_gate_enabled=True,
            same_regime_neighbor_pool_enabled=False,
        )
    if normalized == "gmm_same_regime_neighbors":
        return DiscoveryRegimeModeSettings(
            regime_mode="gmm_same_regime_neighbors",
            regime_detector_type="gmm",
            regime_gate_enabled=True,
            same_regime_neighbor_pool_enabled=True,
        )
    if normalized == "gmm_all_regime_neighbors_with_gate":
        return DiscoveryRegimeModeSettings(
            regime_mode="gmm_all_regime_neighbors_with_gate",
            regime_detector_type="gmm",
            regime_gate_enabled=True,
            same_regime_neighbor_pool_enabled=False,
        )
    raise ValueError(f"unsupported regime_mode:{regime_mode}")


@dataclass(frozen=True, slots=True)
class DiscoveryBudgetSpec:
    max_trials: int = 3
    trial_batch_size: int = 1
    snapshot_interval_minutes: int = 30
    rng_seed: int = 73

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "DiscoveryBudgetSpec":
        payload = payload or {}
        result = cls(
            max_trials=int(payload.get("max_trials", 3)),
            trial_batch_size=int(payload.get("trial_batch_size", 1)),
            snapshot_interval_minutes=int(payload.get("snapshot_interval_minutes", 30)),
            rng_seed=int(payload.get("rng_seed", 73)),
        )
        if result.max_trials <= 0:
            raise ValueError("budget.max_trials must be positive")
        if result.trial_batch_size <= 0:
            raise ValueError("budget.trial_batch_size must be positive")
        if result.snapshot_interval_minutes <= 0:
            raise ValueError("budget.snapshot_interval_minutes must be positive")
        return result

    def to_payload(self) -> dict[str, Any]:
        return {
            "max_trials": self.max_trials,
            "trial_batch_size": self.trial_batch_size,
            "snapshot_interval_minutes": self.snapshot_interval_minutes,
            "rng_seed": self.rng_seed,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryExecutionSpec:
    max_workers: int = 1
    persist_trial_artifacts: str = "all"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "DiscoveryExecutionSpec":
        payload = payload or {}
        spec = cls(
            max_workers=int(payload.get("max_workers", 1)),
            persist_trial_artifacts=str(payload.get("persist_trial_artifacts", "all")).strip().lower() or "all",
        )
        spec.validate()
        return spec

    def validate(self) -> None:
        if self.max_workers <= 0:
            raise ValueError("execution.max_workers must be positive")
        if self.max_workers > 64:
            raise ValueError("execution.max_workers must be <= 64")
        if self.persist_trial_artifacts not in {"all", "interesting_only"}:
            raise ValueError("execution.persist_trial_artifacts must be one of all, interesting_only")

    def to_payload(self) -> dict[str, Any]:
        return {
            "max_workers": self.max_workers,
            "persist_trial_artifacts": self.persist_trial_artifacts,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryDataSpec:
    dataset_path: Path | None = None
    dataset_manifest_paths: tuple[Path, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None, *, repo_root: Path) -> "DiscoveryDataSpec":
        payload = payload or {}
        return cls(
            dataset_path=_resolve_optional_path(payload.get("dataset_path"), repo_root=repo_root),
            dataset_manifest_paths=tuple(
                _resolve_path(item, repo_root=repo_root)
                for item in payload.get("dataset_manifest_paths") or ()
                if str(item).strip()
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "dataset_path": str(self.dataset_path) if self.dataset_path is not None else None,
            "dataset_manifest_paths": [str(path) for path in self.dataset_manifest_paths],
        }


@dataclass(frozen=True, slots=True)
class DiscoverySearchSpec:
    hmm_state_counts: tuple[int, ...] = (4,)
    hmm_posterior_thresholds: tuple[float, ...] = (0.60,)
    hmm_entropy_thresholds: tuple[float, ...] = (0.78,)
    label_horizons: tuple[str, ...] = ("4h",)
    k_values: tuple[int, ...] = (8,)
    min_neighbor_counts: tuple[int, ...] = (4,)
    distance_metrics: tuple[str, ...] = ("euclidean",)
    probability_thresholds: tuple[float, ...] = (0.55,)
    expected_value_thresholds: tuple[float, ...] = (0.0,)
    min_neighbor_agreements: tuple[float, ...] = (0.55,)
    min_distance_qualities: tuple[float, ...] = (0.01,)
    vote_margin_thresholds: tuple[float, ...] = (0.05,)
    same_regime_only_values: tuple[bool, ...] = (True,)
    regime_modes: tuple[str, ...] = ("gmm_same_regime_neighbors",)
    min_splits: int = 4
    purge_embargo_bars: int = 8
    min_trade_count: int = 5
    min_signal_rate: float = 0.0005
    max_signal_rate: float = 0.25
    min_realized_expectancy: float = 0.0

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "DiscoverySearchSpec":
        payload = payload or {}
        same_regime_only_values = _bool_tuple(payload.get("same_regime_only_values"), default=(True,))
        spec = cls(
            hmm_state_counts=_int_tuple(payload.get("hmm_state_counts"), default=(4,)),
            hmm_posterior_thresholds=_float_tuple(payload.get("hmm_posterior_thresholds"), default=(0.60,)),
            hmm_entropy_thresholds=_float_tuple(payload.get("hmm_entropy_thresholds"), default=(0.78,)),
            label_horizons=_string_tuple(payload.get("label_horizons"), default=("4h",)),
            k_values=_int_tuple(payload.get("k_values"), default=(8,)),
            min_neighbor_counts=_int_tuple(payload.get("min_neighbor_counts"), default=(4,)),
            distance_metrics=_string_tuple(payload.get("distance_metrics"), default=("euclidean",)),
            probability_thresholds=_float_tuple(payload.get("probability_thresholds"), default=(0.55,)),
            expected_value_thresholds=_float_tuple(payload.get("expected_value_thresholds"), default=(0.0,)),
            min_neighbor_agreements=_float_tuple(payload.get("min_neighbor_agreements"), default=(0.55,)),
            min_distance_qualities=_float_tuple(payload.get("min_distance_qualities"), default=(0.01,)),
            vote_margin_thresholds=_float_tuple(payload.get("vote_margin_thresholds"), default=(0.05,)),
            same_regime_only_values=same_regime_only_values,
            regime_modes=_regime_mode_tuple(payload.get("regime_modes"), same_regime_only_values=same_regime_only_values),
            min_splits=int(payload.get("min_splits", 4)),
            purge_embargo_bars=int(payload.get("purge_embargo_bars", 8)),
            min_trade_count=int(payload.get("min_trade_count", 5)),
            min_signal_rate=float(payload.get("min_signal_rate", 0.0005)),
            max_signal_rate=float(payload.get("max_signal_rate", 0.25)),
            min_realized_expectancy=float(payload.get("min_realized_expectancy", 0.0)),
        )
        spec.validate()
        return spec

    def validate(self) -> None:
        if any(value <= 0 for value in self.hmm_state_counts):
            raise ValueError("search.hmm_state_counts must be positive")
        for field_name, values in {
            "hmm_posterior_thresholds": self.hmm_posterior_thresholds,
            "hmm_entropy_thresholds": self.hmm_entropy_thresholds,
        }.items():
            if any(value <= 0.0 or value > 1.0 for value in values):
                raise ValueError(f"search.{field_name} values must be between 0 and 1")
        if not self.label_horizons:
            raise ValueError("search.label_horizons must not be empty")
        if any(value <= 0 for value in self.k_values):
            raise ValueError("search.k_values must be positive")
        if any(value <= 0 for value in self.min_neighbor_counts):
            raise ValueError("search.min_neighbor_counts must be positive")
        supported_metrics = {"euclidean", "manhattan", "cosine"}
        invalid_metrics = sorted(set(self.distance_metrics) - supported_metrics)
        if invalid_metrics:
            raise ValueError(f"search.distance_metrics unsupported:{','.join(invalid_metrics)}")
        for field_name, values in {
            "probability_thresholds": self.probability_thresholds,
            "min_neighbor_agreements": self.min_neighbor_agreements,
            "min_distance_qualities": self.min_distance_qualities,
            "vote_margin_thresholds": self.vote_margin_thresholds,
        }.items():
            if any(value < 0.0 or value > 1.0 for value in values):
                raise ValueError(f"search.{field_name} values must be between 0 and 1")
        invalid_regime_modes = sorted(set(self.regime_modes) - set(SUPPORTED_REGIME_MODES))
        if invalid_regime_modes:
            raise ValueError(f"search.regime_modes unsupported:{','.join(invalid_regime_modes)}")
        if self.min_splits < 1:
            raise ValueError("search.min_splits must be positive")
        if self.purge_embargo_bars < 0:
            raise ValueError("search.purge_embargo_bars must be non-negative")
        if self.min_trade_count < 0:
            raise ValueError("search.min_trade_count must be non-negative")
        if self.min_signal_rate < 0.0 or self.max_signal_rate <= 0.0 or self.min_signal_rate > self.max_signal_rate:
            raise ValueError("search signal-rate bounds are invalid")

    def to_payload(self) -> dict[str, Any]:
        return {
            "hmm_state_counts": list(self.hmm_state_counts),
            "hmm_posterior_thresholds": list(self.hmm_posterior_thresholds),
            "hmm_entropy_thresholds": list(self.hmm_entropy_thresholds),
            "label_horizons": list(self.label_horizons),
            "k_values": list(self.k_values),
            "min_neighbor_counts": list(self.min_neighbor_counts),
            "distance_metrics": list(self.distance_metrics),
            "probability_thresholds": list(self.probability_thresholds),
            "expected_value_thresholds": list(self.expected_value_thresholds),
            "min_neighbor_agreements": list(self.min_neighbor_agreements),
            "min_distance_qualities": list(self.min_distance_qualities),
            "vote_margin_thresholds": list(self.vote_margin_thresholds),
            "same_regime_only_values": list(self.same_regime_only_values),
            "regime_modes": list(self.regime_modes),
            "min_splits": self.min_splits,
            "purge_embargo_bars": self.purge_embargo_bars,
            "min_trade_count": self.min_trade_count,
            "min_signal_rate": self.min_signal_rate,
            "max_signal_rate": self.max_signal_rate,
            "min_realized_expectancy": self.min_realized_expectancy,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryTrialTemplate:
    trial_id: str
    candidate_id: str
    ledger_kind: str = "blocked"
    candidate_family: str = "placeholder_discovery_candidate"
    score: float = 0.0
    blocker_code: str = "placeholder_trial_no_signal_engine"
    filter_blocker_code: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, index: int) -> "DiscoveryTrialTemplate":
        if not isinstance(payload, Mapping):
            raise ValueError("trial_templates entries must be JSON objects")
        trial_id = str(payload.get("trial_id") or f"trial-{index:06d}").strip()
        candidate_id = str(payload.get("candidate_id") or f"candidate-{index:06d}").strip()
        if not SAFE_RUN_ID_RE.match(trial_id):
            raise ValueError("trial_templates.trial_id must be a safe file-system identifier")
        ledger_kind = str(payload.get("ledger_kind", "blocked")).strip()
        if ledger_kind not in {"interesting", "blocked", "filter_blocked"}:
            raise ValueError("trial_templates.ledger_kind must be one of interesting, blocked, filter_blocked")
        return cls(
            trial_id=trial_id,
            candidate_id=candidate_id,
            ledger_kind=ledger_kind,
            candidate_family=str(payload.get("candidate_family", "placeholder_discovery_candidate")).strip()
            or "placeholder_discovery_candidate",
            score=float(payload.get("score", 0.0)),
            blocker_code=str(payload.get("blocker_code", "placeholder_trial_no_signal_engine")).strip(),
            filter_blocker_code=str(payload.get("filter_blocker_code", "")).strip(),
            payload=_json_safe_mapping(payload.get("payload") or {}),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "candidate_id": self.candidate_id,
            "ledger_kind": self.ledger_kind,
            "candidate_family": self.candidate_family,
            "score": self.score,
            "blocker_code": self.blocker_code,
            "filter_blocker_code": self.filter_blocker_code,
            "payload": _json_safe_mapping(self.payload),
        }


@dataclass(frozen=True, slots=True)
class DiscoveryRunSpec:
    run_id: str
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    discovery_mode: str = "quick_smoke"
    research_output_dir: Path | None = None
    output_dir: Path | None = None
    feature_column_sets_path: Path | None = None
    feature_column_set_ids: tuple[str, ...] = ()
    data: DiscoveryDataSpec = field(default_factory=DiscoveryDataSpec)
    search: DiscoverySearchSpec = field(default_factory=DiscoverySearchSpec)
    execution: DiscoveryExecutionSpec = field(default_factory=DiscoveryExecutionSpec)
    budget: DiscoveryBudgetSpec = field(default_factory=DiscoveryBudgetSpec)
    trial_templates: tuple[DiscoveryTrialTemplate, ...] = ()

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        spec_path: Path,
        repo_root: Path | None = None,
    ) -> "DiscoveryRunSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("discovery run spec must be a JSON object")
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run_id is required")
        if not SAFE_RUN_ID_RE.match(run_id):
            raise ValueError("run_id must be a safe file-system identifier")
        discovery_mode = str(payload.get("discovery_mode", "quick_smoke")).strip()
        if discovery_mode not in SUPPORTED_DISCOVERY_MODES:
            raise ValueError(f"discovery_mode must be one of: {', '.join(SUPPORTED_DISCOVERY_MODES)}")
        root = (repo_root or _repo_root()).resolve()
        trial_templates = tuple(
            DiscoveryTrialTemplate.from_payload(item, index=index)
            for index, item in enumerate(payload.get("trial_templates") or (), start=1)
        )
        return cls(
            run_id=run_id,
            symbol=str(payload.get("symbol", "BTCUSDT")).upper(),
            timeframe=str(payload.get("timeframe", "15m")).strip(),
            discovery_mode=discovery_mode,
            research_output_dir=_resolve_optional_path(payload.get("research_output_dir"), repo_root=root),
            output_dir=_resolve_optional_path(payload.get("output_dir"), repo_root=root),
            feature_column_sets_path=_resolve_optional_path(payload.get("feature_column_sets_path"), repo_root=root),
            feature_column_set_ids=tuple(
                str(item).strip()
                for item in payload.get("feature_column_set_ids") or ()
                if str(item).strip()
            ),
            data=DiscoveryDataSpec.from_payload(payload.get("data"), repo_root=root),
            search=DiscoverySearchSpec.from_payload(payload.get("search")),
            execution=DiscoveryExecutionSpec.from_payload(payload.get("execution")),
            budget=DiscoveryBudgetSpec.from_payload(payload.get("budget")),
            trial_templates=trial_templates,
        )

    @classmethod
    def from_path(cls, path: Path, *, repo_root: Path | None = None) -> "DiscoveryRunSpec":
        spec_path = Path(path).expanduser().resolve()
        payload = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        return cls.from_payload(payload, spec_path=spec_path, repo_root=repo_root)

    def to_payload(self) -> dict[str, Any]:
        return {
            "spec_version": DISCOVERY_SPEC_VERSION,
            "run_id": self.run_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "discovery_mode": self.discovery_mode,
            "research_output_dir": str(self.research_output_dir) if self.research_output_dir is not None else None,
            "output_dir": str(self.output_dir) if self.output_dir is not None else None,
            "feature_column_sets_path": (
                str(self.feature_column_sets_path) if self.feature_column_sets_path is not None else None
            ),
            "feature_column_set_ids": list(self.feature_column_set_ids),
            "data": self.data.to_payload(),
            "search": self.search.to_payload(),
            "execution": self.execution.to_payload(),
            "budget": self.budget.to_payload(),
            "trial_templates": [template.to_payload() for template in self.trial_templates],
        }


@dataclass(frozen=True, slots=True)
class DiscoveryResolvedPaths:
    repo_root: Path
    research_output_dir: Path
    output_dir: Path

    def to_payload(self) -> dict[str, str]:
        return {
            "repo_root": str(self.repo_root),
            "research_output_dir": str(self.research_output_dir),
            "output_dir": str(self.output_dir),
        }


def resolve_discovery_paths(
    spec: DiscoveryRunSpec,
    *,
    app_config: AppConfig | None = None,
    repo_root: Path | None = None,
) -> DiscoveryResolvedPaths:
    root = (repo_root or _repo_root()).resolve()
    config = app_config or AppConfig.from_env()
    research_output_dir = spec.research_output_dir or _resolve_path(config.research.output_dir, repo_root=root)
    research_output_dir = research_output_dir.resolve()
    output_dir = spec.output_dir or research_output_dir / "discovery_runs" / spec.run_id
    output_dir = output_dir.resolve()
    _assert_path_within(output_dir, research_output_dir, field_name="output_dir")
    return DiscoveryResolvedPaths(repo_root=root, research_output_dir=research_output_dir, output_dir=output_dir)


def generated_trial_templates(spec: DiscoveryRunSpec) -> tuple[DiscoveryTrialTemplate, ...]:
    if spec.trial_templates:
        return spec.trial_templates[: spec.budget.max_trials]
    if spec.discovery_mode in {"entry_discovery_standard", "hmm_regime_knn_lab", "deep_candidate_harvest"}:
        return _generated_real_discovery_trial_templates(spec)
    templates: list[DiscoveryTrialTemplate] = []
    for index in range(1, spec.budget.max_trials + 1):
        if index == 1:
            ledger_kind = "interesting"
            blocker_code = ""
            filter_blocker_code = ""
            score = 0.1
        elif index % 2 == 0:
            ledger_kind = "blocked"
            blocker_code = "placeholder_trial_no_knn_engine"
            filter_blocker_code = ""
            score = 0.0
        else:
            ledger_kind = "filter_blocked"
            blocker_code = ""
            filter_blocker_code = "placeholder_filter_blocker"
            score = 0.0
        templates.append(
            DiscoveryTrialTemplate(
                trial_id=f"trial-{index:06d}",
                candidate_id=f"{spec.run_id}-candidate-{index:06d}",
                ledger_kind=ledger_kind,
                score=score,
                blocker_code=blocker_code,
                filter_blocker_code=filter_blocker_code,
                payload={"placeholder": True, "trial_index": index},
            )
        )
    return tuple(templates)


def _generated_real_discovery_trial_templates(spec: DiscoveryRunSpec) -> tuple[DiscoveryTrialTemplate, ...]:
    import random

    feature_set_ids = spec.feature_column_set_ids or ("price_trend_vol",)
    search = spec.search
    k_neighbor_pairs = tuple(
        {"k": int(k_value), "min_neighbor_count": int(min_neighbor_count)}
        for k_value in search.k_values
        for min_neighbor_count in search.min_neighbor_counts
        if int(min_neighbor_count) <= int(k_value)
    )
    dimensions: tuple[tuple[str, tuple[Any, ...]], ...] = (
        ("feature_column_set_id", tuple(feature_set_ids)),
        ("hmm_state_count", tuple(int(value) for value in search.hmm_state_counts)),
        ("hmm_posterior_threshold", tuple(float(value) for value in search.hmm_posterior_thresholds)),
        ("hmm_entropy_threshold", tuple(float(value) for value in search.hmm_entropy_thresholds)),
        ("label_horizon", tuple(search.label_horizons)),
        ("knn_neighbor_pair", k_neighbor_pairs),
        ("distance_metric", tuple(search.distance_metrics)),
        ("probability_threshold", tuple(float(value) for value in search.probability_thresholds)),
        ("expected_value_threshold", tuple(float(value) for value in search.expected_value_thresholds)),
        ("min_neighbor_agreement", tuple(float(value) for value in search.min_neighbor_agreements)),
        ("min_distance_quality", tuple(float(value) for value in search.min_distance_qualities)),
        ("vote_margin_threshold", tuple(float(value) for value in search.vote_margin_thresholds)),
        ("regime_mode", tuple(search.regime_modes)),
    )
    total_combinations = _dimension_space_size(dimensions)
    rng = random.Random(int(spec.budget.rng_seed))
    if total_combinations <= 0:
        raise ValueError("real discovery search generated no trial combinations")
    if spec.budget.max_trials >= total_combinations:
        sampled_indices = list(range(total_combinations))
        rng.shuffle(sampled_indices)
    else:
        sampled_indices = rng.sample(range(total_combinations), spec.budget.max_trials)
    templates: list[DiscoveryTrialTemplate] = []
    for index, combination_index in enumerate(sampled_indices, start=1):
        payload = _payload_from_dimension_index(combination_index, dimensions)
        payload.update(payload.pop("knn_neighbor_pair"))
        payload["trial_kind"] = "regime_knn_entry_discovery"
        payload.update(regime_mode_settings(str(payload["regime_mode"])).to_payload())
        payload["search_space_total_combinations"] = total_combinations
        digest = _stable_payload_digest({"run_id": spec.run_id, "index": index, **payload})[:16]
        templates.append(
            DiscoveryTrialTemplate(
                trial_id=f"trial-{index:06d}",
                candidate_id=f"{spec.run_id}-regime-knn-{digest}",
                ledger_kind="blocked",
                candidate_family="regime_knn_entry_discovery",
                score=0.0,
                blocker_code="not_evaluated",
                filter_blocker_code="",
                payload=payload,
            )
        )
    return tuple(templates)


def _dimension_space_size(dimensions: tuple[tuple[str, tuple[Any, ...]], ...]) -> int:
    total = 1
    for _, values in dimensions:
        total *= len(values)
    return total


def _payload_from_dimension_index(index: int, dimensions: tuple[tuple[str, tuple[Any, ...]], ...]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    remaining = int(index)
    for name, values in reversed(dimensions):
        size = len(values)
        if size <= 0:
            raise ValueError("real discovery search generated an empty dimension")
        payload[name] = values[remaining % size]
        remaining //= size
    return payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_optional_path(value: Any, *, repo_root: Path) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    return _resolve_path(value, repo_root=repo_root)


def _resolve_path(value: Any, *, repo_root: Path) -> Path:
    candidate = Path(str(value)).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _assert_path_within(path: Path, root: Path, *, field_name: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay under the configured research output directory") from exc


def _json_safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("payload must be a JSON object")
    return json.loads(json.dumps(dict(value), sort_keys=True, default=str, allow_nan=False))


def _string_tuple(value: Any, *, default: tuple[str, ...]) -> tuple[str, ...]:
    values = tuple(str(item).strip() for item in (value or default) if str(item).strip())
    return values or default


def _int_tuple(value: Any, *, default: tuple[int, ...]) -> tuple[int, ...]:
    values = tuple(int(item) for item in (value or default))
    return values or default


def _float_tuple(value: Any, *, default: tuple[float, ...]) -> tuple[float, ...]:
    values = tuple(float(item) for item in (value or default))
    return values or default


def _bool_tuple(value: Any, *, default: tuple[bool, ...]) -> tuple[bool, ...]:
    if value is None:
        return default
    values = tuple(_bool_value(item) for item in value)
    return values or default


def _regime_mode_tuple(value: Any, *, same_regime_only_values: tuple[bool, ...]) -> tuple[str, ...]:
    if value is not None:
        modes = tuple(str(item).strip().lower() for item in value if str(item).strip())
    else:
        modes = tuple(
            "gmm_same_regime_neighbors" if same_regime_only else "gmm_all_regime_neighbors_with_gate"
            for same_regime_only in same_regime_only_values
        )
    deduped = tuple(dict.fromkeys(modes))
    return deduped or ("gmm_same_regime_neighbors",)


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _stable_payload_digest(payload: Mapping[str, Any]) -> str:
    from hashlib import sha256

    return sha256(json.dumps(dict(payload), sort_keys=True, default=str, allow_nan=False).encode("utf-8")).hexdigest()
