from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tradingbotsuite.research_discovery.exit_lab import DISCOVERY_EXIT_LAB_MANIFEST_VERSION
from tradingbotsuite.research_discovery.frozen_entry_exit_lab import write_frozen_entry_exit_lab_artifacts


START_MS = 1_712_649_600_000


def _write_discovery_fixture(
    tmp_path: Path,
    *,
    label_horizon: str = "1h",
    decision_time: object = START_MS,
    signal_side: str = "long",
    signal_bar_close: object = 100.0,
    market_prices: dict[str, list[float]] | None = None,
) -> tuple[Path, Path, Path]:
    run_dir = tmp_path / "discovery"
    ledger_dir = run_dir / "candidate_ledgers"
    ledger_dir.mkdir(parents=True)
    interesting_path = ledger_dir / "interesting_candidates.parquet"
    market_path = run_dir / "market.parquet"
    signals_path = run_dir / "entry_signals.parquet"
    prices = market_prices or {
        "open": [100.0, 102.0, 104.0, 102.0, 100.5, 100.5, 100.5, 100.5],
        "high": [101.0, 103.0, 105.0, 103.0, 101.0, 101.0, 101.0, 101.0],
        "low": [99.0, 101.0, 103.0, 101.0, 100.0, 100.0, 100.0, 100.0],
        "close": [100.0, 102.0, 104.0, 102.0, 100.5, 100.5, 100.5, 100.5],
    }

    pd.DataFrame(
        [
            {
                "run_id": "exact_entry_sweep_btcusdt_candidate_depth_v1",
                "trial_id": "trial-0001",
                "candidate_id": "lead-1",
                "candidate_family": "hmm_knn",
                "score": 1.0,
                "discovery_screen_score_v2": 1.0,
                "final_score": 1.0,
                "feature_column_set_id": "core",
                "regime_mode": "gmm",
                "regime_detector_type": "gmm",
                "label_horizon": label_horizon,
                "distance_metric": "euclidean",
                "k": 3,
                "min_neighbor_count": 3,
                "independent_event_count": 20,
                "event_signal_rate": 0.02,
                "record_sha256": "record-sha",
                "realized_expectancy": 0.03,
            }
        ]
    ).to_parquet(interesting_path, index=False)
    pd.DataFrame(
        {
            "bar_time_ms": [START_MS + index * 900_000 for index in range(8)],
            "open": prices["open"],
            "high": prices["high"],
            "low": prices["low"],
            "close": prices["close"],
        }
    ).to_parquet(market_path, index=False)
    pd.DataFrame(
        [
            {
                "candidate_id": "lead-1",
                "decision_time_ms": decision_time,
                "side": signal_side,
                "symbol": "BTCUSDT",
                "signal_bar_close": signal_bar_close,
            }
        ]
    ).to_parquet(signals_path, index=False)
    manifest_path = run_dir / "discovery_run_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": "exact_entry_sweep_btcusdt_candidate_depth_v1",
                "symbol": "BTCUSDT",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "required_outputs": {"interesting_candidates": str(interesting_path)},
                "data_evidence": {"dataset_path": str(market_path), "row_count": 8},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return manifest_path, signals_path, market_path


def test_frozen_entry_exit_lab_writes_bridge_compatible_exit_lab_artifact(tmp_path: Path) -> None:
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path)

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    matrix = pd.read_parquet(result.matrix_path)
    assert manifest["exit_lab_manifest_version"] == DISCOVERY_EXIT_LAB_MANIFEST_VERSION
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["required_outputs"]["discovery_exit_lab_candidate_gates"] == str(result.candidate_gates_path)
    assert manifest["discovery_exit_lab_candidate_gates_sha256"]
    assert {"fixed_holding_window", "simple_runner_v1"} <= set(matrix["exit_policy_id"])
    assert gates.loc[0, "entry_candidate_id"] == "lead-1"
    assert gates.loc[0, "exit_lab_status"] == "complete"
    assert gates.loc[0, "exit_lab_gate_status"] == "passed"
    assert gates.loc[0, "exit_lab_best_family"] == "trailing_risk"


def test_frozen_entry_exit_lab_blocks_without_entry_signals_but_preserves_gate_schema(tmp_path: Path) -> None:
    manifest_path, _, _ = _write_discovery_fixture(tmp_path)

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "blocked_exit_lab",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    assert manifest["blocked_reason"] == "frozen_entry_signals_missing"
    assert manifest["exit_lab_manifest_version"] == DISCOVERY_EXIT_LAB_MANIFEST_VERSION
    assert gates.loc[0, "entry_candidate_id"] == "lead-1"
    assert gates.loc[0, "exit_lab_gate_status"] == "blocked"
    assert gates.loc[0, "exit_lab_reasons"] == "frozen_entry_signals_missing"
    assert bool(gates.loc[0, "research_only"]) is True
    assert bool(gates.loc[0, "observe_only"]) is True
    assert bool(gates.loc[0, "promotion_ready"]) is False


