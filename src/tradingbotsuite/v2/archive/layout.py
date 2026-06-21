# V2-AUDIT-ID: V2-AUD-ARCH-002
# V2-CONTRACTS: docs/contracts/archive_contract.md, docs/contracts/security_boundary_contract.md
# V2-BOUNDARY: research_only, archive_path_policy, no_live_imports
# V2-OWNER: v2_archive
"""Deterministic v2 archive layout."""

from __future__ import annotations

import re
from pathlib import Path

from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.security.path_policy import PathPolicy

_SAFE_PARTITION_VALUE = re.compile(r"^[A-Za-z0-9_.%~-]+$")


def safe_partition_value(value: str | int) -> str:
    text = str(value).replace("%", "%25").replace(":", "%3A")
    if text in {"", ".", ".."} or not _SAFE_PARTITION_VALUE.fullmatch(text):
        raise ValueError(f"unsafe archive partition value: {value!r}")
    return text


def partition(key: str, value: str | int | None) -> str | None:
    if value is None:
        return None
    return f"{safe_partition_value(key)}={safe_partition_value(value)}"


class ArchiveLayout:
    """Path resolver for the local v2 archive root."""

    REQUIRED_DIRS = (
        "raw",
        "bronze",
        "silver",
        "gold",
        "manifests",
        "performance",
        "lead_book",
    )

    def __init__(self, archive_root: str | Path) -> None:
        self.root = Path(archive_root)
        self.policy = PathPolicy(root=self.root)

    def resolve(self, *parts: str | Path) -> Path:
        relative = Path(*parts)
        return self.policy.resolve(relative)

    def initialize(self) -> list[Path]:
        created: list[Path] = []
        for dirname in self.REQUIRED_DIRS:
            path = self.resolve(dirname)
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)
        return created

    def relative_to_root(self, path: str | Path) -> str:
        resolved = self.policy.resolve(path)
        return resolved.relative_to(self.root.resolve(strict=False)).as_posix()

    def layer_root(self, layer: ArchiveLayer | str) -> Path:
        layer_value = layer.value if isinstance(layer, ArchiveLayer) else layer
        return self.resolve(safe_partition_value(layer_value))

    @property
    def manifests_root(self) -> Path:
        return self.resolve("manifests")

    def raw_file_path(
        self,
        *,
        venue: str,
        datatype: str,
        date: str,
        run_id: str,
        filename: str = "payload",
        interval: str | None = None,
        instrument_id: str | None = None,
        hour: int | None = None,
    ) -> Path:
        parts = [
            "raw",
            partition("venue", venue),
            partition("datatype", datatype),
            partition("interval", interval),
            partition("date", date),
            partition("hour", f"{hour:02d}" if hour is not None else None),
            partition("instrument", instrument_id),
            partition("run_id", run_id),
        ]
        clean_parts = [part for part in parts if part is not None]
        return self.resolve(*clean_parts, f"{safe_partition_value(filename)}.jsonl.zst")

    def raw_native_file_path(
        self,
        *,
        venue: str,
        datatype: str,
        date: str,
        run_id: str,
        filename: str,
        interval: str | None = None,
        instrument_id: str | None = None,
        hour: int | None = None,
    ) -> Path:
        parts = [
            "raw",
            partition("venue", venue),
            partition("datatype", datatype),
            partition("interval", interval),
            partition("date", date),
            partition("hour", f"{hour:02d}" if hour is not None else None),
            partition("instrument", instrument_id),
            partition("run_id", run_id),
        ]
        clean_parts = [part for part in parts if part is not None]
        return self.resolve(*clean_parts, safe_partition_value(filename))

    def parquet_file_path(
        self,
        *,
        layer: ArchiveLayer | str,
        dataset: str,
        venue: str,
        date: str,
        filename: str,
        timeframe: str | None = None,
        hour: int | None = None,
        snapshot_id: str | None = None,
    ) -> Path:
        layer_value = layer.value if isinstance(layer, ArchiveLayer) else layer
        parts = [
            safe_partition_value(layer_value),
            safe_partition_value(dataset),
            partition("timeframe", timeframe),
            partition("venue", venue),
            partition("date", date),
            partition("hour", f"{hour:02d}" if hour is not None else None),
            partition("snapshot_id", snapshot_id),
        ]
        clean_parts = [part for part in parts if part is not None]
        return self.resolve(*clean_parts, f"{safe_partition_value(filename)}.parquet")
