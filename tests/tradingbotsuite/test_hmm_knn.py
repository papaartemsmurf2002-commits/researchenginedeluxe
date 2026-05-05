from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import numpy as np
import pandas as pd
import pytest

import tradingbotsuite.research.hmm_knn as hmm_knn
from tradingbotsuite.research.hmm_knn import (
    HMM_KNN_FEATURE_VERSION,
    KNN_OUTPUT_COLUMNS,
    RegimeModel,
    WT3D_FEATURE_COLUMNS,
    _leakage_safe_meta_knn_features,
    _fit_meta_model,
    _knn_distance_backend_report,
    _knn_predict,
    _overall_metrics,
    _posterior_frame,
    _prepare_dataset,
    _resolve_lorentzian_distance_backend,
    _split_metrics,
    _xgboost_cuda_dependency_report,
    _walk_forward_frames,
    build_wt3d_features,
    load_hmm_knn_plan,
    lorentzian_distance_matrix,
    replay_hmm_knn_artifact,
    robust_scaler_fit,
    run_hmm_knn_research,
)
from tradingbotsuite.research.dataset import LABEL_OUTCOME_COLUMNS
from tradingbotsuite.research.deterministic_datasets import (
    build_hmm_knn_sweep_dataset,
    write_hmm_knn_sweep_dataset,
)
from tradingbotsuite.research.hmm_knn_experiments import run_hmm_knn_experiment_matrix
from tradingbotsuite.research.hmm_knn_monitoring import monitor_hmm_knn_artifact
from tradingbotsuite.strategies.hmm_knn.config import resolve_feature_columns
from tradingbotsuite.strategies.hmm_knn.distances import (
    available_distance_metrics,
    resolve_distance_function,
    resolve_distance_metric,
)


def _write_test_config(tmp_path: Path) -> Path:
    payload = json.loads(Path("configs/v2_btc_hmm_multi_knn_research.json").read_text(encoding="utf-8"))
    payload["version"] = "test-hmm-knn"
    payload["hmm"]["n_states"] = 3
    payload["hmm"]["posterior_threshold"] = 0.45
    payload["hmm"]["entropy_threshold"] = 0.95
    payload["knn"]["primary_k"] = 12
    payload["knn"]["k_values"] = [8, 12]
    payload["knn"]["min_neighbor_count"] = 3
    payload["evaluation"]["min_training_rows"] = 36
    payload["evaluation"]["walk_forward_splits"] = 2
    payload["evaluation"]["purge_embargo_bars"] = 2
    payload["acceptance"]["min_trade_count"] = 1
    config_path = tmp_path / "hmm_knn_config.json"
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


def _write_modified_test_config(tmp_path: Path, **updates: object) -> Path:
    payload = json.loads(Path("configs/v2_btc_hmm_multi_knn_research.json").read_text(encoding="utf-8"))
    payload["version"] = "test-hmm-knn"
    payload["hmm"]["n_states"] = 3
    payload["hmm"]["posterior_threshold"] = 0.45
    payload["hmm"]["entropy_threshold"] = 0.95
    payload["knn"]["primary_k"] = 12
    payload["knn"]["k_values"] = [8, 12]
    payload["knn"]["min_neighbor_count"] = 3
    payload["evaluation"]["min_training_rows"] = 36
    payload["evaluation"]["walk_forward_splits"] = 2
    payload["evaluation"]["purge_embargo_bars"] = 2
    payload["acceptance"]["min_trade_count"] = 1
    for dotted_key, value in updates.items():
        section, key = dotted_key.split("__", maxsplit=1)
        payload[section][key] = value
    config_path = tmp_path / "hmm_knn_modified_config.json"
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


def _synthetic_dataset(row_count: int = 120) -> pd.DataFrame:
    rows = []
    start_ms = 1712649600000
    price = 70000.0
    for index in range(row_count):
        regime = index // 30
        if regime == 0:
            drift = 8.0 * ((index % 2) - 0.5)
            vol = 0.004
            slope = 0.05
            label = 1 if index % 4 in {0, 1} else 0
        elif regime == 1:
            drift = 35.0
            vol = 0.009
            slope = 0.65
            label = 1 if index % 5 != 0 else 0
        elif regime == 2:
            drift = -30.0
            vol = 0.011
            slope = -0.60
            label = 1 if index % 5 == 0 else 0
        else:
            drift = 80.0 if index % 2 == 0 else -90.0
            vol = 0.035
            slope = -0.10
            label = 0 if index % 3 else 1
        price += drift
        direction = "long" if index % 2 == 0 else "short"
        rows.append(
            {
                "signal_id": f"sig-{index}",
                "source": "external_signal",
                "symbol": "BTCUSDT",
                "direction": direction,
                "direction_long": 1.0 if direction == "long" else 0.0,
                "signal_bar_time_ms": start_ms + (index * 900_000),
                "entry_price": price,
                "label_accept": label,
                "label_pnl_multiple": 1.4 if label else -0.9,
                "label_exit_reason": "take_profit" if label else "stop_loss",
                "efficiency_ratio": min(abs(slope), 1.0),
                "choppiness": 62.0 if regime == 0 else (28.0 if regime in {1, 2} else 44.0),
                "directional_slope_atr": slope if direction == "long" else -slope,
                "directional_di_spread": slope * 20.0,
                "range_width": 0.005 + vol,
                "primary_signed_imbalance_ratio": 0.35 if drift > 0 else -0.35,
                "primary_sqrt_signed_imbalance_ratio": 0.25 if drift > 0 else -0.25,
                "top_of_book_imbalance": 0.2 if drift > 0 else -0.2,
                "queue_imbalance_l5": 0.15 if drift > 0 else -0.15,
                "spread_bps": 3.0 + (regime == 3) * 6.0,
                "basis_bps": 2.0 + regime,
                "funding_rate": 0.00008 if regime == 1 else (-0.00004 if regime == 2 else 0.00001),
                "funding_rate_change": 0.00001,
                "open_interest_change_pct": 0.04 if regime in {1, 3} else -0.02,
                "premium_basis_rate": 0.0002 if regime == 1 else -0.0001,
                "realized_volatility": vol,
                "atr_percentile": min(0.95, 0.25 + vol * 20),
                "volatility_shock_zscore": 3.0 if regime == 3 else 0.4,
            }
        )
    return pd.DataFrame(rows)


def test_hmm_knn_synthetic_fixture_contract_is_btc_phase_1_and_offline(tmp_path) -> None:
    config_path = _write_test_config(tmp_path)
    plan = load_hmm_knn_plan(config_path)
    frame = _synthetic_dataset()
    dataset_path = tmp_path / "dataset.parquet"
    frame.to_parquet(dataset_path, index=False)

    required_input_columns = {
        "signal_id",
        "source",
        "symbol",
        "direction",
        "signal_bar_time_ms",
        "entry_price",
        plan.labels.label_column,
        plan.labels.pnl_column,
        "label_exit_reason",
        *plan.hmm.emission_features,
        *[column for column in plan.knn.feature_columns if column not in WT3D_FEATURE_COLUMNS],
    }

    assert set(frame["symbol"].astype(str).str.upper()) == {"BTCUSDT"}
    assert plan.symbol == "BTCUSDT"
    assert plan.asset_scope == ["BTCUSDT"]
    assert frame["source"].eq("external_signal").all()
    assert frame["signal_bar_time_ms"].diff().dropna().eq(900_000).all()
    assert frame[plan.labels.label_column].nunique() == 2
    assert required_input_columns.issubset(frame.columns)

    raw_context_columns = [
        column
        for column in frame.columns
        if column.startswith("raw_") or column.startswith("missing_") or column.endswith("_context_json")
    ]
    assert raw_context_columns == []
    assert {"funding_rate", "funding_rate_change", "open_interest_change_pct", "premium_basis_rate"}.issubset(frame.columns)

    prepared = _prepare_dataset(dataset_path, plan)
    assert set(plan.knn.feature_columns).issubset(prepared.columns)
    assert set(plan.hmm.emission_features).issubset(prepared.columns)
    assert set(LABEL_OUTCOME_COLUMNS).issubset(prepared.columns)


