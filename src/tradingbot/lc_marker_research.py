from __future__ import annotations

import copy
import json
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

import tradingbot.lorentz_tv as lorentz_tv
from tradingbot.features_tv import n_adx, n_cci, n_rsi, n_wt
from tradingbot.indicators import hlc3, normalize_frame, ohlc4
from tradingbot.models import AppConfig
from tradingbot.parity import (
    _entry_events,
    _entry_window_from_tv,
    _event_mismatches,
    _match_entry_events,
    _normalize_tv_export,
    generate_parity_dump,
    run_entry_parity_check,
    run_parity_check,
)


@dataclass(slots=True)
class MarkerResearchCandidate:
    name: str
    dataset_variant: str
    lc_parity_mode: str = "pine_exact"
    wt_source: str = "hlc3"
    cci_source: str = "close"
    adx_zero_previous_on_first_bar: bool = True


@dataclass(slots=True)
class MarkerResearchScore:
    candidate: dict[str, Any]
    exact_matched_entry_count: int
    exact_match_rate: float
    one_bar_matched_entry_count: int
    one_bar_match_rate: float
    tv_entry_count: int
    python_entry_count: int
    exact_missing_entry_count: int
    exact_extra_entry_count: int
    one_bar_missing_entry_count: int
    one_bar_extra_entry_count: int
    best_uniform_shift_bars: int
    best_uniform_shift_matched_entry_count: int
    best_uniform_shift_match_rate: float
    root_cause_counts: dict[str, int]
    first_mismatch: dict[str, Any] | None


@dataclass(slots=True)
class MarkerResearchReport:
    matched_exact: bool
    matched_one_bar: bool
    symbol: str
    export_summary: dict[str, Any]
    rankings: list[MarkerResearchScore]
    best_exact: MarkerResearchScore | None = None
    best_one_bar: MarkerResearchScore | None = None
    notes: list[str] = field(default_factory=list)


