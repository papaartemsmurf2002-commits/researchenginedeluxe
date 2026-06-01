from __future__ import annotations

from tradingbotsuite.research_discovery.artifact_keys import (
    effective_trial_key,
    effective_trial_key_payload,
    entry_event_signature_hash,
    prediction_signature_hash,
)


def test_effective_trial_key_drops_no_regime_noop_dimensions() -> None:
    base = {
        "candidate_family": "regime_knn_entry_discovery",
        "feature_column_set_id": "price_trend_vol",
        "regime_mode": "none",
        "label_horizon": "1h",
        "distance_metric": "euclidean",
        "k": 3,
        "min_neighbor_count": 2,
        "probability_threshold": 0.55,
        "expected_value_threshold": 0.0,
        "min_neighbor_agreement": 0.55,
        "min_distance_quality": 0.0,
        "vote_margin_threshold": 0.0,
        "hmm_state_count": 3,
        "hmm_posterior_threshold": 0.55,
        "hmm_entropy_threshold": 0.78,
        "regime_model_backend": "none",
    }
    changed_noop = {
        **base,
        "hmm_state_count": 5,
        "hmm_posterior_threshold": 0.75,
        "hmm_entropy_threshold": 0.90,
        "regime_model_backend": "sklearn.mixture.GaussianMixture",
    }

    assert effective_trial_key(base) == effective_trial_key(changed_noop)
    payload = effective_trial_key_payload(base)
    assert "hmm_state_count" in payload["inactive_dimensions_dropped"]
    assert "hmm_posterior_threshold" in payload["inactive_dimensions_dropped"]
    assert "regime_model_backend" in payload["inactive_dimensions_dropped"]
    assert "hmm_state_count" not in payload
    assert "regime_model_backend" not in payload


def test_effective_trial_key_keeps_regime_dimensions_when_regime_active() -> None:
    base = {
        "candidate_family": "regime_knn_entry_discovery",
        "feature_column_set_id": "price_trend_vol",
        "regime_mode": "gmm_gate_only",
        "label_horizon": "1h",
        "distance_metric": "euclidean",
        "k": 3,
        "min_neighbor_count": 2,
        "probability_threshold": 0.55,
        "expected_value_threshold": 0.0,
        "min_neighbor_agreement": 0.55,
        "min_distance_quality": 0.0,
        "vote_margin_threshold": 0.0,
        "hmm_state_count": 3,
        "hmm_posterior_threshold": 0.55,
        "hmm_entropy_threshold": 0.78,
        "regime_detector_type": "gmm",
        "regime_model_backend": "sklearn.mixture.GaussianMixture",
        "regime_gate_enabled": True,
    }
    changed_regime = {**base, "hmm_state_count": 5}
    changed_backend = {**base, "regime_model_backend": "unexpected"}

    assert effective_trial_key(base) != effective_trial_key(changed_regime)
    assert effective_trial_key(base) != effective_trial_key(changed_backend)
    assert effective_trial_key_payload(base)["hmm_state_count"] == 3
    assert effective_trial_key_payload(base)["regime_model_backend"] == "sklearn.mixture.GaussianMixture"


def test_prediction_and_entry_signatures_split_on_event_outcomes() -> None:
    base = {
        "feature_column_set_id": "price_trend_vol",
        "regime_mode": "none",
        "label_horizon": "1h",
        "distance_metric": "euclidean",
        "k": 3,
        "min_neighbor_count": 2,
        "accepted_prediction_count": 4,
        "evaluated_prediction_count": 10,
        "accepted_bar_count": 4,
        "signal_rate": 0.2,
        "long_independent_event_count": 2,
        "short_independent_event_count": 1,
        "independent_event_count": 3,
        "suppressed_overlap_count": 1,
        "overlap_ratio": 0.25,
        "side_collapse_ratio": 0.67,
        "event_spacing_bars": 4,
    }
    changed = {**base, "accepted_prediction_count": 5, "accepted_bar_count": 5}

    assert prediction_signature_hash(base) != prediction_signature_hash(changed)
    assert entry_event_signature_hash(base) != entry_event_signature_hash(changed)
