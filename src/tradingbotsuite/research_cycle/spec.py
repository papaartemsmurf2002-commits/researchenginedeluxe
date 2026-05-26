from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


RESEARCH_CYCLE_SPEC_VERSION = "historical-research-cycle-spec-v1"
REQUIRED_HOLDING_WINDOWS = ("1h", "4h", "12h", "24h", "72h", "7d")
DEFAULT_FEATURE_SETS = (
    "features_price_trend_vol",
    "features_price_trend_vol_wt3d",
    "features_full_context_no_wt",
    "features_full_context_wt3d",
    "features_perp_context_only",
    "features_microstructure_filter_only",
)
DEFAULT_STRATEGIES = (
    "baseline_no_trade",
    "trend_following_v1",
    "volatility_breakout_v1",
    "range_reversion_v1",
    "funding_basis_v1",
    "regime_adaptive_v1",
    "hmm_knn_diagnostic_v1",
)
BACKTEST_BACKENDS = ("reference", "vector_fixed_holding", "cuda_fixed_holding", "cuda_batched_fixed_holding", "auto")
GPU_EXECUTION_PROFILES = ("fastest_exact", "conservative", "cuda_exact_batched", "hybrid_tensorcore_screening")
TENSOR_CORE_POLICIES = ("disabled", "screening_only")
SUPPORTED_VALIDATION_SPLIT_MODES = (
    "purged_embargoed_walk_forward",
    "anchored_walk_forward",
    "rolling_walk_forward",
    "shifted_purged_walk_forward",
    "month_holdout",
    "stress_period_holdout",
    "regime_holdout",
)
SUPPORTED_RESEARCH_EXIT_POLICIES = (
    "fixed_holding_window",
    "triple_barrier",
    "triple_barrier_atr",
    "volatility_scaled_barrier",
    "regime_flip_exit",
    "funding_adverse_exit",
    "funding_aware_exit_v1",
    "oi_contraction_exit_v1",
    "basis_normalization_exit_v1",
    "premium_normalization_exit_v1",
    "gmm_transition_exit_v1",
    "knn_remaining_edge_exit_v1",
    "knn_dynamic_barriers_v1",
    "alpha_decay_exit",
    "adverse_selection_exit",
    "trailing_atr_after_profit",
    "simple_runner_v1",
    "max_mae_stop",
)
DEFAULT_EXIT_POLICIES = (
    {
        "exit_policy_id": "fixed_holding_window",
        "exit_policy_params": {},
        "target_return": None,
        "stop_return": None,
        "exit_policy_source": "default_fixed_holding",
    },
)


@dataclass(frozen=True, slots=True)
class CycleDataSpec:
    dataset_manifest_paths: tuple[Path, ...] = ()
    local_fixture_dir: Path | None = None
    dataset_path: Path | None = None
    lower_timeframe_dataset_path: Path | None = None
    synthetic_fixture: bool = False
    synthetic_row_count: int = 240
    synthetic_variant: str = "balanced"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None, *, base_path: Path) -> "CycleDataSpec":
        payload = payload or {}
        return cls(
            dataset_manifest_paths=tuple(_resolve_path(item, base_path=base_path) for item in payload.get("dataset_manifest_paths", ())),
            local_fixture_dir=(
                _resolve_path(payload["local_fixture_dir"], base_path=base_path)
                if payload.get("local_fixture_dir")
                else None
            ),
            dataset_path=(
                _resolve_path(payload["dataset_path"], base_path=base_path)
                if payload.get("dataset_path")
                else None
            ),
            lower_timeframe_dataset_path=(
                _resolve_path(payload["lower_timeframe_dataset_path"], base_path=base_path)
                if payload.get("lower_timeframe_dataset_path")
                else None
            ),
            synthetic_fixture=bool(payload.get("synthetic_fixture", False)),
            synthetic_row_count=int(payload.get("synthetic_row_count", 240)),
            synthetic_variant=str(payload.get("synthetic_variant", "balanced")),
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "dataset_manifest_paths": [str(path) for path in self.dataset_manifest_paths],
            "local_fixture_dir": str(self.local_fixture_dir) if self.local_fixture_dir is not None else None,
            "dataset_path": str(self.dataset_path) if self.dataset_path is not None else None,
            "lower_timeframe_dataset_path": (
                str(self.lower_timeframe_dataset_path)
                if self.lower_timeframe_dataset_path is not None
                else None
            ),
            "synthetic_fixture": self.synthetic_fixture,
        }
        if self.synthetic_fixture:
            payload["synthetic_row_count"] = self.synthetic_row_count
            payload["synthetic_variant"] = self.synthetic_variant
        return payload


