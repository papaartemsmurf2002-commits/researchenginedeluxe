# WPR106-26 Full Repo Mismatch And Bug Audit

## Summary

Run a broad repo audit after the WPR106-24 and WPR106-25 migrated-path fixes.
The goal is to find remaining path mismatches, stale checkout references,
research/live boundary hazards, misleading readiness claims, fragile generated
artifact handoff paths, and validation failures before the next autopilot run.

This packet is audit-first. Code fixes are allowed only for confirmed blockers
that are narrow, reproducible, and covered by focused tests. Generated research
artifacts must not be rewritten.

## Allowed Paths

Audit/read scope:

- Full repository.

Edit scope:

- `docs/work_packets/WPR106-26-full-repo-mismatch-bug-audit.md`
- `docs/stage_reports/STAGE_R106_FULL_REPO_MISMATCH_BUG_AUDIT_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/**` only for a confirmed P0/P1 blocker found during
  this audit
- `tests/**` only for regressions covering such a blocker

Do not edit:

- generated research data, trial files, Parquet ledgers, fixture packs,
  catalog artifacts, or runtime DBs;
- live configuration, runtime mode, sizing, order placement, or promotion
  readiness behavior.

## Audit Plan

1. Governance and dirty-worktree review:
   - Confirm current branch/status.
   - Preserve unrelated prior edits.
   - Confirm open blocker count from `docs/KNOWN_ISSUES.md`.
2. Static mismatch scans:
   - stale old-root paths: `C:\Users\papaa\Music\tradingbotsuite`;
   - current-root assumptions: `C:\Users\papaa\Music\researchenginedeluxe`;
   - `promotion_ready: true`;
   - live/order-placement imports from research packages;
   - runtime-mode/live config writes;
   - silent zero-fill patterns;
   - TODO/FIXME/HACK markers;
   - broad recursive artifact scans and old package import surprises.
3. Generated-artifact portability checks:
   - active catalog/spec paths;
   - BTC/ETH discovery manifests;
   - BTC/ETH historical-cycle manifests;
   - analysis, delta, exit-lab, eligibility manifests where present.
4. Validation:
   - compileall;
   - contracts;
   - research artifacts;
   - research discovery;
   - historical;
   - live;
   - operator UI;
   - focused checks for the WPR106 path-portability surfaces.
5. Findings:
   - Fix narrow P0/P1 blockers immediately if safe.
   - Otherwise record follow-up issue/packet recommendations.

## Acceptance Criteria

- Report states whether the current repo has remaining known migration/path
  blockers likely to break the next autopilot run.
- Report lists validation commands and results.
- Any new P0/P1 finding is added to `docs/KNOWN_ISSUES.md`.
- No generated artifacts are rewritten.
- No live execution, live config, runtime mode, order placement, sizing, or
  promotion readiness is introduced.

## Results

- Found and resolved `ISSUE-R106-006`: nested generated-manifest metadata
  outside `required_outputs` could still retain old checkout strings after
  read-time normalization.
- No generated artifact was rewritten.
- Static scans found no unsafe production `promotion_ready: true`, no
  production source/config hard-coded old checkout path, and no research-owned
  order-placement imports.
- Targeted operator-run manifest audit checked 22 manifests. After the fix,
  normalized payloads had 0 old-root strings, 0 outside required outputs, 0
  missing required outputs, and 0 read errors.
- Grouped validation passed across contracts, research artifacts,
  research-discovery, live, historical, backtesting, features, optimization,
  research-cycle, unit, integration, and tradingbotsuite suites.
