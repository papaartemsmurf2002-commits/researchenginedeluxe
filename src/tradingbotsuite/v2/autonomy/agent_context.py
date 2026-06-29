# V2-AUDIT-ID: V2-AUD-AUTONOMY-019
# V2-CONTRACTS: docs/contracts/autonomous_research_agent_context_contract.md
# V2-BOUNDARY: research_only, read_only_agent_context, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_autonomy
"""Read-only autonomous research agent context snapshot."""

from __future__ import annotations

from datetime import date, datetime
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.config.time import ensure_utc, utc_now
from tradingbotsuite.v2.security.boundary import require_research_boundary

AUTONOMOUS_RESEARCH_AGENT_CONTEXT_SCHEMA_VERSION = "autonomous_research_agent_context_v1"

PROJECT_BAR_REPORT = Path(
    "data/research/central_market_history/manifests/"
    "wpr106-546-project-needed-1m-current-lifecycle-validation-report.json"
)
CENTRAL_COLLECTION_LEDGER = Path(
    "data/research/central_market_history/manifests/"
    "wpr106-544-central-market-history-exhaustive-coverage-v2-collection_ledger-ef0cfdcda209.json"
)
CENTRAL_OF_STYLE_STATUS_REPORT = Path(
    "data/research/central_market_history/manifests/"
    "wpr106-549-of-style-overall-status-report.json"
)
OF_STYLE_MATERIALIZATION_REPORT = Path(
    "data/research/of_style_feature_materialization/wpr106_552/manifests/"
    "wpr106-552-of-style-feature-materialization-report.json"
)
AUTONOMOUS_READINESS_REPORT = Path(
    "data/research/wpr106_556_autonomous_readiness/autonomous_readiness_report.json"
)
DATA_CATALOG_DOC = Path("docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md")
PRODUCT_SCOPE_DOC = Path("docs/PRODUCT_SCOPE.md")
KNOWN_ISSUES_DOC = Path("docs/KNOWN_ISSUES.md")
EXTERNAL_OF_STYLE_ARCHIVE_REPORT = Path(
    r"M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\manifests"
    r"\wpr106-549-heavy-raw-archive-validation-report.json"
)

PROJECT_SYMBOLS: tuple[str, ...] = (
    "AAVE",
    "ADA",
    "AERO",
    "AVAX",
    "BNB",
    "BTC",
    "DOGE",
    "ENA",
    "ETH",
    "FARTCOIN",
    "HYPE",
    "IP",
    "JTO",
    "JUP",
    "KPEPE",
    "LINK",
    "LIT",
    "NEAR",
    "PUMP",
    "SOL",
    "SUI",
    "TAO",
    "UNI",
    "VVV",
    "WLD",
    "XMR",
    "XPL",
    "XRP",
    "ZEC",
)

FALLBACK_BINANCE_SYMBOLS: dict[str, str] = {
    "KPEPE": "1000PEPEUSDT",
    "XPL": "XPLUSDT",
}

_SECRET_NAME_RE = re.compile(
    r"(^\.env($|\.)|secret|credential|password|private|api[-_]?key|token|wallet)",
    re.IGNORECASE,
)


class AgentContextReportRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1)
    path: str = Field(min_length=1)
    repo_relative_path: str | None = None
    exists: bool
    status: str = Field(min_length=1)
    use: str = Field(min_length=1)
    facts: dict[str, Any] = Field(default_factory=dict)
    blockers: tuple[str, ...] = ()


class AgentInstrumentContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1)
    hyperliquid_instrument_id: str = Field(min_length=1)
    binance_usdm_symbol: str = Field(min_length=1)
    binance_instrument_id: str = Field(min_length=1)
    bar_1m_status: str = Field(min_length=1)
    backtest_usable: bool = False
    first_collected_month: str | None = None
    last_collected_month: str | None = None
    exact_lifecycle_start: str | None = None
    manifest_count: int = Field(default=0, ge=0)
    notes: tuple[str, ...] = ()


class AgentDataLane(BaseModel):
    model_config = ConfigDict(frozen=True)

    lane_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    source_access_mode: str = Field(min_length=1)
    primary_path: str = Field(min_length=1)
    authority_report_label: str = Field(min_length=1)
    allowed_uses: tuple[str, ...] = Field(min_length=1)
    blocked_uses: tuple[str, ...] = Field(min_length=1)
    next_action: str = Field(min_length=1)


class AgentCollectionRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(min_length=1)
    allowed: bool
    summary: str = Field(min_length=1)
    required_handling: tuple[str, ...] = Field(min_length=1)


class AgentSelfRepairPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    minor_fix_allowed: tuple[str, ...] = Field(min_length=1)
    must_open_or_update_work_packet: tuple[str, ...] = Field(min_length=1)
    must_escalate_or_record_issue: tuple[str, ...] = Field(min_length=1)


class AutonomousResearchAgentContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(
        default=AUTONOMOUS_RESEARCH_AGENT_CONTEXT_SCHEMA_VERSION,
        pattern=f"^{AUTONOMOUS_RESEARCH_AGENT_CONTEXT_SCHEMA_VERSION}$",
    )
    context_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    created_at: datetime
    repo_root: str = Field(min_length=1)
    manager_readiness_status: str = Field(min_length=1)
    autonomous_research_ready: bool
    candidate_or_live_ready: bool = False
    current_work_packet_required: bool = True
    latest_full_calendar_month: str = Field(min_length=7, max_length=7)
    dynamic_lockbox_month: str = Field(min_length=7, max_length=7)
    ordinary_iteration_end_exclusive: str = Field(min_length=1)
    project_symbol_count: int = Field(ge=0)
    project_symbols: tuple[str, ...]
    instruments: tuple[AgentInstrumentContext, ...]
    report_refs: tuple[AgentContextReportRef, ...]
    data_lanes: tuple[AgentDataLane, ...]
    no_paid_public_collection_rules: tuple[AgentCollectionRule, ...]
    self_repair_policy: AgentSelfRepairPolicy
    first_files_to_read: tuple[str, ...]
    research_loop_entrypoints: tuple[str, ...]
    command_hints: tuple[str, ...]
    boundary_flags: dict[str, bool] = Field(default_factory=lambda: dict(RESEARCH_BOUNDARY))
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

    @field_validator("created_at")
    @classmethod
    def _utc_created_at(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_boundary(self) -> "AutonomousResearchAgentContext":
        if self.candidate_or_live_ready:
            raise ValueError("agent context cannot mark candidate_or_live_ready")
        require_research_boundary(self, context="autonomous research agent context")
        return self


def build_autonomous_research_agent_context(
    *,
    repo_root: str | Path = ".",
    run_id: str = "autonomous-research-agent-context",
    asof_date: date | None = None,
) -> AutonomousResearchAgentContext:
    root = Path(repo_root).resolve(strict=False)
    effective_date = asof_date or date.today()
    lockbox_month, iteration_end = _lockbox_month(effective_date)
    project_report_payload = _read_json_if_present(root / PROJECT_BAR_REPORT)
    materialization_payload = _read_json_if_present(root / OF_STYLE_MATERIALIZATION_REPORT)
    readiness_payload = _read_json_if_present(root / AUTONOMOUS_READINESS_REPORT)

    instruments = _instrument_contexts(project_report_payload)
    report_refs = _report_refs(
        root=root,
        project_report_payload=project_report_payload,
        materialization_payload=materialization_payload,
        readiness_payload=readiness_payload,
    )
    data_lanes = _data_lanes(root=root, report_refs=report_refs)
    manager_status = str(readiness_payload.get("status") or "readiness_report_missing")
    autonomous_ready = (
        readiness_payload.get("status") == "autonomous_research_ready"
        and readiness_payload.get("autonomous_research_ready") is True
        and int(readiness_payload.get("blocker_count") or 0) == 0
    )
    identity = {
        "schema_version": AUTONOMOUS_RESEARCH_AGENT_CONTEXT_SCHEMA_VERSION,
        "run_id": run_id,
        "repo_root": str(root),
        "manager_readiness_status": manager_status,
        "autonomous_research_ready": autonomous_ready,
        "latest_full_calendar_month": lockbox_month,
        "project_symbols": [instrument.symbol for instrument in instruments],
        "report_refs": [ref.model_dump(mode="json") for ref in report_refs],
        "data_lanes": [lane.model_dump(mode="json") for lane in data_lanes],
    }
    return AutonomousResearchAgentContext(
        context_id=canonical_json_hash(identity),
        run_id=run_id,
        created_at=utc_now(),
        repo_root=str(root),
        manager_readiness_status=manager_status,
        autonomous_research_ready=autonomous_ready,
        latest_full_calendar_month=lockbox_month,
        dynamic_lockbox_month=lockbox_month,
        ordinary_iteration_end_exclusive=iteration_end,
        project_symbol_count=len(instruments),
        project_symbols=tuple(instrument.symbol for instrument in instruments),
        instruments=instruments,
        report_refs=report_refs,
        data_lanes=data_lanes,
        no_paid_public_collection_rules=_collection_rules(),
        self_repair_policy=_self_repair_policy(),
        first_files_to_read=(
            "AGENTS.md",
            "docs/RESEARCH_AGENT_QUICKSTART.md",
            "docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md",
            "docs/PRODUCT_SCOPE.md",
            "docs/KNOWN_ISSUES.md",
        ),
        research_loop_entrypoints=(
            "Use WPR106-546 project 1m bars for bar-only multi-instrument research when the requested window is manifest-covered and outside the dynamic lockbox.",
            "Use WPR106-544 collection ledger before any strategy requires a symbol, data family, or window.",
            "Use WPR106-552 OF-style materialized features only for manifest-covered proof-pack windows; open a compute materialization packet for wider OF/L2/trade windows.",
            "Use archive-ref bounded cycles for real local evidence; fixture/public-current cycles are diagnostics only.",
            "Log failed gates and skipped data families as evidence instead of substituting bars for missing OF/L2/trade inputs.",
        ),
        command_hints=(
            "python -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .",
            "python -m tradingbotsuite.v2.cli.main strategy-spec validate --spec-file <spec.json>",
            "python -m tradingbotsuite.v2.cli.main autopilot archive-cycle-spec --help",
            "python -m tradingbotsuite.v2.cli.main autopilot research-cycle --help",
            "python -m tradingbotsuite.v2.cli.main audit autonomous-readiness --help",
        ),
    )


def write_autonomous_research_agent_context(
    context: AutonomousResearchAgentContext,
    output_path: str | Path,
) -> Path:
    path = _validate_output_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_to_json(context.model_dump(mode="json")), encoding="utf-8")
    return path


