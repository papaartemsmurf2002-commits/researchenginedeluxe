from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbot.config import default_app_config
from tradingbot.data.binance import BinanceFuturesCandleProvider
from tradingbot.data.hyperliquid import HyperliquidCandleProvider
from tradingbot.models import AppConfig


@dataclass(slots=True)
class DatasetResolution:
    csv_path: Path
    metadata_path: Path
    timeframe: str
    symbol: str
    requested_start: pd.Timestamp
    requested_end: pd.Timestamp
    actual_start: pd.Timestamp | None
    actual_end: pd.Timestamp | None
    providers: list[dict[str, Any]]
    gaps: list[str]
    row_count: int
    validation: dict[str, Any] | None = None


class DataManager:
    def __init__(
        self,
        app_config: AppConfig | None = None,
        output_dir: str | Path = "data/cache",
        primary_provider: HyperliquidCandleProvider | None = None,
        fallback_provider: BinanceFuturesCandleProvider | None = None,
    ) -> None:
        self.app_config = app_config or default_app_config()
        self.output_dir = Path(output_dir)
        self.primary_provider = primary_provider or HyperliquidCandleProvider(self.app_config.execution)
        self.fallback_provider = fallback_provider

    def close(self) -> None:
        close_primary = getattr(self.primary_provider, "close", None)
        if callable(close_primary):
            close_primary()
        close_fallback = getattr(self.fallback_provider, "close", None)
        if callable(close_fallback):
            close_fallback()

    def resolve_window(self, days: int, timeframe: str) -> tuple[pd.Timestamp, pd.Timestamp]:
        end = self._floor_timeframe(pd.Timestamp.now(tz="UTC"), timeframe) - self._interval_delta(timeframe)
        start = end - pd.Timedelta(days=days)
        return start, end

    def resolve_dataset(
        self,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        provider_policy: str = "hyperliquid_fallback",
        force_refresh: bool = False,
        allow_partial: bool = False,
    ) -> DatasetResolution:
        csv_path = self._dataset_path(symbol, timeframe)
        metadata_path = csv_path.with_suffix(".json")
        if not force_refresh and csv_path.exists() and metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            cached = self._load_resolution(metadata, csv_path, metadata_path)
            if cached.actual_start is not None and cached.actual_end is not None:
                if cached.actual_start <= start and cached.actual_end >= end and (allow_partial or not cached.gaps):
                    return cached
        return self.fetch_dataset(symbol, timeframe, start, end, provider_policy, allow_partial)

    def fetch_dataset(
        self,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        provider_policy: str = "hyperliquid_fallback",
        allow_partial: bool = False,
    ) -> DatasetResolution:
        symbol = symbol.upper()
        start = self._ensure_utc(start)
        end = self._ensure_utc(end)
        interval = self._interval_delta(timeframe)
        providers_used: list[dict[str, Any]] = []
        validation: dict[str, Any] | None = None

        primary = self.primary_provider.fetch_candles(symbol, timeframe, self._to_millis(start), self._to_millis(end))
        primary = self._trim_range(primary, start, end)
        if not primary.empty:
            providers_used.append(self._provider_summary("hyperliquid", primary))
            if self.app_config.data.validate_reference_exchange:
                if self.fallback_provider is None:
                    self.fallback_provider = BinanceFuturesCandleProvider()
                overlap_reference = self.fallback_provider.fetch_candles(symbol, timeframe, self._to_millis(self._coverage_start(primary)), self._to_millis(self._coverage_end(primary)))
                overlap_reference = self._trim_range(overlap_reference, self._coverage_start(primary), self._coverage_end(primary))
                validation = self._validate_cross_exchange(symbol, timeframe, primary, overlap_reference)

        merged = primary
        needs_fallback = primary.empty or self._coverage_start(primary) is None or self._coverage_start(primary) > start
        if needs_fallback and provider_policy == "hyperliquid_fallback":
            if self.fallback_provider is None:
                self.fallback_provider = BinanceFuturesCandleProvider()
            fallback_end = (self._coverage_start(primary) - interval) if not primary.empty else end
            if fallback_end >= start:
                fallback = self.fallback_provider.fetch_candles(symbol, timeframe, self._to_millis(start), self._to_millis(fallback_end))
                fallback = self._trim_range(fallback, start, fallback_end)
                if not fallback.empty:
                    providers_used.append(self._provider_summary("binance_futures", fallback))
                    merged = self._merge_frames(fallback, primary)

        merged = self._trim_range(merged, start, end)
        gaps = self._detect_gaps(merged, timeframe, start, end)
        actual_start = self._coverage_start(merged)
        actual_end = self._coverage_end(merged)

        if not allow_partial:
            if actual_start is None or actual_start > start or actual_end is None or actual_end < end or gaps:
                missing = {
                    "requested_start": start.isoformat(),
                    "requested_end": end.isoformat(),
                    "actual_start": actual_start.isoformat() if actual_start is not None else None,
                    "actual_end": actual_end.isoformat() if actual_end is not None else None,
                    "gaps": gaps,
                    "validation": validation,
                }
                raise RuntimeError(f"Unable to build complete dataset for {symbol} {timeframe}: {json.dumps(missing)}")

        csv_path = self._dataset_path(symbol, timeframe)
        metadata_path = csv_path.with_suffix(".json")
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(csv_path, index=False)
        metadata = {
            "symbol": symbol,
            "timeframe": timeframe,
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "actual_start": actual_start.isoformat() if actual_start is not None else None,
            "actual_end": actual_end.isoformat() if actual_end is not None else None,
            "row_count": int(len(merged)),
            "providers": providers_used,
            "gaps": gaps,
            "validation": validation,
            "cache_path": str(csv_path),
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return self._load_resolution(metadata, csv_path, metadata_path)

    def resolve_required_datasets(
        self,
        symbol: str,
        days: int,
        base_timeframe: str,
        confirm_timeframe: str,
        provider_policy: str = "hyperliquid_fallback",
        force_refresh: bool = False,
        allow_partial: bool = False,
    ) -> tuple[DatasetResolution, DatasetResolution]:
        base_start, base_end = self.resolve_window(days, base_timeframe)
        confirm_start, confirm_end = self.resolve_window(days, confirm_timeframe)
        base = self.resolve_dataset(symbol, base_timeframe, base_start, base_end, provider_policy, force_refresh, allow_partial)
        confirm = self.resolve_dataset(symbol, confirm_timeframe, confirm_start, confirm_end, provider_policy, force_refresh, allow_partial)
        return base, confirm

    def _dataset_path(self, symbol: str, timeframe: str) -> Path:
        return self.output_dir / "resolved" / symbol.upper() / f"{timeframe}.csv"

    def _provider_summary(self, provider: str, frame: pd.DataFrame) -> dict[str, Any]:
        return {
            "provider": provider,
            "start": self._coverage_start(frame).isoformat() if self._coverage_start(frame) is not None else None,
            "end": self._coverage_end(frame).isoformat() if self._coverage_end(frame) is not None else None,
            "rows": int(len(frame)),
        }

    def _merge_frames(self, older: pd.DataFrame, newer: pd.DataFrame) -> pd.DataFrame:
        if older.empty:
            return newer.copy()
        if newer.empty:
            return older.copy()
        merged = pd.concat([older, newer], ignore_index=True)
        merged = merged.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
        return merged

    def _trim_range(self, frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        if frame.empty:
            return frame.copy()
        trimmed = frame[(frame["timestamp"] >= start) & (frame["timestamp"] <= end)].copy()
        return trimmed.sort_values("timestamp").reset_index(drop=True)

    def _detect_gaps(self, frame: pd.DataFrame, timeframe: str, start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
        interval = self._interval_delta(timeframe)
        if frame.empty:
            return [f"missing_all:{start.isoformat()}:{end.isoformat()}"]
        gaps: list[str] = []
        timestamps = frame["timestamp"].sort_values().reset_index(drop=True)
        if timestamps.iloc[0] > start:
            gaps.append(f"leading_gap:{start.isoformat()}:{timestamps.iloc[0].isoformat()}")
        diffs = timestamps.diff().dropna()
        for idx, diff in diffs.items():
            if diff > interval:
                prev_ts = timestamps.iloc[idx - 1]
                curr_ts = timestamps.iloc[idx]
                gaps.append(f"gap:{prev_ts.isoformat()}:{curr_ts.isoformat()}")
        if timestamps.iloc[-1] < end:
            gaps.append(f"trailing_gap:{timestamps.iloc[-1].isoformat()}:{end.isoformat()}")
        return gaps

    def _coverage_start(self, frame: pd.DataFrame) -> pd.Timestamp | None:
        if frame.empty:
            return None
        return self._ensure_utc(frame["timestamp"].min())

    def _coverage_end(self, frame: pd.DataFrame) -> pd.Timestamp | None:
        if frame.empty:
            return None
        return self._ensure_utc(frame["timestamp"].max())

    def _load_resolution(self, metadata: dict[str, Any], csv_path: Path, metadata_path: Path) -> DatasetResolution:
        return DatasetResolution(
            csv_path=csv_path,
            metadata_path=metadata_path,
            timeframe=metadata["timeframe"],
            symbol=metadata["symbol"],
            requested_start=pd.Timestamp(metadata["requested_start"]),
            requested_end=pd.Timestamp(metadata["requested_end"]),
            actual_start=pd.Timestamp(metadata["actual_start"]) if metadata.get("actual_start") else None,
            actual_end=pd.Timestamp(metadata["actual_end"]) if metadata.get("actual_end") else None,
            providers=list(metadata.get("providers", [])),
            gaps=list(metadata.get("gaps", [])),
            row_count=int(metadata.get("row_count", 0)),
            validation=metadata.get("validation"),
        )

    def _interval_delta(self, timeframe: str) -> pd.Timedelta:
        mapping = {
            "1m": pd.Timedelta(minutes=1),
            "3m": pd.Timedelta(minutes=3),
            "5m": pd.Timedelta(minutes=5),
            "15m": pd.Timedelta(minutes=15),
            "30m": pd.Timedelta(minutes=30),
            "1h": pd.Timedelta(hours=1),
            "2h": pd.Timedelta(hours=2),
            "4h": pd.Timedelta(hours=4),
            "8h": pd.Timedelta(hours=8),
            "12h": pd.Timedelta(hours=12),
            "1d": pd.Timedelta(days=1),
        }
        if timeframe not in mapping:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return mapping[timeframe]

    def _floor_timeframe(self, timestamp: pd.Timestamp, timeframe: str) -> pd.Timestamp:
        interval = self._interval_delta(timeframe)
        seconds = int(interval.total_seconds())
        epoch_seconds = int(timestamp.timestamp())
        floored = epoch_seconds - (epoch_seconds % seconds)
        return pd.Timestamp(floored, unit="s", tz="UTC")

    def _to_millis(self, timestamp: pd.Timestamp) -> int:
        return int(timestamp.timestamp() * 1000)

    def _ensure_utc(self, value: Any) -> pd.Timestamp:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            return timestamp.tz_localize("UTC")
        return timestamp.tz_convert("UTC")

    def _validate_cross_exchange(
        self,
        symbol: str,
        timeframe: str,
        hyperliquid: pd.DataFrame,
        binance: pd.DataFrame,
    ) -> dict[str, Any]:
        if hyperliquid.empty or binance.empty:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "skipped",
                "reason": "missing_overlap_data",
            }

        overlap = hyperliquid.merge(
            binance,
            on="timestamp",
            how="inner",
            suffixes=("_hyperliquid", "_binance"),
        )
        overlap = overlap.sort_values("timestamp").reset_index(drop=True)
        if overlap.empty or len(overlap) < self.app_config.data.min_validation_overlap_rows:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "skipped",
                "reason": "insufficient_overlap_rows",
                "overlap_rows": int(len(overlap)),
            }

        close_diff_pct = (
            (overlap["close_hyperliquid"] - overlap["close_binance"]).abs()
            / overlap["close_binance"].replace(0.0, pd.NA).abs()
            * 100.0
        ).fillna(0.0)
        max_close_deviation_pct = float(close_diff_pct.max())
        mean_close_deviation_pct = float(close_diff_pct.mean())
        validation = {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "ok",
            "overlap_rows": int(len(overlap)),
            "max_close_deviation_pct": max_close_deviation_pct,
            "mean_close_deviation_pct": mean_close_deviation_pct,
            "threshold_pct": self.app_config.data.max_close_deviation_pct,
        }
        if max_close_deviation_pct > self.app_config.data.max_close_deviation_pct:
            validation["status"] = "error"
            raise RuntimeError(
                f"{symbol} {timeframe} close deviation between Hyperliquid and Binance is too high: "
                f"max={max_close_deviation_pct:.4f}% threshold={self.app_config.data.max_close_deviation_pct:.4f}%"
            )
        return validation
