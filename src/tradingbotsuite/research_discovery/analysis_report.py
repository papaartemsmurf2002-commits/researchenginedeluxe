from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from tradingbotsuite.research_discovery.state import atomic_write_json


RESEARCH_ANALYSIS_VERSION = "research-discovery-analysis-v1"
RESEARCH_ANALYSIS_ARTIFACT_VERSION = "research-discovery-analysis-artifacts-v1"
PURE_ROI_COLUMN = "net_return_after_fees_slippage_funding"
DISCOVERY_GROUP_COLUMNS = (
    "feature_column_set_id",
    "label_horizon",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "regime_mode",
)
CYCLE_GROUP_METRICS = (
    "costed_expectancy",
    PURE_ROI_COLUMN,
    "final_score",
    "trade_sortino",
    "trade_count",
    "hit_rate",
    "profit_factor",
    "max_drawdown",
)
DISCOVERY_GROUP_METRICS = (
    "realized_expectancy",
    "independent_event_expectancy",
    "final_score",
    "trade_count",
    "accepted_bar_count",
    "independent_event_count",
    "signal_rate",
    "event_signal_rate",
    "overlap_ratio",
    "side_collapse_ratio",
)


@dataclass(frozen=True, slots=True)
class ResearchAnalysisArtifactResult:
    analysis_json_path: Path
    markdown_path: Path
    analysis: Mapping[str, Any]


def build_research_analysis(
    *,
    cycle_dir: str | Path | None = None,
    discovery_dir: str | Path | None = None,
    include_trade_sortino: bool = True,
    max_sortino_trade_files: int = 1000,
) -> dict[str, Any]:
    """Build a deterministic research-only analysis payload from existing outputs."""

    analysis: dict[str, Any] = {
        "analysis_version": RESEARCH_ANALYSIS_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "intended_use": "research_artifact_review_only",
        "metric_priorities": {
            "primary": ["trade_sortino", PURE_ROI_COLUMN],
            "secondary": [
                "costed_expectancy",
                "final_score",
                "trade_count",
                "independent_event_count",
                "cost_stress_survival",
                "split_consistency",
            ],
        },
        "cycle": _summarize_cycle(
            Path(cycle_dir) if cycle_dir else None,
            include_trade_sortino=include_trade_sortino,
            max_sortino_trade_files=max_sortino_trade_files,
        ),
        "discovery": _summarize_discovery(Path(discovery_dir) if discovery_dir else None),
    }
    analysis["interpretation"] = _build_interpretation(analysis)
    return _json_safe(analysis)


def write_research_analysis_artifacts(
    *,
    cycle_dir: str | Path | None,
    discovery_dir: str | Path | None,
    output_dir: str | Path,
    include_trade_sortino: bool = True,
    max_sortino_trade_files: int = 1000,
) -> ResearchAnalysisArtifactResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    analysis = build_research_analysis(
        cycle_dir=cycle_dir,
        discovery_dir=discovery_dir,
        include_trade_sortino=include_trade_sortino,
        max_sortino_trade_files=max_sortino_trade_files,
    )
    analysis_json_path = output / "research_analysis.json"
    markdown_path = output / "research_analysis.md"
    atomic_write_json(analysis_json_path, analysis)
    markdown_path.write_text(render_research_analysis_markdown(analysis), encoding="utf-8")
    return ResearchAnalysisArtifactResult(
        analysis_json_path=analysis_json_path,
        markdown_path=markdown_path,
        analysis=analysis,
    )


