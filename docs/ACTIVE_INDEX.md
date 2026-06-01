# Active Index

Last updated: 2026-06-01

This is the first file to read after `AGENTS.md`.

## Canonical Identity

ResearchEngineDeluxe is a research-only evidence system for BTC/ETH perpetual
futures. It may produce reproducible research evidence, rejection reports, and
candidate-readiness diagnostics. It does not produce live signals, paper
signals, order-placement instructions, sizing instructions, or promotion
authorization.

The Python package name remains `tradingbotsuite` for compatibility. Treat that
as an implementation detail unless a future package-rename packet scopes a
rename.

## Current Checkout

- Local checkout: `codex/wpr106-47-full-replay-exit-lab-controls`.
- Stage role: migrated mirror of `research/v3-experimental-engine`.
- Live runtime branch referenced by older docs: `live/v1-runtime-hardening`.
- Current git state at WPR106-32 open: `.pytest_cache/v/cache/nodeids` was
  already dirty and is unrelated.

If older documents say the current branch is `research/v3-experimental-engine`,
prefer this index plus WPR106-21 and later R106 reports for local checkout
facts.

## Active Stage

- Current stage: Stage R106 centralized historical data catalog.
- Current stage owner: Codex Research Agent.
- Latest WPR106-53 operator UI logic reliability audit packet:
  `docs/work_packets/WPR106-53-operator-ui-logic-reliability-audit.md`.
- Latest WPR106-53 operator UI logic reliability audit report:
  `docs/stage_reports/STAGE_R106_OPERATOR_UI_LOGIC_RELIABILITY_AUDIT_REPORT.md`.
- Previous WPR106-52 GitHub CLI/UI connector review and optimization packet:
  `docs/work_packets/WPR106-52-github-cli-ui-connector-review-and-optimization.md`.
- Previous WPR106-52 connector review report:
  `docs/stage_reports/STAGE_R106_GITHUB_CLI_UI_CONNECTOR_REVIEW_AND_OPTIMIZATION_REPORT.md`.
- Latest WPR106-51 complete review hardening and publish packet:
  `docs/work_packets/WPR106-51-complete-review-hardening-and-publish.md`.
- Latest WPR106-50 full-codebase validation/performance audit packet:
  `docs/work_packets/WPR106-50-full-codebase-validation-and-performance-audit.md`.
- Latest WPR106-49 replay-scope validation manifest refresh packet:
  `docs/work_packets/WPR106-49-replay-scope-validation-manifests-and-eligibility-refresh.md`.
- Latest WPR106-48 first-class negative-control hardening packet:
  `docs/work_packets/WPR106-48-first-class-negative-controls-modern-window-and-hardening.md`.
- Latest WPR106-47 replay exit-lab/control audit packet:
  `docs/work_packets/WPR106-47-full-replay-exit-lab-and-negative-controls.md`.
- Latest closed exact replay overlay domain/cycle implementation packet:
  `docs/work_packets/WPR106-46-exact-replay-overlay-domain-and-cycle.md`.
- Latest closed reusable replay preflight contract packet:
  `docs/work_packets/WPR106-45-replay-overlay-preflight-contract.md`.
- Latest closed empirical preflight packet:
  `docs/work_packets/WPR106-44-replay-overlay-cycle-spec-preflight.md`.
- Latest closed compatibility packet:
  `docs/work_packets/WPR106-43-discovery-replay-spec-schema-compatibility.md`.
- Latest closed overlay infrastructure packet:
  `docs/work_packets/WPR106-42-candidate-scoped-replay-overlay-cycle-gates.md`.
- Latest closed empirical replay packet:
  `docs/work_packets/WPR106-31-discovery-lead-replay-entry-evidence.md`.
- Latest replay evidence report:
  `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_REPLAY_ENTRY_EVIDENCE_REPORT.md`.

