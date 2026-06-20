# Sandbox Research Contract

Status: active for WPR106-228 and later sandbox packets.

## Purpose

The Rapid Strategy Iteration Sandbox is a research-only idea triage layer. It
exists to test many weak or early hypotheses quickly before expensive strict
historical-cycle validation. Sandbox output may explain why a hypothesis is
worth later validation, but it is not candidate evidence.

## Required Boundary Fields

Every sandbox spec, venue descriptor, result row, run manifest, and evidence
request must carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

Sandbox artifacts must not contain live signals, paper signals, sizing
instructions, order-placement instructions, runtime-mode changes, or promotion
authorization.

Run and suite manifests may record integrity metadata for child Parquet/JSON
artifacts, such as SHA-256 digests and byte sizes. Manifest-integrity metadata
must not become candidate evidence and must avoid self-referential hashes of
the manifest file itself. Integrity verification reports may compare those
manifest-recorded values with the current child files, but those reports are
sandbox diagnostics only.

## Date Rule

Sandbox data windows must start on or after `2024-01-01`. Inputs may contain
older rows, but sandbox execution must filter them out before any metric,
ranking, request, or artifact is written.

## Intake Rule

Strategy catalog and spreadsheet-like inputs are descriptors only. Sandbox
intake may parse rows such as hypothesis ID, family, signal column, side,
filter bounds, tags, and JSON parameters. It must not import or execute
external strategy code.

Direct strategy catalog intake may normalize common human spreadsheet header
aliases before lead/proxy fallback. Accepted aliases may cover hypothesis ID,
family, signal column, side, source ID, exit profile, filter column/ranges,
params, tags, and notes. Alias normalization must only decide descriptor field
names for already-local catalog rows; it must not create new strategy logic,
candidate evidence, live signals, or promotion evidence.

If a catalog does not provide a precomputed `signal_column`, sandbox intake may
compile repo strategy JSON configs or spreadsheet-like lead rows into static
built-in blueprint proxies. Those proxies must declare their blueprint ID,
source metadata, deterministic generated signal column, and diagnostic-only
status. Blueprint materialization must use only completed market rows inside
the already-filtered 2024+ sandbox window; pre-2024 rows must not influence
rolling features, signals, metrics, rankings, or evidence requests.

Blueprints are not production strategy plugins. They are bounded sandbox
proxies for fast falsification and may only produce non-promotable sandbox
results or evidence-request descriptors.

Sandbox strategy catalog materializers may compile local strategy catalogs,
spreadsheet-like lead rows, and repo strategy configs into normalized
strategy-catalog artifacts for later sandbox sweeps. Materializers must reuse
the sandbox strategy catalog loader/compiler and keep every materialized row as
a descriptor. They must report skipped files or load errors explicitly instead
of silently dropping them. Materializers must honor configured source-count
limits through deterministic bounded traversal; they must not recursively sort
an entire catalog tree before applying `max_files`.

Workbook strategy catalogs may include multiple usable sheets. Sandbox intake
may aggregate every sheet that is either a direct strategy catalog or a
spreadsheet-like lead table, while skipping notes-only or unsupported sheets.
Sheet names, row counts, sheet kinds, included/skipped counts, and skipped
sheet reasons are descriptor navigation metadata for agent preflight only; they
must not become candidate evidence, live signals, paper signals, sizing
instructions, order instructions, or promotion evidence.
Legacy `.xls` workbooks are not a supported sandbox catalog format unless a
later packet adds an explicit dependency and tests; direct loaders and
materializers must surface `.xls` as a fail-closed repair reason. The
standard-library `.xlsx` fallback must bound workbook ZIP member count,
per-member XML bytes, total parsed XML bytes, sheet count, shared-string count,
row count, cell count, and column count. Bound failures must be reported as
explicit loader errors, not as successful partial strategy catalogs.
Direct workbook strategy rows that omit an explicit source ID may use
`workbook_path#sheet_name` as their descriptor `source_id`, matching the
spreadsheet-like lead provenance convention. Explicit source IDs supplied by a
catalog row remain authoritative.

One-command sandbox iteration manifests, agent briefs, and iteration indexes
may carry compact strategy-source summaries derived from materialized catalog
build reports. Those summaries may include source status/suffix counts,
skipped-source reason counts, bounded skipped-source samples,
family/side/blueprint counts, and bounded workbook sheet diagnostics. They are
agent navigation metadata only and must not alter materialized strategy rows,
preflight trial estimates, sweep metrics, rankings, evidence-request selection,
strict validation behavior, or promotion state.

One-command sandbox iteration manifests, agent briefs, and iteration indexes
may also carry compact archive-source summaries derived from archive manifest
build reports. Those summaries may include archive file status/suffix counts,
skipped-file reason counts, bounded skipped-file samples with source integrity
and requested-window metadata, and truncation flags. They are agent navigation
metadata only and must not alter venue archive descriptors, archive coverage
semantics, preflight trial estimates, sweep metrics, rankings,
evidence-request selection, strict validation behavior, or promotion state.
One-command sandbox iteration manifests, agent briefs, and iteration indexes
may also carry compact venue-expansion archive coverage diagnostics derived
from coverage matrix sidecars. Those diagnostics may include target venues,
ready/missing/blocked/mixed counts, descriptor-only target actions, a sidecar
Parquet path, and bounded actionable samples. They are agent navigation
metadata only and must not add descriptors, mutate archive manifests, download
venue data, alter requested-window readiness, change sweep behavior, or change
promotion state.

Sandbox venue-expansion request bundles may be consumed by a local materializer
that scans only explicitly supplied local archive roots. The materializer may
emit descriptor candidates and manifest-patch dry-run rows, but it must not
download provider data, mutate source archive files, write or modify archive
manifests, run sandbox sweeps, run strict validation, write candidate packs,
create paper/live signals, define sizing, place orders, change runtime mode,
write live configuration, or claim promotion readiness. Missing local coverage
must remain a blocker row rather than fabricated evidence.

Venue-expansion descriptor candidates may be exported into a new standalone
sandbox `venue_archives.json` manifest under a requested output directory by an
explicit candidate-manifest export command. This command may only copy
validated descriptor payloads into a new sandbox manifest and write a report;
it must not mutate existing archive manifests, mutate source archive files,
download provider data, run sandbox sweeps, run strict validation, write
candidate packs, create paper/live signals, define sizing, place orders,
change runtime mode, write live configuration, or claim promotion readiness.

Materialized strategy catalogs are still sandbox descriptors. They must not
execute strategy sweeps, execute strict validation, write candidate packs,
create paper/live signals, define sizing, place orders, change runtime mode,
write live configuration, or claim promotion readiness. Catalog manifests,
rows, and build reports must keep all required sandbox boundary flags.

Venue archive descriptors may refer to Binance, OKX, Bybit, Hyperliquid, or a
local manifest. These descriptors default to diagnostic research evidence and
must not imply candidate-ready venue execution proof.

Venue archive descriptor intake may canonicalize common local/export venue
aliases before validation. Accepted aliases may include Binance USD-M futures
labels, legacy OKEx/OKX labels, Bybit linear/USDT labels, and Hyperliquid
perpetual shorthand. Alias canonicalization only normalizes descriptor
identity; it must not imply provider access, live venue execution proof,
candidate evidence, paper/live signals, or promotion evidence.

Descriptors may include `data_path` for local normalized market data or a local
archive file. The sandbox loader may read local CSV, TSV, JSON, JSONL, NDJSON,
Parquet, gzip-compressed CSV/TSV/JSON/JSONL/NDJSON, or ZIP files containing
CSV/TSV/JSON/JSONL/NDJSON market-data members, including gzip-compressed
members with compound suffixes such as `.csv.gz` or `.jsonl.gz`, or TAR/TGZ
files containing the same member types. ZIP readers should preserve headered
venue-export CSV columns when available, prefer CSV members when a ZIP contains
multiple loadable member types, and still support headerless Binance Vision
kline ZIP members. TAR/TGZ readers may use the same
CSV/TSV/JSON/JSONL/NDJSON member priority order across plain and gzip-compressed
members. When a container has multiple members of the selected highest-priority
loadable type, readers may concatenate all selected members in deterministic
member-name order before 2024+ normalization. Readers must not mix
lower-priority member types into the same loaded frame and must read members in
memory without extracting them to disk. Container readers should expose bounded
member-selection metadata in normalization metadata, including container kind,
selected member suffix, selected member count, selected member-name sample,
available member suffix counts, and loadable member count.
Container readers must also enforce bounded selected-member counts, bounded
raw member bytes, bounded total selected raw bytes, and bounded gzip
decompression. Oversized containers must fail closed with explicit loader
errors that downstream archive audits, preflights, materializers, or sweeps can
surface as blockers; readers must not silently truncate input or fabricate
partial evidence. Accepted container metadata should record the active loader
limits as reproducibility diagnostics.
The loader may normalize common local venue export aliases into canonical
`timestamp`, `open`, `high`, `low`, `close`, and `volume` columns for OKX,
Bybit, Hyperliquid, Binance, and local manifest workflows. Alias normalization
may include mark-price, index-price, and mid-price aliases such as `markPx`,
`idxPx`, and `midPx`. When no explicit close-like price alias exists, loaders
may derive `close` from bid/ask price columns by midpoint and must report that
derivation in normalization metadata.
Local Hyperliquid-style nested `l2Book` JSON payloads with `levels` arrays may
be flattened into best bid/ask price and size columns before the same midpoint
derivation path is applied. Loader source-transformation metadata must report
that flattening when it occurs, and archive manifest builders may use flattened
book columns or `l2Book` content hints to infer `l2_book` data family. Alias,
derivation, and source-transformation metadata must be reported in archive
build or audit metadata when available. Nested book snapshots are diagnostic
archive inputs only; they are not strict L2 fill evidence or venue execution
proof. Network downloads and venue account access are outside the sandbox
loader contract.
Numeric timestamp aliases must be interpreted deterministically as epoch
seconds, milliseconds, microseconds, or nanoseconds by magnitude before the
2024+ sandbox date filter is applied. Compact `YYYYMMDD` timestamp values must
remain calendar dates, not Unix epoch values.

