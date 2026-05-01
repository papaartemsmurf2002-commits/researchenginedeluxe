from __future__ import annotations

from tradingbotsuite.data.contracts import registered_only_manifest


def hyperliquid_archive_registered_manifest(*, symbol: str, data_family: str) -> dict[str, object]:
    return registered_only_manifest(
        source_name="hyperliquid_archive",
        symbol=symbol,
        data_family=data_family,
    )


__all__ = ["hyperliquid_archive_registered_manifest"]