@dataclass(frozen=True, slots=True)
class MaterializedPredictionOverlaySpec:
    feature_set_id: str
    kind: str
    predictions_path: Path
    manifest_path: Path | None = None
    join_key: str = "source_row_index"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, base_path: Path) -> "MaterializedPredictionOverlaySpec":
        if not isinstance(payload, Mapping):
            raise ValueError("features.materialized_prediction_overlays entries must be JSON objects")
        feature_set_id = str(payload.get("feature_set_id") or "").strip()
        if not feature_set_id:
            raise ValueError("features.materialized_prediction_overlays.feature_set_id is required")
        kind = str(payload.get("kind", "hmm_knn_local_analog_v2")).strip()
        if kind != "hmm_knn_local_analog_v2":
            raise ValueError(f"unsupported materialized prediction overlay kind: {kind}")
        if not payload.get("predictions_path"):
            raise ValueError("features.materialized_prediction_overlays.predictions_path is required")
        join_key = str(payload.get("join_key", "source_row_index")).strip()
        if join_key not in {"source_row_index", "bar_time_ms", "feature_time_ms"}:
            raise ValueError(f"unsupported materialized prediction overlay join_key: {join_key}")
        return cls(
            feature_set_id=feature_set_id,
            kind=kind,
            predictions_path=_resolve_path(payload["predictions_path"], base_path=base_path),
            manifest_path=(
                _resolve_path(payload["manifest_path"], base_path=base_path)
                if payload.get("manifest_path")
                else None
            ),
            join_key=join_key,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "feature_set_id": self.feature_set_id,
            "kind": self.kind,
            "predictions_path": str(self.predictions_path),
            "manifest_path": str(self.manifest_path) if self.manifest_path is not None else None,
            "join_key": self.join_key,
        }


@dataclass(frozen=True, slots=True)
class CycleFeatureSpec:
    feature_sets: tuple[str, ...] = DEFAULT_FEATURE_SETS
    materialized_prediction_overlays: tuple[MaterializedPredictionOverlaySpec, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None, *, base_path: Path) -> "CycleFeatureSpec":
        payload = payload or {}
        feature_sets = tuple(str(item) for item in payload.get("feature_sets", DEFAULT_FEATURE_SETS))
        if not feature_sets:
            raise ValueError("at least one feature set is required")
        raw_overlays = payload.get("materialized_prediction_overlays", ())
        if isinstance(raw_overlays, Mapping):
            raw_overlays = (raw_overlays,)
        overlays = tuple(
            MaterializedPredictionOverlaySpec.from_payload(item, base_path=base_path)
            for item in raw_overlays
        )
        unknown_feature_sets = sorted({overlay.feature_set_id for overlay in overlays} - set(feature_sets))
        if unknown_feature_sets:
            raise ValueError(f"materialized prediction overlay feature_set_id not declared: {', '.join(unknown_feature_sets)}")
        duplicate_keys = [
            f"{overlay.feature_set_id}:{overlay.kind}"
            for overlay in overlays
            if sum(1 for item in overlays if item.feature_set_id == overlay.feature_set_id and item.kind == overlay.kind) > 1
        ]
        if duplicate_keys:
            raise ValueError(f"duplicate materialized prediction overlay: {sorted(set(duplicate_keys))[0]}")
        return cls(feature_sets=feature_sets, materialized_prediction_overlays=overlays)

    def to_payload(self) -> dict[str, Any]:
        return {
            "feature_sets": list(self.feature_sets),
            "materialized_prediction_overlays": [
                overlay.to_payload()
                for overlay in self.materialized_prediction_overlays
            ],
        }