When multiple venue descriptors are supplied, sandbox execution must route
each descriptor to its own `data_path` unless the caller explicitly supplies a
shared market-data path for a smoke run. Descriptor-local relative `data_path`
values resolve relative to the descriptor manifest file. Missing descriptor
data paths must fail closed when no shared market-data path is supplied.
Descriptor-routed batch loaders may cache loaded and normalized market frames
for descriptors with identical resolved `data_path` values inside one batch.
They must verify each descriptor's `source_integrity` metadata before a cached
frame is returned for that descriptor, must still filter pre-2024 rows, and
must not collapse descriptors with different resolved source paths.

Descriptor-routed results and manifests must record market-source metadata so
later agents can distinguish OKX, Bybit, Hyperliquid, Binance, and local
manifest inputs without treating sandbox rows as strict venue execution
evidence.

## Execution Rule

Fast sweeps may use simplified vectorized fixed-hold execution for first-pass
falsification. They must avoid same-bar entry/exit optimism, record cost
assumptions, and write rejection or blocker reasons instead of candidate claims.
Sweep implementations may cache prepared signal/filter masks, market numeric
arrays such as close, optional high/low, and entry-date arrays, and trial
metrics for venue descriptors that explicitly share the same prepared market
frame. Caches must be built only from completed rows inside the already-filtered
2024+ window and must not change trial identity, metrics, rankings, or blocker
semantics. Descriptor-routed venue archive sweeps may reuse trial metric work
across descriptors that share the same explicit market source, such as a shared
market-data path, identical descriptor `data_path`, or the same in-memory
market frame object. Descriptor-routed frames with different source paths or
different frame objects must remain distinct and must not be collapsed across
venues.

Primary-bar target/stop exit implementations may vectorize barrier windows for
throughput, provided they preserve first-hit timing, no-hit fixed-hold fallback,
and conservative target/stop stop-first handling when target and stop touch on
the same bar.

Sandbox runs may also declare bounded exit and filter variants. Exit variants
are limited to fixed hold, target-only, stop-only, and conservative target/stop
primary-bar proxies. Target/stop variants require `high` and `low` columns and
must block clearly when those columns are missing. Conservative target/stop
variants must treat same-bar target/stop ambiguity as stop-first. Filter
variants may only apply threshold checks to completed rows in the already
filtered 2024+ sandbox window.

Exit and filter variant payloads are part of trial identity. Two rows with the
same strategy, venue, and holding period but different exit/filter assumptions
must have different deterministic trial IDs.

Direct catalog rows with a non-default `exit_profile` must not be silently
swept through unrelated run-spec exits. A non-default row-level exit profile
may run only against matching run-spec exit variants; if no matching variant is
declared, preflight and execution must fail closed with an explicit blocker.
Rows using the default `fixed_hold` profile remain compatible with normal
run-spec exit sweeps unless a later packet adds an explicit row-level
restriction field.

## Handoff Rule

The only downstream handoff allowed from sandbox to the strict evidence layer
is an evidence-request descriptor. That descriptor requests later validation
under existing historical-cycle, ablation, multiple-testing, validation-floor,
and candidate-gate rules. It must not write candidate packs or mark any row
promotion-ready.

Evidence-request descriptors should carry compact `source_trial_context`
metadata for agent workflow speed. That context may include the source trial
ID, source run ID, hypothesis/family/source ID, venue, symbol, data family,
signal column, side, holding period, exit/filter variant IDs, normalized
market timestamp bounds, descriptor routing metadata such as venue descriptor
ID and local data path, bounded source container diagnostics such as ZIP/TAR
selected member suffix and member counts, and sandbox execution assumptions.
The context is a descriptor for later investigation only; it is not strict
validation evidence, not a candidate identity, and not an instruction to trade.

## Analysis Rule

Sandbox analysis tools may read `manifest.json`, compact Parquet summaries,
rankings, and evidence-request descriptors to produce agent-facing summaries.
Analysis reports must keep the same sandbox boundary flags and must validate
that source rankings remain non-promotable before summarizing them. Direct
analysis readers must verify manifest-recorded child artifact integrity before
opening rankings or evidence-request files, and must fail closed on missing
metadata, missing files, or hash/size drift.

Analysis reports may rank, group, count, and explain sandbox rows, but they are
still sandbox artifacts. They must not become candidate evidence, candidate
packs, paper/live signals, sizing instructions, order instructions, runtime
changes, live configuration writes, or promotion claims.
Run analysis summaries may include bounded bucket rollups for venue, family,
exit, filter, and venue/family clusters derived only from already-validated
ranking rows and descriptor-only evidence-request source trial IDs. These
rollups may expose bucket counts, status counts, positive-net counts,
evidence-request counts, and best representative trial metadata for agent
triage, but must not change scoring, ranking, falsification decisions,
evidence-request selection, trial IDs, archive routing, validation readiness,
or promotion state.
Artifact catalogs may flatten those already-written run analysis bucket rollups
into a compact Parquet sidecar for cross-run agent queries. The sidecar may
include source analysis paths, source run IDs, bucket identity, compact counts,
best representative trial fields, and non-authorizing flags, but it must not
open ranking Parquet files, recompute metrics, execute validation, write
candidate packs, mutate source artifacts, or change evidence-request selection,
trial IDs, scoring, archive routing, or promotion state.

Hypothesis falsification reports are analysis reports. They may group sandbox
rankings across strategy/venue/exit/filter rows, label hypotheses as blocked,
falsified, mixed, screened-positive, or strict-validation-requested, and write
compact JSON/Parquet indexes. Those labels are sandbox triage labels only; a
strict-validation-requested hypothesis is not candidate evidence and is not
promotion-ready. Run and suite falsification readers must verify the relevant
run or suite child artifact integrity before reading source artifacts.

## Suite Rule

Sandbox suites may batch several sandbox run specs, strategy catalogs, venue
archive manifests, and optional shared local market-data paths for agent
workflow speed. Suite case paths resolve relative to the suite spec file unless
they are absolute.

Suite artifacts may include a manifest, JSON/Parquet case index, and aggregated
evidence-request descriptor files. Every suite spec, suite case, suite
manifest, suite index row, and aggregated evidence-request descriptor must keep
the required sandbox boundary flags.

Suite indexes may summarize and compare sandbox runs, but they remain
sandbox-only triage output. Aggregated evidence-request descriptors may only
request later strict validation under the existing historical-cycle gates; a
suite must not execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, change runtime mode, write
live configuration, or claim promotion readiness.

Suites must run compatibility preflight for each case before archive sweep
execution. If a case has zero runnable trials, the suite may write a blocked
case-index row and skip the sweep and evidence-request aggregation for that
case. Blocked suite cases must still keep preflight artifact paths and blocker
counts so agents can repair inputs without treating the missing run as a suite
corruption.

Suites may run independent cases concurrently when the caller explicitly sets a
positive worker count greater than one. Parallel execution must keep each
case's preflight and run artifacts isolated, must preserve final suite index
and evidence-request ordering by suite spec order, and must not collapse
descriptor-routed venue data across cases.
Sequential suite execution may pass one process-local market-data cache across
case preflight and archive sweep steps so repeated resolved local market
sources are not read and normalized again for each case. Parallel suite
execution must keep caches case-local. Suite manifests may record cache scope
metadata, but cached frames and integrity state must stay in memory only and
must not change trial IDs, rankings, market-source metadata, blocker semantics,
or boundary flags.
Sequential suite execution may also cache parsed suite inputs by resolved
local path, including sandbox run specs, strategy catalogs, and venue archive
descriptor manifests. This cache is only a descriptor-parsing speedup for
already-local inputs. Parallel suite execution must keep parsed-input caches
case-local, and suite artifacts may record only input-cache scope metadata, not
cache contents.

