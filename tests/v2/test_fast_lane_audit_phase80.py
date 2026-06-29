from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pytest

from tradingbotsuite.v2.backtest_engine import (
    ArtifactMode,
    BacktestRunConfig,
    EngineLane,
    FastLaneParityStatus,
    FullArtifactReplayVerificationStatus,
    audit_fast_lane_parity,
    build_full_artifact_replay_plan,
    build_reference_rerun_plan,
    run_vectorized_backtest,
    select_reference_audit_sample,
    verify_full_artifact_replay,
)
from tradingbotsuite.v2.strategy_specs import compile_signal_frame, example_strategy_payloads


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
ROOT = Path(__file__).resolve().parents[2]


def test_fast_lane_parity_report_records_benchmark_speedup_without_claim(tmp_path) -> None:
    panel = _panel_rows()
    spec = _short_spec()
    signal_frame = compile_signal_frame(spec, panel)
    reference = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="reference-audit").model_copy(
            update={"benchmark_enabled": True}
        ),
        strategy_spec=spec,
        panel_rows=panel,
    )
    fast = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="fast-audit").model_copy(
            update={"engine_lane": EngineLane.FAST_VECTORIZED, "benchmark_enabled": True}
        ),
        strategy_spec=spec,
        panel_table=pa.Table.from_pylist(panel),
        signal_frame=signal_frame,
    )

    report = audit_fast_lane_parity(
        reference_manifest=reference.manifest,
        fast_manifest=fast.manifest,
    )

    assert report.status == FastLaneParityStatus.PASS
    assert report.suspicious_result is False
    assert report.rerun_plan is None
    assert report.speedup_claimed is False
    assert report.benchmark_observations["reference_runtime_seconds"] >= 0.0
    assert report.benchmark_observations["fast_runtime_seconds"] >= 0.0
    assert report.benchmark_observations["speedup_ratio"] >= 0.0
    assert all(row.within_tolerance for row in report.metric_diffs)
    assert report.research_only is True
    assert report.promotion_ready is False


def test_fast_lane_parity_rejects_speedup_claim_without_complete_benchmark_evidence(tmp_path) -> None:
    panel = _panel_rows()
    spec = _short_spec()
    signal_frame = compile_signal_frame(spec, panel)
    reference = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="reference-incomplete-speedup").model_copy(
            update={"benchmark_enabled": True}
        ),
        strategy_spec=spec,
        panel_rows=panel,
    )
    fast = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="fast-incomplete-speedup").model_copy(
            update={"engine_lane": EngineLane.FAST_VECTORIZED, "benchmark_enabled": True}
        ),
        strategy_spec=spec,
        panel_table=pa.Table.from_pylist(panel),
        signal_frame=signal_frame,
    )

    with pytest.raises(ValueError, match="reference_data_load_seconds"):
        audit_fast_lane_parity(
            reference_manifest=reference.manifest,
            fast_manifest=fast.manifest,
            claim_speedup=True,
        )


def test_fast_lane_parity_allows_speedup_claim_with_complete_benchmark_evidence(tmp_path) -> None:
    panel = _panel_rows()
    spec = _short_spec()
    signal_frame = compile_signal_frame(spec, panel)
    reference = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="reference-complete-speedup").model_copy(
            update={
                "benchmark_enabled": True,
                "benchmark_observations": {"data_load_seconds": 0.01},
            }
        ),
        strategy_spec=spec,
        panel_rows=panel,
    )
    fast = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="fast-complete-speedup").model_copy(
            update={
                "engine_lane": EngineLane.FAST_VECTORIZED,
                "benchmark_enabled": True,
                "benchmark_observations": {"data_load_seconds": 0.005},
            }
        ),
        strategy_spec=spec,
        panel_table=pa.Table.from_pylist(panel),
        signal_frame=signal_frame,
    )

    report = audit_fast_lane_parity(
        reference_manifest=reference.manifest,
        fast_manifest=fast.manifest,
        claim_speedup=True,
    )

    assert report.status == FastLaneParityStatus.PASS
    assert report.speedup_claimed is True
    for key in (
        "reference_runtime_seconds",
        "fast_runtime_seconds",
        "reference_data_load_seconds",
        "fast_data_load_seconds",
        "reference_artifact_write_seconds",
        "fast_artifact_write_seconds",
        "reference_memory_peak_bytes",
        "fast_memory_peak_bytes",
        "speedup_ratio",
    ):
        assert key in report.benchmark_observations


