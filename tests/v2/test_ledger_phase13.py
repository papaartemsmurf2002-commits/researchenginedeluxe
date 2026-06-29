from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.ledger import (
    LedgerAppendRequest,
    LedgerError,
    append_run_to_ledger,
    compact_ledger_parts,
    export_ledger,
    leaderboard,
    read_ledger,
)


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
_DEFAULT_METRICS = object()


def test_ledger_append_rejects_missing_run_manifest(tmp_path) -> None:
    with pytest.raises(LedgerError, match="run_manifest_missing"):
        append_run_to_ledger(
            LedgerAppendRequest(
                run_manifest_path=str(tmp_path / "missing.json"),
                ledger_path=str(tmp_path / "ledger.parquet"),
            )
        )


def test_ledger_append_rejects_missing_validation_status(tmp_path) -> None:
    run_manifest = _write_run_manifest(tmp_path, "missing-validation")
    payload = json.loads(run_manifest.read_text(encoding="utf-8"))
    del payload["validation_status"]
    run_manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(LedgerError, match="validation_status_missing"):
        append_run_to_ledger(
            LedgerAppendRequest(
                run_manifest_path=str(run_manifest),
                ledger_path=str(tmp_path / "ledger.parquet"),
            )
        )


def test_ledger_records_failed_trials(tmp_path) -> None:
    run_manifest = _write_run_manifest(
        tmp_path,
        "failed-trial",
        status="failed",
        validation_status="fail",
        failure_reason="synthetic_failure",
        metrics=None,
    )
    ledger_path = tmp_path / "ledger.parquet"

    row = append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(run_manifest), ledger_path=str(ledger_path))
    )
    rows = read_ledger(ledger_path)

    assert row.row_status == "failed"
    assert row.net_return is None
    assert row.failure_reason == "synthetic_failure"
    assert rows[0].blocker_reasons == (
        "synthetic_failure",
        "run_status_failed",
        "validation_status_fail",
    )


def test_ledger_append_uses_validation_gate_manifest_when_provided(tmp_path) -> None:
    run_manifest = _write_run_manifest(tmp_path, "validation-gate-failed-run")
    validation_manifest = _write_validation_gate_manifest(
        run_manifest,
        validation_status="fail",
        blocker_reasons=["cost_dependent_failure"],
        cost_fragile_warning=True,
    )
    ledger_path = tmp_path / "ledger.parquet"

    row = append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(run_manifest),
            validation_manifest_path=str(validation_manifest),
            ledger_path=str(ledger_path),
            evidence_mode="sandbox_diagnostic",
        )
    )
    rows = read_ledger(ledger_path)

    assert row.row_status == "succeeded"
    assert row.validation_status == "fail"
    assert row.walk_forward_pass is False
    assert row.fold_count == 1
    assert row.fold_stability_score == 0.0
    assert row.cost_fragile_warning is True
    assert row.blocker_reasons == ("validation_status_fail", "cost_dependent_failure")
    assert row.validation_manifest_path == str(validation_manifest.resolve(strict=False))
    assert rows[0] == row


def test_ledger_append_rejects_validation_gate_manifest_for_different_run(tmp_path) -> None:
    run_manifest = _write_run_manifest(tmp_path, "validation-gate-source-run")
    other_run_manifest = _write_run_manifest(tmp_path, "validation-gate-other-run")
    validation_manifest = _write_validation_gate_manifest(
        other_run_manifest,
        validation_status="fail",
        blocker_reasons=["cost_dependent_failure"],
    )

    with pytest.raises(LedgerError, match="validation_manifest_run_id_mismatch"):
        append_run_to_ledger(
            LedgerAppendRequest(
                run_manifest_path=str(run_manifest),
                validation_manifest_path=str(validation_manifest),
                ledger_path=str(tmp_path / "ledger.parquet"),
            )
        )


def test_ledger_rejects_duplicate_run_id(tmp_path) -> None:
    run_manifest = _write_run_manifest(tmp_path, "duplicate-run")
    ledger_path = tmp_path / "ledger.parquet"
    request = LedgerAppendRequest(run_manifest_path=str(run_manifest), ledger_path=str(ledger_path))

    append_run_to_ledger(request)

    with pytest.raises(LedgerError, match="duplicate_run_id"):
        append_run_to_ledger(request)


