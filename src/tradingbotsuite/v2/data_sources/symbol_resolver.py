# V2-AUDIT-ID: V2-AUD-DATASRC-003
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, no_live_imports, strict_free_symbol_mapping
# V2-OWNER: v2_data_sources
"""Deterministic cross-venue symbol-map resolver scaffolding."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.data_sources.schemas import (
    MappingStatus,
    MarketType,
    VenueSymbolMapRow,
    VenueSymbolRef,
)
from tradingbotsuite.v2.universe.models import UniverseSnapshotRow


class ProbeStatus(str, Enum):
    VERIFIED = "verified"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    DELISTED = "delisted"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


PROBE_TO_MAPPING_STATUS = {
    ProbeStatus.VERIFIED: MappingStatus.VERIFIED,
    ProbeStatus.MISSING: MappingStatus.MISSING,
    ProbeStatus.AMBIGUOUS: MappingStatus.AMBIGUOUS,
    ProbeStatus.DELISTED: MappingStatus.DELISTED,
    ProbeStatus.MANUAL_REVIEW_REQUIRED: MappingStatus.MANUAL_REVIEW_REQUIRED,
}


class SymbolProbeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue_key: str = Field(min_length=1)
    status: ProbeStatus
    symbol: str | None = None
    source_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_probe(self) -> "SymbolProbeResult":
        if self.status == ProbeStatus.VERIFIED and not self.symbol:
            raise ValueError("verified probe results require a symbol")
        if self.status in {
            ProbeStatus.AMBIGUOUS,
            ProbeStatus.MANUAL_REVIEW_REQUIRED,
        } and not self.notes:
            raise ValueError("ambiguous/manual-review probe results require notes")
        return self


class VenueCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue_key: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    symbol: str
    market_type: MarketType
    quote_asset: str | None = None
    contract_type: str | None = None
    native_symbol: str | None = None


DEFAULT_VENUE_ORDER = (
    "binance_usdm",
    "binance_spot",
    "bybit_linear",
    "okx_swap",
    "bitget_mix",
    "mexc_contract",
    "gate_futures",
    "kucoin_futures",
    "htx_swap",
    "dydx",
    "deribit_perpetual",
    "coinbase_spot",
    "kraken_spot",
    "pyth_feed",
    "defillama_context",
    "dexscreener",
    "geckoterminal",
)


def resolve_symbol_map_for_coin(
    *,
    hyperliquid_coin: str,
    as_of_date: date,
    hyperliquid_liquid_as_of: bool,
    above_day_notional_threshold: bool,
    probes: Iterable[SymbolProbeResult | Mapping[str, object]] = (),
    universe_snapshot_ref: str,
    external_exchange_info_refs: Sequence[str] = (),
) -> VenueSymbolMapRow:
    """Build one symbol-map row from deterministic candidates plus probe evidence."""

    normalized_base = canonical_base_asset_from_hyperliquid_coin(hyperliquid_coin)
    probe_by_key = _materialize_probes(probes)
    symbols: dict[str, VenueSymbolRef] = {
        "hyperliquid_perp": VenueSymbolRef(
            venue="hyperliquid",
            symbol=hyperliquid_coin,
            market_type=MarketType.PERPETUAL,
            status=MappingStatus.VERIFIED,
            quote_asset="USD",
            contract_type="linear_perpetual",
            native_symbol=hyperliquid_coin,
        )
    }
    blocker_reasons: list[str] = []
    verified_external = 0
    non_native_statuses: list[MappingStatus] = []
    for candidate in candidate_symbols_for_hyperliquid_coin(hyperliquid_coin):
        probe = probe_by_key.get(candidate.venue_key)
        if probe is None:
            status = MappingStatus.NOT_CHECKED
            symbol = candidate.symbol
            notes: tuple[str, ...] = ()
            source_refs: tuple[str, ...] = ()
        else:
            status = PROBE_TO_MAPPING_STATUS[probe.status]
            symbol = probe.symbol or candidate.symbol
            notes = probe.notes
            source_refs = probe.source_refs
        if status == MappingStatus.VERIFIED:
            verified_external += 1
        elif status in {
            MappingStatus.AMBIGUOUS,
            MappingStatus.MANUAL_REVIEW_REQUIRED,
        }:
            blocker_reasons.append(f"{candidate.venue_key}_{status.value}")
        non_native_statuses.append(status)
        symbols[candidate.venue_key] = VenueSymbolRef(
            venue=candidate.venue,
            symbol=symbol,
            market_type=candidate.market_type,
            status=status,
            quote_asset=candidate.quote_asset,
            contract_type=candidate.contract_type,
            native_symbol=candidate.native_symbol or candidate.symbol,
            notes=notes,
            source_refs=source_refs,
        )
    external_status = _aggregate_external_status(
        verified_external=verified_external,
        statuses=non_native_statuses,
    )
    return VenueSymbolMapRow(
        hyperliquid_coin=hyperliquid_coin,
        as_of_date=as_of_date,
        canonical_base_asset=normalized_base,
        symbols=symbols,
        hyperliquid_liquid_as_of=hyperliquid_liquid_as_of,
        above_day_notional_threshold=above_day_notional_threshold,
        external_mapping_verified=external_status,
        provenance={
            "hyperliquid_universe_snapshot_ref": universe_snapshot_ref,
            "external_exchange_info_refs": tuple(external_exchange_info_refs),
        },
        blocker_reasons=tuple(sorted(set(blocker_reasons))),
    )


def resolve_symbol_maps_from_universe_rows(
    rows: Iterable[UniverseSnapshotRow],
    *,
    probes_by_coin: Mapping[str, Iterable[SymbolProbeResult | Mapping[str, object]]] | None = None,
    coin_by_instrument_id: Mapping[str, str] | None = None,
    external_exchange_info_refs: Sequence[str] = (),
) -> list[VenueSymbolMapRow]:
    """Build symbol maps for all supplied Hyperliquid universe rows."""

    probes_by_coin = probes_by_coin or {}
    coin_by_instrument_id = coin_by_instrument_id or {}
    resolved: list[VenueSymbolMapRow] = []
    for row in sorted(rows, key=lambda item: item.instrument_id):
        coin = coin_by_instrument_id.get(row.instrument_id, row.instrument_id.rsplit(":", 1)[-1])
        resolved.append(
            resolve_symbol_map_for_coin(
                hyperliquid_coin=coin,
                as_of_date=row.asof_date,
                hyperliquid_liquid_as_of=row.eligible_status,
                above_day_notional_threshold=row.eligible_volume,
                probes=probes_by_coin.get(coin, ()),
                universe_snapshot_ref=row.snapshot_id,
                external_exchange_info_refs=external_exchange_info_refs,
            )
        )
    return resolved


def candidate_symbols_for_hyperliquid_coin(coin: str) -> tuple[VenueCandidate, ...]:
    """Return deterministic candidate symbols without marking them verified."""

    base = canonical_base_asset_from_hyperliquid_coin(coin)
    binance_contract_base = binance_contract_base_from_hyperliquid_coin(coin)
    return (
        VenueCandidate(
            venue_key="binance_usdm",
            venue="binance",
            symbol=f"{binance_contract_base}USDT",
            market_type=MarketType.PERPETUAL,
            quote_asset="USDT",
            contract_type="linear_perpetual",
        ),
        VenueCandidate(
            venue_key="binance_spot",
            venue="binance",
            symbol=f"{base}USDT",
            market_type=MarketType.SPOT,
            quote_asset="USDT",
        ),
        VenueCandidate(
            venue_key="bybit_linear",
            venue="bybit",
            symbol=f"{base}USDT",
            market_type=MarketType.PERPETUAL,
            quote_asset="USDT",
            contract_type="linear_perpetual",
        ),
        VenueCandidate(
            venue_key="okx_swap",
            venue="okx",
            symbol=f"{base}-USDT-SWAP",
            market_type=MarketType.PERPETUAL,
            quote_asset="USDT",
            contract_type="swap",
        ),
        VenueCandidate(
            venue_key="bitget_mix",
            venue="bitget",
            symbol=f"{base}USDT",
            market_type=MarketType.PERPETUAL,
            quote_asset="USDT",
            contract_type="linear_perpetual",
        ),
        VenueCandidate(
            venue_key="mexc_contract",
            venue="mexc",
            symbol=f"{base}_USDT",
            market_type=MarketType.PERPETUAL,
            quote_asset="USDT",
            contract_type="linear_perpetual",
        ),
        VenueCandidate(
            venue_key="gate_futures",
            venue="gate",
            symbol=f"{base}_USDT",
            market_type=MarketType.PERPETUAL,
            quote_asset="USDT",
            contract_type="linear_perpetual",
        ),
        VenueCandidate(
            venue_key="kucoin_futures",
            venue="kucoin",
            symbol=f"{base}USDTM",
            market_type=MarketType.PERPETUAL,
            quote_asset="USDT",
            contract_type="linear_perpetual",
        ),
        VenueCandidate(
            venue_key="htx_swap",
            venue="htx",
            symbol=f"{base}-USDT",
            market_type=MarketType.PERPETUAL,
            quote_asset="USDT",
            contract_type="linear_perpetual",
        ),
        VenueCandidate(
            venue_key="dydx",
            venue="dydx",
            symbol=f"{base}-USD",
            market_type=MarketType.PERPETUAL,
            quote_asset="USD",
            contract_type="perpetual",
        ),
        VenueCandidate(
            venue_key="deribit_perpetual",
            venue="deribit",
            symbol=f"{base}-PERPETUAL",
            market_type=MarketType.PERPETUAL,
            quote_asset="USD",
            contract_type="perpetual",
        ),
        VenueCandidate(
            venue_key="coinbase_spot",
            venue="coinbase",
            symbol=f"{base}-USD",
            market_type=MarketType.SPOT,
            quote_asset="USD",
        ),
        VenueCandidate(
            venue_key="kraken_spot",
            venue="kraken",
            symbol=f"{base}/USD",
            market_type=MarketType.SPOT,
            quote_asset="USD",
        ),
        VenueCandidate(
            venue_key="pyth_feed",
            venue="pyth",
            symbol=f"Crypto.{base}/USD",
            market_type=MarketType.ORACLE,
            quote_asset="USD",
        ),
        VenueCandidate(
            venue_key="defillama_context",
            venue="defillama",
            symbol=base,
            market_type=MarketType.CONTEXT,
        ),
        VenueCandidate(
            venue_key="dexscreener",
            venue="dexscreener",
            symbol=base,
            market_type=MarketType.CONTEXT,
        ),
        VenueCandidate(
            venue_key="geckoterminal",
            venue="geckoterminal",
            symbol=base,
            market_type=MarketType.CONTEXT,
        ),
    )


def canonical_base_asset_from_hyperliquid_coin(coin: str) -> str:
    normalized = coin.strip()
    if not normalized or not normalized.replace("_", "").isalnum():
        raise ValueError(f"unsupported Hyperliquid coin for symbol mapping: {coin!r}")
    if normalized.startswith("k") and len(normalized) > 1 and normalized[1:].upper() == normalized[1:]:
        return normalized[1:].upper()
    return normalized.upper()


def binance_contract_base_from_hyperliquid_coin(coin: str) -> str:
    normalized = coin.strip()
    if not normalized or not normalized.replace("_", "").isalnum():
        raise ValueError(f"unsupported Hyperliquid coin for Binance mapping: {coin!r}")
    if normalized.startswith("k") and len(normalized) > 1 and normalized[1:].upper() == normalized[1:]:
        return f"1000{normalized[1:].upper()}"
    return normalized.upper()


def _materialize_probes(
    probes: Iterable[SymbolProbeResult | Mapping[str, object]],
) -> dict[str, SymbolProbeResult]:
    materialized: dict[str, SymbolProbeResult] = {}
    for probe in probes:
        item = probe if isinstance(probe, SymbolProbeResult) else SymbolProbeResult(**dict(probe))
        materialized[item.venue_key] = item
    return materialized


def _aggregate_external_status(
    *,
    verified_external: int,
    statuses: Sequence[MappingStatus],
) -> MappingStatus:
    if any(status == MappingStatus.AMBIGUOUS for status in statuses):
        return MappingStatus.AMBIGUOUS
    if any(status == MappingStatus.MANUAL_REVIEW_REQUIRED for status in statuses):
        return MappingStatus.MANUAL_REVIEW_REQUIRED
    if verified_external > 0:
        return MappingStatus.VERIFIED
    if statuses and all(status == MappingStatus.MISSING for status in statuses):
        return MappingStatus.MISSING
    return MappingStatus.NOT_CHECKED
