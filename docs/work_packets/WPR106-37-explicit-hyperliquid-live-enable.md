# WPR106-37 Explicit Hyperliquid Live Enable

## Goal

Close `ISSUE-R106-013` by ensuring local Hyperliquid credential files can load
signer/account/testnet endpoint data but cannot enable live/testnet execution
unless `TBS_HL_ENABLE_LIVE=true` is explicitly present.

This packet must not add live, paper, order-placement, sizing, promotion, or
research strategy behavior.

## Current Repo Facts

- `_load_hyperliquid_testnet_credentials()` parses `hyperliquidtestnet.txt`.
- If the file looks like testnet credentials, it sets testnet `base_url` and
  `enable_live=True`.
- `AppConfig.from_env()` uses that file-provided `enable_live` as the default
  when `TBS_HL_ENABLE_LIVE` is absent.
- `docs/OPERATOR_QUICKSTART.md` says live/testnet requires
  `TBS_RUNTIME_MODE="live"` and `TBS_HL_ENABLE_LIVE="true"`.
- Existing config tests assert the unsafe implicit enablement behavior.

## Conflicts And Stale Docs Found

- The code and config tests conflict with operator docs and current P0 safety
  rules.
- Credential files may remain useful for signer/account and testnet endpoint
  loading, but they must be passive until explicit live enablement is set.

## Allowed Edit Paths

- `docs/work_packets/WPR106-37-explicit-hyperliquid-live-enable.md`
- `docs/work_packets/WPR106-37-progress.jsonl`
- `src/tradingbotsuite/config.py`
- `tests/test_config.py`
- `tests/tradingbotsuite/test_config.py`
- focused live preflight tests if needed
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_EXPLICIT_HYPERLIQUID_LIVE_ENABLE_REPORT.md`

## Forbidden Edit Paths

- execution adapters and order-placement behavior
- runtime mode switching behavior beyond config parsing if not required
- research strategy/model/filter/candidate gates
- generated artifacts, fixture data, or local credential files
- `.pytest_cache/**`

## Subagents Used

- Safety Gatekeeper: inspect config parsing, live preflight expectations, and
  credential-file risk.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\test_config.py tests\tradingbotsuite\test_config.py tests\live\test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Adjust the focused config path to repo reality if only one config test file is
present.

## Artifacts Expected

- Tests proving credential-file presence does not imply `enable_live`.
- Tests proving explicit `TBS_HL_ENABLE_LIVE=true` still enables when the
  operator intentionally requests it.
- Updated issue registry and stage report.

No live order, paper order, runtime mutation, candidate pack, or generated
research data artifact is expected.

## Definition Of Done

- `hyperliquidtestnet.txt` can load passive testnet endpoint/account/signer
  data.
- `enable_live` is false unless `TBS_HL_ENABLE_LIVE` is explicitly truthy.
- Explicit env values override file-derived signer/account/base URL as before.
- Live preflight still blocks unsafe live runtime configurations.
- `ISSUE-R106-013` is resolved only after focused validation passes.

## Rollback Plan

Revert only files in the allowed edit paths. Do not touch local credential
files, execution adapters, runtime/live order-placement code, generated
artifacts, or unrelated cache state.
