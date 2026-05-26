from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

ARCHIVE_SOURCE_CONTRACT_VERSION = "of-archive-source-provider-normalization-contract-v2"

SUPPORTED_SYMBOLS = ("BTCUSDT", "ETHUSDT")

CANONICAL_DATA_FAMILIES = (
    "kline",
    "trade",
    "agg_trade",
    "book_ticker",
    "depth_snapshot",
    "liquidation",
    "funding_rate",
    "open_interest",
    "premium_index",
    "user_fill",
    "user_funding",
    "order_event",
    "position_snapshot",
)

DATA_FAMILY_ALIASES = {
    "bbo": "book_ticker",
    "book_snapshot": "depth_snapshot",
    "order_book_l2": "depth_snapshot",
}

BOOK_FIELD_NAMES = frozenset(
    {
        "bids",
        "asks",
        "best_bid_price",
        "best_bid_size",
        "best_ask_price",
        "best_ask_size",
        "bid_price",
        "bid_size",
        "ask_price",
        "ask_size",
        "spread_bps",
        "depth_10bps_usd",
        "depth_25bps_usd",
        "book_imbalance",
        "queue_imbalance",
        "top_of_book_imbalance",
    }
)
ACCOUNT_EXECUTION_FIELD_NAMES = frozenset(
    {
        "account_address",
        "order_id",
        "cloid",
        "order_status",
        "fill_id",
        "fill_price",
        "fill_size",
        "position_size",
        "position_side",
        "margin_used",
        "funding_payment",
        "funding_rate",
    }
)
PROTECTED_MISSINGNESS_FIELDS = BOOK_FIELD_NAMES | ACCOUNT_EXECUTION_FIELD_NAMES


@dataclass(frozen=True, slots=True)
class ArchiveNormalizedFieldContract:
    data_family: str
    canonical_data_family: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    protected_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchiveSourceDescriptor:
    source_name: str
    source_type: str
    display_name: str
    asset_scope: tuple[str, ...]
    symbol_scope: tuple[str, ...]
    likely_data_families: tuple[str, ...]
    timestamp_requirements: tuple[str, ...]
    promotional_eligible_by_default: bool
    diagnostic_only_by_default: bool
    caveats: tuple[str, ...]
    caveat_quality_flags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ArchiveManifestValidation:
    source_name: str | None
    source_type: str | None
    symbol: str | None
    data_family: str | None
    research_only: bool
    valid: bool
    point_in_time_compatible: bool
    promotable: bool
    diagnostic_only: bool
    errors: tuple[str, ...]
    quality_flags: tuple[str, ...]
    missing_fields: tuple[str, ...]
    unavailable_reason: str | None


_COMMON_OPTIONAL_FIELDS = (
    "receive_time_ms",
    "provider_symbol",
    "provider_exchange",
    "provider_dataset",
    "provider_sequence_id",
    "ingest_time_ms",
)

