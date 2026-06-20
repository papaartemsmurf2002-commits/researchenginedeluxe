# WPR106-365 Sandbox Commit Surface Classification

Date: 2026-06-20

## Classification Summary

The post-audit Rapid Strategy Iteration Sandbox is source-coupled across a
single package, one smoke config, and its focused test directory. These files
must be published or staged together for a coherent sandbox commit because the
checked-in workflow now runs `tests/research_sandbox` and the sandbox commands
import `tradingbotsuite.research_sandbox`.

This packet does not stage, delete, revert, or rewrite the broader inherited
dirty tree. It records the keep/split boundary so later review or publication
work can avoid accidentally mixing sandbox source with unrelated research,
operator, config, or generated-output work.

## Keep Together

As of the local check on 2026-06-20, the intended sandbox source/config/test
surface reported by
`git ls-files --others --exclude-standard src\tradingbotsuite\research_sandbox tests\research_sandbox configs\sandbox`
is:

- `configs/sandbox/rapid_strategy_iteration_sandbox_smoke_v1.json`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/research_sandbox/analytics.py`
- `src/tradingbotsuite/research_sandbox/archive_audit.py`
- `src/tradingbotsuite/research_sandbox/archive_coverage.py`
- `src/tradingbotsuite/research_sandbox/archive_manifest.py`
- `src/tradingbotsuite/research_sandbox/boundary.py`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `src/tradingbotsuite/research_sandbox/evidence_request.py`
- `src/tradingbotsuite/research_sandbox/falsification.py`
- `src/tradingbotsuite/research_sandbox/fast_backtest.py`
- `src/tradingbotsuite/research_sandbox/identity.py`
- `src/tradingbotsuite/research_sandbox/intake.py`
- `src/tradingbotsuite/research_sandbox/integrity.py`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `src/tradingbotsuite/research_sandbox/leaderboard.py`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `src/tradingbotsuite/research_sandbox/paths.py`
- `src/tradingbotsuite/research_sandbox/preflight.py`
- `src/tradingbotsuite/research_sandbox/runner.py`
- `src/tradingbotsuite/research_sandbox/spec.py`
- `src/tradingbotsuite/research_sandbox/store.py`
- `src/tradingbotsuite/research_sandbox/strategy_blueprints.py`
- `src/tradingbotsuite/research_sandbox/strategy_catalog_materializer.py`
- `src/tradingbotsuite/research_sandbox/suite.py`
- `src/tradingbotsuite/research_sandbox/validation_bundle.py`
- `src/tradingbotsuite/research_sandbox/venue_expansion_requests.py`
- `tests/research_sandbox/test_post_audit_safety.py`
- `tests/research_sandbox/test_sandbox_foundation.py`

The packet/report/docs from WPR106-362 through WPR106-365 are also part of the
review context for this sandbox publication surface.

## Ignore Or Keep Out Of Scope

- `outputs/` is generated sandbox/research output and is ignored by
  `.gitignore`; `git ls-files --others --exclude-standard outputs |
  Select-Object -First 20` returned no paths.
- The much broader modified/untracked tree includes inherited operator,
  research, config, docs, cache, and experimental files. Those files are not
  classified by this packet and must not be swept into a sandbox publication
  without their own packet/review.

## Coherence Rule

A future sandbox publication or stage action should include the complete
`configs/sandbox`, `src/tradingbotsuite/research_sandbox`, and
`tests/research_sandbox` surface above together with the related WPR106
packets/reports. Publishing only the tracked workflow changes without the
untracked sandbox package would make the CI workflow reference a missing test
surface.

## Boundary Statement

This is a documentation-only classification. It does not create candidate
packs, run strict validation, mutate archive descriptors/manifests, download
provider data, execute paper/live behavior, place orders, touch sizing, alter
runtime mode, write live configuration, or claim promotion readiness.