@dataclass(frozen=True, slots=True)
class CycleValidationSpec:
    walk_forward: str = "rolling_and_anchored"
    purge_embargo_bars: int = 8
    stress_periods_required: bool = True
    min_splits: int = 6
    trade_count_floor: int = 50
    max_single_split_pnl_share: float = 0.5
    min_cost_stress_survival_rate: float = 1.0
    split_modes: tuple[str, ...] = ("purged_embargoed_walk_forward",)
    rolling_train_window_bars: int | None = None
    shifted_anchor_offsets: tuple[int, ...] = (1,)
    regime_column: str = "validation_regime"
    stress_volatility_column: str = "volatility_shock_zscore"
    stress_zscore_threshold: float = 2.0

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "CycleValidationSpec":
        payload = payload or {}
        split_modes = _validation_split_modes(payload.get("split_modes"))
        rolling_train_window_bars = _optional_positive_int(
            payload.get("rolling_train_window_bars"),
            field_name="validation.rolling_train_window_bars",
        )
        if "rolling_walk_forward" in split_modes and rolling_train_window_bars is None:
            raise ValueError("validation.rolling_train_window_bars is required for rolling_walk_forward")
        return cls(
            walk_forward=str(payload.get("walk_forward", "rolling_and_anchored")),
            purge_embargo_bars=int(payload.get("purge_embargo_bars", 8)),
            stress_periods_required=bool(payload.get("stress_periods_required", True)),
            min_splits=int(payload.get("min_splits", 6)),
            trade_count_floor=int(payload.get("trade_count_floor", 50)),
            max_single_split_pnl_share=float(payload.get("max_single_split_pnl_share", 0.5)),
            min_cost_stress_survival_rate=_bounded_rate(
                payload.get("min_cost_stress_survival_rate", 1.0),
                field_name="validation.min_cost_stress_survival_rate",
            ),
            split_modes=split_modes,
            rolling_train_window_bars=rolling_train_window_bars,
            shifted_anchor_offsets=_shifted_anchor_offsets(payload.get("shifted_anchor_offsets")),
            regime_column=str(payload.get("regime_column", "validation_regime")),
            stress_volatility_column=str(payload.get("stress_volatility_column", "volatility_shock_zscore")),
            stress_zscore_threshold=float(payload.get("stress_zscore_threshold", 2.0)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "walk_forward": self.walk_forward,
            "purge_embargo_bars": self.purge_embargo_bars,
            "stress_periods_required": self.stress_periods_required,
            "min_splits": self.min_splits,
            "trade_count_floor": self.trade_count_floor,
            "max_single_split_pnl_share": self.max_single_split_pnl_share,
            "min_cost_stress_survival_rate": self.min_cost_stress_survival_rate,
            "split_modes": list(self.split_modes),
            "rolling_train_window_bars": self.rolling_train_window_bars,
            "shifted_anchor_offsets": list(self.shifted_anchor_offsets),
            "regime_column": self.regime_column,
            "stress_volatility_column": self.stress_volatility_column,
            "stress_zscore_threshold": self.stress_zscore_threshold,
        }


@dataclass(frozen=True, slots=True)
class CycleOptimizerSpec:
    method_sequence: tuple[str, ...] = ("coarse_lhs", "adaptive_grid", "stability_region_refine")
    max_candidates_per_strategy: int = 2000
    top_regions_to_refine: int = 10
    search_spaces: tuple[Mapping[str, Any], ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "CycleOptimizerSpec":
        payload = payload or {}
        raw_search_spaces = payload.get("search_spaces", ())
        if isinstance(raw_search_spaces, Mapping):
            raw_search_spaces = (raw_search_spaces,)
        return cls(
            method_sequence=tuple(str(item) for item in payload.get("method_sequence", ("coarse_lhs", "adaptive_grid", "stability_region_refine"))),
            max_candidates_per_strategy=int(payload.get("max_candidates_per_strategy", 2000)),
            top_regions_to_refine=int(payload.get("top_regions_to_refine", 10)),
            search_spaces=tuple(_search_space_payload(item) for item in raw_search_spaces),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "method_sequence": list(self.method_sequence),
            "max_candidates_per_strategy": self.max_candidates_per_strategy,
            "top_regions_to_refine": self.top_regions_to_refine,
            "search_spaces": [_json_safe_mapping(space) for space in self.search_spaces],
        }


@dataclass(frozen=True, slots=True)
class CycleComputeSpec:
    cpu_threads: int = 48
    gpu_acceleration: str = "prefer_nvidia_cuda_when_backend_available"
    gpu_device_class: str = "nvidia_50_series"
    gpu_required: bool = False
    gpu_execution_profile: str = "fastest_exact"
    tensor_core_policy: str = "disabled"
    gpu_batch_candidates: int = 512
    gpu_memory_fraction_limit: float = 0.70
    gpu_validation_sample_rate: float = 0.02

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "CycleComputeSpec":
        payload = payload or {}
        cpu_threads = int(payload.get("cpu_threads", 48))
        if cpu_threads < 1 or cpu_threads > 64:
            raise ValueError("compute.cpu_threads must be between 1 and 64")
        gpu_acceleration = str(payload.get("gpu_acceleration", "prefer_nvidia_cuda_when_backend_available")).strip().lower()
        allowed_gpu_modes = {
            "disabled",
            "prefer_nvidia_cuda_when_backend_available",
            "require_nvidia_cuda_backend",
        }
        if gpu_acceleration not in allowed_gpu_modes:
            raise ValueError(f"compute.gpu_acceleration must be one of: {', '.join(sorted(allowed_gpu_modes))}")
        gpu_execution_profile = str(payload.get("gpu_execution_profile", "fastest_exact")).strip().lower()
        if gpu_execution_profile not in GPU_EXECUTION_PROFILES:
            raise ValueError(f"compute.gpu_execution_profile must be one of: {', '.join(GPU_EXECUTION_PROFILES)}")
        tensor_core_policy = str(payload.get("tensor_core_policy", "disabled")).strip().lower()
        if tensor_core_policy not in TENSOR_CORE_POLICIES:
            raise ValueError(f"compute.tensor_core_policy must be one of: {', '.join(TENSOR_CORE_POLICIES)}")
        gpu_batch_candidates = int(payload.get("gpu_batch_candidates", 512))
        if gpu_batch_candidates < 1 or gpu_batch_candidates > 1_000_000:
            raise ValueError("compute.gpu_batch_candidates must be between 1 and 1000000")
        gpu_memory_fraction_limit = float(payload.get("gpu_memory_fraction_limit", 0.70))
        if gpu_memory_fraction_limit <= 0.0 or gpu_memory_fraction_limit > 1.0:
            raise ValueError("compute.gpu_memory_fraction_limit must be greater than 0 and at most 1")
        gpu_validation_sample_rate = _bounded_rate(
            payload.get("gpu_validation_sample_rate", 0.02),
            field_name="compute.gpu_validation_sample_rate",
        )
        return cls(
            cpu_threads=cpu_threads,
            gpu_acceleration=gpu_acceleration,
            gpu_device_class=str(payload.get("gpu_device_class", "nvidia_50_series")),
            gpu_required=bool(payload.get("gpu_required", gpu_acceleration == "require_nvidia_cuda_backend")),
            gpu_execution_profile=gpu_execution_profile,
            tensor_core_policy=tensor_core_policy,
            gpu_batch_candidates=gpu_batch_candidates,
            gpu_memory_fraction_limit=gpu_memory_fraction_limit,
            gpu_validation_sample_rate=gpu_validation_sample_rate,
        )

    def to_payload(self, *, include_r97_defaults: bool = False) -> dict[str, Any]:
        payload = {
            "cpu_threads": int(self.cpu_threads),
            "gpu_acceleration": self.gpu_acceleration,
            "gpu_device_class": self.gpu_device_class,
            "gpu_required": bool(self.gpu_required),
        }
        r97_payload = {
            "gpu_execution_profile": self.gpu_execution_profile,
            "tensor_core_policy": self.tensor_core_policy,
            "gpu_batch_candidates": int(self.gpu_batch_candidates),
            "gpu_memory_fraction_limit": float(self.gpu_memory_fraction_limit),
            "gpu_validation_sample_rate": float(self.gpu_validation_sample_rate),
        }
        if include_r97_defaults or r97_payload != {
            "gpu_execution_profile": "fastest_exact",
            "tensor_core_policy": "disabled",
            "gpu_batch_candidates": 512,
            "gpu_memory_fraction_limit": 0.70,
            "gpu_validation_sample_rate": 0.02,
        }:
            payload.update(r97_payload)
        return payload


@dataclass(frozen=True, slots=True)
class CycleExitSpec:
    exit_policies: tuple[Mapping[str, Any], ...] = field(default_factory=lambda: DEFAULT_EXIT_POLICIES)

    @classmethod
    def from_payload(cls, payload: Any) -> "CycleExitSpec":
        if isinstance(payload, Mapping) and "exit_policies" in payload:
            raw_policies = payload.get("exit_policies")
        else:
            raw_policies = payload if payload is not None else DEFAULT_EXIT_POLICIES
        if isinstance(raw_policies, str) or isinstance(raw_policies, Mapping):
            raw_policies = (raw_policies,)
        policies = tuple(_exit_policy_payload(item) for item in raw_policies)
        if not policies:
            raise ValueError("at least one exit policy is required")
        return cls(exit_policies=policies)

    def to_payload(self) -> dict[str, Any]:
        return {"exit_policies": [_json_safe_mapping(policy) for policy in self.exit_policies]}


@dataclass(frozen=True, slots=True)
class HistoricalResearchCycleSpec:
    cycle_id: str
    symbol: str
    holding_windows: tuple[str, ...]
    data: CycleDataSpec
    features: CycleFeatureSpec
    strategies: tuple[str, ...]
    validation: CycleValidationSpec
    optimizer: CycleOptimizerSpec
    compute: CycleComputeSpec
    exits: CycleExitSpec
    backtest_backend: str = "auto"
    output_dir: Path | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, spec_path: Path) -> "HistoricalResearchCycleSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("historical research cycle spec must be a JSON object")
        cycle_id = str(payload.get("cycle_id") or "").strip()
        if not cycle_id:
            raise ValueError("cycle_id is required")
        holding_windows = tuple(str(item) for item in payload.get("holding_windows", REQUIRED_HOLDING_WINDOWS))
        if not holding_windows:
            raise ValueError("at least one holding window is required")
        unsupported = sorted(set(holding_windows) - set(REQUIRED_HOLDING_WINDOWS))
        if unsupported:
            raise ValueError(f"unsupported holding windows: {', '.join(unsupported)}")
        strategies = tuple(str(item) for item in payload.get("strategies", DEFAULT_STRATEGIES))
        if not strategies:
            raise ValueError("at least one strategy is required")
        backtest_backend = str(payload.get("backtest_backend", "auto")).strip().lower()
        if backtest_backend not in BACKTEST_BACKENDS:
            raise ValueError(f"backtest_backend must be one of: {', '.join(BACKTEST_BACKENDS)}")
        base_path = spec_path.parent
        return cls(
            cycle_id=cycle_id,
            symbol=str(payload.get("symbol", "BTCUSDT")).upper(),
            holding_windows=holding_windows,
            data=CycleDataSpec.from_payload(payload.get("data"), base_path=base_path),
            features=CycleFeatureSpec.from_payload(payload.get("features"), base_path=base_path),
            strategies=strategies,
            validation=CycleValidationSpec.from_payload(payload.get("validation")),
            optimizer=CycleOptimizerSpec.from_payload(payload.get("optimizer")),
            compute=CycleComputeSpec.from_payload(payload.get("compute")),
            exits=CycleExitSpec.from_payload(payload.get("exit_policies") or payload.get("exits")),
            backtest_backend=backtest_backend,
            output_dir=(
                _resolve_path(payload["output_dir"], base_path=base_path)
                if payload.get("output_dir")
                else None
            ),
        )

    @classmethod
    def from_path(cls, path: Path) -> "HistoricalResearchCycleSpec":
        spec_path = Path(path).expanduser()
        payload = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        return cls.from_payload(payload, spec_path=spec_path)

    def to_payload(self) -> dict[str, Any]:
        return {
            "spec_version": RESEARCH_CYCLE_SPEC_VERSION,
            "cycle_id": self.cycle_id,
            "symbol": self.symbol,
            "holding_windows": list(self.holding_windows),
            "data": self.data.to_payload(),
            "features": self.features.to_payload(),
            "strategies": list(self.strategies),
            "validation": self.validation.to_payload(),
            "optimizer": self.optimizer.to_payload(),
            "compute": self.compute.to_payload(include_r97_defaults=True),
            "exits": self.exits.to_payload(),
            "backtest_backend": self.backtest_backend,
            "output_dir": str(self.output_dir) if self.output_dir is not None else None,
        }


def _resolve_path(value: Any, *, base_path: Path) -> Path:
    candidate = Path(str(value)).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_path / candidate).resolve()


