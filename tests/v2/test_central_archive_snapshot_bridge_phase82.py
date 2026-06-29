from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive_inventory import (
    CentralArchiveSnapshotBridgeConfig,
    build_central_archive_snapshot_bridge,
)
from tradingbotsuite.v2.backtest_data import (
    BacktestDataRequest,
    BacktestDataService,
    BacktestEvidenceMode,
)
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.config.time import utc_isoformat
from tradingbotsuite.v2.data_quality.coverage import expected_bar_count
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.universe.hyperliquid import load_universe_rows


ROOT = Path(__file__).resolve().parents[2]
VENUE = "binance_usdm"
BTC = "binance:perp:BTCUSDT"
ETH = "binance:perp:ETHUSDT"


def test_central_archive_snapshot_bridge_writes_v2_snapshot_contract(tmp_path) -> None:
    central_root = tmp_path / "central"
    bridge_root = tmp_path / "bridge"
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 1, 3, tzinfo=UTC)
    _write_central_fixture(
        central_root,
        symbols=("BTC", "ETH"),
        start_ts=start_ts,
        end_ts=end_ts,
    )

    result = build_central_archive_snapshot_bridge(
        CentralArchiveSnapshotBridgeConfig(
            central_archive_root=str(central_root),
            bridge_archive_root=str(bridge_root),
            instrument_ids=(BTC, ETH),
            timeframe="1m",
            start_ts=start_ts,
            end_ts=end_ts,
            asof_date=date(2024, 1, 1),
        )
    )

    expected_per_instrument = expected_bar_count(start_ts, end_ts, "1m")
    assert result.central_archive_mutated is False
    assert result.benchmark_input_ready is True
    assert result.file_manifest_count == 2
    assert result.row_count == expected_per_instrument * 2
    assert result.expected_row_count == expected_per_instrument * 2
    assert result.research_only is True
    assert result.observe_only is True
    assert result.promotion_ready is False
    assert result.live_signal is False
    assert (bridge_root / "manifests" / "central_archive_snapshot_bridge_report.json").exists()

    store = ArchiveManifestStore(ArchiveLayout(bridge_root))
    file_rows = store.load_file_manifest()
    snapshots = store.load_archive_snapshots()
    coverage_reports = CoverageManifestStore(ArchiveLayout(bridge_root)).load_coverage_reports()
    universe_rows = load_universe_rows(bridge_root)

    assert len(file_rows) == 2
    assert {row.instrument_id for row in file_rows} == {BTC, ETH}
    assert {row.layer.value for row in file_rows} == {"silver"}
    assert snapshots and snapshots[0].archive_snapshot_id == result.archive_snapshot_id
    assert {report.evidence_mode.value for report in coverage_reports} == {"accepted_research"}
    assert {report.instrument_id for report in coverage_reports} == {BTC, ETH}
    assert {row.instrument_id for row in universe_rows} == {BTC, ETH}
    assert {row.evidence_scope for row in universe_rows} == {"accepted_research"}
    assert all(row.accepted_research_evidence_allowed for row in universe_rows)

    data_slice = BacktestDataService(bridge_root).load_panel(
        BacktestDataRequest(
            archive_root=str(bridge_root),
            archive_snapshot_id=result.archive_snapshot_id,
            universe_snapshot_id=result.universe_snapshot_id,
            venue=VENUE,
            instrument_id=BTC,
            instrument_ids=(BTC, ETH),
            timeframe="1m",
            start_ts=start_ts,
            end_ts=end_ts,
            requested_fields=("ts", "instrument_id", "open", "close", "volume", "coverage_ratio"),
            evidence_mode=BacktestEvidenceMode.SANDBOX_DIAGNOSTIC,
        ),
        asof_date=date(2024, 1, 4),
        write_manifest=False,
    )
    assert data_slice.reported_row_count == expected_per_instrument * 2
    assert data_slice.data_manifest.instrument_ids == (BTC, ETH)
    assert data_slice.data_manifest.coverage_ratio == 1.0


