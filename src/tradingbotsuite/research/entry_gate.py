from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import re
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

import httpx
from scipy import signal as scipy_signal


ENTRY_GATE_RESEARCH_VERSION = "v2-btc-entry-gate-research-2"
LEGACY_GATE_FAMILY = "acf_hvr_dsp"
GOLDILOCKS_GATE_FAMILY = "goldilocks"
GATE_FAMILIES = (LEGACY_GATE_FAMILY, GOLDILOCKS_GATE_FAMILY)
GATE_COMPONENTS = ("acf", "hvr", "dsp")
GOLDILOCKS_COMPONENTS = ("er", "vwap", "hvp")
DEFAULT_GATE_CANDIDATE_CAP = 10_000
_DEFAULT_OPTIMIZER_COMPONENTS = ("acf", "hvr", "dsp")
_DEFAULT_GOLDILOCKS_COMPONENTS = ("er", "vwap", "hvp")
_FIFTEEN_MINUTES_MS = 15 * 60 * 1000
_DEFAULT_OHLCV_CACHE_DIR = Path("data/research/chart_ohlcv_cache")
_BINANCE_FAPI_URL = "https://fapi.binance.com"
_OHLC_MISMATCH_TOLERANCE_BPS = 5.0
_HEAVY_GRID_DEFAULTS = {
    "acf_window": 14,
    "acf_block_below": -0.20,
    "acf_trend_above": 0.10,
    "hvr_short_window": 6,
    "hvr_long_window": 60,
    "hvr_block_below": 0.50,
    "hvr_release_above": 0.75,
    "dsp_min_cycle_bars": 4,
    "dsp_max_cycle_bars": 16,
    "dsp_cycle_ratio_threshold": 0.55,
    "dsp_trend_slope_threshold": 0.25,
    "er_window": 14,
    "er_min": 0.20,
    "vwap_margin_bps": 0.0,
    "hv_window_bars": 672,
    "hvp_lookback_bars": 2880,
    "hvp_min": 20.0,
    "hvp_max": 80.0,
}


def _inclusive_int_range(start: int, stop: int, step: int) -> list[int]:
    if step <= 0:
        raise ValueError("range step must be positive")
    values = list(range(start, stop + 1, step))
    return values if values and values[-1] == stop else [*values, stop]


def _inclusive_float_range(start: float, stop: float, step: float, *, precision: int = 6) -> list[float]:
    if step <= 0:
        raise ValueError("range step must be positive")
    values: list[float] = []
    current = start
    while current <= stop + (step / 10.0):
        values.append(round(current, precision))
        current += step
    if not values or not math.isclose(values[-1], stop, rel_tol=0.0, abs_tol=10 ** -precision):
        values.append(round(stop, precision))
    return values


_HEAVY_GRID_RANGES = {
    "acf_window": [10, 12, 14, 16, 20],
    "acf_block_below": [-0.30, -0.25, -0.20, -0.15],
    "acf_trend_above": [0.05, 0.10, 0.15, 0.20],
    "hvr_short_window": [4, 6, 8, 10],
    "hvr_long_window": [40, 50, 60, 80],
    "hvr_block_below": [0.40, 0.50, 0.60],
    "hvr_release_above": [0.70, 0.75, 0.85],
    "dsp_min_cycle_bars": [4, 6],
    "dsp_max_cycle_bars": [12, 16, 24],
    "dsp_cycle_ratio_threshold": [0.45, 0.55, 0.65],
    "dsp_trend_slope_threshold": [0.20, 0.25, 0.35],
    "er_window": [10, 14, 20, 24],
    "er_min": [0.12, 0.16, 0.20, 0.24, 0.30],
    "vwap_margin_bps": [0.0, 5.0, 10.0, 20.0, 30.0],
    "hv_window_bars": [96, 288, 672],
    "hvp_lookback_bars": [1344, 2880],
    "hvp_min": [10.0, 15.0, 20.0, 25.0, 30.0],
    "hvp_max": [70.0, 80.0, 90.0, 100.0],
}


@dataclass(frozen=True, slots=True)
class ChartBar:
    time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


@dataclass(frozen=True, slots=True)
class ChartSignal:
    signal_index: int
    entry_index: int
    time_ms: int
    direction: str
    marker_price: float
    next_open: float
    source_row_number: int


@dataclass(frozen=True, slots=True)
class GateParameters:
    gate_family: str = LEGACY_GATE_FAMILY
    acf_window: int = 14
    acf_block_below: float = -0.20
    acf_trend_above: float = 0.10
    hvr_short_window: int = 6
    hvr_long_window: int = 60
    hvr_block_below: float = 0.50
    hvr_release_above: float = 0.75
    dsp_min_cycle_bars: int = 4
    dsp_max_cycle_bars: int = 16
    dsp_cycle_ratio_threshold: float = 0.55
    dsp_trend_slope_threshold: float = 0.25
    use_acf: bool = True
    use_hvr: bool = True
    use_dsp: bool = True
    er_window: int = 14
    er_min: float = 0.20
    vwap_margin_bps: float = 0.0
    hv_window_bars: int = 672
    hvp_lookback_bars: int = 2880
    hvp_min: float = 20.0
    hvp_max: float = 80.0
    use_er: bool = True
    use_vwap: bool = True
    use_hvp: bool = True

    def key(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class OhlcvCoverage:
    policy: str
    cache_status: str
    cache_path: str | None
    manifest_path: str | None
    requested_start_ms: int | None
    requested_end_ms: int | None
    fetched_bar_count: int
    chart_bar_count: int
    volume_available_count: int
    volume_missing_count: int
    ohlc_mismatch_count: int
    vwap_available_count: int
    hvp_available_count: int
    cache_error: str | None = None

    @property
    def volume_coverage_rate(self) -> float:
        return self.volume_available_count / self.chart_bar_count if self.chart_bar_count else 0.0

    @property
    def vwap_coverage_rate(self) -> float:
        return self.vwap_available_count / self.chart_bar_count if self.chart_bar_count else 0.0

    @property
    def hvp_coverage_rate(self) -> float:
        return self.hvp_available_count / self.chart_bar_count if self.chart_bar_count else 0.0

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["volume_coverage_rate"] = self.volume_coverage_rate
        payload["vwap_coverage_rate"] = self.vwap_coverage_rate
        payload["hvp_coverage_rate"] = self.hvp_coverage_rate
        return payload


@dataclass(frozen=True, slots=True)
class SimulationSettings:
    exit_mode: str = "fixed"
    take_profit_pct: float = 0.005
    stop_loss_pct: float = 0.005
    runner_activation_pct: float = 0.005
    runner_trailing_stop_pct: float = 0.003
    runner_profit_floor_pct: float = 0.001
    position_size_btc: float = 0.01
    capital_quote: float = 1000.0
    entry_slippage_bps: float = 5.0
    exit_slippage_bps: float = 5.0
    fee_bps: float = 5.0
    reverse_on_opposite_signal: bool = True


@dataclass(slots=True)
class SimulatedTrade:
    direction: str
    entry_index: int
    exit_index: int
    entry_time_ms: int
    exit_time_ms: int
    entry_price: float
    exit_price: float
    pnl_quote: float
    fee_quote: float
    reason: str


@dataclass(slots=True)
class GateDecision:
    signal: ChartSignal
    accepted: bool
    gate_score: float | None
    reason: str
    corridor: bool
    high_volatility_trend: bool
    components: dict[str, float | None]


@dataclass(frozen=True, slots=True)
class EntryGateResearchResult:
    output_dir: Path
    metrics_path: Path
    grid_results_path: Path
    best_gate_manifest_path: Path
    equity_curve_path: Path
    rejected_vs_accepted_path: Path


@dataclass(frozen=True, slots=True)
class EntryGateOptimizationResult:
    output_dir: Path
    metrics_path: Path
    top_results_path: Path
    best_gate_manifest_path: Path
    equity_curve_path: Path
    rejected_vs_accepted_path: Path


@dataclass(frozen=True, slots=True)
class EntryGatePreflightResult:
    output_dir: Path
    metrics_path: Path
    preflight_results_path: Path


@dataclass(frozen=True, slots=True)
class EntryGateAnalysisResult:
    payload: dict[str, Any]


_OPTIMIZER_BARS: list[ChartBar] | None = None
_OPTIMIZER_SIGNALS: list[ChartSignal] | None = None
_OPTIMIZER_CACHE: IndicatorCache | None = None
_OPTIMIZER_SPLIT_ROWS: list[list[int]] | None = None
_OPTIMIZER_SIGNALS_BY_ROW: dict[int, ChartSignal] | None = None


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_timestamp_ms(value: str) -> int:
    timestamp = int(float(value))
    return timestamp if timestamp > 10_000_000_000 else timestamp * 1000


def _column_index(header: list[str], name: str) -> int:
    try:
        return header.index(name)
    except ValueError as exc:
        raise ValueError(f"TradingView chart export is missing required column {name!r}") from exc


def load_chart_export(path: Path, *, symbol: str = "BTCUSDT") -> tuple[list[ChartBar], list[ChartSignal], dict[str, Any]]:
    if symbol.upper() != "BTCUSDT":
        raise ValueError("entry-gate research is BTC-only in this phase")
    source_path = path.expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source_path)
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if not header:
            raise ValueError("TradingView chart export is empty")
        rows = list(reader)

    time_idx = _column_index(header, "time")
    open_idx = _column_index(header, "open")
    high_idx = _column_index(header, "high")
    low_idx = _column_index(header, "low")
    close_idx = _column_index(header, "close")
    buy_idx = _column_index(header, "Buy")
    sell_idx = _column_index(header, "Sell")
    volume_idx = next((index for index, name in enumerate(header) if name.strip().lower() == "volume"), None)

    bars = [
        ChartBar(
            time_ms=_normalize_timestamp_ms(row[time_idx]),
            open=float(row[open_idx]),
            high=float(row[high_idx]),
            low=float(row[low_idx]),
            close=float(row[close_idx]),
            volume=float(row[volume_idx]) if volume_idx is not None and volume_idx < len(row) and row[volume_idx].strip() else None,
        )
        for row in rows
    ]

    signals: list[ChartSignal] = []
    skipped = {"ambiguous_buy_and_sell": 0, "missing_next_bar": 0}
    for index, row in enumerate(rows):
        buy_marker = row[buy_idx].strip() if buy_idx < len(row) else ""
        sell_marker = row[sell_idx].strip() if sell_idx < len(row) else ""
        if not buy_marker and not sell_marker:
            continue
        if buy_marker and sell_marker:
            skipped["ambiguous_buy_and_sell"] += 1
            continue
        if index + 1 >= len(rows):
            skipped["missing_next_bar"] += 1
            continue
        signals.append(
            ChartSignal(
                signal_index=index,
                entry_index=index + 1,
                time_ms=bars[index].time_ms,
                direction="long" if buy_marker else "short",
                marker_price=float(buy_marker or sell_marker),
                next_open=bars[index + 1].open,
                source_row_number=index + 2,
            )
        )

    metadata = {
        "source_path": str(source_path),
        "source_sha256": _hash_file(source_path),
        "source_file_name": source_path.name,
        "row_count": len(rows),
        "signal_count": len(signals),
        "skip_reasons": {key: value for key, value in skipped.items() if value},
    }
    return bars, signals, metadata


def _cache_policy_for_family(gate_family: str, policy: str | None) -> str:
    if policy is not None:
        normalized = policy.strip().lower()
    else:
        normalized = "use-or-fetch" if gate_family == GOLDILOCKS_GATE_FAMILY else "off"
    if normalized not in {"use-or-fetch", "cache-only", "off"}:
        raise ValueError("ohlcv_cache_policy must be one of: use-or-fetch, cache-only, off")
    return normalized


def _normalize_gate_family(gate_family: str | None) -> str:
    normalized = (gate_family or LEGACY_GATE_FAMILY).strip().lower().replace("-", "_")
    if normalized == "legacy":
        normalized = LEGACY_GATE_FAMILY
    if normalized not in GATE_FAMILIES:
        raise ValueError(f"gate_family must be one of: {', '.join(GATE_FAMILIES)}")
    return normalized


def _required_goldilocks_warmup_bars(params: GateParameters | None = None) -> int:
    if params is None:
        return int(max(_HEAVY_GRID_RANGES["hv_window_bars"]) + max(_HEAVY_GRID_RANGES["hvp_lookback_bars"]))
    return int(max(params.er_window, params.hv_window_bars + params.hvp_lookback_bars))


def _ohlcv_cache_paths(cache_dir: Path, symbol: str, start_ms: int, end_ms: int) -> tuple[Path, Path]:
    slug = f"{symbol.upper()}_15m_{start_ms}_{end_ms}"
    return cache_dir / f"{slug}.json", cache_dir / f"{slug}.manifest.json"


