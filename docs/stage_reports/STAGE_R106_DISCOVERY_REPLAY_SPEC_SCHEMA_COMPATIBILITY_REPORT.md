# Stage R106 Discovery Replay Spec Schema Compatibility Report

Work packet:
`docs/work_packets/WPR106-43-discovery-replay-spec-schema-compatibility.md`

Date: 2026-05-31

## Summary

WPR106-43 restores compatibility between the WPR106-41 discovery-run schema
guard and the WPR106-31 discovery lead replay spec specialization.

The active discovery parser still rejects arbitrary stale or misspelled
`spec_version` values, but it now accepts the known
`discovery-lead-replay-spec-v1` specialization and its top-level
`replay_metadata` field. This keeps replay specs runnable and validateable
without weakening ordinary discovery-run schema checks.

## Code Changes

Updated:

- `src/tradingbotsuite/research_discovery/spec.py`
- `tests/research_discovery/test_discovery_spec.py`

The parser now exposes accepted discovery-run spec versions in
`discovery_run_schema()` and accepts:

- `discovery-run-spec-v1`
- `discovery-lead-replay-spec-v1`

`replay_metadata` is treated as a known top-level replay metadata field. Nested
active discovery sections and trial templates still reject unknown fields.

## Research Boundary

No live, paper, runtime, order-placement, promotion, strategy, discovery
behavior, candidate gate, validation floor, or candidate-pack behavior was
changed. No generated replay artifacts were modified or produced.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_discovery_lead_replay.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Observed:

- focused replay/spec tests: 19 passed;
- full research-discovery suite: 226 passed.

## Candidate Status

No candidate-ready claim exists. No candidate pack was produced. Zero eligible
candidates remains valid evidence.

## Next Work

Continue with the empirical replay-overlay packet: generate cycle specs from
WPR106-31 replay artifacts, validate a small reference sample, and only then run
the full BTCUSDT/ETHUSDT overlay/ranking/gate evidence path.
