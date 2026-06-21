# V2-AUDIT-ID: V2-AUD-SEC-003
# V2-CONTRACTS: docs/contracts/security_boundary_contract.md
# V2-BOUNDARY: research_only, no_live_imports, secret_fail_closed
# V2-OWNER: v2_security
"""Security hygiene helpers for v2 research surfaces."""

from __future__ import annotations

from enum import Enum
import hashlib
from pathlib import Path
import re
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.security.path_policy import resolve_within_root


REDACTED_VALUE = "<redacted>"
UNSAFE_ARTIFACT_EXTENSIONS = frozenset({".dill", ".joblib", ".pickle", ".pkl"})

_HEX_64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_DEFAULT_SECRET_RE = re.compile(
    r"^(?:change[_-]?me|default|dummy|example|not[_-]?set|password|placeholder|"
    r"secret|test|todo|token)(?:[_-]?\d+)?$",
    re.IGNORECASE,
)
_KEY_VALUE_SECRET_RE = re.compile(
    r"\b(secret|token|password|api[_-]?key|webhook[_-]?secret|credential)"
    r"\b(\s*[:=]\s*)([^\s,;]+)",
    re.IGNORECASE,
)
_PREFIXED_SECRET_RE = re.compile(
    r"\b(?:sk|pk|whsec|xox[abprs]?)[_-][A-Za-z0-9_-]{8,}\b"
)
_ACCOUNT_LIKE_RE = re.compile(r"\b0x[0-9a-fA-F]{40}\b")


class SecretScanResult(BaseModel):
    """Result of one fail-closed secret validation scan."""

    model_config = ConfigDict(frozen=True)

    secret_name: str
    required: bool = True
    present: bool
    accepted: bool
    reasons: tuple[str, ...] = Field(default_factory=tuple)
    redacted_preview: str | None = None


class SecretPolicy(BaseModel):
    """Fail-closed policy for webhook and credential-like secret values."""

    model_config = ConfigDict(frozen=True)

    policy_id: str = "v2-secret-policy-v1"
    required_secret_names: tuple[str, ...] = Field(default_factory=tuple)
    minimum_length: int = 16

    @field_validator("minimum_length")
    @classmethod
    def _minimum_length_is_meaningful(cls, value: int) -> int:
        if value < 8:
            raise ValueError("minimum_length must be at least 8")
        return value

    def scan(self, secrets: Mapping[str, str | None]) -> tuple[SecretScanResult, ...]:
        return tuple(
            self.validate_secret(secret_name, secrets.get(secret_name), required=True)
            for secret_name in self.required_secret_names
        )

    def validate_secret(
        self,
        secret_name: str,
        value: str | None,
        *,
        required: bool = True,
    ) -> SecretScanResult:
        value_text = "" if value is None else str(value)
        stripped = value_text.strip()
        reasons: list[str] = []

        if not stripped:
            if required:
                reasons.append("missing_required_secret")
            else:
                return SecretScanResult(
                    secret_name=secret_name,
                    required=required,
                    present=False,
                    accepted=True,
                    reasons=(),
                    redacted_preview=None,
                )
        else:
            if len(stripped) < self.minimum_length:
                reasons.append("secret_too_short")
            if _DEFAULT_SECRET_RE.fullmatch(stripped):
                reasons.append("default_or_placeholder_secret")
            if len(set(stripped)) < 4:
                reasons.append("low_entropy_secret")

        return SecretScanResult(
            secret_name=secret_name,
            required=required,
            present=bool(stripped),
            accepted=not reasons,
            reasons=tuple(reasons),
            redacted_preview=REDACTED_VALUE if stripped else None,
        )


def redact_text(text: str) -> str:
    """Redact common secret/account tokens from log text."""

    redacted = _KEY_VALUE_SECRET_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED_VALUE}",
        text,
    )
    redacted = _PREFIXED_SECRET_RE.sub(REDACTED_VALUE, redacted)
    return _ACCOUNT_LIKE_RE.sub(REDACTED_VALUE, redacted)


