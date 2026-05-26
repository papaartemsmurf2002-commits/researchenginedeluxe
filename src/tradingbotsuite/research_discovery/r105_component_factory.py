from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.config import AppConfig
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.artifact_keys import (
    ARTIFACT_KEY_VERSION,
    LEDGER_SIGNATURE_HASH_SCOPE,
    entry_event_signature_hash,
    effective_trial_key,
    inactive_trial_dimensions,
    prediction_signature_hash,
)
from tradingbotsuite.research_discovery.snapshots import atomic_write_json, iso_utc
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec, generated_trial_templates


R105_COMPONENT_FACTORY_VERSION = "r105-component-factory-v1"
R105_POSTMORTEM_MANIFEST_VERSION = "r105-latest-sweep-postmortem-manifest-v1"

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class R105PostmortemResult:
    manifest: dict[str, Any]
    effective_trial_summary: pd.DataFrame
    prediction_hash_clusters: pd.DataFrame
    top_blocked_by_cluster: pd.DataFrame
    markdown_report: str


@dataclass(frozen=True, slots=True)
class R105PostmortemArtifactResult:
    output_dir: Path
    manifest_path: Path
    effective_trial_summary_path: Path
    prediction_hash_clusters_path: Path
    top_blocked_by_cluster_path: Path
    markdown_report_path: Path


def build_r105_latest_sweep_postmortem(run_dir: Path) -> R105PostmortemResult:
    run_dir = Path(run_dir).expanduser().resolve()
    manifest_path = run_dir / "discovery_run_manifest.json"
    resolved_spec_path = run_dir / "discovery_spec_resolved.json"
    blocked_path = run_dir / "candidate_ledgers" / "blocked_candidates.parquet"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing discovery_run_manifest.json: {run_dir}")
    if not resolved_spec_path.exists():
        raise FileNotFoundError(f"missing discovery_spec_resolved.json: {run_dir}")
    if not blocked_path.exists():
        raise FileNotFoundError(f"missing blocked_candidates.parquet: {run_dir}")

    discovery_manifest = _read_json(manifest_path)
    resolved_spec = DiscoveryRunSpec.from_path(resolved_spec_path)
    blocked = pd.read_parquet(blocked_path)
    if blocked.empty:
        raise ValueError("R105 postmortem requires blocked candidate rows")
    annotated = _annotated_blocked_candidates(blocked, resolved_spec=resolved_spec)
    effective_summary = _effective_trial_summary(annotated)
    prediction_clusters = _prediction_hash_clusters(annotated)
    top_blocked = _top_blocked_by_cluster(annotated)
    summary = _postmortem_summary(
        annotated,
        effective_summary=effective_summary,
        prediction_clusters=prediction_clusters,
        top_blocked=top_blocked,
        resolved_spec=resolved_spec,
        discovery_manifest=discovery_manifest,
    )
    manifest = {
        "r105_postmortem_manifest_version": R105_POSTMORTEM_MANIFEST_VERSION,
        "component_factory_version": R105_COMPONENT_FACTORY_VERSION,
        "artifact_key_version": ARTIFACT_KEY_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "created_at_utc": iso_utc(),
        "source_run_dir": str(run_dir),
        "source_discovery_manifest_path": str(manifest_path),
        "source_discovery_manifest_sha256": _file_sha256(manifest_path),
        "source_resolved_spec_path": str(resolved_spec_path),
        "source_resolved_spec_sha256": _file_sha256(resolved_spec_path),
        "source_blocked_candidates_path": str(blocked_path),
        "source_blocked_candidates_sha256": _file_sha256(blocked_path),
        "source_run_id": str(discovery_manifest.get("run_id") or resolved_spec.run_id),
        "symbol": str(discovery_manifest.get("symbol") or resolved_spec.symbol),
        "timeframe": str(discovery_manifest.get("timeframe") or resolved_spec.timeframe),
        "summary": summary,
        "hash_scope": {
            "effective_trial_key": "scheduled_parameter_payload_with_no_regime_noop_dimensions_removed",
            "prediction_hash": LEDGER_SIGNATURE_HASH_SCOPE,
            "entry_event_hash": LEDGER_SIGNATURE_HASH_SCOPE,
            "prediction_hash_limitation": (
                "Per-bar prediction artifacts were not persisted for blocked R104 trials; "
                "prediction_hash is a deterministic ledger-summary signature, not a full "
                "timestamp-level prediction vector hash."
            ),
        },
        "issue_status": {
            "ISSUE-R104-001": "open_not_closed_by_this_postmortem",
        },
        "claim_scope": "postmortem_and_pruning_evidence_only_no_candidate_ready_claim",
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    markdown_report = _markdown_report(manifest, top_blocked)
    return R105PostmortemResult(
        manifest=manifest,
        effective_trial_summary=effective_summary,
        prediction_hash_clusters=prediction_clusters,
        top_blocked_by_cluster=top_blocked,
        markdown_report=markdown_report,
    )


def write_r105_latest_sweep_postmortem_artifacts(
    output_dir: Path,
    result: R105PostmortemResult,
) -> R105PostmortemArtifactResult:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    effective_path = output_dir / "effective_trial_summary.parquet"
    prediction_path = output_dir / "prediction_hash_clusters.parquet"
    top_blocked_path = output_dir / "top_blocked_by_cluster.parquet"
    report_path = output_dir / "r104_postmortem.md"
    manifest_path = output_dir / "r105_postmortem_manifest.json"

    result.effective_trial_summary.to_parquet(effective_path, index=False)
    result.prediction_hash_clusters.to_parquet(prediction_path, index=False)
    result.top_blocked_by_cluster.to_parquet(top_blocked_path, index=False)
    report_path.write_text(result.markdown_report, encoding="utf-8")

    manifest = dict(result.manifest)
    manifest["output_dir"] = str(output_dir)
    manifest["required_outputs"] = {
        "r105_postmortem_manifest": str(manifest_path),
        "effective_trial_summary": str(effective_path),
        "prediction_hash_clusters": str(prediction_path),
        "top_blocked_by_cluster": str(top_blocked_path),
        "r104_postmortem": str(report_path),
    }
    manifest["output_sha256s"] = {
        "effective_trial_summary": _file_sha256(effective_path),
        "prediction_hash_clusters": _file_sha256(prediction_path),
        "top_blocked_by_cluster": _file_sha256(top_blocked_path),
        "r104_postmortem": _file_sha256(report_path),
    }
    atomic_write_json(manifest_path, manifest)
    return R105PostmortemArtifactResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        effective_trial_summary_path=effective_path,
        prediction_hash_clusters_path=prediction_path,
        top_blocked_by_cluster_path=top_blocked_path,
        markdown_report_path=report_path,
    )


