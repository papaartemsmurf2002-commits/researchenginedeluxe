from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from tradingbotsuite.backtesting.costs import CostModel
from tradingbotsuite.backtesting.execution_sim import ExecutionAssumptions, ExecutionSimulator
from tradingbotsuite.backtesting.metrics import calculate_backtest_metrics
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_discovery.exit_lab import (
    DISCOVERY_EXIT_LAB_MANIFEST_VERSION,
    DISCOVERY_EXIT_LAB_VERSION,
    discovery_entry_lead_evidence_sha256,
)
from tradingbotsuite.research_discovery.state import atomic_write_json


FROZEN_ENTRY_EXIT_LAB_VERSION = "frozen-entry-exit-lab-v1"
MIN_EXIT_LAB_HOLDING_MS = 60 * 60_000
MAX_EXIT_LAB_HOLDING_MS = 7 * 24 * 60 * 60_000
DEFAULT_EXIT_POLICIES = (
    {
        "exit_policy_id": "fixed_holding_window",
        "exit_policy_params": {},
    },
    {
        "exit_policy_id": "simple_runner_v1",
        "exit_policy_params": {"activation_pct": 0.01, "runner_gap_pct": 0.005},
    },
)


@dataclass(frozen=True, slots=True)
class FrozenEntryExitLabArtifactResult:
    output_dir: Path
    manifest_path: Path
    matrix_path: Path
    candidate_gates_path: Path
    trades_path: Path
    manifest: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class _FrameReadResult:
    frame: pd.DataFrame
    malformed_reason: str | None = None


def write_frozen_entry_exit_lab_artifacts(
    *,
    discovery_manifest_path: str | Path,
    output_dir: str | Path,
    entry_signals_path: str | Path | None = None,
    market_data_path: str | Path | None = None,
    max_candidates: int = 12,
    exit_policies: Sequence[Mapping[str, Any]] = DEFAULT_EXIT_POLICIES,
) -> FrozenEntryExitLabArtifactResult:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = build_frozen_entry_exit_lab(
        discovery_manifest_path=discovery_manifest_path,
        entry_signals_path=entry_signals_path,
        market_data_path=market_data_path,
        max_candidates=max_candidates,
        exit_policies=exit_policies,
    )
    manifest = dict(result["manifest"])
    matrix = result["matrix"]
    candidate_gates = result["candidate_gates"]
    trades = result["trades"]

    matrix_path = output / "frozen_entry_exit_lab_matrix.parquet"
    gates_path = output / "frozen_entry_exit_lab_candidate_gates.parquet"
    trades_path = output / "frozen_entry_exit_lab_trades.parquet"
    manifest_path = output / "discovery_exit_lab_manifest.json"
    matrix.to_parquet(matrix_path, index=False)
    candidate_gates.to_parquet(gates_path, index=False)
    trades.to_parquet(trades_path, index=False)
    manifest["required_outputs"] = {
        "discovery_exit_lab_matrix": str(matrix_path),
        "frozen_entry_exit_lab_matrix": str(matrix_path),
        "discovery_exit_lab_candidate_gates": str(gates_path),
        "frozen_entry_exit_lab_trades": str(trades_path),
        "discovery_exit_lab_manifest": str(manifest_path),
    }
    manifest["discovery_exit_lab_matrix_sha256"] = _file_sha256(matrix_path)
    manifest["discovery_exit_lab_candidate_gates_sha256"] = _file_sha256(gates_path)
    manifest["frozen_entry_exit_lab_trades_sha256"] = _file_sha256(trades_path)
    atomic_write_json(manifest_path, _json_safe(manifest))
    return FrozenEntryExitLabArtifactResult(
        output_dir=output,
        manifest_path=manifest_path,
        matrix_path=matrix_path,
        candidate_gates_path=gates_path,
        trades_path=trades_path,
        manifest=manifest,
    )


