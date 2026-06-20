# Stage R106 Sandbox End-To-End Venue Expansion Fixture Smoke Report

Date: 2026-06-20
Packet: `WPR106-369-sandbox-end-to-end-venue-expansion-fixture-smoke`

## Summary

WPR106-369 adds a fixture-level closed-loop regression for the rapid sandbox
venue-expansion workflow. The test proves the current sandbox components now
compose without manual edits:

```text
venue-expansion request bundle
-> local materializer descriptor candidate
-> candidate archive manifest
-> archive coverage
-> compatibility preflight
-> bounded sandbox archive sweep
-> analysis and hypothesis falsification
-> descriptor-only strict-validation request bundle
-> artifact catalog discovery
```

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "end_to_end_venue_expansion_fixture"`
  - `1 passed, 181 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `196 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Boundary Statement

This is fixture workflow regression evidence only. It is not real-market
archive evidence, candidate evidence, or promotion evidence. It does not add
provider downloads, mutate source archive files, mutate existing manifests,
execute strict validation, write candidate packs, create paper/live behavior,
define sizing, place orders, change runtime mode, write live configuration, or
claim promotion readiness.
