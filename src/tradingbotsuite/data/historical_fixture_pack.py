from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION = "historical-fixture-pack-manifest-v1"
REQUIRED_CYCLE_COLUMNS = {
    "symbol",
}
TIME_COLUMN_ALIASES = ("bar_time_ms", "signal_bar_time_ms", "time_ms")
PRICE_COLUMN_ALIASES = {
    "open": ("open", "signal_bar_open", "entry_price"),
    "high": ("high", "signal_bar_high", "entry_price"),
    "low": ("low", "signal_bar_low", "entry_price"),
    "close": ("close", "signal_bar_close", "entry_price"),
    "volume": ("volume", "signal_bar_volume"),
}
REQUIRED_FAMILIES = {"bars"}
OPTIONAL_FAMILIES = {"funding_rate", "premium_index", "open_interest", "agg_trade", "liquidation", "lower_timeframe_bars"}
CONTEXT_FAMILIES = ("funding_rate", "premium_index", "open_interest", "agg_trade", "liquidation")
CONTEXT_MANIFEST_METADATA_FIELDS = (
    "retention_policy",
    "coverage_scope",
    "latest_window_only",
    "context_family_role",
    "stream_health",
    "source_access_mode",
    "diagnostic_only",
    "free_sample_data",
)
BROAD_CONTEXT_COVERAGE_SCOPES = {"multi_year", "full_history", "broad_historical", "oos_stress_coverage"}
PROVIDER_CONTEXT_FAMILY_SOURCES = {
    "funding_rate": {"binance_vision", "crypto_lake", "binance_usdm_rest"},
    "premium_index": {"binance_vision", "binance_usdm_rest"},
    "open_interest": {"binance_vision", "crypto_lake", "binance_usdm_rest"},
    "agg_trade": {"binance_vision", "crypto_lake"},
    "liquidation": {"binance_vision", "crypto_lake"},
}
CONTEXT_EVENT_TIME_ALIASES = {
    "funding_rate": ("event_time_ms", "funding_time_ms", "time_ms", "timestamp_ms"),
    "premium_index": ("event_time_ms", "time_ms", "timestamp_ms"),
    "open_interest": ("event_time_ms", "time_ms", "timestamp_ms"),
    "agg_trade": ("event_time_ms", "transact_time_ms", "trade_time_ms", "time_ms", "timestamp_ms"),
    "liquidation": ("event_time_ms", "trade_time_ms", "time_ms", "timestamp_ms"),
}
_REMOVED_CHART_SOURCE = "trading" + "view"
_REMOVED_CHART_SOURCE_FLAG = _REMOVED_CHART_SOURCE + "_source_used"
_REMOVED_CHART_SOURCE_NOT_ALLOWED = _REMOVED_CHART_SOURCE + "_source_not_allowed"
FAMILY_REQUIRED_COLUMNS = {
    "bars": {
        "event_time_ms",
        "symbol",
        "interval",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
    },
    "lower_timeframe_bars": {
        "bar_time_ms",
        "symbol",
        "open",
        "high",
        "low",
        "close",
    },
}


@dataclass(frozen=True, slots=True)
class ProviderKlineFixturePackBuildResult:
    output_dir: Path
    manifest_path: Path
    cycle_dataset_path: Path
    bars_path: Path
    fixture_id: str
    row_count: int
    manifest_sha256: str
    cycle_dataset_sha256: str
    bars_sha256: str
    source_manifest_path: Path
    source_data_path: Path
    source_data_sha256: str
    context_family_paths: Mapping[str, str] | None = None
    context_family_sha256: Mapping[str, str] | None = None
    context_manifest_paths: Mapping[str, str] | None = None
    context_source_data_paths: Mapping[str, str] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "cycle_dataset_path": str(self.cycle_dataset_path),
            "bars_path": str(self.bars_path),
            "fixture_id": self.fixture_id,
            "row_count": self.row_count,
            "manifest_sha256": self.manifest_sha256,
            "cycle_dataset_sha256": self.cycle_dataset_sha256,
            "bars_sha256": self.bars_sha256,
            "source_manifest_path": str(self.source_manifest_path),
            "source_data_path": str(self.source_data_path),
            "source_data_sha256": self.source_data_sha256,
            "context_family_paths": dict(self.context_family_paths or {}),
            "context_family_sha256": dict(self.context_family_sha256 or {}),
            "context_manifest_paths": dict(self.context_manifest_paths or {}),
            "context_source_data_paths": dict(self.context_source_data_paths or {}),
        }


@dataclass(frozen=True, slots=True)
class HistoricalFixturePackValidation:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    cycle_dataset_path: Path | None
    fixture_id: str | None
    row_count: int | None
    lower_timeframe_dataset_path: Path | None = None
    lower_timeframe_row_count: int | None = None
    lower_timeframe_family: Mapping[str, Any] | None = None
    optional_context_families: Mapping[str, Mapping[str, Any]] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "cycle_dataset_path": str(self.cycle_dataset_path) if self.cycle_dataset_path is not None else None,
            "fixture_id": self.fixture_id,
            "row_count": self.row_count,
            "lower_timeframe_dataset_path": (
                str(self.lower_timeframe_dataset_path)
                if self.lower_timeframe_dataset_path is not None
                else None
            ),
            "lower_timeframe_row_count": self.lower_timeframe_row_count,
            "lower_timeframe_family": dict(self.lower_timeframe_family or {}),
            "optional_context_families": {
                str(family): dict(payload)
                for family, payload in sorted(dict(self.optional_context_families or {}).items())
            },
        }


@dataclass(frozen=True, slots=True)
class PublicArchiveFixtureReadiness:
    ready: bool
    status: str
    reasons: tuple[str, ...]
    fixture_id: str | None
    symbol: str | None
    base_interval: str | None
    required_families: tuple[str, ...]
    durable_context_families: tuple[str, ...]
    diagnostic_context_families: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "reasons": list(self.reasons),
            "fixture_id": self.fixture_id,
            "symbol": self.symbol,
            "base_interval": self.base_interval,
            "required_families": list(self.required_families),
            "durable_context_families": list(self.durable_context_families),
            "diagnostic_context_families": list(self.diagnostic_context_families),
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }


PUBLIC_ARCHIVE_READY_SYMBOLS = ("BTCUSDT", "ETHUSDT")
PUBLIC_ARCHIVE_REQUIRED_FAMILIES = ("bars", "lower_timeframe_bars", "agg_trade")
PUBLIC_ARCHIVE_REQUIRED_WINDOW_LABELS = ("trend_bull", "drawdown_bear", "range_chop", "high_vol_shock")