def test_hmm_knn_deterministic_sweep_dataset_rewrites_identical_artifacts(tmp_path) -> None:
    first = write_hmm_knn_sweep_dataset(output_dir=tmp_path, row_count=120, variant="balanced")
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    second = write_hmm_knn_sweep_dataset(output_dir=tmp_path, row_count=120, variant="balanced")
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))

    assert first.logical_sha256 == second.logical_sha256
    assert first.csv_sha256 == second.csv_sha256
    assert first.parquet_sha256 == second.parquet_sha256
    assert first_manifest == second_manifest
    assert first_manifest["research_only"] is True
    assert first_manifest["determinism"]["no_random_inputs"] is True
    assert first_manifest["asset_scope"] == ["BTCUSDT"]
    assert first_manifest["raw_context_available_counts"]["raw_spread_bps"] == 120
    assert first_manifest["exchange_context_summary"]["microstructure_context"]["successful_count"] == 120


def test_hmm_knn_deterministic_sweep_variants_are_consumable_and_auditable(tmp_path) -> None:
    plan = load_hmm_knn_plan(_write_test_config(tmp_path))
    balanced = build_hmm_knn_sweep_dataset(row_count=120, variant="balanced")
    sparse = build_hmm_knn_sweep_dataset(row_count=120, variant="sparse_context")
    balanced_path = tmp_path / "balanced.parquet"
    sparse_path = tmp_path / "sparse.parquet"
    balanced.to_parquet(balanced_path, index=False)
    sparse.to_parquet(sparse_path, index=False)

    assert set(balanced["symbol"]) == {"BTCUSDT"}
    assert set(sparse["symbol"]) == {"BTCUSDT"}
    assert balanced["label_accept"].nunique() == 2
    assert sparse["label_accept"].nunique() == 2
    assert balanced["missing_spread_bps"].mean() == 0.0
    assert sparse["missing_spread_bps"].mean() == 1.0
    assert sparse["raw_spread_bps"].isna().all()
    assert sparse["spread_bps"].eq(0.0).all()
    assert set(LABEL_OUTCOME_COLUMNS).issubset(balanced.columns)
    assert not set(LABEL_OUTCOME_COLUMNS).intersection(plan.knn.feature_columns)

    prepared_balanced = _prepare_dataset(balanced_path, plan)
    prepared_sparse = _prepare_dataset(sparse_path, plan)

    assert set(plan.knn.feature_columns).issubset(prepared_balanced.columns)
    assert set(plan.hmm.emission_features).issubset(prepared_balanced.columns)
    assert set(plan.knn.feature_columns).issubset(prepared_sparse.columns)
    assert set(plan.hmm.emission_features).issubset(prepared_sparse.columns)


def test_lorentzian_distance_is_deterministic_and_compresses_outliers() -> None:
    train = np.array([[0.0, 0.0], [1.0, 1.0], [100.0, 100.0]])
    query = np.array([[0.0, 0.0]])
    distances = lorentzian_distance_matrix(query, train, np.array([1.0, 1.0]))[0]

    assert distances.tolist() == lorentzian_distance_matrix(query, train, np.array([1.0, 1.0]))[0].tolist()
    assert distances[2] < 100.0
    with pytest.raises(ValueError, match="finite positive"):
        lorentzian_distance_matrix(query, train, np.array([1.0, 0.0]))
    with pytest.raises(ValueError, match="knn.distance_backend"):
        lorentzian_distance_matrix(query, train, backend="gpu")


def test_lorentzian_distance_auto_backend_falls_back_to_cpu_without_cupy(monkeypatch) -> None:
    monkeypatch.setattr(hmm_knn, "_import_cupy", lambda: None)
    train = np.array([[0.0, 0.0], [2.0, 4.0]])
    query = np.array([[1.0, 1.0]])

    distances = lorentzian_distance_matrix(query, train, backend="auto")

    np.testing.assert_allclose(distances, lorentzian_distance_matrix(query, train, backend="cpu"))
    assert _resolve_lorentzian_distance_backend("auto") == "cpu"
    assert _knn_distance_backend_report("auto") == {
        "knn_distance_backend_requested": "auto",
        "knn_distance_backend": "cpu",
        "cupy_available": False,
        "cupy_error": None,
    }


def test_lorentzian_distance_cupy_backend_dispatches_through_optional_import(monkeypatch) -> None:
    calls: dict[str, int] = {"asarray": 0}

    def fake_asarray(value, dtype=float):
        calls["asarray"] += 1
        return np.asarray(value, dtype=dtype)

    fake_cupy = types.SimpleNamespace(
        asarray=fake_asarray,
        abs=np.abs,
        log1p=np.log1p,
        asnumpy=lambda value: np.asarray(value),
    )
    monkeypatch.setitem(sys.modules, "cupy", fake_cupy)
    train = np.array([[0.0, 0.0], [3.0, 4.0]])
    query = np.array([[1.0, 2.0]])

    distances = lorentzian_distance_matrix(query, train, backend="cupy")

    np.testing.assert_allclose(distances, lorentzian_distance_matrix(query, train, backend="cpu"))
    assert _resolve_lorentzian_distance_backend("cupy") == "cupy"
    assert calls["asarray"] >= 3


def test_knn_config_accepts_distance_backend_and_rejects_unknown_backend(tmp_path) -> None:
    auto_config = _write_modified_test_config(tmp_path, knn__distance_backend="auto")
    auto_plan = load_hmm_knn_plan(auto_config)

    assert auto_plan.knn.distance_backend == "auto"

    bad_config = _write_modified_test_config(tmp_path, knn__distance_backend="gpu")
    with pytest.raises(ValueError, match="knn.distance_backend"):
        load_hmm_knn_plan(bad_config)


def test_wt3d_features_use_completed_history_without_future_pivots() -> None:
    frame = pd.DataFrame({"entry_price": [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 105.0]})
    plan = load_hmm_knn_plan(Path("configs/v2_btc_hmm_multi_knn_research.json"))
    baseline = build_wt3d_features(frame, plan.wt3d)
    changed = frame.copy()
    changed.loc[6, "entry_price"] = 1000.0
    perturbed = build_wt3d_features(changed, plan.wt3d)

    pd.testing.assert_frame_equal(baseline.loc[:5, WT3D_FEATURE_COLUMNS], perturbed.loc[:5, WT3D_FEATURE_COLUMNS])
    assert set(baseline.columns) >= {"wt3d_fast", "wt3d_normal", "wt3d_slow", "wt3d_mtf_agreement"}


def test_wt3d_missing_price_fill_does_not_backfill_from_future_rows() -> None:
    plan = load_hmm_knn_plan(Path("configs/v2_btc_hmm_multi_knn_research.json"))
    frame = pd.DataFrame({"entry_price": [np.nan, 101.0, 102.0, 103.0]})
    baseline = build_wt3d_features(frame, plan.wt3d)
    changed = frame.copy()
    changed.loc[1, "entry_price"] = 1000.0
    perturbed = build_wt3d_features(changed, plan.wt3d)

    pd.testing.assert_series_equal(baseline.loc[:0, "wt3d_normal"], perturbed.loc[:0, "wt3d_normal"])


def test_robust_scaler_is_train_only_and_maps_missing_to_neutral() -> None:
    train = pd.DataFrame({"feature": [0.0, 10.0, 20.0], "all_missing": [np.nan, np.nan, np.nan]})
    test = pd.DataFrame({"feature": [1000.0], "all_missing": [np.nan]})

    scaler = robust_scaler_fit(train, ["feature", "all_missing"])
    transformed_train = scaler.transform(train)
    transformed_test = scaler.transform(test)

    assert scaler.median.tolist() == [10.0, 0.0]
    assert scaler.scale.tolist() == [10.0, 1.0]
    assert transformed_train[:, 0].tolist() == [-1.0, 0.0, 1.0]
    assert transformed_test[0, 0] == 99.0
    assert transformed_test[0, 1] == 0.0


