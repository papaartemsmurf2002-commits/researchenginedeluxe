from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from tradingbotsuite.research_sandbox import (
    DataWindow,
    ExitVariant,
    SandboxRunSpec,
    StrategyCatalogRow,
    VenueArchiveDescriptor,
    compile_strategy_config_payload,
    deterministic_trial_id,
    materialize_strategy_signals,
    preflight_sandbox_compatibility,
    require_sandbox_artifact_integrity,
    run_sandbox_sweep,
    run_fixed_hold_sweep_for_venue_frames,
    verify_sandbox_artifact_integrity,
)


def _spec(run_id: str = "post-audit-safety") -> SandboxRunSpec:
    return SandboxRunSpec(
        run_id=run_id,
        data_window=DataWindow("2024-01-01", "2024-01-10"),
        holding_periods=(1,),
        round_trip_cost_bps=1.0,
        min_trades=1,
        max_evidence_requests=2,
    )


def _strategy(**overrides: object) -> StrategyCatalogRow:
    payload = {
        "hypothesis_id": "windowed-signal",
        "family": "post_audit_safety",
        "source_id": "unit_test_catalog",
        "signal_column": "outside_signal",
        "side": "long",
        "params": {"lookback": 1},
    }
    payload.update(overrides)
    return StrategyCatalogRow(**payload)


def _venue(**overrides: object) -> VenueArchiveDescriptor:
    payload = {
        "descriptor_id": "okx-btcusdt-windowed",
        "venue": "okx",
        "symbol": "BTCUSDT",
        "data_family": "kline",
        "interval": "1d",
        "window": DataWindow("2024-01-05", "2024-01-10"),
        "diagnostic_only": True,
    }
    payload.update(overrides)
    return VenueArchiveDescriptor(**payload)


def _windowed_market_frame() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=10, freq="1D", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0 + index for index in range(10)],
            "high": [101.0 + index for index in range(10)],
            "low": [99.0 + index for index in range(10)],
            "close": [100.0 + index for index in range(10)],
            "outside_signal": [1.0 if index == 1 else 0.0 for index in range(10)],
        }
    )


@pytest.mark.parametrize(
    "run_id",
    [
        "../escape",
        "..\\escape",
        "nested/path",
        "nested\\path",
        "C:\\escape",
        "bad..segment",
        "bad ",
        "CON",
    ],
)
def test_sandbox_run_id_rejects_unsafe_path_components(run_id: str) -> None:
    with pytest.raises(ValueError):
        _spec(run_id)