def _ohlcv_row_hash(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_ohlcv_rows(rows: list[dict[str, Any]], *, start_ms: int, end_ms: int) -> None:
    seen: set[int] = set()
    previous_time: int | None = None
    for row in rows:
        time_ms = int(row["time_ms"])
        if time_ms in seen:
            raise ValueError(f"duplicate Binance OHLCV bar at {time_ms}")
        seen.add(time_ms)
        if previous_time is not None and time_ms - previous_time != _FIFTEEN_MINUTES_MS:
            raise ValueError(f"missing Binance OHLCV bar between {previous_time} and {time_ms}")
        previous_time = time_ms


def _write_ohlcv_cache(cache_path: Path, manifest_path: Path, rows: list[dict[str, Any]], *, symbol: str, start_ms: int, end_ms: int) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    _validate_ohlcv_rows(rows, start_ms=start_ms, end_ms=end_ms)
    cache_path.write_text(json.dumps(rows, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    manifest = {
        "symbol": symbol.upper(),
        "interval": "15m",
        "source": "binance_usdm_klines",
        "requested_start_ms": start_ms,
        "requested_end_ms": end_ms,
        "row_count": len(rows),
        "first_time_ms": rows[0]["time_ms"] if rows else None,
        "last_time_ms": rows[-1]["time_ms"] if rows else None,
        "sha256": _ohlcv_row_hash(rows),
        "created_at_ms": int(time.time() * 1000),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _load_ohlcv_cache(cache_path: Path, manifest_path: Path, *, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    rows = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"invalid OHLCV cache rows in {cache_path}")
    _validate_ohlcv_rows(rows, start_ms=start_ms, end_ms=end_ms)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("sha256") != _ohlcv_row_hash(rows):
            raise ValueError(f"OHLCV cache hash mismatch for {cache_path}")
    return rows


def _discover_ohlcv_cache(cache_dir: Path, symbol: str, *, start_ms: int, end_ms: int) -> tuple[Path, Path, list[dict[str, Any]]] | None:
    candidates: list[tuple[int, int, Path, Path, list[dict[str, Any]]]] = []
    for cache_path in cache_dir.glob(f"{symbol.upper()}_15m_*.json"):
        if cache_path.name.endswith(".manifest.json"):
            continue
        manifest_path = cache_path.with_name(cache_path.stem + ".manifest.json")
        try:
            rows = _load_ohlcv_cache(cache_path, manifest_path, start_ms=start_ms, end_ms=end_ms)
        except Exception:
            continue
        if not rows:
            continue
        first_time = int(rows[0]["time_ms"])
        last_time = int(rows[-1]["time_ms"])
        if first_time <= start_ms and last_time >= end_ms:
            candidates.append((first_time, last_time, cache_path, manifest_path, rows))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], -item[1]))
    _first_time, _last_time, cache_path, manifest_path, rows = candidates[0]
    return cache_path, manifest_path, rows


def _fetch_binance_ohlcv(symbol: str, *, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = start_ms
    with httpx.Client(base_url=_BINANCE_FAPI_URL, timeout=30.0) as client:
        while cursor <= end_ms:
            response = client.get(
                "/fapi/v1/klines",
                params={
                    "symbol": symbol.upper(),
                    "interval": "15m",
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1500,
                },
            )
            if response.status_code in {429, 418}:
                raise RuntimeError(f"Binance OHLCV fetch was rate-limited with HTTP {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            if not payload:
                break
            for item in payload:
                open_time = int(item[0])
                if open_time < start_ms or open_time > end_ms:
                    continue
                rows.append(
                    {
                        "time_ms": open_time,
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    }
                )
            next_cursor = int(payload[-1][0]) + _FIFTEEN_MINUTES_MS
            if next_cursor <= cursor:
                break
            cursor = next_cursor
            time.sleep(0.05)
    rows = sorted({int(row["time_ms"]): row for row in rows}.values(), key=lambda row: int(row["time_ms"]))
    _validate_ohlcv_rows(rows, start_ms=start_ms, end_ms=end_ms)
    return rows


def _bps_distance(reference: float, value: float) -> float:
    if reference == 0:
        return math.inf if value != 0 else 0.0
    return abs(value - reference) / abs(reference) * 10_000.0


def _merge_ohlcv_volume(
    bars: list[ChartBar],
    ohlcv_rows: list[dict[str, Any]],
    *,
    tolerance_bps: float = _OHLC_MISMATCH_TOLERANCE_BPS,
) -> tuple[list[ChartBar], int, int]:
    by_time = {int(row["time_ms"]): row for row in ohlcv_rows}
    merged: list[ChartBar] = []
    missing = 0
    mismatch = 0
    for bar in bars:
        row = by_time.get(bar.time_ms)
        if row is None:
            missing += 1
            merged.append(ChartBar(bar.time_ms, bar.open, bar.high, bar.low, bar.close, None))
            continue
        distances = [
            _bps_distance(bar.open, float(row["open"])),
            _bps_distance(bar.high, float(row["high"])),
            _bps_distance(bar.low, float(row["low"])),
            _bps_distance(bar.close, float(row["close"])),
        ]
        if max(distances) > tolerance_bps:
            mismatch += 1
            merged.append(ChartBar(bar.time_ms, bar.open, bar.high, bar.low, bar.close, None))
            continue
        merged.append(ChartBar(bar.time_ms, bar.open, bar.high, bar.low, bar.close, float(row["volume"])))
    return merged, missing, mismatch


def prepare_ohlcv_enriched_bars(
    bars: list[ChartBar],
    *,
    symbol: str,
    gate_family: str,
    ohlcv_cache_policy: str | None = None,
    ohlcv_cache_dir: Path | None = None,
    required_warmup_bars: int | None = None,
    hvp_coverage_window_bars: int | None = None,
    hvp_coverage_lookback_bars: int | None = None,
) -> tuple[list[ChartBar], OhlcvCoverage | None]:
    normalized_family = _normalize_gate_family(gate_family)
    policy = _cache_policy_for_family(normalized_family, ohlcv_cache_policy)
    if normalized_family != GOLDILOCKS_GATE_FAMILY:
        return bars, None
    cache_dir = ohlcv_cache_dir or _DEFAULT_OHLCV_CACHE_DIR
    chart_bar_count = len(bars)
    warmup = required_warmup_bars if required_warmup_bars is not None else _required_goldilocks_warmup_bars()
    coverage_hv_window = int(hvp_coverage_window_bars or _HEAVY_GRID_DEFAULTS["hv_window_bars"])
    coverage_hvp_lookback = int(hvp_coverage_lookback_bars or _HEAVY_GRID_DEFAULTS["hvp_lookback_bars"])
    if not bars:
        coverage = OhlcvCoverage(policy, "empty_chart", None, None, None, None, 0, 0, 0, 0, 0, 0, 0)
        return bars, coverage
    if policy == "off":
        available = sum(1 for bar in bars if bar.volume is not None)
        cache = IndicatorCache(bars)
        coverage = OhlcvCoverage(
            policy=policy,
            cache_status="disabled",
            cache_path=None,
            manifest_path=None,
            requested_start_ms=None,
            requested_end_ms=None,
            fetched_bar_count=0,
            chart_bar_count=chart_bar_count,
            volume_available_count=available,
            volume_missing_count=chart_bar_count - available,
            ohlc_mismatch_count=0,
            vwap_available_count=sum(1 for value in cache.daily_vwap() if value is not None),
            hvp_available_count=sum(1 for value in cache.historical_volatility_percentile(coverage_hv_window, coverage_hvp_lookback) if value is not None),
        )
        return bars, coverage

    start_ms = bars[0].time_ms - int(warmup * _FIFTEEN_MINUTES_MS)
    end_ms = bars[-1].time_ms
    cache_path, manifest_path = _ohlcv_cache_paths(cache_dir, symbol, start_ms, end_ms)
    cache_status = "miss"
    cache_error: str | None = None
    rows: list[dict[str, Any]] = []
    try:
        if cache_path.exists():
            rows = _load_ohlcv_cache(cache_path, manifest_path, start_ms=start_ms, end_ms=end_ms)
            cache_status = "hit"
        elif discovered := _discover_ohlcv_cache(cache_dir, symbol, start_ms=bars[0].time_ms, end_ms=end_ms):
            cache_path, manifest_path, rows = discovered
            cache_status = "hit"
        elif policy == "use-or-fetch":
            rows = _fetch_binance_ohlcv(symbol, start_ms=start_ms, end_ms=end_ms)
            _write_ohlcv_cache(cache_path, manifest_path, rows, symbol=symbol, start_ms=start_ms, end_ms=end_ms)
            cache_status = "fetched"
        else:
            cache_status = "missing"
    except Exception as exc:
        cache_status = "error"
        cache_error = str(exc)
        rows = []

    enriched, missing_count, mismatch_count = _merge_ohlcv_volume(bars, rows) if rows else (bars, chart_bar_count, 0)
    cache = IndicatorCache(enriched)
    vwap_available_count = sum(1 for value in cache.daily_vwap() if value is not None)
    hvp_available_count = sum(1 for value in cache.historical_volatility_percentile(coverage_hv_window, coverage_hvp_lookback) if value is not None)
    volume_available_count = sum(1 for bar in enriched if bar.volume is not None)
    coverage = OhlcvCoverage(
        policy=policy,
        cache_status=cache_status,
        cache_path=str(cache_path),
        manifest_path=str(manifest_path),
        requested_start_ms=start_ms,
        requested_end_ms=end_ms,
        fetched_bar_count=len(rows),
        chart_bar_count=chart_bar_count,
        volume_available_count=volume_available_count,
        volume_missing_count=missing_count + mismatch_count,
        ohlc_mismatch_count=mismatch_count,
        vwap_available_count=vwap_available_count,
        hvp_available_count=hvp_available_count,
        cache_error=cache_error,
    )
    return enriched, coverage


def _rma(values: list[float], length: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if length <= 0 or len(values) < length:
        return result
    seed = sum(values[:length]) / length
    result[length - 1] = seed
    previous = seed
    for index in range(length, len(values)):
        previous = ((previous * (length - 1)) + values[index]) / length
        result[index] = previous
    return result


def _rma_optional(values: list[float | None], length: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    valid_indices = [index for index, value in enumerate(values) if value is not None]
    if length <= 0 or len(valid_indices) < length:
        return result
    seed_indices = valid_indices[:length]
    seed_index = seed_indices[-1]
    seed = sum(float(values[index]) for index in seed_indices) / length
    result[seed_index] = seed
    previous = seed
    for index in range(seed_index + 1, len(values)):
        value = values[index]
        if value is None:
            continue
        previous = ((previous * (length - 1)) + value) / length
        result[index] = previous
    return result


def _clip(value: float, lower: float = -100.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


class IndicatorCache:
    def __init__(self, bars: list[ChartBar]) -> None:
        self.bars = bars
        self.tr = self._true_ranges()
        self.log_returns = self._log_returns()
        self._atr: dict[int, list[float | None]] = {}
        self._adx: dict[int, tuple[list[float | None], list[float | None], list[float | None]]] = {}
        self._chop: dict[int, list[float | None]] = {}
        self._er: dict[int, list[float | None]] = {}
        self._slope: dict[int, list[float | None]] = {}
        self._range_width: dict[int, list[float | None]] = {}
        self._breakout: dict[int, tuple[list[bool], list[bool]]] = {}
        self._atr_percentile: dict[int, list[float | None]] = {}
        self._volatility_shock: dict[int, list[float | None]] = {}
        self._acf1: dict[int, list[float | None]] = {}
        self._hvr: dict[tuple[int, int], list[float | None]] = {}
        self._dsp_cycle_ratio: dict[tuple[int, int], list[float | None]] = {}
        self._return_slope: dict[int, list[float | None]] = {}
        self._daily_vwap: list[float | None] | None = None
        self._hvp: dict[tuple[int, int], list[float | None]] = {}

    def _true_ranges(self) -> list[float]:
        ranges: list[float] = []
        previous_close: float | None = None
        for bar in self.bars:
            if previous_close is None:
                ranges.append(bar.high - bar.low)
            else:
                ranges.append(max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close)))
            previous_close = bar.close
        return ranges

    def _log_returns(self) -> list[float | None]:
        returns: list[float | None] = [None]
        for previous, current in zip(self.bars, self.bars[1:]):
            returns.append(None if previous.close <= 0 or current.close <= 0 else math.log(current.close / previous.close))
        return returns

    def atr(self, length: int) -> list[float | None]:
        if length not in self._atr:
            self._atr[length] = _rma(self.tr, length)
        return self._atr[length]

    def adx(self, length: int) -> tuple[list[float | None], list[float | None], list[float | None]]:
        if length in self._adx:
            return self._adx[length]
        plus_dm = [0.0]
        minus_dm = [0.0]
        for previous, current in zip(self.bars, self.bars[1:]):
            up_move = current.high - previous.high
            down_move = previous.low - current.low
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        tr_rma = self.atr(length)
        plus_rma = _rma(plus_dm, length)
        minus_rma = _rma(minus_dm, length)
        plus_di: list[float | None] = []
        minus_di: list[float | None] = []
        dx_values: list[float | None] = []
        for tr_value, plus_value, minus_value in zip(tr_rma, plus_rma, minus_rma):
            if tr_value is None or plus_value is None or minus_value is None or tr_value <= 0:
                plus_di.append(None)
                minus_di.append(None)
                dx_values.append(None)
                continue
            plus = 100.0 * plus_value / tr_value
            minus = 100.0 * minus_value / tr_value
            plus_di.append(plus)
            minus_di.append(minus)
            denominator = plus + minus
            dx_values.append(None if denominator <= 0 else 100.0 * abs(plus - minus) / denominator)
        adx_values = _rma_optional(dx_values, length)
        self._adx[length] = (adx_values, plus_di, minus_di)
        return self._adx[length]

    def choppiness(self, length: int) -> list[float | None]:
        if length in self._chop:
            return self._chop[length]
        values: list[float | None] = []
        denominator = math.log10(length) if length > 1 else 0.0
        for index in range(len(self.bars)):
            if index + 1 < length or denominator <= 0:
                values.append(None)
                continue
            start = index - length + 1
            high = max(bar.high for bar in self.bars[start : index + 1])
            low = min(bar.low for bar in self.bars[start : index + 1])
            range_width = high - low
            tr_sum = sum(self.tr[start : index + 1])
            values.append(None if range_width <= 0 or tr_sum <= 0 else 100.0 * math.log10(tr_sum / range_width) / denominator)
        self._chop[length] = values
        return values

    def efficiency_ratio(self, length: int) -> list[float | None]:
        if length in self._er:
            return self._er[length]
        closes = [bar.close for bar in self.bars]
        values: list[float | None] = []
        for index in range(len(closes)):
            if index < length:
                values.append(None)
                continue
            net_change = abs(closes[index] - closes[index - length])
            path = sum(abs(closes[j] - closes[j - 1]) for j in range(index - length + 1, index + 1))
            values.append(0.0 if path <= 0 else max(0.0, min(1.0, net_change / path)))
        self._er[length] = values
        return values

    def slope_atr(self, length: int) -> list[float | None]:
        if length in self._slope:
            return self._slope[length]
        closes = [bar.close for bar in self.bars]
        atr_values = self.atr(14)
        x_values = list(range(length))
        x_mean = sum(x_values) / length
        x_denom = sum((x - x_mean) ** 2 for x in x_values)
        values: list[float | None] = []
        for index in range(len(closes)):
            if index + 1 < length or atr_values[index] is None or atr_values[index] == 0 or x_denom <= 0:
                values.append(None)
                continue
            window = closes[index - length + 1 : index + 1]
            y_mean = sum(window) / length
            slope_per_bar = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, window)) / x_denom
            values.append((slope_per_bar * length) / float(atr_values[index]))
        self._slope[length] = values
        return values

    def range_width(self, length: int) -> list[float | None]:
        if length in self._range_width:
            return self._range_width[length]
        values: list[float | None] = []
        for index in range(len(self.bars)):
            if index + 1 < length or self.bars[index].close <= 0:
                values.append(None)
                continue
            window = self.bars[index - length + 1 : index + 1]
            values.append((max(bar.high for bar in window) - min(bar.low for bar in window)) / self.bars[index].close)
        self._range_width[length] = values
        return values

    def daily_vwap(self) -> list[float | None]:
        if self._daily_vwap is not None:
            return self._daily_vwap
        values: list[float | None] = []
        current_day: int | None = None
        cumulative_volume = 0.0
        cumulative_tp_volume = 0.0
        for bar in self.bars:
            day = bar.time_ms // 86_400_000
            if current_day != day:
                current_day = day
                cumulative_volume = 0.0
                cumulative_tp_volume = 0.0
            if bar.volume is None or bar.volume <= 0:
                values.append(None)
                continue
            typical_price = (bar.high + bar.low + bar.close) / 3.0
            cumulative_volume += bar.volume
            cumulative_tp_volume += typical_price * bar.volume
            values.append(None if cumulative_volume <= 0 else cumulative_tp_volume / cumulative_volume)
        self._daily_vwap = values
        return values

    def historical_volatility_percentile(self, hv_window_bars: int, lookback_bars: int) -> list[float | None]:
        key = (hv_window_bars, lookback_bars)
        if key in self._hvp:
            return self._hvp[key]
        hv_values: list[float | None] = []
        for index in range(len(self.log_returns)):
            if hv_window_bars < 2 or index + 1 < hv_window_bars:
                hv_values.append(None)
                continue
            window = self.log_returns[index - hv_window_bars + 1 : index + 1]
            if any(value is None for value in window):
                hv_values.append(None)
                continue
            hv_values.append(_sample_std([float(value) for value in window if value is not None]))
        percentiles: list[float | None] = []
        for index, current in enumerate(hv_values):
            if current is None or lookback_bars <= 1 or index + 1 < lookback_bars:
                percentiles.append(None)
                continue
            window = [value for value in hv_values[index - lookback_bars + 1 : index + 1] if value is not None]
            if len(window) < lookback_bars or current is None:
                percentiles.append(None)
                continue
            percentiles.append(sum(1 for value in window if value <= current) / len(window) * 100.0)
        self._hvp[key] = percentiles
        return percentiles

    def breakout(self, length: int) -> tuple[list[bool], list[bool]]:
        if length in self._breakout:
            return self._breakout[length]
        up: list[bool] = []
        down: list[bool] = []
        for index, bar in enumerate(self.bars):
            if index < length:
                up.append(False)
                down.append(False)
                continue
            history = self.bars[index - length : index]
            up.append(bar.close > max(previous.high for previous in history))
            down.append(bar.close < min(previous.low for previous in history))
        self._breakout[length] = (up, down)
        return self._breakout[length]

    def atr_percentile(self, length: int) -> list[float | None]:
        if length in self._atr_percentile:
            return self._atr_percentile[length]
        atr_values = self.atr(14)
        values: list[float | None] = []
        for index, current in enumerate(atr_values):
            if current is None or index + 1 < length:
                values.append(None)
                continue
            window = [value for value in atr_values[index - length + 1 : index + 1] if value is not None]
            values.append(None if not window else sum(1 for value in window if value <= current) / len(window))
        self._atr_percentile[length] = values
        return values

    def volatility_shock_zscore(self, length: int) -> list[float | None]:
        if length in self._volatility_shock:
            return self._volatility_shock[length]
        closes = [bar.close for bar in self.bars]
        realized: list[float | None] = []
        for index in range(len(closes)):
            if index < length:
                realized.append(None)
                continue
            returns = [math.log(current / previous) for previous, current in zip(closes[index - length : index], closes[index - length + 1 : index + 1]) if previous > 0 and current > 0]
            if len(returns) < 2:
                realized.append(None)
            else:
                mean = sum(returns) / len(returns)
                variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
                realized.append(math.sqrt(max(variance, 0.0)))
        values: list[float | None] = []
        for index, current in enumerate(realized):
            if current is None or index < length * 2:
                values.append(None)
                continue
            history = [value for value in realized[index - length : index] if value is not None]
            if len(history) < 2:
                values.append(None)
                continue
            mean = sum(history) / len(history)
            variance = sum((value - mean) ** 2 for value in history) / (len(history) - 1)
            values.append(0.0 if variance <= 0 else (current - mean) / math.sqrt(variance))
        self._volatility_shock[length] = values
        return values

    def lag1_autocorrelation(self, window: int) -> list[float | None]:
        if window in self._acf1:
            return self._acf1[window]
        values: list[float | None] = []
        for index in range(len(self.log_returns)):
            if index < window:
                values.append(None)
                continue
            returns = self.log_returns[index - window + 1 : index + 1]
            if any(value is None for value in returns):
                values.append(None)
                continue
            series = [float(value) for value in returns if value is not None]
            if len(series) < 3:
                values.append(None)
                continue
            current = series[1:]
            previous = series[:-1]
            current_mean = sum(current) / len(current)
            previous_mean = sum(previous) / len(previous)
            numerator = sum((now - current_mean) * (lagged - previous_mean) for now, lagged in zip(current, previous))
            current_variance = sum((now - current_mean) ** 2 for now in current)
            previous_variance = sum((lagged - previous_mean) ** 2 for lagged in previous)
            denominator = math.sqrt(current_variance * previous_variance)
            values.append(None if denominator <= 0 else max(-1.0, min(1.0, numerator / denominator)))
        self._acf1[window] = values
        return values

    def historical_volatility_ratio(self, short_window: int, long_window: int) -> list[float | None]:
        key = (short_window, long_window)
        if key in self._hvr:
            return self._hvr[key]
        values: list[float | None] = []
        for index in range(len(self.log_returns)):
            if index < long_window or short_window >= long_window:
                values.append(None)
                continue
            short_returns = self.log_returns[index - short_window + 1 : index + 1]
            long_returns = self.log_returns[index - long_window + 1 : index + 1]
            if any(value is None for value in short_returns) or any(value is None for value in long_returns):
                values.append(None)
                continue
            short_std = _sample_std([float(value) for value in short_returns if value is not None])
            long_std = _sample_std([float(value) for value in long_returns if value is not None])
            values.append(None if short_std is None or long_std is None or long_std <= 0 else short_std / long_std)
        self._hvr[key] = values
        return values

    def return_slope(self, length: int) -> list[float | None]:
        if length in self._return_slope:
            return self._return_slope[length]
        x_values = list(range(length))
        x_mean = sum(x_values) / length
        x_denom = sum((x - x_mean) ** 2 for x in x_values)
        values: list[float | None] = []
        for index in range(len(self.log_returns)):
            if index + 1 < length or x_denom <= 0:
                values.append(None)
                continue
            window = self.log_returns[index - length + 1 : index + 1]
            if any(value is None for value in window):
                values.append(None)
                continue
            returns = [float(value) for value in window if value is not None]
            y_mean = sum(returns) / length
            slope = sum((x - x_mean) * (value - y_mean) for x, value in zip(x_values, returns)) / x_denom
            std = _sample_std(returns)
            values.append(None if std is None or std <= 0 else (slope * length) / std)
        self._return_slope[length] = values
        return values

    def dsp_cycle_ratio(self, min_cycle_bars: int, max_cycle_bars: int) -> list[float | None]:
        key = (min_cycle_bars, max_cycle_bars)
        if key in self._dsp_cycle_ratio:
            return self._dsp_cycle_ratio[key]
        if min_cycle_bars <= 1 or max_cycle_bars <= min_cycle_bars:
            self._dsp_cycle_ratio[key] = [None for _ in self.bars]
            return self._dsp_cycle_ratio[key]
        numeric_returns = [0.0 if value is None else float(value) for value in self.log_returns]
        low = 1.0 / max_cycle_bars
        # SciPy interprets frequencies in cycles/sample when fs=1.0, so the
        # upper edge must remain below the 0.5 Nyquist boundary.
        high = min(0.49, 1.0 / min_cycle_bars)
        if not 0.0 < low < high < 0.5:
            self._dsp_cycle_ratio[key] = [None for _ in self.bars]
            return self._dsp_cycle_ratio[key]
        sos = scipy_signal.butter(2, [low, high], btype="bandpass", output="sos", fs=1.0)
        filtered = scipy_signal.sosfilt(sos, numeric_returns)
        rms_window = max(max_cycle_bars, min_cycle_bars * 2)
        warmup = max_cycle_bars * 3
        values: list[float | None] = []
        for index in range(len(numeric_returns)):
            if index < warmup or index + 1 < rms_window:
                values.append(None)
                continue
            raw_window = numeric_returns[index - rms_window + 1 : index + 1]
            filtered_window = filtered[index - rms_window + 1 : index + 1]
            raw_rms = math.sqrt(sum(value * value for value in raw_window) / len(raw_window))
            filtered_rms = math.sqrt(sum(float(value) * float(value) for value in filtered_window) / len(filtered_window))
            values.append(None if raw_rms <= 0 else filtered_rms / raw_rms)
        self._dsp_cycle_ratio[key] = values
        return values


def _score_legacy_gate_at_bar(cache: IndicatorCache, index: int, direction: str, params: GateParameters) -> tuple[float | None, dict[str, float | None], bool, bool, str | None]:
    if index <= 0 or index >= len(cache.bars):
        return None, {}, False, False, "index_out_of_range"
    enabled = [name for name, active in {"acf": params.use_acf, "hvr": params.use_hvr, "dsp": params.use_dsp}.items() if active]
    if not enabled:
        return None, {}, False, False, "no_enabled_components"

    acf_values = cache.lag1_autocorrelation(params.acf_window)
    hvr_values = cache.historical_volatility_ratio(params.hvr_short_window, params.hvr_long_window)
    dsp_values = cache.dsp_cycle_ratio(params.dsp_min_cycle_bars, params.dsp_max_cycle_bars)
    slope_values = cache.return_slope(max(params.dsp_max_cycle_bars, params.hvr_short_window, params.acf_window))

    acf = acf_values[index]
    hvr = hvr_values[index]
    dsp_ratio = dsp_values[index]
    return_slope = slope_values[index]
    missing = (
        (params.use_acf and acf is None)
        or (params.use_hvr and hvr is None)
        or (params.use_dsp and (dsp_ratio is None or return_slope is None))
    )
    if missing:
        return None, {}, False, False, "insufficient_history"

    negative_acf = bool(params.use_acf and acf is not None and acf <= params.acf_block_below)
    compressed_hvr = bool(params.use_hvr and hvr is not None and hvr <= params.hvr_block_below)
    dsp_cycle = bool(
        params.use_dsp
        and dsp_ratio is not None
        and return_slope is not None
        and dsp_ratio >= params.dsp_cycle_ratio_threshold
        and abs(return_slope) <= params.dsp_trend_slope_threshold
    )
    trend_override = bool(
        params.use_acf
        and params.use_hvr
        and acf is not None
        and hvr is not None
        and acf >= params.acf_trend_above
        and hvr >= params.hvr_release_above
    )
    bad_count = sum([negative_acf, compressed_hvr, dsp_cycle])
    required_bad_count = min(2, len(enabled))
    reject_regime = bad_count >= required_bad_count and not trend_override
    score = 100.0 if not reject_regime else -100.0
    components = {
        "lag1_autocorrelation": acf,
        "historical_volatility_ratio": hvr,
        "dsp_cycle_ratio": dsp_ratio,
        "dsp_return_slope": return_slope,
        "negative_acf": 1.0 if negative_acf else 0.0,
        "compressed_hvr": 1.0 if compressed_hvr else 0.0,
        "dsp_cycle_mode": 1.0 if dsp_cycle else 0.0,
        "trend_override": 1.0 if trend_override else 0.0,
        "regime_bad_count": float(bad_count),
        "regime_required_bad_count": float(required_bad_count),
    }
    return score, components, reject_regime, trend_override, None


def _score_goldilocks_gate_at_bar(cache: IndicatorCache, index: int, direction: str, params: GateParameters) -> tuple[float | None, dict[str, float | None], bool, bool, str | None]:
    if index <= 0 or index >= len(cache.bars):
        return None, {}, False, False, "index_out_of_range"
    enabled = [name for name, active in {"er": params.use_er, "vwap": params.use_vwap, "hvp": params.use_hvp}.items() if active]
    if not enabled:
        return None, {}, False, False, "no_enabled_components"

    er = cache.efficiency_ratio(params.er_window)[index]
    vwap = cache.daily_vwap()[index]
    hvp = cache.historical_volatility_percentile(params.hv_window_bars, params.hvp_lookback_bars)[index]
    close = cache.bars[index].close
    vwap_margin = params.vwap_margin_bps / 10_000.0

    missing_components: list[str] = []
    if params.use_er and er is None:
        missing_components.append("er")
    if params.use_vwap and vwap is None:
        missing_components.append("vwap")
    if params.use_hvp and hvp is None:
        missing_components.append("hvp")
    if missing_components:
        return None, {"missing_component_count": float(len(missing_components))}, False, False, "insufficient_goldilocks_history"

    er_pass = bool(not params.use_er or (er is not None and er >= params.er_min))
    if direction == "long":
        vwap_pass = bool(not params.use_vwap or (vwap is not None and close >= vwap * (1.0 + vwap_margin)))
    else:
        vwap_pass = bool(not params.use_vwap or (vwap is not None and close <= vwap * (1.0 - vwap_margin)))
    hvp_pass = bool(not params.use_hvp or (hvp is not None and params.hvp_min <= hvp <= params.hvp_max))
    passed_count = sum([er_pass, vwap_pass, hvp_pass])
    enabled_count = len(enabled)
    accepted = passed_count == enabled_count
    strategic_block = not accepted
    components = {
        "efficiency_ratio": er,
        "daily_vwap": vwap,
        "hvp": hvp,
        "er_pass": 1.0 if er_pass else 0.0,
        "vwap_pass": 1.0 if vwap_pass else 0.0,
        "hvp_pass": 1.0 if hvp_pass else 0.0,
        "goldilocks_passed_count": float(passed_count),
        "goldilocks_enabled_count": float(enabled_count),
        "vwap_distance_bps": None if vwap is None or vwap <= 0 else (close - vwap) / vwap * 10_000.0,
    }
    return 100.0 if accepted else -100.0, components, strategic_block, accepted, None


def score_gate_at_bar(cache: IndicatorCache, index: int, direction: str, params: GateParameters) -> tuple[float | None, dict[str, float | None], bool, bool, str | None]:
    family = _normalize_gate_family(params.gate_family)
    if family == GOLDILOCKS_GATE_FAMILY:
        return _score_goldilocks_gate_at_bar(cache, index, direction, params)
    return _score_legacy_gate_at_bar(cache, index, direction, params)


def decide_signal(cache: IndicatorCache, signal: ChartSignal, params: GateParameters) -> GateDecision:
    gate_score, components, corridor, high_volatility_trend, reason = score_gate_at_bar(cache, signal.signal_index, signal.direction, params)
    if gate_score is None:
        return GateDecision(signal, False, None, reason or "unscored", corridor, high_volatility_trend, components)
    accepted = gate_score > 0
    if accepted and params.gate_family == GOLDILOCKS_GATE_FAMILY:
        reason = "pass_goldilocks"
    elif accepted:
        reason = "pass_trend_override" if high_volatility_trend else "pass"
    elif corridor and params.gate_family == GOLDILOCKS_GATE_FAMILY:
        reason = "goldilocks_block"
    elif corridor:
        reason = "regime_chop_cycle"
    else:
        reason = "regime_block"
    return GateDecision(signal, accepted, gate_score, reason, corridor, high_volatility_trend, components)


def apply_gate(cache: IndicatorCache, signals: list[ChartSignal], params: GateParameters) -> list[GateDecision]:
    return [decide_signal(cache, signal, params) for signal in signals]


def _adjust_entry_price(price: float, direction: str, settings: SimulationSettings) -> float:
    adjustment = settings.entry_slippage_bps / 10000.0
    return price * (1.0 + adjustment) if direction == "long" else price * (1.0 - adjustment)


def _adjust_exit_price(price: float, direction: str, settings: SimulationSettings) -> float:
    adjustment = settings.exit_slippage_bps / 10000.0
    return price * (1.0 - adjustment) if direction == "long" else price * (1.0 + adjustment)


def _trade_pnl(direction: str, entry_price: float, exit_price: float, settings: SimulationSettings) -> tuple[float, float]:
    gross = (exit_price - entry_price) * settings.position_size_btc if direction == "long" else (entry_price - exit_price) * settings.position_size_btc
    fee_quote = ((entry_price + exit_price) * settings.position_size_btc) * (settings.fee_bps / 10000.0)
    return gross - fee_quote, fee_quote


def _natural_exit(bars: list[ChartBar], entry_index: int, direction: str, entry_price: float, settings: SimulationSettings) -> tuple[int, float, str]:
    if settings.exit_mode == "runner":
        return _runner_exit(bars, entry_index, direction, entry_price, settings)
    if settings.exit_mode != "fixed":
        raise ValueError(f"unsupported entry-gate exit_mode: {settings.exit_mode}")
    if entry_index >= len(bars):
        return len(bars) - 1, bars[-1].close, "end_of_data"
    if direction == "long":
        tp_price = entry_price * (1.0 + settings.take_profit_pct)
        sl_price = entry_price * (1.0 - settings.stop_loss_pct)
        for index in range(entry_index, len(bars)):
            hit_sl = bars[index].low <= sl_price
            hit_tp = bars[index].high >= tp_price
            if hit_sl or hit_tp:
                return index, sl_price if hit_sl else tp_price, "sl" if hit_sl else "tp"
    else:
        tp_price = entry_price * (1.0 - settings.take_profit_pct)
        sl_price = entry_price * (1.0 + settings.stop_loss_pct)
        for index in range(entry_index, len(bars)):
            hit_sl = bars[index].high >= sl_price
            hit_tp = bars[index].low <= tp_price
            if hit_sl or hit_tp:
                return index, sl_price if hit_sl else tp_price, "sl" if hit_sl else "tp"
    return len(bars) - 1, bars[-1].close, "end_of_data"


def _runner_exit(bars: list[ChartBar], entry_index: int, direction: str, entry_price: float, settings: SimulationSettings) -> tuple[int, float, str]:
    if entry_index >= len(bars):
        return len(bars) - 1, bars[-1].close, "end_of_data"
    if direction == "long":
        initial_sl = entry_price * (1.0 - settings.stop_loss_pct)
        activation = entry_price * (1.0 + settings.runner_activation_pct)
        profit_floor = entry_price * (1.0 + settings.runner_profit_floor_pct)
        activated = False
        highest_high = entry_price
        trailing_stop = initial_sl
        for index in range(entry_index, len(bars)):
            bar = bars[index]
            if not activated:
                if bar.low <= initial_sl:
                    return index, initial_sl, "sl"
                if bar.high >= activation:
                    activated = True
                    highest_high = max(highest_high, bar.high)
                    trailing_stop = max(initial_sl, profit_floor, highest_high * (1.0 - settings.runner_trailing_stop_pct))
                continue
            if bar.low <= trailing_stop:
                return index, trailing_stop, "runner_trailing_stop"
            highest_high = max(highest_high, bar.high)
            trailing_stop = max(trailing_stop, profit_floor, highest_high * (1.0 - settings.runner_trailing_stop_pct))
    else:
        initial_sl = entry_price * (1.0 + settings.stop_loss_pct)
        activation = entry_price * (1.0 - settings.runner_activation_pct)
        profit_floor = entry_price * (1.0 - settings.runner_profit_floor_pct)
        activated = False
        lowest_low = entry_price
        trailing_stop = initial_sl
        for index in range(entry_index, len(bars)):
            bar = bars[index]
            if not activated:
                if bar.high >= initial_sl:
                    return index, initial_sl, "sl"
                if bar.low <= activation:
                    activated = True
                    lowest_low = min(lowest_low, bar.low)
                    trailing_stop = min(initial_sl, profit_floor, lowest_low * (1.0 + settings.runner_trailing_stop_pct))
                continue
            if bar.high >= trailing_stop:
                return index, trailing_stop, "runner_trailing_stop"
            lowest_low = min(lowest_low, bar.low)
            trailing_stop = min(trailing_stop, profit_floor, lowest_low * (1.0 + settings.runner_trailing_stop_pct))
    return len(bars) - 1, bars[-1].close, "end_of_data"


def simulate_trades(bars: list[ChartBar], decisions: list[GateDecision], settings: SimulationSettings) -> list[SimulatedTrade]:
    accepted_signals = [decision.signal for decision in decisions if decision.accepted]
    natural_exits: dict[int, tuple[int, float, str]] = {}
    for signal in accepted_signals:
        entry_price = _adjust_entry_price(signal.next_open, signal.direction, settings)
        natural_exits[signal.source_row_number] = _natural_exit(bars, signal.entry_index, signal.direction, entry_price, settings)

    trades: list[SimulatedTrade] = []
    open_signal: ChartSignal | None = None
    open_entry_price: float | None = None
    open_natural_exit: tuple[int, float, str] | None = None

    def close_open(exit_index: int, raw_exit_price: float, reason: str) -> None:
        nonlocal open_signal, open_entry_price, open_natural_exit
        if open_signal is None or open_entry_price is None:
            return
        adjusted_exit = _adjust_exit_price(raw_exit_price, open_signal.direction, settings)
        pnl, fee_quote = _trade_pnl(open_signal.direction, open_entry_price, adjusted_exit, settings)
        trades.append(
            SimulatedTrade(
                direction=open_signal.direction,
                entry_index=open_signal.entry_index,
                exit_index=exit_index,
                entry_time_ms=bars[open_signal.entry_index].time_ms,
                exit_time_ms=bars[min(exit_index, len(bars) - 1)].time_ms,
                entry_price=open_entry_price,
                exit_price=adjusted_exit,
                pnl_quote=pnl,
                fee_quote=fee_quote,
                reason=reason,
            )
        )
        open_signal = None
        open_entry_price = None
        open_natural_exit = None

    for signal in accepted_signals:
        if signal.entry_index >= len(bars):
            continue
        if open_signal is not None and open_natural_exit is not None:
            natural_exit_index, natural_exit_price, natural_reason = open_natural_exit
            if natural_exit_index < signal.entry_index:
                close_open(natural_exit_index, natural_exit_price, natural_reason)
        if open_signal is not None:
            if settings.reverse_on_opposite_signal and signal.direction != open_signal.direction:
                close_open(signal.entry_index, signal.next_open, "reverse")
            else:
                continue
        entry_price = _adjust_entry_price(signal.next_open, signal.direction, settings)
        open_signal = signal
        open_entry_price = entry_price
        open_natural_exit = natural_exits[signal.source_row_number]

    if open_signal is not None and open_natural_exit is not None:
        natural_exit_index, natural_exit_price, natural_reason = open_natural_exit
        close_open(natural_exit_index, natural_exit_price, natural_reason)
    return trades


def _profit_factor(pnls: list[float]) -> float | None:
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    if gross_loss <= 0:
        return math.inf if gross_profit > 0 else None
    return gross_profit / gross_loss


def _sortino(returns: list[float]) -> float | None:
    downside = [value for value in returns if value < 0]
    if not returns or len(downside) < 2:
        return None
    mean_return = sum(returns) / len(returns)
    downside_mean = sum(downside) / len(downside)
    downside_deviation = math.sqrt(sum((value - downside_mean) ** 2 for value in downside) / (len(downside) - 1))
    return None if downside_deviation <= 0 else mean_return / downside_deviation


def _max_drawdown_pct(trades: list[SimulatedTrade], capital_quote: float) -> float:
    if capital_quote <= 0:
        return 0.0
    equity = capital_quote
    peak = equity
    max_drawdown = 0.0
    for trade in trades:
        equity += trade.pnl_quote
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, ((peak - equity) / peak) if peak > 0 else 0.0)
    return max_drawdown * 100.0


def _trade_metrics(trades: list[SimulatedTrade], settings: SimulationSettings, *, signal_count: int, accepted_signal_count: int) -> dict[str, Any]:
    pnl_values = [trade.pnl_quote for trade in trades]
    first_notional = abs(trades[0].entry_price * settings.position_size_btc) if trades else settings.capital_quote
    returns = [trade.pnl_quote / max(abs(trade.entry_price * settings.position_size_btc), 1e-12) for trade in trades]
    win_count = sum(1 for trade in trades if trade.pnl_quote > 0)
    retention_rate = accepted_signal_count / signal_count if signal_count else 0.0
    return {
        "signal_count": signal_count,
        "accepted_signal_count": accepted_signal_count,
        "rejected_signal_count": signal_count - accepted_signal_count,
        "retention_rate": retention_rate,
        "rejection_rate": 0.0 if signal_count == 0 else 1.0 - retention_rate,
        "trade_count": len(trades),
        "quote_pnl": sum(pnl_values),
        "return_on_capital_pct": (sum(pnl_values) / settings.capital_quote) * 100.0 if settings.capital_quote else 0.0,
        "return_on_first_trade_notional_pct": (sum(pnl_values) / first_notional) * 100.0 if first_notional else 0.0,
        "winrate": win_count / len(trades) if trades else 0.0,
        "profit_factor": _profit_factor(pnl_values),
        "sortino_ratio": _sortino(returns),
        "max_drawdown_pct": _max_drawdown_pct(trades, settings.capital_quote),
        "fee_quote": sum(trade.fee_quote for trade in trades),
    }


def _equity_curve(trades: list[SimulatedTrade], settings: SimulationSettings) -> list[dict[str, Any]]:
    equity = settings.capital_quote
    rows = [{"trade_index": 0, "time_ms": None, "equity_quote": equity, "pnl_quote": 0.0, "reason": "start"}]
    for index, trade in enumerate(trades, start=1):
        equity += trade.pnl_quote
        rows.append({"trade_index": index, "time_ms": trade.exit_time_ms, "equity_quote": equity, "pnl_quote": trade.pnl_quote, "reason": trade.reason})
    return rows


def _independent_signal_win_map(bars: list[ChartBar], signals: list[ChartSignal], settings: SimulationSettings) -> dict[int, bool]:
    wins: dict[int, bool] = {}
    for signal in signals:
        entry_price = _adjust_entry_price(signal.next_open, signal.direction, settings)
        exit_index, exit_price, _ = _natural_exit(bars, signal.entry_index, signal.direction, entry_price, settings)
        adjusted_exit = _adjust_exit_price(exit_price, signal.direction, settings)
        pnl, _ = _trade_pnl(signal.direction, entry_price, adjusted_exit, settings)
        wins[signal.source_row_number] = pnl > 0 and exit_index >= signal.entry_index
    return wins


def _split_signals(signals: list[ChartSignal], split_count: int = 5) -> list[list[int]]:
    if not signals or split_count <= 0:
        return []
    chunk_size = max(1, math.ceil(len(signals) / split_count))
    return [[signal.source_row_number for signal in signals[index : index + chunk_size]] for index in range(0, len(signals), chunk_size)][:split_count]


def _split_trade_pnls(trades: list[SimulatedTrade], signals_by_row: dict[int, ChartSignal], splits: list[list[int]]) -> list[float]:
    entry_index_to_row = {signal.entry_index: row for row, signal in signals_by_row.items()}
    pnl_by_entry_row: dict[int, float] = {}
    for trade in trades:
        row = entry_index_to_row.get(trade.entry_index)
        if row is not None:
            pnl_by_entry_row[row] = pnl_by_entry_row.get(row, 0.0) + trade.pnl_quote
    return [sum(pnl_by_entry_row.get(row, 0.0) for row in split) for split in splits]


def _decision_quality(decisions: list[GateDecision], independent_wins: dict[int, bool]) -> dict[str, Any]:
    rejected = [decision for decision in decisions if not decision.accepted]
    corridor = [decision for decision in decisions if decision.corridor]
    trend_override = [decision for decision in decisions if decision.high_volatility_trend]
    missing_rejections = [
        decision
        for decision in rejected
        if decision.reason in {"insufficient_history", "insufficient_goldilocks_history"} or decision.reason.startswith("insufficient_")
    ]
    strategic_rejections = [decision for decision in rejected if decision not in missing_rejections]
    missed_winners = [decision for decision in rejected if independent_wins.get(decision.signal.source_row_number, False)]
    trend_override_retention_rate = (
        sum(1 for decision in trend_override if decision.accepted) / len(trend_override) if trend_override else 1.0
    )
    signal_count = len(decisions)
    return {
        "missed_winner_rate": len(missed_winners) / len(rejected) if rejected else 0.0,
        "missing_component_rejection_count": len(missing_rejections),
        "missing_component_rate": len(missing_rejections) / signal_count if signal_count else 0.0,
        "strategic_rejection_count": len(strategic_rejections),
        "strategic_rejection_rate": len(strategic_rejections) / signal_count if signal_count else 0.0,
        "corridor_signal_count": len(corridor),
        "corridor_rejection_rate": sum(1 for decision in corridor if not decision.accepted) / len(corridor) if corridor else 0.0,
        "trend_override_signal_count": len(trend_override),
        "trend_override_retention_rate": trend_override_retention_rate,
        "high_volatility_trend_signal_count": len(trend_override),
        "high_volatility_trend_retention_rate": trend_override_retention_rate,
    }


def _reason_counts(decisions: list[GateDecision]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for decision in decisions:
        counts[decision.reason] = counts.get(decision.reason, 0) + 1
    return [{"reason": reason, "count": count} for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _trade_reason_counts(trades: list[SimulatedTrade]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for trade in trades:
        counts[trade.reason] = counts.get(trade.reason, 0) + 1
    return [{"reason": reason, "count": count} for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _downsample_bars_for_chart(bars: list[ChartBar], max_points: int) -> list[dict[str, Any]]:
    if max_points <= 0 or len(bars) <= max_points:
        return [
            {"bar_index": index, "time_ms": bar.time_ms, "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close}
            for index, bar in enumerate(bars)
        ]
    step = max(1, math.ceil(len(bars) / max_points))
    sampled: list[dict[str, Any]] = []
    for start in range(0, len(bars), step):
        bucket = bars[start : start + step]
        if not bucket:
            continue
        first = bucket[0]
        sampled.append(
            {
                "bar_index": start,
                "time_ms": first.time_ms,
                "open": first.open,
                "high": max(bar.high for bar in bucket),
                "low": min(bar.low for bar in bucket),
                "close": bucket[-1].close,
            }
        )
    return sampled


def _decision_markers(decisions: list[GateDecision], *, limit: int | None = None) -> list[dict[str, Any]]:
    selected = decisions if limit is None else decisions[:limit]
    return [
        {
            "signal_index": decision.signal.signal_index,
            "entry_index": decision.signal.entry_index,
            "time_ms": decision.signal.time_ms,
            "direction": decision.signal.direction,
            "marker_price": decision.signal.marker_price,
            "accepted": decision.accepted,
            "reason": decision.reason,
            "gate_score": decision.gate_score,
            "corridor": decision.corridor,
            "high_volatility_trend": decision.high_volatility_trend,
            "components": decision.components,
            "source_row_number": decision.signal.source_row_number,
        }
        for decision in selected
    ]


def _trade_markers(trades: list[SimulatedTrade]) -> list[dict[str, Any]]:
    return [
        {
            "direction": trade.direction,
            "entry_index": trade.entry_index,
            "exit_index": trade.exit_index,
            "entry_time_ms": trade.entry_time_ms,
            "exit_time_ms": trade.exit_time_ms,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "pnl_quote": trade.pnl_quote,
            "reason": trade.reason,
        }
        for trade in trades
    ]


def _metric_delta(filtered: dict[str, Any], baseline: dict[str, Any], key: str) -> float | None:
    filtered_value = filtered.get(key)
    baseline_value = baseline.get(key)
    if filtered_value is None or baseline_value is None:
        return None
    try:
        return float(filtered_value) - float(baseline_value)
    except (TypeError, ValueError):
        return None


def analyze_entry_gate_configuration(
    *,
    path: Path,
    symbol: str,
    strategy_version: str,
    params: GateParameters,
    settings: SimulationSettings | None = None,
    gate_family: str | None = None,
    ohlcv_cache_policy: str | None = None,
    ohlcv_cache_dir: Path | None = None,
    max_chart_points: int = 1200,
    max_visible_decisions: int | None = None,
) -> EntryGateAnalysisResult:
    settings = settings or preferred_research_exit_settings()
    family = _normalize_gate_family(gate_family or params.gate_family)
    if params.gate_family != family:
        params = GateParameters(**{**asdict(params), "gate_family": family})
    bars, signals, metadata = load_chart_export(path, symbol=symbol)
    if not signals:
        raise ValueError("TradingView chart export has no Buy/Sell candidate signals")
    bars, ohlcv_coverage = prepare_ohlcv_enriched_bars(
        bars,
        symbol=symbol,
        gate_family=family,
        ohlcv_cache_policy=ohlcv_cache_policy,
        ohlcv_cache_dir=ohlcv_cache_dir,
        required_warmup_bars=_required_goldilocks_warmup_bars(params),
        hvp_coverage_window_bars=params.hv_window_bars,
        hvp_coverage_lookback_bars=params.hvp_lookback_bars,
    )
    cache = IndicatorCache(bars)
    independent_wins = _independent_signal_win_map(bars, signals, settings)
    split_rows = _split_signals(signals, split_count=5)
    signals_by_row = {signal.source_row_number: signal for signal in signals}

    baseline_metrics, baseline_decisions, baseline_trades = _evaluate_params(
        bars=bars,
        signals=signals,
        cache=cache,
        params=None,
        settings=settings,
        independent_wins=independent_wins,
        split_rows=split_rows,
        signals_by_row=signals_by_row,
    )
    filtered_metrics, filtered_decisions, filtered_trades = _evaluate_params(
        bars=bars,
        signals=signals,
        cache=cache,
        params=params,
        settings=settings,
        independent_wins=independent_wins,
        split_rows=split_rows,
        signals_by_row=signals_by_row,
    )

    payload = {
        "entry_gate_research_version": ENTRY_GATE_RESEARCH_VERSION,
        "gate_family": family,
        "strategy_version": strategy_version,
        "symbol": symbol.upper(),
        "source_metadata": metadata,
        "ohlcv_coverage": ohlcv_coverage.as_dict() if ohlcv_coverage else None,
        "parameters": asdict(params),
        "simulation_settings": asdict(settings),
        "baseline": _jsonable_record(baseline_metrics),
        "filtered": _jsonable_record(filtered_metrics),
        "delta": {
            "return_on_capital_pct": _metric_delta(filtered_metrics, baseline_metrics, "return_on_capital_pct"),
            "profit_factor": _metric_delta(filtered_metrics, baseline_metrics, "profit_factor"),
            "winrate": _metric_delta(filtered_metrics, baseline_metrics, "winrate"),
            "max_drawdown_pct": _metric_delta(filtered_metrics, baseline_metrics, "max_drawdown_pct"),
            "trade_count": _metric_delta(filtered_metrics, baseline_metrics, "trade_count"),
            "rejection_rate": _metric_delta(filtered_metrics, baseline_metrics, "rejection_rate"),
            "sortino_ratio": _metric_delta(filtered_metrics, baseline_metrics, "sortino_ratio"),
        },
        "selection": {
            "passes_rejection_target": 0.30 <= float(filtered_metrics["rejection_rate"]) <= 0.50,
            "passes_selection": _passes_selection(filtered_metrics, baseline_metrics),
            "selection_score": _candidate_score(filtered_metrics, baseline_metrics),
        },
        "decision_breakdown": {
            "filtered_reason_counts": _reason_counts(filtered_decisions),
            "baseline_reason_counts": _reason_counts(baseline_decisions),
            "filtered_trade_reason_counts": _trade_reason_counts(filtered_trades),
            "baseline_trade_reason_counts": _trade_reason_counts(baseline_trades),
        },
        "chart": {
            "bars": _downsample_bars_for_chart(bars, max_chart_points),
            "filtered_decisions": _decision_markers(filtered_decisions, limit=max_visible_decisions),
            "baseline_decisions": _decision_markers(baseline_decisions, limit=max_visible_decisions),
            "filtered_trades": _trade_markers(filtered_trades),
            "baseline_trades": _trade_markers(baseline_trades),
            "baseline_equity": _equity_curve(baseline_trades, settings),
            "filtered_equity": _equity_curve(filtered_trades, settings),
        },
        "observe_only": True,
    }
    return EntryGateAnalysisResult(payload=payload)


def candidate_grid() -> list[GateParameters]:
    return [
        GateParameters(
            acf_window=acf_window,
            acf_block_below=acf_block_below,
            acf_trend_above=acf_trend_above,
            hvr_short_window=hvr_short_window,
            hvr_long_window=hvr_long_window,
            hvr_block_below=hvr_block_below,
            hvr_release_above=hvr_release_above,
            dsp_min_cycle_bars=dsp_min_cycle_bars,
            dsp_max_cycle_bars=dsp_max_cycle_bars,
            dsp_cycle_ratio_threshold=dsp_cycle_ratio_threshold,
            dsp_trend_slope_threshold=dsp_trend_slope_threshold,
        )
        for (
            acf_window,
            acf_block_below,
            acf_trend_above,
            hvr_short_window,
            hvr_long_window,
            hvr_block_below,
            hvr_release_above,
            dsp_min_cycle_bars,
            dsp_max_cycle_bars,
            dsp_cycle_ratio_threshold,
            dsp_trend_slope_threshold,
        ) in itertools.product(
            [10, 12, 14, 16, 20],
            [-0.30, -0.25, -0.20, -0.15],
            [0.05, 0.10, 0.15, 0.20],
            [4, 6, 8, 10],
            [40, 50, 60, 80],
            [0.40, 0.50, 0.60],
            [0.70, 0.75, 0.85],
            [4, 6],
            [12, 16, 24],
            [0.45, 0.55, 0.65],
            [0.20, 0.25, 0.35],
        )
    ]


def default_visual_gate_parameters() -> GateParameters:
    """Best current compact default for interactive visual analysis.

    This is intentionally based on the latest bounded optimizer result rather
    than the full heavy grid. The UI is for manual inspection and iteration, so
    it needs a stable starting point grounded in current local research.
    """
    return GateParameters(
        gate_family=LEGACY_GATE_FAMILY,
        acf_window=14,
        acf_block_below=-0.20,
        acf_trend_above=0.10,
        hvr_short_window=6,
        hvr_long_window=60,
        hvr_block_below=0.50,
        hvr_release_above=0.75,
        dsp_min_cycle_bars=4,
        dsp_max_cycle_bars=16,
        dsp_cycle_ratio_threshold=0.55,
        dsp_trend_slope_threshold=0.25,
        use_acf=True,
        use_hvr=True,
        use_dsp=True,
    )


def _normalize_allowed_components(
    allowed_components: tuple[str, ...] | list[str] | None,
    gate_family: str = LEGACY_GATE_FAMILY,
) -> tuple[str, ...] | None:
    if allowed_components is None:
        return None
    family = _normalize_gate_family(gate_family)
    valid_components = GOLDILOCKS_COMPONENTS if family == GOLDILOCKS_GATE_FAMILY else GATE_COMPONENTS
    normalized = tuple(dict.fromkeys(component.strip().lower() for component in allowed_components if component.strip()))
    unknown = sorted(set(normalized) - set(valid_components))
    if unknown:
        raise ValueError(f"unknown gate components: {', '.join(unknown)}")
    if not normalized:
        raise ValueError("at least one optimizer component must be selected")
    return normalized


def _optimizer_components(
    allowed_components: tuple[str, ...] | list[str] | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
) -> tuple[str, ...]:
    family = _normalize_gate_family(gate_family)
    return _normalize_allowed_components(allowed_components, family) or (
        _DEFAULT_GOLDILOCKS_COMPONENTS if family == GOLDILOCKS_GATE_FAMILY else _DEFAULT_OPTIMIZER_COMPONENTS
    )


def _component_flags(active_components: tuple[str, ...], gate_family: str = LEGACY_GATE_FAMILY) -> dict[str, bool]:
    family = _normalize_gate_family(gate_family)
    active = set(active_components)
    if family == GOLDILOCKS_GATE_FAMILY:
        flags = {f"use_{component}": component in active for component in GOLDILOCKS_COMPONENTS}
        flags.update({f"use_{component}": False for component in GATE_COMPONENTS})
        return flags
    flags = {f"use_{component}": component in active for component in GATE_COMPONENTS}
    flags.update({f"use_{component}": False for component in GOLDILOCKS_COMPONENTS})
    return flags


def _heavy_parameter_values(active_components: tuple[str, ...], gate_family: str = LEGACY_GATE_FAMILY) -> dict[str, list[int | float]]:
    family = _normalize_gate_family(gate_family)
    active = set(active_components)

    def values_for(name: str, enabled: bool) -> list[int | float]:
        return list(_HEAVY_GRID_RANGES[name] if enabled else [_HEAVY_GRID_DEFAULTS[name]])

    if family == GOLDILOCKS_GATE_FAMILY:
        return {
            "er_window": values_for("er_window", "er" in active),
            "er_min": values_for("er_min", "er" in active),
            "vwap_margin_bps": values_for("vwap_margin_bps", "vwap" in active),
            "hv_window_bars": values_for("hv_window_bars", "hvp" in active),
            "hvp_lookback_bars": values_for("hvp_lookback_bars", "hvp" in active),
            "hvp_min": values_for("hvp_min", "hvp" in active),
            "hvp_max": values_for("hvp_max", "hvp" in active),
        }
    return {
        "acf_window": values_for("acf_window", "acf" in active),
        "acf_block_below": values_for("acf_block_below", "acf" in active),
        "acf_trend_above": values_for("acf_trend_above", "acf" in active),
        "hvr_short_window": values_for("hvr_short_window", "hvr" in active),
        "hvr_long_window": values_for("hvr_long_window", "hvr" in active),
        "hvr_block_below": values_for("hvr_block_below", "hvr" in active),
        "hvr_release_above": values_for("hvr_release_above", "hvr" in active),
        "dsp_min_cycle_bars": values_for("dsp_min_cycle_bars", "dsp" in active),
        "dsp_max_cycle_bars": values_for("dsp_max_cycle_bars", "dsp" in active),
        "dsp_cycle_ratio_threshold": values_for("dsp_cycle_ratio_threshold", "dsp" in active),
        "dsp_trend_slope_threshold": values_for("dsp_trend_slope_threshold", "dsp" in active),
    }


def iter_heavy_candidate_grid(
    allowed_components: tuple[str, ...] | list[str] | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
) -> Iterator[GateParameters]:
    family = _normalize_gate_family(gate_family)
    active_components = _optimizer_components(allowed_components, family)
    values = _heavy_parameter_values(active_components, family)
    names = list(values.keys())
    for candidate_values in itertools.product(*(values[name] for name in names)):
        yield _make_gate_parameters(
            active_components=active_components,
            gate_family=family,
            **dict(zip(names, candidate_values)),
        )


def _make_gate_parameters(*, active_components: tuple[str, ...], gate_family: str = LEGACY_GATE_FAMILY, **values: int | float) -> GateParameters:
    family = _normalize_gate_family(gate_family)
    if family == GOLDILOCKS_GATE_FAMILY:
        return GateParameters(
            gate_family=family,
            er_window=int(values["er_window"]),
            er_min=float(values["er_min"]),
            vwap_margin_bps=float(values["vwap_margin_bps"]),
            hv_window_bars=int(values["hv_window_bars"]),
            hvp_lookback_bars=int(values["hvp_lookback_bars"]),
            hvp_min=float(values["hvp_min"]),
            hvp_max=float(values["hvp_max"]),
            **_component_flags(active_components, family),
        )
    return GateParameters(
        gate_family=family,
        acf_window=int(values["acf_window"]),
        acf_block_below=float(values["acf_block_below"]),
        acf_trend_above=float(values["acf_trend_above"]),
        hvr_short_window=int(values["hvr_short_window"]),
        hvr_long_window=int(values["hvr_long_window"]),
        hvr_block_below=float(values["hvr_block_below"]),
        hvr_release_above=float(values["hvr_release_above"]),
        dsp_min_cycle_bars=int(values["dsp_min_cycle_bars"]),
        dsp_max_cycle_bars=int(values["dsp_max_cycle_bars"]),
        dsp_cycle_ratio_threshold=float(values["dsp_cycle_ratio_threshold"]),
        dsp_trend_slope_threshold=float(values["dsp_trend_slope_threshold"]),
        **_component_flags(active_components, family),
    )


def _gate_candidate_from_linear_index(active_components: tuple[str, ...], linear_index: int, gate_family: str = LEGACY_GATE_FAMILY) -> GateParameters:
    family = _normalize_gate_family(gate_family)
    values = _heavy_parameter_values(active_components, family)
    names = list(values.keys())
    selected: dict[str, int | float] = {}
    remaining = linear_index
    for name in reversed(names):
        candidates = values[name]
        selected[name] = candidates[remaining % len(candidates)]
        remaining //= len(candidates)
    return _make_gate_parameters(active_components=active_components, gate_family=family, **selected)


def _gate_candidate_for_latin_sample(
    active_components: tuple[str, ...],
    sample_index: int,
    sample_count: int,
    gate_family: str = LEGACY_GATE_FAMILY,
) -> GateParameters:
    family = _normalize_gate_family(gate_family)
    values = _heavy_parameter_values(active_components, family)
    multipliers = {
        "acf_window": 1,
        "acf_block_below": 3,
        "acf_trend_above": 5,
        "hvr_short_window": 7,
        "hvr_long_window": 11,
        "hvr_block_below": 13,
        "hvr_release_above": 17,
        "dsp_min_cycle_bars": 19,
        "dsp_max_cycle_bars": 23,
        "dsp_cycle_ratio_threshold": 29,
        "dsp_trend_slope_threshold": 31,
        "er_window": 37,
        "er_min": 41,
        "vwap_margin_bps": 43,
        "hv_window_bars": 47,
        "hvp_lookback_bars": 53,
        "hvp_min": 59,
        "hvp_max": 61,
    }
    selected: dict[str, int | float] = {}
    denominator = max(sample_count - 1, 1)
    for key, candidates in values.items():
        if len(candidates) == 1:
            selected[key] = candidates[0]
            continue
        rotated_index = (sample_index * multipliers[key]) % sample_count
        candidate_index = min(len(candidates) - 1, math.floor((rotated_index * len(candidates)) / denominator))
        selected[key] = candidates[candidate_index]
    return _make_gate_parameters(active_components=active_components, gate_family=family, **selected)


def _sampled_linear_indices(full_count: int, sample_count: int) -> Iterator[int]:
    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    if sample_count >= full_count:
        yield from range(full_count)
        return
    # Use a deterministic coprime stride so sampled runs cover the full
    # mixed-radix grid without duplicates or first-block bias.
    stride = max(1, full_count // sample_count)
    while math.gcd(stride, full_count) != 1:
        stride += 1
    for sample_index in range(sample_count):
        yield (sample_index * stride) % full_count


def sampled_heavy_candidate_grid(
    allowed_components: tuple[str, ...] | list[str] | None = None,
    max_candidates: int | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
) -> Iterator[GateParameters]:
    family = _normalize_gate_family(gate_family)
    active_components = _optimizer_components(allowed_components, family)
    full_count = heavy_candidate_grid_count(active_components, family)
    if max_candidates is None or max_candidates >= full_count:
        yield from iter_heavy_candidate_grid(active_components, family)
        return
    if max_candidates <= 0:
        raise ValueError("max_candidates must be positive when provided")
    seen: set[str] = set()
    # First pass: spread every parameter dimension independently so small
    # samples still touch the full configured range for each active component.
    for sample_index in range(max_candidates):
        candidate = _gate_candidate_for_latin_sample(active_components, sample_index, max_candidates, family)
        key = candidate.key()
        if key in seen:
            continue
        seen.add(key)
        yield candidate
    # Fallback: guarantee the requested unique count when Latin sampling
    # collides on low-cardinality component combinations.
    if len(seen) < max_candidates:
        for linear_index in _sampled_linear_indices(full_count, max_candidates):
            candidate = _gate_candidate_from_linear_index(active_components, linear_index, family)
            key = candidate.key()
            if key in seen:
                continue
            seen.add(key)
            yield candidate
            if len(seen) >= max_candidates:
                break


def heavy_candidate_grid(
    allowed_components: tuple[str, ...] | list[str] | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
) -> Iterator[GateParameters]:
    return iter_heavy_candidate_grid(allowed_components, gate_family)


def heavy_candidate_grid_count(
    allowed_components: tuple[str, ...] | list[str] | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
) -> int:
    family = _normalize_gate_family(gate_family)
    active_components = _optimizer_components(allowed_components, family)
    values = _heavy_parameter_values(active_components, family)
    count = 1
    for candidates in values.values():
        count *= len(candidates)
    return count


def heavy_candidate_count(
    allowed_components: tuple[str, ...] | list[str] | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
) -> int:
    return heavy_candidate_grid_count(allowed_components, gate_family)


def fixed_research_exit_settings() -> SimulationSettings:
    """Predetermined fixed-exit profile for gate research.

    Exit search is intentionally out of scope for the current entry-gate
    research pass. This fixed profile keeps the assumed 0.5% stop while
    allowing a wider 1.5% take-profit from the earlier smoke experiments.
    """
    return SimulationSettings(
        exit_mode="fixed",
        take_profit_pct=0.015,
        stop_loss_pct=0.005,
        position_size_btc=0.01,
        capital_quote=1000.0,
        entry_slippage_bps=5.0,
        exit_slippage_bps=5.0,
        fee_bps=5.0,
    )


def optimizer_exit_settings(exit_profile: str = "runner") -> SimulationSettings:
    normalized = exit_profile.strip().lower()
    if normalized == "runner":
        return preferred_research_exit_settings()
    if normalized == "fixed":
        return fixed_research_exit_settings()
    raise ValueError("exit_profile must be one of: runner, fixed")


def _exit_profile_name(settings: SimulationSettings) -> str:
    if settings.exit_mode == "runner":
        return "runner"
    if settings.exit_mode == "fixed":
        return "fixed"
    return str(settings.exit_mode)


def preferred_research_exit_settings() -> SimulationSettings:
    """Single runner setup for preflight gate screening.

    The values come from the prior runner experiment intent: keep the initial
    0.5% risk, activate after a 0.5% favorable move, trail by 0.3%, and keep a
    small 0.1% profit floor. This keeps preflight focused on gate signal value,
    not exit overfitting.
    """
    return SimulationSettings(
        exit_mode="runner",
        take_profit_pct=0.005,
        stop_loss_pct=0.005,
        runner_activation_pct=0.005,
        runner_trailing_stop_pct=0.003,
        runner_profit_floor_pct=0.001,
        position_size_btc=0.01,
        capital_quote=1000.0,
        entry_slippage_bps=5.0,
        exit_slippage_bps=5.0,
        fee_bps=5.0,
    )


def _single_component_mask(component: str, gate_family: str = LEGACY_GATE_FAMILY) -> dict[str, bool]:
    family = _normalize_gate_family(gate_family)
    keys = list(GOLDILOCKS_COMPONENTS if family == GOLDILOCKS_GATE_FAMILY else GATE_COMPONENTS)
    if component not in keys:
        raise ValueError(f"unknown gate component: {component}")
    return {f"use_{key}": key == component for key in keys}


def single_component_candidate_grid(component: str, gate_family: str = LEGACY_GATE_FAMILY) -> Iterator[GateParameters]:
    yield from iter_heavy_candidate_grid((component,), gate_family)


def preflight_component_grid(gate_family: str = LEGACY_GATE_FAMILY) -> Iterator[tuple[str, GateParameters]]:
    family = _normalize_gate_family(gate_family)
    for component in (GOLDILOCKS_COMPONENTS if family == GOLDILOCKS_GATE_FAMILY else GATE_COMPONENTS):
        for params in single_component_candidate_grid(component, family):
            yield component, params


def _evaluate_params(
    *,
    bars: list[ChartBar],
    signals: list[ChartSignal],
    cache: IndicatorCache,
    params: GateParameters | None,
    settings: SimulationSettings,
    independent_wins: dict[int, bool],
    split_rows: list[list[int]],
    signals_by_row: dict[int, ChartSignal],
) -> tuple[dict[str, Any], list[GateDecision], list[SimulatedTrade]]:
    decisions = (
        [
            GateDecision(signal, True, None, "baseline_no_gate", False, False, {})
            for signal in signals
        ]
        if params is None
        else apply_gate(cache, signals, params)
    )
    trades = simulate_trades(bars, decisions, settings)
    metrics = _trade_metrics(trades, settings, signal_count=len(signals), accepted_signal_count=sum(1 for decision in decisions if decision.accepted))
    metrics.update(_decision_quality(decisions, independent_wins))
    metrics["split_pnls"] = _split_trade_pnls(trades, signals_by_row, split_rows)
    return metrics, decisions, trades


def _candidate_score(candidate: dict[str, Any], baseline: dict[str, Any]) -> float:
    profit_factor = float(candidate.get("profit_factor") or 0.0)
    sortino = float(candidate.get("sortino_ratio") or 0.0)
    rejection_rate = float(candidate["rejection_rate"])
    return (
        float(candidate["return_on_capital_pct"]) * 2.0
        + (profit_factor - float(baseline.get("profit_factor") or 0.0)) * 10.0
        + sortino * 5.0
        - abs(rejection_rate - 0.40) * 20.0
        - max(0.0, rejection_rate - 0.50) * 100.0
        - max(0.0, 0.75 - float(candidate.get("high_volatility_trend_retention_rate", 1.0))) * 30.0
    )


def _passes_selection(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    split_pnls = candidate.get("split_pnls") or []
    baseline_split_pnls = baseline.get("split_pnls") or []
    improved_splits = sum(1 for candidate_pnl, baseline_pnl in zip(split_pnls, baseline_split_pnls) if float(candidate_pnl) > float(baseline_pnl))
    return (
        0.30 <= float(candidate["rejection_rate"]) <= 0.50
        and float(candidate["return_on_capital_pct"]) > float(baseline["return_on_capital_pct"])
        and float(candidate.get("profit_factor") or 0.0) > float(baseline.get("profit_factor") or 0.0)
        and float(candidate.get("sortino_ratio") or 0.0) >= float(baseline.get("sortino_ratio") or 0.0)
        and improved_splits >= 3
        and float(candidate.get("high_volatility_trend_retention_rate", 1.0)) >= 0.75
    )


def _optimizer_selection_key(record: dict[str, Any]) -> tuple[int, float]:
    return (1 if record["passes_selection"] else 0, float(record["selection_score"]))


def _objective_value(record: dict[str, Any], key: str) -> float:
    value = record.get(key)
    if value is None:
        return -math.inf
    numeric = float(value)
    if math.isnan(numeric):
        return -math.inf
    return numeric


def _optimizer_return_key(record: dict[str, Any]) -> tuple[float, float, float]:
    return (
        _objective_value(record, "return_on_capital_pct"),
        _objective_value(record, "profit_factor"),
        -_objective_value(record, "max_drawdown_pct"),
    )


def _optimizer_profit_factor_key(record: dict[str, Any]) -> tuple[float, float, float]:
    return (
        _objective_value(record, "profit_factor"),
        _objective_value(record, "return_on_capital_pct"),
        -_objective_value(record, "max_drawdown_pct"),
    )


def _optimizer_winrate_key(record: dict[str, Any]) -> tuple[float, float, float]:
    return (
        _objective_value(record, "winrate"),
        _objective_value(record, "return_on_capital_pct"),
        _objective_value(record, "profit_factor"),
    )


def _init_optimizer_worker(bars: list[ChartBar], signals: list[ChartSignal]) -> None:
    global _OPTIMIZER_BARS, _OPTIMIZER_SIGNALS, _OPTIMIZER_CACHE, _OPTIMIZER_SPLIT_ROWS, _OPTIMIZER_SIGNALS_BY_ROW
    _OPTIMIZER_BARS = bars
    _OPTIMIZER_SIGNALS = signals
    _OPTIMIZER_CACHE = IndicatorCache(bars)
    _OPTIMIZER_SPLIT_ROWS = _split_signals(signals, split_count=5)
    _OPTIMIZER_SIGNALS_BY_ROW = {signal.source_row_number: signal for signal in signals}


def _optimizer_worker_state() -> tuple[list[ChartBar], list[ChartSignal], IndicatorCache, list[list[int]], dict[int, ChartSignal]]:
    if (
        _OPTIMIZER_BARS is None
        or _OPTIMIZER_SIGNALS is None
        or _OPTIMIZER_CACHE is None
        or _OPTIMIZER_SPLIT_ROWS is None
        or _OPTIMIZER_SIGNALS_BY_ROW is None
    ):
        raise RuntimeError("entry-gate optimizer worker was not initialized")
    return _OPTIMIZER_BARS, _OPTIMIZER_SIGNALS, _OPTIMIZER_CACHE, _OPTIMIZER_SPLIT_ROWS, _OPTIMIZER_SIGNALS_BY_ROW


def _rank_and_trim_records(records: list[dict[str, Any]], top_n: int, key_fn=_optimizer_selection_key) -> list[dict[str, Any]]:
    return sorted(records, key=key_fn, reverse=True)[:top_n]


def _evaluate_gate_record(
    *,
    bars: list[ChartBar],
    signals: list[ChartSignal],
    cache: IndicatorCache,
    split_rows: list[list[int]],
    signals_by_row: dict[int, ChartSignal],
    settings: SimulationSettings,
    params: GateParameters,
    baseline_metrics: dict[str, Any],
    independent_wins: dict[int, bool],
    component: str | None = None,
) -> dict[str, Any]:
    metrics, _, _ = _evaluate_params(
        bars=bars,
        signals=signals,
        cache=cache,
        params=params,
        settings=settings,
        independent_wins=independent_wins,
        split_rows=split_rows,
        signals_by_row=signals_by_row,
    )
    record = {**asdict(params), **metrics}
    record["param_key"] = params.key()
    record["exit_key"] = _settings_key(settings)
    record["exit_settings"] = asdict(settings)
    record["passes_rejection_target"] = 0.30 <= float(metrics["rejection_rate"]) <= 0.50
    record["passes_selection"] = _passes_selection(metrics, baseline_metrics)
    record["selection_score"] = _candidate_score(metrics, baseline_metrics)
    record["baseline_for_exit"] = baseline_metrics
    if component is not None:
        record["component"] = component
    return record


def _evaluate_optimizer_gate_chunk_task(payload: tuple[SimulationSettings, list[GateParameters], int]) -> dict[str, Any]:
    settings, gate_candidates, top_n = payload
    bars, signals, cache, split_rows, signals_by_row = _optimizer_worker_state()
    independent_wins = _independent_signal_win_map(bars, signals, settings)
    baseline_metrics, _, _ = _evaluate_params(
        bars=bars,
        signals=signals,
        cache=cache,
        params=None,
        settings=settings,
        independent_wins=independent_wins,
        split_rows=split_rows,
        signals_by_row=signals_by_row,
    )
    top_records: list[dict[str, Any]] = []
    top_return_records: list[dict[str, Any]] = []
    top_profit_factor_records: list[dict[str, Any]] = []
    top_winrate_records: list[dict[str, Any]] = []
    evaluated_count = 0
    full_pass_count = 0
    rejection_target_count = 0
    for params in gate_candidates:
        record = _evaluate_gate_record(
            bars=bars,
            signals=signals,
            cache=cache,
            split_rows=split_rows,
            signals_by_row=signals_by_row,
            settings=settings,
            params=params,
            baseline_metrics=baseline_metrics,
            independent_wins=independent_wins,
        )
        evaluated_count += 1
        rejection_target_count += 1 if record["passes_rejection_target"] else 0
        full_pass_count += 1 if record["passes_selection"] else 0
        top_records.append(record)
        top_records = _rank_and_trim_records(top_records, top_n)
        top_return_records.append(record)
        top_return_records = _rank_and_trim_records(top_return_records, top_n, _optimizer_return_key)
        top_profit_factor_records.append(record)
        top_profit_factor_records = _rank_and_trim_records(top_profit_factor_records, top_n, _optimizer_profit_factor_key)
        top_winrate_records.append(record)
        top_winrate_records = _rank_and_trim_records(top_winrate_records, top_n, _optimizer_winrate_key)
    return {
        "top_records": top_records,
        "top_return_records": top_return_records,
        "top_profit_factor_records": top_profit_factor_records,
        "top_winrate_records": top_winrate_records,
        "evaluated_count": evaluated_count,
        "candidate_rejection_target_count": rejection_target_count,
        "candidate_full_pass_count": full_pass_count,
    }


def _gate_candidate_chunks(gate_iterable: Iterator[GateParameters], chunk_size: int) -> Iterator[list[GateParameters]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    while True:
        chunk = list(itertools.islice(gate_iterable, chunk_size))
        if not chunk:
            return
        yield chunk


def run_entry_gate_research(
    *,
    path: Path,
    symbol: str,
    strategy_version: str,
    output_dir: Path,
    settings: SimulationSettings | None = None,
    max_candidates: int | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
    allowed_components: tuple[str, ...] | list[str] | None = None,
    ohlcv_cache_policy: str | None = None,
) -> EntryGateResearchResult:
    settings = settings or SimulationSettings()
    family = _normalize_gate_family(gate_family)
    normalized_allowed_components = _normalize_allowed_components(allowed_components, family)
    active_optimizer_components = _optimizer_components(normalized_allowed_components, family)
    bars, signals, metadata = load_chart_export(path, symbol=symbol)
    if not signals:
        raise ValueError("TradingView chart export has no Buy/Sell candidate signals")
    bars, ohlcv_coverage = prepare_ohlcv_enriched_bars(
        bars,
        symbol=symbol,
        gate_family=family,
        ohlcv_cache_policy=ohlcv_cache_policy,
    )
    cache = IndicatorCache(bars)
    independent_wins = _independent_signal_win_map(bars, signals, settings)
    split_rows = _split_signals(signals, split_count=5)
    signals_by_row = {signal.source_row_number: signal for signal in signals}
    baseline_metrics, _, baseline_trades = _evaluate_params(
        bars=bars,
        signals=signals,
        cache=cache,
        params=None,
        settings=settings,
        independent_wins=independent_wins,
        split_rows=split_rows,
        signals_by_row=signals_by_row,
    )

    rows: list[dict[str, Any]] = []
    best_record: dict[str, Any] | None = None
    best_decisions: list[GateDecision] | None = None
    best_trades: list[SimulatedTrade] | None = None
    best_selection_key: tuple[int, float] = (-1, -math.inf)
    full_pass_count = 0
    rejection_target_count = 0
    full_gate_candidate_count = heavy_candidate_grid_count(normalized_allowed_components, family)
    gate_candidate_count = full_gate_candidate_count if max_candidates is None else min(max_candidates, full_gate_candidate_count)
    if gate_candidate_count <= 0:
        raise ValueError("entry-gate research needs at least one gate candidate")
    grid = sampled_heavy_candidate_grid(normalized_allowed_components, max_candidates=max_candidates, gate_family=family)
    for params in grid:
        metrics, decisions, trades = _evaluate_params(
            bars=bars,
            signals=signals,
            cache=cache,
            params=params,
            settings=settings,
            independent_wins=independent_wins,
            split_rows=split_rows,
            signals_by_row=signals_by_row,
        )
        record = {**asdict(params), **metrics}
        record["param_key"] = params.key()
        record["passes_rejection_target"] = 0.30 <= float(metrics["rejection_rate"]) <= 0.50
        record["passes_selection"] = _passes_selection(metrics, baseline_metrics)
        record["selection_score"] = _candidate_score(metrics, baseline_metrics)
        rejection_target_count += 1 if record["passes_rejection_target"] else 0
        full_pass_count += 1 if record["passes_selection"] else 0
        selection_key = (1 if record["passes_selection"] else 0, float(record["selection_score"]))
        if selection_key > best_selection_key:
            best_selection_key = selection_key
            best_record = record
            best_decisions = decisions
            best_trades = trades
        rows.append(record)

    if best_record is None or best_decisions is None or best_trades is None:
        raise ValueError("entry-gate grid produced no candidates")

    component_slug = _safe_filename("-".join(active_optimizer_components))
    output_path = output_dir / f"v2-btc-entry-gates-{_safe_filename(strategy_version)}-{_safe_filename(family)}-{_safe_filename(settings.exit_mode)}-{component_slug}"
    output_path.mkdir(parents=True, exist_ok=True)
    grid_results_path = output_path / "grid_results.csv"
    _write_csv(grid_results_path, rows)
    equity_curve_path = output_path / "equity_curve.csv"
    _write_csv(equity_curve_path, _equity_curve(best_trades, settings))
    rejected_vs_accepted_path = output_path / "rejected_vs_accepted.csv"
    _write_decisions_csv(rejected_vs_accepted_path, best_decisions)

    selection_status = "passed_all_constraints" if bool(best_record["passes_selection"]) else "best_available_failed_constraints"
    best_gate_manifest_path = output_path / "best_gate_manifest.json"
    best_gate_manifest = {
        "entry_gate_research_version": ENTRY_GATE_RESEARCH_VERSION,
        "gate_family": family,
        "strategy_version": strategy_version,
        "symbol": symbol.upper(),
        "selection_status": selection_status,
        "best_parameters": {key: best_record[key] for key in GateParameters.__dataclass_fields__},
        "best_metrics": _jsonable_record(best_record),
        "baseline_metrics": _jsonable_record(baseline_metrics),
        "candidate_count": len(rows),
        "full_gate_candidate_count": full_gate_candidate_count,
        "allowed_components": list(active_optimizer_components),
        "sampling_mode": "full" if max_candidates is None or max_candidates >= full_gate_candidate_count else "stratified_sample",
        "candidate_rejection_target_count": rejection_target_count,
        "candidate_full_pass_count": full_pass_count,
        "simulation_settings": asdict(settings),
        "source_metadata": metadata,
        "ohlcv_coverage": ohlcv_coverage.as_dict() if ohlcv_coverage else None,
        "source_basis": [
            "Lag-1 autocorrelation of closed-bar log returns",
            "Historical volatility ratio of short-window versus long-window log-return standard deviation",
            "Causal SciPy Butterworth bandpass cycle-energy ratio; no forward/backward filtering",
            "time-ordered walk-forward evaluation; no randomized cross-validation",
        ],
        "observe_only": True,
    }
    best_gate_manifest_path.write_text(json.dumps(best_gate_manifest, indent=2, sort_keys=True), encoding="utf-8")
    metrics_path = output_path / "metrics.json"
    metrics = {
        "entry_gate_research_version": ENTRY_GATE_RESEARCH_VERSION,
        "gate_family": family,
        "strategy_version": strategy_version,
        "symbol": symbol.upper(),
        "selection_status": selection_status,
        "baseline": _jsonable_record(baseline_metrics),
        "best": _jsonable_record(best_record),
        "candidate_count": len(rows),
        "full_gate_candidate_count": full_gate_candidate_count,
        "allowed_components": list(active_optimizer_components),
        "sampling_mode": "full" if max_candidates is None or max_candidates >= full_gate_candidate_count else "stratified_sample",
        "candidate_rejection_target_count": rejection_target_count,
        "candidate_full_pass_count": full_pass_count,
        "baseline_trade_count": len(baseline_trades),
        "best_trade_count": len(best_trades),
        "simulation_settings": asdict(settings),
        "ohlcv_coverage": ohlcv_coverage.as_dict() if ohlcv_coverage else None,
        "artifacts": {
            "grid_results": str(grid_results_path),
            "best_gate_manifest": str(best_gate_manifest_path),
            "equity_curve": str(equity_curve_path),
            "rejected_vs_accepted": str(rejected_vs_accepted_path),
        },
        "observe_only": True,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return EntryGateResearchResult(output_path, metrics_path, grid_results_path, best_gate_manifest_path, equity_curve_path, rejected_vs_accepted_path)


def run_entry_gate_optimizer(
    *,
    path: Path,
    symbol: str,
    strategy_version: str,
    output_dir: Path,
    max_gate_candidates: int | None = None,
    exit_profile: str = "runner",
    top_n: int = 5,
    workers: int = 1,
    allowed_components: tuple[str, ...] | list[str] | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
    ohlcv_cache_policy: str | None = None,
) -> EntryGateOptimizationResult:
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    if workers <= 0:
        raise ValueError("workers must be positive")
    if max_gate_candidates is not None and max_gate_candidates <= 0:
        raise ValueError("max_gate_candidates must be positive when provided")
    family = _normalize_gate_family(gate_family)
    normalized_allowed_components = _normalize_allowed_components(allowed_components, family)
    active_optimizer_components = _optimizer_components(normalized_allowed_components, family)
    selected_exit_settings = optimizer_exit_settings(exit_profile)
    bars, signals, metadata = load_chart_export(path, symbol=symbol)
    if not signals:
        raise ValueError("TradingView chart export has no Buy/Sell candidate signals")
    bars, ohlcv_coverage = prepare_ohlcv_enriched_bars(
        bars,
        symbol=symbol,
        gate_family=family,
        ohlcv_cache_policy=ohlcv_cache_policy,
    )
    cache = IndicatorCache(bars)
    split_rows = _split_signals(signals, split_count=5)
    signals_by_row = {signal.source_row_number: signal for signal in signals}
    full_gate_candidate_count = heavy_candidate_grid_count(normalized_allowed_components, family)
    gate_candidate_count = full_gate_candidate_count if max_gate_candidates is None else min(max_gate_candidates, full_gate_candidate_count)
    if gate_candidate_count <= 0:
        raise ValueError("entry-gate optimizer needs at least one gate candidate")

    top_records: list[dict[str, Any]] = []
    top_return_records: list[dict[str, Any]] = []
    top_profit_factor_records: list[dict[str, Any]] = []
    top_winrate_records: list[dict[str, Any]] = []
    evaluated_count = 0
    full_pass_count = 0
    rejection_target_count = 0
    gate_iterable: Iterator[GateParameters] = sampled_heavy_candidate_grid(normalized_allowed_components, max_gate_candidates, family)
    effective_workers = max(1, min(workers, gate_candidate_count))
    chunk_size = max(16, min(512, math.ceil(gate_candidate_count / max(effective_workers * 4, 1))))
    if workers == 1:
        _init_optimizer_worker(bars, signals)
        task_results = [
            _evaluate_optimizer_gate_chunk_task((selected_exit_settings, chunk, top_n))
            for chunk in _gate_candidate_chunks(gate_iterable, chunk_size)
        ]
    else:
        task_results = []
        with ProcessPoolExecutor(max_workers=effective_workers, initializer=_init_optimizer_worker, initargs=(bars, signals)) as pool:
            chunk_iter = _gate_candidate_chunks(gate_iterable, chunk_size)
            pending = set()
            max_pending = effective_workers * 2

            def submit_next_chunk() -> bool:
                try:
                    chunk = next(chunk_iter)
                except StopIteration:
                    return False
                pending.add(pool.submit(_evaluate_optimizer_gate_chunk_task, (selected_exit_settings, chunk, top_n)))
                return True

            for _ in range(max_pending):
                if not submit_next_chunk():
                    break
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    task_results.append(future.result())
                    submit_next_chunk()
    for result in task_results:
        evaluated_count += int(result["evaluated_count"])
        rejection_target_count += int(result["candidate_rejection_target_count"])
        full_pass_count += int(result["candidate_full_pass_count"])
        top_records.extend(result["top_records"])
        top_records = _rank_and_trim_records(top_records, top_n)
        top_return_records.extend(result["top_return_records"])
        top_return_records = _rank_and_trim_records(top_return_records, top_n, _optimizer_return_key)
        top_profit_factor_records.extend(result["top_profit_factor_records"])
        top_profit_factor_records = _rank_and_trim_records(top_profit_factor_records, top_n, _optimizer_profit_factor_key)
        top_winrate_records.extend(result["top_winrate_records"])
        top_winrate_records = _rank_and_trim_records(top_winrate_records, top_n, _optimizer_winrate_key)
    if not top_records:
        raise ValueError("entry-gate optimizer produced no candidates")

    best_record = top_records[0]
    best_settings = SimulationSettings(**best_record["exit_settings"])
    best_params = GateParameters(**{key: best_record[key] for key in GateParameters.__dataclass_fields__})
    independent_wins = _independent_signal_win_map(bars, signals, best_settings)
    _, best_decisions, best_trades = _evaluate_params(
        bars=bars,
        signals=signals,
        cache=cache,
        params=best_params,
        settings=best_settings,
        independent_wins=independent_wins,
        split_rows=split_rows,
        signals_by_row=signals_by_row,
    )
    selection_status = "passed_all_constraints" if bool(best_record["passes_selection"]) else "best_available_failed_constraints"
    component_slug = _safe_filename("-".join(active_optimizer_components))
    cap_slug = "full" if max_gate_candidates is None or max_gate_candidates >= full_gate_candidate_count else str(gate_candidate_count)
    output_path = output_dir / (
        f"v2-btc-entry-gate-optimizer-{_safe_filename(strategy_version)}-"
        f"{_safe_filename(family)}-{_safe_filename(_exit_profile_name(best_settings))}-{component_slug}-{cap_slug}"
    )
    output_path.mkdir(parents=True, exist_ok=True)
    top_results_path = output_path / "top5_results.csv"
    _write_csv(top_results_path, [_flatten_top_record(record, rank=index + 1) for index, record in enumerate(top_records)])
    top_return_results_path = output_path / "top5_by_return_results.csv"
    _write_csv(top_return_results_path, [_flatten_top_record(record, rank=index + 1) for index, record in enumerate(top_return_records)])
    top_profit_factor_results_path = output_path / "top5_by_profit_factor_results.csv"
    _write_csv(top_profit_factor_results_path, [_flatten_top_record(record, rank=index + 1) for index, record in enumerate(top_profit_factor_records)])
    top_winrate_results_path = output_path / "top5_by_winrate_results.csv"
    _write_csv(top_winrate_results_path, [_flatten_top_record(record, rank=index + 1) for index, record in enumerate(top_winrate_records)])
    equity_curve_path = output_path / "equity_curve.csv"
    _write_csv(equity_curve_path, _equity_curve(best_trades, best_settings))
    rejected_vs_accepted_path = output_path / "rejected_vs_accepted.csv"
    _write_decisions_csv(rejected_vs_accepted_path, best_decisions)
    best_gate_manifest_path = output_path / "best_gate_manifest.json"
    best_gate_manifest = {
        "entry_gate_research_version": ENTRY_GATE_RESEARCH_VERSION,
        "optimizer": "heavy_gate_component_optimizer",
        "gate_family": family,
        "strategy_version": strategy_version,
        "symbol": symbol.upper(),
        "selection_status": selection_status,
        "best_parameters": {key: best_record[key] for key in GateParameters.__dataclass_fields__},
        "exit_profile": _exit_profile_name(best_settings),
        "best_exit_settings": asdict(best_settings),
        "best_metrics": _jsonable_record(best_record),
        "baseline_for_best_exit": _jsonable_record(best_record["baseline_for_exit"]),
        "top_n": top_n,
        "workers": workers,
        "effective_workers": effective_workers,
        "optimizer_chunk_size": chunk_size,
        "allowed_components": list(active_optimizer_components),
        "max_gate_candidates": max_gate_candidates,
        "gate_candidate_count": gate_candidate_count,
        "full_gate_candidate_count": full_gate_candidate_count,
        "evaluated_count": evaluated_count,
        "candidate_rejection_target_count": rejection_target_count,
        "candidate_full_pass_count": full_pass_count,
        "source_metadata": metadata,
        "ohlcv_coverage": ohlcv_coverage.as_dict() if ohlcv_coverage else None,
        "observe_only": True,
    }
    best_gate_manifest_path.write_text(json.dumps(best_gate_manifest, indent=2, sort_keys=True), encoding="utf-8")
    metrics_path = output_path / "metrics.json"
    metrics = {
        "entry_gate_research_version": ENTRY_GATE_RESEARCH_VERSION,
        "optimizer": "heavy_gate_component_optimizer",
        "gate_family": family,
        "strategy_version": strategy_version,
        "symbol": symbol.upper(),
        "selection_status": selection_status,
        "evaluated_count": evaluated_count,
        "gate_candidate_count": gate_candidate_count,
        "full_gate_candidate_count": full_gate_candidate_count,
        "exit_profile": _exit_profile_name(best_settings),
        "workers": workers,
        "effective_workers": effective_workers,
        "optimizer_chunk_size": chunk_size,
        "allowed_components": list(active_optimizer_components),
        "ohlcv_coverage": ohlcv_coverage.as_dict() if ohlcv_coverage else None,
        "candidate_rejection_target_count": rejection_target_count,
        "candidate_full_pass_count": full_pass_count,
        "best": _jsonable_record(best_record),
        "baseline_for_best_exit": _jsonable_record(best_record["baseline_for_exit"]),
        "top5": [_jsonable_record(_flatten_top_record(record, rank=index + 1)) for index, record in enumerate(top_records)],
        "top5_by_return": [_jsonable_record(_flatten_top_record(record, rank=index + 1)) for index, record in enumerate(top_return_records)],
        "top5_by_profit_factor": [_jsonable_record(_flatten_top_record(record, rank=index + 1)) for index, record in enumerate(top_profit_factor_records)],
        "top5_by_winrate": [_jsonable_record(_flatten_top_record(record, rank=index + 1)) for index, record in enumerate(top_winrate_records)],
        "artifacts": {
            "top_results": str(top_results_path),
            "top_return_results": str(top_return_results_path),
            "top_profit_factor_results": str(top_profit_factor_results_path),
            "top_winrate_results": str(top_winrate_results_path),
            "best_gate_manifest": str(best_gate_manifest_path),
            "equity_curve": str(equity_curve_path),
            "rejected_vs_accepted": str(rejected_vs_accepted_path),
        },
        "observe_only": True,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return EntryGateOptimizationResult(output_path, metrics_path, top_results_path, best_gate_manifest_path, equity_curve_path, rejected_vs_accepted_path)


def run_entry_gate_preflight(
    *,
    path: Path,
    symbol: str,
    strategy_version: str,
    output_dir: Path,
    settings: SimulationSettings | None = None,
    gate_family: str = LEGACY_GATE_FAMILY,
    ohlcv_cache_policy: str | None = None,
) -> EntryGatePreflightResult:
    settings = settings or preferred_research_exit_settings()
    family = _normalize_gate_family(gate_family)
    bars, signals, metadata = load_chart_export(path, symbol=symbol)
    if not signals:
        raise ValueError("TradingView chart export has no Buy/Sell candidate signals")
    bars, ohlcv_coverage = prepare_ohlcv_enriched_bars(
        bars,
        symbol=symbol,
        gate_family=family,
        ohlcv_cache_policy=ohlcv_cache_policy,
    )
    cache = IndicatorCache(bars)
    independent_wins = _independent_signal_win_map(bars, signals, settings)
    split_rows = _split_signals(signals, split_count=5)
    signals_by_row = {signal.source_row_number: signal for signal in signals}
    baseline_metrics, _, _ = _evaluate_params(
        bars=bars,
        signals=signals,
        cache=cache,
        params=None,
        settings=settings,
        independent_wins=independent_wins,
        split_rows=split_rows,
        signals_by_row=signals_by_row,
    )

    all_rows: list[dict[str, Any]] = []
    best_by_component: dict[str, dict[str, Any]] = {}
    for component, params in preflight_component_grid(family):
        record = _evaluate_gate_record(
            bars=bars,
            signals=signals,
            cache=cache,
            split_rows=split_rows,
            signals_by_row=signals_by_row,
            settings=settings,
            params=params,
            baseline_metrics=baseline_metrics,
            independent_wins=independent_wins,
            component=component,
        )
        record["improves_return"] = float(record["return_on_capital_pct"]) > float(baseline_metrics["return_on_capital_pct"])
        record["improves_profit_factor"] = float(record.get("profit_factor") or 0.0) > float(baseline_metrics.get("profit_factor") or 0.0)
        record["preflight_viable"] = (
            bool(record["improves_return"])
            and bool(record["improves_profit_factor"])
            and 0.10 <= float(record["rejection_rate"]) <= 0.80
            and float(record.get("high_volatility_trend_retention_rate", 1.0)) >= 0.70
        )
        all_rows.append(record)
        current = best_by_component.get(component)
        if current is None or _optimizer_selection_key(record) > _optimizer_selection_key(current):
            best_by_component[component] = record

    output_path = output_dir / f"v2-btc-entry-gate-preflight-{_safe_filename(strategy_version)}-{_safe_filename(family)}"
    output_path.mkdir(parents=True, exist_ok=True)
    preflight_results_path = output_path / "preflight_component_results.csv"
    _write_csv(preflight_results_path, all_rows)
    metrics_path = output_path / "metrics.json"
    ranked_components = sorted(best_by_component.values(), key=_optimizer_selection_key, reverse=True)
    metrics = {
        "entry_gate_research_version": ENTRY_GATE_RESEARCH_VERSION,
        "optimizer": "single_component_preflight",
        "gate_family": family,
        "strategy_version": strategy_version,
        "symbol": symbol.upper(),
        "candidate_count": len(all_rows),
        "component_count": len(best_by_component),
        "simulation_settings": asdict(settings),
        "baseline": _jsonable_record(baseline_metrics),
        "best_by_component": [_jsonable_record(_flatten_top_record(record, rank=index + 1)) for index, record in enumerate(ranked_components)],
        "viable_components": [record["component"] for record in ranked_components if record.get("preflight_viable")],
        "source_metadata": metadata,
        "ohlcv_coverage": ohlcv_coverage.as_dict() if ohlcv_coverage else None,
        "artifacts": {"preflight_component_results": str(preflight_results_path)},
        "observe_only": True,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    return EntryGatePreflightResult(output_path, metrics_path, preflight_results_path)


def _settings_key(settings: SimulationSettings) -> str:
    return (
        f"{settings.exit_mode}_tp{settings.take_profit_pct:g}_sl{settings.stop_loss_pct:g}_"
        f"act{settings.runner_activation_pct:g}_trail{settings.runner_trailing_stop_pct:g}_floor{settings.runner_profit_floor_pct:g}"
    )


def _flatten_top_record(record: dict[str, Any], *, rank: int) -> dict[str, Any]:
    flattened = {key: value for key, value in record.items() if key not in {"baseline_for_exit", "exit_settings", "split_pnls"}}
    flattened["rank"] = rank
    flattened["split_pnls"] = record.get("split_pnls")
    flattened.update({f"exit_{key}": value for key, value in (record.get("exit_settings") or {}).items()})
    baseline = record.get("baseline_for_exit") or {}
    flattened["baseline_return_on_capital_pct"] = baseline.get("return_on_capital_pct")
    flattened["baseline_profit_factor"] = baseline.get("profit_factor")
    flattened["baseline_trade_count"] = baseline.get("trade_count")
    return flattened


def _jsonable_record(record: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
            payload[key] = str(value)
        else:
            payload[key] = value
    return payload


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value) if isinstance(value, (list, dict)) else value for key, value in row.items()})


def _write_decisions_csv(path: Path, decisions: list[GateDecision]) -> None:
    rows = [
        {
            "source_row_number": decision.signal.source_row_number,
            "signal_time_ms": decision.signal.time_ms,
            "direction": decision.signal.direction,
            "accepted": decision.accepted,
            "reason": decision.reason,
            "gate_score": decision.gate_score,
            "corridor": decision.corridor,
            "high_volatility_trend": decision.high_volatility_trend,
            "marker_price": decision.signal.marker_price,
            "next_open": decision.signal.next_open,
            "components_json": json.dumps(decision.components, sort_keys=True),
        }
        for decision in decisions
    ]
    _write_csv(path, rows)
