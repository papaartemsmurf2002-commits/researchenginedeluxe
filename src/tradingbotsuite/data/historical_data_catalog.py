from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Mapping, Sequence

from tradingbotsuite.data.contracts import data_provider_capabilities, data_source_descriptors
from tradingbotsuite.data.durable_public_archive import (
    CANDIDATE_READY_CONTEXT_1M_MIN_ROWS,
    CANDIDATE_READY_MIN_EFFECTIVE_HOURS,
    CANDIDATE_READY_PRIMARY_15M_MIN_BARS,
    DEFAULT_DURABLE_COLLECTION_SYMBOLS,
    collect_candidate_depth_public_archive_fixtures,
)
from tradingbotsuite.research.archive_sources import archive_source_descriptors
from tradingbotsuite.research.live_readiness import research_boundary_metadata

HISTORICAL_DATA_CATALOG_VERSION = "historical-data-catalog-v1"
DEFAULT_HISTORICAL_CATALOG_START_MONTH = "2020-01"
DEFAULT_HISTORICAL_CATALOG_MARKET = "futures/um"

PROVIDER_SOURCE_REFERENCES = {
    "binance_vision": {
        "official_reference": "https://github.com/binance/binance-public-data",
        "operator_note": "Public monthly/daily archive with checksum sidecars; this is the active implemented catalog source.",
    },
    "crypto_lake": {
        "official_reference": "https://crypto-lake.com/data/",
        "operator_note": "Local/vendor exports can be ingested elsewhere in the branch, but no unattended catalog download is configured.",
    },
    "bybit_archive": {
        "official_reference": "https://www.bybit.com/derivatives/en/history-data",
        "operator_note": "Official public history surface exists; normalized downloader/parser/checksum contract is still required before candidate-depth use.",
    },
    "hyperliquid_archive": {
        "official_reference": "https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data",
        "operator_note": "Requester-pays S3 archive exists and may be incomplete; parser plus journal reconciliation is required before candidate-depth use.",
    },
}


@dataclass(frozen=True, slots=True)
class HistoricalDataCatalogRefreshResult:
    output_dir: Path
    catalog_path: Path
    catalog_sha256: str
    source_summary_path: Path | None
    symbol_payloads: Mapping[str, Mapping[str, Any]]
    provider_states: Mapping[str, Mapping[str, Any]]

    def to_payload(self) -> dict[str, Any]:
        return {
            "historical_data_catalog_version": HISTORICAL_DATA_CATALOG_VERSION,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "output_dir": str(self.output_dir),
            "catalog_path": str(self.catalog_path),
            "historical_data_catalog_path": str(self.catalog_path),
            "catalog_sha256": self.catalog_sha256,
            "source_summary_path": str(self.source_summary_path) if self.source_summary_path is not None else None,
            "symbols": {symbol: dict(payload) for symbol, payload in sorted(self.symbol_payloads.items())},
            "provider_states": {
                source_name: dict(payload)
                for source_name, payload in sorted(self.provider_states.items())
            },
        }


def default_historical_catalog_end_month(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    year = current.year
    month = current.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}-{month:02d}"


