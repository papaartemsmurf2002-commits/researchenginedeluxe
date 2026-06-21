from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.ui import (
    AuditChunkVisibilityRow,
    V2VisibilitySnapshot,
    render_visibility_html,
    write_visibility_html,
)
from tradingbotsuite.v2.ui.schemas import (
    ArchiveCoverageRow,
    CollectionStatusRow,
    DeepValidationVisibilityRow,
    FinalHardTestVisibilityRow,
    GapReportRow,
    LeadBookVisibilityRow,
    LockboxVisibility,
    UniverseVisibilityRow,
    WorkerJobVisibilityRow,
)


def test_visibility_snapshot_covers_phase22_sections() -> None:
    snapshot = _snapshot()

    assert snapshot.research_only is True
    assert snapshot.observe_only is True
    assert snapshot.promotion_ready is False
    assert snapshot.read_only is True
    assert snapshot.section_counts() == {
        "active_universe": 2,
        "collection_status": 1,
        "archive_coverage": 1,
        "gap_reports": 1,
        "lockbox": 1,
        "lead_book": 1,
        "deep_validation": 1,
        "final_hard_tests": 1,
        "audit_chunks": 1,
        "worker_jobs": 1,
    }


@pytest.mark.parametrize(
    "updates, reason",
    [
        ({"research_only": False}, "research_only_false"),
        ({"observe_only": False}, "observe_only_false"),
        ({"promotion_ready": True}, "promotion_ready_true"),
        ({"read_only": False}, "read_only_false"),
        ({"command_controls_enabled": True}, "command_controls_enabled"),
        ({"runtime_mutation_enabled": True}, "runtime_mutation_enabled"),
    ],
)
def test_visibility_snapshot_rejects_command_or_promotion_flags(
    updates: dict[str, object],
    reason: str,
) -> None:
    payload = _snapshot().model_dump(mode="json")
    payload.update(updates)

    with pytest.raises(ValidationError, match=reason):
        V2VisibilitySnapshot.model_validate(payload)


def test_visibility_rows_reject_promotable_leads_and_bad_lockbox() -> None:
    with pytest.raises(ValidationError, match="promotion_ready"):
        LeadBookVisibilityRow(
            lead_id="lead-1",
            strategy_family="example",
            state="idea_only",
            human_inspection_status="complete",
            agent_approval_status="approved",
            promotion_ready=True,
        )

    with pytest.raises(ValidationError, match="excluded from tuning"):
        LockboxVisibility(
            policy_id="lockbox",
            start_ts=_dt("2026-01-01T00:00:00+00:00"),
            end_ts=_dt("2026-02-01T00:00:00+00:00"),
            excluded_from_tuning=False,
        )


def test_rendered_html_is_static_read_only_and_escaped() -> None:
    snapshot = _snapshot(
        active_universe=(
            UniverseVisibilityRow(
                venue="hyperliquid",
                instrument_id="<script>alert(1)</script>",
                included=False,
                reason="below threshold",
                caveats=("HIP-3 <b>needs reference</b>",),
            ),
        )
    )

    html = render_visibility_html(snapshot)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script" not in html.lower()
    assert "<form" not in html.lower()
    assert "<button" not in html.lower()
    assert "onclick" not in html.lower()
    assert 'href="' not in html.lower()
    assert "Active Universe" in html
    assert "Final Hard Tests" in html
    assert "promotion false" in html


def test_write_visibility_html_respects_output_root(tmp_path) -> None:
    snapshot = _snapshot()
    output_root = tmp_path / "ui"

    written = write_visibility_html(
        snapshot,
        output_root=output_root,
        output_path="reports/v2.html",
    )

    assert written == output_root.resolve() / "reports" / "v2.html"
    assert "ResearchEngineDeluxe v2 Visibility" in written.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="escapes configured root"):
        write_visibility_html(
            snapshot,
            output_root=output_root,
            output_path="../escape.html",
        )


def test_cli_renders_supplied_snapshot_without_running_jobs(tmp_path, capsys) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    snapshot_path = input_root / "snapshot.json"
    snapshot_path.write_text(_snapshot().model_dump_json(), encoding="utf-8")

    result = main(
        [
            "ui",
            "render",
            "--input-root",
            str(input_root),
            "--snapshot-json",
            "snapshot.json",
            "--output-root",
            str(output_root),
            "--output-html",
            "dashboard/index.html",
        ]
    )
    captured = capsys.readouterr().out
    output_html = output_root / "dashboard" / "index.html"

    assert result == 0
    assert "read_only=true" in captured
    assert "promotion_ready=false" in captured
    assert output_html.exists()
    assert "worker-1" in output_html.read_text(encoding="utf-8")