def test_ledger_append_maintains_sidecar_index(tmp_path) -> None:
    first = _write_run_manifest(tmp_path, "indexed-run-a")
    second = _write_run_manifest(tmp_path, "indexed-run-b")
    ledger_path = tmp_path / "ledger.parquet"

    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(first), ledger_path=str(ledger_path))
    )
    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(second), ledger_path=str(ledger_path))
    )

    index_path = ledger_path.with_suffix(".index.json")
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    rows = read_ledger(ledger_path)
    append_log = ledger_path.with_suffix(".parts") / "append_log.jsonl"

    assert payload["schema_version"] == "ledger_part_index_v1"
    assert payload["storage_mode"] == "append_parts"
    assert payload["row_count"] == 2
    assert payload["run_ids"] == {"indexed-run-a": 0, "indexed-run-b": 1}
    assert len(payload["parts"]) == 1
    assert payload["parts"][0]["row_count"] == 2
    assert payload["parts"][0]["run_ids"] == ["indexed-run-a", "indexed-run-b"]
    assert ledger_path.exists()
    assert pq.read_table(ledger_path).num_rows == 0
    assert append_log.exists()
    assert len(append_log.read_text(encoding="utf-8").strip().splitlines()) == 2
    assert [row.run_id for row in rows] == ["indexed-run-a", "indexed-run-b"]


def test_ledger_part_batch_respects_max_part_rows(tmp_path) -> None:
    first = _write_run_manifest(tmp_path, "part-cap-run-a")
    second = _write_run_manifest(tmp_path, "part-cap-run-b")
    ledger_path = tmp_path / "ledger.parquet"

    append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(first),
            ledger_path=str(ledger_path),
            max_part_rows=1,
        )
    )
    append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(second),
            ledger_path=str(ledger_path),
            max_part_rows=1,
        )
    )
    payload = json.loads(ledger_path.with_suffix(".index.json").read_text(encoding="utf-8"))
    rows = read_ledger(ledger_path)

    assert len(payload["parts"]) == 2
    assert [part["row_count"] for part in payload["parts"]] == [1, 1]
    assert [row.run_id for row in rows] == ["part-cap-run-a", "part-cap-run-b"]


def test_ledger_parts_compact_to_current_parquet_and_keep_appending(tmp_path) -> None:
    first = _write_run_manifest(tmp_path, "compact-run-a")
    second = _write_run_manifest(tmp_path, "compact-run-b")
    third = _write_run_manifest(tmp_path, "compact-run-c")
    ledger_path = tmp_path / "ledger.parquet"

    append_run_to_ledger(LedgerAppendRequest(run_manifest_path=str(first), ledger_path=str(ledger_path)))
    append_run_to_ledger(LedgerAppendRequest(run_manifest_path=str(second), ledger_path=str(ledger_path)))
    compacted = compact_ledger_parts(ledger_path)
    append_run_to_ledger(LedgerAppendRequest(run_manifest_path=str(third), ledger_path=str(ledger_path)))
    payload = json.loads(ledger_path.with_suffix(".index.json").read_text(encoding="utf-8"))
    rows = read_ledger(ledger_path)

    assert compacted.exists()
    assert payload["compacted_path"] == str(compacted)
    assert payload["row_count"] == 3
    assert len(payload["parts"]) == 1
    assert [row.run_id for row in rows] == ["compact-run-a", "compact-run-b", "compact-run-c"]


def test_ledger_rejects_part_index_run_id_drift(tmp_path) -> None:
    run_manifest = _write_run_manifest(tmp_path, "index-drift-run")
    ledger_path = tmp_path / "ledger.parquet"
    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(run_manifest), ledger_path=str(ledger_path))
    )
    index_path = ledger_path.with_suffix(".index.json")
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["run_ids"] = {"forged-run": 0}
    payload["parts"][0]["run_ids"] = ["forged-run"]
    index_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")

    with pytest.raises(LedgerError, match="ledger_part_index_append_log_mismatch"):
        append_run_to_ledger(
            LedgerAppendRequest(run_manifest_path=str(run_manifest), ledger_path=str(ledger_path))
        )