def test_public_feature_columns_are_reflected_in_model_spec() -> None:
    plan = load_hmm_knn_plan(Path("configs/v2_btc_hmm_multi_knn_research.json"))
    spec = Path("docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md").read_text(encoding="utf-8")

    assert "Agent Artifact Communication" in spec
    assert "feature_columns" in spec
    assert "Missing prices are forward-filled from prior rows only" in spec
    assert "Validation/test rows do not influence HMM emissions, KNN distances, or meta-model KNN feature scaling" in spec
    for column in [*plan.knn.feature_columns, *plan.hmm.emission_features, *WT3D_FEATURE_COLUMNS, *KNN_OUTPUT_COLUMNS]:
        assert f"`{column}`" in spec
    for column in LABEL_OUTCOME_COLUMNS:
        assert f"`{column}`" in spec


def test_meta_training_knn_features_use_prior_rows_with_embargo(tmp_path) -> None:
    config_path = _write_modified_test_config(
        tmp_path,
        knn__min_neighbor_count=1,
        evaluation__purge_embargo_bars=2,
    )
    plan = load_hmm_knn_plan(config_path)
    frame = _synthetic_dataset(50)
    scaler = robust_scaler_fit(frame, plan.knn.feature_columns)
    posterior = pd.DataFrame({"top_regime": [0] * len(frame)})

    oof = _leakage_safe_meta_knn_features(
        train_frame=frame,
        train_posterior=posterior,
        feature_scaler=scaler,
        plan=plan,
    )
    available = oof.loc[oof["meta_knn_oof_available"].astype(bool)].copy()

    assert not available.empty
    assert (available["neighbor_max_source_index"].astype(int) < available.index).all()
    assert (available["neighbor_max_source_index"].astype(int) <= available.index - 3).all()
    assert set(oof["meta_knn_feature_source"]) == {"prior_train_rows_with_embargo"}


def test_hmm_online_posterior_is_forward_only_for_prefix_rows() -> None:
    class FakeHmm:
        startprob_ = np.array([0.5, 0.5])
        transmat_ = np.array([[0.85, 0.15], [0.20, 0.80]])

        def _compute_log_likelihood(self, matrix: np.ndarray) -> np.ndarray:
            values = matrix[:, 0]
            return np.column_stack([-np.abs(values), -np.abs(values - 10.0)])

    model = RegimeModel(backend="hmmlearn", model=FakeHmm(), n_states=2, state_labels={0: "low", 1: "high"})
    prefix = np.array([[0.0], [0.5], [1.0]])
    extended = np.vstack([prefix, [[20.0], [25.0], [30.0]]])

    np.testing.assert_allclose(model.posterior(prefix), model.posterior(extended)[: len(prefix)])


def test_uncertain_regime_posterior_sets_no_trade_flag() -> None:
    plan = load_hmm_knn_plan(Path("configs/v2_btc_hmm_multi_knn_research.json"))
    base = pd.DataFrame(
        {
            "signal_id": ["sig-1", "sig-2"],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "direction": ["long", "short"],
            "signal_bar_time_ms": [1712649600000, 1712650500000],
        },
        index=[10, 11],
    )
    posterior = np.array([[0.25, 0.25, 0.25, 0.25], [0.40, 0.30, 0.20, 0.10]])
    model = RegimeModel(
        backend="test",
        model=None,
        n_states=4,
        state_labels={0: "range_chop", 1: "bull_trend", 2: "bear_trend", 3: "shock_transition"},
    )

    regimes = _posterior_frame(base_frame=base, posterior=posterior, model=model, plan=plan, split_index=0, fit_end_index=9)

    assert regimes["regime_no_trade"].tolist() == [True, True]
    assert regimes["hmm_fit_end_row"].tolist() == [9, 9]


