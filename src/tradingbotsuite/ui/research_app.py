from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.research.experiment_runner import run_research_experiment


RESEARCH_UI_VERSION = "research-ui-stage9-v1"
RESEARCH_UI_SCAN_SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "aggregate_backtests",
    "backtests",
    "cache",
    "cost_stress_backtests",
    "feature_cache",
    "feature_frames",
    "snapshots",
    "split_backtests",
    "trial_artifacts",
    "trials",
}
RESEARCH_UI_SCAN_MAX_MATCHES = 500


@dataclass(slots=True)
class ResearchJob:
    job_id: str
    job_type: str
    status: str
    spec_path: str | None
    created_at_ms: int
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ResearchUiService:
    def __init__(
        self,
        *,
        research_root: Path,
        app_config: AppConfig | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.research_root = Path(research_root).expanduser().resolve()
        self.research_root.mkdir(parents=True, exist_ok=True)
        self.app_config = app_config or AppConfig(research=ResearchConfig(output_dir=self.research_root))
        self.repo_root = Path(repo_root).expanduser().resolve() if repo_root is not None else Path(__file__).resolve().parents[3]
        self._jobs: list[ResearchJob] = []

    def dashboard_context(self) -> dict[str, Any]:
        manifests = self.list_manifests()
        return {
            "ui_version": RESEARCH_UI_VERSION,
            "research_root": str(self.research_root),
            "manifest_count": len(manifests),
            "queued_job_count": len(self._jobs),
            "metrics": self.experiment_metrics(),
        }

    def list_manifests(self) -> list[dict[str, Any]]:
        items = []
        for path in _iter_research_paths(self.research_root, "*manifest*.json"):
            payload = _read_json_safely(path)
            items.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "manifest_type": _manifest_type(payload, path),
                    "research_only": bool(payload.get("research_only", False)),
                    "observe_only": bool(payload.get("observe_only", False)),
                    "promotion_ready": bool(payload.get("promotion_ready", False)),
                }
            )
        return items

    def experiment_metrics(self) -> list[dict[str, Any]]:
        rows = []
        for path in _iter_research_paths(self.research_root, "experiment_manifest.json"):
            payload = _read_json_safely(path)
            outputs = payload.get("required_outputs") or {}
            decision = payload.get("orchestrator_decision") or {}
            rows.append(
                {
                    "experiment_name": payload.get("experiment_name") or path.parent.name,
                    "status": decision.get("status") or "unknown",
                    "failure_count": len(decision.get("failure_reasons") or []),
                    "manifest_path": str(path),
                    "summary_path": outputs.get("experiment_summary"),
                    "split_metrics_path": outputs.get("metrics_by_split"),
                    "regime_metrics_path": outputs.get("metrics_by_regime"),
                    "side_metrics_path": outputs.get("metrics_by_side"),
                }
            )
        return rows

    def data_quality_reports(self) -> list[dict[str, Any]]:
        return _typed_artifacts(self.research_root, "data_quality_report.json")

    def dataset_manifests(self) -> list[dict[str, Any]]:
        return _typed_artifacts(self.research_root, "dataset_manifest.json")

    def feature_manifests(self) -> list[dict[str, Any]]:
        return _typed_artifacts(self.research_root, "feature*.json")

    def backtest_manifests(self) -> list[dict[str, Any]]:
        return _typed_artifacts(self.research_root, "backtest_manifest.json")

    def knn_neighbor_diagnostics(self) -> list[dict[str, Any]]:
        return [
            {"path": str(path), "manifest_path": _nearest_manifest(path)}
            for path in _iter_research_paths(self.research_root, "neighbor_diagnostics.csv")
        ]

    def boundary_review_manifests(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.list_manifests()
            if not item["promotion_ready"] and item["research_only"]
        ]

    def queue_research_job(self, *, job_type: str, spec_path: Path | None = None, execute: bool = False) -> ResearchJob:
        if job_type not in {"run-research-experiment"}:
            raise ValueError(f"unsupported_research_job:{job_type}")
        resolved_spec_path = self._validate_research_experiment_spec(spec_path) if spec_path is not None else None
        if execute and self.app_config.runtime_mode == RuntimeMode.LIVE:
            raise ValueError("research_ui_rejects_live_runtime_execution")
        job = ResearchJob(
            job_id=f"research-job-{len(self._jobs) + 1}",
            job_type=job_type,
            status="queued",
            spec_path=str(resolved_spec_path) if resolved_spec_path is not None else None,
            created_at_ms=int(time.time() * 1000),
        )
        self._jobs.append(job)
        if execute:
            self._execute_job(job)
        return job

    def list_jobs(self) -> list[dict[str, Any]]:
        return [asdict(job) for job in self._jobs]

    def _execute_job(self, job: ResearchJob) -> None:
        if job.spec_path is None:
            job.status = "failed"
            job.error = "spec_path is required for execution"
            return
        if self.app_config.runtime_mode == RuntimeMode.LIVE:
            job.status = "failed"
            job.error = "research_ui_rejects_live_runtime_execution"
            return
        job.status = "running"
        try:
            result = run_research_experiment(spec_path=Path(job.spec_path), app_config=self.app_config)
            job.result = {
                "experiment_run_manifest_path": str(result.manifest_path),
                "experiment_manifest_path": str(result.experiment_manifest_path) if result.experiment_manifest_path else None,
                "conclusion_path": str(result.conclusion_path),
            }
            job.status = "succeeded"
        except Exception as exc:  # pragma: no cover - explicit operator-visible job failure path
            job.status = "failed"
            job.error = str(exc)

    def _validate_research_experiment_spec(self, spec_path: Path) -> Path:
        resolved = self._resolve_path(spec_path, base_path=self.repo_root)
        allowed_spec_roots = [
            (self.repo_root / "configs" / "experiments").resolve(),
            self.research_root,
        ]
        if not resolved.is_file():
            raise ValueError("experiment spec_path does not exist")
        if not any(_is_relative_to(resolved, root) for root in allowed_spec_roots):
            raise ValueError("experiment spec_path must be inside configs/experiments or the research output directory")
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"experiment spec is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("experiment spec must be a JSON object")

        output_dir = (
            self._resolve_path(Path(str(payload["output_dir"])), base_path=resolved.parent)
            if payload.get("output_dir")
            else (self.research_root / "experiments").resolve()
        )
        if not _is_relative_to(output_dir, self.research_root):
            raise ValueError("experiment output_dir must be inside the configured research output directory")

        pipeline_spec = payload.get("pipeline_spec")
        if not pipeline_spec:
            raise ValueError("experiment pipeline_spec is required")
        pipeline_path = self._resolve_path(Path(str(pipeline_spec)), base_path=resolved.parent)
        allowed_pipeline_roots = [
            (self.repo_root / "configs" / "data").resolve(),
            self.research_root,
        ]
        if not pipeline_path.is_file():
            raise ValueError("experiment pipeline_spec does not exist")
        if not any(_is_relative_to(pipeline_path, root) for root in allowed_pipeline_roots):
            raise ValueError("experiment pipeline_spec must be inside configs/data or the research output directory")

        supplied_experiment_spec = payload.get("experiment_spec")
        if supplied_experiment_spec:
            supplied_path = self._resolve_path(Path(str(supplied_experiment_spec)), base_path=resolved.parent)
            if not supplied_path.is_file():
                raise ValueError("experiment experiment_spec does not exist")
            if not any(_is_relative_to(supplied_path, root) for root in allowed_spec_roots):
                raise ValueError("experiment experiment_spec must be inside configs/experiments or the research output directory")
        return resolved

    def _resolve_path(self, raw_path: Path, *, base_path: Path) -> Path:
        path = Path(raw_path).expanduser()
        return path.resolve() if path.is_absolute() else (base_path / path).resolve()


