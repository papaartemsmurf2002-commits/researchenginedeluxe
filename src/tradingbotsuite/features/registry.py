from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence

FEATURE_MANIFEST_VERSION = "feature-manifest-v1"
FEATURE_SET_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    column: str
    dtype: str
    description: str
    nullable: bool = True
    availability_column: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FeaturePack:
    pack_id: str
    version: str
    input_families: tuple[str, ...]
    feature_specs: tuple[FeatureSpec, ...]
    point_in_time_safe: bool
    fit_scope: str
    imputation_policy: str
    optional: bool = False
    leakage_risks: tuple[str, ...] = ()

    @property
    def feature_columns(self) -> tuple[str, ...]:
        return tuple(spec.column for spec in self.feature_specs)

    @property
    def availability_columns(self) -> tuple[str, ...]:
        return tuple(
            spec.availability_column or f"missing_{spec.column}"
            for spec in self.feature_specs
        )

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["feature_columns"] = list(self.feature_columns)
        payload["availability_columns"] = list(self.availability_columns)
        return payload


@dataclass(frozen=True, slots=True)
class FeatureAvailabilityReport:
    row_count: int
    feature_columns: tuple[str, ...]
    availability_columns: tuple[str, ...]
    missing_counts: Mapping[str, int]
    missing_rates: Mapping[str, float]
    missing_context_columns: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "row_count": int(self.row_count),
            "feature_columns": list(self.feature_columns),
            "availability_columns": list(self.availability_columns),
            "missing_counts": {key: int(value) for key, value in sorted(self.missing_counts.items())},
            "missing_rates": {key: float(value) for key, value in sorted(self.missing_rates.items())},
            "missing_context_columns": list(self.missing_context_columns),
        }


@dataclass(frozen=True, slots=True)
class FeatureManifest:
    manifest_version: str
    feature_set_id: str
    feature_set_version: str
    feature_packs: tuple[str, ...]
    input_families: tuple[str, ...]
    feature_columns: tuple[str, ...]
    availability_columns: tuple[str, ...]
    point_in_time_safe: bool
    max_feature_age_ms: int | None
    fit_scope: str
    imputation_policy: str
    leakage_risks: tuple[str, ...]
    tests: tuple[str, ...]
    manifest_sha256: str

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "manifest_version": self.manifest_version,
            "feature_set_id": self.feature_set_id,
            "feature_set_version": self.feature_set_version,
            "feature_packs": list(self.feature_packs),
            "input_families": list(self.input_families),
            "feature_columns": list(self.feature_columns),
            "availability_columns": list(self.availability_columns),
            "point_in_time_safe": bool(self.point_in_time_safe),
            "max_feature_age_ms": self.max_feature_age_ms,
            "fit_scope": self.fit_scope,
            "imputation_policy": self.imputation_policy,
            "leakage_risks": list(self.leakage_risks),
            "tests": list(self.tests),
        }
        if include_hash:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


@dataclass(frozen=True, slots=True)
class FeatureManifestValidation:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def feature_pack_registry() -> dict[str, FeaturePack]:
    return {pack.pack_id: pack for pack in _FEATURE_PACKS}


def feature_set_presets() -> dict[str, tuple[str, ...]]:
    return {
        "features_price_trend_vol": ("price_path_v1", "trend_chop_v1", "volatility_v1", "calendar_v1"),
        "features_price_trend_vol_wt3d": (
            "price_path_v1",
            "trend_chop_v1",
            "volatility_v1",
            "wt3d_v1",
            "calendar_v1",
        ),
        "features_perp_context_only": ("perp_context_v1",),
        "features_price_perp_micro_no_wt": (
            "price_path_v1",
            "trend_chop_v1",
            "volatility_v1",
            "perp_context_v1",
            "microstructure_context_v1",
            "calendar_v1",
        ),
        "features_full_context_wt3d": (
            "price_path_v1",
            "trend_chop_v1",
            "volatility_v1",
            "perp_context_v1",
            "microstructure_context_v1",
            "wt3d_v1",
            "cross_asset_v1",
            "calendar_v1",
        ),
        "features_full_context_no_wt": (
            "price_path_v1",
            "trend_chop_v1",
            "volatility_v1",
            "perp_context_v1",
            "microstructure_context_v1",
            "cross_asset_v1",
            "calendar_v1",
        ),
    }