## Strict-Validation Request Bundle Rule

Sandbox validation-request bundles may collect, dedupe, and prioritize
evidence-request descriptors from a run or suite. They may name the existing
strict validation entrypoint, such as `run-historical-research-cycle`, and list
required evidence classes for later work.

Bundles are descriptor-only handoffs. They must not write historical-cycle
specs, execute historical-cycle validation, write candidate packs, create
paper/live signals, define sizing, place orders, change runtime mode, write
live configuration, or claim promotion readiness. Bundle manifests and rows
must keep all required sandbox boundary flags. Bundle exporters must verify
run or suite child artifact integrity before reading evidence-request
descriptors.

Bundle descriptor rows should preserve each request's `source_trial_context`
and may expose stable convenience fields such as source venue descriptor ID,
source market start/end, source market routing metadata, and bounded source
container diagnostics such as source container kind, selected member suffix,
selected member count, selected member-name sample, available suffix counts,
and loadable member count. These fields exist to let agents triage
strict-validation requests quickly from JSON/Parquet handoff files without
reopening ranking Parquets.

`preflight-rapid-strategy-sandbox-validation-requests` may import these
descriptor-only bundles and write a strict-validation descriptor preflight
report. Accepted rows mean only `accepted_for_strict_validation_planning`;
blocked rows must keep concrete blocker reasons such as missing source
context, missing archive identity, proxy-only strategy, missing required
validation requirements, pre-2024 windows, or candidate-pack/promotion flags.
The preflight must not execute strict validation, write historical-cycle specs,
write candidate packs, create paper/live signals, define sizing, place orders,
change runtime mode, write live configuration, or claim promotion readiness.
All preflight reports and rows must keep sandbox boundary flags and
non-authorizing status fields.

## Venue-Expansion Request Bundle Rule

Sandbox venue-expansion request bundles may collect and dedupe catalog-level
venue-expansion worklist rows into descriptor-only OKX, Bybit, and Hyperliquid
archive-intake request descriptors. They may expose target venue, compact
market-symbol key, data family, interval, target status/action, source iteration
IDs, source queues, path references, compact coverage counts, bounded source
references, and blocker reason counts derived only from the already-written
sandbox artifact catalog JSON or its venue-expansion worklist sidecar.

Venue-expansion request bundles are non-executing handoffs. They must not
download provider data, create or mutate archive manifests, mutate archive
source files, execute replay commands, execute or authorize strict validation,
write candidate packs, create paper/live signals, define sizing, place orders,
change runtime mode, write live configuration, change archive routing, change
preflight behavior, change scoring or ranking, change evidence-request
selection, change trial IDs, or claim promotion readiness. Bundle manifests and
descriptor rows must keep all required sandbox boundary flags, set explicit
provider-download, archive-manifest-write, source-archive-mutation, replay,
strict-validation, and candidate-pack authorization flags to false, and refuse
pre-2024 requested or observed market windows.

## Artifact Catalog Rule

Sandbox artifact catalogs may scan known sandbox JSON artifact names under the
configured research output root and write compact JSON/Parquet indexes for
agent navigation. Catalogs must validate sandbox boundary flags before indexing
artifact objects and must keep all required sandbox boundary flags on catalog
manifests and rows.
Catalog sidecar-index rows may include deterministic agent navigation metadata
such as read order, read group, first-read flags, and short navigation hints.
These fields are read-only triage metadata for agent workflow speed. They must
not change sidecar row counts, sidecar payload schemas outside the sidecar
index, artifact discovery, scoring, ranking, falsification decisions,
evidence-request selection, trial IDs, archive routing, strict validation
behavior, replay readiness, source-integrity behavior, candidate-pack state, or
promotion state.

