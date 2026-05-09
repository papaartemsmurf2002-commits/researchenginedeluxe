from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tradingbotsuite.backtesting.splits import build_purged_walk_forward_splits
from tradingbotsuite.research_discovery.hmm_materialization import (
    HmmMaterializationSpec,
    materialize_split_safe_hmm_regimes,
)
from tradingbotsuite.research_discovery.knn_study import (
    KNN_PREDICTION_COLUMNS,
    KnnStudySpec,
    _TrainOnlyScaler,
    _label_horizon_bars,
    _predict_precomputed_row,
    _predict_row,
    _stable_topk_distance_order,
    _validation_positions,
    materialize_regime_local_knn_predictions,
    write_knn_study_artifacts,
)
from tradingbotsuite.research_discovery.strategy_integration import (
    account_hmm_knn_local_analog_strategy,
    write_strategy_accounting_artifacts,
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


def _labeled_frame(row_count: int = 150) -> pd.DataFrame:
    rows = []
    start_ms = 1712649600000
    for index in range(row_count):
        phase = index // 25
        slope = 0.25 if phase % 3 == 1 else (-0.25 if phase % 3 == 2 else 0.02)
        vol = 0.03 if phase % 4 == 3 else 0.01
        label_up = 1.0 if slope >= 0.0 else 0.0
        rows.append(
            {
                "bar_time_ms": start_ms + index * 900_000,
                "source_row_index": index,
                "log_return_1": slope * 0.001 + np.sin(index / 5.0) * 0.0001,
                "log_return_4": slope * 0.002 + np.sin(index / 7.0) * 0.0001,
                "trend_slope_20": slope,
                "efficiency_ratio": 0.4 + abs(slope),
                "directional_slope_atr": slope,
                "realized_volatility": vol,
                "atr_percentile": min(0.95, 0.2 + vol * 10.0),
                "choppiness": 35.0 + 5.0 * (phase % 2),
                "label_up": label_up,
                "label_return": 0.01 if label_up == 1.0 else -0.01,
            }
        )
    return pd.DataFrame(rows)


def _splits(frame: pd.DataFrame):
    return build_purged_walk_forward_splits(
        frame,
        min_splits=3,
        purge_embargo_bars=2,
        time_column="bar_time_ms",
    )


def _hmm_spec() -> HmmMaterializationSpec:
    return HmmMaterializationSpec.from_payload(
        {
            "feature_columns": list(FEATURE_COLUMNS),
            "n_states": 4,
            "posterior_threshold": 0.0 + 0.01,
            "entropy_threshold": 1.0,
            "flip_cooldown_bars": 0,
            "min_training_rows": 24,
            "random_state": 73,
            "max_iter": 50,
            "covariance_type": "diag",
            "hmm_feature_pack_id": "test_hmm_pack",
        }
    )


def _knn_spec(**overrides: object) -> KnnStudySpec:
    payload = {
        "feature_columns": list(FEATURE_COLUMNS),
        "label_column": "label_up",
        "pnl_column": "label_return",
        "k": 6,
        "distance_metric": "euclidean",
        "probability_threshold": 0.50,
        "expected_value_threshold": -0.02,
        "min_neighbor_count": 3,
        "min_neighbor_agreement": 0.50,
        "min_distance_quality": 0.0,
        "vote_margin_threshold": 0.0,
        "same_regime_only": True,
        "feature_column_set_id": "price_trend_vol",
        "label_horizon": "4h",
    }
    payload.update(overrides)
    return KnnStudySpec.from_payload(payload)


def _hmm_frame() -> tuple[pd.DataFrame, object]:
    base = _labeled_frame()
    splits = _splits(base)
    hmm = materialize_split_safe_hmm_regimes(base, splits=splits, spec=_hmm_spec()).frame
    return hmm, splits


def test_knn_study_emits_strategy_prediction_columns_and_split_safe_neighbors() -> None:
    frame, splits = _hmm_frame()
    result = materialize_regime_local_knn_predictions(frame, splits=splits, spec=_knn_spec())
    evaluated = result.frame[result.frame["neighbor_count"] > 0]

    assert set(KNN_PREDICTION_COLUMNS) <= set(result.frame.columns)
    assert not evaluated.empty
    assert (evaluated["neighbor_min_source_index"] <= evaluated["neighbor_max_source_index"]).all()
    assert (evaluated["neighbor_max_source_index"] <= evaluated["hmm_fit_end_row"]).all()
    assert (evaluated["hmm_fit_end_row"] < evaluated["source_row_index"]).all()
    assert (
        result.neighbor_diagnostics["neighbor_source_index"] + result.manifest["label_horizon_bars"]
        < result.neighbor_diagnostics["source_row_index"]
    ).all()
    assert result.manifest["split_safety_passed"] is True
    assert result.manifest["research_only"] is True
    assert result.manifest["observe_only"] is True
    assert result.manifest["promotion_ready"] is False
    assert result.manifest["order_placement_used"] is False


def test_vectorized_knn_prediction_matches_row_helper() -> None:
    frame, splits = _hmm_frame()
    spec = _knn_spec()
    ordered = frame.reset_index(drop=True).copy()
    split = splits[0]
    validation_positions = _validation_positions(split, row_count=len(ordered))
    train_positions = list(range(max(0, int(split.train_start_index)), max(-1, int(split.train_end_index)) + 1))
    train = ordered.iloc[train_positions].copy()
    validation_source_min = int(
        pd.to_numeric(ordered.iloc[validation_positions]["source_row_index"], errors="raise")
        .astype("int64")
        .min()
    )
    label_horizon_bars = _label_horizon_bars(ordered, spec.label_horizon)
    train_source_series = pd.to_numeric(train["source_row_index"], errors="raise").astype("int64")
    train = train.loc[train_source_series <= validation_source_min - label_horizon_bars - 1].copy()
    train = train.dropna(subset=[spec.label_column, spec.pnl_column], how="any")
    assert len(train) >= spec.min_neighbor_count

    scaler = _TrainOnlyScaler.fit(train, spec.feature_columns)
    train_matrix = scaler.transform(train)
    train_source = pd.to_numeric(train["source_row_index"], errors="raise").astype("int64").to_numpy()
    train_regimes = train["top_regime_label"].astype(str).to_numpy()
    labels = pd.to_numeric(train[spec.label_column], errors="coerce").fillna(0.0).clip(0.0, 1.0).to_numpy(dtype=float)
    pnl = pd.to_numeric(train[spec.pnl_column], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    validation = ordered.iloc[validation_positions].copy()
    validation_matrix = scaler.transform(validation)

    checked = 0
    for offset, position in enumerate(validation_positions):
        row = ordered.iloc[position]
        row_prediction, row_diagnostics = _predict_row(
            row,
            train_matrix=train_matrix,
            train_source=train_source,
            train_regimes=train_regimes,
            labels=labels,
            pnl=pnl,
            scaler=scaler,
            spec=spec,
            split_id=str(split.split_id),
        )
        vector_prediction, vector_diagnostics = _predict_precomputed_row(
            source_row=int(row["source_row_index"]),
            fit_end=int(row["hmm_fit_end_row"]),
            no_trade=bool(row["regime_no_trade"]),
            query_regime=str(row["top_regime_label"] or ""),
            query_matrix=validation_matrix[offset],
            train_matrix=train_matrix,
            train_source=train_source,
            train_regimes=train_regimes,
            labels=labels,
            pnl=pnl,
            spec=spec,
            split_id=str(split.split_id),
        )

        assert vector_prediction == row_prediction
        assert vector_diagnostics == row_diagnostics
        checked += 1
        if checked >= 12:
            break

    assert checked == 12


def test_stable_topk_distance_order_matches_full_stable_sort_with_boundary_ties() -> None:
    distances = np.array([0.4, 0.1, 0.2, 0.2, 0.05, 0.2, 0.8, 0.2], dtype=float)

    order = _stable_topk_distance_order(distances, k=4)
    full_order = np.argsort(distances, kind="mergesort")[:4]

    np.testing.assert_array_equal(order, full_order)
    np.testing.assert_array_equal(order, np.array([4, 1, 2, 3]))


def test_stable_topk_distance_order_matches_full_stable_sort_for_random_distances() -> None:
    rng = np.random.default_rng(73)
    distances = rng.normal(size=512)

    for k in (1, 3, 8, 21, 128, 512, 999):
        order = _stable_topk_distance_order(distances, k=k)
        full_order = np.argsort(distances, kind="mergesort")[: min(k, len(distances))]
        np.testing.assert_array_equal(order, full_order)


def test_knn_neighbors_are_same_regime_when_configured() -> None:
    frame, splits = _hmm_frame()
    result = materialize_regime_local_knn_predictions(frame, splits=splits, spec=_knn_spec())
    diagnostics = result.neighbor_diagnostics

    assert not diagnostics.empty
    assert diagnostics["neighbor_regime"].eq(diagnostics["query_regime"]).all()


def test_knn_study_is_train_only_for_earlier_splits() -> None:
    base = _labeled_frame()
    splits = _splits(base)
    hmm_base = materialize_split_safe_hmm_regimes(base, splits=splits, spec=_hmm_spec()).frame
    base_knn = materialize_regime_local_knn_predictions(hmm_base, splits=splits, spec=_knn_spec()).frame

    changed = base.copy()
    first_split_end = int(splits[0].validation_end_index)
    changed.loc[first_split_end + 1 :, list(FEATURE_COLUMNS)] *= 500.0
    changed.loc[first_split_end + 1 :, "label_up"] = 1.0 - changed.loc[first_split_end + 1 :, "label_up"]
    changed.loc[first_split_end + 1 :, "label_return"] *= -1.0
    hmm_changed = materialize_split_safe_hmm_regimes(changed, splits=splits, spec=_hmm_spec()).frame
    changed_knn = materialize_regime_local_knn_predictions(hmm_changed, splits=splits, spec=_knn_spec()).frame

    first_split_mask = hmm_base["hmm_split_id"].eq(splits[0].split_id)
    compare_columns = ["p_up_barrier", "p_down_barrier", "neighbor_count", "neighbor_max_source_index", "knn_skip_reason"]
    pd.testing.assert_frame_equal(
        base_knn.loc[first_split_mask, compare_columns].reset_index(drop=True),
        changed_knn.loc[first_split_mask, compare_columns].reset_index(drop=True),
    )


def test_knn_study_blocks_insufficient_neighbors() -> None:
    frame, splits = _hmm_frame()
    result = materialize_regime_local_knn_predictions(frame, splits=splits, spec=_knn_spec(k=6, min_neighbor_count=6))

    assert "insufficient_regime_neighbors" in set(result.frame["knn_skip_reason"])
    blocked = result.frame[result.frame["knn_skip_reason"].eq("insufficient_regime_neighbors")]
    assert blocked["neighbor_count"].eq(0).all()


def test_knn_study_rejects_missing_columns() -> None:
    frame, splits = _hmm_frame()

    with pytest.raises(ValueError, match="knn_study_missing_columns:label_return"):
        materialize_regime_local_knn_predictions(frame.drop(columns=["label_return"]), splits=splits, spec=_knn_spec())


def test_knn_study_writes_research_only_artifacts(tmp_path: Path) -> None:
    frame, splits = _hmm_frame()
    result = materialize_regime_local_knn_predictions(frame, splits=splits, spec=_knn_spec())

    artifacts = write_knn_study_artifacts(tmp_path / "knn", result)
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    predictions = pd.read_parquet(artifacts.predictions_path)
    diagnostics = pd.read_parquet(artifacts.neighbor_diagnostics_path)

    assert manifest["knn_study_manifest_version"] == "discovery-knn-study-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["required_outputs"]["knn_predictions"] == str(artifacts.predictions_path)
    assert not predictions.empty
    assert not diagnostics.empty


def test_knn_study_artifacts_refuse_overwrite(tmp_path: Path) -> None:
    frame, splits = _hmm_frame()
    result = materialize_regime_local_knn_predictions(frame, splits=splits, spec=_knn_spec())
    output_dir = tmp_path / "knn"
    write_knn_study_artifacts(output_dir, result)

    with pytest.raises(ValueError, match="refusing to overwrite existing KNN study artifacts"):
        write_knn_study_artifacts(output_dir, result)


def test_knn_predictions_flow_into_strategy_accounting(tmp_path: Path) -> None:
    frame, splits = _hmm_frame()
    result = materialize_regime_local_knn_predictions(frame, splits=splits, spec=_knn_spec())

    accounting = account_hmm_knn_local_analog_strategy(
        result.frame,
        holding_window="24h",
        strategy_config={
            "spacing_bars": 1,
            "min_neighbor_count": 1,
            "min_neighbor_agreement": 0.01,
            "min_neighbor_distance_quality": 0.0,
            "min_vote_margin": 0.0,
            "posterior_threshold": 0.01,
            "entropy_threshold": 1.0,
            "probability_threshold": 0.50,
            "expected_value_threshold": -0.02,
        },
    )
    artifacts = write_strategy_accounting_artifacts(tmp_path / "strategy", accounting)
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    signals = pd.read_parquet(artifacts.signals_path)

    assert manifest["strategy_accounting_manifest_version"] == "discovery-strategy-accounting-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["raw_knn_accepted_row_count"] > 0
    assert manifest["plugin_signal_count"] > 0
    assert manifest["backtest_executable_signal_count"] == manifest["plugin_signal_count"]
    assert manifest["filter_block_count"] == 0
    assert not signals.empty


def test_knn_study_spec_config_loads() -> None:
    spec = KnnStudySpec.from_path(Path("configs/discovery/knn_study_v4.json"))

    assert spec.feature_columns == FEATURE_COLUMNS
    assert spec.feature_column_set_id == "price_trend_vol"