def _annotated_blocked_candidates(blocked: pd.DataFrame, *, resolved_spec: DiscoveryRunSpec) -> pd.DataFrame:
    frame = blocked.copy()
    parameter_frame = _scheduled_parameter_frame(resolved_spec)
    if not parameter_frame.empty:
        frame = frame.merge(parameter_frame, on="trial_id", how="left")
    records = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
    frame["effective_trial_key"] = [effective_trial_key(record) for record in records]
    frame["inactive_dimension_count"] = [len(inactive_trial_dimensions(record)) for record in records]
    frame["prediction_hash"] = [prediction_signature_hash(record) for record in records]
    frame["entry_event_hash"] = [entry_event_signature_hash(record) for record in records]
    frame["prediction_hash_scope"] = LEDGER_SIGNATURE_HASH_SCOPE
    frame["entry_event_hash_scope"] = LEDGER_SIGNATURE_HASH_SCOPE
    return frame


def _scheduled_parameter_frame(resolved_spec: DiscoveryRunSpec) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for template in generated_trial_templates(resolved_spec):
        row = {
            "trial_id": template.trial_id,
            "scheduled_candidate_id": template.candidate_id,
            "scheduled_candidate_family": template.candidate_family,
        }
        row.update(dict(template.payload))
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["trial_id"])
    frame = pd.DataFrame(rows)
    passthrough = [
        "trial_id",
        "scheduled_candidate_id",
        "scheduled_candidate_family",
        "hmm_posterior_threshold",
        "hmm_entropy_threshold",
        "probability_threshold",
        "expected_value_threshold",
        "min_neighbor_agreement",
        "min_distance_quality",
        "vote_margin_threshold",
        "search_space_total_combinations",
        "search_space_planned_trials",
        "search_space_sampled_fraction",
        "search_space_exhaustive",
    ]
    columns = [column for column in passthrough if column in frame.columns]
    return frame.loc[:, columns]