NORMALIZED_FIELD_CONTRACTS: dict[str, ArchiveNormalizedFieldContract] = {
    "kline": ArchiveNormalizedFieldContract(
        data_family="kline",
        canonical_data_family="kline",
        required_fields=(
            "event_time_ms",
            "symbol",
            "interval",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "open_time_ms",
            "close_time_ms",
            "quote_volume",
            "trade_count",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
        ),
        protected_fields=(),
    ),
    "trade": ArchiveNormalizedFieldContract(
        data_family="trade",
        canonical_data_family="trade",
        required_fields=("event_time_ms", "symbol", "trade_id", "price", "quantity"),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "side",
            "is_buyer_maker",
            "buyer_order_id",
            "seller_order_id",
        ),
        protected_fields=(),
    ),
    "agg_trade": ArchiveNormalizedFieldContract(
        data_family="agg_trade",
        canonical_data_family="agg_trade",
        required_fields=(
            "event_time_ms",
            "symbol",
            "agg_trade_id",
            "price",
            "quantity",
            "first_trade_id",
            "last_trade_id",
        ),
        optional_fields=_COMMON_OPTIONAL_FIELDS + ("is_buyer_maker",),
        protected_fields=(),
    ),
    "book_ticker": ArchiveNormalizedFieldContract(
        data_family="book_ticker",
        canonical_data_family="book_ticker",
        required_fields=(
            "event_time_ms",
            "symbol",
            "best_bid_price",
            "best_bid_size",
            "best_ask_price",
            "best_ask_size",
        ),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "update_id",
            "transaction_time_ms",
            "spread_bps",
            "top_of_book_imbalance",
        ),
        protected_fields=tuple(sorted(BOOK_FIELD_NAMES)),
    ),
    "depth_snapshot": ArchiveNormalizedFieldContract(
        data_family="depth_snapshot",
        canonical_data_family="depth_snapshot",
        required_fields=("event_time_ms", "symbol", "last_update_id", "bids", "asks"),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "first_update_id",
            "best_bid_price",
            "best_bid_size",
            "best_ask_price",
            "best_ask_size",
            "spread_bps",
            "depth_10bps_usd",
            "depth_25bps_usd",
            "book_imbalance",
            "queue_imbalance",
            "top_of_book_imbalance",
        ),
        protected_fields=tuple(sorted(BOOK_FIELD_NAMES)),
    ),
    "liquidation": ArchiveNormalizedFieldContract(
        data_family="liquidation",
        canonical_data_family="liquidation",
        required_fields=("event_time_ms", "symbol", "side", "price", "quantity"),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "order_type",
            "time_in_force",
            "average_price",
            "order_status",
            "last_filled_quantity",
            "trade_time_ms",
        ),
        protected_fields=(),
    ),
    "funding_rate": ArchiveNormalizedFieldContract(
        data_family="funding_rate",
        canonical_data_family="funding_rate",
        required_fields=("event_time_ms", "symbol", "funding_rate"),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "funding_time_ms",
            "mark_price",
            "index_price",
            "interest_rate",
        ),
        protected_fields=(),
    ),
    "open_interest": ArchiveNormalizedFieldContract(
        data_family="open_interest",
        canonical_data_family="open_interest",
        required_fields=("event_time_ms", "symbol", "open_interest"),
        optional_fields=_COMMON_OPTIONAL_FIELDS + ("open_interest_value_usd",),
        protected_fields=(),
    ),
    "premium_index": ArchiveNormalizedFieldContract(
        data_family="premium_index",
        canonical_data_family="premium_index",
        required_fields=("event_time_ms", "symbol", "mark_price", "index_price", "premium_index"),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "estimated_settle_price",
            "last_funding_rate",
            "next_funding_time_ms",
            "interest_rate",
        ),
        protected_fields=(),
    ),
    "user_fill": ArchiveNormalizedFieldContract(
        data_family="user_fill",
        canonical_data_family="user_fill",
        required_fields=(
            "event_time_ms",
            "symbol",
            "account_address",
            "fill_id",
            "order_id",
            "side",
            "fill_price",
            "fill_size",
        ),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "cloid",
            "fee",
            "fee_token",
            "realized_pnl",
            "position_side",
        ),
        protected_fields=tuple(sorted(ACCOUNT_EXECUTION_FIELD_NAMES)),
    ),
    "user_funding": ArchiveNormalizedFieldContract(
        data_family="user_funding",
        canonical_data_family="user_funding",
        required_fields=("event_time_ms", "symbol", "account_address", "funding_payment", "funding_rate"),
        optional_fields=_COMMON_OPTIONAL_FIELDS + ("position_size", "position_side"),
        protected_fields=tuple(sorted(ACCOUNT_EXECUTION_FIELD_NAMES)),
    ),
    "order_event": ArchiveNormalizedFieldContract(
        data_family="order_event",
        canonical_data_family="order_event",
        required_fields=("event_time_ms", "symbol", "account_address", "order_id", "cloid", "order_status"),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "side",
            "order_type",
            "limit_price",
            "order_size",
            "filled_size",
            "reduce_only",
        ),
        protected_fields=tuple(sorted(ACCOUNT_EXECUTION_FIELD_NAMES)),
    ),
    "position_snapshot": ArchiveNormalizedFieldContract(
        data_family="position_snapshot",
        canonical_data_family="position_snapshot",
        required_fields=("event_time_ms", "symbol", "account_address", "position_size", "position_side"),
        optional_fields=_COMMON_OPTIONAL_FIELDS
        + (
            "entry_price",
            "mark_price",
            "unrealized_pnl",
            "margin_used",
            "leverage",
        ),
        protected_fields=tuple(sorted(ACCOUNT_EXECUTION_FIELD_NAMES)),
    ),
}


