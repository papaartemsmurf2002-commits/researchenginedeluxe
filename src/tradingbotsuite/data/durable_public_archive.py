from __future__ import annotations

import csv
import io
import json
import os
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.data.contracts import provider_capability_payload
from tradingbotsuite.data.historical_fixture_pack import (
    HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION,
    assert_public_archive_fixture_ready,
    assert_valid_historical_fixture_pack_manifest,
)
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research.market_data import download_binance_vision_archive

DURABLE_FIXTURE_COLLECTION_SUMMARY_VERSION = "durable-public-archive-fixture-collection-v1"
DURABLE_FIXTURE_COLLECTION_PROGRESS_VERSION = "durable-public-archive-fixture-collection-progress-v1"
DEFAULT_DURABLE_COLLECTION_START_MONTH = "2024-01"
DEFAULT_DURABLE_COLLECTION_END_MONTH = "2024-12"
DEFAULT_DURABLE_COLLECTION_SYMBOLS = ("BTCUSDT", "ETHUSDT")
SUPPORTED_DURABLE_COLLECTION_SYMBOLS = frozenset(DEFAULT_DURABLE_COLLECTION_SYMBOLS)
CANDIDATE_READY_PRIMARY_15M_MIN_BARS = 365 * 24 * 4
CANDIDATE_READY_CONTEXT_1M_MIN_ROWS = 365 * 24 * 60
CANDIDATE_READY_MIN_EFFECTIVE_HOURS = 365 * 24
MODERN_WINDOW_PROFILE_ID = "modern_window_candidate_depth_v1"
MODERN_WINDOW_START_TIME_MS = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

KLINE_HEADERLESS_FIELDS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
)
AGG_TRADE_HEADERLESS_FIELDS = (
    "aggregate_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
    "is_best_match",
)


@dataclass(frozen=True, slots=True)
class DurablePublicArchiveFixtureCollectionResult:
    output_dir: Path
    summary_path: Path
    fixture_manifest_paths: Mapping[str, Path]
    readiness_config_paths: Mapping[str, Path]
    cycle_spec_paths: Mapping[str, Path]
    discovery_spec_paths: Mapping[str, Path]
    symbol_payloads: Mapping[str, Mapping[str, Any]]

    def to_payload(self) -> dict[str, Any]:
        return {
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "output_dir": str(self.output_dir),
            "summary_path": str(self.summary_path),
            "fixture_manifest_paths": {symbol: str(path) for symbol, path in sorted(self.fixture_manifest_paths.items())},
            "readiness_config_paths": {symbol: str(path) for symbol, path in sorted(self.readiness_config_paths.items())},
            "cycle_spec_paths": {symbol: str(path) for symbol, path in sorted(self.cycle_spec_paths.items())},
            "discovery_spec_paths": {symbol: str(path) for symbol, path in sorted(self.discovery_spec_paths.items())},
            "symbols": {symbol: dict(payload) for symbol, payload in sorted(self.symbol_payloads.items())},
        }


def collect_candidate_depth_public_archive_fixtures(
    *,
    output_dir: Path,
    symbols: Sequence[str] = DEFAULT_DURABLE_COLLECTION_SYMBOLS,
    start_month: str = DEFAULT_DURABLE_COLLECTION_START_MONTH,
    end_month: str = DEFAULT_DURABLE_COLLECTION_END_MONTH,
    repo_root: Path | None = None,
    market: str = "futures/um",
    fetcher: Callable[[str], bytes] | None = None,
    download_cache_dir: Path | None = None,
    download_fallback_dirs: Sequence[Path] = (),
    fixture_fallback_dirs: Sequence[Path] = (),
    min_primary_15m_bars: int = CANDIDATE_READY_PRIMARY_15M_MIN_BARS,
    min_context_1m_rows: int = CANDIDATE_READY_CONTEXT_1M_MIN_ROWS,
    min_effective_hours: int = CANDIDATE_READY_MIN_EFFECTIVE_HOURS,
) -> DurablePublicArchiveFixtureCollectionResult:
    """Collect expanded BTC/ETH public archive fixtures for candidate-depth research.

    This path uses Binance Vision public archive ZIPs plus checksum sidecars. It
    writes research-only generated fixture packs and active specs under
    ``output_dir``; it never touches checked compact fixtures or live runtime
    configuration.
    """

    repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_symbols = _normalize_symbols(symbols)
    periods = _month_periods(start_month, end_month)
    if not periods:
        raise ValueError("durable_data_collection_month_range_empty")
    progress_path = output_dir / "collection_progress.json"
    progress_state = _initial_collection_progress(
        output_dir=output_dir,
        symbols=normalized_symbols,
        periods=periods,
        start_month=start_month,
        end_month=end_month,
        market=market,
    )
    _write_collection_progress(progress_path, progress_state)

    fixture_manifest_paths: dict[str, Path] = {}
    readiness_paths: dict[str, Path] = {}
    cycle_spec_paths: dict[str, Path] = {}
    discovery_spec_paths: dict[str, Path] = {}
    symbol_payloads: dict[str, Mapping[str, Any]] = {}

    try:
        for symbol in normalized_symbols:
            symbol_result = _collect_symbol_fixture(
                symbol=symbol,
                periods=periods,
                output_dir=output_dir,
                repo_root=repo_root,
                market=market,
                fetcher=fetcher,
                download_cache_dir=download_cache_dir,
                download_fallback_dirs=download_fallback_dirs,
                fixture_fallback_dirs=fixture_fallback_dirs,
                progress_path=progress_path,
                progress_state=progress_state,
                min_primary_15m_bars=min_primary_15m_bars,
                min_context_1m_rows=min_context_1m_rows,
                min_effective_hours=min_effective_hours,
            )
            fixture_manifest_paths[symbol] = Path(str(symbol_result["fixture_manifest_path"]))
            readiness_paths[symbol] = Path(str(symbol_result["readiness_config_path"]))
            cycle_spec_paths[symbol] = Path(str(symbol_result["cycle_spec_path"]))
            discovery_spec_paths[symbol] = Path(str(symbol_result["discovery_spec_path"]))
            symbol_payloads[symbol] = symbol_result
    except Exception as exc:
        _mark_collection_progress_failed(progress_path, progress_state, exc)
        raise

    summary = {
        "durable_fixture_collection_summary_version": DURABLE_FIXTURE_COLLECTION_SUMMARY_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_name": "binance_vision",
        "source_type": "public_archive",
        "market": market,
        "start_month": start_month,
        "end_month": end_month,
        "periods": periods,
        "symbols": symbol_payloads,
        "fixture_manifest_paths": {symbol: str(path) for symbol, path in sorted(fixture_manifest_paths.items())},
        "readiness_config_paths": {symbol: str(path) for symbol, path in sorted(readiness_paths.items())},
        "cycle_spec_paths": {symbol: str(path) for symbol, path in sorted(cycle_spec_paths.items())},
        "discovery_spec_paths": {symbol: str(path) for symbol, path in sorted(discovery_spec_paths.items())},
        "candidate_depth_thresholds": {
            "primary_15m_bars": CANDIDATE_READY_PRIMARY_15M_MIN_BARS,
            "context_1m_rows": CANDIDATE_READY_CONTEXT_1M_MIN_ROWS,
            "effective_hours": CANDIDATE_READY_MIN_EFFECTIVE_HOURS,
        },
        "collection_acceptance_thresholds": {
            "primary_15m_bars": min_primary_15m_bars,
            "context_1m_rows": min_context_1m_rows,
            "effective_hours": min_effective_hours,
        },
        "notes": [
            "Generated expanded public-archive fixture packs are research-only and observe-only.",
            "Existing compact checked fixtures are preserved as screening fixtures.",
            "Readiness still depends on manifest hashes, row counts, gap checks, and duplicate checks.",
        ],
    }
    summary_path = output_dir / "durable_fixture_collection_summary.json"
    summary_path.write_text(_canonical_json(summary, indent=2) + "\n", encoding="utf-8")
    _mark_collection_progress_complete(progress_path, progress_state, summary_path=summary_path)
    return DurablePublicArchiveFixtureCollectionResult(
        output_dir=output_dir,
        summary_path=summary_path,
        fixture_manifest_paths=fixture_manifest_paths,
        readiness_config_paths=readiness_paths,
        cycle_spec_paths=cycle_spec_paths,
        discovery_spec_paths=discovery_spec_paths,
        symbol_payloads=symbol_payloads,
    )


