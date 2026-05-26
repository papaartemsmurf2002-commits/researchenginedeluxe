# Local migration extras manifest

Migration date: 2026-05-27
Source project: C:\Users\papaa\Music\tradingbotsuite
Source commit: 174fcb53b0b2f2039c126f345b7abca5afeff34d
Destination repo: papaartemsmurf2002-commits/researchenginedeluxe

## Included in this destination-only commit

- BINANCE_BTCUSDT.P, 15 (2).csv
- chart_export_debug.csv
- .hypothesis/
- .lake_cache/
- .pytest_cache/
- .tmp/
- __pycache__/

These files were ignored/local in the source checkout and small enough for a normal GitHub commit.

## Excluded from Git publication

- hyperliquidtestnet.txt
- .env and .env.*
- .git/
- ignored data/ outputs copied during migration probing

The ignored data/ tree is not committed because the temp-clone audit found roughly 794,341 files totaling about 98.2 GB, 145 files at or above GitHub's 100 MB hard limit, very deep long-path research-output trees, and SQLite/testnet-looking local runtime files. Publishing those into the public destination Git history would be unreliable and could expose local runtime state. The checked research fixtures already tracked by the source branch are included in the preserved branch history.
