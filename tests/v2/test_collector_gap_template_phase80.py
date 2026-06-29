from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.archive_inventory import DataGapRequest
from tradingbotsuite.v2.collectors import ResearchCollectorAdapterTemplate, collector_template_from_gap_request
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[2]


def test_collector_template_requires_gap_and_never_authorizes_collection() -> None:
    gap = _gap_request()

    template = collector_template_from_gap_request(gap)

    assert template.data_gap_request_id == gap.data_gap_request_id
    assert template.requested_family == "bars"
    assert template.venue_probe_allowed is True
    assert template.allowed_venues == gap.venue_preference
    assert template.collection_scope == "bounded_gap_request_only"
    assert template.venue_expansion_allowed is False
    assert template.gap_evidence_provided is True
    assert template.existing_archive_refs_checked == gap.existing_archive_refs_checked
    assert template.missing_coverage_report_ids == gap.missing_coverage_report_ids
    assert template.collection_authorized is False
    assert template.research_only is True
    assert template.promotion_ready is False
    assert "raw_source_ref" in template.manifest_refs_required


def test_collector_template_rejects_gap_without_suggested_collector() -> None:
    gap = _gap_request().model_copy(update={"suggested_collector": None, "venue_probe_allowed": False})

    with pytest.raises(ValueError, match="no suggested collector"):
        collector_template_from_gap_request(gap)


def test_collector_template_rejects_probe_gap_without_checked_evidence() -> None:
    gap = _gap_request().model_copy(
        update={
            "existing_archive_refs_checked": (),
            "missing_coverage_report_ids": (),
        }
    )

    with pytest.raises(ValueError, match="venue probes require checked archive refs"):
        collector_template_from_gap_request(gap)


def test_collector_template_rejects_venue_expansion() -> None:
    template = collector_template_from_gap_request(_gap_request())

    with pytest.raises(ValueError, match="cannot allow venue expansion"):
        ResearchCollectorAdapterTemplate(
            **template.model_dump(exclude={"venue_expansion_allowed"}),
            venue_expansion_allowed=True,
        )


def test_collector_template_rejects_unbounded_probe_venue() -> None:
    template = collector_template_from_gap_request(_gap_request())

    with pytest.raises(ValueError, match="allowed venues must be bounded"):
        ResearchCollectorAdapterTemplate(
            **template.model_dump(exclude={"allowed_venues"}),
            allowed_venues=("hyperliquid", "binance"),
        )


def test_collectors_gap_template_cli_converts_resolver_report_without_collection(tmp_path: Path) -> None:
    bars_gap = _gap_request()
    coverage_gap = _gap_request().model_copy(
        update={
            "requested_family": "coverage",
            "requested_fields": ("coverage_ratio",),
            "suggested_collector": None,
            "venue_probe_allowed": False,
        }
    )
    report_path = tmp_path / "resolver-report.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "data_gap_requests": [
                    bars_gap.model_dump(mode="json"),
                    coverage_gap.model_dump(mode="json"),
                ],
                **dict(RESEARCH_BOUNDARY),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "collectors",
            "gap-template",
            "--gap-request-file",
            str(report_path),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["template_count"] == 1
    assert payload["skipped_gap_count"] == 1
    template = payload["templates"][0]
    assert template["data_gap_request_id"] == bars_gap.data_gap_request_id
    assert template["collection_authorized"] is False
    assert template["venue_probe_allowed"] is True
    assert template["allowed_venues"] == list(bars_gap.venue_preference)
    assert template["collection_scope"] == "bounded_gap_request_only"
    assert template["venue_expansion_allowed"] is False
    assert template["gap_evidence_provided"] is True
    assert template["existing_archive_refs_checked"] == list(bars_gap.existing_archive_refs_checked)
    assert template["research_only"] is True
    assert template["promotion_ready"] is False
    assert payload["skipped_gap_requests"][0]["requested_family"] == "coverage"


def _gap_request() -> DataGapRequest:
    payload = {
        "strategy_id": "test_strategy",
        "requested_family": "bars",
        "requested_fields": ("close",),
        "instrument_ids": ("hyperliquid:perp:SOL",),
        "venue_preference": ("hyperliquid",),
        "start_ts": datetime(2024, 1, 1, tzinfo=UTC),
        "end_ts": datetime(2024, 7, 1, tzinfo=UTC),
        "reason": "archive_inventory_has_no_usable_family_window_for_strategy",
        "existing_archive_refs_checked": (
            "archive_inventory://checked/no_usable_refs?family=bars&venue=hyperliquid&instruments=hyperliquid:perp:SOL",
        ),
        "missing_coverage_report_ids": ("c" * 64,),
        "suggested_collector": "research_only_bars_gap_collector_template",
        "priority": "normal",
        "venue_probe_allowed": True,
        **dict(RESEARCH_BOUNDARY),
    }
    return DataGapRequest(
        **payload,
        data_gap_request_id=canonical_json_hash(
            {
                "schema_version": V2_SCHEMA_VERSION,
                "strategy_id": payload["strategy_id"],
                "family": payload["requested_family"],
                "fields": payload["requested_fields"],
                "instrument_ids": payload["instrument_ids"],
                "start_ts": payload["start_ts"].isoformat(),
                "end_ts": payload["end_ts"].isoformat(),
            }
        ),
    )