def _search_space_payload(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("optimizer.search_spaces entries must be JSON objects")
    return dict(value)


def _validation_split_modes(value: Any) -> tuple[str, ...]:
    raw_modes = value if value is not None else ("purged_embargoed_walk_forward",)
    if isinstance(raw_modes, str):
        raw_modes = (raw_modes,)
    modes = tuple(dict.fromkeys(str(item).strip() for item in raw_modes if str(item).strip()))
    if not modes:
        raise ValueError("validation.split_modes requires at least one split mode")
    unsupported = sorted(set(modes) - set(SUPPORTED_VALIDATION_SPLIT_MODES))
    if unsupported:
        raise ValueError(f"unsupported validation split_modes: {', '.join(unsupported)}")
    return modes


def _optional_positive_int(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    result = int(value)
    if result <= 0:
        raise ValueError(f"{field_name} must be positive")
    return result


def _bounded_rate(value: Any, *, field_name: str) -> float:
    result = float(value)
    if result < 0.0 or result > 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return result


def _shifted_anchor_offsets(value: Any) -> tuple[int, ...]:
    raw_offsets = value if value is not None else (1,)
    if isinstance(raw_offsets, int):
        raw_offsets = (raw_offsets,)
    offsets = tuple(dict.fromkeys(int(item) for item in raw_offsets))
    if not offsets:
        raise ValueError("validation.shifted_anchor_offsets requires at least one offset")
    if any(offset <= 0 for offset in offsets):
        raise ValueError("validation.shifted_anchor_offsets entries must be positive")
    return offsets


def _exit_policy_payload(value: Any) -> Mapping[str, Any]:
    if isinstance(value, str):
        raw = {"exit_policy_id": value}
    elif isinstance(value, Mapping):
        raw = dict(value)
    else:
        raise ValueError("exit policy entries must be strings or JSON objects")
    exit_policy_id = str(raw.get("exit_policy_id") or raw.get("policy_id") or "").strip()
    if not exit_policy_id:
        raise ValueError("exit_policy_id is required")
    if exit_policy_id not in SUPPORTED_RESEARCH_EXIT_POLICIES:
        raise ValueError(f"unsupported exit_policy_id in research cycle: {exit_policy_id}")
    params = raw.get("exit_policy_params") or raw.get("params") or {}
    if not isinstance(params, Mapping):
        raise ValueError("exit_policy_params must be a JSON object")
    params_payload = _json_safe_mapping(params)
    target_return = raw.get("target_return", params_payload.get("target_return"))
    stop_return = raw.get("stop_return", params_payload.get("stop_return"))
    if exit_policy_id in {"triple_barrier", "triple_barrier_atr"}:
        target_return = _positive_float(target_return, field_name=f"{exit_policy_id}.target_return")
        stop_return = _positive_float(stop_return, field_name=f"{exit_policy_id}.stop_return")
        params_payload.setdefault("target_return", target_return)
        params_payload.setdefault("stop_return", stop_return)
    return {
        "exit_policy_id": exit_policy_id,
        "exit_policy_params": params_payload,
        "target_return": target_return,
        "stop_return": stop_return,
        "exit_policy_source": str(raw.get("exit_policy_source") or raw.get("source") or "configured_exit_policy"),
    }


def _positive_float(value: Any, *, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is required")
    result = float(value)
    if result <= 0.0:
        raise ValueError(f"{field_name} must be positive")
    return result


def _json_safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    raw_parameters = payload.get("parameters") or payload.get("parameter_space")
    if isinstance(raw_parameters, Mapping):
        payload["parameters"] = {
            str(key): list(item) if isinstance(item, tuple) else item
            for key, item in raw_parameters.items()
        }
        payload.pop("parameter_space", None)
    return payload