Catalog rows for run and suite manifests may include read-only integrity
verification summaries derived from manifest-recorded child artifact hashes.
Those summaries must not write verifier reports during catalog indexing, must
not modify source artifacts, and must report failed integrity as catalog
metadata rather than candidate evidence.
Catalog rows for sandbox global leaderboards may include read-only bucket
leaderboard metadata already present in the loaded global leaderboard JSON,
including bucket counts, bounded top-bucket counts/types, bucket decision-count
maps, and the companion bucket Parquet path. Catalog writers must not open the
bucket leaderboard Parquet, recompute bucket rows, execute validation, mutate
source artifacts, change scoring or ranking, change evidence-request selection,
change trial IDs, change archive routing, or change promotion state while
surfacing this metadata.
Catalog rows for sandbox global leaderboards may also include read-only global
evidence-request metadata derived only from bounded `top_hypotheses` already
present in the loaded global leaderboard JSON, including request counts, unique
request trial counts, requesting-hypothesis counts, requested-validation count
maps, leaderboard-decision count maps, family count maps, and tested
venue/symbol count maps. Catalog manifests may include a companion top-level
global evidence-request summary derived only from in-memory evidence-request
rows, bucket queues, and representative rows produced during the same catalog
write. These metadata fields may include bounded source-context availability,
source venue, source symbol, source data family, source interval, routing-mode,
source venue descriptor, and source data-path counts derived only from already
loaded global leaderboard preview rows. They must retain sandbox boundary flags
where they are standalone nested objects and must not open the full global
leaderboard Parquet or per-run evidence request files, recompute leaderboard
rows, execute or authorize validation, mutate source artifacts, change scoring
or ranking, change evidence-request selection, change trial IDs, change archive
routing, or change promotion state.
Catalog writers may also flatten those source-context count maps into a compact
Parquet sidecar for cross-catalog agent queries. The sidecar may expose the
source-context field, source-context value, count, unique request-trial count,
source leaderboard count, source market start/end min/max bounds, bounded
representative evidence-request/source IDs, source request IDs, source artifact
paths, best leaderboard/source metric context, compact summary totals, and
non-authorizing flags. It must retain sandbox boundary flags and write an
empty-schema Parquet file when no source-context summary rows exist. It must
not open the full global leaderboard Parquet or per-run evidence request files,
recompute leaderboard rows, execute or authorize validation, mutate source
artifacts, change scoring or ranking, change evidence-request selection, change
trial IDs, change archive routing, or change promotion state.
Catalog writers may also derive a bounded source-priority queue from those
source-summary rows. The queue may sort across source-context fields by best
leaderboard/source metric context and compact counts, expose the source-summary
row rank plus the same descriptor-only source coverage and representative
metadata, and write a compact Parquet sidecar. It must retain sandbox boundary
flags and write an empty-schema Parquet file when no source-summary rows exist.
It must not open the full global leaderboard Parquet or per-run evidence
request files, recompute leaderboard rows, execute or authorize validation,
mutate source artifacts, change scoring or ranking, change evidence-request
selection, change trial IDs, change archive routing, or change promotion state.
Catalog writers may also flatten the bounded `top_buckets` rows already present
in loaded global leaderboard JSON payloads into a compact Parquet sidecar for
cross-leaderboard agent queries. The sidecar may expose source leaderboard
paths, companion bucket Parquet paths, bucket identity, compact counts,
decision labels, best representative trial metadata, and non-authorizing flags.
It must retain sandbox boundary flags and write an empty-schema Parquet file
when no top-bucket rows exist. It must not open the full bucket leaderboard
Parquet, recompute bucket rows, execute validation, mutate source artifacts,
change scoring or ranking, change evidence-request selection, change trial IDs,
change archive routing, or change promotion state.
Catalog writers may also flatten the bounded `top_hypotheses` rows already
present in loaded global leaderboard JSON payloads into a compact Parquet
sidecar for cross-leaderboard agent queries. The sidecar may expose source
leaderboard paths, hypothesis/family identity, tested dimensions, compact
counts, decision labels, best representative trial metadata, evidence-request
trial IDs, bounded descriptor-derived evidence-request source-context previews,
reason counts, and non-authorizing flags. It must retain sandbox boundary flags
and write an empty-schema Parquet file when no top-hypothesis rows exist. It
must not open the full global leaderboard Parquet, recompute leaderboard rows,
execute validation, mutate source artifacts, change scoring or ranking, change
evidence-request selection, change trial IDs, change archive routing, or change
promotion state.
Catalog writers may also flatten bounded
`top_hypotheses[*].evidence_request_trial_ids` from loaded global leaderboard
JSON payloads into a compact descriptor-only Parquet sidecar. The sidecar may
expose source leaderboard paths, evidence request trial/source IDs, requested
validation labels, hypothesis/family context, tested dimensions, compact counts,
decision labels, reason counts, bounded source-request IDs, source run paths,
source market windows, source routing/data-path/container fields, compact source
metric fields, and non-authorizing flags when those fields are already present
in the bounded global leaderboard preview. It must retain sandbox boundary flags
and write an empty-schema Parquet file when no global evidence-request rows
exist. It must not open the full global leaderboard Parquet or per-run evidence
request files, recompute leaderboard rows, execute or authorize validation,
mutate source artifacts, change scoring or ranking, change evidence-request
selection, change trial IDs, change archive routing, or change promotion state.
Catalog writers may also derive a bounded descriptor-only global
evidence-request priority queue from in-memory global evidence-request sidecar
rows produced during the same catalog write. Priority queues may sort
descriptor-only global request rows by leaderboard rank, score, source artifact,
and stable evidence-request identity, expose read-only request/source,
hypothesis/family, tested venue/symbol, compact metric, decision, reason-count,
source leaderboard path, and bounded source-context metadata copied from the
in-memory global evidence-request rows, and write a compact Parquet sidecar with
empty-schema behavior when no global evidence-request rows exist. Priority
queues and sidecars must retain sandbox boundary flags and non-authorizing
flags, and must not open the full global leaderboard Parquet or per-run evidence
request files, recompute leaderboard rows, execute or authorize validation,
mutate source artifacts, change scoring or ranking, change evidence-request
selection, change trial IDs, change archive routing, or change promotion state.
Catalog writers may also derive a bounded descriptor-only bucket queue from
global leaderboard evidence-request sidecar rows. The queue may group by
requested validation, hypothesis, family, tested venue, tested symbol, tested
venue/symbol, tested venue/family, leaderboard decision, and, when row source
context is available, source venue, source symbol, source venue/symbol, source
data family, source interval, source venue descriptor, source routing mode, and
source data path. The queue may expose compact counts, bucket source-context
fields, and representative evidence-request trial IDs for agent routing. It
must retain sandbox boundary flags and write an empty-schema Parquet file when
no global evidence-request buckets exist. It must not open the full global
leaderboard Parquet or per-run evidence request files, recompute leaderboard
rows, execute or authorize validation, mutate source artifacts, change scoring
or ranking, change evidence-request selection, change trial IDs, change archive
routing, or change promotion state.
Catalog writers may also derive descriptor-only representative rows from global
evidence-request bucket queues and in-memory global evidence-request sidecar
rows. The representative sidecar may expose bucket identity, bucket queue rank,
representative rank, evidence request trial/source IDs, hypothesis/family
context, tested dimensions, source leaderboard paths, bucket source-context
fields, row source-context fields, source request IDs/paths/metrics, and
non-authorizing flags. It must retain sandbox boundary flags and write an
empty-schema Parquet file when no global evidence-request bucket
representatives exist. It must not open the full global leaderboard Parquet or
per-run evidence request files, recompute leaderboard rows, execute or
authorize validation, mutate source artifacts, change scoring or ranking,
change evidence-request selection, change trial IDs, change archive routing, or
change promotion state.
Catalog rows for descriptor-only input replay batch plans may include compact
source worklist, ready source, blocked source, plan item, unique ready replay
context, suppressed duplicate counts, and ready/planned archive bucket and
archive-window bucket count maps derived only from the already-loaded batch-plan
JSON payload and summary. These counts and maps are artifact navigation
metadata only and must not execute replay commands, authorize validation,
mutate source artifacts, change replay readiness, change archive routing, change
preflight behavior, change scoring or ranking, change evidence-request
selection, change trial IDs, or change promotion state.
Catalog rows for sandbox iteration indexes may include compact agent
action-plan counts and source-queue rollups derived only from the already-loaded
iteration index JSON payload. Catalog writers may also flatten the bounded
iteration index `agent_action_plan` list into a compact Parquet sidecar. That
sidecar may expose iteration/action identity, action priority/rank,
source-queue names, replay-context identifiers, path references, compact counts,
and non-authorizing flags for agent triage. It must not execute replay
commands, authorize validation, mutate source artifacts, change replay
readiness, change archive routing, change preflight behavior, change scoring or
ranking, change evidence-request selection, change trial IDs, or change
promotion state.
Catalog writers may also flatten bounded venue-expansion gap samples already
present on iteration action-plan items into a dedicated descriptor-only Parquet
worklist. The worklist may expose iteration/action identity, source queues,
path references, target venue, compact market-symbol key, data family,
interval, target status/action, bounded source coverage metadata, compact
counts, and non-authorizing flags so agents can query OKX, Bybit, and
Hyperliquid archive descriptor repair/add targets without reopening every
iteration index JSON. It must be derived only from the already-loaded iteration
index payload, write an empty-schema Parquet file when no samples exist, and
must not add descriptors, mutate archive manifests or source files, download
venue data, execute replay commands, authorize validation, write candidate
packs, change archive routing, change replay readiness, change preflight
behavior, change scoring or ranking, change evidence-request selection, change
trial IDs, or change promotion state.
Catalog writers may also derive a bounded iteration action-plan bucket queue
from those flattened action-plan rows, grouped by action and source queue.
Bucket rows may expose action/source-queue identity, compact counts, bounded
representative iteration IDs/actions/source queues, and non-authorizing flags
for agent triage. Catalog writers may also flatten those bounded bucket
representatives into a companion Parquet sidecar exposing bucket identity,
representative iteration/action metadata, replay-context identifiers, path
references, compact counts, and non-authorizing flags. Bucket queues,
representative rows, and sidecars must not execute replay commands, authorize
validation, mutate source artifacts, change replay readiness, change archive
routing, change preflight behavior, change scoring or ranking, change
evidence-request selection, change trial IDs, or change promotion state.
Catalog manifests may also include top-level replay batch-plan rollups and a
bounded replay batch-plan queue derived only from catalog rows. Rollups may
summarize batch-plan artifact count, descriptor count, ready/blocked source
rows, suppressed duplicates, unique ready replay contexts, ready/planned archive
bucket and archive-window bucket counts, and readiness status counts. Queue
items may expose artifact paths and the same compact counts and maps for agent
triage. These rollups and queues are read-only navigation metadata and must not
execute replay commands, authorize validation, mutate source artifacts, change
replay readiness, change archive routing, change preflight behavior, change
scoring or ranking, change evidence-request selection, change trial IDs, or
change promotion state.
Catalog manifests may also include bounded archive bucket and archive-window
bucket representative queues derived only from replay batch-plan catalog rows.
Representative queue items may expose bucket names, ready/planned source counts,
bounded representative artifact path metadata, and non-executing authorization
flags for agent triage. These representative queues must not read source
batch-plan JSON directly, execute replay commands, authorize validation, mutate
source artifacts, change replay readiness, change archive routing, change
preflight behavior, change scoring or ranking, change evidence-request
selection, change trial IDs, or change promotion state.
Catalog writers may also emit compact Parquet sidecars for replay batch-plan
bucket queues and bucket representatives. These sidecars must be flattened from
the bounded catalog queues, retain sandbox boundary flags, expose only
read-only bucket/count/path metadata and non-executing authorization flags, and
write empty-schema Parquet files when no bucket rows exist. Sidecars must not
execute replay commands, authorize validation, mutate source artifacts, change
replay readiness, change archive routing, change preflight behavior, change
scoring or ranking, change evidence-request selection, change trial IDs, or
change promotion state.
Catalog writers may also emit a compact sidecar index Parquet file for their
own catalog, replay, and strict-validation Parquet outputs. Sidecar index rows
may expose sidecar category, name, role, file name, path, file existence,
byte-size, SHA-256, row count, empty status, and non-authorizing flags. File
identity metadata must be computed only for companion sidecars written by the
same catalog write, after those sidecars are written, and must not include a
self-referential hash of the sidecar index file. The sidecar index is
navigation metadata only and must not scan additional source artifacts, execute
commands, authorize validation, or change any source artifact or research
decision.
Catalog rows for descriptor-only strict-validation request bundles may include
bundle IDs, source scope, request counts, deduped descriptor counts, duplicate
removal counts, execution mode, entrypoint, and source path metadata derived
only from the already-loaded bundle JSON payload. Catalog manifests may also
include a top-level strict-validation bundle summary and bounded bundle queue
derived only from catalog rows, and catalog writers may flatten that bounded
queue into a compact Parquet sidecar. The sidecar must retain sandbox boundary
flags, expose only read-only path/count/source/entrypoint metadata and
non-executing authorization flags, and write an empty-schema Parquet file when
no bundle queue rows exist.

Catalog writers may also flatten individual strict-validation descriptors from
already-loaded bundle JSON payloads into a cross-bundle descriptor Parquet
sidecar. Descriptor sidecars may include descriptor identity, source trial
identity, source scope, venue, symbol, market-window, source routing, compact
source metrics, required-evidence count, strict-validation entrypoint, execution
mode, and non-authorizing flags. They must retain sandbox boundary flags and
write an empty-schema Parquet file when no descriptor rows exist.

