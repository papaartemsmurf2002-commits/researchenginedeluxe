from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from tradingbotsuite.research.archive_sources import (
    ACCOUNT_EXECUTION_FIELD_NAMES,
    ARCHIVE_SOURCE_CONTRACT_VERSION,
    BOOK_FIELD_NAMES,
    CANONICAL_DATA_FAMILIES,
    PROTECTED_MISSINGNESS_FIELDS,
    ArchiveNormalizedFieldContract,
    canonical_data_family,
    get_normalized_field_contract,
)

DATA_MANIFEST_VERSION = "data-manifest-v1"
DATA_SCHEMA_VERSION = "family-schema-v1"
DATA_PROVIDER_CAPABILITY_REGISTRY_VERSION = "provider-capability-registry-v1"

SUPPORTED_SOURCE_NAMES = (
    "binance_rest",
    "binance_vision",
    "bybit_archive",
    "crypto_lake",
    "hyperliquid_archive",
)

SOURCE_TYPES_BY_NAME = {
    "binance_rest": "rest",
    "binance_vision": "archive",
    "bybit_archive": "local_file",
    "crypto_lake": "local_file",
    "hyperliquid_archive": "local_file",
}

REQUIRED_DATA_MANIFEST_FIELDS = (
    "manifest_version",
    "research_only",
    "source_name",
    "source_type",
    "symbol",
    "data_family",
    "event_time_field",
    "start_time_ms",
    "end_time_ms",
    "row_count",
    "schema_version",
    "content_hash",
    "normalized_fields",
    "missing_fields",
    "quality_flags",
    "non_promotable_reasons",
)
RESERVED_DATA_MANIFEST_FIELDS = frozenset(
    {
        *REQUIRED_DATA_MANIFEST_FIELDS,
        "observe_only",
        "promotion_ready",
        "provider_capability",
    }
)
BROAD_CONTEXT_COVERAGE_SCOPES = frozenset({"multi_year", "full_history", "broad_historical", "oos_stress_coverage"})
LATEST_WINDOW_CONTEXT_SOURCE_NAMES = frozenset({"binance_usdm_rest"})


@dataclass(frozen=True, slots=True)
class DataSourceDescriptor:
    source_name: str
    source_type: str
    display_name: str
    data_families: tuple[str, ...]
    implemented_for_ingestion: bool
    diagnostic_only_by_default: bool
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DataProviderCapability:
    source_name: str
    data_family: str
    durability_class: str
    retention_limit: str
    history_start: str | None
    exchange_native: bool
    normalized: bool
    health_policy: str
    diagnostic_only_by_default: bool
    candidate_ready_default: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "registry_version": DATA_PROVIDER_CAPABILITY_REGISTRY_VERSION,
            "source_name": self.source_name,
            "data_family": self.data_family,
            "durability_class": self.durability_class,
            "retention_limit": self.retention_limit,
            "history_start": self.history_start,
            "exchange_native": self.exchange_native,
            "normalized": self.normalized,
            "health_policy": self.health_policy,
            "diagnostic_only_by_default": self.diagnostic_only_by_default,
            "candidate_ready_default": self.candidate_ready_default,
        }


@dataclass(frozen=True, slots=True)
class DataManifestValidation:
    valid: bool
    promotable: bool
    point_in_time_compatible: bool
    source_name: str | None
    source_type: str | None
    symbol: str | None
    data_family: str | None
    errors: tuple[str, ...]
    quality_flags: tuple[str, ...]
    missing_fields: tuple[str, ...]


