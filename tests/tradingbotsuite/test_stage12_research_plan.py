from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from tradingbotsuite import main
from tradingbotsuite.research.stage12_research import (
    STAGE12_RESEARCH_MANIFEST_VERSION,
    stage12_research_tracks,
    write_stage12_research_plan,
)


def test_stage12_research_plan_covers_all_remaining_substages_and_writes_limitations(tmp_path: Path) -> None:
    result = write_stage12_research_plan(output_dir=tmp_path / "stage12", dataset_manifest_hash="sha256:dataset")

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.summary_path)
    limitations = result.limitations_path.read_text(encoding="utf-8")

    assert manifest["stage12_research_manifest_version"] == STAGE12_RESEARCH_MANIFEST_VERSION
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["stage12_exit_gate"]["research_tracks_produce_reproducible_experiment_manifests"] is True
    assert manifest["stage12_exit_gate"]["in_sample_only_promotion_allowed"] is False
    assert manifest["empirical_completion"]["complete"] is False
    assert set(manifest["substage_status"]) == {"12.1", "12.2", "12.3", "12.4", "12.5", "12.6", "12.7"}
    assert len(manifest["tracks"]) == 46
    assert len(summary) == 46
    assert len(list(result.experiment_spec_dir.glob("*.json"))) == len(stage12_research_tracks())
    assert result.feature_ablation_manifest_path.exists()
    assert "Portfolio allocation tracks are blocked until single-strategy evidence passes." in limitations
    assert "No hypothesis is promotion-ready" in limitations


def test_stage12_research_accepts_only_oos_stress_evidence_and_rejects_in_sample(tmp_path: Path) -> None:
    good_evidence = {
        "oos_costed_expectancy": 0.02,
        "stress_passed": True,
        "walk_forward_split_count": 6,
        "max_single_split_pnl_share": 0.25,
        "side_separated_outcomes": {"long": {"expectancy": 0.01}, "short": {"expectancy": 0.011}},
        "rows_per_regime": {"trend": 1200, "chop": 1100},
        "regime_stability": {"median_duration_bars": 24},
        "transition_frequency": 0.04,
        "no_trade_rate": 0.25,
        "per_regime_expectancy": {"trend": 0.02, "chop": 0.01},
        "regime_drift_over_time": {"max_psi": 0.08},
    }
    bad_evidence = {
        **good_evidence,
        "stress_passed": False,
        "in_sample_only": True,
    }

    result = write_stage12_research_plan(
        output_dir=tmp_path / "stage12",
        dataset_manifest_hash="sha256:dataset",
        evidence_by_hypothesis={
            "hmm_regime_model": good_evidence,
            "gaussian_mixture_regimes": bad_evidence,
        },
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    rows = {row["hypothesis_id"]: row for row in manifest["tracks"]}

    assert rows["hmm_regime_model"]["decision"] == "accepted"
    assert "hmm_regime_model" in manifest["accepted_hypotheses"]
    assert rows["gaussian_mixture_regimes"]["decision"] == "rejected"
    assert "stress_gates_not_passed" in rows["gaussian_mixture_regimes"]["failure_reasons"]
    assert "in_sample_only_result_not_accepted" in rows["gaussian_mixture_regimes"]["failure_reasons"]


def test_stage12_research_cli_command_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tradingbot",
            "plan-stage12-research",
            "--output-dir",
            str(tmp_path / "stage12-cli"),
            "--dataset-manifest-hash",
            "sha256:dataset",
        ],
    )

    args = main.parse_args()
    payload = main._run_plan_stage12_research_command(args)

    assert Path(str(payload["stage12_research_manifest_path"])).exists()
    assert Path(str(payload["limitations_path"])).exists()
