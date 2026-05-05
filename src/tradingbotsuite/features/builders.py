from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from tradingbotsuite.features.packs import FeatureFrameResult, build_feature_frame
from tradingbotsuite.features.registry import feature_pack_registry, feature_set_presets


FEATURE_BUILDER_VERSION = "research-feature-builder-v1"
DEFAULT_INTERVAL_MS = 900_000
FEATURE_MANIFEST_TESTS = (
    "tests/contracts/test_feature_contracts.py",
    "tests/tradingbotsuite/test_feature_alignment.py",
)


@dataclass(frozen=True, slots=True)
class BuiltFeatureSet:
    feature_set_id: str
    result: FeatureFrameResult
    source_column_mapping: Mapping[str, str]
    builder_version: str = FEATURE_BUILDER_VERSION

    def manifest_payload(self) -> dict[str, Any]:
        return {
            "builder_version": self.builder_version,
            "feature_set_id": self.feature_set_id,
            "feature_manifest": self.result.manifest.to_payload(),
            "availability_report": self.result.availability_report.to_payload(),
            "completed_bar_validation": {
                "valid": self.result.completed_bar_validation.valid,
                "errors": list(self.result.completed_bar_validation.errors),
                "quality_flags": list(self.result.completed_bar_validation.quality_flags),
                "row_count": self.result.completed_bar_validation.row_count,
            },
            "source_column_mapping": dict(self.source_column_mapping),
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }


@dataclass(frozen=True, slots=True)
class MaterializedFeatureSet:
    feature_set_id: str
    frame: pd.DataFrame
    built: BuiltFeatureSet
    materialization_scope: str = "registered_features_merged_with_execution_context"

    @property
    def feature_columns(self) -> tuple[str, ...]:
        return self.built.result.manifest.feature_columns

    @property
    def availability_columns(self) -> tuple[str, ...]:
        return self.built.result.manifest.availability_columns

    def manifest_payload(self) -> dict[str, Any]:
        return {
            **self.built.manifest_payload(),
            "materialization_scope": self.materialization_scope,
            "materialized_columns": list(self.frame.columns),
            "materialized_row_count": int(len(self.frame)),
        }


@dataclass(frozen=True, slots=True)
class FixtureFamilyMaterializationResult:
    frame: pd.DataFrame
    evidence: Mapping[str, Any]
    context_sha256: str


FIXTURE_FAMILY_CONTEXT_MATERIALIZATION_VERSION = "fixture-family-context-materialization-v1"
FIXTURE_CONTEXT_FAMILY_ORDER = ("funding_rate", "premium_index", "open_interest", "agg_trade")
FIXTURE_CONTEXT_COLUMN_ALIASES = {
    "funding_rate": {
        "funding_rate": ("funding_rate", "last_funding_rate", "rate", "value"),
        "funding_rate_change": ("funding_rate_change", "rate_change"),
    },
    "premium_index": {
        "premium_basis_rate": ("premium_basis_rate", "basis_rate", "premium_index", "value"),
        "basis_bps": ("basis_bps",),
        "premium_basis_abs": ("premium_basis_abs", "basis_abs", "basis"),
        "premium_close": ("premium_close", "premium_index"),
        "mark_price": ("mark_price",),
        "index_price": ("index_price",),
    },
    "open_interest": {
        "open_interest": ("open_interest", "sum_open_interest", "oi", "value"),
        "open_interest_change": ("open_interest_change", "sum_open_interest_change"),
        "open_interest_change_pct": ("open_interest_change_pct", "open_interest_pct_change"),
        "open_interest_value": ("open_interest_value", "open_interest_value_usd", "notional"),
    },
    "agg_trade": {
        "quote_volume": ("quote_volume", "notional", "quote_quantity"),
        "taker_buy_quote_volume": ("taker_buy_quote_volume", "buy_quote_volume"),
        "sell_quote_volume": ("sell_quote_volume", "sell_quantity"),
        "primary_signed_imbalance_ratio": (
            "primary_signed_imbalance_ratio",
            "signed_imbalance_ratio",
            "signed_ratio",
        ),
        "primary_sqrt_signed_imbalance_ratio": ("primary_sqrt_signed_imbalance_ratio",),
        "top_of_book_imbalance": ("top_of_book_imbalance",),
        "spread_bps": ("spread_bps",),
    },
}