def _collect_symbol_fixture(
    *,
    symbol: str,
    periods: Sequence[str],
    output_dir: Path,
    repo_root: Path,
    market: str,
    fetcher: Callable[[str], bytes] | None,
    download_cache_dir: Path | None,
    download_fallback_dirs: Sequence[Path],
    fixture_fallback_dirs: Sequence[Path],
    progress_path: Path,
    progress_state: dict[str, Any],
    min_primary_15m_bars: int,
    min_context_1m_rows: int,
    min_effective_hours: int,
) -> dict[str, Any]:
    downloads_root = Path(download_cache_dir).expanduser().resolve() if download_cache_dir is not None else output_dir / "downloads"
    raw_downloads: dict[str, list[dict[str, Any]]] = {"bars": [], "lower_timeframe_bars": [], "agg_trade": []}
    selected_agg_count = 0
    agg_trade_id_order_anomaly_count = 0
    primary_state = _new_fixed_interval_state()
    lower_state = _new_fixed_interval_state()

    pack_dir = output_dir / "fixture_packs" / f"{symbol.lower()}_public_archive_candidate_depth_v1"
    pack_dir.mkdir(parents=True, exist_ok=True)
    cycle_path = pack_dir / "cycle_dataset.parquet"
    bars_path = pack_dir / "bars_15m.parquet"
    lower_path = pack_dir / "lower_timeframe_bars_1m.parquet"
    agg_path = pack_dir / "agg_trade.parquet"
    reused = _reuse_symbol_fixture_pack_if_available(
        symbol=symbol,
        periods=periods,
        pack_dir=pack_dir,
        output_dir=output_dir,
        repo_root=repo_root,
        market=market,
        fixture_fallback_dirs=fixture_fallback_dirs,
        progress_path=progress_path,
        progress_state=progress_state,
        min_primary_15m_bars=min_primary_15m_bars,
        min_context_1m_rows=min_context_1m_rows,
        min_effective_hours=min_effective_hours,
    )
    if reused is not None:
        return reused

    bars_sink = _ParquetSink(bars_path)
    lower_sink = _ParquetSink(lower_path)
    agg_sink = _ParquetSink(agg_path)

    try:
        for period in periods:
            kline_15m = _download_archive(
                symbol=symbol,
                data_family="kline",
                interval="15m",
                period=period,
                downloads_root=downloads_root,
                market=market,
                fetcher=fetcher,
                fallback_download_roots=download_fallback_dirs,
            )
            raw_downloads["bars"].append(kline_15m)
            raw_period_bars = _read_kline_archive(Path(kline_15m["archive_path"]), symbol=symbol, interval="15m")
            _observe_fixed_interval(primary_state, [row["event_time_ms"] for row in raw_period_bars], interval_ms=15 * 60 * 1000)
            period_bars = _bars_frame(raw_period_bars, interval="15m")
            period_bars["source_row_index"] = range(bars_sink.row_count, bars_sink.row_count + len(period_bars))
            bars_sink.write(period_bars)
            _advance_collection_progress(
                progress_path,
                progress_state,
                symbol=symbol,
                period=period,
                data_family="kline",
                interval="15m",
                archive_path=Path(kline_15m["archive_path"]),
            )

            kline_1m = _download_archive(
                symbol=symbol,
                data_family="kline",
                interval="1m",
                period=period,
                downloads_root=downloads_root,
                market=market,
                fetcher=fetcher,
                fallback_download_roots=download_fallback_dirs,
            )
            raw_downloads["lower_timeframe_bars"].append(kline_1m)
            raw_period_lower = _read_kline_archive(Path(kline_1m["archive_path"]), symbol=symbol, interval="1m")
            _observe_fixed_interval(lower_state, [row["event_time_ms"] for row in raw_period_lower], interval_ms=60 * 1000)
            period_lower = _lower_timeframe_frame(raw_period_lower)
            period_lower["source_row_index"] = range(lower_sink.row_count, lower_sink.row_count + len(period_lower))
            lower_sink.write(period_lower)
            _advance_collection_progress(
                progress_path,
                progress_state,
                symbol=symbol,
                period=period,
                data_family="kline",
                interval="1m",
                archive_path=Path(kline_1m["archive_path"]),
            )

            agg_trade = _download_archive(
                symbol=symbol,
                data_family="agg_trade",
                interval=None,
                period=period,
                downloads_root=downloads_root,
                market=market,
                fetcher=fetcher,
                fallback_download_roots=download_fallback_dirs,
            )
            raw_downloads["agg_trade"].append(agg_trade)
            period_agg_rows, period_selected, period_order_anomalies = _read_agg_trade_archive(Path(agg_trade["archive_path"]), symbol=symbol)
            selected_agg_count += period_selected
            agg_trade_id_order_anomaly_count += period_order_anomalies
            period_agg = _agg_trade_frame(period_agg_rows.values())
            agg_sink.write(period_agg)
            _advance_collection_progress(
                progress_path,
                progress_state,
                symbol=symbol,
                period=period,
                data_family="agg_trade",
                interval=None,
                archive_path=Path(agg_trade["archive_path"]),
            )
    finally:
        bars_sink.close()
        lower_sink.close()
        agg_sink.close()

    primary_gap = _fixed_interval_state_report(primary_state)
    lower_gap = _fixed_interval_state_report(lower_state)
    if primary_gap["gap_count"] or primary_gap["duplicate_count"]:
        raise ValueError(f"primary_bar_archive_quality_failed:{symbol}:{primary_gap}")
    if lower_gap["gap_count"] or lower_gap["duplicate_count"]:
        raise ValueError(f"lower_timeframe_archive_quality_failed:{symbol}:{lower_gap}")
    bars_frame = pd.read_parquet(bars_path)
    cycle_frame = _cycle_frame_from_bars(bars_frame, symbol=symbol)

    primary_bars = int(bars_sink.row_count)
    context_rows = int(lower_sink.row_count)
    agg_proxy_rows = int(agg_sink.row_count)
    effective_hours = round(primary_bars * 15 / 60, 2)
    collection_blockers = _candidate_depth_blockers(
        primary_bars=primary_bars,
        context_rows=context_rows,
        agg_proxy_rows=agg_proxy_rows,
        effective_hours=effective_hours,
        min_primary_15m_bars=min_primary_15m_bars,
        min_context_1m_rows=min_context_1m_rows,
        min_effective_hours=min_effective_hours,
    )
    if collection_blockers:
        raise ValueError(f"candidate_depth_floor_not_met:{symbol}:{','.join(collection_blockers)}")
    global_candidate_depth_blockers = _candidate_depth_blockers(
        primary_bars=primary_bars,
        context_rows=context_rows,
        agg_proxy_rows=agg_proxy_rows,
        effective_hours=effective_hours,
        min_primary_15m_bars=CANDIDATE_READY_PRIMARY_15M_MIN_BARS,
        min_context_1m_rows=CANDIDATE_READY_CONTEXT_1M_MIN_ROWS,
        min_effective_hours=CANDIDATE_READY_MIN_EFFECTIVE_HOURS,
    )
    global_candidate_depth_met = not global_candidate_depth_blockers

    cycle_frame.to_parquet(cycle_path, index=False)

    window_selection = _window_selection_from_frame(bars_frame)
    source_downloads = raw_downloads["bars"]
    manifest = {
        "manifest_version": HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "fixture_id": f"{symbol.lower()}-public-archive-candidate-depth-v1",
        "fixture_scope": "durable_public_archive_candidate_depth_fixture_not_oos_acceptance_evidence",
        "symbol": symbol,
        "base_interval": "15m",
        "source": {
            "source_type": "public_archive",
            "source_name": "binance_vision",
            "source_raw": "binance_vision_klines",
            "data_family": "kline",
            "event_time_field": "open_time_ms",
            "coverage_scope": "public_archive_partition",
            "latest_window_only": False,
            "checksum_status": "verified",
            "checksum_verified": True,
            "source_sha256": _hash_payload([item["archive_sha256"] for item in source_downloads]),
            "source_archive_downloads": source_downloads,
            "provider_capability": provider_capability_payload(
                source_name="binance_vision",
                data_family="kline",
                coverage_scope="public_archive_partition",
            ),
            "non_promotable_reasons": [
                "receive_time_unavailable",
                "candidate_validation_gates_not_yet_passed",
                "binance_archive_not_hyperliquid_fillability_evidence",
            ],
        },
        "derivation": {
            "derivation_type": "contiguous_public_archive_candidate_depth_collection",
            "input_source": "binance_vision_monthly_archive_partitions",
            "synthetic_source_used": False,
            "legacy_chart_source_used": False,
            "row_count": primary_bars,
            "first_time_ms": int(bars_frame["event_time_ms"].min()),
            "last_time_ms": int(bars_frame["event_time_ms"].max()),
            "context_families": ["agg_trade"],
            "context_family_count": 1,
            "periods": list(periods),
            "notes": [
                "Rows are collected from checksum-verified Binance Vision public archives.",
                "Generated pack preserves compact checked fixtures separately as screening evidence.",
                "Receive timestamps and Hyperliquid fillability evidence remain unavailable.",
            ],
        },
        "cycle_dataset": {
            "path": cycle_path.name,
            "sha256": f"sha256:{_file_sha256(cycle_path)}",
            "row_count": primary_bars,
            "time_field": "signal_bar_time_ms",
            "columns": list(cycle_frame.columns),
        },
        "families": {
            "bars": {
                "path": bars_path.name,
                "data_family": "kline",
                "interval": "15m",
                "event_time_field": "event_time_ms",
                "sha256": f"sha256:{_file_sha256(bars_path)}",
                "row_count": primary_bars,
                "required": True,
                "columns": list(bars_sink.columns or []),
                "gap_check_status": "checked_fixed_interval",
                "gap_count": int(primary_gap["gap_count"]),
                "duplicate_count": int(primary_gap["duplicate_count"]),
                "source_archive_downloads": raw_downloads["bars"],
                "source_sha256": _hash_payload([item["archive_sha256"] for item in raw_downloads["bars"]]),
            },
            "lower_timeframe_bars": {
                "path": lower_path.name,
                "data_family": "lower_timeframe_bars",
                "interval": "1m",
                "event_time_field": "bar_time_ms",
                "sha256": f"sha256:{_file_sha256(lower_path)}",
                "row_count": context_rows,
                "required": False,
                "columns": list(lower_sink.columns or []),
                "gap_check_status": "checked_fixed_interval",
                "gap_count": int(lower_gap["gap_count"]),
                "duplicate_count": int(lower_gap["duplicate_count"]),
                "source_name": "binance_vision",
                "coverage_scope": "public_archive_partition",
                "latest_window_only": False,
                "source_archive_downloads": raw_downloads["lower_timeframe_bars"],
                "source_sha256": _hash_payload([item["archive_sha256"] for item in raw_downloads["lower_timeframe_bars"]]),
            },
            "agg_trade": {
                "path": agg_path.name,
                "data_family": "agg_trade",
                "aggregation_interval": "1m",
                "event_time_field": "event_time_ms",
                "sha256": f"sha256:{_file_sha256(agg_path)}",
                "row_count": agg_proxy_rows,
                "required": False,
                "columns": list(agg_sink.columns or []),
                "gap_check_status": "not_applicable_variable_cadence",
                "duplicate_count": 0,
                "duplicate_check_status": "not_checked_full_trade_id_set_memory_bounded",
                "agg_trade_id_order_anomaly_count": int(agg_trade_id_order_anomaly_count),
                "source_name": "binance_vision",
                "source_raw": "binance_vision_aggTrades",
                "coverage_scope": "public_archive_partition",
                "latest_window_only": False,
                "context_family_role": "perp_context",
                "feature_claim_scope": "trade_flow_proxy_not_order_book_imbalance_or_ofi",
                "derivation_type": "agg_trade_archive_rows_aggregated_to_1m_trade_flow_proxy",
                "quality_note": (
                    "Aggregate trade ID order anomalies are recorded as source-order evidence only; "
                    "the fixture aggregates rows by event time into a 1m trade-flow proxy."
                ),
                "source_selected_row_count": int(selected_agg_count),
                "source_archive_downloads": raw_downloads["agg_trade"],
                "source_sha256": _hash_payload([item["archive_sha256"] for item in raw_downloads["agg_trade"]]),
                "provider_capability": provider_capability_payload(
                    source_name="binance_vision",
                    data_family="agg_trade",
                    coverage_scope="public_archive_partition",
                ),
            },
        },
        "omitted_optional_families": {
            "funding_rate": "not_included_in_candidate_depth_collection_v1",
            "liquidation": "not_included_in_candidate_depth_collection_v1",
            "open_interest": "not_included_in_candidate_depth_collection_v1",
            "premium_index": "not_included_in_candidate_depth_collection_v1",
        },
        "research_evidence_limitations": [
            "not_oos_acceptance_by_itself",
            "not_sufficient_for_performance_claims_without_gates",
            "not_hyperliquid_fillability_evidence",
            "not_promotion_ready",
        ],
        "window_selection": window_selection,
    }
    manifest_path = pack_dir / "fixture_pack_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    assert_public_archive_fixture_ready(manifest, manifest_path=manifest_path)

    readiness_path = _write_active_readiness(
        symbol=symbol,
        output_dir=output_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        primary_bars=primary_bars,
        context_rows=context_rows,
        agg_proxy_rows=agg_proxy_rows,
        effective_hours=effective_hours,
        global_candidate_depth_met=global_candidate_depth_met,
        global_candidate_depth_blockers=global_candidate_depth_blockers,
        min_primary_15m_bars=min_primary_15m_bars,
        min_context_1m_rows=min_context_1m_rows,
        min_effective_hours=min_effective_hours,
    )
    cycle_spec_path = _write_active_cycle_spec(symbol=symbol, repo_root=repo_root, output_dir=output_dir, manifest_path=manifest_path, readiness_path=readiness_path)
    discovery_spec_path = _write_active_discovery_spec(symbol=symbol, repo_root=repo_root, output_dir=output_dir, manifest_path=manifest_path)
    modern_window_profiles = _write_modern_window_profiles(
        symbol=symbol,
        repo_root=repo_root,
        output_dir=output_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        readiness_path=readiness_path,
    )
    _patch_active_readiness_paths(
        readiness_path,
        cycle_spec_path=cycle_spec_path,
        discovery_spec_path=discovery_spec_path,
        modern_window_profiles=modern_window_profiles,
    )

    return {
        "symbol": symbol,
        "status": "candidate_depth_fixture_ready" if global_candidate_depth_met else "fixture_ready_below_candidate_depth_floor",
        "fixture_manifest_path": str(manifest_path),
        "fixture_manifest_sha256": f"sha256:{_file_sha256(manifest_path)}",
        "readiness_config_path": str(readiness_path),
        "cycle_spec_path": str(cycle_spec_path),
        "discovery_spec_path": str(discovery_spec_path),
        "cycle_id": _read_json(cycle_spec_path).get("cycle_id"),
        "discovery_run_id": _read_json(discovery_spec_path).get("run_id"),
        "modern_window_profile_count": len(modern_window_profiles),
        "modern_window_profiles": modern_window_profiles,
        "row_counts": {
            "bars": primary_bars,
            "lower_timeframe_bars": context_rows,
            "agg_trade": agg_proxy_rows,
        },
        "source_selected_agg_trade_rows": int(selected_agg_count),
        "download_count": sum(len(items) for items in raw_downloads.values()),
        "checksum_verified_count": sum(1 for items in raw_downloads.values() for item in items if item.get("checksum_verified") is True),
        "candidate_depth_thresholds_met": global_candidate_depth_met,
        "candidate_depth_blockers": global_candidate_depth_blockers,
        "collection_thresholds_met": True,
        "effective_coverage_hours": effective_hours,
        "promotion_ready": False,
        "research_only": True,
        "observe_only": True,
    }


