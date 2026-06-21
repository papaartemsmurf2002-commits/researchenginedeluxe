from __future__ import annotations

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.security.hygiene import (
    CommandClass,
    CommandClassification,
    REDACTED_VALUE,
    SecretPolicy,
    TrustedArtifactRef,
    redact_mapping,
    redact_text,
    validate_trusted_artifact,
)
from tradingbotsuite.v2.security.path_policy import resolve_within_root


def test_required_webhook_secret_fails_closed_when_missing() -> None:
    policy = SecretPolicy(required_secret_names=("operator_webhook_secret",))

    (result,) = policy.scan({})

    assert result.accepted is False
    assert result.present is False
    assert result.reasons == ("missing_required_secret",)


def test_default_and_weak_secret_values_are_rejected() -> None:
    policy = SecretPolicy(minimum_length=16)

    placeholder = policy.validate_secret("operator_webhook_secret", "changeme")
    repeated = policy.validate_secret("operator_webhook_secret", "aaaaaaaaaaaaaaaa")

    assert placeholder.accepted is False
    assert "secret_too_short" in placeholder.reasons
    assert "default_or_placeholder_secret" in placeholder.reasons
    assert repeated.accepted is False
    assert "low_entropy_secret" in repeated.reasons


def test_redaction_masks_secret_keys_and_sensitive_text() -> None:
    payload = {
        "webhook_secret": "super-secret-value",
        "message": (
            "token=redaction-test-token-value "
            "wallet 0x1111111111111111111111111111111111111111"
        ),
        "nested": {"api_key": "abc123"},
    }

    redacted = redact_mapping(payload)
    redacted_text = redact_text(
        "webhook_secret=webhook-secret-test-value password:open-sesame"
    )

    assert redacted["webhook_secret"] == REDACTED_VALUE
    assert redacted["nested"]["api_key"] == REDACTED_VALUE
    assert "redaction-test-token-value" not in redacted["message"]
    assert "0x1111111111111111111111111111111111111111" not in redacted["message"]
    assert "webhook-secret-test-value" not in redacted_text
    assert "open-sesame" not in redacted_text


def test_trusted_artifact_requires_root_containment_and_matching_hash(tmp_path) -> None:
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    artifact = trusted_root / "scorecard.json"
    artifact.write_text('{"research_only": true}\n', encoding="utf-8")
    expected_hash = file_sha256(artifact)

    accepted = validate_trusted_artifact(
        TrustedArtifactRef(
            artifact_path="scorecard.json",
            trusted_root=trusted_root,
            expected_sha256=expected_hash,
        )
    )
    mismatch = validate_trusted_artifact(
        TrustedArtifactRef(
            artifact_path=artifact,
            trusted_root=trusted_root,
            expected_sha256="0" * 64,
        )
    )
    outside = validate_trusted_artifact(
        TrustedArtifactRef(
            artifact_path="../trusted/scorecard.json",
            trusted_root=trusted_root / "nested",
            expected_sha256=expected_hash,
        )
    )

    assert accepted.accepted is True
    assert accepted.sha256 == expected_hash
    assert mismatch.accepted is False
    assert mismatch.reasons == ("artifact_hash_mismatch",)
    assert outside.accepted is False
    assert "artifact_path_outside_trusted_root" in outside.reasons


def test_pickle_like_artifacts_are_rejected_even_with_matching_hash(tmp_path) -> None:
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    artifact = trusted_root / "model.joblib"
    artifact.write_bytes(b"not deserialized")

    result = validate_trusted_artifact(
        TrustedArtifactRef(
            artifact_path=artifact,
            trusted_root=trusted_root,
            expected_sha256=file_sha256(artifact),
        )
    )

    assert result.accepted is False
    assert result.reasons == ("unsafe_pickle_like_artifact_extension",)
    assert result.sha256 is None


@pytest.mark.parametrize(
    "updates, reason",
    [
        ({"command_class": CommandClass.LIVE_FORBIDDEN}, "live_forbidden_command_class"),
        ({"research_only": False}, "research_only_false"),
        ({"touches_live_runtime": True}, "touches_live_runtime"),
        ({"places_orders": True}, "places_orders"),
        ({"emits_sizing": True}, "emits_sizing"),
        ({"mutates_runtime_mode": True}, "mutates_runtime_mode"),
        ({"emits_paper_or_live_signal": True}, "emits_paper_or_live_signal"),
        ({"promotion_implication": True}, "promotion_implication"),
    ],
)
def test_command_classification_rejects_live_order_sizing_runtime_flags(
    updates: dict[str, object],
    reason: str,
) -> None:
    payload = {"command_id": "v2-research-command", **updates}

    with pytest.raises(ValidationError, match=reason):
        CommandClassification(**payload)


def test_research_command_classification_and_path_policy_allow_safe_inputs(tmp_path) -> None:
    root = tmp_path / "archive"
    root.mkdir()

    classification = CommandClassification(
        command_id="v2-archive-snapshot",
        command_class=CommandClass.RESEARCH,
    )

    assert classification.research_only is True
    assert resolve_within_root(root, "raw/file.jsonl") == root.resolve() / "raw" / "file.jsonl"
    with pytest.raises(ValueError, match="escapes configured root"):
        resolve_within_root(root, "../escape.json")
