# V2 No-Touch Paths

Status: initial Phase 0 registry
Audit ID: `V2-AUD-SEC-001`
Source: `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

No-touch means a path cannot be changed accidentally or as a side effect of a
broader v2 packet. It does not mean the path can never change. A future packet
may touch a no-touch path only when that packet names the path explicitly,
states the risk, explains why the change is necessary, and adds focused
validation.

## Registry

| Category | Path examples | Reason |
| --- | --- | --- |
| Live runtime | `src/**/live/**`, `src/**/runtime.py`, `run_live_smoke.py`, `run_manual.py` | V2 research work must not mutate execution behavior. |
| Order placement | `src/**/*order*place*/**`, `src/**/*broker*/**`, execution adapters, exchange submit helpers | Order placement is outside v2 research scope and high risk. |
| Sizing/runtime config | runtime config paths, account sizing helpers, position sizing runtime code | V2 must not emit sizing instructions or runtime-mode changes. |
| Candidate-pack truth layer | `src/tradingbotsuite/research_artifacts/candidate_pack.py`, candidate-pack validators, generated candidate-pack paths | Candidate-pack behavior requires explicit validation scope. |
| Promotion/shadow | `src/tradingbotsuite/promotion/**`, `src/tradingbotsuite/live/shadow_loader.py` | Promotion and shadow loading are not v2 research implementation targets. |
| Old evidence artifacts | committed `data/research/fixtures/**`, committed `data/research/historical_cycles/**`, legacy run artifacts | Preserve audit history and avoid evidence rewrites. |
| Legacy high-return/rejected outputs | `data/research/wpr106_*/**`, `data/research/v2-btc-*/**`, historical discovery/operator outputs | Preserve as Lead Book or negative-control sources only; do not rewrite during v2 migration. |
| Legacy GUI | existing operator UI/web paths unless a packet is explicitly a UI audit or delayed v2 UI packet | Legacy GUI is frozen/drawer until the v2 foundation exists. |
| Old `tradingbot` package | `src/tradingbot/**` | Legacy-visible compatibility package, not v2 core. |
| Secrets and local state | `.env`, credential files, local SQLite operator DBs, unreviewed `outputs/**`, private cache paths | Avoid credential leaks and non-reproducible state. |

## Default Review Rule

Before changing a no-touch path, the packet must include:

- exact path list;
- reason the change cannot be avoided;
- rollback plan;
- focused tests;
- boundary validation proving no live, paper, order, sizing, runtime-mode, or
  promotion behavior was introduced;
- statement that old evidence was not rewritten, or manifest/hash evidence when
  an explicitly scoped rewrite is required.

## V2 Packet Checklist

Every v2 packet must answer:

1. Does it touch a no-touch path?
2. Does it import live/order/runtime code?
3. Does it write or rewrite generated evidence?
4. Does it create candidate-pack, paper/live, sizing, order, or promotion
   implications?
5. Does it keep BTC/ETH as fixture/reference instruments rather than full
   product scope?
6. Does it preserve the research-only invariant in `docs/PRODUCT_SCOPE.md`?
