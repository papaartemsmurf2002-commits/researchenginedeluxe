from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.core.models import Bar
from tradingbotsuite.persistence.sqlite_store import SQLiteStore
from tradingbotsuite.research.archive_sources import (
    ARCHIVE_SOURCE_CONTRACT_VERSION,
    SUPPORTED_ARCHIVE_SOURCES,
    archive_source_descriptors,
    assert_valid_archive_source_manifest,
    get_archive_source_descriptor,
    get_normalized_field_contract,
)
from tradingbotsuite.research.config import load_research_plan
from tradingbotsuite.research.data_quality import build_manifest_data_quality_report
from tradingbotsuite.research.dataset import ResearchDatasetBuilder
from tradingbotsuite.research.hmm_knn import run_hmm_knn_research
from tradingbotsuite.research.hmm_knn_experiments import run_hmm_knn_experiment_matrix
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research.market_data import ingest_binance_vision_archive
from tradingbotsuite.research.market_journal import MarketJournalWriter

DATA_PIPELINE_MANIFEST_VERSION = "v2-hmm-knn-provider-data-pipeline-1"
DATA_PIPELINE_DEFAULT_STAGE = "intake"
DATA_PIPELINE_STAGES = ("intake", "dataset", "evidence", "all")
IMPLEMENTED_LOCAL_INGESTION_PROVIDERS = frozenset({"binance_vision"})


@dataclass(frozen=True, slots=True)
class ResearchDataPipelineResult:
    output_dir: Path
    intake_manifest_path: Path
    data_quality_report_path: Path
    market_journal_manifest_path: Path
    dataset_manifest_path: Path | None
    evidence_manifest_path: Path | None


class ArchiveBackedResearchClient:
    """Research-only client backed by normalized local archive manifests."""

    def __init__(self, archive_manifests: list[Mapping[str, Any]]) -> None:
        self.archive_manifests = [dict(manifest) for manifest in archive_manifests]
        self._bars: dict[tuple[str, str], list[Bar]] = {}
        self._contexts: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._load()

    async def fetch_historical_closed_bar_range(
        self,
        symbol: str,
        *,
        start_time_ms: int,
        end_time_ms: int,
        interval: str = "15m",
    ) -> list[Bar]:
        key = (symbol.strip().upper(), interval)
        bars = self._bars.get(key, [])
        return [
            bar
            for bar in bars
            if int(start_time_ms) <= int(bar.time_ms) <= int(end_time_ms)
        ]

    async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8) -> dict[str, Any]:
        row = self._latest_context_row(symbol, "funding_rate", as_of_ms)
        if row is None:
            return _missing_context("funding_context")
        return {
            "funding_rate": row.get("funding_rate"),
            "funding_rate_change": row.get("funding_rate_change"),
            "time_to_next_funding_ms": row.get("time_to_next_funding_ms"),
            "missing_funding_context": False,
            "context_source": "archive_backed_research_client",
        }

    async def fetch_open_interest_context(
        self,
        symbol: str,
        *,
        as_of_ms: int,
        period: str = "5m",
        lookback_points: int = 13,
    ) -> dict[str, Any]:
        row = self._latest_context_row(symbol, "open_interest", as_of_ms)
        if row is None:
            return _missing_context("open_interest_context")
        return {
            "open_interest": row.get("open_interest"),
            "open_interest_change": row.get("open_interest_change"),
            "open_interest_change_pct": row.get("open_interest_change_pct"),
            "open_interest_value": row.get("open_interest_value") or row.get("open_interest_value_usd"),
            "missing_open_interest_context": False,
            "context_source": "archive_backed_research_client",
        }

    async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m") -> dict[str, Any]:
        row = self._latest_context_row(symbol, "premium_index", as_of_ms)
        if row is None:
            return _missing_context("premium_context")
        return {
            "mark_price": row.get("mark_price"),
            "index_price": row.get("index_price"),
            "basis": row.get("basis"),
            "basis_rate": row.get("basis_rate") or row.get("premium_index"),
            "premium_close": row.get("premium_close") or row.get("premium_index"),
            "missing_premium_context": False,
            "context_source": "archive_backed_research_client",
        }

    def coverage_summary(self) -> dict[str, Any]:
        return {
            "bar_series": {
                f"{symbol}:{interval}": len(bars)
                for (symbol, interval), bars in sorted(self._bars.items())
            },
            "context_series": {
                f"{symbol}:{family}": len(rows)
                for (symbol, family), rows in sorted(self._contexts.items())
            },
        }

    def _load(self) -> None:
        for manifest in self.archive_manifests:
            data_path = manifest.get("data_path")
            if not data_path:
                continue
            path = Path(str(data_path))
            if not path.exists():
                continue
            family = str(manifest.get("data_family") or "").strip()
            symbol = str(manifest.get("symbol") or "").strip().upper()
            rows = _read_jsonl(path)
            if family == "kline":
                interval = str(manifest.get("interval") or "15m")
                bars = [_bar_from_archive_row(row) for row in rows]
                self._bars.setdefault((symbol, interval), []).extend(bars)
                self._bars[(symbol, interval)] = sorted(
                    self._bars[(symbol, interval)],
                    key=lambda bar: int(bar.time_ms),
                )
            elif family in {"funding_rate", "open_interest", "premium_index"}:
                context_rows = sorted(rows, key=lambda row: int(row["event_time_ms"]))
                self._contexts.setdefault((symbol, family), []).extend(context_rows)
                self._contexts[(symbol, family)] = sorted(
                    self._contexts[(symbol, family)],
                    key=lambda row: int(row["event_time_ms"]),
                )

    def _latest_context_row(self, symbol: str, family: str, as_of_ms: int) -> dict[str, Any] | None:
        rows = self._contexts.get((symbol.strip().upper(), family), [])
        candidates = [row for row in rows if int(row.get("event_time_ms", -1)) <= int(as_of_ms)]
        return candidates[-1] if candidates else None


