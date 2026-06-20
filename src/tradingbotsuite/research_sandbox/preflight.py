from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.market_data import (
    SandboxMarketDataCache,
    normalized_market_data_source_key,
)
from tradingbotsuite.research_sandbox.spec import (
    ALLOWED_EXIT_PROFILES,
    ExitVariant,
    SandboxRunSpec,
    StrategyCatalogRow,
    VenueArchiveDescriptor,
)
from tradingbotsuite.research_sandbox.strategy_blueprints import (
    materialize_strategy_signals,
    resolve_materialized_signal_column,
)


SANDBOX_COMPATIBILITY_PREFLIGHT_JSON_NAME = "sandbox_compatibility_preflight.json"
SANDBOX_COMPATIBILITY_PREFLIGHT_PARQUET_NAME = "sandbox_compatibility_preflight.parquet"


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _container_metadata_row_payload(normalization: dict[str, Any]) -> dict[str, Any]:
    container_metadata = normalization.get("container_member_metadata", {}) or {}
    if not isinstance(container_metadata, dict):
        container_metadata = {}
    selected_sample = container_metadata.get("selected_member_name_sample", [])
    if not isinstance(selected_sample, (list, tuple)):
        selected_sample = []
    suffix_counts = container_metadata.get("available_member_suffix_counts", {})
    if not isinstance(suffix_counts, dict):
        suffix_counts = {}
    return {
        "container_member_metadata": container_metadata,
        "container_kind": container_metadata.get("container_kind"),
        "selected_member_suffix": container_metadata.get("selected_member_suffix"),
        "selected_member_count": int(container_metadata.get("selected_member_count", 0) or 0),
        "selected_member_name_sample": [str(name) for name in selected_sample],
        "selected_member_names_truncated": bool(container_metadata.get("selected_member_names_truncated", False)),
        "available_member_suffix_counts": {str(key): int(value) for key, value in suffix_counts.items()},
        "available_member_suffix_count": int(container_metadata.get("available_member_suffix_count", 0) or 0),
        "loadable_member_count": int(container_metadata.get("loadable_member_count", 0) or 0),
    }


def _effective_window_bounds(
    spec: SandboxRunSpec,
    descriptor: VenueArchiveDescriptor,
) -> tuple[pd.Timestamp, pd.Timestamp, bool]:
    start_date = max(spec.data_window.start, descriptor.window.start)
    end_date = min(spec.data_window.end, descriptor.window.end)
    start = pd.Timestamp(start_date, tz="UTC")
    end_exclusive = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    return start, end_exclusive, end_date >= start_date


def _effective_window_payload(spec: SandboxRunSpec, descriptor: VenueArchiveDescriptor) -> dict[str, Any]:
    start, end_exclusive, has_overlap = _effective_window_bounds(spec, descriptor)
    if not has_overlap:
        return {"start": "no_overlap", "end": "no_overlap"}
    return {
        "start": start.date().isoformat(),
        "end": (end_exclusive - pd.Timedelta(days=1)).date().isoformat(),
    }


def _window_frame(frame: pd.DataFrame, spec: SandboxRunSpec, descriptor: VenueArchiveDescriptor) -> pd.DataFrame:
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    start, end_exclusive, has_overlap = _effective_window_bounds(spec, descriptor)
    if not has_overlap:
        return frame.iloc[0:0].copy().reset_index(drop=True)
    return frame[(timestamps >= start) & (timestamps < end_exclusive)].reset_index(drop=True)


def _source_path(descriptor: VenueArchiveDescriptor, shared_market_data_path: str | Path | None) -> Path | None:
    if shared_market_data_path is not None:
        return Path(shared_market_data_path)
    return descriptor.data_path


def _source_cache_key(path: str | Path, *, spec: SandboxRunSpec, descriptor: VenueArchiveDescriptor) -> str:
    window = _effective_window_payload(spec, descriptor)
    return "|".join(
        [
            normalized_market_data_source_key(path),
            str(window["start"]),
            str(window["end"]),
        ]
    )