def build_frozen_entry_exit_lab(
    *,
    discovery_manifest_path: str | Path,
    entry_signals_path: str | Path | None = None,
    market_data_path: str | Path | None = None,
    max_candidates: int = 12,
    exit_policies: Sequence[Mapping[str, Any]] = DEFAULT_EXIT_POLICIES,
) -> dict[str, Any]:
    manifest_path = Path(discovery_manifest_path).expanduser().resolve()
    discovery_manifest = _read_json(manifest_path)
    outputs = discovery_manifest.get("required_outputs") if isinstance(discovery_manifest.get("required_outputs"), Mapping) else {}
    interesting_path = _resolve_output_path(outputs.get("interesting_candidates"), manifest_path.parent / "candidate_ledgers" / "interesting_candidates.parquet")
    interesting_read = _read_frame(interesting_path, malformed_reason="interesting_candidates_malformed")
    if interesting_read.malformed_reason is not None:
        return _blocked_result(
            discovery_manifest=discovery_manifest,
            discovery_manifest_path=manifest_path,
            lead_count=0,
            reason=interesting_read.malformed_reason,
        )
    interesting = interesting_read.frame
    leads = _select_leads(interesting, max_candidates=max_candidates)
    if leads.empty:
        return _blocked_result(
            discovery_manifest=discovery_manifest,
            discovery_manifest_path=manifest_path,
            lead_count=0,
            reason="interesting_candidates_missing",
        )
    if entry_signals_path is None:
        return _blocked_result(
            discovery_manifest=discovery_manifest,
            discovery_manifest_path=manifest_path,
            lead_count=len(leads),
            reason="frozen_entry_signals_missing",
            leads=leads,
        )
    signals_path = Path(entry_signals_path).expanduser().resolve()
    if not signals_path.is_file():
        return _blocked_result(
            discovery_manifest=discovery_manifest,
            discovery_manifest_path=manifest_path,
            lead_count=len(leads),
            reason="frozen_entry_signals_missing",
            leads=leads,
        )
    signals_read = _read_frame(signals_path, malformed_reason="frozen_entry_signals_malformed")
    if signals_read.malformed_reason is not None:
        return _blocked_result(
            discovery_manifest=discovery_manifest,
            discovery_manifest_path=manifest_path,
            lead_count=len(leads),
            reason=signals_read.malformed_reason,
            leads=leads,
        )
    signals = signals_read.frame
    market_path = _resolve_market_data_path(discovery_manifest, market_data_path)
    if market_path is None or not market_path.is_file():
        return _blocked_result(
            discovery_manifest=discovery_manifest,
            discovery_manifest_path=manifest_path,
            lead_count=len(leads),
            reason="market_data_missing",
            leads=leads,
        )
    market_read = _read_frame(market_path, malformed_reason="market_data_malformed")
    if market_read.malformed_reason is not None:
        return _blocked_result(
            discovery_manifest=discovery_manifest,
            discovery_manifest_path=manifest_path,
            lead_count=len(leads),
            reason=market_read.malformed_reason,
            leads=leads,
        )
    market = _market_frame(market_read.frame)
    if market.empty:
        return _blocked_result(
            discovery_manifest=discovery_manifest,
            discovery_manifest_path=manifest_path,
            lead_count=len(leads),
            reason="market_data_empty",
            leads=leads,
        )

    simulator = ExecutionSimulator()
    matrix_rows: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []
    gates: list[dict[str, Any]] = []
    policies = [dict(policy) for policy in exit_policies]
    for _, lead in leads.iterrows():
        lead_record = {str(key): value for key, value in lead.to_dict().items()}
        lead_hash = discovery_entry_lead_evidence_sha256(lead_record)
        candidate_id = str(lead_record.get("candidate_id") or "")
        lead_signals = _signals_for_lead(signals, lead_record)
        if lead_signals.empty:
            gates.append(_blocked_gate(lead_record, lead_hash, "frozen_entry_signals_missing_for_lead"))
            continue
        simulation_signals = _signal_frame(lead_signals, discovery_manifest)
        if simulation_signals.empty:
            gates.append(_blocked_gate(lead_record, lead_hash, "frozen_entry_valid_signals_missing_for_lead"))
            continue
        holding_ms = _normalized_holding_ms(str(lead_record.get("label_horizon") or "1h"))
        if holding_ms is None:
            gates.append(_blocked_gate(lead_record, lead_hash, "frozen_entry_label_horizon_unsupported"))
            continue
        fixed_metric: Mapping[str, Any] | None = None
        best_metric: Mapping[str, Any] | None = None
        best_policy = ""
        simulation_error_reason: str | None = None
        for policy in policies:
            policy_id = str(policy.get("exit_policy_id") or "fixed_holding_window")
            assumptions = ExecutionAssumptions(
                interval_ms=_infer_interval_ms(market),
                entry_latency_ms=0,
                entry_price_source="signal_bar_close_plus_latency",
                min_holding_ms=holding_ms,
                max_holding_ms=holding_ms,
                holding_period_ms=holding_ms,
                allow_same_bar_exit=False,
                exit_policy_id=policy_id,
                exit_policy_params=dict(policy.get("exit_policy_params") or {}),
                exit_price_source="primary_close",
            )
            try:
                trades, equity = simulator.simulate(
                    simulation_signals,
                    market,
                    costs=CostModel(),
                    assumptions=assumptions,
                    initial_equity=1.0,
                )
                metrics = calculate_backtest_metrics(
                    trades=trades,
                    signals=simulation_signals,
                    equity_curve=equity,
                    market_data=market,
                    initial_equity=1.0,
                )
            except (KeyError, TypeError, ValueError) as exc:
                simulation_error_reason = f"frozen_entry_exit_simulation_error:{type(exc).__name__}"
                break
            if not trades.empty:
                trades = trades.assign(candidate_id=candidate_id, entry_lead_evidence_sha256=lead_hash, exit_policy_id=policy_id)
                trade_frames.append(trades)
            row = {
                "entry_candidate_id": candidate_id,
                "research_candidate_id": candidate_id,
                "candidate_id": candidate_id,
                "trial_id": lead_record.get("trial_id"),
                "record_sha256": lead_record.get("record_sha256"),
                "entry_lead_evidence_sha256": lead_hash,
                "exit_policy_id": policy_id,
                "exit_policy_params_json": json.dumps(dict(policy.get("exit_policy_params") or {}), sort_keys=True),
                "trade_count": int(metrics.get("trade_count") or 0),
                "net_return_after_fees_slippage_funding": float(metrics.get("net_return_after_fees_slippage_funding") or 0.0),
                "expectancy_per_trade": float(metrics.get("expectancy_per_trade") or 0.0),
                "profit_factor": float(metrics.get("profit_factor") or 0.0),
                "max_drawdown": float(metrics.get("max_drawdown") or 0.0),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
            matrix_rows.append(row)
            if policy_id == "fixed_holding_window":
                fixed_metric = row
            if best_metric is None or float(row["net_return_after_fees_slippage_funding"]) > float(best_metric["net_return_after_fees_slippage_funding"]):
                best_metric = row
                best_policy = policy_id
        if simulation_error_reason is not None:
            gates.append(_blocked_gate(lead_record, lead_hash, simulation_error_reason))
        else:
            gates.append(_gate_from_metrics(lead_record, lead_hash, fixed_metric, best_metric, best_policy))

    matrix = pd.DataFrame(matrix_rows, columns=_matrix_columns())
    candidate_gates = pd.DataFrame(gates, columns=_candidate_gate_columns())
    trades = pd.concat(trade_frames, ignore_index=True) if trade_frames else _empty_trades()
    manifest = {
        "exit_lab_manifest_version": DISCOVERY_EXIT_LAB_MANIFEST_VERSION,
        "exit_lab_version": DISCOVERY_EXIT_LAB_VERSION,
        "frozen_entry_exit_lab_version": FROZEN_ENTRY_EXIT_LAB_VERSION,
        "exit_lab_scope": "frozen_entry_primary_bar_exit_comparison",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_discovery_manifest_path": str(manifest_path),
        "symbol": discovery_manifest.get("symbol"),
        "entry_signals_path": str(entry_signals_path) if entry_signals_path else None,
        "market_data_path": str(market_path),
        "input_ranking_row_count": int(len(interesting)),
        "selected_lead_count": int(len(leads)),
        "comparison_count": int(len(matrix)),
        "candidate_gate_row_count": int(len(candidate_gates)),
        "decision_counts": _value_counts(candidate_gates, "exit_lab_gate_status"),
        "exit_policies": policies,
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    return {"manifest": manifest, "matrix": matrix, "candidate_gates": candidate_gates, "trades": trades}


def _blocked_result(
    *,
    discovery_manifest: Mapping[str, Any],
    discovery_manifest_path: Path,
    lead_count: int,
    reason: str,
    leads: pd.DataFrame | None = None,
) -> dict[str, Any]:
    gate_rows: list[dict[str, Any]] = []
    if leads is not None and not leads.empty:
        for _, lead in leads.iterrows():
            lead_record = {str(key): value for key, value in lead.to_dict().items()}
            lead_hash = discovery_entry_lead_evidence_sha256(lead_record)
            gate_rows.append(_blocked_gate(lead_record, lead_hash, reason))
    if not gate_rows:
        gate_rows.append(_empty_blocked_gate(reason))
    gates = pd.DataFrame(gate_rows, columns=_candidate_gate_columns())
    manifest = {
        "exit_lab_manifest_version": DISCOVERY_EXIT_LAB_MANIFEST_VERSION,
        "exit_lab_version": DISCOVERY_EXIT_LAB_VERSION,
        "frozen_entry_exit_lab_version": FROZEN_ENTRY_EXIT_LAB_VERSION,
        "exit_lab_scope": "frozen_entry_primary_bar_exit_comparison",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "source_discovery_manifest_path": str(discovery_manifest_path),
        "input_ranking_row_count": int(lead_count),
        "selected_lead_count": int(lead_count),
        "comparison_count": 0,
        "candidate_gate_row_count": int(len(gates)),
        "decision_counts": {"blocked": int(len(gates))},
        "blocked_reason": reason,
        "symbol": discovery_manifest.get("symbol"),
        "candidate_pack_written": False,
        "candidate_pack_paths": [],
        "live_fetch_used": False,
        "order_placement_used": False,
        "runtime_mode_changed": False,
    }
    return {"manifest": manifest, "matrix": pd.DataFrame(columns=_matrix_columns()), "candidate_gates": gates, "trades": _empty_trades()}


def _select_leads(frame: pd.DataFrame, *, max_candidates: int) -> pd.DataFrame:
    if frame.empty:
        return frame
    result = frame.copy()
    for column in ("realized_expectancy", "independent_event_expectancy", "final_score", "trade_count"):
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)
    sort_columns = [column for column in ("realized_expectancy", "independent_event_expectancy", "final_score", "trade_count") if column in result.columns]
    if sort_columns:
        result = result.sort_values(sort_columns, ascending=[False] * len(sort_columns), kind="mergesort")
    return result.head(max(1, int(max_candidates))).reset_index(drop=True)


def _signals_for_lead(signals: pd.DataFrame, lead: Mapping[str, Any]) -> pd.DataFrame:
    if signals.empty:
        return signals
    masks = []
    for column in ("candidate_id", "trial_id", "record_sha256"):
        if column in signals.columns and lead.get(column):
            masks.append(signals[column].astype(str).eq(str(lead.get(column))))
    if not masks:
        return pd.DataFrame(columns=signals.columns)
    mask = masks[0]
    for item in masks[1:]:
        mask = mask | item
    return signals.loc[mask].copy()


def _signal_frame(signals: pd.DataFrame, discovery_manifest: Mapping[str, Any]) -> pd.DataFrame:
    frame = signals.copy()
    signal_times: pd.Series | None = None
    for candidate in ("decision_time_ms", "bar_time_ms", "signal_bar_time_ms", "time_ms"):
        if candidate in frame.columns:
            times = pd.to_numeric(frame[candidate], errors="coerce")
            if times.notna().any():
                signal_times = times
                break
    if signal_times is None:
        return pd.DataFrame(columns=["decision_time_ms", "side", "symbol", "signal_id"])
    frame["decision_time_ms"] = signal_times
    if "side" not in frame.columns:
        frame["side"] = "long"
    if "symbol" not in frame.columns:
        frame["symbol"] = str(discovery_manifest.get("symbol") or "")
    if "signal_bar_close" not in frame.columns and "close" in frame.columns:
        frame["signal_bar_close"] = pd.to_numeric(frame["close"], errors="coerce")
    if "signal_id" not in frame.columns:
        frame["signal_id"] = [f"frozen-entry-{index:06d}" for index in range(len(frame))]
    required = ["decision_time_ms", "side", "symbol", "signal_id"]
    result = frame.dropna(subset=required).reset_index(drop=True)
    if result.empty:
        return pd.DataFrame(columns=required)
    result = result.loc[result["decision_time_ms"].abs().lt(float("inf"))].copy()
    if result.empty:
        return pd.DataFrame(columns=required)
    result["decision_time_ms"] = pd.to_numeric(result["decision_time_ms"], errors="coerce").astype("int64")
    result["side"] = result["side"].astype(str).str.strip().str.lower()
    result = result.loc[result["side"].isin({"long", "short"})].copy()
    if "signal_bar_close" in result.columns:
        result["signal_bar_close"] = pd.to_numeric(result["signal_bar_close"], errors="coerce")
        result = result.loc[result["signal_bar_close"].abs().lt(float("inf")) & result["signal_bar_close"].gt(0.0)].copy()
    if result.empty:
        return pd.DataFrame(columns=required)
    return result


def _market_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "bar_time_ms" not in result.columns:
        for column in ("signal_bar_time_ms", "time_ms"):
            if column in result.columns:
                times = pd.to_numeric(result[column], errors="coerce")
                if times.notna().any():
                    result["bar_time_ms"] = times
                break
    required = {"bar_time_ms", "open", "high", "low", "close"}
    if not required <= set(result.columns):
        return pd.DataFrame(columns=sorted(required))
    for column in ("bar_time_ms", "open", "high", "low", "close"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=list(required))
    finite_mask = result["bar_time_ms"].abs().lt(float("inf"))
    for column in ("open", "high", "low", "close"):
        finite_mask = finite_mask & result[column].abs().lt(float("inf")) & result[column].gt(0.0)
    return result.loc[finite_mask].sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)


