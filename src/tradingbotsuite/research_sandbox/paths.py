from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_SAFE_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def validate_safe_path_component(value: Any, *, field_name: str) -> str:
    raw_text = str(value or "")
    text = raw_text.strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    if raw_text != text:
        raise ValueError(f"{field_name} must not contain leading or trailing whitespace")
    if text in {".", ".."} or ".." in text:
        raise ValueError(f"{field_name} must not contain parent-directory segments")
    if any(separator in text for separator in ("/", "\\")):
        raise ValueError(f"{field_name} must be a safe path component")
    if ":" in text:
        raise ValueError(f"{field_name} must not contain drive or stream separators")
    if text[-1] in {".", " "}:
        raise ValueError(f"{field_name} must not end with a dot or space")
    if any(ord(character) < 32 for character in text):
        raise ValueError(f"{field_name} must not contain control characters")
    if not _SAFE_PATH_COMPONENT.fullmatch(text):
        raise ValueError(f"{field_name} may only contain letters, numbers, '.', '_', or '-'")
    stem = text.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED_NAMES:
        raise ValueError(f"{field_name} must not use a reserved Windows device name")
    return text


def resolve_under_root(root: str | Path, *parts: str | Path, path_name: str = "sandbox path") -> Path:
    root_path = Path(root).expanduser().resolve()
    candidate = root_path.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(f"{path_name} must stay under {root_path}: {candidate}") from exc
    return candidate


def resolve_manifest_child_path(
    raw_path: Any,
    *,
    manifest_path: str | Path,
    path_name: str = "sandbox artifact path",
) -> Path:
    manifest_parent = Path(manifest_path).expanduser().resolve().parent
    child = Path(str(raw_path)).expanduser()
    candidate = child.resolve() if child.is_absolute() else (manifest_parent / child).resolve()
    try:
        candidate.relative_to(manifest_parent)
    except ValueError as exc:
        raise ValueError(f"{path_name} must stay under {manifest_parent}: {candidate}") from exc
    return candidate
