# Orchestrator Stage Ledger

Current stage: Stage R106 centralized historical data catalog
Current stage owner: Codex Research Agent
Stage status: in progress - WPR106-01 through WPR106-45 closed. The one-off durable data collection button is replaced by an R106 Historical Data Catalog source of truth. The completed migrated catalog under `refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb` is candidate-depth ready for BTCUSDT and ETHUSDT, with active generated readiness and full-window cycle/exact-discovery specs; this pre-profile local catalog truthfully reports no local modern-window profile artifacts, while later refresh code continues to write/index profiles when produced. Historical-data refresh uses a central verified archive cache, reports progress with ETA, reuses partial downloads and completed per-symbol fixture packs after interruption, tolerates longer Binance Vision DNS/VPN outages through env-tunable retry/backoff, and records Binance aggTrade source-order anomalies without discarding event-time bucketed data. Operator progress now reports active historical-cycle backtest-evaluation completion, rate, and ETA before final cycle manifests exist, and completed refresh journals no longer mask the active compute panel. The completed BTC R106 cycle is accepted as current required evidence. BTC exact discovery is complete at 570240/570240 durable trial records; WPR106-12 repaired final ledger schema normalization and rebuilt stale final ledgers/manifests from immutable trial JSONs. WPR106-13 adds a repeatable research analysis artifact step and next-agent handoff for feature/filter/KNN/exit interpretation; WPR106-14 wires that analysis step into the operator job API, artifact index, progress checklist, and required UI path; WPR106-15 adds a bounded one-button operator autopilot sequencer; WPR106-16 adds run-to-run deltas, bridge-compatible frozen-entry exit-lab artifacts with `simple_runner_v1`, modern-window profile generation/indexing for refreshed catalogs, and extends autopilot/UI sequencing through eligibility; WPR106-17 hardens frozen-entry exit-lab and candidate-eligibility fail-closed behavior and ensures autopilot runs all requested symbol cycle/discovery prerequisites before downstream analysis and eligibility; WPR106-18 adds bounded automatic autopilot step retries and one-time stale-autopilot restart requeueing; WPR106-19 records the second long performance/utilization study and identifies exact-discovery KNN/materialization plus final artifact rebuild/I/O as the largest safe speedup targets; WPR106-20 implements observed artifact accounting, finalization/process timing visibility, placeholder process-context avoidance, and operator UI/API performance wiring; WPR106-21 validates the migrated `main` checkout mirror and opens `ISSUE-R106-003` for active catalog handoff drift; WPR106-22 resolves that P1 by rebasing stale absolute catalog/spec paths to the current mirrored operator-run paths at read/isolation time without rewriting generated artifacts; WPR106-23 catalogs the external BTC/ETH perpetual strategy master report as research knowledge, including the full imported source and a detailed strategy/simulator/falsification knowledge base, without turning it into an implementation queue; WPR106-24 resolves the latest autopilot P1 by rebasing stale absolute discovery-manifest `required_outputs` at read time for operator candidate eligibility and the candidate-pack bridge; WPR106-25 resolves the follow-up autopilot P1 by rebasing stale absolute historical-cycle evidence outputs such as `ablation_report` at read time for operator candidate eligibility and candidate-pack gate evaluation; WPR106-26 runs a full repo mismatch/bug audit and resolves the remaining nested old-root metadata portability gap by rebasing repo-root-relative artifact paths such as `data/...`, `configs/...`, and `repo_root` metadata at read time; WPR106-27 resolves the latest large-run autopilot stall by replacing exhaustive 570240-trial eligibility preflight reads with large-run count/hash/sample auditing and by caching historical-cycle gate membership across discovery candidates; WPR106-28 resolves the operator transparency gap by writing active autopilot helper-step telemetry before each helper runs, surfacing current step/attempt/elapsed/ETA in the UI, and marking stale generated `running` autopilot manifests as `stale_review` when no active-step telemetry has updated recently; WPR106-29 materializes missing multiple-testing and validation-floor gate evidence for BTC/ETH discovery leads, adds explicit candidate-universe overlap/reason-count diagnostics, caps rejection Markdown output, and confirms both symbols have 0 discovery-to-cycle ranking overlap, so zero eligible candidate-pack rows are expected from current evidence; WPR106-30 adds a bounded discovery-lead materialization lane that emits descriptor-only BTC/ETH candidate specs with stable materialized IDs, source trial hashes, entry/prediction signatures, and explicit downstream gate requirements, without writing rankings, packs, or promotion claims. The latest retry completed ETH exact discovery to 570240/570240 trials before the WPR106-24 fix, and the next retry proved WPR106-24 effective by advancing to the now-fixed BTC cycle-evidence handoff failure. The WPR106-26 audit found no remaining P0/P1 repo mismatch after normalization and grouped validation. WPR106-27 proves current BTC eligibility evaluation completes in about 9 seconds from the checkout with `PYTHONPATH=src`, producing 22560 blocked research-only rows and 0 eligible candidates because discovery IDs do not overlap current cycle rankings. WPR106-28 found no active Python/autopilot process at audit time; the newest `running` autopilot manifest was stale generated evidence, not a live 16-hour process. WPR106-29 proves current full BTC/ETH bridge eligibility completes in about 17 seconds total from the checkout with `PYTHONPATH=src`, producing 22560 BTC and 23040 ETH blocked research-only rows with no candidate pack, no promotion-ready claim, and rejection Markdown capped while full Parquet rows are preserved. WPR106-30 materializes 24 descriptor-only leads per symbol from the completed exact-discovery ledgers, with 24 unique entry-event signatures per symbol and all outputs research-only/observe-only/promotion-false. WPR106-31 replays those 24 BTC and 24 ETH materialized descriptors through real discovery KNN/strategy-accounting artifact generation, writes 969870 BTC and 957643 ETH annotated entry signals across 24 candidates per symbol, and records bounded top-3 frozen-entry exit-lab slices that are blocked because simple runner exits do not improve over fixed holding. WPR106-42 adds candidate-scoped historical-cycle overlay routing so those replayed prediction frames can be mapped to generated cycle candidates without global feature-set leakage. WPR106-43 restores discovery lead replay spec compatibility after schema hardening so `discovery-lead-replay-spec-v1` remains an accepted research-only discovery-run specialization. WPR106-44 preflights all 48 replay leads and finds zero exact replay candidates are representable by the current historical-cycle candidate contract, so no overlay cycle specs or candidate packs were emitted. WPR106-45 codifies that exact replay-overlay preflight as reusable code and tests, validates prediction/manifest boundary evidence, reruns BTC/ETH WPR106-31 artifacts, and again finds 48/48 replay leads unrepresentable with no overlay specs or packs emitted. Exact discovery remains resumable from persisted trial records, large resumes no longer hydrate the full trial corpus before useful work, and default real-discovery process concurrency remains performance-first at 8 workers unless a future measured worker-count packet changes it. Next required work is a decision packet: either add explicit tested support for exact replay lead domains and 1h KNN overlay horizons without weakening gates, or run a separately labeled approximate-current-domain overlay experiment that does not claim exact WPR106-31 replay evidence. No candidate-ready trading claim exists until gates pass.
Current WPR106-46 update: WPR106-46 supersedes the prior decision-packet note
in the stage status line and is closed as the Option A exact
replay-overlay domain and bounded cycle-smoke implementation. Exact `1h`
historical-cycle support and replay-domain values now make all 48 WPR106-31
replay leads representable; 48 singleton overlay specs were generated locally;
bounded BTC/ETH smokes prove candidate-scoped overlay provenance reaches
rankings, backtest index, and gate reports. Candidate packs remain blocked,
`ISSUE-R104-001` remains open, and no candidate-ready or promotion-ready claim
exists.
Last updated: 2026-05-31

WPR106-32 active-index update: the current local checkout is `main`, treated as
the migrated R106 research checkout mirror. `docs/ACTIVE_INDEX.md` is now the
active navigation and blocker index. Newly registered P0 validation and
boundary issues (`ISSUE-R106-009` through `ISSUE-R106-014`) block stage
advancement and empirical expansion until resolved. The prior WPR106-31 replay
evidence remains useful research evidence, but no candidate-ready or
promotion-ready claim exists.

WPR106-33 closes `ISSUE-R106-009` by adding
`.github/workflows/research-validation.yml`, a clean Python 3.11 editable
install baseline with `pip check`, compile, contracts, and focused
live/artifact boundary tests. Open P0 blockers remain and still block empirical
expansion.

WPR106-34 closes `ISSUE-R106-010` by parsing explicit synthetic fallback
policy, rejecting no-source auto-synthesis, rejecting ambiguous local fixture
directories, and writing a required source-selection manifest for historical
research cycles. Open P0 blockers remain and still block empirical expansion.

WPR106-35 closes `ISSUE-R106-011` by adding `LabelSpec` and
label/event-end-aware split purge. Discovery labels now stamp event-end times,
train-only split consumers honor explicit event-safe train indices, historical
cycle split manifests record purge-method evidence, and fixed-bar purge remains
only as an identified fallback when no event-end metadata is available. Open P0
blockers remain and still block empirical expansion.

WPR106-36 closes `ISSUE-R106-012` by making
`lower_timeframe_execution_path` use lower-timeframe latency fills in the
reference research simulator. Entry fills now select the first lower-timeframe
open at or after the latency target, record fill proof metadata, and fail
closed when lower-frame coverage is missing. Vector/CUDA accelerated paths
remain unsupported for lower-timeframe entry sources. Open P0 blockers remain
and still block empirical expansion.

WPR106-37 closes `ISSUE-R106-013` by removing credential-file implied
Hyperliquid live/testnet enablement. Local `hyperliquidtestnet.txt` data can
still supply passive testnet endpoint, signer, and account values, but
`enable_live` is now false unless `TBS_HL_ENABLE_LIVE` is explicitly truthy.
Live preflight has a regression proving file-supplied key/account data still
blocks on missing explicit live enablement. Open P0 blockers remain and still
block empirical expansion.

WPR106-38 closes `ISSUE-R106-014` by adding
`validate_artifact_for_runtime_mode()` and routing live preflight plus runtime
artifact dispatch through it before scorer or shadow-loader construction.
Unknown or mode-ambiguous manifests fail closed, live mode now requires explicit
runtime allowance and live-boundary fields, paper runtime artifact loading is
rejected until an explicit later contract exists, and shadow runtime loading is
restricted to explicit shadow promotion candidates that pass the existing
shadow validator. The active P0 blocker count is now zero; empirical expansion
can resume only through the existing research-only gates.

WPR106-39 normalizes active discovery regime backend semantics without changing
model fitting, strategies, or candidate gates. Discovery trial templates, KNN
specs/manifests, ledgers, run manifests, and artifact identity now carry
`regime_model_backend`; GMM-backed evidence is stamped as
`sklearn.mixture.GaussianMixture`, no-regime evidence is stamped as `none`, and
legacy `hmm_*` columns remain compatibility aliases alongside canonical
`regime_*` fields.

WPR106-40 adds venue-aware research cost/fill profile metadata without changing
trade accounting formulas, strategies, candidate gates, or execution modes.
Backtest manifests and cache keys now carry registered cost profile and fill
profile evidence; historical-cycle cost-stress rows expose source venue,
execution venue, evidence scope, and explicit `not_hyperliquid_execution_proof`
metadata while preserving the required 11-scenario stress set and existing
survival gate semantics.

WPR106-41 adds active config schema and roundtrip validation without changing
research behavior, gates, strategies, execution semantics, or runtime modes.
Historical-cycle and discovery-run spec parsers now reject wrong
`spec_version` values and unknown active nested parser fields, expose
versioned schema summaries, and have focused roundtrip tests proving
`from_payload(to_payload())` preserves effective config contracts.

WPR106-42 adds candidate-scoped materialized prediction overlay routing without
changing strategies, candidate gates, execution semantics, runtime modes, live
behavior, or promotion behavior. Historical-cycle specs can now declare
candidate-scoped KNN prediction overlays keyed to generated candidate IDs or
cache keys; the runner builds candidate-specific feature frames for matched
candidates, fails closed on unsafe or unmatched overlays, and records overlay
provenance in rankings, backtest index, and gate reports. No replay-overlay
cycle outputs or candidate packs were generated by this infrastructure packet.

WPR106-43 restores discovery lead replay spec compatibility after the WPR106-41
schema guard. `discovery-lead-replay-spec-v1` is now an accepted discovery-run
specialization again, `replay_metadata` is a known top-level replay field, and
arbitrary wrong discovery `spec_version` values still fail closed. No generated
replay artifacts, discovery behavior, candidate gates, live behavior, or pack
behavior changed.

WPR106-44 preflights all WPR106-31 BTCUSDT/ETHUSDT replay leads for exact
candidate-scoped historical-cycle overlay execution. All 48 prediction Parquets
and KNN manifests exist, but zero leads are exactly representable by the
current historical-cycle `hmm_knn_local_analog_filter_v2` candidate contract
because the replay leads use 1h horizons, 4-bar spacing, and multiple threshold
values outside the current strategy metadata domain. No overlay cycle specs,
candidate packs, or promotion claims were emitted; zero representable exact
replay candidates is valid evidence.

WPR106-45 codifies the WPR106-44 exact replay-overlay preflight as reusable
research-only code and contract tests. The reusable preflight checks strategy
plugin support, current strategy parameter domains, KNN prediction and manifest
existence, manifest research-boundary flags, split safety, prediction path
match, and prediction SHA match before any overlay spec can be trusted. A fresh
BTC/ETH rerun from the reusable utility checked all 48 WPR106-31 replay leads,
found all 48 prediction Parquets and KNN manifests, found 0 exact representable
candidates, and emitted no overlay specs or candidate packs.

WPR106-46 implements the Option A exact replay-overlay domain and bounded
cycle-smoke lane. Exact `1h` support plus explicit replay-domain values make all
48 WPR106-31 replay leads representable, and the replay preflight now emits one
singleton historical-cycle overlay spec per representable lead. Bounded BTC and
ETH singleton cycles prove candidate-scoped overlay provenance through rankings,
backtest index, and gate reports while preserving fail-closed candidate gates:
zero pack-eligible rows and no candidate packs emitted. `ISSUE-R104-001`
remains open.

## Stage entry decision

- Prior stage completed: yes
- Evidence links:
  - `docs/stage_reports/STAGE_R106_EXACT_REPLAY_OVERLAY_DOMAIN_AND_CYCLE_REPORT.md`
  - `docs/work_packets/WPR106-46-exact-replay-overlay-domain-and-cycle.md`
  - `docs/stage_reports/STAGE_R106_REPLAY_OVERLAY_PREFLIGHT_CONTRACT_REPORT.md`
  - `docs/work_packets/WPR106-45-replay-overlay-preflight-contract.md`
  - `docs/stage_reports/STAGE_R106_CONFIG_SCHEMA_ROUNDTRIP_VALIDATION_REPORT.md`
  - `docs/work_packets/WPR106-41-config-schema-roundtrip-validation.md`
  - `docs/stage_reports/STAGE_R106_CANDIDATE_SCOPED_REPLAY_OVERLAY_CYCLE_GATES_REPORT.md`
  - `docs/work_packets/WPR106-42-candidate-scoped-replay-overlay-cycle-gates.md`
  - `docs/stage_reports/STAGE_R106_DISCOVERY_REPLAY_SPEC_SCHEMA_COMPATIBILITY_REPORT.md`
  - `docs/work_packets/WPR106-43-discovery-replay-spec-schema-compatibility.md`
  - `docs/stage_reports/STAGE_R106_REPLAY_OVERLAY_CYCLE_SPEC_PREFLIGHT_REPORT.md`
  - `docs/work_packets/WPR106-44-replay-overlay-cycle-spec-preflight.md`
  - `docs/stage_reports/STAGE_R106_VENUE_AWARE_COST_FILL_PROFILES_REPORT.md`
  - `docs/work_packets/WPR106-40-venue-aware-cost-fill-profiles.md`
  - `docs/stage_reports/STAGE_R106_REGIME_BACKEND_SEMANTICS_REPORT.md`
  - `docs/work_packets/WPR106-39-regime-backend-semantics.md`
  - `docs/stage_reports/STAGE_R106_ACTIVE_INDEX_RESEARCH_IDENTITY_REPORT.md`
  - `docs/work_packets/WPR106-32-active-index-research-identity.md`
  - `docs/stage_reports/STAGE_R106_CI_REPRODUCIBLE_RESEARCH_INSTALL_REPORT.md`
  - `docs/work_packets/WPR106-33-ci-reproducible-research-install.md`
  - `docs/stage_reports/STAGE_R106_FAIL_CLOSED_SYNTHETIC_SOURCE_SELECTION_REPORT.md`
  - `docs/work_packets/WPR106-34-fail-closed-synthetic-source-selection.md`
  - `docs/stage_reports/STAGE_R106_LABEL_EVENT_END_AWARE_PURGE_REPORT.md`
  - `docs/work_packets/WPR106-35-label-event-end-aware-purge.md`
  - `docs/stage_reports/STAGE_R106_LOWER_TIMEFRAME_ENTRY_PRICING_REPORT.md`
  - `docs/work_packets/WPR106-36-lower-timeframe-entry-pricing.md`
  - `docs/stage_reports/STAGE_R106_EXPLICIT_HYPERLIQUID_LIVE_ENABLE_REPORT.md`
  - `docs/work_packets/WPR106-37-explicit-hyperliquid-live-enable.md`
  - `docs/stage_reports/STAGE_R106_MODE_AWARE_ARTIFACT_RUNTIME_VALIDATION_REPORT.md`
  - `docs/work_packets/WPR106-38-mode-aware-artifact-runtime-validation.md`
  - `docs/ACTIVE_INDEX.md`
  - `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_REPLAY_ENTRY_EVIDENCE_REPORT.md`
  - `docs/work_packets/WPR106-31-discovery-lead-replay-entry-evidence.md`
  - `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_MATERIALIZATION_LANE_REPORT.md`
  - `docs/work_packets/WPR106-30-discovery-lead-materialization-lane.md`
  - `docs/stage_reports/STAGE_R106_CANDIDATE_REJECTION_ROOT_CAUSE_AND_GATE_MATERIALIZATION_REPORT.md`
  - `docs/work_packets/WPR106-29-candidate-rejection-root-cause-and-gate-materialization.md`
  - `docs/stage_reports/STAGE_R106_AUTOPILOT_STEP_TRANSPARENCY_AND_CLEANLINESS_AUDIT_REPORT.md`
  - `docs/work_packets/WPR106-28-autopilot-step-transparency-and-cleanliness-audit.md`
  - `docs/stage_reports/STAGE_R106_CANDIDATE_ELIGIBILITY_LARGE_RUN_STALL_REPORT.md`
  - `docs/work_packets/WPR106-27-candidate-eligibility-large-run-stall.md`
  - `docs/stage_reports/STAGE_R106_FULL_REPO_MISMATCH_BUG_AUDIT_REPORT.md`
  - `docs/work_packets/WPR106-26-full-repo-mismatch-bug-audit.md`
  - `docs/stage_reports/STAGE_R106_CYCLE_MANIFEST_EVIDENCE_PORTABILITY_REPORT.md`
  - `docs/work_packets/WPR106-25-cycle-manifest-evidence-portability.md`
  - `docs/stage_reports/STAGE_R106_DISCOVERY_MANIFEST_HANDOFF_PORTABILITY_REPORT.md`
  - `docs/work_packets/WPR106-24-discovery-manifest-handoff-portability.md`
  - `docs/stage_reports/STAGE_R106_BTC_ETH_PERP_STRATEGY_KNOWLEDGE_INGEST_REPORT.md`
  - `docs/work_packets/WPR106-23-btc-eth-perp-strategy-knowledge-ingest.md`
  - `docs/stage_reports/STAGE_R106_CATALOG_HANDOFF_PORTABILITY_REPORT.md`
  - `docs/work_packets/WPR106-22-catalog-handoff-portability.md`
  - `docs/stage_reports/STAGE_R106_FULL_REPO_DATA_CODE_CROSSCHECK_REPORT.md`
  - `docs/work_packets/WPR106-21-full-repo-data-code-crosscheck.md`
  - `docs/stage_reports/STAGE_R106_COMPLETED_CATALOG_WIRING_VALIDATION_REPORT.md`
  - `docs/work_packets/WPR106-05-completed-catalog-wiring-validation.md`
  - `docs/stage_reports/STAGE_R106_ACTIVE_CYCLE_PROGRESS_AND_RUNTIME_VISIBILITY_REPORT.md`
  - `docs/work_packets/WPR106-06-active-cycle-progress-and-runtime-visibility.md`
  - `docs/stage_reports/STAGE_R106_PROGRESS_STALE_REFRESH_AND_CYCLE_GATE_ALIGNMENT_REPORT.md`
  - `docs/work_packets/WPR106-07-progress-stale-refresh-and-cycle-gate-alignment.md`
  - `docs/stage_reports/STAGE_R106_EXACT_DISCOVERY_PROCESS_WORKER_GUARD_AND_RUNTIME_PROBE_REPORT.md`
  - `docs/work_packets/WPR106-08-exact-discovery-process-worker-guard-and-runtime-probe.md`
  - `docs/stage_reports/STAGE_R106_EXACT_DISCOVERY_FULL_RUN_PROCESS_POOL_CRASH_FOLLOWUP_REPORT.md`
  - `docs/work_packets/WPR106-09-exact-discovery-full-run-process-pool-crash-followup.md`
  - `docs/work_packets/WPR106-10-exact-discovery-performance-first-worker-cap.md`
  - `docs/work_packets/WPR106-11-windows-run-state-atomic-replace-retry.md`
  - `docs/work_packets/WPR106-12-final-ledger-schema-repair.md`
  - `docs/stage_reports/STAGE_R106_RESEARCH_ANALYTICS_NEXT_AGENT_HANDOFF.md`
  - `docs/work_packets/WPR106-13-research-analysis-handoff-and-analytics-step.md`
  - `docs/stage_reports/STAGE_R106_OPERATOR_ANALYSIS_JOB_REQUIRED_WORKFLOW_REPORT.md`
  - `docs/work_packets/WPR106-14-operator-analysis-job-and-required-workflow.md`
  - `docs/stage_reports/STAGE_R106_OPERATOR_RESEARCH_AUTOPILOT_SEQUENCER_REPORT.md`
  - `docs/work_packets/WPR106-15-operator-research-autopilot-sequencer.md`
  - `docs/stage_reports/STAGE_R106_RESEARCH_WORKFLOW_COMPLETION_REPORT.md`
  - `docs/work_packets/WPR106-16-research-workflow-completion.md`
  - `docs/stage_reports/STAGE_R106_FINAL_CROSSCHECK_ROBUSTNESS_REPORT.md`
  - `docs/work_packets/WPR106-17-final-crosscheck-robustness.md`
  - `docs/stage_reports/STAGE_R106_OPERATOR_AUTOPILOT_CRASH_RETRY_HARDENING_REPORT.md`
  - `docs/work_packets/WPR106-18-operator-autopilot-crash-retry-hardening.md`
  - `docs/stage_reports/STAGE_R106_LONG_PERFORMANCE_UTILIZATION_STUDY_REPORT.md`
  - `docs/work_packets/WPR106-19-long-performance-utilization-study.md`
  - `docs/stage_reports/STAGE_R106_PERFORMANCE_SPEEDUPS_AND_UI_WIRING_REPORT.md`
  - `docs/work_packets/WPR106-20-performance-speedups-and-ui-wiring.md`
  - `docs/stage_reports/STAGE_R106_HISTORICAL_REFRESH_LONG_NETWORK_OUTAGE_TOLERANCE_REPORT.md`
  - `docs/work_packets/WPR106-04-historical-refresh-long-network-outage-tolerance.md`
  - `docs/stage_reports/STAGE_R106_CENTRAL_HISTORICAL_DATA_CATALOG_REPORT.md`
  - `docs/work_packets/WPR106-01-central-historical-data-catalog.md`
  - `docs/stage_reports/STAGE_R105_BYBIT_HYPERLIQUID_PROVIDER_SURFACE_AUDIT_REPORT.md`
  - `docs/work_packets/WPR105-107-bybit-hyperliquid-provider-surface-audit.md`
  - `docs/stage_reports/STAGE_R105_DURABLE_DATA_ACQUISITION_STEP0_REPORT.md`
  - `docs/work_packets/WPR105-106-durable-data-acquisition-step0.md`
  - `docs/stage_reports/STAGE_R105_DURABLE_DEPTH_BLOCKER_UI_CLARITY_REPORT.md`
  - `docs/work_packets/WPR105-105-durable-depth-blocker-ui-clarity.md`
  - `docs/stage_reports/STAGE_R105_REQUIRED_DISCOVERY_WIRING_SNAPSHOT_AND_UTILIZATION_REPORT.md`
  - `docs/work_packets/WPR105-104-required-discovery-wiring-snapshot-and-utilization.md`
  - `docs/stage_reports/STAGE_R105_RESEARCH_CHART_READABILITY_AND_NEXT_ACTION_REPORT.md`
  - `docs/work_packets/WPR105-103-research-chart-readability-and-next-action.md`
  - `docs/stage_reports/STAGE_R105_RESEARCH_UI_REQUIRED_WORKFLOW_CLARITY_REPORT.md`
  - `docs/work_packets/WPR105-102-research-ui-required-workflow-clarity.md`
  - `docs/stage_reports/STAGE_R105_FINAL_CODE_AUDIT_HARDWARE_UI_POLISH_REPORT.md`
  - `docs/work_packets/WPR105-101-final-code-audit-hardware-ui-polish.md`
  - `docs/stage_reports/STAGE_R105_HARDWARE_UTILIZATION_STUDY_READINESS_REPORT.md`
  - `docs/work_packets/WPR105-100-hardware-utilization-study-readiness.md`
  - `docs/stage_reports/STAGE_R105_FINAL_CROSSCHECK_PERFORMANCE_VALIDATION_REPORT.md`
  - `docs/work_packets/WPR105-99-final-crosscheck-performance-validation.md`
  - `docs/stage_reports/STAGE_R105_BLOCKED_ARTIFACT_DIRECTORY_SUPPRESSION_REPORT.md`
  - `docs/work_packets/WPR105-04-blocked-artifact-directory-suppression.md`
  - `docs/stage_reports/STAGE_R105_DISCOVERY_PROCESSOR_UTILIZATION_TELEMETRY_REPORT.md`
  - `docs/work_packets/WPR105-03-discovery-processor-utilization-telemetry.md`
  - `docs/stage_reports/STAGE_R105_SECURE_HANDOFF_EXPORT_HYGIENE_REPORT.md`
  - `docs/work_packets/WPR105-02-secure-handoff-export-hygiene.md`
  - `configs/handoff/r105_secure_repo_export.json`
  - `docs/stage_reports/STAGE_R105_R104_POSTMORTEM_EFFECTIVE_TRIAL_DEDUPE_REPORT.md`
  - `docs/stage_reports/STAGE_R105_R104_POSTMORTEM_TRACKED_SUMMARY.json`
  - `docs/work_packets/WPR105-01-latest-sweep-postmortem-effective-trials.md`
  - `docs/stage_reports/STAGE_R104_EXIT_ENTRY_ORDERFLOW_RESEARCH_HANDOFF.md`
  - `docs/work_packets/WPR104-06-exit-entry-orderflow-research-handoff.md`
  - `docs/stage_reports/STAGE_R104_DISCOVERY_SEARCH_FEATURE_CROSSCHECK_REPORT.md`
  - `docs/work_packets/WPR104-05-discovery-search-feature-crosscheck.md`
  - `docs/stage_reports/STAGE_R104_RESEARCH_UI_DURABLE_CANDIDATE_CONSOLE_REPORT.md`
  - `docs/stage_reports/STAGE_R104_DURABLE_BRUTEFORCE_RUN_HARDENING_REPORT.md`
  - `docs/work_packets/WPR104-04-durable-bruteforce-run-hardening.md`
  - `docs/work_packets/WPR104-01-research-ui-durable-candidate-console.md`
  - `docs/stage_reports/STAGE_R104_OPERATOR_CONSOLE_USABILITY_HARDENING_REPORT.md`
  - `docs/work_packets/WPR104-03-operator-console-usability-hardening.md`
  - `docs/stage_reports/STAGE_R104_GAP_AWARE_DURABLE_CYCLE_FEATURE_MATERIALIZATION_REPORT.md`
  - `docs/work_packets/WPR104-02-gap-aware-durable-cycle-feature-materialization.md`
  - `docs/stage_reports/STAGE_R103_DURABLE_PUBLIC_ARCHIVE_FIXTURES_REPORT.md`
  - `docs/work_packets/WPR103-01-durable-public-archive-fixtures.md`
  - `docs/stage_reports/STAGE_R102_BRANCH_COMPLETION_IMPLEMENTATION_REPORT.md`
  - `docs/work_packets/WPR102-01-branch-completion-implementation.md`
  - `docs/stage_reports/STAGE_R101_BRANCH_COMPLETION_REVIEW_ORCHESTRATOR_PLAN.md`
  - `docs/work_packets/WPR101-01-branch-completion-review-orchestrator-plan.md`
  - `docs/stage_reports/STAGE_R100_PROVIDER_CAPABILITY_REGISTRY_REPORT.md`
  - `docs/BRANCH_TECHNOLOGY_AND_DEVELOPMENT_REFERENCE.md`
  - `docs/stage_reports/STAGE_12_1_EXIT_REPORT.md`
  - `docs/stage_reports/STAGE_12_EXIT_REPORT.md`
  - `docs/stage_reports/STAGE_12_COMPLETION_LIMITATIONS.md`
  - `docs/stage_reports/STAGE_13_READINESS_PLANNING_REPORT.md`
  - `src/tradingbotsuite/research/feature_ablation.py`
  - `src/tradingbotsuite/research/stage12_research.py`
  - `configs/features/features_microstructure_filter_only.json`
  - `configs/features/features_cross_asset_context.json`
  - `tests/tradingbotsuite/test_feature_ablation.py`
  - `tests/tradingbotsuite/test_stage12_research_plan.py`
  - `tests/contracts/test_feature_contracts.py`
  - `docs/stage_reports/STAGE_R96_GPU_ACCELERATED_STABILITY_REGION_SEARCH_REPORT.md`