def test_ledger_read_rejects_part_index_that_disagrees_with_rows(tmp_path) -> None:
    run_manifest = _write_run_manifest(tmp_path, "row-index-drift-run")
    ledger_path = tmp_path / "ledger.parquet"
    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(run_manifest), ledger_path=str(ledger_path))
    )
    append_log = ledger_path.with_suffix(".parts") / "append_log.jsonl"
    append_log.unlink()
    index_path = ledger_path.with_suffix(".index.json")
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["run_ids"] = {"forged-row-run": 0}
    payload["parts"][0]["run_ids"] = ["forged-row-run"]
    index_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")

    with pytest.raises(LedgerError, match="ledger_part_index_run_ids_mismatch"):
        read_ledger(ledger_path)


def test_ledger_part_hash_drift_fails_closed_without_rewriting_placeholder(tmp_path) -> None:
    first = _write_run_manifest(tmp_path, "hash-drift-run-a")
    second = _write_run_manifest(tmp_path, "hash-drift-run-b")
    ledger_path = tmp_path / "ledger.parquet"
    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(first), ledger_path=str(ledger_path))
    )
    payload = json.loads(ledger_path.with_suffix(".index.json").read_text(encoding="utf-8"))
    part_path = Path(payload["parts"][0]["path"])
    part_path.write_bytes(b"corrupt-part")

    with pytest.raises(LedgerError, match="ledger_part_hash_mismatch"):
        append_run_to_ledger(
            LedgerAppendRequest(run_manifest_path=str(second), ledger_path=str(ledger_path))
        )

    assert pq.read_table(ledger_path).num_rows == 0


def test_ledger_cli_compact_writes_current_parquet(tmp_path, capsys) -> None:
    first = _write_run_manifest(tmp_path, "cli-compact-run-a")
    second = _write_run_manifest(tmp_path, "cli-compact-run-b")
    ledger_path = tmp_path / "ledger.parquet"
    append_run_to_ledger(LedgerAppendRequest(run_manifest_path=str(first), ledger_path=str(ledger_path)))
    append_run_to_ledger(LedgerAppendRequest(run_manifest_path=str(second), ledger_path=str(ledger_path)))

    exit_code = main(["ledger", "compact", "--ledger", str(ledger_path)])
    output = capsys.readouterr().out
    payload = json.loads(ledger_path.with_suffix(".index.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "ledger_compacted=" in output
    assert "generated_from_canonical=true" in output
    assert Path(payload["compacted_path"]).exists()
    assert payload["compacted_sha256"] == file_sha256(Path(payload["compacted_path"]))
    assert [row.run_id for row in read_ledger(ledger_path)] == [
        "cli-compact-run-a",
        "cli-compact-run-b",
    ]


def test_ledger_rejects_compacted_hash_drift(tmp_path) -> None:
    first = _write_run_manifest(tmp_path, "compact-hash-run-a")
    second = _write_run_manifest(tmp_path, "compact-hash-run-b")
    ledger_path = tmp_path / "ledger.parquet"
    append_run_to_ledger(LedgerAppendRequest(run_manifest_path=str(first), ledger_path=str(ledger_path)))
    append_run_to_ledger(LedgerAppendRequest(run_manifest_path=str(second), ledger_path=str(ledger_path)))
    compacted = compact_ledger_parts(ledger_path)
    compacted.write_bytes(b"corrupt-compacted")

    with pytest.raises(LedgerError, match="ledger_compacted_hash_mismatch"):
        read_ledger(ledger_path)


def test_xlsx_export_is_generated_from_canonical_ledger(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.parquet"
    run_manifest = _write_run_manifest(tmp_path, "xlsx-source")
    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(run_manifest), ledger_path=str(ledger_path))
    )
    xlsx_path = tmp_path / "ledger.xlsx"
    csv_path = tmp_path / "ledger.csv"

    export_ledger(ledger_path=ledger_path, output_path=xlsx_path, export_format="xlsx")
    export_ledger(ledger_path=ledger_path, output_path=csv_path, export_format="csv")

    assert xlsx_path.exists()
    assert csv_path.exists()
    with zipfile.ZipFile(xlsx_path) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "xlsx-source" in sheet
    assert "xlsx-source" in csv_path.read_text(encoding="utf-8")


def test_manual_spreadsheet_edit_is_not_canonical(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.parquet"
    run_manifest = _write_run_manifest(tmp_path, "canonical-run")
    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(run_manifest), ledger_path=str(ledger_path))
    )
    xlsx_path = tmp_path / "ledger.xlsx"
    export_ledger(ledger_path=ledger_path, output_path=xlsx_path, export_format="xlsx")
    xlsx_path.write_text("manual spreadsheet edit: fake-run", encoding="utf-8")

    rows = read_ledger(ledger_path)
    export_ledger(ledger_path=ledger_path, output_path=xlsx_path, export_format="xlsx")

    assert [row.run_id for row in rows] == ["canonical-run"]
    with zipfile.ZipFile(xlsx_path) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "canonical-run" in sheet
    assert "fake-run" not in sheet