Catalog writers may also derive a bounded strict-validation descriptor priority
queue from those flattened descriptor rows. Priority queues may sort
descriptor-only evidence requests by source metric, source rank, and stable
descriptor identity, expose read-only descriptor/source/venue/metric/routing
metadata, and write a compact Parquet sidecar. Priority queues and sidecars
must retain sandbox boundary flags, include non-authorizing flags, and write an
empty-schema Parquet file when no descriptor rows exist.

Catalog writers may also derive bounded strict-validation descriptor bucket
queues from those flattened descriptor rows. Bucket queues may group descriptors
by venue/symbol and venue/symbol/requested-validation, expose descriptor,
bundle, source-trial, top-score, and representative descriptor ID counts, and
write a compact Parquet sidecar. Catalog writers may also write a companion
representative Parquet sidecar flattened from the bounded bucket queue
representatives, exposing read-only bucket identity, descriptor identity, source
trial, venue, symbol, requested-validation, market-window, source metric, and
routing metadata. Bucket queues, representative rows, and sidecars must retain
sandbox boundary flags, include non-authorizing flags, and write empty-schema
Parquet files when no bucket or representative rows exist.

These strict-validation bundle fields, rollups, queues, descriptor rows, and
sidecars are read-only navigation metadata for agent triage; they must not
execute strict validation, authorize validation execution, mutate source
artifacts, write candidate packs, create paper/live artifacts, change replay
readiness, change archive routing, change preflight behavior, change scoring or
ranking, change evidence-request selection, change trial IDs, or change
promotion state.

Catalogs are read-only analysis indexes. They must not execute sandbox runs,
execute strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration, or
claim promotion readiness.

## Next-Action Dashboard Rule

Sandbox next-action dashboards may read existing sandbox artifact catalog JSON
files and sandbox iteration index JSON files under a research output root to
produce a compact first-read JSON/Parquet navigation report. A dashboard may
summarize current iteration status, action queue counts, top blockers, missing
venue coverage, descriptor-only strict-validation request queues,
venue-expansion worklists, artifact integrity warnings, best-hypothesis
sidecar pointers, the next recommended implementation packet type, and exact
files to open next.

Dashboards are read-only navigation artifacts. They must not execute sandbox
sweeps, execute artifact indexers, execute strict-validation preflight, execute
strict validation, recompute rankings, recompute evidence requests, mutate
source artifacts, write candidate packs, create paper/live signals, define
sizing, place orders, change runtime mode, write live configuration, authorize
strict validation, authorize candidate-pack writing, claim candidate evidence,
or claim promotion readiness. Dashboard reports and Parquet rows must keep all
required sandbox boundary flags and explicit non-authorizing fields.

## Throughput Telemetry Rule

One-command sandbox iterations may record measurement-only throughput metadata
for agent diagnostics. This metadata may include total runtime, per-stage
runtime, process-local market-data cache hit/miss counts, 2024+ rows loaded,
source bytes read, workers requested/used, artifact byte estimates, and peak
traced memory when measurable. Telemetry must not include cached market frames
or source-integrity cache contents, and it must not affect trial identity,
strategy signals, archive routing, compatibility blockers, ranking, evidence
request selection, or validation behavior.

Sandbox throughput reports may scan existing iteration manifests under a
research output root and write compact JSON/Parquet summaries with bottleneck
rankings and missing-telemetry blockers for older manifests. Reports are
diagnostic only. They must not execute sandbox sweeps, execute artifact
indexers, execute strict-validation preflight, execute strict validation,
download provider data, mutate source artifacts, write candidate packs, create
paper/live signals, define sizing, place orders, change runtime mode, write
live configuration, claim speedup without a later repeated-baseline benchmark,
claim candidate evidence, or claim promotion readiness.

## Iteration Agent Brief Rule

Sandbox iteration agent briefs may summarize an existing one-command sandbox
iteration for fast agent handoff. A brief may include the next suggested
research action, reason codes, compact counts, top archive/preflight blockers,
top descriptor-only strict-validation request descriptors, and artifact paths
for coverage, preflight, sweep, analysis, falsification, request-bundle,
leaderboard, iteration manifest, and iteration step outputs.
Top validation-request descriptors may include compact source summaries copied
from descriptor-only strict-validation request bundle rows, including source
venue descriptor ID, routing mode, local source path, market bounds, and bounded
ZIP/TAR container member-selection diagnostics. These summaries are navigation
metadata only; they must not be treated as strict validation evidence or
execution authorization.
Briefs may also expose compact strategy-source and archive-source summaries
derived from materializer/build-report metadata so agents can triage skipped
catalog or archive inputs without reopening full build reports.
Briefs may also expose compact venue-expansion gap summaries copied from the
same iteration's archive coverage matrix, including target venues, action/status
counts, bounded actionable gap samples, and the venue-expansion sidecar Parquet
path in artifact references. These summaries are descriptor navigation metadata
only; they must not authorize archive descriptor creation, source downloads,
manifest mutation, strict validation, candidate-pack writing, or promotion.
Completed-iteration briefs may also expose bounded rejection/falsification
samples derived from the same iteration's existing sandbox analysis and
hypothesis falsification outputs. These samples are navigation metadata only:
they may identify failed hypotheses, decisions, representative rejected or
blocked trial IDs, compact metrics, and rejection/blocker reason counts, but
they must not alter scoring, ranking, falsification decisions, evidence-request
selection, strict validation behavior, or promotion state.
Briefs may also expose a compact `input_replay_context` for the same
one-command iteration. Replay context may include a deterministic
`replay_context_id`, the research command name, a non-executing `command_argv`
list, strategy and venue input modes, resolved input paths or roots, data
window values, sweep options, and bounded catalog/archive build options. It is
agent navigation metadata only. The argv list must not be treated as a shell
command, execution authorization, strict-validation authorization, candidate
evidence, or a request to mutate catalogs, archive manifests, or source files.

Generated one-command iteration specs may use recent-window presets for agent
workflow speed. Presets such as `recent_365d` must resolve to concrete
`data_window.start` and `data_window.end` values before preflight or sweep
execution, must record the preset/as-of/lookback/resolved-window metadata in
the iteration manifest and brief, and must clip any resolved start date to
`2024-01-01`. A recent-window preset must not silently override a supplied
explicit sandbox run spec.

Briefs are navigation artifacts only. They must not execute sandbox sweeps,
execute strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration,
mutate source archive files, or claim promotion readiness. Brief manifests and
rows must keep all required sandbox boundary flags. Cached iteration reuse must
validate brief JSON boundary flags and brief Parquet existence before returning
`reused_existing: true`.

## Iteration Index Rule

