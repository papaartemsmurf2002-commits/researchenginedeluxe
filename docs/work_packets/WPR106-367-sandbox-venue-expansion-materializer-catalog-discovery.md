# WPR106-367 - Sandbox Venue Expansion Materializer Catalog Discovery

## Status

closed

## Objective

Make WPR106-366 venue-expansion materializer outputs discoverable from the
existing sandbox artifact catalog so agents can find descriptor candidates and
dry-run blockers without opening materializer output directories manually.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-366-sandbox-venue-expansion-local-materializer.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/work_packets/WPR106-367-sandbox-venue-expansion-materializer-catalog-discovery.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_EXPANSION_MATERIALIZER_CATALOG_DISCOVERY_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Boundary constraints

- Catalog existing materializer artifacts only.
- Do not rerun materialization, mutate source archive files, write or modify
  archive manifests, download provider data, run sandbox sweeps, run strict
  validation, write candidate packs, create paper/live artifacts, add sizing,
  place orders, change runtime mode, write live configuration, or claim
  promotion readiness.
- Preserve all sandbox boundary flags and dry-run semantics.

## Acceptance criteria

- `index_sandbox_artifacts` discovers
  `sandbox_venue_expansion_descriptor_candidates.json` as
  `venue_expansion_descriptor_candidates`.
- `index_sandbox_artifacts` discovers
  `sandbox_venue_expansion_manifest_patch_dry_run.json` as
  `venue_expansion_manifest_patch_dry_run`.
- Catalog rows expose materializer request, candidate, ready, blocked, scan,
  and output path counts.
- Focused tests prove catalog discovery and boundary flags for these artifacts.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "materializer_catalog"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Exit evidence

- Added catalog discovery for
  `sandbox_venue_expansion_descriptor_candidates.json` as
  `venue_expansion_descriptor_candidates`.
- Added catalog discovery for
  `sandbox_venue_expansion_manifest_patch_dry_run.json` as
  `venue_expansion_manifest_patch_dry_run`.
- Catalog rows now expose materializer ID, source/filtered request counts,
  descriptor-candidate counts, dry-run patch row counts, ready/blocked request
  counts, archive scan counts, scan status/reason counts, candidate output
  paths, dry-run patch output paths, and explicit false provider/archive
  mutation authorization/execution fields.
- Focused catalog regression passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "materializer_catalog"`
  reported 1 passed / 178 deselected.
- Broader validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  reported 193 passed.
- `python -m compileall -q src\tradingbotsuite` passed.
