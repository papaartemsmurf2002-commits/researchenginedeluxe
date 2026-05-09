from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.spec import DiscoveryResolvedPaths, DiscoveryRunSpec


DISCOVERY_RUN_MANAGER_VERSION = "discovery-run-manager-v1"
DISCOVERY_RUN_MANIFEST_VERSION = "discovery-run-manifest-v1"


def discovery_manifest_payload(
    *,
    spec: DiscoveryRunSpec,
    spec_path: Path,
    resolved_paths: DiscoveryResolvedPaths,
    state: Mapping[str, Any],
    required_outputs: Mapping[str, str],
    counts: Mapping[str, int],
    feature_column_set_evidence: Mapping[str, Any] | None = None,
    data_evidence: Mapping[str, Any] | None = None,
    runtime_seconds: float,
) -> dict[str, Any]:
    return {
        "discovery_run_manifest_version": DISCOVERY_RUN_MANIFEST_VERSION,
        "runner_version": DISCOVERY_RUN_MANAGER_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "run_id": spec.run_id,
        "symbol": spec.symbol,
        "timeframe": spec.timeframe,
        "discovery_mode": spec.discovery_mode,
        "spec_path": str(Path(spec_path).resolve()),
        "spec_sha256": file_sha256(Path(spec_path)),
        "resolved_paths": resolved_paths.to_payload(),
        "output_dir": str(resolved_paths.output_dir),
        "budget": spec.budget.to_payload(),
        "data": spec.data.to_payload(),
        "data_evidence": dict(data_evidence or {}),
        "search": spec.search.to_payload(),
        "feature_column_set_evidence": dict(feature_column_set_evidence or {}),
        "state": dict(state),
        "counts": dict(counts),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "candidate_acceptance_scope": (
            "real_discovery_ledgers_no_pack_gate"
            if spec.discovery_mode in {"entry_discovery_standard", "hmm_regime_knn_lab", "deep_candidate_harvest"}
            else "discovery_manager_foundation_no_pack_gate"
        ),
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
        "required_outputs": dict(required_outputs),
        "runtime": {"elapsed_seconds": round(runtime_seconds, 6)},
    }


def file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