def archive_provider_descriptors() -> tuple[dict[str, Any], ...]:
    return tuple(_descriptor_payload(descriptor) for descriptor in archive_source_descriptors())


def prepare_hmm_knn_research_data(
    *,
    spec_path: Path,
    stage: str = DATA_PIPELINE_DEFAULT_STAGE,
    app_config: AppConfig | None = None,
) -> ResearchDataPipelineResult:
    if stage not in DATA_PIPELINE_STAGES:
        raise ValueError(f"stage must be one of: {', '.join(DATA_PIPELINE_STAGES)}")
    spec_path = Path(spec_path)
    spec = _read_json(spec_path)
    output_dir = Path(str(spec.get("output_dir") or Path("data/research") / str(spec["version"])))
    output_dir.mkdir(parents=True, exist_ok=True)

    run_intake = stage in {"intake", "dataset", "evidence", "all"}
    run_dataset = stage in {"dataset", "evidence", "all"}
    run_evidence = stage in {"evidence", "all"}

    provider_records: list[dict[str, Any]] = []
    archive_manifests: list[dict[str, Any]] = []
    archive_manifest_paths: list[Path] = []
    journal_manifest: dict[str, Any] | None = None
    dataset_manifest_path: Path | None = None
    evidence_manifest_path: Path | None = None
    stage_status: dict[str, dict[str, Any]] = {
        "intake": {"status": "not_requested"},
        "dataset": {"status": "not_requested"},
        "evidence": {"status": "not_requested"},
    }

    if run_intake:
        intake_result = _run_intake_stage(spec, spec_path=spec_path, output_dir=output_dir)
        provider_records = intake_result["provider_records"]
        archive_manifests = intake_result["archive_manifests"]
        archive_manifest_paths = intake_result["archive_manifest_paths"]
        journal_manifest = intake_result["journal_manifest"]
        stage_status["intake"] = intake_result["stage_status"]

    data_quality_inputs = list(archive_manifests)
    if journal_manifest is not None:
        data_quality_inputs.append(journal_manifest)

    if data_quality_inputs:
        data_quality_report = build_manifest_data_quality_report(data_quality_inputs)
    else:
        data_quality_report = {
            "data_quality_report_version": "v2-archive-market-data-quality-report-1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "manifest_count": 0,
            "alerts": [],
            "manifest_summaries": [],
        }
    data_quality_report_path = output_dir / "data_quality_report.json"
    data_quality_report_path.write_text(_canonical_json(data_quality_report, indent=2) + "\n", encoding="utf-8")

    if run_dataset:
        dataset_result = _run_dataset_stage(
            spec,
            output_dir=output_dir,
            app_config=app_config or AppConfig.from_env(),
            archive_manifests=archive_manifests,
        )
        dataset_manifest_path = dataset_result.get("dataset_manifest_path")
        stage_status["dataset"] = dataset_result["stage_status"]

    if run_evidence:
        evidence_result = _run_evidence_stage(
            spec,
            output_dir=output_dir,
            dataset_manifest_path=dataset_manifest_path,
        )
        evidence_manifest_path = evidence_result.get("evidence_manifest_path")
        stage_status["evidence"] = evidence_result["stage_status"]

    intake_manifest = {
        "data_pipeline_manifest_version": DATA_PIPELINE_MANIFEST_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "version": str(spec["version"]),
        "spec_path": str(spec_path),
        "spec_sha256": _hash_file(spec_path),
        "stage_requested": stage,
        "asset_scope": list(spec.get("asset_scope") or []),
        "output_dir": str(output_dir),
        "provider_descriptors": archive_provider_descriptors(),
        "providers": provider_records,
        "archive_manifest_paths": [str(path) for path in archive_manifest_paths],
        "market_journal_manifest_path": str(output_dir / "market_journal_manifest.json"),
        "data_quality_report_path": str(data_quality_report_path),
        "dataset_manifest_path": str(dataset_manifest_path) if dataset_manifest_path is not None else None,
        "evidence_manifest_path": str(evidence_manifest_path) if evidence_manifest_path is not None else None,
        "stage_status": stage_status,
    }
    intake_manifest_path = output_dir / "data_intake_manifest.json"
    intake_manifest_path.write_text(_canonical_json(intake_manifest, indent=2) + "\n", encoding="utf-8")

    return ResearchDataPipelineResult(
        output_dir=output_dir,
        intake_manifest_path=intake_manifest_path,
        data_quality_report_path=data_quality_report_path,
        market_journal_manifest_path=output_dir / "market_journal_manifest.json",
        dataset_manifest_path=dataset_manifest_path,
        evidence_manifest_path=evidence_manifest_path,
    )