WPR106-31 produced real replayed KNN/strategy-accounting artifacts and
annotated entry-signal evidence for 24 BTC and 24 ETH materialized discovery
leads. It also recorded bounded top-3 frozen-entry exit-lab slices blocked by
no improvement over fixed holding. This is evidence, not candidate readiness.
WPR106-47 verified the local full 24-lead-per-symbol frozen-entry exit-lab
artifacts and added a separate audit manifest for full-window, modern-window,
negative-control, and eligibility status without candidate-ready claims.
WPR106-48 adds first-class negative-control artifacts for shuffled labels,
shifted context, no-KNN overlay, and no-regime backend controls. All 192
control rows remain blocked because replay profile provenance, validation
manifest evidence, and modern-window evidence are missing, but the controls are
now structurally labeled `artifact_family: negative_control`,
`control_only: true`, and `candidate_evidence: false`.
WPR106-49 materializes replay-scope multiple-testing and validation-floor
manifests for all 48 WPR106-31 replay leads and refreshes BTC/ETH eligibility
audits. Missing-manifest blockers are removed for this evidence scope, but all
48 rows remain blocked and no candidate pack is written.
WPR106-50 runs broad compile, full-suite, grouped, benchmark-focused, and CLI
performance validation. It fixes a checked-config relative path bug in the
research-experiment benchmark command and removes repeated legacy pandas
FutureWarnings without changing candidate gates or runtime behavior.
WPR106-51 performs the final broad review, validation, and publish hardening
pass over the inherited WPR106-48 through WPR106-50 worktree. It confirms
compile, contracts, full-suite, focused touched-path validation, and diff
hygiene; hardens replay provenance, negative-control row validation,
candidate-pack runtime-mode-change rejection, benchmark nested path
resolution, and Lorentzian warning cleanup; tightens the known-issue template
so naive counters do not report a fake open template issue; and preserves zero
eligible candidates with no candidate pack, live, paper, order-placement,
sizing, runtime, or promotion claim.
WPR106-52 installs GitHub CLI 2.93.0, confirms local `gh` is available but not
authenticated, records the desktop GitHub connector MCP startup timeout as an
external connector limitation, and hardens UI/research connector paths. The
standalone research UI mutating API now requires a configured operator secret
token and rejects cross-origin writes; generic non-promotable manifests are
shown as research boundary review rather than promotion candidates; operator
artifact indexing skips `trials/`; provider pipeline, research experiment, and
historical-cycle output dirs fail closed outside the configured research output
root; data-pipeline stage paths prefer the owning spec directory over launch
CWD; and negative-control availability blocks no-effect shuffled-label and
weak shifted-context evidence. Final validation reports 1552 passed, 1 skipped,
and 2 warnings. No candidate pack, live/paper/order/sizing/runtime/promotion
behavior is introduced.
WPR106-53 performs the follow-up operator UI logic reliability audit. It
hardens logout CSRF handling, mutating JSON-route validation, worker-time
research/live-boundary checks, public health redaction, artifact scan
offloading, command debouncing, visible browser error states, symbol-scoped
research evidence selection, backend-owned BTC/ETH evidence bundle sequencing,
and standalone boundary-review links/scan bounds. Final validation reports
1561 passed, 1 skipped, and 1 XGBoost environment warning. No candidate pack,
live/paper/order/sizing/runtime authorization, or promotion behavior is
introduced.

## Current Gate State

No candidate-ready trading claim exists. No candidate pack should be written
from current evidence. Zero eligible candidates remains a valid research
outcome.

Open P0 blockers stop stage advancement and empirical expansion until
resolved. Current open P0 count: 0.

Resolved P0 blockers in the active-index wave:

- `ISSUE-R106-008`: active index and ResearchEngineDeluxe identity were
  missing.
- `ISSUE-R106-009`: CI/reproducible install checks were missing.
- `ISSUE-R106-010`: synthetic fallback and source selection were not explicit
  enough.
- `ISSUE-R106-011`: generic purge was fixed-bar based rather than
  label/event-end aware.
- `ISSUE-R106-012`: lower-timeframe entry pricing was labeled but not used.
- `ISSUE-R106-013`: local credential files could imply Hyperliquid
  live/testnet enablement without an explicit env flag.
- `ISSUE-R106-014`: live artifact validation was not fail-closed for unknown
  or mode-ambiguous manifests.

Open P1 blocker:

- `ISSUE-R104-001`: candidate-ready empirical evidence remains blocked until
  durable candidate-depth data, deep cycles, exact sweeps, and eligibility
  review complete.

See `docs/KNOWN_ISSUES.md` for the blocking source of truth.

## Required Read Order