- Known blockers accepted into this stage:
  - Open P0 issue count is zero after WPR106-38. The P0 safety boundaries still
    govern all later research work and must not be weakened.
  - WPR106-39 preserves the non-negotiable regime naming rule by stamping
    active GMM/no-regime backend evidence in machine-readable fields while
    retaining legacy HMM/KNN compatibility names.
  - WPR106-40 preserves the Binance-versus-Hyperliquid boundary by stamping
    venue-aware cost/fill research evidence as historical research only and not
    Hyperliquid execution proof.
  - WPR106-41 preserves config-boundary safety by failing closed on misspelled
    active parser fields and wrong active spec versions while retaining known
    documentary metadata in historical-cycle configs.
  - `ISSUE-R106-014` is resolved by WPR106-38. Runtime artifact validation is
    now mode-aware, unknown/mode-ambiguous manifests fail closed, paper/live
    runtime loading rejects unsupported artifacts, and shadow loading requires
    explicit shadow promotion candidates.
  - `ISSUE-R106-013` is resolved by WPR106-37. Hyperliquid credential files
    can provide passive signer/account/endpoint values, but cannot imply
    `enable_live`; explicit `TBS_HL_ENABLE_LIVE=true` is required.
  - `ISSUE-R106-012` is resolved by WPR106-36. The reference simulator now
    uses lower-timeframe open fills at or after the latency target for
    `lower_timeframe_execution_path`, records entry proof metadata, and fails
    closed when lower-frame entry coverage is unavailable.
  - `ISSUE-R106-011` is resolved by WPR106-35. The split engine now supports
    `LabelSpec`, event-end-aware purge, compact train-index evidence, and
    discovery/historical-cycle wiring for label end-time metadata.
  - `ISSUE-R106-009` is resolved by WPR106-33. The repository now has a
    checked-in clean Python 3.11 CI baseline for editable install, dependency
    consistency, compile, contracts, and live/artifact boundary tests.
  - `ISSUE-R106-010` is resolved by WPR106-34. Historical cycles now fail
    closed instead of silently synthesizing with no source, explicit synthetic
    fixtures are test/demo/benchmark scoped, ambiguous local fixture directories
    are rejected, and source-selection manifests are required outputs.
  - `ISSUE-R106-008` is resolved by WPR106-32. The active index now clarifies
    ResearchEngineDeluxe identity, current checkout state, latest R106
    evidence, open blockers, and research-only boundaries.
  - `ISSUE-R104-001` is open. Compact checksum-verified BTCUSDT/ETHUSDT
    Binance Vision multi-window fixture packs are valid for screening, but
    expanded durable primary-bar fixtures are still required for
    candidate-ready brute-force evidence. WPR105-106 provides the required
    collection pipeline; the issue remains open until the collection and
    downstream evidence runs complete.
  - `ISSUE-R106-001` is resolved by WPR106-08 through WPR106-12. Exact discovery
    has durable progress and snapshot/resume support. WPR106-09 recovered the
    latest interrupted BTC run in place to 407669/570240 completed trials,
    repaired state/manifest lag, and added large-resume recovery. WPR106-10
    keeps the default process cap performance-first at 8 workers per operator
    direction, accepting higher instability risk because checkpoint recovery is
    now durable. WPR106-11 repaired a later Windows checkpoint replace failure
    and reconciled state to 531077/570240 completed trials. WPR106-12 repaired
    final ledger schema normalization after the BTC exact run completed and
    rebuilt the final manifest/Parquet ledgers to 570240/570240 trials.
  - `ISSUE-R106-002` is resolved by WPR106-16. Long research runs now have the
    mandatory analysis, run-to-run delta, bridge-compatible frozen-entry
    exit-lab, candidate eligibility, modern-window profile, and one-button
    operator sequencing machinery. Remaining blockers are empirical evidence
    gates, tracked by `ISSUE-R104-001` and the stage notes.
  - `ISSUE-R106-003` is resolved by WPR106-22. The current `main` checkout
    mirror contains valid BTCUSDT/ETHUSDT candidate-depth catalog data, and
    active catalog/spec path consumers now rebase stale absolute paths from the
    old `C:\Users\papaa\Music\tradingbotsuite` checkout to the current mirrored
    operator-run paths without rewriting generated artifacts. The migrated
    pre-profile catalog remains truthful when it reports no local
    `modern_window_profile.json` artifacts.
  - `ISSUE-R106-004` is resolved by WPR106-24. The latest autopilot retry
    completed ETH exact discovery to 570240/570240 trials, then failed because
    BTC discovery-manifest `required_outputs` still pointed at the old checkout
    root. Operator candidate eligibility and the candidate-pack bridge now
    rebase migrated discovery-manifest paths at read time when mirrored local
    outputs exist, while truly outside paths remain fail-closed.
  - `ISSUE-R106-005` is resolved by WPR106-25. The follow-up autopilot retry
    got past the discovery handoff blocker and failed on BTC historical-cycle
    `required_outputs.ablation_report`, which still pointed at the old checkout
    root. Operator candidate eligibility and candidate-pack gate evaluation now
    rebase mirrored historical-cycle evidence outputs at read time, while truly
    outside paths remain fail-closed.
  - `ISSUE-R106-006` is resolved by WPR106-26. The full repo mismatch audit
    found nested generated-manifest metadata outside `required_outputs` that
    still held old checkout strings after normalization. The shared normalizer
    now rebases repo-root-relative paths such as `data/...`, `configs/...`, and
    `repo_root` metadata at read time, leaving generated artifacts unchanged.
  - `ISSUE-R106-007` is resolved by WPR106-27. The latest long-running
    autopilot reached BTC candidate eligibility and stalled before writing an
    eligibility artifact because the bridge reread 570240 trial JSON records
    twice and reloaded historical-cycle gate evidence per discovery candidate.
    The bridge now uses large-run count/hash/sample auditing plus cached
    candidate-gate membership; real BTC eligibility finishes in about 9 seconds
    from this checkout with `PYTHONPATH=src`.
  - `ISSUE-R95-001` remains resolved by WPR96 with optional
    `cuda_fixed_holding` backend evidence and diagnostic-only status.

## Completion roadmap after WPR105-01

The branch is not empirically complete. Infrastructure is strong, but
candidate-ready completion still depends on proving candidates through
falsification on durable evidence rather than latest-window screening.

Recommended next stages:

1. Continue Stage R105 empirical falsification matrix.
   Test no-regime versus GMM and optional true-HMM variants, independent-event
   scoring, signal-density penalties, matched feature/filter/exit ablations,
   side/split/regime evidence, cost/funding stress, stability neighborhoods,
   and multiple-testing controls. Use the R105 postmortem signatures to avoid
   expensive component combinations before simple matched baselines survive.
2. Stage R105 expanded durable evidence path.
   Run the Step 0 durable data collection pipeline to build materially larger
   BTC/ETH durable public-archive or vendor-backed fixture packs before
   candidate-ready claims. Preserve `research_only`, `observe_only`, and
   `promotion_ready: false`; accept candidate-pack absence when gates block
   weak evidence.
3. Stage R106 maintainability polish.
   Refresh docs after durable-data work and plan narrow extraction of oversized
   orchestration modules without broad rewrites.
4. Stage R107 promotion handoff planning only.
   Open only after a research-only candidate pack exists with durable evidence
   and all research gates passing. This branch must still not start live
   execution, live config changes, runtime-mode changes, order placement, or
   sizing behavior.

WPR106-01 implementation note:

- `WPR106-01-central-historical-data-catalog` introduces
  `historical_data_catalog.json` as the required operator data source of truth.
  The catalog wraps the implemented Binance Vision public-archive fixture
  collector, records active readiness/cycle/discovery spec paths, indexes
  provider states for Binance Vision, Crypto Lake, Bybit, and Hyperliquid, and
  keeps unimplemented provider ingestion explicit instead of marking it ready.
  The operator checklist now starts with `refresh-historical-data-catalog`;
  `collect-durable-data` remains compatibility-only.

WPR106-02 implementation note:

- `WPR106-02-historical-data-refresh-resume-hardening` investigated a failed
  long R106 catalog refresh and found a partial BTCUSDT run with 228
  checksum-verified monthly archive downloads, about 42 GB, but no generated
  catalog. The refresh path now uses a central checksum-verified Binance Vision
  archive cache, seeds that cache from prior partial operator runs, writes a
  `collection_progress.json` journal with archive-step progress and ETA, and
  streams generated Parquet fixture outputs by archive partition to reduce
  memory pressure. Operator progress diagnostics and the Research UI now expose
  historical-data refresh progress. Operator job-log appends now use an
  immediate SQLite write lock plus retry so the background worker cannot race a
  queue request into a duplicate log sequence. All generated data remains
  research-only, observe-only, and `promotion_ready: false`.

WPR106-03 implementation note:

- `WPR106-03-historical-refresh-transient-network-continuation` investigated
  the follow-up failed refresh
  `refresh-historical-data-catalog-500f7d78e7fa458eb3b7077ecbb7e242` and found
  a transient Binance Vision TLS handshake timeout after `241/456` archive
  steps. The refresh path now retries transient archive/checksum fetch failures,
  records fetch attempt/retry counts in download manifests, and reuses completed
  prior symbol fixture packs so a retry does not rebuild BTCUSDT from the
  beginning. Operator research-server runs can set
  `TBS_BINANCE_MARKET_STREAMS_ENABLED=false` to avoid unrelated Binance
  websocket startup noise during long catalog refreshes. All generated data
  remains research-only, observe-only, and `promotion_ready: false`.

WPR106-04 implementation note:

- `WPR106-04-historical-refresh-long-network-outage-tolerance` investigated
  refresh job `refresh-historical-data-catalog-c209bf0dbdb04ab6be9fa9306525b423`
  and found a longer DNS outage (`getaddrinfo failed`) after `286/456` archive
  steps while collecting ETHUSDT `1m` `2021-08`. The WPR106-03 resume path had
  loaded and reused BTCUSDT/partial ETHUSDT work, but the transient retry window
  was too short for the outage. Binance Vision archive/checksum fetches now
  default to 360 attempts, 10 second base backoff, and 60 second max backoff,
  with operator overrides through
  `TBS_BINANCE_VISION_DOWNLOAD_MAX_ATTEMPTS`,
  `TBS_BINANCE_VISION_DOWNLOAD_RETRY_BACKOFF_SECONDS`, and
  `TBS_BINANCE_VISION_DOWNLOAD_RETRY_MAX_BACKOFF_SECONDS`. Download manifests
  record the resolved retry budget, DNS-shaped transient failures retry, and
  checksum mismatches still fail fast. All generated data remains research-only,
  observe-only, and `promotion_ready: false`.

WPR106-05 implementation note:

- `WPR106-05-completed-catalog-wiring-validation` validated completed catalog
  `refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb` as the
  active source of truth. BTCUSDT and ETHUSDT each have 76 months of 15m klines,
  1m klines, and aggTrades from Binance Vision, 228 checksum-verified archives
  per symbol, generated active readiness files, generated active cycle specs,
  and generated active exact-discovery specs. Stale R104-only operator progress
  gates were replaced with catalog-derived expected cycle/discovery IDs,
  generated candidate-depth exact specs are treated as stable resumable sweeps,
  the Research UI recognizes generated candidate-depth artifacts as required,
  and interrupted DB jobs left in `running` state are recovered at operator
  startup. Provider-quality review keeps Binance Vision as the implemented
  active source while Crypto Lake, Bybit, and Hyperliquid remain visible
  expansion sources until their credential/parser/checksum/gap-validation
  contracts are implemented. All generated data remains research-only,
  observe-only, and `promotion_ready: false`.

WPR106-06 implementation note:

- `WPR106-06-active-cycle-progress-and-runtime-visibility` adds active
  historical-cycle progress to `/api/operator/research/progress` and the
  Research UI. The progress payload is read from the isolated operator run
  directory while a cycle is still running, using `candidate_space_manifest.json`,
  `split_manifest.json`, and backtest-manifest counts. It reports aggregate
  candidate completion, total backtest-evaluation completion, rate, ETA, output
  path, and compute policy, and clearly labels the scope before final ranking,
  gate, and manifest outputs exist. The packet also records that the R106 exact discovery
  specs still schedule 570240 trials per symbol; prior R105 telemetry shows the
  comparable exact sweep took about 31.2 wall-clock hours, so no sub-30-hour
  discovery runtime claim is made.

WPR106-07 implementation note:

- `WPR106-07-progress-stale-refresh-and-cycle-gate-alignment` fixes the
  misleading checklist state after the completed BTC R106 cycle. Completed
  historical-data refresh journals are no longer returned as active progress
  when no refresh job is active, so they do not mask cycle/discovery progress.
  Historical-cycle checklist validation now accepts the current
  `candidate_gate_report` output key and accepts the generated R106
  candidate-depth cycle evidence of 63 materialized candidates when the
  manifest records 2048 brute-force-equivalent coverage. The completed BTC
  cycle now advances the checklist to BTC exact discovery.

WPR106-08 implementation note:

- `WPR106-08-exact-discovery-process-worker-guard-and-runtime-probe`
  investigated the failed BTC exact-discovery process-pool run and recovered
  the active output in place. Real-discovery process workers are now capped at
  8 by default while preserving the configured 48-worker request in telemetry,
  completed chunks are persisted as futures return, broken process pools report
  the worker plan, and no-stop exact-discovery runs schedule full KNN cache
  groups rather than tiny randomized chunks. KNN screening reuses relaxed exact
  base predictions, cached threshold metric arrays, cached no-regime baselines,
  and deferred heavy inline artifacts for `interesting_only` sweeps. Bounded
  resume probes advanced the active BTC run from 128 to 512 persisted trial
  records; the final 64-trial probe completed in 610.7 seconds and estimates
  the full BTC exact sweep at roughly 9 to 12 wall-clock hours on this machine.
  The run is still research-only and incomplete until all exact-discovery trials
  finish and downstream eligibility review passes.

WPR106-09 implementation note:

- `WPR106-09-exact-discovery-full-run-process-pool-crash-followup`
  investigated the latest BTC exact-discovery full run after roughly 14 hours.
  Durable trial files reached 407669 while `run_state.json` lagged at 407420
  and the manifest was stale at 512. A zero-trial recovery resume merged the
  249 lagging trial files without restarting discovery compute, leaving the
  run paused at 407669/570240 completed trials with 162571 remaining. The
  stopped run left one partial cache group,
  `price_trend_vol / none / 2h / cosine / hmm_state=3 / posterior=0.55 /
  entropy=0.78 / k=8`, 4469/5760 complete, consistent with process-pool memory
  pressure rather than lost artifacts. Large resumes now validate state-backed
  trial files, hydrate only lagging records, skip context preparation for
  zero-trial recovery, and avoid overwriting ledgers from a partial loaded
  subset. Full ledgers rebuild from trial JSON records only when the run
  completes. The default real-discovery process-worker cap is now 8 unless the
  operator explicitly overrides `TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS`.

WPR106-10 implementation note:

- `WPR106-10-exact-discovery-performance-first-worker-cap` restores the
  default exact-discovery process-worker cap to 8 after operator direction that
  throughput outweighs instability risk for the current study. The WPR106-09
  large-resume recovery behavior remains intact, so a later process-pool crash
  should recover completed trial JSONs instead of restarting the sweep.

WPR106-11 implementation note:

- `WPR106-11-windows-run-state-atomic-replace-retry` investigated failed job
  `run-discovery-5b8013f779ef43c28a8c3567a14d14a4`. The job advanced durable
  BTC exact-discovery trial files to 531077, but Windows denied the atomic
  temp-file replace into `run_state.json`. `atomic_write_json()` now retries
  transient `PermissionError` replace failures with env-tunable attempts and
  backoff. A zero-trial resume reconciled the active run to 531077 completed
  IDs, 531077 hashes, 531077 trial files, and 39163 remaining trials. The
  failed operator job remains failed as a truthful historical job record, but
  its durable progress is preserved.

WPR106-12 implementation note:

- `WPR106-12-final-ledger-schema-repair` investigated failed job
  `run-discovery-40cb1c90d0f8487a859a23e05d21e656`. The BTC exact-discovery
  compute had finished with 570240 durable trial JSON records, but final
  Parquet ledger materialization failed because absent numeric ledger fields
  were emitted as empty strings and mixed with integer metrics such as
  `accepted_bar_count`. Final ledger frames now coerce integer, float, and
  boolean ledger fields to pandas nullable dtypes before Parquet writes.
  Completed-run resume can now rebuild missing, stale, row-count mismatched, or
  unreadable final ledgers/manifests from immutable trial JSONs while still
  refusing clean completed-run overwrite. The active BTC exact-discovery output
  now has 570240 completed state IDs, 570240 completed trial hashes, 570240
  trial JSON records, and final manifest counts of 22560 interesting, 547680
  blocked, and 0 filter-blocked trials. Operator progress now lets this
  repaired complete artifact override the stale failed job row for checklist
  status, while preserving the failed job in history. These outputs are
  research-only leads, not promotion-ready candidates.

WPR106-13 implementation note:

- `WPR106-13-research-analysis-handoff-and-analytics-step` adds
  `tradingbotsuite.research_discovery.analysis_report`, a deterministic
  research-only post-run analysis helper. It reads completed historical-cycle
  and exact-discovery artifacts, summarizes feature-set, strategy, exit-policy,
  holding-window, KNN/filter-setting, blocker, pure-ROI, and trade-level
  Sortino evidence, and writes JSON plus Markdown analysis artifacts without
  rerunning compute or changing evidence. The current BTC analysis output is
  under `data/research/operator_runs/analysis/r106_btc_current_analysis`.
  `STAGE_R106_RESEARCH_ANALYTICS_NEXT_AGENT_HANDOFF.md` records the operator's
  desired next direction: a one-button resumable BTC/ETH research autopilot,
  mandatory post-run analytics, modern-window profiles, frozen-entry exit labs,
  run-to-run deltas, and eventual UI progress/ETA polish. This packet also
  registers `ISSUE-R106-002`; no candidate-ready trading claim exists.

WPR106-14 implementation note:

- `WPR106-14-operator-analysis-job-and-required-workflow` wires the
  WPR106-13 analysis helper into the operator workflow. The new
  `analyze-research-results` operator job validates cycle/discovery manifest
  inputs under the configured research output root, writes isolated
  `research_analysis.json` and `research_analysis.md` artifacts under
  `operator_runs/analysis`, and keeps outputs research-only, observe-only, and
  `promotion_ready: false`. Research artifacts and progress diagnostics now
  index `research_analysis`; the required Research UI checklist places
  analysis before candidate eligibility review. This is a workflow/visibility
  slice only: it does not run a master BTC/ETH autopilot, create modern-window
  specs, run frozen-entry exit labs, write candidate packs, alter live runtime,
  place orders, or claim candidate readiness.

WPR106-15 implementation note:

- `WPR106-15-operator-research-autopilot-sequencer` adds the bounded
  `run-research-autopilot` operator job and primary Research UI action. The
  job sequences the existing Historical Data Catalog, historical-cycle,
  exact-discovery, research-analysis, and candidate-eligibility helpers
  directly rather than queueing child jobs, so it avoids single-worker job-loop
  deadlock. It skips current completed artifacts, executes missing required
  steps up to a bounded `max_steps`, stops on blocked prerequisites, and writes
  `research_autopilot_manifest.json` under `operator_runs/research_autopilot`
  with executed/skipped/blocked step evidence. This packet does not generate
  modern-window specs, write run-to-run deltas, simulate frozen-entry
  alternative exits, write candidate packs, alter live runtime, place orders, or
  claim candidate readiness.

WPR106-16 implementation note:

- `WPR106-16-research-workflow-completion` closes the remaining workflow
  engineering gaps from `ISSUE-R106-002`. The Historical Data Catalog now emits
  modern-window profile manifests/spec links alongside the full-window active
  specs. `simple_runner_v1` is a supported primary-bar research exit policy and
  the frozen-entry exit lab writes bridge-compatible
  `discovery_exit_lab_manifest.json` artifacts, including a fail-closed blocked
  manifest when existing discovery outputs lack per-entry timestamps. The
  operator API, progress checklist, artifact index, Research UI, and autopilot
  now sequence research analysis, run-to-run deltas, frozen-entry exit lab, and
  candidate eligibility before any candidate-pack review. All new artifacts are
  research-only, observe-only, and `promotion_ready: false`; no live runtime,
  order-placement, sizing, candidate-pack-write, or promotion behavior was
  added.

WPR106-17 implementation note:

- `WPR106-17-final-crosscheck-robustness` hardens the completed workflow surface
  without adding new research claims. Frozen-entry exit-lab malformed inputs now
  produce blocked research artifacts instead of uncaught operator failures.
  Candidate-eligibility service execution now enforces research-root path
  allowlisting, nested required-output containment, same-symbol evidence, and
  stricter bridge-manifest completion validation. Research autopilot now runs
  all requested symbol cycle/discovery prerequisites before downstream
  analysis, deltas, frozen-entry exit labs, and eligibility. Focused tests,
  contracts, and full pytest passed; no live runtime, order-placement, sizing,
  candidate-pack-write, or promotion behavior was added.

WPR106-18 implementation note:

- `WPR106-18-operator-autopilot-crash-retry-hardening` adds bounded automatic
  retry behavior for long operator autopilot runs. Direct helper steps retry by
  default once with attempt-specific helper job IDs so partial failed output
  directories do not poison the retry. Exact-discovery retries retain the
  stable-run-id output directory and therefore keep resume-from-`run_state.json`
  behavior. If the operator process restarts with a stale running autopilot job,
  the interrupted job is marked failed for auditability and one restart-retry
  autopilot job is queued automatically. Attempt numbers, max attempts, helper
  job IDs, and error details are written to the autopilot manifest and job logs.
  Focused tests, operator UI tests, contracts, and full pytest passed; no live
  runtime, order-placement, sizing, candidate-pack-write, or promotion behavior
  was added.

WPR106-19 implementation note:

- `WPR106-19-long-performance-utilization-study` records the second
  performance/utilization pass for the R106 research workflow. Hardware probes
  on the Ryzen 7 7700 showed that 16 CPU workers can saturate logical capacity
  better than 8 workers, and the CuPy matrix probe can drive the GPU, but the
  BTC candidate-depth exact-discovery probe remains dominated by
  KNN/materialization and memory/process-shape behavior rather than generic
  CPU/GPU saturation. A bounded 16-trial BTC candidate-depth exact probe over
  the active `221952` row fixture took `1033.65s`, with `105.95s` in context
  preparation and `927.50s` in trial execution. The completed BTC exact final
  manifest also shows finalization/artifact accounting as a low-CPU phase:
  `570555` files, about `7.08GB`, and `86.37%` artifact-write wall-time share.
  No runtime defaults were changed; the next safe optimization work is finer
  child-process/KNN timing, controlled 8/12/16 worker probes on BTC/ETH
  candidate-depth data, and chunked artifact finalization that preserves
  durable trial records and atomic state.

WPR106-20 implementation note:

- `WPR106-20-performance-speedups-and-ui-wiring` implements the safe immediate
  speed improvements from the performance study. Discovery telemetry now uses
  observed parent-process artifact write counters instead of a recursive
  output-directory scan when counters are available, exposes finalization timing
  buckets, and records process-executor chunk timing plus the child-CPU
  accounting limitation. Placeholder process-executor discovery runs avoid
  unnecessary real-discovery context initialization. The operator API/UI now
  surfaces discovery worker plan, cache hit rates, ETA/runtime fields, artifact
  pressure, process timing, top runtime stages, and the WPR106-19 performance
  study artifact without requiring raw manifest JSON. Compile, contracts, full
  research-discovery tests, and full operator UI tests passed. No live runtime,
  order-placement, sizing, candidate-pack-write, promotion behavior, or speed/
  profit claim was added.

WPR106-21 implementation note:

- `WPR106-21-full-repo-data-code-crosscheck` ran a docs-only full repo data and
  code audit on current `main` as the migrated R106 checkout. The audit
  validated the current checkout mirror of the active R106 catalog and confirmed
  BTCUSDT/ETHUSDT candidate-depth fixture manifests are valid, durable-public-
  archive ready, research-only, observe-only, and `promotion_ready: false`.
  Provider surfaces remain truthfully classified: Binance Vision is active,
  Binance REST is secondary/diagnostic, Crypto Lake is local-export dependent,
  and Bybit/Hyperliquid archives are registered but not implemented for active
  catalog use. Static scans found no new order-placement, runtime-mode, sizing,
  live-config, or unsafe promotion-ready regression. The audit opened
  `ISSUE-R106-003` because active catalog path fields still point at the old
  checkout and local modern-window profile artifacts are absent. Compile,
  contracts, research-discovery, historical, research-artifacts, and live tests
  passed.

WPR106-22 implementation note:

- `WPR106-22-catalog-handoff-portability` resolves `ISSUE-R106-003` for the
  migrated `main` checkout. Historical-data catalog reads now rebase stale
  absolute operator-run paths to the current mirrored catalog run directory
  when the target exists locally, and operator isolated cycle/discovery jobs
  normalize embedded dataset/readiness paths before writing their per-job
  specs. The fix does not mutate generated fixture packs, catalogs, source
  specs, cycle outputs, discovery ledgers, live runtime mode, promotion
  readiness, order placement, or sizing behavior. The pre-profile migrated
  catalog remains truthful when it has no local modern-window profile artifacts.
  Compile, market-data collection tests, operator UI tests, and contracts
  passed. `ISSUE-R104-001` remains open for empirical ETH/candidate-gate work.

WPR106-23 implementation note:

- `WPR106-23-btc-eth-perp-strategy-knowledge-ingest` imports the external
  BTC/ETH perpetual futures strategy master report into
  `docs/research_knowledge/source_reports/` and adds a detailed repo-native
  knowledge base under `docs/research_knowledge/`. The artifact preserves the
  report's strategy priority map, strategy cards, feature groups, data and
  simulator requirements, high-value experiment backlog, ML guidance,
  falsification standards, and red-team cautions as hypothesis knowledge only.
  It is explicitly not an implementation queue, candidate evidence, promotion
  evidence, or live trading instruction. `START_HERE.md` now points agents to
  the research knowledge catalog. No source code, configs, fixtures, generated
  artifacts, tests, live behavior, runtime mode, order placement, sizing, or
  promotion behavior changed. `git diff --check` passed.

WPR106-29 implementation note:

- `WPR106-29-candidate-rejection-root-cause-and-gate-materialization`
  materializes BTCUSDT/ETHUSDT multiple-testing and validation-floor gate
  evidence for current exact-discovery leads, then reruns candidate-pack bridge
  eligibility from the working tree with capped rejection Markdown. The result
  is a truthful research-only rejection state: BTC has 22,560 blocked rows and
  ETH has 23,040 blocked rows, both with 0 eligible candidates, 0
  discovery-to-cycle ranking overlap, no candidate pack written, and
  `promotion_ready: false`. The bridge now writes reason counts and candidate
  universe alignment into the manifest, pre-indexes gate rows, and caps
  rejection Markdown while preserving full Parquet evidence. Multiple-testing
  search-space inference and stability-neighborhood derivation avoid avoidable
  large-run scans. No live execution, runtime-mode change, order placement,
  sizing, candidate-pack write, or promotion behavior was added. Compile,
  contracts, research-discovery tests, and candidate-pack/operator-UI tests
  passed.

WPR106-31 implementation note:

- `WPR106-31-discovery-lead-replay-entry-evidence` adds a replay-spec and
  entry-signal evidence lane for WPR106-30 materialized discovery leads. It
  introduces `execution.persist_trial_artifacts: predictions_only`, which
  persists split-safe KNN prediction artifacts and strategy-accounting artifacts
  without writing heavy per-trial neighbor diagnostics or HMM posterior
  artifacts. The real BTC/ETH replay runs completed 24/24 trials per symbol,
  produced 24/24 interesting replay candidates per symbol, and wrote annotated
  entry-signal artifacts for all 24 candidates per symbol. BTC has 969,870
  replayed entry-signal rows; ETH has 957,643 replayed entry-signal rows.
  Bounded top-3 frozen-entry exit-lab slices were run for both symbols and all
  six checked leads were blocked because `simple_runner_v1` did not improve
  over fixed holding. This packet does not write historical-cycle rankings,
  candidate gate pass rows, candidate packs, live behavior, runtime-mode
  changes, order placement, sizing, or promotion readiness. Compile, full
  research-discovery tests, contracts, candidate-pack tests, and diff checks
  passed.

WPR106-30 implementation note:

- `WPR106-30-discovery-lead-materialization-lane` adds a bounded descriptor-only
  materialization artifact for exact-discovery KNN leads. It reads immutable
  discovery trial records, preserves source manifest/ledger/trial hashes,
  assigns stable `mat-*` materialized candidate IDs, records prediction and
  entry-event signatures, and writes candidate descriptor JSONL for the next
  empirical packet. The real BTC/ETH artifact run materialized 24 descriptors
  per symbol with 24 unique entry-event signatures per symbol. These artifacts
  explicitly require cycle backtest, cycle ranking, research candidate gate,
  baseline/no-trade comparator, exit-lab, multiple-testing, validation-floor,
  and candidate-pack eligibility evidence before any candidate-ready claim.
  They do not write `candidate_rankings.parquet`, candidate gate pass rows,
  candidate packs, live behavior, runtime-mode changes, order placement, sizing,
  or promotion readiness. Compile, full research-discovery tests, contracts, and
  candidate-pack tests passed.

R103 implementation note:

- `WPR103-01-durable-public-archive-fixtures` added compact, checked-in
  BTCUSDT/ETHUSDT multi-window public archive fixture packs from
  checksum-verified Binance Vision archives. These are data-foundation
  artifacts only; they do not claim candidate-ready performance or promotion
  readiness.

WPR104-01 implementation note:

- `WPR104-01-research-ui-durable-candidate-console` rewired the operator
  Research tab to durable R104 BTC/ETH defaults, added an R104 readiness API
  and visible settings/recommendations, added a UI-backed candidate-pack
  eligibility job, indexed exit-lab/multiple-testing/validation-floor/bridge
  artifacts, kept provider and signal-history diagnostics secondary, and kept
  all outputs research-only and observe-only.

WPR104-02 implementation note:

- `WPR104-02-gap-aware-durable-cycle-feature-materialization` fixed the failed
  R104 durable historical-cycle run by segmenting intentional multi-window
  fixture gaps during feature materialization. Normal continuous datasets still
  fail closed on bar gaps; compact public-archive screening fixtures no longer
  compute returns or rolling features across selected-window gaps. Segmentation
  is limited to true forward gaps; duplicate bars and short-cadence anomalies
  remain validation failures. The feature-builder cache identity is now
  `research-feature-builder-v2` for this semantic change.

WPR104-03 implementation note:

- `WPR104-03-operator-console-usability-hardening` added a backend-derived
  R104 progress contract, visible progress meter, milestone states, next
  action, recommended defaults, function blocks, and clearer timeline/job
  details. Discovery milestones now remain waiting until the matching
  historical-cycle artifact exists. The Research UI remains a thin
  observe-only operator layer over jobs, readiness, feed, and artifact APIs;
  no live execution, promotion, runtime-mode, order-placement, or sizing
  behavior was added.

WPR104-04 implementation note:

- `WPR104-04-durable-bruteforce-run-hardening` investigated the no-lead durable
  runs and found completed short/sparse artifacts plus compact 32-primary-bar
  fixture limits, not a runner crash. Discovery manifests and snapshots now
  carry search-space coverage metadata. R104 has BTC/ETH exact bounded sweep
  configs with 570240 planned combinations per symbol, deeper BTC/ETH
  historical-cycle configs, durable operator defaults, bounded disk-artifact
  progress indexing, clearer deep/exact UI controls, and mobile/desktop layout
  verification. `ISSUE-R104-001` remains open for expanded durable fixture
  data before candidate-ready claims.

WPR104-05 implementation note:

- `WPR104-05-discovery-search-feature-crosscheck` hardened the R104 discovery
  search path with duplicate dimension rejection, parameter-stable generated
  candidate IDs, failed-trial payload preservation, compact-fixture effective
  feature pruning, a score-policy version bump for the changed feature
  semantics, and focused tests proving exact BTC/ETH sweep dimensions, KNN
  payload propagation, KNN threshold rejection reasons, durable feature
  preflight, and sparse/exhaustive generation uniqueness. `ISSUE-R104-001`
  remains open because expanded durable primary-bar fixtures are still required
  before candidate-ready empirical claims.

WPR104-06 implementation note:

- `WPR104-06-exit-entry-orderflow-research-handoff` inspected the completed
  BTCUSDT exact durable sweep
  `run-discovery-142f3b61b761470b8aeb105967dd9c47`, which completed 570240
  trials with zero failed trials, zero interesting candidates, and all rows
  blocked by overlap, independent-event, signal-density, or expectancy gates.
  The handoff consolidates the run evidence, weak points, and Stage R105
  component-falsification plan: entry-only baselines, simple runner and
  exit-only ablations, orderflow standalone/additive/filter/exit tests,
  KNN/regime/no-regime comparisons, matched filter ablations, effective-trial
  deduplication, and multiple-testing controls. No candidate-ready performance
  claim is made; `ISSUE-R104-001` remains open.

WPR105-01 implementation note:

- `WPR105-01-latest-sweep-postmortem-effective-trials` started the R105
  candidate-factory falsification matrix by deriving postmortem artifacts from
  the completed BTCUSDT exact sweep without modifying the source R104 run. The
  postmortem records 570240 scheduled trials, 570240 blocked rows, 570240
  effective parameter keys, 564 ledger-level prediction signature clusters,
  and 38 entry signature clusters. It explicitly records that per-bar
  prediction hashes are unavailable because the R104 run persisted only
  `interesting_only` trial artifacts and all trials were blocked. All outputs
  remain research-only, observe-only, and `promotion_ready: false`;
  `ISSUE-R104-001` remains open for expanded durable BTC/ETH primary-bar
  evidence before candidate-ready claims.

WPR105-02 implementation note:

- `WPR105-02-secure-handoff-export-hygiene` added
  `configs/handoff/r105_secure_repo_export.json` as a conservative source
  handoff/export config with source/docs/tests/config include patterns,
  gitignore/dotignore/default ignore support, explicit security checks, and
  exclusion patterns for generated data, operator runs, caches, credentials,
  `.env` files, logs, databases, Parquet outputs, archives, CSVs, virtual
  environments, and Python caches. A contract test locks the security settings
  and critical exclusions. No research execution, candidate evidence,
  promotion behavior, live config, runtime mode, order placement, or sizing
  behavior was changed.

WPR105-03 implementation note:

- `WPR105-03-discovery-processor-utilization-telemetry` upgraded discovery
  compute telemetry to `discovery-compute-telemetry-v2`, preserving legacy raw
  process CPU fields while adding logical CPU count, worker/logical capacity
  utilization, active-worker-to-logical-CPU ratio, artifact-write wall-share,
  and processor diagnostic reasons. The discovery runner now measures
  parent-side writes for resolved specs, run state, trial records, ledgers, and
  snapshots with a truthful scope that excludes the final manifest write. This
  addresses the reported processor-utilization concern by making future
  underuse visible; it does not change execution semantics or claim a speedup.

WPR105-04 implementation note:

- `WPR105-04-blocked-artifact-directory-suppression` reduced filesystem
  pressure for no-candidate `interesting_only` discovery sweeps by stopping
  eager creation of empty `trial_artifacts/<trial_id>/<attempt_id>`
  directories before real-discovery trial evaluation. Durable JSON trial
  records, ledgers, scoring, gates, and persisted artifact behavior for
  `persist_trial_artifacts: all` or interesting candidates are unchanged. This
  is a bounded artifact-pressure cleanup, not a processor-parallel speedup
  claim.

WPR105-99 implementation note:

- `WPR105-99-final-crosscheck-performance-validation` fixed final crosscheck
  findings and ran full validation. Historical benchmark report byte
  self-accounting now reconciles to the final file size, R105 component
  factory hashing now uses the shared artifact-key helpers consistently, secure
  handoff excludes no longer omit normal `artifact_keys.py` source/test files,
  a tracked sanitized postmortem summary records ignored local generated
  evidence, and discovery benchmark run payloads expose compact
  `discovery-compute-telemetry-v2` utilization diagnostics. Full pytest passed
  with `1374 passed, 1 skipped`; discovery and historical benchmark gates both
  passed with complete evidence. `ISSUE-R104-001` remains open.

WPR105-100 implementation note:

- `WPR105-100-hardware-utilization-study-readiness` added a research-only
  `benchmark-hardware-utilization` CLI command, local CPU process-pool
  saturation probe, optional CuPy/CUDA matrix-throughput probe, live-rejected
  command registry entry, operator job route, artifact indexing, and Research
  UI controls/status cards. The local RTX 5070 Ti CUDA probe executed
  successfully; the CPU auto path selected the detected physical-core count
  and reached worker-capacity saturation while explicit logical-worker
  oversubscription stayed below target. This is diagnostic prolonged-study
  readiness evidence, not a production speedup, live-readiness, profitability,
  or candidate-ready claim. `ISSUE-R104-001` remains open.

WPR105-101 implementation note:

- `WPR105-101-final-code-audit-hardware-ui-polish` closed final audit findings
  for the hardware-utilization path. Windows spawned process-pool workers no
  longer build the ASGI app through `__mp_main__`, direct CLI inputs now share
  bounded duration/matrix-size guardrails with the operator route, prolonged
  CPU-study readiness is tied to worker-capacity saturation rather than probe
  completion alone, CuPy failure paths release memory pools best-effort, and
  the Research tab shows worker-capacity versus logical-capacity status
  separately. Artifact indexing now uses one pruned manifest walk instead of
  repeated broad recursive scans through trial artifacts, snapshots, raw data,
  and caches. Full pytest passed with `1388 passed, 1 skipped`; the local
  hardware audit run reached `93.453006%` worker-capacity CPU utilization and
  executed the CUDA probe. No live, promotion, candidate-ready, or speedup
  claim is made. `ISSUE-R104-001` remains open.

WPR105-102 implementation note:

- `WPR105-102-research-ui-required-workflow-clarity` reworked the operator
  Research tab so the Required Evidence Checklist is explicitly the only
  required run path. Required action buttons now sit at the top, manual
  required presets are separated from optional diagnostics, and provider
  pipeline diagnostics, HMM/KNN experiments, hardware probes, and legacy
  compatibility controls are secondary. Stale operator-facing R104 headings
  were removed while internal R104 spec paths remain reference-only. Browser
  smoke covered desktop and 390px mobile layout with diagnostics open and no
  page-level horizontal overflow. No live, promotion, candidate-ready,
  scoring, or execution-semantic behavior changed. `ISSUE-R104-001` remains
  open.

WPR105-103 implementation note:

- `WPR105-103-research-chart-readability-and-next-action` fixed the Research
  tab graph section after operator review. Required evidence charts now prefer
  required durable historical-cycle and exact durable discovery artifacts and
  exclude diagnostic, smoke, compatibility, and benchmark cycles from the
  primary chart view. Canvas charts now use readable horizontal labels and
  values instead of tiny rotated axis labels. Browser smoke confirmed desktop
  and 390px mobile rendering with no console errors or page-level horizontal
  overflow, and the required profitability chart selected
  `r104-btcusdt-durable-public-archive-deep-v1` instead of the benchmark-small
  cycle. No live, promotion, candidate-ready, scoring, or execution-semantic
  behavior changed. `ISSUE-R104-001` remains open.

WPR105-104 implementation note:

- `WPR105-104-required-discovery-wiring-snapshot-and-utilization` hardened the
  required discovery workflow after operator review. Durable readiness is now
  split into fixture-integrity readiness and candidate-depth readiness, so the
  checked BTC/ETH 32-bar compact fixture packs show as screening-only instead
  of completing required evidence. Required progress no longer completes from
  stale/minimal/simple artifacts, exact durable discovery jobs use a stable
  run-id output directory with auto-resume from existing `run_state.json`, and
  the Research UI exposes active discovery completed-trial count, rate, ETA,
  run_state, and latest snapshot. Exact BTC/ETH discovery configs now request
  the new process-pool executor so prolonged exact sweeps can use multiple CPU
  cores rather than the prior thread-only path. No live, promotion,
  candidate-pack-write, runtime-mode, order-placement, or sizing behavior was
  added. `ISSUE-R104-001` remains open for expanded durable data before any
  candidate-ready claim.

WPR105-105 implementation note:

- `WPR105-105-durable-depth-blocker-ui-clarity` clarified the operator-visible
  durable data-depth block. The Required Evidence Checklist now states that a
  data-depth block cannot be unblocked by a compute run, the blocked readiness
  milestone uses `Show Data Gap` instead of a dead-looking disabled `Run`
  button, and blocked/waiting milestone actions render as `Data Required` or
  `Waiting`. Readiness feedback points the operator to the real unblock path:
  add expanded BTC/ETH durable historical fixture packs and updated readiness
  hashes, then rerun readiness. No gates were weakened and no live, promotion,
  candidate-pack-write, runtime-mode, order-placement, or sizing behavior was
  added. `ISSUE-R104-001` remains open.

WPR105-106 implementation note:

- `WPR105-106-durable-data-acquisition-step0` adds the missing runnable data
  acquisition path before durable readiness. The new `collect-durable-data`
  CLI/operator job downloads Binance Vision BTCUSDT/ETHUSDT monthly 15m, 1m,
  and aggTrades archives, verifies `.CHECKSUM` sidecars, rejects source gaps or
  duplicate bars, preserves compact checked fixtures, writes generated
  research-only candidate-depth fixture packs, and emits active readiness,
  historical-cycle, exact-discovery, and collection-summary manifests. The
  Research UI required checklist now starts with Step 0 and downstream BTC/ETH
  buttons use active generated specs when present. Step 0 is the default
  public-archive route, not the only possible provider route: Crypto Lake/local
  vendor exports and registered Hyperliquid archive surfaces remain provider
  diagnostics until their outputs are converted into the same validated
  fixture/spec contract. No live, promotion, candidate-pack-write,
  runtime-mode, order-placement, or sizing behavior was added.
  `ISSUE-R104-001` remains open until full collection plus downstream cycles,
  exact sweeps, and eligibility review complete.

WPR105-107 implementation note:

- `WPR105-107-bybit-hyperliquid-provider-surface-audit` registers
  `bybit_archive` as a diagnostic-only, registered-only provider surface and
  keeps `hyperliquid_archive` explicitly registered-only until local archive
  ingestion plus account-journal reconciliation are implemented. Provider
  diagnostics and docs now distinguish implementation states: Binance Vision
  Step 0 is the default implemented public-archive route, Crypto Lake local
  export ingestion is implemented for supported exports, and Bybit/Hyperliquid
  archives are visible but not candidate-depth fixture sources yet. No live,
  promotion, candidate-pack-write, runtime-mode, order-placement, or sizing
  behavior was added.

## Open work packets