SUPPORTED_ARCHIVE_SOURCES: dict[str, ArchiveSourceDescriptor] = {
    "binance_vision": ArchiveSourceDescriptor(
        source_name="binance_vision",
        source_type="public_archive",
        display_name="Binance Vision",
        asset_scope=("BTC", "ETH"),
        symbol_scope=SUPPORTED_SYMBOLS,
        likely_data_families=(
            "agg_trade",
            "trade",
            "kline",
            "premium_index",
            "funding_rate",
            "open_interest",
            "book_ticker",
            "depth_snapshot",
            "liquidation",
        ),
        timestamp_requirements=(
            "event_time_field required",
            "receive_time_field required for promotion eligibility",
            "archive publication time is not a substitute for event receive time",
        ),
        promotional_eligible_by_default=False,
        diagnostic_only_by_default=True,
        caveats=(
            "Historical public archive rows may lack the live receive timestamp needed to prove point-in-time ingestion.",
            "Provider schema can differ from live Binance USD-M stream payloads and must be flagged as source_mismatch when observed.",
        ),
        caveat_quality_flags=(
            "source_caveat:binance_vision_receive_time_gap",
            "source_caveat:binance_vision_schema_may_differ",
        ),
    ),
    "crypto_lake": ArchiveSourceDescriptor(
        source_name="crypto_lake",
        source_type="commercial_archive",
        display_name="Crypto Lake",
        asset_scope=("BTC", "ETH"),
        symbol_scope=SUPPORTED_SYMBOLS,
        likely_data_families=(
            "trade",
            "agg_trade",
            "book_ticker",
            "depth_snapshot",
            "kline",
            "funding_rate",
            "open_interest",
            "liquidation",
        ),
        timestamp_requirements=(
            "event_time_field required",
            "receive_time_field required for promotion eligibility",
            "vendor normalization time must be distinguished from exchange receive time",
        ),
        promotional_eligible_by_default=False,
        diagnostic_only_by_default=True,
        caveats=(
            "Commercial normalization can rename, aggregate, or repair fields; provider mismatch is a first-class quality flag.",
            "Missing depth or trade-side fields must remain null/missing and cannot be zero-filled.",
        ),
        caveat_quality_flags=(
            "source_caveat:crypto_lake_vendor_normalization",
            "source_caveat:crypto_lake_missing_depth_must_be_explicit",
        ),
    ),
    "bybit_archive": ArchiveSourceDescriptor(
        source_name="bybit_archive",
        source_type="exchange_archive",
        display_name="Bybit Archive",
        asset_scope=("BTC", "ETH"),
        symbol_scope=SUPPORTED_SYMBOLS,
        likely_data_families=(
            "trade",
            "kline",
            "funding_rate",
            "open_interest",
            "premium_index",
            "book_ticker",
            "depth_snapshot",
            "liquidation",
        ),
        timestamp_requirements=(
            "event_time_field required",
            "receive_time_field required for promotion eligibility",
            "public historical downloads or REST backfills must be distinguished from live receive time",
        ),
        promotional_eligible_by_default=False,
        diagnostic_only_by_default=True,
        caveats=(
            "Bybit public historical downloads and REST history are exchange data surfaces but are not this branch's active fixture contract yet.",
            "Downloader, parser, checksum or provenance policy, and gap/duplicate validation must be implemented before candidate-depth use.",
        ),
        caveat_quality_flags=(
            "source_caveat:bybit_archive_registered_only",
            "source_caveat:bybit_archive_requires_ingestion_contract",
        ),
    ),
    "hyperliquid_archive": ArchiveSourceDescriptor(
        source_name="hyperliquid_archive",
        source_type="venue_archive",
        display_name="Hyperliquid Archive",
        asset_scope=("BTC", "ETH"),
        symbol_scope=SUPPORTED_SYMBOLS,
        likely_data_families=(
            "trade",
            "depth_snapshot",
            "book_ticker",
            "funding_rate",
            "user_fill",
            "user_funding",
            "order_event",
            "position_snapshot",
        ),
        timestamp_requirements=(
            "event_time_field required",
            "receive_time_field required for promotion eligibility",
            "account/order archives must distinguish exchange event time from local replay ingest time",
        ),
        promotional_eligible_by_default=False,
        diagnostic_only_by_default=True,
        caveats=(
            "Archive-only Hyperliquid data is diagnostic until reconciled against append-only local order/account journals.",
            "Public market archives cannot stand in for private account, open-order, fill, funding, or position state.",
        ),
        caveat_quality_flags=(
            "source_caveat:hyperliquid_requires_local_account_journal_reconciliation",
            "source_caveat:hyperliquid_public_archive_not_account_state",
        ),
    ),
}