def redact_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with secret-bearing keys and strings redacted."""

    return {
        str(key): _redact_payload_value(value, sensitive_key=_is_sensitive_key(str(key)))
        for key, value in payload.items()
    }


class TrustedArtifactRef(BaseModel):
    """Hash-verified artifact reference inside a configured trusted root."""

    model_config = ConfigDict(frozen=True)

    artifact_path: Path
    trusted_root: Path
    expected_sha256: str
    artifact_type: str = "generic"

    @field_validator("expected_sha256")
    @classmethod
    def _expected_hash_is_sha256(cls, value: str) -> str:
        if not _HEX_64_RE.fullmatch(value):
            raise ValueError("expected_sha256 must be a 64-character hex digest")
        return value.lower()


class TrustedArtifactValidation(BaseModel):
    """Validation result for a trusted artifact reference."""

    model_config = ConfigDict(frozen=True)

    artifact_path: Path
    trusted_root: Path
    resolved_path: Path | None = None
    accepted: bool
    sha256: str | None = None
    reasons: tuple[str, ...] = Field(default_factory=tuple)


def validate_trusted_artifact(ref: TrustedArtifactRef) -> TrustedArtifactValidation:
    reasons: list[str] = []
    resolved_path: Path | None = None

    try:
        resolved_path = resolve_within_root(ref.trusted_root, ref.artifact_path)
    except ValueError:
        reasons.append("artifact_path_outside_trusted_root")

    if _has_unsafe_artifact_extension(ref.artifact_path):
        reasons.append("unsafe_pickle_like_artifact_extension")

    sha256: str | None = None
    if resolved_path is not None:
        if not resolved_path.exists():
            reasons.append("artifact_missing")
        elif not resolved_path.is_file():
            reasons.append("artifact_not_file")
        elif not reasons:
            sha256 = _file_sha256(resolved_path)
            if sha256 != ref.expected_sha256:
                reasons.append("artifact_hash_mismatch")

    return TrustedArtifactValidation(
        artifact_path=ref.artifact_path,
        trusted_root=ref.trusted_root,
        resolved_path=resolved_path,
        accepted=not reasons,
        sha256=sha256,
        reasons=tuple(reasons),
    )


class CommandClass(str, Enum):
    RESEARCH = "research"
    COLLECTOR = "collector"
    ADMIN = "admin"
    LIVE_FORBIDDEN = "live_forbidden"


class CommandClassification(BaseModel):
    """V2 command metadata accepted only when research boundaries are intact."""

    model_config = ConfigDict(frozen=True)

    command_id: str
    command_class: CommandClass = CommandClass.RESEARCH
    research_only: bool = True
    touches_live_runtime: bool = False
    places_orders: bool = False
    emits_sizing: bool = False
    mutates_runtime_mode: bool = False
    emits_paper_or_live_signal: bool = False
    promotion_implication: bool = False

    @field_validator("command_id")
    @classmethod
    def _command_id_is_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("command_id must be non-empty")
        return value

    @model_validator(mode="after")
    def _reject_live_implications(self) -> "CommandClassification":
        reasons: list[str] = []
        if self.command_class is CommandClass.LIVE_FORBIDDEN:
            reasons.append("live_forbidden_command_class")
        if not self.research_only:
            reasons.append("research_only_false")
        if self.touches_live_runtime:
            reasons.append("touches_live_runtime")
        if self.places_orders:
            reasons.append("places_orders")
        if self.emits_sizing:
            reasons.append("emits_sizing")
        if self.mutates_runtime_mode:
            reasons.append("mutates_runtime_mode")
        if self.emits_paper_or_live_signal:
            reasons.append("emits_paper_or_live_signal")
        if self.promotion_implication:
            reasons.append("promotion_implication")
        if reasons:
            raise ValueError(
                "v2 command has forbidden implications: " + ", ".join(reasons)
            )
        return self


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    sensitive_fragments = (
        "account",
        "address",
        "api_key",
        "apikey",
        "credential",
        "password",
        "private",
        "secret",
        "token",
        "wallet",
        "webhook",
    )
    return any(fragment in normalized for fragment in sensitive_fragments)


def _redact_payload_value(value: Any, *, sensitive_key: bool) -> Any:
    if sensitive_key:
        return REDACTED_VALUE
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, tuple):
        return tuple(_redact_payload_value(item, sensitive_key=False) for item in value)
    if isinstance(value, list):
        return [_redact_payload_value(item, sensitive_key=False) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def _has_unsafe_artifact_extension(path: Path) -> bool:
    suffixes = {suffix.lower() for suffix in path.suffixes}
    return bool(suffixes & UNSAFE_ARTIFACT_EXTENSIONS)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
