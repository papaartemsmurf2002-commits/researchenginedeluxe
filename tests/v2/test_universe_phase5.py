from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.universe.hyperliquid import (
    diff_snapshots,
    refresh_hyperliquid_universe,
    select_asof_universe,
)
from tradingbotsuite.v2.universe.models import UniverseMode
from tradingbotsuite.v2.universe.rules import (
    CURRENT_UNIVERSE_SANDBOX_ONLY,
    MISSING_HIP3_METADATA,
    VOLUME_BELOW_THRESHOLD,
)


ROOT = Path(__file__).resolve().parents[2]


def test_hyperliquid_universe_includes_non_btc_eth_above_5m(tmp_path) -> None:
    result = refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(day_sol=12_000_000),
        asof_date=date(2026, 6, 1),
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
        eligible_only=True,
    )

    assert result.eligible_count >= 2
    assert "hyperliquid:perp:SOL" in {row.instrument_id for row in rows}


def test_hyperliquid_universe_excludes_below_5m_day_ntl_volume(tmp_path) -> None:
    refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(day_sol=4_999_999),
        asof_date=date(2026, 6, 1),
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
    )
    sol = _by_id(rows, "hyperliquid:perp:SOL")

    assert sol.eligible is False
    assert sol.exclusion_reason == VOLUME_BELOW_THRESHOLD


def test_hyperliquid_universe_archives_excluded_instruments(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    result = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(day_sol=1),
        asof_date=date(2026, 6, 1),
    )
    layout = ArchiveLayout(archive_root)
    catalog_rows = pq.read_table(layout.resolve("manifests", "instrument_catalog.parquet")).to_pylist()
    snapshot_rows = pq.read_table(layout.resolve("manifests", "universe_snapshots.parquet")).to_pylist()

    assert any(row["instrument_id"] == "hyperliquid:perp:SOL" for row in catalog_rows)
    assert any(
        row["instrument_id"] == "hyperliquid:perp:SOL" and row["eligible"] is False
        for row in snapshot_rows
    )
    assert any(layout.layer_root("raw").rglob("*.jsonl.zst"))
    assert result.raw_file_id


def test_hyperliquid_universe_handles_hip3_prefixed_symbols(tmp_path) -> None:
    refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(include_complete_hip3=True),
        asof_date=date(2026, 6, 1),
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
    )
    hip3 = _by_id(rows, "hyperliquid:hip3:xyz:ABC")

    assert hip3.eligible is True
    assert hip3.accepted_research_evidence_allowed is True


def test_missing_hip3_reference_metadata_blocks_evidence(tmp_path) -> None:
    refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(include_incomplete_hip3=True),
        asof_date=date(2026, 6, 1),
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
    )
    hip3 = _by_id(rows, "hyperliquid:hip3:xyz:ABC")

    assert hip3.eligible is False
    assert hip3.exclusion_reason == MISSING_HIP3_METADATA
    assert hip3.accepted_research_evidence_allowed is False


def test_asof_universe_does_not_use_future_volume_snapshot(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    first = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(day_sol=4_000_000),
        asof_date=date(2026, 6, 1),
    )
    second = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(day_sol=12_000_000),
        asof_date=date(2026, 6, 2),
    )

    june_one = select_asof_universe(
        archive_root=archive_root,
        asof_date=date(2026, 6, 1),
        eligible_only=True,
    )
    june_two = select_asof_universe(
        archive_root=archive_root,
        asof_date=date(2026, 6, 2),
        eligible_only=True,
    )

    assert "hyperliquid:perp:SOL" not in {row.instrument_id for row in june_one}
    assert "hyperliquid:perp:SOL" in {row.instrument_id for row in june_two}
    diff = diff_snapshots(
        archive_root=archive_root,
        left_snapshot_id=first.snapshot_id,
        right_snapshot_id=second.snapshot_id,
    )
    assert diff["added"] == ["hyperliquid:perp:SOL"]


def test_current_universe_mode_is_sandbox_only(tmp_path) -> None:
    refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(day_sol=12_000_000),
        asof_date=date(2026, 6, 1),
        mode=UniverseMode.CURRENT_LABELED_SANDBOX,
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
        mode=UniverseMode.CURRENT_LABELED_SANDBOX,
    )

    assert rows
    assert all(row.evidence_scope == "current_sandbox_only" for row in rows)
    assert all(row.accepted_research_evidence_allowed is False for row in rows)


def test_universe_refresh_cli_with_fixture_creates_snapshot(tmp_path) -> None:
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(_payload(day_sol=12_000_000)), encoding="utf-8")
    archive_root = tmp_path / "archive"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "universe",
            "refresh",
            "--venue",
            "hyperliquid",
            "--min-day-notional-usd",
            "5000000",
            "--payload-file",
            str(payload_file),
            "--archive-root",
            str(archive_root),
            "--asof-date",
            "2026-06-01",
            "--include-hip3-dexs",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "universe_snapshot_id=" in result.stdout
    assert "eligible_count=" in result.stdout
    rows = select_asof_universe(
        archive_root=archive_root,
        asof_date=date(2026, 6, 1),
        eligible_only=True,
    )
    assert "hyperliquid:perp:SOL" in {row.instrument_id for row in rows}


def test_universe_list_and_explain_cli(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    result = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(day_sol=12_000_000),
        asof_date=date(2026, 6, 1),
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    listed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "universe",
            "list",
            "--archive-root",
            str(archive_root),
            "--asof-date",
            "2026-06-01",
            "--eligible-only",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    explained = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "universe",
            "explain",
            "--archive-root",
            str(archive_root),
            "--snapshot",
            result.snapshot_id,
            "--instrument",
            "hyperliquid:perp:SOL",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert listed.returncode == 0
    assert "hyperliquid:perp:SOL" in listed.stdout
    assert explained.returncode == 0
    assert '"instrument_id":"hyperliquid:perp:SOL"' in explained.stdout


def _by_id(rows, instrument_id):
    matches = [row for row in rows if row.instrument_id == instrument_id]
    assert len(matches) == 1
    return matches[0]


def _payload(
    *,
    day_sol: float = 12_000_000,
    include_complete_hip3: bool = False,
    include_incomplete_hip3: bool = False,
):
    universe = [
        {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
        {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
        {"name": "LOW", "szDecimals": 1, "maxLeverage": 5},
    ]
    contexts = [
        {"dayNtlVlm": "100000000", "openInterest": "10", "markPx": "60000", "oraclePx": "60001", "funding": "0.0001"},
        {"dayNtlVlm": str(day_sol), "openInterest": "20", "markPx": "150", "oraclePx": "151", "funding": "0.0002"},
        {"dayNtlVlm": "1000", "openInterest": "1", "markPx": "1", "oraclePx": "1", "funding": "0.0"},
    ]
    if include_complete_hip3 or include_incomplete_hip3:
        hip3 = {"name": "xyz:ABC", "szDecimals": 2, "maxLeverage": 3}
        if include_complete_hip3:
            hip3.update(
                {
                    "referenceMarket": "NYSE:ABC",
                    "oracleSource": "official_reference",
                    "referenceSessionCalendar": "us_equities",
                    "weekendBehaviorDocumented": True,
                    "listingAgeDays": 200,
                    "proxyDataAvailable": True,
                }
            )
        universe.append(hip3)
        contexts.append(
            {
                "dayNtlVlm": "9000000",
                "openInterest": "4",
                "markPx": "12",
                "oraclePx": "12",
                "funding": "0.0",
            }
        )
    return [{"universe": universe}, contexts]
