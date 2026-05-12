from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tradingbotsuite.backtesting.splits import build_purged_walk_forward_splits
from tradingbotsuite.research_discovery.hmm_materialization import (
    HMM_POSTERIOR_COLUMNS,
    HmmMaterializationSpec,
    _assign_posterior_rows,
    _empty_result,
    _recent_flip_flags,
    _source_row_index,
    materialize_no_regime_baseline,
    materialize_split_safe_hmm_regimes,
    write_hmm_materialization_artifacts,
)


FEATURE_COLUMNS = (
    "log_return_1",
    "log_return_4",
    "trend_slope_20",
    "efficiency_ratio",
    "directional_slope_atr",
    "realized_volatility",
    "atr_percentile",
)


def _feature_frame(row_count: int = 120) -> pd.DataFrame:
    rows = []
    start_ms = 1712649600000
    for index in range(row_count):
        regime = index // 30
        slope = 0.2 if regime % 4 == 1 else (-0.2 if regime % 4 == 2 else 0.0)
        vol = 0.04 if regime % 4 == 3 else 0.01
        rows.append(
            {
                "bar_time_ms": start_ms + index * 900_000,
                "source_row_index": index,
                "log_return_1": np.sin(index / 5.0) * 0.001,
                "log_return_4": np.sin(index / 7.0) * 0.002,
                "trend_slope_20": slope + np.sin(index / 11.0) * 0.01,
                "efficiency_ratio": 0.3 + 0.1 * (regime % 3),
                "directional_slope_atr": slope,
                "realized_volatility": vol,
                "atr_percentile": min(0.95, 0.2 + vol * 10.0),
                "choppiness": 35.0 + 10.0 * (regime % 2),
            }
        )
    return pd.DataFrame(rows)


def _spec(**overrides: object) -> HmmMaterializationSpec:
    payload = {
        "feature_columns": list(FEATURE_COLUMNS),
        "n_states": 4,
        "posterior_threshold": 0.55,
        "entropy_threshold": 0.95,
        "flip_cooldown_bars": 1,
        "min_training_rows": 24,
        "random_state": 73,
        "max_iter": 50,
        "covariance_type": "diag",
        "hmm_feature_pack_id": "test_hmm_pack",
    }
    payload.update(overrides)
    return HmmMaterializationSpec.from_payload(payload)


def _splits(frame: pd.DataFrame):
    return build_purged_walk_forward_splits(
        frame,
        min_splits=3,
        purge_embargo_bars=2,
        time_column="bar_time_ms",
    )


def test_hmm_materialization_emits_required_columns_and_split_safe_rows() -> None:
    frame = _feature_frame()
    result = materialize_split_safe_hmm_regimes(frame, splits=_splits(frame), spec=_spec())
    materialized = result.frame[result.frame["hmm_fit_end_row"] >= 0]

    assert set(HMM_POSTERIOR_COLUMNS) <= set(result.frame.columns)
    assert not materialized.empty
    assert (materialized["hmm_fit_end_row"] < materialized["source_row_index"]).all()
    assert materialized["hmm_model_id"].astype(str).str.startswith("gaussian_mixture:").all()
    assert materialized["hmm_feature_pack_id"].eq("test_hmm_pack").all()
    assert result.manifest["split_safety_passed"] is True
    assert result.manifest["research_only"] is True
    assert result.manifest["observe_only"] is True
    assert result.manifest["promotion_ready"] is False
    assert result.manifest["regime_detector_type"] == "gmm"
    assert result.manifest["regime_model_backend"] == "sklearn.mixture.GaussianMixture"
    assert result.manifest["true_hmm_backend_used"] is False
    assert result.manifest["order_placement_used"] is False
    assert result.manifest["runtime_mode_changed"] is False


def test_hmm_posteriors_are_finite_and_sum_to_one() -> None:
    frame = _feature_frame()
    result = materialize_split_safe_hmm_regimes(frame, splits=_splits(frame), spec=_spec())
    materialized = result.frame[result.frame["hmm_fit_end_row"] >= 0]
    posterior_columns = [f"regime_p_{state}" for state in range(4)]

    assert np.isfinite(materialized[posterior_columns].to_numpy(dtype=float)).all()
    np.testing.assert_allclose(materialized[posterior_columns].sum(axis=1).to_numpy(dtype=float), 1.0)
    assert np.isfinite(materialized["posterior_entropy"].to_numpy(dtype=float)).all()
    assert materialized["max_regime_probability"].between(0.0, 1.0).all()


