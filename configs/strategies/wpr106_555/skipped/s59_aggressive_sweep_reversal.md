# S59 aggressive sweep reversal skip note

Status: skipped for the WPR106-555 autonomous-readiness strategy set.

Reason:

- S59 requires event-level aggressive sweep detection, stall confirmation,
  depth replenishment, spread/depth checks, and queue/fill assumptions.
- WPR106-552 proves that compact order-flow, BBO, and L2-depth feature rows can
  be materialized from collected Binance USD-M files, but the current bounded
  vectorized cycle does not yet consume those feature rows as an event-driven
  replay surface.
- Substituting 1h candles for sweep/replenishment event state would not test
  S59.

Resolution path:

- Build a scoped event-driven replay packet that consumes collected or
  materialized `trades`, `aggTrades`, `bookTicker`, and `bookDepth` features,
  documents deterministic sweep/replenishment rules, and records queue/fill
  assumptions.
- Until then, S59 is excluded from the readiness strategy set under the
  operator policy that untestable strategies are skipped with evidence.
