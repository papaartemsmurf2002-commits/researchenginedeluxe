# WPR105-02 Secure Handoff Export Hygiene

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-19

## Goal

Add an explicit secure handoff/export configuration for future repo summaries
and external audit bundles. The config should include source, tests, docs, and
configs while excluding generated data, caches, operator artifacts, credentials,
logs, databases, and large binary evidence.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `configs/handoff/**`
- `tests/contracts/**`

## Constraints

- Documentation/config/test only; do not change research execution,
  generated run artifacts, fixture packs, live runtime settings,
  order-placement code, promotion behavior, or sizing behavior.
- Keep the config conservative and security-first.
- Preserve research-only boundaries and do not mark any artifact as
  promotion-ready.

## Planned implementation

1. Add a checked secure handoff export config under `configs/handoff/`.
2. Include only source, configs, docs, tests, README, and packaging metadata.
3. Exclude `data/**`, operator runs, caches, local credentials, `.env`, logs,
   databases, Parquet outputs, virtual environments, and Python caches.
4. Add a contract test that verifies security checks and critical exclusion
   patterns remain present.
5. Record validation and stage evidence.

## Validation target

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_r105_secure_handoff_export_config.py -q
git diff --check
```

## Exit evidence

- Added `configs/handoff/r105_secure_repo_export.json` with source/docs/tests
  include patterns, gitignore/dotignore/default ignore support, explicit
  security checks, and research-only boundary metadata.
- The config excludes generated data, operator runs, caches, local credentials,
  `.env` files, logs, SQLite/DB files, Parquet outputs, archives, CSVs,
  virtual environments, and Python caches.
- Added
  `tests/contracts/test_r105_secure_handoff_export_config.py` to lock the
  security settings and critical exclusion patterns.
- Validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_r105_secure_handoff_export_config.py -q`.
