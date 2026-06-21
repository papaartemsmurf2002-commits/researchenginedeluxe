# V2-AUDIT-ID: V2-AUD-LEAD-001
# V2-CONTRACTS: docs/contracts/lead_book_contract.md
# V2-BOUNDARY: research_only, non_promotable_leads, generated_exports_only, no_live_imports
# V2-OWNER: v2_lead_book
"""Lead Book store, workflow transitions, and gate checks."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.lead_book.schemas import (
    AgentApprovalStatus,
    GateSeverity,
    HumanInspectionStatus,
    LeadBookRow,
    LeadGateResult,
    LeadState,
    MonthlyStabilitySummary,
    PnlConcentrationSummary,
    RoiProjectionConfidence,
    TradeCountSummary,
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
    avg_trades = lead.trade_count_summary.avg_trades_per_month
    usable_months = lead.monthly_stability_summary.usable_months
    if avg_trades < 5.0:
        failures.append("minimum_five_trades_per_month_failed")
    if usable_months < 6:
        failures.append("minimum_six_usable_months_failed")
    if lead.monthly_stability_summary.losing_months_12m >= 6:
        failures.append("six_losing_months_in_year_failed")
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
