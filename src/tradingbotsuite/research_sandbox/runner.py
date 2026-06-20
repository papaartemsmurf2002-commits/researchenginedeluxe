from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.evidence_request import EvidenceRequestDescriptor, build_evidence_requests
from tradingbotsuite.research_sandbox.fast_backtest import (
    TrialResult,
    rank_results,
    run_fixed_hold_sweep,
    run_fixed_hold_sweep_for_venue_frames,
)
from tradingbotsuite.research_sandbox.market_data import (
    SandboxMarketDataCache,
    load_market_frame,
    load_market_frame_for_descriptor,
)
from tradingbotsuite.research_sandbox.spec import SandboxRunSpec, StrategyCatalogRow, VenueArchiveDescriptor
from tradingbotsuite.research_sandbox.store import ResultStore, SandboxArtifacts


@dataclass(frozen=True)
class SandboxRunResult:
    artifacts: SandboxArtifacts
    results: list[TrialResult]
    evidence_requests: list[EvidenceRequestDescriptor]


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _market_source_container_metadata(frame: pd.DataFrame) -> dict[str, Any]:
    normalization = frame.attrs.get("sandbox_normalization_metadata")
    if not isinstance(normalization, dict):
        return {}
    container_metadata = normalization.get("container_member_metadata", {}) or {}
    if not isinstance(container_metadata, dict) or not container_metadata.get("container_kind"):
        return {}
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
        "selected_member_count": _safe_int(container_metadata.get("selected_member_count")),
        "selected_member_name_sample": [str(name) for name in selected_sample],
        "selected_member_names_truncated": bool(container_metadata.get("selected_member_names_truncated", False)),
        "available_member_suffix_counts": {str(key): _safe_int(value) for key, value in suffix_counts.items()},
        "available_member_suffix_count": _safe_int(container_metadata.get("available_member_suffix_count")),
        "loadable_member_count": _safe_int(container_metadata.get("loadable_member_count")),
    }


def run_sandbox_sweep(
    *,
    spec: SandboxRunSpec,
    market_frame: pd.DataFrame,
    strategies: list[StrategyCatalogRow],
    venues: list[VenueArchiveDescriptor],
    output_root: str | Path,
    min_request_score: float = 0.0,
) -> SandboxRunResult:
    if not strategies:
        raise ValueError("sandbox sweep requires at least one strategy catalog row")
    if not venues:
        raise ValueError("sandbox sweep requires at least one venue archive descriptor")

    results = run_fixed_hold_sweep(
        market_frame=market_frame,
        run_spec=spec,
        strategies=strategies,
        venues=venues,
    )
    evidence_requests = build_evidence_requests(
        results,
        max_requests=spec.max_evidence_requests,
        min_score=min_request_score,
    )
    artifacts = ResultStore(output_root).write_run(
        spec=spec,
        strategies=strategies,
        venues=venues,
        results=results,
        evidence_requests=evidence_requests,
    )
    return SandboxRunResult(
        artifacts=artifacts,
        results=results,
        evidence_requests=evidence_requests,
    )
    return SandboxRunResult(
        artifacts=artifacts,
        results=results,
        evidence_requests=evidence_requests,
    )


def run_sandbox_archive_sweep(
    *,
    spec: SandboxRunSpec,
    strategies: list[StrategyCatalogRow],
    venues: list[VenueArchiveDescriptor],
    output_root: str | Path,
    shared_market_data_path: str | Path | None = None,
    min_request_score: float = 0.0,
    market_data_cache: SandboxMarketDataCache | None = None,
) -> SandboxRunResult:
    if not strategies:
        raise ValueError("sandbox archive sweep requires at least one strategy catalog row")
    if not venues:
        raise ValueError("sandbox archive sweep requires at least one venue archive descriptor")

    if shared_market_data_path is not None:
        frame = _load_shared_market_frame(shared_market_data_path, market_data_cache=market_data_cache)
        market_frames = {venue.descriptor_id: frame for venue in venues}
        market_sources = {
            venue.descriptor_id: _market_source_payload(
                venue,
                frame,
                shared_market_data_path=shared_market_data_path,
            )
            for venue in venues
        }
        results = run_fixed_hold_sweep_for_venue_frames(
            market_frames=market_frames,
            run_spec=spec,
            strategies=strategies,
            venues=venues,
            market_sources=market_sources,
        )
    else:
        results = []
        for venue in venues:
            frame = _load_descriptor_market_frame(venue, market_data_cache=market_data_cache)
            market_source = _market_source_payload(venue, frame, shared_market_data_path=None)
            results.extend(
                run_fixed_hold_sweep_for_venue_frames(
                    market_frames={venue.descriptor_id: frame},
                    run_spec=spec,
                    strategies=strategies,
                    venues=[venue],
                    market_sources={venue.descriptor_id: market_source},
                    apply_rank_top_n=False,
                )
            )
        results = rank_results(results, top_n=spec.rank_top_n)
    evidence_requests = build_evidence_requests(
        results,
        max_requests=spec.max_evidence_requests,
        min_score=min_request_score,
    )
    artifacts = ResultStore(output_root).write_run(
        spec=spec,
        strategies=strategies,
        venues=venues,
        results=results,
        evidence_requests=evidence_requests,
    )
    return SandboxRunResult(
        artifacts=artifacts,
        results=results,
        evidence_requests=evidence_requests,
    )


def _load_shared_market_frame(
    shared_market_data_path: str | Path,
    *,
    market_data_cache: SandboxMarketDataCache | None,
) -> pd.DataFrame:
    if market_data_cache is not None:
        return market_data_cache.load_frame(shared_market_data_path)
    return load_market_frame(shared_market_data_path)


def _load_descriptor_market_frame(
    venue: VenueArchiveDescriptor,
    *,
    market_data_cache: SandboxMarketDataCache | None,
) -> pd.DataFrame:
    if market_data_cache is not None:
        market_data_cache.require_descriptor_source_integrity(venue, data_path=venue.data_path)
        if venue.data_path is None:
            raise ValueError("venue descriptor requires data_path or CLI market_data path for sandbox execution")
        return market_data_cache.load_frame(venue.data_path)
    return load_market_frame_for_descriptor(venue)


def _market_source_payload(
    venue: VenueArchiveDescriptor,
    frame: pd.DataFrame,
    *,
    shared_market_data_path: str | Path | None,
) -> dict[str, Any]:
    return {
        "routing_mode": "shared_market_data_path" if shared_market_data_path is not None else "descriptor_data_path",
        "descriptor_id": venue.descriptor_id,
        "venue": venue.venue,
        "symbol": venue.symbol,
        "data_family": venue.data_family,
        "data_path": str(venue.data_path) if venue.data_path is not None else None,
        "shared_market_data_path": str(shared_market_data_path) if shared_market_data_path is not None else None,
        **_market_source_container_metadata(frame),
    }
