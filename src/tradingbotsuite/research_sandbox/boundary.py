from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SANDBOX_BOUNDARY_FLAGS: dict[str, bool] = {
    "research_only": True,
    "observe_only": True,
    "promotion_ready": False,
    "sandbox_only": True,
    "candidate_evidence": False,
    "candidate_pack_eligible": False,
}

_NEGATIVE_BOUNDARY_KEYS = frozenset(
    {
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
        "live_config_writes_allowed",
        "candidate_pack_writes_allowed",
        "candidate_pack_written",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
    }
)
_FREEFORM_CONTAINER_KEYS = frozenset(
    {
        "params",
        "params_json",
        "source_metadata",
        "metadata",
        "notes_payload",
        "extras",
        "extra",
    }
)


def sandbox_boundary_metadata() -> dict[str, Any]:
    return {
        **SANDBOX_BOUNDARY_FLAGS,
        "intended_use": "research_sandbox_hypothesis_triage_only",
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
        "live_config_writes_allowed": False,
        "candidate_pack_writes_allowed": False,
    }


def sandbox_boundary_errors(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, expected in SANDBOX_BOUNDARY_FLAGS.items():
        if payload.get(key) is not expected:
            errors.append(f"{key}_must_be_{str(expected).lower()}")
    for key in (
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
        "live_config_writes_allowed",
        "candidate_pack_writes_allowed",
    ):
        if _is_truthy_boundary_value(payload.get(key)):
            errors.append(f"{key}_must_not_be_true")
    errors.extend(_recursive_boundary_errors(payload))
    return errors


def require_sandbox_boundary(payload: Mapping[str, Any], *, payload_name: str = "sandbox_payload") -> None:
    errors = sandbox_boundary_errors(payload)
    if errors:
        joined = ", ".join(errors)
        raise ValueError(f"{payload_name} violates sandbox boundary: {joined}")


def _is_truthy_boundary_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _recursive_boundary_errors(value: Any, *, path: tuple[str, ...] = ()) -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        in_freeform = bool(set(path).intersection(_FREEFORM_CONTAINER_KEYS))
        for raw_key, child in value.items():
            key = str(raw_key)
            child_path = (*path, key)
            path_label = ".".join(child_path)
            if key in SANDBOX_BOUNDARY_FLAGS:
                expected = SANDBOX_BOUNDARY_FLAGS[key]
                if child is not expected:
                    errors.append(f"{path_label}_must_be_{str(expected).lower()}")
                if in_freeform:
                    errors.append(f"{path_label}_forbidden_in_freeform_payload")
            elif key in _NEGATIVE_BOUNDARY_KEYS:
                if _is_truthy_boundary_value(child):
                    errors.append(f"{path_label}_must_not_be_true")
                if in_freeform:
                    errors.append(f"{path_label}_forbidden_in_freeform_payload")
            errors.extend(_recursive_boundary_errors(child, path=child_path))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            errors.extend(_recursive_boundary_errors(item, path=(*path, str(index))))
    return errors
