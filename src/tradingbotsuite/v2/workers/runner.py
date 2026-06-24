# V2-AUDIT-ID: V2-AUD-WORKER-001
# V2-CONTRACTS: docs/contracts/worker_job_contract.md, docs/contracts/collector_job_contract.md
# V2-BOUNDARY: research_only, worker_runner, no_live_imports
# V2-OWNER: v2_workers
"""Worker runner for one durable v2 job at a time."""

from __future__ import annotations

from tradingbotsuite.v2.audit.jobs import run_audit_job
from tradingbotsuite.v2.backtest_data.jobs import run_backtest_data_job
from tradingbotsuite.v2.backtest_engine.jobs import run_backtest_job
from tradingbotsuite.v2.collectors.jobs import run_collector_job
from tradingbotsuite.v2.data_quality.jobs import run_data_quality_job
from tradingbotsuite.v2.ledger.jobs import run_ledger_job
from tradingbotsuite.v2.lead_book.jobs import run_lead_book_job
from tradingbotsuite.v2.validation.jobs import run_validation_job
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerRunResult

COLLECTOR_KINDS = {
    WorkerJobKind.UNIVERSE_REFRESH,
    WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
    WorkerJobKind.FUNDING_BACKFILL,
    WorkerJobKind.WEBSOCKET_CAPTURE,
    WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
    WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
    WorkerJobKind.OFFICIAL_S3_BACKFILL,
    WorkerJobKind.BINANCE_DERIVATIVES_CONTEXT_BACKFILL,
}

DATA_QUALITY_KINDS = {
    WorkerJobKind.COVERAGE_AUDIT,
}

STRATEGY_QUEUE_KINDS = {
    WorkerJobKind.STRATEGY_QUEUE_SCAN,
}

BACKTEST_DATA_KINDS = {
    WorkerJobKind.BACKTEST_DATA_LOAD,
}

BACKTEST_KINDS = {
    WorkerJobKind.BACKTEST,
    WorkerJobKind.VECTORIZED_BACKTEST,
}

VALIDATION_KINDS = {
    WorkerJobKind.VALIDATION_GATE,
}

LEDGER_KINDS = {
    WorkerJobKind.LEDGER_APPEND_EXPORT,
}

LEAD_BOOK_KINDS = {
    WorkerJobKind.LEAD_BOOK_SCAN,
    WorkerJobKind.LEAD_BOOK_UPSERT,
}

AUDIT_KINDS = {
    WorkerJobKind.AUDIT_CHECK,
}


def run_one_job(
    *,
    store: WorkerJobStore,
    kind: WorkerJobKind | str,
    worker_id: str,
    forbid_asgi: bool = False,
) -> WorkerRunResult | None:
    if forbid_asgi:
        raise RuntimeError("worker jobs must not run inside ASGI/operator process")
    job_kind = WorkerJobKind(kind)
    claimed = store.claim_next(kind=job_kind, worker_id=worker_id)
    if claimed is None:
        return None
    running = store.start_job(claimed.job_id, worker_id=worker_id)
    store.heartbeat(running.job_id, worker_id=worker_id, details={"phase": "running"})
    try:
        if job_kind in COLLECTOR_KINDS:
            return run_collector_job(job=running, store=store, worker_id=worker_id)
        if job_kind in DATA_QUALITY_KINDS:
            return run_data_quality_job(job=running, store=store, worker_id=worker_id)
        if job_kind in STRATEGY_QUEUE_KINDS:
            from tradingbotsuite.v2.autonomy.strategy_queue import run_strategy_queue_job

            return run_strategy_queue_job(job=running, store=store, worker_id=worker_id)
        if job_kind in BACKTEST_DATA_KINDS:
            return run_backtest_data_job(job=running, store=store, worker_id=worker_id)
        if job_kind in BACKTEST_KINDS:
            return run_backtest_job(job=running, store=store, worker_id=worker_id)
        if job_kind in VALIDATION_KINDS:
            return run_validation_job(job=running, store=store, worker_id=worker_id)
        if job_kind in LEDGER_KINDS:
            return run_ledger_job(job=running, store=store, worker_id=worker_id)
        if job_kind in LEAD_BOOK_KINDS:
            return run_lead_book_job(job=running, store=store, worker_id=worker_id)
        if job_kind in AUDIT_KINDS:
            return run_audit_job(job=running, store=store, worker_id=worker_id)
        raise ValueError(f"worker kind is not implemented in Phase 7: {job_kind.value}")
    except Exception as exc:
        failed = store.fail_job(
            running.job_id,
            worker_id=worker_id,
            reason=str(exc),
            retryable=running.attempts < running.max_attempts,
        )
        return WorkerRunResult(
            job_id=running.job_id,
            status=failed.status,
            output_refs=failed.output_refs,
            archive_manifest_refs=failed.archive_manifest_refs,
            gap_record_ids=failed.gap_record_ids,
            failure_reason=failed.failure_reason,
        )