def test_leaderboard_excludes_sandbox_current_universe_claims(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.parquet"
    accepted = _write_run_manifest(tmp_path, "accepted-run", net_return=0.12)
    sandbox = _write_run_manifest(tmp_path, "sandbox-run", net_return=0.4)
    current = _write_run_manifest(tmp_path, "current-run", net_return=0.5, universe_mode="current")

    append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(accepted),
            ledger_path=str(ledger_path),
            evidence_mode="accepted_research",
        )
    )
    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(sandbox), ledger_path=str(ledger_path))
    )
    append_run_to_ledger(
        LedgerAppendRequest(run_manifest_path=str(current), ledger_path=str(ledger_path))
    )

    rows = leaderboard(
        ledger_path=ledger_path,
        require_validation_pass=True,
        exclude_sandbox=True,
    )

    assert [row.run_id for row in rows] == ["accepted-run"]


def test_leaderboard_ranks_net_not_gross(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.parquet"
    gross_heavy = _write_run_manifest(
        tmp_path,
        "gross-heavy",
        gross_return=1.0,
        net_return=0.05,
    )
    net_leader = _write_run_manifest(
        tmp_path,
        "net-leader",
        gross_return=0.15,
        net_return=0.2,
    )

    append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(gross_heavy),
            ledger_path=str(ledger_path),
            evidence_mode="accepted_research",
        )
    )
    append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(net_leader),
            ledger_path=str(ledger_path),
            evidence_mode="accepted_research",
        )
    )

    rows = leaderboard(
        ledger_path=ledger_path,
        require_validation_pass=True,
        exclude_sandbox=True,
    )

    assert [row.run_id for row in rows] == ["net-leader", "gross-heavy"]


