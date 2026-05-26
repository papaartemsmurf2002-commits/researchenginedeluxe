from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import RuntimeMode, SignalDirection
from tradingbotsuite.data.historical_data_catalog import (
    DEFAULT_HISTORICAL_CATALOG_START_MONTH,
    default_historical_catalog_end_month,
)
from tradingbotsuite.research.data_pipeline import DATA_PIPELINE_DEFAULT_STAGE, DATA_PIPELINE_STAGES
from tradingbotsuite.operator_console import OperatorConsoleService
from tradingbotsuite.research_cycle.hardware_benchmark import (
    DEFAULT_CPU_SECONDS,
    DEFAULT_GPU_SECONDS,
    DEFAULT_MATRIX_SIZE,
    MAX_CPU_SECONDS,
    MAX_GPU_SECONDS,
    MAX_MATRIX_SIZE,
    MIN_MATRIX_SIZE,
    MIN_PROBE_SECONDS,
    WINDOWS_PROCESS_POOL_MAX_WORKERS,
)
from tradingbotsuite.research_discovery.spec import DiscoveryRunSpec


def register_operator_routes(app: FastAPI, config: AppConfig, service: OperatorConsoleService) -> None:
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    repo_root = Path(__file__).resolve().parents[3]

    def active_config() -> AppConfig:
        return service.config

    def serializer() -> URLSafeSerializer:
        return URLSafeSerializer(active_config().operator_ui.secret or "disabled", salt="tbs-operator-ui")

    def require_same_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        if origin is None:
            return
        expected = str(request.base_url).rstrip("/")
        if origin.rstrip("/") != expected:
            raise HTTPException(status_code=403, detail="cross-origin request blocked")

    def load_session(request: Request) -> dict[str, Any] | None:
        raw = request.cookies.get(active_config().operator_ui.session_cookie_name)
        if not raw:
            return None
        try:
            return serializer().loads(raw)
        except BadSignature:
            return None

    def require_session_json(request: Request) -> dict[str, Any]:
        session = load_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="authentication required")
        return session

    def require_csrf(request: Request, session: dict[str, Any]) -> None:
        token = request.headers.get("X-CSRF-Token")
        if token is None:
            raise HTTPException(status_code=403, detail="missing csrf token")
        if not secrets.compare_digest(token, str(session.get("csrf_token", ""))):
            raise HTTPException(status_code=403, detail="invalid csrf token")

    def resolve_operator_path(raw_path: object) -> Path:
        path = Path(str(raw_path)).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (repo_root / path).resolve()

    def is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def active_catalog_spec_path(symbol: str, spec_key: str) -> str | None:
        readiness = service.r104_readiness_diagnostics()
        for item in readiness.get("items") or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("symbol") or "").upper() != symbol.upper():
                continue
            value = item.get(spec_key)
            if value is not None and str(value).strip():
                return str(value)
        return None

    def validate_research_file_path(payload: dict[str, Any], field_name: str) -> Path:
        raw_path = payload.get(field_name)
        if raw_path is None or str(raw_path).strip() == "":
            raise HTTPException(status_code=400, detail=f"{field_name} is required")
        path = resolve_operator_path(raw_path)
        research_root = resolve_operator_path(active_config().research.output_dir)
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"{field_name} does not exist")
        if not is_relative_to(path, research_root):
            raise HTTPException(status_code=400, detail=f"{field_name} must be inside the research output directory")
        return path

    def validate_optional_research_file_path(payload: dict[str, Any], field_name: str) -> Path | None:
        raw_path = payload.get(field_name)
        if raw_path is None or str(raw_path).strip() == "":
            return None
        return validate_research_file_path(payload, field_name)

    def validate_provider_pipeline_request(payload: dict[str, Any]) -> Path:
        spec_path = resolve_operator_path(payload.get("spec_path") or "configs/data/v2_btc_hmm_knn_provider_pipeline.json")
        research_root = resolve_operator_path(active_config().research.output_dir)
        allowed_spec_roots = [
            (repo_root / "configs" / "data").resolve(),
            research_root,
        ]
        if not spec_path.is_file():
            raise HTTPException(status_code=400, detail="pipeline spec_path does not exist")
        if not any(is_relative_to(spec_path, root) for root in allowed_spec_roots):
            raise HTTPException(status_code=400, detail="pipeline spec_path must be inside configs/data or the research output directory")
        try:
            spec_payload = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"pipeline spec is not valid JSON: {exc}") from exc
        if not isinstance(spec_payload, dict):
            raise HTTPException(status_code=400, detail="pipeline spec must be a JSON object")
        raw_output_dir = spec_payload.get("output_dir") or Path("data/research") / str(spec_payload.get("version") or "")
        output_dir = resolve_operator_path(raw_output_dir)
        if not is_relative_to(output_dir, research_root):
            raise HTTPException(status_code=400, detail="pipeline output_dir must be inside the configured research output directory")
        return spec_path

    def validate_research_experiment_request(payload: dict[str, Any]) -> Path:
        spec_path = resolve_operator_path(payload.get("spec_path") or "configs/experiments/v2_btc_phase1_research_experiment.json")
        research_root = resolve_operator_path(active_config().research.output_dir)
        allowed_spec_roots = [
            (repo_root / "configs" / "experiments").resolve(),
            research_root,
        ]
        if not spec_path.is_file():
            raise HTTPException(status_code=400, detail="experiment spec_path does not exist")
        if not any(is_relative_to(spec_path, root) for root in allowed_spec_roots):
            raise HTTPException(status_code=400, detail="experiment spec_path must be inside configs/experiments or the research output directory")
        try:
            spec_payload = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"experiment spec is not valid JSON: {exc}") from exc
        if not isinstance(spec_payload, dict):
            raise HTTPException(status_code=400, detail="experiment spec must be a JSON object")
        raw_output_dir = spec_payload.get("output_dir") or research_root / "experiments"
        output_dir = resolve_operator_path(raw_output_dir)
        if not is_relative_to(output_dir, research_root):
            raise HTTPException(status_code=400, detail="experiment output_dir must be inside the configured research output directory")
        raw_pipeline_spec = Path(str(spec_payload.get("pipeline_spec") or "")).expanduser()
        pipeline_spec = (
            raw_pipeline_spec.resolve()
            if raw_pipeline_spec.is_absolute()
            else (spec_path.parent / raw_pipeline_spec).resolve()
        )
        allowed_pipeline_roots = [
            (repo_root / "configs" / "data").resolve(),
            research_root,
        ]
        if not pipeline_spec.is_file():
            raise HTTPException(status_code=400, detail="experiment pipeline_spec does not exist")
        if not any(is_relative_to(pipeline_spec, root) for root in allowed_pipeline_roots):
            raise HTTPException(status_code=400, detail="experiment pipeline_spec must be inside configs/data or the research output directory")
        return spec_path

    def validate_historical_cycle_request(payload: dict[str, Any]) -> Path:
        default_spec = active_catalog_spec_path("BTCUSDT", "cycle_spec_path")
        spec_path = resolve_operator_path(
            payload.get("spec_path")
            or default_spec
            or "configs/research/full_cycle_btcusdt_durable_public_archive_r104_deep_v1.json"
        )
        research_root = resolve_operator_path(active_config().research.output_dir)
        allowed_spec_roots = [
            (repo_root / "configs" / "research").resolve(),
            research_root,
        ]
        if not spec_path.is_file():
            raise HTTPException(status_code=400, detail="historical cycle spec_path does not exist")
        if not any(is_relative_to(spec_path, root) for root in allowed_spec_roots):
            raise HTTPException(status_code=400, detail="historical cycle spec_path must be inside configs/research or the research output directory")
        try:
            spec_payload = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"historical cycle spec is not valid JSON: {exc}") from exc
        if not isinstance(spec_payload, dict):
            raise HTTPException(status_code=400, detail="historical cycle spec must be a JSON object")
        if not str(spec_payload.get("cycle_id") or "").strip():
            raise HTTPException(status_code=400, detail="historical cycle spec requires cycle_id")
        return spec_path

    def validate_discovery_run_request(payload: dict[str, Any]) -> Path:
        default_spec = active_catalog_spec_path("BTCUSDT", "discovery_spec_path")
        spec_path = resolve_operator_path(
            payload.get("spec_path")
            or default_spec
            or "configs/discovery/exact_entry_sweep_btcusdt_durable_r104_v1.json"
        )
        research_root = resolve_operator_path(active_config().research.output_dir)
        allowed_spec_roots = [
            (repo_root / "configs" / "discovery").resolve(),
            research_root,
        ]
        if not spec_path.is_file():
            raise HTTPException(status_code=400, detail="discovery spec_path does not exist")
        if not any(is_relative_to(spec_path, root) for root in allowed_spec_roots):
            raise HTTPException(status_code=400, detail="discovery spec_path must be inside configs/discovery or the research output directory")
        try:
            spec_payload = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"discovery spec is not valid JSON: {exc}") from exc
        if not isinstance(spec_payload, dict):
            raise HTTPException(status_code=400, detail="discovery spec must be a JSON object")
        try:
            DiscoveryRunSpec.from_payload(spec_payload, spec_path=spec_path, repo_root=repo_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"discovery spec is invalid: {exc}") from exc
        raw_output_dir = spec_payload.get("output_dir")
        if raw_output_dir:
            output_dir = resolve_operator_path(raw_output_dir)
            if not is_relative_to(output_dir, research_root):
                raise HTTPException(status_code=400, detail="discovery output_dir must be inside the configured research output directory")
        return spec_path

    def validate_stop_after_trials(raw_value: object) -> int | None:
        if raw_value is None or str(raw_value).strip() == "":
            return None
        try:
            value = int(raw_value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="stop_after_trials must be a positive integer") from exc
        if value <= 0:
            raise HTTPException(status_code=400, detail="stop_after_trials must be a positive integer")
        return value

    def exact_required_discovery_spec(spec_path: Path) -> bool:
        return spec_path.name in {
            "exact_entry_sweep_btcusdt_durable_r104_v1.json",
            "exact_entry_sweep_ethusdt_durable_r104_v1.json",
            "exact_entry_sweep_btcusdt_candidate_depth_v1.json",
            "exact_entry_sweep_ethusdt_candidate_depth_v1.json",
        }

    def template_context(request: Request, page: str, *, session: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        session = session or load_session(request) or {}
        execution_target = "paper"
        current_config = active_config()
        if current_config.runtime_mode.value == "live":
            execution_target = "testnet" if "testnet" in current_config.hyperliquid.base_url.lower() else "live"
        context = {
            "request": request,
            "page": page,
            "mode": current_config.runtime_mode.value,
            "csrf_token": session.get("csrf_token"),
            "execution_target": execution_target,
            "hyperliquid_base_url": current_config.hyperliquid.base_url,
            "hyperliquid_live_enabled": current_config.hyperliquid.enable_live,
            "repo_root": str(repo_root),
        }
        if extra:
            context.update(extra)
        return context

    def page_response(request: Request, page: str, template_name: str, extra: dict[str, Any] | None = None) -> HTMLResponse:
        session = load_session(request)
        if session is None:
            return RedirectResponse("/ui/login", status_code=303)
        return templates.TemplateResponse(request, template_name, template_context(request, page, session=session, extra=extra))

    @app.get("/ui", response_class=HTMLResponse)
    async def operator_home(request: Request):
        session = load_session(request)
        if session is None:
            return RedirectResponse("/ui/login", status_code=303)
        return RedirectResponse("/ui/overview", status_code=303)

    @app.get("/ui/login", response_class=HTMLResponse)
    async def operator_login_page(request: Request):
        return templates.TemplateResponse(request, "login.html", {"request": request, "error": None})

    @app.post("/ui/login", response_class=HTMLResponse)
    async def operator_login(request: Request, password: str = Form(...)):
        if not secrets.compare_digest(password, active_config().operator_ui.secret or ""):
            return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Invalid secret"}, status_code=401)
        session = {"authenticated": True, "csrf_token": secrets.token_urlsafe(24)}
        response = RedirectResponse("/ui/overview", status_code=303)
        response.set_cookie(
            active_config().operator_ui.session_cookie_name,
            serializer().dumps(session),
            httponly=True,
            samesite="lax",
        )
        return response

    @app.post("/ui/logout")
    async def operator_logout(request: Request):
        response = RedirectResponse("/ui/login", status_code=303)
        response.delete_cookie(active_config().operator_ui.session_cookie_name)
        return response

    @app.get("/ui/overview", response_class=HTMLResponse)
    async def operator_overview(request: Request):
        return page_response(request, "overview", "overview.html")

    @app.get("/ui/control", response_class=HTMLResponse)
    async def operator_control(request: Request):
        return page_response(request, "control", "control.html")

    @app.get("/ui/timeline", response_class=HTMLResponse)
    async def operator_timeline(request: Request):
        return page_response(request, "timeline", "timeline.html")

    @app.get("/ui/research", response_class=HTMLResponse)
    async def operator_research(request: Request):
        return page_response(request, "research", "research.html")

    @app.get("/ui/predictions", response_class=HTMLResponse)
    async def operator_predictions(request: Request):
        return page_response(request, "predictions", "predictions.html")

    @app.get("/ui/guides", response_class=HTMLResponse)
    async def operator_guides(request: Request):
        return page_response(
            request,
            "guides",
            "guides.html",
            extra={"guide_documents": service.list_guide_documents()},
        )

    @app.get("/api/operator/snapshot")
    async def operator_snapshot(request: Request, symbol: str = "BTCUSDT"):
        require_session_json(request)
        return await service.snapshot(symbol.upper())

    @app.get("/api/operator/feed")
    async def operator_feed(
        request: Request,
        after_id: str | None = None,
        limit: int = 50,
        include_health_events: bool = True,
        include_execution_metrics: bool = True,
    ):
        require_session_json(request)
        return await service.feed(
            after_id=after_id,
            limit=max(1, min(limit, 200)),
            include_health_events=include_health_events,
            include_execution_metrics=include_execution_metrics,
        )

    @app.get("/api/operator/research/artifacts")
    async def operator_research_artifacts(request: Request):
        require_session_json(request)
        return {"items": service.list_artifacts()}

    @app.get("/api/operator/research/r104-readiness")
    async def operator_r104_readiness(request: Request):
        require_session_json(request)
        return service.r104_readiness_diagnostics()

    @app.get("/api/operator/research/historical-data-catalog")
    async def operator_historical_data_catalog(request: Request):
        require_session_json(request)
        return service.historical_data_catalog_diagnostics()

    @app.get("/api/operator/research/progress")
    async def operator_research_progress(request: Request):
        require_session_json(request)
        return await service.research_progress_diagnostics()

    @app.get("/api/operator/shadow/diagnostics")
    async def operator_shadow_diagnostics(request: Request, symbol: str = "BTCUSDT", limit: int = 20):
        require_session_json(request)
        return await service.shadow_diagnostics(symbol.upper(), limit=max(1, min(limit, 100)))

    @app.get("/api/operator/stage13/readiness")
    async def operator_stage13_readiness(request: Request):
        require_session_json(request)
        return service.stage13_readiness_diagnostics()

    @app.get("/api/operator/research/jobs")
    async def operator_jobs(request: Request):
        require_session_json(request)
        return {"items": await service.list_jobs()}

    @app.get("/api/operator/research/jobs/{job_id}")
    async def operator_job(request: Request, job_id: str):
        require_session_json(request)
        job = await service.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.get("/api/operator/guides")
    async def operator_guides_api(request: Request):
        require_session_json(request)
        return {"items": service.list_guide_documents()}

    @app.post("/api/operator/commands/manual-signal")
    async def operator_manual_signal(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        return await service.execute_command(
            "manual-signal",
            {
                "symbol": str(payload.get("symbol", "BTCUSDT")).upper(),
                "direction": str(payload["direction"]),
                "testnet_short_lived_protections": bool(payload.get("testnet_short_lived_protections", False)),
            },
        )

    @app.post("/api/operator/commands/supervise")
    async def operator_supervise(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        return await service.execute_command("supervise", {"symbol": str(payload.get("symbol", "BTCUSDT")).upper()})

    @app.post("/api/operator/commands/reconcile")
    async def operator_reconcile(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        return await service.execute_command("reconcile", {"symbol": str(payload.get("symbol", "BTCUSDT")).upper()})

    @app.post("/api/operator/commands/refresh-health")
    async def operator_refresh_health(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        return await service.execute_command("refresh-health", {"symbol": str(payload.get("symbol", "BTCUSDT")).upper()})

    @app.post("/api/operator/commands/smoke-live")
    async def operator_smoke_live(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        return await service.execute_command("smoke-live", {"size": payload.get("size")})

    @app.post("/api/operator/commands/set-mode")
    async def operator_set_mode(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        mode = RuntimeMode(str(payload["mode"]))
        return await service.execute_command("set-mode", {"mode": str(mode)})

    @app.post("/api/operator/research/jobs/build-dataset")
    async def operator_build_dataset(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        try:
            return await service.queue_job("build-dataset", {})
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/prepare-hmm-knn-research-data")
    async def operator_prepare_hmm_knn_research_data(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        stage = str(payload.get("stage") or DATA_PIPELINE_DEFAULT_STAGE)
        if stage not in DATA_PIPELINE_STAGES:
            raise HTTPException(status_code=400, detail=f"stage must be one of: {', '.join(DATA_PIPELINE_STAGES)}")
        spec_path = validate_provider_pipeline_request(payload)
        try:
            return await service.queue_job(
                "prepare-hmm-knn-research-data",
                {
                    "spec_path": str(spec_path),
                    "stage": stage,
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/refresh-historical-data-catalog")
    async def operator_refresh_historical_data_catalog(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()

        def month_value(field: str, default: str) -> str:
            value = str(payload.get(field) or default).strip()
            parts = value.split("-")
            if len(parts) != 2:
                raise HTTPException(status_code=400, detail=f"{field} must be YYYY-MM")
            try:
                year = int(parts[0])
                month = int(parts[1])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"{field} must be YYYY-MM") from exc
            if year < 2019 or year > 2100 or month < 1 or month > 12:
                raise HTTPException(status_code=400, detail=f"{field} is outside the supported public-archive range")
            return f"{year:04d}-{month:02d}"

        symbols_raw = payload.get("symbols") or ["BTCUSDT", "ETHUSDT"]
        if not isinstance(symbols_raw, list) or not symbols_raw:
            raise HTTPException(status_code=400, detail="symbols must be a non-empty list")
        symbols = [str(symbol).strip().upper() for symbol in symbols_raw if str(symbol).strip()]
        unsupported = sorted(set(symbols) - {"BTCUSDT", "ETHUSDT"})
        if unsupported:
            raise HTTPException(status_code=400, detail=f"unsupported symbols: {', '.join(unsupported)}")
        try:
            return await service.queue_job(
                "refresh-historical-data-catalog",
                {
                    "symbols": symbols,
                    "start_month": month_value("start_month", DEFAULT_HISTORICAL_CATALOG_START_MONTH),
                    "end_month": month_value("end_month", default_historical_catalog_end_month()),
                    "source_name": "historical_data_catalog",
                    "market": "futures/um",
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/collect-durable-data")
    async def operator_collect_durable_data(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()

        def month_value(field: str, default: str) -> str:
            value = str(payload.get(field) or default).strip()
            parts = value.split("-")
            if len(parts) != 2:
                raise HTTPException(status_code=400, detail=f"{field} must be YYYY-MM")
            try:
                year = int(parts[0])
                month = int(parts[1])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"{field} must be YYYY-MM") from exc
            if year < 2019 or year > 2026 or month < 1 or month > 12:
                raise HTTPException(status_code=400, detail=f"{field} is outside the supported public-archive range")
            return f"{year:04d}-{month:02d}"

        symbols_raw = payload.get("symbols") or ["BTCUSDT", "ETHUSDT"]
        if not isinstance(symbols_raw, list) or not symbols_raw:
            raise HTTPException(status_code=400, detail="symbols must be a non-empty list")
        symbols = [str(symbol).strip().upper() for symbol in symbols_raw if str(symbol).strip()]
        unsupported = sorted(set(symbols) - {"BTCUSDT", "ETHUSDT"})
        if unsupported:
            raise HTTPException(status_code=400, detail=f"unsupported symbols: {', '.join(unsupported)}")
        try:
            return await service.queue_job(
                "collect-durable-data",
                {
                    "symbols": symbols,
                    "start_month": month_value("start_month", "2024-01"),
                    "end_month": month_value("end_month", "2024-12"),
                    "source_name": "binance_vision",
                    "market": "futures/um",
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/run-research-experiment")
    async def operator_run_research_experiment(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        spec_path = validate_research_experiment_request(payload)
        try:
            return await service.queue_job(
                "run-research-experiment",
                {
                    "spec_path": str(spec_path),
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/run-historical-research-cycle")
    async def operator_run_historical_research_cycle(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        spec_path = validate_historical_cycle_request(payload)
        try:
            return await service.queue_job(
                "run-historical-research-cycle",
                {
                    "spec_path": str(spec_path),
                    "overwrite_protection": "isolated_output_dir",
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/run-discovery")
    async def operator_run_discovery(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        spec_path = validate_discovery_run_request(payload)
        stable_run_id = bool(payload.get("stable_run_id", False)) or exact_required_discovery_spec(spec_path)
        try:
            return await service.queue_job(
                "run-discovery",
                {
                    "spec_path": str(spec_path),
                    "resume": bool(payload.get("resume", False)),
                    "stop_after_trials": validate_stop_after_trials(payload.get("stop_after_trials")),
                    "stable_run_id": stable_run_id,
                    "overwrite_protection": "stable_run_id_output_dir" if stable_run_id else "isolated_run_id_output_dir",
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/run-research-autopilot")
    async def operator_run_research_autopilot(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        symbols_raw = payload.get("symbols") or ["BTCUSDT", "ETHUSDT"]
        if not isinstance(symbols_raw, list) or not symbols_raw:
            raise HTTPException(status_code=400, detail="symbols must be a non-empty list")
        symbols = [str(symbol).strip().upper() for symbol in symbols_raw if str(symbol).strip()]
        unsupported = sorted(set(symbols) - {"BTCUSDT", "ETHUSDT"})
        if unsupported:
            raise HTTPException(status_code=400, detail=f"unsupported symbols: {', '.join(unsupported)}")

        def bounded_int(field: str, default: int, minimum: int, maximum: int) -> int:
            raw = payload.get(field, default)
            try:
                value = int(raw)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=f"{field} must be an integer") from exc
            if value < minimum or value > maximum:
                raise HTTPException(status_code=400, detail=f"{field} must be between {minimum} and {maximum}")
            return value

        stop_after = payload.get("discovery_stop_after_trials")
        if stop_after is not None and str(stop_after).strip() != "":
            stop_after = validate_stop_after_trials(stop_after)
        else:
            stop_after = None
        try:
            return await service.queue_job(
                "run-research-autopilot",
                {
                    "symbols": list(dict.fromkeys(symbols)),
                    "max_steps": bounded_int("max_steps", 100, 1, 100),
                    "include_catalog_refresh": bool(payload.get("include_catalog_refresh", True)),
                    "include_eligibility": bool(payload.get("include_eligibility", True)),
                    "include_trade_sortino": bool(payload.get("include_trade_sortino", True)),
                    "max_sortino_trade_files": bounded_int("max_sortino_trade_files", 1000, 0, 100000),
                    "discovery_stop_after_trials": stop_after,
                    "source_name": "research_autopilot",
                    "market": "futures/um",
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/analyze-research-results")
    async def operator_analyze_research_results(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        cycle_manifest_path = validate_optional_research_file_path(payload, "cycle_manifest_path")
        discovery_manifest_path = validate_optional_research_file_path(payload, "discovery_manifest_path")
        if cycle_manifest_path is None and discovery_manifest_path is None:
            raise HTTPException(status_code=400, detail="cycle_manifest_path or discovery_manifest_path is required")
        if cycle_manifest_path is not None and cycle_manifest_path.name != "research_cycle_manifest.json":
            raise HTTPException(status_code=400, detail="cycle_manifest_path must reference research_cycle_manifest.json")
        if discovery_manifest_path is not None and discovery_manifest_path.name != "discovery_run_manifest.json":
            raise HTTPException(status_code=400, detail="discovery_manifest_path must reference discovery_run_manifest.json")
        raw_max_sortino = payload.get("max_sortino_trade_files", 1000)
        try:
            max_sortino_trade_files = int(raw_max_sortino)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="max_sortino_trade_files must be an integer") from exc
        if max_sortino_trade_files < 0 or max_sortino_trade_files > 100000:
            raise HTTPException(status_code=400, detail="max_sortino_trade_files must be between 0 and 100000")
        try:
            return await service.queue_job(
                "analyze-research-results",
                {
                    "cycle_manifest_path": str(cycle_manifest_path) if cycle_manifest_path is not None else None,
                    "discovery_manifest_path": str(discovery_manifest_path) if discovery_manifest_path is not None else None,
                    "include_trade_sortino": bool(payload.get("include_trade_sortino", True)),
                    "max_sortino_trade_files": max_sortino_trade_files,
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/analyze-research-delta")
    async def operator_analyze_research_delta(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        current_analysis_path = validate_optional_research_file_path(payload, "current_analysis_path")
        previous_analysis_path = validate_optional_research_file_path(payload, "previous_analysis_path")
        if current_analysis_path is not None and current_analysis_path.name != "research_analysis.json":
            raise HTTPException(status_code=400, detail="current_analysis_path must reference research_analysis.json")
        if previous_analysis_path is not None and previous_analysis_path.name != "research_analysis.json":
            raise HTTPException(status_code=400, detail="previous_analysis_path must reference research_analysis.json")
        symbol = str(payload.get("symbol") or "").strip().upper()
        if symbol and symbol not in {"BTCUSDT", "ETHUSDT"}:
            raise HTTPException(status_code=400, detail="symbol must be BTCUSDT or ETHUSDT when supplied")
        try:
            return await service.queue_job(
                "analyze-research-delta",
                {
                    "current_analysis_path": str(current_analysis_path) if current_analysis_path is not None else None,
                    "previous_analysis_path": str(previous_analysis_path) if previous_analysis_path is not None else None,
                    "symbol": symbol or None,
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/run-frozen-entry-exit-lab")
    async def operator_run_frozen_entry_exit_lab(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        discovery_manifest_path = validate_research_file_path(payload, "discovery_manifest_path")
        if discovery_manifest_path.name != "discovery_run_manifest.json":
            raise HTTPException(status_code=400, detail="discovery_manifest_path must reference discovery_run_manifest.json")
        entry_signals_path = validate_optional_research_file_path(payload, "entry_signals_path")
        market_data_path = validate_optional_research_file_path(payload, "market_data_path")
        raw_max_candidates = payload.get("max_candidates", 12)
        try:
            max_candidates = int(raw_max_candidates)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="max_candidates must be an integer") from exc
        if max_candidates < 1 or max_candidates > 100:
            raise HTTPException(status_code=400, detail="max_candidates must be between 1 and 100")
        try:
            return await service.queue_job(
                "run-frozen-entry-exit-lab",
                {
                    "discovery_manifest_path": str(discovery_manifest_path),
                    "entry_signals_path": str(entry_signals_path) if entry_signals_path is not None else None,
                    "market_data_path": str(market_data_path) if market_data_path is not None else None,
                    "max_candidates": max_candidates,
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/evaluate-discovery-candidate-pack-eligibility")
    async def operator_evaluate_discovery_candidate_pack_eligibility(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        discovery_manifest_path = validate_research_file_path(payload, "discovery_manifest_path")
        cycle_manifest_path = validate_optional_research_file_path(payload, "cycle_manifest_path")
        exit_lab_manifest_path = validate_optional_research_file_path(payload, "exit_lab_manifest_path")
        multiple_testing_manifest_path = validate_optional_research_file_path(payload, "multiple_testing_manifest_path")
        validation_floors_manifest_path = validate_optional_research_file_path(payload, "validation_floors_manifest_path")
        try:
            return await service.queue_job(
                "evaluate-discovery-candidate-pack-eligibility",
                {
                    "discovery_manifest_path": str(discovery_manifest_path),
                    "cycle_manifest_path": str(cycle_manifest_path) if cycle_manifest_path is not None else None,
                    "exit_lab_manifest_path": str(exit_lab_manifest_path) if exit_lab_manifest_path is not None else None,
                    "multiple_testing_manifest_path": str(multiple_testing_manifest_path) if multiple_testing_manifest_path is not None else None,
                    "validation_floors_manifest_path": str(validation_floors_manifest_path) if validation_floors_manifest_path is not None else None,
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/benchmark-hardware-utilization")
    async def operator_benchmark_hardware_utilization(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()

        def bounded_number(field: str, default: float, minimum: float, maximum: float) -> float:
            raw = payload.get(field, default)
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=f"{field} must be numeric") from exc
            if value < minimum or value > maximum:
                raise HTTPException(status_code=400, detail=f"{field} must be between {minimum:g} and {maximum:g}")
            return value

        def bounded_int(field: str, default: int, minimum: int, maximum: int) -> int:
            raw = payload.get(field, default)
            try:
                if isinstance(raw, float) and not raw.is_integer():
                    raise ValueError
                if isinstance(raw, str) and "." in raw.strip():
                    raise ValueError
                value = int(raw)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=f"{field} must be an integer") from exc
            if value < minimum or value > maximum:
                raise HTTPException(status_code=400, detail=f"{field} must be between {minimum} and {maximum}")
            return value

        cpu_workers = payload.get("cpu_workers")
        if cpu_workers is not None and str(cpu_workers).strip() != "":
            cpu_workers = bounded_int("cpu_workers", 1, 1, WINDOWS_PROCESS_POOL_MAX_WORKERS)
        else:
            cpu_workers = None
        try:
            return await service.queue_job(
                "benchmark-hardware-utilization",
                {
                    "cpu_workers": cpu_workers,
                    "cpu_seconds": bounded_number(
                        "cpu_seconds",
                        DEFAULT_CPU_SECONDS,
                        MIN_PROBE_SECONDS,
                        MAX_CPU_SECONDS,
                    ),
                    "gpu_seconds": bounded_number(
                        "gpu_seconds",
                        DEFAULT_GPU_SECONDS,
                        MIN_PROBE_SECONDS,
                        MAX_GPU_SECONDS,
                    ),
                    "matrix_size": bounded_int(
                        "matrix_size",
                        DEFAULT_MATRIX_SIZE,
                        MIN_MATRIX_SIZE,
                        MAX_MATRIX_SIZE,
                    ),
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/train-model")
    async def operator_train_model(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        dataset_path = validate_research_file_path(payload, "dataset_path")
        try:
            return await service.queue_job("train-model", {"dataset_path": str(dataset_path)})
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/calibrate-model")
    async def operator_calibrate_model(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        train_manifest_path = validate_research_file_path(payload, "train_manifest_path")
        try:
            return await service.queue_job("calibrate-model", {"train_manifest_path": str(train_manifest_path)})
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/operator/research/jobs/replay-eval")
    async def operator_replay_eval(request: Request):
        require_same_origin(request)
        session = require_session_json(request)
        require_csrf(request, session)
        payload = await request.json()
        artifact_manifest_path = validate_research_file_path(payload, "artifact_manifest_path")
        try:
            return await service.queue_job("replay-eval", {"artifact_manifest_path": str(artifact_manifest_path)})
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