def test_degenerate_regime_posterior_normalizes_to_uniform_no_trade() -> None:
    class DegeneratePosteriorModel:
        def predict_proba(self, matrix: np.ndarray) -> np.ndarray:
            return np.array(
                [
                    [np.nan, np.inf, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ]
            )

    plan = load_hmm_knn_plan(Path("configs/v2_btc_hmm_multi_knn_research.json"))
    model = RegimeModel(
        backend="degenerate_test",
        model=DegeneratePosteriorModel(),
        n_states=4,
        state_labels={0: "range_chop", 1: "bull_trend", 2: "bear_trend", 3: "shock_transition"},
    )
    posterior = model.posterior(np.zeros((2, 1)))
    base = pd.DataFrame(
        {
            "signal_id": ["degenerate-1", "degenerate-2"],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "direction": ["long", "short"],
            "signal_bar_time_ms": [1712649600000, 1712650500000],
        },
        index=[20, 21],
    )

    regimes = _posterior_frame(base_frame=base, posterior=posterior, model=model, plan=plan, split_index=3, fit_end_index=19)

    np.testing.assert_allclose(posterior, np.full((2, 4), 0.25))
    assert regimes["max_regime_probability"].tolist() == [0.25, 0.25]
    assert regimes["posterior_entropy"].tolist() == [pytest.approx(1.0), pytest.approx(1.0)]
    assert regimes["regime_no_trade"].tolist() == [True, True]
    assert regimes["regime_model_backend"].tolist() == ["degenerate_test", "degenerate_test"]
    assert regimes["walk_forward_split"].tolist() == [3, 3]
    assert regimes["source_row_index"].tolist() == [20, 21]
    assert regimes["hmm_fit_end_row"].tolist() == [19, 19]


def test_knn_config_accepts_pluggable_distances_and_rejects_unknown_distance(tmp_path) -> None:
    euclidean_config = _write_modified_test_config(tmp_path, knn__distance="euclidean_robust_z")
    euclidean_plan = load_hmm_knn_plan(euclidean_config)
    normalized_config = _write_modified_test_config(tmp_path, knn__distance=" Lorentzian ")
    normalized_plan = load_hmm_knn_plan(normalized_config)

    assert euclidean_plan.knn.distance == "euclidean_robust_z"
    assert resolve_distance_metric(normalized_plan.knn.distance).id == "lorentzian"

    bad_config = _write_modified_test_config(tmp_path, knn__distance="euclidean")
    with pytest.raises(ValueError, match="knn.distance must be one of"):
        load_hmm_knn_plan(bad_config)


def test_hmm_knn_feature_packs_and_distance_functions_are_resolvable() -> None:
    with_wt3d = resolve_feature_columns("full_context_wt3d")
    without_wt3d = resolve_feature_columns("full_context_no_wt3d")
    query = np.array([[0.0, 1.0, 0.5]])
    train = np.array([[0.0, 1.0, 0.5], [3.0, -1.0, 0.25]])

    lorentzian = resolve_distance_function("lorentzian")(query, train, None)
    euclidean = resolve_distance_function("euclidean_robust_z")(query, train, None)
    cosine = resolve_distance_function("cosine")(query, train, None)

    assert any(column.startswith("wt3d_") for column in with_wt3d)
    assert not any(column.startswith("wt3d_") for column in without_wt3d)
    assert lorentzian.shape == euclidean.shape == cosine.shape == (1, 2)
    assert not np.allclose(lorentzian, euclidean)


def test_distance_metric_registry_exposes_metadata_and_aliases() -> None:
    metrics = available_distance_metrics()

    assert set(metrics) == {"cosine", "euclidean_robust_z", "lorentzian"}
    assert metrics["lorentzian"]["supports_backend"] == ["cpu", "auto", "cupy"]
    assert metrics["lorentzian"]["feature_scale_mode"] == "robust_z_or_supplied_scale"
    assert resolve_distance_metric("log_lorentzian").id == "lorentzian"
    assert resolve_distance_metric("cosine").display_name == "Cosine"

    with pytest.raises(ValueError, match="unsupported_hmm_knn_distance"):
        resolve_distance_metric("euclidean")


def test_knn_primary_output_uses_primary_k_and_weighting(tmp_path) -> None:
    config_path = _write_modified_test_config(
        tmp_path,
        knn__primary_k=2,
        knn__k_values=[1, 2],
        knn__neighbor_weighting=["inverse_distance"],
        knn__primary_weighting="inverse_distance",
        knn__min_neighbor_count=1,
        evaluation__fee_bps=0.0,
        evaluation__slippage_bps=0.0,
        evaluation__funding_cost_enabled=False,
    )
    plan = load_hmm_knn_plan(config_path)
    train_frame = pd.DataFrame(
        {
            "signal_id": ["train-1", "train-2"],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "direction": ["long", "long"],
            "signal_bar_time_ms": [1, 2],
            "label_accept": [1, 0],
            "label_pnl_multiple": [1.0, -1.0],
        },
        index=[0, 1],
    )
    test_frame = pd.DataFrame(
        {
            "signal_id": ["test-1"],
            "symbol": ["BTCUSDT"],
            "direction": ["long"],
            "signal_bar_time_ms": [3],
            "label_accept": [1],
            "label_pnl_multiple": [1.0],
        },
        index=[2],
    )

    primary, diagnostics, sweep = _knn_predict(
        train_matrix=np.array([[0.0], [10.0]]),
        test_matrix=np.array([[0.1]]),
        train_frame=train_frame,
        test_frame=test_frame,
        train_regimes=pd.Series([0, 0], index=train_frame.index),
        test_regimes=pd.Series([0], index=test_frame.index),
        plan=plan,
    )

    k1_probability = float(sweep.loc[sweep["k"] == 1, "p_up_barrier"].iloc[0])
    primary_probability = float(sweep.loc[sweep["is_primary"], "p_up_barrier"].iloc[0])
    assert primary["p_up_barrier"].iloc[0] == primary_probability
    assert primary_probability != k1_probability
    assert set(diagnostics["k"]) == {1, 2}
    assert diagnostics.loc[diagnostics["is_primary"], "k"].unique().tolist() == [2]


def test_knn_same_regime_blocks_cross_regime_neighbors_until_fallback_is_enabled(tmp_path) -> None:
    base_path = _write_modified_test_config(
        tmp_path,
        knn__primary_k=1,
        knn__k_values=[1],
        knn__neighbor_weighting=["inverse_distance"],
        knn__primary_weighting="inverse_distance",
        knn__min_neighbor_count=1,
        knn__allow_cross_regime_fallback=False,
    )
    base_plan = load_hmm_knn_plan(base_path)
    fallback_path = _write_modified_test_config(
        tmp_path,
        knn__primary_k=1,
        knn__k_values=[1],
        knn__neighbor_weighting=["inverse_distance"],
        knn__primary_weighting="inverse_distance",
        knn__min_neighbor_count=1,
        knn__allow_cross_regime_fallback=True,
        knn__regime_match_mode=None,
    )
    train_frame = pd.DataFrame(
        {
            "signal_id": ["train-1"],
            "symbol": ["BTCUSDT"],
            "direction": ["long"],
            "signal_bar_time_ms": [1],
            "label_accept": [1],
            "label_pnl_multiple": [1.0],
        },
        index=[0],
    )
    test_frame = pd.DataFrame(
        {
            "signal_id": ["test-1"],
            "symbol": ["BTCUSDT"],
            "direction": ["long"],
            "signal_bar_time_ms": [2],
            "label_accept": [1],
            "label_pnl_multiple": [1.0],
        },
        index=[1],
    )
    kwargs = {
        "train_matrix": np.array([[0.0]]),
        "test_matrix": np.array([[0.1]]),
        "train_frame": train_frame,
        "test_frame": test_frame,
        "train_regimes": pd.Series([0], index=train_frame.index),
        "test_regimes": pd.Series([1], index=test_frame.index),
    }

    blocked, blocked_diagnostics, blocked_sweep = _knn_predict(**kwargs, plan=base_plan)
    fallback, fallback_diagnostics, fallback_sweep = _knn_predict(**kwargs, plan=load_hmm_knn_plan(fallback_path))

    assert blocked["knn_skip_reason"].tolist() == ["no_same_regime_neighbors"]
    assert blocked_sweep["fallback_used"].tolist() == [False]
    assert blocked_diagnostics["knn_skip_reason"].tolist() == ["no_same_regime_neighbors"]
    assert blocked_diagnostics["neighbor_regime"].isna().all()
    assert fallback["knn_skip_reason"].tolist() == [None]
    assert fallback_sweep["fallback_used"].tolist() == [True]
    assert fallback_diagnostics["fallback_used"].tolist() == [True]
    assert fallback_diagnostics["neighbor_regime"].astype(int).tolist() == [0]
    assert fallback_diagnostics["query_regime"].astype(int).tolist() == [1]
    assert fallback_diagnostics["regime_match_mode"].tolist() == ["same_with_all_fallback"]
    assert fallback_diagnostics["candidate_count_before_regime_filter"].astype(int).tolist() == [1]
    assert fallback_diagnostics["candidate_count_after_regime_filter"].astype(int).tolist() == [1]


def test_knn_explicit_regime_modes_all_and_compatible(tmp_path) -> None:
    all_plan = load_hmm_knn_plan(
        _write_modified_test_config(
            tmp_path,
            knn__primary_k=1,
            knn__k_values=[1],
            knn__neighbor_weighting=["inverse_distance"],
            knn__primary_weighting="inverse_distance",
            knn__min_neighbor_count=1,
            knn__regime_match_mode="all",
        )
    )
    compatible_plan = load_hmm_knn_plan(
        _write_modified_test_config(
            tmp_path,
            knn__primary_k=1,
            knn__k_values=[1],
            knn__neighbor_weighting=["inverse_distance"],
            knn__primary_weighting="inverse_distance",
            knn__min_neighbor_count=1,
            knn__regime_match_mode="compatible",
            knn__compatible_regimes={"bull_trend": ["range_chop"]},
        )
    )
    train_frame = pd.DataFrame(
        {
            "signal_id": ["train-1", "train-2"],
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "direction": ["long", "long"],
            "signal_bar_time_ms": [1, 2],
            "label_accept": [1, 0],
            "label_pnl_multiple": [1.0, -1.0],
        },
        index=[0, 1],
    )
    test_frame = pd.DataFrame(
        {
            "signal_id": ["test-1"],
            "symbol": ["BTCUSDT"],
            "direction": ["long"],
            "signal_bar_time_ms": [3],
            "label_accept": [1],
            "label_pnl_multiple": [1.0],
        },
        index=[2],
    )
    kwargs = {
        "train_matrix": np.array([[0.0], [10.0]]),
        "test_matrix": np.array([[0.1]]),
        "train_frame": train_frame,
        "test_frame": test_frame,
        "train_regimes": pd.Series([0, 3], index=train_frame.index),
        "test_regimes": pd.Series([1], index=test_frame.index),
        "train_regime_labels": pd.Series(["range_chop", "shock_transition"], index=train_frame.index),
        "test_regime_labels": pd.Series(["bull_trend"], index=test_frame.index),
    }

    all_prediction, all_diagnostics, _ = _knn_predict(**kwargs, plan=all_plan)
    compatible_prediction, compatible_diagnostics, _ = _knn_predict(**kwargs, plan=compatible_plan)

    assert all_prediction["knn_skip_reason"].tolist() == [None]
    assert all_diagnostics["regime_match_mode"].tolist() == ["all"]
    assert all_diagnostics["same_regime_only"].tolist() == [False]
    assert all_diagnostics["configured_same_regime_only"].tolist() == [True]
    assert all_diagnostics["candidate_count_after_regime_filter"].astype(int).tolist() == [2]
    assert compatible_prediction["knn_skip_reason"].tolist() == [None]
    assert compatible_diagnostics["regime_match_mode"].tolist() == ["compatible"]
    assert compatible_diagnostics["same_regime_only"].tolist() == [False]
    assert compatible_diagnostics["candidate_count_after_regime_filter"].astype(int).tolist() == [1]
    assert compatible_diagnostics["neighbor_regime"].astype(int).tolist() == [0]
    assert compatible_diagnostics["compatible_regime_labels"].tolist() == ["bull_trend,range_chop"]


def test_regime_fit_ignores_rows_after_current_test_split(tmp_path) -> None:
    config_path = _write_test_config(tmp_path)
    baseline_path = tmp_path / "baseline.parquet"
    perturbed_path = tmp_path / "perturbed.parquet"
    baseline = _synthetic_dataset()
    perturbed = baseline.copy()
    future_mask = perturbed.index >= 100
    perturbed.loc[future_mask, "directional_slope_atr"] = 50.0
    perturbed.loc[future_mask, "realized_volatility"] = 10.0
    perturbed.loc[future_mask, "choppiness"] = 1.0
    perturbed.loc[future_mask, "volatility_shock_zscore"] = 100.0
    baseline.to_parquet(baseline_path, index=False)
    perturbed.to_parquet(perturbed_path, index=False)

    baseline_result = run_hmm_knn_research(config_path=config_path, dataset_path=baseline_path, output_dir=tmp_path / "baseline")
    perturbed_result = run_hmm_knn_research(config_path=config_path, dataset_path=perturbed_path, output_dir=tmp_path / "perturbed")
    baseline_regimes = pd.read_parquet(baseline_result.regime_posteriors_path)
    perturbed_regimes = pd.read_parquet(perturbed_result.regime_posteriors_path)
    compare_columns = [
        "regime_p_0",
        "regime_p_1",
        "regime_p_2",
        "top_regime",
        "max_regime_probability",
        "posterior_entropy",
        "regime_no_trade",
        "hmm_fit_end_row",
    ]

    pd.testing.assert_frame_equal(
        baseline_regimes.loc[baseline_regimes["walk_forward_split"] == 0, compare_columns].reset_index(drop=True),
        perturbed_regimes.loc[perturbed_regimes["walk_forward_split"] == 0, compare_columns].reset_index(drop=True),
    )


def test_hmm_knn_research_writes_expected_research_only_artifacts(tmp_path) -> None:
    config_path = _write_test_config(tmp_path)
    dataset_path = tmp_path / "dataset.parquet"
    _synthetic_dataset().to_parquet(dataset_path, index=False)

    result = run_hmm_knn_research(config_path=config_path, dataset_path=dataset_path, output_dir=tmp_path)
    manifest = json.loads(result.artifact_manifest_path.read_text(encoding="utf-8"))
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    regimes = pd.read_parquet(result.regime_posteriors_path)
    knn = pd.read_parquet(result.knn_predictions_path)
    meta = pd.read_parquet(result.meta_predictions_path)
    diagnostics = pd.read_csv(result.neighbor_diagnostics_path)
    replay_metrics_path = replay_hmm_knn_artifact(result.artifact_manifest_path)

    assert manifest["research_only"] is True
    assert manifest["feature_version"] == HMM_KNN_FEATURE_VERSION
    assert set(WT3D_FEATURE_COLUMNS).issubset(manifest["wt3d_feature_columns"])
    assert manifest["knn_settings"]["distance"] == "lorentzian"
    assert manifest["knn_settings"]["distance_metric"]["id"] == "lorentzian"
    assert manifest["knn_settings"]["available_distance_metrics"]["lorentzian"]["supports_backend"] == ["cpu", "auto", "cupy"]
    assert manifest["knn_settings"]["regime_match_mode"] == "same"
    assert manifest["knn_settings"]["distance_backend"] == "cpu"
    assert manifest["knn_settings"]["primary_k"] == 12
    assert manifest["feature_set_variant_id"] == "inline_feature_columns"
    assert isinstance(manifest["feature_set_variant_sha256"], str)
    assert manifest["feature_count"] == len(manifest["feature_columns"])
    assert metrics["feature_set_variant"]["feature_set_variant_sha256"] == manifest["feature_set_variant_sha256"]
    assert manifest["dependencies"]["knn_distance_backend_requested"] == "cpu"
    assert manifest["dependencies"]["knn_distance_backend"] == "cpu"
    assert manifest["dependencies"]["cupy_available"] in {True, False}
    assert metrics["research_only"] is True
    assert metrics["promotion_ready"] is False
    assert metrics["knn_sweep"]["distance_backend_requested"] == "cpu"
    assert metrics["knn_sweep"]["distance_backend"] == "cpu"
    assert metrics["knn_sweep"]["primary_k"] == 12
    assert {
        (result["k"], result["weighting"])
        for result in metrics["knn_sweep"]["results"]
    } == {(8, "inverse_distance"), (8, "softmax"), (12, "inverse_distance"), (12, "softmax")}
    assert replay_metrics_path == result.metrics_path
    posterior_columns = {f"regime_p_{index}" for index in range(3)}
    assert posterior_columns.issubset(regimes.columns)
    assert {
        "top_regime",
        "top_regime_label",
        "max_regime_probability",
        "posterior_entropy",
        "recent_regime_flip",
        "regime_no_trade",
        "regime_model_backend",
        "walk_forward_split",
        "source_row_index",
        "hmm_fit_end_row",
    }.issubset(regimes.columns)
    np.testing.assert_allclose(regimes[list(sorted(posterior_columns))].sum(axis=1).to_numpy(), np.ones(len(regimes)))
    assert set(KNN_OUTPUT_COLUMNS).issubset(knn.columns)
    assert {"meta_probability", "accepted_by_meta", "meta_model_backend"}.issubset(meta.columns)
    assert set(LABEL_OUTCOME_COLUMNS).issubset(meta.columns)
    assert manifest["label_version"] == "triple_barrier_live_parity_v1"
    assert manifest["label_horizons"] == ["6h", "24h", "72h", "7d"]
    assert manifest["primary_label_horizon"] == "24h"
    assert set(manifest["label_outcome_fields"]) == set(LABEL_OUTCOME_COLUMNS)
    assert not set(LABEL_OUTCOME_COLUMNS).intersection(manifest["feature_columns"])
    assert {
        "k",
        "weighting",
        "is_primary",
        "same_regime_only",
        "regime_match_mode",
        "candidate_count_before_regime_filter",
        "candidate_count_after_regime_filter",
        "selected_neighbor_count",
        "fallback_used",
        "fallback_reason",
        "knn_skip_reason",
        "source_row_index",
        "query_regime",
        "query_regime_label",
        "neighbor_rank",
        "neighbor_source_index",
        "neighbor_distance",
        "neighbor_distance_quality",
        "neighbor_weight",
        "neighbor_label_accept",
        "neighbor_label_pnl_multiple",
        "neighbor_regime",
    }.issubset(diagnostics.columns)
    populated_diagnostics = diagnostics.dropna(subset=["neighbor_regime"])
    assert not populated_diagnostics.empty
    assert (populated_diagnostics["neighbor_distance_quality"].astype(float).between(0.0, 1.0)).all()
    assert (populated_diagnostics["neighbor_source_index"].astype(int) <= populated_diagnostics["source_row_index"].astype(int)).all()
    assert (populated_diagnostics["neighbor_regime"].astype(int) == populated_diagnostics["query_regime"].astype(int)).all()
    assert (populated_diagnostics["candidate_count_before_regime_filter"].astype(int) >= populated_diagnostics["candidate_count_after_regime_filter"].astype(int)).all()
    assert (populated_diagnostics["selected_neighbor_count"].astype(int) > 0).all()
    assert set(populated_diagnostics["k"].astype(int)).issubset({8, 12})
    assert set(populated_diagnostics["weighting"].astype(str)) == {"inverse_distance", "softmax"}
    assert set(WT3D_FEATURE_COLUMNS).issubset(meta.columns)
    assert set(meta["hmm_knn_feature_version"]) == {HMM_KNN_FEATURE_VERSION}
    assert result.neighbor_diagnostics_path.exists()
    assert (regimes["hmm_fit_end_row"] < regimes["source_row_index"]).all()
    assert manifest["dependencies"]["meta_backend"]
    assert "meta_validation" in manifest
    assert metrics["evaluation_basis"]["pnl_source"] == "realized_label_return_after_fee_slippage_funding"
    assert {"hmm_regime_lorentzian_knn", "hmm_knn_meta_model"} == set(metrics["comparison"])
    assert metrics["comparison"]["hmm_regime_lorentzian_knn"]["pnl_source"] == "realized_label_return_after_fee_slippage_funding"
    assert metrics["comparison"]["hmm_knn_meta_model"]["pnl_source"] == "realized_label_return_after_fee_slippage_funding"
    assert "meta_validation" in metrics
    assert "research_only_not_live_promotable" in metrics["promotion_failures"]
    assert "neighbor_pool_diagnostics_by_regime" in metrics["artifact_diagnostics"]
    assert "feature_variant_summary" in metrics["artifact_diagnostics"]


def test_hmm_knn_research_runs_without_wt3d_and_with_euclidean_distance(tmp_path) -> None:
    config_path = _write_modified_test_config(
        tmp_path,
        hmm__backend="deterministic_rule_baseline",
        knn__distance="euclidean_robust_z",
        knn__feature_pack="full_context_no_wt3d",
        knn__primary_k=8,
        knn__k_values=[8],
        knn__neighbor_weighting=["inverse_distance"],
        knn__primary_weighting="inverse_distance",
    )
    dataset_path = tmp_path / "dataset.parquet"
    _synthetic_dataset().to_parquet(dataset_path, index=False)

    result = run_hmm_knn_research(config_path=config_path, dataset_path=dataset_path, output_dir=tmp_path)
    manifest = json.loads(result.artifact_manifest_path.read_text(encoding="utf-8"))
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))

    assert manifest["research_only"] is True
    assert manifest["feature_pack"] == "full_context_no_wt3d"
    assert manifest["feature_set_variant_id"] == "full_context_no_wt3d"
    assert manifest["feature_set_source"] == "registered_feature_pack"
    assert manifest["knn_settings"]["distance"] == "euclidean_robust_z"
    assert manifest["knn_settings"]["distance_metric"]["id"] == "euclidean_robust_z"
    assert "euclidean_robust_z" in manifest["knn_settings"]["available_distances"]
    assert not any(column.startswith("wt3d_") for column in manifest["feature_columns"])
    assert manifest["dependencies"]["hmm_backend"] == ["deterministic_rule_baseline"]
    assert manifest["artifact_diagnostics"]["neighbor_distance_quality_distribution"]["p50"] is not None
    assert "no_trade_reason_breakdown" in manifest["artifact_diagnostics"]
    assert manifest["stage6_baseline_benchmark"]["research_only"] is True
    assert {"trend_following_v1", "baseline_no_trade"} == set(manifest["stage6_baseline_benchmark"]["strategies"])
    assert metrics["stage6_baseline_benchmark"]["observe_only"] is True