def _loaded_venue_frame(
    descriptor: VenueArchiveDescriptor,
    *,
    spec: SandboxRunSpec,
    shared_market_data_path: str | Path | None,
    strategies: list[StrategyCatalogRow],
    prepared_source_cache: dict[str, tuple[pd.DataFrame | None, dict[str, Any], list[str]]],
    market_data_cache: SandboxMarketDataCache,
) -> tuple[pd.DataFrame | None, dict[str, Any], list[str]]:
    source_path = _source_path(descriptor, shared_market_data_path)
    routing_mode = "shared_market_data_path" if shared_market_data_path is not None else "descriptor_data_path"
    metadata: dict[str, Any] = {
        "routing_mode": routing_mode,
        "source_path": str(source_path) if source_path is not None else None,
        "normalized_row_count": 0,
        "descriptor_window_row_count": 0,
        "columns": [],
        "has_high_low": False,
        "normalization": {},
        "effective_window": _effective_window_payload(spec, descriptor),
    }
    if source_path is None:
        return None, metadata, ["missing_data_path"]
    try:
        if not Path(source_path).exists():
            return None, metadata, ["data_path_not_found"]
        if shared_market_data_path is None:
            source_integrity_errors = market_data_cache.descriptor_source_integrity_errors(
                descriptor,
                data_path=source_path,
            )
            if source_integrity_errors:
                return None, metadata, source_integrity_errors
        cache_key = _source_cache_key(source_path, spec=spec, descriptor=descriptor)
        cached = prepared_source_cache.get(cache_key)
        if cached is not None:
            return cached[0], dict(cached[1]), list(cached[2])
        frame = market_data_cache.load_frame(source_path)
        window = _window_frame(frame, spec, descriptor)
        window = materialize_strategy_signals(window, strategies, dedupe_blueprint_signals=True)
        metadata.update(
            {
                "normalized_row_count": int(len(frame)),
                "descriptor_window_row_count": int(len(window)),
                "columns": [str(column) for column in window.columns],
                "has_high_low": "high" in window.columns and "low" in window.columns,
                "normalization": dict(frame.attrs.get("sandbox_normalization_metadata") or {}),
            }
        )
        if window.empty:
            result = (window, metadata, ["no_market_rows_in_2024_plus_window"])
            prepared_source_cache[cache_key] = result
            return result[0], dict(result[1]), list(result[2])
        result = (window, metadata, [])
        prepared_source_cache[cache_key] = result
        return result[0], dict(result[1]), list(result[2])
    except Exception as exc:  # noqa: BLE001 - preflight reports loader failures without aborting every descriptor.
        return None, metadata, [f"load_error:{type(exc).__name__}:{exc}"]


def _active_signal_count(frame: pd.DataFrame | None, signal_column: str) -> int:
    if frame is None:
        return 0
    signal_column = resolve_materialized_signal_column(frame, signal_column)
    if signal_column not in frame.columns:
        return 0
    values = pd.to_numeric(frame[signal_column], errors="coerce").fillna(0.0)
    return int((values > 0.0).sum())


def _strategy_base_blockers(frame: pd.DataFrame | None, strategy: StrategyCatalogRow, venue_blockers: list[str]) -> list[str]:
    blockers = list(venue_blockers)
    if frame is None:
        return blockers
    signal_column = resolve_materialized_signal_column(frame, strategy.signal_column)
    if signal_column not in frame.columns:
        blockers.append(f"missing_signal_column:{strategy.signal_column}")
    if strategy.filter_column and strategy.filter_column not in frame.columns:
        blockers.append(f"missing_strategy_filter_column:{strategy.filter_column}")
    return blockers


def _strategy_exit_profile(strategy: StrategyCatalogRow) -> str:
    return str(strategy.exit_profile or "fixed_hold").strip().lower()