Sandbox iteration indexes may scan existing one-command iteration manifests and
agent briefs under a research output root to produce compact JSON/Parquet rows
for agent navigation. Rows may include iteration status, next action, reason
codes, coverage counts, requested-window archive coverage counts, preflight
counts, result counts, descriptor-only request counts, top blockers, top
validation-request descriptors, artifact paths, source catalog/archive
materialization paths and counts, and brief availability status.
Rows may also include read-only artifact availability diagnostics for already
referenced iteration, source-context, and handoff artifact paths. Availability
diagnostics may report referenced, present, and missing artifact counts plus
missing artifact keys, but they must not open child artifacts for validation or
mutate source artifacts.
Rows may preserve full archive coverage blocker reason counts in addition to
bounded top-blocker summaries so action queues do not depend on truncated
display fields.
Rows, agent briefs, action queues, recommended action details, and
agent action-plan items may also preserve bounded archive-coverage blocker
samples derived from coverage matrix rows. Samples may include coverage key,
venue/symbol/data family/interval, blocked descriptor IDs, bounded source
paths, routing modes, blocker reason counts, observed/declared/requested
window bounds, and requested-window row counts. They are descriptor navigation
metadata only and must not alter archive audit readiness, archive coverage
semantics, preflight trial estimates, sweep execution, ranking math,
evidence-request selection, strict validation behavior, or promotion state.
Rows may also preserve full preflight blocker reason counts in addition to
bounded top-preflight summaries so repair queues and agent handoffs retain the
complete blocker context for large strategy/archive matrices.
Rows, agent briefs, action queues, recommended action details, and
agent action-plan items may also preserve bounded compatibility-preflight
blocker samples derived from preflight rows. Samples may include descriptor and
strategy identity, signal/filter columns, side, venue/source routing metadata,
blocker reason counts, trial estimates, active signal count, market row counts,
high/low availability, and bounded column/container diagnostics. They are
descriptor navigation metadata only and must not alter compatibility-preflight
blocker semantics, trial estimates, strategy rows, venue descriptors, sweep
execution, ranking math, evidence-request selection, strict validation
behavior, or promotion state.
Rows, agent briefs, action queues, recommended rejection-review action details,
and agent action-plan items may also preserve bounded rejection/falsification
samples derived from already-produced sandbox analysis and hypothesis
falsification artifacts. Samples may include hypothesis/family identity,
falsification decision/reason, best trial ID and status, venue/symbol, compact
metrics, tested exit/filter variants, and compact rejected/blocked reason
counts. They are review navigation metadata only and must not alter sandbox
scoring, ranking, falsification decisions, blocker/rejection semantics, trial
IDs, evidence-request selection, strict validation behavior, or promotion
state.
Rows, action queues, and agent action-plan items may carry the same compact top
validation-request source summaries from agent briefs so agents can triage
descriptor-only strict-validation requests without reopening bundle artifacts.
Rows, action queues, recommended action details, and agent action-plan items may
also carry compact strategy-source and archive-source repair context, including
skipped-source or skipped-file reason counts and bounded samples.
Rows, action queues, recommended action details, and agent action-plan items may
also carry compact venue-expansion archive gap context derived from coverage
matrix sidecars. Indexes may expose a `venue_expansion_gap_queue` and a
descriptor-only `repair_or_add_venue_expansion_archives` action with target
venues, action/status counts, bounded samples, and the sidecar Parquet path.
That action is an agent planning hint only: it must not create descriptors,
download venue data, modify manifests, execute validation, write candidate
packs, change scoring, or claim promotion readiness.
Rows, action queues, recommended action details, and agent action-plan items may
also carry the same compact `input_replay_context` from iteration manifests or
briefs. Replay context may expose `replay_context_id`, command name,
`command_argv` as a list, strategy and venue input modes, resolved input paths
or roots, data windows, and bounded run/build options so agents can reproduce
or refresh a sandbox iteration from handoff artifacts. It is descriptor
navigation metadata only and must not execute commands, authorize strict
validation, alter source catalogs or archive manifests, mutate source files, or
change scoring, ranking, blocker semantics, evidence-request selection, trial
IDs, or promotion state.
Iteration indexes may also write a dedicated input replay worklist JSON/Parquet
artifact derived from indexed rows with available `input_replay_context`. The
worklist may flatten replay context IDs, argv-list command descriptors, input
modes, resolved paths or roots, data windows, recommended action context,
artifact availability, and compact counts for queryable agent handoffs. It is
not an execution queue: worklist rows must remain descriptor navigation
metadata only and must not execute replay commands, mutate source inputs,
authorize strict validation, write candidate artifacts, or change rankings,
trial IDs, evidence-request selection, or promotion state.
Replay worklist rows may also include filesystem readiness diagnostics for
paths already present in replay context, including output/spec/catalog/archive
references, expected file-vs-directory type, present/missing/wrong-type status,
missing keys, and summary counts. These diagnostics may check path existence
and type only; they must not open, parse, hash, download, repair, or mutate
referenced strategy catalogs, archive manifests, source files, or directories.
Replay worklist summaries may also include archive venue, symbol, data-family,
interval, requested-window, readiness, and path-availability rollups derived
only from worklist rows. These rollups are agent triage metadata for
multi-venue archive-backed iteration coverage and must not alter archive
routing, preflight behavior, sweep execution, ranking, evidence-request
selection, trial IDs, or promotion state.
Replay worklist rows and summaries may also include duplicate replay-context
metadata derived only from already-built worklist rows, including duplicate
group keys, per-row duplicate counts, duplicate flags, unique replay-context
counts, duplicate-group counts, duplicate item counts, duplicate group-key
lists, and archive/window unique-context rollups. These fields are agent triage
metadata for avoiding redundant refresh planning; they must not collapse
indexed rows, execute or suppress replay commands, mutate source artifacts,
alter readiness diagnostics, change archive routing, change preflight behavior,
change scoring or ranking, change evidence-request selection, change trial IDs,
or change promotion state.
Iteration indexes may also write a descriptor-only input replay batch plan
JSON/Parquet artifact derived only from the replay worklist. Batch-plan items
may include one representative ready replay descriptor per unique replay
context, argv as a structured list, source iteration IDs, suppressed duplicate
counts, archive/window fields, path-readiness summaries, and blocked-source
summary counts. The batch plan is an agent navigation artifact only: it must not
be a shell script, scheduler, executor, validation authorization artifact, or
candidate evidence, and it must not execute or suppress replay commands, mutate
source artifacts, change readiness diagnostics, change archive routing, change
preflight behavior, change scoring or ranking, change evidence-request
selection, change trial IDs, or change promotion state.
Rows may include deterministic recommended action hints derived only from
already-indexed metadata such as brief status, artifact availability, archive
blocker counts, materialized strategy-source skipped counts, strategy-source
skip reason counts, preflight blocker counts, descriptor-only validation
request counts, and rejection/block counts. These hints are navigation
metadata, not execution authorization.

Indexes may also include derived action queues for agent workflows. Action
queues may group existing rows into bounded strict-validation request,
preflight-repair, archive-window-repair, strategy-source-repair,
missing-brief, artifact-repair, and rejection-review worklists with stable
ordering, compact counts, blockers, validation-request descriptors, and
artifact paths. Strategy-source-repair queues may include rows whose indexed
materialized strategy-source counts or skip reason counts show skipped catalog
sources. Archive-window-repair queues may include
iterations whose full archive blocker counts, or older top-blocker fallbacks,
include `no_rows_in_requested_window`. These queues are summaries of
already-indexed metadata only; they do not create candidate evidence or
authorize validation execution.
Queue items may include the same recommended action hints as their source rows
so agents can choose the next repair or review step without reopening the row
payload.
Indexes may also include a global `agent_action_plan` derived from those
recommended actions. Action-plan items may carry deterministic priority,
source-queue labels, reason codes, blocker/request context, relevant
artifact/source paths, and a marker for actions blocked by a higher-priority
repair on the same iteration. The action plan is a read-only navigation view
over existing index rows and queues; it must not execute or authorize repair,
validation, candidate-pack, paper, or live work.
When an index report is written, implementations may also write the visible
action plan as a compact Parquet artifact and expose its path in the index
payload. This Parquet export is query-only navigation metadata and must carry
the same sandbox boundary flags as action-plan items.

Indexes may also include `action_queue_summaries` derived from the same matched
rows as each action queue. Queue summaries may aggregate all matched rows,
including rows hidden behind the visible queue limit, into iteration-status,
next-action, strategy-source status/suffix/skip-reason, coverage-status,
archive-blocker, preflight-status, preflight-blocker, falsification-decision,
recommended-action, and numeric count rollups. Queue summaries are read-only
navigation metadata and must not execute or authorize strict validation.
Queue items and summaries may include materialized strategy-catalog and
venue-archive source counts such as included/skipped strategy sources,
strategy-source skip reason counts, bounded skipped-source samples, and archive
files skipped by requested-window filtering, so agents can identify repair work
without reopening build reports.
Action queues may include an artifact-repair worklist for rows whose referenced
artifact paths are missing. This queue is only a read-only repair hint and must
not be treated as integrity validation, candidate evidence, or authorization to
rerun validation.

Indexes must validate sandbox boundary flags on source iteration manifests and
on any loaded brief artifacts. Missing brief references or missing brief files
may be reported as index row status so older or incomplete iterations stay
visible, but they must not be treated as candidate evidence or promotion
evidence. Index manifests and rows must keep all required sandbox boundary
flags.

Iteration indexes are read-only navigation artifacts. They must not execute
sandbox sweeps, execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, change runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Artifact Integrity Verification Rule

Sandbox artifact-integrity verification may read an existing run or suite
manifest and compare each manifest-recorded child artifact SHA-256 and byte
size with the file currently on disk. Verification must fail closed in the
report for missing integrity metadata, missing artifact paths, missing files,
or hash/size mismatches.

Verification reports are read-only diagnostics for agent handoffs. They may
write compact JSON/Parquet reports, but they must not alter source child
artifacts, execute sandbox sweeps, execute strict validation, write candidate
packs, create paper/live signals, define sizing, place orders, change runtime
mode, write live configuration, or claim promotion readiness. Report manifests
and rows must keep all required sandbox boundary flags.

Direct sandbox artifact consumers that read run or suite manifest child files
must reuse no-report integrity verification before opening those files. A
failed check must stop the consumer before writing derived reports or bundles.

## Global Leaderboard Rule

Sandbox global leaderboards may scan existing sandbox run manifests under the
configured research output root and aggregate compact rankings/evidence-request
artifacts by hypothesis and family. They may also derive compact bucket
leaderboard rows from the same already-loaded ranking rows for venue, symbol,
venue/symbol, family, exit, filter, and venue/family clusters, and write a
companion bucket Parquet artifact for agent triage. Leaderboards must validate
source run manifests, run child artifact integrity, ranking rows, and
evidence-request descriptors before summarizing them. Leaderboards must honor
configured run-count limits through deterministic bounded traversal; they must
not recursively sort all run manifests before applying `max_runs`.

