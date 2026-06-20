from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from tradingbotsuite.data.historical_fixture_pack import (
    assert_public_archive_fixture_ready,
    assert_valid_historical_fixture_pack_manifest,
)


FOUR_BAR_HORIZON_VERSION = "wpr106-75-four-bar-horizon-v1"
FOUR_BAR_LABEL_VERSION = "wpr106-75-four-bar-label-v1"
FOUR_BAR_DATASET_VERSION = "wpr106-76-four-bar-knn-dataset-v1"
FOUR_BAR_DATASET_MANIFEST_VERSION = "wpr106-76-four-bar-knn-dataset-manifest-v1"
FOUR_BAR_BINANCE_ARCHIVE_MAPPING_VERSION = "wpr106-79-local-binance-archive-four-bar-mapper-v1"
FOUR_BAR_HORIZON_BARS = 4
BASE_INTERVAL_MS = {
    "1m": 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
}
MISSING_CONTEXT_COLUMNS = (
    "top_of_book_imbalance",
    "queue_imbalance_l5",
    "spread_bps",
    "basis_bps",
    "funding_rate",
    "funding_rate_change",
    "open_interest_change_pct",
    "premium_basis_rate",
    "premium_basis_abs",
)
FLOW_FEATURE_COLUMNS = (
    "primary_signed_imbalance_ratio",
    "primary_sqrt_signed_imbalance_ratio",
    "primary_trade_sign_acf_lag1",
    "primary_flow_price_alignment_bps",
    "primary_impact_efficiency_bps_per_sqrt_notional",
)
NO_RSI_CLOSE_PATH_COLUMNS = (
    "close_return_1_bar",
    "close_return_2_bar",
    "close_return_3_bar",
    "close_return_4_bar",
    "efficiency_ratio",
    "choppiness",
    "directional_slope_atr",
    "directional_di_spread",
    "range_width",
    "realized_volatility",
    "atr_percentile",
    "volatility_shock_zscore",
)
KLINE_HEADERLESS_FIELDS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
)
AGG_TRADE_HEADERLESS_FIELDS = (
    "aggregate_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
    "is_best_match",
)
ARCHIVE_AGG_TRADE_READ_CHUNKSIZE = 1_000_000


@dataclass(frozen=True, slots=True)
class FourBarHorizonResolution:
    base_interval: str
    horizon_bars: int
    resolved_horizon: str
    label_timing: str
    diagnostic_only: bool
    holding_window_supported: bool
    reason: str

    def to_payload(self) -> dict[str, object]:
        return {"version": FOUR_BAR_HORIZON_VERSION, **asdict(self)}


@dataclass(frozen=True, slots=True)
class FourBarDatasetBuildResult:
    dataset_path: Path
    manifest_path: Path
    row_count: int
    dataset_sha256: str
    manifest_sha256: str

    def to_payload(self) -> dict[str, object]:
        return {
            "dataset_path": str(self.dataset_path),
            "manifest_path": str(self.manifest_path),
            "row_count": self.row_count,
            "dataset_sha256": self.dataset_sha256,
            "manifest_sha256": self.manifest_sha256,
        }


def resolve_four_bar_horizon(base_interval: str, *, horizon_bars: int = FOUR_BAR_HORIZON_BARS) -> FourBarHorizonResolution:
    """Resolve the WPR106-75 signal-close plus four completed bars label horizon."""

    interval = str(base_interval).strip().lower()
    if horizon_bars != FOUR_BAR_HORIZON_BARS:
        raise ValueError(f"horizon_bars must be {FOUR_BAR_HORIZON_BARS} for WPR106-75")
    if interval == "15m":
        return FourBarHorizonResolution(
            base_interval="15m",
            horizon_bars=horizon_bars,
            resolved_horizon="1h",
            label_timing="signal_close_plus_4_completed_bars",
            diagnostic_only=False,
            holding_window_supported=True,
            reason="15m base interval times four bars maps to the existing 1h holding label.",
        )
    if interval == "1h":
        return FourBarHorizonResolution(
            base_interval="1h",
            horizon_bars=horizon_bars,
            resolved_horizon="4h",
            label_timing="signal_close_plus_4_completed_bars",
            diagnostic_only=False,
            holding_window_supported=True,
            reason="1h base interval times four bars maps to the existing 4h holding label.",
        )
    if interval == "4h":
        return FourBarHorizonResolution(
            base_interval="4h",
            horizon_bars=horizon_bars,
            resolved_horizon="16h",
            label_timing="signal_close_plus_4_completed_bars",
            diagnostic_only=True,
            holding_window_supported=False,
            reason="16h is recorded as diagnostic-only until explicit 16h holding-window support is added.",
        )
    raise ValueError("base_interval must be one of: 15m, 1h, 4h")


def four_bar_horizon_payload(base_interval: str, *, horizon_bars: int = FOUR_BAR_HORIZON_BARS) -> dict[str, object]:
    return resolve_four_bar_horizon(base_interval, horizon_bars=horizon_bars).to_payload()


def build_four_bar_event_labels(
    events: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    base_interval: str,
    event_time_column: str = "signal_bar_time_ms",
    bar_time_column: str = "bar_time_ms",
    close_column: str = "close",
    direction_column: str = "direction",
    entry_price_column: str = "entry_price",
    purge_embargo_bars: int = FOUR_BAR_HORIZON_BARS,
) -> pd.DataFrame:
    """Attach four-completed-bar labels to event rows without changing entry selection."""

    resolution = resolve_four_bar_horizon(base_interval)
    interval_ms = BASE_INTERVAL_MS[resolution.base_interval]
    _require_columns(events, (event_time_column, direction_column, entry_price_column), "events")
    _require_columns(bars, (bar_time_column, close_column), "bars")

    sorted_bars = bars.sort_values(bar_time_column).reset_index(drop=True)
    bar_times = pd.to_numeric(sorted_bars[bar_time_column], errors="coerce").to_numpy(dtype=np.float64)
    closes = pd.to_numeric(sorted_bars[close_column], errors="coerce").to_numpy(dtype=np.float64)
    if len(bar_times) == 0:
        raise ValueError("bars must contain at least one row")
    if not np.all(np.diff(bar_times[np.isfinite(bar_times)]) >= 0):
        raise ValueError("bars must be sortable by bar_time_column")

    labeled = events.copy()
    label_rows: list[dict[str, Any]] = []
    for _, event in labeled.iterrows():
        signal_close_ms = _float_or_nan(event[event_time_column])
        entry_price = _float_or_nan(event[entry_price_column])
        direction = str(event[direction_column]).strip().lower()
        if not np.isfinite(signal_close_ms) or not np.isfinite(entry_price) or entry_price <= 0 or direction not in {"long", "short"}:
            label_rows.append(_missing_label_payload(resolution, signal_close_ms, reason="invalid_event"))
            continue

        first_future_position = int(np.searchsorted(bar_times, signal_close_ms, side="right"))
        end_position = first_future_position + resolution.horizon_bars - 1
        if first_future_position < 0 or end_position >= len(sorted_bars):
            label_rows.append(_missing_label_payload(resolution, signal_close_ms, reason="insufficient_future_bars"))
            continue

        exit_price = float(closes[end_position])
        if not np.isfinite(exit_price) or exit_price <= 0:
            label_rows.append(_missing_label_payload(resolution, signal_close_ms, reason="invalid_exit_price"))
            continue

        raw_return = (exit_price - float(entry_price)) / float(entry_price)
        directional_return = raw_return if direction == "long" else -raw_return
        future_start_ms = int(bar_times[first_future_position])
        future_end_ms = int(bar_times[end_position])
        label_rows.append(
            {
                "label_accept": int(directional_return > 0.0),
                "label_pnl_multiple": float(directional_return),
                "gross_return": float(directional_return),
                "label_exit_price": exit_price,
                "label_exit_reason": "four_bar_close",
                "label_future_bar_count": int(resolution.horizon_bars),
                "label_future_start_time_ms": future_start_ms,
                "label_future_end_time_ms": future_end_ms,
                "label_exit_time_ms": future_end_ms,
                "label_interval_start_ms": int(signal_close_ms),
                "label_interval_end_ms": future_end_ms,
                "event_end_time_ms": future_end_ms,
                "purge_after_time_ms": future_end_ms + (max(int(purge_embargo_bars), 0) * interval_ms),
                "four_bar_label_available": True,
                "four_bar_label_skip_reason": None,
                "four_bar_label_version": FOUR_BAR_LABEL_VERSION,
                "four_bar_base_interval": resolution.base_interval,
                "four_bar_resolved_horizon": resolution.resolved_horizon,
                "four_bar_diagnostic_only": bool(resolution.diagnostic_only),
            }
        )
    label_frame = pd.DataFrame(label_rows, index=labeled.index)
    for column in label_frame.columns:
        labeled[column] = label_frame[column]
    return labeled


