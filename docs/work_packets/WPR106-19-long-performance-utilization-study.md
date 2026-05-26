# WPR106-19 Long Performance Utilization Study

Status: closed

## Scope

Run a second, longer performance and utilization study for the R106 research
workflow, focused on identifying why some phases saturate hardware and others
do not, and on producing safe speedup recommendations for large runtime
segments.

This packet is measurement-first. Code changes are allowed only if the study
finds a narrow, low-risk runtime issue with focused validation.

## Allowed paths

- `docs/work_packets/WPR106-19-long-performance-utilization-study.md`
- `docs/stage_reports/STAGE_R106_LONG_PERFORMANCE_UTILIZATION_STUDY_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `data/research/operator_runs/performance_utilization_wpr106_19/**`
- `src/tradingbotsuite/**`
- `tests/**`

## Constraints

- Preserve `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not place orders, change live runtime mode, write live configuration, or
  import live order-placement adapters into research code.
- Do not claim candidate-ready trading performance from benchmark artifacts.
- Prefer existing benchmark surfaces before adding new instrumentation.
- Keep any code edits targeted to measured runtime issues and validate them.

## Acceptance

- Record the UI one-line launch command.
- Run long-lived hardware utilization and research runtime benchmarks.
- Identify high-utilization and low-utilization phases with likely causes.
- Produce actionable, safe speedup recommendations for the largest runtime
  components.
- Record validation and residual risks in a stage report.

## Exit summary

- Recorded the one-line PowerShell UI command:
  `$env:TBS_OPERATOR_UI_ENABLED='true'; $env:TBS_OPERATOR_UI_SECRET='operator-secret'; $env:TBS_BINANCE_MARKET_STREAMS_ENABLED='false'; tradingbotsuite serve --host 127.0.0.1 --port 8000`.
- Ran hardware saturation probes at 8 and 16 CPU workers with 45-second GPU
  matrix probes. The 16-worker probe saturated logical CPU capacity better
  (`87.88%`) than the 8-worker probe (`49.53%`) and raised CPU probe throughput
  from about `34.95M` to `53.07M` operations per second.
- Ran the provider latest-month historical-cycle benchmark with two repeats.
  The benchmark passed, averaged `24.73s` per repeat, and recorded measurable
  feature-cache reuse.
- Ran the discovery deep repeat-5 benchmark. It passed as a run-manager,
  resume, snapshot, and artifact-overhead guardrail.
- Ran an isolated bounded BTC candidate-depth exact-discovery probe against the
  active catalog fixture. The probe used `221952` primary rows and took
  `1033.65s` for 16 trials, with `105.95s` in context preparation and
  `927.50s` in trial execution.
- Parsed results into
  `data/research/operator_runs/performance_utilization_wpr106_19/measurement_summary.json`
  and recorded recommendations in
  `docs/stage_reports/STAGE_R106_LONG_PERFORMANCE_UTILIZATION_STUDY_REPORT.md`.
- No runtime source code was changed. The evidence points to exact-discovery
  KNN/materialization, process-child telemetry gaps, and final artifact
  rebuild/I/O as the next safe optimization targets rather than a narrow code
  patch in this packet.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `427 passed`