def build_feature_manifest(
    *,
    feature_set_id: str,
    feature_packs: Sequence[str | FeaturePack],
    max_feature_age_ms: int | None = None,
    tests: Sequence[str] = (),
) -> FeatureManifest:
    registry = feature_pack_registry()
    packs = tuple(registry[item] if isinstance(item, str) else item for item in feature_packs)
    if not packs:
        raise ValueError("feature_packs must contain at least one pack")

    pack_ids = tuple(pack.pack_id for pack in packs)
    if len(set(pack_ids)) != len(pack_ids):
        raise ValueError("feature_packs must not contain duplicates")
    feature_columns = _unique(column for pack in packs for column in pack.feature_columns)
    availability_columns = _unique(column for pack in packs for column in pack.availability_columns)
    input_families = _unique(family for pack in packs for family in pack.input_families)
    leakage_risks = _unique(risk for pack in packs for risk in pack.leakage_risks)
    fit_scopes = {pack.fit_scope for pack in packs}
    fit_scope = "train_only" if "train_only" in fit_scopes else "stateless"
    point_in_time_safe = all(pack.point_in_time_safe for pack in packs)
    imputation_policy = "explicit_missingness_plus_train_only_neutral"

    payload_without_hash = {
        "manifest_version": FEATURE_MANIFEST_VERSION,
        "feature_set_id": str(feature_set_id),
        "feature_set_version": FEATURE_SET_VERSION,
        "feature_packs": list(pack_ids),
        "input_families": list(input_families),
        "feature_columns": list(feature_columns),
        "availability_columns": list(availability_columns),
        "point_in_time_safe": bool(point_in_time_safe),
        "max_feature_age_ms": max_feature_age_ms,
        "fit_scope": fit_scope,
        "imputation_policy": imputation_policy,
        "leakage_risks": list(leakage_risks),
        "tests": list(tests),
    }
    manifest_hash = stable_feature_hash(payload_without_hash)
    return FeatureManifest(
        manifest_version=FEATURE_MANIFEST_VERSION,
        feature_set_id=str(feature_set_id),
        feature_set_version=FEATURE_SET_VERSION,
        feature_packs=pack_ids,
        input_families=input_families,
        feature_columns=feature_columns,
        availability_columns=availability_columns,
        point_in_time_safe=point_in_time_safe,
        max_feature_age_ms=max_feature_age_ms,
        fit_scope=fit_scope,
        imputation_policy=imputation_policy,
        leakage_risks=leakage_risks,
        tests=tuple(str(test) for test in tests),
        manifest_sha256=manifest_hash,
    )


def manifest_from_preset(preset_id: str, *, tests: Sequence[str] = ()) -> FeatureManifest:
    presets = feature_set_presets()
    if preset_id not in presets:
        raise ValueError(f"unknown_feature_preset:{preset_id}")
    return build_feature_manifest(
        feature_set_id=preset_id,
        feature_packs=presets[preset_id],
        tests=tests,
    )


def validate_feature_manifest(payload: FeatureManifest | Mapping[str, Any]) -> FeatureManifestValidation:
    manifest = payload.to_payload() if isinstance(payload, FeatureManifest) else dict(payload)
    errors: list[str] = []
    warnings: list[str] = []
    required = {
        "manifest_version",
        "feature_set_id",
        "feature_set_version",
        "feature_packs",
        "input_families",
        "feature_columns",
        "availability_columns",
        "point_in_time_safe",
        "fit_scope",
        "imputation_policy",
        "leakage_risks",
        "tests",
        "manifest_sha256",
    }
    missing = sorted(required - set(manifest))
    if missing:
        errors.append(f"missing_manifest_fields:{','.join(missing)}")
    if manifest.get("manifest_version") != FEATURE_MANIFEST_VERSION:
        errors.append("unsupported_manifest_version")
    feature_columns = tuple(str(column) for column in manifest.get("feature_columns", ()))
    availability_columns = tuple(str(column) for column in manifest.get("availability_columns", ()))
    if not feature_columns:
        errors.append("feature_columns_empty")
    if len(set(feature_columns)) != len(feature_columns):
        errors.append("duplicate_feature_columns")
    if len(set(availability_columns)) != len(availability_columns):
        errors.append("duplicate_availability_columns")
    if not bool(manifest.get("point_in_time_safe")):
        errors.append("point_in_time_safe_must_be_true")
    if manifest.get("fit_scope") not in {"stateless", "train_only"}:
        errors.append("invalid_fit_scope")
    if "train_only" not in str(manifest.get("imputation_policy", "")):
        warnings.append("imputation_policy_does_not_reference_train_only")
    expected_hash = stable_feature_hash({key: value for key, value in manifest.items() if key != "manifest_sha256"})
    if manifest.get("manifest_sha256") != expected_hash:
        errors.append("manifest_sha256_mismatch")
    return FeatureManifestValidation(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))