def _missing_label_payload(
    resolution: FourBarHorizonResolution,
    signal_close_ms: float,
    *,
    reason: str,
) -> dict[str, Any]:
    event_start = int(signal_close_ms) if np.isfinite(signal_close_ms) else None
    return {
        "label_accept": np.nan,
        "label_pnl_multiple": np.nan,
        "gross_return": np.nan,
        "label_exit_price": np.nan,
        "label_exit_reason": None,
        "label_future_bar_count": int(resolution.horizon_bars),
        "label_future_start_time_ms": None,
        "label_future_end_time_ms": None,
        "label_exit_time_ms": None,
        "label_interval_start_ms": event_start,
        "label_interval_end_ms": None,
        "event_end_time_ms": None,
        "purge_after_time_ms": None,
        "four_bar_label_available": False,
        "four_bar_label_skip_reason": reason,
        "four_bar_label_version": FOUR_BAR_LABEL_VERSION,
        "four_bar_base_interval": resolution.base_interval,
        "four_bar_resolved_horizon": resolution.resolved_horizon,
        "four_bar_diagnostic_only": bool(resolution.diagnostic_only),
    }


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], frame_name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{frame_name} missing required columns: {', '.join(missing)}")


def _float_or_nan(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def build_four_bar_knn_dataset_from_fixture(
    *,
    fixture_root: Path,
    output_dir: Path,
    symbol: str | None = None,
    base_intervals: tuple[str, ...] = ("15m", "1h"),
    dataset_name: str | None = None,
    max_rows_per_interval: int | None = None,
    purge_embargo_bars: int = FOUR_BAR_HORIZON_BARS,
    require_public_archive_ready: bool = True,
) -> FourBarDatasetBuildResult:
    """Build a durable research-only four-bar KNN dataset from a fixture pack."""

    fixture_root = fixture_root.expanduser()
    output_dir = output_dir.expanduser()
    manifest_path = fixture_root / "fixture_pack_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"fixture manifest not found: {manifest_path}")
    fixture_manifest = _read_json(manifest_path)
    resolved_symbol = str(symbol or fixture_manifest.get("symbol") or "").upper()
    if not resolved_symbol:
        raise ValueError("symbol must be supplied or present in the fixture manifest")
    _validate_research_only_fixture_manifest(fixture_manifest)
    fixture_validation = assert_valid_historical_fixture_pack_manifest(fixture_manifest, manifest_path=manifest_path)
    fixture_readiness = (
        assert_public_archive_fixture_ready(fixture_manifest, manifest_path=manifest_path)
        if require_public_archive_ready
        else None
    )

    bars_15m = _load_fixture_bars(fixture_root / str(fixture_manifest["families"]["bars"]["path"]))
    bars_15m = bars_15m.loc[bars_15m["symbol"].astype(str).str.upper() == resolved_symbol].reset_index(drop=True)
    agg_trade = _load_agg_trade_fixture(fixture_root / str(fixture_manifest["families"]["agg_trade"]["path"]), resolved_symbol)
    if bars_15m.empty:
        raise ValueError(f"fixture bars contain no rows for {resolved_symbol}")

    frames: list[pd.DataFrame] = []
    interval_summaries: dict[str, dict[str, object]] = {}
    for interval in base_intervals:
        resolution = resolve_four_bar_horizon(interval)
        base_bars = _base_bars_for_interval(bars_15m, interval)
        if max_rows_per_interval is not None:
            base_bars = _select_evenly_spaced_rows(base_bars, max_rows=max(int(max_rows_per_interval), 0))
        feature_frame = _build_no_rsi_feature_frame(base_bars, agg_trade, base_interval=resolution.base_interval)
        events = _dense_directional_events(feature_frame, symbol=resolved_symbol, base_interval=resolution.base_interval)
        labeled = build_four_bar_event_labels(
            events,
            feature_frame,
            base_interval=resolution.base_interval,
            event_time_column="signal_bar_time_ms",
            bar_time_column="bar_time_ms",
            close_column="close",
            direction_column="direction",
            entry_price_column="entry_price",
            purge_embargo_bars=purge_embargo_bars,
        )
        available = labeled.loc[labeled["four_bar_label_available"].astype(bool)].copy()
        available["label_version"] = FOUR_BAR_LABEL_VERSION
        available["dataset_version"] = FOUR_BAR_DATASET_VERSION
        available["event_label_semantics"] = "signal_close_plus_4_completed_bars"
        available["event_end_semantics"] = "event_end_time_ms_equals_label_future_end_time_ms"
        available["source_fixture_manifest_path"] = str(manifest_path)
        frames.append(available)
        interval_summaries[resolution.base_interval] = {
            "base_interval": resolution.base_interval,
            "resolved_horizon": resolution.resolved_horizon,
            "diagnostic_only": resolution.diagnostic_only,
            "source_bar_rows": int(len(base_bars)),
            "source_bar_row_selection": "deterministic_evenly_spaced" if max_rows_per_interval is not None else "all",
            "raw_event_rows": int(len(events)),
            "labeled_event_rows": int(len(available)),
            "dropped_unlabeled_event_rows": int(len(labeled) - len(available)),
            "skip_reasons": _value_counts(labeled.get("four_bar_label_skip_reason")),
        }

    if not frames:
        raise ValueError("no dataset frames were built")
    dataset = pd.concat(frames, ignore_index=True).sort_values(["four_bar_base_interval", "signal_bar_time_ms", "direction"]).reset_index(drop=True)
    dataset_name = dataset_name or f"{resolved_symbol.lower()}_no_rsi_four_bar_dataset.parquet"
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / dataset_name
    dataset.to_parquet(dataset_path, index=False)
    dataset_sha256 = _file_sha256(dataset_path)

    manifest = _dataset_manifest(
        fixture_manifest=fixture_manifest,
        fixture_validation=fixture_validation.to_payload(),
        fixture_readiness=fixture_readiness.to_payload() if fixture_readiness is not None else None,
        fixture_manifest_path=manifest_path,
        fixture_root=fixture_root,
        dataset=dataset,
        dataset_path=dataset_path,
        dataset_sha256=dataset_sha256,
        symbol=resolved_symbol,
        interval_summaries=interval_summaries,
        purge_embargo_bars=purge_embargo_bars,
    )
    manifest_out_path = output_dir / f"{Path(dataset_name).stem}_manifest.json"
    manifest_out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha256 = _file_sha256(manifest_out_path)
    return FourBarDatasetBuildResult(
        dataset_path=dataset_path,
        manifest_path=manifest_out_path,
        row_count=int(len(dataset)),
        dataset_sha256=dataset_sha256,
        manifest_sha256=manifest_sha256,
    )


def build_four_bar_knn_dataset_from_binance_archive(
    *,
    archive_root: Path,
    output_dir: Path,
    symbol: str,
    start_month: str | None = None,
    end_month: str | None = None,
    periods: tuple[str, ...] | None = None,
    market: str = "futures_um",
    base_intervals: tuple[str, ...] = ("15m", "1h"),
    dataset_name: str | None = None,
    max_rows_per_interval: int | None = None,
    purge_embargo_bars: int = FOUR_BAR_HORIZON_BARS,
) -> FourBarDatasetBuildResult:
    """Build a four-bar KNN dataset from existing local Binance Vision ZIPs.

    This mapper is deliberately local-only. It does not download archives, alter
    fixture packs, or change the WPR106-76 same-entry four-bar labels.
    """

    resolved_symbol = str(symbol).strip().upper()
    if resolved_symbol not in {"BTCUSDT", "ETHUSDT"}:
        raise ValueError("symbol must be BTCUSDT or ETHUSDT")
    downloads_root = _resolve_binance_archive_downloads_root(archive_root=archive_root, market=market)
    selected_periods = _resolve_archive_periods(
        downloads_root=downloads_root,
        market=market,
        symbol=resolved_symbol,
        start_month=start_month,
        end_month=end_month,
        periods=periods,
    )
    if not selected_periods:
        raise ValueError(f"no complete local Binance archive periods found for {resolved_symbol}")

    bars_15m, bar_archives = _load_archive_kline_bars(
        downloads_root=downloads_root,
        market=market,
        symbol=resolved_symbol,
        interval="15m",
        periods=selected_periods,
    )
    bar_quality = _fixed_interval_quality(
        pd.to_numeric(bars_15m["bar_time_ms"], errors="coerce").dropna().astype("int64").tolist(),
        interval_ms=BASE_INTERVAL_MS["15m"],
    )
    lower_audit = _audit_archive_kline_coverage(
        downloads_root=downloads_root,
        market=market,
        symbol=resolved_symbol,
        interval="1m",
        periods=selected_periods,
    )
    agg_trade, agg_audit = _load_archive_agg_trade_proxy(
        downloads_root=downloads_root,
        market=market,
        symbol=resolved_symbol,
        periods=selected_periods,
    )
    if bars_15m.empty:
        raise ValueError(f"local archive bars contain no rows for {resolved_symbol}")

    frames: list[pd.DataFrame] = []
    interval_summaries: dict[str, dict[str, object]] = {}
    for interval in base_intervals:
        resolution = resolve_four_bar_horizon(interval)
        base_bars = _base_bars_for_interval(bars_15m, interval)
        feature_frame = _build_no_rsi_feature_frame(base_bars, agg_trade, base_interval=resolution.base_interval)
        events = _dense_directional_events(feature_frame, symbol=resolved_symbol, base_interval=resolution.base_interval)
        labeled = build_four_bar_event_labels(
            events,
            feature_frame,
            base_interval=resolution.base_interval,
            event_time_column="signal_bar_time_ms",
            bar_time_column="bar_time_ms",
            close_column="close",
            direction_column="direction",
            entry_price_column="entry_price",
            purge_embargo_bars=purge_embargo_bars,
        )
        available = labeled.loc[labeled["four_bar_label_available"].astype(bool)].copy()
        pre_sample_count = int(len(available))
        if max_rows_per_interval is not None:
            available = _select_evenly_spaced_rows(available, max_rows=max(int(max_rows_per_interval), 0))
        available["label_version"] = FOUR_BAR_LABEL_VERSION
        available["dataset_version"] = FOUR_BAR_DATASET_VERSION
        available["event_label_semantics"] = "signal_close_plus_4_completed_bars"
        available["event_end_semantics"] = "event_end_time_ms_equals_label_future_end_time_ms"
        available["source_archive_root"] = str(downloads_root)
        available["source_archive_market"] = _market_dir(market)
        available["source_archive_period_start"] = selected_periods[0]
        available["source_archive_period_end"] = selected_periods[-1]
        frames.append(available)
        interval_summaries[resolution.base_interval] = {
            "base_interval": resolution.base_interval,
            "resolved_horizon": resolution.resolved_horizon,
            "diagnostic_only": resolution.diagnostic_only,
            "source_bar_rows": int(len(base_bars)),
            "source_bar_row_selection": "all_for_labeling",
            "raw_event_rows": int(len(events)),
            "pre_sample_labeled_event_rows": pre_sample_count,
            "labeled_event_rows": int(len(available)),
            "labeled_event_row_selection": "deterministic_evenly_spaced_after_labeling" if max_rows_per_interval is not None else "all",
            "dropped_unlabeled_event_rows": int(len(labeled) - pre_sample_count),
            "skip_reasons": _value_counts(labeled.get("four_bar_label_skip_reason")),
        }

    if not frames:
        raise ValueError("no archive dataset frames were built")
    dataset = pd.concat(frames, ignore_index=True).sort_values(["four_bar_base_interval", "signal_bar_time_ms", "direction"]).reset_index(drop=True)
    dataset_name = dataset_name or f"{resolved_symbol.lower()}_no_rsi_four_bar_binance_archive_dataset.parquet"
    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / dataset_name
    dataset.to_parquet(dataset_path, index=False)
    dataset_sha256 = _file_sha256(dataset_path)

    manifest = _archive_dataset_manifest(
        archive_root=downloads_root,
        market=_market_dir(market),
        selected_periods=selected_periods,
        bar_archives=bar_archives,
        bar_quality=bar_quality,
        lower_timeframe_audit=lower_audit,
        agg_trade_audit=agg_audit,
        dataset=dataset,
        dataset_path=dataset_path,
        dataset_sha256=dataset_sha256,
        symbol=resolved_symbol,
        interval_summaries=interval_summaries,
        purge_embargo_bars=purge_embargo_bars,
    )
    manifest_out_path = output_dir / f"{Path(dataset_name).stem}_manifest.json"
    manifest_out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha256 = _file_sha256(manifest_out_path)
    return FourBarDatasetBuildResult(
        dataset_path=dataset_path,
        manifest_path=manifest_out_path,
        row_count=int(len(dataset)),
        dataset_sha256=dataset_sha256,
        manifest_sha256=manifest_sha256,
    )


def _validate_research_only_fixture_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("research_only") is not True or manifest.get("observe_only") is not True or manifest.get("promotion_ready") is not False:
        raise ValueError("fixture manifest must be research_only true, observe_only true, and promotion_ready false")
    families = manifest.get("families")
    if not isinstance(families, dict):
        raise ValueError("fixture manifest missing families")
    for family in ("bars", "agg_trade"):
        if family not in families or not isinstance(families[family], dict) or not families[family].get("path"):
            raise ValueError(f"fixture manifest missing required {family} path")


def _load_fixture_bars(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    _require_columns(frame, ("event_time_ms", "symbol", "open_price", "high_price", "low_price", "close_price", "volume"), "bars")
    bars = pd.DataFrame(
        {
            "bar_time_ms": pd.to_numeric(frame["event_time_ms"], errors="coerce").astype("int64"),
            "symbol": frame["symbol"].astype(str).str.upper(),
            "open": pd.to_numeric(frame["open_price"], errors="coerce"),
            "high": pd.to_numeric(frame["high_price"], errors="coerce"),
            "low": pd.to_numeric(frame["low_price"], errors="coerce"),
            "close": pd.to_numeric(frame["close_price"], errors="coerce"),
            "volume": pd.to_numeric(frame["volume"], errors="coerce"),
            "source_row_index": pd.to_numeric(frame.get("source_row_index", pd.Series(range(len(frame)))), errors="coerce").fillna(-1).astype(int),
        }
    )
    return bars.sort_values("bar_time_ms").reset_index(drop=True)


def _select_evenly_spaced_rows(frame: pd.DataFrame, *, max_rows: int) -> pd.DataFrame:
    if max_rows <= 0:
        return frame.head(0).copy().reset_index(drop=True)
    if len(frame) <= max_rows:
        return frame.copy().reset_index(drop=True)
    positions = np.linspace(0, len(frame) - 1, num=max_rows, dtype=int)
    positions = np.unique(positions)
    return frame.iloc[positions].copy().reset_index(drop=True)


def _load_agg_trade_fixture(path: Path, symbol: str) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    _require_columns(
        frame,
        (
            "event_time_ms",
            "symbol",
            "agg_trade_count",
            "quote_volume",
            "taker_buy_quote_volume",
            "sell_quote_volume",
            "primary_signed_imbalance_ratio",
            "primary_sqrt_signed_imbalance_ratio",
        ),
        "agg_trade",
    )
    frame = frame.loc[frame["symbol"].astype(str).str.upper() == symbol.upper()].copy()
    for column in (
        "event_time_ms",
        "agg_trade_count",
        "quote_volume",
        "taker_buy_quote_volume",
        "sell_quote_volume",
        "primary_signed_imbalance_ratio",
        "primary_sqrt_signed_imbalance_ratio",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("event_time_ms").reset_index(drop=True)


def _base_bars_for_interval(bars_15m: pd.DataFrame, base_interval: str) -> pd.DataFrame:
    interval = str(base_interval).strip().lower()
    if interval == "15m":
        result = bars_15m.copy()
        result["base_interval"] = "15m"
        return result.reset_index(drop=True)
    if interval != "1h":
        raise ValueError("dataset builder supports base_intervals 15m and 1h")
    frame = bars_15m.copy()
    frame["hour_bucket_ms"] = (pd.to_numeric(frame["bar_time_ms"], errors="coerce").astype("int64") // BASE_INTERVAL_MS["1h"]) * BASE_INTERVAL_MS["1h"]
    rows: list[dict[str, Any]] = []
    for _, group in frame.groupby("hour_bucket_ms", sort=True):
        group = group.sort_values("bar_time_ms").reset_index(drop=True)
        if len(group) != 4:
            continue
        if not np.all(np.diff(group["bar_time_ms"].to_numpy(dtype=np.int64)) == BASE_INTERVAL_MS["15m"]):
            continue
        rows.append(
            {
                "bar_time_ms": int(group["hour_bucket_ms"].iloc[0]),
                "symbol": str(group["symbol"].iloc[0]),
                "open": float(group["open"].iloc[0]),
                "high": float(group["high"].max()),
                "low": float(group["low"].min()),
                "close": float(group["close"].iloc[-1]),
                "volume": float(group["volume"].sum()),
                "source_row_index": int(group["source_row_index"].iloc[0]),
                "base_interval": "1h",
            }
        )
    return pd.DataFrame(rows)


def _build_no_rsi_feature_frame(base_bars: pd.DataFrame, agg_trade: pd.DataFrame, *, base_interval: str) -> pd.DataFrame:
    frame = base_bars.sort_values("bar_time_ms").reset_index(drop=True).copy()
    interval_ms = BASE_INTERVAL_MS[base_interval]
    close = pd.to_numeric(frame["close"], errors="coerce")
    high = pd.to_numeric(frame["high"], errors="coerce")
    low = pd.to_numeric(frame["low"], errors="coerce")
    open_ = pd.to_numeric(frame["open"], errors="coerce")
    volume = pd.to_numeric(frame["volume"], errors="coerce")

    frame["signal_bar_time_ms"] = frame["bar_time_ms"].astype("int64")
    frame["time_ms"] = frame["bar_time_ms"].astype("int64")
    frame["entry_price"] = close
    frame["signal_bar_open"] = open_
    frame["signal_bar_high"] = high
    frame["signal_bar_low"] = low
    frame["signal_bar_close"] = close
    frame["signal_bar_volume"] = volume
    frame["source_interval"] = base_interval

    returns = close.pct_change()
    for lag in range(1, 5):
        frame[f"close_return_{lag}_bar"] = close.pct_change(lag)
    path_delta = (close - close.shift(4)).abs()
    path_sum = close.diff().abs().rolling(4, min_periods=1).sum()
    frame["efficiency_ratio"] = _safe_divide(path_delta, path_sum)

    true_range = _true_range(high, low, close)
    atr_window = 16 if base_interval == "15m" else 12
    atr = true_range.rolling(atr_window, min_periods=4).mean()
    high_roll = high.rolling(atr_window, min_periods=4).max()
    low_roll = low.rolling(atr_window, min_periods=4).min()
    range_span = (high_roll - low_roll).replace(0.0, np.nan)
    tr_sum = true_range.rolling(atr_window, min_periods=4).sum()
    frame["choppiness"] = 100.0 * np.log10(_safe_divide(tr_sum, range_span).clip(lower=1.0)) / np.log10(float(atr_window))
    frame["directional_slope_atr"] = _safe_divide(close - close.shift(4), atr)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    frame["directional_di_spread"] = _safe_divide(
        pd.Series(plus_dm, index=frame.index).rolling(atr_window, min_periods=4).sum()
        - pd.Series(minus_dm, index=frame.index).rolling(atr_window, min_periods=4).sum(),
        atr * atr_window,
    )
    frame["range_width"] = _safe_divide(high - low, close)
    frame["realized_volatility"] = returns.rolling(atr_window, min_periods=4).std().fillna(0.0)
    atr_rank_window = 96 if base_interval == "15m" else 48
    frame["atr_percentile"] = atr.rolling(atr_rank_window, min_periods=8).rank(pct=True)
    tr_mean = true_range.rolling(atr_rank_window, min_periods=8).mean()
    tr_std = true_range.rolling(atr_rank_window, min_periods=8).std()
    frame["volatility_shock_zscore"] = _safe_divide(true_range - tr_mean, tr_std)
    frame["wick_upper_ratio"] = _safe_divide(high - np.maximum(open_, close), high - low)
    frame["wick_lower_ratio"] = _safe_divide(np.minimum(open_, close) - low, high - low)
    frame["range_compression_ratio"] = _safe_divide(high - low, true_range.rolling(atr_window, min_periods=4).mean())

    flow = _aggregate_flow_features(frame["bar_time_ms"].astype("int64").to_numpy(), interval_ms, agg_trade)
    for column in flow.columns:
        frame[column] = flow[column]
    frame["primary_trade_sign_acf_lag1"] = frame["primary_signed_imbalance_ratio"] * frame["primary_signed_imbalance_ratio"].shift(1)
    frame["primary_flow_price_alignment_bps"] = frame["primary_signed_imbalance_ratio"] * returns.fillna(0.0) * 10000.0
    frame["primary_impact_efficiency_bps_per_sqrt_notional"] = _safe_divide(
        returns.fillna(0.0).abs() * 10000.0,
        np.sqrt(pd.to_numeric(frame["primary_quote_volume"], errors="coerce")),
    )

    for column in MISSING_CONTEXT_COLUMNS:
        frame[column] = np.nan
        frame[f"missing_{column}"] = True
    for column in (*NO_RSI_CLOSE_PATH_COLUMNS, *FLOW_FEATURE_COLUMNS):
        frame[f"missing_{column}"] = pd.to_numeric(frame.get(column), errors="coerce").isna()
    numeric_columns = [
        *NO_RSI_CLOSE_PATH_COLUMNS,
        *FLOW_FEATURE_COLUMNS,
        "wick_upper_ratio",
        "wick_lower_ratio",
        "range_compression_ratio",
    ]
    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return frame


def _dense_directional_events(feature_frame: pd.DataFrame, *, symbol: str, base_interval: str) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for direction, direction_long in (("long", 1), ("short", 0)):
        chunk = feature_frame.copy()
        chunk["symbol"] = symbol.upper()
        chunk["direction"] = direction
        chunk["direction_long"] = int(direction_long)
        chunk["signal_id"] = [
            f"{symbol.lower()}-{base_interval}-{direction}-{int(timestamp)}"
            for timestamp in chunk["signal_bar_time_ms"].to_numpy(dtype=np.int64)
        ]
        rows.append(chunk)
    return pd.concat(rows, ignore_index=True)


def _aggregate_flow_features(bar_times: np.ndarray, interval_ms: int, agg_trade: pd.DataFrame) -> pd.DataFrame:
    if agg_trade.empty:
        return pd.DataFrame(
            {
                "primary_agg_trade_count": np.zeros(len(bar_times), dtype=float),
                "primary_quote_volume": np.zeros(len(bar_times), dtype=float),
                "primary_taker_buy_quote_volume": np.zeros(len(bar_times), dtype=float),
                "primary_sell_quote_volume": np.zeros(len(bar_times), dtype=float),
                "primary_signed_imbalance_ratio": np.zeros(len(bar_times), dtype=float),
                "primary_sqrt_signed_imbalance_ratio": np.zeros(len(bar_times), dtype=float),
            }
        )
    times = pd.to_numeric(agg_trade["event_time_ms"], errors="coerce").to_numpy(dtype=np.float64)
    counts = pd.to_numeric(agg_trade["agg_trade_count"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    quote = pd.to_numeric(agg_trade["quote_volume"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    buy_quote = pd.to_numeric(agg_trade["taker_buy_quote_volume"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    sell_quote = pd.to_numeric(agg_trade["sell_quote_volume"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    rows: list[dict[str, float]] = []
    for start in bar_times:
        end = int(start) + interval_ms
        left = int(np.searchsorted(times, start, side="left"))
        right = int(np.searchsorted(times, end, side="left"))
        quote_sum = float(quote[left:right].sum())
        buy_sum = float(buy_quote[left:right].sum())
        sell_sum = float(sell_quote[left:right].sum())
        signed = (buy_sum - sell_sum) / quote_sum if quote_sum > 0 else 0.0
        rows.append(
            {
                "primary_agg_trade_count": float(counts[left:right].sum()),
                "primary_quote_volume": quote_sum,
                "primary_taker_buy_quote_volume": buy_sum,
                "primary_sell_quote_volume": sell_sum,
                "primary_signed_imbalance_ratio": signed,
                "primary_sqrt_signed_imbalance_ratio": float(np.sign(signed) * np.sqrt(abs(signed))),
            }
        )
    return pd.DataFrame(rows)


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    previous_close = close.shift(1)
    return pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _safe_divide(numerator: Any, denominator: Any) -> pd.Series:
    numerator_series = pd.Series(numerator)
    denominator_series = pd.Series(denominator).replace(0.0, np.nan)
    result = numerator_series / denominator_series
    return result.replace([np.inf, -np.inf], np.nan)


def _dataset_manifest(
    *,
    fixture_manifest: dict[str, Any],
    fixture_validation: dict[str, Any],
    fixture_readiness: dict[str, Any] | None,
    fixture_manifest_path: Path,
    fixture_root: Path,
    dataset: pd.DataFrame,
    dataset_path: Path,
    dataset_sha256: str,
    symbol: str,
    interval_summaries: dict[str, dict[str, object]],
    purge_embargo_bars: int,
) -> dict[str, Any]:
    missingness_columns = sorted(column for column in dataset.columns if column.startswith("missing_"))
    return {
        "dataset_manifest_version": FOUR_BAR_DATASET_MANIFEST_VERSION,
        "dataset_version": FOUR_BAR_DATASET_VERSION,
        "generated_at_ms": int(pd.Timestamp.utcnow().timestamp() * 1000),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "intended_use": "research_observe_only_hmm_knn_four_bar_dataset",
        "candidate_pack_written": False,
        "live_signal_input": False,
        "runtime_control_input": False,
        "position_sizing_input": False,
        "symbol": symbol,
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha256,
        "row_count": int(len(dataset)),
        "columns": list(dataset.columns),
        "base_intervals": interval_summaries,
        "label_semantics": {
            "label_version": FOUR_BAR_LABEL_VERSION,
            "horizon_bars": FOUR_BAR_HORIZON_BARS,
            "label_timing": "signal_close_plus_4_completed_bars",
            "event_end_time_ms": "label_future_end_time_ms",
            "purge_after_time_ms": f"label_future_end_time_ms_plus_{int(purge_embargo_bars)}_base_bars",
            "dense_directional_events": True,
            "directions": ["long", "short"],
            "same_entry_long_short_comparison": True,
        },
        "feature_semantics": {
            "no_rsi_core": True,
            "close_path_columns": list(NO_RSI_CLOSE_PATH_COLUMNS),
            "flow_proxy_columns": list(FLOW_FEATURE_COLUMNS),
            "explicit_missing_context_columns": list(MISSING_CONTEXT_COLUMNS),
            "missingness_columns_present": missingness_columns,
            "agg_trade_context": "1m public-archive aggTrade proxy, not L2 OFI or order-book imbalance",
            "perp_context_missing": {
                "funding_rate": "not_in_fixture",
                "open_interest_change_pct": "not_in_fixture",
                "premium_basis_rate": "not_in_fixture",
                "basis_bps": "not_in_fixture",
            },
        },
        "source_fixture": {
            "fixture_root": str(fixture_root),
            "fixture_manifest_path": str(fixture_manifest_path),
            "fixture_manifest_sha256": _file_sha256(fixture_manifest_path),
            "fixture_id": fixture_manifest.get("fixture_id"),
            "fixture_scope": fixture_manifest.get("fixture_scope"),
            "research_only": fixture_manifest.get("research_only"),
            "observe_only": fixture_manifest.get("observe_only"),
            "promotion_ready": fixture_manifest.get("promotion_ready"),
            "fixture_validation": fixture_validation,
            "public_archive_readiness": fixture_readiness,
            "source": fixture_manifest.get("source", {}),
            "omitted_optional_families": fixture_manifest.get("omitted_optional_families", {}),
            "research_evidence_limitations": fixture_manifest.get("research_evidence_limitations", []),
        },
    }


def _archive_dataset_manifest(
    *,
    archive_root: Path,
    market: str,
    selected_periods: tuple[str, ...],
    bar_archives: list[dict[str, Any]],
    bar_quality: dict[str, Any],
    lower_timeframe_audit: dict[str, Any],
    agg_trade_audit: dict[str, Any],
    dataset: pd.DataFrame,
    dataset_path: Path,
    dataset_sha256: str,
    symbol: str,
    interval_summaries: dict[str, dict[str, object]],
    purge_embargo_bars: int,
) -> dict[str, Any]:
    missingness_columns = sorted(column for column in dataset.columns if column.startswith("missing_"))
    return {
        "dataset_manifest_version": FOUR_BAR_DATASET_MANIFEST_VERSION,
        "dataset_version": FOUR_BAR_DATASET_VERSION,
        "archive_mapping_version": FOUR_BAR_BINANCE_ARCHIVE_MAPPING_VERSION,
        "generated_at_ms": int(pd.Timestamp.utcnow().timestamp() * 1000),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "intended_use": "research_observe_only_hmm_knn_four_bar_dataset",
        "candidate_pack_written": False,
        "live_signal_input": False,
        "runtime_control_input": False,
        "position_sizing_input": False,
        "symbol": symbol,
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha256,
        "row_count": int(len(dataset)),
        "columns": list(dataset.columns),
        "base_intervals": interval_summaries,
        "label_semantics": {
            "label_version": FOUR_BAR_LABEL_VERSION,
            "horizon_bars": FOUR_BAR_HORIZON_BARS,
            "label_timing": "signal_close_plus_4_completed_bars",
            "event_end_time_ms": "label_future_end_time_ms",
            "purge_after_time_ms": f"label_future_end_time_ms_plus_{int(purge_embargo_bars)}_base_bars",
            "dense_directional_events": True,
            "directions": ["long", "short"],
            "same_entry_long_short_comparison": True,
            "sample_timing": "after_labeling_so_future_bars_remain_real_completed_bars",
        },
        "feature_semantics": {
            "no_rsi_core": True,
            "close_path_columns": list(NO_RSI_CLOSE_PATH_COLUMNS),
            "flow_proxy_columns": list(FLOW_FEATURE_COLUMNS),
            "explicit_missing_context_columns": list(MISSING_CONTEXT_COLUMNS),
            "missingness_columns_present": missingness_columns,
            "agg_trade_context": "Binance Vision aggTrades aggregated to 1m trade-flow proxy, not L2 OFI or order-book imbalance",
            "lower_timeframe_context": "1m Binance Vision kline coverage audited for provenance; fixed four-bar labels use base bars",
            "perp_context_missing": {
                "funding_rate": "not_in_local_archive_mapper_v1",
                "open_interest_change_pct": "not_in_local_archive_mapper_v1",
                "premium_basis_rate": "not_in_local_archive_mapper_v1",
                "basis_bps": "not_in_local_archive_mapper_v1",
            },
        },
        "source_archive": {
            "source_type": "public_archive",
            "source_name": "binance_vision",
            "source_raw": "local_binance_vision_monthly_zip_cache",
            "archive_root": str(archive_root),
            "market": market,
            "periods": list(selected_periods),
            "period_start": selected_periods[0] if selected_periods else None,
            "period_end": selected_periods[-1] if selected_periods else None,
            "network_download_used": False,
            "synthetic_source_used": False,
            "bars_15m": {
                "archive_count": len(bar_archives),
                "archives": bar_archives,
                "row_count": sum(int(item.get("row_count") or 0) for item in bar_archives),
                "fixed_interval_quality": bar_quality,
            },
            "lower_timeframe_bars_1m": lower_timeframe_audit,
            "agg_trade_1m_proxy": agg_trade_audit,
            "research_evidence_limitations": [
                "not_oos_acceptance_by_itself",
                "not_sufficient_for_performance_claims_without_validation_matrix",
                "not_hyperliquid_fillability_evidence",
                "not_promotion_ready",
            ],
        },
    }


def _resolve_binance_archive_downloads_root(*, archive_root: Path, market: str) -> Path:
    root = Path(archive_root).expanduser().resolve()
    market_dir = _market_dir(market)
    candidates = [
        root,
        root / "downloads",
        root.parent if root.name == market_dir else root,
    ]
    for candidate in candidates:
        if (candidate / market_dir / "monthly").is_dir():
            return candidate
    raise FileNotFoundError(f"local Binance archive downloads root not found under {root}")


def _resolve_archive_periods(
    *,
    downloads_root: Path,
    market: str,
    symbol: str,
    start_month: str | None,
    end_month: str | None,
    periods: tuple[str, ...] | None,
) -> tuple[str, ...]:
    if periods is not None:
        selected = tuple(_validate_month(period) for period in periods)
    else:
        selected = _discover_complete_archive_periods(downloads_root=downloads_root, market=market, symbol=symbol)
    if start_month is not None:
        start = _validate_month(start_month)
        selected = tuple(period for period in selected if period >= start)
    if end_month is not None:
        end = _validate_month(end_month)
        selected = tuple(period for period in selected if period <= end)
    return tuple(sorted(dict.fromkeys(selected)))


def _discover_complete_archive_periods(*, downloads_root: Path, market: str, symbol: str) -> tuple[str, ...]:
    kline_15m = _periods_from_archive_dir(_kline_archive_dir(downloads_root=downloads_root, market=market, symbol=symbol, interval="15m"), f"{symbol}-15m-")
    kline_1m = _periods_from_archive_dir(_kline_archive_dir(downloads_root=downloads_root, market=market, symbol=symbol, interval="1m"), f"{symbol}-1m-")
    agg = _periods_from_archive_dir(_agg_archive_dir(downloads_root=downloads_root, market=market, symbol=symbol), f"{symbol}-aggTrades-")
    return tuple(sorted(kline_15m & kline_1m & agg))


def _periods_from_archive_dir(path: Path, prefix: str) -> set[str]:
    periods: set[str] = set()
    if not path.is_dir():
        return periods
    for archive in path.glob(f"{prefix}*.zip"):
        stem = archive.name.removeprefix(prefix).removesuffix(".zip")
        try:
            periods.add(_validate_month(stem))
        except ValueError:
            continue
    return periods


def _load_archive_kline_bars(
    *,
    downloads_root: Path,
    market: str,
    symbol: str,
    interval: str,
    periods: tuple[str, ...],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames: list[pd.DataFrame] = []
    archives: list[dict[str, Any]] = []
    source_offset = 0
    for period in periods:
        path = _kline_archive_path(downloads_root=downloads_root, market=market, symbol=symbol, interval=interval, period=period)
        frame = _kline_frame_from_archive(path, symbol=symbol, interval=interval, period=period, source_offset=source_offset)
        source_offset += int(len(frame))
        frames.append(frame)
        archives.append({**_archive_metadata(path, data_family="kline", interval=interval, period=period), "row_count": int(len(frame))})
    bars = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return bars.sort_values("bar_time_ms").reset_index(drop=True), archives


def _audit_archive_kline_coverage(
    *,
    downloads_root: Path,
    market: str,
    symbol: str,
    interval: str,
    periods: tuple[str, ...],
) -> dict[str, Any]:
    interval_ms = BASE_INTERVAL_MS[interval]
    all_times: list[int] = []
    archives: list[dict[str, Any]] = []
    row_count = 0
    for period in periods:
        path = _kline_archive_path(downloads_root=downloads_root, market=market, symbol=symbol, interval=interval, period=period)
        times = [int(_required_text(row, "open_time", "open_time_ms")) for row in _zip_csv_dict_rows(path, KLINE_HEADERLESS_FIELDS)]
        row_count += len(times)
        all_times.extend(times)
        archives.append({**_archive_metadata(path, data_family="kline", interval=interval, period=period), "row_count": len(times)})
    return {
        "archive_count": len(archives),
        "archives": archives,
        "row_count": int(row_count),
        "fixed_interval_quality": _fixed_interval_quality(all_times, interval_ms=interval_ms),
        "used_for_labels": False,
        "coverage_role": "lower_timeframe_context_audit",
    }


def _load_archive_agg_trade_proxy(
    *,
    downloads_root: Path,
    market: str,
    symbol: str,
    periods: tuple[str, ...],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    buckets: dict[int, dict[str, Any]] = {}
    archives: list[dict[str, Any]] = []
    selected_rows = 0
    order_anomalies = 0
    for period in periods:
        path = _agg_archive_path(downloads_root=downloads_root, market=market, symbol=symbol, period=period)
        period_selected = 0
        period_order_anomalies = 0
        last_trade_id: int | None = None
        source_row_offset = 0
        for chunk in _zip_csv_dataframe_chunks(path, AGG_TRADE_HEADERLESS_FIELDS, chunksize=ARCHIVE_AGG_TRADE_READ_CHUNKSIZE):
            chunk = chunk.reset_index(drop=True)
            period_selected += int(len(chunk))
            trade_id = _numeric_optional_archive_column(chunk, "aggregate_trade_id", "agg_trade_id", "a")
            if trade_id is not None:
                valid_trade_ids = trade_id.dropna().astype("int64")
                if not valid_trade_ids.empty:
                    if last_trade_id is not None and int(valid_trade_ids.iloc[0]) <= last_trade_id:
                        period_order_anomalies += 1
                    if len(valid_trade_ids) > 1:
                        ids = valid_trade_ids.to_numpy(dtype=np.int64)
                        period_order_anomalies += int((ids[1:] <= ids[:-1]).sum())
                    last_trade_id = int(valid_trade_ids.iloc[-1])
            grouped = _aggregate_archive_agg_trade_chunk(chunk, symbol=symbol, period=period, source_row_offset=source_row_offset)
            source_row_offset += int(len(chunk))
            for row in grouped.itertuples(index=False):
                minute_ms = int(row.event_time_ms)
                bucket = buckets.setdefault(minute_ms, _new_archive_agg_bucket(symbol=symbol, event_time_ms=minute_ms))
                bucket["agg_trade_count"] += int(row.agg_trade_count)
                bucket["quantity"] += float(row.quantity)
                bucket["quote_volume"] += float(row.quote_volume)
                bucket["taker_buy_quote_volume"] += float(row.taker_buy_quote_volume)
                bucket["sell_quote_volume"] += float(row.sell_quote_volume)
                bucket["source_row_index"] = min(int(bucket["source_row_index"]), int(row.source_row_index))
        selected_rows += period_selected
        order_anomalies += period_order_anomalies
        archives.append(
            {
                **_archive_metadata(path, data_family="agg_trade", interval=None, period=period),
                "source_selected_row_count": int(period_selected),
                "source_order_anomaly_count": int(period_order_anomalies),
            }
        )
    frame = _archive_agg_trade_frame(buckets.values())
    return frame, {
        "archive_count": len(archives),
        "archives": archives,
        "row_count": int(len(frame)),
        "source_selected_row_count": int(selected_rows),
        "agg_trade_id_order_anomaly_count": int(order_anomalies),
        "derivation_type": "agg_trade_archive_rows_aggregated_to_1m_trade_flow_proxy",
        "feature_claim_scope": "trade_flow_proxy_not_order_book_imbalance_or_ofi",
    }


def _aggregate_archive_agg_trade_chunk(chunk: pd.DataFrame, *, symbol: str, period: str, source_row_offset: int) -> pd.DataFrame:
    event_time = _numeric_required_archive_column(chunk, "transact_time", "transact_time_ms", "time", "T", period=period)
    price = _numeric_required_archive_column(chunk, "price", "p", period=period)
    quantity = _numeric_required_archive_column(chunk, "quantity", "qty", "q", period=period)
    minute = ((event_time.astype("int64") // 60_000) * 60_000).astype("int64")
    quote_volume = price.astype("float64") * quantity.astype("float64")
    maker_text = _text_optional_archive_column(chunk, "is_buyer_maker", "m")
    taker_buy_quote = quote_volume.where(maker_text.isin({"false", "0"}), 0.0)
    sell_quote = quote_volume.where(maker_text.isin({"true", "1"}), 0.0)
    source_row_index = np.arange(source_row_offset, source_row_offset + len(chunk), dtype=np.int64)
    grouped = (
        pd.DataFrame(
            {
                "event_time_ms": minute.to_numpy(dtype=np.int64),
                "agg_trade_count": np.ones(len(chunk), dtype=np.int64),
                "quantity": quantity.to_numpy(dtype=np.float64),
                "quote_volume": quote_volume.to_numpy(dtype=np.float64),
                "taker_buy_quote_volume": taker_buy_quote.to_numpy(dtype=np.float64),
                "sell_quote_volume": sell_quote.to_numpy(dtype=np.float64),
                "source_row_index": source_row_index,
            }
        )
        .groupby("event_time_ms", sort=False, as_index=False)
        .agg(
            agg_trade_count=("agg_trade_count", "sum"),
            quantity=("quantity", "sum"),
            quote_volume=("quote_volume", "sum"),
            taker_buy_quote_volume=("taker_buy_quote_volume", "sum"),
            sell_quote_volume=("sell_quote_volume", "sum"),
            source_row_index=("source_row_index", "min"),
        )
    )
    grouped.insert(1, "symbol", symbol)
    return grouped


def _kline_frame_from_archive(path: Path, *, symbol: str, interval: str, period: str, source_offset: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for source_row_index, raw in enumerate(_zip_csv_dict_rows(path, KLINE_HEADERLESS_FIELDS)):
        open_time = int(_required_text(raw, "open_time", "open_time_ms"))
        rows.append(
            {
                "bar_time_ms": open_time,
                "symbol": symbol,
                "open": float(_required_text(raw, "open")),
                "high": float(_required_text(raw, "high")),
                "low": float(_required_text(raw, "low")),
                "close": float(_required_text(raw, "close")),
                "volume": float(_required_text(raw, "volume")),
                "source_row_index": int(source_offset + source_row_index),
                "source_archive_period": period,
                "source_archive_path": str(path),
                "source_provider": "binance_vision",
                "source_data_family": "kline",
                "source_interval": interval,
            }
        )
    return pd.DataFrame(rows)


def _archive_agg_trade_frame(rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "event_time_ms",
                "symbol",
                "agg_trade_count",
                "quantity",
                "quote_volume",
                "taker_buy_quote_volume",
                "sell_quote_volume",
                "price",
                "primary_signed_imbalance_ratio",
                "primary_sqrt_signed_imbalance_ratio",
                "source_row_index",
                "source_provider",
                "source_data_family",
            ]
        )
    frame = frame.sort_values(["symbol", "event_time_ms"], kind="mergesort").reset_index(drop=True)
    quote = pd.to_numeric(frame["quote_volume"], errors="coerce").fillna(0.0)
    quantity = pd.to_numeric(frame["quantity"], errors="coerce").replace(0.0, pd.NA)
    taker_buy = pd.to_numeric(frame["taker_buy_quote_volume"], errors="coerce").fillna(0.0)
    sell = pd.to_numeric(frame["sell_quote_volume"], errors="coerce").fillna(0.0)
    denominator = quote.replace(0.0, pd.NA)
    frame["price"] = quote / quantity
    frame["primary_signed_imbalance_ratio"] = ((taker_buy - sell) / denominator).fillna(0.0)
    signed = pd.to_numeric(frame["primary_signed_imbalance_ratio"], errors="coerce")
    frame["primary_sqrt_signed_imbalance_ratio"] = signed.apply(
        lambda value: 0.0 if pd.isna(value) else (1.0 if value >= 0.0 else -1.0) * (abs(float(value)) ** 0.5)
    )
    return frame.loc[
        :,
        [
            "event_time_ms",
            "symbol",
            "agg_trade_count",
            "quantity",
            "quote_volume",
            "taker_buy_quote_volume",
            "sell_quote_volume",
            "price",
            "primary_signed_imbalance_ratio",
            "primary_sqrt_signed_imbalance_ratio",
            "source_row_index",
            "source_provider",
            "source_data_family",
        ],
    ]


def _new_archive_agg_bucket(*, symbol: str, event_time_ms: int) -> dict[str, Any]:
    return {
        "event_time_ms": int(event_time_ms),
        "symbol": symbol,
        "agg_trade_count": 0,
        "quantity": 0.0,
        "quote_volume": 0.0,
        "taker_buy_quote_volume": 0.0,
        "sell_quote_volume": 0.0,
        "source_row_index": 2**63 - 1,
        "source_provider": "binance_vision",
        "source_data_family": "agg_trade",
    }


def _zip_csv_dict_rows(path: Path, fields: tuple[str, ...]) -> Iterable[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"local Binance archive not found: {path}")
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if not members:
            return
        with archive.open(members[0], "r") as raw:
            with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                reader = csv.reader(text)
                first = next(reader, None)
                if first is None:
                    return
                if _looks_like_header(first):
                    header = [str(item).strip() for item in first]
                else:
                    header = list(fields)
                    yield _row_dict(header, first)
                for row in reader:
                    if not row:
                        continue
                    yield _row_dict(header, row)


def _zip_csv_dataframe_chunks(path: Path, fields: tuple[str, ...], *, chunksize: int) -> Iterable[pd.DataFrame]:
    if not path.is_file():
        raise FileNotFoundError(f"local Binance archive not found: {path}")
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if not members:
            return
        member = members[0]
        with archive.open(member, "r") as raw:
            first_line = raw.readline().decode("utf-8-sig").strip()
    if not first_line:
        return
    first_row = next(csv.reader([first_line]), [])
    has_header = _looks_like_header(first_row)
    with zipfile.ZipFile(path) as archive:
        with archive.open(member, "r") as raw:
            read_kwargs: dict[str, Any] = {
                "chunksize": chunksize,
                "encoding": "utf-8-sig",
                "low_memory": False,
            }
            if has_header:
                reader = pd.read_csv(raw, **read_kwargs)
            else:
                reader = pd.read_csv(raw, header=None, names=list(fields), **read_kwargs)
            for chunk in reader:
                if not chunk.empty:
                    yield chunk


def _row_dict(header: list[str], row: list[str]) -> dict[str, str]:
    return {str(key).strip(): str(value).strip() for key, value in zip(header, row)}


def _looks_like_header(row: list[str]) -> bool:
    if not row:
        return False
    try:
        float(str(row[0]).strip())
        return False
    except ValueError:
        return True


def _required_text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        if key in row and row[key] not in {None, ""}:
            return str(row[key])
    raise ValueError(f"archive row missing required field: {'/'.join(keys)}")


def _archive_column(frame: pd.DataFrame, *keys: str) -> pd.Series:
    normalized = {str(column).strip().lower(): column for column in frame.columns}
    for key in keys:
        if key in frame.columns:
            return frame[key]
        column = normalized.get(str(key).strip().lower())
        if column is not None:
            return frame[column]
    raise KeyError("/".join(keys))


def _numeric_required_archive_column(frame: pd.DataFrame, *keys: str, period: str) -> pd.Series:
    column = pd.to_numeric(_archive_column(frame, *keys), errors="coerce")
    missing = int(column.isna().sum())
    if missing:
        raise ValueError(f"archive period {period} has {missing} rows missing numeric field {'/'.join(keys)}")
    return column


def _numeric_optional_archive_column(frame: pd.DataFrame, *keys: str) -> pd.Series | None:
    try:
        return pd.to_numeric(_archive_column(frame, *keys), errors="coerce")
    except KeyError:
        return None


def _text_optional_archive_column(frame: pd.DataFrame, *keys: str) -> pd.Series:
    try:
        column = _archive_column(frame, *keys)
    except KeyError:
        return pd.Series("", index=frame.index, dtype="string")
    return column.astype("string").str.strip().str.lower()


def _optional_int(row: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in row and row[key] not in {None, ""}:
            try:
                return int(float(str(row[key])))
            except ValueError:
                return None
    return None


def _optional_bool(row: Mapping[str, Any], *keys: str) -> bool | None:
    for key in keys:
        if key not in row or row[key] in {None, ""}:
            continue
        text = str(row[key]).strip().lower()
        if text in {"true", "1"}:
            return True
        if text in {"false", "0"}:
            return False
    return None


def _archive_metadata(path: Path, *, data_family: str, interval: str | None, period: str) -> dict[str, Any]:
    archive_sha = _file_sha256(path)
    checksum_path = path.with_suffix(path.suffix + ".CHECKSUM")
    checksum_value = None
    checksum_verified = False
    if checksum_path.is_file():
        checksum_text = checksum_path.read_text(encoding="utf-8-sig").strip()
        checksum_value = checksum_text.split()[0] if checksum_text else None
        checksum_verified = checksum_value is not None and archive_sha.endswith(str(checksum_value).lower())
    return {
        "archive_path": str(path),
        "archive_sha256": archive_sha,
        "checksum_path": str(checksum_path) if checksum_path.is_file() else None,
        "checksum_value": checksum_value,
        "checksum_verified": bool(checksum_verified),
        "data_family": data_family,
        "interval": interval,
        "period": period,
    }


def _fixed_interval_quality(values: Iterable[int], *, interval_ms: int) -> dict[str, Any]:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        return {"row_count": 0, "first_event_time_ms": None, "last_event_time_ms": None, "gap_count": 0, "duplicate_count": 0}
    gap_count = 0
    duplicate_count = 0
    previous: int | None = None
    for value in ordered:
        if previous is not None:
            delta = value - previous
            if delta == 0:
                duplicate_count += 1
            elif delta != interval_ms:
                gap_count += max(1, int(delta // interval_ms) - 1) if delta > interval_ms else 1
        previous = value
    return {
        "row_count": len(ordered),
        "first_event_time_ms": int(ordered[0]),
        "last_event_time_ms": int(ordered[-1]),
        "gap_count": int(gap_count),
        "duplicate_count": int(duplicate_count),
    }


def _kline_archive_dir(*, downloads_root: Path, market: str, symbol: str, interval: str) -> Path:
    return downloads_root / _market_dir(market) / "monthly" / "klines" / symbol / interval


def _agg_archive_dir(*, downloads_root: Path, market: str, symbol: str) -> Path:
    return downloads_root / _market_dir(market) / "monthly" / "aggTrades" / symbol


def _kline_archive_path(*, downloads_root: Path, market: str, symbol: str, interval: str, period: str) -> Path:
    return _kline_archive_dir(downloads_root=downloads_root, market=market, symbol=symbol, interval=interval) / f"{symbol}-{interval}-{period}.zip"


def _agg_archive_path(*, downloads_root: Path, market: str, symbol: str, period: str) -> Path:
    return _agg_archive_dir(downloads_root=downloads_root, market=market, symbol=symbol) / f"{symbol}-aggTrades-{period}.zip"


def _market_dir(market: str) -> str:
    text = str(market or "futures_um").strip().strip("/").replace("\\", "/")
    return text.replace("/", "_")


def _validate_month(value: str) -> str:
    text = str(value).strip()
    if len(text) != 7 or text[4] != "-":
        raise ValueError(f"month must be YYYY-MM, got {value!r}")
    year = int(text[:4])
    month = int(text[5:])
    if year < 2000 or month < 1 or month > 12:
        raise ValueError(f"month must be YYYY-MM, got {value!r}")
    return f"{year:04d}-{month:02d}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _value_counts(series: pd.Series | None) -> dict[str, int]:
    if series is None:
        return {}
    counts = series.dropna().astype(str).value_counts()
    return {str(key): int(value) for key, value in counts.items()}