Global leaderboard top-hypothesis rows may include a bounded
`evidence_request_source_contexts` preview derived only from already-loaded
evidence-request descriptors. The preview may expose source request/run/trial
IDs, source run paths, requested-validation labels, source metric fields,
market windows, venue/symbol/source identifiers, routing/data-path/container
metadata, execution assumptions, and non-authorizing boundary flags for agent
workflow speed. It must stay bounded and descriptor-only, and must not change
leaderboard scoring, ranking, falsification decisions, evidence-request
selection, trial IDs, archive routing, validation readiness, or promotion
state.

Leaderboard decisions such as strict-validation-requested, screened-positive,
mixed, falsified, or blocked are sandbox triage labels only. They must not be
treated as candidate evidence, candidate-pack eligibility, paper/live signals,
sizing instructions, order instructions, runtime changes, live configuration
writes, or promotion claims. Leaderboard manifests and rows must keep all
required sandbox boundary flags. Bucket leaderboard rows are subject to the
same restrictions and must not change scoring, ranking, falsification
decisions, evidence-request selection, trial IDs, archive routing, validation
readiness, or promotion state.

## Archive Descriptor Audit Rule

Sandbox archive descriptor audits may read venue archive manifests and local
market data files to verify descriptor routing, normalized 2024+ row counts,
descriptor-window coverage, and OHLC availability before strategy sweeps.
Audits must report missing data paths, loader failures, or empty descriptor
windows as blocker reasons instead of silently treating descriptors as ready.
When a descriptor source is a ZIP or TAR/TGZ container, audit rows should carry
the same bounded container member-selection metadata exposed by market-frame
normalization and archive manifest building. These fields are diagnostics only;
they must not change descriptor readiness, source-integrity checks, or blocker
semantics.
Audits may cache loaded and normalized market frames by resolved source path
inside one audit so repeated descriptor references do not reread the same local
file. Cached audit frames must preserve descriptor-specific rows, windows,
warnings, and blocker reasons, and source integrity must be evaluated per
descriptor before cached market data is used.
Audits may also receive a requested sandbox data window. When provided, audit
rows must report requested-window row counts and observed bounds separately
from descriptor-window counts, and otherwise loadable descriptors with zero
rows in that requested window must be blocked with an explicit
`no_rows_in_requested_window` reason.

Audits are readiness diagnostics only. They must not execute strategy sweeps,
execute strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration, or
claim promotion readiness. Audit manifests and rows must keep all required
sandbox boundary flags.

## Archive Coverage Matrix Rule

Sandbox archive coverage matrices may aggregate archive descriptor audit rows
into compact agent-facing buckets by venue, symbol, data family, and interval.
Coverage rows may summarize ready/blocked descriptor counts, blocker and
warning reason counts, descriptor IDs, source paths, normalized row counts,
descriptor-window row counts, market timestamp bounds, and declared/observed
window bounds. When a requested sandbox data window is supplied, coverage rows
must also aggregate requested-window row counts, requested-window observed
bounds, and requested-window blockers such as `no_rows_in_requested_window`.
Coverage rows may also aggregate container member-selection diagnostics from
source audit rows, including container kinds, selected member suffixes,
descriptor counts for container sources, selected/loadable member totals,
available member suffix counts, and bounded selected member-name samples. These
aggregates are navigation metadata only and must not change coverage bucket
status or strategy sweep behavior.
Coverage matrices must reuse the existing archive audit path so
source-integrity validation, 2024+ filtering, requested-window readiness,
shared-market-data smoke semantics, and loader failures stay consistent with
preflight and sweeps.
Coverage matrices may also write compact venue-expansion gap rows derived only
from already-produced coverage rows. These rows may compare OKX, Bybit, and
Hyperliquid readiness by market-symbol key, data family, and interval, and may
label each target venue as ready, mixed, blocked, or missing with a
descriptor-only next action. They must not change coverage bucket status,
archive descriptor loading, market-frame normalization, source-integrity
checks, requested-window filtering, preflight behavior, replay readiness,
strategy sweep behavior, ranking/scoring, trial IDs, evidence-request
selection, candidate-pack state, or promotion state.

Coverage matrices are launch-planning diagnostics only. They must not execute
sandbox sweeps, execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, change runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.
Coverage manifests and rows must keep all required sandbox boundary flags. When
agent iterations embed a coverage matrix, the matrix, venue-expansion gap
sidecar when referenced, and source audit artifacts are part of the cached
iteration evidence and must be checked before reusing the iteration manifest.

## Archive Manifest Builder Rule

Sandbox archive manifest builders may scan local archive files and write
loadable venue archive manifests for later sandbox audits and sweeps. Builders
must use the sandbox market-frame loader so pre-2024 rows are filtered out
before descriptor windows, row counts, or timestamp bounds are written.
Builder-supported local suffixes include plain CSV/TSV/JSON/JSONL/NDJSON/Parquet,
gzip-compressed CSV/TSV/JSON/JSONL/NDJSON, ZIP files containing
CSV/TSV/JSON/JSONL/NDJSON market-data members including gzip-compressed member
files, and `.tar`, `.tar.gz`, or `.tgz` files containing the same member types.
Headered CSV members and structured JSON/JSONL/NDJSON members inside ZIP or
TAR/TGZ files may be used for content-derived descriptor identity inference,
while headerless Binance Vision ZIPs remain loadable through the market-frame
normalization path. If multiple selected-priority members are present, build
rows must use the concatenated normalized frame for row counts and timestamp
bounds. Build-report rows should surface bounded container member-selection
metadata and searchable summary fields such as `container_kind`,
`selected_member_suffix`, `selected_member_count`,
`selected_member_name_sample`, `available_member_suffix_counts`, and
`loadable_member_count`. ZIP and TAR members must not be extracted to disk
during manifest building.

Archive manifest builders may receive a requested sandbox data window from an
agent iteration. When provided, builders should include only files whose
normalized 2024+ timestamp bounds overlap that requested window. Files outside
the requested window must be reported as skipped build-report rows with an
explicit `outside_requested_window` reason and requested-window metadata; they
must not be silently dropped.

Builders may infer descriptor identity from local paths and may accept explicit
venue, symbol, data-family, or interval overrides for agent workflows. Files
that cannot be loaded, contain no normalized 2024+ rows, have unsupported
formats, or lack required descriptor identity must be skipped with explicit
reasons. Builders must honor configured file-count limits through deterministic
bounded traversal; they must not recursively sort an entire archive tree before
applying `max_files`.

Builders may also infer descriptor identity from common content columns when
local archive paths are generic. Content-derived inference may use venue,
exchange, provider, symbol, instrument, coin/base/quote, interval, bar,
timeframe, channel, type, or data-family hints from already-loaded local rows.
Build-report rows must expose whether each descriptor identity field came from
an override, path, content, content columns, default, or missing inference.
Build-report rows may also expose loader-derived column metadata such as
bid/ask midpoint close derivations so agents can distinguish explicit
close-like price columns from book-derived midpoint sources.
Content-derived identity is an agent setup convenience only and must not be
treated as live venue execution proof.

Builders must record source-file SHA-256 and byte-size metadata for scanned
local archive files in build-report rows. Generated venue descriptors for
included files must carry the same source integrity metadata, and manifest
identity must change when source file content changes in place.

Descriptor-routed archive consumers must verify source integrity before
reading a descriptor `data_path` when `source_integrity` metadata is present.
Archive audits and compatibility preflights must report source-integrity
mismatches as blocker reasons. Archive-backed sweeps must fail closed before
reading changed local files. Shared-market-data smoke runs may bypass
descriptor source integrity because the caller has explicitly supplied a
separate shared data path.
Batch archive consumers may cache actual file-integrity reads by resolved
source path for speed, but expected integrity metadata must still be evaluated
per descriptor and a mismatch on any descriptor must fail closed before that
descriptor receives cached market data.
Compatibility preflights may cache loaded, windowed, and materialized market
frames by resolved source path inside one preflight run, after descriptor
source-integrity checks pass. Cached preflight frames must not collapse
descriptor-specific rows, routing metadata, trial estimates, or blocker
semantics.
Compatibility preflight rows may surface bounded container member-selection
diagnostics from normalized market metadata as first-class row fields, including
container kind, selected member suffix/count, selected member-name sample,
available member suffix counts, and loadable member count. These fields are
agent navigation metadata only and must not change trial estimates, blocker
reasons, rankings, sweep metrics, or evidence requests.
Archive-backed sweeps may copy the same bounded container member-selection
diagnostics from normalized market metadata into descriptor `market_source`
payloads written to result metadata, run manifests, evidence-request source
contexts, and descriptor-only strict-validation request bundle rows. These
fields are source provenance diagnostics only and must not change market frame
routing, trial IDs, trial estimates, blocker reasons, sweep metrics, rankings,
eligibility, or evidence-request selection.
One-command sandbox iterations may pass a process-local market-data cache
through archive coverage, compatibility preflight, and the archive sweep so the
same resolved local source is not read and normalized repeatedly. This cache
must stay in memory only, must not be serialized into JSON or Parquet artifacts,
must not change trial IDs, rankings, market-source metadata, or blocker
semantics, and must still evaluate source integrity per descriptor before
cached market data is used.