REQUIRED_MANIFEST_FIELDS = (
    "source_name",
    "source_type",
    "symbol",
    "data_family",
    "start_time_ms",
    "end_time_ms",
    "row_count",
    "event_time_field",
    "schema_version",
    "content_hash",
    "normalized_fields",
    "research_only",
)


def get_archive_source_descriptor(source_name: str) -> ArchiveSourceDescriptor:
    try:
        return SUPPORTED_ARCHIVE_SOURCES[str(source_name)]
    except KeyError as exc:
        raise ValueError(f"unsupported archive source: {source_name}") from exc


def archive_source_descriptors() -> tuple[ArchiveSourceDescriptor, ...]:
    return tuple(SUPPORTED_ARCHIVE_SOURCES[name] for name in sorted(SUPPORTED_ARCHIVE_SOURCES))


def canonical_data_family(data_family: str) -> str:
    family = str(data_family).strip()
    return DATA_FAMILY_ALIASES.get(family, family)


def archive_normalized_field_contracts() -> tuple[ArchiveNormalizedFieldContract, ...]:
    return tuple(NORMALIZED_FIELD_CONTRACTS[name] for name in CANONICAL_DATA_FAMILIES)


def get_normalized_field_contract(data_family: str) -> ArchiveNormalizedFieldContract:
    canonical_family = canonical_data_family(data_family)
    try:
        contract = NORMALIZED_FIELD_CONTRACTS[canonical_family]
    except KeyError as exc:
        raise ValueError(f"unsupported data family: {data_family}") from exc
    if str(data_family).strip() == canonical_family:
        return contract
    return ArchiveNormalizedFieldContract(
        data_family=str(data_family).strip(),
        canonical_data_family=canonical_family,
        required_fields=contract.required_fields,
        optional_fields=contract.optional_fields,
        protected_fields=contract.protected_fields,
    )


def get_archive_source_field_contract(
    source_name: str,
    data_family: str,
) -> ArchiveNormalizedFieldContract:
    descriptor = get_archive_source_descriptor(source_name)
    contract = get_normalized_field_contract(data_family)
    if contract.canonical_data_family not in descriptor.likely_data_families:
        raise ValueError(
            f"data family {data_family} is not listed for archive source {source_name}"
        )
    return contract


