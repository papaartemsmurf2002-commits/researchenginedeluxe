# V2-AUDIT-ID: V2-AUD-UNIV-001
# V2-CONTRACTS: docs/contracts/universe_contract.md
# V2-BOUNDARY: research_only, as_of_universe, no_live_imports
# V2-OWNER: v2_universe
"""Hyperliquid universe parsing and snapshot generation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter
from tradingbotsuite.v2.universe.models import (
    AssetContextSnapshotRow,
    InstrumentCatalogRow,
    UniverseMode,
    UniverseRefreshResult,
    UniverseSnapshotRow,
)
from tradingbotsuite.v2.universe.rules import eligibility_reason, evidence_scope_for_mode, hip3_metadata_complete
from tradingbotsuite.v2.venues.hyperliquid.info import (
    HYPERLIQUID_META_AND_ASSET_CTXS_SOURCE,
    HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID,
    HyperliquidInfoClient,
    HyperliquidInfoFetchResult,
)

UNIVERSE_RULE_ID = "hl_perps_day_ntl_vlm_gte_5m_v1"


def load_payload_file(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def refresh_hyperliquid_universe(
    *,
    archive_root: str | Path,
    payload: Any | None = None,
    payload_file: str | Path | None = None,
    asof_date: date,
    min_day_notional_usd: int = 5_000_000,
    mode: UniverseMode = UniverseMode.AS_OF,
    include_hip3_dexs: bool = True,
    coverage_ratio: float = 1.0,
    coverage_min: float = 0.98,
    usable_months: int = 6,
    min_usable_months: int = 6,
    client: HyperliquidInfoClient | None = None,
) -> UniverseRefreshResult:
    payload_source = "inline_payload"
    venue_adapter_id = HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID
    source_endpoint = HYPERLIQUID_META_AND_ASSET_CTXS_SOURCE
    raw_request_id: str | None = None
    raw_response_id: str | None = None
    if payload is None:
        if payload_file is not None:
            payload = load_payload_file(payload_file)
            payload_source = "payload_file"
        else:
            fetch = _fetch_public_meta_and_asset_contexts(client)
            payload = fetch.payload
            payload_source = "public_api"
            venue_adapter_id = fetch.capability.adapter_id
            source_endpoint = fetch.raw_request.source
            raw_request_id = fetch.raw_request.request_id
            raw_response_id = fetch.raw_response.response_id
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    raw_payload_sha256 = canonical_json_hash(payload)
    run_id = f"universe-{asof_date.isoformat()}-{raw_payload_sha256[:16]}"
    start = datetime.combine(asof_date, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(asof_date, datetime.max.time(), tzinfo=UTC)
    raw_row = RawJsonlZstdWriter(layout, store).write_records(
        records=[{"type": "metaAndAssetCtxs", "payload": payload}],
        venue="hyperliquid",
        datatype="meta_and_asset_ctxs",
        date=asof_date.isoformat(),
        run_id=run_id,
        job_id=run_id,
        adapter_id=venue_adapter_id,
        source_endpoint_or_subscription=source_endpoint,
        symbols=(),
        start_ts=start,
        end_ts=end,
        filename="meta_and_asset_ctxs",
    )
    instruments, contexts = parse_meta_and_asset_contexts(
        payload,
        asof_ts=start,
        raw_payload_sha256=raw_payload_sha256,
        raw_file_id=raw_row.file_id,
        include_hip3_dexs=include_hip3_dexs,
    )
    rows = build_universe_rows(
        instruments=instruments,
        contexts=contexts,
        asof_date=asof_date,
        raw_payload_sha256=raw_payload_sha256,
        raw_file_id=raw_row.file_id,
        min_day_notional_usd=min_day_notional_usd,
        mode=mode,
        coverage_ratio=coverage_ratio,
        coverage_min=coverage_min,
        usable_months=usable_months,
        min_usable_months=min_usable_months,
    )
    snapshot_id = _snapshot_id(rows)
    rows = [row.model_copy(update={"snapshot_id": snapshot_id}) for row in rows]
    write_universe_tables(layout=layout, instruments=instruments, contexts=contexts, rows=rows)
    return UniverseRefreshResult(
        snapshot_id=snapshot_id,
        raw_file_id=raw_row.file_id,
        raw_payload_sha256=raw_payload_sha256,
        instrument_count=len(instruments),
        eligible_count=sum(1 for row in rows if row.eligible),
        asof_date=asof_date,
        universe_mode=mode,
        payload_source=payload_source,
        venue_adapter_id=venue_adapter_id,
        source_endpoint_or_subscription=source_endpoint,
        raw_request_id=raw_request_id,
        raw_response_id=raw_response_id,
    )


def _fetch_public_meta_and_asset_contexts(
    client: HyperliquidInfoClient | None,
) -> HyperliquidInfoFetchResult:
    active_client = client or HyperliquidInfoClient()
    if hasattr(active_client, "fetch_meta_and_asset_contexts"):
        return active_client.fetch_meta_and_asset_contexts()
    raise TypeError("Hyperliquid universe public_api client must return fetch provenance")


def parse_meta_and_asset_contexts(
    payload: Any,
    *,
    asof_ts: datetime,
    raw_payload_sha256: str,
    raw_file_id: str,
    include_hip3_dexs: bool = True,
) -> tuple[list[InstrumentCatalogRow], list[AssetContextSnapshotRow]]:
    meta, asset_contexts = _split_meta_and_contexts(payload)
    universe = meta.get("universe", [])
    instruments: list[InstrumentCatalogRow] = []
    contexts: list[AssetContextSnapshotRow] = []
    for index, instrument_meta in enumerate(universe):
        if not isinstance(instrument_meta, Mapping):
            continue
        context = asset_contexts[index] if index < len(asset_contexts) and isinstance(asset_contexts[index], Mapping) else {}
        instrument = _instrument_row(
            instrument_meta,
            asof_ts=asof_ts,
            raw_file_id=raw_file_id,
            include_hip3_dexs=include_hip3_dexs,
        )
        instruments.append(instrument)
        contexts.append(_asset_context_row(instrument, context))
    return instruments, contexts


def build_universe_rows(
    *,
    instruments: list[InstrumentCatalogRow],
    contexts: list[AssetContextSnapshotRow],
    asof_date: date,
    raw_payload_sha256: str,
    raw_file_id: str,
    min_day_notional_usd: int,
    mode: UniverseMode,
    coverage_ratio: float,
    coverage_min: float,
    usable_months: int,
    min_usable_months: int,
) -> list[UniverseSnapshotRow]:
    scope, accepted_allowed = evidence_scope_for_mode(mode)
    rows: list[UniverseSnapshotRow] = []
    context_by_id = {context.instrument_id: context for context in contexts}
    for instrument in sorted(instruments, key=lambda item: item.instrument_id):
        context = context_by_id[instrument.instrument_id]
        reason = eligibility_reason(
            instrument=instrument,
            day_ntl_vlm_usd=context.day_ntl_vlm_usd,
            min_day_notional_usd=min_day_notional_usd,
            coverage_ratio=coverage_ratio,
            coverage_min=coverage_min,
            usable_months=usable_months,
            min_usable_months=min_usable_months,
        )
        eligible = reason is None
        rows.append(
            UniverseSnapshotRow(
                snapshot_id="0" * 64,
                asof_date=asof_date,
                venue="hyperliquid",
                universe_rule_id=UNIVERSE_RULE_ID,
                universe_mode=mode,
                instrument_id=instrument.instrument_id,
                day_ntl_vlm_usd=context.day_ntl_vlm_usd,
                open_interest=context.open_interest,
                mark_px=context.mark_px,
                oracle_px=context.oracle_px,
                funding=context.funding,
                eligible_volume=context.day_ntl_vlm_usd >= min_day_notional_usd,
                eligible_coverage=coverage_ratio >= coverage_min,
                eligible_history=usable_months >= min_usable_months,
                eligible_status=instrument.status not in {"disabled", "delisted", "quarantine"},
                eligible_hip3_metadata=hip3_metadata_complete(instrument),
                eligible=eligible,
                exclusion_reason=reason,
                evidence_scope=scope,
                accepted_research_evidence_allowed=accepted_allowed and eligible,
                raw_payload_sha256=raw_payload_sha256,
                raw_file_id=raw_file_id,
            )
        )
    return rows


def write_universe_tables(
    *,
    layout: ArchiveLayout,
    instruments: list[InstrumentCatalogRow],
    contexts: list[AssetContextSnapshotRow],
    rows: list[UniverseSnapshotRow],
) -> None:
    _append_model_rows(layout.resolve("manifests", "instrument_catalog.parquet"), instruments, ["instrument_id"])
    _append_model_rows(
        layout.resolve("manifests", "asset_context_snapshots.parquet"),
        contexts,
        ["instrument_id"],
    )
    _append_model_rows(
        layout.resolve("manifests", "universe_snapshots.parquet"),
        rows,
        ["snapshot_id", "instrument_id"],
    )


def load_universe_rows(archive_root: str | Path) -> list[UniverseSnapshotRow]:
    path = ArchiveLayout(archive_root).resolve("manifests", "universe_snapshots.parquet")
    if not path.exists():
        return []
    return [UniverseSnapshotRow.model_validate(row) for row in pq.read_table(path).to_pylist()]


def select_asof_universe(
    *,
    archive_root: str | Path,
    asof_date: date,
    eligible_only: bool = False,
    mode: UniverseMode = UniverseMode.AS_OF,
) -> list[UniverseSnapshotRow]:
    rows = [
        row
        for row in load_universe_rows(archive_root)
        if row.asof_date <= asof_date and row.universe_mode == mode
    ]
    if not rows:
        return []
    latest_date = max(row.asof_date for row in rows)
    latest_snapshot = max(row.snapshot_id for row in rows if row.asof_date == latest_date)
    selected = [row for row in rows if row.asof_date == latest_date and row.snapshot_id == latest_snapshot]
    if eligible_only:
        selected = [row for row in selected if row.eligible]
    return sorted(selected, key=lambda row: row.instrument_id)


def explain_instrument(
    *,
    archive_root: str | Path,
    snapshot_id: str,
    instrument_id: str,
) -> UniverseSnapshotRow | None:
    for row in load_universe_rows(archive_root):
        if row.snapshot_id == snapshot_id and row.instrument_id == instrument_id:
            return row
    return None


def diff_snapshots(
    *,
    archive_root: str | Path,
    left_snapshot_id: str,
    right_snapshot_id: str,
) -> dict[str, list[str]]:
    rows = load_universe_rows(archive_root)
    left = {row.instrument_id: row for row in rows if row.snapshot_id == left_snapshot_id and row.eligible}
    right = {row.instrument_id: row for row in rows if row.snapshot_id == right_snapshot_id and row.eligible}
    return {
        "added": sorted(set(right) - set(left)),
        "removed": sorted(set(left) - set(right)),
        "unchanged": sorted(set(left) & set(right)),
    }


def _split_meta_and_contexts(payload: Any) -> tuple[Mapping[str, Any], list[Any]]:
    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[0], Mapping):
        return payload[0], list(payload[1] or [])
    if isinstance(payload, Mapping) and "meta" in payload and "assetCtxs" in payload:
        return payload["meta"], list(payload["assetCtxs"] or [])
    if isinstance(payload, Mapping) and "universe" in payload and "asset_contexts" in payload:
        return payload, list(payload["asset_contexts"] or [])
    raise ValueError("unsupported Hyperliquid metaAndAssetCtxs payload shape")


def _instrument_row(
    instrument_meta: Mapping[str, Any],
    *,
    asof_ts: datetime,
    raw_file_id: str,
    include_hip3_dexs: bool,
) -> InstrumentCatalogRow:
    venue_symbol = str(instrument_meta.get("name") or instrument_meta.get("coin") or "")
    if not venue_symbol:
        raise ValueError("Hyperliquid instrument missing name")
    is_hip3, namespace, canonical = _parse_symbol_namespace(venue_symbol)
    if is_hip3 and not include_hip3_dexs:
        status = "quarantine"
    else:
        status = str(instrument_meta.get("status") or "active")
    instrument_id = (
        f"hyperliquid:hip3:{namespace}:{canonical}"
        if is_hip3
        else f"hyperliquid:perp:{canonical}"
    )
    return InstrumentCatalogRow(
        instrument_id=instrument_id,
        venue="hyperliquid",
        venue_symbol=venue_symbol,
        canonical_symbol=canonical,
        market_type="perp",
        base_asset=canonical,
        quote_asset=str(instrument_meta.get("quoteAsset") or instrument_meta.get("quote_asset") or "USD"),
        settle_asset=str(instrument_meta.get("settleAsset") or instrument_meta.get("settle_asset") or "USDC"),
        first_seen_ts=asof_ts,
        last_seen_ts=asof_ts,
        status=status,
        sz_decimals=_optional_int(instrument_meta.get("szDecimals")),
        max_leverage=_optional_float(instrument_meta.get("maxLeverage")),
        only_isolated=_optional_bool(instrument_meta.get("onlyIsolated")),
        is_hip3_or_rwa=is_hip3 or bool(instrument_meta.get("isRwa") or instrument_meta.get("is_rwa")),
        dex_namespace=namespace,
        reference_market=_optional_str(instrument_meta.get("referenceMarket") or instrument_meta.get("reference_market")),
        oracle_source=_optional_str(instrument_meta.get("oracleSource") or instrument_meta.get("oracle_source")),
        reference_session_calendar=_optional_str(
            instrument_meta.get("referenceSessionCalendar") or instrument_meta.get("reference_session_calendar")
        ),
        weekend_behavior_documented=_optional_bool(
            instrument_meta.get("weekendBehaviorDocumented")
            if "weekendBehaviorDocumented" in instrument_meta
            else instrument_meta.get("weekend_behavior_documented")
        ),
        listing_age_days=_optional_int(instrument_meta.get("listingAgeDays") or instrument_meta.get("listing_age_days")),
        proxy_data_available=_optional_bool(
            instrument_meta.get("proxyDataAvailable")
            if "proxyDataAvailable" in instrument_meta
            else instrument_meta.get("proxy_data_available")
        ),
        source_snapshot_id=raw_file_id,
    )


def _asset_context_row(
    instrument: InstrumentCatalogRow,
    context: Mapping[str, Any],
) -> AssetContextSnapshotRow:
    return AssetContextSnapshotRow(
        instrument_id=instrument.instrument_id,
        venue_symbol=instrument.venue_symbol,
        day_ntl_vlm_usd=_optional_float(context.get("dayNtlVlm") or context.get("day_ntl_vlm")) or 0.0,
        open_interest=_optional_float(context.get("openInterest") or context.get("open_interest")),
        mark_px=_optional_float(context.get("markPx") or context.get("mark_px")),
        oracle_px=_optional_float(context.get("oraclePx") or context.get("oracle_px")),
        funding=_optional_float(context.get("funding")),
        raw_context=dict(context),
    )


def _parse_symbol_namespace(venue_symbol: str) -> tuple[bool, str | None, str]:
    if ":" not in venue_symbol:
        return False, None, venue_symbol.upper()
    namespace, symbol = venue_symbol.split(":", 1)
    return True, namespace.lower(), symbol.upper()


def _snapshot_id(rows: list[UniverseSnapshotRow]) -> str:
    identity_rows = [
        row.model_dump(mode="json", exclude={"snapshot_id", "created_at"})
        for row in sorted(rows, key=lambda item: item.instrument_id)
    ]
    return manifest_rows_hash(identity_rows)


def _append_model_rows(path: Path, records: list[Any], key_fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.exists():
        existing = pq.read_table(path).to_pylist()
    rows = [record.model_dump(mode="json") for record in records]
    by_key = {tuple(row.get(field) for field in key_fields): row for row in existing}
    for row in rows:
        by_key[tuple(row.get(field) for field in key_fields)] = row
    ordered = sorted(by_key.values(), key=lambda row: tuple(str(row.get(field, "")) for field in key_fields))
    pq.write_table(pa.Table.from_pylist(ordered), path, compression="zstd")


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes"}
    return bool(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