def test_frozen_entry_exit_lab_clamps_subhour_label_horizon_to_supported_window(tmp_path: Path) -> None:
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path, label_horizon="15m")

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "subhour_exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    matrix = pd.read_parquet(result.matrix_path)
    assert "blocked_reason" not in manifest
    assert manifest["decision_counts"] == {"passed": 1}
    assert {"fixed_holding_window", "simple_runner_v1"} <= set(matrix["exit_policy_id"])
    assert gates.loc[0, "exit_lab_status"] == "complete"
    assert gates.loc[0, "exit_lab_gate_status"] == "passed"


def test_frozen_entry_exit_lab_blocks_overlong_label_horizon_without_crashing(tmp_path: Path) -> None:
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path, label_horizon="30d")

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "overlong_exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    matrix = pd.read_parquet(result.matrix_path)
    assert manifest["decision_counts"] == {"blocked": 1}
    assert matrix.empty
    assert gates.loc[0, "exit_lab_gate_status"] == "blocked"
    assert gates.loc[0, "exit_lab_reasons"] == "frozen_entry_label_horizon_unsupported"


def test_frozen_entry_exit_lab_blocks_invalid_signal_side_without_crashing(tmp_path: Path) -> None:
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path, signal_side="flat")

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "invalid_side_exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    matrix = pd.read_parquet(result.matrix_path)
    assert manifest["decision_counts"] == {"blocked": 1}
    assert matrix.empty
    assert gates.loc[0, "exit_lab_gate_status"] == "blocked"
    assert gates.loc[0, "exit_lab_reasons"] == "frozen_entry_valid_signals_missing_for_lead"


def test_frozen_entry_exit_lab_blocks_bad_signal_timestamp_without_crashing(tmp_path: Path) -> None:
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path, decision_time="bad-time")

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "bad_time_exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    matrix = pd.read_parquet(result.matrix_path)
    assert manifest["decision_counts"] == {"blocked": 1}
    assert matrix.empty
    assert gates.loc[0, "exit_lab_gate_status"] == "blocked"
    assert gates.loc[0, "exit_lab_reasons"] == "frozen_entry_valid_signals_missing_for_lead"


def test_frozen_entry_exit_lab_blocks_bad_signal_bar_close_without_crashing(tmp_path: Path) -> None:
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path, signal_bar_close="bad-price")

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "bad_signal_price_exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    matrix = pd.read_parquet(result.matrix_path)
    assert manifest["decision_counts"] == {"blocked": 1}
    assert matrix.empty
    assert gates.loc[0, "exit_lab_gate_status"] == "blocked"
    assert gates.loc[0, "exit_lab_reasons"] == "frozen_entry_valid_signals_missing_for_lead"


def test_frozen_entry_exit_lab_blocks_non_positive_market_prices_before_simulation(tmp_path: Path) -> None:
    bad_prices = {
        "open": [-100.0] * 8,
        "high": [-99.0] * 8,
        "low": [-101.0] * 8,
        "close": [-100.0] * 8,
    }
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path, market_prices=bad_prices)

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "bad_market_exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    assert manifest["blocked_reason"] == "market_data_empty"
    assert manifest["decision_counts"] == {"blocked": 1}
    assert gates.loc[0, "exit_lab_gate_status"] == "blocked"
    assert gates.loc[0, "exit_lab_reasons"] == "market_data_empty"


def test_frozen_entry_exit_lab_blocks_malformed_signal_parquet_without_crashing(tmp_path: Path) -> None:
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path)
    signals_path.write_text("not parquet", encoding="utf-8")

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "malformed_signals_exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    assert manifest["blocked_reason"] == "frozen_entry_signals_malformed"
    assert manifest["decision_counts"] == {"blocked": 1}
    assert gates.loc[0, "exit_lab_gate_status"] == "blocked"
    assert gates.loc[0, "exit_lab_reasons"] == "frozen_entry_signals_malformed"


def test_frozen_entry_exit_lab_blocks_malformed_market_parquet_without_crashing(tmp_path: Path) -> None:
    manifest_path, signals_path, market_path = _write_discovery_fixture(tmp_path)
    market_path.write_text("not parquet", encoding="utf-8")

    result = write_frozen_entry_exit_lab_artifacts(
        discovery_manifest_path=manifest_path,
        output_dir=tmp_path / "malformed_market_exit_lab",
        entry_signals_path=signals_path,
        market_data_path=market_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gates = pd.read_parquet(result.candidate_gates_path)
    assert manifest["blocked_reason"] == "market_data_malformed"
    assert manifest["decision_counts"] == {"blocked": 1}
    assert gates.loc[0, "exit_lab_gate_status"] == "blocked"
    assert gates.loc[0, "exit_lab_reasons"] == "market_data_malformed"