def _strategy_exit_variants(
    spec: SandboxRunSpec,
    strategy: StrategyCatalogRow,
) -> tuple[tuple[ExitVariant, ...], tuple[str, ...]]:
    profile = _strategy_exit_profile(strategy)
    if profile == "fixed_hold":
        return tuple(spec.exit_variants), ()
    if profile not in ALLOWED_EXIT_PROFILES:
        return (), (f"unsupported_strategy_exit_profile:{profile}",)
    matching = tuple(variant for variant in spec.exit_variants if variant.exit_profile == profile)
    if not matching:
        return (), (f"strategy_exit_profile_not_in_run_spec:{profile}",)
    return matching, ()


def _trial_counts(
    *,
    frame: pd.DataFrame | None,
    spec: SandboxRunSpec,
    exit_variants: tuple[ExitVariant, ...],
    base_blockers: list[str],
) -> tuple[int, int, dict[str, int]]:
    runnable = 0
    blocked = 0
    reason_counts: Counter[str] = Counter()
    for filter_variant in spec.filter_variants:
        for exit_variant in exit_variants:
            reasons = list(base_blockers)
            if frame is not None and filter_variant.filter_column and filter_variant.filter_column not in frame.columns:
                reasons.append(f"missing_filter_variant_column:{filter_variant.filter_column}")
            if frame is not None and exit_variant.exit_profile != "fixed_hold":
                for column in ("high", "low"):
                    if column not in frame.columns:
                        reasons.append(f"missing_ohlc_column:{column}")
            count = len(spec.holding_periods)
            if reasons:
                blocked += count
                reason_counts.update(reasons)
            else:
                runnable += count
    return runnable, blocked, dict(sorted(reason_counts.items()))


def _preflight_row(
    *,
    preflight_id: str,
    spec: SandboxRunSpec,
    strategy: StrategyCatalogRow,
    descriptor: VenueArchiveDescriptor,
    frame: pd.DataFrame | None,
    venue_metadata: dict[str, Any],
    venue_blockers: list[str],
) -> dict[str, Any]:
    selected_exit_variants, strategy_exit_blockers = _strategy_exit_variants(spec, strategy)
    counted_exit_variants = selected_exit_variants or tuple(spec.exit_variants)
    trial_estimate = len(spec.holding_periods) * len(counted_exit_variants) * len(spec.filter_variants)
    base_blockers = _strategy_base_blockers(frame, strategy, venue_blockers)
    base_blockers.extend(strategy_exit_blockers)
    runnable, blocked, reason_counts = _trial_counts(
        frame=frame,
        spec=spec,
        exit_variants=counted_exit_variants,
        base_blockers=base_blockers,
    )
    normalization = dict(venue_metadata.get("normalization", {}) or {})
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_compatibility_preflight_row",
        "preflight_id": preflight_id,
        "run_id": spec.run_id,
        "descriptor_id": descriptor.descriptor_id,
        "venue": descriptor.venue,
        "symbol": descriptor.symbol,
        "data_family": descriptor.data_family,
        "interval": descriptor.interval,
        "hypothesis_id": strategy.hypothesis_id,
        "family": strategy.family,
        "source_id": strategy.source_id,
        "signal_column": strategy.signal_column,
        "side": strategy.side,
        "strategy_filter_column": strategy.filter_column,
        "strategy_exit_profile": _strategy_exit_profile(strategy),
        "status": "runnable" if runnable > 0 else "blocked",
        "trial_estimate": trial_estimate,
        "runnable_trial_estimate": runnable,
        "blocked_trial_estimate": blocked,
        "blocker_reasons": sorted(reason_counts),
        "blocker_reason_counts": reason_counts,
        "active_signal_count": _active_signal_count(frame, strategy.signal_column),
        "market_row_count": int(venue_metadata.get("descriptor_window_row_count", 0) or 0),
        "normalized_row_count": int(venue_metadata.get("normalized_row_count", 0) or 0),
        "routing_mode": venue_metadata.get("routing_mode"),
        "source_path": venue_metadata.get("source_path"),
        "effective_window": dict(venue_metadata.get("effective_window", {}) or {}),
        "columns": list(venue_metadata.get("columns", [])),
        "has_high_low": bool(venue_metadata.get("has_high_low", False)),
        "normalization": normalization,
        **_container_metadata_row_payload(normalization),
        "holding_period_count": len(spec.holding_periods),
        "exit_variant_count": len(spec.exit_variants),
        "strategy_exit_variant_count": len(selected_exit_variants),
        "filter_variant_count": len(spec.filter_variants),
    }
    require_sandbox_boundary(row, payload_name="sandbox_compatibility_preflight_row")
    return row