def materialize_fixture_family_context(
    frame: pd.DataFrame,
    *,
    optional_context_families: Mapping[str, Mapping[str, Any]] | None,
) -> FixtureFamilyMaterializationResult:
    """Join validated fixture-pack context families onto cycle bars using backward as-of semantics."""

    families = {
        str(family): dict(payload)
        for family, payload in dict(optional_context_families or {}).items()
        if str(family) in FIXTURE_CONTEXT_FAMILY_ORDER
    }
    result = frame.copy()
    time_column = _first_existing(result, ("bar_time_ms", "signal_bar_time_ms", "time_ms"))
    family_records: list[dict[str, Any]] = []
    joined_columns: list[str] = []
    joined_families: list[str] = []
    for family in FIXTURE_CONTEXT_FAMILY_ORDER:
        payload = families.get(family)
        if payload is None:
            continue
        if time_column is None:
            raise ValueError("fixture_context_cycle_time_column_required")
        result, record = _materialize_one_fixture_family(
            result,
            family=family,
            family_payload=payload,
            cycle_time_column=time_column,
        )
        family_records.append(record)
        if record["joined"]:
            joined_families.append(family)
            for column in record["output_columns"]:
                if column not in joined_columns:
                    joined_columns.append(column)

    hash_payload = {
        "materialization_version": FIXTURE_FAMILY_CONTEXT_MATERIALIZATION_VERSION,
        "family_records": family_records,
        "joined_columns": joined_columns,
    }
    context_sha256 = _stable_hash(hash_payload)
    evidence = {
        "materialization_version": FIXTURE_FAMILY_CONTEXT_MATERIALIZATION_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "asof_direction": "backward",
        "lookahead_policy": "family_event_time_ms_lte_cycle_bar_time_ms",
        "cycle_time_column": time_column,
        "source_row_count": int(len(frame)),
        "family_count": int(len(family_records)),
        "families_requested": list(families.keys()),
        "joined_families": joined_families,
        "joined_columns": joined_columns,
        "family_records": family_records,
        "fixture_family_context_sha256": context_sha256,
    }
    return FixtureFamilyMaterializationResult(
        frame=result,
        evidence=evidence,
        context_sha256=context_sha256,
    )


def build_registered_feature_set(
    frame: pd.DataFrame,
    *,
    feature_set_id: str,
    interval_ms: int = DEFAULT_INTERVAL_MS,
    require_continuous: bool = True,
) -> BuiltFeatureSet:
    presets = feature_set_presets()
    if feature_set_id not in presets:
        raise ValueError(f"unknown_feature_set_id:{feature_set_id}")
    bars, mapping = canonicalize_bar_frame(frame)
    result = build_feature_frame(
        bars,
        feature_set_id=feature_set_id,
        feature_packs=presets[feature_set_id],
        interval_ms=interval_ms,
        bar_time_column="bar_time_ms",
        price_column="close",
        require_continuous=require_continuous,
    )
    return BuiltFeatureSet(
        feature_set_id=feature_set_id,
        result=result,
        source_column_mapping=mapping,
    )


def materialize_registered_feature_set(
    frame: pd.DataFrame,
    *,
    feature_set_id: str,
    interval_ms: int = DEFAULT_INTERVAL_MS,
    require_continuous: bool = True,
) -> MaterializedFeatureSet:
    built = build_registered_feature_set(
        frame,
        feature_set_id=feature_set_id,
        interval_ms=interval_ms,
        require_continuous=require_continuous,
    )
    base, _ = canonicalize_bar_frame(frame)
    registered_columns = set(registered_feature_columns()) | {"feature_time_ms"}
    base = base.drop(columns=[column for column in registered_columns if column in base.columns], errors="ignore")
    feature_frame = built.result.frame.loc[
        :,
        [
            "bar_time_ms",
            "feature_time_ms",
            *built.result.manifest.feature_columns,
            *built.result.manifest.availability_columns,
        ],
    ].copy()
    materialized = base.merge(feature_frame, on="bar_time_ms", how="left", validate="one_to_one")
    return MaterializedFeatureSet(
        feature_set_id=feature_set_id,
        frame=materialized.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True),
        built=built,
    )


