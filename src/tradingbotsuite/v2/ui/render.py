# V2-AUDIT-ID: V2-AUD-UI-001
# V2-CONTRACTS: docs/contracts/ui_visibility_contract.md
# V2-BOUNDARY: research_only, read_only_visibility, no_live_imports
# V2-OWNER: v2_ui
"""Static HTML renderer for v2 visibility snapshots."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tradingbotsuite.v2.security.path_policy import resolve_within_root
from tradingbotsuite.v2.ui.schemas import (
    ArchiveCoverageRow,
    AuditChunkVisibilityRow,
    CollectionStatusRow,
    DeepValidationVisibilityRow,
    FinalHardTestVisibilityRow,
    GapReportRow,
    LeadBookVisibilityRow,
    UniverseVisibilityRow,
    V2VisibilitySnapshot,
    WorkerJobVisibilityRow,
)


SECTION_LABELS = (
    ("active_universe", "Active Universe"),
    ("collection_status", "Collection"),
    ("archive_coverage", "Coverage"),
    ("gap_reports", "Gaps"),
    ("lockbox", "Lockbox"),
    ("lead_book", "Lead Book"),
    ("deep_validation", "Deep Validation"),
    ("final_hard_tests", "Final Hard Tests"),
    ("audit_chunks", "Audit"),
    ("worker_jobs", "Workers"),
)


def render_visibility_html(snapshot: V2VisibilitySnapshot) -> str:
    counts = snapshot.section_counts()
    sections = [
        _summary_section(snapshot, counts),
        _table_section(
            "Active Universe",
            snapshot.active_universe,
            ("venue", "instrument", "included", "reason", "notional", "scope", "caveats"),
            _universe_cells,
        ),
        _table_section(
            "Collection",
            snapshot.collection_status,
            ("source", "datatype", "status", "latest event", "manifests", "gaps", "notes"),
            _collection_cells,
        ),
        _table_section(
            "Coverage",
            snapshot.archive_coverage,
            ("venue", "instrument", "family", "timeframe", "window", "coverage", "status", "missing days"),
            _coverage_cells,
        ),
        _table_section(
            "Gaps",
            snapshot.gap_reports,
            ("report", "venue", "instrument", "family", "timeframe", "count", "severity", "sample"),
            _gap_cells,
        ),
        _lockbox_section(snapshot),
        _table_section(
            "Lead Book",
            snapshot.lead_book,
            ("lead", "family", "state", "inspection", "approval", "promotion", "blockers"),
            _lead_cells,
        ),
        _table_section(
            "Deep Validation",
            snapshot.deep_validation,
            ("lead", "status", "active", "scorecard", "blockers"),
            _deep_validation_cells,
        ),
        _table_section(
            "Final Hard Tests",
            snapshot.final_hard_tests,
            ("slot", "lead", "status", "frozen evidence", "disclaimer"),
            _final_test_cells,
        ),
        _table_section(
            "Audit",
            snapshot.audit_chunks,
            ("audit", "area", "status", "purpose", "evidence"),
            _audit_cells,
        ),
        _table_section(
            "Workers",
            snapshot.worker_jobs,
            ("job", "kind", "status", "terminal", "attempts", "manifests", "failure"),
            _worker_cells,
        ),
        _notes_section(snapshot.notes),
    ]
    body = "\n".join(section for section in sections if section)
    return _html_document(snapshot.title, body)


def write_visibility_html(
    snapshot: V2VisibilitySnapshot,
    *,
    output_root: str | Path,
    output_path: str | Path,
) -> Path:
    resolved = resolve_within_root(output_root, output_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(render_visibility_html(snapshot), encoding="utf-8")
    return resolved


def _html_document(title: str, body: str) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(title)}</title>",
            "<style>",
            _stylesheet(),
            "</style>",
            "</head>",
            "<body>",
            body,
            "</body>",
            "</html>",
            "",
        ]
    )


def _summary_section(snapshot: V2VisibilitySnapshot, counts: dict[str, int]) -> str:
    chips = "\n".join(
        f'<span class="metric"><span>{escape(label)}</span><strong>{counts[key]}</strong></span>'
        for key, label in SECTION_LABELS
    )
    return f"""
