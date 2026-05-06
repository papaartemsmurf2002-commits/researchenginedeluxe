# WPR68-01 Operator Quickstart Documentation

Stage: R68 operator quickstart documentation
Owner: Codex Research Agent
Status: closed
Created: 2026-05-06

## Goal

Add a compact, user-friendly operator quickstart that gives ready-to-use
commands, normal workflows, safety responses, and clear live/testnet warnings.
Expose it through the existing operator UI Guides page so an operator can work
from the browser without reading the full technical manual first.

## Allowed paths

```text
README.md
docs/OPERATOR_QUICKSTART.md
docs/OPERATOR_GUIDE.md
src/tradingbotsuite/operator_console.py
tests/tradingbotsuite/test_operator_ui.py
docs/work_packets/WPR68-01-operator-quickstart-documentation.md
docs/stage_reports/STAGE_R68_OPERATOR_QUICKSTART_DOCUMENTATION_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Documentation and guide-list wiring only.
- Do not change operator command behavior, live execution behavior, research
  execution behavior, promotion behavior, or generated artifacts.
- Keep live/testnet instructions explicit that live is opt-in and gated by
  preflight.
- Preserve research-only boundaries and avoid performance claims.

## Review checklist

- Quickstart starts with safe paper-mode usage.
- Commands are copy-ready for PowerShell.
- Operator pages and buttons are explained in compact language.
- Safety states include immediate operator actions.
- Research jobs are described as offline/research-only.
- Live/testnet usage includes preflight, credential, and risk warnings.
- Guides UI includes the quickstart before the longer operator guide.

## Exit validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
```

## Close evidence

- Added `docs/OPERATOR_QUICKSTART.md` as a compact operator run card with
  copy-ready PowerShell commands, page map, normal daily checklist, button
  rules, safety responses, research-job rules, live/testnet checklist, shell
  fallback, common fixes, and stop conditions.
- Linked the quickstart from `README.md` and added a pointer at the top of the
  longer `docs/OPERATOR_GUIDE.md`.
- Wired `Operator Quickstart` as the first guide document exposed by the
  operator UI Guides page/API.
- Added operator UI tests proving the quickstart appears in `/ui/guides` and is
  first in `/api/operator/guides`.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
    - 26 passed
  - `git diff --check`