def test_hmm_vectorized_assignment_matches_scalar_reference() -> None:
    frame = _feature_frame(row_count=12)
    source_index = _source_row_index(frame)
    spec = _spec(n_states=3, entropy_threshold=0.90, flip_cooldown_bars=1)
    positions = [1, 3, 4, 7]
    posterior = np.array(
        [
            [0.70, 0.20, 0.10],
            [0.20, 0.65, 0.15],
            [0.18, 0.62, 0.20],
            [0.10, 0.20, 0.70],
        ],
        dtype=float,
    )
    state_labels = {0: "range_chop", 1: "bull_trend", 2: "bear_trend"}
    vectorized = _empty_result(frame, source_index=source_index, spec=spec)
    scalar = _empty_result(frame, source_index=source_index, spec=spec)

    _assign_posterior_rows(
        vectorized,
        positions=positions,
        source_index=source_index,
        posterior=posterior,
        state_labels=state_labels,
        split_id="split-a",
        fit_end_row=99,
        model_id="model-a",
        spec=spec,
    )
    _assign_posterior_rows_scalar_reference(
        scalar,
        positions=positions,
        source_index=source_index,
        posterior=posterior,
        state_labels=state_labels,
        split_id="split-a",
        fit_end_row=99,
        model_id="model-a",
        spec=spec,
    )

    compare_columns = [f"regime_p_{state}" for state in range(spec.n_states)] + list(HMM_POSTERIOR_COLUMNS)
    pd.testing.assert_frame_equal(vectorized[compare_columns], scalar[compare_columns], check_dtype=False)


def test_hmm_materialization_is_train_only_for_earlier_splits() -> None:
    frame = _feature_frame()
    splits = _splits(frame)
    base = materialize_split_safe_hmm_regimes(frame, splits=splits, spec=_spec()).frame
    changed = frame.copy()
    first_split_end = int(splits[0].validation_end_index)
    changed.loc[first_split_end + 1 :, list(FEATURE_COLUMNS)] *= 1000.0
    rerun = materialize_split_safe_hmm_regimes(changed, splits=splits, spec=_spec()).frame

    first_split_mask = base["hmm_split_id"].eq(splits[0].split_id)
    compare_columns = ["top_regime_label", "max_regime_probability", "posterior_entropy", "regime_no_trade"]
    pd.testing.assert_frame_equal(
        base.loc[first_split_mask, compare_columns].reset_index(drop=True),
        rerun.loc[first_split_mask, compare_columns].reset_index(drop=True),
    )


def test_hmm_materialization_blocks_insufficient_training_without_leaking_rows() -> None:
    frame = _feature_frame(row_count=40)
    result = materialize_split_safe_hmm_regimes(frame, splits=_splits(frame), spec=_spec(min_training_rows=200))

    assert result.frame["hmm_fit_end_row"].eq(-1).all()
    assert result.frame["regime_no_trade"].eq(True).all()
    assert result.manifest["materialized_row_count"] == 0
    assert {record["status"] for record in result.manifest["split_records"]} == {"blocked"}
    assert {record["reason"] for record in result.manifest["split_records"]} == {"insufficient_training_rows"}


def test_hmm_materialization_rejects_missing_columns() -> None:
    frame = _feature_frame().drop(columns=["log_return_4"])

    with pytest.raises(ValueError, match="hmm_materialization_missing_feature_columns:log_return_4"):
        materialize_split_safe_hmm_regimes(frame, splits=_splits(_feature_frame()), spec=_spec())


def test_hmm_materialization_writes_research_only_artifacts(tmp_path: Path) -> None:
    frame = _feature_frame()
    result = materialize_split_safe_hmm_regimes(frame, splits=_splits(frame), spec=_spec())

    artifacts = write_hmm_materialization_artifacts(tmp_path / "hmm", result)
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    posteriors = pd.read_parquet(artifacts.regime_posteriors_path)
    split_summary = pd.read_parquet(artifacts.split_summary_path)

    assert manifest["hmm_materialization_manifest_version"] == "discovery-hmm-materialization-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["required_outputs"]["regime_posteriors"] == str(artifacts.regime_posteriors_path)
    assert not posteriors.empty
    assert not split_summary.empty
    assert manifest["regime_detector_type"] == "gmm"
    assert manifest["true_hmm_backend_used"] is False