def render_research_analysis_markdown(analysis: Mapping[str, Any]) -> str:
    cycle = _mapping(analysis.get("cycle"))
    discovery = _mapping(analysis.get("discovery"))
    interpretation = _mapping(analysis.get("interpretation"))
    lines: list[str] = [
        "# R106 Research Analysis Artifact",
        "",
        "This is research-only evidence review. It is not a promotion claim and does not change live runtime state.",
        "",
        "## Operator Takeaway",
        "",
    ]
    for item in _list_of_text(interpretation.get("takeaways")):
        lines.append(f"- {item}")
    lines.extend(["", "## Historical Cycle", ""])
    if cycle.get("available"):
        manifest = _mapping(cycle.get("manifest"))
        rankings = _mapping(cycle.get("rankings"))
        data_window = _mapping(cycle.get("data_window"))
        lines.extend(
            [
                f"- Symbol: `{manifest.get('symbol', '')}`",
                f"- Cycle: `{manifest.get('cycle_id', '')}`",
                f"- Candidates: `{rankings.get('row_count', 0)}`",
                f"- Pack eligible: `{rankings.get('pack_eligible_count', 0)}`",
                f"- Positive pure ROI candidates: `{rankings.get('positive_pure_roi_count', 0)}`",
                f"- Positive expectancy candidates: `{rankings.get('positive_costed_expectancy_count', 0)}`",
                f"- Data window: `{data_window.get('first_time', '')}` to `{data_window.get('last_time', '')}`; rows `{data_window.get('row_count', '')}`",
                "",
            ]
        )
        lines.extend(_markdown_table("Feature set performance", _list_of_mapping(rankings.get("feature_set_performance")), limit=12))
        lines.extend(_markdown_table("Strategy performance", _list_of_mapping(rankings.get("strategy_performance")), limit=12))
        lines.extend(_markdown_table("Top gate blockers", _list_of_mapping(cycle.get("gate_reason_counts")), limit=16))
        lines.extend(_markdown_table("Top candidates by pure ROI", _list_of_mapping(rankings.get("top_candidates_by_pure_roi")), limit=12))
    else:
        lines.append(f"- unavailable: `{cycle.get('reason', 'not_provided')}`")
    lines.extend(["", "## Exact Discovery", ""])
    if discovery.get("available"):
        counts = _mapping(discovery.get("counts"))
        lines.extend(
            [
                f"- Symbol: `{discovery.get('symbol', '')}`",
                f"- Run: `{discovery.get('run_id', '')}`",
                f"- Completed trials: `{counts.get('completed_trials', 0)}`",
                f"- Interesting candidates: `{counts.get('interesting_candidates', 0)}`",
                f"- Blocked candidates: `{counts.get('blocked_candidates', 0)}`",
                "",
            ]
        )
        lines.extend(_markdown_table("Feature-column-set discovery summary", _list_of_mapping(discovery.get("feature_set_summary")), limit=12))
        lines.extend(_markdown_table("KNN/filter setting leaders", _list_of_mapping(discovery.get("knn_setting_summary")), limit=16))
        lines.extend(_markdown_table("Discovery blockers", _list_of_mapping(discovery.get("blocker_counts")), limit=16))
        lines.extend(_markdown_table("Top interesting discovery rows", _list_of_mapping(discovery.get("top_interesting_candidates")), limit=12))
    else:
        lines.append(f"- unavailable: `{discovery.get('reason', 'not_provided')}`")
    lines.extend(["", "## Next Research Step", ""])
    for item in _list_of_text(interpretation.get("next_steps")):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _summarize_cycle(
    cycle_dir: Path | None,
    *,
    include_trade_sortino: bool,
    max_sortino_trade_files: int,
) -> dict[str, Any]:
    if cycle_dir is None:
        return {"available": False, "reason": "cycle_dir_not_provided"}
    if not cycle_dir.exists():
        return {"available": False, "reason": "cycle_dir_missing", "path": str(cycle_dir)}

    manifest = _read_json(cycle_dir / "research_cycle_manifest.json")
    outputs = _mapping(manifest.get("required_outputs"))
    rankings_path = _output_path(outputs, "candidate_rankings", cycle_dir / "candidate_rankings.parquet")
    gate_path = _output_path(outputs, "candidate_gate_report", cycle_dir / "candidate_gate_report.parquet")
    split_path = _output_path(outputs, "metrics_by_split", cycle_dir / "metrics_by_split.parquet")
    backtest_index_path = _output_path(outputs, "backtest_index", cycle_dir / "backtest_index.parquet")

    rankings = _read_frame(rankings_path)
    gate_report = _read_frame(gate_path)
    metrics_by_split = _read_frame(split_path)
    backtest_index = _read_frame(backtest_index_path)
    if include_trade_sortino and not rankings.empty and not backtest_index.empty:
        sortino = _trade_sortino_by_candidate(backtest_index, max_files=max_sortino_trade_files)
        if not sortino.empty:
            rankings = rankings.merge(sortino, on="candidate_id", how="left")

    gate_reasons = _reason_counts(gate_report.get("gate_reasons", pd.Series(dtype=object)))
    ranking_reasons = _reason_counts(rankings.get("failure_reasons", pd.Series(dtype=object)))
    pack_eligible = _pack_eligible_count(gate_report)
    top_columns = [
        "candidate_id",
        "strategy_id",
        "feature_set_id",
        "holding_window",
        "exit_policy_id",
        "costed_expectancy",
        PURE_ROI_COLUMN,
        "trade_sortino",
        "trade_count",
        "final_score",
        "decision",
    ]
    non_baseline_rankings = _non_baseline_frame(rankings)
    summary = {
        "available": True,
        "path": str(cycle_dir),
        "manifest": {
            "cycle_id": manifest.get("cycle_id"),
            "symbol": manifest.get("symbol"),
            "research_only": manifest.get("research_only"),
            "observe_only": manifest.get("observe_only"),
            "promotion_ready": manifest.get("promotion_ready"),
            "candidate_acceptance_scope": manifest.get("candidate_acceptance_scope"),
            "candidate_pack_written": manifest.get("candidate_pack_written"),
            "candidate_count": manifest.get("candidate_count"),
            "backtest_backend_summary": manifest.get("backtest_backend_summary"),
        },
        "data_window": _data_window(cycle_dir),
        "rankings": {
            "row_count": int(len(rankings)),
            "pack_eligible_count": pack_eligible,
            "positive_pure_roi_count": _positive_count(rankings, PURE_ROI_COLUMN),
            "positive_costed_expectancy_count": _positive_count(rankings, "costed_expectancy"),
            "decision_counts": _value_counts(rankings, "decision"),
            "feature_set_performance": _group_metric_summary(rankings, ["feature_set_id"], CYCLE_GROUP_METRICS),
            "strategy_performance": _group_metric_summary(rankings, ["strategy_id"], CYCLE_GROUP_METRICS),
            "exit_policy_performance": _group_metric_summary(rankings, ["exit_policy_id"], CYCLE_GROUP_METRICS),
            "holding_window_performance": _group_metric_summary(rankings, ["holding_window"], CYCLE_GROUP_METRICS),
            "top_candidates_by_pure_roi": _top_records(non_baseline_rankings, PURE_ROI_COLUMN, top_columns, limit=20),
            "top_candidates_by_sortino": _top_records(non_baseline_rankings, "trade_sortino", top_columns, limit=20),
        },
        "split_summary": _split_summary(metrics_by_split),
        "gate_reason_counts": gate_reasons,
        "ranking_failure_reason_counts": ranking_reasons,
    }
    return summary