def test_meta_model_records_random_forest_fallback_when_xgboost_is_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(hmm_knn, "XGBClassifier", None)
    monkeypatch.setattr(hmm_knn, "_xgboost", None)
    config_path = _write_test_config(tmp_path)
    dataset_path = tmp_path / "dataset.parquet"
    _synthetic_dataset().to_parquet(dataset_path, index=False)

    result = hmm_knn.run_hmm_knn_research(config_path=config_path, dataset_path=dataset_path, output_dir=tmp_path)
    manifest = json.loads(result.artifact_manifest_path.read_text(encoding="utf-8"))
    meta = pd.read_parquet(result.meta_predictions_path)

    assert manifest["dependencies"]["xgboost_available"] is False
    assert manifest["dependencies"]["xgboost_cuda_available"] is False
    assert manifest["dependencies"]["xgboost_cuda_detection"] == "xgboost_unavailable"
    assert manifest["dependencies"]["meta_backend"] == ["random_forest_fallback"]
    assert set(meta["meta_model_backend"]) == {"random_forest_fallback"}
    assert manifest["research_only"] is True


def test_xgboost_cuda_dependency_report_reads_build_info(monkeypatch) -> None:
    class FakeXGBClassifier:
        pass

    class FakeXGBoostModule:
        @staticmethod
        def build_info() -> dict[str, object]:
            return {
                "USE_CUDA": True,
                "CUDA_VERSION": "12.4",
                "USE_NCCL": False,
                "UNRELATED_FLAG": True,
            }

    monkeypatch.setattr(hmm_knn, "XGBClassifier", FakeXGBClassifier)
    monkeypatch.setattr(hmm_knn, "_xgboost", FakeXGBoostModule)

    report = _xgboost_cuda_dependency_report()

    assert report["xgboost_cuda_available"] is True
    assert report["xgboost_cuda_detection"] == "build_info"
    assert report["xgboost_cuda_build_info"] == {
        "USE_CUDA": True,
        "CUDA_VERSION": "12.4",
        "USE_NCCL": False,
    }