def test_sandbox_package_root_uses_lazy_exports() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    script = """
import json
import sys

import tradingbotsuite.research_sandbox as sandbox

payload = {
    "catalog_after_root": "tradingbotsuite.research_sandbox.catalog" in sys.modules,
    "spec_after_root": "tradingbotsuite.research_sandbox.spec" in sys.modules,
}
_ = sandbox.DataWindow
payload["spec_after_data_window"] = "tradingbotsuite.research_sandbox.spec" in sys.modules
payload["catalog_after_data_window"] = "tradingbotsuite.research_sandbox.catalog" in sys.modules
_ = sandbox.index_sandbox_artifacts
payload["catalog_after_catalog_export"] = "tradingbotsuite.research_sandbox.catalog" in sys.modules
payload["has_run_spec_export"] = "SandboxRunSpec" in sandbox.__all__
print(json.dumps(payload, sort_keys=True))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload == {
        "catalog_after_root": False,
        "spec_after_root": False,
        "spec_after_data_window": True,
        "catalog_after_data_window": False,
        "catalog_after_catalog_export": True,
        "has_run_spec_export": True,
    }


def test_nested_forbidden_boundary_fields_fail_before_artifact_write(tmp_path: Path) -> None:
    spec = _spec("nested-boundary-rejection")
    strategy = _strategy(params={"nested": {"order_placement_instruction": True}})
    with pytest.raises(ValueError, match="forbidden|order_placement_instruction"):
        run_sandbox_sweep(
            spec=spec,
            market_frame=_windowed_market_frame(),
            strategies=[strategy],
            venues=[_venue()],
            output_root=tmp_path / "runs",
        )

    assert not (tmp_path / "runs" / spec.run_id).exists()


def test_descriptor_window_intersection_is_enforced_during_execution() -> None:
    result = run_fixed_hold_sweep_for_venue_frames(
        market_frames={"okx-btcusdt-windowed": _windowed_market_frame()},
        run_spec=_spec("descriptor-window-execution"),
        strategies=[_strategy()],
        venues=[_venue()],
    )[0]

    assert result.trade_count == 0
    assert result.status == "blocked"
    assert "no_complete_fixed_hold_trades" in result.rejection_reasons
    assert result.metadata["market_source"]["effective_window"] == {
        "start": "2024-01-05",
        "end": "2024-01-10",
    }


def test_descriptor_window_intersection_is_enforced_during_preflight(tmp_path: Path) -> None:
    market_path = tmp_path / "market.csv"
    _windowed_market_frame().to_csv(market_path, index=False)

    payload = preflight_sandbox_compatibility(
        spec=_spec("descriptor-window-preflight"),
        strategies=[_strategy()],
        venues=[_venue()],
        output_dir=tmp_path / "preflight",
        shared_market_data_path=market_path,
    )
    row = payload["rows"][0]

    assert row["market_row_count"] == 6
    assert row["active_signal_count"] == 0
    assert row["effective_window"] == {"start": "2024-01-05", "end": "2024-01-10"}


def test_catalog_exit_profile_without_matching_run_spec_blocks_execution() -> None:
    result = run_fixed_hold_sweep_for_venue_frames(
        market_frames={"okx-btcusdt-windowed": _windowed_market_frame()},
        run_spec=_spec("exit-profile-blocks-execution"),
        strategies=[_strategy(exit_profile="target_only")],
        venues=[_venue(window=DataWindow("2024-01-01", "2024-01-10"))],
    )[0]

    assert result.status == "blocked"
    assert result.exit_profile == "fixed_hold"
    assert "strategy_exit_profile_not_in_run_spec:target_only" in result.rejection_reasons


def test_catalog_exit_profile_runs_only_matching_run_spec_exit_variant() -> None:
    spec = SandboxRunSpec(
        run_id="exit-profile-matching-variant",
        data_window=DataWindow("2024-01-01", "2024-01-10"),
        holding_periods=(1,),
        min_trades=1,
        exit_variants=(
            ExitVariant("fixed", "fixed_hold"),
            ExitVariant("target", "target_only", target_return=0.01),
        ),
    )

    results = run_fixed_hold_sweep_for_venue_frames(
        market_frames={"okx-btcusdt-windowed": _windowed_market_frame()},
        run_spec=spec,
        strategies=[_strategy(exit_profile="target_only")],
        venues=[_venue(window=DataWindow("2024-01-01", "2024-01-10"))],
    )

    assert [result.exit_variant_id for result in results] == ["target"]
    assert results[0].exit_profile == "target_only"
    assert results[0].trade_count == 1


def test_catalog_exit_profile_without_matching_run_spec_blocks_preflight(tmp_path: Path) -> None:
    market_path = tmp_path / "market.csv"
    _windowed_market_frame().to_csv(market_path, index=False)

    payload = preflight_sandbox_compatibility(
        spec=_spec("exit-profile-preflight"),
        strategies=[_strategy(exit_profile="target_only")],
        venues=[_venue(window=DataWindow("2024-01-01", "2024-01-10"))],
        output_dir=tmp_path / "preflight",
        shared_market_data_path=market_path,
    )
    row = payload["rows"][0]

    assert row["status"] == "blocked"
    assert row["strategy_exit_profile"] == "target_only"
    assert row["runnable_trial_estimate"] == 0
    assert row["blocked_trial_estimate"] == 1
    assert "strategy_exit_profile_not_in_run_spec:target_only" in row["blocker_reasons"]


def test_artifact_integrity_rejects_child_paths_outside_manifest_dir(tmp_path: Path) -> None:
    run = run_sandbox_sweep(
        spec=_spec("artifact-child-containment"),
        market_frame=_windowed_market_frame(),
        strategies=[_strategy(signal_column="outside_signal")],
        venues=[_venue(window=DataWindow("2024-01-01", "2024-01-10"))],
        output_root=tmp_path / "runs",
    )
    outside = tmp_path / "outside.parquet"
    outside.write_text("not parquet", encoding="utf-8")
    manifest = json.loads(run.artifacts.manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["summary_parquet_path"] = str(outside)
    run.artifacts.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    report = verify_sandbox_artifact_integrity(run.artifacts.manifest_path, write_report=False)
    summary_row = next(row for row in report["rows"] if row["artifact_key"] == "summary_parquet")

    assert report["verification_status"] == "failed"
    assert "artifact_path_outside_manifest_dir:summary_parquet" in summary_row["reasons"]
    with pytest.raises(ValueError, match="artifact_path_outside_manifest_dir"):
        require_sandbox_artifact_integrity(run.artifacts.manifest_path)


def test_trial_identity_includes_min_trades_but_not_local_data_paths(tmp_path: Path) -> None:
    strategy = _strategy()
    first_spec = _spec("identity-a")
    second_spec = SandboxRunSpec(
        run_id="identity-b",
        data_window=first_spec.data_window,
        holding_periods=first_spec.holding_periods,
        round_trip_cost_bps=first_spec.round_trip_cost_bps,
        min_trades=first_spec.min_trades + 1,
    )
    first_venue = _venue(
        data_path=tmp_path / "root-a" / "market.csv",
        source_integrity={"sha256": "abc123", "byte_size": 10, "source_path": str(tmp_path / "root-a")},
    )
    moved_venue = _venue(
        data_path=tmp_path / "root-b" / "market.csv",
        source_integrity={"sha256": "abc123", "byte_size": 10, "source_path": str(tmp_path / "root-b")},
    )

    first_id = deterministic_trial_id(run_spec=first_spec, strategy=strategy, venue=first_venue, holding_period=1)
    moved_path_id = deterministic_trial_id(run_spec=first_spec, strategy=strategy, venue=moved_venue, holding_period=1)
    changed_min_trades_id = deterministic_trial_id(
        run_spec=second_spec,
        strategy=strategy,
        venue=first_venue,
        holding_period=1,
    )

    assert first_id == moved_path_id
    assert first_id != changed_min_trades_id


def test_baseline_no_trade_config_compiles_to_non_active_proxy() -> None:
    rows = compile_strategy_config_payload(
        {"strategy_id": "baseline_no_trade", "strategy_version": "v1", "parameters": {}},
        source_path="configs/strategies/no_trade.json",
    )
    market = materialize_strategy_signals(_windowed_market_frame(), rows)

    assert rows
    assert {row.params["sandbox_blueprint_id"] for row in rows} == {"no_trade_proxy"}
    assert all(row.params["sandbox_proxy_only"] is True for row in rows)
    assert all(row.params["strict_cycle_strategy_execution"] is False for row in rows)
    for row in rows:
        assert float(market[row.signal_column].sum()) == 0.0