def _summarize_discovery(discovery_dir: Path | None) -> dict[str, Any]:
    if discovery_dir is None:
        return {"available": False, "reason": "discovery_dir_not_provided"}
    if not discovery_dir.exists():
        return {"available": False, "reason": "discovery_dir_missing", "path": str(discovery_dir)}

    manifest = _read_json(discovery_dir / "discovery_run_manifest.json")
    outputs = _mapping(manifest.get("required_outputs"))
    interesting_path = _output_path(outputs, "interesting_candidates", discovery_dir / "candidate_ledgers" / "interesting_candidates.parquet")
    blocked_path = _output_path(outputs, "blocked_candidates", discovery_dir / "candidate_ledgers" / "blocked_candidates.parquet")
    filter_path = _output_path(outputs, "filter_blockers", discovery_dir / "candidate_ledgers" / "filter_blockers.parquet")

    interesting = _read_frame(interesting_path)
    blocked = _read_frame(blocked_path)
    filter_blockers = _read_frame(filter_path)
    combined = _combine_discovery_ledgers(
        [
            (interesting, "interesting"),
            (blocked, "blocked"),
            (filter_blockers, "filter_blocker"),
        ]
    )
    counts = _mapping(manifest.get("counts"))
    counts = {
        "completed_trials": counts.get("completed_trials", int(len(combined))),
        "interesting_candidates": counts.get("interesting_candidates", int(len(interesting))),
        "blocked_candidates": counts.get("blocked_candidates", int(len(blocked))),
        "filter_blockers": counts.get("filter_blockers", int(len(filter_blockers))),
        "ledger_rows_seen": int(len(combined)),
    }
    blocker_counts = _value_counts(blocked, "blocker_code")
    filter_blocker_counts = _value_counts(filter_blockers, "filter_blocker_code")
    top_columns = [
        "candidate_id",
        "feature_column_set_id",
        "label_horizon",
        "distance_metric",
        "k",
        "min_neighbor_count",
        "regime_mode",
        "trade_count",
        "accepted_bar_count",
        "independent_event_count",
        "realized_expectancy",
        "signal_rate",
        "event_signal_rate",
        "overlap_ratio",
        "side_collapse_ratio",
        "final_score",
    ]
    return {
        "available": True,
        "path": str(discovery_dir),
        "run_id": manifest.get("run_id"),
        "symbol": manifest.get("symbol"),
        "timeframe": manifest.get("timeframe"),
        "research_only": manifest.get("research_only"),
        "observe_only": manifest.get("observe_only"),
        "promotion_ready": manifest.get("promotion_ready"),
        "candidate_acceptance_scope": manifest.get("candidate_acceptance_scope"),
        "counts": counts,
        "feature_set_summary": _discovery_group_summary(combined, ["feature_column_set_id"], limit=20),
        "label_horizon_summary": _discovery_group_summary(combined, ["label_horizon"], limit=20),
        "knn_setting_summary": _discovery_group_summary(combined, DISCOVERY_GROUP_COLUMNS, limit=40),
        "blocker_counts": blocker_counts,
        "filter_blocker_counts": filter_blocker_counts,
        "top_interesting_candidates": _top_records(interesting, "final_score", top_columns, limit=30),
        "trial_execution_error_count": _count_matching(blocked, "blocker_code", "trial_execution_error"),
        "execution_observed": manifest.get("execution_observed"),
        "compute_telemetry": manifest.get("compute_telemetry"),
        "data_evidence": manifest.get("data_evidence"),
    }


