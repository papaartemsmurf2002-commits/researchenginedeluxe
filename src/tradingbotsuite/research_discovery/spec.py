from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from tradingbotsuite.config import AppConfig


DISCOVERY_SPEC_VERSION = "discovery-run-spec-v1"
SUPPORTED_DISCOVERY_MODES = (
    "quick_smoke",
    "entry_discovery_standard",
    "hmm_regime_knn_lab",
    "perp_context_ablation",
    "filter_ablation_lab",
    "exit_lab",
    "deep_candidate_harvest",
    "promotion_gate_research_only",
)
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True, slots=True)
class DiscoveryBudgetSpec:
    max_trials: int = 3
    trial_batch_size: int = 1
    snapshot_interval_minutes: int = 30
    rng_seed: int = 73

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "DiscoveryBudgetSpec":
        payload = payload or {}
        result = cls(
            max_trials=int(payload.get("max_trials", 3)),
            trial_batch_size=int(payload.get("trial_batch_size", 1)),
            snapshot_interval_minutes=int(payload.get("snapshot_interval_minutes", 30)),
            rng_seed=int(payload.get("rng_seed", 73)),
        )
        if result.max_trials <= 0:
            raise ValueError("budget.max_trials must be positive")
        if result.trial_batch_size <= 0:
            raise ValueError("budget.trial_batch_size must be positive")
        if result.snapshot_interval_minutes <= 0:
            raise ValueError("budget.snapshot_interval_minutes must be positive")
        return result

    def to_payload(self) -> dict[str, Any]:
        return {
            "max_trials": self.max_trials,
            "trial_batch_size": self.trial_batch_size,
            "snapshot_interval_minutes": self.snapshot_interval_minutes,
            "rng_seed": self.rng_seed,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryTrialTemplate:
    trial_id: str
    candidate_id: str
    ledger_kind: str = "blocked"
    candidate_family: str = "placeholder_discovery_candidate"
    score: float = 0.0
    blocker_code: str = "placeholder_trial_no_signal_engine"
    filter_blocker_code: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, index: int) -> "DiscoveryTrialTemplate":
        if not isinstance(payload, Mapping):
            raise ValueError("trial_templates entries must be JSON objects")
        trial_id = str(payload.get("trial_id") or f"trial-{index:06d}").strip()
        candidate_id = str(payload.get("candidate_id") or f"candidate-{index:06d}").strip()
        if not SAFE_RUN_ID_RE.match(trial_id):
            raise ValueError("trial_templates.trial_id must be a safe file-system identifier")
        ledger_kind = str(payload.get("ledger_kind", "blocked")).strip()
        if ledger_kind not in {"interesting", "blocked", "filter_blocked"}:
            raise ValueError("trial_templates.ledger_kind must be one of interesting, blocked, filter_blocked")
        return cls(
            trial_id=trial_id,
            candidate_id=candidate_id,
            ledger_kind=ledger_kind,
            candidate_family=str(payload.get("candidate_family", "placeholder_discovery_candidate")).strip()
            or "placeholder_discovery_candidate",
            score=float(payload.get("score", 0.0)),
            blocker_code=str(payload.get("blocker_code", "placeholder_trial_no_signal_engine")).strip(),
            filter_blocker_code=str(payload.get("filter_blocker_code", "")).strip(),
            payload=_json_safe_mapping(payload.get("payload") or {}),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "candidate_id": self.candidate_id,
            "ledger_kind": self.ledger_kind,
            "candidate_family": self.candidate_family,
            "score": self.score,
            "blocker_code": self.blocker_code,
            "filter_blocker_code": self.filter_blocker_code,
            "payload": _json_safe_mapping(self.payload),
        }


