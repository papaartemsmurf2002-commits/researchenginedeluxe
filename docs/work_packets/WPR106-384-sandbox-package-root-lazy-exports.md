# WPR106-384 - Sandbox Package Root Lazy Exports

## Status

closed

## Objective

Close the audit M7 sandbox package-root coupling gap by keeping the existing
`tradingbotsuite.research_sandbox` public export names while avoiding eager
imports of the entire sandbox module graph at package import time.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-377-sandbox-publication-coherence.md`
- `docs/work_packets/WPR106-383-historical-fixture-cycle-runtime-bound.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/__init__.py`
- `tests/research_sandbox/test_post_audit_safety.py`
- `docs/work_packets/WPR106-384-sandbox-package-root-lazy-exports.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_PACKAGE_ROOT_LAZY_EXPORTS_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Preserve the existing package-root public names in `__all__`.
- Do not change sandbox execution, artifact schemas, trial identity,
  candidate-pack gates, strict-validation behavior, live/paper behavior,
  sizing, order placement, runtime mode, live configuration, or promotion
  semantics.
- Do not modify mixed CLI source files in this packet.
- Keep sandbox outputs research-only, observe-only, sandbox-only,
  non-promotable, and non-candidate-evidence.

## Acceptance criteria

- Importing `tradingbotsuite.research_sandbox` alone does not import heavy
  artifact/catalog/iteration modules.
- Accessing an exported name lazily imports only that name's owning module.
- Existing `from tradingbotsuite.research_sandbox import ...` consumers keep
  working.
- Focused sandbox tests and import smoke pass.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_post_audit_safety.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -c "import tradingbotsuite.research_sandbox as sandbox; print(len(sandbox.__all__))"
git diff --cached --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_post_audit_safety.py -q`
  passed with 18 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  passed with 221 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  passed with 26 tests.
- `$env:PYTHONPATH='src'; python -c "import sys; import tradingbotsuite.research_sandbox as sandbox; print(len(sandbox.__all__), 'tradingbotsuite.research_sandbox.catalog' in sys.modules); _ = sandbox.DataWindow; print('tradingbotsuite.research_sandbox.spec' in sys.modules, 'tradingbotsuite.research_sandbox.catalog' in sys.modules)"`
  printed `109 False` and `True False`.
- `python -m compileall -q src\tradingbotsuite` passed.

## Stop conditions

- Lazy exports break existing package-root imports.
- The fix requires touching CLI dispatch or unrelated sandbox modules.
- Import timing changes require weakening boundary or artifact validation.