<header class="topbar">
  <div>
    <p class="eyebrow">research-only visibility</p>
    <h1>{escape(snapshot.title)}</h1>
    <p class="meta">Snapshot {escape(snapshot.snapshot_id)} - {escape(_format_dt(snapshot.generated_at))}</p>
  </div>
  <div class="boundary">
    <span>read-only</span>
    <span>observe-only</span>
    <span>promotion false</span>
  </div>
</header>
<section class="summary" aria-label="Snapshot summary">
{chips}
</section>
"""


def _table_section(
    title: str,
    rows: Sequence[BaseModel],
    headers: Sequence[str],
    cell_builder,
) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    if not rows:
        body = f'<tr><td colspan="{len(headers)}" class="empty">No rows</td></tr>'
    else:
        body = "\n".join(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in cell_builder(row)) + "</tr>"
            for row in rows
        )
    return f"""
<section class="panel" aria-labelledby="{_anchor(title)}">
  <h2 id="{_anchor(title)}">{escape(title)}</h2>
  <div class="table-wrap">
    <table>
      <thead><tr>{head}</tr></thead>
      <tbody>
{body}
      </tbody>
    </table>
  </div>
</section>
"""


def _lockbox_section(snapshot: V2VisibilitySnapshot) -> str:
    lockbox = snapshot.lockbox
    if lockbox is None:
        rows = '<tr><td colspan="5" class="empty">No lockbox row</td></tr>'
    else:
        rows = (
            "<tr>"
            f"<td>{escape(lockbox.policy_id)}</td>"
            f"<td>{escape(_format_dt(lockbox.start_ts))}</td>"
            f"<td>{escape(_format_dt(lockbox.end_ts))}</td>"
            f"<td>{_bool_badge(lockbox.excluded_from_tuning)}</td>"
            f"<td>{escape(lockbox.notes)}</td>"
            "</tr>"
        )
    return f"""
<section class="panel" aria-labelledby="lockbox">
  <h2 id="lockbox">Lockbox</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>policy</th><th>start</th><th>end</th><th>excluded</th><th>notes</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</section>
"""


def _notes_section(notes: Sequence[str]) -> str:
    if not notes:
        return ""
    items = "\n".join(f"<li>{escape(note)}</li>" for note in notes)
    return f"""
<section class="panel notes" aria-labelledby="notes">
  <h2 id="notes">Notes</h2>
  <ul>{items}</ul>
