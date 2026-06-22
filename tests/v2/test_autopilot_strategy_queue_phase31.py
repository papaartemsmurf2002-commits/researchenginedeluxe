from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.autonomy import StrategyQueueScanConfig, scan_strategy_queue
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job


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


def test_strategy_queue_worker_outputs_single_normalized_spec_refs(tmp_path) -> None:
    strategy_root = tmp_path / "queue_inputs"
    output_root = tmp_path / "queue_outputs"
    strategy_root.mkdir()
    payload = example_strategy_payloads()["hl_mean_reversion_v1"]
    (strategy_root / "mean-reversion.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.STRATEGY_QUEUE_SCAN,
        job_id="JOB-strategy-queue-single",
        input_spec={
            "strategy_root": str(strategy_root),
            "output_root": str(output_root),
            "run_id": "queue-worker-single",
            "require_single_accepted": True,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.STRATEGY_QUEUE_SCAN,
        worker_id="worker-strategy-queue",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    values = _ref_values(loaded.output_refs)
    manifest = _read_json(Path(values["strategy_queue_manifest_path"]))
    accepted = manifest["items"][0]
    accepted_path = Path(values["accepted_spec_path"])

    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert values["job_kind"] == "strategy_queue_scan"
    assert values["accepted_research_ready"] == "false"
    assert values["require_single_accepted"] == "true"
    assert values["accepted_count"] == "1"
    assert values["rejected_count"] == "0"
    assert values["blocker_reasons"] == ""
    assert values["strategy_queue_manifest_id"] == manifest["manifest_id"]
    assert values["strategy_queue_manifest_sha256"] == file_sha256(Path(values["strategy_queue_manifest_path"]))
    assert values["accepted_spec_sha256"] == file_sha256(accepted_path)
    assert values["strategy_spec_hash"] == accepted["spec_hash"]
    assert values["strategy_id"] == "hl_mean_reversion_v1"
    assert accepted_path.exists()
    assert any(ref.startswith("strategy_queue_manifest_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("strategy_queue_manifest_sha256=") for ref in loaded.archive_manifest_refs)


def test_strategy_queue_worker_reports_multiple_accepted_specs_without_ambiguous_ref(tmp_path) -> None:
    strategy_root = tmp_path / "queue_inputs"
    output_root = tmp_path / "queue_outputs"
    strategy_root.mkdir()
    examples = example_strategy_payloads()
    (strategy_root / "mean-reversion.json").write_text(
        json.dumps(examples["hl_mean_reversion_v1"], sort_keys=True),
        encoding="utf-8",
    )
    (strategy_root / "funding-carry.json").write_text(
        json.dumps(examples["hl_funding_carry_v1"], sort_keys=True),
        encoding="utf-8",
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.STRATEGY_QUEUE_SCAN,
        job_id="JOB-strategy-queue-multiple",
        input_spec={
            "strategy_root": str(strategy_root),
            "output_root": str(output_root),
            "run_id": "queue-worker-multiple",
            "require_single_accepted": True,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.STRATEGY_QUEUE_SCAN,
        worker_id="worker-strategy-queue-multiple",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    values = _ref_values(loaded.output_refs)

    assert values["accepted_count"] == "2"
    assert values["rejected_count"] == "0"
    assert "multiple_accepted_strategy_specs" in values["blocker_reasons"]
    assert "accepted_spec_path" not in values
    assert "accepted_spec_sha256" not in values
    assert "strategy_spec_hash" not in values


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


def _ref_values(refs: tuple[str, ...]) -> dict[str, str]:
    return dict(ref.split("=", 1) for ref in refs if "=" in ref)