def _effective_trial_summary(frame: pd.DataFrame) -> pd.DataFrame:
    group_columns = [
        column
        for column in ("blocker_code", "feature_column_set_id", "regime_mode", "label_horizon", "distance_metric")
        if column in frame.columns
    ]
    rows: list[dict[str, Any]] = []
    for values, group in frame.groupby(group_columns, dropna=False, sort=False):
        if not isinstance(values, tuple):
            values = (values,)
        row = dict(zip(group_columns, values))
        row.update(
            {
            "effective_trial_count": int(group["effective_trial_key"].nunique(dropna=False)),
            "effective_trial_key": str(group["effective_trial_key"].iloc[0]),
            "effective_trial_key_sample": str(group["effective_trial_key"].iloc[0]),
            "scheduled_trial_count": int(len(group)),
            "prediction_cluster_count": int(group["prediction_hash"].nunique(dropna=False)),
            "entry_cluster_count": int(group["entry_event_hash"].nunique(dropna=False)),
            "blocker_distribution_json": _value_counts_json(group.get("blocker_code")),
            "max_score": _numeric_max(group, "score"),
            "median_score": _numeric_median(group, "score"),
            "median_overlap_ratio": _numeric_median(group, "overlap_ratio"),
            "median_signal_rate": _numeric_median(group, "signal_rate"),
            "median_independent_event_count": _numeric_median(group, "independent_event_count"),
            }
        )
        for column in _dimension_columns(group):
            if column not in row:
                row[column] = _first_value(group[column])
        rows.append(row)
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(
        ["scheduled_trial_count", "max_score"],
        ascending=[False, False],
        kind="mergesort",
    ).reset_index(drop=True)