def test_cli_rejects_snapshot_path_outside_input_root(tmp_path, capsys) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    (tmp_path / "snapshot.json").write_text(_snapshot().model_dump_json(), encoding="utf-8")

    result = main(
        [
            "ui",
            "render",
            "--input-root",
            str(input_root),
            "--snapshot-json",
            "../snapshot.json",
            "--output-root",
            str(output_root),
            "--output-html",
            "dashboard.html",
        ]
    )

    assert result == 1
    assert "ui_render_rejected=" in capsys.readouterr().out
    assert not (output_root / "dashboard.html").exists()


def test_audit_chunk_rows_are_visible() -> None:
    html = render_visibility_html(
        _snapshot(
            audit_chunks=(
                AuditChunkVisibilityRow(
                    audit_id="V2-AUD-UI-001",
                    area="ui",
                    status="self_checked",
                    purpose="read-only visibility",
                    evidence="focused tests passed",
                ),
            )
        )
    )

    assert "V2-AUD-UI-001" in html
    assert "read-only visibility" in html
    assert "focused tests passed" in html


def _snapshot(**updates) -> V2VisibilitySnapshot:
    payload = {
        "snapshot_id": "snapshot-1",
        "generated_at": _dt("2026-06-21T12:00:00+00:00"),
        "active_universe": (
            UniverseVisibilityRow(
                venue="hyperliquid",
                instrument_id="BTC",
                included=True,
                reason="above threshold",
                day_notional_usd=12_000_000,
                caveats=("reference",),
            ),
            UniverseVisibilityRow(
                venue="hyperliquid",
                instrument_id="HIP3:EXAMPLE",
                included=False,
                reason="missing RWA metadata",
                caveats=("HIP-3 caveat", "RWA reference required"),
            ),
        ),
        "collection_status": (
            CollectionStatusRow(
                source="collector",
                datatype="candles",
                status="succeeded",
                latest_event_ts=_dt("2026-06-20T00:00:00+00:00"),
                manifest_refs=("manifest-1",),
            ),
        ),
        "archive_coverage": (
            ArchiveCoverageRow(
                venue="hyperliquid",
                instrument_id="BTC",
                family="bars",
                timeframe="1m",
                start_ts=_dt("2026-01-01T00:00:00+00:00"),
                end_ts=_dt("2026-06-01T00:00:00+00:00"),
                coverage_ratio=0.99,
                status="pass",
            ),
        ),
        "gap_reports": (
            GapReportRow(
                report_id="gap-1",
                venue="hyperliquid",
                instrument_id="BTC",
                family="bars",
                timeframe="1m",
                gap_count=0,
                severity="pass",
            ),
        ),
        "lockbox": LockboxVisibility(
            policy_id="dynamic_full_calendar_months_v1",
            start_ts=_dt("2026-05-01T00:00:00+00:00"),
            end_ts=_dt("2026-06-01T00:00:00+00:00"),
        ),
        "lead_book": (
            LeadBookVisibilityRow(
                lead_id="lead-1",
                strategy_family="example",
                state="deep_validation_requested",
                human_inspection_status="complete",
                agent_approval_status="approved",
                blocker_reasons=("not promotion evidence",),
            ),
        ),
        "deep_validation": (
            DeepValidationVisibilityRow(
                lead_id="lead-1",
                status="active",
                active=True,
                scorecard_status="in_progress",
            ),
        ),
        "final_hard_tests": (
            FinalHardTestVisibilityRow(
                slot_id="slot-1",
                lead_id="lead-1",
                status="allocated",
                frozen_evidence=True,
                non_live_disclaimer="Research-only report; not paper/live readiness.",
            ),
        ),
        "audit_chunks": (
            AuditChunkVisibilityRow(
                audit_id="V2-AUD-UI-001",
                area="ui",
                status="implemented",
                purpose="read-only visibility",
                evidence="pending validation",
            ),
        ),
        "worker_jobs": (
            WorkerJobVisibilityRow(
                job_id="worker-1",
                kind="coverage",
                status="succeeded",
                terminal_state=True,
                attempts=1,
                archive_manifest_refs=("manifest-1",),
            ),
        ),
        "notes": ("No command controls are rendered.",),
    }
    payload.update(updates)
    return V2VisibilitySnapshot(**payload)


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.astimezone(UTC)
