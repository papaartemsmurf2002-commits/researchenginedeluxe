# V2-AUDIT-ID: V2-AUD-LEGACY-010
# V2-CONTRACTS: docs/contracts/strategy_plugin_contract.md
# V2-BOUNDARY: research_only, metadata_only, plugin_execution_forbidden
# V2-OWNER: v2_strategy_plugins
"""Metadata-only v2 manifests for audited legacy strategy plugins."""

from __future__ import annotations

import inspect
import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.strategies.parameters import (
    STRATEGY_PARAMETER_METADATA,
    metadata_for_strategy,
    strategy_metadata_sha256,
)
from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now


class StrategyPluginProtocol(BaseModel):
    model_config = ConfigDict(frozen=True)

    protocol_id: str = "metadata_only_strategy_plugin_protocol_v1"
    execution_enabled: bool = False
    required_inputs_declared: bool = False
    output_columns: tuple[str, ...] = (
        "ts",
        "instrument_id",
        "signal",
        "target_weight",
        "skip_reason",
    )
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_protocol(self) -> "StrategyPluginProtocol":
        if self.execution_enabled:
            raise ValueError("v2 strategy plugin execution remains forbidden")
        _require_boundary(
            research_only=self.research_only,
            observe_only=self.observe_only,
            promotion_ready=self.promotion_ready,
        )
        return self


class StrategyPluginManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_id: str = Field(min_length=64, max_length=64)
    strategy_id: str = Field(min_length=1)
    manifest_kind: str = "legacy_strategy_metadata_wrapper"
    legacy_subsystem: str = "strategy_plugins"
    legacy_classification: str = "wrap_into_v2"
    legacy_audit_id: str = "V2-AUD-LEGACY-001"
    wrapper_audit_id: str = "V2-AUD-LEGACY-010"
    source_path: str = Field(min_length=1)
    source_sha256: str = Field(min_length=64, max_length=64)
    legacy_metadata_sha256: str = Field(min_length=64, max_length=64)
    protocol: StrategyPluginProtocol = Field(default_factory=StrategyPluginProtocol)
    default_parameters: dict[str, Any] = Field(default_factory=dict)
    parameter_space: dict[str, tuple[Any, ...]] = Field(default_factory=dict)
    holding_window_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    additional_allowed_parameter_values: dict[str, dict[str, tuple[Any, ...]]] = Field(default_factory=dict)
    signal_density: dict[str, float] = Field(default_factory=dict)
    failure_modes: tuple[str, ...] = ()
    required_inputs: tuple[str, ...] = ()
    input_declaration_status: str = "metadata_only_no_execution"
    output_columns: tuple[str, ...] = (
        "ts",
        "instrument_id",
        "signal",
        "target_weight",
        "skip_reason",
    )
    plugin_execution_allowed: bool = False
    network_access_allowed: bool = False
    secrets_access_allowed: bool = False
    arbitrary_file_access_allowed: bool = False
    live_runtime_access_allowed: bool = False
    order_placement_allowed: bool = False
    sizing_allowed: bool = False
    runtime_mode_change_allowed: bool = False
    candidate_pack_write_allowed: bool = False
    execution_blocker_reasons: tuple[str, ...] = (
        "plugin_execution_disabled_until_scoped_packet",
        "legacy_metadata_only_wrapper",
    )
    schema_version: str = V2_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utc_now)
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
    def _validate_manifest(self) -> "StrategyPluginManifest":
        _require_boundary(
            research_only=self.research_only,
            observe_only=self.observe_only,
            promotion_ready=self.promotion_ready,
        )
        forbidden = {
            "plugin_execution_allowed": self.plugin_execution_allowed,
            "network_access_allowed": self.network_access_allowed,
            "secrets_access_allowed": self.secrets_access_allowed,
            "arbitrary_file_access_allowed": self.arbitrary_file_access_allowed,
            "live_runtime_access_allowed": self.live_runtime_access_allowed,
            "order_placement_allowed": self.order_placement_allowed,
            "sizing_allowed": self.sizing_allowed,
            "runtime_mode_change_allowed": self.runtime_mode_change_allowed,
            "candidate_pack_write_allowed": self.candidate_pack_write_allowed,
            "candidate_evidence": self.candidate_evidence,
            "candidate_pack_eligible": self.candidate_pack_eligible,
            "live_signal": self.live_signal,
            "paper_signal": self.paper_signal,
            "sizing_instruction": self.sizing_instruction,
            "order_placement_instruction": self.order_placement_instruction,
            "runtime_mode_change": self.runtime_mode_change,
        }
        enabled = [name for name, value in forbidden.items() if value]
        if enabled:
            raise ValueError("strategy plugin manifest violates v2 boundary: " + ",".join(enabled))
        if not self.execution_blocker_reasons:
            raise ValueError("metadata-only plugin manifests require execution blocker reasons")
        if self.protocol.execution_enabled:
            raise ValueError("strategy plugin protocol must keep execution disabled")
        return self


class StrategyPluginRegistryManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    registry_manifest_id: str = Field(min_length=64, max_length=64)
    manifest_kind: str = "legacy_strategy_metadata_registry_wrapper"
    strategy_count: int = Field(ge=0)
    manifests: tuple[StrategyPluginManifest, ...]
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_registry(self) -> "StrategyPluginRegistryManifest":
        _require_boundary(
            research_only=self.research_only,
            observe_only=self.observe_only,
            promotion_ready=self.promotion_ready,
        )
        if self.strategy_count != len(self.manifests):
            raise ValueError("strategy_count must match manifest count")
        return self


def build_legacy_strategy_plugin_manifest(strategy_id: str) -> StrategyPluginManifest:
    if strategy_id not in STRATEGY_PARAMETER_METADATA:
        raise ValueError(f"unknown_legacy_strategy_metadata:{strategy_id}")
    metadata = metadata_for_strategy(strategy_id)
    payload = metadata.to_payload()
    source_path = _legacy_metadata_source_path()
    source_hash = file_sha256(source_path)
    manifest_payload = {
        "strategy_id": metadata.strategy_id,
        "manifest_kind": "legacy_strategy_metadata_wrapper",
        "legacy_subsystem": "strategy_plugins",
        "legacy_classification": "wrap_into_v2",
        "legacy_audit_id": "V2-AUD-LEGACY-001",
        "wrapper_audit_id": "V2-AUD-LEGACY-010",
        "source_path": _source_path_value(source_path),
        "source_sha256": source_hash,
        "legacy_metadata_sha256": strategy_metadata_sha256(strategy_id),
        "default_parameters": payload.get("default_parameters", {}),
        "parameter_space": _tuple_mapping(payload.get("parameter_space", {})),
        "holding_window_overrides": payload.get("holding_window_overrides", {}),
        "additional_allowed_parameter_values": _nested_tuple_mapping(
            payload.get("additional_allowed_parameter_values", {})
        ),
        "signal_density": payload.get("signal_density", {}),
        "failure_modes": tuple(payload.get("failure_modes", ())),
        "schema_version": V2_SCHEMA_VERSION,
        "plugin_execution_allowed": False,
        "network_access_allowed": False,
        "secrets_access_allowed": False,
        "arbitrary_file_access_allowed": False,
        "live_runtime_access_allowed": False,
        "order_placement_allowed": False,
        "sizing_allowed": False,
        "runtime_mode_change_allowed": False,
        "candidate_pack_write_allowed": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    return StrategyPluginManifest(
        manifest_id=canonical_json_hash(manifest_payload),
        **manifest_payload,
    )


def build_legacy_strategy_plugin_registry_manifest(
    strategy_ids: tuple[str, ...] | list[str] | None = None,
) -> StrategyPluginRegistryManifest:
    selected = tuple(strategy_ids or sorted(STRATEGY_PARAMETER_METADATA))
    manifests = tuple(build_legacy_strategy_plugin_manifest(strategy_id) for strategy_id in selected)
    payload = {
        "manifest_ids": [manifest.manifest_id for manifest in manifests],
        "strategy_ids": [manifest.strategy_id for manifest in manifests],
        "strategy_count": len(manifests),
        "schema_version": V2_SCHEMA_VERSION,
    }
    return StrategyPluginRegistryManifest(
        registry_manifest_id=canonical_json_hash(payload),
        strategy_count=len(manifests),
        manifests=manifests,
    )


def write_strategy_plugin_manifest(path: str | Path, manifest: StrategyPluginManifest) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_strategy_plugin_registry_manifest(path: str | Path, manifest: StrategyPluginRegistryManifest) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _legacy_metadata_source_path() -> Path:
    source = inspect.getsourcefile(metadata_for_strategy)
    if source is None:
        raise RuntimeError("could not identify legacy strategy metadata source file")
    return Path(source)


def _source_path_value(path: Path) -> str:
    return path.as_posix()


def _tuple_mapping(value: Mapping[str, Any]) -> dict[str, tuple[Any, ...]]:
    normalized: dict[str, tuple[Any, ...]] = {}
    for key, raw_values in value.items():
        if isinstance(raw_values, (list, tuple)):
            normalized[str(key)] = tuple(raw_values)
        else:
            normalized[str(key)] = (raw_values,)
    return normalized


def _nested_tuple_mapping(value: Mapping[str, Any]) -> dict[str, dict[str, tuple[Any, ...]]]:
    return {
        str(outer_key): _tuple_mapping(inner_value)
        for outer_key, inner_value in value.items()
    }


def _require_boundary(*, research_only: bool, observe_only: bool, promotion_ready: bool) -> None:
    if not research_only or not observe_only or promotion_ready:
        raise ValueError("strategy plugin manifests must preserve the v2 research boundary")