def _run_intake_stage(spec: Mapping[str, Any], *, spec_path: Path, output_dir: Path) -> dict[str, Any]:
    provider_records: list[dict[str, Any]] = []
    archive_manifests: list[dict[str, Any]] = []
    archive_manifest_paths: list[Path] = []

    providers = spec.get("providers") or []
    if not isinstance(providers, list):
        raise ValueError("providers must be a list")

    archive_output_dir = output_dir / "archives"
    for provider in providers:
        if not isinstance(provider, Mapping):
            raise ValueError("provider entries must be objects")
        source_name = str(provider.get("source_name") or provider.get("name") or "").strip()
        if not source_name:
            raise ValueError("provider source_name is required")
        descriptor = get_archive_source_descriptor(source_name)
        enabled = bool(provider.get("enabled", True))
        record = {
            "source_name": source_name,
            "source_type": descriptor.source_type,
            "enabled": enabled,
            "implemented_for_ingestion": source_name in IMPLEMENTED_LOCAL_INGESTION_PROVIDERS,
            "input_count": len(provider.get("inputs") or []),
            "status": "disabled" if not enabled else "pending",
            "manifest_paths": [],
        }
        if not enabled:
            provider_records.append(record)
            continue
        if source_name != "binance_vision":
            manifest_path = _write_not_implemented_provider_manifest(
                provider,
                descriptor=descriptor,
                output_dir=output_dir / "providers" / source_name,
            )
            manifest = _read_json(manifest_path)
            archive_manifests.append(manifest)
            archive_manifest_paths.append(manifest_path)
            record["status"] = "not_implemented_for_ingestion"
            record["manifest_paths"] = [str(manifest_path)]
            provider_records.append(record)
            continue
        inputs = provider.get("inputs") or []
        if not inputs:
            record["status"] = "no_inputs"
            provider_records.append(record)
            continue
        for input_index, input_payload in enumerate(inputs):
            if not isinstance(input_payload, Mapping):
                raise ValueError("provider inputs must be objects")
            result = ingest_binance_vision_archive(
                _resolve_path(input_payload["path"], base_path=spec_path.parent),
                symbol=str(input_payload.get("symbol") or (spec.get("asset_scope") or ["BTCUSDT"])[0]),
                data_family=str(input_payload["data_family"]),
                interval=input_payload.get("interval"),
                output_dir=archive_output_dir,
                strict=bool(input_payload.get("strict", False)),
            )
            manifest = _read_json(result.manifest_path)
            assert_valid_archive_source_manifest(manifest)
            archive_manifests.append(manifest)
            archive_manifest_paths.append(result.manifest_path)
            record["manifest_paths"].append(str(result.manifest_path))
            record.setdefault("inputs", []).append(
                {
                    "input_index": input_index,
                    "path": str(input_payload["path"]),
                    "manifest_path": str(result.manifest_path),
                    "row_count": result.row_count,
                    "gap_count": result.gap_count,
                    "duplicate_count": result.duplicate_count,
                }
            )
        record["status"] = "completed"
        provider_records.append(record)

    journal_manifest = _write_market_journal_from_archives(
        archive_manifests,
        journal_path=output_dir / "market_journal.jsonl",
        manifest_path=output_dir / "market_journal_manifest.json",
    )
    stage_status = {
        "status": "completed",
        "provider_count": len(provider_records),
        "archive_manifest_count": len(archive_manifest_paths),
        "journal_event_count": int(journal_manifest.get("event_count", 0)),
    }
    return {
        "provider_records": provider_records,
        "archive_manifests": archive_manifests,
        "archive_manifest_paths": archive_manifest_paths,
        "journal_manifest": journal_manifest,
        "stage_status": stage_status,
    }


