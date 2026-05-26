from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from tradingbotsuite.research_discovery.analysis_report import PURE_ROI_COLUMN
from tradingbotsuite.research_discovery.state import atomic_write_json


RESEARCH_ANALYSIS_DELTA_VERSION = "research-discovery-analysis-delta-v1"


@dataclass(frozen=True, slots=True)
class ResearchAnalysisDeltaArtifactResult:
    delta_json_path: Path
    markdown_path: Path
    delta: Mapping[str, Any]


def build_research_analysis_delta(
    *,
    current_analysis_path: str | Path,
    previous_analysis_path: str | Path | None = None,
) -> dict[str, Any]:
    current_path = Path(current_analysis_path).expanduser().resolve()
    current = _read_json(current_path)
    previous_path = Path(previous_analysis_path).expanduser().resolve() if previous_analysis_path else None
    previous = _read_json(previous_path) if previous_path is not None and previous_path.is_file() else None

    blockers: list[str] = []
    if previous is None:
        blockers.append("prior_analysis_not_found")
    current_ref = _analysis_ref(current, current_path)
    previous_ref = _analysis_ref(previous, previous_path) if previous is not None and previous_path is not None else None
    symbol_match = previous_ref is None or current_ref.get("symbol") == previous_ref.get("symbol")
    if not symbol_match:
        blockers.append("analysis_symbol_mismatch")

    delta = {
        "delta_version": RESEARCH_ANALYSIS_DELTA_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "intended_use": "research_artifact_run_to_run_review_only",
        "current": current_ref,
        "previous": previous_ref,
        "comparison_scope": {
            "symbol_match": bool(symbol_match),
            "cycle_id_changed": previous_ref is not None and current_ref.get("cycle_id") != previous_ref.get("cycle_id"),
            "discovery_run_id_changed": previous_ref is not None and current_ref.get("discovery_run_id") != previous_ref.get("discovery_run_id"),
            "compatible": not blockers,
            "blocked_reasons": blockers,
        },
        "cycle_delta": _cycle_delta(current, previous),
        "discovery_delta": _discovery_delta(current, previous),
        "leaders": _leader_delta(current, previous),
        "interpretation": {},
    }
    delta["interpretation"] = _interpret_delta(delta)
    return _json_safe(delta)


def write_research_analysis_delta_artifacts(
    *,
    current_analysis_path: str | Path,
    previous_analysis_path: str | Path | None,
    output_dir: str | Path,
) -> ResearchAnalysisDeltaArtifactResult:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    delta = build_research_analysis_delta(
        current_analysis_path=current_analysis_path,
        previous_analysis_path=previous_analysis_path,
    )
    delta_json_path = output / "research_analysis_delta.json"
    markdown_path = output / "research_analysis_delta.md"
    atomic_write_json(delta_json_path, delta)
    markdown_path.write_text(render_research_analysis_delta_markdown(delta), encoding="utf-8")
    return ResearchAnalysisDeltaArtifactResult(delta_json_path=delta_json_path, markdown_path=markdown_path, delta=delta)


