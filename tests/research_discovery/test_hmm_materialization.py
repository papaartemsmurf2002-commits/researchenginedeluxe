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


def test_hmm_materialization_spec_config_loads() -> None:
    spec = HmmMaterializationSpec.from_path(Path("configs/discovery/hmm_materialization_v4.json"))

    assert spec.feature_columns == FEATURE_COLUMNS
    assert spec.hmm_feature_pack_id == "discovery_hmm_price_trend_vol_v4"
