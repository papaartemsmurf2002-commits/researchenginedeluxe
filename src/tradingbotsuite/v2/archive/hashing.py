# V2-AUDIT-ID: V2-AUD-ARCH-001
# V2-CONTRACTS: docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, no_live_imports, deterministic_hashing
# V2-OWNER: v2_archive
"""Deterministic hashing helpers for v2 contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable UTF-8 JSON bytes for JSON-compatible values."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_rows_hash(rows: Iterable[Mapping[str, Any]]) -> str:
    canonical_rows = sorted(canonical_json_bytes(dict(row)) for row in rows)
    digest = hashlib.sha256()
    for row in canonical_rows:
        digest.update(row)
        digest.update(b"\n")
    return digest.hexdigest()
