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
from tradingbotsuite.research.hmm_knn_monitoring import monitor_hmm_knn_artifact
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research.market_data import (
    download_and_ingest_binance_vision_archive,
    fetch_crypto_lake_archive,
    ingest_binance_vision_archive,
    ingest_crypto_lake_archive,
)
from tradingbotsuite.research.market_journal import MarketJournalWriter

DATA_PIPELINE_MANIFEST_VERSION = "v2-hmm-knn-provider-data-pipeline-1"
DATA_PIPELINE_SUMMARY_VERSION = "v2-hmm-knn-provider-data-pipeline-summary-1"
DATA_PIPELINE_DEFAULT_STAGE = "intake"
DATA_PIPELINE_STAGES = ("intake", "dataset", "evidence", "all")
IMPLEMENTED_LOCAL_INGESTION_PROVIDERS = frozenset({"binance_vision", "crypto_lake"})


@dataclass(frozen=True, slots=True)
class ResearchDataPipelineResult:
    output_dir: Path
    intake_manifest_path: Path
    data_quality_report_path: Path
    market_journal_manifest_path: Path
    pipeline_summary_path: Path
    dataset_manifest_path: Path | None
    evidence_manifest_path: Path | None


@dataclass(frozen=True, slots=True)
class ProviderInputSpec:
    path: str | None
    symbol: str | None
    data_family: str
    interval: str | None = None
    strict: bool = False
    extra: Mapping[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, provider_name: str, input_index: int) -> ProviderInputSpec:
        if not isinstance(payload, Mapping):
            raise ValueError(f"provider {provider_name} input {input_index} must be an object")
        path = str(payload.get("path") or "").strip() or None
        has_fetch_or_download = bool(payload.get("fetch") or payload.get("download") or payload.get("period"))
        if path is None and not has_fetch_or_download:
            raise ValueError(f"provider {provider_name} input {input_index} path or fetch/download parameters are required")
        family = str(payload.get("data_family") or "").strip()
        if not family:
            raise ValueError(f"provider {provider_name} input {input_index} data_family is required")
        symbol = str(payload.get("symbol")).strip().upper() if payload.get("symbol") is not None else None
        interval = str(payload.get("interval")).strip() if payload.get("interval") is not None else None
        passthrough_keys = {
            key: value
            for key, value in payload.items()
            if key not in {"path", "symbol", "data_family", "interval", "strict"}
        }
        return cls(path=path, symbol=symbol or None, data_family=family, interval=interval or None, strict=bool(payload.get("strict", False)), extra=passthrough_keys)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "data_family": self.data_family,
            "strict": self.strict,
        }
        if self.extra:
            payload.update(dict(self.extra))
        if self.path is not None:
            payload["path"] = self.path
        if self.symbol is not None:
            payload["symbol"] = self.symbol
        if self.interval is not None:
            payload["interval"] = self.interval
        return payload


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    source_name: str
    enabled: bool
    inputs: tuple[ProviderInputSpec, ...]
    symbol: str | None = None
    data_family: str | None = None
    extra: Mapping[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, index: int) -> ProviderSpec:
        if not isinstance(payload, Mapping):
            raise ValueError(f"provider {index} must be an object")
        source_name = str(payload.get("source_name") or payload.get("name") or "").strip()
        if not source_name:
            raise ValueError(f"provider {index} source_name is required")
        get_archive_source_descriptor(source_name)
        raw_inputs = payload.get("inputs") or []
        if not isinstance(raw_inputs, list):
            raise ValueError(f"provider {source_name} inputs must be a list")
        inputs = tuple(
            ProviderInputSpec.from_payload(input_payload, provider_name=source_name, input_index=input_index)
            for input_index, input_payload in enumerate(raw_inputs)
        )
        symbol = str(payload.get("symbol")).strip().upper() if payload.get("symbol") is not None else None
        data_family = str(payload.get("data_family")).strip() if payload.get("data_family") is not None else None
        passthrough_keys = {
            key: value
            for key, value in payload.items()
            if key not in {"source_name", "name", "enabled", "inputs", "symbol", "data_family"}
        }
        return cls(
            source_name=source_name,
            enabled=bool(payload.get("enabled", True)),
            inputs=inputs,
            symbol=symbol or None,
            data_family=data_family or None,
            extra=passthrough_keys,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = dict(self.extra or {})
        payload.update(
            {
                "source_name": self.source_name,
                "enabled": self.enabled,
                "inputs": [item.to_payload() for item in self.inputs],
            }
        )
        if self.symbol is not None:
            payload["symbol"] = self.symbol
        if self.data_family is not None:
            payload["data_family"] = self.data_family
        return payload


@dataclass(frozen=True, slots=True)
class DatasetStageSpec:
    enabled: bool = False
    research_config: str = "configs/v2_btc_research.json"
    db_path: str | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> DatasetStageSpec:
        payload = payload or {}
        if not isinstance(payload, Mapping):
            raise ValueError("dataset_stage must be an object")
        return cls(
            enabled=bool(payload.get("enabled", False)),
            research_config=str(payload.get("research_config") or "configs/v2_btc_research.json"),
            db_path=str(payload.get("db_path")) if payload.get("db_path") is not None else None,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "enabled": self.enabled,
            "research_config": self.research_config,
        }
        if self.db_path is not None:
            payload["db_path"] = self.db_path
        return payload


@dataclass(frozen=True, slots=True)
class EvidenceStageSpec:
    enabled: bool = False
    hmm_knn_config: str = "configs/v2_btc_hmm_multi_knn_research.json"
    experiment_spec: str | None = None
    dataset_path: str | None = None
    workers: int = 1
    write_monitoring: bool = True

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> EvidenceStageSpec:
        payload = payload or {}
        if not isinstance(payload, Mapping):
            raise ValueError("evidence_stage must be an object")
        workers = int(payload.get("workers", 1))
        if workers < 1:
            raise ValueError("evidence_stage.workers must be at least 1")
        return cls(
            enabled=bool(payload.get("enabled", False)),
            hmm_knn_config=str(payload.get("hmm_knn_config") or "configs/v2_btc_hmm_multi_knn_research.json"),
            experiment_spec=str(payload.get("experiment_spec")) if payload.get("experiment_spec") else None,
            dataset_path=str(payload.get("dataset_path")) if payload.get("dataset_path") else None,
            workers=workers,
            write_monitoring=bool(payload.get("write_monitoring", True)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "hmm_knn_config": self.hmm_knn_config,
            "experiment_spec": self.experiment_spec,
            "dataset_path": self.dataset_path,
            "workers": self.workers,
            "write_monitoring": self.write_monitoring,
        }


@dataclass(frozen=True, slots=True)
class ProviderPipelineSpec:
    version: str
    asset_scope: tuple[str, ...]
    output_dir: Path
    providers: tuple[ProviderSpec, ...]
    dataset_stage: DatasetStageSpec
    evidence_stage: EvidenceStageSpec

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, spec_path: Path) -> ProviderPipelineSpec:
        if not isinstance(payload, Mapping):
            raise ValueError("pipeline spec must be a JSON object")
        version = str(payload.get("version") or "").strip()
        if not version:
            raise ValueError("pipeline spec version is required")
        asset_scope = tuple(str(symbol).strip().upper() for symbol in (payload.get("asset_scope") or []) if str(symbol).strip())
        if not asset_scope:
            raise ValueError("pipeline spec asset_scope must contain at least one symbol")
        raw_output_dir = payload.get("output_dir") or Path("data/research") / version
        output_dir = Path(str(raw_output_dir))
        providers_payload = payload.get("providers") or []
        if not isinstance(providers_payload, list):
            raise ValueError("providers must be a list")
        providers = tuple(ProviderSpec.from_payload(provider, index=index) for index, provider in enumerate(providers_payload))
        return cls(
            version=version,
            asset_scope=asset_scope,
            output_dir=output_dir,
            providers=providers,
            dataset_stage=DatasetStageSpec.from_payload(payload.get("dataset_stage")),
            evidence_stage=EvidenceStageSpec.from_payload(payload.get("evidence_stage")),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "asset_scope": list(self.asset_scope),
            "output_dir": str(self.output_dir),
            "providers": [provider.to_payload() for provider in self.providers],
            "dataset_stage": self.dataset_stage.to_payload(),
            "evidence_stage": self.evidence_stage.to_payload(),
        }


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
    spec_model = ProviderPipelineSpec.from_payload(_read_json(spec_path), spec_path=spec_path)
    spec = spec_model.to_payload()
    output_dir = spec_model.output_dir
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
            spec_path=spec_path,
            output_dir=output_dir,
            app_config=app_config or AppConfig.from_env(),
            archive_manifests=archive_manifests,
        )
        dataset_manifest_path = dataset_result.get("dataset_manifest_path")
        stage_status["dataset"] = dataset_result["stage_status"]

    if run_evidence:
        evidence_result = _run_evidence_stage(
            spec,
            spec_path=spec_path,
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
    summary = _build_pipeline_summary(
        spec=spec,
        spec_path=spec_path,
        stage_requested=stage,
        output_dir=output_dir,
        intake_manifest_path=intake_manifest_path,
        data_quality_report_path=data_quality_report_path,
        market_journal_manifest_path=output_dir / "market_journal_manifest.json",
        dataset_manifest_path=dataset_manifest_path,
        evidence_manifest_path=evidence_manifest_path,
        stage_status=stage_status,
        data_quality_report=data_quality_report,
    )
    pipeline_summary_path = output_dir / "pipeline_summary.json"
    pipeline_summary_path.write_text(_canonical_json(summary, indent=2) + "\n", encoding="utf-8")

    return ResearchDataPipelineResult(
        output_dir=output_dir,
        intake_manifest_path=intake_manifest_path,
        data_quality_report_path=data_quality_report_path,
        market_journal_manifest_path=output_dir / "market_journal_manifest.json",
        pipeline_summary_path=pipeline_summary_path,
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
        if source_name not in IMPLEMENTED_LOCAL_INGESTION_PROVIDERS:
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
            result = _ingest_provider_input(
                source_name=source_name,
                input_payload=input_payload,
                spec=spec,
                spec_path=spec_path,
                output_dir=archive_output_dir,
            )
            manifest = _read_json(result.manifest_path)
            assert_valid_archive_source_manifest(manifest)
            archive_manifests.append(manifest)
            archive_manifest_paths.append(result.manifest_path)
            record["manifest_paths"].append(str(result.manifest_path))
            record.setdefault("inputs", []).append(
                {
                    "input_index": input_index,
                    "path": str(input_payload.get("path")) if input_payload.get("path") else None,
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


def _ingest_provider_input(
    *,
    source_name: str,
    input_payload: Mapping[str, Any],
    spec: Mapping[str, Any],
    spec_path: Path,
    output_dir: Path,
) -> Any:
    symbol = str(input_payload.get("symbol") or (spec.get("asset_scope") or ["BTCUSDT"])[0])
    data_family = str(input_payload["data_family"])
    interval = input_payload.get("interval")
    strict = bool(input_payload.get("strict", False))
    if source_name == "binance_vision":
        if input_payload.get("path"):
            return ingest_binance_vision_archive(
                _resolve_path(input_payload["path"], base_path=spec_path.parent),
                symbol=symbol,
                data_family=data_family,
                interval=interval,
                output_dir=output_dir,
                strict=strict,
            )
        download_payload = input_payload.get("download") if isinstance(input_payload.get("download"), Mapping) else input_payload
        return download_and_ingest_binance_vision_archive(
            symbol=symbol,
            data_family=data_family,
            period=str(download_payload["period"]),
            output_dir=output_dir,
            interval=interval,
            cadence=str(download_payload.get("cadence") or input_payload.get("cadence") or "daily"),
            market=str(download_payload.get("market") or input_payload.get("market") or "futures/um"),
            strict=strict,
            verify_checksum=bool(download_payload.get("verify_checksum", True)),
        )
    if source_name == "crypto_lake":
        if input_payload.get("path"):
            return ingest_crypto_lake_archive(
                _resolve_path(input_payload["path"], base_path=spec_path.parent),
                symbol=symbol,
                data_family=data_family,
                output_dir=output_dir,
                interval=interval,
                provider_symbol=(
                    str(input_payload.get("provider_symbol"))
                    if input_payload.get("provider_symbol") is not None
                    else None
                ),
                strict=strict,
            )
        fetch_payload = input_payload.get("fetch")
        if not isinstance(fetch_payload, Mapping):
            raise ValueError("crypto_lake inputs require path or fetch object")
        return fetch_crypto_lake_archive(
            symbol=symbol,
            data_family=data_family,
            start_time=str(fetch_payload["start_time"]),
            end_time=str(fetch_payload["end_time"]),
            output_dir=output_dir,
            interval=interval,
            exchange=str(fetch_payload.get("exchange") or "BINANCE"),
            table=str(fetch_payload.get("table")) if fetch_payload.get("table") is not None else None,
            provider_symbol=(
                str(fetch_payload.get("provider_symbol") or input_payload.get("provider_symbol"))
                if (fetch_payload.get("provider_symbol") or input_payload.get("provider_symbol")) is not None
                else None
            ),
        )
    raise ValueError(f"unsupported implemented provider source: {source_name}")


def _run_dataset_stage(
    spec: Mapping[str, Any],
    *,
    spec_path: Path,
    output_dir: Path,
    app_config: AppConfig,
    archive_manifests: list[Mapping[str, Any]],
) -> dict[str, Any]:
    dataset_spec = spec.get("dataset_stage") or {}
    if not dataset_spec or not bool(dataset_spec.get("enabled", False)):
        return {"stage_status": {"status": "skipped", "reason": "dataset_stage_disabled"}}
    research_config = _resolve_stage_path(dataset_spec.get("research_config") or "configs/v2_btc_research.json", spec_path=spec_path)
    db_path = _resolve_stage_path(dataset_spec.get("db_path") or app_config.db_path, spec_path=spec_path)
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
    spec_path: Path,
    output_dir: Path,
    dataset_manifest_path: Path | None,
) -> dict[str, Any]:
    evidence_spec = spec.get("evidence_stage") or {}
    if not evidence_spec or not bool(evidence_spec.get("enabled", False)):
        return {"stage_status": {"status": "skipped", "reason": "evidence_stage_disabled"}}
    dataset_path = _dataset_path_from_manifest(dataset_manifest_path)
    if dataset_path is None:
        explicit_dataset = evidence_spec.get("dataset_path")
        dataset_path = _resolve_stage_path(explicit_dataset, spec_path=spec_path) if explicit_dataset else None
    if dataset_path is None or not dataset_path.exists():
        return {"stage_status": {"status": "skipped", "reason": "dataset_not_available"}}
    try:
        if evidence_spec.get("experiment_spec"):
            result = run_hmm_knn_experiment_matrix(
                spec_path=_resolve_stage_path(evidence_spec["experiment_spec"], spec_path=spec_path),
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
            config_path=_resolve_stage_path(evidence_spec.get("hmm_knn_config") or "configs/v2_btc_hmm_multi_knn_research.json", spec_path=spec_path),
            dataset_path=dataset_path,
            output_dir=output_dir / "evidence",
        )
        monitoring_report_path = (
            monitor_hmm_knn_artifact(result.artifact_manifest_path)
            if bool(evidence_spec.get("write_monitoring", True))
            else None
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
            "monitoring_report_path": str(monitoring_report_path) if monitoring_report_path is not None else None,
        },
    }


def _build_pipeline_summary(
    *,
    spec: Mapping[str, Any],
    spec_path: Path,
    stage_requested: str,
    output_dir: Path,
    intake_manifest_path: Path,
    data_quality_report_path: Path,
    market_journal_manifest_path: Path,
    dataset_manifest_path: Path | None,
    evidence_manifest_path: Path | None,
    stage_status: Mapping[str, Mapping[str, Any]],
    data_quality_report: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_summary = _summarize_evidence_manifest(evidence_manifest_path, stage_status.get("evidence") or {})
    top_failure_reasons = _pipeline_failure_reasons(
        stage_status=stage_status,
        data_quality_report=data_quality_report,
        evidence_summary=evidence_summary,
    )
    conclusion_status, conclusion_reason = _pipeline_conclusion(
        stage_status=stage_status,
        data_quality_report=data_quality_report,
        evidence_summary=evidence_summary,
        top_failure_reasons=top_failure_reasons,
    )
    artifact_links = {
        "data_intake_manifest_path": str(intake_manifest_path),
        "data_quality_report_path": str(data_quality_report_path),
        "market_journal_manifest_path": str(market_journal_manifest_path),
        "dataset_manifest_path": str(dataset_manifest_path) if dataset_manifest_path is not None else None,
        "evidence_manifest_path": str(evidence_manifest_path) if evidence_manifest_path is not None else None,
    }
    return {
        "pipeline_summary_version": DATA_PIPELINE_SUMMARY_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "version": str(spec["version"]),
        "spec_path": str(spec_path),
        "spec_sha256": _hash_file(spec_path),
        "stage_requested": stage_requested,
        "asset_scope": list(spec.get("asset_scope") or []),
        "output_dir": str(output_dir),
        "artifact_links": artifact_links,
        "stage_status": stage_status,
        "data_quality": {
            "manifest_count": data_quality_report.get("manifest_count"),
            "alert_count": len(data_quality_report.get("alerts") or []),
            "alerts": data_quality_report.get("alerts") or [],
            "gap_count_total": data_quality_report.get("gap_count_total"),
            "duplicate_count_total": data_quality_report.get("duplicate_count_total"),
            "non_promotable_count": data_quality_report.get("non_promotable_count"),
            "zero_row_manifest_count": data_quality_report.get("zero_row_manifest_count"),
        },
        "evidence": evidence_summary,
        "top_failure_reasons": top_failure_reasons,
        "conclusion": {
            "status": conclusion_status,
            "reason": conclusion_reason,
        },
        "notes": [
            "BTC Phase 1 research-only pipeline summary.",
            "Archive data supplies bars and context only; SQLite TradingView research signals remain the labeled-event trigger source.",
            "GPU/backend metadata is diagnostic and is not promotion evidence.",
        ],
    }


def _summarize_evidence_manifest(
    evidence_manifest_path: Path | None,
    evidence_stage_status: Mapping[str, Any],
) -> dict[str, Any]:
    if evidence_manifest_path is None or not evidence_manifest_path.exists():
        return {
            "available": False,
            "mode": evidence_stage_status.get("mode"),
            "status": evidence_stage_status.get("status"),
            "reason": evidence_stage_status.get("reason"),
            "error": evidence_stage_status.get("error"),
            "promotion_failure_counts": {},
            "backend_metadata": {},
            "monitoring_report_path": evidence_stage_status.get("monitoring_report_path"),
            "monitoring_alert_count": 0,
        }
    manifest = _read_json(evidence_manifest_path)
    if manifest.get("experiment_manifest_version"):
        failed_count = sum(1 for record in manifest.get("experiments") or [] if record.get("status") == "failed")
        return {
            "available": True,
            "mode": "experiment_matrix",
            "status": manifest.get("overall_status"),
            "manifest_path": str(evidence_manifest_path),
            "summary_path": manifest.get("summary_path"),
            "experiment_count": len(manifest.get("experiments") or []),
            "failed_experiment_count": failed_count,
            "effective_workers": manifest.get("effective_workers"),
            "promotion_failure_counts": manifest.get("promotion_failure_counts") or {},
            "research_boundary": manifest.get("research_boundary"),
            "backend_metadata": {},
            "monitoring_report_path": None,
            "monitoring_alert_count": _experiment_monitoring_alert_count(manifest),
        }

    metrics_path = _resolve_manifest_path(evidence_manifest_path, manifest.get("metrics_path")) if manifest.get("metrics_path") else None
    metrics = _read_json(metrics_path) if metrics_path is not None and metrics_path.exists() else {}
    monitoring_path = evidence_stage_status.get("monitoring_report_path")
    monitoring_report_path = Path(str(monitoring_path)) if monitoring_path else evidence_manifest_path.parent / "monitoring_report.json"
    monitoring = _read_json(monitoring_report_path) if monitoring_report_path.exists() else {}
    return {
        "available": True,
        "mode": "hmm_knn_research",
        "status": "completed",
        "manifest_path": str(evidence_manifest_path),
        "metrics_path": str(metrics_path) if metrics_path is not None else None,
        "monitoring_report_path": str(monitoring_report_path) if monitoring_report_path.exists() else None,
        "monitoring_alert_count": len(monitoring.get("alerts") or []),
        "promotion_failure_counts": _count_items(metrics.get("promotion_failures") or []),
        "research_boundary": monitoring.get("research_boundary"),
        "backend_metadata": {
            "knn_distance_backend_requested": (manifest.get("dependencies") or {}).get("knn_distance_backend_requested"),
            "knn_distance_backend": (manifest.get("dependencies") or {}).get("knn_distance_backend"),
            "cupy_available": (manifest.get("dependencies") or {}).get("cupy_available"),
            "xgboost_available": (manifest.get("dependencies") or {}).get("xgboost_available"),
            "xgboost_cuda_available": (manifest.get("dependencies") or {}).get("xgboost_cuda_available"),
            "xgboost_cuda_detection": (manifest.get("dependencies") or {}).get("xgboost_cuda_detection"),
        },
        "comparison": metrics.get("comparison") or {},
    }


def _experiment_monitoring_alert_count(experiment_manifest: Mapping[str, Any]) -> int:
    total = 0
    for record in experiment_manifest.get("experiments") or []:
        monitoring_path = record.get("monitoring_report_path")
        if not monitoring_path:
            continue
        path = Path(str(monitoring_path))
        if not path.exists():
            continue
        try:
            total += len((_read_json(path).get("alerts") or []))
        except Exception:
            continue
    return total


def _pipeline_failure_reasons(
    *,
    stage_status: Mapping[str, Mapping[str, Any]],
    data_quality_report: Mapping[str, Any],
    evidence_summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    for stage_name, status in stage_status.items():
        if status.get("status") == "failed":
            reasons.append(
                {
                    "source": "stage",
                    "code": f"{stage_name}_failed",
                    "count": 1,
                    "detail": status.get("error") or status.get("error_type"),
                }
            )
        elif status.get("status") == "skipped" and status.get("reason"):
            reasons.append(
                {
                    "source": "stage",
                    "code": f"{stage_name}_skipped:{status.get('reason')}",
                    "count": 1,
                    "detail": status.get("reason"),
                }
            )
    for alert in data_quality_report.get("alerts") or []:
        reasons.append(
            {
                "source": "data_quality",
                "code": str(alert.get("code") or "unknown_alert"),
                "count": int(((alert.get("details") or {}).get("manifest_count") or (alert.get("details") or {}).get("flag_count") or 1)),
                "detail": alert.get("message"),
            }
        )
    for code, count in (evidence_summary.get("promotion_failure_counts") or {}).items():
        reasons.append(
            {
                "source": "evidence",
                "code": str(code),
                "count": int(count),
                "detail": "promotion failure reported by HMM/KNN evidence",
            }
        )
    if int(evidence_summary.get("failed_experiment_count") or 0) > 0:
        reasons.append(
            {
                "source": "evidence",
                "code": "experiment_matrix_failed_experiments",
                "count": int(evidence_summary.get("failed_experiment_count") or 0),
                "detail": "one or more matrix experiments failed",
            }
        )
    return sorted(reasons, key=lambda item: (str(item["source"]), str(item["code"])))


def _pipeline_conclusion(
    *,
    stage_status: Mapping[str, Mapping[str, Any]],
    data_quality_report: Mapping[str, Any],
    evidence_summary: Mapping[str, Any],
    top_failure_reasons: list[Mapping[str, Any]],
) -> tuple[str, str]:
    failed_stages = [name for name, status in stage_status.items() if status.get("status") == "failed"]
    if failed_stages:
        missing_data_failure = any(
            "no signals found" in str((stage_status.get(name) or {}).get("error") or "").lower()
            for name in failed_stages
        )
        if missing_data_failure:
            return "inconclusive", "dataset stage could not build because required research signals were unavailable"
        return "rejected", f"pipeline stage failed: {', '.join(failed_stages)}"

    evidence_status = str(evidence_summary.get("status") or "")
    if evidence_status in {"skipped", "not_requested", ""} or not evidence_summary.get("available"):
        return "inconclusive", "no completed evidence artifact was available"

    substantive_evidence_failures = [
        item
        for item in top_failure_reasons
        if item.get("source") == "evidence" and item.get("code") != "research_only_not_live_promotable"
    ]
    if evidence_status == "failed" or substantive_evidence_failures:
        return "rejected", "completed evidence reported promotion or experiment failures"

    warning_alerts = [
        alert
        for alert in data_quality_report.get("alerts") or []
        if str(alert.get("severity") or "").lower() in {"warn", "error", "blocker"}
    ]
    if warning_alerts:
        return "inconclusive", "data-quality alerts require review before interpreting evidence"
    return "supported", "evidence completed without substantive promotion failures or data-quality warnings"


def _count_items(items: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


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


def _resolve_stage_path(path: Any, *, spec_path: Path) -> Path:
    candidate = Path(str(path)).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return (spec_path.parent / candidate).resolve()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _resolve_manifest_path(manifest_path: Path, raw: object) -> Path:
    path = Path(str(raw))
    if path.is_absolute():
        return path
    parent_candidate = manifest_path.parent / path
    if parent_candidate.exists():
        return parent_candidate
    return path


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