Generated manifests and build reports are local sandbox diagnostics only. They
must not download provider data, execute strategy sweeps, execute strict
validation, write candidate packs, create paper/live signals, define sizing,
place orders, change runtime mode, write live configuration, or claim promotion
readiness. Manifest and report rows must keep all required sandbox boundary
flags.

## CLI Rule

`run-rapid-strategy-sandbox` is a research command. It must be rejected in live
mode by the shared research-command preflight and all output directories must
resolve under the configured research output root. The command may read input
strategy catalogs, venue descriptors, and market data from local paths, but it
must only write sandbox artifacts.

`run-rapid-strategy-sandbox-suite` is also a research command. Its
`--output-dir` must resolve under the configured research output root. Suite
inputs may reference local paths, but command output must remain sandbox-only
suite artifacts and aggregated evidence-request descriptors. Suite execution
must preflight each case before running its sweep, and the CLI payload may
surface completed/skipped case counts plus preflight runnable/blocked trial
estimates.

`summarize-rapid-strategy-sandbox` is also a research command. Its `--run-dir`
must resolve under the configured research output root. It may write
`analysis_summary.json` inside the sandbox run directory, and that report must
remain sandbox-only and non-promotable.

`summarize-rapid-strategy-sandbox-hypotheses` is also a research command. Its
`--run-dir` or `--suite-dir` input must resolve under the configured research
output root. It may write hypothesis falsification JSON/Parquet indexes inside
the sandbox run or suite directory, and those indexes must remain sandbox-only
and non-promotable.

`export-rapid-strategy-sandbox-validation-requests` is also a research command.
Its `--run-dir`, `--suite-dir`, and optional `--output-dir` values must resolve
under the configured research output root. It may write descriptor-only
strict-validation request bundles, but it must not execute strict validation or
write candidate artifacts.

`preflight-rapid-strategy-sandbox-validation-requests` is also a research
command. Its `--bundle` and optional `--output-dir` values must resolve under
the configured research output root. It may write descriptor-only
strict-validation descriptor preflight JSON/Parquet reports for planning, but
it must not execute strict validation, write candidate packs, or authorize
promotion.

`export-rapid-strategy-sandbox-venue-expansion-requests` is also a research
command. Its `--catalog`, optional `--worklist`, and optional `--output-dir`
values must resolve under the configured research output root. It may write
descriptor-only venue-expansion archive-intake request bundles from existing
catalog/worklist artifacts, but it must not download provider data, mutate
archive manifests or source files, execute replay commands, execute validation,
or write candidate artifacts.

`index-rapid-strategy-sandbox-artifacts` is also a research command. Its
optional `--root-dir` and `--output-dir` values must resolve under the
configured research output root. It may write sandbox artifact catalog JSON and
Parquet indexes plus bounded queue sidecars, but it must not execute runs or
validation.

`index-rapid-strategy-sandbox-iterations` is also a research command. Its
optional `--root-dir` and `--output-dir` values must resolve under the
configured research output root. It may read existing sandbox iteration
manifests and agent briefs, then write sandbox iteration index JSON/Parquet
artifacts, but it must not execute runs, execute validation, or write candidate
artifacts.

`show-rapid-strategy-sandbox-next-action` is also a research command. Its
optional `--output-root`, `--artifact-catalog`, `--iteration-index`, and
`--output-dir` values must resolve under the configured research output root.
It may discover existing sandbox artifact catalog and iteration index JSON
files, then write a compact sandbox next-action JSON/Parquet report for agent
navigation, but it must not execute runs, execute indexers, execute
strict-validation preflight, execute strict validation, recompute evidence, or
write candidate artifacts.

`summarize-rapid-strategy-sandbox-throughput` is also a research command. Its
optional `--root-dir` and `--output-dir` values must resolve under the
configured research output root. It may scan existing one-command sandbox
iteration manifests and write throughput telemetry JSON/Parquet reports with
runtime, cache, memory, artifact-byte, and bottleneck diagnostics, but it must
not execute runs, execute indexers, execute strict-validation preflight,
execute strict validation, claim speedup, or write candidate artifacts.

`verify-rapid-strategy-sandbox-artifacts` is also a research command. Its
`--target` run/suite directory or manifest path and optional `--output-dir`
must resolve under the configured research output root. It may write
artifact-integrity verification JSON/Parquet reports, but it must not modify
source artifacts, execute runs, execute validation, or write candidate
artifacts.

`preflight-rapid-strategy-sandbox` is also a research command. Its optional
`--output-dir` must resolve under the configured research output root. It may
read a sandbox run spec, strategy catalog, venue archive manifest, and optional
shared market-data path, then write compatibility preflight JSON/Parquet
reports. It must not execute sweeps, execute strict validation, or write
candidate artifacts.

`rank-rapid-strategy-sandbox-artifacts` is also a research command. Its
optional `--root-dir` and `--output-dir` values must resolve under the
configured research output root. It may write global sandbox leaderboard JSON
and Parquet artifacts, but it must not execute runs, execute validation, or
write candidate artifacts.

`audit-rapid-strategy-sandbox-archives` is also a research command. Its
optional `--output-dir` must resolve under the configured research output root.
It may read local venue descriptor manifests and local market data paths, but it
must only write sandbox archive audit artifacts. Optional requested-window
arguments may narrow readiness diagnostics to the active sandbox data window,
but they must not mutate source descriptors or execute sweeps.

`summarize-rapid-strategy-sandbox-archive-coverage` is also a research
command. Its optional `--output-dir` must resolve under the configured research
output root. It may read local venue descriptor manifests and optional shared
market-data paths, run the archive audit path, and write sandbox archive
coverage JSON/Parquet artifacts, but it must not execute sweeps, execute
strict validation, or write candidate artifacts. Optional requested-window
arguments may narrow coverage diagnostics to the active sandbox data window,
but they must not mutate source descriptors or execute sweeps.

`build-rapid-strategy-sandbox-archive-manifest` is also a research command. Its
optional `--output-dir` must resolve under the configured research output root.
It may read local archive roots and write sandbox archive manifest/build-report
artifacts, but it must not download data, execute sweeps, execute validation, or
write candidate artifacts.

`build-rapid-strategy-sandbox-strategy-catalog` is also a research command. Its
optional `--output-dir` must resolve under the configured research output root.
It may read local strategy catalog roots and write normalized sandbox strategy
catalog/build-report artifacts, but it must not execute sweeps, execute
validation, or write candidate artifacts.

`run-rapid-strategy-sandbox-iteration` is also a research command. Its optional
`--output-dir` must resolve under the configured research output root. It may
materialize or reuse strategy catalogs and venue archive manifests, execute the
archive coverage matrix, execute the existing archive-backed sandbox sweep,
write sandbox analysis, hypothesis falsification, descriptor-only
strict-validation request bundles, global leaderboards, an agent brief, and an
iteration manifest. It must write archive coverage before compatibility
preflight, run compatibility preflight before sweep execution, and record the
coverage, preflight, and brief artifact paths plus runnable / blocked trial
estimates in the iteration manifest. Completed iterations may also record
bounded venue-expansion gap samples from archive coverage plus bounded
rejection/falsification samples derived from the already-written analysis and
falsification outputs. Generated-spec CLI window presets must
resolve to concrete 2024+ data windows before archive coverage or preflight
execution and must be recorded as `window_selection` metadata. Iterations must
also record inert `input_replay_context` metadata in the iteration manifest and
agent brief. Replay context may include the command name, non-executing
`command_argv` list, resolved input paths or roots, input modes, data windows,
and bounded options; it must not execute the command, bypass output-root
guards, authorize strict validation, mutate source inputs, or change trial
identity, ranking, evidence-request selection, or promotion state. Iterations
must pass the resolved data window into archive coverage so existing venue archive
manifests report requested-window readiness before preflight. When an
iteration materializes archive roots, the resolved data window should be passed
into archive manifest building so out-of-window files are skipped before
preflight while remaining visible in the build report. If preflight proves
there are zero
runnable trials, the iteration may stop after writing archive coverage,
preflight artifacts, an agent brief, and a final blocked manifest with skipped
downstream steps. It must not execute strict validation, write candidate
artifacts, create paper/live signals, define sizing, place orders, mutate
runtime mode, or write live configuration.

When an iteration manifest already exists and the command returns it as a
cached result, reuse must validate the cached artifact references first. Cached
brief, archive coverage, source-audit, preflight, analysis, falsification,
validation bundle, and leaderboard JSON artifacts must exist and retain sandbox
boundary flags; cached brief, archive coverage, source-audit, preflight,
falsification, validation bundle, leaderboard, and iteration-step Parquet
artifacts must exist; and completed cached iterations must verify the
referenced run manifest's child-artifact integrity before returning
`reused_existing: true`.
