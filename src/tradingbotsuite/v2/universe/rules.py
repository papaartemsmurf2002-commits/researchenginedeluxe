# V2-AUDIT-ID: V2-AUD-UNIV-001
# V2-CONTRACTS: docs/contracts/universe_contract.md
# V2-BOUNDARY: research_only, as_of_universe, no_live_imports
# V2-OWNER: v2_universe
"""Eligibility rules for v2 universe snapshots."""

from __future__ import annotations

from tradingbotsuite.v2.universe.models import InstrumentCatalogRow, UniverseMode

VOLUME_BELOW_THRESHOLD = "volume_below_threshold"
INSUFFICIENT_COVERAGE = "insufficient_coverage"
INSUFFICIENT_HISTORY = "insufficient_history"
INACTIVE_INSTRUMENT = "inactive_instrument"
MISSING_HIP3_METADATA = "missing_hip3_metadata"
CURRENT_UNIVERSE_SANDBOX_ONLY = "current_universe_sandbox_only"


def evidence_scope_for_mode(mode: UniverseMode) -> tuple[str, bool]:
    if mode == UniverseMode.AS_OF:
        return "accepted_research", True
    if mode == UniverseMode.CURRENT_LABELED_SANDBOX:
        return "current_sandbox_only", False
    return "static_fixture_only", False


def hip3_metadata_complete(instrument: InstrumentCatalogRow) -> bool:
    if not instrument.is_hip3_or_rwa:
        return True
    return all(
        (
            instrument.dex_namespace,
            instrument.reference_market,
            instrument.oracle_source,
            instrument.reference_session_calendar,
            instrument.weekend_behavior_documented is not None,
            instrument.listing_age_days is not None,
            instrument.proxy_data_available is not None,
        )
    )


def eligibility_reason(
    *,
    instrument: InstrumentCatalogRow,
    day_ntl_vlm_usd: float,
    min_day_notional_usd: int,
    coverage_ratio: float,
    coverage_min: float,
    usable_months: int,
    min_usable_months: int,
) -> str | None:
    if instrument.status in {"disabled", "delisted", "quarantine"}:
        return INACTIVE_INSTRUMENT
    if day_ntl_vlm_usd < min_day_notional_usd:
        return VOLUME_BELOW_THRESHOLD
    if coverage_ratio < coverage_min:
        return INSUFFICIENT_COVERAGE
    if usable_months < min_usable_months:
        return INSUFFICIENT_HISTORY
    if not hip3_metadata_complete(instrument):
        return MISSING_HIP3_METADATA
    return None