DATA_SOURCE_DESCRIPTORS: dict[str, DataSourceDescriptor] = {
    "binance_rest": DataSourceDescriptor(
        source_name="binance_rest",
        source_type="rest",
        display_name="Binance USD-M REST",
        data_families=("kline",),
        implemented_for_ingestion=True,
        diagnostic_only_by_default=False,
        notes=(
            "REST historical bars are research-only and can support completed-bar replay.",
            "REST collection time is not a substitute for original live receive time.",
        ),
    ),
    "binance_vision": DataSourceDescriptor(
        source_name="binance_vision",
        source_type="archive",
        display_name="Binance Vision",
        data_families=("agg_trade", "trade", "kline", "premium_index", "funding_rate", "open_interest", "book_ticker", "depth_snapshot", "liquidation"),
        implemented_for_ingestion=True,
        diagnostic_only_by_default=True,
        notes=("Public archive rows are diagnostic unless receive-time evidence is available.",),
    ),
    "crypto_lake": DataSourceDescriptor(
        source_name="crypto_lake",
        source_type="local_file",
        display_name="Crypto Lake",
        data_families=("trade", "agg_trade", "book_ticker", "depth_snapshot", "kline", "funding_rate", "open_interest", "liquidation"),
        implemented_for_ingestion=True,
        diagnostic_only_by_default=True,
        notes=("Vendor-normalized rows must preserve explicit missingness.",),
    ),
    "bybit_archive": DataSourceDescriptor(
        source_name="bybit_archive",
        source_type="local_file",
        display_name="Bybit Archive",
        data_families=("trade", "kline", "funding_rate", "open_interest", "premium_index", "book_ticker", "depth_snapshot", "liquidation"),
        implemented_for_ingestion=False,
        diagnostic_only_by_default=True,
        notes=(
            "Registered-only until Bybit archive download/local export ingestion is normalized and validated.",
            "Historical downloads or REST backfills must not be treated as live receive-time evidence.",
        ),
    ),
    "hyperliquid_archive": DataSourceDescriptor(
        source_name="hyperliquid_archive",
        source_type="local_file",
        display_name="Hyperliquid Archive",
        data_families=("trade", "depth_snapshot", "book_ticker", "funding_rate", "user_fill", "user_funding", "order_event", "position_snapshot"),
        implemented_for_ingestion=False,
        diagnostic_only_by_default=True,
        notes=("Registered-only until archive ingestion is reconciled with local account journals.",),
    ),
}


def _capability(
    source_name: str,
    data_family: str,
    *,
    durability_class: str,
    retention_limit: str,
    history_start: str | None,
    exchange_native: bool,
    normalized: bool,
    health_policy: str,
    diagnostic_only_by_default: bool,
    candidate_ready_default: bool,
) -> DataProviderCapability:
    return DataProviderCapability(
        source_name=source_name,
        data_family=canonical_data_family(data_family),
        durability_class=durability_class,
        retention_limit=retention_limit,
        history_start=history_start,
        exchange_native=exchange_native,
        normalized=normalized,
        health_policy=health_policy,
        diagnostic_only_by_default=diagnostic_only_by_default,
        candidate_ready_default=candidate_ready_default,
    )