def _reuse_symbol_fixture_pack_if_available(
    *,
    symbol: str,
    periods: Sequence[str],
    pack_dir: Path,
    output_dir: Path,
    repo_root: Path,
    market: str,
    fixture_fallback_dirs: Sequence[Path],
    progress_path: Path,
    progress_state: dict[str, Any],
    min_primary_15m_bars: int,
    min_context_1m_rows: int,
    min_effective_hours: int,
) -> dict[str, Any] | None:
    for source_pack_dir in _symbol_fixture_pack_fallback_candidates(symbol=symbol, fixture_fallback_dirs=fixture_fallback_dirs):
        if source_pack_dir.resolve() == pack_dir.resolve():
            continue
        source_manifest_path = source_pack_dir / "fixture_pack_manifest.json"
        manifest = _read_reusable_symbol_fixture_manifest(
            source_manifest_path,
            symbol=symbol,
            periods=periods,
            market=market,
        )
        if manifest is None:
            continue
        _copy_reusable_fixture_pack(source_pack_dir=source_pack_dir, target_pack_dir=pack_dir, manifest=manifest)
        manifest_path = pack_dir / "fixture_pack_manifest.json"
        copied_manifest = _read_json(manifest_path)
        assert_valid_historical_fixture_pack_manifest(copied_manifest, manifest_path=manifest_path)
        assert_public_archive_fixture_ready(copied_manifest, manifest_path=manifest_path)
        return _symbol_payload_from_reused_fixture(
            symbol=symbol,
            output_dir=output_dir,
            repo_root=repo_root,
            manifest_path=manifest_path,
            manifest=copied_manifest,
            source_pack_dir=source_pack_dir,
            progress_path=progress_path,
            progress_state=progress_state,
            periods=periods,
            min_primary_15m_bars=min_primary_15m_bars,
            min_context_1m_rows=min_context_1m_rows,
            min_effective_hours=min_effective_hours,
        )
    return None


def _symbol_fixture_pack_fallback_candidates(*, symbol: str, fixture_fallback_dirs: Sequence[Path]) -> list[Path]:
    pack_name = f"{symbol.lower()}_public_archive_candidate_depth_v1"
    candidates: list[Path] = []
    seen: set[Path] = set()
    for raw_root in fixture_fallback_dirs:
        root = Path(raw_root).expanduser().resolve()
        for candidate in (root / pack_name, root / "fixture_packs" / pack_name):
            resolved = candidate.resolve()
            if resolved in seen or not (resolved / "fixture_pack_manifest.json").is_file():
                continue
            seen.add(resolved)
            candidates.append(resolved)
    return candidates


def _read_reusable_symbol_fixture_manifest(
    manifest_path: Path,
    *,
    symbol: str,
    periods: Sequence[str],
    market: str,
) -> dict[str, Any] | None:
    if not manifest_path.is_file():
        return None
    try:
        manifest = _read_json(manifest_path)
        assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
        assert_public_archive_fixture_ready(manifest, manifest_path=manifest_path)
    except Exception:
        return None
    if str(manifest.get("symbol") or "").upper() != symbol:
        return None
    if list((manifest.get("derivation") or {}).get("periods") or []) != list(periods):
        return None
    downloads = list(((manifest.get("source") or {}).get("source_archive_downloads")) or [])
    expected_market_fragment = f"/data/{market.strip().strip('/')}/"
    if downloads and not any(expected_market_fragment in str(item.get("url") or "") for item in downloads if isinstance(item, Mapping)):
        return None
    for relative_path in _fixture_pack_payload_paths(manifest):
        candidate = manifest_path.parent / relative_path
        if not candidate.is_file():
            return None
        expected = _manifest_sha_for_relative_path(manifest, relative_path)
        if expected is not None and expected != f"sha256:{_file_sha256(candidate)}":
            return None
    return manifest


