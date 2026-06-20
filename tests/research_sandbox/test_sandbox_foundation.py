from __future__ import annotations

import gzip
import json
import tarfile
import zipfile
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
import pytest

import tradingbotsuite.research_sandbox.fast_backtest as fast_backtest_module
import tradingbotsuite.research_sandbox.intake as intake_module
import tradingbotsuite.research_sandbox.market_data as market_data_module
import tradingbotsuite.research_sandbox.preflight as preflight_module
import tradingbotsuite.research_sandbox.runner as runner_module
import tradingbotsuite.research_sandbox.strategy_blueprints as strategy_blueprints_module
import tradingbotsuite.research_sandbox.suite as suite_module
from tradingbotsuite.research_sandbox import (
    DataWindow,
    ExitVariant,
    FilterVariant,
    SandboxRunSpec,
    StrategyCatalogRow,
    VenueArchiveDescriptor,
    audit_sandbox_archive_descriptors,
    build_sandbox_archive_manifest,
    build_sandbox_global_leaderboard,
    build_sandbox_iteration_index,
    export_sandbox_venue_expansion_candidate_manifest,
    deterministic_trial_id,
    export_sandbox_suite_validation_request_bundle,
    export_sandbox_validation_request_bundle,
    export_sandbox_venue_expansion_request_bundle,
    index_sandbox_artifacts,
    load_market_frame,
    load_market_frame_for_descriptor,
    load_market_frames_for_descriptors,
    load_sandbox_run_spec,
    load_sandbox_suite_spec,
    load_strategy_catalog,
    load_venue_archive_descriptors,
    materialize_sandbox_strategy_catalog,
    materialize_sandbox_venue_expansion_requests,
    materialize_strategy_signals,
    preflight_sandbox_compatibility,
    preflight_sandbox_strict_validation_descriptors,
    require_sandbox_artifact_integrity,
    run_fixed_hold_sweep,
    run_fixed_hold_sweep_for_venue_frames,
    run_sandbox_agent_iteration,
    run_sandbox_archive_sweep,
    run_sandbox_suite,
    run_sandbox_sweep,
    sandbox_boundary_metadata,
    show_sandbox_next_action,
    summarize_sandbox_hypotheses,
    summarize_sandbox_archive_coverage,
    summarize_sandbox_run,
    summarize_sandbox_throughput,
    summarize_sandbox_suite_hypotheses,
    verify_sandbox_artifact_integrity,
)


def _market_frame() -> pd.DataFrame:
    timestamps = pd.date_range("2023-12-30", periods=80, freq="12h", tz="UTC")
    close = [100.0 + index for index in range(len(timestamps))]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "close": close,
            "fallback_signal": [1 if index % 3 == 0 else 0 for index in range(len(timestamps))],
            "quality": [0.8 if index % 4 else 0.2 for index in range(len(timestamps))],
        }
    )


def _spec(run_id: str = "sandbox-test-run") -> SandboxRunSpec:
    return SandboxRunSpec(
        run_id=run_id,
        data_window=DataWindow("2024-01-01", "2024-02-15"),
        holding_periods=(1, 2),
        round_trip_cost_bps=1.0,
        min_trades=2,
        max_evidence_requests=3,
    )


def _strategy() -> StrategyCatalogRow:
    return StrategyCatalogRow(
        hypothesis_id="fallback-long",
        family="transparent_motif_fallback",
        source_id="curated_leads_csv",
        signal_column="fallback_signal",
        side="long",
        filter_column="quality",
        filter_min=0.5,
        params={"lookback": 4},
        tags=("wpr106-221", "sandbox"),
    )


def _short_strategy() -> StrategyCatalogRow:
    return StrategyCatalogRow(
        hypothesis_id="fallback-short",
        family="transparent_motif_fallback",
        source_id="curated_leads_csv",
        signal_column="fallback_signal",
        side="short",
        filter_column="quality",
        filter_min=0.5,
        params={"lookback": 4},
        tags=("wpr106-control", "sandbox"),
    )


def _blueprint_strategy() -> StrategyCatalogRow:
    return StrategyCatalogRow(
        hypothesis_id="compiled-momentum-long",
        family="trend_following_v1",
        signal_column="sandbox_signal_compiled_momentum_long",
        side="long",
        params={
            "sandbox_blueprint_id": "close_momentum_proxy",
            "sandbox_proxy_signal": True,
            "lookback_bars": 1,
            "return_threshold": 0.015,
        },
        tags=("sandbox_blueprint",),
    )


def _venue(venue: str = "okx") -> VenueArchiveDescriptor:
    return VenueArchiveDescriptor(
        descriptor_id=f"{venue}-btcusdt-2024-kline",
        venue=venue,
        symbol="BTCUSDT",
        data_family="kline",
        interval="12h",
        window=DataWindow("2024-01-01", "2024-02-15"),
        diagnostic_only=True,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _refresh_manifest_artifact_integrity(manifest_path: Path, artifact_key: str, artifact_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("artifact_integrity", {})[artifact_key] = {
        "sha256": _sha256(artifact_path),
        "byte_size": artifact_path.stat().st_size,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _xlsx_column_name(index: int) -> str:
    chars: list[str] = []
    while index >= 0:
        index, remainder = divmod(index, 26)
        chars.append(chr(ord("A") + remainder))
        index -= 1
    return "".join(reversed(chars))


def _xml_attr(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})


def _minimal_xlsx_sheet_xml(rows: list[list[object]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "  <sheetData>",
    ]
    for row_index, row in enumerate(rows, start=1):
        lines.append(f'    <row r="{row_index}">')
        for column_index, value in enumerate(row):
            if value is None:
                continue
            cell_ref = f"{_xlsx_column_name(column_index)}{row_index}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                lines.append(f'      <c r="{cell_ref}"><v>{value}</v></c>')
            else:
                lines.append(f'      <c r="{cell_ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        lines.append("    </row>")
    lines.extend(["  </sheetData>", "</worksheet>"])
    return "\n".join(lines)


def _write_minimal_xlsx(path: Path, sheets: dict[str, list[list[object]]]) -> None:
    sheet_entries = "\n".join(
        f'    <sheet name="{_xml_attr(sheet_name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, sheet_name in enumerate(sheets, start=1)
    )
    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
{sheet_entries}
  </sheets>
</workbook>"""
    rel_entries = "\n".join(
        f'  <Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, len(sheets) + 1)
    )
    rels_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rel_entries}
</Relationships>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for index, rows in enumerate(sheets.values(), start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _minimal_xlsx_sheet_xml(rows))


def _write_suite_fixture(base_dir: Path, *, suite_id: str = "suite-batch-smoke") -> Path:
    suite_dir = base_dir / "suite_bundle"
    suite_dir.mkdir()
    cases: list[dict[str, str]] = []
    for index, venue in enumerate(("okx", "bybit"), start=1):
        case_id = f"case-{venue}"
        case_dir = suite_dir / case_id
        case_dir.mkdir()
        spec_path = case_dir / "spec.json"
        catalog_path = case_dir / "catalog.csv"
        venues_path = case_dir / "venues.json"
        market_path = case_dir / "market.csv"
        spec_path.write_text(
            json.dumps(
                {
                    "run_id": f"suite-run-{venue}",
                    "data_window": {"start": "2024-01-01", "end": "2024-01-08"},
                    "holding_periods": [1],
                    "round_trip_cost_bps": 0.0,
                    "min_trades": 1,
                    "max_evidence_requests": 1,
                    "rank_top_n": 5,
                }
            ),
            encoding="utf-8",
        )
        pd.DataFrame(
            [
                {
                    "hypothesis_id": f"suite-long-{venue}",
                    "family": "suite_fast_iteration",
                    "signal_column": "signal",
                    "side": "long",
                }
            ]
        ).to_csv(catalog_path, index=False)
        pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=8, freq="1D", tz="UTC"),
                "close": [100 + (index * row) for row in range(8)],
                "signal": [1] * 8,
            }
        ).to_csv(market_path, index=False)
        venues_path.write_text(
            json.dumps(
                {
                    "venue_archives": [
                        {
                            "descriptor_id": f"{venue}-suite-btcusdt",
                            "venue": venue,
                            "symbol": "BTCUSDT",
                            "data_family": "kline",
                            "data_path": "market.csv",
                            "window": {"start": "2024-01-01", "end": "2024-01-08"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        cases.append(
            {
                "case_id": case_id,
                "label": f"{venue} suite case",
                "spec": f"{case_id}/spec.json",
                "strategy_catalog": f"{case_id}/catalog.csv",
                "venue_archives": f"{case_id}/venues.json",
                "min_request_score": 0.0,
            }
        )
    suite_path = suite_dir / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": suite_id,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "sandbox_only": True,
                "candidate_evidence": False,
                "candidate_pack_eligible": False,
                "top_n": 1,
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )
    return suite_path


def _write_shared_market_suite_fixture(base_dir: Path, *, suite_id: str = "suite-shared-market") -> Path:
    suite_dir = base_dir / "shared_market_suite"
    suite_dir.mkdir()
    shared_market_path = suite_dir / "shared_market.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=8, freq="1D", tz="UTC"),
            "close": [100 + row for row in range(8)],
            "signal": [1] * 8,
        }
    ).to_csv(shared_market_path, index=False)
    cases: list[dict[str, object]] = []
    for venue in ("okx", "bybit"):
        case_id = f"case-{venue}"
        case_dir = suite_dir / case_id
        case_dir.mkdir()
        (case_dir / "spec.json").write_text(
            json.dumps(
                {
                    "run_id": f"shared-suite-run-{venue}",
                    "data_window": {"start": "2024-01-01", "end": "2024-01-08"},
                    "holding_periods": [1],
                    "round_trip_cost_bps": 0.0,
                    "min_trades": 1,
                    "max_evidence_requests": 1,
                    "rank_top_n": 5,
                }
            ),
            encoding="utf-8",
        )
        pd.DataFrame(
            [
                {
                    "hypothesis_id": f"shared-suite-long-{venue}",
                    "family": "suite_shared_market_cache",
                    "signal_column": "signal",
                    "side": "long",
                }
            ]
        ).to_csv(case_dir / "catalog.csv", index=False)
        (case_dir / "venues.json").write_text(
            json.dumps(
                {
                    "venue_archives": [
                        {
                            "descriptor_id": f"{venue}-shared-suite-btcusdt",
                            "venue": venue,
                            "symbol": "BTCUSDT",
                            "data_family": "kline",
                            "window": {"start": "2024-01-01", "end": "2024-01-08"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        cases.append(
            {
                "case_id": case_id,
                "spec": f"{case_id}/spec.json",
                "strategy_catalog": f"{case_id}/catalog.csv",
                "venue_archives": f"{case_id}/venues.json",
                "market_data": "shared_market.csv",
                "min_request_score": 0.0,
            }
        )
    suite_path = suite_dir / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": suite_id,
                **{
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "sandbox_only": True,
                    "candidate_evidence": False,
                    "candidate_pack_eligible": False,
                },
                "top_n": 1,
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )
    return suite_path


def _write_shared_input_suite_fixture(base_dir: Path, *, suite_id: str = "suite-shared-input") -> Path:
    suite_dir = base_dir / "shared_input_suite"
    suite_dir.mkdir()
    shared_spec_path = suite_dir / "shared_spec.json"
    shared_catalog_path = suite_dir / "shared_catalog.csv"
    shared_venues_path = suite_dir / "shared_venues.json"
    shared_market_path = suite_dir / "shared_market.csv"
    shared_spec_path.write_text(
        json.dumps(
            {
                "run_id": "shared-input-suite-run",
                "data_window": {"start": "2024-01-01", "end": "2024-01-08"},
                "holding_periods": [1],
                "round_trip_cost_bps": 0.0,
                "min_trades": 1,
                "max_evidence_requests": 1,
                "rank_top_n": 5,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "hypothesis_id": "shared-input-suite-long",
                "family": "suite_shared_input_cache",
                "signal_column": "signal",
                "side": "long",
            }
        ]
    ).to_csv(shared_catalog_path, index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=8, freq="1D", tz="UTC"),
            "close": [100 + row for row in range(8)],
            "signal": [1] * 8,
        }
    ).to_csv(shared_market_path, index=False)
    shared_venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-shared-input-suite-btcusdt",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "data_path": "shared_market.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-08"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    suite_path = suite_dir / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": suite_id,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "sandbox_only": True,
                "candidate_evidence": False,
                "candidate_pack_eligible": False,
                "top_n": 1,
                "cases": [
                    {
                        "case_id": "case-first",
                        "spec": "shared_spec.json",
                        "strategy_catalog": "shared_catalog.csv",
                        "venue_archives": "shared_venues.json",
                    },
                    {
                        "case_id": "case-second",
                        "spec": "shared_spec.json",
                        "strategy_catalog": "shared_catalog.csv",
                        "venue_archives": "shared_venues.json",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return suite_path


def test_sandbox_spec_rejects_pre_2024_data_windows() -> None:
    with pytest.raises(ValueError, match="2024-01-01"):
        DataWindow("2023-12-31", "2024-01-31")


def test_venue_archive_descriptors_support_multi_venue_research_only_inputs() -> None:
    venues = [_venue("okx"), _venue("bybit"), _venue("hyperliquid")]

    for venue in venues:
        payload = venue.to_payload()
        assert payload["research_only"] is True
        assert payload["observe_only"] is True
        assert payload["promotion_ready"] is False
        assert payload["candidate_pack_eligible"] is False
        assert payload["diagnostic_only"] is True


def test_strategy_catalog_loader_reads_csv_without_executing_code(tmp_path: Path) -> None:
    catalog_path = tmp_path / "strategy_catalog.csv"
    pd.DataFrame(
        [
            {
                "hypothesis_id": "fallback-long",
                "family": "transparent_motif_fallback",
                "source_id": "curated-leads",
                "signal_column": "fallback_signal",
                "side": "long",
                "filter_column": "quality",
                "filter_min": 0.5,
                "params_json": json.dumps({"lookback": 4}),
                "tags": "wpr106-221|sandbox",
            }
        ]
    ).to_csv(catalog_path, index=False)

    rows = load_strategy_catalog(catalog_path)

    assert len(rows) == 1
    assert rows[0].hypothesis_id == "fallback-long"
    assert rows[0].params == {"lookback": 4}
    assert rows[0].tags == ("wpr106-221", "sandbox")
    assert rows[0].to_payload()["candidate_evidence"] is False


def test_strategy_catalog_loader_compiles_repo_strategy_config_json(tmp_path: Path) -> None:
    config_path = tmp_path / "trend_following_v1.json"
    config_path.write_text(
        json.dumps(
            {
                "strategy_id": "trend_following_v1",
                "strategy_version": "v1",
                "enabled": True,
                "feature_set_id": "features_price_trend_vol",
                "holding_period": "24h",
                "parameters": {"slope_threshold": 0.1, "spacing_bars": 10},
            }
        ),
        encoding="utf-8",
    )

    rows = load_strategy_catalog(config_path)
    rows_again = load_strategy_catalog(config_path)

    assert {row.side for row in rows} == {"long", "short"}
    assert {row.params["sandbox_blueprint_id"] for row in rows} == {"close_momentum_proxy"}
    assert all(row.params["source_metadata"]["strategy_id"] == "trend_following_v1" for row in rows)
    assert [row.signal_column for row in rows] == [row.signal_column for row in rows_again]
    assert all(row.to_payload()["promotion_ready"] is False for row in rows)


def test_strategy_catalog_loader_compiles_spreadsheet_like_lead_table(tmp_path: Path) -> None:
    catalog_path = tmp_path / "curated_leads.csv"
    pd.DataFrame(
        [
            {
                "Packet": "WPR106-221",
                "Lead": "transparent motif active fallback",
                "Evidence": "pre-May positive, May diagnostic only",
                "Next Check": "range reversion proxy falsification",
            }
        ]
    ).to_csv(catalog_path, index=False)

    rows = load_strategy_catalog(catalog_path)

    assert {row.side for row in rows} == {"long", "short"}
    assert {row.params["sandbox_blueprint_id"] for row in rows} == {"range_reversion_proxy"}
    assert all(row.params["source_metadata"]["source_type"] == "spreadsheet_lead_catalog" for row in rows)
    assert all("spreadsheet_lead_catalog" in row.tags for row in rows)


def test_strategy_catalog_loader_normalizes_direct_header_aliases(tmp_path: Path) -> None:
    catalog_path = tmp_path / "human_strategy_sheet.csv"
    pd.DataFrame(
        [
            {
                "Hypothesis": "alias-direct-short",
                "Strategy Family": "alias_family",
                "Source": "existing-sheet",
                "Signal": "short_entry_signal",
                "Direction": "short",
                "Exit": "fixed_hold",
                "Filter": "quality_score",
                "Min Filter": "0.25",
                "Max Filter": "0.90",
                "Params": json.dumps({"lookback": 7, "note": "direct alias"}),
                "Labels": "alias|fast,manual;spreadsheet",
                "Description": "Existing spreadsheet row with human headers.",
            }
        ]
    ).to_csv(catalog_path, index=False)

    rows = load_strategy_catalog(catalog_path)

    assert len(rows) == 1
    row = rows[0]
    assert row.hypothesis_id == "alias-direct-short"
    assert row.family == "alias_family"
    assert row.source_id == "existing-sheet"
    assert row.signal_column == "short_entry_signal"
    assert row.side == "short"
    assert row.exit_profile == "fixed_hold"
    assert row.filter_column == "quality_score"
    assert row.filter_min == pytest.approx(0.25)
    assert row.filter_max == pytest.approx(0.90)
    assert row.params == {"lookback": 7, "note": "direct alias"}
    assert set(row.tags) == {"alias", "fast", "manual", "spreadsheet"}
    assert "sandbox_blueprint_id" not in row.params
    assert row.to_payload()["candidate_pack_eligible"] is False


def test_strategy_catalog_loader_reads_xlsx_without_optional_excel_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workbook_path = tmp_path / "leads.xlsx"
    workbook_xml = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Curated Leads" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    sheet_xml = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>Packet</t></is></c>
      <c r="B1" t="inlineStr"><is><t>Lead</t></is></c>
      <c r="C1" t="inlineStr"><is><t>Next Check</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>WPR106-222</t></is></c>
      <c r="B2" t="inlineStr"><is><t>directional KNN source stability</t></is></c>
      <c r="C2" t="inlineStr"><is><t>momentum proxy falsification</t></is></c>
    </row>
  </sheetData>
</worksheet>"""
    with zipfile.ZipFile(workbook_path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    def _raise_missing_engine(*_args: object, **_kwargs: object) -> object:
        raise ImportError("Missing optional dependency 'openpyxl'")

    monkeypatch.setattr(pd, "ExcelFile", _raise_missing_engine)

    rows = load_strategy_catalog(workbook_path)

    assert len(rows) == 2
    assert {row.params["sandbox_blueprint_id"] for row in rows} == {"close_momentum_proxy"}
    assert all(row.params["source_metadata"]["source_sheet"] == "Curated Leads" for row in rows)


def test_strategy_catalog_loader_rejects_legacy_xls_with_explicit_policy(tmp_path: Path) -> None:
    workbook_path = tmp_path / "legacy_strategy_catalog.xls"
    workbook_path.write_bytes(b"legacy binary workbook")

    with pytest.raises(ValueError, match="unsupported_legacy_xls_strategy_catalog"):
        load_strategy_catalog(workbook_path)


def test_strategy_catalog_materializer_reports_legacy_xls_repair_row(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    workbook_path = catalog_root / "legacy_strategy_catalog.xls"
    workbook_path.write_bytes(b"legacy binary workbook")

    payload = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "out")
    source_row = payload["sources"][0]

    assert payload["included_source_count"] == 0
    assert payload["skipped_source_count"] == 1
    assert source_row["source_suffix"] == ".xls"
    assert source_row["status"] == "skipped"
    assert "unsupported_legacy_xls_strategy_catalog" in source_row["skip_reasons"][0]
    assert source_row["promotion_ready"] is False


def test_strategy_catalog_loader_rejects_oversized_xlsx_fallback_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workbook_path = tmp_path / "oversized_member.xlsx"
    _write_minimal_xlsx(
        workbook_path,
        {
            "Direct Signals": [
                ["Hypothesis", "Strategy Family", "Signal", "Direction"],
                ["direct-sheet-long", "workbook_direct_family", "direct_entry_signal", "long"],
            ]
        },
    )

    def _raise_missing_engine(*_args: object, **_kwargs: object) -> object:
        raise ImportError("Missing optional dependency 'openpyxl'")

    monkeypatch.setattr(pd, "ExcelFile", _raise_missing_engine)
    monkeypatch.setattr(intake_module, "MAX_XLSX_MEMBER_BYTES", 32)

    with pytest.raises(ValueError, match="xlsx_member_bytes_limit_exceeded"):
        load_strategy_catalog(workbook_path)


def test_strategy_catalog_loader_rejects_xlsx_fallback_row_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workbook_path = tmp_path / "too_many_rows.xlsx"
    _write_minimal_xlsx(
        workbook_path,
        {
            "Direct Signals": [
                ["Hypothesis", "Strategy Family", "Signal", "Direction"],
                ["direct-sheet-long", "workbook_direct_family", "direct_entry_signal", "long"],
            ]
        },
    )

    def _raise_missing_engine(*_args: object, **_kwargs: object) -> object:
        raise ImportError("Missing optional dependency 'openpyxl'")

    monkeypatch.setattr(pd, "ExcelFile", _raise_missing_engine)
    monkeypatch.setattr(intake_module, "MAX_XLSX_ROWS_PER_SHEET", 1)

    with pytest.raises(ValueError, match="xlsx_sheet_rows_limit_exceeded"):
        load_strategy_catalog(workbook_path)


def test_strategy_catalog_loader_reads_all_usable_xlsx_sheets_without_optional_excel_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workbook_path = tmp_path / "multi_sheet_strategies.xlsx"
    _write_minimal_xlsx(
        workbook_path,
        {
            "Direct Signals": [
                ["Hypothesis", "Strategy Family", "Signal", "Direction", "Catalog Source"],
                ["direct-sheet-long", "workbook_direct_family", "direct_entry_signal", "long", "direct-workbook"],
            ],
            "Range Ideas": [
                ["Packet", "Lead", "Next Check"],
                ["WPR106-303", "range reversion long workbook setup", "range reversion proxy falsification"],
            ],
            "Notes": [["Note"], ["human notes must not become strategy rows"]],
        },
    )

    def _raise_missing_engine(*_args: object, **_kwargs: object) -> object:
        raise ImportError("Missing optional dependency 'openpyxl'")

    monkeypatch.setattr(pd, "ExcelFile", _raise_missing_engine)

    rows = load_strategy_catalog(workbook_path)

    direct_rows = [row for row in rows if row.hypothesis_id == "direct-sheet-long"]
    lead_rows = [row for row in rows if "spreadsheet_lead_catalog" in row.tags]
    assert len(rows) == 2
    assert len(direct_rows) == 1
    assert direct_rows[0].source_id == "direct-workbook"
    assert direct_rows[0].signal_column == "direct_entry_signal"
    assert len(lead_rows) == 1
    assert lead_rows[0].side == "long"
    assert lead_rows[0].params["sandbox_blueprint_id"] == "range_reversion_proxy"
    assert lead_rows[0].params["source_metadata"]["source_sheet"] == "Range Ideas"


def test_strategy_catalog_loader_preserves_direct_workbook_sheet_source_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    workbook_path = catalog_root / "direct_sheets.xlsx"
    _write_minimal_xlsx(
        workbook_path,
        {
            "Momentum Direct": [
                ["Hypothesis", "Strategy Family", "Signal", "Direction"],
                ["momentum-direct-long", "workbook_direct_family", "momentum_signal", "long"],
            ],
            "Range Direct": [
                ["Hypothesis", "Strategy Family", "Signal", "Direction"],
                ["range-direct-short", "workbook_direct_family", "range_signal", "short"],
            ],
            "Explicit Source": [
                ["Hypothesis", "Strategy Family", "Signal", "Direction", "Catalog Source"],
                ["explicit-source-long", "workbook_direct_family", "explicit_signal", "long", "curated-explicit-source"],
            ],
        },
    )

    def _raise_missing_engine(*_args: object, **_kwargs: object) -> object:
        raise ImportError("Missing optional dependency 'openpyxl'")

    monkeypatch.setattr(pd, "ExcelFile", _raise_missing_engine)

    rows = load_strategy_catalog(workbook_path)
    materialized = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "out")
    materialized_rows = load_strategy_catalog(materialized["strategy_catalog_json_path"])

    source_ids = {row.hypothesis_id: row.source_id for row in rows}
    expected_momentum_source = f"{workbook_path}#Momentum Direct"
    expected_range_source = f"{workbook_path}#Range Direct"
    assert source_ids["momentum-direct-long"] == expected_momentum_source
    assert source_ids["range-direct-short"] == expected_range_source
    assert source_ids["explicit-source-long"] == "curated-explicit-source"
    materialized_source_ids = {row.hypothesis_id: row.source_id for row in materialized_rows}
    assert materialized_source_ids == source_ids
    assert set(materialized["sources"][0]["source_ids"]) == {
        expected_momentum_source,
        expected_range_source,
        "curated-explicit-source",
    }
    assert materialized["sources"][0]["workbook_included_sheet_names"] == [
        "Momentum Direct",
        "Range Direct",
        "Explicit Source",
    ]


def test_strategy_catalog_materializer_reports_workbook_sheet_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    workbook_path = catalog_root / "multi_sheet_strategies.xlsx"
    _write_minimal_xlsx(
        workbook_path,
        {
            "Direct Signals": [
                ["Hypothesis", "Strategy Family", "Signal", "Direction"],
                ["direct-sheet-short", "workbook_direct_family", "direct_short_signal", "short"],
            ],
            "Breakout Ideas": [
                ["Packet", "Lead", "Next Check"],
                ["WPR106-303", "volatility breakout long workbook lead", "breakout proxy falsification"],
            ],
            "Notes": [["Note"], ["ignored operator note"]],
        },
    )

    def _raise_missing_engine(*_args: object, **_kwargs: object) -> object:
        raise ImportError("Missing optional dependency 'openpyxl'")

    monkeypatch.setattr(pd, "ExcelFile", _raise_missing_engine)

    payload = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "out")
    rows = load_strategy_catalog(payload["strategy_catalog_json_path"])
    source_row = payload["sources"][0]
    report_frame = pd.read_parquet(Path(str(payload["build_report_parquet_path"])))
    report_row = report_frame.iloc[0].to_dict()

    assert payload["included_source_count"] == 1
    assert payload["skipped_source_count"] == 0
    assert payload["strategy_count"] == 2
    assert len(rows) == 2
    assert source_row["source_kind"] == "workbook_strategy_catalog"
    assert source_row["workbook_sheet_count"] == 3
    assert source_row["workbook_included_sheet_count"] == 2
    assert source_row["workbook_skipped_sheet_count"] == 1
    assert source_row["workbook_strategy_count"] == 2
    assert source_row["workbook_sheet_status_counts"] == {"included": 2, "skipped": 1}
    assert source_row["workbook_sheet_kind_counts"] == {
        "direct_strategy_catalog": 1,
        "spreadsheet_lead_catalog": 1,
        "unsupported_sheet": 1,
    }
    assert source_row["workbook_included_sheet_names"] == ["Direct Signals", "Breakout Ideas"]
    assert source_row["workbook_skipped_sheet_names"] == ["Notes"]
    assert source_row["workbook_sheet_rows"][2]["skip_reasons"] == ["unsupported_sheet_columns"]
    assert source_row["workbook_fallback_limits"]["max_xlsx_member_bytes"] == intake_module.MAX_XLSX_MEMBER_BYTES
    assert json.loads(report_row["workbook_sheet_rows"])[1]["sheet_name"] == "Breakout Ideas"
    assert json.loads(report_row["workbook_sheet_status_counts"]) == {"included": 2, "skipped": 1}
    assert json.loads(report_row["workbook_fallback_limits"])["max_xlsx_sheets"] == intake_module.MAX_XLSX_SHEETS
    assert report_row["workbook_included_sheet_count"] == 2
    assert report_row["promotion_ready"] is False


def test_strategy_catalog_materializer_preserves_direct_header_aliases(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    pd.DataFrame(
        [
            {
                "Candidate ID": "materialized-alias-long",
                "Category": "materialized_alias_family",
                "Catalog Source": "alias-materializer",
                "Entry Signal": "entry_signal",
                "Trade Side": "long",
                "Quality Filter": "liquidity_score",
                "Filter Lower": "0.5",
                "Filter Upper": "1.0",
                "Parameters JSON": json.dumps({"threshold": 0.2}),
                "Comment": "Alias materializer smoke.",
            }
        ]
    ).to_csv(catalog_root / "alias_direct.csv", index=False)

    payload = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "out")
    rows = load_strategy_catalog(payload["strategy_catalog_json_path"])
    row = rows[0]

    assert payload["included_source_count"] == 1
    assert payload["skipped_source_count"] == 0
    assert payload["strategy_count"] == 1
    assert payload["blueprint_counts"] == {}
    assert row.hypothesis_id == "materialized-alias-long"
    assert row.family == "materialized_alias_family"
    assert row.source_id == "alias-materializer"
    assert row.signal_column == "entry_signal"
    assert row.filter_column == "liquidity_score"
    assert row.filter_min == pytest.approx(0.5)
    assert row.filter_max == pytest.approx(1.0)
    assert row.params == {"threshold": 0.2}
    assert row.to_payload()["promotion_ready"] is False


def test_strategy_catalog_materializer_discovery_bound_is_deterministic(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "bounded-first",
                "family": "bounded_discovery_family",
                "signal_column": "first_signal",
            }
        ]
    ).to_csv(catalog_root / "00_first.csv", index=False)
    (catalog_root / "01_notes.txt").write_text("unsupported but counted as discovered source", encoding="utf-8")
    pd.DataFrame(
        [
            {
                "hypothesis_id": "bounded-third",
                "family": "bounded_discovery_family",
                "signal_column": "third_signal",
            }
        ]
    ).to_csv(catalog_root / "02_third.csv", index=False)

    payload = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "out", max_files=2)
    source_names = [Path(str(row["source_path"])).name for row in payload["sources"]]

    assert payload["file_count"] == 2
    assert payload["source_count"] == 2
    assert payload["truncated"] is True
    assert payload["strategy_count"] == 1
    assert source_names == ["00_first.csv", "01_notes.txt"]


def test_strategy_catalog_loader_compiles_repo_strategy_config_directory(tmp_path: Path) -> None:
    (tmp_path / "trend.json").write_text(
        json.dumps({"strategy_id": "trend_following_v1", "strategy_version": "v1", "parameters": {}}),
        encoding="utf-8",
    )
    (tmp_path / "range.json").write_text(
        json.dumps({"strategy_id": "range_reversion_v1", "strategy_version": "v1", "parameters": {}}),
        encoding="utf-8",
    )

    rows = load_strategy_catalog(tmp_path)

    assert len(rows) == 4
    assert {row.params["sandbox_blueprint_id"] for row in rows} == {"close_momentum_proxy", "range_reversion_proxy"}


def test_strategy_catalog_materializer_writes_loadable_catalog_and_report(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "direct-long",
                "family": "direct_family",
                "source_id": "local-spreadsheet",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        [
            {
                "Packet": "WPR106-241",
                "Lead": "range squeeze",
                "Evidence": "agent materializer smoke",
                "Next Check": "range reversion proxy falsification",
            }
        ]
    ).to_csv(catalog_root / "lead.csv", index=False)
    (catalog_root / "trend.json").write_text(
        json.dumps({"strategy_id": "trend_following_v1", "strategy_version": "v1", "parameters": {}}),
        encoding="utf-8",
    )
    (catalog_root / "notes.txt").write_text("unsupported", encoding="utf-8")
    pd.DataFrame([{"foo": "bar"}]).to_csv(catalog_root / "bad.csv", index=False)

    payload = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "out")
    catalog_path = Path(str(payload["strategy_catalog_json_path"]))
    catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    rows = load_strategy_catalog(catalog_path)
    strategy_frame = pd.read_parquet(Path(str(payload["strategy_catalog_parquet_path"])))
    report_frame = pd.read_parquet(Path(str(payload["build_report_parquet_path"])))
    artifact_catalog = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["included_source_count"] == 3
    assert payload["skipped_source_count"] == 2
    assert payload["strategy_count"] == 5
    assert payload["strategy_count"] == len(rows)
    assert payload["blueprint_counts"] == {"close_momentum_proxy": 2, "range_reversion_proxy": 2}
    assert catalog_path.exists()
    assert Path(str(payload["build_report_json_path"])).exists()
    assert Path(str(payload["strategy_catalog_parquet_path"])).exists()
    assert Path(str(payload["build_report_parquet_path"])).exists()
    assert catalog_payload["artifact_family"] == "rapid_strategy_iteration_sandbox_strategy_catalog"
    assert catalog_payload["strategy_count"] == payload["strategy_count"]
    assert {row.hypothesis_id for row in rows} >= {"direct-long"}
    assert set(report_frame["status"]) == {"included", "skipped"}
    assert strategy_frame["candidate_pack_eligible"].eq(False).all()
    assert artifact_catalog["artifact_kind_counts"]["strategy_catalog"] == 1
    assert artifact_catalog["artifact_kind_counts"]["strategy_catalog_build_report"] == 1


def test_strategy_catalog_materializer_is_idempotent_for_agent_preflight(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "direct-long",
                "family": "direct_family",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)

    first = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "out")
    second = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "out")

    assert second["catalog_id"] == first["catalog_id"]
    assert second["output_dir"] == first["output_dir"]
    assert Path(str(second["strategy_catalog_json_path"])).exists()


def test_venue_descriptor_loader_reads_archive_manifest_json(tmp_path: Path) -> None:
    data_path = tmp_path / "market.csv"
    manifest_path = tmp_path / "venues.json"
    manifest_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "bybit-ethusdt-2024-trades",
                        "venue": "bybit",
                        "symbol": "ETHUSDT",
                        "data_family": "trade",
                        "data_path": str(data_path),
                        "window": {"start": "2024-01-01", "end": "2024-12-31"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    descriptors = load_venue_archive_descriptors(manifest_path)

    assert len(descriptors) == 1
    assert descriptors[0].venue == "bybit"
    assert descriptors[0].manifest_path == manifest_path
    assert descriptors[0].data_path == data_path


def test_venue_descriptor_loader_canonicalizes_common_venue_aliases(tmp_path: Path) -> None:
    manifest_path = tmp_path / "venues.json"
    manifest_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "binance-futures-btcusdt",
                        "venue": "binance_futures",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "window": {"start": "2024-01-01", "end": "2024-01-31"},
                    },
                    {
                        "descriptor_id": "okex-ethusdt",
                        "venue": "okex",
                        "symbol": "ETHUSDT",
                        "data_family": "kline",
                        "window": {"start": "2024-02-01", "end": "2024-02-28"},
                    },
                    {
                        "descriptor_id": "bybit-linear-solusdt",
                        "venue": "bybit_usdt_linear",
                        "symbol": "SOLUSDT",
                        "data_family": "trade",
                        "window": {"start": "2024-03-01", "end": "2024-03-31"},
                    },
                    {
                        "descriptor_id": "hl-perp-btc",
                        "venue": "hl_perp",
                        "symbol": "BTC",
                        "data_family": "trade",
                        "window": {"start": "2024-04-01", "end": "2024-04-30"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    descriptors = load_venue_archive_descriptors(manifest_path)

    assert [descriptor.venue for descriptor in descriptors] == ["binance_usdm", "okx", "bybit", "hyperliquid"]
    assert all(descriptor.to_payload()["promotion_ready"] is False for descriptor in descriptors)
    assert all(descriptor.to_payload()["candidate_pack_eligible"] is False for descriptor in descriptors)


def test_venue_descriptor_rejects_unknown_venue_alias() -> None:
    with pytest.raises(ValueError, match="unsupported sandbox venue"):
        VenueArchiveDescriptor(
            descriptor_id="unsupported-btcusdt",
            venue="coinbase_derivatives",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-31"),
        )


def test_venue_descriptor_loader_resolves_relative_data_path_from_manifest(tmp_path: Path) -> None:
    data_path = tmp_path / "relative_market.csv"
    data_path.write_text("timestamp,close\n2024-01-01T00:00:00Z,100\n", encoding="utf-8")
    manifest_path = tmp_path / "venues.json"
    manifest_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-relative-btcusdt",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "data_path": "relative_market.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-31"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    descriptors = load_venue_archive_descriptors(manifest_path)

    assert descriptors[0].data_path == data_path


def test_sandbox_run_spec_loader_reads_template_shape() -> None:
    spec = load_sandbox_run_spec("configs/sandbox/rapid_strategy_iteration_sandbox_smoke_v1.json")

    assert spec.run_id == "sandbox-smoke-2024-forward-v1"
    assert spec.data_window.start.isoformat() == "2024-01-01"
    assert spec.max_evidence_requests == 10


def test_market_frame_loader_reads_normalized_csv_and_filters_pre_2024(tmp_path: Path) -> None:
    path = tmp_path / "market.csv"
    pd.DataFrame(
        {
            "timestamp": ["2023-12-31T00:00:00Z", "2024-01-01T00:00:00Z", "2024-01-01T12:00:00Z"],
            "close": [99.0, 100.0, 101.0],
            "fallback_signal": [1, 1, 0],
        }
    ).to_csv(path, index=False)

    frame = load_market_frame(path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert frame["timestamp"].iloc[0].isoformat().startswith("2024-01-01")


def test_market_frame_loader_interprets_numeric_timestamp_milliseconds(tmp_path: Path) -> None:
    path = tmp_path / "okx_numeric_timestamp_ms.csv"
    pd.DataFrame(
        {
            "timestamp": [1704067200000, 1704070800000],
            "close": [100.0, 101.0],
        }
    ).to_csv(path, index=False)

    frame = load_market_frame(path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert [value.isoformat() for value in frame["timestamp"]] == [
        "2024-01-01T00:00:00+00:00",
        "2024-01-01T01:00:00+00:00",
    ]


def test_market_frame_loader_interprets_numeric_time_microseconds(tmp_path: Path) -> None:
    path = tmp_path / "bybit_numeric_time_us.csv"
    pd.DataFrame(
        {
            "time": [1706745600000000, 1706746500000000],
            "close": [200.0, 201.0],
        }
    ).to_csv(path, index=False)

    frame = load_market_frame(path)

    assert list(frame["close"]) == [200.0, 201.0]
    assert [value.isoformat() for value in frame["timestamp"]] == [
        "2024-02-01T00:00:00+00:00",
        "2024-02-01T00:15:00+00:00",
    ]


def test_market_frame_loader_preserves_compact_yyyymmdd_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "compact_date_timestamp.csv"
    pd.DataFrame(
        {
            "timestamp": [20240101, 20240102],
            "close": [10.0, 11.0],
        }
    ).to_csv(path, index=False)

    frame = load_market_frame(path)

    assert list(frame["close"]) == [10.0, 11.0]
    assert [value.date().isoformat() for value in frame["timestamp"]] == ["2024-01-01", "2024-01-02"]


def test_market_frame_loader_reads_binance_vision_kline_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / "BTCUSDT-15m-2024-01.zip"
    rows = [
        [1704067200000, "100", "101", "99", "100.5", "10", 1704068099999, "1000", 10, "5", "500", "0"],
        [1704068100000, "100.5", "102", "100", "101.5", "11", 1704068999999, "1100", 11, "6", "600", "0"],
    ]
    csv_payload = "\n".join(",".join(str(value) for value in row) for row in rows) + "\n"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("BTCUSDT-15m-2024-01.csv", csv_payload)

    frame = load_market_frame(zip_path)

    assert list(frame["close"]) == [100.5, 101.5]
    assert frame["timestamp"].iloc[0].isoformat().startswith("2024-01-01")


def test_market_frame_loader_preserves_headered_zip_venue_aliases(tmp_path: Path) -> None:
    zip_path = tmp_path / "generic_venue_export.zip"
    frame = pd.DataFrame(
        {
            "venue": ["bybit", "bybit"],
            "symbol": ["ETHUSDT", "ETHUSDT"],
            "interval": ["15m", "15m"],
            "startTime": [1706745600000, 1706746500000],
            "openPrice": ["200.0", "201.0"],
            "highPrice": ["202.0", "203.0"],
            "lowPrice": ["199.0", "200.0"],
            "closePrice": ["201.0", "202.0"],
            "volume": ["20.0", "21.0"],
        }
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("market_export.csv", frame.to_csv(index=False))

    loaded = load_market_frame(zip_path)
    metadata = loaded.attrs["sandbox_normalization_metadata"]

    assert list(loaded["close"]) == [201.0, 202.0]
    assert list(loaded["venue"]) == ["bybit", "bybit"]
    assert list(loaded["symbol"]) == ["ETHUSDT", "ETHUSDT"]
    assert metadata["alias_columns"]["timestamp"] == "startTime"
    assert metadata["alias_columns"]["close"] == "closePrice"
    assert metadata["assigned_binance_kline_columns"] is False


def test_market_frame_loader_reads_zip_ndjson_member(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_stream_export.zip"
    rows = [
        {"time": "2023-12-31T23:59:00Z", "px": "99.0", "sz": "1.0"},
        {"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
        {"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
    ]
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/trades.ndjson", "\n".join(json.dumps(row) for row in rows))

    frame = load_market_frame(zip_path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert list(frame["volume"]) == [2.0, 3.0]
    assert frame["timestamp"].min().date().isoformat() == "2024-01-01"


def test_market_frame_loader_prefers_csv_zip_member_over_json_stream(tmp_path: Path) -> None:
    zip_path = tmp_path / "mixed_export.zip"
    csv_frame = pd.DataFrame(
        {
            "timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"],
            "close": [200.0, 201.0],
        }
    )
    ndjson_rows = [
        {"time": "2024-01-01T00:00:00Z", "px": "100.0"},
        {"time": "2024-01-01T00:01:00Z", "px": "101.0"},
    ]
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("a_stream.ndjson", "\n".join(json.dumps(row) for row in ndjson_rows))
        archive.writestr("b_market.csv", csv_frame.to_csv(index=False))

    frame = load_market_frame(zip_path)

    assert list(frame["close"]) == [200.0, 201.0]


def test_market_frame_loader_reads_extracted_binance_vision_kline_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "BTCUSDT-15m-2024-01.csv"
    rows = [
        [1704067200000, "100", "101", "99", "100.5", "10", 1704068099999, "1000", 10, "5", "500", "0"],
        [1704068100000, "100.5", "102", "100", "101.5", "11", 1704068999999, "1100", 11, "6", "600", "0"],
    ]
    csv_path.write_text("\n".join(",".join(str(value) for value in row) for row in rows) + "\n", encoding="utf-8")

    frame = load_market_frame(csv_path)

    assert list(frame["close"]) == [100.5, 101.5]


def test_market_frame_loader_reads_gzip_csv_and_filters_pre_2024(tmp_path: Path) -> None:
    csv_gz_path = tmp_path / "okx_BTCUSDT_1h_kline.csv.gz"
    pd.DataFrame(
        {
            "timestamp": [
                "2023-12-31T23:00:00Z",
                "2024-01-01T00:00:00Z",
                "2024-01-01T01:00:00Z",
            ],
            "open": [99.0, 100.0, 101.0],
            "high": [100.0, 101.0, 102.0],
            "low": [98.0, 99.0, 100.0],
            "close": [99.5, 100.5, 101.5],
        }
    ).to_csv(csv_gz_path, index=False, compression="gzip")

    frame = load_market_frame(csv_gz_path)

    assert list(frame["close"]) == [100.5, 101.5]
    assert list(frame["high"]) == [101.0, 102.0]
    assert frame["timestamp"].min().date().isoformat() == "2024-01-01"


def test_market_frame_loader_reads_gzip_jsonl_hyperliquid_aliases(tmp_path: Path) -> None:
    jsonl_gz_path = tmp_path / "hyperliquid_BTC_trades.jsonl.gz"
    rows = [
        {"time": "2023-12-31T23:59:00Z", "px": "99.0", "sz": "1.0"},
        {"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
        {"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
    ]
    with gzip.open(jsonl_gz_path, mode="wt", encoding="utf-8") as handle:
        handle.write("\n".join(json.dumps(row) for row in rows))

    frame = load_market_frame(jsonl_gz_path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert list(frame["volume"]) == [2.0, 3.0]
    assert frame["timestamp"].min().date().isoformat() == "2024-01-01"


def test_market_frame_loader_reads_ndjson_hyperliquid_aliases(tmp_path: Path) -> None:
    ndjson_path = tmp_path / "hyperliquid_BTC_trades.ndjson"
    rows = [
        {"time": "2023-12-31T23:59:00Z", "px": "99.0", "sz": "1.0"},
        {"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
        {"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
    ]
    ndjson_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n\n", encoding="utf-8")

    frame = load_market_frame(ndjson_path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert list(frame["volume"]) == [2.0, 3.0]
    assert frame["timestamp"].min().date().isoformat() == "2024-01-01"


def test_market_frame_loader_reads_gzip_ndjson_venue_aliases(tmp_path: Path) -> None:
    ndjson_gz_path = tmp_path / "bybit_ETHUSDT_trades.ndjson.gz"
    rows = [
        {"startTime": 1706745600000, "closePrice": "200.0", "volume": "20.0"},
        {"startTime": 1706745660000, "closePrice": "201.0", "volume": "21.0"},
    ]
    with gzip.open(ndjson_gz_path, mode="wt", encoding="utf-8") as handle:
        handle.write("\n".join(json.dumps(row) for row in rows))

    frame = load_market_frame(ndjson_gz_path)
    metadata = frame.attrs["sandbox_normalization_metadata"]

    assert list(frame["close"]) == [200.0, 201.0]
    assert list(frame["volume"]) == [20.0, 21.0]
    assert metadata["alias_columns"]["timestamp"] == "startTime"
    assert metadata["alias_columns"]["close"] == "closePrice"


def test_market_frame_loader_normalizes_okx_short_ohlcv_aliases(tmp_path: Path) -> None:
    path = tmp_path / "okx_BTC-USDT-SWAP_1h.csv"
    pd.DataFrame(
        {
            "ts": [1704067200000, 1704070800000],
            "o": ["100.0", "101.0"],
            "h": ["102.0", "103.0"],
            "l": ["99.0", "100.0"],
            "c": ["101.0", "102.0"],
            "vol": ["10.0", "11.0"],
        }
    ).to_csv(path, index=False)

    frame = load_market_frame(path)
    metadata = frame.attrs["sandbox_normalization_metadata"]

    assert list(frame["close"]) == [101.0, 102.0]
    assert list(frame["high"]) == [102.0, 103.0]
    assert list(frame["low"]) == [99.0, 100.0]
    assert list(frame["volume"]) == [10.0, 11.0]
    assert metadata["alias_columns"]["timestamp"] == "ts"
    assert metadata["alias_columns"]["close"] == "c"


def test_market_frame_loader_normalizes_bybit_price_aliases(tmp_path: Path) -> None:
    path = tmp_path / "bybit_ETHUSDT_15m_kline.csv"
    pd.DataFrame(
        {
            "startTime": [1706745600000, 1706746500000],
            "openPrice": ["200.0", "201.0"],
            "highPrice": ["202.0", "203.0"],
            "lowPrice": ["199.0", "200.0"],
            "closePrice": ["201.0", "202.0"],
            "volume": ["20.0", "21.0"],
        }
    ).to_csv(path, index=False)

    frame = load_market_frame(path)

    assert list(frame["close"]) == [201.0, 202.0]
    assert "high" in frame.columns
    assert "low" in frame.columns
    assert frame.attrs["sandbox_normalization_metadata"]["alias_columns"]["timestamp"] == "startTime"


def test_market_frame_loader_normalizes_okx_mark_and_index_price_aliases(tmp_path: Path) -> None:
    mark_path = tmp_path / "okx_BTC-USDT-SWAP_mark_price.csv"
    index_path = tmp_path / "okx_BTC-USDT-SWAP_index_price.csv"
    pd.DataFrame(
        {
            "ts": [1704067200000, 1704070800000],
            "markPx": ["100.1", "101.2"],
        }
    ).to_csv(mark_path, index=False)
    pd.DataFrame(
        {
            "ts": [1704067200000, 1704070800000],
            "idxPx": ["99.9", "100.8"],
        }
    ).to_csv(index_path, index=False)

    mark_frame = load_market_frame(mark_path)
    index_frame = load_market_frame(index_path)

    assert list(mark_frame["close"]) == [100.1, 101.2]
    assert mark_frame.attrs["sandbox_normalization_metadata"]["alias_columns"]["close"] == "markPx"
    assert list(index_frame["close"]) == [99.9, 100.8]
    assert index_frame.attrs["sandbox_normalization_metadata"]["alias_columns"]["close"] == "idxPx"


def test_market_frame_loader_derives_close_from_bid_ask_midpoint(tmp_path: Path) -> None:
    path = tmp_path / "hyperliquid_BTC_l2_book.csv"
    pd.DataFrame(
        {
            "time": ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"],
            "bestBidPx": ["100.0", "101.0"],
            "bestAskPx": ["101.0", "102.0"],
            "bidSize": ["5.0", "6.0"],
            "askSize": ["4.0", "5.0"],
            "venue": ["hyperliquid", "hyperliquid"],
        }
    ).to_csv(path, index=False)

    frame = load_market_frame(path)
    metadata = frame.attrs["sandbox_normalization_metadata"]

    assert list(frame["close"]) == [100.5, 101.5]
    assert metadata["derived_columns"]["close"] == {
        "method": "bid_ask_midpoint",
        "bid_column": "bestBidPx",
        "ask_column": "bestAskPx",
    }
    assert metadata["derived_count"] == 1
    assert metadata["assigned_binance_kline_columns"] is False


def test_market_frame_loader_flattens_hyperliquid_l2_book_json(tmp_path: Path) -> None:
    path = tmp_path / "hyperliquid_BTC_l2Book.json"
    payload = {
        "channel": "l2Book",
        "data": [
            {
                "coin": "BTC",
                "time": 1704067140000,
                "levels": [[{"px": "99.0", "sz": "1.0", "n": 1}], [{"px": "100.0", "sz": "1.5", "n": 1}]],
            },
            {
                "coin": "BTC",
                "time": 1704067200000,
                "levels": [[{"px": "100.0", "sz": "5.0", "n": 2}], [{"px": "101.0", "sz": "4.0", "n": 3}]],
            },
            {
                "coin": "BTC",
                "time": 1704067260000,
                "levels": {
                    "bids": [{"px": "101.0", "sz": "6.0", "n": 1}],
                    "asks": [{"px": "102.0", "sz": "5.0", "n": 2}],
                },
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    frame = load_market_frame(path)
    metadata = frame.attrs["sandbox_normalization_metadata"]

    assert list(frame["close"]) == [100.5, 101.5]
    assert list(frame["bestBidPx"]) == ["100.0", "101.0"]
    assert list(frame["bestAskPx"]) == ["101.0", "102.0"]
    assert metadata["derived_columns"]["close"] == {
        "method": "bid_ask_midpoint",
        "bid_column": "bestBidPx",
        "ask_column": "bestAskPx",
    }
    assert metadata["source_transformations"]["hyperliquid_l2_levels"] == {
        "method": "best_bid_ask_from_levels",
        "row_count": 3,
    }
    assert metadata["source_transformation_count"] == 1
    assert frame["timestamp"].min().date().isoformat() == "2024-01-01"


def test_market_frame_loader_flattens_hyperliquid_l2_book_zip_json(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_BTC_l2Book.zip"
    payload = {
        "channel": "l2Book",
        "data": {
            "coin": "BTC",
            "time": 1704067200000,
            "levels": [[{"px": "100.0", "sz": "5.0", "n": 1}], [{"px": "101.0", "sz": "4.0", "n": 1}]],
        },
    }
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/l2Book.json", json.dumps(payload))

    frame = load_market_frame(zip_path)
    metadata = frame.attrs["sandbox_normalization_metadata"]

    assert list(frame["close"]) == [100.5]
    assert metadata["derived_count"] == 1
    assert metadata["source_transformation_count"] == 1


def test_market_frame_loader_flattens_hyperliquid_l2_book_jsonl_messages(tmp_path: Path) -> None:
    path = tmp_path / "hyperliquid_BTC_l2Book.jsonl"
    rows = [
        {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1704067200000,
                "levels": [[{"px": "100.0", "sz": "5.0", "n": 1}], [{"px": "101.0", "sz": "4.0", "n": 1}]],
            },
        },
        {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1704067260000,
                "levels": [[{"px": "101.0", "sz": "6.0", "n": 1}], [{"px": "102.0", "sz": "5.0", "n": 1}]],
            },
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    frame = load_market_frame(path)
    metadata = frame.attrs["sandbox_normalization_metadata"]

    assert list(frame["close"]) == [100.5, 101.5]
    assert set(frame["channel"]) == {"l2Book"}
    assert metadata["source_transformations"]["hyperliquid_l2_levels"]["row_count"] == 2


def test_market_frame_loader_normalizes_hyperliquid_trade_aliases_and_filters_pre_2024(tmp_path: Path) -> None:
    path = tmp_path / "hyperliquid_BTC_trades.jsonl"
    rows = [
        {"time": "2023-12-31T23:59:00Z", "px": "99.0", "sz": "1.0"},
        {"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
        {"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    frame = load_market_frame(path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert list(frame["volume"]) == [2.0, 3.0]
    assert frame["timestamp"].min().date().isoformat() == "2024-01-01"


def test_market_frame_loader_uses_descriptor_data_path(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_market.csv"
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "close": [100.0]}).to_csv(path, index=False)
    descriptor = VenueArchiveDescriptor(
        descriptor_id="local-ethusdt",
        venue="local_manifest",
        symbol="ETHUSDT",
        data_family="kline",
        window=DataWindow("2024-01-01", "2024-01-31"),
        data_path=path,
    )

    frame = load_market_frame_for_descriptor(descriptor)

    assert frame.shape[0] == 1
    assert frame["close"].iloc[0] == 100.0


def test_market_frame_loader_checks_descriptor_integrity_for_gzip_source(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_market.csv.gz"
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "close": [100.0]}).to_csv(
        path,
        index=False,
        compression="gzip",
    )
    descriptor = VenueArchiveDescriptor(
        descriptor_id="bybit-gzip-integrity",
        venue="bybit",
        symbol="BTCUSDT",
        data_family="kline",
        window=DataWindow("2024-01-01", "2024-01-31"),
        data_path=path,
        source_integrity={"sha256": _sha256(path), "byte_size": path.stat().st_size},
    )

    frame = load_market_frame_for_descriptor(descriptor)

    assert frame.shape[0] == 1
    assert frame["close"].iloc[0] == 100.0


def test_market_frame_loader_rejects_descriptor_source_integrity_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_market.csv"
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "close": [100.0]}).to_csv(path, index=False)
    descriptor = VenueArchiveDescriptor(
        descriptor_id="okx-integrity-guard",
        venue="okx",
        symbol="BTCUSDT",
        data_family="kline",
        window=DataWindow("2024-01-01", "2024-01-31"),
        data_path=path,
        source_integrity={"sha256": _sha256(path), "byte_size": path.stat().st_size},
    )
    path.write_text(f"{path.read_text(encoding='utf-8')}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source_integrity_sha256_mismatch"):
        load_market_frame_for_descriptor(descriptor)


def test_market_frame_loader_routes_multiple_descriptors_to_distinct_data_paths(tmp_path: Path) -> None:
    okx_path = tmp_path / "okx.csv"
    bybit_path = tmp_path / "bybit.csv"
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "close": [101.0]}).to_csv(okx_path, index=False)
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "close": [99.0]}).to_csv(bybit_path, index=False)
    descriptors = [
        VenueArchiveDescriptor(
            descriptor_id="okx-btc",
            venue="okx",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-31"),
            data_path=okx_path,
        ),
        VenueArchiveDescriptor(
            descriptor_id="bybit-btc",
            venue="bybit",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-31"),
            data_path=bybit_path,
        ),
    ]

    frames = load_market_frames_for_descriptors(descriptors)

    assert frames["okx-btc"]["close"].iloc[0] == 101.0
    assert frames["bybit-btc"]["close"].iloc[0] == 99.0
    assert frames["okx-btc"] is not frames["bybit-btc"]


def test_market_frame_loader_reuses_same_descriptor_data_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "shared_descriptor_source.csv"
    pd.DataFrame(
        {
            "timestamp": ["2023-12-31T00:00:00Z", "2024-01-01T00:00:00Z"],
            "close": [99.0, 100.0],
        }
    ).to_csv(path, index=False)
    descriptors = [
        VenueArchiveDescriptor(
            descriptor_id="okx-btc",
            venue="okx",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-31"),
            data_path=path,
            source_integrity={"sha256": _sha256(path), "byte_size": path.stat().st_size},
        ),
        VenueArchiveDescriptor(
            descriptor_id="bybit-btc",
            venue="bybit",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-31"),
            data_path=path,
            source_integrity={"sha256": _sha256(path), "byte_size": path.stat().st_size},
        ),
    ]
    original_read_raw_table = market_data_module._read_raw_table
    read_count = 0

    def counting_read_raw_table(source_path: Path) -> pd.DataFrame:
        nonlocal read_count
        read_count += 1
        return original_read_raw_table(source_path)

    monkeypatch.setattr(market_data_module, "_read_raw_table", counting_read_raw_table)

    frames = load_market_frames_for_descriptors(descriptors)

    assert read_count == 1
    assert frames["okx-btc"] is frames["bybit-btc"]
    assert list(frames["okx-btc"]["close"]) == [100.0]


def test_market_frame_loader_checks_integrity_before_reusing_cached_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "shared_descriptor_source.csv"
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "close": [100.0]}).to_csv(path, index=False)
    descriptors = [
        VenueArchiveDescriptor(
            descriptor_id="okx-btc",
            venue="okx",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-31"),
            data_path=path,
            source_integrity={"sha256": _sha256(path), "byte_size": path.stat().st_size},
        ),
        VenueArchiveDescriptor(
            descriptor_id="bybit-btc",
            venue="bybit",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-31"),
            data_path=path,
            source_integrity={"sha256": "bad", "byte_size": path.stat().st_size},
        ),
    ]
    read_count = 0

    def counting_read_raw_table(source_path: Path) -> pd.DataFrame:
        nonlocal read_count
        read_count += 1
        return pd.read_csv(source_path)

    monkeypatch.setattr(market_data_module, "_read_raw_table", counting_read_raw_table)

    with pytest.raises(ValueError, match="bybit-btc: source_integrity_sha256_mismatch"):
        load_market_frames_for_descriptors(descriptors)

    assert read_count == 0


def test_market_frame_loader_fails_closed_when_descriptor_data_path_missing() -> None:
    descriptor = VenueArchiveDescriptor(
        descriptor_id="hyperliquid-missing",
        venue="hyperliquid",
        symbol="BTC",
        data_family="kline",
        window=DataWindow("2024-01-01", "2024-01-31"),
    )

    with pytest.raises(ValueError, match="data_path"):
        load_market_frames_for_descriptors([descriptor])


def test_archive_descriptor_audit_reports_ready_and_blocked_descriptors(tmp_path: Path) -> None:
    okx_path = tmp_path / "okx_market.csv"
    venues_path = tmp_path / "venues.json"
    pd.DataFrame(
        {
            "timestamp": [
                "2023-12-31T00:00:00Z",
                "2024-01-01T00:00:00Z",
                "2024-01-02T00:00:00Z",
                "2024-01-03T00:00:00Z",
                "2024-01-04T00:00:00Z",
                "2024-01-05T00:00:00Z",
            ],
            "close": [99.0, 100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [99.5, 100.5, 101.5, 102.5, 103.5, 104.5],
            "low": [98.5, 99.5, 100.5, 101.5, 102.5, 103.5],
        }
    ).to_csv(okx_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-audit-btcusdt",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1d",
                        "data_path": "okx_market.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-05"},
                    },
                    {
                        "descriptor_id": "bybit-audit-btcusdt",
                        "venue": "bybit",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1d",
                        "data_path": "missing_bybit.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-05"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = audit_sandbox_archive_descriptors(venues_path, output_dir=tmp_path / "audit_out")
    rows = {row["descriptor_id"]: row for row in payload["descriptors"]}
    parquet = pd.read_parquet(payload["audit_parquet_path"])

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_count"] == 2
    assert payload["ready_count"] == 1
    assert payload["blocked_count"] == 1
    assert Path(payload["audit_json_path"]).exists()
    assert Path(payload["audit_parquet_path"]).exists()
    assert set(parquet["descriptor_id"]) == {"okx-audit-btcusdt", "bybit-audit-btcusdt"}
    assert rows["okx-audit-btcusdt"]["status"] == "ready"
    assert rows["okx-audit-btcusdt"]["normalized_row_count"] == 5
    assert rows["okx-audit-btcusdt"]["descriptor_window_row_count"] == 5
    assert rows["okx-audit-btcusdt"]["has_high_low"] is True
    assert rows["bybit-audit-btcusdt"]["status"] == "blocked"
    assert "data_path_not_found" in rows["bybit-audit-btcusdt"]["blocker_reasons"]


def test_archive_descriptor_audit_uses_shared_market_data_for_smoke_audits(tmp_path: Path) -> None:
    shared_path = tmp_path / "shared_market.csv"
    venues_path = tmp_path / "venues.json"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=4, freq="1D", tz="UTC"),
            "close": [100.0, 101.0, 102.0, 103.0],
            "high": [101.0, 102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0, 102.0],
        }
    ).to_csv(shared_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "hyperliquid-shared-btcusdt",
                        "venue": "hyperliquid",
                        "symbol": "BTC",
                        "data_family": "kline",
                        "window": {"start": "2024-01-01", "end": "2024-01-04"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = audit_sandbox_archive_descriptors(
        venues_path,
        output_dir=tmp_path / "shared_audit_out",
        shared_market_data_path=shared_path,
    )
    row = payload["descriptors"][0]

    assert payload["ready_count"] == 1
    assert row["status"] == "ready"
    assert row["routing_mode"] == "shared_market_data_path"
    assert row["source_path"] == str(shared_path)
    assert row["descriptor_window_row_count"] == 4
    assert row["promotion_ready"] is False


def test_archive_descriptor_audit_records_container_member_metadata(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_BTC_trade.zip"
    venues_path = tmp_path / "venues.json"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "chunks/b.jsonl",
            json.dumps({"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"}),
        )
        archive.writestr(
            "chunks/a.jsonl",
            json.dumps({"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"}),
        )
        archive.writestr(
            "chunks/ignored.ndjson",
            json.dumps({"time": "2024-01-01T00:02:00Z", "px": "999.0", "sz": "9.0"}),
        )
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "hyperliquid-container-audit-btc",
                        "venue": "hyperliquid",
                        "symbol": "BTC",
                        "data_family": "trade",
                        "data_path": zip_path.name,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = audit_sandbox_archive_descriptors(venues_path, output_dir=tmp_path / "audit")
    row = payload["descriptors"][0]
    parquet = pd.read_parquet(payload["audit_parquet_path"]).iloc[0]

    assert row["status"] == "ready"
    assert row["container_kind"] == "zip"
    assert row["selected_member_suffix"] == ".jsonl"
    assert row["selected_member_count"] == 2
    assert row["selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert row["available_member_suffix_counts"] == {".jsonl": 2, ".ndjson": 1}
    assert row["loadable_member_count"] == 3
    assert parquet["container_kind"] == "zip"
    assert parquet["selected_member_suffix"] == ".jsonl"
    assert parquet["selected_member_count"] == 2
    assert json.loads(parquet["selected_member_name_sample"]) == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert json.loads(parquet["available_member_suffix_counts"])[".ndjson"] == 1


def test_archive_descriptor_audit_is_idempotent_for_agent_preflight(tmp_path: Path) -> None:
    shared_path = tmp_path / "shared_market.csv"
    venues_path = tmp_path / "venues.json"
    output_dir = tmp_path / "audit_out"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC"),
            "close": [100.0, 101.0, 102.0],
        }
    ).to_csv(shared_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-idempotent-audit-btcusdt",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "window": {"start": "2024-01-01", "end": "2024-01-03"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    first = audit_sandbox_archive_descriptors(
        venues_path,
        output_dir=output_dir,
        shared_market_data_path=shared_path,
    )
    second = audit_sandbox_archive_descriptors(
        venues_path,
        output_dir=output_dir,
        shared_market_data_path=shared_path,
    )

    assert second["audit_id"] == first["audit_id"]
    assert second["audit_dir"] == first["audit_dir"]
    assert Path(second["audit_json_path"]).exists()
    assert second["descriptors"][0]["status"] == "ready"
    assert "missing_ohlc_column:high" in second["descriptors"][0]["warning_reasons"]


def test_archive_descriptor_audit_requested_window_blocks_out_of_window_descriptor(tmp_path: Path) -> None:
    market_path = tmp_path / "okx_market.csv"
    venues_path = tmp_path / "venues.json"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC"),
            "close": [100.0, 101.0, 102.0, 103.0],
            "high": [101.0, 102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0, 102.0],
        }
    ).to_csv(market_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-jan-btcusdt-1h",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": market_path.name,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    baseline = audit_sandbox_archive_descriptors(venues_path, output_dir=tmp_path / "baseline_audit")
    payload = audit_sandbox_archive_descriptors(
        venues_path,
        output_dir=tmp_path / "requested_audit",
        requested_window=DataWindow("2024-02-01", "2024-02-01"),
    )
    row = payload["descriptors"][0]

    assert baseline["descriptors"][0]["status"] == "ready"
    assert baseline["requested_window_filter_applied"] is False
    assert payload["requested_window_filter_applied"] is True
    assert payload["requested_window_start"] == "2024-02-01"
    assert payload["requested_window_end"] == "2024-02-01"
    assert payload["ready_count"] == 0
    assert payload["blocked_count"] == 1
    assert payload["requested_window_row_count"] == 0
    assert row["descriptor_window_row_count"] == 4
    assert row["requested_window_row_count"] == 0
    assert row["requested_window_observed_start"] is None
    assert row["status"] == "blocked"
    assert "no_rows_in_requested_window" in row["blocker_reasons"]
    assert row["candidate_pack_eligible"] is False


def test_archive_coverage_matrix_groups_ready_blocked_and_mixed_buckets(tmp_path: Path) -> None:
    okx_ready = tmp_path / "okx_ready.csv"
    okx_old = tmp_path / "okx_old.csv"
    bybit_ready = tmp_path / "bybit_ready.csv"
    venues_path = tmp_path / "venues.json"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC"),
            "close": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
        }
    ).to_csv(okx_ready, index=False)
    pd.DataFrame({"timestamp": ["2023-12-31T00:00:00Z"], "close": [99.0]}).to_csv(okx_old, index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-02-01", periods=2, freq="15min", tz="UTC"),
            "close": [200.0, 201.0],
            "high": [201.0, 202.0],
            "low": [199.0, 200.0],
        }
    ).to_csv(bybit_ready, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-ready-btcusdt-1h",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": okx_ready.name,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                    {
                        "descriptor_id": "okx-old-btcusdt-1h",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": okx_old.name,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                    {
                        "descriptor_id": "bybit-ready-ethusdt-15m",
                        "venue": "bybit",
                        "symbol": "ETHUSDT",
                        "data_family": "kline",
                        "interval": "15m",
                        "data_path": bybit_ready.name,
                        "window": {"start": "2024-02-01", "end": "2024-02-01"},
                    },
                    {
                        "descriptor_id": "hyperliquid-missing-btc-1h",
                        "venue": "hyperliquid",
                        "symbol": "BTC",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": "missing_hyperliquid.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = summarize_sandbox_archive_coverage(venues_path, output_dir=tmp_path / "coverage")
    rows = {row["coverage_key"]: row for row in payload["coverage_rows"]}
    frame = pd.read_parquet(payload["coverage_parquet_path"])
    venue_gap_frame = pd.read_parquet(payload["venue_expansion_gaps_parquet_path"])
    catalog = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_count"] == 4
    assert payload["ready_descriptor_count"] == 2
    assert payload["blocked_descriptor_count"] == 2
    assert payload["coverage_bucket_count"] == 3
    assert payload["ready_bucket_count"] == 1
    assert payload["blocked_bucket_count"] == 1
    assert payload["mixed_bucket_count"] == 1
    assert payload["venue_expansion_target_venues"] == ["okx", "bybit", "hyperliquid"]
    assert payload["venue_expansion_gap_row_count"] == 6
    assert payload["venue_expansion_ready_target_count"] == 1
    assert payload["venue_expansion_blocked_target_count"] == 1
    assert payload["venue_expansion_mixed_target_count"] == 1
    assert payload["venue_expansion_missing_target_count"] == 3
    assert payload["venue_expansion_status_counts"] == {
        "blocked": 1,
        "missing_archive_descriptor": 3,
        "mixed": 1,
        "ready": 1,
    }
    assert payload["venue_expansion_action_counts"] == {
        "add_archive_descriptor_for_target_venue": 3,
        "repair_blocked_archive_bucket": 1,
        "repair_blocked_descriptors_or_use_ready_bucket": 1,
        "use_ready_archive_bucket": 1,
    }
    assert Path(payload["coverage_json_path"]).exists()
    assert Path(payload["coverage_parquet_path"]).exists()
    assert Path(payload["venue_expansion_gaps_parquet_path"]).exists()
    okx_bucket = rows["okx|BTCUSDT|kline|1h"]
    assert okx_bucket["status"] == "mixed"
    assert okx_bucket["descriptor_count"] == 2
    assert okx_bucket["ready_descriptor_count"] == 1
    assert okx_bucket["blocked_descriptor_count"] == 1
    assert okx_bucket["descriptor_window_row_count"] == 3
    assert okx_bucket["ready_window_row_count"] == 3
    assert okx_bucket["declared_window_start"] == "2024-01-01"
    assert okx_bucket["observed_window_start"].startswith("2024-01-01")
    assert okx_bucket["blocker_reason_counts"] == {"no_normalized_2024_plus_rows": 1}
    assert rows["bybit|ETHUSDT|kline|15m"]["status"] == "ready"
    assert rows["hyperliquid|BTC|kline|1h"]["blocker_reason_counts"] == {"data_path_not_found": 1}
    assert set(frame["coverage_key"]) == set(rows)
    assert set(frame["candidate_pack_eligible"]) == {False}
    gap_rows = {
        (
            row["market_symbol_key"],
            row["data_family"],
            row["interval"],
            row["target_venue"],
        ): row
        for row in payload["venue_expansion_gap_rows"]
    }
    assert set(venue_gap_frame["target_venue"]) == {"okx", "bybit", "hyperliquid"}
    assert set(venue_gap_frame["candidate_pack_eligible"]) == {False}
    assert (
        gap_rows[("BTC", "kline", "1h", "okx")]["target_action"]
        == "repair_blocked_descriptors_or_use_ready_bucket"
    )
    assert gap_rows[("BTC", "kline", "1h", "okx")]["observed_symbols"] == [
        "BTC",
        "BTCUSDT",
    ]
    assert gap_rows[("BTC", "kline", "1h", "bybit")]["target_missing"] is True
    assert (
        gap_rows[("BTC", "kline", "1h", "bybit")]["target_action"]
        == "add_archive_descriptor_for_target_venue"
    )
    assert gap_rows[("BTC", "kline", "1h", "hyperliquid")]["target_status"] == "blocked"
    assert gap_rows[("ETH", "kline", "15m", "bybit")]["target_status"] == "ready"
    assert gap_rows[("ETH", "kline", "15m", "okx")]["target_missing"] is True
    assert catalog["artifact_kind_counts"]["archive_coverage_matrix"] == 1


def test_archive_coverage_matrix_aggregates_container_member_metadata(tmp_path: Path) -> None:
    first_zip = tmp_path / "hyperliquid_BTC_trade_a.zip"
    second_zip = tmp_path / "hyperliquid_BTC_trade_b.zip"
    venues_path = tmp_path / "venues.json"
    with zipfile.ZipFile(first_zip, "w") as archive:
        archive.writestr("first/b.jsonl", json.dumps({"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"}))
        archive.writestr("first/a.jsonl", json.dumps({"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"}))
    with zipfile.ZipFile(second_zip, "w") as archive:
        archive.writestr("second/a.jsonl", json.dumps({"time": "2024-01-02T00:00:00Z", "px": "102.0", "sz": "4.0"}))
        archive.writestr("second/ignored.ndjson", json.dumps({"time": "2024-01-02T00:01:00Z", "px": "999.0"}))
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "hyperliquid-container-coverage-a",
                        "venue": "hyperliquid",
                        "symbol": "BTC",
                        "data_family": "trade",
                        "data_path": first_zip.name,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                    {
                        "descriptor_id": "hyperliquid-container-coverage-b",
                        "venue": "hyperliquid",
                        "symbol": "BTC",
                        "data_family": "trade",
                        "data_path": second_zip.name,
                        "window": {"start": "2024-01-02", "end": "2024-01-02"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = summarize_sandbox_archive_coverage(venues_path, output_dir=tmp_path / "coverage")
    row = payload["coverage_rows"][0]
    parquet = pd.read_parquet(payload["coverage_parquet_path"]).iloc[0]

    assert row["coverage_key"] == "hyperliquid|BTC|trade|na"
    assert row["status"] == "ready"
    assert row["container_kinds"] == ["zip"]
    assert row["selected_member_suffixes"] == [".jsonl"]
    assert row["container_descriptor_count"] == 2
    assert row["ready_container_descriptor_count"] == 2
    assert row["selected_member_count"] == 3
    assert row["ready_selected_member_count"] == 3
    assert row["loadable_member_count"] == 4
    assert row["selected_member_suffix_counts"] == {".jsonl": 2}
    assert row["available_member_suffix_counts"] == {".jsonl": 3, ".ndjson": 1}
    assert row["selected_member_name_sample"] == ["first/a.jsonl", "first/b.jsonl", "second/a.jsonl"]
    assert json.loads(parquet["container_kinds"]) == ["zip"]
    assert json.loads(parquet["selected_member_suffix_counts"]) == {".jsonl": 2}
    assert json.loads(parquet["available_member_suffix_counts"])[".jsonl"] == 3


def test_archive_coverage_matrix_aggregates_requested_window_readiness(tmp_path: Path) -> None:
    jan_path = tmp_path / "okx_jan.csv"
    feb_path = tmp_path / "okx_feb.csv"
    venues_path = tmp_path / "venues.json"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC"),
            "close": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
        }
    ).to_csv(jan_path, index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-02-01", periods=2, freq="1h", tz="UTC"),
            "close": [110.0, 111.0],
            "high": [111.0, 112.0],
            "low": [109.0, 110.0],
        }
    ).to_csv(feb_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-jan-btcusdt-1h",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": jan_path.name,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                    {
                        "descriptor_id": "okx-feb-btcusdt-1h",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": feb_path.name,
                        "window": {"start": "2024-02-01", "end": "2024-02-01"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = summarize_sandbox_archive_coverage(
        venues_path,
        output_dir=tmp_path / "coverage",
        requested_window=DataWindow("2024-02-01", "2024-02-01"),
    )
    row = payload["coverage_rows"][0]

    assert payload["requested_window_filter_applied"] is True
    assert payload["requested_window_start"] == "2024-02-01"
    assert payload["requested_window_end"] == "2024-02-01"
    assert payload["ready_descriptor_count"] == 1
    assert payload["blocked_descriptor_count"] == 1
    assert payload["requested_window_row_count"] == 2
    assert row["coverage_key"] == "okx|BTCUSDT|kline|1h"
    assert row["status"] == "mixed"
    assert row["descriptor_count"] == 2
    assert row["ready_descriptor_count"] == 1
    assert row["blocked_descriptor_count"] == 1
    assert row["requested_window_filter_applied"] is True
    assert row["requested_window_row_count"] == 2
    assert row["ready_requested_window_row_count"] == 2
    assert row["requested_window_observed_start"].startswith("2024-02-01")
    assert row["blocker_reason_counts"] == {"no_rows_in_requested_window": 1}
    assert row["candidate_pack_eligible"] is False


def test_archive_manifest_builder_discovery_bound_is_deterministic(tmp_path: Path) -> None:
    archive_root = tmp_path / "archives"
    archive_root.mkdir()
    for index, name in enumerate(("00_first.csv", "01_second.csv", "02_third.csv")):
        pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC"),
                "close": [100.0 + index, 101.0 + index, 102.0 + index],
                "high": [101.0 + index, 102.0 + index, 103.0 + index],
                "low": [99.0 + index, 100.0 + index, 101.0 + index],
            }
        ).to_csv(archive_root / name, index=False)

    payload = build_sandbox_archive_manifest(
        archive_root,
        output_dir=tmp_path / "manifest_out",
        venue="okx",
        symbol="BTCUSDT",
        data_family="kline",
        interval="1h",
        max_files=2,
    )
    source_names = [Path(str(row["source_path"])).name for row in payload["files"]]

    assert payload["file_count"] == 2
    assert payload["descriptor_count"] == 2
    assert payload["truncated"] is True
    assert source_names == ["00_first.csv", "01_second.csv"]


def test_global_leaderboard_discovery_bound_is_deterministic(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    first_strategy = StrategyCatalogRow(
        hypothesis_id="bounded-first-run",
        family="bounded_leaderboard_family",
        source_id="leaderboard-bound",
        signal_column="fallback_signal",
        side="long",
    )
    second_strategy = StrategyCatalogRow(
        hypothesis_id="bounded-second-run",
        family="bounded_leaderboard_family",
        source_id="leaderboard-bound",
        signal_column="fallback_signal",
        side="long",
    )
    run_sandbox_sweep(
        spec=_spec("00-first-run"),
        market_frame=_market_frame(),
        strategies=[first_strategy],
        venues=[_venue()],
        output_root=runs_root,
    )
    run_sandbox_sweep(
        spec=_spec("01-second-run"),
        market_frame=_market_frame(),
        strategies=[second_strategy],
        venues=[_venue()],
        output_root=runs_root,
    )

    payload = build_sandbox_global_leaderboard(runs_root, output_dir=tmp_path / "leaderboard", max_runs=1)
    top_ids = {row["hypothesis_id"] for row in payload["top_hypotheses"]}

    assert payload["run_manifest_count"] == 1
    assert payload["source_run_count"] == 1
    assert payload["truncated"] is True
    assert top_ids == {"bounded-first-run"}


def test_archive_manifest_builder_materializes_loadable_multi_venue_manifest(tmp_path: Path) -> None:
    archive_root = tmp_path / "archives"
    okx_dir = archive_root / "okx" / "kline"
    bybit_dir = archive_root / "bybit" / "klines"
    hyperliquid_dir = archive_root / "hyperliquid"
    okx_dir.mkdir(parents=True)
    bybit_dir.mkdir(parents=True)
    hyperliquid_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "timestamp": [
                "2023-12-31T00:00:00Z",
                "2024-01-01T00:00:00Z",
                "2024-01-02T00:00:00Z",
                "2024-01-03T00:00:00Z",
            ],
            "close": [99.0, 100.0, 101.0, 102.0],
            "high": [100.0, 101.0, 102.0, 103.0],
            "low": [98.0, 99.0, 100.0, 101.0],
        }
    ).to_csv(okx_dir / "BTCUSDT-1h-kline.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-02-01", periods=4, freq="15min", tz="UTC"),
            "close": [200.0, 201.0, 202.0, 203.0],
            "high": [201.0, 202.0, 203.0, 204.0],
            "low": [199.0, 200.0, 201.0, 202.0],
        }
    ).to_csv(bybit_dir / "ETHUSDT_15m_kline.csv", index=False)
    pd.DataFrame({"timestamp": ["2023-12-31T00:00:00Z"], "close": [10.0]}).to_csv(
        hyperliquid_dir / "BTC_1h_kline.csv",
        index=False,
    )
    (archive_root / "notes.txt").write_text("not market data", encoding="utf-8")
    (okx_dir / "bad.csv").write_text("timestamp,not_close\n2024-01-01T00:00:00Z,1\n", encoding="utf-8")

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    manifest_payload = json.loads(Path(payload["venue_archive_manifest_path"]).read_text(encoding="utf-8"))
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    catalog = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")
    rows = pd.read_parquet(payload["build_report_parquet_path"])
    descriptor_payloads = {row["venue"]: row for row in manifest_payload["venue_archives"]}
    included_rows = rows[rows["status"] == "included"]

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_count"] == 2
    assert payload["skipped_count"] == 3
    assert Path(payload["venue_archive_manifest_path"]).exists()
    assert Path(payload["build_report_json_path"]).exists()
    assert Path(payload["build_report_parquet_path"]).exists()
    assert {descriptor.venue for descriptor in descriptors} == {"okx", "bybit"}
    assert {descriptor.symbol for descriptor in descriptors} == {"BTCUSDT", "ETHUSDT"}
    assert {descriptor.interval for descriptor in descriptors} == {"1h", "15m"}
    assert all(descriptor.window.start.isoformat() >= "2024-01-01" for descriptor in descriptors)
    assert all(descriptor.source_integrity["sha256"] for descriptor in descriptors)
    assert descriptor_payloads["okx"]["source_integrity"]["sha256"] == _sha256(okx_dir / "BTCUSDT-1h-kline.csv")
    assert descriptor_payloads["okx"]["source_integrity"]["byte_size"] == (okx_dir / "BTCUSDT-1h-kline.csv").stat().st_size
    assert set(included_rows["source_sha256"].dropna()) == {
        _sha256(okx_dir / "BTCUSDT-1h-kline.csv"),
        _sha256(bybit_dir / "ETHUSDT_15m_kline.csv"),
    }
    assert int(rows["source_byte_size"].min()) > 0
    assert audit["ready_count"] == 2
    assert catalog["artifact_kind_counts"]["archive_manifest"] == 1
    assert catalog["artifact_kind_counts"]["archive_manifest_build_report"] == 1
    assert set(rows["status"]) == {"included", "skipped"}
    assert any("no_normalized_2024_plus_rows" in reasons for reasons in rows["skip_reasons"])
    assert any("unsupported_suffix" in reasons for reasons in rows["skip_reasons"])
    assert any("load_error:ValueError" in reasons for reasons in rows["skip_reasons"])


def test_archive_manifest_builder_includes_gzip_venue_export(tmp_path: Path) -> None:
    archive_root = tmp_path / "gzip_archives"
    bybit_dir = archive_root / "bybit" / "klines"
    bybit_dir.mkdir(parents=True)
    market_path = bybit_dir / "ETHUSDT_15m_kline.csv.gz"
    pd.DataFrame(
        {
            "startTime": [1706745600000, 1706746500000],
            "openPrice": ["200.0", "201.0"],
            "highPrice": ["202.0", "203.0"],
            "lowPrice": ["199.0", "200.0"],
            "closePrice": ["201.0", "202.0"],
            "volume": ["20.0", "21.0"],
        }
    ).to_csv(market_path, index=False, compression="gzip")

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    rows = pd.read_parquet(payload["build_report_parquet_path"])
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["venue_counts"] == {"bybit": 1}
    assert descriptors[0].venue == "bybit"
    assert descriptors[0].symbol == "ETHUSDT"
    assert descriptors[0].interval == "15m"
    assert descriptors[0].source_integrity["sha256"] == _sha256(market_path)
    assert descriptors[0].source_integrity["byte_size"] == market_path.stat().st_size
    assert set(rows["source_suffix"]) == {".csv.gz"}
    assert set(rows["status"]) == {"included"}
    assert audit["ready_count"] == 1
    assert audit["blocked_count"] == 0


def test_archive_manifest_builder_includes_gzip_ndjson_export(tmp_path: Path) -> None:
    archive_root = tmp_path / "ndjson_archives"
    hyperliquid_dir = archive_root / "hyperliquid" / "trades"
    hyperliquid_dir.mkdir(parents=True)
    market_path = hyperliquid_dir / "BTC_trade.ndjson.gz"
    rows = [
        {"time": "2023-12-31T23:59:00Z", "px": "99.0", "sz": "1.0"},
        {"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
        {"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
    ]
    with gzip.open(market_path, mode="wt", encoding="utf-8") as handle:
        handle.write("\n".join(json.dumps(row) for row in rows))

    payload = build_sandbox_archive_manifest(
        archive_root,
        output_dir=tmp_path / "manifest_out",
        venue="hyperliquid",
        symbol="BTC",
        data_family="trade",
    )
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    rows = pd.read_parquet(payload["build_report_parquet_path"])
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["venue_counts"] == {"hyperliquid": 1}
    assert descriptors[0].venue == "hyperliquid"
    assert descriptors[0].symbol == "BTC"
    assert descriptors[0].data_family == "trade"
    assert descriptors[0].source_integrity["sha256"] == _sha256(market_path)
    assert descriptors[0].source_integrity["byte_size"] == market_path.stat().st_size
    assert set(rows["source_suffix"]) == {".ndjson.gz"}
    assert set(rows["status"]) == {"included"}
    assert audit["ready_count"] == 1
    assert audit["blocked_count"] == 0


def test_archive_manifest_builder_includes_numeric_timestamp_millisecond_exports(tmp_path: Path) -> None:
    archive_root = tmp_path / "numeric_timestamp_archives"
    archive_root.mkdir()
    market_path = archive_root / "okx_BTCUSDT_1h_kline.csv"
    pd.DataFrame(
        {
            "timestamp": [1704067200000, 1704070800000],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
        }
    ).to_csv(market_path, index=False)

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    rows = pd.read_parquet(payload["build_report_parquet_path"])

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert descriptors[0].venue == "okx"
    assert descriptors[0].symbol == "BTCUSDT"
    assert descriptors[0].window.start.isoformat() == "2024-01-01"
    assert descriptors[0].window.end.isoformat() == "2024-01-01"
    assert set(rows["status"]) == {"included"}
    assert set(rows["window_start"]) == {"2024-01-01"}
    assert set(rows["window_end"]) == {"2024-01-01"}


def test_archive_manifest_builder_infers_identity_from_headered_zip_content(tmp_path: Path) -> None:
    archive_root = tmp_path / "zip_archives"
    archive_root.mkdir()
    zip_path = archive_root / "generic_market_export.zip"
    frame = pd.DataFrame(
        {
            "exchange": ["okx", "okx"],
            "instId": ["BTC-USDT-SWAP", "BTC-USDT-SWAP"],
            "bar": ["1H", "1H"],
            "data_family": ["kline", "kline"],
            "ts": [1704067200000, 1704070800000],
            "o": ["100.0", "101.0"],
            "h": ["102.0", "103.0"],
            "l": ["99.0", "100.0"],
            "c": ["101.0", "102.0"],
            "vol": ["10.0", "11.0"],
        }
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/market_export.csv", frame.to_csv(index=False))

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    rows = pd.read_parquet(payload["build_report_parquet_path"])
    included = rows[rows["status"] == "included"].iloc[0]

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert descriptors[0].venue == "okx"
    assert descriptors[0].symbol == "BTCUSDT"
    assert descriptors[0].interval == "1h"
    assert descriptors[0].data_family == "kline"
    assert descriptors[0].source_integrity["sha256"] == _sha256(zip_path)
    assert set(rows["source_suffix"]) == {".zip"}
    assert included["venue_inference_source"] == "content"
    assert included["symbol_inference_source"] == "content"
    assert included["interval_inference_source"] == "content"
    assert included["data_family_inference_source"] == "content"
    assert json.loads(included["alias_columns"])["timestamp"] == "ts"


def test_archive_manifest_builder_includes_zip_ndjson_member(tmp_path: Path) -> None:
    archive_root = tmp_path / "zip_ndjson_archives"
    archive_root.mkdir()
    zip_path = archive_root / "generic_stream_export.zip"
    rows = [
        {
            "source": "hyperliquid",
            "coin": "BTC",
            "channel": "trades",
            "time": "2023-12-31T23:59:00Z",
            "px": "99.0",
            "sz": "1.0",
        },
        {
            "source": "hyperliquid",
            "coin": "BTC",
            "channel": "trades",
            "time": "2024-01-01T00:00:00Z",
            "px": "100.0",
            "sz": "2.0",
        },
        {
            "source": "hyperliquid",
            "coin": "BTC",
            "channel": "trades",
            "time": "2024-01-01T00:01:00Z",
            "px": "101.0",
            "sz": "3.0",
        },
    ]
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/trades.ndjson", "\n".join(json.dumps(row) for row in rows))

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    build_rows = pd.read_parquet(payload["build_report_parquet_path"])
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    included = build_rows[build_rows["status"] == "included"].iloc[0]

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert descriptors[0].venue == "hyperliquid"
    assert descriptors[0].symbol == "BTC"
    assert descriptors[0].data_family == "trade"
    assert descriptors[0].source_integrity["sha256"] == _sha256(zip_path)
    assert set(build_rows["source_suffix"]) == {".zip"}
    assert included["venue_inference_source"] == "content"
    assert included["symbol_inference_source"] == "content"
    assert included["data_family_inference_source"] == "content"
    assert audit["ready_count"] == 1
    assert audit["blocked_count"] == 0


def test_market_frame_loader_reads_zip_gzip_jsonl_member(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_BTC_trades.zip"
    rows = [
        {"time": "2023-12-31T23:59:00Z", "px": "99.0", "sz": "1.0"},
        {"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
        {"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
    ]
    payload = gzip.compress("\n".join(json.dumps(row) for row in rows).encode("utf-8"))
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/BTC_trades.jsonl.gz", payload)

    frame = load_market_frame(zip_path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert list(frame["volume"]) == [2.0, 3.0]
    assert frame["timestamp"].min().date().isoformat() == "2024-01-01"


def test_market_frame_loader_concatenates_zip_jsonl_members(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_BTC_trades.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "chunks/b.jsonl",
            json.dumps({"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"}),
        )
        archive.writestr(
            "chunks/a.jsonl",
            json.dumps({"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"}),
        )

    frame = load_market_frame(zip_path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert list(frame["volume"]) == [2.0, 3.0]


def test_market_frame_loader_records_zip_container_member_metadata(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_BTC_trades.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("chunks/b.jsonl", json.dumps({"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"}))
        archive.writestr("chunks/a.jsonl", json.dumps({"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"}))
        archive.writestr("chunks/ignored.ndjson", json.dumps({"time": "2024-01-01T00:02:00Z", "px": "999.0"}))
        archive.writestr("README.txt", "not market data")

    frame = load_market_frame(zip_path)
    metadata = frame.attrs["sandbox_normalization_metadata"]
    container_metadata = metadata["container_member_metadata"]

    assert list(frame["close"]) == [100.0, 101.0]
    assert metadata["container_member_count"] == 2
    assert container_metadata["container_kind"] == "zip"
    assert container_metadata["selected_member_suffix"] == ".jsonl"
    assert container_metadata["selected_member_count"] == 2
    assert container_metadata["selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert container_metadata["available_member_suffix_counts"][".jsonl"] == 2
    assert container_metadata["available_member_suffix_counts"][".ndjson"] == 1
    assert container_metadata["loadable_member_count"] == 3


def test_market_frame_loader_merges_multimember_l2_source_transformations(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_BTC_l2Book.zip"
    rows = [
        {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1704067200000,
                "levels": [[{"px": "100.0", "sz": "5.0", "n": 1}], [{"px": "101.0", "sz": "4.0", "n": 1}]],
            },
        },
        {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1704067260000,
                "levels": [[{"px": "101.0", "sz": "6.0", "n": 1}], [{"px": "102.0", "sz": "5.0", "n": 1}]],
            },
        },
    ]
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("chunks/a.jsonl", json.dumps(rows[0]))
        archive.writestr("chunks/b.jsonl", json.dumps(rows[1]))

    frame = load_market_frame(zip_path)
    metadata = frame.attrs["sandbox_normalization_metadata"]

    assert list(frame["close"]) == [100.5, 101.5]
    assert metadata["source_transformations"]["hyperliquid_l2_levels"]["row_count"] == 2


def test_archive_manifest_builder_includes_zip_gzip_jsonl_member(tmp_path: Path) -> None:
    archive_root = tmp_path / "zip_gzip_member_archives"
    archive_root.mkdir()
    zip_path = archive_root / "generic_stream_export.zip"
    rows = [
        {
            "source": "hyperliquid",
            "coin": "BTC",
            "channel": "trades",
            "time": "2024-01-01T00:00:00Z",
            "px": "100.0",
            "sz": "2.0",
        },
        {
            "source": "hyperliquid",
            "coin": "BTC",
            "channel": "trades",
            "time": "2024-01-01T00:01:00Z",
            "px": "101.0",
            "sz": "3.0",
        },
    ]
    payload = gzip.compress("\n".join(json.dumps(row) for row in rows).encode("utf-8"))
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/trades.jsonl.gz", payload)

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    build_rows = pd.read_parquet(payload["build_report_parquet_path"])
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    included = build_rows[build_rows["status"] == "included"].iloc[0]

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert descriptors[0].venue == "hyperliquid"
    assert descriptors[0].symbol == "BTC"
    assert descriptors[0].data_family == "trade"
    assert descriptors[0].source_integrity["sha256"] == _sha256(zip_path)
    assert set(build_rows["source_suffix"]) == {".zip"}
    assert included["data_family_inference_source"] == "content"
    assert audit["ready_count"] == 1
    assert audit["blocked_count"] == 0


def test_archive_manifest_builder_counts_zip_multimember_jsonl_export(tmp_path: Path) -> None:
    archive_root = tmp_path / "zip_multimember_archives"
    archive_root.mkdir()
    zip_path = archive_root / "generic_stream_export.zip"
    rows = [
        {"source": "hyperliquid", "coin": "BTC", "channel": "trades", "time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
        {"source": "hyperliquid", "coin": "BTC", "channel": "trades", "time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
    ]
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("chunks/b.jsonl", json.dumps(rows[1]))
        archive.writestr("chunks/a.jsonl", json.dumps(rows[0]))

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    build_rows = pd.read_parquet(payload["build_report_parquet_path"])
    included = build_rows[build_rows["status"] == "included"].iloc[0]

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert included["normalized_row_count"] == 2
    assert included["window_start"] == "2024-01-01"
    assert included["window_end"] == "2024-01-01"


def test_archive_manifest_builder_records_container_member_metadata(tmp_path: Path) -> None:
    archive_root = tmp_path / "zip_container_metadata_archives"
    archive_root.mkdir()
    zip_path = archive_root / "generic_stream_export.zip"
    rows = [
        {"source": "hyperliquid", "coin": "BTC", "channel": "trades", "time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
        {"source": "hyperliquid", "coin": "BTC", "channel": "trades", "time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
    ]
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("chunks/b.jsonl", json.dumps(rows[1]))
        archive.writestr("chunks/a.jsonl", json.dumps(rows[0]))
        archive.writestr("chunks/ignored.ndjson", json.dumps({**rows[0], "px": "999.0"}))

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    report = json.loads(Path(payload["build_report_json_path"]).read_text(encoding="utf-8"))
    included_json = [row for row in report["files"] if row["status"] == "included"][0]
    build_rows = pd.read_parquet(payload["build_report_parquet_path"])
    included_parquet = build_rows[build_rows["status"] == "included"].iloc[0]

    assert payload["descriptor_count"] == 1
    assert included_json["container_kind"] == "zip"
    assert included_json["selected_member_suffix"] == ".jsonl"
    assert included_json["selected_member_count"] == 2
    assert included_json["selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert included_json["available_member_suffix_counts"][".jsonl"] == 2
    assert included_json["available_member_suffix_counts"][".ndjson"] == 1
    assert included_parquet["container_kind"] == "zip"
    assert included_parquet["selected_member_suffix"] == ".jsonl"
    assert included_parquet["selected_member_count"] == 2
    assert json.loads(included_parquet["selected_member_name_sample"]) == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert json.loads(included_parquet["available_member_suffix_counts"])[".jsonl"] == 2


def test_market_frame_loader_reads_tar_jsonl_member(tmp_path: Path) -> None:
    member_path = tmp_path / "BTC_trade.jsonl"
    member_path.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"time": "2023-12-31T23:59:00Z", "px": "99.0", "sz": "1.0"},
                {"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
                {"time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
            ]
        ),
        encoding="utf-8",
    )
    tar_path = tmp_path / "hyperliquid_BTC_trade.tar.gz"
    with tarfile.open(tar_path, mode="w:gz") as archive:
        archive.add(member_path, arcname="nested/BTC_trade.jsonl")

    frame = load_market_frame(tar_path)

    assert list(frame["close"]) == [100.0, 101.0]
    assert list(frame["volume"]) == [2.0, 3.0]
    assert frame["timestamp"].min().date().isoformat() == "2024-01-01"


def test_market_frame_loader_concatenates_tar_csv_members(tmp_path: Path) -> None:
    first_member = tmp_path / "BTC_1h_a.csv"
    second_member = tmp_path / "BTC_1h_b.csv"
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "close": [100.0]}).to_csv(first_member, index=False)
    pd.DataFrame({"timestamp": ["2024-01-01T01:00:00Z"], "close": [101.0]}).to_csv(second_member, index=False)
    tar_path = tmp_path / "okx_BTCUSDT_1h_kline.tar"
    with tarfile.open(tar_path, mode="w") as archive:
        archive.add(second_member, arcname="chunks/b.csv")
        archive.add(first_member, arcname="chunks/a.csv")

    frame = load_market_frame(tar_path)

    assert list(frame["close"]) == [100.0, 101.0]


def test_market_frame_loader_records_tar_container_member_metadata(tmp_path: Path) -> None:
    tar_path = tmp_path / "okx_BTCUSDT_1h_kline.tar"
    payloads = {
        "chunks/b.csv.gz": gzip.compress(
            pd.DataFrame({"timestamp": ["2024-01-01T01:00:00Z"], "close": [101.0]}).to_csv(index=False).encode("utf-8")
        ),
        "chunks/a.csv.gz": gzip.compress(
            pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "close": [100.0]}).to_csv(index=False).encode("utf-8")
        ),
    }
    ignored_payload = json.dumps({"rows": [{"timestamp": "2024-01-01T02:00:00Z", "close": 999.0}]}).encode("utf-8")
    with tarfile.open(tar_path, mode="w") as archive:
        for name, payload in payloads.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, fileobj=BytesIO(payload))
        info = tarfile.TarInfo("chunks/ignored.json")
        info.size = len(ignored_payload)
        archive.addfile(info, fileobj=BytesIO(ignored_payload))

    frame = load_market_frame(tar_path)
    metadata = frame.attrs["sandbox_normalization_metadata"]["container_member_metadata"]

    assert list(frame["close"]) == [100.0, 101.0]
    assert metadata["container_kind"] == "tar"
    assert metadata["selected_member_suffix"] == ".csv.gz"
    assert metadata["selected_member_count"] == 2
    assert metadata["selected_member_name_sample"] == ["chunks/a.csv.gz", "chunks/b.csv.gz"]
    assert metadata["available_member_suffix_counts"][".csv.gz"] == 2
    assert metadata["available_member_suffix_counts"][".json"] == 1


def test_market_frame_loader_prefers_csv_gzip_tar_member(tmp_path: Path) -> None:
    csv_payload = gzip.compress(
        pd.DataFrame(
            {
                "timestamp": ["2024-01-01T00:00:00Z"],
                "close": [100.0],
            }
        ).to_csv(index=False).encode("utf-8")
    )
    json_member = tmp_path / "BTC_1h.json"
    json_member.write_text(
        json.dumps({"rows": [{"timestamp": "2024-01-01T00:00:00Z", "close": 999.0}]}),
        encoding="utf-8",
    )
    tar_path = tmp_path / "okx_BTCUSDT_1h_kline.tar"
    with tarfile.open(tar_path, mode="w") as archive:
        archive.add(json_member, arcname="nested/BTC_1h.json")
        info = tarfile.TarInfo("nested/BTC_1h.csv.gz")
        info.size = len(csv_payload)
        archive.addfile(info, fileobj=BytesIO(csv_payload))

    frame = load_market_frame(tar_path)

    assert list(frame["close"]) == [100.0]


def test_market_frame_loader_prefers_csv_tar_member(tmp_path: Path) -> None:
    csv_member = tmp_path / "BTC_1h.csv"
    json_member = tmp_path / "BTC_1h.json"
    pd.DataFrame(
        {
            "timestamp": ["2024-01-01T00:00:00Z"],
            "close": [100.0],
        }
    ).to_csv(csv_member, index=False)
    json_member.write_text(
        json.dumps({"rows": [{"timestamp": "2024-01-01T00:00:00Z", "close": 999.0}]}),
        encoding="utf-8",
    )
    tar_path = tmp_path / "okx_BTCUSDT_1h_kline.tgz"
    with tarfile.open(tar_path, mode="w:gz") as archive:
        archive.add(json_member, arcname="nested/BTC_1h.json")
        archive.add(csv_member, arcname="nested/BTC_1h.csv")

    frame = load_market_frame(tar_path)

    assert list(frame["close"]) == [100.0]


def test_archive_manifest_builder_includes_tar_jsonl_member(tmp_path: Path) -> None:
    archive_root = tmp_path / "tar_archives"
    hyperliquid_dir = archive_root / "hyperliquid"
    hyperliquid_dir.mkdir(parents=True)
    member_path = tmp_path / "BTC_trade.jsonl"
    member_path.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"source": "hyperliquid", "coin": "BTC", "channel": "trades", "time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
                {"source": "hyperliquid", "coin": "BTC", "channel": "trades", "time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "3.0"},
            ]
        ),
        encoding="utf-8",
    )
    tar_path = hyperliquid_dir / "BTC_trade.tar.gz"
    with tarfile.open(tar_path, mode="w:gz") as archive:
        archive.add(member_path, arcname="nested/BTC_trade.jsonl")

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    build_rows = pd.read_parquet(payload["build_report_parquet_path"])
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    included = build_rows[build_rows["status"] == "included"].iloc[0]

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert descriptors[0].venue == "hyperliquid"
    assert descriptors[0].symbol == "BTC"
    assert descriptors[0].data_family == "trade"
    assert descriptors[0].source_integrity["sha256"] == _sha256(tar_path)
    assert set(build_rows["source_suffix"]) == {".tar.gz"}
    assert included["data_family_inference_source"] == "path"
    assert audit["ready_count"] == 1
    assert audit["blocked_count"] == 0


def test_archive_manifest_builder_includes_l2_bid_ask_midpoint_export(tmp_path: Path) -> None:
    archive_root = tmp_path / "book_archives"
    book_dir = archive_root / "hyperliquid" / "l2_book"
    book_dir.mkdir(parents=True)
    market_path = book_dir / "BTC_l2_book.csv"
    pd.DataFrame(
        {
            "time": ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"],
            "bestBidPx": ["100.0", "101.0"],
            "bestAskPx": ["101.0", "102.0"],
            "bidSize": ["5.0", "6.0"],
            "askSize": ["4.0", "5.0"],
            "venue": ["hyperliquid", "hyperliquid"],
        }
    ).to_csv(market_path, index=False)

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    build_rows = pd.read_parquet(payload["build_report_parquet_path"])
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    included = build_rows[build_rows["status"] == "included"].iloc[0]
    derived_columns = json.loads(included["derived_columns"])

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert descriptors[0].venue == "hyperliquid"
    assert descriptors[0].symbol == "BTC"
    assert descriptors[0].data_family == "l2_book"
    assert descriptors[0].source_integrity["sha256"] == _sha256(market_path)
    assert set(build_rows["source_suffix"]) == {".csv"}
    assert included["derived_count"] == 1
    assert derived_columns["close"] == {
        "method": "bid_ask_midpoint",
        "bid_column": "bestBidPx",
        "ask_column": "bestAskPx",
    }
    assert audit["ready_count"] == 1
    assert audit["blocked_count"] == 0


def test_archive_manifest_builder_includes_hyperliquid_l2_book_json_export(tmp_path: Path) -> None:
    archive_root = tmp_path / "archives"
    book_dir = archive_root / "hyperliquid" / "snapshots"
    book_dir.mkdir(parents=True)
    market_path = book_dir / "snapshot.json"
    market_path.write_text(
        json.dumps(
            {
                "channel": "l2Book",
                "data": [
                    {
                        "coin": "BTC",
                        "time": 1704067200000,
                        "levels": [
                            [{"px": "100.0", "sz": "5.0", "n": 2}],
                            [{"px": "101.0", "sz": "4.0", "n": 3}],
                        ],
                    },
                    {
                        "coin": "BTC",
                        "time": 1704067260000,
                        "levels": [
                            [{"px": "101.0", "sz": "6.0", "n": 1}],
                            [{"px": "102.0", "sz": "5.0", "n": 2}],
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    build_rows = pd.read_parquet(payload["build_report_parquet_path"])
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    included = build_rows[build_rows["status"] == "included"].iloc[0]
    source_transformations = json.loads(included["source_transformations"])
    derived_columns = json.loads(included["derived_columns"])

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 0
    assert descriptors[0].venue == "hyperliquid"
    assert descriptors[0].symbol == "BTC"
    assert descriptors[0].data_family == "l2_book"
    assert descriptors[0].source_integrity["sha256"] == _sha256(market_path)
    assert included["data_family_inference_source"] == "content"
    assert included["source_transformation_count"] == 1
    assert source_transformations["hyperliquid_l2_levels"] == {
        "method": "best_bid_ask_from_levels",
        "row_count": 2,
    }
    assert derived_columns["close"]["method"] == "bid_ask_midpoint"
    assert audit["ready_count"] == 1
    assert audit["blocked_count"] == 0


@pytest.mark.parametrize(
    ("venue_alias", "expected_venue"),
    [
        ("binance_um", "binance_usdm"),
        ("okex", "okx"),
        ("bybit_linear", "bybit"),
        ("hyperliquid_perp", "hyperliquid"),
    ],
)
def test_archive_manifest_builder_accepts_common_venue_override_aliases(
    tmp_path: Path,
    venue_alias: str,
    expected_venue: str,
) -> None:
    archive_root = tmp_path / "generic_drop"
    archive_root.mkdir()
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC"),
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
        }
    ).to_csv(archive_root / "market_export.csv", index=False)

    payload = build_sandbox_archive_manifest(
        archive_root,
        output_dir=tmp_path / "manifest_out",
        venue=venue_alias,
        symbol="BTCUSDT",
        data_family="kline",
        interval="1h",
    )
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    rows = pd.read_parquet(payload["build_report_parquet_path"])

    assert payload["descriptor_count"] == 1
    assert payload["venue_counts"] == {expected_venue: 1}
    assert descriptors[0].venue == expected_venue
    assert descriptors[0].to_payload()["candidate_pack_eligible"] is False
    assert set(rows["venue"]) == {expected_venue}
    assert set(rows["venue_inference_source"]) == {"override"}


def test_archive_manifest_builder_filters_files_outside_requested_window(tmp_path: Path) -> None:
    archive_root = tmp_path / "windowed_archives"
    archive_root.mkdir()
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-02-01", periods=3, freq="1h", tz="UTC"),
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
        }
    ).to_csv(archive_root / "in_window.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-06-01", periods=3, freq="1h", tz="UTC"),
            "open": [200.0, 201.0, 202.0],
            "high": [201.0, 202.0, 203.0],
            "low": [199.0, 200.0, 201.0],
            "close": [200.5, 201.5, 202.5],
        }
    ).to_csv(archive_root / "outside_window.csv", index=False)

    payload = build_sandbox_archive_manifest(
        archive_root,
        output_dir=tmp_path / "manifest_out",
        venue="okx",
        symbol="BTCUSDT",
        data_family="kline",
        interval="1h",
        requested_window=DataWindow("2024-02-01", "2024-02-28"),
    )
    descriptors = load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    rows = pd.read_parquet(payload["build_report_parquet_path"])
    skipped = rows[rows["status"] == "skipped"].iloc[0]

    assert payload["descriptor_count"] == 1
    assert payload["skipped_count"] == 1
    assert payload["requested_window_filter_applied"] is True
    assert payload["requested_window_start"] == "2024-02-01"
    assert payload["requested_window_end"] == "2024-02-28"
    assert descriptors[0].data_path.name == "in_window.csv"
    assert set(rows["requested_window_filter_applied"]) == {True}
    assert set(rows["requested_window_start"]) == {"2024-02-01"}
    assert "outside_requested_window" in skipped["skip_reasons"]
    assert skipped["normalized_row_count"] == 3
    assert skipped["window_start"].startswith("2024-06-01")
    assert set(rows["candidate_pack_eligible"]) == {False}


def test_archive_manifest_builder_records_venue_export_alias_normalization(tmp_path: Path) -> None:
    archive_root = tmp_path / "venue_exports"
    okx_dir = archive_root / "okx"
    bybit_dir = archive_root / "bybit"
    hyperliquid_dir = archive_root / "hyperliquid"
    okx_dir.mkdir(parents=True)
    bybit_dir.mkdir(parents=True)
    hyperliquid_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "ts": [1704067200000, 1704070800000],
            "o": ["100.0", "101.0"],
            "h": ["102.0", "103.0"],
            "l": ["99.0", "100.0"],
            "c": ["101.0", "102.0"],
        }
    ).to_csv(okx_dir / "BTCUSDT_1h_kline.csv", index=False)
    pd.DataFrame(
        {
            "startTime": [1706745600000, 1706746500000],
            "openPrice": ["200.0", "201.0"],
            "highPrice": ["202.0", "203.0"],
            "lowPrice": ["199.0", "200.0"],
            "closePrice": ["201.0", "202.0"],
        }
    ).to_csv(bybit_dir / "ETHUSDT_15m_kline.csv", index=False)
    (hyperliquid_dir / "BTC_trade.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"time": "2023-12-31T23:59:00Z", "px": "99.0", "sz": "1.0"},
                {"time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
            ]
        ),
        encoding="utf-8",
    )

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    build_rows = pd.read_parquet(payload["build_report_parquet_path"])
    audit_rows = pd.read_parquet(audit["audit_parquet_path"])

    assert payload["descriptor_count"] == 3
    assert set(build_rows["venue"]) == {"okx", "bybit", "hyperliquid"}
    assert build_rows["alias_count"].min() >= 2
    assert audit_rows["alias_count"].min() >= 2
    assert set(audit_rows["status"]) == {"ready"}
    assert set(audit_rows["candidate_pack_eligible"]) == {False}


def test_archive_manifest_builder_infers_identity_from_generic_content_columns(tmp_path: Path) -> None:
    archive_root = tmp_path / "generic_vendor_drop"
    archive_root.mkdir()
    pd.DataFrame(
        {
            "exchange": ["okx", "okx"],
            "instId": ["BTC-USDT-SWAP", "BTC-USDT-SWAP"],
            "bar": ["1H", "1H"],
            "channel": ["candles", "candles"],
            "ts": [1704067200000, 1704070800000],
            "o": ["100.0", "101.0"],
            "h": ["102.0", "103.0"],
            "l": ["99.0", "100.0"],
            "c": ["101.0", "102.0"],
        }
    ).to_csv(archive_root / "export_a.csv", index=False)
    pd.DataFrame(
        {
            "provider": ["bybit", "bybit"],
            "symbol": ["ETHUSDT", "ETHUSDT"],
            "interval": ["15", "15"],
            "type": ["kline", "kline"],
            "startTime": [1706745600000, 1706746500000],
            "openPrice": ["200.0", "201.0"],
            "highPrice": ["202.0", "203.0"],
            "lowPrice": ["199.0", "200.0"],
            "closePrice": ["201.0", "202.0"],
        }
    ).to_csv(archive_root / "export_b.csv", index=False)
    (archive_root / "export_c.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"source": "hyperliquid", "coin": "BTC", "channel": "trades", "time": "2024-01-01T00:00:00Z", "px": "100.0", "sz": "2.0"},
                {"source": "hyperliquid", "coin": "BTC", "channel": "trades", "time": "2024-01-01T00:01:00Z", "px": "101.0", "sz": "1.5"},
            ]
        ),
        encoding="utf-8",
    )

    payload = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = {
        (descriptor.venue, descriptor.symbol, descriptor.data_family, descriptor.interval): descriptor
        for descriptor in load_venue_archive_descriptors(payload["venue_archive_manifest_path"])
    }
    audit = audit_sandbox_archive_descriptors(payload["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    rows = {Path(str(row["source_path"])).name: row for row in payload["files"]}

    assert payload["descriptor_count"] == 3
    assert payload["skipped_count"] == 0
    assert ("okx", "BTCUSDT", "kline", "1h") in descriptors
    assert ("bybit", "ETHUSDT", "kline", "15m") in descriptors
    assert ("hyperliquid", "BTC", "trade", None) in descriptors
    assert rows["export_a.csv"]["venue_inference_source"] == "content"
    assert rows["export_a.csv"]["symbol_inference_source"] == "content"
    assert rows["export_a.csv"]["data_family_inference_source"] == "content"
    assert rows["export_a.csv"]["interval_inference_source"] == "content"
    assert rows["export_b.csv"]["interval_inference_source"] == "content"
    assert rows["export_c.jsonl"]["data_family_inference_source"] == "content"
    assert rows["export_c.jsonl"]["interval_inference_source"] == "missing"
    assert all(descriptor.source_integrity["sha256"] for descriptor in descriptors.values())
    assert audit["ready_count"] == 3
    assert audit["promotion_ready"] is False
    assert audit["candidate_pack_eligible"] is False


def test_archive_manifest_builder_supports_overrides_and_idempotent_preflight(tmp_path: Path) -> None:
    archive_root = tmp_path / "raw_vendor_drop"
    archive_root.mkdir()
    market_path = archive_root / "raw_market.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=3, freq="1h", tz="UTC"),
            "close": [100.0, 101.0, 102.0],
        }
    ).to_csv(market_path, index=False)

    first = build_sandbox_archive_manifest(
        archive_root,
        output_dir=tmp_path / "manifest_out",
        venue="hyperliquid",
        symbol="BTC",
        data_family="kline",
        interval="1h",
    )
    second = build_sandbox_archive_manifest(
        archive_root,
        output_dir=tmp_path / "manifest_out",
        venue="hyperliquid",
        symbol="BTC",
        data_family="kline",
        interval="1h",
    )
    descriptor = load_venue_archive_descriptors(second["venue_archive_manifest_path"])[0]
    second_source_sha256 = str(descriptor.source_integrity["sha256"])
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=3, freq="1h", tz="UTC"),
            "close": [100.0, 101.5, 102.0],
        }
    ).to_csv(market_path, index=False)
    third = build_sandbox_archive_manifest(
        archive_root,
        output_dir=tmp_path / "manifest_out",
        venue="hyperliquid",
        symbol="BTC",
        data_family="kline",
        interval="1h",
    )
    changed_descriptor = load_venue_archive_descriptors(third["venue_archive_manifest_path"])[0]

    assert second["manifest_id"] == first["manifest_id"]
    assert second["output_dir"] == first["output_dir"]
    assert second["descriptor_count"] == 1
    assert descriptor.venue == "hyperliquid"
    assert descriptor.symbol == "BTC"
    assert descriptor.interval == "1h"
    assert descriptor.data_path == market_path.resolve()
    assert second_source_sha256 == str(second["files"][0]["source_sha256"])
    assert second["files"][0]["status"] == "included"
    assert second["files"][0]["promotion_ready"] is False
    assert third["manifest_id"] != second["manifest_id"]
    assert changed_descriptor.descriptor_id == descriptor.descriptor_id
    assert changed_descriptor.source_integrity["sha256"] == _sha256(market_path)
    assert changed_descriptor.source_integrity["sha256"] != second_source_sha256


def test_preflight_records_container_member_metadata(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_BTC_trade.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "chunks/b.jsonl",
            json.dumps(
                {
                    "time": "2024-01-01T00:01:00Z",
                    "px": "101.0",
                    "sz": "3.0",
                    "fallback_signal": 1,
                    "quality": 0.8,
                }
            ),
        )
        archive.writestr(
            "chunks/a.jsonl",
            json.dumps(
                {
                    "time": "2024-01-01T00:00:00Z",
                    "px": "100.0",
                    "sz": "2.0",
                    "fallback_signal": 1,
                    "quality": 0.8,
                }
            ),
        )
        archive.writestr(
            "chunks/ignored.ndjson",
            json.dumps(
                {
                    "time": "2024-01-01T00:02:00Z",
                    "px": "999.0",
                    "fallback_signal": 1,
                    "quality": 0.8,
                }
            ),
        )
    descriptor = VenueArchiveDescriptor(
        descriptor_id="hyperliquid-preflight-container-btc",
        venue="hyperliquid",
        symbol="BTC",
        data_family="trade",
        data_path=zip_path,
        window=DataWindow("2024-01-01", "2024-01-01"),
    )
    spec = SandboxRunSpec(
        run_id="preflight-container-metadata",
        data_window=DataWindow("2024-01-01", "2024-01-01"),
        holding_periods=(1,),
        min_trades=1,
    )

    payload = preflight_sandbox_compatibility(
        spec=spec,
        strategies=[_strategy()],
        venues=[descriptor],
        output_dir=tmp_path / "preflight",
    )
    row = payload["rows"][0]
    parquet = pd.read_parquet(payload["preflight_parquet_path"]).iloc[0]

    assert payload["runnable_trial_estimate"] == 1
    assert row["status"] == "runnable"
    assert row["container_kind"] == "zip"
    assert row["selected_member_suffix"] == ".jsonl"
    assert row["selected_member_count"] == 2
    assert row["selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert row["available_member_suffix_counts"] == {".jsonl": 2, ".ndjson": 1}
    assert row["loadable_member_count"] == 3
    assert row["normalization"]["container_member_count"] == 2
    assert parquet["container_kind"] == "zip"
    assert parquet["selected_member_suffix"] == ".jsonl"
    assert parquet["selected_member_count"] == 2
    assert json.loads(parquet["selected_member_name_sample"]) == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert json.loads(parquet["available_member_suffix_counts"])[".ndjson"] == 1


def test_archive_audit_and_preflight_block_source_integrity_mismatch(tmp_path: Path) -> None:
    archive_root = tmp_path / "archives"
    okx_dir = archive_root / "okx"
    okx_dir.mkdir(parents=True)
    market_path = okx_dir / "BTCUSDT_1h_kline.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC"),
            "close": [100.0, 101.0, 102.0, 103.0],
            "fallback_signal": [1, 1, 1, 1],
            "quality": [0.8, 0.8, 0.8, 0.8],
        }
    ).to_csv(market_path, index=False)
    manifest = build_sandbox_archive_manifest(archive_root, output_dir=tmp_path / "manifest_out")
    descriptors = load_venue_archive_descriptors(manifest["venue_archive_manifest_path"])
    market_path.write_text(f"{market_path.read_text(encoding='utf-8')}\n", encoding="utf-8")
    spec = SandboxRunSpec(
        run_id="source-integrity-preflight",
        data_window=DataWindow("2024-01-01", "2024-01-02"),
        holding_periods=(1,),
        min_trades=1,
    )

    audit = audit_sandbox_archive_descriptors(manifest["venue_archive_manifest_path"], output_dir=tmp_path / "audit")
    preflight = preflight_sandbox_compatibility(
        spec=spec,
        strategies=[_strategy()],
        venues=descriptors,
        output_dir=tmp_path / "preflight",
    )
    shared_audit = audit_sandbox_archive_descriptors(
        manifest["venue_archive_manifest_path"],
        output_dir=tmp_path / "shared_audit",
        shared_market_data_path=market_path,
    )
    shared_preflight = preflight_sandbox_compatibility(
        spec=spec,
        strategies=[_strategy()],
        venues=descriptors,
        output_dir=tmp_path / "shared_preflight",
        shared_market_data_path=market_path,
    )

    assert audit["blocked_count"] == 1
    assert "source_integrity_sha256_mismatch" in audit["descriptors"][0]["blocker_reasons"]
    assert "source_integrity_byte_size_mismatch" in audit["descriptors"][0]["blocker_reasons"]
    assert preflight["runnable_trial_estimate"] == 0
    assert preflight["blocked_trial_estimate"] == 1
    assert preflight["rows"][0]["blocker_reasons"] == [
        "source_integrity_byte_size_mismatch",
        "source_integrity_sha256_mismatch",
    ]
    assert shared_audit["ready_count"] == 1
    assert shared_preflight["runnable_trial_estimate"] == 1


def test_archive_audit_and_preflight_reuse_identical_descriptor_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_path = tmp_path / "shared_ready_source.csv"
    venues_path = tmp_path / "venues.json"
    pd.DataFrame(
        {
            "timestamp": ["2023-12-31T00:00:00Z", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"],
            "close": [99.0, 100.0, 101.0],
            "high": [99.5, 100.5, 101.5],
            "low": [98.5, 99.5, 100.5],
            "fallback_signal": [1, 1, 1],
            "quality": [0.8, 0.8, 0.8],
        }
    ).to_csv(market_path, index=False)
    integrity = {"sha256": _sha256(market_path), "byte_size": market_path.stat().st_size}
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-shared-ready",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": market_path.name,
                        "source_integrity": integrity,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                    {
                        "descriptor_id": "bybit-shared-ready",
                        "venue": "bybit",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": market_path.name,
                        "source_integrity": integrity,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    original_read_raw_table = market_data_module._read_raw_table
    original_file_integrity = market_data_module._file_integrity
    read_count = 0
    integrity_count = 0

    def counting_read_raw_table(source_path: Path) -> pd.DataFrame:
        nonlocal read_count
        read_count += 1
        return original_read_raw_table(source_path)

    def counting_file_integrity(source_path: Path) -> dict[str, object]:
        nonlocal integrity_count
        integrity_count += 1
        return original_file_integrity(source_path)

    monkeypatch.setattr(market_data_module, "_read_raw_table", counting_read_raw_table)
    monkeypatch.setattr(market_data_module, "_file_integrity", counting_file_integrity)

    audit = audit_sandbox_archive_descriptors(venues_path, output_dir=tmp_path / "audit")

    assert read_count == 1
    assert integrity_count == 1
    assert audit["ready_count"] == 2
    assert {row["normalized_row_count"] for row in audit["descriptors"]} == {2}
    assert {row["descriptor_window_row_count"] for row in audit["descriptors"]} == {2}

    read_count = 0
    integrity_count = 0
    descriptors = load_venue_archive_descriptors(venues_path)
    spec = SandboxRunSpec(
        run_id="same-source-readiness-cache",
        data_window=DataWindow("2024-01-01", "2024-01-01"),
        holding_periods=(1,),
        min_trades=1,
    )
    materialize_count = 0
    original_materialize_strategy_signals = preflight_module.materialize_strategy_signals

    def counting_materialize_strategy_signals(
        market: pd.DataFrame,
        strategies: list[StrategyCatalogRow],
        **kwargs: object,
    ) -> pd.DataFrame:
        nonlocal materialize_count
        materialize_count += 1
        return original_materialize_strategy_signals(market, strategies, **kwargs)

    monkeypatch.setattr(preflight_module, "materialize_strategy_signals", counting_materialize_strategy_signals)

    preflight = preflight_sandbox_compatibility(
        spec=spec,
        strategies=[_strategy()],
        venues=descriptors,
        output_dir=tmp_path / "preflight",
    )

    assert read_count == 1
    assert integrity_count == 1
    assert materialize_count == 1
    assert preflight["row_count"] == 2
    assert preflight["runnable_trial_estimate"] == 2
    assert preflight["blocked_trial_estimate"] == 0


def test_readiness_caches_check_integrity_before_reusing_same_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_path = tmp_path / "shared_mixed_integrity_source.csv"
    venues_path = tmp_path / "venues.json"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=2, freq="1h", tz="UTC"),
            "close": [100.0, 101.0],
            "fallback_signal": [1, 1],
            "quality": [0.8, 0.8],
        }
    ).to_csv(market_path, index=False)
    good_integrity = {"sha256": _sha256(market_path), "byte_size": market_path.stat().st_size}
    bad_integrity = {"sha256": "bad", "byte_size": market_path.stat().st_size}
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-shared-good",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": market_path.name,
                        "source_integrity": good_integrity,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                    {
                        "descriptor_id": "bybit-shared-bad",
                        "venue": "bybit",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": market_path.name,
                        "source_integrity": bad_integrity,
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    original_read_raw_table = market_data_module._read_raw_table
    read_count = 0

    def counting_read_raw_table(source_path: Path) -> pd.DataFrame:
        nonlocal read_count
        read_count += 1
        return original_read_raw_table(source_path)

    monkeypatch.setattr(market_data_module, "_read_raw_table", counting_read_raw_table)

    audit = audit_sandbox_archive_descriptors(venues_path, output_dir=tmp_path / "audit")
    rows = {row["descriptor_id"]: row for row in audit["descriptors"]}

    assert read_count == 1
    assert audit["ready_count"] == 1
    assert audit["blocked_count"] == 1
    assert rows["okx-shared-good"]["status"] == "ready"
    assert rows["bybit-shared-bad"]["status"] == "blocked"
    assert rows["bybit-shared-bad"]["normalized_row_count"] == 0
    assert rows["bybit-shared-bad"]["blocker_reasons"] == ["source_integrity_sha256_mismatch"]

    read_count = 0
    spec = SandboxRunSpec(
        run_id="same-source-readiness-integrity-cache",
        data_window=DataWindow("2024-01-01", "2024-01-01"),
        holding_periods=(1,),
        min_trades=1,
    )
    preflight = preflight_sandbox_compatibility(
        spec=spec,
        strategies=[_strategy()],
        venues=load_venue_archive_descriptors(venues_path),
        output_dir=tmp_path / "preflight",
    )
    preflight_rows = {row["descriptor_id"]: row for row in preflight["rows"]}

    assert read_count == 1
    assert preflight["runnable_trial_estimate"] == 1
    assert preflight["blocked_trial_estimate"] == 1
    assert preflight_rows["okx-shared-good"]["status"] == "runnable"
    assert preflight_rows["bybit-shared-bad"]["status"] == "blocked"
    assert preflight_rows["bybit-shared-bad"]["market_row_count"] == 0
    assert preflight_rows["bybit-shared-bad"]["blocker_reasons"] == ["source_integrity_sha256_mismatch"]


def test_blueprint_signal_materialization_uses_completed_rows() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC"),
            "close": [100.0, 101.0, 103.0, 102.0, 105.0],
        }
    )

    market = materialize_strategy_signals(frame, [_blueprint_strategy()])

    assert list(market["sandbox_signal_compiled_momentum_long"]) == [0.0, 0.0, 1.0, 0.0, 1.0]


def test_blueprint_signal_materialization_dedupes_identical_proxy_columns() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC"),
            "close": [100.0, 101.0, 103.0, 102.0, 105.0],
        }
    )
    first = StrategyCatalogRow(
        hypothesis_id="proxy-a",
        family="trend_following_v1",
        signal_column="sandbox_signal_proxy_a",
        side="long",
        params={
            "sandbox_blueprint_id": "close_momentum_proxy",
            "sandbox_proxy_signal": True,
            "lookback_bars": 1,
            "return_threshold": 0.015,
        },
    )
    second = StrategyCatalogRow(
        hypothesis_id="proxy-b",
        family="trend_following_v1",
        signal_column="sandbox_signal_proxy_b",
        side="long",
        params=dict(first.params),
    )

    market = materialize_strategy_signals(frame, [first, second], dedupe_blueprint_signals=True)
    aliases = market.attrs[strategy_blueprints_module.SIGNAL_ALIAS_ATTR]
    canonical_column = aliases[first.signal_column]

    assert aliases[second.signal_column] == canonical_column
    assert canonical_column in market.columns
    assert first.signal_column not in market.columns
    assert second.signal_column not in market.columns
    assert list(market[canonical_column]) == [0.0, 0.0, 1.0, 0.0, 1.0]
    assert first.signal_column == "sandbox_signal_proxy_a"
    assert second.signal_column == "sandbox_signal_proxy_b"


def test_fixed_hold_sweep_reuses_deduped_proxy_signal_without_changing_descriptors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=8, freq="1D", tz="UTC"),
            "close": [100.0, 102.0, 105.0, 104.0, 108.0, 111.0, 110.0, 114.0],
        }
    )
    first = StrategyCatalogRow(
        hypothesis_id="proxy-a",
        family="trend_following_v1",
        signal_column="sandbox_signal_proxy_a",
        side="long",
        params={
            "sandbox_blueprint_id": "close_momentum_proxy",
            "sandbox_proxy_signal": True,
            "lookback_bars": 1,
            "return_threshold": 0.015,
        },
    )
    second = StrategyCatalogRow(
        hypothesis_id="proxy-b",
        family="trend_following_v1",
        signal_column="sandbox_signal_proxy_b",
        side="long",
        params=dict(first.params),
    )
    build_calls = 0
    original_build_signal = strategy_blueprints_module._build_signal

    def counting_build_signal(*args: object, **kwargs: object) -> pd.Series:
        nonlocal build_calls
        build_calls += 1
        return original_build_signal(*args, **kwargs)

    monkeypatch.setattr(strategy_blueprints_module, "_build_signal", counting_build_signal)

    results = run_fixed_hold_sweep(
        market_frame=frame,
        run_spec=SandboxRunSpec(
            run_id="deduped-proxy-sweep",
            data_window=DataWindow("2024-01-01", "2024-01-08"),
            holding_periods=(1,),
            round_trip_cost_bps=0.0,
            min_trades=1,
        ),
        strategies=[first, second],
        venues=[_venue()],
    )

    assert build_calls == 1
    assert {result.signal_column for result in results} == {first.signal_column, second.signal_column}
    assert len({result.trial_id for result in results}) == 2
    assert all(result.status == "screened" for result in results)
    assert not any(
        reason.startswith("missing_signal_column:")
        for result in results
        for reason in result.rejection_reasons
    )


def test_preflight_resolves_deduped_proxy_signal_aliases(tmp_path: Path) -> None:
    market_path = tmp_path / "market.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=8, freq="1D", tz="UTC"),
            "close": [100.0, 102.0, 105.0, 104.0, 108.0, 111.0, 110.0, 114.0],
        }
    ).to_csv(market_path, index=False)
    first = StrategyCatalogRow(
        hypothesis_id="proxy-a",
        family="trend_following_v1",
        signal_column="sandbox_signal_proxy_a",
        side="long",
        params={
            "sandbox_blueprint_id": "close_momentum_proxy",
            "sandbox_proxy_signal": True,
            "lookback_bars": 1,
            "return_threshold": 0.015,
        },
    )
    second = StrategyCatalogRow(
        hypothesis_id="proxy-b",
        family="trend_following_v1",
        signal_column="sandbox_signal_proxy_b",
        side="long",
        params=dict(first.params),
    )

    preflight = preflight_sandbox_compatibility(
        spec=SandboxRunSpec(
            run_id="deduped-proxy-preflight",
            data_window=DataWindow("2024-01-01", "2024-01-08"),
            holding_periods=(1,),
            round_trip_cost_bps=0.0,
            min_trades=1,
        ),
        strategies=[first, second],
        venues=[
            VenueArchiveDescriptor(
                descriptor_id="okx-deduped-proxy",
                venue="okx",
                symbol="BTCUSDT",
                data_family="kline",
                interval="1d",
                window=DataWindow("2024-01-01", "2024-01-08"),
                data_path=market_path,
            )
        ],
        output_dir=tmp_path / "preflight",
    )

    assert len(preflight["rows"]) == 2
    assert {row["status"] for row in preflight["rows"]} == {"runnable"}
    assert {row["signal_column"] for row in preflight["rows"]} == {first.signal_column, second.signal_column}
    assert {row["active_signal_count"] for row in preflight["rows"]} == {5}
    assert all("missing_signal_column" not in " ".join(row["blocker_reasons"]) for row in preflight["rows"])


def test_fixed_hold_sweep_materializes_blueprints_after_2024_window_filter() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2023-12-31T00:00:00Z",
                    "2024-01-01T00:00:00Z",
                    "2024-01-02T00:00:00Z",
                    "2024-01-03T00:00:00Z",
                ],
                utc=True,
            ),
            "close": [100.0, 120.0, 120.0, 120.0],
        }
    )
    strategy = StrategyCatalogRow(
        hypothesis_id="boundary-jump",
        family="close_momentum_proxy",
        signal_column="sandbox_signal_boundary_jump",
        side="long",
        params={
            "sandbox_blueprint_id": "close_momentum_proxy",
            "sandbox_proxy_signal": True,
            "lookback_bars": 1,
            "return_threshold": 0.10,
        },
    )

    results = run_fixed_hold_sweep(
        market_frame=frame,
        run_spec=_spec(),
        strategies=[strategy],
        venues=[_venue()],
    )

    assert len(results) == 2
    assert all(result.trade_count == 0 for result in results)
    assert all("no_complete_fixed_hold_trades" in result.rejection_reasons for result in results)


def test_compiled_strategy_config_runs_through_fixed_hold_sweep(tmp_path: Path) -> None:
    config_path = tmp_path / "trend_following_v1.json"
    config_path.write_text(
        json.dumps({"strategy_id": "trend_following_v1", "strategy_version": "v1", "parameters": {}}),
        encoding="utf-8",
    )
    strategies = load_strategy_catalog(config_path)
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=12, freq="1D", tz="UTC"),
            "close": [100.0 + (index * 2.0) for index in range(12)],
        }
    )
    spec = SandboxRunSpec(
        run_id="compiled-config-sweep",
        data_window=DataWindow("2024-01-01", "2024-01-12"),
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
    )

    results = run_fixed_hold_sweep(
        market_frame=frame,
        run_spec=spec,
        strategies=strategies,
        venues=[_venue()],
    )

    assert len(results) == 2
    assert any(result.status == "screened" and result.side == "long" for result in results)
    top = results[0].to_payload()
    assert top["metadata"]["sandbox_blueprint_id"] == "close_momentum_proxy"
    assert top["candidate_evidence"] is False


def test_run_spec_loader_reads_exit_and_filter_variants(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "variant-spec",
                "data_window": {"start": "2024-01-01", "end": "2024-01-31"},
                "holding_periods": [2],
                "exit_variants": [
                    {"variant_id": "fixed", "exit_profile": "fixed_hold"},
                    {"variant_id": "target-5", "exit_profile": "target_only", "target_return": 0.05},
                ],
                "filter_variants": [
                    {"variant_id": "base"},
                    {"variant_id": "quality-hi", "filter_column": "quality", "filter_min": 0.8},
                ],
            }
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_run_spec(spec_path)

    assert [variant.variant_id for variant in spec.exit_variants] == ["fixed", "target-5"]
    assert [variant.variant_id for variant in spec.filter_variants] == ["base", "quality-hi"]


def test_default_sandbox_grid_shape_is_preserved() -> None:
    results = run_fixed_hold_sweep(
        market_frame=_market_frame(),
        run_spec=_spec(),
        strategies=[_strategy()],
        venues=[_venue()],
    )

    assert len(results) == 2
    assert {result.exit_variant_id for result in results} == {"fixed_hold"}
    assert {result.filter_variant_id for result in results} == {"base"}


def test_sweep_reuses_signal_filter_masks_across_exit_and_holding_grid(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=12, freq="1h", tz="UTC"),
            "close": [100.0 + index for index in range(12)],
            "high": [101.0 + index for index in range(12)],
            "low": [99.0 + index for index in range(12)],
            "signal": [1] * 12,
            "quality": [0.9 if index % 2 == 0 else 0.2 for index in range(12)],
        }
    )
    strategy = StrategyCatalogRow(
        hypothesis_id="mask-cache-long",
        family="mask_cache",
        signal_column="signal",
        side="long",
    )
    spec = SandboxRunSpec(
        run_id="mask-cache-grid",
        data_window=DataWindow("2024-01-01", "2024-01-02"),
        holding_periods=(1, 2, 3),
        exit_variants=(
            ExitVariant("fixed", "fixed_hold"),
            ExitVariant("target", "target_only", target_return=0.01),
        ),
        filter_variants=(
            FilterVariant("base"),
            FilterVariant("quality-hi", filter_column="quality", filter_min=0.8),
        ),
        round_trip_cost_bps=0.0,
        min_trades=1,
        rank_top_n=100,
    )
    original_signal_mask = fast_backtest_module._signal_mask
    call_count = 0

    def counting_signal_mask(*args: object, **kwargs: object):
        nonlocal call_count
        call_count += 1
        return original_signal_mask(*args, **kwargs)

    monkeypatch.setattr(fast_backtest_module, "_signal_mask", counting_signal_mask)

    results = run_fixed_hold_sweep(
        market_frame=frame,
        run_spec=spec,
        strategies=[strategy],
        venues=[_venue("okx"), _venue("bybit")],
    )

    assert len(results) == 24
    assert call_count == 2
    assert {result.filter_variant_id for result in results} == {"base", "quality-hi"}
    assert {result.exit_variant_id for result in results} == {"fixed", "target"}


def test_sweep_reuses_prepared_market_arrays_across_trial_grid(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=12, freq="1h", tz="UTC"),
            "close": [100.0 + index for index in range(12)],
            "high": [101.5 + index for index in range(12)],
            "low": [99.0 + index for index in range(12)],
            "signal": [1] * 12,
            "quality": [0.9 if index % 2 == 0 else 0.2 for index in range(12)],
        }
    )
    strategy = StrategyCatalogRow(
        hypothesis_id="array-cache-long",
        family="array_cache",
        signal_column="signal",
        side="long",
    )
    spec = SandboxRunSpec(
        run_id="array-cache-grid",
        data_window=DataWindow("2024-01-01", "2024-01-02"),
        holding_periods=(1, 2, 3),
        exit_variants=(
            ExitVariant("fixed", "fixed_hold"),
            ExitVariant("target", "target_only", target_return=0.01),
        ),
        filter_variants=(
            FilterVariant("base"),
            FilterVariant("quality-hi", filter_column="quality", filter_min=0.8),
        ),
        round_trip_cost_bps=0.0,
        min_trades=1,
        rank_top_n=100,
    )
    original_prepare = fast_backtest_module._prepared_market_arrays
    prepare_calls: list[bool] = []

    def counting_prepare(*args: object, **kwargs: object):
        prepare_calls.append(bool(kwargs.get("include_ohlc")))
        return original_prepare(*args, **kwargs)

    monkeypatch.setattr(fast_backtest_module, "_prepared_market_arrays", counting_prepare)

    results = run_fixed_hold_sweep(
        market_frame=frame,
        run_spec=spec,
        strategies=[strategy],
        venues=[_venue("okx"), _venue("bybit")],
    )

    assert len(results) == 24
    assert prepare_calls == [True]
    assert {result.filter_variant_id for result in results} == {"base", "quality-hi"}
    assert {result.exit_variant_id for result in results} == {"fixed", "target"}
    assert {result.active_days for result in results} == {1}
    assert any(result.exit_variant_id == "target" and result.trade_count > 0 for result in results)


def test_shared_market_sweep_reuses_trial_metrics_across_venues(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=12, freq="1h", tz="UTC"),
            "close": [100.0 + index for index in range(12)],
            "high": [101.5 + index for index in range(12)],
            "low": [99.0 + index for index in range(12)],
            "signal": [1] * 12,
            "quality": [0.9 if index % 2 == 0 else 0.2 for index in range(12)],
        }
    )
    strategy = StrategyCatalogRow(
        hypothesis_id="shared-market-cache-long",
        family="shared_market_cache",
        signal_column="signal",
        side="long",
    )
    spec = SandboxRunSpec(
        run_id="shared-market-cache-grid",
        data_window=DataWindow("2024-01-01", "2024-01-02"),
        holding_periods=(1, 2, 3),
        exit_variants=(
            ExitVariant("fixed", "fixed_hold"),
            ExitVariant("target", "target_only", target_return=0.01),
        ),
        filter_variants=(
            FilterVariant("base"),
            FilterVariant("quality-hi", filter_column="quality", filter_min=0.8),
        ),
        round_trip_cost_bps=0.0,
        min_trades=1,
        rank_top_n=100,
    )
    original_gross_returns = fast_backtest_module._gross_returns
    gross_return_calls = 0

    def counting_gross_returns(*args: object, **kwargs: object):
        nonlocal gross_return_calls
        gross_return_calls += 1
        return original_gross_returns(*args, **kwargs)

    monkeypatch.setattr(fast_backtest_module, "_gross_returns", counting_gross_returns)

    results = run_fixed_hold_sweep(
        market_frame=frame,
        run_spec=spec,
        strategies=[strategy],
        venues=[_venue("okx"), _venue("bybit")],
    )

    assert len(results) == 24
    assert gross_return_calls == 12
    assert {result.venue for result in results} == {"okx", "bybit"}
    assert len({result.trial_id for result in results}) == 24
    grouped_metrics: dict[tuple[str, str, int], set[tuple[int, float, float, float]]] = {}
    for result in results:
        key = (result.filter_variant_id, result.exit_variant_id, result.holding_period)
        metric = (result.trade_count, result.net_return_sum, result.score, result.max_drawdown)
        grouped_metrics.setdefault(key, set()).add(metric)
    assert len(grouped_metrics) == 12
    assert all(len(metrics) == 1 for metrics in grouped_metrics.values())


def test_descriptor_routed_sweep_keeps_venue_frame_metrics_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    okx = _venue("okx")
    bybit = _venue("bybit")
    base = {
        "timestamp": pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC"),
        "signal": [1, 0, 0, 0],
    }
    okx_frame = pd.DataFrame({**base, "close": [100.0, 100.0, 102.0, 103.0]})
    bybit_frame = pd.DataFrame({**base, "close": [100.0, 100.0, 98.0, 97.0]})
    strategy = StrategyCatalogRow(
        hypothesis_id="descriptor-frame-cache-long",
        family="descriptor_frame_cache",
        signal_column="signal",
        side="long",
    )
    spec = SandboxRunSpec(
        run_id="descriptor-frame-cache",
        data_window=DataWindow("2024-01-01", "2024-01-02"),
        holding_periods=(1,),
        exit_variants=(ExitVariant("fixed", "fixed_hold"),),
        round_trip_cost_bps=0.0,
        min_trades=1,
        rank_top_n=10,
    )
    original_gross_returns = fast_backtest_module._gross_returns
    gross_return_calls = 0

    def counting_gross_returns(*args: object, **kwargs: object):
        nonlocal gross_return_calls
        gross_return_calls += 1
        return original_gross_returns(*args, **kwargs)

    monkeypatch.setattr(fast_backtest_module, "_gross_returns", counting_gross_returns)

    results = run_fixed_hold_sweep_for_venue_frames(
        market_frames={okx.descriptor_id: okx_frame, bybit.descriptor_id: bybit_frame},
        run_spec=spec,
        strategies=[strategy],
        venues=[okx, bybit],
    )

    by_venue = {result.venue: result for result in results}
    assert gross_return_calls == 2
    assert by_venue["okx"].net_return_sum == pytest.approx(0.02)
    assert by_venue["bybit"].net_return_sum == pytest.approx(-0.02)
    assert by_venue["okx"].status == "screened"
    assert by_venue["bybit"].status == "rejected"
    assert by_venue["okx"].trial_id != by_venue["bybit"].trial_id


def test_descriptor_routed_sweep_reuses_metrics_for_same_source_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    okx = _venue("okx")
    bybit = _venue("bybit")
    shared_path = tmp_path / "same_source.csv"
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC"),
            "close": [100.0, 100.0, 102.0, 103.0],
            "signal": [1, 0, 0, 0],
        }
    )
    frame.to_csv(shared_path, index=False)
    strategy = StrategyCatalogRow(
        hypothesis_id="descriptor-source-cache-long",
        family="descriptor_source_cache",
        signal_column="signal",
        side="long",
    )
    spec = SandboxRunSpec(
        run_id="descriptor-source-cache",
        data_window=DataWindow("2024-01-01", "2024-01-02"),
        holding_periods=(1,),
        exit_variants=(ExitVariant("fixed", "fixed_hold"),),
        round_trip_cost_bps=0.0,
        min_trades=1,
        rank_top_n=10,
    )
    original_gross_returns = fast_backtest_module._gross_returns
    gross_return_calls = 0

    def counting_gross_returns(*args: object, **kwargs: object):
        nonlocal gross_return_calls
        gross_return_calls += 1
        return original_gross_returns(*args, **kwargs)

    monkeypatch.setattr(fast_backtest_module, "_gross_returns", counting_gross_returns)

    results = run_fixed_hold_sweep_for_venue_frames(
        market_frames={okx.descriptor_id: frame.copy(), bybit.descriptor_id: frame.copy()},
        run_spec=spec,
        strategies=[strategy],
        venues=[okx, bybit],
        market_sources={
            okx.descriptor_id: {
                "routing_mode": "descriptor_data_path",
                "descriptor_id": okx.descriptor_id,
                "venue": okx.venue,
                "symbol": okx.symbol,
                "data_family": okx.data_family,
                "data_path": str(shared_path),
            },
            bybit.descriptor_id: {
                "routing_mode": "descriptor_data_path",
                "descriptor_id": bybit.descriptor_id,
                "venue": bybit.venue,
                "symbol": bybit.symbol,
                "data_family": bybit.data_family,
                "data_path": str(shared_path),
            },
        },
    )

    by_venue = {result.venue: result for result in results}
    assert gross_return_calls == 1
    assert by_venue["okx"].net_return_sum == pytest.approx(by_venue["bybit"].net_return_sum)
    assert by_venue["okx"].trial_id != by_venue["bybit"].trial_id
    assert by_venue["okx"].metadata["market_source"]["descriptor_id"] == okx.descriptor_id
    assert by_venue["bybit"].metadata["market_source"]["descriptor_id"] == bybit.descriptor_id
    assert by_venue["okx"].metadata["market_source"]["data_path"] == str(shared_path)
    assert by_venue["bybit"].metadata["market_source"]["data_path"] == str(shared_path)


def test_vectorized_barrier_exit_prices_match_reference_for_long_and_short() -> None:
    close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0])
    high = np.array([100.0, 106.0, 103.0, 105.0, 104.0, 107.0, 105.0, 112.0, 110.0, 111.0])
    low = np.array([100.0, 95.0, 100.0, 97.0, 102.0, 103.0, 96.0, 94.0, 100.0, 99.0])
    entry_idx = np.array([0, 2, 4, 6])
    exit_idx = entry_idx + 3
    entry = close[entry_idx]
    variants = (
        ExitVariant("target", "target_only", target_return=0.05),
        ExitVariant("stop", "stop_only", stop_return=0.03),
        ExitVariant("target-stop", "target_stop_conservative", target_return=0.05, stop_return=0.03),
    )

    def reference(side: str, variant: ExitVariant) -> np.ndarray:
        exit_price = close[exit_idx].copy()
        for row_index, (entry_bar, exit_bar, entry_price) in enumerate(zip(entry_idx, exit_idx, entry, strict=False)):
            for bar_index in range(int(entry_bar) + 1, int(exit_bar) + 1):
                hit_target = False
                hit_stop = False
                if side == "short":
                    if variant.target_return is not None:
                        hit_target = bool(low[bar_index] <= entry_price * (1.0 - variant.target_return))
                    if variant.stop_return is not None:
                        hit_stop = bool(high[bar_index] >= entry_price * (1.0 + variant.stop_return))
                else:
                    if variant.target_return is not None:
                        hit_target = bool(high[bar_index] >= entry_price * (1.0 + variant.target_return))
                    if variant.stop_return is not None:
                        hit_stop = bool(low[bar_index] <= entry_price * (1.0 - variant.stop_return))

                if variant.exit_profile == "target_only" and hit_target and variant.target_return is not None:
                    exit_price[row_index] = entry_price * (
                        1.0 - variant.target_return if side == "short" else 1.0 + variant.target_return
                    )
                    break
                if variant.exit_profile == "stop_only" and hit_stop and variant.stop_return is not None:
                    exit_price[row_index] = entry_price * (
                        1.0 + variant.stop_return if side == "short" else 1.0 - variant.stop_return
                    )
                    break
                if variant.exit_profile == "target_stop_conservative":
                    if hit_stop and variant.stop_return is not None:
                        exit_price[row_index] = entry_price * (
                            1.0 + variant.stop_return if side == "short" else 1.0 - variant.stop_return
                        )
                        break
                    if hit_target and variant.target_return is not None:
                        exit_price[row_index] = entry_price * (
                            1.0 - variant.target_return if side == "short" else 1.0 + variant.target_return
                        )
                        break
        return exit_price

    for side in ("long", "short"):
        for variant in variants:
            actual = fast_backtest_module._barrier_exit_prices(
                close=close,
                high=high,
                low=low,
                entry_idx=entry_idx,
                exit_idx=exit_idx,
                entry=entry,
                side=side,
                exit_variant=variant,
            )
            assert actual.tolist() == pytest.approx(reference(side, variant).tolist())


def test_barrier_exit_prices_match_single_batch_when_forced_to_small_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close = np.array(
        [
            100.0,
            101.0,
            99.0,
            103.0,
            102.0,
            106.0,
            104.0,
            108.0,
            105.0,
            110.0,
            107.0,
            111.0,
            109.0,
            113.0,
            112.0,
            115.0,
            114.0,
            116.0,
            118.0,
            117.0,
        ]
    )
    high = close + np.array(
        [
            0.0,
            4.0,
            1.0,
            7.0,
            2.0,
            8.0,
            1.0,
            5.0,
            2.0,
            7.0,
            1.0,
            6.0,
            2.0,
            9.0,
            1.0,
            5.0,
            2.0,
            6.0,
            1.0,
            4.0,
        ]
    )
    low = close - np.array(
        [
            0.0,
            1.0,
            5.0,
            2.0,
            6.0,
            1.0,
            8.0,
            2.0,
            7.0,
            1.0,
            6.0,
            2.0,
            9.0,
            1.0,
            5.0,
            2.0,
            6.0,
            1.0,
            4.0,
            2.0,
        ]
    )
    entry_idx = np.arange(0, 12, dtype=int)
    exit_idx = entry_idx + np.array([5, 4, 6, 3, 5, 4, 6, 3, 5, 4, 6, 3], dtype=int)
    entry = close[entry_idx]
    variants = (
        ExitVariant("target", "target_only", target_return=0.04),
        ExitVariant("stop", "stop_only", stop_return=0.03),
        ExitVariant("target-stop", "target_stop_conservative", target_return=0.04, stop_return=0.03),
    )

    assert entry_idx.size > 2
    for side in ("long", "short"):
        for variant in variants:
            monkeypatch.setattr(fast_backtest_module, "_BARRIER_EXIT_ENTRY_BATCH_SIZE", 10_000)
            expected = fast_backtest_module._barrier_exit_prices(
                close=close,
                high=high,
                low=low,
                entry_idx=entry_idx,
                exit_idx=exit_idx,
                entry=entry,
                side=side,
                exit_variant=variant,
            )

            monkeypatch.setattr(fast_backtest_module, "_BARRIER_EXIT_ENTRY_BATCH_SIZE", 2)
            actual = fast_backtest_module._barrier_exit_prices(
                close=close,
                high=high,
                low=low,
                entry_idx=entry_idx,
                exit_idx=exit_idx,
                entry=entry,
                side=side,
                exit_variant=variant,
            )

            assert actual.tolist() == pytest.approx(expected.tolist())


def test_vectorized_barrier_exit_prices_preserve_stop_first_and_no_hit_fallback() -> None:
    close = np.array([100.0, 100.0, 100.0, 101.0])
    high = np.array([100.0, 106.0, 104.0, 101.0])
    low = np.array([100.0, 94.0, 99.0, 101.0])
    entry_idx = np.array([0, 1])
    exit_idx = np.array([2, 3])
    entry = close[entry_idx]
    variant = ExitVariant("target-stop", "target_stop_conservative", target_return=0.05, stop_return=0.05)

    long_prices = fast_backtest_module._barrier_exit_prices(
        close=close,
        high=high,
        low=low,
        entry_idx=entry_idx,
        exit_idx=exit_idx,
        entry=entry,
        side="long",
        exit_variant=variant,
    )
    short_prices = fast_backtest_module._barrier_exit_prices(
        close=close,
        high=high,
        low=low,
        entry_idx=entry_idx,
        exit_idx=exit_idx,
        entry=entry,
        side="short",
        exit_variant=variant,
    )

    assert long_prices.tolist() == pytest.approx([95.0, 101.0])
    assert short_prices.tolist() == pytest.approx([105.0, 101.0])


def test_exit_variants_rank_target_stop_and_fixed_hold_paths() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC"),
            "open": [100.0, 100.0, 102.0, 103.0, 104.0],
            "high": [100.0, 101.0, 106.0, 104.0, 105.0],
            "low": [100.0, 99.0, 96.0, 100.0, 101.0],
            "close": [100.0, 100.0, 102.0, 103.0, 104.0],
            "signal": [1, 0, 0, 0, 0],
        }
    )
    spec = SandboxRunSpec(
        run_id="exit-grid",
        data_window=DataWindow("2024-01-01", "2024-01-05"),
        holding_periods=(2,),
        exit_variants=(
            ExitVariant("fixed", "fixed_hold"),
            ExitVariant("target-5", "target_only", target_return=0.05),
            ExitVariant("stop-3", "stop_only", stop_return=0.03),
            ExitVariant("target-stop", "target_stop_conservative", target_return=0.05, stop_return=0.03),
        ),
        round_trip_cost_bps=0.0,
        min_trades=1,
    )
    strategy = StrategyCatalogRow("long-signal", "exit_grid", "signal")

    results = run_fixed_hold_sweep(market_frame=frame, run_spec=spec, strategies=[strategy], venues=[_venue()])
    by_exit = {result.exit_variant_id: result for result in results}

    assert len(results) == 4
    assert by_exit["target-5"].net_return_sum == pytest.approx(0.05)
    assert by_exit["fixed"].net_return_sum == pytest.approx(0.03)
    assert by_exit["stop-3"].net_return_sum == pytest.approx(-0.03)
    assert by_exit["target-stop"].net_return_sum == pytest.approx(-0.03)
    assert by_exit["target-stop"].metadata["same_bar_target_stop_policy"] == "stop_first"
    assert len({result.trial_id for result in results}) == 4
    assert all(result.to_payload()["candidate_pack_eligible"] is False for result in results)


def test_exit_variants_block_without_required_high_low_columns() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC"),
            "close": [100.0, 100.0, 102.0, 103.0, 104.0],
            "signal": [1, 0, 0, 0, 0],
        }
    )
    spec = SandboxRunSpec(
        run_id="missing-ohlc",
        data_window=DataWindow("2024-01-01", "2024-01-05"),
        holding_periods=(2,),
        exit_variants=(ExitVariant("target-5", "target_only", target_return=0.05),),
        min_trades=1,
    )
    strategy = StrategyCatalogRow("long-signal", "exit_grid", "signal")

    results = run_fixed_hold_sweep(market_frame=frame, run_spec=spec, strategies=[strategy], venues=[_venue()])

    assert len(results) == 1
    assert results[0].status == "blocked"
    assert "missing_ohlc_column:high" in results[0].rejection_reasons
    assert "missing_ohlc_column:low" in results[0].rejection_reasons


def test_filter_variants_change_trade_counts_and_trial_ids() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=6, freq="1D", tz="UTC"),
            "close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
            "signal": [1, 1, 1, 0, 0, 0],
            "quality": [0.2, 0.9, 0.9, 0.9, 0.9, 0.9],
        }
    )
    spec = SandboxRunSpec(
        run_id="filter-grid",
        data_window=DataWindow("2024-01-01", "2024-01-06"),
        holding_periods=(1,),
        filter_variants=(
            FilterVariant("base"),
            FilterVariant("quality-hi", filter_column="quality", filter_min=0.8),
        ),
        round_trip_cost_bps=0.0,
        min_trades=1,
    )
    strategy = StrategyCatalogRow("long-signal", "filter_grid", "signal")

    results = run_fixed_hold_sweep(market_frame=frame, run_spec=spec, strategies=[strategy], venues=[_venue()])
    by_filter = {result.filter_variant_id: result for result in results}

    assert by_filter["base"].trade_count == 3
    assert by_filter["quality-hi"].trade_count == 2
    assert by_filter["base"].trial_id != by_filter["quality-hi"].trial_id
    assert by_filter["quality-hi"].metadata["filter_variant"]["filter_min"] == 0.8


def test_deterministic_trial_id_is_stable_and_changes_with_inputs() -> None:
    spec = _spec()
    strategy = _strategy()
    venue = _venue()

    first = deterministic_trial_id(run_spec=spec, strategy=strategy, venue=venue, holding_period=1)
    second = deterministic_trial_id(run_spec=spec, strategy=strategy, venue=venue, holding_period=1)
    changed = deterministic_trial_id(run_spec=spec, strategy=strategy, venue=venue, holding_period=2)

    assert first == second
    assert first != changed


def test_fixed_hold_sweep_ignores_pre_2024_rows_and_records_sandbox_results() -> None:
    results = run_fixed_hold_sweep(
        market_frame=_market_frame(),
        run_spec=_spec(),
        strategies=[_strategy()],
        venues=[_venue()],
    )

    assert len(results) == 2
    assert all(result.market_start is None or result.market_start.startswith("2024-") for result in results)
    assert any(result.status == "screened" for result in results)
    top = next(result.to_payload() for result in results if result.status == "screened")
    assert top["sandbox_only"] is True
    assert top["promotion_ready"] is False
    assert top["candidate_evidence"] is False
    assert top["metadata"]["entry_price_source"] == "next_bar_close"
    assert top["metadata"]["same_bar_entry_exit_allowed"] is False


def test_sandbox_run_writes_compact_non_promotable_artifacts(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-artifact-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx"), _venue("hyperliquid")],
        output_root=tmp_path,
    )

    manifest = json.loads(run.artifacts.manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_parquet(run.artifacts.summary_parquet_path)
    rankings = pd.read_parquet(run.artifacts.rankings_parquet_path)
    requests = json.loads(run.artifacts.evidence_requests_json_path.read_text(encoding="utf-8"))
    request_table = pd.read_parquet(run.artifacts.evidence_requests_parquet_path)

    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["sandbox_only"] is True
    assert manifest["candidate_pack_eligible"] is False
    assert manifest["result_count"] == 4
    assert set(manifest["artifact_integrity"]) == {
        "summary_parquet",
        "rankings_parquet",
        "evidence_requests_json",
        "evidence_requests_parquet",
    }
    for key, artifact_key in (
        ("summary_parquet", "summary_parquet_path"),
        ("rankings_parquet", "rankings_parquet_path"),
        ("evidence_requests_json", "evidence_requests_json_path"),
        ("evidence_requests_parquet", "evidence_requests_parquet_path"),
    ):
        artifact_path = Path(str(manifest["artifacts"][artifact_key]))
        assert manifest["artifact_integrity"][key]["sha256"] == _sha256(artifact_path)
        assert manifest["artifact_integrity"][key]["byte_size"] == artifact_path.stat().st_size
    integrity_report = verify_sandbox_artifact_integrity(run.artifacts.run_dir)
    integrity_frame = pd.read_parquet(str(integrity_report["report_parquet_path"]))
    assert integrity_report["verification_status"] == "passed"
    assert integrity_report["checked_artifact_count"] == 4
    assert integrity_report["verified_artifact_count"] == 4
    assert integrity_report["failed_artifact_count"] == 0
    assert Path(str(integrity_report["report_json_path"])).exists()
    assert set(integrity_frame["status"]) == {"matched"}
    assert set(summary["promotion_ready"]) == {False}
    assert set(summary["candidate_pack_eligible"]) == {False}
    assert list(rankings["rank"]) == sorted(rankings["rank"])
    assert requests
    assert request_table.shape[0] == len(requests)
    assert all(request["candidate_evidence"] is False for request in requests)
    assert all(request["candidate_pack_eligible"] is False for request in requests)
    assert all(request["requested_validation"] == "strict_research_cycle_request" for request in requests)


def test_sandbox_artifact_integrity_verifier_detects_tampered_run_artifact(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-tamper-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx")],
        output_root=tmp_path,
    )

    original_text = run.artifacts.evidence_requests_json_path.read_text(encoding="utf-8")
    run.artifacts.evidence_requests_json_path.write_text(f"{original_text}\n", encoding="utf-8")

    integrity_report = verify_sandbox_artifact_integrity(run.artifacts.manifest_path, write_report=False)
    rows = {row["artifact_key"]: row for row in integrity_report["rows"]}
    tampered_row = rows["evidence_requests_json"]

    assert integrity_report["verification_status"] == "failed"
    assert integrity_report["mismatched_artifact_count"] == 1
    assert integrity_report["failed_artifact_count"] == 1
    assert integrity_report["report_json_path"] is None
    assert tampered_row["status"] == "mismatched"
    assert "sha256_mismatch:evidence_requests_json" in tampered_row["reasons"]
    assert "byte_size_mismatch:evidence_requests_json" in tampered_row["reasons"]
    assert rows["summary_parquet"]["status"] == "matched"
    with pytest.raises(ValueError, match="sandbox_test_source failed sandbox artifact integrity"):
        require_sandbox_artifact_integrity(run.artifacts.manifest_path, payload_name="sandbox_test_source")


def test_sandbox_artifact_consumers_reject_tampered_run_children(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-tampered-consumer-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx")],
        output_root=tmp_path / "runs",
    )

    original_text = run.artifacts.evidence_requests_json_path.read_text(encoding="utf-8")
    run.artifacts.evidence_requests_json_path.write_text(f"{original_text}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="sandbox_analysis_source failed sandbox artifact integrity"):
        summarize_sandbox_run(run.artifacts.run_dir)
    with pytest.raises(ValueError, match="sandbox_falsification_source failed sandbox artifact integrity"):
        summarize_sandbox_hypotheses(run.artifacts.run_dir)
    with pytest.raises(ValueError, match="sandbox_validation_bundle_source failed sandbox artifact integrity"):
        export_sandbox_validation_request_bundle(run.artifacts.run_dir)
    with pytest.raises(ValueError, match="sandbox_leaderboard_source failed sandbox artifact integrity"):
        build_sandbox_global_leaderboard(tmp_path / "runs", output_dir=tmp_path / "leaderboard")

    assert not (run.artifacts.run_dir / "analysis_summary.json").exists()
    assert not (run.artifacts.run_dir / "hypothesis_falsification.json").exists()
    assert not (run.artifacts.run_dir / "strict_validation_request_bundle.json").exists()
    assert not (tmp_path / "leaderboard" / "sandbox_global_leaderboard.json").exists()


def test_sandbox_archive_sweep_routes_each_venue_to_its_own_market_frame(tmp_path: Path) -> None:
    okx_path = tmp_path / "okx_market.csv"
    hyperliquid_path = tmp_path / "hyperliquid_market.csv"
    timestamps = pd.date_range("2024-01-01", periods=8, freq="1D", tz="UTC")
    pd.DataFrame(
        {
            "timestamp": timestamps,
            "close": [100.0 + index for index in range(8)],
            "signal": [1] * 8,
        }
    ).to_csv(okx_path, index=False)
    pd.DataFrame(
        {
            "timestamp": timestamps,
            "close": [100.0 - index for index in range(8)],
            "signal": [1] * 8,
        }
    ).to_csv(hyperliquid_path, index=False)
    venues = [
        VenueArchiveDescriptor(
            descriptor_id="okx-btc-2024",
            venue="okx",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-08"),
            data_path=okx_path,
        ),
        VenueArchiveDescriptor(
            descriptor_id="hyperliquid-btc-2024",
            venue="hyperliquid",
            symbol="BTC",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-08"),
            data_path=hyperliquid_path,
        ),
    ]
    spec = SandboxRunSpec(
        run_id="archive-routing-run",
        data_window=DataWindow("2024-01-01", "2024-01-08"),
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
    )
    strategy = StrategyCatalogRow("always-long", "routing", "signal")

    run = run_sandbox_archive_sweep(
        spec=spec,
        strategies=[strategy],
        venues=venues,
        output_root=tmp_path / "out",
    )

    by_venue = {result.venue: result for result in run.results}
    manifest = json.loads(run.artifacts.manifest_path.read_text(encoding="utf-8"))
    requests = json.loads(run.artifacts.evidence_requests_json_path.read_text(encoding="utf-8"))

    assert by_venue["okx"].status == "screened"
    assert by_venue["okx"].net_return_sum > 0
    assert by_venue["hyperliquid"].status == "rejected"
    assert by_venue["hyperliquid"].net_return_sum < 0
    assert by_venue["okx"].rank == 1
    assert by_venue["okx"].metadata["market_source"]["descriptor_id"] == "okx-btc-2024"
    assert len(manifest["market_sources"]) == 2
    assert {source["descriptor_id"] for source in manifest["market_sources"]} == {
        "okx-btc-2024",
        "hyperliquid-btc-2024",
    }
    assert manifest["candidate_pack_eligible"] is False
    assert len(requests) == 1
    request_context = requests[0]["source_trial_context"]
    assert request_context["source_trial_id"] == by_venue["okx"].trial_id
    assert request_context["venue_descriptor_id"] == "okx-btc-2024"
    assert request_context["market_source"]["routing_mode"] == "descriptor_data_path"
    assert request_context["market_source"]["data_path"] == str(okx_path)
    assert request_context["market_start"].startswith("2024-01-01")
    assert request_context["execution_assumptions"]["entry_price_source"] == "next_bar_close"

    bundle = export_sandbox_validation_request_bundle(run.artifacts.run_dir, output_dir=tmp_path / "bundle")
    bundle_frame = pd.read_parquet(Path(str(bundle["bundle_parquet_path"])))
    descriptor = bundle["descriptors"][0]

    assert descriptor["source_trial_context"] == request_context
    assert descriptor["source_venue_descriptor_id"] == "okx-btc-2024"
    assert descriptor["source_market_source"]["routing_mode"] == "descriptor_data_path"
    assert descriptor["strict_validation_executed"] is False
    assert descriptor["candidate_pack_written"] is False
    parquet_context = json.loads(bundle_frame["source_trial_context"].iloc[0])
    assert parquet_context["venue_descriptor_id"] == "okx-btc-2024"
    assert set(bundle_frame["candidate_pack_eligible"]) == {False}


def test_strict_validation_descriptor_preflight_accepts_descriptor_only_planning_request(
    tmp_path: Path,
) -> None:
    market_path = tmp_path / "archives" / "okx_btcusdt_12h.csv"
    market_path.parent.mkdir(parents=True)
    _market_frame().to_csv(market_path, index=False)
    venue = VenueArchiveDescriptor(
        descriptor_id="okx-btc-2024",
        venue="okx",
        symbol="BTCUSDT",
        data_family="kline",
        interval="12h",
        window=DataWindow("2024-01-01", "2024-02-15"),
        data_path=market_path,
    )
    run = run_sandbox_archive_sweep(
        spec=SandboxRunSpec(
            run_id="strict-validation-preflight-accepted",
            data_window=DataWindow("2024-01-01", "2024-02-15"),
            holding_periods=(1,),
            round_trip_cost_bps=1.0,
            min_trades=2,
            max_evidence_requests=1,
        ),
        strategies=[_strategy()],
        venues=[venue],
        output_root=tmp_path / "runs",
    )
    bundle = export_sandbox_validation_request_bundle(
        run.artifacts.run_dir,
        output_dir=tmp_path / "bundle",
    )

    payload = preflight_sandbox_strict_validation_descriptors(
        bundle["bundle_json_path"],
        output_dir=tmp_path / "preflight",
    )
    row = payload["descriptors"][0]
    frame = pd.read_parquet(payload["preflight_parquet_path"])

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["sandbox_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_evidence"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_only"] is True
    assert payload["strict_validation_preflight_only"] is True
    assert payload["strict_validation_executed"] is False
    assert payload["strict_validation_authorized"] is False
    assert payload["candidate_pack_written"] is False
    assert payload["candidate_pack_write_authorized"] is False
    assert payload["accepted_descriptor_count"] == 1
    assert payload["blocked_descriptor_count"] == 0
    assert row["preflight_status"] == "accepted_for_strict_validation_planning"
    assert row["accepted_for_strict_validation_planning"] is True
    assert row["blocker_reasons"] == []
    assert row["source_trial_id"] == bundle["descriptors"][0]["source_trial_id"]
    assert row["source_venue_descriptor_id"] == "okx-btc-2024"
    assert row["source_market_source"]["data_path"] == str(market_path)
    assert row["execution_assumptions"]["entry_price_source"] == "next_bar_close"
    assert row["strict_validation_executed"] is False
    assert row["candidate_pack_written"] is False
    assert row["candidate_pack_paths"] == []
    assert set(frame["candidate_pack_eligible"]) == {False}
    assert Path(str(payload["preflight_json_path"])).exists()
    assert Path(str(payload["preflight_parquet_path"])).exists()


def test_cli_command_preflights_strict_validation_bundle_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    market_path = research_root / "archives" / "okx_btcusdt_12h.csv"
    market_path.parent.mkdir(parents=True)
    _market_frame().to_csv(market_path, index=False)
    venue = VenueArchiveDescriptor(
        descriptor_id="okx-btc-2024",
        venue="okx",
        symbol="BTCUSDT",
        data_family="kline",
        interval="12h",
        window=DataWindow("2024-01-01", "2024-02-15"),
        data_path=market_path,
    )
    run = run_sandbox_archive_sweep(
        spec=SandboxRunSpec(
            run_id="strict-validation-preflight-cli",
            data_window=DataWindow("2024-01-01", "2024-02-15"),
            holding_periods=(1,),
            round_trip_cost_bps=1.0,
            min_trades=2,
            max_evidence_requests=1,
        ),
        strategies=[_strategy()],
        venues=[venue],
        output_root=research_root / "runs",
    )
    bundle = export_sandbox_validation_request_bundle(
        run.artifacts.run_dir,
        output_dir=research_root / "bundle",
    )
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    payload = main._run_preflight_rapid_strategy_sandbox_validation_requests_command(
        argparse.Namespace(
            command="preflight-rapid-strategy-sandbox-validation-requests",
            bundle=str(bundle["bundle_json_path"]),
            output_dir="strict_validation_preflights",
        )
    )

    assert payload["descriptor_only"] is True
    assert payload["strict_validation_preflight_only"] is True
    assert payload["accepted_descriptor_count"] == 1
    assert payload["strict_validation_executed"] is False
    assert payload["candidate_pack_written"] is False
    assert Path(str(payload["preflight_json_path"])).resolve().relative_to(research_root.resolve())
    assert Path(str(payload["preflight_parquet_path"])).resolve().relative_to(research_root.resolve())


def test_strict_validation_descriptor_preflight_blocks_proxy_and_pre_2024_descriptors(
    tmp_path: Path,
) -> None:
    market_path = tmp_path / "archives" / "okx_btcusdt_12h.csv"
    market_path.parent.mkdir(parents=True)
    _market_frame().to_csv(market_path, index=False)
    venue = VenueArchiveDescriptor(
        descriptor_id="okx-btc-2024",
        venue="okx",
        symbol="BTCUSDT",
        data_family="kline",
        interval="12h",
        window=DataWindow("2024-01-01", "2024-02-15"),
        data_path=market_path,
    )
    run = run_sandbox_archive_sweep(
        spec=_spec("strict-validation-preflight-blocked"),
        strategies=[_strategy()],
        venues=[venue],
        output_root=tmp_path / "runs",
    )
    bundle = export_sandbox_validation_request_bundle(
        run.artifacts.run_dir,
        output_dir=tmp_path / "bundle",
    )
    payload = json.loads(Path(str(bundle["bundle_json_path"])).read_text(encoding="utf-8"))
    base_descriptor = payload["descriptors"][0]
    proxy_descriptor = json.loads(json.dumps(base_descriptor))
    proxy_descriptor["descriptor_id"] = "proxy-descriptor"
    proxy_descriptor["source_request_id"] = "proxy-request"
    proxy_descriptor["source_trial_context"]["execution_assumptions"]["sandbox_proxy_only"] = True
    proxy_descriptor["source_trial_context"]["execution_assumptions"]["sandbox_proxy_signal"] = True
    pre_2024_descriptor = json.loads(json.dumps(base_descriptor))
    pre_2024_descriptor["descriptor_id"] = "pre-2024-descriptor"
    pre_2024_descriptor["source_request_id"] = "pre-2024-request"
    pre_2024_descriptor["source_trial_context"]["market_start"] = "2023-12-31T00:00:00+00:00"
    payload["descriptors"] = [proxy_descriptor, pre_2024_descriptor]
    payload["bundle_id"] = "blocked-preflight-bundle"
    bundle_path = tmp_path / "blocked_bundle" / "strict_validation_request_bundle.json"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    preflight = preflight_sandbox_strict_validation_descriptors(
        bundle_path,
        output_dir=tmp_path / "preflight",
    )
    rows = {row["descriptor_id"]: row for row in preflight["descriptors"]}

    assert preflight["accepted_descriptor_count"] == 0
    assert preflight["blocked_descriptor_count"] == 2
    assert rows["proxy-descriptor"]["accepted_for_strict_validation_planning"] is False
    assert rows["proxy-descriptor"]["blocker_reasons"] == ["blocked_proxy_only_strategy"]
    assert rows["pre-2024-descriptor"]["accepted_for_strict_validation_planning"] is False
    assert rows["pre-2024-descriptor"]["blocker_reasons"] == ["blocked_pre_2024_window"]
    assert preflight["blocker_reason_counts"] == {
        "blocked_pre_2024_window": 1,
        "blocked_proxy_only_strategy": 1,
    }
    assert preflight["strict_validation_executed"] is False
    assert preflight["candidate_pack_written"] is False


def test_strict_validation_descriptor_preflight_fails_closed_on_boundary_violation(
    tmp_path: Path,
) -> None:
    market_path = tmp_path / "archives" / "okx_btcusdt_12h.csv"
    market_path.parent.mkdir(parents=True)
    _market_frame().to_csv(market_path, index=False)
    venue = VenueArchiveDescriptor(
        descriptor_id="okx-btc-2024",
        venue="okx",
        symbol="BTCUSDT",
        data_family="kline",
        interval="12h",
        window=DataWindow("2024-01-01", "2024-02-15"),
        data_path=market_path,
    )
    run = run_sandbox_archive_sweep(
        spec=_spec("strict-validation-preflight-unsafe"),
        strategies=[_strategy()],
        venues=[venue],
        output_root=tmp_path / "runs",
    )
    bundle = export_sandbox_validation_request_bundle(
        run.artifacts.run_dir,
        output_dir=tmp_path / "bundle",
    )
    payload = json.loads(Path(str(bundle["bundle_json_path"])).read_text(encoding="utf-8"))
    payload["descriptors"][0]["candidate_pack_eligible"] = True
    unsafe_bundle_path = tmp_path / "unsafe_bundle" / "strict_validation_request_bundle.json"
    unsafe_bundle_path.parent.mkdir(parents=True)
    unsafe_bundle_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    output_dir = tmp_path / "preflight"

    with pytest.raises(ValueError, match="violates sandbox boundary"):
        preflight_sandbox_strict_validation_descriptors(
            unsafe_bundle_path,
            output_dir=output_dir,
        )

    assert not output_dir.exists()

    unsafe_mode_payload = json.loads(Path(str(bundle["bundle_json_path"])).read_text(encoding="utf-8"))
    unsafe_mode_payload["descriptors"][0]["descriptor_only"] = False
    unsafe_mode_bundle_path = tmp_path / "unsafe_mode_bundle" / "strict_validation_request_bundle.json"
    unsafe_mode_bundle_path.parent.mkdir(parents=True)
    unsafe_mode_bundle_path.write_text(
        json.dumps(unsafe_mode_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must remain descriptor-only"):
        preflight_sandbox_strict_validation_descriptors(
            unsafe_mode_bundle_path,
            output_dir=output_dir,
        )

    assert not output_dir.exists()


def test_sandbox_archive_sweep_preserves_container_metadata_in_source_context(tmp_path: Path) -> None:
    zip_path = tmp_path / "hyperliquid_BTC_trade.zip"

    def jsonl(rows: list[dict[str, object]]) -> str:
        return "\n".join(json.dumps(row) for row in rows)

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "chunks/b.jsonl",
            jsonl(
                [
                    {
                        "time": "2024-01-01T00:01:00Z",
                        "px": "101.0",
                        "fallback_signal": 0,
                    },
                    {
                        "time": "2024-01-01T00:02:00Z",
                        "px": "104.0",
                        "fallback_signal": 0,
                    },
                ]
            ),
        )
        archive.writestr(
            "chunks/a.jsonl",
            jsonl(
                [
                    {
                        "time": "2024-01-01T00:00:00Z",
                        "px": "100.0",
                        "fallback_signal": 1,
                    }
                ]
            ),
        )
        archive.writestr(
            "chunks/ignored.ndjson",
            jsonl([{"time": "2024-01-01T00:03:00Z", "px": "999.0", "fallback_signal": 0}]),
        )

    venue = VenueArchiveDescriptor(
        descriptor_id="hyperliquid-container-sweep-btc",
        venue="hyperliquid",
        symbol="BTC",
        data_family="trade",
        data_path=zip_path,
        window=DataWindow("2024-01-01", "2024-01-01"),
    )
    spec = SandboxRunSpec(
        run_id="archive-sweep-container-source-metadata",
        data_window=DataWindow("2024-01-01", "2024-01-01"),
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=1,
        rank_top_n=5,
    )
    strategy = StrategyCatalogRow("zip-long", "container-source", "fallback_signal")

    run = run_sandbox_archive_sweep(
        spec=spec,
        strategies=[strategy],
        venues=[venue],
        output_root=tmp_path / "out",
    )

    result = run.results[0]
    manifest = json.loads(run.artifacts.manifest_path.read_text(encoding="utf-8"))
    rankings = pd.read_parquet(run.artifacts.rankings_parquet_path)
    ranking_metadata = json.loads(rankings["metadata"].iloc[0])
    requests = json.loads(run.artifacts.evidence_requests_json_path.read_text(encoding="utf-8"))
    market_source = result.metadata["market_source"]
    manifest_source = manifest["market_sources"][0]
    ranking_source = ranking_metadata["market_source"]
    request_source = requests[0]["source_trial_context"]["market_source"]

    assert result.status == "screened"
    assert market_source["container_kind"] == "zip"
    assert market_source["selected_member_suffix"] == ".jsonl"
    assert market_source["selected_member_count"] == 2
    assert market_source["selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert market_source["available_member_suffix_counts"] == {".jsonl": 2, ".ndjson": 1}
    assert market_source["loadable_member_count"] == 3
    assert market_source["container_member_metadata"]["container_kind"] == "zip"
    assert manifest_source["container_kind"] == "zip"
    assert ranking_source["selected_member_count"] == 2
    assert request_source["selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert request_source["data_path"] == str(zip_path)

    bundle = export_sandbox_validation_request_bundle(run.artifacts.run_dir, output_dir=tmp_path / "bundle")
    descriptor = bundle["descriptors"][0]
    bundle_frame = pd.read_parquet(Path(str(bundle["bundle_parquet_path"])))
    parquet_row = bundle_frame.iloc[0]

    assert descriptor["source_container_kind"] == "zip"
    assert descriptor["source_selected_member_suffix"] == ".jsonl"
    assert descriptor["source_selected_member_count"] == 2
    assert descriptor["source_selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert descriptor["source_available_member_suffix_counts"] == {".jsonl": 2, ".ndjson": 1}
    assert descriptor["source_loadable_member_count"] == 3
    assert descriptor["source_market_source"]["container_member_metadata"]["selected_member_count"] == 2
    assert parquet_row["source_container_kind"] == "zip"
    assert parquet_row["source_selected_member_count"] == 2
    assert json.loads(parquet_row["source_selected_member_name_sample"]) == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert json.loads(parquet_row["source_available_member_suffix_counts"]) == {".jsonl": 2, ".ndjson": 1}


def test_sandbox_archive_sweep_uses_preloaded_market_data_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_path = tmp_path / "cached_market.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0 + index for index in range(8)],
            "signal": [1] * 8,
        }
    ).to_csv(market_path, index=False)
    venue = VenueArchiveDescriptor(
        descriptor_id="okx-cache-sweep",
        venue="okx",
        symbol="BTCUSDT",
        data_family="kline",
        interval="1h",
        data_path=market_path,
        window=DataWindow("2024-01-01", "2024-01-01"),
        source_integrity={"sha256": _sha256(market_path), "byte_size": market_path.stat().st_size},
    )
    spec = SandboxRunSpec(
        run_id="archive-sweep-cache",
        data_window=DataWindow("2024-01-01", "2024-01-01"),
        holding_periods=(1,),
        min_trades=1,
    )
    strategy = StrategyCatalogRow("cached-long", "routing", "signal")
    cache = market_data_module.SandboxMarketDataCache()
    cache.load_frame(market_path)
    cache.require_descriptor_source_integrity(venue, data_path=market_path)
    read_count = 0

    def counting_read_raw_table(source_path: Path) -> pd.DataFrame:
        nonlocal read_count
        read_count += 1
        return pd.read_csv(source_path)

    monkeypatch.setattr(market_data_module, "_read_raw_table", counting_read_raw_table)

    run = run_sandbox_archive_sweep(
        spec=spec,
        strategies=[strategy],
        venues=[venue],
        output_root=tmp_path / "out",
        market_data_cache=cache,
    )

    assert read_count == 0
    assert len(run.results) == 1
    assert run.results[0].metadata["market_source"]["descriptor_id"] == "okx-cache-sweep"


def test_sandbox_archive_sweep_loads_descriptor_frames_sequentially(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptors: list[VenueArchiveDescriptor] = []
    frames: dict[str, pd.DataFrame] = {}
    for index, venue_name in enumerate(("okx", "bybit", "hyperliquid")):
        descriptor_id = f"{venue_name}-sequential-btcusdt"
        frame = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=8, freq="1h", tz="UTC"),
                "close": [100.0 + index + row for row in range(8)],
                "signal": [1] * 8,
            }
        )
        market_path = tmp_path / f"{descriptor_id}.csv"
        frame.to_csv(market_path, index=False)
        descriptors.append(
            VenueArchiveDescriptor(
                descriptor_id=descriptor_id,
                venue=venue_name,
                symbol="BTCUSDT",
                data_family="kline",
                interval="1h",
                data_path=market_path,
                window=DataWindow("2024-01-01", "2024-01-01"),
                source_integrity={"sha256": _sha256(market_path), "byte_size": market_path.stat().st_size},
            )
        )
        frames[descriptor_id] = load_market_frame_for_descriptor(descriptors[-1])
    spec = SandboxRunSpec(
        run_id="archive-sweep-sequential",
        data_window=DataWindow("2024-01-01", "2024-01-01"),
        holding_periods=(1, 2),
        min_trades=1,
        rank_top_n=4,
    )
    strategies = [
        StrategyCatalogRow("sequential-long", "routing", "signal"),
        StrategyCatalogRow("sequential-short", "routing", "signal", side="short"),
    ]
    load_order: list[str] = []
    active_load_count = 0
    max_active_load_count = 0
    original_loader = runner_module.load_market_frame_for_descriptor

    def counting_loader(descriptor: VenueArchiveDescriptor, *, fallback_path: str | Path | None = None) -> pd.DataFrame:
        nonlocal active_load_count, max_active_load_count
        active_load_count += 1
        max_active_load_count = max(max_active_load_count, active_load_count)
        try:
            load_order.append(descriptor.descriptor_id)
            return original_loader(descriptor, fallback_path=fallback_path)
        finally:
            active_load_count -= 1

    monkeypatch.setattr(runner_module, "load_market_frame_for_descriptor", counting_loader)

    run = run_sandbox_archive_sweep(
        spec=spec,
        strategies=strategies,
        venues=descriptors,
        output_root=tmp_path / "out",
    )
    direct_results = run_fixed_hold_sweep_for_venue_frames(
        market_frames=frames,
        run_spec=spec,
        strategies=strategies,
        venues=descriptors,
    )

    assert load_order == [descriptor.descriptor_id for descriptor in descriptors]
    assert max_active_load_count == 1
    assert [(result.trial_id, result.rank) for result in run.results] == [
        (result.trial_id, result.rank) for result in direct_results
    ]
    assert len(run.results) == spec.rank_top_n


def test_sandbox_analysis_summarizes_compact_artifacts(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-analysis-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx"), _venue("hyperliquid")],
        output_root=tmp_path,
    )

    payload = summarize_sandbox_run(run.artifacts.run_dir, top_n=2)
    report = json.loads(Path(str(payload["analysis_report_path"])).read_text(encoding="utf-8"))

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["sandbox_only"] is True
    assert payload["candidate_evidence"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["result_count"] == len(run.results)
    assert payload["status_counts"]["screened"] >= 1
    assert payload["venue_counts"] == {"okx": 2, "hyperliquid": 2}
    assert payload["evidence_request_count"] == len(run.evidence_requests)
    assert len(payload["top_results"]) == 2
    assert payload["top_results"][0]["rank"] == 1
    assert payload["analysis_bucket_rollup_version"] == 1
    assert payload["analysis_bucket_rollup_count"] == len(payload["analysis_bucket_rollups"])
    assert payload["analysis_bucket_rollup_count"] >= 6
    trial_ids = {result.trial_id for result in run.results}
    okx_rollup = next(
        rollup
        for rollup in payload["analysis_bucket_rollups"]
        if rollup["rollup_type"] == "venue" and rollup["bucket_values"] == {"venue": "okx"}
    )
    venue_family_rollup = next(
        rollup
        for rollup in payload["analysis_bucket_rollups"]
        if rollup["rollup_type"] == "venue_family"
        and rollup["bucket_values"] == {"venue": "okx", "family": "transparent_motif_fallback"}
    )
    assert okx_rollup["research_only"] is True
    assert okx_rollup["observe_only"] is True
    assert okx_rollup["promotion_ready"] is False
    assert okx_rollup["candidate_pack_eligible"] is False
    assert okx_rollup["result_count"] == 2
    assert okx_rollup["best_trial_id"] in trial_ids
    assert okx_rollup["strict_validation_authorized"] is False
    assert okx_rollup["candidate_pack_authorized"] is False
    assert venue_family_rollup["result_count"] == 2
    assert venue_family_rollup["best_family"] == "transparent_motif_fallback"
    assert report["analysis_report_path"] == payload["analysis_report_path"]
    assert report["candidate_pack_eligible"] is False
    assert report["analysis_bucket_rollups"] == payload["analysis_bucket_rollups"]


def test_sandbox_analysis_rejects_promotable_rankings(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-analysis-boundary-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue()],
        output_root=tmp_path,
    )
    rankings = pd.read_parquet(run.artifacts.rankings_parquet_path)
    rankings["promotion_ready"] = True
    rankings.to_parquet(run.artifacts.rankings_parquet_path, index=False)
    _refresh_manifest_artifact_integrity(run.artifacts.manifest_path, "rankings_parquet", run.artifacts.rankings_parquet_path)

    with pytest.raises(ValueError, match="non-promotable boundary"):
        summarize_sandbox_run(run.artifacts.run_dir)


def test_sandbox_hypothesis_falsification_marks_requested_and_falsified(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-hypothesis-falsification-run"),
        market_frame=_market_frame(),
        strategies=[_strategy(), _short_strategy()],
        venues=[_venue("okx")],
        output_root=tmp_path,
    )

    payload = summarize_sandbox_hypotheses(run.artifacts.run_dir)
    report = json.loads(Path(str(payload["hypothesis_falsification_json_path"])).read_text(encoding="utf-8"))
    frame = pd.read_parquet(Path(str(payload["hypothesis_falsification_parquet_path"])))
    decisions = {row["hypothesis_id"]: row["falsification_decision"] for row in payload["hypotheses"]}

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["hypothesis_count"] == 2
    assert decisions["fallback-long"] == "request_strict_validation"
    assert decisions["fallback-short"] == "falsified_in_sandbox"
    assert payload["decision_counts"]["request_strict_validation"] == 1
    assert payload["decision_counts"]["falsified_in_sandbox"] == 1
    assert report["hypothesis_falsification_json_path"] == payload["hypothesis_falsification_json_path"]
    assert set(frame["hypothesis_id"]) == {"fallback-long", "fallback-short"}
    assert set(frame["candidate_pack_eligible"]) == {False}


def test_sandbox_validation_request_bundle_exports_descriptor_only_handoff(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-validation-bundle-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx")],
        output_root=tmp_path,
    )

    payload = export_sandbox_validation_request_bundle(run.artifacts.run_dir)
    frame = pd.read_parquet(Path(str(payload["bundle_parquet_path"])))

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["source_scope"] == "run"
    assert payload["strict_validation_command"] == "run-historical-research-cycle"
    assert payload["execution_mode"] == "descriptor_only_no_execution"
    assert payload["strict_validation_executed"] is False
    assert payload["candidate_pack_written"] is False
    assert payload["request_count"] == len(run.evidence_requests)
    assert payload["deduped_request_count"] == len(run.evidence_requests)
    assert Path(str(payload["bundle_json_path"])).exists()
    assert set(frame["strict_validation_command"]) == {"run-historical-research-cycle"}
    assert set(frame["candidate_pack_eligible"]) == {False}
    assert set(frame["candidate_pack_written"]) == {False}


def test_sandbox_suite_runs_multiple_cases_and_writes_indexes(tmp_path: Path) -> None:
    suite_path = _write_suite_fixture(tmp_path)
    suite = load_sandbox_suite_spec(suite_path)

    result = run_sandbox_suite(suite=suite, output_root=tmp_path / "out")
    manifest = json.loads(result.artifacts.suite_manifest_path.read_text(encoding="utf-8"))
    index_payload = json.loads(result.artifacts.suite_index_json_path.read_text(encoding="utf-8"))
    requests = json.loads(result.artifacts.suite_evidence_requests_json_path.read_text(encoding="utf-8"))
    index_frame = pd.read_parquet(result.artifacts.suite_index_parquet_path)
    request_frame = pd.read_parquet(result.artifacts.suite_evidence_requests_parquet_path)

    assert suite.cases[0].spec_path == (suite_path.parent / "case-okx" / "spec.json").resolve()
    assert manifest["research_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["candidate_pack_eligible"] is False
    assert manifest["suite_spec"]["suite_id"] == "suite-batch-smoke"
    assert manifest["case_count"] == 2
    assert manifest["completed_case_count"] == 2
    assert manifest["skipped_case_count"] == 0
    assert manifest["market_data_cache_scope"] == "suite_sequential"
    assert manifest["input_cache_scope"] == "suite_sequential"
    assert manifest["preflight_trial_estimate"] == 2
    assert manifest["preflight_runnable_trial_estimate"] == 2
    assert manifest["preflight_blocked_trial_estimate"] == 0
    assert set(manifest["artifact_integrity"]) == {
        "suite_index_json",
        "suite_index_parquet",
        "suite_evidence_requests_json",
        "suite_evidence_requests_parquet",
    }
    for key, artifact_key in (
        ("suite_index_json", "suite_index_json_path"),
        ("suite_index_parquet", "suite_index_parquet_path"),
        ("suite_evidence_requests_json", "suite_evidence_requests_json_path"),
        ("suite_evidence_requests_parquet", "suite_evidence_requests_parquet_path"),
    ):
        artifact_path = Path(str(manifest["artifacts"][artifact_key]))
        assert manifest["artifact_integrity"][key]["sha256"] == _sha256(artifact_path)
        assert manifest["artifact_integrity"][key]["byte_size"] == artifact_path.stat().st_size
    integrity_report = verify_sandbox_artifact_integrity(result.artifacts.suite_dir)
    integrity_frame = pd.read_parquet(str(integrity_report["report_parquet_path"]))
    assert integrity_report["verification_status"] == "passed"
    assert integrity_report["source_scope"] == "suite"
    assert integrity_report["checked_artifact_count"] == 4
    assert integrity_report["verified_artifact_count"] == 4
    assert integrity_report["failed_artifact_count"] == 0
    assert set(integrity_frame["artifact_key"]) == set(manifest["artifact_integrity"])
    assert set(integrity_frame["status"]) == {"matched"}
    assert result.artifacts.suite_dir == tmp_path / "out" / "suite-batch-smoke"
    assert len(result.case_results) == 2
    assert len(index_payload["cases"]) == 2
    assert set(index_frame["case_id"]) == {"case-okx", "case-bybit"}
    assert set(index_frame["case_status"]) == {"completed"}
    assert set(index_frame["preflight_runnable_trial_estimate"]) == {1}
    assert set(index_frame["preflight_blocked_trial_estimate"]) == {0}
    assert set(index_frame["screened_count"]) == {1}
    assert len(requests) == 2
    assert len(request_frame) == 2
    assert {request["suite_id"] for request in requests} == {"suite-batch-smoke"}
    assert {request["case_id"] for request in requests} == {"case-okx", "case-bybit"}
    assert all(request["candidate_pack_eligible"] is False for request in requests)
    assert all(Path(str(row["preflight_json_path"])).exists() for row in index_payload["cases"])


def test_sandbox_suite_reuses_market_data_cache_across_sequential_cases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite_path = _write_shared_market_suite_fixture(tmp_path)
    suite = load_sandbox_suite_spec(suite_path)
    read_count = 0

    def counting_read_raw_table(source_path: Path) -> pd.DataFrame:
        nonlocal read_count
        read_count += 1
        return pd.read_csv(source_path)

    monkeypatch.setattr(market_data_module, "_read_raw_table", counting_read_raw_table)

    result = run_sandbox_suite(suite=suite, output_root=tmp_path / "out")
    manifest = json.loads(result.artifacts.suite_manifest_path.read_text(encoding="utf-8"))

    assert read_count == 1
    assert manifest["market_data_cache_scope"] == "suite_sequential"
    assert manifest["completed_case_count"] == 2
    assert manifest["preflight_runnable_trial_estimate"] == 2
    assert len(result.case_results) == 2
    assert [row["case_status"] for row in result.index_rows] == ["completed", "completed"]


def test_sandbox_suite_reuses_input_cache_across_sequential_cases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite_path = _write_shared_input_suite_fixture(tmp_path)
    suite = load_sandbox_suite_spec(suite_path)
    load_counts = {"spec": 0, "catalog": 0, "venues": 0}
    original_load_spec = suite_module.load_sandbox_run_spec
    original_load_catalog = suite_module.load_strategy_catalog
    original_load_venues = suite_module.load_venue_archive_descriptors

    def counting_load_spec(path: str | Path) -> SandboxRunSpec:
        load_counts["spec"] += 1
        return original_load_spec(path)

    def counting_load_catalog(path: str | Path) -> list[StrategyCatalogRow]:
        load_counts["catalog"] += 1
        return original_load_catalog(path)

    def counting_load_venues(path: str | Path) -> list[VenueArchiveDescriptor]:
        load_counts["venues"] += 1
        return original_load_venues(path)

    monkeypatch.setattr(suite_module, "load_sandbox_run_spec", counting_load_spec)
    monkeypatch.setattr(suite_module, "load_strategy_catalog", counting_load_catalog)
    monkeypatch.setattr(suite_module, "load_venue_archive_descriptors", counting_load_venues)

    result = run_sandbox_suite(suite=suite, output_root=tmp_path / "out")
    manifest = json.loads(result.artifacts.suite_manifest_path.read_text(encoding="utf-8"))

    assert load_counts == {"spec": 1, "catalog": 1, "venues": 1}
    assert manifest["input_cache_scope"] == "suite_sequential"
    assert manifest["market_data_cache_scope"] == "suite_sequential"
    assert manifest["completed_case_count"] == 2
    assert [row["case_id"] for row in result.index_rows] == ["case-first", "case-second"]
    assert [row["case_status"] for row in result.index_rows] == ["completed", "completed"]


def test_sandbox_suite_parallel_execution_preserves_case_order(tmp_path: Path) -> None:
    suite_path = _write_suite_fixture(tmp_path, suite_id="parallel-suite-smoke")
    suite = load_sandbox_suite_spec(suite_path)

    result = run_sandbox_suite(suite=suite, output_root=tmp_path / "out", max_workers=2)
    manifest = json.loads(result.artifacts.suite_manifest_path.read_text(encoding="utf-8"))
    index_payload = json.loads(result.artifacts.suite_index_json_path.read_text(encoding="utf-8"))
    requests = json.loads(result.artifacts.suite_evidence_requests_json_path.read_text(encoding="utf-8"))
    index_frame = pd.read_parquet(result.artifacts.suite_index_parquet_path)

    assert manifest["max_workers"] == 2
    assert manifest["market_data_cache_scope"] == "case_local_parallel"
    assert manifest["input_cache_scope"] == "case_local_parallel"
    assert manifest["case_count"] == 2
    assert manifest["completed_case_count"] == 2
    assert [row["case_id"] for row in index_payload["cases"]] == ["case-okx", "case-bybit"]
    assert list(index_frame["case_id"]) == ["case-okx", "case-bybit"]
    assert [request["case_id"] for request in requests] == ["case-okx", "case-bybit"]
    assert [case_result.case.case_id for case_result in result.case_results] == ["case-okx", "case-bybit"]
    assert all(row["research_only"] is True for row in index_payload["cases"])
    assert all(request["candidate_pack_eligible"] is False for request in requests)


def test_sandbox_suite_preflight_skips_fully_blocked_cases(tmp_path: Path) -> None:
    suite_dir = tmp_path / "mixed_suite"
    suite_dir.mkdir()
    cases: list[dict[str, str]] = []
    for case_id, signal_column, market_columns in (
        ("case-runnable", "signal", {"signal": [1] * 8}),
        ("case-blocked", "missing_signal", {}),
    ):
        case_dir = suite_dir / case_id
        case_dir.mkdir()
        (case_dir / "spec.json").write_text(
            json.dumps(
                {
                    "run_id": f"{case_id}-run",
                    "data_window": {"start": "2024-01-01", "end": "2024-01-02"},
                    "holding_periods": [1],
                    "round_trip_cost_bps": 0.0,
                    "min_trades": 1,
                    "max_evidence_requests": 1,
                    "rank_top_n": 5,
                }
            ),
            encoding="utf-8",
        )
        pd.DataFrame(
            [
                {
                    "hypothesis_id": f"{case_id}-long",
                    "family": "suite_preflight_gate",
                    "signal_column": signal_column,
                    "side": "long",
                }
            ]
        ).to_csv(case_dir / "catalog.csv", index=False)
        pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=8, freq="1h", tz="UTC"),
                "close": [100 + index for index in range(8)],
                **market_columns,
            }
        ).to_csv(case_dir / "market.csv", index=False)
        (case_dir / "venues.json").write_text(
            json.dumps(
                {
                    "venue_archives": [
                        {
                            "descriptor_id": f"{case_id}-okx",
                            "venue": "okx",
                            "symbol": "BTCUSDT",
                            "data_family": "kline",
                            "data_path": "market.csv",
                            "window": {"start": "2024-01-01", "end": "2024-01-02"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        cases.append(
            {
                "case_id": case_id,
                "spec": f"{case_id}/spec.json",
                "strategy_catalog": f"{case_id}/catalog.csv",
                "venue_archives": f"{case_id}/venues.json",
            }
        )
    suite_path = suite_dir / "suite.json"
    suite_path.write_text(json.dumps({"suite_id": "mixed-suite-preflight", "cases": cases}), encoding="utf-8")

    suite = load_sandbox_suite_spec(suite_path)
    suite_run = run_sandbox_suite(suite=suite, output_root=tmp_path / "out")
    manifest = json.loads(suite_run.artifacts.suite_manifest_path.read_text(encoding="utf-8"))
    index_payload = json.loads(suite_run.artifacts.suite_index_json_path.read_text(encoding="utf-8"))
    requests = json.loads(suite_run.artifacts.suite_evidence_requests_json_path.read_text(encoding="utf-8"))
    rows = {row["case_id"]: row for row in index_payload["cases"]}
    hypothesis = summarize_sandbox_suite_hypotheses(suite_run.artifacts.suite_dir)
    bundle = export_sandbox_suite_validation_request_bundle(suite_run.artifacts.suite_dir)

    assert manifest["completed_case_count"] == 1
    assert manifest["skipped_case_count"] == 1
    assert manifest["preflight_trial_estimate"] == 2
    assert manifest["preflight_runnable_trial_estimate"] == 1
    assert manifest["preflight_blocked_trial_estimate"] == 1
    assert manifest["result_count"] == 1
    assert manifest["evidence_request_count"] == 1
    assert len(suite_run.case_results) == 2
    assert len(requests) == 1
    assert requests[0]["case_id"] == "case-runnable"
    assert rows["case-runnable"]["case_status"] == "completed"
    assert rows["case-blocked"]["case_status"] == "blocked_by_preflight"
    assert rows["case-blocked"]["run_dir"] is None
    assert rows["case-blocked"]["manifest_path"] is None
    assert rows["case-blocked"]["evidence_request_count"] == 0
    assert rows["case-blocked"]["preflight_runnable_trial_estimate"] == 0
    assert rows["case-blocked"]["preflight_blocked_trial_estimate"] == 1
    assert "missing_signal_column:missing_signal" in rows["case-blocked"]["preflight_blocker_reason_counts"]
    assert Path(str(rows["case-blocked"]["preflight_json_path"])).exists()
    assert Path(str(rows["case-runnable"]["manifest_path"])).exists()
    assert hypothesis["source_run_count"] == 1
    assert hypothesis["skipped_case_count"] == 1
    assert bundle["request_count"] == 1
    assert bundle["deduped_request_count"] == 1


def test_sandbox_suite_hypothesis_falsification_combines_case_runs(tmp_path: Path) -> None:
    suite_path = _write_suite_fixture(tmp_path, suite_id="suite-hypothesis-index")
    suite = load_sandbox_suite_spec(suite_path)
    suite_run = run_sandbox_suite(suite=suite, output_root=tmp_path / "out")

    payload = summarize_sandbox_suite_hypotheses(suite_run.artifacts.suite_dir)
    frame = pd.read_parquet(Path(str(payload["hypothesis_falsification_parquet_path"])))

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["suite_id"] == "suite-hypothesis-index"
    assert payload["source_run_count"] == 2
    assert payload["hypothesis_count"] == 2
    assert payload["decision_counts"]["request_strict_validation"] == 2
    assert set(frame["scope"]) == {"suite"}
    assert set(frame["candidate_pack_eligible"]) == {False}


def test_sandbox_suite_validation_request_bundle_dedupes_requests(tmp_path: Path) -> None:
    suite_path = _write_suite_fixture(tmp_path, suite_id="suite-validation-bundle")
    suite = load_sandbox_suite_spec(suite_path)
    suite_run = run_sandbox_suite(suite=suite, output_root=tmp_path / "out")
    requests_path = suite_run.artifacts.suite_evidence_requests_json_path
    requests = json.loads(requests_path.read_text(encoding="utf-8"))
    requests.append(dict(requests[0]))
    requests_path.write_text(json.dumps(requests, indent=2, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_integrity(
        suite_run.artifacts.suite_manifest_path,
        "suite_evidence_requests_json",
        suite_run.artifacts.suite_evidence_requests_json_path,
    )

    payload = export_sandbox_suite_validation_request_bundle(suite_run.artifacts.suite_dir)
    frame = pd.read_parquet(Path(str(payload["bundle_parquet_path"])))

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["source_scope"] == "suite"
    assert payload["request_count"] == 3
    assert payload["deduped_request_count"] == 2
    assert payload["duplicates_removed"] == 1
    assert set(frame["source_scope"]) == {"suite"}
    assert set(frame["strict_validation_executed"]) == {False}
    assert set(frame["candidate_pack_eligible"]) == {False}


def test_sandbox_suite_consumers_reject_tampered_suite_children(tmp_path: Path) -> None:
    suite_path = _write_suite_fixture(tmp_path, suite_id="suite-tampered-consumers")
    suite = load_sandbox_suite_spec(suite_path)
    suite_run = run_sandbox_suite(suite=suite, output_root=tmp_path / "out")

    original_text = suite_run.artifacts.suite_evidence_requests_json_path.read_text(encoding="utf-8")
    suite_run.artifacts.suite_evidence_requests_json_path.write_text(f"{original_text}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="sandbox_suite_falsification_source failed sandbox artifact integrity"):
        summarize_sandbox_suite_hypotheses(suite_run.artifacts.suite_dir)
    with pytest.raises(ValueError, match="sandbox_suite_validation_bundle_source failed sandbox artifact integrity"):
        export_sandbox_suite_validation_request_bundle(suite_run.artifacts.suite_dir)

    assert not (suite_run.artifacts.suite_dir / "suite_hypothesis_falsification.json").exists()
    assert not (suite_run.artifacts.suite_dir / "suite_strict_validation_request_bundle.json").exists()


def test_sandbox_artifact_catalog_indexes_known_artifacts(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-artifact-catalog-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx")],
        output_root=tmp_path / "runs",
    )
    summarize_sandbox_run(run.artifacts.run_dir)
    summarize_sandbox_hypotheses(run.artifacts.run_dir)
    export_sandbox_validation_request_bundle(run.artifacts.run_dir)
    suite_path = _write_suite_fixture(tmp_path, suite_id="catalog-suite")
    suite = load_sandbox_suite_spec(suite_path)
    suite_run = run_sandbox_suite(suite=suite, output_root=tmp_path / "suites")
    summarize_sandbox_suite_hypotheses(suite_run.artifacts.suite_dir)
    export_sandbox_suite_validation_request_bundle(suite_run.artifacts.suite_dir)

    payload = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")
    frame = pd.read_parquet(Path(str(payload["catalog_parquet_path"])))
    sidecar_index_frame = pd.read_parquet(
        Path(str(payload["catalog_sidecar_index_parquet_path"]))
    )
    analysis_bucket_rollup_frame = pd.read_parquet(
        Path(str(payload["analysis_bucket_rollups_parquet_path"]))
    )
    global_top_hypothesis_frame = pd.read_parquet(
        Path(str(payload["global_top_hypotheses_parquet_path"]))
    )
    global_evidence_request_frame = pd.read_parquet(
        Path(str(payload["global_evidence_requests_parquet_path"]))
    )
    global_evidence_request_source_summary_frame = pd.read_parquet(
        Path(str(payload["global_evidence_request_source_summary_parquet_path"]))
    )
    global_evidence_request_source_priority_queue_frame = pd.read_parquet(
        Path(
            str(
                payload[
                    "global_evidence_request_source_priority_queue_parquet_path"
                ]
            )
        )
    )
    global_evidence_request_priority_queue_frame = pd.read_parquet(
        Path(str(payload["global_evidence_request_priority_queue_parquet_path"]))
    )
    global_evidence_request_bucket_queue_frame = pd.read_parquet(
        Path(str(payload["global_evidence_request_bucket_queue_parquet_path"]))
    )
    global_evidence_request_bucket_representatives_frame = pd.read_parquet(
        Path(
            str(
                payload[
                    "global_evidence_request_bucket_representatives_parquet_path"
                ]
            )
        )
    )
    global_bucket_top_bucket_frame = pd.read_parquet(
        Path(str(payload["global_bucket_top_buckets_parquet_path"]))
    )
    iteration_venue_gap_worklist_frame = pd.read_parquet(
        Path(str(payload["iteration_venue_expansion_gap_worklist_parquet_path"]))
    )
    strict_bundle_queue_frame = pd.read_parquet(
        Path(str(payload["strict_validation_bundle_queue_parquet_path"]))
    )
    strict_descriptor_frame = pd.read_parquet(
        Path(str(payload["strict_validation_descriptor_parquet_path"]))
    )
    strict_descriptor_queue_frame = pd.read_parquet(
        Path(str(payload["strict_validation_descriptor_queue_parquet_path"]))
    )
    strict_descriptor_bucket_frame = pd.read_parquet(
        Path(str(payload["strict_validation_descriptor_bucket_queue_parquet_path"]))
    )
    strict_descriptor_bucket_representatives_frame = pd.read_parquet(
        Path(
            str(
                payload[
                    "strict_validation_descriptor_bucket_representatives_parquet_path"
                ]
            )
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert Path(str(payload["catalog_json_path"])).exists()
    assert Path(str(payload["catalog_sidecar_index_parquet_path"])).exists()
    assert Path(str(payload["analysis_bucket_rollups_parquet_path"])).exists()
    assert Path(str(payload["global_top_hypotheses_parquet_path"])).exists()
    assert Path(str(payload["global_evidence_requests_parquet_path"])).exists()
    assert Path(
        str(payload["global_evidence_request_source_summary_parquet_path"])
    ).exists()
    assert Path(
        str(payload["global_evidence_request_source_priority_queue_parquet_path"])
    ).exists()
    assert Path(
        str(payload["global_evidence_request_priority_queue_parquet_path"])
    ).exists()
    assert Path(str(payload["global_evidence_request_bucket_queue_parquet_path"])).exists()
    assert Path(
        str(payload["global_evidence_request_bucket_representatives_parquet_path"])
    ).exists()
    assert Path(str(payload["global_bucket_top_buckets_parquet_path"])).exists()
    assert Path(
        str(payload["iteration_venue_expansion_gap_worklist_parquet_path"])
    ).exists()
    assert payload["catalog_sidecar_index_row_count"] == 21
    assert len(payload["catalog_sidecar_index"]) == 21
    assert len(sidecar_index_frame) == 21
    assert set(sidecar_index_frame["sidecar_category"]) == {
        "analysis",
        "catalog",
        "iteration_index",
        "leaderboard",
        "replay_batch_plan",
        "strict_validation",
    }
    assert {
        "agent_read_order",
        "agent_read_group",
        "agent_first_read",
        "agent_navigation_hint",
    }.issubset(sidecar_index_frame.columns)
    sidecar_navigation = {
        str(row["sidecar_name"]): row for row in sidecar_index_frame.to_dict("records")
    }
    assert sidecar_navigation["artifact_catalog"]["agent_read_order"] == 10
    assert (
        sidecar_navigation["global_evidence_request_source_priority_queue"][
            "agent_read_order"
        ]
        == 20
    )
    assert (
        sidecar_navigation["global_evidence_request_source_priority_queue"][
            "agent_read_group"
        ]
        == "strict_validation_source_triage"
    )
    assert (
        sidecar_navigation["global_evidence_request_source_summary"]["agent_read_order"]
        > sidecar_navigation["global_evidence_request_source_priority_queue"][
            "agent_read_order"
        ]
    )
    first_read_sidecars = [
        str(row["sidecar_name"])
        for row in sorted(
            sidecar_index_frame.to_dict("records"),
            key=lambda item: int(item["agent_read_order"]),
        )
        if bool(row["agent_first_read"])
    ]
    assert first_read_sidecars == [
        "artifact_catalog",
        "global_evidence_request_source_priority_queue",
        "global_evidence_request_priority_queue",
        "strict_validation_descriptor_queue",
        "iteration_agent_action_plan",
        "iteration_venue_expansion_gap_worklist",
        "replay_batch_plan_bucket_queue",
    ]
    assert all(
        str(hint).strip()
        for hint in sidecar_index_frame["agent_navigation_hint"].tolist()
    )
    assert set(sidecar_index_frame["parquet_written"]) == {True}
    assert set(sidecar_index_frame["descriptor_only"]) == {True}
    assert set(sidecar_index_frame["strict_validation_executed"]) == {False}
    assert set(sidecar_index_frame["candidate_pack_written"]) == {False}
    assert set(sidecar_index_frame["replay_command_execution_authorized"]) == {False}
    assert set(sidecar_index_frame["strict_validation_authorized"]) == {False}
    assert set(sidecar_index_frame["candidate_pack_write_authorized"]) == {False}
    assert set(sidecar_index_frame["candidate_pack_eligible"]) == {False}
    assert all(Path(str(path)).exists() for path in sidecar_index_frame["sidecar_path"])
    for row in sidecar_index_frame.to_dict("records"):
        sidecar_path = Path(str(row["sidecar_path"]))
        assert bool(row["sidecar_exists"]) is True
        assert int(row["sidecar_size_bytes"]) == sidecar_path.stat().st_size
        assert row["sidecar_sha256"] == _sha256(sidecar_path)
    for item in payload["catalog_sidecar_index"]:
        sidecar_path = Path(str(item["sidecar_path"]))
        assert item["sidecar_exists"] is True
        assert int(item["sidecar_size_bytes"]) == sidecar_path.stat().st_size
        assert item["sidecar_sha256"] == _sha256(sidecar_path)
    assert payload["artifact_kind_counts"]["run_manifest"] >= 1
    assert payload["artifact_kind_counts"]["suite_manifest"] >= 1
    assert payload["artifact_kind_counts"]["run_analysis"] >= 1
    assert payload["artifact_kind_counts"]["run_hypothesis_falsification"] >= 1
    assert payload["artifact_kind_counts"]["suite_hypothesis_falsification"] >= 1
    assert payload["artifact_kind_counts"]["run_strict_validation_request_bundle"] >= 1
    assert payload["artifact_kind_counts"]["suite_strict_validation_request_bundle"] >= 1
    strict_bundle_rows = [
        row
        for row in payload["artifacts"]
        if row["artifact_kind"]
        in {"run_strict_validation_request_bundle", "suite_strict_validation_request_bundle"}
    ]
    assert len(strict_bundle_rows) == 2
    assert {row["strict_validation_source_scope"] for row in strict_bundle_rows} == {
        "run",
        "suite",
    }
    assert {row["strict_validation_execution_mode"] for row in strict_bundle_rows} == {
        "descriptor_only_no_execution"
    }
    assert {row["descriptor_only"] for row in strict_bundle_rows} == {True}
    assert {row["strict_validation_executed"] for row in strict_bundle_rows} == {False}
    assert {row["candidate_pack_written"] for row in strict_bundle_rows} == {False}
    assert all(row["strict_validation_request_count"] > 0 for row in strict_bundle_rows)
    assert all(row["strict_validation_deduped_request_count"] > 0 for row in strict_bundle_rows)
    assert all(
        row["evidence_request_count"] == row["strict_validation_request_count"]
        for row in strict_bundle_rows
    )
    assert all(
        row["descriptor_count"] == row["strict_validation_deduped_request_count"]
        for row in strict_bundle_rows
    )
    assert payload["strict_validation_bundle_queue_limit"] == 25
    assert payload["strict_validation_bundle_queue_count"] == 2
    assert payload["strict_validation_bundle_summary"] == {
        "artifact_count": 2,
        "deduped_request_count": sum(
            row["strict_validation_deduped_request_count"] for row in strict_bundle_rows
        ),
        "descriptor_count": sum(row["descriptor_count"] for row in strict_bundle_rows),
        "duplicates_removed": sum(
            row["strict_validation_duplicates_removed"] for row in strict_bundle_rows
        ),
        "request_count": sum(row["strict_validation_request_count"] for row in strict_bundle_rows),
        "source_scope_counts": {"run": 1, "suite": 1},
        "status_counts": {"descriptor_ready": 2},
    }
    assert [
        item["strict_validation_bundle_status"]
        for item in payload["strict_validation_bundle_queue"]
    ] == ["descriptor_ready", "descriptor_ready"]
    assert {
        item["source_scope"] for item in payload["strict_validation_bundle_queue"]
    } == {"run", "suite"}
    assert {
        item["strict_validation_authorized"]
        for item in payload["strict_validation_bundle_queue"]
    } == {False}
    assert {
        item["candidate_pack_write_authorized"]
        for item in payload["strict_validation_bundle_queue"]
    } == {False}
    assert all(
        item["request_count"] == item["descriptor_count"]
        for item in payload["strict_validation_bundle_queue"]
    )
    assert Path(str(payload["strict_validation_bundle_queue_parquet_path"])).exists()
    assert payload["strict_validation_bundle_queue_parquet_row_count"] == 2
    assert len(strict_bundle_queue_frame) == 2
    assert set(strict_bundle_queue_frame["strict_validation_bundle_status"]) == {
        "descriptor_ready"
    }
    assert set(strict_bundle_queue_frame["source_scope"]) == {"run", "suite"}
    assert set(strict_bundle_queue_frame["execution_mode"]) == {
        "descriptor_only_no_execution"
    }
    assert set(strict_bundle_queue_frame["descriptor_only"]) == {True}
    assert set(strict_bundle_queue_frame["strict_validation_executed"]) == {False}
    assert set(strict_bundle_queue_frame["candidate_pack_written"]) == {False}
    assert set(strict_bundle_queue_frame["strict_validation_authorized"]) == {False}
    assert set(strict_bundle_queue_frame["candidate_pack_write_authorized"]) == {False}
    assert set(strict_bundle_queue_frame["candidate_pack_eligible"]) == {False}
    assert strict_bundle_queue_frame["request_count"].sum() == sum(
        row["strict_validation_request_count"] for row in strict_bundle_rows
    )
    assert strict_bundle_queue_frame["deduped_request_count"].sum() == sum(
        row["strict_validation_deduped_request_count"] for row in strict_bundle_rows
    )
    assert Path(str(payload["strict_validation_descriptor_parquet_path"])).exists()
    assert payload["strict_validation_descriptor_parquet_row_count"] == sum(
        row["strict_validation_deduped_request_count"] for row in strict_bundle_rows
    )
    assert len(strict_descriptor_frame) == payload["strict_validation_descriptor_parquet_row_count"]
    descriptor_source_scope_counts = (
        strict_descriptor_frame["source_scope"].value_counts().sort_index().astype(int).to_dict()
    )
    descriptor_requested_validation_counts = (
        strict_descriptor_frame["requested_validation"].value_counts().sort_index().astype(int).to_dict()
    )
    descriptor_symbol_counts = (
        strict_descriptor_frame["symbol"].value_counts().sort_index().astype(int).to_dict()
    )
    descriptor_venue_counts = (
        strict_descriptor_frame["venue"].value_counts().sort_index().astype(int).to_dict()
    )
    assert payload["strict_validation_descriptor_summary"] == {
        "descriptor_count": payload["strict_validation_descriptor_parquet_row_count"],
        "requested_validation_counts": descriptor_requested_validation_counts,
        "source_scope_counts": descriptor_source_scope_counts,
        "status_counts": {"descriptor_ready": len(strict_descriptor_frame)},
        "symbol_counts": descriptor_symbol_counts,
        "venue_counts": descriptor_venue_counts,
    }
    assert set(strict_descriptor_frame["source_scope"]) == {"run", "suite"}
    assert "okx" in set(strict_descriptor_frame["venue"])
    assert strict_descriptor_frame["venue"].notna().all()
    assert set(strict_descriptor_frame["symbol"]) == {"BTCUSDT"}
    assert set(strict_descriptor_frame["requested_validation"]) == {
        "strict_research_cycle_request"
    }
    assert set(strict_descriptor_frame["strict_validation_command"]) == {
        "run-historical-research-cycle"
    }
    assert set(strict_descriptor_frame["execution_mode"]) == {"descriptor_only_no_execution"}
    assert set(strict_descriptor_frame["descriptor_only"]) == {True}
    assert set(strict_descriptor_frame["strict_validation_executed"]) == {False}
    assert set(strict_descriptor_frame["candidate_pack_written"]) == {False}
    assert set(strict_descriptor_frame["strict_validation_authorized"]) == {False}
    assert set(strict_descriptor_frame["candidate_pack_write_authorized"]) == {False}
    assert set(strict_descriptor_frame["candidate_pack_eligible"]) == {False}
    assert strict_descriptor_frame["source_trial_id"].notna().all()
    assert strict_descriptor_frame["source_market_start"].str.startswith("2024-").all()
    sidecar_row_counts = {
        str(row["sidecar_name"]): int(row["row_count"])
        for row in sidecar_index_frame.to_dict("records")
    }
    assert sidecar_row_counts["artifact_catalog"] == len(frame)
    assert sidecar_row_counts["analysis_bucket_rollups"] == len(
        analysis_bucket_rollup_frame
    )
    assert sidecar_row_counts["global_top_hypotheses"] == len(
        global_top_hypothesis_frame
    )
    assert payload["global_top_hypothesis_parquet_row_count"] == 0
    assert global_top_hypothesis_frame.empty
    assert "hypothesis_id" in global_top_hypothesis_frame.columns
    assert "candidate_pack_eligible" in global_top_hypothesis_frame.columns
    assert sidecar_row_counts["global_evidence_requests"] == len(
        global_evidence_request_frame
    )
    assert sidecar_row_counts["global_evidence_request_source_summary"] == len(
        global_evidence_request_source_summary_frame
    )
    assert sidecar_row_counts["global_evidence_request_source_priority_queue"] == len(
        global_evidence_request_source_priority_queue_frame
    )
    assert payload["global_evidence_request_parquet_row_count"] == 0
    assert payload["global_evidence_request_source_summary_parquet_row_count"] == 0
    assert (
        payload["global_evidence_request_source_priority_queue_parquet_row_count"]
        == 0
    )
    assert payload["global_evidence_request_source_priority_queue_count"] == 0
    assert payload["global_evidence_request_source_priority_queue_limit"] == 50
    assert payload["global_evidence_request_count"] == 0
    assert payload["global_evidence_request_unique_trial_count"] == 0
    assert payload["global_evidence_request_hypothesis_count"] == 0
    assert payload["global_evidence_request_requested_validation_counts"] == {}
    assert payload["global_evidence_request_leaderboard_decision_counts"] == {}
    assert payload["global_evidence_request_family_counts"] == {}
    assert payload["global_evidence_request_tested_venue_counts"] == {}
    assert payload["global_evidence_request_tested_symbol_counts"] == {}
    assert payload["global_evidence_request_summary"]["evidence_request_count"] == 0
    assert payload["global_evidence_request_summary"]["priority_queue_count"] == 0
    assert payload["global_evidence_request_summary"]["bucket_queue_count"] == 0
    assert (
        payload["global_evidence_request_summary"]["bucket_representative_count"]
        == 0
    )
    assert global_evidence_request_frame.empty
    assert "evidence_request_trial_id" in global_evidence_request_frame.columns
    assert "candidate_pack_eligible" in global_evidence_request_frame.columns
    assert global_evidence_request_source_summary_frame.empty
    assert (
        "source_context_field"
        in global_evidence_request_source_summary_frame.columns
    )
    assert (
        "candidate_pack_eligible"
        in global_evidence_request_source_summary_frame.columns
    )
    assert global_evidence_request_source_priority_queue_frame.empty
    assert (
        "source_context_field"
        in global_evidence_request_source_priority_queue_frame.columns
    )
    assert (
        "candidate_pack_eligible"
        in global_evidence_request_source_priority_queue_frame.columns
    )
    assert sidecar_row_counts["global_evidence_request_priority_queue"] == len(
        global_evidence_request_priority_queue_frame
    )
    assert payload["global_evidence_request_priority_queue_limit"] == 50
    assert payload["global_evidence_request_priority_queue_count"] == 0
    assert payload["global_evidence_request_priority_queue_parquet_row_count"] == 0
    assert global_evidence_request_priority_queue_frame.empty
    assert "evidence_request_trial_id" in global_evidence_request_priority_queue_frame.columns
    assert "candidate_pack_eligible" in global_evidence_request_priority_queue_frame.columns
    assert sidecar_row_counts["global_evidence_request_bucket_queue"] == len(
        global_evidence_request_bucket_queue_frame
    )
    assert payload["global_evidence_request_bucket_queue_count"] == 0
    assert payload["global_evidence_request_bucket_queue_parquet_row_count"] == 0
    assert global_evidence_request_bucket_queue_frame.empty
    assert "bucket_key" in global_evidence_request_bucket_queue_frame.columns
    assert "candidate_pack_eligible" in global_evidence_request_bucket_queue_frame.columns
    assert sidecar_row_counts[
        "global_evidence_request_bucket_representatives"
    ] == len(global_evidence_request_bucket_representatives_frame)
    assert (
        payload["global_evidence_request_bucket_representative_parquet_row_count"]
        == 0
    )
    assert global_evidence_request_bucket_representatives_frame.empty
    assert "bucket_key" in global_evidence_request_bucket_representatives_frame.columns
    assert (
        "evidence_request_trial_id"
        in global_evidence_request_bucket_representatives_frame.columns
    )
    assert (
        "candidate_pack_eligible"
        in global_evidence_request_bucket_representatives_frame.columns
    )
    assert sidecar_row_counts["global_bucket_top_buckets"] == len(
        global_bucket_top_bucket_frame
    )
    assert payload["global_bucket_top_bucket_parquet_row_count"] == 0
    assert global_bucket_top_bucket_frame.empty
    assert "bucket_key" in global_bucket_top_bucket_frame.columns
    assert "candidate_pack_eligible" in global_bucket_top_bucket_frame.columns
    assert sidecar_row_counts["iteration_venue_expansion_gap_worklist"] == len(
        iteration_venue_gap_worklist_frame
    )
    assert payload["iteration_venue_expansion_gap_worklist_parquet_row_count"] == 0
    assert iteration_venue_gap_worklist_frame.empty
    assert "target_venue" in iteration_venue_gap_worklist_frame.columns
    assert "candidate_pack_eligible" in iteration_venue_gap_worklist_frame.columns
    assert sidecar_row_counts["iteration_agent_action_plan"] == 0
    assert sidecar_row_counts["iteration_agent_action_plan_bucket_queue"] == 0
    assert sidecar_row_counts["iteration_agent_action_plan_bucket_representatives"] == 0
    assert sidecar_row_counts["strict_validation_bundle_queue"] == len(
        strict_bundle_queue_frame
    )
    assert sidecar_row_counts["strict_validation_descriptors"] == len(
        strict_descriptor_frame
    )
    assert sidecar_row_counts["strict_validation_descriptor_queue"] == len(
        strict_descriptor_queue_frame
    )
    assert payload["strict_validation_descriptor_queue_limit"] == 50
    assert payload["strict_validation_descriptor_queue_count"] == min(
        50,
        len(strict_descriptor_frame),
    )
    assert payload["strict_validation_descriptor_queue_parquet_row_count"] == len(
        strict_descriptor_queue_frame
    )
    assert Path(str(payload["strict_validation_descriptor_queue_parquet_path"])).exists()
    assert len(payload["strict_validation_descriptor_queue"]) == len(
        strict_descriptor_queue_frame
    )
    assert list(strict_descriptor_queue_frame["queue_rank"]) == list(
        range(1, len(strict_descriptor_queue_frame) + 1)
    )
    assert [
        item["descriptor_id"] for item in payload["strict_validation_descriptor_queue"]
    ] == list(strict_descriptor_queue_frame["descriptor_id"])
    assert set(strict_descriptor_queue_frame["descriptor_id"]).issubset(
        set(strict_descriptor_frame["descriptor_id"])
    )
    assert set(strict_descriptor_queue_frame["descriptor_status"]) == {
        "descriptor_ready"
    }
    assert set(strict_descriptor_queue_frame["descriptor_only"]) == {True}
    assert set(strict_descriptor_queue_frame["strict_validation_executed"]) == {False}
    assert set(strict_descriptor_queue_frame["candidate_pack_written"]) == {False}
    assert set(strict_descriptor_queue_frame["strict_validation_authorized"]) == {False}
    assert set(strict_descriptor_queue_frame["candidate_pack_write_authorized"]) == {
        False
    }
    assert set(strict_descriptor_queue_frame["candidate_pack_eligible"]) == {False}
    assert [
        float(value) for value in strict_descriptor_queue_frame["source_metric_score"]
    ] == sorted(
        [float(value) for value in strict_descriptor_queue_frame["source_metric_score"]],
        reverse=True,
    )
    assert payload["strict_validation_descriptor_bucket_queue_limit"] == 50
    assert payload["strict_validation_descriptor_bucket_representative_limit"] == 5
    assert payload["strict_validation_descriptor_bucket_queue_count"] == len(
        strict_descriptor_bucket_frame
    )
    assert payload["strict_validation_descriptor_bucket_queue_parquet_row_count"] == len(
        strict_descriptor_bucket_frame
    )
    assert Path(str(payload["strict_validation_descriptor_bucket_queue_parquet_path"])).exists()
    assert Path(
        str(payload["strict_validation_descriptor_bucket_representatives_parquet_path"])
    ).exists()
    assert payload[
        "strict_validation_descriptor_bucket_representative_parquet_row_count"
    ] == int(strict_descriptor_bucket_frame["representative_count"].sum())
    assert len(strict_descriptor_bucket_representatives_frame) == payload[
        "strict_validation_descriptor_bucket_representative_parquet_row_count"
    ]
    assert sidecar_row_counts["strict_validation_descriptor_bucket_queue"] == len(
        strict_descriptor_bucket_frame
    )
    assert sidecar_row_counts[
        "strict_validation_descriptor_bucket_representatives"
    ] == len(strict_descriptor_bucket_representatives_frame)
    assert sidecar_row_counts["replay_batch_plan_bucket_queue"] == 0
    assert sidecar_row_counts["replay_batch_plan_bucket_representatives"] == 0
    assert set(strict_descriptor_bucket_frame["bucket_type"]) == {
        "venue_symbol",
        "venue_symbol_requested_validation",
    }
    venue_symbol_rows = strict_descriptor_bucket_frame[
        strict_descriptor_bucket_frame["bucket_type"] == "venue_symbol"
    ]
    validation_rows = strict_descriptor_bucket_frame[
        strict_descriptor_bucket_frame["bucket_type"] == "venue_symbol_requested_validation"
    ]
    assert int(venue_symbol_rows["descriptor_count"].sum()) == len(strict_descriptor_frame)
    assert int(validation_rows["descriptor_count"].sum()) == len(strict_descriptor_frame)
    assert set(strict_descriptor_bucket_frame["descriptor_only"]) == {True}
    assert set(strict_descriptor_bucket_frame["strict_validation_executed"]) == {False}
    assert set(strict_descriptor_bucket_frame["candidate_pack_written"]) == {False}
    assert set(strict_descriptor_bucket_frame["strict_validation_authorized"]) == {False}
    assert set(strict_descriptor_bucket_frame["candidate_pack_write_authorized"]) == {False}
    assert set(strict_descriptor_bucket_frame["candidate_pack_eligible"]) == {False}
    assert all(
        json.loads(value)
        for value in strict_descriptor_bucket_frame["representative_descriptor_ids"]
    )
    assert set(strict_descriptor_bucket_representatives_frame["bucket_type"]) == {
        "venue_symbol",
        "venue_symbol_requested_validation",
    }
    assert set(strict_descriptor_bucket_representatives_frame["descriptor_only"]) == {True}
    assert set(
        strict_descriptor_bucket_representatives_frame["strict_validation_executed"]
    ) == {False}
    assert set(strict_descriptor_bucket_representatives_frame["candidate_pack_written"]) == {
        False
    }
    assert set(
        strict_descriptor_bucket_representatives_frame["strict_validation_authorized"]
    ) == {False}
    assert set(
        strict_descriptor_bucket_representatives_frame[
            "candidate_pack_write_authorized"
        ]
    ) == {False}
    assert set(strict_descriptor_bucket_representatives_frame["candidate_pack_eligible"]) == {
        False
    }
    assert set(strict_descriptor_bucket_representatives_frame["descriptor_id"]).issubset(
        set(strict_descriptor_frame["descriptor_id"])
    )
    assert strict_descriptor_bucket_representatives_frame["source_trial_id"].notna().all()
    run_manifest_row = next(
        row
        for row in payload["artifacts"]
        if row["artifact_kind"] == "run_manifest" and row["run_id"] == "sandbox-artifact-catalog-run"
    )
    suite_manifest_row = next(
        row for row in payload["artifacts"] if row["artifact_kind"] == "suite_manifest" and row["suite_id"] == "catalog-suite"
    )
    run_analysis_rows = [
        row for row in payload["artifacts"] if row["artifact_kind"] == "run_analysis"
    ]
    run_analysis_row = next(
        row
        for row in run_analysis_rows
        if row["run_id"] == "sandbox-artifact-catalog-run"
    )
    assert run_manifest_row["integrity_verification_status"] == "passed"
    assert run_manifest_row["integrity_checked_artifact_count"] == 4
    assert run_manifest_row["integrity_verified_artifact_count"] == 4
    assert run_manifest_row["integrity_failed_artifact_count"] == 0
    assert suite_manifest_row["integrity_verification_status"] == "passed"
    assert suite_manifest_row["integrity_checked_artifact_count"] == 4
    assert suite_manifest_row["integrity_verified_artifact_count"] == 4
    assert suite_manifest_row["integrity_failed_artifact_count"] == 0
    assert run_analysis_row["integrity_verification_status"] == "not_applicable"
    assert run_analysis_row["analysis_bucket_rollup_count"] == len(
        analysis_bucket_rollup_frame[
            analysis_bucket_rollup_frame["source_run_id"] == "sandbox-artifact-catalog-run"
        ]
    )
    assert sum(row["analysis_bucket_rollup_count"] for row in run_analysis_rows) == len(
        analysis_bucket_rollup_frame
    )
    assert payload["analysis_bucket_rollup_parquet_row_count"] == len(
        analysis_bucket_rollup_frame
    )
    assert set(analysis_bucket_rollup_frame["rollup_type"]) == {
        "exit_profile",
        "exit_variant",
        "family",
        "filter_variant",
        "venue",
        "venue_family",
    }
    assert "sandbox-artifact-catalog-run" in set(
        analysis_bucket_rollup_frame["source_run_id"]
    )
    assert analysis_bucket_rollup_frame["source_run_id"].notna().all()
    assert set(analysis_bucket_rollup_frame["descriptor_only"]) == {True}
    assert set(analysis_bucket_rollup_frame["strict_validation_executed"]) == {False}
    assert set(analysis_bucket_rollup_frame["candidate_pack_written"]) == {False}
    assert set(analysis_bucket_rollup_frame["replay_command_execution_authorized"]) == {
        False
    }
    assert set(analysis_bucket_rollup_frame["strict_validation_authorized"]) == {False}
    assert set(analysis_bucket_rollup_frame["candidate_pack_write_authorized"]) == {
        False
    }
    assert set(analysis_bucket_rollup_frame["candidate_pack_eligible"]) == {False}
    assert analysis_bucket_rollup_frame["best_trial_id"].notna().all()
    assert set(frame["candidate_pack_eligible"]) == {False}


def test_sandbox_artifact_catalog_surfaces_failed_run_integrity(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-catalog-tamper-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx")],
        output_root=tmp_path / "runs",
    )
    original_text = run.artifacts.evidence_requests_json_path.read_text(encoding="utf-8")
    run.artifacts.evidence_requests_json_path.write_text(f"{original_text}\n", encoding="utf-8")

    payload = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")
    run_manifest_row = next(row for row in payload["artifacts"] if row["run_id"] == "sandbox-catalog-tamper-run")
    sidecar_index_frame = pd.read_parquet(
        Path(str(payload["catalog_sidecar_index_parquet_path"]))
    )
    analysis_bucket_rollup_frame = pd.read_parquet(
        Path(str(payload["analysis_bucket_rollups_parquet_path"]))
    )
    global_top_hypothesis_frame = pd.read_parquet(
        Path(str(payload["global_top_hypotheses_parquet_path"]))
    )
    global_evidence_request_frame = pd.read_parquet(
        Path(str(payload["global_evidence_requests_parquet_path"]))
    )
    global_evidence_request_source_summary_frame = pd.read_parquet(
        Path(str(payload["global_evidence_request_source_summary_parquet_path"]))
    )
    global_evidence_request_source_priority_queue_frame = pd.read_parquet(
        Path(
            str(
                payload[
                    "global_evidence_request_source_priority_queue_parquet_path"
                ]
            )
        )
    )
    global_evidence_request_priority_queue_frame = pd.read_parquet(
        Path(str(payload["global_evidence_request_priority_queue_parquet_path"]))
    )
    global_evidence_request_bucket_queue_frame = pd.read_parquet(
        Path(str(payload["global_evidence_request_bucket_queue_parquet_path"]))
    )
    global_evidence_request_bucket_representatives_frame = pd.read_parquet(
        Path(
            str(
                payload[
                    "global_evidence_request_bucket_representatives_parquet_path"
                ]
            )
        )
    )
    global_bucket_top_bucket_frame = pd.read_parquet(
        Path(str(payload["global_bucket_top_buckets_parquet_path"]))
    )
    iteration_venue_gap_worklist_frame = pd.read_parquet(
        Path(str(payload["iteration_venue_expansion_gap_worklist_parquet_path"]))
    )
    strict_bundle_queue_frame = pd.read_parquet(
        Path(str(payload["strict_validation_bundle_queue_parquet_path"]))
    )
    strict_descriptor_frame = pd.read_parquet(
        Path(str(payload["strict_validation_descriptor_parquet_path"]))
    )
    strict_descriptor_queue_frame = pd.read_parquet(
        Path(str(payload["strict_validation_descriptor_queue_parquet_path"]))
    )
    strict_descriptor_bucket_frame = pd.read_parquet(
        Path(str(payload["strict_validation_descriptor_bucket_queue_parquet_path"]))
    )
    strict_descriptor_bucket_representatives_frame = pd.read_parquet(
        Path(
            str(
                payload[
                    "strict_validation_descriptor_bucket_representatives_parquet_path"
                ]
            )
        )
    )

    assert run_manifest_row["artifact_kind"] == "run_manifest"
    assert run_manifest_row["integrity_verification_status"] == "failed"
    assert run_manifest_row["integrity_checked_artifact_count"] == 4
    assert run_manifest_row["integrity_verified_artifact_count"] == 3
    assert run_manifest_row["integrity_failed_artifact_count"] == 1
    assert run_manifest_row["integrity_mismatched_artifact_count"] == 1
    assert run_manifest_row["integrity_missing_artifact_count"] == 0
    assert run_manifest_row["integrity_failure_artifact_keys"] == ["evidence_requests_json"]
    assert "sha256_mismatch:evidence_requests_json" in run_manifest_row["integrity_failure_reasons"]
    assert payload["strict_validation_bundle_queue_count"] == 0
    assert payload["strict_validation_bundle_queue_parquet_row_count"] == 0
    assert payload["analysis_bucket_rollup_parquet_row_count"] == 0
    assert payload["global_top_hypothesis_parquet_row_count"] == 0
    assert payload["global_evidence_request_parquet_row_count"] == 0
    assert payload["global_evidence_request_source_summary_parquet_row_count"] == 0
    assert (
        payload["global_evidence_request_source_priority_queue_parquet_row_count"]
        == 0
    )
    assert payload["global_evidence_request_count"] == 0
    assert payload["global_evidence_request_unique_trial_count"] == 0
    assert payload["global_evidence_request_hypothesis_count"] == 0
    assert payload["global_evidence_request_requested_validation_counts"] == {}
    assert payload["global_evidence_request_leaderboard_decision_counts"] == {}
    assert payload["global_evidence_request_family_counts"] == {}
    assert payload["global_evidence_request_tested_venue_counts"] == {}
    assert payload["global_evidence_request_tested_symbol_counts"] == {}
    assert payload["global_evidence_request_summary"]["evidence_request_count"] == 0
    assert payload["global_evidence_request_summary"]["priority_queue_count"] == 0
    assert payload["global_evidence_request_summary"]["bucket_queue_count"] == 0
    assert (
        payload["global_evidence_request_summary"]["bucket_representative_count"]
        == 0
    )
    assert payload["global_evidence_request_bucket_queue_count"] == 0
    assert payload["global_evidence_request_source_priority_queue_count"] == 0
    assert payload["global_evidence_request_priority_queue_count"] == 0
    assert payload["global_evidence_request_source_priority_queue_parquet_row_count"] == 0
    assert payload["global_evidence_request_priority_queue_parquet_row_count"] == 0
    assert payload["global_evidence_request_bucket_queue_parquet_row_count"] == 0
    assert (
        payload["global_evidence_request_bucket_representative_parquet_row_count"]
        == 0
    )
    assert payload["global_bucket_top_bucket_parquet_row_count"] == 0
    assert payload["catalog_sidecar_index_row_count"] == 21
    assert len(sidecar_index_frame) == 21
    assert set(sidecar_index_frame["parquet_written"]) == {True}
    assert set(sidecar_index_frame["candidate_pack_eligible"]) == {False}
    for row in sidecar_index_frame.to_dict("records"):
        sidecar_path = Path(str(row["sidecar_path"]))
        assert bool(row["sidecar_exists"]) is True
        assert int(row["sidecar_size_bytes"]) == sidecar_path.stat().st_size
        assert row["sidecar_sha256"] == _sha256(sidecar_path)
    empty_sidecars = {
        str(row["sidecar_name"]): bool(row["empty"])
        for row in sidecar_index_frame.to_dict("records")
    }
    sidecar_row_counts = {
        str(row["sidecar_name"]): int(row["row_count"])
        for row in sidecar_index_frame.to_dict("records")
    }
    assert empty_sidecars["artifact_catalog"] is False
    assert sidecar_row_counts["artifact_catalog"] == len(payload["artifacts"])
    assert sidecar_row_counts["analysis_bucket_rollups"] == 0
    assert sidecar_row_counts["global_top_hypotheses"] == 0
    assert sidecar_row_counts["global_evidence_requests"] == 0
    assert sidecar_row_counts["global_evidence_request_source_summary"] == 0
    assert sidecar_row_counts["global_evidence_request_source_priority_queue"] == 0
    assert sidecar_row_counts["global_evidence_request_priority_queue"] == 0
    assert sidecar_row_counts["global_evidence_request_bucket_queue"] == 0
    assert sidecar_row_counts["global_evidence_request_bucket_representatives"] == 0
    assert global_evidence_request_source_summary_frame.empty
    assert global_evidence_request_source_priority_queue_frame.empty
    assert (
        "source_context_field"
        in global_evidence_request_source_summary_frame.columns
    )
    assert (
        "source_context_field"
        in global_evidence_request_source_priority_queue_frame.columns
    )
    assert sidecar_row_counts["global_bucket_top_buckets"] == 0
    assert sidecar_row_counts["iteration_venue_expansion_gap_worklist"] == 0
    assert sidecar_row_counts["iteration_agent_action_plan"] == 0
    assert sidecar_row_counts["iteration_agent_action_plan_bucket_queue"] == 0
    assert sidecar_row_counts["iteration_agent_action_plan_bucket_representatives"] == 0
    assert sidecar_row_counts["strict_validation_bundle_queue"] == 0
    assert sidecar_row_counts["strict_validation_descriptors"] == 0
    assert sidecar_row_counts["strict_validation_descriptor_queue"] == 0
    assert sidecar_row_counts["strict_validation_descriptor_bucket_queue"] == 0
    assert sidecar_row_counts["strict_validation_descriptor_bucket_representatives"] == 0
    assert empty_sidecars["analysis_bucket_rollups"] is True
    assert empty_sidecars["global_top_hypotheses"] is True
    assert empty_sidecars["global_evidence_requests"] is True
    assert empty_sidecars["global_evidence_request_priority_queue"] is True
    assert empty_sidecars["global_evidence_request_bucket_queue"] is True
    assert empty_sidecars["global_evidence_request_bucket_representatives"] is True
    assert empty_sidecars["global_bucket_top_buckets"] is True
    assert empty_sidecars["iteration_venue_expansion_gap_worklist"] is True
    assert empty_sidecars["strict_validation_bundle_queue"] is True
    assert empty_sidecars["strict_validation_descriptors"] is True
    assert empty_sidecars["strict_validation_descriptor_queue"] is True
    assert analysis_bucket_rollup_frame.empty
    assert "rollup_type" in analysis_bucket_rollup_frame.columns
    assert "candidate_pack_eligible" in analysis_bucket_rollup_frame.columns
    assert global_top_hypothesis_frame.empty
    assert "hypothesis_id" in global_top_hypothesis_frame.columns
    assert "evidence_request_source_contexts" in global_top_hypothesis_frame.columns
    assert "candidate_pack_eligible" in global_top_hypothesis_frame.columns
    assert global_evidence_request_frame.empty
    assert "evidence_request_trial_id" in global_evidence_request_frame.columns
    assert "source_context_available" in global_evidence_request_frame.columns
    assert "candidate_pack_eligible" in global_evidence_request_frame.columns
    assert global_evidence_request_priority_queue_frame.empty
    assert "evidence_request_trial_id" in global_evidence_request_priority_queue_frame.columns
    assert "source_context_available" in global_evidence_request_priority_queue_frame.columns
    assert "candidate_pack_eligible" in global_evidence_request_priority_queue_frame.columns
    assert global_evidence_request_bucket_queue_frame.empty
    assert "bucket_key" in global_evidence_request_bucket_queue_frame.columns
    assert "source_context_available" in global_evidence_request_bucket_queue_frame.columns
    assert "source_routing_mode" in global_evidence_request_bucket_queue_frame.columns
    assert "candidate_pack_eligible" in global_evidence_request_bucket_queue_frame.columns
    assert global_evidence_request_bucket_representatives_frame.empty
    assert "bucket_key" in global_evidence_request_bucket_representatives_frame.columns
    assert (
        "bucket_source_routing_mode"
        in global_evidence_request_bucket_representatives_frame.columns
    )
    assert (
        "source_context_available"
        in global_evidence_request_bucket_representatives_frame.columns
    )
    assert (
        "evidence_request_trial_id"
        in global_evidence_request_bucket_representatives_frame.columns
    )
    assert (
        "candidate_pack_eligible"
        in global_evidence_request_bucket_representatives_frame.columns
    )
    assert global_bucket_top_bucket_frame.empty
    assert "bucket_key" in global_bucket_top_bucket_frame.columns
    assert "candidate_pack_eligible" in global_bucket_top_bucket_frame.columns
    assert iteration_venue_gap_worklist_frame.empty
    assert "target_venue" in iteration_venue_gap_worklist_frame.columns
    assert "candidate_pack_eligible" in iteration_venue_gap_worklist_frame.columns
    assert strict_bundle_queue_frame.empty
    assert "strict_validation_bundle_status" in strict_bundle_queue_frame.columns
    assert "candidate_pack_eligible" in strict_bundle_queue_frame.columns
    assert payload["strict_validation_descriptor_parquet_row_count"] == 0
    assert payload["strict_validation_descriptor_summary"] == {
        "descriptor_count": 0,
        "requested_validation_counts": {},
        "source_scope_counts": {},
        "status_counts": {},
        "symbol_counts": {},
        "venue_counts": {},
    }
    assert strict_descriptor_frame.empty
    assert "descriptor_id" in strict_descriptor_frame.columns
    assert "candidate_pack_eligible" in strict_descriptor_frame.columns
    assert payload["strict_validation_descriptor_queue_count"] == 0
    assert payload["strict_validation_descriptor_queue_parquet_row_count"] == 0
    assert strict_descriptor_queue_frame.empty
    assert "descriptor_id" in strict_descriptor_queue_frame.columns
    assert "candidate_pack_eligible" in strict_descriptor_queue_frame.columns
    assert payload["strict_validation_descriptor_bucket_queue_count"] == 0
    assert payload["strict_validation_descriptor_bucket_queue_parquet_row_count"] == 0
    assert payload[
        "strict_validation_descriptor_bucket_representative_parquet_row_count"
    ] == 0
    assert strict_descriptor_bucket_frame.empty
    assert strict_descriptor_bucket_representatives_frame.empty
    assert "bucket_type" in strict_descriptor_bucket_frame.columns
    assert "candidate_pack_eligible" in strict_descriptor_bucket_frame.columns
    assert "descriptor_id" in strict_descriptor_bucket_representatives_frame.columns
    assert (
        "candidate_pack_eligible"
        in strict_descriptor_bucket_representatives_frame.columns
    )
    assert not (run.artifacts.run_dir / "artifact_integrity_report.json").exists()


def test_sandbox_global_leaderboard_ranks_hypotheses_across_runs(tmp_path: Path) -> None:
    run_sandbox_sweep(
        spec=_spec("sandbox-global-leaderboard-run-1"),
        market_frame=_market_frame(),
        strategies=[_strategy(), _short_strategy()],
        venues=[_venue("okx")],
        output_root=tmp_path / "runs",
    )
    run_sandbox_sweep(
        spec=_spec("sandbox-global-leaderboard-run-2"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("bybit")],
        output_root=tmp_path / "runs",
    )

    payload = build_sandbox_global_leaderboard(tmp_path, output_dir=tmp_path / "leaderboard", top_n=20)
    frame = pd.read_parquet(Path(str(payload["leaderboard_parquet_path"])))
    bucket_frame = pd.read_parquet(Path(str(payload["bucket_leaderboard_parquet_path"])))
    rows = {row["hypothesis_id"]: row for row in payload["top_hypotheses"]}
    bucket_rows = {row["bucket_key"]: row for row in payload["top_buckets"]}
    expected_evidence_request_trial_ids = [
        str(trial_id)
        for row in payload["top_hypotheses"]
        for trial_id in row["evidence_request_trial_ids"]
    ]
    expected_requesting_hypotheses = [
        row for row in payload["top_hypotheses"] if row["evidence_request_trial_ids"]
    ]
    expected_request_count = len(expected_evidence_request_trial_ids)
    expected_request_contexts = [
        context
        for row in expected_requesting_hypotheses
        for context in row["evidence_request_source_contexts"]
    ]

    def count_context_values(values):
        counts: dict[str, int] = {}
        for value in values:
            if value is None or str(value) == "":
                continue
            value_text = str(value)
            counts[value_text] = counts.get(value_text, 0) + 1
        return counts

    expected_source_venue_counts = count_context_values(
        context.get("venue") for context in expected_request_contexts
    )
    expected_source_symbol_counts = count_context_values(
        context.get("symbol") for context in expected_request_contexts
    )
    expected_source_data_family_counts = count_context_values(
        context.get("data_family") for context in expected_request_contexts
    )
    expected_source_interval_counts = count_context_values(
        (context.get("source_market_source") or {}).get("interval")
        for context in expected_request_contexts
    )
    expected_source_routing_mode_counts = count_context_values(
        context.get("source_routing_mode") for context in expected_request_contexts
    )
    expected_source_venue_descriptor_counts = count_context_values(
        context.get("source_venue_descriptor_id")
        for context in expected_request_contexts
    )
    expected_source_data_path_counts = count_context_values(
        context.get("source_data_path") for context in expected_request_contexts
    )
    expected_source_summary_counts = {
        "source_venue": expected_source_venue_counts,
        "source_symbol": expected_source_symbol_counts,
        "source_data_family": expected_source_data_family_counts,
        "source_interval": expected_source_interval_counts,
        "source_routing_mode": expected_source_routing_mode_counts,
        "source_venue_descriptor_id": expected_source_venue_descriptor_counts,
        "source_data_path": expected_source_data_path_counts,
    }
    expected_nonempty_source_summary_counts = {
        key: counts
        for key, counts in expected_source_summary_counts.items()
        if counts
    }
    source_summary_context_extractors = {
        "source_venue": lambda context: context.get("venue"),
        "source_symbol": lambda context: context.get("symbol"),
        "source_data_family": lambda context: context.get("data_family"),
        "source_interval": lambda context: (
            context.get("source_market_source") or {}
        ).get("interval"),
        "source_routing_mode": lambda context: context.get("source_routing_mode"),
        "source_venue_descriptor_id": lambda context: context.get(
            "source_venue_descriptor_id"
        ),
        "source_data_path": lambda context: context.get("source_data_path"),
    }
    expected_source_summary_windows: dict[tuple[str, str], dict[str, object]] = {}
    for context in expected_request_contexts:
        for source_context_field, extractor in source_summary_context_extractors.items():
            value = extractor(context)
            if value is None or str(value) == "":
                continue
            key = (source_context_field, str(value))
            windows = expected_source_summary_windows.setdefault(
                key,
                {
                    "trial_ids": set(),
                    "market_starts": [],
                    "market_ends": [],
                },
            )
            trial_id = context.get("source_trial_id")
            if trial_id is not None and str(trial_id) != "":
                windows["trial_ids"].add(str(trial_id))
            market_start = context.get("source_market_start")
            if market_start is not None and str(market_start) != "":
                windows["market_starts"].append(str(market_start))
            market_end = context.get("source_market_end")
            if market_end is not None and str(market_end) != "":
                windows["market_ends"].append(str(market_end))
    expected_request_requested_validation_counts = {
        "strict_validation": expected_request_count
    }
    expected_request_decision_counts: dict[str, int] = {}
    expected_request_family_counts: dict[str, int] = {}
    expected_request_venue_counts: dict[str, int] = {}
    expected_request_symbol_counts: dict[str, int] = {}
    for row in expected_requesting_hypotheses:
        amount = len(row["evidence_request_trial_ids"])
        expected_request_decision_counts[row["leaderboard_decision"]] = (
            expected_request_decision_counts.get(row["leaderboard_decision"], 0)
            + amount
        )
        expected_request_family_counts[row["family"]] = (
            expected_request_family_counts.get(row["family"], 0) + amount
        )
        for venue in row["venues_tested"]:
            expected_request_venue_counts[venue] = (
                expected_request_venue_counts.get(venue, 0) + amount
            )
        for symbol in row["symbols_tested"]:
            expected_request_symbol_counts[symbol] = (
                expected_request_symbol_counts.get(symbol, 0) + amount
            )
    catalog = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["source_run_count"] == 2
    assert payload["hypothesis_count"] == 2
    assert payload["bucket_count"] == len(bucket_frame)
    assert payload["bucket_count"] == 11
    assert len(payload["top_buckets"]) == 11
    assert payload["decision_counts"]["request_strict_validation"] == 1
    assert payload["decision_counts"]["falsified_in_sandbox"] == 1
    assert payload["bucket_decision_counts"]["request_strict_validation"] >= 1
    assert rows["fallback-long"]["leaderboard_rank"] == 1
    assert rows["fallback-long"]["run_count"] == 2
    assert rows["fallback-long"]["leaderboard_decision"] == "request_strict_validation"
    assert set(rows["fallback-long"]["venues_tested"]) == {"bybit", "okx"}
    assert rows["fallback-long"]["evidence_request_source_context_count"] == len(
        rows["fallback-long"]["evidence_request_trial_ids"]
    )
    assert rows["fallback-long"]["evidence_request_source_context_limit"] == 50
    assert (
        rows["fallback-long"]["evidence_request_source_contexts_truncated"]
        is False
    )
    assert [
        context["source_trial_id"]
        for context in rows["fallback-long"]["evidence_request_source_contexts"]
    ] == rows["fallback-long"]["evidence_request_trial_ids"]
    assert {
        context["source_requested_validation"]
        for context in rows["fallback-long"]["evidence_request_source_contexts"]
    } == {"strict_research_cycle_request"}
    assert {
        context["source_routing_mode"]
        for context in rows["fallback-long"]["evidence_request_source_contexts"]
    } == {"shared_market_frame"}
    assert {
        context["venue"]
        for context in rows["fallback-long"]["evidence_request_source_contexts"]
    } == {"bybit", "okx"}
    assert {
        context["source_market_start"]
        for context in rows["fallback-long"]["evidence_request_source_contexts"]
    } == {"2024-01-01T00:00:00+00:00"}
    assert {
        context["strict_validation_authorized"]
        for context in rows["fallback-long"]["evidence_request_source_contexts"]
    } == {False}
    assert rows["fallback-short"]["leaderboard_decision"] == "falsified_in_sandbox"
    assert bucket_rows["venue=bybit"]["bucket_type"] == "venue"
    assert bucket_rows["venue=bybit"]["bucket_values"] == {"venue": "bybit"}
    assert bucket_rows["venue=bybit"]["run_count"] == 1
    assert bucket_rows["venue=bybit"]["best_trial_id"]
    assert bucket_rows["venue=bybit"]["bucket_leaderboard_decision"] == "request_strict_validation"
    assert bucket_rows["venue=okx"]["bucket_type"] == "venue"
    assert bucket_rows["venue=okx"]["run_count"] == 1
    assert "fallback-long" in bucket_rows["venue=okx"]["hypotheses_tested"]
    assert Path(str(payload["leaderboard_json_path"])).exists()
    assert Path(str(payload["leaderboard_parquet_path"])).exists()
    assert Path(str(payload["bucket_leaderboard_parquet_path"])).exists()
    assert set(frame["candidate_pack_eligible"]) == {False}
    assert set(bucket_frame["candidate_pack_eligible"]) == {False}
    assert set(bucket_frame["strict_validation_authorized"]) == {False}
    assert set(bucket_frame["candidate_pack_write_authorized"]) == {False}
    assert list(bucket_frame["bucket_leaderboard_rank"]) == list(
        range(1, len(bucket_frame) + 1)
    )
    assert {"venue", "symbol", "venue_symbol", "venue_family"}.issubset(
        set(bucket_frame["bucket_type"])
    )
    assert catalog["artifact_kind_counts"]["global_leaderboard"] == 1
    global_top_hypothesis_frame = pd.read_parquet(
        Path(str(catalog["global_top_hypotheses_parquet_path"]))
    )
    global_evidence_request_frame = pd.read_parquet(
        Path(str(catalog["global_evidence_requests_parquet_path"]))
    )
    global_evidence_request_source_summary_frame = pd.read_parquet(
        Path(str(catalog["global_evidence_request_source_summary_parquet_path"]))
    )
    global_evidence_request_source_priority_queue_frame = pd.read_parquet(
        Path(
            str(
                catalog[
                    "global_evidence_request_source_priority_queue_parquet_path"
                ]
            )
        )
    )
    global_evidence_request_priority_queue_frame = pd.read_parquet(
        Path(str(catalog["global_evidence_request_priority_queue_parquet_path"]))
    )
    global_evidence_request_bucket_queue_frame = pd.read_parquet(
        Path(str(catalog["global_evidence_request_bucket_queue_parquet_path"]))
    )
    global_evidence_request_bucket_representatives_frame = pd.read_parquet(
        Path(
            str(
                catalog[
                    "global_evidence_request_bucket_representatives_parquet_path"
                ]
            )
        )
    )
    global_bucket_top_bucket_frame = pd.read_parquet(
        Path(str(catalog["global_bucket_top_buckets_parquet_path"]))
    )
    sidecar_index_frame = pd.read_parquet(
        Path(str(catalog["catalog_sidecar_index_parquet_path"]))
    )
    sidecar_row_counts = {
        str(row["sidecar_name"]): int(row["row_count"])
        for row in sidecar_index_frame.to_dict("records")
    }
    catalog_row = next(
        row
        for row in catalog["artifacts"]
        if row["artifact_kind"] == "global_leaderboard"
    )
    catalog_frame = pd.read_parquet(Path(str(catalog["catalog_parquet_path"])))
    catalog_frame_row = catalog_frame[
        catalog_frame["artifact_kind"] == "global_leaderboard"
    ].iloc[0]
    assert catalog_row["global_bucket_count"] == payload["bucket_count"]
    assert catalog_row["global_top_bucket_count"] == len(payload["top_buckets"])
    assert (
        catalog_row["global_bucket_leaderboard_parquet_path"]
        == payload["bucket_leaderboard_parquet_path"]
    )
    assert (
        catalog_row["global_bucket_decision_counts"]
        == payload["bucket_decision_counts"]
    )
    assert set(catalog_row["global_top_bucket_types"]) == set(
        bucket_frame["bucket_type"]
    )
    assert catalog_row["global_evidence_request_count"] == expected_request_count
    assert (
        catalog_row["global_evidence_request_unique_trial_count"]
        == expected_request_count
    )
    assert catalog_row["global_evidence_request_hypothesis_count"] == len(
        expected_requesting_hypotheses
    )
    assert catalog_row["global_evidence_request_unique_hypothesis_count"] == len(
        {row["hypothesis_id"] for row in expected_requesting_hypotheses}
    )
    assert (
        catalog_row["global_evidence_request_requested_validation_counts"]
        == expected_request_requested_validation_counts
    )
    assert (
        catalog_row["global_evidence_request_leaderboard_decision_counts"]
        == expected_request_decision_counts
    )
    assert (
        catalog_row["global_evidence_request_family_counts"]
        == expected_request_family_counts
    )
    assert (
        catalog_row["global_evidence_request_tested_venue_counts"]
        == expected_request_venue_counts
    )
    assert (
        catalog_row["global_evidence_request_tested_symbol_counts"]
        == expected_request_symbol_counts
    )
    assert (
        catalog_row["global_evidence_request_source_context_count"]
        == expected_request_count
    )
    assert (
        catalog_row[
            "global_evidence_request_source_context_truncated_hypothesis_count"
        ]
        == 0
    )
    assert int(catalog_frame_row["global_bucket_count"]) == payload["bucket_count"]
    assert (
        catalog_frame_row["global_bucket_leaderboard_parquet_path"]
        == payload["bucket_leaderboard_parquet_path"]
    )
    assert json.loads(catalog_frame_row["global_bucket_decision_counts"]) == payload[
        "bucket_decision_counts"
    ]
    assert (
        int(catalog_frame_row["global_evidence_request_count"])
        == expected_request_count
    )
    assert (
        int(catalog_frame_row["global_evidence_request_unique_trial_count"])
        == expected_request_count
    )
    assert int(catalog_frame_row["global_evidence_request_hypothesis_count"]) == len(
        expected_requesting_hypotheses
    )
    assert json.loads(
        catalog_frame_row["global_evidence_request_requested_validation_counts"]
    ) == expected_request_requested_validation_counts
    assert json.loads(
        catalog_frame_row["global_evidence_request_leaderboard_decision_counts"]
    ) == expected_request_decision_counts
    assert json.loads(
        catalog_frame_row["global_evidence_request_family_counts"]
    ) == expected_request_family_counts
    assert json.loads(
        catalog_frame_row["global_evidence_request_tested_venue_counts"]
    ) == expected_request_venue_counts
    assert json.loads(
        catalog_frame_row["global_evidence_request_tested_symbol_counts"]
    ) == expected_request_symbol_counts
    assert (
        int(catalog_frame_row["global_evidence_request_source_context_count"])
        == expected_request_count
    )
    assert (
        int(
            catalog_frame_row[
                "global_evidence_request_source_context_truncated_hypothesis_count"
            ]
        )
        == 0
    )
    assert Path(str(catalog["global_top_hypotheses_parquet_path"])).exists()
    assert catalog["global_top_hypothesis_parquet_row_count"] == len(
        payload["top_hypotheses"]
    )
    assert len(global_top_hypothesis_frame) == len(payload["top_hypotheses"])
    assert sidecar_row_counts["global_top_hypotheses"] == len(
        global_top_hypothesis_frame
    )
    assert set(global_top_hypothesis_frame["candidate_pack_eligible"]) == {False}
    assert set(global_top_hypothesis_frame["strict_validation_authorized"]) == {
        False
    }
    assert set(
        global_top_hypothesis_frame["candidate_pack_write_authorized"]
    ) == {False}
    assert set(global_top_hypothesis_frame["source_leaderboard_parquet_path"]) == {
        payload["leaderboard_parquet_path"]
    }
    assert set(global_top_hypothesis_frame["source_artifact_path"]) == {
        payload["leaderboard_json_path"]
    }
    assert list(global_top_hypothesis_frame["top_hypothesis_row_rank"]) == list(
        range(1, len(global_top_hypothesis_frame) + 1)
    )
    assert list(global_top_hypothesis_frame["leaderboard_rank"]) == [
        row["leaderboard_rank"] for row in payload["top_hypotheses"]
    ]
    fallback_long_row = global_top_hypothesis_frame[
        global_top_hypothesis_frame["hypothesis_id"] == "fallback-long"
    ].iloc[0]
    assert fallback_long_row["leaderboard_decision"] == "request_strict_validation"
    assert int(fallback_long_row["run_count"]) == 2
    assert set(json.loads(fallback_long_row["venues_tested"])) == {"bybit", "okx"}
    assert int(fallback_long_row["evidence_request_source_context_count"]) == len(
        rows["fallback-long"]["evidence_request_trial_ids"]
    )
    assert int(fallback_long_row["evidence_request_source_context_limit"]) == 50
    assert bool(fallback_long_row["evidence_request_source_contexts_truncated"]) is False
    assert [
        context["source_trial_id"]
        for context in json.loads(
            fallback_long_row["evidence_request_source_contexts"]
        )
    ] == rows["fallback-long"]["evidence_request_trial_ids"]
    assert json.loads(fallback_long_row["source_decision_counts"]) == payload[
        "decision_counts"
    ]
    assert expected_evidence_request_trial_ids
    assert Path(str(catalog["global_evidence_requests_parquet_path"])).exists()
    assert catalog["global_evidence_request_parquet_row_count"] == len(
        expected_evidence_request_trial_ids
    )
    assert catalog["global_evidence_request_count"] == expected_request_count
    assert (
        catalog["global_evidence_request_unique_trial_count"]
        == expected_request_count
    )
    assert catalog["global_evidence_request_hypothesis_count"] == len(
        {row["hypothesis_id"] for row in expected_requesting_hypotheses}
    )
    assert catalog["global_evidence_request_source_leaderboard_count"] == 1
    assert (
        catalog["global_evidence_request_requested_validation_counts"]
        == expected_request_requested_validation_counts
    )
    assert (
        catalog["global_evidence_request_leaderboard_decision_counts"]
        == expected_request_decision_counts
    )
    assert (
        catalog["global_evidence_request_family_counts"]
        == expected_request_family_counts
    )
    assert (
        catalog["global_evidence_request_tested_venue_counts"]
        == expected_request_venue_counts
    )
    assert (
        catalog["global_evidence_request_tested_symbol_counts"]
        == expected_request_symbol_counts
    )
    assert (
        catalog["global_evidence_request_source_context_available_count"]
        == expected_request_count
    )
    assert catalog["global_evidence_request_source_context_missing_count"] == 0
    assert (
        catalog["global_evidence_request_source_venue_counts"]
        == expected_source_venue_counts
    )
    assert (
        catalog["global_evidence_request_source_symbol_counts"]
        == expected_source_symbol_counts
    )
    assert (
        catalog["global_evidence_request_source_data_family_counts"]
        == expected_source_data_family_counts
    )
    assert (
        catalog["global_evidence_request_source_interval_counts"]
        == expected_source_interval_counts
    )
    assert (
        catalog["global_evidence_request_source_routing_mode_counts"]
        == expected_source_routing_mode_counts
    )
    assert (
        catalog["global_evidence_request_source_venue_descriptor_counts"]
        == expected_source_venue_descriptor_counts
    )
    assert (
        catalog["global_evidence_request_source_data_path_counts"]
        == expected_source_data_path_counts
    )
    expected_source_summary_row_count = sum(
        len(counts) for counts in expected_nonempty_source_summary_counts.values()
    )
    assert Path(
        str(catalog["global_evidence_request_source_summary_parquet_path"])
    ).exists()
    assert Path(
        str(catalog["global_evidence_request_source_priority_queue_parquet_path"])
    ).exists()
    assert (
        catalog["global_evidence_request_source_summary_parquet_row_count"]
        == expected_source_summary_row_count
    )
    assert catalog["global_evidence_request_source_priority_queue_limit"] == 50
    assert catalog["global_evidence_request_source_priority_queue_count"] == min(
        50,
        expected_source_summary_row_count,
    )
    assert (
        catalog["global_evidence_request_source_priority_queue_parquet_row_count"]
        == len(global_evidence_request_source_priority_queue_frame)
    )
    assert len(global_evidence_request_frame) == len(
        expected_evidence_request_trial_ids
    )
    assert sidecar_row_counts["global_evidence_requests"] == len(
        global_evidence_request_frame
    )
    assert sidecar_row_counts["global_evidence_request_source_summary"] == len(
        global_evidence_request_source_summary_frame
    )
    assert sidecar_row_counts["global_evidence_request_source_priority_queue"] == len(
        global_evidence_request_source_priority_queue_frame
    )
    assert len(global_evidence_request_source_summary_frame) == (
        expected_source_summary_row_count
    )
    assert len(global_evidence_request_source_priority_queue_frame) == min(
        50,
        expected_source_summary_row_count,
    )
    assert list(
        global_evidence_request_source_summary_frame["summary_row_rank"]
    ) == list(range(1, len(global_evidence_request_source_summary_frame) + 1))
    assert list(
        global_evidence_request_source_priority_queue_frame["queue_rank"]
    ) == list(range(1, len(global_evidence_request_source_priority_queue_frame) + 1))
    assert set(
        global_evidence_request_source_summary_frame["candidate_pack_eligible"]
    ) == {False}
    assert set(
        global_evidence_request_source_priority_queue_frame[
            "candidate_pack_eligible"
        ]
    ) == {False}
    assert set(
        global_evidence_request_source_summary_frame["strict_validation_authorized"]
    ) == {False}
    assert set(
        global_evidence_request_source_priority_queue_frame[
            "strict_validation_authorized"
        ]
    ) == {False}
    assert set(
        global_evidence_request_source_summary_frame[
            "candidate_pack_write_authorized"
        ]
    ) == {False}
    assert set(
        global_evidence_request_source_priority_queue_frame[
            "candidate_pack_write_authorized"
        ]
    ) == {False}

    def source_priority_sort_key(row: dict[str, object]) -> tuple:
        return (
            float(row["best_leaderboard_rank"]),
            -float(row["best_score"]),
            float(row["best_source_metric_rank"]),
            -float(row["best_source_metric_score"]),
            -int(row["unique_evidence_request_trial_count"]),
            -int(row["source_context_count"]),
            str(row["source_context_field"]),
            str(row["source_context_value"]),
            int(row["summary_row_rank"]),
        )

    expected_source_priority_rows = sorted(
        global_evidence_request_source_summary_frame.to_dict("records"),
        key=source_priority_sort_key,
    )[:50]
    assert list(
        global_evidence_request_source_priority_queue_frame[
            "source_summary_row_rank"
        ]
    ) == [int(row["summary_row_rank"]) for row in expected_source_priority_rows]
    assert list(
        global_evidence_request_source_priority_queue_frame["source_context_field"]
    ) == [row["source_context_field"] for row in expected_source_priority_rows]
    assert list(
        global_evidence_request_source_priority_queue_frame["source_context_value"]
    ) == [row["source_context_value"] for row in expected_source_priority_rows]
    assert list(
        global_evidence_request_source_priority_queue_frame[
            "best_evidence_request_trial_id"
        ]
    ) == [
        row["best_evidence_request_trial_id"]
        for row in expected_source_priority_rows
    ]

    def summary_representative_rows(
        source_context_field: str,
        source_context_value: str,
    ) -> list[dict[str, object]]:
        request_rows = []
        for request_row in global_evidence_request_frame.to_dict("records"):
            if not bool(request_row.get("source_context_available", False)):
                continue
            value = request_row.get(source_context_field)
            if value is None or str(value) != source_context_value:
                continue
            request_rows.append(request_row)
        return sorted(
            request_rows,
            key=lambda request_row: (
                int(request_row["leaderboard_rank"]),
                -float(request_row["best_score"]),
                int(request_row["evidence_request_row_rank"]),
                str(request_row.get("source_artifact_path") or ""),
                str(request_row.get("evidence_request_trial_id") or ""),
            ),
        )[:5]

    def ordered_unique_values(rows: list[dict[str, object]], key: str) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()
        for row in rows:
            value = row.get(key)
            if value is None or str(value) == "":
                continue
            value_text = str(value)
            if value_text in seen:
                continue
            seen.add(value_text)
            values.append(value_text)
        return values

    observed_source_summary_counts: dict[str, dict[str, int]] = {}
    for summary_row in global_evidence_request_source_summary_frame.to_dict(
        "records"
    ):
        observed_source_summary_counts.setdefault(
            summary_row["source_context_field"],
            {},
        )[summary_row["source_context_value"]] = int(
            summary_row["source_context_count"]
        )
        summary_key = (
            summary_row["source_context_field"],
            summary_row["source_context_value"],
        )
        expected_windows = expected_source_summary_windows[summary_key]
        assert int(summary_row["unique_evidence_request_trial_count"]) == len(
            expected_windows["trial_ids"]
        )
        assert int(summary_row["source_leaderboard_count"]) == 1
        representative_rows = summary_representative_rows(*summary_key)
        best_row = representative_rows[0]
        assert int(summary_row["best_leaderboard_rank"]) == int(
            best_row["leaderboard_rank"]
        )
        assert float(summary_row["best_score"]) == float(best_row["best_score"])
        assert int(summary_row["best_source_metric_rank"]) == int(
            best_row["source_metric_rank"]
        )
        assert float(summary_row["best_source_metric_score"]) == float(
            best_row["source_metric_score"]
        )
        assert float(summary_row["best_source_metric_net_return_sum"]) == float(
            best_row["source_metric_net_return_sum"]
        )
        assert int(summary_row["best_source_metric_trade_count"]) == int(
            best_row["source_metric_trade_count"]
        )
        assert summary_row["best_evidence_request_trial_id"] == best_row[
            "evidence_request_trial_id"
        ]
        assert summary_row["best_source_trial_id"] == best_row["source_trial_id"]
        assert summary_row["best_hypothesis_id"] == best_row["hypothesis_id"]
        assert summary_row["best_family"] == best_row["family"]
        assert int(summary_row["representative_limit"]) == 5
        assert int(summary_row["representative_count"]) == len(representative_rows)
        assert json.loads(
            summary_row["representative_evidence_request_trial_ids"]
        ) == ordered_unique_values(
            representative_rows,
            "evidence_request_trial_id",
        )
        assert json.loads(summary_row["representative_source_trial_ids"]) == (
            ordered_unique_values(representative_rows, "source_trial_id")
        )
        assert json.loads(summary_row["representative_source_request_ids"]) == (
            ordered_unique_values(representative_rows, "source_request_id")
        )
        assert json.loads(summary_row["representative_source_artifact_paths"]) == (
            ordered_unique_values(representative_rows, "source_artifact_path")
        )
        assert json.loads(
            summary_row["representative_source_leaderboard_json_paths"]
        ) == ordered_unique_values(
            representative_rows,
            "source_leaderboard_json_path",
        )
        market_starts = expected_windows["market_starts"]
        if market_starts:
            assert summary_row["source_market_start_min"] == min(market_starts)
            assert summary_row["source_market_start_max"] == max(market_starts)
            assert str(summary_row["source_market_start_min"]).startswith("2024-")
        market_ends = expected_windows["market_ends"]
        if market_ends:
            assert summary_row["source_market_end_min"] == min(market_ends)
            assert summary_row["source_market_end_max"] == max(market_ends)
        assert int(summary_row["evidence_request_count"]) == expected_request_count
        assert (
            int(summary_row["source_context_available_count"])
            == expected_request_count
        )
        assert int(summary_row["source_context_missing_count"]) == 0
    assert observed_source_summary_counts == expected_nonempty_source_summary_counts
    assert list(global_evidence_request_frame["evidence_request_row_rank"]) == list(
        range(1, len(global_evidence_request_frame) + 1)
    )
    assert list(global_evidence_request_frame["evidence_request_trial_id"]) == (
        expected_evidence_request_trial_ids
    )
    assert list(global_evidence_request_frame["source_trial_id"]) == (
        expected_evidence_request_trial_ids
    )
    assert set(global_evidence_request_frame["requested_validation"]) == {
        "strict_validation"
    }
    assert set(global_evidence_request_frame["source_context_available"]) == {True}
    assert set(global_evidence_request_frame["source_requested_validation"]) == {
        "strict_research_cycle_request"
    }
    assert set(global_evidence_request_frame["source_routing_mode"]) == {
        "shared_market_frame"
    }
    assert set(global_evidence_request_frame["source_market_start"]) == {
        "2024-01-01T00:00:00+00:00"
    }
    assert {
        context["source_trial_id"]
        for context in expected_request_contexts
    } == set(expected_evidence_request_trial_ids)
    assert {
        json.loads(cell)["routing_mode"]
        for cell in global_evidence_request_frame["source_market_source"]
    } == {"shared_market_frame"}
    assert (
        len(set(global_evidence_request_frame["source_request_id"].dropna()))
        == expected_request_count
    )
    assert set(global_evidence_request_frame["descriptor_only"]) == {True}
    assert set(global_evidence_request_frame["strict_validation_executed"]) == {
        False
    }
    assert set(global_evidence_request_frame["strict_validation_authorized"]) == {
        False
    }
    assert set(
        global_evidence_request_frame["candidate_pack_write_authorized"]
    ) == {False}
    assert set(global_evidence_request_frame["source_leaderboard_parquet_path"]) == {
        payload["leaderboard_parquet_path"]
    }
    assert set(global_evidence_request_frame["source_artifact_path"]) == {
        payload["leaderboard_json_path"]
    }
    fallback_request_rows = global_evidence_request_frame[
        global_evidence_request_frame["evidence_request_trial_id"].isin(
            rows["fallback-long"]["evidence_request_trial_ids"]
        )
    ]
    assert len(fallback_request_rows) == len(
        rows["fallback-long"]["evidence_request_trial_ids"]
    )
    assert set(fallback_request_rows["hypothesis_id"]) == {"fallback-long"}
    assert set(fallback_request_rows["leaderboard_decision"]) == {
        "request_strict_validation"
    }
    assert {
        venue
        for cell in fallback_request_rows["venues_tested"]
        for venue in json.loads(cell)
    } == {"bybit", "okx"}
    assert Path(
        str(catalog["global_evidence_request_priority_queue_parquet_path"])
    ).exists()
    assert catalog["global_evidence_request_priority_queue_limit"] == 50
    assert catalog["global_evidence_request_priority_queue_count"] == len(
        global_evidence_request_priority_queue_frame
    )
    assert (
        catalog["global_evidence_request_priority_queue_parquet_row_count"]
        == len(global_evidence_request_priority_queue_frame)
    )
    assert sidecar_row_counts["global_evidence_request_priority_queue"] == len(
        global_evidence_request_priority_queue_frame
    )
    assert len(global_evidence_request_priority_queue_frame) == len(
        expected_evidence_request_trial_ids
    )
    assert list(global_evidence_request_priority_queue_frame["queue_rank"]) == list(
        range(1, len(global_evidence_request_priority_queue_frame) + 1)
    )
    assert list(
        global_evidence_request_priority_queue_frame["evidence_request_trial_id"]
    ) == expected_evidence_request_trial_ids
    assert list(global_evidence_request_priority_queue_frame["source_trial_id"]) == (
        expected_evidence_request_trial_ids
    )
    assert set(
        global_evidence_request_priority_queue_frame["source_evidence_request_row_rank"]
    ) == set(range(1, len(global_evidence_request_frame) + 1))
    assert set(
        global_evidence_request_priority_queue_frame["requested_validation"]
    ) == {"strict_validation"}
    assert set(
        global_evidence_request_priority_queue_frame["source_context_available"]
    ) == {True}
    assert set(
        global_evidence_request_priority_queue_frame["source_requested_validation"]
    ) == {"strict_research_cycle_request"}
    assert set(
        global_evidence_request_priority_queue_frame["source_routing_mode"]
    ) == {"shared_market_frame"}
    assert set(
        global_evidence_request_priority_queue_frame["source_market_start"]
    ) == {"2024-01-01T00:00:00+00:00"}
    assert {
        json.loads(cell)["routing_mode"]
        for cell in global_evidence_request_priority_queue_frame[
            "source_market_source"
        ]
    } == {"shared_market_frame"}
    assert set(
        global_evidence_request_priority_queue_frame["descriptor_only"]
    ) == {True}
    assert set(
        global_evidence_request_priority_queue_frame["strict_validation_executed"]
    ) == {False}
    assert set(
        global_evidence_request_priority_queue_frame["strict_validation_authorized"]
    ) == {False}
    assert set(
        global_evidence_request_priority_queue_frame[
            "candidate_pack_write_authorized"
        ]
    ) == {False}
    assert set(
        global_evidence_request_priority_queue_frame["source_leaderboard_parquet_path"]
    ) == {payload["leaderboard_parquet_path"]}
    assert set(
        global_evidence_request_priority_queue_frame["source_artifact_path"]
    ) == {payload["leaderboard_json_path"]}
    assert Path(
        str(catalog["global_evidence_request_bucket_queue_parquet_path"])
    ).exists()
    assert catalog["global_evidence_request_bucket_queue_limit"] == 75
    assert catalog["global_evidence_request_bucket_queue_count"] == len(
        global_evidence_request_bucket_queue_frame
    )
    assert catalog["global_evidence_request_bucket_queue_parquet_row_count"] == len(
        global_evidence_request_bucket_queue_frame
    )
    assert sidecar_row_counts["global_evidence_request_bucket_queue"] == len(
        global_evidence_request_bucket_queue_frame
    )
    global_evidence_request_summary = catalog["global_evidence_request_summary"]
    assert (
        global_evidence_request_summary["evidence_request_count"]
        == expected_request_count
    )
    assert (
        global_evidence_request_summary["unique_evidence_request_trial_count"]
        == expected_request_count
    )
    assert (
        global_evidence_request_summary["requested_validation_counts"]
        == expected_request_requested_validation_counts
    )
    assert (
        global_evidence_request_summary["leaderboard_decision_counts"]
        == expected_request_decision_counts
    )
    assert (
        global_evidence_request_summary["family_counts"]
        == expected_request_family_counts
    )
    assert (
        global_evidence_request_summary["tested_venue_counts"]
        == expected_request_venue_counts
    )
    assert (
        global_evidence_request_summary["tested_symbol_counts"]
        == expected_request_symbol_counts
    )
    assert (
        global_evidence_request_summary["source_context_available_count"]
        == expected_request_count
    )
    assert global_evidence_request_summary["source_context_missing_count"] == 0
    assert (
        global_evidence_request_summary["source_venue_counts"]
        == expected_source_venue_counts
    )
    assert (
        global_evidence_request_summary["source_symbol_counts"]
        == expected_source_symbol_counts
    )
    assert (
        global_evidence_request_summary["source_data_family_counts"]
        == expected_source_data_family_counts
    )
    assert (
        global_evidence_request_summary["source_interval_counts"]
        == expected_source_interval_counts
    )
    assert (
        global_evidence_request_summary["source_routing_mode_counts"]
        == expected_source_routing_mode_counts
    )
    assert (
        global_evidence_request_summary["source_venue_descriptor_counts"]
        == expected_source_venue_descriptor_counts
    )
    assert (
        global_evidence_request_summary["source_data_path_counts"]
        == expected_source_data_path_counts
    )
    assert (
        global_evidence_request_summary["priority_queue_count"]
        == len(global_evidence_request_priority_queue_frame)
    )
    assert (
        global_evidence_request_summary["bucket_queue_count"]
        == len(global_evidence_request_bucket_queue_frame)
    )
    assert (
        global_evidence_request_summary["bucket_representative_count"]
        == len(global_evidence_request_bucket_representatives_frame)
    )
    assert global_evidence_request_summary["descriptor_only"] is True
    assert global_evidence_request_summary["strict_validation_executed"] is False
    assert global_evidence_request_summary["candidate_pack_written"] is False
    assert (
        global_evidence_request_summary["strict_validation_authorized"]
        is False
    )
    assert (
        global_evidence_request_summary["candidate_pack_write_authorized"]
        is False
    )
    assert not global_evidence_request_bucket_queue_frame.empty
    assert list(global_evidence_request_bucket_queue_frame["queue_rank"]) == list(
        range(1, len(global_evidence_request_bucket_queue_frame) + 1)
    )
    assert set(
        global_evidence_request_bucket_queue_frame["candidate_pack_eligible"]
    ) == {False}
    assert set(
        global_evidence_request_bucket_queue_frame["strict_validation_authorized"]
    ) == {False}
    assert set(
        global_evidence_request_bucket_queue_frame["candidate_pack_write_authorized"]
    ) == {False}
    bucket_rows_by_key = {
        row["bucket_key"]: row
        for row in global_evidence_request_bucket_queue_frame.to_dict("records")
    }
    expected_bucket_keys = {
        "requested_validation=strict_validation",
        "hypothesis_id=fallback-long",
        "family=transparent_motif_fallback",
        "leaderboard_decision=request_strict_validation",
        "tested_venue=bybit",
        "tested_venue=okx",
        "tested_symbol=BTCUSDT",
        "tested_venue=bybit|family=transparent_motif_fallback",
        "tested_venue=okx|family=transparent_motif_fallback",
        "tested_venue=bybit|tested_symbol=BTCUSDT",
        "tested_venue=okx|tested_symbol=BTCUSDT",
        "source_venue=bybit",
        "source_venue=okx",
        "source_symbol=BTCUSDT",
        "source_venue=bybit|family=transparent_motif_fallback",
        "source_venue=okx|family=transparent_motif_fallback",
        "source_venue=bybit|source_symbol=BTCUSDT",
        "source_venue=okx|source_symbol=BTCUSDT",
        "source_data_family=kline",
        "source_routing_mode=shared_market_frame",
    }
    assert expected_bucket_keys.issubset(set(bucket_rows_by_key))
    request_bucket = bucket_rows_by_key["requested_validation=strict_validation"]
    assert int(request_bucket["evidence_request_count"]) == len(
        expected_evidence_request_trial_ids
    )
    assert int(request_bucket["unique_evidence_request_trial_count"]) == len(
        set(expected_evidence_request_trial_ids)
    )
    assert int(request_bucket["best_leaderboard_rank"]) == 1
    assert json.loads(
        request_bucket["representative_evidence_request_trial_ids"]
    ) == expected_evidence_request_trial_ids[:5]
    bybit_bucket = bucket_rows_by_key["tested_venue=bybit"]
    assert bybit_bucket["bucket_type"] == "tested_venue"
    assert bybit_bucket["venue"] == "bybit"
    assert int(bybit_bucket["evidence_request_count"]) == len(
        expected_evidence_request_trial_ids
    )
    source_bybit_bucket = bucket_rows_by_key["source_venue=bybit"]
    assert source_bybit_bucket["bucket_type"] == "source_venue"
    assert source_bybit_bucket["source_venue"] == "bybit"
    assert bool(source_bybit_bucket["source_context_available"]) is True
    assert int(source_bybit_bucket["evidence_request_count"]) == (
        expected_source_venue_counts["bybit"]
    )
    source_okx_bucket = bucket_rows_by_key["source_venue=okx"]
    assert source_okx_bucket["bucket_type"] == "source_venue"
    assert source_okx_bucket["source_venue"] == "okx"
    assert int(source_okx_bucket["evidence_request_count"]) == (
        expected_source_venue_counts["okx"]
    )
    source_routing_bucket = bucket_rows_by_key[
        "source_routing_mode=shared_market_frame"
    ]
    assert source_routing_bucket["bucket_type"] == "source_routing_mode"
    assert source_routing_bucket["source_routing_mode"] == "shared_market_frame"
    assert int(source_routing_bucket["evidence_request_count"]) == (
        expected_request_count
    )
    assert Path(
        str(catalog["global_evidence_request_bucket_representatives_parquet_path"])
    ).exists()
    assert (
        catalog["global_evidence_request_bucket_representative_parquet_row_count"]
        == len(global_evidence_request_bucket_representatives_frame)
    )
    assert sidecar_row_counts["global_evidence_request_bucket_representatives"] == len(
        global_evidence_request_bucket_representatives_frame
    )
    assert not global_evidence_request_bucket_representatives_frame.empty
    assert set(
        global_evidence_request_bucket_representatives_frame[
            "candidate_pack_eligible"
        ]
    ) == {False}
    assert set(
        global_evidence_request_bucket_representatives_frame[
            "strict_validation_authorized"
        ]
    ) == {False}
    assert set(
        global_evidence_request_bucket_representatives_frame[
            "candidate_pack_write_authorized"
        ]
    ) == {False}
    request_representatives = global_evidence_request_bucket_representatives_frame[
        global_evidence_request_bucket_representatives_frame["bucket_key"]
        == "requested_validation=strict_validation"
    ]
    assert len(request_representatives) == min(
        5,
        len(expected_evidence_request_trial_ids),
    )
    assert list(request_representatives["representative_rank"]) == list(
        range(1, len(request_representatives) + 1)
    )
    assert list(request_representatives["evidence_request_trial_id"]) == (
        expected_evidence_request_trial_ids[: len(request_representatives)]
    )
    assert set(request_representatives["bucket_queue_rank"]) == {
        int(request_bucket["queue_rank"])
    }
    assert set(request_representatives["bucket_requested_validation"]) == {
        "strict_validation"
    }
    assert set(request_representatives["requested_validation"]) == {
        "strict_validation"
    }
    bybit_representatives = global_evidence_request_bucket_representatives_frame[
        global_evidence_request_bucket_representatives_frame["bucket_key"]
        == "tested_venue=bybit"
    ]
    assert not bybit_representatives.empty
    assert set(bybit_representatives["bucket_venue"]) == {"bybit"}
    assert set(bybit_representatives["hypothesis_id"]) == {"fallback-long"}
    assert {
        venue
        for cell in bybit_representatives["venues_tested"]
        for venue in json.loads(cell)
    } == {"bybit", "okx"}
    source_bybit_representatives = global_evidence_request_bucket_representatives_frame[
        global_evidence_request_bucket_representatives_frame["bucket_key"]
        == "source_venue=bybit"
    ]
    assert not source_bybit_representatives.empty
    assert set(source_bybit_representatives["bucket_source_venue"]) == {"bybit"}
    assert set(source_bybit_representatives["source_venue"]) == {"bybit"}
    assert set(source_bybit_representatives["source_context_available"]) == {True}
    assert set(source_bybit_representatives["source_requested_validation"]) == {
        "strict_research_cycle_request"
    }
    source_routing_representatives = global_evidence_request_bucket_representatives_frame[
        global_evidence_request_bucket_representatives_frame["bucket_key"]
        == "source_routing_mode=shared_market_frame"
    ]
    assert not source_routing_representatives.empty
    assert set(source_routing_representatives["bucket_source_routing_mode"]) == {
        "shared_market_frame"
    }
    assert set(source_routing_representatives["source_routing_mode"]) == {
        "shared_market_frame"
    }
    assert Path(str(catalog["global_bucket_top_buckets_parquet_path"])).exists()
    assert catalog["global_bucket_top_bucket_parquet_row_count"] == len(
        payload["top_buckets"]
    )
    assert len(global_bucket_top_bucket_frame) == len(payload["top_buckets"])
    assert sidecar_row_counts["global_bucket_top_buckets"] == len(
        global_bucket_top_bucket_frame
    )
    assert set(global_bucket_top_bucket_frame["candidate_pack_eligible"]) == {False}
    assert set(global_bucket_top_bucket_frame["strict_validation_authorized"]) == {
        False
    }
    assert set(
        global_bucket_top_bucket_frame["candidate_pack_write_authorized"]
    ) == {False}
    assert set(
        global_bucket_top_bucket_frame["source_bucket_leaderboard_parquet_path"]
    ) == {payload["bucket_leaderboard_parquet_path"]}
    assert set(global_bucket_top_bucket_frame["source_artifact_path"]) == {
        payload["leaderboard_json_path"]
    }
    assert list(global_bucket_top_bucket_frame["top_bucket_row_rank"]) == list(
        range(1, len(global_bucket_top_bucket_frame) + 1)
    )
    assert list(global_bucket_top_bucket_frame["bucket_leaderboard_rank"]) == [
        row["bucket_leaderboard_rank"] for row in payload["top_buckets"]
    ]
    global_bybit_bucket = global_bucket_top_bucket_frame[
        global_bucket_top_bucket_frame["bucket_key"] == "venue=bybit"
    ].iloc[0]
    assert global_bybit_bucket["bucket_type"] == "venue"
    assert json.loads(global_bybit_bucket["bucket_values"]) == {"venue": "bybit"}
    assert (
        global_bybit_bucket["bucket_leaderboard_decision"]
        == "request_strict_validation"
    )


def test_sandbox_global_leaderboard_rejects_promotable_rankings(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("sandbox-global-leaderboard-boundary-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx")],
        output_root=tmp_path / "runs",
    )
    rankings = pd.read_parquet(run.artifacts.rankings_parquet_path)
    rankings["promotion_ready"] = True
    rankings.to_parquet(run.artifacts.rankings_parquet_path, index=False)
    _refresh_manifest_artifact_integrity(run.artifacts.manifest_path, "rankings_parquet", run.artifacts.rankings_parquet_path)

    with pytest.raises(ValueError, match="non-promotable boundary"):
        build_sandbox_global_leaderboard(tmp_path, output_dir=tmp_path / "leaderboard")


def test_sandbox_compatibility_preflight_reports_trial_matrix_and_blueprints(tmp_path: Path) -> None:
    okx_path = tmp_path / "okx_market.csv"
    bybit_path = tmp_path / "bybit_market.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0, 102.0, 104.0, 103.0, 105.0, 106.0, 107.0, 108.0],
            "high": [101.0, 103.0, 105.0, 104.0, 106.0, 107.0, 108.0, 109.0],
            "low": [99.0, 101.0, 103.0, 102.0, 104.0, 105.0, 106.0, 107.0],
            "fallback_signal": [1] * 8,
            "quality": [0.8] * 8,
        }
    ).to_csv(okx_path, index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0, 102.0, 104.0, 103.0, 105.0, 106.0, 107.0, 108.0],
        }
    ).to_csv(bybit_path, index=False)
    spec = SandboxRunSpec(
        run_id="compatibility-preflight",
        data_window=DataWindow("2024-01-01", "2024-01-02"),
        holding_periods=(1,),
        exit_variants=(
            ExitVariant(variant_id="hold", exit_profile="fixed_hold"),
            ExitVariant(variant_id="target", exit_profile="target_only", target_return=0.01),
        ),
        filter_variants=(
            FilterVariant(variant_id="base"),
            FilterVariant(variant_id="quality-gate", filter_column="quality", filter_min=0.5),
        ),
        min_trades=1,
    )
    venues = [
        VenueArchiveDescriptor(
            descriptor_id="okx-preflight",
            venue="okx",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-02"),
            data_path=okx_path,
        ),
        VenueArchiveDescriptor(
            descriptor_id="bybit-preflight",
            venue="bybit",
            symbol="BTCUSDT",
            data_family="kline",
            window=DataWindow("2024-01-01", "2024-01-02"),
            data_path=bybit_path,
        ),
    ]

    payload = preflight_sandbox_compatibility(
        spec=spec,
        strategies=[_strategy(), _blueprint_strategy()],
        venues=venues,
        output_dir=tmp_path / "preflight",
    )
    rows = {(row["descriptor_id"], row["hypothesis_id"]): row for row in payload["rows"]}
    frame = pd.read_parquet(Path(str(payload["preflight_parquet_path"])))
    catalog = index_sandbox_artifacts(tmp_path / "preflight", output_dir=tmp_path / "catalog")

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["trial_estimate"] == 16
    assert payload["runnable_trial_estimate"] == 9
    assert payload["blocked_trial_estimate"] == 7
    assert rows[("okx-preflight", "fallback-long")]["runnable_trial_estimate"] == 4
    assert rows[("okx-preflight", "compiled-momentum-long")]["runnable_trial_estimate"] == 4
    assert rows[("bybit-preflight", "fallback-long")]["status"] == "blocked"
    assert "missing_signal_column:fallback_signal" in rows[("bybit-preflight", "fallback-long")]["blocker_reasons"]
    assert rows[("bybit-preflight", "compiled-momentum-long")]["runnable_trial_estimate"] == 1
    assert rows[("bybit-preflight", "compiled-momentum-long")]["blocked_trial_estimate"] == 3
    assert "missing_ohlc_column:high" in rows[("bybit-preflight", "compiled-momentum-long")]["blocker_reasons"]
    assert set(frame["candidate_pack_eligible"]) == {False}
    assert catalog["artifact_kind_counts"]["compatibility_preflight"] == 1


def _write_agent_iteration_inputs(
    base_dir: Path,
    *,
    hypothesis_id: str = "agent-cache-long",
    family: str = "agent_cache_family",
    start: str = "2024-03-01",
) -> tuple[Path, Path]:
    catalog_root = base_dir / "catalogs"
    archive_root = base_dir / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": hypothesis_id,
                "family": family,
                "source_id": "agent-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range(start, periods=8, freq="1h", tz="UTC"),
            "close": [100.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "market.csv", index=False)
    return catalog_root, archive_root


def test_sandbox_agent_iteration_materializes_runs_and_reuses_manifest(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "agent-direct-long",
                "family": "agent_direct_family",
                "source_id": "agent-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    reused = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    steps = pd.read_parquet(Path(str(payload["iteration_steps_parquet_path"])))
    artifact_catalog = index_sandbox_artifacts(tmp_path / "iterations", output_dir=tmp_path / "catalog")

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["strict_validation_executed"] is False
    assert payload["candidate_pack_written"] is False
    assert payload["strategy_source"]["mode"] == "materialized_strategy_catalog"
    assert payload["archive_source"]["mode"] == "built_venue_archive_manifest"
    assert payload["iteration_status"] == "completed"
    assert payload["preflight_runnable_trial_estimate"] == 1
    assert payload["preflight_blocked_trial_estimate"] == 0
    assert payload["result_count"] == 1
    assert payload["evidence_request_count"] == 1
    assert payload["deduped_validation_request_count"] == 1
    assert payload["agent_brief_next_action"] == "review_descriptor_only_strict_validation_requests"
    assert Path(str(payload["iteration_manifest_path"])).exists()
    assert Path(str(payload["agent_brief_json_path"])).exists()
    assert Path(str(payload["agent_brief_parquet_path"])).exists()
    assert Path(str(payload["archive_coverage_json_path"])).exists()
    assert Path(str(payload["archive_coverage_parquet_path"])).exists()
    assert Path(str(payload["archive_coverage_source_audit_json_path"])).exists()
    assert Path(str(payload["archive_coverage_source_audit_parquet_path"])).exists()
    assert Path(str(payload["preflight_json_path"])).exists()
    assert Path(str(payload["preflight_parquet_path"])).exists()
    assert Path(str(payload["run_manifest_path"])).exists()
    assert Path(str(payload["strict_validation_request_bundle_json_path"])).exists()
    assert Path(str(payload["global_leaderboard_json_path"])).exists()
    assert payload["archive_coverage_descriptor_count"] == 1
    assert payload["archive_coverage_ready_descriptor_count"] == 1
    assert payload["archive_coverage_coverage_bucket_count"] == 1
    assert payload["archive_coverage_status_counts"] == {"ready": 1}
    brief = json.loads(Path(str(payload["agent_brief_json_path"])).read_text(encoding="utf-8"))
    brief_frame = pd.read_parquet(Path(str(payload["agent_brief_parquet_path"])))
    assert brief["research_only"] is True
    assert brief["promotion_ready"] is False
    assert brief["candidate_pack_eligible"] is False
    assert brief["next_action"] == "review_descriptor_only_strict_validation_requests"
    assert "descriptor_only_validation_requests_available" in brief["reason_codes"]
    assert brief["counts"]["deduped_validation_request_count"] == 1
    assert brief["top_validation_requests"][0]["hypothesis_id"] == "agent-direct-long"
    assert brief["artifact_paths"]["strict_validation_request_bundle_json_path"] == payload["strict_validation_request_bundle_json_path"]
    assert set(brief_frame["candidate_pack_eligible"]) == {False}
    assert set(steps["candidate_pack_eligible"]) == {False}
    assert set(steps["step_id"]) == {
        "strategy_catalog",
        "venue_archive_manifest",
        "archive_coverage_matrix",
        "compatibility_preflight",
        "archive_sweep",
        "analysis_summary",
        "hypothesis_falsification",
        "strict_validation_request_bundle",
        "global_leaderboard",
        "agent_brief",
    }
    assert artifact_catalog["artifact_kind_counts"]["agent_iteration_manifest"] == 1
    assert artifact_catalog["artifact_kind_counts"]["agent_iteration_brief"] == 1
    assert artifact_catalog["artifact_kind_counts"]["archive_coverage_matrix"] == 1
    assert artifact_catalog["artifact_kind_counts"]["compatibility_preflight"] == 1
    assert artifact_catalog["artifact_kind_counts"]["run_manifest"] == 1
    assert artifact_catalog["artifact_kind_counts"]["run_strict_validation_request_bundle"] == 1
    assert reused["reused_existing"] is True
    assert reused["cached_iteration_validation_status"] == "passed"
    assert reused["iteration_id"] == payload["iteration_id"]


def test_sandbox_agent_iteration_surfaces_rejection_falsification_samples(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "agent-rejected-long",
                "family": "agent_rejected_family",
                "source_id": "agent-rejected-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=8, freq="1h", tz="UTC"),
            "close": [107.0, 106.0, 105.0, 104.0, 103.0, 102.0, 101.0, 100.0],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="bybit",
        archive_symbol="ETHUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    brief = json.loads(Path(str(payload["agent_brief_json_path"])).read_text(encoding="utf-8"))
    brief_frame = pd.read_parquet(Path(str(payload["agent_brief_parquet_path"])))
    index_payload = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    index_row = index_payload["rows"][0]
    queue_item = index_payload["action_queues"]["rejection_review_queue"][0]
    action_plan_item = index_payload["agent_action_plan"][0]
    index_frame = pd.read_parquet(Path(str(index_payload["iteration_index_parquet_path"])))
    action_plan_frame = pd.read_parquet(Path(str(index_payload["agent_action_plan_parquet_path"])))

    assert payload["iteration_status"] == "completed"
    assert payload["result_count"] == 1
    assert payload["rejected_count"] == 1
    assert payload["evidence_request_count"] == 0
    assert payload["deduped_validation_request_count"] == 0
    assert payload["agent_brief_next_action"] == "review_rejections_and_falsified_hypotheses"
    assert payload["falsification_decision_counts"] == {"falsified_in_sandbox": 1}
    samples = payload["rejection_falsification_samples"]
    assert payload["rejection_falsification_samples_truncated"] is False
    assert len(samples) == 1
    sample = samples[0]
    assert sample["hypothesis_id"] == "agent-rejected-long"
    assert sample["family"] == "agent_rejected_family"
    assert sample["falsification_decision"] == "falsified_in_sandbox"
    assert sample["decision_reason"] == "all_completed_trials_failed_sandbox_screening"
    assert sample["best_status"] == "rejected"
    assert sample["best_venue"] == "bybit"
    assert sample["best_symbol"] == "ETHUSDT"
    assert sample["best_trade_count"] == 6
    assert sample["rejected_reason_counts"] == {"non_positive_net_return_after_costs": 1}
    assert sample["all_reason_counts"] == {"non_positive_net_return_after_costs": 1}
    assert sample["best_rejection_reasons"] == ["non_positive_net_return_after_costs"]

    assert brief["falsification_decision_counts"] == {"falsified_in_sandbox": 1}
    assert brief["rejection_falsification_samples"] == samples
    assert brief["rejection_falsification_samples_truncated"] is False
    assert json.loads(brief_frame.iloc[0]["rejection_falsification_samples"]) == samples
    assert index_payload["action_queue_version"] == 14
    assert index_payload["action_queue_counts"]["rejection_review_queue"] == 1
    assert index_payload["action_queue_counts"]["strict_validation_request_queue"] == 0
    assert index_payload["action_queue_counts"]["venue_expansion_gap_queue"] == 1
    assert index_payload["recommended_action_counts"] == {
        "repair_or_add_venue_expansion_archives": 1,
        "review_rejections_and_falsified_hypotheses": 1,
    }
    assert index_row["recommended_action"] == "repair_or_add_venue_expansion_archives"
    assert index_row["recommended_actions"][1]["action"] == "review_rejections_and_falsified_hypotheses"
    assert index_row["falsification_decision_counts"] == {"falsified_in_sandbox": 1}
    assert index_row["rejection_falsification_samples"] == samples
    assert index_row["recommended_actions"][1]["rejection_falsification_samples"] == samples
    assert queue_item["iteration_id"] == payload["iteration_id"]
    assert queue_item["recommended_action"] == "repair_or_add_venue_expansion_archives"
    assert queue_item["falsification_decision_counts"] == {"falsified_in_sandbox": 1}
    assert queue_item["rejection_falsification_samples"] == samples
    assert queue_item["recommended_actions"][1]["rejection_falsification_samples"] == samples
    assert index_payload["action_queue_summaries"]["rejection_review_queue"]["falsification_decision_counts"] == {
        "falsified_in_sandbox": 1
    }
    assert action_plan_item["action"] == "repair_or_add_venue_expansion_archives"
    assert action_plan_item["source_queues"] == ["venue_expansion_gap_queue"]
    rejection_plan_item = index_payload["agent_action_plan"][1]
    assert rejection_plan_item["action"] == "review_rejections_and_falsified_hypotheses"
    assert rejection_plan_item["source_queues"] == ["rejection_review_queue"]
    assert rejection_plan_item["rejection_falsification_samples"] == samples
    assert json.loads(index_frame.iloc[0]["rejection_falsification_samples"]) == samples
    assert json.loads(action_plan_frame.iloc[1]["rejection_falsification_samples"]) == samples
    assert set(index_frame["candidate_pack_eligible"]) == {False}
    assert set(action_plan_frame["candidate_pack_eligible"]) == {False}


def test_sandbox_agent_iteration_surfaces_input_replay_context(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "agent-replay-long",
                "family": "agent_replay_family",
                "source_id": "agent-replay-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-04-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="hyperliquid",
        archive_symbol="BTC",
        archive_data_family="trade",
        archive_interval="1h",
        window_start="2024-04-01",
        window_end="2024-04-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=2,
        rank_top_n=7,
        min_request_score=0.0,
        catalog_max_files=17,
        archive_max_files=19,
        leaderboard_max_runs=23,
        leaderboard_top_n=5,
    )
    brief = json.loads(Path(str(payload["agent_brief_json_path"])).read_text(encoding="utf-8"))
    brief_frame = pd.read_parquet(Path(str(payload["agent_brief_parquet_path"])))
    index_payload = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    index_row = index_payload["rows"][0]
    queue_item = index_payload["action_queues"]["strict_validation_request_queue"][0]
    action_plan_item = index_payload["agent_action_plan"][0]
    index_frame = pd.read_parquet(Path(str(index_payload["iteration_index_parquet_path"])))
    action_plan_frame = pd.read_parquet(Path(str(index_payload["agent_action_plan_parquet_path"])))
    worklist_payload = json.loads(Path(str(index_payload["input_replay_worklist_json_path"])).read_text(encoding="utf-8"))
    worklist_frame = pd.read_parquet(Path(str(index_payload["input_replay_worklist_parquet_path"])))
    batch_plan_payload = json.loads(
        Path(str(index_payload["input_replay_batch_plan_json_path"])).read_text(encoding="utf-8")
    )
    batch_plan_frame = pd.read_parquet(Path(str(index_payload["input_replay_batch_plan_parquet_path"])))

    context = payload["input_replay_context"]
    argv = context["command_argv"]
    assert context["research_only"] is True
    assert context["promotion_ready"] is False
    assert context["candidate_pack_eligible"] is False
    assert context["execution_mode"] == "descriptor_only_no_execution"
    assert context["command"] == "run-rapid-strategy-sandbox-iteration"
    assert context["strategy_input_mode"] == "catalog_roots"
    assert context["venue_input_mode"] == "archive_roots"
    assert context["catalog_root_paths"] == [str(catalog_root.resolve())]
    assert context["archive_root_paths"] == [str(archive_root.resolve())]
    assert context["holding_periods"] == [1]
    assert context["archive_venue"] == "hyperliquid"
    assert context["archive_symbol"] == "BTC"
    assert context["archive_data_family"] == "trade"
    assert context["leaderboard_top_n"] == 5
    assert argv[:4] == ["python", "-m", "tradingbotsuite.main", "run-rapid-strategy-sandbox-iteration"]
    assert argv[argv.index("--output-dir") + 1] == str((tmp_path / "iterations").resolve())
    assert argv[argv.index("--catalog-root") + 1] == str(catalog_root.resolve())
    assert argv[argv.index("--archive-root") + 1] == str(archive_root.resolve())
    assert argv[argv.index("--window-start") + 1] == "2024-04-01"
    assert argv[argv.index("--holding-periods") + 1] == "1"
    assert argv[argv.index("--archive-venue") + 1] == "hyperliquid"
    assert argv[argv.index("--min-request-score") + 1] == "0.0"

    assert brief["input_replay_context"] == context
    assert json.loads(brief_frame.iloc[0]["input_replay_context"]) == context
    assert index_payload["action_queue_version"] == 14
    assert index_row["input_replay_context"] == context
    assert index_row["input_replay_context_id"] == context["replay_context_id"]
    assert index_row["input_replay_command_argv"] == argv
    assert queue_item["input_replay_context"] == context
    assert queue_item["input_replay_command_argv"] == argv
    assert action_plan_item["input_replay_context"] == context
    assert action_plan_item["input_replay_command_argv"] == argv
    assert json.loads(index_frame.iloc[0]["input_replay_context"]) == context
    assert json.loads(index_frame.iloc[0]["input_replay_command_argv"]) == argv
    assert json.loads(action_plan_frame.iloc[0]["input_replay_context"]) == context
    assert json.loads(action_plan_frame.iloc[0]["input_replay_command_argv"]) == argv
    assert index_payload["input_replay_worklist_version"] == 1
    assert index_payload["input_replay_worklist_count"] == 1
    assert index_payload["input_replay_context_missing_count"] == 0
    assert index_payload["input_replay_batch_plan_version"] == 1
    assert index_payload["input_replay_batch_plan_count"] == 1
    assert index_payload["input_replay_worklist_summary"]["ready_count"] == 1
    assert index_payload["input_replay_worklist_summary"]["command_counts"] == {
        "run-rapid-strategy-sandbox-iteration": 1
    }
    worklist_item = index_payload["input_replay_worklist"][0]
    batch_plan_item = index_payload["input_replay_batch_plan"][0]
    assert worklist_payload["research_only"] is True
    assert worklist_payload["promotion_ready"] is False
    assert worklist_payload["candidate_pack_eligible"] is False
    assert worklist_payload["worklist_version"] == 1
    assert worklist_payload["item_count"] == 1
    assert worklist_payload["items"][0] == worklist_item
    assert batch_plan_payload["research_only"] is True
    assert batch_plan_payload["promotion_ready"] is False
    assert batch_plan_payload["candidate_pack_eligible"] is False
    assert batch_plan_payload["descriptor_only"] is True
    assert batch_plan_payload["replay_command_execution_authorized"] is False
    assert batch_plan_payload["strict_validation_authorized"] is False
    assert batch_plan_payload["plan_version"] == 1
    assert batch_plan_payload["item_count"] == 1
    assert batch_plan_payload["items"][0] == batch_plan_item
    assert worklist_item["input_replay_ready"] is True
    assert worklist_item["input_replay_blocker_reasons"] == []
    assert worklist_item["input_replay_context"] == context
    assert worklist_item["input_replay_context_id"] == context["replay_context_id"]
    assert worklist_item["input_replay_command_argv"] == argv
    assert worklist_item["input_replay_archive_venue"] == "hyperliquid"
    assert worklist_item["input_replay_window_start"] == "2024-04-01"
    assert worklist_item["input_replay_path_availability_status"] == "all_present"
    assert worklist_item["input_replay_path_reference_count"] == 3
    assert worklist_item["input_replay_path_present_count"] == 3
    assert worklist_item["input_replay_path_missing_count"] == 0
    assert worklist_item["input_replay_path_wrong_type_count"] == 0
    assert worklist_item["input_replay_path_missing_keys"] == []
    assert worklist_item["input_replay_path_status_counts"] == {"present": 3}
    assert {reference["key"] for reference in worklist_item["input_replay_path_references"]} == {
        "output_dir",
        "catalog_root_paths[1]",
        "archive_root_paths[1]",
    }
    assert index_payload["input_replay_worklist_summary"]["path_availability_status_counts"] == {"all_present": 1}
    assert index_payload["input_replay_worklist_summary"]["total_path_reference_count"] == 3
    assert index_payload["input_replay_worklist_summary"]["total_path_missing_count"] == 0
    assert index_payload["input_replay_worklist_summary"]["archive_venue_counts"] == {"hyperliquid": 1}
    assert index_payload["input_replay_worklist_summary"]["archive_symbol_counts"] == {"BTC": 1}
    assert index_payload["input_replay_worklist_summary"]["archive_data_family_counts"] == {"trade": 1}
    assert index_payload["input_replay_worklist_summary"]["archive_interval_counts"] == {"1h": 1}
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_counts"] == {
        "hyperliquid|BTC|trade|1h": 1
    }
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_ready_counts"] == {
        "hyperliquid|BTC|trade|1h": 1
    }
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_blocked_counts"] == {}
    assert index_payload["input_replay_worklist_summary"]["window_bucket_counts"] == {
        "2024-04-01|2024-04-02|explicit": 1
    }
    assert index_payload["input_replay_worklist_summary"]["archive_window_bucket_counts"] == {
        "hyperliquid|BTC|trade|1h|2024-04-01|2024-04-02": 1
    }
    assert index_payload["input_replay_worklist_summary"]["archive_window_ready_counts"] == {
        "hyperliquid|BTC|trade|1h|2024-04-01|2024-04-02": 1
    }
    assert index_payload["input_replay_worklist_summary"]["unique_replay_context_count"] == 1
    assert index_payload["input_replay_worklist_summary"]["replay_context_group_counts"] == {
        context["replay_context_id"]: 1
    }
    assert index_payload["input_replay_worklist_summary"]["duplicate_replay_context_group_count"] == 0
    assert index_payload["input_replay_worklist_summary"]["duplicate_replay_context_item_count"] == 0
    assert index_payload["input_replay_worklist_summary"]["duplicate_replay_context_group_counts"] == {}
    assert index_payload["input_replay_worklist_summary"]["duplicate_replay_context_group_keys"] == []
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_unique_replay_context_counts"] == {
        "hyperliquid|BTC|trade|1h": 1
    }
    assert index_payload["input_replay_worklist_summary"]["archive_window_unique_replay_context_counts"] == {
        "hyperliquid|BTC|trade|1h|2024-04-01|2024-04-02": 1
    }
    assert worklist_item["input_replay_duplicate_group_key"] == context["replay_context_id"]
    assert worklist_item["input_replay_context_duplicate_count"] == 1
    assert worklist_item["input_replay_context_is_duplicate"] is False
    assert index_payload["input_replay_batch_plan_summary"]["source_worklist_item_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["ready_source_item_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["blocked_source_item_count"] == 0
    assert index_payload["input_replay_batch_plan_summary"]["plan_item_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["suppressed_duplicate_source_item_count"] == 0
    assert index_payload["input_replay_batch_plan_summary"]["plan_archive_bucket_counts"] == {
        "hyperliquid|BTC|trade|1h": 1
    }
    assert batch_plan_item["descriptor_only"] is True
    assert batch_plan_item["replay_command_execution_authorized"] is False
    assert batch_plan_item["strict_validation_authorized"] is False
    assert batch_plan_item["input_replay_ready"] is True
    assert batch_plan_item["input_replay_context"] == context
    assert batch_plan_item["input_replay_context_id"] == context["replay_context_id"]
    assert batch_plan_item["input_replay_duplicate_group_key"] == context["replay_context_id"]
    assert batch_plan_item["input_replay_command_argv"] == argv
    assert batch_plan_item["source_item_count"] == 1
    assert batch_plan_item["suppressed_duplicate_count"] == 0
    assert batch_plan_item["source_iteration_ids"] == [payload["iteration_id"]]
    assert batch_plan_item["suppressed_duplicate_iteration_ids"] == []
    assert worklist_item["candidate_pack_eligible"] is False
    assert json.loads(worklist_frame.iloc[0]["input_replay_context"]) == context
    assert json.loads(worklist_frame.iloc[0]["input_replay_command_argv"]) == argv
    assert json.loads(worklist_frame.iloc[0]["input_replay_path_missing_keys"]) == []
    assert json.loads(worklist_frame.iloc[0]["input_replay_path_status_counts"]) == {"present": 3}
    assert worklist_frame.iloc[0]["input_replay_duplicate_group_key"] == context["replay_context_id"]
    assert int(worklist_frame.iloc[0]["input_replay_context_duplicate_count"]) == 1
    assert bool(worklist_frame.iloc[0]["input_replay_context_is_duplicate"]) is False
    assert json.loads(batch_plan_frame.iloc[0]["input_replay_context"]) == context
    assert json.loads(batch_plan_frame.iloc[0]["input_replay_command_argv"]) == argv
    assert batch_plan_frame.iloc[0]["input_replay_duplicate_group_key"] == context["replay_context_id"]
    assert int(batch_plan_frame.iloc[0]["source_item_count"]) == 1
    assert int(batch_plan_frame.iloc[0]["suppressed_duplicate_count"]) == 0
    assert set(worklist_frame["candidate_pack_eligible"]) == {False}
    assert set(batch_plan_frame["candidate_pack_eligible"]) == {False}
    assert set(index_frame["candidate_pack_eligible"]) == {False}
    assert set(action_plan_frame["candidate_pack_eligible"]) == {False}


def test_sandbox_iteration_input_replay_worklist_groups_duplicate_contexts(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "agent-replay-duplicate",
                "family": "agent_replay_family",
                "source_id": "agent-replay-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-04-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-04-01",
        window_end="2024-04-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=2,
        min_request_score=0.0,
    )
    original_manifest_path = Path(str(payload["iteration_manifest_path"]))
    original_brief_path = Path(str(payload["agent_brief_json_path"]))
    duplicate_dir = original_manifest_path.parent.parent / "duplicate_replay_iteration"
    duplicate_dir.mkdir()
    duplicate_manifest_path = duplicate_dir / original_manifest_path.name
    duplicate_brief_path = duplicate_dir / original_brief_path.name
    duplicate_iteration_id = f"{payload['iteration_id']}-duplicate"

    manifest_payload = json.loads(original_manifest_path.read_text(encoding="utf-8"))
    manifest_payload["iteration_id"] = duplicate_iteration_id
    manifest_payload["iteration_dir"] = str(duplicate_dir)
    manifest_payload["agent_brief_json_path"] = str(duplicate_brief_path)
    manifest_payload.setdefault("artifact_paths", {})["iteration_manifest_path"] = str(duplicate_manifest_path)
    manifest_payload["artifact_paths"]["agent_brief_json_path"] = str(duplicate_brief_path)
    duplicate_manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    brief_payload = json.loads(original_brief_path.read_text(encoding="utf-8"))
    brief_payload["iteration_id"] = duplicate_iteration_id
    brief_payload["iteration_dir"] = str(duplicate_dir)
    brief_payload.setdefault("artifact_paths", {})["iteration_manifest_path"] = str(duplicate_manifest_path)
    brief_payload["artifact_paths"]["agent_brief_json_path"] = str(duplicate_brief_path)
    duplicate_brief_path.write_text(json.dumps(brief_payload, indent=2, sort_keys=True), encoding="utf-8")

    index_payload = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    worklist_payload = json.loads(Path(str(index_payload["input_replay_worklist_json_path"])).read_text(encoding="utf-8"))
    worklist_frame = pd.read_parquet(Path(str(index_payload["input_replay_worklist_parquet_path"])))
    batch_plan_payload = json.loads(
        Path(str(index_payload["input_replay_batch_plan_json_path"])).read_text(encoding="utf-8")
    )
    batch_plan_frame = pd.read_parquet(Path(str(index_payload["input_replay_batch_plan_parquet_path"])))
    artifact_catalog = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")
    context_id = payload["input_replay_context"]["replay_context_id"]
    archive_bucket = "okx|BTCUSDT|kline|1h"
    archive_window_bucket = "okx|BTCUSDT|kline|1h|2024-04-01|2024-04-02"

    assert index_payload["input_replay_worklist_count"] == 2
    assert index_payload["input_replay_worklist_summary"]["ready_count"] == 2
    assert index_payload["input_replay_worklist_summary"]["unique_replay_context_count"] == 1
    assert index_payload["input_replay_worklist_summary"]["replay_context_group_counts"] == {context_id: 2}
    assert index_payload["input_replay_worklist_summary"]["duplicate_replay_context_group_count"] == 1
    assert index_payload["input_replay_worklist_summary"]["duplicate_replay_context_item_count"] == 2
    assert index_payload["input_replay_worklist_summary"]["duplicate_replay_context_group_counts"] == {
        context_id: 2
    }
    assert index_payload["input_replay_worklist_summary"]["duplicate_replay_context_group_keys"] == [context_id]
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_counts"] == {archive_bucket: 2}
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_unique_replay_context_counts"] == {
        archive_bucket: 1
    }
    assert index_payload["input_replay_worklist_summary"]["archive_window_bucket_counts"] == {
        archive_window_bucket: 2
    }
    assert index_payload["input_replay_worklist_summary"]["archive_window_unique_replay_context_counts"] == {
        archive_window_bucket: 1
    }
    assert {item["iteration_id"] for item in index_payload["input_replay_worklist"]} == {
        payload["iteration_id"],
        duplicate_iteration_id,
    }
    assert {item["input_replay_duplicate_group_key"] for item in index_payload["input_replay_worklist"]} == {
        context_id
    }
    assert {item["input_replay_context_duplicate_count"] for item in index_payload["input_replay_worklist"]} == {2}
    assert {item["input_replay_context_is_duplicate"] for item in index_payload["input_replay_worklist"]} == {True}
    assert {item["input_replay_ready"] for item in index_payload["input_replay_worklist"]} == {True}
    assert worklist_payload["summary"]["duplicate_replay_context_group_counts"] == {context_id: 2}
    assert {item["input_replay_context_duplicate_count"] for item in worklist_payload["items"]} == {2}
    assert set(worklist_frame["input_replay_duplicate_group_key"]) == {context_id}
    assert set(worklist_frame["input_replay_context_duplicate_count"]) == {2}
    assert {bool(value) for value in worklist_frame["input_replay_context_is_duplicate"]} == {True}
    assert index_payload["input_replay_batch_plan_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["source_worklist_item_count"] == 2
    assert index_payload["input_replay_batch_plan_summary"]["ready_source_item_count"] == 2
    assert index_payload["input_replay_batch_plan_summary"]["blocked_source_item_count"] == 0
    assert index_payload["input_replay_batch_plan_summary"]["plan_item_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["unique_ready_replay_context_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["suppressed_duplicate_source_item_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["ready_duplicate_group_counts"] == {context_id: 2}
    assert index_payload["input_replay_batch_plan_summary"]["planned_duplicate_group_keys"] == [context_id]
    assert index_payload["input_replay_batch_plan_summary"]["ready_archive_bucket_counts"] == {archive_bucket: 2}
    assert index_payload["input_replay_batch_plan_summary"]["plan_archive_bucket_counts"] == {archive_bucket: 1}
    assert index_payload["input_replay_batch_plan_summary"]["ready_archive_window_bucket_counts"] == {
        archive_window_bucket: 2
    }
    assert index_payload["input_replay_batch_plan_summary"]["plan_archive_window_bucket_counts"] == {
        archive_window_bucket: 1
    }
    batch_plan_item = index_payload["input_replay_batch_plan"][0]
    assert batch_plan_payload["items"][0] == batch_plan_item
    assert batch_plan_payload["summary"]["suppressed_duplicate_source_item_count"] == 1
    assert batch_plan_item["input_replay_context_id"] == context_id
    assert batch_plan_item["input_replay_duplicate_group_key"] == context_id
    assert batch_plan_item["input_replay_command_argv"] == payload["input_replay_context"]["command_argv"]
    assert batch_plan_item["source_item_count"] == 2
    assert batch_plan_item["suppressed_duplicate_count"] == 1
    assert set(batch_plan_item["source_iteration_ids"]) == {payload["iteration_id"], duplicate_iteration_id}
    assert batch_plan_item["suppressed_duplicate_iteration_ids"] == [duplicate_iteration_id]
    assert batch_plan_item["candidate_pack_eligible"] is False
    assert set(batch_plan_frame["input_replay_duplicate_group_key"]) == {context_id}
    assert set(batch_plan_frame["source_item_count"]) == {2}
    assert set(batch_plan_frame["suppressed_duplicate_count"]) == {1}
    assert artifact_catalog["artifact_kind_counts"]["iteration_input_replay_worklist"] == 1
    assert artifact_catalog["artifact_kind_counts"]["iteration_input_replay_batch_plan"] == 1
    batch_plan_catalog_row = next(
        row
        for row in artifact_catalog["artifacts"]
        if row["artifact_kind"] == "iteration_input_replay_batch_plan"
    )
    assert batch_plan_catalog_row["source_worklist_item_count"] == 2
    assert batch_plan_catalog_row["ready_source_item_count"] == 2
    assert batch_plan_catalog_row["blocked_source_item_count"] == 0
    assert batch_plan_catalog_row["suppressed_duplicate_source_item_count"] == 1
    assert batch_plan_catalog_row["plan_item_count"] == 1
    assert batch_plan_catalog_row["unique_ready_replay_context_count"] == 1
    assert batch_plan_catalog_row["ready_archive_bucket_counts"] == {archive_bucket: 2}
    assert batch_plan_catalog_row["plan_archive_bucket_counts"] == {archive_bucket: 1}
    assert batch_plan_catalog_row["ready_archive_window_bucket_counts"] == {
        archive_window_bucket: 2
    }
    assert batch_plan_catalog_row["plan_archive_window_bucket_counts"] == {
        archive_window_bucket: 1
    }
    assert batch_plan_catalog_row["descriptor_count"] == 1
    assert batch_plan_catalog_row["descriptor_only"] is True
    assert batch_plan_catalog_row["strict_validation_executed"] is False
    assert batch_plan_catalog_row["candidate_pack_written"] is False
    assert artifact_catalog["replay_batch_plan_summary"] == {
        "artifact_count": 1,
        "blocked_source_item_count": 0,
        "descriptor_count": 1,
        "plan_item_count": 1,
        "plan_archive_bucket_counts": {archive_bucket: 1},
        "plan_archive_window_bucket_counts": {archive_window_bucket: 1},
        "ready_archive_bucket_counts": {archive_bucket: 2},
        "ready_archive_window_bucket_counts": {archive_window_bucket: 2},
        "ready_source_item_count": 2,
        "source_worklist_item_count": 2,
        "status_counts": {"ready": 1},
        "suppressed_duplicate_source_item_count": 1,
        "unique_ready_replay_context_count": 1,
    }
    assert artifact_catalog["replay_batch_plan_queue_count"] == 1
    replay_queue_item = artifact_catalog["replay_batch_plan_queue"][0]
    assert replay_queue_item["replay_batch_plan_status"] == "ready"
    assert replay_queue_item["descriptor_count"] == 1
    assert replay_queue_item["source_worklist_item_count"] == 2
    assert replay_queue_item["ready_source_item_count"] == 2
    assert replay_queue_item["blocked_source_item_count"] == 0
    assert replay_queue_item["suppressed_duplicate_source_item_count"] == 1
    assert replay_queue_item["plan_item_count"] == 1
    assert replay_queue_item["unique_ready_replay_context_count"] == 1
    assert replay_queue_item["ready_archive_bucket_counts"] == {archive_bucket: 2}
    assert replay_queue_item["plan_archive_bucket_counts"] == {archive_bucket: 1}
    assert replay_queue_item["ready_archive_window_bucket_counts"] == {
        archive_window_bucket: 2
    }
    assert replay_queue_item["plan_archive_window_bucket_counts"] == {
        archive_window_bucket: 1
    }
    assert replay_queue_item["candidate_pack_eligible"] is False
    assert replay_queue_item["strict_validation_executed"] is False
    assert artifact_catalog["replay_batch_plan_bucket_queue_limit"] == 50
    assert artifact_catalog["replay_batch_plan_bucket_representative_limit"] == 5
    assert artifact_catalog["replay_batch_plan_archive_bucket_queue_count"] == 1
    assert artifact_catalog["replay_batch_plan_archive_window_bucket_queue_count"] == 1
    archive_bucket_queue_item = artifact_catalog["replay_batch_plan_archive_bucket_queue"][0]
    assert archive_bucket_queue_item["bucket_type"] == "archive_bucket"
    assert archive_bucket_queue_item["archive_bucket"] == archive_bucket
    assert archive_bucket_queue_item["artifact_count"] == 1
    assert archive_bucket_queue_item["ready_artifact_count"] == 1
    assert archive_bucket_queue_item["plan_artifact_count"] == 1
    assert archive_bucket_queue_item["ready_source_item_count"] == 2
    assert archive_bucket_queue_item["plan_item_count"] == 1
    assert archive_bucket_queue_item["representative_count"] == 1
    assert archive_bucket_queue_item["candidate_pack_eligible"] is False
    assert archive_bucket_queue_item["replay_command_execution_authorized"] is False
    assert archive_bucket_queue_item["strict_validation_authorized"] is False
    assert archive_bucket_queue_item["candidate_pack_write_authorized"] is False
    archive_bucket_representative = archive_bucket_queue_item["representatives"][0]
    assert archive_bucket_representative["artifact_path"] == batch_plan_catalog_row["artifact_path"]
    assert archive_bucket_representative["bucket_ready_source_item_count"] == 2
    assert archive_bucket_representative["bucket_plan_item_count"] == 1
    assert archive_bucket_representative["candidate_pack_eligible"] is False
    assert archive_bucket_representative["replay_command_execution_authorized"] is False
    archive_window_bucket_queue_item = artifact_catalog[
        "replay_batch_plan_archive_window_bucket_queue"
    ][0]
    assert archive_window_bucket_queue_item["bucket_type"] == "archive_window_bucket"
    assert archive_window_bucket_queue_item["archive_window_bucket"] == archive_window_bucket
    assert archive_window_bucket_queue_item["artifact_count"] == 1
    assert archive_window_bucket_queue_item["ready_source_item_count"] == 2
    assert archive_window_bucket_queue_item["plan_item_count"] == 1
    assert archive_window_bucket_queue_item["representative_count"] == 1
    archive_window_bucket_representative = archive_window_bucket_queue_item[
        "representatives"
    ][0]
    assert archive_window_bucket_representative["artifact_path"] == batch_plan_catalog_row["artifact_path"]
    assert archive_window_bucket_representative["bucket_ready_source_item_count"] == 2
    assert archive_window_bucket_representative["bucket_plan_item_count"] == 1
    assert archive_window_bucket_representative["candidate_pack_eligible"] is False
    assert artifact_catalog["replay_batch_plan_bucket_queue_parquet_row_count"] == 2
    assert artifact_catalog["replay_batch_plan_bucket_representative_parquet_row_count"] == 2
    bucket_queue_parquet_path = Path(
        str(artifact_catalog["replay_batch_plan_bucket_queue_parquet_path"])
    )
    bucket_representatives_parquet_path = Path(
        str(artifact_catalog["replay_batch_plan_bucket_representatives_parquet_path"])
    )
    assert bucket_queue_parquet_path.exists()
    assert bucket_representatives_parquet_path.exists()
    bucket_queue_frame = pd.read_parquet(bucket_queue_parquet_path)
    bucket_representatives_frame = pd.read_parquet(bucket_representatives_parquet_path)
    assert len(bucket_queue_frame) == 2
    assert len(bucket_representatives_frame) == 2
    archive_bucket_sidecar_row = bucket_queue_frame[
        bucket_queue_frame["bucket_type"] == "archive_bucket"
    ].iloc[0]
    assert archive_bucket_sidecar_row["bucket_key"] == archive_bucket
    assert archive_bucket_sidecar_row["archive_bucket"] == archive_bucket
    assert int(archive_bucket_sidecar_row["ready_source_item_count"]) == 2
    assert int(archive_bucket_sidecar_row["plan_item_count"]) == 1
    assert json.loads(archive_bucket_sidecar_row["representative_artifact_paths_relative"]) == [
        batch_plan_catalog_row["artifact_path_relative"]
    ]
    archive_window_bucket_sidecar_row = bucket_queue_frame[
        bucket_queue_frame["bucket_type"] == "archive_window_bucket"
    ].iloc[0]
    assert archive_window_bucket_sidecar_row["bucket_key"] == archive_window_bucket
    assert archive_window_bucket_sidecar_row["archive_window_bucket"] == archive_window_bucket
    archive_bucket_representative_row = bucket_representatives_frame[
        bucket_representatives_frame["bucket_type"] == "archive_bucket"
    ].iloc[0]
    assert archive_bucket_representative_row["bucket_key"] == archive_bucket
    assert archive_bucket_representative_row["artifact_path"] == batch_plan_catalog_row["artifact_path"]
    assert archive_bucket_representative_row["artifact_path_relative"] == batch_plan_catalog_row[
        "artifact_path_relative"
    ]
    assert int(archive_bucket_representative_row["bucket_ready_source_item_count"]) == 2
    assert int(archive_bucket_representative_row["bucket_plan_item_count"]) == 1
    assert bool(archive_bucket_representative_row["candidate_pack_eligible"]) is False
    assert bool(archive_bucket_representative_row["replay_command_execution_authorized"]) is False
    archive_window_bucket_representative_row = bucket_representatives_frame[
        bucket_representatives_frame["bucket_type"] == "archive_window_bucket"
    ].iloc[0]
    assert archive_window_bucket_representative_row["bucket_key"] == archive_window_bucket
    assert archive_window_bucket_representative_row["artifact_path"] == batch_plan_catalog_row["artifact_path"]
    assert set(worklist_frame["candidate_pack_eligible"]) == {False}
    assert set(batch_plan_frame["candidate_pack_eligible"]) == {False}


def test_sandbox_iteration_input_replay_worklist_flags_missing_input_paths(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "agent-replay-missing-path",
                "family": "agent_replay_family",
                "source_id": "agent-replay-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-05-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="bybit",
        archive_symbol="ETH",
        archive_data_family="trade",
        archive_interval="1h",
        window_start="2024-05-01",
        window_end="2024-05-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=2,
        min_request_score=0.0,
    )
    missing_catalog_root = tmp_path / "missing_catalog_root"
    mutated_context = dict(payload["input_replay_context"])
    mutated_context["catalog_root_paths"] = [str(missing_catalog_root)]
    manifest_path = Path(str(payload["iteration_manifest_path"]))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["input_replay_context"] = mutated_context
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")
    brief_path = Path(str(payload["agent_brief_json_path"]))
    brief_payload = json.loads(brief_path.read_text(encoding="utf-8"))
    brief_payload["input_replay_context"] = mutated_context
    brief_path.write_text(json.dumps(brief_payload, indent=2, sort_keys=True), encoding="utf-8")

    index_payload = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    worklist_payload = json.loads(Path(str(index_payload["input_replay_worklist_json_path"])).read_text(encoding="utf-8"))
    worklist_frame = pd.read_parquet(Path(str(index_payload["input_replay_worklist_parquet_path"])))
    batch_plan_payload = json.loads(
        Path(str(index_payload["input_replay_batch_plan_json_path"])).read_text(encoding="utf-8")
    )
    batch_plan_frame = pd.read_parquet(Path(str(index_payload["input_replay_batch_plan_parquet_path"])))
    worklist_item = index_payload["input_replay_worklist"][0]

    assert worklist_item["input_replay_ready"] is False
    assert worklist_item["input_replay_blocker_reasons"] == ["missing_input_replay_paths"]
    assert worklist_item["input_replay_path_availability_status"] == "missing_or_invalid_inputs"
    assert worklist_item["input_replay_path_reference_count"] == 3
    assert worklist_item["input_replay_path_present_count"] == 2
    assert worklist_item["input_replay_path_missing_count"] == 1
    assert worklist_item["input_replay_path_wrong_type_count"] == 0
    assert worklist_item["input_replay_path_missing_keys"] == ["catalog_root_paths[1]"]
    assert worklist_item["input_replay_path_status_counts"] == {"missing": 1, "present": 2}
    assert index_payload["input_replay_worklist_summary"]["ready_count"] == 0
    assert index_payload["input_replay_worklist_summary"]["blocked_count"] == 1
    assert index_payload["input_replay_worklist_summary"]["path_availability_status_counts"] == {
        "missing_or_invalid_inputs": 1
    }
    assert index_payload["input_replay_worklist_summary"]["path_missing_key_counts"] == {
        "catalog_root_paths[1]": 1
    }
    assert index_payload["input_replay_worklist_summary"]["total_path_missing_count"] == 1
    assert index_payload["input_replay_worklist_summary"]["archive_venue_counts"] == {"bybit": 1}
    assert index_payload["input_replay_worklist_summary"]["archive_symbol_counts"] == {"ETH": 1}
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_counts"] == {
        "bybit|ETH|trade|1h": 1
    }
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_ready_counts"] == {}
    assert index_payload["input_replay_worklist_summary"]["archive_bucket_blocked_counts"] == {
        "bybit|ETH|trade|1h": 1
    }
    assert index_payload["input_replay_worklist_summary"]["archive_window_blocked_counts"] == {
        "bybit|ETH|trade|1h|2024-05-01|2024-05-02": 1
    }
    assert worklist_payload["items"][0]["input_replay_path_missing_keys"] == ["catalog_root_paths[1]"]
    assert json.loads(worklist_frame.iloc[0]["input_replay_path_missing_keys"]) == ["catalog_root_paths[1]"]
    assert json.loads(worklist_frame.iloc[0]["input_replay_blocker_reasons"]) == ["missing_input_replay_paths"]
    assert index_payload["input_replay_batch_plan_count"] == 0
    assert index_payload["input_replay_batch_plan_summary"]["source_worklist_item_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["ready_source_item_count"] == 0
    assert index_payload["input_replay_batch_plan_summary"]["blocked_source_item_count"] == 1
    assert index_payload["input_replay_batch_plan_summary"]["plan_item_count"] == 0
    assert index_payload["input_replay_batch_plan_summary"]["blocked_replay_blocker_reason_counts"] == {
        "missing_input_replay_paths": 1
    }
    assert batch_plan_payload["item_count"] == 0
    assert batch_plan_payload["summary"]["blocked_source_item_count"] == 1
    assert batch_plan_frame.empty
    artifact_catalog = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")
    batch_plan_catalog_row = next(
        row
        for row in artifact_catalog["artifacts"]
        if row["artifact_kind"] == "iteration_input_replay_batch_plan"
    )
    assert batch_plan_catalog_row["source_worklist_item_count"] == 1
    assert batch_plan_catalog_row["ready_source_item_count"] == 0
    assert batch_plan_catalog_row["blocked_source_item_count"] == 1
    assert batch_plan_catalog_row["suppressed_duplicate_source_item_count"] == 0
    assert batch_plan_catalog_row["plan_item_count"] == 0
    assert batch_plan_catalog_row["unique_ready_replay_context_count"] == 0
    assert batch_plan_catalog_row["ready_archive_bucket_counts"] == {}
    assert batch_plan_catalog_row["plan_archive_bucket_counts"] == {}
    assert batch_plan_catalog_row["ready_archive_window_bucket_counts"] == {}
    assert batch_plan_catalog_row["plan_archive_window_bucket_counts"] == {}
    assert batch_plan_catalog_row["descriptor_count"] == 0
    assert batch_plan_catalog_row["descriptor_only"] is True
    assert batch_plan_catalog_row["candidate_pack_eligible"] is False
    assert artifact_catalog["replay_batch_plan_summary"] == {
        "artifact_count": 1,
        "blocked_source_item_count": 1,
        "descriptor_count": 0,
        "plan_item_count": 0,
        "plan_archive_bucket_counts": {},
        "plan_archive_window_bucket_counts": {},
        "ready_archive_bucket_counts": {},
        "ready_archive_window_bucket_counts": {},
        "ready_source_item_count": 0,
        "source_worklist_item_count": 1,
        "status_counts": {"blocked_only": 1},
        "suppressed_duplicate_source_item_count": 0,
        "unique_ready_replay_context_count": 0,
    }
    assert artifact_catalog["replay_batch_plan_queue_count"] == 1
    replay_queue_item = artifact_catalog["replay_batch_plan_queue"][0]
    assert replay_queue_item["replay_batch_plan_status"] == "blocked_only"
    assert replay_queue_item["descriptor_count"] == 0
    assert replay_queue_item["blocked_source_item_count"] == 1
    assert replay_queue_item["plan_item_count"] == 0
    assert replay_queue_item["ready_archive_bucket_counts"] == {}
    assert replay_queue_item["plan_archive_bucket_counts"] == {}
    assert replay_queue_item["ready_archive_window_bucket_counts"] == {}
    assert replay_queue_item["plan_archive_window_bucket_counts"] == {}
    assert replay_queue_item["candidate_pack_eligible"] is False
    assert artifact_catalog["replay_batch_plan_archive_bucket_queue_count"] == 0
    assert artifact_catalog["replay_batch_plan_archive_window_bucket_queue_count"] == 0
    assert artifact_catalog["replay_batch_plan_archive_bucket_queue"] == []
    assert artifact_catalog["replay_batch_plan_archive_window_bucket_queue"] == []
    assert artifact_catalog["replay_batch_plan_bucket_queue_parquet_row_count"] == 0
    assert artifact_catalog["replay_batch_plan_bucket_representative_parquet_row_count"] == 0
    bucket_queue_parquet_path = Path(
        str(artifact_catalog["replay_batch_plan_bucket_queue_parquet_path"])
    )
    bucket_representatives_parquet_path = Path(
        str(artifact_catalog["replay_batch_plan_bucket_representatives_parquet_path"])
    )
    assert bucket_queue_parquet_path.exists()
    assert bucket_representatives_parquet_path.exists()
    bucket_queue_frame = pd.read_parquet(bucket_queue_parquet_path)
    bucket_representatives_frame = pd.read_parquet(bucket_representatives_parquet_path)
    assert bucket_queue_frame.empty
    assert bucket_representatives_frame.empty
    assert "bucket_type" in bucket_queue_frame.columns
    assert "bucket_type" in bucket_representatives_frame.columns
    assert set(worklist_frame["candidate_pack_eligible"]) == {False}


def test_sandbox_agent_iteration_preserves_strategy_source_summary_for_workbook_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    _write_minimal_xlsx(
        catalog_root / "multi_sheet_strategies.xlsx",
        {
            "Direct Signals": [
                ["Hypothesis", "Strategy Family", "Signal", "Direction"],
                ["iteration-workbook-long", "iteration_workbook_family", "direct_signal", "long"],
            ],
            "Range Ideas": [
                ["Packet", "Lead", "Next Check"],
                ["WPR106-304", "range reversion long iteration setup", "range reversion proxy falsification"],
            ],
            "Notes": [["Note"], ["operator note that must stay descriptor metadata"]],
        },
    )
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=12, freq="1h", tz="UTC"),
            "close": [100.0 + float(index % 4) for index in range(12)],
            "direct_signal": [1] * 12,
        }
    ).to_csv(archive_root / "market.csv", index=False)

    def _raise_missing_engine(*_args: object, **_kwargs: object) -> object:
        raise ImportError("Missing optional dependency 'openpyxl'")

    monkeypatch.setattr(pd, "ExcelFile", _raise_missing_engine)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    brief = json.loads(Path(str(payload["agent_brief_json_path"])).read_text(encoding="utf-8"))
    brief_frame = pd.read_parquet(Path(str(payload["agent_brief_parquet_path"])))
    index_payload = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    index_row = index_payload["rows"][0]
    index_frame = pd.read_parquet(Path(str(index_payload["iteration_index_parquet_path"])))

    summary = payload["strategy_source"]["strategy_source_summary"]
    assert payload["iteration_status"] == "completed"
    assert summary["workbook_source_count"] == 1
    assert summary["workbook_sheet_count"] == 3
    assert summary["workbook_included_sheet_count"] == 2
    assert summary["workbook_skipped_sheet_count"] == 1
    assert summary["workbook_strategy_count"] == 2
    assert summary["workbook_sheet_status_counts"] == {"included": 2, "skipped": 1}
    assert summary["workbook_sheet_kind_counts"] == {
        "direct_strategy_catalog": 1,
        "spreadsheet_lead_catalog": 1,
        "unsupported_sheet": 1,
    }
    assert summary["workbook_sheet_name_sample"] == ["Direct Signals", "Range Ideas", "Notes"]
    assert summary["workbook_skipped_sheet_name_sample"] == ["Notes"]
    assert brief["strategy_source_summary"] == summary
    assert json.loads(brief_frame.iloc[0]["strategy_source_summary"])["workbook_sheet_count"] == 3
    assert index_row["strategy_source_summary"] == summary
    assert index_row["strategy_workbook_source_count"] == 1
    assert index_row["strategy_workbook_sheet_count"] == 3
    assert index_row["strategy_workbook_skipped_sheet_count"] == 1
    assert index_row["strategy_workbook_skipped_sheet_name_sample"] == ["Notes"]
    assert index_payload["total_strategy_workbook_source_count"] == 1
    assert index_payload["total_strategy_workbook_sheet_count"] == 3
    assert index_payload["total_strategy_workbook_skipped_sheet_count"] == 1
    assert json.loads(index_frame.iloc[0]["strategy_source_summary"])["workbook_source_count"] == 1
    assert bool(index_frame.iloc[0]["candidate_pack_eligible"]) is False


def test_sandbox_agent_iteration_surfaces_skipped_strategy_source_samples(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    bad_catalog = catalog_root / "bad.csv"
    notes_file = catalog_root / "notes.txt"
    pd.DataFrame([{"foo": "bar"}]).to_csv(bad_catalog, index=False)
    pd.DataFrame(
        [
            {
                "hypothesis_id": "iteration-skipped-source-long",
                "family": "iteration_skipped_source_family",
                "source_id": "valid-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    notes_file.write_text("operator notes, not a strategy catalog", encoding="utf-8")
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    brief = json.loads(Path(str(payload["agent_brief_json_path"])).read_text(encoding="utf-8"))
    brief_frame = pd.read_parquet(Path(str(payload["agent_brief_parquet_path"])))
    index_payload = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    index_row = index_payload["rows"][0]
    action_plan_frame = pd.read_parquet(Path(str(index_payload["agent_action_plan_parquet_path"])))

    summary = payload["strategy_source"]["strategy_source_summary"]
    samples = summary["skipped_source_samples"]
    assert payload["iteration_status"] == "completed"
    assert payload["strategy_source"]["skipped_source_count"] == 2
    assert summary["source_status_counts"] == {"included": 1, "skipped": 2}
    assert summary["source_suffix_counts"] == {".csv": 2, ".txt": 1}
    assert summary["source_skip_reason_counts"]["unsupported_suffix"] == 1
    assert any(reason.startswith("load_error:ValueError:") for reason in summary["source_skip_reason_counts"])
    assert samples[0]["source_path"] == str(bad_catalog.resolve())
    assert samples[0]["source_suffix"] == ".csv"
    assert samples[0]["skip_reasons"][0].startswith("load_error:ValueError:")
    assert samples[1] == {
        "source_path": str(notes_file.resolve()),
        "source_suffix": ".txt",
        "skip_reasons": ["unsupported_suffix"],
    }
    assert summary["skipped_source_samples_truncated"] is False
    assert brief["strategy_source_summary"] == summary
    assert json.loads(brief_frame.iloc[0]["strategy_source_summary"])["skipped_source_samples"] == samples
    assert index_row["strategy_skipped_source_samples"] == samples
    assert index_row["strategy_skipped_source_samples_truncated"] is False
    assert index_row["recommended_action"] == "repair_strategy_catalog_sources"

    assert index_payload["action_queue_version"] == 14
    assert index_payload["action_queue_counts"]["strategy_source_repair_queue"] == 1
    assert index_payload["action_queue_counts"]["strict_validation_request_queue"] == 1
    assert index_payload["action_queue_counts"]["venue_expansion_gap_queue"] == 1
    queue_item = index_payload["action_queues"]["strategy_source_repair_queue"][0]
    assert queue_item["iteration_id"] == payload["iteration_id"]
    assert queue_item["recommended_action"] == "repair_strategy_catalog_sources"
    assert queue_item["strategy_skipped_source_samples"] == samples
    assert queue_item["recommended_actions"][0]["strategy_skipped_source_samples"] == samples
    assert [item["action"] for item in index_payload["agent_action_plan"]] == [
        "repair_strategy_catalog_sources",
        "review_descriptor_only_strict_validation_requests",
        "repair_or_add_venue_expansion_archives",
    ]
    assert index_payload["agent_action_plan"][0]["source_queues"] == ["strategy_source_repair_queue"]
    assert index_payload["agent_action_plan"][0]["strategy_skipped_source_samples"] == samples
    assert index_payload["agent_action_plan"][1]["blocked_by_prior_action"] is True
    assert index_payload["agent_action_plan"][2]["source_queues"] == ["venue_expansion_gap_queue"]
    assert index_payload["agent_action_plan"][2]["blocked_by_prior_action"] is True
    assert json.loads(action_plan_frame["strategy_skipped_source_samples"].iloc[0]) == samples
    assert set(action_plan_frame["candidate_pack_eligible"]) == {False}


def test_sandbox_agent_iteration_brief_preserves_validation_request_source_summary(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "agent-zip-long",
                "family": "agent_zip_family",
                "source_id": "agent-zip-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)

    def jsonl(rows: list[dict[str, object]]) -> str:
        return "\n".join(json.dumps(row) for row in rows)

    zip_path = archive_root / "hyperliquid_BTC_trade.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "chunks/b.jsonl",
            jsonl(
                [
                    {"time": "2024-03-01T00:01:00Z", "px": "101.0", "direct_signal": 0},
                    {"time": "2024-03-01T00:02:00Z", "px": "104.0", "direct_signal": 0},
                ]
            ),
        )
        archive.writestr(
            "chunks/a.jsonl",
            jsonl([{"time": "2024-03-01T00:00:00Z", "px": "100.0", "direct_signal": 1}]),
        )
        archive.writestr(
            "chunks/ignored.ndjson",
            jsonl([{"time": "2024-03-01T00:03:00Z", "px": "999.0", "direct_signal": 0}]),
        )

    iteration = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="hyperliquid",
        archive_symbol="BTC",
        archive_data_family="trade",
        window_start="2024-03-01",
        window_end="2024-03-01",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=1,
    )
    brief = json.loads(Path(str(iteration["agent_brief_json_path"])).read_text(encoding="utf-8"))
    request = brief["top_validation_requests"][0]

    assert iteration["deduped_validation_request_count"] == 1
    assert request["hypothesis_id"] == "agent-zip-long"
    assert request["source_routing_mode"] == "descriptor_data_path"
    assert request["source_data_path"] == str(zip_path)
    assert request["source_container_kind"] == "zip"
    assert request["source_selected_member_suffix"] == ".jsonl"
    assert request["source_selected_member_count"] == 2
    assert request["source_selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert request["source_loadable_member_count"] == 3
    assert request["source_market_source"]["available_member_suffix_counts"] == {".jsonl": 2, ".ndjson": 1}

    index = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    index_request = index["rows"][0]["top_validation_requests"][0]
    queue_request = index["action_queues"]["strict_validation_request_queue"][0]["top_validation_requests"][0]
    action_plan_request = index["agent_action_plan"][0]["top_validation_requests"][0]
    frame = pd.read_parquet(Path(str(index["iteration_index_parquet_path"])))
    parquet_requests = json.loads(frame["top_validation_requests"].iloc[0])

    assert index_request["source_container_kind"] == "zip"
    assert queue_request["source_selected_member_count"] == 2
    assert action_plan_request["source_selected_member_name_sample"] == ["chunks/a.jsonl", "chunks/b.jsonl"]
    assert parquet_requests[0]["source_market_source"]["container_kind"] == "zip"
    assert index["action_queue_counts"]["strict_validation_request_queue"] == 1
    assert index["agent_action_plan"][0]["action"] == "review_descriptor_only_strict_validation_requests"


def test_sandbox_agent_iteration_reuses_market_data_cache_across_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_path = tmp_path / "catalog.csv"
    venues_path = tmp_path / "venues.json"
    market_path = tmp_path / "market.csv"
    pd.DataFrame(
        [
            {
                "hypothesis_id": "agent-cache-step-long",
                "family": "agent_cache_step_family",
                "source_id": "agent-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_path, index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=8, freq="1h", tz="UTC"),
            "close": [100.0 + index for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(market_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-agent-cache-step",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": str(market_path),
                        "source_integrity": {"sha256": _sha256(market_path), "byte_size": market_path.stat().st_size},
                        "window": {"start": "2024-03-01", "end": "2024-03-02"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    original_read_raw_table = market_data_module._read_raw_table
    original_file_integrity = market_data_module._file_integrity
    read_count = 0
    integrity_count = 0

    def counting_read_raw_table(source_path: Path) -> pd.DataFrame:
        nonlocal read_count
        read_count += 1
        return original_read_raw_table(source_path)

    def counting_file_integrity(source_path: Path) -> dict[str, object]:
        nonlocal integrity_count
        integrity_count += 1
        return original_file_integrity(source_path)

    monkeypatch.setattr(market_data_module, "_read_raw_table", counting_read_raw_table)
    monkeypatch.setattr(market_data_module, "_file_integrity", counting_file_integrity)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        strategy_catalog_path=catalog_path,
        venue_archives_path=venues_path,
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )

    assert read_count == 1
    assert integrity_count == 1
    assert payload["iteration_status"] == "completed"
    assert payload["archive_coverage_ready_descriptor_count"] == 1
    assert payload["preflight_runnable_trial_estimate"] == 1
    assert payload["result_count"] == 1
    assert payload["candidate_pack_eligible"] is False


def test_sandbox_agent_iteration_recent_window_preset_records_resolved_window(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path, start="2025-06-19")

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_preset="recent_365d",
        window_as_of_date="2026-06-18",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    brief = json.loads(Path(str(payload["agent_brief_json_path"])).read_text(encoding="utf-8"))

    assert payload["spec"]["data_window"] == {"start": "2025-06-19", "end": "2026-06-18"}
    assert payload["window_selection"]["window_selection_mode"] == "recent"
    assert payload["window_selection"]["window_preset"] == "recent_365d"
    assert payload["window_selection"]["window_as_of_date"] == "2026-06-18"
    assert payload["window_selection"]["window_lookback_days"] == 365
    assert payload["window_selection"]["resolved_window_start"] == "2025-06-19"
    assert payload["window_selection"]["resolved_window_end"] == "2026-06-18"
    assert payload["window_selection"]["window_start_clipped_to_min_date"] is False
    assert brief["window_selection"] == payload["window_selection"]
    assert brief["candidate_pack_eligible"] is False


def test_sandbox_agent_iteration_filters_archive_roots_to_resolved_window(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "recent-window-long",
                "family": "recent_window_family",
                "source_id": "agent-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=8, freq="1h", tz="UTC"),
            "close": [90.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "old_market.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-06-17", periods=8, freq="1h", tz="UTC"),
            "close": [100.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(archive_root / "recent_market.csv", index=False)

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_preset="recent_365d",
        window_as_of_date="2026-06-18",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    build_report = json.loads(Path(str(payload["archive_source"]["build_report_json_path"])).read_text(encoding="utf-8"))
    brief = json.loads(Path(str(payload["agent_brief_json_path"])).read_text(encoding="utf-8"))
    rows = {Path(row["source_path"]).name: row for row in build_report["files"]}
    archive_summary = payload["archive_source"]["archive_source_summary"]
    samples = archive_summary["skipped_file_samples"]

    assert payload["archive_source"]["descriptor_count"] == 1
    assert payload["archive_coverage_descriptor_count"] == 1
    assert payload["result_count"] == 1
    assert archive_summary["file_status_counts"] == {"included": 1, "skipped": 1}
    assert archive_summary["file_suffix_counts"] == {".csv": 2}
    assert archive_summary["file_skip_reason_counts"] == {"outside_requested_window": 1}
    assert archive_summary["skipped_file_samples_truncated"] is False
    assert len(samples) == 1
    assert Path(samples[0]["source_path"]).name == "old_market.csv"
    assert samples[0]["source_suffix"] == ".csv"
    assert samples[0]["skip_reasons"] == ["outside_requested_window"]
    assert samples[0]["normalized_row_count"] == 8
    assert samples[0]["window_start"] == "2024-03-01"
    assert samples[0]["window_end"] == "2024-03-01"
    assert samples[0]["requested_window_start"] == "2025-06-19"
    assert samples[0]["requested_window_end"] == "2026-06-18"
    assert brief["archive_source_summary"] == archive_summary
    assert build_report["requested_window_filter_applied"] is True
    assert build_report["requested_window_start"] == "2025-06-19"
    assert build_report["requested_window_end"] == "2026-06-18"
    assert rows["recent_market.csv"]["status"] == "included"
    assert rows["old_market.csv"]["status"] == "skipped"
    assert rows["old_market.csv"]["skip_reasons"] == ["outside_requested_window"]
    assert rows["old_market.csv"]["candidate_pack_eligible"] is False

    index_payload = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    index_row = index_payload["rows"][0]
    assert index_payload["action_queue_version"] == 14
    assert index_row["archive_file_status_counts"] == {"included": 1, "skipped": 1}
    assert index_row["archive_file_skip_reason_counts"] == {"outside_requested_window": 1}
    assert index_row["archive_skipped_file_samples"] == samples
    assert index_row["archive_skipped_file_samples_truncated"] is False
    queue_item = index_payload["action_queues"]["strict_validation_request_queue"][0]
    assert queue_item["archive_file_skip_reason_counts"] == {"outside_requested_window": 1}
    assert queue_item["archive_skipped_file_samples"] == samples
    assert index_payload["agent_action_plan"][0]["archive_skipped_file_samples"] == samples


def test_sandbox_agent_iteration_applies_resolved_window_to_existing_archive_coverage(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    market_path = tmp_path / "okx_old_market.csv"
    venues_path = tmp_path / "venues.json"
    catalog_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "existing-manifest-recent-window",
                "family": "recent_window_family",
                "source_id": "agent-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=8, freq="1h", tz="UTC"),
            "close": [90.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(market_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-existing-old-btcusdt-1h",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": market_path.name,
                        "window": {"start": "2024-03-01", "end": "2024-03-01"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        venue_archives_path=venues_path,
        window_preset="recent_365d",
        window_as_of_date="2026-06-18",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    coverage = json.loads(Path(str(payload["archive_coverage_json_path"])).read_text(encoding="utf-8"))
    coverage_row = coverage["coverage_rows"][0]

    assert payload["iteration_status"] == "blocked_by_preflight"
    assert payload["archive_source"]["mode"] == "existing_venue_archive_manifest"
    assert payload["archive_coverage_requested_window_row_count"] == 0
    assert payload["archive_coverage_blocked_descriptor_count"] == 1
    assert payload["archive_coverage_status_counts"] == {"blocked": 1}
    assert coverage["requested_window_filter_applied"] is True
    assert coverage["requested_window_start"] == "2025-06-19"
    assert coverage["requested_window_end"] == "2026-06-18"
    assert coverage_row["requested_window_row_count"] == 0
    assert coverage_row["blocker_reason_counts"] == {"no_rows_in_requested_window": 1}
    assert coverage_row["candidate_pack_eligible"] is False


def test_sandbox_agent_iteration_recent_window_preset_clips_to_2024_floor(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path, start="2024-01-01")

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="bybit",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_preset="recent_365d",
        window_as_of_date="2024-03-01",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )

    assert payload["spec"]["data_window"] == {"start": "2024-01-01", "end": "2024-03-01"}
    assert payload["window_selection"]["raw_window_start"] == "2023-03-03"
    assert payload["window_selection"]["window_start_clipped_to_min_date"] is True
    assert payload["window_selection"]["min_sandbox_date"] == "2024-01-01"
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False


def test_sandbox_agent_iteration_rejects_recent_window_override_for_spec_path(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "explicit-spec-window",
                "data_window": {"start": "2024-03-01", "end": "2024-03-02"},
                "holding_periods": [1],
                "round_trip_cost_bps": 0.0,
                "min_trades": 1,
                "max_evidence_requests": 1,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="window_preset cannot override a spec_path"):
        run_sandbox_agent_iteration(
            output_dir=tmp_path / "iterations",
            spec_path=spec_path,
            catalog_roots=[catalog_root],
            archive_roots=[archive_root],
            archive_venue="okx",
            archive_symbol="BTCUSDT",
            archive_data_family="kline",
            archive_interval="1h",
            window_preset="recent_365d",
            window_as_of_date="2026-06-18",
        )


def test_sandbox_agent_iteration_reuse_rejects_tampered_run_child_artifact(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path)
    kwargs = {
        "output_dir": tmp_path / "iterations",
        "catalog_roots": [catalog_root],
        "archive_roots": [archive_root],
        "archive_venue": "okx",
        "archive_symbol": "BTCUSDT",
        "archive_data_family": "kline",
        "archive_interval": "1h",
        "window_start": "2024-03-01",
        "window_end": "2024-03-02",
        "holding_periods": (1,),
        "round_trip_cost_bps": 0.0,
        "min_trades": 1,
        "max_evidence_requests": 3,
    }
    payload = run_sandbox_agent_iteration(**kwargs)
    run_manifest = json.loads(Path(str(payload["run_manifest_path"])).read_text(encoding="utf-8"))
    evidence_path = Path(str(run_manifest["artifacts"]["evidence_requests_json_path"]))
    original_text = evidence_path.read_text(encoding="utf-8")
    evidence_path.write_text(f"{original_text}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="sandbox_iteration_cached_run_source failed sandbox artifact integrity"):
        run_sandbox_agent_iteration(**kwargs)


def test_sandbox_agent_iteration_reuse_rejects_missing_cached_bundle(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path, hypothesis_id="agent-cache-missing-bundle")
    kwargs = {
        "output_dir": tmp_path / "iterations",
        "catalog_roots": [catalog_root],
        "archive_roots": [archive_root],
        "archive_venue": "bybit",
        "archive_symbol": "ETHUSDT",
        "archive_data_family": "kline",
        "archive_interval": "1h",
        "window_start": "2024-03-01",
        "window_end": "2024-03-02",
        "holding_periods": (1,),
        "round_trip_cost_bps": 0.0,
        "min_trades": 1,
        "max_evidence_requests": 3,
    }
    payload = run_sandbox_agent_iteration(**kwargs)
    Path(str(payload["strict_validation_request_bundle_json_path"])).unlink()

    with pytest.raises(FileNotFoundError, match="strict_validation_request_bundle_json_path"):
        run_sandbox_agent_iteration(**kwargs)


def test_sandbox_agent_iteration_reuse_rejects_missing_cached_archive_coverage(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path, hypothesis_id="agent-cache-missing-coverage")
    kwargs = {
        "output_dir": tmp_path / "iterations",
        "catalog_roots": [catalog_root],
        "archive_roots": [archive_root],
        "archive_venue": "okx",
        "archive_symbol": "BTCUSDT",
        "archive_data_family": "kline",
        "archive_interval": "1h",
        "window_start": "2024-03-01",
        "window_end": "2024-03-02",
        "holding_periods": (1,),
        "round_trip_cost_bps": 0.0,
        "min_trades": 1,
        "max_evidence_requests": 3,
    }
    payload = run_sandbox_agent_iteration(**kwargs)
    Path(str(payload["archive_coverage_parquet_path"])).unlink()

    with pytest.raises(FileNotFoundError, match="archive_coverage_parquet_path"):
        run_sandbox_agent_iteration(**kwargs)


def test_sandbox_agent_iteration_reuse_rejects_missing_cached_agent_brief(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path, hypothesis_id="agent-cache-missing-brief")
    kwargs = {
        "output_dir": tmp_path / "iterations",
        "catalog_roots": [catalog_root],
        "archive_roots": [archive_root],
        "archive_venue": "okx",
        "archive_symbol": "BTCUSDT",
        "archive_data_family": "kline",
        "archive_interval": "1h",
        "window_start": "2024-03-01",
        "window_end": "2024-03-02",
        "holding_periods": (1,),
        "round_trip_cost_bps": 0.0,
        "min_trades": 1,
        "max_evidence_requests": 3,
    }
    payload = run_sandbox_agent_iteration(**kwargs)
    Path(str(payload["agent_brief_parquet_path"])).unlink()

    with pytest.raises(FileNotFoundError, match="agent_brief_parquet_path"):
        run_sandbox_agent_iteration(**kwargs)


def test_sandbox_agent_iteration_reuse_rejects_promotable_cached_agent_brief(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path, hypothesis_id="agent-cache-brief-boundary")
    kwargs = {
        "output_dir": tmp_path / "iterations",
        "catalog_roots": [catalog_root],
        "archive_roots": [archive_root],
        "archive_venue": "hyperliquid",
        "archive_symbol": "BTCUSDT",
        "archive_data_family": "kline",
        "archive_interval": "1h",
        "window_start": "2024-03-01",
        "window_end": "2024-03-02",
        "holding_periods": (1,),
        "round_trip_cost_bps": 0.0,
        "min_trades": 1,
        "max_evidence_requests": 3,
    }
    payload = run_sandbox_agent_iteration(**kwargs)
    brief_path = Path(str(payload["agent_brief_json_path"]))
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["promotion_ready"] = True
    brief_path.write_text(json.dumps(brief, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="sandbox_cached_iteration_artifact:agent_brief_json_path"):
        run_sandbox_agent_iteration(**kwargs)


def test_sandbox_agent_iteration_reuse_rejects_promotable_cached_archive_coverage(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path, hypothesis_id="agent-cache-coverage-boundary")
    kwargs = {
        "output_dir": tmp_path / "iterations",
        "catalog_roots": [catalog_root],
        "archive_roots": [archive_root],
        "archive_venue": "bybit",
        "archive_symbol": "ETHUSDT",
        "archive_data_family": "kline",
        "archive_interval": "1h",
        "window_start": "2024-03-01",
        "window_end": "2024-03-02",
        "holding_periods": (1,),
        "round_trip_cost_bps": 0.0,
        "min_trades": 1,
        "max_evidence_requests": 3,
    }
    payload = run_sandbox_agent_iteration(**kwargs)
    coverage_path = Path(str(payload["archive_coverage_json_path"]))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage["promotion_ready"] = True
    coverage_path.write_text(json.dumps(coverage, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="sandbox_cached_iteration_artifact:archive_coverage_json_path"):
        run_sandbox_agent_iteration(**kwargs)


def test_sandbox_agent_iteration_reuse_rejects_promotable_cached_json(tmp_path: Path) -> None:
    catalog_root, archive_root = _write_agent_iteration_inputs(tmp_path, hypothesis_id="agent-cache-boundary")
    kwargs = {
        "output_dir": tmp_path / "iterations",
        "catalog_roots": [catalog_root],
        "archive_roots": [archive_root],
        "archive_venue": "hyperliquid",
        "archive_symbol": "BTCUSDT",
        "archive_data_family": "kline",
        "archive_interval": "1h",
        "window_start": "2024-03-01",
        "window_end": "2024-03-02",
        "holding_periods": (1,),
        "round_trip_cost_bps": 0.0,
        "min_trades": 1,
        "max_evidence_requests": 3,
    }
    payload = run_sandbox_agent_iteration(**kwargs)
    analysis_path = Path(str(payload["analysis_report_path"]))
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    analysis["promotion_ready"] = True
    analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="sandbox_cached_iteration_artifact:analysis_report_path"):
        run_sandbox_agent_iteration(**kwargs)


def test_sandbox_agent_iteration_uses_existing_materialized_inputs(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "existing-direct-long",
                "family": "existing_direct_family",
                "source_id": "existing-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-04-01", periods=7, freq="1h", tz="UTC"),
            "close": [200.0, 201.0, 202.0, 203.0, 204.0, 205.0, 206.0],
            "direct_signal": [1] * 7,
        }
    ).to_csv(archive_root / "market.csv", index=False)
    strategy_payload = materialize_sandbox_strategy_catalog(catalog_root, output_dir=tmp_path / "inputs" / "catalogs")
    archive_payload = build_sandbox_archive_manifest(
        archive_root,
        output_dir=tmp_path / "inputs" / "archives",
        venue="bybit",
        symbol="ETHUSDT",
        data_family="kline",
        interval="1h",
    )

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        strategy_catalog_path=strategy_payload["strategy_catalog_json_path"],
        venue_archives_path=archive_payload["venue_archive_manifest_path"],
        window_start="2024-04-01",
        window_end="2024-04-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=2,
    )

    assert payload["strategy_source"]["mode"] == "existing_strategy_catalog"
    assert payload["archive_source"]["mode"] == "existing_venue_archive_manifest"
    assert payload["strategy_source"]["strategy_count"] == 1
    assert payload["archive_source"]["descriptor_count"] == 1
    assert payload["result_count"] == 1
    assert payload["evidence_request_count"] == 1
    assert payload["candidate_pack_paths"] == []


def test_sandbox_suite_loader_rejects_unsafe_identifiers(tmp_path: Path) -> None:
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "bad/suite",
                "cases": [
                    {
                        "case_id": "case-ok",
                        "spec": "missing-spec.json",
                        "strategy_catalog": "missing-catalog.csv",
                        "venue_archives": "missing-venues.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="suite_id must be a safe path component"):
        load_sandbox_suite_spec(suite_path)


def test_sandbox_suite_loader_rejects_live_boundary_flags(tmp_path: Path) -> None:
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "bad-live-suite",
                "live_signal": True,
                "cases": [
                    {
                        "case_id": "case-ok",
                        "spec": "missing-spec.json",
                        "strategy_catalog": "missing-catalog.csv",
                        "venue_archives": "missing-venues.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="live_signal_must_not_be_true"):
        load_sandbox_suite_spec(suite_path)


def test_cli_command_runs_sandbox_with_local_archive_descriptors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    spec_path = tmp_path / "spec.json"
    catalog_path = tmp_path / "catalog.csv"
    venues_path = tmp_path / "venues.json"
    market_path = tmp_path / "market.csv"

    spec_path.write_text(
        json.dumps(
            {
                "run_id": "cli-sandbox-smoke",
                "data_window": {"start": "2024-01-01", "end": "2024-01-31"},
                "holding_periods": [1, 2],
                "round_trip_cost_bps": 1.0,
                "min_trades": 2,
                "max_evidence_requests": 2,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "hypothesis_id": "cli-long",
                "family": "transparent_motif_fallback",
                "signal_column": "fallback_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-cli-btcusdt",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "window": {"start": "2024-01-01", "end": "2024-01-31"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=12, freq="12h", tz="UTC"),
            "close": [100 + index for index in range(12)],
            "fallback_signal": [1] * 12,
        }
    ).to_csv(market_path, index=False)

    payload = main._run_rapid_strategy_sandbox_command(
        argparse.Namespace(
            command="run-rapid-strategy-sandbox",
            spec=str(spec_path),
            strategy_catalog=str(catalog_path),
            venue_archives=str(venues_path),
            market_data=str(market_path),
            output_dir="sandbox_cli",
            min_request_score=0.0,
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert Path(str(payload["manifest_path"])).exists()
    assert Path(str(payload["summary_parquet_path"])).exists()
    assert Path(str(payload["output_dir"])).resolve().relative_to(research_root.resolve())


def test_cli_command_runs_sandbox_with_multiple_descriptor_data_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    spec_path = tmp_path / "spec.json"
    catalog_path = tmp_path / "catalog.csv"
    venues_path = tmp_path / "venues.json"
    okx_path = tmp_path / "okx_market.csv"
    bybit_path = tmp_path / "bybit_market.csv"
    timestamps = pd.date_range("2024-01-01", periods=8, freq="1D", tz="UTC")

    spec_path.write_text(
        json.dumps(
            {
                "run_id": "cli-multi-venue-sandbox",
                "data_window": {"start": "2024-01-01", "end": "2024-01-08"},
                "holding_periods": [1],
                "round_trip_cost_bps": 0.0,
                "min_trades": 1,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [{"hypothesis_id": "cli-long", "family": "routing", "signal_column": "signal", "side": "long"}]
    ).to_csv(catalog_path, index=False)
    pd.DataFrame({"timestamp": timestamps, "close": [100 + index for index in range(8)], "signal": [1] * 8}).to_csv(
        okx_path,
        index=False,
    )
    pd.DataFrame({"timestamp": timestamps, "close": [100 - index for index in range(8)], "signal": [1] * 8}).to_csv(
        bybit_path,
        index=False,
    )
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-cli-btcusdt",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "data_path": "okx_market.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-08"},
                    },
                    {
                        "descriptor_id": "bybit-cli-btcusdt",
                        "venue": "bybit",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "data_path": "bybit_market.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-08"},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = main._run_rapid_strategy_sandbox_command(
        argparse.Namespace(
            command="run-rapid-strategy-sandbox",
            spec=str(spec_path),
            strategy_catalog=str(catalog_path),
            venue_archives=str(venues_path),
            market_data=None,
            output_dir="sandbox_cli_multi",
            min_request_score=0.0,
        )
    )

    manifest = json.loads(Path(str(payload["manifest_path"])).read_text(encoding="utf-8"))

    assert payload["result_count"] == 2
    assert payload["candidate_pack_eligible"] is False
    assert Path(str(payload["output_dir"])).resolve().relative_to(research_root.resolve())
    assert {source["descriptor_id"] for source in manifest["market_sources"]} == {
        "okx-cli-btcusdt",
        "bybit-cli-btcusdt",
    }


def test_cli_command_audits_archive_descriptors_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    venues_path = tmp_path / "venues.json"
    market_path = tmp_path / "okx_market.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=6, freq="12h", tz="UTC"),
            "close": [100 + index for index in range(6)],
            "high": [101 + index for index in range(6)],
            "low": [99 + index for index in range(6)],
        }
    ).to_csv(market_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-cli-audit-btcusdt",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "data_path": "okx_market.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-03"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = main._run_audit_rapid_strategy_sandbox_archives_command(
        argparse.Namespace(
            command="audit-rapid-strategy-sandbox-archives",
            venue_archives=str(venues_path),
            market_data=None,
            output_dir="archive_audits",
            requested_window_start="2024-01-02",
            requested_window_end="2024-01-02",
        )
    )

    audit_dir = Path(str(payload["audit_dir"]))
    manifest = json.loads(Path(str(payload["audit_json_path"])).read_text(encoding="utf-8"))

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["requested_window_filter_applied"] is True
    assert payload["requested_window_row_count"] == 2
    assert payload["ready_count"] == 1
    assert Path(str(payload["audit_parquet_path"])).exists()
    assert audit_dir.resolve().relative_to(research_root.resolve())
    assert manifest["descriptors"][0]["descriptor_id"] == "okx-cli-audit-btcusdt"
    assert manifest["descriptors"][0]["requested_window_row_count"] == 2


def test_cli_command_summarizes_archive_coverage_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    venues_path = tmp_path / "venues.json"
    market_path = tmp_path / "okx_market.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC"),
            "close": [100 + index for index in range(5)],
            "high": [101 + index for index in range(5)],
            "low": [99 + index for index in range(5)],
        }
    ).to_csv(market_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-cli-coverage-btcusdt",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": "okx_market.csv",
                        "window": {"start": "2024-01-01", "end": "2024-01-01"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = main._run_summarize_rapid_strategy_sandbox_archive_coverage_command(
        argparse.Namespace(
            command="summarize-rapid-strategy-sandbox-archive-coverage",
            venue_archives=str(venues_path),
            market_data=None,
            output_dir="archive_coverage",
            requested_window_start="2024-01-01",
            requested_window_end="2024-01-01",
        )
    )
    coverage_dir = Path(str(payload["coverage_dir"]))
    frame = pd.read_parquet(Path(str(payload["coverage_parquet_path"])))
    catalog = index_sandbox_artifacts(research_root, output_dir=research_root / "catalog")

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["requested_window_filter_applied"] is True
    assert payload["requested_window_row_count"] == 5
    assert payload["ready_descriptor_count"] == 1
    assert payload["blocked_descriptor_count"] == 0
    assert payload["coverage_bucket_count"] == 1
    assert payload["coverage_rows"][0]["coverage_key"] == "okx|BTCUSDT|kline|1h"
    assert payload["coverage_rows"][0]["requested_window_row_count"] == 5
    assert coverage_dir.resolve().relative_to(research_root.resolve())
    assert Path(str(payload["coverage_json_path"])).exists()
    assert Path(str(payload["coverage_parquet_path"])).exists()
    assert set(frame["coverage_key"]) == {"okx|BTCUSDT|kline|1h"}
    assert catalog["artifact_kind_counts"]["archive_coverage_matrix"] == 1


def test_cli_command_builds_archive_manifest_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    archive_root = tmp_path / "raw_drop"
    archive_root.mkdir()
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-04-01", periods=5, freq="1h", tz="UTC"),
            "close": [300.0, 301.0, 302.0, 303.0, 304.0],
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = main._run_build_rapid_strategy_sandbox_archive_manifest_command(
        argparse.Namespace(
            command="build-rapid-strategy-sandbox-archive-manifest",
            archive_root=[str(archive_root)],
            output_dir="archive_manifests",
            venue="okx",
            symbol="BTCUSDT",
            data_family="kline",
            interval="1h",
            max_files=100,
        )
    )
    manifest_path = Path(str(payload["venue_archive_manifest_path"]))
    descriptors = load_venue_archive_descriptors(manifest_path)

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_count"] == 1
    assert manifest_path.resolve().relative_to(research_root.resolve())
    assert Path(str(payload["build_report_parquet_path"])).exists()
    assert descriptors[0].venue == "okx"
    assert descriptors[0].symbol == "BTCUSDT"


def test_cli_command_builds_strategy_catalog_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    pd.DataFrame(
        [
            {
                "hypothesis_id": "cli-direct-long",
                "family": "cli_direct_family",
                "source_id": "cli-local",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)

    payload = main._run_build_rapid_strategy_sandbox_strategy_catalog_command(
        argparse.Namespace(
            command="build-rapid-strategy-sandbox-strategy-catalog",
            catalog_root=[str(catalog_root)],
            output_dir="strategy_catalogs",
            max_files=100,
        )
    )
    catalog_path = Path(str(payload["strategy_catalog_json_path"]))
    rows = load_strategy_catalog(catalog_path)

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["strategy_count"] == 1
    assert catalog_path.resolve().relative_to(research_root.resolve())
    assert Path(str(payload["build_report_json_path"])).resolve().relative_to(research_root.resolve())
    assert Path(str(payload["build_report_parquet_path"])).exists()
    assert rows[0].hypothesis_id == "cli-direct-long"


def test_cli_command_runs_sandbox_agent_iteration_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    catalog_root.mkdir()
    archive_root.mkdir()
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    pd.DataFrame(
        [
            {
                "hypothesis_id": "cli-agent-direct-long",
                "family": "cli_agent_direct_family",
                "source_id": "cli-agent-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-05-01", periods=7, freq="1h", tz="UTC"),
            "close": [300.0, 301.0, 302.0, 303.0, 304.0, 305.0, 306.0],
            "direct_signal": [1] * 7,
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = main._run_rapid_strategy_sandbox_iteration_command(
        argparse.Namespace(
            command="run-rapid-strategy-sandbox-iteration",
            spec=None,
            strategy_catalog=None,
            catalog_root=[str(catalog_root)],
            venue_archives=None,
            archive_root=[str(archive_root)],
            output_dir="agent_iterations",
            run_id=None,
            window_start="2024-05-01",
            window_end="2024-05-02",
            window_preset="recent_365d",
            window_as_of_date="2024-05-02",
            window_lookback_days=365,
            holding_periods="1",
            round_trip_cost_bps=0.0,
            min_trades=1,
            max_evidence_requests=3,
            rank_top_n=10,
            min_request_score=0.0,
            catalog_max_files=100,
            archive_max_files=100,
            archive_venue="hyperliquid",
            archive_symbol="BTCUSDT",
            archive_data_family="kline",
            archive_interval="1h",
            leaderboard_max_runs=100,
            leaderboard_top_n=10,
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["iteration_status"] == "completed"
    assert payload["spec"]["data_window"] == {"start": "2024-01-01", "end": "2024-05-02"}
    assert payload["window_selection"]["window_preset"] == "recent_365d"
    assert payload["window_selection"]["window_start_clipped_to_min_date"] is True
    assert payload["preflight_runnable_trial_estimate"] == 1
    assert payload["preflight_blocked_trial_estimate"] == 0
    assert payload["result_count"] == 1
    assert payload["evidence_request_count"] == 1
    assert Path(str(payload["agent_brief_json_path"])).exists()
    assert Path(str(payload["agent_brief_parquet_path"])).exists()
    assert Path(str(payload["iteration_manifest_path"])).resolve().relative_to(research_root.resolve())
    assert Path(str(payload["archive_coverage_json_path"])).exists()
    assert Path(str(payload["archive_coverage_parquet_path"])).exists()
    assert Path(str(payload["preflight_json_path"])).exists()
    assert Path(str(payload["preflight_parquet_path"])).exists()
    assert Path(str(payload["run_manifest_path"])).exists()
    assert Path(str(payload["strict_validation_request_bundle_json_path"])).exists()
    assert Path(str(payload["global_leaderboard_json_path"])).exists()
    manifest = json.loads(Path(str(payload["iteration_manifest_path"])).read_text(encoding="utf-8"))
    steps = {step["step_id"]: step for step in manifest["steps"]}

    assert steps["compatibility_preflight"]["status"] == "runnable"
    assert steps["archive_coverage_matrix"]["status"] == "completed"
    assert steps["archive_sweep"]["status"] == "completed"
    assert steps["agent_brief"]["status"] == "completed"


def test_sandbox_agent_iteration_skips_downstream_when_preflight_blocks_all_trials(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    archive_root = tmp_path / "archives"
    output_root = tmp_path / "iterations"
    catalog_root.mkdir()
    archive_root.mkdir()
    pd.DataFrame(
        [
            {
                "hypothesis_id": "blocked-direct-long",
                "family": "blocked_direct_family",
                "source_id": "agent-catalog",
                "signal_column": "missing_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-06-01", periods=8, freq="1h", tz="UTC"),
            "close": [400.0 + index for index in range(8)],
        }
    ).to_csv(archive_root / "market.csv", index=False)

    payload = run_sandbox_agent_iteration(
        output_dir=output_root,
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        window_start="2024-06-01",
        window_end="2024-06-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
        rank_top_n=10,
        catalog_max_files=100,
        archive_max_files=100,
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        leaderboard_max_runs=100,
        leaderboard_top_n=10,
    )
    manifest = json.loads(Path(str(payload["iteration_manifest_path"])).read_text(encoding="utf-8"))
    steps = {step["step_id"]: step for step in manifest["steps"]}

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["iteration_status"] == "blocked_by_preflight"
    assert payload["agent_brief_next_action"] == "repair_preflight_blockers"
    assert payload["preflight_runnable_trial_estimate"] == 0
    assert payload["preflight_blocked_trial_estimate"] == 1
    assert payload["result_count"] == 0
    assert payload["evidence_request_count"] == 0
    assert payload["archive_coverage_descriptor_count"] == 1
    assert payload["archive_coverage_ready_descriptor_count"] == 1
    assert Path(str(payload["agent_brief_json_path"])).exists()
    assert Path(str(payload["agent_brief_parquet_path"])).exists()
    assert Path(str(payload["archive_coverage_json_path"])).exists()
    assert Path(str(payload["archive_coverage_parquet_path"])).exists()
    assert payload["run_manifest_path"] is None
    assert payload["strict_validation_request_bundle_json_path"] is None
    assert Path(str(payload["preflight_json_path"])).exists()
    assert Path(str(payload["preflight_parquet_path"])).exists()
    assert "missing_signal_column:missing_signal" in payload["preflight_blocker_reason_counts"]
    samples = payload["preflight_blocker_samples"]
    assert payload["preflight_blocker_samples_truncated"] is False
    assert len(samples) == 1
    sample = samples[0]
    assert sample["venue"] == "okx"
    assert sample["symbol"] == "BTCUSDT"
    assert sample["hypothesis_id"] == "blocked-direct-long"
    assert sample["signal_column"] == "missing_signal"
    assert sample["blocker_reason_counts"] == {"missing_signal_column:missing_signal": 1}
    assert sample["blocked_trial_estimate"] == 1
    assert sample["runnable_trial_estimate"] == 0
    assert sample["active_signal_count"] == 0
    assert sample["market_row_count"] == 8
    assert Path(sample["source_path"]).name == "market.csv"
    assert "close" in sample["columns_sample"]
    brief = json.loads(Path(str(payload["agent_brief_json_path"])).read_text(encoding="utf-8"))
    assert brief["next_action"] == "repair_preflight_blockers"
    assert "preflight_blocked_all_trials" in brief["reason_codes"]
    assert brief["top_preflight_blockers"][0]["reason"] == "missing_signal_column:missing_signal"
    assert brief["preflight_blocker_samples"] == samples
    assert brief["preflight_blocker_samples_truncated"] is False
    assert steps["archive_coverage_matrix"]["status"] == "completed"
    assert steps["compatibility_preflight"]["status"] == "blocked"
    assert steps["archive_sweep"]["status"] == "skipped_preflight_blocked"
    assert steps["strict_validation_request_bundle"]["status"] == "skipped_preflight_blocked"
    assert steps["agent_brief"]["status"] == "completed"


def test_sandbox_iteration_index_summarizes_agent_iterations_and_briefs(tmp_path: Path) -> None:
    completed_input_root = tmp_path / "completed_inputs"
    completed_input_root.mkdir()
    completed_catalog, completed_archive = _write_agent_iteration_inputs(
        completed_input_root,
        hypothesis_id="index-direct-long",
        family="index_direct_family",
    )
    output_root = tmp_path / "iterations"
    completed = run_sandbox_agent_iteration(
        output_dir=output_root,
        catalog_roots=[completed_catalog],
        archive_roots=[completed_archive],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )

    blocked_root = tmp_path / "blocked_inputs"
    blocked_catalog = blocked_root / "catalogs"
    blocked_archive = blocked_root / "archives"
    blocked_catalog.mkdir(parents=True)
    blocked_archive.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "hypothesis_id": "index-blocked-long",
                "family": "index_blocked_family",
                "source_id": "index-blocked-catalog",
                "signal_column": "missing_signal",
                "side": "long",
            }
        ]
    ).to_csv(blocked_catalog / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=8, freq="1h", tz="UTC"),
            "close": [200.0 + index for index in range(8)],
        }
    ).to_csv(blocked_archive / "market.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC"),
            "close": [190.0 + index for index in range(4)],
        }
    ).to_csv(blocked_archive / "old_market.csv", index=False)
    blocked = run_sandbox_agent_iteration(
        output_dir=output_root,
        catalog_roots=[blocked_catalog],
        archive_roots=[blocked_archive],
        archive_venue="bybit",
        archive_symbol="ETHUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    blocked_brief_path = Path(str(blocked["agent_brief_json_path"]))
    blocked_brief = json.loads(blocked_brief_path.read_text(encoding="utf-8"))
    assert blocked_brief["preflight_blocker_reason_counts"] == {"missing_signal_column:missing_signal": 1}
    blocked_samples = blocked_brief["preflight_blocker_samples"]
    assert blocked_brief["preflight_blocker_samples_truncated"] is False
    assert len(blocked_samples) == 1
    assert blocked_samples[0]["hypothesis_id"] == "index-blocked-long"
    assert blocked_samples[0]["signal_column"] == "missing_signal"
    assert blocked_samples[0]["blocker_reason_counts"] == {"missing_signal_column:missing_signal": 1}
    assert blocked_samples[0]["blocked_trial_estimate"] == 1
    assert blocked_samples[0]["venue"] == "bybit"
    assert blocked_samples[0]["symbol"] == "ETHUSDT"
    assert Path(blocked_samples[0]["source_path"]).name == "market.csv"
    blocked_brief["top_preflight_blockers"] = [{"reason": "display_only_preflight_blocker", "count": 99}]
    blocked_brief_path.write_text(json.dumps(blocked_brief, indent=2, sort_keys=True), encoding="utf-8")

    payload = build_sandbox_iteration_index(output_root, output_dir=tmp_path / "iteration_index")
    frame = pd.read_parquet(Path(str(payload["iteration_index_parquet_path"])))
    action_plan_frame = pd.read_parquet(Path(str(payload["agent_action_plan_parquet_path"])))
    rows = {row["iteration_id"]: row for row in payload["rows"]}
    catalog = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "catalog")
    catalog_action_plan_frame = pd.read_parquet(
        Path(str(catalog["iteration_agent_action_plan_parquet_path"]))
    )
    catalog_venue_gap_worklist_frame = pd.read_parquet(
        Path(str(catalog["iteration_venue_expansion_gap_worklist_parquet_path"]))
    )
    catalog_action_bucket_frame = pd.read_parquet(
        Path(str(catalog["iteration_agent_action_plan_bucket_queue_parquet_path"]))
    )
    catalog_action_bucket_representatives_frame = pd.read_parquet(
        Path(
            str(
                catalog[
                    "iteration_agent_action_plan_bucket_representatives_parquet_path"
                ]
            )
        )
    )
    catalog_sidecar_index_frame = pd.read_parquet(
        Path(str(catalog["catalog_sidecar_index_parquet_path"]))
    )
    catalog_iteration_row = next(
        row for row in catalog["artifacts"] if row["artifact_kind"] == "iteration_index"
    )
    no_write_payload = build_sandbox_iteration_index(output_root, output_dir=tmp_path / "no_write_index", write_report=False)

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["iteration_count"] == 2
    assert payload["iteration_status_counts"] == {"blocked_by_preflight": 1, "completed": 1}
    assert payload["next_action_counts"]["review_descriptor_only_strict_validation_requests"] == 1
    assert payload["next_action_counts"]["repair_preflight_blockers"] == 1
    assert payload["recommended_action_counts"] == {
        "repair_or_add_venue_expansion_archives": 2,
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints": 1,
        "review_descriptor_only_strict_validation_requests": 1,
    }
    assert payload["brief_status_counts"] == {"present": 2}
    assert payload["artifact_availability_status_counts"] == {"all_present": 2}
    assert payload["total_deduped_validation_request_count"] == 1
    assert payload["total_strategy_skipped_source_count"] == 0
    assert payload["total_archive_skipped_count"] == 1
    assert payload["total_artifact_reference_count"] > 0
    assert payload["total_artifact_present_count"] == payload["total_artifact_reference_count"]
    assert payload["total_artifact_missing_count"] == 0
    assert payload["total_archive_coverage_requested_window_row_count"] == 16
    assert payload["total_venue_expansion_gap_row_count"] == 6
    assert payload["total_venue_expansion_actionable_gap_count"] == 4
    assert payload["total_venue_expansion_missing_target_count"] == 4
    assert payload["action_queue_version"] == 14
    assert payload["action_queue_counts"]["strict_validation_request_queue"] == 1
    assert payload["action_queue_counts"]["preflight_repair_queue"] == 1
    assert payload["action_queue_counts"]["archive_window_repair_queue"] == 0
    assert payload["action_queue_counts"]["venue_expansion_gap_queue"] == 2
    assert payload["action_queue_counts"]["strategy_source_repair_queue"] == 0
    assert payload["action_queue_counts"]["missing_brief_queue"] == 0
    assert payload["action_queue_counts"]["artifact_repair_queue"] == 0
    assert payload["action_queue_truncated_counts"] == {
        "strict_validation_request_queue": 0,
        "preflight_repair_queue": 0,
        "archive_window_repair_queue": 0,
        "venue_expansion_gap_queue": 0,
        "strategy_source_repair_queue": 0,
        "missing_brief_queue": 0,
        "artifact_repair_queue": 0,
        "rejection_review_queue": 0,
    }
    assert payload["agent_action_plan_version"] == 1
    assert payload["agent_action_plan_limit"] == 50
    assert payload["agent_action_plan_count"] == 4
    assert payload["agent_action_plan_truncated_count"] == 0
    assert Path(str(payload["agent_action_plan_parquet_path"])).exists()
    assert no_write_payload["agent_action_plan_parquet_path"] is None
    assert payload["input_replay_worklist_version"] == 1
    assert payload["input_replay_worklist_count"] == 2
    assert payload["input_replay_context_missing_count"] == 0
    assert Path(str(payload["input_replay_worklist_json_path"])).exists()
    assert Path(str(payload["input_replay_worklist_parquet_path"])).exists()
    assert no_write_payload["input_replay_worklist_json_path"] is None
    assert no_write_payload["input_replay_worklist_parquet_path"] is None
    assert payload["input_replay_batch_plan_version"] == 1
    assert payload["input_replay_batch_plan_count"] == 2
    assert Path(str(payload["input_replay_batch_plan_json_path"])).exists()
    assert Path(str(payload["input_replay_batch_plan_parquet_path"])).exists()
    assert no_write_payload["input_replay_batch_plan_json_path"] is None
    assert no_write_payload["input_replay_batch_plan_parquet_path"] is None
    assert [item["action"] for item in payload["agent_action_plan"][:2]] == [
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints",
        "review_descriptor_only_strict_validation_requests",
    ]
    assert [item["action"] for item in payload["agent_action_plan"][2:]] == [
        "repair_or_add_venue_expansion_archives",
        "repair_or_add_venue_expansion_archives",
    ]
    assert payload["agent_action_plan"][0]["source_queues"] == ["preflight_repair_queue"]
    assert payload["agent_action_plan"][0]["blocked_by_prior_action"] is False
    assert payload["agent_action_plan"][1]["source_queues"] == ["strict_validation_request_queue"]
    assert payload["agent_action_plan"][2]["source_queues"] == ["venue_expansion_gap_queue"]
    assert payload["agent_action_plan"][2]["blocked_by_prior_action"] is True
    action_plan_summary = payload["agent_action_plan_summary"]
    assert action_plan_summary["matched_action_item_count"] == 4
    assert action_plan_summary["visible_item_count"] == 4
    assert action_plan_summary["truncated_count"] == 0
    assert action_plan_summary["action_counts"] == payload["recommended_action_counts"]
    assert action_plan_summary["source_queue_counts"] == {
        "preflight_repair_queue": 1,
        "strict_validation_request_queue": 1,
        "venue_expansion_gap_queue": 2,
    }
    assert action_plan_frame.shape[0] == payload["agent_action_plan_count"]
    assert list(action_plan_frame["action"])[:2] == [
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints",
        "review_descriptor_only_strict_validation_requests",
    ]
    assert list(action_plan_frame["action"])[2:] == [
        "repair_or_add_venue_expansion_archives",
        "repair_or_add_venue_expansion_archives",
    ]
    assert set(action_plan_frame["candidate_pack_eligible"]) == {False}
    assert set(action_plan_frame["promotion_ready"]) == {False}
    assert json.loads(action_plan_frame["source_queues"].iloc[0]) == ["preflight_repair_queue"]
    assert json.loads(action_plan_frame["source_queues"].iloc[1]) == ["strict_validation_request_queue"]
    assert json.loads(action_plan_frame["source_queues"].iloc[2]) == ["venue_expansion_gap_queue"]
    assert rows[completed["iteration_id"]]["next_action"] == "review_descriptor_only_strict_validation_requests"
    assert rows[completed["iteration_id"]]["recommended_action"] == "review_descriptor_only_strict_validation_requests"
    assert rows[completed["iteration_id"]]["recommended_actions"][0]["reason_codes"] == [
        "deduped_validation_requests"
    ]
    assert rows[completed["iteration_id"]]["deduped_validation_request_count"] == 1
    assert rows[completed["iteration_id"]]["venue_expansion_actionable_gap_count"] == 2
    assert rows[completed["iteration_id"]]["recommended_actions"][1]["action"] == "repair_or_add_venue_expansion_archives"
    assert rows[completed["iteration_id"]]["brief_status"] == "present"
    assert rows[completed["iteration_id"]]["artifact_availability_status"] == "all_present"
    assert rows[completed["iteration_id"]]["artifact_missing_count"] == 0
    assert rows[completed["iteration_id"]]["artifact_missing_keys"] == []
    assert rows[completed["iteration_id"]]["strategy_source_mode"] == "materialized_strategy_catalog"
    assert rows[completed["iteration_id"]]["strategy_included_source_count"] == 1
    assert rows[completed["iteration_id"]]["strategy_skipped_source_count"] == 0
    assert rows[completed["iteration_id"]]["archive_source_mode"] == "built_venue_archive_manifest"
    assert rows[completed["iteration_id"]]["archive_file_count"] == 1
    assert rows[completed["iteration_id"]]["archive_skipped_count"] == 0
    assert rows[completed["iteration_id"]]["strategy_catalog_json_path"] == completed["strategy_source"]["strategy_catalog_json_path"]
    assert rows[completed["iteration_id"]]["strategy_build_report_json_path"] == completed["strategy_source"]["build_report_json_path"]
    assert rows[completed["iteration_id"]]["venue_archive_manifest_path"] == completed["archive_source"]["venue_archive_manifest_path"]
    assert rows[completed["iteration_id"]]["archive_build_report_json_path"] == completed["archive_source"]["build_report_json_path"]
    assert rows[blocked["iteration_id"]]["next_action"] == "repair_preflight_blockers"
    assert (
        rows[blocked["iteration_id"]]["recommended_action"]
        == "repair_strategy_catalog_signal_columns_or_materialize_blueprints"
    )
    assert rows[blocked["iteration_id"]]["recommended_actions"][0]["reason_codes"] == [
        "missing_signal_column:missing_signal"
    ]
    assert rows[blocked["iteration_id"]]["archive_coverage_requested_window_row_count"] == 8
    assert rows[blocked["iteration_id"]]["archive_file_count"] == 2
    assert rows[blocked["iteration_id"]]["archive_skipped_count"] == 1
    assert rows[blocked["iteration_id"]]["preflight_blocked_trial_estimate"] == 1
    assert rows[blocked["iteration_id"]]["preflight_blocker_reason_counts"] == {
        "missing_signal_column:missing_signal": 1
    }
    assert rows[blocked["iteration_id"]]["preflight_blocker_samples"] == blocked_samples
    assert rows[blocked["iteration_id"]]["preflight_blocker_samples_truncated"] is False
    assert rows[blocked["iteration_id"]]["recommended_actions"][0]["preflight_blocker_samples"] == blocked_samples
    assert rows[blocked["iteration_id"]]["venue_expansion_actionable_gap_count"] == 2
    assert rows[blocked["iteration_id"]]["recommended_actions"][1]["action"] == "repair_or_add_venue_expansion_archives"
    assert rows[blocked["iteration_id"]]["top_preflight_blockers"][0]["reason"] == "display_only_preflight_blocker"
    request_item = payload["action_queues"]["strict_validation_request_queue"][0]
    preflight_item = payload["action_queues"]["preflight_repair_queue"][0]
    assert request_item["iteration_id"] == completed["iteration_id"]
    assert request_item["next_action"] == "review_descriptor_only_strict_validation_requests"
    assert request_item["recommended_action"] == "review_descriptor_only_strict_validation_requests"
    assert request_item["recommended_actions"][0]["count"] == 1
    assert request_item["counts"]["deduped_validation_request_count"] == 1
    assert request_item["counts"]["archive_coverage_requested_window_row_count"] == 8
    assert request_item["counts"]["strategy_included_source_count"] == 1
    assert request_item["counts"]["archive_file_count"] == 1
    assert request_item["counts"]["artifact_missing_count"] == 0
    assert request_item["artifact_availability_status"] == "all_present"
    assert request_item["artifact_missing_keys"] == []
    assert request_item["strategy_catalog_json_path"] == completed["strategy_source"]["strategy_catalog_json_path"]
    assert request_item["venue_archive_manifest_path"] == completed["archive_source"]["venue_archive_manifest_path"]
    assert request_item["top_validation_requests"][0]["hypothesis_id"] == "index-direct-long"
    assert request_item["counts"]["venue_expansion_actionable_gap_count"] == 2
    assert request_item["recommended_actions"][1]["action"] == "repair_or_add_venue_expansion_archives"
    assert request_item["candidate_pack_eligible"] is False
    assert preflight_item["iteration_id"] == blocked["iteration_id"]
    assert preflight_item["next_action"] == "repair_preflight_blockers"
    assert (
        preflight_item["recommended_action"]
        == "repair_strategy_catalog_signal_columns_or_materialize_blueprints"
    )
    assert preflight_item["recommended_actions"][0]["count"] == 1
    assert preflight_item["counts"]["preflight_blocked_trial_estimate"] == 1
    assert preflight_item["counts"]["archive_coverage_requested_window_row_count"] == 8
    assert preflight_item["counts"]["archive_file_count"] == 2
    assert preflight_item["counts"]["archive_skipped_count"] == 1
    assert preflight_item["archive_build_report_json_path"] == blocked["archive_source"]["build_report_json_path"]
    assert preflight_item["coverage_status_counts"] == {"ready": 1}
    assert preflight_item["preflight_status_counts"] == {"blocked": 1}
    assert preflight_item["preflight_blocker_reason_counts"] == {"missing_signal_column:missing_signal": 1}
    assert preflight_item["preflight_blocker_samples"] == blocked_samples
    assert preflight_item["preflight_blocker_samples_truncated"] is False
    assert preflight_item["recommended_actions"][0]["preflight_blocker_samples"] == blocked_samples
    assert preflight_item["counts"]["venue_expansion_actionable_gap_count"] == 2
    assert preflight_item["recommended_actions"][1]["action"] == "repair_or_add_venue_expansion_archives"
    assert preflight_item["top_preflight_blockers"][0]["reason"] == "display_only_preflight_blocker"
    assert preflight_item["candidate_pack_eligible"] is False
    preflight_summary = payload["action_queue_summaries"]["preflight_repair_queue"]
    assert preflight_summary["matched_iteration_count"] == 1
    assert preflight_summary["visible_item_count"] == 1
    assert preflight_summary["truncated_count"] == 0
    assert preflight_summary["coverage_status_counts"] == {"ready": 1}
    assert preflight_summary["preflight_status_counts"] == {"blocked": 1}
    assert preflight_summary["preflight_blocker_reason_counts"] == {"missing_signal_column:missing_signal": 1}
    assert preflight_summary["recommended_action_counts"] == {
        "repair_or_add_venue_expansion_archives": 1,
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints": 1
    }
    assert preflight_summary["counts"]["preflight_blocked_trial_estimate"] == 1
    assert preflight_summary["counts"]["archive_file_count"] == 2
    assert preflight_summary["counts"]["archive_skipped_count"] == 1
    assert payload["agent_action_plan"][0]["preflight_blocker_samples"] == blocked_samples
    assert payload["agent_action_plan"][0]["preflight_blocker_samples_truncated"] is False
    request_summary = payload["action_queue_summaries"]["strict_validation_request_queue"]
    assert request_summary["matched_iteration_count"] == 1
    assert request_summary["artifact_availability_status_counts"] == {"all_present": 1}
    assert request_summary["recommended_action_counts"] == {
        "repair_or_add_venue_expansion_archives": 1,
        "review_descriptor_only_strict_validation_requests": 1
    }
    assert request_summary["counts"]["deduped_validation_request_count"] == 1
    assert request_summary["counts"]["strategy_included_source_count"] == 1
    assert request_summary["counts"]["archive_skipped_count"] == 0
    assert request_summary["counts"]["artifact_missing_count"] == 0
    assert set(frame["candidate_pack_eligible"]) == {False}
    assert catalog["artifact_kind_counts"]["iteration_index"] == 1
    assert catalog["artifact_kind_counts"]["iteration_input_replay_worklist"] == 1
    assert catalog["artifact_kind_counts"]["iteration_input_replay_batch_plan"] == 1
    assert Path(str(catalog["iteration_agent_action_plan_parquet_path"])).exists()
    assert Path(
        str(catalog["iteration_venue_expansion_gap_worklist_parquet_path"])
    ).exists()
    assert Path(
        str(catalog["iteration_agent_action_plan_bucket_queue_parquet_path"])
    ).exists()
    assert Path(
        str(catalog["iteration_agent_action_plan_bucket_representatives_parquet_path"])
    ).exists()
    assert catalog["iteration_agent_action_plan_parquet_row_count"] == payload[
        "agent_action_plan_count"
    ]
    assert catalog["iteration_agent_action_plan_summary"] == {
        "artifact_count": 1,
        "action_item_count": payload["agent_action_plan_count"],
        "primary_action_count": 2,
        "blocked_by_prior_action_count": 2,
        "action_counts": payload["agent_action_plan_summary"]["action_counts"],
        "source_queue_counts": payload["agent_action_plan_summary"][
            "source_queue_counts"
        ],
        "iteration_status_counts": payload["agent_action_plan_summary"][
            "iteration_status_counts"
        ],
    }
    assert catalog["iteration_venue_expansion_gap_worklist_parquet_row_count"] == 4
    assert catalog["iteration_venue_expansion_gap_worklist_source_artifact_count"] == 1
    assert catalog["iteration_venue_expansion_gap_worklist_source_iteration_count"] == 2
    assert catalog["iteration_venue_expansion_gap_worklist_target_venue_counts"] == {
        "hyperliquid": 2,
        "bybit": 1,
        "okx": 1,
    }
    assert catalog["iteration_venue_expansion_gap_worklist_target_action_counts"] == {
        "add_archive_descriptor_for_target_venue": 4,
    }
    assert catalog["iteration_venue_expansion_gap_worklist_target_status_counts"] == {
        "missing_archive_descriptor": 4,
    }
    assert catalog["iteration_venue_expansion_gap_worklist_source_queue_counts"] == {
        "venue_expansion_gap_queue": 4,
    }
    assert catalog["iteration_venue_expansion_gap_worklist_summary"] == {
        "blocked_by_prior_action_count": 4,
        "source_action_counts": {"repair_or_add_venue_expansion_archives": 4},
        "source_artifact_count": 1,
        "source_iteration_count": 2,
        "source_queue_counts": {"venue_expansion_gap_queue": 4},
        "target_action_counts": {"add_archive_descriptor_for_target_venue": 4},
        "target_status_counts": {"missing_archive_descriptor": 4},
        "target_venue_counts": {
            "hyperliquid": 2,
            "bybit": 1,
            "okx": 1,
        },
        "worklist_row_count": 4,
    }
    assert catalog_iteration_row["iteration_count"] == payload["iteration_count"]
    assert catalog_iteration_row["iteration_agent_action_plan_count"] == payload[
        "agent_action_plan_count"
    ]
    assert catalog_iteration_row["iteration_agent_action_plan_visible_count"] == len(
        payload["agent_action_plan"]
    )
    assert catalog_iteration_row["iteration_agent_action_counts"] == payload[
        "agent_action_plan_summary"
    ]["action_counts"]
    assert catalog_iteration_row["iteration_agent_source_queue_counts"] == payload[
        "agent_action_plan_summary"
    ]["source_queue_counts"]
    assert len(catalog_action_plan_frame) == payload["agent_action_plan_count"]
    assert list(catalog_action_plan_frame["action"]) == list(action_plan_frame["action"])
    assert list(catalog_action_plan_frame["iteration_id"]) == list(
        action_plan_frame["iteration_id"]
    )
    assert json.loads(catalog_action_plan_frame["source_queues"].iloc[0]) == [
        "preflight_repair_queue"
    ]
    assert json.loads(catalog_action_plan_frame["source_queues"].iloc[1]) == [
        "strict_validation_request_queue"
    ]
    assert json.loads(catalog_action_plan_frame["source_queues"].iloc[2]) == [
        "venue_expansion_gap_queue"
    ]
    assert set(catalog_action_plan_frame["descriptor_only"]) == {True}
    assert set(catalog_action_plan_frame["candidate_pack_eligible"]) == {False}
    assert len(catalog_venue_gap_worklist_frame) == 4
    assert list(catalog_venue_gap_worklist_frame["worklist_row_rank"]) == [1, 2, 3, 4]
    assert set(catalog_venue_gap_worklist_frame["action"]) == {
        "repair_or_add_venue_expansion_archives"
    }
    assert set(catalog_venue_gap_worklist_frame["source_queues"].map(json.loads).map(tuple)) == {
        ("venue_expansion_gap_queue",)
    }
    assert set(catalog_venue_gap_worklist_frame["target_status"]) == {
        "missing_archive_descriptor"
    }
    assert set(catalog_venue_gap_worklist_frame["target_action"]) == {
        "add_archive_descriptor_for_target_venue"
    }
    assert set(catalog_venue_gap_worklist_frame["target_venue"]) == {
        "bybit",
        "hyperliquid",
        "okx",
    }
    assert set(catalog_venue_gap_worklist_frame["market_symbol_key"]) == {"BTC", "ETH"}
    assert set(catalog_venue_gap_worklist_frame["data_family"]) == {"kline"}
    assert set(catalog_venue_gap_worklist_frame["interval"]) == {"1h"}
    assert set(catalog_venue_gap_worklist_frame["descriptor_only"]) == {True}
    assert set(catalog_venue_gap_worklist_frame["strict_validation_executed"]) == {
        False
    }
    assert set(catalog_venue_gap_worklist_frame["candidate_pack_written"]) == {False}
    assert set(catalog_venue_gap_worklist_frame["candidate_pack_eligible"]) == {False}
    assert (
        catalog_venue_gap_worklist_frame.groupby("iteration_id")["target_venue"]
        .apply(lambda values: sorted(str(value) for value in values))
        .to_dict()
    ) == {
        completed["iteration_id"]: ["bybit", "hyperliquid"],
        blocked["iteration_id"]: ["hyperliquid", "okx"],
    }
    venue_request_bundle = export_sandbox_venue_expansion_request_bundle(
        catalog["catalog_json_path"],
        output_dir=tmp_path / "venue_expansion_requests",
    )
    venue_request_frame = pd.read_parquet(
        Path(str(venue_request_bundle["bundle_parquet_path"]))
    )
    catalog_after_venue_bundle = index_sandbox_artifacts(
        tmp_path,
        output_dir=tmp_path / "catalog_after_venue_bundle",
    )
    venue_bundle_catalog_row = next(
        row
        for row in catalog_after_venue_bundle["artifacts"]
        if row["artifact_kind"] == "venue_expansion_request_bundle"
    )
    assert venue_request_bundle["research_only"] is True
    assert venue_request_bundle["promotion_ready"] is False
    assert venue_request_bundle["candidate_pack_eligible"] is False
    assert venue_request_bundle["descriptor_only"] is True
    assert venue_request_bundle["pre_2024_data_allowed"] is False
    assert venue_request_bundle["provider_download_authorized"] is False
    assert venue_request_bundle["archive_manifest_write_authorized"] is False
    assert venue_request_bundle["source_archive_mutation_authorized"] is False
    assert venue_request_bundle["strict_validation_executed"] is False
    assert venue_request_bundle["candidate_pack_written"] is False
    assert venue_request_bundle["request_count"] == 4
    assert venue_request_bundle["deduped_request_count"] == 4
    assert venue_request_bundle["descriptor_count"] == 4
    assert venue_request_bundle["duplicates_removed"] == 0
    assert venue_request_bundle["target_venue_counts"] == {
        "bybit": 1,
        "hyperliquid": 2,
        "okx": 1,
    }
    assert venue_request_bundle["target_action_counts"] == {
        "add_archive_descriptor_for_target_venue": 4,
    }
    assert venue_request_bundle["target_status_counts"] == {
        "missing_archive_descriptor": 4,
    }
    assert Path(str(venue_request_bundle["bundle_json_path"])).exists()
    assert Path(str(venue_request_bundle["bundle_parquet_path"])).exists()
    assert len(venue_request_frame) == 4
    assert set(venue_request_frame["target_venue"]) == {"bybit", "hyperliquid", "okx"}
    assert set(venue_request_frame["market_symbol_key"]) == {"BTC", "ETH"}
    assert set(venue_request_frame["data_family"]) == {"kline"}
    assert set(venue_request_frame["interval"]) == {"1h"}
    assert set(venue_request_frame["source_worklist_row_count"]) == {1}
    assert set(venue_request_frame["descriptor_only"]) == {True}
    assert set(venue_request_frame["provider_download_authorized"]) == {False}
    assert set(venue_request_frame["archive_manifest_write_authorized"]) == {False}
    assert set(venue_request_frame["source_archive_mutation_authorized"]) == {False}
    assert set(venue_request_frame["strict_validation_executed"]) == {False}
    assert set(venue_request_frame["candidate_pack_written"]) == {False}
    assert json.loads(venue_request_frame["source_queues"].iloc[0]) == [
        "venue_expansion_gap_queue"
    ]
    assert catalog_after_venue_bundle["artifact_kind_counts"][
        "venue_expansion_request_bundle"
    ] == 1
    assert venue_bundle_catalog_row["descriptor_count"] == 4
    assert venue_bundle_catalog_row["deduped_request_count"] == 4
    assert venue_bundle_catalog_row["duplicates_removed"] == 0
    assert venue_bundle_catalog_row["strict_validation_executed"] is False
    assert venue_bundle_catalog_row["candidate_pack_written"] is False
    assert catalog["iteration_agent_action_plan_bucket_queue_limit"] == 50
    assert catalog["iteration_agent_action_plan_bucket_representative_limit"] == 5
    assert catalog["iteration_agent_action_plan_bucket_queue_count"] == 6
    assert catalog["iteration_agent_action_plan_bucket_queue_parquet_row_count"] == len(
        catalog_action_bucket_frame
    )
    assert len(catalog_action_bucket_frame) == 6
    assert catalog[
        "iteration_agent_action_plan_bucket_representative_parquet_row_count"
    ] == len(catalog_action_bucket_representatives_frame)
    assert len(catalog_action_bucket_representatives_frame) == 8
    bucket_counts = {
        (str(row["bucket_type"]), str(row["bucket_key"])): int(
            row["action_item_count"]
        )
        for row in catalog_action_bucket_frame.to_dict("records")
    }
    assert bucket_counts == {
        (
            "action",
            "repair_strategy_catalog_signal_columns_or_materialize_blueprints",
        ): 1,
        ("action", "repair_or_add_venue_expansion_archives"): 2,
        ("action", "review_descriptor_only_strict_validation_requests"): 1,
        ("source_queue", "preflight_repair_queue"): 1,
        ("source_queue", "venue_expansion_gap_queue"): 2,
        ("source_queue", "strict_validation_request_queue"): 1,
    }
    assert set(catalog_action_bucket_frame["descriptor_only"]) == {True}
    assert set(catalog_action_bucket_frame["candidate_pack_eligible"]) == {False}
    assert set(catalog_action_bucket_representatives_frame["descriptor_only"]) == {
        True
    }
    assert set(catalog_action_bucket_representatives_frame["candidate_pack_eligible"]) == {
        False
    }
    action_bucket_row = catalog_action_bucket_frame[
        catalog_action_bucket_frame["bucket_key"]
        == "review_descriptor_only_strict_validation_requests"
    ].iloc[0]
    assert int(action_bucket_row["total_deduped_validation_request_count"]) == 1
    assert json.loads(action_bucket_row["representative_iteration_ids"]) == [
        completed["iteration_id"]
    ]
    representative_row = catalog_action_bucket_representatives_frame[
        catalog_action_bucket_representatives_frame["bucket_key"]
        == "review_descriptor_only_strict_validation_requests"
    ].iloc[0]
    assert representative_row["iteration_id"] == completed["iteration_id"]
    assert (
        representative_row["representative_action"]
        == "review_descriptor_only_strict_validation_requests"
    )
    assert int(representative_row["deduped_validation_request_count"]) == 1
    assert json.loads(representative_row["source_queues"]) == [
        "strict_validation_request_queue"
    ]
    catalog_sidecar_row_counts = {
        str(row["sidecar_name"]): int(row["row_count"])
        for row in catalog_sidecar_index_frame.to_dict("records")
    }
    assert catalog_sidecar_row_counts["iteration_agent_action_plan"] == len(
        catalog_action_plan_frame
    )
    assert catalog_sidecar_row_counts[
        "iteration_venue_expansion_gap_worklist"
    ] == len(catalog_venue_gap_worklist_frame)
    assert catalog_sidecar_row_counts["iteration_agent_action_plan_bucket_queue"] == len(
        catalog_action_bucket_frame
    )
    assert catalog_sidecar_row_counts[
        "iteration_agent_action_plan_bucket_representatives"
    ] == len(catalog_action_bucket_representatives_frame)


def test_sandbox_iteration_action_queue_rollups_cover_truncated_matches() -> None:
    from tradingbotsuite.research_sandbox.iteration_index import (
        _build_action_queues,
        _build_agent_action_plan,
    )

    rows = []
    for index, blocked_count in enumerate((1, 2, 3), start=1):
        source_status_counts = {"included": 1}
        source_skip_reason_counts = {}
        archive_file_status_counts = {"included": 1}
        archive_file_skip_reason_counts = {}
        if index > 1:
            source_status_counts["skipped"] = index - 1
            source_skip_reason_counts["load_error:missing_required_columns"] = index - 1
            archive_file_status_counts["skipped"] = index - 1
            archive_file_skip_reason_counts["outside_requested_window"] = index - 1
        source_samples = [
            {
                "source_path": f"/tmp/rollup-blocked-{index}/bad-source-{sample_index}.csv",
                "source_suffix": ".csv",
                "skip_reasons": ["load_error:missing_required_columns"],
            }
            for sample_index in range(1, index)
        ]
        archive_samples = [
            {
                "source_path": f"/tmp/rollup-blocked-{index}/old-market-{sample_index}.csv",
                "source_suffix": ".csv",
                "source_sha256": f"archive-sha-{index}-{sample_index}",
                "source_byte_size": 100 + sample_index,
                "skip_reasons": ["outside_requested_window"],
                "normalized_row_count": 8,
                "window_start": "2024-03-01",
                "window_end": "2024-03-01",
                "requested_window_start": "2025-06-19",
                "requested_window_end": "2026-06-18",
            }
            for sample_index in range(1, index)
        ]
        rows.append(
            {
                "iteration_id": f"rollup-blocked-{index}",
                "run_id": f"rollup-run-{index}",
                "iteration_status": "blocked_by_preflight",
                "next_action": "repair_preflight_blockers",
                "reason_codes": ["preflight_blocked_all_trials"],
                "brief_status": "present",
                "iteration_manifest_path": f"/tmp/rollup-blocked-{index}/sandbox_iteration_manifest.json",
                "agent_brief_json_path": f"/tmp/rollup-blocked-{index}/sandbox_iteration_agent_brief.json",
                "strategy_source_mode": "materialized_strategy_catalog",
                "strategy_catalog_json_path": f"/tmp/rollup-blocked-{index}/strategy_catalog.json",
                "strategy_build_report_json_path": f"/tmp/rollup-blocked-{index}/strategy_catalog_build_report.json",
                "strategy_included_source_count": 1,
                "strategy_skipped_source_count": index - 1,
                "strategy_source_status_counts": source_status_counts,
                "strategy_source_suffix_counts": {".csv": index},
                "strategy_source_skip_reason_counts": source_skip_reason_counts,
                "strategy_skipped_source_samples": source_samples,
                "strategy_skipped_source_samples_truncated": False,
                "archive_source_mode": "built_venue_archive_manifest",
                "venue_archive_manifest_path": f"/tmp/rollup-blocked-{index}/venue_archives.json",
                "archive_build_report_json_path": f"/tmp/rollup-blocked-{index}/archive_manifest_build_report.json",
                "strategy_count": 1,
                "descriptor_count": 1,
                "archive_file_count": index,
                "archive_skipped_count": index - 1,
                "archive_file_status_counts": archive_file_status_counts,
                "archive_file_suffix_counts": {".csv": index},
                "archive_file_skip_reason_counts": archive_file_skip_reason_counts,
                "archive_skipped_file_samples": archive_samples,
                "archive_skipped_file_samples_truncated": False,
                "archive_coverage_ready_descriptor_count": 1,
                "archive_coverage_blocked_descriptor_count": 0,
                "archive_coverage_requested_window_row_count": 8,
                "preflight_trial_estimate": blocked_count,
                "preflight_runnable_trial_estimate": 0,
                "preflight_blocked_trial_estimate": blocked_count,
                "result_count": 0,
                "screened_count": 0,
                "rejected_count": 0,
                "blocked_count": 0,
                "evidence_request_count": 0,
                "deduped_validation_request_count": 0,
                "leaderboard_hypothesis_count": 0,
                "coverage_status_counts": {"ready": 1},
                "archive_coverage_blocker_reason_counts": {},
                "preflight_status_counts": {"blocked": 1},
                "preflight_blocker_reason_counts": {"missing_signal_column:signal": blocked_count},
                "top_archive_blockers": [],
                "top_preflight_blockers": [{"reason": "missing_signal_column:signal", "count": blocked_count}],
                "top_validation_requests": [],
                "artifact_paths": {},
                "artifact_availability_status": "all_present",
                "artifact_reference_count": index,
                "artifact_present_count": index,
                "artifact_missing_count": 0,
                "artifact_missing_keys": [],
                "strict_validation_executed": False,
                "candidate_pack_written": False,
                "candidate_pack_paths": [],
            }
        )

    queues, counts, truncated_counts, summaries = _build_action_queues(rows, limit=1)
    preflight_queue = queues["preflight_repair_queue"]
    preflight_summary = summaries["preflight_repair_queue"]
    strategy_source_queue = queues["strategy_source_repair_queue"]
    strategy_source_summary = summaries["strategy_source_repair_queue"]

    assert counts["preflight_repair_queue"] == 3
    assert len(preflight_queue) == 1
    assert truncated_counts["preflight_repair_queue"] == 2
    assert counts["strategy_source_repair_queue"] == 2
    assert len(strategy_source_queue) == 1
    assert truncated_counts["strategy_source_repair_queue"] == 1
    assert strategy_source_queue[0]["iteration_id"] == "rollup-blocked-3"
    assert strategy_source_queue[0]["recommended_action"] == "repair_strategy_catalog_sources"
    assert strategy_source_queue[0]["recommended_actions"][0]["reason_codes"] == [
        "load_error:missing_required_columns"
    ]
    assert strategy_source_queue[0]["strategy_source_skip_reason_counts"] == {
        "load_error:missing_required_columns": 2
    }
    assert strategy_source_queue[0]["strategy_skipped_source_samples"] == [
        {
            "source_path": "/tmp/rollup-blocked-3/bad-source-1.csv",
            "source_suffix": ".csv",
            "skip_reasons": ["load_error:missing_required_columns"],
        },
        {
            "source_path": "/tmp/rollup-blocked-3/bad-source-2.csv",
            "source_suffix": ".csv",
            "skip_reasons": ["load_error:missing_required_columns"],
        },
    ]
    assert strategy_source_queue[0]["strategy_skipped_source_samples_truncated"] is False
    assert strategy_source_queue[0]["counts"]["strategy_skipped_source_count"] == 2
    assert strategy_source_queue[0]["strategy_build_report_json_path"] == (
        "/tmp/rollup-blocked-3/strategy_catalog_build_report.json"
    )
    assert strategy_source_summary["matched_iteration_count"] == 2
    assert strategy_source_summary["visible_item_count"] == 1
    assert strategy_source_summary["truncated_count"] == 1
    assert strategy_source_summary["recommended_action_counts"] == {
        "repair_strategy_catalog_sources": 2,
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints": 2,
    }
    assert strategy_source_summary["strategy_source_status_counts"] == {"included": 2, "skipped": 3}
    assert strategy_source_summary["strategy_source_skip_reason_counts"] == {
        "load_error:missing_required_columns": 3
    }
    assert strategy_source_summary["counts"]["strategy_skipped_source_count"] == 3
    assert preflight_queue[0]["iteration_id"] == "rollup-blocked-3"
    assert preflight_queue[0]["recommended_action"] == "repair_strategy_catalog_sources"
    assert preflight_queue[0]["recommended_actions"][1]["action"] == (
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints"
    )
    assert preflight_queue[0]["counts"]["strategy_skipped_source_count"] == 2
    assert preflight_queue[0]["counts"]["archive_file_count"] == 3
    assert preflight_queue[0]["counts"]["archive_skipped_count"] == 2
    assert preflight_queue[0]["archive_file_status_counts"] == {"included": 1, "skipped": 2}
    assert preflight_queue[0]["archive_file_skip_reason_counts"] == {"outside_requested_window": 2}
    assert preflight_queue[0]["archive_skipped_file_samples"][0]["source_path"] == (
        "/tmp/rollup-blocked-3/old-market-1.csv"
    )
    assert preflight_queue[0]["archive_skipped_file_samples_truncated"] is False
    assert preflight_queue[0]["strategy_catalog_json_path"] == "/tmp/rollup-blocked-3/strategy_catalog.json"
    assert preflight_queue[0]["venue_archive_manifest_path"] == "/tmp/rollup-blocked-3/venue_archives.json"
    assert preflight_queue[0]["coverage_status_counts"] == {"ready": 1}
    assert preflight_queue[0]["preflight_status_counts"] == {"blocked": 1}
    assert preflight_summary["matched_iteration_count"] == 3
    assert preflight_summary["visible_item_count"] == 1
    assert preflight_summary["truncated_count"] == 2
    assert preflight_summary["iteration_status_counts"] == {"blocked_by_preflight": 3}
    assert preflight_summary["next_action_counts"] == {"repair_preflight_blockers": 3}
    assert preflight_summary["recommended_action_counts"] == {
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints": 3,
        "repair_strategy_catalog_sources": 2,
    }
    assert preflight_summary["artifact_availability_status_counts"] == {"all_present": 3}
    assert preflight_summary["artifact_missing_key_counts"] == {}
    assert preflight_summary["strategy_source_skip_reason_counts"] == {
        "load_error:missing_required_columns": 3
    }
    assert preflight_summary["archive_file_status_counts"] == {"included": 3, "skipped": 3}
    assert preflight_summary["archive_file_skip_reason_counts"] == {"outside_requested_window": 3}
    assert preflight_summary["coverage_status_counts"] == {"ready": 3}
    assert preflight_summary["preflight_status_counts"] == {"blocked": 3}
    assert preflight_summary["preflight_blocker_reason_counts"] == {"missing_signal_column:signal": 6}
    assert preflight_summary["counts"]["strategy_included_source_count"] == 3
    assert preflight_summary["counts"]["strategy_skipped_source_count"] == 3
    assert preflight_summary["counts"]["archive_file_count"] == 6
    assert preflight_summary["counts"]["archive_skipped_count"] == 3
    assert preflight_summary["counts"]["artifact_reference_count"] == 6
    assert preflight_summary["counts"]["artifact_present_count"] == 6
    assert preflight_summary["counts"]["artifact_missing_count"] == 0
    assert preflight_summary["counts"]["preflight_blocked_trial_estimate"] == 6
    assert preflight_summary["counts"]["archive_coverage_requested_window_row_count"] == 24
    assert preflight_summary["counts"]["deduped_validation_request_count"] == 0
    assert preflight_queue[0]["candidate_pack_eligible"] is False
    agent_plan, plan_count, plan_truncated_count, plan_summary = _build_agent_action_plan(rows, limit=1)
    assert plan_count == 5
    assert len(agent_plan) == 1
    assert plan_truncated_count == 4
    assert agent_plan[0]["iteration_id"] == "rollup-blocked-3"
    assert agent_plan[0]["action"] == "repair_strategy_catalog_sources"
    assert agent_plan[0]["source_queues"] == ["strategy_source_repair_queue"]
    assert agent_plan[0]["strategy_source_skip_reason_counts"] == {
        "load_error:missing_required_columns": 2
    }
    assert agent_plan[0]["strategy_skipped_source_samples"][0]["source_path"] == (
        "/tmp/rollup-blocked-3/bad-source-1.csv"
    )
    assert agent_plan[0]["strategy_skipped_source_samples_truncated"] is False
    assert agent_plan[0]["archive_file_skip_reason_counts"] == {"outside_requested_window": 2}
    assert agent_plan[0]["archive_skipped_file_samples"][0]["source_path"] == (
        "/tmp/rollup-blocked-3/old-market-1.csv"
    )
    assert agent_plan[0]["archive_skipped_file_samples_truncated"] is False
    assert plan_summary["matched_action_item_count"] == 5
    assert plan_summary["visible_item_count"] == 1
    assert plan_summary["truncated_count"] == 4
    assert plan_summary["action_counts"] == {
        "repair_strategy_catalog_signal_columns_or_materialize_blueprints": 3,
        "repair_strategy_catalog_sources": 2,
    }
    assert plan_summary["source_queue_counts"] == {
        "preflight_repair_queue": 3,
        "strategy_source_repair_queue": 2,
    }


def test_sandbox_iteration_index_queues_archive_window_repairs(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalogs"
    catalog_root.mkdir()
    market_path = tmp_path / "okx_old_market.csv"
    venues_path = tmp_path / "venues.json"
    pd.DataFrame(
        [
            {
                "hypothesis_id": "index-archive-window",
                "family": "index_archive_window_family",
                "source_id": "index-catalog",
                "signal_column": "direct_signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_root / "direct.csv", index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=8, freq="1h", tz="UTC"),
            "close": [150.0 + float(index) for index in range(8)],
            "direct_signal": [1] * 8,
        }
    ).to_csv(market_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "okx-index-old-btcusdt-1h",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "interval": "1h",
                        "data_path": market_path.name,
                        "window": {"start": "2024-03-01", "end": "2024-03-01"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    iteration = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        venue_archives_path=venues_path,
        window_preset="recent_365d",
        window_as_of_date="2026-06-18",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    manifest_path = Path(str(iteration["iteration_manifest_path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["archive_coverage_blocker_reason_counts"] == {"no_rows_in_requested_window": 1}
    samples = manifest["archive_coverage_blocker_samples"]
    assert manifest["archive_coverage_blocker_samples_truncated"] is False
    assert len(samples) == 1
    sample = samples[0]
    assert sample["coverage_key"] == "okx|BTCUSDT|kline|1h"
    assert sample["blocked_descriptor_ids"] == ["okx-index-old-btcusdt-1h"]
    assert Path(sample["source_paths"][0]).name == "okx_old_market.csv"
    assert sample["blocker_reason_counts"] == {"no_rows_in_requested_window": 1}
    assert sample["requested_window_start"] == "2025-06-19"
    assert sample["requested_window_end"] == "2026-06-18"
    assert sample["requested_window_row_count"] == 0
    assert sample["ready_requested_window_row_count"] == 0
    assert sample["observed_window_start"].startswith("2024-03-01")
    assert sample["observed_window_end"].startswith("2024-03-01")
    assert sample["declared_window_start"] == "2024-03-01"
    assert sample["declared_window_end"] == "2024-03-01"
    assert manifest["archive_coverage_venue_expansion_actionable_gap_count"] == 3
    assert manifest["archive_coverage_venue_expansion_action_counts"] == {
        "add_archive_descriptor_for_target_venue": 2,
        "repair_blocked_archive_bucket": 1,
    }
    venue_gap_samples = manifest["archive_coverage_venue_expansion_gap_samples"]
    assert manifest["archive_coverage_venue_expansion_gap_samples_truncated"] is False
    assert [row["target_action"] for row in venue_gap_samples] == [
        "repair_blocked_archive_bucket",
        "add_archive_descriptor_for_target_venue",
        "add_archive_descriptor_for_target_venue",
    ]
    brief_path = Path(str(iteration["agent_brief_json_path"]))
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    assert brief["archive_blocker_reason_counts"] == {"no_rows_in_requested_window": 1}
    assert brief["archive_blocker_samples"] == samples
    assert brief["archive_blocker_samples_truncated"] is False
    assert brief["venue_expansion_gap_samples"] == venue_gap_samples
    assert brief["venue_expansion_gap_samples_truncated"] is False
    brief["top_archive_blockers"] = [{"reason": "display_only_other_blocker", "count": 99}]
    brief_path.write_text(json.dumps(brief, indent=2, sort_keys=True), encoding="utf-8")

    payload = build_sandbox_iteration_index(tmp_path / "iterations", output_dir=tmp_path / "iteration_index")
    row = payload["rows"][0]
    queue_item = payload["action_queues"]["archive_window_repair_queue"][0]

    assert payload["action_queue_version"] == 14
    assert payload["action_queue_counts"]["archive_window_repair_queue"] == 1
    assert payload["action_queue_counts"]["venue_expansion_gap_queue"] == 1
    assert payload["action_queue_truncated_counts"]["archive_window_repair_queue"] == 0
    assert payload["total_archive_coverage_requested_window_row_count"] == 0
    assert payload["total_venue_expansion_actionable_gap_count"] == 3
    assert row["iteration_id"] == iteration["iteration_id"]
    assert row["recommended_action"] == "adjust_iteration_window_or_refresh_archive_manifest"
    assert row["archive_coverage_requested_window_row_count"] == 0
    assert row["venue_expansion_actionable_gap_count"] == 3
    assert row["venue_expansion_gap_samples"] == venue_gap_samples
    assert row["archive_coverage_blocker_reason_counts"] == {"no_rows_in_requested_window": 1}
    assert row["archive_coverage_blocker_samples"] == samples
    assert row["archive_coverage_blocker_samples_truncated"] is False
    assert row["top_archive_blockers"][0]["reason"] == "display_only_other_blocker"
    assert queue_item["iteration_id"] == iteration["iteration_id"]
    assert queue_item["recommended_action"] == "adjust_iteration_window_or_refresh_archive_manifest"
    assert queue_item["counts"]["archive_coverage_requested_window_row_count"] == 0
    assert queue_item["coverage_status_counts"] == {"blocked": 1}
    assert queue_item["archive_coverage_blocker_reason_counts"] == {"no_rows_in_requested_window": 1}
    assert queue_item["archive_coverage_blocker_samples"] == samples
    assert queue_item["archive_coverage_blocker_samples_truncated"] is False
    assert queue_item["recommended_actions"][0]["archive_coverage_blocker_samples"] == samples
    assert queue_item["recommended_actions"][1]["action"] == "repair_or_add_venue_expansion_archives"
    assert queue_item["recommended_actions"][1]["venue_expansion_gap_samples"] == venue_gap_samples
    assert queue_item["top_archive_blockers"][0]["reason"] == "display_only_other_blocker"
    archive_summary = payload["action_queue_summaries"]["archive_window_repair_queue"]
    assert archive_summary["matched_iteration_count"] == 1
    assert archive_summary["visible_item_count"] == 1
    assert archive_summary["truncated_count"] == 0
    assert archive_summary["coverage_status_counts"] == {"blocked": 1}
    assert archive_summary["archive_coverage_blocker_reason_counts"] == {"no_rows_in_requested_window": 1}
    assert archive_summary["recommended_action_counts"] == {
        "adjust_iteration_window_or_refresh_archive_manifest": 1,
        "repair_or_add_venue_expansion_archives": 1,
    }
    assert archive_summary["counts"]["archive_coverage_requested_window_row_count"] == 0
    assert archive_summary["counts"]["venue_expansion_actionable_gap_count"] == 3
    venue_summary = payload["action_queue_summaries"]["venue_expansion_gap_queue"]
    assert venue_summary["matched_iteration_count"] == 1
    assert venue_summary["venue_expansion_action_counts"] == {
        "add_archive_descriptor_for_target_venue": 2,
        "repair_blocked_archive_bucket": 1,
    }
    assert payload["agent_action_plan_count"] == 2
    assert payload["agent_action_plan"][0]["action"] == "adjust_iteration_window_or_refresh_archive_manifest"
    assert payload["agent_action_plan"][0]["source_queues"] == ["archive_window_repair_queue"]
    assert payload["agent_action_plan"][0]["archive_coverage_blocker_samples"] == samples
    assert payload["agent_action_plan"][0]["archive_coverage_blocker_samples_truncated"] is False
    assert payload["agent_action_plan"][1]["action"] == "repair_or_add_venue_expansion_archives"
    assert payload["agent_action_plan"][1]["source_queues"] == ["venue_expansion_gap_queue"]
    assert payload["agent_action_plan"][1]["venue_expansion_gap_samples"] == venue_gap_samples
    assert payload["agent_action_plan_summary"]["source_queue_counts"] == {
        "archive_window_repair_queue": 1,
        "venue_expansion_gap_queue": 1,
    }
    assert queue_item["candidate_pack_eligible"] is False


def test_sandbox_iteration_index_queues_missing_referenced_artifacts(tmp_path: Path) -> None:
    input_root = tmp_path / "inputs"
    input_root.mkdir()
    catalog_root, archive_root = _write_agent_iteration_inputs(input_root, hypothesis_id="index-missing-artifact")
    output_root = tmp_path / "iterations"
    iteration = run_sandbox_agent_iteration(
        output_dir=output_root,
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    Path(str(iteration["preflight_parquet_path"])).unlink()

    payload = build_sandbox_iteration_index(output_root, output_dir=tmp_path / "iteration_index")
    row = payload["rows"][0]
    queue_item = payload["action_queues"]["artifact_repair_queue"][0]
    queue_summary = payload["action_queue_summaries"]["artifact_repair_queue"]

    assert payload["iteration_count"] == 1
    assert payload["brief_status_counts"] == {"present": 1}
    assert payload["artifact_availability_status_counts"] == {"missing_artifacts": 1}
    assert payload["recommended_action_counts"]["restore_or_rerun_missing_iteration_artifacts"] == 1
    assert payload["recommended_action_counts"]["repair_or_add_venue_expansion_archives"] == 1
    assert payload["total_artifact_missing_count"] == 1
    assert payload["action_queue_counts"]["artifact_repair_queue"] == 1
    assert payload["action_queue_counts"]["venue_expansion_gap_queue"] == 1
    assert payload["action_queue_truncated_counts"]["artifact_repair_queue"] == 0
    assert payload["agent_action_plan_count"] == 3
    assert [item["action"] for item in payload["agent_action_plan"]] == [
        "restore_or_rerun_missing_iteration_artifacts",
        "review_descriptor_only_strict_validation_requests",
        "repair_or_add_venue_expansion_archives",
    ]
    assert payload["agent_action_plan"][0]["source_queues"] == ["artifact_repair_queue"]
    assert payload["agent_action_plan"][0]["blocked_by_prior_action"] is False
    assert payload["agent_action_plan"][1]["source_queues"] == ["strict_validation_request_queue"]
    assert payload["agent_action_plan"][1]["blocked_by_prior_action"] is True
    assert payload["agent_action_plan"][2]["source_queues"] == ["venue_expansion_gap_queue"]
    assert payload["agent_action_plan"][2]["blocked_by_prior_action"] is True
    assert payload["agent_action_plan_summary"]["blocked_by_prior_action_count"] == 2
    assert row["artifact_availability_status"] == "missing_artifacts"
    assert row["recommended_action"] == "restore_or_rerun_missing_iteration_artifacts"
    assert row["venue_expansion_actionable_gap_count"] == 2
    assert row["artifact_missing_count"] == 1
    assert row["artifact_present_count"] == row["artifact_reference_count"] - 1
    assert row["artifact_missing_keys"] == ["preflight_parquet_path"]
    assert queue_item["iteration_id"] == iteration["iteration_id"]
    assert queue_item["recommended_action"] == "restore_or_rerun_missing_iteration_artifacts"
    assert queue_item["recommended_actions"][0]["artifact_missing_keys"] == ["preflight_parquet_path"]
    assert queue_item["recommended_actions"][2]["action"] == "repair_or_add_venue_expansion_archives"
    assert queue_item["artifact_availability_status"] == "missing_artifacts"
    assert queue_item["artifact_missing_keys"] == ["preflight_parquet_path"]
    assert queue_item["counts"]["artifact_missing_count"] == 1
    assert queue_item["candidate_pack_eligible"] is False
    assert queue_summary["matched_iteration_count"] == 1
    assert queue_summary["artifact_availability_status_counts"] == {"missing_artifacts": 1}
    assert queue_summary["artifact_missing_key_counts"] == {"preflight_parquet_path": 1}
    assert queue_summary["recommended_action_counts"] == {
        "repair_or_add_venue_expansion_archives": 1,
        "restore_or_rerun_missing_iteration_artifacts": 1,
        "review_descriptor_only_strict_validation_requests": 1,
    }
    assert queue_summary["counts"]["artifact_missing_count"] == 1


def test_sandbox_iteration_index_reports_missing_agent_brief_file(tmp_path: Path) -> None:
    input_root = tmp_path / "inputs"
    input_root.mkdir()
    catalog_root, archive_root = _write_agent_iteration_inputs(input_root, hypothesis_id="index-missing-brief")
    output_root = tmp_path / "iterations"
    iteration = run_sandbox_agent_iteration(
        output_dir=output_root,
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="hyperliquid",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    Path(str(iteration["agent_brief_json_path"])).unlink()

    payload = build_sandbox_iteration_index(output_root, output_dir=tmp_path / "iteration_index")
    row = payload["rows"][0]

    assert payload["iteration_count"] == 1
    assert payload["brief_status_counts"] == {"missing_file": 1}
    assert payload["recommended_action_counts"] == {
        "repair_or_add_venue_expansion_archives": 1,
        "restore_or_regenerate_iteration_agent_brief": 1,
        "restore_or_rerun_missing_iteration_artifacts": 1,
        "review_descriptor_only_strict_validation_requests": 1,
    }
    assert payload["action_queue_counts"]["missing_brief_queue"] == 1
    assert payload["action_queue_counts"]["artifact_repair_queue"] == 1
    assert payload["action_queue_counts"]["venue_expansion_gap_queue"] == 1
    assert payload["agent_action_plan_count"] == 4
    assert [item["action"] for item in payload["agent_action_plan"]] == [
        "restore_or_regenerate_iteration_agent_brief",
        "restore_or_rerun_missing_iteration_artifacts",
        "review_descriptor_only_strict_validation_requests",
        "repair_or_add_venue_expansion_archives",
    ]
    assert payload["agent_action_plan"][0]["source_queues"] == ["missing_brief_queue"]
    assert payload["agent_action_plan"][1]["source_queues"] == ["artifact_repair_queue"]
    assert payload["agent_action_plan"][2]["source_queues"] == ["strict_validation_request_queue"]
    assert payload["agent_action_plan"][3]["source_queues"] == ["venue_expansion_gap_queue"]
    assert payload["agent_action_plan_summary"]["blocked_by_prior_action_count"] == 3
    assert row["brief_status"] == "missing_file"
    assert row["recommended_action"] == "restore_or_regenerate_iteration_agent_brief"
    assert row["venue_expansion_actionable_gap_count"] == 2
    assert row["artifact_availability_status"] == "missing_artifacts"
    assert row["artifact_missing_keys"] == ["agent_brief_json_path"]
    assert row["next_action"] == iteration["agent_brief_next_action"]
    assert row["deduped_validation_request_count"] == 1
    missing_item = payload["action_queues"]["missing_brief_queue"][0]
    assert missing_item["iteration_id"] == iteration["iteration_id"]
    assert missing_item["recommended_action"] == "restore_or_regenerate_iteration_agent_brief"
    assert missing_item["recommended_actions"][0]["brief_status"] == "missing_file"
    assert missing_item["recommended_actions"][3]["action"] == "repair_or_add_venue_expansion_archives"
    assert missing_item["brief_status"] == "missing_file"
    assert missing_item["agent_brief_json_path"] == iteration["agent_brief_json_path"]
    assert missing_item["candidate_pack_eligible"] is False


def test_cli_command_preflights_sandbox_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    spec_path = tmp_path / "spec.json"
    catalog_path = tmp_path / "catalog.csv"
    venues_path = tmp_path / "venues.json"
    market_path = tmp_path / "market.csv"
    spec_path.write_text(
        json.dumps(
            {
                "run_id": "cli-preflight",
                "data_window": {"start": "2024-01-01", "end": "2024-01-03"},
                "holding_periods": [1],
                "exit_variants": [{"variant_id": "hold", "exit_profile": "fixed_hold"}],
                "filter_variants": [{"variant_id": "base"}],
                "min_trades": 1,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "hypothesis_id": "cli-preflight-long",
                "family": "cli_preflight_family",
                "signal_column": "signal",
                "side": "long",
            }
        ]
    ).to_csv(catalog_path, index=False)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC"),
            "close": [100.0, 101.0, 102.0, 103.0, 104.0],
            "signal": [1] * 5,
        }
    ).to_csv(market_path, index=False)
    venues_path.write_text(
        json.dumps(
            {
                "venue_archives": [
                    {
                        "descriptor_id": "cli-preflight-okx",
                        "venue": "okx",
                        "symbol": "BTCUSDT",
                        "data_family": "kline",
                        "data_path": str(market_path),
                        "window": {"start": "2024-01-01", "end": "2024-01-03"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = main._run_preflight_rapid_strategy_sandbox_command(
        argparse.Namespace(
            command="preflight-rapid-strategy-sandbox",
            spec=str(spec_path),
            strategy_catalog=str(catalog_path),
            venue_archives=str(venues_path),
            market_data=None,
            output_dir="preflights",
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["runnable_trial_estimate"] == 1
    assert Path(str(payload["preflight_json_path"])).resolve().relative_to(research_root.resolve())
    assert Path(str(payload["preflight_parquet_path"])).exists()


def test_cli_command_summarizes_sandbox_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    run = run_sandbox_sweep(
        spec=_spec("cli-summary-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue()],
        output_root=research_root,
    )

    payload = main._run_summarize_rapid_strategy_sandbox_command(
        argparse.Namespace(
            command="summarize-rapid-strategy-sandbox",
            run_dir=str(run.artifacts.run_dir),
            top_n=1,
            no_write_report=False,
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["result_count"] == len(run.results)
    assert len(payload["top_results"]) == 1
    assert Path(str(payload["analysis_report_path"])).exists()


def test_cli_command_summarizes_sandbox_hypotheses_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    run = run_sandbox_sweep(
        spec=_spec("cli-hypothesis-summary-run"),
        market_frame=_market_frame(),
        strategies=[_strategy(), _short_strategy()],
        venues=[_venue()],
        output_root=research_root,
    )

    payload = main._run_summarize_rapid_strategy_sandbox_hypotheses_command(
        argparse.Namespace(
            command="summarize-rapid-strategy-sandbox-hypotheses",
            run_dir=str(run.artifacts.run_dir),
            suite_dir=None,
            no_write_report=False,
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["hypothesis_count"] == 2
    assert Path(str(payload["hypothesis_falsification_json_path"])).exists()


def test_cli_command_exports_sandbox_validation_requests_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    run = run_sandbox_sweep(
        spec=_spec("cli-validation-request-bundle-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue()],
        output_root=research_root,
    )

    payload = main._run_export_rapid_strategy_sandbox_validation_requests_command(
        argparse.Namespace(
            command="export-rapid-strategy-sandbox-validation-requests",
            run_dir=str(run.artifacts.run_dir),
            suite_dir=None,
            output_dir="validation_request_bundles/run_bundle",
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["source_scope"] == "run"
    assert payload["strict_validation_executed"] is False
    assert payload["deduped_request_count"] == len(run.evidence_requests)
    assert Path(str(payload["bundle_json_path"])).resolve().relative_to(research_root.resolve())


def test_cli_command_exports_sandbox_venue_expansion_requests_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    input_root = tmp_path / "inputs"
    input_root.mkdir()
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    catalog_root, archive_root = _write_agent_iteration_inputs(
        input_root,
        hypothesis_id="cli-venue-expansion-long",
    )
    run_sandbox_agent_iteration(
        output_dir=research_root / "agent_iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    build_sandbox_iteration_index(
        research_root / "agent_iterations",
        output_dir=research_root / "iteration_index",
    )
    catalog = index_sandbox_artifacts(
        research_root,
        output_dir=research_root / "artifact_catalog",
    )

    payload = main._run_export_rapid_strategy_sandbox_venue_expansion_requests_command(
        argparse.Namespace(
            command="export-rapid-strategy-sandbox-venue-expansion-requests",
            catalog=str(catalog["catalog_json_path"]),
            worklist=None,
            output_dir="venue_expansion_requests",
        )
    )
    frame = pd.read_parquet(Path(str(payload["bundle_parquet_path"])))

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_only"] is True
    assert payload["request_count"] == 2
    assert payload["deduped_request_count"] == 2
    assert payload["target_venue_counts"] == {"bybit": 1, "hyperliquid": 1}
    assert payload["provider_download_authorized"] is False
    assert payload["archive_manifest_write_authorized"] is False
    assert payload["source_archive_mutation_authorized"] is False
    assert Path(str(payload["bundle_json_path"])).resolve().relative_to(
        research_root.resolve()
    )
    assert Path(str(payload["bundle_parquet_path"])).resolve().relative_to(
        research_root.resolve()
    )
    assert len(frame) == 2


def _write_venue_expansion_materializer_request_bundle(
    path: Path,
    *,
    request_specs: list[dict[str, object]] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    auth_flags = {
        "pre_2024_data_allowed": False,
        "provider_download_authorized": False,
        "archive_manifest_write_authorized": False,
        "source_archive_mutation_authorized": False,
        "replay_command_execution_authorized": False,
        "strict_validation_authorized": False,
        "candidate_pack_write_authorized": False,
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    specs = request_specs or [
        {
            "request_id": "request-bybit-btcusdt-1h",
            "target_venue": "bybit",
            "market_symbol_key": "btcusdt",
            "data_family": "kline",
            "interval": "1h",
            "requested_window_start": "2024-03-01",
            "requested_window_end": "2024-03-02",
        },
        {
            "request_id": "request-hyperliquid-btcusdt-1h",
            "target_venue": "hyperliquid",
            "market_symbol_key": "btcusdt",
            "data_family": "kline",
            "interval": "1h",
            "requested_window_start": "2024-03-01",
            "requested_window_end": "2024-03-02",
        },
    ]
    descriptors = []
    for rank, spec in enumerate(specs, start=1):
        target_venue = str(spec["target_venue"])
        market_symbol_key = str(spec["market_symbol_key"])
        data_family = str(spec["data_family"])
        interval = str(spec["interval"])
        descriptors.append(
            {
                **sandbox_boundary_metadata(),
                **auth_flags,
                "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_request_descriptor",
                "bundle_id": "test-venue-request-bundle",
                "request_id": str(spec["request_id"]),
                "dedupe_key": f"dedupe-{rank}",
                "request_rank": rank,
                "requested_operation": "archive_descriptor_intake_request",
                "execution_mode": "descriptor_only_no_execution",
                "descriptor_only": True,
                "target_venue": target_venue,
                "market_symbol_key": market_symbol_key,
                "data_family": data_family,
                "interval": interval,
                "target_bucket_key": "|".join(
                    (target_venue, market_symbol_key, data_family, interval)
                ),
                "target_status": "missing_target_venue",
                "target_action": "repair_or_add_venue_expansion_archives",
                "target_missing": True,
                "requested_window_start": str(spec["requested_window_start"]),
                "requested_window_end": str(spec["requested_window_end"]),
                "source_references": [],
            }
        )
    payload = {
        **sandbox_boundary_metadata(),
        **auth_flags,
        "artifact_family": "rapid_strategy_iteration_sandbox_venue_expansion_request_bundle",
        "bundle_id": "test-venue-request-bundle",
        "execution_mode": "descriptor_only_no_execution",
        "descriptor_only": True,
        "minimum_window_start": "2024-01-01",
        "request_count": len(descriptors),
        "deduped_request_count": len(descriptors),
        "descriptors": descriptors,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_materializer_archive_csv(path: Path, *, venue: str = "bybit") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-03-01", periods=6, freq="1h", tz="UTC"),
            "venue": [venue] * 6,
            "symbol": ["BTCUSDT"] * 6,
            "data_family": ["kline"] * 6,
            "interval": ["1h"] * 6,
            "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
            "high": [101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0, 104.0],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5],
            "volume": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
            "direct_signal": [1, 1, 1, 1, 1, 1],
        }
    ).to_csv(path, index=False)
    return path


def test_venue_expansion_local_materializer_writes_candidates_and_blockers(tmp_path: Path) -> None:
    request_bundle = _write_venue_expansion_materializer_request_bundle(
        tmp_path / "requests" / "bundle.json"
    )
    archive_root = tmp_path / "archives"
    source_path = _write_materializer_archive_csv(
        archive_root / "bybit_BTCUSDT_kline_1h.csv"
    )
    output_dir = tmp_path / "materialized"

    payload = materialize_sandbox_venue_expansion_requests(
        request_bundle,
        [archive_root],
        output_dir=output_dir,
    )
    candidate_frame = pd.read_parquet(payload["descriptor_candidates_parquet_path"])
    patch_frame = pd.read_parquet(payload["manifest_patch_dry_run_parquet_path"])
    patch_rows = {row["request_id"]: row for row in payload["manifest_patch_rows"]}
    candidate = payload["descriptor_candidates"][0]

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["sandbox_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_evidence"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_only"] is True
    assert payload["dry_run_only"] is True
    assert payload["provider_download_authorized"] is False
    assert payload["archive_manifest_write_authorized"] is False
    assert payload["source_archive_mutation_authorized"] is False
    assert payload["descriptor_candidate_count"] == 1
    assert payload["ready_request_count"] == 1
    assert payload["blocked_request_count"] == 1
    assert len(candidate_frame) == 1
    assert len(patch_frame) == 2
    assert patch_rows["request-bybit-btcusdt-1h"]["status"] == "ready_descriptor_candidates"
    assert patch_rows["request-hyperliquid-btcusdt-1h"]["status"] == "blocked"
    assert patch_rows["request-hyperliquid-btcusdt-1h"]["blocker_reasons"] == [
        "no_matching_local_archive_file"
    ]
    assert candidate["target_venue"] == "bybit"
    assert candidate["source_path"] == str(source_path.resolve())
    assert candidate["descriptor_payload"]["promotion_ready"] is False
    assert candidate["descriptor_payload"]["candidate_pack_eligible"] is False
    assert Path(str(payload["descriptor_candidates_json_path"])).exists()
    assert Path(str(payload["manifest_patch_dry_run_json_path"])).exists()
    assert not (output_dir / "venue_archives.json").exists()


def test_venue_expansion_local_materializer_rejects_pre_2024_requests(tmp_path: Path) -> None:
    request_bundle = _write_venue_expansion_materializer_request_bundle(
        tmp_path / "requests" / "bundle.json",
        request_specs=[
            {
                "request_id": "request-bybit-pre-2024",
                "target_venue": "bybit",
                "market_symbol_key": "btcusdt",
                "data_family": "kline",
                "interval": "1h",
                "requested_window_start": "2023-12-31",
                "requested_window_end": "2024-03-02",
            }
        ],
    )
    archive_root = tmp_path / "archives"
    _write_materializer_archive_csv(archive_root / "bybit_BTCUSDT_kline_1h.csv")

    with pytest.raises(ValueError, match="sandbox data windows must start on or after 2024-01-01"):
        materialize_sandbox_venue_expansion_requests(
            request_bundle,
            [archive_root],
            output_dir=tmp_path / "materialized",
        )

    assert not list((tmp_path / "materialized").glob("*.json"))
    assert not list((tmp_path / "materialized").glob("*.parquet"))


def test_cli_command_materializes_venue_expansion_requests_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    archive_root = tmp_path / "archives"
    request_bundle = _write_venue_expansion_materializer_request_bundle(
        research_root / "requests" / "bundle.json"
    )
    _write_materializer_archive_csv(archive_root / "bybit_BTCUSDT_kline_1h.csv")
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    payload = main._run_materialize_rapid_strategy_sandbox_venue_expansion_requests_command(
        argparse.Namespace(
            command="materialize-rapid-strategy-sandbox-venue-expansion-requests",
            request_bundle=str(request_bundle),
            archive_root=[str(archive_root)],
            output_dir="venue_expansion_materialized",
            venue=None,
            symbol=None,
            data_family=None,
            interval=None,
            max_files=20,
        )
    )

    assert payload["research_only"] is True
    assert payload["descriptor_only"] is True
    assert payload["archive_manifest_write_authorized"] is False
    assert payload["source_archive_mutation_authorized"] is False
    assert payload["descriptor_candidate_count"] == 1
    assert Path(str(payload["manifest_patch_dry_run_json_path"])).resolve().relative_to(
        research_root.resolve()
    )
    assert Path(str(payload["descriptor_candidates_parquet_path"])).resolve().relative_to(
        research_root.resolve()
    )


def test_venue_expansion_materializer_catalog_discovery(tmp_path: Path) -> None:
    request_bundle = _write_venue_expansion_materializer_request_bundle(
        tmp_path / "requests" / "bundle.json"
    )
    archive_root = tmp_path / "archives"
    _write_materializer_archive_csv(archive_root / "bybit_BTCUSDT_kline_1h.csv")
    materialized = materialize_sandbox_venue_expansion_requests(
        request_bundle,
        [archive_root],
        output_dir=tmp_path / "materialized",
    )

    catalog = index_sandbox_artifacts(
        tmp_path,
        output_dir=tmp_path / "catalog_after_materializer",
    )
    rows = {row["artifact_kind"]: row for row in catalog["artifacts"]}

    assert catalog["artifact_kind_counts"]["venue_expansion_descriptor_candidates"] == 1
    assert catalog["artifact_kind_counts"]["venue_expansion_manifest_patch_dry_run"] == 1
    candidate_row = rows["venue_expansion_descriptor_candidates"]
    patch_row = rows["venue_expansion_manifest_patch_dry_run"]
    for row in (candidate_row, patch_row):
        assert row["research_only"] is True
        assert row["observe_only"] is True
        assert row["sandbox_only"] is True
        assert row["promotion_ready"] is False
        assert row["candidate_evidence"] is False
        assert row["candidate_pack_eligible"] is False
        assert row["descriptor_only"] is True
        assert row["strict_validation_executed"] is False
        assert row["candidate_pack_written"] is False
        assert row["provider_download_authorized"] is False
        assert row["archive_manifest_write_authorized"] is False
        assert row["source_archive_mutation_authorized"] is False
        assert row["archive_manifest_write_executed"] is False
        assert row["source_archive_mutation_executed"] is False
        assert row["venue_expansion_materialization_id"] == materialized["materialization_id"]
        assert row["venue_expansion_source_request_count"] == 2
        assert row["venue_expansion_filtered_request_count"] == 2
        assert row["venue_expansion_descriptor_candidate_count"] == 1
        assert row["venue_expansion_dry_run_patch_row_count"] == 2
        assert row["venue_expansion_ready_request_count"] == 1
        assert row["venue_expansion_blocked_request_count"] == 1
        assert row["venue_expansion_archive_file_count"] == 1
        assert row["venue_expansion_loadable_archive_file_count"] == 1
        assert row["venue_expansion_archive_scan_status_counts"] == {"loadable": 1}
        assert row["venue_expansion_archive_skip_reason_counts"] == {}
        assert row["venue_expansion_descriptor_candidates_json_path"] == materialized[
            "descriptor_candidates_json_path"
        ]
        assert row["venue_expansion_descriptor_candidates_parquet_path"] == materialized[
            "descriptor_candidates_parquet_path"
        ]
        assert row["venue_expansion_manifest_patch_dry_run_json_path"] == materialized[
            "manifest_patch_dry_run_json_path"
        ]
        assert row["venue_expansion_manifest_patch_dry_run_parquet_path"] == materialized[
            "manifest_patch_dry_run_parquet_path"
        ]

    frame = pd.read_parquet(catalog["catalog_parquet_path"])
    indexed_kinds = set(frame["artifact_kind"])
    assert "venue_expansion_descriptor_candidates" in indexed_kinds
    assert "venue_expansion_manifest_patch_dry_run" in indexed_kinds


def test_venue_expansion_candidate_manifest_export_writes_loadable_manifest(
    tmp_path: Path,
) -> None:
    request_bundle = _write_venue_expansion_materializer_request_bundle(
        tmp_path / "requests" / "bundle.json"
    )
    archive_root = tmp_path / "archives"
    _write_materializer_archive_csv(archive_root / "bybit_BTCUSDT_kline_1h.csv")
    materialized = materialize_sandbox_venue_expansion_requests(
        request_bundle,
        [archive_root],
        output_dir=tmp_path / "materialized",
    )

    report = export_sandbox_venue_expansion_candidate_manifest(
        materialized["descriptor_candidates_json_path"],
        output_dir=tmp_path / "candidate_manifests",
    )
    manifest_path = Path(str(report["venue_archive_manifest_path"]))
    descriptors = load_venue_archive_descriptors(manifest_path)
    coverage = summarize_sandbox_archive_coverage(
        manifest_path,
        output_dir=tmp_path / "coverage",
        requested_window=DataWindow("2024-03-01", "2024-03-02"),
    )
    preflight = preflight_sandbox_compatibility(
        spec=SandboxRunSpec(
            run_id="candidate-manifest-export-smoke",
            data_window=DataWindow("2024-03-01", "2024-03-02"),
            holding_periods=(1,),
            round_trip_cost_bps=0.0,
            min_trades=1,
            max_evidence_requests=1,
        ),
        strategies=[
            StrategyCatalogRow(
                hypothesis_id="candidate-manifest-direct-long",
                family="candidate_manifest_smoke",
                source_id="candidate_manifest_export_test",
                signal_column="direct_signal",
                side="long",
            )
        ],
        venues=descriptors,
        output_dir=tmp_path / "preflight",
    )
    report_frame = pd.read_parquet(report["candidate_manifest_report_parquet_path"])

    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["sandbox_only"] is True
    assert report["promotion_ready"] is False
    assert report["candidate_evidence"] is False
    assert report["candidate_pack_eligible"] is False
    assert report["provider_download_authorized"] is False
    assert report["source_archive_mutation_authorized"] is False
    assert report["existing_archive_manifest_mutation_authorized"] is False
    assert report["strict_validation_executed"] is False
    assert report["candidate_pack_written"] is False
    assert report["descriptor_count"] == 1
    assert manifest_path.name == "venue_archives.json"
    assert manifest_path.exists()
    assert Path(str(report["candidate_manifest_report_json_path"])).exists()
    assert Path(str(report["candidate_manifest_report_parquet_path"])).exists()
    assert len(report_frame) == 1
    assert set(report_frame["candidate_pack_eligible"]) == {False}
    assert len(descriptors) == 1
    assert descriptors[0].venue == "bybit"
    assert descriptors[0].symbol == "BTCUSDT"
    assert coverage["ready_descriptor_count"] == 1
    assert coverage["blocked_descriptor_count"] == 0
    assert preflight["status_counts"] == {"runnable": 1}
    assert preflight["runnable_trial_estimate"] == 1


def test_cli_command_exports_venue_expansion_candidate_manifest_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    archive_root = tmp_path / "archives"
    request_bundle = _write_venue_expansion_materializer_request_bundle(
        research_root / "requests" / "bundle.json"
    )
    _write_materializer_archive_csv(archive_root / "bybit_BTCUSDT_kline_1h.csv")
    materialized = materialize_sandbox_venue_expansion_requests(
        request_bundle,
        [archive_root],
        output_dir=research_root / "materialized",
    )
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    payload = main._run_export_rapid_strategy_sandbox_venue_expansion_candidate_manifest_command(
        argparse.Namespace(
            command="export-rapid-strategy-sandbox-venue-expansion-candidate-manifest",
            descriptor_candidates=str(materialized["descriptor_candidates_json_path"]),
            output_dir="candidate_manifests",
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_count"] == 1
    assert payload["source_archive_mutation_authorized"] is False
    assert payload["existing_archive_manifest_mutation_authorized"] is False
    assert Path(str(payload["venue_archive_manifest_path"])).resolve().relative_to(
        research_root.resolve()
    )
    assert Path(str(payload["candidate_manifest_report_json_path"])).resolve().relative_to(
        research_root.resolve()
    )


def test_end_to_end_venue_expansion_fixture_smoke(tmp_path: Path) -> None:
    request_bundle = _write_venue_expansion_materializer_request_bundle(
        tmp_path / "requests" / "bundle.json"
    )
    archive_root = tmp_path / "archives"
    _write_materializer_archive_csv(archive_root / "bybit_BTCUSDT_kline_1h.csv")
    materialized = materialize_sandbox_venue_expansion_requests(
        request_bundle,
        [archive_root],
        output_dir=tmp_path / "materialized",
    )
    candidate_manifest = export_sandbox_venue_expansion_candidate_manifest(
        materialized["descriptor_candidates_json_path"],
        output_dir=tmp_path / "candidate_manifests",
    )
    venues = load_venue_archive_descriptors(candidate_manifest["venue_archive_manifest_path"])
    strategies = [
        StrategyCatalogRow(
            hypothesis_id="fixture-loop-direct-long",
            family="fixture_loop_family",
            source_id="wpr106_369_fixture",
            signal_column="direct_signal",
            side="long",
        )
    ]
    spec = SandboxRunSpec(
        run_id="fixture-loop-v1",
        data_window=DataWindow("2024-03-01", "2024-03-02"),
        holding_periods=(1, 2),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=2,
    )

    coverage = summarize_sandbox_archive_coverage(
        candidate_manifest["venue_archive_manifest_path"],
        output_dir=tmp_path / "coverage",
        requested_window=spec.data_window,
    )
    preflight = preflight_sandbox_compatibility(
        spec=spec,
        strategies=strategies,
        venues=venues,
        output_dir=tmp_path / "preflight",
    )
    run = run_sandbox_archive_sweep(
        spec=spec,
        strategies=strategies,
        venues=venues,
        output_root=tmp_path / "runs",
    )
    analysis = summarize_sandbox_run(run.artifacts.run_dir)
    falsification = summarize_sandbox_hypotheses(run.artifacts.run_dir)
    strict_bundle = export_sandbox_validation_request_bundle(
        run.artifacts.run_dir,
        output_dir=tmp_path / "strict_validation_requests",
    )
    catalog = index_sandbox_artifacts(tmp_path, output_dir=tmp_path / "artifact_catalog")

    assert materialized["descriptor_candidate_count"] == 1
    assert materialized["blocked_request_count"] == 1
    assert candidate_manifest["descriptor_count"] == 1
    assert coverage["ready_descriptor_count"] == 1
    assert coverage["blocked_descriptor_count"] == 0
    assert preflight["status_counts"] == {"runnable": 1}
    assert preflight["runnable_trial_estimate"] == 2
    assert len(run.results) == 2
    assert len(run.evidence_requests) == 2
    assert analysis["result_count"] == 2
    assert falsification["hypothesis_count"] == 1
    assert strict_bundle["descriptor_only"] is True
    assert strict_bundle["strict_validation_executed"] is False
    assert strict_bundle["candidate_pack_written"] is False
    assert strict_bundle["candidate_pack_eligible"] is False
    assert strict_bundle["deduped_request_count"] == 2
    assert catalog["artifact_kind_counts"]["venue_expansion_descriptor_candidates"] == 1
    assert catalog["artifact_kind_counts"]["venue_expansion_manifest_patch_dry_run"] == 1
    assert catalog["artifact_kind_counts"]["archive_manifest"] >= 1
    assert catalog["artifact_kind_counts"]["archive_coverage_matrix"] >= 1
    assert catalog["artifact_kind_counts"]["compatibility_preflight"] >= 1
    assert catalog["artifact_kind_counts"]["run_manifest"] >= 1
    assert catalog["artifact_kind_counts"]["run_analysis"] >= 1
    assert catalog["artifact_kind_counts"]["run_hypothesis_falsification"] >= 1
    assert catalog["artifact_kind_counts"]["run_strict_validation_request_bundle"] >= 1
    for payload in (
        materialized,
        candidate_manifest,
        coverage,
        preflight,
        analysis,
        falsification,
        strict_bundle,
        catalog,
    ):
        assert payload["research_only"] is True
        assert payload["observe_only"] is True
        assert payload["sandbox_only"] is True
        assert payload["promotion_ready"] is False
        assert payload["candidate_evidence"] is False
        assert payload["candidate_pack_eligible"] is False
        assert payload["live_signal"] is False
        assert payload["paper_signal"] is False
        assert payload["sizing_instruction"] is False
        assert payload["order_placement_instruction"] is False
        assert payload["runtime_mode_change"] is False


def test_cli_command_indexes_sandbox_artifacts_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    run = run_sandbox_sweep(
        spec=_spec("cli-artifact-catalog-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue()],
        output_root=research_root / "sandbox_runs",
    )
    summarize_sandbox_run(run.artifacts.run_dir)

    payload = main._run_index_rapid_strategy_sandbox_artifacts_command(
        argparse.Namespace(
            command="index-rapid-strategy-sandbox-artifacts",
            root_dir=str(research_root),
            output_dir="sandbox_catalog",
            max_files=100,
            no_write_report=False,
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["artifact_count"] >= 2
    assert payload["artifact_kind_counts"]["run_manifest"] == 1
    assert Path(str(payload["catalog_json_path"])).resolve().relative_to(research_root.resolve())


def test_cli_command_indexes_sandbox_iterations_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    input_root = tmp_path / "inputs"
    input_root.mkdir()
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    catalog_root, archive_root = _write_agent_iteration_inputs(input_root, hypothesis_id="cli-index-iteration-long")
    iteration = run_sandbox_agent_iteration(
        output_dir=research_root / "agent_iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )

    payload = main._run_index_rapid_strategy_sandbox_iterations_command(
        argparse.Namespace(
            command="index-rapid-strategy-sandbox-iterations",
            root_dir="agent_iterations",
            output_dir="iteration_indexes",
            max_files=100,
            no_write_report=False,
        )
    )
    catalog = index_sandbox_artifacts(research_root, output_dir=research_root / "catalog")

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["iteration_count"] == 1
    assert payload["rows"][0]["iteration_id"] == iteration["iteration_id"]
    assert payload["rows"][0]["next_action"] == "review_descriptor_only_strict_validation_requests"
    assert Path(str(payload["iteration_index_json_path"])).resolve().relative_to(research_root.resolve())
    assert Path(str(payload["iteration_index_parquet_path"])).exists()
    assert catalog["artifact_kind_counts"]["iteration_index"] == 1


def test_cli_command_ranks_sandbox_artifacts_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    run_sandbox_sweep(
        spec=_spec("cli-global-leaderboard-run"),
        market_frame=_market_frame(),
        strategies=[_strategy(), _short_strategy()],
        venues=[_venue("okx")],
        output_root=research_root / "sandbox_runs",
    )

    payload = main._run_rank_rapid_strategy_sandbox_artifacts_command(
        argparse.Namespace(
            command="rank-rapid-strategy-sandbox-artifacts",
            root_dir=str(research_root),
            output_dir="sandbox_leaderboard",
            max_runs=100,
            top_n=10,
            no_write_report=False,
        )
    )

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["source_run_count"] == 1
    assert payload["hypothesis_count"] == 2
    assert Path(str(payload["leaderboard_json_path"])).resolve().relative_to(research_root.resolve())
    assert Path(str(payload["leaderboard_parquet_path"])).exists()


def test_cli_command_runs_sandbox_suite_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    suite_path = _write_suite_fixture(tmp_path, suite_id="cli-suite-batch")

    payload = main._run_rapid_strategy_sandbox_suite_command(
        argparse.Namespace(
            command="run-rapid-strategy-sandbox-suite",
            suite=str(suite_path),
            output_dir="sandbox_suite_cli",
            top_n=1,
            max_workers=2,
        )
    )

    suite_dir = Path(str(payload["suite_dir"]))
    manifest = json.loads(Path(str(payload["suite_manifest_path"])).read_text(encoding="utf-8"))

    assert payload["research_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["case_count"] == 2
    assert payload["max_workers"] == 2
    assert payload["completed_case_count"] == 2
    assert payload["skipped_case_count"] == 0
    assert payload["preflight_runnable_trial_estimate"] == 2
    assert payload["preflight_blocked_trial_estimate"] == 0
    assert payload["evidence_request_count"] == 2
    assert suite_dir.resolve().relative_to(research_root.resolve())
    assert manifest["suite_spec"]["suite_id"] == "cli-suite-batch"
    assert manifest["max_workers"] == 2
    assert manifest["completed_case_count"] == 2


def test_cli_command_verifies_sandbox_artifacts_under_research_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    run = run_sandbox_sweep(
        spec=_spec("cli-integrity-run"),
        market_frame=_market_frame(),
        strategies=[_strategy()],
        venues=[_venue("okx")],
        output_root=research_root / "sandbox_runs",
    )

    payload = main._run_verify_rapid_strategy_sandbox_artifacts_command(
        argparse.Namespace(
            command="verify-rapid-strategy-sandbox-artifacts",
            target=str(run.artifacts.run_dir),
            output_dir="sandbox_integrity_reports",
            no_write_report=False,
        )
    )

    report_json_path = Path(str(payload["report_json_path"]))
    report_parquet_path = Path(str(payload["report_parquet_path"]))
    frame = pd.read_parquet(report_parquet_path)

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["sandbox_only"] is True
    assert payload["candidate_pack_eligible"] is False
    assert payload["strict_validation_executed"] is False
    assert payload["candidate_pack_written"] is False
    assert payload["verification_status"] == "passed"
    assert payload["source_scope"] == "run"
    assert payload["verified_artifact_count"] == 4
    assert report_json_path.resolve().relative_to(research_root.resolve())
    assert report_parquet_path.resolve().relative_to(research_root.resolve())
    assert set(frame["status"]) == {"matched"}


def _write_next_action_dashboard_fixture(research_root: Path) -> tuple[Path, Path]:
    research_root.mkdir(parents=True, exist_ok=True)
    catalog_dir = research_root / "catalog"
    index_dir = research_root / "iteration_index"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = catalog_dir / "sandbox_artifact_catalog.json"
    index_path = index_dir / "sandbox_iteration_index.json"
    action_plan_path = index_dir / "sandbox_iteration_agent_action_plan.parquet"
    venue_worklist_path = catalog_dir / "sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist.parquet"
    strict_queue_path = catalog_dir / "sandbox_artifact_catalog_strict_validation_descriptor_queue.parquet"
    global_top_path = catalog_dir / "sandbox_artifact_catalog_global_top_hypotheses.parquet"
    preflight_path = research_root / "iterations" / "run-a" / "preflight.json"
    archive_coverage_path = research_root / "iterations" / "run-a" / "archive_coverage.json"
    strategy_catalog_path = research_root / "strategy_catalogs" / "catalog.json"
    venue_manifest_path = research_root / "archive_manifests" / "venues.json"

    boundary = sandbox_boundary_metadata()
    action_item = {
        **boundary,
        "artifact_family": "rapid_strategy_iteration_sandbox_action_queue_item",
        "iteration_id": "iter-a",
        "run_id": "run-a",
        "next_action": "repair_preflight_blockers",
        "recommended_action": "repair_preflight_blockers",
        "reason_codes": ["missing_close_column"],
        "preflight_json_path": str(preflight_path),
        "archive_coverage_json_path": str(archive_coverage_path),
        "strategy_catalog_json_path": str(strategy_catalog_path),
        "venue_archive_manifest_path": str(venue_manifest_path),
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    strict_item = {
        **boundary,
        "artifact_family": "rapid_strategy_iteration_sandbox_action_queue_item",
        "iteration_id": "iter-b",
        "run_id": "run-b",
        "next_action": "review_descriptor_only_strict_validation_requests",
        "recommended_action": "review_descriptor_only_strict_validation_requests",
        "reason_codes": ["deduped_validation_requests"],
        "top_validation_requests": [{"descriptor_id": "descriptor-okx-btc"}],
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    venue_item = {
        **boundary,
        "artifact_family": "rapid_strategy_iteration_sandbox_action_queue_item",
        "iteration_id": "iter-c",
        "run_id": "run-c",
        "next_action": "repair_or_add_venue_expansion_archives",
        "recommended_action": "repair_or_add_venue_expansion_archives",
        "reason_codes": ["missing_okx_archive_coverage"],
        "archive_coverage_venue_expansion_gaps_parquet_path": str(venue_worklist_path),
        "venue_expansion_target_venues": ["okx"],
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    plan_item = {
        **boundary,
        "artifact_family": "rapid_strategy_iteration_sandbox_agent_action_plan_item",
        "action": "repair_preflight_blockers",
        "source_queues": ["preflight_repair_queue"],
        "reason_codes": ["missing_close_column"],
        "blocked_by_prior_action": False,
        "preflight_json_path": str(preflight_path),
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    index_payload = {
        **boundary,
        "artifact_family": "rapid_strategy_iteration_sandbox_iteration_index",
        "iteration_count": 3,
        "iteration_status_counts": {"blocked": 1, "completed": 2},
        "next_action_counts": {
            "repair_preflight_blockers": 1,
            "review_descriptor_only_strict_validation_requests": 1,
            "repair_or_add_venue_expansion_archives": 1,
        },
        "action_queue_counts": {
            "preflight_repair_queue": 1,
            "strict_validation_request_queue": 1,
            "venue_expansion_gap_queue": 1,
        },
        "action_queue_summaries": {
            "preflight_repair_queue": {
                "preflight_blocker_reason_counts": {"missing_close_column": 2}
            },
            "venue_expansion_gap_queue": {
                "archive_coverage_blocker_reason_counts": {"missing_okx_archive_coverage": 1}
            },
        },
        "action_queues": {
            "preflight_repair_queue": [action_item],
            "strict_validation_request_queue": [strict_item],
            "venue_expansion_gap_queue": [venue_item],
        },
        "agent_action_plan": [plan_item],
        "agent_action_plan_count": 1,
        "agent_action_plan_parquet_path": str(action_plan_path),
        "total_venue_expansion_actionable_gap_count": 1,
        "rows": [
            {
                "iteration_id": "iter-missing-artifact",
                "artifact_availability_status": "missing",
                "artifact_missing_count": 1,
                "artifact_missing_keys": ["agent_brief_json_path"],
            }
        ],
    }
    catalog_descriptor = {
        **boundary,
        "artifact_family": "rapid_strategy_iteration_sandbox_strict_validation_descriptor_queue_row",
        "descriptor_id": "descriptor-okx-btc",
        "venue": "okx",
        "symbol": "BTCUSDT",
        "source_trial_id": "trial-a",
        "descriptor_only": True,
        "strict_validation_executed": False,
        "strict_validation_authorized": False,
        "candidate_pack_written": False,
        "candidate_pack_write_authorized": False,
        "candidate_pack_paths": [],
    }
    catalog_payload = {
        **boundary,
        "artifact_family": "rapid_strategy_iteration_sandbox_artifact_catalog",
        "artifact_count": 1,
        "artifact_kind_counts": {"run_manifest": 1},
        "catalog_json_path": str(catalog_path),
        "catalog_sidecar_index_parquet_path": str(catalog_dir / "sandbox_artifact_catalog_sidecar_index.parquet"),
        "iteration_agent_action_plan_parquet_path": str(action_plan_path),
        "iteration_venue_expansion_gap_worklist_summary": {
            "worklist_row_count": 1,
            "target_venue_counts": {"okx": 1},
        },
        "iteration_venue_expansion_gap_worklist_parquet_path": str(venue_worklist_path),
        "iteration_venue_expansion_gap_worklist_parquet_row_count": 1,
        "iteration_venue_expansion_gap_worklist_target_venue_counts": {"okx": 1},
        "strict_validation_descriptor_queue_count": 1,
        "strict_validation_descriptor_queue": [catalog_descriptor],
        "strict_validation_descriptor_queue_parquet_path": str(strict_queue_path),
        "global_evidence_request_priority_queue": [catalog_descriptor],
        "global_evidence_request_priority_queue_parquet_path": str(
            catalog_dir / "sandbox_artifact_catalog_global_evidence_request_priority_queue.parquet"
        ),
        "global_evidence_request_source_priority_queue_parquet_path": str(
            catalog_dir / "sandbox_artifact_catalog_global_evidence_request_source_priority_queue.parquet"
        ),
        "global_top_hypotheses_parquet_path": str(global_top_path),
        "global_top_hypothesis_parquet_row_count": 2,
        "global_bucket_top_buckets_parquet_path": str(
            catalog_dir / "sandbox_artifact_catalog_global_bucket_top_buckets.parquet"
        ),
        "global_bucket_top_bucket_parquet_row_count": 1,
        "artifacts": [
            {
                "artifact_kind": "run_manifest",
                "artifact_path": str(research_root / "runs" / "run-a" / "sandbox_run_manifest.json"),
                "integrity_verification_status": "failed",
                "integrity_failed_artifact_count": 1,
                "integrity_failure_reasons": ["hash_mismatch"],
            }
        ],
    }
    index_path.write_text(json.dumps(index_payload, indent=2, sort_keys=True), encoding="utf-8")
    catalog_path.write_text(json.dumps(catalog_payload, indent=2, sort_keys=True), encoding="utf-8")
    return catalog_path, index_path


def test_next_action_dashboard_summarizes_existing_catalog_and_iteration_index(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    catalog_path, index_path = _write_next_action_dashboard_fixture(research_root)

    payload = show_sandbox_next_action(
        research_root,
        artifact_catalog_path=catalog_path,
        iteration_index_path=index_path,
        output_dir=research_root / "next_action",
    )
    discovered = show_sandbox_next_action(
        research_root,
        output_dir=research_root / "next_action_discovered",
        write_report=False,
        max_files=100,
    )
    report_json_path = Path(str(payload["report_json_path"]))
    report_parquet_path = Path(str(payload["report_parquet_path"]))
    frame = pd.read_parquet(report_parquet_path)

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["sandbox_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_evidence"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_only"] is True
    assert payload["dashboard_only"] is True
    assert payload["summarizes_existing_artifacts_only"] is True
    assert payload["evidence_recomputed"] is False
    assert payload["sandbox_sweep_executed"] is False
    assert payload["artifact_indexer_executed"] is False
    assert payload["strict_validation_executed"] is False
    assert payload["strict_validation_authorized"] is False
    assert payload["candidate_pack_written"] is False
    assert payload["candidate_pack_write_authorized"] is False
    assert payload["recommended_action"] == "repair_preflight_blockers"
    assert payload["next_recommended_packet_type"] == "preflight_repair_packet"
    assert payload["current_iteration_status"]["iteration_count"] == 3
    assert payload["current_iteration_status"]["action_queue_counts"]["preflight_repair_queue"] == 1
    assert payload["top_blockers"][0]["reason"] == "missing_close_column"
    assert payload["missing_venue_coverage"]["target_venue_counts"] == {"okx": 1}
    assert payload["highest_priority_strict_validation_descriptors"]
    assert payload["highest_priority_venue_expansion_requests"]
    assert payload["stale_or_tampered_artifact_warnings"]
    assert payload["best_hypotheses_by_source_bucket"]
    assert str(catalog_path) in payload["exact_files_to_open_next"]
    assert str(index_path) in payload["exact_files_to_open_next"]
    assert report_json_path.exists()
    assert report_parquet_path.exists()
    assert bool(frame.loc[0, "candidate_pack_written"]) is False
    assert bool(frame.loc[0, "strict_validation_executed"]) is False
    assert bool(frame.loc[0, "artifact_indexer_executed"]) is False
    assert discovered["artifact_catalog_count"] == 1
    assert discovered["iteration_index_count"] == 1


def test_next_action_dashboard_points_to_unindexed_iteration_manifest(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    iteration_dir = research_root / "iteration_smoke" / "sbxiteration-unindexed"
    iteration_dir.mkdir(parents=True)
    manifest_path = iteration_dir / "sandbox_iteration_manifest.json"
    manifest_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_agent_iteration",
        "iteration_id": "sbxiteration-unindexed",
        "iteration_status": "completed",
        "strict_validation_executed": False,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    payload = show_sandbox_next_action(
        research_root,
        output_dir=research_root / "next_action_unindexed",
        write_report=False,
        max_files=100,
    )

    assert payload["research_only"] is True
    assert payload["observe_only"] is True
    assert payload["sandbox_only"] is True
    assert payload["promotion_ready"] is False
    assert payload["candidate_evidence"] is False
    assert payload["candidate_pack_eligible"] is False
    assert payload["descriptor_only"] is True
    assert payload["dashboard_only"] is True
    assert payload["summarizes_existing_artifacts_only"] is True
    assert payload["evidence_recomputed"] is False
    assert payload["sandbox_sweep_executed"] is False
    assert payload["artifact_indexer_executed"] is False
    assert payload["strict_validation_executed"] is False
    assert payload["candidate_pack_written"] is False
    assert payload["artifact_catalog_count"] == 0
    assert payload["iteration_index_count"] == 0
    assert payload["unindexed_iteration_manifest_count"] == 1
    assert payload["unindexed_iteration_manifest_paths"] == [str(manifest_path.resolve())]
    assert payload["unindexed_iteration_manifest_paths_truncated"] is False
    assert payload["recommended_action"] == "index_rapid_strategy_sandbox_iterations"
    assert payload["next_recommended_packet_type"] == "sandbox_iteration_index_packet"
    assert payload["recommended_action_source"]["reason_codes"] == [
        "unindexed_iteration_manifests_found"
    ]
    assert str(manifest_path.resolve()) in payload["exact_files_to_open_next"]


def test_next_action_dashboard_cli_writes_contained_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    catalog_path, index_path = _write_next_action_dashboard_fixture(research_root)
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))

    payload = main._run_show_rapid_strategy_sandbox_next_action_command(
        argparse.Namespace(
            command="show-rapid-strategy-sandbox-next-action",
            output_root=None,
            artifact_catalog=[str(catalog_path)],
            iteration_index=[str(index_path)],
            output_dir="next_action_cli",
            max_files=100,
            limit=5,
            no_write_report=False,
        )
    )
    report_json_path = Path(str(payload["report_json_path"]))
    report_parquet_path = Path(str(payload["report_parquet_path"]))

    assert payload["research_only"] is True
    assert payload["candidate_pack_eligible"] is False
    assert payload["recommended_action"] == "repair_preflight_blockers"
    assert report_json_path.resolve().relative_to(research_root.resolve())
    assert report_parquet_path.resolve().relative_to(research_root.resolve())
    assert report_json_path.exists()
    assert report_parquet_path.exists()


def test_throughput_telemetry_records_iteration_runtime_and_cache(tmp_path: Path) -> None:
    input_root = tmp_path / "inputs"
    input_root.mkdir()
    catalog_root, archive_root = _write_agent_iteration_inputs(
        input_root,
        hypothesis_id="throughput-telemetry-long",
    )

    payload = run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )
    manifest = json.loads(Path(str(payload["iteration_manifest_path"])).read_text(encoding="utf-8"))
    telemetry = payload["throughput_telemetry"]
    cache_stats = telemetry["market_data_cache_stats"]
    stage_ids = {row["stage_id"] for row in telemetry["stage_timings"]}

    assert telemetry["research_only"] is True
    assert telemetry["observe_only"] is True
    assert telemetry["sandbox_only"] is True
    assert telemetry["promotion_ready"] is False
    assert telemetry["candidate_evidence"] is False
    assert telemetry["candidate_pack_eligible"] is False
    assert telemetry["strict_validation_executed"] is False
    assert telemetry["candidate_pack_written"] is False
    assert telemetry["speedup_claimed"] is False
    assert telemetry["benchmark_execution_mode"] == "single_iteration_observed_runtime"
    assert telemetry["total_runtime_seconds"] >= 0.0
    assert telemetry["memory_telemetry_available"] is True
    assert telemetry["peak_traced_memory_bytes"] >= 0
    assert cache_stats["frame_cache_miss_count"] >= 1
    assert cache_stats["frame_cache_hit_count"] >= 1
    assert cache_stats["rows_loaded_after_2024_filter"] > 0
    assert cache_stats["source_bytes_read"] > 0
    assert {"archive_coverage_matrix", "compatibility_preflight", "archive_sweep"}.issubset(stage_ids)
    assert manifest["throughput_telemetry"]["market_data_cache_stats"]["frame_cache_hit_count"] >= 1


def test_throughput_telemetry_report_summarizes_existing_iteration_manifests(tmp_path: Path) -> None:
    input_root = tmp_path / "inputs"
    input_root.mkdir()
    catalog_root, archive_root = _write_agent_iteration_inputs(
        input_root,
        hypothesis_id="throughput-report-long",
    )
    run_sandbox_agent_iteration(
        output_dir=tmp_path / "iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )

    report = summarize_sandbox_throughput(
        tmp_path / "iterations",
        output_dir=tmp_path / "throughput",
        containment_root=tmp_path,
        max_files=100,
    )
    iteration_frame = pd.read_parquet(Path(str(report["iteration_summary_parquet_path"])))
    stage_frame = pd.read_parquet(Path(str(report["stage_summary_parquet_path"])))

    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["sandbox_only"] is True
    assert report["promotion_ready"] is False
    assert report["candidate_evidence"] is False
    assert report["candidate_pack_eligible"] is False
    assert report["descriptor_only"] is True
    assert report["report_only"] is True
    assert report["sandbox_sweep_executed"] is False
    assert report["strict_validation_executed"] is False
    assert report["candidate_pack_written"] is False
    assert report["speedup_claimed"] is False
    assert report["summary"]["iteration_count"] == 1
    assert report["summary"]["telemetry_iteration_count"] == 1
    assert report["summary"]["missing_telemetry_count"] == 0
    assert report["summary"]["bottleneck_ranking"]
    assert Path(str(report["report_json_path"])).exists()
    assert set(iteration_frame["telemetry_status"]) == {"present"}
    assert set(stage_frame["candidate_pack_eligible"]) == {False}


def test_throughput_telemetry_cli_writes_contained_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tradingbotsuite import main

    research_root = tmp_path / "research"
    input_root = tmp_path / "inputs"
    input_root.mkdir()
    monkeypatch.setenv("TBS_RESEARCH_OUTPUT_DIR", str(research_root))
    catalog_root, archive_root = _write_agent_iteration_inputs(
        input_root,
        hypothesis_id="throughput-cli-long",
    )
    run_sandbox_agent_iteration(
        output_dir=research_root / "agent_iterations",
        catalog_roots=[catalog_root],
        archive_roots=[archive_root],
        archive_venue="okx",
        archive_symbol="BTCUSDT",
        archive_data_family="kline",
        archive_interval="1h",
        window_start="2024-03-01",
        window_end="2024-03-02",
        holding_periods=(1,),
        round_trip_cost_bps=0.0,
        min_trades=1,
        max_evidence_requests=3,
    )

    payload = main._run_summarize_rapid_strategy_sandbox_throughput_command(
        argparse.Namespace(
            command="summarize-rapid-strategy-sandbox-throughput",
            root_dir="agent_iterations",
            output_dir="throughput",
            max_files=100,
            limit=5,
            no_write_report=False,
        )
    )
    report_json_path = Path(str(payload["report_json_path"]))
    iteration_parquet_path = Path(str(payload["iteration_summary_parquet_path"]))

    assert payload["research_only"] is True
    assert payload["candidate_pack_eligible"] is False
    assert payload["summary"]["telemetry_iteration_count"] == 1
    assert report_json_path.resolve().relative_to(research_root.resolve())
    assert iteration_parquet_path.resolve().relative_to(research_root.resolve())
    assert report_json_path.exists()
    assert iteration_parquet_path.exists()