1. `AGENTS.md`
2. `docs/ACTIVE_INDEX.md`
3. `docs/ORCHESTRATOR_STAGE_LEDGER.md`
4. `docs/KNOWN_ISSUES.md`
5. `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
6. Latest relevant `docs/stage_reports/STAGE_R106_*.md`
7. Relevant source and tests for the scoped packet

## Near-Term Work Order

Do not add new strategies, filters, models, paper/live behavior, or promotion
logic that weakens the closed P0 safety boundaries. With the active P0 blockers
closed and candidate-scoped overlay routing in place, WPR106-44 proved exact
WPR106-31 replay leads are not representable by the then-current
historical-cycle candidate contract. WPR106-45 turns that preflight into a
reusable research-only contract and reruns it against WPR106-31 artifacts,
again finding 48/48 replay leads unrepresentable with no overlay specs or
candidate packs emitted. WPR106-46 implements the Option A lane: exact replay
lead domains and `1h` KNN overlay horizons now have explicit tested support,
generated singleton overlay specs exist for all 48 WPR106-31 replay leads, and
bounded BTC/ETH smoke cycles prove candidate-scoped overlay provenance reaches
rankings, backtest index, and gate reports. Candidate packs remain blocked
because existing gates do not pass. Do not silently substitute current defaults
for replayed values. WPR106-47 then audits the existing full frozen-entry
exit-lab evidence for all 48 replay leads, records full-window evidence
separately from missing modern-window profiles, emits fail-closed
negative-control rows for missing shuffled-label/shifted-context/no-KNN/no-
regime artifacts, and runs eligibility review with zero eligible rows.
WPR106-48 turns those control rows into first-class fail-closed artifacts,
hardens candidate-pack bridge and pack validation against negative-control
inputs, and normalizes old replay-ledger compatibility columns at read time
without rewriting generated WPR106-31 evidence. WPR106-49 then materializes
the replay-scope multiple-testing and validation-floor manifests that WPR106-48
left missing, refreshes eligibility, removes the missing-manifest blockers, and
still confirms zero eligible rows and no candidate packs.

Broader research queue:

- Generate first-class modern-window replay artifacts instead of relabeling
  full-window evidence.
- Replace the WPR106-48 fail-closed first-class control blockers with real
  replay profile provenance, validation manifests, modern-window evidence, and
  source label/timestamp inputs before treating controls as available.
- Add passing replay validation evidence only through real evidence: current
  WPR106-49 multiple-testing and validation-floor manifests are materialized
  but blocked, so later expansion still needs split/window concentration,
  source capability, baseline, ablation, exit-lab, and full cycle-ranking
  evidence.
- Keep `ISSUE-R104-001` open until durable candidate-depth data, deep cycles,
  exact sweeps, and eligibility review prove closure.
- Keep approximate-current-domain overlays separate and explicitly labeled; they
  cannot claim exact WPR106-31 replay evidence.
- Keep live/paper runtime behavior, order placement, sizing, venue execution
  proof, and promotion handoff out of research packets unless a later ledger
  explicitly scopes them.

WPR106-39 also normalizes active discovery regime backend evidence:
GMM-backed regime/KNN outputs now carry explicit
`regime_model_backend: sklearn.mixture.GaussianMixture`, no-regime outputs
carry `regime_model_backend: none`, and `true_hmm_backend_used` remains false.
Legacy `hmm_*` field names remain compatibility fields only.

WPR106-40 adds venue-aware cost/fill profile metadata to research backtests and
historical-cycle cost-stress rows. The required cost-stress scenario set remains
intact, and Binance USDM historical cost evidence is explicitly
`historical_research_only_not_live_execution_proof`, not Hyperliquid execution
proof.

WPR106-41 adds parser-level schema guards and roundtrip validation for active
historical-cycle and discovery-run specs. Wrong `spec_version` values and
unknown active nested fields now fail closed, while known documentary metadata
in historical-cycle configs remains accepted.

WPR106-42 adds candidate-scoped materialized prediction overlay routing to the
historical-cycle runner. WPR106-31 replayed KNN prediction artifacts can now be
mapped to generated historical-cycle candidate IDs without applying one
candidate's prediction frame globally to every candidate in the feature set.
Overlay provenance is recorded in rankings, backtest index, and gate reports.
This is infrastructure only; no replay-overlay cycle outputs or candidate packs
were generated by WPR106-42.

WPR106-43 restores discovery lead replay spec compatibility after the schema
guard hardening. `discovery-lead-replay-spec-v1` is an accepted discovery-run
specialization again, `replay_metadata` is recognized, and arbitrary wrong
discovery `spec_version` values still fail closed.

WPR106-44 preflighted all 48 WPR106-31 replay leads for exact
candidate-scoped historical-cycle overlay execution. All prediction artifacts
and KNN manifests exist, but zero leads are exactly representable by the current
historical-cycle `hmm_knn_local_analog_filter_v2` candidate contract because
the replay leads use `1h` label horizons, `event_spacing_bars: 4`, and multiple
threshold values outside the current strategy metadata domain. No overlay cycle
specs or candidate packs were emitted; zero representable exact replay
candidates is valid evidence.

WPR106-45 codifies that exact replay-overlay preflight as reusable source and
tests. The reusable preflight checks strategy plugin holding-window support,
current strategy parameter domains, KNN prediction/manifest existence, manifest
research-boundary flags, split-safety status, prediction path match, and
prediction SHA match before any overlay spec can be trusted. A fresh BTC/ETH
rerun from the reusable utility again checked 48 replay leads, found all 48
prediction artifacts and KNN manifests, found 0 exact representable candidates,
and emitted no overlay specs or candidate packs.

WPR106-46 implements the Option A exact replay-overlay domain and cycle lane.
All 48 WPR106-31 replay leads are now representable by explicit `1h`
historical-cycle strategy-domain support, 48 singleton overlay specs were
generated locally, and bounded BTC/ETH smoke cycles produced rankings,
backtest-index rows, gate reports, and rejection reports with candidate-scoped
overlay provenance. No candidate pack was emitted, and `ISSUE-R104-001`
remains open.

WPR106-47 adds the full replay exit-lab and negative-control audit packet. The
packet verifies 48 existing full frozen-entry exit-lab rows, all blocked by no
simple-runner improvement over fixed holding; records two full-window scope rows
available and two modern-window scope rows blocked by missing local modern
profiles; records 192 blocked control rows for missing shuffled-label,
shifted-context, no-KNN, and no-regime control artifacts; and runs BTC/ETH
eligibility bridge audits with 48 blocked rows, zero eligible candidates, and
no candidate packs.

WPR106-49 materializes replay-scope multiple-testing and validation-floor gate
artifacts for the 24 BTC and 24 ETH WPR106-31 replay leads, then refreshes
eligibility with those manifests wired in. Both symbols have 24 blocked
multiple-testing rows, 24 diagnostic validation-floor rows, 24 blocked
eligibility rows, zero eligible rows, and zero missing-manifest blockers. No
candidate pack was emitted.

WPR106-50 performs the full-codebase validation and diagnostic performance
audit. Final validation after fixes reports 1539 passed, 1 skipped, 1 warning;
`pip check` passes; grouped high-risk, benchmark/vector/GPU, integration,
top-level legacy, experiment-runner, and strategy-flow suites pass. CLI
benchmarks pass for historical medium repeat 2, discovery deep repeat 2,
hardware utilization, and the Phase 1 research-experiment benchmark. The
provider latest-month benchmark completes as report-only evidence because
repeat 1 lacks determinism/cache-reuse evidence.

WPR106-51 performs a final complete-review hardening and publish pass. Broad
validation remains green at 1544 passed, 1 skipped, and 1 XGBoost environment
warning; focused touched-path validation passes; retry-agent findings in
replay provenance, negative-control row trust, runtime-mode-change filtering,
benchmark nested path resolution, and Lorentzian warning cleanup are fixed;
the known-issue template no longer resembles a real open issue to naive
counters; `.pytest_cache` and root-level handoff prompts remain unstaged; no
candidate pack or live/paper/promotion behavior is introduced.
WPR106-52 follows with a connector/review/optimization hardening pass. GitHub
CLI is installed but unauthenticated, the desktop GitHub connector still times
out externally, UI/research write surfaces and output-root boundaries are
hardened, negative controls reject no-effect evidence, and the final full suite
passes at 1552 passed, 1 skipped, 2 warnings.
WPR106-53 follows with an operator UI logic reliability audit. It fixes
CSRF/JSON validation, redacts unauthenticated health details, rechecks
research-job live boundaries at worker time, makes command and refresh failure
states visible, symbol-scopes research evidence actions, routes the evidence
bundle through backend autopilot, and keeps standalone research UI scans and
boundary-review labels bounded and current. The final full suite passes at
1561 passed, 1 skipped, 1 warning.

## Non-Negotiable Research Boundary

- Research outputs are not live signals.
- Candidate gates must not be weakened.
- Zero eligible candidates is valid evidence.
- Synthetic data must be explicit and demo/test-only.
- Binance historical evidence is not Hyperliquid execution proof.
- Cost/fill profile metadata is research evidence only unless a later approved
  packet adds separate venue execution proof.
- Research/discovery config schemas must fail closed on misspelled active
  parser fields.
- GMM-backed regime logic must carry the true backend
  (`sklearn.mixture.GaussianMixture`) and must not be treated as true HMM
  evidence.
- Runtime, paper, live, order placement, live configuration, and promotion logic
  are out of scope for research packets unless a later ledger explicitly scopes
  them.

## Validation Baseline

Use focused validation for scoped work and broaden when shared contracts change:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

The checked-in CI baseline is `.github/workflows/research-validation.yml`. It
installs `.[dev]`, runs `pip check`, compiles `src/tradingbotsuite`, runs
contract tests, and runs focused live/artifact boundary tests. Optional
research, Crypto Lake, and GPU extras remain outside the baseline.