def _gate_from_metrics(
    lead: Mapping[str, Any],
    lead_hash: str,
    fixed_metric: Mapping[str, Any] | None,
    best_metric: Mapping[str, Any] | None,
    best_policy: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    fixed_return = float((fixed_metric or {}).get("net_return_after_fees_slippage_funding") or 0.0)
    best_return = float((best_metric or {}).get("net_return_after_fees_slippage_funding") or 0.0)
    if best_metric is None or int(best_metric.get("trade_count") or 0) <= 0:
        reasons.append("frozen_entry_no_trades")
    if best_policy in {"", "fixed_holding_window"}:
        reasons.append("simple_runner_did_not_beat_fixed_holding")
    if best_return <= fixed_return:
        reasons.append("exit_lab_no_improving_exit_over_fixed_holding")
    status = "passed" if not reasons else "blocked"
    candidate_id = str(lead.get("candidate_id") or "")
    best_family = _exit_family(best_policy)
    return {
        "entry_candidate_id": candidate_id,
        "candidate_id": candidate_id,
        "trial_id": lead.get("trial_id"),
        "record_sha256": lead.get("record_sha256"),
        "entry_lead_evidence_sha256": lead_hash,
        "entry_lead_record_sha256": lead_hash,
        "exit_lab_status": "complete",
        "exit_lab_gate_status": status,
        "exit_lab_reasons": "|".join(reasons),
        "exit_lab_best_family": best_family if status == "passed" else "",
        "best_comparison_id": "simple_runner_v1_vs_fixed_holding",
        "baseline_exit_policy_id": "fixed_holding_window",
        "treatment_exit_policy_id": best_policy,
        "fixed_holding_score_delta": best_return - fixed_return,
        "fixed_holding_comparator_delta": best_return - fixed_return,
        "cost_stress_status": "complete",
        "no_improvement_reason": "exit_lab_no_improving_exit_over_fixed_holding" if status != "passed" else "",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _blocked_gate(lead: Mapping[str, Any], lead_hash: str, reason: str) -> dict[str, Any]:
    candidate_id = str(lead.get("candidate_id") or "")
    return {
        "entry_candidate_id": candidate_id,
        "candidate_id": candidate_id,
        "trial_id": lead.get("trial_id"),
        "record_sha256": lead.get("record_sha256"),
        "entry_lead_evidence_sha256": lead_hash,
        "entry_lead_record_sha256": lead_hash,
        "exit_lab_status": "blocked",
        "exit_lab_gate_status": "blocked",
        "exit_lab_reasons": reason,
        "exit_lab_best_family": "",
        "best_comparison_id": "simple_runner_v1_vs_fixed_holding",
        "baseline_exit_policy_id": "fixed_holding_window",
        "treatment_exit_policy_id": "",
        "fixed_holding_score_delta": 0.0,
        "fixed_holding_comparator_delta": 0.0,
        "cost_stress_status": "blocked",
        "no_improvement_reason": reason,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _empty_blocked_gate(reason: str) -> dict[str, Any]:
    return {
        "entry_candidate_id": "",
        "candidate_id": "",
        "trial_id": "",
        "record_sha256": "",
        "entry_lead_evidence_sha256": "",
        "entry_lead_record_sha256": "",
        "exit_lab_status": "blocked",
        "exit_lab_gate_status": "blocked",
        "exit_lab_reasons": reason,
        "exit_lab_best_family": "",
        "best_comparison_id": "simple_runner_v1_vs_fixed_holding",
        "baseline_exit_policy_id": "fixed_holding_window",
        "treatment_exit_policy_id": "",
        "fixed_holding_score_delta": 0.0,
        "fixed_holding_comparator_delta": 0.0,
        "cost_stress_status": "blocked",
        "no_improvement_reason": reason,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _exit_family(policy_id: str) -> str:
    return "trailing_risk" if str(policy_id) == "simple_runner_v1" else "fixed_holding"


def _resolve_market_data_path(discovery_manifest: Mapping[str, Any], raw_path: str | Path | None) -> Path | None:
    if raw_path:
        return Path(raw_path).expanduser().resolve()
    data = discovery_manifest.get("data_evidence") if isinstance(discovery_manifest.get("data_evidence"), Mapping) else {}
    if data.get("dataset_path"):
        return Path(str(data["dataset_path"])).expanduser().resolve()
    return None


def _resolve_output_path(raw_path: Any, fallback: Path) -> Path:
    if not raw_path:
        return fallback
    return Path(str(raw_path)).expanduser().resolve()


def _read_frame(path: Path, *, malformed_reason: str) -> _FrameReadResult:
    if not path.is_file():
        return _FrameReadResult(pd.DataFrame())
    try:
        return _FrameReadResult(pd.read_parquet(path))
    except Exception:
        return _FrameReadResult(pd.DataFrame(), malformed_reason)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _holding_ms(label_horizon: str) -> int:
    text = str(label_horizon or "1h").strip().lower()
    unit = text[-1:]
    try:
        value = float(text[:-1])
    except ValueError:
        return MIN_EXIT_LAB_HOLDING_MS
    if not math.isfinite(value) or value <= 0.0:
        return MIN_EXIT_LAB_HOLDING_MS
    if unit == "m":
        return int(value * 60_000)
    if unit == "h":
        return int(value * 60 * 60_000)
    if unit == "d":
        return int(value * 24 * 60 * 60_000)
    return MIN_EXIT_LAB_HOLDING_MS


def _normalized_holding_ms(label_horizon: str) -> int | None:
    holding_ms = _holding_ms(label_horizon)
    if holding_ms > MAX_EXIT_LAB_HOLDING_MS:
        return None
    return max(holding_ms, MIN_EXIT_LAB_HOLDING_MS)


def _infer_interval_ms(frame: pd.DataFrame) -> int:
    if "bar_time_ms" not in frame.columns or len(frame) < 2:
        return 900_000
    times = pd.to_numeric(frame["bar_time_ms"], errors="coerce").dropna().sort_values(kind="mergesort")
    diffs = times.diff().dropna()
    diffs = diffs[diffs > 0]
    return 900_000 if diffs.empty else int(diffs.median())


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {str(key): int(value) for key, value in frame[column].astype(str).value_counts(dropna=False).sort_index().items()}


def _empty_trades() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "trade_id",
            "signal_id",
            "symbol",
            "side",
            "entry_time_ms",
            "exit_time_ms",
            "entry_price",
            "exit_price",
            "net_return",
            "exit_policy_id",
            "candidate_id",
            "entry_lead_evidence_sha256",
        ]
    )


def _matrix_columns() -> list[str]:
    return [
        "entry_candidate_id",
        "research_candidate_id",
        "candidate_id",
        "trial_id",
        "record_sha256",
        "entry_lead_evidence_sha256",
        "exit_policy_id",
        "exit_policy_params_json",
        "trade_count",
        "net_return_after_fees_slippage_funding",
        "expectancy_per_trade",
        "profit_factor",
        "max_drawdown",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _candidate_gate_columns() -> list[str]:
    return [
        "entry_candidate_id",
        "candidate_id",
        "trial_id",
        "record_sha256",
        "entry_lead_evidence_sha256",
        "entry_lead_record_sha256",
        "exit_lab_status",
        "exit_lab_gate_status",
        "exit_lab_reasons",
        "exit_lab_best_family",
        "best_comparison_id",
        "baseline_exit_policy_id",
        "treatment_exit_policy_id",
        "fixed_holding_score_delta",
        "fixed_holding_comparator_delta",
        "cost_stress_status",
        "no_improvement_reason",
        "research_only",
        "observe_only",
        "promotion_ready",
    ]


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