def test_hmm_materialization_artifacts_refuse_overwrite(tmp_path: Path) -> None:
    frame = _feature_frame()
    result = materialize_split_safe_hmm_regimes(frame, splits=_splits(frame), spec=_spec())
    output_dir = tmp_path / "hmm"
    write_hmm_materialization_artifacts(output_dir, result)

    with pytest.raises(ValueError, match="refusing to overwrite existing HMM materialization artifacts"):
        write_hmm_materialization_artifacts(output_dir, result)


def test_hmm_materialization_spec_config_loads() -> None:
    spec = HmmMaterializationSpec.from_path(Path("configs/discovery/hmm_materialization_v4.json"))

    assert spec.feature_columns == FEATURE_COLUMNS
    assert spec.hmm_feature_pack_id == "discovery_gmm_price_trend_vol_v4"
    assert spec.regime_detector_type == "gmm"
    assert spec.true_hmm_backend_used is False


def test_no_regime_baseline_emits_split_safe_compatibility_columns() -> None:
    frame = _feature_frame()
    result = materialize_no_regime_baseline(frame, splits=_splits(frame), feature_pack_id="test_no_regime_pack")
    materialized = result.frame[result.frame["hmm_fit_end_row"] >= 0]

    assert set(HMM_POSTERIOR_COLUMNS) <= set(result.frame.columns)
    assert not materialized.empty
    assert materialized["top_regime_label"].eq("all_market").all()
    assert materialized["regime_no_trade"].eq(False).all()
    assert materialized["recent_regime_flip"].eq(False).all()
    assert materialized["max_regime_probability"].eq(1.0).all()
    assert materialized["posterior_entropy"].eq(0.0).all()
    assert materialized["hmm_model_id"].astype(str).str.startswith("no_regime:").all()
    assert materialized["hmm_feature_pack_id"].eq("test_no_regime_pack").all()
    assert (materialized["hmm_fit_end_row"] < materialized["source_row_index"]).all()
    assert result.manifest["regime_detector_type"] == "none"
    assert result.manifest["regime_gate_enabled"] is False
    assert result.manifest["same_regime_neighbor_pool_enabled"] is False
    assert result.manifest["true_hmm_backend_used"] is False
    assert result.manifest["split_safety_passed"] is True


def _assign_posterior_rows_scalar_reference(
    result: pd.DataFrame,
    *,
    positions,
    source_index: pd.Series,
    posterior: np.ndarray,
    state_labels: dict[int, str],
    split_id: str,
    fit_end_row: int,
    model_id: str,
    spec: HmmMaterializationSpec,
) -> None:
    top_state = posterior.argmax(axis=1) if len(posterior) else np.array([], dtype=int)
    top_probability = posterior.max(axis=1) if len(posterior) else np.array([], dtype=float)
    safe_posterior = np.clip(posterior, 1e-12, 1.0)
    entropy = -np.sum(safe_posterior * np.log(safe_posterior), axis=1) / np.log(max(spec.n_states, 2))
    recent_flip = _recent_flip_flags(top_state, cooldown=spec.flip_cooldown_bars)
    for local_index, position in enumerate(positions):
        for state in range(spec.n_states):
            result.loc[position, f"regime_p_{state}"] = float(posterior[local_index, state])
        result.loc[position, "top_regime_label"] = state_labels.get(int(top_state[local_index]), f"state_{top_state[local_index]}")
        result.loc[position, "max_regime_probability"] = float(top_probability[local_index])
        result.loc[position, "posterior_entropy"] = float(entropy[local_index])
        result.loc[position, "recent_regime_flip"] = bool(recent_flip[local_index])
        result.loc[position, "regime_no_trade"] = bool(
            top_probability[local_index] < spec.posterior_threshold
            or entropy[local_index] > spec.entropy_threshold
            or recent_flip[local_index]
        )
        result.loc[position, "hmm_fit_end_row"] = int(fit_end_row)
        result.loc[position, "source_row_index"] = int(source_index.iloc[position])
        result.loc[position, "hmm_model_id"] = model_id
        result.loc[position, "hmm_feature_pack_id"] = spec.hmm_feature_pack_id
        result.loc[position, "hmm_split_id"] = split_id