DATA_PROVIDER_CAPABILITIES: dict[tuple[str, str], DataProviderCapability] = {
    ("binance_rest", "kline"): _capability(
        "binance_rest",
        "kline",
        durability_class="direct_rest_backfill",
        retention_limit="exchange_endpoint_dependent_not_vendor_archive",
        history_start=None,
        exchange_native=True,
        normalized=True,
        health_policy="receive_time_unavailable_non_promotable",
        diagnostic_only_by_default=False,
        candidate_ready_default=False,
    ),
    **{
        ("binance_usdm_rest", family): _capability(
            "binance_usdm_rest",
            family,
            durability_class="latest_window_rest",
            retention_limit="direct_endpoint_latest_window",
            history_start=None,
            exchange_native=True,
            normalized=True,
            health_policy="latest_window_only_diagnostic_no_multi_year_claim",
            diagnostic_only_by_default=True,
            candidate_ready_default=False,
        )
        for family in ("funding_rate", "premium_index", "open_interest")
    },
    **{
        ("binance_vision", family): _capability(
            "binance_vision",
            family,
            durability_class="public_archive_partition",
            retention_limit="downloaded_public_archive_partition",
            history_start="source_partition_dependent",
            exchange_native=True,
            normalized=True,
            health_policy="checksum_gap_duplicate_evidence_required_for_durable_claims",
            diagnostic_only_by_default=True,
            candidate_ready_default=False,
        )
        for family in (
            "agg_trade",
            "trade",
            "kline",
            "premium_index",
            "funding_rate",
            "open_interest",
            "book_ticker",
            "depth_snapshot",
            "liquidation",
        )
    },
    **{
        ("crypto_lake", family): _capability(
            "crypto_lake",
            family,
            durability_class="local_vendor_export",
            retention_limit="local_export_or_free_sample",
            history_start="local_export_metadata_required",
            exchange_native=False,
            normalized=True,
            health_policy="explicit_missingness_and_source_health_required",
            diagnostic_only_by_default=True,
            candidate_ready_default=False,
        )
        for family in (
            "trade",
            "agg_trade",
            "book_ticker",
            "depth_snapshot",
            "kline",
            "funding_rate",
            "open_interest",
            "liquidation",
        )
    },
    **{
        ("bybit_archive", family): _capability(
            "bybit_archive",
            family,
            durability_class="registered_only",
            retention_limit="ingestion_not_implemented",
            history_start=None,
            exchange_native=True,
            normalized=False,
            health_policy="registered_only_no_claims",
            diagnostic_only_by_default=True,
            candidate_ready_default=False,
        )
        for family in (
            "trade",
            "kline",
            "funding_rate",
            "open_interest",
            "premium_index",
            "book_ticker",
            "depth_snapshot",
            "liquidation",
        )
    },
    **{
        ("hyperliquid_archive", family): _capability(
            "hyperliquid_archive",
            family,
            durability_class="registered_only",
            retention_limit="ingestion_not_implemented",
            history_start=None,
            exchange_native=True,
            normalized=False,
            health_policy="registered_only_no_claims",
            diagnostic_only_by_default=True,
            candidate_ready_default=False,
        )
        for family in (
            "trade",
            "depth_snapshot",
            "book_ticker",
            "funding_rate",
            "user_fill",
            "user_funding",
            "order_event",
            "position_snapshot",
        )
    },
}


def data_source_descriptors() -> tuple[DataSourceDescriptor, ...]:
    return tuple(DATA_SOURCE_DESCRIPTORS[name] for name in SUPPORTED_SOURCE_NAMES)


def data_provider_capabilities() -> tuple[DataProviderCapability, ...]:
    return tuple(
        DATA_PROVIDER_CAPABILITIES[key]
        for key in sorted(DATA_PROVIDER_CAPABILITIES)
    )


def provider_capability_payload(
    *,
    source_name: str,
    data_family: str,
    source_access_mode: str | None = None,
    latest_window_only: bool | None = None,
    coverage_scope: str | None = None,
) -> dict[str, Any]:
    canonical_family = canonical_data_family(data_family)
    normalized_source = str(source_name or "").strip()
    capability = DATA_PROVIDER_CAPABILITIES.get((normalized_source, canonical_family))
    if capability is None:
        capability = DataProviderCapability(
            source_name=normalized_source,
            data_family=canonical_family,
            durability_class="unknown_source_capability",
            retention_limit="unknown",
            history_start=None,
            exchange_native=False,
            normalized=False,
            health_policy="unsupported_source_or_family_no_claims",
            diagnostic_only_by_default=True,
            candidate_ready_default=False,
        )
    if source_access_mode == "free_sample":
        capability = DataProviderCapability(
            source_name=normalized_source,
            data_family=canonical_family,
            durability_class="free_sample_diagnostic",
            retention_limit="sample_coverage_only",
            history_start=None,
            exchange_native=capability.exchange_native,
            normalized=capability.normalized,
            health_policy="free_sample_diagnostic_only_no_durable_claim",
            diagnostic_only_by_default=True,
            candidate_ready_default=False,
        )
    elif latest_window_only is True or normalized_source in LATEST_WINDOW_CONTEXT_SOURCE_NAMES:
        capability = DataProviderCapability(
            source_name=normalized_source,
            data_family=canonical_family,
            durability_class="latest_window_rest",
            retention_limit="direct_endpoint_latest_window",
            history_start=None,
            exchange_native=capability.exchange_native,
            normalized=capability.normalized,
            health_policy="latest_window_only_diagnostic_no_multi_year_claim",
            diagnostic_only_by_default=True,
            candidate_ready_default=False,
        )
    payload = capability.to_payload()
    if coverage_scope is not None:
        payload["coverage_scope"] = coverage_scope
    return payload


