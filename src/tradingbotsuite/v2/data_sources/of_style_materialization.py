# V2-AUDIT-ID: V2-AUD-DATASRC-050
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, no_archive_writes, no_gold_panel_claim
# V2-OWNER: v2_data_sources
"""Compact OF-style feature materialization from validated free raw archives."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import zipfile
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.security.boundary import require_research_boundary


DEFAULT_OF_STYLE_ARCHIVE_ROOT = Path(r"M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw")
DEFAULT_OF_STYLE_OUTPUT_ROOT = Path("data/research/of_style_feature_materialization/wpr106_552")
DEFAULT_OF_STYLE_VALIDATION_REPORT = (
    DEFAULT_OF_STYLE_ARCHIVE_ROOT / "manifests" / "wpr106-549-heavy-raw-archive-validation-report.json"
)
OF_STYLE_FAMILIES: tuple[str, ...] = (
    "bookDepth",
    "aggTrades",
    "bookTicker",
    "trades",
    "metrics",
    "klines",
    "markPriceKlines",
    "indexPriceKlines",
    "premiumIndexKlines",
)
KLINE_CONTEXT_FAMILIES: frozenset[str] = frozenset(
    {"klines", "markPriceKlines", "indexPriceKlines", "premiumIndexKlines"}
)
TRADE_FAMILIES: frozenset[str] = frozenset({"aggTrades", "trades"})
SUPPORTED_FEATURE_FAMILIES: frozenset[str] = frozenset(
    {"orderflow", "bbo_spread", "l2_depth", "derivatives_context", "kline_context"}
)


class OFStyleMaterializationSourceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_result_id: str = Field(min_length=64, max_length=64)
    family: str = Field(min_length=1)
    feature_family: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    interval: str | None = None
    day: str | None = None
    source_ref: str = Field(min_length=1)
    raw_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    output_ref: str = Field(min_length=1)
    output_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    output_bytes: int = Field(ge=0)
    status: Literal["materialized", "blocked"] = "materialized"
    input_row_count: int = Field(ge=0)
    feature_row_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    blocker_reasons: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    accepted_historical_coverage_proof: bool = False
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_source_result(self) -> "OFStyleMaterializationSourceResult":
        require_research_boundary(self, context="OF-style materialization source result")
        if self.accepted_historical_coverage_proof:
            raise ValueError("OF-style materialized features are not accepted historical coverage proof")
        if self.feature_family not in SUPPORTED_FEATURE_FAMILIES:
            raise ValueError("unsupported OF-style feature family")
        if self.status == "materialized":
            if self.blocker_reasons:
                raise ValueError("materialized source results cannot include blocker reasons")
            if self.feature_row_count <= 0:
                raise ValueError("materialized source results require feature rows")
        if self.status == "blocked" and not self.blocker_reasons:
            raise ValueError("blocked source results require blocker reasons")
        PurePosixPath(self.output_ref)
        expected_id = of_style_materialization_source_result_id_for(self)
        if self.source_result_id != expected_id:
            raise ValueError("source_result_id does not match source result")
        return self


class OFStyleMaterializationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "of_style_feature_materialization_report"
    materialization_report_id: str = Field(min_length=64, max_length=64)
    archive_root: str = Field(min_length=1)
    archive_validation_report_ref: str = Field(min_length=1)
    output_root: str = Field(min_length=1)
    materialization_scope: str = Field(min_length=1)
    bucket_seconds: int = Field(ge=1)
    requested_families: tuple[str, ...] = Field(min_length=1)
    requested_symbols: tuple[str, ...] = ()
    requested_intervals: tuple[str, ...] = ()
    max_sources_per_family: int | None = Field(default=None, ge=1)
    max_sources_per_symbol_per_family: int | None = Field(default=None, ge=1)
    archive_source_count: int = Field(ge=0)
    archive_complete_source_count: int = Field(ge=0)
    archive_missing_source_count: int = Field(ge=0)
    archive_invalid_source_count: int = Field(ge=0)
    archive_partial_file_count: int = Field(ge=0)
    materialized_source_count: int = Field(ge=0)
    blocked_source_count: int = Field(ge=0)
    input_row_count: int = Field(ge=0)
    feature_row_count: int = Field(ge=0)
    family_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    source_results: tuple[OFStyleMaterializationSourceResult, ...] = ()
    source_result_manifest_hash: str = Field(min_length=64, max_length=64)
    final_audit_data_ready: bool = False
    blocker_reasons: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    accepted_historical_coverage_proof: bool = False
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> "OFStyleMaterializationReport":
        require_research_boundary(self, context="OF-style materialization report")
        if self.report_type != "of_style_feature_materialization_report":
            raise ValueError("report_type must be of_style_feature_materialization_report")
        if self.accepted_historical_coverage_proof:
            raise ValueError("OF-style materialization reports are not accepted historical coverage proof")
        if self.archive_complete_source_count != self.archive_source_count:
            raise ValueError("archive_complete_source_count must match archive_source_count")
        if self.archive_missing_source_count or self.archive_invalid_source_count or self.archive_partial_file_count:
            raise ValueError("authoritative OF-style archive cannot have missing, invalid, or partial sources")
        if self.materialized_source_count + self.blocked_source_count != len(self.source_results):
            raise ValueError("source result counts must match source_results")
        if self.input_row_count != sum(row.input_row_count for row in self.source_results):
            raise ValueError("input_row_count must match source result rows")
        if self.feature_row_count != sum(row.feature_row_count for row in self.source_results):
            raise ValueError("feature_row_count must match source result rows")
        if self.source_result_manifest_hash != of_style_materialization_source_results_hash(self.source_results):
            raise ValueError("source_result_manifest_hash does not match source_results")
        if self.final_audit_data_ready and self.blocker_reasons:
            raise ValueError("final_audit_data_ready cannot include blocker reasons")
        if not self.final_audit_data_ready and not self.blocker_reasons:
            raise ValueError("not-ready materialization reports require blocker reasons")
        expected_id = of_style_materialization_report_id_for(self)
        if self.materialization_report_id != expected_id:
            raise ValueError("materialization_report_id does not match report")
        return self


@dataclass(frozen=True)
class OFStyleMaterializationConfig:
    archive_root: Path = DEFAULT_OF_STYLE_ARCHIVE_ROOT
    validation_report_path: Path = DEFAULT_OF_STYLE_VALIDATION_REPORT
    output_root: Path = DEFAULT_OF_STYLE_OUTPUT_ROOT
    families: tuple[str, ...] = OF_STYLE_FAMILIES
    symbols: tuple[str, ...] = ()
    intervals: tuple[str, ...] = ("1m",)
    bucket_seconds: int = 60
    max_sources_per_family: int | None = None
    max_sources_per_symbol_per_family: int | None = 1
    require_complete_archive: bool = True


def materialize_of_style_archive(config: OFStyleMaterializationConfig | None = None) -> OFStyleMaterializationReport:
    parsed = config or OFStyleMaterializationConfig()
    validation_report = _load_validation_report(parsed.validation_report_path)
    if parsed.require_complete_archive:
        _require_complete_archive(validation_report)

    parsed.output_root.mkdir(parents=True, exist_ok=True)
    selected_sources = list(_iter_selected_sources(parsed))
    source_results: list[OFStyleMaterializationSourceResult] = []
    for source_path in selected_sources:
        source_results.append(
            materialize_of_style_source(
                source_path,
                archive_root=parsed.archive_root,
                output_root=parsed.output_root,
                bucket_seconds=parsed.bucket_seconds,
            )
        )

    family_counts = _family_counts(source_results)
    materialized = sum(1 for row in source_results if row.status == "materialized")
    blocked = len(source_results) - materialized
    blocker_reasons: tuple[str, ...] = ()
    if blocked:
        blocker_reasons = tuple(sorted({reason for row in source_results for reason in row.blocker_reasons}))
    if not source_results:
        blocker_reasons = ("no_sources_selected",)

    report_payload = {
        "archive_root": str(parsed.archive_root),
        "archive_validation_report_ref": str(parsed.validation_report_path),
        "output_root": str(parsed.output_root),
        "materialization_scope": _materialization_scope(parsed),
        "bucket_seconds": parsed.bucket_seconds,
        "requested_families": tuple(parsed.families),
        "requested_symbols": tuple(parsed.symbols),
        "requested_intervals": tuple(parsed.intervals),
        "max_sources_per_family": parsed.max_sources_per_family,
        "max_sources_per_symbol_per_family": parsed.max_sources_per_symbol_per_family,
        "archive_source_count": int(validation_report["source_count"]),
        "archive_complete_source_count": int(validation_report["complete_source_count"]),
        "archive_missing_source_count": int(validation_report["missing_source_count"]),
        "archive_invalid_source_count": int(validation_report["invalid_source_count"]),
        "archive_partial_file_count": int(validation_report["partial_file_count"]),
        "materialized_source_count": materialized,
        "blocked_source_count": blocked,
        "input_row_count": sum(row.input_row_count for row in source_results),
        "feature_row_count": sum(row.feature_row_count for row in source_results),
        "family_counts": family_counts,
        "source_results": tuple(source_results),
        "source_result_manifest_hash": of_style_materialization_source_results_hash(tuple(source_results)),
        "final_audit_data_ready": bool(source_results) and blocked == 0,
        "blocker_reasons": blocker_reasons,
        "notes": (
            "WPR106-549 archive validation remains the authoritative full-source completeness proof.",
            "This pass materializes compact research features directly from raw ZIP/CSV sources without central row-level expansion.",
            "Requester-pays or unavailable Hyperliquid-native historical data is outside this strict-free data baseline.",
            "Generated rows are research-only and are not strategy, candidate, paper, live, order, sizing, or promotion evidence.",
        ),
        **dict(RESEARCH_BOUNDARY),
    }
    report = OFStyleMaterializationReport(
        **report_payload,
        materialization_report_id=of_style_materialization_report_id_from_payload(report_payload),
    )
    report_path = parsed.output_root / "manifests" / "wpr106-552-of-style-feature-materialization-report.json"
    _write_json_with_sha(report_path, report.model_dump(mode="json"))
    return report


def materialize_of_style_source(
    source_path: str | Path,
    *,
    archive_root: str | Path,
    output_root: str | Path,
    bucket_seconds: int = 60,
) -> OFStyleMaterializationSourceResult:
    path = Path(source_path)
    archive_root_path = Path(archive_root)
    output_root_path = Path(output_root)
    metadata = _load_source_metadata(path, archive_root=archive_root_path)
    family = str(metadata["family"])

    try:
        rows = _feature_rows_for_source(path, metadata=metadata, bucket_seconds=bucket_seconds)
        status: Literal["materialized", "blocked"] = "materialized" if rows else "blocked"
        blockers: tuple[str, ...] = () if rows else ("no_feature_rows",)
    except Exception as exc:
        rows = []
        status = "blocked"
        blockers = (f"materialization_failed:{type(exc).__name__}",)

    feature_family = _feature_family_for(family)
    output_ref = _output_ref_for_source(metadata, feature_family=feature_family, source_path=path)
    output_path = output_root_path / output_ref
    row_manifest_hash = manifest_rows_hash(rows)
    if rows:
        _write_jsonl_with_sha(output_path, rows)
        output_sha256 = _sha256_file(output_path)
        output_bytes = output_path.stat().st_size
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        _write_text_sha(output_path)
        output_sha256 = _sha256_file(output_path)
        output_bytes = 0

    result_payload = {
        "family": family,
        "feature_family": feature_family,
        "dataset": str(metadata.get("dataset") or family),
        "symbol": str(metadata.get("symbol") or _symbol_from_venue(str(metadata["venue_symbol"]))),
        "venue_symbol": str(metadata["venue_symbol"]),
        "interval": metadata.get("interval"),
        "day": metadata.get("day"),
        "source_ref": str(metadata.get("raw_ref") or _relative_ref(path, archive_root_path)),
        "raw_sha256": metadata.get("raw_sha256") or metadata.get("checksum_sha256"),
        "output_ref": output_ref,
        "output_sha256": output_sha256,
        "output_bytes": output_bytes,
        "status": status,
        "input_row_count": sum(int(row.get("source_row_count", 0)) for row in rows),
        "feature_row_count": len(rows),
        "row_manifest_hash": row_manifest_hash,
        "blocker_reasons": blockers,
        **dict(RESEARCH_BOUNDARY),
    }
    return OFStyleMaterializationSourceResult(
        **result_payload,
        source_result_id=of_style_materialization_source_result_id_from_payload(result_payload),
    )


def of_style_materialization_source_result_id_for(
    result: OFStyleMaterializationSourceResult | Mapping[str, Any],
) -> str:
    payload = result.model_dump(mode="json") if isinstance(result, OFStyleMaterializationSourceResult) else dict(result)
    return of_style_materialization_source_result_id_from_payload(payload)


def of_style_materialization_source_result_id_from_payload(payload: Mapping[str, Any]) -> str:
    return canonical_json_hash(
        {
            "schema_version": payload.get("schema_version", V2_SCHEMA_VERSION),
            "family": payload["family"],
            "feature_family": payload["feature_family"],
            "dataset": payload["dataset"],
            "venue_symbol": payload["venue_symbol"],
            "interval": payload.get("interval"),
            "day": payload.get("day"),
            "source_ref": payload["source_ref"],
            "raw_sha256": payload.get("raw_sha256"),
            "output_ref": payload["output_ref"],
            "output_sha256": payload.get("output_sha256"),
            "status": payload["status"],
            "input_row_count": payload["input_row_count"],
            "feature_row_count": payload["feature_row_count"],
            "row_manifest_hash": payload["row_manifest_hash"],
            "blocker_reasons": tuple(payload.get("blocker_reasons", ())),
        }
    )


def of_style_materialization_source_results_hash(
    rows: Iterable[OFStyleMaterializationSourceResult | Mapping[str, Any]],
) -> str:
    return manifest_rows_hash(
        row.model_dump(mode="json") if isinstance(row, OFStyleMaterializationSourceResult) else dict(row)
        for row in rows
    )


def of_style_materialization_report_id_for(report: OFStyleMaterializationReport | Mapping[str, Any]) -> str:
    payload = report.model_dump(mode="json") if isinstance(report, OFStyleMaterializationReport) else dict(report)
    return of_style_materialization_report_id_from_payload(payload)


def of_style_materialization_report_id_from_payload(payload: Mapping[str, Any]) -> str:
    return canonical_json_hash(
        {
            "schema_version": payload.get("schema_version", V2_SCHEMA_VERSION),
            "report_type": payload.get("report_type", "of_style_feature_materialization_report"),
            "archive_root": payload["archive_root"],
            "archive_validation_report_ref": payload["archive_validation_report_ref"],
            "output_root": payload["output_root"],
            "materialization_scope": payload["materialization_scope"],
            "bucket_seconds": payload["bucket_seconds"],
            "requested_families": tuple(payload["requested_families"]),
            "requested_symbols": tuple(payload.get("requested_symbols", ())),
            "requested_intervals": tuple(payload.get("requested_intervals", ())),
            "max_sources_per_family": payload.get("max_sources_per_family"),
            "max_sources_per_symbol_per_family": payload.get("max_sources_per_symbol_per_family"),
            "archive_source_count": payload["archive_source_count"],
            "archive_complete_source_count": payload["archive_complete_source_count"],
            "archive_missing_source_count": payload["archive_missing_source_count"],
            "archive_invalid_source_count": payload["archive_invalid_source_count"],
            "archive_partial_file_count": payload["archive_partial_file_count"],
            "materialized_source_count": payload["materialized_source_count"],
            "blocked_source_count": payload["blocked_source_count"],
            "input_row_count": payload["input_row_count"],
            "feature_row_count": payload["feature_row_count"],
            "family_counts": payload["family_counts"],
            "source_result_manifest_hash": payload["source_result_manifest_hash"],
            "final_audit_data_ready": payload["final_audit_data_ready"],
            "blocker_reasons": tuple(payload.get("blocker_reasons", ())),
        }
    )


def _feature_rows_for_source(path: Path, *, metadata: Mapping[str, Any], bucket_seconds: int) -> list[dict[str, Any]]:
    family = str(metadata["family"])
    if family in TRADE_FAMILIES:
        return _trade_orderflow_rows(path, metadata=metadata, bucket_seconds=bucket_seconds)
    if family == "bookTicker":
        return _book_ticker_rows(path, metadata=metadata, bucket_seconds=bucket_seconds)
    if family == "bookDepth":
        return _book_depth_rows(path, metadata=metadata, bucket_seconds=bucket_seconds)
    if family == "metrics":
        return _metrics_rows(path, metadata=metadata)
    if family in KLINE_CONTEXT_FAMILIES:
        return _kline_context_rows(path, metadata=metadata)
    raise ValueError(f"unsupported OF-style family: {family}")


def _trade_orderflow_rows(path: Path, *, metadata: Mapping[str, Any], bucket_seconds: int) -> list[dict[str, Any]]:
    family = str(metadata["family"])
    buckets: dict[int, dict[str, float | int]] = defaultdict(
        lambda: {
            "source_row_count": 0,
            "trade_count": 0,
            "total_volume": 0.0,
            "total_quote_volume": 0.0,
            "buy_volume": 0.0,
            "sell_volume": 0.0,
            "unknown_side_volume": 0.0,
            "buy_quote_volume": 0.0,
            "sell_quote_volume": 0.0,
            "unknown_side_quote_volume": 0.0,
        }
    )
    for record in _zip_csv_dict_rows(path, family=family):
        price = _to_float(record.get("price"))
        quantity = _to_float(record.get("quantity") if family == "aggTrades" else record.get("qty"))
        ts = _to_int(record.get("transact_time") if family == "aggTrades" else record.get("time"))
        if price is None or quantity is None or ts is None or price <= 0:
            continue
        quote_quantity = _to_float(record.get("quote_qty"))
        if quote_quantity is None:
            quote_quantity = price * quantity
        side = _side_from_buyer_maker(record.get("is_buyer_maker"))
        bucket_start_ms = _bucket_start_ms(ts, bucket_seconds)
        bucket = buckets[bucket_start_ms]
        bucket["source_row_count"] = int(bucket["source_row_count"]) + 1
        bucket["trade_count"] = int(bucket["trade_count"]) + 1
        bucket["total_volume"] = float(bucket["total_volume"]) + quantity
        bucket["total_quote_volume"] = float(bucket["total_quote_volume"]) + quote_quantity
        bucket[f"{side}_volume"] = float(bucket[f"{side}_volume"]) + quantity
        bucket[f"{side}_quote_volume"] = float(bucket[f"{side}_quote_volume"]) + quote_quantity
    rows: list[dict[str, Any]] = []
    for bucket_start_ms in sorted(buckets):
        bucket = buckets[bucket_start_ms]
        total_volume = float(bucket["total_volume"])
        total_quote = float(bucket["total_quote_volume"])
        if total_volume <= 0 or int(bucket["trade_count"]) <= 0:
            continue
        row = _base_feature_row(
            metadata,
            feature_family="orderflow",
            bucket_start_ms=bucket_start_ms,
            bucket_end_ms=bucket_start_ms + bucket_seconds * 1000,
            bucket_seconds=bucket_seconds,
        )
        buy_volume = float(bucket["buy_volume"])
        sell_volume = float(bucket["sell_volume"])
        buy_quote = float(bucket["buy_quote_volume"])
        sell_quote = float(bucket["sell_quote_volume"])
        row.update(
            {
                "source_row_count": int(bucket["source_row_count"]),
                "trade_count": int(bucket["trade_count"]),
                "total_volume": _round_float(total_volume),
                "total_quote_volume": _round_float(total_quote),
                "buy_volume": _round_float(buy_volume),
                "sell_volume": _round_float(sell_volume),
                "unknown_side_volume": _round_float(float(bucket["unknown_side_volume"])),
                "buy_quote_volume": _round_float(buy_quote),
                "sell_quote_volume": _round_float(sell_quote),
                "unknown_side_quote_volume": _round_float(float(bucket["unknown_side_quote_volume"])),
                "vwap": _round_float(total_quote / total_volume),
                "trade_imbalance": _round_float(_imbalance(buy_volume, sell_volume)),
                "quote_trade_imbalance": _round_float(_imbalance(buy_quote, sell_quote)),
            }
        )
        rows.append(_with_row_hash(row))
    return rows


def _book_ticker_rows(path: Path, *, metadata: Mapping[str, Any], bucket_seconds: int) -> list[dict[str, Any]]:
    buckets: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "source_row_count": 0,
            "sum_mid": 0.0,
            "sum_spread": 0.0,
            "sum_spread_bps": 0.0,
            "sum_bid_size": 0.0,
            "sum_ask_size": 0.0,
            "last_ts": -1,
            "last_bid": 0.0,
            "last_ask": 0.0,
            "last_bid_size": 0.0,
            "last_ask_size": 0.0,
        }
    )
    for record in _zip_csv_dict_rows(path, family="bookTicker"):
        bid = _to_float(record.get("best_bid_price"))
        ask = _to_float(record.get("best_ask_price"))
        bid_size = _to_float(record.get("best_bid_qty")) or 0.0
        ask_size = _to_float(record.get("best_ask_qty")) or 0.0
        ts = _to_int(record.get("event_time")) or _to_int(record.get("transaction_time"))
        if bid is None or ask is None or ts is None or bid <= 0 or ask <= 0 or ask < bid:
            continue
        mid = (bid + ask) / 2.0
        spread = ask - bid
        bucket_start_ms = _bucket_start_ms(ts, bucket_seconds)
        bucket = buckets[bucket_start_ms]
        count = int(bucket["source_row_count"]) + 1
        bucket["source_row_count"] = count
        bucket["sum_mid"] = float(bucket["sum_mid"]) + mid
        bucket["sum_spread"] = float(bucket["sum_spread"]) + spread
        bucket["sum_spread_bps"] = float(bucket["sum_spread_bps"]) + (spread / mid * 10000.0)
        bucket["sum_bid_size"] = float(bucket["sum_bid_size"]) + bid_size
        bucket["sum_ask_size"] = float(bucket["sum_ask_size"]) + ask_size
        if ts >= int(bucket["last_ts"]):
            bucket["last_ts"] = ts
            bucket["last_bid"] = bid
            bucket["last_ask"] = ask
            bucket["last_bid_size"] = bid_size
            bucket["last_ask_size"] = ask_size
    rows: list[dict[str, Any]] = []
    for bucket_start_ms in sorted(buckets):
        bucket = buckets[bucket_start_ms]
        count = int(bucket["source_row_count"])
        if count <= 0:
            continue
        row = _base_feature_row(
            metadata,
            feature_family="bbo_spread",
            bucket_start_ms=bucket_start_ms,
            bucket_end_ms=bucket_start_ms + bucket_seconds * 1000,
            bucket_seconds=bucket_seconds,
        )
        last_bid = float(bucket["last_bid"])
        last_ask = float(bucket["last_ask"])
        last_bid_size = float(bucket["last_bid_size"])
        last_ask_size = float(bucket["last_ask_size"])
        row.update(
            {
                "source_row_count": count,
                "book_ticker_count": count,
                "mean_mid": _round_float(float(bucket["sum_mid"]) / count),
                "mean_spread": _round_float(float(bucket["sum_spread"]) / count),
                "mean_spread_bps": _round_float(float(bucket["sum_spread_bps"]) / count),
                "mean_bid_size": _round_float(float(bucket["sum_bid_size"]) / count),
                "mean_ask_size": _round_float(float(bucket["sum_ask_size"]) / count),
                "last_bid": _round_float(last_bid),
                "last_ask": _round_float(last_ask),
                "last_mid": _round_float((last_bid + last_ask) / 2.0),
                "last_bid_size": _round_float(last_bid_size),
                "last_ask_size": _round_float(last_ask_size),
                "top_of_book_size_imbalance": _round_float(_imbalance(last_bid_size, last_ask_size)),
            }
        )
        rows.append(_with_row_hash(row))
    return rows


def _book_depth_rows(path: Path, *, metadata: Mapping[str, Any], bucket_seconds: int) -> list[dict[str, Any]]:
    buckets: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "source_row_count": 0,
            "timestamps": set(),
            "bid_depth_total": 0.0,
            "ask_depth_total": 0.0,
            "bid_notional_total": 0.0,
            "ask_notional_total": 0.0,
            "inside_depth_rows": 0,
            "outside_depth_rows": 0,
        }
    )
    for record in _zip_csv_dict_rows(path, family="bookDepth"):
        ts = _timestamp_ms(record.get("timestamp"))
        percentage = _to_float(record.get("percentage"))
        depth = _to_float(record.get("depth"))
        notional = _to_float(record.get("notional"))
        if ts is None or percentage is None or depth is None or notional is None:
            continue
        bucket_start_ms = _bucket_start_ms(ts, bucket_seconds)
        bucket = buckets[bucket_start_ms]
        bucket["source_row_count"] = int(bucket["source_row_count"]) + 1
        bucket["timestamps"].add(ts)
        if percentage < 0:
            bucket["bid_depth_total"] = float(bucket["bid_depth_total"]) + depth
            bucket["bid_notional_total"] = float(bucket["bid_notional_total"]) + notional
            bucket["inside_depth_rows"] = int(bucket["inside_depth_rows"]) + (1 if percentage >= -1 else 0)
            bucket["outside_depth_rows"] = int(bucket["outside_depth_rows"]) + (1 if percentage < -1 else 0)
        elif percentage > 0:
            bucket["ask_depth_total"] = float(bucket["ask_depth_total"]) + depth
            bucket["ask_notional_total"] = float(bucket["ask_notional_total"]) + notional
            bucket["inside_depth_rows"] = int(bucket["inside_depth_rows"]) + (1 if percentage <= 1 else 0)
            bucket["outside_depth_rows"] = int(bucket["outside_depth_rows"]) + (1 if percentage > 1 else 0)
    rows: list[dict[str, Any]] = []
    for bucket_start_ms in sorted(buckets):
        bucket = buckets[bucket_start_ms]
        count = int(bucket["source_row_count"])
        if count <= 0:
            continue
        bid_depth = float(bucket["bid_depth_total"])
        ask_depth = float(bucket["ask_depth_total"])
        bid_notional = float(bucket["bid_notional_total"])
        ask_notional = float(bucket["ask_notional_total"])
        row = _base_feature_row(
            metadata,
            feature_family="l2_depth",
            bucket_start_ms=bucket_start_ms,
            bucket_end_ms=bucket_start_ms + bucket_seconds * 1000,
            bucket_seconds=bucket_seconds,
        )
        row.update(
            {
                "source_row_count": count,
                "snapshot_count": len(bucket["timestamps"]),
                "bid_depth_total": _round_float(bid_depth),
                "ask_depth_total": _round_float(ask_depth),
                "bid_notional_total": _round_float(bid_notional),
                "ask_notional_total": _round_float(ask_notional),
                "depth_imbalance": _round_float(_imbalance(bid_depth, ask_depth)),
                "notional_imbalance": _round_float(_imbalance(bid_notional, ask_notional)),
                "inside_depth_rows": int(bucket["inside_depth_rows"]),
                "outside_depth_rows": int(bucket["outside_depth_rows"]),
            }
        )
        rows.append(_with_row_hash(row))
    return rows


def _metrics_rows(path: Path, *, metadata: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in _zip_csv_dict_rows(path, family="metrics"):
        ts = _timestamp_ms(record.get("create_time"))
        if ts is None:
            continue
        numeric_features = {
            key: value
            for key, value in ((key, _to_float(raw_value)) for key, raw_value in record.items())
            if key not in {"create_time", "symbol"} and value is not None and math.isfinite(value)
        }
        if not numeric_features:
            continue
        row = _base_feature_row(
            metadata,
            feature_family="derivatives_context",
            bucket_start_ms=ts,
            bucket_end_ms=ts,
            bucket_seconds=None,
        )
        row.update(
            {
                "feature_timestamp_ms": ts,
                "source_row_count": 1,
                "numeric_features": {key: _round_float(value) for key, value in sorted(numeric_features.items())},
            }
        )
        rows.append(_with_row_hash(row))
    return rows


def _kline_context_rows(path: Path, *, metadata: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in _zip_csv_dict_rows(path, family=str(metadata["family"])):
        open_time = _to_int(record.get("open_time"))
        close_time = _to_int(record.get("close_time"))
        open_price = _to_float(record.get("open"))
        high = _to_float(record.get("high"))
        low = _to_float(record.get("low"))
        close = _to_float(record.get("close"))
        if (
            open_time is None
            or close_time is None
            or open_price is None
            or high is None
            or low is None
            or close is None
            or open_price < 0
            or high < 0
            or low < 0
            or close < 0
        ):
            continue
        row = _base_feature_row(
            metadata,
            feature_family="kline_context",
            bucket_start_ms=open_time,
            bucket_end_ms=close_time + 1,
            bucket_seconds=_interval_seconds(metadata.get("interval")),
        )
        row.update(
            {
                "source_row_count": 1,
                "open": _round_float(open_price),
                "high": _round_float(high),
                "low": _round_float(low),
                "close": _round_float(close),
                "volume": _round_float(_to_float(record.get("volume")) or 0.0),
                "quote_volume": _round_float(_to_float(record.get("quote_volume")) or 0.0),
                "trade_count": _to_int(record.get("count")) or 0,
                "taker_buy_volume": _round_float(_to_float(record.get("taker_buy_volume")) or 0.0),
                "taker_buy_quote_volume": _round_float(_to_float(record.get("taker_buy_quote_volume")) or 0.0),
            }
        )
        rows.append(_with_row_hash(row))
    return rows


def _base_feature_row(
    metadata: Mapping[str, Any],
    *,
    feature_family: str,
    bucket_start_ms: int,
    bucket_end_ms: int,
    bucket_seconds: int | None,
) -> dict[str, Any]:
    family = str(metadata["family"])
    return {
        "schema_version": V2_SCHEMA_VERSION,
        "feature_family": feature_family,
        "source_family": family,
        "dataset": str(metadata.get("dataset") or family),
        "source_id": f"binance_usdm_daily_{family}",
        "venue": "binance_usdm",
        "venue_symbol": str(metadata["venue_symbol"]),
        "symbol": str(metadata.get("symbol") or _symbol_from_venue(str(metadata["venue_symbol"]))),
        "market_type": "perpetual",
        "interval": metadata.get("interval"),
        "day": metadata.get("day"),
        "bucket_seconds": bucket_seconds,
        "bucket_start_ms": bucket_start_ms,
        "bucket_end_ms": bucket_end_ms,
        "source_ref": str(metadata.get("raw_ref") or ""),
        "raw_sha256": metadata.get("raw_sha256") or metadata.get("checksum_sha256"),
        "accepted_historical_coverage_proof": False,
        **dict(RESEARCH_BOUNDARY),
    }


def _iter_selected_sources(config: OFStyleMaterializationConfig) -> Iterator[Path]:
    family_totals: dict[str, int] = defaultdict(int)
    for family in config.families:
        family_root = Path(config.archive_root) / "data" / "futures" / "um" / "daily" / family
        if not family_root.exists():
            continue
        for source_path in _iter_family_sources(
            family_root,
            family=family,
            symbols=config.symbols,
            intervals=config.intervals if family in KLINE_CONTEXT_FAMILIES else (),
            max_sources_per_symbol_per_family=config.max_sources_per_symbol_per_family,
        ):
            if config.max_sources_per_family is not None and family_totals[family] >= config.max_sources_per_family:
                break
            family_totals[family] += 1
            yield source_path


def _iter_family_sources(
    family_root: Path,
    *,
    family: str,
    symbols: Sequence[str],
    intervals: Sequence[str],
    max_sources_per_symbol_per_family: int | None,
) -> Iterator[Path]:
    wanted_symbols = {_venue_symbol(symbol) for symbol in symbols}
    wanted_intervals = {interval for interval in intervals if interval}
    for symbol_dir in sorted((path for path in family_root.iterdir() if path.is_dir()), key=lambda item: item.name):
        if wanted_symbols and symbol_dir.name.upper() not in wanted_symbols:
            continue
        emitted_for_symbol = 0
        if family in KLINE_CONTEXT_FAMILIES:
            interval_dirs = sorted((path for path in symbol_dir.iterdir() if path.is_dir()), key=lambda item: item.name)
            for interval_dir in interval_dirs:
                if wanted_intervals and interval_dir.name not in wanted_intervals:
                    continue
                for source_path in sorted(interval_dir.glob("*.zip"), key=lambda item: item.name):
                    yield source_path
                    emitted_for_symbol += 1
                    if (
                        max_sources_per_symbol_per_family is not None
                        and emitted_for_symbol >= max_sources_per_symbol_per_family
                    ):
                        break
                if (
                    max_sources_per_symbol_per_family is not None
                    and emitted_for_symbol >= max_sources_per_symbol_per_family
                ):
                    break
        else:
            for source_path in sorted(symbol_dir.glob("*.zip"), key=lambda item: item.name):
                yield source_path
                emitted_for_symbol += 1
                if max_sources_per_symbol_per_family is not None and emitted_for_symbol >= max_sources_per_symbol_per_family:
                    break


def _zip_csv_dict_rows(path: Path, *, family: str) -> Iterator[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if not names:
            return
        with archive.open(names[0]) as handle:
            text = io.TextIOWrapper(handle, encoding="utf-8", newline="")
            reader = csv.reader(text)
            try:
                first_row = next(reader)
            except StopIteration:
                return
            header = _csv_header_for(family, first_row)
            if _looks_like_header(first_row, header):
                rows = reader
            else:
                rows = _prepend(first_row, reader)
            for row in rows:
                if not row:
                    continue
                normalized = {header[index]: row[index] for index in range(min(len(header), len(row)))}
                yield normalized


def _csv_header_for(family: str, first_row: Sequence[str]) -> tuple[str, ...]:
    headers = {
        "aggTrades": ("agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"),
        "trades": ("id", "price", "qty", "quote_qty", "time", "is_buyer_maker"),
        "bookTicker": (
            "update_id",
            "best_bid_price",
            "best_bid_qty",
            "best_ask_price",
            "best_ask_qty",
            "transaction_time",
            "event_time",
        ),
        "bookDepth": ("timestamp", "percentage", "depth", "notional"),
        "metrics": (
            "create_time",
            "symbol",
            "sum_open_interest",
            "sum_open_interest_value",
            "count_toptrader_long_short_ratio",
            "sum_toptrader_long_short_ratio",
            "count_long_short_ratio",
            "sum_taker_long_short_vol_ratio",
        ),
        "klines": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
        "markPriceKlines": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
        "indexPriceKlines": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
        "premiumIndexKlines": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
    }
    if family not in headers:
        raise ValueError(f"unsupported CSV family: {family}")
    return headers[family]


def _looks_like_header(row: Sequence[str], header: Sequence[str]) -> bool:
    lowered = tuple(value.strip().lower() for value in row)
    expected = tuple(value.lower() for value in header)
    if lowered[: len(expected)] == expected:
        return True
    return any(value in expected for value in lowered)


def _prepend(first: Sequence[str], rest: Iterable[Sequence[str]]) -> Iterator[Sequence[str]]:
    yield first
    yield from rest


def _load_validation_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("report_type") != "wpr106_549_heavy_raw_archive_validation":
        raise ValueError("unexpected OF-style archive validation report type")
    require_research_boundary(payload, context="OF-style archive validation report")
    return payload


def _require_complete_archive(report: Mapping[str, Any]) -> None:
    if int(report.get("source_count", 0)) <= 0:
        raise ValueError("OF-style archive validation report contains no sources")
    if int(report.get("complete_source_count", 0)) != int(report.get("source_count", -1)):
        raise ValueError("OF-style archive validation report is not complete")
    for key in ("missing_source_count", "invalid_source_count", "partial_file_count"):
        if int(report.get(key, 0)):
            raise ValueError(f"OF-style archive validation report has nonzero {key}")


def _load_source_metadata(path: Path, *, archive_root: Path) -> dict[str, Any]:
    metadata_path = path.with_name(path.name + ".metadata.json")
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        require_research_boundary(metadata, context="OF-style source metadata")
        return metadata
    return _metadata_from_path(path, archive_root=archive_root)


def _metadata_from_path(path: Path, *, archive_root: Path) -> dict[str, Any]:
    relative = _relative_ref(path, archive_root)
    parts = PurePosixPath(relative).parts
    if len(parts) < 7:
        raise ValueError("cannot infer OF-style metadata from source path")
    family = parts[4]
    venue_symbol = parts[5]
    interval: str | None = None
    if family in KLINE_CONTEXT_FAMILIES:
        interval = parts[6]
    stem = path.stem
    day = stem.rsplit("-", 3)[-3:]
    day_value = "-".join(day) if len(day) == 3 else None
    return {
        "family": family,
        "dataset": f"{family}:{interval}" if interval else family,
        "symbol": _symbol_from_venue(venue_symbol),
        "venue_symbol": venue_symbol,
        "interval": interval,
        "day": day_value,
        "raw_ref": relative,
        "raw_sha256": _sha256_file(path),
        **dict(RESEARCH_BOUNDARY),
    }


def _output_ref_for_source(metadata: Mapping[str, Any], *, feature_family: str, source_path: Path) -> str:
    family = str(metadata["family"])
    venue_symbol = str(metadata["venue_symbol"])
    interval = str(metadata.get("interval") or "native")
    filename = source_path.name.removesuffix(".zip") + ".jsonl"
    return f"features/{feature_family}/{family}/{venue_symbol}/{interval}/{filename}"


def _feature_family_for(family: str) -> str:
    if family in TRADE_FAMILIES:
        return "orderflow"
    if family == "bookTicker":
        return "bbo_spread"
    if family == "bookDepth":
        return "l2_depth"
    if family == "metrics":
        return "derivatives_context"
    if family in KLINE_CONTEXT_FAMILIES:
        return "kline_context"
    raise ValueError(f"unsupported OF-style family: {family}")


def _family_counts(source_results: Sequence[OFStyleMaterializationSourceResult]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for result in source_results:
        family_count = counts.setdefault(
            result.family,
            {"materialized_source_count": 0, "blocked_source_count": 0, "input_row_count": 0, "feature_row_count": 0},
        )
        if result.status == "materialized":
            family_count["materialized_source_count"] += 1
        else:
            family_count["blocked_source_count"] += 1
        family_count["input_row_count"] += result.input_row_count
        family_count["feature_row_count"] += result.feature_row_count
    return counts


def _materialization_scope(config: OFStyleMaterializationConfig) -> str:
    if config.max_sources_per_family is None and config.max_sources_per_symbol_per_family is None:
        return "full_selected_archive"
    if config.max_sources_per_symbol_per_family is not None:
        return "bounded_per_symbol_feature_materialization"
    return "bounded_family_feature_materialization"


def _relative_ref(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _with_row_hash(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["row_hash"] = canonical_json_hash(payload)
    return payload


def _write_jsonl_with_sha(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n")
    tmp.replace(path)
    _write_text_sha(path)


def _write_json_with_sha(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    _write_text_sha(path)


def _write_text_sha(path: Path) -> None:
    path.with_name(path.name + ".sha256").write_text(_sha256_file(path) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _timestamp_ms(value: Any) -> int | None:
    parsed = _to_int(value)
    if parsed is not None:
        return parsed
    if value is None or value == "":
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return int(datetime.strptime(text, fmt).replace(tzinfo=UTC).timestamp() * 1000)
        except ValueError:
            continue
    try:
        return int(datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC).timestamp() * 1000)
    except ValueError:
        return None


def _bucket_start_ms(timestamp_ms: int, bucket_seconds: int) -> int:
    bucket_ms = bucket_seconds * 1000
    return timestamp_ms - (timestamp_ms % bucket_ms)


def _side_from_buyer_maker(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return "sell"
    if text in {"false", "0"}:
        return "buy"
    return "unknown"


def _imbalance(left: float, right: float) -> float:
    total = left + right
    if total <= 0:
        return 0.0
    return (left - right) / total


def _round_float(value: float) -> float:
    return round(float(value), 12)


def _symbol_from_venue(venue_symbol: str) -> str:
    upper = venue_symbol.upper()
    return upper.removesuffix("USDT")


def _venue_symbol(symbol: str) -> str:
    upper = symbol.upper()
    return upper if upper.endswith("USDT") else f"{upper}USDT"


def _interval_seconds(interval: Any) -> int | None:
    if interval is None:
        return None
    text = str(interval)
    if not text:
        return None
    unit = text[-1]
    amount = _to_int(text[:-1])
    if amount is None:
        return None
    if unit == "m":
        return amount * 60
    if unit == "h":
        return amount * 60 * 60
    if unit == "d":
        return amount * 24 * 60 * 60
    return None