def _export_base_frame(tv_export_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    export = _normalize_tv_export(tv_export_df)
    frame = export[["timestamp", "open", "high", "low", "close"]].copy()
    frame["volume"] = export["volume"] if "volume" in export.columns else 0.0
    frame["symbol"] = symbol
    return frame


def _dataset_variants(base_df: pd.DataFrame, tv_export_df: pd.DataFrame, symbol: str) -> dict[str, pd.DataFrame]:
    base = normalize_frame(base_df)
    export_base = normalize_frame(_export_base_frame(tv_export_df, symbol))
    first_export_ts = export_base["timestamp"].min()
    variants = {
        "provided_base": base,
        "export_only": export_base,
    }
    prehistory = base[base["timestamp"] < first_export_ts]
    if not prehistory.empty:
        variants["prehistory_tail_1000"] = pd.concat([prehistory.tail(1000), base[base["timestamp"] >= first_export_ts]], ignore_index=True)
    return variants


def _research_candidates(dataset_variants: list[str]) -> list[MarkerResearchCandidate]:
    modes = [
        "pine_exact",
        "research_ann_modulo_0",
        "research_ann_modulo_1",
        "research_ann_modulo_2",
        "research_ann_modulo_3",
        "research_ann_rolling",
        "research_label_inverted",
        "research_label_forward",
        "research_label_forward_inverted",
        "research_barsheld_start0",
    ]
    feature_variants = [
        {"wt_source": "close"},
        {"wt_source": "ohlc4"},
        {"cci_source": "hlc3"},
        {"adx_zero_previous_on_first_bar": False},
        {"wt_source": "close", "cci_source": "hlc3"},
        {"wt_source": "ohlc4", "cci_source": "hlc3"},
    ]
    candidates: list[MarkerResearchCandidate] = []
    for dataset_variant in dataset_variants:
        for mode in modes:
            candidates.append(
                MarkerResearchCandidate(
                    name=f"{dataset_variant}:{mode}",
                    dataset_variant=dataset_variant,
                    lc_parity_mode=mode,
                )
            )
        for variant in feature_variants:
            suffix = ",".join(f"{key}={value}" for key, value in variant.items())
            candidates.append(
                MarkerResearchCandidate(
                    name=f"{dataset_variant}:pine_exact:{suffix}",
                    dataset_variant=dataset_variant,
                    **variant,
                )
            )
    return candidates


def _source(frame: pd.DataFrame, source_name: str) -> pd.Series:
    if source_name == "close":
        return frame["close"]
    if source_name == "hlc3":
        return hlc3(frame)
    if source_name == "ohlc4":
        return ohlc4(frame)
    raise ValueError(f"Unsupported research feature source: {source_name}")


@contextmanager
def _feature_research_patch(candidate: MarkerResearchCandidate):
    original_feature_series = lorentz_tv.feature_series

    def patched_feature_series(
        df: pd.DataFrame,
        feature_name: str,
        param_a: int,
        param_b: int,
        *,
        adx_zero_previous_on_first_bar: bool = True,
    ) -> pd.Series:
        feature_name_upper = feature_name.upper()
        if feature_name_upper == "RSI":
            return n_rsi(df["close"], param_a, param_b)
        if feature_name_upper == "WT":
            return n_wt(_source(df, candidate.wt_source), param_a, param_b)
        if feature_name_upper == "CCI":
            return n_cci(_source(df, candidate.cci_source), param_a, param_b)
        if feature_name_upper == "ADX":
            return n_adx(
                df["high"],
                df["low"],
                df["close"],
                param_a,
                zero_previous_on_first_bar=candidate.adx_zero_previous_on_first_bar,
            )
        return original_feature_series(
            df,
            feature_name,
            param_a,
            param_b,
            adx_zero_previous_on_first_bar=adx_zero_previous_on_first_bar,
        )

    lorentz_tv.feature_series = patched_feature_series
    try:
        yield
    finally:
        lorentz_tv.feature_series = original_feature_series


def _shift_events(events: list[dict[str, Any]], shift_bars: int) -> list[dict[str, Any]]:
    shifted: list[dict[str, Any]] = []
    for event in events:
        shifted_event = dict(event)
        shifted_event["position"] = int(shifted_event["position"]) + int(shift_bars)
        shifted.append(shifted_event)
    return shifted


def _score_window(window: pd.DataFrame, tolerance_bars: int, *, shift_bars: int = 0) -> dict[str, Any]:
    python_events = _entry_events(window, "start_long_trade_py", "start_short_trade_py")
    if shift_bars:
        python_events = _shift_events(python_events, shift_bars)
    tv_events = _entry_events(window, "start_long_trade_tv", "start_short_trade_tv")
    matched, missing, extra = _match_entry_events(python_events, tv_events, tolerance_bars)
    mismatches = _event_mismatches(missing, extra)
    return {
        "matched_entry_count": int(len(matched)),
        "tv_entry_count": int(len(tv_events)),
        "python_entry_count": int(len(python_events)),
        "missing_entry_count": int(len(missing)),
        "extra_entry_count": int(len(extra)),
        "match_rate": float(len(matched) / len(tv_events)) if tv_events else 1.0,
        "first_mismatch": mismatches[0] if mismatches else None,
        "root_cause_counts": dict(Counter(str(item.get("root_cause_candidate", "unknown")) for item in mismatches)),
    }


def _score_candidate(
    base_df: pd.DataFrame,
    tv_export_df: pd.DataFrame,
    app_config: AppConfig,
    symbol: str,
    candidate: MarkerResearchCandidate,
) -> MarkerResearchScore:
    probe_config = copy.deepcopy(app_config)
    probe_config.strategies[symbol].lc_parity_mode = candidate.lc_parity_mode
    with _feature_research_patch(candidate):
        ours = generate_parity_dump(base_df, probe_config, symbol)
    expected = _normalize_tv_export(tv_export_df)
    merged = ours.merge(expected, on="timestamp", how="inner", suffixes=("_py", "_tv"))
    window, _selected_tv_entries = _entry_window_from_tv(merged, mode="full", sample_size=100, sample_offset=0)

    exact = _score_window(window, 0)
    one_bar = _score_window(window, 1)
    shifted_scores = [_score_window(window, 0, shift_bars=shift) | {"shift": shift} for shift in [-1, 0, 1]]
    best_shift = max(
        shifted_scores,
        key=lambda item: (int(item["matched_entry_count"]), -int(item["missing_entry_count"]), -int(item["extra_entry_count"])),
    )
    return MarkerResearchScore(
        candidate=asdict(candidate),
        exact_matched_entry_count=int(exact["matched_entry_count"]),
        exact_match_rate=float(exact["match_rate"]),
        one_bar_matched_entry_count=int(one_bar["matched_entry_count"]),
        one_bar_match_rate=float(one_bar["match_rate"]),
        tv_entry_count=int(exact["tv_entry_count"]),
        python_entry_count=int(exact["python_entry_count"]),
        exact_missing_entry_count=int(exact["missing_entry_count"]),
        exact_extra_entry_count=int(exact["extra_entry_count"]),
        one_bar_missing_entry_count=int(one_bar["missing_entry_count"]),
        one_bar_extra_entry_count=int(one_bar["extra_entry_count"]),
        best_uniform_shift_bars=int(best_shift["shift"]),
        best_uniform_shift_matched_entry_count=int(best_shift["matched_entry_count"]),
        best_uniform_shift_match_rate=float(best_shift["match_rate"]),
        root_cause_counts=dict(exact["root_cause_counts"]),
        first_mismatch=exact["first_mismatch"],
    )


def _export_summary(tv_export_df: pd.DataFrame) -> dict[str, Any]:
    export = _normalize_tv_export(tv_export_df)
    long_events = _entry_events(export, "start_long_trade", "start_short_trade")
    marker_timestamps = [
        {"timestamp": str(event["timestamp"]), "side": event["side"], "position": int(event["position"])}
        for event in long_events
    ]
    return {
        "rows": int(len(export)),
        "columns": [str(column) for column in export.columns],
        "start": str(export["timestamp"].min()) if "timestamp" in export.columns and len(export) else None,
        "end": str(export["timestamp"].max()) if "timestamp" in export.columns and len(export) else None,
        "marker_count": int(len(marker_timestamps)),
        "marker_timestamps": marker_timestamps,
    }


def run_marker_research(
    base_df: pd.DataFrame,
    tv_export_df: pd.DataFrame,
    app_config: AppConfig,
    symbol: str,
    *,
    max_candidates: int | None = None,
) -> MarkerResearchReport:
    variants = _dataset_variants(base_df, tv_export_df, symbol)
    candidates = _research_candidates(list(variants))
    if max_candidates is not None:
        candidates = candidates[: max(int(max_candidates), 0)]

    rankings: list[MarkerResearchScore] = []
    for candidate in candidates:
        score = _score_candidate(variants[candidate.dataset_variant], tv_export_df, app_config, symbol, candidate)
        rankings.append(score)
    rankings.sort(
        key=lambda item: (
            item.one_bar_matched_entry_count,
            item.exact_matched_entry_count,
            -item.one_bar_missing_entry_count,
            -item.one_bar_extra_entry_count,
        ),
        reverse=True,
    )
    best_exact = max(
        rankings,
        key=lambda item: (
            item.exact_matched_entry_count,
            item.one_bar_matched_entry_count,
            -item.exact_missing_entry_count,
            -item.exact_extra_entry_count,
        ),
        default=None,
    )
    best_one_bar = rankings[0] if rankings else None
    tv_count = rankings[0].tv_entry_count if rankings else 0
    matched_exact = bool(best_exact and best_exact.exact_matched_entry_count == tv_count and best_exact.exact_extra_entry_count == 0)
    matched_one_bar = bool(best_one_bar and best_one_bar.one_bar_matched_entry_count == tv_count and best_one_bar.one_bar_extra_entry_count == 0)
    notes = [
        "Research modes are marker-fitting probes only; they must not replace pine_exact without deterministic exported diagnostics.",
        "Uniform shift score is informational and helps identify bar-offset explanations; it is not an accepted parity fix by itself.",
    ]
    return MarkerResearchReport(
        matched_exact=matched_exact,
        matched_one_bar=matched_one_bar,
        symbol=symbol,
        export_summary=_export_summary(tv_export_df),
        rankings=rankings,
        best_exact=best_exact,
        best_one_bar=best_one_bar,
        notes=notes,
    )


def _read_text(path: Path) -> str:
    if not path.exists():
        return f"[missing local optional artifact: {path}]"
    return path.read_text(encoding="utf-8", errors="replace")


def _line_range(path: Path, start: int, end: int) -> str:
    lines = _read_text(path).splitlines()
    return "\n".join(f"{idx + 1}: {line}" for idx, line in enumerate(lines[start - 1 : end], start - 1))


def _json_block(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


def write_gpt55_casefile(
    output_path: str | Path,
    *,
    report: MarkerResearchReport,
    base_path: str | Path,
    tv_export_path: str | Path,
    config_path: str | Path,
    kernel_command: str,
    entry_exact_command: str,
    entry_one_bar_command: str,
    tests_command: str = "python -m pytest -q",
) -> Path:
    root = Path(__file__).resolve().parents[2]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pine_path = root / "references" / "lorentzian-classification" / "original_lorentzian_classification.pine"
    ml_path = root / "references" / "pine-libraries" / "MLExtension.txt"
    chat_path = root / "references" / "optional_chat_export.txt"
    features_path = root / "src" / "tradingbot" / "features_tv.py"
    lorentz_path = root / "src" / "tradingbot" / "lorentz_tv.py"
    parity_path = root / "src" / "tradingbot" / "parity.py"
    config_file = Path(config_path)

    top_rankings = [asdict(item) for item in report.rankings[:20]]
    content = f"""# LC Marker-Only Parity Casefile for GPT-5.5 Pro

## Objective
Reach parity with TradingView Lorentzian Classification on marker-only export `{tv_export_path}`.

Primary target: 67/67 exact Buy/Sell entries. Secondary target: 67/67 within one bar with a source-faithful explanation.

## Fixed User Settings
- Source: `close`
- Neighbors count: `10`
- Max bars back: `1000`
- Features: `RSI 14/1`, `WT 10/11`, `CCI 23/1`, `ADX 20/1`, `RSI 9/1`
- Kernel: lookback `8`, relative weight `8`, regression level `25`, lag `2`
- Filters: volatility off, regime off, ADX off, EMA off, SMA off, kernel trade filter off, dynamic exits off

## Current Results
- Kernel parity: exact after 26 warmup rows.
- Export-only marker parity: 46/67 within one bar.
- Paired-prehistory marker parity before research sweep: 56/67 within one bar, 35/67 exact.
- Best research exact: `{report.best_exact.exact_matched_entry_count if report.best_exact else 0}/{report.best_exact.tv_entry_count if report.best_exact else 0}`.
- Best research one-bar: `{report.best_one_bar.one_bar_matched_entry_count if report.best_one_bar else 0}/{report.best_one_bar.tv_entry_count if report.best_one_bar else 0}`.
- Complete exact reached: `{report.matched_exact}`.
- Complete one-bar reached: `{report.matched_one_bar}`.

## Export Summary
```json
{_json_block(report.export_summary)}
```

## Research Candidate Rankings
```json
{_json_block(top_rankings)}
```

## Reproduction Commands
```powershell
{tests_command}
{kernel_command}
{entry_exact_command}
{entry_one_bar_command}
python -m tradingbot.cli marker-research --config {config_path} --symbol BTC --base-csv {base_path} --tv-export "{tv_export_path}" --casefile-output {output_path}
```

## Original Pine: Feature Selection Through Entries
```pine
{_line_range(pine_path, 165, 491)}
```

## Original Pine Library: Feature Helpers
```pine
{_line_range(ml_path, 30, 250)}
```

## Python Equivalent: Feature Helpers
```python
{_read_text(features_path)}
```

## Python Equivalent: Lorentzian Classifier
```python
{_read_text(lorentz_path)}
```

## Python Equivalent: Parity Parser and Comparator
```python
{_read_text(parity_path)}
```

## Active Config
```yaml
{_read_text(config_file)}
```

## Relevant Chat Export Excerpts
```text
{_line_range(chat_path, 120, 180)}
```

## Open Problem for GPT-5.5 Pro
Given only marker signals, original Pine, Python interpretation, and chat notes, decide whether the remaining mismatch is primarily:
1. Pine execution-state/history alignment: first loaded chart bars, persistent arrays, static first-1000 scan, or modulo index basis.
2. Feature helper parity: especially WT normalization/warmup, CCI normalization, RSI/EMA/RMA startup, or ADX `nz()` behavior.
3. Signal-gate semantics: `ta.change(signal)`, `barsHeld`, first available marker offset, or shape-marker export timing.

Do not recommend changing `pine_exact` unless the change is directly justified by original Pine semantics. If a marker-only tuned variant is proposed, label it research-only.
"""
    output.write_text(content, encoding="utf-8")
    return output


def report_to_dict(report: MarkerResearchReport) -> dict[str, Any]:
    return asdict(report)
