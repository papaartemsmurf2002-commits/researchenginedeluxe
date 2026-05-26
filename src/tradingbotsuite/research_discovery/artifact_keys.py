from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping

import pandas as pd


ARTIFACT_KEY_VERSION = "r105-artifact-keys-v1"
LEDGER_SIGNATURE_HASH_SCOPE = "ledger_summary_no_per_bar_prediction_artifacts"

NO_REGIME_INACTIVE_DIMENSIONS = (
    "hmm_state_count",
    "hmm_posterior_threshold",
    "hmm_entropy_threshold",
    "regime_detector_type",
    "regime_gate_enabled",
    "same_regime_neighbor_pool_enabled",
    "same_regime_only",
    "true_hmm_backend_used",
)

BASE_EFFECTIVE_TRIAL_DIMENSIONS = (
    "candidate_family",
    "feature_column_set_id",
    "regime_mode",
    "label_horizon",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "probability_threshold",
    "expected_value_threshold",
    "min_neighbor_agreement",
    "min_distance_quality",
    "vote_margin_threshold",
)

REGIME_EFFECTIVE_TRIAL_DIMENSIONS = (
    "hmm_state_count",
    "hmm_posterior_threshold",
    "hmm_entropy_threshold",
    "regime_detector_type",
    "regime_gate_enabled",
    "same_regime_neighbor_pool_enabled",
    "true_hmm_backend_used",
)

PREDICTION_SIGNATURE_FIELDS = (
    "feature_column_set_id",
    "regime_mode",
    "label_horizon",
    "distance_metric",
    "k",
    "min_neighbor_count",
    "accepted_prediction_count",
    "evaluated_prediction_count",
    "accepted_bar_count",
    "signal_rate",
    "long_independent_event_count",
    "short_independent_event_count",
    "independent_event_count",
    "suppressed_overlap_count",
    "overlap_ratio",
    "side_collapse_ratio",
)

ENTRY_EVENT_SIGNATURE_FIELDS = (
    "feature_column_set_id",
    "regime_mode",
    "label_horizon",
    "accepted_bar_count",
    "independent_event_count",
    "long_independent_event_count",
    "short_independent_event_count",
    "event_spacing_bars",
    "signal_rate",
    "overlap_ratio",
    "side_collapse_ratio",
)

EXIT_RESULT_SIGNATURE_FIELDS = (
    "exit_policy_id",
    "exit_policy_params_json",
    "exit_reason_distribution_json",
    "trade_count",
    "realized_expectancy",
    "independent_event_expectancy",
    "final_score",
)


def stable_payload_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _json_safe(payload),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def effective_trial_key_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    regime_mode = str(record.get("regime_mode") or "").strip().lower()
    fields = list(BASE_EFFECTIVE_TRIAL_DIMENSIONS)
    if regime_mode != "none":
        fields.extend(REGIME_EFFECTIVE_TRIAL_DIMENSIONS)
    payload = {
        "artifact_key_version": ARTIFACT_KEY_VERSION,
        "key_scope": "effective_trial_parameters",
        "inactive_dimensions_dropped": list(inactive_trial_dimensions(record)),
    }
    payload.update({field: _json_safe(record.get(field)) for field in fields if field in record})
    return payload


def effective_trial_key(record: Mapping[str, Any]) -> str:
    return stable_payload_sha256(effective_trial_key_payload(record))


def inactive_trial_dimensions(record: Mapping[str, Any]) -> tuple[str, ...]:
    regime_mode = str(record.get("regime_mode") or "").strip().lower()
    if regime_mode == "none":
        return NO_REGIME_INACTIVE_DIMENSIONS
    return ()


def prediction_signature_hash(record: Mapping[str, Any]) -> str:
    return _field_signature_hash(
        record,
        key_scope="prediction_signature",
        hash_scope=LEDGER_SIGNATURE_HASH_SCOPE,
        fields=PREDICTION_SIGNATURE_FIELDS,
    )


def entry_event_signature_hash(record: Mapping[str, Any]) -> str:
    return _field_signature_hash(
        record,
        key_scope="entry_event_signature",
        hash_scope=LEDGER_SIGNATURE_HASH_SCOPE,
        fields=ENTRY_EVENT_SIGNATURE_FIELDS,
    )


def exit_result_signature_hash(record: Mapping[str, Any]) -> str:
    return _field_signature_hash(
        record,
        key_scope="exit_result_signature",
        hash_scope=LEDGER_SIGNATURE_HASH_SCOPE,
        fields=EXIT_RESULT_SIGNATURE_FIELDS,
    )


def _field_signature_hash(
    record: Mapping[str, Any],
    *,
    key_scope: str,
    hash_scope: str,
    fields: tuple[str, ...],
) -> str:
    payload = {
        "artifact_key_version": ARTIFACT_KEY_VERSION,
        "key_scope": key_scope,
        "hash_scope": hash_scope,
        "fields": {field: _json_safe(record.get(field)) for field in fields if field in record},
    }
    return stable_payload_sha256(payload)


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if pd.isna(value) or value in {float("inf"), float("-inf")}:
            return None
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(inner) for key, inner in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return str(value)