def refresh_historical_data_catalog(
    *,
    output_dir: Path,
    symbols: Sequence[str] = DEFAULT_DURABLE_COLLECTION_SYMBOLS,
    start_month: str = DEFAULT_HISTORICAL_CATALOG_START_MONTH,
    end_month: str | None = None,
    repo_root: Path | None = None,
    market: str = DEFAULT_HISTORICAL_CATALOG_MARKET,
    fetcher: Callable[[str], bytes] | None = None,
    download_cache_dir: Path | None = None,
    download_fallback_dirs: Sequence[Path] = (),
    fixture_fallback_dirs: Sequence[Path] = (),
    min_primary_15m_bars: int = CANDIDATE_READY_PRIMARY_15M_MIN_BARS,
    min_context_1m_rows: int = CANDIDATE_READY_CONTEXT_1M_MIN_ROWS,
    min_effective_hours: int = CANDIDATE_READY_MIN_EFFECTIVE_HOURS,
) -> HistoricalDataCatalogRefreshResult:
    """Refresh the branch historical-data source-of-truth catalog.

    The catalog is intentionally broader than the currently implemented
    collector. It records all registered provider surfaces, but the active
    generated fixture/spec paths come only from implemented, validated sources.
    """

    repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_end_month = end_month or default_historical_catalog_end_month()

    source_output_dir = output_dir / "sources" / "binance_vision_public_archive"
    source_result = collect_candidate_depth_public_archive_fixtures(
        output_dir=source_output_dir,
        symbols=symbols,
        start_month=start_month,
        end_month=resolved_end_month,
        repo_root=repo_root,
        market=market,
        fetcher=fetcher,
        download_cache_dir=download_cache_dir,
        download_fallback_dirs=download_fallback_dirs,
        fixture_fallback_dirs=fixture_fallback_dirs,
        min_primary_15m_bars=min_primary_15m_bars,
        min_context_1m_rows=min_context_1m_rows,
        min_effective_hours=min_effective_hours,
    )
    symbol_payloads = {
        symbol: _catalog_symbol_payload(symbol, payload, source_result.summary_path)
        for symbol, payload in sorted(source_result.symbol_payloads.items())
    }
    provider_states = historical_data_provider_states(
        source_summary_path=source_result.summary_path,
        active_symbol_count=len(symbol_payloads),
    )
    catalog_ready = bool(symbol_payloads) and all(
        payload.get("candidate_depth_ready") is True for payload in symbol_payloads.values()
    )
    catalog_payload = {
        "historical_data_catalog_version": HISTORICAL_DATA_CATALOG_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "stage": "R106",
        "work_packet": "WPR106-01-central-historical-data-catalog",
        "catalog_scope": "central_source_of_truth_for_research_historical_data",
        "catalog_ready": catalog_ready,
        "candidate_depth_ready": catalog_ready,
        "source_policy": _source_policy(),
        "canonical_format": _canonical_format(),
        "market": market,
        "start_month": start_month,
        "end_month": resolved_end_month,
        "symbols": symbol_payloads,
        "provider_states": provider_states,
        "active_source": {
            "source_name": "binance_vision",
            "source_role": "primary_generated_fixture_contract",
            "source_summary_path": str(source_result.summary_path),
            "symbol_count": len(symbol_payloads),
        },
        "intervention_required": _intervention_required(provider_states),
        "notes": [
            "This catalog is the only required Step 0 data workflow artifact.",
            "Old durable collection summaries are compatibility artifacts; required workflow readiness should prefer this catalog.",
            "Registered provider surfaces remain visible until their ingestion and validation contracts are implemented.",
        ],
    }
    catalog_path = output_dir / "historical_data_catalog.json"
    catalog_path.write_text(_canonical_json(catalog_payload, indent=2) + "\n", encoding="utf-8")
    return HistoricalDataCatalogRefreshResult(
        output_dir=output_dir,
        catalog_path=catalog_path,
        catalog_sha256=f"sha256:{_file_sha256(catalog_path)}",
        source_summary_path=source_result.summary_path,
        symbol_payloads=symbol_payloads,
        provider_states=provider_states,
    )


def historical_data_provider_states(
    *,
    source_summary_path: Path | None = None,
    active_symbol_count: int = 0,
) -> dict[str, dict[str, Any]]:
    archive_descriptors = {descriptor.source_name: descriptor for descriptor in archive_source_descriptors()}
    capabilities_by_source: dict[str, list[dict[str, Any]]] = {}
    for capability in data_provider_capabilities():
        capabilities_by_source.setdefault(capability.source_name, []).append(capability.to_payload())

    states: dict[str, dict[str, Any]] = {}
    for descriptor in data_source_descriptors():
        archive_descriptor = archive_descriptors.get(descriptor.source_name)
        state = _catalog_state_for_source(
            descriptor.source_name,
            active_symbol_count=active_symbol_count,
            source_summary_path=source_summary_path,
        )
        reference = PROVIDER_SOURCE_REFERENCES.get(descriptor.source_name, {})
        states[descriptor.source_name] = {
            "source_name": descriptor.source_name,
            "display_name": descriptor.display_name,
            "source_type": descriptor.source_type,
            "catalog_state": state["catalog_state"],
            "catalog_role": state["catalog_role"],
            "implemented_for_ingestion": descriptor.implemented_for_ingestion,
            "implemented_for_catalog_refresh": bool(state["implemented_for_catalog_refresh"]),
            "candidate_depth_eligible_now": bool(state["candidate_depth_eligible_now"]),
            "diagnostic_only_by_default": descriptor.diagnostic_only_by_default,
            "data_families": list(descriptor.data_families),
            "capabilities": sorted(
                capabilities_by_source.get(descriptor.source_name, []),
                key=lambda item: str(item.get("data_family") or ""),
            ),
            "notes": [*descriptor.notes, reference.get("operator_note", "")],
            "official_reference": reference.get("official_reference"),
            "archive_caveats": list(archive_descriptor.caveats) if archive_descriptor is not None else [],
            "limitations": state["limitations"],
            "required_next_steps": state["required_next_steps"],
            "source_summary_path": str(source_summary_path) if source_summary_path is not None and descriptor.source_name == "binance_vision" else None,
        }
    return states