def agent_context_to_json(context: AutonomousResearchAgentContext) -> str:
    return _to_json(context.model_dump(mode="json"))


def _instrument_contexts(payload: dict[str, Any]) -> tuple[AgentInstrumentContext, ...]:
    rows = payload.get("project_rows")
    if isinstance(rows, list) and rows:
        by_symbol = {
            str(row.get("symbol") or row.get("ledger_symbol")): row
            for row in rows
            if isinstance(row, dict) and (row.get("symbol") or row.get("ledger_symbol"))
        }
        symbols = tuple(symbol for symbol in PROJECT_SYMBOLS if symbol in by_symbol) or tuple(sorted(by_symbol))
        return tuple(_instrument_from_report_row(symbol, by_symbol[symbol]) for symbol in symbols)
    return tuple(_fallback_instrument(symbol) for symbol in PROJECT_SYMBOLS)


def _instrument_from_report_row(symbol: str, row: dict[str, Any]) -> AgentInstrumentContext:
    venue_symbol = str(row.get("venue_symbol") or _fallback_binance_symbol(symbol))
    backtest_usable = bool(row.get("backtest_usable"))
    notes: list[str] = []
    if row.get("strategy_must_call_off_if_required"):
        notes.append("strategy_must_call_off_if_required")
    if row.get("verification_failures"):
        notes.append("verification_failures_present")
    if symbol == "LIT":
        notes.append("lifecycle_scoped_current_lighter_protocol_contract")
    return AgentInstrumentContext(
        symbol=symbol,
        hyperliquid_instrument_id=f"hyperliquid:perp:{symbol}",
        binance_usdm_symbol=venue_symbol,
        binance_instrument_id=f"binance:perp:{venue_symbol}",
        bar_1m_status="ready" if backtest_usable else "blocked",
        backtest_usable=backtest_usable,
        first_collected_month=_optional_str(row.get("first_collected_month")),
        last_collected_month=_optional_str(row.get("last_collected_month")),
        exact_lifecycle_start=_optional_str(row.get("exact_lifecycle_start")),
        manifest_count=int(row.get("manifest_count") or 0),
        notes=tuple(notes),
    )