def validate_archive_source_manifest(manifest: Mapping[str, Any]) -> ArchiveManifestValidation:
    errors: list[str] = []
    quality_flags: list[str] = []

    for field_name in REQUIRED_MANIFEST_FIELDS:
        if field_name not in manifest:
            errors.append(f"missing_required_field:{field_name}")

    source_name = _optional_str(manifest.get("source_name"))
    source_type = _optional_str(manifest.get("source_type"))
    symbol = _optional_str(manifest.get("symbol"))
    data_family = _optional_str(manifest.get("data_family"))
    research_only = bool(manifest.get("research_only") is True)

    descriptor = SUPPORTED_ARCHIVE_SOURCES.get(source_name or "")
    if descriptor is None and source_name is not None:
        errors.append(f"unsupported_source_name:{source_name}")
    if descriptor is not None:
        quality_flags.extend(descriptor.caveat_quality_flags)
        if source_type != descriptor.source_type:
            errors.append(f"source_type_mismatch:{source_type}:{descriptor.source_type}")
        if symbol not in descriptor.symbol_scope:
            errors.append(f"symbol_out_of_scope:{symbol}")
        canonical_family = canonical_data_family(data_family or "")
        if canonical_family not in descriptor.likely_data_families:
            quality_flags.append("unsupported_family")
            quality_flags.append(f"unsupported_or_unlisted_data_family:{data_family}")
    if not research_only:
        errors.append("research_only_must_be_true")

    _validate_time_bounds(manifest, errors)
    _validate_row_count(manifest, errors)
    _validate_non_empty_string(manifest, "schema_version", errors)
    _validate_non_empty_string(manifest, "content_hash", errors)

    event_time_field = _optional_str(manifest.get("event_time_field"))
    if not event_time_field:
        errors.append("event_time_field_required")
    receive_time_field = _optional_str(manifest.get("receive_time_field"))
    unavailable_reason = _optional_str(manifest.get("receive_time_unavailable_reason"))
    if not receive_time_field and not unavailable_reason:
        errors.append("receive_time_field_or_unavailable_reason_required")
        quality_flags.append("missing_receive_time")
    if unavailable_reason:
        quality_flags.append("missing_receive_time")
        quality_flags.append("receive_time_unavailable_non_promotable")
    if receive_time_field and unavailable_reason:
        quality_flags.append("receive_time_field_supersedes_unavailable_reason")

    missing_fields = _string_set_from_keys(
        manifest,
        ("missing_fields", "unavailable_fields", "null_fields"),
    )
    zero_filled_fields = _string_set_from_keys(manifest, ("zero_filled_fields",))
    normalized_fields = _string_set_from_keys(manifest, ("normalized_fields",))
    schema_fields = _string_set_from_keys(manifest, ("schema_fields",))
    protected_zero_filled = sorted(zero_filled_fields & PROTECTED_MISSINGNESS_FIELDS)
    if protected_zero_filled:
        errors.append(f"protected_fields_must_not_be_zero_filled:{','.join(protected_zero_filled)}")

    contract = _field_contract_or_none(data_family)
    if contract is None:
        quality_flags.append("unsupported_family")
        if data_family:
            quality_flags.append(f"unsupported_data_family_contract:{data_family}")
    else:
        if data_family != contract.canonical_data_family:
            quality_flags.append(f"data_family_alias:{data_family}->{contract.canonical_data_family}")
        required_fields = set(contract.required_fields)
        explicitly_missing_required = sorted(required_fields & missing_fields)
        unreported_missing_required = sorted(required_fields - normalized_fields - missing_fields)
        if explicitly_missing_required:
            quality_flags.append("missing_required_normalized_fields")
            quality_flags.append(
                f"missing_required_normalized_fields_explicit:{','.join(explicitly_missing_required)}"
            )
        if unreported_missing_required:
            quality_flags.append("missing_required_normalized_fields")
            errors.append(
                f"normalized_fields_missing_required:{','.join(unreported_missing_required)}"
            )
        protected_missing = sorted(missing_fields & set(contract.protected_fields))
        if protected_missing:
            quality_flags.append("protected_missingness_preserved")

    book_family = contract is not None and contract.canonical_data_family in {
        "book_ticker",
        "depth_snapshot",
    }
    if book_family:
        observed_book_fields = (schema_fields | normalized_fields) & BOOK_FIELD_NAMES
        missing_book_fields = missing_fields & BOOK_FIELD_NAMES
        if not observed_book_fields and not missing_book_fields:
            quality_flags.append("book_family_without_book_field_coverage")
        if missing_book_fields:
            quality_flags.append("book_field_missingness_preserved")
    account_execution_family = contract is not None and contract.canonical_data_family in {
        "user_fill",
        "user_funding",
        "order_event",
        "position_snapshot",
    }
    if account_execution_family:
        observed_execution_fields = (schema_fields | normalized_fields) & ACCOUNT_EXECUTION_FIELD_NAMES
        missing_execution_fields = missing_fields & ACCOUNT_EXECUTION_FIELD_NAMES
        if not observed_execution_fields and not missing_execution_fields:
            quality_flags.append("execution_family_without_account_execution_field_coverage")
        if missing_execution_fields:
            quality_flags.append("account_execution_missingness_preserved")

    source_mismatch_reason = _optional_str(manifest.get("source_mismatch_reason"))
    provider_symbol = _optional_str(manifest.get("provider_symbol"))
    if bool(manifest.get("source_mismatch")) or source_mismatch_reason:
        quality_flags.append("provider_mismatch")
        quality_flags.append("source_mismatch")
    if provider_symbol and symbol and provider_symbol != symbol:
        quality_flags.append("provider_mismatch")
        quality_flags.append("source_mismatch")
        quality_flags.append("provider_symbol_differs_from_symbol")

    point_in_time_compatible = bool(event_time_field) and bool(receive_time_field)
    diagnostic_default = True if descriptor is None else descriptor.diagnostic_only_by_default
    promotable_default = False if descriptor is None else descriptor.promotional_eligible_by_default
    diagnostic_only = diagnostic_default or not point_in_time_compatible or "source_mismatch" in quality_flags
    promotable = (
        promotable_default
        and research_only
        and point_in_time_compatible
        and not diagnostic_only
        and not errors
    )

    return ArchiveManifestValidation(
        source_name=source_name,
        source_type=source_type,
        symbol=symbol,
        data_family=data_family,
        research_only=research_only,
        valid=not errors,
        point_in_time_compatible=point_in_time_compatible,
        promotable=promotable,
        diagnostic_only=diagnostic_only,
        errors=tuple(errors),
        quality_flags=tuple(sorted(set(quality_flags))),
        missing_fields=tuple(sorted(missing_fields)),
        unavailable_reason=unavailable_reason,
    )