def data_family_contracts() -> tuple[ArchiveNormalizedFieldContract, ...]:
    return tuple(get_normalized_field_contract(family) for family in CANONICAL_DATA_FAMILIES)


def build_data_manifest(
    *,
    source_name: str,
    source_type: str,
    symbol: str,
    data_family: str,
    event_time_field: str,
    receive_time_field: str | None,
    receive_time_unavailable_reason: str | None,
    start_time_ms: int,
    end_time_ms: int,
    row_count: int,
    content_hash: str,
    normalized_fields: list[str] | tuple[str, ...],
    missing_fields: list[str] | tuple[str, ...] = (),
    quality_flags: list[str] | tuple[str, ...] = (),
    non_promotable_reasons: list[str] | tuple[str, ...] = (),
    schema_version: str = DATA_SCHEMA_VERSION,
    data_path: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "manifest_version": DATA_MANIFEST_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "source_name": source_name,
        "source_type": source_type,
        "symbol": symbol.strip().upper(),
        "data_family": canonical_data_family(data_family),
        "event_time_field": event_time_field,
        "receive_time_field": receive_time_field,
        "receive_time_unavailable_reason": receive_time_unavailable_reason,
        "start_time_ms": int(start_time_ms),
        "end_time_ms": int(end_time_ms),
        "row_count": int(row_count),
        "schema_version": schema_version,
        "content_hash": content_hash,
        "normalized_fields": sorted({str(field) for field in normalized_fields}),
        "missing_fields": sorted({str(field) for field in missing_fields}),
        "quality_flags": sorted({str(flag) for flag in quality_flags}),
        "non_promotable_reasons": sorted({str(reason) for reason in non_promotable_reasons}),
    }
    if data_path is not None:
        manifest["data_path"] = data_path
    if extra:
        extra_payload = dict(extra)
        reserved = sorted(set(extra_payload) & RESERVED_DATA_MANIFEST_FIELDS)
        if reserved:
            raise ValueError(f"extra_must_not_override_reserved_manifest_fields:{','.join(reserved)}")
        manifest.update(extra_payload)
    manifest["provider_capability"] = provider_capability_payload(
        source_name=str(manifest.get("source_name") or ""),
        data_family=str(manifest.get("data_family") or ""),
        source_access_mode=_optional_str(manifest.get("source_access_mode")),
        latest_window_only=manifest.get("latest_window_only") if isinstance(manifest.get("latest_window_only"), bool) else None,
        coverage_scope=_optional_str(manifest.get("coverage_scope")),
    )
    return manifest