def registered_feature_columns() -> tuple[str, ...]:
    columns = [
        column
        for pack in feature_pack_registry().values()
        for column in (*pack.feature_columns, *pack.availability_columns)
    ]
    return tuple(dict.fromkeys(columns))


def canonicalize_bar_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    mapping = {
        "bar_time_ms": _first_existing(frame, ("bar_time_ms", "signal_bar_time_ms", "time_ms")),
        "open": _first_existing(frame, ("open", "signal_bar_open", "entry_price")),
        "high": _first_existing(frame, ("high", "signal_bar_high", "entry_price")),
        "low": _first_existing(frame, ("low", "signal_bar_low", "entry_price")),
        "close": _first_existing(frame, ("close", "signal_bar_close", "entry_price")),
        "volume": _first_existing(frame, ("volume", "signal_bar_volume")),
    }
    missing_required = [key for key in ("bar_time_ms", "open", "high", "low", "close") if mapping[key] is None]
    if missing_required:
        raise ValueError(f"missing_bar_columns:{','.join(missing_required)}")
    bars = pd.DataFrame(
        {
            target: pd.to_numeric(frame[source], errors="coerce")
            for target, source in mapping.items()
            if source is not None
        }
    )
    if "volume" not in bars.columns:
        bars["volume"] = 0.0
    mapped_columns = set(mapping.values())
    passthrough_columns = [
        column
        for column in frame.columns
        if column not in bars.columns and column not in mapped_columns
    ]
    if passthrough_columns:
        bars = pd.concat([bars, frame.loc[:, passthrough_columns].copy()], axis=1)
    return bars.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True), {
        key: str(value)
        for key, value in mapping.items()
        if value is not None
    }


def _first_existing(frame: pd.DataFrame, columns: tuple[str, ...]) -> str | None:
    for column in columns:
        if column in frame.columns:
            return column
    return None