def assert_valid_archive_source_manifest(manifest: Mapping[str, Any]) -> ArchiveManifestValidation:
    result = validate_archive_source_manifest(manifest)
    if not result.valid:
        raise ValueError("; ".join(result.errors))
    return result


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _field_contract_or_none(data_family: str | None) -> ArchiveNormalizedFieldContract | None:
    if not data_family:
        return None
    try:
        return get_normalized_field_contract(data_family)
    except ValueError:
        return None


def _string_set_from_keys(manifest: Mapping[str, Any], keys: tuple[str, ...]) -> set[str]:
    values: set[str] = set()
    for key in keys:
        raw = manifest.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            values.add(raw)
            continue
        try:
            values.update(str(item) for item in raw if str(item).strip())
        except TypeError:
            values.add(str(raw))
    return values


def _validate_time_bounds(manifest: Mapping[str, Any], errors: list[str]) -> None:
    start_time_ms = _int_or_none(manifest.get("start_time_ms"))
    end_time_ms = _int_or_none(manifest.get("end_time_ms"))
    if start_time_ms is None:
        errors.append("start_time_ms_must_be_integer")
    if end_time_ms is None:
        errors.append("end_time_ms_must_be_integer")
    if start_time_ms is not None and end_time_ms is not None and start_time_ms >= end_time_ms:
        errors.append("start_time_ms_must_be_before_end_time_ms")


def _validate_row_count(manifest: Mapping[str, Any], errors: list[str]) -> None:
    row_count = _int_or_none(manifest.get("row_count"))
    if row_count is None:
        errors.append("row_count_must_be_integer")
    elif row_count <= 0:
        errors.append("row_count_must_be_positive")


def _validate_non_empty_string(manifest: Mapping[str, Any], field_name: str, errors: list[str]) -> None:
    if not _optional_str(manifest.get(field_name)):
        errors.append(f"{field_name}_must_be_non_empty")


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