def normalize_legacy_research_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return a data-manifest-v1 view over older research manifests."""

    source_name = _source_name(manifest)
    data_family = canonical_data_family(str(manifest.get("data_family") or _family_name(manifest)))
    event_time_field = str(manifest.get("event_time_field") or _default_event_time_field(data_family))
    receive_time_field = _optional_str(manifest.get("receive_time_field"))
    unavailable_reason = _optional_str(manifest.get("receive_time_unavailable_reason"))
    if receive_time_field is None and unavailable_reason is None:
        unavailable_reason = "source_manifest_does_not_include_receive_time_field"
    content_hash = _optional_str(manifest.get("content_hash")) or _optional_str(manifest.get("sha256")) or "sha256:missing"
    quality_flags = list(manifest.get("quality_flags") or [])
    non_promotable_reasons = list(manifest.get("non_promotable_reasons") or manifest.get("non_promotable_notes") or [])
    if unavailable_reason:
        quality_flags.append("missing_receive_time")
        non_promotable_reasons.append("receive_time_unavailable")
    return build_data_manifest(
        source_name=source_name,
        source_type=str(manifest.get("source_type") or SOURCE_TYPES_BY_NAME.get(source_name, "local_file")),
        symbol=str(manifest.get("symbol") or "UNKNOWN"),
        data_family=data_family,
        event_time_field=event_time_field,
        receive_time_field=receive_time_field,
        receive_time_unavailable_reason=unavailable_reason,
        start_time_ms=int(manifest.get("start_time_ms") or manifest.get("first_time_ms") or manifest.get("first_event_time_ms") or 0),
        end_time_ms=int(manifest.get("end_time_ms") or manifest.get("last_time_ms") or manifest.get("last_event_time_ms") or 1),
        row_count=int(manifest.get("row_count") or 0),
        content_hash=content_hash,
        normalized_fields=list(manifest.get("normalized_fields") or manifest.get("schema_fields") or []),
        missing_fields=list(manifest.get("missing_fields") or []),
        quality_flags=quality_flags,
        non_promotable_reasons=non_promotable_reasons,
        schema_version=str(manifest.get("schema_version") or ARCHIVE_SOURCE_CONTRACT_VERSION),
        data_path=_optional_str(manifest.get("data_path")),
    )


def validate_data_manifest(manifest: Mapping[str, Any]) -> DataManifestValidation:
    errors: list[str] = []
    quality_flags = {str(flag) for flag in manifest.get("quality_flags", [])}
    for field in REQUIRED_DATA_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"missing_required_field:{field}")

    if manifest.get("manifest_version") != DATA_MANIFEST_VERSION:
        errors.append(f"manifest_version_must_be:{DATA_MANIFEST_VERSION}")
    if manifest.get("research_only") is not True:
        errors.append("research_only_must_be_true")
    if "observe_only" in manifest and manifest.get("observe_only") is not True:
        errors.append("observe_only_must_be_true")
    if "promotion_ready" in manifest and manifest.get("promotion_ready") is not False:
        errors.append("promotion_ready_must_be_false")

    source_name = _optional_str(manifest.get("source_name"))
    source_type = _optional_str(manifest.get("source_type"))
    symbol = _optional_str(manifest.get("symbol"))
    data_family = _optional_str(manifest.get("data_family"))
    descriptor = DATA_SOURCE_DESCRIPTORS.get(source_name or "")
    if descriptor is None:
        errors.append(f"unsupported_source_name:{source_name}")
    elif source_type != descriptor.source_type:
        errors.append(f"source_type_mismatch:{source_type}:{descriptor.source_type}")

    canonical_family = canonical_data_family(data_family or "")
    if descriptor is not None and canonical_family not in descriptor.data_families:
        errors.append(f"unsupported_data_family_for_source:{source_name}:{canonical_family}")

    _validate_time_bounds(manifest, errors)
    _validate_row_count(manifest, errors)
    _validate_hash(manifest, errors)

    event_time_field = _optional_str(manifest.get("event_time_field"))
    if not event_time_field:
        errors.append("event_time_field_required")
    receive_time_field = _optional_str(manifest.get("receive_time_field"))
    receive_reason = _optional_str(manifest.get("receive_time_unavailable_reason"))
    if not receive_time_field and not receive_reason:
        errors.append("receive_time_field_or_unavailable_reason_required")
    if receive_reason:
        quality_flags.add("missing_receive_time")
        quality_flags.add("receive_time_unavailable_non_promotable")

    missing_fields = _string_set(manifest.get("missing_fields"))
    normalized_fields = _string_set(manifest.get("normalized_fields"))
    zero_filled_fields = _string_set(manifest.get("zero_filled_fields"))
    protected_zero_filled = sorted(zero_filled_fields & PROTECTED_MISSINGNESS_FIELDS)
    if protected_zero_filled:
        errors.append(f"protected_fields_must_not_be_zero_filled:{','.join(protected_zero_filled)}")

    try:
        contract = get_normalized_field_contract(canonical_family)
    except ValueError:
        contract = None
        quality_flags.add("unsupported_family")
    if contract is not None:
        required_fields = set(contract.required_fields)
        unreported_missing = sorted(required_fields - normalized_fields - missing_fields)
        explicit_missing = sorted(required_fields & missing_fields)
        if unreported_missing:
            errors.append(f"normalized_fields_missing_required:{','.join(unreported_missing)}")
        if explicit_missing:
            quality_flags.add("missing_required_normalized_fields")
            quality_flags.add(f"missing_required_normalized_fields_explicit:{','.join(explicit_missing)}")
        if missing_fields & set(contract.protected_fields):
            quality_flags.add("protected_missingness_preserved")

    if missing_fields & BOOK_FIELD_NAMES:
        quality_flags.add("book_field_missingness_preserved")
    if missing_fields & ACCOUNT_EXECUTION_FIELD_NAMES:
        quality_flags.add("account_execution_missingness_preserved")

    _validate_context_metadata(manifest, errors, quality_flags)
    _validate_provider_capability_metadata(manifest, errors, quality_flags)

    point_in_time_compatible = bool(event_time_field and receive_time_field)
    diagnostic_only = bool(descriptor and descriptor.diagnostic_only_by_default) or not point_in_time_compatible
    promotable = False

    return DataManifestValidation(
        valid=not errors,
        promotable=promotable,
        point_in_time_compatible=point_in_time_compatible,
        source_name=source_name,
        source_type=source_type,
        symbol=symbol,
        data_family=canonical_family if data_family is not None else None,
        errors=tuple(errors),
        quality_flags=tuple(sorted(quality_flags)),
        missing_fields=tuple(sorted(missing_fields)),
    )


def assert_valid_data_manifest(manifest: Mapping[str, Any]) -> DataManifestValidation:
    result = validate_data_manifest(manifest)
    if not result.valid:
        raise ValueError("; ".join(result.errors))
    return result


def _validate_context_metadata(
    manifest: Mapping[str, Any],
    errors: list[str],
    quality_flags: set[str],
) -> None:
    role = _optional_str(manifest.get("context_family_role"))
    if role is not None:
        if role != "perp_context":
            errors.append(f"context_family_role_must_be:perp_context:{role}")
        else:
            quality_flags.add("perp_context_family")

    latest_window_raw = manifest.get("latest_window_only")
    if latest_window_raw is not None and not isinstance(latest_window_raw, bool):
        errors.append("latest_window_only_must_be_bool")
    coverage_scope = _optional_str(manifest.get("coverage_scope"))
    if latest_window_raw is True:
        quality_flags.add("latest_window_only_context")
        if coverage_scope in BROAD_CONTEXT_COVERAGE_SCOPES:
            errors.append(f"latest_window_context_cannot_claim_broad_coverage:{coverage_scope}")

    source_access_mode = _optional_str(manifest.get("source_access_mode"))
    if source_access_mode == "free_sample":
        quality_flags.add("free_sample_diagnostic_only")
        if manifest.get("diagnostic_only") is not True:
            errors.append("free_sample_manifest_must_be_diagnostic_only")
        if coverage_scope not in {None, "free_sample_diagnostic"}:
            errors.append(f"free_sample_manifest_cannot_claim_coverage_scope:{coverage_scope}")


def _validate_provider_capability_metadata(
    manifest: Mapping[str, Any],
    errors: list[str],
    quality_flags: set[str],
) -> None:
    payload = manifest.get("provider_capability")
    if payload is None:
        return
    if not isinstance(payload, Mapping):
        errors.append("provider_capability_must_be_object")
        return
    required_fields = {
        "registry_version",
        "source_name",
        "data_family",
        "durability_class",
        "retention_limit",
        "history_start",
        "exchange_native",
        "normalized",
        "health_policy",
        "diagnostic_only_by_default",
        "candidate_ready_default",
    }
    missing = sorted(required_fields - set(str(key) for key in payload))
    if missing:
        errors.append(f"provider_capability_missing_fields:{','.join(missing)}")
        return
    if payload.get("registry_version") != DATA_PROVIDER_CAPABILITY_REGISTRY_VERSION:
        errors.append(f"provider_capability_registry_version_must_be:{DATA_PROVIDER_CAPABILITY_REGISTRY_VERSION}")

    expected = provider_capability_payload(
        source_name=str(manifest.get("source_name") or ""),
        data_family=str(manifest.get("data_family") or ""),
        source_access_mode=_optional_str(manifest.get("source_access_mode")),
        latest_window_only=manifest.get("latest_window_only") if isinstance(manifest.get("latest_window_only"), bool) else None,
        coverage_scope=_optional_str(manifest.get("coverage_scope")),
    )
    for field in (
        "source_name",
        "data_family",
        "durability_class",
        "retention_limit",
        "history_start",
        "exchange_native",
        "normalized",
        "health_policy",
        "diagnostic_only_by_default",
        "candidate_ready_default",
    ):
        if payload.get(field) != expected.get(field):
            errors.append(f"provider_capability_mismatch:{field}:{payload.get(field)}:{expected.get(field)}")
    durability_class = _optional_str(payload.get("durability_class"))
    if durability_class:
        quality_flags.add(f"provider_capability:{durability_class}")


def registered_only_manifest(*, source_name: str, symbol: str, data_family: str) -> dict[str, Any]:
    descriptor = DATA_SOURCE_DESCRIPTORS[source_name]
    contract = get_normalized_field_contract(data_family)
    return build_data_manifest(
        source_name=source_name,
        source_type=descriptor.source_type,
        symbol=symbol,
        data_family=data_family,
        event_time_field="event_time_ms",
        receive_time_field=None,
        receive_time_unavailable_reason=f"{source_name} ingestion is registered-only in Stage 3",
        start_time_ms=0,
        end_time_ms=1,
        row_count=0,
        content_hash="sha256:registered-only",
        normalized_fields=[],
        missing_fields=contract.required_fields,
        quality_flags=["registered_only", "diagnostic_only", "zero_row_manifest"],
        non_promotable_reasons=["registered_only_provider_ingestion_not_implemented"],
        extra={"ingestion_status": "registered_only"},
    )


def _source_name(manifest: Mapping[str, Any]) -> str:
    raw = str(manifest.get("source_name") or manifest.get("source") or "").strip()
    if raw == "binance_usdm_klines":
        return "binance_rest"
    return raw


def _family_name(manifest: Mapping[str, Any]) -> str:
    if "interval" in manifest and str(manifest.get("source") or "") == "binance_usdm_klines":
        return "kline"
    return str(manifest.get("family") or manifest.get("data_family") or "")


def _default_event_time_field(data_family: str) -> str:
    if data_family == "kline":
        return "event_time_ms"
    return "event_time_ms"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    try:
        return {str(item) for item in value if str(item).strip()}
    except TypeError:
        return {str(value)}


def _validate_time_bounds(manifest: Mapping[str, Any], errors: list[str]) -> None:
    start = _int_or_none(manifest.get("start_time_ms"))
    end = _int_or_none(manifest.get("end_time_ms"))
    if start is None:
        errors.append("start_time_ms_must_be_integer")
    if end is None:
        errors.append("end_time_ms_must_be_integer")
    if start is not None and end is not None and start >= end:
        errors.append("start_time_ms_must_be_before_end_time_ms")


def _validate_row_count(manifest: Mapping[str, Any], errors: list[str]) -> None:
    row_count = _int_or_none(manifest.get("row_count"))
    if row_count is None:
        errors.append("row_count_must_be_integer")
    elif row_count < 0:
        errors.append("row_count_must_not_be_negative")


def _validate_hash(manifest: Mapping[str, Any], errors: list[str]) -> None:
    content_hash = _optional_str(manifest.get("content_hash"))
    if not content_hash:
        errors.append("content_hash_must_be_non_empty")
    elif not content_hash.startswith("sha256:"):
        errors.append("content_hash_must_use_sha256_prefix")


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
