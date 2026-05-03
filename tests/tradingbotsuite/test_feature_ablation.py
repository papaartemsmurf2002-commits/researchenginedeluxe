from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from tradingbotsuite import main
from tradingbotsuite.research.feature_ablation import (
    FEATURE_ABLATION_MANIFEST_VERSION,
    stage12_feature_ablation_tracks,
    write_feature_ablation_plan,
)


def test_stage12_feature_ablation_plan_covers_required_tracks_and_writes_specs(tmp_path: Path) -> None:
    result = write_feature_ablation_plan(output_dir=tmp_path / "ablation", dataset_manifest_hash="sha256:dataset")

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.summary_path)
    rejected = result.rejected_hypotheses_path.read_text(encoding="utf-8")

    assert manifest["feature_ablation_manifest_version"] == FEATURE_ABLATION_MANIFEST_VERSION
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["promotion_guard"]["live_execution_input"] is False
    assert manifest["hypothesis_count"] == 8
    assert set(manifest["required_plan_tracks"]) == {
        "full WT3D feature pack",
        "no WT3D",
        "price/trend/vol only",
        "perp context only",
        "microstructure context only as filter",
        "full context no WT",
        "full context with WT",
        "cross-asset context",
    }
    assert set(summary["hypothesis_id"]) == {track.hypothesis_id for track in stage12_feature_ablation_tracks()}
    assert set(summary["decision"]) == {"pending_evidence"}
    assert "evidence_not_supplied" in rejected
    assert (result.experiment_spec_dir / "full_context_with_wt.json").exists()
    assert (result.experiment_spec_dir / "microstructure_context_filter_only.json").exists()


def test_stage12_feature_ablation_rejects_weak_evidence_and_accepts_only_oos_stress(tmp_path: Path) -> None:
    result = write_feature_ablation_plan(
        output_dir=tmp_path / "ablation",
        dataset_manifest_hash="sha256:dataset",
        evidence_by_hypothesis={
            "full_context_with_wt": {
                "oos_costed_expectancy": 0.01,
                "stress_passed": True,
                "walk_forward_split_count": 6,
                "max_single_split_pnl_share": 0.25,
                "feature_missingness_rate": 0.01,
                "feature_missingness_ceiling": 0.05,
                "side_separated_outcomes": {"long": {"expectancy": 0.01}, "short": {"expectancy": 0.008}},
                "wt3d_ablation_survives": True,
            },
            "full_wt3d_feature_pack": {
                "oos_costed_expectancy": 0.02,
                "stress_passed": False,
                "walk_forward_split_count": 3,
                "max_single_split_pnl_share": 0.75,
                "feature_missingness_rate": 0.10,
                "feature_missingness_ceiling": 0.05,
                "side_separated_outcomes": {"long": {"expectancy": 0.01}},
                "wt3d_ablation_survives": False,
                "in_sample_only": True,
            },
        },
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    rows = {row["hypothesis_id"]: row for row in manifest["tracks"]}

    assert "full_context_with_wt" in manifest["accepted_hypotheses"]
    assert rows["full_context_with_wt"]["decision"] == "accepted"
    assert rows["full_wt3d_feature_pack"]["decision"] == "rejected"
    assert "stress_gates_not_passed" in rows["full_wt3d_feature_pack"]["failure_reasons"]
    assert "in_sample_only_result_not_accepted" in rows["full_wt3d_feature_pack"]["failure_reasons"]


def test_plan_feature_ablation_cli_command_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tradingbot",
            "plan-feature-ablation",
            "--output-dir",
            str(tmp_path / "cli-ablation"),
            "--dataset-manifest-hash",
            "sha256:dataset",
        ],
    )

    args = main.parse_args()
    payload = main._run_plan_feature_ablation_command(args)

    assert Path(str(payload["feature_ablation_manifest_path"])).exists()
    assert Path(str(payload["summary_path"])).exists()
