# V2-AUDIT-ID: V2-AUD-AUTONOMY-010
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md, docs/contracts/strategy_spec_contract.md
# V2-BOUNDARY: research_only, strategy_queue_scan, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_autonomy
"""Local strategy-spec queue scanner for bounded v2 research loops."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.strategy_specs import (
    load_strategy_spec_file,
    parse_strategy_spec,
    validate_strategy_spec,
)

STRATEGY_QUEUE_CONFIG_SCHEMA_VERSION = "strategy_queue_scan_config_v1"
STRATEGY_QUEUE_MANIFEST_SCHEMA_VERSION = "strategy_queue_manifest_v1"
STRATEGY_QUEUE_RESULT_SCHEMA_VERSION = "strategy_queue_scan_result_v1"
STRATEGY_QUEUE_EVIDENCE_MODE = "input_hygiene_only"
SUPPORTED_STRATEGY_QUEUE_SUFFIXES = frozenset({".json", ".yaml", ".yml"})
SECRET_LIKE_PATH_TOKENS = frozenset(
    {
        ".env",
        "api_key",
        "apikey",
        "credential",
        "credentials",
        "password",
        "private_key",
        "secret",
        "token",
    }
)


class StrategyQueueScanConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = STRATEGY_QUEUE_CONFIG_SCHEMA_VERSION
    strategy_root: str = Field(min_length=1)
    output_root: str = Field(min_length=1)
    run_id: str = Field(default="strategy-queue-scan", pattern=r"^[A-Za-z0-9_.-]+$")
    max_files: int = Field(default=500, ge=1, le=10_000)
    evidence_mode: str = STRATEGY_QUEUE_EVIDENCE_MODE
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_config(self) -> "StrategyQueueScanConfig":
        if self.evidence_mode != STRATEGY_QUEUE_EVIDENCE_MODE:
            raise ValueError(f"strategy queue evidence_mode must be {STRATEGY_QUEUE_EVIDENCE_MODE}")
        if _has_secret_like_path(Path(self.strategy_root)) or _has_secret_like_path(Path(self.output_root)):
            raise ValueError("strategy queue paths must not look like secret or credential paths")
        require_research_boundary(self, context="strategy queue scan config")
        return self


class StrategyQueueItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_path: str = Field(min_length=1)
    source_relpath: str = Field(min_length=1)
    source_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    status: Literal["accepted", "rejected"]
    strategy_id: str | None = None
    spec_hash: str | None = Field(default=None, min_length=64, max_length=64)
    normalized_spec_path: str | None = None
    blocker_reasons: tuple[str, ...] = ()


class StrategyQueueManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = STRATEGY_QUEUE_MANIFEST_SCHEMA_VERSION
    manifest_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    strategy_root: str = Field(min_length=1)
    output_root: str = Field(min_length=1)
    evidence_mode: str = STRATEGY_QUEUE_EVIDENCE_MODE
    accepted_research_ready: bool = False
    item_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    blocker_reasons: tuple[str, ...] = ()
    items: tuple[StrategyQueueItem, ...] = ()
    boundary_flags: dict[str, bool] = Field(default_factory=lambda: dict(RESEARCH_BOUNDARY))
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_manifest(self) -> "StrategyQueueManifest":
        if self.evidence_mode != STRATEGY_QUEUE_EVIDENCE_MODE:
            raise ValueError(f"strategy queue manifest evidence_mode must be {STRATEGY_QUEUE_EVIDENCE_MODE}")
        if self.item_count != len(self.items):
            raise ValueError("item_count must equal number of strategy queue items")
        if self.accepted_count != sum(1 for item in self.items if item.status == "accepted"):
            raise ValueError("accepted_count must equal accepted queue items")
        if self.rejected_count != sum(1 for item in self.items if item.status == "rejected"):
            raise ValueError("rejected_count must equal rejected queue items")
        if self.accepted_research_ready:
            raise ValueError("strategy queue manifests are input hygiene only")
        require_research_boundary(self, context="strategy queue manifest")
        return self


class StrategyQueueScanResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = STRATEGY_QUEUE_RESULT_SCHEMA_VERSION
    manifest_path: str = Field(min_length=1)
    manifest_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    evidence_mode: str = STRATEGY_QUEUE_EVIDENCE_MODE
    accepted_research_ready: bool = False
    item_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    blocker_reasons: tuple[str, ...] = ()
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_result(self) -> "StrategyQueueScanResult":
        if self.evidence_mode != STRATEGY_QUEUE_EVIDENCE_MODE:
            raise ValueError(f"strategy queue result evidence_mode must be {STRATEGY_QUEUE_EVIDENCE_MODE}")
        if self.accepted_research_ready:
            raise ValueError("strategy queue scan results are input hygiene only")
        require_research_boundary(self, context="strategy queue scan result")
        return self


def scan_strategy_queue(
    config: StrategyQueueScanConfig | dict[str, Any],
) -> StrategyQueueScanResult:
    parsed = (
        config if isinstance(config, StrategyQueueScanConfig) else StrategyQueueScanConfig.model_validate(config)
    )
    strategy_root = Path(parsed.strategy_root).resolve(strict=False)
    output_root = Path(parsed.output_root).resolve(strict=False)
    run_root = (output_root / parsed.run_id).resolve(strict=False)
    normalized_root = run_root / "accepted_specs"
    manifest_path = run_root / "strategy_queue_manifest.json"

    if not strategy_root.is_dir():
        raise ValueError("strategy_root must be an existing directory")
    _ensure_child(run_root, output_root, "strategy queue output root escapes requested output_root")
    if _is_relative_to(output_root, strategy_root):
        raise ValueError("strategy queue output_root must not be inside strategy_root")

    source_files = _strategy_queue_files(strategy_root)
    if len(source_files) > parsed.max_files:
        raise ValueError(f"strategy queue file count exceeds max_files: {len(source_files)}>{parsed.max_files}")

    normalized_root.mkdir(parents=True, exist_ok=True)
    items = tuple(
        _scan_strategy_file(path, strategy_root=strategy_root, normalized_root=normalized_root)
        for path in source_files
    )
    blockers = _aggregate_blockers(items)
    if not items:
        blockers = tuple(sorted((*blockers, "strategy_queue_empty")))
    if not any(item.status == "accepted" for item in items):
        blockers = tuple(sorted((*blockers, "no_accepted_strategy_specs")))

    manifest_payload = {
        "schema_version": STRATEGY_QUEUE_MANIFEST_SCHEMA_VERSION,
        "manifest_id": "0" * 64,
        "run_id": parsed.run_id,
        "strategy_root": str(strategy_root),
        "output_root": str(output_root),
        "evidence_mode": STRATEGY_QUEUE_EVIDENCE_MODE,
        "accepted_research_ready": False,
        "item_count": len(items),
        "accepted_count": sum(1 for item in items if item.status == "accepted"),
        "rejected_count": sum(1 for item in items if item.status == "rejected"),
        "blocker_reasons": blockers,
        "items": [item.model_dump(mode="json") for item in items],
        "boundary_flags": dict(RESEARCH_BOUNDARY),
        **dict(RESEARCH_BOUNDARY),
    }
    manifest_payload["manifest_id"] = canonical_json_hash(
        {key: value for key, value in manifest_payload.items() if key != "manifest_id"}
    )
    manifest = StrategyQueueManifest.model_validate(manifest_payload)
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    return StrategyQueueScanResult(
        manifest_path=str(manifest_path),
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        item_count=manifest.item_count,
        accepted_count=manifest.accepted_count,
        rejected_count=manifest.rejected_count,
        blocker_reasons=manifest.blocker_reasons,
    )


def _scan_strategy_file(
    path: Path,
    *,
    strategy_root: Path,
    normalized_root: Path,
) -> StrategyQueueItem:
    relpath = path.relative_to(strategy_root).as_posix()
    common = {
        "source_path": str(path),
        "source_relpath": relpath,
    }
    if _has_secret_like_path(path):
        return StrategyQueueItem(
            **common,
            status="rejected",
            blocker_reasons=("secret_like_strategy_file_path",),
        )
    if path.suffix.lower() not in SUPPORTED_STRATEGY_QUEUE_SUFFIXES:
        return StrategyQueueItem(
            **common,
            status="rejected",
            blocker_reasons=(f"unsupported_strategy_file_suffix:{path.suffix.lower() or '<none>'}",),
        )

    try:
        source_hash = file_sha256(path)
        payload = load_strategy_spec_file(path)
    except Exception as exc:  # noqa: BLE001 - loader errors must become manifest blockers.
        return StrategyQueueItem(
            **common,
            source_sha256=file_sha256(path) if path.is_file() else None,
            status="rejected",
            blocker_reasons=(f"strategy_spec_load_failed:{type(exc).__name__}",),
        )

    validation = validate_strategy_spec(payload)
    if not validation.ok:
        return StrategyQueueItem(
            **common,
            source_sha256=source_hash,
            status="rejected",
            blocker_reasons=tuple(f"strategy_spec_validation_failed:{error}" for error in validation.errors),
        )

    spec = parse_strategy_spec(payload)
    normalized_payload = spec.model_dump(mode="json")
    normalized_path = normalized_root / f"{_safe_filename(spec.strategy_id)}-{spec.spec_hash[:12]}.json"
    normalized_path.write_text(
        json.dumps(normalized_payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return StrategyQueueItem(
        **common,
        source_sha256=source_hash,
        status="accepted",
        strategy_id=spec.strategy_id,
        spec_hash=spec.spec_hash,
        normalized_spec_path=str(normalized_path),
    )


def _strategy_queue_files(root: Path) -> tuple[Path, ...]:
    files = [path for path in root.rglob("*") if path.is_file()]
    return tuple(sorted(files, key=lambda path: path.relative_to(root).as_posix()))


def _aggregate_blockers(items: tuple[StrategyQueueItem, ...]) -> tuple[str, ...]:
    blockers: set[str] = set()
    for item in items:
        blockers.update(item.blocker_reasons)
    return tuple(sorted(blockers))


def _has_secret_like_path(path: Path) -> bool:
    for part in path.parts:
        lower = part.lower()
        if lower in SECRET_LIKE_PATH_TOKENS:
            return True
        if any(token in lower for token in SECRET_LIKE_PATH_TOKENS if token != ".env"):
            return True
    return False


def _safe_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return sanitized or "strategy"


def _ensure_child(child: Path, root: Path, message: str) -> None:
    if not _is_relative_to(child, root):
        raise ValueError(message)


def _is_relative_to(child: Path, root: Path) -> bool:
    try:
        child.relative_to(root)
    except ValueError:
        return False
    return True