def _fallback_instrument(symbol: str) -> AgentInstrumentContext:
    venue_symbol = _fallback_binance_symbol(symbol)
    return AgentInstrumentContext(
        symbol=symbol,
        hyperliquid_instrument_id=f"hyperliquid:perp:{symbol}",
        binance_usdm_symbol=venue_symbol,
        binance_instrument_id=f"binance:perp:{venue_symbol}",
        bar_1m_status="report_missing",
        backtest_usable=False,
        notes=("consult_wpr106_546_report_before_running",),
    )


def _fallback_binance_symbol(symbol: str) -> str:
    return FALLBACK_BINANCE_SYMBOLS.get(symbol, f"{symbol}USDT")


def _report_refs(
    *,
    root: Path,
    project_report_payload: dict[str, Any],
    materialization_payload: dict[str, Any],
    readiness_payload: dict[str, Any],
) -> tuple[AgentContextReportRef, ...]:
    external_archive_payload = _read_json_if_present(EXTERNAL_OF_STYLE_ARCHIVE_REPORT)
    return (
        _report_ref(
            root,
            PROJECT_BAR_REPORT,
            label="wpr106_546_project_1m_bar_validation",
            use="Authoritative project-symbol 1m bar coverage and lifecycle truth.",
            payload=project_report_payload,
            status="ready"
            if project_report_payload.get("all_project_symbols_backtest_usable_1m") is True
            else "missing_or_not_ready",
            facts={
                "project_symbol_count": project_report_payload.get("project_symbol_count"),
                "verified_manifest_count": _nested_get(
                    project_report_payload,
                    "normalized_manifest_verification",
                    "verified_manifest_count",
                ),
                "verified_row_count": _nested_get(
                    project_report_payload,
                    "normalized_manifest_verification",
                    "verified_row_count",
                ),
                "partial_file_count": project_report_payload.get("partial_file_count"),
            },
        ),
        _report_ref(
            root,
            CENTRAL_COLLECTION_LEDGER,
            label="wpr106_544_central_collection_ledger",
            use="First-stop availability ledger for provider, family, symbol, and window decisions.",
            payload=_read_json_if_present(root / CENTRAL_COLLECTION_LEDGER),
            status="mixed_availability_truth_source",
        ),
        _report_ref(
            root,
            CENTRAL_OF_STYLE_STATUS_REPORT,
            label="wpr106_549_central_of_style_status",
            use="Central capped-store OF-style normalized coverage status.",
            payload=_read_json_if_present(root / CENTRAL_OF_STYLE_STATUS_REPORT),
            status="partial_by_design",
        ),
        _report_ref(
            root,
            EXTERNAL_OF_STYLE_ARCHIVE_REPORT,
            label="wpr106_549_external_of_style_raw_archive_validation",
            use="Raw-heavy official Binance USD-M OF-style source completeness authority.",
            payload=external_archive_payload,
            status="ready" if external_archive_payload else "external_authority_may_be_unmounted",
            facts={
                "source_files": external_archive_payload.get("source_files"),
                "complete_source_files": external_archive_payload.get("complete_source_files"),
                "missing_source_files": external_archive_payload.get("missing_source_files"),
                "invalid_source_files": external_archive_payload.get("invalid_source_files"),
                "partial_file_count": external_archive_payload.get("partial_file_count"),
            },
        ),
        _report_ref(
            root,
            OF_STYLE_MATERIALIZATION_REPORT,
            label="wpr106_552_of_style_feature_materialization",
            use="Compact per-symbol OF-style feature proof pack and materializer evidence.",
            payload=materialization_payload,
            status="ready"
            if materialization_payload.get("final_audit_data_ready") is True
            else "missing_or_not_ready",
            facts={
                "archive_source_count": materialization_payload.get("archive_source_count"),
                "materialized_source_count": materialization_payload.get("materialized_source_count"),
                "input_row_count": materialization_payload.get("input_row_count"),
                "feature_row_count": materialization_payload.get("feature_row_count"),
                "blocked_source_count": materialization_payload.get("blocked_source_count"),
            },
        ),
        _report_ref(
            root,
            AUTONOMOUS_READINESS_REPORT,
            label="wpr106_556_autonomous_readiness_report",
            use="Manager-level autonomous research readiness gate output.",
            payload=readiness_payload,
            status=str(readiness_payload.get("status") or "missing"),
            facts={
                "autonomous_research_ready": readiness_payload.get("autonomous_research_ready"),
                "blocker_count": readiness_payload.get("blocker_count"),
                "report_id": readiness_payload.get("report_id"),
            },
        ),
        _report_ref(
            root,
            DATA_CATALOG_DOC,
            label="v2_data_catalog_handoff_doc",
            use="Human-readable data and agentic research handoff.",
            payload={},
            status="doc",
        ),
        _report_ref(
            root,
            PRODUCT_SCOPE_DOC,
            label="product_scope",
            use="Research-only scope and forbidden-claim authority.",
            payload={},
            status="doc",
        ),
        _report_ref(
            root,
            KNOWN_ISSUES_DOC,
            label="known_issues",
            use="Open blocker source for P0/P1 stage gates.",
            payload={},
            status="doc",
        ),
    )