def test_suspicious_fast_result_gets_full_reference_rerun_plan(tmp_path) -> None:
    panel = _panel_rows()
    spec = _short_spec()
    signal_frame = compile_signal_frame(spec, panel)
    reference = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="reference-fail-audit"),
        strategy_spec=spec,
        panel_rows=panel,
    )
    fast = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="fast-fail-audit").model_copy(
            update={"engine_lane": EngineLane.FAST_VECTORIZED}
        ),
        strategy_spec=spec,
        panel_table=pa.Table.from_pylist(panel),
        signal_frame=signal_frame,
    )
    assert fast.metrics is not None
    changed_fast = fast.manifest.model_copy(
        update={
            "metrics": fast.metrics.model_copy(
                update={"net_return": fast.metrics.net_return + 1.0}
            )
        }
    )

    report = audit_fast_lane_parity(
        reference_manifest=reference.manifest,
        fast_manifest=changed_fast,
    )

    assert report.status == FastLaneParityStatus.FAIL
    assert report.suspicious_result is True
    assert report.rerun_plan is not None
    assert report.rerun_plan.source_run_id == fast.manifest.run_id
    assert report.rerun_plan.requested_engine_lane == EngineLane.VECTORIZED
    assert report.rerun_plan.requested_artifact_mode == ArtifactMode.FULL
    assert report.rerun_plan.same_spec_data_config_required is True
    assert report.rerun_plan.config_overrides["speedup_claimed"] is False


def test_reference_rerun_plan_uses_replay_manifest_ref(tmp_path) -> None:
    panel = _panel_rows()
    spec = _short_spec()
    fast = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="fast-rerun-plan").model_copy(
            update={"engine_lane": EngineLane.FAST_VECTORIZED}
        ),
        strategy_spec=spec,
        panel_table=pa.Table.from_pylist(panel),
        signal_frame=compile_signal_frame(spec, panel),
    )
    run_manifest_path = Path(fast.run_dir) / "run_manifest.json"
    manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))

    plan = build_reference_rerun_plan(manifest, run_manifest_ref=run_manifest_path)

    assert plan.source_run_id == fast.manifest.run_id
    assert plan.required_replay_manifest_ref.endswith("replay_manifest.json")
    assert plan.expected_data_manifest_hash == fast.manifest.data_manifest_hash
    assert plan.expected_strategy_spec_hash == fast.manifest.strategy_spec_hash
    assert plan.expected_params_hash == fast.manifest.params_hash
    assert plan.research_only is True
    assert plan.promotion_ready is False


def test_full_artifact_replay_plan_accepts_metrics_only_reference_run(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="metrics-light-plan").model_copy(
            update={"artifact_mode": ArtifactMode.METRICS_ONLY}
        ),
        strategy_spec=_short_spec(),
        panel_rows=_panel_rows(),
    )
    run_manifest_path = Path(result.run_dir) / "run_manifest.json"
    manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))

    plan = build_full_artifact_replay_plan(manifest, run_manifest_ref=run_manifest_path)

    assert plan.source_run_id == result.manifest.run_id
    assert plan.source_artifact_mode == ArtifactMode.METRICS_ONLY
    assert plan.requested_artifact_mode == ArtifactMode.FULL
    assert plan.requested_engine_lane == EngineLane.VECTORIZED
    assert plan.required_replay_manifest_ref.endswith("replay_manifest.json")
    assert plan.expected_data_manifest_hash == result.manifest.data_manifest_hash
    assert plan.expected_strategy_spec_hash == result.manifest.strategy_spec_hash
    assert plan.expected_params_hash == result.manifest.params_hash
    assert plan.expected_replay_identity_hash == result.manifest.replay_identity_hash
    assert plan.config_overrides["artifact_mode"] == "full"
    assert plan.config_overrides["engine_lane"] == "vectorized"
    assert plan.research_only is True
    assert plan.promotion_ready is False