def _write_run_manifest(
    root: Path,
    run_id: str,
    *,
    status: str = "succeeded",
    validation_status: str = "pass",
    failure_reason: str | None = None,
    metrics: dict | None | object = _DEFAULT_METRICS,
    gross_return: float = 0.1,
    net_return: float = 0.08,
    universe_mode: str = "as_of",
) -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if metrics is _DEFAULT_METRICS:
        metrics = _metrics(run_id, gross_return=gross_return, net_return=net_return)
    payload = {
        "schema_version": "run_manifest_v1",
        "run_id": run_id,
        "experiment_id": "phase13-test",
        "trial_index": 0,
        "agent_or_user": "agent",
        "created_at": "2024-08-01T00:00:00Z",
        "status": status,
        "engine_lane": "vectorized",
        "strategy_lane": "declarative",
        "git_sha": "test-git-sha",
        "environment_hash": HEX_A,
        "strategy_id": "strategy_ledger_smoke",
        "strategy_version": "0.1.0",
        "strategy_hash": HEX_B,
        "strategy_spec_hash": HEX_B,
        "params_hash": HEX_C,
        "archive_snapshot_id": "archive-snapshot",
        "universe_snapshot_id": "universe-snapshot",
        "data_manifest_id": "data-manifest",
        "data_manifest_hash": HEX_A,
        "validation_manifest_hash": HEX_B,
        "cost_manifest_hash": HEX_C,
        "universe_mode": universe_mode,
        "venue_scope": "hyperliquid",
        "instrument_count": 3,
        "timeframe": "1h",
        "backtest_start": _iso(datetime(2024, 1, 1, tzinfo=UTC)),
        "backtest_end": _iso(datetime(2024, 8, 1, tzinfo=UTC)),
        "usable_months": 7,
        "lockbox_policy_id": "dynamic_full_calendar_months_v1",
        "lockbox_start": None,
        "lockbox_end": None,
        "data_coverage_min": 0.98,
        "cost_model_id": "conservative_hyperliquid_taker_v1",
        "cost_model_hash": HEX_A,
        "validation_policy_id": "validation-v1",
        "validation_status": validation_status,
        "missing_data_policy": "fail_closed",
        "price_basis": "next_bar_open",
        "failure_reason": failure_reason,
        "metrics": metrics,
        "artifacts": {
            name: {"name": name, "path": path, "sha256": HEX_A, "required": True}
            for name, path in _artifact_paths().items()
        },
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
    }
    if metrics is None:
        payload["metrics"] = None
    path = run_dir / "run_manifest.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return path


def _write_validation_gate_manifest(
    run_manifest: Path,
    *,
    validation_status: str = "pass",
    blocker_reasons: list[str] | None = None,
    cost_fragile_warning: bool = False,
) -> Path:
    payload = json.loads(run_manifest.read_text(encoding="utf-8"))
    blockers = [] if blocker_reasons is None else blocker_reasons
    path = run_manifest.parent / "validation_gate_manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "validation_gate_manifest_v1",
                "validation_manifest_id": "d" * 64,
                "run_id": payload["run_id"],
                "run_manifest_path": str(run_manifest),
                "run_manifest_sha256": file_sha256(run_manifest),
                "validation_status": validation_status,
                "evidence_mode": "sandbox_diagnostic",
                "blocker_reasons": blockers,
                "fold_count": 1,
                "positive_fold_count": 1 if validation_status == "pass" else 0,
                "fold_stability_score": 1.0 if validation_status == "pass" else 0.0,
                "cost_stress_scenarios": ["base", "stress_2x", "stress_3x"],
                "cost_fragile_warning": cost_fragile_warning,
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_evidence": False,
                "candidate_pack_eligible": False,
                "live_signal": False,
                "paper_signal": False,
                "sizing_instruction": False,
                "order_placement_instruction": False,
                "runtime_mode_change": False,
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _metrics(run_id: str, *, gross_return: float, net_return: float) -> dict[str, object]:
    return {
        "schema_version": "v2",
        "run_id": run_id,
        "status": "succeeded",
        "gross_return": gross_return,
        "net_return": net_return,
        "gross_equity_final": 1.0 + gross_return,
        "net_equity_final": 1.0 + net_return,
        "total_fee_cost": 0.01,
        "total_spread_cost": 0.002,
        "total_slippage_cost": 0.003,
        "total_impact_cost": 0.001,
        "total_transaction_cost": 0.016,
        "total_funding_pnl": 0.0,
        "total_turnover": 2.0,
        "trade_count": 4,
        "position_row_count": 12,
        "capacity_blocked_count": 0,
        "gross_only": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _artifact_paths() -> dict[str, str]:
    return {
        "strategy_spec": "strategy_spec.json",
        "params": "params.json",
        "data_manifest": "data_manifest.json",
        "validation_manifest": "validation_manifest.json",
        "cost_manifest": "cost_manifest.json",
        "cost_stress": "cost_stress.parquet",
        "metrics": "metrics.json",
        "equity_curve": "equity_curve.parquet",
        "daily_returns": "daily_returns.parquet",
        "trades": "trades.parquet",
        "positions": "positions.parquet",
        "per_instrument_metrics": "per_instrument_metrics.parquet",
        "fold_metrics": "fold_metrics.parquet",
        "log": "logs/log.txt",
    }


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