def _fixture_pack_payload_paths(manifest: Mapping[str, Any]) -> list[str]:
    paths: list[str] = []
    cycle_dataset = manifest.get("cycle_dataset") if isinstance(manifest.get("cycle_dataset"), Mapping) else {}
    if cycle_dataset.get("path"):
        paths.append(str(cycle_dataset["path"]))
    families = manifest.get("families") if isinstance(manifest.get("families"), Mapping) else {}
    for entry in families.values():
        if isinstance(entry, Mapping) and entry.get("path"):
            paths.append(str(entry["path"]))
    return sorted(set(paths))


def _manifest_sha_for_relative_path(manifest: Mapping[str, Any], relative_path: str) -> str | None:
    cycle_dataset = manifest.get("cycle_dataset") if isinstance(manifest.get("cycle_dataset"), Mapping) else {}
    if cycle_dataset.get("path") == relative_path:
        return str(cycle_dataset.get("sha256")) if cycle_dataset.get("sha256") else None
    families = manifest.get("families") if isinstance(manifest.get("families"), Mapping) else {}
    for entry in families.values():
        if isinstance(entry, Mapping) and entry.get("path") == relative_path:
            return str(entry.get("sha256")) if entry.get("sha256") else None
    return None


def _copy_reusable_fixture_pack(*, source_pack_dir: Path, target_pack_dir: Path, manifest: Mapping[str, Any]) -> None:
    target_pack_dir.mkdir(parents=True, exist_ok=True)
    for relative_path in [*_fixture_pack_payload_paths(manifest), "fixture_pack_manifest.json"]:
        source = source_pack_dir / relative_path
        target = target_pack_dir / relative_path
        if source.resolve() == target.resolve() or target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)


def _symbol_payload_from_reused_fixture(
    *,
    symbol: str,
    output_dir: Path,
    repo_root: Path,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    source_pack_dir: Path,
    progress_path: Path,
    progress_state: dict[str, Any],
    periods: Sequence[str],
    min_primary_15m_bars: int,
    min_context_1m_rows: int,
    min_effective_hours: int,
) -> dict[str, Any]:
    families = manifest["families"]
    primary_bars = int(families["bars"]["row_count"])
    context_rows = int(families["lower_timeframe_bars"]["row_count"])
    agg_proxy_rows = int(families["agg_trade"]["row_count"])
    selected_agg_count = int(families["agg_trade"].get("source_selected_row_count") or 0)
    effective_hours = round(primary_bars * 15 / 60, 2)
    collection_blockers = _candidate_depth_blockers(
        primary_bars=primary_bars,
        context_rows=context_rows,
        agg_proxy_rows=agg_proxy_rows,
        effective_hours=effective_hours,
        min_primary_15m_bars=min_primary_15m_bars,
        min_context_1m_rows=min_context_1m_rows,
        min_effective_hours=min_effective_hours,
    )
    if collection_blockers:
        raise ValueError(f"candidate_depth_floor_not_met:{symbol}:{','.join(collection_blockers)}")
    global_candidate_depth_blockers = _candidate_depth_blockers(
        primary_bars=primary_bars,
        context_rows=context_rows,
        agg_proxy_rows=agg_proxy_rows,
        effective_hours=effective_hours,
        min_primary_15m_bars=CANDIDATE_READY_PRIMARY_15M_MIN_BARS,
        min_context_1m_rows=CANDIDATE_READY_CONTEXT_1M_MIN_ROWS,
        min_effective_hours=CANDIDATE_READY_MIN_EFFECTIVE_HOURS,
    )
    global_candidate_depth_met = not global_candidate_depth_blockers
    readiness_path = _write_active_readiness(
        symbol=symbol,
        output_dir=output_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        primary_bars=primary_bars,
        context_rows=context_rows,
        agg_proxy_rows=agg_proxy_rows,
        effective_hours=effective_hours,
        global_candidate_depth_met=global_candidate_depth_met,
        global_candidate_depth_blockers=global_candidate_depth_blockers,
        min_primary_15m_bars=min_primary_15m_bars,
        min_context_1m_rows=min_context_1m_rows,
        min_effective_hours=min_effective_hours,
    )
    cycle_spec_path = _write_active_cycle_spec(symbol=symbol, repo_root=repo_root, output_dir=output_dir, manifest_path=manifest_path, readiness_path=readiness_path)
    discovery_spec_path = _write_active_discovery_spec(symbol=symbol, repo_root=repo_root, output_dir=output_dir, manifest_path=manifest_path)
    modern_window_profiles = _write_modern_window_profiles(
        symbol=symbol,
        repo_root=repo_root,
        output_dir=output_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        readiness_path=readiness_path,
    )
    _patch_active_readiness_paths(
        readiness_path,
        cycle_spec_path=cycle_spec_path,
        discovery_spec_path=discovery_spec_path,
        modern_window_profiles=modern_window_profiles,
    )
    _advance_collection_progress_reused_symbol(
        progress_path,
        progress_state,
        symbol=symbol,
        periods=periods,
        manifest_path=manifest_path,
        source_pack_dir=source_pack_dir,
    )
    source_downloads = [
        *list(families["bars"].get("source_archive_downloads") or []),
        *list(families["lower_timeframe_bars"].get("source_archive_downloads") or []),
        *list(families["agg_trade"].get("source_archive_downloads") or []),
    ]
    return {
        "symbol": symbol,
        "status": "candidate_depth_fixture_ready" if global_candidate_depth_met else "fixture_ready_below_candidate_depth_floor",
        "fixture_manifest_path": str(manifest_path),
        "fixture_manifest_sha256": f"sha256:{_file_sha256(manifest_path)}",
        "readiness_config_path": str(readiness_path),
        "cycle_spec_path": str(cycle_spec_path),
        "discovery_spec_path": str(discovery_spec_path),
        "cycle_id": _read_json(cycle_spec_path).get("cycle_id"),
        "discovery_run_id": _read_json(discovery_spec_path).get("run_id"),
        "modern_window_profile_count": len(modern_window_profiles),
        "modern_window_profiles": modern_window_profiles,
        "row_counts": {
            "bars": primary_bars,
            "lower_timeframe_bars": context_rows,
            "agg_trade": agg_proxy_rows,
        },
        "source_selected_agg_trade_rows": selected_agg_count,
        "download_count": len(source_downloads),
        "checksum_verified_count": sum(1 for item in source_downloads if isinstance(item, Mapping) and item.get("checksum_verified") is True),
        "candidate_depth_thresholds_met": global_candidate_depth_met,
        "candidate_depth_blockers": global_candidate_depth_blockers,
        "collection_thresholds_met": True,
        "effective_coverage_hours": effective_hours,
        "reused_fixture_pack": True,
        "reused_fixture_pack_source": str(source_pack_dir),
        "promotion_ready": False,
        "research_only": True,
        "observe_only": True,
    }


def _candidate_depth_blockers(
    *,
    primary_bars: int,
    context_rows: int,
    agg_proxy_rows: int,
    effective_hours: float,
    min_primary_15m_bars: int,
    min_context_1m_rows: int,
    min_effective_hours: int,
) -> list[str]:
    blockers: list[str] = []
    if primary_bars < min_primary_15m_bars:
        blockers.append(f"primary_15m_bars_below_candidate_floor:{primary_bars}<{min_primary_15m_bars}")
    if context_rows < min_context_1m_rows:
        blockers.append(f"lower_timeframe_1m_rows_below_candidate_floor:{context_rows}<{min_context_1m_rows}")
    if agg_proxy_rows < min_context_1m_rows:
        blockers.append(f"agg_trade_1m_rows_below_candidate_floor:{agg_proxy_rows}<{min_context_1m_rows}")
    if effective_hours < min_effective_hours:
        blockers.append(f"effective_coverage_hours_below_candidate_floor:{effective_hours}<{min_effective_hours}")
    return blockers


def _initial_collection_progress(
    *,
    output_dir: Path,
    symbols: Sequence[str],
    periods: Sequence[str],
    start_month: str,
    end_month: str,
    market: str,
) -> dict[str, Any]:
    now = _utc_now_iso()
    return {
        "_started_monotonic": time.monotonic(),
        "progress_version": DURABLE_FIXTURE_COLLECTION_PROGRESS_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "status": "running",
        "source_name": "binance_vision",
        "market": market,
        "output_dir": str(output_dir),
        "started_at": now,
        "updated_at": now,
        "start_month": start_month,
        "end_month": end_month,
        "symbols": list(symbols),
        "periods": list(periods),
        "total_archive_steps": len(symbols) * len(periods) * 3,
        "completed_archive_steps": 0,
        "percent_complete": 0.0,
        "elapsed_seconds": 0.0,
        "archive_steps_per_minute": 0.0,
        "eta_seconds": None,
        "current": None,
        "recent_completed_archives": [],
    }


