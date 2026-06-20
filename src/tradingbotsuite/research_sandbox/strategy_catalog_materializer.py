from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbotsuite.research_sandbox.boundary import (
    SANDBOX_BOUNDARY_FLAGS,
    require_sandbox_boundary,
    sandbox_boundary_metadata,
)
from tradingbotsuite.research_sandbox.discovery import bounded_discover_files
from tradingbotsuite.research_sandbox.identity import digest_payload
from tradingbotsuite.research_sandbox.intake import (
    RECOGNIZED_STRATEGY_CATALOG_SUFFIXES,
    load_strategy_catalog_with_diagnostics,
)
from tradingbotsuite.research_sandbox.spec import StrategyCatalogRow
from tradingbotsuite.research_sandbox.strategy_blueprints import BLUEPRINT_PARAM_KEY


MATERIALIZED_STRATEGY_CATALOG_JSON_NAME = "strategy_catalog.json"
MATERIALIZED_STRATEGY_CATALOG_PARQUET_NAME = "strategy_catalog.parquet"
STRATEGY_CATALOG_BUILD_REPORT_JSON_NAME = "strategy_catalog_build_report.json"
STRATEGY_CATALOG_BUILD_REPORT_PARQUET_NAME = "strategy_catalog_build_report.parquet"

SUPPORTED_STRATEGY_CATALOG_SUFFIXES = RECOGNIZED_STRATEGY_CATALOG_SUFFIXES


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_for_parquet(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            row[key] = json.dumps(value, sort_keys=True, default=_json_default)
        else:
            row[key] = value
    return row


def _as_roots(catalog_roots: str | Path | Sequence[str | Path]) -> list[Path]:
    if isinstance(catalog_roots, (str, Path)):
        return [Path(catalog_roots)]
    return [Path(root) for root in catalog_roots]


def _iter_sources(roots: Iterable[Path], *, max_files: int) -> tuple[list[Path], bool]:
    return bounded_discover_files(
        roots,
        max_files=max_files,
        missing_root_message="sandbox strategy catalog root not found",
    )


def _blueprint_ids(strategies: list[StrategyCatalogRow]) -> list[str]:
    ids = {
        str(strategy.params[BLUEPRINT_PARAM_KEY])
        for strategy in strategies
        if strategy.params.get(BLUEPRINT_PARAM_KEY) is not None
    }
    return sorted(ids)


def _source_row(
    path: Path,
    *,
    status: str,
    strategies: list[StrategyCatalogRow],
    skip_reasons: list[str],
    source_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_strategy_catalog_build_row",
        "source_path": str(path),
        "source_suffix": path.suffix.lower(),
        "status": status,
        "skip_reasons": skip_reasons,
        "strategy_count": len(strategies),
        "hypothesis_ids": sorted({strategy.hypothesis_id for strategy in strategies}),
        "families": sorted({strategy.family for strategy in strategies}),
        "source_ids": sorted({strategy.source_id for strategy in strategies}),
        "signal_columns": sorted({strategy.signal_column for strategy in strategies}),
        "sides": sorted({strategy.side for strategy in strategies}),
        "blueprint_ids": _blueprint_ids(strategies),
    }
    if source_diagnostics:
        row.update(source_diagnostics)
    require_sandbox_boundary(row, payload_name="sandbox_strategy_catalog_build_row")
    return row


def _catalog_counts(strategies: list[StrategyCatalogRow]) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    family_counts: dict[str, int] = {}
    side_counts: dict[str, int] = {}
    blueprint_counts: dict[str, int] = {}
    for strategy in strategies:
        family_counts[strategy.family] = family_counts.get(strategy.family, 0) + 1
        side_counts[strategy.side] = side_counts.get(strategy.side, 0) + 1
        blueprint_id = strategy.params.get(BLUEPRINT_PARAM_KEY)
        if blueprint_id is not None:
            key = str(blueprint_id)
            blueprint_counts[key] = blueprint_counts.get(key, 0) + 1
    return dict(sorted(family_counts.items())), dict(sorted(side_counts.items())), dict(sorted(blueprint_counts.items()))


def materialize_sandbox_strategy_catalog(
    catalog_roots: str | Path | Sequence[str | Path],
    *,
    output_dir: str | Path,
    max_files: int = 5000,
) -> dict[str, Any]:
    roots = _as_roots(catalog_roots)
    sources, truncated = _iter_sources(roots, max_files=max_files)
    all_strategies: list[StrategyCatalogRow] = []
    source_rows: list[dict[str, Any]] = []
    for source in sources:
        resolved = source.resolve()
        if resolved.suffix.lower() not in SUPPORTED_STRATEGY_CATALOG_SUFFIXES:
            source_rows.append(_source_row(resolved, status="skipped", strategies=[], skip_reasons=["unsupported_suffix"]))
            continue
        try:
            strategies, source_diagnostics = load_strategy_catalog_with_diagnostics(resolved)
        except Exception as exc:  # noqa: BLE001 - materializer reports bad sources without stopping the batch.
            source_rows.append(
                _source_row(
                    resolved,
                    status="skipped",
                    strategies=[],
                    skip_reasons=[f"load_error:{type(exc).__name__}:{exc}"],
                )
            )
            continue
        all_strategies.extend(strategies)
        source_rows.append(
            _source_row(
                resolved,
                status="included",
                strategies=strategies,
                skip_reasons=[],
                source_diagnostics=source_diagnostics,
            )
        )

    strategy_payloads = [strategy.to_payload() for strategy in all_strategies]
    for payload in strategy_payloads:
        require_sandbox_boundary(payload, payload_name="sandbox_materialized_strategy_row")
    family_counts, side_counts, blueprint_counts = _catalog_counts(all_strategies)
    catalog_id = digest_payload(
        {
            "catalog_roots": [str(root.resolve()) for root in roots],
            "max_files": max_files,
            "strategies": strategy_payloads,
            "skipped": [
                {
                    "source_path": row["source_path"],
                    "skip_reasons": row["skip_reasons"],
                }
                for row in source_rows
                if row["status"] == "skipped"
            ],
        },
        prefix="sbxstrategycatalog",
        length=24,
    )
    destination = Path(output_dir) / catalog_id
    destination.mkdir(parents=True, exist_ok=True)
    catalog_json_path = destination / MATERIALIZED_STRATEGY_CATALOG_JSON_NAME
    catalog_parquet_path = destination / MATERIALIZED_STRATEGY_CATALOG_PARQUET_NAME
    report_json_path = destination / STRATEGY_CATALOG_BUILD_REPORT_JSON_NAME
    report_parquet_path = destination / STRATEGY_CATALOG_BUILD_REPORT_PARQUET_NAME

    catalog_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_strategy_catalog",
        "catalog_id": catalog_id,
        "catalog_roots": [str(root.resolve()) for root in roots],
        "strategy_count": len(strategy_payloads),
        "family_counts": family_counts,
        "side_counts": side_counts,
        "blueprint_counts": blueprint_counts,
        "strategy_catalog_json_path": str(catalog_json_path),
        "strategy_catalog_parquet_path": str(catalog_parquet_path),
        "build_report_json_path": str(report_json_path),
        "build_report_parquet_path": str(report_parquet_path),
        "strategies": strategy_payloads,
    }
    require_sandbox_boundary(catalog_payload, payload_name="sandbox_materialized_strategy_catalog")

    report_payload = {
        **sandbox_boundary_metadata(),
        "artifact_family": "rapid_strategy_iteration_sandbox_strategy_catalog_build_report",
        "catalog_id": catalog_id,
        "catalog_roots": [str(root.resolve()) for root in roots],
        "output_dir": str(destination),
        "strategy_catalog_json_path": str(catalog_json_path),
        "strategy_catalog_parquet_path": str(catalog_parquet_path),
        "build_report_json_path": str(report_json_path),
        "build_report_parquet_path": str(report_parquet_path),
        "file_count": len(sources),
        "source_count": len(source_rows),
        "included_source_count": sum(1 for row in source_rows if row["status"] == "included"),
        "skipped_source_count": sum(1 for row in source_rows if row["status"] == "skipped"),
        "strategy_count": len(strategy_payloads),
        "family_counts": family_counts,
        "side_counts": side_counts,
        "blueprint_counts": blueprint_counts,
        "max_files": max_files,
        "truncated": truncated,
        "sources": source_rows,
        "strategies": strategy_payloads,
    }
    require_sandbox_boundary(report_payload, payload_name="sandbox_strategy_catalog_build_report")

    catalog_frame = pd.DataFrame([_row_for_parquet(strategy) for strategy in strategy_payloads])
    if catalog_frame.empty:
        catalog_frame = pd.DataFrame(columns=["hypothesis_id", "family", "signal_column", *SANDBOX_BOUNDARY_FLAGS])
    catalog_frame.to_parquet(catalog_parquet_path, index=False)
    report_frame = pd.DataFrame([_row_for_parquet(row) for row in source_rows])
    if report_frame.empty:
        report_frame = pd.DataFrame(columns=["source_path", "status", *SANDBOX_BOUNDARY_FLAGS])
    report_frame.to_parquet(report_parquet_path, index=False)
    catalog_json_path.write_text(
        json.dumps(catalog_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    report_json_path.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return report_payload
