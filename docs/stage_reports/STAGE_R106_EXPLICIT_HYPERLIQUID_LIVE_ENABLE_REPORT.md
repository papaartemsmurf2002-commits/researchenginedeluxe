# Stage R106 Explicit Hyperliquid Live Enable Report

Date: 2026-05-31

Work packet: `docs/work_packets/WPR106-37-explicit-hyperliquid-live-enable.md`

## Scope

Closed `ISSUE-R106-013` without adding live, paper, order-placement,
promotion, sizing, or research strategy behavior.

## Changes

- `src/tradingbotsuite/config.py` keeps `hyperliquidtestnet.txt` parsing
  passive. The file may supply account, signer, source path, and testnet base
  URL data, but it no longer supplies `enable_live`.
- `AppConfig.from_env()` now derives `hyperliquid.enable_live` only from
  explicit `TBS_HL_ENABLE_LIVE`, defaulting to false.
- Config tests prove file-only credentials remain passive, explicit
  `TBS_HL_ENABLE_LIVE=true` still opts in, explicit env credentials override
  file credentials, and explicit mainnet URL plus file credentials still does
  not enable live without the live flag.
- Live preflight tests prove file-supplied key/account data blocks with
  `hyperliquid_live_not_enabled` when the explicit live flag is absent.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\test_config.py tests\tradingbotsuite\test_config.py tests\live\test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- compile passed
- focused config/live preflight suite: 50 passed
- contracts: 430 passed
- diff check passed with line-ending warnings only

## Boundary Statement

Credential-file presence is no longer live authorization. Research outputs are
not live signals, no candidate gates were changed, and no runtime/paper/live
execution behavior was added.

## Remaining Blockers

- `ISSUE-R106-014` remains open: runtime artifact validation is not mode-aware
  and unknown or mode-ambiguous manifests must fail closed.
- `ISSUE-R104-001` remains open: candidate-ready empirical evidence still
  requires durable candidate-depth data and downstream validation.