def read_historical_data_catalog(path: Path | str) -> dict[str, Any]:
    catalog_path = Path(path).expanduser().resolve()
    payload = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("historical_data_catalog_must_be_json_object")
    if payload.get("historical_data_catalog_version") != HISTORICAL_DATA_CATALOG_VERSION:
        raise ValueError("historical_data_catalog_version_mismatch")
    normalized = normalize_operator_run_artifact_paths(payload, artifact_path=catalog_path, anchor_root=catalog_path.parent)
    if normalized != payload:
        portability = dict(normalized.get("path_portability") or {})
        portability.update(
            {
                "migrated_absolute_paths_rebased": True,
                "catalog_run_dir": str(catalog_path.parent),
            }
        )
        normalized["path_portability"] = portability
    return normalized


def normalize_operator_run_artifact_paths(
    payload: Mapping[str, Any],
    *,
    artifact_path: Path | str,
    anchor_root: Path | str | None = None,
) -> dict[str, Any]:
    """Rebase migrated operator-run paths when a mirrored path exists locally.

    Historical R106 artifacts can be copied between checkouts while preserving
    absolute paths from the original repo. This keeps generated artifacts
    immutable and fixes the handoff at read time.
    """

    if not isinstance(payload, Mapping):
        raise ValueError("operator_run_artifact_payload_must_be_mapping")
    resolved_artifact = Path(artifact_path).expanduser().resolve()
    context_dir = resolved_artifact if resolved_artifact.is_dir() else resolved_artifact.parent
    resolved_anchor = Path(anchor_root).expanduser().resolve() if anchor_root is not None else _operator_run_anchor_root(context_dir)
    normalized = _normalize_operator_run_node(
        dict(payload),
        key="",
        anchor_root=resolved_anchor,
        context_dir=context_dir,
    )
    return normalized if isinstance(normalized, dict) else dict(payload)


