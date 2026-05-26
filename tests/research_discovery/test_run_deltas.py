from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.research_discovery.run_deltas import (
    RESEARCH_ANALYSIS_DELTA_VERSION,
    build_research_analysis_delta,
    write_research_analysis_delta_artifacts,
)


def _analysis(path: Path, *, run_id: str, interesting: int, roi: float) -> Path:
    payload = {
        "analysis_version": "research-analysis-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "cycle": {
            "available": True,
            "path": str(path.parent / "research_cycle_manifest.json"),
            "manifest": {"cycle_id": "cycle-btc", "symbol": "BTCUSDT"},
            "rankings": {
                "row_count": 4,
                "pack_eligible_count": 0,
                "positive_pure_roi_count": 1,
                "positive_costed_expectancy_count": 1,
                "top_candidates_by_pure_roi": [
                    {"candidate_id": "candidate-a", "net_return_after_fees_slippage_funding": roi}
                ],
                "top_candidates_by_sortino": [{"candidate_id": "candidate-a", "trade_sortino": roi * 10}],
            },
        },
        "discovery": {
            "available": True,
            "path": str(path.parent / "discovery_run_manifest.json"),
            "symbol": "BTCUSDT",
            "run_id": run_id,
            "counts": {
                "completed_trials": 100,
                "interesting_candidates": interesting,
                "blocked_candidates": 3,
                "filter_blockers": 2,
            },
            "top_interesting_candidates": [{"candidate_id": "candidate-a"}],
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_build_research_analysis_delta_compares_cycle_and_discovery(tmp_path: Path) -> None:
    previous = _analysis(tmp_path / "previous" / "research_analysis.json", run_id="run-btc-v1", interesting=1, roi=0.02)
    current = _analysis(tmp_path / "current" / "research_analysis.json", run_id="run-btc-v2", interesting=4, roi=0.05)

    delta = build_research_analysis_delta(current_analysis_path=current, previous_analysis_path=previous)

    assert delta["delta_version"] == RESEARCH_ANALYSIS_DELTA_VERSION
    assert delta["comparison_scope"]["compatible"] is True
    assert delta["discovery_delta"]["interesting_candidates_delta"] == 3
    assert delta["cycle_delta"]["best_pure_roi_delta"] == pytest.approx(0.03)
    assert delta["research_only"] is True
    assert delta["observe_only"] is True
    assert delta["promotion_ready"] is False


def test_write_research_analysis_delta_artifacts_records_missing_prior_baseline(tmp_path: Path) -> None:
    current = _analysis(tmp_path / "current" / "research_analysis.json", run_id="run-btc-v1", interesting=2, roi=0.01)

    result = write_research_analysis_delta_artifacts(
        current_analysis_path=current,
        previous_analysis_path=None,
        output_dir=tmp_path / "delta",
    )

    assert result.delta_json_path.exists()
    assert result.markdown_path.exists()
    payload = json.loads(result.delta_json_path.read_text(encoding="utf-8"))
    assert payload["comparison_scope"]["compatible"] is False
    assert payload["comparison_scope"]["blocked_reasons"] == ["prior_analysis_not_found"]
    assert "comparison baseline" in result.markdown_path.read_text(encoding="utf-8")