def test_central_archive_snapshot_bridge_cli_writes_json_report(tmp_path) -> None:
    central_root = tmp_path / "central"
    bridge_root = tmp_path / "bridge"
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 1, 2, tzinfo=UTC)
    _write_central_fixture(
        central_root,
        symbols=("BTC",),
        start_ts=start_ts,
        end_ts=end_ts,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "archive-inventory",
            "--bridge-central-snapshot",
            "--archive-root",
            str(central_root),
            "--bridge-archive-root",
            str(bridge_root),
            "--instrument-id",
            BTC,
            "--timeframe",
            "1m",
            "--start-ts",
            "2024-01-01T00:00:00Z",
            "--end-ts",
            "2024-01-02T00:00:00Z",
            "--asof-date",
            "2024-01-01",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["report_type"] == "central_archive_snapshot_bridge_report_v1"
    assert payload["central_archive_mutated"] is False
    assert payload["benchmark_input_ready"] is True
    assert payload["instrument_ids"] == [BTC]
    assert payload["promotion_ready"] is False
    assert (bridge_root / "manifests" / "archive_snapshots.parquet").exists()


def _write_central_fixture(
    central_root: Path,
    *,
    symbols: tuple[str, ...],
    start_ts: datetime,
    end_ts: datetime,
) -> None:
    project_rows = []
    for symbol in symbols:
        manifest_ref = _write_central_symbol_month(
            central_root,
            symbol=symbol,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        project_rows.append(
            {
                "symbol": symbol,
                "ledger_symbol": symbol,
                "backtest_usable": True,
                "manifest_refs": [manifest_ref],
            }
        )
    report = {
        "report_id": canonical_json_hash({"symbols": symbols, "start_ts": utc_isoformat(start_ts)}),
        "project_rows": project_rows,
        **dict(RESEARCH_BOUNDARY),
    }
    report_path = central_root / "manifests" / "wpr106-546-project-needed-1m-current-lifecycle-validation-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_central_symbol_month(
    central_root: Path,
    *,
    symbol: str,
    start_ts: datetime,
    end_ts: datetime,
) -> str:
    normalized_ref = f"normalized/{symbol.lower()}-1m.parquet"
    normalized_path = central_root / normalized_ref
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(_central_bar_rows(symbol=symbol, start_ts=start_ts, end_ts=end_ts))
    pq.write_table(table, normalized_path, compression="zstd")
    normalized_sha = file_sha256(normalized_path)
    row_count = table.num_rows
    coverage_report_id = canonical_json_hash(
        {"symbol": symbol, "start_ts": utc_isoformat(start_ts), "end_ts": utc_isoformat(end_ts)}
    )
    manifest_id = canonical_json_hash(
        {"symbol": symbol, "normalized_ref": normalized_ref, "normalized_sha256": normalized_sha}
    )
    manifest_ref = f"manifests/{symbol.lower()}-1m-batch_manifest.json"
    manifest_payload = {
        "manifest_id": manifest_id,
        "normalized_ref": normalized_ref,
        "normalized_sha256": normalized_sha,
        "normalized_row_count": row_count,
        "quality_report": {
            "coverage_reports": [
                {
                    "coverage_report_id": coverage_report_id,
                    "venue": VENUE,
                    "instrument_id": f"binance:perp:{symbol}USDT",
                    "family": "bars",
                    "timeframe": "1m",
                    "start_ts": utc_isoformat(start_ts),
                    "end_ts": utc_isoformat(end_ts - timedelta(minutes=1)),
                    "expected_rows": row_count,
                    "observed_rows": row_count,
                    "coverage_ratio": 1.0,
                    "coverage_min": 0.98,
                    "blocker_reasons": [],
                }
            ]
        },
        **dict(RESEARCH_BOUNDARY),
    }
    manifest_path = central_root / manifest_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest_ref


def _central_bar_rows(
    *,
    symbol: str,
    start_ts: datetime,
    end_ts: datetime,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start_ts
    index = 0
    price_offset = 0.0 if symbol == "BTC" else 100.0
    while current < end_ts:
        close = 1000.0 + price_offset + (index * 0.01)
        rows.append(
            {
                "timestamp": utc_isoformat(current),
                "normalized_symbol": f"{symbol}USDT",
                "provider": "central-fixture",
                "open": close - 0.05,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 10_000.0 + index,
                "trade_count": index + 1,
            }
        )
        current += timedelta(minutes=1)
        index += 1
    return rows