def test_full_artifact_replay_plan_cli_rejects_already_full_run(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="already-full-plan"),
        strategy_spec=_short_spec(),
        panel_rows=_panel_rows(),
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "fast-lane",
            "full-artifact-replay-plan",
            "--run",
            str(Path(result.run_dir) / "run_manifest.json"),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert rejected.returncode == 1
    assert "already has full artifact mode" in rejected.stdout


def test_full_artifact_replay_plan_cli_emits_plan_for_metrics_only_run(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="metrics-light-cli").model_copy(
            update={"artifact_mode": ArtifactMode.METRICS_ONLY}
        ),
        strategy_spec=_short_spec(),
        panel_rows=_panel_rows(),
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "fast-lane",
            "full-artifact-replay-plan",
            "--run",
            str(Path(result.run_dir) / "run_manifest.json"),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    plan = json.loads(completed.stdout)
    assert plan["source_run_id"] == result.manifest.run_id
    assert plan["requested_artifact_mode"] == "full"
    assert plan["requested_engine_lane"] == "vectorized"
    assert plan["expected_replay_identity_hash"] == result.manifest.replay_identity_hash
    assert plan["research_only"] is True
    assert plan["promotion_ready"] is False


def test_full_artifact_replay_verification_accepts_matching_full_replay(tmp_path) -> None:
    panel = _panel_rows()
    spec = _short_spec()
    source = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="metrics-source").model_copy(
            update={"artifact_mode": ArtifactMode.METRICS_ONLY}
        ),
        strategy_spec=spec,
        panel_rows=panel,
    )
    full = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="metrics-source-full"),
        strategy_spec=spec,
        panel_rows=panel,
    )

    report = verify_full_artifact_replay(
        source_manifest=source.manifest,
        replay_manifest=full.manifest,
        source_replay_manifest=_replay_payload(source.run_dir),
        full_replay_manifest=_replay_payload(full.run_dir),
    )

    assert report.status == FullArtifactReplayVerificationStatus.PASS
    assert report.same_spec_data_config_verified is True
    assert report.replay_manifest_identity_verified is True
    assert report.metrics_verified is True
    assert report.full_artifacts_verified is True
    assert report.identity_mismatches == ()
    assert report.replay_manifest_mismatches == ()
    assert report.blocker_reasons == ()
    assert all(row.within_tolerance for row in report.metric_diffs)
    assert report.research_only is True
    assert report.promotion_ready is False


def test_full_artifact_replay_verification_fails_on_metric_mismatch(tmp_path) -> None:
    panel = _panel_rows()
    spec = _short_spec()
    source = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="metrics-source-mismatch").model_copy(
            update={"artifact_mode": ArtifactMode.METRICS_ONLY}
        ),
        strategy_spec=spec,
        panel_rows=panel,
    )
    full = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="metrics-source-mismatch-full"),
        strategy_spec=spec,
        panel_rows=panel,
    )
    assert full.metrics is not None
    changed_full_manifest = full.manifest.model_copy(
        update={
            "metrics": full.metrics.model_copy(
                update={"net_return": full.metrics.net_return + 0.01}
            )
        }
    )

    report = verify_full_artifact_replay(
        source_manifest=source.manifest,
        replay_manifest=changed_full_manifest,
        source_replay_manifest=_replay_payload(source.run_dir),
        full_replay_manifest=_replay_payload(full.run_dir),
    )

    assert report.status == FullArtifactReplayVerificationStatus.FAIL
    assert "metrics_mismatch" in report.blocker_reasons
    assert report.metrics_verified is False