def preflight_sandbox_compatibility(
    *,
    spec: SandboxRunSpec,
    strategies: list[StrategyCatalogRow],
    venues: list[VenueArchiveDescriptor],
    output_dir: str | Path,
    shared_market_data_path: str | Path | None = None,
    market_data_cache: SandboxMarketDataCache | None = None,
) -> dict[str, Any]:
    if not strategies:
        raise ValueError("sandbox compatibility preflight requires at least one strategy")
    if not venues:
        raise ValueError("sandbox compatibility preflight requires at least one venue descriptor")
    preflight_id = digest_payload(
        {
            "spec": spec.to_payload(),
            "strategies": [strategy.to_payload() for strategy in strategies],
            "venues": [venue.to_payload() for venue in venues],
            "shared_market_data_path": str(shared_market_data_path) if shared_market_data_path is not None else None,
        },
        prefix="sbxpreflight",
        length=24,
    )
    rows: list[dict[str, Any]] = []
    venue_cache: dict[str, tuple[pd.DataFrame | None, dict[str, Any], list[str]]] = {}
    prepared_source_cache: dict[str, tuple[pd.DataFrame | None, dict[str, Any], list[str]]] = {}
    cache = market_data_cache or SandboxMarketDataCache()
    for descriptor in venues:
        venue_cache[descriptor.descriptor_id] = _loaded_venue_frame(
            descriptor,
            spec=spec,
            shared_market_data_path=shared_market_data_path,
            strategies=strategies,
            prepared_source_cache=prepared_source_cache,
            market_data_cache=cache,
        )
        frame, metadata, blockers = venue_cache[descriptor.descriptor_id]
        for strategy in strategies:
            rows.append(
                _preflight_row(
                    preflight_id=preflight_id,
                    spec=spec,
                    strategy=strategy,
                    descriptor=descriptor,
                    frame=frame,
                    venue_metadata=metadata,
                    venue_blockers=blockers,
                )
            )

    output_path = Path(output_dir) / preflight_id
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / SANDBOX_COMPATIBILITY_PREFLIGHT_JSON_NAME
    parquet_path = output_path / SANDBOX_COMPATIBILITY_PREFLIGHT_PARQUET_NAME
    frame = pd.DataFrame([_row_for_parquet(row) for row in rows])
    if frame.empty:
        frame = pd.DataFrame(columns=["preflight_id", "status", *SANDBOX_BOUNDARY_FLAGS])
    frame.to_parquet(parquet_path, index=False)
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    blocker_counts: Counter[str] = Counter()
    for row in rows:
        blocker_counts.update(dict(row.get("blocker_reason_counts", {}) or {}))
    payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_compatibility_preflight",
        "preflight_id": preflight_id,
        "output_dir": str(output_path),
        "preflight_json_path": str(json_path),
        "preflight_parquet_path": str(parquet_path),
        "run_id": spec.run_id,
        "data_window": spec.data_window.to_payload(),
        "strategy_count": len(strategies),
        "descriptor_count": len(venues),
        "row_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "trial_estimate": sum(int(row["trial_estimate"]) for row in rows),
        "runnable_trial_estimate": sum(int(row["runnable_trial_estimate"]) for row in rows),
        "blocked_trial_estimate": sum(int(row["blocked_trial_estimate"]) for row in rows),
        "blocker_reason_counts": dict(sorted(blocker_counts.items())),
        "shared_market_data_path": str(shared_market_data_path) if shared_market_data_path is not None else None,
        "rows": rows,
    }
    require_sandbox_boundary(payload, payload_name="sandbox_compatibility_preflight")
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return payload