def _catalog_symbol_payload(
    symbol: str,
    payload: Mapping[str, Any],
    source_summary_path: Path,
) -> dict[str, Any]:
    candidate_depth_ready = bool(payload.get("candidate_depth_thresholds_met") is True)
    collection_ready = bool(payload.get("collection_thresholds_met") is True)
    status = "candidate_depth_ready" if candidate_depth_ready else "fixture_valid_below_candidate_depth_floor"
    if not collection_ready:
        status = "collection_threshold_blocked"
    return {
        "symbol": symbol,
        "status": status,
        "candidate_depth_ready": candidate_depth_ready,
        "fixture_valid": collection_ready,
        "source_name": "binance_vision",
        "source_summary_path": str(source_summary_path),
        "fixture_manifest_path": payload.get("fixture_manifest_path"),
        "fixture_manifest_sha256": payload.get("fixture_manifest_sha256"),
        "readiness_config_path": payload.get("readiness_config_path"),
        "cycle_spec_path": payload.get("cycle_spec_path"),
        "discovery_spec_path": payload.get("discovery_spec_path"),
        "cycle_id": payload.get("cycle_id"),
        "discovery_run_id": payload.get("discovery_run_id"),
        "modern_window_profile_count": int(payload.get("modern_window_profile_count") or 0),
        "modern_window_profiles": {
            str(profile_id): dict(profile)
            for profile_id, profile in (payload.get("modern_window_profiles") or {}).items()
            if isinstance(profile, Mapping)
        },
        "row_counts": dict(payload.get("row_counts") or {}),
        "effective_coverage_hours": payload.get("effective_coverage_hours"),
        "candidate_depth_thresholds_met": candidate_depth_ready,
        "candidate_depth_blockers": list(payload.get("candidate_depth_blockers") or []),
        "collection_thresholds_met": collection_ready,
        "download_count": payload.get("download_count"),
        "checksum_verified_count": payload.get("checksum_verified_count"),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _catalog_state_for_source(
    source_name: str,
    *,
    active_symbol_count: int,
    source_summary_path: Path | None,
) -> dict[str, Any]:
    if source_name == "binance_vision":
        return {
            "catalog_state": "active_implemented_primary" if source_summary_path is not None else "implemented_primary_not_refreshed",
            "catalog_role": "primary_public_archive_fixture_source",
            "implemented_for_catalog_refresh": True,
            "candidate_depth_eligible_now": source_summary_path is not None and active_symbol_count > 0,
            "limitations": [
                "receive_time_unavailable",
                "not_hyperliquid_fillability_evidence",
                "candidate gates still required after data readiness",
            ],
            "required_next_steps": [],
        }
    if source_name == "crypto_lake":
        return {
            "catalog_state": "implemented_local_export_not_auto_collected",
            "catalog_role": "optional_vendor_export_context_source",
            "implemented_for_catalog_refresh": False,
            "candidate_depth_eligible_now": False,
            "limitations": [
                "local_export_or_subscription_required",
                "free_sample_data_remains_diagnostic",
                "catalog refresh has no configured unattended export path",
            ],
            "required_next_steps": [
                "Provide local export manifests or configure a licensed lakeapi cache before adding it to active catalog data.",
            ],
        }
    if source_name == "bybit_archive":
        return {
            "catalog_state": "public_archive_registered_ingestion_not_implemented",
            "catalog_role": "future_cross_venue_public_history_source",
            "implemented_for_catalog_refresh": False,
            "candidate_depth_eligible_now": False,
            "limitations": [
                "downloader_parser_checksum_policy_not_implemented",
                "venue_mismatch_with_current_binance_fixture_contract",
                "receive_time_unavailable_for_live_like_latency_claims",
            ],
            "required_next_steps": [
                "Add a normalized Bybit archive downloader/parser and gap/duplicate/hash validation before active catalog use.",
            ],
        }
    if source_name == "hyperliquid_archive":
        return {
            "catalog_state": "archive_registered_requester_pays_ingestion_not_implemented",
            "catalog_role": "future_target_venue_market_and_account_history_source",
            "implemented_for_catalog_refresh": False,
            "candidate_depth_eligible_now": False,
            "limitations": [
                "requester_pays_transfer_costs",
                "official_docs_warn_data_may_be_missing_or_not_timely",
                "account_journal_reconciliation_required_for fill/order/position evidence",
            ],
            "required_next_steps": [
                "Configure AWS requester-pays access and implement LZ4 parser plus local account-journal reconciliation.",
            ],
        }
    return {
        "catalog_state": "implemented_secondary_not_catalog_primary",
        "catalog_role": "diagnostic_or_backfill_source",
        "implemented_for_catalog_refresh": False,
        "candidate_depth_eligible_now": False,
        "limitations": ["not_used_by_required_catalog_refresh"],
        "required_next_steps": [],
    }


def _source_policy() -> dict[str, Any]:
    return {
        "priority_order": [
            "validated_active_catalog_fixture_pack",
            "validated_local_vendor_exports_with_manifest",
            "registered_public_archives_after_parser_and_validation",
            "latest_window_rest_diagnostics",
        ],
        "merge_policy": [
            "Never merge rows across providers silently.",
            "Primary bars come from one validated fixture manifest per symbol until an explicit merge manifest exists.",
            "Context families may be additive only when event-time alignment, missingness, hashes, and provider capability metadata are recorded.",
        ],
        "readiness_policy": "candidate_depth_ready_requires_all_required_symbols_to_meet_global_1y_15m_and_1m_context_floors",
    }


def _canonical_format() -> dict[str, Any]:
    return {
        "catalog_manifest": "historical_data_catalog.json",
        "active_fixture_manifest": "fixture_pack_manifest.json",
        "active_readiness_manifest": "durable_public_archive_fixture_readiness_*_candidate_depth_v1.json",
        "required_families": ["bars:15m", "lower_timeframe_bars:1m", "agg_trade:1m_proxy"],
        "research_boundary": {
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        },
    }


def _intervention_required(provider_states: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    required: list[dict[str, Any]] = []
    for source_name, state in sorted(provider_states.items()):
        steps = [str(item) for item in state.get("required_next_steps") or [] if str(item).strip()]
        if steps:
            required.append(
                {
                    "source_name": source_name,
                    "catalog_state": state.get("catalog_state"),
                    "required_next_steps": steps,
                }
            )
    return required


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":") if indent is None else None,
        indent=indent,
        ensure_ascii=True,
        default=str,
    )


