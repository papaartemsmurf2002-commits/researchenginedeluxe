# WPR106-208 Calendar Profile Train-Window Control Audit

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Falsify or salvage the WPR106-139 strict calendar/session rows with
source-level train-window sensitivity controls. WPR106-139 found active,
strict-looking 2024-forward rows but all strict rows lost in May 2026.
WPR106-140 and WPR106-185 already rejected causal rolling and prior-month
calendar variants. This packet asks a narrower source-level question: do the
fixed WPR106-139 strict rows remain plausible when the calendar profile is fit
on earlier pre-May subwindows and evaluated on later pre-May pseudo-OOS
windows before any May benchmark is inspected?

## Data And Selection Policy

- Source rows are the fixed WPR106-139 strict selected rows.
- Candidate parameters, templates, sessions, volatility filters, flow filters,
  holds, and thresholds are fixed from WPR106-139 pre-May selection.
- Calendar profile controls are fit only on pre-May source data:
  full pre-May, 2024 only, 2025 only, 2024 through 2025, and recent 2025-H2
  through 2026-April.
- Control selection and pseudo-OOS diagnostics use only 2024-01-01 through
  2026-04-30 evidence.
- May 2026 is benchmark-only after fixed candidate/profile-control rows are
  evaluated and selected from pre-May pseudo-OOS behavior.
- All outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-208-calendar-profile-train-window-control-audit.md`
- `docs/stage_reports/STAGE_R106_CALENDAR_PROFILE_TRAIN_WINDOW_CONTROL_AUDIT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_208_calendar_profile_train_window_control_audit/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope unless this packet is explicitly amended before the
edit.

## Planned Work

1. Create a packet-local runner that imports the WPR106-139 source runner,
   rebuilds BTCUSDT/ETHUSDT archive contexts, and reuses its completed-bar
   feature and accepted-trade accounting.
2. Freeze the WPR106-139 strict candidate parameter rows.
3. Refit each candidate's calendar profile under multiple pre-May training
   windows while preserving the original candidate thresholds and filters.
4. Evaluate each fixed control on pre-May pseudo-OOS windows, especially
   2025 through 2026-April for 2024-only profiles and 2026 Jan-April for
   2024-2025 profiles.
5. Select any profile-control rows that pass pre-May pseudo-OOS stability
   criteria without May feedback, then benchmark that fixed set on May 2026.
6. Compare full-window WPR106-139 fit, train-window controls, and May benchmark
   behavior.
7. Document whether the strict calendar/session pocket is a robust lead, a
   train-window artifact, or a rejected overfit diagnostic.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; compute acceleration is limited
to cached source contexts/features and vectorized pandas/numpy artifact
processing.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_208_calendar_profile_train_window_control_audit\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

The completed runner imported the WPR106-139 source runner, rebuilt BTCUSDT
and ETHUSDT archive contexts, and evaluated the 17 fixed WPR106-139 strict
selected candidates under five pre-May profile training policies. It rebuilt
25 cached feature sets and wrote 510 non-May control-window rows.

Among 51 primary pseudo-OOS rows, 36 were positive, 4 passed strict
pseudo-OOS controls, and 22 passed loose pseudo-OOS controls. The fixed
selected control set contains 22 controls, with median selected pseudo-OOS
return +0.173659 and median selected pseudo-OOS losing months 1.

May was loaded only after the selected controls were fixed. May rejects the
set: 1 positive, 19 negative, 2 flat, median May return -0.064568, best May
return +0.010172, and worst May return -0.134535. The four strict pseudo-OOS
controls all lose in May.

WPR106-208 therefore rejects the WPR106-139 strict calendar/session pocket as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready. The
useful evidence is that alternate pre-May train windows can produce pseudo-OOS
positives, but those controls still do not transfer to May.

Final close validation passed:

```powershell
python -m compileall -q data\research\wpr106_208_calendar_profile_train_window_control_audit\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