def _report_ref(
    root: Path,
    path: Path,
    *,
    label: str,
    use: str,
    payload: dict[str, Any],
    status: str,
    facts: dict[str, Any] | None = None,
) -> AgentContextReportRef:
    resolved = path if path.is_absolute() else (root / path).resolve(strict=False)
    exists = resolved.exists()
    blockers: list[str] = []
    if not exists and status not in {"external_authority_may_be_unmounted"}:
        blockers.append("report_missing")
    payload_blockers = payload.get("blocker_reasons")
    if isinstance(payload_blockers, list):
        blockers.extend(str(item) for item in payload_blockers if item)
    return AgentContextReportRef(
        label=label,
        path=str(resolved),
        repo_relative_path=None if path.is_absolute() else path.as_posix(),
        exists=exists,
        status=status if exists or payload else "missing",
        use=use,
        facts={key: value for key, value in (facts or {}).items() if value is not None},
        blockers=tuple(dict.fromkeys(blockers)),
    )


def _data_lanes(*, root: Path, report_refs: tuple[AgentContextReportRef, ...]) -> tuple[AgentDataLane, ...]:
    status_by_label = {ref.label: ref.status for ref in report_refs}
    return (
        AgentDataLane(
            lane_id="project_1m_bars_binance_usdm",
            status=status_by_label.get("wpr106_546_project_1m_bar_validation", "missing"),
            source_access_mode="official_public_no_paid_archive",
            primary_path=str((root / "data/research/central_market_history").resolve(strict=False)),
            authority_report_label="wpr106_546_project_1m_bar_validation",
            allowed_uses=(
                "bar_only_multi_instrument_research",
                "cross_sectional_ohlcv_features",
                "archive_ref_bounded_cycles_when_window_is_manifest_covered",
            ),
            blocked_uses=(
                "paper_live_signals",
                "candidate_pack_evidence_without_later_gate",
                "substitute_for_missing_l2_trade_or_orderflow_requirements",
            ),
            next_action="Use all manifest-covered project symbols instead of defaulting to BTC/ETH-only tests.",
        ),
        AgentDataLane(
            lane_id="central_collection_ledger",
            status=status_by_label.get("wpr106_544_central_collection_ledger", "missing"),
            source_access_mode="mixed_no_paid_provider_manifest_truth",
            primary_path=str((root / CENTRAL_COLLECTION_LEDGER).resolve(strict=False)),
            authority_report_label="wpr106_544_central_collection_ledger",
            allowed_uses=(
                "availability_preflight",
                "partial_window_restriction",
                "call_off_decisions_for_missing_budget_blocked_or_operator_gated_families",
            ),
            blocked_uses=("infer_coverage_from_raw_files_alone", "silently_substitute_incomplete_data"),
            next_action="Consult before any strategy requires specific symbols, families, or windows.",
        ),
        AgentDataLane(
            lane_id="external_of_style_raw_archive",
            status=status_by_label.get(
                "wpr106_549_external_of_style_raw_archive_validation",
                "external_authority_may_be_unmounted",
            ),
            source_access_mode="official_public_no_paid_external_raw_archive",
            primary_path=str(EXTERNAL_OF_STYLE_ARCHIVE_REPORT.parent.parent),
            authority_report_label="wpr106_549_external_of_style_raw_archive_validation",
            allowed_uses=(
                "raw_source_truth_for_of_style_materialization_packets",
                "source_completeness_audit",
            ),
            blocked_uses=(
                "direct_backtest_panel_without_materialization",
                "copy_into_central_store_without_budget_packet",
            ),
            next_action="Use WPR106-552 materializer or open a scoped compute packet for wider feature expansion.",
        ),
        AgentDataLane(
            lane_id="of_style_compact_feature_proof_pack",
            status=status_by_label.get("wpr106_552_of_style_feature_materialization", "missing"),
            source_access_mode="derived_from_official_public_no_paid_raw_archive",
            primary_path=str((root / "data/research/of_style_feature_materialization/wpr106_552").resolve(strict=False)),
            authority_report_label="wpr106_552_of_style_feature_materialization",
            allowed_uses=(
                "proof_that_available_of_style_schemas_parse",
                "manifest_covered_feature_experiments",
            ),
            blocked_uses=("claim_full_all_file_feature_panel_expansion", "candidate_or_live_readiness"),
            next_action="Open a compute/materialization packet when a strategy needs a wider OF-style window.",
        ),
        AgentDataLane(
            lane_id="hyperliquid_native_official_history",
            status="requester_pays_or_operator_gated_out_of_strict_free_scope",
            source_access_mode="not_available_under_current_no_paid_rule",
            primary_path="none",
            authority_report_label="product_scope_and_wpr106_551_policy",
            allowed_uses=("provenance_caveat",),
            blocked_uses=("strict_free_data_blocker", "silent_requirement_for_agentic_research"),
            next_action="Do not chase requester-pays native history unless the operator explicitly scopes a separate paid/gated packet.",
        ),
    )


