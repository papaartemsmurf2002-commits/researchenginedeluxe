from __future__ import annotations

import inspect
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tradingbotsuite.config import AppConfig, OperatorUIConfig, ResearchConfig
from tradingbotsuite.core.models import RuntimeMode
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


def _write_research_run_spec(root: Path, *, output_dir: Path | None = None) -> Path:
    spec_dir = root / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    pipeline_spec = spec_dir / "pipeline.json"
    pipeline_spec.write_text(json.dumps({"version": "research-ui-pipeline"}), encoding="utf-8")
    run_spec = spec_dir / "experiment.json"
    payload: dict[str, str] = {"pipeline_spec": str(pipeline_spec)}
    if output_dir is not None:
        payload["output_dir"] = str(output_dir)
    run_spec.write_text(json.dumps(payload), encoding="utf-8")
    return run_spec


def test_research_ui_pages_are_passive_and_manifest_linked(tmp_path: Path) -> None:
    manifest_path = _write_experiment_manifest(tmp_path / "research")
    app = create_research_app(service=ResearchUiService(research_root=tmp_path / "research"))

    with TestClient(app) as client:
        home = client.get("/research")
        experiments = client.get("/research/experiments")
        knn = client.get("/research/knn-neighbors")
        boundary = client.get("/research/boundary-review")
        legacy_boundary = client.get("/research/promotion-candidates", follow_redirects=False)
        api = client.get("/research/api/experiments")

    assert home.status_code == 200
    assert experiments.status_code == 200
    assert knn.status_code == 200
    assert "/research/boundary-review" in home.text
    assert "/research/promotion-candidates" not in home.text
    assert str(manifest_path) in experiments.text
    assert "Research Boundary Review" in boundary.text
    assert "Promotion Candidate Review" not in boundary.text
    assert legacy_boundary.status_code == 308
    assert legacy_boundary.headers["location"] == "/research/boundary-review"
    assert api.json()["items"][0]["manifest_path"] == str(manifest_path)
    assert "neighbor_diagnostics.csv" in knn.text


def test_research_ui_skips_heavy_trial_dirs_when_indexing(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    good_manifest = _write_experiment_manifest(research_root)
    noisy_dir = research_root / "trials" / "ignored"
    noisy_dir.mkdir(parents=True)
    noisy_manifest = noisy_dir / "experiment_manifest.json"
    noisy_manifest.write_text(
        json.dumps(
            {
                "experiment_manifest_version": "v3-generic-research-experiment-manifest-1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "experiment_name": "ignored trial",
            }
        ),
        encoding="utf-8",
    )

    manifests = ResearchUiService(research_root=research_root).list_manifests()
    manifest_paths = {item["path"] for item in manifests}

    assert str(good_manifest) in manifest_paths
    assert str(noisy_manifest) not in manifest_paths


def test_research_ui_uses_service_config_for_write_token(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    spec_path = _write_research_run_spec(research_root)
    config = AppConfig(
        research=ResearchConfig(output_dir=research_root),
        operator_ui=OperatorUIConfig(secret="service-secret"),
    )
    service = ResearchUiService(research_root=research_root, app_config=config)
    app = create_research_app(service=service)

    with TestClient(app) as client:
        response = client.post(
            "/research/api/jobs/run-research-experiment",
            json={"spec_path": str(spec_path)},
            headers={"X-Research-UI-Token": "service-secret"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert service.list_jobs()[0]["spec_path"] == str(spec_path.resolve())


def test_research_ui_queues_explicit_research_jobs(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    spec_path = _write_research_run_spec(research_root)
    config = AppConfig(
        research=ResearchConfig(output_dir=research_root),
        operator_ui=OperatorUIConfig(secret="research-secret"),
    )
    app = create_research_app(config=config)

    with TestClient(app) as client:
        response = client.post(
            "/research/api/jobs/run-research-experiment",
            json={"spec_path": str(spec_path)},
            headers={"X-Research-UI-Token": "research-secret"},
        )
        jobs = client.get("/research/api/jobs")

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert jobs.json()["items"][0]["spec_path"] == str(spec_path.resolve())


def test_research_ui_write_api_requires_token(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    spec_path = _write_research_run_spec(research_root)
    config = AppConfig(
        research=ResearchConfig(output_dir=research_root),
        operator_ui=OperatorUIConfig(secret="research-secret"),
    )
    app = create_research_app(config=config)

    with TestClient(app) as client:
        missing = client.post("/research/api/jobs/run-research-experiment", json={"spec_path": str(spec_path)})
        invalid = client.post(
            "/research/api/jobs/run-research-experiment",
            json={"spec_path": str(spec_path)},
            headers={"X-Research-UI-Token": "wrong"},
        )
        disabled = client.post(
            "/research/api/jobs/run-research-experiment",
            json={"spec_path": str(spec_path)},
            headers={"X-Research-UI-Token": "research-secret", "Origin": "http://evil.test"},
        )

    assert missing.status_code == 403
    assert invalid.status_code == 403
    assert disabled.status_code == 403


def test_research_ui_rejects_unallowlisted_spec_path(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    outside_root = tmp_path / "outside"
    spec_path = _write_research_run_spec(outside_root)
    config = AppConfig(
        research=ResearchConfig(output_dir=research_root),
        operator_ui=OperatorUIConfig(secret="research-secret"),
    )
    app = create_research_app(config=config)

    with TestClient(app) as client:
        response = client.post(
            "/research/api/jobs/run-research-experiment",
            json={"spec_path": str(spec_path)},
            headers={"X-Research-UI-Token": "research-secret"},
        )

    assert response.status_code == 400
    assert "spec_path must be inside" in response.json()["detail"]


def test_research_ui_rejects_external_output_dir(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    spec_path = _write_research_run_spec(research_root, output_dir=tmp_path / "outside-output")
    config = AppConfig(
        research=ResearchConfig(output_dir=research_root),
        operator_ui=OperatorUIConfig(secret="research-secret"),
    )
    app = create_research_app(config=config)

    with TestClient(app) as client:
        response = client.post(
            "/research/api/jobs/run-research-experiment",
            json={"spec_path": str(spec_path)},
            headers={"X-Research-UI-Token": "research-secret"},
        )

    assert response.status_code == 400
    assert "output_dir must be inside" in response.json()["detail"]


def test_research_ui_rejects_live_mode_execution(tmp_path: Path) -> None:
    research_root = tmp_path / "research"
    spec_path = _write_research_run_spec(research_root)
    config = AppConfig(
        runtime_mode=RuntimeMode.LIVE,
        research=ResearchConfig(output_dir=research_root),
        operator_ui=OperatorUIConfig(secret="research-secret"),
    )
    app = create_research_app(config=config)

    with TestClient(app) as client:
        response = client.post(
            "/research/api/jobs/run-research-experiment",
            json={"spec_path": str(spec_path), "execute": True},
            headers={"X-Research-UI-Token": "research-secret"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "research_ui_rejects_live_runtime_execution"


def test_research_ui_does_not_import_live_execution_adapters() -> None:
    source = inspect.getsource(research_app)

    assert "tradingbotsuite.adapters.execution" not in source
    assert "TradingEngine" not in source