@dataclass(frozen=True, slots=True)
class DiscoveryRunSpec:
    run_id: str
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    discovery_mode: str = "quick_smoke"
    research_output_dir: Path | None = None
    output_dir: Path | None = None
    feature_column_sets_path: Path | None = None
    feature_column_set_ids: tuple[str, ...] = ()
    budget: DiscoveryBudgetSpec = DiscoveryBudgetSpec()
    trial_templates: tuple[DiscoveryTrialTemplate, ...] = ()

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        spec_path: Path,
        repo_root: Path | None = None,
    ) -> "DiscoveryRunSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("discovery run spec must be a JSON object")
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run_id is required")
        if not SAFE_RUN_ID_RE.match(run_id):
            raise ValueError("run_id must be a safe file-system identifier")
        discovery_mode = str(payload.get("discovery_mode", "quick_smoke")).strip()
        if discovery_mode not in SUPPORTED_DISCOVERY_MODES:
            raise ValueError(f"discovery_mode must be one of: {', '.join(SUPPORTED_DISCOVERY_MODES)}")
        root = (repo_root or _repo_root()).resolve()
        trial_templates = tuple(
            DiscoveryTrialTemplate.from_payload(item, index=index)
            for index, item in enumerate(payload.get("trial_templates") or (), start=1)
        )
        return cls(
            run_id=run_id,
            symbol=str(payload.get("symbol", "BTCUSDT")).upper(),
            timeframe=str(payload.get("timeframe", "15m")).strip(),
            discovery_mode=discovery_mode,
            research_output_dir=_resolve_optional_path(payload.get("research_output_dir"), repo_root=root),
            output_dir=_resolve_optional_path(payload.get("output_dir"), repo_root=root),
            feature_column_sets_path=_resolve_optional_path(payload.get("feature_column_sets_path"), repo_root=root),
            feature_column_set_ids=tuple(
                str(item).strip()
                for item in payload.get("feature_column_set_ids") or ()
                if str(item).strip()
            ),
            budget=DiscoveryBudgetSpec.from_payload(payload.get("budget")),
            trial_templates=trial_templates,
        )

    @classmethod
    def from_path(cls, path: Path, *, repo_root: Path | None = None) -> "DiscoveryRunSpec":
        spec_path = Path(path).expanduser().resolve()
        payload = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        return cls.from_payload(payload, spec_path=spec_path, repo_root=repo_root)

    def to_payload(self) -> dict[str, Any]:
        return {
            "spec_version": DISCOVERY_SPEC_VERSION,
            "run_id": self.run_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "discovery_mode": self.discovery_mode,
            "research_output_dir": str(self.research_output_dir) if self.research_output_dir is not None else None,
            "output_dir": str(self.output_dir) if self.output_dir is not None else None,
            "feature_column_sets_path": (
                str(self.feature_column_sets_path) if self.feature_column_sets_path is not None else None
            ),
            "feature_column_set_ids": list(self.feature_column_set_ids),
            "budget": self.budget.to_payload(),
            "trial_templates": [template.to_payload() for template in self.trial_templates],
        }


@dataclass(frozen=True, slots=True)
class DiscoveryResolvedPaths:
    repo_root: Path
    research_output_dir: Path
    output_dir: Path

    def to_payload(self) -> dict[str, str]:
        return {
            "repo_root": str(self.repo_root),
            "research_output_dir": str(self.research_output_dir),
            "output_dir": str(self.output_dir),
        }


def resolve_discovery_paths(
    spec: DiscoveryRunSpec,
    *,
    app_config: AppConfig | None = None,
    repo_root: Path | None = None,
) -> DiscoveryResolvedPaths:
    root = (repo_root or _repo_root()).resolve()
    config = app_config or AppConfig.from_env()
    research_output_dir = spec.research_output_dir or _resolve_path(config.research.output_dir, repo_root=root)
    research_output_dir = research_output_dir.resolve()
    output_dir = spec.output_dir or research_output_dir / "discovery_runs" / spec.run_id
    output_dir = output_dir.resolve()
    _assert_path_within(output_dir, research_output_dir, field_name="output_dir")
    return DiscoveryResolvedPaths(repo_root=root, research_output_dir=research_output_dir, output_dir=output_dir)


def generated_trial_templates(spec: DiscoveryRunSpec) -> tuple[DiscoveryTrialTemplate, ...]:
    if spec.trial_templates:
        return spec.trial_templates[: spec.budget.max_trials]
    templates: list[DiscoveryTrialTemplate] = []
    for index in range(1, spec.budget.max_trials + 1):
        if index == 1:
            ledger_kind = "interesting"
            blocker_code = ""
            filter_blocker_code = ""
            score = 0.1
        elif index % 2 == 0:
            ledger_kind = "blocked"
            blocker_code = "placeholder_trial_no_knn_engine"
            filter_blocker_code = ""
            score = 0.0
        else:
            ledger_kind = "filter_blocked"
            blocker_code = ""
            filter_blocker_code = "placeholder_filter_blocker"
            score = 0.0
        templates.append(
            DiscoveryTrialTemplate(
                trial_id=f"trial-{index:06d}",
                candidate_id=f"{spec.run_id}-candidate-{index:06d}",
                ledger_kind=ledger_kind,
                score=score,
                blocker_code=blocker_code,
                filter_blocker_code=filter_blocker_code,
                payload={"placeholder": True, "trial_index": index},
            )
        )
    return tuple(templates)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_optional_path(value: Any, *, repo_root: Path) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    return _resolve_path(value, repo_root=repo_root)


def _resolve_path(value: Any, *, repo_root: Path) -> Path:
    candidate = Path(str(value)).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _assert_path_within(path: Path, root: Path, *, field_name: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay under the configured research output directory") from exc


def _json_safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("payload must be a JSON object")
    return json.loads(json.dumps(dict(value), sort_keys=True, default=str, allow_nan=False))