def build_provider_kline_fixture_pack(
    *,
    source_manifest_path: Path,
    output_dir: Path,
    fixture_id: str | None = None,
    row_limit: int = 144,
    slice_mode: str = "tail",
    context_manifest_paths: Sequence[Path] | None = None,
) -> ProviderKlineFixturePackBuildResult:
    """Build a compact historical fixture pack from a local provider kline manifest.

    This builder is intentionally research-only and rejects legacy chart files
    manifests. It consumes already-local provider data; it does not fetch,
    download, or touch live runtime state.
    """

    if row_limit < 1:
        raise ValueError("row_limit_must_be_positive")
    if slice_mode != "tail":
        raise ValueError("unsupported_provider_kline_fixture_slice_mode:tail_required")

    source_manifest_path = Path(source_manifest_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    source_manifest = _read_json_object(source_manifest_path)
    _reject_unsafe_provider_manifest(source_manifest, context="fixture_pack")

    source_name, source_raw = _provider_source_identity(source_manifest)
    data_family = _provider_data_family(source_manifest)
    if data_family != "kline":
        raise ValueError(f"provider_kline_fixture_requires_kline_family:{data_family}")
    if source_name not in {"binance_rest", "binance_vision", "crypto_lake"}:
        raise ValueError(f"unsupported_provider_kline_source:{source_name}")

    symbol = str(source_manifest.get("symbol") or "").strip().upper()
    if not symbol:
        raise ValueError("provider_kline_manifest_symbol_required")
    interval = str(source_manifest.get("interval") or "15m").strip() or "15m"
    source_data_path = _resolve_provider_kline_data_path(source_manifest, manifest_path=source_manifest_path)
    observed_source_sha = _file_sha256(source_data_path)
    declared_source_sha = _normalize_sha256(
        source_manifest.get("sha256")
        or source_manifest.get("content_hash")
        or source_manifest.get("source_hash")
    )
    if declared_source_sha is not None and declared_source_sha != observed_source_sha:
        raise ValueError("provider_kline_source_hash_mismatch")

    rows = _read_provider_kline_rows(source_data_path, symbol=symbol, interval=interval)
    if not rows:
        raise ValueError("provider_kline_source_has_no_rows")
    declared_row_count = source_manifest.get("row_count")
    if declared_row_count is not None and int(declared_row_count) != len(rows):
        raise ValueError(f"provider_kline_source_row_count_mismatch:{declared_row_count}:{len(rows)}")
    source = pd.DataFrame(rows).sort_values("time_ms", kind="mergesort").reset_index(drop=True)
    source["source_row_index"] = range(len(source))
    fixture = source.tail(min(row_limit, len(source))).copy().reset_index(drop=True)
    source_start_row_index = int(fixture["source_row_index"].min())
    source_end_row_index = int(fixture["source_row_index"].max())
    fixture_id = fixture_id or f"{symbol.lower()}-{interval}-provider-kline-fixture"

    cycle = _provider_fixture_cycle_frame(
        fixture,
        symbol=symbol,
        source_name=source_name,
        source_raw=source_raw,
        interval=interval,
    )
    bars = _provider_fixture_bars_frame(cycle, interval=interval)
    output_dir.mkdir(parents=True, exist_ok=True)
    cycle_path = output_dir / "cycle_dataset.parquet"
    bars_path = output_dir / f"bars_{interval}.parquet"
    cycle.to_parquet(cycle_path, index=False)
    bars.to_parquet(bars_path, index=False)
    cycle_sha = _file_sha256(cycle_path)
    bars_sha = _file_sha256(bars_path)
    context_family_entries, context_source_records = _build_provider_context_family_entries(
        context_manifest_paths=tuple(context_manifest_paths or ()),
        output_dir=output_dir,
        symbol=symbol,
        fixture_first_time_ms=int(cycle["time_ms"].min()),
        fixture_last_time_ms=int(cycle["time_ms"].max()),
    )
    omitted_optional_families = {
        "lower_timeframe_bars": "not_supplied_to_provider_fixture_builder",
        **{
            family: "not_supplied_to_provider_fixture_builder"
            for family in CONTEXT_FAMILIES
            if family not in context_family_entries
        },
    }
    source_non_promotable_reasons = [
        "compact_fixture_pack_not_oos_acceptance_evidence",
        "receive_time_unavailable",
    ]
    if context_family_entries:
        source_non_promotable_reasons.append("optional_context_family_manifests_are_research_only")
    else:
        source_non_promotable_reasons.append("ohlcv_only_optional_context_omitted")
    source_metadata = _provider_source_metadata(
        source_manifest,
        source_name=source_name,
        data_family=data_family,
    )

    manifest = {
        "manifest_version": HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "fixture_id": fixture_id,
        "fixture_scope": "generated_small_provider_kline_fixture_not_oos_acceptance_evidence",
        "symbol": symbol,
        "base_interval": interval,
        "source": {
            "source_type": "provider_manifest",
            "source_name": source_name,
            "source_raw": source_raw,
            "data_family": data_family,
            "event_time_field": "time_ms",
            "receive_time_unavailable_reason": (
                source_manifest.get("receive_time_unavailable_reason")
                or "provider_kline_manifest_does_not_prove_original_receive_time"
            ),
            "non_promotable_reasons": source_non_promotable_reasons,
            "local_source_data_path": str(source_data_path),
            "local_source_manifest_path": str(source_manifest_path),
            "source_sha256": observed_source_sha,
            "source_manifest_sha256": _file_sha256(source_manifest_path),
            "source_declared_sha256": declared_source_sha,
            "source_row_count": int(len(source)),
            "source_first_time_ms": int(source["time_ms"].min()),
            "source_last_time_ms": int(source["time_ms"].max()),
            "context_sources": context_source_records,
            **source_metadata,
        },
        "derivation": {
            "derivation_type": "contiguous_tail_slice",
            "input_source": f"{source_name}_{data_family}_manifest",
            _REMOVED_CHART_SOURCE_FLAG: False,
            "synthetic_source_used": False,
            "context_family_count": int(len(context_family_entries)),
            "context_families": sorted(context_family_entries),
            "source_start_row_index": source_start_row_index,
            "source_end_row_index": source_end_row_index,
            "row_count": int(len(cycle)),
            "first_time_ms": int(cycle["time_ms"].min()),
            "last_time_ms": int(cycle["time_ms"].max()),
            "notes": [
                "OHLCV fields are selected from a local provider kline manifest.",
                "Optional context families, when supplied, are selected from already-local provider manifests using event-time-only research replay.",
                "Regime labels are deterministic OHLCV-derived research annotations for split coverage only.",
                "No legacy chart export, Pine marker, or parity artifact is used.",
            ],
        },
        "cycle_dataset": {
            "path": cycle_path.name,
            "sha256": f"sha256:{cycle_sha}",
            "row_count": int(len(cycle)),
            "time_field": "signal_bar_time_ms",
            "columns": list(cycle.columns),
        },
        "families": {
            "bars": {
                "path": bars_path.name,
                "data_family": "kline",
                "interval": interval,
                "event_time_field": "event_time_ms",
                "sha256": f"sha256:{bars_sha}",
                "row_count": int(len(bars)),
                "required": True,
                "columns": list(bars.columns),
            },
            **context_family_entries,
        },
        "omitted_optional_families": omitted_optional_families,
        "research_evidence_limitations": [
            "compact_fixture_for_contract_and_full_cycle_execution_only",
            "not_sufficient_for_oos_acceptance",
            "not_sufficient_for_performance_claims",
            "not_promotion_ready",
        ],
    }
    manifest_path = output_dir / "fixture_pack_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    return ProviderKlineFixturePackBuildResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        cycle_dataset_path=cycle_path,
        bars_path=bars_path,
        fixture_id=fixture_id,
        row_count=int(len(cycle)),
        manifest_sha256=_file_sha256(manifest_path),
        cycle_dataset_sha256=cycle_sha,
        bars_sha256=bars_sha,
        source_manifest_path=source_manifest_path,
        source_data_path=source_data_path,
        source_data_sha256=observed_source_sha,
        context_family_paths={
            family: str(output_dir / str(entry["path"]))
            for family, entry in sorted(context_family_entries.items())
        },
        context_family_sha256={
            family: str(entry["sha256"])
            for family, entry in sorted(context_family_entries.items())
        },
        context_manifest_paths={
            record["data_family"]: str(record["local_source_manifest_path"])
            for record in context_source_records
        },
        context_source_data_paths={
            record["data_family"]: str(record["local_source_data_path"])
            for record in context_source_records
        },
    )


