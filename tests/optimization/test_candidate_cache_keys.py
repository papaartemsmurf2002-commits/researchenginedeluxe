from __future__ import annotations

from tradingbotsuite.optimization import CandidateCache, CandidateConfig, CandidateResult


def test_candidate_cache_keys_are_deterministic_and_order_independent() -> None:
    cache = CandidateCache(
        dataset_hash="dataset-a",
        feature_hash="feature-a",
        engine_version="engine-a",
        validation_hash="validation-a",
    )
    left = CandidateConfig("trend_following_v1", {"b": 2, "a": 1})
    right = CandidateConfig("trend_following_v1", {"a": 1, "b": 2})

    assert cache.key_for(left) == cache.key_for(right)
    key = cache.put(CandidateResult(left, base_score=0.1))
    assert key == cache.key_for(right)
    assert cache.get(right) is not None
    payload = cache.to_payload()
    assert payload["hits"] == 1
    assert payload["misses"] == 0
    assert payload["writes"] == 1
    assert payload["hit_rate"] == 1.0


def test_candidate_cache_records_misses_without_changing_keys() -> None:
    cache = CandidateCache(
        dataset_hash="dataset-a",
        feature_hash="feature-a",
        engine_version="engine-a",
        validation_hash="validation-a",
    )
    config = CandidateConfig("trend_following_v1", {"threshold": 0.2})
    expected_key = cache.key_for(config)

    assert cache.get(config) is None
    assert cache.key_for(config) == expected_key
    payload = cache.to_payload()
    assert payload["hits"] == 0
    assert payload["misses"] == 1
    assert payload["writes"] == 0


def test_candidate_cache_key_changes_for_exit_policy_identity() -> None:
    fixed = CandidateConfig("trend_following_v1", {"threshold": 0.2})
    max_mae = CandidateConfig(
        "trend_following_v1",
        {"threshold": 0.2},
        exit_policy_id="max_mae_stop",
        exit_policy_params={"stop_return": 0.01},
    )
    tighter_mae = CandidateConfig(
        "trend_following_v1",
        {"threshold": 0.2},
        exit_policy_id="max_mae_stop",
        exit_policy_params={"stop_return": 0.02},
    )

    assert fixed.cache_key() != max_mae.cache_key()
    assert max_mae.cache_key() != tighter_mae.cache_key()