def _trade_sortino_by_candidate(backtest_index: pd.DataFrame, *, max_files: int) -> pd.DataFrame:
    required = {"candidate_id", "evaluation_scope", "trades_path"}
    if not required <= set(backtest_index.columns):
        return pd.DataFrame(columns=["candidate_id", "trade_sortino", "sortino_trade_count"])
    aggregate = backtest_index[backtest_index["evaluation_scope"].astype(str).eq("aggregate")]
    rows: list[dict[str, Any]] = []
    seen = 0
    for candidate_id, trades_path in aggregate[["candidate_id", "trades_path"]].itertuples(index=False):
        if seen >= max_files:
            break
        path = Path(str(trades_path))
        if not path.exists():
            continue
        seen += 1
        try:
            trades = pd.read_parquet(path, columns=["net_return"])
        except Exception:
            continue
        returns = pd.to_numeric(trades.get("net_return", pd.Series(dtype=float)), errors="coerce").dropna()
        rows.append(
            {
                "candidate_id": candidate_id,
                "trade_sortino": _sortino(returns),
                "sortino_trade_count": int(len(returns)),
            }
        )
    return pd.DataFrame(rows)


def _sortino(returns: pd.Series) -> float | None:
    if returns.empty:
        return None
    mean_return = float(returns.mean())
    downside = returns[returns < 0.0]
    if downside.empty:
        return None
    downside_std = float(downside.std(ddof=0))
    if downside_std <= 0.0 or not math.isfinite(downside_std):
        return None
    value = mean_return / downside_std * math.sqrt(float(len(returns)))
    return value if math.isfinite(value) else None