def _normalize_operator_run_node(
    value: Any,
    *,
    key: str,
    anchor_root: Path,
    context_dir: Path,
) -> Any:
    if isinstance(value, Mapping):
        return {
            str(child_key): _normalize_operator_run_node(
                child_value,
                key=str(child_key),
                anchor_root=anchor_root,
                context_dir=context_dir,
            )
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [
            _normalize_operator_run_node(
                item,
                key=key,
                anchor_root=anchor_root,
                context_dir=context_dir,
            )
            for item in value
        ]
    if isinstance(value, str):
        rebased = _rebase_operator_run_path(value, key=key, anchor_root=anchor_root, context_dir=context_dir)
        if rebased is not None:
            return str(rebased)
    return value


def _operator_run_anchor_root(context_dir: Path) -> Path:
    current = context_dir.resolve()
    for ancestor in (current, *current.parents):
        if ancestor.name.startswith("refresh-historical-data-catalog-"):
            return ancestor
    return current


def _operator_run_rebase_anchors(*, anchor_root: Path, context_dir: Path) -> list[Path]:
    root = anchor_root.resolve()
    current = context_dir.resolve()
    try:
        current.relative_to(root)
    except ValueError:
        return [root]
    anchors = [current]
    while anchors[-1] != root:
        anchors.append(anchors[-1].parent)
    return anchors


def _operator_run_repo_root(context_dir: Path) -> Path | None:
    current = context_dir.resolve()
    for ancestor in (current, *current.parents):
        if (ancestor / "pyproject.toml").is_file() and (ancestor / "src" / "tradingbotsuite").is_dir():
            return ancestor
    return None


def _rebase_operator_run_path(raw_path: str, *, key: str, anchor_root: Path, context_dir: Path) -> Path | None:
    text = raw_path.strip()
    if not text:
        return None
    candidate_parts = _absolute_path_parts(text)
    if not candidate_parts:
        return None
    anchors_by_name: dict[str, list[Path]] = {}
    for anchor in _operator_run_rebase_anchors(anchor_root=anchor_root, context_dir=context_dir):
        if anchor.name:
            anchors_by_name.setdefault(anchor.name.lower(), []).append(anchor)
    for index, part in enumerate(candidate_parts):
        for anchor in anchors_by_name.get(part.lower(), []):
            rebased = anchor.joinpath(*candidate_parts[index + 1 :]).resolve()
            if rebased.exists() or rebased.parent.exists():
                return rebased
    repo_root = _operator_run_repo_root(context_dir)
    if repo_root is not None:
        if key.strip().lower() in {"repo_root", "repository_root"}:
            return repo_root.resolve()
        for index, part in enumerate(candidate_parts):
            if part.lower() in {"configs", "data", "docs", "src", "tests"}:
                rebased = repo_root.joinpath(*candidate_parts[index:]).resolve()
                if rebased.exists() or rebased.parent.exists():
                    return rebased
    return None


def _absolute_path_parts(text: str) -> tuple[str, ...]:
    candidate = Path(text).expanduser()
    if candidate.is_absolute():
        return candidate.parts
    windows_candidate = PureWindowsPath(text)
    if windows_candidate.is_absolute():
        return windows_candidate.parts
    return ()