def _collection_rules() -> tuple[AgentCollectionRule, ...]:
    return (
        AgentCollectionRule(
            rule_id="official_public_no_paid_archives",
            allowed=True,
            summary="Collect additional data only from official/public/no-paid sources that need no credentials or requester-pays access.",
            required_handling=(
                "write raw source before normalization",
                "record provider, URL or source ref, source access mode, checksums, row counts, coverage, and quality",
                "keep venue provenance instead of relabeling Binance/Bybit rows as Hyperliquid-native",
            ),
        ),
        AgentCollectionRule(
            rule_id="public_recent_or_current_apis",
            allowed=True,
            summary="Unsigned public APIs may be used for current or recent diagnostics when scoped.",
            required_handling=(
                "label current-universe or recent-window bias",
                "block accepted historical/as-of claims unless archive-backed evidence exists",
                "write blockers rather than fabricate missing windows",
            ),
        ),
        AgentCollectionRule(
            rule_id="paid_requester_pays_or_credentials",
            allowed=False,
            summary="Paid vendors, requester-pays buckets, private credentials, account APIs, and local secrets are outside the current lane.",
            required_handling=(
                "do not prompt for secrets in autonomous runs",
                "record as operator-gated or out-of-scope provenance",
                "continue with comparable no-paid sources when policy allows",
            ),
        ),
    )


def _self_repair_policy() -> AgentSelfRepairPolicy:
    return AgentSelfRepairPolicy(
        minor_fix_allowed=(
            "fix stale handoff wording or missing cross-reference inside the current work packet",
            "add or repair focused tests for changed read-only behavior",
            "retry interrupted validation or split around documented local Windows socket setup failures",
            "repair deterministic parser/schema handling when the contract and boundary stay unchanged",
            "skip untestable strategy inputs with explicit blocker evidence instead of proxying them",
        ),
        must_open_or_update_work_packet=(
            "open or update the active work packet before any scoped mutation",
            "any code change",
            "any new generated evidence path",
            "any data collection or materialization run",
            "any strategy spec, backtest, validation, ledger, or Lead Book mutation",
        ),
        must_escalate_or_record_issue=(
            "possible boundary violation or live/order/sizing/runtime behavior",
            "data corruption, checksum mismatch, or unexplained coverage gap in an accepted lane",
            "need for paid, requester-pays, credentialed, or operator-gated data",
            "major schema change, evidence rewrite, or candidate/promotion implication",
        ),
    )


def _lockbox_month(value: date) -> tuple[str, str]:
    first_this_month = date(value.year, value.month, 1)
    if value.month == 1:
        first_previous_month = date(value.year - 1, 12, 1)
    else:
        first_previous_month = date(value.year, value.month - 1, 1)
    return (
        first_previous_month.strftime("%Y-%m"),
        first_previous_month.isoformat() + "T00:00:00+00:00",
    )


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _nested_get(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_output_path(path_value: str | Path) -> Path:
    path = Path(path_value).resolve(strict=False)
    if path.suffix.lower() != ".json":
        raise ValueError("agent context output must be a .json file")
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise ValueError("agent context output path cannot be secret-like")
    return path


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