def test_full_artifact_replay_verification_cli_accepts_matching_replay(tmp_path) -> None:
    panel = _panel_rows()
    spec = _short_spec()
    source = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="metrics-source-cli").model_copy(
            update={"artifact_mode": ArtifactMode.METRICS_ONLY}
        ),
        strategy_spec=spec,
        panel_rows=panel,
    )
    full = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="metrics-source-cli-full"),
        strategy_spec=spec,
        panel_rows=panel,
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "fast-lane",
            "verify-full-artifact-replay",
            "--source-run",
            str(Path(source.run_dir) / "run_manifest.json"),
            "--full-run",
            str(Path(full.run_dir) / "run_manifest.json"),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr + completed.stdout
    report = json.loads(completed.stdout)
    assert report["status"] == "pass"
    assert report["source_run_id"] == source.manifest.run_id
    assert report["replay_run_id"] == full.manifest.run_id
    assert report["same_spec_data_config_verified"] is True
    assert report["replay_manifest_identity_verified"] is True
    assert report["metrics_verified"] is True
    assert report["full_artifacts_verified"] is True
    assert report["promotion_ready"] is False


def test_reference_audit_sample_is_deterministic_and_bounded() -> None:
    run_ids = ("run-c", "run-a", "run-b", "run-a")

    first = select_reference_audit_sample(run_ids, sample_rate=0.2, seed="unit")
    second = select_reference_audit_sample(tuple(reversed(run_ids)), sample_rate=0.2, seed="unit")
    none = select_reference_audit_sample(run_ids, sample_rate=0.0, seed="unit")
    all_ids = select_reference_audit_sample(run_ids, sample_rate=1.0, seed="unit")

    assert first == second
    assert len(first) >= 1
    assert none == ()
    assert all_ids == ("run-a", "run-b", "run-c")


def _config(output_root: Path, *, run_id: str) -> BacktestRunConfig:
    return BacktestRunConfig(
        run_id=run_id,
        experiment_id="phase80-fast-lane-audit",
        trial_index=0,
        output_root=str(output_root),
        archive_snapshot_id="archive-snapshot",
        universe_snapshot_id="universe-snapshot",
        data_manifest_id="data-manifest",
        data_manifest_hash=HEX_A,
        validation_manifest_hash=HEX_B,
        cost_manifest_hash=HEX_C,
        universe_mode="as_of",
        venue_scope="hyperliquid",
        git_sha="test-git-sha",
    )


def _replay_payload(run_dir: str) -> dict[str, object]:
    return json.loads((Path(run_dir) / "replay_manifest.json").read_text(encoding="utf-8"))


def _short_spec():
    payload = example_strategy_payloads()["hl_cross_sectional_momentum_v1"]
    payload = json.loads(json.dumps(payload))
    payload["logic"]["lookback_hours"] = 2
    payload["logic"]["lookback_bars"] = 2
    payload["inputs"]["fields"] = sorted(
        {
            *payload["inputs"]["fields"],
            "open",
            "high",
            "low",
            "close",
            "volume",
            "funding",
            "funding_rate",
            "open_interest",
            "mark_price",
            "oracle_price",
            "spread",
            "coverage_ratio",
        }
    )
    return payload


def _panel_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    instruments = {
        "hyperliquid:perp:BTC": 100.0,
        "hyperliquid:perp:ETH": 80.0,
        "hyperliquid:perp:SOL": 40.0,
    }
    for hour in range(12):
        ts = f"2024-01-01T{hour:02d}:00:00Z"
        for offset, (instrument_id, base) in enumerate(instruments.items()):
            drift = (hour * (offset + 1)) * (1 if offset != 1 else -0.5)
            open_price = base + drift
            close = open_price * (1.01 if offset == 0 else 0.995 if offset == 1 else 1.002)
            rows.append(
                {
                    "ts": ts,
                    "instrument_id": instrument_id,
                    "open": open_price,
                    "high": max(open_price, close) * 1.01,
                    "low": min(open_price, close) * 0.99,
                    "close": close,
                    "volume": 100_000.0 + (hour * 1000) + offset,
                    "funding": 0.0002 if offset == 0 else -0.0001 if offset == 1 else 0.0,
                    "funding_rate": 0.0002 if offset == 0 else -0.0001 if offset == 1 else 0.0,
                    "open_interest": 2_000_000.0 + offset,
                    "mark_price": close,
                    "oracle_price": close,
                    "spread": 0.001,
                    "coverage_ratio": 1.0,
                }
            )
    return rows
