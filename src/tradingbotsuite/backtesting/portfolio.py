from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class PortfolioAllocation:
    position_fraction: float = 1.0
    max_concurrent_positions: int = 1

    def to_payload(self) -> dict[str, object]:
        return {
            "position_fraction": float(self.position_fraction),
            "max_concurrent_positions": int(self.max_concurrent_positions),
        }


class PortfolioSimulator:
    """Deterministic single-asset allocation layer for Stage 5 research fixtures."""

    def allocate(self, candidate_positions: pd.DataFrame, risk_state: dict[str, object] | None = None) -> pd.DataFrame:
        _ = risk_state
        if candidate_positions.empty:
            return candidate_positions.copy()
        ordered = candidate_positions.sort_values("entry_time_ms", kind="mergesort").reset_index(drop=True)
        accepted_rows: list[dict[str, object]] = []
        next_available_time = -1
        for row in ordered.to_dict("records"):
            entry_time = int(row["entry_time_ms"])
            if entry_time < next_available_time:
                continue
            accepted_rows.append(row)
            next_available_time = int(row["exit_time_ms"])
        return pd.DataFrame(accepted_rows, columns=ordered.columns)