def _advance_collection_progress(
    progress_path: Path,
    state: dict[str, Any],
    *,
    symbol: str,
    period: str,
    data_family: str,
    interval: str | None,
    archive_path: Path,
) -> None:
    completed = int(state.get("completed_archive_steps") or 0) + 1
    total = max(1, int(state.get("total_archive_steps") or 1))
    elapsed = max(0.0, time.monotonic() - float(state.get("_started_monotonic") or time.monotonic()))
    rate_per_second = completed / elapsed if elapsed > 0 else 0.0
    remaining = max(0, total - completed)
    eta_seconds = round(remaining / rate_per_second, 2) if rate_per_second > 0 and remaining else 0.0
    completed_item = {
        "symbol": symbol,
        "period": period,
        "data_family": data_family,
        "interval": interval,
        "archive_path": str(archive_path),
        "completed_at": _utc_now_iso(),
    }
    recent = [*list(state.get("recent_completed_archives") or []), completed_item][-20:]
    state.update(
        {
            "status": "running",
            "updated_at": completed_item["completed_at"],
            "completed_archive_steps": completed,
            "percent_complete": round(completed * 100.0 / total, 2),
            "elapsed_seconds": round(elapsed, 2),
            "archive_steps_per_minute": round(rate_per_second * 60.0, 4),
            "eta_seconds": eta_seconds,
            "current": completed_item,
            "recent_completed_archives": recent,
        }
    )
    _write_collection_progress(progress_path, state)


def _advance_collection_progress_reused_symbol(
    progress_path: Path,
    state: dict[str, Any],
    *,
    symbol: str,
    periods: Sequence[str],
    manifest_path: Path,
    source_pack_dir: Path,
) -> None:
    step_count = len(periods) * 3
    completed = int(state.get("completed_archive_steps") or 0) + step_count
    total = max(1, int(state.get("total_archive_steps") or 1))
    elapsed = max(0.0, time.monotonic() - float(state.get("_started_monotonic") or time.monotonic()))
    rate_per_second = completed / elapsed if elapsed > 0 else 0.0
    remaining = max(0, total - completed)
    eta_seconds = round(remaining / rate_per_second, 2) if rate_per_second > 0 and remaining else 0.0
    completed_item = {
        "symbol": symbol,
        "period": f"{periods[0]}..{periods[-1]}" if periods else None,
        "data_family": "fixture_pack",
        "interval": None,
        "archive_path": str(manifest_path),
        "reused_fixture_pack": True,
        "reused_fixture_pack_source": str(source_pack_dir),
        "reused_archive_steps": step_count,
        "completed_at": _utc_now_iso(),
    }
    recent = [*list(state.get("recent_completed_archives") or []), completed_item][-20:]
    state.update(
        {
            "status": "running",
            "updated_at": completed_item["completed_at"],
            "completed_archive_steps": completed,
            "percent_complete": round(completed * 100.0 / total, 2),
            "elapsed_seconds": round(elapsed, 2),
            "archive_steps_per_minute": round(rate_per_second * 60.0, 4),
            "eta_seconds": eta_seconds,
            "current": completed_item,
            "recent_completed_archives": recent,
        }
    )
    _write_collection_progress(progress_path, state)


def _mark_collection_progress_failed(progress_path: Path, state: dict[str, Any], exc: Exception) -> None:
    state.update(
        {
            "status": "failed",
            "updated_at": _utc_now_iso(),
            "error": str(exc),
            "elapsed_seconds": round(max(0.0, time.monotonic() - float(state.get("_started_monotonic") or time.monotonic())), 2),
        }
    )
    _write_collection_progress(progress_path, state)


def _mark_collection_progress_complete(progress_path: Path, state: dict[str, Any], *, summary_path: Path) -> None:
    total = int(state.get("total_archive_steps") or 0)
    state.update(
        {
            "status": "complete",
            "updated_at": _utc_now_iso(),
            "completed_archive_steps": total,
            "percent_complete": 100.0,
            "eta_seconds": 0.0,
            "summary_path": str(summary_path),
            "elapsed_seconds": round(max(0.0, time.monotonic() - float(state.get("_started_monotonic") or time.monotonic())), 2),
        }
    )
    _write_collection_progress(progress_path, state)


def _write_collection_progress(progress_path: Path, state: Mapping[str, Any]) -> None:
    payload = {key: value for key, value in state.items() if not str(key).startswith("_")}
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _download_archive(
    *,
    symbol: str,
    data_family: str,
    interval: str | None,
    period: str,
    downloads_root: Path,
    market: str,
    fetcher: Callable[[str], bytes] | None,
    fallback_download_roots: Sequence[Path] = (),
) -> dict[str, Any]:
    result = download_binance_vision_archive(
        symbol=symbol,
        data_family=data_family,
        interval=interval,
        period=period,
        output_dir=downloads_root,
        cadence="monthly",
        market=market,
        verify_checksum=True,
        fetcher=fetcher,
        reuse_existing=True,
        fallback_output_dirs=fallback_download_roots,
    )
    return {
        "url": result.url,
        "checksum_url": result.checksum_url,
        "archive_path": str(result.output_path),
        "checksum_path": str(result.checksum_path) if result.checksum_path is not None else None,
        "archive_sha256": result.sha256,
        "checksum_sha256": f"sha256:{_file_sha256(result.checksum_path)}" if result.checksum_path is not None else None,
        "checksum_verified": bool(result.verified),
        "archive_member": _zip_csv_member(result.output_path),
        "data_family": data_family,
        "interval": interval,
        "period": period,
    }


def _read_kline_archive(path: Path, *, symbol: str, interval: str) -> list[dict[str, Any]]:
    rows = []
    for source_row_index, raw in enumerate(_zip_csv_dict_rows(path, KLINE_HEADERLESS_FIELDS)):
        time_ms = _required_int(raw, "open_time", "open_time_ms")
        rows.append(
            {
                "event_time_ms": time_ms,
                "symbol": symbol,
                "interval": interval,
                "open_price": float(_required_text(raw, "open")),
                "high_price": float(_required_text(raw, "high")),
                "low_price": float(_required_text(raw, "low")),
                "close_price": float(_required_text(raw, "close")),
                "volume": float(_required_text(raw, "volume")),
                "source_row_index": source_row_index,
            }
        )
    return rows


