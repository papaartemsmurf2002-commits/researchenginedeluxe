# V2-AUDIT-ID: V2-AUD-SEC-002
# V2-CONTRACTS: docs/contracts/security_boundary_contract.md
# V2-BOUNDARY: research_only, path_policy, no_live_imports
# V2-OWNER: v2_security
"""Root containment checks for v2 paths."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class PathPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    root: Path

    def resolve(self, candidate: str | Path) -> Path:
        return resolve_within_root(self.root, candidate)


def resolve_within_root(root: str | Path, candidate: str | Path) -> Path:
    root_path = Path(root).resolve(strict=False)
    candidate_path = Path(candidate)
    if not candidate_path.is_absolute():
        candidate_path = root_path / candidate_path
    resolved = candidate_path.resolve(strict=False)
    root_norm = os.path.normcase(str(root_path))
    resolved_norm = os.path.normcase(str(resolved))
    if os.path.commonpath([root_norm, resolved_norm]) != root_norm:
        raise ValueError(f"path escapes configured root: {candidate}")
    return resolved
