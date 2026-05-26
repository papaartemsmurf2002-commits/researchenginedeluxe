from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import aiosqlite

from tradingbotsuite.core.models import ActionTicket, DecisionPacket, PositionState, SafetyStatus, SignalIntent


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _operator_payload_symbol(*payloads: dict[str, Any] | None, default: str | None = None) -> str | None:
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        symbol = payload.get("symbol")
        if isinstance(symbol, str) and symbol.strip():
            return symbol.strip().upper()
        asset_scope = payload.get("asset_scope")
        if isinstance(asset_scope, list) and len(asset_scope) == 1 and isinstance(asset_scope[0], str):
            return asset_scope[0].strip().upper()
    text = json.dumps(payloads, default=str, sort_keys=True).lower()
    has_eth = "ethusdt" in text
    has_btc = "btcusdt" in text
    if has_eth and not has_btc:
        return "ETHUSDT"
    if has_btc and not has_eth:
        return "BTCUSDT"
    return default


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialized = False

    async def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA foreign_keys=ON;")
            await db.execute("PRAGMA busy_timeout=5000;")
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    signal_bar_time_ms INTEGER NOT NULL,
                    received_time_ms INTEGER NOT NULL,
                    accepted INTEGER,
                    rejection_reason TEXT,
                    raw_payload_json TEXT NOT NULL,
                    PRIMARY KEY (signal_id, symbol, signal_bar_time_ms)
                );

                CREATE TABLE IF NOT EXISTS trade_state (
                    symbol TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    direction TEXT,
                    position_size TEXT NOT NULL,
                    entry_price TEXT,
                    entry_time_ms INTEGER,
                    entry_bar_time_ms INTEGER,
                    entry_atr TEXT,
                    hurst_at_entry TEXT,
                    imbalance_at_entry TEXT,
                    tp_price TEXT,
                    sl_price TEXT,
                    vertical_barrier_time_ms INTEGER,
                    entry_order_cloid TEXT,
                    tp_order_cloid TEXT,
                    sl_order_cloid TEXT,
                    last_exchange_reconcile_ms INTEGER,
                    last_exit_reason TEXT,
                    last_updated_ms INTEGER
                );

                CREATE TABLE IF NOT EXISTS trade_events (
                    event_id TEXT PRIMARY KEY,
                    signal_id TEXT,
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_time_ms INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS action_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    decision_time_ms INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    readable_summary TEXT NOT NULL,
                    features_json TEXT NOT NULL,
                    intended_orders_json TEXT NOT NULL,
                    rationale_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decision_packets (
                    signal_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    decision_time_ms INTEGER NOT NULL,
                    packet_json TEXT NOT NULL,
                    PRIMARY KEY (signal_id, symbol, decision_time_ms)
                );

                CREATE TABLE IF NOT EXISTS runtime_state (
                    state_key TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operator_commands (
                    command_id TEXT PRIMARY KEY,
                    command_type TEXT NOT NULL,
                    requested_at_ms INTEGER NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    success INTEGER
                );

                CREATE TABLE IF NOT EXISTS operator_jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_at_ms INTEGER NOT NULL,
                    started_at_ms INTEGER,
                    finished_at_ms INTEGER,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    error_text TEXT
                );

                CREATE TABLE IF NOT EXISTS operator_job_logs (
                    job_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    time_ms INTEGER NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (job_id, seq)
                );

                CREATE TABLE IF NOT EXISTS execution_metrics (
                    metric_id TEXT PRIMARY KEY,
                    signal_id TEXT,
                    symbol TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    recorded_time_ms INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS health_events (
                    event_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    state TEXT NOT NULL,
                    reason_code TEXT,
                    event_time_ms INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    recommended_action TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS supervision_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    time_ms INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS signal_import_batches (
                    batch_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_mode TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy_version TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    source_file_name TEXT NOT NULL,
                    import_mode TEXT NOT NULL,
                    imported_count INTEGER NOT NULL,
                    skipped_count INTEGER NOT NULL,
                    duplicate_count INTEGER NOT NULL,
                    first_signal_time_ms INTEGER,
                    last_signal_time_ms INTEGER,
                    import_time_ms INTEGER NOT NULL,
                    notes TEXT,
                    payload_json TEXT NOT NULL
                );
                """
            )
            await db.commit()
        self._initialized = True

    async def _connect(self) -> aiosqlite.Connection:
        if not self._initialized:
            await self.initialize()
        connection = await aiosqlite.connect(self.db_path)
        connection.row_factory = aiosqlite.Row
        await connection.execute("PRAGMA foreign_keys=ON;")
        await connection.execute("PRAGMA busy_timeout=5000;")
        return connection

    @asynccontextmanager
    async def _connection(self):
        db = await self._connect()
        try:
            yield db
        finally:
            await db.close()

    async def reserve_signal(self, signal: SignalIntent) -> bool:
        payload_json = json.dumps(signal.raw_payload, default=_json_default, sort_keys=True)
        async with self._connection() as db:
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO signals (
                    signal_id, source, symbol, direction, signal_bar_time_ms, received_time_ms,
                    accepted, rejection_reason, raw_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)
                """,
                (
                    signal.signal_id,
                    signal.source,
                    signal.symbol,
                    signal.direction,
                    signal.signal_bar_time_ms,
                    signal.received_time_ms,
                    payload_json,
                ),
            )
            await db.commit()
            return cursor.rowcount == 1

    async def save_signal_import_batch(
        self,
        *,
        batch: dict[str, Any],
        signals: list[SignalIntent],
        mode: str,
    ) -> dict[str, int]:
        if mode not in {"replace-batch", "append-only"}:
            raise ValueError(f"unsupported import mode: {mode}")
        batch_id = str(batch["batch_id"])
        symbol = str(batch["symbol"]).upper()
        imported_count = 0
        duplicate_count = 0
        async with self._connection() as db:
            try:
                await db.execute("BEGIN")
                if mode == "replace-batch":
                    prefix = f"{batch_id}:%"
                    await db.execute(
                        """
                        DELETE FROM decision_packets
                        WHERE symbol = ?
                          AND signal_id IN (
                              SELECT signal_id
                              FROM signals
                              WHERE symbol = ? AND source = 'research_signal' AND signal_id LIKE ?
                          )
                        """,
                        (symbol, symbol, prefix),
                    )
                    await db.execute(
                        """
                        DELETE FROM signals
                        WHERE symbol = ? AND source = 'research_signal' AND signal_id LIKE ?
                        """,
                        (symbol, prefix),
                    )

                for signal in signals:
                    cursor = await db.execute(
                        """
                        INSERT OR IGNORE INTO signals (
                            signal_id, source, symbol, direction, signal_bar_time_ms, received_time_ms,
                            accepted, rejection_reason, raw_payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)
                        """,
                        (
                            signal.signal_id,
                            signal.source,
                            signal.symbol,
                            signal.direction,
                            signal.signal_bar_time_ms,
                            signal.received_time_ms,
                            json.dumps(signal.raw_payload, default=_json_default, sort_keys=True),
                        ),
                    )
                    if cursor.rowcount == 1:
                        imported_count += 1
                    else:
                        duplicate_count += 1

                payload = {
                    **batch,
                    "imported_count": imported_count,
                    "duplicate_count": duplicate_count,
                }
                await db.execute(
                    """
                    INSERT OR REPLACE INTO signal_import_batches (
                        batch_id, source, source_mode, symbol, strategy_version, timeframe,
                        source_path, source_sha256, source_file_name, import_mode,
                        imported_count, skipped_count, duplicate_count,
                        first_signal_time_ms, last_signal_time_ms, import_time_ms,
                        notes, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        str(batch["source"]),
                        str(batch["source_mode"]),
                        symbol,
                        str(batch["strategy_version"]),
                        str(batch["timeframe"]),
                        str(batch["source_path"]),
                        str(batch["source_sha256"]),
                        str(batch["source_file_name"]),
                        mode,
                        imported_count,
                        int(batch["skipped_count"]),
                        duplicate_count,
                        batch.get("first_signal_time_ms"),
                        batch.get("last_signal_time_ms"),
                        int(batch["import_time_ms"]),
                        batch.get("notes"),
                        json.dumps(payload, default=_json_default, sort_keys=True),
                    ),
                )
                await db.commit()
            except Exception:
                await db.rollback()
                raise
        return {"imported_count": imported_count, "duplicate_count": duplicate_count}

    async def list_signal_import_batches(self, symbol: str | None = None) -> list[dict[str, Any]]:
        async with self._connection() as db:
            if symbol is None:
                cursor = await db.execute(
                    """
                    SELECT *
                    FROM signal_import_batches
                    ORDER BY import_time_ms DESC, batch_id DESC
                    """
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT *
                    FROM signal_import_batches
                    WHERE symbol = ?
                    ORDER BY import_time_ms DESC, batch_id DESC
                    """,
                    (symbol.upper(),),
                )
            rows = await cursor.fetchall()
        return [
            {
                **dict(row),
                "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
            }
            for row in rows
        ]

    async def update_signal_decision(self, signal: SignalIntent, *, accepted: bool, rejection_reason: str | None) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                UPDATE signals
                SET accepted = ?, rejection_reason = ?
                WHERE signal_id = ? AND symbol = ? AND signal_bar_time_ms = ?
                """,
                (
                    1 if accepted else 0,
                    rejection_reason,
                    signal.signal_id,
                    signal.symbol,
                    signal.signal_bar_time_ms,
                ),
            )
            await db.commit()

    async def save_decision_packet(self, packet: DecisionPacket, decision_time_ms: int) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO decision_packets (signal_id, symbol, decision_time_ms, packet_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    packet.signal.signal_id,
                    packet.signal.symbol,
                    decision_time_ms,
                    packet.model_dump_json(),
                ),
            )
            await db.commit()

    async def save_action_ticket(self, ticket: ActionTicket) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO action_tickets (
                    ticket_id, signal_id, mode, symbol, decision_time_ms, action_type,
                    readable_summary, features_json, intended_orders_json, rationale_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket.ticket_id,
                    ticket.signal_id,
                    ticket.mode,
                    ticket.symbol,
                    ticket.decision_time_ms,
                    ticket.action_type,
                    ticket.readable_summary,
                    json.dumps(ticket.features_json, default=_json_default, sort_keys=True),
                    json.dumps(ticket.intended_orders_json, default=_json_default, sort_keys=True),
                    json.dumps(ticket.rationale_json, default=_json_default, sort_keys=True),
                ),
            )
            await db.commit()

    async def append_trade_event(
        self,
        *,
        event_id: str,
        signal_id: str | None,
        symbol: str,
        event_type: str,
        event_time_ms: int,
        payload: dict[str, Any],
    ) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO trade_events (event_id, signal_id, symbol, event_type, event_time_ms, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    signal_id,
                    symbol,
                    event_type,
                    event_time_ms,
                    json.dumps(payload, default=_json_default, sort_keys=True),
                ),
            )
            await db.commit()

    async def upsert_position_state(self, position: PositionState) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO trade_state (
                    symbol, status, direction, position_size, entry_price, entry_time_ms, entry_bar_time_ms,
                    entry_atr, hurst_at_entry, imbalance_at_entry, tp_price, sl_price,
                    vertical_barrier_time_ms, entry_order_cloid, tp_order_cloid, sl_order_cloid,
                    last_exchange_reconcile_ms, last_exit_reason, last_updated_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.symbol,
                    position.status,
                    position.direction,
                    str(position.position_size),
                    str(position.entry_price) if position.entry_price is not None else None,
                    position.entry_time_ms,
                    position.entry_bar_time_ms,
                    str(position.entry_atr) if position.entry_atr is not None else None,
                    str(position.hurst_at_entry) if position.hurst_at_entry is not None else None,
                    str(position.imbalance_at_entry) if position.imbalance_at_entry is not None else None,
                    str(position.tp_price) if position.tp_price is not None else None,
                    str(position.sl_price) if position.sl_price is not None else None,
                    position.vertical_barrier_time_ms,
                    position.entry_order_cloid,
                    position.tp_order_cloid,
                    position.sl_order_cloid,
                    position.last_exchange_reconcile_ms,
                    position.last_exit_reason,
                    position.last_updated_ms,
                ),
            )
            await db.commit()

    async def get_position_state(self, symbol: str) -> PositionState | None:
        async with self._connection() as db:
            cursor = await db.execute("SELECT * FROM trade_state WHERE symbol = ?", (symbol,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return self._position_from_row(row)

    async def list_position_states(self) -> list[PositionState]:
        async with self._connection() as db:
            cursor = await db.execute("SELECT * FROM trade_state")
            rows = await cursor.fetchall()
        return [self._position_from_row(row) for row in rows]

    def _position_from_row(self, row: aiosqlite.Row) -> PositionState:
        return PositionState(
            symbol=row["symbol"],
            status=row["status"],
            direction=row["direction"],
            position_size=Decimal(row["position_size"]),
            entry_price=Decimal(row["entry_price"]) if row["entry_price"] is not None else None,
            entry_time_ms=row["entry_time_ms"],
            entry_bar_time_ms=row["entry_bar_time_ms"],
            entry_atr=Decimal(row["entry_atr"]) if row["entry_atr"] is not None else None,
            hurst_at_entry=Decimal(row["hurst_at_entry"]) if row["hurst_at_entry"] is not None else None,
            imbalance_at_entry=Decimal(row["imbalance_at_entry"]) if row["imbalance_at_entry"] is not None else None,
            tp_price=Decimal(row["tp_price"]) if row["tp_price"] is not None else None,
            sl_price=Decimal(row["sl_price"]) if row["sl_price"] is not None else None,
            vertical_barrier_time_ms=row["vertical_barrier_time_ms"],
            entry_order_cloid=row["entry_order_cloid"],
            tp_order_cloid=row["tp_order_cloid"],
            sl_order_cloid=row["sl_order_cloid"],
            last_exchange_reconcile_ms=row["last_exchange_reconcile_ms"],
            last_exit_reason=row["last_exit_reason"],
            last_updated_ms=row["last_updated_ms"],
        )

    async def set_safety_status(self, status: SafetyStatus) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO runtime_state (state_key, state_json)
                VALUES (?, ?)
                """,
                ("safety_status", status.model_dump_json()),
            )
            await db.commit()

    async def get_safety_status(self) -> SafetyStatus | None:
        async with self._connection() as db:
            cursor = await db.execute("SELECT state_json FROM runtime_state WHERE state_key = ?", ("safety_status",))
            row = await cursor.fetchone()
        if row is None:
            return None
        return SafetyStatus.model_validate_json(row["state_json"])

    async def set_runtime_value(self, state_key: str, payload: dict[str, Any]) -> None:
        async with self._connection() as db:
            await db.execute(
                "INSERT OR REPLACE INTO runtime_state (state_key, state_json) VALUES (?, ?)",
                (state_key, json.dumps(payload, default=_json_default, sort_keys=True)),
            )
            await db.commit()

    async def get_runtime_value(self, state_key: str) -> dict[str, Any] | None:
        async with self._connection() as db:
            cursor = await db.execute("SELECT state_json FROM runtime_state WHERE state_key = ?", (state_key,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return json.loads(row["state_json"])

    async def append_execution_metric(
        self,
        *,
        metric_id: str,
        signal_id: str | None,
        symbol: str,
        metric_type: str,
        recorded_time_ms: int,
        payload: dict[str, Any],
    ) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO execution_metrics (
                    metric_id, signal_id, symbol, metric_type, recorded_time_ms, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    metric_id,
                    signal_id,
                    symbol,
                    metric_type,
                    recorded_time_ms,
                    json.dumps(payload, default=_json_default, sort_keys=True),
                ),
            )
            await db.commit()

    async def append_health_event(
        self,
        *,
        event_id: str,
        symbol: str,
        scope: str,
        state: str,
        reason_code: str | None,
        event_time_ms: int,
        summary: str,
        recommended_action: str | None,
        payload: dict[str, Any],
    ) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO health_events (
                    event_id, symbol, scope, state, reason_code, event_time_ms, summary, recommended_action, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    symbol,
                    scope,
                    state,
                    reason_code,
                    event_time_ms,
                    summary,
                    recommended_action,
                    json.dumps(payload, default=_json_default, sort_keys=True),
                ),
            )
            await db.commit()

    async def append_supervision_snapshot(
        self,
        *,
        snapshot_id: str,
        symbol: str,
        time_ms: int,
        payload: dict[str, Any],
    ) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO supervision_snapshots (snapshot_id, symbol, time_ms, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    symbol,
                    time_ms,
                    json.dumps(payload, default=_json_default, sort_keys=True),
                ),
            )
            await db.commit()

    async def get_latest_supervision_snapshot(self, symbol: str) -> dict[str, Any] | None:
        async with self._connection() as db:
            cursor = await db.execute(
                """
                SELECT snapshot_id, time_ms, payload_json
                FROM supervision_snapshots
                WHERE symbol = ?
                ORDER BY time_ms DESC, snapshot_id DESC
                LIMIT 1
                """,
                (symbol,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
        payload["snapshot_id"] = row["snapshot_id"]
        payload["time_ms"] = row["time_ms"]
        return payload

    async def list_recent_health_events(self, *, symbol: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        async with self._connection() as db:
            if symbol is None:
                cursor = await db.execute(
                    """
                    SELECT * FROM health_events
                    ORDER BY event_time_ms DESC, event_id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM health_events
                    WHERE symbol = ?
                    ORDER BY event_time_ms DESC, event_id DESC
                    LIMIT ?
                    """,
                    (symbol, limit),
                )
            rows = await cursor.fetchall()
        return [
            {
                "event_id": row["event_id"],
                "symbol": row["symbol"],
                "scope": row["scope"],
                "state": row["state"],
                "reason_code": row["reason_code"],
                "event_time_ms": row["event_time_ms"],
                "summary": row["summary"],
                "recommended_action": row["recommended_action"],
                "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
            }
            for row in rows
        ]

    async def sum_realized_pnl_since(self, *, symbol: str, start_time_ms: int) -> Decimal:
        async with self._connection() as db:
            cursor = await db.execute(
                """
                SELECT payload_json
                FROM execution_metrics
                WHERE symbol = ? AND metric_type = 'trade_close' AND recorded_time_ms >= ?
                ORDER BY recorded_time_ms ASC
                """,
                (symbol, start_time_ms),
            )
            rows = await cursor.fetchall()
        total = Decimal("0")
        for row in rows:
            payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
            pnl = payload.get("realized_pnl_quote")
            if pnl is not None:
                total += Decimal(str(pnl))
        return total

    async def summarize_runtime_metrics(self, symbol: str) -> dict[str, Any]:
        async with self._connection() as db:
            rejection_cursor = await db.execute(
                """
                SELECT rejection_reason, COUNT(*) AS count
                FROM signals
                WHERE symbol = ? AND accepted = 0 AND rejection_reason IS NOT NULL
                GROUP BY rejection_reason
                ORDER BY count DESC, rejection_reason ASC
                """,
                (symbol,),
            )
            rejection_rows = await rejection_cursor.fetchall()
            metrics_cursor = await db.execute(
                """
                SELECT metric_type, recorded_time_ms, payload_json
                FROM execution_metrics
                WHERE symbol = ?
                ORDER BY recorded_time_ms DESC, metric_id DESC
                LIMIT 200
                """,
                (symbol,),
            )
            metric_rows = await metrics_cursor.fetchall()

        rejection_reason_distribution = [
            {"reason": row["rejection_reason"], "count": int(row["count"])}
            for row in rejection_rows
        ]
        exit_reason_counts: dict[str, int] = {}
        holding_times_ms: list[int] = []
        decision_latencies_ms: list[int] = []
        slippage_bps: list[Decimal] = []
        basis_entry_bps: list[Decimal] = []
        depth_gap_incidents = 0
        reconcile_mismatches = 0
        basis_dislocations = 0
        cancel_reject_count = 0
        trade_close_count = 0

        recent_metrics: list[dict[str, Any]] = []
        for row in metric_rows:
            payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
            recent_metrics.append(
                {
                    "metric_type": row["metric_type"],
                    "recorded_time_ms": row["recorded_time_ms"],
                    "payload": payload,
                }
            )
            if row["metric_type"] == "decision":
                latency = payload.get("decision_latency_ms")
                if latency is not None:
                    decision_latencies_ms.append(int(latency))
                if payload.get("rejection_reason") == "basis_dislocation":
                    basis_dislocations += 1
                if payload.get("rejection_reason") in {"spread_abnormality", "microstructure_unhealthy"}:
                    depth_gap_incidents += 1
                report_statuses = payload.get("report_statuses") or []
                cancel_reject_count += sum(1 for status in report_statuses if status == "rejected")
            elif row["metric_type"] == "trade_close":
                trade_close_count += 1
                exit_reason = str(payload.get("exit_reason") or "unknown")
                exit_reason_counts[exit_reason] = exit_reason_counts.get(exit_reason, 0) + 1
                holding_ms = payload.get("holding_time_ms")
                if holding_ms is not None:
                    holding_times_ms.append(int(holding_ms))
                entry_slippage = payload.get("entry_slippage_bps")
                if entry_slippage is not None:
                    slippage_bps.append(Decimal(str(entry_slippage)))
                basis_entry = payload.get("basis_entry_bps")
                if basis_entry is not None:
                    basis_entry_bps.append(Decimal(str(basis_entry)))
            elif row["metric_type"] == "reconcile":
                if payload.get("mismatch"):
                    reconcile_mismatches += 1
            elif row["metric_type"] == "market_health":
                if payload.get("reason_code") == "basis_dislocation":
                    basis_dislocations += 1
                if payload.get("reason_code") == "depth_degraded":
                    depth_gap_incidents += 1

        return {
            "symbol": symbol,
            "rejection_reason_distribution": rejection_reason_distribution,
            "exit_reason_distribution": [{"reason": key, "count": value} for key, value in sorted(exit_reason_counts.items())],
            "trade_close_count": trade_close_count,
            "holding_time_ms_mean": (sum(holding_times_ms) / len(holding_times_ms) if holding_times_ms else None),
            "holding_time_ms_median": (median(holding_times_ms) if holding_times_ms else None),
            "decision_latency_ms_mean": (sum(decision_latencies_ms) / len(decision_latencies_ms) if decision_latencies_ms else None),
            "decision_latency_ms_median": (median(decision_latencies_ms) if decision_latencies_ms else None),
            "entry_slippage_bps_mean": (
                str(sum(slippage_bps, start=Decimal("0")) / Decimal(len(slippage_bps))) if slippage_bps else None
            ),
            "basis_entry_bps_mean": (
                str(sum(basis_entry_bps, start=Decimal("0")) / Decimal(len(basis_entry_bps))) if basis_entry_bps else None
            ),
            "depth_gap_incidents": depth_gap_incidents,
            "reconcile_mismatch_count": reconcile_mismatches,
            "basis_dislocation_incidents": basis_dislocations,
            "cancel_reject_count": cancel_reject_count,
            "recent_metrics": recent_metrics[:20],
        }

    async def list_research_signals(self, symbol: str) -> list[dict[str, Any]]:
        async with self._connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    s.signal_id,
                    s.source,
                    s.symbol,
                    s.direction,
                    s.signal_bar_time_ms,
                    s.received_time_ms,
                    s.accepted,
                    s.rejection_reason,
                    s.raw_payload_json,
                    (
                        SELECT dp.packet_json
                        FROM decision_packets AS dp
                        WHERE dp.signal_id = s.signal_id AND dp.symbol = s.symbol
                        ORDER BY dp.decision_time_ms DESC
                        LIMIT 1
                    ) AS decision_packet_json
                FROM signals AS s
                WHERE s.symbol = ?
                ORDER BY s.signal_bar_time_ms ASC, s.received_time_ms ASC
                """,
                (symbol,),
            )
            rows = await cursor.fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "signal_id": row["signal_id"],
                    "source": row["source"],
                    "symbol": row["symbol"],
                    "direction": row["direction"],
                    "signal_bar_time_ms": row["signal_bar_time_ms"],
                    "received_time_ms": row["received_time_ms"],
                    "accepted": None if row["accepted"] is None else bool(row["accepted"]),
                    "rejection_reason": row["rejection_reason"],
                    "raw_payload": json.loads(row["raw_payload_json"]) if row["raw_payload_json"] else {},
                    "decision_packet": (
                        json.loads(row["decision_packet_json"]) if row["decision_packet_json"] is not None else None
                    ),
                }
            )
        return result

    async def save_operator_command(
        self,
        *,
        command_id: str,
        command_type: str,
        requested_at_ms: int,
        request: dict[str, Any],
        result: dict[str, Any] | None,
        success: bool | None,
    ) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO operator_commands (
                    command_id, command_type, requested_at_ms, request_json, result_json, success
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    command_id,
                    command_type,
                    requested_at_ms,
                    json.dumps(request, default=_json_default, sort_keys=True),
                    (json.dumps(result, default=_json_default, sort_keys=True) if result is not None else None),
                    (1 if success else 0) if success is not None else None,
                ),
            )
            await db.commit()

    async def queue_operator_job(
        self,
        *,
        job_id: str,
        job_type: str,
        requested_at_ms: int,
        request: dict[str, Any],
    ) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO operator_jobs (
                    job_id, job_type, status, requested_at_ms, started_at_ms, finished_at_ms, request_json, result_json, error_text
                ) VALUES (?, ?, 'queued', ?, NULL, NULL, ?, NULL, NULL)
                """,
                (
                    job_id,
                    job_type,
                    requested_at_ms,
                    json.dumps(request, default=_json_default, sort_keys=True),
                ),
            )
            await db.commit()

    async def claim_next_operator_job(self) -> dict[str, Any] | None:
        async with self._connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM operator_jobs
                WHERE status = 'queued'
                ORDER BY requested_at_ms ASC, job_id ASC
                LIMIT 1
                """
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            await db.execute(
                """
                UPDATE operator_jobs
                SET status = 'running', started_at_ms = ?
                WHERE job_id = ? AND status = 'queued'
                """,
                (int(row["requested_at_ms"]) if row["requested_at_ms"] is not None else 0, row["job_id"]),
            )
            await db.commit()
        claimed = await self.get_operator_job(row["job_id"])
        return claimed

    async def mark_operator_job_started(self, job_id: str, started_at_ms: int) -> None:
        async with self._connection() as db:
            await db.execute(
                "UPDATE operator_jobs SET status = 'running', started_at_ms = ? WHERE job_id = ?",
                (started_at_ms, job_id),
            )
            await db.commit()

    async def complete_operator_job(
        self,
        *,
        job_id: str,
        status: str,
        finished_at_ms: int,
        result: dict[str, Any] | None = None,
        error_text: str | None = None,
    ) -> None:
        async with self._connection() as db:
            await db.execute(
                """
                UPDATE operator_jobs
                SET status = ?, finished_at_ms = ?, result_json = ?, error_text = ?
                WHERE job_id = ?
                """,
                (
                    status,
                    finished_at_ms,
                    (json.dumps(result, default=_json_default, sort_keys=True) if result is not None else None),
                    error_text,
                    job_id,
                ),
            )
            await db.commit()

    async def append_operator_job_log(
        self,
        *,
        job_id: str,
        time_ms: int,
        level: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        payload = payload or {}
        payload_json = json.dumps(payload, default=_json_default, sort_keys=True)
        last_error: sqlite3.IntegrityError | None = None
        for _ in range(5):
            async with self._connection() as db:
                try:
                    await db.execute("BEGIN IMMEDIATE")
                    cursor = await db.execute(
                        "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM operator_job_logs WHERE job_id = ?",
                        (job_id,),
                    )
                    row = await cursor.fetchone()
                    next_seq = int(row["next_seq"])
                    await db.execute(
                        """
                        INSERT INTO operator_job_logs (job_id, seq, time_ms, level, message, payload_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job_id,
                            next_seq,
                            time_ms,
                            level,
                            message,
                            payload_json,
                        ),
                    )
                    await db.commit()
                    return
                except sqlite3.IntegrityError as exc:
                    last_error = exc
                    await db.rollback()
        if last_error is not None:
            raise last_error

    async def get_operator_job(self, job_id: str) -> dict[str, Any] | None:
        async with self._connection() as db:
            cursor = await db.execute("SELECT * FROM operator_jobs WHERE job_id = ?", (job_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            logs_cursor = await db.execute(
                "SELECT * FROM operator_job_logs WHERE job_id = ? ORDER BY seq ASC",
                (job_id,),
            )
            logs = await logs_cursor.fetchall()
        return {
            "job_id": row["job_id"],
            "job_type": row["job_type"],
            "status": row["status"],
            "requested_at_ms": row["requested_at_ms"],
            "started_at_ms": row["started_at_ms"],
            "finished_at_ms": row["finished_at_ms"],
            "request": json.loads(row["request_json"]) if row["request_json"] else {},
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error_text": row["error_text"],
            "logs": [
                {
                    "seq": log["seq"],
                    "time_ms": log["time_ms"],
                    "level": log["level"],
                    "message": log["message"],
                    "payload": json.loads(log["payload_json"]) if log["payload_json"] else {},
                }
                for log in logs
            ],
        }

    async def list_operator_jobs(self) -> list[dict[str, Any]]:
        async with self._connection() as db:
            cursor = await db.execute("SELECT * FROM operator_jobs ORDER BY requested_at_ms DESC, job_id DESC")
            rows = await cursor.fetchall()
        return [
            {
                "job_id": row["job_id"],
                "job_type": row["job_type"],
                "status": row["status"],
                "requested_at_ms": row["requested_at_ms"],
                "started_at_ms": row["started_at_ms"],
                "finished_at_ms": row["finished_at_ms"],
                "request": json.loads(row["request_json"]) if row["request_json"] else {},
                "result": json.loads(row["result_json"]) if row["result_json"] else None,
                "error_text": row["error_text"],
            }
            for row in rows
        ]

    async def list_operator_feed(
        self,
        *,
        after_id: str | None = None,
        limit: int = 50,
        include_health_events: bool = True,
        include_execution_metrics: bool = True,
    ) -> dict[str, Any]:
        query_limit = max(limit * 4, limit)
        async with self._connection() as db:
            trade_events_cursor = await db.execute(
                "SELECT event_id, symbol, event_type, event_time_ms, payload_json FROM trade_events ORDER BY event_time_ms DESC, event_id DESC LIMIT ?",
                (query_limit,),
            )
            trade_events = await trade_events_cursor.fetchall()
            tickets_cursor = await db.execute(
                "SELECT ticket_id, symbol, action_type, decision_time_ms, readable_summary, features_json, rationale_json FROM action_tickets ORDER BY decision_time_ms DESC, ticket_id DESC LIMIT ?",
                (query_limit,),
            )
            tickets = await tickets_cursor.fetchall()
            packets_cursor = await db.execute(
                "SELECT signal_id, symbol, decision_time_ms, packet_json FROM decision_packets ORDER BY decision_time_ms DESC, signal_id DESC LIMIT ?",
                (query_limit,),
            )
            packets = await packets_cursor.fetchall()
            commands_cursor = await db.execute(
                "SELECT command_id, command_type, requested_at_ms, request_json, result_json, success FROM operator_commands ORDER BY requested_at_ms DESC, command_id DESC LIMIT ?",
                (query_limit,),
            )
            commands = await commands_cursor.fetchall()
            jobs_cursor = await db.execute(
                "SELECT job_id, job_type, status, requested_at_ms, started_at_ms, finished_at_ms, request_json, result_json, error_text FROM operator_jobs ORDER BY requested_at_ms DESC, job_id DESC LIMIT ?",
                (query_limit,),
            )
            jobs = await jobs_cursor.fetchall()
            health_cursor = await db.execute(
                "SELECT * FROM health_events ORDER BY event_time_ms DESC, event_id DESC LIMIT ?",
                (query_limit,),
            )
            health_events = await health_cursor.fetchall()
            supervision_cursor = await db.execute(
                "SELECT * FROM supervision_snapshots ORDER BY time_ms DESC, snapshot_id DESC LIMIT ?",
                (query_limit,),
            )
            supervision_snapshots = await supervision_cursor.fetchall()
            metrics_cursor = await db.execute(
                "SELECT * FROM execution_metrics ORDER BY recorded_time_ms DESC, metric_id DESC LIMIT ?",
                (query_limit,),
            )
            execution_metrics = await metrics_cursor.fetchall()

        entries: list[dict[str, Any]] = []
        for row in trade_events:
            sort_id = f"{int(row['event_time_ms']):013d}:trade:{row['event_id']}"
            entries.append(
                {
                    "id": sort_id,
                    "time_ms": row["event_time_ms"],
                    "kind": "trade_event",
                    "summary": row["event_type"],
                    "symbol": row["symbol"],
                    "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
                }
            )
        for row in tickets:
            sort_id = f"{int(row['decision_time_ms']):013d}:ticket:{row['ticket_id']}"
            entries.append(
                {
                    "id": sort_id,
                    "time_ms": row["decision_time_ms"],
                    "kind": "action_ticket",
                    "summary": row["readable_summary"],
                    "symbol": row["symbol"],
                    "payload": {
                        "action_type": row["action_type"],
                        "features": json.loads(row["features_json"]) if row["features_json"] else {},
                        "rationale": json.loads(row["rationale_json"]) if row["rationale_json"] else {},
                    },
                }
            )
        for row in packets:
            sort_id = f"{int(row['decision_time_ms']):013d}:packet:{row['signal_id']}"
            packet_payload = json.loads(row["packet_json"]) if row["packet_json"] else {}
            entries.append(
                {
                    "id": sort_id,
                    "time_ms": row["decision_time_ms"],
                    "kind": "decision_packet",
                    "summary": packet_payload.get("action", "decision_packet"),
                    "symbol": row["symbol"],
                    "payload": packet_payload,
                }
            )
        for row in commands:
            sort_id = f"{int(row['requested_at_ms']):013d}:command:{row['command_id']}"
            request_payload = json.loads(row["request_json"]) if row["request_json"] else {}
            result_payload = json.loads(row["result_json"]) if row["result_json"] else None
            entries.append(
                {
                    "id": sort_id,
                    "time_ms": row["requested_at_ms"],
                    "kind": "operator_command",
                    "summary": row["command_type"],
                    "symbol": _operator_payload_symbol(request_payload, result_payload, default="BTCUSDT"),
                    "payload": {
                        "request": request_payload,
                        "result": result_payload,
                        "success": None if row["success"] is None else bool(row["success"]),
                    },
                }
            )
        for row in jobs:
            sort_id = f"{int(row['requested_at_ms']):013d}:job:{row['job_id']}"
            request_payload = json.loads(row["request_json"]) if row["request_json"] else {}
            result_payload = json.loads(row["result_json"]) if row["result_json"] else None
            entries.append(
                {
                    "id": sort_id,
                    "time_ms": row["requested_at_ms"],
                    "kind": "operator_job",
                    "summary": f"{row['job_type']}:{row['status']}",
                    "symbol": _operator_payload_symbol(request_payload, result_payload),
                    "payload": {
                        "job_type": row["job_type"],
                        "status": row["status"],
                        "started_at_ms": row["started_at_ms"],
                        "finished_at_ms": row["finished_at_ms"],
                        "request": request_payload,
                        "result": result_payload,
                        "error_text": row["error_text"],
                    },
                }
            )
        if include_health_events:
            for row in health_events:
                sort_id = f"{int(row['event_time_ms']):013d}:health:{row['event_id']}"
                entries.append(
                    {
                        "id": sort_id,
                        "time_ms": row["event_time_ms"],
                        "kind": "health_event",
                        "summary": row["summary"],
                        "symbol": row["symbol"],
                        "reason_code": row["reason_code"],
                        "payload": {
                            "scope": row["scope"],
                            "state": row["state"],
                            "reason_code": row["reason_code"],
                            "recommended_action": row["recommended_action"],
                            "details": json.loads(row["payload_json"]) if row["payload_json"] else {},
                        },
                    }
                )
        for row in supervision_snapshots:
            sort_id = f"{int(row['time_ms']):013d}:supervision:{row['snapshot_id']}"
            payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
            entries.append(
                {
                    "id": sort_id,
                    "time_ms": row["time_ms"],
                    "kind": "supervision_snapshot",
                    "summary": payload.get("summary", "supervision_snapshot"),
                    "symbol": row["symbol"],
                    "reason_code": payload.get("candidate_exit_reason"),
                    "payload": payload,
                }
            )
        if include_execution_metrics:
            for row in execution_metrics:
                sort_id = f"{int(row['recorded_time_ms']):013d}:metric:{row['metric_id']}"
                payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
                entries.append(
                    {
                        "id": sort_id,
                        "time_ms": row["recorded_time_ms"],
                        "kind": "execution_metric",
                        "summary": row["metric_type"],
                        "symbol": row["symbol"],
                        "reason_code": payload.get("rejection_reason") or payload.get("exit_reason"),
                        "payload": {
                            "metric_type": row["metric_type"],
                            **payload,
                        },
                    }
                )

        entries.sort(key=lambda item: item["id"], reverse=True)
        if after_id is not None:
            entries = [entry for entry in entries if entry["id"] > after_id]
        limited = entries[:limit]
        return {
            "items": limited,
            "next_cursor": limited[0]["id"] if limited else after_id,
        }