def test_xgboost_auto_device_uses_cuda_when_build_reports_support(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeXGBClassifier:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def fit(self, frame, labels) -> "FakeXGBClassifier":
            captured["fit_shape"] = frame.shape
            captured["label_count"] = len(labels)
            return self

    class FakeXGBoostModule:
        @staticmethod
        def build_info() -> dict[str, object]:
            return {"USE_CUDA": True, "CUDA_VERSION": "12.8"}

    monkeypatch.setattr(hmm_knn, "XGBClassifier", FakeXGBClassifier)
    monkeypatch.setattr(hmm_knn, "_xgboost", FakeXGBoostModule)
    plan = load_hmm_knn_plan(_write_modified_test_config(tmp_path, meta_model__device="auto"))

    _, backend = _fit_meta_model(
        pd.DataFrame({"feature": [0.0, 1.0, 2.0, 3.0]}),
        ["feature"],
        pd.Series([0, 1, 0, 1]),
        plan,
    )

    assert backend == "xgboost_cuda"
    assert captured["device"] == "cuda"
    assert captured["tree_method"] == "hist"
    assert captured["fit_shape"] == (4, 1)
    assert captured["label_count"] == 4


def test_xgboost_cuda_dependency_report_handles_non_cuda_build_info(monkeypatch) -> None:
    class FakeXGBClassifier:
        pass

    class FakeXGBoostModule:
        @staticmethod
        def build_info() -> dict[str, object]:
            return {
                "USE_CUDA": "OFF",
                "USE_NCCL": "OFF",
                "UNRELATED_FLAG": True,
            }

    monkeypatch.setattr(hmm_knn, "XGBClassifier", FakeXGBClassifier)
    monkeypatch.setattr(hmm_knn, "_xgboost", FakeXGBoostModule)

    report = _xgboost_cuda_dependency_report()

    assert report["xgboost_cuda_available"] is False
    assert report["xgboost_cuda_detection"] == "build_info"
    assert report["xgboost_cuda_build_info"] == {
        "USE_CUDA": "OFF",
        "USE_NCCL": "OFF",
    }


def test_hmm_knn_prepare_dataset_preserves_real_label_outcome_fields(tmp_path) -> None:
    plan = load_hmm_knn_plan(_write_test_config(tmp_path))
    dataset_path = tmp_path / "dataset.parquet"
    frame = _synthetic_dataset(60)
    frame["gross_return"] = 0.0123
    frame["fees_bps"] = 7.0
    frame["slippage_bps"] = 3.0
    frame["funding_paid_or_received"] = -0.0002
    frame["time_in_trade"] = 1.5
    frame["max_adverse_excursion"] = 0.4
    frame["max_favorable_excursion"] = 1.1
    frame["barrier_hit_type"] = frame["label_exit_reason"]
    frame.to_parquet(dataset_path, index=False)

    prepared = _prepare_dataset(dataset_path, plan)

    assert prepared["gross_return"].iloc[0] == 0.0123
    assert prepared["fees_bps"].iloc[0] == 7.0
    assert prepared["slippage_bps"].iloc[0] == 3.0
    assert prepared["funding_paid_or_received"].iloc[0] == -0.0002
    assert prepared["time_in_trade"].iloc[0] == 1.5
    assert prepared["max_adverse_excursion"].iloc[0] == 0.4
    assert prepared["max_favorable_excursion"].iloc[0] == 1.1
    assert prepared["realized_net_return_after_costs"].iloc[0] == pytest.approx(0.0123 - 0.001 + -0.0002)


def test_hmm_knn_walk_forward_uses_label_exit_time_for_purge(tmp_path) -> None:
    plan = load_hmm_knn_plan(_write_test_config(tmp_path))
    frame = _synthetic_dataset(80)
    frame["label_exit_time_ms"] = frame["signal_bar_time_ms"] + (12 * 900_000)

    splits = _walk_forward_frames(frame, plan)

    assert splits
    train_frame, test_frame = splits[0]
    assert train_frame["label_exit_time_ms"].max() + (plan.evaluation.purge_embargo_bars * 900_000) < test_frame["signal_bar_time_ms"].min()


def test_backtest_metrics_use_realized_costed_returns_and_flag_split_concentration(tmp_path) -> None:
    plan = load_hmm_knn_plan(_write_test_config(tmp_path))
    frame = pd.DataFrame(
        {
            "label_accept": [1, 1, 1, 1, 1, 0],
            "label_pnl_multiple": [1.0, 1.0, 1.0, 1.0, 1.0, -0.1],
            "gross_return": [1.0, 1.0, 1.0, 1.0, 1.0, -0.1],
            "funding_paid_or_received": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "expected_net_return_after_costs": [99.0, 99.0, 99.0, 99.0, 99.0, 99.0],
            "accepted_by_knn": [True, True, True, True, True, True],
            "accepted_by_meta": [True, True, True, True, True, True],
            "regime_no_trade": [False, False, False, False, False, False],
            "top_regime_label": ["bull_trend", "bull_trend", "bull_trend", "bull_trend", "bear_trend", "bear_trend"],
            "direction": ["long", "short", "long", "short", "long", "short"],
        }
    )
    split_metrics = [
        _split_metrics(frame.iloc[:5].copy(), 0, plan, meta_training_summary={"meta_training_rows": 5}),
        _split_metrics(frame.iloc[5:].copy(), 1, plan, meta_training_summary={"meta_training_rows": 5}),
    ]

    metrics = _overall_metrics(frame, split_metrics, plan, knn_sweep=pd.DataFrame())
    meta_metrics = metrics["comparison"]["hmm_knn_meta_model"]

    assert meta_metrics["expectancy_after_cost"] == pytest.approx(((5.0 - 0.1) / 6) - 0.001)
    assert meta_metrics["expected_value_mean"] == 99.0
    assert metrics["max_single_split_pnl_share_by_strategy"]["hmm_knn_meta_model"] > 0.6
    assert "meta_single_split_dominates_pnl" in metrics["promotion_failures"]
    assert "knn_single_split_dominates_pnl" in metrics["promotion_failures"]
    assert metrics["promotion_ready"] is False
    assert metrics["research_only"] is True


def test_hmm_knn_monitoring_report_is_research_only_and_observe_only(tmp_path) -> None:
    config_path = _write_test_config(tmp_path)
    dataset_path = tmp_path / "dataset.parquet"
    _synthetic_dataset().to_parquet(dataset_path, index=False)

    result = run_hmm_knn_research(config_path=config_path, dataset_path=dataset_path, output_dir=tmp_path)
    report_path = monitor_hmm_knn_artifact(result.artifact_manifest_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_path == result.output_dir / "monitoring_report.json"
    assert report["research_only"] is True
    assert report["promotion_ready"] is False
    assert report["observe_only"] is True
    assert report["intended_use"] == "research_observe_only"
    assert report["live_signal_input"] is False
    assert report["position_sizing_input"] is False
    assert report["research_boundary"]["passed"] is True
    assert report["live_vs_replay_mismatch"] == "not_available"
    assert report["artifact_identity"]["plan_version"] == "test-hmm-knn"
    assert report["feature_outages"]["configured_feature_count"] > 0
    assert "posterior_entropy_p95" in report["entropy_no_trade"]
    assert report["regime_distribution_drift"]["available"] is True
    assert "neighbor_distance_quality_p05" in report["neighbor_quality"]
    assert report["calibration_decay"]["available"] is True
    assert all(alert["observe_only"] is True for alert in report["alerts"])


def test_hmm_knn_cli_research_then_monitor_writes_expected_temp_artifacts(tmp_path) -> None:
    config_path = _write_test_config(tmp_path)
    dataset_path = tmp_path / "dataset.parquet"
    output_dir = tmp_path / "research_output"
    _synthetic_dataset().to_parquet(dataset_path, index=False)
    env = {**os.environ, "PYTHONPATH": str(Path("src").resolve())}

    research = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.main",
            "research-hmm-knn",
            "--config",
            str(config_path),
            "--dataset",
            str(dataset_path),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    research_payload = json.loads(research.stdout)
    artifact_manifest_path = Path(research_payload["artifact_manifest_path"])
    expected_paths = [
        Path(research_payload["output_dir"]),
        artifact_manifest_path,
        Path(research_payload["metrics_path"]),
        Path(research_payload["regime_posteriors_path"]),
        Path(research_payload["knn_predictions_path"]),
        Path(research_payload["meta_predictions_path"]),
        Path(research_payload["neighbor_diagnostics_path"]),
    ]

    for path in expected_paths:
        assert path.exists()
        assert path.resolve().is_relative_to(tmp_path.resolve())

    manifest = json.loads(artifact_manifest_path.read_text(encoding="utf-8"))
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["intended_use"] == "research_observe_only"
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["artifact_manifest_version"] == "v2-hmm-knn-artifact-manifest-1"
    assert manifest["symbol"] == "BTCUSDT"
    assert manifest["asset_scope"] == ["BTCUSDT"]
    assert manifest["dataset_path"] == str(dataset_path)
    assert set(manifest["feature_columns"]) == set(load_hmm_knn_plan(config_path).knn.feature_columns)

    monitor = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.main",
            "monitor-hmm-knn",
            "--manifest",
            str(artifact_manifest_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    monitor_payload = json.loads(monitor.stdout)
    monitoring_report_path = Path(monitor_payload["monitoring_report_path"])
    assert monitoring_report_path == artifact_manifest_path.parent / "monitoring_report.json"
    assert monitoring_report_path.exists()
    assert monitoring_report_path.resolve().is_relative_to(tmp_path.resolve())

    monitoring_report = json.loads(monitoring_report_path.read_text(encoding="utf-8"))
    assert monitoring_report["research_only"] is True
    assert monitoring_report["observe_only"] is True
    assert monitoring_report["promotion_ready"] is False
    assert monitoring_report["research_boundary"]["passed"] is True


def test_hmm_knn_monitoring_fails_clearly_when_required_artifact_is_missing(tmp_path) -> None:
    config_path = _write_test_config(tmp_path)
    dataset_path = tmp_path / "dataset.parquet"
    _synthetic_dataset().to_parquet(dataset_path, index=False)
    result = run_hmm_knn_research(config_path=config_path, dataset_path=dataset_path, output_dir=tmp_path)
    result.neighbor_diagnostics_path.unlink()

    with pytest.raises(FileNotFoundError, match="missing required artifact files"):
        monitor_hmm_knn_artifact(result.artifact_manifest_path)


def test_tiny_or_one_class_meta_research_reports_explicit_failures(tmp_path) -> None:
    config_path = _write_modified_test_config(
        tmp_path,
        evaluation__walk_forward_splits=1,
        evaluation__min_training_rows=24,
        evaluation__purge_embargo_bars=1,
        acceptance__min_trade_count=2,
    )
    dataset_path = tmp_path / "one_class_dataset.parquet"
    frame = _synthetic_dataset(70)
    frame["label_accept"] = 1
    frame["label_pnl_multiple"] = 1.2
    frame.to_parquet(dataset_path, index=False)

    result = run_hmm_knn_research(config_path=config_path, dataset_path=dataset_path, output_dir=tmp_path)
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))

    assert metrics["promotion_ready"] is False
    assert metrics["research_only"] is True
    assert metrics["meta_validation"]["failure_reasons"]
    assert "insufficient_evaluated_splits" in metrics["promotion_failures"]
    assert "insufficient_meta_training_class_diversity" in metrics["promotion_failures"]
    assert "constant_meta_model_backend" in metrics["promotion_failures"]


def test_hmm_knn_experiment_runner_writes_manifest_summary_and_monitoring(tmp_path) -> None:
    base_config_path = _write_test_config(tmp_path)
    dataset_path = tmp_path / "dataset.parquet"
    output_dir = tmp_path / "experiments"
    _synthetic_dataset().to_parquet(dataset_path, index=False)
    spec_path = tmp_path / "experiment_spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "name": "fixture matrix",
                "base_config_path": str(base_config_path),
                "dataset_path": str(dataset_path),
                "experiments": [
                    {
                        "name": "small k softmax",
                        "slug": "small-k-softmax",
                        "owning_agent": "KNN",
                        "run_order": 1,
                        "config_data_change": "small K softmax diagnostic",
                        "expected_metric_movement": "more candidates with better distance quality",
                        "risk": "can add losing candidates",
                        "requires_new_data": False,
                        "can_run_on_current_artifacts": True,
                        "mutations": {
                            "knn.primary_k": 8,
                            "knn.k_values": [8, 12],
                            "knn.primary_weighting": "softmax",
                            "knn.neighbor_weighting": ["softmax"],
                        },
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_hmm_knn_experiment_matrix(spec_path=spec_path, output_dir=output_dir)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    rows = result.summary_path.read_text(encoding="utf-8").splitlines()

    assert manifest["experiment_manifest_version"] == "v2-hmm-knn-experiment-manifest-1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["intended_use"] == "research_observe_only"
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["research_boundary"]["passed"] is True
    assert manifest["overall_status"] == "passed"
    assert manifest["dataset_path"] == str(dataset_path)
    assert len(manifest["experiments"]) == 1
    experiment = manifest["experiments"][0]
    assert experiment["slug"] == "small-k-softmax"
    assert experiment["status"] == "passed"
    assert experiment["cache_status"] == "miss"
    assert experiment["cache_hit"] is False
    assert isinstance(experiment["runtime_seconds"], float)
    assert Path(experiment["artifact_manifest_path"]).exists()
    assert experiment["artifact_manifest"] == experiment["artifact_manifest_path"]
    assert Path(experiment["monitoring_report_path"]).exists()
    assert experiment["metrics_digest"]["promotion_ready"] is False
    assert experiment["research_boundary"]["passed"] is True
    assert experiment["promotion_failures"] == experiment["metrics_digest"]["promotion_failures"]
    assert "knn_trade_count" in experiment["metrics_digest"]
    assert manifest["runtime_seconds"] >= 0.0
    assert manifest["max_workers"] == 1
    assert manifest["effective_workers"] == 1
    assert manifest["promotion_failure_counts"]
    assert rows[0].startswith("run_order,slug,owning_agent,status,cache_status,cache_hit,runtime_seconds")
    assert "small-k-softmax" in rows[1]


def test_hmm_knn_experiment_runner_reuses_complete_cached_artifact(tmp_path) -> None:
    base_config_path = _write_test_config(tmp_path)
    dataset_path = tmp_path / "dataset.parquet"
    output_dir = tmp_path / "experiments"
    _synthetic_dataset().to_parquet(dataset_path, index=False)
    spec_path = tmp_path / "experiment_spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "base_config_path": str(base_config_path),
                "dataset_path": str(dataset_path),
                "experiments": [
                    {
                        "name": "cooldown zero",
                        "slug": "cooldown-zero",
                        "owning_agent": "Regime",
                        "run_order": 1,
                        "mutations": {"hmm.flip_cooldown_bars": 0},
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    first = run_hmm_knn_experiment_matrix(spec_path=spec_path, output_dir=output_dir, write_monitoring=False)
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    second = run_hmm_knn_experiment_matrix(spec_path=spec_path, output_dir=output_dir, write_monitoring=False)
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))
    first_experiment = first_manifest["experiments"][0]
    second_experiment = second_manifest["experiments"][0]

    assert first_experiment["cache_status"] == "miss"
    assert second_experiment["cache_status"] == "hit"
    assert first_experiment["cache_hit"] is False
    assert second_experiment["cache_hit"] is True
    assert second_experiment["artifact_manifest_path"] == first_experiment["artifact_manifest_path"]
    assert second_experiment["cache_key"] == first_experiment["cache_key"]


def test_hmm_knn_experiment_runner_parallel_workers_preserve_order_and_cache_keys(tmp_path) -> None:
    base_config_path = _write_test_config(tmp_path)
    fixture_result = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "deterministic_sweeps", row_count=120)
    dataset_path = fixture_result.parquet_path
    output_dir = tmp_path / "experiments"
    spec_path = tmp_path / "experiment_spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "base_config_path": str(base_config_path),
                "dataset_path": str(dataset_path),
                "experiments": [
                    {
                        "name": "second by input first by order",
                        "slug": "order-one",
                        "owning_agent": "Backtest",
                        "run_order": 2,
                        "mutations": {"hmm.flip_cooldown_bars": 0},
                    },
                    {
                        "name": "first by order",
                        "slug": "order-zero",
                        "owning_agent": "Backtest",
                        "run_order": 1,
                        "mutations": {"hmm.posterior_threshold": 0.40},
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    first = run_hmm_knn_experiment_matrix(
        spec_path=spec_path,
        output_dir=output_dir,
        write_monitoring=False,
        max_workers=2,
    )
    first_manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    first_rows = list(csv.DictReader(first.summary_path.open(encoding="utf-8")))
    second = run_hmm_knn_experiment_matrix(
        spec_path=spec_path,
        output_dir=output_dir,
        write_monitoring=False,
        max_workers=2,
    )
    second_manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))

    assert first_manifest["max_workers"] == 2
    assert first_manifest["effective_workers"] == 2
    assert [record["slug"] for record in first_manifest["experiments"]] == ["order-zero", "order-one"]
    assert [row["slug"] for row in first_rows] == ["order-zero", "order-one"]
    assert all(record["runtime_seconds"] >= 0.0 for record in first_manifest["experiments"])
    assert all(record["artifact_manifest_path"] for record in first_manifest["experiments"])
    assert first_manifest["promotion_failure_counts"]
    assert [record["cache_status"] for record in first_manifest["experiments"]] == ["miss", "miss"]
    assert [record["cache_status"] for record in second_manifest["experiments"]] == ["hit", "hit"]
    assert [record["cache_key"] for record in second_manifest["experiments"]] == [
        record["cache_key"] for record in first_manifest["experiments"]
    ]
    assert [record["artifact_manifest_path"] for record in second_manifest["experiments"]] == [
        record["artifact_manifest_path"] for record in first_manifest["experiments"]
    ]


def test_hmm_knn_experiment_runner_accepts_utf8_sig_specs(tmp_path) -> None:
    base_config_path = _write_test_config(tmp_path)
    dataset_path = tmp_path / "dataset.parquet"
    output_dir = tmp_path / "experiments"
    _synthetic_dataset().to_parquet(dataset_path, index=False)
    spec_path = tmp_path / "experiment_spec_bom.json"
    spec_payload = json.dumps(
        {
            "base_config_path": str(base_config_path),
            "dataset_path": str(dataset_path),
            "experiments": [
                {
                    "name": "bom spec",
                    "slug": "bom-spec",
                    "owning_agent": "Backtest",
                    "run_order": 1,
                    "mutations": {"hmm.flip_cooldown_bars": 0},
                }
            ],
        },
        indent=2,
    )
    spec_path.write_text("\ufeff" + spec_payload, encoding="utf-8")

    result = run_hmm_knn_experiment_matrix(spec_path=spec_path, output_dir=output_dir, write_monitoring=False)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["overall_status"] == "passed"
    assert manifest["experiments"][0]["slug"] == "bom-spec"
