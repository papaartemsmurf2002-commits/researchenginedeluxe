from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from tradingbotsuite.research.data_quality import build_manifest_data_quality_report


def build_data_quality_report(
    *manifests: Mapping[str, Any] | Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    return build_manifest_data_quality_report(*manifests)
