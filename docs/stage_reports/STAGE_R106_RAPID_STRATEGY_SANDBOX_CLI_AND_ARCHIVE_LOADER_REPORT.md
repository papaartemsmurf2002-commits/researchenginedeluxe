# Stage R106 Rapid Strategy Sandbox CLI And Archive Loader Report

Date: 2026-06-18
Packet: WPR106-229
Status: closed

## Scope

WPR106-229 makes the WPR106-228 sandbox foundation runnable from the canonical
CLI using local strategy catalogs, venue archive descriptors, and 2024+ local
market data files. The packet stays sandbox-only and does not add operator UI,
network downloads, strict-cycle rewrites, candidate-pack writes, live/paper
signals, sizing, order placement, runtime-mode changes, or promotion behavior.

## Steps Completed

1. Opened
   `docs/work_packets/WPR106-229-rapid-strategy-sandbox-cli-and-archive-loader.md`
   before source edits.
2. Extended `VenueArchiveDescriptor` with optional `data_path`.
3. Added sandbox market-frame loading for local CSV, TSV, JSON, JSONL, Parquet,
   direct Binance Vision kline CSV, and Binance Vision kline ZIP files.
4. Added sandbox run-spec JSON parsing, including support for the
   `run_template` shape used by the sandbox config template.
5. Added CLI command `run-rapid-strategy-sandbox` to `src/tradingbotsuite/main.py`.
   The command:
   - loads a sandbox run spec;
   - loads a strategy catalog;
   - loads venue archive descriptors;
   - loads a local market frame from `--market-data` or a single descriptor
     `data_path`;
   - resolves output under the configured research output root;
   - runs the vectorized sandbox sweep;
   - prints JSON artifact paths and counts.
6. Registered `run-rapid-strategy-sandbox` in the research command registry and
   boundary contract so live-mode preflight rejects it.
7. Added focused tests for normalized market CSV, Binance Vision CSV/ZIP,
   descriptor `data_path`, run-spec parsing, end-to-end CLI artifact writing,
   and output-root rejection.

## Validation

Commands run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Sandbox focused tests: 13 passed.
- CLI boundary tests: 8 passed.
- Import-boundary tests: 11 passed.
- Package compile: passed.
- Contracts baseline: 461 passed.

The first full contracts run hit a transient Windows socket/event-loop setup
error (`WinError 10055`) in a pytest-asyncio fixture before the test body ran.
The immediate rerun passed.

## Boundary

`run-rapid-strategy-sandbox` is a local research command only. All sandbox
artifacts remain `research_only`, `observe_only`, `promotion_ready: false`,
`sandbox_only`, `candidate_evidence: false`, and
`candidate_pack_eligible: false`. Evidence requests remain descriptors for
later strict validation and are not candidate packs.

## Remaining Work

Remaining objective work includes operator UI wiring, venue-specific manifest
normalization beyond local file loading, richer strategy/exit/filter blueprint
generation, direct ingestion from existing research lead catalogs into sandbox
catalogs, and query/analytics tools over accumulated sandbox Parquet outputs.