def _read_agg_trade_archive(path: Path, *, symbol: str) -> tuple[dict[int, dict[str, Any]], int, int]:
    buckets: dict[int, dict[str, Any]] = {}
    order_anomaly_count = 0
    selected = 0
    last_trade_id: int | None = None
    for source_row_index, raw in enumerate(_zip_csv_dict_rows(path, AGG_TRADE_HEADERLESS_FIELDS)):
        event_time_ms = _required_int(raw, "transact_time", "transact_time_ms", "time")
        minute_ms = (event_time_ms // 60_000) * 60_000
        price = float(_required_text(raw, "price"))
        quantity = float(_required_text(raw, "quantity", "qty"))
        quote_volume = price * quantity
        trade_id = _optional_int(raw, "aggregate_trade_id", "agg_trade_id", "a")
        if trade_id is not None:
            if last_trade_id is not None and trade_id <= last_trade_id:
                order_anomaly_count += 1
            last_trade_id = trade_id
        is_buyer_maker = _optional_bool(raw, "is_buyer_maker", "m")
        bucket = buckets.setdefault(minute_ms, _new_agg_bucket(symbol=symbol, event_time_ms=minute_ms))
        bucket["agg_trade_count"] += 1
        bucket["quantity"] += quantity
        bucket["quote_volume"] += quote_volume
        if is_buyer_maker is False:
            bucket["taker_buy_quote_volume"] += quote_volume
        elif is_buyer_maker is True:
            bucket["sell_quote_volume"] += quote_volume
        bucket["source_row_index"] = min(int(bucket["source_row_index"]), source_row_index)
        selected += 1
    return buckets, selected, order_anomaly_count


def _new_agg_bucket(*, symbol: str, event_time_ms: int) -> dict[str, Any]:
    return {
        "event_time_ms": int(event_time_ms),
        "symbol": symbol,
        "agg_trade_count": 0,
        "quantity": 0.0,
        "quote_volume": 0.0,
        "taker_buy_quote_volume": 0.0,
        "sell_quote_volume": 0.0,
        "source_row_index": 2**63 - 1,
        "source_provider": "binance_vision",
        "source_data_family": "agg_trade",
    }


@dataclass(slots=True)
class _ParquetSink:
    path: Path
    writer: pq.ParquetWriter | None = None
    row_count: int = 0
    columns: list[str] | None = None

    def write(self, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if self.writer is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.writer = pq.ParquetWriter(self.path, table.schema, compression="snappy")
            self.columns = list(frame.columns)
        self.writer.write_table(table)
        self.row_count += int(len(frame))

    def close(self) -> None:
        if self.writer is not None:
            self.writer.close()
            self.writer = None


def _new_fixed_interval_state() -> dict[str, Any]:
    return {
        "count": 0,
        "first_event_time_ms": None,
        "last_event_time_ms": None,
        "gap_count": 0,
        "duplicate_count": 0,
        "gaps": [],
        "duplicates": [],
    }


def _observe_fixed_interval(state: dict[str, Any], values: Sequence[Any], *, interval_ms: int) -> None:
    for raw_value in values:
        value = int(raw_value)
        previous = state.get("last_event_time_ms")
        if previous is None:
            state["first_event_time_ms"] = value
        else:
            delta = value - int(previous)
            if delta == 0:
                state["duplicate_count"] = int(state["duplicate_count"]) + 1
                if len(state["duplicates"]) < 100:
                    state["duplicates"].append(value)
            elif delta != interval_ms:
                state["gap_count"] = int(state["gap_count"]) + 1
                if len(state["gaps"]) < 100:
                    state["gaps"].append(
                        {
                            "previous_event_time_ms": int(previous),
                            "next_event_time_ms": value,
                            "delta_ms": delta,
                            "missing_event_count": max(0, int(delta // interval_ms) - 1),
                        }
                    )
        state["last_event_time_ms"] = value
        state["count"] = int(state["count"]) + 1


def _fixed_interval_state_report(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "gap_count": int(state.get("gap_count") or 0),
        "duplicate_count": int(state.get("duplicate_count") or 0),
        "gaps": list(state.get("gaps") or []),
        "duplicates": list(state.get("duplicates") or []),
    }


def _bars_frame(rows: Sequence[Mapping[str, Any]], *, interval: str) -> pd.DataFrame:
    frame = pd.DataFrame(rows).drop_duplicates(["symbol", "event_time_ms"], keep="last")
    if frame.empty:
        raise ValueError("no_kline_rows_collected")
    frame = frame.sort_values(["symbol", "event_time_ms"], kind="mergesort").reset_index(drop=True)
    frame["source_row_index"] = range(len(frame))
    return frame.loc[
        :,
        [
            "event_time_ms",
            "symbol",
            "interval",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "source_row_index",
        ],
    ]


def _lower_timeframe_frame(rows: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    bars = _bars_frame(rows, interval="1m")
    return pd.DataFrame(
        {
            "bar_time_ms": bars["event_time_ms"].astype("int64"),
            "symbol": bars["symbol"].astype(str),
            "open": bars["open_price"].astype("float64"),
            "high": bars["high_price"].astype("float64"),
            "low": bars["low_price"].astype("float64"),
            "close": bars["close_price"].astype("float64"),
            "volume": bars["volume"].astype("float64"),
            "interval": "1m",
            "source_row_index": bars["source_row_index"].astype("int64"),
            "source_provider": "binance_vision",
            "source_data_family": "kline",
        }
    )


def _agg_trade_frame(rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("no_agg_trade_rows_collected")
    frame = frame.sort_values(["symbol", "event_time_ms"], kind="mergesort").reset_index(drop=True)
    quote = pd.to_numeric(frame["quote_volume"], errors="coerce").fillna(0.0)
    taker_buy = pd.to_numeric(frame["taker_buy_quote_volume"], errors="coerce").fillna(0.0)
    sell = pd.to_numeric(frame["sell_quote_volume"], errors="coerce").fillna(0.0)
    denominator = quote.replace(0.0, pd.NA)
    frame["price"] = quote / pd.to_numeric(frame["quantity"], errors="coerce").replace(0.0, pd.NA)
    frame["primary_signed_imbalance_ratio"] = ((taker_buy - sell) / denominator).fillna(0.0)
    signed = pd.to_numeric(frame["primary_signed_imbalance_ratio"], errors="coerce")
    frame["primary_sqrt_signed_imbalance_ratio"] = signed.apply(
        lambda value: 0.0 if pd.isna(value) else (1.0 if value >= 0.0 else -1.0) * (abs(float(value)) ** 0.5)
    )
    return frame.loc[
        :,
        [
            "event_time_ms",
            "symbol",
            "agg_trade_count",
            "quantity",
            "quote_volume",
            "taker_buy_quote_volume",
            "sell_quote_volume",
            "price",
            "primary_signed_imbalance_ratio",
            "primary_sqrt_signed_imbalance_ratio",
            "source_row_index",
            "source_provider",
            "source_data_family",
        ],
    ]


def _cycle_frame_from_bars(bars: pd.DataFrame, *, symbol: str) -> pd.DataFrame:
    result = pd.DataFrame(
        {
            "symbol": symbol,
            "time_ms": bars["event_time_ms"].astype("int64"),
            "bar_time_ms": bars["event_time_ms"].astype("int64"),
            "signal_bar_time_ms": bars["event_time_ms"].astype("int64"),
            "open": bars["open_price"].astype("float64"),
            "high": bars["high_price"].astype("float64"),
            "low": bars["low_price"].astype("float64"),
            "close": bars["close_price"].astype("float64"),
            "volume": bars["volume"].astype("float64"),
            "source_row_index": bars["source_row_index"].astype("int64"),
            "source_provider": "binance_vision",
            "source_provider_raw": "binance_vision_klines",
            "source_data_family": "kline",
            "source_interval": "15m",
            "fixture_derivation": "contiguous_public_archive_candidate_depth_collection",
        }
    )
    for column in ("open", "high", "low", "close", "volume"):
        result[f"signal_bar_{column}"] = result[column]
    result["entry_price"] = result["close"]
    returns = result["close"].pct_change().fillna(0.0)
    rolling_vol = returns.rolling(16, min_periods=4).std().fillna(0.0)
    rolling_mean = result["close"].rolling(96, min_periods=16).mean()
    rolling_std = result["close"].rolling(96, min_periods=16).std().replace(0.0, pd.NA)
    zscore = ((result["close"] - rolling_mean) / rolling_std).fillna(0.0)
    trend = result["close"].diff(96).fillna(0.0)
    median_close = float(result["close"].median())
    result["validation_regime"] = [
        "shock" if abs(float(z)) >= 2.0 else "trend" if abs(float(t)) >= median_close * 0.01 else "range"
        for z, t in zip(zscore, trend)
    ]
    result["top_regime_label"] = result["validation_regime"]
    result["regime"] = result["validation_regime"]
    result["provider_cache_realized_volatility"] = rolling_vol.astype("float64")
    return result.loc[
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


def _write_active_readiness(
    *,
    symbol: str,
    output_dir: Path,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    primary_bars: int,
    context_rows: int,
    agg_proxy_rows: int,
    effective_hours: float,
    global_candidate_depth_met: bool,
    global_candidate_depth_blockers: Sequence[str],
    min_primary_15m_bars: int,
    min_context_1m_rows: int,
    min_effective_hours: int,
) -> Path:
    path = output_dir / "active_readiness" / f"durable_public_archive_fixture_readiness_{symbol.lower()}_candidate_depth_v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    required_context = manifest["families"]["agg_trade"]
    window_selection = (manifest.get("window_selection") or {}).get("regime_windows") or {}
    payload = {
        "readiness_config_version": "durable-public-archive-fixture-readiness-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "symbol": symbol,
        "base_interval": "15m",
        "fixture_manifest_path": str(manifest_path),
        "fixture_manifest_sha256": f"sha256:{_file_sha256(manifest_path)}",
        "readiness_status": "durable_public_archive_ready",
        "generated_candidate_depth_fixture": bool(global_candidate_depth_met),
        "required_families": ["bars", "lower_timeframe_bars", "agg_trade"],
        "required_primary_source": "binance_vision",
        "required_context": {
            "agg_trade": {
                "source_name": "binance_vision",
                "feature_claim_scope": required_context.get("feature_claim_scope"),
                "aggregation_interval": "1m",
                "source_selected_row_count": required_context.get("source_selected_row_count"),
                "agg_trade_id_order_anomaly_count": required_context.get("agg_trade_id_order_anomaly_count"),
                "fixture_row_count": agg_proxy_rows,
            }
        },
        "fixture_row_counts": {
            "bars": primary_bars,
            "lower_timeframe_bars": context_rows,
            "agg_trade": agg_proxy_rows,
        },
        "candidate_depth_evidence": {
            "primary_interval": "15m",
            "primary_bars": primary_bars,
            "lower_timeframe_1m_rows": context_rows,
            "agg_trade_1m_rows": agg_proxy_rows,
            "effective_coverage_hours": effective_hours,
            "required_primary_15m_bars": CANDIDATE_READY_PRIMARY_15M_MIN_BARS,
            "required_context_1m_rows": CANDIDATE_READY_CONTEXT_1M_MIN_ROWS,
            "required_effective_hours": CANDIDATE_READY_MIN_EFFECTIVE_HOURS,
            "candidate_depth_thresholds_met": bool(global_candidate_depth_met),
            "candidate_depth_blockers": list(global_candidate_depth_blockers),
            "collection_acceptance_thresholds": {
                "primary_15m_bars": min_primary_15m_bars,
                "context_1m_rows": min_context_1m_rows,
                "effective_hours": min_effective_hours,
            },
        },
        "window_selection_required": ["trend_bull", "drawdown_bear", "range_chop", "high_vol_shock"],
        "window_selection_recorded": {
            label: _iso_window(window)
            for label, window in sorted(window_selection.items())
            if isinstance(window, Mapping)
        },
        "diagnostic_only_sources": ["binance_usdm_rest_latest_window_context", "crypto_lake_free_sample"],
        "claim_scope": "validated_durable_public_archive_candidate_depth_no_candidate_pack_write",
    }
    path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _write_active_cycle_spec(
    *,
    symbol: str,
    repo_root: Path,
    output_dir: Path,
    manifest_path: Path,
    readiness_path: Path,
) -> Path:
    lower = symbol.lower()
    base_name = f"full_cycle_{lower}_durable_public_archive_r104_deep_v1.json"
    base_path = repo_root / "configs" / "research" / base_name
    payload = _read_json(base_path)
    payload["cycle_id"] = f"r105-{lower}-durable-public-archive-candidate-depth-v1"
    payload["work_packet"] = "WPR105-106-durable-data-acquisition-step0"
    payload["maturity_label"] = "durable_candidate_depth_screening"
    payload["output_dir"] = str(output_dir / "historical_cycles" / payload["cycle_id"])
    data = payload.setdefault("data", {})
    data["dataset_manifest_paths"] = [str(manifest_path)]
    data["evidence_scope"] = "durable_public_archive_candidate_depth_screening"
    data["durable_fixture_readiness_config_path"] = str(readiness_path)
    active_dir = output_dir / "active_specs"
    active_dir.mkdir(parents=True, exist_ok=True)
    path = active_dir / f"{payload['cycle_id']}.json"
    path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _write_active_discovery_spec(
    *,
    symbol: str,
    repo_root: Path,
    output_dir: Path,
    manifest_path: Path,
) -> Path:
    lower = symbol.lower()
    base_name = f"exact_entry_sweep_{lower}_durable_r104_v1.json"
    base_path = repo_root / "configs" / "discovery" / base_name
    payload = _read_json(base_path)
    payload["run_id"] = f"exact_entry_sweep_{lower}_candidate_depth_v1"
    payload["research_output_dir"] = str(output_dir)
    payload.setdefault("data", {})["dataset_manifest_paths"] = [str(manifest_path)]
    payload.setdefault("metadata", {})["work_packet"] = "WPR105-106-durable-data-acquisition-step0"
    active_dir = output_dir / "active_specs"
    active_dir.mkdir(parents=True, exist_ok=True)
    path = active_dir / f"{payload['run_id']}.json"
    path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _patch_active_readiness_paths(
    readiness_path: Path,
    *,
    cycle_spec_path: Path,
    discovery_spec_path: Path,
    modern_window_profiles: Mapping[str, Mapping[str, Any]] | None = None,
) -> None:
    payload = _read_json(readiness_path)
    payload["cycle_spec_path"] = str(cycle_spec_path)
    payload["discovery_spec_path"] = str(discovery_spec_path)
    payload["cycle_id"] = _read_json(cycle_spec_path).get("cycle_id")
    payload["discovery_run_id"] = _read_json(discovery_spec_path).get("run_id")
    if modern_window_profiles is not None:
        payload["modern_window_profile_count"] = len(modern_window_profiles)
        payload["modern_window_profiles"] = {
            profile_id: dict(profile)
            for profile_id, profile in sorted(modern_window_profiles.items())
        }
    readiness_path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")


def _write_modern_window_profiles(
    *,
    symbol: str,
    repo_root: Path,
    output_dir: Path,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    readiness_path: Path,
) -> dict[str, dict[str, Any]]:
    profile_id = MODERN_WINDOW_PROFILE_ID
    lower = symbol.lower()
    profile_dir = output_dir / "modern_window_profiles" / f"{lower}_{profile_id}"
    profile_dir.mkdir(parents=True, exist_ok=True)
    source_dataset_path = _manifest_payload_path(manifest_path, manifest, "cycle_dataset")
    if source_dataset_path is None or not source_dataset_path.is_file():
        profile = _blocked_modern_window_profile(
            symbol=symbol,
            profile_id=profile_id,
            profile_dir=profile_dir,
            blocker="modern_window_source_dataset_missing",
            manifest_path=manifest_path,
        )
        return {profile_id: profile}

    frame = pd.read_parquet(source_dataset_path)
    if "bar_time_ms" not in frame.columns:
        profile = _blocked_modern_window_profile(
            symbol=symbol,
            profile_id=profile_id,
            profile_dir=profile_dir,
            blocker="modern_window_source_bar_time_ms_missing",
            manifest_path=manifest_path,
        )
        return {profile_id: profile}
    modern = frame.loc[pd.to_numeric(frame["bar_time_ms"], errors="coerce") >= MODERN_WINDOW_START_TIME_MS].copy()
    if modern.empty:
        profile = _blocked_modern_window_profile(
            symbol=symbol,
            profile_id=profile_id,
            profile_dir=profile_dir,
            blocker="modern_window_has_no_rows",
            manifest_path=manifest_path,
        )
        return {profile_id: profile}

    modern_dataset_path = profile_dir / "cycle_dataset.parquet"
    modern.sort_values("bar_time_ms", kind="mergesort").to_parquet(modern_dataset_path, index=False)
    lower_timeframe_path = _write_modern_lower_timeframe_dataset(
        profile_dir=profile_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        start_time_ms=int(modern["bar_time_ms"].min()),
        end_time_ms=int(modern["bar_time_ms"].max()) + 7 * 24 * 60 * 60_000,
    )
    cycle_spec_path = _write_modern_window_cycle_spec(
        symbol=symbol,
        repo_root=repo_root,
        output_dir=output_dir,
        readiness_path=readiness_path,
        source_manifest_path=manifest_path,
        modern_dataset_path=modern_dataset_path,
        lower_timeframe_path=lower_timeframe_path,
    )
    discovery_spec_path = _write_modern_window_discovery_spec(
        symbol=symbol,
        repo_root=repo_root,
        output_dir=output_dir,
        modern_dataset_path=modern_dataset_path,
        source_manifest_path=manifest_path,
    )
    cycle_payload = _read_json(cycle_spec_path)
    discovery_payload = _read_json(discovery_spec_path)
    window_start = int(modern["bar_time_ms"].min())
    window_end = int(modern["bar_time_ms"].max())
    profile_manifest_path = profile_dir / "modern_window_profile.json"
    profile = {
        "profile_id": profile_id,
        "profile_version": "modern-window-profile-v1",
        "profile_scope": "modern_window_holdout_research",
        "symbol": symbol,
        "status": "ready",
        "source_fixture_manifest_path": str(manifest_path),
        "source_fixture_manifest_sha256": f"sha256:{_file_sha256(manifest_path)}",
        "dataset_path": str(modern_dataset_path),
        "dataset_sha256": f"sha256:{_file_sha256(modern_dataset_path)}",
        "lower_timeframe_dataset_path": str(lower_timeframe_path) if lower_timeframe_path is not None else None,
        "lower_timeframe_dataset_sha256": f"sha256:{_file_sha256(lower_timeframe_path)}" if lower_timeframe_path is not None else None,
        "window_start_time_ms": window_start,
        "window_end_time_ms": window_end,
        "window_start_utc": _iso_time_ms(window_start),
        "window_end_utc": _iso_time_ms(window_end),
        "row_counts": {
            "bars": int(len(modern)),
            "lower_timeframe_bars": _parquet_row_count(lower_timeframe_path),
        },
        "cycle_spec_path": str(cycle_spec_path),
        "discovery_spec_path": str(discovery_spec_path),
        "cycle_id": cycle_payload.get("cycle_id"),
        "discovery_run_id": discovery_payload.get("run_id"),
        "candidate_pack_eligible": False,
        "candidate_pack_written": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    profile_manifest_path.write_text(_canonical_json(profile, indent=2) + "\n", encoding="utf-8")
    profile["profile_manifest_path"] = str(profile_manifest_path)
    profile_manifest_path.write_text(_canonical_json(profile, indent=2) + "\n", encoding="utf-8")
    return {profile_id: profile}


def _blocked_modern_window_profile(
    *,
    symbol: str,
    profile_id: str,
    profile_dir: Path,
    blocker: str,
    manifest_path: Path,
) -> dict[str, Any]:
    profile_manifest_path = profile_dir / "modern_window_profile.json"
    profile = {
        "profile_id": profile_id,
        "profile_version": "modern-window-profile-v1",
        "profile_scope": "modern_window_holdout_research",
        "symbol": symbol,
        "status": "blocked",
        "blockers": [blocker],
        "source_fixture_manifest_path": str(manifest_path),
        "profile_manifest_path": str(profile_manifest_path),
        "candidate_pack_eligible": False,
        "candidate_pack_written": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    profile_manifest_path.write_text(_canonical_json(profile, indent=2) + "\n", encoding="utf-8")
    return profile


def _manifest_payload_path(manifest_path: Path, manifest: Mapping[str, Any], key: str) -> Path | None:
    payload = manifest.get(key) if isinstance(manifest.get(key), Mapping) else {}
    raw = payload.get("path")
    if not raw:
        return None
    candidate = Path(str(raw)).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (manifest_path.parent / candidate).resolve()


def _write_modern_lower_timeframe_dataset(
    *,
    profile_dir: Path,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    start_time_ms: int,
    end_time_ms: int,
) -> Path | None:
    families = manifest.get("families") if isinstance(manifest.get("families"), Mapping) else {}
    lower_family = families.get("lower_timeframe_bars") if isinstance(families.get("lower_timeframe_bars"), Mapping) else {}
    raw = lower_family.get("path")
    if not raw:
        return None
    source = Path(str(raw)).expanduser()
    source_path = source.resolve() if source.is_absolute() else (manifest_path.parent / source).resolve()
    if not source_path.is_file():
        return None
    frame = pd.read_parquet(source_path)
    if "bar_time_ms" not in frame.columns:
        return None
    times = pd.to_numeric(frame["bar_time_ms"], errors="coerce")
    modern = frame.loc[(times >= int(start_time_ms)) & (times <= int(end_time_ms))].copy()
    if modern.empty:
        return None
    path = profile_dir / "lower_timeframe_bars_1m.parquet"
    modern.sort_values("bar_time_ms", kind="mergesort").to_parquet(path, index=False)
    return path


def _write_modern_window_cycle_spec(
    *,
    symbol: str,
    repo_root: Path,
    output_dir: Path,
    readiness_path: Path,
    source_manifest_path: Path,
    modern_dataset_path: Path,
    lower_timeframe_path: Path | None,
) -> Path:
    lower = symbol.lower()
    base_path = repo_root / "configs" / "research" / f"full_cycle_{lower}_durable_public_archive_r104_deep_v1.json"
    payload = _read_json(base_path)
    payload["cycle_id"] = f"r106-{lower}-modern-window-candidate-depth-v1"
    payload["work_packet"] = "WPR106-16-research-workflow-completion"
    payload["maturity_label"] = "modern_window_holdout_research"
    payload["output_dir"] = str(output_dir / "historical_cycles" / payload["cycle_id"])
    payload["candidate_pack_eligible"] = False
    payload["candidate_pack_written"] = False
    data = payload.setdefault("data", {})
    data["dataset_manifest_paths"] = []
    data["dataset_path"] = str(modern_dataset_path)
    data["lower_timeframe_dataset_path"] = str(lower_timeframe_path) if lower_timeframe_path is not None else None
    data["source_fixture_manifest_path"] = str(source_manifest_path)
    data["evidence_scope"] = "modern_window_holdout_research"
    data["durable_fixture_readiness_config_path"] = str(readiness_path)
    data["candidate_pack_eligible"] = False
    data["candidate_blocker_codes"] = [
        "modern_window_profile_is_holdout_research_not_promotion_evidence",
        "candidate_validation_gates_not_yet_passed",
    ]
    active_dir = output_dir / "active_specs"
    active_dir.mkdir(parents=True, exist_ok=True)
    path = active_dir / f"{payload['cycle_id']}.json"
    path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _write_modern_window_discovery_spec(
    *,
    symbol: str,
    repo_root: Path,
    output_dir: Path,
    modern_dataset_path: Path,
    source_manifest_path: Path,
) -> Path:
    lower = symbol.lower()
    base_path = repo_root / "configs" / "discovery" / f"exact_entry_sweep_{lower}_durable_r104_v1.json"
    payload = _read_json(base_path)
    payload["run_id"] = f"exact_entry_sweep_{lower}_modern_window_candidate_depth_v1"
    payload["research_output_dir"] = str(output_dir)
    payload.setdefault("data", {})["dataset_manifest_paths"] = []
    payload.setdefault("data", {})["dataset_path"] = str(modern_dataset_path)
    payload.setdefault("data", {})["source_fixture_manifest_path"] = str(source_manifest_path)
    metadata = payload.setdefault("metadata", {})
    metadata["work_packet"] = "WPR106-16-research-workflow-completion"
    metadata["profile_scope"] = "modern_window_holdout_research"
    metadata["candidate_pack_eligible"] = False
    active_dir = output_dir / "active_specs"
    active_dir.mkdir(parents=True, exist_ok=True)
    path = active_dir / f"{payload['run_id']}.json"
    path.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _parquet_row_count(path: Path | None) -> int | None:
    if path is None or not path.is_file():
        return None
    return int(pq.ParquetFile(path).metadata.num_rows)


def _iso_time_ms(value: int) -> str:
    return datetime.fromtimestamp(int(value) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _zip_csv_member(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv") and not name.endswith("/")]
    if len(members) != 1:
        raise ValueError(f"archive_csv_member_count_mismatch:{path}:{len(members)}")
    return members[0]


def _zip_csv_dict_rows(path: Path, headerless_fields: Sequence[str]) -> Iterable[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        member = _zip_csv_member(path)
        with archive.open(member, "r") as binary_handle:
            text_handle = io.TextIOWrapper(binary_handle, encoding="utf-8-sig", newline="")
            reader = csv.reader(text_handle)
            first: list[str] | None = None
            for candidate in reader:
                if candidate and any(cell.strip() for cell in candidate):
                    first = candidate
                    break
            if first is None:
                raise ValueError(f"archive_csv_has_no_rows:{path}")
            has_header = any(not _looks_numeric(value) for value in first[:2])
            fieldnames = [_field_name(value) for value in first] if has_header else list(headerless_fields)
            if not has_header:
                yield {
                    fieldnames[index] if index < len(fieldnames) else f"extra_{index}": value.strip()
                    for index, value in enumerate(first)
                }
            for row in reader:
                if not row or not any(cell.strip() for cell in row):
                    continue
                yield {
                    fieldnames[index] if index < len(fieldnames) else f"extra_{index}": value.strip()
                    for index, value in enumerate(row)
                }


def _field_name(value: object) -> str:
    text = str(value).strip().replace(" ", "_").replace("-", "_").lower()
    aliases = {
        "open_time": "open_time",
        "open_time_ms": "open_time",
        "close_time": "close_time",
        "quote_asset_volume": "quote_asset_volume",
        "number_of_trades": "number_of_trades",
        "trade_count": "number_of_trades",
        "taker_buy_base_asset_volume": "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume": "taker_buy_quote_asset_volume",
        "agg_trade_id": "aggregate_trade_id",
        "aggregate_trade_id": "aggregate_trade_id",
        "transact_time": "transact_time",
        "transact_time_ms": "transact_time",
        "is_buyer_maker": "is_buyer_maker",
    }
    return aliases.get(text, text)


def _fixed_interval_report(values: Sequence[Any], *, interval_ms: int) -> dict[str, Any]:
    times = sorted(int(value) for value in values)
    seen: set[int] = set()
    duplicates = []
    for value in times:
        if value in seen:
            duplicates.append(value)
        seen.add(value)
    unique = sorted(seen)
    gaps = []
    for previous, current in zip(unique, unique[1:]):
        delta = current - previous
        if delta != interval_ms:
            gaps.append(
                {
                    "previous_event_time_ms": previous,
                    "next_event_time_ms": current,
                    "delta_ms": delta,
                    "missing_event_count": max(0, int(delta // interval_ms) - 1),
                }
            )
    return {"gap_count": len(gaps), "duplicate_count": len(duplicates), "gaps": gaps, "duplicates": duplicates}


def _window_selection_from_frame(frame: pd.DataFrame) -> dict[str, Any]:
    times = sorted(int(value) for value in frame["event_time_ms"].tolist())
    labels = ("trend_bull", "drawdown_bear", "range_chop", "high_vol_shock")
    windows: dict[str, dict[str, Any]] = {}
    for index, label in enumerate(labels):
        start_index = min(len(times) - 1, int(index * len(times) / len(labels)))
        end_index = min(len(times) - 1, int((index + 1) * len(times) / len(labels)) - 1)
        windows[label] = {
            "start_time_ms": times[start_index],
            "end_time_ms": times[end_index] + 15 * 60 * 1000,
            "source": "binance_vision_public_archive_candidate_depth_partition",
            "selection_note": "contiguous candidate-depth coverage segment label for readiness compatibility",
        }
    return {"regime_windows": windows}


def _iso_window(window: Mapping[str, Any]) -> str:
    start = datetime.fromtimestamp(int(window["start_time_ms"]) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    end = datetime.fromtimestamp(int(window["end_time_ms"]) / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return f"{start}/{end}"


def _required_text(row: Mapping[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    raise ValueError(f"required_csv_field_missing:{'/'.join(keys)}")


def _required_int(row: Mapping[str, str], *keys: str) -> int:
    return int(float(_required_text(row, *keys)))


def _optional_int(row: Mapping[str, str], *keys: str) -> int | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return int(float(value))
    return None


def _optional_bool(row: Mapping[str, str], *keys: str) -> bool | None:
    for key in keys:
        value = row.get(key)
        if value is None or str(value).strip() == "":
            continue
        text = str(value).strip().lower()
        if text in {"true", "1", "t", "yes", "y"}:
            return True
        if text in {"false", "0", "f", "no", "n"}:
            return False
        raise ValueError(f"csv_bool_field_invalid:{key}:{value}")
    return None


def _looks_numeric(value: object) -> bool:
    try:
        float(str(value).strip())
        return True
    except ValueError:
        return False


def _normalize_symbols(symbols: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))
    if not normalized:
        raise ValueError("durable_data_collection_symbols_required")
    unsupported = sorted(set(normalized) - SUPPORTED_DURABLE_COLLECTION_SYMBOLS)
    if unsupported:
        raise ValueError(f"unsupported_durable_data_collection_symbols:{','.join(unsupported)}")
    return normalized


def _month_periods(start_month: str, end_month: str) -> list[str]:
    start_year, start_mon = _parse_month(start_month)
    end_year, end_mon = _parse_month(end_month)
    start_value = start_year * 12 + (start_mon - 1)
    end_value = end_year * 12 + (end_mon - 1)
    if end_value < start_value:
        raise ValueError("durable_data_collection_end_month_before_start_month")
    periods = []
    for value in range(start_value, end_value + 1):
        year = value // 12
        month = (value % 12) + 1
        periods.append(f"{year:04d}-{month:02d}")
    return periods


def _parse_month(value: str) -> tuple[int, int]:
    parts = str(value).strip().split("-")
    if len(parts) != 2:
        raise ValueError("month_must_be_yyyy_mm")
    year = int(parts[0])
    month = int(parts[1])
    if month < 1 or month > 12:
        raise ValueError("month_must_be_yyyy_mm")
    return year, month


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_payload(payload: Any) -> str:
    return f"sha256:{sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":") if indent is None else None,
        indent=indent,
        ensure_ascii=True,
        default=str,
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected_json_object:{path}")
    return payload