def _materialize_one_fixture_family(
    frame: pd.DataFrame,
    *,
    family: str,
    family_payload: Mapping[str, Any],
    cycle_time_column: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = Path(str(family_payload.get("path") or "")).expanduser()
    if not path.exists():
        raise ValueError(f"fixture_context_family_path_missing:{family}:{path}")
    family_frame = pd.read_parquet(path)
    event_time_field = str(family_payload.get("event_time_field") or "event_time_ms")
    missing_required = sorted({"symbol", event_time_field} - set(str(column) for column in family_frame.columns))
    if missing_required:
        raise ValueError(f"fixture_context_family_missing_columns:{family}:{','.join(missing_required)}")
    family_frame = family_frame.copy()
    family_frame["__fixture_family_symbol"] = family_frame["symbol"].astype(str)
    family_frame["__fixture_family_event_time_ms"] = pd.to_numeric(family_frame[event_time_field], errors="coerce")
    if family_frame["__fixture_family_event_time_ms"].isna().any():
        raise ValueError(f"fixture_context_family_invalid_event_time:{family}")
    duplicate_mask = family_frame.duplicated(["__fixture_family_symbol", "__fixture_family_event_time_ms"], keep=False)
    if duplicate_mask.any():
        raise ValueError(f"fixture_context_family_duplicate_events:{family}")
    family_frame = family_frame.sort_values(
        ["__fixture_family_symbol", "__fixture_family_event_time_ms"],
        kind="mergesort",
    ).reset_index(drop=True)
    context_columns = _derive_family_context_columns(family, family_frame)
    output_columns = [column for column in FIXTURE_CONTEXT_COLUMN_ALIASES.get(family, {}) if column in context_columns]
    if not output_columns:
        if bool(family_payload.get("required", False)):
            raise ValueError(f"fixture_context_family_no_supported_columns:{family}")
        return frame, _family_materialization_record(
            family=family,
            family_payload=family_payload,
            event_time_field=event_time_field,
            input_columns=list(family_frame.columns),
            output_columns=[],
            joined=False,
            skipped_reason="no_supported_context_columns",
            source_row_count=len(family_frame),
            matched_row_count=0,
            unmatched_row_count=len(frame),
            null_rates={},
        )

    right = pd.DataFrame(
        {
            "__fixture_family_symbol": family_frame["__fixture_family_symbol"],
            "__fixture_family_event_time_ms": family_frame["__fixture_family_event_time_ms"],
            **{column: context_columns[column] for column in output_columns},
        }
    ).sort_values("__fixture_family_event_time_ms", kind="mergesort")
    left = pd.DataFrame(
        {
            "__fixture_original_index": frame.index,
            "__fixture_cycle_symbol": frame["symbol"].astype(str),
            "__fixture_cycle_time_ms": pd.to_numeric(frame[cycle_time_column], errors="coerce"),
        }
    )
    if left["__fixture_cycle_time_ms"].isna().any():
        raise ValueError("fixture_context_cycle_time_invalid")

    joined_values = pd.DataFrame(index=frame.index)
    for column in output_columns:
        joined_values[column] = np.nan
    matched_event_times = pd.Series(np.nan, index=frame.index, dtype="float64")
    for symbol, left_group in left.groupby("__fixture_cycle_symbol", sort=False):
        right_group = right.loc[right["__fixture_family_symbol"] == symbol].drop(columns=["__fixture_family_symbol"])
        if right_group.empty:
            continue
        merged = pd.merge_asof(
            left_group.sort_values("__fixture_cycle_time_ms", kind="mergesort"),
            right_group.sort_values("__fixture_family_event_time_ms", kind="mergesort"),
            left_on="__fixture_cycle_time_ms",
            right_on="__fixture_family_event_time_ms",
            direction="backward",
            allow_exact_matches=True,
        ).set_index("__fixture_original_index")
        matched_event_times.loc[merged.index] = pd.to_numeric(merged["__fixture_family_event_time_ms"], errors="coerce")
        for column in output_columns:
            joined_values.loc[merged.index, column] = pd.to_numeric(merged[column], errors="coerce")

    result = frame.copy()
    for column in output_columns:
        result[column] = pd.to_numeric(joined_values[column], errors="coerce")
    matched_row_count = int(matched_event_times.notna().sum())
    null_rates = {
        column: float(result[column].isna().mean()) if len(result) else 0.0
        for column in output_columns
    }
    record = _family_materialization_record(
        family=family,
        family_payload=family_payload,
        event_time_field=event_time_field,
        input_columns=list(family_frame.columns),
        output_columns=output_columns,
        joined=True,
        skipped_reason="",
        source_row_count=len(family_frame),
        matched_row_count=matched_row_count,
        unmatched_row_count=int(len(frame) - matched_row_count),
        null_rates=null_rates,
    )
    return result, record


def _derive_family_context_columns(family: str, frame: pd.DataFrame) -> dict[str, pd.Series]:
    columns: dict[str, pd.Series] = {}
    for output_column, aliases in FIXTURE_CONTEXT_COLUMN_ALIASES.get(family, {}).items():
        series = _first_numeric_series(frame, aliases)
        if series is not None:
            columns[output_column] = series
    if family == "funding_rate" and "funding_rate" in columns and "funding_rate_change" not in columns:
        columns["funding_rate_change"] = columns["funding_rate"].groupby(frame["__fixture_family_symbol"]).diff()
    if family == "premium_index":
        mark = columns.get("mark_price")
        if mark is None:
            mark = _first_numeric_series(frame, ("mark_price",))
        index = columns.get("index_price")
        if index is None:
            index = _first_numeric_series(frame, ("index_price",))
        if mark is not None and index is not None and "premium_basis_rate" not in columns:
            columns["premium_basis_rate"] = (mark - index) / index.replace(0.0, np.nan)
        if mark is not None and index is not None and "premium_basis_abs" not in columns:
            columns["premium_basis_abs"] = mark - index
        if "premium_basis_rate" in columns and "basis_bps" not in columns:
            columns["basis_bps"] = columns["premium_basis_rate"] * 10_000.0
        if "premium_basis_rate" in columns and "premium_close" not in columns:
            columns["premium_close"] = columns["premium_basis_rate"]
    if family == "open_interest" and "open_interest" in columns:
        if "open_interest_change" not in columns:
            columns["open_interest_change"] = columns["open_interest"].groupby(frame["__fixture_family_symbol"]).diff()
        if "open_interest_change_pct" not in columns:
            previous = columns["open_interest"].groupby(frame["__fixture_family_symbol"]).shift(1)
            columns["open_interest_change_pct"] = columns["open_interest_change"] / previous.replace(0.0, np.nan)
    if family == "agg_trade":
        signed = columns.get("primary_signed_imbalance_ratio")
        if signed is None:
            signed = _derived_agg_trade_signed_ratio(frame)
            if signed is not None:
                columns["primary_signed_imbalance_ratio"] = signed
        if signed is not None and "primary_sqrt_signed_imbalance_ratio" not in columns:
            columns["primary_sqrt_signed_imbalance_ratio"] = np.sign(signed) * np.sqrt(signed.abs())
    return {column: series.replace([np.inf, -np.inf], np.nan) for column, series in columns.items()}


def _derived_agg_trade_signed_ratio(frame: pd.DataFrame) -> pd.Series | None:
    buy = _first_numeric_series(frame, ("taker_buy_quote_volume", "buy_quote_volume", "taker_buy_base_volume", "buy_quantity"))
    total = _first_numeric_series(frame, ("quote_volume", "volume", "quantity"))
    sell = _first_numeric_series(frame, ("sell_quote_volume", "sell_quantity"))
    if buy is not None and sell is not None:
        denominator = (buy + sell).replace(0.0, np.nan)
        return (buy - sell) / denominator
    if buy is not None and total is not None:
        denominator = total.replace(0.0, np.nan)
        return ((2.0 * buy) / denominator) - 1.0
    return None


def _first_numeric_series(frame: pd.DataFrame, aliases: tuple[str, ...]) -> pd.Series | None:
    for column in aliases:
        if column in frame.columns:
            return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return None


def _family_materialization_record(
    *,
    family: str,
    family_payload: Mapping[str, Any],
    event_time_field: str,
    input_columns: list[str],
    output_columns: list[str],
    joined: bool,
    skipped_reason: str,
    source_row_count: int,
    matched_row_count: int,
    unmatched_row_count: int,
    null_rates: Mapping[str, float],
) -> dict[str, Any]:
    return {
        "family": family,
        "path": str(family_payload.get("path") or ""),
        "sha256": family_payload.get("sha256"),
        "row_count": int(family_payload.get("row_count") or source_row_count),
        "actual_row_count": int(source_row_count),
        "columns": list(family_payload.get("columns") or input_columns),
        "event_time_field": event_time_field,
        "data_family": family_payload.get("data_family", family),
        "required": bool(family_payload.get("required", False)),
        "joined": bool(joined),
        "skipped_reason": skipped_reason,
        "join_keys": ["symbol", event_time_field],
        "asof_direction": "backward",
        "lookahead_policy": "family_event_time_ms_lte_cycle_bar_time_ms",
        "output_columns": list(output_columns),
        "matched_row_count": int(matched_row_count),
        "unmatched_row_count": int(unmatched_row_count),
        "null_rates": {str(column): float(rate) for column, rate in sorted(null_rates.items())},
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _stable_hash(payload: Any) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")
    ).hexdigest()
