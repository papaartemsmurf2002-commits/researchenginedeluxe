from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from tradingbotsuite.v2.backtest_engine import BacktestRunConfig, run_vectorized_backtest
from tradingbotsuite.v2.costs import CostModelConfig
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def test_next_bar_open_signal_applies_to_next_rows_open_close_return(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="next-bar-open-causal"),
        strategy_spec=_funding_carry_spec(),
        panel_rows=[
            _row("2024-01-01T00:00:00Z", open_price=100.0, close=50.0, funding=-0.001),
            _row("2024-01-01T01:00:00Z", open_price=100.0, close=110.0, funding=0.0),
            _row("2024-01-01T02:00:00Z", open_price=100.0, close=100.0, funding=0.0),
        ],
    )

    assert result.metrics is not None
    assert result.metrics.gross_return == pytest.approx(0.05 * 0.10)
    assert result.metrics.net_return == pytest.approx(0.05 * 0.10)

    positions = pq.read_table(Path(result.run_dir) / "positions.parquet").to_pylist()
    assert positions[0]["applied_weight"] == pytest.approx(0.0)
    assert positions[0]["target_weight"] == pytest.approx(0.05)
    assert positions[0]["price_return"] == pytest.approx(-0.50)
    assert positions[0]["gross_pnl"] == pytest.approx(0.0)
    assert positions[1]["applied_weight"] == pytest.approx(0.05)
    assert positions[1]["target_weight"] == pytest.approx(0.0)
    assert positions[1]["price_return"] == pytest.approx(0.10)
    assert positions[1]["gross_pnl"] == pytest.approx(0.005)


def test_backtest_writes_monthly_validation_folds_capped_at_four(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="monthly-folds"),
        strategy_spec=_funding_carry_spec(),
        panel_rows=_daily_rows(datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 6, 1, tzinfo=UTC)),
    )

    assert result.metrics is not None
    fold_rows = pq.read_table(Path(result.run_dir) / "fold_metrics.parquet").to_pylist()
    monthly_rows = [row for row in fold_rows if row["fold_family"] == "monthly_validation"]
    diagnostic_rows = [row for row in fold_rows if row["fold_family"] == "diagnostic"]

    assert [row["fold_id"] for row in monthly_rows] == [
        "month-2024-01",
        "month-2024-02",
        "month-2024-03",
        "month-2024-04",
    ]
    assert len(diagnostic_rows) == 1
    assert diagnostic_rows[0]["fold_id"] == "full_window"


def _config(output_root: Path, *, run_id: str) -> BacktestRunConfig:
    cost_model = CostModelConfig(
        cost_model_id="zero_research_costs_v1",
        fee_bps=0.0,
        spread_bps=0.0,
        slippage_bps=0.0,
        impact_bps=0.0,
        funding_required=False,
        funding_missing_policy="explicit_zero",
    )
    return BacktestRunConfig(
        run_id=run_id,
        experiment_id="phase12-backtest-policy",
        output_root=str(output_root),
        archive_snapshot_id="archive-snapshot",
        universe_snapshot_id="universe-snapshot",
        data_manifest_id="data-manifest",
        data_manifest_hash=HEX_A,
        validation_manifest_hash=HEX_B,
        cost_manifest_hash=HEX_C,
        cost_model_id=cost_model.cost_model_id,
        cost_model=cost_model,
        universe_mode="as_of",
        venue_scope="hyperliquid",
        git_sha="test-git-sha",
    )


def _funding_carry_spec() -> dict[str, object]:
    payload = json.loads(json.dumps(example_strategy_payloads()["hl_funding_carry_v1"]))
    payload["strategy_id"] = "phase12_next_bar_funding_carry"
    payload["inputs"]["timeframe"] = "1h"
    payload["inputs"]["fields"] = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "funding",
        "funding_rate",
        "coverage_ratio",
    ]
    payload["logic"]["entry_threshold"] = 0.0
    payload["risk"]["max_gross_leverage"] = 0.05
    payload["risk"]["max_instrument_weight"] = 0.05
    payload["execution"]["price_basis"] = "next_bar_open"
    return payload


def _row(ts: str, *, open_price: float, close: float, funding: float) -> dict[str, object]:
    return {
        "ts": ts,
        "instrument_id": "hyperliquid:perp:BTC",
        "open": open_price,
        "high": max(open_price, close),
        "low": min(open_price, close),
        "close": close,
        "volume": 1_000_000.0,
        "funding": funding,
        "funding_rate": funding,
        "coverage_ratio": 1.0,
    }


def _daily_rows(start: datetime, end: datetime) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start
    index = 0
    while current < end:
        funding = -0.001 if index % 2 == 0 else 0.0
        close = 100.0 * (1.001 if index % 3 else 0.999)
        rows.append(
            _row(
                current.isoformat().replace("+00:00", "Z"),
                open_price=100.0,
                close=close,
                funding=funding,
            )
        )
        current += timedelta(days=1)
        index += 1
    return rows