def render_research_analysis_delta_markdown(delta: Mapping[str, Any]) -> str:
    current = _mapping(delta.get("current"))
    previous = _mapping(delta.get("previous"))
    scope = _mapping(delta.get("comparison_scope"))
    cycle = _mapping(delta.get("cycle_delta"))
    discovery = _mapping(delta.get("discovery_delta"))
    lines = [
        "# R106 Research Analysis Delta",
        "",
        "This is research-only run-to-run review. It is not a promotion claim and does not change live runtime state.",
        "",
        f"- Current: `{current.get('analysis_path', '')}`",
        f"- Previous: `{previous.get('analysis_path', 'none') if previous else 'none'}`",
        f"- Compatible: `{scope.get('compatible')}`",
        f"- Blockers: `{', '.join(scope.get('blocked_reasons') or []) or 'none'}`",
        "",
        "## Cycle Delta",
        "",
        f"- Candidate count delta: `{cycle.get('candidate_count_delta')}`",
        f"- Pack eligible delta: `{cycle.get('pack_eligible_count_delta')}`",
        f"- Best pure ROI delta: `{cycle.get('best_pure_roi_delta')}`",
        f"- Best Sortino delta: `{cycle.get('best_trade_sortino_delta')}`",
        "",
        "## Discovery Delta",
        "",
        f"- Completed trials delta: `{discovery.get('completed_trials_delta')}`",
        f"- Interesting candidates delta: `{discovery.get('interesting_candidates_delta')}`",
        f"- Interesting rate delta: `{discovery.get('interesting_rate_delta')}`",
        "",
        "## Takeaways",
        "",
    ]
    interpretation = _mapping(delta.get("interpretation"))
    for item in interpretation.get("takeaways") or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _analysis_ref(payload: Mapping[str, Any] | None, path: Path | None) -> dict[str, Any]:
    payload = payload or {}
    cycle = _mapping(payload.get("cycle"))
    cycle_manifest = _mapping(cycle.get("manifest"))
    discovery = _mapping(payload.get("discovery"))
    return {
        "analysis_path": str(path) if path is not None else None,
        "analysis_version": payload.get("analysis_version"),
        "symbol": discovery.get("symbol") or cycle_manifest.get("symbol"),
        "cycle_id": cycle_manifest.get("cycle_id"),
        "discovery_run_id": discovery.get("run_id"),
        "cycle_path": cycle.get("path"),
        "discovery_path": discovery.get("path"),
    }


def _cycle_delta(current: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any]:
    current_rankings = _mapping(_mapping(current.get("cycle")).get("rankings"))
    previous_rankings = _mapping(_mapping((previous or {}).get("cycle")).get("rankings"))
    return {
        "available": bool(current_rankings),
        "candidate_count_delta": _int_delta(current_rankings, previous_rankings, "row_count"),
        "pack_eligible_count_delta": _int_delta(current_rankings, previous_rankings, "pack_eligible_count"),
        "positive_pure_roi_count_delta": _int_delta(current_rankings, previous_rankings, "positive_pure_roi_count"),
        "positive_costed_expectancy_count_delta": _int_delta(current_rankings, previous_rankings, "positive_costed_expectancy_count"),
        "best_pure_roi_delta": _best_metric_delta(current_rankings, previous_rankings, "top_candidates_by_pure_roi", PURE_ROI_COLUMN),
        "best_trade_sortino_delta": _best_metric_delta(current_rankings, previous_rankings, "top_candidates_by_sortino", "trade_sortino"),
        "gate_reason_count_delta": _count_list_delta(
            _mapping(current.get("cycle")).get("gate_reason_counts"),
            _mapping((previous or {}).get("cycle")).get("gate_reason_counts"),
        ),
    }


def _discovery_delta(current: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any]:
    current_counts = _mapping(_mapping(current.get("discovery")).get("counts"))
    previous_counts = _mapping(_mapping((previous or {}).get("discovery")).get("counts"))
    current_completed = _number(current_counts.get("completed_trials"))
    previous_completed = _number(previous_counts.get("completed_trials"))
    current_interesting = _number(current_counts.get("interesting_candidates"))
    previous_interesting = _number(previous_counts.get("interesting_candidates"))
    return {
        "available": bool(current_counts),
        "completed_trials_delta": _numeric_delta(current_completed, previous_completed),
        "interesting_candidates_delta": _numeric_delta(current_interesting, previous_interesting),
        "blocked_candidates_delta": _int_delta(current_counts, previous_counts, "blocked_candidates"),
        "filter_blockers_delta": _int_delta(current_counts, previous_counts, "filter_blockers"),
        "interesting_rate_delta": _numeric_delta(
            _rate(current_interesting, current_completed),
            _rate(previous_interesting, previous_completed),
        ),
        "top_blocker_count_delta": _count_list_delta(
            _mapping(current.get("discovery")).get("blocker_counts"),
            _mapping((previous or {}).get("discovery")).get("blocker_counts"),
        ),
    }


