# V1 Findings Report

Audit date: April 10, 2026

This report is ordered by severity and grouped by subsystem. Items already remediated in this pass are called out explicitly.

## Medium

### Market-data feature depth

1. Funding, premium, and open-interest features from the broader blueprint are still not captured in the market-data service.
   Impact: the v1 execution and microstructure stack is complete, but the broader feature packet is still slimmer than the blueprint’s full later-stage research shape.
   Status: acceptable for the current BTC-first v1 baseline, but still a real expansion item.

## Low

### Configuration safety

2. Runtime config previously accepted invalid zero or negative values for critical sizing and timeout settings in [config.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/config.py).
   Impact: silent misconfiguration could have produced unsafe runtime behavior.
   Status: fixed in this audit with fail-fast validation and normalized microstructure windows.

### Operator documentation

3. The operator guide mixed `cmd.exe` syntax into a PowerShell-first workflow.
   Impact: avoidable operator friction during local testing.
   Status: fixed in this audit.

### Hyperliquid live confirmation

4. The earlier false smoke failure was consistent with an adapter-side confirmation window that was capped at `750ms` even when the configured timeout was longer.
   Impact: a real exchange fill could be treated as `order_timeout` under slower post-trade reconciliation, encouraging duplicate retries.
   Status: fixed by using the full configured timeout window and re-verifying on testnet.

## Residual Risk Notes

- Hyperliquid client bootstrap still performs blocking metadata fetches during adapter construction when live mode is enabled. This is acceptable for a single-process bot, but moving that work behind async startup would be a cleaner production hardening step.
- The current market-data feature set now includes local diff-depth reconstruction and queue imbalance, but not the full broader research bundle of funding, premium, and open-interest features.
- Acceptance-model fields remain bootstrap placeholders by design. They are visible and persisted, but not yet trained or calibrated.
