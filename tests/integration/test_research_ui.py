from __future__ import annotations

import inspect
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tradingbotsuite.ui import research_app
from tradingbotsuite.ui.research_app import ResearchUiService, create_research_app


def _write_experiment_manifest(root: Path) -> Path:
    experiment_dir = root / "experiments" / "stage9"
    experiment_dir.mkdir(parents=True)
    manifest_path = experiment_dir / "experiment_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "experiment_manifest_version": "v3-generic-research-experiment-manifest-1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "experiment_name": "stage9 fixture",
                "orchestrator_decision": {"status": "rejected", "failure_reasons": ["research_only_not_promotable"]},
                "required_outputs": {
                    "experiment_summary": str(experiment_dir / "experiment_summary.csv"),
                    "metrics_by_split": str(experiment_dir / "metrics_by_split.parquet"),
                    "metrics_by_regime": str(experiment_dir / "metrics_by_regime.parquet"),
                    "metrics_by_side": str(experiment_dir / "metrics_by_side.parquet"),
                },
            }
        ),
        encoding="utf-8",
    )
    (experiment_dir / "neighbor_diagnostics.csv").write_text("neighbor_distance_quality\n0.5\n", encoding="utf-8")
    return manifest_path


def test_research_ui_pages_are_passive_and_manifest_linked(tmp_path: Path) -> None:
    manifest_path = _write_experiment_manifest(tmp_path / "research")
    app = create_research_app(service=ResearchUiService(research_root=tmp_path / "research"))

    with TestClient(app) as client:
        home = client.get("/research")
        experiments = client.get("/research/experiments")
        knn = client.get("/research/knn-neighbors")
        api = client.get("/research/api/experiments")

    assert home.status_code == 200
    assert experiments.status_code == 200
    assert knn.status_code == 200
    assert str(manifest_path) in experiments.text
    assert api.json()["items"][0]["manifest_path"] == str(manifest_path)
    assert "neighbor_diagnostics.csv" in knn.text


def test_research_ui_queues_explicit_research_jobs(tmp_path: Path) -> None:
    spec_path = tmp_path / "research" / "specs" / "experiment.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text("{}", encoding="utf-8")
    app = create_research_app(service=ResearchUiService(research_root=tmp_path / "research"))

    with TestClient(app) as client:
        response = client.post("/research/api/jobs/run-research-experiment", json={"spec_path": str(spec_path)})
        jobs = client.get("/research/api/jobs")

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert jobs.json()["items"][0]["spec_path"] == str(spec_path)


def test_research_ui_does_not_import_live_execution_adapters() -> None:
    source = inspect.getsource(research_app)

    assert "tradingbotsuite.adapters.execution" not in source
    assert "TradingEngine" not in source