def _leader_delta(current: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any]:
    current_rankings = _mapping(_mapping(current.get("cycle")).get("rankings"))
    previous_rankings = _mapping(_mapping((previous or {}).get("cycle")).get("rankings"))
    current_discovery = _mapping(current.get("discovery"))
    previous_discovery = _mapping((previous or {}).get("discovery"))
    return {
        "new_top_cycle_candidates": _new_ids(current_rankings.get("top_candidates_by_pure_roi"), previous_rankings.get("top_candidates_by_pure_roi"), "candidate_id"),
        "dropped_top_cycle_candidates": _new_ids(previous_rankings.get("top_candidates_by_pure_roi"), current_rankings.get("top_candidates_by_pure_roi"), "candidate_id"),
        "new_top_discovery_candidates": _new_ids(current_discovery.get("top_interesting_candidates"), previous_discovery.get("top_interesting_candidates"), "candidate_id"),
        "dropped_top_discovery_candidates": _new_ids(previous_discovery.get("top_interesting_candidates"), current_discovery.get("top_interesting_candidates"), "candidate_id"),
    }


def _interpret_delta(delta: Mapping[str, Any]) -> dict[str, list[str]]:
    blockers = list(_mapping(delta.get("comparison_scope")).get("blocked_reasons") or [])
    takeaways: list[str] = []
    next_steps: list[str] = []
    if blockers:
        takeaways.append("No compatible prior analysis was available, so this delta establishes the comparison baseline.")
        next_steps.append("Keep this artifact and compare the next completed analysis against it.")
    else:
        discovery = _mapping(delta.get("discovery_delta"))
        interesting_delta = _number(discovery.get("interesting_candidates_delta"))
        takeaways.append(
            "Interesting discovery count improved versus the prior analysis."
            if interesting_delta > 0
            else "Interesting discovery count did not improve versus the prior analysis."
        )
        cycle = _mapping(delta.get("cycle_delta"))
        roi_delta = _number(cycle.get("best_pure_roi_delta"))
        takeaways.append(
            "Best pure ROI improved versus the prior analysis."
            if roi_delta > 0
            else "Best pure ROI did not improve versus the prior analysis."
        )
        next_steps.append("Inspect changed blockers, leaders, and exit-lab evidence before expanding the search surface.")
    return {"takeaways": takeaways, "next_steps": next_steps}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"analysis artifact must be a JSON object: {path}")
    return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def _numeric_delta(current: float, previous: float) -> float | None:
    if previous == 0.0:
        return current if current != 0.0 else 0.0
    return current - previous


def _int_delta(current: Mapping[str, Any], previous: Mapping[str, Any], key: str) -> int:
    return int(_number(current.get(key)) - _number(previous.get(key)))


def _best_metric_delta(current: Mapping[str, Any], previous: Mapping[str, Any], group_key: str, metric: str) -> float | None:
    return _number(_first_metric(current.get(group_key), metric)) - _number(_first_metric(previous.get(group_key), metric))


def _first_metric(rows: Any, metric: str) -> Any:
    if isinstance(rows, list) and rows and isinstance(rows[0], Mapping):
        return rows[0].get(metric)
    return None


def _rate(numerator: float, denominator: float) -> float:
    return 0.0 if denominator <= 0.0 else numerator / denominator


def _count_list_delta(current_rows: Any, previous_rows: Any) -> list[dict[str, Any]]:
    current = _count_map(current_rows)
    previous = _count_map(previous_rows)
    rows = [
        {"value": key, "delta": current.get(key, 0) - previous.get(key, 0)}
        for key in sorted(set(current) | set(previous))
    ]
    return [row for row in rows if row["delta"] != 0]


def _count_map(rows: Any) -> dict[str, int]:
    result: dict[str, int] = {}
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        key = str(row.get("value") or "")
        if key:
            result[key] = int(_number(row.get("count")))
    return result


def _new_ids(current_rows: Any, previous_rows: Any, key: str) -> list[str]:
    current = _id_set(current_rows, key)
    previous = _id_set(previous_rows, key)
    return sorted(current - previous)[:20]


def _id_set(rows: Any, key: str) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {str(row.get(key)) for row in rows if isinstance(row, Mapping) and row.get(key)}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