def _run_dataset_stage(
    spec: Mapping[str, Any],
    *,
    output_dir: Path,
    app_config: AppConfig,
    archive_manifests: list[Mapping[str, Any]],
) -> dict[str, Any]:
    dataset_spec = spec.get("dataset_stage") or {}
    if not dataset_spec or not bool(dataset_spec.get("enabled", False)):
        return {"stage_status": {"status": "skipped", "reason": "dataset_stage_disabled"}}
    research_config = Path(str(dataset_spec.get("research_config") or "configs/v2_btc_research.json"))
    db_path = Path(str(dataset_spec.get("db_path") or app_config.db_path))
    config = replace(
        app_config,
        db_path=db_path,
        research=replace(app_config.research, output_dir=output_dir / "dataset", config_path=research_config),
    )
    try:
        result = asyncio.run(_build_dataset_with_archive_client(config, archive_manifests))
    except Exception as exc:
        return {
            "stage_status": {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        }
    return {
        "dataset_manifest_path": result.manifest_path,
        "stage_status": {
            "status": "completed",
            "dataset_path": str(result.dataset_path),
            "dataset_manifest_path": str(result.manifest_path),
            "row_count": result.row_count,
            "archive_client_coverage": ArchiveBackedResearchClient(archive_manifests).coverage_summary(),
        },
    }


async def _build_dataset_with_archive_client(config: AppConfig, archive_manifests: list[Mapping[str, Any]]) -> Any:
    plan = load_research_plan(config.research.config_path)
    store = SQLiteStore(config.db_path)
    client = ArchiveBackedResearchClient(archive_manifests)
    builder = ResearchDatasetBuilder(config=config, plan=plan, store=store, candle_client=client)  # type: ignore[arg-type]
    return await builder.build()


def _run_evidence_stage(
    spec: Mapping[str, Any],
    *,
    output_dir: Path,
    dataset_manifest_path: Path | None,
) -> dict[str, Any]:
    evidence_spec = spec.get("evidence_stage") or {}
    if not evidence_spec or not bool(evidence_spec.get("enabled", False)):
        return {"stage_status": {"status": "skipped", "reason": "evidence_stage_disabled"}}
    dataset_path = _dataset_path_from_manifest(dataset_manifest_path)
    if dataset_path is None:
        explicit_dataset = evidence_spec.get("dataset_path")
        dataset_path = Path(str(explicit_dataset)) if explicit_dataset else None
    if dataset_path is None or not dataset_path.exists():
        return {"stage_status": {"status": "skipped", "reason": "dataset_not_available"}}
    try:
        if evidence_spec.get("experiment_spec"):
            result = run_hmm_knn_experiment_matrix(
                spec_path=Path(str(evidence_spec["experiment_spec"])),
                dataset_path=dataset_path,
                output_dir=output_dir / "evidence" / "experiments",
                max_workers=int(evidence_spec.get("workers", 1)),
                write_monitoring=bool(evidence_spec.get("write_monitoring", True)),
            )
            return {
                "evidence_manifest_path": result.manifest_path,
                "stage_status": {
                    "status": "completed",
                    "mode": "experiment_matrix",
                    "manifest_path": str(result.manifest_path),
                    "summary_path": str(result.summary_path),
                },
            }
        result = run_hmm_knn_research(
            config_path=Path(str(evidence_spec.get("hmm_knn_config") or "configs/v2_btc_hmm_multi_knn_research.json")),
            dataset_path=dataset_path,
            output_dir=output_dir / "evidence",
        )
    except Exception as exc:
        return {
            "stage_status": {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        }
    return {
        "evidence_manifest_path": result.artifact_manifest_path,
        "stage_status": {
            "status": "completed",
            "mode": "hmm_knn_research",
            "manifest_path": str(result.artifact_manifest_path),
            "metrics_path": str(result.metrics_path),
        },
    }


def _write_market_journal_from_archives(
    archive_manifests: list[Mapping[str, Any]],
    *,
    journal_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    if journal_path.exists():
        journal_path.unlink()
    writer = MarketJournalWriter(journal_path, manifest_path=manifest_path)
    appended = 0
    for manifest in archive_manifests:
        data_path = manifest.get("data_path")
        if not data_path:
            continue
        source_name = str(manifest.get("source_name") or "missing")
        symbol = str(manifest.get("symbol") or "BTCUSDT")
        family = str(manifest.get("data_family") or "trade")
        for row in _read_jsonl(Path(str(data_path))):
            event_time_ms = row.get("event_time_ms")
            if event_time_ms is None:
                continue
            writer.append(
                raw_payload=row.get("raw_payload") if isinstance(row.get("raw_payload"), Mapping) else row,
                normalized_payload={**row, "source_name": source_name, "symbol": symbol, "data_family": family},
                source_event_time_ms=int(event_time_ms),
                local_receive_time_ms=_int_or_none(row.get("receive_time_ms") or row.get("local_receive_time_ms")),
                source_name=source_name,
                symbol=symbol,
                data_family=family,
                source_row_index=appended,
            )
            appended += 1
    if not journal_path.exists():
        journal_path.write_text("", encoding="utf-8")
    return writer.write_manifest(strict=False)


def _write_not_implemented_provider_manifest(
    provider: Mapping[str, Any],
    *,
    descriptor: Any,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    symbol = str(provider.get("symbol") or "BTCUSDT").upper()
    family = str(provider.get("data_family") or descriptor.likely_data_families[0])
    contract = get_normalized_field_contract(family)
    manifest = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_name": descriptor.source_name,
        "source_type": descriptor.source_type,
        "symbol": symbol,
        "data_family": family,
        "start_time_ms": 0,
        "end_time_ms": 1,
        "row_count": 0,
        "event_time_field": "event_time_ms",
        "receive_time_unavailable_reason": "Provider ingestion is not implemented in this local research pipeline pass.",
        "schema_version": ARCHIVE_SOURCE_CONTRACT_VERSION,
        "content_hash": _hash_payload(
            {
                "source_name": descriptor.source_name,
                "status": "not_implemented_for_ingestion",
            }
        ),
        "normalized_fields": [],
        "schema_fields": [],
        "missing_fields": list(contract.required_fields),
        "zero_filled_fields": [],
        "ingestion_status": "not_implemented_for_ingestion",
        "diagnostic_only": True,
        "non_promotable_notes": [
            "Provider contract is registered, but local ingestion is not implemented in this pass.",
            "No rows were read, downloaded, synthesized, or promoted.",
        ],
    }
    path = output_dir / f"{descriptor.source_name}_not_implemented.manifest.json"
    path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def _dataset_path_from_manifest(dataset_manifest_path: Path | None) -> Path | None:
    if dataset_manifest_path is None or not dataset_manifest_path.exists():
        return None
    manifest = _read_json(dataset_manifest_path)
    value = manifest.get("dataset_path")
    return Path(str(value)) if value else None


def _bar_from_archive_row(row: Mapping[str, Any]) -> Bar:
    return Bar(
        time_ms=int(row.get("open_time_ms") or row["event_time_ms"]),
        open=Decimal(str(row["open_price"])),
        high=Decimal(str(row["high_price"])),
        low=Decimal(str(row["low_price"])),
        close=Decimal(str(row["close_price"])),
        volume=Decimal(str(row.get("volume") or "0")),
    )


def _missing_context(context_name: str) -> dict[str, Any]:
    return {
        f"missing_{context_name}": True,
        "context_source": "archive_backed_research_client",
        "unavailable_reason": "No point-in-time local archive rows were available at or before as_of_ms.",
    }


def _descriptor_payload(descriptor: Any) -> dict[str, Any]:
    return {
        "source_name": descriptor.source_name,
        "source_type": descriptor.source_type,
        "display_name": descriptor.display_name,
        "asset_scope": list(descriptor.asset_scope),
        "symbol_scope": list(descriptor.symbol_scope),
        "likely_data_families": list(descriptor.likely_data_families),
        "promotional_eligible_by_default": descriptor.promotional_eligible_by_default,
        "diagnostic_only_by_default": descriptor.diagnostic_only_by_default,
        "implemented_for_ingestion": descriptor.source_name in IMPLEMENTED_LOCAL_INGESTION_PROVIDERS,
    }


def _resolve_path(path: Any, *, base_path: Path) -> Path:
    candidate = Path(str(path))
    if candidate.is_absolute():
        return candidate
    return (base_path / candidate).resolve()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(payload)
    return rows


def _hash_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _hash_payload(payload: Any) -> str:
    return f"sha256:{sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":") if indent is None else None,
        indent=indent,
        ensure_ascii=True,
        default=str,
    )


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