def _group_metric_summary(
    frame: pd.DataFrame,
    group_columns: Iterable[str],
    metric_columns: Iterable[str],
    *,
    limit: int = 40,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    columns = [column for column in group_columns if column in frame.columns]
    if not columns:
        return []
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(columns, dropna=False):
        row = _group_key_row(columns, key)
        row["candidate_count"] = int(len(group))
        row["pack_eligible_count"] = _pack_eligible_count(group)
        for metric in metric_columns:
            if metric not in group.columns:
                continue
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            if values.empty:
                continue
            row[f"{metric}_mean"] = float(values.mean())
            row[f"{metric}_median"] = float(values.median())
            row[f"{metric}_max"] = float(values.max())
            row[f"{metric}_min"] = float(values.min())
            row[f"{metric}_positive_count"] = int((values > 0.0).sum())
        rows.append(row)
    return sorted(
        _json_safe(rows),
        key=lambda row: (
            float(row.get(f"{PURE_ROI_COLUMN}_max") or float("-inf")),
            float(row.get("trade_sortino_max") or float("-inf")),
            float(row.get("costed_expectancy_max") or float("-inf")),
        ),
        reverse=True,
    )[:limit]


def _discovery_group_summary(
    frame: pd.DataFrame,
    group_columns: Iterable[str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    columns = [column for column in group_columns if column in frame.columns]
    if not columns:
        return []
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(columns, dropna=False):
        ledger_kind = group.get("ledger_kind", pd.Series(dtype=object)).astype(str)
        interesting_count = int(ledger_kind.eq("interesting").sum())
        total = int(len(group))
        row = _group_key_row(columns, key)
        row["total_trials"] = total
        row["interesting_trials"] = interesting_count
        row["blocked_trials"] = int(ledger_kind.eq("blocked").sum())
        row["filter_blocker_trials"] = int(ledger_kind.eq("filter_blocker").sum())
        row["interesting_rate"] = interesting_count / total if total else 0.0
        for metric in DISCOVERY_GROUP_METRICS:
            if metric not in group.columns:
                continue
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            if values.empty:
                continue
            row[f"{metric}_mean"] = float(values.mean())
            row[f"{metric}_max"] = float(values.max())
            row[f"{metric}_min"] = float(values.min())
        rows.append(row)
    return sorted(
        _json_safe(rows),
        key=lambda row: (
            int(row.get("interesting_trials") or 0),
            float(row.get("interesting_rate") or 0.0),
            float(row.get("realized_expectancy_max") or float("-inf")),
            float(row.get("final_score_max") or float("-inf")),
        ),
        reverse=True,
    )[:limit]


def _split_summary(metrics_by_split: pd.DataFrame) -> dict[str, Any]:
    if metrics_by_split.empty:
        return {"available": False, "reason": "metrics_by_split_missing"}
    return {
        "available": True,
        "row_count": int(len(metrics_by_split)),
        "validation_method_counts": _value_counts(metrics_by_split, "validation_method"),
        "split_mode_counts": _value_counts(metrics_by_split, "split_mode"),
        "min_trade_count": _numeric_stat(metrics_by_split, "trade_count", "min"),
        "max_trade_count": _numeric_stat(metrics_by_split, "trade_count", "max"),
        "max_pure_roi": _numeric_stat(metrics_by_split, PURE_ROI_COLUMN, "max"),
        "min_pure_roi": _numeric_stat(metrics_by_split, PURE_ROI_COLUMN, "min"),
    }


def _data_window(cycle_dir: Path) -> dict[str, Any]:
    report = _read_json(cycle_dir / "data_quality_report.json")
    time_span = _mapping(report.get("time_span"))
    source = _mapping(report.get("data_source"))
    derivation = _mapping(source.get("fixture_derivation"))
    return {
        "row_count": report.get("row_count") or derivation.get("row_count"),
        "first_time": _timestamp_label(time_span.get("first_time") or time_span.get("start_time") or derivation.get("first_time_ms")),
        "last_time": _timestamp_label(time_span.get("last_time") or time_span.get("end_time") or derivation.get("last_time_ms")),
        "base_interval": source.get("base_interval"),
        "dataset_path": source.get("dataset_path"),
        "derivation_type": derivation.get("derivation_type"),
        "period_count": len(_list(derivation.get("periods"))),
        "notes": _list(derivation.get("notes")),
    }


def _non_baseline_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "strategy_id" not in frame.columns:
        return frame
    filtered = frame[~frame["strategy_id"].fillna("").astype(str).eq("baseline_no_trade")]
    return filtered if not filtered.empty else frame


def _timestamp_label(value: Any) -> Any:
    if value is None or value == "":
        return value
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        numeric = float(value)
        unit = "ms" if abs(numeric) > 10_000_000_000 else "s"
        return pd.to_datetime(numeric, unit=unit, utc=True).isoformat()
    return value


def _build_interpretation(analysis: Mapping[str, Any]) -> dict[str, list[str]]:
    cycle = _mapping(analysis.get("cycle"))
    discovery = _mapping(analysis.get("discovery"))
    takeaways: list[str] = []
    next_steps: list[str] = []

    if cycle.get("available"):
        rankings = _mapping(cycle.get("rankings"))
        if int(rankings.get("pack_eligible_count") or 0) <= 0:
            takeaways.append("The historical cycle remains fail-closed: no candidate is pack eligible from this evidence.")
        if int(rankings.get("positive_pure_roi_count") or 0) <= 0:
            takeaways.append("The current brute-force cycle did not produce a positive pure-ROI candidate.")
        exit_policy_rows = _list_of_mapping(rankings.get("exit_policy_performance"))
        if len(exit_policy_rows) == 1 and str(exit_policy_rows[0].get("exit_policy_id")) == "fixed_holding_window":
            takeaways.append("The completed cycle only tested fixed-holding exits; frozen-entry exit-model comparison still has to run.")
    if discovery.get("available"):
        counts = _mapping(discovery.get("counts"))
        if int(counts.get("interesting_candidates") or 0) > 0:
            takeaways.append("Exact discovery found interesting KNN entry rows, but they are not candidate-pack evidence until exit, split, cost-stress, and gate review pass.")
        if int(discovery.get("trial_execution_error_count") or 0) > 0:
            takeaways.append("The exact ledger still contains trial execution errors; repair or retry those rows before treating the sweep as analytically clean.")
    next_steps.extend(
        [
            "Run the same analysis step after every BTC/ETH cycle and exact discovery run before deciding the next search mutation.",
            "Add a one-button research autopilot that refreshes/reuses the catalog, runs BTC/ETH cycle and discovery jobs, runs this analysis, and writes run-to-run deltas.",
            "Run frozen-entry exit labs on the strongest exact-discovery entry rows before expanding more feature/filter combinations.",
            "Compare full-window evidence with a modern-window profile so early crypto market structure does not dominate current-regime results.",
            "Promote orderflow and KNN feature/filter ablations into the active specs only when matched simple baselines survive.",
        ]
    )
    return {"takeaways": takeaways, "next_steps": next_steps}


def _combine_discovery_ledgers(frames: Iterable[tuple[pd.DataFrame, str]]) -> pd.DataFrame:
    normalized: list[pd.DataFrame] = []
    for frame, default_kind in frames:
        if frame.empty:
            continue
        copy = frame.copy()
        if "ledger_kind" not in copy.columns:
            copy["ledger_kind"] = default_kind
        normalized.append(copy)
    if not normalized:
        return pd.DataFrame()
    return pd.concat(normalized, ignore_index=True, sort=False)


def _top_records(frame: pd.DataFrame, sort_column: str, columns: Iterable[str], *, limit: int) -> list[dict[str, Any]]:
    if frame.empty or sort_column not in frame.columns:
        return []
    selected = [column for column in columns if column in frame.columns]
    if not selected:
        return []
    sortable = frame.copy()
    sortable[sort_column] = pd.to_numeric(sortable[sort_column], errors="coerce")
    sortable = sortable.dropna(subset=[sort_column])
    if sortable.empty:
        return []
    return _json_safe(sortable.sort_values(sort_column, ascending=False).head(limit)[selected].to_dict("records"))


def _reason_counts(series: pd.Series) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for value in series.dropna().tolist():
        for reason in _split_reasons(value):
            counts[reason] = counts.get(reason, 0) + 1
    return [{"reason": reason, "count": count} for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _split_reasons(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    delimiter = "|" if "|" in text else ","
    return [item.strip() for item in text.split(delimiter) if item.strip()]


def _value_counts(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if frame.empty or column not in frame.columns:
        return []
    values = frame[column].fillna("").astype(str).str.strip()
    counts = values[values.ne("")].value_counts()
    return [{"value": index, "count": int(value)} for index, value in counts.items()]


def _count_matching(frame: pd.DataFrame, column: str, value: str) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    return int(frame[column].fillna("").astype(str).eq(value).sum())


def _pack_eligible_count(frame: pd.DataFrame) -> int:
    if frame.empty or "pack_eligible" not in frame.columns:
        return 0
    values = frame["pack_eligible"]
    if values.dtype == bool:
        return int(values.sum())
    return int(values.astype(str).str.lower().isin({"true", "1", "yes", "passed"}).sum())


def _positive_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    return int((pd.to_numeric(frame[column], errors="coerce").fillna(0.0) > 0.0).sum())


def _numeric_stat(frame: pd.DataFrame, column: str, stat: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return None
    if stat == "min":
        return float(values.min())
    if stat == "max":
        return float(values.max())
    if stat == "mean":
        return float(values.mean())
    raise ValueError(f"unsupported stat: {stat}")


def _group_key_row(columns: list[str], key: Any) -> dict[str, Any]:
    if len(columns) == 1 and not isinstance(key, tuple):
        values = (key,)
    else:
        values = tuple(key)
    return {column: _json_safe_value(value) for column, value in zip(columns, values)}


def _output_path(outputs: Mapping[str, Any], key: str, fallback: Path) -> Path:
    value = outputs.get(key)
    if value:
        return Path(str(value))
    return fallback


def _read_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return _json_safe_value(value)


def _json_safe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return _json_safe_value(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _list_of_mapping(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _list_of_text(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _markdown_table(title: str, rows: list[Mapping[str, Any]], *, limit: int) -> list[str]:
    if not rows:
        return [f"### {title}", "", "_No rows._", ""]
    preferred = [
        "feature_set_id",
        "feature_column_set_id",
        "strategy_id",
        "exit_policy_id",
        "holding_window",
        "label_horizon",
        "distance_metric",
        "k",
        "min_neighbor_count",
        "regime_mode",
        "candidate_count",
        "total_trials",
        "interesting_trials",
        "interesting_rate",
        f"{PURE_ROI_COLUMN}_max",
        "costed_expectancy_max",
        "trade_sortino_max",
        "realized_expectancy_max",
        "final_score_max",
        "count",
        "reason",
        "value",
        "candidate_id",
        PURE_ROI_COLUMN,
        "trade_sortino",
        "realized_expectancy",
        "trade_count",
    ]
    columns = [column for column in preferred if any(column in row for row in rows)]
    if not columns:
        columns = list(rows[0].keys())[:8]
    columns = columns[:10]
    lines = [f"### {title}", "", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(_markdown_cell(row.get(column)) for column in columns) + " |")
    lines.append("")
    return lines


def _markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write research-only cycle/discovery analysis artifacts.")
    parser.add_argument("--cycle", dest="cycle_dir", default=None, help="Historical cycle output directory.")
    parser.add_argument("--discovery", dest="discovery_dir", default=None, help="Exact discovery output directory.")
    parser.add_argument("--out", dest="output_dir", required=True, help="Output directory for analysis artifacts.")
    parser.add_argument(
        "--skip-trade-sortino",
        action="store_true",
        help="Do not read aggregate trade ledgers to compute trade-level Sortino.",
    )
    parser.add_argument(
        "--max-sortino-trade-files",
        type=int,
        default=1000,
        help="Maximum aggregate trade parquet files to read for Sortino analysis.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    result = write_research_analysis_artifacts(
        cycle_dir=args.cycle_dir,
        discovery_dir=args.discovery_dir,
        output_dir=args.output_dir,
        include_trade_sortino=not args.skip_trade_sortino,
        max_sortino_trade_files=args.max_sortino_trade_files,
    )
    print(result.analysis_json_path)
    print(result.markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
