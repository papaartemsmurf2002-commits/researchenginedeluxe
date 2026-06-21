from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tradingbotsuite.v2.autonomy import StrategyQueueScanConfig, scan_strategy_queue
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads


def test_strategy_queue_scan_accepts_valid_and_reports_rejections(tmp_path) -> None:
    strategy_root = tmp_path / "queue_inputs"
    output_root = tmp_path / "queue_outputs"
    strategy_root.mkdir()
    valid_payload = example_strategy_payloads()["hl_mean_reversion_v1"]
    invalid_payload = copy.deepcopy(valid_payload)
    del invalid_payload["execution"]["fee_model"]
    (strategy_root / "valid.json").write_text(
        json.dumps(valid_payload, sort_keys=True),
        encoding="utf-8",
    )
    (strategy_root / "invalid.json").write_text(
        json.dumps(invalid_payload, sort_keys=True),
        encoding="utf-8",
    )
    (strategy_root / "custom.py").write_text(
        "raise RuntimeError('must not execute')\n",
        encoding="utf-8",
    )
    (strategy_root / "credentials.json").write_text(
        json.dumps(valid_payload, sort_keys=True),
        encoding="utf-8",
    )

    result = scan_strategy_queue(
        StrategyQueueScanConfig(
            strategy_root=str(strategy_root),
            output_root=str(output_root),
            run_id="queue-pass",
        )
    )
    manifest = _read_json(Path(result.manifest_path))

    assert result.item_count == 4
    assert result.accepted_count == 1
    assert result.rejected_count == 3
    assert result.accepted_research_ready is False
    assert result.promotion_ready is False
    assert manifest["evidence_mode"] == "input_hygiene_only"
    assert manifest["accepted_research_ready"] is False
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["candidate_evidence"] is False
    assert manifest["candidate_pack_eligible"] is False
    assert manifest["live_signal"] is False
    assert manifest["paper_signal"] is False
    assert manifest["sizing_instruction"] is False
    assert manifest["order_placement_instruction"] is False
    assert manifest["runtime_mode_change"] is False
    assert '"live_signal": true' not in json.dumps(manifest, sort_keys=True)

    items = {item["source_relpath"]: item for item in manifest["items"]}
    accepted = items["valid.json"]
    invalid = items["invalid.json"]
    unsupported = items["custom.py"]
    credential_like = items["credentials.json"]

    assert accepted["status"] == "accepted"
    assert accepted["strategy_id"] == "hl_mean_reversion_v1"
    assert accepted["spec_hash"]
    assert accepted["source_sha256"]
    normalized_path = Path(accepted["normalized_spec_path"])
    assert normalized_path.exists()
    normalized = _read_json(normalized_path)
    assert normalized["strategy_id"] == "hl_mean_reversion_v1"
    assert normalized["candidate_pack_eligible"] is False
    assert invalid["status"] == "rejected"
    assert any(
        blocker.startswith("strategy_spec_validation_failed:execution.fee_model")
        for blocker in invalid["blocker_reasons"]
    )
    assert unsupported["status"] == "rejected"
    assert unsupported["source_sha256"] is None
    assert unsupported["blocker_reasons"] == ["unsupported_strategy_file_suffix:.py"]
    assert credential_like["status"] == "rejected"
    assert credential_like["source_sha256"] is None
    assert credential_like["blocker_reasons"] == ["secret_like_strategy_file_path"]
    assert "unsupported_strategy_file_suffix:.py" in result.blocker_reasons
    assert "secret_like_strategy_file_path" in result.blocker_reasons


def test_strategy_queue_scan_is_deterministic_for_same_inputs(tmp_path) -> None:
    strategy_root = tmp_path / "queue_inputs"
    output_root = tmp_path / "queue_outputs"
    strategy_root.mkdir()
    payload = example_strategy_payloads()["hl_funding_carry_v1"]
    (strategy_root / "funding.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )

    first = scan_strategy_queue(
        StrategyQueueScanConfig(
            strategy_root=str(strategy_root),
            output_root=str(output_root),
            run_id="queue-repeat",
        )
    )
    second = scan_strategy_queue(
        StrategyQueueScanConfig(
            strategy_root=str(strategy_root),
            output_root=str(output_root),
            run_id="queue-repeat",
        )
    )

    assert first.manifest_id == second.manifest_id
    assert _read_json(Path(first.manifest_path)) == _read_json(Path(second.manifest_path))


def test_strategy_queue_rejects_nested_output_root(tmp_path) -> None:
    strategy_root = tmp_path / "queue_inputs"
    strategy_root.mkdir()

    with pytest.raises(ValueError, match="output_root must not be inside strategy_root"):
        scan_strategy_queue(
            StrategyQueueScanConfig(
                strategy_root=str(strategy_root),
                output_root=str(strategy_root / "out"),
                run_id="queue-bad-output",
            )
        )


def test_strategy_queue_cli_writes_manifest(tmp_path, capsys) -> None:
    strategy_root = tmp_path / "queue_inputs"
    output_root = tmp_path / "queue_outputs"
    strategy_root.mkdir()
    payload = example_strategy_payloads()["hl_liquidity_filtered_momentum_v1"]
    (strategy_root / "liquidity.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "autopilot",
            "strategy-queue-scan",
            "--strategy-root",
            str(strategy_root),
            "--output-root",
            str(output_root),
            "--run-id",
            "queue-cli",
        ]
    )
    output = capsys.readouterr().out
    values = dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)

    assert exit_code == 0
    assert values["run_id"] == "queue-cli"
    assert values["item_count"] == "1"
    assert values["accepted_count"] == "1"
    assert values["rejected_count"] == "0"
    assert values["blocker_count"] == "0"
    assert values["evidence_mode"] == "input_hygiene_only"
    assert values["accepted_research_ready"] == "false"
    assert values["promotion_ready"] == "false"
    assert Path(values["strategy_queue_manifest"]).exists()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