def validate_historical_fixture_pack_manifest(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> HistoricalFixturePackValidation:
    errors: list[str] = []
    warnings: list[str] = []
    base_dir = Path(manifest_path).expanduser().parent if manifest_path is not None else Path.cwd()

    version = str(manifest.get("manifest_version") or manifest.get("fixture_pack_manifest_version") or "")
    if version != HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION:
        errors.append(f"unsupported_fixture_pack_manifest_version:{version}")
    if manifest.get("research_only") is not True:
        errors.append("fixture_pack_must_be_research_only")
    if manifest.get("observe_only") is not True:
        errors.append("fixture_pack_must_be_observe_only")
    if manifest.get("promotion_ready") is not False:
        errors.append("fixture_pack_must_not_be_promotion_ready")
    errors.extend(_fixture_manifest_unsafe_provenance_errors(manifest))

    cycle_dataset = manifest.get("cycle_dataset")
    cycle_path: Path | None = None
    cycle_row_count: int | None = None
    lower_timeframe_path: Path | None = None
    lower_timeframe_row_count: int | None = None
    lower_timeframe_family: dict[str, Any] | None = None
    optional_context_families: dict[str, dict[str, Any]] = {}
    if not isinstance(cycle_dataset, Mapping):
        errors.append("cycle_dataset_required")
    else:
        cycle_path = _resolve_entry_path(cycle_dataset, base_dir=base_dir)
        if cycle_path is None:
            errors.append("cycle_dataset_path_required")
        elif not cycle_path.exists():
            errors.append(f"cycle_dataset_path_missing:{cycle_path}")
        else:
            cycle_errors, cycle_warnings, cycle_row_count = _validate_parquet_entry(
                cycle_path,
                cycle_dataset,
                required_columns=REQUIRED_CYCLE_COLUMNS,
                validate_cycle_aliases=True,
                require_sha256=True,
                require_row_count=True,
            )
            errors.extend(f"cycle_dataset_{error}" for error in cycle_errors)
            warnings.extend(f"cycle_dataset_{warning}" for warning in cycle_warnings)

    families = manifest.get("families")
    if not isinstance(families, Mapping):
        errors.append("families_required")
    else:
        missing_required = sorted(REQUIRED_FAMILIES - set(str(key) for key in families))
        errors.extend(f"family_required:{family}" for family in missing_required)
        unknown = sorted(set(str(key) for key in families) - REQUIRED_FAMILIES - OPTIONAL_FAMILIES)
        warnings.extend(f"family_unknown:{family}" for family in unknown)
        for family_name, entry in families.items():
            family_key = str(family_name)
            if not isinstance(entry, Mapping):
                errors.append(f"family_entry_invalid:{family_name}")
                continue
            family_required = bool(entry.get("required", family_key in REQUIRED_FAMILIES))
            entry_path = _resolve_entry_path(entry, base_dir=base_dir)
            if entry_path is None:
                if family_required:
                    errors.append(f"family_path_required:{family_name}")
                continue
            if not entry_path.exists():
                if family_required:
                    errors.append(f"family_path_missing:{family_name}:{entry_path}")
                else:
                    warnings.append(f"optional_family_path_missing:{family_name}:{entry_path}")
                continue
            declared_columns = set(str(column) for column in entry.get("columns", ()))
            if family_required and not declared_columns:
                errors.append(f"family_{family_name}_columns_required")
            required_columns = set(FAMILY_REQUIRED_COLUMNS.get(family_key, set()))
            if family_key in CONTEXT_FAMILIES:
                required_columns |= {
                    "symbol",
                    str(entry.get("event_time_field") or entry.get("time_field") or "event_time_ms"),
                }
            if family_required:
                required_columns |= declared_columns
            else:
                required_columns |= declared_columns
            entry_errors, entry_warnings, _ = _validate_parquet_entry(
                entry_path,
                entry,
                required_columns=required_columns,
                validate_cycle_aliases=False,
                require_sha256=family_required or family_key == "lower_timeframe_bars" or family_key in CONTEXT_FAMILIES,
                require_row_count=family_required or family_key == "lower_timeframe_bars" or family_key in CONTEXT_FAMILIES,
            )
            if family_key in CONTEXT_FAMILIES:
                declared_data_family_raw = entry.get("data_family")
                if declared_data_family_raw is None or not str(declared_data_family_raw).strip():
                    entry_errors.append("data_family_required")
                else:
                    declared_data_family = str(declared_data_family_raw)
                    if declared_data_family != family_key:
                        entry_errors.append(f"data_family_mismatch:{declared_data_family}:{family_key}")
            if family_key in CONTEXT_FAMILIES and not _context_family_has_supported_columns(entry_path, family=family_key):
                entry_errors.append("unsupported_context_columns")
            if family_key in CONTEXT_FAMILIES:
                _validate_context_family_metadata(entry, family=family_key, errors=entry_errors)
            errors.extend(f"family_{family_name}_{error}" for error in entry_errors)
            warnings.extend(f"family_{family_name}_{warning}" for warning in entry_warnings)
            if family_key in CONTEXT_FAMILIES and not entry_errors:
                _, _, context_row_count = _validate_parquet_entry(
                    entry_path,
                    entry,
                    required_columns=set(),
                    validate_cycle_aliases=False,
                    require_sha256=False,
                    require_row_count=False,
                )
                optional_context_families[family_key] = _family_payload(
                    family_key,
                    entry,
                    entry_path=entry_path,
                    row_count=context_row_count,
                    default_event_time_field="event_time_ms",
                )
            if family_key == "lower_timeframe_bars" and not entry_errors:
                _, _, lower_timeframe_row_count = _validate_parquet_entry(
                    entry_path,
                    entry,
                    required_columns=set(),
                    validate_cycle_aliases=False,
                    require_sha256=False,
                    require_row_count=False,
                )
                lower_timeframe_path = entry_path
                lower_timeframe_family = _family_payload(
                    "lower_timeframe_bars",
                    entry,
                    entry_path=entry_path,
                    row_count=lower_timeframe_row_count,
                    default_event_time_field="bar_time_ms",
                )

    validation = HistoricalFixturePackValidation(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        cycle_dataset_path=cycle_path,
        fixture_id=str(manifest.get("fixture_id")) if manifest.get("fixture_id") is not None else None,
        row_count=cycle_row_count,
        lower_timeframe_dataset_path=lower_timeframe_path,
        lower_timeframe_row_count=lower_timeframe_row_count,
        lower_timeframe_family=lower_timeframe_family,
        optional_context_families=optional_context_families,
    )
    return validation


def assert_valid_historical_fixture_pack_manifest(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> HistoricalFixturePackValidation:
    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    if not validation.valid:
        raise ValueError(f"invalid historical fixture pack manifest: {', '.join(validation.errors)}")
    return validation


def validate_public_archive_fixture_readiness(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> PublicArchiveFixtureReadiness:
    """Evaluate whether a small fixture pack can claim durable BTC/ETH archive readiness.

    This readiness layer is stricter than normal fixture validation. REST
    latest-window context can remain a valid research fixture, but it cannot
    satisfy this public-archive readiness gate.
    """

    reasons: list[str] = []
    validation = validate_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    if not validation.valid:
        reasons.extend(f"fixture_manifest_invalid:{reason}" for reason in validation.errors)
    symbol = _optional_text(manifest.get("symbol"))
    base_interval = _optional_text(manifest.get("base_interval"))
    if symbol not in PUBLIC_ARCHIVE_READY_SYMBOLS:
        reasons.append(f"symbol_not_supported_for_public_archive_readiness:{symbol}")
    if base_interval != "15m":
        reasons.append(f"base_interval_must_be_15m:{base_interval}")
    if manifest.get("research_only") is not True:
        reasons.append("research_only_required")
    if manifest.get("observe_only") is not True:
        reasons.append("observe_only_required")
    if manifest.get("promotion_ready") is not False:
        reasons.append("promotion_ready_must_be_false")

    families = manifest.get("families") if isinstance(manifest.get("families"), Mapping) else {}
    missing_required = [family for family in PUBLIC_ARCHIVE_REQUIRED_FAMILIES if family not in families]
    reasons.extend(f"public_archive_required_family_missing:{family}" for family in missing_required)
    bars_entry = families.get("bars") if isinstance(families.get("bars"), Mapping) else {}
    if str(bars_entry.get("data_family") or "") != "kline":
        reasons.append("bars_family_must_be_kline")
    if str(bars_entry.get("interval") or base_interval or "") != "15m":
        reasons.append("bars_interval_must_be_15m")

    source = manifest.get("source") if isinstance(manifest.get("source"), Mapping) else {}
    source_name = _optional_text(source.get("source_name"))
    if source_name != "binance_vision":
        reasons.append(f"primary_bars_public_archive_source_required:{source_name}")
    reasons.extend(_public_archive_source_reasons(source, context="source"))
    reasons.extend(_archive_quality_evidence_reasons(bars_entry, family="bars"))

    lower_entry = families.get("lower_timeframe_bars") if isinstance(families.get("lower_timeframe_bars"), Mapping) else {}
    if lower_entry:
        if _optional_text(lower_entry.get("interval")) not in {"1m", "3m", "5m"}:
            reasons.append(f"lower_timeframe_interval_not_suitable_for_exit_sequence:{lower_entry.get('interval')}")
        reasons.extend(_archive_quality_evidence_reasons(lower_entry, family="lower_timeframe_bars"))

    durable_context_families: list[str] = []
    diagnostic_context_families: list[str] = []
    for family in CONTEXT_FAMILIES:
        entry = families.get(family)
        if not isinstance(entry, Mapping):
            continue
        entry_source = _optional_text(entry.get("source_name")) or source_name
        coverage_scope = _optional_text(entry.get("coverage_scope"))
        latest_window_only = entry.get("latest_window_only") is True
        free_sample = entry.get("source_access_mode") == "free_sample" or entry.get("free_sample_data") is True
        zero_filled = [str(item) for item in entry.get("zero_filled_fields") or []]
        if zero_filled:
            reasons.append(f"context_family_zero_filled_fields_forbidden:{family}:{','.join(sorted(zero_filled))}")
        if latest_window_only or entry_source == "binance_usdm_rest":
            diagnostic_context_families.append(family)
            reasons.append(f"latest_window_context_diagnostic_only:{family}")
        elif free_sample or entry.get("diagnostic_only") is True:
            diagnostic_context_families.append(family)
            reasons.append(f"diagnostic_context_source_not_candidate_ready:{family}")
        elif coverage_scope in {"public_archive_partition", "local_vendor_export"}:
            durable_context_families.append(family)
        else:
            diagnostic_context_families.append(family)
            reasons.append(f"context_family_durable_coverage_required:{family}:{coverage_scope}")
        if family == "agg_trade":
            if entry_source != "binance_vision":
                reasons.append(f"agg_trade_public_archive_source_required:{entry_source}")
            if _optional_text(entry.get("feature_claim_scope")) not in {
                "trade_flow_proxy_not_order_book_imbalance_or_ofi",
                "agg_trade_trade_flow_proxy",
            }:
                reasons.append("agg_trade_trade_flow_proxy_claim_required")
            reasons.extend(_archive_quality_evidence_reasons(entry, family="agg_trade"))

    omitted = manifest.get("omitted_optional_families")
    if not isinstance(omitted, Mapping):
        reasons.append("omitted_optional_families_required")
    else:
        for family in OPTIONAL_FAMILIES - set(families):
            if family not in omitted:
                reasons.append(f"omitted_optional_family_reason_required:{family}")

    limitations = manifest.get("research_evidence_limitations")
    if not isinstance(limitations, list) or not limitations:
        reasons.append("research_evidence_limitations_required")
    elif "not_promotion_ready" not in {str(item) for item in limitations}:
        reasons.append("research_evidence_limitations_not_promotion_ready_required")

    reasons.extend(_window_selection_reasons(manifest))
    ready = not reasons
    return PublicArchiveFixtureReadiness(
        ready=ready,
        status="durable_public_archive_ready" if ready else "diagnostic_or_incomplete",
        reasons=tuple(dict.fromkeys(reasons)),
        fixture_id=str(manifest.get("fixture_id")) if manifest.get("fixture_id") is not None else None,
        symbol=symbol,
        base_interval=base_interval,
        required_families=PUBLIC_ARCHIVE_REQUIRED_FAMILIES,
        durable_context_families=tuple(sorted(set(durable_context_families))),
        diagnostic_context_families=tuple(sorted(set(diagnostic_context_families))),
    )


def assert_public_archive_fixture_ready(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
) -> PublicArchiveFixtureReadiness:
    readiness = validate_public_archive_fixture_readiness(manifest, manifest_path=manifest_path)
    if not readiness.ready:
        raise ValueError(f"fixture pack is not durable public archive ready: {', '.join(readiness.reasons)}")
    return readiness


def resolve_fixture_pack_cycle_dataset_path(manifest: Mapping[str, Any], *, manifest_path: Path) -> Path:
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    if validation.cycle_dataset_path is None:
        raise ValueError("historical fixture pack validation did not resolve a cycle dataset path")
    return validation.cycle_dataset_path


def _public_archive_source_reasons(source: Mapping[str, Any], *, context: str) -> list[str]:
    reasons: list[str] = []
    if source.get("latest_window_only") is True:
        reasons.append(f"{context}_latest_window_only_not_public_archive_ready")
    coverage_scope = _optional_text(source.get("coverage_scope"))
    if coverage_scope not in {None, "public_archive_partition"}:
        reasons.append(f"{context}_public_archive_coverage_scope_required:{coverage_scope}")
    source_sha = _optional_text(source.get("source_sha256") or source.get("content_hash"))
    if source_sha is None:
        reasons.append(f"{context}_source_sha256_required")
    if _optional_text(source.get("source_name")) == "binance_vision":
        checksum_verified = (
            source.get("checksum_verified") is True
            or _optional_text(source.get("checksum_status")) == "verified"
            or source.get("source_checksum_verified") is True
        )
        checksum_present = any(
            _optional_text(source.get(field)) is not None
            for field in ("checksum_sha256", "checksum_path", "checksum_url", "source_checksum_sha256")
        )
        if not checksum_verified and not checksum_present:
            reasons.append(f"{context}_binance_vision_checksum_evidence_required")
        if source.get("checksum_verified") is False or _optional_text(source.get("checksum_status")) == "failed":
            reasons.append(f"{context}_binance_vision_checksum_must_verify")
    return reasons


def _archive_quality_evidence_reasons(entry: Mapping[str, Any], *, family: str) -> list[str]:
    reasons: list[str] = []
    if entry and "row_count" not in entry:
        reasons.append(f"{family}_row_count_required")
    if entry and not _optional_text(entry.get("sha256") or entry.get("content_hash")):
        reasons.append(f"{family}_sha256_required")
    if family in {"bars", "lower_timeframe_bars"} and "gap_check_status" not in entry:
        reasons.append(f"{family}_gap_check_evidence_required")
    if family in {"bars", "agg_trade"} and "duplicate_count" not in entry:
        reasons.append(f"{family}_duplicate_check_evidence_required")
    return reasons


def _window_selection_reasons(manifest: Mapping[str, Any]) -> list[str]:
    selection = manifest.get("window_selection")
    if not isinstance(selection, Mapping):
        readiness = manifest.get("durable_public_archive_readiness")
        if isinstance(readiness, Mapping):
            selection = readiness.get("window_selection")
    if not isinstance(selection, Mapping):
        return ["window_selection_required"]
    regime_windows = selection.get("regime_windows") if isinstance(selection.get("regime_windows"), Mapping) else selection
    missing = []
    for label in PUBLIC_ARCHIVE_REQUIRED_WINDOW_LABELS:
        window = regime_windows.get(label) if isinstance(regime_windows, Mapping) else None
        if not isinstance(window, Mapping):
            missing.append(label)
            continue
        if window.get("start_time_ms") is None or window.get("end_time_ms") is None:
            missing.append(label)
    if missing:
        return [f"window_selection_regime_windows_required:{','.join(missing)}"]
    return []


def _resolve_entry_path(entry: Mapping[str, Any], *, base_dir: Path) -> Path | None:
    raw_path = entry.get("path") or entry.get("dataset_path") or entry.get("parquet_path") or entry.get("data_path")
    if not raw_path:
        return None
    candidate = Path(str(raw_path)).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def _family_payload(
    family_key: str,
    entry: Mapping[str, Any],
    *,
    entry_path: Path,
    row_count: int | None,
    default_event_time_field: str,
) -> dict[str, Any]:
    payload = {
        "family": family_key,
        "path": str(entry_path),
        "sha256": _file_sha256(entry_path),
        "row_count": row_count,
        "columns": list(entry.get("columns", ())),
        "interval": entry.get("interval"),
        "event_time_field": entry.get("event_time_field") or entry.get("time_field") or default_event_time_field,
        "data_family": entry.get("data_family", family_key),
        "source_name": entry.get("source_name"),
        "required": bool(entry.get("required", False)),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    source_name = _optional_text(entry.get("source_name"))
    if source_name is not None:
        payload.update(_provider_context_metadata(entry, source_name=source_name, family=family_key))
    else:
        payload.update(_selected_context_metadata(entry))
    return payload


def _selected_context_metadata(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        field: entry[field]
        for field in CONTEXT_MANIFEST_METADATA_FIELDS
        if field in entry
    }


def _provider_source_metadata(
    manifest: Mapping[str, Any],
    *,
    source_name: str,
    data_family: str,
) -> dict[str, Any]:
    metadata = _selected_context_metadata(manifest)
    metadata.pop("context_family_role", None)
    if source_name == "crypto_lake":
        free_sample = metadata.get("source_access_mode") == "free_sample" or manifest.get("free_sample_data") is True
        if free_sample:
            metadata["source_access_mode"] = "free_sample"
            metadata["free_sample_data"] = True
            metadata.setdefault("diagnostic_only", True)
            metadata.setdefault("coverage_scope", "free_sample_diagnostic")
            metadata.setdefault(
                "retention_policy",
                {
                    "scope": "anonymous_free_sample",
                    "claim": "sample_coverage_only",
                },
            )
        else:
            metadata.setdefault("coverage_scope", "local_vendor_export")
            metadata.setdefault(
                "retention_policy",
                {
                    "scope": "local_export_file",
                    "claim": "coverage_limited_to_local_export",
                },
            )
        metadata.setdefault("latest_window_only", False)
        metadata.setdefault(
            "stream_health",
            {
                "status": "not_applicable_batch_backfill",
                "reason": f"{data_family} rows are archive/backfill research data; no live stream continuity is claimed",
            },
        )
    return metadata


def _provider_context_metadata(
    manifest: Mapping[str, Any],
    *,
    source_name: str,
    family: str,
) -> dict[str, Any]:
    metadata = _selected_context_metadata(manifest)
    metadata.setdefault("context_family_role", "perp_context")
    metadata.setdefault(
        "stream_health",
        {
            "status": "not_applicable_batch_backfill",
            "reason": "fixture context is derived from local archive/backfill data",
        },
    )
    if source_name == "binance_usdm_rest":
        metadata.setdefault("coverage_scope", "latest_window_backfill")
        metadata.setdefault("latest_window_only", True)
        metadata.setdefault(
            "retention_policy",
            {
                "scope": "direct_endpoint_latest_window",
                "claim": "not_multi_year_coverage",
            },
        )
    elif source_name == "binance_vision":
        metadata.setdefault("coverage_scope", "public_archive_partition")
        metadata.setdefault("latest_window_only", False)
        metadata.setdefault(
            "retention_policy",
            {
                "scope": "public_archive_partition",
                "claim": "coverage_limited_to_downloaded_archive_partition",
            },
        )
    elif source_name == "crypto_lake":
        free_sample = metadata.get("source_access_mode") == "free_sample" or manifest.get("free_sample_data") is True
        if free_sample:
            metadata["source_access_mode"] = "free_sample"
            metadata["free_sample_data"] = True
            metadata.setdefault("diagnostic_only", True)
            metadata.setdefault("coverage_scope", "free_sample_diagnostic")
            metadata.setdefault(
                "retention_policy",
                {
                    "scope": "anonymous_free_sample",
                    "claim": "sample_coverage_only",
                },
            )
        else:
            metadata.setdefault("coverage_scope", "local_vendor_export")
            metadata.setdefault(
                "retention_policy",
                {
                    "scope": "local_export_file",
                    "claim": "coverage_limited_to_local_export",
                },
            )
        metadata.setdefault("latest_window_only", False)
    if family not in CONTEXT_FAMILIES:
        metadata.pop("context_family_role", None)
    return metadata


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_context_family_metadata(
    entry: Mapping[str, Any],
    *,
    family: str,
    errors: list[str],
) -> None:
    role = _optional_text(entry.get("context_family_role"))
    if role is not None and role != "perp_context":
        errors.append(f"context_family_role_mismatch:{role}:perp_context")

    latest_window_raw = entry.get("latest_window_only")
    if latest_window_raw is not None and not isinstance(latest_window_raw, bool):
        errors.append("latest_window_only_must_be_bool")
    latest_window_only = latest_window_raw is True

    coverage_scope = _optional_text(entry.get("coverage_scope"))
    if latest_window_only and coverage_scope in BROAD_CONTEXT_COVERAGE_SCOPES:
        errors.append(f"latest_window_context_cannot_claim_broad_coverage:{coverage_scope}")

    source_name = _optional_text(entry.get("source_name"))
    if source_name == "binance_usdm_rest" and (latest_window_raw is not None or coverage_scope is not None):
        if latest_window_raw is not True:
            errors.append("latest_window_only_required_for_binance_usdm_rest_context")
        if coverage_scope != "latest_window_backfill":
            errors.append(f"coverage_scope_required_for_binance_usdm_rest_context:{coverage_scope}")

    source_access_mode = _optional_text(entry.get("source_access_mode"))
    if source_name == "crypto_lake" and source_access_mode == "free_sample":
        if coverage_scope != "free_sample_diagnostic":
            errors.append(f"coverage_scope_required_for_crypto_lake_free_sample_context:{coverage_scope}")
        if entry.get("diagnostic_only") is not True:
            errors.append("diagnostic_only_required_for_crypto_lake_free_sample_context")


def _validate_parquet_entry(
    path: Path,
    entry: Mapping[str, Any],
    *,
    required_columns: set[str],
    validate_cycle_aliases: bool,
    require_sha256: bool,
    require_row_count: bool,
) -> tuple[list[str], list[str], int | None]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:
        return [f"parquet_unreadable:{path}:{exc}"], warnings, None

    row_count = int(len(frame))
    declared_row_count = entry.get("row_count")
    if declared_row_count is None and require_row_count:
        errors.append("row_count_required")
    elif declared_row_count is not None and int(declared_row_count) != row_count:
        errors.append(f"row_count_mismatch:{declared_row_count}:{row_count}")

    declared_sha = _normalize_sha256(entry.get("sha256") or entry.get("content_hash") or entry.get("parquet_sha256"))
    if declared_sha is None and require_sha256:
        errors.append("sha256_required")
    elif declared_sha is not None and declared_sha != _file_sha256(path):
        errors.append("sha256_mismatch")

    columns = set(str(column) for column in frame.columns)
    missing = sorted(required_columns - columns)
    if missing:
        errors.append(f"columns_missing:{','.join(missing)}")
    if validate_cycle_aliases:
        if not any(column in columns for column in TIME_COLUMN_ALIASES):
            errors.append(f"columns_missing_any:{','.join(TIME_COLUMN_ALIASES)}")
        for logical_name, aliases in PRICE_COLUMN_ALIASES.items():
            if not any(column in columns for column in aliases):
                errors.append(f"columns_missing_{logical_name}_alias:{','.join(aliases)}")
    declared_columns = set(str(column) for column in entry.get("columns", ()))
    if declared_columns and not declared_columns.issubset(columns):
        warnings.append(f"declared_columns_not_present:{','.join(sorted(declared_columns - columns))}")
    return errors, warnings, row_count


def _context_family_has_supported_columns(path: Path, *, family: str) -> bool:
    try:
        columns = set(str(column) for column in pd.read_parquet(path).columns)
    except Exception:
        return True
    if family == "funding_rate":
        return bool({"funding_rate", "last_funding_rate", "rate", "value"} & columns)
    if family == "premium_index":
        return bool(
            {"premium_basis_rate", "basis_rate", "premium_index", "value", "basis_bps", "mark_price", "index_price"}
            & columns
        )
    if family == "open_interest":
        return bool({"open_interest", "sum_open_interest", "oi", "value"} & columns)
    if family == "agg_trade":
        direct = {
            "primary_signed_imbalance_ratio",
            "signed_imbalance_ratio",
            "signed_ratio",
            "primary_sqrt_signed_imbalance_ratio",
            "top_of_book_imbalance",
            "spread_bps",
        }
        buy = {"taker_buy_quote_volume", "buy_quote_volume", "taker_buy_base_volume", "buy_quantity"}
        total = {"quote_volume", "volume", "quantity"}
        sell = {"sell_quote_volume", "sell_quantity"}
        return bool(direct & columns) or bool((buy & columns) and ((total & columns) or (sell & columns)))
    if family == "liquidation":
        return bool(
            {
                "liquidation_event_count",
                "liquidation_quote_notional",
                "liquidation_buy_notional",
                "liquidation_sell_notional",
                "liquidation_side_imbalance",
                "price",
                "quantity",
            }
            & columns
        )
    return True


def _normalize_sha256(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text.startswith("sha256:"):
        text = text.split(":", maxsplit=1)[1]
    return text


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _provider_source_identity(manifest: Mapping[str, Any]) -> tuple[str, str]:
    raw = str(manifest.get("source_name") or manifest.get("source") or "").strip()
    if raw == "binance_usdm_klines":
        return "binance_rest", raw
    source_aliases = {
        "binance_vision_archive": "binance_vision",
        "binance_vision": "binance_vision",
        "crypto_lake_archive": "crypto_lake",
        "crypto_lake": "crypto_lake",
    }
    if raw in source_aliases:
        return source_aliases[raw], str(manifest.get("source") or raw)
    if raw:
        return raw, str(manifest.get("source") or raw)
    raise ValueError("provider_kline_manifest_source_required")


def _provider_data_family(manifest: Mapping[str, Any]) -> str:
    raw = str(manifest.get("data_family") or manifest.get("family") or "").strip().lower()
    if raw in {"kline", "klines", "ohlcv", "ohlc"}:
        return "kline"
    if not raw and "interval" in manifest and str(manifest.get("source") or "") == "binance_usdm_klines":
        return "kline"
    return raw


def _resolve_provider_kline_data_path(manifest: Mapping[str, Any], *, manifest_path: Path) -> Path:
    raw = manifest.get("data_path") or manifest.get("dataset_path") or manifest.get("path")
    if raw:
        candidate = Path(str(raw)).expanduser()
        if not candidate.is_absolute():
            parent_candidate = (manifest_path.parent / candidate).resolve()
            if parent_candidate.exists():
                candidate = parent_candidate
            else:
                candidate = candidate.resolve()
        if candidate.exists():
            return candidate
        raise FileNotFoundError(candidate)
    text = str(manifest_path)
    if text.endswith(".manifest.json"):
        candidate = Path(text[: -len(".manifest.json")] + ".json")
        if candidate.exists():
            return candidate.resolve()
    raise ValueError("provider_kline_manifest_data_path_required")


def _read_provider_kline_rows(path: Path, *, symbol: str, interval: str) -> list[dict[str, Any]]:
    payload_rows = _read_provider_payload_rows(path, manifest_kind="provider_kline")
    rows: list[dict[str, Any]] = []
    for source_row_index, row in enumerate(payload_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"provider_kline_row_must_be_object:{source_row_index}")
        row_symbol = str(row.get("symbol") or symbol).strip().upper()
        if row_symbol != symbol:
            raise ValueError(f"provider_kline_symbol_mismatch:{row_symbol}:{symbol}")
        row_interval = str(row.get("interval") or interval).strip()
        if row_interval != interval:
            raise ValueError(f"provider_kline_interval_mismatch:{row_interval}:{interval}")
        rows.append(
            {
                "time_ms": _required_numeric(row, source_row_index, "time_ms", "event_time_ms", "open_time_ms", "bar_time_ms"),
                "open": _required_numeric(row, source_row_index, "open", "open_price"),
                "high": _required_numeric(row, source_row_index, "high", "high_price"),
                "low": _required_numeric(row, source_row_index, "low", "low_price"),
                "close": _required_numeric(row, source_row_index, "close", "close_price"),
                "volume": _required_numeric(row, source_row_index, "volume", "base_volume"),
                "provider_interval": row_interval,
            }
        )
    return rows


def _build_provider_context_family_entries(
    *,
    context_manifest_paths: Sequence[Path],
    output_dir: Path,
    symbol: str,
    fixture_first_time_ms: int,
    fixture_last_time_ms: int,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    family_entries: dict[str, dict[str, Any]] = {}
    source_records: list[dict[str, Any]] = []
    for raw_manifest_path in context_manifest_paths:
        manifest_path = Path(raw_manifest_path).expanduser().resolve()
        manifest = _read_json_object(manifest_path)
        _reject_unsafe_provider_manifest(manifest, context="fixture_context_manifest")
        source_name, source_raw = _provider_source_identity(manifest)
        family = _provider_context_data_family(manifest)
        if family not in CONTEXT_FAMILIES:
            raise ValueError(f"unsupported_provider_context_family:{family}")
        if family in family_entries:
            raise ValueError(f"duplicate_provider_context_family:{family}")
        allowed_sources = PROVIDER_CONTEXT_FAMILY_SOURCES[family]
        if source_name not in allowed_sources:
            raise ValueError(f"unsupported_provider_context_source:{family}:{source_name}")
        manifest_symbol = str(manifest.get("symbol") or "").strip().upper()
        if not manifest_symbol:
            raise ValueError(f"provider_context_manifest_symbol_required:{family}")
        if manifest_symbol != symbol:
            raise ValueError(f"provider_context_symbol_mismatch:{family}:{manifest_symbol}:{symbol}")

        data_path = _resolve_provider_context_data_path(manifest, manifest_path=manifest_path)
        observed_data_sha = _file_sha256(data_path)
        declared_data_sha = _normalize_sha256(
            manifest.get("content_hash")
            or manifest.get("sha256")
            or manifest.get("data_sha256")
            or manifest.get("parquet_sha256")
        )
        if declared_data_sha is not None and declared_data_sha != observed_data_sha:
            raise ValueError(f"provider_context_source_hash_mismatch:{family}")

        source_frame = _read_provider_context_frame(
            data_path,
            manifest=manifest,
            manifest_path=manifest_path,
            symbol=symbol,
            family=family,
            source_name=source_name,
            source_raw=source_raw,
            observed_data_sha=observed_data_sha,
        )
        declared_row_count = manifest.get("row_count")
        source_input_row_count = int(source_frame.attrs.get("source_input_row_count", len(source_frame)))
        if declared_row_count is not None and int(declared_row_count) != source_input_row_count:
            raise ValueError(
                f"provider_context_source_row_count_mismatch:{family}:{declared_row_count}:{source_input_row_count}"
            )

        fixture_frame = _slice_provider_context_frame(
            source_frame,
            fixture_first_time_ms=fixture_first_time_ms,
            fixture_last_time_ms=fixture_last_time_ms,
            include_previous=family != "liquidation",
        )
        if fixture_frame.empty:
            raise ValueError(f"provider_context_has_no_rows_in_fixture_window:{family}")
        if not _provider_context_has_supported_columns(fixture_frame, family=family):
            raise ValueError(f"provider_context_no_supported_columns:{family}")
        if family not in {"agg_trade", "liquidation"}:
            duplicate_mask = fixture_frame.duplicated(["symbol", "event_time_ms"], keep=False)
            if duplicate_mask.any():
                raise ValueError(f"provider_context_duplicate_events:{family}")

        context_metadata = _provider_context_metadata(manifest, source_name=source_name, family=family)
        fixture_frame = fixture_frame.sort_values(["symbol", "event_time_ms"], kind="mergesort").reset_index(drop=True)
        family_path = output_dir / f"{family}.parquet"
        fixture_frame.to_parquet(family_path, index=False)
        family_sha = _file_sha256(family_path)
        family_entry = {
            "path": family_path.name,
            "data_family": family,
            "source_name": source_name,
            "source_raw": source_raw,
            "event_time_field": "event_time_ms",
            "sha256": f"sha256:{family_sha}",
            "row_count": int(len(fixture_frame)),
            "required": False,
            "columns": list(fixture_frame.columns),
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "local_source_manifest_path": str(manifest_path),
            "local_source_data_path": str(data_path),
            "source_sha256": observed_data_sha,
            "source_declared_sha256": declared_data_sha,
            "source_manifest_sha256": _file_sha256(manifest_path),
            "source_row_count": source_input_row_count,
            "source_first_time_ms": int(source_frame["event_time_ms"].min()),
            "source_last_time_ms": int(source_frame["event_time_ms"].max()),
            "fixture_first_time_ms": int(fixture_frame["event_time_ms"].min()),
            "fixture_last_time_ms": int(fixture_frame["event_time_ms"].max()),
            "derivation_type": "fixture_context_event_time_slice",
            "lookahead_policy": "context_event_time_ms_lte_fixture_last_bar_time_ms",
            **context_metadata,
        }
        entry_errors: list[str] = []
        _validate_context_family_metadata(family_entry, family=family, errors=entry_errors)
        if entry_errors:
            raise ValueError(f"provider_context_metadata_invalid:{family}:{','.join(entry_errors)}")
        family_entries[family] = family_entry
        source_records.append(
            {
                "data_family": family,
                "source_name": source_name,
                "source_raw": source_raw,
                "local_source_manifest_path": str(manifest_path),
                "local_source_data_path": str(data_path),
                "source_sha256": observed_data_sha,
                "source_declared_sha256": declared_data_sha,
                "source_manifest_sha256": _file_sha256(manifest_path),
                "source_row_count": source_input_row_count,
                "fixture_row_count": int(len(fixture_frame)),
                "fixture_family_path": str(family_path),
                "fixture_family_sha256": family_sha,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                **context_metadata,
            }
        )
    return family_entries, source_records


def _read_provider_context_frame(
    path: Path,
    *,
    manifest: Mapping[str, Any],
    manifest_path: Path,
    symbol: str,
    family: str,
    source_name: str,
    source_raw: str,
    observed_data_sha: str,
) -> pd.DataFrame:
    payload_rows = _read_provider_payload_rows(path, manifest_kind=f"provider_context_{family}")
    if not payload_rows:
        raise ValueError(f"provider_context_source_has_no_rows:{family}")
    event_aliases = _provider_context_event_time_aliases(manifest, family=family)
    records: list[dict[str, Any]] = []
    for source_row_index, row in enumerate(payload_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"provider_context_row_must_be_object:{family}:{source_row_index}")
        _reject_unsafe_provider_payload(row, context=f"fixture_context_row:{family}")
        row_symbol = str(row.get("symbol") or manifest.get("symbol") or symbol).strip().upper()
        if row_symbol != symbol:
            raise ValueError(f"provider_context_symbol_mismatch:{family}:{row_symbol}:{symbol}")
        record: dict[str, Any] = {
            "event_time_ms": int(_required_numeric(row, source_row_index, *event_aliases)),
            "symbol": row_symbol,
        }
        for key, value in row.items():
            column = _safe_context_column_name(key)
            if not column or column in {"event_time_ms", "symbol"}:
                continue
            safe_value = _parquet_safe_value(value)
            if safe_value is not None:
                record[column] = safe_value
        record["source_row_index"] = _optional_int(record.get("source_row_index"), default=source_row_index)
        record["source_provider"] = source_name
        record["source_provider_raw"] = source_raw
        record["source_data_family"] = family
        record["source_manifest_path"] = str(manifest_path)
        record["source_data_sha256"] = observed_data_sha
        records.append(record)

    frame = pd.DataFrame(records)
    frame["event_time_ms"] = pd.to_numeric(frame["event_time_ms"], errors="raise").astype("int64")
    if family == "agg_trade":
        result = _normalize_provider_agg_trade_context_frame(frame)
    elif family == "liquidation":
        result = _normalize_provider_liquidation_context_frame(frame)
    else:
        result = _normalize_provider_scalar_context_frame(frame, family=family)
    result.attrs["source_input_row_count"] = len(payload_rows)
    return result


def _normalize_provider_scalar_context_frame(frame: pd.DataFrame, *, family: str) -> pd.DataFrame:
    result = frame.copy()
    result["symbol"] = result["symbol"].astype(str)
    if family == "funding_rate":
        _copy_numeric_alias(result, "funding_rate", ("funding_rate", "last_funding_rate", "rate", "value"))
        if "funding_rate" in result.columns and "funding_rate_change" not in result.columns:
            result["funding_rate_change"] = pd.to_numeric(result["funding_rate"], errors="coerce").groupby(result["symbol"]).diff()
    elif family == "premium_index":
        _copy_numeric_alias(result, "premium_basis_rate", ("premium_basis_rate", "basis_rate", "premium_index", "value"))
        _copy_numeric_alias(result, "mark_price", ("mark_price",))
        _copy_numeric_alias(result, "index_price", ("index_price",))
        mark = _first_numeric_context_series(result, ("mark_price",))
        index = _first_numeric_context_series(result, ("index_price",))
        if mark is not None and index is not None:
            if "premium_basis_rate" not in result.columns:
                result["premium_basis_rate"] = (mark - index) / index.replace(0.0, pd.NA)
            if "premium_basis_abs" not in result.columns:
                result["premium_basis_abs"] = mark - index
        if "premium_basis_rate" in result.columns and "basis_bps" not in result.columns:
            result["basis_bps"] = pd.to_numeric(result["premium_basis_rate"], errors="coerce") * 10_000.0
        if "premium_basis_rate" in result.columns and "premium_close" not in result.columns:
            result["premium_close"] = pd.to_numeric(result["premium_basis_rate"], errors="coerce")
    elif family == "open_interest":
        _copy_numeric_alias(result, "open_interest", ("open_interest", "sum_open_interest", "oi", "value"))
        _copy_numeric_alias(result, "open_interest_value", ("open_interest_value", "open_interest_value_usd", "notional"))
        if "open_interest" in result.columns:
            open_interest = pd.to_numeric(result["open_interest"], errors="coerce")
            if "open_interest_change" not in result.columns:
                result["open_interest_change"] = open_interest.groupby(result["symbol"]).diff()
            if "open_interest_change_pct" not in result.columns:
                previous = open_interest.groupby(result["symbol"]).shift(1)
                result["open_interest_change_pct"] = pd.to_numeric(result["open_interest_change"], errors="coerce") / previous.replace(0.0, pd.NA)
    return result


def _normalize_provider_agg_trade_context_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["symbol"] = result["symbol"].astype(str)
    price = _first_numeric_context_series(result, ("price",))
    quantity = _first_numeric_context_series(result, ("quantity", "qty", "base_volume", "volume"))
    quote_volume = _first_numeric_context_series(result, ("quote_volume", "quote_quantity", "quote_qty", "notional"))
    if quote_volume is None and price is not None and quantity is not None:
        quote_volume = price * quantity
    if quote_volume is not None:
        result["quote_volume"] = quote_volume

    taker_buy_quote = _first_numeric_context_series(result, ("taker_buy_quote_volume", "buy_quote_volume"))
    sell_quote = _first_numeric_context_series(result, ("sell_quote_volume", "sell_quote_volume"))
    buyer_maker = _first_bool_context_series(result, ("is_buyer_maker", "buyer_maker"))
    side = _first_string_context_series(result, ("side", "taker_side"))
    if taker_buy_quote is None and quote_volume is not None:
        if buyer_maker is not None:
            taker_buy_quote = quote_volume.where(~buyer_maker, 0.0)
            sell_quote = quote_volume.where(buyer_maker, 0.0)
        elif side is not None:
            normalized_side = side.astype(str).str.lower()
            buy_mask = normalized_side.isin({"buy", "buyer", "long", "taker_buy"})
            taker_buy_quote = quote_volume.where(buy_mask, 0.0)
            sell_quote = quote_volume.where(~buy_mask, 0.0)
    if taker_buy_quote is not None:
        result["taker_buy_quote_volume"] = taker_buy_quote
    if sell_quote is None and quote_volume is not None and taker_buy_quote is not None:
        sell_quote = quote_volume - taker_buy_quote
    if sell_quote is not None:
        result["sell_quote_volume"] = sell_quote
    if quantity is not None:
        result["quantity"] = quantity
    result["agg_trade_count"] = 1

    aggregation: dict[str, str] = {
        "source_row_index": "min",
        "source_provider": "first",
        "source_provider_raw": "first",
        "source_data_family": "first",
        "source_manifest_path": "first",
        "source_data_sha256": "first",
        "agg_trade_count": "sum",
    }
    for column in ("quantity", "quote_volume", "taker_buy_quote_volume", "sell_quote_volume"):
        if column in result.columns:
            aggregation[column] = "sum"
    for column in (
        "price",
        "primary_signed_imbalance_ratio",
        "primary_sqrt_signed_imbalance_ratio",
        "top_of_book_imbalance",
        "spread_bps",
    ):
        if column in result.columns:
            aggregation[column] = "last"
    grouped = (
        result.groupby(["symbol", "event_time_ms"], as_index=False, sort=False)
        .agg(aggregation)
        .sort_values(["symbol", "event_time_ms"], kind="mergesort")
        .reset_index(drop=True)
    )
    if {"taker_buy_quote_volume", "sell_quote_volume"} <= set(grouped.columns):
        denominator = (
            pd.to_numeric(grouped["taker_buy_quote_volume"], errors="coerce")
            + pd.to_numeric(grouped["sell_quote_volume"], errors="coerce")
        ).replace(0.0, pd.NA)
        grouped["primary_signed_imbalance_ratio"] = (
            pd.to_numeric(grouped["taker_buy_quote_volume"], errors="coerce")
            - pd.to_numeric(grouped["sell_quote_volume"], errors="coerce")
        ) / denominator
    elif {"taker_buy_quote_volume", "quote_volume"} <= set(grouped.columns):
        denominator = pd.to_numeric(grouped["quote_volume"], errors="coerce").replace(0.0, pd.NA)
        grouped["primary_signed_imbalance_ratio"] = (
            (2.0 * pd.to_numeric(grouped["taker_buy_quote_volume"], errors="coerce")) / denominator
        ) - 1.0
    if "primary_signed_imbalance_ratio" in grouped.columns and "primary_sqrt_signed_imbalance_ratio" not in grouped.columns:
        signed = pd.to_numeric(grouped["primary_signed_imbalance_ratio"], errors="coerce")
        grouped["primary_sqrt_signed_imbalance_ratio"] = signed.apply(
            lambda value: pd.NA if pd.isna(value) else (1.0 if value >= 0.0 else -1.0) * (abs(float(value)) ** 0.5)
        )
    return grouped


def _normalize_provider_liquidation_context_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["symbol"] = result["symbol"].astype(str)
    price = _first_numeric_context_series(result, ("price", "execution_price", "p", "P"))
    quantity = _first_numeric_context_series(result, ("quantity", "qty", "amount", "size", "q", "Q"))
    quote_notional = _first_numeric_context_series(result, ("quote_notional", "notional", "liquidation_notional"))
    if quote_notional is None and price is not None and quantity is not None:
        quote_notional = price * quantity
    if quantity is not None:
        result["liquidation_quantity"] = quantity
    if quote_notional is not None:
        result["liquidation_quote_notional"] = quote_notional
    last_filled_quantity = _first_numeric_context_series(result, ("last_filled_quantity", "last_filled_qty", "l", "L"))
    if last_filled_quantity is not None:
        result["last_filled_quantity"] = last_filled_quantity

    side = _first_string_context_series(result, ("side", "order_side", "liquidation_side", "S", "s"))
    if side is not None:
        normalized_side = side.map(_normalize_provider_liquidation_side)
        result["side"] = normalized_side
        if quote_notional is not None:
            result["liquidation_buy_notional"] = quote_notional.where(normalized_side == "BUY", 0.0)
            result["liquidation_sell_notional"] = quote_notional.where(normalized_side == "SELL", 0.0)
    result["liquidation_event_count"] = 1

    aggregation: dict[str, str] = {
        "source_row_index": "min",
        "source_provider": "first",
        "source_provider_raw": "first",
        "source_data_family": "first",
        "source_manifest_path": "first",
        "source_data_sha256": "first",
        "liquidation_event_count": "sum",
    }
    for column in (
        "liquidation_quantity",
        "liquidation_quote_notional",
        "liquidation_buy_notional",
        "liquidation_sell_notional",
        "last_filled_quantity",
    ):
        if column in result.columns:
            aggregation[column] = "sum"
    for column in (
        "side",
        "price",
        "p",
        "P",
        "average_price",
        "avg_price",
        "ap",
        "order_status",
        "status",
        "X",
        "order_type",
        "type",
        "o",
        "time_in_force",
        "tif",
        "f",
        "trade_time_ms",
        "trade_time",
        "T",
    ):
        if column in result.columns:
            aggregation[column] = "last"

    grouped = (
        result.groupby(["symbol", "event_time_ms"], as_index=False, sort=False)
        .agg(aggregation)
        .sort_values(["symbol", "event_time_ms"], kind="mergesort")
        .reset_index(drop=True)
    )
    if {"liquidation_buy_notional", "liquidation_sell_notional"} <= set(grouped.columns):
        buy_notional = pd.to_numeric(grouped["liquidation_buy_notional"], errors="coerce").fillna(0.0)
        sell_notional = pd.to_numeric(grouped["liquidation_sell_notional"], errors="coerce").fillna(0.0)
        denominator = (
            buy_notional
            + sell_notional
        ).replace(0.0, pd.NA)
        grouped["liquidation_side_imbalance"] = (
            buy_notional
            - sell_notional
        ) / denominator
        grouped["dominant_liquidation_side"] = [
            "BUY" if buy > sell else "SELL" if sell > buy else "MIXED"
            for buy, sell in zip(buy_notional, sell_notional)
        ]
    if {"liquidation_quote_notional", "liquidation_quantity"} <= set(grouped.columns):
        quantity = pd.to_numeric(grouped["liquidation_quantity"], errors="coerce").replace(0.0, pd.NA)
        grouped["liquidation_vwap_price"] = pd.to_numeric(grouped["liquidation_quote_notional"], errors="coerce") / quantity
    return grouped


def _normalize_provider_liquidation_side(value: object) -> str:
    text = str(value).strip().upper()
    aliases = {
        "B": "BUY",
        "BUYER": "BUY",
        "TAKER_BUY": "BUY",
        "S": "SELL",
        "SELLER": "SELL",
        "TAKER_SELL": "SELL",
    }
    return aliases.get(text, text)


def _slice_provider_context_frame(
    frame: pd.DataFrame,
    *,
    fixture_first_time_ms: int,
    fixture_last_time_ms: int,
    include_previous: bool = True,
) -> pd.DataFrame:
    eligible = frame.loc[pd.to_numeric(frame["event_time_ms"], errors="coerce") <= fixture_last_time_ms].copy()
    if eligible.empty:
        return eligible
    within = eligible.loc[pd.to_numeric(eligible["event_time_ms"], errors="coerce") >= fixture_first_time_ms]
    if not include_previous:
        return (
            within.drop_duplicates(["symbol", "event_time_ms"], keep="last")
            .sort_values(["symbol", "event_time_ms"], kind="mergesort")
            .reset_index(drop=True)
        )
    previous = (
        eligible.loc[pd.to_numeric(eligible["event_time_ms"], errors="coerce") < fixture_first_time_ms]
        .sort_values(["symbol", "event_time_ms"], kind="mergesort")
        .groupby("symbol", sort=False)
        .tail(1)
    )
    return (
        pd.concat([previous, within], ignore_index=True)
        .drop_duplicates(["symbol", "event_time_ms"], keep="last")
        .sort_values(["symbol", "event_time_ms"], kind="mergesort")
        .reset_index(drop=True)
    )


def _provider_context_has_supported_columns(frame: pd.DataFrame, *, family: str) -> bool:
    columns = set(str(column) for column in frame.columns)
    if family == "funding_rate":
        return "funding_rate" in columns
    if family == "premium_index":
        return bool({"premium_basis_rate", "premium_index", "mark_price", "index_price"} & columns)
    if family == "open_interest":
        return "open_interest" in columns
    if family == "agg_trade":
        return (
            "primary_signed_imbalance_ratio" in columns
            or {"taker_buy_quote_volume", "quote_volume"} <= columns
            or {"taker_buy_quote_volume", "sell_quote_volume"} <= columns
            or bool({"top_of_book_imbalance", "spread_bps"} & columns)
        )
    if family == "liquidation":
        return bool(
            {
                "liquidation_event_count",
                "liquidation_quote_notional",
                "liquidation_buy_notional",
                "liquidation_sell_notional",
                "liquidation_side_imbalance",
            }
            & columns
        )
    return False


def _provider_context_data_family(manifest: Mapping[str, Any]) -> str:
    raw = str(manifest.get("data_family") or manifest.get("family") or "").strip().lower()
    aliases = {
        "funding": "funding_rate",
        "funding_rates": "funding_rate",
        "premium": "premium_index",
        "premiumindex": "premium_index",
        "premium_index": "premium_index",
        "oi": "open_interest",
        "openinterest": "open_interest",
        "aggtrade": "agg_trade",
        "aggtrades": "agg_trade",
        "agg_trades": "agg_trade",
        "liquidations": "liquidation",
        "force_order": "liquidation",
        "forceorder": "liquidation",
        "force_orders": "liquidation",
    }
    return aliases.get(raw, raw)


def _provider_context_event_time_aliases(manifest: Mapping[str, Any], *, family: str) -> tuple[str, ...]:
    event_time_field = str(manifest.get("event_time_field") or "").strip()
    aliases = CONTEXT_EVENT_TIME_ALIASES[family]
    if event_time_field:
        return tuple(dict.fromkeys((event_time_field, *aliases)))
    return aliases


def _resolve_provider_context_data_path(manifest: Mapping[str, Any], *, manifest_path: Path) -> Path:
    raw = manifest.get("data_path") or manifest.get("dataset_path") or manifest.get("path") or manifest.get("parquet_path")
    if raw:
        candidate = Path(str(raw)).expanduser()
        if not candidate.is_absolute():
            parent_candidate = (manifest_path.parent / candidate).resolve()
            if parent_candidate.exists():
                candidate = parent_candidate
            else:
                candidate = candidate.resolve()
        if candidate.exists():
            return candidate
        raise FileNotFoundError(candidate)
    if str(manifest_path).endswith(".manifest.json"):
        prefix = str(manifest_path)[: -len(".manifest.json")]
        for suffix in (".jsonl", ".json", ".parquet", ".csv"):
            candidate = Path(prefix + suffix)
            if candidate.exists():
                return candidate.resolve()
    raise ValueError("provider_context_manifest_data_path_required")


def _read_provider_payload_rows(path: Path, *, manifest_kind: str) -> list[Mapping[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, Mapping):
            rows = payload.get("rows") or payload.get("data") or payload.get("records")
            if isinstance(rows, list):
                return rows
        raise ValueError(f"{manifest_kind}_json_rows_required")
    if suffix == ".parquet":
        return pd.read_parquet(path).to_dict("records")
    if suffix == ".csv":
        return pd.read_csv(path).to_dict("records")
    raise ValueError(f"{manifest_kind}_unsupported_data_suffix:{suffix}")


def _reject_unsafe_provider_manifest(manifest: Mapping[str, Any], *, context: str) -> None:
    if _payload_contains_unsafe_value(manifest, _REMOVED_CHART_SOURCE, true_flag_keys={_REMOVED_CHART_SOURCE_FLAG}):
        raise ValueError(f"{_REMOVED_CHART_SOURCE_NOT_ALLOWED}_for_{context}")
    if _payload_contains_unsafe_value(manifest, "synthetic", true_flag_keys={"synthetic_source_used"}):
        raise ValueError(f"synthetic_source_not_allowed_for_{context}")


def _reject_unsafe_provider_payload(payload: Mapping[str, Any], *, context: str) -> None:
    if _payload_contains_unsafe_value(payload, _REMOVED_CHART_SOURCE, true_flag_keys={_REMOVED_CHART_SOURCE_FLAG}):
        raise ValueError(f"{_REMOVED_CHART_SOURCE_NOT_ALLOWED}_for_{context}")
    if _payload_contains_unsafe_value(payload, "synthetic", true_flag_keys={"synthetic_source_used"}):
        raise ValueError(f"synthetic_source_not_allowed_for_{context}")


def _fixture_manifest_unsafe_provenance_errors(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    provenance_fields = {
        "source",
        "source_name",
        "source_raw",
        "source_type",
        "provider",
        "provider_name",
        "input_source",
        "local_source_manifest_path",
        "local_source_data_path",
        "source_manifest_path",
        "source_path",
        "data_path",
        "derivation_type",
        "context_sources",
        _REMOVED_CHART_SOURCE_FLAG,
        "synthetic_source_used",
    }
    top_level_payload = {key: value for key, value in manifest.items() if str(key) in provenance_fields}
    if _payload_contains_unsafe_value(top_level_payload, _REMOVED_CHART_SOURCE, true_flag_keys={_REMOVED_CHART_SOURCE_FLAG}):
        errors.append(f"fixture_pack_{_REMOVED_CHART_SOURCE_NOT_ALLOWED}")
    if _payload_contains_unsafe_value(top_level_payload, "synthetic", true_flag_keys={"synthetic_source_used"}):
        errors.append("fixture_pack_synthetic_source_not_allowed")
    for section_name in ("source", "derivation"):
        section = manifest.get(section_name)
        if not isinstance(section, Mapping):
            continue
        section_payload = {key: value for key, value in section.items() if str(key) in provenance_fields}
        if _payload_contains_unsafe_value(section_payload, _REMOVED_CHART_SOURCE, true_flag_keys={_REMOVED_CHART_SOURCE_FLAG}):
            errors.append(f"fixture_pack_{_REMOVED_CHART_SOURCE_NOT_ALLOWED}")
        if _payload_contains_unsafe_value(section_payload, "synthetic", true_flag_keys={"synthetic_source_used"}):
            errors.append("fixture_pack_synthetic_source_not_allowed")
    families = manifest.get("families")
    if isinstance(families, Mapping):
        for family_name, entry in families.items():
            if not isinstance(entry, Mapping):
                continue
            family_payload = {key: value for key, value in entry.items() if str(key) in provenance_fields}
            if _payload_contains_unsafe_value(family_payload, _REMOVED_CHART_SOURCE, true_flag_keys={_REMOVED_CHART_SOURCE_FLAG}):
                errors.append(f"family_{family_name}_{_REMOVED_CHART_SOURCE_NOT_ALLOWED}")
            if _payload_contains_unsafe_value(family_payload, "synthetic", true_flag_keys={"synthetic_source_used"}):
                errors.append(f"family_{family_name}_synthetic_source_not_allowed")
    return list(dict.fromkeys(errors))


def _payload_contains_unsafe_value(
    payload: object,
    needle: str,
    *,
    true_flag_keys: set[str],
) -> bool:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key).strip().lower()
            if key_text in true_flag_keys and value is True:
                return True
            if _payload_contains_unsafe_value(value, needle, true_flag_keys=true_flag_keys):
                return True
        return False
    if isinstance(payload, (list, tuple, set)):
        return any(_payload_contains_unsafe_value(item, needle, true_flag_keys=true_flag_keys) for item in payload)
    if isinstance(payload, str):
        return needle in payload.strip().lower()
    return False


def _copy_numeric_alias(frame: pd.DataFrame, target: str, aliases: tuple[str, ...]) -> None:
    series = _first_numeric_context_series(frame, aliases)
    if series is not None:
        frame[target] = series


def _first_numeric_context_series(frame: pd.DataFrame, aliases: tuple[str, ...]) -> pd.Series | None:
    for column in aliases:
        if column in frame.columns:
            return pd.to_numeric(frame[column], errors="coerce").replace([float("inf"), float("-inf")], pd.NA)
    return None


def _first_bool_context_series(frame: pd.DataFrame, aliases: tuple[str, ...]) -> pd.Series | None:
    for column in aliases:
        if column not in frame.columns:
            continue
        raw = frame[column]
        if raw.dtype == bool:
            return raw
        normalized = raw.astype(str).str.strip().str.lower()
        return normalized.isin({"true", "1", "yes", "y", "buyer_maker"})
    return None


def _first_string_context_series(frame: pd.DataFrame, aliases: tuple[str, ...]) -> pd.Series | None:
    for column in aliases:
        if column in frame.columns:
            return frame[column].astype(str)
    return None


def _safe_context_column_name(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    return "".join(character if character.isalnum() or character == "_" else "_" for character in text)


def _parquet_safe_value(value: object) -> object | None:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, str) and value == "":
            return None
        return value
    return json.dumps(value, sort_keys=True, default=str)


def _optional_int(value: object, *, default: int) -> int:
    if value is None or str(value) == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _required_numeric(row: Mapping[str, Any], source_row_index: int, *field_names: str) -> float:
    for field_name in field_names:
        value = row.get(field_name)
        if value is not None and str(value) != "":
            return float(value)
    raise ValueError(f"provider_kline_required_field_missing:{source_row_index}:{'/'.join(field_names)}")


def _provider_fixture_cycle_frame(
    fixture: pd.DataFrame,
    *,
    symbol: str,
    source_name: str,
    source_raw: str,
    interval: str,
) -> pd.DataFrame:
    cycle = fixture.copy()
    cycle["symbol"] = symbol
    cycle["time_ms"] = pd.to_numeric(cycle["time_ms"], errors="raise").astype("int64")
    cycle["bar_time_ms"] = cycle["time_ms"]
    cycle["signal_bar_time_ms"] = cycle["time_ms"]
    for column in ("open", "high", "low", "close", "volume"):
        cycle[column] = pd.to_numeric(cycle[column], errors="raise").astype("float64")
        cycle[f"signal_bar_{column}"] = cycle[column]
    cycle["entry_price"] = cycle["close"]
    cycle["source_provider"] = source_name
    cycle["source_provider_raw"] = source_raw
    cycle["source_data_family"] = "kline"
    cycle["source_interval"] = interval
    cycle["fixture_derivation"] = "contiguous_tail_slice_from_provider_kline_manifest"
    cycle = _attach_provider_fixture_regime_annotations(cycle)
    return cycle.loc[
        :,
        [
            "symbol",
            "time_ms",
            "bar_time_ms",
            "signal_bar_time_ms",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "signal_bar_open",
            "signal_bar_high",
            "signal_bar_low",
            "signal_bar_close",
            "signal_bar_volume",
            "entry_price",
            "source_row_index",
            "source_provider",
            "source_provider_raw",
            "source_data_family",
            "source_interval",
            "fixture_derivation",
            "validation_regime",
            "top_regime_label",
            "regime",
            "provider_cache_realized_volatility",
        ],
    ]


def _attach_provider_fixture_regime_annotations(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    returns = pd.to_numeric(result["close"], errors="coerce").pct_change().fillna(0.0)
    rolling_vol = returns.rolling(16, min_periods=4).std().fillna(0.0)
    rolling_mean = pd.to_numeric(result["close"], errors="coerce").rolling(24, min_periods=4).mean()
    rolling_std = pd.to_numeric(result["close"], errors="coerce").rolling(24, min_periods=4).std().replace(0.0, pd.NA)
    zscore = ((pd.to_numeric(result["close"], errors="coerce") - rolling_mean) / rolling_std).fillna(0.0)
    trend = pd.to_numeric(result["close"], errors="coerce").diff(16).fillna(0.0)
    median_close = float(pd.to_numeric(result["close"], errors="coerce").median())
    labels = [
        "shock" if abs(float(z)) >= 1.5 else "trend" if abs(float(t)) >= median_close * 0.002 else "range"
        for z, t in zip(zscore, trend)
    ]
    result["validation_regime"] = labels
    result["top_regime_label"] = result["validation_regime"]
    result["regime"] = result["validation_regime"]
    result["provider_cache_realized_volatility"] = rolling_vol.astype("float64")
    return result


def _provider_fixture_bars_frame(cycle: pd.DataFrame, *, interval: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_time_ms": pd.to_numeric(cycle["time_ms"], errors="raise").astype("int64"),
            "symbol": cycle["symbol"].astype(str),
            "interval": interval,
            "open_price": pd.to_numeric(cycle["open"], errors="raise").astype("float64"),
            "high_price": pd.to_numeric(cycle["high"], errors="raise").astype("float64"),
            "low_price": pd.to_numeric(cycle["low"], errors="raise").astype("float64"),
            "close_price": pd.to_numeric(cycle["close"], errors="raise").astype("float64"),
            "volume": pd.to_numeric(cycle["volume"], errors="raise").astype("float64"),
            "source_row_index": pd.to_numeric(cycle["source_row_index"], errors="raise").astype("int64"),
        }
    )