def _prediction_hash_clusters(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for prediction_hash, group in frame.groupby("prediction_hash", sort=False):
        row = {
            "prediction_hash": prediction_hash,
            "prediction_hash_scope": LEDGER_SIGNATURE_HASH_SCOPE,
            "row_count": int(len(group)),
            "effective_trial_cluster_count": int(group["effective_trial_key"].nunique(dropna=False)),
            "entry_cluster_count": int(group["entry_event_hash"].nunique(dropna=False)),
            "blocker_distribution_json": _value_counts_json(group.get("blocker_code")),
            "max_score": _numeric_max(group, "score"),
            "median_overlap_ratio": _numeric_median(group, "overlap_ratio"),
            "median_signal_rate": _numeric_median(group, "signal_rate"),
            "median_independent_event_count": _numeric_median(group, "independent_event_count"),
        }
        for column in ("feature_column_set_id", "regime_mode", "label_horizon", "distance_metric"):
            if column in group.columns:
                row[column] = _first_value(group[column])
        rows.append(row)
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(
        ["row_count", "max_score", "prediction_hash"],
        ascending=[False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _top_blocked_by_cluster(frame: pd.DataFrame) -> pd.DataFrame:
    group_columns = [
        column
        for column in ("blocker_code", "feature_column_set_id", "label_horizon", "distance_metric")
        if column in frame.columns
    ]
    rows: list[dict[str, Any]] = []
    for values, group in frame.groupby(group_columns, dropna=False, sort=False):
        if not isinstance(values, tuple):
            values = (values,)
        row = dict(zip(group_columns, values))
        scores = pd.to_numeric(group.get("score"), errors="coerce")
        top_index = scores.idxmax() if scores.notna().any() else group.index[0]
        top = group.loc[top_index]
        row.update(
            {
                "rows": int(len(group)),
                "prediction_clusters": int(group["prediction_hash"].nunique(dropna=False)),
                "entry_clusters": int(group["entry_event_hash"].nunique(dropna=False)),
                "effective_trial_clusters": int(group["effective_trial_key"].nunique(dropna=False)),
                "max_score": _numeric_max(group, "score"),
                "median_overlap": _numeric_median(group, "overlap_ratio"),
                "median_signal_rate": _numeric_median(group, "signal_rate"),
                "median_independent_event_count": _numeric_median(group, "independent_event_count"),
                "top_candidate_id": str(top.get("candidate_id") or ""),
                "top_trial_id": str(top.get("trial_id") or ""),
                "top_score": _optional_float(top.get("score")),
                "top_realized_expectancy": _optional_float(top.get("realized_expectancy")),
            }
        )
        rows.append(row)
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result = result.sort_values(
        ["rows", "max_score"],
        ascending=[False, False],
        kind="mergesort",
    ).reset_index(drop=True)
    result.insert(0, "blocker_cluster_rank", range(1, len(result) + 1))
    return result


def _postmortem_summary(
    frame: pd.DataFrame,
    *,
    effective_summary: pd.DataFrame,
    prediction_clusters: pd.DataFrame,
    top_blocked: pd.DataFrame,
    resolved_spec: DiscoveryRunSpec,
    discovery_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    search_space = discovery_manifest.get("search_space") if isinstance(discovery_manifest.get("search_space"), Mapping) else {}
    scheduled = int(search_space.get("planned_trials") or resolved_spec.budget.max_trials or len(frame))
    inactive_dimensions = sorted(
        {
            dimension
            for record in frame[["regime_mode"]].astype(object).where(pd.notna(frame[["regime_mode"]]), None).to_dict("records")
            for dimension in inactive_trial_dimensions(record)
        }
    )
    return {
        "scheduled_trial_count": scheduled,
        "blocked_candidate_rows": int(len(frame)),
        "effective_trial_count": int(frame["effective_trial_key"].nunique(dropna=False)),
        "prediction_hash_cluster_count": int(len(prediction_clusters)),
        "entry_event_hash_cluster_count": int(frame["entry_event_hash"].nunique(dropna=False)),
        "blocker_distribution": _value_counts_dict(frame.get("blocker_code")),
        "top_blocker_clusters": top_blocked.head(10).to_dict("records"),
        "inactive_dimensions_dropped_under_no_regime": inactive_dimensions,
        "compact_fixture_candidate_ready": False,
        "issue_r104_001_remains_open": True,
        "limitations": [
            "Compact R104 fixture evidence remains screening-only, not candidate-ready.",
            "Per-bar prediction artifacts were not persisted for blocked trials under interesting_only persistence.",
            "Prediction and entry hashes are deterministic ledger-summary signatures, not full event-vector hashes.",
            "This postmortem does not rerun historical cycles, exact sweeps, exit labs, or candidate-pack gates.",
        ],
    }


def _markdown_report(manifest: Mapping[str, Any], top_blocked: pd.DataFrame) -> str:
    summary = dict(manifest.get("summary") or {})
    lines = [
        "# R104 Exact Sweep Postmortem",
        "",
        f"Generated: `{manifest.get('created_at_utc')}`",
        "",
        "## Research Boundary",
        "",
        "This report is research-only postmortem evidence. It does not promote a "
        "candidate, write live configuration, place orders, change runtime mode, "
        "or make a profitability claim. `ISSUE-R104-001` remains open because "
        "expanded durable primary-bar evidence and reruns are still required.",
        "",
        "## Summary",
        "",
        f"- Source run: `{manifest.get('source_run_id')}`",
        f"- Symbol/timeframe: `{manifest.get('symbol')}` / `{manifest.get('timeframe')}`",
        f"- Scheduled trials: `{summary.get('scheduled_trial_count')}`",
        f"- Blocked rows: `{summary.get('blocked_candidate_rows')}`",
        f"- Effective trial keys: `{summary.get('effective_trial_count')}`",
        f"- Prediction signature clusters: `{summary.get('prediction_hash_cluster_count')}`",
        f"- Entry signature clusters: `{summary.get('entry_event_hash_cluster_count')}`",
        "",
        "## Blocker Distribution",
        "",
    ]
    for blocker, count in dict(summary.get("blocker_distribution") or {}).items():
        lines.append(f"- `{blocker}`: `{count}`")
    lines.extend(
        [
            "",
            "## Top Blocked Clusters",
            "",
            "| Rank | Blocker | Feature set | Horizon | Distance | Rows | Prediction clusters | Entry clusters | Max score | Median overlap |",
            "| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_blocked.head(10).to_dict("records"):
        lines.append(
            "| {rank} | `{blocker}` | `{feature}` | `{horizon}` | `{distance}` | {rows} | {pred} | {entry} | {score:.6f} | {overlap:.6f} |".format(
                rank=int(row.get("blocker_cluster_rank") or 0),
                blocker=str(row.get("blocker_code") or ""),
                feature=str(row.get("feature_column_set_id") or ""),
                horizon=str(row.get("label_horizon") or ""),
                distance=str(row.get("distance_metric") or ""),
                rows=int(row.get("rows") or 0),
                pred=int(row.get("prediction_clusters") or 0),
                entry=int(row.get("entry_clusters") or 0),
                score=float(row.get("max_score") or 0.0),
                overlap=float(row.get("median_overlap") or 0.0),
            )
        )
    lines.extend(
        [
            "",
            "## Hash Limitations",
            "",
            "The completed R104 run used `interesting_only` trial-artifact persistence. "
            "Because all rows were blocked, per-bar prediction ledgers were not "
            "available for those trials. R105 therefore records deterministic "
            "ledger-summary prediction and entry signatures, not full timestamp-level "
            "prediction vector hashes.",
            "",
            "## R105 Decision",
            "",
            "Use this postmortem to prune no-regime no-op dimensions and prioritize "
            "entry-only, exit-only, orderflow, KNN/regime, and filter falsification "
            "labs before any new coupled brute-force sweep.",
            "",
        ]
    )
    return "\n".join(lines)


def _dimension_columns(group: pd.DataFrame) -> list[str]:
    return [
        column
        for column in (
            "candidate_family",
            "feature_column_set_id",
            "regime_mode",
            "label_horizon",
            "distance_metric",
            "k",
            "min_neighbor_count",
            "probability_threshold",
            "expected_value_threshold",
            "min_neighbor_agreement",
            "min_distance_quality",
            "vote_margin_threshold",
            "hmm_state_count",
            "hmm_posterior_threshold",
            "hmm_entropy_threshold",
        )
        if column in group.columns
    ]


def _value_counts_json(series: pd.Series | None) -> str:
    return json.dumps(_value_counts_dict(series), sort_keys=True, separators=(",", ":"))


def _value_counts_dict(series: pd.Series | None) -> dict[str, int]:
    if series is None:
        return {}
    counts = series.fillna("").astype(str).value_counts(dropna=False)
    return {str(key): int(value) for key, value in counts.items()}


def _numeric_max(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns:
        return 0.0
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(values.max()) if not values.empty else 0.0


def _numeric_median(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns:
        return 0.0
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(values.median()) if not values.empty else 0.0


def _optional_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if pd.notna(parsed) else None


def _first_value(series: pd.Series) -> Any:
    values = series.dropna()
    if values.empty:
        return ""
    value = values.iloc[0]
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_research_output_dir(raw_path: str | Path, *, config: AppConfig) -> Path:
    root = Path(config.research.output_dir).expanduser()
    root = root.resolve() if root.is_absolute() else (REPO_ROOT / root).resolve()
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        repo_relative = (REPO_ROOT / candidate).resolve()
        try:
            repo_relative.relative_to(root)
            resolved = repo_relative
        except ValueError:
            resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("output_dir must stay inside the configured research output directory") from exc
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R105 research-only candidate factory utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    postmortem = subparsers.add_parser("postmortem", help="Build an R105 postmortem for a completed discovery run")
    postmortem.add_argument("--run", required=True, help="Completed discovery run directory")
    postmortem.add_argument("--out", required=True, help="Output directory under the research output root")
    args = parser.parse_args(argv)

    if args.command == "postmortem":
        config = AppConfig.from_env()
        result = build_r105_latest_sweep_postmortem(Path(args.run))
        artifacts = write_r105_latest_sweep_postmortem_artifacts(
            _resolve_research_output_dir(args.out, config=config),
            result,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(artifacts.output_dir),
                    "manifest_path": str(artifacts.manifest_path),
                    "effective_trial_summary_path": str(artifacts.effective_trial_summary_path),
                    "prediction_hash_clusters_path": str(artifacts.prediction_hash_clusters_path),
                    "top_blocked_by_cluster_path": str(artifacts.top_blocked_by_cluster_path),
                    "markdown_report_path": str(artifacts.markdown_report_path),
                    "promotion_ready": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    raise ValueError(f"unsupported command:{args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