def create_research_app(config: AppConfig | None = None, service: ResearchUiService | None = None) -> FastAPI:
    config = config or (service.app_config if service is not None else AppConfig.from_env())
    service = service or ResearchUiService(research_root=config.research.output_dir, app_config=config)
    service.app_config = config
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates" / "research"))
    app = FastAPI(title="Trading Bot Suite Research UI")
    app.state.research_ui_service = service

    def context(request: Request, page: str, title: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "request": request,
            "page": page,
            "title": title,
            "dashboard": service.dashboard_context(),
        }
        if extra:
            payload.update(extra)
        return payload

    def require_write_api(request: Request) -> None:
        secret = config.operator_ui.secret
        if not secret:
            raise HTTPException(status_code=403, detail="research_ui_write_api_disabled")
        origin = request.headers.get("origin")
        if origin is not None and origin.rstrip("/") != str(request.base_url).rstrip("/"):
            raise HTTPException(status_code=403, detail="cross-origin request blocked")
        token = request.headers.get("X-Research-UI-Token")
        if token is None:
            raise HTTPException(status_code=403, detail="missing research ui token")
        if not secrets.compare_digest(token, str(secret)):
            raise HTTPException(status_code=403, detail="invalid research ui token")

    @app.get("/research", response_class=HTMLResponse)
    async def research_home(request: Request):
        return templates.TemplateResponse(request, "index.html", context(request, "dashboard", "Research Dashboard"))

    @app.get("/research/data-quality", response_class=HTMLResponse)
    async def data_quality(request: Request):
        return templates.TemplateResponse(request, "artifacts.html", context(request, "data_quality", "Data Quality", {"items": service.data_quality_reports()}))

    @app.get("/research/datasets", response_class=HTMLResponse)
    async def datasets(request: Request):
        return templates.TemplateResponse(request, "artifacts.html", context(request, "datasets", "Dataset Manifests", {"items": service.dataset_manifests()}))

    @app.get("/research/features", response_class=HTMLResponse)
    async def features(request: Request):
        return templates.TemplateResponse(request, "artifacts.html", context(request, "features", "Feature Availability", {"items": service.feature_manifests()}))

    @app.get("/research/backtests", response_class=HTMLResponse)
    async def backtests(request: Request):
        return templates.TemplateResponse(request, "artifacts.html", context(request, "backtests", "Backtest Runs", {"items": service.backtest_manifests()}))

    @app.get("/research/experiments", response_class=HTMLResponse)
    async def experiments(request: Request):
        return templates.TemplateResponse(request, "experiments.html", context(request, "experiments", "Experiment Comparison", {"metrics": service.experiment_metrics()}))

    @app.get("/research/equity", response_class=HTMLResponse)
    async def equity(request: Request):
        return templates.TemplateResponse(request, "artifacts.html", context(request, "equity", "Equity and Drawdown", {"items": _typed_artifacts(service.research_root, "equity_curve.parquet")}))

    @app.get("/research/trades", response_class=HTMLResponse)
    async def trades(request: Request):
        return templates.TemplateResponse(request, "artifacts.html", context(request, "trades", "Trade Distribution", {"items": _typed_artifacts(service.research_root, "trades.parquet")}))

    @app.get("/research/regimes", response_class=HTMLResponse)
    async def regimes(request: Request):
        return templates.TemplateResponse(request, "artifacts.html", context(request, "regimes", "Regime and Side Breakdowns", {"items": _typed_artifacts(service.research_root, "metrics_by_regime.parquet")}))

    @app.get("/research/knn-neighbors", response_class=HTMLResponse)
    async def knn_neighbors(request: Request):
        return templates.TemplateResponse(request, "artifacts.html", context(request, "knn_neighbors", "KNN Neighbor Diagnostics", {"items": service.knn_neighbor_diagnostics()}))

    @app.get("/research/boundary-review", response_class=HTMLResponse)
    async def boundary_review(request: Request):
        return templates.TemplateResponse(
            request,
            "artifacts.html",
            context(
                request,
                "boundary_review",
                "Research Boundary Review",
                {"items": service.boundary_review_manifests()},
            ),
        )

    @app.get("/research/promotion-candidates", response_class=HTMLResponse)
    async def legacy_promotion_review():
        return RedirectResponse("/research/boundary-review", status_code=308)

    @app.get("/research/jobs", response_class=HTMLResponse)
    async def jobs(request: Request):
        return templates.TemplateResponse(request, "jobs.html", context(request, "jobs", "Research Jobs", {"jobs": service.list_jobs()}))

    @app.get("/research/api/manifests")
    async def api_manifests():
        return {"items": service.list_manifests()}

    @app.get("/research/api/experiments")
    async def api_experiments():
        return {"items": service.experiment_metrics()}

    @app.get("/research/api/jobs")
    async def api_jobs():
        return {"items": service.list_jobs()}

    @app.post("/research/api/jobs/run-research-experiment")
    async def api_run_research_experiment(request: Request):
        require_write_api(request)
        payload = await request.json()
        spec_path = payload.get("spec_path")
        if not spec_path:
            raise HTTPException(status_code=400, detail="spec_path is required")
        execute = bool(payload.get("execute", False))
        if execute and config.runtime_mode == RuntimeMode.LIVE:
            raise HTTPException(status_code=400, detail="research_ui_rejects_live_runtime_execution")
        try:
            job = service.queue_research_job(job_type="run-research-experiment", spec_path=Path(str(spec_path)), execute=execute)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return asdict(job)

    return app


def _typed_artifacts(root: Path, pattern: str) -> list[dict[str, Any]]:
    return [
        {"path": str(path), "manifest_path": _nearest_manifest(path)}
        for path in _iter_research_paths(Path(root), pattern)
    ]


def _nearest_manifest(path: Path) -> str | None:
    for parent in [path.parent, *path.parents]:
        candidates = sorted(parent.glob("*manifest*.json"))
        if candidates:
            return str(candidates[0])
    return None


def _read_json_safely(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _manifest_type(payload: dict[str, Any], path: Path) -> str:
    for key in ("experiment_manifest_version", "experiment_run_manifest_version", "backtest_manifest_version", "dataset_manifest_version"):
        if payload.get(key):
            return key.removesuffix("_version")
    return path.stem


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _iter_research_paths(root: Path, pattern: str) -> list[Path]:
    if not root.exists():
        return []
    matches: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in RESEARCH_UI_SCAN_SKIP_DIRS and not name.startswith(".")
        ]
        for filename in filenames:
            if not fnmatch(filename, pattern):
                continue
            matches.append(Path(dirpath) / filename)
            if len(matches) >= RESEARCH_UI_SCAN_MAX_MATCHES:
                return sorted(matches)
    return sorted(matches)
