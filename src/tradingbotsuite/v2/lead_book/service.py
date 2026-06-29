# V2-AUDIT-ID: V2-AUD-LEAD-001
# V2-CONTRACTS: docs/contracts/lead_book_contract.md
# V2-BOUNDARY: research_only, non_promotable_leads, generated_exports_only, no_live_imports
# V2-OWNER: v2_lead_book
"""Lead Book store, workflow transitions, and gate checks."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.lead_book.schemas import (
    AgentApprovalStatus,
    GateSeverity,
    HumanInspectionStatus,
    LeadBookRow,
    LeadGateResult,
    LeadBookScanConfig,
    LeadBookScanItem,
    LeadBookScanManifest,
    LeadBookScanResult,
    LeadState,
    MonthlyStabilitySummary,
    PnlConcentrationSummary,
    RoiProjectionConfidence,
    TradeCountSummary,
)

_SECRET_NAME_RE = re.compile(
    r"(^\.env$|secret|credential|private|token|password|wallet|api[_-]?key)",
    re.IGNORECASE,
)


class LeadBookError(ValueError):
    """Raised when a Lead Book operation is invalid."""


def create_lead_from_source(
    *,
    source_artifact_path: str | Path,
    source_type: str,
    strategy_family: str,
    economic_thesis: str,
    created_by_id: str,
    venue_scope: str = "hyperliquid",
    universe_scope: str = "as_of",
    instrument_scope: Iterable[str] = ("unknown",),
    data_window_start: datetime | None = None,
    data_window_end: datetime | None = None,
    data_source: str = "source_artifact",
    roi_observed: float,
    roi_projected: float,
    roi_projection_assumptions: str,
    why_interesting: str,
    trade_count_summary: TradeCountSummary | dict[str, Any],
    monthly_stability_summary: MonthlyStabilitySummary | dict[str, Any],
    pnl_concentration_summary: PnlConcentrationSummary | dict[str, Any],
    lead_id: str | None = None,
    created_by_type: str = "agent",
    cost_assumptions: str = "manifested_cost_model",
    funding_assumptions: str = "manifested_funding_model",
    slippage_assumptions: str = "manifested_slippage_model",
    fill_assumptions: str = "research_fill_assumptions_only",
    roi_projection_confidence: RoiProjectionConfidence = RoiProjectionConfidence.UNKNOWN,
    known_blockers: Iterable[str] = (),
    missing_evidence: Iterable[str] = (),
    required_next_validation: Iterable[str] = ("deep_validation",),
    notes: str = "",
) -> LeadBookRow:
    source_path = Path(source_artifact_path).resolve()
    if not source_path.exists():
        raise LeadBookError("lead_source_artifact_missing")
    start = data_window_start or datetime(2024, 1, 1, tzinfo=UTC)
    end = data_window_end or datetime(2024, 7, 1, tzinfo=UTC)
    lead = LeadBookRow(
        lead_id=lead_id or _lead_id(source_path, strategy_family, economic_thesis),
        created_at=utc_now(),
        created_by_type=created_by_type,
        created_by_id=created_by_id,
        source_type=source_type,
        source_artifact_path=str(source_path),
        source_artifact_sha256=file_sha256(source_path),
        strategy_family=strategy_family,
        economic_thesis=economic_thesis,
        venue_scope=venue_scope,
        universe_scope=universe_scope,
        instrument_scope=tuple(instrument_scope),
        data_window_start=start,
        data_window_end=end,
        data_source=data_source,
        cost_assumptions=cost_assumptions,
        funding_assumptions=funding_assumptions,
        slippage_assumptions=slippage_assumptions,
        fill_assumptions=fill_assumptions,
        headline_metrics={"roi_observed": roi_observed, "roi_projected": roi_projected},
        roi_observed=roi_observed,
        roi_projected=roi_projected,
        roi_projection_assumptions=roi_projection_assumptions,
        roi_projection_confidence=roi_projection_confidence,
        why_interesting=why_interesting,
        known_blockers=tuple(known_blockers),
        missing_evidence=tuple(missing_evidence),
        required_next_validation=tuple(required_next_validation),
        trade_count_summary=_trade_summary(trade_count_summary),
        monthly_stability_summary=_monthly_summary(monthly_stability_summary),
        pnl_concentration_summary=_pnl_summary(pnl_concentration_summary),
        notes=notes,
    )
    gate_result = evaluate_lead_gates(lead)
    if gate_result.failures:
        lead = lead.model_copy(
            update={
                "known_blockers": tuple(dict.fromkeys([*lead.known_blockers, *gate_result.failures])),
                "state": LeadState.DEEP_VALIDATION_REJECTED
                if "pre_2024_fallback_absent" in gate_result.failures
                else lead.state,
            }
        )
    if gate_result.warnings:
        lead = lead.model_copy(
            update={
                "known_blockers": tuple(dict.fromkeys([*lead.known_blockers, *gate_result.warnings])),
                "diminishing_returns_warning": lead.diminishing_returns_warning
                or "diminishing_returns_warning" in gate_result.warnings,
            }
        )
    return lead


class LeadBookStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def read(self) -> list[LeadBookRow]:
        if not self.path.exists():
            return []
        table = pq.read_table(self.path)
        return [LeadBookRow.model_validate(_normalize_lead_payload(row)) for row in table.to_pylist()]

    def upsert(self, lead: LeadBookRow) -> LeadBookRow:
        leads = [row for row in self.read() if row.lead_id != lead.lead_id]
        leads.append(lead)
        self._write(sorted(leads, key=lambda row: row.lead_id))
        return lead

    def get(self, lead_id: str) -> LeadBookRow:
        for lead in self.read():
            if lead.lead_id == lead_id:
                return lead
        raise LeadBookError(f"lead_not_found: {lead_id}")

    def list(self, *, state: LeadState | str | None = None) -> list[LeadBookRow]:
        leads = self.read()
        if state is None:
            return leads
        parsed = state if isinstance(state, LeadState) else LeadState(state)
        return [lead for lead in leads if lead.state == parsed]

    def export_csv(self, output_path: str | Path) -> Path:
        rows = self.read()
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = list(LeadBookRow.model_fields)
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                payload = row.model_dump(mode="json")
                for key, value in payload.items():
                    if isinstance(value, list | dict):
                        payload[key] = canonical_json_hash(value) if isinstance(value, dict) else ";".join(value)
                writer.writerow(payload)
        return output

    def _write(self, rows: list[LeadBookRow]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payloads = []
        for row in rows:
            payload = row.model_dump(mode="json")
            payload["headline_metrics"] = {
                str(key): str(value) for key, value in payload["headline_metrics"].items()
            }
            payloads.append(payload)
        table = pa.Table.from_pylist(
            payloads,
            schema=_lead_schema(),
        )
        pq.write_table(table, self.path, compression="zstd")


def request_human_inspection(lead: LeadBookRow) -> LeadBookRow:
    return lead.model_copy(
        update={
            "human_inspection_status": HumanInspectionStatus.REQUESTED,
            "state": LeadState.HUMAN_INSPECTION_REQUESTED,
        }
    )


def complete_human_inspection(
    lead: LeadBookRow,
    *,
    inspected_by: str,
    notes: str,
    inspected_at: datetime | None = None,
) -> LeadBookRow:
    return lead.model_copy(
        update={
            "human_inspection_status": HumanInspectionStatus.COMPLETED,
            "human_inspected_by": inspected_by,
            "human_inspected_at": inspected_at or utc_now(),
            "human_inspection_notes": notes,
            "state": LeadState.HUMAN_INSPECTION_COMPLETED,
        }
    )


def approve_after_human_inspection(
    lead: LeadBookRow,
    *,
    approving_agent_id: str,
    approved_at: datetime | None = None,
) -> LeadBookRow:
    if lead.human_inspection_status != HumanInspectionStatus.COMPLETED:
        raise LeadBookError("agent_approval_requires_human_inspection")
    return lead.model_copy(
        update={
            "agent_approval_status": AgentApprovalStatus.APPROVED_AFTER_HUMAN_INSPECTION,
            "approving_agent_id": approving_agent_id,
            "approved_at": approved_at or utc_now(),
            "state": LeadState.AGENT_APPROVED_AFTER_HUMAN_INSPECTION,
        }
    )


def request_deep_validation(lead: LeadBookRow) -> LeadBookRow:
    if lead.human_inspection_status != HumanInspectionStatus.COMPLETED:
        raise LeadBookError("deep_validation_requires_human_inspection_completed")
    if lead.agent_approval_status != AgentApprovalStatus.APPROVED_AFTER_HUMAN_INSPECTION:
        raise LeadBookError("deep_validation_requires_agent_approval_after_human_inspection")
    return lead.model_copy(update={"state": LeadState.DEEP_VALIDATION_REQUESTED})


def evaluate_lead_gates(lead: LeadBookRow) -> LeadGateResult:
    warnings: list[str] = []
    failures: list[str] = []
    usable_months = lead.monthly_stability_summary.usable_months
    avg_trades = _avg_trades_per_usable_month(
        total_trades=lead.trade_count_summary.total_trades,
        usable_months=usable_months,
        fallback=lead.trade_count_summary.avg_trades_per_month,
    )
    if avg_trades < 10.0:
        failures.append("minimum_ten_trades_per_usable_month_failed")
    if usable_months < 6:
        failures.append("minimum_six_usable_months_failed")
    if lead.monthly_stability_summary.losing_months_12m > 4:
        failures.append("max_four_losing_months_per_year_failed")
    top_share = lead.pnl_concentration_summary.top_2_trades_profit_share
    month_share = lead.pnl_concentration_summary.best_month_profit_share
    if top_share > 0.50:
        failures.append("top_2_trades_profit_share_failed")
    elif top_share > 0.35:
        warnings.append("top_2_trades_profit_share_warning")
    if month_share > 0.50:
        failures.append("best_month_profit_share_failed")
    elif month_share > 0.35:
        warnings.append("best_month_profit_share_warning")
    if lead.diminishing_returns_warning:
        warnings.append("diminishing_returns_warning")
    if lead.data_window_start.year < 2024 and not lead.monthly_stability_summary.pre_2024_fallback_label:
        failures.append("pre_2024_fallback_absent")
    status = GateSeverity.FAIL if failures else GateSeverity.WARNING if warnings else GateSeverity.PASS
    return LeadGateResult(
        lead_id=lead.lead_id,
        status=status,
        warnings=tuple(dict.fromkeys(warnings)),
        failures=tuple(dict.fromkeys(failures)),
        avg_trades_per_month=avg_trades,
        usable_months=usable_months,
    )


def _avg_trades_per_usable_month(
    *,
    total_trades: int,
    usable_months: int,
    fallback: float,
) -> float:
    if usable_months > 0 and total_trades > 0:
        return total_trades / usable_months
    return fallback


def scan_lead_book_queue(
    config: LeadBookScanConfig | dict[str, Any],
) -> LeadBookScanResult:
    parsed = config if isinstance(config, LeadBookScanConfig) else LeadBookScanConfig.model_validate(config)
    lead_book_path = Path(parsed.lead_book_path).resolve(strict=False)
    output_path = Path(parsed.output_path).resolve(strict=False)
    _validate_scan_path(lead_book_path, field_name="lead_book_path", suffix=".parquet")
    _validate_scan_path(output_path, field_name="output_path", suffix=".json")

    blockers: list[str] = []
    rows: list[LeadBookRow] = []
    lead_book_sha: str | None = None
    lead_book_exists = lead_book_path.exists()
    if lead_book_exists:
        if not lead_book_path.is_file():
            raise LeadBookError("lead_book_path_must_be_file")
        rows = LeadBookStore(lead_book_path).read()
        lead_book_sha = file_sha256(lead_book_path)
    else:
        blockers.append("lead_book_missing")

    requested_states = frozenset(parsed.states)
    matched_rows = [row for row in rows if row.state in requested_states]
    if not matched_rows:
        blockers.append("no_matching_lead_book_rows")
    returned_rows = matched_rows[: parsed.max_rows]
    if len(matched_rows) > parsed.max_rows:
        blockers.append("lead_book_scan_max_rows_exceeded")

    items = tuple(_scan_item(row) for row in returned_rows)
    blocker_reasons = tuple(sorted(dict.fromkeys(blockers)))
    manifest_payload = {
        "schema_version": "lead_book_scan_manifest_v1",
        "scan_id": "0" * 64,
        "lead_book_path": str(lead_book_path),
        "lead_book_exists": lead_book_exists,
        "lead_book_sha256": lead_book_sha,
        "output_path": str(output_path),
        "evidence_mode": "lead_book_queue_scan",
        "accepted_research_ready": False,
        "states": [state.value for state in parsed.states],
        "max_rows": parsed.max_rows,
        "total_lead_count": len(rows),
        "matched_count": len(matched_rows),
        "returned_count": len(items),
        "state_counts": _state_counts(rows),
        "matched_state_counts": _state_counts(matched_rows),
        "blocker_count": len(blocker_reasons),
        "blocker_reasons": blocker_reasons,
        "items": [item.model_dump(mode="json") for item in items],
        "boundary_flags": dict(RESEARCH_BOUNDARY),
        **dict(RESEARCH_BOUNDARY),
    }
    manifest_payload["scan_id"] = canonical_json_hash(
        {key: value for key, value in manifest_payload.items() if key != "scan_id"}
    )
    manifest = LeadBookScanManifest.model_validate(manifest_payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    return LeadBookScanResult(
        scan_manifest_path=str(output_path),
        scan_id=manifest.scan_id,
        states=manifest.states,
        total_lead_count=manifest.total_lead_count,
        matched_count=manifest.matched_count,
        returned_count=manifest.returned_count,
        blocker_reasons=manifest.blocker_reasons,
    )


def _lead_id(source_path: Path, strategy_family: str, thesis: str) -> str:
    digest = canonical_json_hash(
        {
            "source": str(source_path),
            "source_sha256": file_sha256(source_path),
            "strategy_family": strategy_family,
            "economic_thesis": thesis,
        }
    )
    return "LEAD-" + digest[:16]


def _scan_item(row: LeadBookRow) -> LeadBookScanItem:
    return LeadBookScanItem(
        lead_id=row.lead_id,
        state=row.state,
        strategy_family=row.strategy_family,
        source_type=row.source_type,
        source_artifact_path=row.source_artifact_path,
        source_artifact_sha256=row.source_artifact_sha256,
        human_inspection_status=row.human_inspection_status,
        agent_approval_status=row.agent_approval_status,
        roi_projection_is_not_claim=row.roi_projection_is_not_claim,
        promotion_ready=row.promotion_ready,
        candidate_evidence=row.candidate_evidence,
        known_blockers=row.known_blockers,
        missing_evidence=row.missing_evidence,
        required_next_validation=row.required_next_validation,
    )


def _state_counts(rows: Iterable[LeadBookRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.state.value] = counts.get(row.state.value, 0) + 1
    return dict(sorted(counts.items()))


def _validate_scan_path(path: Path, *, field_name: str, suffix: str) -> None:
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise LeadBookError(f"{field_name}_secret_like_path")
    if path.suffix.lower() != suffix:
        raise LeadBookError(f"{field_name}_must_use_{suffix}_suffix")


def _trade_summary(value: TradeCountSummary | dict[str, Any]) -> TradeCountSummary:
    return value if isinstance(value, TradeCountSummary) else TradeCountSummary.model_validate(value)


def _monthly_summary(value: MonthlyStabilitySummary | dict[str, Any]) -> MonthlyStabilitySummary:
    return (
        value
        if isinstance(value, MonthlyStabilitySummary)
        else MonthlyStabilitySummary.model_validate(value)
    )


def _pnl_summary(value: PnlConcentrationSummary | dict[str, Any]) -> PnlConcentrationSummary:
    return (
        value
        if isinstance(value, PnlConcentrationSummary)
        else PnlConcentrationSummary.model_validate(value)
    )


def _normalize_lead_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    metrics = normalized.get("headline_metrics")
    if isinstance(metrics, list):
        normalized["headline_metrics"] = {str(key): value for key, value in metrics}
    return normalized


def _lead_schema() -> pa.Schema:
    return pa.schema(
        [
            ("schema_version", pa.string()),
            ("lead_id", pa.string()),
            ("lead_version", pa.string()),
            ("created_at", pa.string()),
            ("created_by_type", pa.string()),
            ("created_by_id", pa.string()),
            ("source_type", pa.string()),
            ("source_artifact_path", pa.string()),
            ("source_artifact_sha256", pa.string()),
            ("strategy_family", pa.string()),
            ("economic_thesis", pa.string()),
            ("venue_scope", pa.string()),
            ("universe_scope", pa.string()),
            ("instrument_scope", pa.list_(pa.string())),
            ("hip3_or_rwa_flag", pa.bool_()),
            ("data_window_start", pa.string()),
            ("data_window_end", pa.string()),
            ("data_source", pa.string()),
            ("archive_snapshot_id", pa.string()),
            ("universe_snapshot_id", pa.string()),
            ("feature_snapshot_id", pa.string()),
            ("cost_assumptions", pa.string()),
            ("funding_assumptions", pa.string()),
            ("slippage_assumptions", pa.string()),
            ("fill_assumptions", pa.string()),
            ("headline_metrics", pa.map_(pa.string(), pa.string())),
            ("roi_observed", pa.float64()),
            ("roi_projected", pa.float64()),
            ("roi_projection_assumptions", pa.string()),
            ("roi_projection_confidence", pa.string()),
            ("roi_projection_is_not_claim", pa.bool_()),
            ("why_interesting", pa.string()),
            ("known_blockers", pa.list_(pa.string())),
            ("missing_evidence", pa.list_(pa.string())),
            ("required_next_validation", pa.list_(pa.string())),
            ("trade_count_summary", pa.struct([("avg_trades_per_month", pa.float64()), ("total_trades", pa.int64())])),
            ("monthly_stability_summary", pa.struct([
                ("usable_months", pa.int64()),
                ("losing_months_12m", pa.int64()),
                ("positive_months_12m", pa.int64()),
                ("pre_2024_fallback_label", pa.string()),
            ])),
            ("pnl_concentration_summary", pa.struct([
                ("top_2_trades_profit_share", pa.float64()),
                ("best_month_profit_share", pa.float64()),
            ])),
            ("diminishing_returns_warning", pa.bool_()),
            ("pre_2024_fallback_absent", pa.bool_()),
            ("human_inspection_status", pa.string()),
            ("human_inspected_by", pa.string()),
            ("human_inspected_at", pa.string()),
            ("human_inspection_notes", pa.string()),
            ("agent_approval_status", pa.string()),
            ("approving_agent_id", pa.string()),
            ("approved_at", pa.string()),
            ("state", pa.string()),
            ("non_promotable_flags", pa.list_(pa.string())),
            ("notes", pa.string()),
            ("research_only", pa.bool_()),
            ("observe_only", pa.bool_()),
            ("promotion_ready", pa.bool_()),
            ("candidate_evidence", pa.bool_()),
            ("candidate_pack_eligible", pa.bool_()),
            ("live_signal", pa.bool_()),
            ("paper_signal", pa.bool_()),
            ("sizing_instruction", pa.bool_()),
            ("order_placement_instruction", pa.bool_()),
            ("runtime_mode_change", pa.bool_()),
        ]
    )