def stable_feature_hash(payload: Mapping[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = str(value)
        if key not in seen:
            seen.add(key)
            result.append(key)
    return tuple(result)


def _specs(columns: Sequence[str], description_prefix: str) -> tuple[FeatureSpec, ...]:
    return tuple(
        FeatureSpec(
            column=column,
            dtype="float64",
            description=f"{description_prefix}: {column}",
            nullable=True,
            availability_column=f"missing_{column}",
        )
        for column in columns
    )


PRICE_PATH_COLUMNS = (
    "log_return_1",
    "log_return_4",
    "log_return_16",
    "momentum_4",
    "momentum_16",
    "path_zscore_20",
    "trend_slope_20",
)
TREND_CHOP_COLUMNS = (
    "efficiency_ratio",
    "choppiness",
    "directional_slope_atr",
    "directional_di_spread",
    "range_width",
    "hurst_proxy",
    "adx_proxy",
)
VOLATILITY_COLUMNS = (
    "atr",
    "realized_volatility",
    "atr_percentile",
    "volatility_shock_zscore",
    "vol_of_vol",
)
PERP_CONTEXT_COLUMNS = (
    "basis_bps",
    "funding_rate",
    "funding_rate_change",
    "open_interest_change_pct",
    "premium_basis_rate",
)
MICROSTRUCTURE_COLUMNS = (
    "primary_signed_imbalance_ratio",
    "primary_sqrt_signed_imbalance_ratio",
    "top_of_book_imbalance",
    "queue_imbalance_l5",
    "spread_bps",
)
WT3D_COLUMNS = (
    "wt3d_fast",
    "wt3d_normal",
    "wt3d_slow",
    "wt3d_fast_normal_spread",
    "wt3d_normal_slow_spread",
    "wt3d_slope",
    "wt3d_acceleration",
    "wt3d_bars_since_cross",
    "wt3d_reversal_intensity",
    "wt3d_mtf_agreement",
)
CROSS_ASSET_COLUMNS = (
    "btc_eth_lead_lag_corr_24",
    "eth_btc_relative_return_24",
)
CALENDAR_COLUMNS = (
    "session_hour_sin",
    "session_hour_cos",
    "session_weekday",
    "hours_to_next_funding",
    "weekend_session",
)

_FEATURE_PACKS = (
    FeaturePack(
        pack_id="price_path_v1",
        version="v1",
        input_families=("kline",),
        feature_specs=_specs(PRICE_PATH_COLUMNS, "Backward-only price path"),
        point_in_time_safe=True,
        fit_scope="stateless",
        imputation_policy="explicit_missingness",
    ),
    FeaturePack(
        pack_id="trend_chop_v1",
        version="v1",
        input_families=("kline",),
        feature_specs=_specs(TREND_CHOP_COLUMNS, "Backward-only trend and chop"),
        point_in_time_safe=True,
        fit_scope="stateless",
        imputation_policy="explicit_missingness",
    ),
    FeaturePack(
        pack_id="volatility_v1",
        version="v1",
        input_families=("kline",),
        feature_specs=_specs(VOLATILITY_COLUMNS, "Backward-only volatility"),
        point_in_time_safe=True,
        fit_scope="stateless",
        imputation_policy="explicit_missingness",
    ),
    FeaturePack(
        pack_id="perp_context_v1",
        version="v1",
        input_families=("funding_rate", "open_interest", "premium_index"),
        feature_specs=_specs(PERP_CONTEXT_COLUMNS, "As-of perpetual context"),
        point_in_time_safe=True,
        fit_scope="stateless",
        imputation_policy="explicit_missingness",
        optional=True,
    ),
    FeaturePack(
        pack_id="microstructure_context_v1",
        version="v1",
        input_families=("trade", "agg_trade", "book_ticker", "depth_snapshot"),
        feature_specs=_specs(MICROSTRUCTURE_COLUMNS, "As-of microstructure context"),
        point_in_time_safe=True,
        fit_scope="stateless",
        imputation_policy="explicit_missingness",
        optional=True,
    ),
    FeaturePack(
        pack_id="wt3d_v1",
        version="v1",
        input_families=("kline",),
        feature_specs=_specs(WT3D_COLUMNS, "Backward-only WT3D oscillator"),
        point_in_time_safe=True,
        fit_scope="stateless",
        imputation_policy="explicit_missingness",
        optional=True,
        leakage_risks=("WT-style oscillators must not use future pivots or undelayed divergences.",),
    ),
    FeaturePack(
        pack_id="cross_asset_v1",
        version="v1",
        input_families=("kline",),
        feature_specs=_specs(CROSS_ASSET_COLUMNS, "Backward-only BTC/ETH relative context"),
        point_in_time_safe=True,
        fit_scope="stateless",
        imputation_policy="explicit_missingness",
        optional=True,
    ),
    FeaturePack(
        pack_id="calendar_v1",
        version="v1",
        input_families=("kline",),
        feature_specs=_specs(CALENDAR_COLUMNS, "Calendar and funding-window context"),
        point_in_time_safe=True,
        fit_scope="stateless",
        imputation_policy="explicit_missingness",
    ),
)
