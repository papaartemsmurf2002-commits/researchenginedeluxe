# V2 Decision Register

Status: initial Phase 0 register
Audit ID: `V2-AUD-SCOPE-001`
Source: `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

This register converts the roadmap's CEO decisions into implementation facts.
No agent may silently override these decisions. A conflict must be recorded in
this file or in `docs/audit/V2_AUDIT_INDEX.md` and the affected chunk must
block until resolved.

Each decision status is `accepted` unless a later scoped packet changes it.

| ID | Area | Decision | Required consequence |
| --- | --- | --- | --- |
| D1 | Product identity | V2 canonical direction is approved. | Migrate active docs and defaults away from BTC/ETH-only framing. |
| D2 | Research boundary | Research-only is mandatory. Paper/live is not a future option for this repo. | Remove paper/live roadmap language and test v2 code against order/sizing/live imports. |
| D3 | Migration style | Use strangler migration. | Preserve, inspect, classify, fix, wrap, or migrate useful legacy code; no big-bang rewrite. |
| D4 | Legacy code | Legacy is not automatically obsolete. | Add audit records and classification labels before reuse. |
| D5 | Legacy GUI | Legacy GUI is frozen/drawer material. | Do not prioritize UI early and do not let old GUI define v2 behavior. |
| D6 | Old outputs | Old high-return and rejected outputs may become Lead Book sources or failure evidence. | Preserve old outputs and never silently delete evidence. |
| D7 | Lead Book | Lead Book is the canonical queue for serious ideas. | Implement human inspection status and agent approval status. |
| D8 | Lead evidence | Serious leads need stability, monthly adequacy, trade frequency, and unseen-month checks. | Implement lead gates before deep validation or final hard-test entry. |
| D9 | ROI | Lead Book records observed ROI and ROI projections separately. | Separate observed results from projection assumptions and confidence. |
| D10 | Archive ownership | The repo must own its market data archive. | Backtests read archive snapshots, not direct API pulls. |
| D11 | Archive layers | Archive uses raw, bronze, silver, and gold layers. | Implement four-layer contracts and provenance. |
| D12 | Collection posture | Collect relevant available data aggressively. | Design for candles, trades, funding, contexts, L2/BBO, official files, and compatible venues. |
| D13 | Universe floor | Default floor is USD 5M daily notional. | Evidence universe uses `dayNtlVlm >= 5_000_000`. |
| D14 | Universe mode | Accepted evidence requires as-of universe. | Every accepted backtest manifest states universe mode and survivorship status. |
| D15 | HIP-3/RWA | Include HIP-3/RWA instruments if threshold and metadata gates pass. | Universe manager supports namespaces, reference markets, and caveats. |
| D16 | Date floor | Accepted research evidence starts in 2024 or later. | Backtest data service and ledger append reject pre-2024 accepted evidence. |
| D17 | Data length | Minimum usable history is 6 months; 12 months preferred. | Backtest data service and ledger append validate usable-month counts. |
| D18 | Lockbox | Dynamic latest full-calendar-month lockbox is excluded from ordinary iteration. | Backtest data service rejects lockbox overlap before strategy code runs. |
| D19 | Coverage | Default minimum coverage is 0.98. | Accepted evidence below 98 percent coverage fails closed. |
| D20 | Strategy interface | Declarative specs come first; narrow Python plugins come later. | No arbitrary Python execution by agents. |
| D21 | Backtest engines | Vectorized and event-driven engines are both first-class. | Shared artifact contracts come before engine-specific behavior. |
| D22 | Costs | Conservative cost model is mandatory. | Gross-only results cannot advance; fees/funding/spread/slippage/impact/liquidity stress are required. |
| D23 | Ledger | Append-only ledger is canonical. | XLSX is generated view only and failed trials must be logged. |
| D24 | Deep validation | Deep validation runs one serious lead at a time. | Broad sweeps remain triage; expensive validation is serial. |
| D25 | Final hard test | Final hard-test workflow allows top 3 only. | Enforce max 3 active final hard-test slots. |
| D26 | Workers | Dedicated workers are required. | Collectors and long backtests must not run inside ASGI/operator loop. |
| D27 | Jobs | Durable local job store comes first; queue abstraction later. | No ephemeral collectors or long backtests. |
| D28 | Cross-venue | Hyperliquid remains the primary venue; other venues are comparable sources. | Preserve venue provenance and do not dilute Hyperliquid-first evidence rules. |
| D29 | Audit/security | Chunk-level audit and parallel security hygiene are required. | Add audit markers, no-touch registry, independent review workflow, and boundary tests. |

## Extra Defaults

- V2 command namespace should be `redx` unless integration with the existing
  `tradingbotsuite` CLI is explicitly chosen by a scoped packet.
- Physical archive default is local `data/archive` with path policy and backup
  notes before aggressive collection.
- DuckDB, Polars, and PyArrow are acceptable implementation choices when the
  repo's dependency and contract rules permit them.
- UI replacement is delayed until data, archive, universe, coverage, ledger,
  and Lead Book foundations exist.
- A final hard-test survivor remains research-only and non-promotable.