| Packet | Owner | Status | Paths | Exit evidence |
| --- | --- | --- | --- | --- |
| WPR106-46-exact-replay-overlay-domain-and-cycle | Codex Research Agent | closed | `docs/work_packets/WPR106-46-exact-replay-overlay-domain-and-cycle.md`, `docs/work_packets/WPR106-46-progress.jsonl`, `docs/stage_reports/STAGE_R106_EXACT_REPLAY_OVERLAY_DOMAIN_AND_CYCLE_REPORT.md`, `docs/ACTIVE_INDEX.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `src/tradingbotsuite/**`, `tests/**` | Option A exact replay-overlay implementation: explicit `1h` and replay-domain strategy support, exact singleton spec drafts for 48/48 WPR106-31 replay leads, bounded BTC/ETH cycle smokes with overlay provenance in rankings/backtest/gates, zero pack-eligible rows, no candidate packs, full validation passed, `ISSUE-R104-001` kept open, and no live/paper/order/sizing/promotion authorization. |
| WPR106-45-replay-overlay-preflight-contract | Codex Research Agent | closed | `docs/work_packets/WPR106-45-replay-overlay-preflight-contract.md`, `docs/work_packets/WPR106-45-progress.jsonl`, `src/tradingbotsuite/research_discovery/replay_overlay_preflight.py`, `src/tradingbotsuite/research_discovery/__init__.py`, `tests/research_discovery/test_replay_overlay_preflight.py`, `docs/ACTIVE_INDEX.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_REPLAY_OVERLAY_PREFLIGHT_CONTRACT_REPORT.md` | Reusable exact replay-overlay preflight utility, manifest validator, focused contract tests, BTC/ETH WPR106-31 preflight rerun with 48/48 unrepresentable exact replay leads, 48 prediction artifacts and manifests found, 0 overlay specs, 0 candidate packs, and passing compile/research-discovery/contracts/diff validation recorded in `docs/stage_reports/STAGE_R106_REPLAY_OVERLAY_PREFLIGHT_CONTRACT_REPORT.md`. |
| WPR106-41-config-schema-roundtrip-validation | Codex Research Agent | closed | `docs/work_packets/WPR106-41-config-schema-roundtrip-validation.md`, `docs/work_packets/WPR106-41-progress.jsonl`, `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_discovery/spec.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/research_discovery/test_discovery_spec.py`, `docs/ACTIVE_INDEX.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_CONFIG_SCHEMA_ROUNDTRIP_VALIDATION_REPORT.md` | Versioned schema summaries, fail-closed wrong-version and unknown active-field rejection for historical-cycle/discovery-run specs, parser roundtrip tests, and passing compile/focused research-cycle/discovery/contracts/discovery-parser/diff validation recorded in `docs/stage_reports/STAGE_R106_CONFIG_SCHEMA_ROUNDTRIP_VALIDATION_REPORT.md`. |
| WPR106-40-venue-aware-cost-fill-profiles | Codex Research Agent | closed | `docs/work_packets/WPR106-40-venue-aware-cost-fill-profiles.md`, `docs/work_packets/WPR106-40-progress.jsonl`, `src/tradingbotsuite/backtesting/costs.py`, `src/tradingbotsuite/backtesting/__init__.py`, `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/backtesting/vector_engine.py`, `src/tradingbotsuite/backtesting/cuda_engine.py`, `src/tradingbotsuite/backtesting/cuda_batched_engine.py`, `src/tradingbotsuite/research_cycle/runner.py`, `tests/contracts/test_backtest_contracts.py`, `tests/historical/test_full_cycle_synthetic.py`, `docs/ACTIVE_INDEX.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_VENUE_AWARE_COST_FILL_PROFILES_REPORT.md` | Venue-aware registered research cost/fill profiles, explicit historical-research-only execution-proof scope, cost/fill profile metadata in backtest manifests/cache identity/backtest-index rows/cost-stress rows, required stress scenario set preserved, and passing compile/focused backtest/unit/synthetic/contracts/candidate-pack/diff validation recorded in `docs/stage_reports/STAGE_R106_VENUE_AWARE_COST_FILL_PROFILES_REPORT.md`. |
| WPR106-39-regime-backend-semantics | Codex Research Agent | closed | `docs/work_packets/WPR106-39-regime-backend-semantics.md`, `docs/work_packets/WPR106-39-progress.jsonl`, `src/tradingbotsuite/research_discovery/hmm_materialization.py`, `src/tradingbotsuite/research_discovery/spec.py`, `src/tradingbotsuite/research_discovery/knn_study.py`, `src/tradingbotsuite/research_discovery/runner.py`, `src/tradingbotsuite/research_discovery/manifests.py`, `src/tradingbotsuite/research_discovery/artifact_keys.py`, `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`, `tests/research_discovery/test_hmm_materialization.py`, `tests/research_discovery/test_discovery_spec.py`, `tests/research_discovery/test_knn_study.py`, `tests/research_discovery/test_discovery_runner.py`, `tests/research_discovery/test_artifact_keys.py`, `docs/ACTIVE_INDEX.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_REGIME_BACKEND_SEMANTICS_REPORT.md` | Active discovery GMM/no-regime backend evidence now carries explicit `regime_model_backend`, ledgers/run manifests/artifact identity preserve backend truthfulness, canonical `regime_*` aliases sit beside legacy `hmm_*` compatibility fields, and passing compile/focused discovery/contracts/diff validation recorded in `docs/stage_reports/STAGE_R106_REGIME_BACKEND_SEMANTICS_REPORT.md`. |
| WPR106-38-mode-aware-artifact-runtime-validation | Codex Research Agent | closed | `docs/work_packets/WPR106-38-mode-aware-artifact-runtime-validation.md`, `docs/work_packets/WPR106-38-progress.jsonl`, `src/tradingbotsuite/promotion/artifact_validator.py`, `src/tradingbotsuite/promotion/__init__.py`, `src/tradingbotsuite/live/preflight.py`, `src/tradingbotsuite/live/shadow_loader.py`, `src/tradingbotsuite/runtime.py`, `tests/live/test_reject_research_artifacts.py`, `tests/live/test_promotion_candidate_validator.py`, `tests/live/test_shadow_loader.py`, `tests/research_artifacts/test_candidate_pack.py`, `docs/ACTIVE_INDEX.md`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_MODE_AWARE_ARTIFACT_RUNTIME_VALIDATION_REPORT.md` | Mode-aware fail-closed artifact runtime validation, live preflight and runtime dispatch validation before scorer/shadow-loader construction, explicit shadow runtime declarations, `ISSUE-R106-014` resolved, active P0 count reduced to zero, and passing compile/focused live/artifact/candidate-pack/contracts/diff validation recorded in `docs/stage_reports/STAGE_R106_MODE_AWARE_ARTIFACT_RUNTIME_VALIDATION_REPORT.md`. |
| WPR106-37-explicit-hyperliquid-live-enable | Codex Research Agent | closed | `docs/work_packets/WPR106-37-explicit-hyperliquid-live-enable.md`, `docs/work_packets/WPR106-37-progress.jsonl`, `src/tradingbotsuite/config.py`, `tests/test_config.py`, `tests/tradingbotsuite/test_config.py`, `tests/live/test_preflight.py`, `docs/ACTIVE_INDEX.md`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_EXPLICIT_HYPERLIQUID_LIVE_ENABLE_REPORT.md` | Hyperliquid credential-file parsing is passive for signer/account/endpoint data, explicit `TBS_HL_ENABLE_LIVE=true` is required for enablement, file credentials without explicit enable fail live preflight, `ISSUE-R106-013` resolved, and passing compile/focused config-live/contracts/diff validation recorded in `docs/stage_reports/STAGE_R106_EXPLICIT_HYPERLIQUID_LIVE_ENABLE_REPORT.md`. |
| WPR106-36-lower-timeframe-entry-pricing | Codex Research Agent | closed | `docs/work_packets/WPR106-36-lower-timeframe-entry-pricing.md`, `docs/work_packets/WPR106-36-progress.jsonl`, `src/tradingbotsuite/backtesting/execution_sim.py`, `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/backtesting/vector_engine.py`, `src/tradingbotsuite/backtesting/cuda_engine.py`, `src/tradingbotsuite/backtesting/cuda_batched_engine.py`, `tests/unit/test_execution_simulator.py`, `docs/ACTIVE_INDEX.md`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_LOWER_TIMEFRAME_ENTRY_PRICING_REPORT.md` | Reference simulator lower-timeframe entry fills now use lower-timeframe open at or after latency target, missing coverage fails closed, trade rows record entry proof metadata, accelerated primary-bar paths preserve metadata parity while still rejecting lower-timeframe entry sources, `ISSUE-R106-012` resolved, and passing compile/unit/backtesting/contracts/diff validation recorded in `docs/stage_reports/STAGE_R106_LOWER_TIMEFRAME_ENTRY_PRICING_REPORT.md`. |
| WPR106-35-label-event-end-aware-purge | Codex Research Agent | closed | `docs/work_packets/WPR106-35-label-event-end-aware-purge.md`, `src/tradingbotsuite/backtesting/splits.py`, `src/tradingbotsuite/features/split_transforms.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_discovery/runner.py`, `src/tradingbotsuite/research_discovery/hmm_materialization.py`, `src/tradingbotsuite/research_discovery/knn_study.py`, `tests/backtesting/test_splits.py`, `tests/features/test_feature_builders.py`, `tests/research_discovery/test_hmm_materialization.py`, `tests/research_discovery/test_discovery_runner.py`, `tests/historical/test_full_cycle_synthetic.py`, `docs/ACTIVE_INDEX.md`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_LABEL_EVENT_END_AWARE_PURGE_REPORT.md` | `LabelSpec` event-end-aware split purge, compact train-index split-manifest evidence, discovery label event-end stamping, HMM/KNN/train-only consumers honoring explicit event-safe training rows, historical-cycle split purge evidence, `ISSUE-R106-011` resolved, and passing compile/focused backtesting/features/research-discovery/historical/contracts/diff validation recorded in `docs/stage_reports/STAGE_R106_LABEL_EVENT_END_AWARE_PURGE_REPORT.md`. |
| WPR106-34-fail-closed-synthetic-source-selection | Codex Research Agent | closed | `docs/work_packets/WPR106-34-fail-closed-synthetic-source-selection.md`, `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_cycle/runner.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `docs/ACTIVE_INDEX.md`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_FAIL_CLOSED_SYNTHETIC_SOURCE_SELECTION_REPORT.md` | `synthetic_fallback_allowed` contract parsing, no-source synthetic fallback removed, explicit synthetic test/demo/benchmark scope, synthetic-plus-real-source rejection, ambiguous `local_fixture_dir` rejection, required `source_selection_manifest`, `ISSUE-R106-010` resolved, and passing compile/focused historical/contracts/diff validation recorded in `docs/stage_reports/STAGE_R106_FAIL_CLOSED_SYNTHETIC_SOURCE_SELECTION_REPORT.md`. |
| WPR106-33-ci-reproducible-research-install | Codex Research Agent | closed | `docs/work_packets/WPR106-33-ci-reproducible-research-install.md`, `.github/workflows/research-validation.yml`, `README.md`, `docs/ACTIVE_INDEX.md`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_CI_REPRODUCIBLE_RESEARCH_INSTALL_REPORT.md` | Clean Python 3.11 GitHub Actions baseline for editable `.[dev]` install, `pip check`, compile, contracts, and focused live/artifact boundary tests; `ISSUE-R106-009` resolved; local compile/contracts/live-boundary/workflow YAML/diff validation recorded in `docs/stage_reports/STAGE_R106_CI_REPRODUCIBLE_RESEARCH_INSTALL_REPORT.md`. |
| WPR106-32-active-index-research-identity | Codex Research Agent | closed | `docs/work_packets/WPR106-32-active-index-research-identity.md`, `docs/ACTIVE_INDEX.md`, `START_HERE.md`, `README.md`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/STAGE_R106_ACTIVE_INDEX_RESEARCH_IDENTITY_REPORT.md` | Active index and identity clarification, newly registered P0 stop-condition issues, current `main` checkout/migrated R106 mirror guidance, no source/config/data/live behavior changes, and baseline validation recorded in `docs/stage_reports/STAGE_R106_ACTIVE_INDEX_RESEARCH_IDENTITY_REPORT.md`. |
| WPR106-31-discovery-lead-replay-entry-evidence | Codex Research Agent | closed | `docs/work_packets/WPR106-31-discovery-lead-replay-entry-evidence.md`, `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_REPLAY_ENTRY_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `src/tradingbotsuite/research_discovery/discovery_lead_replay.py`, `src/tradingbotsuite/research_discovery/spec.py`, `src/tradingbotsuite/research_discovery/runner.py`, `src/tradingbotsuite/research_discovery/__init__.py`, `tests/research_discovery/test_discovery_lead_replay.py`, `tests/research_discovery/test_discovery_spec.py`, `tests/research_discovery/test_discovery_runner.py` | Replay-spec and entry-signal evidence lane, `predictions_only` discovery artifact policy, 24/24 BTC and 24/24 ETH replay trials completed, 969,870 BTC and 957,643 ETH annotated entry signals across 24 candidates per symbol, bounded top-3 exit-lab slices blocked by no improvement over fixed holding, no ranking/pack/promotion claim, and passing compile/research-discovery/contracts/candidate-pack/diff validation recorded in `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_REPLAY_ENTRY_EVIDENCE_REPORT.md`. |
| WPR106-30-discovery-lead-materialization-lane | Codex Research Agent | closed | `docs/work_packets/WPR106-30-discovery-lead-materialization-lane.md`, `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_MATERIALIZATION_LANE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `src/tradingbotsuite/research_discovery/discovery_lead_materialization.py`, `src/tradingbotsuite/research_discovery/__init__.py`, `tests/research_discovery/test_discovery_lead_materialization.py` | Descriptor-only discovery-lead materialization lane, 24 BTC and 24 ETH hash-backed materialized descriptors, source trial/signature preservation, explicit downstream gate requirements, no ranking/pack/promotion claim, and passing compile/research-discovery/contracts/candidate-pack validation recorded in `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_MATERIALIZATION_LANE_REPORT.md`. |
| WPR106-29-candidate-rejection-root-cause-and-gate-materialization | Codex Research Agent | closed | `docs/work_packets/WPR106-29-candidate-rejection-root-cause-and-gate-materialization.md`, `docs/stage_reports/STAGE_R106_CANDIDATE_REJECTION_ROOT_CAUSE_AND_GATE_MATERIALIZATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`, `src/tradingbotsuite/research_discovery/multiple_testing.py`, `tests/research_discovery/test_candidate_pack_bridge.py`, `tests/research_discovery/test_multiple_testing.py` | BTC/ETH gate materialization and bridge rerun show 0 discovery-to-cycle ranking overlap, 22,560 BTC and 23,040 ETH blocked research-only rows, capped rejection Markdown, explicit manifest reason counts/alignment, no candidate pack, no promotion claim, and passing compile/contracts/research-discovery/candidate-pack/UI validation recorded in `docs/stage_reports/STAGE_R106_CANDIDATE_REJECTION_ROOT_CAUSE_AND_GATE_MATERIALIZATION_REPORT.md`. |
| WPR106-23-btc-eth-perp-strategy-knowledge-ingest | Codex Research Agent | closed | `docs/work_packets/WPR106-23-btc-eth-perp-strategy-knowledge-ingest.md`, `docs/stage_reports/STAGE_R106_BTC_ETH_PERP_STRATEGY_KNOWLEDGE_INGEST_REPORT.md`, `docs/research_knowledge/**`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `START_HERE.md` | External BTC/ETH perp strategy report imported as full source plus detailed research knowledge base, with strategy taxonomy, feature/data requirements, simulator standards, ML guidance, falsification checks, and red-team cautions cataloged as hypothesis knowledge only. |
| WPR106-22-catalog-handoff-portability | Codex Research Agent | closed | `docs/work_packets/WPR106-22-catalog-handoff-portability.md`, `docs/stage_reports/STAGE_R106_CATALOG_HANDOFF_PORTABILITY_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `src/tradingbotsuite/data/historical_data_catalog.py`, `src/tradingbotsuite/operator_console.py`, `tests/tradingbotsuite/test_market_data_collection.py`, `tests/tradingbotsuite/test_operator_ui.py` | Migrated catalog/spec path rebasing, operator isolated spec path normalization, `ISSUE-R106-003` resolution, compile, market-data collection tests, operator UI tests, and contracts recorded in `docs/stage_reports/STAGE_R106_CATALOG_HANDOFF_PORTABILITY_REPORT.md`. |
| WPR106-21-full-repo-data-code-crosscheck | Codex Research Agent | closed | `docs/work_packets/WPR106-21-full-repo-data-code-crosscheck.md`, `docs/stage_reports/STAGE_R106_FULL_REPO_DATA_CODE_CROSSCHECK_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Full repo data/code crosscheck on migrated `main`, active catalog/fixture validation, provider surface classification, static boundary/performance scans, `ISSUE-R106-003` registration, compile, contracts, research-discovery, historical, research-artifacts, and live tests recorded in `docs/stage_reports/STAGE_R106_FULL_REPO_DATA_CODE_CROSSCHECK_REPORT.md`. |
| WPR106-20-performance-speedups-and-ui-wiring | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/research_discovery/**`, `tests/tradingbotsuite/test_operator_ui.py` | Observed artifact accounting, finalization/process timing telemetry, placeholder process-context avoidance, performance-study artifact indexing, operator UI performance wiring, compile, contracts, full research-discovery tests, and full operator UI tests recorded in `docs/stage_reports/STAGE_R106_PERFORMANCE_SPEEDUPS_AND_UI_WIRING_REPORT.md`. |
| WPR106-19-long-performance-utilization-study | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `data/research/operator_runs/performance_utilization_wpr106_19/**` | Second long performance/utilization study, hardware utilization evidence, historical-cycle provider latest-month benchmark, BTC candidate-depth exact-discovery probe, final artifact rebuild evidence, and safe speedup targets recorded in `docs/stage_reports/STAGE_R106_LONG_PERFORMANCE_UTILIZATION_STUDY_REPORT.md`. |
| WPR106-18-operator-autopilot-crash-retry-hardening | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/operator_console.py`, `tests/tradingbotsuite/test_operator_ui.py` | Bounded autopilot step retries, attempt-specific helper job IDs, exact-discovery resume-preserving retries, one-time stale-autopilot restart requeueing, focused tests, operator UI tests, contracts, and full pytest recorded in `docs/stage_reports/STAGE_R106_OPERATOR_AUTOPILOT_CRASH_RETRY_HARDENING_REPORT.md`. |
| WPR106-17-final-crosscheck-robustness | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/contracts/boundary_contract.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/research_discovery/frozen_entry_exit_lab.py`, `src/tradingbotsuite/web/**`, `tests/research_discovery/test_frozen_entry_exit_lab.py`, `tests/tradingbotsuite/test_operator_ui.py` | Final robustness crosscheck, frozen-entry exit-lab fail-closed malformed input handling, candidate-eligibility service path/root/symbol/manifest validation, two-phase autopilot prerequisite ordering, focused tests, contracts, and full pytest recorded in `docs/stage_reports/STAGE_R106_FINAL_CROSSCHECK_ROBUSTNESS_REPORT.md`. |
| WPR106-16-research-workflow-completion | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/backtesting/**`, `src/tradingbotsuite/data/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/web/**`, `tests/backtesting/**`, `tests/research_discovery/**`, `tests/tradingbotsuite/test_operator_ui.py` | Modern-window profile artifacts, `simple_runner_v1`, run-to-run delta artifacts, bridge-compatible frozen-entry exit lab, operator/autopilot/UI sequencing through eligibility, focused tests, contracts, and full pytest recorded in `docs/stage_reports/STAGE_R106_RESEARCH_WORKFLOW_COMPLETION_REPORT.md`. |
| WPR106-15-operator-research-autopilot-sequencer | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py` | One-button operator research autopilot sequencer, reusable artifact skipping, bounded direct helper execution, autopilot manifest indexing, blocked-prerequisite reporting, focused UI/operator tests, compile, and contracts recorded in `docs/stage_reports/STAGE_R106_OPERATOR_RESEARCH_AUTOPILOT_SEQUENCER_REPORT.md`. |
| WPR106-14-operator-analysis-job-and-required-workflow | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py` | Operator analysis job route, research-analysis artifact indexing, required checklist analysis milestone before eligibility, path allowlist/job/artifact/progress tests, focused analysis tests, compile, and contracts recorded in `docs/stage_reports/STAGE_R106_OPERATOR_ANALYSIS_JOB_REQUIRED_WORKFLOW_REPORT.md`. |
| WPR106-05-completed-catalog-wiring-validation | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/persistence/sqlite_store.py`, `src/tradingbotsuite/web/**`, `tests/tradingbotsuite/test_operator_ui.py` | Completed catalog validation, active catalog spec wiring, generated candidate-depth ID recognition, stale running job recovery, provider-quality review, focused tests, contracts, and full pytest recorded in `docs/stage_reports/STAGE_R106_COMPLETED_CATALOG_WIRING_VALIDATION_REPORT.md`. |
| WPR106-04-historical-refresh-long-network-outage-tolerance | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/research/market_data.py`, `tests/tradingbotsuite/test_market_data_collection.py` | Long DNS/VPN outage tolerance for Binance Vision refreshes, env-tunable retry/backoff defaults, retry-budget manifest evidence, DNS-shaped retry and checksum fail-fast tests, contracts, and full pytest recorded in `docs/stage_reports/STAGE_R106_HISTORICAL_REFRESH_LONG_NETWORK_OUTAGE_TOLERANCE_REPORT.md`. |
| WPR106-03-historical-refresh-transient-network-continuation | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/config.py`, `src/tradingbotsuite/core/engine.py`, `src/tradingbotsuite/data/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/research/market_data.py`, `tests/tradingbotsuite/**` | Transient Binance Vision fetch retry, completed per-symbol fixture-pack reuse, retry manifest evidence, optional market-stream suppression for research server runs, focused tests, contracts, and full pytest recorded in `docs/stage_reports/STAGE_R106_HISTORICAL_REFRESH_TRANSIENT_NETWORK_CONTINUATION_REPORT.md`. |
| WPR106-02-historical-data-refresh-resume-hardening | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/data/**`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/persistence/sqlite_store.py`, `src/tradingbotsuite/research/market_data.py`, `src/tradingbotsuite/web/**`, `tests/tradingbotsuite/**` | Central verified archive cache, prior partial-download fallback, progress/ETA journal, streamed Parquet generation, SQLite job-log race hardening, aggTrade order-anomaly handling, focused tests, contracts, and full pytest recorded in `docs/stage_reports/STAGE_R106_HISTORICAL_DATA_REFRESH_RESUME_HARDENING_REPORT.md`. |
| WPR106-01-central-historical-data-catalog | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/data/**`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/research/**`, `src/tradingbotsuite/web/**`, `tests/**` | R106 historical-data catalog source of truth, provider state registry, active fixture/spec path wiring, UI checklist Step 0 replacement, and validation recorded in `docs/stage_reports/STAGE_R106_CENTRAL_HISTORICAL_DATA_CATALOG_REPORT.md`. |
| WPR105-107-bybit-hyperliquid-provider-surface-audit | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/contracts/**`, `docs/tradingbotsuite_runtime/**`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/data/**`, `src/tradingbotsuite/research/archive_sources.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/contracts/**`, `tests/tradingbotsuite/**` | Bybit registered-only provider surface, Hyperliquid registered-only status clarified, provider diagnostics/docs wording, focused validation, and no ingestion or promotion claim recorded in `docs/stage_reports/STAGE_R105_BYBIT_HYPERLIQUID_PROVIDER_SURFACE_AUDIT_REPORT.md`. |
| WPR105-106-durable-data-acquisition-step0 | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/contracts/boundary_contract.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/data/**`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/research/command_registry.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/**` | Runnable Step 0 durable data collection pipeline, checksum/source-quality validation, generated candidate-depth fixture packs and active specs, Research UI required-checklist wiring, focused validation, and no live or promotion claim recorded in `docs/stage_reports/STAGE_R105_DURABLE_DATA_ACQUISITION_STEP0_REPORT.md`. |
| WPR105-105-durable-depth-blocker-ui-clarity | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py` | Durable data-depth blocked UX now says this is a data-acquisition requirement, not a runnable compute step; blocked action labels clarified; focused UI tests recorded in `docs/stage_reports/STAGE_R105_DURABLE_DEPTH_BLOCKER_UI_CLARITY_REPORT.md`. |
| WPR105-104-required-discovery-wiring-snapshot-and-utilization | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `configs/discovery/**`, `configs/research/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `src/tradingbotsuite/research_discovery/**`, `tests/tradingbotsuite/test_operator_ui.py`, `tests/research_discovery/**`, `tests/contracts/**` | Candidate-depth readiness split, stale artifact completion blocking, stable exact-discovery run-id output, auto-resume, progress/ETA UI, process-pool exact sweep executor, focused tests, and validation recorded in `docs/stage_reports/STAGE_R105_REQUIRED_DISCOVERY_WIRING_SNAPSHOT_AND_UTILIZATION_REPORT.md`. |
| WPR105-103-research-chart-readability-and-next-action | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py` | Required evidence chart readability, benchmark/diagnostic cycle exclusion from primary graphs, focused UI test, contracts, browser smoke, and validation recorded in `docs/stage_reports/STAGE_R105_RESEARCH_CHART_READABILITY_AND_NEXT_ACTION_REPORT.md`. |
| WPR105-102-research-ui-required-workflow-clarity | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py` | Research UI required-checklist clarity, secondary diagnostics/legacy separation, stale operator-facing R104 heading removal, mobile overflow polish, focused UI test, contracts, browser smoke, and validation recorded in `docs/stage_reports/STAGE_R105_RESEARCH_UI_REQUIRED_WORKFLOW_CLARITY_REPORT.md`. |
| WPR105-101-final-code-audit-hardware-ui-polish | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/**`, `tests/**` | Final hardware/UI audit fixes, bounded direct CLI validation, Windows process-pool app-construction guard, worker/logical CPU status separation, pruned artifact index scan, browser UI smoke, focused tests, contracts, full pytest, and hardware audit benchmark recorded in `docs/stage_reports/STAGE_R105_FINAL_CODE_AUDIT_HARDWARE_UI_POLISH_REPORT.md`. |
| WPR105-100-hardware-utilization-study-readiness | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/contracts/**`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/**`, `tests/**` | Research-only hardware benchmark command, CPU process-pool saturation diagnostics, CuPy/CUDA matrix probe, operator route/job/artifact/UI wiring, local RTX 5070 Ti evidence, full pytest, discovery and historical benchmark gates, and no live or promotion claim recorded in `docs/stage_reports/STAGE_R105_HARDWARE_UTILIZATION_STUDY_READINESS_REPORT.md`. |
| WPR105-99-final-crosscheck-performance-validation | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `configs/**`, `src/tradingbotsuite/**`, `tests/**` | Final R105 crosscheck fixes, full pytest, discovery benchmark gate, historical-cycle benchmark gate, tracked postmortem summary, benchmark telemetry exposure, and no candidate-ready claim recorded in `docs/stage_reports/STAGE_R105_FINAL_CROSSCHECK_PERFORMANCE_VALIDATION_REPORT.md`. |
| WPR105-04-blocked-artifact-directory-suppression | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/research_discovery/runner.py`, `tests/research_discovery/**`, `tests/contracts/**` | Blocked `interesting_only` real-discovery trials no longer leave empty trial artifact directories; focused and broad validation passed; no scoring, ledger, candidate-gate, or live behavior changes recorded in `docs/stage_reports/STAGE_R105_BLOCKED_ARTIFACT_DIRECTORY_SUPPRESSION_REPORT.md`. |
| WPR105-03-discovery-processor-utilization-telemetry | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/research_discovery/runner.py`, `src/tradingbotsuite/research_discovery/telemetry.py`, `tests/research_discovery/**`, `tests/contracts/**` | Discovery compute telemetry v2 with worker/logical CPU capacity utilization, nested processor diagnostics, parent-side artifact write timing for resolved spec/state/trial/ledger/snapshot writes, focused and broad validation, and no execution-semantic or speedup claim recorded in `docs/stage_reports/STAGE_R105_DISCOVERY_PROCESSOR_UTILIZATION_TELEMETRY_REPORT.md`. |
| WPR105-02-secure-handoff-export-hygiene | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `configs/handoff/**`, `tests/contracts/**` | Secure R105 handoff/export config with security checks, conservative include/exclude patterns, research-only metadata, contract coverage, and validation recorded in `docs/stage_reports/STAGE_R105_SECURE_HANDOFF_EXPORT_HYGIENE_REPORT.md`. |
| WPR105-01-latest-sweep-postmortem-effective-trials | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/research_discovery/**`, `tests/research_discovery/**`, `tests/contracts/**`, `data/research/operator_runs/r105/**` | R105 artifact keys and postmortem command, completed R104 exact-sweep derived postmortem artifacts, effective-trial and ledger-signature clustering, no-candidate/no-promotion issue status, and validation recorded in `docs/stage_reports/STAGE_R105_R104_POSTMORTEM_EFFECTIVE_TRIAL_DEDUPE_REPORT.md`. |
| WPR104-06-exit-entry-orderflow-research-handoff | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `docs/KNOWN_ISSUES.md` | Completed BTCUSDT exact-sweep postmortem, zero-lead interpretation, exit/entry/orderflow/KNN/regime/filter falsification plan, separate research-model handoff prompt, and validation recorded in `docs/stage_reports/STAGE_R104_EXIT_ENTRY_ORDERFLOW_RESEARCH_HANDOFF.md`. |
| WPR104-05-discovery-search-feature-crosscheck | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `configs/discovery/**`, `src/tradingbotsuite/research_discovery/**`, `tests/contracts/**`, `tests/features/**`, `tests/research_discovery/**`, `tests/tradingbotsuite/test_operator_ui.py` | Exact R104 sweep dimension and uniqueness regressions, duplicate dimension fail-closed validation, parameter-stable discovery candidate IDs, compact-fixture effective feature pruning, score-policy versioning for changed feature semantics, KNN payload/failure audit coverage, durable feature preflight checks, and validation recorded in `docs/stage_reports/STAGE_R104_DISCOVERY_SEARCH_FEATURE_CROSSCHECK_REPORT.md`. |
| WPR104-04-durable-bruteforce-run-hardening | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `configs/discovery/**`, `configs/research/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/contracts/**`, `tests/research_discovery/**`, `tests/tradingbotsuite/test_operator_ui.py` | R104 exact bounded discovery profiles, deeper durable cycle configs, manifest search-space coverage metadata, bounded disk-artifact progress indexing, UI deep/exact operation path, compact-fixture blocker issue, browser layout checks, and validation recorded in `docs/stage_reports/STAGE_R104_DURABLE_BRUTEFORCE_RUN_HARDENING_REPORT.md`. |
| WPR104-03-operator-console-usability-hardening | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/persistence/sqlite_store.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `src/tradingbotsuite/web/templates/timeline.html`, `tests/tradingbotsuite/test_operator_ui.py`, `tests/contracts/**` | Backend-derived R104 progress API, command-center progress meter/function blocks/defaults, evidence-state milestone ordering, timeline job status/symbol hardening, responsive UI verification, and validation recorded in `docs/stage_reports/STAGE_R104_OPERATOR_CONSOLE_USABILITY_HARDENING_REPORT.md`. |
| WPR104-02-gap-aware-durable-cycle-feature-materialization | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `src/tradingbotsuite/features/builders.py`, `src/tradingbotsuite/research_cycle/runner.py`, `tests/features/**`, `tests/historical/**`, `tests/contracts/**` | Gap-aware segmented feature materialization for intentional R104 multi-window fixture cycles, duplicate/short-interval regressions, failed BTC operator spec rerun successfully, and validation recorded in `docs/stage_reports/STAGE_R104_GAP_AWARE_DURABLE_CYCLE_FEATURE_MATERIALIZATION_REPORT.md`. |
| WPR104-01-research-ui-durable-candidate-console | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/work_packets/**`, `docs/stage_reports/**`, `configs/research/**`, `configs/discovery/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/base.html`, `src/tradingbotsuite/web/templates/research.html`, `tests/contracts/**`, `tests/integration/test_research_ui.py`, `tests/research_discovery/**`, `tests/tradingbotsuite/test_operator_ui.py` | Durable R104 Research UI/control path, BTC/ETH durable cycle and discovery defaults, candidate-pack eligibility route/job, readiness/artifact indexing, and validation recorded in `docs/stage_reports/STAGE_R104_RESEARCH_UI_DURABLE_CANDIDATE_CONSOLE_REPORT.md`. |
| WPR103-01-durable-public-archive-fixtures | Codex Research Agent | closed | `.gitignore`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `configs/research/**`, `data/research/fixtures/btcusdt_public_archive_multi_window_v1/**`, `data/research/fixtures/ethusdt_public_archive_multi_window_v1/**`, `tests/contracts/**` | Checksum-verified BTCUSDT/ETHUSDT Binance Vision multi-window fixture packs, durable public archive readiness configs, checked-in fixture readiness tests, and validation recorded in `docs/stage_reports/STAGE_R103_DURABLE_PUBLIC_ARCHIVE_FIXTURES_REPORT.md`. |
| WPR102-01-branch-completion-implementation | Codex Research Agent | closed | `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/contracts/**`, `docs/stage_reports/**`, `docs/work_packets/**`, `pyproject.toml`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/data/**`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/research_artifacts/**`, `src/tradingbotsuite/research_discovery/**`, `tests/contracts/**`, `tests/historical/**`, `tests/live/**`, `tests/research_artifacts/**`, `tests/research_discovery/**`, `tests/tradingbotsuite/**` | Source provider capability validation, direct CLI output-root allowlisting, expanded import-boundary coverage, capability-aware readiness and candidate-pack gates, package identity cleanup, and validation recorded in `docs/stage_reports/STAGE_R102_BRANCH_COMPLETION_IMPLEMENTATION_REPORT.md`. |
| WPR101-01-branch-completion-review-orchestrator-plan | Codex Research Agent | closed | `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**` | Broad branch review, issues, weak points, completion roadmap, and validation recorded in `docs/stage_reports/STAGE_R101_BRANCH_COMPLETION_REVIEW_ORCHESTRATOR_PLAN.md`. |
| WPR100-01-provider-capability-registry | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/data/contracts.py`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `tests/contracts/test_data_contracts.py`, `tests/contracts/test_historical_fixture_pack_contract.py` | Provider capability registry, fixture metadata wiring, mismatch validation, and validation recorded in `docs/stage_reports/STAGE_R100_PROVIDER_CAPABILITY_REGISTRY_REPORT.md`. |
| WPR99-01-branch-technology-development-reference | Codex Research Agent | closed | `docs/BRANCH_TECHNOLOGY_AND_DEVELOPMENT_REFERENCE.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**` | Branch technology/development reference created and validation recorded in `docs/stage_reports/STAGE_R99_BRANCH_TECHNOLOGY_DEVELOPMENT_REFERENCE_REPORT.md`. |
| WPR98-01-research-boundary-validation-hardening | Codex Research Agent | closed | `pyproject.toml`, `README.md`, `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/contracts/boundary_contract.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/cli.py`, `src/tradingbotsuite/research/**`, `src/tradingbotsuite/research_discovery/**`, `tests/live/**`, `tests/research_discovery/**`, `tests/tradingbotsuite/**` | Research artifact boundary metadata normalization, validation-floor exit-lab gate and blocker-registry hardening, canonical console script, docs updates, and validation recorded in `docs/stage_reports/STAGE_R98_RESEARCH_BOUNDARY_VALIDATION_HARDENING_REPORT.md`. |
| WPR97-07-fastest-worker-scaling-default | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/research_cycle/**`, `tests/contracts/**`, `tests/historical/**` | Worker scaling benchmark, 48-worker default, CPU48 benchmark evidence, and validation recorded in `docs/stage_reports/STAGE_R97_FASTEST_WORKER_SCALING_DEFAULT_REPORT.md`. |
| WPR97-06-research-ui-fastest-compute-summary | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py` | Research UI compute/backend summary wiring and validation recorded in `docs/stage_reports/STAGE_R97_RESEARCH_UI_FASTEST_COMPUTE_SUMMARY_REPORT.md`. |
| WPR97-05-fastest-exact-default-polish | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/research_cycle/**`, `tests/contracts/**`, `tests/historical/**` | Fastest exact default profile, 15-worker default, default smoke, and validation recorded in `docs/stage_reports/STAGE_R97_FASTEST_EXACT_DEFAULT_POLISH_REPORT.md`. |
| WPR97-04-throughput-default-and-tensorcore-dependency | Codex Research Agent | closed | `pyproject.toml`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/research_cycle/**`, `tests/contracts/**`, `tests/historical/**` | Throughput default routing, Tensor Core dependency fix, local benchmarks, and validation recorded in `docs/stage_reports/STAGE_R97_THROUGHPUT_DEFAULT_AND_TENSORCORE_DEPENDENCY_REPORT.md`. |
| WPR97-03-gpu-telemetry-smoke-fix | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/research_cycle/**`, `tests/contracts/**`, `tests/historical/**` | GPU parity telemetry fix, performance estimate, mini full-cycle smoke, and validation recorded in `docs/stage_reports/STAGE_R97_GPU_TELEMETRY_SMOKE_FIX_REPORT.md`. |
| WPR97-02-default-accelerated-runtime-polish | Codex Research Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/backtesting/**`, `src/tradingbotsuite/optimization/**`, `src/tradingbotsuite/research_cycle/**`, `tests/backtesting/**`, `tests/contracts/**`, `tests/historical/**`, `tests/optimization/**` | Default accelerated research runtime, CPU/reference fallback evidence, longer CUDA parity, and validation recorded in `docs/stage_reports/STAGE_R97_DEFAULT_ACCELERATED_RUNTIME_POLISH_REPORT.md`. |
| WPR97-01-aggressive-cuda-tensorcore-stability-search | Codex Research Agent | closed | `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/backtesting/**`, `src/tradingbotsuite/optimization/**`, `src/tradingbotsuite/research_cycle/**`, `tests/backtesting/**`, `tests/contracts/**`, `tests/historical/**`, `tests/optimization/**` | Aggressive CUDA/TensorCore stability search implemented and validation recorded in `docs/stage_reports/STAGE_R97_AGGRESSIVE_CUDA_TENSORCORE_STABILITY_SEARCH_REPORT.md`. |
| WP0-01-branch-and-ledger-setup | Orchestrator Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/BRANCH_PURPOSE.md`, `docs/work_packets/WP0-01-branch-and-ledger-setup.md`, `docs/stage_reports/STAGE_0_EXIT_REPORT.md` | Branch exists; governance files created; validation recorded in Stage 0 exit report. |
| WP1-01-repo-inventory | Repo Cartographer Agent | closed | `docs/repo_cartography/REPO_INVENTORY.md`, `docs/stage_reports/STAGE_1_EXIT_REPORT.md` | File-family inventory, import map, root launchers, live order paths, research commands, and tests listed. |
| WP1-02-tradingview-archive-map | Documentation Agent | closed | `docs/repo_cartography/TRADINGVIEW_ARCHIVE_MAP.md`, `docs/stage_reports/STAGE_1_EXIT_REPORT.md` | TradingView/Pine/parity files classified as removed, legacy reference, or candidate archive material. |
| WP2-01-contract-docs | Documentation Agent | closed | `AGENTS.md`, `START_HERE.md`, `docs/contracts/**`, `tests/contracts/**`, `docs/stage_reports/STAGE_2_EXIT_REPORT.md` | Contract docs and import-boundary tests created; validation recorded in Stage 2 exit report. |
| WP3-01-data-manifest-consolidation | Data Agent | closed | `src/tradingbotsuite/data/**`, `tests/contracts/test_data_contracts.py`, `tests/integration/test_provider_intake_smoke.py`, `docs/stage_reports/STAGE_3_EXIT_REPORT.md` | Normalized data package, data manifest validator, partitioned Parquet store, Binance REST intake smoke, and registered-only provider manifests created. |
| WP4-01-feature-registry | Feature Agent | closed | `src/tradingbotsuite/features/**`, `configs/features/**`, `tests/contracts/test_feature_contracts.py`, `docs/stage_reports/STAGE_4_EXIT_REPORT.md` | Point-in-time alignment package, feature registry, feature packs, preset manifests, and train-only preprocessing tests created. |
| WP5-01-backtesting-engine | Backtest Agent | closed | `src/tradingbotsuite/backtesting/**`, `tests/contracts/test_backtest_contracts.py`, `tests/unit/test_execution_simulator.py`, `tests/integration/test_backtest_engine_fixture.py`, `docs/stage_reports/STAGE_5_EXIT_REPORT.md` | Modular research backtest engine, execution simulator, cost model, metrics, deterministic outputs, and benchmark baselines created. |
| WP6-01-strategy-plugin-library | Strategy Agent | closed | `src/tradingbotsuite/strategies/**`, `configs/strategies/**`, `tests/contracts/test_strategy_contracts.py`, `tests/integration/test_backtest_engine_fixture.py`, `docs/stage_reports/STAGE_6_EXIT_REPORT.md` | Strategy plugin contract, registry, configs, four baseline plugins, LC reference, HMM/KNN diagnostic plugin, and engine integration created. |
| WP7-01-hmm-knn-refactor | Orchestrator Agent | closed | `src/tradingbotsuite/strategies/hmm_knn/**`, `src/tradingbotsuite/research/hmm_knn.py`, `tests/tradingbotsuite/test_hmm_knn.py`, `docs/stage_reports/STAGE_7_EXIT_REPORT.md` | HMM/KNN split into modules, feature packs and distances are configurable, deterministic regime baseline added, artifact diagnostics added, and Stage 6 baseline benchmark recorded. |
| WP8-01-generic-experiment-runner | Orchestrator Agent | closed | `src/tradingbotsuite/research/experiment_runner.py`, `tests/tradingbotsuite/test_experiment_runner.py`, `tests/tradingbotsuite/test_research.py`, `docs/stage_reports/STAGE_8_EXIT_REPORT.md` | Generic experiment specs, deterministic cache keys, search expansion, split/regime/side/cost stress outputs, and explicit rejection reasons added. |
| WP9-01-research-ui-command-layer | Orchestrator Agent | closed | `src/tradingbotsuite/ui/**`, `docs/runbooks/research_ui_runbook.md`, `tests/integration/test_research_ui.py`, `docs/stage_reports/STAGE_9_EXIT_REPORT.md` | Research UI pages, manifest-linked metrics, visible queued research jobs, and live-adapter import boundary tests added. |
| WP10-01-live-preflight-hardening | Orchestrator Agent | closed | `src/tradingbotsuite/live/preflight.py`, `src/tradingbotsuite/promotion/artifact_validator.py`, `tests/live/**`, `docs/stage_reports/STAGE_10_EXIT_REPORT.md` | Live mode fails closed on unsafe config, research commands and research artifacts are rejected, root launchers delegate through canonical preflight, and testnet smoke remains documented. |
| WP11-01-promotion-shadow-bridge | Orchestrator Agent | closed | `src/tradingbotsuite/promotion/artifact_validator.py`, `src/tradingbotsuite/live/shadow_loader.py`, `src/tradingbotsuite/runtime.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/**`, `tests/live/**`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/stage_reports/STAGE_11_EXIT_REPORT.md` | Promotion candidates validate against Stage 11 evidence floors, load only in shadow mode without execution changes, are rejected as live order inputs, and display read-only shadow diagnostics in the operator UI. |
| WP12-01-feature-ablation-and-replacement | Orchestrator Agent | closed | `src/tradingbotsuite/research/feature_ablation.py`, `configs/features/**`, `tests/tradingbotsuite/test_feature_ablation.py`, `docs/stage_reports/STAGE_12_1_EXIT_REPORT.md` | Stage 12.1 feature ablation tracks produce reproducible manifests, pending/rejected hypothesis records, per-hypothesis experiment specs, and OOS/stress-only acceptance rules. |
| WP12-02-research-track-gates-and-limitations | Orchestrator Agent | closed with empirical limitations | `src/tradingbotsuite/research/stage12_research.py`, `tests/tradingbotsuite/test_stage12_research_plan.py`, `docs/stage_reports/STAGE_12_EXIT_REPORT.md`, `docs/stage_reports/STAGE_12_COMPLETION_LIMITATIONS.md` | Substages 12.2-12.7 produce reproducible manifests/specs and documented blocked/pending hypotheses; empirical acceptance remains blocked until real OOS/stress evidence exists. |
| WP13-01-readiness-planning-and-offline-verifiers | Orchestrator Agent | closed - execution blocked | `src/tradingbotsuite/promotion/stage13_readiness.py`, `src/tradingbotsuite/research/command_registry.py`, `src/tradingbotsuite/live/preflight.py`, `src/tradingbotsuite/web/**`, `tests/tradingbotsuite/test_stage13_readiness.py`, `tests/live/test_preflight.py`, `docs/stage_reports/STAGE_13_READINESS_PLANNING_REPORT.md` | Stage 13 readiness schemas, offline validators, read-only diagnostics, rollback checklist generation, and centralized research-command live rejection are complete. |
| WPR0-01-historical-research-cycle-foundation | Codex Research Agent | closed | `src/tradingbotsuite/research/experiment_runner.py`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/backtesting/splits.py`, `src/tradingbotsuite/optimization/**`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/command_registry.py`, `configs/research/**`, `tests/tradingbotsuite/test_experiment_runner.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/contracts/test_backtest_contracts.py`, `tests/historical/**`, `tests/optimization/**`, `tests/live/test_preflight.py`, `docs/work_packets/WPR0-01-historical-research-cycle-foundation.md`, `docs/stage_reports/STAGE_R0_R1_HISTORICAL_RESEARCH_FOUNDATION_REPORT.md` | Generic experiment placeholders are contract-only, historical cycle command writes real backtest-derived research artifacts, holding windows align to 1h/4h/12h/24h/72h/7d, optimizer/stability foundation rejects spikes; validation recorded in Stage R0/R1 report. |
| WPR2-01-real-backtests-splits-features-exits | Codex Research Agent | closed | `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/command_registry.py`, `src/tradingbotsuite/research/experiment_runner.py`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/backtesting/**`, `src/tradingbotsuite/features/builders.py`, `src/tradingbotsuite/features/cache.py`, `src/tradingbotsuite/features/split_transforms.py`, `src/tradingbotsuite/features/__init__.py`, `src/tradingbotsuite/optimization/**`, `tests/tradingbotsuite/test_experiment_runner.py`, `tests/backtesting/**`, `tests/features/**`, `tests/historical/**`, `tests/optimization/**`, `tests/contracts/**`, `docs/work_packets/WPR2-01-real-backtests-splits-features-exits.md`, `docs/stage_reports/STAGE_R2_R3_R6_R7_RESEARCH_COMPUTATION_REPORT.md` | Real generic backtest artifacts, split/exit/feature foundations, optimizer search-space cycle expansion, actual stability regions, strengthened cache identity, and validation recorded in Stage R2/R3/R6/R7 report. |
| WPR6-08-11-exit-strategy-candidate-pack-hardening | Codex Research Agent | closed | `src/tradingbotsuite/backtesting/exits.py`, `src/tradingbotsuite/backtesting/execution_sim.py`, `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/backtesting/__init__.py`, `src/tradingbotsuite/strategies/_helpers.py`, `src/tradingbotsuite/strategies/parameters.py`, `src/tradingbotsuite/strategies/__init__.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_artifacts/**`, `tests/backtesting/**`, `tests/contracts/test_strategy_contracts.py`, `tests/contracts/test_backtest_contracts.py`, `tests/historical/**`, `tests/research_artifacts/**`, `tests/unit/test_execution_simulator.py`, `docs/work_packets/WPR6-08-11-exit-strategy-candidate-pack-hardening.md`, `docs/stage_reports/STAGE_R6_R8_R11_RESEARCH_HARDENING_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Lower-timeframe triple-barrier sequencing, strategy parameter metadata, research-only candidate pack foundation, fail-closed boundary fixes, and validation recorded in Stage R6/R8/R11 report. |
| WPR9-10-12-knn-fixtures-benchmarks | Codex Research Agent | closed | `configs/v2_btc_hmm_multi_knn_research.json`, `src/tradingbotsuite/research/hmm_knn.py`, `src/tradingbotsuite/research/hmm_knn_experiments.py`, `src/tradingbotsuite/strategies/hmm_knn/**`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/data/__init__.py`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/command_registry.py`, `tests/tradingbotsuite/test_hmm_knn.py`, `tests/contracts/test_data_contracts.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR9-10-12-knn-fixtures-benchmarks.md`, `docs/stage_reports/STAGE_R9_R10_R12_RESEARCH_COMPLETION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | KNN diagnostics, fixture-pack validation, research-cycle benchmark gate, review fixes, and validation recorded in Stage R9/R10/R12 report. |
| WPR7-12-materialized-feature-cache | Codex Research Agent | closed | `src/tradingbotsuite/features/builders.py`, `src/tradingbotsuite/features/cache.py`, `src/tradingbotsuite/features/__init__.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_cycle/benchmark.py`, `tests/features/test_feature_builders.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR7-12-materialized-feature-cache.md`, `docs/stage_reports/STAGE_R7_R12_MATERIALIZED_FEATURE_CACHE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Materialized registered feature frames, validated feature-cache artifacts, candidate feature-set provenance, measured feature-cache benchmark evidence, review fixes, and validation recorded in Stage R7/R12 report. |
| WPR5-12-optimizer-stability-truthfulness | Codex Research Agent | closed | `src/tradingbotsuite/optimization/cache.py`, `src/tradingbotsuite/optimization/optimizer.py`, `src/tradingbotsuite/optimization/stability.py`, `src/tradingbotsuite/optimization/__init__.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `src/tradingbotsuite/research_cycle/runner.py`, `tests/optimization/test_candidate_cache_keys.py`, `tests/optimization/test_parallel_results_equal_serial.py`, `tests/optimization/test_region_of_stability.py`, `tests/optimization/test_spike_candidate_rejected.py`, `tests/optimization/test_plateau_candidate_ranked_above_spike.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/research_artifacts/test_candidate_pack.py`, `docs/work_packets/WPR5-12-optimizer-stability-truthfulness.md`, `docs/stage_reports/STAGE_R5_R12_OPTIMIZER_STABILITY_TRUTHFULNESS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Optimizer cache telemetry, duplicate-candidate hardening, truthful stability validation scope, durable candidate gate reports, pack-gate stability blockers, review fixes, and validation recorded in Stage R5/R12 report. |
| WPR12-13-backtest-identity-cache-evidence | Codex Research Agent | closed | `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/research_cycle/runner.py`, `tests/contracts/test_backtest_contracts.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_research_cycle_benchmark.py`, `docs/work_packets/WPR12-13-backtest-identity-cache-evidence.md`, `docs/stage_reports/STAGE_R12_R13_BACKTEST_IDENTITY_CACHE_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Identity-only cache policy fields, auditable backtest cache-key components, lower-timeframe path-independent identity, ranking identity columns, benchmark repeat identity evidence, review fixes, and validation recorded in Stage R12/R13 report. |
| WPR8-01-strategy-comparator-contract-hardening | Codex Research Agent | closed | `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/strategies/contracts.py`, `src/tradingbotsuite/strategies/registry.py`, `src/tradingbotsuite/strategies/_helpers.py`, `src/tradingbotsuite/strategies/no_trade.py`, `src/tradingbotsuite/strategies/parameters.py`, `tests/contracts/test_strategy_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/integration/test_backtest_engine_fixture.py`, `docs/work_packets/WPR8-01-strategy-comparator-contract-hardening.md`, `docs/stage_reports/STAGE_R8_STRATEGY_COMPARATOR_CONTRACT_HARDENING_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Baseline comparator coverage evidence, candidate strategy metadata audit fields, resolved-parameter candidate identity, fail-closed strategy contracts, and validation recorded in Stage R8 report. |
| WPR4-08-metadata-backed-default-search | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/optimization/search_space.py`, `src/tradingbotsuite/strategies/parameters.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/optimization/test_search_space_expansion.py`, `docs/work_packets/WPR4-08-metadata-backed-default-search.md`, `docs/stage_reports/STAGE_R4_R8_METADATA_BACKED_DEFAULT_SEARCH_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Metadata-backed default candidate expansion, lazy capped grid generation, unique metadata sampling, explicit-search preservation, and validation recorded in Stage R4/R8 metadata default search report. |
| WPR12-14-benchmark-threshold-parallel-evidence | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/optimization/optimizer.py`, `src/tradingbotsuite/optimization/search_space.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/optimization/test_parallel_results_equal_serial.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR12-14-benchmark-threshold-parallel-evidence.md`, `docs/stage_reports/STAGE_R12_BENCHMARK_THRESHOLD_PARALLEL_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Benchmark regression thresholds, strict evidence-complete gate semantics, manifest-derived live/cache safety checks, tracemalloc-scoped memory evidence, synthetic optimizer parallel evaluator evidence, and validation recorded in Stage R12 benchmark threshold report. |
| WPR10-11-candidate-pack-fixture-provenance | Codex Research Agent | closed | `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `src/tradingbotsuite/research_cycle/runner.py`, `tests/research_artifacts/test_candidate_pack.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR10-11-candidate-pack-fixture-provenance.md`, `docs/stage_reports/STAGE_R10_R11_CANDIDATE_PACK_FIXTURE_PROVENANCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Candidate packs now require validated non-synthetic fixture provenance, complete candidate-tied evidence rows, durable gate/backtest/stability agreement, live-adjacent rejection, and validation recorded in Stage R10/R11 report. |
| WPR12-15-feature-ablation-historical-execution | Codex Research Agent | closed | `src/tradingbotsuite/research/experiment_runner.py`, `src/tradingbotsuite/research/feature_ablation.py`, `tests/tradingbotsuite/test_experiment_runner.py`, `tests/tradingbotsuite/test_feature_ablation.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR12-15-feature-ablation-historical-execution.md`, `docs/stage_reports/STAGE_R12_FEATURE_ABLATION_HISTORICAL_EXECUTION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Supplied generic specs and all generated feature-ablation specs execute through real research backtests when a dataset is available; search candidates, supplied validation, and no-dataset/no-split truthfulness are validated; no promotion/live readiness claimed. |
| WPR16-01-research-candidate-gate-evidence-tables | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/research_artifacts/test_candidate_pack.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR16-01-research-candidate-gate-evidence-tables.md`, `docs/stage_reports/STAGE_R16_RESEARCH_CANDIDATE_GATE_EVIDENCE_TABLES_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Real candidate-tied side/regime evidence, semantic durable pack gates, non-synthetic complete fixture pass path, synthetic/incomplete fail-closed paths, and validation recorded in Stage R16 report. |
| WPR17-01-research-candidate-ablation-evidence-gates | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/research_artifacts/test_candidate_pack.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR17-01-research-candidate-ablation-evidence-gates.md`, `docs/stage_reports/STAGE_R17_RESEARCH_CANDIDATE_ABLATION_EVIDENCE_GATES_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Candidate-tied ablation evidence, full research stress scenario registry, durable pack gates for ablation/stress completeness, and validation recorded in Stage R17 report. |
| WPR18-01-optimizer-adaptive-refinement-bootstrap-evidence | Codex Research Agent | closed | `src/tradingbotsuite/optimization/optimizer.py`, `src/tradingbotsuite/optimization/search_space.py`, `tests/optimization/test_parallel_results_equal_serial.py`, `tests/optimization/test_region_of_stability.py`, `tests/optimization/test_search_space_expansion.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR18-01-optimizer-adaptive-refinement-bootstrap-evidence.md`, `docs/stage_reports/STAGE_R18_OPTIMIZER_ADAPTIVE_REFINEMENT_BOOTSTRAP_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Staged optimizer reports, adaptive local-neighbor refinement, deterministic bootstrap evidence, updated multiple-comparison metadata, and validation recorded in Stage R18 report. |
| WPR19-01-vector-backtest-fixed-holding-parity-foundation | Codex Research Agent | closed | `src/tradingbotsuite/backtesting/vector_engine.py`, `src/tradingbotsuite/backtesting/__init__.py`, `tests/backtesting/test_vector_engine_matches_reference.py`, `tests/contracts/test_backtest_contracts.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR19-01-vector-backtest-fixed-holding-parity-foundation.md`, `docs/stage_reports/STAGE_R19_VECTOR_BACKTEST_FIXED_HOLDING_PARITY_FOUNDATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Vector fixed-holding primary-bar backtest artifacts, parity tests against the reference engine, unsupported-scope rejection, vector config/cache identity, and validation recorded in Stage R19 report. |
| WPR20-01-vector-backtest-cycle-integration-benchmark-evidence | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/backtesting/vector_engine.py`, `tests/backtesting/test_vector_engine_matches_reference.py`, `tests/contracts/test_backtest_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR20-01-vector-backtest-cycle-integration-benchmark-evidence.md`, `docs/stage_reports/STAGE_R20_VECTOR_BACKTEST_CYCLE_INTEGRATION_BENCHMARK_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Opt-in vector backend routing, default reference behavior, auto fallback evidence, benchmark parity/runtime observations, and validation recorded in Stage R20 report. |
| WPR21-01-research-exit-policy-expansion-foundation | Codex Research Agent | closed | `src/tradingbotsuite/backtesting/exits.py`, `src/tradingbotsuite/backtesting/execution_sim.py`, `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/backtesting/vector_engine.py`, `tests/backtesting/test_exit_policy_expansion.py`, `tests/backtesting/test_vector_engine_matches_reference.py`, `tests/contracts/test_backtest_contracts.py`, `tests/live/test_preflight.py`, `tests/unit/test_execution_simulator.py`, `docs/work_packets/WPR21-01-research-exit-policy-expansion-foundation.md`, `docs/stage_reports/STAGE_R21_RESEARCH_EXIT_POLICY_EXPANSION_FOUNDATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Conservative research exit-policy foundations, exit-policy parameter manifest/cache identity, vector fixed-holding rejection, and validation recorded in Stage R21 report. |
| WPR22-01-exit-policy-candidate-cycle-evidence | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/optimization/candidate.py`, `src/tradingbotsuite/optimization/search_space.py`, `src/tradingbotsuite/backtesting/engine.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/optimization/test_candidate_cache_keys.py`, `tests/optimization/test_search_space_expansion.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR22-01-exit-policy-candidate-cycle-evidence.md`, `docs/stage_reports/STAGE_R22_EXIT_POLICY_CANDIDATE_CYCLE_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Exit policies are first-class research-cycle candidate dimensions with deterministic candidate identity, rankings/backtest-index evidence, and validation recorded in Stage R22 report. |
| WPR23-01-validation-split-mode-cycle-evidence | Codex Research Agent | closed | `src/tradingbotsuite/backtesting/splits.py`, `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_cycle/runner.py`, `tests/backtesting/test_splits.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR23-01-validation-split-mode-cycle-evidence.md`, `docs/stage_reports/STAGE_R23_VALIDATION_SPLIT_MODE_CYCLE_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Configured validation split modes, split manifest/index evidence, fail-closed unavailable-mode behavior, default preservation, and validation recorded in Stage R23 report. |
| WPR24-01-research-evidence-floor-gates | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/research_artifacts/test_candidate_pack.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR24-01-research-evidence-floor-gates.md`, `docs/stage_reports/STAGE_R24_RESEARCH_EVIDENCE_FLOOR_GATES_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Per-split trade floors, validation-method coverage, cost-stress survival floors, durable dominance recomputation, and validation recorded in Stage R24 report. |
| WPR25-01-lower-timeframe-triple-barrier-cycle-evidence | Codex Research Agent | closed | `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/backtesting/vector_engine.py`, `tests/backtesting/test_vector_engine_matches_reference.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR25-01-lower-timeframe-triple-barrier-cycle-evidence.md`, `docs/stage_reports/STAGE_R25_LOWER_TIMEFRAME_TRIPLE_BARRIER_CYCLE_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Lower-timeframe triple-barrier cycle policies, fixture provenance, sequence proof evidence, vector auto fallback evidence, fail-closed schema checks, and validation recorded in Stage R25 report. |
| WPR26-01-lower-timeframe-candidate-pack-gates | Codex Research Agent | closed | `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `tests/research_artifacts/test_candidate_pack.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR26-01-lower-timeframe-candidate-pack-gates.md`, `docs/stage_reports/STAGE_R26_LOWER_TIMEFRAME_CANDIDATE_PACK_GATES_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Durable lower-timeframe source, backtest identity, manifest, and sequence-proof gates before triple-barrier candidates can be packed; validation recorded in Stage R26 report. |
| WPR27-01-fixture-family-context-materialization | Codex Research Agent | closed | `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/features/builders.py`, `src/tradingbotsuite/features/cache.py`, `src/tradingbotsuite/research_cycle/runner.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/features/test_feature_builders.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR27-01-fixture-family-context-materialization.md`, `docs/stage_reports/STAGE_R27_FIXTURE_FAMILY_CONTEXT_MATERIALIZATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Fixture-family context materialization, provenance, cache identity, no-lookahead tests, and validation recorded in Stage R27 report. |
| WPR28-01-generic-experiment-nonscoreable-not-run-rows | Codex Research Agent | closed | `src/tradingbotsuite/research/experiment_runner.py`, `tests/tradingbotsuite/test_experiment_runner.py`, `tests/tradingbotsuite/test_feature_ablation.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR28-01-generic-experiment-nonscoreable-not-run-rows.md`, `docs/stage_reports/STAGE_R28_GENERIC_EXPERIMENT_TRUTHFULNESS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Generic missing-dataset, failed-backtest, and validation-incomplete rows are non-scoreable/non-rankable; validation recorded in Stage R28 report. |
| WPR29-01-benchmark-cli-gate-completeness | Codex Research Agent | closed | `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research_cycle/benchmark.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR29-01-benchmark-cli-gate-completeness.md`, `docs/stage_reports/STAGE_R29_BENCHMARK_CLI_GATE_COMPLETENESS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Benchmark CLI now fails closed on failed/evidence-incomplete gates, exposes gate payload details, and records validation in Stage R29 report. |
| WPR30-01-benchmark-evidence-completeness-hardening | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/main.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR30-01-benchmark-evidence-completeness-hardening.md`, `docs/stage_reports/STAGE_R30_BENCHMARK_EVIDENCE_COMPLETENESS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Artifact overhead now includes backend comparison and final report evidence, cache/memory semantics are non-claiming and scoped, bounded medium-tier execution is tested, and validation recorded in Stage R30 report. |
| WPR31-01-generic-validation-scoreability-hardening | Codex Research Agent | closed | `src/tradingbotsuite/research/experiment_runner.py`, `tests/tradingbotsuite/test_experiment_runner.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR31-01-generic-validation-scoreability-hardening.md`, `docs/stage_reports/STAGE_R31_GENERIC_VALIDATION_SCOREABILITY_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Unsupported, executable-not-executed, and report-output-not-executed configured validation methods now make generic experiment rows non-scoreable; validation recorded in Stage R31 report. |
| WPR32-01-checked-in-btcusdt-fixture-pack | Codex Research Agent | closed | `configs/research/full_cycle_btc_v1.json`, `data/research/fixtures/btcusdt_v1/**`, `.gitignore`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR32-01-checked-in-btcusdt-fixture-pack.md`, `docs/stage_reports/STAGE_R32_CHECKED_IN_BTCUSDT_FIXTURE_PACK_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Checked-in Binance USD-M kline-derived BTCUSDT fixture pack, no TradingView/synthetic provenance, synthetic fallback disabled, optional-family absence tested, and validation recorded in Stage R32 report. |
| WPR33-01-provider-kline-fixture-pack-builder | Codex Research Agent | closed | `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/command_registry.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR33-01-provider-kline-fixture-pack-builder.md`, `docs/stage_reports/STAGE_R33_PROVIDER_KLINE_FIXTURE_PACK_BUILDER_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Provider kline fixture-pack builder and CLI added; TradingView/synthetic/interval mismatch fail-closed behavior tested; validation recorded in Stage R33 report. |
| WPR34-01-fixture-source-provenance-propagation | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/research_artifacts/test_candidate_pack.py`, `docs/work_packets/WPR34-01-fixture-source-provenance-propagation.md`, `docs/stage_reports/STAGE_R34_FIXTURE_SOURCE_PROVENANCE_PROPAGATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Fixture source, derivation, optional-family omissions, and limitations now propagate into historical-cycle and candidate-pack provenance evidence with fail-closed mismatch gates. |
| WPR35-01-provider-context-fixture-pack-builder | Codex Research Agent | closed | `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/main.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR35-01-provider-context-fixture-pack-builder.md`, `docs/stage_reports/STAGE_R35_PROVIDER_CONTEXT_FIXTURE_PACK_BUILDER_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Provider context manifests now build funding, premium, open-interest, and aggregate-trade fixture families from local provider data; TradingView/synthetic/unsupported provenance fails closed; validation recorded in Stage R35 report. |
| WPR36-01-binance-usdm-context-collector | Codex Research Agent | closed | `src/tradingbotsuite/research/market_data.py`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/command_registry.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/tradingbotsuite/test_market_data_collection.py`, `tests/live/test_preflight.py`, `docs/work_packets/WPR36-01-binance-usdm-context-collector.md`, `docs/stage_reports/STAGE_R36_BINANCE_USDM_CONTEXT_COLLECTOR_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Binance USD-M REST context collector added for funding, premium, and open-interest manifests; collector output feeds fixture builder; validation recorded in Stage R36 report. |
| WPR37-01-btcusdt-context-fixture-data-run | Codex Research Agent | closed | `data/research/market_data/binance_usdm/**`, `data/research/fixtures/btcusdt_context_provider_v1/**`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `docs/work_packets/WPR37-01-btcusdt-context-fixture-data-run.md`, `docs/stage_reports/STAGE_R37_BTCUSDT_CONTEXT_FIXTURE_DATA_RUN_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Collected BTCUSDT Binance USD-M funding, premium, and open-interest context; built generated context-aware fixture pack; validation recorded in Stage R37 report. |
| WPR38-01-context-fixture-cycle-execution | Codex Research Agent | closed | `data/research/historical_cycles/btcusdt_context_provider_cycle/**`, `docs/work_packets/WPR38-01-context-fixture-cycle-execution.md`, `docs/stage_reports/STAGE_R38_CONTEXT_FIXTURE_CYCLE_EXECUTION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Executed bounded historical cycle against generated BTCUSDT context fixture pack; context materialization, rankings, gates, and validation evidence recorded without promoting local generated data to canonical tracked config. |
| WPR39-01-extended-context-fixture-comparator-cycle | Codex Research Agent | closed | `data/research/market_data/binance_usdm/wpr39_btcusdt_context_provider_30d_v1/**`, `data/research/market_data/binance_usdm/wpr39_btcusdt_context_provider_7d_v1/**`, `data/research/fixtures/btcusdt_context_provider_oi500_v1/**`, `data/research/historical_cycles/btcusdt_context_provider_oi500_cycle/**`, `docs/work_packets/WPR39-01-extended-context-fixture-comparator-cycle.md`, `docs/stage_reports/STAGE_R39_EXTENDED_CONTEXT_FIXTURE_COMPARATOR_CYCLE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Built 500-row provider context fixture after recording Binance open-interest row/retention limits; ran comparator-aware cycle with ablation evidence, vector backend execution, and fail-closed candidate gates. |
| WPR40-01-binance-open-interest-pagination-7d-cycle | Codex Research Agent | closed | `src/tradingbotsuite/research/market_data.py`, `tests/tradingbotsuite/test_market_data_collection.py`, `data/research/market_data/binance_usdm/wpr40_btcusdt_context_provider_7d_v2/**`, `data/research/fixtures/btcusdt_context_provider_7d_v2/**`, `data/research/historical_cycles/btcusdt_context_provider_7d_v2_cycle/**`, `docs/work_packets/WPR40-01-binance-open-interest-pagination-7d-cycle.md`, `docs/stage_reports/STAGE_R40_BINANCE_OPEN_INTEREST_PAGINATION_7D_CYCLE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Fixed Binance USD-M open-interest REST pagination for the endpoint's 500-row page limit, then rebuilt a 7-day complete context fixture and reran comparator-cycle evidence. |
| WPR41-01-latest-month-provider-context-cycle | Codex Research Agent | closed | `data/research/market_data/binance_usdm/wpr41_btcusdt_latest_month_context_provider_v1/**`, `data/research/fixtures/btcusdt_context_provider_latest_month_v1/**`, `data/research/historical_cycles/btcusdt_context_provider_latest_month_v1_cycle/**`, `docs/work_packets/WPR41-01-latest-month-provider-context-cycle.md`, `docs/stage_reports/STAGE_R41_LATEST_MONTH_PROVIDER_CONTEXT_CYCLE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Collected fresh direct Binance USD-M bars and paginated context, built a 2,873-row latest-month BTCUSDT context fixture, and ran a comparator cycle with fail-closed gates. |
| WPR42-01-provider-backed-benchmark-evidence | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/benchmark.py`, `tests/historical/test_research_cycle_benchmark.py`, `data/research/benchmarks/wpr42_latest_month_provider_benchmark/**`, `docs/work_packets/WPR42-01-provider-backed-benchmark-evidence.md`, `docs/stage_reports/STAGE_R42_PROVIDER_BACKED_BENCHMARK_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added and ran a provider-fixture benchmark tier using the WPR41 latest-month BTCUSDT context fixture while preserving synthetic benchmark guardrails. |
| WPR43-01-provider-wt3d-full-context-ablation-cycle | Codex Research Agent | closed | `data/research/historical_cycles/btcusdt_context_provider_wt3d_ablation_cycle/**`, `docs/work_packets/WPR43-01-provider-wt3d-full-context-ablation-cycle.md`, `docs/stage_reports/STAGE_R43_PROVIDER_WT3D_FULL_CONTEXT_ABLATION_CYCLE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Ran a provider-backed historical cycle comparing no-WT and WT3D full-context feature sets on the WPR41 latest-month fixture with fail-closed candidate gates. |
| WPR44-01-final-crosscheck-hardening | Codex Research Agent | closed | `.gitignore`, `configs/research/full_cycle_btc_v1.json`, `src/tradingbotsuite/backtesting/splits.py`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/optimization/stability.py`, `src/tradingbotsuite/research/feature_ablation.py`, `src/tradingbotsuite/research/market_data.py`, `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_cycle/spec.py`, `tests/**`, `data/research/fixtures/btcusdt_context_provider_latest_month_v1/**`, `docs/work_packets/WPR44-01-final-crosscheck-hardening.md`, `docs/stage_reports/STAGE_R44_FINAL_CROSSCHECK_HARDENING_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Final crosscheck fixed benchmark path hygiene, durable provider fixture evidence, exact holdout membership, exit-policy-aware stability/ablation grouping, fixed-interval context gap detection, and validation regressions before commit/push. |
| WPR45-01-research-branch-distillation | Codex Research Agent | closed | `docs/RESEARCH_BRANCH_DISTILLATION.md`, `docs/work_packets/WPR45-01-research-branch-distillation.md`, `docs/stage_reports/STAGE_R45_RESEARCH_BRANCH_DISTILLATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Added a current research-branch distillation document covering purpose, framework, stack, artifact model, validation boundaries, and safe future-agent orientation. |
| WPR46-01-perp-strategy-plan-alignment | Codex Research Agent | closed | `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/work_packets/WPR46-01-perp-strategy-plan-alignment.md`, `docs/stage_reports/STAGE_R46_PERP_STRATEGY_PLAN_ALIGNMENT_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Curated the downloaded BTC/ETH perpetual strategy plan into repo-native agent instructions aligned to current cycle specs, data families, feature IDs, strategy contracts, exit IDs, gates, and future packet sequencing. |
| WPR47-01-crypto-lake-access-setup | Codex Research Agent | closed | `.gitignore`, `README.md`, `pyproject.toml`, `configs/data/v2_btc_hmm_knn_provider_pipeline.json`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/data_pipeline.py`, `src/tradingbotsuite/research/market_data.py`, `tests/tradingbotsuite/test_market_data_collection.py`, `docs/runbooks/crypto_lake_free_data_runbook.md`, `docs/work_packets/WPR47-01-crypto-lake-access-setup.md`, `docs/stage_reports/STAGE_R47_CRYPTO_LAKE_FREE_DATA_FALLBACK_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Added optional Crypto Lake free-sample fallback guidance, ignored lakeapi cache, direct free sample-data fetch mode, clearer missing-dependency errors, and a real BTCUSDT free-sample smoke test with 1,440 rows and no gaps/duplicates. |
| WPR48-01-perp-plan-free-data-refresh | Codex Research Agent | closed | `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/work_packets/WPR48-01-perp-plan-free-data-refresh.md`, `docs/stage_reports/STAGE_R48_PERP_PLAN_FREE_DATA_REFRESH_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Curated perpetual plan refreshed after WPR47; future implementation now starts at WPR49, Crypto Lake is documented as credential-free free-sample fallback only, and provider source priority is aligned with current branch structure. |
| WPR49-01-perp-context-manifest-foundation | Codex Research Agent | closed | `src/tradingbotsuite/data/contracts.py`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/research/market_data.py`, `tests/contracts/**`, `tests/tradingbotsuite/test_market_data_collection.py`, `docs/work_packets/WPR49-01-perp-context-manifest-foundation.md`, `docs/stage_reports/STAGE_R49_PERP_CONTEXT_MANIFEST_FOUNDATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added non-breaking perp context metadata, latest-window/free-sample coverage truthfulness checks, context gap/duplicate evidence, fixture-pack metadata propagation, and data manifest boundary hardening; validation recorded in Stage R49 report. |
| WPR50-01-perp-context-v2-feature-pack | Codex Research Agent | closed | `src/tradingbotsuite/features/registry.py`, `src/tradingbotsuite/features/packs.py`, `src/tradingbotsuite/features/builders.py`, `src/tradingbotsuite/features/cache.py`, `configs/features/features_perp_context_v2.json`, `tests/features/**`, `tests/contracts/test_feature_contracts.py`, `docs/work_packets/WPR50-01-perp-context-v2-feature-pack.md`, `docs/stage_reports/STAGE_R50_PERP_CONTEXT_V2_FEATURE_PACK_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added registered `features_perp_context_v2`, interval-aware perp context features, agg-trade flow passthroughs, explicit missingness/quality tests, cache context identity coverage, and validation recorded in Stage R50 report. |
| WPR51-01-perp-basis-convergence-strategy | Codex Research Agent | closed | `src/tradingbotsuite/strategies/perp_basis_convergence.py`, `src/tradingbotsuite/strategies/registry.py`, `src/tradingbotsuite/strategies/parameters.py`, `src/tradingbotsuite/strategies/__init__.py`, `configs/strategies/perp_basis_convergence_v2.json`, `tests/contracts/test_strategy_contracts.py`, `tests/integration/test_backtest_engine_fixture.py`, `tests/historical/**`, `docs/work_packets/WPR51-01-perp-basis-convergence-strategy.md`, `docs/stage_reports/STAGE_R51_PERP_BASIS_CONVERGENCE_STRATEGY_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added `perp_basis_convergence_v2`, conservative strategy metadata/config, fail-closed v2 quality gates, focused contract and engine tests, and validation recorded in Stage R51 report. |
| WPR52-01-provider-perp-context-cycle-evidence | Codex Research Agent | closed | `configs/research/full_cycle_btcusdt_perp_context_v2.json`, `data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**`, `src/tradingbotsuite/strategies/no_trade.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/contracts/test_strategy_contracts.py`, `tests/historical/**`, `docs/work_packets/WPR52-01-provider-perp-context-cycle-evidence.md`, `docs/stage_reports/STAGE_R52_PROVIDER_PERP_CONTEXT_CYCLE_EVIDENCE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added checked provider-backed perp context v2 cycle spec, completed no-trade comparator coverage for v2 features, ran local cycle evidence, recorded fail-closed gate outcome, and validation recorded in Stage R52 report. |
| WPR53-01-funding-crowding-fade-strategy | Codex Research Agent | closed | `src/tradingbotsuite/strategies/funding_crowding_fade.py`, `src/tradingbotsuite/strategies/registry.py`, `src/tradingbotsuite/strategies/parameters.py`, `configs/strategies/funding_crowding_fade_v2.json`, `configs/research/full_cycle_btcusdt_perp_context_v2.json`, `tests/contracts/test_strategy_contracts.py`, `tests/integration/test_backtest_engine_fixture.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `docs/work_packets/WPR53-01-funding-crowding-fade-strategy.md`, `docs/stage_reports/STAGE_R53_FUNDING_CROWDING_FADE_STRATEGY_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added `funding_crowding_fade_v2`, bounded strategy metadata/config, fail-closed funding/premium/OI quality gates, checked-cycle inclusion, local cycle evidence, and validation recorded in Stage R53 report. |
| WPR54-01-oi-flow-breakout-strategy | Codex Research Agent | closed | `src/tradingbotsuite/strategies/oi_flow_breakout.py`, `src/tradingbotsuite/strategies/registry.py`, `src/tradingbotsuite/strategies/parameters.py`, `configs/strategies/oi_flow_breakout_v2.json`, `configs/research/full_cycle_btcusdt_perp_context_v2.json`, `data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**`, `tests/contracts/test_strategy_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/integration/test_backtest_engine_fixture.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `docs/work_packets/WPR54-01-oi-flow-breakout-strategy.md`, `docs/stage_reports/STAGE_R54_OI_FLOW_BREAKOUT_STRATEGY_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added `oi_flow_breakout_v2`, bounded strategy metadata/config, fail-closed OI/premium/quality gates, optional flow confirmation, checked-cycle inclusion, local cycle evidence, and validation recorded in Stage R54 report. |
| WPR55-01-funding-window-timing-strategy | Codex Research Agent | closed | `src/tradingbotsuite/strategies/funding_window_timing.py`, `src/tradingbotsuite/strategies/registry.py`, `src/tradingbotsuite/strategies/parameters.py`, `configs/strategies/funding_window_timing_v1.json`, `configs/research/full_cycle_btcusdt_perp_context_v2.json`, `data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**`, `tests/contracts/test_strategy_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/integration/test_backtest_engine_fixture.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `docs/work_packets/WPR55-01-funding-window-timing-strategy.md`, `docs/stage_reports/STAGE_R55_FUNDING_WINDOW_TIMING_STRATEGY_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added `funding_window_timing_v1`, bounded strategy metadata/config, fail-closed funding/timing/premium/quality gates, checked-cycle inclusion, local cycle evidence, and validation recorded in Stage R55 report. |
| WPR56-01-ethusdt-fixture-mirror-cycle-evidence | Codex Research Agent | closed | `.gitignore`, `configs/research/full_cycle_ethusdt_perp_context_v2.json`, `data/research/market_data/binance_usdm/wpr56_ethusdt_latest_month_context_provider_v1/**`, `data/research/fixtures/ethusdt_context_provider_latest_month_v1/**`, `data/research/historical_cycles/ethusdt_perp_context_v2_foundation/**`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/features/builders.py`, `src/tradingbotsuite/research/market_data.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/features/test_feature_builders.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/tradingbotsuite/test_market_data_collection.py`, `docs/work_packets/WPR56-01-ethusdt-fixture-mirror-cycle-evidence.md`, `docs/stage_reports/STAGE_R56_ETHUSDT_FIXTURE_MIRROR_CYCLE_EVIDENCE_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added ETHUSDT provider fixture, checked mirror cycle, bounded OI pagination fix, latest-window provenance propagation, fail-closed cycle evidence, and validation recorded in Stage R56 report. |
| WPR57-01-funding-aware-exit-policy | Codex Research Agent | closed | `src/tradingbotsuite/backtesting/exits.py`, `src/tradingbotsuite/backtesting/execution_sim.py`, `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/research_cycle/spec.py`, `configs/research/full_cycle_btcusdt_perp_context_v2.json`, `configs/research/full_cycle_ethusdt_perp_context_v2.json`, `data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**`, `data/research/historical_cycles/ethusdt_perp_context_v2_foundation/**`, `tests/backtesting/test_exit_policy_expansion.py`, `tests/backtesting/test_vector_engine_matches_reference.py`, `tests/contracts/test_backtest_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `docs/work_packets/WPR57-01-funding-aware-exit-policy.md`, `docs/stage_reports/STAGE_R57_FUNDING_AWARE_EXIT_POLICY_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added `funding_aware_exit_v1`, checked BTC/ETH cycle evidence, fail-closed gate outcomes, and validation recorded in Stage R57 report. |
| WPR58-01-oi-contraction-exit-policy | Codex Research Agent | closed | `src/tradingbotsuite/backtesting/exits.py`, `src/tradingbotsuite/backtesting/execution_sim.py`, `src/tradingbotsuite/backtesting/engine.py`, `src/tradingbotsuite/research_cycle/spec.py`, `configs/research/full_cycle_btcusdt_perp_context_v2.json`, `configs/research/full_cycle_ethusdt_perp_context_v2.json`, `data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**`, `data/research/historical_cycles/ethusdt_perp_context_v2_foundation/**`, `tests/backtesting/test_exit_policy_expansion.py`, `tests/backtesting/test_vector_engine_matches_reference.py`, `tests/contracts/test_backtest_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `docs/work_packets/WPR58-01-oi-contraction-exit-policy.md`, `docs/stage_reports/STAGE_R58_OI_CONTRACTION_EXIT_POLICY_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added `oi_contraction_exit_v1`, checked BTC/ETH cycle evidence, fail-closed gate outcomes, and validation recorded in Stage R58 report. |
| WPR59-01-trial-budget-overfit-diagnostic-reports | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/research_artifacts/test_candidate_pack.py`, `configs/research/full_cycle_btcusdt_perp_context_v2.json`, `configs/research/full_cycle_ethusdt_perp_context_v2.json`, `data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**`, `data/research/historical_cycles/ethusdt_perp_context_v2_foundation/**`, `docs/work_packets/WPR59-01-trial-budget-overfit-diagnostic-reports.md`, `docs/stage_reports/STAGE_R59_TRIAL_BUDGET_OVERFIT_DIAGNOSTICS_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added trial-budget and overfit-adjustment research diagnostics without changing candidate-pack metric gates, with validation recorded in Stage R59 report. |
| WPR60-01-split-safe-hmm-router | Codex Research Agent | closed | `src/tradingbotsuite/strategies/hmm_routed_alpha_sleeves.py`, `src/tradingbotsuite/strategies/registry.py`, `src/tradingbotsuite/strategies/parameters.py`, `src/tradingbotsuite/strategies/__init__.py`, `configs/strategies/hmm_routed_alpha_sleeves_v2.json`, `tests/contracts/test_strategy_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/tradingbotsuite/test_hmm_knn.py`, `docs/work_packets/WPR60-01-split-safe-hmm-router.md`, `docs/stage_reports/STAGE_R60_SPLIT_SAFE_HMM_ROUTER_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added `hmm_routed_alpha_sleeves_v2` as a research-only split-safe posterior router strategy without fitting HMMs inside the strategy or changing checked provider-cycle wiring. |
| WPR61-01-split-safe-knn-local-analog-filter | Codex Research Agent | closed | `src/tradingbotsuite/strategies/hmm_knn_local_analog_filter.py`, `src/tradingbotsuite/strategies/registry.py`, `src/tradingbotsuite/strategies/parameters.py`, `configs/strategies/hmm_knn_local_analog_filter_v2.json`, `tests/contracts/test_strategy_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/tradingbotsuite/test_hmm_knn.py`, `docs/work_packets/WPR61-01-split-safe-knn-local-analog-filter.md`, `docs/stage_reports/STAGE_R61_SPLIT_SAFE_KNN_LOCAL_ANALOG_FILTER_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added `hmm_knn_local_analog_filter_v2` as a research-only split-safe KNN local analog strategy without recomputing neighbors or changing checked provider-cycle wiring. |
| WPR62-01-liquidation-fixture-intake-foundation | Codex Research Agent | closed | `src/tradingbotsuite/research/market_data.py`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/main.py`, `tests/tradingbotsuite/test_market_data_collection.py`, `tests/contracts/test_historical_fixture_pack_contract.py`, `docs/work_packets/WPR62-01-liquidation-fixture-intake-foundation.md`, `docs/stage_reports/STAGE_R62_LIQUIDATION_FIXTURE_INTAKE_FOUNDATION_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added research-only liquidation archive intake and optional fixture-pack context materialization without implementing the classifier or changing checked provider-cycle wiring. |
| WPR63-01-liquidation-context-feature-pack | Codex Research Agent | closed | `src/tradingbotsuite/features/registry.py`, `src/tradingbotsuite/features/packs.py`, `src/tradingbotsuite/features/builders.py`, `configs/features/features_liquidation_context_v1.json`, `tests/features/test_feature_builders.py`, `tests/contracts/test_feature_contracts.py`, `docs/work_packets/WPR63-01-liquidation-context-feature-pack.md`, `docs/stage_reports/STAGE_R63_LIQUIDATION_CONTEXT_FEATURE_PACK_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added registered `features_liquidation_context_v1` with windowed liquidation materialization, explicit missingness, and no classifier or checked cycle wiring. |
| WPR64-01-checked-liquidation-fixture-evidence | Codex Research Agent | closed | `.gitignore`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `data/research/fixtures/btcusdt_liquidation_free_sample_v1/**`, `docs/runbooks/crypto_lake_free_data_runbook.md`, `tests/contracts/test_historical_fixture_pack_contract.py`, `docs/work_packets/WPR64-01-checked-liquidation-fixture-evidence.md`, `docs/stage_reports/STAGE_R64_CHECKED_LIQUIDATION_FIXTURE_EVIDENCE_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added checked BTCUSDT Crypto Lake free-sample liquidation fixture evidence with 1,440 primary bars, 1,162 liquidation context rows, diagnostic-only provenance, and validation recorded in Stage R64 report. |
| WPR65-01-liquidation-absorption-classifier | Codex Research Agent | closed | `src/tradingbotsuite/strategies/liquidation_absorption_classifier.py`, `src/tradingbotsuite/strategies/registry.py`, `src/tradingbotsuite/strategies/parameters.py`, `src/tradingbotsuite/strategies/no_trade.py`, `configs/strategies/liquidation_absorption_classifier_v1.json`, `tests/contracts/test_strategy_contracts.py`, `docs/work_packets/WPR65-01-liquidation-absorption-classifier.md`, `docs/stage_reports/STAGE_R65_LIQUIDATION_ABSORPTION_CLASSIFIER_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added research-only `liquidation_absorption_classifier_v1`, bounded metadata/config, no-trade comparator support for liquidation features, WPR64 fixture classifier validation, no checked provider-cycle wiring, and validation recorded in Stage R65 report. |
| WPR66-01-interval-aware-feature-building | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/runner.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `docs/work_packets/WPR66-01-interval-aware-feature-building.md`, `docs/stage_reports/STAGE_R66_INTERVAL_AWARE_FEATURE_BUILDING_REPORT.md`, `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added interval-aware historical-cycle feature building, feature/cache interval evidence, WPR64 1m liquidation tmp-cycle regression, 15m preservation checks, and validation recorded in Stage R66 report. |
| WPR67-01-repo-structure-dependency-fuse | Codex Research Agent | closed | `AGENTS.md`, `START_HERE.md`, `README.md`, `src/tradingbotsuite/__init__.py`, `src/tradingbotsuite/backtesting/__init__.py`, `src/tradingbotsuite/data/__init__.py`, `src/tradingbotsuite/features/__init__.py`, `src/tradingbotsuite/live/__init__.py`, `src/tradingbotsuite/research_artifacts/__init__.py`, `src/tradingbotsuite/research_cycle/__init__.py`, `src/tradingbotsuite/strategies/__init__.py`, `src/tradingbotsuite/ui/research_app.py`, `tests/integration/test_research_ui.py`, `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`, `docs/work_packets/WPR67-01-repo-structure-dependency-fuse.md`, `docs/stage_reports/STAGE_R67_REPO_STRUCTURE_DEPENDENCY_FUSE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Final review found no P0/P1 blockers, added the repo structure/dependency fuse and critical pointers, hardened standalone research UI path/live execution boundaries, and passed compile, focused UI, contracts, live, import-boundary, and full-suite validation. |
| WPR68-01-operator-quickstart-documentation | Codex Research Agent | closed | `README.md`, `docs/OPERATOR_QUICKSTART.md`, `docs/OPERATOR_GUIDE.md`, `src/tradingbotsuite/operator_console.py`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/work_packets/WPR68-01-operator-quickstart-documentation.md`, `docs/stage_reports/STAGE_R68_OPERATOR_QUICKSTART_DOCUMENTATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added compact operator quickstart, linked it from README and the long operator guide, exposed it first in UI Guides, and passed compile, operator UI tests, and diff check. |
| WPR69-01-operator-research-tab-expansion | Codex Research Agent | closed | `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/work_packets/WPR69-01-operator-research-tab-expansion.md`, `docs/stage_reports/STAGE_R69_OPERATOR_RESEARCH_TAB_EXPANSION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Expanded Research tab explanations, added read-only profitability/research chart panels, added historical research-cycle artifact summaries, and passed compile, operator UI tests, script parse check, and diff check. |
| WPR70-01-operator-research-product-redesign | Codex Research Agent | closed | `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/work_packets/WPR70-01-operator-research-product-redesign.md`, `docs/stage_reports/STAGE_R70_OPERATOR_RESEARCH_PRODUCT_REDESIGN_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Rebuilt the operator Research tab as a preset-driven research control room with explained stages, current historical-cycle review, evidence charts, and guarded signal-history diagnostics; validation passed. |
| WPR71-01-operator-historical-cycle-job-ux | Codex Research Agent | closed | `src/tradingbotsuite/main.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py`, `tests/historical/test_full_cycle_synthetic.py`, `docs/work_packets/WPR71-01-operator-historical-cycle-job-ux.md`, `docs/stage_reports/STAGE_R71_OPERATOR_HISTORICAL_CYCLE_JOB_UX_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added safe operator historical-cycle job execution, overwrite protection, full-run buttoning, local UI action history, robust repo-relative CLI spec resolution, and validation evidence. |
| WPR72-01-discovery-engine-agent-plan | Codex Research Agent | closed | `docs/RESEARCH_V4_DISCOVERY_ENGINE_AGENT_PLAN.md`, `docs/work_packets/WPR72-01-discovery-engine-agent-plan.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Curated the next-stage discovery-engine plan: split-safe HMM regime materialization, regime-local KNN tuning, perp/microstructure ablation boundaries, resumable snapshots, and staged implementation packets. |
| WPR72-02-discovery-feature-set-flexibility-addendum | Codex Research Agent | closed | `docs/RESEARCH_V4_DISCOVERY_ENGINE_AGENT_PLAN.md`, `docs/work_packets/WPR72-02-discovery-feature-set-flexibility-addendum.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Refined V4 plan with bounded flexible KNN feature-column sets, optional WT/WT3D handling, non-WT alternatives, feature-combination stability diagnostics, and calculation-correctness standards. |
| WPR72-03-implementation-handoff | Codex Research Agent | closed | `docs/RESEARCH_V4_IMPLEMENTATION_AGENT_HANDOFF.md`, `docs/work_packets/WPR72-03-implementation-handoff.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added a ready implementation handoff and prompt for the next agent to open WPR73 Discovery Run Manager work. |
| WPR73-01-discovery-run-manager | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `configs/discovery/**`, `tests/research_discovery/**`, `tests/contracts/test_import_boundaries.py`, `docs/work_packets/WPR73-01-discovery-run-manager.md`, `docs/stage_reports/STAGE_R73_DISCOVERY_RUN_MANAGER_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added the research-only discovery run manager foundation with specs, isolated output paths, manifests, run state, immutable placeholder trials, atomic snapshots, ledgers, resume behavior, boundary coverage, and validation recorded in Stage R73 report. |
| WPR74-01-discovery-feature-column-sets | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `configs/discovery/**`, `tests/research_discovery/**`, `tests/contracts/test_import_boundaries.py`, `docs/work_packets/WPR74-01-discovery-feature-column-sets.md`, `docs/stage_reports/STAGE_R74_DISCOVERY_FEATURE_COLUMN_SETS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added bounded discovery-side KNN feature-column set manifests and validation, checked V4 column-set config, run-manifest feature-set evidence, focused tests, and validation recorded in Stage R74 report. |
| WPR75-01-split-safe-hmm-materialization | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `configs/discovery/**`, `tests/research_discovery/**`, `docs/work_packets/WPR75-01-split-safe-hmm-materialization.md`, `docs/stage_reports/STAGE_R75_SPLIT_SAFE_HMM_MATERIALIZATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added train-only per-split HMM materialization, required posterior/router columns, artifact writer, checked config, split-safety tests, future-perturbation tests, and validation recorded in Stage R75 report. |
| WPR76-01-regime-local-knn-study-engine | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `configs/discovery/**`, `tests/research_discovery/**`, `docs/work_packets/WPR76-01-regime-local-knn-study-engine.md`, `docs/stage_reports/STAGE_R76_REGIME_LOCAL_KNN_STUDY_ENGINE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added deterministic regime-local KNN study engine, same-regime neighbor pools, prediction columns, neighbor diagnostics, artifact writer, split-safety tests, future-perturbation tests, and validation recorded in Stage R76 report. |
| WPR77-01-wt-knn-strategy-candidate-integration | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/research_cycle/spec.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/strategies/hmm_knn_local_analog_filter.py`, `tests/research_discovery/**`, `tests/contracts/test_research_cycle_contract.py`, `tests/contracts/test_strategy_contracts.py`, `docs/work_packets/WPR77-01-wt-knn-strategy-candidate-integration.md`, `docs/stage_reports/STAGE_R77_WT_KNN_STRATEGY_CANDIDATE_INTEGRATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added opt-in historical-cycle materialized prediction overlays, overlay identity/hash evidence, split-safe HMM/KNN overlay validation, discovery strategy accounting artifacts, executable HMM/KNN local analog signals, focused tests, full contracts, and temp overlay smoke validation. |
| WPR78-01-perp-context-filter-ablation-matrix | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `configs/discovery/**`, `tests/research_discovery/**`, `docs/work_packets/WPR78-01-perp-context-filter-ablation-matrix.md`, `docs/stage_reports/STAGE_R78_PERP_CONTEXT_FILTER_ABLATION_MATRIX_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added discovery-side perp/filter ablation matrix evaluation, checked config, feature-combination stability diagnostics, default-filter guardrails, artifact writer, focused tests, and validation evidence. |
| WPR79-01-discovery-exit-lab | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `configs/discovery/**`, `tests/research_discovery/**`, `docs/work_packets/WPR79-01-discovery-exit-lab.md`, `docs/stage_reports/STAGE_R79_DISCOVERY_EXIT_LAB_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added discovery-side exit lab evaluation, checked config, trade-density-gated exit family comparisons, artifact writer, focused tests, and validation evidence. |
| WPR80-01-operator-discovery-ui | Codex Research Agent | closed | `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/work_packets/WPR80-01-operator-discovery-ui.md`, `docs/stage_reports/STAGE_R80_OPERATOR_DISCOVERY_UI_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added guarded operator discovery launch/resume jobs, isolated discovery output rewriting, discovery artifact summaries for state/snapshots/ledgers/blockers, Research-tab controls and charting, focused operator tests, and validation evidence. |
| WPR81-01-deep-discovery-benchmarks | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/command_registry.py`, `configs/discovery/**`, `tests/research_discovery/**`, `tests/live/test_preflight.py`, `docs/work_packets/WPR81-01-deep-discovery-benchmarks.md`, `docs/stage_reports/STAGE_R81_DEEP_DISCOVERY_BENCHMARKS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added quick/standard/deep discovery benchmark tiers, resume-vs-uninterrupted ledger equality checks, snapshot and trial integrity checks, artifact overhead gate, CLI command, live-preflight research-command registration, focused tests, and validation evidence. |
| WPR82-01-candidate-pack-bridge | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/research/command_registry.py`, `configs/discovery/**`, `tests/research_discovery/**`, `tests/live/test_preflight.py`, `docs/work_packets/WPR82-01-candidate-pack-bridge.md`, `docs/stage_reports/STAGE_R82_CANDIDATE_PACK_BRIDGE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added a research-only discovery candidate-pack eligibility bridge that validates completed discovery run state, ledgers, trial hashes, and existing historical-cycle candidate gates, writes audit artifacts only, registers the CLI as live-rejected research, and preserves candidate-pack writer ownership. |
| WPR83-01-discovery-review-hardening | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/research/command_registry.py`, `src/tradingbotsuite/main.py`, `src/tradingbotsuite/web/operator.py`, `tests/research_discovery/**`, `tests/live/test_preflight.py`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/work_packets/WPR83-01-discovery-review-hardening.md`, `docs/stage_reports/STAGE_R83_DISCOVERY_REVIEW_HARDENING_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Fixed discovery review findings: KNN label-horizon leakage, selected WT3D comparator enforcement, resume missing-trial checks, bridge ledger/state/trial tamper false positives, artifact overwrite risks, operator artifact path allowlisting, and live rejection for `run-discovery`; validation recorded in Stage R83 report. |
| WPR84-01-full-research-run-fix | Codex Research Agent | closed | `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/web/templates/research.html`, `tests/historical/test_full_cycle_local_fixture_pack.py`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/work_packets/WPR84-01-full-research-run-fix.md`, `docs/stage_reports/STAGE_R84_FULL_RESEARCH_RUN_FIX_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Removed impossible perp-context ablation comparator false blockers, queued V4 discovery from the full-review UI, preserved research-only gates, and recorded validation in Stage R84 report. |
| WPR85-01-real-discovery-search-alignment | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/templates/research.html`, `configs/discovery/**`, `tests/research_discovery/**`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/work_packets/WPR85-01-real-discovery-search-alignment.md`, `docs/stage_reports/STAGE_R85_REAL_DISCOVERY_SEARCH_ALIGNMENT_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Standard/deep discovery now generate bounded real HMM/KNN trials, operator defaults to standard real discovery, deep harvest is available for long unattended runs, quick smoke remains plumbing-only, completed-run collisions are avoided, and validation is recorded in the Stage R85 report. |
| WPR86-01-discovery-runtime-optimization | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `configs/discovery/**`, `tests/research_discovery/**`, `docs/work_packets/WPR86-01-discovery-runtime-optimization.md`, `docs/stage_reports/STAGE_R86_DISCOVERY_RUNTIME_OPTIMIZATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added bounded threaded trial evaluation, in-run HMM reuse, compact blocked-trial artifacts, feature preflight, clean all-NaN scaler handling, measured runtime improvement, and validation recorded in the Stage R86 report. |
| WPR87-01-knn-vectorized-prediction | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/knn_study.py`, `tests/research_discovery/test_knn_study.py`, `docs/work_packets/WPR87-01-knn-vectorized-prediction.md`, `docs/stage_reports/STAGE_R87_KNN_VECTORIZED_PREDICTION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Split-local KNN validation prediction now transforms validation rows once per split, preserves row outputs and split-safety evidence, and validation is recorded in Stage R87 report. |
| WPR88-01-discovery-hmm-label-cache | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/runner.py`, `tests/research_discovery/test_discovery_runner.py`, `docs/work_packets/WPR88-01-discovery-hmm-label-cache.md`, `docs/stage_reports/STAGE_R88_DISCOVERY_HMM_LABEL_CACHE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Cached discovery label/split preparation, reused HMM materializations across label horizons without label leakage, added cache-hit telemetry, and validation is recorded in Stage R88 report. |
| WPR89-01-knn-deterministic-topk | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/knn_study.py`, `tests/research_discovery/test_knn_study.py`, `docs/work_packets/WPR89-01-knn-deterministic-topk.md`, `docs/stage_reports/STAGE_R89_KNN_DETERMINISTIC_TOPK_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Replaced full KNN candidate distance sorts with deterministic partition-backed top-k while preserving tie behavior and diagnostics; validation is recorded in Stage R89 report. |
| WPR90-01-hmm-vectorized-assignment | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/hmm_materialization.py`, `tests/research_discovery/test_hmm_materialization.py`, `docs/work_packets/WPR90-01-hmm-vectorized-assignment.md`, `docs/stage_reports/STAGE_R90_HMM_VECTORIZED_ASSIGNMENT_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Replaced per-row HMM posterior/router pandas assignment with vectorized assignment, preserved output semantics, and validation is recorded in Stage R90 report. |
| WPR91-01-discovery-batched-state-checkpoints | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/runner.py`, `tests/research_discovery/test_discovery_runner.py`, `docs/work_packets/WPR91-01-discovery-batched-state-checkpoints.md`, `docs/stage_reports/STAGE_R91_DISCOVERY_BATCHED_STATE_CHECKPOINTS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Reduced discovery run-state write amplification by checkpointing state at batch/snapshot boundaries and recovering from durable trial records on resume; validation is recorded in Stage R91 report. |
| WPR92-01-final-branch-crosscheck | Codex Research Agent | closed | `src/tradingbotsuite/**`, `tests/**`, `configs/**`, `docs/work_packets/WPR92-01-final-branch-crosscheck.md`, `docs/stage_reports/STAGE_R92_FINAL_BRANCH_CROSSCHECK_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/**` | Final branch crosscheck fixed KNN short-side expectancy/metrics, removed stale UI docs preference, validated real discovery output, and recorded validation in Stage R92 report. |
| WPR93-01-research-branch-audit-handoff | Codex Research Agent | closed | `docs/work_packets/WPR93-01-research-branch-audit-handoff.md`, `docs/RESEARCH_BRANCH_AUDIT_AND_NEXT_STAGE_HANDOFF.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Added compact current-state research branch handoff with repo structure, completed work, latest discovery-run audit findings, next-stage recommendations, and ready prompt for a higher-capability research agent. |
| WPR93-02-expanded-repo-free-handoff | Codex Research Agent | closed | `docs/work_packets/WPR93-02-expanded-repo-free-handoff.md`, `docs/RESEARCH_BRANCH_AUDIT_AND_NEXT_STAGE_HANDOFF.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Expanded the handoff for repo-free research use with deeper architecture, discovery semantics, research questions, experiment matrices, metrics/gates, compute plan, statistical safeguards, UI/doc warnings, and separate prompts for external research and repo-access implementation agents. |
| WPR93-03-real-strategies-filters-features-plan | Codex Research Agent | closed | `docs/work_packets/WPR93-03-real-strategies-filters-features-plan.md`, `docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md`, `docs/RESEARCH_BRANCH_AUDIT_AND_NEXT_STAGE_HANDOFF.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Analyzed the external real-strategies/filter/features plan, selected useful findings, aligned them with existing data/feature/strategy/backtest/discovery infrastructure, and created the Stage R94 development roadmap. |
| WPR93-04-btc-eth-implementation-handoff-alignment | Codex Research Agent | closed | `docs/work_packets/WPR93-04-btc-eth-implementation-handoff-alignment.md`, `docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Analyzed the BTC/ETH perp implementation handoff and folded repo-aligned candidate priorities, data truthfulness rules, exit requirements, validation floors, and blocker registry guidance into the Stage R94 development roadmap. |
| WPR93-05-ui-modernization-roadmap-alignment | Codex Research Agent | closed | `docs/work_packets/WPR93-05-ui-modernization-roadmap-alignment.md`, `docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Expanded the Stage R94 UI roadmap to include Research tab modernization, fluff and legacy-copy removal, command-oriented controls, dynamic run feedback, local run history, overwrite protection, and useful charting requirements. |
| WPR94-01-regime-baseline-naming-truthfulness | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/**`, `src/tradingbotsuite/web/templates/research.html`, `configs/discovery/*.json`, `tests/research_discovery/**`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/work_packets/WPR94-01-regime-baseline-naming-truthfulness.md`, `docs/stage_reports/STAGE_R94_REGIME_BASELINE_NAMING_TRUTHFULNESS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Added explicit no-regime/GMM discovery regime modes, truthful GMM/no-HMM metadata, no-regime split-safe KNN compatibility, updated discovery configs and UI/docs wording, and recorded validation in the Stage R94 report. |
| WPR94-02-independent-event-accounting-score-v2 | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/event_accounting.py`, `src/tradingbotsuite/research_discovery/runner.py`, `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`, `src/tradingbotsuite/research_discovery/manifests.py`, `tests/research_discovery/**`, `docs/work_packets/WPR94-02-independent-event-accounting-score-v2.md`, `docs/stage_reports/STAGE_R94_INDEPENDENT_EVENT_ACCOUNTING_SCORE_V2_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Added deterministic independent-event accounting, versioned `discovery_screen_score_v2`, event-based score quality terms, score-policy resume guard, candidate-bridge ledger parity, blocker reasons, and validation evidence. |
| WPR94-03-mandatory-exit-lab-gate | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/exit_lab.py`, `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`, `src/tradingbotsuite/main.py`, `configs/discovery/discovery_exit_lab_v4.json`, `configs/discovery/discovery_candidate_pack_bridge_v4.json`, `tests/research_discovery/test_exit_lab.py`, `tests/research_discovery/test_candidate_pack_bridge.py`, `docs/work_packets/WPR94-03-mandatory-exit-lab-gate.md`, `docs/stage_reports/STAGE_R94_MANDATORY_EXIT_LAB_GATE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Added candidate-tied exit-lab gate artifacts, mandatory bridge exit-lab evidence input, hash-mismatch/fixed-holding/no-improvement blockers, CLI/config updates, and validation evidence. |
| WPR94-04-matched-filter-ablation-v2 | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/ablation_matrix.py`, `configs/discovery/perp_filter_ablation_matrix_v4.json`, `configs/discovery/filter_ablation_matrix_v5.json`, `tests/research_discovery/test_ablation_matrix.py`, `docs/work_packets/WPR94-04-matched-filter-ablation-v2.md`, `docs/stage_reports/STAGE_R94_MATCHED_FILTER_ABLATION_V2_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Added matched-filter V2 labels, strict matched no-filter comparator grouping, finite/provider-backed evidence checks, V5 filter config, default lock, and validation evidence. |
| WPR94-05-multiple-testing-stability-gate | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/multiple_testing.py`, `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`, `src/tradingbotsuite/research_discovery/__init__.py`, `src/tradingbotsuite/main.py`, `configs/discovery/discovery_candidate_pack_bridge_v4.json`, `tests/research_discovery/test_multiple_testing.py`, `tests/research_discovery/test_candidate_pack_bridge.py`, `docs/work_packets/WPR94-05-multiple-testing-stability-gate.md`, `docs/stage_reports/STAGE_R94_MULTIPLE_TESTING_STABILITY_GATE_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Added source-hash-tied multiple-testing/stability gate artifacts, bridge mandatory evidence input, candidate hash/concentration/stability blockers, CLI/config updates, and validation evidence. |
| WPR94-06-validation-floors-blocker-registry | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/validation_floors.py`, `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`, `src/tradingbotsuite/research_discovery/__init__.py`, `src/tradingbotsuite/main.py`, `configs/discovery/discovery_candidate_pack_bridge_v4.json`, `tests/research_discovery/test_validation_floors.py`, `tests/research_discovery/test_candidate_pack_bridge.py`, `docs/work_packets/WPR94-06-validation-floors-blocker-registry.md`, `docs/stage_reports/STAGE_R94_VALIDATION_FLOORS_BLOCKER_REGISTRY_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added validation-floor candidate gates, canonical blocker registry, maturity labels, experiment-budget ledger metadata, mandatory bridge validation evidence, CLI/config updates, and validation evidence. |
| WPR94-07-durable-btc-eth-public-archive-fixture-readiness | Codex Research Agent | closed | `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/data/__init__.py`, `configs/research/durable_public_archive_fixture_readiness_btcusdt_v1.json`, `configs/research/durable_public_archive_fixture_readiness_ethusdt_v1.json`, `tests/contracts/test_historical_fixture_pack_contract.py`, `tests/contracts/test_data_contracts.py`, `docs/work_packets/WPR94-07-durable-btc-eth-public-archive-fixture-readiness.md`, `docs/stage_reports/STAGE_R94_DURABLE_BTC_ETH_PUBLIC_ARCHIVE_FIXTURE_READINESS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added durable public archive fixture readiness validation, BTC/ETH readiness config templates, latest-window diagnostic blockers, aggTrade proxy claim requirement, exports, and validation evidence. |
| WPR94-08-perp-context-source-version-audit | Codex Research Agent | closed | `src/tradingbotsuite/features/builders.py`, `src/tradingbotsuite/features/packs.py`, `src/tradingbotsuite/features/registry.py`, `configs/features/features_perp_context_v3.json`, `tests/features/test_feature_builders.py`, `tests/contracts/test_feature_contracts.py`, `docs/work_packets/WPR94-08-perp-context-source-version-audit.md`, `docs/stage_reports/STAGE_R94_PERP_CONTEXT_SOURCE_VERSION_AUDIT_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added versioned `features_perp_context_v3` source eligibility, fixture-family source/version evidence, latest-window diagnostic blocking, aggTrade proxy truthfulness, config manifest, and validation evidence. |
| WPR94-09-aggtrade-orderflow-feature-pack | Codex Research Agent | closed | `src/tradingbotsuite/features/builders.py`, `src/tradingbotsuite/features/packs.py`, `src/tradingbotsuite/features/registry.py`, `configs/features/features_aggtrade_orderflow_v1.json`, `configs/features/features_price_perp_aggflow_no_wt.json`, `tests/features/test_feature_builders.py`, `tests/contracts/test_feature_contracts.py`, `docs/work_packets/WPR94-09-aggtrade-orderflow-feature-pack.md`, `docs/stage_reports/STAGE_R94_AGGTRADE_ORDERFLOW_FEATURE_PACK_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added dedicated aggTrade trade-flow proxy feature pack, manifests, combined no-WT preset without microstructure/depth fields, explicit missingness/quality flags, no-depth/true-OFI tests, and validation evidence. |
| WPR94-10-discovery-compute-telemetry-cached-knn-sweeps | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/telemetry.py`, `src/tradingbotsuite/research_discovery/neighbor_cache.py`, `src/tradingbotsuite/research_discovery/runner.py`, `src/tradingbotsuite/research_discovery/knn_study.py`, `src/tradingbotsuite/research_discovery/spec.py`, `src/tradingbotsuite/research_discovery/manifests.py`, `src/tradingbotsuite/research_discovery/__init__.py`, `configs/discovery/deep_candidate_harvest_btcusdt_v4.json`, `tests/research_discovery/test_discovery_runner.py`, `tests/research_discovery/test_knn_study.py`, `tests/research_discovery/test_discovery_spec.py`, `docs/work_packets/WPR94-10-discovery-compute-telemetry-cached-knn-sweeps.md`, `docs/stage_reports/STAGE_R94_DISCOVERY_COMPUTE_TELEMETRY_CACHED_KNN_SWEEPS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added run compute telemetry, exact deterministic neighbor-cache reuse for KNN sweeps, per-trial neighbor cache fields, parity tests, and validation evidence. |
| WPR94-11-exit-model-upgrade-remaining-edge-lab | Codex Research Agent | closed | `src/tradingbotsuite/research_discovery/exit_lab.py`, `src/tradingbotsuite/backtesting/exits.py`, `src/tradingbotsuite/backtesting/execution_sim.py`, `src/tradingbotsuite/backtesting/engine.py`, `configs/discovery/discovery_exit_lab_v4.json`, `tests/research_discovery/test_exit_lab.py`, `tests/backtesting/test_exit_policy_expansion.py`, `tests/backtesting/test_vector_engine_matches_reference.py`, `tests/contracts/test_backtest_contracts.py`, `docs/work_packets/WPR94-11-exit-model-upgrade-remaining-edge-lab.md`, `docs/stage_reports/STAGE_R94_EXIT_MODEL_UPGRADE_REMAINING_EDGE_LAB_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added basis/premium normalization, current GMM transition, KNN remaining-edge, and KNN dynamic-barrier research exits; upgraded exit-lab grouping and deferred true-HMM/depth exits; validation recorded in the Stage R94 report. |
| WPR94-12-strategy-family-matrix-existing-plugins | Codex Research Agent | closed | `configs/research/strategy_family_matrix_existing_plugins_v1.json`, `configs/research/full_cycle_btcusdt_strategy_family_matrix_v1.json`, `src/tradingbotsuite/research_cycle/spec.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/contracts/test_strategy_contracts.py`, `tests/historical/test_full_cycle_synthetic.py`, `docs/work_packets/WPR94-12-strategy-family-matrix-existing-plugins.md`, `docs/stage_reports/STAGE_R94_STRATEGY_FAMILY_MATRIX_EXISTING_PLUGINS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added a research-only strategy-family matrix using existing plugins, explicit no-trade and transparent comparators, KNN overlay constraints, current GMM truthfulness, diagnostic-only liquidation scope, BTCUSDT cycle config, WPR94-11 exit-policy parser coverage, and validation evidence. |
| WPR94-13-btc-eth-candidate-blueprint-configs | Codex Research Agent | closed | `configs/research/btc_eth_candidate_blueprints_v1.json`, `configs/research/full_cycle_btcusdt_candidate_blueprints_v1.json`, `configs/research/full_cycle_ethusdt_candidate_blueprints_blocked_v1.json`, `tests/contracts/test_strategy_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `docs/work_packets/WPR94-13-btc-eth-candidate-blueprint-configs.md`, `docs/stage_reports/STAGE_R94_BTC_ETH_CANDIDATE_BLUEPRINT_CONFIGS_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added BTC/ETH v3 candidate blueprint configs mapped to existing v2 plugins, BTCUSDT diagnostic cycle config, ETHUSDT blocked durable-fixture config, KNN deferral, required ablations, latest-window blockers, and validation evidence. |
| WPR94-14-cross-asset-btc-eth-residual-research | Codex Research Agent | closed | `configs/features/features_cross_asset_btc_eth_v2.json`, `configs/research/cross_asset_btc_eth_residual_research_v1.json`, `src/tradingbotsuite/features/packs.py`, `src/tradingbotsuite/features/registry.py`, `tests/contracts/test_feature_contracts.py`, `tests/features/test_feature_builders.py`, `tests/historical/test_full_cycle_synthetic.py`, `docs/work_packets/WPR94-14-cross-asset-btc-eth-residual-research.md`, `docs/stage_reports/STAGE_R94_CROSS_ASSET_BTC_ETH_RESIDUAL_RESEARCH_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added versioned BTC/ETH cross-asset residual features, point-in-time join/future-alignment quality flags, blocked ETH/BTC residual research metadata, missing-context tests, and validation evidence. |
| WPR94-15-operator-ui-truthfulness-modernization | Codex Research Agent | closed | `src/tradingbotsuite/web/templates/research.html`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/OPERATOR_GUIDE.md`, `docs/OPERATOR_QUICKSTART.md`, `docs/runbooks/research_ui_runbook.md`, `docs/work_packets/WPR94-15-operator-ui-truthfulness-modernization.md`, `docs/stage_reports/STAGE_R94_OPERATOR_UI_TRUTHFULNESS_MODERNIZATION_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Modernized the Research tab with Operator Board, maturity labels, routine research actions, chart missing-evidence reasons, stricter planning/promotion wording, docs/runbook updates, and validation evidence. |
| WPR94-16-final-crosscheck-review-push | Codex Research Agent | closed | See `docs/work_packets/WPR94-16-final-crosscheck-review-push.md` Allowed Paths. | Final branch crosscheck fixed review findings in discovery identity, exit-lab cost-stress gating, multiple-testing concentration evidence, validation-floor status precedence, selected-row filter evidence, and Research tab maturity/empty states. Compile, contracts, research-discovery, operator UI, full suite, static boundary scans, and diff checks passed. |
| WPR95-01-performance-candidate-selection-engine-crosscheck | Codex Research Agent | closed | `configs/research/**`, `src/tradingbotsuite/optimization/**`, `src/tradingbotsuite/research_cycle/**`, `tests/optimization/**`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `docs/work_packets/WPR95-01-performance-candidate-selection-engine-crosscheck.md`, `docs/stage_reports/STAGE_R95_PERFORMANCE_CANDIDATE_SELECTION_ENGINE_CROSSCHECK_REPORT.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md` | Added exact brute-force-equivalent search accounting, bounded compute policy, CPU aggregate parallelism, performance-plan artifacts, 15-thread research-cycle config defaults, and truthful CUDA-blocked evidence; validation recorded in Stage R95 report. |
| WPR96-01-cuda-fixed-holding-parity-and-stability-search | Codex Research Agent | closed | `docs/KNOWN_ISSUES.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/stage_reports/**`, `docs/work_packets/**`, `src/tradingbotsuite/backtesting/**`, `src/tradingbotsuite/optimization/**`, `src/tradingbotsuite/research_cycle/**`, `tests/backtesting/**`, `tests/contracts/test_backtest_contracts.py`, `tests/contracts/test_research_cycle_contract.py`, `tests/historical/test_full_cycle_synthetic.py`, `tests/historical/test_research_cycle_benchmark.py`, `tests/optimization/**`, `tests/live/test_preflight.py` | Optional `cuda_fixed_holding` backend, runtime smoke evidence, auto routing/fallback, CPU/reference validation guard, stability search counters, benchmark evidence, and validation recorded in `docs/stage_reports/STAGE_R96_GPU_ACCELERATED_STABILITY_REGION_SEARCH_REPORT.md`. |

## Gate checklist

| Requirement | Evidence | Passed |
| --- | --- | --- |
| Stage 12.1 completed | `docs/stage_reports/STAGE_12_1_EXIT_REPORT.md` | yes |
| Required feature ablation tracks represented | `tests/tradingbotsuite/test_feature_ablation.py` | yes |
| Reproducible ablation manifests and experiment specs are written | `src/tradingbotsuite/research/feature_ablation.py` | yes |
| Rejected/pending hypotheses are documented | `tests/tradingbotsuite/test_feature_ablation.py` | yes |
| In-sample-only acceptance is rejected | `tests/tradingbotsuite/test_feature_ablation.py` | yes |
| Substages 12.2-12.7 have reproducible manifests/specs | `src/tradingbotsuite/research/stage12_research.py`, `tests/tradingbotsuite/test_stage12_research_plan.py` | yes |
| Empirical Stage 12 acceptance limitation documented | `docs/stage_reports/STAGE_12_COMPLETION_LIMITATIONS.md` | yes |
| Stage 13 readiness templates and blocked report are generated | `tests/tradingbotsuite/test_stage13_readiness.py` | yes |
| Live mode rejects every registered research command | `tests/live/test_preflight.py` | yes |
| Operator Stage 13 diagnostics are read-only | `tests/tradingbotsuite/test_operator_ui.py` | yes |
| No P0 issues open | `docs/KNOWN_ISSUES.md` | no - open P0 issues were registered by WPR106-32 |
| Fewer than four unresolved P1 issues | `docs/KNOWN_ISSUES.md` | yes |

## Orchestrator decision

Decision: hold before Stage 13 execution
Reason: Stage 13 readiness planning and offline validation infrastructure is complete, but execution remains blocked. Do not run paper, shadow, testnet, or live canary Stage 13 work until real OOS/stress evidence, paper/shadow/testnet archives, rollback evidence, and explicit human approval artifacts exist.

## Historical research completion wave

Decision: R0/R1/R4/R5 foundations complete; continue holding before empirical acceptance
Reason: No P0 issues or four-P1 stop condition are open. The completed wave is explicitly limited to historical research artifacts and does not start Stage 13 paper, shadow, testnet, or live execution. Candidate acceptance remains blocked until real OOS/stress/stability evidence exists.

## Research computation foundation wave

Decision: R2/R3/R6/R7 foundations complete; continue holding before empirical acceptance
Reason: Real local backtest artifacts, split/exit/feature foundations, optimizer search spaces, and stability-region outputs are now implemented and validated as research-only artifacts. No P0 issues or four-P1 stop condition are open. Candidate acceptance and Stage 13 execution remain blocked until approved empirical evidence and human approval artifacts exist.

## Research hardening foundation wave

Decision: R6/R8/R11 foundations complete; continue holding before empirical acceptance
Reason: Lower-timeframe exit sequencing, strategy parameter metadata, and research-only candidate pack foundations are implemented and validated. Review-identified P1 risks were fixed before closure. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability, fixture, benchmark, and approval evidence exists.

## Research completion foundation wave

Decision: R9/R10/R12 foundations complete; continue holding before empirical acceptance
Reason: HMM/KNN diagnostics, validated local fixture-pack loading, and historical research-cycle benchmark gates are implemented and validated as research-only artifacts. Review-identified risks were fixed before closure. Candidate acceptance and Stage 13 execution remain blocked until long-range real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit human approval artifacts exist.

## Materialized feature cache wave

Decision: R7/R12 materialized feature cache complete; continue holding before empirical acceptance
Reason: Historical-cycle backtests now consume materialized registered feature frames with validated feature-cache artifacts and measured feature-build cache reuse. Review-identified P1/P2 risks were fixed before closure. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit human approval artifacts exist.

## Optimizer stability truthfulness wave

Decision: R5/R12 optimizer stability truthfulness complete; continue holding before empirical acceptance
Reason: Optimizer cache telemetry, duplicate-candidate hardening, validation-scoped stability regions, truthful ranking flags, durable gate reports, and pack-gate stability blockers are implemented and validated as research-only artifacts. Review-identified risks were fixed before closure. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit human approval artifacts exist.

## Backtest identity cache evidence wave

Decision: R12/R13 backtest identity cache evidence complete; continue holding before empirical acceptance
Reason: Backtest manifests now expose identity-only cache policy and cache-key components, historical rankings carry aggregate identity evidence, and benchmarks report repeat identity consistency without claiming execution-cache reuse. Reviewers found no blocking issues. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit human approval artifacts exist.

## Strategy comparator contract hardening wave

Decision: R8 strategy comparator contract hardening complete; continue holding before empirical acceptance
Reason: Historical-cycle manifests and rankings now expose baseline comparator coverage, resolved-parameter candidate identity, and strategy metadata audit fields, while strategy configs/signals fail closed on malformed research evidence. Reviewers found no blocking issues after fixes. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Metadata-backed default search wave

Decision: R4/R8 metadata-backed default search complete; continue holding before empirical acceptance
Reason: Default historical cycles now include resolved-default seed candidates plus bounded metadata-backed grid samples, with lazy capped generation, unique candidate sampling, manifest source-count evidence, and preserved comparator coverage. Review-identified boundedness and dedupe issues were fixed before closure. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Benchmark threshold and parallel evidence wave

Decision: R12 benchmark threshold and parallel evidence complete; continue holding before empirical acceptance
Reason: Historical-cycle benchmark reports now include strict regression threshold gates, evidence-complete semantics, manifest-derived live/order/cache safety checks, tracemalloc-scoped memory evidence, and clearly scoped synthetic optimizer evaluator parallel evidence. Review-identified truthfulness risks were fixed before closure. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Candidate pack fixture provenance wave

Decision: R10/R11 candidate pack fixture provenance complete; continue holding before empirical acceptance
Reason: Research candidate-pack eligibility now requires validated non-synthetic historical fixture-pack provenance, matching fixture manifest hash and identity, complete candidate-tied evidence artifacts, durable gate/stability/backtest agreement, and explicit rejection of live-adjacent cycle/evidence/backtest artifacts. Runner pack paths are derived from the durable gate and reset on write failure. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Feature ablation historical execution wave

Decision: R12/R15 feature ablation historical execution complete; continue holding before empirical acceptance
Reason: Supplied generic `ExperimentSpec` payloads now control feature, strategy, search, validation, and backtest execution when valid, with supplied dataset paths taking precedence. Generated feature-ablation specs run through real research backtests against available datasets, while no-dataset/no-split cases fail closed without placeholder empirical metrics. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Vector fixed-holding parity foundation wave

Decision: R19 vector fixed-holding parity foundation complete; continue holding before empirical acceptance
Reason: The vector backtest foundation now writes the reference artifact family for fixed-holding primary-bar research runs, matches reference trades/signals/equity/metrics across supported parity cases, rejects unsupported vector scopes, and records vector config/cache identity. It is not yet the default historical-cycle runner and makes no speed or promotion claim. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Vector cycle integration benchmark wave

Decision: R20 vector cycle integration benchmark evidence complete; continue holding before empirical acceptance
Reason: Historical research cycles now support default-reference, explicit vector fixed-holding, and auto backend routing with manifest/index/ranking evidence. Benchmark reports include reference-vs-vector behavioral parity and local runtime observations with `speed_claimed: false`. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Research exit policy expansion wave

Decision: R21 research exit policy expansion foundation complete; continue holding before empirical acceptance
Reason: Primary-bar research exit-policy foundations now support volatility-scaled barriers, regime/funding/alpha/adverse-selection exits, trailing-after-profit exits, and MAE stops with explicit context requirements and exit-policy parameter identity. Fixed-holding and lower-timeframe triple-barrier behavior are preserved, and vector execution remains fixed-holding only. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Exit policy candidate cycle wave

Decision: R22 exit policy candidate cycle evidence complete; continue holding before empirical acceptance
Reason: Historical cycles now support configured exit policies as deterministic candidate dimensions, while fixed-holding remains the default. Candidate-space manifests, rankings, backtest indexes, and optimizer cache keys include exit-policy identity. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Validation split mode cycle wave

Decision: R23 validation split mode cycle evidence complete; continue holding before empirical acceptance
Reason: Historical cycles now support configured purged, anchored, rolling, shifted, month holdout, stress-period holdout, and regime holdout validation split evidence while preserving the default purged walk-forward behavior. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Research evidence floor gates wave

Decision: R24 research evidence floor gates complete; continue holding before empirical acceptance
Reason: Historical cycle rankings and durable candidate-pack validation now enforce per-split trade floors, configured validation method coverage, cost-stress survival floors, and split dominance from evidence artifacts. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Provider context fixture pack builder wave

Decision: R35 provider context fixture pack builder complete; continue holding before empirical acceptance
Reason: The local provider fixture-pack builder can now generate optional funding, premium, open-interest, and aggregate-trade context families from already-local provider manifests while preserving research-only, observe-only, non-promotion provenance. TradingView and synthetic provenance remain rejected. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Binance USD-M context collector wave

Decision: R36 Binance USD-M context collector complete; continue holding before empirical acceptance
Reason: Research-only Binance USD-M REST collection now writes funding, premium, and open-interest context manifests that can feed the fixture-pack builder without legacy chart exports or live runtime writes. Candidate acceptance and Stage 13 execution remain blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## BTCUSDT context fixture data run wave

Decision: R37 BTCUSDT context fixture data run complete; continue holding before empirical acceptance
Reason: A generated BTCUSDT context-aware fixture pack now exists locally from provider kline cache plus collected Binance USD-M REST funding, premium, and open-interest context manifests. It is research-only and not OOS acceptance evidence. Candidate acceptance and Stage 13 execution remain blocked until full real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.

## Context fixture cycle execution wave

Decision: R38 context fixture cycle execution complete; continue holding before empirical acceptance
Reason: The historical research-cycle command now consumes the generated BTCUSDT context fixture pack end-to-end, materializes funding, premium, and open-interest context into features, writes rankings/gates/stress artifacts, and truthfully rejects all candidates with no candidate pack. The run remains compact local research evidence, not OOS acceptance, a performance claim, promotion evidence, or Stage 13 execution.

## Extended context fixture comparator cycle wave

Decision: R39 extended context fixture comparator cycle complete; continue holding before empirical acceptance
Reason: A 500-row BTCUSDT provider context fixture now records complete funding, premium, and open-interest joins within Binance USD-M open-interest row limits. A paired price/trend versus full-context trend-following cycle produced ablation comparator evidence and vector fixed-holding backtests, while all candidates remained fail-closed and no candidate pack was written. This is broader local research evidence only, not OOS acceptance or promotion evidence.

## Binance open-interest pagination and 7d context cycle wave

Decision: R40 Binance open-interest pagination and 7d context cycle complete; continue holding before empirical acceptance
Reason: The Binance USD-M open-interest collector now pages backward across the endpoint's 500-row page limit, allowing the 7-day BTCUSDT fixture to include complete 673-row open-interest context and 672 primary bars. The comparator cycle materializes all context families and remains fail-closed with no candidate pack, no promotion evidence, and no Stage 13 execution.

## Latest-month provider context cycle wave

Decision: R41 latest-month provider context cycle complete; continue holding before empirical acceptance
Reason: Fresh direct Binance USD-M REST bars plus funding, premium, and paginated open-interest context now produce a 2,873-row BTCUSDT latest-month fixture with complete context joins. The comparator cycle ran 16 candidates and 128 vector fixed-holding backtests, but all candidate gates remained blocked and no candidate pack, promotion evidence, performance claim, or Stage 13 execution was produced.

## Provider-backed benchmark evidence wave

Decision: R42 provider-backed benchmark evidence complete; continue holding before empirical acceptance
Reason: The benchmark command now has a `provider_latest_month` tier that writes non-synthetic fixture manifest specs against the WPR41 BTCUSDT context fixture. The generated benchmark report records provider-fixture scope, deterministic repeat evidence, feature-cache reuse, memory, artifact overhead, optimizer parallel evidence, and reference/vector comparison with a passed evidence-complete gate. This remains a local research benchmark and makes no live, promotion, or profit claim.

## Provider WT3D full-context ablation wave

Decision: R43 provider WT3D full-context ablation cycle complete; stop for final crosscheck
Reason: The latest-month provider fixture now has real historical-cycle ablation evidence for price/trend, full-context no-WT, and full-context WT3D feature sets. WT3D full-context candidates produced candidate-tied comparator evidence, but all candidate gates remained blocked and no candidate pack, promotion evidence, performance claim, or Stage 13 execution was produced. The research branch has reached the development-plan implementation stop point and should be crosschecked before any new stage is opened.

## Final crosscheck hardening wave

Decision: R44 final crosscheck hardening complete; ready for commit/push after final validation
Reason: Final review blockers were fixed before branch publication: provider fixture evidence is durable, benchmark paths are clean on Windows, holdout and context evidence is truthful, exit-policy identity is preserved in stability/ablation grouping, and focused validations pass. This wave does not advance empirical acceptance, does not create promotion evidence, and does not start Stage 13 execution.

## Research branch distillation wave

Decision: R45 research branch distillation complete; continue holding before empirical acceptance
Reason: The branch now has a current distillation document that explains the research framework, package ownership, stack, artifact model, provider fixture evidence, candidate gates, validation baseline, and live/promotion boundaries for future agents. This wave is documentation-only and does not advance empirical acceptance, create promotion evidence, or start Stage 13 execution.

## Perp strategy plan alignment wave

Decision: R46 perp strategy plan alignment complete; ready to open WPR47 implementation packet
Reason: The downloaded BTC/ETH perpetual strategy plan is now aligned with the current research branch naming contracts and staged into additive work packets. The curated plan preserves existing cycle spec shape, supported holding windows, feature-set naming, strategy signal contracts, exit-policy IDs, provider fixture boundaries, and fail-closed candidate gates. This wave is documentation-only and does not advance empirical acceptance, create promotion evidence, or start Stage 13 execution.

## Crypto Lake free data fallback wave

Decision: R47 Crypto Lake free data fallback complete; ready for optional local free-sample smoke tests
Reason: The branch now documents optional Crypto Lake free sample installation, anonymous sample-data mode, smoke tests, local-export ingestion, fallback pipeline inputs, and agent rules. The optional `lakeapi` dependency is isolated behind a `crypto-lake` extra, direct fetches enable `lakeapi.use_sample_data(anonymous_access=True)`, lakeapi cache output is ignored, and missing dependency failures are actionable. Local access was verified with BTCUSDT/BTC-USDT-PERP Binance Futures candles for 2025-04-06 to 2025-04-07, producing 1,440 rows with no gaps or duplicates. No provider credentials, large provider data, promotion evidence, or Stage 13 execution were added.

## Perp plan free-data refresh wave

Decision: R48 perp plan free-data refresh complete; ready to open WPR49 implementation packet
Reason: The curated perpetual agent-development plan now reflects closed WPR47 Crypto Lake free-sample fallback work, removes future paid/provider-account assumptions, defines provider source priority, and renumbers upcoming implementation packets so the next code stage starts cleanly at WPR49.

## Perp context manifest foundation wave

Decision: R49 perp context manifest foundation complete; ready to open WPR50 feature-pack implementation packet
Reason: Provider/archive context manifests now carry non-breaking retention, coverage, latest-window, role, and stream-health metadata; Binance USD-M REST latest-window context and Crypto Lake free-sample context remain explicitly diagnostic; fixed-interval gap evidence and variable-cadence non-applicability are recorded; fixture-pack context metadata propagates into family entries and source records; validation passed with focused WPR49 tests, full contract tests, provider intake smoke, import-boundary smoke, compile, and diff check.

## Perp context v2 feature pack wave

Decision: R50 perp context v2 feature pack complete; ready to open WPR51 transparent strategy implementation packet
Reason: The branch now has a registered `features_perp_context_v2` preset and config, interval-aware premium/funding/OI/flow/quality features, backward-as-of context materialization tests across current context families, cache context-identity coverage, and clean focused, contract, and selected historical validation. Missing optional context remains explicit and non-zero-filled.

## Perp basis convergence strategy wave

Decision: R51 perp basis convergence strategy complete; ready to open WPR52 provider-backed cycle evidence packet
Reason: The branch now has a registered `perp_basis_convergence_v2` strategy and checked config, bounded metadata, conservative carry-adjusted basis/premium rules, fail-closed v2 quality requirements, latest-window provenance handling, and focused contract, integration, contract-suite, and historical-smoke validation. The strategy remains a research-only single-leg directional convergence proxy and does not add live execution or promotion behavior.

## Provider perp context cycle evidence wave

Decision: R52 provider perp context cycle evidence complete; ready for WPR53 planning
Reason: The branch now has a checked BTCUSDT provider-backed perp-context-v2 cycle spec, `baseline_no_trade` comparator support for `features_perp_context_v2`, local cycle artifacts under `data/research/historical_cycles/btcusdt_perp_context_v2_foundation`, complete no-trade comparator coverage, and a truthful fail-closed gate result with no candidate pack written. Validation passed compile, focused WPR52 tests, research-cycle contracts, full historical tests, strategy contracts, and diff check.

## Funding crowding fade strategy wave

Decision: R53 funding crowding fade strategy complete; ready for WPR54 planning
Reason: The branch now has a registered `funding_crowding_fade_v2` strategy and checked config, bounded metadata, fail-closed funding/premium/OI/quality context requirements, checked-cycle inclusion, complete no-trade comparator coverage, local provider-cycle evidence with 37 aggregate funding-crowding trades across candidates, and a truthful fail-closed gate result with no candidate pack written. Validation passed compile, focused strategy/integration tests, checked historical test, WPR53 validation suite, and diff check.

## OI flow breakout strategy wave

Decision: R54 OI flow breakout strategy complete; ready for WPR55 planning
Reason: The branch now has a registered `oi_flow_breakout_v2` strategy and checked config, bounded metadata, fail-closed OI/premium/quality context requirements, optional flow confirmation for fixtures without durable `agg_trade`, checked-cycle inclusion, complete no-trade comparator coverage, local provider-cycle evidence with 197 aggregate OI-flow trades across candidates, and a truthful fail-closed gate result with no candidate pack written. Validation passed compile, focused strategy/integration tests, checked historical test, WPR54 validation suite, and full contracts.

## Funding window timing strategy wave

Decision: R55 funding window timing strategy complete; ready for WPR56 planning
Reason: The branch now has a registered `funding_window_timing_v1` strategy and checked config, bounded metadata, fail-closed funding-window timing, funding stretch, premium/basis, OI, and quality requirements, checked-cycle inclusion, complete no-trade comparator coverage, local provider-cycle evidence with 5 aggregate funding-window trades across candidates, and a truthful fail-closed gate result with no candidate pack written. Validation passed compile, focused strategy/integration tests, checked historical test, WPR55 validation suite, and full contracts.

## ETHUSDT fixture mirror cycle evidence wave

Decision: R56 ETHUSDT fixture mirror cycle evidence complete; ready for WPR57 planning
Reason: The branch now has a durable 2,810-row ETHUSDT provider-backed perp-context fixture, a checked `full_cycle_ethusdt_perp_context_v2` spec, bounded Binance open-interest pagination for current endpoint limits, complete funding/premium/open-interest context joins, latest-window provenance propagated into feature quality flags, local mirror-cycle evidence with transparent-strategy trades, and a truthful fail-closed gate result with no candidate pack written. Validation passed focused pagination, fixture, historical-cycle, and WPR56 suites.

## Funding-aware exit policy wave

Decision: R57 funding-aware exit policy complete; ready for WPR58 planning
Reason: The branch now has a primary-bar `funding_aware_exit_v1` research exit policy, checked BTCUSDT and ETHUSDT perp-context-v2 cycle configs include both fixed-holding and funding-aware exits, vector execution still rejects non-fixed exits, local provider-cycle evidence remains fail-closed with no candidate pack written, and validation passed WPR57 focused tests.

## OI contraction exit policy wave

Decision: R58 OI contraction exit policy complete; ready for WPR59 planning
Reason: The branch now has a primary-bar `oi_contraction_exit_v1` research exit policy, checked BTCUSDT and ETHUSDT perp-context-v2 cycle configs include fixed-holding, funding-aware, and OI-contraction exits, vector execution still rejects non-fixed exits, local provider-cycle evidence remains fail-closed with no candidate pack written, and validation passed WPR58 focused tests.

## Trial-budget and overfit diagnostics wave

Decision: R59 trial-budget and overfit diagnostics complete; ready for WPR60 planning
Reason: Historical research cycles now write `trial_budget_report.json` and `overfit_adjustment_report.json` as reproducible research-only diagnostic outputs. Candidate-pack validation requires the artifacts to exist, but diagnostic scores remain report-only and do not alter pack metric gates, promotion gates, or live readiness. Checked BTCUSDT and ETHUSDT cycles remain fail-closed with no candidate pack written.

## Split-safe HMM router wave

Decision: R60 split-safe HMM router complete; ready for WPR61 planning
Reason: The branch now has a registered `hmm_routed_alpha_sleeves_v2` research strategy that consumes existing split-safe HMM posterior columns and requires `hmm_fit_end_row < source_row_index` before emitting standard research-only signals. It is a normal research candidate, not a comparator baseline. Checked provider-cycle configs remain unchanged until posterior materialization is explicitly added.

## Split-safe KNN local analog filter wave

Decision: R61 split-safe KNN local analog filter complete; WPR62 requires liquidation fixture planning before classifier work
Reason: The branch now has a registered `hmm_knn_local_analog_filter_v2` research strategy that consumes existing KNN/HMM artifact columns and requires `neighbor_min_source_index <= neighbor_max_source_index <= hmm_fit_end_row < source_row_index` before emitting standard research-only signals. It is a normal research candidate, not a comparator baseline. Checked provider-cycle configs remain unchanged until KNN prediction materialization is explicitly added.

## Liquidation fixture intake foundation wave

Decision: R62 liquidation fixture intake foundation complete; classifier remains gated on liquidation features or checked fixture evidence
Reason: The branch now accepts research-only Crypto Lake `liquidation` archive rows, preserves diagnostic-only provider metadata, and can materialize `liquidation` as an optional historical fixture-pack context family with deterministic same-timestamp aggregation. No classifier, liquidation feature set, checked provider-cycle wiring, live behavior, or promotion evidence was added.

## Liquidation context feature pack wave

Decision: R63 liquidation context feature pack complete; checked liquidation fixture evidence required before classifier or cycle wiring
Reason: The branch now has a registered `features_liquidation_context_v1` feature set backed by `liquidation_context_v1`, with event-window materialization for optional liquidation context and explicit missingness for unknown windows. Checked BTCUSDT/ETHUSDT cycles, classifier work, live behavior, and promotion evidence remain unchanged.

## Checked liquidation fixture evidence wave

Decision: R64 checked liquidation fixture evidence complete; ready to open classifier implementation packet
Reason: The branch now has a checked BTCUSDT Crypto Lake free-sample liquidation fixture pack with matching 1m candles and real liquidation context rows. The fixture is research-only, observe-only, promotion-ready false, and diagnostic-only free-sample evidence. It is sufficient to support local classifier implementation and tests, but not broad OOS/stress acceptance, checked BTCUSDT/ETHUSDT provider-cycle wiring, candidate-pack eligibility, promotion evidence, or live behavior.

## Liquidation absorption classifier wave

Decision: R65 liquidation absorption classifier complete; stop before cycle wiring
Reason: The branch now has a registered research-only `liquidation_absorption_classifier_v1` strategy consuming `features_liquidation_context_v1`, with bounded metadata, checked config, fail-closed quality/context gates, empty accepted-signal skip reasons, and WPR64 checked-fixture validation. Checked BTCUSDT/ETHUSDT provider-cycle configs, candidate-pack eligibility, promotion evidence, live behavior, and performance claims remain unchanged. Local liquidation cycle evidence should first resolve interval-aware cycle feature building for the 1m WPR64 fixture or use a separately built 15m liquidation fixture.

## Interval-aware feature building wave

Decision: R66 interval-aware feature building complete; ready for optional checked liquidation cycle planning
Reason: Historical research-cycle feature building now resolves primary bar interval from fixture/source evidence before feature-cache identity and registered feature materialization. The WPR64 BTCUSDT 1m Crypto Lake free-sample liquidation fixture now has tmp-output cycle regression coverage with 1m feature times and cache identity, while 15m fixture behavior remains covered. No checked BTCUSDT/ETHUSDT provider-cycle wiring, candidate-pack eligibility, promotion evidence, live behavior, or performance claim was added.

## Repo structure dependency fuse wave

Decision: R67 final structure crosscheck and dependency fuse complete; development goals remain complete outside live/promotion execution
Reason: Final review found no open P0/P1 blockers. The branch now has a visible repo architecture, dependency, workflow, and unsafe-to-rewrite fuse document with pointers in onboarding docs and critical package roots. The standalone research UI now shares stronger command-boundary behavior for spec/output allowlists and live-mode execution rejection. This wave does not change research-cycle semantics, feature math, strategy behavior, checked artifacts, live execution, promotion readiness, or performance claims.

## Operator quickstart documentation wave

Decision: R68 operator quickstart documentation complete; operator-facing compact run card is ready
Reason: The branch now has a compact `docs/OPERATOR_QUICKSTART.md` with ready-to-use commands, page explanations, safe daily workflow, button rules, safety-response table, research-job boundaries, live/testnet checklist, shell fallback, common fixes, and stop conditions. The operator UI exposes it as the first Guides document. This wave is documentation/UI-guide wiring only and does not change operator command behavior, live execution, research execution, promotion behavior, or generated artifacts.

## Operator research tab expansion wave

Decision: R69 operator research tab expansion complete; Research page now covers the full research branch
Reason: The operator Research tab now explains data intake, feature construction, strategy research, backtests/exits, optimizer/gates, and promotion boundaries instead of presenting the page as mostly HMM/KNN. It adds read-only chart panels for profitability, candidate mix, gate status, and holding windows, backed by existing model/HMM metrics and historical research-cycle artifacts. This wave is UI/artifact-summary only and does not change operator commands, research execution, live execution, promotion behavior, generated artifacts, or research-only boundaries.

## Operator research product redesign wave

Decision: R70 operator research product redesign complete; Research page is now the current-branch research control room
Reason: The operator Research tab now starts from operator intent, uses preset-driven provider and experiment controls, explains intake/dataset/evidence/all stages inline, provides exact historical-cycle review commands, keeps current artifact charts and diagnostics prominent, and moves older signal-history model tooling into advanced diagnostics. This wave is UI/template and focused test coverage only; it does not change provider execution, research-cycle execution, live execution, promotion behavior, generated evidence, or research-only boundaries.

## Operator historical-cycle job UX wave

Decision: R71 operator historical-cycle job UX complete; historical-cycle review is button-driven and overwrite-protected
Reason: The operator Research tab now queues historical research cycles through a safe operator job endpoint that rewrites checked specs into isolated job-specific output directories under the configured research output root. The page also has a full research review button, browser-local action history, clearer active/latest job status, and PowerShell commands that change into the repo root. The CLI now resolves repo-relative historical-cycle spec paths from outside the repo. This wave does not change historical-cycle research semantics, live execution, promotion behavior, or research-only boundaries.

## Discovery engine planning wave

Decision: R72 discovery engine planning complete; ready to open WPR73 discovery run manager implementation
Reason: The branch now has a repo-native V4 discovery-engine agent plan that digests the latest operator research direction and sparse idea notes into additive implementation packets. The plan keeps perp/microstructure context semi-separate until ablation evidence exists, defines HMM as a split-safe regime materialization layer, defines regime-local KNN studies and WT/KNN high-signal entry discovery, and requires resumable day-long runs with 30-minute snapshots. This wave is planning-only and does not change research execution, live execution, promotion behavior, generated artifacts, or candidate-pack gates.

## Discovery feature-set flexibility addendum wave

Decision: R72 addendum complete; WPR73 remains the next implementation entry point
Reason: The V4 discovery plan now treats KNN feature-column sets as bounded research variables rather than fixed truth or uncontrolled brute-force search. It distinguishes registered feature-set manifests from KNN column-set variants, treats WT and WT3D as optional candidates rather than privileged defaults, requires non-WT alternatives, adds feature-combination stability diagnostics separate from the existing region-of-stability gate, and adds calculation-correctness standards for future implementation agents. This wave is documentation-only and does not change research execution, feature math, live execution, promotion behavior, generated artifacts, or candidate-pack gates.

## Implementation handoff wave

Decision: R72 handoff complete; next agent should open WPR73 Discovery Run Manager
Reason: The branch now has a concise V4 implementation handoff with a ready prompt for the next agent. It directs WPR73 to build the discovery run manager foundation first: specs, isolated output paths, run manifests, run state, immutable trial records, atomic snapshots, resume behavior, and focused tests. This wave is documentation-only and does not change research execution, feature math, live execution, promotion behavior, generated artifacts, or candidate-pack gates.

## Discovery run manager foundation wave

Decision: R73 discovery run manager foundation complete; ready to open WPR74 core discovery feature-pack planning/implementation
Reason: The branch now has a research-only `tradingbotsuite.research_discovery` package that parses discovery specs, resolves isolated output directories under the configured research output root, writes run manifests and resolved specs, maintains resumable run state, records immutable placeholder trials, writes atomic snapshots, and maintains interesting/blocked/filter-blocker ledgers. The new package is covered by import-boundary tests and focused resume/snapshot/state tests. This wave intentionally does not add feature math, HMM materialization, KNN search, optimizer changes, UI behavior, candidate-pack bridge behavior, promotion readiness, or live execution.

## Discovery feature-column set foundation wave

Decision: R74 discovery feature-column set foundation complete; ready to open WPR75 split-safe HMM materialization planning/implementation
Reason: The branch now has a bounded discovery-side feature-column set manifest contract that keeps KNN study column sets separate from registered `features_*` manifests, validates selected columns against existing feature manifests, requires WT3D sets to keep no-WT comparators, includes a first-class non-WT alternative, and records selected feature-column set evidence in discovery run manifests. This wave selects existing feature columns only and does not add feature math, HMM materialization, KNN search, optimizer changes, UI behavior, candidate-pack bridge behavior, promotion readiness, or live execution.

## Split-safe HMM materialization foundation wave

Decision: R75 split-safe HMM materialization foundation complete; ready to open WPR76 regime-local KNN study engine planning/implementation
Reason: The branch now has a discovery-side HMM materializer that fits Gaussian mixture regimes only on each split's training rows, applies train-only scaling, emits existing strategy-consumer posterior columns plus `hmm_model_id`, `hmm_feature_pack_id`, and `hmm_split_id`, writes HMM materialization artifacts, and proves `hmm_fit_end_row < source_row_index` with focused tests including future-row perturbation. This wave does not add KNN search, strategy candidate wiring, optimizer changes, UI behavior, candidate-pack bridge behavior, promotion readiness, or live execution.

## Regime-local KNN study foundation wave

Decision: R76 regime-local KNN study foundation complete; ready to open WPR77 WT/KNN strategy candidate integration planning/implementation
Reason: The branch now has a deterministic discovery-side regime-local KNN reference engine that consumes split-safe HMM rows, fits scalers on train rows only, restricts local analog pools to prior same-regime neighbors by default, emits existing HMM/KNN strategy prediction columns, writes neighbor diagnostics and KNN study artifacts, and proves neighbor safety with focused future-perturbation tests. This wave does not wire strategy candidates into historical cycles, change optimizer behavior, expose UI controls, bridge candidate packs, claim promotion readiness, or add live execution.

## WT/KNN strategy candidate integration wave

Decision: R77 WT/KNN strategy candidate integration complete; ready to open WPR78 perp context and filter ablation matrix planning/implementation
Reason: Historical research-cycle specs now support explicit materialized prediction overlays for split-safe HMM/KNN discovery outputs, the runner validates research-only overlay manifests, approved columns, one-to-one alignment, and accepted-neighbor split safety before candidate backtests, and feature-build identity records include post-overlay frame hashes. Discovery now writes strategy accounting for raw accepted KNN rows, plugin signals, executable signals, filter blocks, and optional executed trades. `hmm_knn_local_analog_filter_v2` active signals are executable by the standard backtest path. This wave does not change checked BTCUSDT/ETHUSDT configs, optimizer gates, UI behavior, candidate-pack promotion, live execution, or promotion readiness.

## Perp context filter ablation matrix wave

Decision: R78 perp context and filter ablation matrix complete; ready to open WPR79 exit lab planning/implementation
Reason: The discovery package now writes a research-only perp/filter ablation matrix that compares no-perp references, perp feature additions, HMM/KNN filter treatments, perp strategies, and perp-aware exits against configured comparators. Default-filter use remains blocked unless a treatment wins with comparator evidence, trade-count floors, and missingness floors. Discovery feature-column sets now have separate feature-combination stability diagnostics for no-WT, WT3D, non-WT alternatives, and pending evidence without changing the optimizer region-of-stability gate. This wave does not change checked BTCUSDT/ETHUSDT historical-cycle configs, candidate-pack gates, promotion readiness, operator UI, live execution, or sizing.

## Discovery exit lab wave

Decision: R79 discovery exit lab complete; ready to open WPR80 operator discovery UI planning/implementation
Reason: The discovery package now writes a research-only exit lab matrix and family summary that compare fixed-holding references, barrier exits, funding/OI exits, HMM/KNN-adjacent exits, and trailing/risk-control exits only after fixed-holding entry candidates satisfy configured trade-density floors. Missing HMM/KNN exit evidence remains pending, low-density entries are skipped, and winners remain research-only diagnostics. This wave does not add exit policy math, change checked BTCUSDT/ETHUSDT historical-cycle configs, alter candidate-pack gates, claim promotion readiness, expose UI controls, add live execution, or affect sizing.

## Operator discovery UI wave

Decision: R80 operator discovery UI complete; ready to open WPR81 deep discovery benchmarks planning/implementation
Reason: The operator Research tab can now queue guarded V4 discovery runs with stop-after-trials and resume controls, rewriting specs into the configured research output root and preserving research-job live/safety blocks. Discovery run artifacts are visible as observe-only cards and charts with state, snapshots, candidate ledgers, blocker counts, and research-only boundary flags. This wave does not change discovery math, historical-cycle semantics, checked BTCUSDT/ETHUSDT configs, candidate-pack gates, promotion readiness, live execution, or sizing.

## Deep discovery benchmarks wave

Decision: R81 deep discovery benchmarks complete; ready to open WPR82 candidate pack bridge planning/implementation
Reason: The branch now has research-only quick, standard, and deep discovery benchmark tiers that generate isolated discovery specs, compare uninterrupted runs with interrupted/resumed runs, verify completed-ledger hash equality, validate snapshot readability and final state agreement, check immutable trial-record hashes, and gate artifact overhead without making performance, profit, promotion, or live-readiness claims. The new `benchmark-discovery-run` CLI is registered as a research command and rejected in live preflight. This wave does not change discovery math, historical-cycle semantics, checked BTCUSDT/ETHUSDT configs, candidate-pack gates, promotion readiness, live execution, or sizing.

## Candidate pack bridge wave

Decision: R82 candidate pack bridge complete; V4 discovery implementation can continue with post-bridge planning
Reason: The branch now has a research-only discovery candidate-pack eligibility bridge that evaluates completed discovery-run candidates against the existing historical-cycle `evaluate_research_candidate_gate` validator, requires intact discovery state, ledgers, and trial-record hashes, blocks discovery-only or blocker-ledger candidates, and writes observe-only eligibility/rejection artifacts with `candidate_pack_written: false`. The new `evaluate-discovery-candidate-pack-eligibility` CLI is registered as a research command and rejected in live preflight. This wave does not write candidate packs, change historical-cycle semantics, weaken candidate-pack gates, claim promotion readiness, add live execution, or affect sizing.

## KNN vectorized prediction wave

Decision: R87 KNN vectorized prediction complete; discovery runtime optimization can continue from measured bottlenecks.
Reason: The regime-local KNN study now transforms validation rows once per split and predicts from precomputed numpy vectors while preserving the row helper, output columns, neighbor diagnostics, split-safety rule, label-safety rule, and research-only manifest boundary. Focused KNN equivalence coverage, full discovery tests, quick discovery benchmark, compile, and contracts pass. This wave does not change candidate-pack gates, historical-cycle semantics, promotion readiness, live execution, or sizing.

## Discovery HMM label cache wave

Decision: R88 discovery HMM label cache complete; next target is grouped KNN top-k optimization.
Reason: Real discovery runs now cache horizon-labeled frames and splits, reuse HMM regime materializations across label horizons by grafting cached HMM posterior/router columns onto the current horizon-labeled frame, and expose cache-hit telemetry in trial records. Regression coverage proves HMM reuse does not leak labels into KNN trials. Focused runner tests, full discovery tests, compile, contracts, and a 10-trial deep-shaped probe passed. This wave does not change candidate-pack gates, historical-cycle semantics, promotion readiness, live execution, or sizing.

## KNN deterministic top-k wave

Decision: R89 KNN deterministic top-k complete; next target is HMM assignment and discovery IO profiling/optimization.
Reason: The KNN study now selects nearest neighbors through partition-backed deterministic top-k selection, preserves full stable-sort tie behavior at the kth-distance boundary, and records the selection engine in KNN manifests. Focused KNN tests, full discovery tests, compile, contracts, and a 10-trial deep-shaped probe passed. This wave does not change candidate-pack gates, historical-cycle semantics, promotion readiness, live execution, or sizing.

## HMM vectorized assignment wave

Decision: R90 HMM vectorized assignment complete; discovery CPU optimization wave is complete enough for operator deep-harvest use on the checked latest-month fixture.
Reason: HMM posterior/router output assignment now uses vectorized column writes, preserves scalar-reference output semantics, and records the assignment engine in HMM manifests. Focused HMM tests, full discovery tests, compile, contracts, and a 10-trial deep-shaped probe passed. The probe improved from the R88/R89 roughly 22.5-second range to 13.245 seconds, projecting about 1.84 hours for 5,000 trials on the local checked fixture slice. This wave does not change candidate-pack gates, historical-cycle semantics, promotion readiness, live execution, or sizing.

## Discovery batched state checkpoints wave

Decision: R91 discovery batched state checkpoints complete; discovery IO optimization can continue with append/checkpoint ledgers if needed.
Reason: Discovery now writes durable trial records per trial but checkpoints run state at setup, resume merge, snapshot, pause, completion, and final boundaries rather than after every trial. Resume rebuilds completed state from trial records when `run_state.json` lags. Focused runner tests, full discovery tests, compile, contracts, and a 10-trial deep-shaped probe passed. The probe completed in 10.967 seconds, projecting about 1.52 hours for 5,000 trials on the local checked fixture slice. This wave does not change candidate-pack gates, historical-cycle semantics, promotion readiness, live execution, or sizing.

## Final branch crosscheck wave

Decision: R92 final branch crosscheck complete; research/v3-experimental-engine is clean for handoff/push.
Reason: The audit found and fixed one material KNN logic issue: short-majority local analog rows now use side-adjusted expectancy and discovery metrics use side-adjusted realized returns. Operator guide lookup now prefers canonical current docs, the research UI runbook and operator docs match the current Research page, and the removed-source boundary test no longer contains forbidden legacy vendor text. Official NumPy/scikit-learn/pandas docs were checked for deterministic top-k, Gaussian mixture posterior, and vectorized assignment assumptions. Focused HMM/KNN/discovery/UI/contracts validation, a real four-trial discovery probe, the deep discovery benchmark gate, compile, and the full test suite passed. This wave preserves research-only, observe-only, non-promotion boundaries and does not add live execution, candidate-pack promotion, or sizing behavior.

## Regime baseline and naming truthfulness wave

Decision: R94-01 regime baseline and naming truthfulness complete; ready to open WPR94-02 independent event accounting and score redesign.
Reason: Discovery specs now generate explicit `regime_mode` trials for no-regime, GMM gate-only, GMM same-regime-neighbor, and GMM all-regime-with-gate modes. Trial records, ledgers, KNN manifests, GMM/no-regime materialization manifests, and run manifests record `regime_detector_type`, gate/pool booleans, and `true_hmm_backend_used: false`. No-regime trials produce split-safe compatibility columns without fitting GMM or applying `regime_no_trade`, while existing downstream HMM-compatible columns remain stable for strategy contracts. Focused discovery, candidate-bridge, operator UI, compile, contracts, and full research-discovery validation passed. This wave does not add true HMM, independent-event scoring, exit-gate changes, candidate-pack promotion, live execution, or sizing behavior.

## Independent event accounting and score v2 wave

Decision: R94-02 independent event accounting and score v2 complete; ready to open WPR94-03 mandatory exit-lab gate.
Reason: Real discovery trials now collapse accepted KNN rows into deterministic same-symbol independent events before calculating `trade_count`, `realized_expectancy`, `gross_realized_return`, `score`, and `final_score`. `final_score` maps to versioned `discovery_screen_score_v2`, while `legacy_density_score` remains diagnostic. Score-v2 quality and vote-margin terms are event-based, new blocker reasons expose event-count/overlap/signal-ceiling/side-collapse failures, ledgers and the candidate-pack bridge carry the new fields, and resume fails closed for old real discovery score policies. Focused event/runner/bridge tests, full research-discovery tests, contracts, compile, and diff checks passed. This wave does not add exit-lab gate changes, candidate-pack promotion, live execution, live config writes, order placement, or sizing behavior.

## Mandatory exit-lab gate wave

Decision: R94-03 mandatory exit-lab gate complete; ready to open WPR94-04 matched filter ablation v2.
Reason: Discovery exit-lab artifacts now write candidate-tied gate rows with fixed-holding comparator deltas, cost-stress status, non-fixed best exit family, and deterministic entry-lead evidence hashes. The discovery candidate-pack bridge now requires an exit-lab manifest and blocks missing evidence, absent candidate gate rows, entry-lead hash mismatches, fixed-holding-only evidence, and no-improvement exit evidence before applying the existing historical-cycle candidate gate. Focused exit-lab/bridge tests, full research-discovery tests, contracts, compile, and diff checks passed. This wave does not write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Matched filter ablation v2 wave

Decision: R94-04 matched filter ablation v2 complete; ready to open multiple-testing and stability gate upgrade.
Reason: Discovery filter ablation now has a V2 matched-filter policy with exact no-filter comparator grouping across entry, feature, horizon, regime, KNN, exit, split, and cost keys. Filter labels distinguish edge improvement, sample reduction only, instability, side-specific behavior, non-testable evidence, and harmful filters. Missing, non-finite, or not-provider-backed filter evidence fails closed as `not_testable`, and `filter_default_allowed` only unlocks for V2 `edge_improving` rows. Focused ablation tests, full research-discovery tests, contracts, compile, and diff checks passed. This wave does not add new feature math, candidate-pack writing, promotion readiness, live execution, live config changes, order placement, or sizing behavior.

## Multiple-testing and stability gate wave

Decision: R94-05 multiple-testing and stability gate complete; ready to open validation floors and blocker registry.
Reason: Discovery now has a research-only multiple-testing/stability artifact that derives declared search space from discovery manifests, resolved specs, ledgers, and trial records, ties candidate gate rows to `record_sha256` and source manifest hashes, and exposes sampled fraction, effective trial count, top-score concentration, stability-neighborhood size, split/window concentration, side concentration, and latest-window-only penalties. The discovery bridge now requires this evidence and blocks missing artifacts, source or candidate hash mismatches, isolated large-grid winners, concentration failures, low stability, and latest-window-only evidence before applying the existing historical candidate gate. Focused multiple-testing/bridge tests, full research-discovery tests, contracts, compile, and diff checks passed. This wave does not write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Validation floors and blocker registry wave

Decision: R94-06 validation floors and blocker registry complete; ready to open durable BTC/ETH public archive fixture readiness.
Reason: Discovery now has a research-only validation-floor artifact with screen-worthy and candidate-ready floor profiles, canonical blocker registry codes, maturity labels, source manifest hashes, candidate record hashes, and experiment-budget ledger metadata. The discovery bridge now requires validation-floor evidence and blocks missing artifacts, source or candidate hash mismatches, non-candidate-ready maturity, independent-event/overlap/split/side/cost/stability floor failures, latest-window diagnostic-only evidence, and missing comparator/no-regime/exit/filter/feature-ablation evidence before applying the existing historical candidate gate. Focused validation-floor/bridge tests, full research-discovery tests, contracts, compile, and diff checks passed. This wave does not write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Durable BTC/ETH public archive fixture readiness wave

Decision: R94-07 durable BTC/ETH public archive fixture readiness complete; ready to open perp context source/version audit.
Reason: Historical fixture packs now have an executable BTCUSDT/ETHUSDT public archive readiness contract that requires 15m primary bars, lower-timeframe bars, aggTrade trade-flow proxy context, public archive provenance, checksum/hash evidence, gap/duplicate evidence, explicit regime-window selection, omitted optional family reasons, and visible non-promotion limitations. Latest-window REST context and free-sample context remain valid research diagnostics but fail durable readiness. Focused fixture/data contract tests, local fixture historical-cycle tests, full contracts, full research-discovery tests, compile, and diff checks passed. This wave does not download large archives, write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Perp context source/version audit wave

Decision: R94-08 perp context source/version audit complete; ready to open AggTrade orderflow feature pack.
Reason: The branch now has versioned `features_perp_context_v3` source eligibility without changing `features_perp_context_v2`, explicit durable-provider/self-archived/latest-window/missing-unknown/candidate-ready flags, fixture-family source/version evidence, latest-window diagnostic blocking, and aggTrade proxy truthfulness in manifest risks. Focused feature tests, full contracts, full research-discovery tests, compile, and diff checks passed. This wave does not write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## AggTrade orderflow feature pack wave

Decision: R94-09 aggTrade orderflow feature pack complete; ready to open discovery compute telemetry and cached KNN sweeps.
Reason: The branch now has a dedicated `aggtrade_orderflow_v1` trade-flow proxy feature pack, checked `features_aggtrade_orderflow_v1` and `features_price_perp_aggflow_no_wt` manifests, explicit missingness/quality flags, materialized aggTrade fixture coverage, and contract tests proving top-of-book, queue imbalance, depth/L2, and true OFI stay out of the new pack. Focused feature tests, full contracts, full research-discovery tests, compile, and diff checks passed. This wave does not add provider intake, archive downloads, candidate-pack writes, promotion readiness, live execution, live config changes, order placement, or sizing behavior.

## Discovery compute telemetry and cached KNN sweeps wave

Decision: R94-10 discovery compute telemetry and cached KNN sweeps complete; ready to open exit model upgrade and remaining-edge lab.
Reason: Discovery run manifests now expose compute telemetry with wall/process timing, stage timing, memory peak, worker count, throughput, cache hit rates/counts, and artifact byte/file counts. KNN materialization now supports exact deterministic neighbor-prefix reuse across `k` and threshold variants with source/feature/split/horizon/regime/distance identity and cached-vs-uncached parity tests. Focused KNN/runner/spec tests, full contracts, full research-discovery tests, compile, and diff checks passed. This wave does not add ANN/GPU/randomized KNN, alter score/gate semantics, write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Exit model upgrade and remaining-edge lab wave

Decision: R94-11 exit model upgrade and remaining-edge lab complete; ready to open strategy family matrix using existing plugins.
Reason: Backtesting now exposes executable research exits for basis normalization, premium normalization, current GMM regime transition, KNN remaining-edge decay, and KNN dynamic barriers. Discovery exit-lab grouping now preserves side, split, regime mode, holding window, cost stress, feature setup, and KNN setup where present. True HMM transition and liquidity/depth adverse-selection exits are deferred evidence and cannot win candidate gates. Focused exit-lab/backtesting tests, full backtesting tests, full contracts, full research-discovery tests, compile, JSON parse, and diff checks passed. This wave does not write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Strategy family matrix using existing plugins wave

Decision: R94-12 strategy family matrix using existing plugins complete; ready to open BTC/ETH candidate blueprint configs.
Reason: The branch now has a research-only strategy-family matrix over existing plugins for trend, range, funding/basis, OI flow, current GMM regime, KNN local analog overlay, and diagnostic liquidation families. Every family carries no-trade and transparent comparator coverage. KNN remains an overlay/filter treatment with required non-KNN companion strategies, and the BTCUSDT cycle defers KNN strategy/exits until split-safe materialized prediction overlays exist. Current regime evidence is explicitly GMM/current-regime rather than true HMM with no-regime/GMM mode requirements, latest-month fixture evidence is diagnostic-only and candidate-pack ineligible, and liquidation remains diagnostic-only and candidate-pack ineligible. Focused strategy/research-cycle/historical tests, full contracts, full research-discovery tests, compile, JSON parse, follow-up architecture review, and diff checks passed. This wave does not write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## BTC/ETH candidate blueprint configs wave

Decision: R94-13 BTC/ETH candidate blueprint configs complete; ready to open cross-asset BTC/ETH residual research.
Reason: The branch now has research-only v3 blueprint metadata for perp basis convergence, OI flow breakout, and funding crowding fade mapped to existing executable v2 plugins. BTCUSDT has a diagnostic latest-window cycle config with no-trade/transparent comparators, no-regime requirements, non-KNN exits, required ablations, and candidate-pack blockers. ETHUSDT remains blocked until durable ETH public-archive fixture readiness exists, and the blocked config declares a required missing durable fixture manifest so it cannot silently fall back to synthetic data. KNN remains deferred until split-safe materialized prediction overlays exist. Focused strategy/research-cycle/historical tests, full contracts, full research-discovery tests, compile, JSON parse, follow-up architecture review, and diff checks passed. This wave does not write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Cross-asset BTC/ETH residual research wave

Decision: R94-14 cross-asset BTC/ETH residual research complete; ready to open operator UI truthfulness modernization.
Reason: The branch now has versioned `cross_asset_btc_eth_v2` features for BTC/ETH matched returns, rolling beta, residual return/z-score, ETHBTC trend/state, rolling correlation, funding spread, OI delta spread, and explicit cross-symbol quality flags. Tests prove future BTC/ETH rows do not alter prior features, future-aligned source timestamps block point-in-time join and candidate-ready flags, and missing funding/OI context stays unknown/`NaN` with quality flags. `eth_btc_beta_residual_v2` remains blocked until durable ETH fixture readiness, cross-symbol join proof, comparator evidence, and correlation/stability gates exist. Focused feature/historical tests, full contracts, full research-discovery tests, compile, JSON parse, and diff checks passed. This wave does not write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Operator UI truthfulness modernization wave

Decision: R94-15 operator UI truthfulness modernization complete; R94 roadmap implementation closed.
Reason: The Research tab now presents a compact operator surface with data readiness, current run, progress, latest snapshot, blockers, leads, artifact count, maturity labels, routine research actions, local history, overwrite protection, and DOM-visible missing-evidence chart reasons. Dynamic candidate-ready display requires explicit maturity evidence; Stage 13 and model-artifact language stays planning/shadow-review only. Focused operator UI tests, compile, full contracts, full research-discovery tests, docs review, UI review fixes, and diff checks passed. This wave does not add backend routes, write candidate packs, claim promotion readiness, add live execution, alter live config, place orders, or touch sizing behavior.

## Final R94 crosscheck review push wave

Decision: R94-16 final crosscheck complete; branch ready for commit and push.
Reason: Final review found and fixed material research-truthfulness and gate
logic issues before handoff: generated real-discovery templates now use
`regime_knn_entry_discovery`, non-fixed exit-lab winners require passing
cost-stress evidence, missing concentration evidence blocks multiple-testing,
blocked gate statuses override companion `complete` statuses in validation
floors, selected filter treatments must carry finite/provider-backed evidence,
and Research tab maturity/empty-state labels no longer overstate evidence.
Static boundary scans found no unsafe promotion, live-fetch, order-placement,
runtime-mode-change, true-HMM, or candidate-pack-write source/config outputs.
Compile, contracts, research-discovery, operator UI, full suite, and diff checks
passed. This wave does not write candidate packs, claim promotion readiness, add
live execution, alter live config, place orders, or touch sizing behavior.

## Performance candidate-selection engine crosscheck wave

Decision: WPR95-01 performance candidate-selection crosscheck complete.
Reason: Historical-cycle candidate selection now records exact explicit-grid
brute-force-equivalent counts, materialized sampled fractions, stability-region
selection policy, and compute policy in candidate-space, trial-budget, and cycle
manifests. Aggregate candidate backtests can run through bounded CPU threads
while preserving deterministic artifact order. Checked-in full-cycle research
configs request 15 CPU threads and prefer NVIDIA 50-series CUDA only when a
validated backend exists. At R95 closeout the missing CUDA backend was tracked
as `ISSUE-R95-001`; WPR96 later resolved that issue with diagnostic-only CUDA
evidence. This branch still does not claim live-ready candidate selection.
Compile, focused optimization/contracts/historical tests, full contracts, full
research-discovery tests, JSON parse, and diff checks passed. This wave does not
write candidate packs, claim promotion readiness, add live execution, alter live
config, place orders, or touch sizing behavior.

## GPU-accelerated stability-region candidate search wave

Decision: WPR96-01 CUDA fixed-holding parity and stability search complete.
Reason: The branch now has an optional `cuda_fixed_holding` research backend
limited to fixed-holding primary-bar screening, with lazy CuPy import, CUDA
runtime smoke checks, support/fallback reason codes, diagnostic manifests,
`speed_claimed: false`, fake-CuPy parity coverage, and local hardware parity
when available. Historical research-cycle `auto` routing uses CUDA only when GPU
is requested and the candidate is eligible; split and cost-stress validation are
forced back to CPU/reference when CUDA routing is requested. Benchmark evidence
now compares serial CPU reference, 15-thread CPU reference, CPU vector, and
optional CUDA runs. Stability-region search counters use observed backend
metadata and select only accepted regions. `ISSUE-R95-001` is resolved. Compile,
focused backtesting/optimization/contracts/historical tests, fixture-pack
validation, and benchmark validation passed. This wave does not write candidate
packs, claim promotion readiness or GPU speedup, add live execution, alter live
config, place orders, or touch sizing behavior.

## Aggressive CUDA TensorCore stability search wave

Decision: WPR97-01 aggressive CUDA/TensorCore stability search complete.
Reason: The branch now has an explicit opt-in `cuda_batched_fixed_holding`
research backend beside the R96 `cuda_fixed_holding` backend, with RawKernel
candidate indexing, FP64 accounting, deterministic non-overlap trade
construction, CPU/vector parity evidence, kernel hash, SM target, runtime
evidence, fallback reason codes, and `speed_claimed: false`. Historical-cycle
`auto` routing stays conservative unless `gpu_execution_profile` explicitly
requests `cuda_exact_batched` or `hybrid_tensorcore_screening`, and
`gpu_required` fails closed when the requested GPU profile/runtime is
unavailable. Optimization now exposes `cuda_screening_batch_v1` as a
diagnostic-only matrix screening evaluator for Tensor Core-style prefilters,
with CPU reference hashes and no candidate-gate authority. Stability-region
counters now distinguish Tensor Core screened, exact GPU screened,
CPU/reference validated, parity rechecked, and mismatch counts while retaining
brute-force-avoidance accounting. Compile, contracts, backtesting,
optimization, historical benchmark/full-cycle, research-discovery, focused
local RTX 5070 Ti CUDA parity, and diff checks passed. This wave does not write
candidate packs, claim promotion readiness or GPU speedup, add live execution,
alter live config, place orders, or touch sizing behavior.

## Default accelerated runtime polish wave

Decision: WPR97-02 default accelerated runtime polish complete.
Reason: Historical research cycles now default to accelerated `auto` routing
with `gpu_execution_profile: cuda_exact_batched`, while CPU vector/reference
remain the fallback when CUDA is unavailable, unsupported, or disabled.
Aggregate fixed-holding screening can use `cuda_batched_fixed_holding`; split
and cost-stress validation remain CPU/reference when CUDA screening was
requested. Fallback reasons and performance-plan evidence were updated to match
the new default. Local RTX 5070 Ti parity was crosschecked on five deterministic
720-row cases with exact signal/trade agreement, strict equity/metric checks,
zero max metric diff, and passed CUDA manifests. Compile, contracts,
backtesting, optimization, historical benchmark/full-cycle/local-fixture,
research-discovery, live-preflight, longer CUDA parity, and diff checks passed.
This wave does not write candidate packs, claim promotion readiness or GPU
speedup, add live execution, alter live config, place orders, or touch sizing
behavior.

## GPU telemetry smoke fix wave

Decision: WPR97-03 GPU telemetry smoke fix complete.
Reason: Post-push GPU verification found that exact CUDA aggregate manifests
recorded passing parity, but cycle-level stability counters still reported
`parity_rechecked_count: 0`. The backtest index now carries CUDA exact parity
status plus max metric/equity/trade diffs, and research-cycle stability
counters count aggregate CUDA parity rechecks and mismatches from that evidence.
The mini default GPU full-cycle smoke on RTX 5070 Ti used
`cuda_batched_fixed_holding` for aggregate screening, CPU/reference for
validation, `parity_rechecked_count: 4`, and `mismatch_count: 0`. Local
performance timing did not support a speedup claim for single-candidate
artifact-producing backtests, so `speed_claimed: false` remains correct.
Compile, focused contracts, synthetic full-cycle, benchmark/local-fixture
historical tests, CUDA/GPU tests, research-discovery, and diff checks passed.
This wave does not write candidate packs, claim promotion readiness or GPU
speedup, add live execution, alter live config, place orders, or touch sizing
behavior.

## Throughput default and TensorCore dependency wave

Decision: WPR97-04 throughput default and TensorCore dependency complete.
Reason: Local RTX 5070 Ti benchmarks showed the parity-correct
`cuda_batched_fixed_holding` path is slower than CPU vector execution for the
current one-candidate, artifact-producing fixed-holding workload. Historical
research cycles now default to conservative `auto` routing: aggregate
fixed-holding screening uses `vector_fixed_holding` when supported, while
validation paths still fall through to the reference engine under
`auto_validation_reference_required`. Explicit `cuda_exact_batched`,
`hybrid_tensorcore_screening`, and `cuda_batched_fixed_holding` requests remain
available for GPU evidence. The optional `research-gpu` dependency set now
includes `nvidia-cublas-cu12>=12.8` after local Tensor Core-shaped CuPy matmul
failed without discoverable cuBLASLt DLLs. Longer local benchmarks, Tensor
Core-shaped matrix timing, Tensor Core screening smoke, compile, contracts,
historical full-cycle/local-fixture tests, CUDA/GPU focused tests, and diff
checks passed. This wave does not write candidate packs, claim promotion
readiness or GPU speedup, add live execution, alter live config, place orders,
or touch sizing behavior.

## Fastest exact default polish wave

Decision: WPR97-05 fastest exact default polish complete.
Reason: The default historical research-cycle compute policy now explicitly
selects the fastest parity-safe route measured for the current engine:
`gpu_execution_profile: fastest_exact`, `cpu_threads: 15`, aggregate
`vector_fixed_holding` where supported, and reference validation under
`auto_validation_reference_required`. Explicit `cuda_exact_batched`,
`hybrid_tensorcore_screening`, and CUDA backtest requests remain opt-in
diagnostic evidence paths. Performance-plan evidence now distinguishes
fastest-exact vector selection from a failed CUDA probe through
`gpu_execution_profile_fastest_exact_vector_selected` and
`cuda_runtime_checked: false`. Focused compile, contract, synthetic full-cycle,
and default full-cycle smoke checks passed. This wave does not write candidate
packs, claim promotion readiness or GPU speedup, add live execution, alter live
config, place orders, or touch sizing behavior.

## Research UI fastest compute summary wave

Decision: WPR97-06 research UI fastest compute summary complete.
Reason: Operator Research artifact summaries now surface the historical-cycle
compute profile, CPU threads, aggregate workers, backend used counts, GPU
execution status, selected CUDA backend, CUDA runtime checked flag, R97 batched
CUDA request flag, and Tensor Core screening request flag. The Research artifact
card displays compute profile, workers, backend mix, GPU status, and CUDA
selection without requiring operators to open raw manifest JSON. Focused
operator API/page tests and compile passed. This wave is read-only UI wiring and
does not change research execution, write candidate packs, claim promotion
readiness or GPU speedup, add live execution, alter live config, place orders,
or touch sizing behavior.

## Fastest worker scaling default wave

Decision: WPR97-07 fastest worker scaling default complete.
Reason: Local full-cycle worker scaling tests assigned 15, 24, 32, 48, and 64
aggregate workers correctly with no run errors. The 48-worker setting had the
best median runtime on the 720-row synthetic full-cycle test, while 64 workers
was slower despite assigning correctly. The default `fastest_exact`
`cpu_threads` value is now 48, and benchmark comparison labels/evidence use
CPU48 naming. Focused compile, contracts, synthetic full-cycle, benchmark, and
operator artifact tests passed. This wave does not change backtest math,
strategy signals, candidate gates, live execution, live config, order placement,
promotion readiness, or sizing behavior.

## Research boundary validation hardening wave

Decision: WPR98-01 research boundary validation hardening complete.
Reason: Legacy research dataset/model/evaluation artifacts now carry
fail-closed boundary metadata and replay evaluation can no longer mark local
research metrics promotion-ready. Discovery validation floors now require an
explicit passed exit-lab gate for candidate-ready evidence, preserve separate
exit-lab status fields, and the candidate-pack bridge verifies blocker-registry
hash and payload integrity before accepting validation-floor evidence. The
active CLI now has a canonical `tradingbotsuite` console script while retaining
legacy `tradingbot` compatibility. Focused research, validation-floor, bridge,
live CLI, contracts, research-discovery, live, compile, full-suite, and diff
checks passed. This wave does not change live execution, live config, order
placement, runtime mode, candidate-pack writing, promotion authorization, or
sizing behavior.

## Branch technology development reference wave

Decision: WPR99-01 branch technology development reference complete.
Reason: The branch now has a single durable reference document covering the
technology stack, package architecture, implemented research subsystems,
development logic, historical stage summary, command surface, validation
strategy, live/promotion boundaries, high-risk rewrite areas, and deferred
work. This was a documentation-only wave. Diff checks, compile, and contract
tests passed. This wave does not change source behavior, generated artifacts,
live execution, live config, order placement, runtime mode, candidate-pack
writing, promotion authorization, or sizing behavior.

## Provider capability registry wave

Decision: WPR100-01 provider capability registry complete.
Reason: The external deep-research report's safest useful recommendation was
implemented as a contract-layer provider capability registry for existing data
surfaces, with durability class, retention limit, history-start, exchange-native
status, normalization status, health policy, diagnostic default, and candidate
readiness default metadata. Data manifests and generated fixture-pack
source/context entries now carry this metadata, and supplied mismatches fail
contract validation. Focused data/fixture contracts, compile, full contracts,
and diff checks passed. This wave does not add providers, download data,
generate fixtures, run candidate batches, write candidate packs, claim data or
live readiness, alter live execution, live config, order placement, runtime
mode, promotion authorization, or sizing behavior.

## Branch completion review and orchestrator plan wave

Decision: WPR101-01 branch completion review and orchestrator plan complete.
Reason: A broad post-R100 review found that the branch has strong
research-only/live-boundary guardrails and passing contract/high-risk validation,
but is not empirically complete. The review registered six follow-up issues:
source provider-capability validation, direct CLI output-root allowlisting,
durable multi-window candidate-ready evidence, import-boundary test coverage,
capability-aware gate integration, and package naming cleanup. The ledger now
sets the completion sequence: R102 contract/boundary closure, R103 durable
BTC/ETH data, R104 candidate validation on durable evidence, R105 empirical
falsification, R106 packaging/maintainability, and R107 promotion handoff
planning only if durable research-only candidate packs exist. Compile,
contracts, research-discovery, live, historical, backtesting, optimization,
research-artifact, and feature validation passed. This wave does not change
source behavior, generated artifacts, live execution, live config, order
placement, runtime mode, candidate-pack writing, promotion authorization, or
sizing behavior.

## Branch completion implementation wave

Decision: WPR102-01 branch completion implementation complete.
Reason: The R101 contract and boundary findings were closed without weakening
the research-only boundary. Fixture manifests now revalidate top-level source
provider capability metadata, direct research CLI output directories use the
research output-root allowlist resolver, import-boundary tests cover
`research_cycle`, `optimization`, and `research_artifacts`, and provider
capability plus durable public archive readiness feed research-cycle,
discovery, bridge, and candidate-pack gate evidence. The project distribution
name is now `tradingbotsuite` while legacy compatibility remains. Durable
BTC/ETH multi-window archive data was not fabricated; `ISSUE-R101-003` remains
the sole open P1 and is the entry blocker for R103. Compile, focused contract
and gate suites, CLI boundary suites, high-risk historical/discovery/artifact/
live suites, full contracts, full `tests/tradingbotsuite`, backtesting/
optimization/features, and full-suite validation passed. This wave does not
write candidate packs from weak data, claim promotion readiness, add live
execution, alter live config, change runtime mode, place orders, or touch
sizing behavior.

## Durable public archive fixture data foundation wave

Decision: WPR103-01 durable public archive fixtures complete.
Reason: The branch now has compact checked-in BTCUSDT and ETHUSDT public
archive multi-window fixture packs under
`data/research/fixtures/*_public_archive_multi_window_v1`. The fixtures were
generated from checksum-verified Binance Vision USD-M daily archives for 15m
klines, 1m lower-timeframe klines, and aggTrades across trend, drawdown, range,
and high-volatility windows. Raw aggTrade rows were compacted to a 1-minute
trade-flow proxy while preserving selected raw row counts, source archive URLs,
archive hashes, checksum evidence, provider capability metadata, and
window-selection metadata. Both manifests pass historical fixture validation
and durable public archive readiness validation. `ISSUE-R101-003` is resolved
as a data-foundation blocker, but candidate validation remains R104 work and no
candidate-ready performance claim is made. Focused fixture contract validation,
compile, full-suite validation, and diff checks passed. This wave does not
write candidate packs, claim promotion readiness, add live execution, alter
live config, change runtime mode, place orders, or touch sizing behavior.