</section>
"""


def _universe_cells(row: UniverseVisibilityRow) -> tuple[str, ...]:
    return (
        escape(row.venue),
        escape(row.instrument_id),
        _bool_badge(row.included),
        escape(row.reason),
        "" if row.day_notional_usd is None else escape(f"{row.day_notional_usd:,.0f}"),
        escape(row.evidence_scope),
        _join(row.caveats),
    )


def _collection_cells(row: CollectionStatusRow) -> tuple[str, ...]:
    return (
        escape(row.source),
        escape(row.datatype),
        _status(row.status),
        escape(_format_dt(row.latest_event_ts)),
        _join(row.manifest_refs),
        escape(str(row.gap_count)),
        escape(row.notes),
    )


def _coverage_cells(row: ArchiveCoverageRow) -> tuple[str, ...]:
    return (
        escape(row.venue),
        escape(row.instrument_id),
        escape(row.family),
        escape(row.timeframe),
        escape(f"{_format_dt(row.start_ts)} to {_format_dt(row.end_ts)}"),
        escape(f"{row.coverage_ratio:.4f}"),
        _status(row.status),
        _join(row.missing_days),
    )


def _gap_cells(row: GapReportRow) -> tuple[str, ...]:
    return (
        escape(row.report_id),
        escape(row.venue),
        escape(row.instrument_id),
        escape(row.family),
        escape(row.timeframe),
        escape(str(row.gap_count)),
        _status(row.severity),
        _join(row.sample),
    )


def _lead_cells(row: LeadBookVisibilityRow) -> tuple[str, ...]:
    return (
        escape(row.lead_id),
        escape(row.strategy_family),
        _status(row.state),
        _status(row.human_inspection_status),
        _status(row.agent_approval_status),
        _bool_badge(row.promotion_ready),
        _join(row.blocker_reasons),
    )


def _deep_validation_cells(row: DeepValidationVisibilityRow) -> tuple[str, ...]:
    return (
        escape(row.lead_id),
        _status(row.status),
        _bool_badge(row.active),
        _status(row.scorecard_status),
        _join(row.blocker_reasons),
    )


def _final_test_cells(row: FinalHardTestVisibilityRow) -> tuple[str, ...]:
    return (
        escape(row.slot_id),
        escape(row.lead_id),
        _status(row.status),
        _bool_badge(row.frozen_evidence),
        escape(row.non_live_disclaimer),
    )


def _audit_cells(row: AuditChunkVisibilityRow) -> tuple[str, ...]:
    return (
        escape(row.audit_id),
        escape(row.area),
        _status(row.status),
        escape(row.purpose),
        escape(row.evidence),
    )


def _worker_cells(row: WorkerJobVisibilityRow) -> tuple[str, ...]:
    return (
        escape(row.job_id),
        escape(row.kind),
        _status(row.status),
        _bool_badge(row.terminal_state),
        escape(str(row.attempts)),
        _join(row.archive_manifest_refs),
        escape(row.failure_reason),
    )


def _status(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-") or "unknown"
    return f'<span class="status status-{escape(normalized)}">{escape(value)}</span>'


def _bool_badge(value: bool) -> str:
    label = "true" if value else "false"
    class_name = "yes" if value else "no"
    return f'<span class="badge {class_name}">{label}</span>'


def _join(values: Iterable[Any]) -> str:
    text = ", ".join(str(value) for value in values if str(value))
    return escape(text)


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _anchor(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def _stylesheet() -> str:
    return """
:root {
  color-scheme: light;
  --bg: #f5f7f8;
  --panel: #ffffff;
  --ink: #182026;
  --muted: #5d6a72;
  --line: #d9e0e4;
  --accent: #0f766e;
  --warn: #a16207;
  --bad: #b42318;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 14px/1.45 Arial, Helvetica, sans-serif;
}
.topbar {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 28px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--panel);
}
.eyebrow {
  margin: 0 0 4px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0;
}
h2 {
  margin: 0 0 12px;
  font-size: 18px;
  letter-spacing: 0;
}
.meta { margin: 6px 0 0; color: var(--muted); }
.boundary {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  justify-content: flex-end;
  gap: 8px;
  max-width: 360px;
}
.boundary span, .metric, .badge, .status {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #f8fafb;
}
.boundary span {
  padding: 6px 10px;
  color: var(--muted);
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  padding: 16px 28px;
}
.metric {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  padding: 10px 12px;
}
.metric span { color: var(--muted); }
.metric strong { font-size: 20px; }
.panel {
  margin: 12px 28px;
  padding: 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.table-wrap { overflow-x: auto; }
table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}
th, td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.empty { color: var(--muted); text-align: center; }
.badge, .status {
  display: inline-block;
  padding: 2px 7px;
  white-space: nowrap;
}
.yes { color: var(--accent); }
.no, .status-fail, .status-blocked, .status-rejected { color: var(--bad); }
.status-warn, .status-warning { color: var(--warn); }
.notes ul { margin: 0; padding-left: 20px; }
@media (max-width: 720px) {
  .topbar { display: block; padding: 18px; }
  .boundary { justify-content: flex-start; margin-top: 12px; }
  .summary { padding: 12px 18px; }
  .panel { margin: 10px 18px; padding: 12px; }
  h1 { font-size: 22px; }
}
"""
